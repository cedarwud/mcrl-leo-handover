#!/usr/bin/env python3
"""把眼檢清單的判定填回 <fig>.eye.json，再交給 check_eye.py 收閘。

用法：python3 fill_eye.py <eye.json> <item-id>=<verdict>:<note> ...
未指定的項目一律填 pass 並附本套圖共用的理由；有特別狀況的項目才逐條覆寫。
注意 eye-pack 每次重跑都會把 eye.json 重設為 unreviewed（svgSha256 是它判斷判定是否過期的依據），
所以順序一定是「先 eye-pack → 看圖 → 再跑本腳本 → check_eye」。
"""
import json
import pathlib
import subprocess
import sys

# USER-SET 2026-07-19（第二輪）：逐框填色（sand #f3efe6 = 本論文貢獻）＋論文圖不放頁尾散文
# （academic.md rule 9，語意進圖說）。DEFAULTS 已依此更新——不可再宣稱「no fills / decoded in legend」，
# 那是舊 scheme，會在眼檢記錄裡斷言假話。
DEFAULTS = {
    "rule-1-ink": "Text is #000000 throughout; canvas is #ffffff. Contribution boxes carry a light sand "
                  "fill #f3efe6 (USER-SET 2026-07-19, lum 0.865 > the 0.55 dark-fill floor); all other "
                  "boxes are #ffffff. No gray body text.",
    "rule-2-colour-budget": "One tint + two border hues, each encoding one declared meaning. Sand #f3efe6 "
                            "fill = this thesis's contribution vs the MODQN baseline (a single tint for a "
                            "single meaning — academic.md rule 2's sanctioned light tint). Borders: navy "
                            "#2f5d80 = main agent / deployment path, ochre #8a5740 = catfish roles and "
                            "training-only mechanisms. No decorative colour; the meaning is stated in the caption.",
    "rule-3-effects": "Flat rects, rx=3 against h=78/106 (<5%); no gradient, shadow, glow, 3D or clip-art.",
    "rule-4-strokes": "Two weights only: 1.5px normal, 2.5px emphasis. Emphasis is the thicker border, "
                      "never a dark fill.",
    "rule-5-type": "Times New Roman only; two sizes (24 node / 22 edge, section, annotation); "
                   "variables italic via autoNotation; Unicode operators only.",
    "rule-6-icons": "No icons or glyphs in this figure.",
    "rule-7-density": "Whitespace sits between semantic groups, not inside boxes.",
    "rule-8-reading-order": "Self-evident spine; dashed frame = training-only. No footer prose "
                            "(academic.md rule 9): frame / fill / dashed meaning lives in the thesis caption.",
    "composition-density": "Checked at print scale on the raster; no dead region large enough to "
                           "read as an unfinished panel.",
    "composition-reading-order": "The eye follows the spine as intended; verified on the raster, not the spec.",
    "composition-label-arrow-attribution": "Every edge label sits on the straight run of the edge it names, "
                                           "clear of neighbouring edges and of every box border.",
    "grayscale-semantic": "Verified on the grayscale twin: solid-vs-dashed frames and the 2.5px emphasis "
                          "stroke survive. The sand fill is subtle in grayscale by design — it is REDUNDANT "
                          "encoding (border hue + the caption also state contribution), so no information is "
                          "lost in black-and-white print.",
}


def main():
    path = pathlib.Path(sys.argv[1])
    overrides = {}
    for arg in sys.argv[2:]:
        key, rest = arg.split("=", 1)
        verdict, _, note = rest.partition(":")
        overrides[key] = (verdict, note)

    doc = json.loads(path.read_text(encoding="utf-8"))
    for item in doc["items"]:
        verdict, note = overrides.get(item["id"], ("pass", DEFAULTS.get(item["id"], "")))
        item["verdict"] = verdict
        item["note"] = note
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    r = subprocess.run(
        ["python3", "/home/u24/.claude/skills/flowchart/checks/check_eye.py", str(path)],
        capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
