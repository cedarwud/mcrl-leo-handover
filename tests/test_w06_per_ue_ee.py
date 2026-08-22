"""W-06 — the per-link angle-aware EE closure, the ``r1`` objective.

Two properties carry the weight: the power share is piecewise (so it sums to
exactly 1 with no epsilon anywhere), and the ``eta`` denominator is
fail-closed rather than floored (P-7).
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.energy_efficiency import (
    EPSILON_NUM,
    per_ue_energy_efficiency,
)


def _closure(rates, admitted, p_req, p_max, p_tot, p0_w=0.0):
    return per_ue_energy_efficiency(
        rates_nmk=np.array(rates, dtype=float),
        admitted_link_nmk=np.array(admitted, dtype=bool),
        p_req_nmk=np.array(p_req, dtype=float),
        p_max_nm=np.array(p_max, dtype=float),
        p_tot_nm=np.array(p_tot, dtype=float),
        p0_w=p0_w,
    )


# -- the power share -------------------------------------------------------


def test_admitted_shares_on_a_beam_sum_to_exactly_one():
    """The piecewise form's whole point: exactly 1, not 1 - O(eps)."""
    result = _closure(
        [1e7, 2e7, 3e7], [True, True, True], [0.2, 0.5, 0.3], [1.65], [1.0]
    )
    assert float(result.alpha.sum()) == 1.0
    assert result.alpha.tolist() == [0.2, 0.5, 0.3]


def test_a_beam_with_no_admitted_link_gives_zero_shares_not_a_zero_division():
    """The unsoundness S11a M-10 fixed: eq. (3.27) evaluates κ on every beam."""
    result = _closure(
        [0.0, 0.0], [False, False], [0.4, 0.6], [1.65], [1.0]
    )
    assert result.alpha.tolist() == [0.0, 0.0]
    assert np.all(np.isfinite(result.alpha))
    assert result.eta.tolist() == [0.0, 0.0]


def test_unadmitted_links_take_no_share_from_the_admitted_ones():
    result = _closure(
        [1e7, 0.0], [True, False], [0.4, 0.6], [1.65], [1.0]
    )
    assert result.alpha.tolist() == [1.0, 0.0]
    assert float(result.alpha[result.alpha > 0].sum()) == 1.0


def test_the_share_uses_the_capped_request():
    """``q = min(p_req, P_max)`` — a link cannot claim more than the ceiling."""
    result = _closure(
        [1e7, 1e7], [True, True], [10.0, 1.65], [1.65], [1.0]
    )
    assert result.alpha.tolist() == [0.5, 0.5]


def test_shares_are_proportional_to_the_capped_requests():
    result = _closure(
        [1e7] * 4, [True] * 4, [0.1, 0.2, 0.3, 0.4], [1.65], [1.0]
    )
    assert np.allclose(result.alpha, [0.1, 0.2, 0.3, 0.4])


# -- the eta denominator is fail-closed, not floored ----------------------


def test_positive_rate_on_zero_attributed_power_raises():
    """The P-7 failure mode: a floor would return rate x 1e12, silently."""
    with pytest.raises(MCRLContractError, match="zero attributed power"):
        _closure([1e7], [True], [0.0], [1.65], [1.0])


def test_zero_rate_on_zero_power_is_a_flagged_zero_over_zero():
    result = _closure([0.0], [True], [0.0], [1.65], [1.0])
    assert result.eta.tolist() == [0.0]
    assert result.zero_over_zero.tolist() == [True]
    assert result.any_zero_over_zero


def test_no_epsilon_is_ever_used_as_a_denominator():
    """The constant is kept for provenance and must stay unused."""
    import inspect

    from mcrl.runtime import energy_efficiency

    source = inspect.getsource(energy_efficiency.per_ue_energy_efficiency)
    assert "EPSILON_NUM" not in source
    assert EPSILON_NUM == 1e-12  # provenance value, referenced nowhere else

    # And the quantitative reason: flooring would invent 19 orders of EE.
    inflated = 1e7 / EPSILON_NUM
    assert inflated > 1e18


