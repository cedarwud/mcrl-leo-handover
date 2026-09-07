#!/usr/bin/env python3
"""Run the first matched M0/neutral/full/route-ablation screen for V0.3."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch" / "c2-v03"
for path in (HERE, C2_V03, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_c2_v03_deterministic_plumbing_probe as c2_probe  # noqa: E402
import run_c2_v03_real_backend_smoke as c2_backend_smoke  # noqa: E402
import run_v03_bounded_informed_pilot as informed_pilot  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairwiseTrainer  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_evaluation import evaluate_ee_axis_episode  # noqa: E402
from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_pilot_runner import EEAxisPilotRunSpec, run_pairwise_pilot  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import (  # noqa: E402
    EEAxisTemporalDataset,
    read_temporal_dataset,
)
from mcrl.runtime.ee_axis_training_schedule import EEAxisThreeRouteBatches  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-10ep-matched-ablation-v1"
CLAIM_CEILING = "TWO_SEED_TEN_EP_DIRECTIONAL_ABLATION_NOT_CHAPTER5_EFFICACY"
LEARNING_RATE = 0.001
TRAIN_SEED = 2026083111
# Fresh relative to the learning-rate screen; do not reuse the seeds that
# selected lr=0.001.
EVALUATION_SEEDS = (2026090201, 2026090202)


class MatchedAblationError(RuntimeError):
    """The matched bounded ablation could not close."""


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _m0_episode(
    trainer: Any,
    archive: Any,
    *,
    seed: int,
    checkpoint_sha256: str,
) -> dict[str, Any]:
    wrapped = loader._make_environment(archive, users=100)
    field = KeyedFadingField.from_components(
        "multi-catfish-mcrl-v03-ablation-paired-evaluation-v1",
        checkpoint_sha256,
        seed,
    )
    wrapped.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    interval_s = float(wrapped.environment.driver.config.ephemeris.time_step_s)
    total_bits = 0.0
    total_energy = 0.0
    served = 0
    steps = 0
    action_trace: list[list[int]] = []
    while True:
        actions, _physical = c2_backend_smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        actions = np.asarray(actions, dtype=np.int64)
        action_trace.append([int(value) for value in actions.tolist()])
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        system_rate = float(math.fsum(float(value) for value in rates))
        if (
            rates.shape != (100,)
            or not np.all(np.isfinite(rates))
            or np.any(rates < 0.0)
            or not math.isfinite(power)
            or power < 0.0
            or (power == 0.0 and system_rate > 0.0)
        ):
            raise MatchedAblationError("M0 evaluation produced malformed physics")
        total_bits += system_rate * interval_s
        total_energy += power * interval_s
        served += int(outcome.resolution.served_count)
        steps += 1
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = outcome.observation
    decisions = steps * 100
    return {
        "policy_label": "M0",
        "evaluation_seed": seed,
        "fading_field_sha256": field.root_digest,
        "steps": steps,
        "users": 100,
        "decision_count": decisions,
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy if total_energy else 0.0,
        "served_user_steps": served,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
        "action_trace_sha256": _canonical_sha256(action_trace),
    }


def _evaluate(
    policies: dict[str, EEAxisPairwiseTrainer],
    *,
    checkpoint_sha256: str,
    tle_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    record = read_prereg(REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json")
    rows: dict[str, list[dict[str, Any]]] = {
        **{label: [] for label in policies},
        "M0": [],
    }
    with tempfile.TemporaryDirectory(prefix="mcrl-v03-matched-ablation-eval-") as temporary:
        archive = c2_probe._frozen_archive(
            record, tle_root, Path(temporary) / "frozen-tle"
        )
        main, checkpoint = loader._verify_and_load_trainer(
            record,
            archive,
            run_dir=REPO / "artifacts" / "training-2026-08-25-rerun01" / "main",
            users=100,
        )
        if checkpoint["checkpoint_sha256"] != checkpoint_sha256:
            raise MatchedAblationError("M0 and Catfish policies use different checkpoints")
        main_before = c2_backend_smoke._network_snapshot(main)
        for seed in EVALUATION_SEEDS:
            for label, trainer in policies.items():
                wrapped = loader._make_environment(archive, users=100)
                wrapped.environment._fading_field = KeyedFadingField.from_components(
                    "multi-catfish-mcrl-v03-ablation-paired-evaluation-v1",
                    checkpoint_sha256,
                    seed,
                )
                env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(seed)
                receipt = evaluate_ee_axis_episode(
                    trainer,
                    wrapped,
                    env_rng=env_rng,
                    mobility_rng=mobility_rng,
                    evaluation_seed=seed,
                    policy_label=label,
                )
                rows[label].append(
                    {
                        **receipt.payload(),
                        "receipt_sha256": receipt.verify(),
                        "total_bits": receipt.total_bits,
                        "total_energy_j": receipt.total_energy_j,
                        "ratio_of_sums_ee_bits_per_j": receipt.ratio_of_sums_ee_bits_per_j,
                        "served_fraction": receipt.served_fraction,
                        "outage_fraction": receipt.outage_fraction,
                    }
                )
            rows["M0"].append(
                _m0_episode(
                    main,
                    archive,
                    seed=seed,
                    checkpoint_sha256=checkpoint_sha256,
                )
            )
        if not c2_backend_smoke._networks_equal(main, main_before):
            raise MatchedAblationError("M0 evaluation mutated the frozen Main networks")
    return rows


def _aggregate(rows: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for label, policy_rows in rows.items():
        bits = float(math.fsum(float(row["total_bits"]) for row in policy_rows))
        energy = float(math.fsum(float(row["total_energy_j"]) for row in policy_rows))
        decisions = int(sum(int(row["decision_count"]) for row in policy_rows))
        served = int(sum(int(row["served_user_steps"]) for row in policy_rows))
        summary[label] = {
            "pooled_ratio_of_sums_ee_bits_per_j": bits / energy if energy else 0.0,
            "mean_episode_ee_bits_per_j": float(
                np.mean([float(row["ratio_of_sums_ee_bits_per_j"]) for row in policy_rows])
            ),
            "pooled_served_fraction": served / decisions,
            "pooled_outage_fraction": 1.0 - served / decisions,
            "total_bits": bits,
            "total_energy_j": energy,
        }
    return summary


def run_ablation(
    *,
    informed_corpus_dir: Path,
    informed_temporal_paths: tuple[Path, ...],
    neutral_opening_dir: Path,
    neutral_temporal_paths: tuple[Path, ...],
    output_dir: Path,
    tle_root: Path,
    episodes: int,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite matched ablation: {output_dir}")
    if type(episodes) is not int or not 1 <= episodes <= 20:
        raise ValueError("episodes must be in [1,20]")
    started = time.perf_counter()
    informed_opening = read_opening_dataset(informed_corpus_dir / "opening-do.json")
    informed_parts = [read_temporal_dataset(path) for path in informed_temporal_paths]
    informed_temporal = EEAxisTemporalDataset.from_pairs(
        row for dataset in informed_parts for row in dataset.rows
    )
    neutral_opening = read_opening_dataset(neutral_opening_dir / "opening-do.json")
    neutral_parts = [read_temporal_dataset(path) for path in neutral_temporal_paths]
    neutral_temporal = EEAxisTemporalDataset.from_pairs(
        row for dataset in neutral_parts for row in dataset.rows
    )
    datasets = (informed_opening, informed_temporal, neutral_opening, neutral_temporal)
    checkpoints = {dataset.checkpoint_sha256 for dataset in datasets}
    if len(checkpoints) != 1:
        raise MatchedAblationError("ablation datasets mix Main checkpoints")
    checkpoint_sha256 = checkpoints.pop()
    lambdas = {
        float(informed_opening.rows[0].raw_pair.lambda_bits_per_j),
        float(informed_temporal.lambda_bits_per_j),
        float(neutral_opening.rows[0].raw_pair.lambda_bits_per_j),
        float(neutral_temporal.lambda_bits_per_j),
    }
    if len(lambdas) != 1:
        raise MatchedAblationError("ablation datasets mix lambda0 values")
    if informed_opening.common_random_field_sha256 != neutral_opening.common_random_field_sha256:
        raise MatchedAblationError("informed/neutral opening data do not share keyed fading")
    if len(informed_opening.c1_pairs) != len(neutral_opening.c1_pairs):
        raise MatchedAblationError("C1 informed/neutral budgets disagree")
    if len(informed_opening.c3_pairs) != len(neutral_opening.c3_pairs):
        raise MatchedAblationError("C3 informed/neutral budgets disagree")
    if len(informed_temporal.rows) != len(neutral_temporal.rows):
        raise MatchedAblationError("C2 informed/neutral budgets disagree")
    informed_c2_fields = {
        row.seed: row.common_random_field_sha256 for row in informed_temporal.rows
    }
    neutral_c2_fields = {
        row.seed: row.common_random_field_sha256 for row in neutral_temporal.rows
    }
    if informed_c2_fields != neutral_c2_fields:
        raise MatchedAblationError(
            "C2 informed/neutral rows are not paired by seed and keyed fading"
        )
    calibration = informed_pilot._calibration(
        checkpoint_sha256=checkpoint_sha256,
        lambda_bits_per_j=lambdas.pop(),
    )

    informed = {
        "C1": informed_opening.c1_batch(),
        "C2": informed_temporal.route_batch(),
        "C3": informed_opening.c3_batch(),
    }
    neutral = {
        "C1": neutral_opening.c1_batch(),
        "C2": neutral_temporal.route_batch(),
        "C3": neutral_opening.c3_batch(),
    }
    arm_routes = {
        "F111": (informed["C1"], informed["C2"], informed["C3"]),
        "N000": (neutral["C1"], neutral["C2"], neutral["C3"]),
        "A011": (neutral["C1"], informed["C2"], informed["C3"]),
        "A101": (informed["C1"], neutral["C2"], informed["C3"]),
        "A110": (informed["C1"], informed["C2"], neutral["C3"]),
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        policies: dict[str, EEAxisPairwiseTrainer] = {}
        training: dict[str, Any] = {}
        for label, route_batches in arm_routes.items():
            batches = EEAxisThreeRouteBatches(
                c1=route_batches[0], c2=route_batches[1], c3=route_batches[2]
            )
            trainer = EEAxisPairwiseTrainer(
                calibration.pairwise_config(learning_rate=LEARNING_RATE),
                train_seed=TRAIN_SEED,
            )
            status = run_pairwise_pilot(
                trainer,
                batches,
                spec=EEAxisPilotRunSpec(
                    run_id=label,
                    episodes=episodes,
                    checkpoint_every_episodes=100,
                ),
                output_dir=staging / label,
            )
            policies[label] = trainer
            training[label] = {
                "initial_fit": status["initial_fit"],
                "final_fit": status["final_fit"],
                "elapsed_s": status["elapsed_s"],
            }
        evaluation_rows = _evaluate(
            policies,
            checkpoint_sha256=checkpoint_sha256,
            tle_root=tle_root,
        )
        aggregate = _aggregate(evaluation_rows)
        ee = {
            label: values["pooled_ratio_of_sums_ee_bits_per_j"]
            for label, values in aggregate.items()
        }
        contrasts = {
            "full_vs_neutral": ee["F111"] - ee["N000"],
            "full_vs_m0": ee["F111"] - ee["M0"],
            "c1_contribution_full_vs_A011": ee["F111"] - ee["A011"],
            "c2_contribution_full_vs_A101": ee["F111"] - ee["A101"],
            "c3_contribution_full_vs_A110": ee["F111"] - ee["A110"],
        }
        payload = {
            "schema": SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "episodes": episodes,
            "learning_rate": LEARNING_RATE,
            "train_seed": TRAIN_SEED,
            "evaluation_seeds": list(EVALUATION_SEEDS),
            "checkpoint_sha256": checkpoint_sha256,
            "budgets": {
                "C1": len(informed_opening.c1_pairs),
                "C2": len(informed_temporal.rows),
                "C3": len(informed_opening.c3_pairs),
            },
            "training": training,
            "heldout_rows": evaluation_rows,
            "aggregate": aggregate,
            "ee_contrasts_bits_per_j": contrasts,
            "directional_pass": {
                "F111_gt_N000": contrasts["full_vs_neutral"] > 0.0,
                "F111_gt_M0": contrasts["full_vs_m0"] > 0.0,
                "C1": contrasts["c1_contribution_full_vs_A011"] > 0.0,
                "C2": contrasts["c2_contribution_full_vs_A101"] > 0.0,
                "C3": contrasts["c3_contribution_full_vs_A110"] > 0.0,
            },
            "elapsed_s": time.perf_counter() - started,
        }
        (staging / "receipt.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        shutil.move(str(staging), str(output_dir))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--informed-corpus-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-phase1-informed-corpus-20260831",
    )
    parser.add_argument(
        "--informed-temporal",
        type=Path,
        action="append",
        default=None,
    )
    parser.add_argument(
        "--neutral-opening-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-phase1-neutral-opening-20260831",
    )
    parser.add_argument(
        "--neutral-temporal",
        type=Path,
        action="append",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-10ep-matched-ablation-20260831",
    )
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--episodes", type=int, default=10)
    args = parser.parse_args()
    neutral_paths = tuple(args.neutral_temporal or (
        REPO / "artifacts" / "multi-catfish-v03-c2-neutral-temporal-seed1-20260831.json",
        REPO / "artifacts" / "multi-catfish-v03-c2-neutral-temporal-seed2-20260831.json",
    ))
    informed_paths = tuple(args.informed_temporal or (
        REPO / "artifacts" / "multi-catfish-v03-c2-matched-informed-temporal-seed1-20260831.json",
        REPO / "artifacts" / "multi-catfish-v03-c2-matched-informed-temporal-seed2-20260831.json",
    ))
    payload = run_ablation(
        informed_corpus_dir=args.informed_corpus_dir,
        informed_temporal_paths=informed_paths,
        neutral_opening_dir=args.neutral_opening_dir,
        neutral_temporal_paths=neutral_paths,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
        episodes=args.episodes,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
