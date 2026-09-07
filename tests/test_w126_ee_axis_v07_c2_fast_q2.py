"""W-126 -- development-only tiny-batch Q2 rapid-iteration learner."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v07_c2_fast_q2 import (
    FAST_Q2_KAPPA_BITS,
    FAST_Q2_MAX_UPDATES,
    FreshQ2,
    q2_parameter_sha256,
)
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)


def _batch() -> EEAxisPairBatch:
    states = np.zeros((3, V07_C2_Q2_STATE_DIM), dtype=np.float32)
    states[0, 0] = 0.10
    states[1, 7] = -0.20
    states[2, 140] = 0.30
    masks = np.zeros((3, 28), dtype=np.bool_)
    masks[0, [0, 4, 9]] = True
    masks[1, [2, 3]] = True
    masks[2, [1, 7, 12, 27]] = True
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray([0, 2, 1], dtype=np.int64),
        candidate_actions=np.asarray([4, 3, 7], dtype=np.int64),
        # Keep targets in the native bits-equivalent units; the learner
        # normalizes by the frozen V0.7 kappa before optimization.
        target_surplus_bits=FAST_Q2_KAPPA_BITS
        * np.asarray([0.04, -0.03, 0.02], dtype=np.float64),
        action_masks=masks,
    )


def test_q2_values_centers_each_partial_legal_panel_and_zeros_illegal_slots() -> None:
    trainer = FreshQ2(train_seed=2026090201)
    batch = _batch()
    values = trainer.q2_values(batch.states, batch.action_masks)

    assert values.shape == (3, 28)
    assert np.all(values[~batch.action_masks] == 0.0)
    for row, mask in enumerate(batch.action_masks):
        assert np.isclose(values[row, mask].mean(), 0.0, atol=1e-7)
    assert trainer.state_schema == V07_C2_Q2_STATE_SCHEMA
    assert trainer.state_schema_sha256 == V07_C2_Q2_STATE_SCHEMA_SHA256
    assert not hasattr(trainer, "q1")
    assert not hasattr(trainer, "q3")
    assert not hasattr(trainer, "q_nets")


def test_empty_masks_are_non_deployable_but_return_zero_q2_values() -> None:
    trainer = FreshQ2(train_seed=2026090202)
    states = np.zeros((2, V07_C2_Q2_STATE_DIM), dtype=np.float32)
    masks = np.zeros((2, 28), dtype=np.bool_)
    masks[1, [5, 11]] = True
    values = trainer.q2_values(states, masks)
    assert np.array_equal(values[0], np.zeros(28, dtype=np.float32))
    assert np.allclose(values[1, masks[1]].mean(), 0.0, atol=1e-7)


def test_fit_is_deterministic_and_reports_development_only_diagnostics() -> None:
    batch = _batch()
    first = FreshQ2(train_seed=2026090203)
    second = FreshQ2(train_seed=2026090203)
    first_receipt = first.fit(batch, updates=12)
    second_receipt = second.fit(batch, updates=12)

    assert first_receipt == second_receipt
    assert q2_parameter_sha256(first.q2) == q2_parameter_sha256(second.q2)
    assert first_receipt["updates"] == 12
    assert first_receipt["update_count"] == 12
    assert first_receipt["batch_size"] == 3
    assert first_receipt["claim_ceiling"] == "development-only-not-efficacy-evidence"
    assert first_receipt["state_schema"] == V07_C2_Q2_STATE_SCHEMA
    assert first_receipt["state_schema_sha256"] == V07_C2_Q2_STATE_SCHEMA_SHA256
    assert first_receipt["learning_rate"] == 0.001
    assert first_receipt["beta"] == 0.001
    assert first_receipt["final_loss"] <= first_receipt["initial_loss"]


def test_small_batch_target_fit_reduces_pairwise_error() -> None:
    trainer = FreshQ2(train_seed=2026090204)
    receipt = trainer.fit(_batch(), updates=100)
    assert receipt["updates"] == FAST_Q2_MAX_UPDATES
    assert receipt["update_count"] == FAST_Q2_MAX_UPDATES
    assert receipt["final_pair_mse"] < receipt["initial_pair_mse"]
    assert np.isfinite(receipt["final_loss"])


def test_fit_rejects_empty_batch_and_invalid_update_budget() -> None:
    trainer = FreshQ2(train_seed=2026090205)
    empty = EEAxisPairBatch(
        states=np.empty((0, V07_C2_Q2_STATE_DIM), dtype=np.float32),
        reference_actions=np.empty((0,), dtype=np.int64),
        candidate_actions=np.empty((0,), dtype=np.int64),
        target_surplus_bits=np.empty((0,), dtype=np.float64),
        action_masks=np.empty((0, 28), dtype=np.bool_),
    )
    with pytest.raises(ValueError, match="positive row count"):
        trainer.fit(empty, updates=1)
    for updates in (0, FAST_Q2_MAX_UPDATES + 1, True, 1.0):
        with pytest.raises(ValueError, match="updates"):
            trainer.fit(_batch(), updates=updates)


def test_fit_rejects_noncanonical_masks_state_width_and_changed_batch() -> None:
    trainer = FreshQ2(train_seed=2026090206)
    batch = _batch()

    bad_masks = EEAxisPairBatch(
        states=batch.states,
        reference_actions=batch.reference_actions,
        candidate_actions=batch.candidate_actions,
        target_surplus_bits=batch.target_surplus_bits,
        action_masks=batch.action_masks.astype(np.int8),
    )
    with pytest.raises(ValueError, match="boolean"):
        trainer.fit(bad_masks, updates=1)

    bad_states = EEAxisPairBatch(
        states=batch.states[:, :-1],
        reference_actions=batch.reference_actions,
        candidate_actions=batch.candidate_actions,
        target_surplus_bits=batch.target_surplus_bits,
        action_masks=batch.action_masks,
    )
    with pytest.raises(ValueError, match="state"):
        trainer.fit(bad_states, updates=1)

    trainer.fit(batch, updates=1)
    changed = EEAxisPairBatch(
        states=batch.states,
        reference_actions=batch.reference_actions,
        candidate_actions=batch.candidate_actions,
        target_surplus_bits=batch.target_surplus_bits + 1.0,
        action_masks=batch.action_masks,
    )
    with pytest.raises(MCRLContractError, match="batch changed"):
        trainer.fit(changed, updates=1)


def test_constructor_is_cpu_only_and_fit_rejects_empty_legal_rows() -> None:
    with pytest.raises(ValueError, match="CPU"):
        FreshQ2(train_seed=1, device="cuda")

    batch = _batch()
    masks = batch.action_masks.copy()
    masks[0] = False
    empty_legal = EEAxisPairBatch(
        states=batch.states,
        reference_actions=batch.reference_actions,
        candidate_actions=batch.candidate_actions,
        target_surplus_bits=batch.target_surplus_bits,
        action_masks=masks,
    )
    with pytest.raises(ValueError, match="at least one legal"):
        FreshQ2(train_seed=2).fit(empty_legal, updates=1)
