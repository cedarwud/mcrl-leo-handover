"""W-17 — the vectorised Bessel must equal the scalar one, elementwise.

``bessel_j`` is the reference: G-10's anchors are measured against it and it
was not touched.  ``bessel_j_array`` exists only because the interference
sums need ``G^T`` for every (victim, radiating beam) pair, which the scalar
path serves at ~28 us each.

A speed-up that changes a number is not a speed-up, so the agreement is
pinned across the whole live domain rather than sampled: both sides of the
``|x| > 34`` routing threshold, the first four zeros of ``J₁`` (where
cancellation is worst and a relative comparison is meaningless), the
negative half, and the ``mu`` ceiling of 67.3 the horizon actually reaches.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.antenna import G0_LINEAR, THETA_3DB_DEG, mu_of, transmit_gain_linear
from mcrl.runtime.bessel import (
    BESSEL_SERIES_MAX_ABS_X,
    bessel_j,
    bessel_j_array,
    uses_miller_recursion,
)

J1_ZEROS = (3.8317059702, 7.0155866698, 10.1734681351, 13.3236919363)
"""The first four zeros of ``J₁``: where the answer is 0 and every digit of
the input matters.  A relative tolerance is undefined here, so these are
checked absolutely."""

MU_CEILING = 67.4
"""``μ`` at the horizon under this paper's half-angle convention."""


def _domain() -> np.ndarray:
    return np.concatenate(
        [
            np.linspace(0.0, BESSEL_SERIES_MAX_ABS_X, 400),
            np.linspace(BESSEL_SERIES_MAX_ABS_X, MU_CEILING, 400),
            np.array(J1_ZEROS),
            np.array([-5.0, -40.0, -MU_CEILING, 1e-12, 0.0]),
        ]
    )


def _scalar(orders, values):
    return np.array(
        [[bessel_j(order, float(value)) for value in values] for order in orders]
    )


def test_the_two_paths_agree_across_the_whole_live_domain():
    values = _domain()
    reference = _scalar((1, 3), values)
    vectorised = bessel_j_array((1, 3), values)
    assert vectorised.shape == reference.shape
    error = np.abs(vectorised - reference)
    assert float(error.max()) < 1e-14, (
        f"max absolute divergence {float(error.max()):.3e}"
    )


def test_they_agree_relatively_where_the_value_is_not_a_zero():
    values = _domain()
    reference = _scalar((1, 3), values)
    vectorised = bessel_j_array((1, 3), values)
    significant = np.abs(reference) > 1e-8
    relative = np.abs(vectorised[significant] - reference[significant]) / np.abs(
        reference[significant]
    )
    assert float(relative.max()) < 1e-11


def test_both_branches_of_the_routing_are_exercised():
    """A test that only ever hit one branch would prove nothing about the other."""
    values = _domain()
    assert np.any([uses_miller_recursion(float(v)) for v in values])
    assert np.any([not uses_miller_recursion(float(v)) for v in values])


def test_the_threshold_itself_is_on_the_series_side():
    """``> 34``, not ``>= 34`` — the boundary belongs to the series."""
    assert not uses_miller_recursion(BESSEL_SERIES_MAX_ABS_X)
    exact = np.array([BESSEL_SERIES_MAX_ABS_X])
    assert bessel_j_array((1,), exact)[0, 0] == pytest.approx(
        bessel_j(1, BESSEL_SERIES_MAX_ABS_X), abs=1e-15
    )


def test_the_sign_symmetry_holds():
    """``J_n(-x) = (-1)^n J_n(x)`` on the vectorised path too."""
    positive = np.array([0.5, 5.0, 40.0, 67.0])
    plus = bessel_j_array((1, 2, 3), positive)
    minus = bessel_j_array((1, 2, 3), -positive)
    assert np.allclose(minus[0], -plus[0], atol=1e-15)
    assert np.allclose(minus[1], plus[1], atol=1e-15)
    assert np.allclose(minus[2], -plus[2], atol=1e-15)


def test_zero_is_exact():
    values = bessel_j_array((0, 1, 3), np.array([0.0]))
    assert values[0, 0] == 1.0
    assert values[1, 0] == 0.0
    assert values[2, 0] == 0.0


def test_the_transmit_gain_is_unchanged_by_the_vectorisation():
    """The number G-10 anchors, recomputed the slow way and compared."""
    angles = np.concatenate([np.linspace(0.0, 90.0, 600), np.array([0.0, 1.66, 3.32])])
    mu = mu_of(angles, theta_3db_deg=THETA_3DB_DEG)
    reference = np.empty(mu.shape)
    for index in np.ndindex(mu.shape):
        value = float(mu[index])
        if abs(value) < 1e-10:
            reference[index] = G0_LINEAR
            continue
        bracket = bessel_j(1, value) / (2.0 * value) + 36.0 * bessel_j(
            3, value
        ) / value**3
        reference[index] = G0_LINEAR * bracket * bracket

    assert np.allclose(transmit_gain_linear(angles), reference, atol=1e-15, rtol=0.0)


def test_boresight_is_the_exact_peak_gain():
    """``F(0) = 1``: the bracket is a genuine 0/0 and the limit is exact."""
    assert float(transmit_gain_linear(np.array([0.0]))[0]) == G0_LINEAR
    # And just inside the epsilon, where the limit branch takes over.
    assert float(transmit_gain_linear(np.array([1e-12]))[0]) == G0_LINEAR


def test_shapes_are_preserved():
    assert transmit_gain_linear(np.zeros((3, 4))).shape == (3, 4)
    assert transmit_gain_linear(np.zeros((2, 3, 4))).shape == (2, 3, 4)
    assert np.shape(transmit_gain_linear(np.float64(5.0))) == ()


def test_a_non_finite_input_is_refused():
    with pytest.raises(ValueError, match="finite"):
        bessel_j_array((1,), np.array([np.nan]))
    with pytest.raises(ValueError, match="finite"):
        bessel_j_array((1,), np.array([np.inf]))


def test_a_negative_order_is_refused():
    with pytest.raises(ValueError, match="non-negative"):
        bessel_j_array((-1,), np.array([1.0]))


def test_the_vectorised_path_is_actually_faster():
    """The whole reason it exists, asserted rather than assumed.

    A generous margin: this is a guard against the vectorisation silently
    degenerating into a Python loop, not a benchmark.
    """
    import time

    values = np.linspace(0.1, MU_CEILING, 4000)

    start = time.perf_counter()
    bessel_j_array((1, 3), values)
    vector_s = time.perf_counter() - start

    start = time.perf_counter()
    _scalar((1, 3), values[:400])
    scalar_s = (time.perf_counter() - start) * 10.0

    assert vector_s < scalar_s
