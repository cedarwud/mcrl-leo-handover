"""The three scalarisation scales ``c_1``, ``c_2``, ``c_3``.

The scalarised reward is ``Σ_j ω_j · r_j / c_j``, so the **effective**
trade-off is ``ω_j / c_j`` — which means ``c_j`` decides how much of the
headline result each objective accounts for, just as directly as ``ω_j``
does.  Freezing ``Ω`` while leaving ``c`` to be computed later would freeze
half of a ratio.

**Why the three rules differ, and why that is not arbitrary.**  The common
*intent* is uniform: each normalised objective should span roughly unit
range so that ``Ω = (0.5, 0.3, 0.2)`` means what Table I says.  What differs
is what each objective is bounded by:

======  ==========================  ==============================
``r_2``  bounded **by construction** (3.27) gives {0, −φ1, −φ2}
``r_3``  bounded **by the population** a head count with a modest tail
``r_1``  **unbounded**                a positive ratio with a right tail
======  ==========================  ==============================

So ``c_2`` is an analytic bound needing no measurement, while ``c_1`` and
``c_3`` are p95s of their own distributions — robust to the tail that the
max would track.

⚠ **The p95 rule cannot be transplanted to ``r_2``.**  Its signed p95 is
**0**, because most steps carry no handover, so "divide by the p95" would
divide by zero.  The sign convention puts ``r_2``'s informative end at p05,
and p05 is exactly ``−φ2`` by construction — which is why the analytic
bound is both simpler and exact.

**What this replaces.**  Measured ``r_1`` has a median of 5.09e5 against a
legacy ``c_1`` of 1.17e8 — **230× too large**.  Under the legacy value the
calibrated ``r_1`` median would be 0.0043 against ``|r_3|``'s 0.500, and the
first objective would be crushed.  Uncalibrated is worse still: the
``ω_1 r_1`` term is 4.1e5 times the ``ω_3 r_3`` term, and the
three-objective problem degenerates into single-objective ``r_1``.
"""

from __future__ import annotations

from ..env.action_contract import PHI2
from ..env.service import R3_CALIBRATION_SCALE

C1_SCALE: float = 2471140.576
"""``c_1`` — **D**, the p95 of ``r_1`` over served steps (probe P3).

Not rounded, unlike ``c_3``: ``r_3`` is a head count and rounding keeps its
scale a countable quantity, while ``r_1`` is a continuous bit/J ratio with
no unit to round to.  Rounding it would need its own justification and has
none.

⚠ **Provenance disclosure.**  P3 had already run when the Q-F rule was
written, so ``r_1``'s distribution was visible — "the rule preceded the
numbers" is not literally true here the way it is for ``c_3``.  What
protects it: the rule is structural (unbounded ⇒ p95, bounded ⇒ the bound),
it is the *same* rule already frozen for ``c_3`` — ⚠ ``c_1`` and
``c_3`` share the p95 rule while ``c_2`` is separate because its
distribution shape forbids it, **not** all three alike — and it was
not selected from among alternatives by checking which produced a
preferred balance.  That last point is the one that matters: choosing
among candidate rules by their output is how the leak actually happens.
"""

C2_SCALE: float = PHI2
"""``c_2 = φ2 = 1.0`` — **D**, and closed by **no probe at all**.

``|r_2| ≤ φ2`` by construction, so dividing by ``φ2`` normalises it to
``[0, 1]`` exactly.  It was determined the moment ``φ1`` and ``φ2`` were
frozen; measuring it would only recover a number already known.
"""

C3_SCALE: float = float(R3_CALIBRATION_SCALE)
"""``c_3 = 6`` — **D**, the p95 of ``|r_3|`` rounded (probe P3, Q-D).

Imported rather than restated: ``env.service`` owns it, and a second copy
is how two numbers that must agree stop agreeing.
"""

REWARD_SCALES: tuple[float, float, float] = (C1_SCALE, C2_SCALE, C3_SCALE)

REWARD_SCALES_ARE_FROZEN: bool = True
"""Whether ``c_1`` and ``c_2`` have been decided.  **True since 2026-08-23.**

``c_3`` has its own flag in ``env.service`` because Q-D is its own
pre-registered question; this one covers Q-F and Q-G.  Both are read by
``prereg.open_questions()`` from the modules that own them, never restated.
"""


def calibrated_contribution(
    typical_magnitudes: tuple[float, float, float],
    objective_weights: tuple[float, float, float],
) -> tuple[float, float, float]:
    """``ω_j · |r_j| / c_j`` — what each objective actually contributes.

    The number that matters when judging whether a scalarisation is
    balanced.  At the measured typicals (5.09e5, 0.112, 3.0) and
    ``Ω = (0.5, 0.3, 0.2)`` this gives **0.103 / 0.034 / 0.100**: the first
    and third objectives near-equal, the second smaller because a handover
    penalty only fires occasionally — which is the intended shape, not an
    imbalance.
    """
    return tuple(
        weight * magnitude / scale
        for weight, magnitude, scale in zip(
            objective_weights, typical_magnitudes, REWARD_SCALES
        )
    )
