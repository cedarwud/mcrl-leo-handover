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
    release_boundary: int | None = None, chunk_start: int | None = None,
    chunk_end: int | None = None, previous_rung_receipt: Path | None = None,
) -> dict[str, object]:
    preflight_binding = runner.validate_sealed_file(preflight)
    manifest = runner.read_json(preflight, field="confirmatory preflight")
    if manifest.get("schema") != f"{runner.SCHEMA}-preflight" or manifest.get("status") != "FROZEN_PREFLIGHT":
        raise runner.ConfirmatoryError("preflight schema/status drifted")
    configured_root = Path(str(manifest.get("execution", {}).get("output_root", ""))).resolve()
    if output_root.resolve() != configured_root:
        raise runner.ConfirmatoryError("authority output root differs from preflight")
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
        if release_boundary not in runner.RUNG_BOUNDARIES:
            raise runner.ConfirmatoryError("formal authority requires one declared rung boundary")
        previous = {100: 0, 500: 100, 1500: 500, 3000: 1500}[int(release_boundary)]
        if previous == 0 and chunk_start is not None and (output_root.exists() or output_root.is_symlink()):
            raise runner.ConfirmatoryError("first-rung authority requires the formal output root to remain absent")
        if previous > 0 and chunk_start is not None and (output_root.is_symlink() or not output_root.is_dir()):
            raise runner.ConfirmatoryError("later-rung authority requires the existing authenticated formal root")
        if (chunk_start is None) != (chunk_end is None):
            raise runner.ConfirmatoryError("formal chunk binding requires both start and end")
        if chunk_start is not None and (
            chunk_start < previous or chunk_end != chunk_start + 100 or chunk_end > int(release_boundary)
        ):
            raise runner.ConfirmatoryError("formal chunk is outside the currently released rung interval")
        if previous == 0:
            if previous_rung_receipt is not None:
                raise runner.ConfirmatoryError("the first rung cannot bind a previous rung receipt")
            release_source = None
        else:
            if previous_rung_receipt is None:
                raise runner.ConfirmatoryError("later rung authority requires the preceding RUNG_HELD receipt")
            release_source = runner.validate_sealed_file(previous_rung_receipt)
            prior = runner.read_json(previous_rung_receipt, field="previous rung receipt")
            if prior.get("completed_episode") != previous or prior.get("rung_status") != runner.RUNG_HELD or prior.get("next_interval_released") is not True:
                raise runner.ConfirmatoryError("previous rung did not release this interval")
    elif acceptance_receipts:
        raise runner.ConfirmatoryError("acceptance authority cannot pre-bind future acceptance receipts")
    elif output_root.exists() or output_root.is_symlink():
        raise runner.ConfirmatoryError("acceptance authority requires the formal output root to remain absent")
    return {
        "schema": f"{runner.SCHEMA}-launch-authority", "status": "FROZEN_LAUNCH_AUTHORITY",
        "mode": mode, "claim_ceiling": runner.CLAIM_CEILING,
        "preflight": preflight_binding,
        "plan_contract": manifest["plan_v2"],
        "stage_a_full2_export": manifest["stage_a"]["full2_export"],
        "coordinator": manifest["coordinator"],
        "world_plan": manifest["world_plan"],
        "physical_inputs": manifest["physical_inputs"],
        "acceptance_receipts": accepted,
        "acceptance_required_before_formal": True,
        "release": None if mode == "acceptance" else {
            "rung_boundary": release_boundary, "chunk_start": chunk_start,
            "chunk_end": chunk_end, "previous_rung_receipt": release_source,
        },
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
    parser.add_argument("--release-boundary", type=int)
    parser.add_argument("--chunk-start", type=int); parser.add_argument("--chunk-end", type=int)
    parser.add_argument("--previous-rung-receipt", type=Path)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_authority(
            preflight=args.preflight, mode=args.mode, launch_arguments=args.launch_arguments,
            output_root=args.output_root, authority_path=args.output,
            acceptance_receipts=args.acceptance_receipt,
            release_boundary=args.release_boundary, chunk_start=args.chunk_start,
            chunk_end=args.chunk_end, previous_rung_receipt=args.previous_rung_receipt,
        )
        digest = runner.write_once(args.output, payload)
    except Exception as error:
        print(f"C3S_CONFIRM_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_CONFIRM_AUTHORITY_PASS path={args.output} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
