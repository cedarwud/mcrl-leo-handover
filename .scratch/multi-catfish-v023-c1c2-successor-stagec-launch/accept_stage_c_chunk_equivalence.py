#!/usr/bin/env python3
"""Mandatory server acceptance: direct sequential versus chunked execution."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
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


def _without_provenance(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _without_provenance(child)
            for key, child in value.items()
            if key not in PROVENANCE_ONLY_FIELDS
        }
    if isinstance(value, list):
        return [_without_provenance(child) for child in value]
    return value


def _bitwise_equal(left: object, right: object) -> bool:
    if isinstance(left, float) or isinstance(right, float):
        return isinstance(left, float) and isinstance(right, float) and struct.pack(">d", left) == struct.pack(">d", right)
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict) and isinstance(right, dict)
            and set(left) == set(right)
            and all(_bitwise_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, list) or isinstance(right, list):
        return isinstance(left, list) and isinstance(right, list) and len(left) == len(right) and all(
            _bitwise_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right and type(left) is type(right)


def accept(args: argparse.Namespace) -> dict[str, object]:
    for name in common.NUMERICAL_THREAD_ENV:
        if os.environ.get(name) != "1":
            raise common.StageCError(f"equivalence acceptance requires {name}=1")
    if args.output.exists() or args.output.is_symlink():
        raise common.StageCError("acceptance output root must be absent")
    bindings = common.verify_bindings(args.bindings)
    supplement = common.verify_stage_ab_supplement(
        args.admission_supplement, args.bindings, bindings
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings, chunk_mode=True)
    runner = chunk_controller._runner()
    policy = chunk_controller._policy(bindings, runner, args.arm)
    admission = runner.authenticate_runtime_admission(
        args.runtime_admission,
        expected_sha256=common.verify_named_sidecar(args.runtime_admission),
        expected_statuses=("PASS_SOURCE_TRAINING_INTEGRITY", "PASS_PLUMBING_INTEGRITY"),
    )
    if args.episodes < 1 or args.chunks < 1 or args.episodes % args.chunks:
        raise common.StageCError("acceptance episodes must divide evenly into positive chunks")
    chunk_size = args.episodes // args.chunks
    if chunk_size % 100 and not (
        args.non_formal and args.episodes == 100 and args.chunks == 2 and chunk_size == 50
    ):
        raise common.StageCError("non-100-aligned chunks require explicit 100/2 non-formal rehearsal")
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
    boundaries = tuple(range(chunk_size, args.episodes + 1, chunk_size))
    for episode in range(1, args.episodes + 1):
        row = sequential_adapter.run_episode(
            arm=args.arm, world=plan.worlds[episode - 1],
            plan_sha256=plan.plan_sha256, resume_state=state,
        )
        sequential_rows.append(row)
        state = sequential_adapter.resume_state_for(args.arm)
        if episode in set(boundaries):
            sequential_states[episode] = state
    chunk_adapter = adapter()
    physical = bindings["physical_inputs"]
    context = {
        "arm": args.arm,
        "adapter": chunk_adapter,
        "schedule_sha256": bindings["scheduling_addendum"]["sha256"],
        "execution_mode": "arm_decoupled",
        "formal": False,
        "acceptance_mode": "NONFORMAL_EQUIVALENCE_REHEARSAL",
        "chunk_alignment": chunk_size,
        "continuation_limit": 3000,
        "provenance": {
            "authority_sha256": common.file_sha256(args.bindings),
            "code_manifest_sha256": bindings["code"]["external_manifest_sha256"],
            "configuration_sha256": common.canonical_sha256(bindings["execution"]),
            "tle_sha256": physical["tle_manifest_sha256"],
            "prereg_sha256": physical["prereg_sha256"],
            "admission_sha256": admission["admission_sha256"],
            "stage_ab_supplement_sha256": supplement["supplement_sha256"],
            "acceptance_evidence_sha256": common.canonical_sha256({"pending": args.arm}),
            "acceptance_procedure_sha256": bindings["acceptance_procedure"]["sha256"],
        },
    }
    table_boundaries = (0, *boundaries)
    table = runner.build_chunk_boundary_states(plan, context, table_boundaries)
    args.output.mkdir(parents=True, exist_ok=False)
    roots = []
    start = 0
    for end in boundaries:
        root = args.output / "chunks" / f"{args.arm}-{start:06d}-{end:06d}"
        runner.run_arm_chunk(args.arm, start, end, table[start], root)
        roots.append(root)
        start = end
    chunk_rows = []
    for root, start, end in zip(roots, (0, *boundaries[:-1]), boundaries, strict=True):
        for episode in range(start + 1, end + 1):
            row, _state = runner._read_episode_record(
                root / "episodes" / f"episode-{episode:06d}.json"
            )
            chunk_rows.append(row)
    if not _bitwise_equal(
        [row.as_dict() for row in sequential_rows], [row.as_dict() for row in chunk_rows]
    ):
        raise common.StageCError("episode values are not bitwise identical")
    for boundary in boundaries:
        if sequential_states[boundary] != table[boundary]["resume_state"]:
            raise common.StageCError(f"boundary state differs at {boundary}")
        direct_pool = runner.pool_receipts(sequential_rows[:boundary], arm=args.arm)
        chunk_pool = runner.pool_receipts(chunk_rows[:boundary], arm=args.arm)
        if not _bitwise_equal(direct_pool, chunk_pool):
            raise common.StageCError(f"pool/rung values differ at {boundary}")
    merged_root = args.output / "merged"
    runner.merge_arm_chunks(args.arm, roots, merged_root, formal_required=False)
    for boundary in boundaries:
        merged_checkpoint = common.read_json(
            merged_root / "checkpoints" / f"checkpoint-{boundary:06d}.json",
            field=f"merged acceptance checkpoint {boundary}",
        )
        merged_rung = common.read_json(
            merged_root / "rungs" / f"rung-{boundary:06d}.json",
            field=f"merged acceptance rung {boundary}",
        )
        expected_pool = runner.pool_receipts(sequential_rows[:boundary], arm=args.arm)
        expected_checkpoint = {
            "arm": args.arm,
            "completed_episode": boundary,
            "plan_sha256": plan.plan_sha256,
            "receipts": [row.as_dict() for row in sequential_rows[:boundary]],
            "pooled": expected_pool,
            "resume_state": sequential_states[boundary],
        }
        expected_rung = {
            "arm": args.arm,
            "completed_episode": boundary,
            "plan_sha256": plan.plan_sha256,
            "pooled": expected_pool,
        }
        for key, value in expected_checkpoint.items():
            if not _bitwise_equal(_without_provenance(merged_checkpoint.get(key)), value):
                raise common.StageCError(f"merged checkpoint differs from sequential reference at {boundary}: {key}")
        for key, value in expected_rung.items():
            if not _bitwise_equal(_without_provenance(merged_rung.get(key)), value):
                raise common.StageCError(f"merged rung differs from sequential reference at {boundary}: {key}")
    result = {
        "schema": f"{runner.SCHEMA}-server-chunk-equivalence-v1",
        "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
        "formal": False,
        "arm": args.arm,
        "episodes": args.episodes,
        "chunks": [[start + 1, end] for start, end in zip((0, *boundaries[:-1]), boundaries, strict=True)],
        "plan_sha256": plan.plan_sha256,
        "schedule_sha256": bindings["scheduling_addendum"]["sha256"],
        "episode_digest": runner.canonical_sha256([row.as_dict() for row in chunk_rows]),
        "boundary_state_hashes": {
            str(boundary): table[boundary]["boundary_state_sha256"] for boundary in table_boundaries
        },
        "receipt_comparison_excluded_provenance_fields": list(PROVENANCE_ONLY_FIELDS),
        "execution_mode": "arm_decoupled",
        "code_manifest_sha256": bindings["code"]["external_manifest_sha256"],
        "configuration_sha256": common.canonical_sha256(bindings["execution"]),
        "acceptance_procedure_sha256": bindings["acceptance_procedure"]["sha256"],
        "stage_ab_supplement_sha256": supplement["supplement_sha256"],
        "bindings_sha256": common.file_sha256(args.bindings),
        "merged_artifacts_compared": ["receipts", "checkpoints", "rungs", "resume_states"],
    }
    common.write_once(args.output / "ACCEPTANCE.json", result)
    common.write_digest_sidecar(args.output / "ACCEPTANCE.json")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--arm", choices=common.ARMS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-admission", type=Path, required=True)
    parser.add_argument("--admission-supplement", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--chunks", type=int, default=2)
    parser.add_argument("--non-formal", action="store_true")
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
