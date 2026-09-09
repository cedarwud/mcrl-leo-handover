#!/usr/bin/env python3
"""Bounded, read-only timing probe for one complete V0.23 C1 sampling unit.

This companion to ``benchmark_v023_c1c2_targets.py`` measures the smallest
sealed C1 anchor/user unit for exactly one source mode.  An informed C1 unit
contains every ACRM physical alternative for the selected user, so the probe
does not invalidate the source contract merely to become faster.  It writes no
dataset, learner state, replay item, receipt, or persistent target output.
"""

from __future__ import annotations

from dataclasses import replace
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
from types import ModuleType
from typing import Any, Mapping, Sequence


sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
BENCHMARK_PATH = HERE / "benchmark_v023_c1c2_targets.py"
SCHEMA = "multi-catfish-mcrl-v023-c1-target-generation-benchmark-v1"
CLAIM_CEILING = (
    "TRAIN_C1_PHYSICAL_TARGET_GENERATION_BENCHMARK_ONLY_NO_LEARNER_"
    "NO_REPLAY_WRITE_NO_EPISODE_TRAINING_NO_TEST"
)


class C1BenchmarkError(RuntimeError):
    """The bounded C1 timing probe cannot be authenticated."""


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise C1BenchmarkError(f"cannot import benchmark module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


BENCH = _load_module("mcrl_v023_c1_timing_base", BENCHMARK_PATH)
GENERATOR = BENCH.GENERATOR


def _world_step(sealed: Any, row: Any) -> tuple[int, int]:
    try:
        record = sealed.c1_record_by_anchor[str(row.anchor_sha256)]
    except KeyError as error:
        raise C1BenchmarkError("C1 row has no sealed source record") from error
    return int(record.source_seed), int(row.step_index)


def choose_smallest_complete_unit(sealed: Any, selection: Any) -> tuple[int, int, tuple[Any, ...]]:
    """Return the cheapest complete anchor/user ACRM unit in one selection."""

    groups: dict[tuple[str, int], list[Any]] = {}
    for row in tuple(selection.opportunities):
        groups.setdefault((str(row.anchor_sha256), int(row.focal_user)), []).append(row)
    if not groups:
        raise C1BenchmarkError("sealed C1 selection is empty")

    candidates: list[tuple[int, int, int, str, int, tuple[Any, ...]]] = []
    for (anchor, focal), rows in groups.items():
        ordered = tuple(sorted(rows, key=BENCH._row_sort_key))
        world, step = _world_step(sealed, ordered[0])
        if any(_world_step(sealed, row) != (world, step) for row in ordered):
            raise C1BenchmarkError("one C1 anchor/user unit spans worlds or steps")
        candidates.append((len(ordered), step, world, anchor, focal, ordered))
    _count, step, world, _anchor, _focal, rows = min(candidates)
    return world, step, rows


def subset_complete_unit(selection: Any, rows: Sequence[Any]) -> Any:
    chosen = tuple(rows)
    if not chosen:
        raise C1BenchmarkError("C1 benchmark unit is empty")
    anchors = tuple(sorted({str(row.anchor_sha256) for row in chosen}))
    users = tuple(sorted({(str(row.anchor_sha256), int(row.focal_user)) for row in chosen}))
    subset = replace(
        selection,
        selected_anchor_sha256s=anchors,
        selected_focal_users=users,
        opportunities=chosen,
    )
    subset.verify()
    return subset


def _seconds(value: float) -> float:
    return round(float(value), 6)


def run_c1_benchmark(
    *,
    capture_path: Path,
    materialization_dir: Path,
    tle_root: Path,
    prereg: Path,
    manifest: Path,
    manifest_digest: Path,
    execution_addendum: Path,
    mode: str,
    timeout_s: float,
) -> Mapping[str, object]:
    if mode not in ("informed", "neutral"):
        raise C1BenchmarkError("mode must be informed or neutral")
    generator_sha256 = BENCH._verify_generator_manifest_binding()
    load_started = time.perf_counter()
    sealed = GENERATOR.load_sealed_inputs(capture_path, materialization_dir)
    load_s = time.perf_counter() - load_started
    if getattr(sealed.bundle, "split", BENCH.TRAIN) not in (BENCH.TRAIN, None):
        raise C1BenchmarkError("sealed inputs are not TRAIN-only")
    selection = sealed.c1_routes[mode]
    world, step, rows = choose_smallest_complete_unit(sealed, selection)
    subset = subset_complete_unit(selection, rows)
    sealed_before = BENCH._sealed_file_snapshot(sealed)

    with tempfile.TemporaryDirectory(prefix="mcrl-v023-c1-benchmark-") as temporary_name:
        setup_started = time.perf_counter()
        with BENCH._deadline("100-user runtime setup", timeout_s):
            context = GENERATOR._prepare_runtime(
                sealed,
                tle_root=tle_root,
                prereg=prereg,
                manifest=manifest,
                manifest_digest=manifest_digest,
                execution_addendum=execution_addendum,
                users=BENCH.USERS,
                temporary=Path(temporary_name),
            )
        setup_s = time.perf_counter() - setup_started
        snapshot, equal = GENERATOR._network_integrity_helpers(context.modules.temporal_smoke)
        network_before = snapshot(context.trainer)
        replay_before = len(context.trainer.replay) if hasattr(context.trainer, "replay") else None
        (dataset, bindings), elapsed_s = BENCH._timed(
            f"C1 {mode} complete unit world={world} step={step}",
            lambda: GENERATOR._generate_c1_world(
                context, sealed, subset, world=world
            ),
            timeout_s=timeout_s,
        )
        if len(dataset.rows) != len(rows) or len(bindings) != len(rows):
            raise C1BenchmarkError("C1 probe did not materialize its complete unit")
        if not equal(context.trainer, network_before):
            raise C1BenchmarkError("C1 probe changed the Main network")
        if replay_before is not None and len(context.trainer.replay) != replay_before:
            raise C1BenchmarkError("C1 probe changed the Main replay")

    BENCH._digest_guard(sealed_before, BENCH._sealed_file_snapshot(sealed))
    row_count = len(rows)
    route_rows = len(tuple(selection.opportunities))
    route_estimate_s = setup_s + elapsed_s * route_rows / row_count
    return {
        "schema": SCHEMA,
        "status": "BENCHMARK_PASS",
        "claim_ceiling": CLAIM_CEILING,
        "scope": "C1 physical target timing only; no C2, learner, episode training, TEST, or efficacy claim",
        "inputs": {
            "frozen_generator_sha256": generator_sha256,
            "split": BENCH.TRAIN,
            "users": BENCH.USERS,
            "capture_sha256": sealed.capture_sha256,
            "materialization_manifest_sha256": sealed.materialization_manifest_sha256,
            "checkpoint_sha256": sealed.checkpoint_sha256,
        },
        "selection": {
            "mode": mode,
            "world": world,
            "step": step,
            "complete_sampling_unit_rows": row_count,
            "full_route_rows": route_rows,
        },
        "timing": {
            "sealed_input_load_s": _seconds(load_s),
            "runtime_setup_100_users_s": _seconds(setup_s),
            "unit_elapsed_s": _seconds(elapsed_s),
            "seconds_per_selected_row": _seconds(elapsed_s / row_count),
            "linear_route_estimate_s_including_one_setup": _seconds(route_estimate_s),
            "benchmark_wall_s": _seconds(load_s + setup_s + elapsed_s),
            "strict_unit_timeout_s": _seconds(timeout_s),
        },
        "estimate_caveat": (
            "single smallest complete C1 unit; linear route estimate excludes per-world reset variation, "
            "controller merge/seal, and CPU contention"
        ),
        "guards": {
            "training_or_replay_write": False,
            "learner_update": False,
            "episode_training": False,
            "test_split_opened": False,
            "main_network_unchanged": True,
            "main_replay_unchanged": True,
            "sealed_train_inputs_unchanged": True,
            "persistent_target_output_created": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--materialization-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-digest", type=Path, required=True)
    parser.add_argument("--execution-addendum", type=Path, required=True)
    parser.add_argument("--mode", choices=("informed", "neutral"), required=True)
    parser.add_argument("--timeout-s", type=float, default=540.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_c1_benchmark(
            capture_path=args.capture,
            materialization_dir=args.materialization_dir,
            tle_root=args.tle_root,
            prereg=args.prereg,
            manifest=args.manifest,
            manifest_digest=args.manifest_digest,
            execution_addendum=args.execution_addendum,
            mode=args.mode,
            timeout_s=args.timeout_s,
        )
    except Exception as error:
        chain: list[str] = []
        current: BaseException | None = error
        while current is not None and len(chain) < 8:
            chain.append(f"{type(current).__name__}: {current}")
            current = current.__cause__ or current.__context__
        print("V023_C1_TARGET_BENCHMARK_BLOCKED: " + " <- ".join(chain), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
