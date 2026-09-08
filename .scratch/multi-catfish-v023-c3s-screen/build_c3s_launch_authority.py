#!/usr/bin/env python3
"""Build one immutable per-invocation C3S launch authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3s_screen as screen


def build_authority(
    *, preflight_manifest: Path, contract: Path, output_root: Path,
    launch_arguments: Sequence[str], authority_path: Path,
) -> dict[str, object]:
    preflight_path = Path(preflight_manifest)
    manifest, preflight_sha = screen.validate_preflight_manifest(preflight_path)
    sealed_contract = screen.sealed_contract_binding()
    if not Path(contract).is_absolute() or str(Path(contract).resolve()) != sealed_contract["path"]:
        raise screen.C3SScreenError("--contract must be the absolute controller-sealed C3S contract")
    destination = screen._local(Path(output_root), field="output root")
    authority = screen._local(Path(authority_path), field="launch authority")
    arguments = list(launch_arguments)
    if not arguments or any(not isinstance(value, str) for value in arguments):
        raise screen.C3SScreenError("--launch-arguments must bind one runner invocation")
    parsed = screen._parser().parse_args(arguments)
    if (
        parsed.dry_run or parsed.estimate
        or (parsed.unit is None) == (not parsed.merge)
        or parsed.launch_authority is None
        or Path(parsed.launch_authority).resolve() != authority
        or Path(parsed.preflight_manifest).resolve() != preflight_path.resolve()
        or screen._local(parsed.output, field="output root") != destination
    ):
        raise screen.C3SScreenError("launch arguments do not bind one exact C3S unit/merge invocation")
    target = screen.UnitKey.parse(parsed.unit) if parsed.unit is not None else None
    if parsed.horizon != screen.DEFAULT_HORIZON:
        raise screen.C3SScreenError("formal authority requires the contract-fixed 30-step horizon")
    static = screen.validate_static_bindings()
    return {
        "schema": screen.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": screen.CLAIM_CEILING,
        "contract": sealed_contract,
        "preflight_manifest": {"path": str(preflight_path.resolve()), "sha256": preflight_sha},
        "lineage_authorities": static["lineage_authorities"],
        "preregistration": static["preregistration"],
        "tle_archive": static["tle_archive"],
        "code_files": screen.expected_code_bindings(),
        "freeze_provenance": {
            "evidence_manifest": manifest["evidence_manifest"],
            "world_census": manifest["world_census"],
            "freeze": manifest["freeze"],
        },
        "execution": {
            "mode": "unit" if target is not None else "merge",
            "unit": None if target is None else target.as_dict(),
            "panel": screen.panel_bindings(parsed.horizon),
            "eta_ref_exact": screen.fraction_payload(
                screen.c3s_policy.load_eta_ref(screen.CONFIG_PATH)
            ),
        },
        "output_root": str(destination),
        "launch_arguments": arguments,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def write_authority(
    *, preflight_manifest: Path, contract: Path, output_root: Path,
    launch_arguments: Sequence[str], output: Path,
) -> tuple[Path, Path, str]:
    target = screen._local(output, field="launch authority")
    payload = build_authority(
        preflight_manifest=preflight_manifest, contract=contract,
        output_root=output_root, launch_arguments=launch_arguments,
        authority_path=target,
    )
    return screen.write_once_with_sidecar(target, payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        screen.pin_single_thread_runtime()
        target, sidecar, digest = write_authority(
            preflight_manifest=args.preflight_manifest, contract=args.contract,
            output_root=args.output_root, launch_arguments=args.launch_arguments,
            output=args.output,
        )
    except Exception as error:
        print(f"C3S_LAUNCH_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_LAUNCH_AUTHORITY_PASS authority={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
