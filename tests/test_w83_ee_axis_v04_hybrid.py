from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_action_shared_meanmax import (
    EEAxisMaskedMeanMaxConfig,
    EEAxisMaskedMeanMaxTrainer,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v04_hybrid import (
    FrozenMeanMaxCheckpointSpec,
    EEAxisV04HybridTrainer,
    extract_frozen_meanmax_head,
    load_frozen_meanmax_head_pair,
)
from mcrl.errors import MCRLContractError


SEED = 2026092101
AUTHORITY = "a" * 64


def _configs() -> tuple[EEAxisMaskedMeanMaxConfig, EEAxisActionSharedConfig]:
    kwargs = {
        "state_dim": 228,
        "action_dim": 28,
        "hidden_layers": (5, 3),
        "activation": "tanh",
        "learning_rate": 0.01,
        "kappa_bits": 100.0,
        "beta": 0.1,
        "loss_weights": (1.0, 1.0, 1.0),
    }
    return EEAxisMaskedMeanMaxConfig(**kwargs), EEAxisActionSharedConfig(**kwargs)


def _checkpoint(tmp_path: Path) -> tuple[FrozenMeanMaxCheckpointSpec, EEAxisMaskedMeanMaxConfig]:
    v03_config, _v04_config = _configs()
    source = EEAxisMaskedMeanMaxTrainer(v03_config, train_seed=SEED)
    path = tmp_path / "init-2026092101-rung-000010.pt"
    torch.save(
        {
            "schema": "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-checkpoint",
            "authority_sha256": AUTHORITY,
            "initialization_seed": SEED,
            "rung": 10,
            "validation_dataset_bytes_opened": True,
            "validation_metrics_computed": True,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "trainer": source.checkpoint_state(update_count=30),
        },
        path,
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return (
        FrozenMeanMaxCheckpointSpec(
            path=path,
            sha256=digest,
            authority_sha256=AUTHORITY,
            initialization_seed=SEED,
        ),
        v03_config,
    )


def _hybrid(tmp_path: Path) -> EEAxisV04HybridTrainer:
    spec, v03_config = _checkpoint(tmp_path)
    _unused, v04_config = _configs()
    return EEAxisV04HybridTrainer.from_sealed_checkpoint(
        spec,
        v03_config=v03_config,
        v04_config=v04_config,
        selected_q3_rung=30,
    )


def _views(rows: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    v03 = np.linspace(-0.4, 0.4, rows * 228, dtype=np.float32).reshape(rows, 228)
    v04 = np.linspace(0.6, 1.4, rows * 228, dtype=np.float32).reshape(rows, 228)
    masks = np.ones((rows, 28), dtype=np.bool_)
    masks[:, 0] = False
    return v03, v04, masks


def _batch(rows: int = 4) -> EEAxisPairBatch:
    states = np.linspace(-0.7, 0.7, rows * 228, dtype=np.float32).reshape(rows, 228)
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.zeros(rows, dtype=np.int64),
        candidate_actions=np.ones(rows, dtype=np.int64),
        target_surplus_bits=np.linspace(5.0, 25.0, rows, dtype=np.float64),
        action_masks=np.ones((rows, 28), dtype=np.bool_),
    )


def test_only_heads_zero_and_one_are_extracted_with_exact_lineage(tmp_path: Path) -> None:
    spec, config = _checkpoint(tmp_path)
    pair = load_frozen_meanmax_head_pair(spec, config)
    head0, lineage0 = extract_frozen_meanmax_head(
        spec, config, head_index=0
    )
    head1, lineage1 = extract_frozen_meanmax_head(
        spec, config, head_index=1
    )

    assert pair.q1_lineage.head_index == lineage0.head_index == 0
    assert pair.q2_lineage.head_index == lineage1.head_index == 1
    assert pair.q1_lineage.checkpoint_sha256 == spec.sha256
    assert pair.q2_lineage.authority_sha256 == AUTHORITY
    for expected, actual in (
        (pair.q1.state_dict(), head0.state_dict()),
        (pair.q2.state_dict(), head1.state_dict()),
    ):
        assert all(torch.equal(expected[name], actual[name]) for name in expected)
    with pytest.raises(MCRLContractError, match="only head indices"):
        extract_frozen_meanmax_head(spec, config, head_index=2)


def test_strict_lineage_rejects_hash_seed_authority_rung_and_config_drift(tmp_path: Path) -> None:
    spec, config = _checkpoint(tmp_path)
    _unused, v04_config = _configs()

    with pytest.raises(MCRLContractError, match="bytes"):
        load_frozen_meanmax_head_pair(
            FrozenMeanMaxCheckpointSpec(
                path=spec.path,
                sha256="0" * 64,
                authority_sha256=AUTHORITY,
                initialization_seed=SEED,
            ),
            config,
        )
    with pytest.raises(MCRLContractError, match="initialization_seed"):
        load_frozen_meanmax_head_pair(
            FrozenMeanMaxCheckpointSpec(
                path=spec.path,
                sha256=spec.sha256,
                authority_sha256=AUTHORITY,
                initialization_seed=SEED + 1,
            ),
            config,
        )
    with pytest.raises(MCRLContractError, match="authority"):
        load_frozen_meanmax_head_pair(
            FrozenMeanMaxCheckpointSpec(
                path=spec.path,
                sha256=spec.sha256,
                authority_sha256="b" * 64,
                initialization_seed=SEED,
            ),
            config,
        )
    with pytest.raises(MCRLContractError, match="rung 10"):
        FrozenMeanMaxCheckpointSpec(
            path=spec.path,
            sha256=spec.sha256,
            authority_sha256=AUTHORITY,
            initialization_seed=SEED,
            rung=30,
        )
    wrong_config = EEAxisMaskedMeanMaxConfig(
        state_dim=228,
        action_dim=28,
        hidden_layers=(7, 3),
        activation="tanh",
        learning_rate=0.01,
        kappa_bits=100.0,
        beta=0.1,
        loss_weights=(1.0, 1.0, 1.0),
    )
    with pytest.raises(MCRLContractError, match="config"):
        load_frozen_meanmax_head_pair(spec, wrong_config)
    trainer = EEAxisV04HybridTrainer.from_sealed_checkpoint(
        spec,
        v03_config=config,
        v04_config=v04_config,
        selected_q3_rung=30,
    )
    assert trainer.selected_q3_rung == 30


def test_hybrid_has_exactly_three_networks_and_isolates_v03_from_v04_views(tmp_path: Path) -> None:
    trainer = _hybrid(tmp_path)
    v03, v04, masks = _views()
    first = trainer.q_values_by_route(v03, v04, masks)
    changed_v04 = v04 + 0.75
    second = trainer.q_values_by_route(v03, changed_v04, masks)

    assert len(trainer.q_nets) == 3
    assert trainer.q1 is trainer.q_nets[0]
    assert trainer.q2 is trainer.q_nets[1]
    assert trainer.q3 is trainer.q_nets[2]
    assert not trainer.q1.training and not trainer.q2.training
    assert trainer.q3.training
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])
    assert not np.array_equal(first[2], second[2])
    assert not hasattr(trainer, "q1_optimizer")
    assert not hasattr(trainer, "q2_optimizer")


