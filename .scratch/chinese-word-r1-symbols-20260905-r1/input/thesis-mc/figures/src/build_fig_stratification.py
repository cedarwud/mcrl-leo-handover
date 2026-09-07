#!/usr/bin/env python3
"""能效分層 — spec builder（自舊圖 4-6 上半拆出的獨立圖；圖號待 USER 指派）。

USER 裁決 2026-07-19（第二輪）：舊圖 4-6 把能效分層與週期性介入擠在一張；本輪拆成兩張獨立圖，
讓兩個真正在運作的機制各有版面（見 HANDOFF §(b)）。本檔＝能效分層那一張。

真相源：thesis-mc/ch4-method.md §4.3「策略一：能效分層」式 (4.10) ＋ 圖說。
程式對照：catfish_faithful_familyb/stratification.py:66-122（三路分流、滾動視窗分位數）。

填色（USER-SET 軸 A）：鯰魚角色轉移、分層規則、鯰魚經驗池＝本論文加的（填 CONTRIB）；
主要經驗池是標準元件（留白）、捨棄段以灰色框線去強調。

誠實邊界：只畫機制，不畫「分層 ⇒ 學得比較好」的因果箭頭；無數值、無式號（式號進圖說）。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-stratification"

fig = fk.Fig(
    "Energy-efficiency stratification",
    1440, 520,
    "Three-way routing of catfish transitions in the implemented MCRL framework per "
    "thesis-mc/ch4-method.md 4.3, equation (4.10). Mechanism only — no effectiveness claim, "
    "no result numbers.",
)

# 整張圖都是僅訓練期 ⇒ 虛線框（虛線語意＝僅訓練期，在圖說宣告；R67 只管虛線邊，不管虛線框）。

fig.add(fk.box("trans", ["Catfish role transition", "energy efficiency η"],
               70, 245, fk.CF, contrib=True))
fig.add(fk.box("rule", ["Stratify by quantiles", "q_lo, q_hi over window W"],
               470, 245, fk.CF, contrib=True))
# 每個目的地自己說收的是哪一段 ⇒ 扇出的三條邊不掛標籤（共用主幹，掛了也會被規則 17b 擋）。
fig.add(fk.box("cf_pool", ["Catfish replay buffer", "highest band"],
               880, 110, fk.INK, contrib=True))
fig.add(fk.box("main_pool", ["Main replay buffer", "middle band"],
               880, 245, fk.INK))
fig.add(fk.box("discard", ["Discard", "lowest band"],
               880, 380, fk.MUTE))
fig.n("rule")["style"]["strokeWidth"] = 2.5   # 強調＝本圖主題

X_FAN = 840      # 分流扇出的垂直走廊

E = fig.edge
E("e-trans-rule", "trans", "rule", fromAnchor="right", toAnchor="left")
E("e-rule-main", "rule", "main_pool", fromAnchor="right", toAnchor="left")
E("e-rule-cf", "rule", "cf_pool", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_FAN, "y": fig.cy("rule")}, {"x": X_FAN, "y": fig.cy("cf_pool")}])
E("e-rule-discard", "rule", "discard", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_FAN, "y": fig.cy("rule")}, {"x": X_FAN, "y": fig.cy("discard")}])

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。分位數規則與式號進論文圖說。
fig.crop()   # 四邊收到貼合內容（USER 2026-07-19：單框圖去外框＋去標題，畫布往內收）

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
