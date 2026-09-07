#!/usr/bin/env python3
"""Replace a generated thesis cover with the canonical cover DOCX body.

Usage:
  apply_cover.py COVER.docx TARGET.docx

The target must already have passed the regular ris/bilingual post-processing.
Only the cover's body paragraphs and the styles they reference are imported.
The target package remains authoritative for the watermark, body header/footer,
equations, numbering, media, and all content beginning at 摘要/Abstract.
"""

from __future__ import annotations

import copy
import hashlib
import io
import os
import pathlib
import posixpath
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET


W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
XML = 'http://www.w3.org/XML/1998/namespace'

W_VAL = '{%s}val' % W
W_STYLE_ID = '{%s}styleId' % W
W_DEFAULT = '{%s}default' % W
W_TYPE = '{%s}type' % W
W_START = '{%s}start' % W
R_ID = '{%s}id' % R

STYLE_PREFIX = 'ThesisCover_'
ABSTRACT_HEADINGS = {'摘要', 'Abstract'}
STYLE_REFERENCE_TAGS = {
    '{%s}pStyle' % W,
    '{%s}rStyle' % W,
    '{%s}tblStyle' % W,
    '{%s}basedOn' % W,
    '{%s}next' % W,
    '{%s}link' % W,
}
UNSUPPORTED_BODY_TAGS = {
    '{%s}altChunk' % W,
    '{%s}drawing' % W,
    '{%s}footnoteReference' % W,
    '{%s}endnoteReference' % W,
    '{%s}hyperlink' % W,
    '{%s}object' % W,
}
VOLATILE_LOCAL_ATTRIBUTES = {
    'paraId',
    'textId',
    'rsidDel',
    'rsidP',
    'rsidR',
    'rsidRDefault',
    'rsidRPr',
}


class CoverError(Exception):
    """Raised when the cover cannot be imported without package ambiguity."""


def _local_name(name: str) -> str:
    return name.rsplit('}', 1)[-1]


def _register_namespaces(*documents: bytes) -> None:
    """Preserve the familiar OOXML prefixes during ElementTree writes."""
    seen = set()
    for document in documents:
        for _event, item in ET.iterparse(
                io.BytesIO(document), events=('start-ns',)):
            prefix, uri = item
            if prefix == 'xml' or (prefix, uri) in seen:
                continue
            try:
                ET.register_namespace(prefix or '', uri)
            except ValueError:
                # ElementTree reserves nsN prefixes. They are safe to regenerate.
                pass
            seen.add((prefix, uri))


def _read_package(path: pathlib.Path):
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise CoverError('%s has corrupt member %s' % (path, bad_member))
            infos = archive.infolist()
            data = {info.filename: archive.read(info.filename) for info in infos}
    except zipfile.BadZipFile as exc:
        raise CoverError('%s is not a valid DOCX package' % path) from exc
    return infos, data


def _parse(package, name: str):
    try:
        return ET.fromstring(package[name])
    except KeyError as exc:
        raise CoverError('DOCX is missing required part %s' % name) from exc
    except ET.ParseError as exc:
        raise CoverError('DOCX has invalid XML in %s' % name) from exc


def _paragraph_text(paragraph) -> str:
    return ''.join(node.text or '' for node in paragraph.iter('{%s}t' % W))


def _relationships(package, source_part: str):
    directory = posixpath.dirname(source_part)
    name = posixpath.basename(source_part)
    rels_part = posixpath.join(directory, '_rels', name + '.rels')
    root = _parse(package, rels_part)
    return {
        rel.get('Id'): rel
        for rel in root.findall('{%s}Relationship' % REL)
    }


def _resolve_target(source_part: str, target: str) -> str:
    if target.startswith('/'):
        return posixpath.normpath(target.lstrip('/'))
    return posixpath.normpath(
        posixpath.join(posixpath.dirname(source_part), target))


