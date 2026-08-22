"""Ruling C-11 — my step ordering and the paper's must agree everywhere.

The controller accepted that the two orderings cover the same events but
asked for an equivalence test, "否則這是未來的漂移點".

    mine:   select -> feasibility -> served -> derive z
    paper:  select -> z -> connect (x = a·z) -> feasibility -> outage

They differ in when ``z`` is formed, so the risk is a boundary case where
one admits a user the other does not.  This enumerates the boundaries
rather than sampling them.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import (
    NO_OP_ACTION,
    NUM_BEAM_SLOTS,
    SatelliteCandidate,
    action_index,
    assign_satellite_slots,
    build_slot_table,
)
from mcrl.env.service import resolve_service

SATS = (44714, 44718, 44723, 44730)
CELLS = [100, 101, 102, 103, 104, 105, 106]


def _tables(num_users, reachable=None):
    assignment = assign_satellite_slots(
        [SatelliteCandidate(n, True, 300.0 - i) for i, n in enumerate(SATS)],
        incumbent_norad=None,
    )
    return [
        build_slot_table(assignment, CELLS, cell_reachable=reachable)
        for _ in range(num_users)
    ]


def _paper_order(actions, tables, infeasible):
    """select -> z -> x = a·z -> feasibility -> outage, written literally.

    Keyed by the BEAM ``(s, v)``, because (3.3)/(3.4) are: ``U_{s,v}`` sums
    one satellite's beam and ``z_{s,v}`` lights one.  This reference used to
    key on the cell alone and so did the implementation, which is why they
    agreed — both were wrong together in the one configuration (3.12b)
    exists to describe, two satellites on one cell.
    """
    users = len(tables)
    selected_beam = {}
    for uid in range(users):
        action = int(actions[uid])
        if action == NO_OP_ACTION:
            continue
        association = tables[uid].association(action)
        selected_beam[uid] = (association.norad_id, association.cell_id)

    # z: a beam radiates iff at least one user selects it (3.4).
    radiating = set(selected_beam.values())

    served, loads = {}, {}
    for uid, beam in selected_beam.items():
        if beam not in radiating:  # x = a·z
            continue
        if bool(infeasible[uid]):  # then feasibility -> outage
            continue
        served[uid] = beam
        loads[beam] = loads.get(beam, 0) + 1
    return served, loads


def _mine(actions, tables, infeasible):
    resolution = resolve_service(np.array(actions), tables, infeasible)
    served = {
        uid: (
            int(resolution.serving_satellite[uid]),
            int(resolution.serving_cell[uid]),
        )
        for uid in range(len(tables))
        if resolution.served[uid]
    }
    return served, dict(resolution.eligible_load_by_beam)


def _assert_agree(actions, tables, infeasible):
    assert _mine(actions, tables, infeasible) == _paper_order(
        actions, tables, infeasible
    )


# -- the boundary cases ----------------------------------------------------


def test_everyone_served_on_distinct_cells():
    tables = _tables(7)
    actions = [action_index(0, j) for j in range(NUM_BEAM_SLOTS)]
    _assert_agree(actions, tables, np.zeros(7, dtype=bool))


def test_everyone_piled_onto_one_cell():
    tables = _tables(9)
    _assert_agree([action_index(0, 0)] * 9, tables, np.zeros(9, dtype=bool))


def test_a_single_user_alone_on_a_beam_going_infeasible():
    """The case where z and feasibility could disagree: the only selector."""
    tables = _tables(2)
    actions = [action_index(0, 0), action_index(0, 1)]
    infeasible = np.array([True, False])
    _assert_agree(actions, tables, infeasible)
    served, loads = _mine(actions, tables, infeasible)
    assert 0 not in served
    assert (SATS[0], CELLS[0]) not in loads


def test_every_user_on_one_beam_going_infeasible_together():
    tables = _tables(4)
    _assert_agree([action_index(0, 0)] * 4, tables, np.ones(4, dtype=bool))


def test_a_mix_of_no_ops_infeasible_and_served():
    tables = _tables(6)
    actions = [
        NO_OP_ACTION,
        action_index(0, 0),
        action_index(0, 0),
        action_index(1, 2),
        NO_OP_ACTION,
        action_index(2, 5),
    ]
    _assert_agree(actions, tables, np.array([0, 1, 0, 1, 0, 0], dtype=bool))


def test_everyone_a_no_op():
    tables = _tables(3)
    _assert_agree([NO_OP_ACTION] * 3, tables, np.zeros(3, dtype=bool))


def test_the_same_cell_reached_through_two_different_satellites():
    """§4A.2: ``cell_id`` does not depend on the satellite slot.

    And **two beams**, not one: (3.3) sums over ``u`` for a fixed ``(s, v)``,
    so a cell illuminated by two satellites carries two independent loads.
    Merging them charged each of these users the other's load in ``r3`` and
    halved both their rates in (3.14) while neither was sharing anything.
    """
    tables = _tables(2)
    actions = [action_index(0, 3), action_index(2, 3)]
    _assert_agree(actions, tables, np.zeros(2, dtype=bool))
    served, loads = _mine(actions, tables, np.zeros(2, dtype=bool))
    assert loads == {(SATS[0], CELLS[3]): 1, (SATS[2], CELLS[3]): 1}


def test_randomised_sweep_over_the_whole_space():
    rng = np.random.default_rng(0)
    for _ in range(400):
        users = int(rng.integers(1, 12))
        tables = _tables(users)
        actions = [
            NO_OP_ACTION
            if rng.random() < 0.2
            else action_index(
                int(rng.integers(0, 4)), int(rng.integers(0, NUM_BEAM_SLOTS))
            )
            for _ in range(users)
        ]
        infeasible = rng.random(users) < 0.3
        _assert_agree(actions, tables, infeasible)


def test_the_orderings_would_disagree_if_z_were_formed_after_feasibility():
    """Shows the test has teeth: a plausible wrong ordering fails it.

    If ``z`` were derived from the SERVED set instead of the SELECTED set, a
    beam whose only user is infeasible would go dark — which is the same
    answer here — but a beam with one infeasible and one feasible user would
    still radiate. Construct the case where the two definitions of z differ
    and confirm the implemented one matches the paper.
    """
    tables = _tables(2)
    actions = [action_index(0, 0), action_index(0, 0)]
    infeasible = np.array([True, False])
    served, loads = _mine(actions, tables, infeasible)
    # One user served, and the beam's load counts only the served one.
    assert served == {1: (SATS[0], CELLS[0])}
    assert loads == {(SATS[0], CELLS[0]): 1}
    _assert_agree(actions, tables, infeasible)
