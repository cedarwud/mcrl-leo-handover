from __future__ import annotations

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_surplus_targets import ee_surplus_axis_targets


def test_v02_targets_reconstruct_fixed_lambda_window_surplus() -> None:
    targets = ee_surplus_axis_targets(
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        reference_system_rates_bps=np.array(
            [[3.0, 7.0], [4.0, 6.0], [5.0, 5.0]]
        ),
        reference_system_power_w=np.array([4.0, 4.0, 4.0]),
        candidate_system_rates_bps=np.array(
            [[5.0, 7.0], [5.0, 6.0], [4.0, 5.0]]
        ),
        candidate_system_power_w=np.array([5.0, 4.0, 3.0]),
        reference_isolated_rate_bps=3.0,
        reference_isolated_power_w=2.0,
        candidate_isolated_rate_bps=5.0,
        candidate_isolated_power_w=2.5,
    )

    assert targets.system_step_surplus_bits == pytest.approx((0.0, 1.0, 1.0))
    assert targets.z1_direct_surplus_bits == pytest.approx(1.0)
    assert targets.z3_spatial_surplus_bits == pytest.approx(-1.0)
    assert targets.z2_temporal_surplus_bits == pytest.approx(2.0)
    assert targets.system_window_surplus_bits == pytest.approx(2.0)
    assert targets.reconstructed_window_surplus_bits == pytest.approx(2.0)
    assert targets.identity_residual_bits == pytest.approx(0.0, abs=1e-12)


def test_all_dark_candidate_is_retained_and_signed_by_global_lambda() -> None:
    targets = ee_surplus_axis_targets(
        lambda_bits_per_j=1.5,
        interval_s=1.0,
        reference_system_rates_bps=np.array([[10.0]]),
        reference_system_power_w=np.array([5.0]),
        candidate_system_rates_bps=np.array([[0.0]]),
        candidate_system_power_w=np.array([0.0]),
        reference_isolated_rate_bps=10.0,
        reference_isolated_power_w=5.0,
        candidate_isolated_rate_bps=0.0,
        candidate_isolated_power_w=0.0,
    )

    assert targets.system_window_surplus_bits == pytest.approx(-2.5)
    assert targets.z1_direct_surplus_bits == pytest.approx(-2.5)
    assert targets.z2_temporal_surplus_bits == pytest.approx(0.0)
    assert targets.z3_spatial_surplus_bits == pytest.approx(0.0)


def test_zero_power_with_positive_rate_fails_closed() -> None:
    with pytest.raises(MCRLContractError, match="positive throughput at zero power"):
        ee_surplus_axis_targets(
            lambda_bits_per_j=1.0,
            interval_s=1.0,
            reference_system_rates_bps=np.array([[1.0]]),
            reference_system_power_w=np.array([1.0]),
            candidate_system_rates_bps=np.array([[1.0]]),
            candidate_system_power_w=np.array([0.0]),
            reference_isolated_rate_bps=1.0,
            reference_isolated_power_w=1.0,
            candidate_isolated_rate_bps=0.0,
            candidate_isolated_power_w=0.0,
        )


@pytest.mark.parametrize("multiplier", [0.0, -1.0, float("nan")])
def test_multiplier_must_be_positive_and_finite(multiplier: float) -> None:
    with pytest.raises(MCRLContractError, match="lambda_bits_per_j"):
        ee_surplus_axis_targets(
            lambda_bits_per_j=multiplier,
            interval_s=1.0,
            reference_system_rates_bps=np.array([[0.0]]),
            reference_system_power_w=np.array([0.0]),
            candidate_system_rates_bps=np.array([[0.0]]),
            candidate_system_power_w=np.array([0.0]),
            reference_isolated_rate_bps=0.0,
            reference_isolated_power_w=0.0,
            candidate_isolated_rate_bps=0.0,
            candidate_isolated_power_w=0.0,
        )
