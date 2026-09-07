#!/usr/bin/env python3
"""Server controller for cumulative formal Stage-C pauses and continuation."""

from __future__ import annotations

import argparse
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


def _authenticate_preflight(path: Path, bindings_sha: str) -> None:
    receipt = common.read_json(path, field="Stage-C preflight receipt")
    common.verify_named_sidecar(path)
    if (
        receipt.get("status") != "PASS_V023_C1C2_SUCCESSOR_STAGEC_PREFLIGHT"
        or receipt.get("formal") is not True
        or receipt.get("bindings_sha256") != bindings_sha
        or receipt.get("arms") != list(common.ARMS)
    ):
        raise common.StageCError("Stage-C preflight receipt drifted")


def _authenticate_stage_b(root: Path, bindings_sha: str) -> None:
    gate_path = root / "stage-b-gate.json"
    gate = common.read_json(gate_path, field="Stage-B gate")
    common.verify_named_sidecar(gate_path)
    receipt = root / "plumbing-receipt.json"
    if (
        gate.get("status") != "PASS_PLUMBING_INTEGRITY"
        or gate.get("formal") is not True
        or gate.get("bindings_sha256") != bindings_sha
        or gate.get("plumbing_receipt_sha256") != common.file_sha256(receipt)
        or gate.get("arms") != list(common.ARMS)
    ):
        raise common.StageCError("mandatory Stage-B plumbing gate drifted")


def _policies(bindings: Mapping[str, object], runner: Any) -> tuple[Any, ...]:
    stage_a = bindings["stage_a"]
    baseline = bindings["baseline"]
    exports = stage_a["exports"]
    learned = tuple(
        runner.load_learned_two_route_checkpoint(
            Path(str(stage_a["root"])) / str(entry["path"]),
            arm=arm,
            expected_sha256=str(entry["sha256"]),
        )
        for arm, entry in zip(common.LEARNED_ARMS, exports, strict=True)
    )
    base = runner.load_baseline_policy(
        checkpoint_path=baseline["checkpoint_path"],
        status_path=baseline["status_path"],
        expected_status_sha256=baseline["status_sha256"],
    )
    return (*learned, base)


def _adapter_and_plan(bindings: Mapping[str, object], runner: Any) -> tuple[Any, Any]:
    from mcrl.env.tle import TleArchive
    physical = bindings["physical_inputs"]
    archive = TleArchive(Path(str(physical["tle_root"])))
    policies = _policies(bindings, runner)
    adapter = runner.FixedPolicyEpisodeAdapter(
        policies=policies,
        archive=archive,
        environment_factory=_make_environment,
        rng_factory=_rngs,
    )
    plan = runner.EvaluationPlan.from_file(bindings["world_plan"]["path"])
    return adapter, plan


def _formal_marker(output: Path, bindings_sha: str, plan_sha: str) -> None:
    marker = output / "FORMAL-RUN.json"
    payload = {
        "schema": "multi-catfish-mcrl-v023-c1c2-successor-stagec-formal-root-v1",
        "formal": True,
        "bindings_sha256": bindings_sha,
        "plan_sha256": plan_sha,
        "arms": list(common.ARMS),
    }
    if marker.exists():
        if common.read_json(marker, field="formal root marker") != payload:
            raise common.StageCError("formal root marker drifted")
    else:
        common.write_once(marker, payload)


