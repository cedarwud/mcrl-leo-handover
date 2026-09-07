#!/usr/bin/env python3
"""Build the six controller-owned editable SVG drafts for the 2026-08-27 SMC-ER batch.

The SVGs are generated artifacts.  This script is the authoring source for the
six figures it emits.  It intentionally has no third-party dependencies.
"""

from __future__ import annotations

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "svg"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1600, 920

BG = "#FBFAF6"
INK = "#24313A"
MUTED = "#66727B"
NAVY = "#17324D"
NAVY_TINT = "#E7EEF4"
OCHRE = "#9B5E2E"
OCHRE_TINT = "#F5E9DE"
TEAL = "#1F7A78"
TEAL_TINT = "#E2F0ED"
RUST = "#B44939"
RUST_TINT = "#F7E7E3"
NEUTRAL = "#EEF1F2"
LINE = "#AAB3B8"
WHITE = "#FFFFFF"


def txt(
    ident: str,
    x: float,
    y: float,
    value: str,
    *,
    size: int = 26,
    fill: str = INK,
    weight: int = 400,
    anchor: str = "start",
    family: str = "Noto Sans",
    italic: bool = False,
    rotate: float | None = None,
) -> str:
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    style = "italic" if italic else "normal"
    return (
        f'<text id="{ident}" x="{x}" y="{y}" text-anchor="{anchor}"'
        f' font-family="{family}" font-size="{size}" font-weight="{weight}"'
        f' font-style="{style}" fill="{fill}"{transform}>{escape(value)}</text>'
    )


def multiline(
    ident: str,
    x: float,
    y: float,
    lines: list[str],
    *,
    size: int = 26,
    fill: str = INK,
    weight: int = 400,
    anchor: str = "start",
    family: str = "Noto Sans",
    leading: int | None = None,
) -> str:
    leading = leading or int(size * 1.35)
    spans = []
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else leading
        spans.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    return (
        f'<text id="{ident}" x="{x}" y="{y}" text-anchor="{anchor}"'
        f' font-family="{family}" font-size="{size}" font-weight="{weight}"'
        f' fill="{fill}">{"".join(spans)}</text>'
    )


def mathlabel(
    ident: str,
    x: float,
    y: float,
    base: str,
    *,
    sub: str = "",
    sup: str = "",
    tail: str = "",
    size: int = 34,
    fill: str = INK,
) -> str:
    base_w = size * 0.68 * max(1, len(base))
    extra = size * 0.63 * max(len(sub), len(sup), 1)
    parts = [
        f'<text id="{ident}" x="{x}" y="{y}" font-family="FreeSerif" font-size="{size}"'
        f' font-style="italic" fill="{fill}">{escape(base)}</text>'
    ]
    if sub:
        parts.append(
            f'<text x="{x + base_w}" y="{y + size * 0.27}" font-family="FreeSerif"'
            f' font-size="{int(size * 0.68)}" font-style="italic" fill="{fill}">{escape(sub)}</text>'
        )
    if sup:
        parts.append(
            f'<text x="{x + base_w}" y="{y - size * 0.48}" font-family="FreeSerif"'
            f' font-size="{int(size * 0.68)}" font-style="italic" fill="{fill}">{escape(sup)}</text>'
        )
    if tail:
        parts.append(
            f'<text x="{x + base_w + extra + 4}" y="{y}" font-family="FreeSerif"'
            f' font-size="{size}" fill="{fill}">{escape(tail)}</text>'
        )
    return f'<g id="{ident}-group">{"".join(parts)}</g>'


def rect_card(
    ident: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str = WHITE,
    stroke: str = INK,
    radius: int = 12,
    sw: int = 2,
    dash: str | None = None,
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<rect id="{ident}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}"'
        f' fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>'
    )


def main_card(ident: str, x: float, y: float, w: float, h: float) -> str:
    return (
        f'<g id="{ident}">'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{NAVY_TINT}"'
        f' stroke="{NAVY}" stroke-width="5"/>'
        f'<rect x="{x + 10}" y="{y + 10}" width="{w - 20}" height="{h - 20}" rx="12"'
        f' fill="none" stroke="{NAVY}" stroke-width="2"/>'
        f'</g>'
    )


def clipped_card(ident: str, x: float, y: float, w: float, h: float, fill: str = OCHRE_TINT) -> str:
    c = 18
    pts = f"{x+c},{y} {x+w-c},{y} {x+w},{y+c} {x+w},{y+h-c} {x+w-c},{y+h} {x+c},{y+h} {x},{y+h-c} {x},{y+c}"
    return f'<polygon id="{ident}" points="{pts}" fill="{fill}" stroke="{OCHRE}" stroke-width="3"/>'


def pill(
    ident: str,
    x: float,
    y: float,
    w: float,
    label: str,
    *,
    fill: str = NEUTRAL,
    stroke: str = MUTED,
    color: str = INK,
) -> str:
    return (
        f'<g id="{ident}"><rect x="{x}" y="{y}" width="{w}" height="42" rx="21"'
        f' fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        f'{txt(ident+"-label", x+w/2, y+29, label, size=24, fill=color, weight=700, anchor="middle")}</g>'
    )


def arrow(
    ident: str,
    d: str,
    *,
    color: str = INK,
    width: int = 3,
    dash: str | None = None,
    marker: str | None = None,
    opacity: float = 1.0,
) -> str:
    marker = marker or {INK: "arrow-ink", NAVY: "arrow-navy", OCHRE: "arrow-ochre", TEAL: "arrow-teal", RUST: "arrow-rust"}.get(color, "arrow-ink")
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<path id="{ident}" d="{d}" fill="none" stroke="{color}" stroke-width="{width}"'
        f' stroke-linecap="round" stroke-linejoin="round"{dash_attr}'
        f' marker-end="url(#{marker})" opacity="{opacity}"/>'
    )


def line(ident: str, d: str, *, color: str = INK, width: int = 2, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path id="{ident}" d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr}/>'


def gate(ident: str, cx: float, cy: float, w: float, h: float, label: list[str], *, color: str = RUST) -> str:
    pts = f"{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}"
    return (
        f'<g id="{ident}"><polygon points="{pts}" fill="{RUST_TINT if color == RUST else NEUTRAL}"'
        f' stroke="{color}" stroke-width="3"/>'
        f'{multiline(ident+"-label", cx, cy-8, label, size=24, fill=color, weight=700, anchor="middle", leading=28)}</g>'
    )


def title_block(fig_id: str, title: str, subtitle: str) -> str:
    return (
        pill("figure-id", 42, 28, 128, fig_id, fill=NAVY, stroke=NAVY, color=WHITE)
        + txt("figure-title", 198, 61, title, size=36, fill=NAVY, weight=700)
        + txt("figure-subtitle", 198, 92, subtitle, size=24, fill=MUTED)
        + pill("draft-status", 1315, 28, 242, "EDITABLE DRAFT", fill=NEUTRAL, stroke=LINE, color=MUTED)
    )


def defs() -> str:
    return f"""
<defs>
  <marker id="arrow-ink" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 Z" fill="{INK}"/></marker>
  <marker id="arrow-navy" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 Z" fill="{NAVY}"/></marker>
  <marker id="arrow-ochre" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 Z" fill="{OCHRE}"/></marker>
  <marker id="arrow-teal" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 Z" fill="{TEAL}"/></marker>
  <marker id="arrow-rust" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 Z" fill="{RUST}"/></marker>
</defs>
"""


