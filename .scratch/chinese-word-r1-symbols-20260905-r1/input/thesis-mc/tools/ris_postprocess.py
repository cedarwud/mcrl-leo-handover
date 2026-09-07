#!/usr/bin/env python3
"""ris_postprocess.py — repo-local docx POST-pass for the to-ris-docx build.

Operates on the pandoc-produced .docx (a zip). Fixes the two build/tooling-level
blockers found in the 2026-06-29 dry-run that pandoc + ris-style.docx do not
emit on their own:

  B4  Page geometry. pandoc emits a bare `<w:sectPr>` with NO `<w:pgSz>` /
      `<w:pgMar>`, so Word defaults to US-Letter (612x792 pt) + ~1in symmetric
      margins. Inject A4 (`w:w=11906 w:h=16838`) + the ris binding margins
      (top/right/bottom 2.5 cm = 1418 twips, left 1.5 cm = 851 twips).

  B5  Page numbers. The package has no header*/footer* parts. Add a default
      footer with a centered PAGE field, wire its relationship + content-type,
      and reference it from the section properties.

  B8  Three-line (三線表) table borders. The bundled "Table" style only draws a
      header rule, so tables have no top/bottom rules (not the academic 三線表
      look). For every table inject table-level borders = top + bottom single
      rule (1.5 pt), all inside/side borders OFF, and give the header row a
      0.75 pt bottom rule. Result: a clean top / header / bottom three-line
      table with no grid.

In-place rewrite of the given .docx. Idempotent (re-running detects the footer
relationship and rebuilds the same sectPr / skips tables already bordered).

Usage:  ris_postprocess.py path/to.docx
"""
import re
import sys
import zipfile

# B8 three-line table borders -------------------------------------------------
_TBL_BORDERS = (
    '<w:tblBorders>'
    '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
    '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
    '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
    '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
    '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
    '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
    '</w:tblBorders>'
)
_TC_HDR_BOTTOM = (
    '<w:tcPr><w:tcBorders>'
    '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
    '</w:tcBorders></w:tcPr>'
)
# The thesis docDefaults set a 2-char first-line indent (首行縮排); it is
# inherited by table cell paragraphs and makes every cell look tab-indented.
# Zero it inside tables only (body paragraphs keep their indent).
_NO_INDENT = '<w:ind w:firstLine="0" w:firstLineChars="0"/>'

# B9 algorithm-table indentation. An algorithm rendered as a table encodes each
# step's nesting depth with leading non-breaking spaces (U+00A0) in the step
# cell. pandoc keeps the nbsp, but they only indent the FIRST visual line — a
# wrapped continuation falls back to the cell's left edge, breaking alignment.
# Convert the leading-nbsp run into a real paragraph LEFT indent so the whole
# step (incl. any wrapped line) sits at its nesting depth and aligns
# (algorithm2e-style depth, no vertical rule). Scoped to tables whose title
# contains "Algorithm " so ordinary data tables are untouched.
ALGO_INDENT_UNIT = 200  # twips of left indent per leading nbsp (2 nbsp ~= one level)
_ALGO_LEAD = re.compile(
    r'</w:pPr>(?:<w:r>(?:<w:rPr>.*?</w:rPr>)?<w:t xml:space="preserve">)(\u00a0+)')


def _algo_indent_para(p: str) -> str:
    """Convert one paragraph's leading U+00A0 depth marker into a real left
    indent; strip the nbsp. No-op when there is no leading nbsp (e.g. the
    line-number cell or a depth-0 step)."""
    m = _ALGO_LEAD.search(p)
    if not m:
        return p
    left = len(m.group(1)) * ALGO_INDENT_UNIT
    p = p[:m.start(1)] + p[m.end(1):]                  # strip the leading nbsp
    if re.search(r'<w:ind\b[^>]*w:left=', p) is None:  # idempotent
        p = re.sub(r'<w:ind ', '<w:ind w:left="%d" ' % left, p, count=1)
    return p


