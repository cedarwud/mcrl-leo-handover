#!/usr/bin/env python3
"""Fail-closed R7 balanced-successor metric and decision layer.

It reuses the copied source, fit, composition, and service implementation
without changing their teacher, features, loss, physics, or composition rules.
It neither creates a world nor fits a learner.  The server-side independent
verifiers supply the exact 8 x 3 x 2 held-out numeric receipts to
:func:`evaluate_r7_panel` and use :func:`adjudicate_section14_r7` exactly once.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np


WORLDS = tuple(range(2026121801, 2026121809))
STUDENT_SEEDS = (2026135201, 2026135202, 2026135203)
ARMS = ("INFORMED", "MATCHED_PLACEBO")
SIGN_THRESHOLD = 0.02
MIN_CLASS_ROWS = 24
MEAN_INFORMED_BACC_MIN = 0.60
BACC_GAP_MIN = 0.05
MEAN_INFORMED_SPEARMAN_MIN = 0.20
INFORMED_WORLD_WINS_MIN = 6
INFORMED_SEED_NONNEGATIVE_WORLDS_MIN = 5
PROCESS_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


class R7BalancedGateError(RuntimeError):
    """R7 input or a frozen successor predicate failed closed."""


def balanced_sign_metrics(
    predictions: Sequence[float] | np.ndarray,
    targets: Sequence[float] | np.ndarray,
) -> dict[str, int | float | None]:
    """Return raw and balanced sign receipts on the unchanged eligible set.

    Strictly zero predictions are counted as wrong for both classes.  A missing,
    non-finite, or zero class denominator produces an invalid metric (rather
    than a value that can be averaged into a decision).
    """

    predicted = np.asarray(predictions, dtype=np.float64)
    truth = np.asarray(targets, dtype=np.float64)
    if predicted.ndim != 1 or truth.shape != predicted.shape:
        raise R7BalancedGateError("predictions and targets must be aligned vectors")
    if not np.all(np.isfinite(predicted)) or not np.all(np.isfinite(truth)):
        raise R7BalancedGateError("balanced sign inputs must be finite")
    eligible = np.abs(truth) >= SIGN_THRESHOLD
    positive = eligible & (truth > 0.0)
    negative = eligible & (truth < 0.0)
    n_positive = int(np.count_nonzero(positive))
    n_negative = int(np.count_nonzero(negative))
    predicted_positive = predicted > 0.0
    predicted_negative = predicted < 0.0
    correct_positive = int(np.count_nonzero(positive & predicted_positive))
    correct_negative = int(np.count_nonzero(negative & predicted_negative))
    evaluated = int(np.count_nonzero(eligible))
    raw_correct = correct_positive + correct_negative
    positive_recall = None if n_positive == 0 else correct_positive / n_positive
    negative_recall = None if n_negative == 0 else correct_negative / n_negative
    balanced = (
        None
        if positive_recall is None or negative_recall is None
        else (positive_recall + negative_recall) / 2.0
    )
    raw_accuracy = None if evaluated == 0 else raw_correct / evaluated
    return {
        "threshold": SIGN_THRESHOLD,
        "total_rows": int(truth.size),
        "evaluated_rows": evaluated,
        "excluded_rows": int(truth.size - evaluated),
        "raw_correct_rows": raw_correct,
        "raw_sign_accuracy": raw_accuracy,
        "positive_denominator": n_positive,
        "negative_denominator": n_negative,
        "correct_positive": correct_positive,
        "correct_negative": correct_negative,
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "balanced_accuracy": balanced,
    }


@dataclass(frozen=True)
class HeldOutShard:
    world: int
    seed: int
    arm: str
    predictions: Sequence[float]
    targets: Sequence[float]
    spearman: float | None


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _mean(values: Sequence[float | None]) -> float | None:
    if not values or any(value is None or not _finite(value) for value in values):
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _midranks(values: np.ndarray) -> np.ndarray:
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
    """Recompute the unchanged pooled held-out Spearman estimand."""

    first = np.asarray(left, dtype=np.float64)
    second = np.asarray(right, dtype=np.float64)
    if first.ndim != 1 or second.shape != first.shape:
        raise R7BalancedGateError("Spearman inputs must be aligned vectors")
    if first.size < 2 or not np.all(np.isfinite(first)) or not np.all(np.isfinite(second)):
        return None
    a = _midranks(first)
    b = _midranks(second)
    a -= float(np.mean(a))
    b -= float(np.mean(b))
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    if denominator == 0.0 or not math.isfinite(denominator):
        return None
    value = float(np.dot(a, b) / denominator)
    return value if math.isfinite(value) else None


def _same_metric(declared: float | None, recomputed: float | None) -> bool:
    if declared is None or recomputed is None:
        return declared is None and recomputed is None
    return _finite(declared) and math.isclose(
        float(declared), float(recomputed), rel_tol=1.0e-12, abs_tol=1.0e-12
    )


def _strictly_above(left: float, right: float) -> bool:
    tolerance = max(
        1.0e-12,
        1024.0
        * np.finfo(np.float64).eps
        * max(1.0, abs(float(left)), abs(float(right))),
    )
    return float(left) - float(right) > tolerance


def validate_process_environment(environment: Mapping[str, str]) -> dict[str, str]:
    actual = {key: environment.get(key) for key in PROCESS_ENVIRONMENT}
    if actual != PROCESS_ENVIRONMENT:
        raise R7BalancedGateError("deterministic BLAS/OpenMP process environment drifted")
    return dict(PROCESS_ENVIRONMENT)


def evaluate_r7_panel(
    shards: Sequence[HeldOutShard],
    *,
    informed_world_wins: int | None = None,
    informed_seed_nonnegative_worlds: Mapping[int, int] | None = None,
) -> dict[str, Any]:
    """Recompute the exact R7 learner predicate from all 48 held-out shards.

    The optional stability arguments are compatibility cross-checks only.  The
    decisive counts are always recomputed from the shard Spearman values.
    """

    expected = {(world, seed, arm) for world in WORLDS for seed in STUDENT_SEEDS for arm in ARMS}
    by_key = {(shard.world, shard.seed, shard.arm): shard for shard in shards}
    if len(shards) != len(expected) or set(by_key) != expected:
        raise R7BalancedGateError("R7 panel is not the exact fresh 8 x 3 x 2 schedule")

    seed_metrics: dict[str, dict[str, Any]] = {}
    reference_targets: list[np.ndarray] | None = None
    for seed in STUDENT_SEEDS:
        seed_metrics[str(seed)] = {}
        for arm in ARMS:
            ordered = [by_key[(world, seed, arm)] for world in WORLDS]
            prediction = np.concatenate([np.asarray(item.predictions, dtype=np.float64) for item in ordered])
            target = np.concatenate([np.asarray(item.targets, dtype=np.float64) for item in ordered])
            if reference_targets is None:
                reference_targets = [np.asarray(by_key[(world, seed, arm)].targets, dtype=np.float64) for world in WORLDS]
            else:
                for world, expected_target in zip(WORLDS, reference_targets, strict=True):
                    current = np.asarray(by_key[(world, seed, arm)].targets, dtype=np.float64)
                    if not np.array_equal(current, expected_target):
                        raise R7BalancedGateError("held-out labels differ across seed or arm")
            seed_metrics[str(seed)][arm] = {
                "spearman": tie_aware_spearman(prediction, target),
                "sign": balanced_sign_metrics(prediction, target),
            }

    world_metrics: dict[str, dict[str, Any]] = {}
    recomputed_world_wins = 0
    recomputed_nonnegative = {seed: 0 for seed in STUDENT_SEEDS}
    for world in WORLDS:
        world_entry: dict[str, Any] = {}
        for arm in ARMS:
            seed_entries: dict[str, Any] = {}
            seed_rhos: list[float | None] = []
            for seed in STUDENT_SEEDS:
                shard = by_key[(world, seed, arm)]
                rho = tie_aware_spearman(shard.predictions, shard.targets)
                if not _same_metric(shard.spearman, rho):
                    raise R7BalancedGateError(
                        "serialized shard Spearman disagrees with raw predictions and targets"
                    )
                seed_rhos.append(rho)
                seed_entries[str(seed)] = {
                    "spearman": rho,
                    "sign": balanced_sign_metrics(shard.predictions, shard.targets),
                }
                if arm == "INFORMED" and rho is not None and rho >= 0.0:
                    recomputed_nonnegative[seed] += 1
            world_entry[arm] = {
                "seed_metrics": seed_entries,
                "mean_spearman": _mean(seed_rhos),
            }
        informed_mean = world_entry["INFORMED"]["mean_spearman"]
        placebo_mean = world_entry["MATCHED_PLACEBO"]["mean_spearman"]
        win = bool(
            informed_mean is not None
            and placebo_mean is not None
            and _strictly_above(informed_mean, placebo_mean)
        )
        recomputed_world_wins += int(win)
        world_entry["informed_strictly_above_placebo"] = win
        world_metrics[str(world)] = world_entry

    if informed_world_wins is not None and informed_world_wins != recomputed_world_wins:
        raise R7BalancedGateError("supplied informed-world win count disagrees with raw shards")
    if informed_seed_nonnegative_worlds is not None:
        supplied_nonnegative = {
            seed: informed_seed_nonnegative_worlds.get(seed)
            for seed in STUDENT_SEEDS
        }
        if supplied_nonnegative != recomputed_nonnegative:
            raise R7BalancedGateError(
                "supplied per-seed nonnegative-world counts disagree with raw shards"
            )

    informed_bacc = [seed_metrics[str(seed)]["INFORMED"]["sign"]["balanced_accuracy"] for seed in STUDENT_SEEDS]
    placebo_bacc = [seed_metrics[str(seed)]["MATCHED_PLACEBO"]["sign"]["balanced_accuracy"] for seed in STUDENT_SEEDS]
    informed_raw = [seed_metrics[str(seed)]["INFORMED"]["sign"]["raw_sign_accuracy"] for seed in STUDENT_SEEDS]
    placebo_raw = [seed_metrics[str(seed)]["MATCHED_PLACEBO"]["sign"]["raw_sign_accuracy"] for seed in STUDENT_SEEDS]
    informed_rho = [seed_metrics[str(seed)]["INFORMED"]["spearman"] for seed in STUDENT_SEEDS]
    class_targets = balanced_sign_metrics(
        np.zeros(sum(item.size for item in reference_targets or []), dtype=np.float64),
        np.concatenate(reference_targets or []),
    )
    mean_informed_bacc = _mean(informed_bacc)
    mean_placebo_bacc = _mean(placebo_bacc)
    mean_informed_raw = _mean(informed_raw)
    mean_placebo_raw = _mean(placebo_raw)
    mean_informed_rho = _mean(informed_rho)
    denominators_valid = all(
        entry[arm]["sign"]["positive_denominator"] > 0
        and entry[arm]["sign"]["negative_denominator"] > 0
        and entry[arm]["sign"]["balanced_accuracy"] is not None
        for entry in seed_metrics.values()
        for arm in ARMS
    )
    pooled_class_support = bool(
        class_targets["positive_denominator"] >= MIN_CLASS_ROWS
        and class_targets["negative_denominator"] >= MIN_CLASS_ROWS
    )
    world_stability = bool(
        recomputed_world_wins >= INFORMED_WORLD_WINS_MIN
        and all(
            recomputed_nonnegative[seed] >= INFORMED_SEED_NONNEGATIVE_WORLDS_MIN
            for seed in STUDENT_SEEDS
        )
    )
    held_out_learner = bool(
        denominators_valid
        and pooled_class_support
        and mean_informed_rho is not None
        and mean_informed_rho >= MEAN_INFORMED_SPEARMAN_MIN
        and mean_informed_bacc is not None and mean_informed_bacc >= MEAN_INFORMED_BACC_MIN
        and mean_placebo_bacc is not None and mean_informed_bacc - mean_placebo_bacc >= BACC_GAP_MIN
        and world_stability
    )
    return {
        "schema": "multi-catfish-mcrl-v023-r7-balanced-successor-metrics-v1",
        "worlds": list(WORLDS),
        "student_seeds": list(STUDENT_SEEDS),
        "seed_metrics": seed_metrics,
        "world_metrics": world_metrics,
        "informed_world_wins": recomputed_world_wins,
        "informed_seed_nonnegative_worlds": {
            str(seed): recomputed_nonnegative[seed] for seed in STUDENT_SEEDS
        },
        "pooled_eligible_denominators": {
            "positive": class_targets["positive_denominator"],
            "negative": class_targets["negative_denominator"],
        },
        "aggregate": {
            "mean_informed_spearman": mean_informed_rho,
            "mean_informed_balanced_accuracy": mean_informed_bacc,
            "mean_placebo_balanced_accuracy": mean_placebo_bacc,
            "informed_minus_placebo_balanced_accuracy": None if mean_informed_bacc is None or mean_placebo_bacc is None else mean_informed_bacc - mean_placebo_bacc,
            "mean_informed_raw_sign_accuracy": mean_informed_raw,
            "mean_placebo_raw_sign_accuracy": mean_placebo_raw,
            "informed_minus_placebo_raw_sign_accuracy": None if mean_informed_raw is None or mean_placebo_raw is None else mean_informed_raw - mean_placebo_raw,
        },
        "predicates": {
            "finite_nonzero_class_denominators": denominators_valid,
            "pooled_class_support": pooled_class_support,
            "held_out_learner": held_out_learner,
            "world_stability": world_stability,
            "raw_sign_accuracy_reported_nondecisive": True,
        },
        "decision_basis": {
            "balanced_accuracy": "PRIMARY",
            "raw_sign_accuracy": "SERIALIZED_NONDECISIVE",
        },
    }


def adjudicate_section14_r7(
    *,
    integrity: bool,
    pair_coverage: bool,
    mechanics: bool,
    physical_signature: bool,
    teacher_composition: bool,
    target_support: bool,
    held_out_learner: bool,
    world_stability: bool,
    action_exposure: bool,
    literal_11: bool,
    harmful_partial: bool,
    topology_consistency: bool,
    learned_composition: bool,
    service: bool,
) -> str:
    """Apply R6 Section-14 precedence with only the R7 learner metric replaced."""

    if not integrity:
        return "INVALID_RUN"
    if not pair_coverage:
        return "INSUFFICIENT_PAIRS_R7"
    if not (mechanics and physical_signature and teacher_composition):
        return "STOP_PHYSICS_R7"
    if not (target_support and held_out_learner and world_stability):
        return "STOP_OBSERVABILITY_R7"
    if not (
        action_exposure
        and literal_11
        and harmful_partial
        and topology_consistency
        and learned_composition
        and service
    ):
        return "REDESIGN_INTERFACE_R7"
    return "GO_FIXED_LEARNER_SCREEN_CONTRACT_R7"