def test_deployment_is_direct_sum_one_masked_argmax_and_drop_c3_reuses_q1_q2(
    tmp_path: Path,
) -> None:
    trainer = _hybrid(tmp_path)
    v03, v04, masks = _views(rows=2)
    q1, q2, q3 = trainer.q_values_by_route(v03, v04, masks)
    full = trainer.deployment_scores(v03, v04, masks)
    drop = trainer.deployment_scores(v03, v04, masks, drop_c3=True)
    assert np.array_equal(full, q1 + q2 + q3)
    assert np.array_equal(drop, q1 + q2)
    assert np.array_equal(
        trainer.select_greedy_actions(v03, v04, masks),
        np.argmax(np.where(masks, full, -np.inf), axis=1),
    )
    assert np.array_equal(
        trainer.select_greedy_actions(v03, v04, masks, drop_c3=True),
        np.argmax(np.where(masks, drop, -np.inf), axis=1),
    )


def test_update_c3_changes_only_q3_and_leaves_frozen_heads_bitwise_unchanged(
    tmp_path: Path,
) -> None:
    trainer = _hybrid(tmp_path)
    frozen_before = [copy.deepcopy(network.state_dict()) for network in trainer.q_nets[:2]]
    q3_before = copy.deepcopy(trainer.q3.state_dict())
    result = trainer.update_c3(_batch())

    assert result["route"] == "C3"
    assert result["update_count"] == 1
    for before, network in zip(frozen_before, trainer.q_nets[:2], strict=True):
        assert all(torch.equal(before[name], network.state_dict()[name]) for name in before)
        assert all(parameter.grad is None for parameter in network.parameters())
    assert any(
        not torch.equal(q3_before[name], trainer.q3.state_dict()[name])
        for name in q3_before
    )
    with pytest.raises(MCRLContractError, match="only for C3"):
        trainer.update_route("C1", _batch())


def test_selected_hybrid_reload_treats_q1_q2_as_receipts(tmp_path: Path) -> None:
    spec, v03_config = _checkpoint(tmp_path)
    _unused, v04_config = _configs()
    trainer = EEAxisV04HybridTrainer.from_sealed_checkpoint(
        spec,
        v03_config=v03_config,
        v04_config=v04_config,
        selected_q3_rung=30,
    )
    for _ in range(trainer.selected_q3_rung):
        trainer.update_c3(_batch())
    state = trainer.checkpoint_state()

    restored = EEAxisV04HybridTrainer.from_sealed_checkpoint(
        spec,
        v03_config=v03_config,
        v04_config=v04_config,
        selected_q3_rung=30,
    )
    assert restored.load_checkpoint_state(state) == trainer.selected_q3_rung
    assert all(
        torch.equal(trainer.q3.state_dict()[name], restored.q3.state_dict()[name])
        for name in trainer.q3.state_dict()
    )

    drifted = copy.deepcopy(state)
    first_name = next(iter(drifted["q_networks"][0]))
    drifted["q_networks"][0][first_name].view(-1)[0] += 1.0
    with pytest.raises(MCRLContractError, match="frozen-head tensor drifted"):
        restored.load_checkpoint_state(drifted)