def add_three_line_borders(doc: str) -> str:
    """B8: give every table a top+bottom rule (table-level) and a header-row
    bottom rule, with no inside/side borders -> academic three-line table."""
    def _tblpr(m):
        # OOXML requires tblPr children in schema order: tblBorders must come
        # after tblW and BEFORE tblLayout/tblLook (inserting it later mangles
        # the table). Anchor on the first of those that exists.
        pr = m.group(0)
        if 'w:tblBorders' in pr:
            return pr
        for anchor in ('<w:tblLayout', '<w:tblLook'):
            if anchor in pr:
                return pr.replace(anchor, _TBL_BORDERS + anchor, 1)
        return pr.replace('</w:tblPr>', _TBL_BORDERS + '</w:tblPr>', 1)

    doc = re.sub(r'<w:tblPr>.*?</w:tblPr>', _tblpr, doc, flags=re.S)

    def _table(m):
        tbl = m.group(0)
        # zero the inherited first-line indent in every cell paragraph
        tbl = re.sub(r'(<w:pStyle w:val="Compact" />)(?!<w:ind)',
                     r'\1' + _NO_INDENT, tbl)
        # Every table cell uses explicit left alignment.  This applies to
        # headers, body cells, and algorithm tables alike, so the three DOCX
        # variants do not inherit inconsistent alignment from the reference
        # template or from pandoc's individual cell styles.
        def _left_align_cell_paragraph(pm):
            paragraph = pm.group(0)
            ppr = re.search(r'<w:pPr>.*?</w:pPr>', paragraph, flags=re.S)
            if ppr:
                props = ppr.group(0)
                if re.search(r'<w:jc\b[^>]*/>', props):
                    props = re.sub(r'<w:jc\b[^>]*/>', '<w:jc w:val="left"/>',
                                   props, count=1)
                else:
                    props = props.replace('</w:pPr>', '<w:jc w:val="left"/></w:pPr>')
                return paragraph.replace(ppr.group(0), props, 1)
            return paragraph.replace('<w:p>', '<w:p><w:pPr><w:jc w:val="left"/></w:pPr>', 1)

        tbl = re.sub(r'<w:p\b.*?</w:p>', _left_align_cell_paragraph, tbl, flags=re.S)
        # B9: in algorithm tables, turn leading-nbsp depth markers into a real
        # left indent (whole step incl. wraps aligns at its nesting depth).
        if 'Algorithm ' in re.sub(r'<[^>]+>', '', tbl):
            tbl = re.sub(r'<w:p\b.*?</w:p>',
                         lambda pm: _algo_indent_para(pm.group(0)),
                         tbl, flags=re.S)
        tr = re.search(r'<w:tr\b.*?</w:tr>', tbl, flags=re.S)
        if not tr:
            return tbl
        hdr = tr.group(0)
        if '<w:tcBorders>' in hdr:
            return tbl
        new_hdr = hdr.replace('<w:tcPr />', _TC_HDR_BOTTOM).replace(
            '<w:tcPr/>', _TC_HDR_BOTTOM)
        # bold the header row (house norm: catfish thesis headers are bold)
        new_hdr = new_hdr.replace('<w:r><w:rPr>', '<w:r><w:rPr><w:b/><w:bCs/>')
        new_hdr = new_hdr.replace('<w:r><w:t', '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t')
        return tbl.replace(hdr, new_hdr, 1)

    return re.sub(r'<w:tbl>.*?</w:tbl>', _table, doc, flags=re.S)


# B11 heading / bold-title first-line indent ----------------------------------
# The thesis docDefaults set a 2-char first-line indent (首行縮排,
# w:firstLineChars="200") which is the intended body 首行縮排 and is inherited by
# every paragraph that has no <w:ind> of its own (BodyText / FirstParagraph /
# Compact). Chapter + section titles in ch1-3 (and the chapter-level title of
# ch4-6) are authored in the markdown as **bold** paragraphs, NOT ATX headings,
# so pandoc renders them as ordinary BodyText paragraphs whose runs are all bold.
# Lacking an <w:ind> they ALSO inherit the docDefaults indent and render indented
# (the user sees a title pushed in by ~2 full-width spaces / a tab) — but a title
# must sit flush-left. Real Heading1-6 styles already zero the indent in
# styles.xml; the markdown-bold titles do not use those styles.
#
# This pass forces a zero first-line indent on (a) any Heading-styled paragraph
# (belt-and-suspenders) and (b) every all-bold paragraph OUTSIDE a table (the
# markdown-bold titles). BODY paragraphs KEEP the docDefaults indent: a plain
# paragraph or a "bold lead-in + normal text" paragraph is NOT all-bold, so it is
# left untouched. The global docDefaults indent is deliberately NOT removed —
# doing so would un-indent the body. Tables are carved out first so bold header
# cells (already zeroed by add_three_line_borders) are never touched. Idempotent:
# a paragraph whose first-line indent is already 0 is skipped.
_HEADING_PSTYLE = re.compile(r'<w:pStyle w:val="Heading[1-9]"\s*/>')
_BOLD_RUN = re.compile(r'<w:b(?:\s|/)')          # <w:b/> or <w:b ...> (NOT <w:bCs>)


