#!/usr/bin/env python3
"""ris_preprocess.py — repo-local pandoc PRE-pass for the to-ris-docx build.

Runs on a COPY of a thesis-mc markdown file (never edits the source). Fixes the
two PREPROCESSOR-level conversion blockers found in the 2026-06-29 dry-run
(scratch/conversion-test/SMOKE-REPORT.md):

  B1  pandoc's OMML writer silently DROPS LaTeX `\\tag{X}` equation numbers.
      Each display block `$$ <body> \\tag{X} $$` is rewritten into the
      matrix-wrapper that already numbers eqs 3.1-3.25 correctly:
          $$\\begin{matrix}
           & <body> & & \\text{(X)}
          \\end{matrix}$$
      Multi-line bodies (incl. `\\begin{cases}`) are preserved verbatim.

  B2  Three display blocks glue TWO `\\begin{matrix}` groups inside one `$$`
      via a `}{` / `}` seam (mc-modqn-base.md L304/L323/L359 = 3.13/14,
      3.18/19, 3.21/22). pandoc lays them out left-to-right and the 2nd eq
      overflows the right margin. Each glued block is split into one `$$...$$`
      per matrix group (each already carries its own `\\text{(3.N)}` number).

  --references (optional): two passes on REFERENCES.md.
    (a) TRIM to the citation list only -- drop the leading build-meta blockquote
        note and everything from the `## 核實附錄` provenance appendix onward
        (that appendix is explicitly marked "非引用格式一部分" / author-tracking
        only), plus the orphaned `---` rule that preceded it. Build-time content
        SELECTION on a copy, not a source structure fix.
    (b) REFORMAT each `[N] body` entry into the ris house-style bibliography
        paragraph. ris.docx renders every reference as `[N]` + Tab + body in a
        HANGING-INDENT paragraph (`w:ind left=425 hanging=425 hangingChars=177`)
        with STRAIGHT quotes and an italic venue name. Plain `[N] body` markdown
        instead inherits the body 2-char first-line indent (空兩格), gets
        pandoc's smart-CURLY quotes, and has no hanging indent -> the list looks
        ragged and unlike ris. Markdown cannot encode a docx hanging indent, so
        each entry is emitted as a pandoc raw-openxml paragraph reproducing
        ris.docx's exact `w:pPr` verbatim (pandoc passes `{=openxml}` blocks
        through untouched; raw text also bypasses smartquotes -> straight quotes
        survive). The `# References` heading + blank lines pass through unchanged.

B7  table column widths. Markdown pipe tables convert to EQUAL-width columns,
    so wide math-heavy cells (e.g. the J_w "value [CI]" column of TABLE-5.2)
    overflow a narrow column and the trailing exponent gets CLIPPED (data loss),
    while CJK headers wrap mid-word. For tables with >=4 columns this pass
    rewrites the separator row with PROPORTIONAL dash counts: each column's
    width tracks its rendered content (CJK=2 units, LaTeX approximated), capped
    so very long cells wrap to 2-3 lines instead of starving the others, and
    floored so each CJK header still fits on one line. The dash counts are
    scaled to sum > pandoc's default --columns (72) so the table fills the page
    width. pandoc maps these relative widths to docx <w:gridCol>, fixing both
    the clip and the bad wrapping. 2-3 column tables already render fine and are
    left byte-identical.

SOURCE markdown structure fixes (B3 heading hierarchy, B5/B6 stray chars) are
DEFERRED and are NOT done here.

Usage:
  ris_preprocess.py IN.md OUT.md [--references]
"""
import re
import sys
import unicodedata

TAG_RE = re.compile(r'\\tag\{([^}]*)\}')
MATH_BLOCK_RE = re.compile(r'\$\$(.*?)\$\$', re.S)
MATRIX_GROUP_RE = re.compile(r'\\begin\{matrix\}.*?\\end\{matrix\}', re.S)
# Everything after the entry list is author-facing bookkeeping (renumber
# crosswalk, moved-out entries with their restore conditions, venue-upgrade
# candidates, the provenance appendix). It stays in REFERENCES.md — those notes
# carry binding restore conditions — but must not print in the thesis, so the
# first `## ` heading after the entries ends the printable region.
# (Was `^##\s*核實附錄`, which cut only the last of the four; USER 2026-07-20.)
AFTER_ENTRIES_RE = re.compile(r'^##\s')


