#!/usr/bin/env python3
"""build_bilingual.py — assemble the EN->ZH interleaved bilingual MC thesis.

Reads the reviewed English chapters (thesis-mc/en/*.en.md) and the Chinese
sources (thesis-mc/*.md), and produces per-chapter *bilingual* markdown under
thesis-mc/en/bilingual/. Sources are READ-ONLY; this script only writes the
bilingual copies.

Interleaving policy (USER-approved 2026-06-29):

  * Headings  -> emitted ONCE from the EN source as an ATX heading.
  * Display equations ($$...$$) -> emitted ONCE from the EN source after exact
    equality or skeleton equality (whitespace and translated \text{} labels are
    ignored by the structural comparison).
  * Prose paragraphs, lists, [FIG-*] caption placeholders
    -> EN block immediately followed by its ZH block (the interleave).
  * Markdown tables + figure/table caption lines -> EN only (USER 2026-07-20).
    The earlier policy kept both grids because the route-B era tables genuinely
    differed (EN descriptive arm names vs ZH B0/A1/A2 codes); those arms are dead
    and the surviving tables are straight translations, so the ZH grid only
    repeated the EN one directly above it.

Front matter + abstract (mc-modqn-base only):
  * Front matter = the already-bilingual title page (ZH source, before the
    abstract) is reused verbatim.
  * Abstract = the USER-approved en/abstract-bilingual-SAMPLE.md is spliced in.
    Every sample block must also occur verbatim in both monolingual base files,
    so it may reorder those blocks but cannot become an independently worded
    third manuscript.

The walker asserts the EN and ZH block-type sequences stay aligned; any
divergence (a paragraph split differently, a missing equation, or a different
normalized inline-math expression multiset in a paired block) aborts with
context instead of silently corrupting the interleave.

Usage:
  build_bilingual.py [THESIS_MC_DIR] [OUT_DIR]
    THESIS_MC_DIR default: directory of this script's parent (thesis-mc)
    OUT_DIR       default: <THESIS_MC_DIR>/en/bilingual
"""
import os
import re
import sys
from collections import Counter

CJK = re.compile(r'[一-鿿]')
MATH_RE = re.compile(r'\$\$.*?\$\$', re.S)
ATX_RE = re.compile(r'^(#{1,6})\s+(.*\S)\s*$')
BOLD_HEAD_RE = re.compile(r'^\*\*\s*\d.*\*\*\s*$')
# The trailing `{width=NNmm}` pandoc attribute block is optional but MUST be
# tolerated: every figure in this thesis carries one, so a pattern anchored on
# the closing `)` classified all of them as prose, and the interleaver emitted
# the EN and ZH copies of the same byte-identical image line — every figure
# rendered twice in the bilingual docx (29 drawings for 15 figures).
# (USER-reported 2026-07-20.)
IMG_RE = re.compile(r'^!\[[^\]]*\]\([^)]*\)(?:\{[^}]*\})?$')
LEAD_NUM_RE = re.compile(r'^[\d.]+\s*')


class AlignError(Exception):
    pass


TEXT_BODY_RE = re.compile(r'\\text\{[^{}]*\}')
INLINE_MATH_RE = re.compile(
    r'(?<!\\)(?<!\$)\$(?!\$)(.*?)(?<!\\)(?<!\$)\$(?!\$)', re.S)

# Standalone figure-caption placeholders. EN: "[FIG-N: ...]"; ZH: "\[FIG-N：...\]".
FIG_EN_RE = re.compile(r'^\[FIG-([\w.-]+):\s*(.*)\]$', re.S)
FIG_ZH_RE = re.compile(r'^\\\[FIG-([\w.-]+)：\s*(.*)\\\]$', re.S)


