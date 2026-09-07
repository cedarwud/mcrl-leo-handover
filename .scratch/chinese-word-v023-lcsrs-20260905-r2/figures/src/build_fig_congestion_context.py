#!/usr/bin/env python3
"""圖 4-4 壅塞情境狀態擴充 — spec builder（重繪，取代過期的 fig7.png）。

USER 2026-07-19 抓到：舊 fig7.png 是 cell/coordinate 時期的圖（用「cell c」+ o_c/n_c/q_u^c，
把 s̃_u 標成 [s_u,χ_u]，缺式 (4.9) 的跨使用者 z-score）。本檔依現行機制重繪、風格對齊本輪 12 張。

真相源：thesis-mc/ch4-method.md §4.2 式 (4.7)（χ_u 三個值）、式 (4.8)（擴充狀態 [s_u,χ_u]）、
        式 (4.9)（情境正規化在此之後套用）＋ notation-table §10。
程式對照：route_b_factorial（壅塞情境三特徵、動作前資訊）。

現行符號（相對舊 fig7 的修正）：beam (s,v) 不是 cell c；三特徵＝上一步佔用 o_{s,v}(t-1)、
本步競爭者數 c_{s,v}(t)、訊號排名 rank_{u,s,v}(t)；擴充狀態是 [s_u,χ_u]（舊圖誤標 s̃_u）；
式 (4.9) 的跨使用者 z-score 是「之後」的另一步（見情境正規化那張圖）。

⚠ 方框省略多重下標（rank_{u,s,v} 這種會斷成 rank + 下標 u + 正常大小的 ,s,v）——改用敘述，
精確符號進圖說（同 power-EE 鏈的作法）。χ_u / s_u / s̃_u 的單 token 下標可保留。

填色（USER-SET 軸 A）：三特徵＋壅塞情境＋擴充狀態＝本論文新增（填 CONTRIB）；基準狀態 s_u
與正規化後的網路輸入介面沿用（留白）。實線框：此編碼在部署與訓練都用。

誠實邊界：只畫編碼，不畫效果宣稱；無數值。「只用動作前資訊、不洩漏他人當步選擇」進圖說。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-congestion-context"

fig = fk.Fig(
    "Congestion-context state augmentation",
    1440, 640,
    "Construction of the congestion context in the implemented MCRL framework per "
    "thesis-mc/ch4-method.md 4.2, equations (4.7) to (4.9). Encoding only — no effectiveness "
    "claim, no result numbers.",
)

# 實線框：此編碼在部署與訓練兩端都用（非僅訓練期）。

# 三特徵（動作前資訊；符號進圖說）。y 取 100/235/370（間隔 135）⇒ section 上下邊距約 60/64 對稱，
# 最下面那個 rank 框不會貼著 section 底看起來像被切。
fig.add(fk.box("occ", ["Prior occupancy", "last-step users on the beam"], 90, 100, fk.MAIN, contrib=True))
fig.add(fk.box("cont", ["Contender count", "users choosing it this step"], 90, 235, fk.MAIN, contrib=True))
fig.add(fk.box("rank", ["Signal rank", "this user among contenders"], 90, 370, fk.MAIN, contrib=True))
# 壅塞情境（三特徵匯入；對齊中間那列 cont）
fig.add(fk.box("chi", ["Congestion context χ_u", "three per-beam values"], 560, 235,
               fk.MAIN, contrib=True))
fig.n("chi")["style"]["strokeWidth"] = 2.5   # 強調＝本圖主題
# 基準狀態（沿用）＋ 擴充。圖到擴充狀態（式 4.8）為止；式 (4.9) 的情境正規化是下一張圖（§3.4），進圖說。
fig.add(fk.box("base", ["Base state s_u"], 0, 100, fk.MAIN))
fig.add(fk.box("aug", ["Augmented state", "[s_u, χ_u]"], 1000, 235, fk.MAIN,
               contrib=True))
fig.center_on("base", "aug")

X_CONV = 530     # 三特徵匯入壅塞情境的垂直走廊（清過最寬特徵框右緣）

E = fig.edge
# 三特徵匯入 chi（共用 chi 左緣錨點＝合併；cont 與 chi 同列直進，occ/rank 走走廊）
E("e-occ-chi", "occ", "chi", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_CONV, "y": fig.cy("occ")}, {"x": X_CONV, "y": fig.cy("chi")}])
E("e-cont-chi", "cont", "chi", fromAnchor="right", toAnchor="left")
E("e-rank-chi", "rank", "chi", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_CONV, "y": fig.cy("rank")}, {"x": X_CONV, "y": fig.cy("chi")}])
# chi → aug（右），base → aug（下）
E("e-chi-aug", "chi", "aug", fromAnchor="right", toAnchor="left")
E("e-base-aug", "base", "aug", fromAnchor="bottom", toAnchor="top")

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。精確符號（o_{s,v}/c_{s,v}/rank_{u,s,v}）、
# 「動作前資訊不洩漏他人當步選擇」、式 (4.9) 之後套用等，全進論文圖說。
fig.crop()   # 四邊收到貼合內容（USER 2026-07-19：單框圖去外框＋去標題，畫布往內收）

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
