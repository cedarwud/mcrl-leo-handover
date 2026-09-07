"""W-59 -- E1 cluster-bootstrap statistics."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_e1_statistics import (
    E1StatisticsError,
    bootstrap_action_main_effect_difference,
    bootstrap_clustered_proportion,
    bootstrap_pair_skill,
    bootstrap_relative_error_reduction,
)


def test_pair_skill_bootstrap_preserves_clusters_and_proportional_skill() -> None:
    baseline = np.asarray([2.0, 4.0, 6.0, 8.0])
    result = bootstrap_pair_skill(
        model_absolute_errors=baseline * 0.5,
        baseline_absolute_errors=baseline,
        cluster_ids=["a", "a", "b", "b"],
        replications=200,
        confidence=0.95,
        bootstrap_seed=7,
    )
    assert result.estimate == pytest.approx(0.5)
    assert result.lower == pytest.approx(0.5)
    assert result.upper == pytest.approx(0.5)
    assert result.clusters == 2


def test_clustered_proportion_resamples_whole_clusters() -> None:
    result = bootstrap_clustered_proportion(
        events=np.asarray([True, True, False, False], dtype=np.bool_),
        cluster_ids=["a", "a", "b", "b"],
        estimand="C1-removal-change-rate",
        replications=200,
        confidence=0.95,
        bootstrap_seed=11,
    )
    assert result.estimate == pytest.approx(0.5)
    assert result.lower == pytest.approx(0.0)
    assert result.upper == pytest.approx(1.0)


def test_bootstrap_fails_closed_on_one_cluster_or_zero_baseline_error() -> None:
    with pytest.raises(E1StatisticsError, match="at least two clusters"):
        bootstrap_clustered_proportion(
            events=np.asarray([True, False], dtype=np.bool_),
            cluster_ids=["one", "one"],
            estimand="rate",
            replications=100,
            confidence=0.95,
            bootstrap_seed=1,
        )


def test_relative_error_reduction_is_paired_within_cluster() -> None:
    result = bootstrap_relative_error_reduction(
        probe_correct=np.asarray([True, True, True, False], dtype=np.bool_),
        baseline_correct=np.asarray([True, False, False, False], dtype=np.bool_),
        cluster_ids=["a", "a", "b", "b"],
        replications=200,
        confidence=0.95,
        bootstrap_seed=3,
    )
    assert result.estimate == pytest.approx(2.0 / 3.0)
    assert result.lower <= result.estimate <= result.upper


def test_action_main_effect_difference_uses_validation_fit_and_test_clusters() -> None:
    masks = np.ones((4, 2), dtype=np.bool_)
    trained = np.asarray([[1.0, -1.0], [-1.0, 1.0], [1.0, -1.0], [-1.0, 1.0]])
    initialized = np.tile(np.asarray([0.0, 1.0]), (4, 1))
    result = bootstrap_action_main_effect_difference(
        trained_validation_scores=trained,
        initialized_validation_scores=initialized,
        validation_masks=masks,
        trained_test_scores=trained,
        initialized_test_scores=initialized,
        test_masks=masks,
        test_cluster_ids=["a", "a", "b", "b"],
        replications=200,
        confidence=0.95,
        bootstrap_seed=5,
    )
    assert result.trained_fraction == pytest.approx(0.0)
    assert result.initialized_fraction == pytest.approx(1.0)
    assert result.trained_minus_initialized.estimate == pytest.approx(-1.0)
    assert result.trained_minus_initialized.upper == pytest.approx(-1.0)
    with pytest.raises(E1StatisticsError, match="zero held-out error"):
        bootstrap_pair_skill(
            model_absolute_errors=np.asarray([0.0, 0.0]),
            baseline_absolute_errors=np.asarray([0.0, 0.0]),
            cluster_ids=["a", "b"],
            replications=100,
            confidence=0.95,
            bootstrap_seed=1,
        )
