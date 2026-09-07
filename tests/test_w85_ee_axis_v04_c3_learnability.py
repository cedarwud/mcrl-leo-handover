from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.runtime.ee_axis_v04_c3_learnability import (
    C3V04LearnabilityMetricError,
    anchor_then_seed_mae,
    compute_anchor_seed_balanced_generalization,
)


def _batch(targets: list[float]) -> EEAxisPairBatch:
    rows = len(targets)
    references = np.asarray([index % 3 for index in range(rows)], dtype=np.int64)
    candidates = np.asarray([(index % 3) + 1 for index in range(rows)], dtype=np.int64)
    return EEAxisPairBatch(
        states=np.arange(rows * 8, dtype=np.float32).reshape(rows, 8) / 10.0,
        reference_actions=references,
        candidate_actions=candidates,
        target_surplus_bits=np.asarray(targets, dtype=np.float64),
        action_masks=np.ones((rows, 4), dtype=np.bool_),
    )


def _anchor(character: str) -> str:
    return character * 64


def test_anchor_then_seed_mae_is_invariant_to_duplicate_rows_inside_anchor() -> None:
    first = anchor_then_seed_mae(
        np.asarray([1.0, 3.0, 9.0]),
        source_seeds=[10, 10, 11],
        anchor_sha256s=[_anchor("a"), _anchor("a"), _anchor("b")],
    )
    duplicated = anchor_then_seed_mae(
        np.asarray([1.0, 3.0, 1.0, 3.0, 9.0]),
        source_seeds=[10, 10, 10, 10, 11],
        anchor_sha256s=[
            _anchor("a"),
            _anchor("a"),
            _anchor("a"),
            _anchor("a"),
            _anchor("b"),
        ],
    )
    assert first == duplicated
    assert first[0] == pytest.approx(5.5)


def test_balanced_generalization_uses_train_only_nulls_and_equal_seed_weight() -> None:
    train = _batch([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    validation = _batch([1.5, 2.5, 5.5, 6.5])
    q = np.zeros((4, 4), dtype=np.float64)
    for row, (reference, candidate, target) in enumerate(
        zip(
            validation.reference_actions,
            validation.candidate_actions,
            validation.target_surplus_bits,
            strict=True,
        )
    ):
        q[row, candidate] = target
        q[row, reference] = 0.0
    report = compute_anchor_seed_balanced_generalization(
        train_batch=train,
        validation_batch=validation,
        validation_source_seeds=[20, 20, 21, 21],
        validation_anchor_sha256s=[
            _anchor("a"),
            _anchor("a"),
            _anchor("b"),
            _anchor("c"),
        ],
        heldout_q_surface=q,
        state_dim=8,
        action_dim=4,
        kappa_bits=1.0,
    )
    assert report.model_mae == 0.0
    assert report.skill_vs_strongest_null == 1.0
    assert report.validation_seeds == 2
    assert report.anchor_counts_by_seed == ((20, 1), (21, 2))
    assert report.train_median_value == 3.5


def test_balanced_generalization_rejects_unidentified_validation_pair() -> None:
    train = _batch([1.0, 2.0])
    validation = _batch([3.0])
    validation.reference_actions[:] = 2
    validation.candidate_actions[:] = 3
    with pytest.raises(C3V04LearnabilityMetricError, match="unidentified"):
        compute_anchor_seed_balanced_generalization(
            train_batch=train,
            validation_batch=validation,
            validation_source_seeds=[20],
            validation_anchor_sha256s=[_anchor("a")],
            heldout_q_surface=np.zeros((1, 4)),
            state_dim=8,
            action_dim=4,
            kappa_bits=1.0,
        )
