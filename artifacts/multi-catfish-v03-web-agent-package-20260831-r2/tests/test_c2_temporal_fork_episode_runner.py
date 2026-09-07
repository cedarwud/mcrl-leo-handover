"""Bounded orchestration tests for the append-only C2 V0.3 runner."""

from __future__ import annotations

import copy
from dataclasses import asdict as real_asdict, dataclass
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SMC_DIR = HERE.parent / "smc-er-short-ep"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SMC_DIR))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import c2_temporal_fork_episode_runner as runner  # noqa: E402
import c2_temporal_fork_training_step as training_step  # noqa: E402


def test_c2_code_authority_includes_policy_compositor_and_direct_runtime_dependencies():
    relative = {
        path.relative_to(runner.REPO).as_posix()
        for path in runner._c2_code_authority_paths()
    }
    required = {
        ".scratch/c2-v03/c2_temporal_fork_core.py",
        ".scratch/c2-v03/c2_temporal_fork_forecast_adapter.py",
        ".scratch/c2-v03/c2_temporal_fork_trainer_backend.py",
        ".scratch/c2-v03/c2_temporal_fork_option_runner.py",
        ".scratch/c2-v03/c2_temporal_fork_episode_runner.py",
        ".scratch/smc-er-short-ep/run_short_ep.py",
        ".scratch/smc-er-short-ep/smc_er_core.py",
        ".scratch/smc-er-short-ep/smc_er_roles.py",
        ".scratch/catfish-stage0/c3_reward_aligned_v3_trainer_backend.py",
    }

    assert required <= relative
    assert all(path.is_file() for path in runner._c2_code_authority_paths())
    assert runner._code_sha256(runner._c2_code_authority_paths()) != (
        runner._code_sha256(runner._default_code_paths())
    )


class _Trajectory:
    def __init__(self, environment):
        self.environment = environment
        self.states = None
        self.masks = None
        self.observation = None
        self.reset_count = 0

    def reset(self):
        self.reset_count += 1
        self.states = [object()]
        self.masks = [object()]
        self.observation = SimpleNamespace(candidates=SimpleNamespace(slot_tables=()))

    def advance(self, _result):  # pragma: no cover - patched source helpers do not use it
        raise AssertionError("fake trajectory advance should not be called")


class _Specialist:
    def __init__(self):
        self.syncs = 0

    def state_dict(self):
        return {"policy_version": 0}

    def sync_target(self):
        self.syncs += 1


class _EmptyLedger:
    def state_dict(self):
        return {}

    def __len__(self):
        return 0


class _Main:
    train_seed = 17

    def __init__(self, steps_per_episode: int):
        self.config = SimpleNamespace(
            target_update_every_episodes=100,
            discount_factor=0.9,
        )
        self.replay = []
        self._steps_per_episode = steps_per_episode
        self.syncs = 0

    def epsilon(self, _episode):
        return 0.1

    def sync_targets(self):
        self.syncs += 1

    def save_checkpoint(self, *_args, **_kwargs):
        return None

    def training_state_dict(self):
        return {"schema": "fake"}


def _runtime(steps_per_episode: int = 1):
    main = _Main(steps_per_episode)
    environment = SimpleNamespace(config=SimpleNamespace(steps_per_episode=steps_per_episode))
    trajectories = {
        source: _Trajectory(environment)
        for source in ("Main", "C1", "C2", "C3")
    }
    return runner._C2Runtime(
        main=main,
        trajectories=trajectories,
        specialists={source: _Specialist() for source in ("C1", "C2", "C3")},
        replays={source: SimpleNamespace(state_dict=lambda: {}) for source in ("C1", "C2", "C3")},
        consumed_ledger=_EmptyLedger(),
        c2_option_ledger=_EmptyLedger(),
        transaction_ledger=_EmptyLedger(),
        selection_rng=np.random.default_rng(11),
        checkpoint_sha256="a" * 64,
        environment_source_sha256="b" * 64,
        reward_source_sha256="c" * 64,
    )


class _ResumeEnvironment:
    def __init__(self, marker: str):
        self.config = SimpleNamespace(num_users=2, steps_per_episode=3)
        self.marker = marker

    def training_state_dict(self):
        return {"format_version": 1, "marker": self.marker}

    def load_training_state_dict(self, state):
        if state.get("format_version") != 1:
            raise ValueError("bad fake environment state")
        self.marker = str(state["marker"])


class _ResumeTrajectory:
    def __init__(self, source: str):
        self.environment = _ResumeEnvironment(source)
        self.env_rng = np.random.default_rng(101 + len(source))
        self.mobility_rng = np.random.default_rng(202 + len(source))
        self.states = [{"source": source, "cursor": 0}]
        self.masks = [{"source": source, "valid": True}]
        self.observation = {"source": source, "cursor": 0}


class _ResumeMain:
    def __init__(self):
        self.config = SimpleNamespace(trainer_name="resume-fixture", learning_rate=0.001)
        self.state = {
            "trainer_config": {"trainer_name": "resume-fixture", "learning_rate": 0.001},
            "step": 4,
        }

    def training_state_dict(self):
        return copy.deepcopy(self.state)

    def load_training_state_dict(self, state):
        if state.get("trainer_config") != {
            "trainer_name": "resume-fixture",
            "learning_rate": 0.001,
        }:
            raise ValueError("bad fake Main trainer config")
        self.state = copy.deepcopy(dict(state))


