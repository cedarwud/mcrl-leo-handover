"""Pure metric and adjudication helpers for the frozen V0.23 LC-SRS gate.

This module deliberately has no simulator, learner, filesystem, or random
number dependency.  Both the execution adapter and an independent verifier
can therefore recompute the contract's numerical comparisons without trusting
persisted PASS booleans.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import numpy as np

from ..errors import MCRLContractError


V023_SIGN_THRESHOLD = 0.02
V023_PAIR_COVERAGE_PREDICATES = ("pair_coverage",)
V023_PHYSICS_PREDICATES = (
    "mechanics",
    "physical_signature",
    "teacher_composition",
)
V023_OBSERVABILITY_PREDICATES = (
    "interface_a",
    "target_support",
    "held_out_learner",
    "world_stability",
)
V023_COMPOSITION_PREDICATES = (
    "action_exposure",
    "pair_composition",
    "topology_consistency",
    "learned_composition",
    "service",
)
V023_REQUIRED_PREDICATES = (
    *V023_PAIR_COVERAGE_PREDICATES,
    *V023_PHYSICS_PREDICATES,
    *V023_OBSERVABILITY_PREDICATES,
    *V023_COMPOSITION_PREDICATES,
)
V023_C3_DECISIONS = (
    "INVALID_RUN",
    "INSUFFICIENT_PAIRS",
    "STOP_PHYSICS",
    "STOP_OBSERVABILITY",
    "REDESIGN_INTERFACE",
    "GO_FIXED_LEARNER_SCREEN_CONTRACT",
)
V023_CONTEXT_STATUSES = (
    "CONTEXT_DIAGNOSTICS_PASS",
    "HOLD_C1",
    "HOLD_C2",
    "HOLD_C1_C2",
)


class LCSRSC3GateMetricError(MCRLContractError):
    """A persisted value cannot satisfy the frozen gate arithmetic."""


def comparison_tolerance(*values: float) -> float:
    """Return Section 12's scale-aware floating comparison tolerance."""

    if not values:
        raise ValueError("comparison_tolerance needs at least one value")
    converted = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in converted):
        raise LCSRSC3GateMetricError("comparison tolerance inputs must be finite")
    return max(
        1.0e-12,
        1024.0
        * np.finfo(np.float64).eps
        * max(1.0, *(abs(value) for value in converted)),
    )


def strict_direction(left: float, right: float) -> int:
    """Return +1, 0, or -1 using the frozen scale-aware tie rule."""

    left_value = float(left)
    right_value = float(right)
    tolerance = comparison_tolerance(left_value, right_value)
    difference = left_value - right_value
    if difference > tolerance:
        return 1
    if difference < -tolerance:
        return -1
    return 0


@dataclass(frozen=True)
class RatioDirection:
    """Exact ratio-of-sums direction represented by its cross product."""

    direction: int
    cross_product: float
    tolerance: float
    left_ee: float
    right_ee: float


def ratio_of_sums_direction(
    *,
    left_bits: float,
    left_energy_j: float,
    right_bits: float,
    right_energy_j: float,
) -> RatioDirection:
    """Compare B_l/E_l and B_r/E_r without subtracting rounded ratios."""

    values = tuple(
        float(value)
        for value in (left_bits, left_energy_j, right_bits, right_energy_j)
    )
    if not all(math.isfinite(value) for value in values):
        raise LCSRSC3GateMetricError("ratio-of-sums inputs must be finite")
    lb, le, rb, re = values
    if lb < 0.0 or rb < 0.0 or le <= 0.0 or re <= 0.0:
        raise LCSRSC3GateMetricError(
            "ratio-of-sums needs nonnegative bits and strictly positive energy"
        )
    left_product = lb * re
    right_product = rb * le
    if not math.isfinite(left_product) or not math.isfinite(right_product):
        raise LCSRSC3GateMetricError("ratio cross product overflowed")
    tolerance = comparison_tolerance(left_product, right_product)
    cross_product = left_product - right_product
    direction = 1 if cross_product > tolerance else -1 if cross_product < -tolerance else 0
    return RatioDirection(
        direction=direction,
        cross_product=cross_product,
        tolerance=tolerance,
        left_ee=lb / le,
        right_ee=rb / re,
    )


def _midranks(values: np.ndarray) -> np.ndarray:
    """Assign exact-tie average ranks using deterministic stable ordering."""

    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise LCSRSC3GateMetricError("rank input must be one finite vector")
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def tie_aware_spearman(
    left: Sequence[float] | np.ndarray,
    right: Sequence[float] | np.ndarray,
) -> float | None:
    """Return tie-aware Spearman rho, or ``None`` for a failed denominator."""

    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    if left_array.ndim != 1 or right_array.shape != left_array.shape:
        raise LCSRSC3GateMetricError("Spearman inputs must be aligned vectors")
    if left_array.size < 2 or not np.all(np.isfinite(left_array)) or not np.all(
        np.isfinite(right_array)
    ):
        return None
    left_rank = _midranks(left_array)
    right_rank = _midranks(right_array)
    left_centered = left_rank - float(np.mean(left_rank))
    right_centered = right_rank - float(np.mean(right_rank))
    denominator = math.sqrt(
        float(np.dot(left_centered, left_centered))
        * float(np.dot(right_centered, right_centered))
    )
    if denominator == 0.0 or not math.isfinite(denominator):
        return None
    result = float(np.dot(left_centered, right_centered) / denominator)
    return result if math.isfinite(result) else None


