#!/usr/bin/env python3
"""SLIDE-GRADE 競爭獎勵機制 ACRM（自論文 fig-competitive-reward 改編）。

簡報簡化：同狀態配對比較的兩支評估（鯰魚動作 vs 主要代理貪婪動作）匯入「整形後的競爭獎勵」
（競爭項直接寫進整形公式），只更新鯰魚；「原始獎勵送主要經驗池」的邊界併入更新框第二行。
視覺鍵：赭＝鯰魚／僅訓練期；navy＝主要代理；sand 填色＝本論文貢獻。
內容紅線：只畫機制、無數值（η_w 為權重符號）、無效果宣稱。同步環境副本的舞台＝進講稿。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-competitive-reward"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "Competitive reward mechanism (slide)",
    2400, 700,
    "Paired same-state action comparison for the competitive reward on the first objective. "
    "Mechanism only — no effectiveness claim, no result numbers.",
)

# 左：兩支評估（上下疊，配對中心對到主鏈中心）
Y_UP, Y_LO = 40, 40 + 150 + 150   # 40 / 340（配對中心 = 265）
cf = fig.add(fk.box("cf_act", ["Catfish action", "reward r_1^CF"], 70, Y_UP, fk.CF, contrib=True))
m = fig.add(fk.box("m_act", ["Main greedy action", "reward r_1^M"], 70, Y_LO, fk.MAIN))
evalright = max(fig.right("cf_act"), fig.right("m_act"))
# 走廊與框距收緊（2026-07-20）：投影 pt = 42×72×12.80/W_px ⇒ W_px 每寬 100 就掉約 0.8 pt。
# 這裡把三段間距 130/130/150 收成 110/110/120，不動任何標籤語意。
X_MERGE = evalright + 110                       # 兩支評估匯入的垂直走廊
YROW = (fig.cy("cf_act") + fig.cy("m_act")) // 2 - 75   # 主鏈中心列

# 整形後的競爭獎勵（競爭項寫進公式）→ 只更新鯰魚
shape = fig.add(fk.box("shape", ["Shaped catfish reward", "r_1^CF + η_w (r_1^CF − r_1^M)"],
                       X_MERGE + 110, YROW, fk.CF, contrib=True))
fig.n("shape")["style"]["strokeWidth"] = 3.0   # 強調＝整形後的競爭獎勵
# "main buffer" → "main pool"：與 C5／C6 投影片同一用詞（經驗池），且省下約 40px。
fig.add(fk.box("cf_upd", ["Updates catfish only", "raw r_1^CF to main pool"],
               fig.right("shape") + 120, YROW, fk.CF, contrib=True))

E = fig.edge
E("e-cf-shape", "cf_act", "shape", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_MERGE, "y": fig.cy("cf_act")}, {"x": X_MERGE, "y": fig.cy("shape")}])
E("e-m-shape", "m_act", "shape", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_MERGE, "y": fig.cy("m_act")}, {"x": X_MERGE, "y": fig.cy("shape")}])
E("e-shape-upd", "shape", "cf_upd", fromAnchor="right", toAnchor="left")

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
