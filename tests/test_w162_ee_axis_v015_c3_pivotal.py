"""Pure V0.15 learned-background C3 pivotal residual tests."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig
from mcrl.runtime.ee_axis_v015_c3_pivotal import (
    C3PivotalContractError,
    EEAxisV015C3PivotalLearner,
    build_pivotal_pairs,
    derive_pivotal_labels,
    evaluate_pivotal_decisions,
)


TEST_KAPPA = 10.0


def _source() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rows = 3
    states = np.zeros((rows, 287), dtype=np.float32)
    states[1, 0] = 1.0
    states[2, 1] = 1.0
    masks = np.zeros((rows, 28), dtype=np.bool_)
    masks[:, [0, 1, 2]] = True
    masks[2, 2] = False
    masks[2, 3] = True

    q1 = np.zeros((rows, 28), dtype=np.float64)
    q2 = np.zeros((rows, 28), dtype=np.float64)
    # Row 0: base=2, teacher=1.  The ZR surplus at action 1 is large
    # enough to overcome the learned-background gap.
    q1[0, 2] = 1.0
    # Row 1: base=0 and teacher remains 0 after the small ZR alternative.
    q1[1, 0] = 1.0
    q1[1, 1] = 0.8
    # Row 2: base=0, teacher=0 with a different legal action set.
    q1[2, 0] = 1.0
    q1[2, 3] = 0.2
    z3 = np.zeros((rows, 28), dtype=np.float64)
    z3[0, 1] = 20.0
    z3[1, 1] = 1.0
    z3[2, 3] = 1.0
    return states, masks, q1, q2, z3


def _config() -> EEAxisV014HeadConfig:
    return EEAxisV014HeadConfig(
        action_dim=28,
        local_feature_dim=10,
        global_feature_dim=7,
        hidden_layers=(8, 4),
        activation="tanh",
        learning_rate=0.01,
        kappa_bits=TEST_KAPPA,
        beta=0.1,
    )


def test_labels_use_detached_learned_background_and_deterministic_frontier() -> None:
    _states, masks, q1, q2, z3 = _source()
    labels = derive_pivotal_labels(q1, q2, z3, masks, kappa_bits=TEST_KAPPA)

    assert labels.base_actions.tolist() == [2, 0, 0]
    assert labels.teacher_actions.tolist() == [1, 0, 0]
    assert labels.pivotal.tolist() == [True, False, False]
    # Stable rows choose the teacher-surface runner-up, not a random legal
    # action and not the old V0.14 reference action.
    assert labels.runner_up_actions.tolist() == [1, 1, 3]
    assert not labels.background_values.flags.writeable
    assert not labels.teacher_values.flags.writeable


def test_source_contains_one_frontier_pair_per_eligible_row() -> None:
    states, masks, q1, q2, z3 = _source()
    pairs = build_pivotal_pairs(
        states, masks, q1, q2, z3, kappa_bits=TEST_KAPPA
    )

    assert pairs.rows == 3
    assert pairs.pivotal_rows == 1
    assert pairs.stable_rows == 2
    assert pairs.reference_actions.tolist() == [2, 0, 0]
    assert pairs.candidate_actions.tolist() == [1, 1, 3]
    assert pairs.target_surplus_bits.tolist() == [20.0, 1.0, 1.0]
    assert pairs.source_row_indices.tolist() == [0, 1, 2]
    assert not pairs.background_values.flags.writeable


class _FixedSurface(torch.nn.Module):
    """Test-only frozen Q3 output used to inspect the combined objective."""

    def __init__(self, surface: np.ndarray) -> None:
        super().__init__()
        self.register_buffer("surface", torch.tensor(surface, dtype=torch.float32))

    def forward(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        del masks
        if states.shape[0] != self.surface.shape[0]:
            raise AssertionError("fixed test surface row mismatch")
        return self.surface


def test_combined_loss_rewards_pivotal_alignment_and_penalizes_stable_flip() -> None:
    states, masks, q1, q2, z3 = _source()
    pairs = build_pivotal_pairs(
        states, masks, q1, q2, z3, kappa_bits=TEST_KAPPA
    )
    learner = EEAxisV015C3PivotalLearner(_config(), train_seed=162)

    # Exact ZR residual surface reproduces the source teacher on the pivotal
    # row and preserves the two stable rows.
    exact = z3 / TEST_KAPPA
    learner.q = _FixedSurface(exact)
    exact_metrics = learner.measure(pairs)
    assert exact_metrics["pivotal_residual_mse"] == pytest.approx(0.0, abs=1e-12)
    assert exact_metrics["pivotal_decision_violation"] == pytest.approx(0.0, abs=1e-12)
    assert exact_metrics["stable_decision_violation"] == pytest.approx(0.0, abs=1e-12)

    # A positive Q3 on a stable runner-up is not treated as a desired target:
    # the deployment-score stability term becomes strictly positive.
    flipped = exact.copy()
    flipped[1, 1] = 0.5  # B_1(0)=1.0, B_1(1)=0.8 -> stable row flips.
    learner.q = _FixedSurface(flipped)
    flipped_metrics = learner.measure(pairs)
    assert flipped_metrics["stable_decision_violation"] > 0.0


def test_zero_residual_initialization_preserves_background_argmax() -> None:
    states, masks, q1, q2, z3 = _source()
    pairs = build_pivotal_pairs(
        states, masks, q1, q2, z3, kappa_bits=TEST_KAPPA
    )
    learner = EEAxisV015C3PivotalLearner(_config(), train_seed=163)
    q3 = learner.q_values(pairs.states, pairs.action_masks)
    metrics = evaluate_pivotal_decisions(
        q1_values=q1,
        q2_values=q2,
        z3_target_bits=z3,
        q3_values=q3,
        action_masks=masks,
        kappa_bits=TEST_KAPPA,
    )
    assert np.allclose(q3, 0.0)
    assert metrics["stable_preservation"] == pytest.approx(1.0)
    assert metrics["pivotal_agreement"] == pytest.approx(0.0)


def test_checkpoint_state_is_deep_copied_and_strict() -> None:
    learner = EEAxisV015C3PivotalLearner(_config(), train_seed=164)
    payload = learner.checkpoint_state(update_count=0)
    before = {
        key: value.detach().clone()
        for key, value in payload["q"].items()
    }
    with torch.no_grad():
        for parameter in learner.q.parameters():
            parameter.add_(1.0)
    for key, value in before.items():
        torch.testing.assert_close(payload["q"][key], value, rtol=0, atol=0)

    restored = EEAxisV015C3PivotalLearner(_config(), train_seed=164)
    assert restored.load_checkpoint_state(payload) == 0
    with pytest.raises(C3PivotalContractError, match="schema"):
        restored.load_checkpoint_state({**payload, "schema": "stale"})


def test_single_legal_rows_are_not_silently_used_as_pairs() -> None:
    states, masks, q1, q2, z3 = _source()
    masks[2, 0] = False
    masks[2, 1] = False
    masks[2, 2] = False
    masks[2, 3] = True
    labels = derive_pivotal_labels(q1, q2, z3, masks, kappa_bits=TEST_KAPPA)
    assert labels.eligible.tolist() == [True, True, False]
    pairs = build_pivotal_pairs(
        states, masks, q1, q2, z3, kappa_bits=TEST_KAPPA
    )
    assert pairs.rows == 2
