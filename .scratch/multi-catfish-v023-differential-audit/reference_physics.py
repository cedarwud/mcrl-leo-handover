"""Clean-room reference for the documented V0.23 downlink physics.

This module intentionally imports no code from :mod:`mcrl.env`.  Equations and
numbers come from the documents named in the audit request and the constant
docstrings.  Arrays are NumPy arrays in SI units unless a name ends in ``_db``
or ``_deg``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence

import numpy as np
from scipy.special import jv


# Documented constants, repeated deliberately rather than imported.
CARRIER_FREQ_HZ = 20.0e9
TOTAL_BANDWIDTH_HZ = 500.0e6
FREQUENCY_REUSE_FACTOR = 3
BEAM_BANDWIDTH_HZ = TOTAL_BANDWIDTH_HZ / FREQUENCY_REUSE_FACTOR
SPEED_OF_LIGHT_M_S = 299_792_458.0
BOLTZMANN_J_PER_K = 1.380649e-23
ANTENNA_TEMPERATURE_K = 150.0
REFERENCE_TEMPERATURE_K = 290.0
RECEIVER_NOISE_FIGURE_DB = 1.2
SYSTEM_TEMPERATURE_K = ANTENNA_TEMPERATURE_K + REFERENCE_TEMPERATURE_K * (
    10.0 ** (RECEIVER_NOISE_FIGURE_DB / 10.0) - 1.0
)
ZENITH_GASEOUS_LOSS_DB = 0.25
THETA_3DB_DEG = 3.32
TX_GAIN_BORESIGHT_LINEAR = 2000.0
TX_PATTERN_COEFFICIENT = 2.07123
TX_BORESIGHT_EPSILON = 1.0e-10
RX_PATTERN_A_DBI = 32.0
RX_PATTERN_B = 25.0
RX_GAIN_MAX_DBI = 35.0
RX_GAIN_FLOOR_DBI = -10.0
RX_TERMINAL_DIAMETER_M = 0.6
SEGMENT_START_POWER_W = 0.825
BEAM_POWER_MAX_W = 1.65
PA_MAX_EFFICIENCY = 0.35
PA_OUTPUT_BACKOFF_DB = 5.0
PA_SATURATION_POWER_W = BEAM_POWER_MAX_W * 10.0 ** (
    PA_OUTPUT_BACKOFF_DB / 10.0
)
CIRCUIT_POWER_PER_BEAM_W = 0.338
BASEBAND_POWER_PER_SATELLITE_W = 0.200
RICIAN_K_FACTOR_DB = 20.0
DECISION_STEP_S = 30.08

SCINTILLATION_ELEVATION_DEG = np.array(
    [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]
)
SCINTILLATION_LOSS_DB = np.array(
    [1.08, 0.48, 0.30, 0.22, 0.17, 0.13, 0.12, 0.12, 0.12]
)
SHADOW_SIGMA_DB = np.array([1.9, 1.6, 1.9, 2.3, 2.7, 3.1, 3.0, 3.6, 0.4])


def _float_array(value: object) -> np.ndarray:
    return np.asarray(value, dtype=np.float64)


def free_space_loss_db(
    slant_range_km: object, carrier_freq_hz: float = CARRIER_FREQ_HZ
) -> np.ndarray:
    """Positive free-space path loss, ``20 log10(4 pi d/lambda)``."""
    distance_m = _float_array(slant_range_km) * 1000.0
    if np.any(distance_m <= 0.0) or carrier_freq_hz <= 0.0:
        raise ValueError("distance and carrier frequency must be positive")
    wavelength_m = SPEED_OF_LIGHT_M_S / carrier_freq_hz
    return 20.0 * np.log10(4.0 * np.pi * distance_m / wavelength_m)


def atmospheric_loss_db(elevation_deg: object) -> np.ndarray:
    """TR 38.811 (6.6-8), with sine guarded only at zero elevation."""
    sine = np.maximum(np.sin(np.deg2rad(_float_array(elevation_deg))), 0.001)
    return ZENITH_GASEOUS_LOSS_DB / sine


def scintillation_loss_db(elevation_deg: object) -> np.ndarray:
    """Held-endpoint linear interpolation of the documented 20 GHz table."""
    return np.interp(
        _float_array(elevation_deg),
        SCINTILLATION_ELEVATION_DEG,
        SCINTILLATION_LOSS_DB,
    )


def shadow_sigma_db(elevation_deg: object) -> np.ndarray:
    return np.interp(
        _float_array(elevation_deg),
        SCINTILLATION_ELEVATION_DEG,
        SHADOW_SIGMA_DB,
    )


def shadow_loss_db_from_standard_normal(
    elevation_deg: object, standard_normal: object
) -> np.ndarray:
    """Signed, zero-mean-dB shadow loss; deliberately not mean-normalised."""
    return shadow_sigma_db(elevation_deg) * _float_array(standard_normal)


def total_path_loss_db(
    slant_range_km: object,
    elevation_deg: object,
    shadow_loss_db: object = 0.0,
) -> np.ndarray:
    return (
        free_space_loss_db(slant_range_km)
        + atmospheric_loss_db(elevation_deg)
        + scintillation_loss_db(elevation_deg)
        + _float_array(shadow_loss_db)
    )


def transmit_pattern_gain(off_axis_deg: object) -> np.ndarray:
    """Thesis eqs. (3.8-3.9), using the full-HPBW/half-angle convention."""
    theta = np.deg2rad(_float_array(off_axis_deg))
    half_hpbw = math.radians(THETA_3DB_DEG / 2.0)
    mu = TX_PATTERN_COEFFICIENT * np.sin(theta) / math.sin(half_hpbw)
    with np.errstate(divide="ignore", invalid="ignore"):
        bracket = jv(1, mu) / (2.0 * mu) + 36.0 * jv(3, mu) / mu**3
        pattern = bracket**2
    return np.where(
        np.abs(mu) < TX_BORESIGHT_EPSILON,
        TX_GAIN_BORESIGHT_LINEAR,
        TX_GAIN_BORESIGHT_LINEAR * pattern,
    )


def s465_minimum_angle_deg(
    diameter_m: float = RX_TERMINAL_DIAMETER_M,
    carrier_freq_hz: float = CARRIER_FREQ_HZ,
) -> float:
    """S.465-6 recommends-2 ``phi_min`` with its D/lambda branch."""
    wavelength_m = SPEED_OF_LIGHT_M_S / carrier_freq_hz
    ratio = diameter_m / wavelength_m
    if ratio >= 50.0:
        return max(1.0, 100.0 / ratio)
    return max(2.0, 114.0 * ratio**-1.09)


def receive_pattern_gain_dbi(separation_deg: object) -> np.ndarray:
    """Eq. (3.10c), including the thesis's disclosed near-axis extension."""
    theta = _float_array(separation_deg)
    if np.any(theta < 0.0) or np.any(theta > 180.0):
        raise ValueError("receive off-axis angle must be in [0, 180] degrees")
    with np.errstate(divide="ignore"):
        envelope = RX_PATTERN_A_DBI - RX_PATTERN_B * np.log10(theta)
    return np.clip(envelope, RX_GAIN_FLOOR_DBI, RX_GAIN_MAX_DBI)


