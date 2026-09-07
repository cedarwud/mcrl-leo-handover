#!/usr/bin/env python3
"""Bounded, read-only repriced OPS-3 C2 generation benchmark for V0.23.

The benchmark imports the exact frozen target generator and exercises only its
sealed TRAIN C2 replay seam.  It deliberately has no ``--output`` argument,
never calls ``generate_targets``/``_write_outputs``, and keeps the temporary
archive/cache under a disposable ``TemporaryDirectory``.  The JSON summary is
printed to stdout; no receipt, dataset, target root, or persistent log is
created.

The default probe is one C2 opportunity from the earliest common TRAIN
world/step cohort, including late terminally-truncated anchors, using the same
100-user runtime as the real target-generation command. ``--anchor-count``
may be 1, 2, or 4. Each unit has a strict sub-10-minute deadline (default 9
minutes); a timeout is a failed-closed benchmark, not a partial runtime
estimate.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, replace
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import sys
import tempfile
import time
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence


# Do not leave import bytecode in the checkout while probing a frozen server
# tree.  The target generator itself remains the only source of runtime logic.
sys.dont_write_bytecode = True


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FROZEN_GENERATOR_PATH = HERE / "generate_v023_c1c2_targets.py"
LAUNCH_MANIFEST_PATH = (
    REPO / ".scratch" / "multi-catfish-v023-c1c2-target-generation-launch" / "CODE-MANIFEST.json"
)
SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-benchmark-v1"
CLAIM_CEILING = (
    "TRAIN_C2_PHYSICAL_TARGET_GENERATION_BENCHMARK_ONLY_NO_LEARNER_"
    "NO_REPLAY_WRITE_NO_EPISODE_TRAINING_NO_TEST"
)
TRAIN = "TRAIN"
USERS = 100
ANCHOR_COUNTS = (1, 2, 4)
DEFAULT_ANCHOR_COUNT = 1
DEFAULT_MAX_STEP = 9
DEFAULT_TIMEOUT_S = 540.0
MAX_TIMEOUT_S = 600.0


class BenchmarkError(RuntimeError):
    """A bounded benchmark cannot make a safe, typed measurement."""


class BenchmarkTimeout(BenchmarkError):
    """One benchmark unit exceeded its strict wall-time deadline."""


def _load_frozen_generator() -> ModuleType:
    """Import the exact production generator by path, without running it."""

    if FROZEN_GENERATOR_PATH.is_symlink() or not FROZEN_GENERATOR_PATH.is_file():
        raise BenchmarkError(
            f"frozen target generator is missing or symlinked: {FROZEN_GENERATOR_PATH}"
        )
    spec = importlib.util.spec_from_file_location(
        "mcrl_v023_frozen_target_generator_benchmark",
        FROZEN_GENERATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise BenchmarkError(f"cannot import frozen target generator: {FROZEN_GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(spec.name, None)
        raise BenchmarkError("frozen target generator import failed") from error
    return module


GENERATOR = _load_frozen_generator()


def _generator_digest() -> str:
    """Return the imported generator's current byte digest for the receipt."""

    return GENERATOR._sha256_file(FROZEN_GENERATOR_PATH)


def _verify_generator_manifest_binding() -> str:
    """Require the launch manifest, when present, to bind this exact file."""

    digest = _generator_digest()
    if LAUNCH_MANIFEST_PATH.is_symlink() or not LAUNCH_MANIFEST_PATH.is_file():
        raise BenchmarkError(f"target-generation launch manifest is missing: {LAUNCH_MANIFEST_PATH}")
    try:
        payload = json.loads(LAUNCH_MANIFEST_PATH.read_text(encoding="ascii"))
        bindings = payload["bindings"]
        expected = next(
            row["sha256"] for row in bindings if row["role"] == "target_generator"
        )
    except (KeyError, StopIteration, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise BenchmarkError("target-generation launch manifest is malformed") from error
    if expected != digest:
        raise BenchmarkError(
            "target generator digest disagrees with launch manifest: "
            f"expected={expected} actual={digest}"
        )
    return digest


@dataclass(frozen=True)
class BenchmarkCohort:
    """One same-world/same-step cohort selected independently per mode."""

    world: int
    step: int
    rows_by_mode: Mapping[str, tuple[Any, ...]]

    @property
    def modes(self) -> tuple[str, ...]:
        return tuple(sorted(self.rows_by_mode))

    def rows(self, mode: str) -> tuple[Any, ...]:
        try:
            return self.rows_by_mode[str(mode)]
        except KeyError as error:
            raise BenchmarkError(f"benchmark cohort has no {mode} rows") from error


@contextmanager
def _deadline(label: str, timeout_s: float) -> Iterable[None]:
    """Raise after ``timeout_s`` seconds on Ubuntu without killing a process."""

    if timeout_s <= 0.0 or timeout_s >= MAX_TIMEOUT_S:
        raise BenchmarkError(
            f"{label} timeout must be >0 and strictly below {MAX_TIMEOUT_S:g}s"
        )
    if not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"):
        raise BenchmarkError("strict benchmark deadline requires POSIX SIGALRM")

    def _alarm(_signum: int, _frame: Any) -> None:
        raise BenchmarkTimeout(
            f"{label} exceeded {timeout_s:.1f}s deadline; benchmark stopped"
        )

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, float(timeout_s))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer != (0.0, 0.0):
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


