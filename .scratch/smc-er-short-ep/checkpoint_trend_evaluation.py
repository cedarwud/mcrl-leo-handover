#!/usr/bin/env python3
"""Evaluate every 100EP Main-only checkpoint as an intermediate EE curve.

This evaluator is deliberately separate from the final EE-vs-users sweep.
It uses one fixed load (100 users) and the five frozen TEST seeds to show the
training trajectory without changing or selecting a training checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from intermediate_trend_authority import (  # noqa: E402
    ALLOWED_ARMS,
    TREND_CHECKPOINT_EVERY_EPISODES,
    TREND_EVALUATION_SEEDS,
    TREND_USERS,
)
from mcrl.artifacts import read_checkpoint  # noqa: E402
from sweep_evaluation import (  # noqa: E402
    canonical_ephemeris_authority,
    evaluate_checkpoint_point,
    ratio_of_sums,
    sha256_file,
)


SCHEMA = "multi-catfish-mcrl-checkpoint-ee-trajectory-v1"
ARM_LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A011": "Full - C1",
    "A101": "Full - C2",
    "A110": "Full - C3",
}
PLOT_STYLE = {
    "B000": ("#6E7278", "--", "o"),
    "F111": ("#1F6FB4", "-", "D"),
    "A011": ("#C6533D", "-.", "s"),
    "A101": ("#8A5FB5", ":", "^"),
    "A110": ("#2E8B4A", (0, (5, 2)), "v"),
}


class CheckpointTrendError(RuntimeError):
    """Raised when a checkpoint trajectory is incomplete or inconsistent."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CheckpointTrendError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise CheckpointTrendError(f"{label} must be a JSON object")
    return value


def checkpoint_schedule(episodes: int) -> tuple[int, ...]:
    if type(episodes) is not int or episodes < TREND_CHECKPOINT_EVERY_EPISODES:
        raise CheckpointTrendError("episodes cannot satisfy the 100EP cadence")
    if episodes % TREND_CHECKPOINT_EVERY_EPISODES != 0:
        raise CheckpointTrendError("episodes must end on a 100EP checkpoint")
    return tuple(
        range(
            TREND_CHECKPOINT_EVERY_EPISODES,
            episodes + 1,
            TREND_CHECKPOINT_EVERY_EPISODES,
        )
    )


