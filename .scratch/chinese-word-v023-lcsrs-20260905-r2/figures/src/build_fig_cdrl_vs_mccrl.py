#!/usr/bin/env python3
"""CDRL 與 MCRL 訓練流程對照（圖 4-3）— spec builder（2026-07-20 rev-5：貢獻歸屬更正）。

★★ rev-5 更正（USER 2026-07-20 裁決「照證據修正」）★★
rev-4 把**能效分層**與**週期性介入**畫成本論文所加（CDRL 側留空、MCRL 側填沙色）。
這與本專案自己的 CDRL 重現規格衝突——那些規格是**為了重現 [12] 而寫的**：

  * `docs/research/catfish-faithful-route-a/06-catfish-protagonist-executor-sdd.md:101`
    「faithful CDRL: EE stratification + asymmetric discount + ACRM + 70/30 intervention」，
    出處欄註明 "CDRL thesis (reproduce)"。
  * `.../01-catfish-faithful-route-a-sdd.md:125`「The 3 core mechanisms
    (asymmetric discount + stratification + intervention)」。
  * `.../01-...:148`「intervention 70/30; ablation ranking discount>strat>ACRM (**source prior**)」
    ——來源自己跑過 strat 的消融；沒有的機制不可能被消融。
  * `AGENTS.md`「Thesis catfish core = EE stratification + asymmetric discount + ACRM
    + framework conduit (periodic intervention 70/30)」。

⇒ 四個鯰魚機制（能效分層／非對稱折扣／競爭獎勵／週期性介入）**全部沿用 CDRL [12]**，兩側都要畫。
⇒ 連帶：rev-4 左側那條「extra signal」的模糊通道不成立。CDRL 的鯰魚→主要代理通道就是
   分層跨送＋週期性介入本身，不是一條沒說清楚的訊號線。兩側鯰魚欄因此同構。

**本論文相對 CDRL 真正新增的**（＝沙色填底，只有四個框）：
  1. 壅塞情境（m_state）      2. 情境正規化（m_norm）
  3. 鯰魚由 1 個變 3 個、依目標分工（m_cf）
  4. 容量懲罰 L_cap＝懲罰塑形（m_lcap）——CDRL 側無對應，該列留空
（介入退火已於 2026-07-20 依 USER 指示自框架移除——機制仍在測試中；MCRL 的介入比例因此
與 CDRL 同為固定值。）

排法：兩側各一條由上而下的訓練流程，**逐列對齊**——同一列＝同一個步驟，MCRL 多出來的步驟在
CDRL 側留空（情境正規化列、容量懲罰列）。主線右側掛鯰魚支線；分層把中段經驗跨送主要經驗池、
週期性介入定期讓主要代理多更新一次，兩條都指回主要更新。更新→狀態的回線讓它是訓練迴圈。

鯰魚更新框（c_cfupd / m_cfupd）**兩側都是終端**：它從鯰魚經驗池更新鯰魚自己的網路，不直接
回饋主要代理——回饋走的是經驗池（分層跨送＋介入混合批次）。兩側同構，不是右側漏畫。

非對稱折扣不另立方框：直接以兩個更新框上的 β_M 與 β_CF 呈現（β_M < β_CF），這也是實作裡的樣子。

引用編號＝[12]（`REFERENCES.md:33` B.-H. Ke, CDRL, M.S. thesis, NTPU, 2025）。rev-4 寫的 [8] 是
參考文獻重新編號前的舊號。

誠實邊界：只畫訓練流程，不含效果數值。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-cdrl-vs-mccrl"

fig = fk.Fig(
    "CDRL and MCRL training procedures",
    1476, 1320,
    "Side-by-side training procedure of CDRL [12] and the implemented MCRL framework, per "
    "thesis-mc/mc-modqn-base.md 2.1 and ch4-method.md 4.1-4.7. Rows are aligned so that a step "
    "present only in MCRL leaves its CDRL row empty. The four catfish mechanisms are inherited "
    "from CDRL [12]. Procedure only — no effectiveness claim, no result numbers.",
)

fig.note("hdr_l", ["CDRL [12]: RIS-assisted link"], 40, 40)
fig.note("hdr_r", ["MCRL: LEO multi-beam handover"], 770, 40)

# 逐列對齊：同一列＝同一個步驟
Y = dict(state=110, norm=250, q=390, act=530, env=670, upd=810, extra=960, pen=1110)


def centered(nid, lines, cx, y, stroke, **kw):
    n = fk.box(nid, lines, 0, y, stroke, **kw)
    n["x"] = int(cx - n["w"] // 2)
    return fig.add(n)


E = fig.edge


def chain(pairs):
    for a, b in pairs:
        E(f"e-{a}-{b}", a, b, fromAnchor="bottom", toAnchor="top")


# ── 左：CDRL 訓練流程（全部留白＝沒有一項是本論文的） ─────────────────────────
MX_L, CX_L, LOOP_L = 210, 545, 35
centered("c_state", ["State"], MX_L, Y["state"], fk.MAIN)
centered("c_q", ["Single-objective", "Q-network"], MX_L, Y["q"], fk.MAIN)
centered("c_act", ["Select action"], MX_L, Y["act"], fk.MAIN)
centered("c_env", ["Environment", "scalar EE reward"], MX_L, Y["env"], fk.MAIN)
centered("c_upd", ["Main agent update", "discount β_M"], MX_L, Y["upd"], fk.MAIN)
centered("c_cf", ["One catfish role", "no decision output"], CX_L, Y["q"], fk.CF)
centered("c_comp", ["Competitive reward", "vs the main agent"], CX_L, Y["act"], fk.CF)
centered("c_strat", ["EE stratification", "two buffers"], CX_L, Y["env"], fk.CF)
centered("c_cfupd", ["Catfish update", "discount β_CF"], CX_L, Y["upd"], fk.CF)
centered("c_interv", ["Periodic intervention", "fixed mixed batch"], CX_L, Y["extra"], fk.CF)
chain([("c_state", "c_q"), ("c_q", "c_act"), ("c_act", "c_env"), ("c_env", "c_upd"),
       ("c_cf", "c_comp"), ("c_comp", "c_strat"), ("c_strat", "c_cfupd")])
# 分層把中段經驗跨送主要經驗池 ⇒ 分層同時餵主要更新
E("e-c-strat-upd", "c_strat", "c_upd", fromAnchor="left", toAnchor="right",
  waypoints=[{"x": 370, "y": fig.cy("c_strat")}, {"x": 370, "y": fig.cy("c_upd")}])
E("e-c-interv-upd", "c_interv", "c_upd", fromAnchor="left", toAnchor="bottom",
  waypoints=[{"x": MX_L, "y": fig.cy("c_interv")}])
E("e-c-loop", "c_upd", "c_state", fromAnchor="left", toAnchor="left",
  waypoints=[{"x": LOOP_L, "y": fig.cy("c_upd")}, {"x": LOOP_L, "y": fig.cy("c_state")}])

# ── 右：MCRL 訓練流程 ───────────────────────────────────────────────────────
MX_R, CX_R, LOOP_R = 900, 1290, 715
centered("m_state", ["State and", "congestion context"], MX_R, Y["state"], fk.MAIN, contrib=True)
centered("m_norm", ["Context", "normalization"], MX_R, Y["norm"], fk.MAIN, contrib=True)
centered("m_q", ["Three objective", "Q-networks"], MX_R, Y["q"], fk.MAIN)
centered("m_act", ["Per-user arg max"], MX_R, Y["act"], fk.MAIN)
centered("m_env", ["Environment", "reward vector"], MX_R, Y["env"], fk.MAIN)
centered("m_upd", ["Main agent update", "β_M, loss with L_cap"], MX_R, Y["upd"], fk.MAIN)
# 三個鯰魚角色＝依目標分工，是本論文相對 CDRL（單一鯰魚）的延伸 ⇒ 填沙色
centered("m_cf", ["Three catfish", "independent rollout; same model"], CX_R, Y["q"], fk.CF, contrib=True)
centered("m_comp", ["Competitive reward", "on r_1"], CX_R, Y["act"], fk.CF)
centered("m_strat", ["EE stratification", "by EE rank, two buffers"], CX_R, Y["env"], fk.CF)
centered("m_cfupd", ["Catfish update", "discount β_CF"], CX_R, Y["upd"], fk.CF)
centered("m_interv", ["Periodic intervention", "fixed mixed batch"], CX_R, Y["extra"], fk.CF)
# 懲罰塑形：不經由鯰魚，直接加在主要代理的訓練目標上 ⇒ 放**主線欄**、CDRL 側該列留空。
# 框線仍用赭（fk.CF）：FIGURE-MANIFEST §2 的語意是「赭＝鯰魚角色**與各訓練期機制**」，L_cap 是
# 訓練期機制。欄位（主線欄）表達「不經由鯰魚」，顏色表達「僅訓練期」，兩者各司其職。
# 先前誤用 fk.MAIN，與圖 4-2、圖 4-8 的同一個框不一致（2026-07-20 自查抓到）。
centered("m_lcap", ["Capacity penalty L_cap", "in the training objective"], MX_R, Y["pen"],
         fk.CF, contrib=True)
chain([("m_state", "m_norm"), ("m_norm", "m_q"), ("m_q", "m_act"), ("m_act", "m_env"),
       ("m_env", "m_upd"),
       ("m_cf", "m_comp"), ("m_comp", "m_strat"), ("m_strat", "m_cfupd")])
E("e-m-strat-upd", "m_strat", "m_upd", fromAnchor="left", toAnchor="right",
  waypoints=[{"x": 1075, "y": fig.cy("m_strat")}, {"x": 1075, "y": fig.cy("m_upd")}])
E("e-m-interv-upd", "m_interv", "m_upd", fromAnchor="left", toAnchor="bottom-right",
  waypoints=[{"x": MX_R + fk.ANCHOR_DX, "y": fig.cy("m_interv")}])
E("e-m-lcap-upd", "m_lcap", "m_upd", fromAnchor="top", toAnchor="bottom")
E("e-m-loop", "m_upd", "m_state", fromAnchor="left", toAnchor="left",
  waypoints=[{"x": LOOP_R, "y": fig.cy("m_upd")}, {"x": LOOP_R, "y": fig.cy("m_state")}])

fig.crop()

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
