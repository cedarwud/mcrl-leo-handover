"""Downlink budget: path loss, atmosphere, noise, SINR (SDD W-06, G-2).

Values come from ``NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`` §1.  Every
constant carries its class code; the two places this layer departs from the
source project are marked ★ and explained.
"""

from __future__ import annotations

import math

import numpy as np

from ..errors import MCRLContractError

# -- carrier and bandwidth -------------------------------------------------

CARRIER_FREQ_HZ: float = 20.0e9
"""**P** — Table I ``f_c = 20 GHz``."""

BANDWIDTH_HZ: float = 500.0e6
"""**P** — Table I ``B = 500 MHz``."""

FREQUENCY_REUSE_FACTOR: int = 3
"""**P'** — TR 38.821 Table 6.1.3.2-1 lists FRF 1/2/3.  MODQN never mentions
reuse, so the three-colour choice is disclosed rather than paper-backed."""

BEAM_BANDWIDTH_HZ: float = BANDWIDTH_HZ / FREQUENCY_REUSE_FACTOR
"""**D** — 166.667 MHz per colour."""

SPEED_OF_LIGHT_M_S: float = 299_792_458.0

# -- terminal noise --------------------------------------------------------

BOLTZMANN_J_PER_K: float = 1.380649e-23
ANTENNA_TEMPERATURE_K: float = 150.0
"""**P'** — TR 38.821 Table 6.1.1.1-3, Ka VSAT."""

REFERENCE_TEMPERATURE_K: float = 290.0
RECEIVER_NOISE_FIGURE_DB: float = 1.2
"""**P'** — same."""

SYSTEM_TEMPERATURE_K: float = ANTENNA_TEMPERATURE_K + REFERENCE_TEMPERATURE_K * (
    10.0 ** (RECEIVER_NOISE_FIGURE_DB / 10.0) - 1.0
)
"""**D** — 242.294 K."""

# -- atmosphere ------------------------------------------------------------

CHI_DB_PER_KM: float = 0.05
"""**P** — Table I ``χ = 0.05 dB/km``."""

ATMOSPHERE_HEIGHT_KM: float = 10.0
"""**S** — effective absorbing-slab height."""

ZENITH_ATMOSPHERIC_LOSS_DB: float = CHI_DB_PER_KM * ATMOSPHERE_HEIGHT_KM
"""**D** — 0.5 dB straight up."""

_MIN_SIN_ELEVATION: float = 1e-3

# -- power -----------------------------------------------------------------

BEAM_POWER_MAX_W: float = 1.65
"""**S** — project-set per-beam transmit ceiling."""

# NOTE (ruling 2026-08-22, §7.6): there is deliberately NO satellite-level
# power ceiling here, and none may be added.  The source project's version
# sits downstream of a ``beam_power_w`` that is gated as a historical
# negative control, so SDD §2.6's r6 argued on a path that was already
# disabled.  Reviving it would re-introduce a per-satellite resource
# mechanism through the back door.  A satellite-level power constraint would
# be a separate decision needing its own source.
#
# The per-satellite resource constraint is carried entirely by PER-LINK power
# feasibility (``classify_link_power_feasibility`` below): per link,
# continuously degrading, sourced, and producing no unserved cliff.

PA_BASE_W: float = 0.25
PA_SCALE_W: float = 0.35
PA_EXPONENT: float = 0.5
"""**S** — idealised class-B-like PA model; efficiency relation per Cripps."""


def free_space_path_gain(slant_km: np.ndarray) -> np.ndarray:
    """Linear FSPL gain ``(λ/4πd)²``.  Multiply, do not divide."""
    slant = np.asarray(slant_km, dtype=np.float64)
    if np.any(slant <= 0.0):
        raise MCRLContractError("slant range must be positive")
    wavelength_m = SPEED_OF_LIGHT_M_S / CARRIER_FREQ_HZ
    return (wavelength_m / (4.0 * math.pi * slant * 1000.0)) ** 2


def atmospheric_loss_db(elevation_deg: np.ndarray) -> np.ndarray:
    """Slab model: ``χ·H_atm / sin(elevation)``, dB, positive.

    ★ **Departure from the source project, declared.**
    ``family_b_geometry.atmos_loss_db`` defaults to a ``corrected_lossy``
    form, ``3·d·χ/(10·h)``, which (a) carries an undocumented 3/10 factor,
    (b) gives 0.015 dB at zenith where ``χ = 0.05 dB/km`` over a 10 km
    atmosphere gives 0.5 dB — a factor of 33 — and (c) **divides by the
    altitude**, which SDD F3 turned from a constant into an observed
    distribution, so the form is no longer even well defined.

    The slab model is the standard derivation from Table I's own ``χ`` and
    is the one used here.  Classed **D** (derived from a **P** value plus
    the declared 10 km slab height).
    """
    elevation = np.asarray(elevation_deg, dtype=np.float64)
    if np.any(elevation < -90.0) or np.any(elevation > 90.0):
        raise MCRLContractError("elevation must lie in [-90, 90] degrees")
    sin_elevation = np.maximum(
        np.sin(np.radians(elevation)), _MIN_SIN_ELEVATION
    )
    return ZENITH_ATMOSPHERIC_LOSS_DB / sin_elevation


def atmospheric_gain(elevation_deg: np.ndarray) -> np.ndarray:
    """Atmospheric loss as a linear gain in (0, 1]."""
    return 10.0 ** (-atmospheric_loss_db(elevation_deg) / 10.0)


def noise_power_w(bandwidth_hz: float = BEAM_BANDWIDTH_HZ) -> float:
    """``σ² = k_B · T_sys · B``."""
    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth must be positive")
    return BOLTZMANN_J_PER_K * SYSTEM_TEMPERATURE_K * bandwidth_hz


