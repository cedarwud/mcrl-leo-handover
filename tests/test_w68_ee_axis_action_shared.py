from __future__ import annotations

import copy

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import (
    ACTION_ALIGNED_FEATURES,
    GLOBAL_FEATURES,
    ActionSharedQNetwork,
    EEAxisActionSharedConfig,
    EEAxisActionSharedTrainer,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.errors import MCRLContractError


ACTION_DIM = 4
STATE_DIM = ACTION_ALIGNED_FEATURES * ACTION_DIM + GLOBAL_FEATURES


def _config(*, beta: float = 0.1) -> EEAxisActionSharedConfig:
    return EEAxisActionSharedConfig(
        state_dim=STATE_DIM,
        action_dim=ACTION_DIM,
        hidden_layers=(8,),
        activation="tanh",
        learning_rate=0.01,
        kappa_bits=10.0,
        beta=beta,
        loss_weights=(1.0, 2.0, 3.0),
    )


def _batch(target: float = 20.0) -> EEAxisPairBatch:
    return EEAxisPairBatch(
        states=np.ones((3, STATE_DIM), dtype=np.float32),
        reference_actions=np.zeros(3, dtype=np.int64),
        candidate_actions=np.ones(3, dtype=np.int64),
        target_surplus_bits=np.full(3, target, dtype=np.float64),
        action_masks=np.ones((3, ACTION_DIM), dtype=np.bool_),
    )


def test_network_is_equivariant_to_action_slot_permutation() -> None:
    config = _config()
    network = ActionSharedQNetwork(config)
    states = torch.arange(2 * STATE_DIM, dtype=torch.float32).reshape(2, STATE_DIM) / 100
    permutation = torch.tensor([2, 0, 3, 1])
    local = states[:, : ACTION_ALIGNED_FEATURES * ACTION_DIM].reshape(
        2, ACTION_ALIGNED_FEATURES, ACTION_DIM
    )
    permuted = torch.cat(
        (
            local[:, :, permutation].reshape(2, -1),
            states[:, ACTION_ALIGNED_FEATURES * ACTION_DIM :],
        ),
        dim=1,
    )
    assert torch.allclose(network(permuted), network(states)[:, permutation])


def test_topology_has_exactly_three_independent_action_shared_q_functions() -> None:
    trainer = EEAxisActionSharedTrainer(_config(), train_seed=7)
    assert len(trainer.q_nets) == 3
    parameter_sets = [
        {id(parameter) for parameter in network.parameters()}
        for network in trainer.q_nets
    ]
    assert not parameter_sets[0] & parameter_sets[1]
    assert not parameter_sets[0] & parameter_sets[2]
    assert not parameter_sets[1] & parameter_sets[2]


def test_route_update_remains_diagonal_and_uses_common_surplus_units() -> None:
    trainer = EEAxisActionSharedTrainer(_config(), train_seed=11)
    before = [copy.deepcopy(network.state_dict()) for network in trainer.q_nets]
    result = trainer.update_route("C3", _batch())
    assert result["route"] == "C3"
    assert any(
        not torch.equal(before[2][name], trainer.q_nets[2].state_dict()[name])
        for name in before[2]
    )
    assert all(
        torch.equal(before[index][name], trainer.q_nets[index].state_dict()[name])
        for index in (0, 1)
        for name in before[index]
    )


def test_zero_gauge_penalty_is_supported_without_changing_pair_target() -> None:
    trainer = EEAxisActionSharedTrainer(_config(beta=0.0), train_seed=13)
    with torch.no_grad():
        for network in trainer.q_nets:
            for parameter in network.parameters():
                parameter.zero_()
    result = trainer.update_route("C2", _batch(target=20.0))
    assert result["pair_mse"] == pytest.approx(4.0)
    assert result["loss"] == pytest.approx(8.0)


def test_checkpoint_roundtrip_and_old_algorithm_rejection() -> None:
    trainer = EEAxisActionSharedTrainer(_config(), train_seed=17)
    trainer.update_route("C1", _batch())
    checkpoint = copy.deepcopy(trainer.checkpoint_state(update_count=9))
    restored = EEAxisActionSharedTrainer(_config(), train_seed=17)
    assert restored.load_checkpoint_state(checkpoint) == 9
    for expected, actual in zip(trainer.q_nets, restored.q_nets, strict=True):
        assert all(
            torch.equal(expected.state_dict()[name], actual.state_dict()[name])
            for name in expected.state_dict()
        )
    with pytest.raises(MCRLContractError, match="not an action-shared"):
        restored.load_checkpoint_state({"algorithm": "legacy"})

    wrong_seed = EEAxisActionSharedTrainer(_config(), train_seed=18)
    with pytest.raises(MCRLContractError, match="train_seed mismatch"):
        wrong_seed.load_checkpoint_state(checkpoint)


def test_state_width_must_match_eight_action_blocks_plus_four_globals() -> None:
    with pytest.raises(ValueError, match="state_dim must equal"):
        EEAxisActionSharedConfig(
            state_dim=STATE_DIM - 1,
            action_dim=ACTION_DIM,
            hidden_layers=(8,),
            activation="tanh",
            learning_rate=0.01,
            kappa_bits=10.0,
            beta=0.1,
            loss_weights=(1.0, 1.0, 1.0),
        )
