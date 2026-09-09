#!/usr/bin/env python3
"""Figure 1 (mechanism): required RF power and energy efficiency vs off-axis angle.

Everything here is recomputed from the sealed closed-form equations of
`V025-ANGLE-POWER-EE-NOTE-2026-09-08.md` ("Exact equations").  No number is
copied from that note's results table; the table is used only by
`figure1_selftest.py` as an external oracle to confirm the recomputation.

Sealed model (primary `a-r0` = V025-ANGLE-RATE-TPC-TDM-ACM, reference `b0` = fixed RF):

    mu(theta)   = 2.07123 * sin(theta) / sin(3.32 deg / 2)
    G_T(theta)  = 2000 * [ J1(mu)/(2 mu) + 36 J3(mu)/mu^3 ]^2 ,  G_T(0) = 2000
    L(10 deg)   = 0.25/sin(10 deg) + 1.08                              [dB]
    h_hat(th)   = G_T(th) * (c/f_c / (4 pi d))^2 * 10^(-L/10) * 10^(G_R/10)
    SE_m        = eta_m / (1 + rolloff)
    gamma_m     = 10^[ (EsN0_m + margin_dB - 10 log10(1+rolloff)) / 10 ]
    m_r(n_b)    = argmin_m { gamma_m : W SE_m / n_b >= r_target }
    Gamma_r(nb) = max(gamma_{m_r(nb)}, gamma_PHY_min)
    p_a(th,nb)  = min(p_cap, Gamma_r(nb) N / h_hat(th))
    p_b(th)     = p_cap
    B_u         = Delta * (W/n_b) * SE_{m(SINR_u)} ,   B = sum_u B_u
    p_sat       = p_cap * 10^(OBO_dB/10)
    E           = Delta * ( sqrt(p p_sat)/eta_PA + P_bb + P_rf )
    EE          = B / E
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

OUT = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Sealed constants (V025 physics successor)
# --------------------------------------------------------------------------
C_LIGHT = 299_792_458.0          # m/s
K_BOLTZMANN = 1.380649e-23       # J/K (SI exact)

F_C_HZ = 20.0e9                  # Ka-band downlink carrier
BANDWIDTH_HZ = 500.0e6 / 3.0     # W, full beam bandwidth
ROLLOFF = 0.20                   # alpha
DECISION_INTERVAL_S = 47 * 0.640  # Delta = 30.08 s (47 sub-intervals of 0.640 s)

TX_FULL_HPBW_DEG = 3.32          # full half-power beamwidth
PATTERN_EDGE_DEG = TX_FULL_HPBW_DEG / 2.0   # 1.66 deg
TX_PEAK_GAIN = 2000.0            # G_T(0), linear
BESSEL_SCALE = 2.07123           # mu scale constant

RX_GAIN_MAX_DBI = 35.0
ZENITH_GASEOUS_LOSS_DB = 0.25
SLANT_KM = 2_000.0
ELEVATION_DEG = 10.0

T_ANT_K = 150.0                  # antenna noise temperature
T_REF_K = 290.0                  # reference temperature
NOISE_FIGURE_DB = 1.2            # receiver noise figure

BEAM_RF_CAP_W = 1.65             # p_cap
OBO_DB = 5.0                     # output back-off -> p_sat
PA_EFFICIENCY = 0.35             # eta_PA
P_BASEBAND_W = 0.338             # P_bb
P_RFFRONTEND_W = 0.200           # P_rf

ACM_MARGIN_DB = 1.7              # implementation margin
RATE_TARGET_BPS = 50_000_000.0   # r* = 50 Mbit/s per served user

# The successor's service rule: a user is served iff its post-resolution SINR
# clears this threshold. It is the sealed PHY floor gamma_PHY_min, carried as a
# rounded-dB constant rather than recomputed from the lowest MODCOD, so it sits
# a relative 1.1e-10 ABOVE the exact QPSK 1/4 threshold. The max() in
# gamma_required() therefore selects this constant at occupancy 1.
SERVICE_THRESHOLD_DB = -1.44181246

OCCUPANCIES = (1, 2, 4)

# DVB-S2 / EN 302 307-1 QPSK ACM table: (name, eta_m [bit/symbol], Es/N0 [dB]).
ACM_TABLE = (
    ("QPSK 1/4",  0.490243, -2.35),
    ("QPSK 1/3",  0.656448, -1.24),
    ("QPSK 2/5",  0.789412, -0.30),
    ("QPSK 1/2",  0.988858,  1.00),
    ("QPSK 3/5",  1.188304,  2.23),
    ("QPSK 2/3",  1.322253,  3.10),
    ("QPSK 3/4",  1.487473,  4.03),
    ("QPSK 4/5",  1.587196,  4.68),
    ("QPSK 5/6",  1.654663,  5.18),
    ("QPSK 8/9",  1.766451,  6.20),
    ("QPSK 9/10", 1.788612,  6.42),
)


# --------------------------------------------------------------------------
# Bessel functions of the first kind, integer order, by the ascending series.
# The argument range needed here is mu in [0, 2.07123], where the series is
# rapidly and accurately convergent; no external special-function library is
# used, so the radiation pattern is an independent recomputation.
#
#   J_n(x) = sum_{k>=0} (-1)^k / (k! (k+n)!) * (x/2)^(2k+n)
# --------------------------------------------------------------------------
def bessel_j(order: int, x: float) -> float:
    half = 0.5 * x
    term = half ** order / math.factorial(order)
    total = term
    k = 0
    while True:
        k += 1
        term *= -(half * half) / (k * (k + order))
        total += term
        if abs(term) <= 1e-18 * max(abs(total), 1e-300) or k > 200:
            return total


def transmit_gain_linear(theta_deg: float) -> float:
    """G_T(theta): the sealed two-term aperture pattern, normalised to G_T(0)=2000."""
    if theta_deg == 0.0:
        return TX_PEAK_GAIN
    mu = BESSEL_SCALE * math.sin(math.radians(theta_deg)) / math.sin(
        math.radians(TX_FULL_HPBW_DEG / 2.0)
    )
    shape = bessel_j(1, mu) / (2.0 * mu) + 36.0 * bessel_j(3, mu) / (mu ** 3)
    return TX_PEAK_GAIN * shape * shape


# --------------------------------------------------------------------------
# Link budget
# --------------------------------------------------------------------------
def free_space_path_gain(slant_km: float) -> float:
    wavelength = C_LIGHT / F_C_HZ
    return (wavelength / (4.0 * math.pi * slant_km * 1.0e3)) ** 2


def scintillation_loss_db(_elevation_deg: float) -> float:
    return 1.08


def atmospheric_loss_db(elevation_deg: float) -> float:
    gaseous = ZENITH_GASEOUS_LOSS_DB / math.sin(math.radians(elevation_deg))
    return gaseous + scintillation_loss_db(elevation_deg)


def angle_independent_gain() -> float:
    """The theta-free product C, so that h_hat(theta) = G_T(theta) * C."""
    return (
        free_space_path_gain(SLANT_KM)
        * 10.0 ** (-atmospheric_loss_db(ELEVATION_DEG) / 10.0)
        * 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
    )


def system_noise_temperature_k() -> float:
    return T_ANT_K + T_REF_K * (10.0 ** (NOISE_FIGURE_DB / 10.0) - 1.0)


def noise_power_w() -> float:
    return K_BOLTZMANN * system_noise_temperature_k() * BANDWIDTH_HZ


def saturated_power_w() -> float:
    return BEAM_RF_CAP_W * 10.0 ** (OBO_DB / 10.0)


# --------------------------------------------------------------------------
# ACM
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Mode:
    name: str
    eta: float          # bit/symbol
    esn0_db: float
    se: float           # bit/s/Hz after roll-off
    gamma: float        # required linear SINR including margin


def _build_modes() -> tuple[Mode, ...]:
    rolloff_db = 10.0 * math.log10(1.0 + ROLLOFF)
    modes = []
    for name, eta, esn0 in ACM_TABLE:
        se = eta / (1.0 + ROLLOFF)
        gamma = 10.0 ** ((esn0 + ACM_MARGIN_DB - rolloff_db) / 10.0)
        modes.append(Mode(name, eta, esn0, se, gamma))
    return tuple(sorted(modes, key=lambda m: m.gamma))


MODES = _build_modes()
GAMMA_PHY_MIN = 10.0 ** (SERVICE_THRESHOLD_DB / 10.0)


def select_mode(sinr_linear: float) -> Mode | None:
    """Highest-rate mode whose threshold the realised SINR clears."""
    chosen = None
    for mode in MODES:
        if sinr_linear >= mode.gamma:
            chosen = mode
        else:
            break
    return chosen


def rate_target_mode(occupancy: int) -> Mode:
    """m_r(n_b): cheapest mode meeting the per-user rate target under equal TDM."""
    for mode in MODES:
        if BANDWIDTH_HZ * mode.se / occupancy >= RATE_TARGET_BPS:
            return mode
    raise ValueError(f"rate target unreachable at occupancy {occupancy}")


def gamma_required(occupancy: int) -> float:
    return max(rate_target_mode(occupancy).gamma, GAMMA_PHY_MIN)


# --------------------------------------------------------------------------
# The two architectures
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Point:
    angle_deg: float
    model: str
    occupancy: int
    transmit_gain: float
    rf_power_w: float
    capped: bool
    mode: str
    bits_beam: float          # bit per decision step, summed over the beam
    bits_user: float
    energy_j: float
    ee_bit_per_j: float


def energy_j(rf_power_w: float) -> float:
    return DECISION_INTERVAL_S * (
        math.sqrt(rf_power_w * saturated_power_w()) / PA_EFFICIENCY
        + P_BASEBAND_W
        + P_RFFRONTEND_W
    )


def evaluate(angle_deg: float, occupancy: int, *, fixed_rf: bool) -> Point:
    gain = transmit_gain_linear(angle_deg)
    h_hat = gain * angle_independent_gain()
    noise = noise_power_w()

    if fixed_rf:
        power = BEAM_RF_CAP_W
        capped = True
    else:
        uncapped = gamma_required(occupancy) * noise / h_hat
        power = min(BEAM_RF_CAP_W, uncapped)
        capped = uncapped >= BEAM_RF_CAP_W

    # One ULP of realised-field clearance: the rate-target controller lands
    # exactly on an ACM threshold, and this keeps the final divide/multiply
    # round trip from deciding decodability. Relative size < 2.3e-16.
    sinr = math.nextafter(power * h_hat, math.inf) / noise
    mode = select_mode(sinr)
    if mode is None:
        bits_beam = 0.0
        name = "outage"
    else:
        bits_beam = DECISION_INTERVAL_S * BANDWIDTH_HZ * mode.se
        name = mode.name

    energy = energy_j(power)
    return Point(
        angle_deg,
        "b0" if fixed_rf else "a-r0",
        occupancy,
        gain,
        power,
        capped,
        name,
        bits_beam,
        bits_beam / occupancy,
        energy,
        bits_beam / energy,
    )


def cap_hit_angle_deg(occupancy: int) -> float | None:
    """Angle at which p_a first reaches p_cap, by bisection on G_T(theta)."""
    needed_gain = (
        gamma_required(occupancy) * noise_power_w()
        / (BEAM_RF_CAP_W * angle_independent_gain())
    )
    if needed_gain >= TX_PEAK_GAIN or needed_gain <= transmit_gain_linear(
        PATTERN_EDGE_DEG
    ):
        return None
    lo, hi = 0.0, PATTERN_EDGE_DEG
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if transmit_gain_linear(mid) > needed_gain:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------
def sweep(n_points: int = 601) -> list[Point]:
    step = PATTERN_EDGE_DEG / (n_points - 1)
    angles = [i * step for i in range(n_points)]
    # Include the exact cap-hit angles so the kink is rendered without rounding.
    for occupancy in OCCUPANCIES:
        hit = cap_hit_angle_deg(occupancy)
        if hit is not None:
            angles.append(hit)
    angles = sorted(set(angles))

    points: list[Point] = []
    for angle in angles:
        for occupancy in OCCUPANCIES:
            points.append(evaluate(angle, occupancy, fixed_rf=False))
        points.append(evaluate(angle, 1, fixed_rf=True))
    return points


CSV_FIELDS = (
    "angle_deg",
    "model",
    "n_b",
    "G_T_linear",
    "p_rf_W",
    "at_cap",
    "acm_mode",
    "bits_per_beam_step_bit",
    "bits_per_user_step_bit",
    "energy_per_step_J",
    "ee_bit_per_J",
)


def write_csv(points: list[Point], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_FIELDS)
        for p in points:
            writer.writerow(
                [
                    f"{p.angle_deg:.9f}",
                    p.model,
                    p.occupancy,
                    f"{p.transmit_gain:.9f}",
                    f"{p.rf_power_w:.12f}",
                    "1" if p.capped else "0",
                    p.mode,
                    f"{p.bits_beam:.6f}",
                    f"{p.bits_user:.6f}",
                    f"{p.energy_j:.9f}",
                    f"{p.ee_bit_per_j:.6f}",
                ]
            )


if __name__ == "__main__":
    pts = sweep()
    write_csv(pts, OUT / "figure1-data.csv")
    print(f"rows={len(pts)} -> {OUT / 'figure1-data.csv'}")
    for nb in OCCUPANCIES:
        hit = cap_hit_angle_deg(nb)
        print(
            f"  n_b={nb}  m_r={rate_target_mode(nb).name}"
            f"  Gamma_r={gamma_required(nb):.15f}"
            f"  cap-hit={'none' if hit is None else format(hit, '.12f') + ' deg'}"
        )
