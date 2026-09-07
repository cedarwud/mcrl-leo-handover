#!/usr/bin/env python3
"""系統情境幾何 — spec builder（新作；圖號待 USER 指派）。

內容參考：thesis-mc/figures/from-archive/reference/f1-system-model.{svg,tex}
真相源：thesis-mc/mc-modqn-base.md §3.1 式 (3.1)–(3.5)、式 (3.4a)、式 (3.23)、式 (3.26)
        ＋ notation-table §1、§2、§6。

USER 裁決 2026-07-19：本圖與既有圖 3-1 並存、分工不同——圖 3-1 是角度幾何剖面（θ/α/d、
波束錐），本圖是**系統情境方塊圖**（容量閘、換手成本、獎勵向量）。因此不用衛星／手機圖示，
維持與其餘概念圖同一種方塊語言。

相對參考圖的改動（from-archive/README 判定）：
  * **補上容量閘 v_max**（式 (3.4a)）——框架名稱裡的「容量感知」就是指這個，參考圖沒有。
  * **補上換手成本 φ_1 / φ_2**（式 (3.23)：換波束成本／換衛星成本），畫成兩條虛線。
  * 波束索引 `b` → `v`。
  * 去掉參考圖的 tag 橫幅（帶專案代號）。

誠實邊界：只畫情境結構，不畫任何效果宣稱；無數值。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-system-scenario"

fig = fk.Fig(
    "System scenario",
    1440, 1100,
    "Scenario structure per thesis-mc/mc-modqn-base.md 3.1. "
    "Structure only — no effectiveness claim, no result numbers.",
)


# 兩顆衛星各帶兩個波束；左右兩組的中心線
GROUP_CX = {"a": 380, "b": 1060}
BEAM_CX = {"a": (220, 540), "b": (900, 1220)}
Y_SAT, Y_GATE, Y_BEAM, Y_USER, Y_ENV = 110, 260, 410, 560, 730
Y_FAN = 390     # 容量閘扇出到兩個波束的轉折
Y_TRUNK = 690   # 四位使用者匯入環境的匯流排

SAT_LAB = {"a": ["Satellite s", "V beams available"], "b": ["Satellite s′", "V beams available"]}
BEAM_LAB = {"a": ("Beam (s,1)", "Beam (s,2)"), "b": ("Beam (s′,1)", "Beam (s′,2)")}
USER_LAB = {"a": ("User u_1", "User u_2"), "b": ("User u_3", "User u_4")}


def centered(nid, lines, cx, y, stroke, **kw):
    n = fk.box(nid, lines, 0, y, stroke, **kw)
    n["x"] = int(cx - n["w"] // 2)
    return fig.add(n)


for g in ("a", "b"):
    centered(f"sat_{g}", SAT_LAB[g], GROUP_CX[g], Y_SAT, fk.MAIN)
    # 容量閘：框架名稱裡的「容量感知」指的就是這一關，畫成結構上看得見的一道閘
    centered(f"gate_{g}", ["Capacity gate", "at most v_max beams lit"], GROUP_CX[g], Y_GATE,
             fk.INK)
    for i in (0, 1):
        centered(f"beam_{g}{i}", [BEAM_LAB[g][i]], BEAM_CX[g][i], Y_BEAM, fk.MAIN)
        centered(f"user_{g}{i}", [USER_LAB[g][i]], BEAM_CX[g][i], Y_USER, fk.MAIN)

# 不要在這裡再寫一次「套用容量上限」：容量閘已經是圖中唯一陳述該限制的地方，
# 寫兩次會讀成限制被套用了兩次。
centered("env", ["Environment step", "applies the joint action"], 548, Y_ENV, fk.MAIN)
centered("reward", ["Reward vector", "[r_1, r_2, r_3]"], 938, Y_ENV, fk.MAIN)

E = fig.edge
for g in ("a", "b"):
    E(f"e-sat-gate-{g}", f"sat_{g}", f"gate_{g}", fromAnchor="bottom", toAnchor="top")
    # 共用主幹的扇出 ⇒ 不掛標籤
    for i in (0, 1):
        E(f"e-gate-beam-{g}{i}", f"gate_{g}", f"beam_{g}{i}",
          fromAnchor="bottom", toAnchor="top",
          waypoints=[{"x": GROUP_CX[g], "y": Y_FAN}, {"x": BEAM_CX[g][i], "y": Y_FAN}])
        E(f"e-beam-user-{g}{i}", f"beam_{g}{i}", f"user_{g}{i}",
          fromAnchor="bottom", toAnchor="top")

# 換手成本：同衛星換波束＝φ_1，跨衛星換衛星＝φ_2。虛線＝可能發生的換手，不是固定連線。
E("e-ho-beam", "beam_a0", "beam_a1", fromAnchor="right", toAnchor="left",
  # 標籤要抬離自己的虛線，否則線會從字中間穿過去
  label="φ_1", style={"dash": "6 4", "labelDy": -32})
E("e-ho-sat", "beam_a1", "beam_b0", fromAnchor="right", toAnchor="left",
  label="φ_2", style={"dash": "6 4", "labelDy": -32})

# 四位使用者匯入環境：匯流排式扇入（fixture-laws §4）⇒ 不掛標籤
for g in ("a", "b"):
    for i in (0, 1):
        E(f"e-user-env-{g}{i}", f"user_{g}{i}", "env", fromAnchor="bottom", toAnchor="top",
          waypoints=[{"x": BEAM_CX[g][i], "y": Y_TRUNK}, {"x": fig.cx("env"), "y": Y_TRUNK}])

E("e-env-reward", "env", "reward", fromAnchor="right", toAnchor="left")

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。容量閘與換手成本的說明進論文圖說。
# 本圖無貢獻填色：§3.1 是既有系統情境（容量閘是基準也面對的環境限制，屬「沿用」）；
# 容量閘僅以赭色框線作為圖內強調，其語意在圖說宣告。
# 例外（rule 9 允許的「一行短鍵」）：虛線邊是語意承載的（可能的換手 vs 固定連線），
# R67-dashed-legend-required 硬性要求圖內宣告 ⇒ 保留一行短鍵，不是散文區塊。
fig.note("dashkey", ["Dashed = a handover a user may make, not a fixed link"], 60, 872)
fig.crop()   # 四邊收到貼合內容（USER 2026-07-19：單框圖去外框＋去標題，畫布往內收）

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