@dataclass(frozen=True)
class SignAccuracy:
    """Complete denominator receipt for the frozen nontrivial-target sign test."""

    threshold: float
    total_rows: int
    evaluated_rows: int
    excluded_rows: int
    correct_rows: int
    accuracy: float | None


def sign_accuracy(
    predictions: Sequence[float] | np.ndarray,
    targets: Sequence[float] | np.ndarray,
    *,
    threshold: float = V023_SIGN_THRESHOLD,
) -> SignAccuracy:
    """Score signs only where ``abs(target) >= 0.02``; zero predictions fail."""

    predicted = np.asarray(predictions, dtype=np.float64)
    truth = np.asarray(targets, dtype=np.float64)
    if predicted.ndim != 1 or truth.shape != predicted.shape:
        raise LCSRSC3GateMetricError("sign inputs must be aligned vectors")
    if not np.all(np.isfinite(predicted)) or not np.all(np.isfinite(truth)):
        raise LCSRSC3GateMetricError("sign inputs must be finite")
    if threshold != V023_SIGN_THRESHOLD:
        raise LCSRSC3GateMetricError("V0.23 sign threshold is frozen at 0.02")
    eligible = np.abs(truth) >= threshold
    denominator = int(np.count_nonzero(eligible))
    predicted_sign = np.sign(predicted[eligible])
    target_sign = np.sign(truth[eligible])
    correct = int(np.count_nonzero(predicted_sign == target_sign))
    return SignAccuracy(
        threshold=threshold,
        total_rows=int(truth.size),
        evaluated_rows=denominator,
        excluded_rows=int(truth.size - denominator),
        correct_rows=correct,
        accuracy=(correct / denominator) if denominator else None,
    )


def context_status(*, c1_pass: bool, c2_pass: bool) -> str:
    """Return the independent Section 9 C1/C2 context token."""

    if type(c1_pass) is not bool or type(c2_pass) is not bool:
        raise TypeError("context predicates must be exact booleans")
    if c1_pass and c2_pass:
        return "CONTEXT_DIAGNOSTICS_PASS"
    if not c1_pass and c2_pass:
        return "HOLD_C1"
    if c1_pass and not c2_pass:
        return "HOLD_C2"
    return "HOLD_C1_C2"


def adjudicate_c3(
    predicates: Mapping[str, bool],
    *,
    integrity_pass: bool,
) -> str:
    """Apply the exact Section 14 decision precedence to a complete table."""

    if type(integrity_pass) is not bool:
        raise TypeError("integrity_pass must be an exact boolean")
    if not integrity_pass:
        return "INVALID_RUN"
    missing = tuple(name for name in V023_REQUIRED_PREDICATES if name not in predicates)
    extra = tuple(sorted(set(predicates) - set(V023_REQUIRED_PREDICATES)))
    if missing or extra:
        raise LCSRSC3GateMetricError(
            f"predicate table is not exact (missing={missing!r}, extra={extra!r})"
        )
    for name in V023_REQUIRED_PREDICATES:
        if type(predicates[name]) is not bool:
            raise LCSRSC3GateMetricError(f"predicate {name} is not an exact boolean")
    if not all(predicates[name] for name in V023_PAIR_COVERAGE_PREDICATES):
        return "INSUFFICIENT_PAIRS"
    if not all(predicates[name] for name in V023_PHYSICS_PREDICATES):
        return "STOP_PHYSICS"
    if not all(predicates[name] for name in V023_OBSERVABILITY_PREDICATES):
        return "STOP_OBSERVABILITY"
    if not all(predicates[name] for name in V023_COMPOSITION_PREDICATES):
        return "REDESIGN_INTERFACE"
    return "GO_FIXED_LEARNER_SCREEN_CONTRACT"


__all__ = [
    "V023_SIGN_THRESHOLD",
    "V023_PAIR_COVERAGE_PREDICATES",
    "V023_PHYSICS_PREDICATES",
    "V023_OBSERVABILITY_PREDICATES",
    "V023_COMPOSITION_PREDICATES",
    "V023_REQUIRED_PREDICATES",
    "V023_C3_DECISIONS",
    "V023_CONTEXT_STATUSES",
    "LCSRSC3GateMetricError",
    "RatioDirection",
    "SignAccuracy",
    "comparison_tolerance",
    "strict_direction",
    "ratio_of_sums_direction",
    "tie_aware_spearman",
    "sign_accuracy",
    "context_status",
    "adjudicate_c3",
]
