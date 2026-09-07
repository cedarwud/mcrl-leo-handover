#!/usr/bin/env python3
"""競爭獎勵機制（ACRM）— spec builder。

真相源：thesis-mc/ch4-method.md §4.4 式 (4.14)：
    r^S_{1,u} = r^CF_{1,u} − r^M_{1,u}          （競爭項＝與主要代理的差距）
    r^C_{1,u} = r^CF_{1,u} + η_w · r^S_{1,u}    （線性整形；η_w ≥ 0，η_w=0 退回原獎勵）
程式對照：shared_q_isolation/catfish_pack.py（競爭獎勵、同狀態配對比較）。

2026-07-21 改版（USER 判定舊版「看不懂」，四個缺陷逐條修）。舊版是五個方框的資料流圖，
把式子寫在方框裡 —— 那是「先知道公式才看得懂圖」，等於沒畫。改為 fig4-9 系的**量級圖**：

  1. 符號沒有身分 → 每根長條下方是「詞＋符號」同一塊（Main agent / r_1^M），符號由相鄰的詞定義。
  2. 最關鍵的關係看不出來 → **第三根長條在幾何上就是「第二根 ＋ 那一段」**：
     shaped 那一欄由兩個方框疊成，下半塊與 catfish 長條同高同樣式，上半塊才是 η_w r_1^S。
     鯰魚水平虛線正好落在兩塊的接縫上。落後時（下欄）上半塊改為空心＝被扣掉的那一段。
  3. η 不見了 → 差距 r_1^S（箭頭，主要代理 → 鯰魚）與加上去的 η_w r_1^S 共用鯰魚水平線為鉸鏈，
     一個在線的一側、一個在另一側，後者明顯短於前者 ⇒ η_w 就是那個比例。
  4. ahead / behind 相對於誰 → 欄標題寫明「of Main / behind Main」，且主要代理的水平虛線
     橫貫整欄＝比較基準線。

USER 2026-07-21（逐輪裁決，依序）：
  * 「Main greedy」→「Main agent」。三欄一致以角色命名；「貪婪動作」是限定詞，畫布上解不開
    （ε-greedy 不在圖上），依 rule 9／10 歸圖說——圖說已寫「主要代理的貪婪動作取得 r^M」。
  * r_1^S 移到箭頭右側（尺寸標註的常規位置）並貼近箭頭；η_w r_1^S 貼近 I 形標記。
  * η_w r_1^S 左側加 I 形尺寸標記（上下端帽的豎線），把「那一段」的範圍畫出來——原本只有
    標籤浮在右邊，沒有東西界定它量的是哪一段。
  * **移除「same state, two actions」括號**（原為回答「相對於誰、比的是什麼」而加）。它帶的是
    「配對」這個**成立條件**——兩根長條是同一狀態下兩個動作的結果，不是兩個代理各跑各的平均——
    不是機制本身；圖說第一句已逐字寫了同狀態配對比較與每回合的同步環境副本。條件進圖說、機制留
    畫布是 rule 9／10 的分工，而它是畫面上唯一不屬於長條構造的元件。
    ⚠ 代價要誠實記著：**畫布本身不再排除「這是兩個代理的平均績效比較」的誤讀**。要復原＝把
    brk 那條折線與 lab-state 標籤加回上緣。
  * 全圖字級 24 → **36**（≈12.4pt @175mm）。這在 684px 寬的並排欄裡放不下：光是
    「Catfish trains on」在 36 就 238px，加上 y 軸、三欄間距、I 形標記與 η 標籤，實測最少需要
    ~825px／欄（可行域為空，差 ~140px）。⇒ 兩欄改為**上下堆疊**（academic.md Part 2 明示
    paired panels 可並排或直向堆疊，fig4-10 即是），圖高因此到 ~133mm；本套最高的
    fig-cdrl-vs-mccrl 是 148.7mm，仍在範圍內。
  * 字級與 diagram-kit.json 宣告的論文 profile（node 24／section 22／annotation 22）不同 ⇒
    三個 F0-figure-profile warning。USER 裁決上位，但代價是本圖字級與其他 13 張不一致；
    要不要同步整套是 USER 的決定，本次只改這一張。

⚠ 下標寫在上標之前（r_1^CF 而非 r^CF_1）：渲染器把 notation runs 依序排開、不做上下堆疊。
⚠ 只作用在第一個目標（能量效率）；「主要代理拿未整形的原始獎勵」是圖說的邊界說明（rule 9），
   不進畫布。

誠實邊界：schematic 量級，無刻度、無數值、無效果宣稱。長條高度只表達「誰高、差多少」。
"""
import copy
import pathlib
import sys

# 本資料夾是這批圖的最終位置；figkit 仍住在共用的 src/。
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-competitive-reward"

