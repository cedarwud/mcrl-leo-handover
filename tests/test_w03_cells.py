"""W-03 — the global earth-fixed cell lattice (SDD §4A.2).

Also measures how many pointing cells 95% coverage actually needs, which is
what turns SDD F5's ``V = 39`` from a quoted number into a checked one.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcrl.env.cells import (
    AXIAL_NEIGHBOR_DIRS,
    NUM_NEIGHBORS,
    THETA_3DB_DEG,
    build_cell_grid,
    cell_radius_km,
    coverage_fraction,
    greedy_coverage_order,
)
from mcrl.env.constants import R_E_KM
from mcrl.errors import MCRLContractError

V_FROZEN = 39
"""SDD F5 / Q-G: the frozen number of pointing cells."""

MEASURED_ALTITUDE_KM = 485.0
"""docs/EPHEMERIS-NOTES.md §5 — visible-satellite altitude p50, recent corpus."""


@pytest.fixture(scope="module")
def grid_550():
    return build_cell_grid(altitude_km=550.0)


@pytest.fixture(scope="module")
def grid_measured():
    return build_cell_grid(altitude_km=MEASURED_ALTITUDE_KM)


# -- lattice construction --------------------------------------------------


def test_cell_radius_uses_the_half_angle(grid_550):
    assert grid_550.cell_radius_km == pytest.approx(15.94, abs=0.01)
    assert cell_radius_km(550.0) == pytest.approx(
        550.0 * math.tan(math.radians(THETA_3DB_DEG / 2.0))
    )


def test_build_requires_exactly_one_sizing_argument():
    with pytest.raises(ValueError):
        build_cell_grid()
    with pytest.raises(ValueError):
        build_cell_grid(altitude_km=550.0, cell_radius_km_override=10.0)


def test_neighbour_directions_are_the_six_canonical_axial_steps():
    assert len(AXIAL_NEIGHBOR_DIRS) == NUM_NEIGHBORS == 6
    assert len(set(AXIAL_NEIGHBOR_DIRS)) == 6
    # Opposite directions must pair up, or "neighbour of my neighbour" breaks.
    as_set = set(AXIAL_NEIGHBOR_DIRS)
    for dq, dr in AXIAL_NEIGHBOR_DIRS:
        assert (-dq, -dr) in as_set


def test_neighbour_relation_is_symmetric(grid_550):
    for cell in range(grid_550.count):
        for direction in range(NUM_NEIGHBORS):
            neighbour = int(grid_550.neighbor_ids[cell, direction])
            if neighbour < 0:
                continue
            opposite = (direction + 3) % NUM_NEIGHBORS
            assert int(grid_550.neighbor_ids[neighbour, opposite]) == cell


def test_neighbour_distance_is_one_pitch(grid_550):
    for cell in range(grid_550.count):
        for neighbour in grid_550.neighbor_ids[cell]:
            if neighbour < 0:
                continue
            distance = float(
                np.linalg.norm(
                    grid_550.centers_km[cell] - grid_550.centers_km[int(neighbour)]
                )
            )
            assert distance == pytest.approx(grid_550.pitch_km, rel=1e-9)


def test_every_area_serving_cell_has_a_full_neighbourhood(grid_550):
    serving = np.flatnonzero(grid_550.serves_area)
    assert serving.size > 0
    assert (grid_550.neighbor_ids[serving] >= 0).all()


def test_zero_guard_rings_is_rejected_when_it_truncates_the_neighbourhood():
    with pytest.raises(MCRLContractError, match="6-neighbourhood"):
        build_cell_grid(altitude_km=550.0, guard_rings=0)


def test_cell_centres_sit_on_the_sphere(grid_550):
    radii = np.linalg.norm(grid_550.centers_ecef_km, axis=1)
    assert np.allclose(radii, R_E_KM, atol=1e-6)


def test_three_colour_reuse_map_never_repeats_on_a_neighbour(grid_550):
    for cell in range(grid_550.count):
        own = int(grid_550.colors[cell])
        for neighbour in grid_550.neighbor_ids[cell]:
            if neighbour >= 0:
                assert int(grid_550.colors[int(neighbour)]) != own


# -- anchor and neighbourhood ---------------------------------------------


def test_anchor_is_the_nearest_centre(grid_550):
    rng = np.random.default_rng(1)
    points = rng.uniform([-100.0, -45.0], [100.0, 45.0], size=(50, 2))
    anchors = grid_550.anchor_cell_ids(points)
    for point, anchor in zip(points, anchors.tolist()):
        distances = np.linalg.norm(grid_550.centers_km - point, axis=1)
        assert distances[anchor] == pytest.approx(distances.min())


def test_neighbourhood_row_is_anchor_then_six_neighbours(grid_550):
    anchors = grid_550.anchor_cell_ids(np.array([[0.0, 0.0], [30.0, 10.0]]))
    rows = grid_550.neighborhood_cell_ids(anchors)
    assert rows.shape == (2, 7)
    for row, anchor in zip(rows, anchors.tolist()):
        assert int(row[0]) == anchor
        assert list(row[1:]) == list(grid_550.neighbor_ids[anchor])


def test_neighbourhood_depends_only_on_the_anchor(grid_550):
    """§4A.2: ``cell_id(j)`` is independent of the satellite slot ``l``."""
    anchor = int(grid_550.anchor_cell_ids(np.array([[0.0, 0.0]]))[0])
    first = grid_550.neighborhood_cell_ids(np.array([anchor]))
    second = grid_550.neighborhood_cell_ids(np.array([anchor]))
    assert np.array_equal(first, second)


def test_out_of_range_anchor_is_rejected(grid_550):
    with pytest.raises(MCRLContractError, match="out of range"):
        grid_550.neighborhood_cell_ids(np.array([grid_550.count]))


def test_a_user_barely_moves_between_dwell_boundaries(grid_550):
    """§4A.2: 30 km/h for 10 s is 83 m against a 15.94 km cell radius."""
    displacement_km = 30.0 / 3600.0 * 10.0
    assert displacement_km == pytest.approx(0.0833, abs=1e-3)
    assert displacement_km < 0.01 * grid_550.cell_radius_km


# -- coverage: checking F5's V = 39 ---------------------------------------


def test_coverage_of_a_single_cell_is_its_own_footprint(grid_550):
    centre = int(grid_550.anchor_cell_ids(np.array([[0.0, 0.0]]))[0])
    fraction = coverage_fraction(grid_550, np.array([centre]))
    area_ratio = math.pi * grid_550.cell_radius_km**2 / (200.0 * 90.0)
    assert fraction == pytest.approx(area_ratio, rel=0.05)


def test_coverage_is_monotone_in_the_number_of_cells(grid_550):
    order, curve = greedy_coverage_order(grid_550, max_cells=20)
    assert np.all(np.diff(curve) > 0)
    assert coverage_fraction(grid_550, order[:5]) == pytest.approx(curve[4])


@pytest.mark.parametrize(
    "altitude_km, cells_for_95, coverage_at_39",
    [
        (780.0, 16, 1.000),
        (550.0, 34, 0.997),
        (MEASURED_ALTITUDE_KM, 39, 0.955),
    ],
)
def test_measured_coverage_against_the_frozen_V(
    altitude_km, cells_for_95, coverage_at_39
):
    """F5 targets 95% coverage; this measures what ``V = 39`` actually buys.

    F5's own derivation used an area ratio (18,000 km² × 0.95 ÷ cell area)
    with a ×1.5 guard factor, giving 29.1 cells at 550 km.  That ignores
    edge overhang: a lattice cropped to a rectangle wastes footprint outside
    it, and the measured requirement at 550 km is 34 cells, not 29.
    """
    grid = build_cell_grid(altitude_km=altitude_km)
    _order, curve = greedy_coverage_order(grid, max_cells=V_FROZEN + 5)
    needed = int(np.argmax(curve >= 0.95)) + 1
    assert needed == cells_for_95
    # The greedy order stops once nothing new can be covered, so at 780 km it
    # saturates at 19 cells; the remaining 20 of V=39 add nothing.
    achieved = float(curve[min(V_FROZEN, len(curve)) - 1])
    assert achieved == pytest.approx(coverage_at_39, abs=0.005)


def test_V_39_still_meets_the_95_percent_target_at_the_measured_altitude(
    grid_measured,
):
    """It does — but with no margin left, which F5 did not anticipate."""
    _order, curve = greedy_coverage_order(grid_measured, max_cells=V_FROZEN)
    achieved = float(curve[V_FROZEN - 1])
    assert achieved >= 0.95
    assert achieved < 0.96, "the margin F5 assumed is gone"


def test_lower_altitude_needs_strictly_more_cells():
    counts = []
    for altitude_km in (780.0, 550.0, MEASURED_ALTITUDE_KM):
        grid = build_cell_grid(altitude_km=altitude_km)
        _order, curve = greedy_coverage_order(grid, max_cells=50)
        counts.append(int(np.argmax(curve >= 0.95)) + 1)
    assert counts == sorted(counts)
    assert counts[0] < counts[-1]
