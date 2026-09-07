from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_action_shared_meanmax import (
    EEAxisMaskedMeanMaxConfig,
    EEAxisMaskedMeanMaxTrainer,
    MaskedMeanMaxQNetwork,
    config_from_action_shared,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch, ROUTE_NAMES


def _config(action_dim: int = 3) -> EEAxisMaskedMeanMaxConfig:
    return EEAxisMaskedMeanMaxConfig(
        state_dim=8 * action_dim + 4,
        action_dim=action_dim,
        hidden_layers=(7, 5),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=2.0,
        beta=0.1,
        loss_weights=(1.0, 1.0, 1.0),
    )


def _states(rows: int = 2, action_dim: int = 3) -> np.ndarray:
    values = np.arange(rows * (8 * action_dim + 4), dtype=np.float32)
    return (values.reshape(rows, -1) / 17.0).astype(np.float32)


def _permute_action_slots(states: np.ndarray, permutation: list[int]) -> np.ndarray:
    action_dim = len(permutation)
    result = np.array(states, copy=True)
    for feature in range(8):
        start = feature * action_dim
        result[:, start : start + action_dim] = states[:, start : start + action_dim][
            :, permutation
        ]
    return result


def test_masked_meanmax_uses_explicit_mask_when_state_access_disagrees() -> None:
    config = _config()
    network = MaskedMeanMaxQNetwork(config)
    states = np.zeros((1, config.state_dim), dtype=np.float32)
    # Feature 1 deliberately has a large value in the masked-out slot.  The
    # state access feature itself is intentionally inconsistent with masks.
    states[0, :3] = [1.0, 1.0, 1.0]
    states[0, 3:6] = [1.0, 100.0, 3.0]
    masks = np.asarray([[True, False, True]], dtype=np.bool_)
    import torch

    features = network._features(
        torch.tensor(states), torch.tensor(masks, dtype=torch.bool)
    ).detach().numpy()
    # Input order is local 8, global 4, masked mean 8, masked max 8.
    assert features[0, 0, 12 + 1] == pytest.approx(2.0)
    assert features[0, 0, 20 + 1] == pytest.approx(3.0)
    # An explicit mask must work even when every state access bit is zero.
    states[0, :3] = 0.0
    trainer = EEAxisMaskedMeanMaxTrainer(config, train_seed=10)
    surfaces = trainer.q_values(states, masks)
    assert all(np.isfinite(surface).all() for surface in surfaces)


def test_masked_meanmax_is_permutation_equivariant() -> None:
    config = _config()
    trainer = EEAxisMaskedMeanMaxTrainer(config, train_seed=11)
    states = _states()
    masks = np.asarray([[True, False, True], [False, True, True]], dtype=np.bool_)
    permutation = [2, 0, 1]
    permuted_states = _permute_action_slots(states, permutation)
    permuted_masks = masks[:, permutation]
    original = trainer.q_values(states, masks)
    permuted = trainer.q_values(permuted_states, permuted_masks)
    for expected, actual in zip(original, permuted, strict=True):
        np.testing.assert_allclose(actual, expected[:, permutation], rtol=0.0, atol=1e-6)


def test_masked_out_extreme_features_do_not_change_legal_scores() -> None:
    config = _config()
    trainer = EEAxisMaskedMeanMaxTrainer(config, train_seed=12)
    states = _states(rows=1)
    masks = np.asarray([[True, False, True]], dtype=np.bool_)
    altered = np.array(states, copy=True)
    for feature in range(8):
        altered[0, feature * 3 + 1] = 1_000_000.0 * (feature + 1)
    baseline = trainer.q_values(states, masks)
    changed = trainer.q_values(altered, masks)
    legal = masks[0]
    for expected, actual in zip(baseline, changed, strict=True):
        np.testing.assert_allclose(actual[0, legal], expected[0, legal], rtol=0.0, atol=1e-6)


def test_trainer_requires_explicit_nonempty_boolean_masks() -> None:
    config = _config()
    trainer = EEAxisMaskedMeanMaxTrainer(config, train_seed=13)
    states = _states(rows=1)
    with pytest.raises(ValueError, match="Boolean"):
        trainer.q_values(states, np.ones((1, 3), dtype=np.float32))
    with pytest.raises(ValueError, match="at least one"):
        trainer.q_values(states, np.zeros((1, 3), dtype=np.bool_))


def test_fallback_keeps_scalar_hyperparameters_and_checkpoint_reload() -> None:
    primary = EEAxisActionSharedConfig(
        state_dim=28,
        action_dim=3,
        hidden_layers=(7, 5),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=2.0,
        beta=0.1,
        loss_weights=(1.0, 1.0, 1.0),
    )
    config = config_from_action_shared(primary)
    assert config.learning_rate == primary.learning_rate
    assert config.beta == primary.beta
    assert config.kappa_bits == primary.kappa_bits
    states = _states(rows=4)
    masks = np.asarray(
        [[True, True, False], [True, False, True], [False, True, True], [True, True, True]],
        dtype=np.bool_,
    )
    batch = EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray([0, 0, 1, 2], dtype=np.int64),
        candidate_actions=np.asarray([1, 2, 2, 0], dtype=np.int64),
        target_surplus_bits=np.asarray([1.0, -0.5, 0.25, 0.0], dtype=np.float64),
        action_masks=masks,
    )
    trainer = EEAxisMaskedMeanMaxTrainer(config, train_seed=14)
    trainer.update_route(ROUTE_NAMES[0], batch)
    checkpoint = trainer.checkpoint_state(update_count=1)
    restored = EEAxisMaskedMeanMaxTrainer(config, train_seed=14)
    assert restored.load_checkpoint_state(checkpoint) == 1
    for expected, actual in zip(
        trainer.q_values(states, masks), restored.q_values(states, masks), strict=True
    ):
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-7)
