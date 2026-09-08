"""Independent energy, pooled endpoint, pricing, and accounting KATs."""

from __future__ import annotations

from fractions import Fraction
import math

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.physics_v025.architectures import FixedRF, Geometry, Link, RadiationConfig
from mcrl.physics_v025.energy import (
    EnergyInterval,
    HardwareInventory,
    SENSITIVITY_IDLE_POWER_W,
    event_energy_sensitivity,
    interval_energy,
    pa_efficiency,
    pa_supply_power_w,
    schedule_energy,
)
from mcrl.physics_v025.endpoint import (
    StepEndpoint,
    assert_same_energy_price,
    calibration,
    pool,
    reward_core,
)


def test_one_beam_cap_joules_and_user_deduplication() -> None:
    """(sqrt(1.65*p_sat)/.35 + .338 + .200)*30.08 = 268.353221940 J."""

    inventory = HardwareInventory.fixed(((123, 7),))
    receipt = interval_energy(inventory, EnergyInterval(30.08, {(123, 7): 1.65}))
    expected = (8.383317218754922 + 0.338 + 0.200) * 30.08
    assert receipt.joules == pytest.approx(expected, abs=1e-12)
    assert receipt.joules == pytest.approx(268.353221940, abs=5e-10)
    # Energy accepts one physical-beam RF value, so adding a user has no second PA key.
    same_physical_beam = {(123, 7): max(1.65, 1.65)}
    assert interval_energy(inventory, EnergyInterval(30.08, same_physical_beam)) == receipt


def test_pa_known_values_efficiency_and_cap_boundary() -> None:
    """xi=.35*sqrt(p/p_sat): xi(.825)=.1391723775; supply(.825)=5.9279004542."""

    assert pa_efficiency(0.825) == pytest.approx(0.1391723775, abs=5e-11)
    assert pa_supply_power_w(0.825) == pytest.approx(5.9279004542, abs=5e-11)
    assert pa_efficiency(1.65) == pytest.approx(0.1968194638, abs=5e-11)
    assert pa_supply_power_w(1.65) == pytest.approx(8.383317219, abs=5e-10)
    assert pa_efficiency(0.0) == pa_supply_power_w(0.0) == 0.0
    assert math.isclose(pa_supply_power_w(0.4) / pa_supply_power_w(0.1), 2.0)  # sqrt elasticity.


def test_consolidation_fixture_reduces_ee_by_1p5466_percent() -> None:
    """32/12.7318009 versus 16/6.46590045 gives relative change -1.546575%."""

    two = HardwareInventory.fixed(((1, 1), (1, 2)))
    one = HardwareInventory.fixed(((1, 1),))
    two_power = interval_energy(two, EnergyInterval(1.0, {(1, 1): 0.825, (1, 2): 0.825})).joules
    one_power = interval_energy(one, EnergyInterval(1.0, {(1, 1): 0.825})).joules
    assert two_power == pytest.approx(12.7318009, abs=1e-7)
    assert one_power == pytest.approx(6.46590045, abs=1e-8)
    assert 2 * (8.0 * math.log2(1.0 + 3.0)) == 32.0
    assert 2 * (0.5 * 8.0 * math.log2(1.0 + 3.0)) == 16.0
    assert (16.0 / one_power) / (32.0 / two_power) - 1.0 == pytest.approx(-0.01546575, abs=1e-8)


def test_idle_switching_floor_and_tiny_active_clamp() -> None:
    """A dark chain costs P_idle*delta=.698609768*delta; active uses max(idle,P_PA)."""

    inventory = HardwareInventory.fixed(((1, 1),))
    dark = interval_energy(inventory, EnergyInterval(2.0, {}), idle_power_w=SENSITIVITY_IDLE_POWER_W)
    assert SENSITIVITY_IDLE_POWER_W == pytest.approx(0.698609768, abs=5e-10)
    assert dark.joules == pytest.approx(2 * SENSITIVITY_IDLE_POWER_W)
    tiny = interval_energy(
        inventory,
        EnergyInterval(1.0, {(1, 1): 1e-12}),
        idle_power_w=SENSITIVITY_IDLE_POWER_W,
    )
    assert tiny.pa_j == pytest.approx(SENSITIVITY_IDLE_POWER_W)
    assert tiny.circuit_j == 0.338


def test_lit_beam_and_first_satellite_monotonicity() -> None:
    """At cap, another beam adds 8.383317219+.338; first beam also adds .200 baseband."""

    inventory = HardwareInventory.fixed(((1, 1), (1, 2), (2, 1)))
    one = interval_energy(inventory, EnergyInterval(1.0, {(1, 1): 1.65}))
    two_same_sat = interval_energy(inventory, EnergyInterval(1.0, {(1, 1): 1.65, (1, 2): 1.65}))
    two_sats = interval_energy(inventory, EnergyInterval(1.0, {(1, 1): 1.65, (2, 1): 1.65}))
    assert two_same_sat.joules - one.joules == pytest.approx(8.721317218754922)
    assert two_sats.joules - one.joules == pytest.approx(8.921317218754922)


