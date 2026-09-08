"""Independent synthetic radiation, sharing, interference, and solver KATs."""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcrl.physics_v025.acm import ACMRate, UncappedShannonDiagnosticRate
from mcrl.physics_v025.architectures import (
    AngleTPC_FDM,
    AngleTPC_TDM,
    FixedRF,
    Geometry,
    Link,
    RadiationConfig,
)
from mcrl.physics_v025.channel import noise_power_w
from mcrl.physics_v025.constants_v025 import POWER_CONTROL_TARGET_LINEAR
from mcrl.physics_v025.energy import HardwareInventory
from mcrl.physics_v025.resolution import resolve_configuration


def geometry(links: tuple[Link, ...], cross: np.ndarray | None = None) -> Geometry:
    matrix = np.zeros((len(links), len(links))) if cross is None else cross
    return Geometry(links, matrix)


def test_anchor_free_invariance_for_association_outage_and_dwell_histories() -> None:
    """Identical current states have identical RF/wanted fields under any irrelevant history label."""

    current = geometry((Link(7, (1001, 3), 0, 2.0),))
    config = RadiationConfig(bandwidth_hz=1.0)
    baseline = AngleTPC_TDM().radiate(config, current, "nominal")
    for ignored_history in ("association-change", "outage-reentry", "dwell-boundary"):
        del ignored_history  # There is deliberately no history argument in the V0.25 interface.
        replay = AngleTPC_TDM().radiate(config, current, "nominal")
        assert replay == baseline


def test_b02_fixed_rf_consistency_at_received_field_level() -> None:
    """Both equal-gain co-users transmit p=1.65 and receive p*h=3.30 in their slots."""

    links = (Link(0, (10, 1), 0, 2.0), Link(1, (10, 1), 0, 2.0))
    result = FixedRF().radiate(RadiationConfig(bandwidth_hz=8.0), geometry(links), "nominal")
    assert len(result.slots) == 2
    transmissions = [slot.transmissions[0] for slot in result.slots]
    assert [tx.rf_power_w for tx in transmissions] == [1.65, 1.65]
    assert [tx.wanted_w for tx in transmissions] == [3.30, 3.30]
    assert [dict(slot.beam_rf_w)[(10, 1)] for slot in result.slots] == [1.65, 1.65]


def test_tdm_union_boundaries_and_deterministic_user_order() -> None:
    """Loads 2 and 3 yield union {0,1/3,1/2,2/3,1}; users are ordered by stable ID."""

    links = (
        Link(9, (1, 1), 0, 1.0),
        Link(2, (1, 1), 0, 1.0),
        Link(8, (2, 1), 1, 1.0),
        Link(6, (2, 1), 1, 1.0),
        Link(4, (2, 1), 1, 1.0),
    )
    result = FixedRF().radiate(RadiationConfig(bandwidth_hz=1.0), geometry(links), "nominal")
    assert [(s.start_fraction, s.end_fraction) for s in result.slots] == pytest.approx(
        [(0, 1 / 3), (1 / 3, 1 / 2), (1 / 2, 2 / 3), (2 / 3, 1)]
    )
    assert [[tx.user_id for tx in slot.transmissions] for slot in result.slots] == [
        [2, 4], [2, 6], [9, 6], [9, 8]
    ]


def test_tdm_and_fdm_synthetic_noise_rate_fixture() -> None:
    """FDM: B/2=4 Hz, N=kT*4, gamma=3, so each U rate is 4*log2(4)=8 bit/s."""

    config = RadiationConfig(bandwidth_hz=8.0, target_sinr=3.0)
    n_sub = noise_power_w(4.0)
    desired_power = 0.1
    gain = 3.0 * n_sub / desired_power
    links = (Link(0, (1, 1), 0, gain), Link(1, (1, 1), 0, gain))
    radiation = AngleTPC_FDM().radiate(config, geometry(links), "nominal")
    assert [tx.bandwidth_hz for tx in radiation.slots[0].transmissions] == [4.0, 4.0]
    assert [tx.noise_w for tx in radiation.slots[0].transmissions] == pytest.approx([n_sub, n_sub])
    assert [tx.sinr for tx in radiation.slots[0].transmissions] == pytest.approx([3.0, 3.0], rel=1e-12)
    model = UncappedShannonDiagnosticRate()
    assert [model.rate_bps(tx.sinr, tx.bandwidth_hz) for tx in radiation.slots[0].transmissions] == pytest.approx([8.0, 8.0])

    n_full = noise_power_w(8.0)
    tdm_gain = 3.0 * n_full / desired_power
    tdm = AngleTPC_TDM().radiate(
        config,
        geometry((Link(0, (1, 1), 0, tdm_gain), Link(1, (1, 1), 0, tdm_gain))),
        "nominal",
    )
    average = {0: 0.0, 1: 0.0}
    for slot in tdm.slots:
        tx = slot.transmissions[0]
        average[tx.user_id] += slot.fraction * model.rate_bps(tx.sinr, tx.bandwidth_hz)
    assert average == pytest.approx({0: 8.0, 1: 8.0})


