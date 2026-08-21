"""W-06 / P-6 / P-7 / G-8 / G-12 — the EE closure's fail-closed semantics."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.link_budget import beam_transmit_power_w, consumed_power_w
from mcrl.errors import MCRLContractError
from mcrl.runtime.energy_efficiency import (
    additive_system_ee,
    assert_single_load_semantics,
    format_ee_comparison,
)


def _ee(rates, power, serving, loads, active):
    return additive_system_ee(
        np.array(rates, dtype=float),
        power,
        serving_beam_u=np.array(serving),
        beam_load_b=np.array(loads, dtype=float),
        beam_active_b=np.array(active, dtype=bool),
    )


# -- P-7: zero power ------------------------------------------------------


def test_P7_zero_power_with_positive_throughput_raises():
    with pytest.raises(MCRLContractError, match="zero consumed power is invalid"):
        _ee([1.0e6, 0.0], 0.0, [0, -1], [1.0, 0.0], [True, False])


def test_P7_zero_over_zero_returns_zero_and_flags_itself():
    result = _ee([0.0, 0.0], 0.0, [-1, -1], [0.0, 0.0], [False, False])
    assert result.system_ee_bits_per_j == 0.0
    assert result.zero_over_zero is True
    assert result.served == 0
    assert result.eff_beams == 0


def test_P7_no_epsilon_is_ever_added_to_the_denominator():
    """The failure P-7 exists to prevent: a floored denominator inflating EE.

    With a 1e-9 W floor, an all-dark step reporting even a whisker of
    throughput would come out at ~1e15 bits/J and look like the best step of
    the run.
    """
    result = _ee([0.0, 0.0], 0.0, [-1, -1], [0.0, 0.0], [False, False])
    assert result.system_consumed_power_w == 0.0
    assert result.system_ee_bits_per_j == 0.0
    # And a tiny-but-real power is used as-is, not rounded away.
    tiny = _ee([1.0, 0.0], 1e-9, [0, -1], [1.0, 0.0], [True, False])
    assert tiny.system_consumed_power_w == 1e-9
    assert tiny.system_ee_bits_per_j == pytest.approx(1e9)


def test_P7_zero_power_with_an_active_beam_raises():
    with pytest.raises(MCRLContractError, match="active beams is invalid"):
        _ee([0.0], 0.0, [0], [1.0], [True])


def test_negative_or_non_finite_inputs_are_refused():
    with pytest.raises(MCRLContractError, match="throughputs"):
        _ee([-1.0], 1.0, [-1], [0.0], [False])
    with pytest.raises(MCRLContractError, match="throughputs"):
        _ee([float("nan")], 1.0, [-1], [0.0], [False])
    with pytest.raises(MCRLContractError, match="consumed power"):
        _ee([0.0], -1.0, [-1], [0.0], [False])


# -- P-6 / G-12: one load semantics ---------------------------------------


def test_P6_load_must_equal_the_counts_implied_by_serving():
    serving = np.array([0, 0, 1, -1])
    good = np.array([2.0, 1.0])
    assert np.array_equal(
        assert_single_load_semantics(serving, good, np.array([True, True])), good
    )
    with pytest.raises(MCRLContractError, match="separate load semantics"):
        assert_single_load_semantics(
            serving, np.array([1.0, 1.0]), np.array([True, True])
        )


def test_P6_activation_and_positive_load_must_coincide():
    serving = np.array([0, 0])
    with pytest.raises(MCRLContractError, match="coincide"):
        assert_single_load_semantics(
            serving, np.array([2.0, 0.0]), np.array([True, True])
        )
    with pytest.raises(MCRLContractError, match="coincide"):
        assert_single_load_semantics(
            serving, np.array([2.0, 0.0]), np.array([False, False])
        )


def test_P6_a_served_user_cannot_point_at_a_dark_beam():
    # Loads agree with serving, but the beam is flagged inactive.
    with pytest.raises(MCRLContractError, match="coincide"):
        assert_single_load_semantics(
            np.array([1]), np.array([0.0, 1.0]), np.array([False, False])
        )


def test_P6_out_of_range_serving_index_is_refused():
    with pytest.raises(MCRLContractError, match="valid beam index"):
        assert_single_load_semantics(
            np.array([5]), np.array([1.0]), np.array([True])
        )


def test_unserved_users_contribute_no_load():
    loads = assert_single_load_semantics(
        np.array([-1, -1, 0]), np.array([1.0, 0.0]), np.array([True, False])
    )
    assert loads.tolist() == [1.0, 0.0]


# -- the additive decomposition -------------------------------------------


def test_the_decomposition_sums_exactly_to_the_system_value():
    rates = [1.0e7, 2.5e7, 4.0e6]
    result = _ee(rates, 3.3, [0, 0, 1], [2.0, 1.0], [True, True])
    assert sum(result.per_user_contributions_bits_per_j) == pytest.approx(
        result.system_ee_bits_per_j, rel=1e-12
    )
    assert result.system_throughput_bps == pytest.approx(sum(rates))
    assert result.served == 3
    assert result.eff_beams == 2


def test_it_plugs_into_the_real_power_model():
    loads = np.array([2.0, 1.0, 0.0])
    power = beam_transmit_power_w(loads)
    assert power[2] == 0.0, "a dark beam draws exactly zero, not a floor"
    result = _ee(
        [1e7, 1e7, 5e6],
        consumed_power_w(power),
        [0, 0, 1],
        loads,
        power > 0.0,
    )
    assert result.eff_beams == 2
    assert result.system_ee_bits_per_j > 0.0


# -- G-8: an EE comparison must carry the service rate --------------------


def test_G8_comparison_shows_served_and_eff_beams():
    dispersed = _ee([1e7, 1e7], 2.0, [0, 1], [1.0, 1.0], [True, True])
    concentrated = _ee([2e7, 0.0], 1.0, [0, -1], [1.0, 0.0], [True, False])
    rendered = format_ee_comparison(
        {"dispersed": dispersed, "concentrated": concentrated}, num_users=2
    )
    assert "served" in rendered and "eff_beams" in rendered
    for line in rendered.splitlines()[1:]:
        assert "%" in line

    # The trap G-8 exists for: the concentrated arm looks twice as efficient
    # while serving half as many users.
    assert concentrated.system_ee_bits_per_j == pytest.approx(
        2.0 * dispersed.system_ee_bits_per_j
    )
    assert concentrated.served == 1 and dispersed.served == 2


def test_G8_refuses_an_empty_or_ill_specified_comparison():
    with pytest.raises(MCRLContractError, match="nothing to compare"):
        format_ee_comparison({}, num_users=10)
    with pytest.raises(ValueError):
        format_ee_comparison(
            {"a": _ee([0.0], 0.0, [-1], [0.0], [False])}, num_users=0
        )


def test_the_result_dict_always_carries_the_G8_fields():
    payload = _ee([1e6], 1.0, [0], [1.0], [True]).as_dict()
    assert {"served", "eff_beams", "zero_over_zero"} <= set(payload)
