#!/usr/bin/env python3
"""Build the immutable C-A preflight after the contract and cap are sealed."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3_candidate_ca as ca


def build_manifest(*, profile_count_cap: int) -> dict[str, object]:
    return {
        "schema": ca.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": ca.CLAIM_CEILING,
        **ca.static_bindings(profile_count_cap),
        "code_files": ca.expected_code_bindings(),
    }


def write_manifest(
    path: Path, *, profile_count_cap: int
) -> tuple[Path, Path, str]:
    target = Path(path)
    if target.exists() or target.is_symlink() or Path(f"{target}.sha256").exists():
        raise ca.CAError("refusing to overwrite preflight manifest or sidecar")
    digest = ca.write_once(target, build_manifest(profile_count_cap=profile_count_cap))
    sidecar = ca._write_sidecar(target, digest)
    ca.validate_preflight_manifest(target, profile_count_cap=profile_count_cap)
    return target, sidecar, digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-count-cap", type=int, required=True)
    parser.add_argument("--output", type=Path, default=ca.DEFAULT_PREFLIGHT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        ca.pin_single_thread_runtime()
        args = _parser().parse_args(argv)
        target, sidecar, digest = write_manifest(
            args.output, profile_count_cap=args.profile_count_cap
        )
    except Exception as error:
        print(f"CA_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"CA_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
