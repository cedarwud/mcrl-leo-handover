"""Fast synthetic contract tests for the V0.4 C3 source runner."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.interference import empty_radiating_beams
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.step import ActionEvaluation, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_v04_c3_schedule import (
    C3_V04_INFORMED_SOURCE_RULE,
    C3V04ContextCandidate,
    C3V04SourceSchedule,
    read_v04_c3_schedule,
)
from mcrl.runtime.ee_axis_v04_c3_selector import C3V04SourceSelection
from mcrl.runtime.ee_axis_v04_c3_state import (
    EE_AXIS_V04_C3_STATE_SCHEMA,
    EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
)


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "c3-v04" / "run_v04_c3_source.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "run_v04_c3_source_w81", RUNNER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _table(user: int) -> SlotTable:
    # Every action is legal and has a distinct physical key, so the synthetic
    # schedule can exercise the full 28-action graph without real geometry.
    norads = np.asarray(
        [1000 + user * 100 + action for action in range(NUM_ACTIONS)],
        dtype=np.int64,
    )
    cells = np.arange(NUM_ACTIONS, dtype=np.int64) + 1
    return SlotTable(
        norads,
        cells,
        np.ones(NUM_ACTIONS, dtype=np.bool_),
    )


class _FakeEnvironment:
    def __init__(self, *, evaluate_guard=None) -> None:
        tables = tuple(_table(user) for user in range(3))
        masks = np.stack([table.mask for table in tables])
        self.candidates = SimpleNamespace(slot_tables=tables, masks=masks)
        self.observation = StepObservation(
            step_index=0,
            candidates=self.candidates,
            user_states=(object(), object(), object()),
            state_matrix=np.zeros((3, 112), dtype=np.float32),
            masks=masks,
            candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
        )
        self.environment = object.__new__(StepEnvironment)
        self.environment.num_users = 3
        self.environment._candidates = self.candidates
        self.environment._previous_association = [None, None, None]
        self.environment._previous_served_rate_bps = np.zeros(
            3, dtype=np.float64
        )
        self.environment._previous_link_power_w = np.zeros(3, dtype=np.float64)
        self.environment._previous_demand = {}
        self.environment._previous_radiating = empty_radiating_beams()
        self.environment._segments = [None, None, None]
        self.environment._step_index = 0
        self.environment.physics = SimpleNamespace(
            beam_power_max_w=2.2,
            fading_enabled=True,
        )
        self.environment.driver = SimpleNamespace(
            grid=SimpleNamespace(),
            step_index=0,
            config=SimpleNamespace(
                steps_per_episode=10,
                ephemeris=SimpleNamespace(time_step_s=2.0),
            ),
        )
        if evaluate_guard is not None:
            self.environment.evaluate_actions = evaluate_guard
        self.last_outcome = SimpleNamespace(observation=self.observation)

    def reset(self, env_rng, mobility_rng):
        del env_rng, mobility_rng
        self.environment._step_index = 0
        self.environment.driver.step_index = 0
        self.environment._candidates = self.candidates
        self.observation = StepObservation(
            step_index=0,
            candidates=self.candidates,
            user_states=(object(), object(), object()),
            state_matrix=np.zeros((3, 112), dtype=np.float32),
            masks=self.candidates.masks,
            candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
        )
        self.last_outcome = SimpleNamespace(observation=self.observation)
        return (
            list(self.observation.user_states),
            [SimpleNamespace(mask=row.copy()) for row in self.observation.masks],
            self.observation,
        )

    def step(self, actions, env_rng):
        del actions, env_rng
        step = self.environment._step_index + 1
        self.environment._step_index = step
        self.environment.driver.step_index = step
        self.observation = StepObservation(
            step_index=step,
            candidates=self.candidates,
            user_states=(object(), object(), object()),
            state_matrix=np.zeros((3, 112), dtype=np.float32),
            masks=self.candidates.masks,
            candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
        )
        self.last_outcome = SimpleNamespace(observation=self.observation)
        return SimpleNamespace(
            done=step >= 10,
            user_states=list(self.observation.user_states),
            action_masks=[
                SimpleNamespace(mask=row.copy())
                for row in self.observation.masks
            ],
        )


class _FakeWrapped:
    def __init__(self, *, evaluate_guard=None) -> None:
        fake = _FakeEnvironment(evaluate_guard=evaluate_guard)
        self.environment = fake.environment
        self._fake = fake
        self.last_outcome = fake.last_outcome

    def reset(self, env_rng, mobility_rng):
        result = self._fake.reset(env_rng, mobility_rng)
        self.last_outcome = self._fake.last_outcome
        return result

    def step(self, actions, env_rng):
        result = self._fake.step(actions, env_rng)
        self.last_outcome = self._fake.last_outcome
        return result


class _FakeTrainer:
    def __init__(self) -> None:
        self.replay = []
        self.version = 1


def _runtime(runner, *, evaluate_guard=None):
    trainer = _FakeTrainer()

    def frozen_archive(record, tle_root, target_root):
        del record, tle_root, target_root
        return object()

    def load_trainer(record, archive, *, run_dir, users):
        del record, archive, run_dir, users
        return trainer, {
            "checkpoint_sha256": runner.EXPECTED_MAIN_CHECKPOINT_SHA256
        }

    def make_environment(archive, *, users):
        del archive
        assert users == runner.USERS
        return _FakeWrapped(evaluate_guard=evaluate_guard)

    def evaluation_rngs(seed):
        sequence = np.random.SeedSequence(int(seed)).spawn(4)
        return tuple(np.random.default_rng(child) for child in sequence)

    def main_actions(trainer_arg, wrapped, states, masks, observation, env_rng):
        del trainer_arg, wrapped, states, masks, observation, env_rng
        return np.zeros(runner.USERS, dtype=np.int64)

    def network_snapshot(trainer_arg):
        return trainer_arg.version

    def networks_equal(trainer_arg, before):
        return trainer_arg.version == before

    return (
        runner.C3V04RunnerRuntime(
            frozen_archive=frozen_archive,
            load_trainer=load_trainer,
            make_environment=make_environment,
            evaluation_rngs=evaluation_rngs,
            main_actions=main_actions,
            network_snapshot=network_snapshot,
            networks_equal=networks_equal,
        ),
        trainer,
    )


def _configure_small_protocol(runner, monkeypatch):
    monkeypatch.setattr(runner, "USERS", 3)
    monkeypatch.setattr(runner, "MAX_SOURCE_STEPS", 2)
    monkeypatch.setattr(
        runner,
        "SOURCE_SEED_SPLIT",
        {
            1: "train",
            2: "train",
            3: "train",
            4: "train",
            5: "validation",
            6: "validation",
            7: "validation",
        },
    )
    monkeypatch.setattr(runner, "TRAIN_CONTEXT_GOAL", 8)
    monkeypatch.setattr(runner, "VALIDATION_CONTEXT_GOAL", 6)
    monkeypatch.setattr(runner, "TRAIN_ROW_BUDGET", 32)
    monkeypatch.setattr(runner, "VALIDATION_ROW_BUDGET", 24)


def _install_outcome_blind_selector(runner, monkeypatch):
    calls = {seed: 0 for seed in runner.SOURCE_SEED_SPLIT}
    groups = (
        (1, 2, 3, 4),
        (5, 6, 7, 8),
        (9, 10, 11, 12),
        (13, 14, 15, 16),
        (17, 18, 19, 20),
        (21, 22, 23, 24),
        (25, 26, 27),
    )
    train_seeds = (1, 2, 3, 4)
    train_index = {seed: index for index, seed in enumerate(train_seeds)}

    def fake_select(
        environment,
        observation,
        *,
        anchor_sha256,
        reference_actions,
        interval_s,
        kappa_bits,
        max_focal_users,
        state,
    ):
        del environment, interval_s, kappa_bits, max_focal_users
        return C3V04SourceSelection(
            anchor_sha256=anchor_sha256,
            step_index=int(observation.step_index),
            source_rule=C3_V04_INFORMED_SOURCE_RULE,
            state_schema=EE_AXIS_V04_C3_STATE_SCHEMA,
            state_schema_sha256=EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
            state=state,
            reference_actions=np.asarray(reference_actions),
            eligible_focal_users=(0,),
            selected_focal_users=(0,),
            all_opportunities=(),
            opportunities=(),
        )

    def fake_contexts(*, source_seed, split, selection):
        ordinal = calls[source_seed]
        calls[source_seed] += 1
        if split == "train":
            group_index = train_index[source_seed] * 2 + ordinal
            candidates = groups[group_index] if group_index < len(groups) else (1,)
        else:
            candidates = (1, 2, 3, 4)
        row = C3V04ContextCandidate(
            source_seed=source_seed,
            split=split,
            anchor_sha256=selection.anchor_sha256,
            state_observation_sha256=selection.state.state_sha256,
            step_index=selection.step_index,
            focal_user=0,
            source_rule=C3_V04_INFORMED_SOURCE_RULE,
            reference_action=0,
            reference_physical_key=(1000, 1),
            candidate_actions=tuple(candidates),
            candidate_physical_keys=tuple(
                (1000 + int(action), 1 + int(action))
                for action in candidates
            ),
            burden_deltas=tuple(float(action) for action in candidates),
            satellite_burden_deltas=tuple(
                float(action + 0.5) for action in candidates
            ),
            victim_pressures=tuple(float(action + 1) for action in candidates),
            satellite_victim_pressures=tuple(
                float(action + 1.5) for action in candidates
            ),
        )
        row.verify()
        return (row,)

    monkeypatch.setattr(runner, "select_v04_c3_source", fake_select)
    monkeypatch.setattr(runner, "contexts_from_selection", fake_contexts)


def _write_fake_prereg(runner, tmp_path, monkeypatch):
    path = tmp_path / "prereg.json"
    path.write_text("{}", encoding="ascii")
    file_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    prereg_digest = "d" * 64
    ephemeris_sha256 = "e" * 64
    monkeypatch.setattr(runner, "EXPECTED_PREREG_FILE_SHA256", file_sha256)
    monkeypatch.setattr(runner, "EXPECTED_PREREG_DIGEST", prereg_digest)
    monkeypatch.setattr(
        runner,
        "EXPECTED_EPHEMERIS_FILE_SET_SHA256",
        ephemeris_sha256,
    )
    record = SimpleNamespace(
        digest=prereg_digest,
        sections={"ephemeris": {"file_set_sha256": ephemeris_sha256}},
    )
    return path, record


def _write_fake_main_authority(runner, tmp_path, monkeypatch):
    root = tmp_path / "main"
    root.mkdir()
    files = {
        "status.json": b"fake-status\n",
        "episode-logs.json": b"fake-episode-logs\n",
        "final-checkpoint.pt": b"fake-checkpoint\n",
    }
    for name, payload in files.items():
        (root / name).write_bytes(payload)
    monkeypatch.setattr(
        runner,
        "EXPECTED_MAIN_STATUS_FILE_SHA256",
        hashlib.sha256(files["status.json"]).hexdigest(),
    )
    monkeypatch.setattr(
        runner,
        "EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256",
        hashlib.sha256(files["episode-logs.json"]).hexdigest(),
    )
    monkeypatch.setattr(
        runner,
        "EXPECTED_MAIN_CHECKPOINT_SHA256",
        hashlib.sha256(files["final-checkpoint.pt"]).hexdigest(),
    )
    return root


def _install_smoke_selector(runner, monkeypatch):
    def outcome_blind_select(
        environment,
        observation,
        *,
        anchor_sha256,
        reference_actions,
        interval_s,
        kappa_bits,
        max_focal_users,
        state,
    ):
        del environment, reference_actions, interval_s, kappa_bits, max_focal_users
        if int(observation.step_index) == 0:
            return None
        table = observation.candidates.slot_tables[0]
        return SimpleNamespace(
            anchor_sha256=anchor_sha256,
            step_index=int(observation.step_index),
            source_rule=C3_V04_INFORMED_SOURCE_RULE,
            state=state,
            selected_focal_users=(0,),
            opportunities=tuple(
                SimpleNamespace(
                    focal_user=0,
                    candidate_action=action,
                    reference_action=0,
                    reference_physical_key=runner._physical_key(table, 0),
                    candidate_physical_key=runner._physical_key(table, action),
                    burden_delta=delta,
                    satellite_burden_delta=delta / 2.0,
                    victim_pressure=2.0,
                    satellite_victim_pressure=1.0,
                )
                for action, delta in ((1, 1.0), (2, -1.0))
            ),
            verify=lambda: None,
        )

    monkeypatch.setattr(runner, "select_v04_c3_source", outcome_blind_select)


def _fake_smoke_evaluate(self, actions, rng):
    del self, rng
    action = int(actions[0])
    return ActionEvaluation(
        rewards=(),
        resolution=SimpleNamespace(),
        energy=SimpleNamespace(),
        interference=SimpleNamespace(),
        radiating=empty_radiating_beams(),
        link_power_w=np.zeros(3, dtype=np.float64),
        link_sinr=np.zeros(3, dtype=np.float64),
        link_rate_bps=np.asarray(
            [100.0, 200.0 + action, 300.0], dtype=np.float64
        ),
        handovers=(),
        system_power_w=10.0 + action,
        fixed_power_w=0.0,
    )


def _prepare(runner, tmp_path, monkeypatch, *, evaluate_guard=None):
    _configure_small_protocol(runner, monkeypatch)
    prereg, record = _write_fake_prereg(runner, tmp_path, monkeypatch)
    main_dir = _write_fake_main_authority(runner, tmp_path, monkeypatch)
    smoke_runtime, _smoke_trainer = _runtime(runner)
    _install_smoke_selector(runner, monkeypatch)
    monkeypatch.setattr(
        StepEnvironment, "evaluate_actions", _fake_smoke_evaluate
    )
    smoke_dir = tmp_path / "smoke"
    runner.smoke(
        output_dir=smoke_dir,
        tle_root=tmp_path / "tle",
        prereg_path=prereg,
        main_dir=main_dir,
        runtime=smoke_runtime,
        record=record,
    )

    _install_outcome_blind_selector(runner, monkeypatch)
    runtime, trainer = _runtime(runner, evaluate_guard=evaluate_guard)
    output = tmp_path / "prepared"
    receipt = runner.prepare(
        output_dir=output,
        tle_root=tmp_path / "tle",
        prereg_path=prereg,
        main_dir=main_dir,
        smoke_dir=smoke_dir,
        runtime=runtime,
        record=record,
    )
    return output, prereg, runtime, trainer, receipt, record


def test_prepare_is_outcome_blind_and_seals_exact_schedule_contract(
    tmp_path, monkeypatch
):
    runner = _module()
    evaluate_calls = 0

    def forbidden(*args, **kwargs):
        nonlocal evaluate_calls
        evaluate_calls += 1
        raise AssertionError("prepare must not call evaluate_actions")

    output, prereg, _runtime_adapter, trainer, receipt, _record = _prepare(
        runner, tmp_path, monkeypatch, evaluate_guard=forbidden
    )
    assert evaluate_calls == 0
    assert trainer.replay == []
    assert receipt["counterfactual_outcomes_evaluated"] is False
    assert receipt["candidate_reference_branches_evaluated"] is False
    assert receipt["test_split_present"] is False
    assert receipt["training"] is False

    schedule = read_v04_c3_schedule(output / "schedule.json")
    assert isinstance(schedule, C3V04SourceSchedule)
    assert len(schedule.train) == 8
    assert len(schedule.validation) == 6
    assert runner._context_balance(schedule) == {
        "train": {"1": 2, "2": 2, "3": 2, "4": 2},
        "validation": {"5": 2, "6": 2, "7": 2},
    }
    train_pairs = {
        pair for row in schedule.train for pair in row.directed_pairs
    }
    assert {action for pair in train_pairs for action in pair} == set(range(28))
    validation_pairs = {
        pair for row in schedule.validation for pair in row.directed_pairs
    }
    assert validation_pairs <= train_pairs


def test_prepare_rejects_missing_or_tampered_real_tle_smoke(
    tmp_path, monkeypatch
):
    runner = _module()
    _configure_small_protocol(runner, monkeypatch)
    prereg, record = _write_fake_prereg(runner, tmp_path, monkeypatch)
    main_dir = _write_fake_main_authority(runner, tmp_path, monkeypatch)
    runtime, _trainer = _runtime(runner)
    _install_outcome_blind_selector(runner, monkeypatch)

    with pytest.raises(runner.C3V04SourceRunnerError, match="smoke authority"):
        runner.prepare(
            output_dir=tmp_path / "missing-smoke-prepare",
            tle_root=tmp_path / "tle",
            prereg_path=prereg,
            main_dir=main_dir,
            smoke_dir=tmp_path / "absent-smoke",
            runtime=runtime,
            record=record,
        )

    _install_smoke_selector(runner, monkeypatch)
    monkeypatch.setattr(
        StepEnvironment, "evaluate_actions", _fake_smoke_evaluate
    )
    smoke_dir = tmp_path / "tampered-smoke"
    runner.smoke(
        output_dir=smoke_dir,
        tle_root=tmp_path / "tle",
        prereg_path=prereg,
        main_dir=main_dir,
        runtime=runtime,
        record=record,
    )
    receipt_path = smoke_dir / "receipt.json"
    payload = json.loads(receipt_path.read_text(encoding="ascii"))
    payload["published_learning_data"] = True
    receipt_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="ascii",
    )
    _install_outcome_blind_selector(runner, monkeypatch)
    with pytest.raises(runner.C3V04SourceRunnerError, match="smoke receipt"):
        runner.prepare(
            output_dir=tmp_path / "tampered-smoke-prepare",
            tle_root=tmp_path / "tle",
            prereg_path=prereg,
            main_dir=main_dir,
            smoke_dir=smoke_dir,
            runtime=runtime,
            record=record,
        )


def test_prepare_rejects_self_consistent_but_unfrozen_main_lineage(
    tmp_path, monkeypatch
):
    runner = _module()
    _configure_small_protocol(runner, monkeypatch)
    prereg, record = _write_fake_prereg(runner, tmp_path, monkeypatch)
    _write_fake_main_authority(runner, tmp_path, monkeypatch)
    swapped = tmp_path / "swapped-main"
    swapped.mkdir()
    checkpoint = b"different-but-self-consistent-checkpoint\n"
    checkpoint_sha = hashlib.sha256(checkpoint).hexdigest()
    (swapped / "final-checkpoint.pt").write_bytes(checkpoint)
    (swapped / "episode-logs.json").write_text("[]\n", encoding="ascii")
    (swapped / "status.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "episodes_completed": 9000,
                "role": "main-training",
                "checkpoint_sha256": checkpoint_sha,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="ascii",
    )
    runtime, _trainer = _runtime(runner)
    with pytest.raises(runner.C3V04SourceRunnerError, match="Main status/log"):
        runner.prepare(
            output_dir=tmp_path / "swapped-main-prepare",
            tle_root=tmp_path / "tle",
            prereg_path=prereg,
            main_dir=swapped,
            smoke_dir=tmp_path / "not-reached-smoke",
            runtime=runtime,
            record=record,
        )


def test_generate_materializes_every_scheduled_row_without_sign_filter(
    tmp_path, monkeypatch
):
    runner = _module()
    output, prereg, runtime, trainer, _prepare_receipt, record = _prepare(
        runner, tmp_path, monkeypatch
    )
    producer_calls = []

    def fake_evaluate(self, actions, rng):
        del self, rng
        action = int(actions[0])
        if action == 0:
            rates = np.asarray([100.0, 200.0, 300.0], dtype=np.float64)
        elif action % 2:
            rates = np.asarray([100.0, 210.0, 300.0], dtype=np.float64)
        else:
            rates = np.asarray([100.0, 190.0, 300.0], dtype=np.float64)
        return ActionEvaluation(
            rewards=(),
            resolution=SimpleNamespace(),
            energy=SimpleNamespace(),
            interference=SimpleNamespace(),
            radiating=empty_radiating_beams(),
            link_power_w=np.zeros(3, dtype=np.float64),
            link_sinr=np.zeros(3, dtype=np.float64),
            link_rate_bps=rates,
            handovers=(),
            system_power_w=10.0 + action,
            fixed_power_w=0.0,
        )

    original_producer = runner.produce_v04_c3_opening_comparison

    def recording_producer(*args, **kwargs):
        result = original_producer(*args, **kwargs)
        producer_calls.append(
            (
                result.pair.anchor_sha256,
                result.pair.focal_user,
                result.pair.reference_action,
                result.pair.candidate_action,
                result.pair.route_target_surplus_bits,
            )
        )
        return result

    monkeypatch.setattr(StepEnvironment, "evaluate_actions", fake_evaluate)
    monkeypatch.setattr(
        runner, "produce_v04_c3_opening_comparison", recording_producer
    )
    real_replace = runner.os.replace

    def same_filesystem_publish(source, destination):
        source_path = Path(source).resolve()
        destination_path = Path(destination).resolve()
        if destination_path.name == "source-data":
            assert source_path.is_relative_to(destination_path.parent)
        return real_replace(source, destination)

    monkeypatch.setattr(runner.os, "replace", same_filesystem_publish)
    generated = runner.generate(
        output_dir=output,
        tle_root=tmp_path / "tle",
        prereg_path=prereg,
        main_dir=tmp_path / "main",
        runtime=runtime,
        record=record,
    )
    schedule = read_v04_c3_schedule(output / "schedule.json")
    expected_rows = sum(
        len(context.candidate_actions)
        for context in (*schedule.train, *schedule.validation)
    )
    assert len(producer_calls) == expected_rows
    assert generated["target_sign_filter"] is False
    assert generated["training"] is False
    assert trainer.replay == []
    assert any(row[-1] > 0.0 for row in producer_calls)
    assert any(row[-1] < 0.0 for row in producer_calls)
    assert sum(generated["dataset_rows"].values()) == expected_rows

    verified = runner.verify(output_dir=output, prereg_path=prereg)
    assert verified["status"] == "PASS_VERIFIED"
    assert sum(verified["dataset_rows"].values()) == expected_rows


def test_verify_rejects_tampered_generate_receipt(tmp_path, monkeypatch):
    runner = _module()
    output, prereg, runtime, _trainer, _prepare_receipt, record = _prepare(
        runner, tmp_path, monkeypatch
    )

    def fake_evaluate(self, actions, rng):
        del self, rng
        action = int(actions[0])
        return ActionEvaluation(
            rewards=(),
            resolution=SimpleNamespace(),
            energy=SimpleNamespace(),
            interference=SimpleNamespace(),
            radiating=empty_radiating_beams(),
            link_power_w=np.zeros(3, dtype=np.float64),
            link_sinr=np.zeros(3, dtype=np.float64),
            link_rate_bps=np.asarray(
                [100.0, 200.0 + action, 300.0], dtype=np.float64
            ),
            handovers=(),
            system_power_w=10.0,
            fixed_power_w=0.0,
        )

    monkeypatch.setattr(StepEnvironment, "evaluate_actions", fake_evaluate)
    runner.generate(
        output_dir=output,
        tle_root=tmp_path / "tle",
        prereg_path=prereg,
        main_dir=tmp_path / "main",
        runtime=runtime,
        record=record,
    )
    receipt_path = output / "source-data" / "receipt.json"
    payload = json.loads(receipt_path.read_text(encoding="ascii"))
    payload["target_sign_filter"] = True
    receipt_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="ascii",
    )
    with pytest.raises(runner.C3V04SourceRunnerError, match="generate receipt"):
        runner.verify(output_dir=output, prereg_path=prereg)


class _InferenceTrainer:
    """Small read-only policy surface for the runner's Main equivalence test."""

    def __init__(self, values: np.ndarray) -> None:
        self.config = SimpleNamespace(objective_weights=(0.5, 0.3, 0.2))
        self.values = np.asarray(values, dtype=np.float64)
        self.encoded_calls = 0
        self.scalarized_calls: list[tuple[float, float, float]] = []
        self.q_nets = tuple(torch.nn.Linear(1, 1, bias=False) for _ in range(3))

    def encode_states(self, states):
        self.encoded_calls += 1
        return np.zeros((len(states), 1), dtype=np.float32)

    def scalarized_q_values(self, encoded, *, objective_weights):
        assert encoded.shape == (self.values.shape[0], 1)
        self.scalarized_calls.append(tuple(objective_weights))
        return self.values.copy()


