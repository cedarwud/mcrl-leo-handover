#!/usr/bin/env python3
"""Build the immutable preflight manifest for C3-S diagnostic arms."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3s_diagnostic_arms as runner


def build_manifest() -> dict[str, object]:
    """Derive every binding from the current checkout; accept no scientific knobs."""

    return {
        "schema": runner.PREFLIGHT_SCHEMA, "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": runner.CLAIM_CEILING, **runner.static_bindings(),
        "purpose": "C3S_PLACEBO_AND_HOSTILE_BASELINE_DIAGNOSTICS",
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }


def write_manifest(path: Path) -> tuple[Path, Path, str]:
    return runner.donor.write_once_with_sidecar(path, build_manifest())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=runner.DEFAULT_PREFLIGHT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        runner.donor.pin_single_thread_runtime()
        target, sidecar, digest = write_manifest(args.output)
    except Exception as error:
        print(f"C3S_DIAGNOSTIC_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_DIAGNOSTIC_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
