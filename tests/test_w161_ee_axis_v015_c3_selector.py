"""W-161 -- deterministic pre-outcome V0.15 C3 pair selector."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.step import StepObservation
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v015_c3_selector import (
    EEAxisV015C3SelectorError,
    V015_C3_SELECTOR_SCHEMA,
    V015C3Proposal,
    select_v015_c3_proposals,
)


def _table(keys: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in keys.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _observation(
    tables: tuple[SlotTable, ...], sinr: np.ndarray | None = None
) -> StepObservation:
    masks = np.stack([table.mask for table in tables])
    values = (
        np.zeros((len(tables), NUM_ACTIONS), dtype=np.float64)
        if sinr is None
        else np.asarray(sinr, dtype=np.float64)
    )
    candidates = SimpleNamespace(slot_tables=tables)
    return StepObservation(
        step_index=7,
        candidates=candidates,
        user_states=tuple(object() for _ in tables),
        state_matrix=np.zeros((len(tables), EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=masks,
        candidate_sinr=values,
    )


def _fixture() -> StepObservation:
    tables = (
        _table({0: (100, 1), 1: (300, 1), 2: (500, 1)}),
        _table({0: (200, 2), 1: (300, 1), 2: (500, 1)}),
        _table({0: (400, 3), 1: (500, 1), 2: (300, 1)}),
        _table({0: (700, 4), 1: (300, 1)}),
    )
    sinr = np.zeros((4, NUM_ACTIONS), dtype=np.float64)
    sinr[:, 0] = 10.0
    sinr[0, 1] = 9.0
    sinr[0, 2] = 8.0
    sinr[1, 1] = 8.0
    sinr[1, 2] = 7.0
    sinr[2, 1] = 6.0
    sinr[2, 2] = 5.0
    sinr[3, 1] = 4.0
    return _observation(tables, sinr)


def test_selector_returns_disjoint_same_physical_beam_proposals_with_exact_scores() -> None:
    observation = _fixture()
    proposals = select_v015_c3_proposals(
        observation,
        np.asarray([0, 0, 0, 0], dtype=np.int64),
        max_proposals=2,
    )

    assert all(isinstance(item, V015C3Proposal) for item in proposals)
    assert len(proposals) == 2
    assert len({user for item in proposals for user in (item.u, item.v)}) == 4
    assert all(item.au in (0, 1, 2) for item in proposals)
    assert all(item.av in (0, 1, 2) for item in proposals)
    assert all(item.key in {(300, 1), (500, 1)} for item in proposals)
    assert all(item.active_beam_reduction >= 0 for item in proposals)
    assert all(item.active_satellite_reduction >= 0 for item in proposals)
    assert all(0.0 <= item.min_normalized_log1p_sinr_retention <= 1.0 for item in proposals)
    assert all(item.schema == V015_C3_SELECTOR_SCHEMA for item in proposals)


def test_exact_beam_reduction_precedes_satellite_and_sinr_ties_are_deterministic() -> None:
    # Pair (0,1) merges two globally active beams.  Pair (0,2) is crafted to
    # have no beam reduction but does remove one active satellite: its target
    # is a new beam on an already-active satellite.
    tables = (
        _table({0: (10, 1), 1: (99, 9)}),
        _table({0: (10, 1), 1: (99, 9)}),
        _table({0: (10, 1), 1: (10, 2), 2: (20, 2)}),
        _table({0: (20, 3)}),
    )
    sinr = np.zeros((4, NUM_ACTIONS), dtype=np.float64)
    sinr[:, 0] = 1.0
    sinr[0, 1] = 1.0
    sinr[1, 1] = 1.0
    sinr[2, 1] = 1.0
    observation = _observation(tables, sinr)

    first = select_v015_c3_proposals(
        observation,
        reference_actions=np.asarray([0, 0, 0, 0], dtype=np.int64),
        max_proposals=1,
    )
    second = select_v015_c3_proposals(
        observation,
        reference_actions=np.asarray([0, 0, 0, 0], dtype=np.int64),
        max_proposals=1,
    )
    assert [(item.u, item.v, item.au, item.av, item.key) for item in first] == [
        (0, 1, 1, 1, (99, 9))
    ]
    assert first == second


def test_selector_uses_each_peer_only_once_and_never_evaluates_outcomes() -> None:
    tables = (
        _table({0: (1, 1), 1: (9, 9)}),
        _table({0: (2, 2), 1: (9, 9)}),
    )
    observation = _observation(tables)
    proposal = select_v015_c3_proposals(
        observation, np.asarray([0, 0], dtype=np.int64), max_proposals=1
    )[0]
    assert proposal.u == 0 and proposal.v == 1
    assert proposal.key == (9, 9)
    assert proposal.min_normalized_log1p_sinr_retention == pytest.approx(1.0)
    with pytest.raises(FrozenInstanceError):
        proposal.u = 1  # type: ignore[misc]


def test_selector_rejects_illegal_reference_or_candidate_sinr() -> None:
    observation = _fixture()
    with pytest.raises(EEAxisV015C3SelectorError, match="reference"):
        select_v015_c3_proposals(
            observation,
            np.asarray([4, 0, 0, 0], dtype=np.int64),
            max_proposals=1,
        )

    bad_sinr = np.zeros_like(observation.candidate_sinr)
    bad_sinr[0, 0] = np.nan
    broken = _observation(observation.candidates.slot_tables, bad_sinr)
    with pytest.raises(EEAxisV015C3SelectorError, match="SINR"):
        select_v015_c3_proposals(
            broken,
            np.asarray([0, 0, 0, 0], dtype=np.int64),
            max_proposals=1,
        )


def test_selector_returns_empty_when_no_common_legal_physical_beam() -> None:
    observation = _observation(
        (
            _table({0: (1, 1)}),
            _table({0: (2, 2)}),
        )
    )
    assert (
        select_v015_c3_proposals(
            observation,
            np.asarray([0, 0], dtype=np.int64),
            max_proposals=3,
        )
        == ()
    )
