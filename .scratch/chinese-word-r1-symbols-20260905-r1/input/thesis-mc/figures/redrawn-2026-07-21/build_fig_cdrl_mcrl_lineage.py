#!/usr/bin/env python3
"""CDRL -> MCRL causal training-flow comparison (2026-07-22).

Truth source: thesis-mc/ch4-method.md §§4.1--4.6 and the Fig. 4-3 caption.
The figure shows where the Catfish strategies act on data, reward, and
training updates.  It deliberately does *not* imply Catfish-to-Main weight,
policy, or shaped-reward transfer: the two visible Main conduits are the
middle-tier raw transition and the periodic mixed batch.
"""
import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
import figkit as fk


HERE = pathlib.Path(__file__).parent
STEM = "fig-cdrl-mcrl-lineage"
FS = 54
HEAD = 60
# Keep a visibly calm text-to-frame margin after enlarging the type.  These
# are intentionally larger than the minimum measured fit: the figure is read
# at thesis scale, where cramped labels are much more damaging than white space.
HPAD = 56
VPAD = 36
# The wider canvas is printed at 175 mm, so 1.7 px preserves the validator's
# 0.25 pt minimum without making the deliberately light connectors heavy.
STROKE = 1.7
INK, MAIN, CF, MUTE, CONTRIB = fk.INK, fk.MAIN, fk.CF, fk.MUTE, fk.CONTRIB
NN_LINK = MUTE
MLP_LAYERS = (3, 4, 3)
SPARSE = frozenset({0, 1, 2, 5, 6, 7, 9, 11, 12, 14, 15, 16, 19, 20, 21, 23})


def card(nid, lines, cx, y, *, stroke=INK, fill="#ffffff", shape=None,
         stroke_width=STROKE, cross=False):
    """Measured two-line editable card; every visible label uses the same size."""
    width = int(2 * round((max(fk.text_w(line, FS) for line in lines) + 2 * HPAD) / 2))
    height = int(2 * round((len(lines) * FS * 1.2 + 2 * VPAD) / 2))
    style = {"fill": fill, "stroke": stroke, "strokeWidth": stroke_width,
             "fontFamily": fk.SERIF, "fontSize": FS, "textFill": "#000000", "rx": 4}
    if shape:
        style["shape"] = shape
    if cross:
        style["crossSection"] = True
    node = {"id": nid, "label": list(lines), "x": int(cx - width / 2), "y": int(y),
            "w": width, "h": height, "style": style}
    fig.add(node)
    return node


def diamond(nid, lines, cx, y, *, stroke=INK, fill="#ffffff"):
    """Decision diamond with usable text clearance, not merely rectangular fit."""
    # At the two text baselines a diamond is substantially narrower than its
    # bounding rectangle.  The 680 x 340 minimum leaves real clearance at
    # both baselines for the two-line label, rather than merely fitting its
    # rectangular bounding box inside the diamond.
    width = max(680, int(2 * round(
        (max(fk.text_w(line, FS) for line in lines) + 2 * (HPAD + 58)) / 2
    )))
    height = max(340, int(2 * round(
        (len(lines) * FS * 1.2 + 2 * (VPAD + 24)) / 2
    )))
    node = {
        "id": nid, "label": list(lines), "x": int(cx - width / 2), "y": int(y),
        "w": width, "h": height,
        "style": {"fill": fill, "stroke": stroke, "strokeWidth": STROKE,
                  "fontFamily": fk.SERIF, "fontSize": FS, "textFill": "#000000",
                  # The widest line sits below the narrow top of the diamond;
                  # this puts the two-line block slightly below geometric centre.
                  "textOffsetY": 9, "rx": 4, "shape": "diamond"},
    }
    fig.add(node)
    return node


def port(nid, x, y):
    fig.add({
        "id": nid, "label": [""], "x": int(x) - 1, "y": int(y) - 1, "w": 2, "h": 2,
        "style": {"fill": "none", "stroke": "none", "crossSection": True,
                  "fontFamily": fk.SERIF, "fontSize": FS, "textFill": "none"},
    })


def panel(nid, label, x, *, w=1530, h=2400):
    sec = fig.sec(nid, label, x, 30, w, h)
    sec["style"] = {"fill": "#ffffff", "stroke": MUTE, "strokeWidth": STROKE, "rx": 5,
                    "fontFamily": fk.SERIF, "fontSize": HEAD, "textFill": "#000000"}
    return sec


