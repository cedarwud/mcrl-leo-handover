#!/usr/bin/env python3
"""Build the immutable C3S code-and-binding preflight manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import run_v023_c3s_screen as screen


def _binding(path: Path, *, field: str) -> dict[str, str]:
    target = screen._local(path, field=field)
    digest = screen.file_sha256(target)
    screen._validate_sealed(target, digest=digest, field=field)
    return {"path": str(target), "sha256": digest}


def build_manifest(
    *, evidence_manifest: Path, world_census: Path,
    freeze_timestamp_utc: str, reviewer: str,
) -> dict[str, object]:
    evidence = _binding(evidence_manifest, field="C3S evidence manifest")
    census = _binding(world_census, field="C3S world census")
    freeze = screen.validate_freeze_metadata({
        "timestamp_utc": freeze_timestamp_utc, "reviewer": reviewer,
    })
    screen.validate_evidence_manifest(evidence)
    screen.validate_world_census(census)
    return {
        "schema": screen.PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": screen.CLAIM_CEILING,
        **screen.validate_static_bindings(),
        "code_files": screen.expected_code_bindings(),
        "evidence_manifest": evidence,
        "world_census": census,
        "freeze": freeze,
    }


def write_manifest(
    path: Path, *, evidence_manifest: Path, world_census: Path,
    freeze_timestamp_utc: str, reviewer: str,
) -> tuple[Path, Path, str]:
    return screen.write_once_with_sidecar(path, build_manifest(
        evidence_manifest=evidence_manifest, world_census=world_census,
        freeze_timestamp_utc=freeze_timestamp_utc, reviewer=reviewer,
    ))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=screen.DEFAULT_PREFLIGHT)
    parser.add_argument("--evidence-manifest", type=Path, required=True)
    parser.add_argument("--world-census", type=Path, required=True)
    parser.add_argument("--freeze-timestamp-utc", required=True)
    parser.add_argument("--reviewer", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        screen.pin_single_thread_runtime()
        target, sidecar, digest = write_manifest(
            args.output, evidence_manifest=args.evidence_manifest,
            world_census=args.world_census,
            freeze_timestamp_utc=args.freeze_timestamp_utc,
            reviewer=args.reviewer,
        )
    except Exception as error:
        print(f"C3S_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"C3S_PREFLIGHT_PASS manifest={target} sidecar={sidecar} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
