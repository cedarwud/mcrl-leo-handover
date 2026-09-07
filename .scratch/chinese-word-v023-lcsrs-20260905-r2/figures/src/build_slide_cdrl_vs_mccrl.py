#!/usr/bin/env python3
"""SLIDE-GRADE CDRL 對 MCRL（自論文 fig-cdrl-vs-mccrl **rev-2** 改編）。

⚠ 對齊的是論文版 rev-2（鯰魚子系統群組框），不是更早的「逐列對照 + 縱向脊」版：
rev-2 的關鍵結構修正＝**鯰魚訓練策略是同時作用的集合、彼此不串接 ⇒ 策略之間不畫箭頭**，
且鯰魚整組是**僅訓練期**（虛線群組框）。舊版用一條縱向脊把策略串起來，會讀成有先後順序。

簡報簡化（相對論文 rev-2）：每側策略合併成「沿用（白）」與「本論文新增（sand）」兩格，
用填色承載 inherited vs added，不逐項列。定位圖非流程圖。
視覺鍵：虛線群組＝僅訓練期；navy＝主要代理面；赭＝鯰魚／訓練機制；sand＝本論文新增／延伸。
內容紅線：只說明設計延伸與定位、無效果數值、無「鯰魚驅動改善」因果宣稱。

★★ 2026-07-20 貢獻歸屬更正（USER 裁決「照證據修正」；與論文版 rev-5 同步）★★
先前把 `m_added` 標成「EE stratification, periodic intervention」＝**錯誤歸類**。本專案自己的
CDRL 重現規格（`06-catfish-protagonist-executor-sdd.md:101`「faithful CDRL: EE stratification +
asymmetric discount + ACRM + 70/30 intervention」、`01-...:148`「ablation ranking
discount>strat>ACRM (source prior)」、`AGENTS.md` 同）記載**四個鯰魚機制全部來自 CDRL [12]**
——來源自己跑過 strat 的消融，沒有的機制不可能被消融。
⇒ CDRL 側改為列出全部四個機制；右側 `m_inherit` 承載這四個。（退火於同日移除後 `m_added` 已刪。）
   鯰魚側之外的新增（壅塞情境＋正規化、逐目標三鯰魚、容量懲罰）維持沙色不變。
⇒ 引用編號改為 [12]（`REFERENCES.md:33`）；先前的 [8] 是參考文獻重新編號前的舊號。
這張是口試會投出來的圖，錯誤歸屬會被當場念出來，故與論文版同批修正。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-cdrl-vs-mccrl"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "CDRL and MCRL (slide)",
    2100, 1200,
    "Design lineage and positioning of MCRL relative to CDRL [12]. Design extension only — "
    "no effectiveness claim, no result numbers.",
)

CX_L, CX_R = 470, 1560
Y_IN, Y_AGENT, Y_CF, Y_STRAT = 140, 400, 720, 900

grp_l = fig.sec("cdrl_cf", "Catfish (train-only)", 0, 640, 100, 420, dash="7 5")
grp_r = fig.sec("mccrl_cf", "Catfish (train-only)", 0, 640, 100, 420, dash="7 5")


def centered(nid, lines, cx, y, stroke, **kw):
    n = fk.box(nid, lines, 0, y, stroke, **kw)
    n["x"] = int(cx - n["w"] // 2)
    return fig.add(n)


def pair(specs, cx, y, gap=70):
    """把兩個方框並排、整體置中於 cx。specs = [(nid, lines, stroke, kwargs), ...]"""
    ws = [2 * round((max(fk.text_w(l) for l in lines) + 2 * fk.HPAD) / 2) for _, lines, _, _ in specs]
    x = cx - (sum(ws) + gap * (len(specs) - 1)) // 2
    for (nid, lines, stroke, kw), w in zip(specs, ws):
        n = fk.box(nid, lines, x, y, stroke, **kw)
        fig.add(n)
        x += w + gap


def header(nid, text, cx, y):
    fig.note(nid, [text], int(cx - fk.text_w(text, fk.FS_SMALL) // 2), y)


header("hdr_l", "CDRL [12]: RIS-assisted link", CX_L, 40)
header("hdr_r", "MCRL (this thesis): LEO multi-beam handover", CX_R, 40)

# ── 左：CDRL（全白＝本論文未新增） ─────────────────────────────────────────────
centered("c_reward", ["Single scalar", "EE reward"], CX_L, Y_IN, fk.MAIN)
centered("c_agent", ["Single-objective", "main agent"], CX_L, Y_AGENT, fk.MAIN)
centered("c_catfish", ["One catfish role"], CX_L, Y_CF, fk.CF, section="cdrl_cf")
centered("c_strat", ["Stratification · asymmetric discount",
                     "competitive reward · intervention"], CX_L, Y_STRAT, fk.CF,
         section="cdrl_cf")

# ── 右：MCRL（新增／延伸填 sand） ────────────────────────────────────────────
pair([("m_reward", ["Reward vector", "[r_1, r_2, r_3]"], fk.MAIN, {}),
      ("m_context", ["Congestion context", "normalized input"], fk.MAIN, {"contrib": True})],
     CX_R, Y_IN)
centered("m_agent", ["Three-objective", "main agent"], CX_R, Y_AGENT, fk.MAIN)
cap = fig.add(fk.box("m_cap", ["Capacity penalty", "L_cap in the loss"], 0, Y_AGENT, fk.CF,
                     contrib=True))
cap["x"] = fig.right("m_agent") + 130
centered("m_catfish", ["Three catfish", "one per objective"], CX_R, Y_CF, fk.CF,
         section="mccrl_cf", contrib=True)
# 2026-07-20：介入退火自框架移除（USER）⇒ 鯰魚欄已無任何本論文新增項，`m_added` 整格刪除。
# 現在的敘事：四個鯰魚機制**原封沿用** CDRL；本論文的新增全在鯰魚欄之外（壅塞情境＋正規化、
# 逐目標三鯰魚、容量懲罰）。這是收窄但誠實的宣稱。
centered("m_inherit", ["Four mechanisms unchanged", "inherited from CDRL"], CX_R, Y_STRAT, fk.CF,
         section="mccrl_cf")
fig.n("m_catfish")["style"]["strokeWidth"] = 3.0   # 強調＝本論文把單一鯰魚擴成逐目標三鯰魚

# 群組框收到各自所含方框（否則 crop 會被過寬的 section 撐大）
for grp, ids in ((grp_l, ["c_catfish", "c_strat"]),
                 (grp_r, ["m_catfish", "m_inherit"])):
    xs = [fig.n(i)["x"] for i in ids] + [fig.right(i) for i in ids]
    grp["x"], grp["w"] = min(xs) - 55, (max(xs) - min(xs)) + 110

Y_MERGE = 340   # 兩個輸入匯入主要代理的橫走（輸入列之下、代理列之上）

E = fig.edge
E("e-c-reward-agent", "c_reward", "c_agent", fromAnchor="bottom", toAnchor="top")
E("e-c-cf-agent", "c_catfish", "c_agent", fromAnchor="top", toAnchor="bottom")

E("e-m-reward-agent", "m_reward", "m_agent", fromAnchor="bottom", toAnchor="top",
  waypoints=[{"x": fig.cx("m_reward"), "y": Y_MERGE}, {"x": fig.cx("m_agent"), "y": Y_MERGE}])
E("e-m-context-agent", "m_context", "m_agent", fromAnchor="bottom", toAnchor="top",
  waypoints=[{"x": fig.cx("m_context"), "y": Y_MERGE}, {"x": fig.cx("m_agent"), "y": Y_MERGE}])
E("e-m-cap-agent", "m_cap", "m_agent", fromAnchor="left", toAnchor="right")
E("e-m-cf-agent", "m_catfish", "m_agent", fromAnchor="top", toAnchor="bottom")
# 策略之間【不畫箭頭】：它們是同時作用的集合，不是先後步驟（論文 rev-2 的結構修正）。

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
