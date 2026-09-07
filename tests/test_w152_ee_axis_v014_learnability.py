"""W-152 -- compact V0.14 learnability and joint-action diagnostics."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_v014_learnability import (
    CompactHeadSurfaceDataset,
    compact_balanced_generalization,
    joint_teacher_student_diagnostics,
)


def _dataset(targets: np.ndarray, *, seeds: np.ndarray) -> CompactHeadSurfaceDataset:
    anchors, actions = targets.shape
    masks = np.ones((anchors, actions), dtype=np.bool_)
    references = np.zeros(anchors, dtype=np.int64)
    names = np.asarray(
        [format(index + 1, "064x") for index in range(anchors)], dtype="U64"
    )
    return CompactHeadSurfaceDataset(
        states=np.arange(anchors * 5, dtype=np.float32).reshape(anchors, 5),
        masks=masks,
        reference_actions=references,
        target_surfaces_bits=targets,
        source_seeds=seeds,
        anchor_sha256s=names,
    )


def test_compact_generalization_recovers_perfect_model_against_train_only_nulls() -> None:
    train_targets = np.asarray(
        [[0.0, 1.0, -1.0], [0.0, 2.0, -2.0], [0.0, 3.0, -3.0]]
    )
    validation_targets = np.asarray(
        [[0.0, 4.0, -4.0], [0.0, 5.0, -5.0]]
    )
    train = _dataset(train_targets, seeds=np.asarray([1, 1, 2]))
    validation = _dataset(validation_targets, seeds=np.asarray([3, 4]))
    report = compact_balanced_generalization(
        train=train,
        validation=validation,
        validation_q_surface=validation_targets,
        kappa_bits=1.0,
    )
    assert report.model_mae == 0.0
    assert report.skill_vs_strongest_null == 1.0
    assert report.validation_seeds == 2
    assert report.validation_anchors == 2


def test_joint_diagnostics_use_one_masked_sum_and_measure_supported_changes() -> None:
    masks = np.asarray([[True, True, True], [True, True, False]])
    q1 = np.asarray([[3.0, 2.0, 0.0], [2.0, 1.0, 99.0]])
    q2_bits = np.zeros((2, 3), dtype=np.float64)
    q3_bits = np.asarray([[0.0, 20.0, -5.0], [0.0, 0.0, 0.0]])
    # Teacher changes row 0 from action 0 to action 1. Student matches it.
    q2_hat = np.zeros((2, 3), dtype=np.float64)
    q3_hat = np.asarray([[0.0, 2.0, -0.5], [0.0, 0.0, 0.0]])
    compatibility = np.asarray([[True, True, False], [True, False, False]])
    result = joint_teacher_student_diagnostics(
        q1_values=q1,
        q2_target_bits=q2_bits,
        q3_target_bits=q3_bits,
        q2_hat=q2_hat,
        q3_hat=q3_hat,
        masks=masks,
        q3_compatibility=compatibility,
        kappa_bits=10.0,
    )
    assert result["all_anchor_argmax_agreement"] == 1.0
    assert result["teacher_change_exposure"] == 1
    assert result["teacher_change_conditional_agreement"] == 1.0
    assert result["student_change_exposure"] == 1
    assert result["student_changed_action_positive_support_rate"] == 1.0


def test_joint_diagnostics_reject_illegal_or_empty_surfaces() -> None:
    with pytest.raises(Exception, match="legal"):
        joint_teacher_student_diagnostics(
            q1_values=np.zeros((1, 2)),
            q2_target_bits=np.zeros((1, 2)),
            q3_target_bits=np.zeros((1, 2)),
            q2_hat=np.zeros((1, 2)),
            q3_hat=np.zeros((1, 2)),
            masks=np.zeros((1, 2), dtype=np.bool_),
            q3_compatibility=np.zeros((1, 2), dtype=np.bool_),
            kappa_bits=1.0,
        )
