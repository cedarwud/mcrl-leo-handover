"""W-190 -- pure V0.23 LC-SRS C3 topology and coverage receipts."""

from __future__ import annotations

from dataclasses import replace
import hashlib

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.algorithms.ee_axis_lcsrs_three_route import DetachedQ12Snapshot
from mcrl.runtime.ee_axis_lcsrs_c3_topology import (
    LCSRS_C3_TOPOLOGY_SCHEMA,
    LCSRS_RETENTION_EMPTY_CLASS,
    LCSRS_RETENTION_NO_PAIRS,
    LCSRS_RETENTION_RETAINED,
    LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS,
    LCSRS_TOPOLOGY_OK,
    LCSRSC3AnchorCapture,
    LCSRSC3ScheduleTopologyReceipt,
    LCSRSC3TopologyError,
    enumerate_lcsrs_c3_anchor,
    enumerate_lcsrs_c3_schedule,
    enumerate_lcsrs_c3_world,
)


def _capture(
    *,
    world_id: int = 7,
    phase: int = 1,
    no_pair: bool = False,
    no_opening: bool = False,
    split_opening: bool = False,
    closed_pair_source: bool = False,
) -> LCSRSC3AnchorCapture:
    """Seven users: one exact-two source, one exact-three source, and controls."""

    users = 7
    mask = np.zeros((users, NUM_ACTIONS), dtype=np.bool_)
    mask[:, :3] = True
    opening = np.array(mask, copy=True)
    if no_opening:
        opening[:, 1:] = False
    if split_opening:
        opening[1, 1] = False
    if closed_pair_source:
        opening[1, 0] = False

    keys = np.full((users, NUM_ACTIONS, 2), -1, dtype=np.int64)
    if no_pair:
        sources = [(100 + user, 0) for user in range(users)]
    else:
        sources = [(10, 0), (10, 0), (30, 2), (40, 3), (50, 4), (50, 4), (50, 4)]
    for user, source in enumerate(sources):
        if no_pair:
            destinations = [source, (200 + user, 1), (300 + user, 2)]
        elif user in (0, 1):
            destinations = [source, (30, 2), (40, 3)]
        elif user == 2:
            destinations = [source, (10, 0), (40, 3)]
        elif user == 3:
            destinations = [source, (10, 0), (30, 2)]
        else:
            destinations = [source, (30, 2), (40, 3)]
        for action, physical_key in enumerate(destinations):
            keys[user, action] = physical_key

    q12 = np.full((users, NUM_ACTIONS), -100.0, dtype=np.float64)
    q12[:, :3] = np.asarray([10.0, 5.0, 5.0], dtype=np.float64)
    q1 = np.asarray(q12, dtype=np.float32)
    snapshot = DetachedQ12Snapshot(
        q1=q1,
        q2=np.zeros_like(q1),
        source_state_digest=hashlib.sha256(q1.tobytes() + b"state").hexdigest(),
        native_observation_event_digest=hashlib.sha256(
            q1.tobytes() + b"native-observation-event"
        ).hexdigest(),
        model_digest=hashlib.sha256(q1.tobytes() + b"model").hexdigest(),
    )
    return LCSRSC3AnchorCapture(
        world_id=world_id,
        phase=phase,
        anchor_id=f"world-{world_id}-phase-{phase}",
        q12_snapshot=snapshot,
        action_mask=mask,
        opening_feasibility=opening,
        physical_keys=keys,
    )


