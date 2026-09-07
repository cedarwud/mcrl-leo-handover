#!/usr/bin/env python3
"""bilingual_postprocess.py — extra ris-fidelity fixes for the bilingual docx.

Runs AFTER ris_postprocess.py (which already injected A4 pgSz + ris pgMar +
page-number footer). Adds three fixes that the pandoc + ris-style.docx pipeline
does not emit on its own, matching the catfish/ris.docx gold standard:

  S1  Body paragraph spacing. The ris-style reference doc puts before/after 180
      twips on the body 'Body Text' style (and 36 on 'Compact'); with ~300 body
      paragraphs duplicated bilingually this adds several pages of dead space.
      ris.docx uses 1.5 line spacing with NO extra inter-paragraph space, so zero
      before/after on the body styles only (heading/title spacings untouched).

  T1  Table column layout. pandoc emits <w:tblLayout w:type="fixed"> with equal
      gridCol widths, so wide tables (e.g. the 6-column k_cap sweep) cram numbers
      and wrap names mid-word. Switch every table to autofit so columns size to
      content within the full page width.

  R1  References hanging indent. ris.docx formats each entry as "[N]" + Tab +
      text with a hanging indent (w:ind left=425 hanging=425 hangingChars=177).
      Apply that indent to every reference paragraph (text starts with "[N]") and
      insert a tab after the "[N]" marker.

  W1  NTPU 校徽 page-background watermark. ris.docx places the university emblem
      as a faint behind-text image in the default header, so it appears on every
      page. pandoc + ris-style.docx emit no header part, so the emblem is missing.
      Inject the emblem (thesis-mc/assets/ntpu-watermark.jpeg) + the proven
      behindDoc header (thesis-mc/assets/ntpu_header.xml, lifted verbatim from
      catfish/ris.docx) as a default header, wire its rels + content-types, and
      reference it from the section properties.

In-place rewrite of the given .docx. Idempotent.

Usage:  bilingual_postprocess.py [--watermark-only] path/to.docx

With ``--watermark-only``, apply only W1.  The monolingual build routes use
this mode so all three formal DOCX variants carry the same NTPU watermark.
"""
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.environ.get(
    'THESIS_MC_ASSET_DIR', os.path.join(HERE, '..', 'assets'))

# W1 — NTPU watermark header (rId900 is taken by the ris_postprocess footer).
HEADER_RID = 'rId901'
HEADER_PART = 'word/ntpu_header.xml'
HEADER_RELS_PART = 'word/_rels/ntpu_header.xml.rels'
WM_IMAGE_PART = 'word/media/ntpu-watermark.jpeg'
HEADER_ASSET = os.path.join(ASSETS, 'ntpu_header.xml')
WM_IMAGE_ASSET = os.path.join(ASSETS, 'ntpu-watermark.jpeg')

HEADER_REF = '<w:headerReference w:type="default" r:id="%s"/>' % HEADER_RID
HEADER_RELN = (
    '<Relationship Id="%s" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" '
    'Target="ntpu_header.xml"/>'
) % HEADER_RID
HEADER_CT = (
    '<Override PartName="/word/ntpu_header.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
)
JPEG_DEFAULT = '<Default Extension="jpeg" ContentType="image/jpeg"/>'
# header references its image as rId1 (matches the verbatim ntpu_header.xml).
HEADER_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
    'Target="media/ntpu-watermark.jpeg"/></Relationships>'
)

BODY_SPACING = [
    ('<w:spacing w:after="180" w:before="180" />',
     '<w:spacing w:after="0" w:before="0" />'),
    ('<w:spacing w:after="36" w:before="36" />',
     '<w:spacing w:after="0" w:before="0" />'),
]

HANGING_IND = '<w:ind w:left="425" w:hanging="425" w:hangingChars="177"/>'
REF_TEXT_RE = re.compile(r'^\[\d+\]')
PARA_RE = re.compile(r'<w:p\b.*?</w:p>', re.S)
PPR_RE = re.compile(r'<w:pPr>.*?</w:pPr>', re.S)
IND_RE = re.compile(r'<w:ind\b[^/]*/>')


def _para_text(p):
    return ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p))


def _fix_reference_para(p):
    """Add hanging indent + a tab after the [N] marker to one reference para."""
    # 1) hanging indent in pPr
    m = PPR_RE.search(p)
    if m:
        ppr = m.group(0)
        new_ppr = (IND_RE.sub(HANGING_IND, ppr) if IND_RE.search(ppr)
                   else ppr.replace('<w:pPr>', '<w:pPr>' + HANGING_IND, 1))
        p = p.replace(ppr, new_ppr, 1)
    else:
        p = re.sub(r'(<w:p\b[^>]*>)', r'\1<w:pPr>' + HANGING_IND + '</w:pPr>', p,
                   count=1)
    # 2) tab after the first "] " so the text aligns to the hanging stop
    p = re.sub(r'\]\s', ']</w:t><w:tab/><w:t xml:space="preserve">', p, count=1)
    return p


