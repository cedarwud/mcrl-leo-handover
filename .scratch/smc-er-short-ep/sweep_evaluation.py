#!/usr/bin/env python3
"""Measured Main-only EE sweep for Multi-Catfish MCRL checkpoints.

The evaluator never averages per-step EE ratios.  It pools useful bits and
system energy over every fresh-seed developmental rollout first, then divides.  A checkpoint is
loaded into the unchanged scalarized/masked-greedy MODQN policy; Catfish roles
are absent during evaluation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.constants import DECISION_STEP_S, TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TEST,
    BlockAlternatingSplit,
    EpisodeStartSampler,
)
from mcrl.env.mobility import MobilityConfig  # noqa: E402
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver  # noqa: E402
from mcrl.env.step import StepEnvironment  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402


SCHEMA = "multi-catfish-mcrl-short-ep-ee-users-sweep-v2"
EVALUATION_PARTITION = TEST
DEFAULT_USERS = (60, 80, 100, 120, 140)
PLOT_ORDER = (
    "Baseline MODQN",
    "Full Multi-Catfish MCRL",
    "Full - C1",
    "Full - C2",
    "Full - C3",
)
PLOT_STYLE = {
    "Baseline MODQN": ("#6E7278", "--", "o"),
    "Full Multi-Catfish MCRL": ("#1F6FB4", "-", "D"),
    "Full - C1": ("#C6533D", "-.", "s"),
    "Full - C2": ("#8A5FB5", ":", "^"),
    "Full - C3": ("#2E8B4A", (0, (5, 2)), "v"),
}


@dataclass(frozen=True)
class EpisodeTotals:
    """Additive quantities for one fresh-seed TEST-partition episode."""

    arm: str
    checkpoint_sha256: str
    training_seed: int
    evaluation_seed: int
    users: int
    steps: int
    duration_s: float
    useful_bits: float
    system_energy_j: float
    system_ee_bits_per_j: float
    mean_system_power_w: float
    mean_system_throughput_bps: float
    served_user_intervals: int
    total_user_intervals: int
    served_fraction: float
    zero_power_intervals: int
    zero_service_intervals: int
    r1_sum: float
    r2_sum: float
    r3_sum: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_ephemeris_authority(
    prereg_path: Path, tle_root: Path
) -> tuple[TleArchive, dict[str, Any]]:
    prereg = Path(prereg_path).expanduser().resolve()
    if (
        prereg != Path(CANONICAL_PREREG).resolve()
        or not prereg.is_file()
        or sha256_file(prereg) != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("EE sweep requires the canonical sealed preregistration")
    record = read_prereg(prereg)
    record.verify()
    archive = TleArchive(Path(tle_root).expanduser().resolve())
    ephemeris = assert_ephemeris_matches_record(record, archive=archive)
    return archive, {
        "prereg_path": str(prereg),
        "prereg_sha256": sha256_file(prereg),
        "tle_root_path": str(archive.root.resolve()),
        "tle_file_set_sha256": str(ephemeris["file_set_sha256"]),
        "tle_file_count": int(ephemeris["archive"]["file_count"]),
    }


def ratio_of_sums(useful_bits: float, system_energy_j: float) -> float:
    """Return pooled EE and fail closed on physically impossible input."""

    bits = float(useful_bits)
    energy = float(system_energy_j)
    if not math.isfinite(bits) or bits < 0.0:
        raise ValueError("useful_bits must be finite and non-negative")
    if not math.isfinite(energy) or energy < 0.0:
        raise ValueError("system_energy_j must be finite and non-negative")
    if energy == 0.0:
        if bits != 0.0:
            raise ValueError("positive useful bits with zero system energy")
        return 0.0
    return bits / energy


def _trainer_config(payload: Mapping[str, Any]) -> TrainerConfig:
    values = dict(payload)
    for key in ("hidden_layers", "objective_weights", "reward_calibration_scales"):
        if key in values:
            values[key] = tuple(values[key])
    return TrainerConfig(**values)


def make_environment(archive: TleArchive, *, users: int) -> TrainerEnvironment:
    if users < 1:
        raise ValueError("users must be positive")
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=int(users))),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(
        archive, split, EVALUATION_PARTITION
    )
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def evaluation_rngs(seed: int) -> tuple[np.random.Generator, np.random.Generator]:
    env_seq, mobility_seq, _action_seq, _control_seq = np.random.SeedSequence(
        int(seed)
    ).spawn(4)
    return np.random.default_rng(env_seq), np.random.default_rng(mobility_seq)


def evaluate_checkpoint_point(
    *,
    archive: TleArchive,
    checkpoint_path: Path,
    checkpoint_payload: Any,
    arm: str,
    checkpoint_sha256: str,
    users: int,
    evaluation_seed: int,
) -> EpisodeTotals:
    """Evaluate one point from a newly constructed, frozen runtime.

    A fresh evaluation seed must not inherit mutable state from a preceding seed:
    ``MODQNTrainer`` owns an action RNG and the environment owns persistent
    scenario/mobility state. Reconstruct both, then load the same checkpoint,
    for every ``(checkpoint, users, evaluation_seed)`` point.
    """

    environment = make_environment(archive, users=users)
    environment.assert_ready_to_train()
    trainer = MODQNTrainer(
        environment,
        _trainer_config(checkpoint_payload.trainer_config),
        train_seed=int(checkpoint_payload.train_seed),
        env_seed=int(checkpoint_payload.env_seed),
        mobility_seed=int(checkpoint_payload.mobility_seed),
        device="cpu",
    )
    trainer.load_checkpoint(checkpoint_path, load_optimizers=False)
    return evaluate_one_episode(
        trainer,
        environment,
        arm=arm,
        checkpoint_sha256=checkpoint_sha256,
        training_seed=int(checkpoint_payload.train_seed),
        evaluation_seed=evaluation_seed,
    )


def _validated_checkpoint_inputs(
    arms: Sequence[tuple[str, Path]],
) -> list[tuple[str, Path, Any, str]]:
    """Read input receipts and reject ambiguous arm/training-seed identities."""

    seen: set[tuple[str, int]] = set()
    materialized: list[tuple[str, Path, Any, str]] = []
    for label, checkpoint_path in arms:
        if not checkpoint_path.is_file():
            raise ValueError(f"checkpoint does not exist: {checkpoint_path}")
        payload = read_checkpoint(checkpoint_path, map_location="cpu")
        identity = (label, int(payload.train_seed))
        if identity in seen:
            raise ValueError(
                "duplicate (arm, training_seed) input is not allowed: "
                f"{label!r}, {payload.train_seed}"
            )
        seen.add(identity)
        materialized.append((label, checkpoint_path, payload, sha256_file(checkpoint_path)))
    return materialized


def evaluate_one_episode(
    trainer: MODQNTrainer,
    environment: TrainerEnvironment,
    *,
    arm: str,
    checkpoint_sha256: str,
    training_seed: int,
    evaluation_seed: int,
) -> EpisodeTotals:
    """Run one frozen Main policy and retain the EE numerator/denominator."""

    env_rng, mobility_rng = evaluation_rngs(evaluation_seed)
    states, masks, _observation = environment.reset(env_rng, mobility_rng)
    useful_bits = 0.0
    system_energy_j = 0.0
    served_user_intervals = 0
    zero_power_intervals = 0
    zero_service_intervals = 0
    reward_sum = np.zeros(3, dtype=np.float64)
    steps = 0

    for _ in range(environment.config.steps_per_episode):
        encoded = trainer.encode_states(states)
        actions = trainer.select_actions(encoded, masks, eps=0.0, raw_states=states)
        result = environment.step(actions, env_rng)
        outcome = environment.last_outcome
        throughput = float(outcome.energy.system_throughput_bps)
        power = float(outcome.energy.system_consumed_power_w)
        if not math.isfinite(throughput) or throughput < 0.0:
            raise RuntimeError("fresh-seed system throughput is invalid")
        if not math.isfinite(power) or power < 0.0:
            raise RuntimeError("fresh-seed system power is invalid")
        useful_bits += throughput * DECISION_STEP_S
        system_energy_j += power * DECISION_STEP_S
        served_user_intervals += int(outcome.energy.served)
        zero_power_intervals += int(power == 0.0)
        zero_service_intervals += int(outcome.energy.served == 0)
        reward_sum += outcome.reward_matrix.sum(axis=0)
        steps += 1
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks

    duration = float(steps * DECISION_STEP_S)
    ee = ratio_of_sums(useful_bits, system_energy_j)
    total_user_intervals = int(steps * environment.num_users)
    return EpisodeTotals(
        arm=arm,
        checkpoint_sha256=checkpoint_sha256,
        training_seed=int(training_seed),
        evaluation_seed=int(evaluation_seed),
        users=int(environment.num_users),
        steps=steps,
        duration_s=duration,
        useful_bits=useful_bits,
        system_energy_j=system_energy_j,
        system_ee_bits_per_j=ee,
        mean_system_power_w=(system_energy_j / duration if duration else 0.0),
        mean_system_throughput_bps=(useful_bits / duration if duration else 0.0),
        served_user_intervals=served_user_intervals,
        total_user_intervals=total_user_intervals,
        served_fraction=(
            served_user_intervals / total_user_intervals
            if total_user_intervals
            else 0.0
        ),
        zero_power_intervals=zero_power_intervals,
        zero_service_intervals=zero_service_intervals,
        r1_sum=float(reward_sum[0]),
        r2_sum=float(reward_sum[1]),
        r3_sum=float(reward_sum[2]),
    )


def aggregate_rows(rows: Sequence[EpisodeTotals]) -> list[dict[str, Any]]:
    """Pool eval episodes within a training seed, then mean training seeds."""

    by_train: dict[tuple[str, int, int], list[EpisodeTotals]] = defaultdict(list)
    for row in rows:
        by_train[(row.arm, row.users, row.training_seed)].append(row)

    seed_rows: list[dict[str, Any]] = []
    for (arm, users, training_seed), group in sorted(by_train.items()):
        bits = math.fsum(row.useful_bits for row in group)
        energy = math.fsum(row.system_energy_j for row in group)
        duration = math.fsum(row.duration_s for row in group)
        served = sum(row.served_user_intervals for row in group)
        user_intervals = sum(row.total_user_intervals for row in group)
        seed_rows.append(
            {
                "arm": arm,
                "users": users,
                "training_seed": training_seed,
                "evaluation_seeds": [row.evaluation_seed for row in group],
                "useful_bits": bits,
                "system_energy_j": energy,
                "system_ee_bits_per_j": ratio_of_sums(bits, energy),
                "mean_system_power_w": energy / duration if duration else 0.0,
                "mean_system_throughput_bps": bits / duration if duration else 0.0,
                "served_fraction": served / user_intervals if user_intervals else 0.0,
                "zero_power_intervals": sum(row.zero_power_intervals for row in group),
                "zero_service_intervals": sum(
                    row.zero_service_intervals for row in group
                ),
            }
        )

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in seed_rows:
        grouped[(str(row["arm"]), int(row["users"]))].append(row)

    summary: list[dict[str, Any]] = []
    for (arm, users), group in sorted(grouped.items()):
        ee = np.array(
            [float(row["system_ee_bits_per_j"]) for row in group],
            dtype=np.float64,
        )
        summary.append(
            {
                "arm": arm,
                "users": users,
                "training_seed_count": len(group),
                "mean_ee_bits_per_j": float(np.mean(ee)),
                "median_ee_bits_per_j": float(np.median(ee)),
                "min_ee_bits_per_j": float(np.min(ee)),
                "max_ee_bits_per_j": float(np.max(ee)),
                "seed_rows": group,
            }
        )
    return summary


def _parse_arm(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--arm must be LABEL=/path/to/checkpoint.pt")
    label, raw_path = value.split("=", 1)
    label = label.strip()
    path = Path(raw_path).expanduser().resolve()
    if not label:
        raise argparse.ArgumentTypeError("--arm label cannot be empty")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"checkpoint does not exist: {path}")
    return label, path


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        raise ValueError("refusing to write an empty sweep CSV")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)


def _plot(path: Path, summary: Sequence[Mapping[str, Any]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_arm: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in summary:
        by_arm[str(row["arm"])].append(row)

    fig, ax = plt.subplots(figsize=(12.0, 4.8))
    ordered = [arm for arm in PLOT_ORDER if arm in by_arm]
    ordered.extend(sorted(set(by_arm) - set(ordered)))
    for arm in ordered:
        rows = sorted(by_arm[arm], key=lambda item: int(item["users"]))
        xs = np.array([int(row["users"]) for row in rows], dtype=np.int64)
        ys = np.array(
            [float(row["mean_ee_bits_per_j"]) / 1e6 for row in rows],
            dtype=np.float64,
        )
        low = np.array(
            [float(row["min_ee_bits_per_j"]) / 1e6 for row in rows],
            dtype=np.float64,
        )
        high = np.array(
            [float(row["max_ee_bits_per_j"]) / 1e6 for row in rows],
            dtype=np.float64,
        )
        colour, linestyle, marker = PLOT_STYLE.get(arm, (None, "-", "o"))
        ax.plot(
            xs,
            ys,
            color=colour,
            linestyle=linestyle,
            marker=marker,
            markersize=7,
            linewidth=2.4,
            label=arm,
        )
        if np.any(high > low):
            ax.vlines(xs, low, high, color=colour, alpha=0.32, linewidth=1.4)

    ax.set_xlabel("Number of users", fontsize=20)
    ax.set_ylabel("Held-out EE (Mbits/J)", fontsize=20)
    ax.tick_params(axis="both", labelsize=17)
    ax.grid(True, linestyle=":", linewidth=0.9, alpha=0.45)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=min(3, max(len(ordered), 1)),
        frameon=False,
        fontsize=15,
    )
    fig.text(
        0.995,
        0.008,
        "short-EP measured trend - not Chapter 5 evidence",
        ha="right",
        va="bottom",
        fontsize=13,
        style="italic",
    )
    fig.tight_layout(pad=0.6, rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arm",
        action="append",
        required=True,
        type=_parse_arm,
        help="repeatable LABEL=/path/to/final-checkpoint.pt",
    )
    parser.add_argument("--users", nargs="+", type=int, default=list(DEFAULT_USERS))
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    users = tuple(int(value) for value in args.users)
    seeds = tuple(int(value) for value in args.seeds)
    if len(set(users)) != len(users) or min(users) < 1:
        raise ValueError("--users must be unique positive integers")
    if len(set(seeds)) != len(seeds):
        raise ValueError("--seeds must be unique")
    archive, ephemeris_authority = canonical_ephemeris_authority(
        args.prereg, args.tle_root
    )
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    raw: list[EpisodeTotals] = []
    checkpoint_receipts: list[dict[str, Any]] = []
    for label, checkpoint_path, payload, checkpoint_sha in _validated_checkpoint_inputs(
        args.arm
    ):
        checkpoint_receipts.append(
            {
                "arm": label,
                "path": str(checkpoint_path),
                "sha256": checkpoint_sha,
                "episode": int(payload.episode),
                "training_seed": int(payload.train_seed),
                "checkpoint_kind": payload.checkpoint_kind,
            }
        )
        for user_count in users:
            for seed in seeds:
                raw.append(
                    evaluate_checkpoint_point(
                        archive=archive,
                        checkpoint_path=checkpoint_path,
                        checkpoint_payload=payload,
                        arm=label,
                        checkpoint_sha256=checkpoint_sha,
                        users=user_count,
                        evaluation_seed=seed,
                    )
                )

    summary = aggregate_rows(raw)
    raw_rows = [asdict(row) for row in raw]
    (output_dir / "sweep-raw.json").write_text(
        json.dumps(raw_rows, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / "sweep-summary.json").write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "method_family": "Multi-Catfish MCRL",
                "evaluation_policy": "Main-only masked-greedy MODQN",
                "evaluation_partition": EVALUATION_PARTITION,
                "ee_aggregation": "per-training-seed ratio-of-sums, then equal-weight training-seed mean",
                "users": list(users),
                "evaluation_seeds": list(seeds),
                "authority": ephemeris_authority,
                "checkpoints": checkpoint_receipts,
                "summary": summary,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _write_csv(output_dir / "sweep-raw.csv", raw_rows)
    flat_summary = [
        {key: value for key, value in row.items() if key != "seed_rows"}
        for row in summary
    ]
    _write_csv(output_dir / "sweep-summary.csv", flat_summary)
    plot_path = output_dir / "ee-vs-users-short-ep.png"
    try:
        _plot(plot_path, summary)
        plot_receipt = {"status": "complete", "path": str(plot_path)}
    except ModuleNotFoundError as error:
        if error.name != "matplotlib":
            raise
        plot_receipt = {
            "status": "data-complete-plot-dependency-missing",
            "path": None,
            "error": str(error),
            "next_command": (
                "python3 .scratch/smc-er-short-ep/render_sweep_plot.py "
                f"--summary {output_dir / 'sweep-summary.json'} "
                f"--output {plot_path}"
            ),
        }
    (output_dir / "plot-status.json").write_text(
        json.dumps(plot_receipt, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(plot_receipt["path"] or output_dir / "sweep-summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
