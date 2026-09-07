#!/usr/bin/env python3
"""Build the immutable pre-outcome F3 code and design manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import f3_common as common


def build_manifest() -> dict[str, object]:
    return {
        "schema": common.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PRE_OUTCOME",
        "claim_ceiling": common.DESIGN_CLAIM_CEILING,
        **common.static_bindings(),
        "code_files": common.expected_code_bindings(),
    }


def write_manifest(path: Path) -> tuple[Path, Path, str]:
    target = Path(path)
    digest = common.write_once_json(target, build_manifest())
    sidecar = target.with_suffix(".sha256")
    common.write_once_bytes(sidecar, f"{digest}  {target.name}\n".encode("ascii"))
    return target, sidecar, digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=common.HERE / "F3-PREFLIGHT-MANIFEST.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        target, sidecar, digest = write_manifest(args.output)
    except Exception as error:
        print(f"F3_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"F3_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
