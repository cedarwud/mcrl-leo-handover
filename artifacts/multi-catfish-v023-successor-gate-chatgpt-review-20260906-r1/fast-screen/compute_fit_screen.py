#!/usr/bin/env python3
"""Read-only early screen over the frozen V0.23 R6 fit panel."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


WORLDS = tuple(range(2026121705, 2026121713))
SEEDS = (2026135101, 2026135102, 2026135103)
ARMS = ("INFORMED", "MATCHED_PLACEBO")
SIGN_THRESHOLD = 0.02


def midranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def spearman(left: np.ndarray, right: np.ndarray) -> float | None:
    if left.shape != right.shape or left.ndim != 1 or left.size < 2:
        return None
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        return None
    a = midranks(left)
    b = midranks(right)
    a -= float(np.mean(a))
    b -= float(np.mean(b))
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    if denominator == 0.0 or not math.isfinite(denominator):
        return None
    value = float(np.dot(a, b) / denominator)
    return value if math.isfinite(value) else None


def sign_accuracy(prediction: np.ndarray, target: np.ndarray) -> float | None:
    eligible = np.abs(target) >= SIGN_THRESHOLD
    if not np.any(eligible):
        return None
    return float(np.mean(np.sign(prediction[eligible]) == np.sign(target[eligible])))


def load_panel(root: Path) -> dict[tuple[int, int, str], dict[str, np.ndarray]]:
    panel: dict[tuple[int, int, str], dict[str, np.ndarray]] = {}
    for world in WORLDS:
        for seed in SEEDS:
            for arm in ARMS:
                basename = "informed" if arm == "INFORMED" else "matched_placebo"
                path = root / f"world-{world}" / f"seed-{seed}" / f"{basename}.metrics.npz"
                if not path.is_file():
                    raise SystemExit(f"missing frozen fit metrics: {path}")
                with np.load(path, allow_pickle=False) as payload:
                    panel[(world, seed, arm)] = {
                        key: np.asarray(payload[key]).copy()
                        for key in (
                            "identity_world",
                            "identity_anchor",
                            "identity_user",
                            "identity_action",
                            "prediction",
                            "target",
                        )
                    }
    return panel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fit_root", type=Path)
    args = parser.parse_args()
    panel = load_panel(args.fit_root)

    for world in WORLDS:
        reference = panel[(world, SEEDS[0], ARMS[0])]
        for seed in SEEDS:
            for arm in ARMS:
                item = panel[(world, seed, arm)]
                for key in ("identity_world", "identity_anchor", "identity_user", "identity_action", "target"):
                    if not np.array_equal(item[key], reference[key]):
                        raise SystemExit(f"identity/target mismatch at {(world, seed, arm)} field={key}")

    seed_metrics: dict[str, dict[str, dict[str, float | None]]] = {}
    for seed in SEEDS:
        seed_metrics[str(seed)] = {}
        for arm in ARMS:
            prediction = np.concatenate([panel[(world, seed, arm)]["prediction"] for world in WORLDS])
            target = np.concatenate([panel[(world, seed, arm)]["target"] for world in WORLDS])
            seed_metrics[str(seed)][arm] = {
                "spearman": spearman(prediction, target),
                "sign_accuracy": sign_accuracy(prediction, target),
            }

    world_metrics: dict[str, dict[str, object]] = {}
    informed_world_wins = 0
    nonnegative = {str(seed): 0 for seed in SEEDS}
    for world in WORLDS:
        entry: dict[str, object] = {}
        for arm in ARMS:
            values = [
                spearman(panel[(world, seed, arm)]["prediction"], panel[(world, seed, arm)]["target"])
                for seed in SEEDS
            ]
            mean = None if any(value is None for value in values) else float(np.mean(values))
            entry[arm] = {"seed_spearman": values, "mean_spearman": mean}
        informed_mean = entry["INFORMED"]["mean_spearman"]  # type: ignore[index]
        placebo_mean = entry["MATCHED_PLACEBO"]["mean_spearman"]  # type: ignore[index]
        win = informed_mean is not None and placebo_mean is not None and informed_mean > placebo_mean
        informed_world_wins += int(win)
        entry["informed_strictly_above_placebo"] = win
        world_metrics[str(world)] = entry
        for seed in SEEDS:
            value = entry["INFORMED"]["seed_spearman"][SEEDS.index(seed)]  # type: ignore[index]
            nonnegative[str(seed)] += int(value is not None and value >= 0.0)

    informed_rho = [seed_metrics[str(seed)]["INFORMED"]["spearman"] for seed in SEEDS]
    informed_sign = [seed_metrics[str(seed)]["INFORMED"]["sign_accuracy"] for seed in SEEDS]
    placebo_sign = [seed_metrics[str(seed)]["MATCHED_PLACEBO"]["sign_accuracy"] for seed in SEEDS]
    valid = not any(value is None for value in (*informed_rho, *informed_sign, *placebo_sign))
    mean_rho = None if not valid else float(np.mean(informed_rho))
    mean_informed_sign = None if not valid else float(np.mean(informed_sign))
    mean_placebo_sign = None if not valid else float(np.mean(placebo_sign))
    delta_sign = None if not valid else mean_informed_sign - mean_placebo_sign
    unique_targets = np.concatenate([panel[(world, SEEDS[0], "INFORMED")]["target"] for world in WORLDS])
    target_support = int(np.count_nonzero(np.abs(unique_targets) >= SIGN_THRESHOLD))
    result = {
        "status": "EARLY_FIT_ONLY_SCREEN",
        "scientific_claim": False,
        "episode_training": False,
        "fit_count": len(panel),
        "seed_metrics": seed_metrics,
        "world_metrics": world_metrics,
        "informed_world_wins": informed_world_wins,
        "informed_seed_nonnegative_worlds": nonnegative,
        "target_support_count": target_support,
        "aggregate": {
            "mean_informed_spearman": mean_rho,
            "mean_informed_sign_accuracy": mean_informed_sign,
            "mean_placebo_sign_accuracy": mean_placebo_sign,
            "informed_minus_placebo_sign_accuracy": delta_sign,
        },
        "predicates": {
            "target_support": target_support >= 24,
            "held_out_learner": bool(
                valid
                and mean_rho >= 0.20
                and mean_informed_sign >= 0.60
                and delta_sign >= 0.05
            ),
            "world_stability": bool(
                informed_world_wins >= 6 and all(count >= 5 for count in nonnegative.values())
            ),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
