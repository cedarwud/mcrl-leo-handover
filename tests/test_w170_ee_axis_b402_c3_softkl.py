"""W-170 -- B402 source-only masked teacher-distribution KL learner."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
)
from mcrl.runtime.ee_axis_b402_c3_softkl import (
    B402_ACTION_DIM,
    B402_ACTIVATION,
    B402_BETA,
    B402_GLOBAL_FEATURE_DIM,
    B402_HIDDEN_LAYERS,
    B402_LEARNING_RATE,
    B402_LOCAL_FEATURE_DIM,
    B402_SOFTKL_ALGORITHM,
    B402_SOFTKL_BATCH_SCHEMA,
    B402_SOFTKL_CHECKPOINT_VERSION,
    B402_SOFTKL_CLAIM_CEILING,
    B402_SOFTKL_SCHEMA,
    B402_STATE_DIM,
    B402SoftKLBatch,
    B402SoftKLContractError,
    EEAxisB402SoftKLLearner,
    build_b402_softkl_batch,
    masked_kl_loss,
    masked_kl_rows,
)


TEST_KAPPA = 2.0


def _config(*, kappa_bits: float = TEST_KAPPA) -> EEAxisV014HeadConfig:
    return EEAxisV014HeadConfig(
        action_dim=B402_ACTION_DIM,
        local_feature_dim=B402_LOCAL_FEATURE_DIM,
        global_feature_dim=B402_GLOBAL_FEATURE_DIM,
        hidden_layers=B402_HIDDEN_LAYERS,
        activation=B402_ACTIVATION,
        learning_rate=B402_LEARNING_RATE,
        kappa_bits=kappa_bits,
        beta=B402_BETA,
    )


def _batch() -> B402SoftKLBatch:
    rows = 4
    states = np.zeros((rows, B402_STATE_DIM), dtype=np.float32)
    states[1, 0] = 1.0
    states[3, 1] = 1.0

    masks = np.zeros((rows, B402_ACTION_DIM), dtype=np.bool_)
    masks[0, [0, 1, 2]] = True
    masks[1, [0, 3]] = True
    masks[2, 7] = True  # A one-action row must remain in the objective.
    masks[3, [1, 4, 6, 9]] = True

    background = np.zeros((rows, B402_ACTION_DIM), dtype=np.float64)
    background[0, [0, 1, 2]] = [0.5, 0.2, -0.1]
    background[1, [0, 3]] = [1.0, 0.25]
    background[2, 7] = 3.0
    background[3, [1, 4, 6, 9]] = [0.0, 0.1, -0.2, 0.4]

    z3 = np.zeros_like(background)
    z3[0, [1, 2]] = [2.0, -1.0]
    z3[1, 3] = 4.0
    z3[3, [4, 6, 9]] = [2.0, 1.0, -2.0]
    references = np.asarray([0, 0, 7, 1], dtype=np.int64)
    return build_b402_softkl_batch(
        states=states,
        action_masks=masks,
        background_values=background,
        z3_target_bits=z3,
        reference_actions=references,
        kappa_bits=TEST_KAPPA,
    )


class _FixedSurface(torch.nn.Module):
    """Test-only Q3 surface for exact objective checks."""

    def __init__(self, surface: np.ndarray) -> None:
        super().__init__()
        self.register_buffer("surface", torch.tensor(surface, dtype=torch.float32))

    def forward(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        del masks
        if states.shape[0] != self.surface.shape[0]:
            raise AssertionError("fixed Q3 surface row count mismatch")
        return self.surface


def test_batch_is_full_surface_immutable_and_take_preserves_rows() -> None:
    batch = _batch()
    batch.verify()
    assert batch.rows == 4
    assert batch.schema == B402_SOFTKL_BATCH_SCHEMA
    assert all(
        not np.asarray(getattr(batch, name)).flags.writeable
        for name in (
            "states",
            "action_masks",
            "background_values",
            "z3_target_bits",
            "reference_actions",
        )
    )

    selected = batch.take(np.asarray([2, 0, 3], dtype=np.int64))
    assert selected.rows == 3
    np.testing.assert_array_equal(selected.reference_actions, [7, 0, 1])
    assert not selected.states.flags.writeable

    with pytest.raises(B402SoftKLContractError, match="indices"):
        batch.take(np.asarray([], dtype=np.int64))


def test_masked_kl_matches_analytic_optimum_and_row_mean() -> None:
    mask = torch.zeros((2, B402_ACTION_DIM), dtype=torch.bool)
    mask[0, [0, 2]] = True
    mask[1, [1, 3, 5, 7]] = True
    teacher = torch.zeros((2, B402_ACTION_DIM), dtype=torch.float64)
    teacher[0, [0, 2]] = torch.tensor([2.0, -1.0], dtype=torch.float64)
    teacher[1, [1, 3, 5, 7]] = torch.tensor(
        [0.0, 1.0, -2.0, 0.5], dtype=torch.float64
    )
    # Equality of masked logits is the exact KL optimum.  Illegal student
    # entries intentionally differ by a huge amount and must not matter.
    student = teacher.clone()
    student[~mask] = -1.0e30
    rows = masked_kl_rows(teacher, student, mask)
    assert rows.shape == (2,)
    torch.testing.assert_close(rows, torch.zeros_like(rows), rtol=0, atol=1e-12)
    torch.testing.assert_close(masked_kl_loss(teacher, student, mask), rows.mean())

    # The reduction is mean over rows, not mean over the variable number of
    # legal actions in each row.
    shifted = student.clone()
    shifted[0, 0] += 1.0
    shifted[1, 1] += 1.0
    shifted_rows = masked_kl_rows(teacher, shifted, mask)
    torch.testing.assert_close(
        masked_kl_loss(teacher, shifted, mask), shifted_rows.mean()
    )


def test_masked_kl_is_stable_for_extreme_logits_and_has_no_illegal_gradient() -> None:
    mask = torch.zeros((2, B402_ACTION_DIM), dtype=torch.bool)
    mask[0, [0, 4]] = True
    mask[1, 8] = True
    teacher = torch.full((2, B402_ACTION_DIM), 1.0e30, dtype=torch.float64)
    student = torch.full((2, B402_ACTION_DIM), -1.0e30, dtype=torch.float64)
    teacher[0, 0], teacher[0, 4] = 1.0e30, -1.0e30
    student[0, 0], student[0, 4] = -1.0e30, 1.0e30
    teacher[1, 8] = -1.0e30
    student[1, 8] = 1.0e30
    student.requires_grad_()
    rows = masked_kl_rows(teacher, student, mask)
    assert bool(torch.isfinite(rows).all())
    rows.sum().backward()
    assert bool(torch.isfinite(student.grad).all())
    assert torch.count_nonzero(student.grad[~mask]) == 0


def test_one_action_row_has_zero_kl_but_gauge_still_applies() -> None:
    mask = torch.zeros((1, B402_ACTION_DIM), dtype=torch.bool)
    mask[0, 11] = True
    teacher = torch.full((1, B402_ACTION_DIM), 1.0e30, dtype=torch.float64)
    student = torch.full((1, B402_ACTION_DIM), -1.0e30, dtype=torch.float64)
    assert float(masked_kl_loss(teacher, student, mask)) == pytest.approx(0.0)

    batch = _batch().take([2])
    learner = EEAxisB402SoftKLLearner(_config(), train_seed=1701)
    metrics = learner.measure(batch)
    assert metrics["batch_size"] == 1
    assert metrics["row_mean_kl"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["gauge_mse"] == pytest.approx(0.0, abs=1e-12)


def test_exact_zr_surface_is_zero_loss_and_gauge_selects_zero_reference() -> None:
    batch = _batch()
    learner = EEAxisB402SoftKLLearner(_config(), train_seed=1702)
    exact = np.zeros_like(batch.z3_target_bits)
    exact[batch.action_masks] = (
        batch.z3_target_bits[batch.action_masks] / TEST_KAPPA
    )
    learner.q = _FixedSurface(exact)
    metrics = learner.measure(batch)
    assert metrics["row_mean_kl"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["gauge_mse"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["loss"] == pytest.approx(0.0, abs=1e-12)

    shifted = exact.copy()
    shifted[batch.action_masks] += 0.5
    learner.q = _FixedSurface(shifted)
    shifted_metrics = learner.measure(batch)
    assert shifted_metrics["row_mean_kl"] == pytest.approx(0.0, abs=1e-7)
    assert shifted_metrics["gauge_mse"] == pytest.approx(0.25, abs=1e-7)
    assert shifted_metrics["loss"] == pytest.approx(0.025, abs=1e-7)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("schema", "stale", "schema"),
        ("action_masks", np.zeros((4, 28), dtype=np.bool_), "nonempty"),
        ("reference_actions", np.asarray([0, 0, 99, 1], dtype=np.int64), "reference"),
    ),
)
def test_batch_rejects_stale_or_invalid_contract_fields(
    field: str, value: object, message: str
) -> None:
    batch = _batch()
    if field == "schema":
        invalid = replace(batch, schema=value)
    else:
        invalid = replace(batch, **{field: np.array(value, copy=True)})
        for name in (
            "states",
            "action_masks",
            "background_values",
            "z3_target_bits",
            "reference_actions",
        ):
            current = np.asarray(getattr(invalid, name))
            current.setflags(write=False)
    with pytest.raises(B402SoftKLContractError, match=message):
        invalid.verify()


def test_batch_rejects_nonzero_illegal_or_reference_targets() -> None:
    batch = _batch()
    illegal = np.array(batch.z3_target_bits, copy=True)
    illegal[0, 27] = 1.0
    illegal.setflags(write=False)
    with pytest.raises(B402SoftKLContractError, match="outside"):
        replace(batch, z3_target_bits=illegal).verify()

    reference = np.array(batch.z3_target_bits, copy=True)
    reference[0, 0] = 1.0
    reference.setflags(write=False)
    with pytest.raises(B402SoftKLContractError, match="reference"):
        replace(batch, z3_target_bits=reference).verify()


def test_zero_initialization_uses_frozen_actionset_and_preserves_background_argmax() -> None:
    batch = _batch()
    learner = EEAxisB402SoftKLLearner(_config(), train_seed=1703)
    assert isinstance(learner.q, V014ActionSetQNetwork)
    q3 = learner.q_values(batch.states, batch.action_masks)
    np.testing.assert_array_equal(q3, np.zeros_like(q3))
    base = np.argmax(
        np.where(batch.action_masks, batch.background_values, -np.inf), axis=1
    )
    student = np.argmax(
        np.where(batch.action_masks, batch.background_values + q3, -np.inf),
        axis=1,
    )
    np.testing.assert_array_equal(student, base)

    update = learner.update(batch)
    assert update["batch_size"] == batch.rows
    assert all(np.isfinite(float(update[name])) for name in ("loss", "row_mean_kl", "gauge_mse"))
    assert all(
        bool(torch.isfinite(parameter).all())
        for parameter in learner.q.parameters()
    )


def test_checkpoint_is_deep_copied_and_strictly_bound() -> None:
    config = _config()
    learner = EEAxisB402SoftKLLearner(config, train_seed=1704)
    before = learner.q_values(_batch().states, _batch().action_masks)
    payload = learner.checkpoint_state(update_count=3)
    assert payload["schema"] == B402_SOFTKL_SCHEMA
    assert payload["checkpoint_version"] == B402_SOFTKL_CHECKPOINT_VERSION
    assert payload["algorithm"] == B402_SOFTKL_ALGORITHM
    assert payload["claim_ceiling"] == B402_SOFTKL_CLAIM_CEILING
    assert payload["test_split_opened"] is False
    assert payload["episode_training"] is False

    saved = {
        key: value.detach().clone() for key, value in payload["q"].items()
    }
    with torch.no_grad():
        for parameter in learner.q.parameters():
            parameter.add_(1.0)
    for key, value in saved.items():
        torch.testing.assert_close(payload["q"][key], value, rtol=0, atol=0)

    restored = EEAxisB402SoftKLLearner(config, train_seed=1704)
    assert restored.load_checkpoint_state(payload) == 3
    np.testing.assert_array_equal(
        restored.q_values(_batch().states, _batch().action_masks), before
    )

    for field, value, message in (
        ("schema", "stale", "schema"),
        ("checkpoint_version", 999, "version"),
        ("algorithm", "stale", "algorithm"),
        ("train_seed", 1705, "train_seed"),
        ("claim_ceiling", "too-high", "claim ceiling"),
        ("test_split_opened", True, "forbidden"),
        ("episode_training", True, "forbidden"),
    ):
        with pytest.raises(B402SoftKLContractError, match=message):
            restored.load_checkpoint_state({**payload, field: value})

    with pytest.raises(B402SoftKLContractError, match="update_count"):
        learner.checkpoint_state(update_count=True)


def test_frozen_architecture_rejects_a_tunable_alternative() -> None:
    config = replace(_config(), hidden_layers=(50, 25, 10))
    with pytest.raises(B402SoftKLContractError, match="frozen 402-D"):
        EEAxisB402SoftKLLearner(config, train_seed=1705)
