#!/usr/bin/env python3
"""Verify structural/source parity of the ZH, EN, and bilingual thesis DOCX.

Usage:
  verify_three_docx.py SOURCE_ROOT ZH.docx EN.docx BILINGUAL.docx

This is a structural OOXML gate, not a visual renderer. Final pagination and
appearance still require MS Word inspection.
"""
import hashlib
import collections
import pathlib
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET


NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
}
W_VAL = '{%s}val' % NS['w']
W_STYLE_ID = '{%s}styleId' % NS['w']
W_ABSTRACT_NUM_ID = '{%s}abstractNumId' % NS['w']
W_NUM_ID = '{%s}numId' % NS['w']
W_ILVL = '{%s}ilvl' % NS['w']
W_LEFT = '{%s}left' % NS['w']
W_HANGING = '{%s}hanging' % NS['w']
W_POS = '{%s}pos' % NS['w']
W_START = '{%s}start' % NS['w']
W_TYPE = '{%s}type' % NS['w']
R_EMBED = '{%s}embed' % NS['r']
EXPECTED_LIST_LEVEL_STEP_TWIPS = 120
EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS = 360
CJK_RE = re.compile(
    r'[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff'
    r'\uff01-\uff60\uffe0-\uffee]')
IMAGE_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)(?:\{[^}]*\})?')
MATH_RE = re.compile(r'\$\$.*?\$\$', re.S)
TAG_RE = re.compile(r'\\tag\{([^}]+)\}')
DOCX_EQ_LABEL_RE = re.compile(r'\(([^()]+)\)')
FIG_CAPTION_RE = re.compile(r'^Fig\. \d+(?:-\d+)?:')
REFERENCE_RE = re.compile(r'^\[(\d+)\]')

ZH_SOURCES = (
    'mc-modqn-base.md',
    'ch4-method.md',
    'ch5-experimental-result.md',
    'ch6-conclusion.md',
)
EN_SOURCES = (
    'en/mc-modqn-base.en.md',
    'en/ch4-method.en.md',
    'en/ch5-experimental-result.en.md',
    'en/ch6-conclusion.en.md',
)


class VerifyError(Exception):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _style_map(archive):
    root = ET.fromstring(archive.read('word/styles.xml'))
    result = {}
    for style in root.findall('w:style', NS):
        style_id = style.get(W_STYLE_ID, '')
        name = style.find('w:name', NS)
        result[style_id] = name.get(W_VAL, style_id) if name is not None else style_id
    return result


def _paragraph_text(paragraph):
    return ''.join(node.text or '' for node in paragraph.findall('.//w:t', NS))