def receive_pattern_gain(separation_deg: object) -> np.ndarray:
    return 10.0 ** (receive_pattern_gain_dbi(separation_deg) / 10.0)


def noise_power_w(bandwidth_hz: float = BEAM_BANDWIDTH_HZ) -> float:
    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth must be positive")
    return BOLTZMANN_J_PER_K * SYSTEM_TEMPERATURE_K * bandwidth_hz


def rician_power_gain_from_standard_normals(
    normal_i: object,
    normal_q: object,
    k_factor_db: float = RICIAN_K_FACTOR_DB,
) -> np.ndarray:
    """Unit-mean Rician power from two independent N(0,1) variates."""
    k_linear = 10.0 ** (k_factor_db / 10.0)
    sigma = math.sqrt(1.0 / (2.0 * (k_linear + 1.0)))
    direct = math.sqrt(k_linear / (k_linear + 1.0))
    i = direct + sigma * _float_array(normal_i)
    q = sigma * _float_array(normal_q)
    return i * i + q * q


def link_power_factor(
    slant_range_km: object,
    elevation_deg: object,
    receive_separation_deg: object,
    rician_gain: object = 1.0,
    shadow_loss_db: object = 0.0,
) -> np.ndarray:
    """Thesis eq. (3.10a), including the named Rician factor."""
    loss = total_path_loss_db(slant_range_km, elevation_deg, shadow_loss_db)
    return (
        10.0 ** (-loss / 10.0)
        * receive_pattern_gain(receive_separation_deg)
        * _float_array(rician_gain)
    )


