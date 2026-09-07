#!/usr/bin/env python3
"""Run the bounded V0.5 C2 screen on the sealed controlled-tape source.

This is an additive source adapter.  It authenticates the V0.5 1,296-row
controlled source, maps its learner pairs into the already-tested V0.4 Q2
offline learner/evaluator, and preserves the frozen 100/500/1500 update
ladder.  Only Q2 receives gradients.  TEST is never opened.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


source = _load_module(
    "mcrl_v05_c2_controlled_screen_source",
    HERE / "run_v05_c2_controlled_source.py",
)
legacy = _load_module(
    "mcrl_v05_c2_controlled_screen_learner",
    HERE / "run_v04_c2_parallel_screen.py",
)


class ControlledScreenError(RuntimeError):
    """A V0.5 source-adapter or screen contract failed closed."""


V05_ARM_TO_LEARNER = {
    "CT-MAIN-VALUE": legacy.C2_MAIN_VALUE,
    "CT-Q13-VALUE": legacy.C2_Q13_VALUE,
    "CT-Q13-HUBER": legacy.C2_Q13_HUBER,
}
LEARNER_TO_V05_ARM = {value: key for key, value in V05_ARM_TO_LEARNER.items()}
V05_ARMS = tuple(V05_ARM_TO_LEARNER)
DEFAULT_SOURCE_ROOT = (
    REPO / "artifacts" / "multi-catfish-v05-c2-controlled-source-20260901-r2"
)
DEFAULT_PREPARE_ROOT = (
    REPO / "artifacts" / "multi-catfish-v05-c2-controlled-screen-prepare-20260901-r1"
)
DEFAULT_BASELINE_ROOT = (
    REPO / "artifacts" / "multi-catfish-v05-c2-controlled-screen-baseline-20260901-r1"
)
DEFAULT_ARM_ROOT = (
    REPO / "artifacts" / "multi-catfish-v05-c2-controlled-screen-arms-20260901-r1"
)
DEFAULT_RESULT_ROOT = (
    REPO / "artifacts" / "multi-catfish-v05-c2-controlled-screen-result-20260901-r1"
)
V05_FIELD_COMPONENT = "V05_C2_CONTROLLED_SCREEN_V1"
V05_ADAPTER_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-screen-adapter-v1"


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ControlledScreenError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _authenticate_source(root: Path) -> dict[str, Any]:
    source_root = Path(root)
    if source_root.is_symlink() or not source_root.is_dir():
        raise ControlledScreenError(f"controlled source root is not regular: {source_root}")
    prepare, schedule, prepare_file_sha = source._read_prepare(
        source_root / "prepare.json"
    )
    merge, merge_file_sha = source._read_json(source_root / "merge.json")
    merge_body = dict(merge)
    merge_sha = _digest(
        merge_body.pop("merge_sha256", None), field="controlled_source.merge_sha256"
    )
    if (
        merge.get("schema") != source.MERGE_SCHEMA
        or merge.get("status") != "CONTROLLED_SOURCE_MERGE_COMPLETE"
        or merge.get("decision") != "AUTHORIZE_THREE_BOUNDED_C2_LEARNER_ARMS"
        or merge.get("claim_ceiling") != source.CLAIM_CEILING
        or merge_sha != source._canonical_sha256(merge_body)
        or merge.get("prepare_file_sha256") != prepare_file_sha
        or merge.get("prepare_sha256") != prepare["prepare_sha256"]
        or merge.get("schedule_sha256") != prepare["schedule"]["schedule_sha256"]
        or merge.get("shard_count") != 48
        or merge.get("row_count") != source.EXPECTED_TOTAL_ROWS
        or merge.get("rows_per_policy_view") != source.EXPECTED_ROWS_PER_VIEW
        or merge.get("training_run") is not False
        or merge.get("test_split_opened") is not False
        or merge.get("held_out_ee_evaluated") is not False
    ):
        raise ControlledScreenError("controlled-source merge receipt is not authentic")
    receipts = merge.get("shards")
    if not isinstance(receipts, list) or len(receipts) != 48:
        raise ControlledScreenError("controlled-source merge lacks exactly 48 shards")
    by_file: dict[str, Mapping[str, Any]] = {}
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise ControlledScreenError("controlled-source shard receipt is malformed")
        name = receipt.get("file")
        if not isinstance(name, str) or Path(name).name != name or name in by_file:
            raise ControlledScreenError("controlled-source shard filename is invalid or duplicated")
        _digest(receipt.get("file_sha256"), field=f"shards[{name}].file_sha256")
        _digest(receipt.get("shard_sha256"), field=f"shards[{name}].shard_sha256")
        if receipt.get("row_count") != source.SIBLINGS_PER_ANCHOR:
            raise ControlledScreenError("controlled-source shard row count drifted")
        by_file[name] = receipt
    return {
        "root": source_root,
        "prepare": prepare,
        "prepare_file_sha256": prepare_file_sha,
        "schedule": schedule,
        "merge": merge,
        "merge_file_sha256": merge_file_sha,
        "merge_sha256": merge_sha,
        "receipts_by_file": by_file,
        # Compatibility fields consumed by the existing learner/evaluator.
        "phase_b_sha256": merge_sha,
        "result_file_sha256": merge_file_sha,
        "seal_file_sha256": prepare_file_sha,
        "eligible_arms": tuple(V05_ARM_TO_LEARNER.values()),
        "eligible_candidates": tuple(V05_ARM_TO_LEARNER.values()),
        "result": {"controlled_source_merge_sha256": merge_sha},
    }


def _verify_hashed_mapping(
    value: object,
    *,
    hash_field: str,
    field: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ControlledScreenError(f"{field} is not a mapping")
    body = dict(value)
    claimed = _digest(body.pop(hash_field, None), field=f"{field}.{hash_field}")
    if claimed != source._canonical_sha256(body):
        raise ControlledScreenError(f"{field} self-digest is invalid")
    return dict(value)


def _read_view_rows(
    phase: Mapping[str, Any],
    *,
    tape_policy: str,
    initialization_seed: int | None,
) -> tuple[dict[str, Any], ...]:
    if tape_policy not in source.POLICY_VIEWS:
        raise ControlledScreenError("unknown V0.5 tape policy")
    if tape_policy == "main" and initialization_seed is not None:
        raise ControlledScreenError("Main source view forbids an initialization seed")
    if tape_policy == "q13" and initialization_seed not in source.Q13_SEEDS:
        raise ControlledScreenError("Q13 source view requires a frozen initialization seed")
    root = Path(phase["root"])
    schedule = phase["schedule"]
    rows: list[dict[str, Any]] = []
    for anchor_index, anchor in enumerate(schedule.anchors):
        name = source._shard_name(tape_policy, initialization_seed, anchor_index)
        payload, file_sha = source._read_json(root / "shards" / name)
        receipt = phase["receipts_by_file"].get(name)
        if not isinstance(receipt, Mapping) or receipt.get("file_sha256") != file_sha:
            raise ControlledScreenError(f"shard {name} is not bound to the merge receipt")
        body = dict(payload)
        shard_sha = _digest(body.pop("shard_sha256", None), field=f"{name}.shard_sha256")
        shard_rows = payload.get("rows")
        if (
            payload.get("schema") != source.SHARD_SCHEMA
            or payload.get("status") != "CONTROLLED_SOURCE_SHARD_COMPLETE"
            or payload.get("claim_ceiling") != source.CLAIM_CEILING
            or shard_sha != source._canonical_sha256(body)
            or receipt.get("shard_sha256") != shard_sha
            or payload.get("prepare_file_sha256") != phase["prepare_file_sha256"]
            or payload.get("anchor_index") != anchor_index
            or payload.get("anchor_sha256") != anchor.anchor_sha256
            or payload.get("tape_policy") != tape_policy
            or payload.get("initialization_seed") != initialization_seed
            or payload.get("policy_parameters_unchanged") is not True
            or payload.get("row_count") != source.SIBLINGS_PER_ANCHOR
            or not isinstance(shard_rows, list)
            or len(shard_rows) != source.SIBLINGS_PER_ANCHOR
            or payload.get("training_run") is not False
            or payload.get("test_split_opened") is not False
            or payload.get("held_out_ee_evaluated") is not False
        ):
            raise ControlledScreenError(f"controlled-source shard failed authentication: {name}")
        observed_keys: list[tuple[int, int]] = []
        state_hashes: set[str] = set()
        for row_index, raw_row in enumerate(shard_rows):
            if not isinstance(raw_row, Mapping):
                raise ControlledScreenError(f"{name}.rows[{row_index}] is malformed")
            row = dict(raw_row)
            if (
                row.get("schema") != source.ROW_SCHEMA
                or row.get("tape_policy") != tape_policy
                or row.get("initialization_seed") != initialization_seed
                or row.get("training_run") is not False
                or row.get("test_split_opened") is not False
                or row.get("held_out_ee_evaluated") is not False
            ):
                raise ControlledScreenError(f"{name}.rows[{row_index}] lineage drifted")
            state = _verify_hashed_mapping(
                row.get("anchor_state"),
                hash_field="anchor_state_sha256",
                field=f"{name}.rows[{row_index}].anchor_state",
            )
            pair = _verify_hashed_mapping(
                row.get("learner_pair"),
                hash_field="learner_pair_sha256",
                field=f"{name}.rows[{row_index}].learner_pair",
            )
            target = row.get("target")
            key = row.get("candidate_physical_key")
            if (
                not isinstance(target, Mapping)
                or not isinstance(key, list)
                or len(key) != 2
                or any(type(value) is not int or value < 0 for value in key)
                or pair.get("target_sha256") != target.get("target_sha256")
                or pair.get("zeta2_temporal_surplus_bits")
                != target.get("zeta2_temporal_surplus_bits")
                or pair.get("candidate_physical_key") != key
            ):
                raise ControlledScreenError(f"{name}.rows[{row_index}] learner pair drifted")
            try:
                target_value = float.fromhex(str(pair["zeta2_temporal_surplus_bits"]))
            except (KeyError, TypeError, ValueError) as error:
                raise ControlledScreenError(
                    f"{name}.rows[{row_index}] target is not an exact finite hex float"
                ) from error
            if not math.isfinite(target_value):
                raise ControlledScreenError(f"{name}.rows[{row_index}] target is nonfinite")
            observed_keys.append((int(key[0]), int(key[1])))
            state_hashes.add(str(state["anchor_state_sha256"]))
            rows.append(row)
        if observed_keys != list(anchor.candidate_physical_keys) or len(state_hashes) != 1:
            raise ControlledScreenError(f"{name} candidate census or anchor state drifted")
    if len(rows) != source.EXPECTED_ROWS_PER_VIEW:
        raise ControlledScreenError("controlled source view is not exactly 324 rows")
    return tuple(rows)


def _build_pair_batch(
    phase: Mapping[str, Any],
    *,
    candidate_id: str,
    initialization_seed: int,
) -> tuple[Any, tuple[dict[str, Any], ...], str]:
    if candidate_id not in V05_ARM_TO_LEARNER.values():
        raise ControlledScreenError("unknown V0.5 learner arm")
    if initialization_seed not in source.Q13_SEEDS:
        raise ControlledScreenError("initialization seed lies outside the frozen lineages")
    tape_policy = "main" if candidate_id == legacy.C2_MAIN_VALUE else "q13"
    view_seed = None if tape_policy == "main" else initialization_seed
    rows = _read_view_rows(
        phase,
        tape_policy=tape_policy,
        initialization_seed=view_seed,
    )
    states: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    references: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    metadata: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        state_record = row["anchor_state"]
        pair = row["learner_pair"]
        state = np.asarray(state_record["state"], dtype=np.float32)
        mask = np.asarray(state_record["action_mask"])
        reference = pair.get("reference_action")
        candidate = pair.get("candidate_action")
        if (
            state.shape != (legacy.STATE_DIM,)
            or not np.all(np.isfinite(state))
            or mask.dtype != np.bool_
            or mask.shape != (legacy.ACTION_DIM,)
            or type(reference) is not int
            or type(candidate) is not int
            or not 0 <= reference < legacy.ACTION_DIM
            or not 0 <= candidate < legacy.ACTION_DIM
            or not bool(mask[reference])
            or not bool(mask[candidate])
        ):
            raise ControlledScreenError(f"learner row {index} has an invalid state/action pair")
        target = float.fromhex(str(pair["zeta2_temporal_surplus_bits"]))
        physical = tuple(int(value) for value in row["candidate_physical_key"])
        cluster = [
            int(row["source_seed"]),
            str(row["anchor_sha256"]),
            str(row["tape"]["tape_sha256"]),
            int(row["focal_user"]),
        ]
        sibling = [*cluster, list(physical)]
        states.append(state)
        masks.append(mask)
        references.append(reference)
        candidates.append(candidate)
        targets.append(target)
        metadata.append(
            {
                "sibling_key": sibling,
                "intervention_key": cluster,
                "candidate_id": candidate_id,
                "v05_arm_id": LEARNER_TO_V05_ARM[candidate_id],
                "target_source": tape_policy,
                "target_surplus_bits": target,
                "candidate_action": candidate,
                "reference_action": reference,
            }
        )
    if legacy.torch is None:
        raise ControlledScreenError("torch-backed learner is unavailable")
    from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch

    batch = EEAxisPairBatch(
        states=np.asarray(states, dtype=np.float32),
        reference_actions=np.asarray(references, dtype=np.int64),
        candidate_actions=np.asarray(candidates, dtype=np.int64),
        target_surplus_bits=np.asarray(targets, dtype=np.float32),
        action_masks=np.asarray(masks, dtype=np.bool_),
    )
    batch.validate(state_dim=legacy.STATE_DIM, action_dim=legacy.ACTION_DIM)
    corpus_sha = legacy._array_sha256(
        batch.states,
        batch.reference_actions,
        batch.candidate_actions,
        batch.target_surplus_bits,
        batch.action_masks,
    )
    return batch, tuple(metadata), corpus_sha


def _gate_binding(phase: Mapping[str, Any], gate: Mapping[str, Any]) -> None:
    if gate.get("selected_q3_rung") != 100:
        raise ControlledScreenError("the controlled screen requires the frozen Q3 rung 100")
    selected = gate.get("result", {}).get("selected_hybrids")
    if not isinstance(selected, Mapping) or set(selected) != {
        str(seed) for seed in source.Q13_SEEDS
    }:
        raise ControlledScreenError("Q1+Q3 gate does not contain exactly three frozen lineages")
    _digest(phase.get("merge_sha256"), field="controlled_source.merge_sha256")


def _authenticate_prepare(
    path: Path,
    *,
    phase_b: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(path)
    payload, payload_sha = legacy._read_json(root / "prepare.json")
    seal, seal_sha = legacy._read_json(root / "prepare-seal.json")
    binding = payload.get("gate_binding")
    if not isinstance(binding, Mapping):
        raise ControlledScreenError("controlled-screen prepare lacks a gate binding")
    for field in (
        "authority_sha256",
        "authority_file_sha256",
        "result_file_sha256",
        "source_manifest_sha256",
        "schedule_sha256",
    ):
        _digest(binding.get(field), field=f"prepare.gate_binding.{field}")
    if (
        payload.get("schema") != legacy.PREPARE_SCHEMA
        or payload.get("status") != "PREPARED"
        or payload.get("claim_ceiling") != legacy.CLAIM_CEILING
        or payload.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or payload.get("eligible_arms") != list(phase_b["eligible_arms"])
        or payload.get("initialization_seeds") != list(legacy.INITIALIZATION_SEEDS)
        or payload.get("update_ladder") != list(legacy.UPDATE_LADDER)
        or payload.get("checkpoint_every") != legacy.CHECKPOINT_EVERY
        or payload.get("field_components")
        != [legacy.FIELD_COMPONENT, phase_b["phase_b_sha256"], "evaluation_seed"]
        or binding.get("selected_q3_rung") != 100
        or payload.get("counterfactual_outcomes_evaluated") is not False
        or payload.get("test_split_opened") is not False
        or payload.get("held_out_ee_evaluated") is not False
        or payload.get("episode_training") is not False
        or seal.get("schema") != legacy.PREPARE_SEAL_SCHEMA
        or seal.get("prepare_file_sha256") != payload_sha
        or seal.get("phase_b_sha256") != phase_b["phase_b_sha256"]
        or seal.get("counterfactual_outcomes_evaluated") is not False
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
        or seal.get("episode_training") is not False
    ):
        raise ControlledScreenError("controlled-screen prepare receipt is not authentic")
    return {
        "dir": root,
        "payload": payload,
        "payload_file_sha256": payload_sha,
        "seal": seal,
        "seal_file_sha256": seal_sha,
    }


_ORIGINAL_BASELINE_AUTH = legacy.authenticate_shared_baseline


def _install_adapters(phase: Mapping[str, Any]) -> None:
    legacy.FIELD_COMPONENT = V05_FIELD_COMPONENT
    legacy.authenticate_phase_b = lambda _path, *, phase_a_dir: phase
    legacy.build_pair_batch = _build_pair_batch
    legacy._phase_b_gate_binding = _gate_binding
    legacy.authenticate_prepare = _authenticate_prepare
    legacy.authenticate_shared_baseline = _ORIGINAL_BASELINE_AUTH


def _mapped_result(result: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(result)
    candidate = output.get("candidate_id")
    if candidate in LEARNER_TO_V05_ARM:
        output["learner_candidate_id"] = candidate
        output["candidate_id"] = LEARNER_TO_V05_ARM[candidate]
    selected = output.get("selected")
    if isinstance(selected, Mapping) and selected.get("candidate_id") in LEARNER_TO_V05_ARM:
        output["selected"] = dict(selected) | {
            "learner_candidate_id": selected["candidate_id"],
            "candidate_id": LEARNER_TO_V05_ARM[selected["candidate_id"]],
        }
    output["adapter_schema"] = V05_ADAPTER_SCHEMA
    return output


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "baseline", "arm", "merge"))
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--prepare-root", type=Path, default=DEFAULT_PREPARE_ROOT)
    parser.add_argument("--baseline-root", type=Path, default=DEFAULT_BASELINE_ROOT)
    parser.add_argument("--arm-root", type=Path, default=DEFAULT_ARM_ROOT)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--arm", choices=V05_ARMS)
    parser.add_argument("--initialization-seed", type=int, choices=source.Q13_SEEDS)
    parser.add_argument("--target-update", type=int, choices=legacy.UPDATE_LADDER, default=100)
    parser.add_argument("--gate-dir", type=Path, default=legacy.DEFAULT_GATE_DIR)
    parser.add_argument("--c3-source-dir", type=Path, default=legacy.DEFAULT_C3_SOURCE_DIR)
    parser.add_argument("--v03-root", type=Path, default=legacy.DEFAULT_V03_ROOT)
    parser.add_argument("--prereg", type=Path, default=legacy.DEFAULT_PREREG)
    parser.add_argument("--tle-root", type=Path, default=legacy.DEFAULT_TLE_ROOT)
    parser.add_argument("--main-dir", type=Path, default=legacy.DEFAULT_MAIN_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    phase = _authenticate_source(args.source_root)
    _install_adapters(phase)
    common = {
        "phase_b_dir": args.source_root,
        "phase_a_dir": args.source_root,
    }
    runtime = {
        "gate_dir": args.gate_dir,
        "c3_source_dir": args.c3_source_dir,
        "v03_root": args.v03_root,
        "prereg_path": args.prereg,
        "tle_root": args.tle_root,
        "main_dir": args.main_dir,
    }
    if args.command == "prepare":
        result = legacy.prepare_screen(
            **common,
            **runtime,
            output_dir=args.prepare_root,
        )
    elif args.command == "baseline":
        result = legacy.run_shared_baseline(
            **common,
            **runtime,
            prepare_dir=args.prepare_root,
            output_dir=args.baseline_root,
        )
    elif args.command == "arm":
        if args.arm is None or args.initialization_seed is None:
            raise ControlledScreenError("arm requires --arm and --initialization-seed")
        learner_id = V05_ARM_TO_LEARNER[args.arm]
        output_dir = args.arm_root / learner_id / f"init-{args.initialization_seed}"
        result = legacy.run_arm(
            **common,
            **runtime,
            prepare_dir=args.prepare_root,
            baseline_dir=args.baseline_root,
            candidate_id=learner_id,
            initialization_seed=args.initialization_seed,
            target_update=args.target_update,
            output_dir=output_dir,
        )
    else:
        result = legacy.merge_screen(
            **common,
            prepare_dir=args.prepare_root,
            baseline_dir=args.baseline_root,
            arm_root=args.arm_root,
            target_update=args.target_update,
            output_dir=args.result_root,
        )
    print(json.dumps(_mapped_result(result), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
