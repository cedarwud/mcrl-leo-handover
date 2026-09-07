"""W-131 -- exact OPS-3 h=0 opening-service persistence gate.

These tests exercise only the formula boundary.  They do not construct a
scenario, open a TLE outcome, run an episode, or train a learner.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_ops3 import (
    OPS3FrozenBackground,
    OPS3Offset,
    OPS3FormulaError,
    build_ops3_surface,
    opening_service_feasibility_surface,
)


NATIVE = 28
LEGAL_ACTIONS = np.array([0, 1, 7, 8], dtype=np.int64)


def _identity() -> tuple[np.ndarray, np.ndarray]:
    norad = np.full(NATIVE, -1, dtype=np.int64)
    cell = np.full(NATIVE, -1, dtype=np.int64)
    norad[0], cell[0] = 100, 1
    norad[1], cell[1] = 100, 2
    norad[7], cell[7] = 101, 1
    norad[8], cell[8] = 101, 2
    return norad, cell


def _legal() -> np.ndarray:
    result = np.zeros(NATIVE, dtype=np.bool_)
    result[LEGAL_ACTIONS] = True
    return result


def _background() -> OPS3FrozenBackground:
    return OPS3FrozenBackground(
        norad_ids=np.array([100], dtype=np.int64),
        cell_ids=np.array([1], dtype=np.int64),
        load=np.array([2], dtype=np.int64),
        power_w=np.array([0.5], dtype=np.float64),
    )


def _offsets() -> tuple[OPS3Offset, ...]:
    d2 = np.zeros(NATIVE, dtype=np.bool_)
    visible = np.zeros(NATIVE, dtype=np.bool_)
    d2[LEGAL_ACTIONS] = True
    visible[LEGAL_ACTIONS] = True
    gain = np.zeros(NATIVE, dtype=np.float64)
    gain[LEGAL_ACTIONS] = 1.0
    rate = np.zeros(NATIVE, dtype=np.float64)
    rate[LEGAL_ACTIONS] = 10.0
    sinr = np.zeros(NATIVE, dtype=np.float64)
    sinr[LEGAL_ACTIONS] = 1.0
    value = OPS3Offset(gain, d2, visible, rate, sinr)
    return value, value, value


def test_h0_service_failure_blocks_every_future_persistence_term():
    """A legal future-capable action that fails at h=0 gets only -kappa."""

    norad, cell = _identity()
    legal = _legal()
    opening = legal.copy()
    opening[1] = False
    surface = build_ops3_surface(
        legal_mask=legal,
        opening_service_feasible=opening,
        reference_action=0,
        candidate_norad_ids=norad,
        candidate_cell_ids=cell,
        segment_start_gain_linear=np.where(legal, 1.0, 0.0),
        offsets=_offsets(),
        background=_background(),
        user_count=4,
        step_index=0,
        total_steps=4,
        p0_w=0.5,
        pmax_w=1.0,
        lambda_bits_per_j=1.0,
        kappa_bits=100.0,
        interval_s=1.0,
    )

    assert surface.opening_service_feasible[1] is np.False_
    np.testing.assert_array_equal(surface.persistence[:, 1], [0.0, 0.0, 0.0])
    np.testing.assert_array_equal(surface.rate_bps[:, 1], [0.0, 0.0, 0.0])
    np.testing.assert_array_equal(surface.marginal_power_w[:, 1], [0.0, 0.0, 0.0])
    np.testing.assert_array_equal(surface.sinr_linear[:, 1], [0.0, 0.0, 0.0])
    assert surface.z2_bits[1] == -100.0


def test_opening_service_surface_uses_execution_equivalent_recurrence_ceiling():
    legal = _legal()
    start = np.where(legal, 1.0, 0.0)
    current = start.copy()
    current[1] = 0.2  # 0.5 * 1.0 / 0.2 = 2.5 > the 1.0 ceiling.
    current[7] = 0.0  # execution treats a null-pointing link as infeasible.

    feasible = opening_service_feasibility_surface(
        legal_mask=legal,
        segment_start_gain_linear=start,
        current_gain_linear=current,
        p0_w=0.5,
        pmax_w=1.0,
    )

    assert feasible.dtype == np.bool_
    assert feasible[0]
    assert not feasible[1]
    assert not feasible[7]
    assert feasible[8]
    assert not np.any(feasible[~legal])


def test_opening_service_surface_fails_closed_on_nonfinite_current_gain():
    legal = _legal()
    with pytest.raises(OPS3FormulaError, match="current_gain_linear"):
        opening_service_feasibility_surface(
            legal_mask=legal,
            segment_start_gain_linear=np.where(legal, 1.0, 0.0),
            current_gain_linear=np.full(NATIVE, np.nan, dtype=np.float64),
            p0_w=0.5,
            pmax_w=1.0,
        )
