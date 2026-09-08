#!/usr/bin/env python3
"""Build one immutable exact-invocation authority for C3-S diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3s_diagnostic_arms as runner


def build_authority(
    *, preflight_manifest: Path, output_root: Path,
    launch_arguments: Sequence[str], authority_path: Path,
) -> dict[str, object]:
    manifest, preflight_sha = runner.validate_preflight_manifest(preflight_manifest)
    arguments = list(launch_arguments)
    parsed = runner._parser().parse_args(arguments)
    selected = runner.parse_arms(parsed.arms)
    target = runner.UnitKey.parse(parsed.unit) if parsed.unit else None
    destination = runner.donor._local(output_root, field="diagnostic output root")
    authority = runner.donor._local(authority_path, field="diagnostic launch authority")
    if (
        parsed.dry_run or parsed.estimate or (parsed.unit is None) == (not parsed.merge)
        or parsed.launch_authority is None
        or Path(parsed.launch_authority).resolve() != authority
        or Path(parsed.preflight_manifest).resolve() != Path(preflight_manifest).resolve()
        or runner.donor._local(parsed.output, field="diagnostic output root") != destination
        or parsed.handover_energy_sensitivity and not parsed.merge
    ):
        raise runner.DiagnosticRunnerError("launch arguments do not bind one exact invocation")
    static = runner.static_bindings()
    return {
        "schema": runner.LAUNCH_AUTHORITY_SCHEMA, "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": runner.CLAIM_CEILING,
        "preflight_manifest": {"path": str(Path(preflight_manifest).resolve()), "sha256": preflight_sha},
        "source_contract": static["source_contract"], "code_files": static["code_files"],
        "lineage_authorities": static["lineage_authorities"],
        "preregistration": static["preregistration"], "tle_archive": static["tle_archive"],
        "execution": {
            "mode": "unit" if target is not None else "merge",
            "unit": None if target is None else target.as_dict(),
            "panel": runner.panel_bindings(
                horizon=parsed.horizon, arms=selected,
                assert_null_equals_base=parsed.assert_null_equals_base,
                physics_override=parsed.physics_override,
            ),
        },
        "output_root": str(destination), "launch_arguments": arguments,
        "merge_analysis": {
            "handover_energy_sensitivity": bool(parsed.handover_energy_sensitivity),
        },
        "preflight_status": manifest["status"],
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }


def write_authority(
    *, preflight_manifest: Path, output_root: Path,
    launch_arguments: Sequence[str], output: Path,
) -> tuple[Path, Path, str]:
    target = runner.donor._local(output, field="diagnostic launch authority")
    payload = build_authority(
        preflight_manifest=preflight_manifest, output_root=output_root,
        launch_arguments=launch_arguments, authority_path=target,
    )
    return runner.donor.write_once_with_sidecar(target, payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        runner.donor.pin_single_thread_runtime()
        target, sidecar, digest = write_authority(
            preflight_manifest=args.preflight_manifest, output_root=args.output_root,
            launch_arguments=args.launch_arguments, output=args.output,
        )
    except Exception as error:
        print(f"C3S_DIAGNOSTIC_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_DIAGNOSTIC_AUTHORITY_PASS authority={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