def group(nid, label, x, y, w, h, *, stroke):
    """A quiet collective enclosure for the three MCRL Q-heads."""
    sec = fig.sec(nid, label, x, y, w, h)
    sec["style"] = {"fill": "#ffffff", "stroke": stroke, "strokeWidth": STROKE, "rx": 4,
                    "fontFamily": fk.SERIF, "fontSize": FS, "textFill": "#000000"}
    return sec


def mlp(nid, label, x, y, *, w=280, h=210, stroke=MAIN, fill="#ffffff"):
    """The required 3x4x3 network, with subdued representative links."""
    frame = fig.sec(f"{nid}-frame", " ", x, y, w, h)
    frame["style"] = {"fill": fill, "stroke": stroke, "strokeWidth": STROKE, "rx": 3,
                       "fontFamily": fk.SERIF, "fontSize": FS, "textFill": "#000000"}
    label_w = int(2 * round((fk.text_w(label, FS) + 2 * HPAD) / 2))
    label_h = int(2 * round((FS * 1.2 + 2 * VPAD) / 2))
    fig.add({
        "id": f"{nid}-label", "label": [label],
        "x": int(x + (w - label_w) / 2), "y": int(y), "w": label_w, "h": label_h,
        "crossSection": True,
        "style": {"stroke": "none", "fill": "none", "strokeWidth": STROKE,
                  "fontFamily": fk.SERIF, "fontSize": FS, "textFill": "#000000",
                  "textOffsetY": -18, "rx": 0, "crossSection": True},
    })
    left, inner_w = x + 56, w - 112
    mid = (y + 108 + y + h - 18) / 2
    cols = []
    for layer, count in enumerate(MLP_LAYERS):
        cx = left + layer * inner_w / 2
        top = mid - (count - 1) * 17 / 2
        cols.append([(int(round(cx)), int(round(top + row * 17))) for row in range(count)])
    idx = 0
    for src, dst in zip(cols, cols[1:]):
        for x1, y1 in src:
            for x2, y2 in dst:
                if idx in SPARSE:
                    fig.spec["lines"].append({
                        "id": f"{nid}-link-{idx}", "from": {"x": x1, "y": y1},
                        "to": {"x": x2, "y": y2}, "role": "axis",
                        "style": {"stroke": NN_LINK, "strokeWidth": 1.0},
                    })
                idx += 1
    for layer, col in enumerate(cols, start=1):
        for row, (cx, cy) in enumerate(col, start=1):
            fig.spec["points"].append({
                "id": f"{nid}-n-{layer}-{row}", "x": cx, "y": cy,
                "style": {"radius": 6, "fill": "#ffffff", "stroke": INK,
                          "strokeWidth": STROKE},
            })
    port(f"{nid}-in", x, y + h / 2)
    port(f"{nid}-out", x + w, y + h / 2)
    port(f"{nid}-top", x + w / 2, y)
    port(f"{nid}-bottom", x + w / 2, y + h)


def direct(eid, src, dst, *, stroke=INK, width=STROKE, from_anchor="right", to_anchor="left"):
    fig.edge(eid, src, dst, fromAnchor=from_anchor, toAnchor=to_anchor,
             style={"stroke": stroke, "strokeWidth": width})


def vroute(eid, src, dst, mid_y, *, stroke=INK, width=STROKE):
    """Bottom-to-top connector with an orthogonal, deliberately empty bend row."""
    fig.edge(eid, src, dst, fromAnchor="bottom", toAnchor="top",
             waypoints=[{"x": fig.cx(src), "y": mid_y},
                        {"x": fig.cx(dst), "y": mid_y}],
             style={"stroke": stroke, "strokeWidth": width})


def hroute(eid, src, dst, mid_x, *, stroke=INK, width=STROKE, from_anchor="right",
           to_anchor="left"):
    """Side-to-side connector with an orthogonal, deliberately empty bend column."""
    fig.edge(eid, src, dst, fromAnchor=from_anchor, toAnchor=to_anchor,
             waypoints=[{"x": mid_x, "y": fig.cy(src)},
                        {"x": mid_x, "y": fig.cy(dst)}],
             style={"stroke": stroke, "strokeWidth": width})


