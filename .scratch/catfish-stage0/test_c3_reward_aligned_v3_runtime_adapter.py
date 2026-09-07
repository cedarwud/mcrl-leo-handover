"""Focused fixtures for the read-only C3 V3 canonical-runtime seams."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("c3_reward_aligned_v3_runtime_adapter.py")
spec = importlib.util.spec_from_file_location(
    "c3_reward_aligned_v3_runtime_adapter", MODULE_PATH
)
adapter = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)
c3 = adapter.core


SOURCE = (100, 1)
DESTINATION = (100, 2)


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


def test_scalarized_main_receipts_q_table_masks_table_actions_and_physical_ids():
    from mcrl.env.action_contract import SlotTable

    trainer = _FakeTrainer()
    tables = []
    for _ in range(2):
        norads = np.full(28, -1, dtype=np.int64)
        cells = np.full(28, -1, dtype=np.int64)
        table_mask = np.zeros(28, dtype=bool)
        norads[:2] = 100
        cells[:2] = [1, 2]
        table_mask[:2] = True
        tables.append(SlotTable(norads, cells, table_mask))
    decision = adapter.scalarized_main_decision(
        trainer,
        [object(), object()],
        np.asarray([[True, True], [True, False]], dtype=bool),
        slot_tables=tables,
    )
    assert decision.actions == (1, 0)
    assert decision.table_actions == (1, 0)
    assert decision.physical_actions == ((100, 2), (100, 1))
    assert decision.physical_ids == decision.physical_actions
    assert decision.objective_weights == (0.5, 0.3, 0.2)
    assert decision.q_values == ((1.0, 4.0), (3.0, 2.0))
    assert decision.masks == ((True, True), (True, False))
    assert trainer.scalar_calls == [(0.5, 0.3, 0.2)]


def test_weight_drift_fails_before_encoding_or_inference():
    trainer = _FakeTrainer(weights=(1.0, 0.0, 0.0))
    with pytest.raises(RuntimeError, match="weights drifted"):
        adapter.scalarized_main_decision(
            trainer, [object()], np.asarray([[True, True]], dtype=bool)
        )
    assert trainer.encode_calls == 0
    assert trainer.scalar_calls == []

    malformed = _FakeTrainer(weights=("0.5", "0.3", "0.2"))
    with pytest.raises(RuntimeError, match="numeric"):
        adapter.scalarized_main_decision(
            malformed, [object()], np.asarray([[True, True]], dtype=bool)
        )
    assert malformed.encode_calls == 0


def test_scalarized_main_rejects_nonboolean_mask_rows_and_nonfinite_q():
    trainer = _FakeTrainer()
    with pytest.raises(ValueError, match="Boolean"):
        adapter.scalarized_main_decision(trainer, [object()], [[1, 0]])
    with pytest.raises(ValueError, match="finite"):
        adapter.scalarized_main_decision(
            _FakeTrainer(q_values=[[1.0, float("nan")], [3.0, 2.0]]),
            [object(), object()],
            np.asarray([[True, True], [True, True]], dtype=bool),
        )


def _evaluation(*, system_delta=0.0, active_beams=None, reward_matrix=None):
    from mcrl.env.link_budget import fixed_power_w, system_power_w

    beam_power = np.asarray([0.5, 0.7], dtype=np.float64)
    efficiency = adapter.pa_efficiency(beam_power)
    supply = adapter.supply_power_w(beam_power, efficiency)
    counts = np.asarray([2.0])
    fixed = fixed_power_w(counts)
    total = system_power_w(supply, counts) + system_delta
    resolution = SimpleNamespace(
        served=np.asarray([True, True, False], dtype=bool),
        serving_satellite=np.asarray([100, 100, -1], dtype=np.int64),
        serving_cell=np.asarray([1, 2, -1], dtype=np.int64),
        eligible_load_by_beam={SOURCE: 1, DESTINATION: 1},
        active_beams=(SOURCE, DESTINATION) if active_beams is None else active_beams,
    )
    return SimpleNamespace(
        radiating=SimpleNamespace(
            norad_ids=np.asarray([100, 100], dtype=np.int64),
            cell_ids=np.asarray([1, 2], dtype=np.int64),
            power_w=beam_power,
        ),
        resolution=resolution,
        link_power_w=np.asarray([0.5, 0.7, 0.0], dtype=np.float64),
        fixed_power_w=fixed,
        system_power_w=total,
        reward_matrix=(
            np.asarray(
                [[1.0, 0.0, -1.0], [2.0, 0.0, -1.0], [0.0, 0.0, 0.0]]
            )
            if reward_matrix is None
            else reward_matrix
        ),
    )


def test_power_projection_uses_canonical_pa_chain_and_complete_identity():
    projected = adapter.canonical_power_projection(_evaluation())
    assert projected.identity.passed
    assert projected.terms.beams[0].recurrence_outputs_w == (0.5,)
    assert projected.terms.beams[1].recurrence_outputs_w == (0.7,)
    assert projected.terms.active_beam_counts_by_satellite == {100: 2}


def test_power_projection_rejects_total_active_set_and_link_max_drift():
    with pytest.raises(RuntimeError, match="system_power_mismatch"):
        adapter.canonical_power_projection(_evaluation(system_delta=1.0))
    with pytest.raises(ValueError, match="active-beam"):
        adapter.canonical_power_projection(_evaluation(active_beams=(SOURCE,)))
    malformed = _evaluation()
    malformed.link_power_w[0] = 0.4
    with pytest.raises(RuntimeError, match="beam_max_mismatch"):
        adapter.canonical_power_projection(malformed)


def test_power_projection_rejects_unserved_nonzero_link_and_ids():
    malformed = _evaluation()
    malformed.link_power_w[2] = 0.1
    with pytest.raises(ValueError, match="zero link power"):
        adapter.canonical_power_projection(malformed)
    malformed = _evaluation()
    malformed.resolution.serving_cell[2] = 3
    with pytest.raises(ValueError, match="serving IDs"):
        adapter.canonical_power_projection(malformed)


def test_load_projection_receipts_unmodified_r3_column_and_unserved_zero():
    projected = adapter.canonical_load_projection(_evaluation())
    assert projected.identity.passed
    assert projected.snapshot.served_associations == (SOURCE, DESTINATION, None)
    assert projected.snapshot.reported_eligible_loads == {SOURCE: 1, DESTINATION: 1}
    assert projected.snapshot.reported_active_beams == frozenset({SOURCE, DESTINATION})
    assert projected.reward_column == (-1.0, -1.0, 0.0)
    assert projected.identity.canonical_r3_total == -2.0
    assert projected.identity.squared_load_total == 2


def test_load_projection_rejects_reward_rewrite_and_load_or_active_set_drift():
    wrong_reward = _evaluation(
        reward_matrix=np.asarray(
            [[1.0, 0.0, -2.0], [2.0, 0.0, -1.0], [0.0, 0.0, 0.0]]
        )
    )
    with pytest.raises(RuntimeError, match="canonical_r3_per_user_mismatch"):
        adapter.canonical_load_projection(wrong_reward)
    wrong_load = _evaluation()
    wrong_load.resolution.eligible_load_by_beam = {SOURCE: 2}
    with pytest.raises(RuntimeError, match="eligible_load_reconstruction_mismatch"):
        adapter.canonical_load_projection(wrong_load)
    wrong_active = _evaluation(active_beams=(SOURCE,))
    with pytest.raises(RuntimeError, match="positive_load_active_beam_mismatch"):
        adapter.canonical_load_projection(wrong_active)


@pytest.mark.parametrize("field", ["served", "serving_satellite", "serving_cell"])
def test_load_projection_rejects_resolution_shape_or_type_drift(field):
    malformed = _evaluation()
    if field == "served":
        malformed.resolution.served = np.asarray([1, 1, 0], dtype=np.int64)
    elif field == "serving_satellite":
        malformed.resolution.serving_satellite = np.asarray([100, 100], dtype=np.int64)
    else:
        malformed.resolution.serving_cell = np.asarray([1, 2, -1, -1], dtype=np.int64)
    with pytest.raises(ValueError, match="Boolean|shape"):
        adapter.canonical_load_projection(malformed)


def test_load_projection_rejects_non_three_column_or_object_reward_matrix():
    with pytest.raises(ValueError, match="shape"):
        adapter.canonical_load_projection(
            _evaluation(reward_matrix=np.zeros((3, 2), dtype=np.float64))
        )
    with pytest.raises(ValueError, match="numeric"):
        adapter.canonical_load_projection(
            _evaluation(
                reward_matrix=np.asarray(
                    [["1", "0", "-1"], ["2", "0", "-1"], ["0", "0", "0"]],
                    dtype=object,
                )
            )
        )
