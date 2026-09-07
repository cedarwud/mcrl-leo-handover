#!/usr/bin/env python3
"""Regression tests for the thesis cover importer."""

from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# The test is intentionally runnable as a standalone script from the repository
# root, without requiring thesis-mc to be an installed Python package.
TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import apply_cover  # noqa: E402


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}
W_P = f"{{{W}}}p"
W_BODY = f"{{{W}}}body"
W_VAL = f"{{{W}}}val"
W_TYPE = f"{{{W}}}type"
R_ID = f"{{{R}}}id"
STYLE_PREFIX = "ThesisCover_"


class ApplyCoverRegressionTests(unittest.TestCase):
    """Check the package-level invariants promised by apply_cover."""

    cover_fixture = Path(__file__).resolve().parents[1] / "outputs" / "thesis-cover.docx"
    target_fixture = Path(__file__).resolve().parents[1] / "outputs" / "mcrl-thesis-ZH.docx"

    @staticmethod
    def _paragraph_text(paragraph: ET.Element) -> str:
        return "".join(node.text or "" for node in paragraph.iter(f"{{{W}}}t"))

    @classmethod
    def _document_root(cls, package_path: Path) -> ET.Element:
        with zipfile.ZipFile(package_path) as package:
            return ET.fromstring(package.read("word/document.xml"))

    @staticmethod
    def _top_level_paragraph_texts(root: ET.Element) -> list[str]:
        body = root.find("w:body", NS)
        if body is None:
            raise AssertionError("document has no w:body")
        return [
            ApplyCoverRegressionTests._paragraph_text(child)
            for child in list(body)
            if child.tag == W_P
        ]

    def test_cover_prefix_sections_styles_and_idempotence(self) -> None:
        expected_cover_texts = self._top_level_paragraph_texts(
            self._document_root(self.cover_fixture)
        )

        with tempfile.TemporaryDirectory(prefix="test-apply-cover-") as temp_dir:
            temp_dir_path = Path(temp_dir)
            cover_path = temp_dir_path / "thesis-cover.docx"
            target_path = temp_dir_path / "mcrl-thesis-ZH.docx"
            shutil.copyfile(self.cover_fixture, cover_path)
            shutil.copyfile(self.target_fixture, target_path)

            apply_cover.apply_cover(cover_path, target_path)

            root = self._document_root(target_path)
            body = root.find("w:body", NS)
            self.assertIsNotNone(body)
            elements = list(body)
            abstract_index = next(
                index
                for index, element in enumerate(elements)
                if element.tag == W_P
                and self._paragraph_text(element).strip() == "摘要"
            )
            prefix_paragraphs = [
                element
                for element in elements[:abstract_index]
                if element.tag == W_P
            ]
            self.assertEqual(
                [self._paragraph_text(paragraph) for paragraph in prefix_paragraphs],
                expected_cover_texts,
            )

            # The imported section break belongs to the final cover paragraph;
            # the document body retains only its separate final section.
            paragraph_sections = root.findall(".//w:p/w:pPr/w:sectPr", NS)
            self.assertEqual(len(paragraph_sections), 1)
            cover_section = paragraph_sections[0]
            self.assertFalse(cover_section.findall("w:footerReference", NS))
            default_headers = [
                reference
                for reference in cover_section.findall("w:headerReference", NS)
                if reference.get(W_TYPE) == "default"
            ]
            self.assertTrue(default_headers)
            self.assertTrue(default_headers[0].get(R_ID))

            final_section = body.find("w:sectPr", NS)
            self.assertIsNotNone(final_section)
            page_number_types = final_section.findall("w:pgNumType", NS)
            self.assertEqual(len(page_number_types), 1)
            self.assertEqual(page_number_types[0].get(f"{{{W}}}start"), "1")

            with zipfile.ZipFile(target_path) as package:
                styles = ET.fromstring(package.read("word/styles.xml"))
            style_ids = {
                style.get(f"{{{W}}}styleId")
                for style in styles.findall("w:style", NS)
            }
            cover_style_ids = {
                style_id
                for style_id in style_ids
                if style_id and style_id.startswith(STYLE_PREFIX)
            }
            self.assertTrue(cover_style_ids)
            cover_style_refs = []
            for paragraph in prefix_paragraphs:
                p_style = paragraph.find("w:pPr/w:pStyle", NS)
                self.assertIsNotNone(p_style)
                style_id = p_style.get(W_VAL)
                self.assertIsNotNone(style_id)
                cover_style_refs.append(style_id)
            self.assertTrue(cover_style_refs)
            self.assertTrue(
                all(style_id.startswith(STYLE_PREFIX) for style_id in cover_style_refs)
            )
            self.assertTrue(set(cover_style_refs) <= style_ids)

            first_sha256 = hashlib.sha256(target_path.read_bytes()).digest()
            apply_cover.apply_cover(cover_path, target_path)
            second_sha256 = hashlib.sha256(target_path.read_bytes()).digest()
            self.assertEqual(second_sha256, first_sha256)


if __name__ == "__main__":
    unittest.main()
