"""Integer-order Bessel functions with a numerical-domain guard (SDD §3.4a).

W-15 / guardrail P-1 / gate G-10.

The transmit pattern of HOBS eq. (3) is ``[J₁(μ)/(2μ) + 36·J₃(μ)/μ³]²``.  A
rewrite from the specification alone would reach for the ascending power
series, which is exact for small ``|x|`` and **catastrophically wrong** past
it: the largest intermediate term grows like ``e^|x|/√(2π|x|)``, so once it
passes ~1e16 the float64 mantissa has nothing left and the alternating sum
collapses into pure cancellation noise.  The live source records the damage
verbatim (``angle_aware_ee.py:938-953``)::

    _bessel_j_integer(3, 70) -> -5.8e11     true value -0.0154

Seventeen orders of magnitude, silently, with no exception raised.

**Why this matters here and not in the source project.**  The source note
left a standing condition:

    "the 1.62 margin is a property of the scenario constants (780 km
    altitude, 2.0 deg ring tilt); a future scenario change that lowers
    altitude or widens the ring tilt must re-verify
    mu_ceiling < _BESSEL_SERIES_MAX_ABS_X"

SDD F3 lowers the altitude, so the condition fired.  Re-verified in
``tests/test_w02_altitude_chain.py``: under this paper's **half-angle**
convention the ``μ`` **ceiling** reaches 64.80 at 780 km, 66.75 at 550 km,
and **67.32** at the corpus's measured 485 km.  Lowering the altitude
widens the horizon cone, so the ceiling goes up, not down.

Both branches are live.  ``μ = 2.07123·sin(θ)/sin(θ_3dB/2)`` runs from 0
on boresight to that ceiling at the horizon, so the main lobe is served by
the series and the far side lobes — every inter-satellite interference
term — by Miller.  A rewrite that used the series alone would keep the main
beam correct and return astronomical numbers for interference, which is the
worst possible failure shape: plausible where it is checked, absurd where
it is not.

Nothing in SDD §6 would have caught it: G-7 anchors ``G^R`` only, which is
why G-10 exists.
"""

from __future__ import annotations

import math

BESSEL_SERIES_MAX_ABS_X: float = 34.0
"""Above this the ascending series is abandoned for Miller recursion.

Ported unchanged from ``angle_aware_ee.py:954``.  The value is a property of
float64, not of the scenario: at ``x = 34`` the series still carries ~5e-4
absolute error, and by ``x ≈ 40`` it has none of the answer left.
"""


def bessel_j_miller(n: int, x: float) -> float:
    """``J_n(x)`` by Miller's downward recurrence — stable for every ``|x|``.

    Upward recurrence on ``J`` is unstable (it amplifies the ``Y``
    contamination); downward recurrence is self-correcting, because the same
    contamination decays.  The seed is arbitrary and divided out by the
    normalisation identity ``J₀(x) + 2·Σ_{k≥1} J_{2k}(x) = 1``.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if not math.isfinite(x):
        raise ValueError("x must be finite")
    if x < 0.0:
        return (-1.0 if n % 2 else 1.0) * bessel_j_miller(n, -x)
    if x == 0.0:
        return 1.0 if n == 0 else 0.0

    start = int(n + x + 20.0 + 10.0 * math.sqrt(x))
    if start % 2 == 1:
        # Keep the highest retained order even, so the J0 + 2*(J2+J4+...)
        # normaliser closes on a term it actually accumulated.
        start += 1

    j_hi = 0.0  # J_{start+1}
    j_cur = 1.0e-30  # J_{start}: arbitrary seed, cancelled by the normaliser
    target = 0.0
    norm = 0.0  # accumulates 2*(J_2 + J_4 + ...)
    for k in range(start, 0, -1):
        j_low = (2.0 * k / x) * j_cur - j_hi  # J_{k-1}
        if k - 1 == n:
            target = j_low
        if (k - 1) >= 2 and (k - 1) % 2 == 0:
            norm += 2.0 * j_low
        j_hi = j_cur
        j_cur = j_low
        if abs(j_cur) > 1.0e250:  # rescale away from the turning point
            scale = 1.0e-250
            j_cur *= scale
            j_hi *= scale
            target *= scale
            norm *= scale
    norm += j_cur  # + J_0
    return target / norm


def bessel_j_series(n: int, x: float) -> float:
    """``J_n(x)`` by the ascending power series.

    **Exported for the G-10 regression test only.**  Production code calls
    :func:`bessel_j`, which routes away from this past
    ``BESSEL_SERIES_MAX_ABS_X``.  Keeping it reachable is deliberate: the
    gate has to be able to demonstrate the failure it prevents, and a
    guardrail whose failure mode cannot be exhibited tends to get "cleaned
    up" by a later reader who cannot see why it is there.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if not math.isfinite(x):
        raise ValueError("x must be finite")
    if x == 0.0:
        return 1.0 if n == 0 else 0.0

    if n <= 20:
        term = (0.5 * x) ** n / math.factorial(n)
    else:
        # ``(x/2)**n / n!`` overflows int->float conversion long before the
        # ratio itself does.  Only the structural identity tests reach these
        # orders; production uses n = 1 and n = 3, which keep the exact
        # expression above.
        log_term = n * math.log(0.5 * abs(x)) - math.lgamma(n + 1.0)
        term = 0.0 if log_term < -700.0 else math.exp(log_term)
        if x < 0.0 and n % 2:
            term = -term
    total = term
    x2_over_4 = (x * x) / 4.0
    for m in range(200):
        term *= -x2_over_4 / ((m + 1) * (m + n + 1))
        total += term
        if abs(term) <= 1e-15 * max(1.0, abs(total)):
            break
    return float(total)