def _docx_facts(path):
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise VerifyError('%s: corrupt zip member %s' % (path, bad_member))
        document = ET.fromstring(archive.read('word/document.xml'))
        body = document.find('w:body', NS)
        if body is None:
            raise VerifyError('%s: document has no body' % path)
        rel_root = ET.fromstring(
            archive.read('word/_rels/document.xml.rels'))
        rels = {
            rel.get('Id'): rel.get('Target')
            for rel in rel_root.findall('rel:Relationship', NS)
        }
        styles = _style_map(archive)
        numbering = ET.fromstring(archive.read('word/numbering.xml'))

        numbering_levels = {}
        for abstract in numbering.findall('w:abstractNum', NS):
            abstract_id = abstract.get(W_ABSTRACT_NUM_ID)
            for level in abstract.findall('w:lvl', NS):
                ilvl = int(level.get(W_ILVL, '0'))
                num_fmt_node = level.find('w:numFmt', NS)
                num_fmt = (
                    num_fmt_node.get(W_VAL)
                    if num_fmt_node is not None else None
                )
                indent = level.find('./w:pPr/w:ind', NS)
                if indent is None:
                    raise VerifyError(
                        '%s: numbering level %s/%d has no indentation'
                        % (path, abstract_id, ilvl))
                left = indent.get(W_LEFT)
                hanging = indent.get(W_HANGING)
                if left is None or hanging is None:
                    raise VerifyError(
                        '%s: numbering level %s/%d lacks left/hanging'
                        % (path, abstract_id, ilvl))
                num_tabs = [
                    tab for tab in level.findall('./w:pPr/w:tabs/w:tab', NS)
                    if tab.get(W_VAL) == 'num'
                ]
                if (num_fmt == 'bullet'
                        and (len(num_tabs) != 1
                             or num_tabs[0].get(W_POS) is None)):
                    raise VerifyError(
                        '%s: numbering level %s/%d lacks exactly one num tab'
                        % (path, abstract_id, ilvl))
                numbering_levels[(abstract_id, ilvl)] = (
                    num_fmt,
                    int(left),
                    int(hanging),
                    (int(num_tabs[0].get(W_POS)) if num_tabs else None),
                )

        num_to_abstract = {}
        for num in numbering.findall('w:num', NS):
            abstract = num.find('w:abstractNumId', NS)
            if abstract is not None:
                num_to_abstract[num.get(W_NUM_ID)] = abstract.get(W_VAL)

        drawings = []
        for drawing in document.findall('.//w:drawing', NS):
            blip = drawing.find('.//a:blip', NS)
            if blip is None or not blip.get(R_EMBED):
                raise VerifyError('%s: drawing without embedded image' % path)
            target = rels.get(blip.get(R_EMBED))
            if not target:
                raise VerifyError('%s: unresolved drawing relationship' % path)
            member = posixpath.normpath(posixpath.join('word', target))
            drawings.append(_sha256(archive.read(member)))

        equations = []
        equation_xml_hashes = []
        equation_labels = []
        for equation in document.findall('.//m:oMathPara', NS):
            tokens = [
                node.text or '' for node in equation.findall('.//m:t', NS)
            ]
            equations.append(''.join(tokens))
            equation_xml_hashes.append(_sha256(ET.tostring(equation)))
            labels = [
                match.group(1)
                for token in tokens
                for match in [DOCX_EQ_LABEL_RE.fullmatch(token)]
                if match
            ]
            equation_labels.append(labels[-1] if labels else None)

        parents = {
            child: parent for parent in document.iter() for child in parent
        }
        inline_math_xml_hashes = []
        for equation in document.findall('.//m:oMath', NS):
            ancestor = parents.get(equation)
            is_display = False
            while ancestor is not None:
                if ancestor.tag == '{%s}oMathPara' % NS['m']:
                    is_display = True
                    break
                ancestor = parents.get(ancestor)
            if not is_display:
                inline_math_xml_hashes.append(
                    _sha256(ET.tostring(equation)))

        headings = []
        image_captions = []
        formal_captions = []
        references = []
        visible = []
        list_items = []
        table_alignments = []
        for paragraph in document.findall('.//w:tbl//w:p', NS):
            alignment = paragraph.find('./w:pPr/w:jc', NS)
            table_alignments.append(
                alignment.get(W_VAL) if alignment is not None else None)
        for paragraph in document.findall('.//w:p', NS):
            text = _paragraph_text(paragraph)
            if text:
                visible.append(text)
            num_pr = paragraph.find('./w:pPr/w:numPr', NS)
            if num_pr is not None:
                ilvl_node = num_pr.find('w:ilvl', NS)
                num_id_node = num_pr.find('w:numId', NS)
                if num_id_node is None:
                    raise VerifyError('%s: list paragraph has no numId' % path)
                ilvl = int(
                    ilvl_node.get(W_VAL, '0') if ilvl_node is not None else '0')
                num_id = num_id_node.get(W_VAL)
                abstract_id = num_to_abstract.get(num_id)
                base_indent = numbering_levels.get((abstract_id, ilvl))
                if base_indent is None:
                    raise VerifyError(
                        '%s: cannot resolve list indentation for numId=%s ilvl=%d'
                        % (path, num_id, ilvl))
                num_fmt, left, hanging, tab_pos = base_indent
                direct_indent = paragraph.find('./w:pPr/w:ind', NS)
                if direct_indent is not None:
                    if direct_indent.get(W_LEFT) is not None:
                        left = int(direct_indent.get(W_LEFT))
                    if direct_indent.get(W_HANGING) is not None:
                        hanging = int(direct_indent.get(W_HANGING))
                direct_num_tabs = [
                    tab for tab in paragraph.findall(
                        './w:pPr/w:tabs/w:tab', NS)
                    if tab.get(W_VAL) == 'num'
                ]
                if direct_num_tabs:
                    tab_pos = int(direct_num_tabs[-1].get(W_POS))
                list_items.append({
                    'text': text,
                    'num_id': num_id,
                    'num_fmt': num_fmt,
                    'ilvl': ilvl,
                    'left': left,
                    'hanging': hanging,
                    'tab_pos': tab_pos,
                })
            style_node = paragraph.find('./w:pPr/w:pStyle', NS)
            style_id = style_node.get(W_VAL, '') if style_node is not None else ''
            style_name = styles.get(style_id, style_id)
            style_key = re.sub(r'[^a-z0-9]', '', style_name.lower())
            id_key = re.sub(r'[^a-z0-9]', '', style_id.lower())
            if style_key.startswith('heading') or id_key.startswith('heading'):
                headings.append(text)
            if style_key == 'imagecaption' or id_key == 'imagecaption':
                image_captions.append(text)
            if FIG_CAPTION_RE.match(text):
                formal_captions.append(text)
            if REFERENCE_RE.match(text):
                references.append(text)

        body_children = list(body)
        abstract_child_index = None
        abstract_heading = None
        for index, child in enumerate(body_children):
            if child.tag != '{%s}p' % NS['w']:
                continue
            text = _paragraph_text(child).strip()
            if text in ('摘要', 'Abstract'):
                abstract_child_index = index
                abstract_heading = text
                break
        cover_paragraph_texts = []
        if abstract_child_index is not None:
            cover_paragraph_texts = [
                _paragraph_text(child)
                for child in body_children[:abstract_child_index]
                if child.tag == '{%s}p' % NS['w']
            ]

        paragraph_sections = body.findall('./w:p/w:pPr/w:sectPr', NS)
        cover_section = (
            paragraph_sections[0] if len(paragraph_sections) == 1 else None)
        cover_header_types = []
        cover_footer_count = None
        if cover_section is not None:
            cover_header_types = [
                node.get(W_TYPE)
                for node in cover_section.findall('w:headerReference', NS)
                if node.get('{%s}id' % NS['r'])
            ]
            cover_footer_count = len(
                cover_section.findall('w:footerReference', NS))
        final_section = body.find('w:sectPr', NS)
        final_page_number_start = None
        final_footer_count = 0
        if final_section is not None:
            page_number = final_section.find('w:pgNumType', NS)
            if page_number is not None:
                final_page_number_start = page_number.get(W_START)
            final_footer_count = len(
                final_section.findall('w:footerReference', NS))

        data_sync_members = [
            name for name in archive.namelist()
            if b'DATA-SYNC' in archive.read(name)
        ]
        watermark_sha256 = (
            _sha256(archive.read('word/media/ntpu-watermark.jpeg'))
            if 'word/media/ntpu-watermark.jpeg' in archive.namelist()
            else None
        )
        ntpu_header_sha256 = (
            _sha256(archive.read('word/ntpu_header.xml'))
            if 'word/ntpu_header.xml' in archive.namelist()
            else None
        )

    return {
        'drawings': drawings,
        'equations': equations,
        'equation_xml_hashes': equation_xml_hashes,
        'equation_labels': equation_labels,
        'inline_math_xml_hashes': inline_math_xml_hashes,
        'headings': headings,
        'image_captions': image_captions,
        'formal_captions': formal_captions,
        'references': references,
        'visible': visible,
        'numbering_levels': numbering_levels,
        'list_items': list_items,
        'table_alignments': table_alignments,
        'data_sync_members': data_sync_members,
        'watermark_sha256': watermark_sha256,
        'ntpu_header_sha256': ntpu_header_sha256,
        'abstract_heading': abstract_heading,
        'cover_paragraph_texts': cover_paragraph_texts,
        'paragraph_section_count': len(paragraph_sections),
        'cover_header_types': cover_header_types,
        'cover_footer_count': cover_footer_count,
        'final_page_number_start': final_page_number_start,
        'final_footer_count': final_footer_count,
    }


