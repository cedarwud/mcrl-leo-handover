#!/usr/bin/env python3
"""Independent receipt verifier for the frozen V0.20 repriced C3 gate.

This script reads completed JSON receipts only.  It imports no simulator or
learner code, opens no split, and performs no optimization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


WORLDS = (2026121501, 2026121502, 2026121503, 2026121504)
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = ("BASE", "EXACT_ZR", "NOMINAL_ZR")
CHECKPOINTS = {
    2026092101: "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc",
    2026092102: "bb45bed30465f8be0ea9a1463c3b6e958d8f8b90cf11b4cd8e5d56a71f4b7057",
    2026092103: "32b5accfa1595ff19ddc11779402b5c86e115b883d04c6c5cbf90434ee32d44c",
}
CONTRACT_SHA256 = "8587537e0c4790b383b62680748b21ecffb89550849814e50043d035cd918759"
FIT_SHA256 = "4657a1f758fa83c92deb631231431abf6bae586c050abfffc9f7e06963d9029a"
RUNNER_SHA256 = "e3add6909ac665e3d6330e62e499250f9995d6f98eeaed396812073328f53a1e"
FIELD_COMPONENT = "MCRL_V020_REPRICED_C3_GATE_V1"
KEYED_FADING_VERSION = "keyed-branch-independent-v1"
CLAIM_CEILING = "TRAIN_MATCHED_GATE_NO_Q3_LEARNER_NO_TEST_NO_EFFICACY"
SERVICE_MARGIN = 0.001
BASE_SCHEMA = "multi-catfish-mcrl-v020-repriced-c3-lambda-confound-gate-v1"
SHARD_SCHEMA = f"{BASE_SCHEMA}-shard"
RESULT_SCHEMA = f"{BASE_SCHEMA}-result"


class VerificationError(RuntimeError):
    """A frozen identity, receipt, or recomputation check failed."""


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise VerificationError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> object:
        raise VerificationError(f"non-finite JSON constant {value} in {path}")

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise VerificationError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            path.read_text(encoding="ascii"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"invalid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise VerificationError(f"JSON root is not an object: {path}")
    return payload


def expected_field_digest(world: int) -> str:
    root_payload = json.dumps(
        [KEYED_FADING_VERSION, FIELD_COMPONENT, world],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    root_key = hashlib.sha256(root_payload).hexdigest()
    return hashlib.sha256(root_key.encode("utf-8")).hexdigest()


def require_false(mapping: Mapping[str, object], name: str, where: Path | str) -> None:
    if mapping.get(name) is not False:
        raise VerificationError(f"{name} is not literal false in {where}")


def require_true(mapping: Mapping[str, object], name: str, where: Path | str) -> None:
    if mapping.get(name) is not True:
        raise VerificationError(f"{name} is not literal true in {where}")


def pool(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    opportunities = sum(int(row["served_opportunities"]) for row in rows)
    exposure = sum(int(row["action_exposure"]) for row in rows)
    if len(rows) == 0 or bits <= 0.0 or energy <= 0.0 or opportunities <= 0:
        raise VerificationError("cannot pool malformed rows")
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_opportunities": opportunities,
        "served_fraction": served / opportunities,
        "action_exposure": exposure,
    }


def relative(treatment: Mapping[str, object], base: Mapping[str, object]) -> float:
    return (
        float(treatment["ratio_of_sums_ee_bits_per_j"])
        / float(base["ratio_of_sums_ee_bits_per_j"])
        - 1.0
    )


def contrast(
    indexed: Mapping[tuple[int, str, int], Mapping[str, object]], arm: str
) -> dict[str, object]:
    base = pool([indexed[(world, "BASE", lineage)] for world in WORLDS for lineage in LINEAGES])
    treatment = pool([indexed[(world, arm, lineage)] for world in WORLDS for lineage in LINEAGES])
    by_world = {
        str(world): relative(
            pool([indexed[(world, arm, lineage)] for lineage in LINEAGES]),
            pool([indexed[(world, "BASE", lineage)] for lineage in LINEAGES]),
        )
        for world in WORLDS
    }
    by_lineage = {
        str(lineage): relative(
            pool([indexed[(world, arm, lineage)] for world in WORLDS]),
            pool([indexed[(world, "BASE", lineage)] for world in WORLDS]),
        )
        for lineage in LINEAGES
    }
    delta = relative(treatment, base)
    positive_worlds = sum(value > 0.0 for value in by_world.values())
    positive_lineages = sum(value > 0.0 for value in by_lineage.values())
    service_noninferior = (
        float(treatment["served_fraction"])
        >= float(base["served_fraction"]) - SERVICE_MARGIN
    )
    passed = bool(
        delta > 0.0
        and positive_lineages == 3
        and positive_worlds >= 3
        and service_noninferior
        and int(treatment["action_exposure"]) > 0
    )
    return {
        "arm": arm,
        "base": base,
        "treatment": treatment,
        "relative_delta_ee": delta,
        "by_world_relative_delta_ee": by_world,
        "by_lineage_relative_delta_ee": by_lineage,
        "positive_world_count": positive_worlds,
        "positive_lineage_count": positive_lineages,
        "service_noninferior": service_noninferior,
        "passed": passed,
    }


def verify(run_root: Path) -> dict[str, object]:
    run_root = run_root.resolve()
    if run_root.is_symlink() or not run_root.is_dir():
        raise VerificationError(f"missing regular run directory: {run_root}")
    shard_paths = sorted((run_root / "shards").glob("*/shard.json"))
    if len(shard_paths) != 36:
        raise VerificationError(f"expected 36 shard receipts, found {len(shard_paths)}")

    indexed: dict[tuple[int, str, int], Mapping[str, object]] = {}
    shard_hashes: set[str] = set()
    runner_hashes: set[str] = set()
    q_hashes: dict[tuple[int, str], set[str]] = {}
    for path in shard_paths:
        payload = read_json(path)
        if payload.get("schema") != SHARD_SCHEMA:
            raise VerificationError(f"stale shard schema: {path}")
        if payload.get("contract_sha256") != CONTRACT_SHA256:
            raise VerificationError(f"contract drift in shard: {path}")
        if payload.get("fit_merged_file_sha256") != FIT_SHA256:
            raise VerificationError(f"Q1/Q2 fit drift in shard: {path}")
        if payload.get("claim_ceiling") != CLAIM_CEILING:
            raise VerificationError(f"claim ceiling drift in shard: {path}")
        for name in ("test_split_opened", "learner_update", "episode_training"):
            require_false(payload, name, path)
        row = payload.get("row")
        if not isinstance(row, Mapping) or payload.get("row_sha256") != canonical_sha256(row):
            raise VerificationError(f"row digest mismatch: {path}")
        key = (int(row["world_seed"]), str(row["arm"]), int(row["lineage"]))
        if key in indexed:
            raise VerificationError(f"duplicate shard identity: {key}")
        if key != (int(payload["world"]), str(payload["arm"]), int(payload["lineage"])):
            raise VerificationError(f"payload/row identity mismatch: {path}")
        if payload.get("checkpoint_sha256") != CHECKPOINTS[key[2]]:
            raise VerificationError(f"checkpoint mismatch: {path}")
        if payload.get("runner_file_sha256") != RUNNER_SHA256:
            raise VerificationError(f"runner hash mismatch: {path}")
        if row.get("split") != "TRAIN_DEVELOPMENT":
            raise VerificationError(f"split drift: {path}")
        for name in ("test_split_opened", "learner_update", "episode_training"):
            require_false(row, name, path)
        require_true(row, "mechanics_passed", path)
        require_true(row, "compatibility_proof_passed", path)
        if int(row.get("users", -1)) != 100 or int(row.get("steps", -1)) != 10:
            raise VerificationError(f"episode extent drift: {path}")
        if int(row.get("served_opportunities", -1)) != 1000:
            raise VerificationError(f"served opportunity drift: {path}")
        if int(row.get("initialization_seed", -1)) != key[2]:
            raise VerificationError(f"lineage seed drift: {path}")
        expected_q2_seed = {2026092101: 2026108101, 2026092102: 2026108102, 2026092103: 2026108103}[key[2]]
        if int(payload.get("q2_initialization_seed", expected_q2_seed)) != expected_q2_seed:
            raise VerificationError(f"outer Q2 seed drift: {path}")
        if int(row.get("q2_initialization_seed", -1)) != expected_q2_seed:
            raise VerificationError(f"row Q2 seed drift: {path}")
        bits = float(row["total_bits"])
        energy = float(row["total_energy_j"])
        ee = float(row["ratio_of_sums_ee_bits_per_j"])
        served = int(row["served_user_steps"])
        if not all(math.isfinite(value) for value in (bits, energy, ee)) or bits <= 0.0 or energy <= 0.0:
            raise VerificationError(f"non-finite/non-positive endpoint: {path}")
        if not 0 <= served <= 1000:
            raise VerificationError(f"served count out of range: {path}")
        if not math.isclose(ee, bits / energy, rel_tol=1e-14, abs_tol=1e-9):
            raise VerificationError(f"row EE arithmetic mismatch: {path}")
        if not math.isclose(float(row["served_fraction"]), served / 1000.0, rel_tol=0.0, abs_tol=1e-15):
            raise VerificationError(f"served fraction arithmetic mismatch: {path}")
        exposure = int(row["action_exposure"])
        if (key[1] == "BASE" and exposure != 0) or (key[1] != "BASE" and exposure < 0):
            raise VerificationError(f"invalid action exposure: {path}")

        steps = row.get("per_step")
        if not isinstance(steps, list) or len(steps) != 10:
            raise VerificationError(f"per-step record is incomplete: {path}")
        for index, step in enumerate(steps):
            if not isinstance(step, Mapping) or int(step.get("step_index", -1)) != index:
                raise VerificationError(f"step identity drift: {path} step {index}")
            for vector_name in ("reference_actions", "selected_actions"):
                vector = step.get(vector_name)
                if not isinstance(vector, list) or len(vector) != 100:
                    raise VerificationError(f"{vector_name} shape drift: {path} step {index}")
                if any(isinstance(action, bool) or not isinstance(action, int) or not 0 <= action <= 27 for action in vector):
                    raise VerificationError(f"{vector_name} value drift: {path} step {index}")
            mechanics = step.get("mechanics")
            if not isinstance(mechanics, Mapping):
                raise VerificationError(f"missing step mechanics: {path} step {index}")
            for name in (
                "live_state_and_rng_unchanged",
                "common_native_mask",
                "relational_state_verified",
                "exact_measurement_mask_equal",
                "compatibility_reconstruction_exact",
                "opening_service_gate_equal",
                "q1_surface_finite",
                "learned_q2_surface_finite",
                "nominal_surface_finite",
                "native_action_vector",
                "passed",
            ):
                require_true(mechanics, name, f"{path} step {index}")
            if key[1] == "EXACT_ZR":
                require_true(mechanics, "joint_support_required_passed", f"{path} step {index}")
        if not math.isclose(
            math.fsum(float(step["total_bits"]) for step in steps), bits, rel_tol=1e-14, abs_tol=1e-3
        ):
            raise VerificationError(f"per-step bits do not reconstruct row: {path}")
        if not math.isclose(
            math.fsum(float(step["total_energy_j"]) for step in steps), energy, rel_tol=1e-14, abs_tol=1e-9
        ):
            raise VerificationError(f"per-step energy does not reconstruct row: {path}")
        if sum(int(step["served_user_steps"]) for step in steps) != served:
            raise VerificationError(f"per-step service does not reconstruct row: {path}")
        if sum(int(step["action_exposure"]) for step in steps) != exposure:
            raise VerificationError(f"per-step exposure does not reconstruct row: {path}")
        for head in ("q1", "q2"):
            before = str(row[f"{head}_parameter_sha256_before"])
            after = str(row[f"{head}_parameter_sha256_after"])
            if before != after:
                raise VerificationError(f"{head.upper()} mutated: {path}")
            q_hashes.setdefault((key[2], head), set()).add(before)
        indexed[key] = row
        shard_hashes.add(file_sha256(path))
        runner_hashes.add(str(payload.get("runner_file_sha256")))

    expected = {(world, arm, lineage) for world in WORLDS for arm in ARMS for lineage in LINEAGES}
    if set(indexed) != expected:
        raise VerificationError("shards do not form the frozen rectangular panel")
    if len(runner_hashes) != 1 or "None" in runner_hashes:
        raise VerificationError("shards do not share one runner hash")
    if any(len(values) != 1 for values in q_hashes.values()):
        raise VerificationError("a frozen Q parameter hash varies across rows")
    for world in WORLDS:
        rows = [indexed[(world, arm, lineage)] for arm in ARMS for lineage in LINEAGES]
        if len({str(row["initial_world_sha256"]) for row in rows}) != 1:
            raise VerificationError(f"initial world mismatch for {world}")
        field_digests = {str(row["field_root_digest"]) for row in rows}
        if len(field_digests) != 1:
            raise VerificationError(f"keyed field mismatch for {world}")
        if field_digests != {expected_field_digest(world)}:
            raise VerificationError(f"keyed field root is not the frozen component/world digest for {world}")

    exact = contrast(indexed, "EXACT_ZR")
    nominal = contrast(indexed, "NOMINAL_ZR")
    decision = (
        "REDESIGN_R3_TARGET"
        if not exact["passed"]
        else "GO_Q3_SOURCE_AND_LEARNER"
        if nominal["passed"]
        else "REVISE_NOMINAL_Q3"
    )
    pooled = {
        arm: pool([indexed[(world, arm, lineage)] for world in WORLDS for lineage in LINEAGES])
        for arm in ARMS
    }

    result_path = run_root / "result" / "result.json"
    result = read_json(result_path)
    if result.get("schema") != RESULT_SCHEMA or result.get("decision") != decision:
        raise VerificationError("recorded result schema/decision disagrees with recomputation")
    if result.get("contract_sha256") != CONTRACT_SHA256 or result.get("fit_merged_file_sha256") != FIT_SHA256:
        raise VerificationError("recorded result input digest drifted")
    if result.get("field_component") != FIELD_COMPONENT:
        raise VerificationError("recorded keyed-field component drifted")
    if result.get("pooled_by_arm") != pooled:
        raise VerificationError("recorded pooled arm table disagrees with recomputation")
    if result.get("contrasts") != {"EXACT_ZR": exact, "NOMINAL_ZR": nominal}:
        raise VerificationError("recorded contrasts disagree with recomputation")
    for name in ("test_split_opened", "learner_update", "episode_training"):
        require_false(result, name, result_path)
    recorded_result_digest = result.get("result_sha256")
    unsigned = dict(result)
    unsigned.pop("result_sha256", None)
    if recorded_result_digest != canonical_sha256(unsigned):
        raise VerificationError("result canonical digest mismatch")
    receipt_hashes = {str(item["sha256"]) for item in result.get("shard_receipts", [])}
    if receipt_hashes != shard_hashes or len(result.get("shard_receipts", [])) != 36:
        raise VerificationError("result shard hash closure disagrees with fetched shards")

    seal = read_json(run_root / "result" / "result-seal.json")
    if seal.get("result_file_sha256") != file_sha256(result_path):
        raise VerificationError("result file seal mismatch")
    if seal.get("result_sha256") != recorded_result_digest:
        raise VerificationError("canonical result seal mismatch")

    log_paths = sorted((run_root / "logs").glob("*.log"))
    if len(log_paths) != 36:
        raise VerificationError(f"expected 36 shard logs, found {len(log_paths)}")
    for log_path in log_paths:
        text = log_path.read_text(encoding="utf-8", errors="strict")
        if "Traceback (most recent call last)" in text or "TEST" in text.upper() or "learner update" in text.lower():
            raise VerificationError(f"forbidden text in shard log: {log_path}")
        if "EE=" not in text or "elapsed=" not in text:
            raise VerificationError(f"incomplete shard log: {log_path}")

    return {
        "status": "PASS_INDEPENDENT_RECEIPT_VERIFICATION",
        "decision": decision,
        "runner_file_sha256": next(iter(runner_hashes)),
        "pooled_by_arm": pooled,
        "contrasts": {"EXACT_ZR": exact, "NOMINAL_ZR": nominal},
        "test_split_opened": False,
        "learner_update": False,
        "episode_training": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.run_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
