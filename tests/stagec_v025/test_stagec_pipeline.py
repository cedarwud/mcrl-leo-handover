from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import numpy as np
import pytest

from mcrl.stagec_v025.canonical import (
    StageCContractError,
    read_verified_json,
    write_once_json,
)
from mcrl.stagec_v025.deployment import (
    DeploymentAdapter,
    ResolvedProfile,
    UserActionTable,
)
from mcrl.stagec_v025.evaluation import (
    AllocationManifest,
    AllocationUnit,
    AttemptRegistry,
    StepOutcome,
    _step_payload,
)
from mcrl.stagec_v025.learner import (
    LEARNED_ARMS,
    ROUTES,
    SOURCE_MAP,
    LineageOrchestrator,
    LinearHead,
    ThreeRouteModel,
    build_pairwise_batches,
)
from mcrl.stagec_v025.merge import AdditiveTotals, _metrics, merge_receipts
from mcrl.stagec_v025.shards import read_source_shard, write_source_shard
from mcrl.stagec_v025.state import (
    PhysicalAction,
    Q1_FEATURES,
    Q2_FEATURES,
    extract_source_rows,
)
from mcrl.stagec_v025.synthetic import (
    make_synthetic_anchors,
    run_synthetic_pipeline,
)


def _training_fixture(tmp_path: Path) -> tuple[LineageOrchestrator, object]:
    rows = tuple(
        row
        for anchor in make_synthetic_anchors()
        for row in extract_source_rows(anchor)
    )
    shard = write_source_shard(tmp_path / "source.jsonl", rows)
    reopened = read_source_shard(shard.path)
    batches = build_pairwise_batches((reopened,))
    return LineageOrchestrator(learner_seed=101, batches=batches), reopened


def test_synthetic_end_to_end_five_seeds_six_arms(tmp_path: Path) -> None:
    report = run_synthetic_pipeline(tmp_path, epochs=3, bootstrap_draws=32)

    assert report["schema"] == "mcrl-v025-stagec-terminal-report-v1-draft"
    assert report["cluster_count"] == 10
    assert report["world_count"] == 20
    assert report["synthetic"]["learner_seeds"] == [101, 202, 303, 404, 505]
    assert report["synthetic"]["arms_per_seed"] == 6
    assert report["synthetic"]["learned_arms_per_seed"] == 5
    assert report["synthetic"]["external_baseline_per_seed"] == 1
    assert report["synthetic"]["conformance"]["null_equals_base"] is True
    assert report["synthetic"]["conformance"]["real_step_arms"] == [
        "FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL", "BASELINE"
    ]
    assert report["synthetic"]["conformance"]["supportive_comparators"] == ["S_UNI"]
    assert report["supportive_comparators"]["S_UNI"]["pooled_joules"] > 0
    assert report["claim"]["decision"] in {"CLAIM_PASS", "CLAIM_FAIL"}
    assert report["physics_admission"]["decision"] == "PHYSICS-GO"
    assert report["terminal_adjudication_count"] == 1
    assert report["artifact_digests"]["deployment_capability"]
    assert report["pooled_additive_totals"]["FULL"]["joules_hex"]
    assert report["attempt_registry"]["record_count"] == 40
    conformance_records = AttemptRegistry(
        tmp_path / "CONFORMANCE-ATTEMPT-REGISTRY-2026-09.jsonl"
    ).records()
    assert [record["status"] for record in conformance_records] == ["STARTED", "DONE"]
    assert (tmp_path / "conformance" / "d0-s101-w0.conformance.json.sha256").is_file()
    receipt = read_verified_json(
        tmp_path / "receipts" / "d0-s101-w0.receipt.json"
    )
    full_rows = [row for row in receipt["steps"] if row["arm"] == "FULL"]
    assert {event["event_type"] for event in full_rows[0]["events"]} <= {
        "unchanged", "beam_change", "satellite_change"
    }
    assert {event["event_type"] for event in full_rows[1]["events"]} == {"unchanged"}