class _ResumeStateObject:
    def __init__(self, source: str):
        self.source = source
        self.state = {"source": source, "value": 1}

    def state_dict(self):
        return copy.deepcopy(self.state)

    def load_state_dict(self, state):
        if state.get("source") != self.source:
            raise ValueError("fake source mismatch")
        if "value" not in state:
            raise ValueError("fake state is incomplete")
        self.state = copy.deepcopy(dict(state))


def _resume_runtime():
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=4,
        users=2,
        train_seed=11,
        env_seed=12,
        mobility_seed=13,
    )
    trajectories = {
        source: _ResumeTrajectory(source)
        for source in ("Main", "C1", "C2", "C3")
    }
    trajectories["C3"]._c3_option = runner.legacy.OptionCommitment(
        focal_user=1,
        physical_key=(7, 8),
        remaining=2,
        opened_step=3,
    )
    return (
        config,
        runner._C2Runtime(
            main=_ResumeMain(),
            trajectories=trajectories,
            specialists={
                source: _ResumeStateObject(source)
                for source in ("C1", "C2", "C3")
            },
            replays={
                source: _ResumeStateObject(source)
                for source in ("C1", "C2", "C3")
            },
            consumed_ledger=_ResumeStateObject("consumed"),
            c2_option_ledger=_ResumeStateObject("c2-option"),
            transaction_ledger=_ResumeStateObject("joint"),
            selection_rng=np.random.default_rng(303),
            checkpoint_sha256="a" * 64,
            environment_source_sha256="b" * 64,
            reward_source_sha256="c" * 64,
            loop_config=config,
        ),
    )


def _resume_next_signature(runtime_state):
    values = [int(runtime_state.selection_rng.integers(0, 2**31))]
    for source in ("Main", "C1", "C2", "C3"):
        trajectory = runtime_state.trajectories[source]
        values.append(int(trajectory.env_rng.integers(0, 2**31)))
        values.append(int(trajectory.mobility_rng.integers(0, 2**31)))
    return tuple(values)


def test_runtime_snapshot_round_trips_all_sources_and_rngs(monkeypatch, tmp_path):
    config, original = _resume_runtime()
    monkeypatch.setattr(runner, "_network_digest", lambda _main: "a" * 64)
    path = tmp_path / "resume" / "state.pt"
    runner._save_runtime_state(path, original, episode=2, config=config)
    payload = runner._torch_load_runtime_state(path)
    assert payload["trainer_config"] == {
        "learning_rate": 0.001,
        "trainer_name": "resume-fixture",
    }
    assert payload["loop_config"]["acrm_eta"] == 1.0

    # Consume and mutate every category that the loader is required to own.
    original.main.state["step"] = 99
    original.specialists["C2"].state["value"] = 99
    original.replays["C3"].state["value"] = 99
    original.consumed_ledger.state["value"] = 99
    original.trajectories["C1"].environment.marker = "mutated"
    original.trajectories["C3"]._c3_option.remaining = 99
    _resume_next_signature(original)

    _, restored = _resume_runtime()
    assert runner.load_c2_v03_runtime_state(path, restored, config=config) == 2
    assert restored.main.state["step"] == 4
    assert restored.specialists["C2"].state["value"] == 1
    assert restored.replays["C3"].state["value"] == 1
    assert restored.consumed_ledger.state["value"] == 1
    assert restored.trajectories["C1"].environment.marker == "C1"
    assert restored.trajectories["C3"]._c3_option.remaining == 2

    # The untouched pre-save continuation and the loaded continuation must
    # draw identical values from selection plus every source stream.
    _, expected = _resume_runtime()
    runner.load_c2_v03_runtime_state(path, expected, config=config)
    assert _resume_next_signature(restored) == _resume_next_signature(expected)


def test_runtime_snapshot_rejects_an_old_or_missing_c2_policy_version(
    monkeypatch, tmp_path
):
    config, runtime_state = _resume_runtime()
    monkeypatch.setattr(runner, "_network_digest", lambda _main: "a" * 64)
    path = tmp_path / "resume" / "state.pt"
    runner._save_runtime_state(path, runtime_state, episode=2, config=config)
    payload = runner._torch_load_runtime_state(path)

    old = copy.deepcopy(dict(payload))
    old["c2_policy_version"] = "C2_V0.3A_FIXED_HOLD"
    with pytest.raises(ValueError, match="policy version"):
        runner._validate_runtime_snapshot(
            old, runtime_state=runtime_state, config=config
        )

    missing = copy.deepcopy(dict(payload))
    del missing["c2_policy_version"]
    with pytest.raises(ValueError, match="policy version"):
        runner._validate_runtime_snapshot(
            missing, runtime_state=runtime_state, config=config
        )