def noise_psd_dbm_per_hz() -> float:
    """Noise PSD in dBm/Hz, for the Table I comparison (−174 at 290 K)."""
    return 10.0 * math.log10(BOLTZMANN_J_PER_K * SYSTEM_TEMPERATURE_K) + 30.0


def beam_transmit_power_w(load: np.ndarray) -> np.ndarray:
    """Per-beam transmit power from its served-user count.

    Zero load means a dark beam: exactly zero power, no floor.  P-6 ties
    activation to positive load, and P-7 forbids padding a denominator.

    The result is **not clipped** to ``BEAM_POWER_MAX_W``.  A silent clamp
    would deliver less power than the link needs and still report the user
    as served; the ceiling is an admission test, not a saturation
    (:func:`classify_link_power_feasibility`).
    """
    counts = np.asarray(load, dtype=np.float64)
    if np.any(counts < 0.0):
        raise MCRLContractError("beam loads must be non-negative")
    power = PA_BASE_W + PA_SCALE_W * np.power(
        np.maximum(counts, 0.0), PA_EXPONENT
    )
    return np.where(counts > 0.0, power, 0.0)


def classify_link_power_feasibility(
    required_power_w: np.ndarray,
    *,
    max_power_w: float = BEAM_POWER_MAX_W,
) -> np.ndarray:
    """``p_req > p_max`` — the per-link admission test (ruling §7.5).

    This is where a satellite's finite resources bite, and it is the ONLY
    place they do.  It is **per link**: two users on one beam are judged
    separately, so a demanding link drops out while its neighbours keep
    service.  There is no per-satellite beam-count ceiling anywhere in this
    project — see the note above ``free_space_path_gain`` — because any
    count-based cap darkens whole beams at once and produces exactly the
    unserved cliff this test avoids.

    Returns a boolean array: True where the link is infeasible and the user
    is in ``outage_infeasible``.
    """
    required = np.asarray(required_power_w, dtype=np.float64)
    if np.any(required < 0.0):
        raise MCRLContractError("required power must be non-negative")
    if not np.all(np.isfinite(required)):
        raise MCRLContractError("required power must be finite")
    if max_power_w <= 0.0:
        raise ValueError("max_power_w must be positive")
    return required > max_power_w


def consumed_power_w(beam_power_w: np.ndarray) -> float:
    """Total radiated power of the active beams, W.

    Only the radiated term: the EE denominator SDD ADR-003 fixes is the
    system consumed power, and any additional fixed overhead would have to
    be sourced before it could be added.
    """
    power = np.asarray(beam_power_w, dtype=np.float64)
    if np.any(power < 0.0):
        raise MCRLContractError("beam powers must be non-negative")
    return float(power.sum())


def shannon_rate_bps(
    sinr_linear: np.ndarray,
    *,
    beam_load: np.ndarray,
    bandwidth_hz: float = BEAM_BANDWIDTH_HZ,
) -> np.ndarray:
    """Paper eq. (3.14): ``R = (B^w / U_{s,v}) · log₂(1 + γ)``.

    The beam is time-shared, so its bandwidth is divided by the number of
    users it serves.  ``beam_load`` is **keyword-only and required**: an
    earlier version defaulted the bandwidth to the whole ``B^w`` and left
    the divisor to the caller, which returns a rate exactly ``U`` times too
    high for anyone who forgets — silently, and in the direction that
    flatters the result.

    A zero-load beam has no rate rather than an infinite one.
    """
    sinr = np.asarray(sinr_linear, dtype=np.float64)
    load = np.asarray(beam_load, dtype=np.float64)
    if np.any(sinr < 0.0):
        raise MCRLContractError("SINR must be non-negative")
    if np.any(load < 0.0):
        raise MCRLContractError("beam load must be non-negative")
    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth must be positive")
    shared = np.where(load > 0.0, bandwidth_hz / np.maximum(load, 1.0), 0.0)
    return shared * np.log2(1.0 + sinr)


BOLTZMANN_DBW_PER_K_PER_HZ: float = 10.0 * math.log10(BOLTZMANN_J_PER_K)
"""−228.60 dBW/K/Hz."""


def carrier_to_noise_db(
    *,
    eirp_dbw: float,
    free_space_loss_db: float,
    other_losses_db: float,
    g_over_t_db_per_k: float,
    bandwidth_hz: float,
) -> float:
    """``C/N = EIRP − FSL − L + G/T − k − 10log₁₀(B)``, all dB.

    The standard link equation, written out term by term so a delta ledger
    against a published budget (G-2) can be built from the same pieces.
    """
    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth must be positive")
    return (
        eirp_dbw
        - free_space_loss_db
        - other_losses_db
        + g_over_t_db_per_k
        - BOLTZMANN_DBW_PER_K_PER_HZ
        - 10.0 * math.log10(bandwidth_hz)
    )


def g_over_t_db_per_k(receive_gain_dbi: float) -> float:
    """Terminal figure of merit against this project's ``T_sys``."""
    return receive_gain_dbi - 10.0 * math.log10(SYSTEM_TEMPERATURE_K)


def eirp_dbw(transmit_power_w: float, transmit_gain_dbi: float) -> float:
    if transmit_power_w <= 0.0:
        raise MCRLContractError("EIRP is undefined for zero transmit power")
    return 10.0 * math.log10(transmit_power_w) + transmit_gain_dbi


def free_space_loss_db(slant_km: np.ndarray) -> np.ndarray:
    """Positive FSPL in dB — the reciprocal of :func:`free_space_path_gain`."""
    return -10.0 * np.log10(free_space_path_gain(slant_km))
