#!/usr/bin/env python3
"""Create-only directory reservation and receipt-last publication for R7."""

from __future__ import annotations

import ctypes
import errno
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


INCOMPLETE_MARKER = ".R7-INCOMPLETE.json"
AT_FDCWD = -100
RENAME_NOREPLACE = 1


def acquire_evaluation_lock(path: Path, *, marker: Mapping[str, Any]) -> Path:
    lock = Path(path).expanduser().resolve()
    lock.parent.mkdir(parents=True, exist_ok=True)
    marker_payload = dict(marker)
    reserved = {"schema", "status", "created_utc", "pid"}
    if reserved & set(marker_payload):
        raise ValueError("R7 evaluation lock marker uses a reserved ownership field")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise FileExistsError(f"R7 evaluation lock already exists: {lock}") from error
    payload = {
        "schema": "multi-catfish-mcrl-c2-v03a-r7-evaluation-lock-v1",
        "status": "ACTIVE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        **marker_payload,
    }
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return lock


def release_evaluation_lock(path: Path, *, expected_marker: Mapping[str, Any]) -> None:
    """Release only the lock created by this process for the expected work item."""

    lock = Path(path).expanduser().resolve()
    try:
        payload = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"R7 evaluation lock is unreadable: {lock}") from error
    expected = dict(expected_marker)
    if {"schema", "status", "created_utc", "pid"} & set(expected):
        raise ValueError("R7 evaluation lock expectation uses a reserved ownership field")
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema")
        != "multi-catfish-mcrl-c2-v03a-r7-evaluation-lock-v1"
        or payload.get("status") != "ACTIVE"
        or payload.get("pid") != os.getpid()
        or any(payload.get(key) != value for key, value in expected.items())
    ):
        raise RuntimeError("refusing to release an R7 evaluation lock owned by another work item")
    lock.unlink()


def _rename_noreplace(source: Path, destination: Path) -> None:
    """Atomically publish one file or directory without replacing a peer."""

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "renameat2 is required for R7 publication")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        AT_FDCWD,
        os.fsencode(source),
        AT_FDCWD,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            str(destination),
        )


def reserve_output_directory(
    output: Path, *, marker: Mapping[str, Any]
) -> tuple[Path, Path]:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    ).resolve()
    created_output = False
    try:
        output.mkdir(parents=False, exist_ok=False)
        created_output = True
        marker_path = output / INCOMPLETE_MARKER
        descriptor = os.open(
            marker_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(dict(marker), stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if created_output:
            try:
                output.rmdir()
            except OSError:
                pass
        raise
    return output, staging


def publish_receipt_last(
    *, staging: Path, output: Path, receipt_name: str
) -> None:
    staging = Path(staging).resolve()
    output = Path(output).resolve()
    receipt = staging / receipt_name
    if not receipt.is_file():
        raise FileNotFoundError(f"R7 publication receipt is missing: {receipt}")
    existing = {child.name for child in output.iterdir()}
    if existing != {INCOMPLETE_MARKER}:
        raise FileExistsError("reserved R7 output was modified before publication")
    staged_names = {child.name for child in staging.iterdir()}
    if receipt_name not in staged_names:
        raise FileNotFoundError(f"R7 publication receipt is missing: {receipt}")
    marker_path = output / INCOMPLETE_MARKER
    marker_payload = json.loads(marker_path.read_text(encoding="utf-8"))
    if not isinstance(marker_payload, dict):
        raise ValueError("R7 reservation marker is malformed")
    marker_payload["expected_entries"] = sorted(staged_names)
    marker_path.write_text(
        json.dumps(marker_payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    published_names: set[str] = set()
    for child in sorted(staging.iterdir(), key=lambda path: path.name):
        if child.name == receipt_name:
            continue
        _rename_noreplace(child, output / child.name)
        published_names.add(child.name)
    if {child.name for child in output.iterdir()} != {
        INCOMPLETE_MARKER,
        *published_names,
    }:
        raise FileExistsError("reserved R7 output gained foreign bytes during publication")
    _rename_noreplace(receipt, output / receipt_name)
    if {child.name for child in output.iterdir()} != {
        INCOMPLETE_MARKER,
        receipt_name,
        *published_names,
    }:
        raise FileExistsError("reserved R7 output changed before commit")
    staging.rmdir()


def finalize_publication(*, output: Path, receipt_name: str) -> None:
    """Remove the incomplete marker only after every external gate is clear."""

    output = Path(output).resolve()
    marker_path = output / INCOMPLETE_MARKER
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("R7 publication marker is unreadable") from error
    expected = marker.get("expected_entries") if isinstance(marker, Mapping) else None
    if (
        not isinstance(expected, list)
        or receipt_name not in expected
        or any(not isinstance(name, str) or not name for name in expected)
        or {child.name for child in output.iterdir()}
        != {INCOMPLETE_MARKER, *expected}
    ):
        raise RuntimeError("R7 publication contents drifted before finalization")
    marker_path.unlink()


def abort_reserved_output(*, staging: Path, output: Path) -> None:
    """Discard private staging while preserving all visible output bytes."""

    shutil.rmtree(Path(staging), ignore_errors=True)


__all__ = [
    "INCOMPLETE_MARKER",
    "_rename_noreplace",
    "acquire_evaluation_lock",
    "abort_reserved_output",
    "finalize_publication",
    "publish_receipt_last",
    "release_evaluation_lock",
    "reserve_output_directory",
]
