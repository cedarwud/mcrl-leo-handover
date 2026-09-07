#!/usr/bin/env python3
"""SLIDE-GRADE 圖 4-7 訓練與部署流程（自論文 fig4-7 改編）。

簡報簡化：保留「每步主迴圈（實線）vs 僅訓練期更新（虛線）」這個本圖的重點。
主迴圈線性一列（環境 → 狀態＋正規化輸入 → Q 網路 → arg max，動作回饋環境）；
訓練帶一列（分層路由 → 主要代理更新 → 鯰魚角色更新 → 週期性介入），梯度上行邊訓練 Q 網路。
非對稱折扣 β_M < β_CF 於本圖標出（ch4 §4.3 據此不另立專圖）。
視覺鍵：實線帶＝部署共用主線；虛線帶＝僅訓練期；navy＝主要代理；赭＝鯰魚；sand＝本論文貢獻。
內容紅線：只畫流程順序、無數值（β 為符號）、無效果宣稱。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-fig4-7-training-deployment-flow"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "Training and deployment procedure (slide)",
    2600, 1120,
    "Per-step procedure of the implemented MCRL framework. Order of operations only — "
    "no effectiveness claim, no result numbers.",
)

sec_loop = fig.sec("loop", "Per-step main loop", 40, 40, 100, 360)
sec_trn = fig.sec("train", "Training only", 40, 460, 100, 530, dash="7 5")

# ── 主迴圈（實線，線性一列，環境在最左＝上行邊清爽） ──────────────────────────
LOOP = [
    ("env", ["Environment", "≤ v_max beams lit"]),
    ("input", ["Augmented, normalized", "input s̃_u"]),
    ("value", ["Three Q-networks", "value b_u(a)"]),
    ("act", ["Per-user arg max", "ε-greedy in training"]),
]
fk.spread_row(fig, LOOP, 150, 90, 2260, stroke=fk.MAIN, contribs={"input"})
fig.n("value")["style"]["strokeWidth"] = 3.0

# ── 訓練帶（虛線）：四框對齊主迴圈四框 ──────────────────────────────────────────
# USER 2026-07-20 修正（同 ba44b9e3 的修正精神）：訓練期的更新**不是一條鏈**。
# 分層路由把轉移分進兩個池，主要代理與鯰魚角色**各自平行**更新；週期性介入是對
# 「主要代理」多做一次混合批次更新，不是接在鯰魚更新之後（ch4 §4.7）。
YT, YT2 = 620, 800
fig.add(fk.box("route", ["Stratified routing", "to replay buffers"], 0, YT, fk.CF,
               section="train", contrib=True))
fig.add(fk.box("umain", ["Main agent update", "β_M, loss with L_cap"], 0, YT, fk.MAIN,
               section="train"))
fig.add(fk.box("interv", ["Periodic intervention", "extra update"], 0, YT, fk.CF,
               section="train", contrib=True))
fig.add(fk.box("ucf", ["Catfish role update", "discount β_CF"], 0, YT2, fk.CF,
               section="train", contrib=True))
fig.center_on("route", "env")
fig.center_on("umain", "input")
fig.center_on("interv", "value")
fig.center_on("ucf", "env")

# β_M < β_CF：無框標籤（annotation 不吃下標），放在鯰魚更新框右側的空白處
beta = fig.add(fk.box("beta", ["β_M < β_CF"], 0, YT2, fk.INK,
                      style={"fill": "none", "stroke": "none", "crossSection": True}))
beta["x"] = fig.cx("umain") - beta["w"] // 2

# section 框住實際 box 範圍
xs = [n["x"] for n in fig.spec["nodes"]] + [n["x"] + n["w"] for n in fig.spec["nodes"]]
x0, x1 = min(xs) - 30, max(xs) + 30
for s in (sec_loop, sec_trn):
    s["x"], s["w"] = x0, x1 - x0

E = fig.edge
E("e-env-input", "env", "input", fromAnchor="right", toAnchor="left")
E("e-input-value", "input", "value", fromAnchor="right", toAnchor="left")
E("e-value-act", "value", "act", fromAnchor="right", toAnchor="left")
# 回線壓低到 section 標題之下（y=110）：85 時與較長的 "Per-step main loop" 標題觸發
# section-label-overlap 警告；110 仍在方框（y=150）之上。
E("e-act-env", "act", "env", fromAnchor="top", toAnchor="top", label="joint action",
  waypoints=[{"x": fig.cx("act"), "y": 110}, {"x": fig.cx("env"), "y": 110}])

# 跨帶邊的標籤要離開 section 邊框：labelDy 推進虛線帶內、boxes 之上的空白帶。
E("e-env-route", "env", "route", fromAnchor="bottom", toAnchor="top", label="transitions",
  style={"labelDx": 160, "labelDy": 72})
E("e-route-umain", "route", "umain", fromAnchor="right", toAnchor="left")
# 路由分岔到兩個更新（平行，不串接）；介入是給主要代理的額外一次更新。
E("e-route-ucf", "route", "ucf", fromAnchor="bottom", toAnchor="top")
E("e-interv-umain", "interv", "umain", fromAnchor="left", toAnchor="right")
# 梯度上行：umain 對齊 input，value 在其右一格 ⇒ 走跳線（上到帶間、右到 value、再上）
# 標籤靠左貼在自己的垂直上升段旁（labelDx 正值會把它推到「週期性介入」框正上方，讀起來
# 像在標 interv→umain 那條邊）。2026-07-20 修正。
E("e-umain-value", "umain", "value", fromAnchor="top", toAnchor="bottom", label="gradient step",
  style={"labelDx": -230, "labelDy": 46},
  waypoints=[{"x": fig.cx("umain"), "y": 545}, {"x": fig.cx("value"), "y": 545}])

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
