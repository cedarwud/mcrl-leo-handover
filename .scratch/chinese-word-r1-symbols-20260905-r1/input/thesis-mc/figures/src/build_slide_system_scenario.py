#!/usr/bin/env python3
"""SLIDE-GRADE 系統情境（自論文 fig-system-scenario 改編）。

簡報簡化：論文版畫兩顆衛星×兩波束×四使用者＋換手虛線（~15 框），簡報壓成一條情境管線
（衛星 → 容量閘 → 波束服務使用者 → 環境步 → 獎勵向量），5 框 3+2 蛇行。
「容量感知」＝框架名稱本體，故容量閘以粗框強調。換手成本 φ_1/φ_2 併入服務框（不用虛線邊，
免 R67 圖內短鍵）。全白＝既有系統情境（非本論文新增機制）。
內容紅線：只畫情境結構、無數值、無效果宣稱。角度幾何剖面另見系統模型圖（進講稿）。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-system-scenario"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "System scenario (slide)",
    2400, 620,
    "Scenario structure. Structure only — no effectiveness claim, no result numbers.",
)

Y1, Y2 = 40, 40 + 150 + 130   # 40 / 320
ROW1 = [
    ("sat", ["Satellites", "each with V beams"]),
    ("gate", ["Capacity gate", "at most v_max beams lit"]),
    ("serve", ["Beams serve users", "handover cost φ_1, φ_2"]),
]
fk.spread_row(fig, ROW1, Y1, 70, 2000, stroke=fk.MAIN)
fig.n("gate")["style"]["strokeWidth"] = 3.0   # 強調＝容量感知的本體

# 下列（蛇行，flow 右到左）：環境步 → 獎勵向量
env = fig.add(fk.box("env", ["Environment step", "applies the joint action"], 0, Y2, fk.MAIN))
fig.center_on("env", "serve")                          # 蛇行純垂直落點
reward = fig.add(fk.box("reward", ["Reward vector", "[r_1, r_2, r_3]"], 0, Y2, fk.MAIN))
reward["x"] = fig.n("env")["x"] - reward["w"] - 240

E = fig.edge
E("e-sat-gate", "sat", "gate", fromAnchor="right", toAnchor="left")
E("e-gate-serve", "gate", "serve", fromAnchor="right", toAnchor="left")
E("e-serve-env", "serve", "env", fromAnchor="bottom", toAnchor="top")   # 換列往下
E("e-env-reward", "env", "reward", fromAnchor="left", toAnchor="right")

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
