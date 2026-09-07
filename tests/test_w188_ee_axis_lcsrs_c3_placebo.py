"""W-188 -- fold-safe V0.23 LC-SRS matched placebo."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRSAnchorRecord,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3ClassBalancedSampler
from mcrl.runtime.ee_axis_lcsrs_c3_placebo import (
    LCSRSC3PlaceboError,
    build_lcsrs_matched_placebo,
    placebo_stratum,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


def _record(*, world: int, anchor: str, value: float) -> LCSRSAnchorRecord:
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
    context[0:2, 1, 3] = 1.0
    context[0:2, 1, 27] = np.float32(1.0 / users)
    q12 = np.zeros((users, actions), dtype=np.float64)
    q12[:, 1:] = -0.005
    context[:, :3, 23] = np.asarray(np.tanh(q12[:, :3] - q12[:, [0]]), dtype=np.float32)
    view = assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )
    draws = np.tile(np.asarray([[value, -value]], dtype=np.float64), (LCSRS_DRAW_COUNT, 1))
    pair = LCSRSPairTargets(
        pair_id=f"{anchor}-p",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    surface = assemble_lcsrs_anchor_surface(view, [pair])
    return LCSRSAnchorRecord(
        world_id=world,
        phase=1,
        anchor_id=anchor,
        surface=surface,
        q12_values=q12,
    )


def test_placebo_is_deterministic_nonzero_cyclic_and_preserves_row_universe() -> None:
    records = [_record(world=1, anchor="a", value=1.0), _record(world=1, anchor="b", value=2.0)]
    first = build_lcsrs_matched_placebo(records, placebo_key="frozen-key")
    second = build_lcsrs_matched_placebo(records, placebo_key="frozen-key")
    assert first.content_digest == second.content_digest
    assert first.coverage == pytest.approx(1.0)
    assert first.meets_coverage_gate
    assert len(first.mappings) == 4
    informed = sorted(
        float(record.surface.normalized_targets[user, 1])
        for record in records
        for user in (0, 1)
    )
    placebo = sorted(
        float(target[user, 1])
        for target in first.normalized_targets_by_anchor
        for user in (0, 1)
    )
    assert placebo == informed
    assert any(
        not np.array_equal(target, record.surface.normalized_targets)
        for target, record in zip(first.normalized_targets_by_anchor, records, strict=True)
    )
    for target, record in zip(first.normalized_targets_by_anchor, records, strict=True):
        np.testing.assert_array_equal(
            target[record.surface.row_class != 3],
            record.surface.normalized_targets[record.surface.row_class != 3],
        )
        assert not target.flags.writeable


def test_placebo_never_crosses_world_even_when_strata_otherwise_match() -> None:
    records = [_record(world=1, anchor="a", value=1.0), _record(world=2, anchor="b", value=2.0)]
    placebo = build_lcsrs_matched_placebo(records, placebo_key="frozen-key")
    assert placebo.eligible_supported_rows == 4
    assert placebo.coverage == 1.0
    for mapping in placebo.mappings:
        assert (
            records[mapping.source_anchor].world_id
            == records[mapping.destination_anchor].world_id
        )


def test_placebo_targets_feed_same_sampler_cells_with_different_labels_only() -> None:
    records = [_record(world=1, anchor="a", value=1.0), _record(world=1, anchor="b", value=2.0)]
    placebo = build_lcsrs_matched_placebo(records, placebo_key="frozen-key")
    surfaces = [record.surface for record in records]
    informed_batch = LCSRSC3ClassBalancedSampler(surfaces, student_seed=31).draw(256)
    placebo_batch = LCSRSC3ClassBalancedSampler(
        surfaces,
        student_seed=31,
        normalized_targets_by_anchor=placebo.normalized_targets_by_anchor,
    ).draw(256)
    for field in ("anchor_indices", "row_classes", "user_indices", "action_indices"):
        np.testing.assert_array_equal(
            getattr(informed_batch, field), getattr(placebo_batch, field)
        )
    assert np.any(informed_batch.normalized_targets != placebo_batch.normalized_targets)


def test_stratum_rejects_non_supported_cell() -> None:
    record = _record(world=1, anchor="a", value=1.0)
    with pytest.raises(LCSRSC3PlaceboError, match="SUPPORTED"):
        placebo_stratum(record, 2, 2)
