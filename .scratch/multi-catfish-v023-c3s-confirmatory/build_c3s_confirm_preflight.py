#!/usr/bin/env python3
"""Build the immutable preflight manifest for the C3-S confirmatory ladder."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import build_c3s_confirm_world_plan as plan_builder
import run_v023_c3s_confirmatory as runner


def _binding(path: Path, *, sealed: bool = False) -> dict[str, str]:
    return runner.validate_sealed_file(path) if sealed else {
        "path": str(path.resolve()), "sha256": runner.file_sha256(path),
    }


def selected_catalog(screen: Mapping[str, object]) -> str:
    if (
        screen.get("status") != "COMPLETE"
        or screen.get("outcome") != "C3S_THREE_ARM_SCREEN_COMPLETE"
        or screen.get("integrity") is not True
    ):
        raise runner.ConfirmatoryError("screen is absent, incomplete, or invalid")
    decisions = screen.get("decisions")
    if not isinstance(decisions, Mapping):
        raise runner.ConfirmatoryError("screen decisions are absent")
    full = decisions.get("FULL")
    lite = decisions.get("LITE")
    if not isinstance(full, Mapping) or not isinstance(lite, Mapping):
        raise runner.ConfirmatoryError("screen progression coverage is malformed")
    full_support = full.get("outcome") == "C3S_FULL_SCREEN_SUPPORT"
    lite_support = lite.get("outcome") == "C3S_LITE_SCREEN_SUPPORT"
    valid_full = full.get("outcome") in ("C3S_FULL_SCREEN_SUPPORT", "C3S_FULL_SCREEN_NO_SUPPORT")
    valid_lite = lite.get("outcome") in ("C3S_LITE_SCREEN_SUPPORT", "C3S_LITE_SCREEN_NO_SUPPORT")
    if not valid_full or not valid_lite:
        raise runner.ConfirmatoryError("screen disposition is not a valid SUPPORT/NO_SUPPORT pair")
    if lite_support:
        return "lite"
    if full_support:
        return "full"
    raise runner.ConfirmatoryError("C3-S progression is closed because neither catalog has SUPPORT")


def _full2_export(stage_a_manifest: Path) -> tuple[dict[str, object], dict[str, object]]:
    manifest = runner.read_json(stage_a_manifest, field="stage-A epoch-100 export manifest")
    exports = manifest.get("exports")
    if (
        manifest.get("epoch") != 100
        or manifest.get("update_count") != 200
        or manifest.get("arm_order") != ["FULL2", "DROP_C1", "DROP_C2"]
        or not isinstance(exports, list)
    ):
        raise runner.ConfirmatoryError("stage-A manifest is not the epoch-100 successor export set")
    matches = [entry for entry in exports if isinstance(entry, Mapping) and entry.get("arm") == "FULL2"]
    if len(matches) != 1:
        raise runner.ConfirmatoryError("stage-A manifest does not bind FULL2 exactly once")
    entry = dict(matches[0])
    relative = entry.get("path")
    digest = entry.get("sha256")
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise runner.ConfirmatoryError("FULL2 export path is unsafe")
    if not isinstance(digest, str) or len(digest) != 64:
        raise runner.ConfirmatoryError("FULL2 export digest is malformed")
    path = stage_a_manifest.parent.parent / relative if stage_a_manifest.parent.name == "exports" else stage_a_manifest.parent / relative
    if runner.file_sha256(path) != digest:
        raise runner.ConfirmatoryError("FULL2 export bytes disagree with the stage-A manifest")
    return manifest, {"path": str(path.resolve()), "sha256": digest, "entry": entry}


def build_manifest(
    *,
    plan_contract: Path,
    screen_receipt: Path,
    stage_a_manifest: Path,
    world_plan: Path,
    prereg: Path,
    tle_manifest: Path,
    tle_root: Path,
    output_root: Path,
    reviewer: str,
    freeze_timestamp_utc: str,
) -> dict[str, object]:
    contract = runner.validate_sealed_file(plan_contract)
    screen_binding = runner.validate_sealed_file(screen_receipt)
    screen = runner.read_json(screen_receipt, field="C3-S screen terminal receipt")
    catalog = selected_catalog(screen)
    timing = screen.get("coordinator_timing")
    if not isinstance(timing, Mapping) or not isinstance(timing.get(catalog.upper()), Mapping):
        raise runner.ConfirmatoryError("screen receipt lacks selected-catalog measured timing")
    stage_a_binding = runner.validate_sealed_file(stage_a_manifest)
    _manifest, full2 = _full2_export(stage_a_manifest)
    plan_binding = runner.validate_sealed_file(world_plan)
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
        runner.HERE / "c3s_full2_policy_adapter.py",
        runner.HERE / "build_c3s_confirm_world_plan.py",
        runner.HERE / "run_v023_c3s_confirmatory.py",
        runner.HERE / "build_c3s_confirm_preflight.py",
        runner.HERE / "build_c3s_confirm_launch_authority.py",
        runner.SCREEN_DIR / "c3s_policy.py",
        runner.SCREEN_DIR / "c3s_config.json",
        runner.BOUNDARY_DONOR,
        runner.ACCEPTANCE_DONOR,
        runner.COMMON_DONOR,
    )
    return {
        "schema": f"{runner.SCHEMA}-preflight", "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": runner.CLAIM_CEILING,
        "plan_contract": contract,
        "screen": {
            **screen_binding, "selected_catalog": catalog,
            "progression_rule": screen.get("progression_rule"),
            "decisions": screen.get("decisions"),
            "timing_binding": {"path": screen_binding["path"], "sha256": screen_binding["sha256"]},
        },
        "stage_a": {"manifest": stage_a_binding, "full2_export": full2},
        "coordinator": {
            "code": _binding(runner.SCREEN_DIR / "c3s_policy.py"),
            "config": _binding(runner.SCREEN_DIR / "c3s_config.json"),
            "catalog": catalog,
            "eta_ref_float_hex": "0x1.d94fb72305d6ap+26",
        },
        "world_plan": {**plan_binding, "plan_sha256": plan["plan_sha256"], "episode_budget": 9000},
        "physical_inputs": {
            "prereg": _binding(prereg, sealed=True),
            "tle_manifest": _binding(tle_manifest, sealed=True),
            "tle_root": str(tle_root.resolve()),
        },
        "acceptance": {
            "required": True, "episodes_per_arm": 200, "chunks": [[1, 100], [101, 200]],
            "world_domain": "C3S_CONFIRM_ACCEPT/world/{i}",
            "comparison_source": _binding(runner.ACCEPTANCE_DONOR),
            "excluded_fields": list(runner._equivalence_exclusions()),
        },
        "execution": {
            "arms": list(runner.ARMS), "steps": 10, "users": 100,
            "chunk_size": 100, "checkpoints_every": 100,
            "rungs": list(runner.RUNG_BOUNDARIES), "terminal_boundary": 3000,
            "output_root": str(output_root.resolve()),
            "test_split_opened": False, "episode_training": False, "learner_update": False,
        },
        "code_files": [_binding(path) for path in code_paths],
        "freeze": {"timestamp_utc": freeze_timestamp_utc, "reviewer": reviewer.strip()},
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=runner.DEFAULT_PREFLIGHT)
    parser.add_argument("--plan-contract", type=Path, default=runner.PLAN_CONTRACT_PLACEHOLDER)
    parser.add_argument("--screen-receipt", type=Path, required=True)
    parser.add_argument("--stage-a-manifest", type=Path, required=True)
    parser.add_argument("--world-plan", type=Path, default=runner.DEFAULT_WORLD_PLAN)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--tle-manifest", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--freeze-timestamp-utc", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_manifest(
            plan_contract=args.plan_contract, screen_receipt=args.screen_receipt,
            stage_a_manifest=args.stage_a_manifest, world_plan=args.world_plan,
            prereg=args.prereg, tle_manifest=args.tle_manifest, tle_root=args.tle_root,
            output_root=args.output_root, reviewer=args.reviewer,
            freeze_timestamp_utc=args.freeze_timestamp_utc,
        )
        digest = runner.write_once(args.output, payload)
    except Exception as error:
        print(f"C3S_CONFIRM_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_CONFIRM_PREFLIGHT_PASS path={args.output} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