def test_anchor_enumerates_exact_two_pair_and_exact_three_no_close() -> None:
    capture = _capture()
    receipt = enumerate_lcsrs_c3_anchor(capture)

    assert receipt.reference_source_occupancies == (
        ((10, 0), 2),
        ((30, 2), 1),
        ((40, 3), 1),
        ((50, 4), 3),
    )
    assert receipt.pair_count == 1
    pair = receipt.pairs[0]
    assert pair.source_key == (10, 0)
    assert pair.member_users == (0, 1)
    # Actions 1 and 2 have equal detached Q12; native index 1 wins.
    assert pair.eligible_actions_by_member == ((1, 2), (1, 2))
    assert pair.designated_actions == (1, 1)
    assert pair.destination_keys == ((30, 2), (30, 2))

    assert receipt.no_close_count == 1
    control = receipt.no_close_controls[0]
    assert control.source_key == (50, 4)
    assert control.member_users == (4, 5)
    assert control.third_user == 6
    assert control.designated_actions == (1, 1)
    assert control.destination_keys == ((30, 2), (30, 2))
    assert control.eligible
    assert receipt.class_counts == {"S": 2, "R": 7, "C": 12, "MASKED": 175}
    assert receipt.retained_for_fitting
    assert receipt.retention_status == LCSRS_RETENTION_RETAINED
    serialized = receipt.to_receipt()
    assert serialized["schema"] == LCSRS_C3_TOPOLOGY_SCHEMA
    assert serialized["pairs"][0]["designated_actions"] == [1, 1]
    assert serialized["no_close_controls"][0]["third_user"] == 6
    assert not {
        "label",
        "outcome",
        "bits",
        "energy",
        "fading",
        "rate",
    }.intersection(serialized)


def test_destination_set_is_legal_opening_occupied_and_q12_frozen() -> None:
    capture = _capture(split_opening=True)
    receipt = enumerate_lcsrs_c3_anchor(capture)
    pair = receipt.pairs[0]
    assert pair.eligible_actions_by_member == ((1, 2), (2,))
    assert pair.designated_actions == (1, 2)

    # The capture owns copied, masked arrays; post-capture mutation cannot
    # change the references, topology, or digest.
    source_q12 = np.array(capture.detached_q12, copy=True)
    source_q12[:, 1] = 10_000.0
    source_q12[:, 4:] = np.nan
    assert capture.reference_actions.tolist() == [0] * 7
    assert receipt.content_digest == enumerate_lcsrs_c3_anchor(capture).content_digest
    assert not capture.detached_q12.flags.writeable
    with pytest.raises(ValueError):
        capture.detached_q12[0, 0] = 0.0

    # An opening bit on an illegal native row is a fail-closed input error.
    bad_opening = np.array(capture.opening_feasibility, copy=True)
    bad_opening[0, 27] = True
    with pytest.raises(LCSRSC3TopologyError, match="subset"):
        LCSRSC3AnchorCapture(
            world_id=capture.world_id,
            phase=capture.phase,
            anchor_id=capture.anchor_id,
            q12_snapshot=capture.q12_snapshot,
            action_mask=capture.action_mask,
            opening_feasibility=bad_opening,
            physical_keys=capture.physical_keys,
        )


def test_exact_two_pair_requires_both_reference_links_to_open() -> None:
    receipt = enumerate_lcsrs_c3_anchor(_capture(closed_pair_source=True))
    assert receipt.pair_count == 0
    assert receipt.retention_status == LCSRS_RETENTION_NO_PAIRS


def test_world_and_schedule_are_phase_ordered_and_emit_pair_gate_receipts() -> None:
    phases = tuple(_capture(phase=phase) for phase in range(1, 10))
    world = enumerate_lcsrs_c3_world(phases)
    assert tuple(anchor.phase for anchor in world.anchors) == tuple(range(1, 10))
    assert world.pair_count == 9

    complete_worlds = tuple(
        tuple(_capture(world_id=world_id, phase=phase) for phase in range(1, 10))
        for world_id in (7, 8, 9)
    )
    enough = enumerate_lcsrs_c3_schedule(complete_worlds)
    assert enough.status == LCSRS_TOPOLOGY_OK
    assert enough.meets_pair_gate
    assert enough.minimum_pairs == 24
    assert enough.pair_count == 27
    assert len(enough.retained_anchors) == 27
    assert [(anchor.world_id, anchor.phase) for anchor in enough.coverage_anchors] == [
        (world_id, phase)
        for world_id in (7, 8, 9)
        for phase in range(1, 10)
    ]

    below_contract_minimum = enumerate_lcsrs_c3_schedule(phases)
    assert below_contract_minimum.status == LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS
    assert below_contract_minimum.minimum_pairs == 24
    assert below_contract_minimum.pair_count == 9
    assert not below_contract_minimum.meets_pair_gate

    zero_world = tuple(_capture(world_id=10, phase=phase, no_pair=True) for phase in range(1, 10))
    mixed = enumerate_lcsrs_c3_schedule((*complete_worlds, zero_world))
    assert mixed.status == LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS
    assert mixed.pair_count == 27
    assert mixed.to_receipt()["zero_pair_world_ids"] == [10]


