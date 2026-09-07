#!/usr/bin/env python3
"""週期性介入 — spec builder（2026-07-20 rev-3：退火移除後的「按比例注入」圖）。

USER 2026-07-20：「不是應該會有 main agent 跟 catfish agent 然後用比例去注入之類的嗎?怎麼都沒畫
出來，也沒看到比例?」——查證後成立，而且是真缺口：
  · 圖 4-2 有兩個代理、兩個經驗池、介入打回主要 Q 網路，**但沒有比例**；
  · 本圖（前一版）有比例 ρ_I(e)、n_CF，**但沒有兩個經驗池**，終點只有一個孤立的「額外更新」。
  ⇒ 「從鯰魚池按 ρ_I 抽 n_CF 筆、與主池的 B−n_CF 筆混成一批、打進主要代理」這件事，兩張圖都沒畫。
本版把它畫出來：兩個經驗池各自以**帶樣本數的邊**匯入混合批次，鯰魚佔比 ρ_I 決定其組成。

★★ 2026-07-20 USER 指示：**介入退火自框架移除**（機制仍在測試中），本圖同步刪除退火。
移除的內容與理由：
  * `anneal` 框（δ(e) 三段排程 1 → δ_f over [E_0,E_1]）——機制不在框架內了。
  * `rho` 由 ρ_I(e)=ρ_I·δ(e) 改回**固定值 ρ_I**（ch4 §4.3 現行式子即 n_CF=⌈ρ_I·B⌋，無 δ）。
  * `xpool` 框（中段經驗跨池機率＝δ(e)）——那是退火的第二條通道；沒有退火後中段一律跨送，
    此事屬能效分層（§4.3 策略一），本圖不再重複標示。
已核對：ch4 全章已無「退火／anneal」，§4.4 現為 Reward Shaping，消融表亦無該臂。

真相源：thesis-mc/ch4-method.md §4.3（週期性介入，固定比例混合批次）。
程式對照：route_b_factorial/faithful_catfish_trainer.py（介入時點與混合批次組成）。

填色（USER-SET 軸 A）：佔比、混合批次、間隔、額外更新事件＝本論文加的。
兩個經驗池本身是標準元件 ⇒ 主要經驗池留白；鯰魚經驗池是本論文新增 ⇒ 填色（與圖 4-2 一致）。

誠實邊界：只畫機制，不畫效果宣稱；無數值（B/ρ_I/T 皆以符號出現）。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-intervention-annealing"

fig = fk.Fig(
    "Periodic intervention: ratio-based injection into the main agent",
    1440, 620,
    "How the periodic intervention composes its mixed batch in the implemented MCRL framework, "
    "per thesis-mc/ch4-method.md 4.3. The catfish share is a fixed ratio; intervention annealing "
    "was removed from the framework on 2026-07-20. Mechanism only — no effectiveness claim, "
    "no result numbers.",
)


def centered(nid, lines, cx, y, stroke, **kw):
    n = fk.box(nid, lines, 0, y, stroke, **kw)
    n["x"] = int(cx - n["w"] // 2)
    return fig.add(n)


# 鯰魚佔比：決定混合批次裡的鯰魚樣本數。**固定值**——介入退火已自框架移除（見檔頭）。
centered("rho", ["Catfish share", "ρ_I"], 580, 50, fk.CF, contrib=True)
fig.n("rho")["style"]["strokeWidth"] = 2.5
# 兩個經驗池：各自貢獻多少筆，就是「比例注入」本身
centered("cfbuf", ["Catfish", "replay buffer"], 580, 220, fk.CF, contrib=True)
centered("mainbuf", ["Main", "replay buffer"], 580, 390, fk.MAIN)
centered("mix", ["Mixed batch", "size B"], 950, 220, fk.CF, contrib=True)
fig.n("mix")["style"]["strokeWidth"] = 2.5
centered("upd", ["Main agent", "extra update"], 1270, 220, fk.MAIN, contrib=True)
centered("interval", ["Interval [T_lo, T_hi]", "random per intervention"], 950, 470, fk.CF,
         contrib=True)

E = fig.edge
# 佔比決定混合批次的組成
E("e-rho-mix", "rho", "mix", fromAnchor="right", toAnchor="top",
  waypoints=[{"x": fig.cx("mix"), "y": fig.cy("rho")}])
# ★ 比例注入：兩個池各自帶樣本數匯入同一批
E("e-cfbuf-mix", "cfbuf", "mix", fromAnchor="right", toAnchor="left", label="n_CF")
E("e-mainbuf-mix", "mainbuf", "mix", fromAnchor="right", toAnchor="bottom",
  label="B − n_CF", style={"labelDx": -70},
  waypoints=[{"x": fig.cx("mix"), "y": fig.cy("mainbuf")}])
E("e-mix-upd", "mix", "upd", fromAnchor="right", toAnchor="left")
E("e-interval-upd", "interval", "upd", fromAnchor="right", toAnchor="bottom",
  waypoints=[{"x": fig.cx("upd"), "y": fig.cy("interval")}])

# academic.md rule 9（USER-SET）：n_CF 的四捨五入取整、混合批次的抽取方式
# 等細節進論文圖說。
fig.crop()

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
