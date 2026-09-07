"""Bounded deterministic smoke for the C2 V0.3 environment backend.

This test intentionally uses a tiny in-memory environment.  It exercises the
same exact ForecastStepPayload/chronology boundary without loading a 9000
episode checkpoint or claiming a scientific EE result.
"""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".scratch" / "c2-v03"))
sys.path.insert(0, str(ROOT / "src"))

import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import c3_reward_aligned_v3_trainer_backend as c3_backend  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.keyed_fading import (  # noqa: E402
    KEYED_FADING_VERSION,
    KeyedFadingField,
)


CHECKPOINT = "a" * 64
ENVIRONMENT = "b" * 64
REWARD = "c" * 64


def test_real_detached_copy_error_preserves_root_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    wrapped = SimpleNamespace(environment=SimpleNamespace(driver=object()))

    def fail_copy(_wrapped: object) -> object:
        raise TypeError("copy sentinel")

    monkeypatch.setattr(c3_backend, "_copy_trainer_environment", fail_copy)

    with pytest.raises(
        backend.C2BackendError,
        match=r"real detached TrainerEnvironment copy failed: TypeError: copy sentinel",
    ):
        backend._copy_detached_environment(wrapped)


class _Observation:
    def __init__(self, step_index: int, state_matrix: np.ndarray, tables: tuple[object, ...]):
        self.step_index = int(step_index)
        self.state_matrix = np.asarray(state_matrix, dtype=np.float32)
        self.masks = np.stack([table.mask for table in tables]).astype(bool)
        self.user_states = tuple(np.array(row, copy=True) for row in self.state_matrix)
        self.candidates = SimpleNamespace(slot_tables=tables)
        self.candidate_sinr = np.zeros((len(tables), 28), dtype=np.float64)

    @property
    def num_users(self) -> int:
        return len(self.user_states)


class _Table:
    def __init__(self, bindings: dict[int, tuple[int, int]]):
        self.mask = np.zeros(28, dtype=bool)
        self.norad_ids = np.full(28, -1, dtype=np.int64)
        self.cell_ids = np.full(28, -1, dtype=np.int64)
        for action, (norad, cell) in bindings.items():
            self.mask[action] = True
            self.norad_ids[action] = norad
            self.cell_ids[action] = cell

    def association(self, action: int):
        if int(action) < 0 or not bool(self.mask[int(action)]):
            return None
        return Association(int(self.norad_ids[int(action)]), int(self.cell_ids[int(action)]))


class _Resolution:
    def __init__(self, served: np.ndarray, active_beams: tuple[tuple[int, int], ...]):
        self.served = served
        self.active_beams = active_beams


class _Outcome:
    def __init__(self, observation: _Observation, actions: np.ndarray):
        focal_is_hold = int(actions[0]) == 3
        rewards = np.tile(np.asarray((1.0, -0.5, -1.0), dtype=np.float64), (2, 1))
        rewards[0, 1] = 0.0 if focal_is_hold else -0.5
        physical = (
            (1, 3) if focal_is_hold else (1, 11),
            (2, 11),
        )
        self.observation = observation
        self.reward_matrix = rewards
        self.resolution = _Resolution(np.ones(2, dtype=bool), physical)
        self.link_rate_bps = np.asarray((10.0, 10.0), dtype=np.float64)
        self.system_power_w = 90.0 if focal_is_hold else 100.0
        self.done = False


class _Result:
    def __init__(self, observation: _Observation, actions: np.ndarray):
        self.done = False
        self.user_states = [np.array(row, copy=True) for row in observation.state_matrix]
        self.action_masks = [SimpleNamespace(mask=np.array(table.mask, copy=True)) for table in observation.candidates.slot_tables]
        self.observation = observation


