#!/usr/bin/env python3
"""Bind sealed target, code, learner, model, baseline, and git identities."""

from __future__ import annotations

import argparse
import ast
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
    STAGE_A_PLACEHOLDERS,
    SUCCESSOR_REL,
    TARGET_ADAPTER_REL,
    TARGET_ROOT,
    TRAINER_REL,
    TRAIN_SEED,
    SuccessorLaunchError,
    assert_stage_a_placeholders,
    canonical_bytes,
    discover_mcrl_runtime,
    directory_files,
    file_manifest,
    file_sha256,
    read_canonical_json,
    reject_forbidden_config,
    sidecar_path,
    validate_no_circular_digest,
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
LEARNER_RUNTIME_MODULES = {
    "src/mcrl/algorithms/ee_axis_action_shared.py": "mcrl.algorithms.ee_axis_action_shared",
    "src/mcrl/algorithms/ee_axis_pairwise.py": "mcrl.algorithms.ee_axis_pairwise",
    "src/mcrl/algorithms/ee_axis_v014_head.py": "mcrl.algorithms.ee_axis_v014_head",
    "src/mcrl/env/action_contract.py": "mcrl.env.action_contract",
    "src/mcrl/errors.py": "mcrl.errors",
    "src/mcrl/runtime/ee_axis_ops3.py": "mcrl.runtime.ee_axis_ops3",
    "src/mcrl/runtime/ee_axis_state.py": "mcrl.runtime.ee_axis_state",
    "src/mcrl/runtime/ee_axis_v014_q2_state.py": "mcrl.runtime.ee_axis_v014_q2_state",
    "src/mcrl/runtime/ee_surplus_targets.py": "mcrl.runtime.ee_surplus_targets",
    "src/mcrl/runtime/finiteness.py": "mcrl.runtime.finiteness",
    "src/mcrl/runtime/q_network.py": "mcrl.runtime.q_network",
}


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=repo, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _git_identity(repo: Path) -> dict[str, Any]:
    return {
        "commit_sha": _git(repo, "rev-parse", "HEAD"),
        "tree_sha": _git(repo, "rev-parse", "HEAD^{tree}"),
        "dirty": bool(_git(repo, "status", "--porcelain=v1", "--untracked-files=all")),
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


def _verify_learner_manifest(repo: Path, manifest_path: Path) -> str:
    payload = read_canonical_json(manifest_path, field="successor learner manifest")
    if payload.get("schema") != LEARNER_MANIFEST_SCHEMA or payload.get("status") != "FROZEN":
        raise SuccessorLaunchError("successor learner manifest header drifted")
    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or [item.get("path") for item in bindings] != sorted(LEARNER_RUNTIME_MODULES):
        raise SuccessorLaunchError("successor learner manifest L-list drifted")
    for item in bindings:
        path = item.get("path")
        if item.get("module") != LEARNER_RUNTIME_MODULES.get(path):
            raise SuccessorLaunchError(f"successor learner module drifted: {path}")
        if file_sha256(repo / path) != item.get("sha256"):
            raise SuccessorLaunchError(f"successor learner runtime drifted: {path}")
    return file_sha256(manifest_path)


def build_payloads(repo: Path, target_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    factory = _load_factory(repo)
    if dict(factory.REQUIRED_LEARNER_RUNTIME_MODULES) != LEARNER_RUNTIME_MODULES:
        raise SuccessorLaunchError("factory-v3 learner runtime declaration drifted")
    target_snapshot = factory._target_snapshot(target_root)
    try:
        target_artifact = factory._TARGET.load_completed_target_artifact(target_root)
        factory._validate_target_artifact(target_artifact)
    except Exception as error:
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
        for path, module in sorted(LEARNER_RUNTIME_MODULES.items())
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
    transitive_runtime_manifest = file_manifest(repo, discover_mcrl_runtime(repo))
    resolutions = {
        "r8_manifest_sha256": target_manifest_sha,
        "r8_receipt_sha256": file_sha256(target_receipt),
        "r8_complete_line": complete_line.rstrip("\n"),
        "factory_v3_manifest_sha256": factory_manifest["manifest_sha256"],
        "learner_manifest_sha256": learner_sha,
        "runner_manifest_sha256": runner_manifest["manifest_sha256"],
    }
    assert_stage_a_placeholders(contract_path.read_text(encoding="utf-8"), resolutions)
    bindings_payload = {
        "schema": EXECUTION_BINDINGS_SCHEMA,
        "status": "FROZEN_STAGE_A",
        "claim_ceiling": CLAIM_CEILING,
        "resolved_stage_a_placeholders": resolutions,
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
            "transitive_mcrl_runtime": transitive_runtime_manifest,
        },
        "learner": {
            "manifest_path": (BUNDLE_REL / LEARNER_MANIFEST_NAME).as_posix(),
            "manifest_sha256": learner_sha,
            "runtime_manifest_sha256": __import__("hashlib").sha256(
                canonical_bytes(learner_bindings)[:-1]
            ).hexdigest(),
            "runtime_file_count": len(learner_bindings),
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
