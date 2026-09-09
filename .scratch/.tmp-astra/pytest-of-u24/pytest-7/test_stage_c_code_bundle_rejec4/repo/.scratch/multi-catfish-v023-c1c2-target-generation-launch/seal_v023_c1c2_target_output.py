#!/usr/bin/env python3
"""Verify and write the write-once COMPLETE marker for target outputs."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-v1"
HERE = Path(__file__).resolve().parent
GENERATOR = (
    HERE.parent
    / "multi-catfish-v023-c1c2-target-generation"
    / "generate_v023_c1c2_targets.py"
)


class SealError(RuntimeError):
    pass


def _load_generator():
    name = "mcrl_v023_c1c2_target_generation_controller_schedule"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, GENERATOR)
    if spec is None or spec.loader is None:
        raise SealError(f"target generator is unavailable: {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(name, None)
        raise SealError("target generator contract module failed to import") from error
    return module


# The producer owns the receipt contract; the sealer must not carry a second
# literal that can drift from generator output.
CLAIM_CEILING = _load_generator().CLAIM_CEILING


def sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SealError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise SealError(f"refusing to overwrite: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def seal(root: Path) -> str:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise SealError(f"output root is missing or symlinked: {root}")
    complete = root / "COMPLETE"
    failed = root / "FAILED"
    if complete.exists() or complete.is_symlink() or failed.exists() or failed.is_symlink():
        raise SealError("output already has a terminal marker")
    receipt_path = root / "receipt.json"
    manifest_path = root / "MANIFEST.sha256"
    if receipt_path.is_symlink() or manifest_path.is_symlink() or not receipt_path.is_file() or not manifest_path.is_file():
        raise SealError("generator receipt or manifest is missing/symlinked")
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    if receipt.get("schema") != SCHEMA or receipt.get("status") != "TARGETS_MATERIALIZED_TRAIN":
        raise SealError("target receipt schema/status is not TRAIN target generation")
    if receipt.get("claim_ceiling") != CLAIM_CEILING:
        raise SealError("target receipt claim ceiling drifted")
    if any(receipt.get("training_or_replay_write") is not False for _ in (0,)):
        raise SealError("target receipt permits training/replay writes")
    for field in ("learner_update", "test_split_opened"):
        if receipt.get(field) is not False:
            raise SealError(f"target receipt permits {field}")
    listed: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64 or parts[1] in listed:
            raise SealError("malformed target manifest")
        relative = Path(parts[1])
        if relative.is_absolute() or ".." in relative.parts or relative.name in {"MANIFEST.sha256", "COMPLETE", "FAILED"}:
            raise SealError("unsafe target manifest path")
        listed[relative.as_posix()] = parts[0]
    if "receipt.json" not in listed:
        raise SealError("target manifest omits receipt")
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    } - {"MANIFEST.sha256", "COMPLETE", "FAILED"}
    if actual_files != set(listed):
        raise SealError(f"target manifest closure drifted: extra={sorted(actual_files - set(listed))}, missing={sorted(set(listed) - actual_files)}")
    for relative, expected in listed.items():
        if sha256_file(root / relative) != expected:
            raise SealError(f"target file hash drifted: {relative}")
    manifest_sha = sha256_file(manifest_path)
    _write_once(complete, f"{manifest_sha}  MANIFEST.sha256\n".encode("ascii"))
    return manifest_sha


if __name__ == "__main__":
    try:
        print(seal(Path(sys.argv[1])))
    except Exception as error:
        print(f"V023_C1C2_TARGET_SEAL_BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
