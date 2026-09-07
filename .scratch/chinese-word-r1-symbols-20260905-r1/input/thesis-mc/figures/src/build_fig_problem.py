#!/usr/bin/env python3
"""問題圖：per-user arg max 的兩條失效路徑 — spec builder（2026-07-20 重畫；同日再修敘事）。

⛔ 2026-07-20 FOUNDATION CORRECTION 之後的措辭紅線：family_b 的 MODQN「崩潰」已查明是 lr 設定
   造成的假象（單變數隔離：只翻 lr 0.01→0.001，argmax EE 235.53→472.22、min_cov 0.312→0.698），
   「MODQN/per-user-argmax 會崩」這個一般前提**已撤回**，任何「本框架修好/解除了崩潰」的線都死了。
   ⇒ 本圖只能陳述「這條決策規則**可能**產生的兩種結構性情形」，**不得**寫成基準的病灶／退化／崩潰。
   前一版畫「All choose the same beam」（全體同質化）即是踩線，已改為 "Several can choose"。
   仍然成立、且撐得住本圖動機的是：raw MODQN 的 min_cov=.586（覆蓋不足是真的，崩潰不是）。

⛔ 前一版的錯（codex 跨模型審查抓到、已逐項查證）：把 v_max 畫成「每波束可服務人數上限」，
於是畫出「多人選同一波束 → 超過 v_max 的人被丟掉」。**這在物理上錯**：
  * notation-table §2：v_max ＝「每顆衛星可同時**啟用的波束數**上限」（式 3.4a），不是每束人數。
  * 多人選**同一個**波束只佔用**一個** active beam ⇒ 不會超過 v_max ⇒ 沒有人會因此被丟掉。
  * ch4 §4.6 明文：「若所有偏好都集中到少數幾個波束上，Δ_s 同樣接近零」——集中反而不觸發容量問題。
  * 使用者被丟掉的真正條件（ch4 §4.1）：「選中的波束沒有被點亮」。

USER 裁決 2026-07-20：問題圖**兩種病灶都畫**（框架剛好各用一個機制對付）：
  帶 A（§4.2 情境正規化要解的）：狀態相近的使用者各自取 arg max ⇒ 同時選中**同一個**波束
     ⇒ 該波束頻寬被分掉、每人吞吐量下降。（不是被丟掉。）
  帶 B（§4.6 容量懲罰要解的）：使用者選到**超過 v_max 個不同**波束 ⇒ 每顆衛星只點亮其中
     v_max 個 ⇒ 選到未點亮波束的使用者該步沒有服務。

兩帶皆為基準行為 ⇒ 無貢獻填色（全白）；痛點以粗框強調。
本圖有 2 個外框 ⇒ 依 USER 規則保留外框＋標題（外框/標題只給 ≥2 框的圖）。

誠實邊界：只畫問題結構，不畫效果宣稱；無數值（v_max 以符號出現，不給具體值）。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-problem-overcrowding"

fig = fk.Fig(
    "Two ways per-user arg max can lose throughput or coverage",
    1440, 900,
    "Two structural situations the per-user arg max rule can produce under the capacity limit, "
    "per thesis-mc/ch4-method.md 4.1, 4.2 and 4.6. These are possibilities of the decision rule, "
    "NOT a claim that the baseline degenerates. Structure only — no effectiveness claim, no "
    "result numbers.",
)

# 兩條全寬帶：兩種不同的失效路徑（≥2 框 ⇒ 保留外框＋標題）
fig.sec("crowd", "Same-beam crowding: bandwidth is shared", 40, 40, 1360, 290)
fig.sec("cap", "More distinct beams than a satellite can light", 40, 375, 1360, 290)


def chain(ids_lines, y, section, emph_last=True):
    """一列等距方框 + 串接的邊；回傳 node ids。"""
    widths = [2 * round((max(fk.text_w(l) for l in lines) + 2 * fk.HPAD) / 2)
              for _, lines in ids_lines]
    gap = (1300 - sum(widths)) // (len(ids_lines) - 1)
    x = 70
    for (nid, lines), w in zip(ids_lines, widths):
        fig.add(fk.box(nid, lines, x, y, fk.MAIN, section=section))
        x += w + gap
    for (a, _), (b, _) in zip(ids_lines, ids_lines[1:]):
        fig.edge(f"e-{a}-{b}", a, b, fromAnchor="right", toAnchor="left")
    if emph_last:
        fig.n(ids_lines[-1][0])["style"]["strokeWidth"] = 2.5   # 強調＝該路徑的後果
    return [n for n, _ in ids_lines]


# ── 帶 A：同束集中 ⇒ 頻寬被分掉（§4.2 的動機） ────────────────────────────────
chain([
    ("a_pick", ["Users with similar inputs", "each take arg max"]),
    ("a_same", ["Several can choose", "the same beam"]),
    ("a_harm", ["Bandwidth is shared", "throughput per user drops"]),
], 130, "crowd")

# ── 帶 B：選了超過 v_max 個不同波束 ⇒ 未點亮的那些沒有服務（§4.6 的動機） ──────
chain([
    ("b_spread", ["Users choose more distinct", "beams than v_max"]),
    ("b_gate", ["Satellite lights only", "v_max of them"]),
    ("b_harm", ["Users on unlit beams", "get no service this step"]),
], 465, "cap")

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。兩條路徑各對應哪個機制，進論文圖說。
fig.crop()

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
