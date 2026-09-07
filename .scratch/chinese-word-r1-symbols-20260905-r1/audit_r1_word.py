#!/usr/bin/env python3
"""Read-only audit for the private R1 Chinese thesis mirror and DOCX."""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "input" / "thesis-mc"
TABLE = ROOT / "input" / "active-symbol-table.md"
DOCX = ROOT.parent.parent / "artifacts" / "chinese-word-r1-symbols-20260905-r1" / "mcrl-thesis-ZH-r1-symbols-20260905.docx"

R1_FILES = [SRC / name for name in (
    "mc-modqn-base.md", "ch4-method.md", "ch5-experimental-result.md", "ch6-conclusion.md"
)]

OLD_ACTIVE = (
    r"theta_{3dB}", r"p_{\max}", r"p_{\mathrm{sat}}", r"\xi_{\max}",
    r"N^{\mathrm{act}}", r"P_{\mathrm{cir}}", r"P_{\mathrm{BB}}", r"P_{\mathrm{RF}}",
    r"P_{\mathrm{DC}}", r"G_{R,\min}", r"G_{R,\max}", r"\theta^R_{\min}",
    r"A_{\mathrm{zen}}", r"I^{\mathrm{intra}}", r"I^{\mathrm{inter}}", r"B_{\mathrm{sys}}",
    r"^{NF/10}", r"$NF$", r"^{BO/10}", r"$BO$",
)

NEW_ACTIVE = (
    r"\theta_3", r"p^{+}", r"p^{s}", r"\xi^{+}", r"N^a_s", r"P^c", r"P^b",
    r"p_{s,v}", r"P^p_{s,v}", r"G^R_{-}", r"G^R_{+}", r"\theta^R_{-}",
    r"A^z", r"I^i", r"I^x", r"B^g", r"N_f", r"b_o",
)

# These are actual long word-bearing subscripts/superscripts that are forbidden
# on the new R1 paper surface. Function names (mathrm{sin}, log, etc.) are not
# subscripts/superscripts and are intentionally outside this scan.
FORBIDDEN_WORD_MARKS = {
    "3dB", "max", "sat", "act", "cir", "BB", "RF", "DC", "min", "intra",
    "inter", "sys", "zen", "NF", "BO", "req", "target", "estimated", "contrib",
}
IGNORED_TEX_INDEX_OPERATORS = {r"\circ", r"\max"}


def old_hits(text: str) -> list[str]:
    hits: list[str] = []
    for token in OLD_ACTIVE:
        if token in text:
            hits.append(token)
    return hits


def normalize_tex(text: str) -> str:
    """Make one-character bracing variants comparable for presence checks."""
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\{([A-Za-z0-9+_-])\}", r"\1", text)
    return text


def suspicious_indices(text: str) -> list[str]:
    """Find word-bearing braced indices, not products such as k_BTB."""
    found: list[str] = []
    for match in re.finditer(r"(?:_|\^)\{([^{}]*)\}", text):
        value = match.group(1)
        if value in IGNORED_TEX_INDEX_OPERATORS:
            continue
        if any(mark in value for mark in FORBIDDEN_WORD_MARKS):
            found.append(value)
            continue
        for command_value in re.findall(r"\\(?:mathrm|text)\{([^{}]+)\}", value):
            if len(re.sub(r"[^A-Za-z]", "", command_value)) >= 2:
                found.append(value)
                break
    return found


def r1_scope(path: Path, text: str) -> str:
    """Keep the index scan on the paper-facing R1 surface only."""
    if path.name == "mc-modqn-base.md":
        return "\n".join(text.splitlines()[157:376])
    tokens = tuple(normalize_tex(token) for token in NEW_ACTIVE)
    return "\n".join(
        line for line in text.splitlines()
        if any(normalize_tex(token) in normalize_tex(line) for token in tokens)
    )


def main() -> None:
    print(f"DOCX={DOCX}")
    print(f"DOCX_EXISTS={DOCX.is_file()} SIZE={DOCX.stat().st_size if DOCX.is_file() else 0}")
    print("SOURCE_OLD_TOKEN_HITS:")
    for path in R1_FILES:
        hits = old_hits(path.read_text(encoding="utf-8"))
        print(f"  {path.name}: {hits or 'NONE'}")

    # Ignore the first mapping column of the generated overlay when checking
    # the table; historical/legacy sections are reported separately below.
    table = TABLE.read_text(encoding="utf-8")
    overlay_end = table.find("\n## 1. 使用規則\n")
    table_body = table[overlay_end:] if overlay_end >= 0 else table
    print("TABLE_BODY_OLD_TOKEN_HITS:", old_hits(table_body) or "NONE")
    normalized_table = normalize_tex(table_body)
    print("TABLE_ACTIVE_TOKEN_PRESENCE:")
    for token in NEW_ACTIVE:
        print(f"  {token}: {'YES' if normalize_tex(token) in normalized_table else 'NO'}")

    print("R1_MULTI_LETTER_SUBSUP:")
    for path in R1_FILES:
        text = path.read_text(encoding="utf-8")
        words = suspicious_indices(r1_scope(path, text))
        print(f"  {path.name}: {words or 'NONE'}")

    ns = {
        "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    }
    with zipfile.ZipFile(DOCX) as archive:
        ET.fromstring(archive.read("word/document.xml"))
        document = ET.fromstring(archive.read("word/document.xml"))
        maths = document.findall(".//m:oMath", ns)
        styles = [node.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/math}val")
                  for node in document.findall(".//m:oMath//m:sty", ns)]
        texts = "".join(
            (node.text or "")
            for node in document.iter()
            if node.tag in {
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t",
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}t",
            }
        )
        print("OOXML_OMATH_COUNT", len(maths))
        print("OOXML_OMATHPARA_COUNT", len(document.findall(".//m:oMathPara", ns)))
        print("OOXML_MATH_STYLE_COUNTS", {value: styles.count(value) for value in sorted(set(styles))})
        print("OOXML_TEXT_OLD_TOKEN_HITS", old_hits(texts) or "NONE")


if __name__ == "__main__":
    main()
