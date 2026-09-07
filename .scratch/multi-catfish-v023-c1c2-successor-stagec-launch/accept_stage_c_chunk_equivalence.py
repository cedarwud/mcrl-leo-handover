#!/usr/bin/env python3
"""Mandatory server acceptance: direct sequential 200 versus two 100 chunks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import run_v023_c1c2_successor_stage_c as sequential_controller
import run_v023_c1c2_successor_stage_c_chunks as chunk_controller
import stagec_common as common


PROVENANCE_ONLY_FIELDS = (
    "schema",
    "status",
    "chunk_id",
    "range",
    "start_boundary",
    "end_boundary",
    "start_boundary_state_sha256",
    "end_boundary_state_sha256",
    "threads",
    "runtime",
    "parent_checkpoint",
    "ordered_episode_records",
    "ordered_episode_record_digest",
    "started_utc",
    "ended_utc",
    "execution_mode",
)


def accept(args: argparse.Namespace) -> dict[str, object]:
    if os.environ.get("OMP_NUM_THREADS") != "1":
        raise common.StageCError("equivalence acceptance requires OMP_NUM_THREADS=1")
    if args.output.exists() or args.output.is_symlink():
        raise common.StageCError("acceptance output root must be absent")
    bindings = common.verify_bindings(args.bindings)
    common.verify_runtime_identity(bindings, chunk_mode=True)
    runner = chunk_controller._runner()
    policy = chunk_controller._policy(bindings, runner, args.arm)
    if args.arm == "BASELINE":
        if args.early_baseline_admission is None:
            raise common.StageCError("BASELINE acceptance requires early admission")
        admission = runner.authenticate_early_baseline_admission(
            args.early_baseline_admission,
            expected_sha256=common.verify_named_sidecar(args.early_baseline_admission),
            plan_sha256=common.PLAN_SHA256,
            policy_binding=policy.binding(),
        )
    else:
        if args.runtime_admission is None:
            raise common.StageCError("learned-arm acceptance requires runtime admission")
        admission = runner.authenticate_runtime_admission(
            args.runtime_admission,
            expected_sha256=common.verify_named_sidecar(args.runtime_admission),
            expected_statuses=("PASS_SOURCE_TRAINING_INTEGRITY", "PASS_PLUMBING_INTEGRITY"),
        )
    from mcrl.env.tle import TleArchive

    archive = TleArchive(Path(str(bindings["physical_inputs"]["tle_root"])))

    def adapter():
        return runner.FixedPolicyEpisodeAdapter(
            policies=(policy,), archive=archive,
            environment_factory=sequential_controller._make_environment,
            rng_factory=sequential_controller._rngs,
            runtime_admission=admission,
        )

    plan = runner.EvaluationPlan.from_file(bindings["world_plan"]["path"])
    sequential_adapter = adapter()
    sequential_rows = []
    sequential_states = {}
    state = None
    for episode in range(1, 201):
        row = sequential_adapter.run_episode(
            arm=args.arm, world=plan.worlds[episode - 1],
            plan_sha256=plan.plan_sha256, resume_state=state,
        )
        sequential_rows.append(row)
        state = sequential_adapter.resume_state_for(args.arm)
        if episode in {100, 200}:
            sequential_states[episode] = state
    chunk_adapter = adapter()
    physical = bindings["physical_inputs"]
    context = {
        "arm": args.arm,
        "adapter": chunk_adapter,
        "schedule_sha256": bindings["scheduling_addendum"]["sha256"],
        "execution_mode": "arm_decoupled",
        "continuation_limit": 3000,
        "provenance": {
            "authority_sha256": common.file_sha256(args.bindings),
            "code_manifest_sha256": bindings["code"]["external_manifest_sha256"],
            "configuration_sha256": common.canonical_sha256(bindings["execution"]),
            "tle_sha256": physical["tle_manifest_sha256"],
            "prereg_sha256": physical["prereg_sha256"],
            "admission_sha256": admission["admission_sha256"],
        },
    }
    table = runner.build_chunk_boundary_states(plan, context, (0, 100, 200))
    args.output.mkdir(parents=True, exist_ok=False)
    first = args.output / "chunks" / f"{args.arm}-000000-000100"
    second = args.output / "chunks" / f"{args.arm}-000100-000200"
    runner.run_arm_chunk(args.arm, 0, 100, table[0], first)
    runner.run_arm_chunk(args.arm, 100, 200, table[100], second)
    chunk_rows = []
    for root, start, end in ((first, 0, 100), (second, 100, 200)):
        for episode in range(start + 1, end + 1):
            row, _state = runner._read_episode_record(
                root / "episodes" / f"episode-{episode:06d}.json"
            )
            chunk_rows.append(row)
    if runner._canonical_bytes([row.as_dict() for row in sequential_rows]) != runner._canonical_bytes(
        [row.as_dict() for row in chunk_rows]
    ):
        raise common.StageCError("episode values are not bitwise identical")
    for boundary in (100, 200):
        if sequential_states[boundary] != table[boundary]["resume_state"]:
            raise common.StageCError(f"boundary state differs at {boundary}")
        direct_pool = runner.pool_receipts(sequential_rows[:boundary], arm=args.arm)
        chunk_pool = runner.pool_receipts(chunk_rows[:boundary], arm=args.arm)
        if runner._canonical_bytes(direct_pool) != runner._canonical_bytes(chunk_pool):
            raise common.StageCError(f"pool/rung values differ at {boundary}")
    result = {
        "schema": f"{runner.SCHEMA}-server-chunk-equivalence-v1",
        "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
        "arm": args.arm,
        "episodes": 200,
        "chunks": [[1, 100], [101, 200]],
        "plan_sha256": plan.plan_sha256,
        "schedule_sha256": bindings["scheduling_addendum"]["sha256"],
        "episode_digest": runner.canonical_sha256([row.as_dict() for row in chunk_rows]),
        "boundary_state_hashes": {
            str(boundary): table[boundary]["boundary_state_sha256"] for boundary in (0, 100, 200)
        },
        "receipt_comparison_excluded_provenance_fields": list(PROVENANCE_ONLY_FIELDS),
        "execution_mode": "arm_decoupled",
    }
    common.write_once(args.output / "ACCEPTANCE.json", result)
    common.write_digest_sidecar(args.output / "ACCEPTANCE.json")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--arm", choices=common.ARMS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--early-baseline-admission", type=Path)
    parser.add_argument("--runtime-admission", type=Path)
    args = parser.parse_args(argv)
    try:
        result = accept(args)
    except Exception as error:
        print(f"STOP_PHYSICAL_EVALUATION_INTEGRITY: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
