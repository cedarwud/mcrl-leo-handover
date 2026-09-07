from __future__ import annotations

import copy

import numpy as np
import pytest
import torch
import torch.nn as nn

from mcrl.algorithms.ee_axis_pairwise import (
    EEAxisPairBatch,
    EEAxisPairwiseConfig,
    EEAxisPairwiseTrainer,
)
from mcrl.env.action_contract import NO_OP_ACTION
from mcrl.errors import MCRLContractError


STATE_DIM = 5
ACTION_DIM = 4


def _config() -> EEAxisPairwiseConfig:
    return EEAxisPairwiseConfig(
        state_dim=STATE_DIM,
        action_dim=ACTION_DIM,
        hidden_layers=(8,),
        activation="tanh",
        learning_rate=0.01,
        kappa_bits=10.0,
        beta=0.1,
        loss_weights=(1.0, 2.0, 3.0),
    )


def _batch(target: float = 20.0) -> EEAxisPairBatch:
    masks = np.ones((3, ACTION_DIM), dtype=np.bool_)
    return EEAxisPairBatch(
        states=np.ones((3, STATE_DIM), dtype=np.float32),
        reference_actions=np.zeros(3, dtype=np.int64),
        candidate_actions=np.ones(3, dtype=np.int64),
        target_surplus_bits=np.full(3, target, dtype=np.float64),
        action_masks=masks,
    )


def _snapshot(trainer: EEAxisPairwiseTrainer):
    return [
        {name: value.detach().clone() for name, value in network.state_dict().items()}
        for network in trainer.q_nets
    ]


def _equal(left, right) -> bool:
    return all(
        left[index].keys() == right[index].keys()
        and all(torch.equal(left[index][key], right[index][key]) for key in left[index])
        for index in range(3)
    )


def test_topology_is_exactly_three_independent_online_q_functions() -> None:
    trainer = EEAxisPairwiseTrainer(_config(), train_seed=7)
    assert len(trainer.q_nets) == 3
    assert len(trainer.optimizers) == 3
    assert not hasattr(trainer, "target_nets")
    parameter_sets = [
        {id(parameter) for parameter in network.parameters()}
        for network in trainer.q_nets
    ]
    assert not parameter_sets[0] & parameter_sets[1]
    assert not parameter_sets[0] & parameter_sets[2]
    assert not parameter_sets[1] & parameter_sets[2]


def test_route_update_is_diagonal() -> None:
    trainer = EEAxisPairwiseTrainer(_config(), train_seed=11)
    before = _snapshot(trainer)
    result = trainer.update_route("C2", _batch())
    after = _snapshot(trainer)
    assert result["route"] == "C2"
    assert result["batch_size"] == 3
    assert not _equal(before, after)
    assert all(torch.equal(before[0][key], after[0][key]) for key in before[0])
    assert all(torch.equal(before[2][key], after[2][key]) for key in before[2])
    assert any(not torch.equal(before[1][key], after[1][key]) for key in before[1])


def test_shared_kappa_and_route_loss_weight_are_applied() -> None:
    trainer = EEAxisPairwiseTrainer(_config(), train_seed=13)
    with torch.no_grad():
        for network in trainer.q_nets:
            for parameter in network.parameters():
                parameter.zero_()
    result = trainer.update_route("C3", _batch(target=20.0))
    # target/kappa = 2, pair MSE = 4, C3 loss weight = 3, gauge = 0.
    assert result["pair_mse"] == pytest.approx(4.0)
    assert result["loss"] == pytest.approx(12.0)


def test_candidate_reference_swap_and_target_sign_are_symmetric() -> None:
    first = EEAxisPairwiseTrainer(_config(), train_seed=17)
    second = EEAxisPairwiseTrainer(_config(), train_seed=17)
    forward = _batch(target=20.0)
    reverse = EEAxisPairBatch(
        states=forward.states,
        reference_actions=forward.candidate_actions,
        candidate_actions=forward.reference_actions,
        target_surplus_bits=-forward.target_surplus_bits,
        action_masks=forward.action_masks,
    )
    assert first.update_route("C1", forward)["pair_mse"] == pytest.approx(
        second.update_route("C1", reverse)["pair_mse"]
    )


class _Fixed(nn.Module):
    def __init__(self, row: list[float]) -> None:
        super().__init__()
        self.register_buffer("row", torch.tensor(row, dtype=torch.float32))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.row[None, :].expand(values.shape[0], -1)


def test_deployment_is_one_masked_argmax_of_the_unweighted_sum() -> None:
    trainer = EEAxisPairwiseTrainer(_config(), train_seed=19)
    trainer.q_nets[0] = _Fixed([0.0, 4.0, 0.0, 0.0])
    trainer.q_nets[1] = _Fixed([0.0, 0.0, 3.0, 0.0])
    trainer.q_nets[2] = _Fixed([0.0, 0.0, 3.0, 5.0])
    states = np.zeros((2, STATE_DIM), dtype=np.float32)
    masks = np.array(
        [[True, True, True, True], [True, True, False, False]], dtype=np.bool_
    )
    actions = trainer.select_greedy_actions(states, masks)
    assert actions.tolist() == [2, 1]

    masks[1] = False
    actions = trainer.select_greedy_actions(states, masks)
    assert actions[1] == NO_OP_ACTION


def test_pair_actions_must_be_valid_under_the_stored_mask() -> None:
    trainer = EEAxisPairwiseTrainer(_config(), train_seed=23)
    batch = _batch()
    batch.action_masks[0, 1] = False
    with pytest.raises(MCRLContractError, match="candidate action is invalid"):
        trainer.update_route("C1", batch)


def test_checkpoint_roundtrip_and_legacy_rejection() -> None:
    trainer = EEAxisPairwiseTrainer(_config(), train_seed=29)
    trainer.update_route("C1", _batch())
    expected = _snapshot(trainer)
    state = copy.deepcopy(trainer.checkpoint_state(update_count=5))

    restored = EEAxisPairwiseTrainer(_config(), train_seed=29)
    assert restored.load_checkpoint_state(state) == 5
    assert _equal(expected, _snapshot(restored))

    with pytest.raises(MCRLContractError, match="not a Multi-Catfish V0.3"):
        restored.load_checkpoint_state({"format_version": 1, "q_networks": []})