class _Wrapped:
    def __init__(self):
        tables = (
            _Table({3: (1, 3), 11: (1, 11)}),
            _Table({2: (2, 2), 11: (2, 11)}),
        )
        self._tables = tables
        self._offset = 0
        self._observation = _Observation(0, np.asarray(((0, 1, 2, 3), (4, 5, 6, 7)), dtype=np.float32), tables)
        self._last_outcome = None
        self.environment = SimpleNamespace(
            _mobility_rng=np.random.default_rng(19),
            physics=SimpleNamespace(fading_enabled=True),
            _previous_association=[Association(1, 3), Association(2, 11)],
            _previous_radiating=SimpleNamespace(
                norad_ids=np.asarray([], dtype=np.int64),
                cell_ids=np.asarray([], dtype=np.int64),
            ),
        )

    @property
    def last_outcome(self):
        return self._last_outcome

    def step(self, actions: np.ndarray, env_rng: np.random.Generator):
        # Consume only the detached RNG.  The chronology test detects any
        # accidental use of the live generator separately.
        _ = env_rng.random()
        next_matrix = self._observation.state_matrix + 1.0
        next_observation = _Observation(self._offset + 1, next_matrix, self._tables)
        self._last_outcome = _Outcome(next_observation, np.asarray(actions, dtype=np.int32))
        self._observation = next_observation
        self._offset += 1
        return _Result(next_observation, np.asarray(actions, dtype=np.int32))


class _TerminalWrapped(_Wrapped):
    def step(self, actions: np.ndarray, env_rng: np.random.Generator):
        result = super().step(actions, env_rng)
        result.done = True
        self._last_outcome.done = True
        return result


class _SupportExpiringWrapped(_Wrapped):
    """Fixture whose focal candidate key disappears after the opening step."""

    def step(self, actions: np.ndarray, env_rng: np.random.Generator):
        _ = env_rng.random()
        next_matrix = self._observation.state_matrix + 1.0
        # The next predecision table is the authority for offset one.  Once
        # the opening key is absent, the policy must latch release and use the
        # branch-local Main action for every remaining forecast offset.
        next_tables = (
            _Table({11: (1, 11)}),
            self._tables[1],
        )
        self._tables = next_tables
        next_observation = _Observation(self._offset + 1, next_matrix, next_tables)
        self._last_outcome = _Outcome(
            next_observation, np.asarray(actions, dtype=np.int32)
        )
        self._observation = next_observation
        self._offset += 1
        return _Result(next_observation, np.asarray(actions, dtype=np.int32))


class _Trainer:
    def __init__(self):
        self.config = SimpleNamespace(objective_weights=(0.5, 0.3, 0.2))
        self.inference_calls = 0

    def encode_states(self, states):
        return np.asarray(states, dtype=np.float32)

    def scalarized_q_values(self, encoded, *, objective_weights):
        del encoded, objective_weights
        self.inference_calls += 1
        q = np.full((2, 28), -100.0, dtype=np.float64)
        q[0, 3] = 9.0
        q[0, 11] = 10.0
        q[1, 2] = 9.0
        q[1, 11] = 10.0
        return q


def _backend(
    *,
    forecast_fading_mode: str = "disabled",
) -> tuple[backend.C2TemporalForkTrainerBackend, _Wrapped, _Trainer]:
    wrapped = _Wrapped()
    trainer = _Trainer()
    return (
        backend.C2TemporalForkTrainerBackend(
            wrapped=wrapped,
            states=list(wrapped._observation.user_states),
            masks=[SimpleNamespace(mask=np.array(table.mask, copy=True)) for table in wrapped._tables],
            observation=wrapped._observation,
            env_rng=np.random.default_rng(7),
            trainer=trainer,
            checkpoint_sha256=CHECKPOINT,
            environment_source_sha256=ENVIRONMENT,
            reward_source_sha256=REWARD,
            evaluation_seed=23,
            focal_user=0,
            pre_active_physical_ids=(),
            forecast_fading_mode=forecast_fading_mode,
        ),
        wrapped,
        trainer,
    )


