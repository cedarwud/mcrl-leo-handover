"""W-149 -- complete legal-action OPS3-Q2 pair dataset."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.runtime.ee_axis_ops3 import OPS3_FEATURE_DIM, OPS3_HORIZON, OPS3Surface
from mcrl.runtime.ee_axis_v014_q2_pairs import (
    EEAxisV014Q2PairError,
    V014Q2LabeledSurface,
    build_ee_axis_v014_q2_pair_dataset,
)


def _surface() -> OPS3Surface:
    actions = 28
    legal = np.zeros(actions, dtype=np.bool_)
    legal[[0, 3, 7]] = True
    features = np.zeros((actions, OPS3_FEATURE_DIM), dtype=np.float64)
    features[0] = 1.0
    features[3] = 2.0
    features[7] = 3.0
    matrices = np.zeros((OPS3_HORIZON, actions), dtype=np.float64)
    z2 = np.zeros(actions, dtype=np.float64)
    z2[0], z2[3], z2[7] = -20.0, 10.0, 40.0
    q2 = (z2 - z2[3]) / 10.0
    q2[~legal] = 0.0
    return OPS3Surface(
        z2_bits=z2,
        q2_values=q2,
        features=features,
        required_power_w=matrices,
        persistence=matrices,
        rate_bps=matrices,
        marginal_power_w=matrices,
        sinr_linear=matrices,
        legal_mask=legal,
        opening_service_feasible=legal,
        reference_action=3,
        horizon=3,
    )


def test_builder_emits_every_nonreference_legal_action_and_all_signs() -> None:
    labeled = V014Q2LabeledSurface(
        surface=_surface(), source_seed=12, anchor_sha256="a" * 64
    )
    dataset = build_ee_axis_v014_q2_pair_dataset((labeled,))
    batch = dataset.batch
    assert batch.reference_actions.tolist() == [3, 3]
    assert batch.candidate_actions.tolist() == [0, 7]
    assert batch.target_surplus_bits.tolist() == [-30.0, 30.0]
    assert dataset.source_seeds.tolist() == [12, 12]
    assert dataset.anchor_sha256s.tolist() == ["a" * 64, "a" * 64]
    np.testing.assert_array_equal(batch.states[0], batch.states[1])
    np.testing.assert_array_equal(batch.action_masks[0], _surface().legal_mask)
    dataset.verify()


def test_builder_uses_z2_difference_not_precentered_q2_payload() -> None:
    surface = _surface()
    corrupted_q2 = replace(surface, q2_values=np.full(28, 999.0))
    dataset = build_ee_axis_v014_q2_pair_dataset(
        (V014Q2LabeledSurface(corrupted_q2, 12, "b" * 64),)
    )
    assert dataset.batch.target_surplus_bits.tolist() == [-30.0, 30.0]


def test_builder_rejects_bad_reference_or_empty_comparisons() -> None:
    surface = _surface()
    bad = replace(surface, reference_action=1)
    with pytest.raises(EEAxisV014Q2PairError, match="reference"):
        build_ee_axis_v014_q2_pair_dataset(
            (V014Q2LabeledSurface(bad, 12, "c" * 64),)
        )

    only_reference = replace(
        surface,
        legal_mask=np.asarray([index == 3 for index in range(28)], dtype=np.bool_),
        opening_service_feasible=np.asarray(
            [index == 3 for index in range(28)], dtype=np.bool_
        ),
    )
    with pytest.raises(EEAxisV014Q2PairError, match="comparison"):
        build_ee_axis_v014_q2_pair_dataset(
            (V014Q2LabeledSurface(only_reference, 12, "d" * 64),)
        )
