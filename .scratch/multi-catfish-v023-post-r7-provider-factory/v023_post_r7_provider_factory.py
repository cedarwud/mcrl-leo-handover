"""Fail-closed post-R7 provider factory for the V0.23 source learner.

This module is the small, production-facing seam between three already
authenticated artifacts:

* a *sealed* R7 result root, from which the current source panel and an exact
  :class:`R7GoDecisionBinding` are reconstructed;
* the completed C1/C2 target root; and
* the deterministic C3 informed/neutral schedule built from the same R7
  records.

It deliberately does not run a simulator, open TEST, update a learner, or
write an artifact.  ``make_provider`` is a zero-argument factory so it can be
passed directly to the unchanged source-training runner.  Its two narrowly
named environment variables identify one canonical JSON configuration and its
expected byte SHA-256; missing or changed configuration fails closed.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import MappingProxyType, ModuleType
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

CONFIG_PATH_ENV = "MCRL_V023_POST_R7_PROVIDER_CONFIG_PATH"
CONFIG_SHA256_ENV = "MCRL_V023_POST_R7_PROVIDER_CONFIG_SHA256"
CONFIG_SCHEMA = "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v1"
FACTORY_SCHEMA = "multi-catfish-mcrl-v023-post-r7-provider-factory-v1"
IDENTITY_SCHEMA = "multi-catfish-mcrl-v023-post-r7-provider-identity-v1"
R7_ROOT_RESULT = "result.json"
R7_ROOT_VERIFICATION = "verification.json"
R7_ROOT_SOURCE_MANIFEST = "source-manifest.json"
R7_ROOT_AUTHORITY = "authority/AUTHORITY.json"
R7_AUTHORITY_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-r7-balanced-authority-snapshot-v1"
)
R7_AUTHORITY_CONTRACT = (
    "authority/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md"
)
R7_AUTHORITY_EXECUTION_ADDENDUM = (
    "authority/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
)
R7_ROOT_PREFLIGHT = "authority/R7-PREFLIGHT-MANIFEST.json"
R7_ROOT_PREFLIGHT_DIGEST = "authority/R7-PREFLIGHT-MANIFEST.sha256"
R7_PREFLIGHT_SCHEMA = "multi-catfish-mcrl-v023-r7-balanced-launch-preflight-v1"
R7_PREFLIGHT_STATUS = "FROZEN_PRE_OUTCOME"
R7_PREFLIGHT_LAUNCH = "AUTHORIZED_ONE_SHOT"
R7_PREFLIGHT_RECEIPT_SCHEMA = (
    "multi-catfish-mcrl-v023-r7-balanced-launch-preflight-receipt-v1"
)
R7_PREFLIGHT_RECEIPT_STATUS = "PASS_FROZEN_PRE_OUTCOME_PREFLIGHT"
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CONFIG_FIELDS = frozenset({"schema", "r7_root", "target_root", "epoch_budget", "schedule_seed"})
_R7_COMMON_FIELDS = (
    "schema",
    "status",
    "integrity_status",
    "c3_decision",
    "context_status",
    "claim_ceiling",
    "source_count",
    "fit_count",
    "composition_count",
    "contract_sha256",
    "execution_addendum_sha256",
    "launch_decision_sha256",
    "code_manifest_sha256",
    "preflight_manifest_sha256",
    "launch_manifest_sha256",
    "source_manifest_sha256",
    "test_split_opened",
    "episode_training",
    "scientific_claim",
    "no_rescue",
    "no_scientific_token_before_integrity",
)


class V023PostR7ProviderFactoryError(RuntimeError):
    """An authenticated post-R7 provider boundary failed closed."""


def _load_sibling_module(*, name: str, path: Path) -> ModuleType:
    """Load one scratch sibling without duplicating its implementation."""

    wanted = path.resolve()
    for module in tuple(sys.modules.values()):
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str):
            continue
        try:
            if Path(module_file).resolve() == wanted:
                return module
        except OSError:
            continue
    if wanted.is_symlink() or not wanted.is_file():
        raise V023PostR7ProviderFactoryError(f"sibling seam is unavailable: {path}")
    spec = importlib.util.spec_from_file_location(name, wanted)
    if spec is None or spec.loader is None:
        raise V023PostR7ProviderFactoryError(f"cannot load sibling seam: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_FIT = _load_sibling_module(
    name="v023_fit_adapter_for_post_r7_provider_factory",
    path=REPO / ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py",
)
_R7_GATE = _load_sibling_module(
    name="r7_balanced_successor_gate",
    path=REPO / ".scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py",
)
if sys.modules.get("r7_balanced_successor_gate") is not _R7_GATE:
    sys.modules["r7_balanced_successor_gate"] = _R7_GATE
_PREFLIGHT = _load_sibling_module(
    name="v023_r7_preflight_for_post_r7_provider_factory",
    path=REPO / ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py",
)
_SCHEDULE = _load_sibling_module(
    name="v023_c3_schedule_for_post_r7_provider_factory",
    path=REPO / ".scratch/multi-catfish-v023-c3-source-schedule/v023_c3_source_schedule.py",
)
_BRIDGE = _load_sibling_module(
    name="v023_provider_bridge_for_post_r7_provider_factory",
    path=REPO / ".scratch/multi-catfish-v023-provider-orchestrator-bridge/v023_provider_orchestrator_bridge.py",
)


def _fail(message: str, *, cause: BaseException | None = None) -> None:
    if cause is None:
        raise V023PostR7ProviderFactoryError(message)
    raise V023PostR7ProviderFactoryError(message) from cause


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _fail(f"{field} must be a lowercase SHA-256")
    return value


def _regular_file(path: Path, *, field: str) -> None:
    if path.is_symlink() or not path.is_file():
        _fail(f"{field} must be a regular non-symlink file")


def _regular_dir(path: Path, *, field: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        _fail(f"{field} must be a regular non-symlink directory")
    return path.resolve()


def _file_sha256(path: Path, *, field: str = "file") -> str:
    _regular_file(path, field=field)
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as cause:
        _fail(f"cannot read {field}", cause=cause)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as cause:
        _fail("value is not finite canonical ASCII JSON", cause=cause)


def _read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    _regular_file(path, field=field)
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as cause:
        _fail(f"{field} is not readable canonical JSON", cause=cause)
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        _fail(f"{field} is not canonical JSON")
    return value


def _safe_relative(root: Path, relative: str, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        _fail(f"{field} is not a relative path")
    candidate = root / relative
    if candidate.is_symlink():
        _fail(f"{field} is a symlink")
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        _fail(f"{field} escapes its root")
    return resolved


def _verify_result_manifest(root: Path) -> dict[str, str]:
    """Authenticate the write-once seal and every listed result-tree file."""

    manifest_path = root / "MANIFEST.sha256"
    complete_path = root / "COMPLETE"
    _regular_file(manifest_path, field="R7 MANIFEST.sha256")
    _regular_file(complete_path, field="R7 COMPLETE")
    manifest_sha = _file_sha256(manifest_path, field="R7 manifest")
    try:
        complete = complete_path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as cause:
        _fail("R7 COMPLETE is unreadable", cause=cause)
    if complete != f"{manifest_sha}  MANIFEST.sha256\n":
        _fail("R7 COMPLETE is not bound to MANIFEST.sha256")

    listed: dict[str, str] = {}
    try:
        lines = manifest_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as cause:
        _fail("R7 manifest is unreadable", cause=cause)
    if not lines:
        _fail("R7 manifest is empty")
    for line in lines:
        parts = line.split("  ")
        if len(parts) != 2:
            _fail("R7 manifest line is malformed")
        declared, relative = parts
        _digest(declared, field=f"R7 manifest entry {relative}")
        if relative in listed or relative in {"MANIFEST.sha256", "COMPLETE"}:
            _fail("R7 manifest has duplicate or self-referential entries")
        path = _safe_relative(root, relative, field=f"R7 manifest entry {relative}")
        actual = _file_sha256(path, field=f"R7 manifest entry {relative}")
        if actual != declared:
            _fail(f"R7 manifest entry hash disagrees: {relative}")
        listed[relative] = declared

    actual_files: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            _fail(f"R7 result tree contains a symlink: {path.relative_to(root)}")
        if path.is_dir():
            continue
        if not path.is_file():
            _fail(f"R7 result tree contains a special file: {path.relative_to(root)}")
        actual_files.add(path.relative_to(root).as_posix())
    expected_files = actual_files - {"MANIFEST.sha256", "COMPLETE"}
    if set(listed) != expected_files:
        _fail("R7 manifest does not cover the complete sealed result tree")
    return listed


def _verify_r7_authority_snapshot(
    root: Path,
    listed: Mapping[str, str],
    *,
    expected_preflight_sha256: str,
    expected_contract_sha256: str,
    expected_execution_addendum_sha256: str,
) -> None:
    """Authenticate the immutable authority snapshot inside the sealed root."""

    authority_path = root / R7_ROOT_AUTHORITY
    if R7_ROOT_AUTHORITY not in listed:
        _fail("R7 authority/AUTHORITY.json is not manifest-listed")
    authority = _read_canonical_json(
        authority_path, field="R7 authority/AUTHORITY.json"
    )
    expected_fields = {
        "schema",
        "contract_sha256",
        "execution_addendum_sha256",
        "preflight_manifest_sha256",
        "entries",
        "test_split_opened",
        "episode_training",
    }
    if set(authority) != expected_fields:
        _fail("R7 authority snapshot field set drifted")
    if (
        authority.get("schema") != R7_AUTHORITY_SCHEMA
        or authority.get("contract_sha256") != _SCHEDULE.R7_CONTRACT_SHA256
        or authority.get("execution_addendum_sha256")
        != _SCHEDULE.R7_EXECUTION_ADDENDUM_SHA256
        or authority.get("preflight_manifest_sha256")
        != expected_preflight_sha256
        or authority.get("test_split_opened") is not False
        or authority.get("episode_training") is not False
    ):
        _fail("R7 authority snapshot crossed a frozen boundary")
    if (
        expected_contract_sha256 != _SCHEDULE.R7_CONTRACT_SHA256
        or expected_execution_addendum_sha256
        != _SCHEDULE.R7_EXECUTION_ADDENDUM_SHA256
    ):
        _fail("R7 result and authority snapshot disagree on frozen documents")

    entries = authority.get("entries")
    expected_entries = {
        "contract": (R7_AUTHORITY_CONTRACT, _SCHEDULE.R7_CONTRACT_SHA256),
        "execution_addendum": (
            R7_AUTHORITY_EXECUTION_ADDENDUM,
            _SCHEDULE.R7_EXECUTION_ADDENDUM_SHA256,
        ),
        "preflight_manifest": (R7_ROOT_PREFLIGHT, expected_preflight_sha256),
        "preflight_manifest_digest": (R7_ROOT_PREFLIGHT_DIGEST, None),
    }
    if not isinstance(entries, Mapping) or set(entries) != set(expected_entries):
        _fail("R7 authority snapshot entry set drifted")
    for role, (relative, fixed_digest) in expected_entries.items():
        entry = entries.get(role)
        if not isinstance(entry, Mapping) or set(entry) != {"path", "sha256"}:
            _fail(f"R7 authority snapshot entry drifted for {role}")
        if entry.get("path") != relative:
            _fail(f"R7 authority snapshot path drifted for {role}")
        if relative not in listed:
            _fail(f"R7 authority snapshot file is not manifest-listed: {relative}")
        declared = _digest(
            entry.get("sha256"), field=f"R7 authority snapshot {role} sha256"
        )
        target = _safe_relative(root, relative, field=f"R7 authority snapshot {role}")
        actual = _file_sha256(target, field=f"R7 authority snapshot {role}")
        if declared != actual or (fixed_digest is not None and actual != fixed_digest):
            _fail(f"R7 authority snapshot digest drifted for {role}")
        if listed[relative] != actual:
            _fail(f"R7 authority snapshot manifest binding drifted for {role}")

    digest_sidecar = root / R7_ROOT_PREFLIGHT_DIGEST
    try:
        sidecar = digest_sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeError) as cause:
        _fail("R7 authority preflight digest is unreadable", cause=cause)
    if sidecar != f"{expected_preflight_sha256}  R7-PREFLIGHT-MANIFEST.json\n":
        _fail("R7 authority preflight digest sidecar disagrees")


def _verify_r7_preflight(
    root: Path,
    *,
    expected_sha256: str,
    expected_code_manifest_sha256: str,
) -> str:
    preflight = root / R7_ROOT_PREFLIGHT
    preflight_digest = root / R7_ROOT_PREFLIGHT_DIGEST
    actual = _file_sha256(preflight, field="R7 authority preflight manifest")
    if actual != _digest(expected_sha256, field="R7 preflight manifest sha256"):
        _fail("R7 result and authority preflight manifest disagree")
    _regular_file(preflight_digest, field="R7 authority preflight digest")
    try:
        sidecar = preflight_digest.read_text(encoding="ascii")
    except (OSError, UnicodeError) as cause:
        _fail("R7 authority preflight digest is unreadable", cause=cause)
    if sidecar != f"{actual}  R7-PREFLIGHT-MANIFEST.json\n":
        _fail("R7 authority preflight digest disagrees")
    payload = _read_canonical_json(preflight, field="R7 authority preflight manifest")
    expected_fields = {
        "bindings",
        "code_manifest",
        "configuration",
        "contract",
        "initial_network_sha256_by_seed",
        "launch",
        "manifest_version",
        "process_environment",
        "schema",
        "status",
        "student_seeds",
        "worlds",
    }
    if set(payload) != expected_fields:
        _fail("R7 preflight manifest field set drifted")
    if (
        payload.get("schema") != R7_PREFLIGHT_SCHEMA
        or payload.get("manifest_version") != 1
        or payload.get("status") != R7_PREFLIGHT_STATUS
        or payload.get("launch") != R7_PREFLIGHT_LAUNCH
        or payload.get("worlds") != list(_PREFLIGHT.WORLDS)
        or payload.get("student_seeds") != list(_PREFLIGHT.STUDENT_SEEDS)
        or payload.get("process_environment") != _PREFLIGHT.PROCESS_ENVIRONMENT
    ):
        _fail("R7 preflight schema/status/world/seed boundary drifted")
    if payload.get("initial_network_sha256_by_seed") != _PREFLIGHT.INITIAL_DIGESTS:
        _fail("R7 preflight initial network seed digests drifted")
    if payload.get("contract") != {
        "path": _PREFLIGHT.CONTRACT,
        "sha256": _SCHEDULE.R7_CONTRACT_SHA256,
    }:
        _fail("R7 preflight contract binding drifted")

    code_link = payload.get("code_manifest")
    expected_code_path = Path(_PREFLIGHT.CODE_MANIFEST).resolve().relative_to(REPO).as_posix()
    if not isinstance(code_link, Mapping) or set(code_link) != {"path", "sha256"}:
        _fail("R7 preflight code-manifest binding is missing")
    if (
        code_link.get("path") != expected_code_path
        or code_link.get("sha256") != expected_code_manifest_sha256
    ):
        _fail("R7 preflight code-manifest binding disagrees")
    actual_code_manifest_sha = _file_sha256(
        REPO / expected_code_path, field="R7 launch code manifest"
    )
    if actual_code_manifest_sha != expected_code_manifest_sha256:
        _fail("R7 launch code manifest bytes disagree with sealed R7")
    code_manifest_digest_path = Path(_PREFLIGHT.CODE_MANIFEST_SHA).resolve()
    actual_code_manifest_digest_sha = _file_sha256(
        code_manifest_digest_path, field="R7 launch code-manifest digest"
    )

    configuration = payload.get("configuration")
    if not isinstance(configuration, Mapping):
        _fail("R7 preflight configuration is missing")
    critical_configuration = {
        "split": "TRAIN_DEVELOPMENT",
        "test_split_opened": False,
        "episode_training": False,
        "scientific_efficacy": False,
        "claim_ceiling": _PREFLIGHT.CLAIM_CEILING,
        "worlds": list(_PREFLIGHT.WORLDS),
        "student_seeds": list(_PREFLIGHT.STUDENT_SEEDS),
        "steps_per_episode": 10,
        "users": 100,
        "action_count": 28,
        "draw_count": 32,
        "fold_count": 8,
        "fit_updates": 2000,
        "lineage": 2026092101,
        "field_component": "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1",
        "placebo_key": "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1",
        "placebo_key_sha256": (
            "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
        ),
        "source_artifact_schema": "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1",
        "lambda_hex": "0x1.c3c0a7b6b86d3p+26",
        "kappa_hex": "0x1.2cea89d260f2ap+33",
        "process_environment": _PREFLIGHT.PROCESS_ENVIRONMENT,
        "source_jobs": 8,
        "fit_jobs": 8,
        "composition_jobs": 8,
        "selected_checkpoint_role": (
            "FROZEN_GATE_BACKGROUND_PROVENANCE_ONLY_NOT_CURRENT_LEARNER_INITIALIZATION"
        ),
    }
    for field, expected in critical_configuration.items():
        if configuration.get(field) != expected:
            _fail(f"R7 preflight configuration.{field} drifted")
    if configuration.get("learner") != _PREFLIGHT.EXPECTED_LEARNER:
        _fail("R7 preflight learner configuration drifted")

    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        _fail("R7 preflight bindings are missing")
    by_role: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(bindings):
        if not isinstance(item, Mapping) or set(item) != {"path", "role", "sha256"}:
            _fail(f"R7 preflight binding {index} is malformed")
        role = item.get("role")
        if not isinstance(role, str) or not role or role in by_role:
            _fail("R7 preflight binding roles are missing or repeated")
        by_role[role] = item
    expected_bindings = {
        "base_contract": (
            _PREFLIGHT.BASE_CONTRACT,
            _SCHEDULE.R7_BASE_CONTRACT_SHA256,
        ),
        "code_manifest": (
            expected_code_path,
            expected_code_manifest_sha256,
        ),
        "code_manifest_digest": (
            Path(_PREFLIGHT.CODE_MANIFEST_SHA).resolve().relative_to(REPO).as_posix(),
            actual_code_manifest_digest_sha,
        ),
    }
    for role, (expected_path, expected_binding_sha) in expected_bindings.items():
        binding = by_role.get(role)
        if not isinstance(binding, Mapping):
            _fail(f"R7 preflight lacks {role} binding")
        if (
            binding.get("path") != expected_path
            or binding.get("sha256") != expected_binding_sha
        ):
            _fail(f"R7 preflight {role} binding disagrees")
        _digest(binding.get("sha256"), field=f"R7 preflight {role} sha256")

    try:
        receipt = _PREFLIGHT.validate_manifest(
            preflight,
            manifest_digest_path=preflight_digest,
            repo=REPO,
        )
    except Exception as cause:
        _fail("R7 preflight authoritative validation failed", cause=cause)
    if not isinstance(receipt, Mapping):
        _fail("R7 preflight authoritative validator returned no receipt")
    if (
        receipt.get("schema") != R7_PREFLIGHT_RECEIPT_SCHEMA
        or receipt.get("status") != R7_PREFLIGHT_RECEIPT_STATUS
        or receipt.get("manifest_status") != R7_PREFLIGHT_STATUS
        or receipt.get("launch") != R7_PREFLIGHT_LAUNCH
        or receipt.get("manifest_file_sha256") != actual
        or receipt.get("code_manifest_sha256") != expected_code_manifest_sha256
        or receipt.get("worlds") != list(_PREFLIGHT.WORLDS)
        or receipt.get("student_seeds") != list(_PREFLIGHT.STUDENT_SEEDS)
        or receipt.get("claim_ceiling") != _PREFLIGHT.CLAIM_CEILING
        or receipt.get("test_split_opened") is not False
        or receipt.get("episode_training") is not False
        or receipt.get("scientific_efficacy") is not False
    ):
        _fail("R7 preflight authoritative receipt crossed a frozen boundary")
    return _digest(
        by_role["base_contract"].get("sha256"),
        field="R7 base contract sha256",
    )


def _verify_launch_metadata(root: Path, listed: Mapping[str, str]) -> Mapping[str, Any]:
    """Recover the split field omitted by the final-verification receipt."""

    path = root / "LAUNCH-METADATA.json"
    relative = path.relative_to(root).as_posix()
    if relative not in listed:
        _fail("R7 LAUNCH-METADATA.json is not manifest-listed")
    payload = _read_canonical_json(path, field="R7 LAUNCH-METADATA.json")
    if (
        payload.get("schema")
        != "multi-catfish-mcrl-v023-lcsrs-r7-balanced-server-run-v1"
        or payload.get("split") != _SCHEDULE.R7_SPLIT
        or payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
    ):
        _fail("R7 launch metadata crossed a frozen boundary")
    return payload


def _essential_result_fields(payload: Mapping[str, Any]) -> None:
    exact = {
        "schema": _SCHEDULE.R7_FINAL_SCHEMA,
        "status": _SCHEDULE.R7_FINAL_STATUS,
        "integrity_status": _SCHEDULE.R7_INTEGRITY_STATUS,
        "c3_decision": _SCHEDULE.R7_GO_DECISION,
        "claim_ceiling": _SCHEDULE.R7_CLAIM_CEILING,
        "source_count": 8,
        "fit_count": 48,
        "composition_count": 48,
        "test_split_opened": False,
        "episode_training": False,
        "scientific_claim": False,
        "no_rescue": True,
        "no_scientific_token_before_integrity": True,
    }
    for field, expected in exact.items():
        if payload.get(field) != expected:
            _fail(f"R7 final result {field} is not the frozen GO value")
    if payload.get("context_status") not in _SCHEDULE.R7_CONTEXT_STATUSES:
        _fail("R7 final result context_status is not admissible")
    for field in (
        "contract_sha256",
        "execution_addendum_sha256",
        "launch_decision_sha256",
        "code_manifest_sha256",
        "preflight_manifest_sha256",
        "launch_manifest_sha256",
        "source_manifest_sha256",
    ):
        _digest(payload.get(field), field=f"R7 final result {field}")


@dataclass(frozen=True, slots=True)
class R7GoAuthentication:
    """A sealed result, its authenticated source panel, and exact binding."""

    root: Path
    result_path: Path
    result_sha256: str
    result: Mapping[str, Any]
    source_panel: object
    records: tuple[object, ...]
    binding: object


def authenticate_r7_go(root: str | Path) -> R7GoAuthentication:
    """Reopen one sealed R7 root and build its exact current GO binding.

    No result JSON is read until ``COMPLETE`` and the whole result-tree
    manifest have been authenticated.  The source panel is then reconstructed
    through the audited fit adapter and its record-panel digest is computed,
    rather than copied from a result receipt.
    """

    root_path = _regular_dir(Path(root), field="R7 result root")
    listed = _verify_result_manifest(root_path)
    result_path = root_path / R7_ROOT_RESULT
    verification_path = root_path / R7_ROOT_VERIFICATION
    source_manifest_path = root_path / R7_ROOT_SOURCE_MANIFEST
    for path, field in (
        (result_path, "R7 result.json"),
        (verification_path, "R7 verification.json"),
        (source_manifest_path, "R7 source-manifest.json"),
    ):
        relative = path.relative_to(root_path).as_posix()
        if relative not in listed:
            _fail(f"{field} is not manifest-listed")
        _regular_file(path, field=field)
    result = _read_canonical_json(result_path, field="R7 result.json")
    verification = _read_canonical_json(verification_path, field="R7 verification.json")
    _essential_result_fields(result)
    # The frozen final verifier deliberately omits ``split`` from its result;
    # recover that execution boundary only from the separately manifest-bound
    # launch metadata.  A future result may repeat it, but may not disagree.
    launch_metadata = _verify_launch_metadata(root_path, listed)
    split = launch_metadata["split"]
    if "split" in result and result["split"] != split:
        _fail("R7 final result split disagrees with launch metadata")
    for result_field, metadata_field in (
        ("contract_sha256", "contract_sha256"),
        ("launch_decision_sha256", "launch_decision_sha256"),
        ("code_manifest_sha256", "code_manifest_sha256"),
        ("preflight_manifest_sha256", "preflight_manifest_sha256"),
        # The final verifier calls this the launch-manifest digest; in the
        # frozen launcher it is the authenticated preflight manifest digest.
        ("launch_manifest_sha256", "preflight_manifest_sha256"),
    ):
        if launch_metadata.get(metadata_field) != result.get(result_field):
            _fail(
                f"R7 final result and launch metadata disagree at {result_field}"
            )
    # The result sealer adds only thresholds/design_basis to result.json.  All
    # fields used to make a GO binding must still agree byte-for-byte with the
    # independently written final-verification receipt.
    for field in _R7_COMMON_FIELDS:
        if verification.get(field) != result.get(field):
            _fail(f"R7 result and verification disagree at {field}")

    preflight_sha = str(result["preflight_manifest_sha256"])
    _verify_r7_authority_snapshot(
        root_path,
        listed,
        expected_preflight_sha256=preflight_sha,
        expected_contract_sha256=result["contract_sha256"],
        expected_execution_addendum_sha256=result["execution_addendum_sha256"],
    )
    base_contract_sha = _verify_r7_preflight(
        root_path,
        expected_sha256=preflight_sha,
        expected_code_manifest_sha256=result["code_manifest_sha256"],
    )
    if base_contract_sha != _SCHEDULE.R7_BASE_CONTRACT_SHA256:
        _fail("R7 base contract does not equal the current frozen contract")

    try:
        source_panel = _FIT.load_v023_source_panel(
            source_directory=root_path,
            source_manifest=source_manifest_path,
            preflight_manifest_sha256=preflight_sha,
        )
    except Exception as cause:
        _fail("sealed R7 source panel failed typed reauthentication", cause=cause)
    if source_panel.source_manifest_sha256 != result["source_manifest_sha256"]:
        _fail("R7 source panel manifest digest disagrees with final result")
    records_by_world = source_panel.records_by_world
    if tuple(sorted(records_by_world)) != _SCHEDULE.R7_WORLDS:
        _fail("R7 source panel does not cover the exact frozen worlds")
    records = tuple(
        record
        for world in _SCHEDULE.R7_WORLDS
        for record in records_by_world[world]
    )
    if any(not records_by_world[world] for world in _SCHEDULE.R7_WORLDS):
        _fail("R7 source panel contains an empty world")
    try:
        record_panel_sha = _SCHEDULE.canonical_record_panel_sha256(records)
    except Exception as cause:
        _fail("R7 source record panel failed canonical reauthentication", cause=cause)
    result_sha = _file_sha256(result_path, field="R7 result.json")
    if listed["result.json"] != result_sha:
        _fail("R7 result manifest entry disagrees")
    try:
        binding = _SCHEDULE.R7GoDecisionBinding(
            schema=result["schema"],
            status=result["status"],
            integrity_status=result["integrity_status"],
            c3_decision=result["c3_decision"],
            context_status=result["context_status"],
            claim_ceiling=result["claim_ceiling"],
            split=split,
            worlds=_SCHEDULE.R7_WORLDS,
            source_count=result["source_count"],
            fit_count=result["fit_count"],
            composition_count=result["composition_count"],
            base_contract_sha256=base_contract_sha,
            contract_sha256=result["contract_sha256"],
            execution_addendum_sha256=result["execution_addendum_sha256"],
            launch_decision_sha256=result["launch_decision_sha256"],
            code_manifest_sha256=result["code_manifest_sha256"],
            preflight_manifest_sha256=result["preflight_manifest_sha256"],
            launch_manifest_sha256=result["launch_manifest_sha256"],
            source_manifest_sha256=result["source_manifest_sha256"],
            gate_result_sha256=result_sha,
            record_panel_sha256=record_panel_sha,
            test_split_opened=result["test_split_opened"],
            episode_training=result["episode_training"],
            scientific_claim=result["scientific_claim"],
            no_rescue=result["no_rescue"],
            no_scientific_token_before_integrity=result["no_scientific_token_before_integrity"],
        )
        binding.verify()
    except Exception as cause:
        _fail("sealed R7 result could not form a valid GO binding", cause=cause)
    return R7GoAuthentication(
        root=root_path,
        result_path=result_path,
        result_sha256=result_sha,
        result=MappingProxyType(dict(result)),
        source_panel=source_panel,
        records=records,
        binding=binding,
    )


@dataclass(frozen=True, slots=True)
class PostR7ProviderConfig:
    """Canonical factory inputs; no mutable runtime state is stored here."""

    r7_root: Path
    target_root: Path
    epoch_budget: int
    schedule_seed: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.r7_root, "r7_root"),
            (self.target_root, "target_root"),
        ):
            if not isinstance(value, Path) or not value.is_absolute():
                _fail(f"config {field} must be an absolute path")
        if type(self.epoch_budget) is not int or self.epoch_budget not in _SCHEDULE.FORMAL_SOURCE_TRAINING_EPOCH_BUDGETS:
            _fail("config epoch_budget must be exactly 100 or 500")
        if type(self.schedule_seed) is not int or not 0 <= self.schedule_seed < 2**64:
            _fail("config schedule_seed must be an unsigned 64-bit integer")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "PostR7ProviderConfig":
        if set(payload) != _CONFIG_FIELDS:
            _fail("post-R7 provider config has an unexpected key set")
        if payload.get("schema") != CONFIG_SCHEMA:
            _fail("post-R7 provider config schema drifted")
        raw_paths = (payload.get("r7_root"), payload.get("target_root"))
        paths: list[Path] = []
        for value, field in zip(raw_paths, ("r7_root", "target_root"), strict=True):
            if not isinstance(value, str) or not value or not Path(value).is_absolute():
                _fail(f"config {field} must be an absolute path")
            paths.append(Path(value))
        epoch_budget = payload.get("epoch_budget")
        if type(epoch_budget) is not int or epoch_budget not in _SCHEDULE.FORMAL_SOURCE_TRAINING_EPOCH_BUDGETS:
            _fail("config epoch_budget must be exactly 100 or 500")
        schedule_seed = payload.get("schedule_seed")
        if type(schedule_seed) is not int or not 0 <= schedule_seed < 2**64:
            _fail("config schedule_seed must be an unsigned 64-bit integer")
        return cls(
            r7_root=paths[0],
            target_root=paths[1],
            epoch_budget=epoch_budget,
            schedule_seed=schedule_seed,
        )


def _config_from_environment() -> PostR7ProviderConfig:
    config_text = os.environ.get(CONFIG_PATH_ENV)
    expected_text = os.environ.get(CONFIG_SHA256_ENV)
    if not config_text or not expected_text:
        _fail(
            f"{CONFIG_PATH_ENV} and {CONFIG_SHA256_ENV} are both required"
        )
    config_path = Path(config_text)
    if not config_path.is_absolute():
        _fail(f"{CONFIG_PATH_ENV} must be an absolute path")
    expected = _digest(expected_text, field=CONFIG_SHA256_ENV)
    actual = _file_sha256(config_path, field="post-R7 provider config")
    if actual != expected:
        _fail("post-R7 provider config SHA-256 disagrees")
    return PostR7ProviderConfig.from_payload(
        _read_canonical_json(config_path, field="post-R7 provider config")
    )


def _schedule_receipt_identity(
    schedule: object,
    *,
    expected_epoch_budget: int | None = None,
    expected_schedule_seed: int | None = None,
    expected_gate: object | None = None,
    expected_records: tuple[object, ...] | None = None,
) -> str:
    """Authenticate the complete deterministic C3 schedule receipt.

    The schedule builder is deliberately a separate seam.  Rechecking the
    receipt against its immutable object fields here prevents a future
    builder/loader drift from turning a self-consistent but unrelated receipt
    into provider identity.
    """

    if expected_epoch_budget is None:
        _fail("C3 schedule config epoch budget is required")
    if (
        type(expected_epoch_budget) is not int
        or expected_epoch_budget
        not in _SCHEDULE.FORMAL_SOURCE_TRAINING_EPOCH_BUDGETS
    ):
        _fail("C3 schedule config epoch budget is not frozen")
    schedule_epoch_budget = getattr(schedule, "epoch_budget", None)
    if schedule_epoch_budget != expected_epoch_budget:
        _fail("C3 schedule epoch budget disagrees with config")
    if expected_schedule_seed is not None:
        if (
            type(expected_schedule_seed) is not int
            or not 0 <= expected_schedule_seed < 2**64
        ):
            _fail("C3 schedule config seed is not an unsigned 64-bit integer")
        if getattr(schedule, "schedule_seed", None) != expected_schedule_seed:
            _fail("C3 schedule seed disagrees with config")

    receipt_sha = getattr(schedule, "receipt_sha256", None)
    _digest(receipt_sha, field="C3 schedule receipt_sha256")
    receipt = getattr(schedule, "receipt", None)
    if not isinstance(receipt, Mapping):
        _fail("C3 schedule does not expose a receipt mapping")
    unsigned = dict(receipt)
    declared = unsigned.pop("receipt_sha256", None)
    if declared != receipt_sha or _SCHEDULE.canonical_sha256(unsigned) != declared:
        _fail("C3 schedule receipt seal disagrees")
    expected_fields = {
        "schema",
        "status",
        "claim_ceiling",
        "gate_decision",
        "worlds",
        "records",
        "record_panel_sha256",
        "target_surfaces",
        "matched_placebo",
        "sampling",
        "source_training_epoch_budget",
        "batch_schedule",
        "sources",
        "boundaries",
        "receipt_sha256",
    }
    if set(receipt) != expected_fields:
        _fail("C3 schedule receipt field set drifted")
    if (
        receipt.get("schema") != _SCHEDULE.SOURCE_SCHEDULE_SCHEMA
        or receipt.get("status") != _SCHEDULE.SOURCE_SCHEDULE_STATUS
        or receipt.get("claim_ceiling")
        != _SCHEDULE.SOURCE_SCHEDULE_CLAIM_CEILING
        or receipt.get("source_training_epoch_budget") != expected_epoch_budget
    ):
        _fail("C3 schedule receipt schema/status/claim/budget drifted")

    gate = getattr(schedule, "gate_decision", None)
    if type(gate) is not _SCHEDULE.R7GoDecisionBinding:
        _fail("C3 schedule gate binding is not the current R7 binding")
    try:
        gate.verify()
        gate_payload = gate.to_payload()
        gate_binding_sha = gate.binding_sha256
    except Exception as cause:
        _fail("C3 schedule gate binding failed verification", cause=cause)
    gate_receipt = receipt.get("gate_decision")
    expected_gate_receipt = json.loads(
        _SCHEDULE.canonical_bytes(
            {**gate_payload, "binding_sha256": gate_binding_sha}
        ).decode("ascii")
    )
    if not isinstance(gate_receipt, Mapping) or dict(gate_receipt) != expected_gate_receipt:
        _fail("C3 schedule receipt gate binding disagrees")
    if expected_gate is not None:
        if type(expected_gate) is not _SCHEDULE.R7GoDecisionBinding:
            _fail("C3 schedule expected gate is not the current R7 binding")
        try:
            expected_gate.verify()
            if expected_gate.to_payload() != gate_payload:
                _fail("C3 schedule gate binding disagrees with authenticated R7")
        except V023PostR7ProviderFactoryError:
            raise
        except Exception as cause:
            _fail("authenticated R7 gate binding could not be compared", cause=cause)

    if receipt.get("worlds") != list(_SCHEDULE.R7_WORLDS):
        _fail("C3 schedule receipt worlds drifted")
    try:
        records = tuple(getattr(schedule, "records"))
    except (AttributeError, TypeError) as cause:
        _fail("C3 schedule records are missing", cause=cause)
    if not records:
        _fail("C3 schedule records are empty")
    try:
        record_entries = _SCHEDULE._record_entries(records)
        record_panel_sha = _SCHEDULE.canonical_record_panel_sha256(records)
    except Exception as cause:
        _fail("C3 schedule records failed canonical reauthentication", cause=cause)
    if receipt.get("records") != record_entries:
        _fail("C3 schedule receipt records disagree")
    if (
        receipt.get("record_panel_sha256") != record_panel_sha
        or getattr(schedule, "record_panel_sha256", None) != record_panel_sha
    ):
        _fail("C3 schedule record panel digest disagrees")
    if tuple(sorted({record.world_id for record in records})) != _SCHEDULE.R7_WORLDS:
        _fail("C3 schedule records do not cover the exact R7 worlds")
    if expected_records is not None:
        try:
            expected_record_panel_sha = _SCHEDULE.canonical_record_panel_sha256(
                expected_records
            )
        except Exception as cause:
            _fail("authenticated R7 records failed canonical comparison", cause=cause)
        if expected_record_panel_sha != record_panel_sha:
            _fail("C3 schedule records disagree with authenticated R7")

    target_surfaces = receipt.get("target_surfaces")
    if not isinstance(target_surfaces, Mapping) or set(target_surfaces) != {
        "informed",
        "neutral",
        "original_typed_surface_count",
        "neutral_lcsrs_anchor_surfaces_constructed",
        "differences_limited_to_supported",
        "reference_control_masked_targets_exact_zero",
    }:
        _fail("C3 schedule target-surface receipt is malformed")
    surfaces = getattr(schedule, "surfaces", None)
    try:
        if len(surfaces) != len(records):
            _fail("C3 schedule surface count disagrees with records")
    except TypeError as cause:
        _fail("C3 schedule surfaces are missing", cause=cause)
    if (
        target_surfaces.get("original_typed_surface_count") != len(records)
        or target_surfaces.get("neutral_lcsrs_anchor_surfaces_constructed") is not False
        or target_surfaces.get("differences_limited_to_supported") is not True
        or target_surfaces.get("reference_control_masked_targets_exact_zero")
        is not True
    ):
        _fail("C3 schedule target-surface boundary drifted")
    target_payloads: dict[str, Mapping[str, Any]] = {}
    for source in ("informed", "neutral"):
        targets = getattr(schedule, f"{source}_targets_by_anchor", None)
        try:
            target_payload = _SCHEDULE._target_panel_payload(
                records, tuple(targets), source=source
            )
        except Exception as cause:
            _fail(
                f"C3 schedule {source} target panel failed reauthentication",
                cause=cause,
            )
        if target_surfaces.get(source) != target_payload:
            _fail(f"C3 schedule receipt {source} target panel disagrees")
        target_payloads[source] = target_payload

    placebo = getattr(schedule, "matched_placebo", None)
    placebo_receipt = receipt.get("matched_placebo")
    if placebo is None or not isinstance(placebo_receipt, Mapping):
        _fail("C3 schedule matched-placebo receipt is missing")
    expected_placebo_fields = {
        "schema",
        "key",
        "key_sha256",
        "content_sha256",
        "mapping_count",
        "mappings_sha256",
        "eligible_supported_rows",
        "total_supported_rows",
        "coverage",
        "coverage_hex",
        "minimum_coverage",
        "minimum_coverage_hex",
        "meets_coverage_gate",
        "per_world",
        "world_crossing_count",
    }
    if set(placebo_receipt) != expected_placebo_fields:
        _fail("C3 schedule matched-placebo receipt field set drifted")
    if (
        placebo_receipt.get("schema") != _SCHEDULE.LCSRS_C3_PLACEBO_SCHEMA
        or placebo_receipt.get("key") != _SCHEDULE.PLACEBO_KEY
        or placebo_receipt.get("key_sha256") != _SCHEDULE.PLACEBO_KEY_SHA256
        or placebo_receipt.get("content_sha256")
        != getattr(placebo, "content_digest", None)
        or placebo_receipt.get("mapping_count") != len(placebo.mappings)
        or placebo_receipt.get("eligible_supported_rows")
        != placebo.eligible_supported_rows
        or placebo_receipt.get("total_supported_rows") != placebo.total_supported_rows
        or placebo_receipt.get("coverage") != placebo.coverage
        or placebo_receipt.get("coverage_hex") != float(placebo.coverage).hex()
        or placebo_receipt.get("minimum_coverage")
        != _SCHEDULE.LCSRS_C3_PLACEBO_MIN_COVERAGE
        or placebo_receipt.get("minimum_coverage_hex")
        != float(_SCHEDULE.LCSRS_C3_PLACEBO_MIN_COVERAGE).hex()
        or placebo_receipt.get("meets_coverage_gate") is not True
        or placebo_receipt.get("world_crossing_count") != 0
    ):
        _fail("C3 schedule matched-placebo receipt disagrees")
    try:
        mappings = _SCHEDULE._mapping_payload(placebo)
        if placebo_receipt.get("mappings_sha256") != _SCHEDULE.canonical_sha256(
            mappings
        ):
            _fail("C3 schedule matched-placebo mapping digest disagrees")
    except V023PostR7ProviderFactoryError:
        raise
    except Exception as cause:
        _fail("C3 schedule matched-placebo mappings failed reauthentication", cause=cause)

    sampling = receipt.get("sampling")
    if not isinstance(sampling, Mapping) or set(sampling) != {
        "rng",
        "bit_generator",
        "seed_domain",
        "explicit_seed",
        "seed_derivation_sha256",
        "derived_pcg64_seed_uint128",
        "learner_config_sha256",
        "batch_size",
        "paired_draw_identity",
    }:
        _fail("C3 schedule sampling receipt is malformed")
    schedule_seed = getattr(schedule, "schedule_seed", None)
    if (
        type(schedule_seed) is not int
        or not 0 <= schedule_seed < 2**64
        or sampling.get("rng") != _SCHEDULE.SCHEDULE_RNG
        or sampling.get("bit_generator") != "PCG64"
        or sampling.get("seed_domain") != _SCHEDULE.SCHEDULE_SEED_DOMAIN
        or sampling.get("explicit_seed") != schedule_seed
        or sampling.get("learner_config_sha256")
        != _SCHEDULE.LCSRS_C3_LEARNER_CONFIG_SHA256
        or sampling.get("batch_size") != _SCHEDULE.LCSRS_C3_BATCH_SIZE
        or sampling.get("paired_draw_identity") != "anchor-class-user-action"
    ):
        _fail("C3 schedule sampling seed/configuration drifted")
    try:
        seed_derivation_sha, derived_seed = _SCHEDULE._derive_pcg64_seed(schedule_seed)
    except Exception as cause:
        _fail("C3 schedule seed derivation failed", cause=cause)
    if (
        sampling.get("seed_derivation_sha256") != seed_derivation_sha
        or sampling.get("derived_pcg64_seed_uint128") != str(derived_seed)
        or getattr(schedule, "derived_pcg64_seed", None) != derived_seed
    ):
        _fail("C3 schedule derived seed disagrees")

    batch_schedule = receipt.get("batch_schedule")
    if not isinstance(batch_schedule, Mapping) or set(batch_schedule) != {
        "batch_count_by_source",
        "entries",
        "paired_draw_schedule_sha256",
        "informed_batch_schedule_sha256",
        "neutral_batch_schedule_sha256",
    }:
        _fail("C3 schedule batch receipt is malformed")
    try:
        informed_batches = tuple(schedule.informed_batches)
        neutral_batches = tuple(schedule.neutral_batches)
    except (AttributeError, TypeError) as cause:
        _fail("C3 schedule batches are missing", cause=cause)
    if len(informed_batches) != expected_epoch_budget or len(neutral_batches) != expected_epoch_budget:
        _fail("C3 schedule batch count disagrees with config")
    counts = batch_schedule.get("batch_count_by_source")
    if counts != {"informed": expected_epoch_budget, "neutral": expected_epoch_budget}:
        _fail("C3 schedule receipt batch count disagrees")
    entries = batch_schedule.get("entries")
    if not isinstance(entries, list) or len(entries) != expected_epoch_budget:
        _fail("C3 schedule receipt batch entry count disagrees")
    expected_entries: list[dict[str, Any]] = []
    for epoch_index, (informed, neutral) in enumerate(
        zip(informed_batches, neutral_batches, strict=True)
    ):
        try:
            informed_batch = _SCHEDULE._batch_payload(informed)
            neutral_batch = _SCHEDULE._batch_payload(neutral)
            draw = _SCHEDULE._draw_payload(informed)
            neutral_draw = _SCHEDULE._draw_payload(neutral)
        except Exception as cause:
            _fail(f"C3 schedule batch {epoch_index} failed reauthentication", cause=cause)
        if draw != neutral_draw:
            _fail(f"C3 schedule paired draw {epoch_index} diverged")
        expected_entries.append(
            {
                "epoch_index": epoch_index,
                "paired_draw_sha256": draw["sha256"],
                "informed_batch_sha256": informed_batch["sha256"],
                "neutral_batch_sha256": neutral_batch["sha256"],
            }
        )
    if entries != expected_entries:
        _fail("C3 schedule receipt batch entries disagree")
    expected_schedule_hashes = {
        "paired_draw_schedule_sha256": _SCHEDULE.canonical_sha256(
            {
                "domain": f"{_SCHEDULE._BATCH_DOMAIN}:PAIRED_DRAW_SCHEDULE",
                "entries": [entry["paired_draw_sha256"] for entry in entries],
            }
        ),
        "informed_batch_schedule_sha256": _SCHEDULE.canonical_sha256(
            {
                "domain": f"{_SCHEDULE._BATCH_DOMAIN}:INFORMED_SCHEDULE",
                "entries": [entry["informed_batch_sha256"] for entry in entries],
            }
        ),
        "neutral_batch_schedule_sha256": _SCHEDULE.canonical_sha256(
            {
                "domain": f"{_SCHEDULE._BATCH_DOMAIN}:NEUTRAL_SCHEDULE",
                "entries": [entry["neutral_batch_sha256"] for entry in entries],
            }
        ),
    }
    if any(
        batch_schedule.get(field) != expected
        or getattr(schedule, field, None) != expected
        for field, expected in expected_schedule_hashes.items()
    ):
        _fail("C3 schedule batch schedule digest disagrees")

    sources = receipt.get("sources")
    if not isinstance(sources, Mapping) or set(sources) != {"neutral", "informed"}:
        _fail("C3 schedule receipt sources are malformed")
    source_ids: dict[str, str] = {}
    for source in ("neutral", "informed"):
        entry = sources.get(source)
        if not isinstance(entry, Mapping) or set(entry) != {"source_id", "source_sha256"}:
            _fail(f"C3 schedule receipt {source} source entry is malformed")
        source_id = getattr(schedule, f"{source}_source_id", None)
        source_sha256 = _digest(
            entry.get("source_sha256"),
            field=f"C3 schedule {source} source_sha256",
        )
        if entry.get("source_id") != source_id or not isinstance(source_id, str):
            _fail(f"C3 schedule receipt {source} source identity disagrees")
        source_ids[source] = source_id
        expected_id, expected_sha = _SCHEDULE._source_identity(
            source=source,
            gate_binding_sha256=gate_binding_sha,
            record_panel_sha256=record_panel_sha,
            target_panel_sha256=str(target_payloads[source]["sha256"]),
            batch_schedule_sha256=str(
                expected_schedule_hashes[f"{source}_batch_schedule_sha256"]
            ),
            placebo_sha256=(
                None
                if source == "informed"
                else str(placebo.content_digest)
            ),
            epoch_budget=expected_epoch_budget,
            seed_derivation_sha256=seed_derivation_sha,
        )
        if source_id != expected_id or source_sha256 != expected_sha:
            _fail(f"C3 schedule {source} source hash disagrees")
    if source_ids["neutral"] == source_ids["informed"]:
        _fail("C3 schedule informed and neutral source identities alias")

    if receipt.get("boundaries") != {
        "simulator_run": False,
        "learner_update": False,
        "model_fit": False,
        "test_split_opened": False,
        "episode_training": False,
        "artifact_write": False,
    }:
        _fail("C3 schedule receipt crossed a forbidden boundary")
    return receipt_sha


@dataclass(frozen=True, slots=True)
class V023PostR7Provider:
    """Thin provider facade with an identity bound to all source authorities."""

    _delegate: object
    _identity_payload: Mapping[str, Any]
    _identity: str

    @property
    def provider_identity(self) -> str:
        """Stable compact identity consumed by the unchanged runner."""

        return self._identity

    @property
    def planned_epoch_budget(self) -> int:
        """The exact source-training budget bound into this provider."""

        return int(self._identity_payload["epoch_budget"])

    @property
    def provider_identity_payload(self) -> Mapping[str, Any]:
        """The bound fields, returned as a defensive plain mapping."""

        return deepcopy(dict(self._identity_payload))

    def next_batch(self, *, route: str, source: str, update_cursor: int) -> object:
        return self._delegate.next_batch(
            route=route, source=source, update_cursor=update_cursor
        )

    def sampler_state(self) -> Mapping[str, Any]:
        return self._delegate.sampler_state()

    def load_sampler_state(self, state: Mapping[str, Any]) -> None:
        self._delegate.load_sampler_state(state)


def build_provider(config: PostR7ProviderConfig) -> V023PostR7Provider:
    """Authenticate inputs, construct paired C3 sources, and return a provider."""

    if type(config) is not PostR7ProviderConfig:
        _fail("build_provider requires PostR7ProviderConfig")
    r7 = authenticate_r7_go(config.r7_root)
    target_root = _regular_dir(config.target_root, field="C1/C2 target root")
    target_manifest_sha = _file_sha256(
        target_root / "MANIFEST.sha256", field="C1/C2 target MANIFEST.sha256"
    )
    try:
        target_artifact = _BRIDGE.load_completed_target_artifact(target_root)
        if _file_sha256(target_root / "MANIFEST.sha256", field="C1/C2 target manifest") != target_manifest_sha:
            _fail("C1/C2 target root changed during authentication")
        schedule = _SCHEDULE.build_v023_c3_source_schedule(
            r7.records,
            r7_go=r7.binding,
            epoch_budget=config.epoch_budget,
            schedule_seed=config.schedule_seed,
        )
        receipt_sha = _schedule_receipt_identity(
            schedule,
            expected_epoch_budget=config.epoch_budget,
            expected_schedule_seed=config.schedule_seed,
            expected_gate=r7.binding,
            expected_records=r7.records,
        )
        neutral_inputs = _BRIDGE.load_lcsrs_c3_inputs(
            schedule.surfaces,
            schedule.neutral_batches,
            normalized_targets_by_anchor=schedule.neutral_targets_by_anchor,
        )
        informed_inputs = _BRIDGE.load_lcsrs_c3_inputs(
            schedule.surfaces,
            schedule.informed_batches,
            normalized_targets_by_anchor=schedule.informed_targets_by_anchor,
        )
        neutral = _BRIDGE.C3SourceBinding(
            source="neutral",
            source_id=schedule.neutral_source_id,
            inputs=neutral_inputs,
        )
        informed = _BRIDGE.C3SourceBinding(
            source="informed",
            source_id=schedule.informed_source_id,
            inputs=informed_inputs,
        )
        delegate = _BRIDGE.V023ProviderOrchestratorBridge(
            target_artifact,
            c3_neutral=neutral,
            c3_informed=informed,
            planned_source_training_epochs=config.epoch_budget,
        )
        if not isinstance(delegate, _BRIDGE.DeterministicRouteBatchProvider):
            _fail("post-R7 bridge does not satisfy the runner provider protocol")
    except V023PostR7ProviderFactoryError:
        raise
    except Exception as cause:
        _fail("post-R7 provider construction failed closed", cause=cause)

    identity_payload = {
        "schema": IDENTITY_SCHEMA,
        "target_manifest_sha256": target_manifest_sha,
        "c3_schedule_receipt_sha256": receipt_sha,
        "epoch_budget": config.epoch_budget,
        "c3_source_ids": {
            "neutral": schedule.neutral_source_id,
            "informed": schedule.informed_source_id,
        },
    }
    identity_digest = _SCHEDULE.canonical_sha256(identity_payload)
    identity = f"{FACTORY_SCHEMA}:{identity_digest}"
    if len(identity) > 512:
        _fail("provider identity exceeds runner limit")
    return V023PostR7Provider(
        _delegate=delegate,
        _identity_payload=MappingProxyType(identity_payload),
        _identity=identity,
    )


def make_provider() -> V023PostR7Provider:
    """Zero-argument runner factory using the explicitly authenticated config."""

    return build_provider(_config_from_environment())


__all__ = [
    "CONFIG_PATH_ENV",
    "CONFIG_SCHEMA",
    "CONFIG_SHA256_ENV",
    "FACTORY_SCHEMA",
    "IDENTITY_SCHEMA",
    "PostR7ProviderConfig",
    "R7GoAuthentication",
    "V023PostR7Provider",
    "V023PostR7ProviderFactoryError",
    "authenticate_r7_go",
    "build_provider",
    "make_provider",
]