def _strip_indent(raw):
    """Drop a leading full-width-space (U+3000) manual indent. The docx body style
    already applies a 2-character first-line indent, so the literal 　　 in the ZH
    source would double-indent; remove it (EN blocks have none, so this is a
    no-op for them). Sources stay read-only — only the bilingual copy is stripped."""
    return re.sub(r'^　+', '', raw)


def _format_figure(raw):
    """Turn a buried "[FIG-N: caption]" placeholder into a visible bold figure
    caption ("**Fig. N (image pending).** caption" / "**圖 N（圖片待插入）。** caption").
    The figure number N stays in the text so the later image-insertion pass can
    still locate each slot. Non-figure blocks pass through unchanged."""
    m = FIG_EN_RE.match(raw.strip())
    if m:
        return '**Fig. %s (image pending).** %s' % (m.group(1), m.group(2).strip())
    m = FIG_ZH_RE.match(raw.strip())
    if m:
        return '**圖 %s（圖片待插入）。** %s' % (m.group(1), m.group(2).strip())
    return raw


def _math_skeleton(s):
    """Math with the bodies of \\text{...} blanked AND all whitespace collapsed, so
    an equation that differs only in an embedded natural-language label (e.g.
    \\text{$a$ activated} vs \\text{$a$ 已開啟}) or in cosmetic layout whitespace
    (e.g. a trailing space before the closing $$, which LaTeX ignores) compares
    equal, while a genuinely different equation does not."""
    s = TEXT_BODY_RE.sub(r'\\text{}', s)
    return re.sub(r'\s+', '', s)


def _inline_math_counter(raw):
    """Return the normalized multiset of inline LaTeX expressions in one block.

    Translation may reorder clauses, so expression order is not significant.
    Digits, operators, grouping, subscripts, superscripts, and multiplicity all
    remain significant. Whitespace and translated ``\\text{...}`` bodies follow
    the same language-neutral normalization used for display equations.
    """
    return Counter(
        _math_skeleton('$' + expression + '$')
        for expression in INLINE_MATH_RE.findall(raw)
    )


def split_blocks(text):
    """Tokenize markdown into a flat list of (type, raw) blocks.

    type is one of: 'math', 'heading', 'table', 'prose'. Display-math regions are
    extracted first (so blank-line layout around equations does not matter), then
    the remaining text is split into paragraph blocks on blank lines.
    """
    blocks = []
    pos = 0
    for m in MATH_RE.finditer(text):
        _add_text_blocks(text[pos:m.start()], blocks)
        blocks.append(('math', m.group(0).strip()))
        pos = m.end()
    _add_text_blocks(text[pos:], blocks)
    return blocks


def _add_text_blocks(chunk, blocks):
    for para in re.split(r'\n[ \t]*\n', chunk):
        para = para.strip('\n')
        if para.strip() == '':
            continue
        blocks.append(_classify(para))


def _classify(para):
    lines = [l for l in para.split('\n') if l.strip() != '']
    if len(lines) == 1 and IMG_RE.match(lines[0].strip()):
        return ('image', para.strip())
    if len(lines) == 1 and (ATX_RE.match(lines[0]) or BOLD_HEAD_RE.match(lines[0])):
        return ('heading', para.strip())
    if lines and all(l.lstrip().startswith('|') for l in lines):
        return ('table', para.strip('\n'))
    return ('prose', para.strip('\n'))


def _heading_text(raw):
    m = ATX_RE.match(raw)
    if m:
        return m.group(2).strip()
    m = re.match(r'^\*\*(.*)\*\*$', raw.strip())
    return m.group(1).strip() if m else raw.strip()


def _atx_level(raw):
    m = ATX_RE.match(raw)
    if m:
        return m.group(1)
    # bold heading: infer level from the numbering depth (N -> #, N.M -> ##, ...)
    txt = _heading_text(raw)
    num = LEAD_NUM_RE.match(txt)
    depth = num.group(0).strip().rstrip('.').count('.') + 1 if num else 1
    return '#' * min(depth, 6)


