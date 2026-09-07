#!/usr/bin/env python3
"""Independent arithmetic and decision verification for the V0.21 fast screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


CONTRACT_SHA256 = "9630e6c51784a8d8f36a7eeea34a2c3b611d9ee4b87f95be157a6adbc75e3c66"
SCHEMA = "multi-catfish-mcrl-v021-expected-zr-fast-screen-v1"
ARMS = ("B", "N", "E", "R", "P")


class VerificationError(RuntimeError):
    pass


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _same_float(left: object, right: object) -> bool:
    return float(left).hex() == float(right).hex()


def _metrics(rows: list[Mapping[str, object]]) -> dict[str, object]:
    bits = sum(float(row["bits"]) for row in rows)
    energy = sum(float(row["energy_j"]) for row in rows)
    served = sum(int(row["served_users"]) for row in rows)
    total = sum(int(row["total_users"]) for row in rows)
    if not all(math.isfinite(value) for value in (bits, energy)) or energy <= 0.0:
        raise VerificationError("arm totals are invalid")
    return {
        "bits": bits,
        "energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_fraction": served / total,
        "served_users": served,
        "total_users": total,
        "per_draw_ee_bits_per_j": [float(row["ee_bits_per_j"]) for row in rows],
    }


def verify(result_path: Path) -> dict[str, object]:
    payload = json.loads(result_path.read_text(encoding="ascii"))
    if payload.get("schema") != SCHEMA:
        raise VerificationError("result schema mismatch")
    if payload.get("contract_sha256") != CONTRACT_SHA256:
        raise VerificationError("contract hash mismatch")
    stored_hash = payload.get("result_sha256")
    unhashed = dict(payload)
    unhashed.pop("result_sha256", None)
    if stored_hash != _canonical_sha256(unhashed):
        raise VerificationError("result payload hash mismatch")
    if any(
        payload.get(field) is not False
        for field in ("test_split_opened", "learner_update", "episode_training")
    ):
        raise VerificationError("claim ceiling was violated")
    if payload.get("integration_draws") != 8 or payload.get("evaluation_draws") != 8:
        raise VerificationError("draw counts drifted")
    integration = payload.get("integration_field_root_digests")
    evaluation = payload.get("evaluation_field_root_digests")
    if not isinstance(integration, list) or not isinstance(evaluation, list):
        raise VerificationError("field receipts are absent")
    if len(integration) != 8 or len(evaluation) != 8:
        raise VerificationError("field receipt counts drifted")
    if len(set(integration + evaluation)) != 16:
        raise VerificationError("integration/evaluation roots are not disjoint")

    raw_rows = payload.get("per_draw")
    stored_metrics = payload.get("metrics")
    if not isinstance(raw_rows, Mapping) or not isinstance(stored_metrics, Mapping):
        raise VerificationError("arm rows or metrics are absent")
    recomputed: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        rows = raw_rows.get(arm)
        expected = stored_metrics.get(arm)
        if not isinstance(rows, list) or len(rows) != 8 or not isinstance(expected, Mapping):
            raise VerificationError(f"{arm} rows are malformed")
        if [int(row["draw"]) for row in rows] != list(range(8)):
            raise VerificationError(f"{arm} draw order drifted")
        for row in rows:
            if not _same_float(
                row["ee_bits_per_j"], float(row["bits"]) / float(row["energy_j"])
            ):
                raise VerificationError(f"{arm} per-draw EE is inconsistent")
        actual = _metrics(rows)
        for key, value in actual.items():
            if isinstance(value, list):
                if len(value) != len(expected[key]) or any(
                    not _same_float(left, right)
                    for left, right in zip(value, expected[key], strict=True)
                ):
                    raise VerificationError(f"{arm} metric {key} drifted")
            elif isinstance(value, float):
                if not _same_float(value, expected[key]):
                    raise VerificationError(f"{arm} metric {key} drifted")
            elif value != expected[key]:
                raise VerificationError(f"{arm} metric {key} drifted")
        recomputed[arm] = actual

    r_rows = raw_rows["R"]
    b_rows = raw_rows["B"]
    positive_draws = sum(
        float(r["ee_bits_per_j"]) > float(b["ee_bits_per_j"])
        for r, b in zip(r_rows, b_rows, strict=True)
    )
    if positive_draws != payload.get("positive_r_vs_b_evaluation_draws"):
        raise VerificationError("positive draw count drifted")
    criteria = {
        "mechanics_pass": bool(payload["mechanics"]["passed"]),
        "r_exposure_positive": int(payload["r_exposure_users"]) > 0,
        "r_gt_b": float(recomputed["R"]["ratio_of_sums_ee_bits_per_j"])
        > float(recomputed["B"]["ratio_of_sums_ee_bits_per_j"]),
        "r_gt_n": float(recomputed["R"]["ratio_of_sums_ee_bits_per_j"])
        > float(recomputed["N"]["ratio_of_sums_ee_bits_per_j"]),
        "r_gt_p": float(recomputed["R"]["ratio_of_sums_ee_bits_per_j"])
        > float(recomputed["P"]["ratio_of_sums_ee_bits_per_j"]),
        "service_guard": float(recomputed["R"]["served_fraction"])
        >= float(recomputed["B"]["served_fraction"]) - 0.001,
        "positive_draws_at_least_6_of_8": positive_draws >= 6,
    }
    if criteria != payload.get("criteria"):
        raise VerificationError("stored criteria differ from recomputation")
    decision = (
        "GO_FULL_EXPECTED_ZR_GATE"
        if all(criteria.values())
        else "STOP_EXPECTED_ZR_FAST"
    )
    if decision != payload.get("decision"):
        raise VerificationError("stored decision differs from frozen rule")
    return {
        "schema": "multi-catfish-mcrl-v021-fast-screen-independent-verification-v1",
        "source_result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "source_payload_sha256": stored_hash,
        "contract_sha256": CONTRACT_SHA256,
        "metrics": recomputed,
        "criteria": criteria,
        "decision": decision,
        "passed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise VerificationError(f"refusing to overwrite {args.output}")
    report = verify(args.result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(_canonical_bytes(report))
    print(f"{report['decision']}: independent verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
