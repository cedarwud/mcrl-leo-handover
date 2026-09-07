#!/usr/bin/env python3
"""圖 4-2 MCRL 整體架構 — spec builder（英文重作版）。

真相源：thesis-mc/ch4-method.md §4.1（圖 4-2 圖說）＋ thesis-mc/notation-table.md。
程式對照：route_b_factorial/faithful_catfish_trainer.py（雙 rollout、能效分層、週期性介入）、
          shared_q_isolation/catfish_pack.py（競爭獎勵機制）、
          shared_q_isolation/capacity_penalty.py（容量懲罰）。

版型：兩條全寬帶狀 section（fixture-laws §9 的 label-safe 版型）。
上帶實線＝部署路徑，下帶虛線＝僅訓練期。

保留自前一版眼檢的設計決定：兩個經驗池必須是**兩個獨立方框**。合併成單一上下分隔框時，
箭頭只能接到整框上／下緣，會讓「主線轉移」看似流進鯰魚經驗池、「自身更新」看似來自
主要經驗池——兩者都與實作相反。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig4-2-mccrl-architecture"

fig = fk.Fig(
    "Fig 4-2 MCRL overall architecture",
    1440, 1010,
    "Architecture of the implemented MCRL framework per thesis-mc/ch4-method.md 4.1 and "
    "thesis-mc/notation-table.md. Structure only — no effectiveness claim, no result numbers.",
)

# ── 上帶：部署路徑（與基準相同） ──────────────────────────────────────────────
# section 標題只放「名稱」，說明進圖例：長標題會把帶 B 的標題帶橫向拉到 x≈430，
# 任何從上帶落下的垂直段都會撞上它（規則 9 section-label-overlap）。
fig.sec("deploy", "Deployment path", 40, 40, 1360, 260)
fig.sec("train", "Catfish mechanisms, training only", 40, 345, 1360, 545, dash="7 5")

DEPLOY = [
    ("env", ["Environment", "capacity limit v_max"]),
    ("input", ["Congestion context χ_u", "normalized input s̃_u"]),
    ("qnets", ["Three objective", "Q-networks Q_1, Q_2, Q_3"]),
    ("select", ["Scalarize by Ω", "per-user arg max"]),
]
# 把整列置中於 [60, 1380]，間隔由剩餘空間平均分配（同列同行數 ⇒ 中心線自動對齊）
widths = [2 * round((max(fk.text_w(l) for l in lines) + 2 * fk.HPAD) / 2)
          for _, lines in DEPLOY]
gap = (1320 - sum(widths)) // (len(DEPLOY) - 1)
# 貢獻框（USER-SET 填色軸 A）：情境正規化的輸入是本論文加的；env／qnets／select 沿用基準。
CONTRIB_DEPLOY = {"input"}
x = 60
for (nid, lines), w in zip(DEPLOY, widths):
    n = fig.add(fk.box(nid, lines, x, 130, fk.MAIN, section="deploy",
                       contrib=(nid in CONTRIB_DEPLOY)))
    x += w + gap
fig.n("qnets")["style"]["strokeWidth"] = 2.5   # 強調＝部署時唯一運作的學習元件

# ── 下帶：僅訓練期 ───────────────────────────────────────────────────────────
# 貢獻框：鯰魚角色／鯰魚經驗池／週期性介入／競爭獎勵／容量懲罰皆為本論文加的（填 CONTRIB）；
# 主要經驗池是標準元件（留白）。
fig.add(fk.box("catfish", ["Catfish Q-nets Q_j^CF", "independent rollout; same model"],
               60, 470, fk.CF, section="train", contrib=True))
fig.add(fk.box("main_pool", ["Main", "replay buffer"], 600, 400, fk.INK, section="train"))
fig.add(fk.box("cf_pool", ["Catfish", "replay buffer"], 600, 560, fk.INK, section="train",
               contrib=True))
# 佔比是固定的 ρ_I：介入退火已於 2026-07-20 依 USER 指示自框架移除（原為 ρ_I(e)=ρ_I·δ(e)）。
fig.add(fk.box("interv", ["Periodic intervention", "mixed batch, share ρ_I"], 990, 470, fk.CF,
               section="train", contrib=True))
fig.add(fk.box("acrm", ["Reward shaping (ACRM)", "same-state comparison"], 0, 720, fk.CF,
               section="train", contrib=True))
fig.add(fk.box("lcap", ["Penalty shaping L_cap", "on intent concentration"], 0, 720, fk.CF,
               section="train", contrib=True))
fig.center_on("acrm", "catfish")
fig.center_on("lcap", "qnets")

# 走廊要夠寬才放得下分流標籤：catfish 右緣 382 到經驗池左緣 600 之間留 218px。
X_FAN = 470      # 鯰魚扇出兩池的垂直走廊
X_JOIN = 890     # 兩池匯入週期性介入的垂直走廊
# 跨帶的兩條線都在兩帶之間的空隙（300..345）轉折：走 section 內部會撞標題帶，
# 貼著任一框線又會讓邊標籤觸發 edge-label-on-frame。
Y_MAINTR = 318   # 主線轉移的橫走
Y_GAP = 328      # 介入回主要代理的橫走
Y_RETURN = 862   # 鯰魚經驗池回鯰魚角色的水平走線（在 acrm/lcap 之下）
X_MARGIN = 20    # 回線的左側畫布邊緣走廊（section 起於 x=40 ⇒ 理想值 20）

E = fig.edge
E("e-env-input", "env", "input", fromAnchor="right", toAnchor="left")
E("e-input-q", "input", "qnets", fromAnchor="right", toAnchor="left")
E("e-q-sel", "qnets", "select", fromAnchor="right", toAnchor="left")
E("e-sel-env", "select", "env", fromAnchor="top", toAnchor="top", label="joint action",
  waypoints=[{"x": fig.cx("select"), "y": 85}, {"x": fig.cx("env"), "y": 85}])

# 兩帶之間的空隙只有 45px，放不下任何邊標籤（label 盒高約 26px，貼上下任一框線都會
# 觸發 edge-label-on-frame）=> 標籤一律用 labelDy 推進帶 B 內部的空白處。
E("e-env-mainpool", "env", "main_pool", fromAnchor="bottom", toAnchor="top",
  label="main-agent transitions", style={"labelDy": 55},
  waypoints=[{"x": fig.cx("env"), "y": Y_MAINTR},
             {"x": fig.cx("main_pool"), "y": Y_MAINTR}])

# 能效分層的扇出。眼檢：原本兩條共用主幹、名稱只能靠一條浮動註記承載，而註記不管放
# 哪裡都會被讀成在標鄰近的另一條箭頭。改成從不同錨點出發 ⇒ 兩條邊完全獨立 ⇒ 各自
# 掛得起標籤（規則 17b 只在同幹時距離為 0），分流語意因此掛在它描述的那條線上。
# 各走一段長水平線 ⇒ 標籤有地方放。走 X_FAN 走廊時標籤只能擠在轉角或壓到經驗池框線
# （後者機器閘看不到，因為它只檢查標籤對「非端點」方框的碰撞）。
E("e-cf-mainpool", "catfish", "main_pool", fromAnchor="top", toAnchor="left",
  label="middle band", style={"labelDy": -30},
  waypoints=[{"x": fig.cx("catfish"), "y": fig.cy("main_pool")}])
E("e-cf-cfpool", "catfish", "cf_pool", fromAnchor="bottom-right", toAnchor="left",
  label="highest band", style={"labelDy": 30},
  waypoints=[{"x": fig.cx("catfish") + fk.ANCHOR_DX, "y": fig.cy("cf_pool")}])

E("e-mainpool-interv", "main_pool", "interv", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_JOIN, "y": fig.cy("main_pool")}, {"x": X_JOIN, "y": fig.cy("interv")}])
# ⚠ 這裡不能用 trimStartPoints：兩條匯入邊只共用最後的接近段，起點並不共用。
# 裁掉第一點會把「鯰魚經驗池 → 走廊」整段砍掉，畫面上剩一條懸空線頭，而兩道機器閘
# 都看不出來（眼檢才抓到）。
E("e-cfpool-interv", "cf_pool", "interv", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_JOIN, "y": fig.cy("cf_pool")}, {"x": X_JOIN, "y": fig.cy("interv")}])

E("e-interv-q", "interv", "qnets", fromAnchor="top", toAnchor="bottom-right",
  # labelDx 必須大過「半個標籤寬 + 到自身垂直段的距離」，否則標籤盒仍被 x=1101 那段貫穿
  label="extra update", style={"labelDx": 150, "labelDy": 80},
  waypoints=[{"x": fig.cx("interv"), "y": Y_GAP},
             {"x": fig.cx("qnets") + fk.ANCHOR_DX, "y": Y_GAP}])

# 回線走畫布左緣，不穿 section 內部（fixture-laws §5）
E("e-cfpool-cf", "cf_pool", "catfish", fromAnchor="bottom", toAnchor="left",
  label="own update",
  waypoints=[{"x": fig.cx("cf_pool"), "y": Y_RETURN},
             {"x": X_MARGIN, "y": Y_RETURN},
             {"x": X_MARGIN, "y": fig.cy("catfish")}])

E("e-acrm-cf", "acrm", "catfish", fromAnchor="top", toAnchor="bottom")
E("e-lcap-q", "lcap", "qnets", fromAnchor="top", toAnchor="bottom")

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。框線／填色／虛線語意進論文圖說。
fig.crop()   # 四邊收到貼合內容（USER 2026-07-19：畫布往內收；本圖有多個外框/欄首，外框保留）

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
