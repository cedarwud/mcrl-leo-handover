#!/usr/bin/env python3
"""Build one immutable exact-invocation shadow-replay launch authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3s_shadow_replay as runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--screen-run", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--arm", choices=runner.COORDINATOR_ARMS, default="LITE")
    parser.add_argument("--horizon", type=int, default=runner.HORIZON)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        launch = runner._parser().parse_args(args.launch_arguments)
        key = runner.v1runner.UnitKey.parse(launch.unit) if launch.unit else None
        if (
            launch.dry_run or launch.estimate or (key is None) == (not launch.merge)
            or launch.launch_authority is None
            or Path(launch.launch_authority).resolve() != Path(args.output).resolve()
            or Path(launch.preflight_manifest).resolve()
            != Path(args.preflight_manifest).resolve()
            or launch.screen_run is None
            or Path(launch.screen_run).resolve() != Path(args.screen_run).resolve()
            or runner._local(launch.output, field="output root")
            != runner._local(args.output_root, field="output root")
            or launch.arm != args.arm or launch.horizon != args.horizon
        ):
            raise runner.ShadowReplayError(
                "launch arguments do not bind this exact shadow unit/merge invocation"
            )
        execution = {
            "mode": "unit" if key is not None else "merge",
            "unit": None if key is None else key.as_dict(),
        }
        payload = runner.build_launch_authority(
            preflight_manifest=args.preflight_manifest, screen_run=args.screen_run,
            output=args.output_root, arm=args.arm, horizon=args.horizon,
            execution=execution, launch_arguments=args.launch_arguments,
        )
        target, digest = runner._write_once(
            args.output, runner.canonical_bytes(payload) + b"\n",
        )
    except Exception as error:
        print(f"C3S_SHADOW_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_SHADOW_AUTHORITY_PASS authority={target} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
