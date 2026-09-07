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
PHYSICAL_EVALUATION_REL = Path(
    ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation"
)
STAGE_C_LAUNCH_REL = Path(
    ".scratch/multi-catfish-v023-c1c2-successor-stagec-launch"
)
CLOSURE_LIST_REL = Path(
    ".scratch/multi-catfish-v023-controller-handoff-20260907/"
    "SHADOW-CLOSURE-LIST-2026-09-07.txt"
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
STAGE_C_CODE_MANIFEST_NAME = "V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256"
STAGE_C_CODE_PIN_NAME = "V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST-FROZEN.sha256"
STAGE_C_ADDENDUM_REL = SUCCESSOR_REL / (
    "V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md"
)
STAGE_C_ADDENDUM_SIDECAR_REL = Path(
    STAGE_C_ADDENDUM_REL.as_posix() + ".sha256"
)

# The authoritative 246-path shadow closure intentionally predates this launch
# bundle.  These are the only additional payloads the Stage-A sync may add.
# Generated freeze inputs are included once the binder has created them.
LAUNCH_BUNDLE_SYNC_NAMES = frozenset(
    {
        "README.md",
        "bind_v023_c1c2_successor_freeze.py",
        "build_v023_c1c2_successor_launch_manifest.py",
        "preflight_v023_c1c2_successor.py",
        "run_v023_c1c2_successor_formal.py",
        "run_v023_c1c2_successor_one_epoch_diagnostic.py",
        "successor_launch_common.py",
        "sync_launch_v023_c1c2_successor_server.sh",
        "test_v023_c1c2_successor_launch.py",
        "verify_v023_c1c2_successor.py",
        BINDINGS_NAME,
        BINDINGS_NAME + ".sha256",
        LEARNER_MANIFEST_NAME,
        PROVIDER_CONFIG_NAME,
        PROVIDER_CONFIG_NAME + ".sha256",
    }
)
LAUNCH_MANIFEST_ADDITIONS = frozenset(
    {BUNDLE_REL / name for name in LAUNCH_BUNDLE_SYNC_NAMES}
    | {
        REVIEW_REL,
        CLOSURE_LIST_REL,
        STAGE_C_LAUNCH_REL / STAGE_C_CODE_MANIFEST_NAME,
        STAGE_C_LAUNCH_REL / STAGE_C_CODE_PIN_NAME,
    }
)

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
CONTRACT_PLACEHOLDER_RE = re.compile(r"<<BIND_AT_FREEZE:([a-z0-9_]+)>>")
STAGE_A_PLACEHOLDER_RE = CONTRACT_PLACEHOLDER_RE
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
# The contract permits only identities produced by Stage A to be supplied at a
# later Stage-C admission.  None of the predetermined Stage-C code bindings is
# deferrable.  Keep this closed list here so a new nonempty reason cannot open a
# deferral by accident.
ALLOWED_LATER_CONTRACT_DEFERRALS = frozenset(
    {
        "stage_a_manifest_sha256",
        "stage_a_pass_receipt_sha256",
        "stage_a_exports_manifest_sha256",
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
    if path.is_symlink() or not path.is_file():
        raise SuccessorLaunchError(f"{field} is missing or symlinked")
    raw = path.read_bytes()
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


def launch_manifest_additions(root: Path) -> list[Path]:
    """Return the exact enumerated bundle additions that currently exist."""

    missing_static = [
        path
        for path in LAUNCH_MANIFEST_ADDITIONS
        if path.parent != BUNDLE_REL or path.name not in {
            BINDINGS_NAME,
            BINDINGS_NAME + ".sha256",
            LEARNER_MANIFEST_NAME,
            PROVIDER_CONFIG_NAME,
            PROVIDER_CONFIG_NAME + ".sha256",
        }
        if not (root / path).is_file() or (root / path).is_symlink()
    ]
    if missing_static:
        raise SuccessorLaunchError(
            "enumerated launch-bundle addition is missing or symlinked: "
            + ", ".join(path.as_posix() for path in sorted(missing_static))
        )
    return sorted(
        path
        for path in LAUNCH_MANIFEST_ADDITIONS
        if (root / path).is_file() and not (root / path).is_symlink()
    )


def stage_c_manifest_members(root: Path) -> list[Path]:
    """Return the live, authenticated member set declared by Stage C."""

    verify_stage_c_code_bundle(root)
    manifest = root / STAGE_C_LAUNCH_REL / STAGE_C_CODE_MANIFEST_NAME
    return sorted(Path(path) for path in _parse_sha256_manifest(manifest))


def required_sync_closure(root: Path) -> list[Path]:
    source = root / CLOSURE_LIST_REL
    if source.is_symlink() or not source.is_file():
        raise SuccessorLaunchError("authoritative sync closure list is unavailable")
    try:
        rows = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise SuccessorLaunchError("authoritative sync closure list is unreadable") from error
    paths = [Path(safe_relative(row, field="sync closure path")) for row in rows if row]
    if len(paths) != 246 or len(set(paths)) != len(paths) or rows != sorted(rows):
        raise SuccessorLaunchError("authoritative sync closure is not the exact sorted 246-path set")
    missing = [path for path in paths if not (root / path).is_file() or (root / path).is_symlink()]
    if missing:
        raise SuccessorLaunchError(
            "authoritative sync closure has missing/symlinked paths: "
            + ", ".join(path.as_posix() for path in missing)
        )
    return paths


def assert_sync_coverage(required: Sequence[Path], observed: Sequence[Path]) -> None:
    absent = set(required) - set(observed)
    if absent:
        raise SuccessorLaunchError(
            "launch sync coverage is incomplete: "
            + ", ".join(path.as_posix() for path in sorted(absent))
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


def assert_contract_placeholders(
    contract_text: str, bindings: Mapping[str, object]
) -> None:
    found = set(CONTRACT_PLACEHOLDER_RE.findall(contract_text))
    missing = found - set(bindings)
    malformed: set[str] = set()
    for key in found & set(bindings):
        record = bindings[key]
        if not isinstance(record, Mapping):
            malformed.add(key)
            continue
        status = record.get("status")
        if status == "RESOLVED":
            if not isinstance(record.get("value"), str) or not record["value"]:
                malformed.add(key)
        elif status == "DEFERRED":
            if (
                key not in ALLOWED_LATER_CONTRACT_DEFERRALS
                or not isinstance(record.get("reason"), str)
                or not record["reason"].strip()
            ):
                malformed.add(key)
        else:
            malformed.add(key)
    if missing or malformed:
        raise SuccessorLaunchError(
            "contract freeze placeholders are neither resolved nor explicitly deferred: "
            + ", ".join(sorted(missing | malformed))
        )


def _parse_sha256_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    try:
        rows = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        raise SuccessorLaunchError("Stage-C code manifest is unreadable") from error
    for row in rows:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\x00]+)", row)
        if match is None:
            raise SuccessorLaunchError(f"malformed Stage-C manifest row: {row!r}")
        declared, relative_raw = match.groups()
        relative = safe_relative(relative_raw, field="Stage-C code manifest path")
        if relative in entries:
            raise SuccessorLaunchError(f"duplicate Stage-C manifest path: {relative}")
        entries[relative] = declared
    if not entries:
        raise SuccessorLaunchError("Stage-C code manifest is empty")
    return entries


def verify_stage_c_code_bundle(repo: Path) -> dict[str, Any]:
    """Authenticate the externally pinned Stage-C and physical code closure."""

    manifest_path = repo / STAGE_C_LAUNCH_REL / STAGE_C_CODE_MANIFEST_NAME
    pin_path = repo / STAGE_C_LAUNCH_REL / STAGE_C_CODE_PIN_NAME
    manifest_sha = file_sha256(manifest_path)
    expected_pin = f"{manifest_sha}  {STAGE_C_CODE_MANIFEST_NAME}\n"
    try:
        observed_pin = pin_path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        raise SuccessorLaunchError("Stage-C code-manifest pin is unreadable") from error
    if pin_path.is_symlink() or observed_pin != expected_pin:
        raise SuccessorLaunchError("Stage-C code manifest disagrees with its frozen pin")
    entries = _parse_sha256_manifest(manifest_path)
    missing_members = [
        relative
        for relative in entries
        if not (repo / relative).is_file() or (repo / relative).is_symlink()
    ]
    if missing_members:
        raise SuccessorLaunchError(
            "Stage-C code manifest member is missing or symlinked: "
            + ", ".join(missing_members)
        )
    stale_members = [
        relative
        for relative, declared in entries.items()
        if file_sha256(repo / relative) != declared
    ]
    if stale_members:
        raise SuccessorLaunchError(
            "Stage-C code manifest member digest disagrees: "
            + ", ".join(stale_members)
        )
    required_addendum_members = {
        STAGE_C_ADDENDUM_REL.as_posix(),
        STAGE_C_ADDENDUM_SIDECAR_REL.as_posix(),
    }
    absent_addendum_members = sorted(required_addendum_members - set(entries))
    if absent_addendum_members:
        raise SuccessorLaunchError(
            "Stage-C addendum and sidecar must both be manifest members: "
            + ", ".join(absent_addendum_members)
        )
    verify_sidecar(repo / STAGE_C_ADDENDUM_REL)
    physical_prefix = PHYSICAL_EVALUATION_REL.as_posix() + "/"
    physical_entries = {
        path: value for path, value in entries.items() if path.startswith(physical_prefix)
    }
    expected_physical = {
        path.as_posix() for path in directory_files(repo, PHYSICAL_EVALUATION_REL)
    }
    if set(physical_entries) != expected_physical:
        raise SuccessorLaunchError(
            "Stage-C code manifest does not exactly cover the physical-evaluation package"
        )
    stage_c_prefix = STAGE_C_LAUNCH_REL.as_posix() + "/"
    stage_c_entries = {
        path: value for path, value in entries.items() if path.startswith(stage_c_prefix)
    }
    verifier_path = (
        STAGE_C_LAUNCH_REL / "verify_v023_c1c2_successor_stagec.py"
    ).as_posix()
    if verifier_path not in stage_c_entries:
        raise SuccessorLaunchError("Stage-C verifier is absent from the pinned code manifest")
    return {
        "code_manifest_path": (STAGE_C_LAUNCH_REL / STAGE_C_CODE_MANIFEST_NAME).as_posix(),
        "code_manifest_sha256": manifest_sha,
        "code_manifest_pin_path": (STAGE_C_LAUNCH_REL / STAGE_C_CODE_PIN_NAME).as_posix(),
        "code_manifest_pin_sha256": file_sha256(pin_path),
        "physical_evaluation_package_manifest_sha256": canonical_sha256(
            dict(sorted(physical_entries.items()))
        ),
        "stage_c_bundle_manifest_sha256": manifest_sha,
        "code_manifest_entry_count": len(entries),
    }


def assert_predetermined_stage_c_bound(
    repo: Path, bindings: Mapping[str, object]
) -> dict[str, Any]:
    """Reject all Stage-C code deferrals and authenticate their live bytes."""

    placeholders = bindings.get("contract_placeholder_bindings")
    stage_c = bindings.get("stage_c")
    if not isinstance(placeholders, Mapping) or not isinstance(stage_c, Mapping):
        raise SuccessorLaunchError("predetermined Stage-C bindings are missing")
    evaluation = placeholders.get("evaluation_runner_manifest_sha256")
    if (
        not isinstance(evaluation, Mapping)
        or evaluation.get("status") != "RESOLVED"
    ):
        raise SuccessorLaunchError("Stage-C evaluation runner manifest cannot be deferred")
    live = verify_stage_c_code_bundle(repo)
    physical_digest = digest(
        evaluation.get("value"), field="Stage-C evaluation runner manifest"
    )
    runner_digest = digest(
        stage_c.get("runner_bundle_manifest_sha256"),
        field="Stage-C runner bundle manifest",
    )
    verifier_digest = digest(
        stage_c.get("verifier_bundle_manifest_sha256"),
        field="Stage-C verifier bundle manifest",
    )
    code = stage_c.get("code_bundle")
    if not isinstance(code, Mapping) or dict(code) != live:
        raise SuccessorLaunchError("Stage-C pinned code-bundle binding drifted")
    if (
        physical_digest != live["physical_evaluation_package_manifest_sha256"]
        or stage_c.get("physical_evaluation_package_manifest_sha256") != physical_digest
        or runner_digest != live["stage_c_bundle_manifest_sha256"]
        or verifier_digest != live["stage_c_bundle_manifest_sha256"]
    ):
        raise SuccessorLaunchError("predetermined Stage-C code digest binding drifted")
    return live


def reject_forbidden_config(value: object) -> None:
    token_re = re.compile(
        r"(?<![A-Za-z0-9])(?:r7|c3|q3|test|all_neutral_control|drop_c3)(?![A-Za-z0-9])",
        re.IGNORECASE,
    )

    def visit(item: object, *, field: str) -> None:
        field_lower = field.lower()
        if isinstance(item, Mapping):
            for key, child in item.items():
                visit(child, field=str(key))
            return
        if isinstance(item, (list, tuple)):
            for child in item:
                visit(child, field=field)
            return
        if field_lower.endswith("sha256") or "digest" in field_lower:
            digest(item, field=field)
            return
        if not isinstance(item, str):
            return
        semantic = any(
            marker in field_lower
            for marker in ("path", "root", "route", "split", "arm", "module", "source")
        )
        if semantic and token_re.search(item):
            raise SuccessorLaunchError("provider config contains forbidden token(s)")
        if "arm" in field_lower and item.upper() == "FULL":
            raise SuccessorLaunchError("provider config names FULL as a trained arm")

    visit(value, field="config")


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


def authenticate_preflight_freeze_authorities(
    *, repo: Path, preflight: Mapping[str, object], requested_output_root: Path
) -> dict[str, Any]:
    """Re-authenticate the two freeze authorities named by a preflight receipt."""

    required = {
        "launch_manifest_path",
        "launch_manifest_sha256",
        "execution_bindings_path",
        "execution_bindings_sha256",
        "requested_output_root",
    }
    missing = sorted(required - set(preflight))
    if missing:
        raise SuccessorLaunchError(
            "preflight freeze authority fields are missing: " + ", ".join(missing)
        )
    launch_path_raw = preflight.get("launch_manifest_path")
    bindings_path_raw = preflight.get("execution_bindings_path")
    if not isinstance(launch_path_raw, str) or not isinstance(bindings_path_raw, str):
        raise SuccessorLaunchError("preflight freeze authority paths are malformed")
    launch_path = Path(launch_path_raw)
    bindings_path = Path(bindings_path_raw)
    if not launch_path.is_absolute():
        launch_path = repo / safe_relative(
            launch_path_raw, field="preflight launch manifest path"
        )
    if not bindings_path.is_absolute():
        bindings_path = repo / safe_relative(
            bindings_path_raw, field="preflight execution bindings path"
        )
    launch = verify_launch_manifest(repo, launch_path)
    bindings_sha = verify_sidecar(bindings_path)
    bindings = read_canonical_json(bindings_path, field="referenced execution bindings")
    if (
        bindings.get("schema") != EXECUTION_BINDINGS_SCHEMA
        or bindings.get("status") != "FROZEN_STAGE_A"
    ):
        raise SuccessorLaunchError("referenced execution bindings are not frozen Stage A")
    contract_path = repo / SUCCESSOR_REL / CONTRACT_NAME
    assert_contract_placeholders(
        contract_path.read_text(encoding="utf-8"),
        bindings.get("contract_placeholder_bindings", {}),
    )
    assert_predetermined_stage_c_bound(repo, bindings)
    declared_launch = digest(
        preflight.get("launch_manifest_sha256"),
        field="preflight launch_manifest_sha256",
    )
    declared_bindings = digest(
        preflight.get("execution_bindings_sha256"),
        field="preflight execution_bindings_sha256",
    )
    input_binding = preflight.get("input_binding")
    if not isinstance(input_binding, Mapping):
        raise SuccessorLaunchError("preflight input binding is missing")
    if (
        declared_launch != launch["sha256"]
        or declared_bindings != bindings_sha
        or input_binding.get("launch_manifest_sha256") != declared_launch
        or input_binding.get("bindings_sha256") != declared_bindings
    ):
        raise SuccessorLaunchError("preflight freeze authority digest binding drifted")
    expected_root = str(requested_output_root.resolve(strict=False))
    if (
        preflight.get("requested_output_root") != expected_root
        or preflight.get("output_root") != expected_root
    ):
        raise SuccessorLaunchError("preflight requested output root drifted")
    return {
        "launch_manifest_sha256": declared_launch,
        "execution_bindings_sha256": declared_bindings,
        "requested_output_root": expected_root,
        "bindings": bindings,
    }