FS = 40            # USER 2026-07-21：全圖同一字級（24 → 36 → 40，逐輪加大）

fig = fk.Fig(
    "Competitive reward mechanism",
    878, 1116,
    "Paired same-state action comparison for the competitive reward on the first objective (energy efficiency) in the "
    "implemented MCRL framework per thesis-mc/ch4-method.md 4.4, equation (4.14). Schematic bar "
    "levels — no scale, no result numbers, no effectiveness claim.",
)

# 畫布窄了就要同比例縮 targetWidthMm，否則 Word 會把它拉到 175mm、字跟著放大成 17pt。
# 1440px↔175mm 是本套的 px/mm 密度（FIGURE-MANIFEST §2 規則 5，crop() 的同一條算式）。
fig.spec["targetWidthMm"] = round(fig.spec["canvas"]["width"] / 1440 * 175, 2)

fig.spec["style"] = copy.deepcopy(fk.STYLE)
fig.spec["style"]["node"]["fontSize"] = FS
fig.spec["style"]["section"]["fontSize"] = FS          # 欄標題
fig.spec["style"]["annotation"]["fontSize"] = FS       # y 軸語意詞
# edge.labelFontSize 維持 22：本圖沒有任何邊標籤，改它只會多一個 F0 warning 而畫面不變。

# ── 版面常數（兩欄上下堆疊，共用同一套骨架；只有「鯰魚在上／在下」不同） ────────────────
# 畫布寬 = 內容寬，不是紙寬：堆疊後每欄只需要 ~990px，攤到 1392px 會讓長條又矮又遠（實測過）。
# targetWidthMm 隨畫布寬同比例縮（1440px↔175mm 的密度不變）⇒ 字的實體大小不受影響，只是圖變窄。
# USER 2026-07-21：外框左緣往內收 10px、右緣往內收 20px（框與內容之間左 42、右 62）。
# 外框與內容分開定位：CONTENT_X 是內容的原點，SEC_X／SEC_W 只管那個框。
CONTENT_X = 14
SEC_X, SEC_W = 24, 830
SEC_H, SEC_GAP = 520, 28
PANEL_Y = {"a": 24, "b": 24 + SEC_H + SEC_GAP}

# 直向（相對於欄框上緣）
AX_TOP, BASE = 66, 366        # y 軸上端／長條底線 ⇒ 繪圖區高 300
H_HI, H_LO = 220, 130         # 高／低那一根的高度 ⇒ 差距 = 90
PIECE = 45                    # η_w·r_1^S 那一段（schematic：差距的一半 ⇒ η_w 是個比例）
# 差距 80 → 90：字級 40 下 r_1^S 標籤的框有 68px 高，兩條比較線只隔 80px 時只剩 6px 餘裕。
LVL_HI, LVL_LO = BASE - H_HI, BASE - H_LO
XLAB_Y = BASE + 14            # 詞＋符號標籤（兩行）的上緣

# 橫向（相對於欄框左緣）
AXIS_WORD_X = 82              # y 軸語意詞（旋轉 −90）的錨點
AX_X, AX_RIGHT = 120, 668     # y 軸 x／x 軸右端
BAR_W = 76
# 欄距（USER 2026-07-21：長條靠緊一點）。下限由**軸下的兩行標籤**給，不是長條本身：
# 40px 下「Main agent」181px、「Catfish」116px、「Catfish trains on」265px，兩兩之間留 30px
# ⇒ C2−C1 ≥ 179、C3−C2 ≥ 221。現值 180／222 已經貼著這條線，再靠近就要縮短第三欄的詞。
C1, C2, C3 = 188, 368, 590    # 三欄中心
SPAN_X = 446                  # 差距箭頭（第二、三欄之間的走廊）
ETA_MARK_X, ETA_CAP = 656, 12    # I 形尺寸標記：豎線 x 與端帽半寬
# 兩個符號標籤改用 textAnchor="start"（字從方框左緣 +15px 起排），位置由**方框左緣**給。
# 置中排版時字會停在方框中央，而方框寬度是用「含 _ 與 ^ 的原字串」算的（"r_1^S" 量到 85px，
# 實際渲染只有 37px）⇒ 字被推離它所標的東西 50–57px（實測 PNG 像素）。改左對齊後由左緣直接
# 決定字的位置，方框剩下的空白往右擺，不再把字推開。
GAP_LAB_X = 453               # r_1^S：字起於 468，箭頭在 446 ⇒ 22px
ETA_LAB_X = 671               # η_w r_1^S：字起於 686，I 形端帽止於 668 ⇒ 18px

