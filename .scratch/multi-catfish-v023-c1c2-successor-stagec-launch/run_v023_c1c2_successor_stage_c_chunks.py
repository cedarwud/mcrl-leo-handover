#!/usr/bin/env python3
"""Arm-decoupled Stage-C chunk worker and deterministic merge controller."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

import stagec_common as common
import run_v023_c1c2_successor_stage_c as sequential_controller


def _runner() -> Any:
    return sequential_controller._module(
        common.PHYSICAL / "v023_c1c2_successor_physical_runner.py"
    )


def _policy(bindings: Mapping[str, object], runner: Any, arm: str) -> Any:
    if arm == "BASELINE":
        baseline = bindings["baseline"]
        return runner.load_baseline_policy(
            checkpoint_path=baseline["checkpoint_path"],
            status_path=baseline["status_path"],
            expected_status_sha256=baseline["status_sha256"],
        )
    stage_a = bindings["stage_a"]
    exports = stage_a["exports"]
    entry = next(item for item in exports if item["arm"] == arm)
    provenance = common.learned_training_provenance(bindings)
    return runner.load_learned_two_route_checkpoint(
        Path(str(stage_a["root"])) / str(entry["path"]),
        arm=arm,
        expected_sha256=str(entry["sha256"]),
        training_provenance=provenance[arm],
    )


def _authenticate_continuation(
    args: argparse.Namespace,
    bindings: Mapping[str, object],
    runner: Any,
) -> dict[str, object]:
    authority_path = getattr(args, "continuation_authority", None)
    marker_path = getattr(args, "owner_notification_marker", None)
    if authority_path is None or marker_path is None:
        raise common.StageCError(
            "post-3000 scheduling requires continuation authority and owner-notification marker"
        )
    root = Path(str(bindings.get("stage_c_output_root", "")))
    checkpoint = common.read_json(
        root / "checkpoints/checkpoint-003000.json", field="preserved 3000 checkpoint"
    )
    policy_bindings = checkpoint.get("policy_bindings")
    if not isinstance(policy_bindings, Mapping) or set(policy_bindings) != set(common.ARMS):
        raise common.StageCError("preserved 3000 checkpoint policy mapping drifted")
    activity = _verify_continuation_activity(args, bindings)
    try:
        authenticated = runner.authenticate_continuation_chain(
            authority_path,
            marker_path,
            root=root,
            bindings_sha256=common.file_sha256(args.bindings),
            plan_sha256=common.PLAN_SHA256,
            policy_bindings=policy_bindings,
            allow_published_continuation=bool(
                getattr(args, "resume_continuation", False)
            ),
        )
    except runner.C1C2PhysicalError as error:
        raise common.StageCError(str(error)) from error
    if (
        activity.get("continuation_authority_sha256")
        != authenticated.get("authority_sha256")
        or activity.get("owner_notification_sha256")
        != authenticated.get("owner_notification_sha256")
    ):
        raise common.StageCError("continuation activity authority binding drifted")
    return authenticated


def _verify_continuation_activity(
    args: argparse.Namespace,
    bindings: Mapping[str, object],
) -> dict[str, object]:
    activity_path = getattr(args, "continuation_activity", None)
    if activity_path is None:
        raise common.StageCError("post-3000 work requires a continuation activity marker")
    activity = common.read_json(activity_path, field="continuation activity marker")
    activity_sha = common.verify_named_sidecar(activity_path)
    receipt_record = activity.get("prefix_verification")
    roots = activity.get("registered_chunk_roots")
    if not isinstance(receipt_record, Mapping) or not isinstance(roots, list) or not roots:
        raise common.StageCError("continuation activity registry is malformed")
    receipt_path = Path(str(receipt_record.get("path", "")))
    receipt = common.read_json(receipt_path, field="continuation prefix verification receipt")
    receipt_sha = common.verify_named_sidecar(receipt_path)
    sequence = activity.get("history_sequence", 1)
    recorded_arm = activity.get("arm")
    recorded_barrier = activity.get("barrier")
    expected_root = Path(str(bindings.get("stage_c_output_root", ""))).resolve()
    expected_activity_root = expected_root / "continuation"
    identity_shape_ok = (
        recorded_arm in common.ARMS
        and type(recorded_barrier) is int
        and recorded_barrier in (6000, 9000)
    )
    base_name = (
        f"ACTIVITY-{recorded_arm}-{recorded_barrier:06d}"
        if identity_shape_ok else "INVALID-ACTIVITY"
    )
    expected_activity_name = (
        f"{base_name}.json" if sequence == 1 else
        f"{base_name}-REVERIFY-{sequence:06d}.json"
        if type(sequence) is int else "INVALID-ACTIVITY.json"
    )
    expected_receipt_names = {
        f"PREFIX-VERIFICATION-{recorded_arm}-{recorded_barrier:06d}-{sequence:06d}.json"
        if identity_shape_ok and type(sequence) is int else "INVALID-RECEIPT"
    }
    if sequence == 1:
        expected_receipt_names.add("PREFIX-VERIFICATION.json")
    if (
        Path(activity_path).resolve().parent != expected_activity_root
        or not identity_shape_ok
        or Path(activity_path).name != expected_activity_name
        or receipt_path.resolve().parent != expected_activity_root
        or receipt_path.name not in expected_receipt_names
        or type(sequence) is not int
        or sequence < 1
        or activity.get("schema") != common.SCHEMA_CONTINUATION_ACTIVITY
        or activity.get("status") != "CONTINUATION_ACTIVITY_REGISTERED"
        or activity.get("formal") is not True
        or Path(str(activity.get("reporting_root", ""))).resolve() != expected_root
        or activity.get("arm") != getattr(args, "arm", activity.get("arm"))
        or activity.get("barrier") != getattr(args, "barrier", activity.get("barrier"))
        or activity.get("bindings_sha256") != common.file_sha256(args.bindings)
        or receipt_record.get("sha256") != receipt_sha
        or receipt.get("schema") != common.SCHEMA_CONTINUATION_PREFIX_VERIFICATION
        or receipt.get("status") != "VERIFIED_HELD_3000_PREFIX"
        or receipt.get("formal") is not True
        or receipt.get("overall_token") != verifier_token()
        or receipt.get("completed_episode") != 3000
        or receipt.get("bindings_sha256") != common.file_sha256(args.bindings)
        or receipt.get("history_sequence", 1) != sequence
    ):
        raise common.StageCError("continuation activity marker authentication drifted")
    predecessor = activity.get("previous_activity")
    if sequence == 1:
        if predecessor is not None:
            raise common.StageCError("initial continuation activity has a predecessor")
    else:
        expected_previous = expected_activity_root / (
            f"{base_name}.json" if sequence == 2
            else f"{base_name}-REVERIFY-{sequence - 1:06d}.json"
        )
        if (
            not isinstance(predecessor, Mapping)
            or Path(str(predecessor.get("path", ""))).resolve()
            != expected_previous.resolve()
            or predecessor.get("sha256") != common.verify_named_sidecar(expected_previous)
        ):
            raise common.StageCError("continuation activity history link drifted")
        shadow = argparse.Namespace(**vars(args))
        shadow.continuation_activity = expected_previous
        prior = _verify_continuation_activity(shadow, bindings)
        if prior.get("registered_chunk_roots") != roots:
            raise common.StageCError("continuation activity registry changed across history")
    chunk_root = getattr(args, "chunk_root", None)
    if chunk_root is not None and str(Path(chunk_root).resolve()) not in roots:
        raise common.StageCError("continuation chunk root is absent from the reporting registry")
    return {**activity, "activity_sha256": activity_sha}


def verifier_token() -> str:
    verifier = sequential_controller._module(
        common.HERE / "verify_v023_c1c2_successor_stagec.py"
    )
    return str(verifier.HELD)


def register_continuation_activity(args: argparse.Namespace) -> dict[str, object]:
    """Verify the complete 3000 prefix and durably register scheduled roots."""

    prospective = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, prospective
    )
    common.verify_acceptance_bundle(
        args.acceptance_bundle,
        {**prospective, "bindings_sha256": common.file_sha256(args.bindings)},
    )
    bindings = common.materialize_stage_ab(prospective, supplement)
    common.verify_runtime_identity(bindings)
    reporting_root = Path(str(bindings["stage_c_output_root"])).resolve()
    registered = [str(path.resolve()) for path in args.chunk_roots]
    if len(registered) != len(set(registered)) or not registered:
        raise common.StageCError("continuation activity requires unique chunk roots")
    with common.root_lock(reporting_root):
        verifier = sequential_controller._module(
            common.HERE / "verify_v023_c1c2_successor_stagec.py"
        )
        report = verifier.verify_finished(
            reporting_root,
            args.bindings,
            args.admission_supplement,
            require_tree_seal=False,
        )
        if report.get("completed_episode") != 3000 or report.get("overall_token") != verifier.HELD:
            raise common.StageCError(
                "continuation scheduling requires a fully verified HELD 3000 prefix"
            )
        authority = _authenticate_continuation_without_activity(
            args, bindings, _runner()
        )
        continuation_dir = reporting_root / "continuation"
        base_name = f"ACTIVITY-{args.arm}-{args.barrier:06d}"
        base_path = continuation_dir / f"{base_name}.json"
        history_paths = ([base_path] if base_path.is_file() else []) + sorted(
            continuation_dir.glob(f"{base_name}-REVERIFY-*.json")
        )
        previous: dict[str, object] | None = None
        for expected_sequence, path in enumerate(history_paths, start=1):
            shadow = argparse.Namespace(**vars(args))
            shadow.continuation_activity = path
            recorded = _verify_continuation_activity(shadow, bindings)
            sequence = recorded.get("history_sequence", 1)
            predecessor = recorded.get("previous_activity")
            if sequence != expected_sequence:
                raise common.StageCError("continuation activity history is not contiguous")
            if expected_sequence == 1:
                if predecessor is not None:
                    raise common.StageCError("initial continuation activity has a predecessor")
            elif (
                not isinstance(predecessor, Mapping)
                or previous is None
                or Path(str(predecessor.get("path", ""))).resolve()
                != Path(str(previous["path"])).resolve()
                or predecessor.get("sha256") != previous["sha256"]
            ):
                raise common.StageCError("continuation activity history link drifted")
            previous = {
                "path": str(path.resolve()),
                "sha256": recorded["activity_sha256"],
            }
        sequence = len(history_paths) + 1
        receipt_path = continuation_dir / (
            f"PREFIX-VERIFICATION-{args.arm}-{args.barrier:06d}-{sequence:06d}.json"
        )
        receipt = {
            "schema": common.SCHEMA_CONTINUATION_PREFIX_VERIFICATION,
            "status": "VERIFIED_HELD_3000_PREFIX",
            "formal": True,
            "history_sequence": sequence,
            "reporting_root": str(reporting_root),
            "completed_episode": 3000,
            "overall_token": verifier.HELD,
            "bindings_sha256": common.file_sha256(args.bindings),
            "plan_sha256": common.PLAN_SHA256,
            "result_3000_sha256": common.file_sha256(reporting_root / "result.json"),
            "checkpoint_3000_sha256": common.file_sha256(
                reporting_root / "checkpoints/checkpoint-003000.json"
            ),
        }
        receipt_sha = common.publish_sealed_json(
            receipt_path, receipt, field="continuation prefix verification receipt"
        )
        activity_path = continuation_dir / (
            f"{base_name}.json" if sequence == 1
            else f"{base_name}-REVERIFY-{sequence:06d}.json"
        )
        activity = {
            "schema": common.SCHEMA_CONTINUATION_ACTIVITY,
            "status": "CONTINUATION_ACTIVITY_REGISTERED",
            "formal": True,
            "history_sequence": sequence,
            "previous_activity": previous,
            "reporting_root": str(reporting_root),
            "arm": args.arm,
            "barrier": args.barrier,
            "bindings_sha256": common.file_sha256(args.bindings),
            "continuation_authority_sha256": authority["authority_sha256"],
            "owner_notification_sha256": authority["owner_notification_sha256"],
            "prefix_verification": {
                "path": str(receipt_path.resolve()), "sha256": receipt_sha,
            },
            "registered_chunk_roots": registered,
            "published_before_chunk_execution": True,
        }
        activity_sha = common.publish_sealed_json(
            activity_path, activity, field="continuation activity marker"
        )
    return {
        **activity,
        "activity_path": str(activity_path.resolve()),
        "activity_sha256": activity_sha,
    }


def _authenticate_continuation_without_activity(
    args: argparse.Namespace,
    bindings: Mapping[str, object],
    runner: Any,
) -> dict[str, object]:
    """Authenticate authority while the activity marker is being created."""

    shadow = argparse.Namespace(**vars(args))
    shadow.continuation_activity = None
    root = Path(str(bindings.get("stage_c_output_root", "")))
    checkpoint = common.read_json(
        root / "checkpoints/checkpoint-003000.json", field="preserved 3000 checkpoint"
    )
    policy_bindings = checkpoint.get("policy_bindings")
    if not isinstance(policy_bindings, Mapping) or set(policy_bindings) != set(common.ARMS):
        raise common.StageCError("preserved 3000 checkpoint policy mapping drifted")
    try:
        return runner.authenticate_continuation_chain(
            shadow.continuation_authority,
            shadow.owner_notification_marker,
            root=root,
            bindings_sha256=common.file_sha256(shadow.bindings),
            plan_sha256=common.PLAN_SHA256,
            policy_bindings=policy_bindings,
        )
    except runner.C1C2PhysicalError as error:
        raise common.StageCError(str(error)) from error


def authenticate_launch(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, bindings
    )
    acceptance = common.verify_acceptance_bundle(
        args.acceptance_bundle,
        {**bindings, "bindings_sha256": common.file_sha256(args.bindings)},
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings, chunk_mode=True)
    runner = _runner()
    policy = _policy(bindings, runner, args.arm)
    admission_sha = common.verify_named_sidecar(args.runtime_admission)
    admission = runner.authenticate_runtime_admission(
        args.runtime_admission,
        expected_sha256=admission_sha,
        expected_statuses=("PASS_SOURCE_TRAINING_INTEGRITY", "PASS_PLUMBING_INTEGRITY"),
    )
    from mcrl.env.tle import TleArchive

    archive = TleArchive(Path(str(bindings["physical_inputs"]["tle_root"])))
    runner.authenticate_tle_archive(archive, admission)
    environment = sequential_controller._make_environment(archive, 100)
    if common.canonical_sha256(environment.sampler.as_dict()) != admission["sampler"]["as_dict_sha256"]:
        raise common.StageCError("live TRAIN sampler differs from the authenticated admission")
    runner.FixedPolicyEpisodeAdapter(
        policies=(policy,), archive=archive,
        environment_factory=sequential_controller._make_environment,
        rng_factory=sequential_controller._rngs,
        runtime_admission=admission,
    )
    result = {
        "status": "AUTHENTICATED_STAGEC_CHUNK_LAUNCH",
        "arm": args.arm,
        "bindings_sha256": common.file_sha256(args.bindings),
        "supplement_sha256": supplement["supplement_sha256"],
        "acceptance_sha256": acceptance["acceptance_bundle_sha256"],
        "runtime_admission_sha256": admission_sha,
    }
    if (
        getattr(args, "continuation_authority", None) is not None
        or getattr(args, "owner_notification_marker", None) is not None
    ):
        authority = _authenticate_continuation(args, bindings, runner)
        result["continuation_authority_sha256"] = authority["authority_sha256"]
        result["owner_notification_sha256"] = authority["owner_notification_sha256"]
    return result


def run_chunk(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, bindings
    )
    acceptance = common.verify_acceptance_bundle(
        args.acceptance_bundle,
        {**bindings, "bindings_sha256": common.file_sha256(args.bindings)},
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings, chunk_mode=True)
    runner = _runner()
    continuation = (
        _authenticate_continuation(args, bindings, runner) if args.end > 3000 else None
    )
    policy = _policy(bindings, runner, args.arm)
    admission = runner.authenticate_runtime_admission(
        args.runtime_admission,
        expected_sha256=common.verify_named_sidecar(args.runtime_admission),
        expected_statuses=(
            "PASS_SOURCE_TRAINING_INTEGRITY",
            "PASS_PLUMBING_INTEGRITY",
        ),
    )
    from mcrl.env.tle import TleArchive

    physical = bindings["physical_inputs"]
    archive = TleArchive(Path(str(physical["tle_root"])))
    adapter = runner.FixedPolicyEpisodeAdapter(
        policies=(policy,),
        archive=archive,
        environment_factory=sequential_controller._make_environment,
        rng_factory=sequential_controller._rngs,
        runtime_admission=admission,
    )
    plan = runner.EvaluationPlan.from_file(bindings["world_plan"]["path"])
    schedule_sha = str(bindings["scheduling_addendum"]["sha256"])
    context = {
        "arm": args.arm,
        "adapter": adapter,
        "schedule_sha256": schedule_sha,
        "execution_mode": "arm_decoupled",
        "formal": True,
        "continuation_limit": 9000 if continuation is not None else 3000,
        "continuation_authority": continuation,
        "parent_checkpoint": (
            None if args.parent_checkpoint is None else {
                "path": str(args.parent_checkpoint.resolve()),
                "sha256": common.file_sha256(args.parent_checkpoint),
            }
        ),
        "repair_authority_path": args.repair_authority,
        "repair_authority_sha256": (
            None if args.repair_authority is None else common.verify_named_sidecar(args.repair_authority)
        ),
        "provenance": {
            "authority_sha256": common.file_sha256(args.bindings),
            "code_manifest_sha256": bindings["code"]["external_manifest_sha256"],
            "configuration_sha256": common.canonical_sha256(bindings["execution"]),
            "tle_sha256": physical["tle_manifest_sha256"],
            "prereg_sha256": physical["prereg_sha256"],
            "admission_sha256": admission["admission_sha256"],
            "stage_ab_supplement_sha256": supplement["supplement_sha256"],
            "acceptance_evidence_sha256": acceptance["acceptance_bundle_sha256"],
            "acceptance_procedure_sha256": bindings["acceptance_procedure"]["sha256"],
        },
    }
    boundaries = tuple(sorted({0, args.start, args.end}))
    table = runner.build_chunk_boundary_states(plan, context, boundaries)
    return runner.run_arm_chunk(
        args.arm, args.start, args.end, table[args.start], args.chunk_root
    )


def merge_arm(args: argparse.Namespace) -> dict[str, object]:
    verifier = sequential_controller._module(
        common.HERE / "verify_v023_c1c2_successor_stagec.py"
    )
    runner = _runner()
    continuation_required = any(
        common.read_json(root / "chunk-receipt.json", field="chunk receipt").get(
            "end_boundary", 0
        ) > 3000
        for root in args.chunk_roots
    )
    bindings = None
    if continuation_required:
        prospective = common.verify_bindings(args.bindings)
        supplement = common.verify_stage_ab_supplement(
            args.admission_supplement, args.bindings, prospective
        )
        bindings = common.materialize_stage_ab(prospective, supplement)
        _authenticate_continuation(args, bindings, runner)
    for root in args.chunk_roots:
        verifier.verify_arm_chunk(
            root, args.bindings, arm=args.arm,
            admission_supplement=args.admission_supplement,
            acceptance_bundle=args.acceptance_bundle,
            runtime_admission=args.runtime_admission,
            continuation_authority=getattr(args, "continuation_authority", None),
            owner_notification_marker=getattr(args, "owner_notification_marker", None),
            allow_published_continuation=bool(
                getattr(args, "resume_continuation", False)
            ),
        )
    return runner.merge_arm_chunks(args.arm, args.chunk_roots, args.output)


def check_barrier(args: argparse.Namespace) -> dict[str, object]:
    root = args.arm_merge_root
    merge = common.read_json(root / "arm-merge.json", field="previous arm merge")
    if (
        getattr(args, "continuation_authority", None) is not None
        or getattr(args, "owner_notification_marker", None) is not None
        or args.completed > 3000
    ):
        prospective = common.verify_bindings(args.bindings)
        supplement = common.verify_stage_ab_supplement(
            args.admission_supplement, args.bindings, prospective
        )
        bindings = common.materialize_stage_ab(prospective, supplement)
        _authenticate_continuation(args, bindings, _runner())
    if (
        merge.get("status") != "COMPLETE_ARM_MERGE"
        or merge.get("formal") is not True
        or merge.get("arm") != args.arm
        or merge.get("arm_order") != list(common.ARMS)
        or merge.get("completed_episode") != args.completed
    ):
        raise common.StageCError("previous cumulative arm barrier is not complete")
    verifier = sequential_controller._module(
        common.HERE / "verify_v023_c1c2_successor_stagec.py"
    )
    chunks = merge.get("chunk_receipts")
    if not isinstance(chunks, list) or len(chunks) != args.completed // 100:
        raise common.StageCError("previous barrier lacks chunk provenance")
    runner = _runner()
    rows: list[object] = []
    expected_chunk_ids = []
    for index, record in enumerate(chunks):
        if not isinstance(record, Mapping):
            raise common.StageCError("previous barrier chunk record is malformed")
        start = index * 100
        end = start + 100
        expected_chunk_id = f"{args.arm}-{start:06d}-{end:06d}"
        expected_chunk_ids.append(expected_chunk_id)
        receipt_path = Path(str(record.get("path", "")))
        receipt = common.read_json(receipt_path, field="previous barrier chunk receipt")
        if (
            common.file_sha256(receipt_path) != record.get("sha256")
            or record.get("chunk_id") != expected_chunk_id
            or receipt.get("chunk_id") != expected_chunk_id
            or receipt.get("arm") != args.arm
            or receipt.get("range") != [start + 1, end]
            or receipt.get("start_boundary") != start
            or receipt.get("end_boundary") != end
        ):
            raise common.StageCError("previous barrier chunk receipt drifted")
        verifier.verify_arm_chunk(
            receipt_path.parent, args.bindings, arm=args.arm,
            admission_supplement=args.admission_supplement,
            acceptance_bundle=args.acceptance_bundle,
            runtime_admission=args.runtime_admission,
            continuation_authority=getattr(args, "continuation_authority", None),
            owner_notification_marker=getattr(args, "owner_notification_marker", None),
            allow_published_continuation=bool(
                getattr(args, "resume_continuation", False)
            ),
        )
        for episode in range(start + 1, end + 1):
            row, _state = runner._read_episode_record(
                receipt_path.parent / "episodes" / f"episode-{episode:06d}.json"
            )
            rows.append(row)
    if merge.get("chunk_ids") != expected_chunk_ids:
        raise common.StageCError("previous barrier chunk set is not exact contiguous coverage")
    expected_names = [f"checkpoint-{boundary:06d}.json" for boundary in range(100, args.completed + 1, 100)]
    if (
        [path.name for path in sorted((root / "checkpoints").glob("checkpoint-*.json"))]
        != expected_names
        or [path.name for path in sorted((root / "rungs").glob("rung-*.json"))]
        != [name.replace("checkpoint", "rung") for name in expected_names]
    ):
        raise common.StageCError("previous barrier checkpoint/rung cadence is incomplete")
    artifacts = merge.get("barrier_artifacts")
    expected_boundaries = {str(boundary) for boundary in range(100, args.completed + 1, 100)}
    if not isinstance(artifacts, Mapping) or set(artifacts) != expected_boundaries:
        raise common.StageCError("previous barrier artifact bindings are incomplete")
    checkpoint_fields = {
        "schema", "arm", "completed_episode", "plan_sha256", "schedule_sha256",
        "receipts", "pooled", "execution_mode", "chunk_receipts", "resume_state",
        "scientific_disposition_emitted",
    }
    rung_fields = {
        "schema", "arm", "completed_episode", "plan_sha256", "schedule_sha256",
        "pooled", "execution_mode", "chunk_receipts", "scientific_disposition_emitted",
    }
    for boundary in range(100, args.completed + 1, 100):
        record = artifacts[str(boundary)]
        if not isinstance(record, Mapping):
            raise common.StageCError("previous barrier artifact binding is malformed")
        loaded = {}
        for kind, expected_path in (
            ("checkpoint", root / "checkpoints" / f"checkpoint-{boundary:06d}.json"),
            ("rung", root / "rungs" / f"rung-{boundary:06d}.json"),
        ):
            binding = record.get(kind)
            if (
                not isinstance(binding, Mapping)
                or Path(str(binding.get("path", ""))).resolve(strict=False)
                != expected_path.resolve(strict=False)
                or common.file_sha256(expected_path) != binding.get("sha256")
            ):
                raise common.StageCError(f"previous barrier {kind} digest drifted")
            loaded[kind] = common.read_json(expected_path, field=f"barrier {kind} {boundary}")
        checkpoint = loaded["checkpoint"]
        rung = loaded["rung"]
        prefix = rows[:boundary]
        pooled = runner.pool_receipts(prefix, arm=args.arm)
        if (
            set(checkpoint) != checkpoint_fields
            or checkpoint.get("schema") != f"{runner.CHECKPOINT_SCHEMA}-arm-merge-v1"
            or checkpoint.get("arm") != args.arm
            or checkpoint.get("completed_episode") != boundary
            or checkpoint.get("plan_sha256") != merge.get("plan_sha256")
            or checkpoint.get("schedule_sha256") != merge.get("schedule_sha256")
            or checkpoint.get("receipts") != [row.as_dict() for row in prefix]
            or checkpoint.get("pooled") != pooled
            or checkpoint.get("chunk_receipts") != chunks
            or checkpoint.get("scientific_disposition_emitted") is not False
            or checkpoint.get("execution_mode") != "arm_decoupled"
        ):
            raise common.StageCError("previous barrier checkpoint contents drifted")
        if (
            set(rung) != rung_fields
            or rung.get("schema") != f"{runner.RUNG_SCHEMA}-arm-merge-v1"
            or rung.get("arm") != args.arm
            or rung.get("completed_episode") != boundary
            or rung.get("plan_sha256") != merge.get("plan_sha256")
            or rung.get("schedule_sha256") != merge.get("schedule_sha256")
            or rung.get("pooled") != pooled
            or rung.get("chunk_receipts") != chunks
            or rung.get("scientific_disposition_emitted") is not False
            or rung.get("execution_mode") != "arm_decoupled"
        ):
            raise common.StageCError("previous barrier rung contents drifted")
    if (
        merge.get("ordered_episode_digest")
        != runner.canonical_sha256([row.as_dict() for row in rows])
        or merge.get("pooled") != runner.pool_receipts(rows, arm=args.arm)
    ):
        raise common.StageCError("previous barrier merged episode count/pool drifted")
    return {
        "status": "AUTHENTICATED_CUMULATIVE_BARRIER",
        "arm": args.arm,
        "completed_episode": args.completed,
        "arm_merge_sha256": common.file_sha256(root / "arm-merge.json"),
    }


def merge_four(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, bindings
    )
    common.verify_acceptance_bundle(
        args.acceptance_bundle,
        {**bindings, "bindings_sha256": common.file_sha256(args.bindings)},
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings)
    roots = {arm: root for arm, root in zip(common.ARMS, args.arm_roots, strict=True)}
    mappings = common.read_json(args.admission_mapping, field="four-arm admission mapping")
    mapping = common.verify_stage_c_admission_mapping(mappings.get("admission_mapping"))
    runner = _runner()
    merges = {
        arm: common.read_json(root / "arm-merge.json", field=f"{arm} arm merge")
        for arm, root in roots.items()
    }
    completed = {merge.get("completed_episode") for merge in merges.values()}
    if len(completed) != 1:
        raise common.StageCError("four-arm merge boundaries disagree")
    boundary = completed.pop()
    continuation = None
    verifier = sequential_controller._module(
        common.HERE / "verify_v023_c1c2_successor_stagec.py"
    )
    if boundary == 9000:
        continuation = _authenticate_continuation(args, bindings, runner)
        if not args.resume_continuation:
            prefix = verifier.verify_finished(
                args.output, args.bindings, args.admission_supplement,
                require_tree_seal=False,
            )
            if prefix.get("completed_episode") != 3000 or prefix.get("overall_token") != runner.HELD:
                raise common.StageCError("continuation requires an independently verified HELD 3000 root")
    elif boundary != 3000:
        raise common.StageCError("four-arm merge must publish boundary 3000 or 9000")
    result = runner.merge_four_arm(
        roots, args.output, admission_mapping=mapping,
        continuation_authority=continuation,
        resume_continuation=bool(args.resume_continuation),
    )
    policy_bindings = {
        arm: mapping[arm]["policy_binding"] for arm in common.ARMS
    }
    if boundary == 3000:
        sequential_controller._formal_marker(
            args.output,
            common.file_sha256(args.bindings),
            common.PLAN_SHA256,
            mapping,
        )
        common.publish_sealed_json(
            args.output / common.FORMAL_ADMISSION_NAME,
            mappings,
            field="formal Stage-C admission",
        )
        if result.get("overall_token") == runner.FALSIFIED:
            common.write_tree_seal(args.output)
    else:
        verifier._verify_continuation_result_semantics(
            common.read_json(
                args.output / "continuation-result.json",
                field="producer 9000 continuation receipt",
            )
        )
        verifier.verify_finished(
            args.output, args.bindings, args.admission_supplement,
            require_tree_seal=False,
        )
        common.write_tree_seal(args.output)
        verifier.verify_finished(args.output, args.bindings, args.admission_supplement)
    result["bindings_sha256"] = common.file_sha256(args.bindings)
    result["policy_bindings_sha256"] = common.canonical_sha256(policy_bindings)
    result["stage_ab_supplement_sha256"] = supplement["supplement_sha256"]
    result["acceptance_evidence_sha256"] = common.file_sha256(args.acceptance_bundle)
    return result


def _parser() -> argparse.ArgumentParser:
    def continuation_options(
        command: argparse.ArgumentParser, *, resume: bool = False
    ) -> None:
        command.add_argument("--continuation-authority", type=Path)
        command.add_argument("--owner-notification-marker", type=Path)
        command.add_argument("--continuation-activity", type=Path)
        if resume:
            command.add_argument("--resume-continuation", action="store_true")

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-launch")
    check.add_argument("--bindings", type=Path, required=True)
    check.add_argument("--admission-supplement", type=Path, required=True)
    check.add_argument("--acceptance-bundle", type=Path, required=True)
    check.add_argument("--runtime-admission", type=Path, required=True)
    check.add_argument("--arm", choices=common.ARMS, required=True)
    continuation_options(check, resume=True)
    barrier = sub.add_parser("check-barrier")
    barrier.add_argument("--bindings", type=Path, required=True)
    barrier.add_argument("--admission-supplement", type=Path, required=True)
    barrier.add_argument("--acceptance-bundle", type=Path, required=True)
    barrier.add_argument("--runtime-admission", type=Path, required=True)
    barrier.add_argument("--arm", choices=common.ARMS, required=True)
    barrier.add_argument("--completed", type=int, choices=common.CHUNK_BARRIERS, required=True)
    barrier.add_argument("--arm-merge-root", type=Path, required=True)
    continuation_options(barrier, resume=True)
    chunk = sub.add_parser("run-chunk")
    chunk.add_argument("--bindings", type=Path, required=True)
    chunk.add_argument("--arm", choices=common.ARMS, required=True)
    chunk.add_argument("--start", type=int, required=True)
    chunk.add_argument("--end", type=int, required=True)
    chunk.add_argument("--chunk-root", type=Path, required=True)
    chunk.add_argument("--runtime-admission", type=Path, required=True)
    chunk.add_argument("--admission-supplement", type=Path, required=True)
    chunk.add_argument("--acceptance-bundle", type=Path, required=True)
    chunk.add_argument("--parent-checkpoint", type=Path)
    chunk.add_argument("--repair-authority", type=Path)
    continuation_options(chunk)
    arm = sub.add_parser("merge-arm")
    arm.add_argument("--arm", choices=common.ARMS, required=True)
    arm.add_argument("--chunk-roots", type=Path, nargs="+", required=True)
    arm.add_argument("--output", type=Path, required=True)
    arm.add_argument("--bindings", type=Path, required=True)
    arm.add_argument("--admission-supplement", type=Path, required=True)
    arm.add_argument("--acceptance-bundle", type=Path, required=True)
    arm.add_argument("--runtime-admission", type=Path, required=True)
    continuation_options(arm, resume=True)
    four = sub.add_parser("merge-four")
    four.add_argument("--bindings", type=Path, required=True)
    four.add_argument("--arm-roots", type=Path, nargs=4, required=True)
    four.add_argument(
        "--admission-mapping",
        type=Path,
        required=True,
        help="wrapped JSON produced by build_stage_c_admission_mapping.py",
    )
    four.add_argument("--admission-supplement", type=Path, required=True)
    four.add_argument("--acceptance-bundle", type=Path, required=True)
    four.add_argument("--output", type=Path, required=True)
    continuation_options(four, resume=True)
    register = sub.add_parser("register-continuation")
    register.add_argument("--bindings", type=Path, required=True)
    register.add_argument("--admission-supplement", type=Path, required=True)
    register.add_argument("--acceptance-bundle", type=Path, required=True)
    register.add_argument("--arm", choices=common.ARMS, required=True)
    register.add_argument("--barrier", type=int, choices=(6000, 9000), required=True)
    register.add_argument("--chunk-roots", type=Path, nargs="+", required=True)
    register.add_argument("--continuation-authority", type=Path, required=True)
    register.add_argument("--owner-notification-marker", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check-launch":
            result = authenticate_launch(args)
        elif args.command == "check-barrier":
            result = check_barrier(args)
        elif args.command == "run-chunk":
            result = run_chunk(args)
        elif args.command == "merge-arm":
            result = merge_arm(args)
        elif args.command == "register-continuation":
            result = register_continuation_activity(args)
        else:
            result = merge_four(args)
    except Exception as error:
        print(f"STOP_PHYSICAL_EVALUATION_INTEGRITY: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
