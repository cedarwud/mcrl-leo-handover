#!/usr/bin/env python3
"""Build the immutable F2 launch-authority preflight manifest."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_contingency_f2 as f2


def build_manifest() -> dict[str, object]:
    return {
        "schema": f2.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": f2.CLAIM_CEILING,
        **f2.validate_static_bindings(),
        "code_files": f2.expected_code_bindings(),
    }


def write_manifest(path: Path) -> tuple[Path, Path, str]:
    target = Path(path)
    digest = f2._write_once(target, build_manifest())
    sidecar = target.with_suffix(".sha256")
    if sidecar.exists() or sidecar.is_symlink():
        raise f2.F2Error(f"refusing to overwrite preflight digest sidecar: {sidecar}")
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    return target, sidecar, digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=f2.DEFAULT_PREFLIGHT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        target, sidecar, digest = write_manifest(args.output)
    except Exception as error:
        print(f"F2_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"F2_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