def _construct_backend(
    wrapped: _Wrapped,
    trainer: _Trainer,
    *,
    focal_user: int = 0,
    states=None,
    masks=None,
) -> backend.C2TemporalForkTrainerBackend:
    return backend.C2TemporalForkTrainerBackend(
        wrapped=wrapped,
        states=(
            list(wrapped._observation.user_states)
            if states is None
            else states
        ),
        masks=(
            [SimpleNamespace(mask=np.array(table.mask, copy=True)) for table in wrapped._tables]
            if masks is None
            else masks
        ),
        observation=wrapped._observation,
        env_rng=np.random.default_rng(7),
        trainer=trainer,
        checkpoint_sha256=CHECKPOINT,
        environment_source_sha256=ENVIRONMENT,
        reward_source_sha256=REWARD,
        evaluation_seed=23,
        focal_user=focal_user,
        pre_active_physical_ids=(),
    )


def _rng_snapshot(value):
    return copy.deepcopy(value.bit_generator.state)


def test_one_candidate_build_is_exact_and_does_not_touch_live_state():
    service, wrapped, trainer = _backend()
    live_env_rng = _rng_snapshot(service.env_rng)
    live_mobility_rng = _rng_snapshot(service.mobility_rng)
    opening = np.array(service.observation.state_matrix, copy=True)
    initial_offset = wrapped._offset
    prepared = service.prepare_incumbent_hold(focal_user=0)

    built = prepared.run_forecast()

    assert built.certificate.passed is True
    assert built.certificate.hold_steps == 3
    assert prepared.phase == "forecast_complete"
    assert wrapped._offset == initial_offset
    np.testing.assert_array_equal(service.observation.state_matrix, opening)
    assert _rng_snapshot(service.env_rng) == live_env_rng
    assert _rng_snapshot(service.mobility_rng) == live_mobility_rng
    assert built.authority.forecast_namespace == backend.FORECAST_NAMESPACE
    assert built.authority.reference_checkpoint_sha256 == CHECKPOINT
    assert built.authority.environment_source_sha256 == ENVIRONMENT
    assert built.authority.reward_source_sha256 == REWARD
    # Reference/candidate forecast RNGs are separately labelled and hashed;
    # neither is the live RNG mapping.
    assert built.authority.forecast_rng_state_sha256 != built.authority.live_rng_state_sha256

    # The generated certificate is derived from exact traces.  Release is a
    # complete candidate-local Main joint action, not a focal-only release.
    assert built.evidence.hold_steps == 3
    assert built.evidence.nonfocal_policy_aligned is True
    assert built.evidence.release_observed is True
    assert built.evidence.forecast_hold_r2_margin > 0.0
    assert built.evidence.candidate_energy_j < built.evidence.reference_energy_j
    assert tuple(step.offset for step in prepared.reference_trace) == (0, 1, 2, 3)
    assert tuple(step.offset for step in prepared.candidate_trace) == (0, 1, 2, 3)
    assert prepared.candidate_trace[3].executed_actions == prepared.candidate_trace[3].detached_main_actions
    assert prepared.candidate_trace[3].executed_physical_actions == prepared.candidate_trace[3].detached_main_physical_actions
    assert prepared.candidate_trace[0].executed_physical_actions[0] == (1, 3)
    assert service._anchor_payload["main_policy_contract"] == {
        "main_policy_version": backend.MAIN_POLICY_VERSION,
        "compositor_version": backend.POLICY_COMPOSITOR_VERSION,
        "checkpoint_sha256": CHECKPOINT,
        "objective_weights": (0.5, 0.3, 0.2),
    }
    assert trainer.inference_calls == 9  # one opening Main + 4 reference + 4 candidate decisions

    live_step, receipt = prepared.run_live_step()
    assert prepared.phase == "closed"
    assert live_step.action_indices == (3, 11)
    assert live_step.physical_actions == ((1, 3), (2, 11))
    assert receipt.live_rng_unchanged_during_forecast is True
    assert receipt.forecast_sequence[-2:] == ("live_step_started", "live_step_completed")
    assert wrapped._offset == initial_offset + 1
    with pytest.raises(Exception):
        prepared.run_live_step()


