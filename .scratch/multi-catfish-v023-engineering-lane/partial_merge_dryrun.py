#!/usr/bin/env python3
"""Exercise the real V0.23 C1/C2 merge/seal path on terminal shards.

This is an engineering-only, read-only diagnostic.  It never writes below the
staging root and makes no scientific claim.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping


sys.dont_write_bytecode = True

CLAIM_CEILING = "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"
REPORT_SCHEMA = "multi-catfish-v023-partial-merge-dryrun-v1"
REPORT_NAME = "partial-merge-dryrun-report.json"
CONTROLLER_RELATIVE = Path(
    ".scratch/multi-catfish-v023-c1c2-target-generation-launch/"
    "run_v023_c1c2_targets_server.py"
)
ADAPTER_RELATIVE = Path(
    ".scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py"
)


class PartialMergeDryRunError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_controller(checkout: Path) -> ModuleType:
    """Load the checkout-bound controller without installing a module alias."""

    path = checkout / CONTROLLER_RELATIVE
    if path.is_symlink() or not path.is_file():
        raise PartialMergeDryRunError(f"controller is missing or symlinked: {path}")
    spec = importlib.util.spec_from_file_location(
        "_v023_partial_merge_controller", path
    )
    if spec is None or spec.loader is None:
        raise PartialMergeDryRunError(f"controller is unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_sealer(controller: ModuleType) -> ModuleType:
    path = Path(controller.SEALER)
    if path.is_symlink() or not path.is_file():
        raise PartialMergeDryRunError(f"sealer is missing or symlinked: {path}")
    spec = importlib.util.spec_from_file_location("_v023_partial_merge_sealer", path)
    if spec is None or spec.loader is None:
        raise PartialMergeDryRunError(f"sealer is unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_adapter(checkout: Path) -> ModuleType:
    """Import the checkout's adapter normally so its dataclasses are registered."""

    path = (checkout / ADAPTER_RELATIVE).resolve()
    if path.is_symlink() or not path.is_file():
        raise PartialMergeDryRunError(f"target adapter is missing or symlinked: {path}")
    search = (str(path.parent), str((checkout / "src").resolve()))
    inserted = [entry for entry in search if entry not in sys.path]
    sys.path[:0] = inserted
    try:
        module = importlib.import_module("target_batch_adapter")
    finally:
        for entry in inserted:
            sys.path.remove(entry)
    loaded = Path(module.__file__).resolve()
    if loaded != path:
        raise PartialMergeDryRunError(
            f"target adapter resolved outside checkout: expected={path} actual={loaded}"
        )
    return module


def _exception(error: BaseException) -> dict[str, str]:
    return {"type": type(error).__name__, "text": str(error).replace("\n", " ")}


def _emit(step: Mapping[str, object]) -> None:
    print(json.dumps(step, sort_keys=True, separators=(",", ":")))


