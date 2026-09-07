"""W-180 -- bounded mechanics for the V0.21 conditional-expected ZR surface."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_expected_zr_c3 import (
    ExpectedZRC3Error,
    apply_positive_support_after_centering,
    expected_zr_from_measurements,
)
from mcrl.runtime.ee_axis_zero_marginal_c3 import build_zr_surface
from mcrl.runtime.ee_axis_zero_marginal_c3_live import ZeroMarginalC3Measurements


def _measurement(candidate_action_one_rate: float) -> ZeroMarginalC3Measurements:
    users = 2
    legal = np.zeros((users, 28), dtype=np.bool_)
    legal[:, :2] = True
    references = np.zeros(users, dtype=np.int64)
    reference = np.zeros((users, users), dtype=np.float64)
    reference[0, 1] = 10.0
    reference[1, 0] = 10.0
    candidate = np.zeros((users, 28, users), dtype=np.float64)
    candidate[0, 0] = reference[0]
    candidate[1, 0] = reference[1]
    candidate[0, 1, 1] = candidate_action_one_rate
    candidate[1, 1, 0] = 10.0
    replacement = candidate - reference[:, None, :]
    replacement[~legal] = 0.0
    compatible = np.zeros_like(legal)
    compatible[:, 0] = True
    components = [compatible.copy() for _ in range(5)]
    return ZeroMarginalC3Measurements(
        reference_actions=references,
        legal_mask=legal,
        reference_rate_bps=reference,
        candidate_rate_bps=candidate,
        removed_rate_bps=None,
        replacement_delta_bits=replacement,
        insertion_delta_bits=None,
        compatible=compatible,
        served_equal=components[0],
        active_beams_equal=components[1],
        active_satellites_equal=components[2],
        rf_power_equal=components[3],
        network_power_equal=components[4],
        reference_signature_sha256="a" * 64,
        counterfactual_evaluations=3,
        interval_s=1.0,
    )


def test_support_is_reapplied_after_reference_centering() -> None:
    centred = np.zeros((1, 28), dtype=np.float64)
    centred[0, 0] = -2.0
    centred[0, 1] = 1.0
    legal = np.zeros((1, 28), dtype=np.bool_)
    legal[0, :2] = True
    compatible = np.zeros_like(legal)
    compatible[0, 0] = True
    result = apply_positive_support_after_centering(
        centred,
        compatibility=compatible,
        legal_mask=legal,
        reference_actions=np.asarray([0], dtype=np.int64),
    )
    assert result[0, 0] == 0.0
    assert result[0, 1] == 0.0
    assert np.all(result[0, 2:] == 0.0)


def test_expectation_is_over_complete_nonlinear_draw_labels() -> None:
    high = _measurement(12.0)
    low = _measurement(6.0)
    expected = expected_zr_from_measurements([high, low], kappa_bits=1.0)
    assert expected.integration_draws == 2
    assert expected.q3_values[0, 1] == -2.0

    mean_rate_surface = build_zr_surface(
        baseline_rate_bps=high.reference_rate_bps[0],
        candidate_rate_bps=np.mean(
            np.stack(
                [high.candidate_rate_bps[0], low.candidate_rate_bps[0]], axis=0
            ),
            axis=0,
        ),
        compatibility=high.compatible[0],
        legal_mask=high.legal_mask[0],
        reference_action=0,
        interval_s=1.0,
        kappa_bits=1.0,
    )
    assert mean_rate_surface.q3_values[1] == -1.0
    assert expected.q3_values[0, 1] != mean_rate_surface.q3_values[1]


def test_draw_identity_must_remain_fixed() -> None:
    first = _measurement(12.0)
    second = _measurement(12.0)
    changed = second.compatible.copy()
    changed[0, 1] = True
    components = [changed.copy() for _ in range(5)]
    altered = ZeroMarginalC3Measurements(
        reference_actions=second.reference_actions,
        legal_mask=second.legal_mask,
        reference_rate_bps=second.reference_rate_bps,
        candidate_rate_bps=second.candidate_rate_bps,
        removed_rate_bps=None,
        replacement_delta_bits=second.replacement_delta_bits,
        insertion_delta_bits=None,
        compatible=changed,
        served_equal=components[0],
        active_beams_equal=components[1],
        active_satellites_equal=components[2],
        rf_power_equal=components[3],
        network_power_equal=components[4],
        reference_signature_sha256="b" * 64,
        counterfactual_evaluations=3,
        interval_s=1.0,
    )
    with pytest.raises(ExpectedZRC3Error, match="compatibility changed"):
        expected_zr_from_measurements([first, altered], kappa_bits=1.0)
