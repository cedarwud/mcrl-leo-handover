#!/usr/bin/env python3
"""Build the write-once F1 preflight manifest for later server authority."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_contingency_f1 as f1


def build_manifest() -> dict[str, object]:
    static = f1.validate_static_bindings()
    return {
        "schema": f1.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": f1.CLAIM_CEILING,
        **static,
        "code_files": f1.expected_code_bindings(),
    }


def write_manifest(path: Path) -> tuple[Path, Path, str]:
    target = Path(path)
    payload = build_manifest()
    digest = f1._write_once(target, payload)
    sidecar = target.with_suffix(".sha256")
    if sidecar.exists() or sidecar.is_symlink():
        raise f1.F1Error(f"refusing to overwrite preflight digest sidecar: {sidecar}")
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    return target, sidecar, digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=f1.DEFAULT_PREFLIGHT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        target, sidecar, digest = write_manifest(args.output)
    except Exception as error:
        print(f"F1_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"F1_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