def _para_all_bold(p: str) -> bool:
    """True when every text-bearing run in the paragraph is bold -> a title.
    A body paragraph (plain, or bold lead-in + normal text) is not all-bold."""
    text_runs = [r for r in re.findall(r'<w:r\b.*?</w:r>', p, flags=re.S)
                 if '<w:t' in r]
    return bool(text_runs) and all(_BOLD_RUN.search(r) for r in text_runs)


def _zero_first_line(p: str) -> str:
    """Force a zero first-line indent on one paragraph (idempotent)."""
    pr = re.search(r'<w:pPr>.*?</w:pPr>', p, flags=re.S)
    if pr and re.search(r'<w:ind\b', pr.group(0)):
        if re.search(r'<w:ind\b[^>]*w:firstLine="0"', pr.group(0)):
            return p                                       # already flush
        new = re.sub(r'<w:ind\b[^>]*/>', _NO_INDENT, pr.group(0), count=1)
        return p.replace(pr.group(0), new, 1)
    if re.search(r'<w:pStyle w:val="[^"]*"\s*/>', p):      # inject after pStyle
        return re.sub(r'(<w:pStyle w:val="[^"]*"\s*/>)',
                      r'\1' + _NO_INDENT, p, count=1)
    if '<w:pPr>' in p:                                      # or at pPr start
        return p.replace('<w:pPr>', '<w:pPr>' + _NO_INDENT, 1)
    return re.sub(r'(<w:p\b[^>]*>)',                        # or add a pPr
                  r'\1<w:pPr>' + _NO_INDENT + '</w:pPr>', p, count=1)


def flush_left_titles(doc: str) -> str:
    """B11: titles (Heading-styled OR all-bold markdown titles, outside tables)
    render flush-left; body paragraphs keep their docDefaults first-line indent."""
    stash = []                                   # carve tables out (never touched)

    def _hide(m):
        stash.append(m.group(0))
        return '\x00T%d\x00' % (len(stash) - 1)

    body = re.sub(r'<w:tbl>.*?</w:tbl>', _hide, doc, flags=re.S)

    def _para(m):
        p = m.group(0)
        if _HEADING_PSTYLE.search(p) or _para_all_bold(p):
            return _zero_first_line(p)
        return p

    body = re.sub(r'<w:p\b.*?</w:p>', _para, body, flags=re.S)

    for i, t in enumerate(stash):                # restore tables
        body = body.replace('\x00T%d\x00' % i, t, 1)
    return body


def flush_list_items(doc: str) -> str:
    """USER 2026-07-20「又開始出現過度縮排」：清單項目吃到雙重縮排。

    根因與 B11/表格儲存格同一個：thesis docDefaults 有 2 字元首行縮排
    (`w:firstLine=480 / w:firstLineChars=200`)，而 pandoc 產出的清單段落 pPr 只帶
    `<w:pStyle w:val="Compact"/>` + `<w:numPr>`，**沒有 w:ind 覆寫** ⇒ 它同時吃到
    numbering 自己的縮排「和」繼承來的首行縮排，疊起來就是過度縮排。
    這裡只把繼承的首行縮排歸零；清單本身的階層縮排(numPr)完全不動，
    所以巢狀清單的層級仍然正確。表格內不碰（已由既有的表格通道處理）。
    """
    stash = []

    def _hide(m):
        stash.append(m.group(0))
        return '\x00L%d\x00' % (len(stash) - 1)

    body = re.sub(r'<w:tbl>.*?</w:tbl>', _hide, doc, flags=re.S)

    def _para(m):
        p = m.group(0)
        return _zero_first_line(p) if '<w:numPr>' in p else p

    body = re.sub(r'<w:p\b.*?</w:p>', _para, body, flags=re.S)
    for i, t in enumerate(stash):
        body = body.replace('\x00L%d\x00' % i, t, 1)
    return body


