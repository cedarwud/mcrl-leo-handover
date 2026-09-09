"""Fail-closed C1/C2-only provider factory for the V0.23 successor.

The factory consumes a producer-sealed target root through the existing typed
adapter.  It does not construct targets, import an R7 authority, run physics,
or provide a fallback data source.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
from types import MappingProxyType, ModuleType
from typing import Any

import numpy as np

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014NormalizedPairBatch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TARGET_ADAPTER_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py"
)
PROVIDER_PROTOCOL_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-five-arm-learner-orchestrator/"
    "v023_five_arm_learner_orchestrator.py"
)
DEFAULT_LEARNER_MANIFEST_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-two-route-source-training-runner/"
    "LEARNER-MANIFEST.json"
)
CONTRACT_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-c1c2-successor/"
    "V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md"
)
SCIENTIFIC_DECLARATION_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-c1c2-successor/"
    "V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md"
)
PREDECESSOR_MANIFEST_PATH = (
    REPO / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json"
)
PREDECESSOR_MANIFEST_SIDECAR_PATH = PREDECESSOR_MANIFEST_PATH.with_suffix(".sha256")
PREREG_PATH = REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"

CONFIG_PATH_ENV = "MCRL_V023_C1C2_PROVIDER_CONFIG_PATH"
CONFIG_SHA256_ENV = "MCRL_V023_C1C2_PROVIDER_CONFIG_SHA256"
LEARNER_MANIFEST_PATH_ENV = "MCRL_V023_C1C2_LEARNER_MANIFEST_PATH"
CONFIG_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-provider-factory-config-v3"
FACTORY_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-provider-factory-v3"
IDENTITY_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-provider-identity-v3"
SAMPLER_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-provider-sampler-v3"
LEARNER_MANIFEST_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-learner-manifest-v1"
)
LEARNER_MANIFEST_STATUS = "FROZEN"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY"
)
PROVIDER_IDENTITY_FIELDS = frozenset(
    {
        "schema",
        "routes",
        "sources",
        "train_seed",
        "epoch_budget",
        "contract_sha256",
        "model_config_sha256",
        "provider_config_sha256",
        "factory_code_sha256",
        "target_adapter_code_sha256",
        "provider_protocol_code_sha256",
        "learner_manifest_path",
        "learner_manifest_sha256",
        "learner_runtime",
        "learner_runtime_sha256",
        "arm_independent_target_identity",
        "arm_independent_target_identity_sha256",
        "consumed_file_order_plan_sha256",
        "predecessor_manifest_sha256",
        "prereg_sha256",
        "scientific_declaration_sha256",
        "tle_file_set_sha256",
    }
)

ROUTES = ("C1", "C2")
SOURCES = ("neutral", "informed")
EXPECTED_WORLDS = tuple(range(2026121705, 2026121713))
TRAIN_SEED = 2927175120652069826
MODEL_CONFIG_SHA256 = "9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d"
EPOCH_BUDGET = 100
EXPECTED_LAMBDA_HEX = "0x1.c3c0a7b6b86d3p+26"
EXPECTED_KAPPA_HEX = "0x1.2cea89d260f2ap+33"
EXPECTED_INTERVAL_HEX = "0x1.e147ae147ae15p+4"
EXPECTED_C1_STATE_DIM = 228
EXPECTED_C2_STATE_DIM = 448
EXPECTED_ACTION_DIM = 28

_CONFIG_FIELDS = frozenset(
    {
        "schema",
        "contract_sha256",
        "target_root",
        "target_manifest_sha256",
        "target_receipt_sha256",
        "learner_manifest_sha256",
        "model_config_sha256",
        "train_seed",
        "epoch_budget",
    }
)
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_TOKEN_RE = re.compile(r"(?<![a-z0-9])(r7|c3|q3)(?![a-z0-9])", re.I)

LEARNER_RUNTIME_ROOT_MODULES = MappingProxyType(
    {
        ".scratch/multi-catfish-v023-two-route-source-training-runner/"
        "ee_axis_two_route_model.py": "ee_axis_two_route_model",
        ".scratch/multi-catfish-v023-two-route-source-training-runner/"
        "v023_two_route_learner_orchestrator.py": "v023_two_route_learner_orchestrator",
        ".scratch/multi-catfish-v023-two-route-source-training-runner/"
        "v023_two_route_source_training_runner.py": "v023_two_route_source_training_runner",
        ".scratch/multi-catfish-v023-heterogeneous-trainer/"
        "v023_heterogeneous_trainer.py": "v023_heterogeneous_trainer",
    }
)


class V023C1C2ProviderFactoryError(RuntimeError):
    """A successor provider input or deterministic request is inadmissible."""


def _fail(message: str, *, cause: BaseException | None = None) -> None:
    if cause is None:
        raise V023C1C2ProviderFactoryError(message)
    raise V023C1C2ProviderFactoryError(message) from cause


def _import_exact_module(name: str, path: Path) -> ModuleType:
    """Import a module by its natural name and require its exact source origin."""

    expected = path.resolve(strict=True)
    existing = sys.modules.get(name)
    if existing is None:
        directory = str(expected.parent)
        sys.path.insert(0, directory)
        try:
            existing = importlib.import_module(name)
        except Exception as cause:
            _fail(f"cannot import required module {name}", cause=cause)
        finally:
            if sys.path and sys.path[0] == directory:
                sys.path.pop(0)
            else:
                try:
                    sys.path.remove(directory)
                except ValueError:
                    pass
    module_file = getattr(existing, "__file__", None)
    if not isinstance(module_file, str):
        _fail(f"required module {name} has no source origin")
    try:
        origin = Path(module_file).resolve(strict=True)
    except OSError as cause:
        _fail(f"required module {name} origin is unavailable", cause=cause)
    if origin != expected:
        _fail(f"required module {name} loaded from an unexpected origin")
    return existing


_TARGET = _import_exact_module("target_batch_adapter", TARGET_ADAPTER_PATH)
_PROTOCOL = _import_exact_module(
    "v023_five_arm_learner_orchestrator", PROVIDER_PROTOCOL_PATH
)
DeterministicRouteBatchProvider = _PROTOCOL.DeterministicRouteBatchProvider
ProvidedRouteBatch = _PROTOCOL.ProvidedRouteBatch


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _fail(f"{field} must be a lowercase SHA-256 digest")
    return value


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
    except (TypeError, ValueError, UnicodeError) as cause:
        _fail("value cannot be canonically encoded", cause=cause)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)[:-1]).hexdigest()


def _file_sha256(path: Path, *, field: str = "file") -> str:
    if path.is_symlink() or not path.is_file():
        _fail(f"{field} must be a regular non-symlink file")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as cause:
        _fail(f"cannot hash {field}", cause=cause)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"canonical JSON repeats key {key}")
        result[key] = value
    return result


def _read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        _fail(f"{field} must be a regular non-symlink file")
    try:
        raw = path.read_bytes()
        payload = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: _fail(
                f"{field} contains non-standard constant {value}"
            ),
        )
    except V023C1C2ProviderFactoryError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as cause:
        _fail(f"{field} is not canonical ASCII JSON", cause=cause)
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        _fail(f"{field} is not a canonical JSON object")
    return payload


def _forbidden_text(value: str, *, field: str, reject_test: bool = True) -> None:
    if _FORBIDDEN_TOKEN_RE.search(value):
        _fail(f"{field} names a forbidden R7/C3/Q3 dependency")
    if reject_test and "TEST" in value:
        _fail(f"{field} names the closed TEST split")


def _absolute_path(value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        _fail(f"config {field} must be a nonempty absolute path")
    _forbidden_text(value, field=f"config {field}")
    return Path(value)


@dataclass(frozen=True, slots=True)
class C1C2ProviderConfig:
    contract_sha256: str
    target_root: Path
    target_manifest_sha256: str
    target_receipt_sha256: str
    learner_manifest_sha256: str
    model_config_sha256: str
    train_seed: int
    epoch_budget: int

    def __post_init__(self) -> None:
        for name in (
            "contract_sha256",
            "target_manifest_sha256",
            "target_receipt_sha256",
            "learner_manifest_sha256",
            "model_config_sha256",
        ):
            _digest(getattr(self, name), field=f"config {name}")
        if not isinstance(self.target_root, Path) or not self.target_root.is_absolute():
            _fail("config target_root must be an absolute Path")
        _forbidden_text(str(self.target_root), field="config target_root")
        if type(self.train_seed) is not int or self.train_seed != TRAIN_SEED:
            _fail(f"config train_seed must be exactly {TRAIN_SEED}")
        if self.model_config_sha256 != MODEL_CONFIG_SHA256:
            _fail("config model_config_sha256 must bind the frozen successor JSON")
        if type(self.epoch_budget) is not int or self.epoch_budget != EPOCH_BUDGET:
            _fail(f"config epoch_budget must be exactly {EPOCH_BUDGET}")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "C1C2ProviderConfig":
        if not isinstance(payload, Mapping):
            _fail("successor provider config must be a mapping")
        keys = set(payload)
        if any(isinstance(key, str) and key.lower().startswith("r7_") for key in keys):
            _fail("successor provider config may not name R7")
        if keys != _CONFIG_FIELDS:
            _fail("successor provider config has an unexpected key set")
        if payload.get("schema") != CONFIG_SCHEMA:
            _fail("successor provider config schema drifted")
        return cls(
            contract_sha256=_digest(
                payload.get("contract_sha256"), field="config contract_sha256"
            ),
            target_root=_absolute_path(payload.get("target_root"), field="target_root"),
            target_manifest_sha256=_digest(
                payload.get("target_manifest_sha256"),
                field="config target_manifest_sha256",
            ),
            target_receipt_sha256=_digest(
                payload.get("target_receipt_sha256"),
                field="config target_receipt_sha256",
            ),
            learner_manifest_sha256=_digest(
                payload.get("learner_manifest_sha256"),
                field="config learner_manifest_sha256",
            ),
            model_config_sha256=_digest(
                payload.get("model_config_sha256"),
                field="config model_config_sha256",
            ),
            train_seed=payload.get("train_seed"),
            epoch_budget=payload.get("epoch_budget"),
        )

    def payload(self) -> dict[str, Any]:
        return {
            "schema": CONFIG_SCHEMA,
            "contract_sha256": self.contract_sha256,
            "target_root": str(self.target_root),
            "target_manifest_sha256": self.target_manifest_sha256,
            "target_receipt_sha256": self.target_receipt_sha256,
            "learner_manifest_sha256": self.learner_manifest_sha256,
            "model_config_sha256": self.model_config_sha256,
            "train_seed": self.train_seed,
            "epoch_budget": self.epoch_budget,
        }


def _config_from_environment() -> tuple[C1C2ProviderConfig, str]:
    path_text = os.environ.get(CONFIG_PATH_ENV)
    expected_text = os.environ.get(CONFIG_SHA256_ENV)
    if not path_text or not expected_text:
        _fail(f"{CONFIG_PATH_ENV} and {CONFIG_SHA256_ENV} are both required")
    config_path = _absolute_path(path_text, field=CONFIG_PATH_ENV)
    expected = _digest(expected_text, field=CONFIG_SHA256_ENV)
    if _file_sha256(config_path, field="successor provider config") != expected:
        _fail("successor provider config SHA-256 disagrees")
    return (
        C1C2ProviderConfig.from_payload(
            _read_canonical_json(config_path, field="successor provider config")
        ),
        expected,
    )


def _safe_manifest_path(
    relative: object, *, field: str, reject_forbidden_tokens: bool = True
) -> str:
    if not isinstance(relative, str) or not relative:
        _fail(f"{field} must be a nonempty relative path")
    path = Path(relative)
    if (
        path.is_absolute()
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail(f"{field} is not a safe relative path")
    if reject_forbidden_tokens:
        _forbidden_text(relative, field=field)
    return path.as_posix()


def _module_path(module_name: str) -> Path | None:
    """Resolve an in-checkout import without executing it."""

    if module_name.startswith("mcrl"):
        base = REPO / "src" / Path(*module_name.split("."))
        candidates = (base.with_suffix(".py"), base / "__init__.py")
    else:
        candidates = tuple(
            REPO / relative
            for relative, natural_name in LEARNER_RUNTIME_ROOT_MODULES.items()
            if natural_name == module_name
        )
    for candidate in candidates:
        if candidate.is_file() and not candidate.is_symlink():
            return candidate.resolve(strict=True)
    return None


def _module_name_for_path(path: Path) -> str:
    relative = path.relative_to(REPO)
    if relative.parts[:2] == ("src", "mcrl"):
        parts = list(relative.with_suffix("").parts[1:])
        if parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
    return path.stem


def _package_initializers(path: Path) -> tuple[Path, ...]:
    relative = path.relative_to(REPO)
    if relative.parts[:2] != ("src", "mcrl"):
        return ()
    parents: list[Path] = []
    current = path.parent
    src = (REPO / "src").resolve(strict=True)
    while current != src:
        initializer = current / "__init__.py"
        if initializer.is_file() and not initializer.is_symlink():
            parents.append(initializer.resolve(strict=True))
        current = current.parent
    return tuple(parents)


def _absolute_import_name(
    *, current_module: str, current_path: Path, imported: str | None, level: int
) -> str:
    if level == 0:
        return imported or ""
    package = current_module if current_path.name == "__init__.py" else current_module.rpartition(".")[0]
    parts = package.split(".") if package else []
    if level > len(parts) + 1:
        return ""
    prefix = parts[: len(parts) - level + 1]
    if imported:
        prefix.extend(imported.split("."))
    return ".".join(prefix)


def derive_learner_runtime_modules() -> Mapping[str, str]:
    """Derive the complete local learner import graph from its executing roots.

    The graph is rebuilt whenever a learner manifest is authenticated.  This
    deliberately includes imported donor modules even when the successor uses
    only their C1/C2 methods; importing the donor file executes those imports.
    """

    pending = [
        (REPO / relative).resolve(strict=True)
        for relative in LEARNER_RUNTIME_ROOT_MODULES
    ]
    discovered: dict[Path, str] = {}
    while pending:
        path = pending.pop()
        if path in discovered:
            continue
        module_name = _module_name_for_path(path)
        discovered[path] = module_name
        for initializer in _package_initializers(path):
            if initializer not in discovered:
                pending.append(initializer)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as cause:
            _fail(f"cannot derive learner imports from {path}", cause=cause)
        candidates: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                candidates.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = _absolute_import_name(
                    current_module=module_name,
                    current_path=path,
                    imported=node.module,
                    level=node.level,
                )
                if base:
                    candidates.add(base)
                if node.module is None and base:
                    candidates.update(f"{base}.{alias.name}" for alias in node.names)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
                and node.func.attr == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                candidates.add(node.args[0].value)
        for imported in candidates:
            imported_path = _module_path(imported)
            if imported_path is not None and imported_path not in discovered:
                pending.append(imported_path)
    return MappingProxyType(
        {
            path.relative_to(REPO).as_posix(): discovered[path]
            for path in sorted(discovered)
        }
    )


# Compatibility/export surface only.  Authentication derives the graph again
# so an added transitive import cannot be hidden by this import-time snapshot.
REQUIRED_LEARNER_RUNTIME_MODULES = derive_learner_runtime_modules()


def _verify_named_sidecar(path: Path) -> str:
    actual = _file_sha256(path, field=str(path.relative_to(REPO)))
    sidecar = path.with_name(path.name + ".sha256")
    try:
        observed = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeError) as cause:
        _fail(f"authority sidecar is unavailable: {sidecar}", cause=cause)
    if observed != f"{actual}  {path.name}\n":
        _fail(f"authority sidecar disagrees: {sidecar}")
    return actual


def _authenticate_local_authorities(config: C1C2ProviderConfig) -> Mapping[str, Any]:
    contract_sha = _file_sha256(CONTRACT_PATH, field="successor contract")
    if config.contract_sha256 != contract_sha:
        _fail("config contract_sha256 does not authenticate the contract on disk")
    declaration_sha = _verify_named_sidecar(SCIENTIFIC_DECLARATION_PATH)
    predecessor_sha = _file_sha256(
        PREDECESSOR_MANIFEST_PATH, field="predecessor preflight manifest"
    )
    try:
        sidecar = PREDECESSOR_MANIFEST_SIDECAR_PATH.read_text(encoding="ascii")
        predecessor = json.loads(PREDECESSOR_MANIFEST_PATH.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as cause:
        _fail("predecessor authority is unreadable", cause=cause)
    if sidecar != f"{predecessor_sha}  {PREDECESSOR_MANIFEST_PATH.name}\n":
        _fail("predecessor manifest sidecar disagrees")
    bindings = predecessor.get("bindings")
    configuration = predecessor.get("configuration")
    if not isinstance(bindings, list) or not isinstance(configuration, Mapping):
        _fail("predecessor authority schema drifted")
    prereg_rows = [row for row in bindings if row.get("role") == "preregistration"]
    if len(prereg_rows) != 1 or prereg_rows[0].get("path") != PREREG_PATH.relative_to(REPO).as_posix():
        _fail("predecessor authority does not name the frozen preregistration")
    prereg_sha = _file_sha256(PREREG_PATH, field="frozen preregistration")
    if prereg_rows[0].get("sha256") != prereg_sha:
        _fail("predecessor authority preregistration digest drifted")
    try:
        prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
        ephemeris = prereg["sections"]["ephemeris"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as cause:
        _fail("frozen preregistration ephemeris record is unavailable", cause=cause)
    expected = {
        "worlds": list(EXPECTED_WORLDS),
        "lambda_hex": EXPECTED_LAMBDA_HEX,
        "kappa_hex": EXPECTED_KAPPA_HEX,
    }
    if any(configuration.get(key) != value for key, value in expected.items()):
        _fail("predecessor producer constants/world panel drifted")
    if float(ephemeris["config"]["time_step_s"]).hex() != EXPECTED_INTERVAL_HEX:
        _fail("predecessor producer interval drifted")
    tle_sha = _digest(ephemeris.get("file_set_sha256"), field="frozen TLE file set")
    return MappingProxyType(
        {
            "contract_sha256": contract_sha,
            "scientific_declaration_sha256": declaration_sha,
            "predecessor_manifest_sha256": predecessor_sha,
            "prereg_sha256": prereg_sha,
            "tle_file_set_sha256": tle_sha,
        }
    )


def _target_snapshot(root: Path) -> Mapping[str, Any]:
    if root.is_symlink() or not root.is_dir():
        _fail("target_root must be an existing regular directory")
    manifest = root / "MANIFEST.sha256"
    receipt = root / "receipt.json"
    complete = root / "COMPLETE"
    manifest_sha = _file_sha256(manifest, field="target MANIFEST.sha256")
    receipt_sha = _file_sha256(receipt, field="target receipt.json")
    complete_sha = _file_sha256(complete, field="target COMPLETE")
    try:
        manifest_raw = manifest.read_bytes()
        manifest_text = manifest_raw.decode("ascii")
    except (OSError, UnicodeError) as cause:
        _fail("target MANIFEST.sha256 is unreadable", cause=cause)
    if not manifest_raw.endswith(b"\n") or b"\r" in manifest_raw:
        _fail("target MANIFEST.sha256 has noncanonical line endings")
    listed: dict[str, str] = {}
    for number, line in enumerate(manifest_text.splitlines(), start=1):
        parts = line.split("  ", 1)
        if len(parts) != 2:
            _fail(f"target manifest line {number} is malformed")
        digest = _digest(parts[0], field=f"target manifest line {number}")
        name = _safe_manifest_path(parts[1], field=f"target manifest line {number}")
        if Path(name).name != name or name in listed:
            _fail("target manifest must contain unique flat filenames")
        listed[name] = digest
    if tuple(listed) != tuple(sorted(listed)) or "receipt.json" not in listed:
        _fail("target manifest ordering or receipt closure drifted")
    for path in root.rglob("*"):
        if path.is_symlink():
            _fail(f"target root contains a symlink: {path.name}")
    actual_names = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    } - {"MANIFEST.sha256", "COMPLETE"}
    if actual_names != set(listed):
        _fail("target manifest file closure drifted")
    observed: dict[str, str] = {}
    for name, expected in listed.items():
        actual = _file_sha256(root / name, field=f"target file {name}")
        if actual != expected:
            _fail(f"target file digest drifted: {name}")
        observed[name] = actual
    try:
        complete_line = complete.read_bytes()
    except OSError as cause:
        _fail("target COMPLETE is unreadable", cause=cause)
    if complete_line != f"{manifest_sha}  MANIFEST.sha256\n".encode("ascii"):
        _fail("target COMPLETE does not bind MANIFEST.sha256")
    return MappingProxyType(
        {
            "manifest_sha256": manifest_sha,
            "receipt_sha256": receipt_sha,
            "complete_sha256": complete_sha,
            "files": MappingProxyType(observed),
        }
    )


def _validate_target_artifact(artifact: object) -> Mapping[str, Any]:
    if not isinstance(artifact, _TARGET.V023TargetArtifact):
        _fail("target adapter returned an unexpected artifact type")
    receipt = artifact.receipt
    if receipt.get("schema") != _TARGET.TARGET_GENERATION_SCHEMA:
        _fail("target producer schema drifted")
    if receipt.get("status") != _TARGET.TARGET_STATUS:
        _fail("target producer status drifted")
    if receipt.get("claim_ceiling") != _TARGET.TARGET_CLAIM_CEILING:
        _fail("target producer claim ceiling drifted")
    source_provenance = receipt.get("source")
    if not isinstance(source_provenance, Mapping):
        _fail("target producer source provenance is missing")
    for path_field in ("capture_path", "materialization_dir"):
        path_value = source_provenance.get(path_field)
        if not isinstance(path_value, str):
            _fail(f"target source {path_field} is malformed")
        if "TEST" in path_value:
            _fail(f"target source {path_field} names the closed TEST split")
    formula = receipt.get("formula_constants")
    expected_formula = {
        "lambda_bits_per_j": EXPECTED_LAMBDA_HEX,
        "kappa_bits": EXPECTED_KAPPA_HEX,
        "interval_s": EXPECTED_INTERVAL_HEX,
        "c2_schema": _TARGET.OPS3_SELECTED_PAIR_SCHEMA,
        "c2_target_unit": _TARGET.OPS3_TARGET_UNIT,
        "c2_horizon_steps": 3,
        "c2_terminal_rule": "PREDECLARED_H_T_TRUNCATION_TERMINAL_ZERO",
    }
    if formula != expected_formula:
        _fail("target formula constants drifted")
    if receipt.get("parallel_modes") != ["informed", "neutral"]:
        _fail("target modes are not the exact informed/neutral pair")
    if receipt.get("parallel_worlds") != list(EXPECTED_WORLDS):
        _fail("target worlds are not the exact frozen eight-world panel")
    expected_shards = [
        f"{mode}:{world}"
        for mode in ("informed", "neutral")
        for world in EXPECTED_WORLDS
    ]
    if receipt.get("parallel_shards") != expected_shards:
        _fail("target root does not contain the exact 16 mode-by-world shards")
    shards = receipt.get("shards")
    if not isinstance(shards, Mapping) or set(shards) != set(expected_shards):
        _fail("target shard receipt closure drifted")
    schedule = receipt.get("schedule")
    if not isinstance(schedule, Mapping) or set(schedule.get("shards", {})) != set(
        expected_shards
    ):
        _fail("target schedule does not cover the exact 16 shards")
    if tuple(inputs.mode for inputs in artifact.modes) != ("informed", "neutral"):
        _fail("target adapter did not return both modes in fixed order")

    consumed: dict[str, list[str]] = {}
    for source in ("informed", "neutral"):
        inputs = artifact.for_mode(source)
        for route, datasets, batch in (
            ("C1", inputs.c1_datasets, inputs.c1_pair_batch),
            ("C2", inputs.c2_datasets, inputs.c2_pair_batch),
        ):
            if tuple(entry.world for entry in datasets) != EXPECTED_WORLDS:
                _fail(f"{route}/{source} does not cover the exact frozen worlds")
            expected_names = [
                f"{route.lower()}-{source}-world-{world}.json"
                for world in EXPECTED_WORLDS
            ]
            if [entry.path.name for entry in datasets] != expected_names:
                _fail(f"{route}/{source} consumed-file order drifted")
            states = np.asarray(batch.states)
            masks = np.asarray(batch.action_masks)
            expected_dim = (
                EXPECTED_C1_STATE_DIM if route == "C1" else EXPECTED_C2_STATE_DIM
            )
            if states.ndim != 2 or states.shape[1] != expected_dim:
                _fail(f"{route}/{source} state dimension drifted")
            if masks.dtype != np.bool_ or masks.shape != (
                states.shape[0],
                EXPECTED_ACTION_DIM,
            ) or not np.all(np.any(masks, axis=1)):
                _fail(f"{route}/{source} masks drifted")
            if route == "C1" and not isinstance(batch, EEAxisPairBatch):
                _fail("C1 did not retain raw-surplus batch type")
            if route == "C2" and not isinstance(
                batch, EEAxisV014NormalizedPairBatch
            ):
                _fail("C2 did not retain already-normalized batch type")
            consumed[f"{route}:{source}"] = expected_names
    return MappingProxyType(
        {
            "routes": list(ROUTES),
            "modes": ["informed", "neutral"],
            "worlds": list(EXPECTED_WORLDS),
            "shards": expected_shards,
            "consumed_files": consumed,
            "source": deepcopy(dict(source_provenance)),
            "formula_constants": deepcopy(dict(formula)),
            "code_closure_sha256": receipt["code_closure_sha256"],
        }
    )


def _learner_manifest_path() -> Path:
    raw = os.environ.get(LEARNER_MANIFEST_PATH_ENV)
    path = Path(raw) if raw else DEFAULT_LEARNER_MANIFEST_PATH
    if not path.is_absolute():
        _fail(f"{LEARNER_MANIFEST_PATH_ENV} must be an absolute path")
    _forbidden_text(str(path), field="successor learner manifest path")
    return path


def _module_origin(module: ModuleType, *, module_name: str, expected: Path) -> Path:
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str) or not Path(module_file).is_absolute():
        _fail(f"learner runtime module {module_name} has no absolute origin")
    raw = Path(module_file)
    if raw.is_symlink() or not raw.is_file():
        _fail(f"learner runtime module {module_name} origin is not regular")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as cause:
        _fail(f"learner runtime module {module_name} origin is unavailable", cause=cause)
    if raw != expected or resolved != expected or not resolved.is_relative_to(REPO):
        _fail(f"learner runtime module {module_name} origin drifted")
    return resolved


def _authenticate_learner_manifest(
    path: Path, *, expected_sha256: str
) -> tuple[tuple[Mapping[str, str], ...], str]:
    required_runtime = derive_learner_runtime_modules()
    actual_manifest_sha = _file_sha256(path, field="successor learner manifest")
    if actual_manifest_sha != expected_sha256:
        _fail("successor learner manifest SHA-256 disagrees with config")
    payload = _read_canonical_json(path, field="successor learner manifest")
    if set(payload) != {"schema", "status", "claim_ceiling", "bindings"}:
        _fail("successor learner manifest field set drifted")
    if (
        payload.get("schema") != LEARNER_MANIFEST_SCHEMA
        or payload.get("status") != LEARNER_MANIFEST_STATUS
        or payload.get("claim_ceiling") != CLAIM_CEILING
    ):
        _fail("successor learner manifest header drifted")
    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        _fail("successor learner manifest bindings are missing")
    by_path: dict[str, Mapping[str, str]] = {}
    for index, binding in enumerate(bindings):
        if not isinstance(binding, Mapping) or set(binding) != {
            "path",
            "module",
            "sha256",
        }:
            _fail(f"successor learner binding {index} schema drifted")
        relative = _safe_manifest_path(
            binding.get("path"),
            field=f"successor learner binding {index}.path",
            # C3-named donor modules are admissible only when they are members
            # of the mechanically derived executing-code import graph below.
            reject_forbidden_tokens=False,
        )
        module_name = binding.get("module")
        if (
            not isinstance(module_name, str)
            or not module_name
            or module_name != module_name.strip()
        ):
            _fail(f"successor learner binding {index}.module is malformed")
        declared = _digest(
            binding.get("sha256"),
            field=f"successor learner binding {index}.sha256",
        )
        if relative in by_path:
            _fail("successor learner manifest repeats a runtime path")
        by_path[relative] = {
            "path": relative,
            "module": module_name,
            "sha256": declared,
        }
    missing = set(required_runtime) - set(by_path)
    extra = set(by_path) - set(required_runtime)
    if missing or extra:
        _fail(
            "successor learner manifest differs from the derived import graph: "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )
    if tuple(by_path) != tuple(sorted(by_path)):
        _fail("successor learner manifest bindings must be path sorted")

    observed: list[Mapping[str, str]] = []
    seen_modules: set[str] = set()
    for relative, binding in by_path.items():
        module_name = binding["module"]
        expected_module = required_runtime.get(relative)
        if module_name != expected_module:
            _fail(f"successor learner runtime module name drifted: {relative}")
        expected_path = (REPO / relative).resolve(strict=False)
        if not expected_path.is_relative_to(REPO):
            _fail("successor learner runtime escaped the checkout")
        try:
            module = _import_exact_module(module_name, expected_path)
        except (OSError, V023C1C2ProviderFactoryError):
            raise
        except Exception as cause:
            _fail(f"cannot import learner runtime module {module_name}", cause=cause)
        if module_name in seen_modules:
            _fail("successor learner manifest repeats a module name")
        seen_modules.add(module_name)
        origin = _module_origin(module, module_name=module_name, expected=expected_path)
        actual = _file_sha256(origin, field=f"learner runtime {relative}")
        if actual != binding["sha256"]:
            _fail(f"successor learner runtime digest drifted: {relative}")
        observed.append(
            MappingProxyType(
                {
                    "path": relative,
                    "module": module_name,
                    "loaded_from": str(origin),
                    "sha256": actual,
                }
            )
        )
    return tuple(observed), actual_manifest_sha


def _immutable(value: np.ndarray, *, dtype: np.dtype[Any]) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _copy_batch(
    batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch,
) -> EEAxisPairBatch | EEAxisV014NormalizedPairBatch:
    if isinstance(batch, EEAxisPairBatch):
        return EEAxisPairBatch(
            states=_immutable(batch.states, dtype=np.dtype(np.float32)),
            reference_actions=_immutable(
                batch.reference_actions, dtype=np.dtype(np.int64)
            ),
            candidate_actions=_immutable(
                batch.candidate_actions, dtype=np.dtype(np.int64)
            ),
            target_surplus_bits=_immutable(
                batch.target_surplus_bits, dtype=np.dtype(np.float64)
            ),
            action_masks=_immutable(batch.action_masks, dtype=np.dtype(np.bool_)),
        )
    return EEAxisV014NormalizedPairBatch(
        states=_immutable(batch.states, dtype=np.dtype(np.float32)),
        reference_actions=_immutable(
            batch.reference_actions, dtype=np.dtype(np.int64)
        ),
        candidate_actions=_immutable(
            batch.candidate_actions, dtype=np.dtype(np.int64)
        ),
        normalized_target_deltas=_immutable(
            batch.normalized_target_deltas, dtype=np.dtype(np.float64)
        ),
        action_masks=_immutable(batch.action_masks, dtype=np.dtype(np.bool_)),
    )


def _panel_id(
    *,
    route: str,
    source: str,
    members: tuple[str, ...],
    batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"MCRL_V023_C1C2_SUCCESSOR_AUTHENTICATED_PANEL_V3\0")
    digest.update(route.encode("ascii") + b"\0" + source.encode("ascii"))
    for member in members:
        digest.update(b"\0" + member.encode("ascii"))
    for field in (
        "states",
        "reference_actions",
        "candidate_actions",
        "target_surplus_bits"
        if isinstance(batch, EEAxisPairBatch)
        else "normalized_target_deltas",
        "action_masks",
    ):
        value = np.ascontiguousarray(np.asarray(getattr(batch, field)))
        digest.update(b"\0" + field.encode("ascii"))
        digest.update(value.dtype.str.encode("ascii"))
        digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
        digest.update(value.tobytes())
    return f"{route.lower()}-{source}-panel-{digest.hexdigest()}"


class V023C1C2Provider:
    """Deterministic two-route provider with exact resume and drift checks."""

    def __init__(
        self,
        *,
        artifact: object,
        config: C1C2ProviderConfig,
        target_snapshot: Mapping[str, Any],
        target_identity: Mapping[str, Any],
        learner_manifest_path: Path,
        learner_runtime: tuple[Mapping[str, str], ...],
        identity_payload: Mapping[str, Any],
        identity: str,
    ) -> None:
        self._artifact = artifact
        self._config = config
        self._target_snapshot = target_snapshot
        self._target_identity = target_identity
        self._learner_manifest_path = learner_manifest_path
        self._learner_runtime = learner_runtime
        self._identity_payload = MappingProxyType(deepcopy(dict(identity_payload)))
        self._identity = identity
        self._batches: dict[
            tuple[str, str], EEAxisPairBatch | EEAxisV014NormalizedPairBatch
        ] = {}
        self._source_members: dict[str, list[str]] = {}
        self._source_files: dict[str, list[str]] = {}
        for route in ROUTES:
            for source in SOURCES:
                inputs = artifact.for_mode(source)
                batch = (
                    inputs.c1_pair_batch if route == "C1" else inputs.c2_pair_batch
                )
                members = tuple(target_identity["consumed_files"][f"{route}:{source}"])
                file_id = _panel_id(
                    route=route, source=source, members=members, batch=batch
                )
                self._batches[(route, source)] = batch
                self._source_members[f"{route}:{source}"] = list(members)
                self._source_files[f"{route}:{source}"] = [file_id]
        self._positions = {
            (route, source): 0 for route in ROUTES for source in SOURCES
        }
        self._next_update_cursor = 0
        self._next_source_index = 0
        self._consumed_file_order: list[dict[str, Any]] = []

    @property
    def provider_identity(self) -> str:
        return self._identity

    @property
    def provider_identity_payload(self) -> Mapping[str, Any]:
        return deepcopy(dict(self._identity_payload))

    @property
    def planned_epoch_budget(self) -> int:
        return self._config.epoch_budget

    def _assert_integrity(self) -> None:
        for path, identity_field, label in (
            (Path(__file__).resolve(), "factory_code_sha256", "provider factory code"),
            (
                TARGET_ADAPTER_PATH,
                "target_adapter_code_sha256",
                "target adapter code",
            ),
            (
                PROVIDER_PROTOCOL_PATH,
                "provider_protocol_code_sha256",
                "provider protocol code",
            ),
        ):
            if _file_sha256(path, field=label) != self._identity_payload[identity_field]:
                _fail(f"{label} digest drifted after provider construction")
        current_target = _target_snapshot(self._config.target_root)
        if dict(current_target) != dict(self._target_snapshot):
            _fail("target root digest drifted after provider construction")
        if _file_sha256(
            self._learner_manifest_path, field="successor learner manifest"
        ) != self._config.learner_manifest_sha256:
            _fail("successor learner manifest drifted after provider construction")
        for record in self._learner_runtime:
            path = Path(record["loaded_from"])
            module = sys.modules.get(record["module"])
            if not isinstance(module, ModuleType):
                _fail(f"learner runtime module disappeared: {record['module']}")
            _module_origin(module, module_name=record["module"], expected=path)
            if _file_sha256(path, field=f"learner runtime {record['path']}") != record[
                "sha256"
            ]:
                _fail(f"learner runtime digest drifted: {record['path']}")

    def _expected_positions(
        self, *, update_cursor: int, source_index: int
    ) -> dict[tuple[str, str], int]:
        counts = {(route, source): 0 for route in ROUTES for source in SOURCES}
        completed_cycles, remainder = divmod(update_cursor, len(ROUTES))
        for route_index, route in enumerate(ROUTES):
            route_count = completed_cycles + int(route_index < remainder)
            for source in SOURCES:
                counts[(route, source)] = route_count
        if source_index:
            counts[(ROUTES[remainder], SOURCES[0])] += 1
        return counts

    def next_batch(
        self, *, route: str, source: str, update_cursor: int
    ) -> ProvidedRouteBatch:
        self._assert_integrity()
        if route not in ROUTES:
            _fail("requested route is outside the closed C1/C2 provider")
        if source not in SOURCES:
            _fail("requested source is outside informed/neutral")
        if type(update_cursor) is not int or update_cursor < 0:
            _fail("update_cursor must be a nonnegative exact integer")
        expected_route = ROUTES[self._next_update_cursor % len(ROUTES)]
        expected_source = SOURCES[self._next_source_index]
        if (
            update_cursor != self._next_update_cursor
            or route != expected_route
            or source != expected_source
        ):
            _fail("provider request violates deterministic route/source order")
        key = (route, source)
        position = self._positions[key]
        if position >= self._config.epoch_budget:
            _fail(f"{route}/{source} epoch schedule is exhausted")
        batch = _copy_batch(self._batches[key])
        file_id = self._source_files[f"{route}:{source}"][0]
        self._positions[key] = position + 1
        self._consumed_file_order.append(
            {
                "update_cursor": update_cursor,
                "route": route,
                "source": source,
                "file_id": file_id,
                "members": list(self._source_members[f"{route}:{source}"]),
            }
        )
        if self._next_source_index + 1 == len(SOURCES):
            self._next_source_index = 0
            self._next_update_cursor += 1
        else:
            self._next_source_index += 1
        return ProvidedRouteBatch(
            route=route, source=source, file_id=file_id, batch=batch
        )

    def sampler_state(self) -> Mapping[str, Any]:
        self._assert_integrity()
        return deepcopy(
            {
                "schema": SAMPLER_SCHEMA,
                "routes": list(ROUTES),
                "sources": list(SOURCES),
                "epoch_budget": self._config.epoch_budget,
                "provider_identity": self._identity,
                "source_files": self._source_files,
                "source_members": self._source_members,
                "cursors": {
                    f"{route}:{source}": self._positions[(route, source)]
                    for route in ROUTES
                    for source in SOURCES
                },
                "next_update_cursor": self._next_update_cursor,
                "next_source_index": self._next_source_index,
                "consumed_file_order": self._consumed_file_order,
            }
        )

    def load_sampler_state(self, state: Mapping[str, Any]) -> None:
        self._assert_integrity()
        expected_fields = {
            "schema",
            "routes",
            "sources",
            "epoch_budget",
            "provider_identity",
            "source_files",
            "source_members",
            "cursors",
            "next_update_cursor",
            "next_source_index",
            "consumed_file_order",
        }
        if not isinstance(state, Mapping) or set(state) != expected_fields:
            _fail("provider sampler state schema drifted")
        if (
            state["schema"] != SAMPLER_SCHEMA
            or state["routes"] != list(ROUTES)
            or state["sources"] != list(SOURCES)
            or state["epoch_budget"] != self._config.epoch_budget
            or state["provider_identity"] != self._identity
            or state["source_files"] != self._source_files
            or state["source_members"] != self._source_members
        ):
            _fail("provider sampler state identity drifted")
        update_cursor = state["next_update_cursor"]
        source_index = state["next_source_index"]
        if (
            type(update_cursor) is not int
            or update_cursor < 0
            or update_cursor > len(ROUTES) * self._config.epoch_budget
            or type(source_index) is not int
            or source_index not in range(len(SOURCES))
        ):
            _fail("provider sampler state cursor is invalid")
        raw_cursors = state["cursors"]
        expected_keys = {
            f"{route}:{source}" for route in ROUTES for source in SOURCES
        }
        if not isinstance(raw_cursors, Mapping) or set(raw_cursors) != expected_keys:
            _fail("provider sampler state lacks route/source cursors")
        positions: dict[tuple[str, str], int] = {}
        for route in ROUTES:
            for source in SOURCES:
                value = raw_cursors[f"{route}:{source}"]
                if type(value) is not int or not 0 <= value <= self._config.epoch_budget:
                    _fail("provider sampler position is invalid")
                positions[(route, source)] = value
        if positions != self._expected_positions(
            update_cursor=update_cursor, source_index=source_index
        ):
            _fail("provider sampler cursors are not route/source exact")
        consumed = state["consumed_file_order"]
        expected_length = update_cursor * len(SOURCES) + source_index
        if not isinstance(consumed, list) or len(consumed) != expected_length:
            _fail("provider consumed-file order length drifted")
        expected_consumed: list[dict[str, Any]] = []
        for call_index in range(expected_length):
            call_cursor, call_source_index = divmod(call_index, len(SOURCES))
            route = ROUTES[call_cursor % len(ROUTES)]
            source = SOURCES[call_source_index]
            expected_consumed.append(
                {
                    "update_cursor": call_cursor,
                    "route": route,
                    "source": source,
                    "file_id": self._source_files[f"{route}:{source}"][0],
                    "members": list(self._source_members[f"{route}:{source}"]),
                }
            )
        if consumed != expected_consumed:
            _fail("provider consumed-file order drifted")
        self._positions = positions
        self._next_update_cursor = update_cursor
        self._next_source_index = source_index
        self._consumed_file_order = deepcopy(consumed)


def build_provider(
    config: C1C2ProviderConfig,
    *,
    authenticated_config_sha256: str | None = None,
) -> V023C1C2Provider:
    if type(config) is not C1C2ProviderConfig:
        _fail("build_provider requires C1C2ProviderConfig")
    authority_snapshot = _authenticate_local_authorities(config)
    root = config.target_root
    before = _target_snapshot(root)
    if before["manifest_sha256"] != config.target_manifest_sha256:
        _fail("target MANIFEST.sha256 disagrees with config")
    if before["receipt_sha256"] != config.target_receipt_sha256:
        _fail("target receipt.json disagrees with config")
    try:
        artifact = _TARGET.load_completed_target_artifact(root)
    except Exception as cause:
        _fail("authenticated target adapter rejected the target root", cause=cause)
    target_identity = _validate_target_artifact(artifact)
    after = _target_snapshot(root)
    if dict(after) != dict(before):
        _fail("target root changed while it was being loaded")

    learner_manifest_path = _learner_manifest_path()
    learner_runtime, learner_manifest_sha = _authenticate_learner_manifest(
        learner_manifest_path,
        expected_sha256=config.learner_manifest_sha256,
    )
    runtime_payload = [dict(record) for record in learner_runtime]
    runtime_sha256 = _canonical_sha256(runtime_payload)
    target_payload = deepcopy(dict(target_identity))
    target_payload.update(
        {
            "root": str(root.resolve(strict=True)),
            "manifest_sha256": before["manifest_sha256"],
            "receipt_sha256": before["receipt_sha256"],
            "complete_sha256": before["complete_sha256"],
            "manifest_files": dict(before["files"]),
        }
    )
    source_order_plan = [
        {
            "route": route,
            "source": source,
            "members": target_payload["consumed_files"][f"{route}:{source}"],
        }
        for _epoch in range(config.epoch_budget)
        for route in ROUTES
        for source in SOURCES
    ]
    provider_config_sha256 = (
        hashlib.sha256(_canonical_bytes(config.payload())).hexdigest()
        if authenticated_config_sha256 is None
        else _digest(
            authenticated_config_sha256, field="authenticated provider config"
        )
    )
    identity_payload = {
        "schema": IDENTITY_SCHEMA,
        "routes": list(ROUTES),
        "sources": list(SOURCES),
        "train_seed": config.train_seed,
        "epoch_budget": config.epoch_budget,
        "contract_sha256": config.contract_sha256,
        "model_config_sha256": config.model_config_sha256,
        "provider_config_sha256": provider_config_sha256,
        "factory_code_sha256": _file_sha256(
            Path(__file__).resolve(), field="provider factory code"
        ),
        "target_adapter_code_sha256": _file_sha256(
            TARGET_ADAPTER_PATH, field="target adapter code"
        ),
        "provider_protocol_code_sha256": _file_sha256(
            PROVIDER_PROTOCOL_PATH, field="provider protocol code"
        ),
        "learner_manifest_path": str(learner_manifest_path.resolve(strict=True)),
        "learner_manifest_sha256": learner_manifest_sha,
        "learner_runtime": runtime_payload,
        "learner_runtime_sha256": runtime_sha256,
        "arm_independent_target_identity": target_payload,
        "arm_independent_target_identity_sha256": _canonical_sha256(target_payload),
        "consumed_file_order_plan_sha256": _canonical_sha256(source_order_plan),
        "predecessor_manifest_sha256": authority_snapshot[
            "predecessor_manifest_sha256"
        ],
        "prereg_sha256": authority_snapshot["prereg_sha256"],
        "scientific_declaration_sha256": authority_snapshot[
            "scientific_declaration_sha256"
        ],
        "tle_file_set_sha256": authority_snapshot["tle_file_set_sha256"],
    }
    if set(identity_payload) != PROVIDER_IDENTITY_FIELDS:
        _fail("provider identity field declaration drifted")
    identity = f"{FACTORY_SCHEMA}:{_canonical_sha256(identity_payload)}"
    if len(identity) > 512:
        _fail("provider identity exceeds the runner limit")
    provider = V023C1C2Provider(
        artifact=artifact,
        config=config,
        target_snapshot=before,
        target_identity=target_identity,
        learner_manifest_path=learner_manifest_path,
        learner_runtime=learner_runtime,
        identity_payload=identity_payload,
        identity=identity,
    )
    if not isinstance(provider, DeterministicRouteBatchProvider):
        _fail("provider does not implement DeterministicRouteBatchProvider")
    return provider


def make_provider() -> V023C1C2Provider:
    """Zero-argument runner entry point for ``MODULE:CALLABLE`` loading."""

    config, config_sha256 = _config_from_environment()
    return build_provider(
        config, authenticated_config_sha256=config_sha256
    )


__all__ = [
    "CLAIM_CEILING",
    "CONFIG_PATH_ENV",
    "CONFIG_SCHEMA",
    "CONFIG_SHA256_ENV",
    "C1C2ProviderConfig",
    "DEFAULT_LEARNER_MANIFEST_PATH",
    "DeterministicRouteBatchProvider",
    "EPOCH_BUDGET",
    "EXPECTED_WORLDS",
    "FACTORY_SCHEMA",
    "IDENTITY_SCHEMA",
    "LEARNER_MANIFEST_PATH_ENV",
    "LEARNER_MANIFEST_SCHEMA",
    "LEARNER_MANIFEST_STATUS",
    "MODEL_CONFIG_SHA256",
    "PROVIDER_IDENTITY_FIELDS",
    "ProvidedRouteBatch",
    "REQUIRED_LEARNER_RUNTIME_MODULES",
    "LEARNER_RUNTIME_ROOT_MODULES",
    "ROUTES",
    "SAMPLER_SCHEMA",
    "SOURCES",
    "TRAIN_SEED",
    "V023C1C2Provider",
    "V023C1C2ProviderFactoryError",
    "build_provider",
    "derive_learner_runtime_modules",
    "make_provider",
]
