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
from types import ModuleType
from typing import Any, Mapping


SCHEMA = "multi-catfish-mcrl-v023-100e-source-training-preflight-v1"
STATUS = "PASS_FROZEN_PREOUTCOME_100E_PREFLIGHT"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_ONLY_NO_SIMULATOR_NO_EPISODE_NO_TEST_NO_EFFICACY"
)
EXPECTED_EPOCHS = 100
EXPECTED_TRAIN_SEED = 2927175120652069826
EXPECTED_SCHEDULE_SEED = 1113171504590631764
EXPECTED_OUTPUT_ROOT = Path(
    "/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1"
)
EXPECTED_CONTRACT_SHA256 = (
    "7f417ca66d935ba3748dc7204a0ee241ad70ff491ed6cdae69a92e7f71ae20b6"
)
EXPECTED_MODEL_CONFIG_SHA256 = (
    "2fab1e4a0b61bf88a428709815d078d9b613b06b645c4d9cef7e46b2220b78ec"
)
EXPECTED_PROVIDER_CONFIG_SHA256 = (
    "939582ffb8537eef865c1a71d8c324ad475059a0d96dd29e36da39ea18ee9f7b"
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


def _verify_manifest(repo: Path, manifest: Path, expected_sha256: str) -> str:
    manifest_sha = _file_sha256(manifest, field="launch manifest")
    if manifest_sha != _sha(expected_sha256, field="launch manifest sha256"):
        raise V023PreflightError("launch manifest disagrees with its external pin")
    lines = manifest.read_text(encoding="ascii").splitlines()
    if not lines:
        raise V023PreflightError("launch manifest is empty")
    seen: set[str] = set()
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
        path = repo / rel
        if _file_sha256(path, field=f"manifest entry {relative}") != expected:
            raise V023PreflightError(f"launch manifest entry drifted: {relative}")
    return manifest_sha


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

    launch_manifest_sha = _verify_manifest(root, manifest, manifest_sha256)
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
        / "v023_post_r7_provider_factory.py",
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

    identity = getattr(provider, "provider_identity", None)
    identity_payload = getattr(provider, "provider_identity_payload", None)
    provider_epoch_budget = getattr(provider, "planned_epoch_budget", None)
    if callable(provider_epoch_budget):
        provider_epoch_budget = provider_epoch_budget()
    if not isinstance(identity, str) or not identity or not isinstance(
        identity_payload, Mapping
    ):
        raise V023PreflightError("provider identity is incomplete")
    if provider_epoch_budget != EXPECTED_EPOCHS:
        raise V023PreflightError("provider planned epoch budget drifted")
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
        "provider_identity_payload": dict(identity_payload),
        "provider_config_sha256": provider_config_sha,
        "model_config_sha256": model_sha,
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