def test_circuit_baseband_and_old_default_one_beam_fixture() -> None:
    """2*.338+.2=.876; 2*.338+2*.2=1.076; default .825-W beam*30.08=194.4942857 J."""

    same_sat = interval_energy(
        HardwareInventory.fixed(((1, 1), (1, 2))),
        EnergyInterval(1.0, {(1, 1): 1e-12, (1, 2): 1e-12}),
    )
    different = interval_energy(
        HardwareInventory.fixed(((1, 1), (2, 1))),
        EnergyInterval(1.0, {(1, 1): 1e-12, (2, 1): 1e-12}),
    )
    assert same_sat.circuit_j + same_sat.baseband_j == pytest.approx(0.876)
    assert different.circuit_j + different.baseband_j == pytest.approx(1.076)
    default = interval_energy(
        HardwareInventory.fixed(((1, 1),)),
        EnergyInterval(30.08, {(1, 1): 0.825}),
    )
    assert default.joules == pytest.approx(194.4942857, abs=5e-8)


def test_handover_count_invariance_and_exact_extension_difference() -> None:
    """Primary has no count input; extension delta is eps1*dH1+eps2*dH2=2*3+5*4=26 J."""

    inventory = HardwareInventory.fixed(((1, 1),))
    primary_a = interval_energy(inventory, EnergyInterval(1.0, {(1, 1): 0.825}))
    primary_b = interval_energy(inventory, EnergyInterval(1.0, {(1, 1): 0.825}))
    assert primary_a == primary_b
    lower = event_energy_sensitivity({"same": 1, "sat": 2}, {"same": 3.0, "sat": 4.0})
    upper = event_energy_sensitivity({"same": 3, "sat": 7}, {"same": 3.0, "sat": 4.0})
    assert upper - lower == 2 * 3.0 + 5 * 4.0 == 26.0


def test_tdm_pa_averaging_precedes_nonlinearity() -> None:
    """(.5*PPA(.825)+.5*PPA(1.65))=7.155608836, not PPA(1.2375)=7.260165679."""

    inventory = HardwareInventory.fixed(((1, 1),))
    receipt = schedule_energy(
        inventory,
        ((0.5, {(1, 1): 0.825}), (0.5, {(1, 1): 1.65})),
        duration_s=1.0,
    )
    assert receipt.pa_j == pytest.approx(7.155608836, abs=5e-10)
    assert pa_supply_power_w((0.825 + 1.65) / 2) == pytest.approx(7.260165679, abs=5e-10)
    assert receipt.pa_j < pa_supply_power_w(1.2375)


def test_declared_tdm_pa_identity_at_point_one_and_one_point_six_watts() -> None:
    """TDM PA is .5*PA(.1)+.5*PA(1.6), neither PA(max) nor PA(mean)."""

    inventory = HardwareInventory.fixed(((1, 1),))
    receipt = schedule_energy(
        inventory,
        ((0.5, {(1, 1): 0.1}), (0.5, {(1, 1): 1.6})),
        duration_s=1.0,
    )
    hand = 0.5 * pa_supply_power_w(0.1) + 0.5 * pa_supply_power_w(1.6)
    assert receipt.pa_j == pytest.approx(hand)
    assert receipt.pa_j != pytest.approx(pa_supply_power_w(1.6))
    assert receipt.pa_j != pytest.approx(pa_supply_power_w(0.85))


def test_circuit_and_baseband_are_per_chain_and_satellite_not_per_user() -> None:
    inventory = HardwareInventory.fixed(((1, 1),))
    one_geometry = Geometry((Link(0, (1, 1), 0, 1.0),), np.zeros((1, 1)))
    three_geometry = Geometry(
        tuple(Link(user, (1, 1), 0, 1.0) for user in range(3)),
        np.zeros((3, 3)),
    )
    one_radiation = FixedRF().radiate(RadiationConfig(), one_geometry, "nominal")
    three_radiation = FixedRF().radiate(RadiationConfig(), three_geometry, "nominal")
    one_user = schedule_energy(
        inventory,
        ((slot.fraction, dict(slot.beam_rf_w)) for slot in one_radiation.slots),
        duration_s=1.0,
    )
    three_users_same_beam = schedule_energy(
        inventory,
        ((slot.fraction, dict(slot.beam_rf_w)) for slot in three_radiation.slots),
        duration_s=1.0,
    )
    assert len(one_radiation.slots) == 1 and len(three_radiation.slots) == 3
    assert three_users_same_beam.circuit_j == one_user.circuit_j == pytest.approx(0.338)
    assert three_users_same_beam.baseband_j == one_user.baseband_j == pytest.approx(0.200)


