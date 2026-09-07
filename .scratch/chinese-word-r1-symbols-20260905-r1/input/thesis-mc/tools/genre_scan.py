#!/usr/bin/env python3
"""體裁掃描：把「對齊 CDRL 參考論文」的機械準則變成讀數，只報不改。

用法（在 thesis-mc/ 下）：
    python3 tools/genre_scan.py            # 掃所有章
    python3 tools/genre_scan.py ch2 ch3    # 只掃指定章

準則出處＝ WRITING-RULES.md 2026-07-21 條目（自 ch1 對齊導出）。
參考數值取自 ../docs/ref/ris.docx（CDRL 中文定稿）；ch6 的中文只翻了 1 段，其參考值標為不可用。

⛔ 本腳本不判斷內容對錯，只報可機械偵測的體裁項。長度目標（B 層）不在這裡下判決。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                      # thesis-mc/
REF_DOCX = ROOT.parent / "docs" / "ref" / "ris.docx"

# 我方各章的來源檔與起訖錨點
CHAPTERS = {
    "ch1": ("mc-modqn-base.md", "# 1. Introduction", "# 2. Background"),
    "ch2": ("mc-modqn-base.md", "# 2. Background", "# 3. Preliminaries"),
    "ch3": ("mc-modqn-base.md", "# 3. Preliminaries", None),
    "ch4": ("ch4-method.md", "# 4.", None),
    "ch5": ("ch5-experimental-result.md", "# 5.", None),
    "ch6": ("ch6-conclusion.md", "# 6.", None),
}

# 參考論文 ris.docx 的章起訖段落索引（以 "N. Title" 樣式的段落為錨）
REF_RANGES = {"ch1": (25, 50), "ch2": (50, 81), "ch3": (81, 251),
              "ch4": (251, 458), "ch5": (458, 557), "ch6": (557, None)}
REF_BROKEN = {"ch6": "ris.docx 的 ch6 中文只翻了 1 段（EN 25 段 vs ZH 1 段）→ 中文尺不可用"}

# ch1 實測的參考體裁基準（見 WRITING-RULES.md）
REF_SENTENCE_MAX = 74      # 參考 ch1 最長句
REF_SENTENCE_MEAN = 37     # 參考 ch1 平均句長
SENTENCE_CEILING = 75      # A7：參考 ch1 最長值，僅供參照
SENTENCE_HARD = 100        # A7：>100 進人工複核（2026-07-21 跨模型審查後由硬閘降級）

ENUM_PATTERNS = ["其一", "其二", "其三", "第一，", "第二，", "第三，"]
PARA_OPENERS = ["本研究", "本文", "本論文", "在方法上", "在獎勵上"]
DEAD_TERMS = ["目標塑形", "兩類", "兩個兄弟項", "協調式波束分配", "MCCRL", "容量感知",
              "介入退火", "消融", "Double-DQN"]
LOADBEARING_AUTHORS = {"Sun", "Chen"}   # A3：只有這兩個來源可以具名


def zc(s: str) -> int:
    return len(re.findall(r"[一-鿿]", s))


def strip_noise(text: str) -> str:
    """去 HTML 註解、數學、圖行、表格行、標題行——只留可讀散文。"""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.S)
    text = re.sub(r"\$[^$\n]*\$", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?", " ", text)
    keep = [ln for ln in text.splitlines()
            if not ln.startswith("#") and not ln.lstrip().startswith("|")]
    return "\n".join(keep)


def blocks_of(text: str) -> list[str]:
    """連續非空行＝一個段落（markdown 語意）。"""
    out = []
    for raw in text.split("\n\n"):
        b = re.sub(r"\s*\n\s*", " ", raw).strip()
        if b:
            out.append(b)
    return out


def sentences_of(block: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[。])", block) if s.strip()]


def load_ours(name: str) -> str:
    fname, start, end = CHAPTERS[name]
    t = (ROOT / fname).read_text()
    i = t.index(start)
    j = t.index(end) if end else len(t)
    return t[i:j]


def load_ref_len(name: str) -> int | None:
    try:
        import docx  # type: ignore
    except ImportError:
        return None
    if not REF_DOCX.exists():
        return None
    paras = docx.Document(str(REF_DOCX)).paragraphs
    a, b = REF_RANGES[name]
    b = b if b is not None else len(paras)
    return sum(zc(paras[i].text) for i in range(a, b))


def scan(name: str) -> list[str]:
    raw = load_ours(name)
    prose = strip_noise(raw)
    blocks = blocks_of(prose)
    sents = [s for b in blocks for s in sentences_of(b)]
    total = sum(zc(b) for b in blocks)

    lines = [f"\n=== {name} ===", f"中文字 {total}｜段落 {len(blocks)}｜句 {len(sents)}"]

    ref_len = load_ref_len(name)
    if name in REF_BROKEN:
        lines.append(f"  參考長度：⚠ 不可用（{REF_BROKEN[name]}）")
    elif ref_len:
        lines.append(f"  參考 {ref_len} 字 → {total / ref_len:.2f}x  [B 層，本腳本不下判決]")

    if sents:
        mean = sum(zc(s) for s in sents) / len(sents)
        longest = max(sents, key=zc)
        lines.append(f"  平均句長 {mean:.0f}（參考 {REF_SENTENCE_MEAN}）｜"
                     f"最長句 {zc(longest)}（參考 {REF_SENTENCE_MAX}）")

    def report(tag: str, hits: list[str], rule: str) -> None:
        mark = "✅" if not hits else "⚠"
        lines.append(f"  {mark} {rule} {tag}: {len(hits)}")
        for h in hits[:12]:
            lines.append(f"       {h}")
        if len(hits) > 12:
            lines.append(f"       …另 {len(hits) - 12} 筆")

    # A7 句長
    hard = [f"{zc(s)}字 | {s[:52]}…" for s in sents if zc(s) > SENTENCE_HARD]
    soft = [f"{zc(s)}字 | {s[:52]}…" for s in sents
            if SENTENCE_CEILING < zc(s) <= SENTENCE_HARD]
    report("句 >100 字（進人工複核；⛔ 不得為拉低平均而拆散定義／條件／例外／式號）", hard, "A7")
    report("句 76–100 字（參照，非違規）", soft, "A7")

    # A1 列舉體例
    enum = [p for p in ENUM_PATTERNS if p in prose]
    report("列舉用語", [f"{p} ×{prose.count(p)}" for p in enum], "A1")

    # A2 段首主詞 ＋ 全章自稱詞（R4：不用 we／本文／本論文／本研究當主詞）
    openers = [b[:24] + "…" for b in blocks
               if any(b.startswith(o) for o in PARA_OPENERS)]
    report("段落以自稱／方位語開頭", openers, "A2")
    selfref = [f"{w} ×{prose.count(w)}" for w in ("本研究", "本文", "本論文") if w in prose]
    report("自稱詞（全章，含句中；來源歸屬處為已知例外）", selfref, "A2")

    # A3 具名引用
    authors = re.findall(r"([A-Z][A-Za-zÀ-ÿ]+)\s*等人", prose)
    extra = [a for a in authors if a not in LOADBEARING_AUTHORS]
    a3_scope = (name == "ch1")
    report("非載重來源具名（Sun／Chen 以外）" + ("" if a3_scope else "｜A3 僅適用 ch1，本章不算違規"),
           [f"{a} 等人" for a in extra] if a3_scope else [], "A3")
    if not a3_scope and extra:
        lines.append("       （參照：本章具名 " + str(len(extra)) + " 處 — "
                     + "、".join(a + " 等人" for a in extra) + "；參考論文 ch2 用 11 次）")

    # A4 方法名密度
    lines.append(f"  ·  A4 方法名密度：MODQN {prose.count('MODQN')}｜MCRL {prose.count('MCRL')}"
                 f"（每千字 {prose.count('MODQN') / max(total, 1) * 1000:.1f} / "
                 f"{prose.count('MCRL') / max(total, 1) * 1000:.1f}）")

    # A5 清單段首標籤
    labels = [b[:30] + "…" for b in blocks
              if b.startswith("- ") and re.match(r"- [^：]{2,24}：", b)]
    a5_scope = (name == "ch1")
    report("貢獻條帶段首標籤" + ("" if a5_scope else "｜A5 僅適用 ch1 貢獻條，定義式清單可有標籤"),
           labels if a5_scope else [], "A5")
    if not a5_scope and labels:
        lines.append("       （參照：本章帶標籤清單 " + str(len(labels)) + " 條 — 屬定義式清單，體例合法）")

    # A8 + 已刪詞
    dead = [f"{d} ×{prose.count(d)}" for d in DEAD_TERMS if d in prose]
    report("已刪詞／舊分類殘留", dead, "A8")

    # A9 體例
    bold = re.findall(r"\*\*[^*]+\*\*", prose)
    report("內文粗體", [b[:28] for b in bold], "A9")
    fw = [b[:20] + "…" for b in blocks if b.startswith("　")]
    report("段首全形空白", fw, "A9")

    return lines


def main() -> int:
    names = sys.argv[1:] or list(CHAPTERS)
    bad = [n for n in names if n not in CHAPTERS]
    if bad:
        print(f"未知章節：{bad}；可用：{list(CHAPTERS)}")
        return 2
    out: list[str] = ["體裁掃描（只報不改）— 準則見 WRITING-RULES.md 2026-07-21 條目"]
    for n in names:
        out += scan(n)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
