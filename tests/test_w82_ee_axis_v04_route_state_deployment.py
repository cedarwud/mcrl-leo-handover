"""Route-specific causal state views with one three-Q deployment argmax."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import (
    EEAxisActionSharedConfig,
    EEAxisActionSharedTrainer,
)


def _trainer() -> EEAxisActionSharedTrainer:
    return EEAxisActionSharedTrainer(
        EEAxisActionSharedConfig(
            state_dim=228,
            action_dim=28,
            hidden_layers=(12,),
            activation="tanh",
            learning_rate=0.001,
            kappa_bits=100.0,
            beta=0.1,
            loss_weights=(1.0, 1.0, 1.0),
        ),
        train_seed=20260901,
    )


def _views(batch: int = 3):
    return {
        "C1": np.full((batch, 228), 0.1, dtype=np.float32),
        "C2": np.full((batch, 228), 0.2, dtype=np.float32),
        "C3": np.full((batch, 228), 0.3, dtype=np.float32),
    }


def test_each_q_receives_only_its_named_view_and_sum_is_direct():
    trainer = _trainer()
    views = _views()
    actual = trainer.q_values_by_route(views)

    with torch.no_grad():
        expected = tuple(
            network(torch.tensor(views[route])).numpy()
            for network, route in zip(trainer.q_nets, ("C1", "C2", "C3"), strict=True)
        )
    for observed, wanted in zip(actual, expected, strict=True):
        assert np.array_equal(observed, wanted)
    assert np.array_equal(
        trainer.deployment_scores_by_route(views),
        expected[0] + expected[1] + expected[2],
    )


def test_changing_only_c3_view_cannot_change_q1_or_q2_surface():
    trainer = _trainer()
    first = _views()
    second = {**first, "C3": np.full((3, 228), 0.9, dtype=np.float32)}

    before = trainer.q_values_by_route(first)
    after = trainer.q_values_by_route(second)

    assert np.array_equal(before[0], after[0])
    assert np.array_equal(before[1], after[1])
    assert not np.array_equal(before[2], after[2])


def test_route_view_selection_uses_one_common_masked_argmax():
    trainer = _trainer()
    views = _views(batch=2)
    masks = np.zeros((2, 28), dtype=np.bool_)
    masks[0, (0, 3, 7)] = True
    masks[1, (2, 5)] = True
    scores = trainer.deployment_scores_by_route(views)

    actions = trainer.select_greedy_actions_by_route(views, masks)

    assert actions.tolist() == [
        int(np.argmax(np.where(masks[0], scores[0], -np.inf))),
        int(np.argmax(np.where(masks[1], scores[1], -np.inf))),
    ]


def test_route_view_contract_rejects_missing_route_or_batch_drift():
    trainer = _trainer()
    views = _views()
    with pytest.raises(ValueError, match="exactly"):
        trainer.q_values_by_route({"C1": views["C1"], "C2": views["C2"]})
    with pytest.raises(ValueError, match="batch"):
        trainer.q_values_by_route({**views, "C3": views["C3"][:2]})