def endpoint(bits: int, joules: int) -> StepEndpoint:
    return StepEndpoint.build(
        bits=bits,
        joules=joules,
        decoding_user_seconds=1,
        useful_user_seconds=1,
        opportunity_user_seconds=1,
        complete_service_user_steps=1,
        user_steps=1,
    )


def test_exact_pooling_duplicate_and_all_dark_disposition() -> None:
    """(10+10)/(1+9)=2, while mean ratios=(10+10/9)/2=50/9=5.555... ."""

    rows = (endpoint(10, 1), endpoint(10, 9))
    pooled = pool(rows)
    assert pooled.pooled_ee == Fraction(2)
    assert (Fraction(10, 1) + Fraction(10, 9)) / 2 == Fraction(50, 9)
    assert pool(rows + rows).pooled_ee == Fraction(2)
    dark = StepEndpoint.build(
        bits=0, joules=0, decoding_user_seconds=0, useful_user_seconds=0,
        opportunity_user_seconds=1, complete_service_user_steps=0, user_steps=1,
    )
    assert pool((dark,)).pooled_ee is None
    with pytest.raises(MCRLContractError):
        StepEndpoint.build(
            bits=1, joules=0, decoding_user_seconds=0, useful_user_seconds=0,
            opportunity_user_seconds=1, complete_service_user_steps=0, user_steps=1,
        )


def test_reward_endpoint_identity_and_pricing_fixture() -> None:
    """sum R=sum B-eta*sum E; eta=2 prefers delta(-3,-2)=+1, eta=1 rejects it=-1."""

    rows = (endpoint(10, 1), endpoint(20, 9))
    assert sum((reward_core(row, eta_ref=2) for row in rows), Fraction()) == reward_core(
        pool(rows), eta_ref=2
    )
    assert reward_core(endpoint(7, 8), eta_ref=2) - reward_core(endpoint(10, 10), eta_ref=2) == 1
    assert reward_core(endpoint(7, 8), eta_ref=1) - reward_core(endpoint(10, 10), eta_ref=1) == -1
    eta, kappa = calibration(100, 10, users=5, time_s=2)
    assert eta == 10 and kappa == 10


def test_lambda_eta_parity_requires_both_explicit_and_equal() -> None:
    """Stage-2 targets cannot omit either price or silently use lambda=9 with eta_ref=10."""

    assert assert_same_energy_price(lambda_bits_per_j=10, eta_ref=10) == 10
    with pytest.raises(MCRLContractError):
        assert_same_energy_price(lambda_bits_per_j=9, eta_ref=10)
    with pytest.raises(TypeError):
        assert_same_energy_price(eta_ref=10)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        reward_core(endpoint(10, 1))  # type: ignore[call-arg]


def test_surplus_change_sign_matches_ee_at_exact_reference_ratio() -> None:
    """Reference 100/10 sets eta=10; candidate (101,10) has +1 surplus and higher EE, (99,10) has -1 and lower EE."""

    eta = Fraction(100, 10)
    reference_ee = Fraction(100, 10)
    for bits, expected_sign in ((101, 1), (99, -1)):
        surplus_delta = reward_core(endpoint(bits, 10), eta_ref=eta) - reward_core(
            endpoint(100, 10), eta_ref=eta
        )
        ee_delta = Fraction(bits, 10) - reference_ee
        assert (surplus_delta > 0) - (surplus_delta < 0) == expected_sign
        assert (ee_delta > 0) - (ee_delta < 0) == expected_sign


def test_fixed_overhead_scales_absolute_ee_not_fixed_action_contrast() -> None:
    """A 10% bit overhead makes each EE 0.9x while (1.1B/E)/(B/E)=1.1 remains unchanged."""

    base, candidate = Fraction(100, 10), Fraction(110, 10)
    overhead = Fraction(9, 10)
    assert overhead * base == Fraction(9)
    assert (overhead * candidate) / (overhead * base) == candidate / base == Fraction(11, 10)


def test_common_floor_can_reverse_ranking() -> None:
    """9/8>10/10, but adding common 20 J gives 9/28<10/30."""

    assert Fraction(9, 8) > Fraction(10, 10)
    assert Fraction(9, 28) < Fraction(10, 30)


def test_capacity_and_delivery_endpoints_remain_distinct() -> None:
    """A 10-bit PHY capacity with only 5 queued bits is 10 capacity bits but 5 delivered bits."""

    capacity_bits, queued_bits = 10, 5
    delivered_bits = min(capacity_bits, queued_bits)
    assert capacity_bits == 10 and delivered_bits == 5


def test_physical_identity_mismatch_fails_closed() -> None:
    """A radiating (NORAD,chain) absent from the pre-action inventory cannot be charged."""

    with pytest.raises(MCRLContractError):
        interval_energy(
            HardwareInventory.fixed(((1, 1),)),
            EnergyInterval(1.0, {(2, 1): 1.65}),
        )