def _source_facts(root, names):
    image_hashes = []
    equation_labels = []
    for name in names:
        text = (root / name).read_text(encoding='utf-8')
        for block in MATH_RE.findall(text):
            tags = TAG_RE.findall(block)
            if len(tags) != 1:
                raise VerifyError(
                    '%s: display equation has %d tag(s)' % (name, len(tags)))
            equation_labels.append(tags[0])
        for raw_path in IMAGE_RE.findall(text):
            image = root / raw_path
            if not image.is_file():
                raise VerifyError('%s: missing source image %s' % (name, raw_path))
            image_hashes.append(_sha256(image.read_bytes()))
    return {'drawings': image_hashes, 'equation_labels': equation_labels}


def _cover_paragraphs(path):
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise VerifyError('%s: corrupt zip member %s' % (path, bad_member))
        document = ET.fromstring(archive.read('word/document.xml'))
    body = document.find('w:body', NS)
    if body is None or body.find('w:sectPr', NS) is None:
        raise VerifyError('%s: canonical cover lacks body/final section' % path)
    paragraphs = [
        _paragraph_text(child)
        for child in list(body)
        if child.tag == '{%s}p' % NS['w']
    ]
    if not paragraphs or not any(paragraphs):
        raise VerifyError('%s: canonical cover has no visible text' % path)
    return paragraphs


