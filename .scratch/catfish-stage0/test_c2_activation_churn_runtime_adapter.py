"""Deterministic integration fixtures for the read-only C2 V3 runtime seams."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("c2_activation_churn_runtime_adapter.py")
spec = importlib.util.spec_from_file_location(
    "c2_activation_churn_runtime_adapter", MODULE_PATH
)
adapter = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


class _FakeTrainer:
    def __init__(self, weights=adapter.OBJECTIVE_WEIGHTS, q_values=None):
        self.config = SimpleNamespace(objective_weights=weights)
        self.q_values = np.asarray(
            [[1.0, 4.0], [3.0, 2.0]] if q_values is None else q_values,
            dtype=np.float64,
        )
        self.encode_calls = 0
        self.scalar_calls = []

    def encode_states(self, states):
        self.encode_calls += 1
        return np.zeros((len(states), 4), dtype=np.float32)

    def scalarized_q_values(self, encoded, *, objective_weights):
        assert encoded.shape[0] == self.q_values.shape[0]
        self.scalar_calls.append(tuple(objective_weights))
        return self.q_values.copy()


def test_scalarized_main_fixture_differs_from_q1_only_and_receipts_exact_surface():
    trainer = _FakeTrainer()
    decision = adapter.scalarized_main_decision(
        trainer,
        [object(), object()],
        np.asarray([[True, True], [True, False]], dtype=bool),
    )
    assert decision.actions == (1, 0)
    assert decision.objective_weights == (0.5, 0.3, 0.2)
    assert decision.q_values == ((1.0, 4.0), (3.0, 2.0))
    assert decision.masks == ((True, True), (True, False))
    assert trainer.scalar_calls == [(0.5, 0.3, 0.2)]


def test_weight_drift_fails_before_encoding_or_inference():
    trainer = _FakeTrainer(weights=(1.0, 0.0, 0.0))
    with pytest.raises(RuntimeError, match="weights drifted"):
        adapter.scalarized_main_decision(
            trainer,
            [object()],
            np.asarray([[True, True]], dtype=bool),
        )
    assert trainer.encode_calls == 0
    assert trainer.scalar_calls == []

    malformed = _FakeTrainer(weights=("0.5", "0.3", "0.2"))
    with pytest.raises(RuntimeError, match="numeric"):
        adapter.scalarized_main_decision(
            malformed,
            [object()],
            np.asarray([[True, True]], dtype=bool),
        )


@pytest.mark.parametrize(
    "q_values",
    [
        [[1.0, float("nan")], [3.0, 2.0]],
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
    ],
)
def test_nonfinite_or_shape_drifted_scalarized_tables_fail_closed(q_values):
    with pytest.raises(ValueError, match="finite|share shape"):
        adapter.scalarized_main_decision(
            _FakeTrainer(q_values=q_values),
            [object(), object()],
            np.asarray([[True, True], [True, True]], dtype=bool),
        )


def _evaluation(*, system_delta=0.0, active_beams=None):
    from mcrl.env.link_budget import (
        fixed_power_w,
        pa_efficiency,
        supply_power_w,
        system_power_w,
    )

    beam_power = np.asarray([0.5, 0.7], dtype=np.float64)
    efficiency = pa_efficiency(beam_power)
    supply = supply_power_w(beam_power, efficiency)
    counts = np.asarray([2.0])
    fixed = fixed_power_w(counts)
    total = system_power_w(supply, counts) + system_delta
    return SimpleNamespace(
        radiating=SimpleNamespace(
            norad_ids=np.asarray([100, 100], dtype=np.int64),
            cell_ids=np.asarray([1, 2], dtype=np.int64),
            power_w=beam_power,
        ),
        resolution=SimpleNamespace(
            active_beams=(
                ((100, 1), (100, 2)) if active_beams is None else active_beams
            ),
            served=np.asarray([True, True, True], dtype=bool),
            serving_satellite=np.asarray([100, 100, 100], dtype=np.int64),
            serving_cell=np.asarray([1, 1, 2], dtype=np.int64),
        ),
        link_power_w=np.asarray([0.5, 0.4, 0.7], dtype=np.float64),
        fixed_power_w=fixed,
        system_power_w=total,
    )


def test_power_projection_uses_canonical_pa_functions_and_complete_system_identity():
    from mcrl.env.link_budget import PA_MAX_EFFICIENCY, PA_SATURATION_POWER_W

    projected = adapter.canonical_power_projection(
        _evaluation(),
        pa_max_efficiency=PA_MAX_EFFICIENCY,
        pa_saturation_power_w=PA_SATURATION_POWER_W,
    )
    assert projected.identity.passed
    assert projected.terms.beams[0].recurrence_outputs_w == (0.5, 0.4)
    assert projected.terms.beams[0].reported_beam_max_w == 0.5
    assert projected.terms.beams[1].recurrence_outputs_w == (0.7,)
    assert projected.terms.active_beam_counts_by_satellite == {100: 2}


def test_power_projection_rejects_superseded_or_drifted_total():
    from mcrl.env.link_budget import PA_MAX_EFFICIENCY, PA_SATURATION_POWER_W

    with pytest.raises(RuntimeError, match="system_power_mismatch"):
        adapter.canonical_power_projection(
            _evaluation(system_delta=1.0),
            pa_max_efficiency=PA_MAX_EFFICIENCY,
            pa_saturation_power_w=PA_SATURATION_POWER_W,
        )


def test_power_projection_rejects_active_set_or_link_max_mismatch():
    from mcrl.env.link_budget import PA_MAX_EFFICIENCY, PA_SATURATION_POWER_W

    with pytest.raises(ValueError, match="active-beam"):
        adapter.canonical_power_projection(
            _evaluation(active_beams=((100, 1),)),
            pa_max_efficiency=PA_MAX_EFFICIENCY,
            pa_saturation_power_w=PA_SATURATION_POWER_W,
        )

    malformed = _evaluation()
    malformed.link_power_w[0] = 0.4
    with pytest.raises(RuntimeError, match="beam_max_mismatch"):
        adapter.canonical_power_projection(
            malformed,
            pa_max_efficiency=PA_MAX_EFFICIENCY,
            pa_saturation_power_w=PA_SATURATION_POWER_W,
        )


def test_power_projection_rejects_coerced_service_or_identity_types():
    from mcrl.env.link_budget import PA_MAX_EFFICIENCY, PA_SATURATION_POWER_W

    malformed = _evaluation()
    malformed.resolution.served = np.asarray([1, 1, 1], dtype=np.int64)
    with pytest.raises(ValueError, match="Boolean"):
        adapter.canonical_power_projection(
            malformed,
            pa_max_efficiency=PA_MAX_EFFICIENCY,
            pa_saturation_power_w=PA_SATURATION_POWER_W,
        )
