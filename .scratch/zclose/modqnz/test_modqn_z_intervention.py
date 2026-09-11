from __future__ import annotations

import unittest

import numpy as np

from run_modqn_z_intervention import ARMS, transform_encoded, zscore_over_users


class TransformTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = np.arange(5 * 112, dtype=np.float32).reshape(5, 112)

    def test_shapes_and_raw_recovery(self) -> None:
        expected = {
            "MODQN_RAW": 112,
            "MODQN_Z_INPLACE": 112,
            "MODQN_Z_CONCAT": 224,
            "MODQN_RAW_DUP": 224,
        }
        for arm in ARMS:
            got = transform_encoded(self.raw, arm)
            self.assertEqual(got.shape, (5, expected[arm]))
            self.assertEqual(got.dtype, np.float32)
        np.testing.assert_array_equal(
            transform_encoded(self.raw, "MODQN_Z_CONCAT")[:, :112], self.raw
        )
        duplicated = transform_encoded(self.raw, "MODQN_RAW_DUP")
        np.testing.assert_array_equal(duplicated[:, :112], duplicated[:, 112:])

    def test_zscore_over_users(self) -> None:
        got = zscore_over_users(self.raw)
        np.testing.assert_allclose(got.mean(axis=0), 0.0, atol=2e-7)
        np.testing.assert_allclose(got.std(axis=0), 1.0, atol=2e-6)

    def test_constant_features_are_zero(self) -> None:
        raw = np.ones((100, 112), dtype=np.float32)
        np.testing.assert_array_equal(zscore_over_users(raw), np.zeros_like(raw))


if __name__ == "__main__":
    unittest.main()
