#!/usr/bin/env python3
"""SLIDE-GRADE 圖 4-2 MCRL 整體架構（自論文 fig4-2 改編）。

簡報簡化：保留「部署帶（實線）vs 僅訓練期帶（虛線）」這個本圖的重點；訓練帶壓成一列四框
（鯰魚角色 → 分層路由 → 週期性介入 ← 競爭獎勵＋容量懲罰），一條上行邊表示訓練 Q 網路。
部署帶＝基準 MODQN 迴圈；壅塞情境／正規化＝本論文新增（sand，精確符號在專圖）。
視覺鍵：實線帶＝部署；虛線帶＝僅訓練期；navy＝部署；赭＝鯰魚／訓練機制；sand＝本論文貢獻。
內容紅線：只畫結構、無數值、無效果宣稱、無「鯰魚驅動改善」因果宣稱。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-fig4-2-mccrl-architecture"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "MCRL overall architecture (slide)",
    2600, 1120,
    "Architecture of the implemented MCRL framework. Structure only — no effectiveness "
    "claim, no result numbers.",
)

# 幾何收緊（2026-07-20，投影字級用）：投影 pt = 42×72×min(12.80/W_px, h_in/H_px)。原版
# W=2304 / H=940 ⇒ 只有 16.8 pt，比它要取代的原生 pptx 圖（18–20 pt）還小。以下只動
# **留白與最長標籤**，不動任何結構、顏色語意或內容紅線：section 上下留白 360→300 / 460→320，
# 兩帶間距 60→50，並把每個框最長的那一行縮短（語意不變）。
sec_dep = fig.sec("deploy", "Deployment path", 40, 40, 100, 300)
sec_trn = fig.sec("train", "Training only", 40, 390, 100, 320, dash="7 5")

# ── 部署帶（實線）：基準 MODQN 迴圈 ─────────────────────────────────────────────
DEPLOY = [
    ("env", ["Environment", "beam cap v_max"]),
    ("context", ["Congestion context", "+ normalization"]),
    ("qnets", ["Three Q-networks", "Q_1, Q_2, Q_3"]),
    ("select", ["Scalarize by Ω", "per-user arg max"]),
]
fk.spread_row(fig, DEPLOY, 140, 90, 2050, stroke=fk.MAIN, contribs={"context"})
fig.n("qnets")["style"]["strokeWidth"] = 3.0

# ── 僅訓練期帶（虛線）：訓練框對齊部署框，上行邊訓練 Q 網路 ─────────────────────
YT = 520
# "competes on r_1"：第二行必須留住「只作用在第一個目標」這件事（ch4 §4.5），否則架構圖
# 會誤示競爭項作用在三個目標上。第一行 18 字已是本框最寬行 ⇒ 這行 ≤18 字不吃寬度。
fig.add(fk.box("catfish", ["Catfish Q-networks", "competes on r_1"], 0, YT, fk.CF,
               section="train", contrib=True))
fig.add(fk.box("buffers", ["Stratified routing", "to replay buffers"], 0, YT, fk.INK,
               section="train"))
fig.add(fk.box("interv", ["Periodic intervention", "mixed batch"], 0, YT, fk.CF,
               section="train", contrib=True))
fig.add(fk.box("cappen", ["Capacity penalty", "into training loss"], 0, YT, fk.CF,
               section="train", contrib=True))
fig.center_on("catfish", "env")
fig.center_on("buffers", "context")
fig.center_on("interv", "qnets")
fig.center_on("cappen", "select")

# section 框住實際 box 範圍（否則 crop 會被過寬的 section 撐大 → targetWidthMm 破 300）
xs = [n["x"] for n in fig.spec["nodes"]] + [n["x"] + n["w"] for n in fig.spec["nodes"]]
x0, x1 = min(xs) - 30, max(xs) + 30
for s in (sec_dep, sec_trn):
    s["x"], s["w"] = x0, x1 - x0

E = fig.edge
E("e-env-context", "env", "context", fromAnchor="right", toAnchor="left")
E("e-context-q", "context", "qnets", fromAnchor="right", toAnchor="left")
E("e-q-select", "qnets", "select", fromAnchor="right", toAnchor="left")
E("e-select-env", "select", "env", fromAnchor="top", toAnchor="top", label="joint action",
  waypoints=[{"x": fig.cx("select"), "y": 85}, {"x": fig.cx("env"), "y": 85}])

# 跨帶邊的標籤要離開 section 邊框：labelDy 推進虛線帶內、boxes 之上的空白帶（390..520）。
E("e-env-catfish", "env", "catfish", fromAnchor="bottom", toAnchor="top",
  label="transitions", style={"labelDx": 160, "labelDy": 85})
E("e-catfish-buffers", "catfish", "buffers", fromAnchor="right", toAnchor="left")
E("e-buffers-interv", "buffers", "interv", fromAnchor="right", toAnchor="left")
# USER 2026-07-20 修正（同 ba44b9e3 對 fig 4-3 的修正）：訓練期機制**不串接**。
# 週期性介入＝對主要代理多做一次混合批次更新；容量懲罰＝直接加進主要代理的訓練損失
# （ch4 §4.6／圖 4-2 圖說）。兩者各自接到 Q 網路，彼此之間沒有資料流。
# 兩條上行邊都不掛標籤：方框本文已說明各自角色（額外一次更新／進訓練損失），
# 且兩條邊在 Q 網路底部僅相距 35px，任一標籤都會被判定可能歸屬另一條邊。
E("e-interv-q", "interv", "qnets", fromAnchor="top", toAnchor="bottom")
# 無標籤：方框本文已寫 "into the training loss"，再掛邊標籤會與上一條邊的標籤互相干擾。
E("e-cappen-q", "cappen", "qnets", fromAnchor="top", toAnchor="bottom-right",
  waypoints=[{"x": fig.cx("cappen"), "y": 455}, {"x": fig.cx("qnets") + 35, "y": 455}])

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
