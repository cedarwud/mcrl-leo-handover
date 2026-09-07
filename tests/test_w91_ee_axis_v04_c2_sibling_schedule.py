"""W-91 -- outcome-blind, support-complete V0.4 C2 sibling census."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from mcrl.runtime.ee_axis_v04_c2_sibling_schedule import (
    C2_V04_ANCHOR_SCHEDULE_SCHEMA,
    C2_V04_ROW_FAILURE,
    C2_V04_ROW_READY,
    C2_V04_ROW_SUPPORT_EXPIRED,
    C2_V04_SCHEDULE_SCHEMA,
    C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
    C2V04AnchorSchedule,
    C2V04SiblingRow,
    C2V04SiblingScheduleContractError,
    build_c2_v04_support_complete_schedule,
    canonical_anchor_schedule_sha256,
    read_c2_v04_support_complete_schedule,
    write_c2_v04_support_complete_schedule,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _anchor(
    *,
    source_seed: int = 2026092801,
    world: str = "world-a",
    anchor: str = "anchor-a",
    focal_user: int = 3,
    reference_action: int = 0,
    legal_actions: tuple[int, ...] = (0, 2, 5, 9),
    candidate_keys: tuple[tuple[int, int], ...] | None = None,
    **changes: object,
) -> C2V04AnchorSchedule:
    candidates = tuple(action for action in legal_actions if action != reference_action)
    keys = candidate_keys or tuple((70000 + action, action) for action in candidates)
    payload: dict[str, object] = {
        "source_seed": source_seed,
        "anchor_step": 2,
        "world_anchor_sha256": _sha(world),
        "anchor_sha256": _sha(anchor),
        "focal_user": focal_user,
        "reference_action": reference_action,
        "reference_physical_key": (70000, 0),
        "incumbent_physical_key": (71000, 0),
        "common_random_field_sha256": _sha("field"),
        "predecision_heuristic_scores": tuple(
            float(index + 1) for index, _ in enumerate(candidates)
        ),
        "legal_action_mask": tuple(action in legal_actions for action in range(28)),
        "candidate_actions": candidates,
        "candidate_physical_keys": keys,
        "checkpoint_sha256": _sha("checkpoint"),
        "source_manifest_sha256": _sha("manifest"),
        "policy_sha256": _sha("policy"),
        "evaluation_seed": 2026092901,
    }
    payload.update(changes)
    if "candidate_actions" in changes and candidate_keys is None:
        payload["candidate_physical_keys"] = tuple(
            (70000 + action, action) for action in payload["candidate_actions"]  # type: ignore[index]
        )
        payload["predecision_heuristic_scores"] = tuple(
            float(index + 1)
            for index, _ in enumerate(payload["candidate_actions"])  # type: ignore[arg-type]
        )
    row = C2V04AnchorSchedule(**payload)  # type: ignore[arg-type]
    assert row.source_rule == C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
    return row


def test_complete_census_binds_keys_and_preserves_nonready_rows() -> None:
    anchor = _anchor()
    rows = (
        C2V04SiblingRow.from_anchor(
            anchor,
            candidate_action=2,
            candidate_physical_key=(70002, 2),
            row_status=C2_V04_ROW_FAILURE,
            failure_code="prepare_failed",
        ),
        C2V04SiblingRow.from_anchor(
            anchor,
            candidate_action=5,
            candidate_physical_key=(70005, 5),
            row_status="support_expired",
            failure_code="support_lost_at_offset_1",
        ),
        C2V04SiblingRow.from_anchor(
            anchor,
            candidate_action=9,
            candidate_physical_key=(70009, 9),
        ),
    )
    schedule = build_c2_v04_support_complete_schedule((anchor,), rows=reversed(rows))

    assert schedule.schema == C2_V04_SCHEDULE_SCHEMA
    assert anchor.intervention_key == (
        2026092801,
        _sha("world-a"),
        _sha("anchor-a"),
        3,
    )
    assert rows[0].sibling_key == anchor.intervention_key + ((70002, 2),)
    assert schedule.anchors[0].anchor_schedule_sha256 == canonical_anchor_schedule_sha256(anchor)
    assert tuple(row.row_status for row in schedule.rows) == (
        C2_V04_ROW_FAILURE,
        "support-expired",
        C2_V04_ROW_READY,
    )
    assert len(schedule.rows) == 3


def test_schedule_digest_is_deterministic_and_round_trips(tmp_path) -> None:
    first_anchor = _anchor()
    second_anchor = _anchor(
        source_seed=2026092802,
        world="world-b",
        anchor="anchor-b",
        focal_user=4,
        legal_actions=(1, 3),
        reference_action=1,
    )
    first = build_c2_v04_support_complete_schedule((first_anchor, second_anchor))
    second = build_c2_v04_support_complete_schedule((second_anchor, first_anchor))
    assert first.schedule_sha256 == second.schedule_sha256
    assert first.file_sha256 == second.file_sha256

    path = tmp_path / "c2-sibling-schedule.json"
    file_sha = write_c2_v04_support_complete_schedule(path, first)
    assert file_sha == hashlib.sha256(path.read_bytes()).hexdigest()
    restored = read_c2_v04_support_complete_schedule(path, expected_file_sha256=file_sha)
    assert restored == first
    with pytest.raises(FileExistsError):
        write_c2_v04_support_complete_schedule(path, first)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"candidate_actions": (0, 2, 5, 9)},
            "Main reference action",
        ),
        (
            {"candidate_actions": (2, 5)},
            r"missing=\[9\]",
        ),
        (
            {"candidate_actions": (2, 5, 9, 10)},
            r"extra=\[10\]",
        ),
        (
            {"candidate_physical_keys": ((70002, 2), (70002, 2), (70009, 9))},
            "physical keys contain duplicates",
        ),
    ],
)
def test_anchor_fails_closed_on_main_duplicate_or_incomplete_census(changes, message) -> None:
    with pytest.raises(C2V04SiblingScheduleContractError, match=message):
        _anchor(**changes)


def test_anchor_rejects_unsorted_action_key_pairs() -> None:
    with pytest.raises(C2V04SiblingScheduleContractError, match="canonically sorted"):
        _anchor(
            candidate_actions=(9, 2, 5),
            candidate_physical_keys=((70009, 9), (70002, 2), (70005, 5)),
        )


def test_schedule_rejects_missing_extra_duplicate_and_mismatched_rows() -> None:
    anchor = _anchor()
    rows = tuple(
        C2V04SiblingRow.from_anchor(
            anchor,
            candidate_action=action,
            candidate_physical_key=key,
        )
        for key, action in anchor.candidate_pairs
    )

    with pytest.raises(C2V04SiblingScheduleContractError, match="complete legal census"):
        build_c2_v04_support_complete_schedule((anchor,), rows=rows[:-1])
    with pytest.raises(C2V04SiblingScheduleContractError, match="duplicate sibling_key"):
        build_c2_v04_support_complete_schedule((anchor,), rows=rows + (rows[0],))

    mismatched = replace(rows[0], anchor_schedule_sha256=_sha("wrong-anchor-digest"))
    with pytest.raises(C2V04SiblingScheduleContractError, match="shared anchor fields"):
        build_c2_v04_support_complete_schedule((anchor,), rows=(mismatched, *rows[1:]))

def test_mapping_tampering_and_outcome_leakage_fail_closed(tmp_path) -> None:
    schedule = build_c2_v04_support_complete_schedule((_anchor(),))
    payload = schedule.to_mapping()
    payload["rows"][0]["target"] = 1.0  # type: ignore[index]
    with pytest.raises(C2V04SiblingScheduleContractError, match="unsupported"):
        type(schedule).from_mapping(payload)

    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(schedule.to_mapping()), encoding="ascii")
    on_disk = json.loads(path.read_text(encoding="ascii"))
    on_disk["anchors"][0]["candidate_actions"][0] = 4
    path.write_text(json.dumps(on_disk), encoding="ascii")
    with pytest.raises(C2V04SiblingScheduleContractError):
        read_c2_v04_support_complete_schedule(path)

    canonical_path = tmp_path / "noncanonical.json"
    canonical_path.write_bytes(json.dumps(schedule.to_mapping()).encode("ascii"))
    with pytest.raises(C2V04SiblingScheduleContractError, match="canonical JSON"):
        read_c2_v04_support_complete_schedule(canonical_path)


def test_new_schema_does_not_mutate_old_v03_schema() -> None:
    old_v03_schema = "multi-catfish-mcrl-v03-e1-c2-preoutcome-schedule-v1"
    assert C2_V04_ANCHOR_SCHEDULE_SCHEMA != old_v03_schema
    assert C2_V04_SCHEDULE_SCHEMA != old_v03_schema
