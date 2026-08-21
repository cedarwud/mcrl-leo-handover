"""W-15 / G-10 — the Bessel numerical-domain guard (SDD §3.4a, P-1).

The independent reference is ``mpmath.besselj`` at 30 decimal digits, an
arbitrary-precision implementation with no shared code path.  That is the
same role ``tcppver.out`` plays for SGP4 in G-1: without it these tests
would only prove the implementation agrees with itself.
"""

from __future__ import annotations

import math

import mpmath as mp
import numpy as np
import pytest

from mcrl.runtime.bessel import (
    BESSEL_SERIES_MAX_ABS_X,
    bessel_j,
    bessel_j_miller,
    bessel_j_series,
    uses_miller_recursion,
)

mp.mp.dps = 30

MU_CEILING_MEASURED = 67.32
"""docs/EPHEMERIS-NOTES.md §6 — the ceiling at the corpus's 485 km."""


def reference(n: int, x: float) -> float:
    return float(mp.besselj(n, x))


# -- G-10(c): the headline anchor -----------------------------------------


def test_G10c_J3_of_70_is_not_an_astronomical_number():
    """SDD §3.4a: the series returns -5.8e11 where the truth is -0.0154."""
    assert bessel_j(3, 70.0) == pytest.approx(-0.0153948, abs=1e-6)
    assert reference(3, 70.0) == pytest.approx(-0.0153948, abs=1e-6)
    assert abs(bessel_j(3, 70.0)) < 1.0


def test_the_failure_the_guard_prevents_is_real_and_reproducible():
    """Exhibit the defect, so nobody later 'cleans up' the routing."""
    broken = bessel_j_series(3, 70.0)
    assert abs(broken) > 1e11
    assert broken == pytest.approx(-5.8e11, rel=0.05)
    # Seventeen orders of magnitude, and no exception on the way.
    assert abs(broken / reference(3, 70.0)) > 1e13


def test_routing_threshold_is_where_the_spec_says():
    assert BESSEL_SERIES_MAX_ABS_X == 34.0
    assert not uses_miller_recursion(33.9)
    assert uses_miller_recursion(34.1)
    assert uses_miller_recursion(-70.0)


def test_the_measured_mu_ceiling_routes_to_miller():
    """P-1 re-verification at the altitude the corpus actually shows."""
    assert uses_miller_recursion(MU_CEILING_MEASURED)
    for order in (1, 3):
        assert bessel_j(order, MU_CEILING_MEASURED) == pytest.approx(
            reference(order, MU_CEILING_MEASURED), abs=1e-12
        )


# -- accuracy against the independent reference ---------------------------


def test_routed_values_match_mpmath_across_the_whole_domain():
    worst = 0.0
    worst_at = None
    for order in (0, 1, 2, 3, 5):
        for x in np.linspace(0.05, 400.0, 500):
            error = abs(bessel_j(order, float(x)) - reference(order, float(x)))
            if error > worst:
                worst, worst_at = error, (order, float(x))
    assert worst < 2e-3, f"worst {worst:.3e} at {worst_at}"


def test_miller_is_accurate_everywhere_to_machine_precision():
    worst = 0.0
    for order in (0, 1, 2, 3, 5):
        for x in np.linspace(0.05, 400.0, 400):
            worst = max(
                worst, abs(bessel_j_miller(order, float(x)) - reference(order, float(x)))
            )
    assert worst < 1e-14, f"worst {worst:.3e}"


def test_the_series_is_accurate_only_below_the_threshold():
    """Why the threshold sits at 34 and not higher."""
    assert abs(bessel_j_series(3, 20.0) - reference(3, 20.0)) < 1e-9
    assert abs(bessel_j_series(3, 30.0) - reference(3, 30.0)) < 1e-5
    # At the boundary the series still carries ~1e-3.
    assert abs(bessel_j_series(3, 34.0) - reference(3, 34.0)) < 2e-3
    # Just past it, it is already useless.
    assert abs(bessel_j_series(3, 45.0) - reference(3, 45.0)) > 1.0


