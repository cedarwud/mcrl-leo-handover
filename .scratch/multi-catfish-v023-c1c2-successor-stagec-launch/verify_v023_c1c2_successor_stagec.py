#!/usr/bin/env python3
"""Independent verifier for a finished formal Stage-C root."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import struct
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

import stagec_common as common


STOP = "STOP_PHYSICAL_EVALUATION_INTEGRITY"
HELD = "C1C2_DEVELOPMENT_PREDICTION_HELD"
FALSIFIED = "C1C2_DEVELOPMENT_PREDICTION_FALSIFIED"
RECEIPT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-episode-receipt"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-checkpoint"
RUNG_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-rung-receipt"
RESULT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-result"
STATUS = "FIXED_POLICY_EVALUATION"
CONTINUATION_STATUSES = frozenset({STATUS})
CONTINUATION_RESULT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-continuation-result"
ADMINISTRATIVE_CLOSURE_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-"
    "administrative-closure-v1"
)


def _same(left: float, right: float, tolerance: float = 0.0) -> bool:
    """IEEE-754 binary64 equality; tolerance is retained only for API stability."""

    del tolerance
    return struct.pack(">d", left) == struct.pack(">d", right)


def _reject_nonformal(root: Path) -> None:
    def contains_stop(value: object) -> bool:
        if isinstance(value, Mapping):
            return any(contains_stop(child) for child in value.values())
        if isinstance(value, (list, tuple)):
            return any(contains_stop(child) for child in value)
        return isinstance(value, str) and value.upper().startswith("STOP_")

    if "REHEARSAL-NONFORMAL" in str(root).upper():
        raise common.StageCError("REHEARSAL-NONFORMAL roots are rejected")
    for path in root.rglob("*"):
        if "REHEARSAL-NONFORMAL" in path.name.upper():
            raise common.StageCError("REHEARSAL-NONFORMAL receipt is rejected")
        if path.is_symlink():
            raise common.StageCError(f"finished root contains a symlink: {path}")
        if path.is_file() and path.suffix == ".json":
            value = common.read_json(path, field=f"receipt {path.relative_to(root)}")
            if value.get("formal") is False:
                raise common.StageCError(f"non-formal receipt is rejected: {path.name}")
            if "REHEARSAL-NONFORMAL" in json.dumps(value, ensure_ascii=True).upper():
                raise common.StageCError(f"rehearsal receipt is rejected: {path.name}")
            if contains_stop(value):
                raise common.StageCError(f"root carrying a STOP token is not a scientific result: {path.name}")


def _physical_runner() -> Any:
    parent = str(common.PHYSICAL)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    module = importlib.import_module("v023_c1c2_successor_physical_runner")
    if Path(module.__file__).resolve() != (common.PHYSICAL / "v023_c1c2_successor_physical_runner.py").resolve():
        raise common.StageCError("physical runner module origin drifted")
    return module


def _expected_policy_bindings(bindings: Mapping[str, object]) -> dict[str, object]:
    runner = _physical_runner()
    stage_a = bindings.get("stage_a")
    baseline = bindings.get("baseline")
    if not isinstance(stage_a, Mapping) or not isinstance(baseline, Mapping):
        raise common.StageCError("frozen policy inputs are malformed")
    exports = stage_a.get("exports")
    if not isinstance(exports, list):
        raise common.StageCError("frozen learned exports are malformed")
    provenance = common.learned_training_provenance(bindings)
    learned = [
        runner.load_learned_two_route_checkpoint(
            Path(str(stage_a["root"])) / str(entry["path"]),
            arm=arm,
            expected_sha256=str(entry["sha256"]),
            training_provenance=provenance[arm],
        )
        for arm, entry in zip(common.LEARNED_ARMS, exports, strict=True)
    ]
    base = runner.load_baseline_policy(
        checkpoint_path=baseline["checkpoint_path"],
        status_path=baseline["status_path"],
        expected_status_sha256=baseline["status_sha256"],
    )
    return {policy.arm: policy.binding() for policy in (*learned, base)}


def _expected_policy_binding(bindings: Mapping[str, object], arm: str) -> Mapping[str, object]:
    if arm != "BASELINE":
        return _expected_policy_bindings(bindings)[arm]
    runner = _physical_runner()
    baseline = bindings.get("baseline")
    if not isinstance(baseline, Mapping):
        raise common.StageCError("frozen BASELINE input is malformed")
    return runner.load_baseline_policy(
        checkpoint_path=baseline["checkpoint_path"],
        status_path=baseline["status_path"],
        expected_status_sha256=baseline["status_sha256"],
    ).binding()


def _verify_formal_admission(
    root: Path,
    bindings: Mapping[str, object],
    expected_policy_bindings: Mapping[str, object],
    bindings_sha256: str,
    supplement: Mapping[str, object],
) -> dict[str, object]:
    path = root / common.FORMAL_ADMISSION_NAME
    payload = common.read_json(path, field="formal Stage-C admission")
    common.verify_named_sidecar(path)
    mapping = common.verify_stage_c_admission_mapping(payload.get("admission_mapping"))
    inputs = payload.get("authenticated_inputs")
    required = {
        "prereg": "prereg_sha256",
        "tle_manifest": "tle_manifest_sha256",
        "execution_configuration": "execution_configuration_sha256",
        "stage_a_pass_receipt": "stage_a_pass_receipt_sha256",
        "stage_b_pass_receipt": "stage_b_pass_receipt_sha256",
        "runtime_admission": None,
    }
    if not isinstance(inputs, Mapping):
        raise common.StageCError("formal admission lacks authenticated input files")
    for name, digest_field in required.items():
        record = inputs.get(name)
        if not isinstance(record, Mapping):
            raise common.StageCError(f"formal admission input missing: {name}")
        observed = common.file_sha256(str(record.get("path")), field=f"formal admission {name}")
        expected = common.digest(record.get("sha256"), field=f"formal admission {name} digest")
        if observed != expected or (digest_field is not None and payload.get(digest_field) != expected):
            raise common.StageCError(f"formal admission input bytes drifted: {name}")
        if name in {"tle_manifest", "execution_configuration", "stage_b_pass_receipt", "runtime_admission"}:
            common.verify_named_sidecar(str(record.get("path")))
    stage_a = supplement.get("stage_a")
    stage_b = supplement.get("stage_b_pass_receipt")
    if not isinstance(stage_a, Mapping) or not isinstance(stage_b, Mapping):
        raise common.StageCError("formal admission lacks authenticated Stage-A/B supplement inputs")
    stage_a_pass = stage_a.get("pass_receipt")
    if not isinstance(stage_a_pass, Mapping):
        raise common.StageCError("formal admission lacks the supplemented Stage-A PASS receipt")
    expected_stage_a_path = (
        Path(str(stage_a.get("root", ""))) / str(stage_a_pass.get("path", ""))
    ).resolve()
    expected_stage_b_path = Path(str(stage_b.get("path", ""))).resolve()
    for name, expected_path, expected_sha in (
        ("stage_a_pass_receipt", expected_stage_a_path, stage_a_pass.get("sha256")),
        ("stage_b_pass_receipt", expected_stage_b_path, stage_b.get("sha256")),
    ):
        record = inputs[name]
        if (
            Path(str(record.get("path", ""))).resolve() != expected_path
            or record.get("sha256") != expected_sha
        ):
            raise common.StageCError(f"formal admission {name} differs from Stage-A/B supplement")
    if (
        payload.get("schema") != f"{_physical_runner().SCHEMA}-formal-admission-v1"
        or payload.get("status") != "FORMAL_STAGE_C_ADMITTED"
        or payload.get("formal") is not True
        or payload.get("integrity_status") != "VERIFIED"
        or payload.get("split") != "TRAIN"
        or payload.get("arms") != list(common.ARMS)
        or payload.get("plan_sha256") != common.PLAN_SHA256
        or payload.get("bindings_sha256") != bindings_sha256
        or payload.get("stage_ab_supplement_sha256")
        != supplement.get("supplement_sha256")
        or payload.get("git") != bindings.get("git")
        or payload.get("policy_bindings_sha256") != common.canonical_sha256(expected_policy_bindings)
        or payload.get("admission_mapping_sha256") != common.canonical_sha256(mapping)
        or any(mapping[arm].get("policy_binding") != expected_policy_bindings[arm] for arm in common.ARMS)
    ):
        raise common.StageCError("formal admission identity/policy mapping drifted")
    return payload


def _pool(rows: Sequence[Mapping[str, object]], arm: str) -> dict[str, object]:
    selected = [row for row in rows if row.get("arm") == arm]
    if not selected:
        raise common.StageCError(f"empty pooled arm: {arm}")
    bits = math.fsum(float(row["total_bits"]) for row in selected)
    energy = math.fsum(float(row["total_energy_j"]) for row in selected)
    served = sum(int(row["served_user_steps"]) for row in selected)
    opportunities = sum(int(row["service_opportunities"]) for row in selected)
    if not math.isfinite(bits) or bits < 0 or not math.isfinite(energy) or energy <= 0 or opportunities <= 0:
        raise common.StageCError("invalid additive pooled endpoint")
    return {
        "arm": arm,
        "routes": [] if arm == "BASELINE" else ["C1", "C2"],
        "episodes": len(selected),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
        "episode_training": False,
        "learner_update": False,
    }


def _verify_pool(actual: object, expected: Mapping[str, object], *, field: str) -> None:
    if not isinstance(actual, Mapping) or set(actual) != set(expected):
        raise common.StageCError(f"{field} pooled fields drifted")
    for key, value in expected.items():
        observed = actual[key]
        if isinstance(value, float):
            if not isinstance(observed, (int, float)) or not _same(float(observed), value):
                raise common.StageCError(f"{field}.{key} is not pooled from additive totals")
        elif observed != value:
            raise common.StageCError(f"{field}.{key} drifted")


def verify_episode_rows(
    rows: Sequence[Mapping[str, object]],
    plan: Mapping[str, object],
    completed: int,
    *,
    expected_policy_bindings: Mapping[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    if len(rows) != completed * len(common.ARMS):
        raise common.StageCError("checkpoint lacks exact four-arm episode coverage")
    worlds = plan.get("worlds")
    if not isinstance(worlds, list) or len(worlds) != 9000:
        raise common.StageCError("frozen plan world list drifted")
    bindings_by_arm: dict[str, object] = {}
    for episode in range(1, completed + 1):
        block = rows[(episode - 1) * 4 : episode * 4]
        if [row.get("arm") for row in block] != list(common.ARMS):
            raise common.StageCError("episode arm order/coverage drifted")
        world = worlds[episode - 1]
        initials = set()
        for arm, row in zip(common.ARMS, block, strict=True):
            if row.get("schema") != RECEIPT_SCHEMA or row.get("status") != STATUS or row.get("split") != "TRAIN":
                raise common.StageCError("episode receipt identity drifted")
            routes = [] if arm == "BASELINE" else ["C1", "C2"]
            expected = {
                "arm": arm, "routes": routes, "episode_index": episode,
                "world_id": world["world_id"], "world_seed": world["world_seed"],
                "users": 100, "steps": 10, "field_component": common.FIELD_COMPONENT,
                "field_root_digest": world["field_root_digest"], "plan_sha256": common.PLAN_SHA256,
                "q3_evaluated": False, "test_split_opened": False,
                "episode_training": False, "learner_update": False,
                "claim_ceiling": common.FORMAL_CLAIM,
            }
            for key, value in expected.items():
                if row.get(key) != value:
                    raise common.StageCError(f"episode {episode} {arm} field drifted: {key}")
            bits = float(row.get("total_bits", math.nan))
            energy = float(row.get("total_energy_j", math.nan))
            ratio = float(row.get("ratio_of_sums_ee_bits_per_j", math.nan))
            served = row.get("served_user_steps")
            opportunities = row.get("service_opportunities")
            if not math.isfinite(bits) or bits < 0 or not math.isfinite(energy) or energy <= 0 or not _same(ratio, bits / energy):
                raise common.StageCError("episode endpoint is not additive bits/positive energy")
            if type(served) is not int or opportunities != 1000 or not 0 <= served <= opportunities:
                raise common.StageCError("service denominator/count drifted")
            if not _same(float(row.get("service_fraction", math.nan)), served / opportunities, 1e-15):
                raise common.StageCError("service fraction is not served/opportunity")
            policy = row.get("policy_binding")
            if not isinstance(policy, Mapping) or policy.get("arm") != arm or policy.get("routes") != routes:
                raise common.StageCError("policy binding drifted")
            if arm in bindings_by_arm and bindings_by_arm[arm] != policy:
                raise common.StageCError("policy binding changed across episodes")
            if expected_policy_bindings is not None and policy != expected_policy_bindings.get(arm):
                raise common.StageCError(f"{arm} policy binding differs from frozen policy")
            bindings_by_arm[arm] = policy
            initials.add(row.get("initial_world_sha256"))
        if len(initials) != 1:
            raise common.StageCError("matched arms do not share one initial world")
    return {arm: _pool(rows, arm) for arm in common.ARMS}


def _read_checkpoint(path: Path) -> dict[str, Any]:
    value = common.read_json(path, field=f"checkpoint {path.name}")
    claimed = value.pop("checkpoint_sha256", None)
    if common.digest(claimed, field="checkpoint_sha256") != common.canonical_sha256(value):
        raise common.StageCError(f"checkpoint content digest drifted: {path.name}")
    return value


def _disposition(pooled: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    ee = {arm: float(pooled[arm]["ratio_of_sums_ee_bits_per_j"]) for arm in common.ARMS}
    service = {arm: float(pooled[arm]["service_fraction"]) for arm in common.ARMS}
    reasons = []
    for arm in common.LEARNED_ARMS:
        if ee[arm] <= ee["BASELINE"]:
            reasons.append(f"{arm}_NOT_ABOVE_BASELINE")
    for arm in ("DROP_C1", "DROP_C2"):
        if ee[arm] >= ee["FULL2"]:
            reasons.append(f"{arm}_NOT_BELOW_FULL2")
    for arm in common.LEARNED_ARMS:
        if service[arm] < service["BASELINE"] - 0.001:
            reasons.append(f"SERVICE_NONINFERIORITY_FAILED:{arm}")
    return {"overall_token": HELD if not reasons else FALSIFIED, "reasons": reasons}


def _verify_cumulative_prefix(
    previous_rows: Sequence[Mapping[str, object]],
    previous_pooled: Mapping[str, Mapping[str, object]] | None,
    rows: Sequence[Mapping[str, object]],
    pooled: Mapping[str, Mapping[str, object]],
    *,
    boundary: int,
) -> None:
    if previous_rows and list(rows[: len(previous_rows)]) != list(previous_rows):
        raise common.StageCError(f"cumulative receipt prefix was rewritten at {boundary}")
    if previous_pooled is None:
        return
    delta_rows = rows[len(previous_rows) :]
    for arm in common.ARMS:
        delta = _pool(delta_rows, arm)
        previous = previous_pooled[arm]
        for additive in (
            "episodes",
            "total_bits",
            "total_energy_j",
            "served_user_steps",
            "service_opportunities",
        ):
            observed = pooled[arm][additive]
            expected_sum = previous[additive] + delta[additive]
            if isinstance(observed, float):
                if not math.isclose(
                    float(observed), float(expected_sum), rel_tol=1e-15, abs_tol=1e-12
                ):
                    raise common.StageCError(
                        f"rung {boundary} {arm} cumulative {additive} is not prefix plus new episodes"
                    )
            elif observed != expected_sum:
                raise common.StageCError(
                    f"rung {boundary} {arm} cumulative {additive} is not prefix plus new episodes"
                )


def _verify_arm_merge_provenance(value: object, arm_order: object) -> None:
    if (
        not isinstance(value, Mapping)
        or set(value) != set(common.ARMS)
        or arm_order != list(common.ARMS)
    ):
        raise common.StageCError("four-arm output lost arm-merge provenance")
    for arm in common.ARMS:
        record = value[arm]
        if not isinstance(record, Mapping):
            raise common.StageCError(f"{arm} arm-merge provenance is malformed")
        path = Path(str(record.get("path", "")))
        if common.file_sha256(path, field=f"{arm} arm merge") != record.get("sha256"):
            raise common.StageCError(f"{arm} arm-merge bytes drifted")
        merge = common.read_json(path, field=f"{arm} arm merge")
        chunks = record.get("chunk_receipts")
        if merge.get("chunk_receipts") != chunks or not isinstance(chunks, list):
            raise common.StageCError(f"{arm} chunk provenance was disconnected")
        for chunk in chunks:
            if not isinstance(chunk, Mapping) or common.file_sha256(str(chunk.get("path", ""))) != chunk.get("sha256"):
                raise common.StageCError(f"{arm} indexed chunk receipt drifted")
        completed = merge.get("completed_episode")
        if completed == 9000:
            pairs = merge.get("boundary_state_hash_pairs")
            if not isinstance(pairs, list) or len(pairs) != 90 or len(chunks) != 90:
                raise common.StageCError(f"{arm} continuation boundary coverage drifted")
            for index, (chunk, pair) in enumerate(zip(chunks, pairs, strict=True)):
                receipt_path = Path(str(chunk["path"]))
                receipt = common.read_json(receipt_path, field=f"{arm} chunk receipt")
                expected_start = index * 100
                expected_end = expected_start + 100
                if (
                    receipt.get("start_boundary") != expected_start
                    or receipt.get("end_boundary") != expected_end
                    or pair != [
                        receipt.get("start_boundary_state_sha256"),
                        receipt.get("end_boundary_state_sha256"),
                    ]
                    or (index and pairs[index - 1][1] != pair[0])
                ):
                    raise common.StageCError(f"{arm} continuation boundary continuity drifted")
            for offset in (30, 60):
                before = Path(str(chunks[offset - 1]["path"])).parent / "boundary-end.json"
                after = Path(str(chunks[offset]["path"])).parent / "boundary-start.json"
                if before.read_bytes() != after.read_bytes():
                    raise common.StageCError(
                        f"{arm} continuation continuity failed at {offset * 100}->{offset * 100 + 1}"
                    )


def _verify_administrative_closure(
    root: Path,
    *,
    bindings_sha256: str,
    policy_bindings_sha256: str,
    admission_mapping_sha256: str,
    scheduling_addendum_path: str,
    scheduling_addendum_sha256: str,
) -> dict[str, object] | None:
    path = root / "ADMINISTRATIVE-CLOSURE.json"
    if not path.exists():
        return None
    receipt = common.read_json(path, field="administrative closure receipt")
    receipt_sha = common.verify_named_sidecar(path)
    result_sha = common.file_sha256(root / "result.json")
    checkpoint_sha = common.file_sha256(root / "checkpoints/checkpoint-003000.json")
    marker_record = receipt.get("decision_marker")
    addendum_record = receipt.get("addendum_r2")
    bindings_record = receipt.get("execution_bindings")
    if (
        not isinstance(marker_record, Mapping)
        or not isinstance(addendum_record, Mapping)
        or not isinstance(bindings_record, Mapping)
    ):
        raise common.StageCError(
            "administrative closure lacks decision/addendum/execution-bindings bindings"
        )
    marker_path = Path(str(marker_record.get("path", "")))
    marker_sha = common.verify_named_sidecar(marker_path)
    bound_bindings_path = Path(str(bindings_record.get("path", "")))
    bound_bindings_sha = common.verify_named_sidecar(bound_bindings_path)
    if (
        bindings_record.get("sha256") != bound_bindings_sha
        or bound_bindings_sha != bindings_sha256
    ):
        raise common.StageCError("administrative closure execution bindings drifted")
    bound_bindings = common.read_json(
        bound_bindings_path, field="administrative closure execution bindings"
    )
    addendum_path, addendum_sha = common.verify_bound_scheduling_addendum(
        addendum_record, bound_bindings
    )
    marker = common.read_json(marker_path, field="owner closure decision marker")
    decision = receipt.get("decision")
    common.validate_owner_closure_decision_marker(
        marker,
        bindings_sha256=bindings_sha256,
        plan_sha256=common.PLAN_SHA256,
        policy_bindings_sha256=policy_bindings_sha256,
        admission_mapping_sha256=admission_mapping_sha256,
        result_3000_sha256=result_sha,
        held_terminal_token_sha256=hashlib.sha256(HELD.encode("ascii")).hexdigest(),
        checkpoint_3000_sha256=checkpoint_sha,
    )
    if (
        receipt.get("schema") != ADMINISTRATIVE_CLOSURE_SCHEMA
        or receipt.get("status") != "ADMINISTRATIVE_CLOSURE_SEALED"
        or receipt.get("formal") is not True
        or decision not in {"DECLINE_CONTINUATION", "DEFER_AND_CLOSE_REPORTING_ROOT"}
        or receipt.get("reason") != decision
        or receipt.get("continuation_performed") is not False
        or receipt.get("planned_maximum_episodes") != 9000
        or receipt.get("completed_boundary") != 3000
        or receipt.get("bindings_sha256") != bindings_sha256
        or receipt.get("plan_sha256") != common.PLAN_SHA256
        or receipt.get("policy_bindings_sha256") != policy_bindings_sha256
        or receipt.get("admission_mapping_sha256") != admission_mapping_sha256
        or receipt.get("result_3000_sha256") != result_sha
        or receipt.get("checkpoint_3000_sha256") != checkpoint_sha
        or receipt.get("held_terminal_token_sha256")
        != hashlib.sha256(HELD.encode("ascii")).hexdigest()
        or marker_record.get("sha256") != marker_sha
        or addendum_record.get("sha256") != addendum_sha
        or bindings_record.get("sha256") != bound_bindings_sha
        or addendum_path.resolve() != Path(scheduling_addendum_path).resolve()
        or addendum_sha != scheduling_addendum_sha256
        or marker.get("decision") != decision
        or receipt.get("controller_identity") != marker.get("recorded_by")
    ):
        raise common.StageCError("administrative closure authentication drifted")
    return {**receipt, "receipt_sha256": receipt_sha}


def _verify_continuation_result_semantics(continuation: Mapping[str, object]) -> None:
    """Reject a second disposition or any boundary opened by continuation."""

    if (
        continuation.get("schema") != CONTINUATION_RESULT_SCHEMA
        or continuation.get("status") not in CONTINUATION_STATUSES
        or continuation.get("split") != "TRAIN"
        or continuation.get("completed_episode") != 9000
        or continuation.get("terminal_boundary") != 9000
        or continuation.get("plan_sha256") != common.PLAN_SHA256
        or continuation.get("arms") != list(common.ARMS)
        or continuation.get("authorized_from_3000_token") != HELD
        or continuation.get("scientific_disposition_emitted") is not False
        or "overall_token" in continuation
        or "reasons" in continuation
        or continuation.get("q3_evaluated") is not False
        or continuation.get("test_split_opened") is not False
        or continuation.get("episode_training") is not False
        or continuation.get("learner_update") is not False
        or continuation.get("claim_ceiling") != common.FORMAL_CLAIM
    ):
        raise common.StageCError("9000 continuation result contains forbidden semantics")


def verify_finished(
    root: Path, bindings_path: Path, admission_supplement: Path, *,
    require_tree_seal: bool = True,
) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise common.StageCError("finished Stage-C root is unavailable")
    _reject_nonformal(root)
    bindings = common.verify_bindings(bindings_path)
    supplement = common.verify_stage_ab_supplement(
        admission_supplement, bindings_path, bindings
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings)
    bindings_sha = common.file_sha256(bindings_path)
    code_sha, _entries = common.verify_code_manifest()
    if bindings.get("code", {}).get("external_manifest_sha256") != code_sha:
        raise common.StageCError("finished root code closure differs from bindings")
    if str(root.resolve()) != bindings.get("stage_c_output_root"):
        raise common.StageCError("finished root differs from frozen Stage-C output root")
    expected_policy_bindings = _expected_policy_bindings(bindings)
    expected_admission_mapping = common.stage_c_admission_mapping(bindings, expected_policy_bindings)
    admission = _verify_formal_admission(
        root, bindings, expected_policy_bindings, bindings_sha, supplement
    )
    marker = common.read_json(root / "FORMAL-RUN.json", field="formal root marker")
    if marker.get("formal") is not True or marker.get("arms") != list(common.ARMS):
        raise common.StageCError("formal root marker is absent or drifted")
    if (
        marker.get("bindings_sha256") != bindings_sha
        or marker.get("admission_mapping_sha256")
        != common.canonical_sha256(expected_admission_mapping)
        or admission.get("admission_mapping") != expected_admission_mapping
    ):
        raise common.StageCError("formal root marker bindings drifted")
    plan = common.read_json(bindings["world_plan"]["path"], field="frozen world plan")
    if (
        common.file_sha256(bindings["world_plan"]["path"], field="frozen world plan") != bindings["world_plan"].get("file_sha256")
        or plan.get("plan_sha256") != common.PLAN_SHA256
        or plan.get("arms") != list(common.ARMS)
    ):
        raise common.StageCError("frozen plan identity/arm order drifted")
    plan_body = dict(plan)
    plan_body.pop("plan_sha256", None)
    if common.canonical_sha256(plan_body) != common.PLAN_SHA256:
        raise common.StageCError("frozen plan content digest drifted")
    result = common.read_json(root / "result.json", field="3000 result")
    result_expected = {
        "schema": RESULT_SCHEMA,
        "status": STATUS,
        "split": "TRAIN",
        "completed_episode": 3000,
        "terminal_boundary": 3000,
        "plan_sha256": common.PLAN_SHA256,
        "arms": list(common.ARMS),
        "continuation_authority_sha256": None,
        "q3_evaluated": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "claim_ceiling": common.FORMAL_CLAIM,
    }
    if any(result.get(key) != value for key, value in result_expected.items()):
        raise common.StageCError("terminal result must be the 3000 boundary")
    completed = 9000 if (root / "continuation-result.json").is_file() else 3000
    result_like = sorted(path.name for path in root.glob("*result*.json"))
    expected_result_files = ["continuation-result.json", "result.json"] if completed == 9000 else ["result.json"]
    if result_like != expected_result_files:
        raise common.StageCError("finished root terminal result file set drifted")
    checkpoint_names = [path.name for path in sorted((root / "checkpoints").glob("checkpoint-*.json"))]
    rung_names = [path.name for path in sorted((root / "rungs").glob("rung-*.json"))]
    expected_names = [f"checkpoint-{index:06d}.json" for index in range(100, completed + 1, 100)]
    if checkpoint_names != expected_names or rung_names != [name.replace("checkpoint", "rung") for name in expected_names]:
        raise common.StageCError("100-episode checkpoint/rung cadence is incomplete or ahead")
    latest_rows: list[Mapping[str, object]] | None = None
    latest_pooled: dict[str, dict[str, object]] | None = None
    previous_rows: list[Mapping[str, object]] = []
    previous_pooled: dict[str, dict[str, object]] | None = None
    for boundary in range(100, completed + 1, 100):
        checkpoint = _read_checkpoint(root / "checkpoints" / f"checkpoint-{boundary:06d}.json")
        if (
            checkpoint.get("schema") != CHECKPOINT_SCHEMA or checkpoint.get("status") != STATUS
            or checkpoint.get("completed_episode") != boundary or checkpoint.get("arms") != list(common.ARMS)
            or checkpoint.get("checkpoint_every") != 100 or checkpoint.get("plan_sha256") != common.PLAN_SHA256
            or checkpoint.get("policy_bindings") != expected_policy_bindings
            or checkpoint.get("admission_mapping") != expected_admission_mapping
        ):
            raise common.StageCError(f"checkpoint identity drifted at {boundary}")
        if checkpoint.get("execution_mode") == "arm_decoupled":
            _verify_arm_merge_provenance(
                checkpoint.get("arm_merge_provenance"), checkpoint.get("arm_order")
            )
        rows = checkpoint.get("receipts")
        if not isinstance(rows, list):
            raise common.StageCError(f"checkpoint receipts missing at {boundary}")
        pooled = verify_episode_rows(
            rows,
            plan,
            boundary,
            expected_policy_bindings=expected_policy_bindings,
        )
        rung = common.read_json(root / "rungs" / f"rung-{boundary:06d}.json", field=f"rung {boundary}")
        if (
            rung.get("schema") != RUNG_SCHEMA or rung.get("completed_episode") != boundary
            or rung.get("plan_sha256") != common.PLAN_SHA256 or rung.get("arms") != list(common.ARMS)
            or rung.get("scientific_disposition_emitted") is not False
            or rung.get("admission_mapping") != expected_admission_mapping
        ):
            raise common.StageCError(f"rung receipt identity drifted at {boundary}")
        if rung.get("execution_mode") == "arm_decoupled":
            _verify_arm_merge_provenance(
                rung.get("arm_merge_provenance"), rung.get("arm_order")
            )
        for arm in common.ARMS:
            _verify_pool(rung.get("pooled_by_arm", {}).get(arm), pooled[arm], field=f"rung {boundary} {arm}")
        _verify_cumulative_prefix(
            previous_rows,
            previous_pooled,
            rows,
            pooled,
            boundary=boundary,
        )
        previous_rows = rows
        previous_pooled = pooled
        latest_rows, latest_pooled = rows, pooled
    assert latest_rows is not None and latest_pooled is not None
    pooled_3000 = {arm: _pool(latest_rows[: 3000 * 4], arm) for arm in common.ARMS}
    for arm in common.ARMS:
        _verify_pool(result.get("pooled_by_arm", {}).get(arm), pooled_3000[arm], field=f"result {arm}")
    disposition = _disposition(pooled_3000)
    if result.get("overall_token") != disposition["overall_token"] or result.get("reasons") != disposition["reasons"]:
        raise common.StageCError("single overall token/reason set disagrees with contract")
    if result.get("overall_token") not in {HELD, FALSIFIED}:
        raise common.StageCError("result contains no valid single scientific token")
    if result.get("admission_mapping") != expected_admission_mapping:
        raise common.StageCError("3000 result admission mapping drifted")
    if result.get("execution_mode") == "arm_decoupled":
        _verify_arm_merge_provenance(
            result.get("arm_merge_provenance"), result.get("arm_order")
        )
    closure = _verify_administrative_closure(
        root,
        bindings_sha256=bindings_sha,
        policy_bindings_sha256=common.canonical_sha256(expected_policy_bindings),
        admission_mapping_sha256=common.canonical_sha256(expected_admission_mapping),
        scheduling_addendum_path=str(bindings["scheduling_addendum"]["path"]),
        scheduling_addendum_sha256=str(bindings["scheduling_addendum"]["sha256"]),
    )
    if closure is not None and (completed != 3000 or result.get("overall_token") != HELD):
        raise common.StageCError("administrative closure is valid only for a HELD 3000 root")
    if (
        completed == 3000
        and result.get("overall_token") == HELD
        and closure is None
        and ((root / common.TREE_MANIFEST_NAME).exists() or (root / common.COMPLETE_NAME).exists())
    ):
        raise common.StageCError("sealed HELD root lacks administrative closure receipt")
    if require_tree_seal and (completed == 9000 or result.get("overall_token") == FALSIFIED):
        common.verify_tree_seal(root)
    if require_tree_seal and closure is not None:
        common.verify_tree_seal(root)
    if completed == 9000:
        continuation = common.read_json(root / "continuation-result.json", field="9000 continuation receipt")
        _verify_continuation_result_semantics(continuation)
        authority_record = continuation.get("continuation_authority")
        if not isinstance(authority_record, Mapping):
            raise common.StageCError("9000 continuation lacks authority file binding")
        runner = _physical_runner()
        authority = runner._authenticate_continuation_authority(
            authority_record.get("path"),
            expected_sha256=authority_record.get("sha256"),
            plan_sha256=common.PLAN_SHA256,
            policy_bindings=expected_policy_bindings,
        )
        if (
            result.get("overall_token") != HELD
            or continuation.get("plan_sha256") != common.PLAN_SHA256 or continuation.get("arms") != list(common.ARMS)
            or continuation.get("admission_mapping") != expected_admission_mapping
            or continuation.get("continuation_authority_sha256") != authority["authority_sha256"]
            or continuation.get("owner_notification")
            != {
                "path": authority["owner_notification_path"],
                "sha256": authority["owner_notification_sha256"],
            }
            or continuation.get("result_3000_sha256") != common.file_sha256(root / "result.json")
            or continuation.get("checkpoint_3000_sha256")
            != common.file_sha256(root / "checkpoints/checkpoint-003000.json")
            or authority.get("result_3000_sha256") != common.file_sha256(root / "result.json")
            or authority.get("checkpoint_3000_sha256")
            != common.file_sha256(root / "checkpoints/checkpoint-003000.json")
            or authority.get("bindings_sha256") != bindings_sha
        ):
            raise common.StageCError("9000 continuation authority/result semantics drifted")
        for arm in common.ARMS:
            _verify_pool(continuation.get("pooled_by_arm", {}).get(arm), latest_pooled[arm], field=f"continuation {arm}")
    return {
        "status": "VERIFIED",
        "formal": True,
        "completed_episode": completed,
        "plan_sha256": common.PLAN_SHA256,
        "arms": list(common.ARMS),
        "overall_token": result["overall_token"],
        "reasons": result["reasons"],
        "administrative_closure": closure,
    }


def _verify_boundary_state(
    payload: Mapping[str, object],
    *,
    arm: str,
    boundary: int,
    plan_sha256: str,
    schedule_sha256: str,
    expected_age_state: Mapping[str, object] | None,
) -> None:
    body = dict(payload)
    claimed = body.pop("boundary_state_sha256", None)
    if common.digest(claimed, field="boundary state digest") != common.canonical_sha256(body):
        raise common.StageCError("boundary-state content digest drifted")
    expected_training = {
        "format_version": 1,
        "age_rng_state": expected_age_state,
    }
    replay = body.get("draw_replay")
    if (
        body.get("arm") != arm
        or body.get("episode_index") != boundary
        or body.get("plan_sha256") != plan_sha256
        or body.get("schedule_sha256") != schedule_sha256
        or body.get("rng_library") != "numpy"
        or body.get("rng_version") != np.__version__
        or body.get("environment_training_state") != expected_training
        or not isinstance(replay, Mapping)
        or replay.get("operation") != "integers"
        or replay.get("low") != 0
        or replay.get("high") != 10
        or replay.get("size") != 100
        or replay.get("draws_replayed") != boundary
        or replay.get("arithmetic_advance_used") is not False
    ):
        raise common.StageCError("boundary-state replay identity drifted")


def verify_arm_chunk(
    root: Path,
    bindings_path: Path,
    *,
    arm: str,
    admission_supplement: Path,
    acceptance_bundle: Path,
    runtime_admission: Path,
    continuation_authority: Path | None = None,
    owner_notification_marker: Path | None = None,
) -> dict[str, object]:
    """Independently recompute one chunk's plan, stream, coverage and pools."""

    if root.is_symlink() or not root.is_dir():
        raise common.StageCError("chunk root is unavailable")
    _reject_nonformal(root)
    bindings = common.verify_bindings(bindings_path)
    supplement = common.verify_stage_ab_supplement(
        admission_supplement, bindings_path, bindings
    )
    acceptance = common.verify_acceptance_bundle(
        acceptance_bundle,
        {**bindings, "bindings_sha256": common.file_sha256(bindings_path)},
    )
    bindings = common.materialize_stage_ab(bindings, supplement)
    common.verify_runtime_identity(bindings, chunk_mode=True)
    physical_runner = _physical_runner()
    admission_sha = common.verify_named_sidecar(runtime_admission)
    physical_runner.authenticate_runtime_admission(
        runtime_admission,
        expected_sha256=admission_sha,
        expected_statuses=("PASS_SOURCE_TRAINING_INTEGRITY", "PASS_PLUMBING_INTEGRITY"),
    )
    receipt = common.read_json(root / "chunk-receipt.json", field="chunk receipt")
    if (
        receipt.get("schema") != physical_runner.CHUNK_RECEIPT_SCHEMA
        or receipt.get("status") != "COMPLETE_ARM_CHUNK"
        or receipt.get("formal") is not True
        or receipt.get("arm") != arm
        or receipt.get("execution_mode") != "arm_decoupled"
        or receipt.get("scientific_disposition_emitted") is not False
        or receipt.get("plan_sha256") != common.PLAN_SHA256
        or receipt.get("schedule_sha256") != bindings["scheduling_addendum"]["sha256"]
    ):
        raise common.StageCError("chunk receipt identity drifted")
    forbidden = receipt.get("forbidden_boundary_flags")
    if (
        not isinstance(forbidden, Mapping)
        or set(forbidden) != set(physical_runner.FORBIDDEN_BOUNDARY_FLAGS)
        or any(value is not False for value in forbidden.values())
    ):
        raise common.StageCError("chunk crossed a forbidden boundary")
    start = receipt.get("start_boundary")
    end = receipt.get("end_boundary")
    if type(start) is not int or type(end) is not int or start < 0 or end <= start or start % 100 or end % 100:
        raise common.StageCError("chunk range is not contiguous 100-aligned coverage")
    if end > 9000 or receipt.get("range") != [start + 1, end] or receipt.get("chunk_id") != f"{arm}-{start:06d}-{end:06d}":
        raise common.StageCError("chunk endpoint arithmetic/authority drifted")
    plan = common.read_json(bindings["world_plan"]["path"], field="frozen world plan")
    plan_body = dict(plan)
    plan_body.pop("plan_sha256", None)
    if common.canonical_sha256(plan_body) != common.PLAN_SHA256:
        raise common.StageCError("plan identity did not independently recompute")
    expected_policy = _expected_policy_binding(bindings, arm)
    if receipt.get("policy_binding") != expected_policy:
        raise common.StageCError("chunk policy provenance drifted")
    expected_provenance = {
        "authority_sha256": common.file_sha256(bindings_path),
        "code_manifest_sha256": bindings["code"]["external_manifest_sha256"],
        "configuration_sha256": common.canonical_sha256(bindings["execution"]),
        "tle_sha256": bindings["physical_inputs"]["tle_manifest_sha256"],
        "prereg_sha256": bindings["physical_inputs"]["prereg_sha256"],
        "admission_sha256": admission_sha,
        "stage_ab_supplement_sha256": supplement["supplement_sha256"],
        "acceptance_evidence_sha256": acceptance["acceptance_bundle_sha256"],
        "acceptance_procedure_sha256": bindings["acceptance_procedure"]["sha256"],
    }
    if end > 3000:
        if continuation_authority is None or owner_notification_marker is None:
            raise common.StageCError(
                "post-3000 chunk requires continuation authority and owner-notification marker"
            )
        prefix_root = Path(str(bindings.get("stage_c_output_root", "")))
        prefix_checkpoint = common.read_json(
            prefix_root / "checkpoints/checkpoint-003000.json",
            field="preserved 3000 checkpoint",
        )
        policy_bindings = prefix_checkpoint.get("policy_bindings")
        if not isinstance(policy_bindings, Mapping) or policy_bindings.get(arm) != expected_policy:
            raise common.StageCError("preserved 3000 policy mapping drifted")
        try:
            continuation = physical_runner.authenticate_continuation_chain(
                continuation_authority,
                owner_notification_marker,
                root=prefix_root,
                bindings_sha256=common.file_sha256(bindings_path),
                plan_sha256=common.PLAN_SHA256,
                policy_bindings=policy_bindings,
            )
        except physical_runner.C1C2PhysicalError as error:
            raise common.StageCError(str(error)) from error
        expected_provenance.update({
            "continuation_authority_sha256": continuation["authority_sha256"],
            "owner_notification_sha256": continuation["owner_notification_sha256"],
            "result_3000_sha256": continuation["result_3000_sha256"],
            "checkpoint_3000_sha256": continuation["checkpoint_3000_sha256"],
        })
    if receipt.get("provenance") != expected_provenance:
        raise common.StageCError("chunk full provenance drifted")
    if receipt.get("threads") != {name: 1 for name in common.NUMERICAL_THREAD_ENV}:
        raise common.StageCError("chunk numerical-thread attestation drifted")
    record_index = receipt.get("ordered_episode_records")
    if not isinstance(record_index, list) or receipt.get("ordered_episode_record_digest") != common.canonical_sha256(record_index):
        raise common.StageCError("chunk ordered episode-record digest drifted")
    names = [f"episode-{episode:06d}.json" for episode in range(start + 1, end + 1)]
    paths = sorted((root / "episodes").glob("episode-*.json"))
    if [path.name for path in paths] != names or len(record_index) != len(paths):
        raise common.StageCError("chunk episode coverage is incomplete or duplicated")
    rows: list[Mapping[str, object]] = []
    actual_states: dict[int, Mapping[str, object]] = {}
    for episode, path, index in zip(range(start + 1, end + 1), paths, record_index, strict=True):
        record = common.read_json(path, field=f"chunk episode {episode}")
        body = dict(record)
        claimed = body.pop("record_sha256", None)
        if common.digest(claimed, field="episode record digest") != common.canonical_sha256(body):
            raise common.StageCError("chunk episode record digest drifted")
        row = body.get("receipt")
        state = body.get("resume_state")
        world = plan["worlds"][episode - 1]
        if (
            not isinstance(row, Mapping)
            or row.get("episode_index") != episode
            or row.get("arm") != arm
            or row.get("world_id") != world["world_id"]
            or row.get("world_seed") != world["world_seed"]
            or row.get("field_root_digest") != world["field_root_digest"]
            or row.get("policy_binding") != expected_policy
            or not isinstance(state, Mapping)
            or state.get("episode_index") != episode
            or index != {"episode_index": episode, "sha256": common.file_sha256(path)}
        ):
            raise common.StageCError("chunk episode plan/provenance/state drifted")
        rows.append(row)
        actual_states[episode] = state
    sequence = np.random.SeedSequence(plan["worlds"][0]["world_seed"])
    environment_rng = np.random.default_rng(sequence.spawn(2)[0])
    age_rng = environment_rng.spawn(1)[0]
    states: dict[int, Mapping[str, object]] = {}
    for episode in range(1, end + 1):
        age_rng.integers(0, 10, size=100)
        states[episode] = dict(age_rng.bit_generator.state)
        if episode > start:
            world = plan["worlds"][episode - 1]
            expected_state = {
                "schema": f"{physical_runner.SCHEMA}-resume-state",
                "arm": arm,
                "episode_index": episode,
                "world_id": world["world_id"],
                "world_seed": world["world_seed"],
                "field_root_digest": world["field_root_digest"],
                "plan_sha256": common.PLAN_SHA256,
                "policy_binding": expected_policy,
                "environment_training_state": {
                    "format_version": 1,
                    "age_rng_state": states[episode],
                },
            }
            if actual_states.get(episode) != expected_state:
                raise common.StageCError("chunk actual resume state disagrees with replay")
    start_payload = common.read_json(root / "boundary-start.json", field="chunk start boundary")
    end_payload = common.read_json(root / "boundary-end.json", field="chunk end boundary")
    _verify_boundary_state(
        start_payload,
        arm=arm,
        boundary=start,
        plan_sha256=common.PLAN_SHA256,
        schedule_sha256=bindings["scheduling_addendum"]["sha256"],
        expected_age_state=None if start == 0 else states[start],
    )
    _verify_boundary_state(
        end_payload,
        arm=arm,
        boundary=end,
        plan_sha256=common.PLAN_SHA256,
        schedule_sha256=bindings["scheduling_addendum"]["sha256"],
        expected_age_state=states[end],
    )
    if (
        receipt.get("start_boundary_state_sha256") != start_payload["boundary_state_sha256"]
        or receipt.get("end_boundary_state_sha256") != end_payload["boundary_state_sha256"]
    ):
        raise common.StageCError("chunk receipt boundary hashes drifted")
    checkpoint_paths = sorted((root / "checkpoints").glob("checkpoint-*.json"))
    expected_checkpoint_episodes = list(range(start + 100, end + 1, 100))
    if [path.name for path in checkpoint_paths] != [f"checkpoint-{episode:06d}.json" for episode in expected_checkpoint_episodes]:
        raise common.StageCError("chunk checkpoint cadence/completeness drifted")
    for episode, checkpoint_path in zip(expected_checkpoint_episodes, checkpoint_paths, strict=True):
        checkpoint = physical_runner._read_chunk_checkpoint(checkpoint_path)
        if (
            checkpoint.get("formal") is not True
            or checkpoint.get("arm") != arm
            or checkpoint.get("chunk_id") != receipt["chunk_id"]
            or checkpoint.get("completed_episode") != episode
            or checkpoint.get("resume_state") != actual_states[episode]
            or checkpoint.get("threads") != {name: 1 for name in common.NUMERICAL_THREAD_ENV}
            or checkpoint.get("forbidden_boundary_flags")
            != {name: False for name in physical_runner.FORBIDDEN_BOUNDARY_FLAGS}
        ):
            raise common.StageCError("chunk checkpoint identity/state drifted")
    final_checkpoint = receipt.get("final_checkpoint")
    final_path = root / "checkpoints" / f"checkpoint-{end:06d}.json"
    if (
        not isinstance(final_checkpoint, Mapping)
        or final_checkpoint.get("path") != str(final_path.resolve())
        or final_checkpoint.get("sha256") != common.file_sha256(final_path)
    ):
        raise common.StageCError("chunk final checkpoint binding drifted")
    parent = receipt.get("parent_checkpoint")
    if not isinstance(parent, Mapping):
        raise common.StageCError("chunk parent checkpoint is missing")
    if parent.get("kind") == "authenticated-boundary-table":
        if (
            parent.get("episode_index") != start
            or parent.get("boundary_state_sha256") != start_payload["boundary_state_sha256"]
        ):
            raise common.StageCError("chunk boundary parent checkpoint drifted")
    elif parent.get("kind") in {"arm-chunk-checkpoint", "arm-merge-checkpoint"}:
        parent_path = Path(str(parent.get("path", "")))
        if common.file_sha256(parent_path) != parent.get("sha256"):
            raise common.StageCError("chunk parent checkpoint bytes drifted")
        parent_payload = common.read_json(parent_path, field="chunk parent checkpoint")
        if parent.get("kind") == "arm-chunk-checkpoint":
            parent_payload = physical_runner._read_chunk_checkpoint(parent_path)
        if parent_payload.get("completed_episode") != start or parent_payload.get("resume_state") != start_payload.get("resume_state"):
            raise common.StageCError("chunk parent checkpoint state drifted")
    else:
        raise common.StageCError("chunk parent checkpoint kind drifted")
    attempts = receipt.get("execution_attempts")
    if not isinstance(attempts, list) or not attempts:
        raise common.StageCError("chunk execution-attempt provenance is missing")
    for ordinal, record in enumerate(attempts, 1):
        if not isinstance(record, Mapping) or record.get("attempt") != ordinal:
            raise common.StageCError("chunk execution-attempt index drifted")
        attempt_path = root / "attempts" / str(record.get("path", ""))
        if common.file_sha256(attempt_path) != record.get("sha256"):
            raise common.StageCError("chunk execution-attempt hash drifted")
        attempt = common.read_json(attempt_path, field="chunk execution attempt")
        if attempt.get("attempt") != ordinal or attempt.get("threads") != {name: 1 for name in common.NUMERICAL_THREAD_ENV}:
            raise common.StageCError("chunk execution-attempt attestation drifted")
        if ordinal == 1 and receipt.get("started_utc") != attempt.get("started_utc"):
            raise common.StageCError("chunk original start time was not preserved")
    repair_path = root / "repair-receipt.json"
    if repair_path.exists():
        repair = common.read_json(repair_path, field="chunk repair receipt")
        authority = repair.get("repair_authority")
        if (
            repair.get("status") != "REPAIRED_CHECKPOINT_PUBLICATION"
            or repair.get("chunk_id") != receipt["chunk_id"]
            or repair.get("prefix_episode") != end
            or not isinstance(authority, Mapping)
            or common.file_sha256(str(authority.get("path", ""))) != authority.get("sha256")
            or common.verify_named_sidecar(str(authority.get("path", ""))) != authority.get("sha256")
        ):
            raise common.StageCError("chunk repair authority/receipt drifted")
    pooled = _pool(rows, arm)
    return {
        "status": "VERIFIED_ARM_CHUNK",
        "arm": arm,
        "range": [start + 1, end],
        "plan_sha256": common.PLAN_SHA256,
        "schedule_sha256": bindings["scheduling_addendum"]["sha256"],
        "pooled": pooled,
        "execution_mode": "arm_decoupled",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--arm", choices=common.ARMS)
    parser.add_argument("--admission-supplement", type=Path, required=True)
    parser.add_argument("--acceptance-bundle", type=Path)
    parser.add_argument("--runtime-admission", type=Path)
    parser.add_argument("--continuation-authority", type=Path)
    parser.add_argument("--owner-notification-marker", type=Path)
    args = parser.parse_args(argv)
    try:
        report = (
            verify_arm_chunk(
                args.root, args.bindings, arm=args.arm,
                admission_supplement=args.admission_supplement,
                acceptance_bundle=args.acceptance_bundle,
                runtime_admission=args.runtime_admission,
                continuation_authority=args.continuation_authority,
                owner_notification_marker=args.owner_notification_marker,
            )
            if args.arm is not None
            else verify_finished(args.root, args.bindings, args.admission_supplement)
        )
    except Exception as error:
        print(f"{STOP}: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
