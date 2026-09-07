#!/usr/bin/env python3
"""Shared fail-closed primitives for the successor launch bundle."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


BUNDLE_REL = Path(".scratch/multi-catfish-v023-c1c2-successor-launch")
SUCCESSOR_REL = Path(".scratch/multi-catfish-v023-c1c2-successor")
FACTORY_REL = Path(".scratch/multi-catfish-v023-c1c2-provider-factory-v3")
RUNNER_REL = Path(".scratch/multi-catfish-v023-two-route-source-training-runner")
TARGET_ADAPTER_REL = Path(".scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py")
BASELINE_ADAPTER_REL = Path(".scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py")
PROTOCOL_REL = Path(
    ".scratch/multi-catfish-v023-five-arm-learner-orchestrator/"
    "v023_five_arm_learner_orchestrator.py"
)
TRAINER_REL = Path(
    ".scratch/multi-catfish-v023-heterogeneous-trainer/"
    "v023_heterogeneous_trainer.py"
)
CONTRACT_NAME = "V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md"
DECLARATION_NAME = "V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md"
MODEL_CONFIG_NAME = "V023-C1C2-SUCCESSOR-MODEL-CONFIG.json"
REVIEW_REL = Path(
    ".scratch/multi-catfish-v023-controller-handoff-20260907/"
    "REVIEW-C1C2-SUCCESSOR-CONTRACT-CODEX-GPT6-ASTRA-2026-09-07.md"
)
BINDINGS_NAME = "V023-C1C2-SUCCESSOR-EXECUTION-BINDINGS.json"
LEARNER_MANIFEST_NAME = "V023-C1C2-SUCCESSOR-LEARNER-MANIFEST.json"
PROVIDER_CONFIG_NAME = "V023-C1C2-SUCCESSOR-PROVIDER-CONFIG.json"
LAUNCH_MANIFEST_NAME = "V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json"
LAUNCH_MANIFEST_SIDECAR = LAUNCH_MANIFEST_NAME + ".sha256"

EXECUTION_BINDINGS_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-execution-bindings-v1"
)
LAUNCH_MANIFEST_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-launch-manifest-v1"
)
LEARNER_MANIFEST_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-learner-manifest-v1"
)
PROVIDER_CONFIG_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-provider-factory-config-v3"
)
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY"
)
TARGET_ROOT = Path("/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8")
TRAIN_SEED = 2927175120652069826
EPOCH_BUDGET = 100
ARM_ORDER = ("FULL2", "DROP_C1", "DROP_C2")
ROUTE_ORDER = ("C1", "C2")
SOURCE_MAP = {
    "FULL2": {"C1": "informed", "C2": "informed"},
    "DROP_C1": {"C1": "neutral", "C2": "informed"},
    "DROP_C2": {"C1": "informed", "C2": "neutral"},
}
EXPECTED_MODEL_CONFIG_SHA256 = (
    "9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d"
)

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
STAGE_A_PLACEHOLDER_RE = re.compile(r"<<BIND_AT_FREEZE:([a-z0-9_]+)>>")
STAGE_A_PLACEHOLDERS = frozenset(
    {
        "r8_manifest_sha256",
        "r8_receipt_sha256",
        "r8_complete_line",
        "factory_v3_manifest_sha256",
        "learner_manifest_sha256",
        "runner_manifest_sha256",
    }
)


class SuccessorLaunchError(RuntimeError):
    """A frozen launch input or output failed authentication."""


def canonical_bytes(value: object) -> bytes:
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
    except (TypeError, ValueError, UnicodeError) as error:
        raise SuccessorLaunchError("value is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)[:-1]).hexdigest()


def file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SuccessorLaunchError(f"required regular file is missing or symlinked: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or DIGEST_RE.fullmatch(value) is None:
        raise SuccessorLaunchError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SuccessorLaunchError(f"canonical JSON repeats key: {key}")
        result[key] = value
    return result


def read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    raw = path.read_bytes() if path.is_file() and not path.is_symlink() else b""
    try:
        payload = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                SuccessorLaunchError(f"{field} contains {token}")
            ),
        )
    except SuccessorLaunchError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise SuccessorLaunchError(f"{field} is not canonical ASCII JSON") from error
    if not isinstance(payload, dict) or raw != canonical_bytes(payload):
        raise SuccessorLaunchError(f"{field} is not a canonical JSON object")
    return payload


def sidecar_path(path: Path) -> Path:
    return path.with_name(path.name + ".sha256")


def verify_sidecar(path: Path) -> str:
    actual = file_sha256(path)
    expected_line = f"{actual}  {path.name}\n"
    sidecar = sidecar_path(path)
    if sidecar.is_symlink() or not sidecar.is_file():
        raise SuccessorLaunchError(f"digest sidecar is missing: {sidecar}")
    try:
        observed = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        raise SuccessorLaunchError(f"digest sidecar is unreadable: {sidecar}") from error
    if observed != expected_line:
        raise SuccessorLaunchError(f"digest sidecar disagrees: {sidecar}")
    return actual


def write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise SuccessorLaunchError(f"refusing to overwrite: {path}")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return hashlib.sha256(payload).hexdigest()


def write_reproducible(path: Path, payload: bytes, *, check: bool) -> str:
    value = hashlib.sha256(payload).hexdigest()
    if check:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise SuccessorLaunchError(f"frozen file drifted: {path}")
    else:
        path.write_bytes(payload)
    return value


def safe_relative(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SuccessorLaunchError(f"{field} must be a nonempty relative path")
    path = Path(value)
    if path.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        raise SuccessorLaunchError(f"{field} is unsafe")
    return path.as_posix()


def directory_files(root: Path, relative_root: Path) -> list[Path]:
    base = root / relative_root
    if base.is_symlink() or not base.is_dir():
        raise SuccessorLaunchError(f"required directory is missing or symlinked: {base}")
    return sorted(
        path.relative_to(root)
        for path in base.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


def discover_mcrl_runtime(root: Path) -> list[Path]:
    """Return the actual project modules loaded by the factory and runner seam."""

    for path in (root / "src", root / FACTORY_REL, root / RUNNER_REL):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    importlib.import_module("v023_c1c2_provider_factory_v3")
    importlib.import_module("v023_two_route_source_training_runner")
    paths: set[Path] = set()
    for module in tuple(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str):
            continue
        try:
            relative = Path(origin).resolve(strict=True).relative_to(root)
        except (OSError, ValueError):
            continue
        if relative.parts[:2] == ("src", "mcrl") and relative.suffix == ".py":
            paths.add(relative)
    if not paths:
        raise SuccessorLaunchError("executing mcrl runtime closure is empty")
    return sorted(paths)


def file_manifest(root: Path, paths: Sequence[Path]) -> dict[str, Any]:
    records = [
        {"path": path.as_posix(), "sha256": file_sha256(root / path)}
        for path in sorted(paths)
    ]
    if not records or len({item["path"] for item in records}) != len(records):
        raise SuccessorLaunchError("code manifest is empty or repeats a path")
    return {"files": records, "manifest_sha256": canonical_sha256(records)}


def assert_stage_a_placeholders(contract_text: str, resolutions: Mapping[str, object]) -> None:
    section_one = contract_text.split("## 2.", 1)[0]
    found = set(STAGE_A_PLACEHOLDER_RE.findall(section_one))
    missing_declarations = STAGE_A_PLACEHOLDERS - found
    unresolved = found - set(resolutions)
    empty = {
        key for key in found if not isinstance(resolutions.get(key), str) or not resolutions[key]
    }
    if missing_declarations or unresolved or empty:
        detail = sorted(missing_declarations | unresolved | empty)
        raise SuccessorLaunchError(
            "stage-A freeze placeholders are missing or unresolved: " + ", ".join(detail)
        )


def reject_forbidden_config(value: object) -> None:
    raw = canonical_bytes(value).decode("ascii")
    forbidden = ("r" + "7", "C" + "3", "q" + "3", "TE" + "ST", "ALL_NEUTRAL_CONTROL", "DROP_C" + "3")
    lowered = raw.lower()
    present = [token for token in forbidden if token.lower() in lowered]
    if present:
        raise SuccessorLaunchError("provider config contains forbidden token(s)")


def validate_no_circular_digest(payload: Mapping[str, object]) -> None:
    forbidden_fields = {
        "launch_manifest_sha256",
        "execution_bindings_sha256",
        "self_sha256",
    }
    found: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if str(key) in forbidden_fields:
                    found.add(str(key))
                visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(payload)
    if found:
        raise SuccessorLaunchError(
            "circular/self digest field is prohibited: " + ", ".join(sorted(found))
        )


def verify_launch_manifest(repo: Path, path: Path) -> dict[str, Any]:
    manifest_sha = verify_sidecar(path)
    payload = read_canonical_json(path, field="successor launch manifest")
    if payload.get("schema") != LAUNCH_MANIFEST_SCHEMA or set(payload) != {
        "schema", "groups", "file_count"
    }:
        raise SuccessorLaunchError("successor launch manifest schema drifted")
    validate_no_circular_digest(payload)
    groups = payload.get("groups")
    if not isinstance(groups, list) or not groups:
        raise SuccessorLaunchError("successor launch manifest groups are missing")
    seen: set[str] = set()
    count = 0
    for group in groups:
        if not isinstance(group, Mapping) or set(group) != {"name", "files", "manifest_sha256"}:
            raise SuccessorLaunchError("successor launch manifest group is malformed")
        files = group["files"]
        if not isinstance(files, list) or not files:
            raise SuccessorLaunchError("successor launch manifest group is empty")
        if canonical_sha256(files) != digest(group["manifest_sha256"], field="group digest"):
            raise SuccessorLaunchError("successor launch manifest group digest disagrees")
        for record in files:
            if not isinstance(record, Mapping) or set(record) != {"path", "sha256"}:
                raise SuccessorLaunchError("successor launch manifest file record is malformed")
            relative = safe_relative(record["path"], field="launch manifest path")
            if relative in seen or Path(relative).name in {LAUNCH_MANIFEST_NAME, LAUNCH_MANIFEST_SIDECAR}:
                raise SuccessorLaunchError("launch manifest repeats itself or a payload path")
            if file_sha256(repo / relative) != digest(record["sha256"], field="file digest"):
                raise SuccessorLaunchError(f"launch manifest file drifted: {relative}")
            seen.add(relative)
            count += 1
    if payload["file_count"] != count:
        raise SuccessorLaunchError("successor launch manifest file count drifted")
    return {"sha256": manifest_sha, "paths": sorted(seen), "payload": payload}
