"""Focused tests for the real-environment C3 H3 backend boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "c3_h3_trainer_backend.py"
SPEC = importlib.util.spec_from_file_location("c3_h3_trainer_backend", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
B = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = B
SPEC.loader.exec_module(B)


def _trainer(weights=(0.5, 0.3, 0.2)):
    return SimpleNamespace(config=SimpleNamespace(objective_weights=weights))


def _anchor(*, step: int = 1, actions: tuple[tuple[int, ...], ...] | None = None):
    if actions is None:
        actions = (tuple([0] * 100),) if step == 1 else ()
    return B.h3.PreOutcomeAnchor(
        checkpoint_sha256=B.legacy.EXPECTED_CHECKPOINT_SHA256,
        expected_anchor_fingerprint_sha256="c" * 64,
        evaluation_seed=17,
        step_index=step,
        focal_user_id=9,
        source_id=(8, 1),
        prefix_actions=actions,
    )


def test_backend_requires_the_corrected_checkpoint_weights():
    B.TrainerEnvironmentH3Backend(object(), _trainer())
    with pytest.raises(ValueError, match="frozen to the legacy 100-user"):
        B.TrainerEnvironmentH3Backend(object(), _trainer(), expected_user_count=99)
    with pytest.raises(ValueError, match="objective weights drifted"):
        B.TrainerEnvironmentH3Backend(object(), _trainer((1.0, 0.0, 0.0)))
    with pytest.raises(ValueError, match="requires corrected Main checkpoint"):
        B.TrainerEnvironmentH3Backend(
            object(), _trainer(), objective_weights=(1.0, 0.0, 0.0)
        )


def test_replay_prefix_binds_exact_focal_user_and_independent_fingerprint(monkeypatch):
    observed = {}

    def fake_reconstruct(archive, *, seed, prefix_actions):
        observed.update(archive=archive, seed=seed, prefix_actions=prefix_actions)
        return {
            "wrapped": object(),
            "env_rng": np.random.default_rng(3),
            "states": [object()] * 100,
            "masks": [object()] * 100,
            "observation": SimpleNamespace(step_index=1),
            "fingerprint_sha256": "c" * 64,
        }

    monkeypatch.setattr(B.legacy, "_reconstruct_anchor", fake_reconstruct)
    archive = object()
    backend = B.TrainerEnvironmentH3Backend(archive, _trainer())
    branch = backend.replay_prefix(_anchor())

    assert observed["archive"] is archive
    assert observed["seed"] == 17
    assert len(observed["prefix_actions"]) == 1
    assert observed["prefix_actions"][0].dtype == np.int32
    assert branch.focal_user_id == 9
    assert backend.fingerprint(branch) == "c" * 64


def test_replay_prefix_rejects_incomplete_or_misaligned_action_history():
    backend = B.TrainerEnvironmentH3Backend(object(), _trainer())
    with pytest.raises(RuntimeError, match="prefix length"):
        backend.replay_prefix(_anchor(step=2, actions=(tuple([0] * 100),)))
    with pytest.raises(RuntimeError, match="every user"):
        backend.replay_prefix(_anchor(actions=((1, 2, 3),)))


def test_replay_prefix_rejects_anchors_outside_the_three_interval_window():
    backend = B.TrainerEnvironmentH3Backend(object(), _trainer())
    with pytest.raises(RuntimeError, match="outside the three-interval"):
        backend.replay_prefix(_anchor(step=8))


def test_replay_prefix_rejects_out_of_range_actions_before_int32_cast():
    backend = B.TrainerEnvironmentH3Backend(object(), _trainer())
    invalid = tuple([B.NUM_ACTIONS] + [0] * 99)
    with pytest.raises(RuntimeError, match="out of range"):
        backend.replay_prefix(_anchor(actions=(invalid,)))


def test_main_actions_uses_deployed_scalarized_weights_and_masks():
    observed = {}

    class FakeTrainer:
        config = SimpleNamespace(objective_weights=(0.5, 0.3, 0.2))

        def encode_states(self, states):
            observed["states"] = states
            return np.zeros((100, 2), dtype=np.float32)

        def scalarized_q_values(self, encoded, *, objective_weights):
            observed["encoded_shape"] = encoded.shape
            observed["weights"] = objective_weights
            q_values = np.zeros((100, B.NUM_ACTIONS), dtype=np.float64)
            q_values[:, 2] = 2.0
            q_values[:, 3] = 1.0
            return q_values

    mask = np.zeros(B.NUM_ACTIONS, dtype=bool)
    mask[:3] = True
    masks = [SimpleNamespace(mask=mask.copy()) for _ in range(100)]
    branch = B.TrainerH3Branch(
        wrapped=object(),
        env_rng=np.random.default_rng(1),
        states=[object()] * 100,
        masks=masks,
        observation=object(),
        fingerprint_sha256="c" * 64,
        focal_user_id=0,
    )
    actions = B.TrainerEnvironmentH3Backend(object(), FakeTrainer())._main_actions(
        branch
    )

    assert actions.shape == (100,)
    assert np.all(actions == 2)
    assert observed["encoded_shape"] == (100, 2)
    assert observed["weights"] == B.DEFAULT_OBJECTIVE_WEIGHTS
    assert B.MAIN_BEHAVIOR_WEIGHTS == B.DEFAULT_OBJECTIVE_WEIGHTS


def test_roll_forward_rejects_an_early_terminal_forecast(monkeypatch):
    class Physics:
        fading_enabled = True

    class Wrapped:
        def __init__(self):
            self.environment = SimpleNamespace(
                _mobility_rng=np.random.default_rng(4), physics=Physics()
            )
            self.environment.evaluate_actions = self.evaluate_actions

        def evaluate_actions(self, actions, rng):
            return object()

        def step(self, actions, rng):
            return SimpleNamespace(done=True)

    observation = SimpleNamespace(
        candidates=SimpleNamespace(slot_tables=[object()] * 100)
    )
    branch = B.TrainerH3Branch(
        wrapped=Wrapped(),
        env_rng=np.random.default_rng(2),
        states=[object()] * 100,
        masks=[object()] * 100,
        observation=observation,
        fingerprint_sha256="c" * 64,
        focal_user_id=0,
    )
    backend = B.TrainerEnvironmentH3Backend(object(), _trainer())
    monkeypatch.setattr(
        backend,
        "_main_actions",
        lambda _branch: np.zeros(100, dtype=np.int32),
    )
    monkeypatch.setattr(B.legacy, "_action_for_key", lambda _table, _key: 0)
    monkeypatch.setattr(
        B.legacy, "_physical_key_rows", lambda _actions, _observation: (None,) * 100
    )
    monkeypatch.setattr(
        B,
        "replace",
        lambda _physics, **kwargs: SimpleNamespace(fading_enabled=kwargs["fading_enabled"]),
    )

    with pytest.raises(RuntimeError, match="episode end before three intervals"):
        backend.roll_forward(
            branch,
            (8, 1),
            0,
            np.random.default_rng(3),
        )


def test_roll_forward_rejects_a_forecast_rng_that_reuses_mobility_state():
    actual = np.random.default_rng(4)
    branch = B.TrainerH3Branch(
        wrapped=SimpleNamespace(
            environment=SimpleNamespace(
                _mobility_rng=actual,
                physics=SimpleNamespace(fading_enabled=True),
            )
        ),
        env_rng=np.random.default_rng(5),
        states=(),
        masks=(),
        observation=object(),
        fingerprint_sha256="c" * 64,
        focal_user_id=0,
    )
    backend = B.TrainerEnvironmentH3Backend(object(), _trainer())
    with pytest.raises(RuntimeError, match="object/state-independent"):
        backend.roll_forward(branch, (8, 1), 0, np.random.default_rng(4))


def test_power_snapshot_recomputes_from_per_beam_supply_not_reported_total():
    physics = SimpleNamespace(pa_max_efficiency=0.35, pa_saturation_power_w=2.0)
    radiated = np.asarray([0.5, 1.0, 1.5], dtype=np.float64)
    efficiency = B.pa_efficiency(
        radiated,
        max_efficiency=physics.pa_max_efficiency,
        saturation_power_w=physics.pa_saturation_power_w,
    )
    supply = B.supply_power_w(radiated, efficiency)
    fixed = 3 * B.h3.core.CIRCUIT_POWER_PER_BEAM_W + 2 * B.h3.core.BASEBAND_POWER_PER_SATELLITE_W
    total = fixed + float(np.sum(supply))
    outcome = SimpleNamespace(
        radiating=SimpleNamespace(
            power_w=radiated,
            norad_ids=np.asarray([8, 8, 9]),
            cell_ids=np.asarray([1, 2, 1]),
        ),
        fixed_power_w=fixed,
        system_power_w=total,
    )

    snapshot = B._power_snapshot(outcome, physics)
    assert B.h3.core.validate_power_snapshot(snapshot) == ()
    assert snapshot.radiating_beams_by_satellite == {8: 2, 9: 1}
    assert snapshot.pa_identity_residual_w == pytest.approx(0.0, abs=1e-12)


def test_power_snapshot_exposes_a_reported_total_mismatch_to_the_core():
    physics = SimpleNamespace(pa_max_efficiency=0.35, pa_saturation_power_w=2.0)
    outcome = SimpleNamespace(
        radiating=SimpleNamespace(
            power_w=np.asarray([1.0]),
            norad_ids=np.asarray([8]),
            cell_ids=np.asarray([1]),
        ),
        fixed_power_w=B.h3.core.CIRCUIT_POWER_PER_BEAM_W
        + B.h3.core.BASEBAND_POWER_PER_SATELLITE_W,
        system_power_w=999.0,
    )
    reasons = B.h3.core.validate_power_snapshot(B._power_snapshot(outcome, physics))
    assert "reported_system_power_mismatch" in reasons
    assert "pa_identity_failed" in reasons