def transform_math_block(inner: str) -> str:
    """Transform the content between one `$$ ... $$` pair. Returns the full
    replacement text INCLUDING the `$$` delimiters."""
    tag = TAG_RE.search(inner)
    if tag:
        # B1: clean `\tag{X}` eq -> matrix-wrapped numbered eq.
        label = tag.group(1).strip()
        body = (inner[:tag.start()] + inner[tag.end():]).strip()
        return (
            '$$\\begin{matrix}\n'
            ' & ' + body + ' & & \\text{(' + label + ')}\n'
            '\\end{matrix}$$'
        )
    if inner.count('\\begin{matrix}') > 1:
        # B2: glued matrix pairs -> one `$$...$$` per matrix group.
        groups = MATRIX_GROUP_RE.findall(inner)
        return '\n'.join('$$' + g + '$$' for g in groups)
    # Single already-numbered matrix block (3.1-3.25) or any other block:
    # pass through byte-identical.
    return '$$' + inner + '$$'


def preprocess_math(text: str) -> str:
    return MATH_BLOCK_RE.sub(lambda m: transform_math_block(m.group(1)), text)


def trim_references(text: str) -> str:
    """Keep the `# References` heading + the [N] entries; drop the leading build-meta
    blockquote note and every author-facing section after the entries."""
    lines = text.splitlines()
    out = []
    seen_first_ref = False
    for line in lines:
        if seen_first_ref and AFTER_ENTRIES_RE.match(line):
            break  # cut the bookkeeping sections and everything after them
        if not seen_first_ref:
            if re.match(r'^\[\d+\]', line):
                seen_first_ref = True
            elif line.lstrip().startswith('>'):
                continue  # drop the leading format-note blockquote
        out.append(line)
    # collapse trailing blank lines + the orphaned `---` rule that used to
    # separate the (now-removed) provenance appendix; keep one terminal newline
    while out and out[-1].strip() in ('', '---', '***', '___'):
        out.pop()
    return '\n'.join(out) + '\n'


# --references reformat: reproduce the ris house-style bibliography ------------
# Target = ris.docx's exact reference paragraph (verified 2026-06-30 against
# catfish/ris.docx): `[N]` + <w:tab/> + body, hanging indent, justified.
REF_ENTRY_RE = re.compile(r'^\[(\d+)\]\s*(.*)$')
REF_PPR = ('<w:pPr>'
           '<w:ind w:left="425" w:hanging="425" w:hangingChars="177"/>'
           '<w:jc w:val="both"/>'
           '</w:pPr>')


def _ref_xml_escape(s: str) -> str:
    """Escape only XML metacharacters; straight quotes are left literal so the
    rendered titles match ris (which stores straight `"`, not curly)."""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _ref_body_runs(body: str) -> str:
    """Markdown `*italic*` spans -> OOXML runs: splitting on `*`, even segments
    are normal text and odd segments are italic (every `*` in these entries is a
    paired italic delimiter -- venue names, acronyms, `*et al.*`)."""
    runs = []
    for i, seg in enumerate(body.split('*')):
        if not seg:
            continue
        t = '<w:t xml:space="preserve">%s</w:t>' % _ref_xml_escape(seg)
        if i % 2:  # inside a *...* pair -> italic
            runs.append('<w:r><w:rPr><w:i/><w:iCs/></w:rPr>%s</w:r>' % t)
        else:
            runs.append('<w:r>%s</w:r>' % t)
    return ''.join(runs)


def format_references(text: str) -> str:
    """Replace every `[N] ...` entry line with a raw-openxml hanging-indent
    paragraph in the ris house style. Non-entry lines (heading, blanks) pass
    through unchanged."""
    out = []
    for line in text.splitlines():
        m = REF_ENTRY_RE.match(line)
        if not m:
            out.append(line)
            continue
        num, body = m.group(1), m.group(2).strip()
        para = ('<w:p>' + REF_PPR
                + '<w:r><w:t xml:space="preserve">[' + num + ']</w:t></w:r>'
                + '<w:r><w:tab/></w:r>'
                + _ref_body_runs(body)
                + '</w:p>')
        out.extend(['```{=openxml}', para, '```'])
    return '\n'.join(out) + '\n'


_PIPE_ROW = re.compile(r'^\s*\|.*\|\s*$')
_SEP_ROW = re.compile(r'^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$')


