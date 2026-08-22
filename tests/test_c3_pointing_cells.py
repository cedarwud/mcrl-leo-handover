"""Ruling C-3 — the 39 pointing cells, chosen by a total order and frozen.

The controller rejected both of my proposals and gave a third: keep the
greedy's *intent* but replace it with a total order, then write the 39
``cell_id`` values into the PREREG verbatim so reproducibility stops
depending on the rule at all.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.cells import (
    POINTING_CELL_COUNT,
    build_cell_grid,
    cell_area_fraction_inside_service_area,
    coverage_fraction,
    freeze_pointing_cells,
    select_pointing_cells,
)
from mcrl.errors import MCRLContractError

ALTITUDE_KM = 483.0


@pytest.fixture(scope="module")
def grid():
    return build_cell_grid(altitude_km=ALTITUDE_KM)


def test_V_is_39(grid):
    assert POINTING_CELL_COUNT == 39
    assert select_pointing_cells(grid).size == 39


def test_the_order_is_total_so_the_result_is_unique(grid):
    """The third key exists to make ties impossible."""
    first = select_pointing_cells(grid)
    for _ in range(3):
        assert np.array_equal(select_pointing_cells(grid), first)
    assert len(set(first.tolist())) == first.size


def test_the_selection_is_deterministic_without_a_seed(grid):
    """No RNG anywhere: the sample lattice for the area fraction is fixed.

    Checked on the parsed tree — a text search trips on the docstring that
    explains why there is no RNG.
    """
    import ast
    import inspect
    import textwrap

    from mcrl.env import cells

    for function in (
        cells.cell_area_fraction_inside_service_area,
        cells.select_pointing_cells,
    ):
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not called & {"default_rng", "random", "choice", "shuffle"}


def test_cells_inside_the_service_area_are_preferred(grid):
    fraction = cell_area_fraction_inside_service_area(grid)
    chosen = select_pointing_cells(grid)
    rejected = np.setdiff1d(np.arange(grid.count), chosen)
    assert fraction[chosen].min() >= fraction[rejected].max() - 1e-12


def test_fully_interior_cells_are_all_chosen(grid):
    fraction = cell_area_fraction_inside_service_area(grid)
    interior = np.flatnonzero(fraction >= 0.999)
    assert interior.size > 0
    assert set(interior.tolist()) <= set(select_pointing_cells(grid).tolist())


def test_the_area_fraction_is_a_proper_fraction(grid):
    fraction = cell_area_fraction_inside_service_area(grid)
    assert fraction.shape == (grid.count,)
    assert np.all((fraction >= 0.0) & (fraction <= 1.0))
    assert fraction.max() > 0.99, "some cell must sit wholly inside"
    assert fraction.min() == 0.0, "the guard ring must sit wholly outside"


# -- ★ the coverage the ruling asked to be measured and reported ----------


def test_the_chosen_39_meet_the_95_percent_target(grid):
    """Ruling C-3: measure, record, and escalate rather than change the rule."""
    frozen = freeze_pointing_cells(grid)
    assert frozen["count"] == 39
    assert frozen["coverage_fraction"] >= 0.95, (
        "below target — escalate, do not swap the selection rule"
    )
    assert frozen["coverage_fraction"] == pytest.approx(0.9517, abs=0.002)


def test_the_frozen_record_carries_what_the_prereg_needs(grid):
    frozen = freeze_pointing_cells(grid)
    assert len(frozen["cell_ids"]) == 39
    assert all(isinstance(cell, int) for cell in frozen["cell_ids"])
    assert frozen["cell_ids"] == sorted(frozen["cell_ids"])
    assert "selection_rule" in frozen
    assert frozen["cell_radius_km"] == pytest.approx(13.998, abs=0.001)


def test_the_frozen_ids_reproduce_the_coverage_without_the_rule(grid):
    """The point of freezing them: the rule is no longer load-bearing."""
    frozen = freeze_pointing_cells(grid)
    replayed = coverage_fraction(grid, np.array(frozen["cell_ids"]))
    assert replayed == pytest.approx(frozen["coverage_fraction"])


def test_the_set_is_fixed_not_recomputed_per_step(grid):
    """A set drifting with the sub-satellite point would fake handovers.

    Nothing in the selection depends on a satellite, a time, or a user — the
    signature takes only the grid.
    """
    import inspect

    signature = inspect.signature(select_pointing_cells)
    assert list(signature.parameters) == ["grid", "count"]


def test_an_impossible_count_is_refused(grid):
    with pytest.raises(MCRLContractError, match="cannot select"):
        select_pointing_cells(grid, count=grid.count + 1)
    with pytest.raises(MCRLContractError, match="cannot select"):
        select_pointing_cells(grid, count=0)


def test_a_lower_altitude_still_yields_39_but_less_coverage():
    """The sensitivity behind C-2/C-3: coverage falls as the shell drops."""
    lower = freeze_pointing_cells(build_cell_grid(altitude_km=426.0))
    higher = freeze_pointing_cells(build_cell_grid(altitude_km=540.0))
    assert lower["count"] == higher["count"] == 39
    assert lower["coverage_fraction"] < higher["coverage_fraction"]
