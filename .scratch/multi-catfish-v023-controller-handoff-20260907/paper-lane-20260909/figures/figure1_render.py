#!/usr/bin/env python3
"""Render Figure 1 (mechanism) to PDF, SVG and PNG.

Two stacked panels over a shared off-axis-angle abscissa:
  (a) RF transmit power  p_{u,s,v}  [W]
  (b) energy efficiency  eta^N      [bit/J]

Curves: the primary architecture `a-r0` at beam occupancies U_{s,v} = 1, 2, 4,
plus the fixed-RF reference `b0`. The per-beam RF cap p^+ and the angle at
which occupancy 4 reaches it are both marked.

Symbol and terminology decisions follow `active-symbol-table-v023-20260905.md`;
see `FIGURE1-NOTES.md` for the per-label citation and for the three places where
the v0.25 successor needs vocabulary the v0.23 table does not yet carry.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import ScalarFormatter

import figure1_compute as f1

OUT = Path(__file__).resolve().parent

# --- typography -----------------------------------------------------------
# Traditional-Chinese serif to sit with the deck's Times New Roman body face.
plt.rcParams.update(
    {
        "font.family": ["Noto Serif CJK TC", "AR PL UMing TW", "serif"],
        "mathtext.fontset": "stix",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "figure.dpi": 100,
    }
)

# --- palette (extends CORE-FLOW-DRAFT.svg) --------------------------------
OCCUPANCY_COLOUR = {1: "#7DA9F0", 2: "#2563EB", 3: "#1E3A8A", 4: "#14235C"}
B0_COLOUR = "#D97706"      # amber: the reference, as in the deck's route palette
CAP_COLOUR = "#DC2626"     # red: a hard bound
MARK_COLOUR = "#15803D"    # green: an exactly-solved structural feature
INK = "#0F172A"
MUTED = "#475569"
GRID = "#E2E8F0"

LABEL_ANGLE = r"偏軸角 $\theta_{u,s,v}$（度）"
LABEL_POWER = r"RF 發射功率 $p_{u,s,v}$（W）"
LABEL_EE = r"能量效率 $\eta^{N}$（bit/J）"


def series(occupancy: int, fixed_rf: bool, n: int = 1201):
    """Dense sweep, with the exact cap-hit angle inserted so the kink is sharp."""
    edge = f1.PATTERN_EDGE_DEG
    angles = [edge * i / (n - 1) for i in range(n)]
    hit = f1.cap_hit_angle_deg(occupancy)
    if hit is not None and not fixed_rf:
        angles.append(hit)
    angles = sorted(set(angles))
    pts = [f1.evaluate(a, occupancy, fixed_rf=fixed_rf) for a in angles]
    return (
        [p.angle_deg for p in pts],
        [p.rf_power_w for p in pts],
        [p.ee_bit_per_j for p in pts],
    )


def main() -> None:
    fig, (ax_p, ax_e) = plt.subplots(
        2, 1, figsize=(7.8, 7.9), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.12], "hspace": 0.15,
                     "bottom": 0.145, "top": 0.955, "left": 0.13, "right": 0.975},
    )

    edge = f1.PATTERN_EDGE_DEG
    cap = f1.BEAM_RF_CAP_W
    hit4 = f1.cap_hit_angle_deg(4)

    # ---------------- panel (a): RF power ---------------------------------
    for occupancy in f1.OCCUPANCIES:
        x, p, _ = series(occupancy, fixed_rf=False)
        ax_p.plot(x, p, color=OCCUPANCY_COLOUR[occupancy], lw=2.0, zorder=3,
                  label=rf"a-r0，$U_{{s,v}}={occupancy}$")

    x0, p0, _ = series(1, fixed_rf=True)
    ax_p.plot(x0, p0, color=B0_COLOUR, lw=2.0, ls=(0, (5, 2)), zorder=4,
              label=r"b0 參考：$p_{u,s,v}\equiv p^{+}$")

    ax_p.axhline(cap, color=CAP_COLOUR, lw=1.1, ls=(0, (1.5, 1.5)), zorder=2)
    # Sits in the empty band above the cap line, so it cannot collide with any curve.
    ax_p.text(
        0.030, cap + 0.045, r"$p^{+}=1.65$ W（每波束 RF 輸出上限）",
        fontsize=9, color=CAP_COLOUR, va="bottom", ha="left",
    )

    ax_p.set_ylabel(LABEL_POWER, fontsize=11, color=INK)
    ax_p.set_ylim(0.0, 1.90)
    ax_p.set_title("(a) 角度驅動所需 RF 發射功率", fontsize=12, color=INK, pad=8)

    # ---------------- panel (b): energy efficiency -------------------------
    for occupancy in f1.OCCUPANCIES:
        x, _, ee = series(occupancy, fixed_rf=False)
        ax_e.plot(x, ee, color=OCCUPANCY_COLOUR[occupancy], lw=2.0, zorder=3)

    x0, _, ee0 = series(1, fixed_rf=True)
    ax_e.plot(x0, ee0, color=B0_COLOUR, lw=2.0, ls=(0, (5, 2)), zorder=4)

    ax_e.set_ylabel(LABEL_EE, fontsize=11, color=INK)
    ax_e.set_xlabel(LABEL_ANGLE, fontsize=11, color=INK)
    ax_e.set_title("(b) 對應之能量效率", fontsize=12, color=INK, pad=8)
    fmt = ScalarFormatter(useMathText=True)
    fmt.set_powerlimits((7, 7))
    ax_e.yaxis.set_major_formatter(fmt)

    # ---------------- shared marks ----------------------------------------
    for ax in (ax_p, ax_e):
        ax.axvline(hit4, color=MARK_COLOUR, lw=1.1, ls=(0, (1, 2)), zorder=2)
        ax.axvline(edge, color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=2)
        ax.set_xlim(0.0, edge * 1.005)
        ax.grid(True, color=GRID, lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#94A3B8")
        ax.tick_params(colors=MUTED, labelsize=9)

    ax_p.annotate(
        f"$U_{{s,v}}=4$ 於 {hit4:.4f}° 觸及 $p^{{+}}$",
        xy=(hit4, cap), xytext=(hit4 + 0.085, 1.16),
        fontsize=9, color=MARK_COLOUR,
        arrowprops=dict(arrowstyle="->", color=MARK_COLOUR, lw=1.0,
                        shrinkA=0, shrinkB=3),
    )
    # Pattern-edge marker on the upper panel only, to keep the lower-right of
    # panel (b) free for the cap-regime note.
    ax_p.annotate(
        r"$\theta_{3}/2$（半功率單邊角）",
        xy=(edge, 0.60), xycoords=("data", "axes fraction"),
        xytext=(-7, 0), textcoords="offset points",
        fontsize=9, color=MUTED, ha="right", va="center", rotation=90,
    )
    # Where the cap binds, RF and energy are flat and delivered bits step down.
    # Placed in the clear band between the U=2 curve and the U=4 / b0 pair.
    ax_e.annotate(
        "上限生效後：功率與能耗持平，\n改由 ACM 位元逐級下降",
        xy=(0.875, 2.07e7), xytext=(0.055, 2.31e7),
        fontsize=9, color=INK, ha="left", va="top",
        arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.0,
                        shrinkA=3, shrinkB=3),
    )

    handles, labels = ax_p.get_legend_handles_labels()
    handles.append(Line2D([], [], color=MARK_COLOUR, lw=1.1, ls=(0, (1, 2))))
    labels.append(r"$U_{s,v}=4$ 觸及上限之角度")
    leg = fig.legend(
        handles, labels, loc="lower center", ncol=3, fontsize=9.5,
        frameon=True, framealpha=1.0, edgecolor="#CBD5E1",
        borderpad=0.7, columnspacing=1.8, handlelength=2.6,
        bbox_to_anchor=(0.5, 0.005),
    )
    leg.get_frame().set_linewidth(0.8)

    fig.align_ylabels((ax_p, ax_e))

    for suffix in ("pdf", "svg", "png"):
        path = OUT / f"figure1-angle-power-ee.{suffix}"
        fig.savefig(path, dpi=400 if suffix == "png" else None, facecolor="white")
        print(f"wrote {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
