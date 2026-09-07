"""Focused tests for the real TrainerEnvironment C3 V3 development bridge."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("c3_reward_aligned_v3_trainer_backend.py")
spec = importlib.util.spec_from_file_location("c3_v3_trainer_backend", MODULE_PATH)
backend = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = backend
spec.loader.exec_module(backend)

runner = backend.shadow
adapter = backend.adapter
c3 = runner.core


SOURCE = (7, 1)
DESTINATION_1 = (7, 2)
DESTINATION_2 = (7, 3)


class _ArchiveMustBeShared:
    def __deepcopy__(self, memo):
        raise AssertionError("immutable archive must not be deep-copied")


def _fake_environment(*, users: int = 2):
    archive = _ArchiveMustBeShared()
    driver = SimpleNamespace(
        archive=archive,
        config=SimpleNamespace(),
        grid=SimpleNamespace(),
        _users=SimpleNamespace(_xy_km=np.ones((users, 2)), _heading_rad=np.ones(users)),
        _dwell=SimpleNamespace(_anchors=np.ones(users, dtype=np.int64)),
        _tracker=SimpleNamespace(
            _latched=np.ones(users, dtype=bool),
            _condition_active=np.zeros(users, dtype=bool),
            _condition_started=np.zeros(users, dtype=np.int64),
            _ttt_elapsed=np.zeros(users, dtype=np.int64),
            _steps_seen=0,
            _primed=True,
        ),
        _satellites=SimpleNamespace(norad_ids=np.asarray([7], dtype=np.int64), records=()),
        _start_utc=None,
        _step_index=0,
        _frozen_window_norad_ids=np.asarray([7], dtype=np.int64),
    )
    environment = SimpleNamespace(
        driver=driver,
        physics=SimpleNamespace(fading_enabled=True),
        _ledgers=[SimpleNamespace(previous=None, _started=False) for _ in range(users)],
        _segments=[None] * users,
        _previous_radiating=SimpleNamespace(),
        _previous_demand={SOURCE: 1},
        _previous_association=[None] * users,
        _candidates=SimpleNamespace(),
        _mobility_rng=np.random.default_rng(2),
        _pending_segment_age=np.zeros(users, dtype=np.int64),
        _age_rng=np.random.default_rng(3),
        _step_index=0,
        _started=True,
    )
    return SimpleNamespace(
        environment=environment,
        sampler=SimpleNamespace(archive=archive),
        _epoch=None,
        _last_outcome=None,
    )


def test_clone_shares_archive_but_detaches_mutable_episode_state():
    wrapped = _fake_environment()
    cloned = backend._copy_trainer_environment(wrapped)
    assert cloned is not wrapped
    assert cloned.sampler is wrapped.sampler
    assert cloned.environment.driver.archive is wrapped.environment.driver.archive
    assert cloned.environment.driver is not wrapped.environment.driver
    assert cloned.environment.driver._users is not wrapped.environment.driver._users
    assert cloned.environment._ledgers is not wrapped.environment._ledgers
    assert cloned.environment._mobility_rng is not wrapped.environment._mobility_rng
    cloned.environment.driver._users._xy_km[0, 0] = 99.0
    assert wrapped.environment.driver._users._xy_km[0, 0] == 1.0
    assert cloned.environment.physics.fading_enabled is False
    assert wrapped.environment.physics.fading_enabled is True


def _slot_table(*physical_ids):
    from mcrl.env.action_contract import SlotTable

    norads = np.full(28, -1, dtype=np.int64)
    cells = np.full(28, -1, dtype=np.int64)
    mask = np.zeros(28, dtype=bool)
    for action, (norad, cell) in enumerate(physical_ids):
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _main_decision_for_tables(tables):
    return adapter.ScalarizedMainDecision(
        actions=(0,) * len(tables),
        physical_actions=(SOURCE,) * len(tables),
        objective_weights=adapter.OBJECTIVE_WEIGHTS,
        q_values=((1.0,),) * len(tables),
        masks=((True,),) * len(tables),
    )


def test_force_focal_remaps_physical_id_on_branch_local_table(monkeypatch):
    users = 2
    wrapped = _fake_environment(users=users)
    tables = [_slot_table(SOURCE, DESTINATION_1), _slot_table(SOURCE, DESTINATION_1)]
    observation = SimpleNamespace(
        step_index=0,
        num_users=users,
        candidates=SimpleNamespace(slot_tables=tables),
    )
    masks = [SimpleNamespace(mask=np.asarray([True, True] + [False] * 26, dtype=bool))] * users
    trainer = SimpleNamespace(config=SimpleNamespace(objective_weights=(0.5, 0.3, 0.2)))
    branch = backend.TrainerC3V3Branch(
        wrapped=wrapped,
        env_rng=np.random.default_rng(4),
        states=[object(), object()],
        masks=masks,
        observation=observation,
        trainer=trainer,
        focal_user_id=0,
        anchor_fingerprint_sha256="a" * 64,
    )
    instance = backend.TrainerEnvironmentC3V3Backend(
        wrapped=wrapped,
        states=branch.states,
        masks=branch.masks,
        observation=observation,
        env_rng=branch.env_rng,
        trainer=trainer,
        checkpoint_sha256="b" * 64,
        anchor_fingerprint_sha256="a" * 64,
        focal_user_id=0,
    )
    instance.source_id = SOURCE
    monkeypatch.setattr(backend, "_main_decision", lambda branch: _main_decision_for_tables(tables))
    captured = {}

    def fake_advance(
        branch, *, actions, main_focal_action, offset, branch_main_nonfocal_actions
    ):
        captured["actions"] = np.asarray(actions).copy()
        captured["offset"] = offset
        return runner.ShadowStep(
            evaluation=object(),
            focal_action=DESTINATION_1,
            nonfocal_actions={1: SOURCE},
            useful_bits=1.0,
            reentry=(False, False),
            events=(c3.EventClass.NONE, c3.EventClass.NONE),
            preview_commit_equal=True,
        )

    monkeypatch.setattr(backend, "_advance", fake_advance)
    result = instance.force_focal(branch, DESTINATION_1, 0)
    assert result.focal_action == DESTINATION_1
    assert captured["actions"].tolist() == [1, 0]
    assert captured["offset"] == 0


def test_reference_nonfocal_script_is_remapped_and_keeps_local_main_diagnostic(monkeypatch):
    users = 2
    wrapped = _fake_environment(users=users)
    tables = [_slot_table(SOURCE, DESTINATION_1), _slot_table(SOURCE, DESTINATION_1)]
    observation = SimpleNamespace(
        step_index=0,
        num_users=users,
        candidates=SimpleNamespace(slot_tables=tables),
    )
    masks = [
        SimpleNamespace(mask=np.asarray([True, True] + [False] * 26, dtype=bool))
        for _ in range(users)
    ]
    trainer = SimpleNamespace(config=SimpleNamespace(objective_weights=(0.5, 0.3, 0.2)))
    branch = backend.TrainerC3V3Branch(
        wrapped=wrapped,
        env_rng=np.random.default_rng(4),
        states=[object(), object()],
        masks=masks,
        observation=observation,
        trainer=trainer,
        focal_user_id=0,
        anchor_fingerprint_sha256="a" * 64,
    )
    instance = backend.TrainerEnvironmentC3V3Backend(
        wrapped=wrapped,
        states=branch.states,
        masks=branch.masks,
        observation=observation,
        env_rng=branch.env_rng,
        trainer=trainer,
        checkpoint_sha256="b" * 64,
        anchor_fingerprint_sha256="a" * 64,
        focal_user_id=0,
    )
    instance.source_id = SOURCE
    monkeypatch.setattr(
        backend, "_main_decision", lambda branch: _main_decision_for_tables(tables)
    )
    captured = {}

    def fake_advance(
        branch, *, actions, main_focal_action, offset, branch_main_nonfocal_actions
    ):
        captured["actions"] = np.asarray(actions).copy()
        captured["branch_main_nonfocal_actions"] = dict(branch_main_nonfocal_actions)
        return runner.ShadowStep(
            evaluation=object(),
            focal_action=DESTINATION_1,
            nonfocal_actions={1: DESTINATION_1},
            useful_bits=1.0,
            reentry=(False, False),
            events=(c3.EventClass.NONE, c3.EventClass.NONE),
            preview_commit_equal=True,
            branch_main_nonfocal_actions=branch_main_nonfocal_actions,
        )

    monkeypatch.setattr(backend, "_advance", fake_advance)
    result = instance.force_focal(
        branch,
        DESTINATION_1,
        0,
        reference_nonfocal_actions={1: DESTINATION_1},
    )
    assert result.nonfocal_actions == {1: DESTINATION_1}
    assert result.branch_main_nonfocal_actions == {1: SOURCE}
    assert captured["actions"].tolist() == [1, 1]
    assert captured["branch_main_nonfocal_actions"] == {1: SOURCE}


def test_unmappable_reference_nonfocal_script_fails_closed(monkeypatch):
    users = 2
    wrapped = _fake_environment(users=users)
    tables = [_slot_table(SOURCE, DESTINATION_1), _slot_table(SOURCE)]
    observation = SimpleNamespace(
        step_index=0,
        num_users=users,
        candidates=SimpleNamespace(slot_tables=tables),
    )
    masks = [
        SimpleNamespace(mask=np.asarray([True, True] + [False] * 26, dtype=bool)),
        SimpleNamespace(mask=np.asarray([True] + [False] * 27, dtype=bool)),
    ]
    trainer = SimpleNamespace(config=SimpleNamespace(objective_weights=(0.5, 0.3, 0.2)))
    branch = backend.TrainerC3V3Branch(
        wrapped=wrapped,
        env_rng=np.random.default_rng(4),
        states=[object(), object()],
        masks=masks,
        observation=observation,
        trainer=trainer,
        focal_user_id=0,
        anchor_fingerprint_sha256="a" * 64,
    )
    instance = backend.TrainerEnvironmentC3V3Backend(
        wrapped=wrapped,
        states=branch.states,
        masks=branch.masks,
        observation=observation,
        env_rng=branch.env_rng,
        trainer=trainer,
        checkpoint_sha256="b" * 64,
        anchor_fingerprint_sha256="a" * 64,
        focal_user_id=0,
    )
    instance.source_id = SOURCE
    monkeypatch.setattr(
        backend, "_main_decision", lambda branch: _main_decision_for_tables(tables)
    )
    with pytest.raises(RuntimeError, match="disappeared from current candidate table"):
        instance.force_focal(
            branch,
            DESTINATION_1,
            0,
            reference_nonfocal_actions={1: DESTINATION_1},
        )


def test_replay_prefix_preserves_anchor_observation_and_generator_lineage():
    users = 2
    wrapped = _fake_environment(users=users)
    tables = [_slot_table(SOURCE), _slot_table(SOURCE)]
    observation = SimpleNamespace(
        step_index=0,
        num_users=users,
        candidates=SimpleNamespace(slot_tables=tables),
        state_matrix=np.arange(users * 3, dtype=np.float64).reshape(users, 3),
        masks=np.asarray([[True] + [False] * 27] * users, dtype=bool),
    )
    states = [SimpleNamespace(uid=uid, vector=np.arange(3)) for uid in range(users)]
    masks = [SimpleNamespace(mask=row.copy()) for row in observation.masks]
    trainer = SimpleNamespace(config=SimpleNamespace(objective_weights=(0.5, 0.3, 0.2)))
    env_rng = np.random.default_rng(41)
    live_fingerprint = backend.live_anchor_fingerprint(
        wrapped,
        env_rng=env_rng,
        states=states,
        masks=masks,
        observation=observation,
        checkpoint_sha256="b" * 64,
    )
    backend_instance = backend.TrainerEnvironmentC3V3Backend(
        wrapped=wrapped,
        states=states,
        masks=masks,
        observation=observation,
        env_rng=env_rng,
        trainer=trainer,
        checkpoint_sha256="b" * 64,
        anchor_fingerprint_sha256="a" * 64,
        focal_user_id=0,
        derivation_anchor_fingerprint_sha256=live_fingerprint,
    )
    backend_instance.source_id = SOURCE
    anchor = runner.C3V3ShadowAnchor(
        checkpoint_sha256="b" * 64,
        expected_anchor_fingerprint_sha256="a" * 64,
        evaluation_seed=0,
        step_index=0,
        focal_user_id=0,
        source_id=SOURCE,
        prefix_actions=(),
    )
    branch = backend_instance.replay_prefix(anchor)
    assert branch.observation is not observation
    np.testing.assert_array_equal(branch.observation.state_matrix, observation.state_matrix)
    np.testing.assert_array_equal(branch.observation.masks, observation.masks)
    assert branch.observation.candidates is not observation.candidates
    assert branch.env_rng is not env_rng
    expected_env = backend.derive_forecast_rng(
        backend.FORECAST_ENV_NAMESPACE,
        checkpoint_sha256="b" * 64,
        anchor_fingerprint_sha256=live_fingerprint,
        focal_user_id=0,
        step_index=0,
        evaluation_seed=0,
    )
    expected_mobility = backend.derive_forecast_rng(
        backend.FORECAST_MOBILITY_NAMESPACE,
        checkpoint_sha256="b" * 64,
        anchor_fingerprint_sha256=live_fingerprint,
        focal_user_id=0,
        step_index=0,
        evaluation_seed=0,
    )
    assert backend._rng_state_sha256(branch.env_rng) == backend._rng_state_sha256(
        expected_env
    )
    assert branch.env_rng is not expected_env
    assert backend._rng_state_sha256(branch.env_rng) != backend._rng_state_sha256(env_rng)
    assert branch.wrapped.environment._mobility_rng is not expected_mobility
    assert backend._rng_state_sha256(
        branch.wrapped.environment._mobility_rng
    ) == backend._rng_state_sha256(expected_mobility)
    assert backend._rng_state_sha256(
        branch.wrapped.environment._mobility_rng
    ) != backend._rng_state_sha256(wrapped.environment._mobility_rng)
    # Derivation is digest-only: merely creating a forecast branch must not
    # consume the eventual live streams.
    assert backend._rng_state_sha256(env_rng) == backend._rng_state_sha256(
        np.random.default_rng(41)
    )
    assert branch.wrapped.environment._age_rng is not wrapped.environment._age_rng
    assert backend._rng_state_sha256(branch.wrapped.environment._age_rng) == backend._rng_state_sha256(
        wrapped.environment._age_rng
    )


def _fingerprinted_backend_fixture():
    users = 2
    wrapped = _fake_environment(users=users)
    tables = [_slot_table(SOURCE), _slot_table(SOURCE)]
    observation = SimpleNamespace(
        step_index=0,
        num_users=users,
        candidates=SimpleNamespace(slot_tables=tables),
        state_matrix=np.arange(users * 3, dtype=np.float64).reshape(users, 3),
        masks=np.asarray([[True] + [False] * 27] * users, dtype=bool),
    )
    states = [SimpleNamespace(uid=uid, vector=np.arange(3)) for uid in range(users)]
    masks = [SimpleNamespace(mask=row.copy()) for row in observation.masks]
    trainer = SimpleNamespace(config=SimpleNamespace(objective_weights=(0.5, 0.3, 0.2)))
    env_rng = np.random.default_rng(41)
    live_fingerprint = backend.live_anchor_fingerprint(
        wrapped,
        env_rng=env_rng,
        states=states,
        masks=masks,
        observation=observation,
        checkpoint_sha256="b" * 64,
    )
    forecast_fingerprint = backend._forecast_anchor_fingerprint(
        wrapped=wrapped,
        states=states,
        masks=masks,
        observation=observation,
        checkpoint_sha256="b" * 64,
        derivation_anchor_fingerprint_sha256=live_fingerprint,
        focal_user_id=0,
        step_index=0,
        evaluation_seed=0,
    )
    instance = backend.TrainerEnvironmentC3V3Backend(
        wrapped=wrapped,
        states=states,
        masks=masks,
        observation=observation,
        env_rng=env_rng,
        trainer=trainer,
        checkpoint_sha256="b" * 64,
        anchor_fingerprint_sha256=forecast_fingerprint,
        derivation_anchor_fingerprint_sha256=live_fingerprint,
        focal_user_id=0,
    )
    instance.source_id = SOURCE
    anchor = runner.C3V3ShadowAnchor(
        checkpoint_sha256="b" * 64,
        expected_anchor_fingerprint_sha256=forecast_fingerprint,
        evaluation_seed=0,
        step_index=0,
        focal_user_id=0,
        source_id=SOURCE,
        prefix_actions=(),
    )
    return instance, anchor, forecast_fingerprint


def test_fingerprint_recomputes_equal_positive_twins_from_actual_branch_state():
    instance, anchor, expected = _fingerprinted_backend_fixture()
    reference = instance.replay_prefix(anchor)
    candidate = instance.replay_prefix(anchor)

    assert reference is not candidate
    assert instance.fingerprint(reference) == expected
    assert instance.fingerprint(candidate) == expected
    assert reference.env_rng is not candidate.env_rng
    assert reference.wrapped.environment._mobility_rng is not candidate.wrapped.environment._mobility_rng
    assert backend._rng_state_sha256(reference.env_rng) == backend._rng_state_sha256(
        candidate.env_rng
    )
    assert backend._rng_state_sha256(
        reference.wrapped.environment._mobility_rng
    ) == backend._rng_state_sha256(candidate.wrapped.environment._mobility_rng)
    reference.env_rng.random()
    assert instance.fingerprint(reference) != expected
    candidate.wrapped.environment._mobility_rng.random()
    assert instance.fingerprint(candidate) != expected


def test_generic_runner_closes_on_mutated_twin_fingerprint():
    instance, anchor, _ = _fingerprinted_backend_fixture()
    original_replay = instance.replay_prefix
    calls = 0

    def replay_with_mutation(value):
        nonlocal calls
        calls += 1
        branch = original_replay(value)
        if calls == 2:
            branch.states[0].vector[0] += 1
        return branch

    instance.replay_prefix = replay_with_mutation
    receipt = runner.certify_candidate_support(
        instance,
        anchor=anchor,
        candidate_id=DESTINATION_1,
        expected_user_count=2,
    )
    assert receipt.status == "FAIL_CLOSED"
    assert receipt.certificate is None
    assert receipt.reasons == ("deep_twin_anchor_fingerprint_mismatch",)


def test_scan_refuses_horizon_shorter_than_hold_plus_release():
    result = backend.scan_current_support(
        wrapped=object(),
        states=[object()],
        masks=[object()],
        observation=SimpleNamespace(step_index=4, num_users=1),
        env_rng=np.random.default_rng(1),
        trainer=object(),
        checkpoint_sha256="b" * 64,
        steps_remaining=3,
    )
    assert result.status == "INSUFFICIENT_HORIZON"
    assert result.support_ids_by_user == {}
    assert result.scanned_candidates == 0


@dataclass(frozen=True)
class _FakeReceipt:
    candidate_id: tuple[int, int]
    certified: bool
    status: str = "PASS"

    def to_dict(self):
        return {"candidate_id": list(self.candidate_id), "certified": self.certified}


def test_scan_exposes_support_only_after_two_certified_choices(monkeypatch):
    users = 5
    wrapped = _fake_environment(users=users)
    tables = [
        _slot_table(SOURCE),
        _slot_table(SOURCE),
        _slot_table(SOURCE, DESTINATION_1, DESTINATION_2),
        _slot_table(SOURCE, DESTINATION_1),
        _slot_table(SOURCE, DESTINATION_2),
    ]
    masks = [
        SimpleNamespace(mask=np.asarray([True, True, True] + [False] * 25, dtype=bool))
        for _ in range(users)
    ]
    observation = SimpleNamespace(
        step_index=0,
        num_users=users,
        candidates=SimpleNamespace(slot_tables=tables),
        state_matrix=np.zeros((users, 1), dtype=np.float64),
        masks=np.asarray([row.mask for row in masks]),
    )
    states = [object() for _ in range(users)]
    main = adapter.ScalarizedMainDecision(
        actions=(0, 0, 0, 0, 0),
        physical_actions=(SOURCE, SOURCE, SOURCE, DESTINATION_1, DESTINATION_2),
        objective_weights=adapter.OBJECTIVE_WEIGHTS,
        q_values=((1.0,),) * users,
        masks=((True,),) * users,
    )
    load = SimpleNamespace(
        snapshot=SimpleNamespace(
            served_associations=(SOURCE, SOURCE, SOURCE, DESTINATION_1, DESTINATION_2),
            reported_eligible_loads={SOURCE: 3, DESTINATION_1: 1, DESTINATION_2: 1},
            reported_active_beams=frozenset({SOURCE, DESTINATION_1, DESTINATION_2}),
        )
    )
    monkeypatch.setattr(adapter, "scalarized_main_decision", lambda *args, **kwargs: main)
    monkeypatch.setattr(adapter, "canonical_load_projection", lambda evaluation: load)
    monkeypatch.setattr(adapter, "canonical_power_projection", lambda evaluation: object())
    monkeypatch.setattr(backend, "live_anchor_fingerprint", lambda *args, **kwargs: "a" * 64)
    monkeypatch.setattr(
        runner,
        "certify_candidate_support",
        lambda backend, *, anchor, candidate_id, expected_user_count, scheduled_anchor: _FakeReceipt(
            tuple(candidate_id), True
        ),
    )
    trainer = SimpleNamespace(config=SimpleNamespace(objective_weights=(0.5, 0.3, 0.2)))
    wrapped.environment.evaluate_actions = lambda actions, rng: object()
    result = backend.scan_current_support(
        wrapped=wrapped,
        states=states,
        masks=masks,
        observation=observation,
        env_rng=np.random.default_rng(1),
        trainer=trainer,
        checkpoint_sha256="b" * 64,
        steps_remaining=4,
        max_focal_users=1,
        max_candidates_per_focal=2,
    )
    assert result.status == "COMPLETE"
    assert result.scanned_focal_users == (2,)
    assert result.support_ids_by_user == {2: (DESTINATION_1, DESTINATION_2)}
    assert set(result.support_action_indices_by_focal[2]) == {
        DESTINATION_1,
        DESTINATION_2,
    }
    assert len(result.receipts_by_focal[2]) == 2

    monkeypatch.setattr(
        runner,
        "certify_candidate_support",
        lambda backend, *, anchor, candidate_id, expected_user_count, scheduled_anchor: _FakeReceipt(
            tuple(candidate_id), tuple(candidate_id) == DESTINATION_1
        ),
    )
    result_one = backend.scan_current_support(
        wrapped=wrapped,
        states=states,
        masks=masks,
        observation=observation,
        env_rng=np.random.default_rng(1),
        trainer=trainer,
        checkpoint_sha256="b" * 64,
        steps_remaining=4,
        max_focal_users=1,
        max_candidates_per_focal=2,
    )
    assert result_one.support_ids_by_user == {}