def test_golden_tape_to_row_all_q1_q2_fields_and_authorities() -> None:
    rows = extract_source_rows(make_synthetic_anchors()[0])
    row = rows[0]

    assert [feature.name for feature in Q1_FEATURES] == [
        "nominal_sinr_margin_at_rate_target",
        "nominal_required_power_over_cap",
        "nominal_mode_spectral_efficiency",
        "background_occupancy_excluding_focal",
        "beam_active_before_focal",
        "satellite_active_before_focal",
        "off_axis_angle",
        "remaining_d2_time",
        "remaining_visibility_time",
        "refresh_phase",
        "previous_served_association_for_action",
        "previous_served_load_for_action",
        "previous_beam_active_for_action",
        "previous_satellite_active_for_action",
        "previous_beam_max_rf_over_cap",
        "missing_incumbent",
    ]
    assert row.q1_state == pytest.approx(
        (0.1, 0.7, 0.5, 0.1, 1.0, 1.0, 0.1, 0.75, 5 / 6, 0.0,
         1.0, 0.1, 1.0, 1.0, 0.7, 0.0)
    )
    assert len(Q2_FEATURES) == 22
    assert row.q2_state == pytest.approx(
        (0.1, 0.0, 0.75, 5 / 6, 0.0, 0.1, 1.0, 1.0, 0.5 / 1.65, 0.0,
         1.0, 1.0, 0.2, 0.5, 1.0, 1.0, 0.25, 0.525,
         1.0, 1.0, 0.3, 0.55)
    )
    assert row.action_mask == (True, True, True)
    assert row.reference_action is True
    assert row.c1_label_normalized_hex == 0.0.hex()
    assert all(
        len(getattr(row, field)) == 64
        for field in (
            "code_digest", "physics_digest", "launch_digest", "catalogue_digest",
            "setting_digest", "calibration_digest", "provider_digest", "archive_digest",
            "allocation_manifest_digest",
        )
    )
    candidate = rows[1]
    assert candidate.user_id == 0
    assert candidate.action_index == 1
    assert candidate.action == PhysicalAction(200, 20)
    assert candidate.decision_time_utc == "2026-01-01T00:00:00Z"
    assert candidate.decision_time_ns == 0
    assert candidate.learner_seed is None
    assert candidate.q1_state[3] == 0.0  # focal excluded from background occupancy
    assert candidate.c1_label_normalized_hex == 1.2.hex()
    assert candidate.c2_label_normalized_hex == 0.8.hex()
    assert candidate.c3_label_normalized_hex == 0.6.hex()
    assert (candidate.terminal, candidate.null_action, candidate.outage) == (
        False, False, False
    )
    null = rows[2]
    assert null.null_action is True
    assert null.action == PhysicalAction(None, None)


def test_noncontiguous_disconnected_partial_service_roster_is_preserved() -> None:
    digest = "0" * 64
    unit = AllocationUnit(
        "e", "p", "c", "u", "w", "2026-01-01T00:00:00Z", "2026-01-01",
        "TRAIN", "synthetic", digest, digest, digest, digest, digest, digest, digest,
        digest, digest, 101, 1,
    )
    row = _step_payload(
        unit=unit,
        arm="BASELINE",
        step_index=0,
        outcome=StepOutcome(
            bits=0.0,
            energy_components_j={"standby": 1.0},
            user_ids=(41, 99),
            profile=(PhysicalAction(None, None), PhysicalAction(7, 3)),
            complete_service=(False, True),
            decoding_user_seconds=1.0,
            useful_user_seconds=1.0,
            opportunity_user_seconds=2.0,
            jointly_legal=True,
        ),
        previous=None,
        ever_served=set(),
    )

    assert [event["user_id"] for event in row["events"]] == [41, 99]
    assert [event["event_type"] for event in row["events"]] == ["unchanged", "initial_entry"]
    assert row["complete_service_numerator"] == 1
    assert row["complete_service_denominator"] == 2
    assert row["bits_hex"] == 0.0.hex()


def test_all_temporal_event_identities_are_derived_from_committed_history() -> None:
    digest = "0" * 64
    unit = AllocationUnit(
        "e", "p", "c", "events", "w", "2026-01-01T00:00:00Z", "2026-01-01",
        "TRAIN", "synthetic", digest, digest, digest, digest, digest, digest, digest,
        digest, digest, 101, 1,
    )
    before = (
        PhysicalAction(1, 1), PhysicalAction(2, 1), PhysicalAction(3, 1),
        PhysicalAction(5, 1), PhysicalAction(None, None),
        PhysicalAction(None, None), PhysicalAction(8, 1),
    )
    after = (
        PhysicalAction(1, 1), PhysicalAction(2, 2), PhysicalAction(4, 1),
        PhysicalAction(5, 1), PhysicalAction(6, 1), PhysicalAction(7, 1),
        PhysicalAction(None, None),
    )
    row = _step_payload(
        unit=unit,
        arm="FULL",
        step_index=0,
        outcome=StepOutcome(
            bits=1.0,
            energy_components_j={"total": 1.0},
            user_ids=(10, 11, 12, 13, 14, 15, 16),
            profile=after,
            complete_service=(True,) * 7,
            decoding_user_seconds=7.0,
            useful_user_seconds=7.0,
            opportunity_user_seconds=7.0,
            jointly_legal=True,
            cell_rekey_users=frozenset({13}),
        ),
        previous=before,
        ever_served={10, 11, 12, 13, 15, 16},
    )

    assert [event["event_type"] for event in row["events"]] == [
        "unchanged", "beam_change", "satellite_change", "cell_rekey",
        "initial_entry", "reentry", "exit",
    ]


