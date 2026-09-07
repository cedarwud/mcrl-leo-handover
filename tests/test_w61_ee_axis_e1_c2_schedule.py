"""W-61 -- immutable, pre-outcome E1 C2 schedule sealing."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path

import pytest

from mcrl.runtime.ee_axis_e1_c2_schedule import (
    E1C2PreOutcomeSchedule,
    E1C2ScheduleCluster,
    E1C2ScheduleContractError,
    E1_C2_CLUSTER_SCHEMA,
    E1_C2_SCHEDULE_SCHEMA,
    e1_c2_world_anchor_sha256,
    load_e1_c2_schedule,
    seal_e1_c2_schedule,
    validate_e1_c2_schedule,
)


_POLICY = "a" * 64
_SOURCE = "b" * 64
_CHECKPOINT = "c" * 64
_CRF = "d" * 64


def _cluster(
    *,
    source_seed: int = 2026091001,
    anchor_sha256: str = "1" * 64,
    focal_user: int = 7,
    anchor_step: int = 3,
    source_manifest_sha256: str = _SOURCE,
    policy_sha256: str = _POLICY,
    common_random_field_sha256: str = _CRF,
) -> E1C2ScheduleCluster:
    return E1C2ScheduleCluster(
        source_seed=source_seed,
        anchor_sha256=anchor_sha256,
        world_anchor_sha256=e1_c2_world_anchor_sha256(
            source_seed=source_seed, anchor_step=anchor_step
        ),
        anchor_schedule_sha256="2" * 64,
        anchor_step=anchor_step,
        focal_user=focal_user,
        reference_action=11,
        candidate_action=7,
        reference_physical_key=(56355, 11),
        candidate_physical_key=(56355, 52),
        candidate_source_rule="incumbent-hold",
        policy_sha256=policy_sha256,
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=_CHECKPOINT,
        common_random_field_sha256=common_random_field_sha256,
    )


def _schedule(
    *,
    source_seed: int = 2026091001,
    clusters: tuple[E1C2ScheduleCluster, ...] | None = None,
) -> E1C2PreOutcomeSchedule:
    return E1C2PreOutcomeSchedule(
        source_seed=source_seed,
        clusters=clusters or (_cluster(source_seed=source_seed),),
        policy_sha256=_POLICY,
        source_manifest_sha256=_SOURCE,
        checkpoint_sha256=_CHECKPOINT,
    )


def test_schedule_is_immutable_and_identity_digest_is_outcome_free() -> None:
    schedule = _schedule()
    cluster = schedule.clusters[0]

    assert schedule.to_mapping()["schema"] == E1_C2_SCHEDULE_SCHEMA
    assert cluster.to_mapping()["schema"] == E1_C2_CLUSTER_SCHEMA
    assert cluster.cluster_key == (2026091001, "1" * 64, 7)
    assert len(cluster.cluster_sha256) == 64
    assert len(schedule.schedule_sha256) == 64
    assert "target" not in cluster.to_mapping()
    assert "outcome" not in schedule.to_mapping()

    with pytest.raises(FrozenInstanceError):
        schedule.source_seed = 9  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        cluster.focal_user = 9  # type: ignore[misc]


def test_canonical_mapping_round_trips_and_binds_schedule_and_cluster_digests() -> None:
    schedule = _schedule()
    decoded = E1C2PreOutcomeSchedule.from_mapping(schedule.to_mapping())

    assert decoded == schedule
    assert decoded.schedule_sha256 == schedule.schedule_sha256
    assert decoded.file_sha256 == schedule.file_sha256
    assert decoded.clusters[0].cluster_sha256 == schedule.clusters[0].cluster_sha256


def test_duplicate_anchor_focal_cluster_is_rejected() -> None:
    cluster = _cluster()

    with pytest.raises(E1C2ScheduleContractError, match="duplicate"):
        _schedule(clusters=(cluster, cluster))


def test_focal_specific_anchor_ids_share_one_world_anchor_at_same_step() -> None:
    first = _cluster(anchor_sha256="1" * 64, focal_user=7, anchor_step=3)
    second = _cluster(anchor_sha256="3" * 64, focal_user=8, anchor_step=3)
    schedule = _schedule(clusters=(first, second))
    assert schedule.clusters[0].anchor_sha256 != schedule.clusters[1].anchor_sha256
    assert (
        schedule.clusters[0].world_anchor_sha256
        == schedule.clusters[1].world_anchor_sha256
    )


def test_cluster_seed_must_match_schedule_seed() -> None:
    with pytest.raises(E1C2ScheduleContractError, match="source_seed"):
        _schedule(
            clusters=(
                _cluster(source_seed=2026091002),
            )
        )


def test_mixed_lineage_digests_are_rejected() -> None:
    with pytest.raises(E1C2ScheduleContractError, match="mixed source_manifest_sha256"):
        _schedule(
            clusters=(
                _cluster(),
                _cluster(
                    anchor_sha256="3" * 64,
                    focal_user=8,
                    source_manifest_sha256="e" * 64,
                ),
            )
        )


def test_cluster_local_crf_digests_are_allowed_and_can_be_bound() -> None:
    first = _cluster()
    second = _cluster(
        anchor_sha256="3" * 64,
        focal_user=8,
        common_random_field_sha256="e" * 64,
    )
    schedule = _schedule(clusters=(first, second))
    bindings = {
        cluster.cluster_sha256: cluster.common_random_field_sha256
        for cluster in schedule.clusters
    }

    assert first.common_random_field_sha256 != second.common_random_field_sha256
    assert validate_e1_c2_schedule(
        schedule, cluster_crf_sha256=bindings
    ) == schedule.schedule_sha256


def test_cluster_crf_binding_rejects_missing_extra_or_wrong_identity() -> None:
    schedule = _schedule(
        clusters=(
            _cluster(),
            _cluster(
                anchor_sha256="3" * 64,
                focal_user=8,
                common_random_field_sha256="e" * 64,
            ),
        )
    )
    bindings = {
        cluster.cluster_sha256: cluster.common_random_field_sha256
        for cluster in schedule.clusters
    }

    missing = dict(bindings)
    missing.pop(schedule.clusters[1].cluster_sha256)
    with pytest.raises(E1C2ScheduleContractError, match="keys must match"):
        validate_e1_c2_schedule(schedule, cluster_crf_sha256=missing)

    extra = dict(bindings)
    extra["f" * 64] = _CRF
    with pytest.raises(E1C2ScheduleContractError, match="keys must match"):
        validate_e1_c2_schedule(schedule, cluster_crf_sha256=extra)

    wrong = dict(bindings)
    wrong[schedule.clusters[0].cluster_sha256] = "f" * 64
    with pytest.raises(E1C2ScheduleContractError, match="cluster CRF digest"):
        validate_e1_c2_schedule(schedule, cluster_crf_sha256=wrong)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target", 1.0),
        ("zeta2_temporal_surplus_bits", 1.0),
        ("release_offset", 3),
        ("release_reason", "horizon"),
        ("candidate_trace_sha256", "f" * 64),
        ("outcome", "COMPLETE_TRACE_SCORED"),
    ],
)
def test_outcome_derived_schedule_fields_are_rejected(field: str, value: object) -> None:
    payload = _schedule().to_mapping()
    payload[field] = value

    with pytest.raises(E1C2ScheduleContractError, match="outcome-derived"):
        E1C2PreOutcomeSchedule.from_mapping(payload)


def test_outcome_derived_cluster_fields_are_rejected() -> None:
    payload = _schedule().to_mapping()
    payload["clusters"][0]["candidate_trace"] = []  # type: ignore[index]

    with pytest.raises(E1C2ScheduleContractError, match="outcome-derived"):
        E1C2PreOutcomeSchedule.from_mapping(payload)


def test_nonfinite_json_constant_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "schedule.json"
    payload = _schedule().to_mapping()
    payload["source_seed"] = float("nan")
    path.write_text(
        json.dumps(payload, allow_nan=True, sort_keys=True), encoding="ascii"
    )

    with pytest.raises(E1C2ScheduleContractError, match="non-finite"):
        load_e1_c2_schedule(path)


def test_action_and_physical_identity_must_be_distinct() -> None:
    with pytest.raises(E1C2ScheduleContractError, match="must differ"):
        E1C2ScheduleCluster(
            **{
                **_cluster().__dict__,
                "candidate_action": 11,
            }
        )
    with pytest.raises(E1C2ScheduleContractError, match="physical_key"):
        E1C2ScheduleCluster(
            **{
                **_cluster().__dict__,
                "candidate_physical_key": (56355, 11),
            }
        )


def test_policy_source_checkpoint_and_cluster_crf_digests_are_required() -> None:
    payload = _schedule().to_mapping()
    payload.pop("checkpoint_sha256")

    with pytest.raises(E1C2ScheduleContractError, match="missing"):
        E1C2PreOutcomeSchedule.from_mapping(payload)


def test_anchor_and_focal_identity_digest_tampering_is_rejected() -> None:
    payload = _schedule().to_mapping()
    payload["clusters"][0]["focal_user"] = 8  # type: ignore[index]

    with pytest.raises(E1C2ScheduleContractError, match="cluster_sha256"):
        E1C2PreOutcomeSchedule.from_mapping(payload)


def test_validate_can_bind_expected_seed_and_lineage() -> None:
    schedule = _schedule()

    assert (
        validate_e1_c2_schedule(
            schedule,
            source_seed=2026091001,
            policy_sha256=_POLICY,
            source_manifest_sha256=_SOURCE,
            checkpoint_sha256=_CHECKPOINT,
            cluster_crf_sha256={
                schedule.clusters[0].cluster_sha256: _CRF
            },
        )
        == schedule.schedule_sha256
    )
    with pytest.raises(E1C2ScheduleContractError, match="requested seed"):
        validate_e1_c2_schedule(schedule, source_seed=2026091002)
    with pytest.raises(E1C2ScheduleContractError, match="requested lineage"):
        validate_e1_c2_schedule(schedule, checkpoint_sha256="e" * 64)


def test_seal_is_atomic_write_once_and_load_checks_file_sha(tmp_path: Path) -> None:
    schedule = _schedule()
    path = tmp_path / "sealed" / "c2-schedule.json"
    file_sha256 = seal_e1_c2_schedule(path, schedule)

    assert file_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    loaded = load_e1_c2_schedule(
        path,
        expected_file_sha256=file_sha256,
        source_seed=schedule.source_seed,
        policy_sha256=_POLICY,
        source_manifest_sha256=_SOURCE,
        checkpoint_sha256=_CHECKPOINT,
        cluster_crf_sha256={
            schedule.clusters[0].cluster_sha256: _CRF
        },
    )
    assert loaded == schedule

    with pytest.raises(FileExistsError, match="overwrite"):
        seal_e1_c2_schedule(path, schedule)
    with pytest.raises(E1C2ScheduleContractError, match="expected seal"):
        load_e1_c2_schedule(path, expected_file_sha256="f" * 64)


def test_load_rejects_noncanonical_or_tampered_bytes(tmp_path: Path) -> None:
    schedule = _schedule()
    path = tmp_path / "schedule.json"
    seal_e1_c2_schedule(path, schedule)
    payload = json.loads(path.read_text(encoding="ascii"))
    payload["clusters"][0]["anchor_step"] = 4
    path.write_text(json.dumps(payload, sort_keys=True), encoding="ascii")

    with pytest.raises(E1C2ScheduleContractError):
        load_e1_c2_schedule(path)
