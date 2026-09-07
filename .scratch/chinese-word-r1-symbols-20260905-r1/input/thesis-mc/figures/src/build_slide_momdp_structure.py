#!/usr/bin/env python3
"""SLIDE-GRADE 多目標 MDP 結構（自論文 fig-momdp-structure 改編）。

簡報簡化：論文版八框（含情境／正規化分兩格、獎勵向量獨立框），簡報壓成一個矩形迴圈：
狀態 →（壅塞情境＋情境正規化，合一格）→ Q 網路 → 純量化 arg max → 環境 → 回到狀態。
可行動作集合＝選動作的側輸入；獎勵向量＝環境回線的標籤。
視覺鍵：sand 填色＝本論文在輸入端新增（壅塞情境＋情境正規化）；MDP 骨架沿用＝白。
內容紅線：只畫形式化結構、無數值、無效果宣稱。可行動作集合 𝒜_u 不在字體 cmap ⇒ 用文字。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-momdp-structure"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "Multi-objective Markov decision process (slide)",
    2200, 900,
    "Formalization used by the framework. Structure only — no effectiveness claim, "
    "no result numbers.",
)

Y1 = 40
ROW1 = [
    ("state", ["State s_u", "connection, SINR, angle, load"]),
    ("context", ["Congestion context", "normalization → input s̃_u"]),
    ("qnets", ["Three objective", "Q-networks Q_1, Q_2, Q_3"]),
]
fk.spread_row(fig, ROW1, Y1, 70, 1900, stroke=fk.MAIN, contribs={"context"})

Y2 = Y1 + 150 + 200   # 390
select = fig.add(fk.box("select", ["Scalarize by Ω", "per-user arg max"], 0, Y2, fk.MAIN))
fig.center_on("select", "qnets")
env = fig.add(fk.box("env", ["Environment", "capacity limit v_max"], 0, Y2, fk.MAIN))
fig.center_on("env", "state")

Y3 = Y2 + 150 + 100   # 640
feasible = fig.add(fk.box("feasible", ["Feasible actions", "from mask m_u(t)"], 0, Y3, fk.MAIN))
fig.center_on("feasible", "select")

E = fig.edge
E("e-state-context", "state", "context", fromAnchor="right", toAnchor="left")
E("e-context-qnets", "context", "qnets", fromAnchor="right", toAnchor="left")
E("e-qnets-select", "qnets", "select", fromAnchor="bottom", toAnchor="top")
E("e-select-env", "select", "env", fromAnchor="left", toAnchor="right", label="action a_u(t)")
E("e-env-state", "env", "state", fromAnchor="top", toAnchor="bottom",
  label="reward vector, next state", style={"labelDx": 190})
E("e-feasible-select", "feasible", "select", fromAnchor="top", toAnchor="bottom")

fig.note("beta_note", ["Q-networks give the expected β-discounted return"],
         fig.n("feasible")["x"], Y3 + 210)

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
