#!/usr/bin/env python3
"""Build the immutable C-C code-and-binding preflight manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_candidate_cc as cc


def build_manifest() -> dict[str, object]:
    return {
        "schema": cc.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": cc.CLAIM_CEILING,
        **cc.validate_static_bindings(),
        "code_files": cc.expected_code_bindings(),
    }


def write_manifest(path: Path) -> tuple[Path, Path, str]:
    return cc.write_once_with_sidecar(Path(path), build_manifest())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=cc.DEFAULT_PREFLIGHT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        cc.pin_single_thread_runtime()
    except cc.CCError as error:
        print(f"C_C_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    args = _parser().parse_args(argv)
    try:
        target, sidecar, digest = write_manifest(args.output)
    except Exception as error:
        print(f"C_C_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(
        f"C_C_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