def bessel_j(n: int, x: float) -> float:
    """``J_n(x)`` — series for small ``|x|``, Miller recursion beyond.

    This is the only entry point production code may use.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if not math.isfinite(x):
        raise ValueError("x must be finite")
    if x == 0.0:
        return 1.0 if n == 0 else 0.0
    if abs(x) > BESSEL_SERIES_MAX_ABS_X:
        return bessel_j_miller(n, x)
    return bessel_j_series(n, x)


def uses_miller_recursion(x: float) -> bool:
    """Whether :func:`bessel_j` would route ``x`` to Miller recursion."""
    return abs(x) > BESSEL_SERIES_MAX_ABS_X


# ---------------------------------------------------------------------------
# Vectorised twin (W-17)
# ---------------------------------------------------------------------------
#
# The scalar :func:`bessel_j` above is the **reference**: G-10's anchors are
# measured against it and it stays untouched.  What follows evaluates the
# same two branches over a whole array, because the interference sums of
# (3.12a)/(3.12b) need ``G^T`` for every (victim user, radiating beam) pair
# and the scalar path costs ~28 us each — a hundred users against sixty
# radiating beams is 6000 evaluations per step before the candidate table is
# even touched.
#
# ``tests/test_w17_bessel_vectorised.py`` pins the two against each other
# elementwise across the whole live domain, including both sides of the
# routing threshold and the first four nulls of J1.


def bessel_j_array(orders, x):
    """``J_n(x)`` for several orders over an array, shape ``(len(orders), *x.shape)``.

    Same routing as :func:`bessel_j` — ascending series at or below
    ``BESSEL_SERIES_MAX_ABS_X``, Miller recursion beyond — applied
    elementwise, so a mixed array gets each element the branch the scalar
    function would have given it.
    """
    import numpy as np

    requested = [int(order) for order in orders]
    if any(order < 0 for order in requested):
        raise ValueError("n must be non-negative")
    values = np.asarray(x, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("x must be finite")

    magnitude = np.abs(values)
    out = np.zeros((len(requested),) + values.shape, dtype=np.float64)

    miller = magnitude > BESSEL_SERIES_MAX_ABS_X
    if np.any(miller):
        out[:, miller] = _miller_array(requested, magnitude[miller])
    if np.any(~miller):
        out[:, ~miller] = _series_array(requested, magnitude[~miller])

    # J_n(-x) = (-1)^n J_n(x); the scalar path takes the same route.
    negative = values < 0.0
    for index, order in enumerate(requested):
        if order % 2:
            out[index][negative] *= -1.0
    return out


def _miller_array(orders, x):
    """Downward recurrence over an array of **positive** ``x``.

    One shared starting order for the whole array rather than the scalar
    path's per-element ``n + x + 20 + 10*sqrt(x)``.  Starting higher than
    needed is free in accuracy terms — the seed is arbitrary and divided out
    — so taking the maximum is the conservative choice, not a shortcut.
    """
    import numpy as np

    highest = max(orders)
    peak = float(np.max(x))
    start = int(highest + peak + 20.0 + 10.0 * math.sqrt(peak))
    if start % 2 == 1:
        start += 1

    j_hi = np.zeros_like(x)
    j_cur = np.full_like(x, 1.0e-30)
    targets = {order: np.zeros_like(x) for order in orders}
    norm = np.zeros_like(x)

    wanted = set(orders)
    for k in range(start, 0, -1):
        j_low = (2.0 * k / x) * j_cur - j_hi
        if (k - 1) in wanted:
            targets[k - 1] = j_low
        if (k - 1) >= 2 and (k - 1) % 2 == 0:
            norm += 2.0 * j_low
        j_hi = j_cur
        j_cur = j_low
        overflow = np.abs(j_cur) > 1.0e250
        if np.any(overflow):
            # Rescale only the columns that need it, so a single large-|x|
            # element cannot cost the rest of the array its precision.
            scale = np.where(overflow, 1.0e-250, 1.0)
            j_cur = j_cur * scale
            j_hi = j_hi * scale
            norm = norm * scale
            for order in orders:
                targets[order] = targets[order] * scale
    norm = norm + j_cur
    return np.stack([targets[order] / norm for order in orders])


def _series_array(orders, x):
    """Ascending series over an array of ``|x| <= BESSEL_SERIES_MAX_ABS_X``.

    The scalar path stops early once a term stops mattering; here the loop
    runs its full length with the converged elements simply adding zeros,
    which is what keeps the two paths agreeing to the last bit rather than
    to wherever each happened to break.
    """
    import numpy as np

    rows = []
    x2_over_4 = (x * x) / 4.0
    for order in orders:
        if order <= 20:
            term = (0.5 * x) ** order / math.factorial(order)
        else:
            with np.errstate(divide="ignore"):
                log_term = order * np.log(np.maximum(0.5 * x, 1e-300)) - math.lgamma(
                    order + 1.0
                )
            term = np.where(log_term < -700.0, 0.0, np.exp(np.minimum(log_term, 700.0)))
        total = np.array(term, dtype=np.float64, copy=True)
        for m in range(200):
            term = term * (-x2_over_4 / ((m + 1) * (m + order + 1)))
            total = total + term
        rows.append(np.where(x == 0.0, 1.0 if order == 0 else 0.0, total))
    return np.stack(rows)