# USER 2026-07-28: Word was falling back to the document's 720-twip default tab
# because the numbering level had no explicit `num` tab.  Set the actual
# marker-to-text anchor to 360 twips — exactly half that effective Word gap —
# without moving the marker position of a future nested level.  Keep the level
# step and the point-to-text gap as separate constants.
LIST_LEVEL_INDENT_STEP = 120  # marker-position step between nested list levels
LIST_MARKER_TEXT_GAP = 360    # half of Word's former 720-twip fallback tab
_CONTRIBUTION_LIST_INDENT = (
    '<w:ind w:left="%d" w:hanging="%d" '
    'w:firstLine="0" w:firstLineChars="0"/>'
    % (LIST_MARKER_TEXT_GAP, LIST_MARKER_TEXT_GAP)
)
_CONTRIBUTION_LIST_FIRST_ITEM_PREFIXES = (
    "MCRL retains MODQN",
    "MCRL 保留 MODQN 的多目標",
)
_LEFT_ALIGNED_PARAGRAPH_PREFIXES = (
    "Inactive beams (",
    "未啟用的波束（",
)


def left_align_selected_paragraphs(doc: str) -> str:
    """Keep the paired inactive-beam notes left-aligned, never justified."""
    def _para(m: 're.Match[str]') -> str:
        p = m.group(0)
        plain = re.sub(r'<[^>]+>', '', p)
        if not any(plain.startswith(prefix)
                   for prefix in _LEFT_ALIGNED_PARAGRAPH_PREFIXES):
            return p
        pr = re.search(r'<w:pPr>.*?</w:pPr>', p, flags=re.S)
        if not pr:
            return p
        if re.search(r'<w:jc\b[^>]*/>', pr.group(0)):
            new_pr = re.sub(r'<w:jc\b[^>]*/>', '<w:jc w:val="left"/>',
                            pr.group(0), count=1)
        else:
            new_pr = pr.group(0).replace('</w:pPr>', '<w:jc w:val="left"/></w:pPr>')
        return p.replace(pr.group(0), new_pr, 1)

    return re.sub(r'<w:p\b.*?</w:p>', _para, doc, flags=re.S)


def flush_contribution_list_items(doc: str) -> str:
    """Make the introduction's contribution list flush with the text margin.

    All lists retain the thesis-wide 120-twip marker-position step and use the
    explicit 360-twip marker-to-text anchor.
    The unique first contribution item identifies this contiguous three-item
    list in the Chinese, English, and bilingual outputs.  Each item receives a
    direct 360/360 paragraph override, so its marker stays at the left margin
    and its text starts at the same explicit number-tab position.  This also prevents
    Word from falling through to a much wider default tab after the marker.
    """
    active_num_id = None

    def _para(m: 're.Match[str]') -> str:
        nonlocal active_num_id
        p = m.group(0)
        plain = re.sub(r'<[^>]+>', '', p)
        num_id = re.search(r'<w:numId w:val="(\d+)"\s*/>', p)
        if any(prefix in plain for prefix in _CONTRIBUTION_LIST_FIRST_ITEM_PREFIXES):
            active_num_id = num_id.group(1) if num_id else None
        elif not num_id or num_id.group(1) != active_num_id:
            active_num_id = None
        if active_num_id is None:
            return p
        pr = re.search(r'<w:pPr>.*?</w:pPr>', p, flags=re.S)
        if not pr:
            return p
        if re.search(r'<w:ind\b[^>]*/>', pr.group(0)):
            new_pr = re.sub(r'<w:ind\b[^>]*/>', _CONTRIBUTION_LIST_INDENT,
                            pr.group(0), count=1)
        else:
            new_pr = re.sub(r'(</w:numPr>)', r'\1' + _CONTRIBUTION_LIST_INDENT,
                            pr.group(0), count=1)
        return p.replace(pr.group(0), new_pr, 1)

    return re.sub(r'<w:p\b.*?</w:p>', _para, doc, flags=re.S)


