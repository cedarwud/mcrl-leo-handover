"""W-32 — objective-head pivotality helpers."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.runtime.head_pivotality import (
    masked_greedy_actions,
    physical_action_keys,
    pivotality_counts,
    weights_without_head,
)


def _slot_table(pairs: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=bool)
    for action, (norad, cell) in pairs.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norad_ids=norads, cell_ids=cells, mask=mask)


def test_weights_without_head_preserve_the_other_tradeoff():
    weights = (0.5, 0.3, 0.2)
    assert weights_without_head(weights, 1) == pytest.approx((5 / 7, 0.0, 2 / 7))
    assert weights_without_head(weights, 2) == pytest.approx((5 / 8, 3 / 8, 0.0))


def test_masked_greedy_uses_no_op_only_for_an_empty_mask():
    values = np.zeros((2, NUM_ACTIONS), dtype=np.float64)
    values[0, 2] = 3.0
    masks = np.zeros((2, NUM_ACTIONS), dtype=bool)
    masks[0, [1, 2]] = True
    assert masked_greedy_actions(values, masks).tolist() == [2, -1]


def test_pivotality_is_counted_in_physical_associations_not_only_indices():
    tables = (
        _slot_table({0: (10, 7), 1: (10, 7)}),
        _slot_table({0: (20, 8), 2: (21, 8)}),
    )
    full = np.asarray([0, 0], dtype=np.int64)
    ablated = np.asarray([1, 2], dtype=np.int64)
    full_keys = physical_action_keys(full, tables)
    ablated_keys = physical_action_keys(ablated, tables)

    assert full_keys == ((10, 7), (20, 8))
    assert ablated_keys == ((10, 7), (21, 8))
    assert pivotality_counts(full, ablated, tables) == {
        "action_index_flips": 2,
        "physical_action_flips": 1,
        "index_only_flips": 1,
        "physical_flip_user_ids": [1],
    }