def _default_header(document, package, source_part='word/document.xml'):
    body = document.find('{%s}body' % W)
    if body is None:
        raise CoverError('%s has no w:body' % source_part)
    section = body.find('{%s}sectPr' % W)
    if section is None:
        raise CoverError('%s has no final w:sectPr' % source_part)
    default_ref = None
    for ref in section.findall('{%s}headerReference' % W):
        if ref.get(W_TYPE) == 'default':
            default_ref = ref
            break
    if default_ref is None or not default_ref.get(R_ID):
        raise CoverError('%s has no default header relationship' % source_part)
    rel_id = default_ref.get(R_ID)
    rel = _relationships(package, source_part).get(rel_id)
    if rel is None or not rel.get('Type', '').endswith('/header'):
        raise CoverError('%s has unresolved default header %s'
                         % (source_part, rel_id))
    if rel.get('TargetMode') == 'External':
        raise CoverError('%s uses an external default header' % source_part)
    return rel_id, _resolve_target(source_part, rel.get('Target')), section


def _header_image_hashes(package, header_part: str):
    header = _parse(package, header_part)
    rels = _relationships(package, header_part)
    used_ids = {
        value
        for node in header.iter()
        for name, value in node.attrib.items()
        if name.startswith('{%s}' % R)
    }
    image_parts = []
    for rel_id in sorted(used_ids):
        rel = rels.get(rel_id)
        if rel is None:
            raise CoverError('%s has unresolved relationship %s'
                             % (header_part, rel_id))
        if rel.get('TargetMode') == 'External':
            raise CoverError('%s uses external relationship %s'
                             % (header_part, rel_id))
        if rel.get('Type', '').endswith('/image'):
            image_parts.append(_resolve_target(header_part, rel.get('Target')))
    if not image_parts:
        raise CoverError('%s contains no embedded watermark image' % header_part)
    try:
        return [hashlib.sha256(package[name]).hexdigest()
                for name in image_parts]
    except KeyError as exc:
        raise CoverError('%s references a missing image part' % header_part) from exc


def _style_closure(cover_styles, cover_children):
    by_id = {
        style.get(W_STYLE_ID): style
        for style in cover_styles.findall('{%s}style' % W)
        if style.get(W_STYLE_ID)
    }
    required = {
        node.get(W_VAL)
        for child in cover_children
        for node in child.iter()
        if node.tag in STYLE_REFERENCE_TAGS and node.get(W_VAL)
    }
    queue = list(required)
    while queue:
        style_id = queue.pop()
        style = by_id.get(style_id)
        if style is None:
            raise CoverError('cover references missing style %s' % style_id)
        for tag in ('basedOn', 'next', 'link'):
            dependency = style.find('{%s}%s' % (W, tag))
            if (dependency is not None and dependency.get(W_VAL)
                    and dependency.get(W_VAL) not in required):
                required.add(dependency.get(W_VAL))
                queue.append(dependency.get(W_VAL))

    ordered = [
        style for style in cover_styles.findall('{%s}style' % W)
        if style.get(W_STYLE_ID) in required
    ]
    return ordered


def _style_id_map(styles):
    mapping = {}
    used = set()
    for style in styles:
        original = style.get(W_STYLE_ID)
        stem = re.sub(r'[^A-Za-z0-9_.-]+', '_', original).strip('_') or 'Style'
        candidate = STYLE_PREFIX + stem
        suffix = 2
        while candidate in used:
            candidate = '%s%s_%d' % (STYLE_PREFIX, stem, suffix)
            suffix += 1
        mapping[original] = candidate
        used.add(candidate)
    return mapping


def _remap_style_references(element, mapping) -> None:
    for node in element.iter():
        if node.tag in STYLE_REFERENCE_TAGS and node.get(W_VAL) in mapping:
            node.set(W_VAL, mapping[node.get(W_VAL)])


def _strip_nonportable_markup(element) -> None:
    for parent in list(element.iter()):
        for child in list(parent):
            if child.tag in ('{%s}bookmarkStart' % W,
                             '{%s}bookmarkEnd' % W,
                             '{%s}proofErr' % W,
                             '{%s}rsid' % W):
                parent.remove(child)
    for node in element.iter():
        for name in list(node.attrib):
            if _local_name(name) in VOLATILE_LOCAL_ATTRIBUTES:
                del node.attrib[name]


