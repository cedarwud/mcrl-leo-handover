#!/usr/bin/env python3
"""圖 4-7 訓練與部署流程 — spec builder（英文重作版）。

真相源：thesis-mc/ch4-method.md §4.7（圖 4-7 圖說）＋ notation-table §10–§14。
程式對照：route_b_factorial/faithful_catfish_trainer.py（每步順序：主更新 → 鯰魚 rollout 與分層
          → 鯰魚評論家更新 → 週期性介入）、shared_q_isolation/capacity_penalty.py（L_cap 併入主更新）。

視覺語言與圖 4-2 一致：實線框＝訓練與部署共用的主線；虛線框＝僅訓練期，部署時整組移除。
主線畫成矩形迴圈（狀態 → 正規化 → 估值 → 選動作 → 環境 → 回到狀態），訓練支線掛在下帶。

⚠ FIGURE-MANIFEST §5：若消融判非對稱折扣 NEUTRAL，本圖兩處要改字（β_CF 那行與 β_M 那行）；
建議改字不刪行——刪掉整行會讓該框從兩行變一行，破壞「同列同行數」的中心線對齊。

誠實邊界：只畫流程順序，不畫任何效果宣稱；無數值、無式號（式號放圖例）。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig4-7-training-deployment-flow"

fig = fk.Fig(
    "Fig 4-7 Training and deployment procedure",
    1440, 1100,
    "Per-step procedure of the implemented MCRL framework per thesis-mc/ch4-method.md 4.7. "
    "Order of operations only — no effectiveness claim, no result numbers.",
)

fig.sec("loop", "Per-step main loop", 40, 40, 1360, 420)
fig.sec("train", "Training only", 40, 505, 1360, 395, dash="7 5")

# ── 主線：矩形迴圈 ───────────────────────────────────────────────────────────
ROW1 = [
    # `s^χ_u` 不能寫：autoNotation 不認非 ASCII 上標，插入號會原樣印出（figkit 現在會擋）。
    # 直接畫出它的組成，反而比畫出它的名字清楚。
    ("state", ["Augmented state", "[s_u, χ_u]"]),
    ("norm", ["Context normalization", "network input s̃_u"]),
    ("value", ["Three objective Q-networks", "combined value b_u(a)"]),
]
ENV_LAB = ["Environment", "lights at most v_max beams"]
ACT_LAB = ["Per-user arg max", "ε-greedy during training"]


def _w(lines):
    return 2 * round((max(fk.text_w(l) for l in lines) + 2 * fk.HPAD) / 2)


# 貢獻框（USER-SET 填色軸 A）：狀態擴充 χ_u 與情境正規化是本論文加的；估值／選動作／環境沿用。
CONTRIB_LOOP = {"state", "norm"}
widths = [_w(lines) for _, lines in ROW1]
# 第二列的環境框比第一列的狀態框寬，兩者又要共用同一條中心線（回線是直上直下）。
# 起點若固定 70，環境框的左緣會掉出 section 被 R54 擋下 ⇒ 由寬度差回推起點。
X0 = max(70, 60 + (_w(ENV_LAB) - widths[0]) // 2)
gap = (1370 - X0 - sum(widths)) // (len(ROW1) - 1)
x = X0
for (nid, lines), w in zip(ROW1, widths):
    fig.add(fk.box(nid, lines, x, 110, fk.MAIN, section="loop", contrib=(nid in CONTRIB_LOOP)))
    x += w + gap

fig.add(fk.box("act", ACT_LAB, 0, 300, fk.MAIN, section="loop"))
fig.add(fk.box("env", ENV_LAB, 0, 300, fk.MAIN, section="loop"))
fig.center_on("act", "norm")
fig.center_on("env", "state")

# ── 訓練支線 ─────────────────────────────────────────────────────────────────
fig.add(fk.box("route", ["Stratified routing", "into two replay buffers"], 0, 660, fk.CF,
               section="train", contrib=True))
# 主要代理的更新放上排：梯度回線才能從它的上緣直上，不必繞過鯰魚更新框（放下排時
# 那條線會穿過鯰魚框，被 edge-through-node 擋下）。順帶讓它緊鄰上方的主線。
# upd_main 留白＝更新機制沿用 Double-DQN；本論文加的那一項（L_cap）另立方框（見下）。
# ⚠ 2026-07-20 USER 回報「這張圖看不到容量懲罰」。查證後成立：舊版把 L_cap 塞進本框標籤的附屬
#   子句「discount β_M, loss with L_cap」，而本框是白底 ⇒ 掃過去看不見。而且不一致——圖 4-2 與
#   圖 4-3 都給了 L_cap 專屬沙色框，只有這張沒有。偏偏這張是**訓練流程圖**，職責就是逐步顯示每步
#   發生什麼，把損失裡的那一項藏進子句，等於在最該看到它的地方藏起來。⇒ 拆成獨立方框。
fig.add(fk.box("upd_main", ["Main agent update", "discount β_M"], 560, 560,
               fk.MAIN, section="train"))
# 不等式直接寫在鯰魚更新框上（原為兩框之間的浮動無框節點 beta）。改法理由：那個節點寬 224、
# 正好佔滿 650–744 的整個間隙帶，使 L_cap 無論從哪個底部錨點接進 upd_main 都會 edge-through-node。
# codex 審查要的是「圖上要出現不等式本身」（否則 ch4 §4.3「已於本圖呈現、故不另立非對稱折扣專圖」
# 的宣稱不成立）——寫成 β_CF > β_M 同樣滿足，且與上方 upd_main 的 β_M 並排即可對讀。
fig.add(fk.box("upd_cf", ["Catfish role update", "discount β_CF > β_M"], 560, 760, fk.CF,
               section="train", contrib=True))
fig.add(fk.box("interv", ["Intervention point", "extra mixed-batch update"], 1020, 560, fk.CF,
               section="train", contrib=True))
# 懲罰塑形：不經由鯰魚，直接加在主要代理的訓練目標上（ch4 §4.6）⇒ 與介入分列右側上下兩格，
# 兩者都是「改動主要更新」的來源，但一個走經驗、一個走目標。
fig.add(fk.box("lcap", ["Penalty shaping L_cap", "added to the main loss"], 880, 760, fk.CF,
               section="train", contrib=True))
fig.center_on("route", "env")

X_FAN = 460      # 分流扇出兩個更新的走廊
Y_ACT = 258      # 估值 → 選動作 的橫走（第一列之下、第二列之上）
Y_GRAD = 482     # 梯度回主線的橫走（兩帶之間的空隙）

E = fig.edge
E("e-state-norm", "state", "norm", fromAnchor="right", toAnchor="left")
E("e-norm-value", "norm", "value", fromAnchor="right", toAnchor="left")
# 估值框的下緣要接兩條方向相反的線（出：選動作；入：梯度）⇒ 分別用 bottom-left / bottom-right，
# 否則兩者會擠在同一個單埠錨點上。
E("e-value-act", "value", "act", fromAnchor="bottom-left", toAnchor="top",
  waypoints=[{"x": fig.cx("value") - fk.ANCHOR_DX, "y": Y_ACT},
             {"x": fig.cx("act"), "y": Y_ACT}])
# 環境框與選動作框之間只有約 100px，標籤放在線上會壓到兩端的方框（R58）
# ⇒ 下移到第二列下方的空白處。
E("e-act-env", "act", "env", fromAnchor="left", toAnchor="right",
  label="joint action", style={"labelDy": 95})
E("e-env-state", "env", "state", fromAnchor="top", toAnchor="bottom",
  label="reward vector, next state", style={"labelDx": 175})

E("e-env-route", "env", "route", fromAnchor="bottom", toAnchor="top")
E("e-route-cf", "route", "upd_cf", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_FAN, "y": fig.cy("route")}, {"x": X_FAN, "y": fig.cy("upd_cf")}])
E("e-route-main", "route", "upd_main", fromAnchor="right", toAnchor="left",
  waypoints=[{"x": X_FAN, "y": fig.cy("route")}, {"x": X_FAN, "y": fig.cy("upd_main")}])
E("e-interv-main", "interv", "upd_main", fromAnchor="left", toAnchor="right")
# L_cap 走 upd_main 的 bottom-right 錨點（right 已被介入佔用；同錨點會與介入那條完全重疊 ⇒
# edge-overlap ERROR）。橫走取 y=700：在 upd_main 底緣(650) 與 upd_cf 頂緣(744) 之間，且已把
# beta 靠左對齊讓出 x≈777 的上行段。
Y_LCAP = 700
E("e-lcap-main", "lcap", "upd_main", fromAnchor="top", toAnchor="bottom-right",
  waypoints=[{"x": fig.cx("lcap"), "y": Y_LCAP},
             {"x": fig.cx("upd_main") + fk.ANCHOR_DX, "y": Y_LCAP}])
E("e-main-value", "upd_main", "value", fromAnchor="top", toAnchor="bottom-right",
  # 兩帶之間只有 45px，標籤放在轉折高度會被自己的線貫穿；往上推進主線帶的空白處，
  # 且不加 labelDx（加了會讓標籤盒橫跨 x=1220 那段自身垂直線）。
  label="gradient step", style={"labelDy": -60},
  waypoints=[{"x": fig.cx("upd_main"), "y": Y_GRAD},
             {"x": fig.cx("value") + fk.ANCHOR_DX, "y": Y_GRAD}])

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。順序與式號一律進論文圖說。
fig.crop()   # 四邊收到貼合內容（USER 2026-07-19：畫布往內收；本圖有多個外框/欄首，外框保留）

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
