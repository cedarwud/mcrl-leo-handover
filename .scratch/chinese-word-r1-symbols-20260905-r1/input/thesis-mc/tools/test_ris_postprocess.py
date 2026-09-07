#!/usr/bin/env python3
"""Regression tests for thesis-specific Word postprocessing."""
import importlib.util
import pathlib
import unittest


HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'ris_postprocess', HERE / 'ris_postprocess.py')
RIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RIS)


class ListIndentTests(unittest.TestCase):
    def test_bullet_gap_halves_without_moving_nested_markers(self):
        bullet_0 = (
            '<w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/>'
            '<w:pPr><w:ind w:left="120" w:hanging="120"/></w:pPr>'
            '</w:lvl>'
        )
        bullet_1 = (
            '<w:lvl w:ilvl="1"><w:numFmt w:val="bullet"/>'
            '<w:pPr><w:ind w:left="240" w:hanging="120"/></w:pPr>'
            '</w:lvl>'
        )
        ordered = (
            '<w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/>'
            '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>'
            '</w:lvl>'
        )
        source = '<w:numbering>%s%s%s</w:numbering>' % (
            bullet_0, bullet_1, ordered)

        result = RIS.match_reference_list_indent(source)

        self.assertIn(
            '<w:tabs><w:tab w:val="num" w:pos="360"/></w:tabs>'
            '<w:ind w:left="360" w:hanging="360"/>',
            result,
        )
        self.assertIn(
            '<w:tabs><w:tab w:val="num" w:pos="480"/></w:tabs>'
            '<w:ind w:left="480" w:hanging="360"/>',
            result,
        )
        self.assertIn(ordered, result)
        self.assertEqual(RIS.match_reference_list_indent(result), result)

    def test_all_contribution_items_receive_explicit_half_default_tab_gap(self):
        def paragraph(text, num_id):
            return (
                '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/>'
                '<w:numId w:val="%s"/></w:numPr>'
                '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                '</w:pPr><w:r><w:t>%s</w:t></w:r></w:p>'
                % (num_id, text)
            )

        source = ''.join((
            paragraph('MCRL retains MODQN and changes objective one.', '1001'),
            paragraph('Second contribution.', '1001'),
            paragraph('Third contribution.', '1001'),
            paragraph('Unrelated list.', '1002'),
        ))

        result = RIS.flush_contribution_list_items(source)

        expected = (
            '<w:ind w:left="360" w:hanging="360" '
            'w:firstLine="0" w:firstLineChars="0"/>'
        )
        self.assertEqual(result.count(expected), 3)
        self.assertNotIn('w:left="0" w:hanging="0"', result)
        self.assertIn(
            '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            '</w:pPr><w:r><w:t>Unrelated list.',
            result,
        )


if __name__ == '__main__':
    unittest.main()
