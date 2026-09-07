#!/usr/bin/env python3
"""Fit tiny P0/B2 Q2 candidates and run fresh matched FULL/DROP screens.

This runner is for rapid falsification only.  It consumes development source
JSON from ``run_v07_c2_fast_iteration.py``, applies exactly 100 deterministic
Q2-only full-batch updates, and evaluates fresh development seeds under the
same keyed physical field.  It never opens TEST and cannot establish paper
efficacy.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch  # noqa: E402
from mcrl.algorithms.ee_axis_v07_c2_fast_q2 import FreshQ2  # noqa: E402
from mcrl.runtime.ee_axis_v07_c2_d2 import (  # noqa: E402
    D2_DEFAULT_KAPPA_BITS,
    D2_INTERVAL_S,
)
from mcrl.runtime.ee_axis_v07_c2_state import (  # noqa: E402
    V07_C2_Q2_STATE_DIM,
)


CLAIM_CEILING = "DEVELOPMENT_100_UPDATE_FRESH_SCREEN_ONLY__NOT_EFFICACY"
LINEAGES = ("q13-a", "q13-b", "q13-c")
TRAIN_SEEDS = {
    "q13-a": 2026104401,
    "q13-b": 2026104402,
    "q13-c": 2026104403,
}
EVALUATION_SEEDS = (2026104301, 2026104302)

DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_PREREG = REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_MAIN = REPO / "artifacts/training-2026-08-25-rerun01/main"
DEFAULT_GATE = REPO / "artifacts/multi-catfish-v04-c3-learnability-20260901-r2"
DEFAULT_Q13_SOURCE = REPO / "artifacts/multi-catfish-v04-c3-source-20260901-r2"
DEFAULT_V03 = REPO / "artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"


class FastTrainEvalError(RuntimeError):
    """The development-only fit/evaluation cannot be compared safely."""


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FastTrainEvalError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_source(path: Path, *, lineage: str) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FastTrainEvalError(f"cannot read source {path}") from error
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "COMPLETE"
        or payload.get("lineage") != lineage
        or payload.get("training") is not False
        or payload.get("heldout_evaluation") is not False
    ):
        raise FastTrainEvalError(f"source for {lineage} is incomplete or stale")
    return payload


def _float32_state(values: object) -> np.ndarray:
    if not isinstance(values, list) or len(values) != V07_C2_Q2_STATE_DIM:
        raise FastTrainEvalError("source state must contain 228 hexadecimal values")
    try:
        state = np.asarray([float.fromhex(value) for value in values], dtype=np.float32)
    except (TypeError, ValueError, OverflowError) as error:
        raise FastTrainEvalError("source state contains malformed hexadecimal values") from error
    if not np.all(np.isfinite(state)):
        raise FastTrainEvalError("source state is non-finite")
    return state


def _batch(source: Mapping[str, object], *, target_name: str) -> EEAxisPairBatch:
    anchors = source.get("anchors")
    if not isinstance(anchors, list) or len(anchors) < 2:
        raise FastTrainEvalError("rapid fit requires at least two source anchors")
    target_field = {
        "p0": "p0_surplus_bits",
        "b2-proxy": "b2_proxy_surplus_bits",
    }[target_name]
    states: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    references: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise FastTrainEvalError("source anchor is malformed")
        state = _float32_state(anchor.get("q2_state_float32_hex"))
        mask = np.asarray(anchor.get("action_mask"))
        reference = anchor.get("reference_action")
        rows = anchor.get("rows")
        if (
            mask.shape != (28,)
            or mask.dtype != np.bool_
            or type(reference) is not int
            or not bool(mask[reference])
            or not isinstance(rows, list)
        ):
            raise FastTrainEvalError("source anchor mask/reference is malformed")
        for row in rows:
            if not isinstance(row, dict) or type(row.get("opening_action")) is not int:
                raise FastTrainEvalError("source target row is malformed")
            candidate = int(row["opening_action"])
            if candidate == reference:
                continue
            value = row.get(target_field)
            if isinstance(value, bool):
                raise FastTrainEvalError("source target is not numeric")
            try:
                target = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise FastTrainEvalError("source target is not numeric") from error
            if not np.isfinite(target):
                raise FastTrainEvalError("source target is non-finite")
            states.append(state.copy())
            masks.append(mask.copy())
            references.append(reference)
            candidates.append(candidate)
            targets.append(target)
    if len(states) < 2:
        raise FastTrainEvalError("rapid fit requires at least two non-reference rows")
    batch = EEAxisPairBatch(
        states=np.asarray(states, dtype=np.float32),
        reference_actions=np.asarray(references, dtype=np.int64),
        candidate_actions=np.asarray(candidates, dtype=np.int64),
        target_surplus_bits=np.asarray(targets, dtype=np.float64),
        action_masks=np.asarray(masks, dtype=np.bool_),
    )
    batch.validate(state_dim=V07_C2_Q2_STATE_DIM, action_dim=28)
    return batch


def _evaluate_arm(
    *,
    live_v07: Any,
    runtime: Any,
    hybrid: Any,
    fresh_q2: FreshQ2 | None,
    field: Any,
    evaluation_seed: int,
    steps: int,
    q2_user_scope: str,
) -> dict[str, object]:
    wrapped = runtime.make_environment(runtime.archive, users=int(runtime.users))
    runtime.bind_field(wrapped, field)
    env_rng, mobility_rng, *_ = runtime.evaluation_rngs(evaluation_seed)
    _states, _masks, observation = wrapped.reset(env_rng, mobility_rng)
    total_bits = 0.0
    total_energy_j = 0.0
    served_user_steps = 0
    actions_trace: list[list[int]] = []
    completed = 0
    for _ in range(steps):
        decision, _q2_state = live_v07._decision(
            hybrid,
            fresh_q2,
            wrapped,
            observation,
            interval_s=D2_INTERVAL_S,
            kappa_bits=D2_DEFAULT_KAPPA_BITS,
            q2_user_scope=q2_user_scope,
        )
        actions = np.asarray(decision.actions, dtype=np.int64)
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        if not np.all(np.isfinite(rates)) or np.any(rates < 0.0) or not np.isfinite(power) or power <= 0.0:
            raise FastTrainEvalError("fresh evaluation produced invalid rate/power")
        total_bits += float(np.sum(rates)) * D2_INTERVAL_S
        total_energy_j += power * D2_INTERVAL_S
        served_user_steps += int(np.count_nonzero(outcome.resolution.served))
        actions_trace.append([int(value) for value in actions.tolist()])
        completed += 1
        if bool(result.done):
            break
        observation = outcome.observation
    if completed < 1 or total_energy_j <= 0.0:
        raise FastTrainEvalError("fresh evaluation produced no complete step")
    return {
        "steps": completed,
        "total_bits": total_bits,
        "total_energy_j": total_energy_j,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy_j,
        "served_user_steps": served_user_steps,
        "actions": actions_trace,
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    evaluation_seeds = tuple(
        EVALUATION_SEEDS if args.evaluation_seed is None else args.evaluation_seed
    )
    if (
        not evaluation_seeds
        or any(type(seed) is not int or seed < 0 for seed in evaluation_seeds)
        or len(set(evaluation_seeds)) != len(evaluation_seeds)
    ):
        raise FastTrainEvalError("fresh development evaluation seeds must be unique integers")
    sources: dict[str, Mapping[str, object]] = {}
    source_paths: dict[str, str] = {}
    for item in args.source:
        try:
            lineage, raw_path = item.split("=", 1)
        except ValueError as error:
            raise FastTrainEvalError("--source must be LINEAGE=PATH") from error
        if lineage not in LINEAGES or lineage in sources:
            raise FastTrainEvalError("--source lineages must be unique q13-a/b/c")
        path = Path(raw_path)
        sources[lineage] = _read_source(path, lineage=lineage)
        source_paths[lineage] = str(path.resolve())
    if set(sources) != set(LINEAGES):
        raise FastTrainEvalError("exactly one source is required for every lineage")

    trainers: dict[str, FreshQ2] = {}
    training: dict[str, object] = {}
    for lineage in LINEAGES:
        batch = _batch(sources[lineage], target_name=args.target)
        trainer = FreshQ2(train_seed=TRAIN_SEEDS[lineage])
        training[lineage] = trainer.fit(batch, updates=100)
        trainers[lineage] = trainer

    runner_v07 = _load("v07_fast_eval_authority", HERE / "run_v07_c2_d2.py")
    live_v06, runner_v06, live_v07, simulator_manifest_sha256 = runner_v07._modules()
    started = time.monotonic()
    evaluations: list[dict[str, object]] = []
    with live_v06.authenticated_runtime(
        tle_root=args.tle_root,
        prereg_path=args.prereg,
        main_dir=args.main_dir,
        gate_dir=args.gate_dir,
        source_dir=args.q13_source_dir,
        v03_root=args.v03_root,
    ) as runtime:
        for lineage in LINEAGES:
            hybrid = runtime.hybrids[lineage]
            for evaluation_seed in evaluation_seeds:
                field = runner_v06._physical_world_field(
                    checkpoint_sha256=runtime.checkpoint_sha256,
                    source_manifest_sha256=simulator_manifest_sha256,
                    simulator_prereg_file_sha256=runtime.prereg_file_sha256,
                    source_seed=evaluation_seed,
                )
                drop = _evaluate_arm(
                    live_v07=live_v07,
                    runtime=runtime,
                    hybrid=hybrid,
                    fresh_q2=None,
                    field=field,
                    evaluation_seed=evaluation_seed,
                    steps=args.steps,
                    q2_user_scope=args.q2_user_scope,
                )
                full = _evaluate_arm(
                    live_v07=live_v07,
                    runtime=runtime,
                    hybrid=hybrid,
                    fresh_q2=trainers[lineage],
                    field=field,
                    evaluation_seed=evaluation_seed,
                    steps=args.steps,
                    q2_user_scope=args.q2_user_scope,
                )
                drop_ee = float(drop["ratio_of_sums_ee_bits_per_j"])
                full_ee = float(full["ratio_of_sums_ee_bits_per_j"])
                drop_actions = np.asarray(drop["actions"], dtype=np.int64)
                full_actions = np.asarray(full["actions"], dtype=np.int64)
                evaluations.append(
                    {
                        "lineage": lineage,
                        "evaluation_seed": evaluation_seed,
                        "target": args.target,
                        "q2_user_scope": args.q2_user_scope,
                        "drop_c2": drop,
                        "full": full,
                        "ee_improvement_fraction": full_ee / drop_ee - 1.0,
                        "action_flip_count": int(
                            np.count_nonzero(full_actions != drop_actions)
                        ),
                        "service_delta_user_steps": int(
                            full["served_user_steps"] - drop["served_user_steps"]
                        ),
                    }
                )
                print(
                    json.dumps(
                        {
                            "status": "FRESH_CELL_COMPLETE",
                            "lineage": lineage,
                            "evaluation_seed": evaluation_seed,
                            "ee_improvement_fraction": evaluations[-1][
                                "ee_improvement_fraction"
                            ],
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )

    improvements = np.asarray(
        [row["ee_improvement_fraction"] for row in evaluations], dtype=np.float64
    )
    payload: dict[str, object] = {
        "schema": "multi-catfish-mcrl-v07-c2-fast-train-eval-v1",
        "claim_ceiling": CLAIM_CEILING,
        "target": args.target,
        "q2_user_scope": args.q2_user_scope,
        "source_paths": source_paths,
        "training": training,
        "evaluation_seeds": list(evaluation_seeds),
        "evaluation_steps_cap": args.steps,
        "evaluations": evaluations,
        "summary": {
            "cells": int(improvements.size),
            "positive_cells": int(np.count_nonzero(improvements > 0.0)),
            "negative_cells": int(np.count_nonzero(improvements < 0.0)),
            "zero_cells": int(np.count_nonzero(improvements == 0.0)),
            "mean_improvement_fraction": float(np.mean(improvements)),
            "median_improvement_fraction": float(np.median(improvements)),
            "minimum_improvement_fraction": float(np.min(improvements)),
            "maximum_improvement_fraction": float(np.max(improvements)),
        },
        "elapsed_evaluation_wall_seconds": time.monotonic() - started,
        "test_split_opened": False,
        "formal_training": False,
        "efficacy_established": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--target", choices=("p0", "b2-proxy"), default="p0")
    parser.add_argument(
        "--q2-user-scope",
        choices=("all", "motion-one"),
        default="all",
        help="development deployment support for the fresh Q2",
    )
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument(
        "--evaluation-seed",
        action="append",
        type=int,
        default=None,
        help="repeatable fresh development seed; defaults to the two fixed smoke seeds",
    )
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--main-dir", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--q13-source-dir", type=Path, default=DEFAULT_Q13_SOURCE)
    parser.add_argument("--v03-root", type=Path, default=DEFAULT_V03)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if type(args.steps) is not int or not 1 <= args.steps <= 10:
        raise FastTrainEvalError("--steps must be in [1,10]")
    result = run(args)
    print(
        json.dumps(
            {
                "status": "FAST_TRAIN_EVAL_COMPLETE",
                "target": result["target"],
                "summary": result["summary"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
