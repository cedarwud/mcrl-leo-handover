#!/usr/bin/env python3
"""SLIDE-GRADE 壅塞情境狀態擴充（自論文 fig-congestion-context 改編）。

同結構（三特徵匯入壅塞情境，再與基準狀態接成擴充狀態），字大留白收緊。
視覺鍵：sand 填色＝本論文貢獻（基準狀態沿用＝白）；navy＝部署路徑（此編碼部署也用）。
內容紅線：只畫編碼、無數值、無效果宣稱。精確符號 o_{s,v}/c_{s,v}/rank_{u,s,v} 進講稿。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-congestion-context"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "Congestion-context state augmentation (slide)",
    2500, 760,
    "Construction of the congestion context. Encoding only — no effectiveness claim, "
    "no result numbers.",
)

# 三特徵（col1，堆疊）
GAPV = 70
YF = [40, 40 + 150 + GAPV, 40 + 2 * (150 + GAPV)]   # 40 / 260 / 480
occ = fig.add(fk.box("occ", ["Prior occupancy", "last-step users on it"], 70, YF[0], fk.MAIN, contrib=True))
cont = fig.add(fk.box("cont", ["Contender count", "users choosing it now"], 70, YF[1], fk.MAIN, contrib=True))
rank = fig.add(fk.box("rank", ["Signal rank", "this user's SINR order"], 70, YF[2], fk.MAIN, contrib=True))
featright = max(fig.right("occ"), fig.right("cont"), fig.right("rank"))

# 壅塞情境（col2，對齊中列 cont）
chi = fig.add(fk.box("chi", ["Congestion context χ_u", "three per-beam values"],
                     featright + 260, YF[1], fk.MAIN, contrib=True))
fig.n("chi")["style"]["strokeWidth"] = 3.0   # 強調＝本圖主題

# col3：基準狀態（上，沿用＝白）＋ 擴充狀態（中，與 chi 同列）
aug = fig.add(fk.box("aug", ["Augmented state", "[s_u, χ_u]"], fig.right("chi") + 210, YF[1],
                     fk.MAIN, contrib=True))
base = fig.add(fk.box("base", ["Base state s_u"], 0, YF[0], fk.MAIN))
fig.center_on("base", "aug")

X_CONV = featright + 120   # 三特徵匯入壅塞情境的垂直走廊

E = fig.edge
E("e-occ-chi", "occ", "chi", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_CONV, "y": fig.cy("occ")}, {"x": X_CONV, "y": fig.cy("chi")}])
E("e-cont-chi", "cont", "chi", fromAnchor="right", toAnchor="left")
E("e-rank-chi", "rank", "chi", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_CONV, "y": fig.cy("rank")}, {"x": X_CONV, "y": fig.cy("chi")}])
E("e-chi-aug", "chi", "aug", fromAnchor="right", toAnchor="left")
E("e-base-aug", "base", "aug", fromAnchor="bottom", toAnchor="top")

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
