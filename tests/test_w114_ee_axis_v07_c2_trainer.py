"""W-114 -- V0.7 focal-next fresh Q2 and legal-mask centering."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_v07_c2_focal_next import (
    EEAxisV07C2Trainer,
    V07_C2_SEED_BY_ROLE_LINEAGE,
    center_legal_surface,
    q2_parameter_sha256,
)
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)
from mcrl.runtime.ee_axis_v07_c2_dataset import (
    V07C2Dataset,
    V07C2DecisionCoverage,
    V07C2Row,
)
from mcrl.runtime.ee_axis_v07_c2_focal_next import focal_next_surplus_target


def _trainer(*, lineage: str = "q13-a", role: str = "provisional") -> EEAxisV07C2Trainer:
    return EEAxisV07C2Trainer(
        lineage=lineage,
        role=role,
        train_seed=V07_C2_SEED_BY_ROLE_LINEAGE[role][lineage],
    )


def _target(value: float):
    base = 1.0e9
    return focal_next_surplus_target(
        lambda_bits_per_j=1.0,
        interval_s=1.0,
        candidate_focal_rate_bps=base + value,
        reference_focal_rate_bps=base,
        candidate_full_power_w=10.0,
        candidate_without_focal_power_w=8.0,
        reference_full_power_w=10.0,
        reference_without_focal_power_w=8.0,
    )


def _dataset(*, lineage: str = "q13-a", role: str = "provisional") -> V07C2Dataset:
    round_name = "bootstrap" if role == "provisional" else "refresh"
    specs = (
        (0, (0, 3), 0, (0.0, -2.0e8)),
        (1, (1, 4, 9), 1, (0.0, 3.0e8, -1.0e8)),
        (2, (2, 6), 2, (0.0, 5.0e7)),
    )
    rows: list[V07C2Row] = []
    coverage: list[V07C2DecisionCoverage] = []
    for world, actions, reference, targets in specs:
        mask = np.zeros(28, dtype=np.bool_)
        mask[list(actions)] = True
        state = np.full(V07_C2_Q2_STATE_DIM, world / 10.0, dtype=np.float32)
        coverage.append(
            V07C2DecisionCoverage(
                lineage=lineage,
                refresh_round=round_name,
                world_id=world,
                step_index=world,
                focal_user=world,
                action_mask=mask,
            )
        )
        for action, target in zip(actions, targets, strict=True):
            rows.append(
                V07C2Row(
                    lineage=lineage,
                    refresh_round=round_name,
                    world_id=world,
                    step_index=world,
                    focal_user=world,
                    state=state,
                    action_mask=mask,
                    reference_action=reference,
                    candidate_action=action,
                    target=_target(target),
                )
            )
    return V07C2Dataset.from_records(rows=rows, coverage=coverage)


def test_centering_has_zero_legal_mean_and_preserves_pair_differences() -> None:
    raw = torch.tensor(
        [[1.0, 9.0, 3.0, 5.0], [2.0, 4.0, 8.0, 16.0]],
        dtype=torch.float32,
    )
    masks = torch.tensor(
        [[True, False, True, True], [False, True, True, False]],
        dtype=torch.bool,
    )
    centered = center_legal_surface(raw, masks)
    assert torch.allclose(centered[0, masks[0]].mean(), torch.tensor(0.0))
    assert torch.allclose(centered[1, masks[1]].mean(), torch.tensor(0.0))
    assert centered[0, 2] - centered[0, 0] == raw[0, 2] - raw[0, 0]
    assert centered[1, 2] - centered[1, 1] == raw[1, 2] - raw[1, 1]
    assert torch.all(centered[~masks] == 0.0)


def test_one_fresh_q2_accepts_variable_masks_and_signed_targets() -> None:
    trainer = _trainer()
    assert not hasattr(trainer, "q1")
    assert not hasattr(trainer, "q3")
    assert not hasattr(trainer, "q_nets")
    before = q2_parameter_sha256(trainer.q2)
    receipt = trainer.update(_dataset())
    assert receipt["batch_size"] == 7
    assert receipt["update_count"] == 1
    assert receipt["max_abs_legal_mean"] < 1e-5
    assert receipt["state_schema"] == V07_C2_Q2_STATE_SCHEMA
    assert receipt["state_schema_sha256"] == V07_C2_Q2_STATE_SCHEMA_SHA256
    assert q2_parameter_sha256(trainer.q2) != before


def test_q2_values_skip_empty_masks_and_center_each_native_legal_set() -> None:
    trainer = _trainer(lineage="q13-b", role="final")
    states = np.zeros((3, V07_C2_Q2_STATE_DIM), dtype=np.float32)
    masks = np.zeros((3, 28), dtype=np.bool_)
    masks[1, [1, 2, 7]] = True
    masks[2, [0, 27]] = True
    values = trainer.q2_values(states, masks)
    assert np.array_equal(values[0], np.zeros(28, dtype=np.float32))
    assert np.allclose(values[1, masks[1]].mean(), 0.0, atol=1e-7)
    assert np.allclose(values[2, masks[2]].mean(), 0.0, atol=1e-7)
    assert np.all(values[~masks] == 0.0)


def test_batch_is_immutable_across_updates_and_zero_control_is_exact() -> None:
    trainer = _trainer()
    dataset = _dataset()
    trainer.update(dataset)
    changed_rows = list(dataset.rows)
    changed_rows[-1] = replace(changed_rows[-1], target=_target(5.0e7 + 1.0))
    changed = V07C2Dataset.from_records(
        rows=changed_rows, coverage=dataset.coverage
    )
    with pytest.raises(MCRLContractError, match="batch changed|corpus changed"):
        trainer.update(changed)

    with pytest.raises(MCRLContractError, match="role/lineage"):
        _trainer(lineage="q13-c").update(_dataset(lineage="q13-a"))


def test_checkpoint_requires_100_update_rung_and_same_fresh_role() -> None:
    trainer = _trainer(lineage="q13-c", role="provisional")
    update0 = trainer.checkpoint_state()
    assert update0["update_count"] == 0
    assert update0["legal_mask_centering"] is True
    assert update0["state_schema"] == V07_C2_Q2_STATE_SCHEMA
    assert update0["state_schema_sha256"] == V07_C2_Q2_STATE_SCHEMA_SHA256
    trainer.update(_dataset(lineage="q13-c"))
    with pytest.raises(MCRLContractError, match="every 100"):
        trainer.checkpoint_state()

    reloaded = _trainer(lineage="q13-c", role="provisional")
    assert reloaded.load_checkpoint_state(update0) == 0
    wrong_role = _trainer(lineage="q13-c", role="final")
    with pytest.raises(MCRLContractError, match="identity"):
        wrong_role.load_checkpoint_state(update0)


def test_constructor_rejects_unfrozen_seed_or_device() -> None:
    with pytest.raises(ValueError, match="train_seed"):
        EEAxisV07C2Trainer(lineage="q13-a", role="final", train_seed=1)
    with pytest.raises(ValueError, match="CPU"):
        EEAxisV07C2Trainer(
            lineage="q13-a",
            role="final",
            train_seed=V07_C2_SEED_BY_ROLE_LINEAGE["final"]["q13-a"],
            device="cuda",
        )


@pytest.mark.parametrize("bad_count", [False, 0.0, "0"])
def test_checkpoint_rejects_non_exact_integer_update_count(bad_count: object) -> None:
    trainer = _trainer()
    state = trainer.checkpoint_state()
    state["update_count"] = bad_count
    with pytest.raises(MCRLContractError, match="100-update rung"):
        _trainer().load_checkpoint_state(state)


def test_checkpoint_rejects_bad_digest_before_mutating_live_q2() -> None:
    trainer = _trainer(lineage="q13-b")
    before = q2_parameter_sha256(trainer.q2)
    state = trainer.checkpoint_state()
    state["parameter_sha256"] = "z" * 64
    with pytest.raises(MCRLContractError, match="digest"):
        trainer.load_checkpoint_state(state)
    assert q2_parameter_sha256(trainer.q2) == before


def test_checkpoint_rejects_stale_q2_state_schema() -> None:
    trainer = _trainer(lineage="q13-b")
    state = trainer.checkpoint_state()
    state["state_schema_sha256"] = "0" * 64
    with pytest.raises(MCRLContractError, match="state schema"):
        trainer.load_checkpoint_state(state)


def test_nonzero_checkpoint_requires_bound_batch_authority() -> None:
    trainer = _trainer(lineage="q13-c")
    state = trainer.checkpoint_state()
    state["update_count"] = 100
    with pytest.raises(MCRLContractError, match="source authority"):
        trainer.load_checkpoint_state(state)
