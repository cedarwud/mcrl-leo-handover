#!/usr/bin/env python3
"""Authenticate every frozen stage-A input without creating the output root."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

from successor_launch_common import (
    BINDINGS_NAME, BUNDLE_REL, CLAIM_CEILING, DECLARATION_NAME,
    EPOCH_BUDGET, EXECUTION_BINDINGS_SCHEMA, EXPECTED_MODEL_CONFIG_SHA256,
    FACTORY_REL, LAUNCH_MANIFEST_NAME, LEARNER_MANIFEST_NAME,
    MODEL_CONFIG_NAME, PROVIDER_CONFIG_NAME, PROVIDER_CONFIG_SCHEMA,
    ROUTE_ORDER, RUNNER_REL, SUCCESSOR_REL, TARGET_ROOT, TRAIN_SEED,
    SuccessorLaunchError, canonical_bytes, canonical_sha256, file_sha256,
    assert_contract_placeholders, assert_predetermined_stage_c_bound,
    assert_sync_coverage, digest, read_canonical_json, reject_forbidden_config,
    required_sync_closure, sidecar_path,
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


def _load_orchestrator(repo: Path) -> Any:
    for path in (repo / "src", repo / FACTORY_REL, repo / RUNNER_REL):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    module = importlib.import_module("v023_two_route_learner_orchestrator")
    origin = Path(module.__file__).resolve(strict=True)
    expected = (
        repo / RUNNER_REL / "v023_two_route_learner_orchestrator.py"
    ).resolve(strict=True)
    if origin != expected:
        raise SuccessorLaunchError("orchestrator imported from an unexpected checkout")
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


def _provider_identity(
    provider: object, *, factory: Any | None = None, orchestrator: Any | None = None
) -> tuple[str, dict[str, Any]]:
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
    factory = _load_factory(REPO) if factory is None else factory
    declared_fields = getattr(factory, "PROVIDER_IDENTITY_FIELDS", None)
    if not isinstance(declared_fields, frozenset) or set(payload) != declared_fields:
        raise SuccessorLaunchError("provider identity field set drifted from factory-v3")
    orchestrator = _load_orchestrator(REPO) if orchestrator is None else orchestrator
    try:
        orchestrator.authenticate_factory_v3_provider_identity(
            provider,
            expected_train_seed=TRAIN_SEED,
            expected_model_config_sha256=EXPECTED_MODEL_CONFIG_SHA256,
        )
    except Exception as error:
        raise SuccessorLaunchError(
            "provider identity fails orchestrator authentication"
        ) from error
    if payload.get("routes") != list(ROUTE_ORDER):
        raise SuccessorLaunchError("provider identity routes are not exactly C1/C2")
    if payload.get("epoch_budget") != EPOCH_BUDGET or payload.get("train_seed") != TRAIN_SEED:
        raise SuccessorLaunchError("provider identity budget or train seed drifted")
    return identity, payload


def verify_diagnostic_receipt(
    path: Path,
    expected_provider_identity: str | None = None,
    expected_preflight_receipt: Path | None = None,
) -> dict[str, Any]:
    verify_sidecar(path)
    receipt = read_canonical_json(path, field="one-epoch diagnostic receipt")
    if (
        receipt.get("schema") != DIAGNOSTIC_SCHEMA
        or receipt.get("status") != DIAGNOSTIC_STATUS
        or receipt.get("formal") is not False
        or receipt.get("failed_checks") != []
    ):
        raise SuccessorLaunchError("one-epoch diagnostic did not pass")
    required_checks = {
        "factory_v3_real_target_loaded",
        "one_epoch_route_order",
        "one_epoch_losses_finite",
        "c2_loss_uses_pre_update_q2_weights",
        "c2_post_update_weight_mutation_is_rejected",
        "export_reload_exact",
        "exact_continuation_after_reload",
    }
    checks = receipt.get("checks")
    if not isinstance(checks, dict) or set(checks) != required_checks or any(
        value is not True for value in checks.values()
    ):
        raise SuccessorLaunchError("one-epoch diagnostic behavioural evidence is incomplete")
    required_timings = {
        "factory_v3_real_target_load", "one_c1_to_c2_epoch",
        "c2_pre_update_behavioural_check", "export_and_reload",
        "exact_continuation", "total",
    }
    timings = receipt.get("phase_timings_s")
    if not isinstance(timings, dict) or set(timings) != required_timings or any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0.0
        for value in timings.values()
    ):
        raise SuccessorLaunchError("one-epoch diagnostic timing evidence is incomplete")
    identity_fields = {
        "provider_config_sha256", "model_config_sha256", "learner_manifest_sha256",
        "factory_code_sha256", "diagnostic_code_sha256",
    }
    for field in identity_fields:
        try:
            digest(receipt.get(field), field=f"one-epoch diagnostic {field}")
        except SuccessorLaunchError as error:
            raise SuccessorLaunchError(f"one-epoch diagnostic identity is incomplete: {field}")
    if expected_provider_identity is not None and receipt.get("provider_identity") != expected_provider_identity:
        raise SuccessorLaunchError("one-epoch diagnostic provider identity drifted")
    if expected_preflight_receipt is not None:
        verify_sidecar(expected_preflight_receipt)
        preflight = read_canonical_json(
            expected_preflight_receipt, field="diagnostic-bound preflight receipt"
        )
        binding = preflight.get("input_binding")
        if not isinstance(binding, dict):
            raise SuccessorLaunchError("diagnostic preflight identity is incomplete")
        expected = {
            "provider_identity": binding.get("provider_identity"),
            "provider_config_sha256": binding.get("provider_config_sha256"),
            "model_config_sha256": binding.get("model_config_sha256"),
            "learner_manifest_sha256": binding.get("learner_manifest_sha256"),
            "factory_code_sha256": binding.get("factory_code_sha256"),
            "diagnostic_code_sha256": binding.get("diagnostic_code_sha256"),
        }
        if any(receipt.get(key) != value for key, value in expected.items()):
            raise SuccessorLaunchError("one-epoch diagnostic is not bound to this launch")
    return receipt


def _verify_target_root(
    *, bindings: dict[str, Any], provider_config: dict[str, Any],
    target_root: Path, formal: bool,
) -> None:
    frozen_target_root = bindings.get("target", {}).get("root")
    if not isinstance(frozen_target_root, str) or not frozen_target_root:
        raise SuccessorLaunchError("execution bindings target root is missing")
    if str(target_root) != frozen_target_root:
        raise SuccessorLaunchError("requested target root disagrees with execution bindings")
    if provider_config.get("target_root") != frozen_target_root:
        raise SuccessorLaunchError("factory-v3 config drifted: target_root")
    if formal and target_root != TARGET_ROOT:
        raise SuccessorLaunchError("formal target root is not the declared target root")


def run_preflight(
    *, repo: Path, bindings_path: Path, manifest_path: Path,
    provider_config_path: Path, model_config_path: Path,
    declaration_path: Path, output_root: Path, receipt_path: Path | None,
    target_root: Path, formal: bool,
    instantiate_provider: bool = True,
) -> dict[str, Any]:
    if output_root.exists() or output_root.is_symlink():
        raise SuccessorLaunchError("formal output root must be absent")
    bindings_sha = verify_sidecar(bindings_path)
    bindings = read_canonical_json(bindings_path, field="execution bindings")
    if (
        bindings.get("schema") != EXECUTION_BINDINGS_SCHEMA
        or bindings.get("status") != "FROZEN_STAGE_A"
    ):
        raise SuccessorLaunchError("execution bindings schema drifted")
    contract_path = repo / SUCCESSOR_REL / "V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md"
    assert_contract_placeholders(
        contract_path.read_text(encoding="utf-8"),
        bindings.get("contract_placeholder_bindings", {}),
    )
    assert_predetermined_stage_c_bound(repo, bindings)
    manifest = verify_launch_manifest(repo, manifest_path)
    assert_sync_coverage(required_sync_closure(repo), [Path(path) for path in manifest["paths"]])
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
        "train_seed": TRAIN_SEED,
        "epoch_budget": EPOCH_BUDGET,
        "model_config_sha256": EXPECTED_MODEL_CONFIG_SHA256,
    }
    for key, value in expected.items():
        if provider_config.get(key) != value:
            raise SuccessorLaunchError(f"factory-v3 config drifted: {key}")
    _verify_target_root(
        bindings=bindings, provider_config=provider_config,
        target_root=target_root, formal=formal,
    )
    if bindings.get("provider_config", {}).get("sha256") != provider_sha:
        raise SuccessorLaunchError("execution bindings disagree with provider config")
    learner_path = repo / BUNDLE_REL / LEARNER_MANIFEST_NAME
    learner_sha = file_sha256(learner_path)
    if provider_config["learner_manifest_sha256"] != learner_sha:
        raise SuccessorLaunchError("provider config learner manifest digest drifted")
    required_manifest_paths = {
        (BUNDLE_REL / BINDINGS_NAME).as_posix(),
        (BUNDLE_REL / LEARNER_MANIFEST_NAME).as_posix(),
        (BUNDLE_REL / PROVIDER_CONFIG_NAME).as_posix(),
        (SUCCESSOR_REL / DECLARATION_NAME).as_posix(),
        (SUCCESSOR_REL / MODEL_CONFIG_NAME).as_posix(),
    }
    if not required_manifest_paths.issubset(set(manifest["paths"])):
        raise SuccessorLaunchError("launch manifest omits a generated or sealed authority input")

    identity = "NOT_INSTANTIATED"
    identity_payload: dict[str, Any] = {"routes": list(ROUTE_ORDER)}
    if instantiate_provider:
        factory = _load_factory(repo)
        orchestrator = _load_orchestrator(repo)
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
            identity, identity_payload = _provider_identity(
                provider, factory=factory, orchestrator=orchestrator
            )
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
        "learner_manifest_sha256": learner_sha,
        "target_manifest_sha256": provider_config["target_manifest_sha256"],
        "factory_code_sha256": identity_payload.get("factory_code_sha256"),
        "diagnostic_code_sha256": file_sha256(
            repo / BUNDLE_REL / "run_v023_c1c2_successor_one_epoch_diagnostic.py"
        ),
        "initialization_bytes_sha256": bindings.get("learner", {}).get(
            "initialization_bytes_sha256"
        ),
    }
    requested_output_root = str(output_root.resolve(strict=False))
    payload = {
        "schema": SCHEMA,
        "status": STATUS,
        "claim_ceiling": CLAIM_CEILING,
        "formal": formal,
        "epoch_budget": EPOCH_BUDGET,
        "completed_updates_required": 200,
        "train_seed": TRAIN_SEED,
        "arm_order": ["FULL2", "DROP_C1", "DROP_C2"],
        "route_order": list(ROUTE_ORDER),
        "source_split": "SOURCE_TRAIN",
        "output_root": requested_output_root,
        "requested_output_root": requested_output_root,
        "launch_manifest_path": str(manifest_path.resolve(strict=True)),
        "launch_manifest_sha256": manifest["sha256"],
        "execution_bindings_path": str(bindings_path.resolve(strict=True)),
        "execution_bindings_sha256": bindings_sha,
        "authority_sha256": provider_config["contract_sha256"],
        "code_sha256": learner_sha,
        "input_binding": input_binding,
        "input_sha256": provider_config["target_manifest_sha256"],
        "preflight_input_bundle_sha256": canonical_sha256(input_binding),
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
    parser.add_argument("--target-root", type=Path, default=TARGET_ROOT)
    parser.add_argument("--formal", action="store_true")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--diagnostic-receipt", type=Path)
    parser.add_argument("--expected-provider-identity")
    parser.add_argument("--diagnostic-preflight-receipt", type=Path)
    parser.add_argument("--no-provider-load", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    try:
        if arguments.diagnostic_receipt:
            verify_diagnostic_receipt(
                arguments.diagnostic_receipt,
                arguments.expected_provider_identity,
                arguments.diagnostic_preflight_receipt,
            )
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
            target_root=arguments.target_root, formal=arguments.formal,
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