def _disp_width(cell: str) -> float:
    """Approximate the rendered width of a markdown/LaTeX table cell, in
    en-units (CJK glyph = 2, Latin glyph = 1). Heuristic — used only for
    relative column proportions, so exactness is not required."""
    s = cell.strip()
    s = s.replace('$', '')
    # commands that render to nothing / a name
    s = re.sub(r'\\arg\s*\\?max', 'argmax', s)
    s = re.sub(r'\\(?:text|mathrm|mathcal|mathbb|mathbf|boldsymbol|widehat|'
               r'overrightarrow|left|right)\b', '', s)
    s = re.sub(r'\\(?:times|cdot|approx|le|ge|leq|geq|pm|in|neq|to)\b', 'x', s)
    s = re.sub(r'\\[,!;: ]', '', s)          # thin/medium math spaces
    s = re.sub(r'[_^]\{([^{}]*)\}', r'\1', s)  # sub/superscript -> inner glyphs
    s = re.sub(r'[_^]', '', s)
    s = re.sub(r'\\[a-zA-Z]+', 'x', s)        # any remaining command -> 1 glyph
    s = s.replace('{', '').replace('}', '').replace('\\', '')
    w = 0.0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('W', 'F') or ch == '　':
            w += 2.0
        else:
            w += 1.0
    return w


def _split_cells(row: str):
    r = row.strip()
    if r.startswith('|'):
        r = r[1:]
    if r.endswith('|'):
        r = r[:-1]
    return [c.strip() for c in r.split('|')]


_MATH_SPAN = re.compile(r'\$[^$]*\$')


def _is_cjk(ch: str) -> bool:
    return ch == '　' or unicodedata.east_asian_width(ch) in ('W', 'F')


def _token_floor(cell: str) -> float:
    """Width of the WIDEST unbreakable token in the cell. A `$...$` math span
    never line-breaks in Word OMML, and a Latin word (e.g. ``DQN_throughput``)
    breaks only at spaces/CJK — both must fit their column or they get CLIPPED.
    CJK runs break per character, so they impose no floor."""
    s = cell.strip()
    floor = 0.0
    for m in _MATH_SPAN.findall(s):
        floor = max(floor, _disp_width(m))
    run = ''
    for ch in _MATH_SPAN.sub(' ', s):
        if ch.isspace() or _is_cjk(ch):
            floor = max(floor, _disp_width(run) if run else 0.0)
            run = ''
        else:
            run += ch
    return max(floor, _disp_width(run) if run else 0.0)


def set_table_widths(text: str, *, min_cols: int = 4, cap: float = 10.0,
                     margin: float = 2.0, target_sum: float = 100.0,
                     min_dash: int = 4) -> str:
    """Rewrite the separator row of every pipe table with >= ``min_cols``
    columns to encode proportional column widths (see module docstring B7).

    Per column the target width is ``max(token_floor + margin,
    min(content, cap))``:
      * ``token_floor`` (HARD) = widest unbreakable token, so math spans and
        Latin words never get clipped;
      * ``min(content, cap)`` (SOFT) sizes by content but caps long wrappable
        (CJK) cells so they wrap to a few lines instead of starving the rest.
    Dash counts are scaled so the row sums past pandoc's 72-column default,
    making the table fill the text width. 2-3 column tables are left untouched."""
    lines = text.split('\n')
    out = []
    i, n = 0, len(lines)
    while i < n:
        if (_PIPE_ROW.match(lines[i]) and i + 1 < n
                and _SEP_ROW.match(lines[i + 1])):
            header = lines[i]
            j = i + 2
            body = []
            while j < n and _PIPE_ROW.match(lines[j]) and not _SEP_ROW.match(lines[j]):
                body.append(lines[j])
                j += 1
            hdr_cells = _split_cells(header)
            ncol = len(hdr_cells)
            rows = [_split_cells(r) for r in body]
            if ncol >= min_cols:
                targets = []
                for c in range(ncol):
                    col = [hdr_cells[c]] + [r[c] for r in rows if len(r) > c]
                    content = max(_disp_width(x) for x in col)
                    hard = max(_token_floor(x) for x in col) + margin
                    targets.append(max(hard, min(content, cap)))
                tot = sum(targets) or 1.0
                scale = target_sum / tot
                dashes = [max(min_dash, round(t * scale)) for t in targets]
                # left-align all columns to match the house norm (catfish thesis
                # Tables 3.1 / 5.1 left-align every column, incl. value columns)
                new_sep = '|' + '|'.join(':' + '-' * d for d in dashes) + '|'
                out.append(header)
                out.append(new_sep)
                out.extend(body)
                i = j
                continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_refs = '--references' in sys.argv[1:]
    if len(args) != 2:
        sys.stderr.write('usage: ris_preprocess.py IN.md OUT.md [--references]\n')
        return 2
    src, dst = args
    with open(src, encoding='utf-8') as fh:
        text = fh.read()
    text = preprocess_math(text)
    text = set_table_widths(text)
    if do_refs:
        text = trim_references(text)
        text = format_references(text)
    with open(dst, 'w', encoding='utf-8') as fh:
        fh.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
