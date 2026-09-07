#!/usr/bin/env python3
"""SLIDE-GRADE 過度集中的兩種病灶（自論文 fig-problem-overcrowding 改編）。

口試動機圖：框架剛好各用一個機制對付兩種病灶。兩條實線帶（皆為基準行為 ⇒ 全白，病灶以粗框標）。
帶 A（情境正規化要解的）：狀態相近的使用者各取 arg max → 同選一個波束 → 頻寬被分掉。
帶 B（容量懲罰要解的）：選到超過 v_max 個不同波束 → 衛星只點亮 v_max 個 → 未點亮者該步無服務。
內容紅線：只畫問題結構、無數值（v_max 為符號）、無效果宣稱。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import figkit_slide as fk

HERE = pathlib.Path(__file__).parent
STEM = "slide-problem-overcrowding"
OUT_SVG = HERE.parents[2] / "slides" / "figures" / "svg" / f"{STEM}.editable.svg"

fig = fk.Fig(
    "Two failure modes of per-user arg max (slide)",
    2400, 940,
    "The two pathologies the framework targets, from the baseline decision rule. "
    "Problem structure only — no effectiveness claim, no result numbers.",
)

SW = 2320
fig.sec("crowd", "Same-beam crowding: bandwidth is shared", 40, 40, SW, 370)
fig.sec("cap", "More distinct beams than a satellite can light", 40, 470, SW, 370)


def band(prefix, labels, y, section):
    ids_lines = [(f"{prefix}{i}", l) for i, l in enumerate(labels)]
    widths = [2 * round((max(fk.text_w(x) for x in l) + 2 * fk.HPAD) / 2) for _, l in ids_lines]
    left, right = 100, 40 + SW - 60
    gap = (right - left - sum(widths)) // (len(ids_lines) - 1)
    x = left
    for (nid, l), w in zip(ids_lines, widths):
        fig.add(fk.box(nid, l, x, y, fk.MAIN, section=section))
        x += w + gap
    for (a, _), (b, _) in zip(ids_lines, ids_lines[1:]):
        fig.edge(f"e-{a}-{b}", a, b, fromAnchor="right", toAnchor="left")
    fig.n(ids_lines[-1][0])["style"]["strokeWidth"] = 3.0   # 強調＝病灶


band("a", [["Users with similar", "inputs take arg max"],
           ["All choose", "the same beam"],
           ["Bandwidth is shared", "throughput per user drops"]], 180, "crowd")
band("b", [["Users pick more", "distinct beams than v_max"],
           ["Satellite lights", "only v_max of them"],
           ["Users on unlit beams", "get no service this step"]], 610, "cap")

fig.crop()
out = fig.write(HERE / f"{STEM}.viz.json")
ok, log = fk.gates(str(out), str(OUT_SVG))
print(log)
print("\nRESULT:", "OK" if ok else "BLOCKED")
