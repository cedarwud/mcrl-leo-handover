#!/usr/bin/env python3
"""容量懲罰（L_cap）— spec builder（新作；圖號待 USER 指派）。

USER 裁決 2026-07-19（第二輪）：補此機制圖——容量懲罰是框架名稱裡「容量感知」的本體，也是目前
唯一健康的 SIGNAL，先前只在 4-2 佔一個方框。
真相源：thesis-mc/ch4-method.md §4.6 式 (4.17)–(4.19)。
程式對照：shared_q_isolation/capacity_penalty.py。

鏈：純量化價值 → 逐使用者軟性偏好（softmax）→ 依實體波束彙總的偏好壓力 → 每顆衛星前 v_max 名
之外的尾端質量 → 平方懲罰 L_cap → 併入訓練損失（部署選法不變）。

⚠ 避開未納入字集的字母（Π/Δ/Ṽ；fixture-laws §7）：這些在方框裡改用敘述，精確符號進圖說。
  只用已納入的 τ／λ／Σ 與 ASCII 下標（L_cap、v_max）。

誠實邊界：只畫機制，不畫效果宣稱；無數值。§4.6 明載單靠此項不保證散開，效果由第五章消融回答
（此邊界寫進圖說，不進畫布）。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit as fk

HERE = pathlib.Path(__file__).parent
STEM = "fig-capacity-penalty"

fig = fk.Fig(
    "Capacity penalty",
    1440, 520,
    "Differentiable capacity penalty in the implemented MCRL framework per "
    "thesis-mc/ch4-method.md 4.6, equations (4.17) to (4.19). Mechanism only — no effectiveness "
    "claim, no result numbers.",
)

# USER 2026-07-19：單一外框的圖不要外框、不要標題（外框＋標題只給圖內有 ≥2 個框的圖）⇒ 移除 section。
# 「僅訓練期／併入損失」等語意進圖說。符號改與 notation-table §13 一致：Π/Δ_s/Ṽ_u 皆 cmap-present（R14 警告非阻擋）。

# 上列（左→右）：價值 → 軟性偏好 → 偏好壓力
ROW1 = [
    ("val", ["Scalarized value", "V_u(a)"]),
    ("soft", ["Per-user preference π_u(a)", "softmax of Ṽ_u at temp. τ"]),
    ("press", ["Per-beam pressure Π", "summed over users"]),
]
# 下列（右→左）：尾端質量 → 平方懲罰 → 併入損失（視覺左到右＝loss, pen, tail）
ROW2 = [
    ("loss", ["Added to the training loss", "deployment arg max unchanged"]),
    ("pen", ["Capacity penalty L_cap", "λ Σ Δ_s²"]),
    ("tail", ["Tail mass Δ_s", "beyond the top v_max"]),
]
CONTRIB = {"soft", "press", "tail", "pen", "loss"}   # val 沿用（純量化價值＝選動作用的 b_u(a)）


def lay(row, y):
    widths = [2 * round((max(fk.text_w(l) for l in lines) + 2 * fk.HPAD) / 2) for _, lines in row]
    gap = (1300 - sum(widths)) // (len(row) - 1)
    x = 70
    for (nid, lines), w in zip(row, widths):
        fig.add(fk.box(nid, lines, x, y, fk.MAIN if nid=="val" else fk.CF, contrib=(nid in CONTRIB)))
        x += w + gap


lay(ROW1, 110)
lay(ROW2, 300)
# 換列的純垂直對齊：兩列寬度不同 ⇒ 平移整個下列，讓 press 與 tail 中心線對齊。
shift = fig.cx("press") - fig.cx("tail")
for nid, _ in ROW2:
    fig.n(nid)["x"] += shift
fig.n("pen")["style"]["strokeWidth"] = 2.5   # 強調＝容量懲罰本體

E = fig.edge
E("e-val-soft", "val", "soft", fromAnchor="right", toAnchor="left")
E("e-soft-press", "soft", "press", fromAnchor="right", toAnchor="left")
E("e-press-tail", "press", "tail", fromAnchor="bottom", toAnchor="top")   # 換列往下
E("e-tail-pen", "tail", "pen", fromAnchor="left", toAnchor="right")
E("e-pen-loss", "pen", "loss", fromAnchor="left", toAnchor="right")

# academic.md rule 9（USER-SET）：論文圖不放頁尾散文。精確式 (4.17)–(4.19) 與邊界說明進論文圖說。
fig.crop()   # 四邊收到貼合內容（targetWidthMm 同比例縮，字級不變）

out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(HERE.parent / f"{STEM}.editable.svg"))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