def _prepare_styles(cover_styles, target_styles, cover_children):
    styles = _style_closure(cover_styles, cover_children)
    mapping = _style_id_map(styles)

    for style in list(target_styles.findall('{%s}style' % W)):
        if style.get(W_STYLE_ID, '').startswith(STYLE_PREFIX):
            target_styles.remove(style)

    imported = []
    for source in styles:
        style = copy.deepcopy(source)
        original = style.get(W_STYLE_ID)
        style.set(W_STYLE_ID, mapping[original])
        style.attrib.pop(W_DEFAULT, None)
        name = style.find('{%s}name' % W)
        if name is not None and name.get(W_VAL):
            name.set(W_VAL, 'Thesis cover - ' + name.get(W_VAL))
        _remap_style_references(style, mapping)
        _strip_nonportable_markup(style)
        if style.find('.//{%s}numId' % W) is not None:
            raise CoverError(
                'cover style %s depends on numbering; import is unsupported'
                % original)
        target_styles.append(style)
        imported.append(style)

    for child in cover_children:
        _remap_style_references(child, mapping)
    return len(imported)


def _validate_cover_children(children) -> None:
    for child in children:
        for node in child.iter():
            if node.tag in UNSUPPORTED_BODY_TAGS:
                raise CoverError(
                    'cover body contains unsupported %s content'
                    % _local_name(node.tag))
            if node.tag == '{%s}numId' % W:
                raise CoverError('cover body contains unsupported numbering')
            for name in node.attrib:
                if name.startswith('{%s}' % R):
                    raise CoverError(
                        'cover body contains an unimported relationship')


def _cover_children_and_section(cover_document):
    body = cover_document.find('{%s}body' % W)
    if body is None:
        raise CoverError('cover has no w:body')
    section = body.find('{%s}sectPr' % W)
    if section is None:
        raise CoverError('cover has no final w:sectPr')
    children = []
    for source in list(body):
        if source is section or source.tag in (
                '{%s}bookmarkStart' % W, '{%s}bookmarkEnd' % W):
            continue
        child = copy.deepcopy(source)
        _strip_nonportable_markup(child)
        children.append(child)
    if not children or not any(_paragraph_text(child) for child in children):
        raise CoverError('cover body is empty')
    _validate_cover_children(children)
    return children, section


def _cover_section_break(cover_section, target_header_id: str):
    section = copy.deepcopy(cover_section)
    for child in list(section):
        if child.tag == '{%s}footerReference' % W:
            section.remove(child)
        elif child.tag == '{%s}headerReference' % W:
            child.set(R_ID, target_header_id)
        elif child.tag in ('{%s}type' % W, '{%s}pgNumType' % W):
            section.remove(child)
    if not section.findall('{%s}headerReference' % W):
        header = ET.Element('{%s}headerReference' % W, {
            W_TYPE: 'default',
            R_ID: target_header_id,
        })
        section.insert(0, header)
    section_type = ET.Element('{%s}type' % W, {W_VAL: 'nextPage'})
    insert_at = len(section)
    for index, child in enumerate(list(section)):
        if child.tag in ('{%s}pgSz' % W, '{%s}pgMar' % W):
            insert_at = index
            break
    section.insert(insert_at, section_type)
    return section


def _restart_body_page_numbers(final_section) -> None:
    for node in list(final_section.findall('{%s}pgNumType' % W)):
        final_section.remove(node)
    page_number = ET.Element('{%s}pgNumType' % W, {W_START: '1'})
    insert_at = len(final_section)
    for index, child in enumerate(list(final_section)):
        if child.tag in (
                '{%s}cols' % W,
                '{%s}formProt' % W,
                '{%s}vAlign' % W,
                '{%s}docGrid' % W):
            insert_at = index
            break
    final_section.insert(insert_at, page_number)


