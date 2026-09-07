"""W-194 -- fold isolation and held-out row metrics for V0.23."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRSAnchorRecord,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_gate_fit import (
    LCSRSC3GateFitError,
    V023_GATE_WORLDS,
    V023_PLACEBO_KEY_SHA256,
    V023_STUDENT_SEEDS,
    evaluate_lcsrs_heldout_rows,
    fit_lcsrs_loo_arm,
    prepare_lcsrs_loo_fold,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    LCSRSC3FitReceipt,
    lcsrs_c3_network_sha256,
    make_lcsrs_c3_student,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


def _record(*, world: int, value: float) -> LCSRSAnchorRecord:
    users, actions = 3, 28
    context = np.zeros((users, actions, 29), dtype=np.float32)
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    mask = np.zeros((users, actions), dtype=np.bool_)
    mask[:, :3] = True
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = mask
    tokens[:, :, users, 1][mask] = 1.0
    tokens[0:2, 1, users, 2:5] = 1.0
    context[0:2, 1, 3] = 1.0
    context[0:2, 1, 27] = np.float32(1.0 / users)
    q12 = np.zeros((users, actions), dtype=np.float64)
    q12[:, 1:] = -0.005
    context[:, :3, 23] = np.asarray(
        np.tanh(q12[:, :3] - q12[:, [0]]), dtype=np.float32
    )
    view = assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )
    draws = np.tile(
        np.asarray([[value, -value]], dtype=np.float64),
        (LCSRS_DRAW_COUNT, 1),
    )
    pair = LCSRSPairTargets(
        pair_id=f"w{world}-p",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    return LCSRSAnchorRecord(
        world_id=world,
        phase=1,
        anchor_id=f"w{world}-a1",
        surface=assemble_lcsrs_anchor_surface(view, [pair]),
        q12_values=q12,
    )


def _panel() -> dict[int, tuple[LCSRSAnchorRecord, ...]]:
    return {
        world: (_record(world=world, value=float(offset + 1)),)
        for offset, world in enumerate(V023_GATE_WORLDS)
    }


def test_fold_excludes_heldout_world_and_freezes_one_placebo_for_all_seeds() -> None:
    heldout = V023_GATE_WORLDS[3]
    fold = prepare_lcsrs_loo_fold(_panel(), held_out_world=heldout)
    assert {record.world_id for record in fold.training_records} == set(
        V023_GATE_WORLDS
    ) - {heldout}
    assert {record.world_id for record in fold.held_out_records} == {heldout}
    assert fold.matched_placebo.placebo_key_sha256 == V023_PLACEBO_KEY_SHA256
    assert fold.matched_placebo.meets_coverage_gate


def test_source_panel_requires_exact_worlds_and_unique_partition_identity() -> None:
    panel = _panel()
    panel.pop(V023_GATE_WORLDS[-1])
    with pytest.raises(LCSRSC3GateFitError, match="exact frozen eight worlds"):
        prepare_lcsrs_loo_fold(panel, held_out_world=V023_GATE_WORLDS[0])


def test_heldout_metrics_cover_only_supported_rows_and_are_digest_stable() -> None:
    record = _record(world=V023_GATE_WORLDS[0], value=1.0)
    network, _ = make_lcsrs_c3_student(student_seed=194)
    first = evaluate_lcsrs_heldout_rows(network, [record])
    second = evaluate_lcsrs_heldout_rows(network, [record])
    assert len(first.identities) == 2
    assert all(identity[0] == V023_GATE_WORLDS[0] for identity in first.identities)
    assert first.content_digest == second.content_digest
    assert first.targets.tolist() == [1.0, -1.0]
    assert first.sign.total_rows == 2
    assert not first.predictions.flags.writeable


def test_heldout_metrics_reject_empty_world() -> None:
    network, _ = make_lcsrs_c3_student(student_seed=194)
    with pytest.raises(LCSRSC3GateFitError, match="retained anchor"):
        evaluate_lcsrs_heldout_rows(network, [])


def test_student_seed_panel_is_frozen() -> None:
    assert V023_STUDENT_SEEDS == (2026135101, 2026135102, 2026135103)
    fold = prepare_lcsrs_loo_fold(
        _panel(), held_out_world=V023_GATE_WORLDS[0]
    )
    with pytest.raises(LCSRSC3GateFitError, match="frozen panel"):
        fit_lcsrs_loo_arm(fold, arm="INFORMED", student_seed=194)


def test_fit_wrapper_rebinds_surface_receipt_to_record_digests(monkeypatch) -> None:
    """The learner emits surface digests; the gate receipt binds full records."""

    fold = prepare_lcsrs_loo_fold(
        _panel(), held_out_world=V023_GATE_WORLDS[0]
    )
    assert any(
        record.surface.content_digest != record.content_digest
        for record in fold.training_records
    )
    raw_receipts = []

    def surface_bound_fit(
        source,
        *,
        arm,
        student_seed,
        normalized_targets_by_anchor,
        device,
    ):
        network, _optimizer = make_lcsrs_c3_student(
            student_seed=student_seed, device=device
        )
        target_source = tuple(surface.normalized_targets for surface in source)
        digest = hashlib.sha256()
        digest.update(b"multi-catfish-mcrl-v023-lcsrs-fitting-source-v1")
        for surface, target in zip(source, target_source, strict=True):
            digest.update(surface.content_digest.encode("ascii"))
            digest.update(np.ascontiguousarray(target, dtype=np.float32).tobytes())
        logical = lcsrs_c3_network_sha256(network)
        receipt = LCSRSC3FitReceipt(
            arm=arm,
            student_seed=student_seed,
            source_anchor_sha256s=tuple(
                surface.content_digest for surface in source
            ),
            target_source_sha256=digest.hexdigest(),
            initial_network_sha256=logical,
            final_network_sha256=logical,
            losses=np.zeros(2000, dtype=np.float64),
        )
        raw_receipts.append(receipt)
        return network, receipt

    monkeypatch.setattr(
        "mcrl.runtime.ee_axis_lcsrs_c3_gate_fit.fit_lcsrs_c3_source",
        surface_bound_fit,
    )
    fitted = fit_lcsrs_loo_arm(
        fold,
        arm="INFORMED",
        student_seed=V023_STUDENT_SEEDS[0],
    )
    assert fitted.fit_receipt.source_anchor_sha256s == tuple(
        record.content_digest for record in fold.training_records
    )
    assert fitted.fit_receipt.source_anchor_sha256s != tuple(
        record.surface.content_digest for record in fold.training_records
    )
    raw = raw_receipts[0]
    assert fitted.fit_receipt.target_source_sha256 == raw.target_source_sha256
    assert fitted.fit_receipt.initial_network_sha256 == raw.initial_network_sha256
    assert fitted.fit_receipt.final_network_sha256 == raw.final_network_sha256
    assert fitted.fit_receipt.config_sha256 == raw.config_sha256
    assert fitted.fit_receipt.updates == raw.updates
    assert fitted.fit_receipt.batch_size == raw.batch_size
    np.testing.assert_array_equal(fitted.fit_receipt.losses, raw.losses)