def _timed(
    label: str,
    callback: Callable[[], Any],
    *,
    timeout_s: float,
) -> tuple[Any, float]:
    started = time.perf_counter()
    with _deadline(label, timeout_s):
        value = callback()
    return value, time.perf_counter() - started


def _row_sort_key(row: Any) -> tuple[Any, ...]:
    key = tuple(int(value) for value in row.candidate_physical_key)
    return (
        str(row.anchor_sha256),
        int(row.step_index),
        int(row.focal_user),
        key,
        int(row.candidate_action),
    )


def _row_world_step(sealed: Any, row: Any) -> tuple[int, int]:
    key = (str(row.anchor_sha256), int(row.focal_user))
    try:
        authenticated = sealed.c2_anchor_by_key[key]
    except KeyError as error:
        raise BenchmarkError(
            f"C2 row has no authenticated anchor binding: {key}"
        ) from error
    world = int(authenticated.world_id)
    source_seed = int(authenticated.source_seed)
    if world != source_seed:
        raise BenchmarkError(
            f"C2 anchor world/source seed disagree: world={world} seed={source_seed}"
        )
    anchor_step = int(authenticated.anchor.step_index)
    row_step = int(row.step_index)
    if anchor_step != row_step:
        raise BenchmarkError(
            f"C2 row/anchor step disagree: row={row_step} anchor={anchor_step}"
        )
    return world, row_step


