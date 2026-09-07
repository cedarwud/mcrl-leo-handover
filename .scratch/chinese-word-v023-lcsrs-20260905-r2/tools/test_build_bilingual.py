#!/usr/bin/env python3
"""Focused regression tests for bilingual provenance/alignment fail-closed gates."""
import unittest

import build_bilingual as builder


class BilingualBuilderGateTests(unittest.TestCase):
    def test_inline_expression_differences_are_rejected(self):
        probes = (
            ('$x_1$', '$x_2$'),
            ('$x+y$', '$x-y$'),
            ('$x+x$', '$x$'),
            ('$x_u$', '$y_u$'),
        )
        for zh_math, en_math in probes:
            with self.subTest(zh=zh_math, en=en_math):
                with self.assertRaises(builder.AlignError):
                    builder.interleave(
                        '同一公式為 %s。' % zh_math,
                        'The same formula is %s.' % en_math,
                        label='synthetic-inline-mismatch',
                    )

    def test_abstract_block_outside_abstract_is_rejected(self):
        sample = '# Abstract\n\nApproved abstract paragraph.'
        zh = (
            '# Abstract\n\nDifferent abstract paragraph.\n\n'
            '# 1. Introduction\n\nApproved abstract paragraph.'
        )
        en = (
            '# Abstract\n\nDifferent abstract paragraph.\n\n'
            '# 1. Introduction\n\nApproved abstract paragraph.'
        )
        with self.assertRaises(builder.AlignError):
            builder._assert_abstract_provenance(sample, zh, en)


if __name__ == '__main__':
    unittest.main()