def test_main_decision_matches_common_masked_greedy_and_ignores_wrapper_masks():
    runner = _module()
    fake = _FakeWrapped()
    values = np.zeros((3, NUM_ACTIONS), dtype=np.float64)
    values[0, 2] = 8.0
    values[0, 5] = 3.0
    values[1, 7] = 9.0
    values[2, 11] = 6.0
    trainer = _InferenceTrainer(values)
    states = list(fake._fake.observation.user_states)
    # Deliberately pass a wrong wrapper-mask value.  The deployment authority
    # is the sealed StepObservation mask matrix, exactly as the live policy
    # sees it.
    wrong_wrapper_masks = [SimpleNamespace(mask=np.zeros(NUM_ACTIONS, dtype=bool))] * 3
    actions = runner._main_decision(
        trainer,
        fake,
        states,
        wrong_wrapper_masks,
        fake._fake.observation,
        None,
    )
    from mcrl.runtime.head_pivotality import masked_greedy_actions

    expected = masked_greedy_actions(values, fake._fake.observation.masks)
    np.testing.assert_array_equal(actions, expected)
    assert trainer.encoded_calls == 1
    assert trainer.scalarized_calls == [(0.5, 0.3, 0.2)]


def test_main_decision_rejects_mask_surface_that_does_not_match_q_surface():
    runner = _module()
    fake = _FakeWrapped()
    trainer = _InferenceTrainer(np.zeros((3, NUM_ACTIONS), dtype=np.float64))
    malformed = SimpleNamespace(
        masks=np.zeros((3, NUM_ACTIONS - 1), dtype=bool)
    )
    with pytest.raises(
        runner.C3V04SourceRunnerError,
        match="observation masks",
    ):
        runner._main_decision(
            trainer,
            fake,
            list(fake._fake.observation.user_states),
            [],
            malformed,
            None,
        )