def match_reference_list_indent(numbering: str) -> str:
    """USER 2026-07-28：所有清單維持左齊，Word 實際點字定位間距由 720 減半為 360 twips。

    清單縮排有**兩層**，只修一層會以為修好了：
      (a) 繼承自 docDefaults 的首行縮排 → `flush_list_items()`（2026-07-20）已處理；
      (b) numbering 自己的階層縮排 → 就是這裡，2026-07-21 之前從未處理。

    根因不是「值設錯了」而是**pandoc 覆蓋掉模板**：模板 `ris-style.docx` 自己定義
    `abstractNum 990 = left 480 / hanging 480`，但 pandoc 產出時用它的預設
    `left=720 / hanging=360` 蓋掉（符號落在 360、文字塊落在 720）。

    量測到的三個來源都是 480/480（模板、參考中文定稿 `docs/ref/ris.docx` 的貢獻條、
    參考英文 `thesis.pdf` 的渲染亦有縮排）。先前雖把 left/hanging 寫成 120/120，
    但沒有明寫 `num` tab，Microsoft Word 仍可能回退到文件的 720-twip 預設定位點；
    所以使用者看到的實際大空白沒有跟著 120 生效。**USER 2026-07-28 裁決把這個
    Word 實際定位間距減半：每一層明寫 360-twip `num` tab**。符號仍留在各層
    原有位置，換行仍對齊該項文字。這是相對模板的刻意偏離，記於
    `GENRE-RULES.md` §F。

    第 N 層 = `left=120×N+360`、`hanging=360`、`num tab=left`；因此 marker 位置仍為
    `left-hanging=120×N`，只縮短 marker 到文字的距離。由 ilvl 直接算出，
    所以重複執行是冪等的。
    """
    def _lvl(m: 're.Match[str]') -> str:
        lvl = m.group(0)
        if not re.search(r'<w:numFmt w:val="bullet"\s*/>', lvl):
            return lvl
        ilvl = int(m.group(1))
        left = LIST_LEVEL_INDENT_STEP * ilvl + LIST_MARKER_TEXT_GAP
        new_tabs = (
            '<w:tabs><w:tab w:val="num" w:pos="%d"/></w:tabs>' % left
        )
        new_ind = '<w:ind w:left="%d" w:hanging="%d"/>' % (
            left, LIST_MARKER_TEXT_GAP)
        lvl = re.sub(r'<w:ind\b[^>]*/>', new_ind, lvl, count=1)
        if re.search(r'<w:tabs>.*?</w:tabs>', lvl, flags=re.S):
            return re.sub(
                r'<w:tabs>.*?</w:tabs>', new_tabs, lvl, count=1, flags=re.S)
        return lvl.replace(new_ind, new_tabs + new_ind, 1)

    return re.sub(r'<w:lvl w:ilvl="(\d+)"[^>]*>.*?</w:lvl>', _lvl,
                  numbering, flags=re.S)


A4_PGSZ = '<w:pgSz w:w="11906" w:h="16838"/>'
RIS_PGMAR = (
    '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="851" '
    'w:header="720" w:footer="720" w:gutter="0"/>'
)
FOOTER_RID = 'rId900'
FOOTER_PART = 'word/footer1.xml'

FOOTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<w:p><w:pPr><w:jc w:val="center"/>'
    '<w:ind w:firstLine="0" w:firstLineChars="0"/></w:pPr>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:t>1</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    '</w:p></w:ftr>'
)

NEW_SECTPR = (
    '<w:sectPr>'
    '<w:footerReference w:type="default" r:id="%s"/>'
    '<w:footnotePr><w:numRestart w:val="eachSect"/></w:footnotePr>'
    + A4_PGSZ + RIS_PGMAR +
    '</w:sectPr>'
) % FOOTER_RID

FOOTER_RELN = (
    '<Relationship Id="%s" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" '
    'Target="footer1.xml"/>'
) % FOOTER_RID

FOOTER_CT = (
    '<Override PartName="/word/footer1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
)


