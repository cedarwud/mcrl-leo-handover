"""W-113 -- V0.7 variable-mask focal-next dataset contract."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from mcrl.runtime.ee_axis_v07_c2_dataset import (
    V07C2Dataset,
    V07C2DatasetError,
    V07C2DecisionCoverage,
    V07C2Row,
    build_v07_pair_batch,
    canonical_json_bytes,
    canonical_sha256,
)
from mcrl.runtime.ee_axis_v07_c2_focal_next import focal_next_surplus_target
from mcrl.runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)
from mcrl.env.action_contract import NUM_ACTIONS


def _mask(*actions: int) -> np.ndarray:
    value = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    value[list(actions)] = True
    return value


def _target(*, candidate_rate: float, reference_rate: float, candidate_full: float = 30.0, candidate_without: float = 24.0, reference_full: float = 25.0, reference_without: float = 21.0):
    return focal_next_surplus_target(
        lambda_bits_per_j=10.0,
        interval_s=2.0,
        candidate_focal_rate_bps=candidate_rate,
        reference_focal_rate_bps=reference_rate,
        candidate_full_power_w=candidate_full,
        candidate_without_focal_power_w=candidate_without,
        reference_full_power_w=reference_full,
        reference_without_focal_power_w=reference_without,
    )


def _coverage(*, world: int, step: int, user: int, mask: np.ndarray, round: int | str = "bootstrap"):
    return V07C2DecisionCoverage(
        lineage="q13-a",
        refresh_round=round,
        world_id=world,
        step_index=step,
        focal_user=user,
        action_mask=mask,
    )


def _row(*, world: int, step: int, user: int, mask: np.ndarray, candidate: int, reference: int, target):
    return V07C2Row(
        lineage="q13-a",
        refresh_round="bootstrap",
        world_id=world,
        step_index=step,
        focal_user=user,
        state=np.arange(V07_C2_Q2_STATE_DIM, dtype=np.float32) + world + step + user,
        action_mask=mask,
        reference_action=reference,
        candidate_action=candidate,
        target=target,
    )


def _fixture() -> tuple[V07C2Dataset, tuple[V07C2Row, ...], tuple[V07C2DecisionCoverage, ...]]:
    one = _mask(0)
    two = _mask(1, 2)
    empty = _mask()
    zero = _target(candidate_rate=10.0, reference_rate=10.0, candidate_full=25.0, candidate_without=21.0, reference_full=25.0, reference_without=21.0)
    negative = _target(candidate_rate=5.0, reference_rate=10.0, candidate_full=30.0, candidate_without=24.0, reference_full=25.0, reference_without=21.0)
    rows = (
        _row(world=2, step=1, user=0, mask=two, candidate=2, reference=1, target=negative),
        _row(world=1, step=0, user=0, mask=one, candidate=0, reference=0, target=zero),
        _row(world=2, step=1, user=0, mask=two, candidate=1, reference=1, target=zero),
    )
    coverage = (
        _coverage(world=2, step=1, user=0, mask=two),
        _coverage(world=3, step=0, user=1, mask=empty),
        _coverage(world=1, step=0, user=0, mask=one),
    )
    return V07C2Dataset.from_records(rows=rows, coverage=coverage), rows, coverage


def test_variable_native_mask_coverage_and_deterministic_digest() -> None:
    dataset, rows, coverage = _fixture()

    assert [item.candidate_action for item in dataset.rows] == [0, 1, 2]
    assert [item.mask_count for item in dataset.coverage] == [1, 2, 0]
    assert dataset.rows[2].z2_focal_next_surplus_bits < 0.0
    assert dataset.state_schema == V07_C2_Q2_STATE_SCHEMA
    assert dataset.state_schema_sha256 == V07_C2_Q2_STATE_SCHEMA_SHA256
    assert dataset.corpus_sha256 == dataset.verify()

    reversed_dataset = V07C2Dataset.from_records(rows=reversed(rows), coverage=reversed(coverage))
    assert reversed_dataset.corpus_sha256 == dataset.corpus_sha256
    assert canonical_json_bytes(dataset.to_document()) == canonical_json_bytes(reversed_dataset.to_document())
    assert all(not row.state.flags.writeable for row in dataset.rows)
    assert all(not item.action_mask.flags.writeable for item in dataset.coverage)


def test_batch_contains_only_nonempty_rows_and_all_cardinalities() -> None:
    dataset, _, _ = _fixture()
    batch = build_v07_pair_batch(dataset)

    assert batch.states.shape == (3, V07_C2_Q2_STATE_DIM)
    assert batch.action_masks.shape == (3, NUM_ACTIONS)
    assert [int(value) for value in batch.candidate_actions] == [0, 1, 2]
    assert [int(np.count_nonzero(mask)) for mask in batch.action_masks] == [1, 2, 2]
    assert np.array_equal(batch.target_surplus_bits, np.array([0.0, 0.0, -50.0]))
    assert not batch.states.flags.writeable
    assert not batch.action_masks.flags.writeable


def test_empty_only_selected_view_fails_without_materializing_fake_rows() -> None:
    dataset, _, _ = _fixture()
    empty_dataset = V07C2Dataset.from_records(
        rows=(),
        coverage=tuple(item for item in dataset.coverage if item.mask_count == 0),
    )
    with pytest.raises(V07C2DatasetError, match="no non-empty"):
        build_v07_pair_batch(empty_dataset)

    # The named empty decision is still a first-class source coverage record.
    empty = [item for item in dataset.coverage if item.mask_count == 0]
    assert len(empty) == 1


def test_candidate_reference_legality_and_exact_zero_control() -> None:
    dataset, rows, coverage = _fixture()
    assert all(row.reference_action in row.action_mask.nonzero()[0] for row in dataset.rows)
    assert all(row.candidate_action in row.action_mask.nonzero()[0] for row in dataset.rows)

    nonzero_equal = _row(
        world=1,
        step=0,
        user=0,
        mask=_mask(0),
        candidate=0,
        reference=0,
        target=_target(candidate_rate=11.0, reference_rate=10.0),
    )
    with pytest.raises(V07C2DatasetError, match="exact zero"):
        V07C2Dataset.from_records(rows=(nonzero_equal,), coverage=(coverage[2],))

    illegal = replace(rows[1], candidate_action=3, action_mask=_mask(0))
    with pytest.raises(V07C2DatasetError, match="illegal"):
        V07C2Dataset.from_records(rows=(illegal,), coverage=(coverage[2],))


def test_signed_targets_are_retained_without_clip_or_filter() -> None:
    dataset, _, _ = _fixture()
    assert dataset.rows[2].z2_focal_next_surplus_bits == -50.0
    assert any(row.z2_focal_next_surplus_bits == 0.0 for row in dataset.rows)


def test_missing_duplicate_and_mask_drift_fail_closed() -> None:
    dataset, rows, coverage = _fixture()
    with pytest.raises(V07C2DatasetError, match="exactly once"):
        V07C2Dataset.from_records(rows=rows[:2], coverage=coverage)

    duplicate = rows + (replace(rows[2], candidate_action=1),)
    with pytest.raises(V07C2DatasetError, match="duplicate|repeats|exactly once"):
        V07C2Dataset.from_records(rows=duplicate, coverage=coverage)

    drift = replace(rows[1], action_mask=_mask(0, 1))
    with pytest.raises(V07C2DatasetError, match="mask|candidate|exactly"):
        V07C2Dataset.from_records(rows=rows[:1] + (drift,) + rows[2:], coverage=coverage)

    with pytest.raises(V07C2DatasetError, match="missing|orphaned"):
        V07C2Dataset.from_records(rows=rows, coverage=coverage[:2])

    with pytest.raises(V07C2DatasetError, match="duplicate"):
        V07C2Dataset.from_records(rows=rows, coverage=coverage + (coverage[0],))


def test_nonempty_mask_requires_every_legal_action_once() -> None:
    dataset, rows, coverage = _fixture()
    missing = tuple(row for row in rows if row.candidate_action != 2)
    with pytest.raises(V07C2DatasetError, match="exactly once"):
        V07C2Dataset.from_records(rows=missing, coverage=coverage)

    extra = _row(
        world=2,
        step=1,
        user=0,
        mask=_mask(1, 2),
        candidate=3,
        reference=1,
        target=_target(candidate_rate=18.0, reference_rate=10.0),
    )
    with pytest.raises(V07C2DatasetError, match="illegal"):
        V07C2Dataset.from_records(rows=rows + (extra,), coverage=coverage)


def test_document_round_trip_and_row_digest_are_canonical() -> None:
    dataset, _, _ = _fixture()
    document = dataset.to_document()
    restored = V07C2Dataset.from_document(document)

    assert restored.corpus_sha256 == dataset.corpus_sha256
    assert [row.row_sha256 for row in restored.rows] == [row.row_sha256 for row in dataset.rows]
    tampered = dict(document)
    tampered["corpus_sha256"] = "0" * 64
    with pytest.raises(V07C2DatasetError, match="digest"):
        V07C2Dataset.from_document(tampered)

    stale = dict(document)
    stale["state_schema"] = "stale"
    body = {key: value for key, value in stale.items() if key != "corpus_sha256"}
    stale["corpus_sha256"] = canonical_sha256(body)
    with pytest.raises(V07C2DatasetError, match="state schema"):
        V07C2Dataset.from_document(stale)


def test_target_receipt_inconsistency_is_rejected() -> None:
    good = _target(candidate_rate=5.0, reference_rate=10.0)
    bad = replace(good, z2_focal_next_surplus_bits=0.0)
    with pytest.raises(V07C2DatasetError, match="arithmetic"):
        _row(world=9, step=9, user=9, mask=_mask(0), candidate=0, reference=1, target=bad)

    bad_rate = replace(good, candidate_focal_rate_bps=6.0)
    with pytest.raises(V07C2DatasetError, match="arithmetic"):
        _row(world=9, step=9, user=9, mask=_mask(0), candidate=0, reference=1, target=bad_rate)
