"""W-147 -- route-local V0.14 action-set learner."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014PairwiseLearner,
    V014ActionSetQNetwork,
)


def _config(*, local: int, global_: int) -> EEAxisV014HeadConfig:
    return EEAxisV014HeadConfig(
        action_dim=4,
        local_feature_dim=local,
        global_feature_dim=global_,
        hidden_layers=(12, 6),
        activation="tanh",
        learning_rate=0.01,
        kappa_bits=10.0,
        beta=0.1,
    )


def _feature_major_state(local: np.ndarray, global_: np.ndarray) -> np.ndarray:
    return np.concatenate((local.T.reshape(-1), global_)).astype(np.float32)


def test_config_supports_distinct_q2_and_q3_state_widths() -> None:
    q2 = EEAxisV014HeadConfig(
        action_dim=28,
        local_feature_dim=16,
        global_feature_dim=0,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=float.fromhex("0x1.2cea89d260f2ap+33"),
        beta=0.1,
    )
    q3 = replace(q2, local_feature_dim=10, global_feature_dim=7)
    assert q2.state_dim == 448
    assert q3.state_dim == 287


def test_network_is_action_permutation_equivariant_and_mask_local() -> None:
    torch.manual_seed(4)
    config = _config(local=3, global_=2)
    network = V014ActionSetQNetwork(config)
    local = np.asarray(
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0], [90.0, 91.0, 92.0]],
        dtype=np.float32,
    )
    state = _feature_major_state(local, np.asarray([0.25, 0.75], dtype=np.float32))
    mask = np.asarray([True, True, True, False])
    original = network(
        torch.tensor(state[None, :]), torch.tensor(mask[None, :])
    ).detach().numpy()[0]

    # An illegal action is excluded from legal-set mean/max context.
    changed = local.copy()
    changed[3] = [-900.0, 800.0, 700.0]
    changed_state = _feature_major_state(changed, np.asarray([0.25, 0.75]))
    changed_q = network(
        torch.tensor(changed_state[None, :]), torch.tensor(mask[None, :])
    ).detach().numpy()[0]
    np.testing.assert_allclose(original[:3], changed_q[:3], rtol=0, atol=1e-6)

    permutation = np.asarray([2, 0, 3, 1])
    permuted_state = _feature_major_state(
        local[permutation], np.asarray([0.25, 0.75])
    )
    permuted_q = network(
        torch.tensor(permuted_state[None, :]),
        torch.tensor(mask[permutation][None, :]),
    ).detach().numpy()[0]
    np.testing.assert_allclose(permuted_q, original[permutation], rtol=0, atol=1e-6)


def test_pairwise_update_reduces_error_without_other_heads() -> None:
    config = _config(local=2, global_=1)
    learner = EEAxisV014PairwiseLearner(config, train_seed=7)
    local = np.asarray(
        [
            [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
            [[0.1, 0.0], [1.1, 0.0], [0.0, 1.1], [1.1, 1.1]],
        ],
        dtype=np.float32,
    )
    states = np.stack(
        [_feature_major_state(row, np.asarray([0.5])) for row in local]
    )
    batch = EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray([0, 0], dtype=np.int64),
        candidate_actions=np.asarray([1, 1], dtype=np.int64),
        target_surplus_bits=np.asarray([10.0, 10.0], dtype=np.float64),
        action_masks=np.ones((2, 4), dtype=np.bool_),
    )
    before = learner.measure(batch)["pair_mse"]
    for _ in range(100):
        learner.update(batch)
    after = learner.measure(batch)["pair_mse"]
    assert after < before * 0.05
    assert len(list(learner.q.parameters())) > 0
    assert not hasattr(learner, "q1")
    assert not hasattr(learner, "q2")
    assert not hasattr(learner, "q3")


def test_checkpoint_roundtrip_is_strict() -> None:
    config = _config(local=2, global_=1)
    learner = EEAxisV014PairwiseLearner(config, train_seed=8)
    states = np.zeros((1, config.state_dim), dtype=np.float32)
    masks = np.ones((1, 4), dtype=np.bool_)
    expected = learner.q_values(states, masks)
    payload = learner.checkpoint_state(update_count=17)

    restored = EEAxisV014PairwiseLearner(config, train_seed=8)
    assert restored.load_checkpoint_state(payload) == 17
    np.testing.assert_array_equal(restored.q_values(states, masks), expected)

    wrong = EEAxisV014PairwiseLearner(_config(local=3, global_=0), train_seed=8)
    with pytest.raises(Exception, match="config"):
        wrong.load_checkpoint_state(payload)


def test_compact_surface_update_is_exactly_equivalent_to_expanded_pairs() -> None:
    config = _config(local=2, global_=1)
    states = np.stack(
        [
            _feature_major_state(
                np.asarray(
                    [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
                    dtype=np.float32,
                ),
                np.asarray([0.2]),
            ),
            _feature_major_state(
                np.asarray(
                    [[0.1, 0.0], [1.1, 0.0], [0.0, 1.1], [1.1, 1.1]],
                    dtype=np.float32,
                ),
                np.asarray([0.8]),
            ),
        ]
    )
    masks = np.asarray(
        [[True, True, True, False], [True, False, True, True]], dtype=np.bool_
    )
    references = np.asarray([0, 2], dtype=np.int64)
    target_surfaces = np.asarray(
        [[0.0, 10.0, -5.0, 0.0], [4.0, 0.0, 0.0, 8.0]],
        dtype=np.float64,
    )
    pair_rows = [(0, 1), (0, 2), (1, 0), (1, 3)]
    expanded = EEAxisPairBatch(
        states=np.stack([states[row] for row, _action in pair_rows]),
        reference_actions=np.asarray(
            [references[row] for row, _action in pair_rows], dtype=np.int64
        ),
        candidate_actions=np.asarray(
            [action for _row, action in pair_rows], dtype=np.int64
        ),
        target_surplus_bits=np.asarray(
            [
                target_surfaces[row, action]
                - target_surfaces[row, references[row]]
                for row, action in pair_rows
            ],
            dtype=np.float64,
        ),
        action_masks=np.stack([masks[row] for row, _action in pair_rows]),
    )

    expanded_learner = EEAxisV014PairwiseLearner(config, train_seed=19)
    compact_learner = EEAxisV014PairwiseLearner(config, train_seed=19)
    pair_metrics = expanded_learner.measure(expanded)
    compact_metrics = compact_learner.measure_surfaces(
        states, masks, references, target_surfaces
    )
    assert compact_metrics == pytest.approx(pair_metrics)

    expanded_learner.update(expanded)
    compact_learner.update_surfaces(states, masks, references, target_surfaces)
    for left, right in zip(
        expanded_learner.q.parameters(), compact_learner.q.parameters(), strict=True
    ):
        torch.testing.assert_close(left, right, rtol=0, atol=1e-7)