def _combine_heading(en_raw, zh_raw):
    en_text = _heading_text(en_raw)
    level = _atx_level(en_raw)
    # USER 2026-07-07: bilingual headings are EN-only (no "/ ZH" suffix).
    return '%s %s' % (level, en_text)


# Figures and tables — and their captions — are emitted EN-only (USER 2026-07-20:
# "圖只需要放英文的就好" / "table 也只放英文就好"). A caption is the prose block
# directly after an image or table whose two language variants BOTH open with a
# figure/table number, so ordinary prose that happens to follow one is never
# silently dropped. The short English label above a figure (pandoc's
# ImageCaption, from the alt text) is the house figure label and is left alone.
CAP_EN_RE = re.compile(r'^\**\s*(?:Fig(?:ure)?\.?|Table)\s*\d')
CAP_ZH_RE = re.compile(r'^\**\s*[圖表]\s*\d')


def _is_media_caption(en_raw, zh_raw):
    return bool(CAP_EN_RE.match(en_raw.strip())) and bool(CAP_ZH_RE.match(zh_raw.strip()))


def interleave(zh_text, en_text, label=''):
    zb = split_blocks(zh_text)
    eb = split_blocks(en_text)
    out = []
    prev_media = False
    i = j = 0
    while i < len(zb) and j < len(eb):
        zt, zr = zb[i]
        et, er = eb[j]
        if zt != et:
            raise AlignError(
                '%s: type mismatch at zh#%d=%s / en#%d=%s\n  ZH: %s\n  EN: %s'
                % (label, i, zt, j, et, zr[:140].replace('\n', ' '),
                   er[:140].replace('\n', ' ')))
        z_inline = _inline_math_counter(zr)
        e_inline = _inline_math_counter(er)
        if z_inline != e_inline:
            raise AlignError(
                '%s: inline-math expression multiset differs zh#%d/en#%d\n'
                '  ZH only: %s\n  EN only: %s'
                % (label, i, j,
                   repr(z_inline - e_inline),
                   repr(e_inline - z_inline)))
        if zt == 'heading':
            out.append(_combine_heading(er, zr))
        elif zt == 'image':
            out.append(er)  # language-neutral image, emit once (not duplicated per language)
        elif zt == 'math':
            if zr != er and _math_skeleton(zr) != _math_skeleton(er):
                raise AlignError(
                    '%s: math differs zh#%d/en#%d\n  ZH: %s\n  EN: %s'
                    % (label, i, j, zr[:160].replace('\n', ' '),
                       er[:160].replace('\n', ' ')))
            out.append(er)  # emit once; EN carries any translated \text{} label
        elif zt == 'table':
            out.append(er)  # table: EN only
        elif prev_media and zt == 'prose' and _is_media_caption(er, zr):
            out.append(_format_figure(_strip_indent(er)))  # figure/table caption: EN only
        else:  # prose -> EN then ZH
            out.append(_format_figure(_strip_indent(er)))
            out.append(_format_figure(_strip_indent(zr)))
        prev_media = zt in ('image', 'table')
        i += 1
        j += 1
    if i != len(zb) or j != len(eb):
        raise AlignError('%s: length mismatch: consumed zh %d/%d, en %d/%d'
                         % (label, i, len(zb), j, len(eb)))
    return '\n\n'.join(out) + '\n'


def _read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def _abstract_region(text, label):
    heading = '# 摘要' if label == 'mc-modqn-base.md' else '# Abstract'
    if text.count(heading) != 1:
        raise AlignError('%s: expected exactly one %s heading' % (label, heading))
    start = text.index(heading)
    chapter_one = re.search(r'^(?:#+[ \t]+|\*\*)1\. Introduction', text, re.M)
    if not chapter_one or chapter_one.start() <= start:
        raise AlignError('%s: cannot delimit Abstract before Chapter 1' % label)
    return text[start:chapter_one.start()]


