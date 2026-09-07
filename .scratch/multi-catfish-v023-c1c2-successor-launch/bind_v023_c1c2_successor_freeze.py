#!/usr/bin/env python3
"""Bind sealed target, code, learner, model, baseline, and git identities."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from successor_launch_common import (
    BASELINE_ADAPTER_REL,
    BINDINGS_NAME,
    BUNDLE_REL,
    CLAIM_CEILING,
    CONTRACT_NAME,
    DECLARATION_NAME,
    EPOCH_BUDGET,
    EXECUTION_BINDINGS_SCHEMA,
    EXPECTED_MODEL_CONFIG_SHA256,
    FACTORY_REL,
    PHYSICAL_EVALUATION_REL,
    LAUNCH_MANIFEST_NAME,
    LAUNCH_MANIFEST_SIDECAR,
    LEARNER_MANIFEST_NAME,
    LEARNER_MANIFEST_SCHEMA,
    MODEL_CONFIG_NAME,
    PROTOCOL_REL,
    PROVIDER_CONFIG_NAME,
    PROVIDER_CONFIG_SCHEMA,
    REVIEW_REL,
    ROUTE_ORDER,
    RUNNER_REL,
    SUCCESSOR_REL,
    TARGET_ADAPTER_REL,
    TARGET_ROOT,
    TRAINER_REL,
    TRAIN_SEED,
    SuccessorLaunchError,
    assert_contract_placeholders,
    canonical_bytes,
    directory_files,
    file_manifest,
    file_sha256,
    read_canonical_json,
    reject_forbidden_config,
    sidecar_path,
    validate_no_circular_digest,
    verify_stage_c_code_bundle,
    verify_sidecar,
    write_reproducible,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GENERATED_BUNDLE_NAMES = {
    BINDINGS_NAME,
    BINDINGS_NAME + ".sha256",
    LEARNER_MANIFEST_NAME,
    PROVIDER_CONFIG_NAME,
    PROVIDER_CONFIG_NAME + ".sha256",
    LAUNCH_MANIFEST_NAME,
    LAUNCH_MANIFEST_SIDECAR,
    "PREFLIGHT-RECEIPT.json",
    "PREFLIGHT-RECEIPT.json.sha256",
}


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=repo, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _git_identity(repo: Path) -> dict[str, Any]:
    excluded = [
        f":(exclude){(BUNDLE_REL / name).as_posix()}"
        for name in sorted(GENERATED_BUNDLE_NAMES)
    ]
    dirty = bool(
        _git(
            repo,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            ".",
            *excluded,
        )
    )
    return {
        "commit_sha": _git(repo, "rev-parse", "HEAD"),
        "tree_sha": _git(repo, "rev-parse", "HEAD^{tree}"),
        "dirty": dirty,
    }


def _baseline_checkpoint_constant(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "EXPECTED_CHECKPOINT_SHA256"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, str) and len(value) == 64:
                return value
    raise SuccessorLaunchError("baseline adapter checkpoint constant is unavailable")


def _bundle_code_paths(repo: Path) -> list[Path]:
    return [
        path for path in directory_files(repo, BUNDLE_REL)
        if path.name not in GENERATED_BUNDLE_NAMES
    ]


def _load_factory(repo: Path) -> Any:
    for entry in (repo / "src", repo / FACTORY_REL):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    return importlib.import_module("v023_c1c2_provider_factory_v3")


def _initialization_bytes_sha256(repo: Path, model_path: Path) -> str:
    for entry in (repo / "src", repo / RUNNER_REL):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    runner = importlib.import_module("v023_two_route_source_training_runner")
    orchestrator = importlib.import_module("v023_two_route_learner_orchestrator")
    model = orchestrator.EEAxisTwoRouteModel(
        runner._load_model_config(model_path), train_seed=TRAIN_SEED
    )
    state = model.checkpoint_state(
        update_count=0, route_update_counts={"C1": 0, "C2": 0}
    )
    return hashlib.sha256(orchestrator._torch_bytes(state)).hexdigest()


def _world_plan_sha256(repo: Path) -> str:
    directory = repo / PHYSICAL_EVALUATION_REL
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    builder = importlib.import_module("build_v023_c1c2_successor_world_plan")
    origin = Path(builder.__file__).resolve(strict=True)
    if origin != (directory / "build_v023_c1c2_successor_world_plan.py").resolve(strict=True):
        raise SuccessorLaunchError("Stage-C world-plan builder origin drifted")
    plan = builder.build_world_plan()
    observed = builder.verify_world_plan(plan)
    expected = "866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb"
    if observed != expected:
        raise SuccessorLaunchError("Stage-C 9000-world plan digest drifted")
    return observed


def _verify_learner_manifest(repo: Path, manifest_path: Path) -> str:
    factory = _load_factory(repo)
    learner_runtime_modules = dict(factory.derive_learner_runtime_modules())
    payload = read_canonical_json(manifest_path, field="successor learner manifest")
    if payload.get("schema") != LEARNER_MANIFEST_SCHEMA or payload.get("status") != "FROZEN":
        raise SuccessorLaunchError("successor learner manifest header drifted")
    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or [item.get("path") for item in bindings] != sorted(learner_runtime_modules):
        raise SuccessorLaunchError("successor learner manifest L-list drifted")
    for item in bindings:
        path = item.get("path")
        if item.get("module") != learner_runtime_modules.get(path):
            raise SuccessorLaunchError(f"successor learner module drifted: {path}")
        if file_sha256(repo / path) != item.get("sha256"):
            raise SuccessorLaunchError(f"successor learner runtime drifted: {path}")
    return file_sha256(manifest_path)


def build_payloads(repo: Path, target_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    factory = _load_factory(repo)
    learner_runtime_modules = dict(factory.derive_learner_runtime_modules())
    if not learner_runtime_modules:
        raise SuccessorLaunchError("factory-v3 derived an empty learner runtime")
    try:
        target_snapshot = factory._target_snapshot(target_root)
        target_artifact = factory._TARGET.load_completed_target_artifact(target_root)
        factory._validate_target_artifact(target_artifact)
    except Exception as error:
        if target_root.is_symlink() or not target_root.is_dir():
            raise SuccessorLaunchError(
                f"required r8 target root is absent: {target_root}"
            ) from error
        raise SuccessorLaunchError("sealed target root failed typed authentication") from error
    target_manifest = target_root / "MANIFEST.sha256"
    target_receipt = target_root / "receipt.json"
    target_complete = target_root / "COMPLETE"
    for path in (target_manifest, target_receipt, target_complete):
        file_sha256(path)
    complete_raw = target_complete.read_bytes()
    try:
        complete_line = complete_raw.decode("ascii")
    except UnicodeError as error:
        raise SuccessorLaunchError("target COMPLETE is not ASCII") from error
    target_manifest_sha = file_sha256(target_manifest)
    if target_snapshot["manifest_sha256"] != target_manifest_sha:
        raise SuccessorLaunchError("target snapshot manifest digest drifted")
    if complete_line != f"{target_manifest_sha}  MANIFEST.sha256\n":
        raise SuccessorLaunchError("target COMPLETE does not authenticate MANIFEST.sha256")

    model_path = repo / SUCCESSOR_REL / MODEL_CONFIG_NAME
    model_sha = verify_sidecar(model_path)
    if model_sha != EXPECTED_MODEL_CONFIG_SHA256:
        raise SuccessorLaunchError("successor model config digest drifted")
    declaration_path = repo / SUCCESSOR_REL / DECLARATION_NAME
    declaration_sha = verify_sidecar(declaration_path)
    contract_path = repo / SUCCESSOR_REL / CONTRACT_NAME
    review_path = repo / REVIEW_REL
    baseline_path = repo / BASELINE_ADAPTER_REL
    baseline_checkpoint_path = (
        repo / "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"
    )
    baseline_status_path = baseline_checkpoint_path.with_name("status.json")
    baseline_constant = _baseline_checkpoint_constant(baseline_path)
    if file_sha256(baseline_checkpoint_path) != baseline_constant:
        raise SuccessorLaunchError("baseline checkpoint disagrees with adapter constant")
    baseline_status_sha = file_sha256(baseline_status_path)
    if baseline_status_sha == baseline_constant:
        raise SuccessorLaunchError("baseline status/authentication digest must be distinct")

    learner_bindings = [
        {"path": path, "module": module, "sha256": file_sha256(repo / path)}
        for path, module in sorted(learner_runtime_modules.items())
    ]
    learner_payload = {
        "schema": LEARNER_MANIFEST_SCHEMA,
        "status": "FROZEN",
        "claim_ceiling": CLAIM_CEILING,
        "bindings": learner_bindings,
    }
    learner_sha = __import__("hashlib").sha256(canonical_bytes(learner_payload)).hexdigest()
    provider_payload = {
        "schema": PROVIDER_CONFIG_SCHEMA,
        "contract_sha256": file_sha256(contract_path),
        "target_root": str(target_root),
        "target_manifest_sha256": target_manifest_sha,
        "target_receipt_sha256": file_sha256(target_receipt),
        "learner_manifest_sha256": learner_sha,
        "model_config_sha256": model_sha,
        "train_seed": TRAIN_SEED,
        "epoch_budget": EPOCH_BUDGET,
    }
    reject_forbidden_config(provider_payload)

    factory_manifest = file_manifest(repo, directory_files(repo, FACTORY_REL))
    runner_manifest = file_manifest(repo, directory_files(repo, RUNNER_REL))
    bundle_manifest = file_manifest(repo, _bundle_code_paths(repo))
    target_adapter_manifest = file_manifest(repo, [TARGET_ADAPTER_REL])
    baseline_adapter_manifest = file_manifest(repo, [BASELINE_ADAPTER_REL])
    support_manifest = file_manifest(repo, [PROTOCOL_REL, TRAINER_REL])
    physical_evaluation_manifest = file_manifest(
        repo, directory_files(repo, PHYSICAL_EVALUATION_REL)
    )
    stage_c_code = verify_stage_c_code_bundle(repo)
    initialization_sha = _initialization_bytes_sha256(repo, model_path)
    world_plan_sha = _world_plan_sha256(repo)
    prereg_path = repo / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
    prereg_payload = json.loads(prereg_path.read_text(encoding="utf-8"))
    tle_file_set_sha = prereg_payload["sections"]["ephemeris"]["file_set_sha256"]
    predecessor_manifest_path = (
        repo / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json"
    )
    predecessor_manifest_sha = file_sha256(predecessor_manifest_path)
    resolutions = {
        "r8_manifest_sha256": target_manifest_sha,
        "r8_receipt_sha256": file_sha256(target_receipt),
        "r8_complete_line": complete_line.rstrip("\n"),
        "factory_v3_manifest_sha256": factory_manifest["manifest_sha256"],
        "learner_manifest_sha256": learner_sha,
        "runner_manifest_sha256": runner_manifest["manifest_sha256"],
    }
    contract_placeholders = {
        key: {"status": "RESOLVED", "value": value}
        for key, value in resolutions.items()
    }
    contract_placeholders["baseline_checkpoint_sha256"] = {
        "status": "RESOLVED", "value": baseline_constant,
    }
    contract_placeholders["evaluation_runner_manifest_sha256"] = {
        "status": "RESOLVED",
        "value": stage_c_code[
            "physical_evaluation_package_manifest_sha256"
        ],
    }
    assert_contract_placeholders(
        contract_path.read_text(encoding="utf-8"), contract_placeholders
    )
    bindings_payload = {
        "schema": EXECUTION_BINDINGS_SCHEMA,
        "status": "FROZEN_STAGE_A",
        "claim_ceiling": CLAIM_CEILING,
        "resolved_stage_a_placeholders": resolutions,
        "contract_placeholder_bindings": contract_placeholders,
        "target": {
            "root": str(target_root),
            "manifest_sha256": target_manifest_sha,
            "receipt_sha256": file_sha256(target_receipt),
            "complete_sha256": file_sha256(target_complete),
            "complete_line": complete_line.rstrip("\n"),
        },
        "authority": {
            "contract_path": (SUCCESSOR_REL / CONTRACT_NAME).as_posix(),
            "contract_sha256": file_sha256(contract_path),
            "scientific_declaration_path": (SUCCESSOR_REL / DECLARATION_NAME).as_posix(),
            "scientific_declaration_sha256": declaration_sha,
            "astra_review_path": REVIEW_REL.as_posix(),
            "astra_review_sha256": file_sha256(review_path),
        },
        "code_manifests": {
            "factory_v3": factory_manifest,
            "runner_package": runner_manifest,
            "launch_bundle": bundle_manifest,
            "target_adapter": target_adapter_manifest,
            "baseline_adapter": baseline_adapter_manifest,
            "support_runtime": support_manifest,
            "physical_evaluation_package": physical_evaluation_manifest,
        },
        "learner": {
            "manifest_path": (BUNDLE_REL / LEARNER_MANIFEST_NAME).as_posix(),
            "manifest_sha256": learner_sha,
            "runtime_manifest_sha256": __import__("hashlib").sha256(
                canonical_bytes(learner_bindings)[:-1]
            ).hexdigest(),
            "runtime_file_count": len(learner_bindings),
            "initialization_bytes_sha256": initialization_sha,
            "sampler_policy": "deterministic-route-source-order-with-recorded-consumed-file-order",
            "rng_policy": {
                "train_seed": TRAIN_SEED,
                "torch": "torch.manual_seed-before-each-independent-model-construction",
                "provider": "authenticated-deterministic-per-route-sampler",
            },
        },
        "baseline": {
            "checkpoint_path": baseline_checkpoint_path.relative_to(repo).as_posix(),
            "checkpoint_sha256": baseline_constant,
            "status_path": baseline_status_path.relative_to(repo).as_posix(),
            "status_authentication_sha256": baseline_status_sha,
            "state_dim": 112,
            "episodes": 9000,
            "routes": [],
            "adapter_manifest_sha256": baseline_adapter_manifest["manifest_sha256"],
        },
        "model_config": {
            "path": (SUCCESSOR_REL / MODEL_CONFIG_NAME).as_posix(),
            "sha256": model_sha,
        },
        "predecessor_authorities": {
            "producer_preflight_manifest_path": predecessor_manifest_path.relative_to(repo).as_posix(),
            "producer_preflight_manifest_sha256": predecessor_manifest_sha,
            "prereg_path": prereg_path.relative_to(repo).as_posix(),
            "prereg_sha256": file_sha256(prereg_path),
            "frozen_tle_file_set_sha256": tle_file_set_sha,
        },
        "stage_c": {
            "world_plan_sha256": world_plan_sha,
            "physical_evaluation_package_manifest_sha256": stage_c_code[
                "physical_evaluation_package_manifest_sha256"
            ],
            "runner_bundle_manifest_sha256": stage_c_code[
                "stage_c_bundle_manifest_sha256"
            ],
            "verifier_bundle_manifest_sha256": stage_c_code[
                "stage_c_bundle_manifest_sha256"
            ],
            "code_bundle": stage_c_code,
            "keyed_field_namespace": "MCRL_V020_REPRICED_C3_GATE_V1",
            "aggregation": {
                "energy_efficiency": "ratio-of-sums:additive-bits-over-additive-positive-energy",
                "service": "pooled-served-over-pooled-opportunity",
            },
            "integrity_dispositions": [
                "STOP_PLUMBING_INTEGRITY", "STOP_PHYSICAL_EVALUATION_INTEGRITY",
            ],
        },
        "execution_policy": {
            "deterministic_environment": {
                "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            "resource_limits": {
                "server": "sat", "tmux_session": "mcrl-v023-c1c2-successor-100e-r1",
                "source_epoch_budget": EPOCH_BUDGET, "updates_per_learner": 200,
            },
            "required_absent_roots": {
                "source_training": "/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1",
                "one_epoch_diagnostic": "/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout/successor-one-epoch-diagnostic-scratch",
                "physical_evaluation": "/home/sat/mcrl-v023-c1c2-successor-physical-evaluation-20260907-r1",
            },
        },
        "provider_config": {
            "path": (BUNDLE_REL / PROVIDER_CONFIG_NAME).as_posix(),
            "sha256": __import__("hashlib").sha256(canonical_bytes(provider_payload)).hexdigest(),
        },
        "git": _git_identity(repo),
    }
    validate_no_circular_digest(bindings_payload)
    return learner_payload, provider_payload, bindings_payload


def _write_or_check(path: Path, payload: dict[str, Any], *, check: bool, sidecar: bool) -> str:
    raw = canonical_bytes(payload)
    value = write_reproducible(path, raw, check=check)
    if sidecar:
        line = f"{value}  {path.name}\n".encode("ascii")
        write_reproducible(sidecar_path(path), line, check=check)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--target-root", type=Path, default=TARGET_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--verify-learner-manifest-only", action="store_true")
    arguments = parser.parse_args(argv)
    repo = arguments.repo.resolve()
    bundle = repo / BUNDLE_REL
    try:
        if arguments.verify_learner_manifest_only:
            value = _verify_learner_manifest(repo, bundle / LEARNER_MANIFEST_NAME)
            print(f"SUCCESSOR_LEARNER_MANIFEST_PASS sha256={value}")
            return 0
        learner, provider, bindings = build_payloads(repo, arguments.target_root)
        learner_sha = _write_or_check(
            bundle / LEARNER_MANIFEST_NAME, learner, check=arguments.check, sidecar=False
        )
        provider_sha = _write_or_check(
            bundle / PROVIDER_CONFIG_NAME, provider, check=arguments.check, sidecar=True
        )
        bindings_sha = _write_or_check(
            bundle / BINDINGS_NAME, bindings, check=arguments.check, sidecar=True
        )
        verb = "CURRENT" if arguments.check else "WRITTEN"
        print(
            f"SUCCESSOR_EXECUTION_BINDINGS_{verb} bindings_sha256={bindings_sha} "
            f"learner_sha256={learner_sha} provider_sha256={provider_sha}"
        )
        return 0
    except (OSError, subprocess.SubprocessError, SuccessorLaunchError) as error:
        print(f"SUCCESSOR_EXECUTION_BINDINGS_FAIL: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