def test_the_two_paths_agree_below_the_threshold():
    """Agreement is bounded by the *series'* accuracy, which degrades with x."""
    for order in (0, 1, 3):
        for x in np.linspace(0.05, 30.0, 200):
            assert bessel_j_series(order, float(x)) == pytest.approx(
                bessel_j_miller(order, float(x)), abs=1e-4
            )
    # Well inside the safe domain they agree to near machine precision.
    for order in (0, 1, 3):
        for x in np.linspace(0.05, 12.0, 100):
            assert bessel_j_series(order, float(x)) == pytest.approx(
                bessel_j_miller(order, float(x)), abs=1e-12
            )


# -- structural identities -------------------------------------------------


def test_recurrence_identity_holds_exactly_on_the_miller_path():
    """``J_{n-1}(x) + J_{n+1}(x) = (2n/x)·J_n(x)``, to machine precision."""
    for x in (35.0, 67.32, 120.0, 200.0):
        assert uses_miller_recursion(x)
        for order in (1, 2, 3, 4):
            left = bessel_j(order - 1, x) + bessel_j(order + 1, x)
            right = (2.0 * order / x) * bessel_j(order, x)
            assert left == pytest.approx(right, abs=1e-12)


def test_recurrence_identity_degrades_on_the_series_path():
    """The same identity, only to the series' own accuracy.

    Each order is summed independently, so the errors do not cancel.  This
    is the quantitative reason the routing threshold cannot be pushed higher.
    """
    for x, tolerance in ((1.0, 1e-14), (12.0, 1e-12), (33.0, 5e-3)):
        assert not uses_miller_recursion(x)
        for order in (1, 2, 3, 4):
            left = bessel_j(order - 1, x) + bessel_j(order + 1, x)
            right = (2.0 * order / x) * bessel_j(order, x)
            assert left == pytest.approx(right, abs=tolerance)


def test_normalisation_identity_holds():
    """``J₀(x) + 2·Σ_{k≥1} J_{2k}(x) = 1``."""
    for x in (0.5, 10.0, 40.0, 100.0):
        total = bessel_j(0, x) + 2.0 * sum(
            bessel_j(2 * k, x) for k in range(1, 120)
        )
        assert total == pytest.approx(1.0, abs=1e-9)


def test_known_zeros_are_zeros():
    assert bessel_j(0, 2.404825557695773) == pytest.approx(0.0, abs=1e-12)
    assert bessel_j(1, 3.831705970207512) == pytest.approx(0.0, abs=1e-12)
    # Zeros past the routing threshold, so Miller is exercised too.
    assert uses_miller_recursion(40.05842576462824)
    assert bessel_j(0, 40.05842576462824) == pytest.approx(0.0, abs=1e-13)
    assert bessel_j(1, 41.61709421281445) == pytest.approx(0.0, abs=1e-13)


def test_parity_and_origin():
    for order in (0, 1, 2, 3):
        assert bessel_j(order, 0.0) == (1.0 if order == 0 else 0.0)
        for x in (5.0, 50.0):
            sign = -1.0 if order % 2 else 1.0
            assert bessel_j(order, -x) == pytest.approx(sign * bessel_j(order, x))


def test_large_argument_decay():
    """``|J_n(x)| ≲ √(2/(πx))`` — the amplitude envelope."""
    for x in (50.0, 120.0, 350.0):
        envelope = math.sqrt(2.0 / (math.pi * x))
        for order in (0, 1, 3):
            assert abs(bessel_j(order, x)) <= envelope * 1.05


# -- input validation ------------------------------------------------------


def test_negative_order_is_refused():
    for function in (bessel_j, bessel_j_series, bessel_j_miller):
        with pytest.raises(ValueError, match="non-negative"):
            function(-1, 1.0)


def test_non_finite_argument_is_refused():
    for function in (bessel_j, bessel_j_series, bessel_j_miller):
        with pytest.raises(ValueError, match="finite"):
            function(1, float("nan"))
        with pytest.raises(ValueError, match="finite"):
            function(1, float("inf"))
