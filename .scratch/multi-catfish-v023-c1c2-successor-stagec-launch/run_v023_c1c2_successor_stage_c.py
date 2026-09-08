#!/usr/bin/env python3
"""Server controller for cumulative formal Stage-C pauses and continuation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Mapping

import stagec_common as common


def _module(path: Path) -> Any:
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    result = importlib.import_module(path.stem)
    if Path(result.__file__).resolve() != path.resolve():
        raise common.StageCError(f"module origin drifted: {path}")
    return result


def _make_environment(archive: Any, users: int) -> Any:
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.runtime.trainer_env import TrainerEnvironment

    driver = ScenarioDriver(archive, ScenarioConfig(mobility=MobilityConfig(num_users=users)))
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def _rngs(seed: int) -> tuple[Any, Any]:
    import numpy as np
    sequence = np.random.SeedSequence(seed)
    children = sequence.spawn(2)
    return np.random.default_rng(children[0]), np.random.default_rng(children[1])


def _authenticate_preflight(
    path: Path, bindings_sha: str, *, supplement_sha: str, acceptance_sha: str
) -> None:
    receipt = common.read_json(path, field="Stage-C preflight receipt")
    common.verify_named_sidecar(path)
    if (
        receipt.get("status") != "PASS_V023_C1C2_SUCCESSOR_STAGEC_PREFLIGHT"
        or receipt.get("formal") is not True
        or receipt.get("bindings_sha256") != bindings_sha
        or receipt.get("arms") != list(common.ARMS)
        or receipt.get("stage_ab_supplement_sha256") != supplement_sha
        or receipt.get("acceptance_evidence_sha256") != acceptance_sha
    ):
        raise common.StageCError("Stage-C preflight receipt drifted")


def _authenticate_stage_b(root: Path, bindings_sha: str) -> None:
    gate_path = root / "stage-b-gate.json"
    gate = common.read_json(gate_path, field="Stage-B gate")
    common.verify_named_sidecar(gate_path)
    receipt = root / "plumbing-receipt.json"
    plumbing = common.read_json(receipt, field="Stage-B plumbing receipt")
    admission = gate.get("runtime_admission")
    stage_a = gate.get("admitted_stage_a")
    exports = gate.get("admitted_exports")
    if (
        gate.get("status") != "PASS_PLUMBING_INTEGRITY"
        or gate.get("formal") is not True
        or gate.get("bindings_sha256") != bindings_sha
        or gate.get("plumbing_receipt_sha256") != common.file_sha256(receipt)
        or gate.get("arms") != list(common.ARMS)
        or not isinstance(admission, Mapping)
        or not isinstance(stage_a, Mapping)
        or not isinstance(exports, list)
        or plumbing.get("runtime_admission") != admission
        or plumbing.get("admitted_stage_a") != stage_a
        or plumbing.get("admitted_exports") != exports
    ):
        raise common.StageCError("mandatory Stage-B plumbing gate drifted")
    admission_path = Path(str(admission.get("path")))
    if (
        common.file_sha256(admission_path, field="Stage-B runtime admission")
        != admission.get("sha256")
        or common.verify_named_sidecar(admission_path) != admission.get("sha256")
    ):
        raise common.StageCError("Stage-B runtime admission bytes drifted")
    if common.file_sha256(str(stage_a.get("path")), field="Stage-A admitted receipt") != stage_a.get("sha256"):
        raise common.StageCError("Stage-B admitted Stage-A receipt drifted")
    if [entry.get("arm") for entry in exports if isinstance(entry, Mapping)] != list(common.LEARNED_ARMS):
        raise common.StageCError("Stage-B admitted export order drifted")
    for entry in exports:
        if common.file_sha256(str(entry.get("path")), field="Stage-B admitted export") != entry.get("sha256"):
            raise common.StageCError("Stage-B admitted export bytes drifted")


def _policies(bindings: Mapping[str, object], runner: Any) -> tuple[Any, ...]:
    stage_a = bindings["stage_a"]
    baseline = bindings["baseline"]
    exports = stage_a["exports"]
    provenance = common.learned_training_provenance(bindings)
    learned = tuple(
        runner.load_learned_two_route_checkpoint(
            Path(str(stage_a["root"])) / str(entry["path"]),
            arm=arm,
            expected_sha256=str(entry["sha256"]),
            training_provenance=provenance[arm],
        )
        for arm, entry in zip(common.LEARNED_ARMS, exports, strict=True)
    )
    base = runner.load_baseline_policy(
        checkpoint_path=baseline["checkpoint_path"],
        status_path=baseline["status_path"],
        expected_status_sha256=baseline["status_sha256"],
    )
    return (*learned, base)


def _adapter_and_plan(
    bindings: Mapping[str, object],
    runner: Any,
    *,
    policies: tuple[Any, ...],
    runtime_admission: Mapping[str, object],
) -> tuple[Any, Any]:
    from mcrl.env.tle import TleArchive
    physical = bindings["physical_inputs"]
    archive = TleArchive(Path(str(physical["tle_root"])))
    adapter = runner.FixedPolicyEpisodeAdapter(
        policies=policies,
        archive=archive,
        environment_factory=_make_environment,
        rng_factory=_rngs,
        runtime_admission=runtime_admission,
    )
    plan = runner.EvaluationPlan.from_file(bindings["world_plan"]["path"])
    return adapter, plan


def _admission_mapping(
    bindings: Mapping[str, object], adapter: Any
) -> dict[str, dict[str, object]]:
    return common.verified_stage_c_admission_mapping(
        bindings, adapter.policy_bindings
    )


def _formal_marker(
    output: Path,
    bindings_sha: str,
    plan_sha: str,
    admission_mapping: Mapping[str, object],
) -> None:
    marker = output / "FORMAL-RUN.json"
    payload = {
        "schema": "multi-catfish-mcrl-v023-c1c2-successor-stagec-formal-root-v1",
        "formal": True,
        "bindings_sha256": bindings_sha,
        "plan_sha256": plan_sha,
        "arms": list(common.ARMS),
        "admission_mapping_sha256": common.canonical_sha256(admission_mapping),
    }
    if marker.exists():
        if common.read_json(marker, field="formal root marker") != payload:
            raise common.StageCError("formal root marker drifted")
    else:
        common.write_once(marker, payload)


def _stage_a_receipt(bindings: Mapping[str, object]) -> dict[str, object]:
    stage_a = bindings.get("stage_a")
    if not isinstance(stage_a, Mapping):
        raise common.StageCError("Stage-A binding is missing")
    receipt = stage_a.get("pass_receipt")
    if not isinstance(receipt, Mapping):
        raise common.StageCError("Stage-A PASS receipt binding is missing")
    return {
        "path": str((Path(str(stage_a["root"])) / str(receipt["path"])).resolve()),
        "sha256": receipt["sha256"],
        "status": "PASS_SOURCE_TRAINING_INTEGRITY",
    }


def _stage_c_runtime_admission(
    *,
    bindings: Mapping[str, object],
    runner: Any,
    stage_b_root: Path,
    admission_root: Path,
) -> dict[str, object]:
    physical = bindings.get("physical_inputs")
    if not isinstance(physical, Mapping):
        raise common.StageCError("Stage-C physical inputs are malformed")
    from mcrl.env.tle import TleArchive

    archive = TleArchive(Path(str(physical["tle_root"])))
    environment = _make_environment(archive, 100)
    stage_b_gate = stage_b_root / "stage-b-gate.json"
    return common.ensure_runtime_admission(
        bindings=bindings,
        path=admission_root / "stage-c-runtime-admission.json",
        runner_schema=runner.SCHEMA,
        admitted_evaluation_sha256=common.PLAN_SHA256,
        predecessor_pass_receipts=(
            _stage_a_receipt(bindings),
            {
                "path": str(stage_b_gate.resolve()),
                "sha256": common.file_sha256(stage_b_gate, field="Stage-B PASS gate"),
                "status": "PASS_PLUMBING_INTEGRITY",
            },
        ),
        sampler_sha256=common.canonical_sha256(environment.sampler.as_dict()),
    )


def _formal_admission_payload(
    *,
    bindings: Mapping[str, object],
    bindings_sha: str,
    runtime_admission: Mapping[str, object],
    admission_mapping: Mapping[str, object],
    policy_bindings: Mapping[str, object],
    stage_ab_supplement_sha256: str,
    acceptance_evidence_sha256: str,
) -> dict[str, object]:
    inputs = {
        "prereg": runtime_admission["prereg"],
        "tle_manifest": runtime_admission["tle_manifest"],
        "execution_configuration": runtime_admission["execution_configuration"],
        "stage_a_pass_receipt": runtime_admission["predecessor_pass_receipts"][0],
        "stage_b_pass_receipt": runtime_admission["predecessor_pass_receipts"][1],
        "runtime_admission": {
            "path": runtime_admission["admission_path"],
            "sha256": runtime_admission["admission_sha256"],
        },
    }
    return {
        "schema": "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-formal-admission-v1",
        "status": "FORMAL_STAGE_C_ADMITTED",
        "formal": True,
        "integrity_status": "VERIFIED",
        "split": "TRAIN",
        "arms": list(common.ARMS),
        "plan_sha256": common.PLAN_SHA256,
        "bindings_sha256": bindings_sha,
        "policy_bindings_sha256": common.canonical_sha256(policy_bindings),
        "admission_mapping": admission_mapping,
        "admission_mapping_sha256": common.canonical_sha256(admission_mapping),
        "prereg_sha256": inputs["prereg"]["sha256"],
        "tle_manifest_sha256": inputs["tle_manifest"]["sha256"],
        "execution_configuration_sha256": inputs["execution_configuration"]["sha256"],
        "stage_a_pass_receipt_sha256": inputs["stage_a_pass_receipt"]["sha256"],
        "stage_b_pass_receipt_sha256": inputs["stage_b_pass_receipt"]["sha256"],
        "authenticated_inputs": inputs,
        "git": bindings["git"],
        "stage_ab_supplement_sha256": stage_ab_supplement_sha256,
        "acceptance_evidence_sha256": acceptance_evidence_sha256,
        "acceptance_procedure_sha256": bindings["acceptance_procedure"]["sha256"],
    }


def _publish_formal_admission(output: Path, payload: Mapping[str, object]) -> None:
    common.publish_sealed_json(
        output / common.FORMAL_ADMISSION_NAME, payload, field="formal Stage-C admission"
    )


def _continuation_banner(args: argparse.Namespace) -> str:
    if args.owner_notification_marker is None or args.continuation_authority is None:
        raise common.StageCError("9000 requires continuation authority and owner-notification marker")
    if not isinstance(args.controller_session_id, str) or not args.controller_session_id.strip():
        raise common.StageCError("9000 requires the controller session id")
    marker = common.read_json(args.owner_notification_marker, field="owner-notification marker")
    marker_sha = common.verify_named_sidecar(args.owner_notification_marker)
    reply = marker.get("owner_reply_verbatim")
    required = (
        "notification_sent_utc",
        "owner_reply_received_utc",
        "notification_channel",
        "recorded_by",
    )
    if (
        marker.get("formal") is not True
        or marker.get("status") != "OWNER_NOTIFIED_FOR_9000_CONTINUATION"
        or marker.get("recorded_by") != args.controller_session_id
        or marker.get("bindings_sha256") != common.file_sha256(args.bindings)
        or marker.get("plan_sha256") != common.PLAN_SHA256
        or marker.get("result_3000_sha256") != common.file_sha256(args.output / "result.json")
        or not isinstance(reply, str)
        or len(reply.strip()) < 20
        or any(not isinstance(marker.get(field), str) or not str(marker[field]).strip() for field in required)
    ):
        raise common.StageCError("owner notification marker is incomplete or disagrees")
    try:
        sent = datetime.fromisoformat(str(marker["notification_sent_utc"])[:-1] + "+00:00")
        received = datetime.fromisoformat(str(marker["owner_reply_received_utc"])[:-1] + "+00:00")
    except ValueError as error:
        raise common.StageCError("owner notification timestamps are not valid UTC") from error
    if (
        not str(marker["notification_sent_utc"]).endswith("Z")
        or not str(marker["owner_reply_received_utc"]).endswith("Z")
        or sent.tzinfo != timezone.utc
        or received.tzinfo != timezone.utc
        or received < sent
    ):
        raise common.StageCError("owner notification timestamps are not ordered UTC")
    authority = common.read_json(args.continuation_authority, field="continuation authority")
    common.verify_named_sidecar(args.continuation_authority)
    notification = authority.get("owner_notification")
    if (
        authority.get("bindings_sha256") != common.file_sha256(args.bindings)
        or authority.get("recorded_by") != args.controller_session_id
        or not isinstance(notification, Mapping)
        or notification.get("path") != str(args.owner_notification_marker.resolve())
        or notification.get("sha256") != marker_sha
    ):
        raise common.StageCError("continuation authority does not embed the owner marker")
    return reply


def run(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, bindings
    )
    acceptance = common.verify_acceptance_bundle(
        args.acceptance_bundle,
        {**bindings, "bindings_sha256": common.file_sha256(args.bindings)},
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings)
    bindings_sha = common.file_sha256(args.bindings)
    code_sha, _entries = common.verify_code_manifest()
    if bindings.get("code", {}).get("external_manifest_sha256") != code_sha:
        raise common.StageCError("Stage-C code closure drifted")
    physical = bindings.get("physical_inputs")
    if not isinstance(physical, Mapping):
        raise common.StageCError("Stage-C physical input bindings are malformed")
    tle_rows, tle_sha = common.tree_manifest(Path(str(physical.get("tle_root"))))
    if tle_rows != physical.get("tle_manifest") or tle_sha != physical.get("tle_manifest_sha256"):
        raise common.StageCError("Stage-C frozen TLE tree drifted")
    if str(args.output.resolve(strict=False)) != bindings.get("stage_c_output_root"):
        raise common.StageCError("Stage-C output root differs from frozen binding")
    _authenticate_preflight(
        args.preflight_receipt, bindings_sha,
        supplement_sha=supplement["supplement_sha256"],
        acceptance_sha=acceptance["acceptance_bundle_sha256"],
    )
    _authenticate_stage_b(args.stage_b_root, bindings_sha)
    runner = _module(common.PHYSICAL / "v023_c1c2_successor_physical_runner.py")
    admission_root = args.runtime_admission_root
    if admission_root is None:
        admission_root = args.output.with_name(f"{args.output.name}-admission")
    runtime_admission = _stage_c_runtime_admission(
        bindings=bindings,
        runner=runner,
        stage_b_root=args.stage_b_root,
        admission_root=admission_root,
    )
    policies = _policies(bindings, runner)
    adapter, plan = _adapter_and_plan(
        bindings, runner, policies=policies, runtime_admission=runtime_admission
    )
    admission_mapping = _admission_mapping(bindings, adapter)
    if (args.output / common.COMPLETE_NAME).exists() or (args.output / common.TREE_MANIFEST_NAME).exists():
        raise common.StageCError("sealed Stage-C result root cannot be resumed")
    if args.pause_at == 9000:
        if args.continuation_authority is None or args.owner_notification_marker is None:
            raise common.StageCError("9000 requires continuation authority and owner-notification marker")
        if args.resume_checkpoint is None:
            raise common.StageCError("9000 continuation requires checkpoint 3000")
        evaluation = runner.FixedPolicyEvaluationRunner(
            adapter=adapter, plan=plan, terminal_boundary=9000,
            continuation_authority_path=args.continuation_authority,
            continuation_authority_sha256=common.file_sha256(args.continuation_authority),
            repair_authority_path=args.repair_authority,
            repair_authority_sha256=(
                None if args.repair_authority is None else common.file_sha256(args.repair_authority)
            ),
            admission_mapping=admission_mapping,
        )
    else:
        previous = {100: None, 500: 100, 1500: 500, 3000: 1500}[args.pause_at]
        if previous is None:
            if args.resume_checkpoint is not None or args.output.exists() or args.output.is_symlink():
                raise common.StageCError("the 100 rung requires a fresh absent output root")
        else:
            expected = args.output / "checkpoints" / f"checkpoint-{previous:06d}.json"
            if args.resume_checkpoint is None or args.resume_checkpoint.resolve() != expected.resolve():
                raise common.StageCError(f"rung {args.pause_at} must resume the cumulative {previous} checkpoint")
        evaluation = runner.FixedPolicyEvaluationRunner(
            adapter=adapter,
            plan=plan,
            terminal_boundary=3000,
            repair_authority_path=args.repair_authority,
            repair_authority_sha256=(
                None if args.repair_authority is None else common.file_sha256(args.repair_authority)
            ),
            admission_mapping=admission_mapping,
        )
    summary = evaluation.run(output_dir=args.output, pause_at=args.pause_at, resume_checkpoint=args.resume_checkpoint)
    _formal_marker(args.output, bindings_sha, plan.plan_sha256, admission_mapping)
    _publish_formal_admission(
        args.output,
        _formal_admission_payload(
            bindings=bindings,
            bindings_sha=bindings_sha,
            runtime_admission=runtime_admission,
            admission_mapping=admission_mapping,
            policy_bindings=adapter.policy_bindings,
            stage_ab_supplement_sha256=supplement["supplement_sha256"],
            acceptance_evidence_sha256=acceptance["acceptance_bundle_sha256"],
        ),
    )
    if (
        args.pause_at == 9000
        or (args.pause_at == 3000 and summary.get("overall_token") == runner.FALSIFIED)
    ):
        common.write_tree_seal(args.output)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--preflight-receipt", type=Path, required=True)
    parser.add_argument("--admission-supplement", type=Path, required=True)
    parser.add_argument("--acceptance-bundle", type=Path, required=True)
    parser.add_argument("--stage-b-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pause-at", type=int, choices=(*common.PAUSES, 9000), required=True)
    parser.add_argument("--resume-checkpoint", type=Path)
    parser.add_argument("--continuation-authority", type=Path)
    parser.add_argument("--owner-notification-marker", type=Path)
    parser.add_argument("--controller-session-id")
    parser.add_argument("--repair-authority", type=Path)
    parser.add_argument("--runtime-admission-root", type=Path)
    parser.add_argument("--startup-marker", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    started = time.monotonic()
    try:
        if args.pause_at == 9000:
            reply = _continuation_banner(args)
            print("=" * 72)
            print("OWNER REPLY QUOTED BEFORE 9000 CONTINUATION:")
            print(reply)
            print("=" * 72)
        if args.startup_marker is not None:
            common.write_once(
                args.startup_marker,
                {
                    "schema": "multi-catfish-mcrl-v023-c1c2-successor-stagec-startup-v1",
                    "status": "CONTROLLER_STARTED",
                    "formal": True,
                    "pid": os.getpid(),
                    "pause_at": args.pause_at,
                    "bindings_sha256": common.file_sha256(args.bindings),
                },
            )
        result = run(args)
    except Exception as error:
        print(f"STOP_PHYSICAL_EVALUATION_INTEGRITY: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    print(f"STAGEC_PAUSE_COMPLETE pause={args.pause_at} output={args.output} wall_time_s={time.monotonic()-started:.6f}")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
