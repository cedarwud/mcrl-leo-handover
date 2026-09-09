#!/usr/bin/env python3
"""Emit OUTLINE.md from the same DECK object the .pptx is built from.

Generated, not hand-written, so the Markdown review copy cannot drift from the
deck. Native equations are shown as the LaTeX source recorded in
native-formulas-v025.json — that manifest is what the OMML injector consumes,
so the outline quotes the authority rather than a transcription of it.
"""

from __future__ import annotations

import json
from pathlib import Path

from deck_content import DECK

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "native-formulas-v025.json").read_text(encoding="utf-8"))
BY_ID = {f["id"]: f for f in MANIFEST["formulas"]}

DISPOSITION = {
    1: "REWRITE of V0.23 p.1",
    2: "NEW (states the delta)",
    3: "KEEP of p.2, plus the 10° rule",
    4: "KEEP of p.4",
    5: "REWRITE of p.3",
    6: "NEW (Δ1)",
    7: "NEW (Δ2)",
    8: "NEW (Δ1, coupled solve)",
    9: "NEW (Δ3)",
    10: "NEW (energy model)",
    11: "NEW (metric boundary)",
    12: "REWRITE of p.5",
    13: "NEW (Φ pricing)",
    14: "REWRITE of p.6",
    15: "REWRITE of p.7 merged with p.11",
    16: "NEW — replaces DELETE p.13, 22, 23, 24",
    17: "REWRITE of p.25",
    18: "REWRITE of p.8",
    19: "NEW (the e_i absorption)",
    20: "NEW (Δ9)",
    21: "NEW (two views)",
    22: "NEW (Δ2 accounting)",
    23: "NEW (Δ5 catalogue)",
    24: "NEW (per-arm keys)",
    25: "REWRITE of p.27 — replaces DELETE p.32",
    26: "REWRITE of p.33",
    27: "REWRITE of p.28 and p.29",
    28: "KEEP of p.9, p.30; REWRITE of p.14",
    29: "NEW (comparators)",
    30: "NEW (Δ10)",
    31: "NEW — replaces DELETE p.35, 37",
    32: "REWRITE of p.38 — replaces DELETE p.36",
    33: "NEW (declared idealisations)",
    34: "NEW (symbol succession)",
}


def block(spec, number):
    out = [f"## Slide {number} — {spec['title']}", ""]
    meta = [f"**Disposition:** {DISPOSITION[number]}"]
    if spec.get("badge"):
        meta.append(f"**Badge:** `{spec['badge']}`")
    meta.append(f"**Layout:** {spec['kind']}")
    out.append(" · ".join(meta))
    out.append("")
    if spec.get("subtitle"):
        out.append(f"*{spec['subtitle']}*")
        out.append("")

    kind = spec["kind"]
    if kind == "title":
        for line in spec["lines"]:
            out.append(f"- {line}")
        out.append("")
    elif kind == "cards":
        for card in spec["cards"]:
            out.append(f"**{card['header']}**")
            out.append("")
            for line in card["lines"]:
                out.append(f"- {line}")
            out.append("")
    elif kind == "math":
        for host in spec["hosts"]:
            entry = BY_ID[host["id"]]
            out.append(f"**Native OMML — `{host['id']}`** (label “{host['label']}”, "
                       f"{entry['source']})")
            out.append("")
            out.append("```latex")
            out.append(entry["latex"])
            out.append("```")
            out.append("")
        out.append(f"**{spec['left_header']}**")
        out.append("")
        for line in spec["left_lines"]:
            out.append(f"- {line}")
        out.append("")
        if spec.get("note"):
            out.append(f"> {spec['note']}")
            out.append("")
    elif kind == "quote":
        out.append("> " + spec["quote"])
        out.append("")
        out.append(f"**{spec['header']}**")
        out.append("")
        for line in spec["lines"]:
            out.append(f"- {line}")
        out.append("")
    elif kind == "table":
        out.append("| " + " | ".join(spec["headers"]) + " |")
        out.append("|" + "|".join(["---"] * len(spec["headers"])) + "|")
        for row in spec["rows"]:
            out.append("| " + " | ".join(row) + " |")
        out.append("")

    if spec.get("footer"):
        out.append(f"> {spec['footer']}")
        out.append("")
    out.append(f"**Speaker note.** {spec['notes']}")
    out.append("")
    return out


def main() -> Path:
    hosts = sum(len(s.get("hosts", [])) for s in DECK)
    lines = [
        "# OUTLINE — V0.25 physics-successor deck skeleton",
        "",
        f"Markdown review copy of `v025-deck-skeleton.pptx`: **{len(DECK)} slides**, "
        f"**{hosts} native OfficeMath equations**, one speaker note per slide.",
        "",
        "- **Generated file.** Produced by `make_outline.py` from the same `DECK` "
        "object the deck is built from, so the two cannot drift. Equations are "
        "quoted from `native-formulas-v025.json`, the manifest the OMML injector "
        "consumes.",
        "- **Dispositions** refer to `STORYBOARD-DELTA.md`; V0.23 page numbers are "
        "those of `agy-pilot/STORYBOARD.md`.",
        "- **No result numbers.** `⟨結果待填⟩` marks every slot where a result "
        "belongs.",
        "- **Typography** is the V0.23 contract, unchanged: Times New Roman; 28 pt "
        "titles, 24 pt ordinary body text, 20 pt inside cards, boxes and badges; "
        "no other sizes.",
        "",
        "---",
        "",
    ]
    for number, spec in enumerate(DECK, 1):
        lines += block(spec, number)
        lines.append("---")
        lines.append("")
    path = HERE / "OUTLINE.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(main())
