#!/usr/bin/env python3
"""SLIDE-GRADE 週期性介入（自論文 fig-intervention-annealing 改編）。

★★ 2026-07-20 USER 指示：**介入退火自框架移除**（機制仍在測試中）⇒ 本圖同步重寫。
舊版整張圖的主題就是退火（退火排程框 ＋ 它分叉出的兩條通道：鯰魚佔比 ρ_I(e)=ρ_I·δ(e)、
中段跨池機率 δ(e)）。退火拿掉後那三個框全部失去依據，只剩兩格，太薄。
⇒ 改為鏡射修正後的論文版：主題回到「**按比例注入**」——鯰魚池出 n_CF 筆、主池出 B−n_CF 筆，
   混成一批打進主要代理，佔比 ρ_I 為固定值。中段跨池屬能效分層（§4.3 策略一），不在本圖重複。
已核對：ch4 全章已無「退火／anneal」，§4.4 現為 Reward Shaping，消融表亦無該臂。

⚠ 檔名仍為 `slide-intervention-annealing`（同步基準與 deliverable 都指著它）——改名要連
   viz.json／SVG／PNG／SLIDE-FIGURE-SYNC 一起動，未經指示不自行更名。

視覺鍵：赭＝訓練期機制；navy＝主要代理；sand 填色＝本論文新增／延伸。
內容紅線：只畫機制、無數值（B/ρ_I/T_lo/T_hi 皆符號）、無效果宣稱。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-intervention-annealing"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "Periodic intervention: ratio-based injection (slide)",
    2500, 800,
    "How the periodic intervention composes its mixed batch in the implemented MCRL framework, "
    "per thesis-mc/ch4-method.md 4.3. The catfish share is a fixed ratio; intervention annealing "
    "was removed from the framework on 2026-07-20. Mechanism only — no effectiveness claim, "
    "no result numbers.",
)

GAPV = 70
Y_TOP, Y_MID, Y_BOT = 40, 40 + 150 + GAPV, 40 + 2 * (150 + GAPV)   # 40 / 260 / 480

# 左欄：佔比 ＋ 兩個經驗池（各自貢獻多少筆，就是「比例注入」本身）
share = fig.add(fk.box("share", ["Catfish share", "ρ_I"], 70, Y_TOP, fk.CF, contrib=True))
cfbuf = fig.add(fk.box("cfbuf", ["Catfish", "replay buffer"], 70, Y_MID, fk.CF, contrib=True))
mainbuf = fig.add(fk.box("mainbuf", ["Main", "replay buffer"], 70, Y_BOT, fk.MAIN))

XB = max(fig.right("share"), fig.right("cfbuf"), fig.right("mainbuf")) + 260
mix = fig.add(fk.box("mix", ["Mixed batch", "size B"], XB, Y_MID, fk.CF, contrib=True))
fig.n("mix")["style"]["strokeWidth"] = 3.0   # 強調＝本圖主題

upd = fig.add(fk.box("upd", ["Main-agent extra update", "interval [T_lo, T_hi]"],
                     fig.right("mix") + 200, Y_MID, fk.MAIN, contrib=True))

E = fig.edge
# 佔比決定混合批次的組成（自上方落下）
E("e-share-mix", "share", "mix", fromAnchor="right", toAnchor="top",
  waypoints=[{"x": fig.cx("mix"), "y": fig.cy("share")}])
# ★ 比例注入：兩個池各自帶樣本數匯入同一批
E("e-cfbuf-mix", "cfbuf", "mix", fromAnchor="right", toAnchor="left", label="n_CF")
E("e-mainbuf-mix", "mainbuf", "mix", fromAnchor="right", toAnchor="bottom",
  label="B − n_CF", style={"labelDx": -90},
  waypoints=[{"x": fig.cx("mix"), "y": fig.cy("mainbuf")}])
E("e-mix-upd", "mix", "upd", fromAnchor="right", toAnchor="left")

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