def _terminal_receipt(
    controller: ModuleType, staging: Path, key: str
) -> dict[str, Any] | None:
    path = controller._shard_status_path(staging, key, "terminal")
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise PartialMergeDryRunError(f"terminal shard status is not a regular file: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PartialMergeDryRunError(f"terminal shard status is malformed: {path}") from error
    mode, world_text = key.split(":", 1)
    expected = {
        "schema": controller.SHARD_STATUS_SCHEMA,
        "event": "terminal",
        "state": "PASS",
        "mode": mode,
        "world": int(world_text),
        "returncode": 0,
    }
    if raw != controller._canonical(payload) or not isinstance(payload, dict):
        raise PartialMergeDryRunError(f"terminal shard status is not canonical: {path}")
    for field, value in expected.items():
        if payload.get(field) != value:
            raise PartialMergeDryRunError(
                f"terminal shard status disagrees: {key} {field}={payload.get(field)!r}"
            )
    return payload


def _batch_layout(array: object) -> dict[str, object]:
    return {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "c_contiguous": bool(array.flags.c_contiguous),
        "writeable": bool(array.flags.writeable),
    }


def _adapter_layouts(adapter: ModuleType, merged: Path) -> dict[str, object]:
    artifact = adapter.load_completed_target_artifact(merged)
    result: dict[str, object] = {}
    for mode in adapter.TARGET_MODES:
        inputs = artifact.for_mode(mode)
        result[mode] = {
            "C1": {
                field: _batch_layout(getattr(inputs.c1_pair_batch, field))
                for field in (
                    "states",
                    "reference_actions",
                    "candidate_actions",
                    "target_surplus_bits",
                    "action_masks",
                )
            },
            "C2": {
                field: _batch_layout(getattr(inputs.c2_pair_batch, field))
                for field in (
                    "states",
                    "reference_actions",
                    "candidate_actions",
                    "normalized_target_deltas",
                    "action_masks",
                )
            },
        }
    return result


def run(args: argparse.Namespace) -> int:
    checkout = Path(args.checkout).resolve()
    staging = Path(args.staging).resolve()
    scratch = Path(args.scratch).resolve()
    if checkout.is_symlink() or not checkout.is_dir():
        raise PartialMergeDryRunError(f"checkout is missing or symlinked: {checkout}")
    if staging.is_symlink() or not staging.is_dir():
        raise PartialMergeDryRunError(f"staging is missing or symlinked: {staging}")
    if scratch.exists() or scratch.is_symlink():
        raise PartialMergeDryRunError(f"scratch root must be absent: {scratch}")
    if scratch.is_relative_to(staging):
        raise PartialMergeDryRunError("scratch root must be outside the staging tree")
    scratch.mkdir(parents=True)

    steps: list[dict[str, object]] = []
    identities: list[dict[str, object]] = []
    failed = False

    def record(name: str, status: str, **fields: object) -> None:
        nonlocal failed
        row = {"step": name, "status": status, **fields}
        steps.append(row)
        _emit(row)
        if status == "FAIL":
            failed = True

    try:
        controller = _load_controller(checkout)
        expected_schedule = controller._expected_schedule(args)
        ordered = sorted(expected_schedule, key=controller._shard_sort_key)
        if len(ordered) != 16:
            raise PartialMergeDryRunError(
                f"authenticated full schedule has {len(ordered)} shards, expected 16"
            )
        record("authenticated_schedule", "PASS", shards=ordered)
    except Exception as error:
        record("authenticated_schedule", "FAIL", exception=_exception(error))
        controller = None
        expected_schedule = {}
        ordered = []

    passed: dict[str, Path] = {}
    if controller is not None:
        for key in ordered:
            mode, world_text = key.split(":", 1)
            root = staging / mode / f"world-{world_text}"
            try:
                terminal = _terminal_receipt(controller, staging, key)
                if terminal is None:
                    continue
                receipt = controller._read_receipt(root)
                controller._validate_shard(key, root, receipt, expected_schedule[key])
                receipt_sha = controller._sha(root / "receipt.json")
                manifest_sha = controller._sha(root / "MANIFEST.sha256")
                if terminal.get("receipt_sha256") != receipt_sha:
                    raise PartialMergeDryRunError(
                        f"terminal receipt digest disagrees with shard: {key}"
                    )
                if terminal.get("manifest_sha256") != manifest_sha:
                    raise PartialMergeDryRunError(
                        f"terminal manifest digest disagrees with shard: {key}"
                    )
                passed[key] = root
                identity = {
                    "shard": key,
                    "shard_dir": str(root.resolve()),
                    "receipt_sha256": receipt_sha,
                    "manifest_sha256": manifest_sha,
                }
                identities.append(identity)
                record(f"authenticate_shard:{key}", "PASS", input_identity=identity)
            except Exception as error:
                record(
                    f"authenticate_shard:{key}",
                    "FAIL",
                    shard_dir=str(root.resolve()),
                    exception=_exception(error),
                )
        record(
            "terminal_subset",
            "PASS" if passed else "FAIL",
            available=len(passed),
            scheduled=len(ordered),
            shards=sorted(passed, key=controller._shard_sort_key),
        )

    merged = scratch / "merged-output"
    if controller is not None and passed:
        if set(passed) != set(expected_schedule):
            guard_output = scratch / "full-schedule-guard-probe"
            try:
                controller._merge(
                    passed, guard_output, expected_schedule=expected_schedule
                )
            except Exception as error:
                guard_text = "mode/world shard set disagrees with the authenticated schedule"
                status = (
                    "EXPECTED_FULL_SCHEDULE_GUARD"
                    if str(error) == guard_text
                    else "FAIL"
                )
                record("full_schedule_merge_guard", status, exception=_exception(error))
                if guard_output.exists() or guard_output.is_symlink():
                    record(
                        "full_schedule_guard_no_write",
                        "FAIL",
                        exception={
                            "type": "UnexpectedOutput",
                            "text": f"guard probe created output: {guard_output}",
                        },
                    )
            else:
                record(
                    "full_schedule_merge_guard",
                    "FAIL",
                    exception={
                        "type": "MissingGuard",
                        "text": "partial shard set unexpectedly passed the full schedule",
                    },
                )
        else:
            record("full_schedule_merge_guard", "PASS", message="full schedule present")

        subset_schedule = {key: expected_schedule[key] for key in passed}
        try:
            controller._merge(passed, merged, expected_schedule=subset_schedule)
            manifest_entries = (merged / "MANIFEST.sha256").read_text(
                encoding="ascii"
            ).splitlines()
            record(
                "controller_merge_and_manifest",
                "PASS",
                merged_shards=len(passed),
                manifest_entries=len(manifest_entries),
            )
        except Exception as error:
            record(
                "controller_merge_and_manifest", "FAIL", exception=_exception(error)
            )

    if merged.is_dir():
        try:
            sealer = _load_sealer(controller)
            manifest_sha = sealer.seal(merged)
            record(
                "sealer_field_and_manifest_checks",
                "PASS",
                manifest_sha256=manifest_sha,
            )
        except Exception as error:
            record(
                "sealer_field_and_manifest_checks", "FAIL", exception=_exception(error)
            )

    if (merged / "COMPLETE").is_file():
        try:
            adapter = _load_adapter(checkout)
            layouts = _adapter_layouts(adapter, merged)
            record("adapter_dataset_concatenation", "PASS", layouts=layouts)
        except Exception as error:
            record(
                "adapter_dataset_concatenation", "FAIL", exception=_exception(error)
            )

    if controller is not None and passed:
        try:
            for identity in identities:
                key = str(identity["shard"])
                root = passed[key]
                receipt = controller._read_receipt(root)
                controller._validate_shard(key, root, receipt, expected_schedule[key])
                if controller._sha(root / "receipt.json") != identity["receipt_sha256"]:
                    raise PartialMergeDryRunError(f"input receipt changed: {key}")
                if controller._sha(root / "MANIFEST.sha256") != identity["manifest_sha256"]:
                    raise PartialMergeDryRunError(f"input manifest changed: {key}")
            record("input_integrity_after_dryrun", "PASS", shards=len(identities))
        except Exception as error:
            record("input_integrity_after_dryrun", "FAIL", exception=_exception(error))

    verdict = "FAIL" if failed else "PASS"
    report = {
        "schema": REPORT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_output": False,
        "checkout": str(checkout),
        "staging": str(staging),
        "scratch": str(scratch),
        "input_identities": identities,
        "steps": steps,
        "verdict": verdict,
    }
    report_path = scratch / REPORT_NAME
    report_path.write_bytes(_canonical(report))
    print(f"PARTIAL_MERGE_DRYRUN_{verdict}")
    return 0 if verdict == "PASS" else 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--staging", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--materialization-dir", type=Path, required=True)
    p.add_argument("--tle-root", type=Path, required=True)
    p.add_argument("--prereg", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--manifest-digest", type=Path, required=True)
    p.add_argument("--execution-addendum", type=Path, required=True)
    p.add_argument("--python", type=Path, default=Path(sys.executable))
    p.add_argument("--users", type=int, default=100)
    return p


if __name__ == "__main__":
    try:
        raise SystemExit(run(parser().parse_args()))
    except Exception as error:
        print(f"PARTIAL_MERGE_DRYRUN_FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
