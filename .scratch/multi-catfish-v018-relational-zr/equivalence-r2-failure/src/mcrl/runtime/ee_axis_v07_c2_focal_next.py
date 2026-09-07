"""Formula-first V0.7 C2 focal-next EE-surplus target.

V0.6 attributed the entire next-slot network response to one focal opening
action.  The sealed negative result showed that this network-total label did
not generalise from the causal state.  V0.7 keeps C2's temporal role but limits
its public target to the focal user's next-slot rate and marginal network
power.  Non-focal next-slot continuation cascades are deliberately outside the
learned target.

This module is formula-only.  It does not select actions, run a continuation,
train Q2, or change the canonical ratio-of-sums EE endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from ..errors import MCRLContractError


V07_C2_TARGET_SCHEMA = "multi-catfish-mcrl-v07-c2-focal-next-target-v1"


@dataclass(frozen=True)
class FocalNextSurplus:
    """One matched focal-next C2 target in native bit units."""

    z2_focal_next_surplus_bits: float
    focal_next_rate_delta_bits: float
    focal_next_marginal_energy_delta_j: float
    candidate_focal_rate_bps: float
    reference_focal_rate_bps: float
    candidate_focal_marginal_power_w: float
    reference_focal_marginal_power_w: float
    candidate_full_power_w: float
    candidate_without_focal_power_w: float
    reference_full_power_w: float
    reference_without_focal_power_w: float
    lambda_bits_per_j: float
    interval_s: float
    schema: str = V07_C2_TARGET_SCHEMA


def _finite_nonnegative(value: float, *, field: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise MCRLContractError(f"{field} must be finite and non-negative")
    return result


def _positive(value: float, *, field: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise MCRLContractError(f"{field} must be finite and strictly positive")
    return result


def focal_next_surplus_target(
    *,
    lambda_bits_per_j: float,
    interval_s: float,
    candidate_focal_rate_bps: float,
    reference_focal_rate_bps: float,
    candidate_full_power_w: float,
    candidate_without_focal_power_w: float,
    reference_full_power_w: float,
    reference_without_focal_power_w: float,
) -> FocalNextSurplus:
    """Return the V0.7 focal-attributable next-slot C2 target.

    For branch ``b`` in ``{C, M}``, the focal marginal power is

    ``p[b,u] = P_full[b] - P_without_focal[b]``.

    The without-focal evaluation must keep every non-focal action fixed and
    replace only the focal next-slot action by a physics-only no-op.  The
    caller is responsible for matched branch states, the common keyed random
    field, and a non-committing evaluation.
    """

    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    interval = _positive(interval_s, field="interval_s")
    candidate_rate = _finite_nonnegative(
        candidate_focal_rate_bps,
        field="candidate_focal_rate_bps",
    )
    reference_rate = _finite_nonnegative(
        reference_focal_rate_bps,
        field="reference_focal_rate_bps",
    )
    candidate_full = _finite_nonnegative(
        candidate_full_power_w,
        field="candidate_full_power_w",
    )
    candidate_without = _finite_nonnegative(
        candidate_without_focal_power_w,
        field="candidate_without_focal_power_w",
    )
    reference_full = _finite_nonnegative(
        reference_full_power_w,
        field="reference_full_power_w",
    )
    reference_without = _finite_nonnegative(
        reference_without_focal_power_w,
        field="reference_without_focal_power_w",
    )

    candidate_marginal = candidate_full - candidate_without
    reference_marginal = reference_full - reference_without
    # A negative marginal value is not clipped.  Shared-beam activation,
    # interference, and service resolution are nonlinear; the matched physics
    # result, including its sign, is the estimand.
    rate_delta_bits = interval * (candidate_rate - reference_rate)
    marginal_energy_delta_j = interval * (
        candidate_marginal - reference_marginal
    )
    target = rate_delta_bits - multiplier * marginal_energy_delta_j
    if not all(
        math.isfinite(value)
        for value in (
            candidate_marginal,
            reference_marginal,
            rate_delta_bits,
            marginal_energy_delta_j,
            target,
        )
    ):
        raise MCRLContractError("focal-next target arithmetic is non-finite")

    return FocalNextSurplus(
        z2_focal_next_surplus_bits=float(target),
        focal_next_rate_delta_bits=float(rate_delta_bits),
        focal_next_marginal_energy_delta_j=float(marginal_energy_delta_j),
        candidate_focal_rate_bps=candidate_rate,
        reference_focal_rate_bps=reference_rate,
        candidate_focal_marginal_power_w=float(candidate_marginal),
        reference_focal_marginal_power_w=float(reference_marginal),
        candidate_full_power_w=candidate_full,
        candidate_without_focal_power_w=candidate_without,
        reference_full_power_w=reference_full,
        reference_without_focal_power_w=reference_without,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
    )


__all__ = [
    "FocalNextSurplus",
    "V07_C2_TARGET_SCHEMA",
    "focal_next_surplus_target",
]
