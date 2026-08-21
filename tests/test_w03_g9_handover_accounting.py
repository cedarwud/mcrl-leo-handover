"""W-03 / G-9 — SDD §4A.7 acceptance tests T1…T12.

Gate G-9: "§4A.7 的 T1–T6 六項測試全數通過。**不得以索引比較實作 `r2`**".
T7–T10 came from review round 4, T9 was corrected in r7, T12 in round 5.

T1, T2, T3 are the counter-examples review verified by hand: each one is a
way that comparing action *indices* silently mis-scores a handover.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import (
    HANDOVER_COST,
    NO_OP_ACTION,
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
    PHI1,
    PHI2,
    Association,
    HandoverClass,
    HandoverLedger,
    SatelliteCandidate,
    SlotTable,
    UNSERVED,
    action_index,
    assert_selected_actions_valid,
    assign_satellite_slots,
    build_slot_table,
    classify_handover,
    contract_state_fields,
    decode_action,
    normalise_candidates,
)
from mcrl.errors import MCRLContractError

# Three satellites and a small cell neighbourhood shared by the scenarios.
SAT_A, SAT_B, SAT_C = 44714, 44718, 44723
CELLS = [100, 101, 102, 103, 104, 105, 106]


def _candidate(norad: int, margin: float, *, eligible: bool = True):
    return SatelliteCandidate(
        norad_id=norad, eligible=eligible, margin_km=margin
    )


def _table(candidates, incumbent, cells=None):
    assignment = assign_satellite_slots(
        normalise_candidates(candidates), incumbent_norad=incumbent
    )
    return assignment, build_slot_table(assignment, cells or CELLS)


# ---------------------------------------------------------------------------
# T1 — forced handover must not read as "stayed put"
# ---------------------------------------------------------------------------


def test_T1_incumbent_loses_eligibility_and_the_same_index_is_a_phi2():
    """Index 0 at both steps, but slot 0 changed hands: that is a handover."""
    ledger = HandoverLedger()

    _a, before = _table(
        [_candidate(SAT_A, 300.0), _candidate(SAT_B, 200.0)], incumbent=None
    )
    assert before.association(0) == Association(SAT_A, CELLS[0])
    assert ledger.observe(before.association(0)) is HandoverClass.NONE

    # A drops out of D2 eligibility; B takes slot 0.  Same action index.
    _a, after = _table(
        [_candidate(SAT_A, 300.0, eligible=False), _candidate(SAT_B, 200.0)],
        incumbent=SAT_A,
    )
    assert after.association(0) == Association(SAT_B, CELLS[0])

    assert ledger.observe(after.association(0)) is HandoverClass.INTER_SATELLITE


# ---------------------------------------------------------------------------
# T2 — a handover that already happened must not be charged twice
# ---------------------------------------------------------------------------


def test_T2_returning_to_slot_zero_after_a_handover_is_free():
    """Index changes 2 -> 0 but the satellite does not: cost must be 0."""
    ledger = HandoverLedger()

    _a, before = _table(
        [
            _candidate(SAT_A, 300.0),
            _candidate(SAT_B, 250.0),
            _candidate(SAT_C, 200.0),
        ],
        incumbent=SAT_A,
    )
    # slot 0 = A (incumbent), slot 1 = B, slot 2 = C -> a = 14 reaches C.
    switch_action = action_index(2, 0)
    assert before.association(switch_action) == Association(SAT_C, CELLS[0])
    ledger.observe(before.association(0))
    assert ledger.observe(before.association(switch_action)) is (
        HandoverClass.INTER_SATELLITE
    )

    # Next step C is the incumbent and occupies slot 0.  Staying on C is a=0.
    _a, after = _table(
        [
            _candidate(SAT_A, 300.0),
            _candidate(SAT_B, 250.0),
            _candidate(SAT_C, 200.0),
        ],
        incumbent=SAT_C,
    )
    assert after.association(0) == Association(SAT_C, CELLS[0])

    assert ledger.observe(after.association(0)) is HandoverClass.NONE


# ---------------------------------------------------------------------------
# T3 — same satellite, different cell
# ---------------------------------------------------------------------------


def test_T3_same_satellite_different_cell_is_phi1():
    ledger = HandoverLedger()
    _a, table = _table([_candidate(SAT_A, 300.0)], incumbent=SAT_A)
    ledger.observe(table.association(action_index(0, 0)))
    assert ledger.observe(table.association(action_index(0, 3))) is (
        HandoverClass.INTRA_SATELLITE
    )


def test_phi1_is_structurally_reachable_at_all():
    """The defect B-1 guarded against: no φ1 event can ever be detected.

    If satellite identity were the whole identity, every same-satellite cell
    change would score 0 and φ1 would be dead code.
    """
    _a, table = _table([_candidate(SAT_A, 300.0)], incumbent=SAT_A)
    classes = {
        classify_handover(
            table.association(action_index(0, 0)),
            table.association(action_index(0, j)),
        )
        for j in range(NUM_BEAM_SLOTS)
    }
    assert HandoverClass.INTRA_SATELLITE in classes


# ---------------------------------------------------------------------------
# T5 / T8 — outage boundaries
# ---------------------------------------------------------------------------


def test_T5_reentry_after_an_outage_is_phi2():
    ledger = HandoverLedger()
    _a, table = _table([_candidate(SAT_A, 300.0)], incumbent=None)
    ledger.observe(table.association(0))
    assert ledger.observe(UNSERVED) is HandoverClass.NONE
    assert ledger.observe(table.association(0)) is HandoverClass.INTER_SATELLITE


def test_T5_reentry_is_charged_even_returning_to_the_same_satellite():
    """Otherwise a policy could go offline on purpose to clear its cost."""
    ledger = HandoverLedger()
    same = Association(SAT_A, CELLS[0])
    ledger.observe(same)
    ledger.observe(UNSERVED)
    assert ledger.observe(same) is HandoverClass.INTER_SATELLITE


def test_T8_consecutive_outage_steps_each_score_zero():
    ledger = HandoverLedger()
    ledger.observe(Association(SAT_A, CELLS[0]))
    for _ in range(5):
        assert ledger.observe(UNSERVED) is HandoverClass.NONE
    # Exactly one re-entry charge, no matter how long the outage was.
    assert ledger.observe(Association(SAT_A, CELLS[0])) is (
        HandoverClass.INTER_SATELLITE
    )
    assert ledger.observe(Association(SAT_A, CELLS[0])) is HandoverClass.NONE


def test_episode_start_is_not_a_reentry():
    """P-8, the vacuum first step: no previous action exists to compare to."""
    ledger = HandoverLedger()
    assert ledger.observe(Association(SAT_A, CELLS[0])) is HandoverClass.NONE

    ledger.reset()
    assert ledger.previous is None
    assert ledger.observe(Association(SAT_B, CELLS[2])) is HandoverClass.NONE


def test_episode_start_differs_from_previously_unserved():
    assert classify_handover(None, Association(SAT_A, 1)) is HandoverClass.NONE
    assert classify_handover(UNSERVED, Association(SAT_A, 1)) is (
        HandoverClass.INTER_SATELLITE
    )


# ---------------------------------------------------------------------------
# T6 — dwell re-key
# ---------------------------------------------------------------------------


def test_T6_same_beam_slot_across_a_dwell_boundary_is_phi1():
    """After re-keying, ``j`` points at a different physical cell."""
    ledger = HandoverLedger()
    _a, before = _table([_candidate(SAT_A, 300.0)], incumbent=SAT_A, cells=CELLS)
    ledger.observe(before.association(action_index(0, 0)))

    rekeyed = [201, 202, 203, 204, 205, 206, 207]
    _a, after = _table(
        [_candidate(SAT_A, 300.0)], incumbent=SAT_A, cells=rekeyed
    )
    assert after.association(action_index(0, 0)).cell_id != CELLS[0]

    assert ledger.observe(after.association(action_index(0, 0))) is (
        HandoverClass.INTRA_SATELLITE
    )


def test_dwell_rekey_that_lands_on_the_same_cell_is_free():
    """Re-keying is not itself a handover — only a change of cell is."""
    ledger = HandoverLedger()
    ledger.observe(Association(SAT_A, CELLS[0]))
    shifted = [CELLS[0], 900, 901, 902, 903, 904, 905]
    _a, after = _table([_candidate(SAT_A, 300.0)], incumbent=SAT_A, cells=shifted)
    assert ledger.observe(after.association(action_index(0, 0))) is (
        HandoverClass.NONE
    )


# ---------------------------------------------------------------------------
# T7 — the branches of eq. (3.27) are mutually exclusive
# ---------------------------------------------------------------------------


def test_T7_changing_satellite_and_cell_is_exactly_phi2():
    result = classify_handover(
        Association(SAT_A, CELLS[0]), Association(SAT_B, CELLS[4])
    )
    assert result is HandoverClass.INTER_SATELLITE
    assert HANDOVER_COST[result] == PHI2
    assert HANDOVER_COST[result] != PHI1 + PHI2


def test_handover_costs_are_ordered_as_the_paper_requires():
    """The paper states only ``0 < φ1 < φ2``."""
    assert 0.0 < PHI1 < PHI2
    assert HANDOVER_COST[HandoverClass.NONE] == 0.0


def test_every_transition_gets_exactly_one_class():
    options = [
        UNSERVED,
        Association(SAT_A, CELLS[0]),
        Association(SAT_A, CELLS[1]),
        Association(SAT_B, CELLS[0]),
    ]
    for previous in options:
        for current in options:
            assert isinstance(
                classify_handover(previous, current), HandoverClass
            )


# ---------------------------------------------------------------------------
# T9 — normalisation is invariant to the raw enumeration order
# ---------------------------------------------------------------------------


def test_T9_shuffled_candidate_order_rebuilds_an_identical_contract():
    """r7 correction: this tests the NORMALISATION, not Q-value ordering.

    A flat MLP is not permutation-equivariant; asserting that its Q ranking
    survives a shuffle would be testing a property it does not have.
    """
    candidates = [
        _candidate(SAT_A, 300.0),
        _candidate(SAT_B, 250.0),
        _candidate(SAT_C, 200.0),
        _candidate(50000, 150.0),
        _candidate(50001, 100.0, eligible=False),
    ]
    rng = np.random.default_rng(0)

    assignment, table = _table(candidates, incumbent=SAT_B)
    reference_state = contract_state_fields(assignment, dwell_phase=0.25)

    for _ in range(20):
        shuffled = list(candidates)
        rng.shuffle(shuffled)
        other_assignment, other_table = _table(shuffled, incumbent=SAT_B)
        assert other_assignment == assignment
        assert np.array_equal(other_table.norad_ids, table.norad_ids)
        assert np.array_equal(other_table.cell_ids, table.cell_ids)
        assert np.array_equal(other_table.mask, table.mask)
        assert np.array_equal(
            contract_state_fields(other_assignment, dwell_phase=0.25),
            reference_state,
        )
        # The physical meaning of every action index is unchanged.
        for action in range(NUM_ACTIONS):
            if table.mask[action]:
                assert other_table.association(action) == table.association(
                    action
                )


def test_ties_in_margin_are_broken_by_norad_id():
    assignment = assign_satellite_slots(
        normalise_candidates(
            [_candidate(SAT_C, 200.0), _candidate(SAT_A, 200.0)]
        ),
        incumbent_norad=None,
    )
    assert assignment.norad_ids[:2] == (SAT_A, SAT_C)


# ---------------------------------------------------------------------------
# T12 — an empty mask trains nothing
# ---------------------------------------------------------------------------


def test_T12_empty_mask_admits_only_the_no_op():
    _a, table = _table([_candidate(SAT_A, 300.0, eligible=False)], incumbent=None)
    assert table.num_valid == 0
    assert not table.mask.any()
    assert table.association(NO_OP_ACTION) is UNSERVED
    with pytest.raises(MCRLContractError, match="not valid"):
        table.association(0)


def test_T12_selected_action_validation_rejects_a_fallback_index():
    _a, empty = _table([_candidate(SAT_A, 300.0, eligible=False)], incumbent=None)
    _a, full = _table([_candidate(SAT_A, 300.0)], incumbent=None)

    assert_selected_actions_valid(np.array([NO_OP_ACTION, 0]), [empty, full])

    with pytest.raises(MCRLContractError, match="invalid under its own mask"):
        assert_selected_actions_valid(np.array([0, 0]), [empty, full])

    with pytest.raises(MCRLContractError, match="valid actions available"):
        assert_selected_actions_valid(
            np.array([NO_OP_ACTION, NO_OP_ACTION]), [empty, full]
        )

    with pytest.raises(MCRLContractError, match="out of range"):
        assert_selected_actions_valid(np.array([0, NUM_ACTIONS]), [full, full])


# ---------------------------------------------------------------------------
# Index layout, slot assignment, masking, state block
# ---------------------------------------------------------------------------


def test_index_layout_is_satellite_major():
    assert NUM_ACTIONS == 28
    for satellite_slot in range(NUM_SATELLITE_SLOTS):
        for beam_slot in range(NUM_BEAM_SLOTS):
            action = action_index(satellite_slot, beam_slot)
            assert action == 7 * satellite_slot + beam_slot
            assert decode_action(action) == (satellite_slot, beam_slot)


def test_no_op_has_no_index_decomposition():
    with pytest.raises(MCRLContractError):
        decode_action(NO_OP_ACTION)


def test_incumbent_takes_slot_zero_even_with_a_worse_margin():
    assignment = assign_satellite_slots(
        normalise_candidates(
            [_candidate(SAT_A, 10.0), _candidate(SAT_B, 900.0)]
        ),
        incumbent_norad=SAT_A,
    )
    assert assignment.norad_ids[0] == SAT_A
    assert assignment.is_incumbent == (True, False, False, False)
    assert assignment.norad_ids[1] == SAT_B


def test_an_ineligible_incumbent_yields_slot_zero_to_the_best_margin():
    assignment = assign_satellite_slots(
        normalise_candidates(
            [
                _candidate(SAT_A, 900.0, eligible=False),
                _candidate(SAT_B, 100.0),
                _candidate(SAT_C, 200.0),
            ]
        ),
        incumbent_norad=SAT_A,
    )
    assert assignment.norad_ids[0] == SAT_C
    assert not any(assignment.is_incumbent)


def test_slots_beyond_the_eligible_count_are_masked():
    assignment = assign_satellite_slots(
        normalise_candidates([_candidate(SAT_A, 300.0), _candidate(SAT_B, 200.0)]),
        incumbent_norad=None,
    )
    assert assignment.occupied == (True, True, False, False)
    table = build_slot_table(assignment, CELLS)
    assert table.num_valid == 2 * NUM_BEAM_SLOTS
    assert not table.mask[2 * NUM_BEAM_SLOTS :].any()


def test_ordering_is_strictly_by_decreasing_margin():
    assignment = assign_satellite_slots(
        normalise_candidates(
            [
                _candidate(1, 10.0),
                _candidate(2, 50.0),
                _candidate(3, 30.0),
                _candidate(4, 40.0),
                _candidate(5, 20.0),
            ]
        ),
        incumbent_norad=None,
    )
    assert assignment.norad_ids == (2, 4, 3, 5)  # margins 50, 40, 30, 20
    margins = assignment.margin_km
    assert list(margins) == sorted(margins, reverse=True)


def test_more_than_four_eligible_satellites_fill_exactly_four_slots():
    assignment = assign_satellite_slots(
        normalise_candidates([_candidate(i, float(100 - i)) for i in range(20)]),
        incumbent_norad=None,
    )
    assert all(assignment.occupied)
    assert len(set(assignment.norad_ids)) == NUM_SATELLITE_SLOTS


def test_duplicate_candidates_are_rejected():
    with pytest.raises(MCRLContractError, match="duplicate NORAD"):
        assign_satellite_slots(
            [_candidate(SAT_A, 1.0), _candidate(SAT_A, 2.0)],
            incumbent_norad=None,
        )


def test_missing_lattice_neighbour_masks_only_that_beam_slot():
    assignment = assign_satellite_slots(
        normalise_candidates([_candidate(SAT_A, 300.0)]), incumbent_norad=None
    )
    cells = [100, 101, -1, 103, 104, 105, 106]
    table = build_slot_table(assignment, cells)
    assert not table.mask[action_index(0, 2)]
    assert table.mask[action_index(0, 1)]
    assert table.cell_ids[action_index(0, 2)] == -1


def test_link_geometry_predicate_masks_individual_pairs():
    assignment = assign_satellite_slots(
        normalise_candidates([_candidate(SAT_A, 300.0), _candidate(SAT_B, 200.0)]),
        incumbent_norad=None,
    )
    reachable = np.ones((NUM_SATELLITE_SLOTS, NUM_BEAM_SLOTS), dtype=bool)
    reachable[1, 4] = False
    table = build_slot_table(assignment, CELLS, cell_reachable=reachable)
    assert not table.mask[action_index(1, 4)]
    assert table.mask[action_index(0, 4)]


def test_cell_identity_does_not_depend_on_the_satellite_slot():
    """§4A.2: the two factors are orthogonal."""
    assignment = assign_satellite_slots(
        normalise_candidates(
            [_candidate(SAT_A, 300.0), _candidate(SAT_B, 200.0), _candidate(SAT_C, 100.0)]
        ),
        incumbent_norad=None,
    )
    table = build_slot_table(assignment, CELLS)
    for beam_slot in range(NUM_BEAM_SLOTS):
        cells_seen = {
            int(table.cell_ids[action_index(satellite_slot, beam_slot)])
            for satellite_slot in range(NUM_SATELLITE_SLOTS)
            if table.mask[action_index(satellite_slot, beam_slot)]
        }
        assert cells_seen == {CELLS[beam_slot]}


def test_slot_table_rejects_a_valid_action_without_identity():
    with pytest.raises(MCRLContractError, match="no satellite identity"):
        SlotTable(
            norad_ids=np.full(NUM_ACTIONS, -1, dtype=np.int64),
            cell_ids=np.zeros(NUM_ACTIONS, dtype=np.int64),
            mask=np.ones(NUM_ACTIONS, dtype=bool),
        )


def test_contract_state_block_is_thirteen_dimensions():
    assignment = assign_satellite_slots(
        normalise_candidates(
            [
                SatelliteCandidate(SAT_A, True, 300.0, -6.1, 3),
                SatelliteCandidate(SAT_B, True, 200.0, 4.2, 1),
            ]
        ),
        incumbent_norad=SAT_A,
    )
    block = contract_state_fields(assignment, dwell_phase=0.5)
    assert block.shape == (13,)
    assert block.tolist()[:4] == [1.0, 0.0, 0.0, 0.0]
    assert block.tolist()[4:8] == [3.0, 1.0, 0.0, 0.0]
    assert block.tolist()[8:12] == pytest.approx([-6.1, 4.2, 0.0, 0.0], abs=1e-6)
    assert block[12] == pytest.approx(0.5)


def test_radial_rate_keeps_its_sign_and_magnitude():
    """A flag would lose the magnitude; §4A.6 requires the rate."""
    approaching = assign_satellite_slots(
        [SatelliteCandidate(SAT_A, True, 100.0, -7.4, 0)], incumbent_norad=None
    )
    receding = assign_satellite_slots(
        [SatelliteCandidate(SAT_A, True, 100.0, 7.4, 0)], incumbent_norad=None
    )
    assert contract_state_fields(approaching, dwell_phase=0.0)[8] < 0
    assert contract_state_fields(receding, dwell_phase=0.0)[8] > 0


def test_dwell_phase_is_range_checked():
    assignment = assign_satellite_slots(
        [_candidate(SAT_A, 1.0)], incumbent_norad=None
    )
    with pytest.raises(ValueError):
        contract_state_fields(assignment, dwell_phase=1.5)


def test_state_dimension_is_the_authoritative_125():
    from mcrl.env.action_contract import CONTRACT_STATE_DIM, STATE_DIM

    assert CONTRACT_STATE_DIM == 13
    assert STATE_DIM == 4 * 28 + 13 == 125


def test_ledger_reports_the_incumbent_for_the_next_assignment():
    ledger = HandoverLedger()
    assert ledger.incumbent_norad is None
    ledger.observe(Association(SAT_B, CELLS[0]))
    assert ledger.incumbent_norad == SAT_B
    ledger.observe(UNSERVED)
    assert ledger.incumbent_norad is None
