#!/usr/bin/env python3
"""SLIDE-GRADE 能效分層（自論文 fig-stratification 改編）。

簡報版與論文版同結構（1→1→3 分流已經很適合投影）；差別＝字大、線粗、留白收緊。
視覺鍵沿用：赭框＝鯰魚／僅訓練期機制；sand 填色＝本論文貢獻；灰＝捨棄（去強調）。
內容紅線：只畫機制、無數值、無效果宣稱、不出現禁用方法詞。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-stratification"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"
OUT_PNG = HERE.parents[2] / "slides" / "figures" / f"{STEM}.png"

fig = fk.Fig(
    "Energy-efficiency stratification (slide)",
    2400, 760,
    "Three-way routing of catfish transitions in the implemented MCRL framework. "
    "Mechanism only — no effectiveness claim, no result numbers.",
)

GAPV = 70
Y_CF, Y_MAIN, Y_DIS = 40, 40 + 150 + GAPV, 40 + 2 * (150 + GAPV)   # 40 / 260 / 480

trans = fig.add(fk.box("trans", ["Catfish transition", "energy efficiency η"],
                       70, Y_MAIN, fk.CF, contrib=True))
rule = fig.add(fk.box("rule", ["Stratify by quantiles", "q_lo, q_hi over window W"],
                      fig.right("trans") + 150, Y_MAIN, fk.CF, contrib=True))
fig.n("rule")["style"]["strokeWidth"] = 3.0   # 強調＝本圖主題

XP = fig.right("rule") + 210
fig.add(fk.box("cf_pool", ["Catfish replay buffer", "highest band"], XP, Y_CF, fk.INK, contrib=True))
fig.add(fk.box("main_pool", ["Main replay buffer", "middle band"], XP, Y_MAIN, fk.INK))
fig.add(fk.box("discard", ["Discard", "lowest band"], XP, Y_DIS, fk.MUTE))

X_FAN = XP - 90   # 分流扇出的垂直走廊

E = fig.edge
E("e-trans-rule", "trans", "rule", fromAnchor="right", toAnchor="left")
E("e-rule-main", "rule", "main_pool", fromAnchor="right", toAnchor="left")
E("e-rule-cf", "rule", "cf_pool", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_FAN, "y": fig.cy("rule")}, {"x": X_FAN, "y": fig.cy("cf_pool")}])
E("e-rule-discard", "rule", "discard", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_FAN, "y": fig.cy("rule")}, {"x": X_FAN, "y": fig.cy("discard")}])

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
