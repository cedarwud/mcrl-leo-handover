"""W-158 -- deployable V0.14 Q3 precision-calibrated support bonus."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from mcrl.algorithms.ee_axis_v014_q3_support_head import (
    Q3SupportMixtureLearner,
    V014_Q3_SUPPORT_STATE_DIM,
    natural_probability_from_balanced_logit,
    q3_support_config,
)


def _config():
    return q3_support_config(hidden_layers=(4,), learning_rate=0.01, kappa_bits=100.0)


def _batch(*, rows: int = 4):
    rng = np.random.default_rng(158)
    states = rng.normal(size=(rows, V014_Q3_SUPPORT_STATE_DIM)).astype(np.float32)
    masks = np.zeros((rows, 28), dtype=np.bool_)
    masks[:, :2] = True
    references = np.zeros(rows, dtype=np.int64)
    targets = np.zeros((rows, 28), dtype=np.float64)
    compatibility = np.zeros((rows, 28), dtype=np.bool_)
    # One positive comparison and three negatives give a 1/4 support prior.
    targets[0, 1] = 100.0
    targets[1:, 1] = -100.0
    compatibility[0, 1] = True
    return states, masks, references, targets, compatibility


def _learner(*, seed: int = 158, prior: float = 0.25, threshold: float = 0.5):
    return Q3SupportMixtureLearner(
        _config(),
        positive_prior=prior,
        support_threshold=threshold,
        train_seed=seed,
    )


def test_arm_a_keeps_the_287d_action_set_and_two_independent_scorers() -> None:
    learner = _learner()
    assert learner.config.state_dim == 287
    assert learner.config.state_dim == V014_Q3_SUPPORT_STATE_DIM
    classifier_ids = {id(parameter) for parameter in learner.classifier.parameters()}
    amplitude_ids = {
        id(parameter) for parameter in learner.positive_amplitude.parameters()
    }
    assert classifier_ids.isdisjoint(amplitude_ids)


def test_balanced_logit_prior_correction_and_thresholded_nonnegative_bonus() -> None:
    corrected = natural_probability_from_balanced_logit(
        torch.tensor([0.0]), positive_prior=0.04
    )
    assert float(corrected[0]) == pytest.approx(0.04)

    learner = _learner()
    states, masks, references, targets, compatibility = _batch()
    with torch.no_grad():
        for network in (learner.classifier, learner.positive_amplitude):
            for parameter in network.parameters():
                parameter.zero_()
    metrics = learner.update(states, masks, references, targets, compatibility)
    assert metrics["support_count"] == 1
    assert metrics["comparison_count"] == 4
    assert metrics["balanced_bce"] == pytest.approx(np.log(2.0))

    # Make the natural posterior exceed the frozen threshold while retaining
    # a zero amplitude path, so the exact bonus formula is observable.
    with torch.no_grad():
        for network in (learner.classifier, learner.positive_amplitude):
            for parameter in network.parameters():
                parameter.zero_()
        learner.classifier.scorer[-1].bias.fill_(2.0)
    probability, positive, q_values = learner.predict(states, masks)
    assert probability.shape == positive.shape == q_values.shape == (4, 28)
    assert np.all(q_values >= 0.0)
    expected = float(probability[0, 1]) * np.log(2.0)
    assert q_values[0, 1] == pytest.approx(expected, abs=1e-6)
    with pytest.raises(TypeError):
        learner.q_values(states, masks, references)


def test_checkpoint_roundtrip_restores_calibration_optimizer_and_count() -> None:
    states, masks, references, targets, compatibility = _batch()
    learner = _learner(seed=17, prior=0.25, threshold=0.6)
    learner.update(states, masks, references, targets, compatibility)
    expected = learner.q_values(states, masks)
    payload = learner.checkpoint_state()

    assert payload["positive_prior"] == 0.25
    assert payload["support_threshold"] == 0.6
    assert "unsupported_mean" not in payload
    assert payload["config"] == dict(payload["config"])
    assert payload["update_count"] == 1

    restored = _learner(seed=17, prior=0.25, threshold=0.6)
    assert restored.load_checkpoint_state(payload) == 1
    assert restored.update_count == 1
    np.testing.assert_array_equal(restored.q_values(states, masks), expected)

    wrong_prior = _learner(seed=17, prior=0.5, threshold=0.6)
    with pytest.raises(Exception, match="positive_prior"):
        wrong_prior.load_checkpoint_state(payload)
    wrong_threshold = _learner(seed=17, prior=0.25, threshold=0.7)
    with pytest.raises(Exception, match="support_threshold"):
        wrong_threshold.load_checkpoint_state(payload)
    damaged = deepcopy(payload)
    damaged["config"]["global_feature_dim"] = 17
    with pytest.raises(Exception, match="config"):
        restored.load_checkpoint_state(damaged)


def test_same_seed_and_checkpoint_continuation_are_deterministic() -> None:
    states, masks, references, targets, compatibility = _batch()
    left = _learner(seed=41)
    right = _learner(seed=41)
    left_metrics = left.update(states, masks, references, targets, compatibility)
    right_metrics = right.update(states, masks, references, targets, compatibility)
    assert left_metrics == right_metrics
    np.testing.assert_array_equal(
        left.q_values(states, masks),
        right.q_values(states, masks),
    )

    checkpoint = left.checkpoint_state()
    resumed = _learner(seed=41)
    assert resumed.load_checkpoint_state(checkpoint) == 1
    left.update(states, masks, references, targets, compatibility)
    resumed.update(states, masks, references, targets, compatibility)
    np.testing.assert_array_equal(
        left.q_values(states, masks),
        resumed.q_values(states, masks),
    )
