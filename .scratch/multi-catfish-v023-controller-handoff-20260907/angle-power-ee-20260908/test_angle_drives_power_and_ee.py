"""Sealed KAT for the owner's requirement 1: angle drives power and EE.

The geometry is deliberately synthetic and history-free.  Slant range and
elevation stay fixed while only transmit off-axis angle changes.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pytest

from mcrl.physics_v025.acm import ACMRate, select_mode
from mcrl.physics_v025.architectures import (
    AngleRateTPC_TDM,
    FixedRF,
    Geometry,
    Link,
    RadiationConfig,
)
from mcrl.physics_v025.channel import (
    free_space_path_gain,
    scintillation_loss_db,
    transmit_gain_linear,
)
from mcrl.physics_v025.constants_v025 import (
    BEAM_RF_CAP_W,
    DECISION_INTERVAL_S,
    RX_GAIN_MAX_DBI,
    TX_FULL_HPBW_DEG,
    ZENITH_GASEOUS_LOSS_DB,
)
from mcrl.physics_v025.energy import HardwareInventory
from mcrl.physics_v025.resolution import resolve_configuration


SLANT_KM = 2_000.0
ELEVATION_DEG = 10.0
PATTERN_EDGE_DEG = TX_FULL_HPBW_DEG / 2.0
BEAM = (90_001, 0)
CAP_HIT_DEG_N4 = 0.8530697951488015


@dataclass(frozen=True)
class SweepPoint:
    transmit_gain: float
    rf_power_w: float
    mode: str
    bits_per_user: float
    total_bits: float
    energy_j: float
    ee_bit_per_j: float


def _direct_gain(theta_deg: float) -> float:
    # h(theta) = G_T(theta) * (lambda/(4*pi*d))^2
    #            * 10^(-(0.25/sin(10 deg) + 1.08)/10) * 10^(35/10).
    # At 2,000 km and 10 deg the angle-independent product is
    # 3.557146035714657e-19 * 10^(-2.519692620785909/10) * 3162.27766016838
    # = 6.296981727548675e-16, hence h(0) = 1.259396345509735e-12.
    gaseous_loss_db = ZENITH_GASEOUS_LOSS_DB / math.sin(
        math.radians(ELEVATION_DEG)
    )
    angle_independent = (
        float(free_space_path_gain(SLANT_KM))
        * 10.0
        ** (-(gaseous_loss_db + float(scintillation_loss_db(ELEVATION_DEG))) / 10.0)
        * 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
    )
    return float(transmit_gain_linear(theta_deg)) * angle_independent


def _point(theta_deg: float, occupancy: int, *, fixed_rf: bool = False) -> SweepPoint:
    nominal_gain = _direct_gain(theta_deg)
    # The nominal controller lands exactly on an ACM threshold.  One ULP of
    # realised-field clearance prevents the direction of the final IEEE-754
    # divide/multiply rounding from deciding whether equality decodes.  This
    # is <2.3e-16 relative and changes neither printed physics value nor power.
    realised_gain = math.nextafter(nominal_gain, math.inf)
    links = tuple(
        Link(user, BEAM, 0, nominal_gain, realised_gain)
        for user in range(occupancy)
    )
    geometry = Geometry(links, np.zeros((occupancy, occupancy), dtype=np.float64))
    result = resolve_configuration(
        FixedRF() if fixed_rf else AngleRateTPC_TDM(),
        RadiationConfig(),
        geometry,
        ACMRate(),
        HardwareInventory.fixed((BEAM,)),
        duration_s=DECISION_INTERVAL_S,
        field="realised",
    )
    assert result.valid and result.bits is not None and result.energy is not None
    transmissions = [
        tx for slot in result.radiation.slots for tx in slot.transmissions
    ]
    modes = {select_mode(tx.sinr).name for tx in transmissions}  # type: ignore[union-attr]
    powers = {tx.rf_power_w for tx in transmissions}
    assert len(modes) == len(powers) == 1
    total_bits = math.fsum(result.bits.values())
    return SweepPoint(
        float(transmit_gain_linear(theta_deg)),
        powers.pop(),
        modes.pop(),
        result.bits[0],
        total_bits,
        result.energy.joules,
        total_bits / result.energy.joules,
    )


# Independent decimal oracles.  Examples of the hand arithmetic:
#
# N = k*T*(500e6/3) = 5.575393264517296e-13 W.
# Gamma_r(1,2,4) = (0.717494793565848, 1.150320220502404,
#                    3.117588235600445).
# At boresight, p_4 = Gamma_r(4)*N/h(0)
#                       = 3.117588235600445*5.575393264517296e-13
#                         / 1.259396345509735e-12
#                       = 1.380167610639674 W.
# At the edge G_T=1000.000816665574, so p_1=0.635274572094577 W.
# B_1 = 30.08*(500e6/3)*(0.490243/1.20)
#     = 2,048,126,311.111111 bit.
# E(p_1(0)) = 30.08*(sqrt(0.317637545450725*5.217758139277826)/.35
#                    + .338 + .200)
#             = 126.824443279015 J.
ORACLES = {
    (0.0, 1, False): SweepPoint(
        2000.0,
        0.317637545450725,
        "QPSK 1/4",
        2_048_126_311.111111,
        2_048_126_311.111111,
        126.824443279015,
        16_149_302.5962292,
    ),
    (0.0, 2, False): SweepPoint(
        2000.0,
        0.509250930598129,
        "QPSK 2/5",
        1_648_993_955.5555556,
        3_297_987_911.111111,
        156.276439932170,
        21_103_551.5816879,
    ),
    (0.0, 4, False): SweepPoint(
        2000.0,
        1.380167610639674,
        "QPSK 3/4",
        1_553_582_911.1111114,
        6_214_331_644.444446,
        246.814036415551,
        25_178_193.8122094,
    ),
    (0.0, 1, True): SweepPoint(
        2000.0,
        1.65,
        "QPSK 4/5",
        6_630_952_177.777779,
        6_630_952_177.777779,
        268.353221940148,
        24_709_791.5569529,
    ),
    (1.66, 1, False): SweepPoint(
        1000.000816665574,
        0.635274572094577,
        "QPSK 1/4",
        2_048_126_311.111111,
        2_048_126_311.111111,
        172.653549185147,
        11_862_636.5966840,
    ),
    (1.66, 2, False): SweepPoint(
        1000.000816665574,
        1.018501029421530,
        "QPSK 2/5",
        1_648_993_955.5555556,
        3_297_987_911.111111,
        214.304945283380,
        15_389_229.1507791,
    ),
    (1.66, 4, False): SweepPoint(
        1000.000816665574,
        1.65,
        "QPSK 1/2",
        1_032_807_244.4444445,
        4_131_228_977.777778,
        268.353221940148,
        15_394_743.3457653,
    ),
    (1.66, 1, True): SweepPoint(
        1000.000816665574,
        1.65,
        "QPSK 1/2",
        4_131_228_977.777778,
        4_131_228_977.777778,
        268.353221940148,
        15_394_743.3457653,
    ),
}


@pytest.mark.parametrize("key, expected", ORACLES.items())
def test_hand_computed_angle_power_bits_energy_and_ee_oracles(
    key: tuple[float, int, bool], expected: SweepPoint
) -> None:
    angle, occupancy, fixed_rf = key
    actual = _point(angle, occupancy, fixed_rf=fixed_rf)
    assert actual.transmit_gain == pytest.approx(expected.transmit_gain, rel=2e-10)
    assert actual.rf_power_w == pytest.approx(expected.rf_power_w, rel=2e-12)
    assert actual.mode == expected.mode
    assert actual.bits_per_user == pytest.approx(expected.bits_per_user, rel=2e-12)
    assert actual.total_bits == pytest.approx(expected.total_bits, rel=2e-12)
    assert actual.energy_j == pytest.approx(expected.energy_j, rel=2e-12)
    assert actual.ee_bit_per_j == pytest.approx(expected.ee_bit_per_j, rel=2e-12)


def test_a_r0_power_is_monotone_until_the_cap_and_cap_angle_is_sealed() -> None:
    angles = np.linspace(0.0, PATTERN_EDGE_DEG, 101)
    for occupancy in (1, 2, 4):
        power = np.asarray([_point(angle, occupancy).rf_power_w for angle in angles])
        differences = np.diff(power)
        assert np.all(differences >= -1e-13)
        below_cap = power[:-1] < BEAM_RF_CAP_W - 1e-9
        assert np.all(differences[below_cap] > 0.0)

    # For n_b=4, cap requires G_T = Gamma_4*N/(1.65*C)
    # = 1672.930437138998.  Solving the independent Bessel-pattern equation
    # G_T(theta)=1672.930437138998 gives theta=0.853069795148802 deg.
    below = _point(CAP_HIT_DEG_N4 - 1e-6, 4).rf_power_w
    at = _point(CAP_HIT_DEG_N4, 4).rf_power_w
    above = _point(CAP_HIT_DEG_N4 + 1e-6, 4).rf_power_w
    assert below < BEAM_RF_CAP_W
    assert at == pytest.approx(BEAM_RF_CAP_W, abs=2e-15)
    assert above == BEAM_RF_CAP_W
    assert _point(PATTERN_EDGE_DEG, 1).rf_power_w < BEAM_RF_CAP_W
    assert _point(PATTERN_EDGE_DEG, 2).rf_power_w < BEAM_RF_CAP_W


def test_a_r0_ee_decreases_as_angle_moves_off_axis() -> None:
    angles = np.linspace(0.0, PATTERN_EDGE_DEG, 101)
    for occupancy in (1, 2, 4):
        ee = np.asarray([_point(angle, occupancy).ee_bit_per_j for angle in angles])
        assert np.all(np.diff(ee) <= 1e-6)
        assert ee[-1] < ee[0]


def test_b0_keeps_rf_constant_while_acm_bits_and_ee_fall() -> None:
    angles = np.linspace(0.0, PATTERN_EDGE_DEG, 101)
    points = [_point(angle, 1, fixed_rf=True) for angle in angles]
    assert {point.rf_power_w for point in points} == {BEAM_RF_CAP_W}
    bits = np.asarray([point.total_bits for point in points])
    ee = np.asarray([point.ee_bit_per_j for point in points])
    assert np.all(np.diff(bits) <= 0.0)
    assert np.all(np.diff(ee) <= 0.0)
    assert bits[-1] < bits[0]
    assert ee[-1] < ee[0]
    assert points[0].mode == "QPSK 4/5"
    assert points[-1].mode == "QPSK 1/2"
