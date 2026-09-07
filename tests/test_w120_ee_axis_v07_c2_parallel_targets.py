from __future__ import annotations

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_v07_c2_parallel_targets import (
    focal_segment_continuation_target,
    successor_option_set_target,
)


def test_b1_sums_signed_focal_successor_surplus() -> None:
    target = focal_segment_continuation_target(
        lambda_bits_per_j=2.0,
        interval_s=0.5,
        candidate_focal_rates_bps=[20.0, 4.0, 12.0],
        reference_focal_rates_bps=[10.0, 8.0, 10.0],
        candidate_full_power_w=[15.0, 14.0, 13.0],
        candidate_without_focal_power_w=[10.0, 10.0, 10.0],
        reference_full_power_w=[13.0, 11.0, 15.0],
        reference_without_focal_power_w=[10.0, 10.0, 10.0],
    )
    assert target.offset_rate_delta_bits == pytest.approx((5.0, -2.0, 1.0))
    assert target.offset_marginal_energy_delta_j == pytest.approx((1.0, 1.5, -1.0))
    assert target.offset_surplus_bits == pytest.approx((3.0, -5.0, 3.0))
    assert target.z2_focal_segment_surplus_bits == pytest.approx(1.0)
    assert target.candidate_focal_marginal_power_w == pytest.approx((5.0, 4.0, 3.0))
    assert target.reference_focal_marginal_power_w == pytest.approx((3.0, 1.0, 5.0))
    assert target.candidate_full_power_w == pytest.approx((15.0, 14.0, 13.0))
    assert target.candidate_focal_rates_bps == pytest.approx((20.0, 4.0, 12.0))
    assert target.reference_focal_rates_bps == pytest.approx((10.0, 8.0, 10.0))
    assert target.successor_offsets == (1, 2, 3)


def test_b1_equal_branches_are_exact_zero() -> None:
    values = np.asarray([1.0, 2.0, 3.0])
    target = focal_segment_continuation_target(
        lambda_bits_per_j=3.0,
        interval_s=1.0,
        candidate_focal_rates_bps=values,
        reference_focal_rates_bps=values,
        candidate_full_power_w=values,
        candidate_without_focal_power_w=np.zeros(3),
        reference_full_power_w=values,
        reference_without_focal_power_w=np.zeros(3),
    )
    assert target.z2_focal_segment_surplus_bits == 0.0
    assert target.offset_surplus_bits == (0.0, 0.0, 0.0)


def test_b1_rejects_mismatched_or_nonphysical_vectors() -> None:
    with pytest.raises(MCRLContractError, match="identical shapes"):
        focal_segment_continuation_target(
            lambda_bits_per_j=1.0,
            interval_s=1.0,
            candidate_focal_rates_bps=[1.0, 2.0],
            reference_focal_rates_bps=[1.0],
            candidate_full_power_w=[1.0, 2.0],
            candidate_without_focal_power_w=[0.0, 0.0],
            reference_full_power_w=[1.0, 2.0],
            reference_without_focal_power_w=[0.0, 0.0],
        )
    with pytest.raises(MCRLContractError, match="non-negative"):
        focal_segment_continuation_target(
            lambda_bits_per_j=1.0,
            interval_s=1.0,
            candidate_focal_rates_bps=[-1.0],
            reference_focal_rates_bps=[1.0],
            candidate_full_power_w=[1.0],
            candidate_without_focal_power_w=[0.0],
            reference_full_power_w=[1.0],
            reference_without_focal_power_w=[0.0],
        )


def test_b1_requires_exact_three_successor_offsets() -> None:
    with pytest.raises(MCRLContractError, match="exactly three"):
        focal_segment_continuation_target(
            lambda_bits_per_j=1.0,
            interval_s=1.0,
            candidate_focal_rates_bps=[1.0, 2.0],
            reference_focal_rates_bps=[1.0, 2.0],
            candidate_full_power_w=[1.0, 2.0],
            candidate_without_focal_power_w=[0.0, 0.0],
            reference_full_power_w=[1.0, 2.0],
            reference_without_focal_power_w=[0.0, 0.0],
        )