def load_checkpoint_inventory(
    matrix_root: Path,
) -> tuple[int, int, list[dict[str, Any]]]:
    """Return exact arm/episode checkpoint rows from a complete matrix."""

    root = Path(matrix_root).expanduser().resolve()
    matrix = _read_object(root / "matrix-receipt.json", label="matrix receipt")
    if matrix.get("status") != "complete":
        raise CheckpointTrendError("matrix receipt must be complete")
    if tuple(matrix.get("arms", ())) != tuple(ALLOWED_ARMS):
        raise CheckpointTrendError("matrix receipt arm order drifted")
    episodes = matrix.get("episodes")
    if type(episodes) is not int:
        raise CheckpointTrendError("matrix episode count is malformed")
    expected = checkpoint_schedule(episodes)
    training = matrix.get("training")
    if not isinstance(training, Mapping):
        raise CheckpointTrendError("matrix training block is missing")
    if training.get("checkpoint_every_episodes") != TREND_CHECKPOINT_EVERY_EPISODES:
        raise CheckpointTrendError("matrix checkpoint cadence drifted")
    training_seed = training.get("training_seed")
    if type(training_seed) is not int:
        raise CheckpointTrendError("matrix training seed is malformed")

    inventory: list[dict[str, Any]] = []
    for arm in ALLOWED_ARMS:
        status_path = root / arm / "status.json"
        status = _read_object(status_path, label=f"{arm} status")
        if status.get("status") != "complete" or status.get("arm") != arm:
            raise CheckpointTrendError(f"{arm} status is not complete")
        result = status.get("result")
        if not isinstance(result, Mapping):
            raise CheckpointTrendError(f"{arm} result is missing")
        rows = result.get("periodic_checkpoints")
        if not isinstance(rows, list):
            raise CheckpointTrendError(f"{arm} periodic checkpoints are missing")
        observed: list[int] = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise CheckpointTrendError(f"{arm} checkpoint row is malformed")
            completed = row.get("episodes_completed")
            if type(completed) is not int:
                raise CheckpointTrendError(f"{arm} checkpoint episode is malformed")
            observed.append(completed)
            expected_path = (
                root / arm / "checkpoints" / f"ep-{completed:06d}-main.pt"
            ).resolve()
            try:
                recorded_path = Path(str(row.get("path"))).expanduser().resolve()
            except (OSError, RuntimeError):
                recorded_path = None
            if recorded_path != expected_path or not expected_path.is_file():
                raise CheckpointTrendError(
                    f"{arm} checkpoint {completed} path/file mismatch"
                )
            digest = sha256_file(expected_path)
            if row.get("sha256") != digest:
                raise CheckpointTrendError(f"{arm} checkpoint {completed} hash mismatch")
            payload = read_checkpoint(expected_path, map_location="cpu")
            if payload.episode != completed - 1:
                raise CheckpointTrendError(
                    f"{arm} checkpoint {completed} payload episode mismatch"
                )
            if int(payload.train_seed) != training_seed:
                raise CheckpointTrendError(
                    f"{arm} checkpoint {completed} training seed mismatch"
                )
            inventory.append(
                {
                    "arm": arm,
                    "arm_label": ARM_LABELS[arm],
                    "episodes_completed": completed,
                    "path": expected_path,
                    "sha256": digest,
                    "payload": payload,
                }
            )
        if tuple(observed) != expected:
            raise CheckpointTrendError(f"{arm} checkpoint sequence is incomplete")
    return episodes, training_seed, inventory


def aggregate_trajectory(raw_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        grouped[(str(row["arm"]), int(row["episodes_completed"]))].append(row)

    summary: list[dict[str, Any]] = []
    for arm in ALLOWED_ARMS:
        for (row_arm, completed), group in sorted(grouped.items()):
            if row_arm != arm:
                continue
            seeds = [int(row["evaluation_seed"]) for row in group]
            if tuple(seeds) != tuple(TREND_EVALUATION_SEEDS):
                raise CheckpointTrendError(
                    f"{arm} checkpoint {completed} evaluation seeds drifted"
                )
            bits = math.fsum(float(row["useful_bits"]) for row in group)
            energy = math.fsum(float(row["system_energy_j"]) for row in group)
            served = sum(int(row["served_user_intervals"]) for row in group)
            total = sum(int(row["total_user_intervals"]) for row in group)
            summary.append(
                {
                    "arm": arm,
                    "arm_label": ARM_LABELS[arm],
                    "episodes_completed": completed,
                    "users": TREND_USERS,
                    "evaluation_seeds": seeds,
                    "useful_bits": bits,
                    "system_energy_j": energy,
                    "system_ee_bits_per_j": ratio_of_sums(bits, energy),
                    "served_fraction": served / total if total else 0.0,
                    "zero_power_intervals": sum(
                        int(row["zero_power_intervals"]) for row in group
                    ),
                    "zero_service_intervals": sum(
                        int(row["zero_service_intervals"]) for row in group
                    ),
                }
            )
    return summary


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        raise CheckpointTrendError("refusing to write an empty trajectory CSV")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)


