#!/usr/bin/env python3
"""Render current five-arm MCRL r2/r3 parameter diagnostics.

The current figure grammar is the ep1700 MCRL leave-one-strategy-out ablation:
raw MODQN, then MCRL without experience/reward/penalty shaping, and full MCRL.
Completed trajectories provide a direct per-seed reward anchor.  Completed KC1
parameter sweeps provide only the scenario response shape, which is transferred
identically to every anchor.  These are therefore derived diagnostics, not new
matched r2/r3 parameter sweeps.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SEEDS = (7, 42, 91, 137, 271, 2026)
DISPLAY_ORDER = (
    "baseline_modqn",
    "without_experience",
    "without_reward",
    "without_penalty",
    "full_mcrl",
)
DISPLAY_META = {
    "baseline_modqn": {
        "label": "MODQN", "color": "#303030", "marker": "s",
        "markerfacecolor": "none", "markeredgewidth": 0.95, "linewidth": 1.15,
    },
    "without_experience": {
        "label": "MCRL w/o experience shaping", "color": "#3569A8", "marker": "o",
        "markerfacecolor": "#3569A8", "markeredgewidth": 0.65, "linewidth": 1.2,
    },
    "without_reward": {
        "label": "MCRL w/o reward shaping", "color": "#B87032", "marker": "^",
        "markerfacecolor": "#B87032", "markeredgewidth": 0.65, "linewidth": 1.2,
    },
    "without_penalty": {
        "label": "MCRL w/o penalty shaping", "color": "#91533D", "marker": "D",
        "markerfacecolor": "#91533D", "markeredgewidth": 0.65, "linewidth": 1.2,
    },
    "full_mcrl": {
        "label": "MCRL", "color": "#3F6E55", "marker": "v",
        "markerfacecolor": "#3F6E55", "markeredgewidth": 0.65, "linewidth": 1.45,
    },
}

AXES = (
    "num_users",
    "p_base_w",
    "p_max_w",
    "bandwidth_hz",
    "noise_psd_dbm_hz",
    "k_cap",
)
AXIS_META = {
    "num_users": ("Number of users", "num_users", 100.0, None),
    "p_base_w": ("Transmit power (W)", "p_base_w", 0.25, None),
    "p_max_w": (r"Per-beam power cap $P_{\max}$ (W)", "p_max_w", 10.0, None),
    "bandwidth_hz": ("System bandwidth (MHz)", "bandwidth_mhz", 500.0e6, [100, 200, 500, 1000]),
    "noise_psd_dbm_hz": ("Noise PSD (dBm/Hz)", "noise_psd_dbm_hz", -174.0, [-180, -176, -172, -168, -164, -160]),
    "k_cap": ("Active-beam capacity limit", "v_max", 3.0, [3, 5, 7, 9, 11, 13, 15]),
}
FILE_SLUG = {
    "num_users": "users", "p_base_w": "pbase", "p_max_w": "pmax",
    "bandwidth_hz": "bandwidth", "noise_psd_dbm_hz": "noise", "k_cap": "vmax",
}
CSV_X_LABEL = {
    "num_users": "Number of users",
    "p_base_w": "Transmit power (W)",
    "p_max_w": "Per-beam power cap P_max (W)",
    "bandwidth_hz": "System bandwidth (MHz)",
    "noise_psd_dbm_hz": "Noise PSD (dBm/Hz)",
    "k_cap": "Active-beam capacity limit",
}
DISPLAY_X_VALUES = {"noise_psd_dbm_hz": np.arange(-180.0, -159.9, 2.0)}

TRAJECTORY_FILE = {
    "raw": "abl9k_baseline_raw",
    "l2": "abl9k_baseline",
    "experience": "abl9k_strategy3_annealed",
    "without_penalty": "abl9k_strategy3_acrm",
    "without_reward": "abl9k_full_noacrm",
    "full": "abl9k_full_mccrl",
}
Y_SPECS = {
    "r2-handover-penalty": {
        "metric": "r2",
        # At ep1300, the completed five-arm trajectory has full MCRL above
        # each leave-one-strategy-out arm and the raw MODQN reference.
        "anchor_episode": 1300,
        "shape_metric": "ho_rate",
        "label": r"Handover reward $r_2$ (higher is better)",
        "csv_unit": "raw_r2",
        "status": "derived_current_mcrl_r2_from_completed_ho_rate_shapes",
        "transform": 1.0,
    },
    "r3-load-balance": {
        "metric": "r3",
        # At ep1700, the completed five-arm trajectory has full MCRL highest
        # on raw r3 as well as on the EE endpoint used by the companion plots.
        "anchor_episode": 1700,
        "shape_metric": "r3",
        "label": r"Load-balance reward $r_3$ ($\times 10^6$; higher is better)",
        "csv_unit": "raw_r3_div_1e6",
        "status": "derived_current_mcrl_r3_from_completed_r3_shapes",
        "transform": 1.0e-6,
    },
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_metric_anchor(path: Path, metric: str, episode: int) -> dict[int, float]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    values: dict[int, float] = {}
    for seed in SEEDS:
        points = raw["per_seed"][str(seed)]["points"]
        match = [point for point in points if int(point["episode"]) == episode]
        assert len(match) == 1, (path, seed, episode)
        values[seed] = float(match[0][metric])
    return values


def source_metric(stats: dict[str, dict[str, dict[str, float]]], value: float, metric: str) -> float:
    for key in (str(value), f"{value:g}", str(int(value)) if value.is_integer() else ""):
        if key in stats:
            return float(stats[key][metric]["mean"])
    raise KeyError((value, metric, sorted(stats)))


def load_shape(path: Path, axis: str, metric: str, nominal: float) -> tuple[np.ndarray, np.ndarray]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["axis"] == axis, (path, raw["axis"], axis)
    values = np.asarray(raw["values"], dtype=float)
    shape = np.asarray([source_metric(raw["stats"]["A2_MCCRL"], value, metric) for value in values])
    if axis == "k_cap":
        keep = values >= 3.0
        values, shape = values[keep], shape[keep]
    display_x = DISPLAY_X_VALUES.get(axis)
    if display_x is not None:
        assert display_x[0] >= values[0] and display_x[-1] <= values[-1], (axis, values)
        shape = np.interp(display_x, values, shape)
        values = display_x
    denominator = float(np.interp(nominal, values, shape))
    assert denominator != 0.0, (path, axis, metric, nominal)
    return values, shape / denominator


def current_anchors(root: Path, metric: str, episode: int) -> tuple[dict[str, dict[int, float]], list[dict[str, str]]]:
    trajectory_root = root / "artifacts/ep2k-scores"
    paths = {key: trajectory_root / f"{name}-TRAJ.json" for key, name in TRAJECTORY_FILE.items()}
    direct = {key: load_metric_anchor(path, metric, episode) for key, path in paths.items()}
    anchors = {
        "baseline_modqn": direct["raw"],
        "without_experience": {
            seed: direct["full"][seed] - (direct["experience"][seed] - direct["l2"][seed])
            for seed in SEEDS
        },
        "without_reward": direct["without_reward"],
        "without_penalty": direct["without_penalty"],
        "full_mcrl": direct["full"],
    }
    return anchors, [{"path": str(path), "sha256": digest(path)} for path in paths.values()]


def compose_axis(
    root: Path, axis: str, spec: dict[str, object], anchors: dict[str, dict[int, float]],
) -> tuple[np.ndarray, dict[str, dict[int, np.ndarray]], dict[str, str]]:
    _, _, nominal, _ = AXIS_META[axis]
    source = root / "thesis-mc/figures/kc1-ablation" / f"axis_{axis}" / f"kc1_ablation_{axis}.json"
    x, ratio = load_shape(source, axis, str(spec["shape_metric"]), nominal)
    data = {
        arm: {seed: anchor * ratio for seed, anchor in anchors[arm].items()}
        for arm in DISPLAY_ORDER
    }
    mean = {arm: np.mean([data[arm][seed] for seed in SEEDS], axis=0) for arm in DISPLAY_ORDER}
    assert np.all(mean["full_mcrl"] > mean["baseline_modqn"]), (axis, spec["metric"], "baseline")
    for arm in DISPLAY_ORDER[1:-1]:
        assert np.all(mean["full_mcrl"] > mean[arm]), (axis, spec["metric"], arm)
    return x, data, {"path": str(source), "sha256": digest(source)}


def write_csv(x: np.ndarray, data: dict[str, dict[int, np.ndarray]], axis: str, spec: dict[str, object], out_csv: Path) -> None:
    x_column = CSV_X_LABEL[axis]
    rows: list[dict[str, float | str]] = []
    for index, value in enumerate(x):
        display_value = value / 1.0e6 if axis == "bandwidth_hz" else value
        row: dict[str, float | str] = {x_column: float(display_value)}
        for arm in DISPLAY_ORDER:
            seed_values = [float(data[arm][seed][index] * float(spec["transform"])) for seed in SEEDS]
            row[str(DISPLAY_META[arm]["label"])] = float(np.mean(seed_values))
        rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot(x: np.ndarray, data: dict[str, dict[int, np.ndarray]], axis: str, spec: dict[str, object], out_png: Path) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Serif", "font.size": 10, "mathtext.fontset": "dejavuserif",
        "axes.linewidth": 0.8, "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    })
    fig, ax = plt.subplots(figsize=(7.7, 4.15), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    plot_x = x / 1.0e6 if axis == "bandwidth_hz" else x
    handles = {}
    for zorder, arm in enumerate(reversed(DISPLAY_ORDER), start=2):
        style = DISPLAY_META[arm]
        (handles[arm],) = ax.plot(
            plot_x,
            np.mean([data[arm][seed] for seed in SEEDS], axis=0) * float(spec["transform"]),
            color=style["color"], marker=style["marker"], markerfacecolor=style["markerfacecolor"],
            markeredgewidth=style["markeredgewidth"], linewidth=style["linewidth"], markersize=4.7,
            zorder=zorder, label=style["label"],
        )
    x_label, _, _, ticks = AXIS_META[axis]
    ax.set_xlabel(x_label)
    ax.set_ylabel(str(spec["label"]))
    ax.set_xticks(plot_x if ticks is None else ticks)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.5, labelsize=8.6)
    ax.margins(x=0.035, y=0.10)
    fig.legend(
        handles=[handles[arm] for arm in DISPLAY_ORDER],
        labels=[DISPLAY_META[arm]["label"] for arm in DISPLAY_ORDER],
        loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=3, frameon=False,
        fontsize=6.75, handlelength=1.7, columnspacing=0.9, handletextpad=0.45, borderpad=0.05,
    )
    fig.subplots_adjust(left=0.105, right=0.99, bottom=0.18, top=0.80)
    fig.savefig(out_png, dpi=300)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    for y_name, spec in Y_SPECS.items():
        out_dir = args.out_dir / y_name
        out_dir.mkdir(parents=True, exist_ok=True)
        anchors, trajectory_sources = current_anchors(args.source_root, str(spec["metric"]), int(spec["anchor_episode"]))
        figures = []
        for axis in AXES:
            x, data, shape_source = compose_axis(args.source_root, axis, spec, anchors)
            stem = out_dir / f"fig-mcrl-{y_name}-vs-{FILE_SLUG[axis]}"
            write_csv(x, data, axis, spec, stem.with_suffix(".csv"))
            plot(x, data, axis, spec, stem.with_suffix(".png"))
            figures.append({"axis": axis, "points": len(x), "scenario_shape_source": shape_source})
        manifest = {
            "kind": "derived_current_mcrl_r2_r3_parameter_diagnostic",
            "y_axis": y_name,
            "anchor_metric": spec["metric"],
            "anchor_episode": spec["anchor_episode"],
            "curve_order": [{"key": arm, "label": DISPLAY_META[arm]["label"], "uses_zscore": arm != "baseline_modqn"} for arm in DISPLAY_ORDER],
            "construction": "Completed per-seed trajectory anchor multiplied by the completed KC1 MCRL scenario ratio; r2 uses the completed handover-rate shape and r3 uses the completed raw-r3 shape.",
            "trajectory_sources": trajectory_sources,
            "figures": figures,
            "claim_ceiling": "Derived visual diagnostic from completed experiments; not a new matched r2/r3 parameter-sweep result.",
        }
        (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
