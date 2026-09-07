"""Cluster-respecting uncertainty estimates for the no-EE E1 gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Callable, Sequence

import numpy as np

from ..errors import MCRLContractError
from .ee_axis_instrument_validity import (
    compute_action_main_effect,
    fit_action_only_effects,
    score_action_only_effects,
)


class E1StatisticsError(MCRLContractError):
    """An E1 bootstrap input cannot support the preregistered estimand."""


@dataclass(frozen=True)
class ClusterBootstrapInterval:
    estimand: str
    estimate: float
    lower: float
    upper: float
    confidence: float
    replications: int
    clusters: int
    bootstrap_seed: int

    def as_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


@dataclass(frozen=True)
class ActionMainEffectDifference:
    trained_fraction: float
    initialized_fraction: float
    trained_minus_initialized: ClusterBootstrapInterval

    def as_dict(self) -> dict[str, object]:
        return {
            "trained_fraction": self.trained_fraction,
            "initialized_fraction": self.initialized_fraction,
            "trained_minus_initialized": self.trained_minus_initialized.as_dict(),
        }


def _bootstrap_inputs(
    cluster_ids: Sequence[str] | np.ndarray,
    *,
    rows: int,
    replications: int,
    confidence: float,
    bootstrap_seed: int,
) -> tuple[np.ndarray, list[str], list[np.ndarray]]:
    clusters = np.asarray(cluster_ids, dtype=object)
    if clusters.shape != (rows,):
        raise E1StatisticsError("cluster_ids must align with metric rows")
    if any(not isinstance(value, str) or not value for value in clusters.tolist()):
        raise E1StatisticsError("cluster_ids must be nonempty strings")
    unique = sorted(set(clusters.tolist()))
    if len(unique) < 2:
        raise E1StatisticsError("cluster bootstrap requires at least two clusters")
    if isinstance(replications, bool) or not isinstance(replications, int) or replications < 100:
        raise E1StatisticsError("bootstrap replications must be an integer >= 100")
    if not math.isfinite(confidence) or not 0.5 < confidence < 1.0:
        raise E1StatisticsError("bootstrap confidence must lie in (0.5,1)")
    if isinstance(bootstrap_seed, bool) or not isinstance(bootstrap_seed, int) or bootstrap_seed < 0:
        raise E1StatisticsError("bootstrap_seed must be a nonnegative integer")
    indices = [np.flatnonzero(clusters == cluster) for cluster in unique]
    return clusters, unique, indices


def _cluster_bootstrap(
    *,
    estimand: str,
    point: float,
    cluster_indices: list[np.ndarray],
    statistic: Callable[[np.ndarray], float],
    replications: int,
    confidence: float,
    bootstrap_seed: int,
) -> ClusterBootstrapInterval:
    generator = np.random.default_rng(bootstrap_seed)
    cluster_count = len(cluster_indices)
    samples = np.empty(replications, dtype=np.float64)
    for replication in range(replications):
        chosen = generator.integers(0, cluster_count, size=cluster_count)
        row_indices = np.concatenate([cluster_indices[index] for index in chosen])
        samples[replication] = statistic(row_indices)
    if not np.all(np.isfinite(samples)):
        raise E1StatisticsError("bootstrap statistic produced non-finite values")
    tail = (1.0 - confidence) / 2.0
    lower, upper = np.quantile(samples, [tail, 1.0 - tail], method="linear")
    return ClusterBootstrapInterval(
        estimand=estimand,
        estimate=float(point),
        lower=float(lower),
        upper=float(upper),
        confidence=float(confidence),
        replications=replications,
        clusters=cluster_count,
        bootstrap_seed=bootstrap_seed,
    )


def bootstrap_pair_skill(
    *,
    model_absolute_errors: np.ndarray,
    baseline_absolute_errors: np.ndarray,
    cluster_ids: Sequence[str] | np.ndarray,
    replications: int,
    confidence: float,
    bootstrap_seed: int,
) -> ClusterBootstrapInterval:
    """Bootstrap ``1 - MAE_model / MAE_bias`` by independent cluster."""

    model = np.asarray(model_absolute_errors, dtype=np.float64)
    baseline = np.asarray(baseline_absolute_errors, dtype=np.float64)
    if model.ndim != 1 or baseline.shape != model.shape or model.size < 1:
        raise E1StatisticsError("pair error vectors must be nonempty and aligned")
    if (
        not np.all(np.isfinite(model))
        or not np.all(np.isfinite(baseline))
        or np.any(model < 0.0)
        or np.any(baseline < 0.0)
    ):
        raise E1StatisticsError("pair errors must be finite and nonnegative")
    _clusters, _unique, indices = _bootstrap_inputs(
        cluster_ids,
        rows=model.size,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )

    def statistic(rows: np.ndarray) -> float:
        denominator = float(np.sum(baseline[rows]))
        if denominator <= 0.0:
            return float("nan")
        return 1.0 - float(np.sum(model[rows])) / denominator

    point = statistic(np.arange(model.size))
    if not math.isfinite(point):
        raise E1StatisticsError("action-only baseline has zero held-out error")
    return _cluster_bootstrap(
        estimand="pair_skill",
        point=point,
        cluster_indices=indices,
        statistic=statistic,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )


def bootstrap_clustered_proportion(
    *,
    events: np.ndarray,
    cluster_ids: Sequence[str] | np.ndarray,
    estimand: str,
    replications: int,
    confidence: float,
    bootstrap_seed: int,
) -> ClusterBootstrapInterval:
    """Bootstrap a binary decision-level rate while resampling clusters."""

    values = np.asarray(events)
    if values.ndim != 1 or values.size < 1 or values.dtype != np.bool_:
        raise E1StatisticsError("events must be a nonempty boolean vector")
    if not isinstance(estimand, str) or not estimand.strip():
        raise E1StatisticsError("estimand must be a nonempty string")
    _clusters, _unique, indices = _bootstrap_inputs(
        cluster_ids,
        rows=values.size,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )

    def statistic(rows: np.ndarray) -> float:
        return float(np.mean(values[rows]))

    return _cluster_bootstrap(
        estimand=estimand,
        point=statistic(np.arange(values.size)),
        cluster_indices=indices,
        statistic=statistic,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )


def bootstrap_relative_error_reduction(
    *,
    probe_correct: np.ndarray,
    baseline_correct: np.ndarray,
    cluster_ids: Sequence[str] | np.ndarray,
    replications: int,
    confidence: float,
    bootstrap_seed: int,
) -> ClusterBootstrapInterval:
    """Bootstrap paired classifier relative error reduction by cluster."""

    probe = np.asarray(probe_correct)
    baseline = np.asarray(baseline_correct)
    if (
        probe.ndim != 1
        or baseline.shape != probe.shape
        or probe.size < 1
        or probe.dtype != np.bool_
        or baseline.dtype != np.bool_
    ):
        raise E1StatisticsError(
            "probe and baseline correctness must be aligned boolean vectors"
        )
    _clusters, _unique, indices = _bootstrap_inputs(
        cluster_ids,
        rows=probe.size,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )

    def statistic(rows: np.ndarray) -> float:
        baseline_accuracy = float(np.mean(baseline[rows]))
        if baseline_accuracy >= 1.0:
            return float("nan")
        probe_accuracy = float(np.mean(probe[rows]))
        return (probe_accuracy - baseline_accuracy) / (1.0 - baseline_accuracy)

    point = statistic(np.arange(probe.size))
    if not math.isfinite(point):
        raise E1StatisticsError(
            "a perfect action-prior baseline has undefined relative error reduction"
        )
    return _cluster_bootstrap(
        estimand="reference_action_relative_error_reduction",
        point=point,
        cluster_indices=indices,
        statistic=statistic,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )


def bootstrap_action_main_effect_difference(
    *,
    trained_validation_scores: np.ndarray,
    initialized_validation_scores: np.ndarray,
    validation_masks: np.ndarray,
    trained_test_scores: np.ndarray,
    initialized_test_scores: np.ndarray,
    test_masks: np.ndarray,
    test_cluster_ids: Sequence[str] | np.ndarray,
    replications: int,
    confidence: float,
    bootstrap_seed: int,
) -> ActionMainEffectDifference:
    """Bootstrap test G-S(trained)-G-S(initialized) by held-out cluster."""

    trained_validation = np.asarray(trained_validation_scores, dtype=np.float64)
    initialized_validation = np.asarray(initialized_validation_scores, dtype=np.float64)
    trained_test = np.asarray(trained_test_scores, dtype=np.float64)
    initialized_test = np.asarray(initialized_test_scores, dtype=np.float64)
    validation_valid = np.asarray(validation_masks)
    test_valid = np.asarray(test_masks)
    if trained_validation.shape != initialized_validation.shape:
        raise E1StatisticsError("trained and initialized validation surfaces must align")
    if trained_test.shape != initialized_test.shape:
        raise E1StatisticsError("trained and initialized test surfaces must align")
    if validation_valid.shape != trained_validation.shape or validation_valid.dtype != np.bool_:
        raise E1StatisticsError("validation masks must align with score surfaces")
    if test_valid.shape != trained_test.shape or test_valid.dtype != np.bool_:
        raise E1StatisticsError("test masks must align with score surfaces")
    trained_point = compute_action_main_effect(
        validation_scores=trained_validation,
        validation_masks=validation_valid,
        test_scores=trained_test,
        test_masks=test_valid,
    ).action_main_effect_fraction
    initialized_point = compute_action_main_effect(
        validation_scores=initialized_validation,
        validation_masks=validation_valid,
        test_scores=initialized_test,
        test_masks=test_valid,
    ).action_main_effect_fraction
    trained_effects = fit_action_only_effects(trained_validation, validation_valid)
    initialized_effects = fit_action_only_effects(
        initialized_validation, validation_valid
    )
    _clusters, _unique, indices = _bootstrap_inputs(
        test_cluster_ids,
        rows=trained_test.shape[0],
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )

    def statistic(rows: np.ndarray) -> float:
        trained_fraction = score_action_only_effects(
            trained_test[rows], test_valid[rows], trained_effects
        )[2]
        initialized_fraction = score_action_only_effects(
            initialized_test[rows], test_valid[rows], initialized_effects
        )[2]
        return trained_fraction - initialized_fraction

    difference = _cluster_bootstrap(
        estimand="action_main_effect_trained_minus_initialized",
        point=trained_point - initialized_point,
        cluster_indices=indices,
        statistic=statistic,
        replications=replications,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
    )
    return ActionMainEffectDifference(
        trained_fraction=float(trained_point),
        initialized_fraction=float(initialized_point),
        trained_minus_initialized=difference,
    )


__all__ = [
    "ActionMainEffectDifference",
    "ClusterBootstrapInterval",
    "E1StatisticsError",
    "bootstrap_clustered_proportion",
    "bootstrap_action_main_effect_difference",
    "bootstrap_pair_skill",
    "bootstrap_relative_error_reduction",
]
