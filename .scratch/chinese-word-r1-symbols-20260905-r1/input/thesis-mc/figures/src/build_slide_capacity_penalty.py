#!/usr/bin/env python3
"""SLIDE-GRADE 容量懲罰 L_cap（自論文 fig-capacity-penalty 改編）。

簡報簡化：六格鏈併成五格（末兩格「平方懲罰」「併入損失」合成一格），3+2 蛇行。
視覺鍵：sand 填色＝本論文貢獻（純量化價值沿用＝白底）；赭框＝訓練期機制。
符號沿用 notation-table §13：Π／Δ_s／Ṽ_u／π_u／L_cap（各帶一個非阻擋 R14 警告）。
內容紅線：只畫機制、無數值、無效果宣稱。§4.6 明載單靠此項不保證散開＝進講稿，不上簡報。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-capacity-penalty"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "Capacity penalty (slide)",
    2400, 620,
    "Differentiable capacity penalty added to the training loss. "
    "Mechanism only — no effectiveness claim, no result numbers.",
)

Y1, Y2 = 40, 40 + 150 + 130   # 40 / 320
# 上列 L→R：純量化價值（沿用，白）→ 逐使用者偏好 → 逐波束壓力
ROW1 = [
    ("val", ["Scalarized value", "V_u(a)"]),
    ("soft", ["Per-user preference", "softmax π_u(a)"]),
    ("press", ["Per-beam pressure Π", "summed over users"]),
]
fk.spread_row(fig, ROW1, Y1, 70, 2000, stroke=fk.MAIN,
              strokes={"soft": fk.CF, "press": fk.CF}, contribs={"soft", "press"})

# 下列（蛇行，flow 由右到左）：尾端質量 → 容量懲罰（強調，併入損失）
tail = fig.add(fk.box("tail", ["Tail mass Δ_s", "beyond the top v_max"], 0, Y2, fk.CF, contrib=True))
fig.center_on("tail", "press")                              # 蛇行純垂直落點
pen = fig.add(fk.box("pen", ["Capacity penalty L_cap", "added to the training loss"], 0, Y2,
                     fk.CF, contrib=True))
pen["x"] = fig.n("tail")["x"] - pen["w"] - 200
fig.n("pen")["style"]["strokeWidth"] = 3.0   # 強調＝容量懲罰本體

E = fig.edge
E("e-val-soft", "val", "soft", fromAnchor="right", toAnchor="left")
E("e-soft-press", "soft", "press", fromAnchor="right", toAnchor="left")
E("e-press-tail", "press", "tail", fromAnchor="bottom", toAnchor="top")   # 換列往下
E("e-tail-pen", "tail", "pen", fromAnchor="left", toAnchor="right")

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