def _replace_generated_cover(target_document, cover_children,
                             cover_section_break) -> str:
    body = target_document.find('{%s}body' % W)
    if body is None:
        raise CoverError('target has no w:body')
    elements = list(body)
    heading_index = None
    heading_text = None
    for index, element in enumerate(elements):
        if element.tag != '{%s}p' % W:
            continue
        text = _paragraph_text(element).strip()
        if text in ABSTRACT_HEADINGS:
            heading_index = index
            heading_text = text
            break
    if heading_index is None:
        raise CoverError('target has no 摘要 or Abstract heading')

    keep_index = heading_index
    while (keep_index > 0 and elements[keep_index - 1].tag
           == '{%s}bookmarkStart' % W):
        keep_index -= 1
    for element in elements[:keep_index]:
        body.remove(element)

    imported = [copy.deepcopy(child) for child in cover_children]
    if imported[-1].tag != '{%s}p' % W:
        imported.append(ET.Element('{%s}p' % W))
    last_paragraph = imported[-1]
    properties = last_paragraph.find('{%s}pPr' % W)
    if properties is None:
        properties = ET.Element('{%s}pPr' % W)
        last_paragraph.insert(0, properties)
    for old_section in list(properties.findall('{%s}sectPr' % W)):
        properties.remove(old_section)
    properties.append(copy.deepcopy(cover_section_break))

    for index, element in enumerate(imported):
        body.insert(index, element)
    final_section = body.find('{%s}sectPr' % W)
    if final_section is None:
        raise CoverError('target lost its final w:sectPr')
    _restart_body_page_numbers(final_section)
    return heading_text


def apply_cover(cover_path, target_path):
    cover_path = pathlib.Path(cover_path).resolve()
    target_path = pathlib.Path(target_path).resolve()
    if cover_path == target_path:
        raise CoverError('cover and target paths must differ')
    _cover_infos, cover_package = _read_package(cover_path)
    target_infos, target_package = _read_package(target_path)

    for name in ('word/document.xml', 'word/styles.xml'):
        if name not in cover_package or name not in target_package:
            raise CoverError('both DOCX files must contain %s' % name)
    _register_namespaces(
        cover_package['word/document.xml'], cover_package['word/styles.xml'],
        target_package['word/document.xml'], target_package['word/styles.xml'])

    cover_document = _parse(cover_package, 'word/document.xml')
    target_document = _parse(target_package, 'word/document.xml')
    cover_styles = _parse(cover_package, 'word/styles.xml')
    target_styles = _parse(target_package, 'word/styles.xml')

    _cover_header_id, cover_header_part, _cover_final_section = _default_header(
        cover_document, cover_package)
    target_header_id, target_header_part, target_final_section = _default_header(
        target_document, target_package)
    if (_header_image_hashes(cover_package, cover_header_part)
            != _header_image_hashes(target_package, target_header_part)):
        raise CoverError(
            'cover watermark differs from the target thesis watermark asset')

    cover_children, cover_section = _cover_children_and_section(cover_document)
    imported_style_count = _prepare_styles(
        cover_styles, target_styles, cover_children)
    section_break = _cover_section_break(cover_section, target_header_id)
    heading = _replace_generated_cover(
        target_document, cover_children, section_break)

    # The target final section object was obtained before replacement and must
    # still be the body-level section. This assertion catches accidental moves.
    body = target_document.find('{%s}body' % W)
    if body.find('{%s}sectPr' % W) is not target_final_section:
        raise CoverError('target final section identity changed unexpectedly')

    target_package['word/document.xml'] = ET.tostring(
        target_document, encoding='utf-8', xml_declaration=True)
    target_package['word/styles.xml'] = ET.tostring(
        target_styles, encoding='utf-8', xml_declaration=True)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        dir=target_path.parent, prefix='.apply-cover-', suffix='.docx',
        delete=False)
    temporary_path = pathlib.Path(temporary.name)
    temporary.close()
    try:
        with zipfile.ZipFile(temporary_path, 'w') as output:
            for info in target_infos:
                output.writestr(info, target_package[info.filename])
        with zipfile.ZipFile(temporary_path) as check:
            bad_member = check.testzip()
            if bad_member:
                raise CoverError('rewritten DOCX has corrupt member %s' % bad_member)
        os.replace(temporary_path, target_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return {
        'cover_paragraphs': sum(
            child.tag == '{%s}p' % W for child in cover_children),
        'imported_styles': imported_style_count,
        'body_heading': heading,
    }


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    result = apply_cover(argv[1], argv[2])
    print('COVER -> APPLIED (%d paragraphs, %d styles; body starts at %s)'
          % (result['cover_paragraphs'], result['imported_styles'],
             result['body_heading']))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv))
    except (CoverError, OSError, KeyError, ValueError, ET.ParseError) as exc:
        sys.stderr.write('COVER APPLY ERROR: %s\n' % exc)
        raise SystemExit(1)