def segment_link_power_w(start_gain: object, current_gain: object) -> np.ndarray:
    """Eq. (3.12), with no cap or projection."""
    start = _float_array(start_gain)
    current = _float_array(current_gain)
    if np.any(start < 0.0) or np.any(current <= 0.0):
        raise ValueError("segment gains must be non-negative/positive")
    return SEGMENT_START_POWER_W * start / current


def feasible_power(power_w: object) -> np.ndarray:
    """Declared external feasibility gate, inclusive at p_max."""
    power = _float_array(power_w)
    return np.isfinite(power) & (power >= 0.0) & (power <= BEAM_POWER_MAX_W)


@dataclass(frozen=True)
class PowerSegment:
    """Anchor for one uninterrupted served physical association."""

    association: tuple[int, int]
    start_gain: float


def advance_power_segment(
    association: tuple[int, int],
    current_gain: float,
    previous: PowerSegment | None,
) -> tuple[float, bool, PowerSegment | None]:
    """Apply eq. (3.12) and its declared reset/feasibility semantics.

    A physical association is ``(satellite_id, cell_id)``.  A change creates
    a new anchor at the current gain, while a continuation retains its prior
    anchor across decision epochs (including dwell boundaries).  An
    infeasible proposal is unserved and breaks the segment; the next served
    attempt therefore starts a new segment.
    """
    gain = float(current_gain)
    if not math.isfinite(gain) or gain <= 0.0:
        raise ValueError("current gain must be finite and positive")
    if previous is None or previous.association != association:
        anchor = PowerSegment(association=association, start_gain=gain)
    else:
        anchor = previous
    power = float(segment_link_power_w(anchor.start_gain, gain))
    is_feasible = bool(feasible_power(power))
    return power, is_feasible, anchor if is_feasible else None


def per_beam_power_w(
    link_power_w: object, beam_keys: Sequence[tuple[int, int]]
) -> dict[tuple[int, int], float]:
    """Maximum link RF power among served users on each beam."""
    power = _float_array(link_power_w)
    if power.shape != (len(beam_keys),):
        raise ValueError("one beam key is required per link power")
    result: dict[tuple[int, int], float] = {}
    for key, value in zip(beam_keys, power, strict=True):
        result[key] = max(result.get(key, 0.0), float(value))
    return result


def pa_efficiency(power_w: object) -> np.ndarray:
    power = _float_array(power_w)
    if np.any(power < 0.0):
        raise ValueError("RF power must be non-negative")
    return np.minimum(
        PA_MAX_EFFICIENCY,
        PA_MAX_EFFICIENCY * np.sqrt(power / PA_SATURATION_POWER_W),
    )


def pa_supply_power_w(power_w: object) -> np.ndarray:
    power = _float_array(power_w)
    efficiency = pa_efficiency(power)
    if np.any((power > 0.0) & (efficiency <= 0.0)):
        raise ValueError("positive RF power with zero PA efficiency")
    return np.divide(power, efficiency, out=np.zeros_like(power), where=efficiency > 0)


def fixed_power_w(beam_keys: Sequence[tuple[int, int]]) -> float:
    active_satellites = {satellite for satellite, _ in beam_keys}
    return (
        len(beam_keys) * CIRCUIT_POWER_PER_BEAM_W
        + len(active_satellites) * BASEBAND_POWER_PER_SATELLITE_W
    )


def system_power_w(beam_powers: Mapping[tuple[int, int], float]) -> float:
    keys = tuple(beam_powers)
    supply = pa_supply_power_w(np.fromiter(beam_powers.values(), dtype=float))
    return fixed_power_w(keys) + float(np.sum(supply))


@dataclass(frozen=True)
class Interferer:
    """One active beam's inputs at one victim user."""

    satellite_id: int
    cell_id: int
    colour: int
    beam_power_w: float
    transmit_off_axis_deg: float
    slant_range_km: float
    elevation_deg: float
    receive_separation_deg: float
    rician_gain: float
    shadow_loss_db: float