def test_network_snapshot_detects_exact_tensor_mutation():
    runner = _module()
    trainer = _InferenceTrainer(np.zeros((3, NUM_ACTIONS), dtype=np.float64))
    before = runner._network_snapshot(trainer)
    assert runner._networks_equal(trainer, before) is True
    with torch.no_grad():
        trainer.q_nets[1].weight[0, 0].add_(1.0)
    assert runner._networks_equal(trainer, before) is False


def test_source_manifest_is_current_repo_closure_without_archived_runner_paths():
    runner = _module()
    source = RUNNER.read_text(encoding="utf-8")
    assert ".scratch/c2-v03" not in source
    paths = runner._source_paths()
    labels = {path.resolve().relative_to(REPO.resolve()).as_posix() for path in paths}
    assert ".scratch/c2-v03" not in labels
    assert ".scratch/ee-axis-redesign" not in labels
    assert all(
        not label.startswith((".scratch/c2-v03/", ".scratch/ee-axis-redesign/"))
        for label in labels
    )
    assert "scripts/run_head_pivotality_probe.py" in labels
    assert "pyproject.toml" in labels
    assert ".scratch/c3-v04/run_v04_c3_source.py" in labels
    assert "src/mcrl/runtime/head_pivotality.py" in labels
    assert {label for label in labels if label.startswith("src/mcrl/")} == {
        path.relative_to(REPO).as_posix()
        for path in (REPO / "src" / "mcrl").rglob("*.py")
    }
    manifest = runner._build_source_manifest()
    assert {
        row["path"] for row in manifest["files"]
    } == labels


