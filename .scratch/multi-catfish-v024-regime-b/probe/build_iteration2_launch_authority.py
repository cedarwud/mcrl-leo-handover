#!/usr/bin/env python3
"""Build one immutable exact-invocation B2 launch authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v024_iteration2_probe as runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exposure-timestamp-utc", required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    arguments = list(args.launch_arguments)
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    try:
        runner.pin_single_thread_runtime()
        parsed = runner._parser().parse_args(arguments)
        mode = "unit" if parsed.unit is not None else "merge" if parsed.merge else ""
        if parsed.dry_run or parsed.estimate or not mode:
            raise runner.Iteration2Error("authority must bind one non-dry unit or merge invocation")
        if parsed.preflight.resolve() != args.preflight.resolve() or parsed.output.resolve() != args.output_root.resolve():
            raise runner.Iteration2Error("launch arguments disagree with preflight/output root")
        if parsed.launch_authority is None or parsed.launch_authority.resolve() != args.output.resolve():
            raise runner.Iteration2Error("launch arguments must bind this authority path")
        payload = runner.launch_authority_payload(
            preflight=args.preflight,
            output=args.output_root,
            mode=mode,
            unit=parsed.unit,
            launch_arguments=arguments,
            exposure_timestamp_utc=args.exposure_timestamp_utc,
        )
        target, sidecar, digest = runner.write_once_with_sidecar(args.output, payload)
    except Exception as error:
        print(f"V024_ITERATION2_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"V024_ITERATION2_AUTHORITY_PASS authority={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
