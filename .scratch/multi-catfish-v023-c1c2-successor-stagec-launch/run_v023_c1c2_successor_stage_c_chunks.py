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


def run_chunk(args: argparse.Namespace) -> dict[str, object]:
    if os.environ.get("OMP_NUM_THREADS") != "1":
        raise common.StageCError("chunk controller requires OMP_NUM_THREADS=1")
    bindings = common.verify_bindings(args.bindings)
    common.verify_runtime_identity(bindings, chunk_mode=True)
    runner = _runner()
    policy = _policy(bindings, runner, args.arm)
    if args.arm == "BASELINE":
        if args.early_baseline_admission is None:
            raise common.StageCError("early BASELINE requires sealed admission")
        admission_sha = common.verify_named_sidecar(args.early_baseline_admission)
        admission = runner.authenticate_early_baseline_admission(
            args.early_baseline_admission,
            expected_sha256=admission_sha,
            plan_sha256=common.PLAN_SHA256,
            policy_binding=policy.binding(),
        )
    else:
        if args.runtime_admission is None:
            raise common.StageCError("learned arm chunks require Stage-A/B runtime admission")
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
        "continuation_limit": 3000,
        "parent_checkpoint": args.parent_checkpoint,
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
        },
    }
    boundaries = tuple(range(0, 3001, 100))
    table = runner.build_chunk_boundary_states(plan, context, boundaries)
    return runner.run_arm_chunk(
        args.arm, args.start, args.end, table[args.start], args.chunk_root
    )


def merge_arm(args: argparse.Namespace) -> dict[str, object]:
    return _runner().merge_arm_chunks(args.arm, args.chunk_roots, args.output)


def merge_four(args: argparse.Namespace) -> dict[str, object]:
    bindings = common.verify_bindings(args.bindings)
    roots = {arm: root for arm, root in zip(common.ARMS, args.arm_roots, strict=True)}
    mappings = common.read_json(args.admission_mapping, field="four-arm admission mapping")
    mapping = common.verify_stage_c_admission_mapping(mappings.get("admission_mapping"))
    result = _runner().merge_four_arm(roots, args.output, admission_mapping=mapping)
    policy_bindings = {
        arm: mapping[arm]["policy_binding"] for arm in common.ARMS
    }
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
    if result.get("overall_token") == _runner().FALSIFIED:
        common.write_tree_seal(args.output)
    result["bindings_sha256"] = common.file_sha256(args.bindings)
    result["policy_bindings_sha256"] = common.canonical_sha256(policy_bindings)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    chunk = sub.add_parser("run-chunk")
    chunk.add_argument("--bindings", type=Path, required=True)
    chunk.add_argument("--arm", choices=common.ARMS, required=True)
    chunk.add_argument("--start", type=int, required=True)
    chunk.add_argument("--end", type=int, required=True)
    chunk.add_argument("--chunk-root", type=Path, required=True)
    chunk.add_argument("--early-baseline-admission", type=Path)
    chunk.add_argument("--runtime-admission", type=Path)
    chunk.add_argument("--parent-checkpoint")
    chunk.add_argument("--repair-authority", type=Path)
    arm = sub.add_parser("merge-arm")
    arm.add_argument("--arm", choices=common.ARMS, required=True)
    arm.add_argument("--chunk-roots", type=Path, nargs="+", required=True)
    arm.add_argument("--output", type=Path, required=True)
    four = sub.add_parser("merge-four")
    four.add_argument("--bindings", type=Path, required=True)
    four.add_argument("--arm-roots", type=Path, nargs=4, required=True)
    four.add_argument("--admission-mapping", type=Path, required=True)
    four.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run-chunk":
            result = run_chunk(args)
        elif args.command == "merge-arm":
            result = merge_arm(args)
        else:
            result = merge_four(args)
    except Exception as error:
        print(f"STOP_PHYSICAL_EVALUATION_INTEGRITY: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
