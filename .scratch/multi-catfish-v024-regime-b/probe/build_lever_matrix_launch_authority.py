#!/usr/bin/env python3
"""Build one immutable per-lever exact-invocation launch authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v024_lever_matrix_probe as runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exposure-timestamp-utc", required=True)
    parser.add_argument("--launch-arguments", nargs=argparse.REMAINDER, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        separator_index = raw_arguments.index("--", raw_arguments.index("--launch-arguments") + 1)
    except ValueError:
        pass
    else:
        raw_arguments.pop(separator_index)
    args = _parser().parse_args(raw_arguments)
    arguments = list(args.launch_arguments)
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    try:
        runner.pin_single_thread_runtime()
        parsed = runner._parser().parse_args(arguments)
        mode = "unit" if parsed.unit is not None else "merge" if parsed.merge else ""
        if parsed.estimate or parsed.dry_run or parsed.lever is None or not mode:
            raise runner.MatrixProbeError("authority must bind one non-dry per-lever unit or merge")
        if parsed.preflight.resolve() != args.preflight.resolve() or parsed.output.resolve() != args.output_root.resolve():
            raise runner.MatrixProbeError("launch arguments disagree with preflight/output root")
        if parsed.launch_authority is None or parsed.launch_authority.resolve() != args.output.resolve():
            raise runner.MatrixProbeError("launch arguments must bind this authority path")
        payload = runner.launch_authority_payload(
            preflight=args.preflight,
            output=args.output_root,
            lever_id=parsed.lever,
            mode=mode,
            unit=parsed.unit,
            launch_arguments=arguments,
            exposure_timestamp_utc=args.exposure_timestamp_utc,
        )
        target, sidecar, digest = runner.write_once_with_sidecar(args.output, payload)
    except Exception as error:
        print(f"V024_LEVER_MATRIX_AUTHORITY_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"V024_LEVER_MATRIX_AUTHORITY_PASS authority={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
