#!/usr/bin/env python3
"""Verify merged C2 V0.3 history against an uninterrupted reference run.

The verifier permits only real-clock duration/provenance variance and IEEE-754
aggregate summation noise.  It does not convert this engineering equivalence
into an EE-efficacy or training-trend claim.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_temporal_fork_segment_merge as merger  # noqa: E402
from verify_c2_v03_resume_parity import exact_differences  # noqa: E402


SCHEMA = "c2-v03-merged-history-parity-receipt-v1"
CLAIM_CEILING = (
    "bounded artifact-history and training-result reconstruction equivalence only; "
    "no EE efficacy, training trend, Chapter-5 result, or deployment authorization"
)
HISTORY_ARTIFACTS = merger.LIST_ARTIFACTS + ("run-telemetry.json",)
AUDIT_CHRONOLOGY_HASH_FIELDS = (
    "chronology_receipt_sha256",
    "admission_plan_sha256",
    "admission_proof_sha256",
    "transition_sha256",
    "primitive_sequence_sha256",
    "joint_record_sha256",
)
MAIN_CHRONOLOGY_HASH_FIELDS = (
    "primitive_sequence_sha256",
    "transition_sha256",
    "joint_record_sha256",
)


class HistoryParityError(RuntimeError):
    """The merged history is not equivalent under the frozen variance policy."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            ),
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise HistoryParityError(f"cannot read valid JSON {path}: {error}") from error


def _normalized_pair(
    artifact: str,
    reference: Any,
    merged: Any,
) -> tuple[Any, Any, str]:
    left = copy.deepcopy(reference)
    right = copy.deepcopy(merged)
    marker = "<allowed-real-clock-provenance>"
    if artifact == "episode-logs.json":
        for side in (left, right):
            for row in side:
                row["telemetry"]["c2"]["forecast_wall_time_s"] = marker
        policy = "per-episode forecast wall time excluded"
    elif artifact == "c2-training-receipts.json":
        for side in (left, right):
            for receipt in side:
                for candidate in receipt["candidate_rows"]:
                    candidate["elapsed_s"] = marker
        policy = "per-candidate forecast elapsed time excluded"
    elif artifact == "main-update-receipts.json":
        for side in (left, right):
            for receipt in side:
                c2 = receipt.get("c2_training")
                if isinstance(c2, dict) and c2.get("live_committed") is True:
                    for name in MAIN_CHRONOLOGY_HASH_FIELDS:
                        c2[name] = marker
        policy = "three chronology-derived C2 transaction hashes excluded"
    elif artifact == "c2-option-chronology-audits.json":
        for side in (left, right):
            for audit in side:
                chronology = audit["chronology_receipt"]
                for name in merger.CHRONOLOGY_TIME_FIELDS:
                    chronology[name] = marker
                for name in AUDIT_CHRONOLOGY_HASH_FIELDS:
                    audit[name] = marker
        policy = "four monotonic timestamps and six bound hashes excluded"
    elif artifact == "run-telemetry.json":
        left["c2"]["forecast_wall_time_s"] = marker
        right["c2"]["forecast_wall_time_s"] = marker
        policy = "aggregate forecast wall time excluded; numeric sums use tight tolerance"
    else:
        raise HistoryParityError(f"unknown history artifact {artifact}")
    return left, right, policy


def _verify_merge_receipt(merged_dir: Path) -> Mapping[str, Any]:
    receipt_path = merged_dir / "merge-receipt.json"
    receipt = _load_json(receipt_path)
    if not isinstance(receipt, Mapping):
        raise HistoryParityError("merge receipt must be a mapping")
    if receipt.get("schema") != merger.SCHEMA or receipt.get("status") != "PASS":
        raise HistoryParityError("merged history lacks a PASS merge receipt")
    hashes = receipt.get("merged_artifact_sha256")
    if not isinstance(hashes, Mapping) or set(hashes) != set(HISTORY_ARTIFACTS):
        raise HistoryParityError("merge receipt artifact hash inventory drifted")
    for name in HISTORY_ARTIFACTS:
        if _sha256_file(merged_dir / name) != hashes[name]:
            raise HistoryParityError(f"merged artifact hash drifted: {name}")
    return receipt


def verify(reference_dir: Path, merged_dir: Path) -> dict[str, Any]:
    reference_dir = Path(reference_dir).expanduser().resolve()
    merged_dir = Path(merged_dir).expanduser().resolve()
    reference_segment = merger._load_segment(reference_dir)
    merge_receipt = _verify_merge_receipt(merged_dir)
    expected_range = {
        "start_episode": reference_segment["start"],
        "episodes_completed": reference_segment["end"],
        "episode_count": reference_segment["end"] - reference_segment["start"],
    }
    if merge_receipt.get("episode_range") != expected_range:
        raise HistoryParityError("merged and reference episode ranges differ")
    if merge_receipt.get("config") != reference_segment["config"]:
        raise HistoryParityError("merged and reference configs differ")
    if merge_receipt.get("authority_identity") != reference_segment["authority"]:
        raise HistoryParityError("merged and reference authority identities differ")

    comparisons: dict[str, Any] = {}
    for name in HISTORY_ARTIFACTS:
        reference = _load_json(reference_dir / name)
        merged = _load_json(merged_dir / name)
        raw_differences = exact_differences(reference, merged, limit=256)
        left, right, policy = _normalized_pair(name, reference, merged)
        if name == "run-telemetry.json":
            try:
                merger._compare_payloads(left, right, field="run-telemetry")
            except merger.SegmentMergeError as error:
                raise HistoryParityError(str(error)) from error
            normalized_differences: list[str] = []
            comparison_mode = "tight-numeric-semantic"
        else:
            normalized_differences = exact_differences(left, right, limit=256)
            if normalized_differences:
                raise HistoryParityError(
                    f"unexpected {name} differences: {normalized_differences[:4]}"
                )
            comparison_mode = "normalized-exact"
        comparisons[name] = {
            "status": "PASS",
            "comparison_mode": comparison_mode,
            "variance_policy": policy,
            "raw_difference_count_capped": len(raw_differences),
            "unexpected_difference_count": len(normalized_differences),
        }

    reference_telemetry = _load_json(reference_dir / "run-telemetry.json")
    merged_telemetry = _load_json(merged_dir / "run-telemetry.json")
    reference_ee = float(reference_telemetry["main"]["ratio_of_sums_ee_bits_per_j"])
    merged_ee = float(merged_telemetry["main"]["ratio_of_sums_ee_bits_per_j"])
    relative_error = abs(reference_ee - merged_ee) / max(abs(reference_ee), 1.0)
    if not math.isfinite(relative_error) or relative_error > 1e-12:
        raise HistoryParityError("merged Main EE exceeds the numeric tolerance")

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "reference_run": {
            "path": str(reference_dir),
            "status_sha256": _sha256_file(reference_dir / "status.json"),
        },
        "merged_history": {
            "path": str(merged_dir),
            "merge_receipt_sha256": _sha256_file(merged_dir / "merge-receipt.json"),
        },
        "episode_range": expected_range,
        "artifact_comparisons": comparisons,
        "main_ratio_of_sums_ee": {
            "reference_bits_per_j": reference_ee,
            "merged_bits_per_j": merged_ee,
            "relative_error": relative_error,
            "status": "PASS",
            "meaning": "numeric reconstruction parity only, not an efficacy comparison",
        },
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--merged-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    payload = verify(args.reference_dir, args.merged_dir)
    if args.output is None:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite parity receipt: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