def _require(condition, message):
    if not condition:
        raise VerifyError(message)


def _is_subsequence(needle, haystack):
    index = 0
    for item in haystack:
        if index < len(needle) and needle[index] == item:
            index += 1
    return index == len(needle)


def _abstract_blocks(facts, label):
    visible = facts['visible']
    try:
        heading = '摘要' if label == 'ZH' else 'Abstract'
        start = visible.index(heading)
        end = visible.index('1. Introduction', start + 1)
    except ValueError as exc:
        raise VerifyError('%s DOCX cannot delimit Abstract region' % label) from exc
    return visible[start + 1:end]


def _verify_list_geometry(label, facts):
    bullet_items = [
        item for item in facts['list_items'] if item['num_fmt'] == 'bullet'
    ]
    _require(bool(bullet_items), '%s DOCX contains no bullet list items' % label)
    for item in bullet_items:
        expected_left = (
            EXPECTED_LIST_LEVEL_STEP_TWIPS * item['ilvl']
            + EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS
        )
        _require(
            item['left'] == expected_left
            and item['hanging'] == EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS
            and item['tab_pos'] == expected_left,
            '%s DOCX list indent differs at numId=%s ilvl=%d: '
            'left/hanging/tab=%d/%d/%d, expected %d/%d/%d; text=%s'
            % (
                label,
                item['num_id'],
                item['ilvl'],
                item['left'],
                item['hanging'],
                item['tab_pos'],
                expected_left,
                EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS,
                expected_left,
                item['text'][:80],
            ),
        )

    for (abstract_id, ilvl), (num_fmt, left, hanging, tab_pos) in facts[
            'numbering_levels'].items():
        if num_fmt != 'bullet':
            continue
        expected_left = (
            EXPECTED_LIST_LEVEL_STEP_TWIPS * ilvl
            + EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS
        )
        _require(
            left == expected_left
            and hanging == EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS
            and tab_pos == expected_left,
            '%s DOCX numbering level %s/%d has left/hanging/tab=%d/%d/%d, '
            'expected %d/%d/%d'
            % (
                label,
                abstract_id,
                ilvl,
                left,
                hanging,
                tab_pos,
                expected_left,
                EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS,
                expected_left,
            ),
        )


