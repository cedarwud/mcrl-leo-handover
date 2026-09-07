#!/usr/bin/env python3
"""Explicit Ubuntu-server entrypoint for one V0.23 learner fit shard.

This entrypoint is intentionally separate from the safe plan-only launcher.
It is not invoked by tests or by the local shell launcher.  A parent launch
contract must first authenticate the preflight and source-manifest hashes,
then run this command in an already prepared server environment.  It opens
only the requested TRAIN-development fit shard; TEST and episode training
remain closed by the runner and adapter validators.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"required server entrypoint module is missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load server entrypoint module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = _load("mcrl_v023_gate_runner_server", HERE / "run_v023_lcsrs_observability_gate.py")
ADAPTER = _load("mcrl_v023_fit_adapter_server", HERE / "v023_lcsrs_fit_adapter.py")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--held-out-world", type=int, choices=RUNNER.WORLDS, required=True)
    parser.add_argument("--student-seed", type=int, choices=RUNNER.STUDENT_SEEDS, required=True)
    parser.add_argument("--arm", choices=RUNNER.ARMS, required=True)
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--preflight-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)

    adapter = ADAPTER.V023LearnerAdapter(device=args.device)
    spec = RUNNER.FitShardSpec(
        held_out_world=args.held_out_world,
        student_seed=args.student_seed,
        arm=args.arm,
        source_directory=args.source_directory,
        output=args.output,
        source_manifest=args.source_manifest,
        preflight_manifest_sha256=args.preflight_sha256,
    )
    receipt = RUNNER.run_fit_stage(spec, adapter=adapter)
    print(f"FIT_PASS: {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
