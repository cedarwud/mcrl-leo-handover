"""W-30 — P6 is an executable protocol, not a heading in the PREREG."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.probe_p6 import (
    P6_EVALUATION_SEEDS,
    P6_LEARNING_RATES,
    P6_NEAR_TIE_FRACTION,
    P6_PERTURBATION_REPLICATES,
    P6_PERTURBATION_STD_FRACTION,
    choose_learning_rate,
    cross_seed_rank_consistency,
    near_tie_actions,
    perturbation_stability,
)


def test_near_ties_use_a_dimensionless_fraction_of_the_valid_q_range():
    q = np.array([10.0, 9.95, 0.0, 1_000.0])
    mask = np.array([True, True, True, False])

    tied = near_tie_actions(q, mask, fraction=0.01)

    assert tied.tolist() == [0, 1]
    assert P6_NEAR_TIE_FRACTION == pytest.approx(0.01)


def test_a_flat_q_surface_randomises_over_every_valid_action():
    q = np.array([3.0, 3.0, -99.0, 3.0])
    mask = np.array([True, True, False, True])
    assert near_tie_actions(q, mask).tolist() == [0, 1, 3]


def test_perturbation_stability_is_reproducible_and_scale_aware():
    mask = np.array([True, True, True, False])
    separated = np.array([10.0, 5.0, 0.0, 999.0])
    close = np.array([10.0, 9.99, 0.0, 999.0])

    stable_a = perturbation_stability(
        separated,
        mask,
        np.random.default_rng(7),
        std_fraction=0.01,
        replicates=128,
    )
    stable_b = perturbation_stability(
        separated,
        mask,
        np.random.default_rng(7),
        std_fraction=0.01,
        replicates=128,
    )
    fragile = perturbation_stability(
        close,
        mask,
        np.random.default_rng(7),
        std_fraction=0.01,
        replicates=128,
    )

    assert stable_a == stable_b
    assert stable_a is not None and fragile is not None
    assert stable_a["greedy_action_retention"] > fragile["greedy_action_retention"]
    assert stable_a["kendall_tau"] > fragile["kendall_tau"]


def test_cross_seed_consistency_reports_modal_order_and_kendall_w():
    scores = {
        0.003: [3.0, 2.0, 4.0, 5.0],
        0.001: [2.0, 3.0, 1.0, 4.0],
    }
    report = cross_seed_rank_consistency(scores)
    assert report["num_seeds"] == 4
    assert report["num_arms"] == 2
    assert report["modal_order"] in ([0.003, 0.001], [0.001, 0.003])
    assert 0.0 <= report["modal_order_fraction"] <= 1.0
    assert 0.0 <= report["kendall_w"] <= 1.0


def test_cross_seed_exact_ties_follow_the_declared_sweep_order():
    report = cross_seed_rank_consistency(
        {0.003: [1.0, 1.0], 0.001: [1.0, 1.0]}
    )
    assert report["modal_order"] == [0.003, 0.001]
    assert report["modal_order_fraction"] == pytest.approx(1.0)


def test_lr_selection_excludes_nonfinite_then_uses_declared_sweep_order_for_ties():
    tied_scores = [1.0, 2.0, 3.0, 4.0, 5.0] * 2
    arms = {
        0.01: {"status": "nonfinite"},
        0.003: {
            "status": "complete",
            "calibrated_scalar_reward_by_seed": tied_scores,
            "perturbation_greedy_action_retention": 0.80,
        },
        0.001: {
            "status": "complete",
            "calibrated_scalar_reward_by_seed": tied_scores,
            "perturbation_greedy_action_retention": 0.90,
        },
    }
    selected, report = choose_learning_rate(arms)
    assert selected == pytest.approx(0.003)
    assert report["excluded_nonfinite_or_incomplete"] == [0.01]
    assert report["rule"].startswith("exclude non-finite")


def test_lr_selection_uses_mean_not_median_or_diagnostic_retention():
    arms = {
        0.01: {"status": "nonfinite"},
        0.003: {
            "status": "complete",
            "calibrated_scalar_reward_by_seed": [0.0] * 9 + [100.0],
            "perturbation_greedy_action_retention": 0.01,
        },
        0.001: {
            "status": "complete",
            "calibrated_scalar_reward_by_seed": [9.0] * 10,
            "perturbation_greedy_action_retention": 1.0,
        },
    }

    selected, _report = choose_learning_rate(arms)

    assert selected == pytest.approx(0.003)


def test_the_operational_constants_have_no_hidden_fourth_arm():
    assert P6_LEARNING_RATES == (0.01, 0.003, 0.001)
    assert len(P6_EVALUATION_SEEDS) == 10
    assert len(set(P6_EVALUATION_SEEDS)) == 10
    assert P6_PERTURBATION_STD_FRACTION == pytest.approx(0.01)
    assert P6_PERTURBATION_REPLICATES == 32