def _inject_watermark(data):
    """W1: add the NTPU 校徽 behind-text watermark as a default header on every
    page. Returns True if applied, False if the assets are missing. Idempotent
    (re-running detects the header relationship and does not duplicate)."""
    if not (os.path.exists(HEADER_ASSET) and os.path.exists(WM_IMAGE_ASSET)):
        return False
    with open(HEADER_ASSET, 'rb') as fh:
        data[HEADER_PART] = fh.read()
    with open(WM_IMAGE_ASSET, 'rb') as fh:
        data[WM_IMAGE_PART] = fh.read()
    data[HEADER_RELS_PART] = HEADER_RELS_XML.encode('utf-8')

    rels = data['word/_rels/document.xml.rels'].decode('utf-8')
    if HEADER_RID not in rels:
        rels = rels.replace('</Relationships>', HEADER_RELN + '</Relationships>')
    data['word/_rels/document.xml.rels'] = rels.encode('utf-8')

    ct = data['[Content_Types].xml'].decode('utf-8')
    if 'Extension="jpeg"' not in ct:
        ct = ct.replace('</Types>', JPEG_DEFAULT + '</Types>')
    if '/word/ntpu_header.xml' not in ct:
        ct = ct.replace('</Types>', HEADER_CT + '</Types>')
    data['[Content_Types].xml'] = ct.encode('utf-8')
    return True


def main():
    if len(sys.argv) == 2:
        watermark_only = False
        path = sys.argv[1]
    elif len(sys.argv) == 3 and sys.argv[1] == '--watermark-only':
        watermark_only = True
        path = sys.argv[2]
    else:
        sys.stderr.write(
            'usage: bilingual_postprocess.py [--watermark-only] path/to.docx\n')
        return 2
    with zipfile.ZipFile(path) as z:
        data = {n: z.read(n) for n in z.namelist()}

    if not watermark_only:
        # S1 body spacing (styles.xml)
        sty = data['word/styles.xml'].decode('utf-8')
        for old, new in BODY_SPACING:
            sty = sty.replace(old, new)
        data['word/styles.xml'] = sty.encode('utf-8')

    doc = data['word/document.xml'].decode('utf-8')

    n_li = 0
    n_ref = 0
    if not watermark_only:
        # T1 table autofit
        doc = doc.replace('<w:tblLayout w:type="fixed" />',
                          '<w:tblLayout w:type="autofit" />')
        doc = doc.replace('<w:tblLayout w:type="fixed"/>',
                          '<w:tblLayout w:type="autofit"/>')

        # L1 list-item style. The interleave puts the ZH copy of a bullet list right
        # after the EN one, and pandoc merges the two into a single list with a blank
        # line inside it -- a LOOSE list, whose items pandoc emits with NO w:pStyle at
        # all. They then fall back to "Normal" instead of "Compact", which the S1 pass
        # above is the only thing that zeroes, so every multi-item list rendered with
        # visibly larger gaps than the ZH-only build. Stamp Compact on any numbered
        # paragraph that lacks a style; single-item lists already carry it.
        # (USER-reported 2026-07-20.)
        def _stamp_list_style(m):
            nonlocal n_li
            p = m.group(0)
            if '<w:numPr>' not in p or 'w:pStyle' in p:
                return p
            n_li += 1
            return p.replace('<w:pPr>', '<w:pPr><w:pStyle w:val="Compact"/>', 1)

        doc = PARA_RE.sub(_stamp_list_style, doc)

        # R1 reference hanging indent + tab
        def repl(m):
            nonlocal n_ref
            p = m.group(0)
            if REF_TEXT_RE.match(_para_text(p).strip()):
                n_ref += 1
                return _fix_reference_para(p)
            return p

        doc = PARA_RE.sub(repl, doc)

    # W1 sectPr: reference the watermark header (before the existing
    # footerReference; insert after the bare sectPr open as a fallback).
    if HEADER_REF not in doc:
        if '<w:sectPr><w:footerReference' in doc:
            doc = doc.replace('<w:sectPr><w:footerReference',
                              '<w:sectPr>' + HEADER_REF + '<w:footerReference', 1)
        else:
            doc = doc.replace('<w:sectPr>', '<w:sectPr>' + HEADER_REF, 1)
    data['word/document.xml'] = doc.encode('utf-8')

    # W1 parts/rels/content-types
    wm = _inject_watermark(data)

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zo:
        for name, blob in data.items():
            zo.writestr(name, blob)

    if watermark_only:
        print('watermark_postprocess %s : NTPU watermark %s'
              % (path, 'added' if wm else 'SKIPPED (assets missing)'))
    else:
        print('bilingual_postprocess %s : body-spacing 0, tables autofit, %d list '
              'items restyled Compact, %d refs hanging-indented, NTPU watermark %s'
              % (path, n_li, n_ref, 'added' if wm else 'SKIPPED (assets missing)'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
