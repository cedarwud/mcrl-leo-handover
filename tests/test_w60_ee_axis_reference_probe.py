"""W-60 -- offline E1 frozen-Main reference-action probe."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_reference_probe import (
    E1_REFERENCE_PROBE_HIDDEN_LAYERS,
    E1ReferenceProbeConfig,
    E1ReferenceProbeError,
    run_reference_action_probe,
)


def _data(repetitions: int):
    states = []
    actions = []
    clusters = []
    for index in range(repetitions):
        states.extend(([-1.0, float(index) / repetitions], [1.0, float(index) / repetitions]))
        actions.extend((0, 1))
        clusters.extend((f"cluster-{index}", f"cluster-{index}"))
    values = np.asarray(states, dtype=np.float32)
    masks = np.ones((values.shape[0], 2), dtype=np.bool_)
    return values, masks, np.asarray(actions, dtype=np.int64), clusters


def test_probe_architecture_is_fixed_and_learns_state_conditioned_reference_action() -> None:
    train_x, train_m, train_y, _train_clusters = _data(20)
    test_x, test_m, test_y, test_clusters = _data(8)
    config = E1ReferenceProbeConfig(
        state_dim=2,
        action_dim=2,
        learning_rate=0.01,
        updates=100,
        bootstrap_replications=200,
    )
    result = run_reference_action_probe(
        train_states=train_x,
        train_masks=train_m,
        train_reference_actions=train_y,
        test_states=test_x,
        test_masks=test_m,
        test_reference_actions=test_y,
        test_cluster_ids=test_clusters,
        config=config,
        train_seed=7,
        bootstrap_seed=11,
    )
    assert E1_REFERENCE_PROBE_HIDDEN_LAYERS == (100, 50, 50)
    assert result.final_cross_entropy < result.initial_cross_entropy
    assert result.probe_top1_accuracy == pytest.approx(1.0)
    assert result.action_prior_top1_accuracy == pytest.approx(0.5)
    assert result.relative_error_reduction == pytest.approx(1.0)
    assert result.relative_error_reduction_interval.lower == pytest.approx(1.0)


def test_probe_rejects_illegal_reference_action() -> None:
    with pytest.raises(E1ReferenceProbeError, match="violates its mask"):
        run_reference_action_probe(
            train_states=np.zeros((2, 2), dtype=np.float32),
            train_masks=np.asarray([[True, False], [True, False]], dtype=np.bool_),
            train_reference_actions=np.asarray([0, 1]),
            test_states=np.zeros((2, 2), dtype=np.float32),
            test_masks=np.ones((2, 2), dtype=np.bool_),
            test_reference_actions=np.asarray([0, 1]),
            test_cluster_ids=["a", "b"],
            config=E1ReferenceProbeConfig(
                state_dim=2,
                action_dim=2,
                updates=1,
                bootstrap_replications=100,
            ),
            train_seed=1,
            bootstrap_seed=2,
        )