def test_unequal_energy_kat_uses_pooled_ratios_not_mean_world_ratios() -> None:
    full = AdditiveTotals(bits=20.0, joules=10.0)
    drop = AdditiveTotals(bits=16.0, joules=2.0)
    metrics = _metrics(full, drop)
    mean_world_relative = ((10.0 / 1.0) / (8.0 / 1.0) - 1.0 + (10.0 / 9.0) / (8.0 / 1.0) - 1.0) / 2.0

    assert metrics["ee_relative"] == pytest.approx(-0.75)
    assert metrics["ee_relative"] != pytest.approx(mean_world_relative)
    assert _metrics(
        AdditiveTotals(bits=0.0, joules=1.0),
        AdditiveTotals(bits=1.0, joules=1.0),
    )["ee_relative"] == -1.0
    assert _metrics(
        AdditiveTotals(bits=1.0, joules=1.0),
        AdditiveTotals(bits=0.0, joules=1.0),
    )["ee_relative"] is None


def test_two_user_independent_argmax_cannot_commit_jointly_infeasible_profile() -> None:
    q1_dimension = len(Q1_FEATURES)
    q2_dimension = len(Q2_FEATURES)
    c3_dimension = q1_dimension + q2_dimension
    model = ThreeRouteModel(
        {
            "C1": LinearHead(np.ones(q1_dimension), 0.0),
            "C2": LinearHead(np.ones(q2_dimension), 0.0),
            "C3": LinearHead(np.zeros(c3_dimension), 0.0),
        }
    )
    tables = tuple(
        UserActionTable(
            user_id=user,
            actions=(
                PhysicalAction(100 + user, 10 + user),
                PhysicalAction(200 + user, 20 + user),
                PhysicalAction(None, None),
            ),
            action_mask=(True, True, True),
            q1_states=(
                tuple(np.zeros(q1_dimension)),
                tuple(np.ones(q1_dimension)),
                tuple(np.zeros(q1_dimension)),
            ),
            q2_states=(
                tuple(np.zeros(q2_dimension)),
                tuple(np.ones(q2_dimension)),
                tuple(np.zeros(q2_dimension)),
            ),
        )
        for user in range(2)
    )
    decision = DeploymentAdapter().select(
        model=model,
        tables=tables,
        base_profile=(0, 0),
        catalogue=((0, 0),),
        jointly_legal=lambda profile: profile != (1, 1),
        resolve_profile=lambda profile: ResolvedProfile(profile, 2),
    )

    assert decision.independent_profile == (1, 1)
    assert decision.profile == (0, 0)
    assert decision.jointly_legal is True
    assert decision.used_fallback is True
    assert decision.fallback_reason == "independent_profile_jointly_infeasible"


def test_deployment_validation_exception_commits_base_atomically() -> None:
    dimension_q1 = len(Q1_FEATURES)
    dimension_q2 = len(Q2_FEATURES)
    model = ThreeRouteModel(
        {
            "C1": LinearHead(np.ones(dimension_q1), 0.0),
            "C2": LinearHead(np.ones(dimension_q2), 0.0),
            "C3": LinearHead(np.zeros(dimension_q1 + dimension_q2), 0.0),
        }
    )
    table = UserActionTable(
        user_id=8,
        actions=(PhysicalAction(1, 1), PhysicalAction(2, 2), PhysicalAction(None, None)),
        action_mask=(True, True, True),
        q1_states=(
            tuple(np.zeros(dimension_q1)),
            tuple(np.ones(dimension_q1)),
            tuple(np.zeros(dimension_q1)),
        ),
        q2_states=(
            tuple(np.zeros(dimension_q2)),
            tuple(np.ones(dimension_q2)),
            tuple(np.zeros(dimension_q2)),
        ),
    )

    def resolve(profile: tuple[int, ...]) -> ResolvedProfile:
        if profile == (1,):
            raise RuntimeError("synthetic resolver failure")
        return ResolvedProfile(profile, 1)

    decision = DeploymentAdapter().select(
        model=model,
        tables=(table,),
        base_profile=(0,),
        catalogue=((1,),),
        jointly_legal=lambda profile: profile in {(0,), (1,)},
        resolve_profile=resolve,
    )

    assert decision.profile == (0,)
    assert decision.used_fallback is True
    assert decision.fallback_reason == "validation_failure:RuntimeError"