def _cohort_rows(
    sealed: Any,
    selection: Any,
    *,
    max_step: int,
) -> dict[tuple[int, int], tuple[Any, ...]]:
    """Group route rows into small same-world/same-step one-row-per-anchor cohorts."""

    groups: dict[tuple[int, int], dict[str, list[Any]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in tuple(selection.opportunities):
        world, step = _row_world_step(sealed, row)
        if step > max_step:
            continue
        groups[(world, step)][str(row.anchor_sha256)].append(row)

    result: dict[tuple[int, int], tuple[Any, ...]] = {}
    for cohort_key, by_anchor in sorted(groups.items()):
        chosen: list[Any] = []
        # One physical opportunity per anchor makes ``--anchor-count`` an
        # unambiguous bounded unit even if a neutral universe exposes several
        # legal candidates for one anchor.
        for anchor_sha256 in sorted(by_anchor):
            chosen.append(sorted(by_anchor[anchor_sha256], key=_row_sort_key)[0])
        result[cohort_key] = tuple(chosen)
    return result


def choose_cohort(
    sealed: Any,
    selections: Mapping[str, Any],
    *,
    modes: Sequence[str],
    anchor_count: int,
    max_step: int,
) -> BenchmarkCohort:
    """Pick the earliest cohort that has ``anchor_count`` anchors per mode."""

    if anchor_count not in ANCHOR_COUNTS:
        raise BenchmarkError(
            f"anchor_count must be one of {ANCHOR_COUNTS}, got {anchor_count}"
        )
    if type(max_step) is not int or max_step < 0:
        raise BenchmarkError("max_step must be a nonnegative exact integer")
    mode_values = tuple(str(mode) for mode in modes)
    if not mode_values or len(set(mode_values)) != len(mode_values):
        raise BenchmarkError("benchmark modes must be nonempty and unique")
    if any(mode not in ("informed", "neutral") for mode in mode_values):
        raise BenchmarkError("benchmark modes must be informed and/or neutral")

    grouped = {
        mode: _cohort_rows(sealed, selections[mode], max_step=max_step)
        for mode in mode_values
    }
    common_keys = set.intersection(*(set(rows) for rows in grouped.values()))
    for world, step in sorted(common_keys):
        rows_by_mode: dict[str, tuple[Any, ...]] = {}
        if all(len(grouped[mode][(world, step)]) >= anchor_count for mode in mode_values):
            for mode in mode_values:
                rows_by_mode[mode] = tuple(
                    grouped[mode][(world, step)][:anchor_count]
                )
            return BenchmarkCohort(world=world, step=step, rows_by_mode=rows_by_mode)

    available = {
        mode: {
            f"{world}:{step}": len(rows)
            for (world, step), rows in sorted(grouped[mode].items())
        }
        for mode in mode_values
    }
    raise BenchmarkError(
        "no common C2 cohort satisfies the bounded selection: "
        f"anchor_count={anchor_count} max_step={max_step} available={available}"
    )


def choose_full_step_cohort(
    sealed: Any,
    selections: Mapping[str, Any],
    *,
    modes: Sequence[str],
    max_step: int,
) -> BenchmarkCohort:
    """Choose the smallest complete world/step schedule shared by all modes."""

    mode_values = tuple(str(mode) for mode in modes)
    grouped = {
        mode: _cohort_rows(sealed, selections[mode], max_step=max_step)
        for mode in mode_values
    }
    common_keys = set.intersection(*(set(rows) for rows in grouped.values()))
    if not common_keys:
        raise BenchmarkError("no complete world/step cohort is available")
    world, step = min(
        common_keys,
        key=lambda key: (
            max(len(grouped[mode][key]) for mode in mode_values),
            sum(len(grouped[mode][key]) for mode in mode_values),
            key,
        ),
    )
    return BenchmarkCohort(
        world=world,
        step=step,
        rows_by_mode={mode: grouped[mode][(world, step)] for mode in mode_values},
    )


def _subset_selection(selection: Any, rows: Sequence[Any]) -> Any:
    """Return a typed copy whose selected rows are bounded to this probe."""

    subset = replace(selection, opportunities=tuple(rows))
    # Neutral C2 selections carry the selected budget as a field; the informed
    # materialization exposes budget as a property and needs no replacement.
    if hasattr(subset, "informed_budget"):
        subset = replace(subset, informed_budget=len(tuple(rows)))
    verifier = getattr(subset, "verify", None)
    if not callable(verifier):
        raise BenchmarkError("C2 selection has no typed verifier")
    verifier()
    return subset


def _sealed_file_snapshot(sealed: Any) -> dict[str, str]:
    names = (
        "c1-informed.json",
        "c1-neutral.json",
        "c2-informed.json",
        "c2-neutral.json",
        "receipt.json",
        "MANIFEST.sha256",
    )
    paths = [Path(sealed.capture_path)] + [
        Path(sealed.materialization_dir) / name for name in names
    ]
    return {str(path): GENERATOR._sha256_file(path) for path in paths}


def _digest_guard(before: Mapping[str, str], after: Mapping[str, str]) -> None:
    if dict(before) != dict(after):
        changed = sorted(
            path
            for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        )
        raise BenchmarkError(f"sealed TRAIN inputs changed during benchmark: {changed}")


def _float_seconds(value: float) -> float:
    return round(float(value), 6)


def _mode_summary(
    *,
    mode: str,
    rows: Sequence[Any],
    elapsed_s: float,
    full_rows: int,
    dataset: Mapping[str, object],
    bindings: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    count = len(tuple(rows))
    if count <= 0:
        raise BenchmarkError(f"{mode} benchmark selection is empty")
    rows_payload = dataset.get("rows")
    if not isinstance(rows_payload, list) or len(rows_payload) != count or len(tuple(bindings)) != count:
        raise BenchmarkError(f"{mode} benchmark did not materialize exactly its bounded rows")
    return {
        "selected_rows": count,
        "selected_unique_anchors": len({str(row.anchor_sha256) for row in rows}),
        "elapsed_s": _float_seconds(elapsed_s),
        "seconds_per_selected_row": _float_seconds(elapsed_s / count),
        "full_route_rows": int(full_rows),
        "linear_c2_route_estimate_s": _float_seconds(
            elapsed_s * full_rows / count
        ),
        "dataset_rows_verified_in_memory": len(rows_payload),
        "bindings_verified_in_memory": len(tuple(bindings)),
    }


def run_benchmark(
    *,
    capture_path: Path,
    materialization_dir: Path,
    tle_root: Path,
    prereg: Path,
    manifest: Path,
    manifest_digest: Path,
    execution_addendum: Path,
    modes: Sequence[str] = ("informed",),
    anchor_count: int = DEFAULT_ANCHOR_COUNT,
    max_step: int = DEFAULT_MAX_STEP,
    full_step_cohort: bool = False,
    users: int = USERS,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, object]:
    """Run one or more bounded in-memory C2 probes and return stdout data."""

    if type(users) is not int or users != USERS:
        raise BenchmarkError(f"benchmark runtime is fixed at exactly {USERS} users")
    if timeout_s <= 0.0 or timeout_s >= MAX_TIMEOUT_S:
        raise BenchmarkError(
            f"timeout_s must be strictly between 0 and {MAX_TIMEOUT_S:g} seconds"
        )
    mode_values = tuple(str(mode) for mode in modes)
    if not mode_values or len(set(mode_values)) != len(mode_values):
        raise BenchmarkError("modes must be nonempty and unique")
    if any(mode not in ("informed", "neutral") for mode in mode_values):
        raise BenchmarkError("modes must be informed and/or neutral")

    load_started = time.perf_counter()
    generator_sha256 = _verify_generator_manifest_binding()
    sealed = GENERATOR.load_sealed_inputs(
        Path(capture_path), Path(materialization_dir)
    )
    load_elapsed_s = time.perf_counter() - load_started
    if getattr(sealed.bundle, "split", TRAIN) not in (TRAIN, None):
        raise BenchmarkError("sealed inputs are not TRAIN-only")
    selections = sealed.c2_routes
    cohort = (
        choose_full_step_cohort(
            sealed, selections, modes=mode_values, max_step=max_step
        )
        if full_step_cohort
        else choose_cohort(
            sealed,
            selections,
            modes=mode_values,
            anchor_count=anchor_count,
            max_step=max_step,
        )
    )
    sealed_before = _sealed_file_snapshot(sealed)

    with tempfile.TemporaryDirectory(prefix="mcrl-v023-c1c2-benchmark-") as temporary_name:
        setup_started = time.perf_counter()
        with _deadline("100-user runtime setup", timeout_s):
            context = GENERATOR._prepare_runtime(
                sealed,
                tle_root=Path(tle_root),
                prereg=Path(prereg),
                manifest=Path(manifest),
                manifest_digest=Path(manifest_digest),
                execution_addendum=Path(execution_addendum),
                users=USERS,
                temporary=Path(temporary_name),
            )
        setup_elapsed_s = time.perf_counter() - setup_started

        network_before = str(context.modules.source._model_digest(
            context.q1, context.q2,
            context.auth["q1_receipt"], context.auth["q2_receipt"],
        ))
        mode_results: dict[str, object] = {}
        for mode in mode_values:
            rows = cohort.rows(mode)
            subset = _subset_selection(selections[mode], rows)
            (dataset, bindings), elapsed_s = _timed(
                f"C2 {mode} cohort world={cohort.world} step={cohort.step}",
                lambda subset=subset, mode=mode: GENERATOR._generate_c2_world(
                    context,
                    sealed,
                    subset,
                    world=cohort.world,
                    mode=mode,
                ),
                timeout_s=timeout_s,
            )
            mode_results[mode] = _mode_summary(
                mode=mode,
                rows=rows,
                elapsed_s=elapsed_s,
                full_rows=len(tuple(selections[mode].opportunities)),
                dataset=dataset,
                bindings=bindings,
            )

        network_after = str(context.modules.source._model_digest(
            context.q1, context.q2,
            context.auth["q1_receipt"], context.auth["q2_receipt"],
        ))
        if network_after != network_before:
            raise BenchmarkError("benchmark changed the Main network")

    sealed_after = _sealed_file_snapshot(sealed)
    _digest_guard(sealed_before, sealed_after)
    total_elapsed_s = load_elapsed_s + setup_elapsed_s + sum(
        float(result["elapsed_s"]) for result in mode_results.values()
    )
    estimated_mode_s = {
        mode: _float_seconds(
            setup_elapsed_s + float(result["linear_c2_route_estimate_s"])
        )
        for mode, result in mode_results.items()
    }
    return {
        "schema": SCHEMA,
        "status": "BENCHMARK_PASS",
        "claim_ceiling": CLAIM_CEILING,
        "scope": "C2 repriced OPS-3 selected-pair generation only; no C1 timing, learner, TEST, or efficacy claim",
        "inputs": {
            "frozen_generator_sha256": generator_sha256,
            "capture": str(Path(capture_path).resolve()),
            "materialization_dir": str(Path(materialization_dir).resolve()),
            "split": TRAIN,
            "users": USERS,
            "capture_sha256": sealed.capture_sha256,
            "materialization_manifest_sha256": sealed.materialization_manifest_sha256,
            "source_manifest_sha256": sealed.source_manifest_sha256,
            "checkpoint_sha256": sealed.checkpoint_sha256,
        },
        "selection": {
            "modes": list(mode_values),
            "anchor_count_requested": int(anchor_count),
            "full_step_cohort": bool(full_step_cohort),
            "max_step": int(max_step),
            "world": cohort.world,
            "step": cohort.step,
            "rows_by_mode": {
                mode: [
                    {
                        "anchor_sha256": str(row.anchor_sha256),
                        "focal_user": int(row.focal_user),
                        "candidate_physical_key": [
                            int(row.candidate_physical_key[0]),
                            int(row.candidate_physical_key[1]),
                        ],
                    }
                    for row in cohort.rows(mode)
                ]
                for mode in mode_values
            },
        },
        "timing": {
            "sealed_input_load_s": _float_seconds(load_elapsed_s),
            "runtime_setup_100_users_s": _float_seconds(setup_elapsed_s),
            "modes": mode_results,
            "benchmark_wall_s": _float_seconds(total_elapsed_s),
            "strict_unit_timeout_s": _float_seconds(timeout_s),
        },
        "linear_estimate": {
            "mode_total_s_including_one_setup": estimated_mode_s,
            "parallel_modes_wall_s_lower_bound": _float_seconds(
                max(estimated_mode_s.values())
            ),
            "method": "setup_s + selected_cohort_elapsed_s * full_route_rows / selected_rows",
            "caveat": "C2-only OPS-3 replay estimate; it excludes C1, controller merge/seal, and CPU contention between informed/neutral shards",
        },
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
    parser.add_argument(
        "--mode",
        choices=("informed", "neutral", "both"),
        default="informed",
        help="probe one route (default) or both routes sequentially",
    )
    parser.add_argument(
        "--anchor-count",
        type=int,
        choices=ANCHOR_COUNTS,
        default=DEFAULT_ANCHOR_COUNT,
        help="one-row-per-anchor bounded cohort size (default: 1)",
    )
    parser.add_argument(
        "--max-step",
        type=int,
        default=DEFAULT_MAX_STEP,
        help="highest allowed sealed C2 anchor step (default: 2)",
    )
    parser.add_argument(
        "--full-step-cohort",
        action="store_true",
        help="time the smallest complete same-world/same-step schedule",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=USERS,
        help="fixed at 100 to match production runtime",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help="strict per-unit/setup timeout, strictly below 600 seconds",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    modes = ("informed", "neutral") if args.mode == "both" else (args.mode,)
    try:
        result = run_benchmark(
            capture_path=args.capture,
            materialization_dir=args.materialization_dir,
            tle_root=args.tle_root,
            prereg=args.prereg,
            manifest=args.manifest,
            manifest_digest=args.manifest_digest,
            execution_addendum=args.execution_addendum,
            modes=modes,
            anchor_count=args.anchor_count,
            max_step=args.max_step,
            full_step_cohort=args.full_step_cohort,
            users=args.users,
            timeout_s=args.timeout_s,
        )
    except Exception as error:
        chain: list[str] = []
        current: BaseException | None = error
        while current is not None and len(chain) < 8:
            chain.append(f"{type(current).__name__}: {current}")
            current = current.__cause__ or current.__context__
        print(
            "V023_C1C2_TARGET_BENCHMARK_BLOCKED: " + " <- ".join(chain),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