def bottom_to_right(eid, src, dst, *, stroke=INK):
    """A one-elbow local transfer: down from a pool, then into a right edge."""
    fig.edge(eid, src, dst, fromAnchor="bottom", toAnchor="right",
             waypoints=[{"x": fig.cx(src), "y": fig.cy(dst)}],
             style={"stroke": stroke, "strokeWidth": STROKE})


def side_to_top(eid, src, dst, side_x, mid_y, *, stroke=INK, from_anchor="left"):
    """Exit a pool sideways, then enter a lower mixer from its top edge."""
    fig.edge(eid, src, dst, fromAnchor=from_anchor, toAnchor="top",
             waypoints=[{"x": side_x, "y": fig.cy(src)},
                        {"x": side_x, "y": mid_y},
                        {"x": fig.cx(dst), "y": mid_y}],
             style={"stroke": stroke, "strokeWidth": STROKE})


def bottom_to_left(eid, src, dst, mid_y, side_x, *, stroke=INK):
    """Leave a source below its local row, then reach a lower operator from the left."""
    fig.edge(eid, src, dst, fromAnchor="bottom", toAnchor="left",
             waypoints=[{"x": fig.cx(src), "y": mid_y},
                        {"x": side_x, "y": mid_y},
                        {"x": side_x, "y": fig.cy(dst)}],
             style={"stroke": stroke, "strokeWidth": STROKE})


fig = fk.Fig(
    "CDRL and MCRL strategy-level training comparison",
    3310,
    2460,
    "Strategy-level comparison of CDRL and MCRL. Each panel is arranged as a "
    "main learning loop and a Catfish learning loop, with the Catfish strategies "
    "attached to the data or update edge they affect. No effectiveness claim.",
)
fig.spec["style"] = copy.deepcopy(fk.STYLE)
for scope in ("node", "section", "annotation"):
    fig.spec["style"][scope]["fontSize"] = FS
for scope in ("node", "edge", "section"):
    fig.spec["style"][scope]["strokeWidth"] = STROKE
fig.spec["style"]["edge"]["labelFontSize"] = FS
fig.spec["style"]["annotation"]["fontSize"] = FS
fig.spec["points"] = []
fig.spec["lines"] = []


# This is an overview, not a vertical time-line.  The two spatial loops show
# the Main and Catfish learning systems; the five compact operators show where
# the strategies intervene.  Threshold details and loss expansions remain in
# the dedicated mechanism figures.
C, M = 30, 1640
panel("c", "CDRL", C, w=1580)
panel("m", "MCRL", M, w=1640)


# ── CDRL: one Main loop and one Catfish loop ──────────────────────────────
# The primary Main loop is deliberately aligned as a set of straight arrows.
# Only feedback and cross-pool transfer take an orthogonal rail.
card("c-state", ["State"], C + 170, 222, stroke=MAIN)
mlp("c-main-q", "Q^M", C + 350, 185, w=270, h=210)
card("c-main-rollout", ["Main rollout", "a^M"], C + 850, 189, stroke=MAIN)
card("c-main-buffer", ["D_M"], C + 850, 465, stroke=MAIN, shape="cylinder")
card("c-main-update", ["Main TD", "β_M"], C + 485, 432, stroke=MAIN)
card("c-mix", ["Periodic mix", "D_M + D_CF"], C + 485, 715, stroke=CF)

# State branches vertically to the Catfish Q; this replaces the previous
# long, multi-bend left loop.
mlp("c-cf-q", "Q^CF", C + 35, 1100, w=270, h=210, stroke=CF)
card("c-cf-rollout", ["CF rollout", "a^CF"], C + 600, 1104, stroke=CF)
diamond("c-router", ["EE stratification", "high / middle"], C + 1130, 1035,
        stroke=CF)
card("c-reward", ["Competitive reward"], C + 600, 1395, stroke=CF)
card("c-cf-buffer", ["D_CF"], C + 1130, 1420, stroke=CF, shape="cylinder")
card("c-cf-update", ["Catfish TD", "β_CF > β_M"], C + 600, 1605, stroke=CF)