def _assert_abstract_provenance(sample, zh, en):
    """Require every bilingual-abstract block to exist in both monolingual bases.

    The sample deliberately reorders the four abstract/keyword blocks into an
    EN->ZH presentation, so the complete sample is not a contiguous substring
    of either base file.  Block membership proves that it changes ordering only,
    not wording, and prevents the bilingual abstract from becoming a third,
    independently edited manuscript.
    """
    zh_abstract = _abstract_region(zh, 'mc-modqn-base.md')
    en_abstract = _abstract_region(en, 'en/mc-modqn-base.en.md')
    for block_type, raw in split_blocks(sample):
        # The bilingual sample is assembled from the corresponding monolingual
        # source: CJK blocks from the Chinese abstract and non-CJK blocks from
        # the English abstract.  This keeps the Chinese DOCX genuinely Chinese
        # while still preventing a third independently worded abstract.
        source, source_name = (
            (zh_abstract, 'mc-modqn-base.md') if CJK.search(raw)
            else (en_abstract, 'en/mc-modqn-base.en.md')
        )
        if block_type == 'heading':
            source, source_name = en_abstract, 'en/mc-modqn-base.en.md'
        if raw not in source:
            raise AlignError(
                'abstract-bilingual-SAMPLE.md: %s block is absent from '
                'the Abstract region of %s\n  BLOCK: %s'
                % (block_type, source_name, raw[:160].replace('\n', ' ')))


def build_base(src_dir):
    zh = _read(os.path.join(src_dir, 'mc-modqn-base.md'))
    en = _read(os.path.join(src_dir, 'en', 'mc-modqn-base.en.md'))
    sample = _read(os.path.join(src_dir, 'en', 'abstract-bilingual-SAMPLE.md')).strip()
    _assert_abstract_provenance(sample, zh, en)

    front = zh.split('# 摘要', 1)[0].strip()

    zi = zh.index('# 1. Introduction')
    m = re.search(r'^(?:#+[ \t]+|\*\*)1\. Introduction', en, re.M)
    if not m:
        raise SystemExit('build_base: cannot locate ch1 heading in EN file')
    ei = m.start()
    body = interleave(zh[zi:], en[ei:], label='mc-modqn-base')

    return front + '\n\n' + sample + '\n\n' + body


def build_chapter(src_dir, zh_name, en_name):
    zh = _read(os.path.join(src_dir, zh_name))
    en = _read(os.path.join(src_dir, 'en', en_name))
    return interleave(zh, en, label=zh_name)


CHAPTERS = [
    ('bi-ch4-method.md', 'ch4-method.md', 'ch4-method.en.md'),
    # Restored 2026-07-20: the 2026-07-07 exclusion was because the EN result-figure
    # scheme was not block-aligned with ZH ch5. The ch5 retranslation of 2026-07-20 is
    # aligned (34/34 blocks, all four figures byte-identical), and interleave() runs
    # clean. Note ch5 still carries its 〔暫定〕 provisional-figure markers in both
    # languages — that is deliberate; the figures are mid-training estimates.
    ('bi-ch5-experimental-result.md', 'ch5-experimental-result.md', 'ch5-experimental-result.en.md'),
    ('bi-ch6-conclusion.md', 'ch6-conclusion.md', 'ch6-conclusion.en.md'),
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(here)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(src_dir, 'en', 'bilingual')
    os.makedirs(out_dir, exist_ok=True)

    outputs = [('bi-mc-modqn-base.md', build_base(src_dir))]
    for out_name, zh_name, en_name in CHAPTERS:
        outputs.append((out_name, build_chapter(src_dir, zh_name, en_name)))

    for name, content in outputs:
        path = os.path.join(out_dir, name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print('wrote %s (%d bytes)' % (path, len(content.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except AlignError as exc:
        sys.stderr.write('ALIGN ERROR: %s\n' % exc)
        raise SystemExit(1)
