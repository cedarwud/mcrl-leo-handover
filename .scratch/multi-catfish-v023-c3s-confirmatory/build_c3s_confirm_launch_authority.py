#!/usr/bin/env python3
"""Build one immutable acceptance or formal C3-S launch authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3s_confirmatory as runner


def build_authority(
    *, preflight: Path, mode: str, launch_arguments: Sequence[str],
    output_root: Path, authority_path: Path,
    acceptance_receipts: Sequence[Path] = (),
) -> dict[str, object]:
    preflight_binding = runner.validate_sealed_file(preflight)
    manifest = runner.read_json(preflight, field="confirmatory preflight")
    if manifest.get("schema") != f"{runner.SCHEMA}-preflight" or manifest.get("status") != "FROZEN_PREFLIGHT":
        raise runner.ConfirmatoryError("preflight schema/status drifted")
    configured_root = Path(str(manifest.get("execution", {}).get("output_root", ""))).resolve()
    if output_root.resolve() != configured_root:
        raise runner.ConfirmatoryError("authority output root differs from preflight")
    if output_root.exists() or output_root.is_symlink():
        raise runner.ConfirmatoryError("authority requires the formal output root to remain absent")
    if authority_path.exists() or authority_path.is_symlink():
        raise runner.ConfirmatoryError("launch authority path must be absent")
    if mode not in ("acceptance", "formal"):
        raise runner.ConfirmatoryError("authority mode must be acceptance or formal")
    arguments = list(launch_arguments)
    if not arguments or any(not isinstance(value, str) or not value for value in arguments):
        raise runner.ConfirmatoryError("launch arguments must bind one exact invocation")
    accepted: list[dict[str, object]] = []
    if mode == "formal":
        accepted = runner.verify_acceptance_receipts(
            acceptance_receipts, preflight_sha256=preflight_binding["sha256"],
        )
    elif acceptance_receipts:
        raise runner.ConfirmatoryError("acceptance authority cannot pre-bind future acceptance receipts")
    return {
        "schema": f"{runner.SCHEMA}-launch-authority", "status": "FROZEN_LAUNCH_AUTHORITY",
        "mode": mode, "claim_ceiling": runner.CLAIM_CEILING,
        "preflight": preflight_binding,
        "plan_contract": manifest["plan_contract"],
        "stage_a_full2_export": manifest["stage_a"]["full2_export"],
        "coordinator": manifest["coordinator"],
        "world_plan": manifest["world_plan"],
        "physical_inputs": manifest["physical_inputs"],
        "acceptance_receipts": accepted,
        "acceptance_required_before_formal": True,
        "output_root": str(output_root.resolve()),
        "authority_path": str(authority_path.resolve()),
        "launch_arguments": arguments,
        "test_split_opened": False, "episode_training": False, "learner_update": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--mode", choices=("acceptance", "formal"), required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acceptance-receipt", type=Path, action="append", default=[])
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_authority(
            preflight=args.preflight, mode=args.mode, launch_arguments=args.launch_arguments,
            output_root=args.output_root, authority_path=args.output,
            acceptance_receipts=args.acceptance_receipt,
        )
        digest = runner.write_once(args.output, payload)
    except Exception as error:
        print(f"C3S_CONFIRM_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_CONFIRM_AUTHORITY_PASS path={args.output} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

