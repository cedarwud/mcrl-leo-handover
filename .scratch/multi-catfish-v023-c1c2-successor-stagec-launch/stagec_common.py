#!/usr/bin/env python3
"""Shared fail-closed primitives for the formal successor Stage-B/C bundle."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import stat
import tempfile
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHYSICAL = REPO / ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation"
BASELINE = REPO / ".scratch/multi-catfish-v023-baseline-adapter"
SOURCE_RUNNER = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
CONTRACT = REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md"
DECLARATION = REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md"
PREREG = REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")
BASELINE_CHECKPOINT = REPO / "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"
BASELINE_STATUS = BASELINE_CHECKPOINT.with_name("status.json")
BASELINE_CHECKPOINT_SHA256 = "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
PLAN_SHA256 = "866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb"
FIELD_COMPONENT = "MCRL_V020_REPRICED_C3_GATE_V1"
ARMS = ("FULL2", "DROP_C1", "DROP_C2", "BASELINE")
LEARNED_ARMS = ARMS[:3]
PAUSES = (100, 500, 1500, 3000)
BINDINGS_NAME = "V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json"
CODE_MANIFEST_NAME = "V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256"
CODE_PIN_NAME = "V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST-FROZEN.sha256"
SCHEMA_BINDINGS = "multi-catfish-mcrl-v023-c1c2-successor-stagec-execution-bindings-v1"
FORMAL_CLAIM = "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_PHYSICAL_EVALUATION_NO_C3_NO_TEST_NO_EFFICACY"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class StageCError(RuntimeError):
    """A formal Stage-B/C authentication boundary failed."""


def digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise StageCError(f"{field} must be a lowercase SHA-256")
    return value


def regular_file(path: str | Path, *, field: str) -> Path:
    candidate = Path(path)
    try:
        info = candidate.lstat()
    except OSError as error:
        raise StageCError(f"{field} is missing: {candidate}") from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise StageCError(f"{field} is not a regular non-symlink file: {candidate}")
    return candidate


def file_sha256(path: str | Path, *, field: str = "file") -> str:
    source = regular_file(path, field=field)
    result = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise StageCError("canonical mappings require string keys")
        return {key: _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise StageCError(f"value is not canonical JSON: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StageCError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: str | Path, *, field: str) -> dict[str, Any]:
    source = regular_file(path, field=field)
    try:
        value = json.loads(
            source.read_text(encoding="ascii"), object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(StageCError(f"nonfinite JSON: {token}")),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise StageCError(f"{field} is not strict ASCII JSON") from error
    if not isinstance(value, dict):
        raise StageCError(f"{field} must be a JSON object")
    return value


def write_once(path: str | Path, payload: object, *, newline: bool = True) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise StageCError(f"refusing to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(payload) + (b"\n" if newline else b"")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            raise StageCError(f"concurrent publication: {target}") from error
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_digest_sidecar(path: str | Path) -> Path:
    source = regular_file(path, field="sidecar source")
    sidecar = source.with_name(source.name + ".sha256")
    if sidecar.exists() or sidecar.is_symlink():
        raise StageCError(f"refusing to overwrite sidecar: {sidecar}")
    raw = f"{file_sha256(source)}  {source.name}\n".encode("ascii")
    descriptor = -1
    try:
        descriptor = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise StageCError(f"refusing to overwrite sidecar: {sidecar}") from error
    finally:
        if descriptor != -1:
            os.close(descriptor)
    return sidecar


def verify_named_sidecar(path: str | Path) -> str:
    source = regular_file(path, field="sidecar source")
    sidecar = regular_file(source.with_name(source.name + ".sha256"), field="digest sidecar")
    fields = sidecar.read_text(encoding="ascii").strip().split()
    if len(fields) != 2 or fields[1] != source.name:
        raise StageCError(f"malformed digest sidecar: {sidecar}")
    expected = digest(fields[0], field=f"{source.name} sidecar digest")
    if file_sha256(source) != expected:
        raise StageCError(f"digest sidecar mismatch: {source}")
    return expected


def parse_sha256_manifest(path: str | Path, *, root: Path) -> dict[str, str]:
    manifest = regular_file(path, field="SHA-256 manifest")
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\x00]+)", line)
        if match is None:
            raise StageCError(f"malformed manifest line: {line!r}")
        declared, relative_raw = match.groups()
        relative = Path(relative_raw)
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_raw:
            raise StageCError(f"unsafe manifest path: {relative_raw}")
        if relative_raw in entries:
            raise StageCError(f"duplicate manifest entry: {relative_raw}")
        target = root / relative
        if file_sha256(target, field=f"manifest member {relative_raw}") != declared:
            raise StageCError(f"manifest member drifted: {relative_raw}")
        entries[relative_raw] = declared
    if not entries:
        raise StageCError("SHA-256 manifest is empty")
    return entries


def verify_code_manifest(repo: Path = REPO) -> tuple[str, dict[str, str]]:
    manifest = HERE / CODE_MANIFEST_NAME
    pin = HERE / CODE_PIN_NAME
    manifest_sha = file_sha256(manifest, field="Stage-C code manifest")
    fields = regular_file(pin, field="Stage-C code-manifest pin").read_text(encoding="ascii").strip().split()
    if fields != [manifest_sha, CODE_MANIFEST_NAME]:
        raise StageCError("Stage-C code manifest disagrees with its external pin")
    return manifest_sha, parse_sha256_manifest(manifest, root=repo)


def assert_no_placeholders(value: object) -> None:
    text = canonical_bytes(value).decode("ascii")
    if "<<" in text or ">>" in text or "BIND_AT_FREEZE" in text or "PLACEHOLDER" in text:
        raise StageCError("unresolved placeholder in execution bindings")


def tree_manifest(root: Path) -> tuple[list[dict[str, object]], str]:
    if root.is_symlink() or not root.is_dir():
        raise StageCError(f"TLE root is missing or symlinked: {root}")
    rows = []
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise StageCError(f"frozen TLE root contains a non-regular member: {path.name}")
        rows.append({"path": path.name, "sha256": file_sha256(path, field="frozen TLE member")})
    if not rows:
        raise StageCError("frozen TLE root contains no regular files")
    return rows, canonical_sha256(rows)


def process_environment() -> dict[str, object]:
    expected = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "OMP_NUM_THREADS": "2",
        "PYTHONPATH": str(REPO / "src"),
        "TMPDIR": str(REPO / ".tmp"),
    }
    for key, value in expected.items():
        if os.environ.get(key) != value:
            raise StageCError(f"deterministic process environment drifted: {key}")
    try:
        oom_score_adj = int(Path("/proc/self/oom_score_adj").read_text(encoding="ascii").strip())
    except (OSError, UnicodeError, ValueError) as error:
        raise StageCError("cannot authenticate oom_score_adj") from error
    if oom_score_adj != 1000:
        raise StageCError("oom_score_adj must equal 1000")
    limits = {}
    for name in ("RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_NOFILE", "RLIMIT_NPROC"):
        identifier = getattr(resource, name)
        soft, hard = resource.getrlimit(identifier)
        limits[name] = ["infinity" if value == resource.RLIM_INFINITY else value for value in (soft, hard)]
    return {
        **expected,
        "oom_score_adj": oom_score_adj,
        "resource_limits": limits,
        "rng_policy": "numpy.SeedSequence(world_seed).spawn(2); fresh environment per arm; fixed-policy inference",
    }


def require_formal(value: Mapping[str, object], *, field: str) -> None:
    if value.get("formal") is False:
        raise StageCError(f"{field} is explicitly non-formal")


def verify_bindings(path: str | Path) -> dict[str, Any]:
    value = read_json(path, field="execution bindings")
    verify_named_sidecar(path)
    if value.get("schema") != SCHEMA_BINDINGS or value.get("formal") is not True:
        raise StageCError("execution bindings are not formal Stage C bindings")
    assert_no_placeholders(value)
    if value.get("arms") != list(ARMS):
        raise StageCError("execution bindings arm order drifted")
    if value.get("world_plan", {}).get("plan_sha256") != PLAN_SHA256:
        raise StageCError("execution bindings plan digest drifted")
    return value


def forbid_policy_tokens(value: object, *, field: str) -> None:
    """Reject prohibited topology/split tokens with two declared exceptions.

    The frozen keyed-field namespace contains the historical substring C3 and
    the producer receipts carry boolean q3_evaluated=false audit fields.  They
    are authenticated exceptions, not routes, arms, models, or split openings.
    """
    def walk(child: object, key: str = "") -> None:
        if isinstance(child, Mapping):
            for nested_key, nested in child.items():
                if str(nested_key).lower() == "q3_evaluated" and nested is False:
                    continue
                walk(nested, str(nested_key))
            return
        if isinstance(child, (list, tuple)):
            for nested in child:
                walk(nested, key)
            return
        if not isinstance(child, str) or child == FIELD_COMPONENT:
            return
        tokens = [token.upper() for token in re.split(r"[^A-Za-z0-9]+", child) if token]
        normalized = child.upper()
        if (
            any(token in {"R7", "C3", "Q3", "TEST"} for token in tokens)
            or "ALL_NEUTRAL_CONTROL" in normalized
            or "DROP_C3" in normalized
        ):
            if "NO_C3" in normalized and "NO_TEST" in normalized:
                return
            raise StageCError(f"forbidden token in {field}: {child}")
        if normalized == "FULL":
            raise StageCError(f"FULL is forbidden as a trained arm in {field}")
    walk(value)