def test_real_tle_smoke_seals_nonopening_schedule_and_only_publishes_smoke_data(
    tmp_path, monkeypatch
):
    """The bounded smoke cannot silently become production source or training."""

    runner = _module()
    _configure_small_protocol(runner, monkeypatch)
    runtime, trainer = _runtime(runner, evaluate_guard=None)

    def outcome_blind_select(
        environment,
        observation,
        *,
        anchor_sha256,
        reference_actions,
        interval_s,
        kappa_bits,
        max_focal_users,
        state,
    ):
        del environment, interval_s, kappa_bits, max_focal_users
        if int(observation.step_index) == 0:
            return None
        table = observation.candidates.slot_tables[0]
        return SimpleNamespace(
            anchor_sha256=anchor_sha256,
            step_index=int(observation.step_index),
            source_rule=C3_V04_INFORMED_SOURCE_RULE,
            state=state,
            selected_focal_users=(0,),
            opportunities=(
                SimpleNamespace(
                    focal_user=0,
                    candidate_action=1,
                    reference_action=0,
                    reference_physical_key=runner._physical_key(table, 0),
                    candidate_physical_key=runner._physical_key(table, 1),
                    burden_delta=1.0,
                    satellite_burden_delta=0.5,
                    victim_pressure=2.0,
                    satellite_victim_pressure=1.0,
                ),
                SimpleNamespace(
                    focal_user=0,
                    candidate_action=2,
                    reference_action=0,
                    reference_physical_key=runner._physical_key(table, 0),
                    candidate_physical_key=runner._physical_key(table, 2),
                    burden_delta=-1.0,
                    satellite_burden_delta=-0.5,
                    victim_pressure=2.0,
                    satellite_victim_pressure=1.0,
                ),
            ),
            verify=lambda: None,
        )

    monkeypatch.setattr(runner, "select_v04_c3_source", outcome_blind_select)

    def fake_evaluate(self, actions, rng):
        del self, rng
        action = int(actions[0])
        rates = np.asarray(
            [100.0, 200.0 + action, 300.0],
            dtype=np.float64,
        )
        return ActionEvaluation(
            rewards=(),
            resolution=SimpleNamespace(),
            energy=SimpleNamespace(),
            interference=SimpleNamespace(),
            radiating=empty_radiating_beams(),
            link_power_w=np.zeros(3, dtype=np.float64),
            link_sinr=np.zeros(3, dtype=np.float64),
            link_rate_bps=rates,
            handovers=(),
            system_power_w=10.0 + action,
            fixed_power_w=0.0,
        )

    monkeypatch.setattr(StepEnvironment, "evaluate_actions", fake_evaluate)
    prereg, record = _write_fake_prereg(runner, tmp_path, monkeypatch)
    main_dir = _write_fake_main_authority(runner, tmp_path, monkeypatch)
    output = tmp_path / "real-tle-smoke"
    result = runner.smoke(
        output_dir=output,
        tle_root=tmp_path / "tle",
        prereg_path=prereg,
        main_dir=main_dir,
        runtime=runtime,
        record=record,
    )

    assert result["status"] == "PASS_SMOKE_ONLY"
    assert result["source_seed"] == runner.SMOKE_SOURCE_SEED
    assert result["split"] == runner.SMOKE_SOURCE_SPLIT
    assert result["training"] is False
    assert result["held_out_ee_evaluated"] is False
    assert result["production_output_touched"] is False
    assert trainer.replay == []

    schedule = json.loads(
        (output / "smoke-schedule.json").read_text(encoding="ascii")
    )
    receipt = json.loads((output / "receipt.json").read_text(encoding="ascii"))
    assert schedule["split"] == "development_smoke"
    assert schedule["contexts"][0]["step_index"] == 1
    assert len(schedule["contexts"][0]["candidate_actions"]) == 2
    assert schedule["contexts"][0]["candidate_physical_keys"] == [
        [1001, 2],
        [1002, 3],
    ]
    assert receipt["schedule_sealed_before_counterfactuals"] is True
    assert receipt["all_scheduled_rows_materialized"] is True
    assert receipt["scheduled_rows"] == 2
    assert receipt["materialized_rows"] == 2
    assert receipt["nonopening_anchor_present"] is True
    assert receipt["physical_keys_verified"] is True
    assert receipt["state_bitwise_unchanged"] is True
    assert receipt["main_networks_bitwise_unchanged"] is True
    assert receipt["main_replay_unchanged"] is True
    assert receipt["counterfactual_outcomes_evaluated"] is True
    assert receipt["train_split_present"] is False
    assert receipt["validation_split_present"] is False
    assert receipt["test_split_present"] is False
    assert receipt["test_split_opened"] is False
    assert receipt["held_out_ee_evaluated"] is False
    assert receipt["ee_evaluated"] is False
    assert receipt["training"] is False
    assert receipt["optimizer_called"] is False
    assert receipt["smoke_dataset_for_training"] is False
    assert receipt["published_learning_data"] is False
    assert receipt["ephemeral_dataset_round_trip_verified"] is True
    assert len(receipt["comparison_sha256s"]) == 2
    assert not (output / "source-data").exists()
    assert not (output / "smoke-data").exists()
    assert {path.name for path in output.iterdir()} == {
        "source-manifest.json",
        "smoke-schedule.json",
        "smoke-schedule-seal.json",
        "receipt.json",
        "receipt-seal.json",
    }