# B10 figure-caption styling --------------------------------------------------
# pandoc renders each figure's short title (the image alt text) as a paragraph
# in style "ImageCaption", which is basedOn "Caption" -> inherits <w:i/> =
# italic, and is left-aligned. The image itself sits in a "CaptionedFigure"
# paragraph. House rule (USER 2026-06-30): figure titles must be CENTERED and
# NON-italic, in English (e.g. "Fig. 4-1 ..."). Patch both styles in
# styles.xml (one place -> every figure). The long Chinese caption below the
# title is a separate BodyText paragraph and is intentionally left untouched.
# Idempotent: re-running detects the injected jc and skips.
def restyle_figure_captions(styles: str) -> str:
    # centered + no first-line indent (the docDefaults 2-char 首行縮排 "空2格"
    # otherwise shifts the centered figure title / image to the right).
    _CENTER_NOIND = '<w:jc w:val="center"/><w:ind w:firstLine="0" w:firstLineChars="0"/>'

    def _imgcap(m):
        s = m.group(0)
        if 'w:jc w:val="center"' in s:          # already patched
            return s
        inject = ('<w:pPr>' + _CENTER_NOIND + '</w:pPr>'
                  '<w:rPr><w:i w:val="false"/><w:iCs w:val="false"/></w:rPr>')
        return s.replace('</w:style>', inject + '</w:style>', 1)

    def _capfig(m):
        s = m.group(0)
        if 'w:jc w:val="center"' in s:
            return s
        if '<w:pPr>' in s:
            return s.replace('<w:pPr>', '<w:pPr>' + _CENTER_NOIND, 1)
        return s.replace('</w:style>',
                         '<w:pPr>' + _CENTER_NOIND + '</w:pPr></w:style>', 1)

    styles = re.sub(r'<w:style [^>]*w:styleId="ImageCaption"[^>]*>.*?</w:style>',
                    _imgcap, styles, flags=re.S)
    styles = re.sub(r'<w:style [^>]*w:styleId="CaptionedFigure"[^>]*>.*?</w:style>',
                    _capfig, styles, flags=re.S)
    return styles


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write('usage: ris_postprocess.py path/to.docx\n')
        return 2
    path = sys.argv[1]
    with zipfile.ZipFile(path) as z:
        data = {n: z.read(n) for n in z.namelist()}

    # --- B4 + B5 sectPr: replace the body-level sectPr (DOTALL, exactly one) ---
    doc = data['word/document.xml'].decode('utf-8')
    new_doc, n = re.subn(r'<w:sectPr>.*?</w:sectPr>', NEW_SECTPR, doc,
                         count=1, flags=re.S)
    if n != 1:
        sys.stderr.write('error: expected exactly one <w:sectPr>; found %d\n' % n)
        return 1
    new_doc = add_three_line_borders(new_doc)  # B8
    new_doc = flush_left_titles(new_doc)       # B11 flush-left headings/titles
    new_doc = flush_list_items(new_doc)       # 清單項目：去掉繼承的首行縮排（USER 2026-07-20）
    new_doc = flush_contribution_list_items(new_doc)  # introduction 貢獻條目：完全靠左
    new_doc = left_align_selected_paragraphs(new_doc)  # inactive-beam 中英對照：左對齊
    data['word/document.xml'] = new_doc.encode('utf-8')

    # --- B10 figure captions: centered + non-italic (styles.xml) ---
    if 'word/styles.xml' in data:
        styles = data['word/styles.xml'].decode('utf-8')
        data['word/styles.xml'] = restyle_figure_captions(styles).encode('utf-8')

    # --- 清單層級位置不動，Word 點字定位間距由 720 減半為 360（USER 2026-07-28）---
    if 'word/numbering.xml' in data:
        numbering = data['word/numbering.xml'].decode('utf-8')
        data['word/numbering.xml'] = match_reference_list_indent(numbering).encode('utf-8')

    # --- B5 footer part ---
    data[FOOTER_PART] = FOOTER_XML.encode('utf-8')

    # --- B5 relationship ---
    rels = data['word/_rels/document.xml.rels'].decode('utf-8')
    if FOOTER_RID not in rels:
        rels = rels.replace('</Relationships>', FOOTER_RELN + '</Relationships>')
    data['word/_rels/document.xml.rels'] = rels.encode('utf-8')

    # --- B5 content type ---
    ct = data['[Content_Types].xml'].decode('utf-8')
    if '/word/footer1.xml' not in ct:
        ct = ct.replace('</Types>', FOOTER_CT + '</Types>')
    data['[Content_Types].xml'] = ct.encode('utf-8')

    # rewrite the zip
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zo:
        for name, blob in data.items():
            zo.writestr(name, blob)

    print('postprocessed %s : A4 pgSz + ris pgMar + page-number footer '
          '+ three-line table borders + centered non-italic figure captions '
          '+ flush-left headings/titles + list level step %d / marker-text gap %d'
          % (path, LIST_LEVEL_INDENT_STEP, LIST_MARKER_TEXT_GAP))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