@pytest.mark.parametrize("tamper", ["config", "authority", "acrm", "trainer"])
def test_runtime_snapshot_rejects_tamper_before_mutation(monkeypatch, tmp_path, tamper):
    config, runtime_state = _resume_runtime()
    monkeypatch.setattr(runner, "_network_digest", lambda _main: "a" * 64)
    path = tmp_path / "state.pt"
    runner._save_runtime_state(path, runtime_state, episode=2, config=config)
    payload = copy.deepcopy(dict(runner._torch_load_runtime_state(path)))
    if tamper == "config":
        payload["loop_config"]["beta"] = 0.75
    elif tamper == "acrm":
        payload["loop_config"]["acrm_eta"] = 2.0
    elif tamper == "trainer":
        payload["trainer_config"]["learning_rate"] = 0.01
    else:
        payload["authority"]["environment_source_sha256"] = "d" * 64
    tampered = tmp_path / f"tampered-{tamper}.pt"
    runner.torch.save(payload, tampered)
    before = copy.deepcopy(runtime_state.main.state)

    with pytest.raises(ValueError):
        runner.load_c2_v03_runtime_state(tampered, runtime_state, config=config)
    assert runtime_state.main.state == before


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, True])
def test_loop_config_rejects_unbound_acrm_eta(value):
    with pytest.raises(ValueError, match="acrm_eta"):
        runner.C2EpisodeLoopConfig(
            arm="F111",
            episodes=1,
            users=1,
            train_seed=1,
            env_seed=2,
            mobility_seed=3,
            acrm_eta=value,
        )


def test_programmatic_runner_rejects_acrm_override_that_drifts_from_config(tmp_path):
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
        acrm_eta=1.0,
    )
    with pytest.raises(ValueError, match="does not match loop config identity"):
        runner.run_c2_v03_episode_loop(
            config=config,
            output_dir=tmp_path / "drift",
            archive=object(),
            trainer_config={"trainer_name": "fixture", "learning_rate": 0.001},
            acrm_eta=2.0,
        )


def test_runtime_snapshot_rolls_back_nested_restore_failure(monkeypatch, tmp_path):
    config, runtime_state = _resume_runtime()
    monkeypatch.setattr(runner, "_network_digest", lambda _main: "a" * 64)
    path = tmp_path / "state.pt"
    runner._save_runtime_state(path, runtime_state, episode=2, config=config)
    payload = copy.deepcopy(dict(runner._torch_load_runtime_state(path)))
    del payload["specialists"]["C2"]["value"]
    tampered = tmp_path / "tampered-nested.pt"
    runner.torch.save(payload, tampered)
    before = copy.deepcopy(runtime_state.main.state)

    with pytest.raises(ValueError, match="incomplete"):
        runner.load_c2_v03_runtime_state(tampered, runtime_state, config=config)
    assert runtime_state.main.state == before
    assert runtime_state.specialists["C2"].state["value"] == 1


def _choice(*, selected: bool):
    receipt = SimpleNamespace(
        support=(SimpleNamespace(option_id="o1"),) if selected else (),
        receipt_sha256="d" * 64,
        candidate_schedule_sha256="8" * 64,
        candidate_schedule_size=1 if selected else 0,
    )
    return SimpleNamespace(receipt=receipt)


