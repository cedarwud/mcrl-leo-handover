#!/usr/bin/env python3
"""Authenticate every frozen stage-A input without creating the output root."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from successor_launch_common import (
    BINDINGS_NAME, BUNDLE_REL, CLAIM_CEILING, DECLARATION_NAME,
    EPOCH_BUDGET, EXECUTION_BINDINGS_SCHEMA, EXPECTED_MODEL_CONFIG_SHA256,
    FACTORY_REL, LAUNCH_MANIFEST_NAME, LEARNER_MANIFEST_NAME,
    MODEL_CONFIG_NAME, PROVIDER_CONFIG_NAME, PROVIDER_CONFIG_SCHEMA,
    ROUTE_ORDER, SUCCESSOR_REL, TARGET_ROOT, TRAIN_SEED,
    SuccessorLaunchError, canonical_bytes, canonical_sha256, file_sha256,
    read_canonical_json, reject_forbidden_config, sidecar_path,
    verify_launch_manifest, verify_sidecar, write_once,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-preflight-v1"
STATUS = "PASS_FROZEN_C1C2_SUCCESSOR_PREFLIGHT"
DIAGNOSTIC_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-one-epoch-diagnostic-v1"
DIAGNOSTIC_STATUS = "PASS_ONE_EPOCH_C1C2_SUCCESSOR_DIAGNOSTIC"


def _load_factory(repo: Path) -> Any:
    for path in (repo / "src", repo / FACTORY_REL):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    module = importlib.import_module("v023_c1c2_provider_factory_v3")
    origin = Path(module.__file__).resolve(strict=True)
    expected = (repo / FACTORY_REL / "v023_c1c2_provider_factory_v3.py").resolve(strict=True)
    if origin != expected:
        raise SuccessorLaunchError("factory v3 imported from an unexpected checkout")
    return module


def _verify_model_config(path: Path, bindings: dict[str, Any]) -> dict[str, Any]:
    actual = verify_sidecar(path)
    if actual != EXPECTED_MODEL_CONFIG_SHA256:
        raise SuccessorLaunchError("successor model config digest drifted")
    if bindings.get("model_config", {}).get("sha256") != actual:
        raise SuccessorLaunchError("execution bindings disagree with model config")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"q1", "q2"}:
        raise SuccessorLaunchError("model config must contain exactly two head records")
    q1, q2 = payload["q1"], payload["q2"]
    if (
        q1.get("state_dim") != 228 or q1.get("action_dim") != 28
        or q2.get("action_dim") != 28 or q2.get("local_feature_dim") != 16
        or q2.get("global_feature_dim") != 0
    ):
        raise SuccessorLaunchError("model config dimensions drifted")
    return payload


def _provider_identity(provider: object) -> tuple[str, dict[str, Any]]:
    identity = getattr(provider, "provider_identity", None)
    identity = identity() if callable(identity) else identity
    payload = getattr(provider, "provider_identity_payload", None)
    payload = payload() if callable(payload) else payload
    if not isinstance(payload, dict):
        try:
            payload = dict(payload)
        except (TypeError, ValueError) as error:
            raise SuccessorLaunchError("provider identity is incomplete") from error
    if not isinstance(identity, str) or not identity or identity != identity.strip():
        raise SuccessorLaunchError("provider identity is incomplete")
    if payload.get("routes") != list(ROUTE_ORDER):
        raise SuccessorLaunchError("provider identity routes are not exactly C1/C2")
    if payload.get("epoch_budget") != EPOCH_BUDGET or payload.get("train_seed") != TRAIN_SEED:
        raise SuccessorLaunchError("provider identity budget or train seed drifted")
    if ("TE" + "ST") in canonical_bytes(payload).decode("ascii").upper():
        raise SuccessorLaunchError("provider identity names a closed split")
    return identity, payload


def verify_diagnostic_receipt(path: Path, expected_provider_identity: str | None = None) -> dict[str, Any]:
    verify_sidecar(path)
    receipt = read_canonical_json(path, field="one-epoch diagnostic receipt")
    if (
        receipt.get("schema") != DIAGNOSTIC_SCHEMA
        or receipt.get("status") != DIAGNOSTIC_STATUS
        or receipt.get("formal") is not False
        or receipt.get("failed_checks") != []
    ):
        raise SuccessorLaunchError("one-epoch diagnostic did not pass")
    if expected_provider_identity is not None and receipt.get("provider_identity") != expected_provider_identity:
        raise SuccessorLaunchError("one-epoch diagnostic provider identity drifted")
    return receipt


def run_preflight(
    *, repo: Path, bindings_path: Path, manifest_path: Path,
    provider_config_path: Path, model_config_path: Path,
    declaration_path: Path, output_root: Path, receipt_path: Path | None,
    instantiate_provider: bool = True,
) -> dict[str, Any]:
    if output_root.exists() or output_root.is_symlink():
        raise SuccessorLaunchError("formal output root must be absent")
    bindings_sha = verify_sidecar(bindings_path)
    bindings = read_canonical_json(bindings_path, field="execution bindings")
    if bindings.get("schema") != EXECUTION_BINDINGS_SCHEMA:
        raise SuccessorLaunchError("execution bindings schema drifted")
    manifest = verify_launch_manifest(repo, manifest_path)
    declaration_sha = verify_sidecar(declaration_path)
    if bindings.get("authority", {}).get("scientific_declaration_sha256") != declaration_sha:
        raise SuccessorLaunchError("scientific declaration digest disagrees with bindings")
    model_payload = _verify_model_config(model_config_path, bindings)

    provider_sha = verify_sidecar(provider_config_path)
    provider_config = read_canonical_json(provider_config_path, field="factory-v3 config")
    reject_forbidden_config(provider_config)
    if set(provider_config) != {
        "schema", "contract_sha256", "target_root", "target_manifest_sha256",
        "target_receipt_sha256", "learner_manifest_sha256", "model_config_sha256",
        "train_seed", "epoch_budget",
    }:
        raise SuccessorLaunchError("factory-v3 config field set drifted")
    expected = {
        "schema": PROVIDER_CONFIG_SCHEMA,
        "target_root": str(TARGET_ROOT),
        "train_seed": TRAIN_SEED,
        "epoch_budget": EPOCH_BUDGET,
        "model_config_sha256": EXPECTED_MODEL_CONFIG_SHA256,
    }
    for key, value in expected.items():
        if provider_config.get(key) != value:
            raise SuccessorLaunchError(f"factory-v3 config drifted: {key}")
    if bindings.get("provider_config", {}).get("sha256") != provider_sha:
        raise SuccessorLaunchError("execution bindings disagree with provider config")
    learner_path = repo / BUNDLE_REL / LEARNER_MANIFEST_NAME
    learner_sha = file_sha256(learner_path)
    if provider_config["learner_manifest_sha256"] != learner_sha:
        raise SuccessorLaunchError("provider config learner manifest digest drifted")

    identity = "NOT_INSTANTIATED"
    identity_payload: dict[str, Any] = {"routes": list(ROUTE_ORDER)}
    if instantiate_provider:
        factory = _load_factory(repo)
        if factory.CONFIG_SCHEMA != PROVIDER_CONFIG_SCHEMA:
            raise SuccessorLaunchError("factory-v3 schema constant drifted")
        old = {
            factory.CONFIG_PATH_ENV: os.environ.get(factory.CONFIG_PATH_ENV),
            factory.CONFIG_SHA256_ENV: os.environ.get(factory.CONFIG_SHA256_ENV),
            factory.LEARNER_MANIFEST_PATH_ENV: os.environ.get(factory.LEARNER_MANIFEST_PATH_ENV),
        }
        os.environ[factory.CONFIG_PATH_ENV] = str(provider_config_path.resolve())
        os.environ[factory.CONFIG_SHA256_ENV] = provider_sha
        os.environ[factory.LEARNER_MANIFEST_PATH_ENV] = str(learner_path.resolve())
        try:
            provider = factory.make_provider()
            identity, identity_payload = _provider_identity(provider)
        except Exception as error:
            raise SuccessorLaunchError("factory-v3 provider preflight failed") from error
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    input_binding = {
        "bindings_sha256": bindings_sha,
        "launch_manifest_sha256": manifest["sha256"],
        "provider_config_sha256": provider_sha,
        "model_config_sha256": file_sha256(model_config_path),
        "scientific_declaration_sha256": declaration_sha,
        "provider_identity": identity,
        "provider_identity_payload": identity_payload,
    }
    payload = {
        "schema": SCHEMA,
        "status": STATUS,
        "claim_ceiling": CLAIM_CEILING,
        "formal": True,
        "epoch_budget": EPOCH_BUDGET,
        "completed_updates_required": 200,
        "train_seed": TRAIN_SEED,
        "arm_order": ["FULL2", "DROP_C1", "DROP_C2"],
        "route_order": list(ROUTE_ORDER),
        "source_split": "SOURCE_TRAIN",
        "output_root": str(output_root),
        "authority_sha256": provider_config["contract_sha256"],
        "code_sha256": manifest["sha256"],
        "input_binding": input_binding,
        "input_sha256": canonical_sha256(input_binding),
        "closed_split_opened": False,
        "simulator_episode_opened": False,
    }
    if receipt_path is not None:
        raw = canonical_bytes(payload)
        value = write_once(receipt_path, raw)
        write_once(sidecar_path(receipt_path), f"{value}  {receipt_path.name}\n".encode("ascii"))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--bindings", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--provider-config", type=Path)
    parser.add_argument("--model-config", type=Path)
    parser.add_argument("--declaration", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--diagnostic-receipt", type=Path)
    parser.add_argument("--expected-provider-identity")
    parser.add_argument("--no-provider-load", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    try:
        if arguments.diagnostic_receipt:
            verify_diagnostic_receipt(arguments.diagnostic_receipt, arguments.expected_provider_identity)
            print("DIAGNOSTIC_RECEIPT_PASS")
            return 0
        required = (
            arguments.bindings, arguments.manifest, arguments.provider_config,
            arguments.model_config, arguments.declaration, arguments.output_root,
        )
        if any(item is None for item in required):
            parser.error("formal preflight paths are required")
        payload = run_preflight(
            repo=arguments.repo.resolve(), bindings_path=arguments.bindings,
            manifest_path=arguments.manifest, provider_config_path=arguments.provider_config,
            model_config_path=arguments.model_config, declaration_path=arguments.declaration,
            output_root=arguments.output_root, receipt_path=arguments.receipt,
            instantiate_provider=not arguments.no_provider_load,
        )
        print(
            f"SUCCESSOR_PREFLIGHT_PASS input_sha256={payload['input_sha256']} "
            f"provider_identity={payload['input_binding']['provider_identity']}"
        )
        return 0
    except (OSError, ValueError, SuccessorLaunchError) as error:
        print(f"SUCCESSOR_PREFLIGHT_FAIL: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