def co_colour_interference_w(
    *,
    serving_satellite_id: int,
    serving_cell_id: int,
    serving_colour: int,
    interferers: Iterable[Interferer],
) -> tuple[float, float]:
    """Eqs. (3.12a-b); returns intra- then inter-satellite watts."""
    intra = 0.0
    inter = 0.0
    for term in interferers:
        if term.colour != serving_colour:
            continue
        # Exclude the serving physical beam only.  A same cell on another
        # satellite remains an interferer as required by (3.12b).
        if (
            term.satellite_id == serving_satellite_id
            and term.cell_id == serving_cell_id
        ):
            continue
        receive_sep = (
            0.0
            if term.satellite_id == serving_satellite_id
            else term.receive_separation_deg
        )
        h = link_power_factor(
            term.slant_range_km,
            term.elevation_deg,
            receive_sep,
            term.rician_gain,
            term.shadow_loss_db,
        )
        received = float(
            term.beam_power_w
            * transmit_pattern_gain(term.transmit_off_axis_deg)
            * h
        )
        if term.satellite_id == serving_satellite_id:
            intra += received
        else:
            inter += received
    return intra, inter


def wanted_power_w(
    link_power_w: object,
    transmit_off_axis_deg: object,
    slant_range_km: object,
    elevation_deg: object,
    rician_gain: object,
    shadow_loss_db: object,
) -> np.ndarray:
    """Eq. (3.13) numerator; wanted receive separation is zero."""
    h = link_power_factor(
        slant_range_km,
        elevation_deg,
        0.0,
        rician_gain,
        shadow_loss_db,
    )
    return (
        _float_array(link_power_w)
        * transmit_pattern_gain(transmit_off_axis_deg)
        * h
    )


def sinr(wanted_w: object, interference_w: object, bandwidth_hz: float = BEAM_BANDWIDTH_HZ) -> np.ndarray:
    denominator = _float_array(interference_w) + noise_power_w(bandwidth_hz)
    if np.any(denominator <= 0.0):
        raise ValueError("SINR denominator must be positive")
    return _float_array(wanted_w) / denominator


def shannon_rate_bps(
    sinr_linear: object,
    beam_load: object,
    bandwidth_hz: float = BEAM_BANDWIDTH_HZ,
) -> np.ndarray:
    load = _float_array(beam_load)
    if np.any(load <= 0.0):
        raise ValueError("served-link beam load must be positive")
    return bandwidth_hz / load * np.log2(1.0 + _float_array(sinr_linear))


def delivered_bits(rate_bps: object, duration_s: float = DECISION_STEP_S) -> np.ndarray:
    if duration_s <= 0.0:
        raise ValueError("duration must be positive")
    return _float_array(rate_bps) * duration_s


def pooled_energy_efficiency(
    step_bits: object, step_system_power_w: object, duration_s: float = DECISION_STEP_S
) -> float:
    bits = float(np.sum(_float_array(step_bits)))
    energy_j = float(np.sum(_float_array(step_system_power_w))) * duration_s
    if energy_j == 0.0:
        if bits == 0.0:
            return 0.0
        raise ValueError("positive bits with zero network energy")
    return bits / energy_j


def axial_colour(q: int, r: int) -> int:
    return (q - r) % FREQUENCY_REUSE_FACTOR


if __name__ == "__main__":
    # Small red-capable anchors: these deliberately assert the branch that the
    # local docstring gets wrong for D/lambda ~= 40.
    assert math.isclose(float(transmit_pattern_gain(0.0)), 2000.0)
    half = float(transmit_pattern_gain(THETA_3DB_DEG / 2.0)) / 2000.0
    assert math.isclose(half, 0.5, rel_tol=2e-5)
    assert 2.0 <= s465_minimum_angle_deg() < 2.1
    assert math.isclose(float(receive_pattern_gain_dbi(1.0)), 32.0)
    assert math.isclose(float(receive_pattern_gain_dbi(48.0)), -10.0)
    p0, ok, segment = advance_power_segment((1, 2), 0.25, None)
    assert ok and segment is not None and math.isclose(p0, SEGMENT_START_POWER_W)
    p1, ok, segment = advance_power_segment((1, 2), 0.125, segment)
    assert ok and segment is not None and math.isclose(p1, BEAM_POWER_MAX_W)
    _p2, ok, segment = advance_power_segment((1, 2), 0.1, segment)
    assert not ok and segment is None
    print("reference anchors: PASS")