def _patch_loop_common(monkeypatch, runtime_state):
    monkeypatch.setattr(runner, "_network_digest", lambda _main: "9" * 64)
    monkeypatch.setattr(
        training_step,
        "assert_real_candidate_main_identity",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner.legacy.FrozenMainComparator,
        "from_main",
        classmethod(lambda cls, _main: SimpleNamespace(version_sha256="e" * 64)),
    )
    main_bundle = SimpleNamespace(bundle_id="main-bundle")
    outcome = SimpleNamespace(
        reward_matrix=np.zeros((1, 3), dtype=np.float64),
        energy=SimpleNamespace(
            system_throughput_bps=10.0,
            system_consumed_power_w=5.0,
        ),
        resolution=SimpleNamespace(
            served=np.asarray([True], dtype=np.bool_),
            served_count=1,
        ),
    )
    monkeypatch.setattr(
        runner,
        "_main_source_step",
        lambda *_args, **_kwargs: (main_bundle, outcome, np.asarray([0])),
    )
    monkeypatch.setattr(
        runner,
        "_collect_c1",
        lambda *_args, **_kwargs: (SimpleNamespace(bundle_id="c1"), outcome, 0.0),
    )
    monkeypatch.setattr(
        runner,
        "_collect_c3",
        lambda *_args, **_kwargs: (SimpleNamespace(bundle_id="c3"), outcome, 0.0, "fake"),
    )
    monkeypatch.setattr(
        runner,
        "_save_runtime_state",
        lambda *_args, **_kwargs: None,
    )
    # Fake environments do not expose TrainerEnvironment.last_outcome.  The
    # successor-specific test below replaces this seam with an observation;
    # all other orchestration tests keep it side-effect free.
    monkeypatch.setattr(
        runner,
        "_advance_from_outcome",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(runner, "_write_json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner, "_sha256_file", lambda _path: "f" * 64)
    monkeypatch.setattr(runner, "asdict", lambda value: real_asdict(value) if hasattr(value, "__dataclass_fields__") else dict(vars(value)))


def test_arm_matrix_is_explicit_and_baseline_is_separate():
    assert runner.SUPPORTED_ARMS == ("B000", "F111", "A011", "A101", "A110")
    assert runner.ARM_ACTIVE_SOURCES["F111"] == frozenset({"C1", "C2", "C3"})
    assert runner.ARM_ACTIVE_SOURCES["A011"] == frozenset({"C2", "C3"})
    assert runner.ARM_ACTIVE_SOURCES["A101"] == frozenset({"C1", "C3"})
    assert runner.ARM_ACTIVE_SOURCES["A110"] == frozenset({"C1", "C2"})
    assert runner.ARM_LANES["B000"] is None
    default_config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    assert default_config.max_c2_candidates == 9
    with pytest.raises(ValueError, match="unsupported arm"):
        runner.C2EpisodeLoopConfig(
            arm="not-an-arm",
            episodes=1,
            users=1,
            train_seed=1,
            env_seed=2,
            mobility_seed=3,
        )


def test_baseline_uses_unchanged_trainer_with_read_only_main_telemetry(
    monkeypatch, tmp_path
):
    outcome = SimpleNamespace(
        reward_matrix=np.zeros((1, 3), dtype=np.float64),
        energy=SimpleNamespace(
            system_throughput_bps=10.0,
            system_consumed_power_w=5.0,
        ),
        resolution=SimpleNamespace(
            served=np.asarray([True], dtype=np.bool_),
            served_count=1,
        ),
    )

    class Environment:
        last_outcome = outcome

        def step(self, _actions, _rng):
            return object()

    @dataclass
    class Log:
        episode: int

    seen = {}

    class Trainer:
        def __init__(self, environment, _config, **_kwargs):
            seen["environment"] = environment
            self.env = environment

        def train(self, *, progress_every, episode_callback):
            assert progress_every == 1
            self.env.step([0], object())
            self.env.step([0], object())
            log = Log(episode=0)
            episode_callback(log)
            return [log]

        def save_checkpoint(self, *_args, **_kwargs):
            return None

        def training_state_dict(self):
            return {"state": "real"}

        def get_masking_diagnostics(self):
            return {"decision_steps_seen": 2}

    written = {}
    monkeypatch.setattr(runner.legacy, "_make_environment", lambda *_a, **_k: Environment())
    monkeypatch.setattr(runner, "MODQNTrainer", Trainer)
    monkeypatch.setattr(
        runner.legacy,
        "_save_periodic_main_checkpoint",
        lambda **_kwargs: {"episodes_completed": 1},
    )
    monkeypatch.setattr(runner.legacy, "_save_training_state", lambda *_a, **_k: None)
    monkeypatch.setattr(runner, "_sha256_file", lambda _path: "f" * 64)
    monkeypatch.setattr(
        runner,
        "_write_json",
        lambda path, payload: written.__setitem__(Path(path).name, payload),
    )

    result = runner._run_baseline_with_telemetry(
        output_dir=tmp_path,
        archive=object(),
        trainer_config=SimpleNamespace(episodes=1),
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
        checkpoint_every=1,
    )

    assert isinstance(
        seen["environment"], runner.c2_telemetry.OutcomeTelemetryEnvironment
    )
    assert result["dispatch"] == (
        "unchanged_MODQNTrainer.train+read_only_outcome_telemetry"
    )
    assert result["telemetry"]["main"]["steps"] == 2
    assert result["telemetry"]["main"]["ratio_of_sums_ee_bits_per_j"] == 2.0
    assert written["run-telemetry.json"] == result["telemetry"]


def test_c2_candidate_contract_error_fails_closed(monkeypatch):
    trajectory = SimpleNamespace(
        states=[object()],
        masks=[object()],
        observation=object(),
        environment=object(),
        env_rng=np.random.default_rng(1),
        mobility_rng=np.random.default_rng(2),
    )
    runtime_state = SimpleNamespace(
        main=object(),
        checkpoint_sha256="a" * 64,
        environment_source_sha256="b" * 64,
        reward_source_sha256="c" * 64,
        selection_rng=np.random.default_rng(3),
        specialists={"C2": object()},
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
        max_c2_candidates=1,
    )
    monkeypatch.setattr(
        runner.c2_backend,
        "_main_actions",
        lambda *_args, **_kwargs: (np.asarray([0]), ((1, 1),)),
    )
    monkeypatch.setattr(runner, "_departure_users", lambda *_args: [0])

    class BrokenService:
        def __init__(self, **_kwargs):
            raise TypeError("detached-copy sentinel")

    monkeypatch.setattr(
        runner.c2_backend, "C2TemporalForkTrainerBackend", BrokenService
    )

    with pytest.raises(
        runner.c2_backend.C2BackendError,
        match="candidate 0.*TypeError: detached-copy sentinel",
    ):
        runner._build_c2_choice(
            runtime_state,
            config=config,
            trajectory=trajectory,
            episode=0,
            epsilon=1.0,
            informed=True,
            remaining_steps=4,
            timestamp_ns=0,
        )


def test_programmatic_runner_leaves_durable_failed_journal(monkeypatch, tmp_path):
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    monkeypatch.setattr(
        runner,
        "_make_runtime",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("forced failure")),
    )
    output_dir = tmp_path / "failed-run"

    with pytest.raises(RuntimeError, match="forced failure"):
        runner.run_c2_v03_episode_loop(
            config=config,
            output_dir=output_dir,
            archive=object(),
            trainer_config={"trainer_name": "forced-failure", "learning_rate": 0.001},
        )

    journal = json.loads((output_dir / "run-journal.json").read_text())
    assert journal["status"] == "failed"
    assert journal["failure"] == {
        "error_message": "forced failure",
        "error_type": "RuntimeError",
    }


def test_programmatic_runner_closes_complete_journal(monkeypatch, tmp_path):
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    monkeypatch.setattr(runner, "_make_runtime", lambda **_kwargs: object())
    expected = {
        "dispatch": "bounded-fixture",
        "episodes": 1,
        "joint_transaction_count": 0,
        "checkpoint_sha256": "a" * 64,
        "trainer_config": {
            "trainer_name": "complete-fixture",
            "learning_rate": 0.001,
        },
        "acrm_eta": 1.0,
    }
    monkeypatch.setattr(runner, "_run_treatment", lambda **_kwargs: expected)
    output_dir = tmp_path / "complete-run"

    result = runner.run_c2_v03_episode_loop(
        config=config,
        output_dir=output_dir,
        archive=object(),
        trainer_config={"trainer_name": "complete-fixture", "learning_rate": 0.001},
    )

    assert result is expected
    journal = json.loads((output_dir / "run-journal.json").read_text())
    assert journal["status"] == "complete"
    assert journal["result_summary"] == {
        "dispatch": "bounded-fixture",
        "episodes": 1,
        "joint_transaction_count": 0,
        "checkpoint_sha256": "a" * 64,
    }
    assert journal["trainer_config"] == expected["trainer_config"]


def test_public_treatment_records_verified_c1_exp_prefill(monkeypatch, tmp_path):
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=100,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    manifest = tmp_path / "c1-exp-corpus-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    runtime_state = SimpleNamespace(
        main=SimpleNamespace(state_dim=125, action_dim=38),
        specialists={"C1": object()},
        replays={"C1": object()},
    )
    monkeypatch.setattr(runner, "_make_runtime", lambda **_kwargs: runtime_state)
    corpus = object()
    loaded = []

    def load_verified(path, *, expected_state_dim, expected_action_dim, tle_root):
        loaded.append((path, expected_state_dim, expected_action_dim, tle_root))
        return corpus

    monkeypatch.setattr(runner.legacy, "load_verified_c1_corpus", load_verified)
    prefilled = []

    def prefill(*, specialist, replay, informed, corpus):
        prefilled.append((specialist, replay, informed, corpus))
        return {
            "corpus_manifest": str(manifest.resolve()),
            "corpus_manifest_sha256": "a" * 64,
            "bundles": 60,
            "enters_main": False,
        }

    monkeypatch.setattr(runner.legacy, "_prefill_c1", prefill)

    def treatment(**_kwargs):
        assert prefilled
        return {
            "dispatch": "prefill-fixture",
            "episodes": 1,
            "joint_transaction_count": 0,
            "checkpoint_sha256": "b" * 64,
        }

    monkeypatch.setattr(runner, "_run_treatment", treatment)
    result = runner.run_c2_v03_episode_loop(
        config=config,
        output_dir=tmp_path / "run",
        archive=SimpleNamespace(root=tmp_path / "tle"),
        trainer_config={"trainer_name": "prefill-fixture", "learning_rate": 0.001},
        c1_corpus_manifest=manifest,
    )

    assert loaded == [(manifest.resolve(), 125, 38, tmp_path / "tle")]
    assert prefilled == [
        (runtime_state.specialists["C1"], runtime_state.replays["C1"], True, corpus)
    ]
    assert result["c1_prefill"]["bundles"] == 60
    assert result["c1_prefill"]["enters_main"] is False


