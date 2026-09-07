"""W-186 -- V0.23 unique LC-SRS anchor teacher surface."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_CONTROL,
    LCSRS_ROW_MASKED,
    LCSRS_ROW_REFERENCE,
    LCSRS_ROW_SUPPORTED,
    LCSRSC3DatasetError,
    LCSRSAnchorRecord,
    LCSRSAnchorSurface,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import (
    LCSRS_ACTION_CONTEXT_DIM,
    LCSRS_ACTION_DIM,
    LCSRS_TOKEN_DIM,
    assemble_c3_view,
)


def _view(*, designated: tuple[tuple[int, int], ...] = ((0, 1), (1, 1))):
    users = 4
    context = np.zeros(
        (users, LCSRS_ACTION_DIM, LCSRS_ACTION_CONTEXT_DIM), dtype=np.float32
    )
    tokens = np.zeros(
        (users, LCSRS_ACTION_DIM, users + 1, LCSRS_TOKEN_DIM), dtype=np.float32
    )
    action_mask = np.zeros((users, LCSRS_ACTION_DIM), dtype=np.bool_)
    action_mask[:, :3] = True
    token_mask = np.zeros((users, LCSRS_ACTION_DIM, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0
    for user, action in designated:
        tokens[user, action, users, 2:5] = 1.0
    return assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )


def _pair(
    *,
    pair_id: str = "p0",
    users: tuple[int, int] = (0, 1),
    actions: tuple[int, int] = (1, 1),
) -> LCSRSPairTargets:
    draws = np.column_stack(
        (
            np.arange(LCSRS_DRAW_COUNT, dtype=np.float64),
            -np.arange(LCSRS_DRAW_COUNT, dtype=np.float64) - 1.0,
        )
    )
    return LCSRSPairTargets(
        pair_id=pair_id,
        user_ids=np.asarray(users, dtype=np.int64),
        action_ids=np.asarray(actions, dtype=np.int64),
        normalized_targets_by_draw=draws,
    )


def test_assembly_writes_each_pair_mean_once_and_preserves_all_classes() -> None:
    pair = _pair()
    surface = assemble_lcsrs_anchor_surface(_view(), [pair])
    assert surface.normalized_targets[0, 1] == np.float32(15.5)
    assert surface.normalized_targets[1, 1] == np.float32(-16.5)
    assert surface.row_class[0, 1] == LCSRS_ROW_SUPPORTED
    assert surface.row_class[1, 1] == LCSRS_ROW_SUPPORTED
    assert np.all(surface.row_class[:, 0] == LCSRS_ROW_REFERENCE)
    assert surface.row_class[2, 1] == LCSRS_ROW_CONTROL
    assert surface.row_class[0, 3] == LCSRS_ROW_MASKED
    assert surface.cells_for_class(LCSRS_ROW_SUPPORTED).tolist() == [[0, 1], [1, 1]]
    assert not surface.normalized_targets.flags.writeable
    assert not surface.row_class.flags.writeable
    assert len(surface.content_digest) == 64
    surface.view.verify()


def test_assembly_rejects_overwrite_reference_and_unsupported_designation() -> None:
    pair = _pair()
    repeated_user = _pair(pair_id="p1", users=(0, 2))
    with pytest.raises(LCSRSC3DatasetError, match="user-disjoint"):
        assemble_lcsrs_anchor_surface(
            _view(designated=((0, 1), (1, 1), (2, 1))),
            [pair, repeated_user],
        )

    reference = _pair(actions=(0, 1))
    with pytest.raises(LCSRSC3DatasetError, match="overwrite"):
        assemble_lcsrs_anchor_surface(_view(designated=((0, 0), (1, 1))), [reference])

    with pytest.raises(LCSRSC3DatasetError, match="designated"):
        assemble_lcsrs_anchor_surface(_view(designated=()), [pair])


def test_pair_requires_exactly_32_finite_draws_and_unique_users() -> None:
    base = np.zeros((LCSRS_DRAW_COUNT, 2), dtype=np.float64)
    with pytest.raises(LCSRSC3DatasetError, match="exactly 32"):
        LCSRSPairTargets("p", np.asarray([0, 1]), np.asarray([1, 1]), base[:-1])
    with pytest.raises(LCSRSC3DatasetError, match="unique users"):
        LCSRSPairTargets("p", np.asarray([0, 0]), np.asarray([1, 1]), base)
    base[0, 0] = np.nan
    with pytest.raises(LCSRSC3DatasetError, match="finite"):
        LCSRSPairTargets("p", np.asarray([0, 1]), np.asarray([1, 1]), base)


def test_surface_authenticates_pair_mapping_and_digest() -> None:
    surface = assemble_lcsrs_anchor_surface(_view(), [_pair()])
    altered_targets = np.array(surface.normalized_targets, copy=True)
    altered_targets[0, 1] += np.float32(1.0)
    with pytest.raises(LCSRSC3DatasetError, match="32-draw mean"):
        LCSRSAnchorSurface(
            view=surface.view,
            normalized_targets=altered_targets,
            row_class=surface.row_class,
            pairs=surface.pairs,
        )
    with pytest.raises(LCSRSC3DatasetError, match="digest"):
        replace(surface, content_digest="0" * 64)


def test_anchor_record_binds_raw_q12_reference_margin_and_provenance() -> None:
    surface = assemble_lcsrs_anchor_surface(_view(), [_pair()])
    q12 = np.zeros((4, LCSRS_ACTION_DIM), dtype=np.float64)
    q12[:, 1:] = -1.0
    # Rebuild the view so its encoded margin agrees with this raw surface.
    arrays = {
        "action_context": np.array(surface.view.action_context, copy=True),
        "tokens": np.array(surface.view.tokens, copy=True),
        "token_mask": surface.view.token_mask,
        "action_mask": surface.view.action_mask,
        "reference_actions": surface.view.reference_actions,
    }
    arrays["action_context"][:, :3, 23] = np.asarray(
        np.tanh(q12[:, :3] - q12[:, [0]]), dtype=np.float32
    )
    view = assemble_c3_view(**arrays)
    surface = assemble_lcsrs_anchor_surface(view, [_pair()])
    record = LCSRSAnchorRecord(
        world_id=2026121705,
        phase=1,
        anchor_id="a0",
        surface=surface,
        q12_values=q12,
    )
    assert record.base_gap(0, 1) == pytest.approx(1.0)
    assert not record.q12_values.flags.writeable
    assert len(record.content_digest) == 64
    with pytest.raises(LCSRSC3DatasetError, match="reference"):
        replace(record, q12_values=-q12, content_digest="")
