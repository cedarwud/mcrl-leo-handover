"""W-148 -- leakage-resistant V0.14 OPS3-Q2 state boundary."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.runtime.ee_axis_ops3 import (
    OPS3_FEATURE_DIM,
    OPS3_HORIZON,
    OPS3Surface,
)
from mcrl.runtime.ee_axis_v014_q2_state import (
    EEAxisV014Q2StateError,
    V014_Q2_LOCAL_FEATURES,
    V014_Q2_STATE_DIM,
    encode_ee_axis_v014_q2_states,
)


def _surface(*, offset: float = 0.0) -> OPS3Surface:
    actions = 28
    legal = np.zeros(actions, dtype=np.bool_)
    legal[[0, 3, 7]] = True
    features = np.arange(
        actions * OPS3_FEATURE_DIM, dtype=np.float64
    ).reshape(actions, OPS3_FEATURE_DIM)
    features += offset
    features[~legal] = 0.0
    matrices = np.zeros((OPS3_HORIZON, actions), dtype=np.float64)
    return OPS3Surface(
        z2_bits=np.linspace(-2.0, 3.0, actions),
        q2_values=np.linspace(-0.5, 0.5, actions),
        features=features,
        required_power_w=matrices,
        persistence=matrices,
        rate_bps=matrices,
        marginal_power_w=matrices,
        sinr_linear=matrices,
        legal_mask=legal,
        opening_service_feasible=legal,
        reference_action=0,
        horizon=3,
    )


def test_encoder_uses_feature_major_16_by_28_layout() -> None:
    surface = _surface()
    encoded = encode_ee_axis_v014_q2_states((surface,))
    assert V014_Q2_LOCAL_FEATURES == 16
    assert V014_Q2_STATE_DIM == 448
    assert encoded.state_matrix.shape == (1, 448)
    np.testing.assert_array_equal(
        encoded.state_matrix[0], surface.features.T.reshape(-1).astype(np.float32)
    )
    np.testing.assert_array_equal(encoded.action_masks[0], surface.legal_mask)
    assert encoded.verify() == encoded.state_sha256


def test_encoder_never_uses_teacher_values_or_reference_action() -> None:
    surface = _surface()
    altered = replace(
        surface,
        z2_bits=np.linspace(1000.0, 2000.0, 28),
        q2_values=np.linspace(-100.0, 100.0, 28),
        reference_action=7,
    )
    first = encode_ee_axis_v014_q2_states((surface,))
    second = encode_ee_axis_v014_q2_states((altered,))
    np.testing.assert_array_equal(first.state_matrix, second.state_matrix)
    np.testing.assert_array_equal(first.action_masks, second.action_masks)
    assert first.state_sha256 == second.state_sha256


def test_multiple_surfaces_stack_without_writable_aliases() -> None:
    encoded = encode_ee_axis_v014_q2_states((_surface(), _surface(offset=0.5)))
    assert encoded.state_matrix.shape == (2, 448)
    assert encoded.action_masks.shape == (2, 28)
    assert not encoded.state_matrix.flags.writeable
    assert not encoded.action_masks.flags.writeable
    with pytest.raises(ValueError):
        encoded.state_matrix[0, 0] = 10.0


def test_empty_or_no_legal_surface_fails_closed() -> None:
    with pytest.raises(EEAxisV014Q2StateError, match="nonempty"):
        encode_ee_axis_v014_q2_states(())
    surface = _surface()
    no_legal = replace(
        surface,
        legal_mask=np.zeros(28, dtype=np.bool_),
        opening_service_feasible=np.zeros(28, dtype=np.bool_),
        reference_action=-1,
    )
    with pytest.raises(EEAxisV014Q2StateError, match="legal action"):
        encode_ee_axis_v014_q2_states((no_legal,))