INVIS = {"fill": "none", "stroke": "none", "crossSection": True, "rx": 0}
BAR_MAIN = {"fill": "#ffffff", "stroke": fk.MAIN, "strokeWidth": 1.5, "rx": 0}
BAR_CF = {"fill": fk.CONTRIB, "stroke": fk.CF, "strokeWidth": 1.5, "rx": 0}
BAR_SHAPED = {"fill": fk.CONTRIB, "stroke": fk.CF, "strokeWidth": 2.5, "rx": 0}
# 被扣掉的那一段＝鯰魚長條的頂端被掏空：同一個赭色外框、無填色
BAR_CUT = {"fill": "#ffffff", "stroke": fk.CF, "strokeWidth": 1.5, "rx": 0}

TPAD = 16            # 無框標籤的內距（全圖一致 ⇒ check_layout 規則 8 的 hpad spread = 0）。
                     # 下限是 16：R28 box-fit 用 w−30 當可用寬，15 會在四捨五入時擦邊失敗。
                     # 上限由 R60 給：η 標籤的框（左對齊、右側全是空白）不得超出畫布右緣。
TH = {1: 68, 2: 116}  # vpad = (h − n·48)/2 = 10 / 10 ⇒ spread 0（規則 7 上限 8）

LINES = []
fig.spec["lines"] = LINES


def bar(nid, x, top, h, style):
    """一根長條：無標籤的量級標記（check_layout 的 hpad/vpad 規則會跳過無字方框）。"""
    return fig.add({"id": nid, "label": [""], "x": int(x), "y": int(top),
                    "w": BAR_W, "h": int(h), "style": dict(style)})


def anchor(nid, x, y):
    """看不見的連線端點（邊只能接方框；差距箭頭需要兩個高度上的端點）。"""
    return fig.add({"id": nid, "label": [""], "x": int(x) - 1, "y": int(y) - 1,
                    "w": 2, "h": 2, "style": dict(INVIS)})