def verify(source_root, zh_path, en_path, bi_path):
    zh_source = _source_facts(source_root, ZH_SOURCES)
    en_source = _source_facts(source_root, EN_SOURCES)
    cover_paragraphs = _cover_paragraphs(
        source_root / 'outputs/thesis-cover.docx')
    zh = _docx_facts(zh_path)
    en = _docx_facts(en_path)
    bi = _docx_facts(bi_path)

    _require(zh_source['drawings'] == en_source['drawings'],
             'ZH and EN Markdown reference different image byte sequences')
    _require(zh_source['equation_labels'] == en_source['equation_labels'],
             'ZH and EN Markdown have different display-equation label sequences')
    for label, facts in (('ZH', zh), ('EN', en), ('BI', bi)):
        _verify_list_geometry(label, facts)
        _require(facts['drawings'] == zh_source['drawings'],
                 '%s DOCX drawing sequence differs from the common source sequence'
                 % label)
        _require(len(facts['equations']) == len(zh_source['equation_labels']),
                 '%s DOCX display-equation count differs from source' % label)
        _require(facts['equation_labels'] == zh_source['equation_labels'],
                 '%s DOCX equation-number sequence differs from source' % label)
        _require(not facts['data_sync_members'],
                 '%s DOCX exposes DATA-SYNC in zip members: %s'
                 % (label, ', '.join(facts['data_sync_members'])))
        _require(bool(facts['table_alignments'])
                 and all(value == 'left' for value in facts['table_alignments']),
                 '%s DOCX has a table paragraph that is not left-aligned' % label)
        expected_heading = '摘要' if label == 'ZH' else 'Abstract'
        _require(facts['abstract_heading'] == expected_heading,
                 '%s DOCX body does not begin at the expected abstract heading'
                 % label)
        _require(facts['cover_paragraph_texts'] == cover_paragraphs,
                 '%s DOCX cover paragraphs differ from canonical thesis-cover.docx'
                 % label)
        _require(facts['paragraph_section_count'] == 1,
                 '%s DOCX must have exactly one cover section break' % label)
        _require('default' in facts['cover_header_types'],
                 '%s DOCX cover section has no watermark header' % label)
        _require(facts['cover_footer_count'] == 0,
                 '%s DOCX cover section unexpectedly has a page footer' % label)
        _require(facts['final_page_number_start'] == '1',
                 '%s DOCX body page numbering does not restart at 1' % label)
        _require(facts['final_footer_count'] >= 1,
                 '%s DOCX body section has no page-number footer' % label)

    _require(zh['equations'] == en['equations'] == bi['equations'],
             'DOCX display-equation text/order differs across versions')
    _require(
        zh['equation_xml_hashes']
        == en['equation_xml_hashes']
        == bi['equation_xml_hashes'],
        'DOCX display-equation OMML structure/order differs across versions')
    _require(
        _is_subsequence(
            en['inline_math_xml_hashes'], bi['inline_math_xml_hashes']),
        'English DOCX inline-math OMML is not an ordered subsequence of bilingual')
    _require(len(zh['headings']) == len(en['headings']) == len(bi['headings']),
             'DOCX heading counts differ across versions')
    _require(en['headings'] == bi['headings'],
             'EN and bilingual heading text/order differs')
    _require(en['image_captions'] == bi['image_captions'],
             'EN and bilingual ImageCaption text/order differs')
    _require(en['formal_captions'] == bi['formal_captions'],
             'EN and bilingual formal figure-caption text/order differs')
    _require(zh['references'] == en['references'] == bi['references'],
             'DOCX reference text/order differs across versions')
    _require(len(zh['list_items']) == len(en['list_items']),
             'ZH and EN DOCX list-item counts differ')
    _require(len(bi['list_items'])
             == len(zh['list_items']) + len(en['list_items']),
             'bilingual DOCX list-item count is not ZH + EN')
    reference_numbers = [
        int(REFERENCE_RE.match(text).group(1)) for text in en['references']
    ]
    _require(bool(reference_numbers), 'DOCX contains no numbered references')
    _require(reference_numbers == list(range(1, len(reference_numbers) + 1)),
             'DOCX reference numbering is not contiguous from [1]')

    zh_abstract = _abstract_blocks(zh, 'ZH')
    en_abstract = _abstract_blocks(en, 'EN')
    bi_abstract = _abstract_blocks(bi, 'BI')
    bi_chinese_abstract = [
        block for block in bi_abstract if CJK_RE.search(block)
    ]
    _require(zh_abstract == bi_chinese_abstract,
             'Chinese rendered abstract is not the Chinese subset of bilingual')
    bi_english_abstract = [
        block for block in bi_abstract if not CJK_RE.search(block)
    ]
    _require(en_abstract == bi_english_abstract,
             'English rendered abstract is not the English subset of bilingual')

    expected_watermark = _sha256(
        (source_root / 'assets/ntpu-watermark.jpeg').read_bytes())
    expected_header = _sha256(
        (source_root / 'assets/ntpu_header.xml').read_bytes())
    for label, facts in (('ZH', zh), ('EN', en), ('BI', bi)):
        _require(facts['watermark_sha256'] == expected_watermark,
                 '%s DOCX watermark differs from snapshotted asset' % label)
        _require(facts['ntpu_header_sha256'] == expected_header,
                 '%s DOCX NTPU header differs from snapshotted asset' % label)

    en_body_start = en['visible'].index('Abstract')
    en_cjk = [
        text for text in en['visible'][en_body_start:]
        if CJK_RE.search(text)
    ]
    _require(not en_cjk,
             'English DOCX body contains visible CJK paragraphs: %s'
             % ' | '.join(en_cjk[:8]))

    return {
        'drawings': len(zh['drawings']),
        'display_equations': len(zh['equations']),
        'english_inline_math_objects': len(en['inline_math_xml_hashes']),
        'headings': len(zh['headings']),
        'image_captions': len(en['image_captions']),
        'formal_figure_captions': len(en['formal_captions']),
        'references': len(en['references']),
        'list_items_zh_en_bi': '%d/%d/%d' % (
            len(zh['list_items']),
            len(en['list_items']),
            len(bi['list_items'])),
        'bullet_list_items_zh_en_bi': '%d/%d/%d' % (
            sum(item['num_fmt'] == 'bullet' for item in zh['list_items']),
            sum(item['num_fmt'] == 'bullet' for item in en['list_items']),
            sum(item['num_fmt'] == 'bullet' for item in bi['list_items'])),
        'list_marker_text_gap_twips': EXPECTED_LIST_MARKER_TEXT_GAP_TWIPS,
        'abstract_blocks_zh_en_bi': '%d/%d/%d' % (
            len(zh_abstract), len(en_abstract), len(bi_abstract)),
        'canonical_cover_paragraphs': len(cover_paragraphs),
        'cover_section_breaks_zh_en_bi': '%d/%d/%d' % (
            zh['paragraph_section_count'],
            en['paragraph_section_count'],
            bi['paragraph_section_count']),
        'english_body_visible_cjk_paragraphs': len(en_cjk),
    }


def main(argv):
    if len(argv) != 5:
        raise SystemExit(__doc__)
    result = verify(
        pathlib.Path(argv[1]).resolve(),
        pathlib.Path(argv[2]).resolve(),
        pathlib.Path(argv[3]).resolve(),
        pathlib.Path(argv[4]).resolve(),
    )
    print('DOCX STRUCTURE PARITY -> PASS')
    for key, value in result.items():
        print('%s=%s' % (key, value))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv))
    except (OSError, KeyError, ValueError, VerifyError, zipfile.BadZipFile) as exc:
        sys.stderr.write('DOCX VERIFY ERROR: %s\n' % exc)
        raise SystemExit(1)
