#!/usr/bin/env python3
"""Seal the failed V0.5 controlled-tape expansion as diagnostic evidence.

This command never opens target values.  It authenticates the completed
shard envelopes, inventories the deterministic fail-closed logs, and writes
one canonical receipt that forbids using the incomplete batch for learning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping


PREPARE_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-source-prepare-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-source-shard-v1"
RECEIPT_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-support-failure-v1"
CLAIM_CEILING = "DIAGNOSTIC_ONLY_NO_LEARNING_NO_TRAINING_NO_TEST_NO_EE_EFFICACY"
Q13_SEEDS = (2026092101, 2026092102, 2026092103)
EXPECTED_ROWS_PER_SHARD = 27
EXPECTED_SHARDS = 48
EXPECTED_FAILURES = {
    "main-anchor-10": ("main", None, 10, 3, 15),
    "q13-2026092101-anchor-00": ("q13", 2026092101, 0, 3, 19),
    "q13-2026092101-anchor-07": ("q13", 2026092101, 7, 1, 5),
    "q13-2026092102-anchor-01": ("q13", 2026092102, 1, 3, 27),
    "q13-2026092102-anchor-10": ("q13", 2026092102, 10, 3, 15),
    "q13-2026092103-anchor-01": ("q13", 2026092103, 1, 3, 27),
    "q13-2026092103-anchor-10": ("q13", 2026092103, 10, 3, 15),
}
FAILURE_PATTERN = re.compile(
    r"ControlledTapeContractError: candidate_slot_tables\[(\d+)]\[(\d+)] "
    r"physical key is missing; matches=\[\]"
)


class SupportFailureSealError(RuntimeError):
    """The incomplete controlled-tape batch does not match its evidence."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise SupportFailureSealError("payload is not finite canonical JSON") from error


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)[:-1]).hexdigest()


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SupportFailureSealError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_canonical_json(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise SupportFailureSealError(f"expected a regular JSON file: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SupportFailureSealError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise SupportFailureSealError(f"JSON is not canonical: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def _write_once(path: Path, payload: Mapping[str, object]) -> str:
    if path.exists() or path.is_symlink():
        raise SupportFailureSealError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_bytes(dict(payload))
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as error:
        raise SupportFailureSealError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(raw).hexdigest()


def _expected_entries() -> tuple[tuple[str, str, int | None, int], ...]:
    rows: list[tuple[str, str, int | None, int]] = []
    for anchor in range(12):
        rows.append((f"main-anchor-{anchor:02d}", "main", None, anchor))
    for seed in Q13_SEEDS:
        for anchor in range(12):
            rows.append((f"q13-{seed}-anchor-{anchor:02d}", "q13", seed, anchor))
    return tuple(rows)


def _authenticate_shard(
    path: Path,
    *,
    policy: str,
    seed: int | None,
    anchor: int,
) -> dict[str, object]:
    value, file_sha = _read_canonical_json(path)
    body = dict(value)
    claimed = body.pop("shard_sha256", None)
    if (
        value.get("schema") != SHARD_SCHEMA
        or value.get("status") != "CONTROLLED_SOURCE_SHARD_COMPLETE"
        or value.get("tape_policy") != policy
        or value.get("initialization_seed") != seed
        or value.get("anchor_index") != anchor
        or value.get("row_count") != EXPECTED_ROWS_PER_SHARD
        or not isinstance(value.get("rows"), list)
        or len(value["rows"]) != EXPECTED_ROWS_PER_SHARD
        or value.get("training_run") is not False
        or value.get("test_split_opened") is not False
        or value.get("held_out_ee_evaluated") is not False
        or claimed != _canonical_sha256(body)
    ):
        raise SupportFailureSealError(f"completed shard failed authentication: {path}")
    # Target payloads remain opaque; this seal records only the envelope.
    return {
        "name": path.stem,
        "file_sha256": file_sha,
        "shard_sha256": claimed,
        "row_count": EXPECTED_ROWS_PER_SHARD,
        "tape_policy": policy,
        "initialization_seed": seed,
        "anchor_index": anchor,
    }


def _authenticate_failure_log(
    path: Path,
    *,
    stem: str,
    policy: str,
    seed: int | None,
    anchor: int,
) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SupportFailureSealError(f"missing regular failure log: {path}")
    text = path.read_text(encoding="utf-8")
    matches = FAILURE_PATTERN.findall(text)
    if len(matches) != 1:
        raise SupportFailureSealError(f"failure log is not an exact support failure: {path}")
    offset, user = (int(item) for item in matches[0])
    expected = EXPECTED_FAILURES.get(stem)
    if expected != (policy, seed, anchor, offset, user):
        raise SupportFailureSealError(f"failure identity drifted: {path}")
    if "Traceback (most recent call last):" not in text:
        raise SupportFailureSealError(f"failure log lacks traceback: {path}")
    return {
        "name": stem,
        "log_file_sha256": _file_sha256(path),
        "tape_policy": policy,
        "initialization_seed": seed,
        "anchor_index": anchor,
        "candidate_offset": offset,
        "nonfocal_user": user,
        "failure": "TAPED_PHYSICAL_ACTION_MISSING_FROM_CANDIDATE_SUPPORT",
    }


def build_receipt(source_dir: Path) -> dict[str, object]:
    root = source_dir.resolve()
    if source_dir.is_symlink() or not root.is_dir():
        raise SupportFailureSealError("source_dir must be a regular directory")
    prepare, prepare_file_sha = _read_canonical_json(root / "prepare.json")
    if (
        prepare.get("schema") != PREPARE_SCHEMA
        or prepare.get("anchor_count") != 12
        or prepare.get("sibling_count_per_policy_view") != 324
        or prepare.get("training_run") is not False
        or prepare.get("test_split_opened") is not False
        or prepare.get("held_out_ee_evaluated") is not False
    ):
        raise SupportFailureSealError("prepare receipt failed authentication")

    shard_dir = root / "shards"
    log_dir = root / "logs"
    actual_json = {path.stem for path in shard_dir.glob("*.json") if path.is_file()}
    actual_tmp = tuple(sorted(path.name for path in shard_dir.glob("*.tmp")))
    if actual_tmp:
        raise SupportFailureSealError("orphan temporary shards exist")

    completed: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for stem, policy, seed, anchor in _expected_entries():
        shard_path = shard_dir / f"{stem}.json"
        log_path = log_dir / f"{stem}.log"
        if stem in EXPECTED_FAILURES:
            if shard_path.exists() or shard_path.is_symlink():
                raise SupportFailureSealError(f"failed shard unexpectedly exists: {shard_path}")
            failures.append(
                _authenticate_failure_log(
                    log_path,
                    stem=stem,
                    policy=policy,
                    seed=seed,
                    anchor=anchor,
                )
            )
        else:
            completed.append(
                _authenticate_shard(
                    shard_path,
                    policy=policy,
                    seed=seed,
                    anchor=anchor,
                )
            )

    expected_completed = {item[0] for item in _expected_entries()} - set(EXPECTED_FAILURES)
    if actual_json != expected_completed:
        raise SupportFailureSealError("shard directory contains missing or unexpected JSON files")
    if len(completed) != 41 or len(failures) != 7:
        raise SupportFailureSealError("controlled support failure cardinality drifted")

    body: dict[str, object] = {
        "schema": RECEIPT_SCHEMA,
        "status": "CONTROLLED_TAPE_NATIVE_SUPPORT_INVALID",
        "claim_ceiling": CLAIM_CEILING,
        "disposition": {
            "completed_shards": "DIAGNOSTICS_ONLY",
            "failed_shards": "POSITIVITY_FAILURE_EVIDENCE",
            "learning_use": "FORBIDDEN",
            "retry_same_program": "FORBIDDEN_DETERMINISTIC_FAILURE",
            "test_split": "UNOPENED",
        },
        "reason": (
            "the focal intervention changes branch state and legal support, so a "
            "reference-taped nonfocal physical action is not always representable "
            "in the candidate branch"
        ),
        "prepare_file_sha256": prepare_file_sha,
        "prepare_sha256": prepare.get("prepare_sha256"),
        "expected_shard_count": EXPECTED_SHARDS,
        "completed_shard_count": len(completed),
        "failed_shard_count": len(failures),
        "persisted_row_count": sum(int(item["row_count"]) for item in completed),
        "expected_row_count": EXPECTED_SHARDS * EXPECTED_ROWS_PER_SHARD,
        "completed_shards": completed,
        "support_failures": failures,
        "target_values_inspected": False,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    body["receipt_sha256"] = _canonical_sha256(body)
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    args = parser.parse_args()
    receipt = build_receipt(args.source_dir)
    file_sha = _write_once(args.output_file, receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "completed_shard_count": receipt["completed_shard_count"],
                "failed_shard_count": receipt["failed_shard_count"],
                "output_file_sha256": file_sha,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
