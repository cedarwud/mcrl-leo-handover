"""W-106 -- exact V0.6 C2-k1 Q2-only learner."""

from __future__ import annotations

import copy

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v06_c2_k1 import (
    EEAxisV06C2K1Trainer,
    V06_C2_K1_ADAM,
    V06_C2_K1_LINEAGES,
    V06_C2_K1_ROWS,
    V06_C2_K1_SEED_BY_LINEAGE,
    V06_C2_K1_UPDATES,
    q2_parameter_sha256,
)
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM


EXPECTED_UPDATE0 = {
    "q13-a": "502a1c13f840d21d94730ec2502eb2a9384294dc26f938c233a28a24b2c441a6",
    "q13-b": "050ac3b794f4db81748b464fd0a4eecd0c228cab5572d839e53bb5b9b673fd4e",
    "q13-c": "da4abd36fe154c240839df89560c504ec95458df221c408f312144bf05cb47d7",
}


def _batch() -> EEAxisPairBatch:
    anchor_states = np.arange(12 * EE_AXIS_STATE_DIM, dtype=np.float32).reshape(
        12, EE_AXIS_STATE_DIM
    ) / 1000.0
    states = np.repeat(anchor_states, 28, axis=0)
    references = np.repeat(np.arange(12, dtype=np.int64) % 28, 28)
    candidates = np.tile(np.arange(28, dtype=np.int64), 12)
    targets = (candidates.astype(np.float64) - references.astype(np.float64)) * 1e8
    masks = np.ones((V06_C2_K1_ROWS, 28), dtype=np.bool_)
    return EEAxisPairBatch(
        states=states,
        reference_actions=references,
        candidate_actions=candidates,
        target_surplus_bits=targets,
        action_masks=masks,
    )


@pytest.mark.parametrize("lineage", V06_C2_K1_LINEAGES)
def test_update0_parameter_digest_is_frozen_and_reproducible(lineage: str) -> None:
    seed = V06_C2_K1_SEED_BY_LINEAGE[lineage]
    first = EEAxisV06C2K1Trainer(lineage=lineage, train_seed=seed)
    second = EEAxisV06C2K1Trainer(lineage=lineage, train_seed=seed)
    assert first.update0_parameter_sha256 == EXPECTED_UPDATE0[lineage]
    assert second.update0_parameter_sha256 == EXPECTED_UPDATE0[lineage]
    assert q2_parameter_sha256(first.q2) == EXPECTED_UPDATE0[lineage]


def test_trainer_owns_only_q2_and_exact_adam_parameters() -> None:
    trainer = EEAxisV06C2K1Trainer(
        lineage="q13-a", train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-a"]
    )
    assert not hasattr(trainer, "q1")
    assert not hasattr(trainer, "q3")
    assert not hasattr(trainer, "q_nets")
    optimizer_ids = {
        id(parameter)
        for group in trainer.optimizer.param_groups
        for parameter in group["params"]
    }
    assert optimizer_ids == {id(parameter) for parameter in trainer.q2.parameters()}
    group = trainer.optimizer.param_groups[0]
    assert group["lr"] == V06_C2_K1_ADAM["lr"]
    assert group["betas"] == V06_C2_K1_ADAM["betas"]
    assert group["eps"] == V06_C2_K1_ADAM["eps"]
    assert group["weight_decay"] == V06_C2_K1_ADAM["weight_decay"]
    assert group["amsgrad"] is V06_C2_K1_ADAM["amsgrad"]
    assert torch.are_deterministic_algorithms_enabled() is True
    assert torch.get_num_threads() == 1


def test_empty_mask_rows_are_not_evaluated_and_remain_zero() -> None:
    trainer = EEAxisV06C2K1Trainer(
        lineage="q13-a", train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-a"]
    )
    states = np.zeros((2, EE_AXIS_STATE_DIM), dtype=np.float32)
    masks = np.asarray([[False] * 28, [True] * 28], dtype=np.bool_)
    values = trainer.q2_values(states, masks)
    assert values.shape == (2, 28)
    assert np.array_equal(values[0], np.zeros(28, dtype=np.float32))
    assert np.all(np.isfinite(values[1]))


def test_exact_100_update_budget_and_update100_reload() -> None:
    trainer = EEAxisV06C2K1Trainer(
        lineage="q13-a", train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-a"]
    )
    update0 = trainer.checkpoint_state()
    assert update0["update_count"] == 0
    batch = _batch()
    receipt = None
    for _ in range(V06_C2_K1_UPDATES):
        receipt = trainer.update(batch)
    assert receipt is not None and receipt["update_count"] == 100
    update100 = trainer.checkpoint_state()
    assert update100["update_count"] == 100
    with pytest.raises(MCRLContractError, match="exhausted"):
        trainer.update(batch)
    reloaded = EEAxisV06C2K1Trainer(
        lineage="q13-a", train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-a"]
    )
    assert reloaded.load_checkpoint_state(update100) == 100
    assert q2_parameter_sha256(reloaded.q2) == update100["parameter_sha256"]


def test_batch_must_be_canonical_and_byte_stable_across_updates() -> None:
    trainer = EEAxisV06C2K1Trainer(
        lineage="q13-b", train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-b"]
    )
    batch = _batch()
    trainer.update(batch)
    changed = copy.deepcopy(batch)
    changed.target_surplus_bits[0] = 1.0
    with pytest.raises(MCRLContractError, match="batch changed"):
        trainer.update(changed)

    shuffled = _batch()
    shuffled.candidate_actions[[0, 1]] = shuffled.candidate_actions[[1, 0]]
    other = EEAxisV06C2K1Trainer(
        lineage="q13-b", train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-b"]
    )
    with pytest.raises(ValueError, match="canonical action"):
        other.update(shuffled)


def test_wrong_seed_device_or_checkpoint_rung_is_rejected() -> None:
    with pytest.raises(ValueError, match="train_seed"):
        EEAxisV06C2K1Trainer(lineage="q13-a", train_seed=1)
    with pytest.raises(ValueError, match="CPU"):
        EEAxisV06C2K1Trainer(
            lineage="q13-a",
            train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-a"],
            device="cuda",
        )
    trainer = EEAxisV06C2K1Trainer(
        lineage="q13-c", train_seed=V06_C2_K1_SEED_BY_LINEAGE["q13-c"]
    )
    trainer.update(_batch())
    with pytest.raises(MCRLContractError, match="update-0 and update-100"):
        trainer.checkpoint_state()
