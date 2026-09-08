#!/usr/bin/env python3
"""Build the immutable matrix-wide code/document/constants/tape preflight."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v024_lever_matrix_probe as runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=runner.DEFAULT_PREFLIGHT)
    parser.add_argument("--exposure-timestamp-utc", required=True)
    parser.add_argument("--reviewer", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        runner.pin_single_thread_runtime()
        payload = runner.build_preflight_payload(exposure_timestamp_utc=args.exposure_timestamp_utc, reviewer=args.reviewer)
        target, sidecar, digest = runner.write_once_with_sidecar(args.output, payload)
    except Exception as error:
        print(f"V024_LEVER_MATRIX_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"V024_LEVER_MATRIX_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
