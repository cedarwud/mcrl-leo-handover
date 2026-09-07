#!/usr/bin/env python3
"""Independent verifier for a finished formal Stage-C root."""

from __future__ import annotations

import argparse
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


def _same(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def _reject_nonformal(root: Path) -> None:
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


def verify_episode_rows(rows: Sequence[Mapping[str, object]], plan: Mapping[str, object], completed: int) -> dict[str, dict[str, object]]:
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


def verify_finished(root: Path, bindings_path: Path) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise common.StageCError("finished Stage-C root is unavailable")
    _reject_nonformal(root)
    bindings = common.verify_bindings(bindings_path)
    code_sha, _entries = common.verify_code_manifest()
    if bindings.get("code", {}).get("external_manifest_sha256") != code_sha:
        raise common.StageCError("finished root code closure differs from bindings")
    if str(root.resolve()) != bindings.get("stage_c_output_root"):
        raise common.StageCError("finished root differs from frozen Stage-C output root")
    marker = common.read_json(root / "FORMAL-RUN.json", field="formal root marker")
    if marker.get("formal") is not True or marker.get("arms") != list(common.ARMS):
        raise common.StageCError("formal root marker is absent or drifted")
    if marker.get("bindings_sha256") != common.file_sha256(bindings_path):
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
    result_like = sorted(path.name for path in root.glob("*result*.json"))
    if result_like != ["result.json"]:
        raise common.StageCError("finished root must contain exactly one terminal result.json")
    completed = 9000 if (root / "continuation-009000.json").is_file() else 3000
    checkpoint_names = [path.name for path in sorted((root / "checkpoints").glob("checkpoint-*.json"))]
    rung_names = [path.name for path in sorted((root / "rungs").glob("rung-*.json"))]
    expected_names = [f"checkpoint-{index:06d}.json" for index in range(100, completed + 1, 100)]
    if checkpoint_names != expected_names or rung_names != [name.replace("checkpoint", "rung") for name in expected_names]:
        raise common.StageCError("100-episode checkpoint/rung cadence is incomplete or ahead")
    latest_rows: list[Mapping[str, object]] | None = None
    latest_pooled: dict[str, dict[str, object]] | None = None
    for boundary in range(100, completed + 1, 100):
        checkpoint = _read_checkpoint(root / "checkpoints" / f"checkpoint-{boundary:06d}.json")
        if (
            checkpoint.get("schema") != CHECKPOINT_SCHEMA or checkpoint.get("status") != STATUS
            or checkpoint.get("completed_episode") != boundary or checkpoint.get("arms") != list(common.ARMS)
            or checkpoint.get("checkpoint_every") != 100 or checkpoint.get("plan_sha256") != common.PLAN_SHA256
        ):
            raise common.StageCError(f"checkpoint identity drifted at {boundary}")
        rows = checkpoint.get("receipts")
        if not isinstance(rows, list):
            raise common.StageCError(f"checkpoint receipts missing at {boundary}")
        pooled = verify_episode_rows(rows, plan, boundary)
        rung = common.read_json(root / "rungs" / f"rung-{boundary:06d}.json", field=f"rung {boundary}")
        if (
            rung.get("schema") != RUNG_SCHEMA or rung.get("completed_episode") != boundary
            or rung.get("plan_sha256") != common.PLAN_SHA256 or rung.get("arms") != list(common.ARMS)
            or rung.get("scientific_disposition_emitted") is not False
        ):
            raise common.StageCError(f"rung receipt identity drifted at {boundary}")
        for arm in common.ARMS:
            _verify_pool(rung.get("pooled_by_arm", {}).get(arm), pooled[arm], field=f"rung {boundary} {arm}")
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
    if completed == 9000:
        continuation = common.read_json(root / "continuation-009000.json", field="9000 continuation receipt")
        authority_binding_path = root / "CONTINUATION-AUTHORITY.json"
        authority_binding = common.read_json(authority_binding_path, field="continuation authority binding")
        if (
            result.get("overall_token") != HELD or continuation.get("formal") is not True
            or continuation.get("completed_episode") != 9000 or continuation.get("new_scientific_token_emitted") is not False
            or continuation.get("plan_sha256") != common.PLAN_SHA256 or continuation.get("arms") != list(common.ARMS)
            or authority_binding.get("formal") is not True
            or authority_binding.get("plan_sha256") != common.PLAN_SHA256
            or continuation.get("continuation_authority_binding_sha256") != common.file_sha256(authority_binding_path)
            or continuation.get("continuation_authority_sha256") != authority_binding.get("continuation_authority_sha256")
            or continuation.get("owner_notification_sha256") != authority_binding.get("owner_notification_sha256")
            or continuation.get("owner_acknowledgement_sha256") != authority_binding.get("owner_acknowledgement_sha256")
            or continuation.get("result_3000_sha256") != common.file_sha256(root / "result.json")
            or authority_binding.get("result_3000_sha256") != common.file_sha256(root / "result.json")
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