def test_schedule_receipt_rejects_non_frozen_minimum_pairs() -> None:
    world = enumerate_lcsrs_c3_world(
        tuple(_capture(world_id=7, phase=phase) for phase in range(1, 10))
    )
    with pytest.raises(LCSRSC3TopologyError, match="frozen at 24"):
        LCSRSC3ScheduleTopologyReceipt(worlds=(world,), minimum_pairs=9)


def test_retention_records_empty_classes_and_no_pair_coverage() -> None:
    no_pair = enumerate_lcsrs_c3_anchor(_capture(no_pair=True))
    assert no_pair.pair_count == 0
    assert no_pair.class_counts["S"] == 0
    assert not no_pair.retained_for_fitting
    assert no_pair.retention_status == LCSRS_RETENTION_NO_PAIRS

    # A supported pair can exist while the unique anchor surface has no C
    # rows.  The source user outside the pair supplies the occupied destination
    # but has only its reference action.
    users = 3
    mask = np.zeros((users, NUM_ACTIONS), dtype=np.bool_)
    mask[0, :2] = True
    mask[1, :2] = True
    mask[2, 0] = True
    opening = np.array(mask, copy=True)
    keys = np.full((users, NUM_ACTIONS, 2), -1, dtype=np.int64)
    keys[0, :2] = np.asarray([(10, 0), (30, 2)])
    keys[1, :2] = np.asarray([(10, 0), (30, 2)])
    keys[2, 0] = np.asarray((30, 2))
    q12 = np.full((users, NUM_ACTIONS), -1.0, dtype=np.float64)
    q12[:, 0] = 10.0
    q12[:2, 1] = 5.0
    q1 = np.asarray(q12, dtype=np.float32)
    sparse_snapshot = DetachedQ12Snapshot(
        q1=q1,
        q2=np.zeros_like(q1),
        source_state_digest=hashlib.sha256(q1.tobytes() + b"state").hexdigest(),
        native_observation_event_digest=hashlib.sha256(
            q1.tobytes() + b"native-observation-event"
        ).hexdigest(),
        model_digest=hashlib.sha256(q1.tobytes() + b"model").hexdigest(),
    )
    sparse = enumerate_lcsrs_c3_anchor(
        LCSRSC3AnchorCapture(
            world_id=7,
            phase=1,
            anchor_id="sparse",
            q12_snapshot=sparse_snapshot,
            action_mask=mask,
            opening_feasibility=opening,
            physical_keys=keys,
        )
    )
    assert sparse.pair_count == 1
    assert sparse.class_counts["C"] == 0
    assert not sparse.retained_for_fitting
    assert sparse.retention_status == LCSRS_RETENTION_EMPTY_CLASS


def test_duplicate_pair_receipt_and_incomplete_world_fail_closed() -> None:
    receipt = enumerate_lcsrs_c3_anchor(_capture())
    with pytest.raises(LCSRSC3TopologyError, match="duplicated"):
        replace(
            receipt,
            pairs=receipt.pairs + (receipt.pairs[0],),
            content_digest="",
        )
    with pytest.raises(LCSRSC3TopologyError, match="phase 1..9"):
        enumerate_lcsrs_c3_world((_capture(phase=1),))


def test_anchor_capture_rejects_an_unauthenticated_q12_array() -> None:
    capture = _capture()
    with pytest.raises(LCSRSC3TopologyError, match="DetachedQ12Snapshot"):
        LCSRSC3AnchorCapture(
            world_id=capture.world_id,
            phase=capture.phase,
            anchor_id=capture.anchor_id,
            q12_snapshot=capture.detached_q12,
            action_mask=capture.action_mask,
            opening_feasibility=capture.opening_feasibility,
            physical_keys=capture.physical_keys,
        )