def test_interference_partition_excludes_serving_and_off_colour() -> None:
    """Wanted victim sees same-satellite 2 + other-satellite 3; off-colour 4 is excluded."""

    links = (
        Link(0, (1, 1), 0, 10.0 / 1.65),
        Link(1, (1, 2), 0, 1.0),
        Link(2, (2, 1), 0, 1.0),
        Link(3, (3, 1), 1, 1.0),
    )
    cross = np.zeros((4, 4))
    cross[0, 1] = 2.0 / 1.65
    cross[0, 2] = 3.0 / 1.65
    cross[0, 3] = 4.0 / 1.65
    result = FixedRF().radiate(RadiationConfig(bandwidth_hz=1.0), geometry(links, cross), "nominal")
    victim = next(tx for tx in result.slots[0].transmissions if tx.user_id == 0)
    assert victim.wanted_w == pytest.approx(10.0)
    assert victim.intra_interference_w == pytest.approx(2.0)
    assert victim.inter_interference_w == pytest.approx(3.0)
    assert victim.interference_w == pytest.approx(5.0)


def test_slot_consistent_interference_changes_with_tdm_aggressor() -> None:
    """Victim user 2 sees 1.65*1 in slot 1 and 1.65*2 in slot 2, never their sum."""

    links = (
        Link(0, (1, 1), 0, 1.0),
        Link(1, (1, 1), 0, 1.0),
        Link(2, (2, 1), 0, 1.0),
    )
    cross = np.zeros((3, 3))
    cross[2, 0], cross[2, 1] = 1.0, 2.0
    result = FixedRF().radiate(RadiationConfig(bandwidth_hz=1.0), geometry(links, cross), "nominal")
    interference = [next(tx for tx in slot.transmissions if tx.user_id == 2).inter_interference_w for slot in result.slots]
    assert interference == pytest.approx([1.65, 3.30])


def test_memoryless_isolated_power_halves_when_gain_doubles() -> None:
    """p=gamma*N/h: choosing h for 0.5 W then doubling h gives 0.25 W."""

    config = RadiationConfig(bandwidth_hz=1.0)
    noise = noise_power_w(1.0)
    gain = POWER_CONTROL_TARGET_LINEAR * noise / 0.5
    one = AngleTPC_TDM().radiate(config, geometry((Link(0, (1, 1), 0, gain),)), "nominal")
    two = AngleTPC_TDM().radiate(config, geometry((Link(0, (1, 1), 0, 2 * gain),)), "nominal")
    assert one.slots[0].transmissions[0].rf_power_w == pytest.approx(0.5, abs=1e-10)
    assert two.slots[0].transmissions[0].rf_power_w == pytest.approx(0.25, abs=1e-10)


