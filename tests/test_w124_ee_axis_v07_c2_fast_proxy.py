"""W-124 -- bounded four-action B2 direction proxy."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_v07_c2_fast_proxy import (
    B2FastProxyContractError,
    V07_C2_B2_PROXY_MAX_ACTIONS,
    select_b2_proxy_action_panel,
    successor_proxy_option_set_target,
)


def _mask() -> np.ndarray:
    mask = np.zeros(28, dtype=np.bool_)
    mask[[1, 4, 7, 13, 20]] = True
    return mask


def test_panel_is_outcome_blind_bounded_and_uses_lowest_index_ties() -> None:
    sinr = np.zeros(28, dtype=np.float64)
    sinr[[4, 7]] = 10.0
    radial = np.zeros(28, dtype=np.float64)
    radial[13] = -2.0
    radial[20] = 3.0

    panel = select_b2_proxy_action_panel(
        legal_mask=_mask(),
        reference_action=7,
        candidate_sinr=sinr,
        signed_range_rate_km_s=radial,
    )

    assert panel.actions == (7, 4, 13, 20)
    assert len(panel.actions) <= V07_C2_B2_PROXY_MAX_ACTIONS
    assert panel.claim_ceiling == "DIRECTION_SCREEN_ONLY__NOT_FINAL_B2"


def test_panel_deduplicates_when_extremes_name_the_same_action() -> None:
    mask = np.zeros(28, dtype=np.bool_)
    mask[5] = True
    panel = select_b2_proxy_action_panel(
        legal_mask=mask,
        reference_action=5,
        candidate_sinr=np.zeros(28),
        signed_range_rate_km_s=np.zeros(28),
    )
    assert panel.actions == (5,)


def test_proxy_target_reconstructs_signed_value_and_exact_zero() -> None:
    common = dict(
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        candidate_actions=(1, 4),
        candidate_action_rates_bps=(10.0, 8.0),
        candidate_action_full_power_w=(5.0, 5.0),
        candidate_action_without_focal_power_w=(3.0, 4.0),
        reference_actions=(2, 7),
        reference_action_rates_bps=(7.0, 6.0),
        reference_action_full_power_w=(5.0, 5.0),
        reference_action_without_focal_power_w=(3.0, 4.0),
    )
    target = successor_proxy_option_set_target(**common)
    assert target.candidate_option_value_bits == 6.0
    assert target.reference_option_value_bits == 4.0
    assert target.z2_proxy_surplus_bits == 2.0
    assert target.candidate_best_action == 1
    assert target.claim_ceiling == "DIRECTION_SCREEN_ONLY__NOT_FINAL_B2"

    identical = successor_proxy_option_set_target(
        **{
            **common,
            "reference_actions": common["candidate_actions"],
            "reference_action_rates_bps": common["candidate_action_rates_bps"],
            "reference_action_full_power_w": common["candidate_action_full_power_w"],
            "reference_action_without_focal_power_w": common[
                "candidate_action_without_focal_power_w"
            ],
        }
    )
    assert identical.z2_proxy_surplus_bits == 0.0


def test_proxy_keeps_zero_noop_floor_for_uniformly_harmful_panel() -> None:
    target = successor_proxy_option_set_target(
        lambda_bits_per_j=10.0,
        interval_s=1.0,
        candidate_actions=(1, 4),
        candidate_action_rates_bps=(1.0, 1.0),
        candidate_action_full_power_w=(2.0, 2.0),
        candidate_action_without_focal_power_w=(0.0, 0.0),
        reference_actions=(2,),
        reference_action_rates_bps=(1.0,),
        reference_action_full_power_w=(2.0,),
        reference_action_without_focal_power_w=(0.0,),
    )
    assert target.candidate_option_value_bits == 0.0
    assert target.reference_option_value_bits == 0.0
    assert target.candidate_best_action == -1
    assert target.reference_best_action == -1


@pytest.mark.parametrize(
    "change",
    [
        {"candidate_actions": (1, 1)},
        {"candidate_actions": (0, 1, 2, 3, 4)},
        {"candidate_action_rates_bps": (1.0,)},
        {"candidate_action_full_power_w": (np.nan, 2.0)},
    ],
)
def test_proxy_rejects_malformed_or_posthoc_expanded_panels(change: dict[str, object]) -> None:
    kwargs: dict[str, object] = {
        "lambda_bits_per_j": 2.0,
        "interval_s": 1.0,
        "candidate_actions": (1, 4),
        "candidate_action_rates_bps": (4.0, 5.0),
        "candidate_action_full_power_w": (2.0, 2.0),
        "candidate_action_without_focal_power_w": (1.0, 1.0),
        "reference_actions": (2, 7),
        "reference_action_rates_bps": (4.0, 5.0),
        "reference_action_full_power_w": (2.0, 2.0),
        "reference_action_without_focal_power_w": (1.0, 1.0),
    }
    kwargs.update(change)
    with pytest.raises(B2FastProxyContractError):
        successor_proxy_option_set_target(**kwargs)


def test_proxy_panel_rejects_illegal_reference_or_nonboolean_mask() -> None:
    with pytest.raises(B2FastProxyContractError):
        select_b2_proxy_action_panel(
            legal_mask=_mask().astype(np.int64),
            reference_action=7,
            candidate_sinr=np.zeros(28),
            signed_range_rate_km_s=np.zeros(28),
        )
    with pytest.raises(B2FastProxyContractError):
        select_b2_proxy_action_panel(
            legal_mask=_mask(),
            reference_action=0,
            candidate_sinr=np.zeros(28),
            signed_range_rate_km_s=np.zeros(28),
        )
