#!/usr/bin/env python3
"""Independent verifier for a finished formal Stage-C root."""

from __future__ import annotations

import argparse
import importlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import stagec_common as common


STOP = "STOP_PHYSICAL_EVALUATION_INTEGRITY"
HELD = "C1C2_DEVELOPMENT_PREDICTION_HELD"
FALSIFIED = "C1C2_DEVELOPMENT_PREDICTION_FALSIFIED"
RECEIPT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-episode-receipt"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-checkpoint"
RUNG_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-rung-receipt"
RESULT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-result"
STATUS = "FIXED_POLICY_EVALUATION"
CONTINUATION_RESULT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-continuation-result"


def _same(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


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


def _verify_formal_admission(
    root: Path,
    bindings: Mapping[str, object],
    expected_policy_bindings: Mapping[str, object],
    bindings_sha256: str,
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
    if (
        payload.get("schema") != f"{_physical_runner().SCHEMA}-formal-admission-v1"
        or payload.get("status") != "FORMAL_STAGE_C_ADMITTED"
        or payload.get("formal") is not True
        or payload.get("integrity_status") != "VERIFIED"
        or payload.get("split") != "TRAIN"
        or payload.get("arms") != list(common.ARMS)
        or payload.get("plan_sha256") != common.PLAN_SHA256
        or payload.get("bindings_sha256") != bindings_sha256
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


def verify_finished(root: Path, bindings_path: Path) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise common.StageCError("finished Stage-C root is unavailable")
    _reject_nonformal(root)
    bindings = common.verify_bindings(bindings_path)
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
        root, bindings, expected_policy_bindings, bindings_sha
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
    if completed == 9000 or result.get("overall_token") == FALSIFIED:
        common.verify_tree_seal(root)
    if completed == 9000:
        continuation = common.read_json(root / "continuation-result.json", field="9000 continuation receipt")
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
            or continuation.get("schema") != CONTINUATION_RESULT_SCHEMA
            or continuation.get("completed_episode") != 9000
            or continuation.get("scientific_disposition_emitted") is not False
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
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_finished(args.root, args.bindings)
    except Exception as error:
        print(f"{STOP}: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