def document(fig_id: str, title: str, desc: str, body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="92mm" viewBox="0 0 {W} {H}" role="img" aria-labelledby="svg-title svg-desc">
<title id="svg-title">{escape(fig_id + " " + title)}</title>
<desc id="svg-desc">{escape(desc)}</desc>
{defs()}
<rect id="background" x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>
{body}
</svg>
'''


def q_head(ident: str, x: float, y: float, j: int, *, role: str = "M", w: float = 112, h: float = 118) -> str:
    stroke = NAVY if role == "M" else OCHRE
    fill = NAVY_TINT if role == "M" else OCHRE_TINT
    return (
        f'<g id="{ident}">{rect_card(ident+"-target-copy", x+9, y-9, w, h, fill=WHITE, stroke=LINE, radius=10, sw=2, dash="5 5")}'
        f'{rect_card(ident+"-online", x, y, w, h, fill=fill, stroke=stroke, radius=10, sw=3)}'
        f'{mathlabel(ident+"-q", x+23, y+55, "Q", sub=str(j), sup=role, size=36, fill=stroke)}'
        f'{multiline(ident+"-target-label", x+w/2, y+h-37, ["online +", "target copy"], size=18, fill=MUTED, anchor="middle", leading=20)}</g>'
    )


def figure_2_1() -> str:
    b: list[str] = [title_block("FIG 2-1", "MODQN baseline substrate", "Three objective value networks produce one feasible beam action and learn from replay")]
    b += [
        rect_card("observation-mask", 42, 176, 270, 174, fill=WHITE, stroke=TEAL, radius=16, sw=3),
        multiline("observation-mask-label", 177, 217, ["per-user observation", "+ feasible-beam", "mask"], size=22, fill=TEAL, weight=700, anchor="middle", leading=32),

        rect_card("value-network-group", 346, 130, 480, 286, fill=NAVY_TINT, stroke=NAVY, radius=18, sw=4),
        txt("value-network-group-title", 586, 171, "three parallel objective networks", size=26, fill=NAVY, weight=700, anchor="middle"),
        rect_card("ee-value-network", 380, 199, 412, 54, fill=WHITE, stroke=NAVY, radius=10, sw=2),
        txt("ee-value-network-label", 586, 234, "energy-efficiency value network", size=23, fill=INK, weight=700, anchor="middle"),
        rect_card("handover-value-network", 380, 270, 412, 54, fill=WHITE, stroke=NAVY, radius=10, sw=2),
        txt("handover-value-network-label", 586, 305, "handover-cost value network", size=23, fill=INK, weight=700, anchor="middle"),
        rect_card("load-value-network", 380, 341, 412, 54, fill=WHITE, stroke=NAVY, radius=10, sw=2),
        txt("load-value-network-label", 586, 376, "load-balancing value network", size=23, fill=INK, weight=700, anchor="middle"),

        rect_card("scalarization-exploration", 860, 188, 285, 150, fill=WHITE, stroke=NAVY, radius=16, sw=3),
        multiline("scalarization-exploration-label", 1002, 225, ["masked weighted", "scalarization", "+ exploration"], size=22, fill=NAVY, weight=700, anchor="middle", leading=31),
        rect_card("selected-beam", 1185, 198, 190, 132, fill=NAVY_TINT, stroke=NAVY, radius=66, sw=3),
        multiline("selected-beam-label", 1280, 247, ["selected", "feasible beam"], size=23, fill=NAVY, weight=700, anchor="middle", leading=34),
        rect_card("baseline-environment", 1410, 168, 150, 196, fill=TEAL_TINT, stroke=TEAL, radius=18, sw=3),
        multiline("baseline-environment-label", 1485, 218, ["LEO", "multi-beam", "environment"], size=20, fill=TEAL, weight=700, anchor="middle", leading=32),
        arrow("observation-to-networks", "M312 263 H346", color=INK, width=3),
        arrow("networks-to-scalarization", "M826 263 H860", color=INK, width=3),
        arrow("scalarization-to-beam", "M1145 263 H1185", color=INK, width=3),
        arrow("beam-to-environment", "M1375 263 H1410", color=INK, width=3),

        rect_card("reward-return", 1144, 424, 416, 122, fill=WHITE, stroke=TEAL, radius=14, sw=3),
        txt("reward-return-title", 1352, 463, "complete canonical reward vector", size=21, fill=TEAL, weight=700, anchor="middle"),
        multiline("reward-return-label", 1352, 500, ["energy efficiency / handover cost", "/ load balancing"], size=23, fill=INK, weight=700, anchor="middle", leading=31),
        arrow("environment-to-reward", "M1485 364 V424", color=INK, width=3),
        rect_card("replay-memory", 730, 450, 300, 114, fill=WHITE, stroke=NAVY, radius=16, sw=4),
        txt("replay-memory-label", 880, 500, "replay memory", size=28, fill=NAVY, weight=700, anchor="middle"),
        txt("replay-memory-note", 880, 538, "complete transition", size=22, fill=MUTED, anchor="middle"),
        arrow("reward-to-replay", "M1144 485 H1030", color=NAVY, width=7),

        line("sample-spine", "M880 564 V625 M250 625 H1350", color=OCHRE, width=4),
        rect_card("td-update-ee", 60, 666, 385, 154, fill=OCHRE_TINT, stroke=OCHRE, radius=14, sw=3),
        txt("td-update-ee-label", 252, 711, "objective-wise TD update", size=25, fill=OCHRE, weight=700, anchor="middle"),
        txt("td-update-ee-target", 252, 752, "objective-wise target max", size=22, fill=INK, anchor="middle"),
        txt("td-update-ee-copy", 252, 790, "energy-efficiency target-network copy", size=19, fill=MUTED, anchor="middle"),
        rect_card("td-update-handover", 608, 666, 385, 154, fill=OCHRE_TINT, stroke=OCHRE, radius=14, sw=3),
        txt("td-update-handover-label", 800, 711, "objective-wise TD update", size=25, fill=OCHRE, weight=700, anchor="middle"),
        txt("td-update-handover-target", 800, 752, "objective-wise target max", size=22, fill=INK, anchor="middle"),
        txt("td-update-handover-copy", 800, 790, "handover-cost target-network copy", size=19, fill=MUTED, anchor="middle"),
        rect_card("td-update-load", 1155, 666, 385, 154, fill=OCHRE_TINT, stroke=OCHRE, radius=14, sw=3),
        txt("td-update-load-label", 1347, 711, "objective-wise TD update", size=25, fill=OCHRE, weight=700, anchor="middle"),
        txt("td-update-load-target", 1347, 752, "objective-wise target max", size=22, fill=INK, anchor="middle"),
        txt("td-update-load-copy", 1347, 790, "load-balancing target-network copy", size=19, fill=MUTED, anchor="middle"),
        arrow("sample-to-ee", "M250 625 V666", color=OCHRE, width=4),
        arrow("sample-to-handover", "M800 625 V666", color=OCHRE, width=4),
        arrow("sample-to-load", "M1350 625 V666", color=OCHRE, width=4),
        arrow("sync-ee", "M252 666 V635 H470 V394", color=MUTED, width=2, dash="8 8"),
        arrow("sync-handover", "M800 666 V635 H586 V324", color=MUTED, width=2, dash="8 8"),
        arrow("sync-load", "M1347 666 V635 H705 V395", color=MUTED, width=2, dash="8 8"),
        txt("baseline-boundary", 1548, 882, "Baseline only · no proposed training extension", size=22, fill=MUTED, anchor="end", italic=True),
    ]
    return document("Fig. 2-1", "MODQN baseline substrate", "A symbol-free Chapter 2 science card showing masked feasible-beam selection, three objective value networks, complete-transition replay, objective-wise target maxima, and independent target-network copies. It contains no SMC-ER mechanism.", "".join(b))


def satellite(ident: str, x: float, y: float, scale: float = 1.0, label: str = "s") -> str:
    return f'''<g id="{ident}" transform="translate({x} {y}) scale({scale})">
<rect x="-92" y="-14" width="70" height="28" fill="{NAVY}" stroke="{INK}" stroke-width="2"/>
<rect x="22" y="-14" width="70" height="28" fill="{NAVY}" stroke="{INK}" stroke-width="2"/>
<line x1="-22" y1="0" x2="22" y2="0" stroke="{INK}" stroke-width="5"/>
<circle cx="0" cy="0" r="28" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>
<circle cx="0" cy="0" r="8" fill="{TEAL}"/>
{txt(ident+"-label", 0, -42, label, size=28, fill=NAVY, weight=700, anchor="middle", family="FreeSerif", italic=True)}
</g>'''


def ue(ident: str, x: float, y: float, label: str = "u") -> str:
    return f'''<g id="{ident}" transform="translate({x} {y})">
<circle cx="0" cy="0" r="16" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>
<line x1="0" y1="-18" x2="0" y2="-42" stroke="{INK}" stroke-width="3"/>
<path d="M-12 -35 Q0 -48 12 -35" fill="none" stroke="{TEAL}" stroke-width="3"/>
{txt(ident+"-label", 23, 8, label, size=30, fill=INK, weight=700, family="FreeSerif", italic=True)}
</g>'''


def occupancy(ident: str, x: float, y: float, count: int, color: str) -> str:
    dots = []
    for i in range(count):
        dx = (i % 4) * 28
        dy = (i // 4) * 28
        dots.append(f'<circle cx="{x+dx}" cy="{y+dy}" r="8" fill="{WHITE}" stroke="{color}" stroke-width="3"/>')
    return f'<g id="{ident}">{"".join(dots)}</g>'


def figure_3_1() -> str:
    b: list[str] = [title_block("FIG 3-1", "Physical LEO handover and EE chain", "Candidate association, handover geometry, beam load, and the single physical SINR pathway")]
    b += [
        rect_card("physical-scene", 42, 122, 1020, 545, fill=WHITE, stroke=LINE, radius=18, sw=2),
        txt("scene-label", 72, 163, "Illustrative physical scene · not to scale", size=24, fill=MUTED, italic=True),
        '<ellipse id="ground-plane" cx="550" cy="545" rx="430" ry="78" fill="#F4F1E9" stroke="#B8B3A8" stroke-width="2"/>',
        '<ellipse id="beam-footprint-v" cx="410" cy="520" rx="220" ry="68" fill="#E7EEF4" stroke="#17324D" stroke-width="3"/>',
        '<ellipse id="beam-footprint-vp" cx="690" cy="520" rx="220" ry="68" fill="#E2F0ED" stroke="#1F7A78" stroke-width="3"/>',
        '<ellipse id="candidate-footprint" cx="845" cy="545" rx="125" ry="45" fill="none" stroke="#66727B" stroke-width="2" stroke-dasharray="10 8"/>',
        '<path id="beam-cone-v" d="M485 210 L190 520 Q410 625 630 520 Z" fill="#E7EEF4" fill-opacity="0.66" stroke="#17324D" stroke-width="2"/>',
        '<path id="beam-cone-vp" d="M485 210 L470 520 Q690 625 910 520 Z" fill="#E2F0ED" fill-opacity="0.64" stroke="#1F7A78" stroke-width="2"/>',
        '<path id="candidate-cone" d="M900 250 L720 545 Q845 590 970 545 Z" fill="none" stroke="#66727B" stroke-width="2" stroke-dasharray="10 8"/>',
        satellite("serving-satellite", 485, 205, 0.72, "satellite s"),
        satellite("candidate-satellite", 900, 230, 0.58, "candidate s′"),
        ue("focal-ue", 580, 518, "u ∈ 𝒰"),
        ue("served-ue-2", 365, 548, ""),
        ue("served-ue-3", 300, 568, ""),
        line("beam-center-vector", "M485 225 L410 500", color=NAVY, width=3, dash="10 8"),
        arrow("realized-link", "M485 225 L575 500", color=INK, width=5),
        arrow("candidate-link", "M900 250 L596 501", color=MUTED, width=3, dash="10 8"),
        '<path id="off-axis-angle" d="M474 269 A52 52 0 0 1 512 266" fill="none" stroke="#B44939" stroke-width="4"/>',
        txt("off-axis-label", 530, 285, "θᵤ,ₛ,ᵥ(t)", size=28, fill=RUST, weight=700, family="FreeSerif"),
        txt("selected-link-label", 505, 390, "xᵤ,ₛ,ᵥ(t)=1", size=24, fill=NAVY, weight=700, family="FreeSerif"),
        txt("association-label", 610, 556, "(ρᵤ(t), δᵤ(t))=(s,v)", size=22, fill=INK, weight=700, family="FreeSerif"),
        txt("candidate-link-label", 765, 355, "feasible · unselected", size=21, fill=MUTED, italic=True),
        arrow("cross-satellite-handover", "M540 180 C650 105 790 115 855 190", color=RUST, width=3),
        txt("cross-handover-label", 705, 132, "ϕ₂", size=29, fill=RUST, weight=700, anchor="middle", family="FreeSerif"),
        arrow("intra-handover", "M395 607 C470 654 625 654 700 607", color=TEAL, width=4),
        txt("handover-label", 550, 657, "ϕ₁ · same-satellite v → v′", size=23, fill=TEAL, weight=700, anchor="middle", family="FreeSerif"),
        txt("beam-v-label", 330, 477, "beam (s,v)", size=26, fill=NAVY, weight=700, anchor="middle", family="FreeSerif"),
        txt("beam-vp-label", 750, 477, "beam (s,v′)", size=26, fill=TEAL, weight=700, anchor="middle", family="FreeSerif"),
        occupancy("load-v-users", 270, 536, 6, NAVY),
        txt("load-v-label", 250, 596, "Uₛ,ᵥ(t)>0 · zₛ,ᵥ(t)=1", size=22, fill=NAVY, weight=700, family="FreeSerif"),
        txt("load-vp-label", 700, 596, "Uₛ,ᵥ′(t)=0 · zₛ,ᵥ′(t)=0", size=22, fill=TEAL, weight=700, family="FreeSerif"),
        pill("realized-key", 1095, 155, 430, "solid · realized serving link", fill=WHITE, stroke=INK),
        pill("candidate-key", 1095, 212, 430, "dashed · candidate association", fill=NEUTRAL, stroke=MUTED, color=MUTED),
        rect_card("physical-variables", 1095, 286, 430, 316, fill=WHITE, stroke=TEAL, radius=16, sw=3),
        txt("physical-vars-title", 1310, 330, "Physical state at time t", size=28, fill=TEAL, weight=700, anchor="middle"),
        multiline("physical-vars-body", 1132, 380, ["selected: xᵤ,ₛ,ᵥ(t)=1", "association: (ρᵤ(t),δᵤ(t))", "occupied: Uₛ,ᵥ(t)>0, zₛ,ᵥ(t)=1", "empty: Uₛ,ᵥ′(t)=0, zₛ,ᵥ′(t)=0", "off-axis: θᵤ,ₛ,ᵥ(t)"], size=24, fill=INK, leading=42, family="FreeSerif"),
        rect_card("chain-geometry", 42, 690, 220, 154, fill=WHITE, stroke=TEAL, radius=12, sw=3),
        txt("chain-geometry-title", 152, 733, "Position → angle", size=25, fill=TEAL, weight=700, anchor="middle"),
        txt("chain-geometry-math", 152, 786, "θᵤ,ₛ,ᵥ(t)", size=30, fill=INK, anchor="middle", family="FreeSerif"),
        rect_card("chain-gain", 306, 690, 220, 154, fill=WHITE, stroke=TEAL, radius=12, sw=3),
        txt("chain-gain-title", 416, 733, "Link gain", size=27, fill=TEAL, weight=700, anchor="middle"),
        txt("chain-gain-math", 416, 786, "antenna + channel", size=22, fill=INK, anchor="middle"),
        rect_card("chain-power", 570, 690, 220, 154, fill=WHITE, stroke=TEAL, radius=12, sw=3),
        txt("chain-power-title", 680, 733, "Power", size=27, fill=TEAL, weight=700, anchor="middle"),
        txt("chain-power-math", 680, 786, "link + system power", size=21, fill=INK, anchor="middle"),
        rect_card("chain-sinr", 834, 690, 190, 154, fill=WHITE, stroke=TEAL, radius=12, sw=3),
        txt("chain-sinr-title", 929, 733, "Single SINR", size=27, fill=TEAL, weight=700, anchor="middle"),
        txt("chain-sinr-math", 929, 789, "one physical path", size=21, fill=INK, anchor="middle"),
        rect_card("chain-rate", 1068, 690, 220, 154, fill=WHITE, stroke=TEAL, radius=12, sw=3),
        txt("chain-rate-title", 1178, 733, "Rate + load", size=27, fill=TEAL, weight=700, anchor="middle"),
        txt("chain-rate-math", 1178, 786, "shared resources", size=22, fill=INK, anchor="middle"),
        rect_card("chain-ee", 1332, 690, 226, 154, fill=TEAL_TINT, stroke=TEAL, radius=12, sw=4),
        txt("chain-ee-title", 1445, 733, "EE endpoint", size=27, fill=TEAL, weight=700, anchor="middle"),
        txt("chain-ee-math", 1445, 786, "rate / system power", size=21, fill=INK, anchor="middle"),
        arrow("geometry-to-gain", "M262 767 H306", color=INK, width=3),
        arrow("gain-to-power", "M526 767 H570", color=INK, width=3),
        arrow("power-to-sinr", "M790 767 H834", color=INK, width=3),
        arrow("sinr-to-rate", "M1024 767 H1068", color=INK, width=3),
        arrow("rate-to-ee", "M1288 767 H1332", color=INK, width=3),
    ]
    return document("Fig. 3-1", "Physical LEO handover and EE chain", "A purely physical scene shows multiple satellites, beams, users, selected and feasible-unselected associations, same- and cross-satellite handover classes, the single-sided off-axis angle, occupied and empty beams, and the angle-to-gain-to-power-to-SINR-to-rate-to-EE chain. It contains no learner.", "".join(b))


def specialist_overview_card(ident: str, x: float, y: float, j: int, title: str, reward: str) -> str:
    title_lines = [title]
    if "Spatial Load-Balancing" in title:
        title_lines = ["C3 · Spatial", "Load-Balancing"]
    q_y = y + (137 if len(title_lines) > 1 else 126)
    return (
        clipped_card(ident, x, y, 330, 142)
        + rect_card(ident+"-training", x+18, y+16, 154, 36, fill=OCHRE, stroke=OCHRE, radius=18, sw=2)
        + txt(ident+"-training-label", x+95, y+41, "TRAINING-ONLY", size=19, fill=WHITE, weight=700, anchor="middle")
        + mathlabel(ident+"-role", x+248, y+49, "F", sub=str(j), size=34, fill=OCHRE)
        + multiline(ident+"-title", x+24, y+84, title_lines, size=21, fill=INK, weight=700, leading=22)
        + mathlabel(ident+"-q", x+24, q_y, "Q", sub=str(j), sup="F", size=27, fill=OCHRE)
        + txt(ident+"-reward", x+84, q_y, f"learns {reward}", size=19, fill=MUTED, family="FreeSerif")
    )


def figure_4_1() -> str:
    b: list[str] = [title_block("FIG 4-1", "Proposed SMC-ER method overview", "Training-only specialists route complete experience; evaluation and deployment retain Main only")]
    b += [
        rect_card("training-boundary", 42, 125, 1125, 720, fill="#FFFDF8", stroke=OCHRE, radius=18, sw=3, dash="12 10"),
        pill("training-boundary-label", 72, 146, 360, "PROPOSED · TRAINING ONLY", fill=OCHRE, stroke=OCHRE, color=WHITE),
        specialist_overview_card("specialist-f1", 78, 230, 1, "C1 · Energy-Frontier", "canonical r₁"),
        specialist_overview_card("specialist-f2", 78, 420, 2, "C2 · Temporal-Continuity", "canonical r₂"),
        specialist_overview_card("specialist-f3", 78, 610, 3, "C3 · Spatial Load-Balancing", "canonical r₃"),
        gate("f1-consumer-gate", 555, 301, 180, 112, ["F₁ consumer", "gate"], color=RUST),
        gate("f2-consumer-gate", 555, 491, 180, 112, ["F₂ consumer", "gate"], color=RUST),
        gate("f3-consumer-gate", 555, 681, 180, 122, ["F₃ consumer", "gate"], color=RUST),
        main_card("main-learner", 730, 224, 385, 450),
        pill("main-role", 765, 250, 210, "MAIN LEARNER", fill=NAVY, stroke=NAVY, color=WHITE),
        txt("main-title", 922, 325, "Main MODQN", size=34, fill=NAVY, weight=700, anchor="middle"),
        rect_card("overview-main-q1", 765, 370, 96, 118, fill=WHITE, stroke=NAVY, radius=10, sw=3),
        mathlabel("overview-main-q1-label", 786, 430, "Q", sub="1", sup="M", size=37, fill=NAVY),
        txt("overview-main-q1-note", 813, 472, "objective 1", size=16, fill=MUTED, anchor="middle"),
        rect_card("overview-main-q2", 875, 370, 96, 118, fill=WHITE, stroke=NAVY, radius=10, sw=3),
        mathlabel("overview-main-q2-label", 896, 430, "Q", sub="2", sup="M", size=37, fill=NAVY),
        txt("overview-main-q2-note", 923, 472, "objective 2", size=16, fill=MUTED, anchor="middle"),
        rect_card("overview-main-q3", 985, 370, 96, 118, fill=WHITE, stroke=NAVY, radius=10, sw=3),
        mathlabel("overview-main-q3-label", 1006, 430, "Q", sub="3", sup="M", size=37, fill=NAVY),
        txt("overview-main-q3-note", 1033, 472, "objective 3", size=16, fill=MUTED, anchor="middle"),
        rect_card("overview-main-replay", 810, 535, 225, 92, fill=WHITE, stroke=NAVY, radius=12, sw=3),
        multiline("overview-main-replay-label", 922, 568, ["D_M", "gated complete bundles"], size=22, fill=NAVY, weight=700, anchor="middle", leading=27, family="FreeSerif"),
        arrow("f1-bundle-to-gate", "M408 301 H465", color=OCHRE, width=7),
        arrow("f2-bundle-to-gate", "M408 491 H465", color=OCHRE, width=7),
        arrow("f3-bundle-to-alias", "M408 681 H465", color=OCHRE, width=7),
        mathlabel("bundle-label-1", 420, 280, "τ", sub="1,t", sup="F", size=27, fill=OCHRE),
        mathlabel("bundle-label-2", 420, 470, "τ", sub="2,t", sup="F", size=27, fill=OCHRE),
        mathlabel("bundle-label-3", 420, 660, "τ", sub="3,t", sup="F", size=27, fill=OCHRE),
        arrow("f1-gate-pass", "M645 301 H685 V555 H810", color=RUST, width=5, dash="12 9"),
        arrow("f2-gate-pass", "M645 491 H705 V580 H810", color=RUST, width=5, dash="12 9"),
        arrow("f3-gate-pass", "M645 681 H725 V605 H810", color=RUST, width=5, dash="12 9"),
        txt("f3-gate-note", 650, 660, "pass only after alias check", size=16, fill=RUST, weight=700),
        rect_card("f1-shadow", 650, 324, 72, 32, fill=RUST_TINT, stroke=RUST, radius=8, sw=2, dash="6 5"),
        txt("f1-shadow-label", 686, 346, "shadow", size=16, fill=RUST, weight=700, anchor="middle"),
        arrow("f1-gate-fail", "M590 338 H650", color=RUST, width=2, dash="7 6"),
        rect_card("f2-shadow", 650, 514, 72, 32, fill=RUST_TINT, stroke=RUST, radius=8, sw=2, dash="6 5"),
        txt("f2-shadow-label", 686, 536, "shadow", size=16, fill=RUST, weight=700, anchor="middle"),
        arrow("f2-gate-fail", "M590 528 H650", color=RUST, width=2, dash="7 6"),
        rect_card("shadow-only", 445, 780, 335, 56, fill=RUST_TINT, stroke=RUST, radius=10, sw=2, dash="8 6"),
        txt("shadow-only-label", 612, 816, "CURRENT F₃ · SHADOW-ONLY", size=23, fill=RUST, weight=700, anchor="middle"),
        arrow("alias-fail-shadow", "M555 742 V780", color=RUST, width=4, dash="12 10"),
        line("deployment-divider", "M1192 132 V842", color=LINE, width=3, dash="10 10"),
        pill("deployment-label", 1205, 148, 360, "EVALUATION / DEPLOYMENT", fill=NAVY, stroke=NAVY, color=WHITE),
        rect_card("deployment-card", 1240, 305, 310, 270, fill=NAVY_TINT, stroke=NAVY, radius=22, sw=4),
        txt("deployment-main", 1395, 365, "Main only", size=36, fill=NAVY, weight=700, anchor="middle"),
        multiline("deployment-body", 1395, 422, ["Q₁ᴹ · Q₂ᴹ · Q₃ᴹ", "masked-greedy action", "specialist dose = 0"], size=27, fill=INK, anchor="middle", leading=43, family="FreeSerif"),
        arrow("main-to-deployment", "M1115 450 H1240", color=NAVY, width=5),
        txt("deployment-arrow-label", 1177, 414, "trained Main", size=21, fill=NAVY, weight=700, anchor="middle"),
        pill("overview-legend-bundle", 1225, 660, 330, "wide line · complete bundle", fill=OCHRE_TINT, stroke=OCHRE, color=OCHRE),
        pill("overview-legend-conditional", 1225, 718, 330, "dashed rust · conditional", fill=RUST_TINT, stroke=RUST, color=RUST),
        multiline("overview-no-arrow", 1390, 795, ["No action fusion, auction,", "coordination, or override"], size=20, fill=MUTED, anchor="middle", leading=27),
    ]
    return document("Fig. 4-1", "Proposed SMC-ER method overview", "Three training-only specialists create complete executed bundles. The Main-consumer gate precedes Main replay, the C3 path remains conditional and shadow-only on gate failure, and only Main reaches evaluation or deployment.", "".join(b))


def specialist_topology_card(ident: str, x: float, y: float, j: int, title: str) -> str:
    return (
        clipped_card(ident, x, y, 610, 172)
        + mathlabel(ident+"-role", x+28, y+53, "F", sub=str(j), size=40, fill=OCHRE)
        + txt(ident+"-title", x+105, y+48, title, size=26, fill=INK, weight=700)
        + txt(ident+"-independent", x+585, y+80, "independent learner · private replay", size=20, fill=OCHRE, weight=700, anchor="end", italic=True)
        + rect_card(ident+"-q-target", x+38, y+88, 185, 62, fill=WHITE, stroke=LINE, radius=10, sw=2, dash="5 5")
        + rect_card(ident+"-q", x+30, y+96, 185, 62, fill=WHITE, stroke=OCHRE, radius=10, sw=3)
        + mathlabel(ident+"-q-label", x+98, y+139, "Q", sub=str(j), sup="F", size=32, fill=OCHRE)
        + rect_card(ident+"-d", x+247, y+96, 150, 62, fill=WHITE, stroke=OCHRE, radius=10, sw=3)
        + mathlabel(ident+"-d-label", x+298, y+139, "D", sub=str(j), sup="F", size=32, fill=OCHRE)
        + rect_card(ident+"-bundle", x+426, y+96, 154, 62, fill=OCHRE, stroke=OCHRE, radius=10, sw=2)
        + mathlabel(ident+"-bundle-label", x+462, y+127, "τ", sub=f"{j},t", sup="F", size=31, fill=WHITE)
        + txt(ident+"-bundle-shape", x+535, y+148, "U × 3", size=20, fill=WHITE, anchor="middle", family="FreeSerif")
    )


def figure_4_2() -> str:
    b: list[str] = [title_block("FIG 4-2", "Learner topology", "Four logical learners · six online Q functions · independent target copies")]
    b += [
        pill("stat-learners", 55, 126, 290, "4 LOGICAL LEARNERS", fill=NEUTRAL, stroke=INK, color=INK),
        pill("stat-q", 365, 126, 320, "6 ONLINE Q FUNCTIONS", fill=NEUTRAL, stroke=INK, color=INK),
        specialist_topology_card("topology-f1", 55, 205, 1, "C1 · Energy-Frontier"),
        specialist_topology_card("topology-f2", 55, 407, 2, "C2 · Temporal-Continuity"),
        specialist_topology_card("topology-f3", 55, 609, 3, "C3 · Spatial Load-Balancing"),
        gate("topology-f1-gate", 790, 318, 150, 100, ["F₁", "gate"], color=RUST),
        gate("topology-f2-gate", 790, 520, 150, 100, ["F₂", "gate"], color=RUST),
        gate("topology-f3-gate", 790, 722, 150, 100, ["F₃", "gate"], color=RUST),
        arrow("topology-f1-route", "M665 318 H715", color=OCHRE, width=7),
        arrow("topology-f2-route", "M665 520 H715", color=OCHRE, width=7),
        arrow("topology-f3-route", "M665 722 H715", color=OCHRE, width=7),
        txt("topology-f1-pass", 883, 305, "pass", size=18, fill=RUST, weight=700),
        txt("topology-f2-pass", 883, 507, "pass", size=18, fill=RUST, weight=700),
        rect_card("topology-f1-shadow", 715, 375, 150, 30, fill=RUST_TINT, stroke=RUST, radius=7, sw=2, dash="6 5"),
        txt("topology-f1-shadow-label", 790, 396, "fail → shadow", size=17, fill=RUST, weight=700, anchor="middle"),
        arrow("topology-f1-fail", "M790 368 V375", color=RUST, width=2, dash="6 5"),
        rect_card("topology-f2-shadow", 715, 577, 150, 30, fill=RUST_TINT, stroke=RUST, radius=7, sw=2, dash="6 5"),
        txt("topology-f2-shadow-label", 790, 598, "fail → shadow", size=17, fill=RUST, weight=700, anchor="middle"),
        arrow("topology-f2-fail", "M790 570 V577", color=RUST, width=2, dash="6 5"),
        rect_card("topology-f3-shadow", 680, 779, 220, 34, fill=RUST_TINT, stroke=RUST, radius=7, sw=3, dash="6 5"),
        txt("topology-f3-shadow-label", 790, 802, "CURRENT SHADOW-ONLY", size=17, fill=RUST, weight=700, anchor="middle"),
        arrow("topology-f3-fail", "M790 772 V779", color=RUST, width=3, dash="6 5"),
        txt("topology-c3-note", 650, 858, "F₃ Main route opens only after its observational-alias gate passes", size=21, fill=RUST, anchor="middle", italic=True),
        main_card("topology-main", 960, 168, 590, 630),
        pill("topology-main-role", 1000, 198, 228, "MAIN LEARNER", fill=NAVY, stroke=NAVY, color=WHITE),
        txt("topology-main-title", 1255, 280, "One Main MODQN", size=34, fill=NAVY, weight=700, anchor="middle"),
        rect_card("topology-main-replay", 1075, 306, 360, 90, fill=WHITE, stroke=NAVY, radius=14, sw=4),
        txt("topology-main-replay-label", 1255, 344, "D_M · admitted full bundles", size=23, fill=NAVY, weight=700, anchor="middle", family="FreeSerif"),
        txt("topology-main-replay-note", 1255, 378, "not a same-number-head connection", size=21, fill=MUTED, anchor="middle", italic=True),
        q_head("topology-main-q1", 1015, 493, 1, w=145, h=138),
        q_head("topology-main-q2", 1182, 493, 2, w=145, h=138),
        q_head("topology-main-q3", 1349, 493, 3, w=145, h=138),
        line("main-head-bracket", "M1087 457 H1421", color=NAVY, width=3),
        arrow("replay-to-head-bracket", "M1255 396 V457", color=NAVY, width=4),
        arrow("bracket-to-q1", "M1087 457 V493", color=MUTED, width=3, dash="3 8"),
        arrow("bracket-to-q2", "M1255 457 V493", color=MUTED, width=3, dash="3 8"),
        arrow("bracket-to-q3", "M1421 457 V493", color=MUTED, width=3, dash="3 8"),
        multiline("topology-main-note", 1255, 686, ["All three Main heads learn the same bundle", "and preserve its cross-objective consequence"], size=22, fill=NAVY, weight=700, anchor="middle", leading=29),
        arrow("f1-gate-to-main-replay", "M865 318 H900 V330 H1075", color=RUST, width=5, dash="12 9"),
        arrow("f2-gate-to-main-replay", "M865 520 H920 V351 H1075", color=RUST, width=5, dash="12 9"),
        arrow("f3-gate-to-main-replay", "M865 722 H940 V372 H1075", color=MUTED, width=3, dash="4 10"),
        arrow("topology-legend-line", "M1010 770 H1090", color=OCHRE, width=7),
        txt("topology-legend-label", 1112, 778, "complete executed experience", size=21, fill=MUTED, weight=700),
    ]
    return document("Fig. 4-2", "Learner topology", "The topology has one three-head Main learner and three independent one-head specialists, for four logical learners and six online Q functions plus target copies. Every specialist bundle targets the whole Main replay, while the C3 route remains conditional.", "".join(b))


def reward_matrix(x: float, y: float) -> str:
    col_w, row_h = 130, 62
    parts = ['<g id="reward-matrix">']
    headers = ["r₁,ᵤ", "r₂,ᵤ", "r₃,ᵤ"]
    for c, header in enumerate(headers):
        parts.append(rect_card(f"matrix-header-{c+1}", x + 90 + c * col_w, y, col_w, row_h, fill=NAVY_TINT if c == 0 else NEUTRAL, stroke=LINE, radius=0, sw=2))
        parts.append(txt(f"matrix-header-label-{c+1}", x + 90 + c * col_w + col_w/2, y+41, header, size=28, fill=INK, weight=700, anchor="middle", family="FreeSerif"))
    row_labels = ["u=1", "u=2", "⋮", "u=U"]
    cell_values = [["r₁,₁", "r₂,₁", "r₃,₁"], ["r₁,₂", "r₂,₂", "r₃,₂"], ["⋮", "⋮", "⋮"], ["r₁,ᵁ", "r₂,ᵁ", "r₃,ᵁ"]]
    for r, label in enumerate(row_labels):
        yy = y + row_h + r * row_h
        parts.append(rect_card(f"matrix-row-label-{r+1}", x, yy, 90, row_h, fill=WHITE, stroke=LINE, radius=0, sw=2))
        parts.append(txt(f"matrix-row-label-text-{r+1}", x+45, yy+41, label, size=26, fill=MUTED, weight=700, anchor="middle", family="FreeSerif"))
        for c in range(3):
            parts.append(rect_card(f"matrix-cell-{r+1}-{c+1}", x+90+c*col_w, yy, col_w, row_h, fill=WHITE, stroke=LINE, radius=0, sw=2))
            parts.append(txt(f"matrix-cell-text-{r+1}-{c+1}", x+90+c*col_w+col_w/2, yy+41, cell_values[r][c], size=26, fill=INK, anchor="middle", family="FreeSerif"))
    parts.append('</g>')
    return ''.join(parts)


def figure_4_6() -> str:
    b: list[str] = [title_block("FIG 4-6", "Atomic experience routing", "One joint U × 3 reward matrix stays intact from execution to all three Main heads")]
    b += [
        rect_card("atomic-bundle", 42, 145, 590, 685, fill=WHITE, stroke=OCHRE, radius=18, sw=4),
        pill("atomic-bundle-tag", 72, 170, 405, "ONE EXECUTED JOINT BUNDLE", fill=OCHRE, stroke=OCHRE, color=WHITE),
        mathlabel("atomic-bundle-symbol", 145, 252, "τ", sub="j,t", sup="F", size=34, fill=INK),
        txt("atomic-bundle-symbol-note", 280, 252, "joint action + every user row", size=23, fill=INK, family="FreeSerif"),
        multiline("atomic-fields", 337, 289, ["states · masks · successors · terminal", "shared source and execution lineage"], size=21, fill=MUTED, anchor="middle", leading=29),
        multiline("matrix-title", 337, 360, ["Complete canonical reward matrix", "U users × 3 objectives"], size=24, fill=INK, weight=700, anchor="middle", leading=30),
        reward_matrix(72, 405),
        rect_card("adverse-retained", 78, 735, 518, 66, fill=RUST_TINT, stroke=RUST, radius=12, sw=2),
        multiline("adverse-retained-title", 337, 762, ["retain adverse outcomes · route at most once", "no row, objective, or branch deletion"], size=20, fill=RUST, weight=700, anchor="middle", leading=27),

        rect_card("source-quota-rack", 675, 145, 480, 685, fill=NEUTRAL, stroke=MUTED, radius=16, sw=3),
        txt("quota-title", 915, 190, "Fixed source quotas · per bundle", size=25, fill=INK, weight=700, anchor="middle"),
        txt("quota-subtitle", 915, 222, "each specialist owns an independent consumer gate", size=20, fill=MUTED, anchor="middle"),
        pill("quota-main", 700, 255, 165, "Main origin", fill=NAVY_TINT, stroke=NAVY, color=NAVY),
        arrow("main-direct-admission", "M865 276 H1118", color=NAVY, width=5),
        txt("main-direct-label", 988, 255, "direct admission", size=18, fill=NAVY, weight=700, anchor="middle"),

        pill("quota-f1", 700, 334, 145, "F₁ bundle", fill=OCHRE_TINT, stroke=OCHRE, color=OCHRE),
        gate("atomic-f1-gate", 940, 355, 120, 72, ["F₁ gate"], color=RUST),
        arrow("quota-f1-to-gate", "M845 355 H880", color=OCHRE, width=6),
        arrow("atomic-f1-pass", "M1000 355 H1118", color=RUST, width=4, dash="10 8"),
        txt("atomic-f1-pass-label", 1058, 342, "pass", size=17, fill=RUST, weight=700, anchor="middle"),
        rect_card("atomic-f1-shadow", 860, 401, 160, 32, fill=RUST_TINT, stroke=RUST, radius=7, sw=2, dash="6 5"),
        txt("atomic-f1-shadow-label", 940, 423, "fail → shadow", size=18, fill=RUST, weight=700, anchor="middle"),
        arrow("atomic-f1-fail", "M940 391 V401", color=RUST, width=2, dash="6 5"),

        pill("quota-f2", 700, 465, 145, "F₂ bundle", fill=OCHRE_TINT, stroke=OCHRE, color=OCHRE),
        gate("atomic-f2-gate", 940, 486, 120, 72, ["F₂ gate"], color=RUST),
        arrow("quota-f2-to-gate", "M845 486 H880", color=OCHRE, width=6),
        arrow("atomic-f2-pass", "M1000 486 H1118", color=RUST, width=4, dash="10 8"),
        txt("atomic-f2-pass-label", 1058, 473, "pass", size=17, fill=RUST, weight=700, anchor="middle"),
        rect_card("atomic-f2-shadow", 860, 532, 160, 32, fill=RUST_TINT, stroke=RUST, radius=7, sw=2, dash="6 5"),
        txt("atomic-f2-shadow-label", 940, 554, "fail → shadow", size=18, fill=RUST, weight=700, anchor="middle"),
        arrow("atomic-f2-fail", "M940 522 V532", color=RUST, width=2, dash="6 5"),

        pill("quota-f3", 700, 596, 145, "F₃ bundle", fill=OCHRE_TINT, stroke=OCHRE, color=OCHRE),
        gate("atomic-f3-gate", 940, 617, 120, 72, ["F₃ gate"], color=RUST),
        arrow("quota-f3-to-gate", "M845 617 H880", color=OCHRE, width=6),
        arrow("atomic-f3-pass-closed", "M1000 617 H1118", color=MUTED, width=3, dash="4 9"),
        txt("atomic-f3-pass-label", 1058, 604, "inactive until pass", size=15, fill=MUTED, weight=700, anchor="middle"),
        rect_card("atomic-f3-shadow", 820, 670, 240, 38, fill=RUST_TINT, stroke=RUST, radius=8, sw=3, dash="7 5"),
        txt("atomic-f3-shadow-label", 940, 696, "CURRENT SHADOW-ONLY", size=17, fill=RUST, weight=700, anchor="middle"),
        arrow("atomic-f3-fail", "M940 653 V670", color=RUST, width=3, dash="6 5"),
        line("admitted-bus", "M1118 276 V617", color=NAVY, width=4),
        multiline("quota-weight", 915, 748, ["source age + dose are bundle-level", "unfold all valid rows atomically", "average losses · total sample weight = 1"], size=18, fill=INK, weight=700, anchor="middle", leading=27),
        arrow("bundle-to-quota", "M632 300 H675", color=OCHRE, width=6),

        main_card("atomic-main", 1195, 145, 363, 685),
        pill("atomic-main-tag", 1235, 170, 280, "MAIN LEARNER", fill=NAVY, stroke=NAVY, color=WHITE),
        rect_card("atomic-main-replay", 1240, 247, 273, 76, fill=WHITE, stroke=NAVY, radius=12, sw=3),
        txt("atomic-main-replay-label", 1376, 295, "D_M · gate-pass full bundle", size=22, fill=NAVY, weight=700, anchor="middle", family="FreeSerif"),
        arrow("admitted-bus-to-main", "M1118 276 H1195", color=NAVY, width=7),
        rect_card("main-calibration", 1240, 354, 273, 76, fill=WHITE, stroke=TEAL, radius=12, sw=3),
        multiline("main-calibration-label", 1376, 382, ["unchanged baseline", "reward calibration"], size=20, fill=TEAL, weight=700, anchor="middle", leading=27),
        arrow("replay-to-calibration", "M1376 323 V354", color=NAVY, width=4),
        rect_card("atomic-q1", 1240, 475, 273, 70, fill=NAVY_TINT, stroke=NAVY, radius=10, sw=3),
        txt("atomic-q1-label", 1376, 519, "Q₁ᴹ objective-wise update", size=23, fill=NAVY, weight=700, anchor="middle", family="FreeSerif"),
        rect_card("atomic-q2", 1240, 568, 273, 70, fill=NAVY_TINT, stroke=NAVY, radius=10, sw=3),
        txt("atomic-q2-label", 1376, 612, "Q₂ᴹ objective-wise update", size=23, fill=NAVY, weight=700, anchor="middle", family="FreeSerif"),
        rect_card("atomic-q3", 1240, 661, 273, 70, fill=NAVY_TINT, stroke=NAVY, radius=10, sw=3),
        txt("atomic-q3-label", 1376, 705, "Q₃ᴹ objective-wise update", size=23, fill=NAVY, weight=700, anchor="middle", family="FreeSerif"),
        line("calibration-update-spine", "M1376 430 V452 M1376 452 H1218 V696", color=OCHRE, width=4),
        arrow("calibration-to-q1", "M1218 510 H1240", color=OCHRE, width=3),
        arrow("calibration-to-q2", "M1218 603 H1240", color=OCHRE, width=3),
        arrow("calibration-to-q3", "M1218 696 H1240", color=OCHRE, width=3),
        multiline("private-exclusion", 1376, 758, ["private shaping · option state", "ΔPᴺ diagnostic", "remain outside Main reward"], size=18, fill=RUST, weight=700, anchor="middle", leading=24, family="FreeSerif"),
    ]
    return document("Fig. 4-6", "Atomic experience routing", "A complete executed bundle contains the joint action, all user rows and an unmodified U by 3 reward matrix. Main origin is directly quota-admitted, while each specialist owns a separate checked consumer gate. Gate failure keeps that source in shadow lineage, F3 is currently shadow-only, and every admitted bundle has total sample weight one across all three Main objective updates.", "".join(b))


def phase_label(ident: str, y: float, number: str, title: str, color: str) -> str:
    return (
        f'<circle id="{ident}-circle" cx="83" cy="{y}" r="40" fill="{color}"/>'
        + txt(ident+"-number", 83, y+10, number, size=30, fill=WHITE, weight=700, anchor="middle")
        + txt(ident+"-title", 145, y+10, title, size=31, fill=color, weight=700)
    )


def figure_4_7() -> str:
    b: list[str] = [title_block("FIG 4-7", "Training and deployment procedure", "Three phases separate source construction, independent collection, and Main-only use")]
    b += [
        rect_card("phase-1", 42, 130, 1516, 210, fill="#FFFDF8", stroke=OCHRE, radius=18, sw=2),
        phase_label("phase-1-label", 180, "I", "LEO-native source construction", OCHRE),
        rect_card("source-local", 330, 210, 250, 58, fill=WHITE, stroke=OCHRE, radius=12, sw=3),
        txt("source-local-label", 455, 247, "local SNR-greedy source", size=20, fill=OCHRE, weight=700, anchor="middle"),
        rect_card("source-neutral", 330, 280, 250, 44, fill=WHITE, stroke=MUTED, radius=12, sw=2),
        txt("source-neutral-label", 455, 308, "masked-uniform neutral control", size=16, fill=MUTED, anchor="middle"),
        gate("source-gate-a", 660, 250, 130, 120, ["Source", "Gate A"], color=RUST),
        rect_card("immutable-source", 780, 195, 260, 110, fill=OCHRE_TINT, stroke=OCHRE, radius=12, sw=3),
        multiline("immutable-source-label", 910, 235, ["immutable EXP source", "offline · proposed"], size=24, fill=OCHRE, weight=700, anchor="middle", leading=34),
        arrow("source-local-to-gate", "M580 239 H595", color=INK, width=3),
        arrow("source-neutral-to-gate", "M580 302 H610 C625 302 635 286 635 282", color=INK, width=3),
        arrow("source-gate-to-set", "M725 250 H780", color=OCHRE, width=5),
        rect_card("phase1-d1f", 1135, 195, 220, 110, fill=WHITE, stroke=OCHRE, radius=12, sw=4),
        txt("phase1-d1f-label", 1245, 242, "C1-only prefill", size=25, fill=OCHRE, weight=700, anchor="middle"),
        mathlabel("phase1-d1f-symbol", 1208, 282, "D", sub="1", sup="F", size=36, fill=OCHRE),
        arrow("set-to-d1f", "M1040 250 H1135", color=OCHRE, width=7),
        rect_card("no-prefill-main", 1390, 202, 135, 96, fill=RUST_TINT, stroke=RUST, radius=12, sw=3, dash="8 6"),
        multiline("no-prefill-main-label", 1457, 233, ["NO ROUTE", "to Main replay"], size=18, fill=RUST, weight=700, anchor="middle", leading=28),

        rect_card("phase-2", 42, 365, 1516, 270, fill=WHITE, stroke=LINE, radius=18, sw=2),
        phase_label("phase-2-label", 405, "II", "Independent collection and source-specific gates", TEAL),
        txt("phase2-retain-note", 514, 429, "execute · retain all outcomes", size=19, fill=MUTED, weight=700, anchor="middle"),
        pill("lane-main", 330, 440, 180, "Main collection", fill=NAVY_TINT, stroke=NAVY, color=NAVY),
        pill("lane-f1", 330, 486, 180, "F₁ collection", fill=OCHRE_TINT, stroke=OCHRE, color=OCHRE),
        pill("lane-f2", 330, 532, 180, "F₂ collection", fill=OCHRE_TINT, stroke=OCHRE, color=OCHRE),
        pill("lane-f3", 330, 578, 180, "F₃ collection", fill=OCHRE_TINT, stroke=OCHRE, color=OCHRE),
        rect_card("update-f1", 560, 489, 180, 36, fill=OCHRE_TINT, stroke=OCHRE, radius=9, sw=2),
        txt("update-f1-label", 650, 514, "update F₁", size=20, fill=OCHRE, weight=700, anchor="middle", family="FreeSerif"),
        rect_card("update-f2", 560, 535, 180, 36, fill=OCHRE_TINT, stroke=OCHRE, radius=9, sw=2),
        txt("update-f2-label", 650, 560, "update F₂", size=20, fill=OCHRE, weight=700, anchor="middle", family="FreeSerif"),
        rect_card("update-f3", 560, 581, 180, 36, fill=OCHRE_TINT, stroke=OCHRE, radius=9, sw=2),
        txt("update-f3-label", 650, 606, "update F₃", size=20, fill=OCHRE, weight=700, anchor="middle", family="FreeSerif"),
        arrow("f1-to-private-update", "M510 507 H560", color=OCHRE, width=4),
        arrow("f2-to-private-update", "M510 553 H560", color=OCHRE, width=4),
        arrow("f3-to-private-update", "M510 599 H560", color=OCHRE, width=4),
        gate("phase2-f1-gate", 840, 507, 116, 54, ["F₁ gate"], color=RUST),
        gate("phase2-f2-gate", 840, 553, 116, 54, ["F₂ gate"], color=RUST),
        gate("phase2-f3-gate", 840, 599, 116, 54, ["F₃ gate"], color=RUST),
        arrow("f1-update-to-gate", "M740 507 H782", color=OCHRE, width=5),
        arrow("f2-update-to-gate", "M740 553 H782", color=OCHRE, width=5),
        arrow("f3-update-to-gate", "M740 599 H782", color=OCHRE, width=5),
        arrow("f1-gate-pass-route", "M898 507 H1120", color=RUST, width=4, dash="9 7"),
        arrow("f2-gate-pass-route", "M898 553 H1120", color=RUST, width=4, dash="9 7"),
        txt("f1-gate-outcome", 1005, 495, "pass routes · fail shadows", size=16, fill=RUST, weight=700, anchor="middle"),
        txt("f2-gate-outcome", 1005, 541, "pass routes · fail shadows", size=16, fill=RUST, weight=700, anchor="middle"),
        rect_card("phase2-shadow", 925, 581, 180, 36, fill=RUST_TINT, stroke=RUST, radius=8, sw=3, dash="8 6"),
        txt("phase2-shadow-label", 1015, 606, "CURRENT SHADOW-ONLY", size=16, fill=RUST, weight=700, anchor="middle"),
        arrow("f3-gate-to-shadow", "M898 599 H925", color=RUST, width=4, dash="8 6"),
        rect_card("phase2-main-update", 1120, 430, 385, 187, fill=NAVY_TINT, stroke=NAVY, radius=14, sw=4),
        multiline("phase2-main-update-label", 1312, 466, ["Main origin: direct quota admission", "gate-pass complete bundles → Main replay", "unchanged calibration → Q₁ᴹ, Q₂ᴹ, Q₃ᴹ", "fixed quotas · total bundle weight = 1"], size=20, fill=NAVY, weight=700, anchor="middle", leading=34, family="FreeSerif"),
        arrow("main-lane-to-update", "M510 461 H1085 V466 H1120", color=NAVY, width=5),

        rect_card("phase-3", 42, 660, 1516, 205, fill=NAVY_TINT, stroke=NAVY, radius=18, sw=3),
        phase_label("phase-3-label", 700, "III", "Main-only evaluation and deployment", NAVY),
        clipped_card("removed-specialists", 335, 730, 285, 100, fill=WHITE),
        txt("removed-specialists-label", 477, 772, "F₁ · F₂ · F₃ removed", size=26, fill=OCHRE, weight=700, anchor="middle", family="FreeSerif"),
        txt("removed-specialists-note", 477, 809, "specialist dose = 0", size=24, fill=MUTED, anchor="middle"),
        line("removed-specialists-x1", "M352 744 L603 816", color=RUST, width=4),
        line("removed-specialists-x2", "M603 744 L352 816", color=RUST, width=4),
        main_card("phase3-main", 725, 730, 265, 100),
        txt("phase3-main-label", 857, 772, "Main Q₁ᴹ · Q₂ᴹ · Q₃ᴹ", size=25, fill=NAVY, weight=700, anchor="middle", family="FreeSerif"),
        txt("phase3-main-note", 857, 808, "one deployment policy", size=22, fill=MUTED, anchor="middle"),
        rect_card("masked-greedy", 1070, 730, 220, 100, fill=WHITE, stroke=NAVY, radius=50, sw=3),
        multiline("masked-greedy-label", 1180, 768, ["masked-greedy", "per-user action"], size=23, fill=NAVY, weight=700, anchor="middle", leading=31),
        rect_card("deployment-output", 1370, 730, 150, 100, fill=NAVY, stroke=NAVY, radius=14, sw=3),
        txt("deployment-output-label", 1445, 788, "DEPLOY", size=28, fill=WHITE, weight=700, anchor="middle"),
        arrow("phase3-main-to-greedy", "M990 780 H1070", color=NAVY, width=5),
        arrow("phase3-greedy-to-deploy", "M1290 780 H1370", color=NAVY, width=5),
        txt("forbidden-boundary", 930, 850, "No voting · no auction · no coordination · no action/reward fusion · no override", size=21, fill=RUST, weight=700, anchor="middle"),
    ]
    return document("Fig. 4-7", "Training and deployment procedure", "Phase I builds an immutable LEO-native source and prefills only the C1 replay. Phase II independently collects Main and specialist experience, updates specialists, gates complete bundles, and updates Main. Phase III removes every specialist and deploys only Main with masked-greedy actions.", "".join(b))


FIGURES = {
    "fig2-1-main-modqn-baseline.svg": figure_2_1,
    "fig3-1-physical-leo-system.svg": figure_3_1,
    "fig4-1-method-overview.svg": figure_4_1,
    "fig4-2-learner-topology.svg": figure_4_2,
    "fig4-6-atomic-experience-routing.svg": figure_4_6,
    "fig4-7-training-deployment-flow.svg": figure_4_7,
}


def main() -> None:
    for name, build in FIGURES.items():
        path = OUT / name
        path.write_text(build(), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
