#!/usr/bin/env python3
"""Assemble/check the temporary English-only Markdown used by build_en.sh.

The reviewed EN base source intentionally retains the bilingual university
front matter and both abstracts because it also participates in the bilingual
build.  The English-only DOCX must not expose those Chinese blocks, so this tool
filters only the temporary build copy.  It never edits a thesis source.

Usage:
  assemble_english.py assemble-base INPUT OUTPUT
  assemble_english.py check FILE [FILE ...]
"""
import pathlib
import re
import sys


CJK_RE = re.compile(
    r'[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff'
    r'\uff01-\uff60\uffe0-\uffee]')


def _blocks(text):
    return [block.strip() for block in re.split(r'\n[ \t]*\n', text)
            if block.strip()]


def assemble_base(text):
    if text.count('# Abstract') != 1:
        raise ValueError('expected exactly one "# Abstract" heading')
    before_abstract, after_abstract = text.split('# Abstract', 1)
    if after_abstract.count('# 1. Introduction') != 1:
        raise ValueError('expected exactly one "# 1. Introduction" heading')
    abstract, body = after_abstract.split('# 1. Introduction', 1)

    front_blocks = [
        block.replace('Advisor：', 'Advisor: ').replace('Student：', 'Student: ')
        for block in _blocks(before_abstract)
        if not CJK_RE.search(block)
    ]
    abstract_blocks = [
        block for block in _blocks(abstract)
        if not CJK_RE.search(block)
    ]
    if not any(block.startswith('Keywords:') for block in abstract_blocks):
        raise ValueError('English Keywords block not found')

    assembled = (
        '\n\n'.join(front_blocks)
        + '\n\n# Abstract\n\n'
        + '\n\n'.join(abstract_blocks)
        + '\n\n# 1. Introduction'
        + body
    )
    assert_no_cjk(assembled, 'assembled English base')
    return assembled


def assert_no_cjk(text, label):
    match = CJK_RE.search(text)
    if match:
        line = text.count('\n', 0, match.start()) + 1
        excerpt = text[match.start():match.start() + 80].splitlines()[0]
        raise ValueError(
            '%s contains visible CJK at line %d: %s' % (label, line, excerpt))


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    command = argv[1]
    if command == 'assemble-base' and len(argv) == 4:
        src = pathlib.Path(argv[2])
        dst = pathlib.Path(argv[3])
        dst.write_text(assemble_base(src.read_text(encoding='utf-8')),
                       encoding='utf-8')
        print('assembled English-only base -> %s' % dst)
        return 0
    if command == 'check' and len(argv) >= 3:
        for raw in argv[2:]:
            path = pathlib.Path(raw)
            assert_no_cjk(path.read_text(encoding='utf-8'), str(path))
        print('English-only visible-text check PASS (%d files)'
              % (len(argv) - 2))
        return 0
    raise SystemExit(__doc__)


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv))
    except ValueError as exc:
        sys.stderr.write('ENGLISH ASSEMBLY ERROR: %s\n' % exc)
        raise SystemExit(1)
