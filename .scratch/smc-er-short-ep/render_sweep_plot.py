#!/usr/bin/env python3
"""Render a previously measured SMC-ER EE sweep without training imports."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PLOT_ORDER = (
    "Baseline MODQN",
    "Full SMC-ER",
    "Full - C1",
    "Full - C2",
    "Full - C3",
)
PLOT_STYLE = {
    "Baseline MODQN": ("#6E7278", "--", "o"),
    "Full SMC-ER": ("#1F6FB4", "-", "D"),
    "Full - C1": ("#C6533D", "-.", "s"),
    "Full - C2": ("#8A5FB5", ":", "^"),
    "Full - C3": ("#2E8B4A", (0, (5, 2)), "v"),
}


def render(path: Path, summary: Sequence[Mapping[str, Any]]) -> None:
    by_arm: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in summary:
        by_arm[str(row["arm"])].append(row)
    if not by_arm:
        raise ValueError("sweep summary has no rows")

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
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.summary.read_text(encoding="utf-8"))
    render(args.output, payload["summary"])
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