direct("c-state-main", "c-state", "c-main-q-in", stroke=MAIN)
direct("c-state-cf", "c-state", "c-cf-q-top", stroke=CF,
       from_anchor="bottom", to_anchor="top")
direct("c-q-to-main-rollout", "c-main-q-out", "c-main-rollout", stroke=MAIN)
direct("c-main-store", "c-main-rollout", "c-main-buffer", stroke=MAIN,
       from_anchor="bottom", to_anchor="top")
direct("c-main-buffer-to-update", "c-main-buffer", "c-main-update", stroke=MAIN,
       from_anchor="left", to_anchor="right")
direct("c-main-feedback", "c-main-update", "c-main-q-bottom", stroke=MAIN,
       from_anchor="top", to_anchor="bottom")

direct("c-q-to-cf-rollout", "c-cf-q-out", "c-cf-rollout", stroke=CF)
direct("c-ee-route", "c-cf-rollout", "c-router", stroke=CF)
direct("c-router-high", "c-router", "c-cf-buffer", stroke=CF,
       from_anchor="bottom", to_anchor="top")
fig.edge("c-router-middle", "c-router", "c-main-buffer", fromAnchor="right", toAnchor="right",
         waypoints=[{"x": C + 1490, "y": fig.cy("c-router")},
                    {"x": C + 1490, "y": fig.cy("c-main-buffer")}],
         style={"stroke": MAIN, "strokeWidth": STROKE})
direct("c-rollout-reward", "c-cf-rollout", "c-reward", stroke=CF,
       from_anchor="bottom", to_anchor="top")
direct("c-reward-update", "c-reward", "c-cf-update", stroke=CF,
       from_anchor="bottom", to_anchor="top")
bottom_to_right("c-cf-buffer-to-update", "c-cf-buffer", "c-cf-update", stroke=CF)
fig.edge("c-cf-feedback", "c-cf-update", "c-cf-q-bottom", fromAnchor="left", toAnchor="bottom",
         waypoints=[{"x": C + 170, "y": fig.cy("c-cf-update")}],
         style={"stroke": CF, "strokeWidth": STROKE})
bottom_to_right("c-main-mix", "c-main-buffer", "c-mix", stroke=MAIN)
fig.edge("c-cf-mix", "c-cf-buffer", "c-mix", fromAnchor="right", toAnchor="bottom",
         waypoints=[{"x": C + 1520, "y": fig.cy("c-cf-buffer")},
                    {"x": C + 1520, "y": 995},
                    {"x": fig.cx("c-mix"), "y": 995}],
         style={"stroke": CF, "strokeWidth": STROKE})
direct("c-mix-main", "c-mix", "c-main-update", stroke=MAIN,
       from_anchor="top", to_anchor="bottom")


# ── MCRL: context-normalized, three-head Main and Catfish loops ──────────
# The MCRL main loop follows the same straight-arrow grammar as CDRL.  The
# two long rails are retained only where a real cross-loop transfer must pass
# around the role-specific Catfish rollout block.
card("m-state", ["State + context"], M + 515, 100, stroke=MAIN, fill=CONTRIB)
card("m-normalize", ["Context normalization"], M + 515, 270, stroke=MAIN, fill=CONTRIB)
group("m-main-group", "Main Qs", M + 50, 480, 860, 340, stroke=MAIN)
port("m-main-group-top", M + 515, 480)
port("m-main-group-out", M + 910, 675)
port("m-main-group-bottom", M + 675, 820)
for i, x in enumerate((M + 80, M + 360, M + 640), start=1):
    mlp(f"m-main-q{i}", f"Q_{i}", x, 575, w=240, h=200)
card("m-main-rollout", ["Main rollout", "arg max"], M + 1180, 574, stroke=MAIN)
card("m-main-buffer", ["D_M"], M + 1180, 916, stroke=MAIN, shape="cylinder")
card("m-main-update", ["Main TD", "β_M"], M + 675, 883, stroke=MAIN)
card("m-lcap", ["L_cap", "training only"], M + 255, 883, stroke=CF, fill=CONTRIB)
card("m-mix", ["Periodic mix", "D_M + D_CF"], M + 675, 1150, stroke=CF)

