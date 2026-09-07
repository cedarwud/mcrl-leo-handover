#!/usr/bin/env python3
"""Launch-ready R7 learner-fit worker.

The frozen launch manifest is authenticated before importing the learner
adapter or opening a source shard.  This process can fit only a declared
TRAIN-development LOO shard; TEST, episode-policy training, and efficacy
claims remain closed by the adapter and receipt validators.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from preflight_r7_balanced import MANIFEST, MANIFEST_SHA, PREREGISTRATION, REPO, validate_manifest


HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> ModuleType:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise RuntimeError(f"required launch module is missing or symlinked: {target}")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load launch module: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--held-out-world", type=int, required=True)
    parser.add_argument("--student-seed", type=int, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--preflight-sha256", required=True)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--manifest-digest", type=Path, default=MANIFEST_SHA)
    parser.add_argument("--prereg", type=Path, default=REPO / PREREGISTRATION)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    receipt = validate_manifest(
        args.manifest,
        manifest_digest_path=args.manifest_digest,
        repo=REPO,
        prereg_path=args.prereg,
    )
    if receipt["manifest_file_sha256"] != args.preflight_sha256:
        raise SystemExit("preflight digest disagrees with authenticated launch manifest")

    runner = _load("mcrl_v023_r7_gate_runner_fit_worker", HERE / "run_v023_lcsrs_observability_gate.py")
    adapter_module = _load("mcrl_v023_r7_fit_adapter_worker", HERE / "v023_lcsrs_fit_adapter.py")
    runner_worlds = tuple(getattr(runner, "WORLDS", ()))
    runner_seeds = tuple(getattr(runner, "STUDENT_SEEDS", ()))
    runner_arms = tuple(getattr(runner, "ARMS", ()))
    if args.held_out_world not in runner_worlds or args.student_seed not in runner_seeds or args.arm not in runner_arms:
        raise SystemExit("fit shard identity is outside frozen R7 schedule")
    adapter_type = getattr(adapter_module, "V023LearnerAdapter", None)
    spec_type = getattr(runner, "FitShardSpec", None)
    run_stage = getattr(runner, "run_fit_stage", None)
    if not callable(adapter_type) or not callable(spec_type) or not callable(run_stage):
        raise SystemExit("launch fit adapter seam is incomplete")
    adapter = adapter_type(device=args.device)
    spec = spec_type(
        held_out_world=args.held_out_world,
        student_seed=args.student_seed,
        arm=args.arm,
        source_directory=args.source_directory,
        output=args.output,
        source_manifest=args.source_manifest,
        preflight_manifest_sha256=args.preflight_sha256,
    )
    result = run_stage(spec, adapter=adapter)
    print(f"FIT_PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
