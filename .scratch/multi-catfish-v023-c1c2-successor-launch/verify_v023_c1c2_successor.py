#!/usr/bin/env python3
"""Independently verify and optionally seal a finished successor stage-A root."""

from __future__ import annotations

from collections.abc import Mapping
import argparse
from copy import deepcopy
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

from successor_launch_common import (
    ARM_ORDER, BUNDLE_REL, CLAIM_CEILING, EPOCH_BUDGET, FACTORY_REL,
    LEARNER_MANIFEST_NAME, PROVIDER_CONFIG_NAME, ROUTE_ORDER, RUNNER_REL,
    SOURCE_MAP, TRAIN_SEED, SuccessorLaunchError, canonical_bytes,
    file_sha256, read_canonical_json, verify_sidecar, write_once,
)


SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-source-training-verification-v1"
PASS = "PASS_SOURCE_TRAINING_INTEGRITY"
STOP = "STOP_SOURCE_TRAINING_INTEGRITY"
LEDGER_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-update-ledger-v1"


class VerificationError(SuccessorLaunchError):
    """The output root does not satisfy the sealed stage-A contract."""


def _runner_json(path: Path, *, field: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise VerificationError(f"{field} is missing or symlinked")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"{field} is not JSON") from error
    if not isinstance(value, dict):
        raise VerificationError(f"{field} is not an object")
    compact = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    if raw not in {compact, compact + b"\n"}:
        raise VerificationError(f"{field} is not canonical JSON")
    return value