def test_public_baseline_rejects_c1_exp_manifest(tmp_path):
    config = runner.C2EpisodeLoopConfig(
        arm="B000",
        episodes=1,
        users=100,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    manifest = tmp_path / "c1-exp-corpus-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="baseline cannot consume a C1 EXP corpus"):
        runner.run_c2_v03_episode_loop(
            config=config,
            output_dir=tmp_path / "baseline",
            archive=object(),
            trainer_config={"trainer_name": "baseline", "learning_rate": 0.001},
            c1_corpus_manifest=manifest,
        )


def test_programmatic_resume_loads_before_absolute_episode_continuation(
    monkeypatch, tmp_path
):
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=4,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    runtime_state = object()
    resume_state = tmp_path / "source-state.pt"
    resume_state.write_bytes(b"bounded-state")
    monkeypatch.setattr(runner, "_make_runtime", lambda **_kwargs: runtime_state)
    load_calls = []
    monkeypatch.setattr(
        runner,
        "load_c2_v03_runtime_state",
        lambda path, runtime, *, config: load_calls.append((path, runtime, config)) or 2,
    )
    treatment_calls = []
    expected = {
        "dispatch": "resume-fixture",
        "episodes": 4,
        "joint_transaction_count": 0,
        "checkpoint_sha256": "a" * 64,
    }

    def treatment(**kwargs):
        treatment_calls.append(kwargs)
        return dict(expected)

    monkeypatch.setattr(runner, "_run_treatment", treatment)
    monkeypatch.setattr(runner, "_sha256_file", lambda _path: "f" * 64)
    output_dir = tmp_path / "continued"
    result = runner.run_c2_v03_episode_loop(
        config=config,
        output_dir=output_dir,
        archive=object(),
        trainer_config={"trainer_name": "resume-fixture", "learning_rate": 0.001},
        resume_state=resume_state,
    )

    assert load_calls == [(resume_state.resolve(), runtime_state, config)]
    assert treatment_calls[0]["start_episode"] == 2
    assert result["resume_source"] == {
        "path": str(resume_state.resolve()),
        "sha256": "f" * 64,
        "episodes_completed": 2,
        "artifact_scope": "new continuation segment",
    }


def test_treatment_uses_absolute_episode_cursor_after_resume(monkeypatch, tmp_path):
    runtime_state = _runtime(steps_per_episode=1)
    _patch_loop_common(monkeypatch, runtime_state)
    monkeypatch.setattr(runner, "_fallback_c2_step", lambda *_a, **_k: None)
    monkeypatch.setattr(
        runner,
        "_combined_main_update",
        lambda *_a, **_k: SimpleNamespace(
            mode="exact_baseline_delegate", updated=False, warmup=True
        ),
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=4,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )

    result = runner._run_treatment(
        runtime_state=runtime_state,
        config=config,
        output_dir=tmp_path,
        acrm_eta=1.0,
        start_episode=2,
    )

    assert [row["episode"] for row in result["episode_rows"]] == [2, 3]
    assert result["start_episode"] == 2
    assert result["episodes_executed"] == 2
    assert result["episodes_completed"] == 4
    assert result["artifact_scope"] == "resume_segment_only"


def test_k0_fallback_consumes_one_c2_step_and_one_main_carrier(monkeypatch, tmp_path):
    # The first source step primes the reset trajectory; K=0 is sealed at the
    # next pre-outcome boundary and then consumes its own fallback step.
    runtime_state = _runtime(steps_per_episode=2)
    _patch_loop_common(monkeypatch, runtime_state)
    monkeypatch.setattr(
        runner,
        "_build_c2_choice",
        lambda *_args, **_kwargs: (_choice(selected=False), []),
    )
    c2_calls = []
    monkeypatch.setattr(
        training_step,
        "run_c2_training_step",
        lambda choice, **kwargs: c2_calls.append((choice, kwargs))
        or SimpleNamespace(admitted=False, updated=False),
    )
    fallback_calls = []
    monkeypatch.setattr(
        runner,
        "_fallback_c2_step",
        lambda *_args, **_kwargs: fallback_calls.append(True),
    )
    carrier_calls = []
    monkeypatch.setattr(
        runner,
        "_combined_main_update",
        lambda *_args, **_kwargs: carrier_calls.append(True)
        or SimpleNamespace(mode="exact_baseline_delegate", updated=False, warmup=True),
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    result = runner._run_treatment(
        runtime_state=runtime_state,
        config=config,
        output_dir=tmp_path,
        acrm_eta=1.0,
    )
    assert len(c2_calls) == 1
    assert c2_calls[0][1]["specialist"] is None
    assert len(fallback_calls) == 2
    assert len(carrier_calls) == 2
    assert result["joint_transaction_count"] == 0
    assert runtime_state.checkpoint_sha256 == "9" * 64


def test_empty_reset_frame_retries_until_a_real_candidate_schedule(monkeypatch, tmp_path):
    runtime_state = _runtime(steps_per_episode=3)
    _patch_loop_common(monkeypatch, runtime_state)
    choices = [(_choice(selected=False), []), (_choice(selected=True), [{"passed": True}])]
    build_calls = []

    def build(*_args, **_kwargs):
        build_calls.append(True)
        return choices.pop(0)

    monkeypatch.setattr(runner, "_build_c2_choice", build)
    unit = SimpleNamespace(committed_payloads=(1,))
    monkeypatch.setattr(
        runner.c2_option_runner,
        "commit_prepared_option",
        lambda *_args, **_kwargs: unit,
    )

    def fake_training_step(choice, **kwargs):
        if choice.receipt.support:
            kwargs["runner_fn"](object())
            return SimpleNamespace(
                admitted=True,
                updated=True,
                joint_committed=True,
            )
        return SimpleNamespace(
            admitted=False,
            updated=False,
            joint_committed=False,
        )

    monkeypatch.setattr(training_step, "run_c2_training_step", fake_training_step)
    fallback_calls = []
    monkeypatch.setattr(
        runner,
        "_fallback_c2_step",
        lambda *_args, **_kwargs: fallback_calls.append(True),
    )
    carrier_calls = []
    monkeypatch.setattr(
        runner,
        "_combined_main_update",
        lambda *_args, **_kwargs: carrier_calls.append(True)
        or SimpleNamespace(mode="exact_baseline_delegate", updated=False, warmup=True),
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    result = runner._run_treatment(
        runtime_state=runtime_state,
        config=config,
        output_dir=tmp_path,
        acrm_eta=1.0,
    )
    assert len(build_calls) == 2
    assert len(fallback_calls) == 2
    assert len(carrier_calls) == 2
    assert result["episode_rows"][0]["c2_options"] == 1
    assert result["episode_rows"][0]["c2_environment_steps"] == 3


def test_admitted_c2_option_owns_single_main_update_and_counts_four_steps(
    monkeypatch, tmp_path
):
    # One prime step plus the four primitive steps of the H=3+release option.
    runtime_state = _runtime(steps_per_episode=5)
    _patch_loop_common(monkeypatch, runtime_state)
    selected = _choice(selected=True)
    monkeypatch.setattr(
        runner,
        "_build_c2_choice",
        lambda *_args, **_kwargs: (selected, [{"passed": True}]),
    )
    unit = SimpleNamespace(committed_payloads=(1, 2, 3, 4))
    option_calls = []
    monkeypatch.setattr(
        runner.c2_option_runner,
        "commit_prepared_option",
        lambda prepared, **kwargs: option_calls.append((prepared, kwargs)) or unit,
    )
    training_calls = []

    def fake_training_step(choice, **kwargs):
        training_calls.append((choice, kwargs))
        kwargs["runner_fn"](object(), token="formal")
        return SimpleNamespace(
            admitted=True,
            updated=True,
            joint_committed=True,
        )

    monkeypatch.setattr(training_step, "run_c2_training_step", fake_training_step)
    fallback_calls = []
    monkeypatch.setattr(
        runner,
        "_fallback_c2_step",
        lambda *_args, **_kwargs: fallback_calls.append(True),
    )
    carrier_calls = []
    monkeypatch.setattr(
        runner,
        "_combined_main_update",
        lambda *_args, **_kwargs: carrier_calls.append(True)
        or SimpleNamespace(mode="exact_baseline_delegate", updated=False, warmup=True),
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    result = runner._run_treatment(
        runtime_state=runtime_state,
        config=config,
        output_dir=tmp_path,
        acrm_eta=1.0,
    )
    assert len(training_calls) == 1
    assert len(option_calls) == 1
    assert fallback_calls == [True]
    # The prime and the three later Main logical steps use the ordinary
    # carrier; the option boundary itself is owned by the formal transaction.
    assert len(carrier_calls) == 4
    first = result["episode_rows"][0]
    assert first["c2_environment_steps"] == 5
    assert first["c2_options"] == 1


def test_admitted_warmup_does_not_claim_the_main_update_slot(
    monkeypatch, tmp_path
):
    runtime_state = _runtime(steps_per_episode=5)
    _patch_loop_common(monkeypatch, runtime_state)
    selected = _choice(selected=True)
    monkeypatch.setattr(
        runner,
        "_build_c2_choice",
        lambda *_args, **_kwargs: (selected, [{"passed": True}]),
    )
    unit = SimpleNamespace(committed_payloads=(1, 2, 3, 4))
    monkeypatch.setattr(
        runner.c2_option_runner,
        "commit_prepared_option",
        lambda *_args, **_kwargs: unit,
    )

    def fake_training_step(_choice_value, **kwargs):
        kwargs["runner_fn"](object())
        return SimpleNamespace(
            admitted=True,
            updated=False,
            warmup=True,
            joint_committed=False,
        )

    monkeypatch.setattr(training_step, "run_c2_training_step", fake_training_step)
    monkeypatch.setattr(runner, "_fallback_c2_step", lambda *_args, **_kwargs: None)
    carrier_calls = []
    monkeypatch.setattr(
        runner,
        "_combined_main_update",
        lambda *_args, **_kwargs: carrier_calls.append(True)
        or SimpleNamespace(mode="warmup_no_update", updated=False, warmup=True),
    )
    written = {}
    monkeypatch.setattr(
        runner,
        "_write_json",
        lambda path, payload: written.__setitem__(Path(path).name, payload),
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    result = runner._run_treatment(
        runtime_state=runtime_state,
        config=config,
        output_dir=tmp_path,
        acrm_eta=1.0,
    )
    assert carrier_calls == [True, True, True, True, True]
    step = written["main-update-receipts.json"][1]
    assert step["formal_c2_owned_main_update"] is False
    assert step["main_carrier"]["mode"] == "warmup_no_update"


def test_live_option_advances_outer_c2_trajectory_once(monkeypatch, tmp_path):
    """Bulk live option steps must publish the exact live successor once."""

    runtime_state = _runtime(steps_per_episode=5)
    _patch_loop_common(monkeypatch, runtime_state)
    selected = _choice(selected=True)
    monkeypatch.setattr(
        runner,
        "_build_c2_choice",
        lambda *_args, **_kwargs: (selected, [{"passed": True}]),
    )
    unit = SimpleNamespace(committed_payloads=(1, 2, 3, 4))
    monkeypatch.setattr(
        runner.c2_option_runner,
        "commit_prepared_option",
        lambda *_args, **_kwargs: unit,
    )

    def fake_training_step(_choice_value, **kwargs):
        kwargs["runner_fn"](object())
        return SimpleNamespace(
            admitted=True,
            updated=True,
            warmup=False,
            joint_committed=True,
        )

    monkeypatch.setattr(training_step, "run_c2_training_step", fake_training_step)
    monkeypatch.setattr(
        runner,
        "_fallback_c2_step",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner,
        "_combined_main_update",
        lambda *_args, **_kwargs: SimpleNamespace(
            mode="exact_baseline_delegate", updated=False, warmup=True
        ),
    )
    advanced = []
    monkeypatch.setattr(
        runner,
        "_advance_from_outcome",
        lambda trajectory: advanced.append(trajectory),
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    result = runner._run_treatment(
        runtime_state=runtime_state,
        config=config,
        output_dir=tmp_path,
        acrm_eta=1.0,
    )
    assert advanced == [runtime_state.trajectories["C2"]]
    assert result["episode_rows"][0]["c2_options"] == 1
    assert result["episode_rows"][0]["c2_environment_steps"] == 5


def test_c2_forecast_binds_network_digest_after_prime_update(monkeypatch, tmp_path):
    """The forecast authority must be refreshed after the first source step."""

    runtime_state = _runtime(steps_per_episode=2)
    _patch_loop_common(monkeypatch, runtime_state)
    runtime_state.main.policy_marker = 0

    def digest(main):
        # A real Main optimizer/carrier update is represented by the marker
        # change below; the digest must observe the post-update marker.
        return f"{int(main.policy_marker):064x}"

    monkeypatch.setattr(runner, "_network_digest", digest)
    monkeypatch.setattr(
        runner,
        "_fallback_c2_step",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner,
        "_combined_main_update",
        lambda *_args, **_kwargs: setattr(runtime_state.main, "policy_marker", 1)
        or SimpleNamespace(mode="exact_baseline_delegate", updated=True, warmup=False),
    )
    seen = []

    def build(*_args, **_kwargs):
        seen.append(runtime_state.checkpoint_sha256)
        return _choice(selected=False), []

    monkeypatch.setattr(runner, "_build_c2_choice", build)
    monkeypatch.setattr(
        training_step,
        "run_c2_training_step",
        lambda *_args, **_kwargs: SimpleNamespace(
            admitted=False, updated=False, joint_committed=False
        ),
    )
    config = runner.C2EpisodeLoopConfig(
        arm="F111",
        episodes=1,
        users=1,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
    )
    runner._run_treatment(
        runtime_state=runtime_state,
        config=config,
        output_dir=tmp_path,
        acrm_eta=1.0,
    )
    assert seen == [f"{1:064x}"]


def test_option_audit_preserves_clock_receipt_but_exposes_stable_identity():
    @dataclass(frozen=True)
    class Chronology:
        schema: str
        option_id: str
        anchor_sha256: str
        forecast_started_ns: int
        forecast_completed_ns: int
        live_step_started_ns: int
        live_step_completed_ns: int
        forecast_sequence: tuple[str, ...]

    def make_unit(times):
        chronology = Chronology(
            schema="chronology-v1",
            option_id="option-1",
            anchor_sha256="a" * 64,
            forecast_started_ns=times[0],
            forecast_completed_ns=times[1],
            live_step_started_ns=times[2],
            live_step_completed_ns=times[3],
            forecast_sequence=("forecast", "live"),
        )
        proof = SimpleNamespace(plan_sha256="b" * 64, proof_sha256="c" * 64)
        sequence = SimpleNamespace(
            admission_proof=proof,
            selection_receipt_sha256="d" * 64,
            sequence_sha256="e" * 64,
        )
        return SimpleNamespace(
            chronology_receipt=chronology,
            closure=SimpleNamespace(
                plan=SimpleNamespace(
                    option_id="option-1",
                    main_bundle_ids=("bundle-1",),
                    chronology_receipt_sha256="f" * 64,
                )
            ),
            sequence=sequence,
            transition=SimpleNamespace(sequence_sha256="1" * 64),
        )

    receipt = SimpleNamespace(joint_record_sha256="2" * 64)
    first = runner._c2_option_audit(
        make_unit((10, 11, 12, 13)), receipt, episode=1, step_index=2
    )
    second = runner._c2_option_audit(
        make_unit((20, 21, 22, 23)), receipt, episode=1, step_index=2
    )

    assert first["chronology_receipt"]["forecast_started_ns"] == 10
    assert second["chronology_receipt"]["forecast_started_ns"] == 20
    assert (
        first["clock_excluded_identity_sha256"]
        == second["clock_excluded_identity_sha256"]
    )


def test_option_audit_rejects_out_of_order_monotonic_times():
    @dataclass(frozen=True)
    class Chronology:
        forecast_started_ns: int = 10
        forecast_completed_ns: int = 9
        live_step_started_ns: int = 11
        live_step_completed_ns: int = 12

    unit = SimpleNamespace(
        chronology_receipt=Chronology(),
        closure=SimpleNamespace(plan=SimpleNamespace()),
    )
    with pytest.raises(RuntimeError, match="out-of-order"):
        runner._c2_option_audit(
            unit, SimpleNamespace(), episode=0, step_index=0
        )
