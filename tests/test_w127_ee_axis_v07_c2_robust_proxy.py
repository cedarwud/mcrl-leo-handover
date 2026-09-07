"""W-127 -- development-only bounded robust B2 proxy mechanics."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_v07_c2_robust_proxy import (
    B2RobustProxyContractError,
    V07_C2_B2_ROBUST_PROXY_MAX_ACTIONS,
    V07_C2_B2_ROBUST_PROXY_TOP_K,
    successor_robust_proxy_option_set_target,
)


def _target(**overrides: object):
    values: dict[str, object] = {
        "lambda_bits_per_j": 2.0,
        "interval_s": 0.5,
        "candidate_actions": (7, 2, 5),
        "candidate_action_rates_bps": (20.0, 10.0, 4.0),
        "candidate_action_full_power_w": (10.0, 5.0, 3.0),
        "candidate_action_without_focal_power_w": (8.0, 4.0, 2.0),
        "reference_actions": (3, 1),
        "reference_action_rates_bps": (12.0, 10.0),
        "reference_action_full_power_w": (10.0, 5.0),
        "reference_action_without_focal_power_w": (8.0, 4.0),
    }
    values.update(overrides)
    return successor_robust_proxy_option_set_target(**values)


def test_robust_proxy_uses_signed_action_surplus_and_mean_top_two() -> None:
    target = _target()

    # After canonicalising the panel by action index, candidate action
    # surpluses are 4, 1, and 8; reference values are 4 and 4.  The robust
    # branch values are therefore mean(8, 4) = 6 and
    # mean(4, 4) = 4, leaving a signed target of +2 bits.
    assert target.candidate_action_surplus_bits == pytest.approx((4.0, 1.0, 8.0))
    assert target.reference_action_surplus_bits == pytest.approx((4.0, 4.0))
    assert target.candidate_top_two_surplus_bits == pytest.approx((8.0, 4.0))
    assert target.reference_top_two_surplus_bits == pytest.approx((4.0, 4.0))
    assert target.candidate_robust_option_value_bits == pytest.approx(6.0)
    assert target.reference_robust_option_value_bits == pytest.approx(4.0)
    assert target.z2_robust_proxy_surplus_bits == pytest.approx(2.0)
    assert target.z2_proxy_surplus_bits == pytest.approx(2.0)
    assert target.candidate_top_two_actions == (7, 2)
    assert target.reference_top_two_actions == (1, 3)


def test_zero_outside_is_padded_and_negative_target_is_retained() -> None:
    target = _target(
        candidate_actions=(9,),
        candidate_action_rates_bps=(1.0,),
        candidate_action_full_power_w=(2.0,),
        candidate_action_without_focal_power_w=(0.0,),
        reference_actions=(4, 6),
        reference_action_rates_bps=(10.0, 4.0),
        reference_action_full_power_w=(1.0, 1.0),
        reference_action_without_focal_power_w=(0.0, 0.0),
    )

    # Candidate action surplus is -1.5, so the outside option is duplicated;
    # the reference values are 4 and 1, giving a robust value of 2.5.
    assert target.candidate_action_surplus_bits == pytest.approx((-1.5,))
    assert target.candidate_top_two_surplus_bits == (0.0, 0.0)
    assert target.candidate_top_two_actions == (-1, -1)
    assert target.candidate_robust_option_value_bits == 0.0
    assert target.reference_top_two_surplus_bits == pytest.approx((4.0, 1.0))
    assert target.reference_robust_option_value_bits == pytest.approx(2.5)
    assert target.z2_robust_proxy_surplus_bits == pytest.approx(-2.5)


def test_one_positive_opportunity_is_averaged_with_zero_outside() -> None:
    target = _target(
        candidate_actions=(2,),
        candidate_action_rates_bps=(10.0,),
        candidate_action_full_power_w=(1.0,),
        candidate_action_without_focal_power_w=(0.0,),
        reference_actions=(2,),
        reference_action_rates_bps=(0.0,),
        reference_action_full_power_w=(0.0,),
        reference_action_without_focal_power_w=(0.0,),
    )
    assert target.candidate_action_surplus_bits == pytest.approx((4.0,))
    assert target.candidate_top_two_surplus_bits == pytest.approx((4.0, 0.0))
    assert target.candidate_top_two_actions == (2, -1)
    assert target.candidate_robust_option_value_bits == pytest.approx(2.0)


def test_panel_and_receipt_are_order_invariant_with_deterministic_ties() -> None:
    ordered = _target()
    permuted = _target(
        candidate_actions=(5, 7, 2),
        candidate_action_rates_bps=(4.0, 20.0, 10.0),
        candidate_action_full_power_w=(3.0, 10.0, 5.0),
        candidate_action_without_focal_power_w=(2.0, 8.0, 4.0),
        reference_actions=(1, 3),
        reference_action_rates_bps=(10.0, 12.0),
        reference_action_full_power_w=(5.0, 10.0),
        reference_action_without_focal_power_w=(4.0, 8.0),
    )
    assert permuted == ordered

    tied = _target(
        candidate_actions=(9, 4, 1),
        candidate_action_rates_bps=(5.0, 5.0, 5.0),
        candidate_action_full_power_w=(0.0, 0.0, 0.0),
        candidate_action_without_focal_power_w=(0.0, 0.0, 0.0),
    )
    assert tied.candidate_top_two_actions == (1, 4)


@pytest.mark.parametrize(
    "change",
    [
        {"candidate_actions": (1, 1)},
        {
            "candidate_actions": tuple(range(V07_C2_B2_ROBUST_PROXY_MAX_ACTIONS + 1))
        },
        {"candidate_actions": ()},
        {"candidate_action_rates_bps": (1.0,)},
        {"candidate_action_full_power_w": (np.nan, 2.0, 3.0)},
        {"candidate_action_without_focal_power_w": (-1.0, 1.0, 1.0)},
        {"lambda_bits_per_j": 0.0},
        {"interval_s": float("inf")},
    ],
)
def test_robust_proxy_rejects_malformed_or_expanded_panels(change: dict[str, object]) -> None:
    with pytest.raises(B2RobustProxyContractError):
        _target(**change)


def test_raw_measurement_receipts_and_development_claim_ceiling_are_exposed() -> None:
    target = _target()
    assert target.candidate_actions == (2, 5, 7)
    assert target.reference_actions == (1, 3)
    assert target.candidate_action_rates_bps == pytest.approx((10.0, 4.0, 20.0))
    assert target.reference_action_rates_bps == pytest.approx((10.0, 12.0))
    assert target.candidate_action_full_power_w == pytest.approx((5.0, 3.0, 10.0))
    assert target.candidate_action_without_focal_power_w == pytest.approx((4.0, 2.0, 8.0))
    assert target.reference_action_full_power_w == pytest.approx((5.0, 10.0))
    assert target.reference_action_without_focal_power_w == pytest.approx((4.0, 8.0))
    assert target.lambda_bits_per_j == 2.0
    assert target.interval_s == 0.5
    assert target.claim_ceiling == "DEVELOPMENT_ONLY__NOT_FINAL_B2_EVIDENCE"
    assert "robust" in target.schema
    assert V07_C2_B2_ROBUST_PROXY_TOP_K == 2