def text(nid, lines, cx, ycenter):
    """詞＋符號的無框標籤。方框緊貼文字 ⇒ 不會被連線／引線穿過（那是 ERROR 級）。"""
    n = fk.box(nid, lines, 0, 0, style=dict(INVIS))
    n["w"] = int(round(max(fk.text_w(l, FS) for l in lines))) + 2 * TPAD
    n["h"] = TH[len(lines)]
    n["x"] = int(cx - n["w"] // 2)
    n["y"] = int(ycenter - n["h"] // 2)
    return fig.add(n)


def text_left(nid, lines, left_x, ycenter, w=None):
    """同上，但**左對齊**：字起於 left_x + 15（渲染器對 textAnchor="start" 的固定位移）。

    用於緊貼標記的符號標籤——見 GAP_LAB_X / ETA_LAB_X 的說明。
    """
    n = text(nid, lines, 0, ycenter)
    if w:
        n["w"] = int(w)
    n["x"] = int(left_x)
    n["style"]["textAnchor"] = "start"
    return n


def line(lid, pts, dash=None, stroke=fk.MUTE, role="leader"):
    ln = {"id": lid, "from": {"x": int(pts[0][0]), "y": int(pts[0][1])},
          "to": {"x": int(pts[-1][0]), "y": int(pts[-1][1])}, "role": role,
          "style": {"stroke": stroke}}
    if len(pts) > 2:
        ln["waypoints"] = [{"x": int(px), "y": int(py)} for px, py in pts[1:-1]]
    if dash:
        ln["style"]["dash"] = dash
    LINES.append(ln)
    return ln


def panel(tag, title, cf_ahead):
    """畫一欄。cf_ahead=True ⇒ 鯰魚在主要代理之上（差距為正、加上去一段）。"""
    y0 = PANEL_Y[tag]
    fig.sec(f"{tag}-sec", title, SEC_X, y0, SEC_W, SEC_H)
    X = lambda v: CONTENT_X + v               # noqa: E731  panel-local → absolute
    Y = lambda v: y0 + v                      # noqa: E731

    lvl_m = LVL_LO if cf_ahead else LVL_HI    # 主要代理的水平線
    lvl_c = LVL_HI if cf_ahead else LVL_LO    # 鯰魚的水平線（＝整形的鉸鏈）

    # 軸：語意軸詞，無刻度、無數值（academic.md Part 2 的 mechanism glyph）
    line(f"{tag}-axis-y", [(X(AX_X), Y(AX_TOP)), (X(AX_X), Y(BASE))], stroke=fk.INK, role="axis")
    line(f"{tag}-axis-x", [(X(AX_X), Y(BASE)), (X(AX_RIGHT), Y(BASE))], stroke=fk.INK, role="axis")
    # USER 2026-07-21：軸名縮成「EE Reward」並上移，隨後兩次各再往下 10px。旋轉 −90 時字從
    # 錨點往上排，所以錨點 = 想要的下端；擺在繪圖區上緣往下 40px 處 ⇒ 字落在上半段。
    axis_w = fk.text_w("EE Reward", FS)
    fig.note(f"{tag}-axis-word", ["EE Reward"],
             X(AXIS_WORD_X), Y(AX_TOP + 40 + int(axis_w)), style={"rotate": -90})

    # 兩支評估：同一個狀態下，主要代理的貪婪動作 vs 鯰魚的動作（配對這個條件在圖說）
    bar(f"{tag}-bar-main", X(C1 - BAR_W // 2), Y(lvl_m), BASE - lvl_m, BAR_MAIN)
    bar(f"{tag}-bar-cf", X(C2 - BAR_W // 2), Y(lvl_c), BASE - lvl_c, BAR_CF)

    # 第三根＝第二根 ＋ 那一段。下半塊與鯰魚長條同高同樣式；上半塊才是整形量。
    x3 = X(C3 - BAR_W // 2)
    if cf_ahead:
        bar(f"{tag}-bar-shaped-base", x3, Y(lvl_c), BASE - lvl_c, BAR_CF)
        bar(f"{tag}-bar-piece", x3, Y(lvl_c - PIECE), PIECE, BAR_SHAPED)
        piece_far = lvl_c - PIECE
    else:
        bar(f"{tag}-bar-shaped-base", x3, Y(lvl_c + PIECE), BASE - lvl_c - PIECE, BAR_SHAPED)
        bar(f"{tag}-bar-piece", x3, Y(lvl_c), PIECE, BAR_CUT)   # 空心＝被扣掉的那一段
        piece_far = lvl_c + PIECE
    piece_mid = (lvl_c + piece_far) // 2

    # 兩條比較水平線：主要代理那條橫貫整欄＝「ahead / behind 是相對於誰」
    line(f"{tag}-lvl-main", [(X(C1 + BAR_W // 2), Y(lvl_m)), (X(C3 - BAR_W // 2), Y(lvl_m))],
         dash="12 9")
    line(f"{tag}-lvl-cf", [(X(C2 + BAR_W // 2), Y(lvl_c)), (X(C3 - BAR_W // 2), Y(lvl_c))],
         dash="12 9")

    # 差距：從主要代理的水平線指向鯰魚的水平線（方向＝正負號）
    anchor(f"{tag}-anch-m", X(SPAN_X), Y(lvl_m))
    anchor(f"{tag}-anch-c", X(SPAN_X), Y(lvl_c))
    fig.edge(f"{tag}-gap", f"{tag}-anch-m", f"{tag}-anch-c",
             fromAnchor="top" if cf_ahead else "bottom",
             toAnchor="bottom" if cf_ahead else "top",
             style={"stroke": fk.CF})
    text_left(f"{tag}-lab-gap", ["r_1^S"], X(GAP_LAB_X), Y((lvl_m + lvl_c) // 2))

    # 加上去（或扣掉）的那一段：與差距共用鯰魚水平線為鉸鏈，明顯短於差距 ⇒ η_w 是比例。
    # I 形尺寸標記界定它量的是哪一段（兩個端帽＝鯰魚水平線與整形後的水平線）。
    p_top, p_bot = min(lvl_c, piece_far), max(lvl_c, piece_far)
    line(f"{tag}-eta-dim", [(X(ETA_MARK_X), Y(p_top)), (X(ETA_MARK_X), Y(p_bot))], stroke=fk.CF)
    for cap, cy in (("t", p_top), ("b", p_bot)):
        line(f"{tag}-eta-cap-{cap}",
             [(X(ETA_MARK_X - ETA_CAP), Y(cy)), (X(ETA_MARK_X + ETA_CAP), Y(cy))], stroke=fk.CF)
    # 框寬吃掉：左對齊時右側全是空白，用原字串算出來的 206px 會超出畫布右緣（R60）。
    # 190 讓 hpad 掉到 8（其餘標籤 16），check_layout 規則 8 容許 12 以內的差距。
    text_left(f"{tag}-lab-eta", ["η_w r_1^S"], X(ETA_LAB_X), Y(piece_mid), w=190)

    # 詞＋符號同一塊：符號的身分由相鄰的詞給，不靠讀者記公式
    for cx, lines in ((C1, ["Main agent", "r_1^M"]),
                      (C2, ["Catfish", "r_1^CF"]),
                      (C3, ["Catfish trains on", "r_1^C"])):
        text(f"{tag}-lab-x{[C1, C2, C3].index(cx) + 1}", lines, X(cx), Y(XLAB_Y + TH[2] // 2))


panel("a", "Catfish ahead of Main", True)
panel("b", "Catfish behind Main", False)

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