def test_drop_arms_retain_and_update_all_heads(tmp_path: Path) -> None:
    orchestrator, _ = _training_fixture(tmp_path)
    initial = {
        arm: {
            route: orchestrator.models[arm].heads[route].weights.copy()
            for route in ROUTES
        }
        for arm in LEARNED_ARMS
    }
    orchestrator.train_epoch()

    assert SOURCE_MAP["DROP_C1"] == {
        "C1": "neutral", "C2": "informed", "C3": "informed"
    }
    for arm in LEARNED_ARMS:
        assert set(orchestrator.models[arm].heads) == set(ROUTES)
        assert all(
            not np.array_equal(initial[arm][route], orchestrator.models[arm].heads[route].weights)
            for route in ROUTES
        )
    checkpoint = orchestrator.checkpoint_payload()
    assert checkpoint["completed_source_epochs"] == 1
    assert checkpoint["route_update_count"] == 3
    assert all(set(checkpoint["arms"][arm]) == set(ROUTES) for arm in LEARNED_ARMS)
    assert checkpoint["zero_bootstrap"] is True


def test_summary_mutation_is_rejected_even_when_receipt_hash_is_recomputed(
    tmp_path: Path,
) -> None:
    original_root = tmp_path / "original"
    run_synthetic_pipeline(original_root, epochs=1, bootstrap_draws=8)
    allocation_payload = read_verified_json(original_root / "allocation-manifest.json")
    units = tuple(
        AllocationUnit(**payload) for payload in allocation_payload["units"]
    )
    manifest = AllocationManifest.create(
        units,
        bootstrap_draws=int(allocation_payload["bootstrap_draws"]),
        bootstrap_seed=int(allocation_payload["bootstrap_seed"]),
    )
    assert manifest.digest == allocation_payload["allocation_manifest_sha256"]

    replacement_root = tmp_path / "mutated"
    replacement_registry = AttemptRegistry(replacement_root / "attempts.jsonl")
    replacement_receipts: list[Path] = []
    for index, unit in enumerate(units):
        source = original_root / "receipts" / f"{unit.unit_id}.receipt.json"
        payload = read_verified_json(source)
        if index == 0:
            payload["summary"]["FULL"]["bits_hex"] = float(999999.0).hex()
        destination = replacement_root / "receipts" / source.name
        replacement_registry.append(
            status="STARTED",
            unit=unit,
            allocation_manifest_digest=manifest.digest,
        )
        digest = write_once_json(destination, payload)
        replacement_registry.append(
            status="DONE",
            unit=unit,
            allocation_manifest_digest=manifest.digest,
            receipt_sha256=digest,
        )
        replacement_receipts.append(destination)

    with pytest.raises(StageCContractError, match="summary disagrees with rows"):
        merge_receipts(
            replacement_receipts,
            manifest=manifest,
            registry=replacement_registry,
            bootstrap_draws=8,
        )


def test_checkpoint_cadence_and_authenticated_resume(tmp_path: Path) -> None:
    orchestrator, _ = _training_fixture(tmp_path)
    checkpoint_directory = tmp_path / "checkpoints"
    orchestrator.train(100, checkpoint_directory=checkpoint_directory)
    checkpoint = checkpoint_directory / "learner-101-epoch-000100.json"
    assert checkpoint.is_file()
    assert checkpoint.with_name(checkpoint.name + ".sha256").is_file()

    clone, _ = _training_fixture(tmp_path / "second")
    clone.load_checkpoint(checkpoint)
    assert clone.completed_source_epochs == 100
    assert clone.route_update_count == 300
    assert clone.checkpoint_payload()["arms"] == orchestrator.checkpoint_payload()["arms"]


def test_train_assertion_rejects_non_train_anchor() -> None:
    anchor = make_synthetic_anchors()[0]
    payload = {field.name: getattr(anchor, field.name) for field in fields(anchor)}
    payload["split"] = "TEST"
    with pytest.raises(StageCContractError, match="TRAIN-only"):
        extract_source_rows(type(anchor)(**payload))


def test_shard_boundary_recomputes_dimensions_masks_and_labels(
    tmp_path: Path,
) -> None:
    row = extract_source_rows(make_synthetic_anchors()[0])[1]
    corruptions = (
        replace(row, q1_state=(0.0,)),
        replace(row, action_mask=(True, False, True)),
        replace(row, lambda_bits_per_j_hex=11.0.hex()),
        replace(row, c1_label_normalized_hex=999.0.hex()),
    )

    for index, corrupted in enumerate(corruptions):
        with pytest.raises(StageCContractError):
            write_source_shard(tmp_path / f"bad-{index}.jsonl", (corrupted,))
