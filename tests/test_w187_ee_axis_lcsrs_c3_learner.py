"""W-187 -- fixed V0.23 LC-SRS class-balanced source learner."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_REFERENCE,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    LCSRS_C3_BATCH_SIZE,
    LCSRS_C3_LEARNER_CONFIG,
    LCSRS_C3_UPDATE_COUNT,
    LCSRSC3ClassBalancedSampler,
    LCSRSC3FitReceipt,
    LCSRSC3LearnerError,
    LCSRSC3LearnerConfig,
    LCSRSC3SampledBatch,
    lcsrs_c3_training_step,
    lcsrs_c3_network_sha256,
    make_lcsrs_c3_student,
    score_sampled_cells,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


def _surface():
    users, actions = 3, 28
    context = np.zeros((users, actions, 29), dtype=np.float32)
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    action_mask = np.zeros((users, actions), dtype=np.bool_)
    action_mask[:, :3] = True
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0
    tokens[0, 1, users, 2:5] = 1.0
    tokens[1, 1, users, 2:5] = 1.0
    # Give candidates distinct observable feature content.
    context[0, 1, 0] = 0.2
    context[1, 1, 0] = -0.2
    view = assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )
    draws = np.tile(np.asarray([[1.0, -1.0]], dtype=np.float64), (LCSRS_DRAW_COUNT, 1))
    pair = LCSRSPairTargets(
        pair_id="p0",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    return assemble_lcsrs_anchor_surface(view, [pair])


def test_sampler_is_seed_exact_and_draws_only_declared_anchor_classes() -> None:
    surface = _surface()
    left = LCSRSC3ClassBalancedSampler([surface], student_seed=7).draw(512)
    right = LCSRSC3ClassBalancedSampler([surface], student_seed=7).draw(512)
    for field in (
        "anchor_indices",
        "row_classes",
        "user_indices",
        "action_indices",
        "normalized_targets",
    ):
        np.testing.assert_array_equal(getattr(left, field), getattr(right, field))
        assert not getattr(left, field).flags.writeable
    assert set(left.row_classes.tolist()) == {1, 2, 3}
    np.testing.assert_array_equal(
        surface.row_class[left.user_indices, left.action_indices], left.row_classes
    )


def test_sparse_batch_scorer_matches_full_surface_and_reference_is_exact_zero() -> None:
    surface = _surface()
    network, _optimizer = make_lcsrs_c3_student(student_seed=11)
    batch = LCSRSC3SampledBatch(
        anchor_indices=np.asarray([0, 0, 0, 0]),
        row_classes=np.asarray([3, 3, 1, 2], dtype=np.uint8),
        user_indices=np.asarray([0, 1, 2, 2]),
        action_indices=np.asarray([1, 1, 0, 2]),
        normalized_targets=np.asarray([1.0, -1.0, 0.0, 0.0]),
    )
    selected = score_sampled_cells(network, [surface], batch)
    full = network.forward_view(surface.view)
    user_indices = torch.tensor(np.asarray(batch.user_indices), dtype=torch.int64)
    action_indices = torch.tensor(np.asarray(batch.action_indices), dtype=torch.int64)
    torch.testing.assert_close(
        selected,
        full[user_indices, action_indices],
        rtol=0.0,
        atol=1.0e-7,
    )
    assert selected[2].item() == 0.0


def test_one_training_step_is_finite_updates_parameters_and_retains_negative_rows() -> None:
    surface = _surface()
    network, optimizer = make_lcsrs_c3_student(student_seed=19)
    sampler = LCSRSC3ClassBalancedSampler([surface], student_seed=19)
    before = [parameter.detach().clone() for parameter in network.parameters()]
    batch = sampler.draw(LCSRS_C3_BATCH_SIZE)
    assert np.any(batch.normalized_targets < 0.0)
    loss = lcsrs_c3_training_step(network, optimizer, [surface], batch)
    assert np.isfinite(loss) and loss >= 0.0
    assert any(
        not torch.equal(old, new.detach())
        for old, new in zip(before, network.parameters(), strict=True)
    )


def test_frozen_constants_and_reference_only_batch_has_zero_loss_and_gradient() -> None:
    assert LCSRS_C3_LEARNER_CONFIG.batch_size == 256
    assert LCSRS_C3_LEARNER_CONFIG.updates == LCSRS_C3_UPDATE_COUNT == 2000
    surface = _surface()
    network, optimizer = make_lcsrs_c3_student(student_seed=23)
    rows = np.arange(3, dtype=np.int64)
    batch = LCSRSC3SampledBatch(
        anchor_indices=np.zeros(3, dtype=np.int64),
        row_classes=np.full(3, LCSRS_ROW_REFERENCE, dtype=np.uint8),
        user_indices=rows,
        action_indices=np.zeros(3, dtype=np.int64),
        normalized_targets=np.zeros(3, dtype=np.float32),
    )
    before = [parameter.detach().clone() for parameter in network.parameters()]
    assert lcsrs_c3_training_step(network, optimizer, [surface], batch) == pytest.approx(0.0)
    assert all(
        torch.equal(old, new.detach())
        for old, new in zip(before, network.parameters(), strict=True)
    )


def test_initial_student_hash_is_seed_exact_and_configuration_rejects_drift() -> None:
    left, _ = make_lcsrs_c3_student(student_seed=101)
    right, _ = make_lcsrs_c3_student(student_seed=101)
    other, _ = make_lcsrs_c3_student(student_seed=102)
    assert lcsrs_c3_network_sha256(left) == lcsrs_c3_network_sha256(right)
    assert lcsrs_c3_network_sha256(left) != lcsrs_c3_network_sha256(other)
    with pytest.raises(ValueError, match="frozen"):
        LCSRSC3LearnerConfig(updates=1999)


def test_fit_receipt_accepts_actual_sha_values_and_freezes_losses() -> None:
    """Guard the post-fit return seam without running the 2000-update budget."""

    digest = "a" * 64
    receipt = LCSRSC3FitReceipt(
        arm="INFORMED",
        student_seed=17,
        source_anchor_sha256s=(digest,),
        target_source_sha256="b" * 64,
        initial_network_sha256="c" * 64,
        final_network_sha256="d" * 64,
        losses=np.zeros(LCSRS_C3_UPDATE_COUNT, dtype=np.float64),
    )
    assert receipt.target_source_sha256 == "b" * 64
    assert not receipt.losses.flags.writeable

    with pytest.raises(LCSRSC3LearnerError, match="malformed SHA-256"):
        LCSRSC3FitReceipt(
            arm="INFORMED",
            student_seed=17,
            source_anchor_sha256s=(digest,),
            target_source_sha256="not-a-digest",
            initial_network_sha256="c" * 64,
            final_network_sha256="d" * 64,
            losses=np.zeros(LCSRS_C3_UPDATE_COUNT, dtype=np.float64),
        )
