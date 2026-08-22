"""W-18 item 3 — ``A_u(t)`` **can** be a proper subset of ``𝒞``.

The controller asked whether the mask is (i) able to shrink the action set
but not doing so in this scenario, or (ii) redundant by construction because
the candidate table is only ever built from valid beams.

It is (i) for two of the three terms and (ii) for one, and the difference
matters: under (ii) the empty-mask no-op of C-15 would be dead code and
§4.1's mask would be an always-true check.  Each term is triggered here in
isolation, which is the only way to tell the two apart — a scenario in which
nothing binds proves nothing either way.
"""

from __future__ import annotations

import numpy as np

from mcrl.env.action_contract import (
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
    SatelliteCandidate,
    assign_satellite_slots,
    build_slot_table,
)
from mcrl.env.cells import build_cell_grid

CELLS = [10, 11, 12, 13, 14, 15, 16]


def _assignment(count: int):
    return assign_satellite_slots(
        [SatelliteCandidate(100 + i, True, 300.0 - i) for i in range(count)],
        incumbent_norad=None,
    )


def test_term_1_binds_when_fewer_than_four_satellites_are_d2_eligible():
    """Slot occupancy.  ``assign_satellite_slots`` leaves slots EMPTY.

    This is the one that makes the mask non-redundant: nothing upstream
    pads the window, so a sparse D2 result propagates straight into the
    mask instead of being papered over.
    """
    table = build_slot_table(_assignment(2), CELLS)
    assert table.num_valid == 2 * NUM_BEAM_SLOTS == 14
    assert table.num_valid < NUM_ACTIONS


def test_term_2_binds_when_the_lattice_has_no_such_neighbour():
    cells = [10, 11, -1, -1, 14, 15, 16]
    table = build_slot_table(_assignment(4), cells)
    assert table.num_valid == NUM_SATELLITE_SLOTS * 5 == 20


def test_term_3_binds_when_a_satellite_is_below_the_cells_horizon():
    """Evaluated AFTER the slots are filled, not as a pre-filter."""
    reachable = np.ones((NUM_SATELLITE_SLOTS, NUM_BEAM_SLOTS), dtype=bool)
    reachable[0, :] = False
    table = build_slot_table(_assignment(4), CELLS, cell_reachable=reachable)
    assert table.num_valid == 3 * NUM_BEAM_SLOTS == 21


def test_the_empty_mask_is_reachable_so_the_no_op_is_not_dead_code():
    """C-15's no-op has a live trigger: zero D2-eligible satellites."""
    table = build_slot_table(_assignment(0), CELLS)
    assert table.num_valid == 0
    assert not table.mask.any()


def test_term_2_is_the_one_that_cannot_fire_and_that_is_by_design():
    """The guard ring makes "cell exists" always true for served cells.

    ``build_cell_grid`` refuses to return a lattice in which an
    area-serving cell lacks a full six-neighbourhood, so within the service
    area term 2 is structurally satisfied.  That is answer (ii) for this
    term — and it is a deliberate property of the geometry, not an accident
    of the parameters, which is why it is asserted rather than measured.
    """
    grid = build_cell_grid(altitude_km=483.0)
    serving = np.flatnonzero(grid.serves_area)
    assert serving.size > 0
    assert np.all(grid.neighbor_ids[serving] >= 0), (
        "the guard ring exists precisely to make this hold"
    )