def test_a_reachable_link_is_unaffected_by_the_change():
    """Every case with real power behaves exactly as the source did."""
    result = _closure([1e7], [True], [0.5], [1.65], [1.0])
    assert float(result.eta[0]) == pytest.approx(1e7 / 1.0)
    assert not result.any_zero_over_zero


# -- the full-cost attribution --------------------------------------------


def test_eta_is_rate_over_the_links_own_share_of_beam_power():
    result = _closure(
        [1e7, 3e7], [True, True], [0.25, 0.75], [1.65], [2.0]
    )
    assert np.allclose(result.alpha, [0.25, 0.75])
    assert float(result.eta[0]) == pytest.approx(1e7 / (0.25 * 2.0))
    assert float(result.eta[1]) == pytest.approx(3e7 / (0.75 * 2.0))


def test_a_fixed_overhead_lowers_every_links_efficiency():
    without = _closure([1e7], [True], [0.5], [1.65], [1.0])
    with_overhead = _closure([1e7], [True], [0.5], [1.65], [1.0], p0_w=0.5)
    assert float(with_overhead.eta[0]) < float(without.eta[0])
    assert float(with_overhead.eta[0]) == pytest.approx(1e7 / 1.5)


def test_a_single_link_call_matches_the_trainer_usage():
    """The shape ``modqn.reward_vector_from_step_result`` passes."""
    result = per_ue_energy_efficiency(
        rates_nmk=np.array([5.0e7]),
        admitted_link_nmk=np.array([True]),
        p_req_nmk=np.array([0.8]),
        p_max_nm=np.array([1.65]),
        p_tot_nm=np.array([0.8]),
    )
    assert result.eta.shape == (1,)
    assert float(result.eta[0]) == pytest.approx(5.0e7 / 0.8)


def test_it_broadcasts_a_per_beam_ceiling_over_the_ue_axis():
    result = per_ue_energy_efficiency(
        rates_nmk=np.array([[1e7, 1e7], [2e7, 0.0]]),
        admitted_link_nmk=np.array([[True, True], [True, False]]),
        p_req_nmk=np.array([[0.5, 0.5], [1.0, 0.4]]),
        p_max_nm=np.array([1.65, 1.65]),
        p_tot_nm=np.array([1.0, 2.0]),
    )
    assert result.alpha.shape == (2, 2)
    assert np.allclose(result.alpha[0], [0.5, 0.5])
    assert np.allclose(result.alpha[1], [1.0, 0.0])


# -- validation ------------------------------------------------------------


def test_shape_disagreement_fails_loud():
    with pytest.raises(MCRLContractError, match="share a shape"):
        _closure([1e7, 1e7], [True], [0.5], [1.65], [1.0])


def test_negative_and_non_finite_inputs_fail_loud():
    with pytest.raises(MCRLContractError, match="non-negative"):
        _closure([-1.0], [True], [0.5], [1.65], [1.0])
    with pytest.raises(MCRLContractError, match="finite"):
        _closure([float("nan")], [True], [0.5], [1.65], [1.0])
    with pytest.raises(MCRLContractError, match="non-negative"):
        _closure([1e7], [True], [0.5], [-1.0], [1.0])
    with pytest.raises(ValueError, match="p0_w"):
        _closure([1e7], [True], [0.5], [1.65], [1.0], p0_w=-1.0)


def test_a_non_broadcastable_beam_quantity_fails_loud():
    with pytest.raises(MCRLContractError, match="does not broadcast"):
        per_ue_energy_efficiency(
            rates_nmk=np.array([1e7, 1e7, 1e7]),
            admitted_link_nmk=np.array([True, True, True]),
            p_req_nmk=np.array([0.5, 0.5, 0.5]),
            p_max_nm=np.array([1.0, 2.0]),
            p_tot_nm=np.array([1.0]),
        )


def test_the_two_closures_share_one_zero_power_policy():
    """P-7 must not mean one thing per link and another per system."""
    import inspect

    from mcrl.runtime import energy_efficiency

    per_link = inspect.getsource(energy_efficiency.per_ue_energy_efficiency)
    system = inspect.getsource(energy_efficiency.additive_system_ee)
    for source in (per_link, system):
        assert "zero_over_zero" in source
        assert "raise MCRLContractError" in source