def test_b2_values_best_legal_successor_option() -> None:
    candidate_rates = np.zeros(28)
    candidate_rates[:3] = [20.0, 16.0, 100.0]
    candidate_full = np.zeros(28)
    candidate_full[:3] = [4.0, 1.0, 1.0]
    reference_rates = np.zeros(28)
    reference_rates[:3] = [15.0, 10.0, 200.0]
    reference_full = np.zeros(28)
    reference_full[:3] = [3.0, 1.0, 1.0]
    mask = np.zeros(28, dtype=np.bool_)
    mask[:2] = True
    target = successor_option_set_target(
        lambda_bits_per_j=2.0,
        interval_s=0.5,
        candidate_action_rates_bps=candidate_rates,
        candidate_action_full_power_w=candidate_full,
        candidate_action_without_focal_power_w=np.zeros(28),
        candidate_legal_mask=mask,
        reference_action_rates_bps=reference_rates,
        reference_action_full_power_w=reference_full,
        reference_action_without_focal_power_w=np.zeros(28),
        reference_legal_mask=mask,
    )
    # Candidate legal values: 6, 7. Reference legal values: 4.5, 4.
    assert target.candidate_option_value_bits == pytest.approx(7.0)
    assert target.reference_option_value_bits == pytest.approx(4.5)
    assert target.candidate_best_action == 1
    assert target.reference_best_action == 0
    assert target.z2_successor_option_set_surplus_bits == pytest.approx(2.5)
    assert target.candidate_action_marginal_power_w[:3] == pytest.approx((4.0, 1.0, 1.0))
    assert target.reference_action_full_power_w[:3] == pytest.approx((3.0, 1.0, 1.0))
    assert target.candidate_action_rates_bps[:3] == pytest.approx((20.0, 16.0, 100.0))
    assert target.candidate_legal_mask[:3] == (True, True, False)
    assert target.reference_legal_mask[:3] == (True, True, False)
    assert target.successor_offset == 1


def test_b2_noop_is_zero_floor_without_inventing_legal_action() -> None:
    candidate_rates = np.zeros(28)
    candidate_rates[:2] = [1.0, 2.0]
    candidate_full = np.zeros(28)
    candidate_full[:2] = 1.0
    reference_rates = np.zeros(28)
    reference_rates[:2] = 100.0
    reference_full = np.zeros(28)
    reference_full[:2] = 1.0
    candidate_mask = np.zeros(28, dtype=np.bool_)
    candidate_mask[:2] = True
    target = successor_option_set_target(
        lambda_bits_per_j=10.0,
        interval_s=1.0,
        candidate_action_rates_bps=candidate_rates,
        candidate_action_full_power_w=candidate_full,
        candidate_action_without_focal_power_w=np.zeros(28),
        candidate_legal_mask=candidate_mask,
        reference_action_rates_bps=reference_rates,
        reference_action_full_power_w=reference_full,
        reference_action_without_focal_power_w=np.zeros(28),
        reference_legal_mask=np.zeros(28, dtype=np.bool_),
    )
    assert target.candidate_option_value_bits == 0.0
    assert target.reference_option_value_bits == 0.0
    assert target.candidate_best_action == -1
    assert target.reference_best_action == -1
    assert target.z2_successor_option_set_surplus_bits == 0.0


def test_b2_equal_surfaces_are_exact_zero() -> None:
    rate = np.arange(28, dtype=np.float64) + 10.0
    power = np.arange(28, dtype=np.float64) + 1.0
    mask = np.zeros(28, dtype=np.bool_)
    mask[[0, 2]] = True
    target = successor_option_set_target(
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        candidate_action_rates_bps=rate,
        candidate_action_full_power_w=power,
        candidate_action_without_focal_power_w=np.zeros(28),
        candidate_legal_mask=mask,
        reference_action_rates_bps=rate,
        reference_action_full_power_w=power,
        reference_action_without_focal_power_w=np.zeros(28),
        reference_legal_mask=mask,
    )
    assert target.z2_successor_option_set_surplus_bits == 0.0


def test_b2_requires_boolean_matching_masks() -> None:
    with pytest.raises(MCRLContractError, match="Boolean vector"):
        successor_option_set_target(
            lambda_bits_per_j=1.0,
            interval_s=1.0,
            candidate_action_rates_bps=np.ones(28),
            candidate_action_full_power_w=np.ones(28),
            candidate_action_without_focal_power_w=np.zeros(28),
            candidate_legal_mask=np.ones(28, dtype=np.int64),
            reference_action_rates_bps=np.ones(28),
            reference_action_full_power_w=np.ones(28),
            reference_action_without_focal_power_w=np.zeros(28),
            reference_legal_mask=np.ones(28, dtype=np.bool_),
        )


def test_b2_requires_exact_native_28_action_surface() -> None:
    with pytest.raises(MCRLContractError, match="28"):
        successor_option_set_target(
            lambda_bits_per_j=1.0,
            interval_s=1.0,
            candidate_action_rates_bps=np.ones(2),
            candidate_action_full_power_w=np.ones(2),
            candidate_action_without_focal_power_w=np.zeros(2),
            candidate_legal_mask=np.ones(2, dtype=np.bool_),
            reference_action_rates_bps=np.ones(2),
            reference_action_full_power_w=np.ones(2),
            reference_action_without_focal_power_w=np.zeros(2),
            reference_legal_mask=np.ones(2, dtype=np.bool_),
        )
