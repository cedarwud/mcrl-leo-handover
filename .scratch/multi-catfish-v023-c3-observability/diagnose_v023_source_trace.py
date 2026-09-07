#!/usr/bin/env python3
"""Reproduce one frozen V0.23 source shard while preserving its exception chain.

This is a diagnosis-only entrypoint.  It imports the frozen source server and
calls the same ``launch_source`` seam, but deliberately does not collapse the
underlying traceback into the generic fail-closed message used by production.
It writes only to a caller-supplied fresh output path.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys
import traceback


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE_SERVER = HERE / "run_v023_lcsrs_source_server.py"


def _load_source_server():
    spec = importlib.util.spec_from_file_location("v023_trace_source", SOURCE_SERVER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load source server: {SOURCE_SERVER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", type=int, default=2026121705)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = _load_source_server()
    manifest = HERE / "PREFLIGHT-MANIFEST.json"
    source_args = source._parser().parse_args(
        [
            "--world",
            str(args.world),
            "--tle-root",
            str(args.tle_root),
            "--prereg",
            str(args.prereg),
            "--manifest",
            str(manifest),
            "--manifest-digest",
            str(HERE / "PREFLIGHT-MANIFEST.sha256"),
            "--execution-addendum",
            str(
                REPO
                / "docs"
                / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
            ),
            "--placebo-key",
            "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1",
            "--placebo-key-sha256",
            "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825",
            "--lineage",
            "2026092101",
            "--source-family",
            "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1",
            "--preflight-sha256",
            hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "--output",
            str(args.output),
        ]
    )
    try:
        result = source.launch_source(source_args)
    except BaseException:
        traceback.print_exc()
        return 2
    print(f"TRACE_SOURCE_PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