def _continuation(
    *, runner: Any, evaluation: Any, output: Path, checkpoint: Path,
    authority: Path, owner_marker: Path, bindings_sha: str,
) -> dict[str, object]:
    result = common.read_json(output / "result.json", field="3000 scientific result")
    if result.get("overall_token") != runner.HELD or result.get("completed_episode") != 3000:
        raise common.StageCError("9000 continuation requires the held 3000 result")
    authority_sha = common.file_sha256(authority, field="continuation authority")
    owner = common.read_json(owner_marker, field="owner-notification marker")
    if (
        owner.get("formal") is not True
        or owner.get("status") != "OWNER_NOTIFIED_FOR_9000_CONTINUATION"
        or owner.get("authority_sha256") != authority_sha
        or owner.get("bindings_sha256") != bindings_sha
        or owner.get("plan_sha256") != common.PLAN_SHA256
    ):
        raise common.StageCError("owner-notification marker is absent or disagrees")
    authority_marker = output / "CONTINUATION-AUTHORITY.json"
    authority_binding = {
        "schema": "multi-catfish-mcrl-v023-c1c2-successor-stagec-continuation-authority-binding-v1",
        "formal": True,
        "continuation_authority_sha256": authority_sha,
        "owner_notification_sha256": common.file_sha256(owner_marker),
        "bindings_sha256": bindings_sha,
        "plan_sha256": common.PLAN_SHA256,
    }
    if authority_marker.exists():
        if common.read_json(authority_marker, field="continuation authority binding") != authority_binding:
            raise common.StageCError("continuation authority binding drifted on resume")
    else:
        common.write_once(authority_marker, authority_binding)
    start, receipts = evaluation._validate_resume(runner._read_checkpoint(checkpoint))
    if start < 3000 or start >= 9000 or start % 100:
        raise common.StageCError("9000 continuation must resume a 100-cadence checkpoint from 3000 onward")
    if (output / "continuation-009000.json").exists():
        raise common.StageCError("9000 continuation is already complete")
    existing = sorted((output / "checkpoints").glob("checkpoint-*.json"))
    expected = [f"checkpoint-{index:06d}.json" for index in range(100, start + 1, 100)]
    if [path.name for path in existing] != expected:
        raise common.StageCError("pre-continuation checkpoint history drifted")
    for index in range(start, 9000):
        world = evaluation.plan.worlds[index]
        rows = []
        for arm in common.ARMS:
            row = evaluation.adapter.run_episode(
                arm=arm, world=world, plan_sha256=evaluation.plan.plan_sha256,
                resume_state=evaluation.adapter.resume_state_for(arm),
            )
            rows.append(row)
            receipts.append(row)
        runner._verify_matched_episode(rows, world)
        completed = index + 1
        if completed % 100 == 0:
            runner._write_once(output / "checkpoints" / f"checkpoint-{completed:06d}.json", evaluation._checkpoint_payload(completed, receipts))
            runner._write_once(output / "rungs" / f"rung-{completed:06d}.json", evaluation._rung_payload(completed, receipts))
    pooled = {arm: runner.pool_receipts([row for row in receipts if row.arm == arm], arm=arm) for arm in common.ARMS}
    continuation = {
        "schema": "multi-catfish-mcrl-v023-c1c2-successor-stagec-continuation-v1",
        "status": "COMPLETED_AUTHORIZED_9000_CONTINUATION",
        "formal": True,
        "completed_episode": 9000,
        "plan_sha256": common.PLAN_SHA256,
        "arms": list(common.ARMS),
        "pooled_by_arm": pooled,
        "continuation_authority_sha256": authority_sha,
        "owner_notification_sha256": common.file_sha256(owner_marker),
        "continuation_authority_binding_sha256": common.file_sha256(authority_marker),
        "scientific_result_remains": result["overall_token"],
        "new_scientific_token_emitted": False,
    }
    common.write_once(output / "continuation-009000.json", continuation)
    return continuation


def run(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
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
    _authenticate_preflight(args.preflight_receipt, bindings_sha)
    _authenticate_stage_b(args.stage_b_root, bindings_sha)
    runner = _module(common.PHYSICAL / "v023_c1c2_successor_physical_runner.py")
    adapter, plan = _adapter_and_plan(bindings, runner)
    if args.pause_at == 9000:
        if args.continuation_authority is None or args.owner_notification_marker is None:
            raise common.StageCError("9000 requires continuation authority and owner-notification marker")
        if args.resume_checkpoint is None:
            raise common.StageCError("9000 continuation requires checkpoint 3000")
        evaluation = runner.FixedPolicyEvaluationRunner(
            adapter=adapter, plan=plan, terminal_boundary=9000,
            continuation_authority_sha256=common.file_sha256(args.continuation_authority),
        )
        return _continuation(
            runner=runner, evaluation=evaluation, output=args.output,
            checkpoint=args.resume_checkpoint, authority=args.continuation_authority,
            owner_marker=args.owner_notification_marker, bindings_sha=bindings_sha,
        )
    previous = {100: None, 500: 100, 1500: 500, 3000: 1500}[args.pause_at]
    if previous is None:
        if args.resume_checkpoint is not None or args.output.exists() or args.output.is_symlink():
            raise common.StageCError("the 100 rung requires a fresh absent output root")
    else:
        expected = args.output / "checkpoints" / f"checkpoint-{previous:06d}.json"
        if args.resume_checkpoint is None or args.resume_checkpoint.resolve() != expected.resolve():
            raise common.StageCError(f"rung {args.pause_at} must resume the cumulative {previous} checkpoint")
    evaluation = runner.FixedPolicyEvaluationRunner(adapter=adapter, plan=plan, terminal_boundary=3000)
    summary = evaluation.run(output_dir=args.output, pause_at=args.pause_at, resume_checkpoint=args.resume_checkpoint)
    _formal_marker(args.output, bindings_sha, plan.plan_sha256)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--preflight-receipt", type=Path, required=True)
    parser.add_argument("--stage-b-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pause-at", type=int, choices=(*common.PAUSES, 9000), required=True)
    parser.add_argument("--resume-checkpoint", type=Path)
    parser.add_argument("--continuation-authority", type=Path)
    parser.add_argument("--owner-notification-marker", type=Path)
    parser.add_argument("--startup-marker", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    started = time.monotonic()
    try:
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