group("m-cf-group", "Catfish Qs", M + 50, 1420, 860, 340, stroke=CF)
port("m-cf-group-in", M + 50, 1615)
port("m-cf-group-out", M + 910, 1615)
port("m-cf-group-bottom", M + 675, 1760)
port("m-cf-group-feedback", M + 300, 1760)
for i, x in enumerate((M + 80, M + 360, M + 640), start=1):
    mlp(f"m-cf-q{i}", f"Q_{i}^CF", x, 1515, w=240, h=200, stroke=CF)
card("m-roles", ["3 objective-wise", "CF rollouts"], M + 1180, 1514,
     stroke=CF, fill=CONTRIB)
diamond("m-router", ["EE stratification", "high / middle"], M + 1180, 1830,
        stroke=CF)
card("m-reward", ["Competitive r_1", "r_2, r_3 raw"], M + 580, 1830, stroke=CF)
card("m-cf-buffer", ["D_CF"], M + 1180, 2205, stroke=CF, shape="cylinder")
card("m-cf-update", ["Catfish TD", "β_CF > β_M"], M + 580, 2172, stroke=CF)

direct("m-state-normalize", "m-state", "m-normalize", stroke=MAIN,
       from_anchor="bottom", to_anchor="top")
direct("m-normalize-main", "m-normalize", "m-main-group-top", stroke=MAIN,
       from_anchor="bottom", to_anchor="top")
fig.edge("m-normalize-cf", "m-normalize", "m-cf-group-in", fromAnchor="left", toAnchor="left",
         waypoints=[{"x": M + 25, "y": fig.cy("m-normalize")},
                    {"x": M + 25, "y": fig.cy("m-cf-group-in")}],
         style={"stroke": CF, "strokeWidth": STROKE})
direct("m-main-group-to-rollout", "m-main-group-out", "m-main-rollout", stroke=MAIN)
direct("m-main-store", "m-main-rollout", "m-main-buffer", stroke=MAIN,
       from_anchor="bottom", to_anchor="top")
direct("m-main-buffer-to-update", "m-main-buffer", "m-main-update", stroke=MAIN,
       from_anchor="left", to_anchor="right")
direct("m-main-feedback", "m-main-update", "m-main-group-bottom", stroke=MAIN,
       from_anchor="top", to_anchor="bottom")
direct("m-lcap-update", "m-lcap", "m-main-update", stroke=CF,
       from_anchor="right", to_anchor="left")

direct("m-cf-rollout", "m-cf-group-out", "m-roles", stroke=CF)
direct("m-roles-router", "m-roles", "m-router", stroke=CF,
       from_anchor="bottom", to_anchor="top")
direct("m-router-high", "m-router", "m-cf-buffer", stroke=CF,
       from_anchor="bottom", to_anchor="top")
fig.edge("m-router-middle", "m-router", "m-main-buffer", fromAnchor="right", toAnchor="right",
         waypoints=[{"x": M + 1540, "y": fig.cy("m-router")},
                    {"x": M + 1540, "y": fig.cy("m-main-buffer")}],
         style={"stroke": MAIN, "strokeWidth": STROKE})
vroute("m-roles-reward", "m-roles", "m-reward", 1790, stroke=CF)
direct("m-reward-update", "m-reward", "m-cf-update", stroke=CF,
       from_anchor="bottom", to_anchor="top")
direct("m-cf-buffer-to-update", "m-cf-buffer", "m-cf-update", stroke=CF,
       from_anchor="left", to_anchor="right")
fig.edge("m-cf-feedback", "m-cf-update", "m-cf-group-feedback", fromAnchor="left", toAnchor="bottom",
         waypoints=[{"x": M + 300, "y": fig.cy("m-cf-update")}],
         style={"stroke": CF, "strokeWidth": STROKE})
bottom_to_right("m-main-mix", "m-main-buffer", "m-mix", stroke=MAIN)
fig.edge("m-cf-mix", "m-cf-buffer", "m-mix", fromAnchor="right", toAnchor="bottom",
         waypoints=[{"x": M + 1570, "y": fig.cy("m-cf-buffer")},
                    {"x": M + 1570, "y": 1383},
                    {"x": fig.cx("m-mix"), "y": 1383}],
         style={"stroke": CF, "strokeWidth": STROKE})
direct("m-mix-main", "m-mix", "m-main-update", stroke=MAIN,
       from_anchor="top", to_anchor="bottom")


out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