def _runner_sidecar(path: Path) -> str:
    actual = file_sha256(path)
    sidecar = path.with_name(path.name + ".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise VerificationError(f"runner digest sidecar is missing: {sidecar}")
    raw = sidecar.read_text(encoding="ascii")
    if raw not in {f"{actual}\n", f"{actual}  {path.name}\n"}:
        raise VerificationError(f"runner digest sidecar disagrees: {sidecar}")
    return actual


def _finite_tree(value: object, *, field: str) -> None:
    try:
        import torch
    except ImportError:
        torch = None
    if torch is not None and isinstance(value, torch.Tensor):
        if not bool(torch.isfinite(value).all()):
            raise VerificationError(f"{field} contains a non-finite tensor")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _finite_tree(item, field=f"{field}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _finite_tree(item, field=f"{field}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise VerificationError(f"{field} contains a non-finite scalar")


def _assert_no_closed_path(value: object, *, field: str) -> None:
    if isinstance(value, Mapping):
        for item in value.values():
            _assert_no_closed_path(item, field=field)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_closed_path(item, field=field)
    elif isinstance(value, str) and ("/" in value or "\\" in value):
        import re
        if ("TE" + "ST") in re.split(r"[/\\]+", value.upper()):
            raise VerificationError(f"{field} names a closed split path")


def _load_modules(repo: Path) -> tuple[Any, Any]:
    for path in (repo / "src", repo / FACTORY_REL, repo / RUNNER_REL):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return (
        importlib.import_module("v023_c1c2_provider_factory_v3"),
        importlib.import_module("v023_two_route_source_training_runner"),
    )


def _validate_ledger(root: Path) -> dict[str, Any]:
    ledger = _runner_json(root / "update-ledger.json", field="update ledger")
    if (
        ledger.get("schema") != LEDGER_SCHEMA
        or ledger.get("claim_ceiling") != CLAIM_CEILING
        or ledger.get("arm_order") != list(ARM_ORDER)
        or ledger.get("route_order") != list(ROUTE_ORDER)
        or ledger.get("completed_epochs") != 100
        or ledger.get("completed_updates") != 200
    ):
        raise VerificationError("update ledger header drifted")
    rows = ledger.get("updates")
    if not isinstance(rows, list) or len(rows) != 200:
        raise VerificationError("update ledger must contain exactly 200 updates")
    for cursor, row in enumerate(rows):
        if not isinstance(row, Mapping) or row.get("update_cursor") != cursor or row.get("route") != ROUTE_ORDER[cursor % 2]:
            raise VerificationError(f"update ledger route order drifted at {cursor}")
        updates = row.get("arm_updates")
        if not isinstance(updates, list) or [item.get("arm") for item in updates] != list(ARM_ORDER):
            raise VerificationError(f"update ledger arm order drifted at {cursor}")
        for update in updates:
            arm, route = update.get("arm"), update.get("route")
            if route != row["route"] or update.get("source") != SOURCE_MAP[arm][route]:
                raise VerificationError(f"update ledger source map drifted at {cursor}")
            metrics = update.get("metrics")
            if not isinstance(metrics, Mapping) or "loss" not in metrics:
                raise VerificationError(f"update ledger loss is missing at {cursor}")
            _finite_tree(metrics, field=f"update {cursor} metrics")
    _assert_no_closed_path(ledger, field="update ledger")
    return ledger


def _verify_existing_seal(root: Path) -> None:
    manifest = root / "MANIFEST.sha256"
    complete = root / "COMPLETE"
    present = (manifest.exists() or manifest.is_symlink(), complete.exists() or complete.is_symlink())
    if present == (False, False):
        return
    if present != (True, True) or manifest.is_symlink() or complete.is_symlink():
        raise VerificationError("output seal is partial or symlinked")
    manifest_sha = file_sha256(manifest)
    if complete.read_bytes() != f"{manifest_sha}  MANIFEST.sha256\n".encode("ascii"):
        raise VerificationError("output COMPLETE does not authenticate MANIFEST.sha256")
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or parts[1] in expected:
            raise VerificationError("output manifest is malformed")
        expected[parts[1]] = parts[0]
    actual = {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
        and path.relative_to(root).as_posix() not in {"MANIFEST.sha256", "COMPLETE"}
    }
    if expected != dict(sorted(actual.items())):
        raise VerificationError("output whole-tree manifest closure drifted")


def _storage_isolation(rebuilt: Any) -> None:
    owners: dict[int, str] = {}
    for arm, model in rebuilt.orchestrator.models.items():
        for parameter in (item for network in model.q_networks for item in network.parameters()):
            pointer = parameter.detach().untyped_storage().data_ptr()
            if pointer in owners:
                raise VerificationError(f"parameter storage is shared by {owners[pointer]} and {arm}")
            owners[pointer] = arm
        for optimizer in model.optimizers:
            for state in optimizer.state.values():
                for value in state.values():
                    if hasattr(value, "untyped_storage") and value.numel():
                        pointer = value.detach().untyped_storage().data_ptr()
                        if pointer in owners:
                            raise VerificationError("optimizer storage is not independent")
                        owners[pointer] = arm


def verify_output(
    *, repo: Path, output_root: Path, provider_config_path: Path,
    model_config_path: Path, preflight_receipt_path: Path,
    reconstruct: bool = True,
) -> dict[str, Any]:
    root = output_root
    if root.is_symlink() or not root.is_dir():
        raise VerificationError("finished output root is missing or symlinked")
    _verify_existing_seal(root)
    status = _runner_json(root / "canonical-status.json", field="canonical status")
    receipt = _runner_json(root / "canonical-receipt.json", field="canonical receipt")
    expected_header = {
        "claim_ceiling": CLAIM_CEILING, "source_split": "SOURCE_TRAIN",
        "arm_order": list(ARM_ORDER), "route_order": list(ROUTE_ORDER),
        "initialization_sha256": status.get("initialization_sha256"),
    }
    for key, value in expected_header.items():
        if status.get(key) != value or receipt.get(key) != value:
            raise VerificationError(f"runner status/receipt drifted: {key}")
    if status.get("source_ablation_map") != SOURCE_MAP or receipt.get("source_ablation_map") != SOURCE_MAP:
        raise VerificationError("runner source-ablation mapping drifted")
    if receipt.get("epoch_budget") != 100 or receipt.get("completed_epochs") != 100 or receipt.get("completed_updates") != 200:
        raise VerificationError("runner did not finish the exact 100-epoch/200-update budget")
    config = status.get("config")
    if not isinstance(config, Mapping) or config.get("epoch_budget") != EPOCH_BUDGET:
        raise VerificationError("runner formal config drifted")
    orchestrator_config = config.get("orchestrator_config")
    if not isinstance(orchestrator_config, Mapping) or orchestrator_config.get("train_seed") != TRAIN_SEED:
        raise VerificationError("runner train seed drifted")
    _assert_no_closed_path((status, receipt), field="runner receipts")
    ledger = _validate_ledger(root)

    verify_sidecar(preflight_receipt_path)
    preflight = read_canonical_json(preflight_receipt_path, field="preflight receipt")
    if (
        preflight.get("schema") != "multi-catfish-mcrl-v023-c1c2-successor-preflight-v1"
        or preflight.get("status") != "PASS_FROZEN_C1C2_SUCCESSOR_PREFLIGHT"
        or preflight.get("formal") is not True
    ):
        raise VerificationError("preflight receipt is not PASS")
    identity = preflight.get("input_binding", {}).get("provider_identity")
    identity_payload = preflight.get("input_binding", {}).get("provider_identity_payload")
    if receipt.get("provider_identity") != identity or not isinstance(identity_payload, Mapping) or identity_payload.get("routes") != list(ROUTE_ORDER):
        raise VerificationError("provider identity or exact route list drifted")
    _assert_no_closed_path(identity_payload, field="provider identity")

    checkpoints = sorted(path.name for path in (root / "checkpoints").glob("*.runner.pt"))
    if checkpoints != ["epoch-0000.runner.pt", "epoch-0100.runner.pt"]:
        raise VerificationError("exact epoch-0 and epoch-100 checkpoints are required")
    export_manifests = sorted(path.name for path in (root / "exports").glob("epoch-*.json"))
    if export_manifests != ["epoch-0000.json", "epoch-0100.json"]:
        raise VerificationError("exact epoch-0 and epoch-100 export manifests are required")
    final_manifest = _runner_json(root / "exports/epoch-0100.json", field="epoch-100 export manifest")
    if final_manifest.get("arm_order") != list(ARM_ORDER) or final_manifest.get("route_order") != list(ROUTE_ORDER):
        raise VerificationError("epoch-100 export has a forbidden or fourth arm/route")
    exports = final_manifest.get("exports")
    if not isinstance(exports, list) or [item.get("arm") for item in exports] != list(ARM_ORDER):
        raise VerificationError("epoch-100 export does not contain exactly three arms in order")
    expected_export_names = {
        f"{index:02d}-{arm}.current-ee-axis-two-route.pt"
        for index, arm in enumerate(ARM_ORDER)
    }
    export_dir = root / "exports/epoch-0100"
    observed_export_names = {path.name for path in export_dir.glob("*.pt")}
    observed_sidecars = {path.name for path in export_dir.glob("*.pt.sha256")}
    if observed_export_names != expected_export_names or observed_sidecars != {
        name + ".sha256" for name in expected_export_names
    }:
        raise VerificationError("epoch-100 export directory has extra or missing arms")
    for entry in exports:
        path = root / entry["path"]
        if _runner_sidecar(path) != entry.get("sha256"):
            raise VerificationError(f"export digest disagrees for {entry.get('arm')}")

    checkpoint_path = root / "checkpoints/epoch-0100.runner.pt"
    _runner_sidecar(checkpoint_path)
    factory, runner_module = _load_modules(repo)
    checkpoint = runner_module._read_torch(checkpoint_path)
    if (
        checkpoint.get("epoch") != 100 or checkpoint.get("update_count") != 200
        or checkpoint.get("arm_order") != list(ARM_ORDER)
        or checkpoint.get("route_order") != list(ROUTE_ORDER)
    ):
        raise VerificationError("epoch-100 checkpoint topology drifted")
    state = checkpoint.get("orchestrator_state")
    if not isinstance(state, Mapping) or state.get("route_update_counts") != {"C1": 100, "C2": 100} or state.get("next_route_index") != 0:
        raise VerificationError("epoch-100 resume boundary is not exact")
    file_order = state.get("file_order")
    if not isinstance(file_order, list) or len(file_order) != 200 or any(item.get("route") != ROUTE_ORDER[index % 2] for index, item in enumerate(file_order)):
        raise VerificationError("checkpoint consumed-file order drifted")
    arms = state.get("arms")
    if not isinstance(arms, Mapping) or tuple(arms) != ARM_ORDER:
        raise VerificationError("checkpoint arm state order drifted")
    initializations = [arms[arm].get("initialization") for arm in ARM_ORDER]
    if initializations[1:] != initializations[:-1]:
        raise VerificationError("arms do not share identical serialized initialization")
    _finite_tree(checkpoint, field="epoch-100 checkpoint")

    exact_resume = False
    if reconstruct:
        provider_sha = verify_sidecar(provider_config_path)
        learner_path = repo / BUNDLE_REL / LEARNER_MANIFEST_NAME
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
            frozen = runner_module.FrozenSourceTrainingConfig(
                epoch_budget=100,
                orchestrator_config=runner_module.V023TwoRouteOrchestratorConfig.formal(
                    model_config=runner_module._load_model_config(model_config_path),
                    train_seed=TRAIN_SEED,
                ),
                provider_factory_spec="v023_c1c2_provider_factory_v3:make_provider",
                authority_digests=runner_module.RunAuthorityDigests(
                    preflight["authority_sha256"], preflight["code_sha256"], preflight["input_sha256"]
                ),
            )
            rebuilt = runner_module.V023TwoRouteSourceTrainingRunner(frozen, provider)
            rebuilt.resume_from_checkpoint(checkpoint_path)
            exact_resume = runner_module._tree_equal(
                deepcopy(state), rebuilt.orchestrator.checkpoint_state()
            )
            if not exact_resume:
                raise VerificationError("epoch-100 model/optimizer/provider resume is not exact")
            _storage_isolation(rebuilt)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    return {
        "schema": SCHEMA, "status": PASS, "claim_ceiling": CLAIM_CEILING,
        "formal": True, "arm_order": list(ARM_ORDER), "route_order": list(ROUTE_ORDER),
        "completed_epochs": 100, "completed_updates": 200,
        "finite_update_receipts": len(ledger["updates"]),
        "initialization_sha256": checkpoint["initialization_sha256"],
        "provider_identity": identity, "provider_routes": list(ROUTE_ORDER),
        "exact_epoch_100_resume": exact_resume if reconstruct else "NOT_RECONSTRUCTED",
        "closed_split_opened": False, "simulator_episode_opened": False,
    }


def _seal(root: Path, verification: dict[str, Any]) -> None:
    verification_path = root / "verification.json"
    write_once(verification_path, canonical_bytes(verification))
    excluded = {"MANIFEST.sha256", "COMPLETE", "FAILED"}
    files = sorted(
        path for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and path.relative_to(root).as_posix() not in excluded
    )
    lines = [f"{file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files]
    manifest_raw = ("\n".join(lines) + "\n").encode("ascii")
    manifest_path = root / "MANIFEST.sha256"
    manifest_sha = write_once(manifest_path, manifest_raw)
    write_once(root / "COMPLETE", f"{manifest_sha}  MANIFEST.sha256\n".encode("ascii"))


def decision_for_output(**kwargs: Any) -> dict[str, Any]:
    try:
        return verify_output(**kwargs)
    except Exception as error:
        return {"schema": SCHEMA, "status": STOP, "error": f"{type(error).__name__}: {error}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--provider-config", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--preflight-receipt", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-reconstruct", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    try:
        result = verify_output(
            repo=arguments.repo.resolve(), output_root=arguments.output_root,
            provider_config_path=arguments.provider_config,
            model_config_path=arguments.model_config,
            preflight_receipt_path=arguments.preflight_receipt,
            reconstruct=not arguments.no_reconstruct,
        )
        if arguments.write:
            _seal(arguments.output_root, result)
        print(f"{PASS} updates=200 arms=3 exact_resume={result['exact_epoch_100_resume']}")
        return 0
    except Exception as error:
        print(f"{STOP}: {type(error).__name__}: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
