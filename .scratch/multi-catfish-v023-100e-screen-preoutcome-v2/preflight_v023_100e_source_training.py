#!/usr/bin/env python3
"""Authenticate all frozen inputs for the V0.23 100-epoch learner screen.

This preflight performs no optimizer update, simulator step, or TEST access.
It is intentionally allowed to open the R7 decision only after the provider
factory has authenticated the sealed whole-tree result manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import MappingProxyType, ModuleType
from typing import Any, Mapping


SCHEMA = "multi-catfish-mcrl-v023-100e-source-training-preflight-v2"
STATUS = "PASS_FROZEN_PREOUTCOME_100E_PREFLIGHT"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_ONLY_NO_SIMULATOR_NO_EPISODE_NO_TEST_NO_EFFICACY"
)
EXPECTED_EPOCHS = 100
EXPECTED_TRAIN_SEED = 2927175120652069826
EXPECTED_SCHEDULE_SEED = 1113171504590631764
EXPECTED_OUTPUT_ROOT = Path(
    "/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2"
)
EXPECTED_CONTRACT_SHA256 = (
    "5b84ac3b857fba6717c4c9ca34e48ed433a2945fbbc1006b8619db2ca60d6932"
)
EXPECTED_MODEL_CONFIG_SHA256 = (
    "81e30b716ce996fb69e57ec9c1c3a4806f93598e6c009216287dd6a7dbde5df7"
)
EXPECTED_PROVIDER_CONFIG_SHA256 = (
    "c6c8dc6347a838bd4e437f73127929a8594c3e1aa66ca060a33a8bcb659583ba"
)
EXPECTED_PROVIDER_FACTORY_SCHEMA = (
    "multi-catfish-mcrl-v023-post-r7-provider-factory-v2"
)
EXPECTED_PROVIDER_IDENTITY_SCHEMA = (
    "multi-catfish-mcrl-v023-post-r7-provider-identity-v2"
)
EXPECTED_PROVIDER_IDENTITY_FIELDS = frozenset(
    {
        "schema",
        "target_manifest_sha256",
        "c3_schedule_receipt_sha256",
        "epoch_budget",
        "c3_source_ids",
        "r7_code_root",
        "r7_preflight_manifest_sha256",
        "r7_code_manifest_sha256",
        "r7_result_manifest_sha256",
        "r7_gate_result_sha256",
        "r7_authentication_runtime",
        "r7_authentication_runtime_sha256",
        "r7_bound_learner_runtime",
        "r7_bound_learner_runtime_sha256",
    }
)
EXPECTED_R7_AUTHENTICATION_RUNTIME_MODULES = MappingProxyType({
    ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py":
        "v023_r7_preflight_for_post_r7_provider_factory",
    ".scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py":
        "r7_balanced_successor_gate",
    ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py":
        "v023_fit_adapter_for_post_r7_provider_factory",
    "src/mcrl/__init__.py": "mcrl",
    "src/mcrl/errors.py": "mcrl.errors",
    "src/mcrl/algorithms/__init__.py": "mcrl.algorithms",
    "src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py":
        "mcrl.algorithms.ee_axis_lcsrs_c3_head",
    "src/mcrl/env/__init__.py": "mcrl.env",
    "src/mcrl/env/action_contract.py": "mcrl.env.action_contract",
    "src/mcrl/runtime/__init__.py": "mcrl.runtime",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_dataset.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_dataset",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_fit.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_gate_fit",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_metrics.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_gate_metrics",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_learner.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_learner",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_placebo.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_placebo",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_source_artifact",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_state.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_state",
    "src/mcrl/runtime/finiteness.py": "mcrl.runtime.finiteness",
})
EXPECTED_R7_AUTHENTICATION_RUNTIME_PATHS = tuple(
    EXPECTED_R7_AUTHENTICATION_RUNTIME_MODULES
)
EXPECTED_R7_BOUND_LEARNER_RUNTIME_MODULES = MappingProxyType({
    "src/mcrl/algorithms/ee_axis_action_shared.py":
        "mcrl.algorithms.ee_axis_action_shared",
    "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py":
        "mcrl.algorithms.ee_axis_lcsrs_three_route",
    "src/mcrl/algorithms/ee_axis_pairwise.py":
        "mcrl.algorithms.ee_axis_pairwise",
    "src/mcrl/algorithms/ee_axis_v014_head.py":
        "mcrl.algorithms.ee_axis_v014_head",
    "src/mcrl/env/antenna.py": "mcrl.env.antenna",
    "src/mcrl/env/candidates.py": "mcrl.env.candidates",
    "src/mcrl/env/cells.py": "mcrl.env.cells",
    "src/mcrl/env/constants.py": "mcrl.env.constants",
    "src/mcrl/env/d2.py": "mcrl.env.d2",
    "src/mcrl/env/dwell.py": "mcrl.env.dwell",
    "src/mcrl/env/ephemeris.py": "mcrl.env.ephemeris",
    "src/mcrl/env/geometry.py": "mcrl.env.geometry",
    "src/mcrl/env/interference.py": "mcrl.env.interference",
    "src/mcrl/env/keyed_fading.py": "mcrl.env.keyed_fading",
    "src/mcrl/env/link_budget.py": "mcrl.env.link_budget",
    "src/mcrl/env/mobility.py": "mcrl.env.mobility",
    "src/mcrl/env/observation_provenance.py":
        "mcrl.env.observation_provenance",
    "src/mcrl/env/pointing.py": "mcrl.env.pointing",
    "src/mcrl/env/scenario.py": "mcrl.env.scenario",
    "src/mcrl/env/service.py": "mcrl.env.service",
    "src/mcrl/env/step.py": "mcrl.env.step",
    "src/mcrl/env/step_types.py": "mcrl.env.step_types",
    "src/mcrl/env/tle.py": "mcrl.env.tle",
    "src/mcrl/runtime/bessel.py": "mcrl.runtime.bessel",
    "src/mcrl/runtime/ee_axis_opening_pairs.py":
        "mcrl.runtime.ee_axis_opening_pairs",
    "src/mcrl/runtime/ee_axis_ops3.py": "mcrl.runtime.ee_axis_ops3",
    "src/mcrl/runtime/ee_axis_state.py": "mcrl.runtime.ee_axis_state",
    "src/mcrl/runtime/ee_axis_v014_q2_state.py":
        "mcrl.runtime.ee_axis_v014_q2_state",
    "src/mcrl/runtime/ee_surplus_targets.py":
        "mcrl.runtime.ee_surplus_targets",
    "src/mcrl/runtime/energy_efficiency.py":
        "mcrl.runtime.energy_efficiency",
    "src/mcrl/runtime/q_network.py": "mcrl.runtime.q_network",
    "src/mcrl/runtime/state_encoding.py": "mcrl.runtime.state_encoding",
    "src/mcrl/runtime/trainer_spec.py": "mcrl.runtime.trainer_spec",
})
EXPECTED_R7_BOUND_LEARNER_RUNTIME_PATHS = tuple(
    EXPECTED_R7_BOUND_LEARNER_RUNTIME_MODULES
)
EXPECTED_PROVIDER_CONFIG = {
    "epoch_budget": 100,
    "r7_code_root": "/home/sat/mcrl-v023-r7-launch-ready-20260906-r4",
    "r7_root": "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1",
    "schedule_seed": EXPECTED_SCHEDULE_SEED,
    "schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2",
    "target_root": "/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8",
}
EXPECTED_C3_SOURCE_DISCLOSURE = (
    "FIXED_SEALED_R7_C3_VIEW_OFFLINE_SOURCE_Q1_Q2_UPDATE;"
    "MEASURE_DEPLOYMENT_COVARIATE_SHIFT_LATER;NO_SILENT_REBUILD"
)
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class V023PreflightError(RuntimeError):
    """The future run does not match the frozen 100-epoch contract."""


def _sha(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise V023PreflightError(f"{field} must be a lowercase SHA-256")
    return value


def _file_sha256(path: Path, *, field: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise V023PreflightError(f"{field} must be a regular non-symlink file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
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
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023PreflightError("preflight payload is not canonical finite JSON") from error


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _canonical_compact_sha256(value: object) -> str:
    # Provider identities and both runtime-list digests use the complete
    # compact finite-ASCII JSON value with no trailing newline.
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023PreflightError(
            "provider identity payload is not canonical finite JSON"
        ) from error
    return hashlib.sha256(payload).hexdigest()


def _provider_code_root(provider_config: object) -> object:
    if isinstance(provider_config, Mapping):
        return provider_config.get("r7_code_root")
    return getattr(provider_config, "r7_code_root", None)


def _validated_runtime_records(
    payload: Mapping[str, Any],
    *,
    list_field: str,
    digest_field: str,
    declarations: Mapping[str, str],
    learner_repo: Path,
    launch_bindings: Mapping[str, str],
    sort_records: bool,
    label: str,
) -> None:
    runtime = payload.get(list_field)
    if not isinstance(runtime, list):
        raise V023PreflightError(f"provider {label} is missing")
    expected_items = list(declarations.items())
    if sort_records:
        expected_items.sort(key=lambda item: (item[0], item[1]))
    observed_items: list[tuple[str, str]] = []
    for index, record in enumerate(runtime):
        if not isinstance(record, Mapping) or set(record) != {
            "path", "module", "loaded_from", "sha256"
        }:
            raise V023PreflightError(
                f"provider {label} record {index} is malformed"
            )
        path = record.get("path")
        module = record.get("module")
        loaded_from = record.get("loaded_from")
        if (
            not isinstance(path, str)
            or not isinstance(module, str)
            or not module
            or not isinstance(loaded_from, str)
            or not loaded_from
        ):
            raise V023PreflightError(
                f"provider {label} record {index} has invalid fields"
            )
        observed_items.append((path, module))
        expected_origin = learner_repo / path
        raw_origin = Path(loaded_from)
        if not raw_origin.is_absolute() or raw_origin != expected_origin:
            raise V023PreflightError(
                f"provider {label} origin changed: {module}"
            )
        if raw_origin.is_symlink() or not raw_origin.is_file():
            raise V023PreflightError(
                f"provider {label} origin is not a regular file: {module}"
            )
        try:
            resolved = raw_origin.resolve(strict=True)
        except OSError as error:
            raise V023PreflightError(
                f"provider {label} origin is unavailable: {module}"
            ) from error
        if resolved != expected_origin or not resolved.is_relative_to(learner_repo):
            raise V023PreflightError(
                f"provider {label} origin escaped the learner checkout: {module}"
            )
        record_sha = _sha(record.get("sha256"), field=f"provider {label} {path}")
        actual_sha = _file_sha256(raw_origin, field=f"provider {label} {path}")
        launch_sha = _sha(
            launch_bindings.get(path),
            field=f"launch manifest binding for provider {label} {path}",
        )
        if record_sha != actual_sha or record_sha != launch_sha:
            raise V023PreflightError(
                f"provider {label} hash disagrees with the live launch binding: {path}"
            )
    if observed_items != expected_items:
        raise V023PreflightError(f"provider {label} declaration changed")
    if len({path for path, _ in observed_items}) != len(observed_items):
        raise V023PreflightError(f"provider {label} repeats a path")
    expected_digest = _sha(
        payload.get(digest_field), field=f"provider {label} digest"
    )
    if _canonical_compact_sha256(runtime) != expected_digest:
        raise V023PreflightError(f"provider {label} digest disagrees")


def _validated_provider_identity(
    identity: object,
    identity_payload: object,
    *,
    provider_config: object,
    learner_repo: Path,
    launch_bindings: Mapping[str, str],
) -> dict[str, Any]:
    if not isinstance(identity, str) or not identity:
        raise V023PreflightError("provider identity is incomplete")
    if not isinstance(identity_payload, Mapping):
        raise V023PreflightError("provider identity payload is incomplete")
    payload = dict(identity_payload)
    if set(payload) != EXPECTED_PROVIDER_IDENTITY_FIELDS:
        raise V023PreflightError("provider identity payload field set drifted")
    if payload.get("schema") != EXPECTED_PROVIDER_IDENTITY_SCHEMA:
        raise V023PreflightError("provider identity schema drifted")
    if type(payload.get("epoch_budget")) is not int or payload["epoch_budget"] != EXPECTED_EPOCHS:
        raise V023PreflightError("provider identity epoch budget drifted")
    source_ids = payload.get("c3_source_ids")
    if (
        not isinstance(source_ids, Mapping)
        or set(source_ids) != {"neutral", "informed"}
        or any(not isinstance(value, str) or not value for value in source_ids.values())
        or source_ids["neutral"] == source_ids["informed"]
    ):
        raise V023PreflightError("provider identity C3 source IDs drifted")
    for field in (
        "target_manifest_sha256",
        "c3_schedule_receipt_sha256",
        "r7_preflight_manifest_sha256",
        "r7_code_manifest_sha256",
        "r7_result_manifest_sha256",
        "r7_gate_result_sha256",
        "r7_authentication_runtime_sha256",
        "r7_bound_learner_runtime_sha256",
    ):
        _sha(payload.get(field), field=f"provider identity {field}")

    repo_path = Path(learner_repo)
    if repo_path.is_symlink() or not repo_path.is_dir():
        raise V023PreflightError("learner checkout is unavailable or symlinked")
    repo_path = repo_path.resolve()
    _validated_runtime_records(
        payload,
        list_field="r7_authentication_runtime",
        digest_field="r7_authentication_runtime_sha256",
        declarations=EXPECTED_R7_AUTHENTICATION_RUNTIME_MODULES,
        learner_repo=repo_path,
        launch_bindings=launch_bindings,
        sort_records=False,
        label="authentication runtime",
    )
    _validated_runtime_records(
        payload,
        list_field="r7_bound_learner_runtime",
        digest_field="r7_bound_learner_runtime_sha256",
        declarations=EXPECTED_R7_BOUND_LEARNER_RUNTIME_MODULES,
        learner_repo=repo_path,
        launch_bindings=launch_bindings,
        sort_records=True,
        label="R7-bound learner runtime",
    )

    code_root_value = payload.get("r7_code_root")
    if not isinstance(code_root_value, str) or not Path(code_root_value).is_absolute():
        raise V023PreflightError("provider identity r7_code_root is invalid")
    try:
        identity_code_root = Path(code_root_value).resolve(strict=True)
        configured_value = _provider_code_root(provider_config)
        if not isinstance(configured_value, (str, Path)):
            raise OSError("provider config has no R7 code root")
        config_code_root = Path(configured_value).resolve(strict=True)
    except OSError as error:
        raise V023PreflightError("provider identity r7_code_root is unavailable") from error
    if identity_code_root != config_code_root:
        raise V023PreflightError("provider identity r7_code_root disagrees with config")

    expected_identity = (
        f"{EXPECTED_PROVIDER_FACTORY_SCHEMA}:{_canonical_compact_sha256(payload)}"
    )
    if identity != expected_identity:
        raise V023PreflightError("provider identity does not bind its complete payload")
    return payload


def _load_module(name: str, path: Path) -> ModuleType:
    if path.is_symlink() or not path.is_file():
        raise V023PreflightError(f"required module is unavailable: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V023PreflightError(f"cannot import required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise V023PreflightError(f"required module import failed: {path}") from error
    return module


def _verify_manifest(
    repo: Path, manifest: Path, expected_sha256: str
) -> tuple[str, dict[str, str]]:
    manifest_sha = _file_sha256(manifest, field="launch manifest")
    if manifest_sha != _sha(expected_sha256, field="launch manifest sha256"):
        raise V023PreflightError("launch manifest disagrees with its external pin")
    lines = manifest.read_text(encoding="ascii").splitlines()
    if not lines:
        raise V023PreflightError("launch manifest is empty")
    seen: set[str] = set()
    bindings: dict[str, str] = {}
    for line in lines:
        parts = line.split("  ")
        if len(parts) != 2:
            raise V023PreflightError("launch manifest line is malformed")
        expected, relative = parts
        _sha(expected, field=f"manifest entry {relative}")
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts or relative in seen:
            raise V023PreflightError("launch manifest path is unsafe or repeated")
        seen.add(relative)
        bindings[relative] = expected
        path = repo / rel
        if _file_sha256(path, field=f"manifest entry {relative}") != expected:
            raise V023PreflightError(f"launch manifest entry drifted: {relative}")
    return manifest_sha, bindings


def _verify_loaded_project_modules(
    repo: Path, launch_bindings: Mapping[str, str]
) -> list[str]:
    """Require every executing local mcrl/scratch module to be launch-bound."""

    root = repo.resolve()
    src_root = root / "src/mcrl"
    scratch_root = root / ".scratch"
    uncovered: set[str] = set()
    mismatched: set[str] = set()
    loaded: set[str] = set()

    # A foreign mcrl origin must fail before the checkout-location filter below.
    for module_name, module in tuple(sys.modules.items()):
        if module_name != "mcrl" and not module_name.startswith("mcrl."):
            continue
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str) or not module_file:
            raise V023PreflightError(
                f"loaded mcrl module has no origin: {module_name}"
            )
        base = root / "src" / Path(*module_name.split("."))
        allowed = {base.with_suffix(".py"), base / "__init__.py"}
        if Path(module_file) not in allowed:
            raise V023PreflightError(
                f"loaded mcrl module has a foreign origin: {module_name}"
            )

    for module_name, module in tuple(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str) or not Path(module_file).is_absolute():
            continue
        raw_origin = Path(module_file)
        try:
            origin = raw_origin.resolve(strict=True)
        except OSError:
            if raw_origin.is_relative_to(src_root) or raw_origin.is_relative_to(scratch_root):
                mismatched.add(raw_origin.relative_to(root).as_posix())
            continue
        if not (
            origin.is_relative_to(src_root) or origin.is_relative_to(scratch_root)
        ):
            continue
        relative = origin.relative_to(root).as_posix()
        loaded.add(relative)
        if raw_origin != origin or raw_origin.is_symlink() or not raw_origin.is_file():
            mismatched.add(relative)
            continue
        declared = launch_bindings.get(relative)
        if declared is None:
            uncovered.add(relative)
            continue
        if _file_sha256(origin, field=f"loaded project module {relative}") != _sha(
            declared, field=f"launch manifest binding {relative}"
        ):
            mismatched.add(relative)
    if uncovered or mismatched:
        raise V023PreflightError(
            "loaded project modules are not fully launch-bound; "
            f"uncovered={sorted(uncovered)}, hash_mismatches={sorted(mismatched)}"
        )
    return sorted(loaded)


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise V023PreflightError(f"refusing to overwrite preflight output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return hashlib.sha256(payload).hexdigest()


def run_preflight(
    *,
    repo: Path,
    manifest: Path,
    manifest_sha256: str,
    provider_config: Path,
    model_config: Path,
    contract: Path,
    output_root: Path,
    receipt_path: Path,
) -> Mapping[str, Any]:
    root = repo.resolve()
    if repo.is_symlink() or not root.is_dir():
        raise V023PreflightError("repo must be a regular directory")
    if output_root != EXPECTED_OUTPUT_ROOT:
        raise V023PreflightError("output root drifted from the frozen contract")
    if output_root.exists() or output_root.is_symlink():
        raise V023PreflightError("source-training output root must be absent")

    launch_manifest_sha, launch_bindings = _verify_manifest(
        root, manifest, manifest_sha256
    )
    contract_sha = _file_sha256(contract, field="100-epoch contract")
    model_sha = _file_sha256(model_config, field="model config")
    provider_config_sha = _file_sha256(provider_config, field="provider config")
    if contract_sha != EXPECTED_CONTRACT_SHA256:
        raise V023PreflightError("100-epoch contract digest drifted")
    if model_sha != EXPECTED_MODEL_CONFIG_SHA256:
        raise V023PreflightError("model config digest drifted")
    if provider_config_sha != EXPECTED_PROVIDER_CONFIG_SHA256:
        raise V023PreflightError("provider config digest drifted")

    factory = _load_module(
        "v023_post_r7_factory_for_100e_preflight",
        root
        / ".scratch/multi-catfish-v023-post-r7-provider-factory"
        / "v023_post_r7_provider_factory_v2.py",
    )
    runner = _load_module(
        "v023_five_arm_runner_for_100e_preflight",
        root
        / ".scratch/multi-catfish-v023-five-arm-training-runner"
        / "v023_five_arm_source_training_runner.py",
    )
    config_payload = factory._read_canonical_json(
        provider_config, field="post-R7 provider config"
    )
    if config_payload != EXPECTED_PROVIDER_CONFIG:
        raise V023PreflightError(
            "post-R7 provider config drifted from the frozen six-field contract"
        )
    parsed = factory.PostR7ProviderConfig.from_payload(config_payload)
    if parsed.epoch_budget != EXPECTED_EPOCHS:
        raise V023PreflightError("provider epoch budget drifted")
    if parsed.schedule_seed != EXPECTED_SCHEDULE_SEED:
        raise V023PreflightError("provider schedule seed drifted")

    old_path = os.environ.get(factory.CONFIG_PATH_ENV)
    old_sha = os.environ.get(factory.CONFIG_SHA256_ENV)
    os.environ[factory.CONFIG_PATH_ENV] = str(provider_config.resolve())
    os.environ[factory.CONFIG_SHA256_ENV] = provider_config_sha
    try:
        provider = factory.make_provider()
    finally:
        if old_path is None:
            os.environ.pop(factory.CONFIG_PATH_ENV, None)
        else:
            os.environ[factory.CONFIG_PATH_ENV] = old_path
        if old_sha is None:
            os.environ.pop(factory.CONFIG_SHA256_ENV, None)
        else:
            os.environ[factory.CONFIG_SHA256_ENV] = old_sha

    _verify_loaded_project_modules(root, launch_bindings)

    identity = getattr(provider, "provider_identity", None)
    identity_payload = getattr(provider, "provider_identity_payload", None)
    provider_epoch_budget = getattr(provider, "planned_epoch_budget", None)
    if callable(provider_epoch_budget):
        provider_epoch_budget = provider_epoch_budget()
    identity_payload = _validated_provider_identity(
        identity,
        identity_payload,
        provider_config=parsed,
        learner_repo=root,
        launch_bindings=launch_bindings,
    )
    if provider_epoch_budget != EXPECTED_EPOCHS:
        raise V023PreflightError("provider planned epoch budget drifted")
    try:
        raw_model = json.loads(model_config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023PreflightError("model config JSON is not readable") from error
    if not isinstance(raw_model, dict) or set(raw_model) != {"q1", "q2", "q3"}:
        raise V023PreflightError(
            "V2 model config must expose separate q1, q2, and q3 records; legacy q12 is refused"
        )
    model = runner._load_model_config(model_config)
    if (
        model.q1.state_dim != 228
        or model.q1.action_dim != 28
        or tuple(model.q1.hidden_layers) != (100, 50, 50)
        or model.q1.activation != "tanh"
        or model.q1.learning_rate != 0.001
        or model.q1.kappa_bits != 10097071012.757404
        or model.q1.beta != 0.1
        or tuple(model.q1.loss_weights) != (1.0, 1.0, 1.0)
        or model.q2.state_dim != 448
        or model.q2.action_dim != 28
        or model.q2.local_feature_dim != 16
        or model.q2.global_feature_dim != 0
        or tuple(model.q2.hidden_layers) != (100, 50, 50)
        or model.q2.activation != "tanh"
        or model.q2.learning_rate != 0.001
        or model.q2.kappa_bits != model.q1.kappa_bits
        or model.q2.beta != 0.1
    ):
        raise V023PreflightError("current heterogeneous Q1/Q2 model configuration drifted")

    input_binding = {
        "schema": f"{SCHEMA}-input-binding",
        "provider_identity": identity,
        "provider_identity_payload": identity_payload,
        "provider_config_sha256": provider_config_sha,
        "model_config_sha256": model_sha,
        "code_sha256": launch_manifest_sha,
    }
    input_sha = _canonical_sha256(input_binding)
    payload = {
        "schema": SCHEMA,
        "status": STATUS,
        "claim_ceiling": CLAIM_CEILING,
        "epoch_budget": EXPECTED_EPOCHS,
        "route_updates": 300,
        "checkpoint_epochs": [100],
        "train_seed": EXPECTED_TRAIN_SEED,
        "schedule_seed": EXPECTED_SCHEDULE_SEED,
        "source_split": "SOURCE_TRAIN",
        "test_split_opened": False,
        "simulator_episode_opened": False,
        "authority_sha256": contract_sha,
        "code_sha256": launch_manifest_sha,
        "input_sha256": input_sha,
        "input_binding": input_binding,
        "output_root": str(output_root),
        "c3_source_disclosure": EXPECTED_C3_SOURCE_DISCLOSURE,
    }
    receipt_sha = _write_once(receipt_path, _canonical_bytes(payload))
    sidecar = receipt_path.with_suffix(receipt_path.suffix + ".sha256")
    _write_once(sidecar, f"{receipt_sha}  {receipt_path.name}\n".encode("ascii"))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--provider-config", required=True, type=Path)
    parser.add_argument("--model-config", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    arguments = parser.parse_args()
    payload = run_preflight(
        repo=arguments.repo,
        manifest=arguments.manifest,
        manifest_sha256=arguments.manifest_sha256,
        provider_config=arguments.provider_config,
        model_config=arguments.model_config,
        contract=arguments.contract,
        output_root=arguments.output_root,
        receipt_path=arguments.receipt,
    )
    print(payload["input_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