def test_coupled_power_convergence_saturation_and_failure_certificate() -> None:
    """For p=.5+.1p_peer, p*=5/9; weak h caps at 1.65; one iteration remains INVALID."""

    config = RadiationConfig(bandwidth_hz=1.0)
    noise = noise_power_w(1.0)
    direct = POWER_CONTROL_TARGET_LINEAR * noise / 0.5
    coupling = 0.1 * direct / POWER_CONTROL_TARGET_LINEAR
    cross = np.array([[0.0, coupling], [coupling, 0.0]])
    links = (Link(0, (1, 1), 0, direct), Link(1, (2, 1), 0, direct))
    converged = AngleTPC_TDM().radiate(config, geometry(links, cross), "nominal")
    assert converged.certificate.status == "CONVERGED"
    assert converged.certificate.residual_w <= 1e-10
    assert [tx.rf_power_w for tx in converged.slots[0].transmissions] == pytest.approx([5 / 9, 5 / 9], abs=2e-10)

    weak = POWER_CONTROL_TARGET_LINEAR * noise / 10.0
    saturated = AngleTPC_TDM().radiate(config, geometry((Link(0, (1, 1), 0, weak),)), "nominal")
    assert saturated.slots[0].transmissions[0].rf_power_w == 1.65
    assert saturated.certificate.saturated_users == (0,)

    invalid = AngleTPC_TDM().radiate(
        RadiationConfig(bandwidth_hz=1.0, solver_iteration_cap=1),
        geometry((Link(0, (1, 1), 0, direct),)),
        "nominal",
    )
    assert invalid.certificate.status == "INVALID"
    assert not invalid.valid


def test_fdm_per_user_and_sum_caps() -> None:
    """Two users share one beam: each cap is 1.65/2=.825 and sum is 1.65 W."""

    config = RadiationConfig(bandwidth_hz=2.0)
    noise = noise_power_w(1.0)
    weak = POWER_CONTROL_TARGET_LINEAR * noise / 10.0
    links = (Link(0, (1, 1), 0, weak), Link(1, (1, 1), 0, weak))
    result = AngleTPC_FDM().radiate(config, geometry(links), "nominal")
    assert [tx.rf_power_w for tx in result.slots[0].transmissions] == [0.825, 0.825]
    assert dict(result.slots[0].beam_rf_w)[(1, 1)] == 1.65


def test_nominal_power_realised_decode_can_fail_without_pruning_attempt() -> None:
    """Realised gain collapse makes user 0 fail, but both 1.65-W beams stay in energy/interference."""

    links = (
        Link(0, (1, 1), 0, 1.0, 1e-30),
        Link(1, (2, 1), 0, 1.0, 1.0),
    )
    cross = np.zeros((2, 2))
    cross[1, 0] = 2.0
    inventory = HardwareInventory.fixed(((1, 1), (2, 1)))
    outcome = resolve_configuration(
        FixedRF(),
        RadiationConfig(bandwidth_hz=1.0),
        Geometry(links, cross),
        ACMRate(),
        inventory,
        duration_s=1.0,
    )
    assert outcome.valid and outcome.bits is not None and outcome.energy is not None
    assert outcome.bits[0] == 0.0
    assert len(outcome.radiation.slots[0].beam_rf_w) == 2
    victim = next(tx for tx in outcome.radiation.slots[0].transmissions if tx.user_id == 1)
    assert victim.inter_interference_w == pytest.approx(3.3)
    assert outcome.energy.joules > 2 * 8.0


def test_nominal_control_power_is_field_invariant_but_realised_bits_need_not_be() -> None:
    """Power uses nominal h: p=.5 in both calls; realised h/2 halves wanted/SINR and may change ACM bits."""

    config = RadiationConfig(bandwidth_hz=1.0)
    n = noise_power_w(1.0)
    nominal_gain = POWER_CONTROL_TARGET_LINEAR * n / 0.5
    current = geometry((Link(0, (1, 1), 0, nominal_gain, nominal_gain / 2),))
    nominal = AngleTPC_TDM().radiate(config, current, "nominal").slots[0].transmissions[0]
    realised = AngleTPC_TDM().radiate(config, current, "realised").slots[0].transmissions[0]
    assert nominal.rf_power_w == pytest.approx(0.5, abs=1e-10)
    assert realised.rf_power_w == nominal.rf_power_w
    assert realised.wanted_w == pytest.approx(nominal.wanted_w / 2)


def test_geometry_copies_and_freezes_caller_arrays() -> None:
    """Mutating the caller's matrix after construction cannot pollute a counterfactual tape."""

    caller = np.zeros((1, 1))
    current = Geometry((Link(0, (1, 1), 0, 1.0),), caller)
    caller[0, 0] = 99.0
    assert current.nominal_cross_gain[0, 0] == 0.0
    with pytest.raises(ValueError):
        current.nominal_cross_gain[0, 0] = 1.0
