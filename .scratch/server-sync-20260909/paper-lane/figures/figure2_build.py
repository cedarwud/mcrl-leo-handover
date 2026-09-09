#!/usr/bin/env python3
"""Build Figure 2 (architecture): the V0.25 successor decision path.

Extends the visual language of `CORE-FLOW-DRAFT.svg`:
  * same three-lane swimlane geometry (x = 30/555/1075, widths 490/470/495),
  * same palette, same Times New Roman 28/24/20 px type scale,
  * same rounded-rect vocabulary (panels rx=10, cards rx=8, badges rx=4 h=34),
  * same arrow markers and 15/26/28 text padding rhythm.

It adds what the draft had no need for, and declares each addition in a legend:
  * a violet dashed separator for the INFORMATION BOUNDARY (I_heads | I_coordinator),
  * an amber dashed path for the DEADLINE / FALLBACK route,
  * a green dashed separator for the NOMINAL -> REALISED transition at the endpoint.

Flow: world tape -> per-user rows -> the two heads -> per-user proposal (a0/BASE)
   -> set-level layer over the bounded catalogue -> validation -> execution
   -> 48-boundary endpoint.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent

W, H = 1600, 1098

# ---- palette (inherited from CORE-FLOW-DRAFT.svg) -------------------------
INK_DARK = "#0F172A"
INK = "#1E293B"
SUB = "#475569"
NAVY = "#003366"
PANEL_STROKE = "#94A3B8"
STRIP = "#F1F5F9"
HAIRLINE = "#CBD5E1"
WHITE = "#FFFFFF"

BLUE_FILL, BLUE_STROKE, BLUE_TITLE = "#EFF6FF", "#3B82F6", "#1D4ED8"
BLUE_DEEP = "#1E40AF"
AMBER_FILL, AMBER_STROKE, AMBER_TITLE = "#FFFBEB", "#F59E0B", "#B45309"
AMBER_EDGE = "#D97706"
VIOLET_FILL, VIOLET_STROKE, VIOLET_TITLE = "#F5F3FF", "#8B5CF6", "#6D28D9"
VIOLET_EDGE = "#7C3AED"
VIOLET_BADGE = "#EDE9FE"
GREEN_FILL, GREEN_STROKE, GREEN_TITLE = "#F0FDF4", "#16A34A", "#15803D"
GREEN_EDGE = "#059669"
GREEN_DEEP = "#065F46"
GREEN_PALE = "#ECFDF5"
SKY = "#38BDF8"
RED_FILL, RED_STROKE, RED_TEXT = "#FEF2F2", "#DC2626", "#991B1B"

parts: list[str] = []
warnings: list[str] = []


# ---- text metrics (approximate Times New Roman advance at a given size) ----
_NARROW = set("iIjlft.,;:'|!()[]{}/\\ ")
_WIDE = set("ABCDEFGHKLNOPQRSTUVXYZmwMW@%&")


def text_width(s: str, size: int, bold: bool = False) -> float:
    total = 0.0
    for ch in s:
        if ord(ch) > 0x2E00:          # CJK and friends: full width
            total += size
        elif ch in _NARROW:
            total += size * 0.28
        elif ch in _WIDE:
            total += size * 0.68
        else:
            total += size * 0.50
    return total * (1.06 if bold else 1.0)


def check_fit(s: str, size: int, avail: float, where: str, bold: bool = False) -> None:
    w = text_width(s, size, bold)
    if w > avail:
        warnings.append(f"{where}: {w:.0f}px > {avail:.0f}px :: {s!r}")


# ---- primitives -----------------------------------------------------------
def rect(x, y, w, h, fill, stroke=None, rx=8, sw=1.5, dash=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = f' stroke="{stroke}" stroke-width="{sw}"{d}' if stroke else ""
    parts.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}{extra}/>')


def text(x, y, s, cls, fill=None, anchor=None, rotate=None):
    f = f' fill="{fill}"' if fill else ""
    a = f' text-anchor="{anchor}"' if anchor else ""
    t = f' transform="rotate({rotate} {x} {y})"' if rotate else ""
    parts.append(f'  <text x="{x}" y="{y}" class="{cls}"{f}{a}{t}>{escape(s)}</text>')


def card(x, y, w, h, title, title_fill, lines, *, fill=WHITE, stroke=None,
         sw=1.5, sub_last=False, where="card"):
    """A lane card: 15px left pad, first baseline +26, 28px line pitch."""
    rect(x, y, w, h, fill, stroke or HAIRLINE, sw=sw)
    avail = w - 30
    check_fit(title, 20, avail, f"{where}/title", bold=True)
    text(x + 15, y + 26, title, "font-box-title", title_fill)
    for i, line in enumerate(lines):
        cls = "font-box-sub" if (sub_last and i == len(lines) - 1) else "font-box-body"
        check_fit(line, 20, avail, f"{where}/L{i}")
        text(x + 15, y + 26 + 28 * (i + 1), line, cls)


def badge(x, y, w, s, fill, stroke, fg, *, h=34, size_cls="font-badge", center=True):
    rect(x, y, w, h, fill, stroke, rx=4, sw=1)
    check_fit(s, 20, w - 16, "badge", bold=True)
    if center:
        text(x + w / 2, y + 23, s, size_cls, fg, anchor="middle")
    else:
        text(x + 10, y + 23, s, size_cls, fg)


def lane(x, y, w, h, heading):
    rect(x, y, w, h, WHITE, PANEL_STROKE, rx=10, extra=' filter="url(#shadow)"')
    rect(x, y, w, 42, STRIP, None, rx=10)
    text(x + 15, y + 30, heading, "font-section", NAVY)


# ---- geometry -------------------------------------------------------------
HDR_Y, HDR_H = 15, 80
RIB_Y, RIB_H = 108, 80
LANE_Y, LANE_H = 198, 532
WRAP_Y = 750               # the return run, in the gap below the lanes
BAND_Y, BAND_H = 768, 200
FOOT_Y, FOOT_H = 986, 82

L1X, L1W = 30, 490
L2X, L2W = 555, 470
L3X, L3W = 1075, 495
BOUNDARY_X = 1050          # gutter between the per-user side and the coordinator

parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'width="{W}" height="{H}">'
)
parts.append("""  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F8FAFC"/>
      <stop offset="100%" stop-color="#EFF6FF"/>
    </linearGradient>
    <filter id="shadow" x="-2%" y="-2%" width="104%" height="106%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#000000" flood-opacity="0.08"/>
    </filter>
    <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#1D4ED8" />
    </marker>
    <marker id="arrowAmber" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#D97706" />
    </marker>
    <marker id="arrowGreen" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#059669" />
    </marker>
    <marker id="arrowDark" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#1E293B" />
    </marker>
    <marker id="arrowViolet" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#7C3AED" />
    </marker>
  </defs>
  <style>
    .font-title { font-family: 'Times New Roman', serif; font-size: 28px; font-weight: bold; fill: #0F172A; }
    .font-section { font-family: 'Times New Roman', serif; font-size: 24px; font-weight: bold; fill: #003366; }
    .font-box-title { font-family: 'Times New Roman', serif; font-size: 20px; font-weight: bold; }
    .font-box-body { font-family: 'Times New Roman', serif; font-size: 20px; fill: #1E293B; }
    .font-box-sub { font-family: 'Times New Roman', serif; font-size: 20px; fill: #475569; }
    .font-badge { font-family: 'Times New Roman', serif; font-size: 20px; font-weight: bold; }
  </style>""")

parts.append(f'  <rect x="0" y="0" width="{W}" height="{H}" fill="url(#bgGrad)"/>')

# ---- header ---------------------------------------------------------------
rect(30, HDR_Y, 1540, HDR_H, WHITE, HAIRLINE, extra=' filter="url(#shadow)"')
text(50, 48, "Multi-Catfish MCRL V0.25: Successor Decision Path", "font-title")
text(50, 76,
     "World Tape  •  Two Per-User Heads  •  Set-Level Coordinator over a Bounded Catalogue  "
     "•  Atomic Commit  •  48-Boundary Endpoint",
     "font-box-sub")
badge(909, 24, 163, "PRIMARY: a-r0", "#DEF7EC", "#31C48D", "#03543F")
badge(1084, 24, 298, "ENDPOINT: 48 BOUNDARIES", VIOLET_BADGE, VIOLET_EDGE, "#5B21B6")
badge(1380, 24, 170, "PRE-SEALED", AMBER_FILL, "#EAB308", "#854D0E")

# ---- information-boundary ribbon -----------------------------------------
def ribbon(x, w, fill, stroke, title, lines, where):
    rect(x, RIB_Y, w, RIB_H, fill, stroke, rx=6, dash="8 5")
    avail = w - 30
    check_fit(title, 20, avail, f"{where}/title", bold=True)
    text(x + 15, RIB_Y + 25, title, "font-box-title", VIOLET_TITLE)
    for i, line in enumerate(lines):
        check_fit(line, 20, avail, f"{where}/L{i}")
        text(x + 15, RIB_Y + 49 + 22 * i, line, "font-box-body")


ribbon(30, 995, VIOLET_FILL, VIOLET_STROKE,
       "I_heads  —  per user i, per legal action",
       ["i's candidate nominal geometry • i's history • previous served set",
        "excluding i (b⁻₋ᵢ)  •  no joint physics  •  one forward pass"],
       "ribbon/heads")

ribbon(L3X, L3W, VIOLET_BADGE, VIOLET_EDGE,
       "I_coordinator  —  per anchor",
       ["global nominal geometry + beam cross gains",
        "all legal sets • b⁻ • a⁰ • \U0001D49E • \U0001D4DC"],
       "ribbon/coord")

# the boundary itself, running the full height of the per-user / coordinator split
parts.append(
    f'  <line x1="{BOUNDARY_X}" y1="{RIB_Y - 6}" x2="{BOUNDARY_X}" y2="{BAND_Y - 14}" '
    f'stroke="{VIOLET_EDGE}" stroke-width="2.5" stroke-dasharray="9 6"/>'
)
text(BOUNDARY_X - 9, (RIB_Y + BAND_Y) / 2, "INFORMATION BOUNDARY", "font-badge",
     VIOLET_EDGE, anchor="middle", rotate=-90)

# ---- lane 1 ---------------------------------------------------------------
lane(L1X, LANE_Y, L1W, LANE_H, "1. World Tape and Per-User Rows")
cx, cw = L1X + 15, L1W - 30
card(cx, 248, cw, 132, "World Tape (built once per world)", BLUE_TITLE, [
    "33 steps × 48 boundaries at t + k(0.640 s)",
    "Geometry, channel and cross gains precomputed",
    "Reused by every arm and every setting",
], fill=BLUE_FILL, stroke=BLUE_STROKE, sub_last=True, where="L1/tape")

card(cx, 396, cw, 132, "Per-User Candidate Rows", BLUE_TITLE, [
    "28 association slots (4 satellites × 7 cells)",
    "NO_OP legal exactly for an empty mask",
    "One row per user per legal action",
], sub_last=True, where="L1/rows")

card(cx, 544, cw, 160, "Frozen Row Schemas", BLUE_TITLE, [
    "Q1: rate-target margin, required power / cap,",
    "mode SE, occupancy excluding focal, angle, times",
    "Q2: 22 fields; background b⁻₋ᵢ at decision time",
    "Nominal model only — realised fading is excluded",
], sub_last=True, where="L1/schema")

# ---- lane 2 ---------------------------------------------------------------
lane(L2X, LANE_Y, L2W, LANE_H, "2. Two Heads → Per-User Proposal")
cx, cw = L2X + 15, L2W - 30
card(cx, 248, cw, 118, "Q₁ : Focal Opening Head", BLUE_TITLE, [
    "Pairwise zero-bootstrap regression",
    "Supervised surrogate, not a Bellman value",
], fill=BLUE_FILL, stroke=BLUE_STROKE, sw=2, sub_last=True, where="L2/q1")

card(cx, 378, cw, 118, "Q₂ : Continuation / Forecast Head", AMBER_TITLE, [
    "Same training form, 22-field schema",
    "Certificate is forecast validity",
], fill=AMBER_FILL, stroke=AMBER_EDGE, sw=2, sub_last=True, where="L2/q2")

card(cx, 508, cw, 104, "Per-User Masked Argmax", INK_DARK, [
    "argmax over \U0001D49Cᵤ⁺ of normalised Q₁ + Q₂",
    "One forward pass per candidate row",
], sub_last=True, where="L2/argmax")

card(cx, 624, cw, 104, "a⁰ (BASE) — validated profile", GREEN_TITLE, [
    "Independent picks repaired into a legal profile",
    "Built BEFORE the coordinator's clock starts",
], fill=GREEN_FILL, stroke=GREEN_STROKE, sw=2, sub_last=True, where="L2/a0")

# ---- lane 3 ---------------------------------------------------------------
lane(L3X, LANE_Y, L3W, LANE_H, "3. Set-Level Layer over the Catalogue")
cx, cw = L3X + 15, L3W - 30
card(cx, 248, cw, 156, "Bounded Catalogue \U0001D49E  (≈ 1 200 rows)", GREEN_TITLE, [
    "≤ 800 unilateral: top-8 options per user",
    "≤ 180 pairwise: top-10 users × top-2 options",
    "≈ 40 per-active-beam evacuation sets",
    "≤ 200 S0 proposals and evacuations",
], fill=GREEN_PALE, stroke=GREEN_EDGE, where="L3/cat")

card(cx, 416, cw, 156, "Set-Level Selectors", GREEN_TITLE, [
    "S3  learned Ψ̂_θ(Z, a⁰, A, a_A), deployed",
    "     permutation-invariant, Ψ̂(∅) = Ψ̂({u}) = 0",
    "S0  the same selector with exact Ψ_A",
    "S_UNI  iterated exact unilateral comparator",
], stroke=GREEN_EDGE, sw=2, where="L3/sel")

card(cx, 584, cw, 140, "Two-Stage Scoring", INK_DARK, [
    "Stage 1  C₁ + Ψ over all rows at k = 0",
    "Stage 2  C₂ continuation over the top M = 64",
    "Select the argmax of the complete score",
], sub_last=True, where="L3/score")
badge(cx + cw - 202, 596, 202, "10 s • 4 WORKERS", AMBER_FILL, "#EAB308", "#854D0E", h=28)

# ---- band 4 ---------------------------------------------------------------
lane(30, BAND_Y, 1540, BAND_H, "4. Validation, Execution and the 48-Boundary Endpoint")
BW, BGAP = 362, 20
bx = [45, 45 + BW + BGAP, 45 + 2 * (BW + BGAP), 45 + 3 * (BW + BGAP)]
BY, BH = 824, 124

card(bx[0], BY, BW, BH, "Validation", GREEN_TITLE, [
    "Joint legality and repair",
    "Service guard: no served-count",
    "decrease versus BASE",
], stroke=GREEN_EDGE, where="B/val")

card(bx[1], BY, BW, BH, "Coupled Capped Solve", GREEN_TITLE, [
    "p ← min(p⁺, Γ(N₀W + I(p))/ĥ)",
    "Unique capped fixed point;",
    "CONVERGED / CONVERGED_SLOW",
], stroke=GREEN_EDGE, where="B/solve")

card(bx[2], BY, BW, BH, "Atomic Commit", INK_DARK, [
    "One complete profile committed",
    "Never split into per-user",
    "adoptions",
], where="B/commit")

rect(bx[3], BY, BW, BH, INK, INK_DARK, sw=2)
text(bx[3] + 15, BY + 26, "48-Boundary Endpoint", "font-box-title", WHITE)
text(bx[3] + 15, BY + 54, "Realised fading • 47 trapezoidal intervals", "font-box-body", "#CBD5E1")
text(bx[3] + 15, BY + 82, "Pooled ΣB / ΣE  •  C₁ / C₂ / C₃ labels", "font-box-body", "#CBD5E1")
text(bx[3] + 15, BY + 110, "⟨結果待填⟩", "font-box-title", SKY)

# nominal -> realised separator, just left of the endpoint card
NRX = bx[3] - BGAP / 2
parts.append(
    f'  <line x1="{NRX}" y1="{BY - 4}" x2="{NRX}" y2="{BY + BH + 6}" '
    f'stroke="{GREEN_EDGE}" stroke-width="2.5" stroke-dasharray="9 6"/>'
)
text(NRX, BY - 12, "NOMINAL → REALISED", "font-badge", GREEN_EDGE, anchor="middle")

# ---- edges ----------------------------------------------------------------
parts.append("  <!-- lane 1 -> lane 2 -->")
for y1, y2 in ((314, 307), (462, 437), (624, 560)):
    parts.append(
        f'  <path d="M 520 {y1} L 537 {y1} L 537 {y2} L 555 {y2}" fill="none" '
        f'stroke="{BLUE_TITLE}" stroke-width="2.5" marker-end="url(#arrowBlue)"/>'
    )

parts.append("  <!-- inside lane 2: heads -> argmax -> a0 -->")
for y1, y2 in ((496, 508), (612, 624)):
    parts.append(
        f'  <line x1="790" y1="{y1}" x2="790" y2="{y2}" stroke="{INK}" '
        f'stroke-width="2" marker-end="url(#arrowDark)"/>'
    )

parts.append("  <!-- lane 2 -> lane 3: a0 crosses the information boundary -->")
parts.append(
    f'  <path d="M 1010 676 L 1036 676 L 1036 326 L 1075 326" fill="none" '
    f'stroke="{VIOLET_EDGE}" stroke-width="2.5" marker-end="url(#arrowViolet)"/>'
)
text(1028, 704, "a⁰", "font-badge", VIOLET_EDGE, anchor="middle")

parts.append("  <!-- catalogue -> selectors -> scoring -->")
for y1, y2 in ((404, 416), (572, 584)):
    parts.append(
        f'  <line x1="1322" y1="{y1}" x2="1322" y2="{y2}" stroke="{GREEN_EDGE}" '
        f'stroke-width="2" marker-end="url(#arrowGreen)"/>'
    )

parts.append("  <!-- committed selection returns along the left margin to band 4 -->")
parts.append(
    f'  <path d="M 1322 724 L 1322 {WRAP_Y} L 16 {WRAP_Y} L 16 {BY + BH / 2} '
    f'L {bx[0]} {BY + BH / 2}" fill="none" '
    f'stroke="{INK}" stroke-width="2" marker-end="url(#arrowDark)"/>'
)
text(1150, WRAP_Y - 6, "selected profile", "font-box-sub", INK)

parts.append("  <!-- band 4 left-to-right -->")
for i in range(3):
    x1 = bx[i] + BW
    parts.append(
        f'  <line x1="{x1}" y1="{BY + 62}" x2="{bx[i + 1]}" y2="{BY + 62}" '
        f'stroke="{INK}" stroke-width="2" marker-end="url(#arrowDark)"/>'
    )

parts.append("  <!-- deadline / fallback path (crosses the return run at a right angle) -->")
parts.append(
    f'  <path d="M 700 728 L 700 800 L {bx[2] + BW / 2} 800 L {bx[2] + BW / 2} {BY}" '
    f'fill="none" stroke="{AMBER_EDGE}" stroke-width="2.5" stroke-dasharray="8 5" '
    f'marker-end="url(#arrowAmber)"/>'
)
text(712, 794, "deadline miss → commit the pre-validated a⁰ (counted in B and E)",
     "font-box-body", AMBER_TITLE)

# ---- footer ---------------------------------------------------------------
rect(30, FOOT_Y, 1540, FOOT_H, INK, "#334155", extra=' filter="url(#shadow)"')
text(50, FOOT_Y + 30, "Reading the boundaries:", "font-box-title", "#F8FAFC")
text(240, FOOT_Y + 30,
     "violet dashed = information boundary (what each layer may see)   •   "
     "amber dashed = deadline / fallback path   •   green dashed = nominal → realised",
     "font-box-body", "#CBD5E1")
text(50, FOOT_Y + 60,
     "Selection may be approximated (k = 0, top-M pruning, margin adjustment); the endpoint may not "
     "— every committed profile and every label is recomputed on all 48 boundaries with realised fading.",
     "font-box-body", "#CBD5E1")

parts.append("</svg>")

svg = "\n".join(parts) + "\n"
path = OUT / "figure2-architecture.svg"
path.write_text(svg, encoding="utf-8")
print(f"wrote {path}  ({len(svg)} bytes)")

# A page-sized wrapper so headless Chrome prints the PDF at the figure's own
# aspect instead of fitting it onto a portrait Letter sheet. 96 px = 1 in.
wrapper = OUT / "figure2-architecture.print.html"
wrapper.write_text(
    "<!doctype html><meta charset='utf-8'>"
    f"<style>@page{{size:{W / 96:.4f}in {H / 96:.4f}in;margin:0}}"
    "html,body{margin:0;padding:0}svg{display:block}</style>\n" + svg,
    encoding="utf-8",
)
print(f"wrote {wrapper}")
if warnings:
    print(f"\n{len(warnings)} overflow warning(s):")
    for w in warnings:
        print("  " + w)
else:
    print("no text-overflow warnings")
