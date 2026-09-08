#!/usr/bin/env python3
"""Build the immutable C3S code-and-binding preflight manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3s_screen as screen


def build_manifest() -> dict[str, object]:
    return {
        "schema": screen.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": screen.CLAIM_CEILING,
        **screen.validate_static_bindings(),
        "code_files": screen.expected_code_bindings(),
    }


def write_manifest(path: Path) -> tuple[Path, Path, str]:
    return screen.write_once_with_sidecar(path, build_manifest())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=screen.DEFAULT_PREFLIGHT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        screen.pin_single_thread_runtime()
        target, sidecar, digest = write_manifest(args.output)
    except Exception as error:
        print(f"C3S_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
