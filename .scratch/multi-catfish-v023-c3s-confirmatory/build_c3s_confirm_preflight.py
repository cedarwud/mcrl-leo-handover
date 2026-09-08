#!/usr/bin/env python3
"""Build the immutable launch preflight after the scientific plan is sealed."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Mapping, Sequence

import build_c3s_confirm_world_plan as plan_builder
import run_v023_c3s_confirmatory as runner


SCREEN_CONTRACT = runner.SCREEN_DIR / "V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md"  # Provenance: astra B/C v1 contract.
MATRIX_CONTRACT = runner.VARIANT_DIR / "V023-C3S-VARIANT-MATRIX-KILL-SCREEN-CONTRACT-2026-09-08.md"  # Provenance: astra B/C matrix contract.


def _binding(path: Path, *, sealed: bool = False) -> dict[str, str]:
    return runner.validate_sealed_file(path) if sealed else {"path": str(path.resolve()), "sha256": runner.file_sha256(path)}


def selected_catalog(matrix: Mapping[str, object], v1: Mapping[str, object]) -> str:
    """Compatibility name for the binding function; returns a configuration id."""

    result = runner.resolve_confirmatory_arm(matrix, v1)
    if result == runner.ARM_UNRESOLVED:
        raise runner.ConfirmatoryError("ARM_UNRESOLVED: matrix/v1 progression inputs do not authorize a confirmatory arm")
    return result


def _require_pass(path: Path, *, stage: str) -> tuple[dict[str, str], dict[str, object]]:
    binding = runner.validate_sealed_file(path)
    payload = runner.read_json(path, field=f"{stage} PASS receipt")
    if stage == "stage-A":
        decision = payload.get("epoch_100_integrity")
        passed = payload.get("status") == "PASS_SOURCE_TRAINING_INTEGRITY" or (
            isinstance(decision, Mapping) and decision.get("decision") == "PASS_SOURCE_TRAINING_INTEGRITY"
        )
        attempt = payload.get("attempt", payload.get("attempt_number", payload.get("source_training_attempt")))
        normalized = str(attempt).lower().replace("attempt", "").replace("-", "").replace("#", "").strip()
        if not passed or normalized != "3":
            raise runner.ConfirmatoryError("stage-A PASS receipt is not authenticated attempt #3")
    elif payload.get("status") != "PASS_PLUMBING_INTEGRITY" or payload.get("formal") is not True:
        raise runner.ConfirmatoryError("stage-B PASS receipt is absent or non-formal")
    return binding, payload


def _full2_export(
    stage_a_manifest: Path, stage_b_pass: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    manifest = runner.read_json(stage_a_manifest, field="stage-A attempt-3 epoch-100 export manifest")
    exports = manifest.get("exports")
    if manifest.get("epoch") != 100 or manifest.get("update_count") != 200 or manifest.get("arm_order") != ["FULL2", "DROP_C1", "DROP_C2"] or not isinstance(exports, list):
        raise runner.ConfirmatoryError("stage-A manifest is not the epoch-100/200-update successor export set")
    matches = [entry for entry in exports if isinstance(entry, Mapping) and entry.get("arm") == "FULL2" and entry.get("update_count") == 200]
    if len(matches) != 1:
        raise runner.ConfirmatoryError("stage-A manifest does not bind FULL2 exactly once at update 200")
    entry = dict(matches[0])
    relative, digest = entry.get("path"), entry.get("sha256")
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise runner.ConfirmatoryError("FULL2 export path is unsafe")
    if not isinstance(digest, str) or len(digest) != 64:
        raise runner.ConfirmatoryError("FULL2 export digest is malformed")
    root = stage_a_manifest.parent.parent if stage_a_manifest.parent.name == "exports" else stage_a_manifest.parent
    path = root / relative
    if runner.file_sha256(path) != digest:
        raise runner.ConfirmatoryError("FULL2 export bytes disagree with the stage-A manifest")
    frozen = runner.load_full2_export(path, digest)
    model_binding = frozen.binding()
    q1, q2 = model_binding.get("q1_parameter_sha256"), model_binding.get("q2_parameter_sha256")
    if not all(isinstance(value, str) and len(value) == 64 for value in (q1, q2)):
        raise runner.ConfirmatoryError("FULL2 export lacks Q1/Q2 parameter hashes")
    admitted = stage_b_pass.get("admitted_exports")
    if not isinstance(admitted, list) or not any(isinstance(row, Mapping) and row.get("arm") == "FULL2" and row.get("sha256") == digest for row in admitted):
        raise runner.ConfirmatoryError("stage-B PASS does not admit the same FULL2 export")
    return manifest, {
        "path": str(path.resolve()), "sha256": digest, "entry": entry,
        "q1_parameter_sha256": q1, "q2_parameter_sha256": q2,
        "stage_a_status": "PASS_SOURCE_TRAINING_INTEGRITY", "attempt": 3,
        "epoch": 100, "update_count": 200, "stage_b_status": "PASS_PLUMBING_INTEGRITY",
    }


def build_manifest(
    *, plan_contract: Path, screen_contract: Path, matrix_contract: Path,
    matrix_receipt: Path, v1_receipt: Path, stage_a_pass: Path,
    stage_a_manifest: Path, stage_b_pass: Path, world_plan: Path,
    prereg: Path, tle_manifest: Path, tle_root: Path, output_root: Path,
    reviewer: str, freeze_timestamp_utc: str,
    equivalence_receipt: Path | None = None,
) -> dict[str, object]:
    plan_binding = runner.validate_sealed_file(plan_contract)
    screen_contract_binding = runner.validate_sealed_file(screen_contract)
    matrix_contract_binding = runner.validate_sealed_file(matrix_contract)
    matrix_binding, v1_binding = runner.validate_sealed_file(matrix_receipt), runner.validate_sealed_file(v1_receipt)
    matrix = runner.read_json(matrix_receipt, field="matrix terminal receipt")
    v1 = runner.read_json(v1_receipt, field="v1 terminal receipt")
    configuration = selected_catalog(matrix, v1)
    stage_a_pass_binding, _stage_a = _require_pass(stage_a_pass, stage="stage-A")
    stage_b_pass_binding, stage_b = _require_pass(stage_b_pass, stage="stage-B")
    export_manifest_binding = runner.validate_sealed_file(stage_a_manifest)
    _manifest, full2 = _full2_export(stage_a_manifest, stage_b)
    world_binding = runner.validate_sealed_file(world_plan)
    plan = plan_builder.read_world_plan(world_plan)
    if plan.get("episode_budget") != 9000:
        raise runner.ConfirmatoryError("formal confirmatory world plan must contain 9000 worlds")
    if output_root.exists() or output_root.is_symlink():
        raise runner.ConfirmatoryError("formal output root must be absent at freeze")
    try:
        timestamp = datetime.fromisoformat(freeze_timestamp_utc.replace("Z", "+00:00"))
    except ValueError as error:
        raise runner.ConfirmatoryError("freeze timestamp is not ISO-8601") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp) or not reviewer.strip():
        raise runner.ConfirmatoryError("freeze metadata requires UTC timestamp and reviewer")
    code_paths = (
        runner.HERE / "c3s_full2_policy_adapter.py", runner.HERE / "build_c3s_confirm_world_plan.py",
        runner.HERE / "run_v023_c3s_confirmatory.py", runner.HERE / "build_c3s_confirm_preflight.py",
        runner.HERE / "build_c3s_confirm_launch_authority.py", runner.SCREEN_DIR / "c3s_policy.py",
        runner.VARIANT_DIR / "variant_policy.py", runner.VARIANT_DIR / "variants_config.json",
        runner.BOUNDARY_DONOR, runner.ACCEPTANCE_DONOR, runner.COMMON_DONOR,
    )
    engineering_rebinding = None
    if equivalence_receipt is not None:
        engineering_rebinding = runner.validate_sealed_file(equivalence_receipt)
        receipt = runner.read_json(equivalence_receipt, field="engineering equivalence receipt")
        old_code, new_code = receipt.get("old_code"), receipt.get("new_code")
        if not isinstance(old_code, Mapping) or not isinstance(new_code, Mapping):
            raise runner.ConfirmatoryError("engineering equivalence receipt lacks code bindings")
        runner.verify_equivalence_receipt(equivalence_receipt, old_sha256=str(old_code.get("sha256")), new_sha256=str(new_code.get("sha256")))
        current_code_digests = {runner.file_sha256(path) for path in code_paths}
        if old_code.get("sha256") == new_code.get("sha256") or new_code.get("sha256") not in current_code_digests:
            raise runner.ConfirmatoryError("engineering rebinding does not bind old bytes to the current verified implementation")
    return {
        "schema": f"{runner.SCHEMA}-preflight", "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": runner.CLAIM_CEILING, "plan_v2": plan_binding,
        "contracts": {"screen_v1": screen_contract_binding, "matrix": matrix_contract_binding},
        "arm_resolution": {"function": "ASTRA_B_I_MATRIX_WINNER_THEN_V1_LITE_FALLBACK", "configuration": configuration, "matrix_terminal_receipt": matrix_binding, "v1_terminal_receipt": v1_binding, "matrix_tie_order": list(runner.MATRIX_TIE_ORDER)},
        "stage_a": {"pass_receipt": stage_a_pass_binding, "export_manifest": export_manifest_binding, "full2_export": full2},
        "stage_b": {"pass_receipt": stage_b_pass_binding},
        "coordinator": {
            "code": _binding(runner.SCREEN_DIR / "c3s_policy.py"), "variant_hooks": _binding(runner.VARIANT_DIR / "variant_policy.py"),
            "config": _binding(runner.VARIANT_DIR / "variants_config.json"), "configuration": configuration,
            "eta_ref_float_hex": "0x1.d94fb72305d6ap+26",
        },
        "world_plan": {**world_binding, "plan_sha256": plan["plan_sha256"], "episode_budget": 9000},
        "physical_inputs": {"prereg": _binding(prereg, sealed=True), "tle_manifest": _binding(tle_manifest, sealed=True), "tle_root": str(tle_root.resolve())},
        "acceptance": {"required": True, "episodes_per_arm": 200, "chunks": [[1, 100], [101, 200]], "world_domain": "C3S_CONFIRM_ACCEPT/world/{i}", "comparison_source": _binding(runner.ACCEPTANCE_DONOR), "excluded_fields": list(runner._equivalence_exclusions())},
        "execution": {
            "arms": list(runner.ARMS), "steps": runner.STEPS, "users": runner.USERS,
            "opportunities_per_episode": runner.USERS * runner.STEPS, "chunk_size": runner.CHECKPOINT_EVERY,
            "checkpoints_every": runner.CHECKPOINT_EVERY, "rungs": list(runner.RUNG_BOUNDARIES),
            "futility_boundaries": list(runner.FUTILITY_BOUNDARIES), "terminal_boundary": runner.TERMINAL_BOUNDARY,
            "output_root": str(output_root.resolve()), "test_split_opened": False,
            "episode_training": False, "learner_update": False,
        },
        "engineering_rebinding": engineering_rebinding, "code_files": [_binding(path) for path in code_paths],
        "freeze": {"timestamp_utc": freeze_timestamp_utc, "reviewer": reviewer.strip(), "scientific_seal_precedes_launch": True},
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=runner.DEFAULT_PREFLIGHT)
    parser.add_argument("--plan-contract", type=Path, default=runner.PLAN_CONTRACT_PLACEHOLDER)
    parser.add_argument("--screen-contract", type=Path, default=SCREEN_CONTRACT); parser.add_argument("--matrix-contract", type=Path, default=MATRIX_CONTRACT)
    parser.add_argument("--matrix-receipt", type=Path, required=True); parser.add_argument("--v1-receipt", type=Path, required=True)
    parser.add_argument("--stage-a-pass", type=Path, required=True); parser.add_argument("--stage-a-manifest", type=Path, required=True)
    parser.add_argument("--stage-b-pass", type=Path, required=True); parser.add_argument("--world-plan", type=Path, default=runner.DEFAULT_WORLD_PLAN)
    parser.add_argument("--prereg", type=Path, required=True); parser.add_argument("--tle-manifest", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True); parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reviewer", required=True); parser.add_argument("--freeze-timestamp-utc", required=True)
    parser.add_argument("--equivalence-receipt", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_manifest(
            plan_contract=args.plan_contract, screen_contract=args.screen_contract, matrix_contract=args.matrix_contract,
            matrix_receipt=args.matrix_receipt, v1_receipt=args.v1_receipt, stage_a_pass=args.stage_a_pass,
            stage_a_manifest=args.stage_a_manifest, stage_b_pass=args.stage_b_pass, world_plan=args.world_plan,
            prereg=args.prereg, tle_manifest=args.tle_manifest, tle_root=args.tle_root, output_root=args.output_root,
            reviewer=args.reviewer, freeze_timestamp_utc=args.freeze_timestamp_utc, equivalence_receipt=args.equivalence_receipt,
        )
        digest = runner.write_once(args.output, payload)
    except Exception as error:
        print(f"C3S_CONFIRM_PREFLIGHT_ERROR: {error}", file=sys.stderr); return 2
    print(f"C3S_CONFIRM_PREFLIGHT_PASS path={args.output} sha256={digest}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