def _plot(path: Path, summary: Sequence[Mapping[str, Any]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12.0, 5.2))
    for arm in ALLOWED_ARMS:
        rows = [row for row in summary if row["arm"] == arm]
        xs = [int(row["episodes_completed"]) for row in rows]
        ys = [float(row["system_ee_bits_per_j"]) / 1e6 for row in rows]
        colour, linestyle, marker = PLOT_STYLE[arm]
        mark_every = max(1, len(xs) // 10)
        ax.plot(
            xs,
            ys,
            color=colour,
            linestyle=linestyle,
            marker=marker,
            markevery=mark_every,
            markersize=6,
            linewidth=2.2,
            label=ARM_LABELS[arm],
        )
    ax.set_xlabel("Training episodes", fontsize=20)
    ax.set_ylabel("Held-out EE at 100 users (Mbits/J)", fontsize=20)
    ax.tick_params(axis="both", labelsize=16)
    ax.grid(True, linestyle=":", linewidth=0.9, alpha=0.45)
    ax.legend(loc="best", frameon=False, fontsize=13)
    fig.text(
        0.995,
        0.008,
        "one-seed 100EP trajectory - not Chapter 5 evidence",
        ha="right",
        va="bottom",
        fontsize=12,
        style="italic",
    )
    fig.tight_layout(pad=0.7, rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def evaluate_trajectory(
    *,
    matrix_root: Path,
    output_dir: Path,
    tle_root: Path,
    prereg: Path,
) -> dict[str, Any]:
    episodes, training_seed, inventory = load_checkpoint_inventory(matrix_root)
    archive, ephemeris = canonical_ephemeris_authority(prereg, tle_root)
    raw_rows: list[dict[str, Any]] = []
    for item in inventory:
        for seed in TREND_EVALUATION_SEEDS:
            totals = evaluate_checkpoint_point(
                archive=archive,
                checkpoint_path=item["path"],
                checkpoint_payload=item["payload"],
                arm=item["arm"],
                checkpoint_sha256=item["sha256"],
                users=TREND_USERS,
                evaluation_seed=seed,
            )
            row = asdict(totals)
            row["arm_label"] = item["arm_label"]
            row["episodes_completed"] = item["episodes_completed"]
            raw_rows.append(row)
    summary = aggregate_trajectory(raw_rows)
    expected_rows = len(ALLOWED_ARMS) * len(checkpoint_schedule(episodes))
    if len(summary) != expected_rows:
        raise CheckpointTrendError("trajectory summary row count mismatch")

    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw_path = out / "checkpoint-trend-raw.json"
    summary_path = out / "checkpoint-trend-summary.json"
    raw_path.write_text(
        json.dumps(raw_rows, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    payload = {
        "schema": SCHEMA,
        "status": "complete",
        "claim_ceiling": "ONE_SEED_100EP_MAIN_ONLY_EE_TRAJECTORY_NOT_CHAPTER5",
        "episodes": episodes,
        "checkpoint_every_episodes": TREND_CHECKPOINT_EVERY_EPISODES,
        "training_seed": training_seed,
        "users": TREND_USERS,
        "evaluation_seeds": list(TREND_EVALUATION_SEEDS),
        "evaluation_partition": "TEST",
        "evaluation_policy": "Main-only masked-greedy MODQN",
        "ee_aggregation": "ratio of pooled useful bits to pooled system energy within each arm/checkpoint cell",
        "authority": ephemeris,
        "matrix_receipt": str(Path(matrix_root).expanduser().resolve() / "matrix-receipt.json"),
        "matrix_receipt_sha256": sha256_file(
            Path(matrix_root).expanduser().resolve() / "matrix-receipt.json"
        ),
        "summary": summary,
    }
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(out / "checkpoint-trend-raw.csv", raw_rows)
    flat = [
        {key: value for key, value in row.items() if key != "evaluation_seeds"}
        for row in summary
    ]
    _write_csv(out / "checkpoint-trend-summary.csv", flat)
    plot_path = out / "ee-vs-training-episodes.png"
    try:
        _plot(plot_path, summary)
        plot_status = {"status": "complete", "path": str(plot_path)}
    except ModuleNotFoundError as error:
        if error.name != "matplotlib":
            raise
        plot_status = {
            "status": "data-complete-plot-dependency-missing",
            "path": None,
            "error": str(error),
        }
    (out / "plot-status.json").write_text(
        json.dumps(plot_status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        evaluate_trajectory(
            matrix_root=args.matrix_root,
            output_dir=args.output_dir,
            tle_root=args.tle_root,
            prereg=args.prereg,
        )
    except CheckpointTrendError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(Path(args.output_dir).expanduser().resolve() / "checkpoint-trend-summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