def test_detached_branch_preserves_current_predecision_candidate_identity():
    """A detached observation must point at its detached environment candidates."""

    wrapped = _Wrapped()
    wrapped.environment._candidates = wrapped._observation.candidates
    service = _construct_backend(wrapped, _Trainer())
    prepared = service.prepare_incumbent_hold(focal_user=0)

    branch = backend._branch_from_anchor(
        prepared.anchor,
        role="identity-regression",
        env_rng=np.random.default_rng(29),
        mobility_rng=np.random.default_rng(31),
    )

    assert branch.observation.candidates is branch.wrapped.environment._candidates
    assert branch.observation.candidates is not wrapped.environment._candidates


def test_candidate_latches_first_support_expiry_and_never_reacquires():
    wrapped = _SupportExpiringWrapped()
    service = _construct_backend(wrapped, _Trainer())
    prepared = service.prepare_incumbent_hold(focal_user=0)

    built = prepared.run_forecast()

    assert built.certificate.passed is True
    assert built.certificate.release_offset == 1
    assert built.certificate.release_reason == "support_expired"
    candidate = prepared.candidate_trace
    assert tuple(step.held_key_match_count for step in candidate) == (1, 0, 0, 0)
    assert candidate[0].executed_physical_actions[0] == (1, 3)
    assert tuple(step.executed_physical_actions[0] for step in candidate[1:]) == (
        (1, 11),
        (1, 11),
        (1, 11),
    )
    assert all(step.release_offset == 1 for step in candidate)
    assert all(step.release_reason == "support_expired" for step in candidate)


def test_keyed_forecast_twins_share_one_immutable_field_and_receipt(monkeypatch):
    captured: list[KeyedFadingField | None] = []
    original = backend._copy_detached_environment

    def capture_copy(wrapped, *, fading_field=None):
        clone = original(wrapped, fading_field=fading_field)
        captured.append(clone.environment._fading_field)
        return clone

    monkeypatch.setattr(backend, "_copy_detached_environment", capture_copy)
    service, wrapped, _trainer = _backend(
        forecast_fading_mode=KEYED_FADING_VERSION
    )
    prepared = service.prepare_incumbent_hold(focal_user=0)

    built = prepared.run_forecast()

    assert len(captured) == 2
    assert isinstance(captured[0], KeyedFadingField)
    assert captured[0] is captured[1]
    assert captured[0].version == KEYED_FADING_VERSION
    assert built.authority.fading_mode == KEYED_FADING_VERSION
    assert prepared.forecast_rng_state["fading_mode"] == KEYED_FADING_VERSION
    assert (
        prepared.forecast_rng_state["fading_field_receipt"]
        == captured[0].receipt()
    )
    assert wrapped.environment.physics.fading_enabled is True
    assert not hasattr(wrapped.environment, "_fading_field")


def test_disabled_forecast_remains_the_default_and_has_no_field_receipt(monkeypatch):
    captured: list[tuple[bool, KeyedFadingField | None]] = []
    original = backend._copy_detached_environment

    def capture_copy(wrapped, *, fading_field=None):
        clone = original(wrapped, fading_field=fading_field)
        captured.append(
            (
                bool(clone.environment.physics.fading_enabled),
                clone.environment._fading_field,
            )
        )
        return clone

    monkeypatch.setattr(backend, "_copy_detached_environment", capture_copy)
    service, _wrapped, _trainer = _backend()
    prepared = service.prepare_incumbent_hold(focal_user=0)

    built = prepared.run_forecast()

    assert captured == [(False, None), (False, None)]
    assert built.authority.fading_mode == "disabled"
    assert prepared.forecast_rng_state["fading_mode"] == "disabled"
    assert prepared.forecast_rng_state["fading_field_receipt"] is None


def test_explicit_legal_non_incumbent_candidate_is_supported():
    service, _wrapped, _trainer = _backend()
    prepared = service.prepare_one_candidate(focal_user=0, candidate_key=(1, 3))
    assert prepared.candidate_key == (1, 3)
    assert prepared.source_rule == "explicit-preoutcome-candidate"


