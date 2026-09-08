#!/usr/bin/env python3
"""Build the immutable E1 code-and-binding preflight manifest."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_existence_e1 as e1


def build_manifest() -> dict[str, object]:
    return {
        "schema": e1.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": e1.CLAIM_CEILING,
        **e1.validate_static_bindings(),
        "code_files": e1.expected_code_bindings(),
    }


def write_manifest(path: Path) -> tuple[Path, Path, str]:
    target = Path(path)
    sidecar = target.with_suffix(".sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise e1.E1Error("refusing to overwrite preflight manifest or digest sidecar")
    digest = e1._write_once(target, build_manifest())
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    if (
        sidecar.read_text(encoding="ascii").split() != [digest, target.name]
        or sidecar.stat().st_mode & 0o777 != 0o444
        or e1.file_sha256(target) != digest
    ):
        raise e1.E1Error("preflight publication failed immutable readback")
    return target, sidecar, digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=e1.DEFAULT_PREFLIGHT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        target, sidecar, digest = write_manifest(args.output)
    except Exception as error:
        print(f"E1_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"E1_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
