#!/usr/bin/env python3
"""MDP 結構 — spec builder（新作；圖號待 USER 指派）。

內容參考：thesis-mc/figures/from-archive/reference/f2-momdp-formulation.{svg,tex}
真相源：thesis-mc/ch4-method.md §4.1 式 (4.1)–(4.6)、§4.2 式 (4.7)–(4.9)、式 (4.13)
        ＋ notation-table §8、§9。

相對參考圖的改動（from-archive/README 判定）：
  * **補上情境正規化階段**——參考圖從狀態直接進策略，缺 §4.2 的 χ_u 與 s̃_u。
  * 純量化權重 `w` → `ω`（符號表 §9）。
  * 端點維持每位使用者各自取 arg max（參考圖本來就正確，不動）。
  * 去掉參考圖的 tag 橫幅與 warn 方塊（前者帶專案代號，後者的話進圖例）。

誠實邊界：只畫形式化結構，不畫任何效果宣稱；無數值、無式號（式號放圖例）。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-momdp-structure"

fig = fk.Fig(
    "Multi-objective Markov decision process",
    1440, 900,
    "Formalization used by the implemented framework per thesis-mc/ch4-method.md 4.1 and 4.2. "
    "Structure only — no effectiveness claim, no result numbers.",
)


# 第一列（左→右）：狀態如何變成網路輸入
ROW1 = [
    ("state", ["State s_u(t)", "connection, SINR, angle, load"]),
    ("context", ["Congestion context", "χ_u per candidate beam"]),
    ("norm", ["Context normalization", "input s̃_u"]),
]
# 貢獻框（USER-SET 填色軸 A）：MDP 本身是 MODQN 的形式化（既有）；本論文在輸入端加的是
# 壅塞情境 χ_u 與情境正規化 ⇒ 只填 context、norm。
CONTRIB = {"context", "norm"}
widths = [2 * round((max(fk.text_w(l) for l in lines) + 2 * fk.HPAD) / 2) for _, lines in ROW1]
gap = (1300 - sum(widths)) // (len(ROW1) - 1)
x = 70
for (nid, lines), w in zip(ROW1, widths):
    fig.add(fk.box(nid, lines, x, 110, fk.MAIN, contrib=(nid in CONTRIB)))
    x += w + gap

# 第二列（右→左）：蛇行折返，估值 → 選動作 → 環境
fig.add(fk.box("qnets", ["Three objective", "Q-networks Q_1, Q_2, Q_3"], 0, 300, fk.MAIN))
fig.add(fk.box("select", ["Scalarize ζ by Ω", "per-user arg max"], 0, 300, fk.MAIN))
fig.add(fk.box("env", ["Environment", "capacity limit v_max"], 0, 300, fk.MAIN))
fig.center_on("qnets", "norm")
fig.center_on("select", "context")
fig.center_on("env", "state")

# 第三列：可行動作集合（選動作的側輸入）與獎勵向量（環境的輸出）
fig.add(fk.box("reward", ["Reward vector", "[r_1, r_2, r_3]"], 0, 470, fk.MAIN))
# 可行動作集合在符號表／內文是花體 𝒜_u(t)，但花體 A（U+1D49C）不在字體 cmap（Chrome 會替換成
# 別的字型 ⇒ 與全圖不一致）；平體 A 又是「本表沒有的符號」。⇒ 方框只用文字「Feasible actions」，
# 精確符號 𝒜_u(t) 進圖說（同 Π/Δ 的處置）。
fig.add(fk.box("feasible", ["Feasible actions", "from mask m_u(t)"], 0, 470, fk.MAIN))
fig.center_on("reward", "env")
fig.center_on("feasible", "select")

E = fig.edge
E("e-state-context", "state", "context", fromAnchor="right", toAnchor="left")
E("e-context-norm", "context", "norm", fromAnchor="right", toAnchor="left")
E("e-norm-qnets", "norm", "qnets", fromAnchor="bottom", toAnchor="top")
E("e-qnets-select", "qnets", "select", fromAnchor="left", toAnchor="right")
E("e-select-env", "select", "env", fromAnchor="left", toAnchor="right", label="action a_u(t)")
E("e-feasible-select", "feasible", "select", fromAnchor="top", toAnchor="bottom")
E("e-env-reward", "env", "reward", fromAnchor="bottom", toAnchor="top")
E("e-env-state", "env", "state", fromAnchor="top", toAnchor="bottom",
  label="transition P, next state", style={"labelDx": 130})
# codex 審查（已查證）：MDP 圖原缺 tuple 的折扣 β 與轉移 P，看起來像縮小版 4-7。P 已由環境轉移
# 邊明示；折扣 β 以無框標籤補上（β 無下標 ⇒ annotation 安全）。完整 tuple ⟨S,A,R,P,β⟩ 見圖說。
fig.note("beta_note", ["Q-networks give the expected β-discounted return"],
         fig.n("reward")["x"], 620)

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。tuple 說明與式號進論文圖說。
fig.crop()   # 四邊收到貼合內容（USER 2026-07-19：單框圖去外框＋去標題，畫布往內收）

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