def test_hold_or_rival_falls_back_to_max_lagged_candidate_sinr():
    wrapped = _Wrapped()
    wrapped._tables = (
        _Table({2: (1, 2), 5: (1, 5), 11: (1, 11)}),
        wrapped._tables[1],
    )
    wrapped._observation = _Observation(
        0,
        np.asarray(((0, 1, 2, 3), (4, 5, 6, 7)), dtype=np.float32),
        wrapped._tables,
    )
    wrapped._observation.candidate_sinr[0, 2] = 7.0
    wrapped._observation.candidate_sinr[0, 5] = 9.0
    service = _construct_backend(wrapped, _Trainer(), focal_user=0)

    prepared = service.prepare_hold_or_max_lagged_gain_rival(focal_user=0)

    assert prepared.candidate_key == (1, 5)
    assert prepared.source_rule == "max-lagged-candidate-sinr-rival"


def test_lagged_rival_tie_breaks_by_physical_id():
    wrapped = _Wrapped()
    wrapped._tables = (
        _Table({2: (9, 2), 5: (3, 5), 11: (1, 11)}),
        wrapped._tables[1],
    )
    wrapped._observation = _Observation(
        0,
        np.asarray(((0, 1, 2, 3), (4, 5, 6, 7)), dtype=np.float32),
        wrapped._tables,
    )
    wrapped._observation.candidate_sinr[0, 2] = 9.0
    wrapped._observation.candidate_sinr[0, 5] = 9.0
    service = _construct_backend(wrapped, _Trainer(), focal_user=0)

    prepared = service.prepare_hold_or_max_lagged_gain_rival(focal_user=0)

    assert prepared.candidate_key == (3, 5)


def test_anchor_payload_binds_the_requested_nonzero_focal_user():
    wrapped = _Wrapped()
    trainer = _Trainer()

    service = _construct_backend(wrapped, trainer, focal_user=1)

    assert service._anchor_payload["focal_user"] == 1
    with pytest.raises(backend.C2BackendError, match="must equal the focal authority"):
        service.prepare_incumbent_hold(focal_user=0)


def test_stale_live_states_are_rejected_at_construction():
    wrapped = _Wrapped()
    trainer = _Trainer()
    stale = list(wrapped._observation.user_states)
    stale[0] = np.array(stale[0], copy=True)
    stale[0][0] += 1.0

    with pytest.raises(backend.C2BackendError, match="encoded live states disagree"):
        _construct_backend(wrapped, trainer, states=stale)


def test_stale_live_masks_are_rejected_at_construction():
    wrapped = _Wrapped()
    trainer = _Trainer()
    stale = [SimpleNamespace(mask=np.array(table.mask, copy=True)) for table in wrapped._tables]
    stale[0].mask[3] = False

    with pytest.raises(backend.C2BackendError, match="supplied live masks disagree"):
        _construct_backend(wrapped, trainer, masks=stale)


def test_candidate_local_nonfocal_main_divergence_is_policy_aligned(monkeypatch):
    service, _wrapped, _trainer = _backend()
    prepared = service.prepare_incumbent_hold(focal_user=0)
    original = backend._main_actions
    calls = {"candidate": 0}

    def divergent_main(trainer, branch):
        actions, physical = original(trainer, branch)
        if branch.role == "candidate":
            calls["candidate"] += 1
            if calls["candidate"] == 2:
                actions = actions.copy()
                actions[1] = 2
                physical = backend._physical_vector(actions.tolist(), branch.observation, users=2)
        return actions, physical

    monkeypatch.setattr(backend, "_main_actions", divergent_main)
    built = prepared.run_forecast()
    assert built.certificate.passed
    assert built.evidence.nonfocal_policy_aligned
    assert prepared.candidate_trace[1].executed_actions[1] == 2
    assert prepared.candidate_trace[1].executed_actions[1] == (
        prepared.candidate_trace[1].detached_main_actions[1]
    )
    assert prepared.candidate_trace[1].executed_physical_actions[1] == (2, 2)
    assert prepared.reference_trace[1].executed_physical_actions[1] == (2, 11)
    assert prepared.phase == "forecast_complete"


