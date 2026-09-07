"""W-57 -- non-EE E1 instrument-validity metrics."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_instrument_validity import (
    EEAxisInstrumentValidityError,
    compute_action_main_effect,
    compute_deployment_diversity,
    compute_head_pivotality,
    compute_observability_collisions,
    compute_pair_generalization,
    compute_strong_baseline_pair_generalization,
)


def test_deployment_diversity_reports_modal_share_and_all_dark_rows() -> None:
    scores = np.zeros((1001, 10), dtype=np.float64)
    masks = np.ones_like(scores, dtype=np.bool_)
    masks[-1] = False
    for row in range(1000):
        scores[row, 0 if row < 600 else 1 + (row % 8)] = 1.0
    result = compute_deployment_diversity(
        scores, masks, minimum_eligible_decisions=1000
    )
    assert result.eligible_decisions == 1000
    assert result.all_dark_decisions == 1
    assert result.distinct_action_count == 9
    assert result.modal_action == 0
    assert result.modal_action_share == pytest.approx(0.6)


def test_deployment_diversity_fails_closed_on_insufficient_decisions() -> None:
    with pytest.raises(EEAxisInstrumentValidityError, match="fewer eligible"):
        compute_deployment_diversity(
            np.zeros((9, 2)),
            np.ones((9, 2), dtype=np.bool_),
            minimum_eligible_decisions=10,
        )


def test_head_pivotality_removes_each_head_from_the_same_three_head_score() -> None:
    # Full scores select action 0 on both rows.  Removing C1 changes row 0;
    # removing C2 changes row 1; C3 is never pivotal.
    c1 = np.asarray([[3.0, 0.0], [0.0, 0.0]])
    c2 = np.asarray([[0.0, 0.0], [3.0, 0.0]])
    c3 = np.asarray([[0.0, 2.0], [0.0, 2.0]])
    reports = compute_head_pivotality(
        head_scores=(c1, c2, c3),
        masks=np.ones((2, 2), dtype=np.bool_),
        minimum_eligible_decisions=2,
    )
    assert [report.changed_decisions for report in reports] == [1, 1, 0]
    assert [report.changed_fraction for report in reports] == [0.5, 0.5, 0.0]


def test_action_main_effect_is_one_for_validation_stable_action_bias() -> None:
    validation = np.tile(np.asarray([0.0, 1.0, 3.0]), (4, 1))
    test = np.tile(np.asarray([10.0, 11.0, 13.0]), (3, 1))
    validation_masks = np.ones_like(validation, dtype=np.bool_)
    test_masks = np.ones_like(test, dtype=np.bool_)
    result = compute_action_main_effect(
        validation_scores=validation,
        validation_masks=validation_masks,
        test_scores=test,
        test_masks=test_masks,
    )
    assert result.action_main_effect_fraction == pytest.approx(1.0)


def test_action_main_effect_is_zero_when_validation_action_effect_does_not_transfer() -> None:
    validation = np.tile(np.asarray([-1.0, 0.0, 1.0]), (3, 1))
    test = np.tile(np.asarray([1.0, 0.0, -1.0]), (3, 1))
    masks = np.ones((3, 3), dtype=np.bool_)
    result = compute_action_main_effect(
        validation_scores=validation,
        validation_masks=masks,
        test_scores=test,
        test_masks=masks,
    )
    # A validation-fitted effect can be worse than predicting zero centered
    # score on test; G-S is an out-of-sample R^2 and may therefore be negative.
    assert result.action_main_effect_fraction == pytest.approx(-3.0)


def test_pair_generalization_compares_with_action_only_train_fit() -> None:
    train_r = np.asarray([0, 0, 1, 1], dtype=np.int64)
    train_c = np.asarray([1, 2, 2, 0], dtype=np.int64)
    train_y = np.asarray([1.0, 3.0, 2.0, -1.0])
    test_r = np.asarray([0, 2], dtype=np.int64)
    test_c = np.asarray([2, 1], dtype=np.int64)
    # The action-only baseline predicts [3,-2].  Add state-dependent targets;
    # the supplied Q surface predicts the held-out rows exactly.
    test_y = np.asarray([4.0, -1.0])
    q = np.asarray([[0.0, 0.0, 4.0], [0.0, 0.0, 1.0]])
    result = compute_pair_generalization(
        train_reference_actions=train_r,
        train_candidate_actions=train_c,
        train_targets=train_y,
        heldout_reference_actions=test_r,
        heldout_candidate_actions=test_c,
        heldout_targets=test_y,
        heldout_q_surface=q,
        action_dim=3,
    )
    assert result.model_mae == pytest.approx(0.0)
    assert result.action_only_baseline_mae == pytest.approx(1.0)
    assert result.relative_mae_improvement == pytest.approx(1.0)


def test_pair_generalization_rejects_unidentified_action_component() -> None:
    with pytest.raises(EEAxisInstrumentValidityError, match="not identified"):
        compute_pair_generalization(
            train_reference_actions=np.asarray([0]),
            train_candidate_actions=np.asarray([1]),
            train_targets=np.asarray([1.0]),
            heldout_reference_actions=np.asarray([2]),
            heldout_candidate_actions=np.asarray([3]),
            heldout_targets=np.asarray([1.0]),
            heldout_q_surface=np.zeros((1, 4)),
            action_dim=4,
        )


def test_strong_pair_baseline_prevents_weak_action_model_from_creating_skill() -> None:
    train_r = np.asarray([0, 0], dtype=np.int64)
    train_c = np.asarray([1, 1], dtype=np.int64)
    train_y = np.asarray([5.0, 5.0])
    heldout_r = np.asarray([0, 0], dtype=np.int64)
    heldout_c = np.asarray([1, 1], dtype=np.int64)
    heldout_y = np.asarray([1.0, -1.0])
    # Q predicts the held-out rows as zero. The action-only and train-median
    # nulls both predict +5 and are much worse than the parameter-free zero
    # null, so the amended metric must not credit the model for beating them.
    q = np.zeros((2, 2), dtype=np.float64)
    result = compute_strong_baseline_pair_generalization(
        train_reference_actions=train_r,
        train_candidate_actions=train_c,
        train_targets=train_y,
        heldout_reference_actions=heldout_r,
        heldout_candidate_actions=heldout_c,
        heldout_targets=heldout_y,
        heldout_q_surface=q,
        action_dim=2,
    )
    assert result.action_only_baseline_mae == pytest.approx(5.0)
    assert result.train_median_baseline_mae == pytest.approx(5.0)
    assert result.zero_baseline_mae == pytest.approx(1.0)
    assert result.strongest_baseline_name == "zero"
    assert result.model_mae == pytest.approx(1.0)
    assert result.relative_mae_improvement == pytest.approx(0.0)


def test_strong_pair_baseline_uses_train_median_without_heldout_fitting() -> None:
    train_r = np.asarray([0, 0, 0], dtype=np.int64)
    train_c = np.asarray([1, 1, 1], dtype=np.int64)
    train_y = np.asarray([2.0, 2.0, 100.0])
    heldout_y = np.asarray([2.0, 3.0])
    q = np.asarray([[0.0, 2.0], [0.0, 3.0]])
    result = compute_strong_baseline_pair_generalization(
        train_reference_actions=train_r,
        train_candidate_actions=train_c,
        train_targets=train_y,
        heldout_reference_actions=np.asarray([0, 0], dtype=np.int64),
        heldout_candidate_actions=np.asarray([1, 1], dtype=np.int64),
        heldout_targets=heldout_y,
        heldout_q_surface=q,
        action_dim=2,
    )
    assert result.train_median_value == pytest.approx(2.0)
    assert result.train_median_baseline_mae == pytest.approx(0.5)
    assert result.strongest_baseline_name == "train_median"
    assert result.relative_mae_improvement == pytest.approx(1.0)


def test_observability_collision_reports_conflicting_targets_and_mae_floor() -> None:
    states = np.asarray(
        [[1.0, 2.0], [1.0, 2.0], [1.0, 2.0], [1.0, 2.0], [3.0, 4.0]],
        dtype=np.float32,
    )
    masks = np.ones((5, 3), dtype=np.bool_)
    result = compute_observability_collisions(
        routes=["C1"] * 5,
        policy_digests=["a" * 64] * 5,
        states=states,
        masks=masks,
        reference_actions=np.asarray([0, 0, 0, 0, 0]),
        candidate_actions=np.asarray([1, 1, 1, 1, 2]),
        targets=np.asarray([2.0, 2.0, -2.0, -2.0, 1.0]),
    )
    assert result.repeated_input_groups == 1
    assert result.conflicting_sign_groups == 1
    assert result.conflicting_sign_rows == 4
    assert result.deterministic_mae_floor == pytest.approx(8.0 / 5.0)
    assert result.normalized_mae_floor == pytest.approx(8.0 / 9.0)


def test_observability_requires_two_targets_per_sign_for_persistent_collision() -> None:
    result = compute_observability_collisions(
        routes=["C1", "C1"],
        policy_digests=["b" * 64, "b" * 64],
        states=np.asarray([[1.0], [2.0]], dtype=np.float32),
        masks=np.ones((2, 2), dtype=np.bool_),
        reference_actions=np.asarray([0, 0]),
        candidate_actions=np.asarray([1, 1]),
        targets=np.asarray([1.0, -1.0]),
    )
    assert result.conflicting_sign_groups == 0
