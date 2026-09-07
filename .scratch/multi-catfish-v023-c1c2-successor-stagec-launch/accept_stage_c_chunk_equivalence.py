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


def _without_provenance(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _without_provenance(child)
            for key, child in value.items()
            if key not in common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS
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


def _first_bitwise_difference(left: object, right: object, path: str) -> str | None:
    if isinstance(left, float) or isinstance(right, float):
        return None if _bitwise_equal(left, right) else path
    if isinstance(left, dict) or isinstance(right, dict):
        if not isinstance(left, dict) or not isinstance(right, dict):
            return path
        for key in sorted(set(left) | set(right)):
            child_path = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                return child_path
            difference = _first_bitwise_difference(left[key], right[key], child_path)
            if difference is not None:
                return difference
        return None
    if isinstance(left, list) or isinstance(right, list):
        if not isinstance(left, list) or not isinstance(right, list):
            return path
        if len(left) != len(right):
            return f"{path}.length"
        for index, (left_child, right_child) in enumerate(zip(left, right, strict=True)):
            difference = _first_bitwise_difference(
                left_child, right_child, f"{path}[{index}]"
            )
            if difference is not None:
                return difference
        return None
    return None if left == right and type(left) is type(right) else path


def _assert_equivalent(left: object, right: object, *, artifact: str) -> None:
    difference = _first_bitwise_difference(
        _without_provenance(left), _without_provenance(right), artifact
    )
    if difference is not None:
        raise common.StageCError(f"bitwise chunk equivalence differs first at {difference}")


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
    formal = not args.non_formal
    if args.non_formal and not (
        args.episodes == 100 and args.chunks == 2 and chunk_size == 50
    ):
        raise common.StageCError("non-100-aligned chunks require explicit 100/2 non-formal rehearsal")
    if formal and (args.episodes != 200 or args.chunks != 2 or chunk_size != 100):
        raise common.StageCError("formal acceptance requires exactly 200 episodes in 2x100 chunks")
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
        "formal": formal,
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
    if not formal:
        context.update({
            "acceptance_mode": "NONFORMAL_EQUIVALENCE_REHEARSAL",
            "chunk_alignment": chunk_size,
        })
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
    _assert_equivalent(
        [row.as_dict() for row in sequential_rows],
        [row.as_dict() for row in chunk_rows],
        artifact="receipts.chunk_outputs",
    )
    for boundary in boundaries:
        _assert_equivalent(
            sequential_states[boundary], table[boundary]["resume_state"],
            artifact=f"resume_states.boundary_table[{boundary}]",
        )
        direct_pool = runner.pool_receipts(sequential_rows[:boundary], arm=args.arm)
        chunk_pool = runner.pool_receipts(chunk_rows[:boundary], arm=args.arm)
        _assert_equivalent(
            direct_pool, chunk_pool, artifact=f"rungs.chunk_pool[{boundary}]"
        )
    merged_root = args.output / "merged"
    runner.merge_arm_chunks(args.arm, roots, merged_root, formal_required=formal)
    merged_rows = [
        common.read_json(
            merged_root / "episodes" / f"episode-{episode:06d}.json",
            field=f"merged acceptance receipt {episode}",
        )
        for episode in range(1, args.episodes + 1)
    ]
    _assert_equivalent(
        [row.as_dict() for row in sequential_rows], merged_rows,
        artifact="receipts.merged",
    )
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
        merged_resume_state = common.read_json(
            merged_root / "resume-states" / f"state-{boundary:06d}.json",
            field=f"merged acceptance resume state {boundary}",
        )
        _assert_equivalent(
            merged_resume_state, sequential_states[boundary],
            artifact=f"resume_states.merged[{boundary}]",
        )
        for key, value in expected_checkpoint.items():
            _assert_equivalent(
                merged_checkpoint.get(key), value,
                artifact=f"checkpoints[{boundary}].{key}",
            )
        for key, value in expected_rung.items():
            _assert_equivalent(
                merged_rung.get(key), value,
                artifact=f"rungs[{boundary}].{key}",
            )
    result = {
        "schema": f"{runner.SCHEMA}-server-chunk-equivalence-v1",
        "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
        "formal": formal,
        "rehearsal_chunk": None if formal else 50,
        "arm": args.arm,
        "episodes": args.episodes,
        "chunks": [[start + 1, end] for start, end in zip((0, *boundaries[:-1]), boundaries, strict=True)],
        "plan_sha256": plan.plan_sha256,
        "schedule_sha256": bindings["scheduling_addendum"]["sha256"],
        "episode_digest": runner.canonical_sha256([row.as_dict() for row in chunk_rows]),
        "boundary_state_hashes": {
            str(boundary): table[boundary]["boundary_state_sha256"] for boundary in table_boundaries
        },
        "receipt_comparison_excluded_provenance_fields": list(
            common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS
        ),
        "execution_mode": "arm_decoupled",
        "code_manifest_sha256": bindings["code"]["external_manifest_sha256"],
        "configuration_sha256": common.canonical_sha256(bindings["execution"]),
        "acceptance_procedure_sha256": bindings["acceptance_procedure"]["sha256"],
        "stage_ab_supplement_sha256": supplement["supplement_sha256"],
        "bindings_sha256": common.file_sha256(args.bindings),
        "merged_artifacts_compared": list(common.CHUNK_EQUIVALENCE_ARTIFACTS),
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
