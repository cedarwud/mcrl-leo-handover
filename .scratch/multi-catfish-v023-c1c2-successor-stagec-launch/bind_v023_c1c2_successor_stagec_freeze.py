#!/usr/bin/env python3
"""Bind authenticated Stage-A outputs and immutable Stage-B/C inputs once."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import stagec_common as common


PASS_SOURCE = "PASS_SOURCE_TRAINING_INTEGRITY"


def _load_module(name: str, path: Path) -> Any:
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    module = importlib.import_module(path.stem)
    if Path(module.__file__).resolve() != path.resolve():
        raise common.StageCError(f"module origin drifted: {name}")
    return module


def _verify_plain_sidecar(path: Path, expected: str) -> None:
    sidecar = common.regular_file(path.with_name(path.name + ".sha256"), field=f"{path.name} sidecar")
    if sidecar.read_text(encoding="ascii") != f"{expected}\n":
        raise common.StageCError(f"producer digest sidecar disagrees: {path}")


def bind_stage_a(root: Path) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise common.StageCError("sealed Stage-A output root is unavailable")
    complete = common.regular_file(root / "COMPLETE", field="Stage-A COMPLETE").read_text(encoding="ascii")
    manifest_path = root / "MANIFEST.sha256"
    entries = common.parse_sha256_manifest(manifest_path, root=root)
    manifest_sha = common.file_sha256(manifest_path, field="Stage-A manifest")
    if complete != f"{manifest_sha}  MANIFEST.sha256\n":
        raise common.StageCError("Stage-A COMPLETE does not authenticate MANIFEST.sha256")
    actual_members = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
        and path.relative_to(root).as_posix() not in {"MANIFEST.sha256", "COMPLETE"}
    }
    if actual_members != set(entries):
        raise common.StageCError("Stage-A whole-tree manifest is incomplete or contains extra entries")
    receipt_path = root / "canonical-receipt.json"
    receipt = common.read_json(receipt_path, field="Stage-A canonical receipt")
    decision = receipt.get("epoch_100_integrity")
    if not isinstance(decision, Mapping) or decision.get("decision") != PASS_SOURCE:
        raise common.StageCError("Stage-A canonical receipt did not pass source-training integrity")
    if receipt.get("arm_order") != list(common.LEARNED_ARMS):
        raise common.StageCError("Stage-A arm order drifted")
    common.forbid_policy_tokens(receipt, field="Stage-A canonical receipt")
    export_manifest_path = root / "exports/epoch-0100.json"
    export_manifest = common.read_json(export_manifest_path, field="Stage-A epoch-100 export manifest")
    if export_manifest.get("epoch") != 100 or export_manifest.get("update_count") != 200:
        raise common.StageCError("Stage-A export boundary drifted")
    if export_manifest.get("arm_order") != list(common.LEARNED_ARMS):
        raise common.StageCError("Stage-A export arm order drifted")
    common.forbid_policy_tokens(export_manifest, field="Stage-A export manifest")
    raw_exports = export_manifest.get("exports")
    if not isinstance(raw_exports, list) or len(raw_exports) != 3:
        raise common.StageCError("Stage A must publish exactly three epoch-100 exports")
    exports = []
    for arm, entry in zip(common.LEARNED_ARMS, raw_exports, strict=True):
        if not isinstance(entry, Mapping) or entry.get("arm") != arm or entry.get("update_count") != 200:
            raise common.StageCError(f"Stage-A export entry drifted: {arm}")
        relative_raw = entry.get("path")
        if not isinstance(relative_raw, str):
            raise common.StageCError(f"Stage-A export path missing: {arm}")
        relative = Path(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise common.StageCError(f"unsafe Stage-A export path: {relative_raw}")
        path = root / relative
        observed = common.file_sha256(path, field=f"{arm} epoch-100 export")
        declared = common.digest(entry.get("sha256"), field=f"{arm} epoch-100 export digest")
        if observed != declared or entries.get(relative.as_posix()) != declared:
            raise common.StageCError(f"Stage-A export authentication failed: {arm}")
        _verify_plain_sidecar(path, declared)
        exports.append({"arm": arm, "path": relative.as_posix(), "sha256": declared})
    receipt_relative = receipt_path.relative_to(root).as_posix()
    receipt_sha = common.file_sha256(receipt_path, field="Stage-A PASS receipt")
    if entries.get(receipt_relative) != receipt_sha:
        raise common.StageCError("Stage-A PASS receipt is not sealed by MANIFEST.sha256")
    return {
        "root": str(root.resolve()),
        "complete_line": complete.rstrip("\n"),
        "manifest_sha256": manifest_sha,
        "pass_receipt": {"path": receipt_relative, "sha256": receipt_sha},
        "exports": exports,
    }


def bind_baseline(checkpoint: Path, status: Path, adapter_path: Path = common.BASELINE / "baseline_adapter.py") -> dict[str, object]:
    if common.file_sha256(checkpoint, field="BASELINE checkpoint") != common.BASELINE_CHECKPOINT_SHA256:
        raise common.StageCError("BASELINE checkpoint digest drifted")
    adapter_module = _load_module("v023_stagec_baseline_adapter_binding", adapter_path)
    try:
        adapter = adapter_module.BaselineAdapter.from_artifacts(checkpoint, status)
    except Exception as error:
        raise common.StageCError("BASELINE adapter authentication failed") from error
    excluded = getattr(adapter, "contract_fields_excluded", None)
    if excluded is None:
        excluded = getattr(adapter_module, "CONTRACT_FIELDS_EXCLUDED", None)
    binding_method = getattr(adapter, "binding", None)
    if excluded is None and callable(binding_method):
        adapter_binding = binding_method()
        if isinstance(adapter_binding, Mapping):
            excluded = adapter_binding.get("contract_fields_excluded")
    if excluded is not True:
        raise common.StageCError("BASELINE adapter must assert contract_fields_excluded: true")
    if adapter.checkpoint_sha256 != common.BASELINE_CHECKPOINT_SHA256 or adapter.state_dim != 112:
        raise common.StageCError("BASELINE adapter invariants drifted")
    closure_paths = [
        adapter_path,
        common.REPO / "src/mcrl/runtime/q_network.py",
        common.REPO / "src/mcrl/runtime/state_encoding.py",
        common.REPO / "src/mcrl/env/action_contract.py",
        common.REPO / "src/mcrl/env/step_types.py",
    ]
    closure = {
        path.resolve().relative_to(common.REPO.resolve()).as_posix(): common.file_sha256(path)
        for path in closure_paths
    }
    return {
        "checkpoint_path": str(checkpoint.resolve()),
        "checkpoint_sha256": common.BASELINE_CHECKPOINT_SHA256,
        "status_path": str(status.resolve()),
        "status_sha256": common.file_sha256(status, field="BASELINE status"),
        "adapter_closure": closure,
        "adapter_closure_sha256": common.canonical_sha256(closure),
        "contract_fields_excluded": True,
        "state_dim": 112,
        "training_episodes": 9000,
        "routes": [],
    }


def _package_manifest(paths: list[Path]) -> dict[str, object]:
    entries = {
        path.resolve().relative_to(common.REPO.resolve()).as_posix(): common.file_sha256(path)
        for path in sorted(paths)
    }
    return {"entries": entries, "manifest_sha256": common.canonical_sha256(entries)}


def build_bindings(args: argparse.Namespace) -> dict[str, object]:
    if args.stage_c_output.exists() or args.stage_c_output.is_symlink():
        raise common.StageCError("Stage-C output root must be absent at freeze")
    if args.stage_b_output.exists() or args.stage_b_output.is_symlink():
        raise common.StageCError("Stage-B output root must be absent at freeze")
    code_sha, code_entries = common.verify_code_manifest()
    declaration_sha = common.verify_named_sidecar(common.DECLARATION)
    schedule_sha = common.file_sha256(
        common.SCHEDULING_ADDENDUM, field="Stage-C scheduling addendum"
    )
    stage_a = (
        bind_stage_a(args.stage_a_output)
        if args.stage_a_output is not None
        else {
            "status": "PENDING_PREDETERMINED_STAGE_A_AUTHENTICATION",
            "required_for_arms": list(common.LEARNED_ARMS),
            "scheduling_addendum_sha256": schedule_sha,
            "exports": [],
        }
    )
    baseline = bind_baseline(args.baseline_checkpoint, args.baseline_status)

    builder = _load_module(
        "v023_stagec_world_plan_builder_binding",
        common.PHYSICAL / "build_v023_c1c2_successor_world_plan.py",
    )
    if args.plan_output.exists() or args.plan_output.is_symlink():
        raise common.StageCError("world-plan output must be absent before freeze build")
    payload = builder.build_world_plan()
    builder._write_once(args.plan_output, payload)
    if builder.read_world_plan(args.plan_output)["plan_sha256"] != common.PLAN_SHA256:
        raise common.StageCError("rebuilt 9000-world plan digest disagrees with declaration")

    tle_rows, tle_manifest_sha = common.tree_manifest(args.tle_root)
    physical_paths = [path for path in common.PHYSICAL.iterdir() if path.is_file() and not path.name.endswith(".pyc")]
    transitive = {
        relative: sha for relative, sha in code_entries.items()
        if relative.startswith("src/mcrl/") or "baseline-adapter" in relative or "two-route-source-training-runner" in relative
    }
    bundle_prefix = common.HERE.resolve().relative_to(common.REPO.resolve()).as_posix() + "/"
    bundle_entries = {relative: sha for relative, sha in code_entries.items() if relative.startswith(bundle_prefix)}
    result: dict[str, object] = {
        "schema": common.SCHEMA_BINDINGS,
        "formal": True,
        "arms": list(common.ARMS),
        "trained_arms": list(common.LEARNED_ARMS),
        "stage_a": stage_a,
        "baseline": baseline,
        "world_plan": {
            "path": str(args.plan_output.resolve()),
            "file_sha256": common.file_sha256(args.plan_output, field="world plan"),
            "plan_sha256": common.PLAN_SHA256,
            "episode_budget": 9000,
            "pauses": list(common.PAUSES),
        },
        "stage_b_output_root": str(args.stage_b_output.resolve(strict=False)),
        "stage_c_output_root": str(args.stage_c_output.resolve(strict=False)),
        "physical_inputs": {
            "prereg_path": str(common.PREREG.resolve()),
            "prereg_sha256": common.file_sha256(common.PREREG, field="PREREG"),
            "tle_root": str(args.tle_root.resolve()),
            "tle_manifest": tle_rows,
            "tle_manifest_sha256": tle_manifest_sha,
            "keyed_field_namespace": common.FIELD_COMPONENT,
        },
        "execution": common.process_environment(),
        "code": {
            "external_manifest_path": str((common.HERE / common.CODE_MANIFEST_NAME).resolve()),
            "external_manifest_sha256": code_sha,
            "stagec_bundle": {"entries": bundle_entries, "manifest_sha256": common.canonical_sha256(bundle_entries)},
            "physical_evaluation": _package_manifest(physical_paths),
            "transitive_closure": {"entries": transitive, "manifest_sha256": common.canonical_sha256(transitive)},
        },
        "git": common.git_identity(common.REPO),
        "contract": {
            "path": str(common.CONTRACT.resolve()),
            "sha256": common.file_sha256(common.CONTRACT, field="development contract"),
            "scientific_declaration_path": str(common.DECLARATION.resolve()),
            "scientific_declaration_sha256": declaration_sha,
        },
        "scheduling_addendum": {
            "path": str(common.SCHEDULING_ADDENDUM.resolve()),
            "sha256": schedule_sha,
            "stage_a_pin_name": "stage_c_scheduling_addendum_sha256",
            "scientific_declaration_changed": False,
        },
        "claim_ceiling": common.FORMAL_CLAIM,
        "continuation_to_9000_authorized": False,
    }
    common.assert_no_placeholders(result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-a-output", type=Path)
    parser.add_argument("--plan-output", type=Path, required=True)
    parser.add_argument("--stage-b-output", type=Path, required=True)
    parser.add_argument("--stage-c-output", type=Path, required=True)
    parser.add_argument("--baseline-checkpoint", type=Path, default=common.BASELINE_CHECKPOINT)
    parser.add_argument("--baseline-status", type=Path, default=common.BASELINE_STATUS)
    parser.add_argument("--tle-root", type=Path, default=common.TLE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=common.HERE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    destination = args.output_dir / common.BINDINGS_NAME
    try:
        if destination.exists() or destination.is_symlink():
            raise common.StageCError("execution bindings already exist")
        bindings = build_bindings(args)
        common.write_once(destination, bindings)
        common.write_digest_sidecar(destination)
        runner = _load_module(
            "v023_stagec_physical_runner_early_admission",
            common.PHYSICAL / "v023_c1c2_successor_physical_runner.py",
        )
        baseline = bindings["baseline"]
        policy = runner.load_baseline_policy(
            checkpoint_path=baseline["checkpoint_path"],
            status_path=baseline["status_path"],
            expected_status_sha256=baseline["status_sha256"],
        )
        common.ensure_early_baseline_admission(
            bindings=bindings,
            bindings_path=destination,
            path=args.output_dir / common.EARLY_BASELINE_ADMISSION_NAME,
            runner_schema=runner.SCHEMA,
            policy_binding=policy.binding(),
        )
    except Exception as error:
        print(f"STAGEC_BIND_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"STAGEC_BINDINGS_WRITTEN path={destination} sha256={common.file_sha256(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