def test_shared_compositor_preserves_candidate_local_nonfocal_main():
    tables = (
        _Table({3: (1, 3), 11: (1, 11)}),
        _Table({2: (2, 2)}),
    )
    observation = _Observation(
        2,
        np.asarray(((0, 1, 2, 3), (4, 5, 6, 7)), dtype=np.float32),
        tables,
    )
    actions, physical = backend._compose_candidate_actions(
        observation=observation,
        main_actions=np.asarray((11, 2), dtype=np.int32),
        main_physical=((1, 11), (2, 2)),
        candidate_key=(1, 3),
        focal_user=0,
        offset=2,
    )

    assert tuple(actions.tolist()) == (3, 2)
    assert physical == ((1, 3), (2, 2))


def test_focal_hold_remap_failure_reports_offset_user_and_candidate_key():
    table = _Table({11: (1, 11)})

    with pytest.raises(
        backend.C2ForecastSupportRejection,
        match=r"offset=1, user=7, physical_key=\(1, 3\)",
    ) as raised:
        backend._map_candidate_focal_hold(
            table,
            (1, 3),
            focal_user=7,
            offset=1,
        )
    assert raised.value.reason == "focal_hold_expired"
    assert raised.value.forecast_offset == 1
    assert raised.value.user == 7
    assert raised.value.physical_key == (1, 3)


def test_opening_incumbent_unavailable_is_a_support_rejection():
    wrapped = _Wrapped()
    wrapped._tables = (
        _Table({11: (1, 11)}),
        wrapped._tables[1],
    )
    wrapped._observation = _Observation(
        0,
        np.asarray(((0, 1, 2, 3), (4, 5, 6, 7)), dtype=np.float32),
        wrapped._tables,
    )
    service = _construct_backend(wrapped, _Trainer(), focal_user=0)

    with pytest.raises(
        backend.C2ForecastSupportRejection,
        match=r"offset=0, user=0, physical_key=\(1, 3\)",
    ) as raised:
        service.prepare_incumbent_hold(focal_user=0)

    assert raised.value.reason == "opening_incumbent_unavailable"
    assert raised.value.forecast_offset == 0
    assert raised.value.user == 0
    assert raised.value.physical_key == (1, 3)


def test_live_branch_returns_real_early_terminal_but_forecast_fails_closed():
    wrapped = _TerminalWrapped()
    trainer = _Trainer()
    states = list(wrapped._observation.user_states)
    masks = [
        SimpleNamespace(mask=np.array(table.mask, copy=True))
        for table in wrapped._tables
    ]
    branch = backend.C2ForecastBranch(
        wrapped=wrapped,
        env_rng=np.random.default_rng(31),
        mobility_rng=np.random.default_rng(32),
        states=states,
        masks=masks,
        observation=wrapped._observation,
        trainer=trainer,
        focal_user=0,
        role="live-option-commit",
        offset=1,
    )
    payload = backend._step_payload(
        branch,
        offset=1,
        detached_main_actions=(11, 11),
        detached_main_physical=((1, 11), (2, 11)),
        executed_actions=(3, 11),
    )
    assert payload.done is True
    assert branch.offset == 2

    forecast_wrapped = _TerminalWrapped()
    forecast_branch = backend.C2ForecastBranch(
        wrapped=forecast_wrapped,
        env_rng=np.random.default_rng(33),
        mobility_rng=np.random.default_rng(34),
        states=list(forecast_wrapped._observation.user_states),
        masks=[
            SimpleNamespace(mask=np.array(table.mask, copy=True))
            for table in forecast_wrapped._tables
        ],
        observation=forecast_wrapped._observation,
        trainer=trainer,
        focal_user=0,
        role="candidate",
        offset=1,
    )
    with pytest.raises(backend.C2BackendError, match="terminated before release"):
        backend._step_payload(
            forecast_branch,
            offset=1,
            detached_main_actions=(11, 11),
            detached_main_physical=((1, 11), (2, 11)),
            executed_actions=(3, 11),
        )
