"""Formula-only backup targets for the V0.7 C2 parallel screen.

The primary V0.7 candidate (P0) values the focal user's realised successor
effect.  This module defines two *pre-outcome* backup estimands that can be
computed from the same sealed physical anchors without waiting for P0 to
fail:

* B1 -- focal segment-continuation EE surplus over successor offsets; and
* B2 -- focal successor option-set EE-surplus value.

Both targets remain in native bit-equivalent EE-surplus units under the one
frozen ``lambda_bits_per_j``.  They consume already matched measurements and
do not select anchors, simulate branches, train Q2, or choose a winning arm.
The source runner remains responsible for canonical multi-user physics,
common random numbers, a precommitted non-focal action tape, and outcome-blind
retention.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError


V07_C2_B1_TARGET_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-focal-segment-continuation-target-v1"
)
V07_C2_B2_TARGET_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-successor-option-set-target-v1"
)


@dataclass(frozen=True)
class FocalSegmentContinuationSurplus:
    """B1 target and its signed successor-offset decomposition."""

    z2_focal_segment_surplus_bits: float
    successor_offsets: tuple[int, ...]
    offset_surplus_bits: tuple[float, ...]
    offset_rate_delta_bits: tuple[float, ...]
    offset_marginal_energy_delta_j: tuple[float, ...]
    candidate_focal_rates_bps: tuple[float, ...]
    reference_focal_rates_bps: tuple[float, ...]
    candidate_focal_marginal_power_w: tuple[float, ...]
    reference_focal_marginal_power_w: tuple[float, ...]
    candidate_full_power_w: tuple[float, ...]
    candidate_without_focal_power_w: tuple[float, ...]
    reference_full_power_w: tuple[float, ...]
    reference_without_focal_power_w: tuple[float, ...]
    lambda_bits_per_j: float
    interval_s: float
    schema: str = V07_C2_B1_TARGET_SCHEMA


@dataclass(frozen=True)
class SuccessorOptionSetSurplus:
    """B2 difference between candidate/reference successor option values."""

    z2_successor_option_set_surplus_bits: float
    successor_offset: int
    candidate_option_value_bits: float
    reference_option_value_bits: float
    candidate_best_action: int
    reference_best_action: int
    candidate_action_surplus_bits: tuple[float, ...]
    reference_action_surplus_bits: tuple[float, ...]
    candidate_action_rates_bps: tuple[float, ...]
    reference_action_rates_bps: tuple[float, ...]
    candidate_legal_mask: tuple[bool, ...]
    reference_legal_mask: tuple[bool, ...]
    candidate_action_marginal_power_w: tuple[float, ...]
    reference_action_marginal_power_w: tuple[float, ...]
    candidate_action_full_power_w: tuple[float, ...]
    candidate_action_without_focal_power_w: tuple[float, ...]
    reference_action_full_power_w: tuple[float, ...]
    reference_action_without_focal_power_w: tuple[float, ...]
    lambda_bits_per_j: float
    interval_s: float
    schema: str = V07_C2_B2_TARGET_SCHEMA


def _positive(value: object, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise MCRLContractError(f"{field} must be finite and positive") from error
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise MCRLContractError(f"{field} must be finite and positive")
    return parsed


def _vector(value: object, *, field: str, nonnegative: bool = True) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise MCRLContractError(f"{field} must be a finite vector") from error
    if result.ndim != 1 or result.size < 1 or not np.all(np.isfinite(result)):
        raise MCRLContractError(f"{field} must be a nonempty finite vector")
    if nonnegative and np.any(result < 0.0):
        raise MCRLContractError(f"{field} must be non-negative")
    return result


def _same_shape(*values: np.ndarray) -> None:
    if any(value.shape != values[0].shape for value in values[1:]):
        raise MCRLContractError("matched C2 vectors must have identical shapes")


def focal_segment_continuation_target(
    *,
    lambda_bits_per_j: float,
    interval_s: float,
    candidate_focal_rates_bps: object,
    reference_focal_rates_bps: object,
    candidate_full_power_w: object,
    candidate_without_focal_power_w: object,
    reference_full_power_w: object,
    reference_without_focal_power_w: object,
) -> FocalSegmentContinuationSurplus:
    """Return B1 over the registered successor offsets ``k=1,2,3``.

    Focal marginal network power is reconstructed here as
    ``P_full - P_without_focal``.  Accepting and retaining both raw terms keeps
    the formula receipt independently verifiable.  The caller must not include
    opening offset zero.
    """

    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    interval = _positive(interval_s, field="interval_s")
    candidate_rate = _vector(
        candidate_focal_rates_bps, field="candidate_focal_rates_bps"
    )
    reference_rate = _vector(
        reference_focal_rates_bps, field="reference_focal_rates_bps"
    )
    candidate_full = _vector(
        candidate_full_power_w,
        field="candidate_full_power_w",
    )
    candidate_without = _vector(
        candidate_without_focal_power_w,
        field="candidate_without_focal_power_w",
    )
    reference_full = _vector(
        reference_full_power_w,
        field="reference_full_power_w",
    )
    reference_without = _vector(
        reference_without_focal_power_w,
        field="reference_without_focal_power_w",
    )
    _same_shape(
        candidate_rate,
        reference_rate,
        candidate_full,
        candidate_without,
        reference_full,
        reference_without,
    )
    if candidate_rate.size != 3:
        raise MCRLContractError("B1 requires exactly three successor offsets k=1,2,3")

    candidate_power = candidate_full - candidate_without
    reference_power = reference_full - reference_without

    with np.errstate(over="ignore", invalid="ignore"):
        rate_delta = interval * (candidate_rate - reference_rate)
        energy_delta = interval * (candidate_power - reference_power)
        surplus = rate_delta - multiplier * energy_delta
    if not all(np.all(np.isfinite(value)) for value in (rate_delta, energy_delta, surplus)):
        raise MCRLContractError("B1 target arithmetic is non-finite")
    target = float(math.fsum(float(value) for value in surplus))
    if not math.isfinite(target):
        raise MCRLContractError("B1 target arithmetic is non-finite")
    return FocalSegmentContinuationSurplus(
        z2_focal_segment_surplus_bits=target,
        successor_offsets=(1, 2, 3),
        offset_surplus_bits=tuple(float(value) for value in surplus.tolist()),
        offset_rate_delta_bits=tuple(float(value) for value in rate_delta.tolist()),
        offset_marginal_energy_delta_j=tuple(
            float(value) for value in energy_delta.tolist()
        ),
        candidate_focal_rates_bps=tuple(
            float(value) for value in candidate_rate.tolist()
        ),
        reference_focal_rates_bps=tuple(
            float(value) for value in reference_rate.tolist()
        ),
        candidate_focal_marginal_power_w=tuple(
            float(value) for value in candidate_power.tolist()
        ),
        reference_focal_marginal_power_w=tuple(
            float(value) for value in reference_power.tolist()
        ),
        candidate_full_power_w=tuple(float(value) for value in candidate_full.tolist()),
        candidate_without_focal_power_w=tuple(
            float(value) for value in candidate_without.tolist()
        ),
        reference_full_power_w=tuple(float(value) for value in reference_full.tolist()),
        reference_without_focal_power_w=tuple(
            float(value) for value in reference_without.tolist()
        ),
        lambda_bits_per_j=multiplier,
        interval_s=interval,
    )


def _mask(value: object, *, field: str, size: int) -> np.ndarray:
    result = np.asarray(value)
    if result.dtype != np.bool_ or result.shape != (size,):
        raise MCRLContractError(f"{field} must be a Boolean vector of length {size}")
    return result


def _option_value(
    *,
    rates_bps: np.ndarray,
    marginal_power_w: np.ndarray,
    legal_mask: np.ndarray,
    multiplier: float,
    interval: float,
) -> tuple[float, int, np.ndarray]:
    with np.errstate(over="ignore", invalid="ignore"):
        action_surplus = interval * (rates_bps - multiplier * marginal_power_w)
    if not np.all(np.isfinite(action_surplus)):
        raise MCRLContractError("B2 action-surplus arithmetic is non-finite")
    # A physics-only no-op is always an available zero-value outside action
    # index space.  It makes an empty or uniformly harmful option set finite
    # without pretending that an illegal beam action was executable.
    best_value = 0.0
    best_action = -1
    for action in np.flatnonzero(legal_mask).tolist():
        value = float(action_surplus[action])
        if value > best_value:
            best_value = value
            best_action = int(action)
    return best_value, best_action, action_surplus


def successor_option_set_target(
    *,
    lambda_bits_per_j: float,
    interval_s: float,
    candidate_action_rates_bps: object,
    candidate_action_full_power_w: object,
    candidate_action_without_focal_power_w: object,
    candidate_legal_mask: object,
    reference_action_rates_bps: object,
    reference_action_full_power_w: object,
    reference_action_without_focal_power_w: object,
    reference_legal_mask: object,
) -> SuccessorOptionSetSurplus:
    """Return B2 from branch-local successor focal-action surfaces.

    The surface for each branch is evaluated at successor offset one while a
    precommitted non-focal vector is held fixed.  The target values the best
    physically legal focal option (or the zero-value no-op), not a learned
    continuation policy.
    """

    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    interval = _positive(interval_s, field="interval_s")
    candidate_rate = _vector(
        candidate_action_rates_bps, field="candidate_action_rates_bps"
    )
    candidate_full = _vector(
        candidate_action_full_power_w,
        field="candidate_action_full_power_w",
    )
    candidate_without = _vector(
        candidate_action_without_focal_power_w,
        field="candidate_action_without_focal_power_w",
    )
    reference_rate = _vector(
        reference_action_rates_bps, field="reference_action_rates_bps"
    )
    reference_full = _vector(
        reference_action_full_power_w,
        field="reference_action_full_power_w",
    )
    reference_without = _vector(
        reference_action_without_focal_power_w,
        field="reference_action_without_focal_power_w",
    )
    _same_shape(
        candidate_rate,
        candidate_full,
        candidate_without,
        reference_rate,
        reference_full,
        reference_without,
    )
    if candidate_rate.size != NUM_ACTIONS:
        raise MCRLContractError(
            f"B2 requires the exact native {NUM_ACTIONS}-action surface"
        )
    candidate_power = candidate_full - candidate_without
    reference_power = reference_full - reference_without
    candidate_mask = _mask(
        candidate_legal_mask, field="candidate_legal_mask", size=candidate_rate.size
    )
    reference_mask = _mask(
        reference_legal_mask, field="reference_legal_mask", size=candidate_rate.size
    )
    candidate_value, candidate_action, candidate_surface = _option_value(
        rates_bps=candidate_rate,
        marginal_power_w=candidate_power,
        legal_mask=candidate_mask,
        multiplier=multiplier,
        interval=interval,
    )
    reference_value, reference_action, reference_surface = _option_value(
        rates_bps=reference_rate,
        marginal_power_w=reference_power,
        legal_mask=reference_mask,
        multiplier=multiplier,
        interval=interval,
    )
    target = candidate_value - reference_value
    if not math.isfinite(target):
        raise MCRLContractError("B2 target arithmetic is non-finite")
    return SuccessorOptionSetSurplus(
        z2_successor_option_set_surplus_bits=float(target),
        successor_offset=1,
        candidate_option_value_bits=float(candidate_value),
        reference_option_value_bits=float(reference_value),
        candidate_best_action=candidate_action,
        reference_best_action=reference_action,
        candidate_action_surplus_bits=tuple(
            float(value) for value in candidate_surface.tolist()
        ),
        reference_action_surplus_bits=tuple(
            float(value) for value in reference_surface.tolist()
        ),
        candidate_action_rates_bps=tuple(
            float(value) for value in candidate_rate.tolist()
        ),
        reference_action_rates_bps=tuple(
            float(value) for value in reference_rate.tolist()
        ),
        candidate_legal_mask=tuple(bool(value) for value in candidate_mask.tolist()),
        reference_legal_mask=tuple(bool(value) for value in reference_mask.tolist()),
        candidate_action_marginal_power_w=tuple(
            float(value) for value in candidate_power.tolist()
        ),
        reference_action_marginal_power_w=tuple(
            float(value) for value in reference_power.tolist()
        ),
        candidate_action_full_power_w=tuple(
            float(value) for value in candidate_full.tolist()
        ),
        candidate_action_without_focal_power_w=tuple(
            float(value) for value in candidate_without.tolist()
        ),
        reference_action_full_power_w=tuple(
            float(value) for value in reference_full.tolist()
        ),
        reference_action_without_focal_power_w=tuple(
            float(value) for value in reference_without.tolist()
        ),
        lambda_bits_per_j=multiplier,
        interval_s=interval,
    )


__all__ = [
    "FocalSegmentContinuationSurplus",
    "SuccessorOptionSetSurplus",
    "V07_C2_B1_TARGET_SCHEMA",
    "V07_C2_B2_TARGET_SCHEMA",
    "focal_segment_continuation_target",
    "successor_option_set_target",
]
