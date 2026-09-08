"""Canonical serialization and write-once artifact helpers for Stage C.

The helpers in this module deliberately do not depend on ``physics_v025``.
That package is still moving; Stage C authenticates values at its boundary and
keeps the adapter replaceable.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
from typing import Any


class StageCContractError(RuntimeError):
    """A fail-closed Stage C contract check failed."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the one admitted JSON representation."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise StageCContractError("value is not canonical finite JSON") from error


def canonical_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise StageCContractError(f"artifact is not a regular file: {source}")
    digest = sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def float_hex(value: float | int) -> str:
    number = float(value)
    if not (number == number and abs(number) != float("inf")):
        raise StageCContractError("receipt floats must be finite")
    return number.hex()


def parse_float_hex(value: object, *, field: str) -> float:
    if not isinstance(value, str):
        raise StageCContractError(f"{field} must be a hexadecimal float string")
    try:
        number = float.fromhex(value)
    except ValueError as error:
        raise StageCContractError(f"{field} is not a hexadecimal float") from error
    if not (number == number and abs(number) != float("inf")):
        raise StageCContractError(f"{field} must be finite")
    if number.hex() != value:
        raise StageCContractError(f"{field} is not canonical float.hex output")
    return number


def _write_once_bytes(path: Path, payload: bytes) -> str:
    """Publish complete bytes without an overwrite race, then make read-only."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise StageCContractError(f"refusing to overwrite artifact: {path}")
    temporary = path.parent / f".{path.name}.{secrets.token_hex(12)}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise StageCContractError(f"refusing to overwrite artifact: {path}") from error
        path.chmod(0o444)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return sha256(payload).hexdigest()


def write_once_with_sha256(path: str | Path, payload: bytes) -> str:
    """Write one immutable artifact and its immediate immutable SHA sidecar."""

    destination = Path(path)
    digest = _write_once_bytes(destination, payload)
    _write_once_bytes(
        destination.with_name(destination.name + ".sha256"),
        f"{digest}  {destination.name}\n".encode("ascii"),
    )
    return digest


def write_once_json(path: str | Path, value: Any) -> str:
    return write_once_with_sha256(path, canonical_json_bytes(value) + b"\n")


def verify_sha256_sidecar(path: str | Path) -> str:
    source = Path(path)
    sidecar = source.with_name(source.name + ".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise StageCContractError(f"missing SHA-256 sidecar: {sidecar}")
    try:
        parts = sidecar.read_text(encoding="ascii").strip().split()
    except OSError as error:
        raise StageCContractError(f"cannot read SHA-256 sidecar: {sidecar}") from error
    if len(parts) != 2 or parts[1] != source.name:
        raise StageCContractError(f"malformed SHA-256 sidecar: {sidecar}")
    expected = parts[0]
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise StageCContractError(f"malformed SHA-256 digest: {sidecar}")
    actual = file_sha256(source)
    if actual != expected:
        raise StageCContractError(f"SHA-256 mismatch for {source}")
    return actual


def read_verified_json(path: str | Path) -> Any:
    source = Path(path)
    verify_sha256_sidecar(source)
    try:
        encoded = source.read_bytes()
        payload = json.loads(encoded.decode("ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StageCContractError(f"cannot read canonical JSON: {source}") from error
    if encoded != canonical_json_bytes(payload) + b"\n":
        raise StageCContractError(f"noncanonical JSON artifact: {source}")
    return payload


__all__ = [
    "StageCContractError",
    "canonical_json_bytes",
    "canonical_sha256",
    "file_sha256",
    "float_hex",
    "parse_float_hex",
    "read_verified_json",
    "verify_sha256_sidecar",
    "write_once_json",
    "write_once_with_sha256",
]
