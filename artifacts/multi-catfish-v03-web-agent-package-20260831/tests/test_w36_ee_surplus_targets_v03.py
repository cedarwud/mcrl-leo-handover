from __future__ import annotations

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_surplus_targets import ee_surplus_axis_targets_v03


def _targets(*, multiplier: float = 2.0):
    return ee_surplus_axis_targets_v03(
        lambda_bits_per_j=multiplier,
        interval_s=1.0,
        focal_user=0,
        reference_system_rates_bps=np.array(
            [[3.0, 7.0], [4.0, 6.0], [5.0, 5.0]]
        ),
        reference_system_power_w=np.array([4.0, 4.0, 4.0]),
        candidate_system_rates_bps=np.array(
            [[5.0, 8.0], [5.0, 6.0], [4.0, 5.0]]
        ),
        candidate_system_power_w=np.array([5.0, 4.0, 3.0]),
    )


def test_v03_reconstructs_fixed_lambda_window_surplus() -> None:
    targets = _targets()

    assert targets.system_step_surplus_bits == pytest.approx((1.0, 1.0, 1.0))
    assert targets.z1_focal_surplus_bits == pytest.approx(0.0)
    assert targets.z3_nonfocal_externality_bits == pytest.approx(1.0)
    assert targets.z2_temporal_surplus_bits == pytest.approx(2.0)
    assert targets.system_window_surplus_bits == pytest.approx(3.0)
    assert targets.identity_residual_bits == pytest.approx(0.0, abs=1e-12)


def test_p1_no_nonfocal_interaction_means_zero_externality() -> None:
    targets = ee_surplus_axis_targets_v03(
        lambda_bits_per_j=3.0,
        interval_s=2.0,
        focal_user=1,
        reference_system_rates_bps=np.array([[4.0, 5.0, 6.0]]),
        reference_system_power_w=np.array([7.0]),
        candidate_system_rates_bps=np.array([[4.0, 9.0, 6.0]]),
        candidate_system_power_w=np.array([8.0]),
    )

    assert targets.z3_nonfocal_externality_bits == 0.0


def test_p2_identical_branches_mean_all_targets_zero() -> None:
    rates = np.array([[4.0, 5.0], [7.0, 8.0]])
    power = np.array([3.0, 4.0])
    targets = ee_surplus_axis_targets_v03(
        lambda_bits_per_j=3.0,
        interval_s=2.0,
        focal_user=1,
        reference_system_rates_bps=rates,
        reference_system_power_w=power,
        candidate_system_rates_bps=rates.copy(),
        candidate_system_power_w=power.copy(),
    )

    assert targets.z1_focal_surplus_bits == 0.0
    assert targets.z2_temporal_surplus_bits == 0.0
    assert targets.z3_nonfocal_externality_bits == 0.0
    assert targets.system_window_surplus_bits == 0.0


def test_p4_externality_is_invariant_to_lambda() -> None:
    low = _targets(multiplier=1.0)
    high = _targets(multiplier=1.0e9)

    assert low.z3_nonfocal_externality_bits == high.z3_nonfocal_externality_bits
    assert low.z1_focal_surplus_bits != high.z1_focal_surplus_bits


def test_large_cancelling_terms_do_not_false_fail_identity() -> None:
    targets = ee_surplus_axis_targets_v03(
        lambda_bits_per_j=1.0e8,
        interval_s=30.0,
        focal_user=0,
        reference_system_rates_bps=np.array([[1.0e10, 2.0e10], [3.0e10, 4.0e10]]),
        reference_system_power_w=np.array([100.0, 100.0]),
        candidate_system_rates_bps=np.array(
            [[1.0e10 + 1.0, 2.0e10 - 1.0], [3.0e10 + 1.0, 4.0e10]]
        ),
        candidate_system_power_w=np.array([100.0 + 1.0e-7, 100.0]),
    )

    assert abs(targets.identity_residual_bits) <= 1e-3


def test_unilateral_effect_survives_large_common_rate_offset() -> None:
    common = 8.0e15
    reference = np.array([[common, common, common]])
    candidate = reference.copy()
    candidate[0, 0] += 10.0
    candidate[0, 1] -= 4.0
    targets = ee_surplus_axis_targets_v03(
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        focal_user=0,
        reference_system_rates_bps=reference,
        reference_system_power_w=np.array([5.0]),
        candidate_system_rates_bps=candidate,
        candidate_system_power_w=np.array([6.0]),
    )

    # At this magnitude float64 quantizes the requested +10/-4 to +10/-4
    # representable deltas; the accounting must use those matched deltas rather
    # than subtract two independently rounded system totals.
    assert targets.z1_focal_surplus_bits + targets.z3_nonfocal_externality_bits == pytest.approx(
        targets.system_window_surplus_bits
    )


@pytest.mark.parametrize("focal", [-1, 2, 1.5])
def test_focal_user_must_be_valid_integer_index(focal: float) -> None:
    with pytest.raises(MCRLContractError, match="focal_user"):
        ee_surplus_axis_targets_v03(
            lambda_bits_per_j=1.0,
            interval_s=1.0,
            focal_user=focal,  # type: ignore[arg-type]
            reference_system_rates_bps=np.array([[1.0, 2.0]]),
            reference_system_power_w=np.array([1.0]),
            candidate_system_rates_bps=np.array([[1.0, 2.0]]),
            candidate_system_power_w=np.array([1.0]),
        )
