#!/usr/bin/env python3
"""Render the CH5 result figures from matrix-probe receipts.

    make_ch5_figures.py --receipts <dir> --out <dir> --label <LABEL>

    LABEL ∈ {PILOT_NOT_CLAIM, MATRIX, CONFIRMATORY}

Produces, in `--out`:

    figure3-physics-certificates.{pdf,svg,png} + figure3-physics-certificates.csv
    figure4-mechanism.{pdf,svg,png}            + figure4-mechanism.csv
    figure5-learned-contrasts.{pdf,svg,png}    + figure5-learned-contrasts.csv

Figure 3 is the a-r0 regime map of physics certificates; Figure 4 is the
mechanism decomposition; Figure 5 is the learned FULL-vs-DROP contrast panel
that the confirmatory track fills in later.

Typography, palette and label style follow `figure1_render.py`.  Every plotted
point is written to the sidecar CSV together with the v1.7 erratum item 6
disclosure for its interval.  A missing receipt field is a hard error naming
the field: this pipeline never silently drops a series.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from ch5_receipts import (
    ANCHORINGS,
    ARM_S0,
    FACTORS,
    FIG3_J1_QUANTITY,
    FIG3_QUANTITIES,
    FIG5_QUANTITIES,
    LABELS,
    PRIMARY_SETTING,
    QOS_CO_PRIMARIES,
    Diagnostics,
    Interval,
    Mechanism,
    MergeReceipt,
    ReceiptFieldError,
    SettingCertificates,
    load_certificates,
    load_diagnostics,
    load_interval,
    load_mechanism,
    load_merge,
    load_qos,
    load_units,
    pluck,
)

# --------------------------------------------------------------------------
# Typography and palette — the deck invariant, as in figure1_render.py.
# --------------------------------------------------------------------------

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

INK = "#0F172A"
MUTED = "#475569"
GRID = "#E2E8F0"
RULE = "#94A3B8"

POINT = "#1E3A8A"          # point estimate
BAR = "#2563EB"            # primary interval
LIGHT = "#7DA9F0"          # secondary / seedwise
CEILING = "#94A3B8"        # ceiling arms and non-decisive quantities
MARGIN = "#DC2626"         # a hard bound
DIAG = "#D97706"           # diagnostics, visually subordinate

VERDICT_COLOUR = {
    "ADMIT_FULL": "#16A34A",
    "ADMIT_C1C2": "#D97706",
    "NOT_ADMITTED": "#DC2626",
}

BANNER_COLOUR = {
    "PILOT_NOT_CLAIM": "#DC2626",
    "MATRIX": "#D97706",
    "CONFIRMATORY": "#16A34A",
}

BANNER_TEXT = {
    "PILOT_NOT_CLAIM": (
        "PILOT_NOT_CLAIM　試辦數據，非主張證據："
        "不得進入論文、不得選定任何組態、制度、邊際、種子數或封存規則"
    ),
    "MATRIX": (
        "MATRIX　物理矩陣探測結果：僅 a-r0 為主要設定，"
        "其餘設定為探索性敏感度分析，不單獨宣稱發現"
    ),
}

# --------------------------------------------------------------------------
# Chinese labels.  Terminology follows the two figure specifications and
# `active-symbol-table-v023-20260905.md`; the successor-vocabulary additions
# are listed in CH5-FIGURE-PIPELINE-README.md §4.
# --------------------------------------------------------------------------

L_EE_AXIS = "相對載波基準之合併能量效率 $\\eta^{N}$（%，相對）"
L_ZERO = "無效應"
L_MARGIN_HALF = "δ = +0.5 %（實務邊際）"
L_MARGIN_ONE = "+1 %（S0 載重門檻）"
L_UNCERTIFIED = "未取得終止證明"
L_ANCHOR_FRACTION = "錨點比例（%）"

FIG3_TITLE = "圖 3　物理證書：a-r0 制度地圖"
FIG3_A = "(a) 各設定之物理證書與其區間"
FIG3_B = "(b) J1 − U_all（位元，於校準價格）"
FIG3_C = "(c) 診斷：完整服務可用度與功率上限觸及率"
FIG3_D = "(d) 准入三分結果"

FIG4_TITLE = "圖 4　機制：淨避碰價值之分解與名目對實現"
FIG4_A = "(a) 淨避碰價值分解（未截斷，單位 κ）"
FIG4_B = "(b) 加性反轉頻率"
FIG4_C = "(c) 每錨點之名目預測與實現結果（單位 κ）"

FIG5_TITLE = "圖 5　學習對比：FULL 對各 DROP 與對齊之 QoS 邊際"
FIG5_A = "(a) FULL 對各 DROP 之學習對比"
FIG5_B = "(b) 對齊之 QoS 共同主要指標與其前瞻性邊際"

L_CA_NET = "淨避碰價值 $V_{CA}$"
L_CA_INTERACTION = "已避免之交互作用損失"
L_CA_SINGLETON = "已犧牲之單體價值"

ANCHORING_LABEL = {
    "carrier_a0": "錨定於載波 a⁰",
    "reanchored_at_s_uni": "重錨定於 S_UNI 局部最適",
}

DIAG_NOTE = "診斷量，不得升格為主張（v1.6 §4）"


# --------------------------------------------------------------------------
# CSV sidecar.
# --------------------------------------------------------------------------

CSV_COLUMNS = (
    "figure",
    "panel",
    "setting",
    "series_key",
    "series_label_zh",
    "point_label",
    "value",
    "lo",
    "hi",
    "unit",
    "margin",
    "margin_pass",
    "decisive",
    "claim_label",
    "claim_classification",
    "admission_trichotomy",
    "source_field",
    # v1.7 erratum item 6 disclosure, one row per plotted interval.
    "interval_contrast",
    "endpoint",
    "interval_units",
    "decision_margin",
    "method",
    "sidedness",
    "nominal_level",
    "coverage_type",
    "n_tle_dates",
    "n_learner_seeds",
    "panel_scope",
    "measured_coverage_two_sided",
    "measured_coverage_two_sided_mc",
    "measured_coverage_one_sided",
    "measured_coverage_one_sided_mc",
)


class Sidecar:
    """Accumulates every plotted point for the `.csv` beside each figure."""

    def __init__(self, figure: str, label: str) -> None:
        self.figure = figure
        self.label = label
        self.rows: list[dict[str, Any]] = []

    def add(self, **kwargs: Any) -> None:
        unknown = set(kwargs) - set(CSV_COLUMNS)
        if unknown:
            raise KeyError(f"sidecar column(s) not declared: {sorted(unknown)}")
        row = {column: "" for column in CSV_COLUMNS}
        row["figure"] = self.figure
        row["claim_label"] = self.label
        row.update(kwargs)
        self.rows.append(row)

    def add_interval(
        self,
        interval: Interval,
        *,
        panel: str,
        setting: str,
        source_field: str,
        point_label: str = "",
        scale: float = 1.0,
        **extra: Any,
    ) -> None:
        self.add(
            panel=panel,
            setting=setting,
            series_key=interval.key,
            series_label_zh=interval.label_zh,
            point_label=point_label,
            value=interval.point * scale,
            lo=interval.lo * scale,
            hi=interval.hi * scale,
            unit=interval.unit,
            margin="" if interval.margin is None else interval.margin * scale,
            margin_pass="" if interval.margin_pass is None else interval.margin_pass,
            decisive=interval.decisive,
            source_field=source_field,
            **interval.report.as_csv_columns(),
            **extra,
        )

    def write(self, path: Path) -> Path:
        if not self.rows:
            raise RuntimeError(f"{path}: refusing to write an empty sidecar")
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
            writer.writeheader()
            writer.writerows(self.rows)
        return path


# --------------------------------------------------------------------------
# Shared drawing helpers.
# --------------------------------------------------------------------------


def style_axes(ax: plt.Axes) -> None:
    ax.grid(True, axis="x", color=GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=8.5)


def draw_interval(
    ax: plt.Axes,
    y: float,
    interval: Interval,
    *,
    scale: float = 100.0,
    decisive: bool | None = None,
    hatched: bool = False,
) -> None:
    """One point with its bar.  The lower end carries the decision, so it is
    drawn with a heavier cap: the sealed rule reads the 2.5th percentile."""

    is_decisive = interval.decisive if decisive is None else decisive
    colour = BAR if is_decisive else CEILING
    lo, hi, point = interval.lo * scale, interval.hi * scale, interval.point * scale
    ax.plot([lo, hi], [y, y], color=colour, lw=2.2, solid_capstyle="butt", zorder=3)
    # The decision end.
    ax.plot([lo, lo], [y - 0.22, y + 0.22], color=colour, lw=3.0, zorder=4)
    ax.plot([hi, hi], [y - 0.13, y + 0.13], color=colour, lw=1.4, zorder=4)
    ax.plot(
        [point], [y], marker="o", ms=5.0,
        color=POINT if is_decisive else CEILING,
        markeredgecolor="white", markeredgewidth=0.6, zorder=5,
    )
    if hatched:
        ax.add_patch(
            Rectangle(
                (lo, y - 0.34), hi - lo, 0.68,
                facecolor="none", edgecolor=MARGIN, hatch="////", lw=0.8, zorder=2,
            )
        )


def draw_banner(fig: plt.Figure, label: str) -> None:
    """The label banner, rendered visibly whenever the label is not
    CONFIRMATORY.  A pilot artefact must be unmistakable at a glance."""

    if label == "CONFIRMATORY":
        return
    colour = BANNER_COLOUR[label]
    fig.patches.append(
        Rectangle(
            (0.0, 0.972), 1.0, 0.028, transform=fig.transFigure,
            facecolor=colour, edgecolor="none", zorder=50, figure=fig,
        )
    )
    fig.text(
        0.5, 0.9858, BANNER_TEXT[label], ha="center", va="center",
        fontsize=9.5, color="white", zorder=51,
    )
    if label == "PILOT_NOT_CLAIM":
        fig.text(
            0.5, 0.47, "PILOT_NOT_CLAIM", ha="center", va="center",
            fontsize=64, color=colour, alpha=0.10, rotation=28,
            zorder=1, fontweight="bold",
        )


def save(fig: plt.Figure, out: Path, stem: str) -> list[Path]:
    written = []
    for suffix in ("pdf", "svg", "png"):
        path = out / f"{stem}.{suffix}"
        fig.savefig(path, dpi=400 if suffix == "png" else None, facecolor="white")
        written.append(path)
    plt.close(fig)
    return written


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}"


# --------------------------------------------------------------------------
# Label / receipt consistency.
# --------------------------------------------------------------------------


def check_label(
    label: str, merge: MergeReceipt, certificates: Sequence[SettingCertificates]
) -> None:
    """Refuse the combinations the sealed rules forbid outright."""

    if label not in LABELS:
        raise ReceiptFieldError(f"unknown label {label!r}; expected one of {list(LABELS)}")
    classifications = {c.setting: c.claim_classification for c in certificates}
    primary = classifications.get(PRIMARY_SETTING)
    if primary is None:
        raise ReceiptFieldError(
            f"{merge.where}: the primary setting '{PRIMARY_SETTING}' is absent from "
            "'uncertainty.per_cell'; the regime map is anchored on it"
        )
    if primary != "PRIMARY":
        raise ReceiptFieldError(
            f"{merge.where}: 'uncertainty.per_cell.{PRIMARY_SETTING}."
            f"claim_classification' is {primary!r}, expected 'PRIMARY'"
        )
    if label == "CONFIRMATORY":
        training = pluck(merge.payload, "training", where=merge.where)
        if bool(training) is not True:
            raise ReceiptFieldError(
                f"{merge.where}: --label CONFIRMATORY was requested but 'training' is "
                f"{training!r}; a matrix probe receipt cannot carry a confirmatory "
                "claim.  Re-run with --label MATRIX."
            )


# --------------------------------------------------------------------------
# Figure 3 — physics certificates, the a-r0 regime map.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SettingBlock:
    setting: str
    certificates: SettingCertificates
    intervals: tuple[Interval, ...]
    j1: Interval
    diagnostics: Diagnostics


def collect_fig3(merge: MergeReceipt, units: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[SettingBlock]:
    ordered = [PRIMARY_SETTING] + [c for c in merge.cell_order if c != PRIMARY_SETTING]
    blocks = []
    for cell in ordered:
        blocks.append(
            SettingBlock(
                setting=cell,
                certificates=load_certificates(merge, cell),
                intervals=tuple(load_interval(merge, cell, q) for q in FIG3_QUANTITIES),
                j1=load_interval(merge, cell, FIG3_J1_QUANTITY),
                diagnostics=load_diagnostics(units[cell], cell, ARM_S0),
            )
        )
    return blocks


def s_uni_certified(merge: MergeReceipt, cell: str) -> bool:
    state = pluck(
        merge.payload,
        f"uncertainty.per_cell.{cell}.physics_certificates.s_uni_termination_certificate",
        where=merge.where, kind=str,
    )
    if state not in {"PRESENT", "ABSENT"}:
        raise ReceiptFieldError(
            f"{merge.where}: 'uncertainty.per_cell.{cell}.physics_certificates."
            f"s_uni_termination_certificate' is {state!r}; expected PRESENT or ABSENT"
        )
    return state == "PRESENT"


def figure3(
    merge: MergeReceipt,
    units: Mapping[str, Sequence[Mapping[str, Any]]],
    out: Path,
    label: str,
) -> list[Path]:
    blocks = collect_fig3(merge, units)
    sidecar = Sidecar("figure3", label)

    n_rows = sum(len(b.intervals) for b in blocks)
    height = max(8.4, 0.30 * n_rows + 4.3)
    fig = plt.figure(figsize=(13.6, height))
    gs = fig.add_gridspec(
        2, 3, width_ratios=[2.35, 0.95, 1.05], height_ratios=[1.0, 0.20],
        left=0.155, right=0.982, top=0.918, bottom=0.075, wspace=0.30, hspace=0.30,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    ax_d = fig.add_subplot(gs[1, :])

    # ---- panel (a): the certificate forest ------------------------------
    y = 0.0
    ticks: list[float] = []
    tick_labels: list[str] = []
    block_spans: list[tuple[str, float, float, str]] = []
    for block in blocks:
        top = y
        certified = s_uni_certified(merge, block.setting)
        for interval in block.intervals:
            hatched = interval.key.endswith("S_UNI") and not certified
            draw_interval(ax_a, y, interval, hatched=hatched)
            ticks.append(y)
            tick_labels.append(interval.label_zh)
            if hatched:
                ax_a.text(
                    interval.hi * 100.0, y + 0.34, L_UNCERTIFIED,
                    fontsize=7.2, color=MARGIN, va="bottom", ha="left",
                )
            sidecar.add_interval(
                interval, panel="a", setting=block.setting, scale=100.0,
                source_field=(
                    f"uncertainty.per_cell.{block.setting}.contrasts.{interval.key}"
                ),
                claim_classification=block.certificates.claim_classification,
                admission_trichotomy=block.certificates.trichotomy,
                point_label=(
                    L_UNCERTIFIED if hatched else ("載重" if interval.decisive else "上界")
                ),
            )
            y += 1.0
        block_spans.append((block.setting, top - 0.5, y - 0.5, block.certificates.trichotomy))
        y += 0.9

    ax_a.axvline(0.0, color=RULE, lw=1.0, zorder=1)
    ax_a.axvline(0.5, color=MARGIN, lw=1.1, ls=(0, (5, 2)), zorder=2)
    ax_a.axvline(1.0, color=MARGIN, lw=1.1, ls=(0, (1.5, 1.5)), zorder=2)
    ax_a.set_yticks(ticks)
    ax_a.set_yticklabels(tick_labels, fontsize=8.2, color=INK)
    ax_a.set_ylim(y - 0.9, -0.9)
    ax_a.set_xlabel(L_EE_AXIS, fontsize=10, color=INK)
    ax_a.set_title(FIG3_A, fontsize=11.5, color=INK, pad=9, loc="left")
    style_axes(ax_a)

    # Setting bands, so the reader can see which rows belong together.
    for index, (setting, lo_y, hi_y, verdict) in enumerate(block_spans):
        if index % 2 == 0:
            ax_a.axhspan(lo_y, hi_y, color="#F8FAFC", zorder=0)
        ax_a.text(
            -0.012, (lo_y + hi_y) / 2.0, setting,
            transform=ax_a.get_yaxis_transform(), fontsize=9.5, color=INK,
            ha="right", va="center", rotation=90, fontweight="bold",
        )
        ax_a.axhline(hi_y + 0.45, color=GRID, lw=0.8, zorder=1)

    ax_a.legend(
        handles=[
            Line2D([], [], color=BAR, lw=2.2, marker="o", ms=5,
                   markerfacecolor=POINT, markeredgecolor="white", label="載重證書（決策端為下界）"),
            Line2D([], [], color=CEILING, lw=2.2, marker="o", ms=5,
                   markerfacecolor=CEILING, markeredgecolor="white", label="天花板／非決策量"),
            Line2D([], [], color=MARGIN, lw=1.1, ls=(0, (5, 2)), label=L_MARGIN_HALF),
            Line2D([], [], color=MARGIN, lw=1.1, ls=(0, (1.5, 1.5)), label=L_MARGIN_ONE),
            Line2D([], [], color=RULE, lw=1.0, label=L_ZERO),
        ],
        loc="lower left", bbox_to_anchor=(0.0, 1.055), ncol=3, fontsize=8,
        frameon=False, columnspacing=1.5, handlelength=2.4,
    )

    # ---- panel (b): J1 − U_all, own units, explicitly not decisive -------
    y = 0.0
    bticks, blabels = [], []
    for block in blocks:
        draw_interval(ax_b, y, block.j1, scale=1.0, decisive=False)
        bticks.append(y)
        blabels.append(block.setting)
        sidecar.add_interval(
            block.j1, panel="b", setting=block.setting, scale=1.0,
            source_field=(
                f"uncertainty.per_cell.{block.setting}.contrasts.{block.j1.key}"
            ),
            claim_classification=block.certificates.claim_classification,
            admission_trichotomy=block.certificates.trichotomy,
            point_label="資訊性，不具決策性",
        )
        y += 1.0
    ax_b.axvline(0.0, color=RULE, lw=1.0, zorder=1)
    ax_b.set_yticks(bticks)
    ax_b.set_yticklabels(blabels, fontsize=8.2, color=INK)
    ax_b.set_ylim(y - 0.5, -0.5)
    ax_b.set_xlabel("J1 − U_all（位元）", fontsize=9.5, color=INK)
    ax_b.set_title(FIG3_B, fontsize=11.5, color=INK, pad=9, loc="left")
    ax_b.text(
        0.0, 1.012, FIG3_J1_QUANTITY.note_zh, transform=ax_b.transAxes,
        fontsize=7.8, color=MUTED, va="bottom",
    )
    style_axes(ax_b)

    # ---- panel (c): diagnostics, subordinate -----------------------------
    y = 0.0
    cticks, clabels = [], []
    for block in blocks:
        diag = block.diagnostics
        ax_c.barh(y + 0.19, diag.availability * 100.0, height=0.34,
                  color=DIAG, alpha=0.75, zorder=3)
        ax_c.barh(y - 0.19, diag.cap_hit_share * 100.0, height=0.34,
                  color=CEILING, alpha=0.85, zorder=3)
        cticks.append(y)
        clabels.append(block.setting)
        for key, zh, value, num, den in (
            ("availability", "完整服務可用度", diag.availability,
             diag.availability_served, diag.availability_opportunities),
            ("rf_cap_share", "功率上限觸及率", diag.cap_hit_share,
             diag.cap_hits, diag.transmission_observations),
        ):
            sidecar.add(
                panel="c", setting=block.setting, series_key=f"{ARM_S0}:{key}",
                series_label_zh=zh, value=value * 100.0, unit="pct",
                decisive=False, point_label=DIAG_NOTE,
                claim_classification=block.certificates.claim_classification,
                admission_trichotomy=block.certificates.trichotomy,
                source_field=(
                    f"units/{block.setting}/world-*.json:failure_analysis.arms."
                    f"{ARM_S0}."
                    + ("qos_additive.availability_served / "
                       "qos_additive.availability_opportunities"
                       if key == "availability"
                       else "rf_cap_hits / rf_transmission_observations")
                ),
                method=f"ratio of sums over worlds (numerator={num}, denominator={den})",
            )
        y += 1.0
    ax_c.set_yticks(cticks)
    ax_c.set_yticklabels(clabels, fontsize=8.2, color=INK)
    ax_c.set_ylim(y - 0.5, -0.5)
    ax_c.set_xlim(0, 100)
    ax_c.set_xlabel("比例（%）", fontsize=9.5, color=INK)
    ax_c.set_title(FIG3_C, fontsize=11.5, color=INK, pad=9, loc="left")
    ax_c.text(
        0.0, 1.012, f"{DIAG_NOTE}；臂 = {ARM_S0}", transform=ax_c.transAxes,
        fontsize=7.8, color=MUTED, va="bottom",
    )
    ax_c.legend(
        handles=[
            Patch(facecolor=DIAG, alpha=0.75, label="完整服務可用度"),
            Patch(facecolor=CEILING, alpha=0.85, label="功率上限觸及率"),
        ],
        loc="lower right", fontsize=7.8, frameon=True, framealpha=0.95,
        edgecolor="#CBD5E1",
    )
    style_axes(ax_c)

    # ---- panel (d): the admission trichotomy -----------------------------
    ax_d.set_axis_off()
    ax_d.set_title(FIG3_D, fontsize=11.5, color=INK, pad=6, loc="left")
    width = 1.0 / max(1, len(blocks))
    for index, block in enumerate(blocks):
        cert = block.certificates
        colour = VERDICT_COLOUR[cert.trichotomy]
        ax_d.add_patch(
            Rectangle(
                (index * width + 0.004, 0.30), width - 0.008, 0.46,
                transform=ax_d.transAxes, facecolor=colour, alpha=0.14,
                edgecolor=colour, lw=1.2, clip_on=False,
            )
        )
        ax_d.text(
            index * width + width / 2.0, 0.645, block.setting,
            transform=ax_d.transAxes, ha="center", va="center",
            fontsize=9.5, color=INK, fontweight="bold",
        )
        ax_d.text(
            index * width + width / 2.0, 0.455, cert.trichotomy,
            transform=ax_d.transAxes, ha="center", va="center",
            fontsize=9.0, color=colour, fontweight="bold",
        )
        ax_d.text(
            index * width + width / 2.0, 0.16, cert.trichotomy_reason_zh,
            transform=ax_d.transAxes, ha="center", va="top",
            fontsize=6.9, color=MUTED, wrap=True,
        )
        sidecar.add(
            panel="d", setting=block.setting, series_key="admission",
            series_label_zh="准入三分結果", point_label=cert.trichotomy_reason_zh,
            value=cert.trichotomy, unit="verdict",
            claim_classification=cert.claim_classification,
            admission_trichotomy=cert.trichotomy,
            source_field=(
                "training_admission.certificates"
                if cert.is_primary
                else f"training_admission.regime_sensitivity_certificates.{block.setting}"
            ),
            method=f"probe decision={cert.decision}; trichotomy derived per 宣告 v1.9 item 6",
        )
    ax_d.text(
        0.0, -0.10,
        "ADMIT_C1C2 並非 C3 失敗：訓練仍獲准入，C3 以已評估層帶入，"
        "其學習陳述明確標註缺少神諭證書。",
        transform=ax_d.transAxes, fontsize=7.8, color=MUTED, va="top",
    )

    # ---- the erratum item 6 disclosure, adjacent to the intervals --------
    fig.text(
        0.155, 0.0125, blocks[0].intervals[0].report.banner_zh(),
        fontsize=7.6, color=INK, va="bottom", linespacing=1.5,
    )
    fig.suptitle(FIG3_TITLE, fontsize=14, color=INK, x=0.155, ha="left", y=0.978)
    draw_banner(fig, label)

    paths = save(fig, out, "figure3-physics-certificates")
    paths.append(sidecar.write(out / "figure3-physics-certificates.csv"))
    return paths


# --------------------------------------------------------------------------
# Figure 4 — mechanism.
# --------------------------------------------------------------------------


def figure4(
    merge: MergeReceipt,
    units: Mapping[str, Sequence[Mapping[str, Any]]],
    out: Path,
    label: str,
) -> list[Path]:
    mech: Mechanism = load_mechanism(merge, units[PRIMARY_SETTING], PRIMARY_SETTING)
    sidecar = Sidecar("figure4", label)

    fig = plt.figure(figsize=(13.6, 5.9))
    gs = fig.add_gridspec(
        1, 3, width_ratios=[1.28, 0.80, 1.10],
        left=0.075, right=0.982, top=0.845, bottom=0.155, wspace=0.30,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    # ---- panel (a): the unclipped decomposition, reported twice ----------
    ys = []
    for index, anchoring in enumerate(ANCHORINGS):
        totals = mech.totals_by_anchoring[anchoring]
        avoided = totals["interaction_loss_avoided_kappa"]
        sacrificed = totals["singleton_value_sacrificed_kappa"]
        net = totals["collision_avoidance_value_kappa"]
        y = float(index)
        ys.append(y)
        ax_a.barh(y + 0.17, avoided, height=0.30, color=BAR, alpha=0.85,
                  zorder=3, label=L_CA_INTERACTION if index == 0 else None)
        ax_a.barh(y - 0.17, sacrificed, height=0.30, color=DIAG, alpha=0.85,
                  zorder=3, label=L_CA_SINGLETON if index == 0 else None)
        ax_a.plot([net], [y], marker="D", ms=8.0, color=POINT,
                  markeredgecolor="white", markeredgewidth=0.8, zorder=5,
                  label=L_CA_NET if index == 0 else None)
        for key, zh, value in (
            ("interaction_loss_avoided_kappa", L_CA_INTERACTION, avoided),
            ("singleton_value_sacrificed_kappa", L_CA_SINGLETON, sacrificed),
            ("collision_avoidance_value_kappa", L_CA_NET, net),
        ):
            sidecar.add(
                panel="a", setting=PRIMARY_SETTING, series_key=f"{anchoring}:{key}",
                series_label_zh=zh, point_label=ANCHORING_LABEL[anchoring],
                value=value, unit="kappa", decisive=False,
                source_field=(
                    f"units/{PRIMARY_SETTING}/world-*.json:"
                    f"failure_analysis.collision_avoidance.{anchoring}.{key}"
                ),
                method=(
                    "additive sum over worlds; components unclipped "
                    f"(κ = {mech.kappa_bits_per_user_step} bits per user-step)"
                ),
            )
    ax_a.axvline(0.0, color=RULE, lw=1.0, zorder=1)
    ax_a.set_yticks(ys)
    ax_a.set_yticklabels([ANCHORING_LABEL[a] for a in ANCHORINGS], fontsize=8.6, color=INK)
    ax_a.set_ylim(len(ANCHORINGS) - 0.55, -0.55)
    ax_a.set_xlabel("價值（κ，單位 = 每使用者步的 Φ 價格）", fontsize=9.5, color=INK)
    ax_a.set_title(FIG4_A, fontsize=11.5, color=INK, pad=9, loc="left")
    ax_a.text(
        0.0, 1.012,
        "兩個分量皆未截斷；淨值 $V_{CA} = [F(a_C) - F(a_D)]/\\kappa$",
        transform=ax_a.transAxes, fontsize=7.8, color=MUTED, va="bottom",
    )
    ax_a.legend(loc="lower right", fontsize=8, frameon=True, framealpha=0.95,
                edgecolor="#CBD5E1")
    style_axes(ax_a)

    # ---- panel (b): additive-reversal frequency --------------------------
    reversal = mech.reversal_fraction
    draw_interval(ax_b, 0.0, reversal, scale=100.0, decisive=False)
    observed = sum(1 for a in mech.anchors if a.additive_reversal)
    ax_b.set_yticks([0.0])
    ax_b.set_yticklabels(["加性反轉"], fontsize=8.6, color=INK)
    ax_b.set_ylim(0.9, -0.9)
    ax_b.set_xlabel(L_ANCHOR_FRACTION, fontsize=9.5, color=INK)
    ax_b.set_title(FIG4_B, fontsize=11.5, color=INK, pad=9, loc="left")
    ax_b.text(
        0.0, 1.012,
        f"$D(a_D) > 0$ 但 $D(a_D) + \\Psi(a_D) < 0$；"
        f"錨點 {observed}/{len(mech.anchors)}",
        transform=ax_b.transAxes, fontsize=7.8, color=MUTED, va="bottom",
    )
    ax_b.axvline(0.0, color=RULE, lw=1.0, zorder=1)
    sidecar.add_interval(
        reversal, panel="b", setting=PRIMARY_SETTING, scale=100.0,
        source_field=(
            f"uncertainty.per_cell.{PRIMARY_SETTING}.contrasts.{reversal.key}"
        ),
        point_label=f"observed {observed}/{len(mech.anchors)} anchors",
    )
    style_axes(ax_b)

    # ---- panel (c): nominal prediction vs realised outcome ---------------
    nominal = [a.nominal_predicted_gain for a in mech.anchors]
    realised = [a.realised_gain for a in mech.anchors]
    reversed_flags = [a.additive_reversal for a in mech.anchors]
    lo = min([*nominal, *realised, 0.0])
    hi = max([*nominal, *realised, 0.0])
    pad = 0.08 * (hi - lo) if hi > lo else 1.0
    ax_c.plot([lo - pad, hi + pad], [lo - pad, hi + pad],
              color=RULE, lw=1.1, ls=(0, (4, 3)), zorder=2)
    ax_c.scatter(
        [n for n, r in zip(nominal, reversed_flags) if not r],
        [v for v, r in zip(realised, reversed_flags) if not r],
        s=17, facecolors="none", edgecolors=LIGHT, linewidths=0.9,
        zorder=3, label="錨點",
    )
    ax_c.scatter(
        [n for n, r in zip(nominal, reversed_flags) if r],
        [v for v, r in zip(realised, reversed_flags) if r],
        s=25, color=MARGIN, marker="x", linewidths=1.1, zorder=4, label="加性反轉錨點",
    )
    ax_c.axhline(0.0, color=GRID, lw=0.9, zorder=1)
    ax_c.axvline(0.0, color=GRID, lw=0.9, zorder=1)
    ax_c.set_xlim(lo - pad, hi + pad)
    ax_c.set_ylim(lo - pad, hi + pad)
    ax_c.set_xlabel("名目預測增益（κ）", fontsize=9.5, color=INK)
    ax_c.set_ylabel("實現結果增益（κ）", fontsize=9.5, color=INK)
    ax_c.set_title(FIG4_C, fontsize=11.5, color=INK, pad=9, loc="left")
    bases = sorted({a.decomposition_basis for a in mech.anchors})
    ax_c.text(
        0.0, 1.012,
        "選擇經過近似，端點從不近似；虛線為 y = x。基底：" + "、".join(bases),
        transform=ax_c.transAxes, fontsize=7.8, color=MUTED, va="bottom",
    )
    ax_c.legend(loc="lower right", fontsize=8, frameon=True, framealpha=0.95,
                edgecolor="#CBD5E1")
    ax_c.grid(True, color=GRID, lw=0.7, zorder=0)
    ax_c.set_axisbelow(True)
    for side in ("top", "right"):
        ax_c.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax_c.spines[side].set_color(RULE)
    ax_c.tick_params(colors=MUTED, labelsize=8.5)

    for anchor in mech.anchors:
        sidecar.add(
            panel="c", setting=PRIMARY_SETTING,
            series_key=f"anchor:{anchor.world_index}:{anchor.anchor_index}",
            series_label_zh="名目預測 vs 實現結果",
            point_label="加性反轉" if anchor.additive_reversal else "",
            value=anchor.realised_gain, lo=anchor.nominal_predicted_gain,
            unit="kappa", decisive=False,
            source_field=(
                f"units/{PRIMARY_SETTING}/world-{anchor.world_index}.json:"
                "failure_analysis.matched_anchor_decomposition.by_anchor"
                f"[{anchor.anchor_index}]"
            ),
            method=anchor.decomposition_basis,
        )

    fig.text(
        0.075, 0.020, reversal.report.banner_zh(),
        fontsize=7.6, color=INK, va="bottom", linespacing=1.5,
    )
    fig.suptitle(FIG4_TITLE, fontsize=14, color=INK, x=0.075, ha="left", y=0.955)
    draw_banner(fig, label)

    paths = save(fig, out, "figure4-mechanism")
    paths.append(sidecar.write(out / "figure4-mechanism.csv"))
    return paths


# --------------------------------------------------------------------------
# Figure 5 — learned contrasts.
# --------------------------------------------------------------------------


def figure5(merge: MergeReceipt, out: Path, label: str) -> list[Path]:
    sidecar = Sidecar("figure5", label)
    intervals = [load_interval(merge, PRIMARY_SETTING, q) for q in FIG5_QUANTITIES]

    fig = plt.figure(figsize=(13.6, 5.6))
    outer = fig.add_gridspec(
        1, 2, width_ratios=[1.15, 1.85],
        left=0.105, right=0.982, top=0.845, bottom=0.185, wspace=0.24,
    )
    ax_a = fig.add_subplot(outer[0, 0])
    inner = outer[0, 1].subgridspec(1, 3, wspace=0.42)
    qos_axes = [fig.add_subplot(inner[0, i]) for i in range(3)]

    # ---- panel (a): FULL vs each DROP ------------------------------------
    for index, interval in enumerate(intervals):
        draw_interval(ax_a, float(index), interval)
        sidecar.add_interval(
            interval, panel="a", setting=PRIMARY_SETTING, scale=100.0,
            source_field=(
                f"uncertainty.per_cell.{PRIMARY_SETTING}.contrasts.{interval.key}"
            ),
            point_label="達成邊際" if interval.margin_pass else "未確立（非負結果）",
        )
    ax_a.axvline(0.0, color=RULE, lw=1.0, zorder=1)
    ax_a.axvline(0.5, color=MARGIN, lw=1.1, ls=(0, (5, 2)), zorder=2)
    ax_a.set_yticks(range(len(intervals)))
    ax_a.set_yticklabels([i.label_zh for i in intervals], fontsize=9, color=INK)
    ax_a.set_ylim(len(intervals) - 0.6, -0.6)
    ax_a.set_xlabel("合併能量效率相對邊際（%）", fontsize=9.5, color=INK)
    ax_a.set_title(FIG5_A, fontsize=11.5, color=INK, pad=9, loc="left")
    ax_a.text(
        0.0, 1.012,
        "決策使用單側 2.5 百分位下界；條件交集–聯集單一主張，各成分不單獨宣稱發現。",
        transform=ax_a.transAxes, fontsize=7.8, color=MUTED, va="bottom",
    )
    ax_a.legend(
        handles=[
            Line2D([], [], color=MARGIN, lw=1.1, ls=(0, (5, 2)), label=L_MARGIN_HALF),
            Line2D([], [], color=RULE, lw=1.0, label=L_ZERO),
        ],
        loc="lower right", fontsize=8, frameon=True, framealpha=0.95,
        edgecolor="#CBD5E1",
    )
    style_axes(ax_a)

    # ---- panel (b): aligned QoS contrasts, one axis per unit -------------
    for ax, spec in zip(qos_axes, QOS_CO_PRIMARIES):
        scale = 100.0
        for index, factor in enumerate(FACTORS):
            interval = load_qos(merge, PRIMARY_SETTING, factor, spec)
            draw_interval(ax, float(index), interval, scale=scale)
            sidecar.add_interval(
                interval, panel="b", setting=PRIMARY_SETTING, scale=scale,
                source_field=(
                    f"uncertainty.per_cell.{PRIMARY_SETTING}.contrasts.{factor}."
                    f"{spec.point_field} / {spec.bound_field} / {spec.margin_field}"
                ),
                point_label=("非劣" if interval.margin_pass else "未達非劣邊際"),
            )
            margin = interval.margin * scale
        ax.axvline(0.0, color=RULE, lw=1.0, zorder=1)
        ax.axvline(margin, color=MARGIN, lw=1.1, ls=(0, (5, 2)), zorder=2)
        # Shade the failing side, so pass/fail is a visual state.
        lo_x, hi_x = ax.get_xlim()
        if spec.direction == "higher_is_better":
            ax.axvspan(lo_x, margin, color=MARGIN, alpha=0.055, zorder=0)
        else:
            ax.axvspan(margin, hi_x, color=MARGIN, alpha=0.055, zorder=0)
        ax.set_xlim(lo_x, hi_x)
        ax.set_yticks(range(len(FACTORS)))
        ax.set_yticklabels([f"FULL vs DROP_{f}" for f in FACTORS], fontsize=8.2, color=INK)
        ax.set_ylim(len(FACTORS) - 0.6, -0.6)
        ax.set_xlabel(spec.axis_zh, fontsize=8.8, color=INK)
        ax.set_title(
            spec.label_zh
            + ("（越高越好）" if spec.direction == "higher_is_better" else "（越低越好）"),
            fontsize=9.2, color=INK, pad=6, loc="left",
        )
        style_axes(ax)
    qos_axes[0].text(
        0.0, 1.115, FIG5_B, transform=qos_axes[0].transAxes,
        fontsize=11.5, color=INK, va="bottom",
    )
    qos_axes[0].text(
        0.0, 1.062,
        "單位不共用座標軸：可用度為百分點，換手率與 Φ 計價成本為相對百分比。",
        transform=qos_axes[0].transAxes, fontsize=7.8, color=MUTED, va="bottom",
    )

    fig.text(
        0.105, 0.020, intervals[0].report.banner_zh(),
        fontsize=7.6, color=INK, va="bottom", linespacing=1.5,
    )
    fig.text(
        0.105, 0.088,
        "未達 +0.5 % 代表益處「未確立」，並非效應非正；"
        "更強的陳述需要一個上界校準於零或以下。",
        fontsize=7.6, color=MUTED, va="bottom",
    )
    fig.suptitle(FIG5_TITLE, fontsize=14, color=INK, x=0.105, ha="left", y=0.955)
    draw_banner(fig, label)

    paths = save(fig, out, "figure5-learned-contrasts")
    paths.append(sidecar.write(out / "figure5-learned-contrasts.csv"))
    return paths


# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipts", type=Path, required=True,
                        help="matrix-probe output directory (holds merged-receipt.json and units/)")
    parser.add_argument("--out", type=Path, required=True, help="figure output directory")
    parser.add_argument("--label", choices=list(LABELS), required=True,
                        help="claim label; rendered as a banner unless CONFIRMATORY")
    parser.add_argument("--only", choices=["3", "4", "5"], action="append",
                        help="render only these figures (repeatable)")
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    merge = load_merge(args.receipts)
    ordered = [PRIMARY_SETTING] + [c for c in merge.cell_order if c != PRIMARY_SETTING]
    units = load_units(args.receipts, ordered)
    certificates = [load_certificates(merge, cell) for cell in ordered]
    check_label(args.label, merge, certificates)

    wanted = set(args.only or ["3", "4", "5"])
    written: list[Path] = []
    if "3" in wanted:
        written += figure3(merge, units, args.out, args.label)
    if "4" in wanted:
        written += figure4(merge, units, args.out, args.label)
    if "5" in wanted:
        written += figure5(merge, args.out, args.label)

    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReceiptFieldError as error:
        print(f"RECEIPT CONTRACT VIOLATION\n  {error}", file=sys.stderr)
        sys.exit(2)
