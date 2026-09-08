"""V0.25 channel and antenna scalar helpers.

The helpers are pure and vectorised where useful.  Random draws require an
explicit generator so candidate ordering or counterfactual evaluation cannot
silently acquire a private RNG stream.
"""

from __future__ import annotations

import math

import numpy as np

from mcrl.errors import MCRLContractError
from mcrl.runtime.bessel import bessel_j_array, bessel_j_miller

from .constants_v025 import (
    BOLTZMANN_J_PER_K,
    CARRIER_FREQUENCY_HZ,
    RICIAN_K_FACTOR_DB,
    RX_ENVELOPE_A_DBI,
    RX_ENVELOPE_B,
    RX_GAIN_FLOOR_DBI,
    RX_GAIN_MAX_DBI,
    SPEED_OF_LIGHT_M_S,
    SYSTEM_TEMPERATURE_K,
    SCINTILLATION_ELEVATION_DEG,
    SCINTILLATION_LOSS_DB,
    SHADOW_SIGMA_DB,
    SHADOW_SIGMA_ELEVATION_DEG,
    MINIMUM_ELEVATION_DEG,
    TX_FULL_HPBW_DEG,
    TX_G0_LINEAR,
)

_BESSEL_MU_COEFFICIENT = 2.07123
_MU_ZERO = 1.0e-10


def noise_power_w(bandwidth_hz: float) -> float:
    """Return ``k*T_sys*bandwidth`` in watts."""

    if not math.isfinite(bandwidth_hz) or bandwidth_hz <= 0.0:
        raise ValueError("bandwidth_hz must be finite and positive")
    return BOLTZMANN_J_PER_K * SYSTEM_TEMPERATURE_K * bandwidth_hz


def free_space_path_gain(slant_km: np.ndarray | float) -> np.ndarray:
    """Linear free-space gain; doubling distance gives exactly one quarter."""

    distance = np.asarray(slant_km, dtype=np.float64)
    if not np.all(np.isfinite(distance)) or np.any(distance <= 0.0):
        raise MCRLContractError("slant range must be finite and positive")
    wavelength = SPEED_OF_LIGHT_M_S / CARRIER_FREQUENCY_HZ
    return (wavelength / (4.0 * math.pi * distance * 1000.0)) ** 2


def db_loss_gain(loss_db: np.ndarray | float) -> np.ndarray:
    """Convert a nonnegative dB loss to its linear power multiplier."""

    loss = np.asarray(loss_db, dtype=np.float64)
    if not np.all(np.isfinite(loss)) or np.any(loss < 0.0):
        raise MCRLContractError("loss_db must be finite and nonnegative")
    return 10.0 ** (-loss / 10.0)


def scintillation_loss_db(elevation_deg: np.ndarray | float) -> np.ndarray:
    """Retained 20-GHz deterministic table, linearly interpolated and clamped."""

    elevation = np.asarray(elevation_deg, dtype=np.float64)
    if not np.all(np.isfinite(elevation)) or np.any((elevation < -90.0) | (elevation > 90.0)):
        raise MCRLContractError("elevation must be finite and in [-90,90] degrees")
    return np.interp(
        np.clip(elevation, SCINTILLATION_ELEVATION_DEG[0], SCINTILLATION_ELEVATION_DEG[-1]),
        SCINTILLATION_ELEVATION_DEG,
        SCINTILLATION_LOSS_DB,
    )


def shadow_sigma_db(elevation_deg: np.ndarray | float) -> np.ndarray:
    """Retained Ka-LOS zero-mean-dB shadow sigma table."""

    elevation = np.asarray(elevation_deg, dtype=np.float64)
    if not np.all(np.isfinite(elevation)) or np.any((elevation < -90.0) | (elevation > 90.0)):
        raise MCRLContractError("elevation must be finite and in [-90,90] degrees")
    return np.interp(
        np.clip(elevation, SHADOW_SIGMA_ELEVATION_DEG[0], SHADOW_SIGMA_ELEVATION_DEG[-1]),
        SHADOW_SIGMA_ELEVATION_DEG,
        SHADOW_SIGMA_DB,
    )


def transmit_gain_linear(theta_deg: np.ndarray | float) -> np.ndarray:
    """HOBS ideal aperture pattern, with full-HPBW converted once."""

    theta = np.asarray(theta_deg, dtype=np.float64)
    if not np.all(np.isfinite(theta)):
        raise MCRLContractError("off-axis angles must be finite")
    half_power = math.radians(TX_FULL_HPBW_DEG / 2.0)
    mu = _BESSEL_MU_COEFFICIENT * np.sin(np.radians(theta)) / math.sin(half_power)
    flat = np.atleast_1d(mu).ravel()
    on_axis = np.abs(flat) < _MU_ZERO
    safe = np.where(on_axis, 1.0, flat)
    # The historical ascending series is already measurably inaccurate at
    # mu=34.  Route the new engine to stable Miller recursion from mu>=20;
    # keep the vectorised series only in its well-conditioned main-lobe range.
    j1, j3 = bessel_j_array((1, 3), safe)
    stable = np.abs(safe) >= 20.0
    if np.any(stable):
        stable_values = safe[stable]
        j1[stable] = np.asarray([bessel_j_miller(1, float(value)) for value in stable_values])
        j3[stable] = np.asarray([bessel_j_miller(3, float(value)) for value in stable_values])
    bracket = j1 / (2.0 * safe) + 36.0 * j3 / safe**3
    result = TX_G0_LINEAR * bracket**2
    result[on_axis] = TX_G0_LINEAR
    return result.reshape(theta.shape)


def receive_gain_dbi(separation_deg: np.ndarray | float) -> np.ndarray:
    """Retained clipped near-axis extrapolation, explicitly not ITU-prescribed."""

    separation = np.asarray(separation_deg, dtype=np.float64)
    if not np.all(np.isfinite(separation)) or np.any(separation < 0.0):
        raise MCRLContractError("receive separations must be finite and nonnegative")
    with np.errstate(divide="ignore"):
        envelope = RX_ENVELOPE_A_DBI - RX_ENVELOPE_B * np.log10(
            np.maximum(separation, 1.0e-12)
        )
    return np.clip(envelope, RX_GAIN_FLOOR_DBI, RX_GAIN_MAX_DBI)


def receive_gain_linear(separation_deg: np.ndarray | float) -> np.ndarray:
    return 10.0 ** (receive_gain_dbi(separation_deg) / 10.0)


def rician_power_gain(
    rng: np.random.Generator,
    size: tuple[int, ...],
    *,
    k_factor_db: float = RICIAN_K_FACTOR_DB,
) -> np.ndarray:
    """Unit-mean Rician power gain."""

    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be an explicit numpy Generator")
    if not math.isfinite(k_factor_db):
        raise ValueError("k_factor_db must be finite")
    k_linear = 10.0 ** (k_factor_db / 10.0)
    los = math.sqrt(k_linear / (k_linear + 1.0))
    sigma = math.sqrt(1.0 / (2.0 * (k_linear + 1.0)))
    real = los + sigma * rng.standard_normal(size)
    imaginary = sigma * rng.standard_normal(size)
    return real**2 + imaginary**2


def shadow_linear_mean(sigma_db: float) -> float:
    """Mean of ``10**(-X/10)`` for ``X ~ Normal(0, sigma_db**2)``."""

    if not math.isfinite(sigma_db) or sigma_db < 0.0:
        raise ValueError("sigma_db must be finite and nonnegative")
    return math.exp(0.5 * (sigma_db * math.log(10.0) / 10.0) ** 2)


def keyed_component_seed(
    world: int,
    user: int,
    norad: int,
    absolute_time_ns: int,
    component: str,
) -> int:
    """Stable action/history-free key material for external tape builders."""

    import hashlib

    payload = f"{world}|{user}|{norad}|{absolute_time_ns}|{component}".encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def is_visible(elevation_deg: float) -> bool:
    """The live V0.25 visibility contract uses the wired 10-degree floor."""

    if not math.isfinite(elevation_deg):
        raise MCRLContractError("elevation must be finite")
    return elevation_deg >= MINIMUM_ELEVATION_DEG


__all__ = [
    "db_loss_gain",
    "free_space_path_gain",
    "keyed_component_seed",
    "is_visible",
    "noise_power_w",
    "receive_gain_dbi",
    "receive_gain_linear",
    "rician_power_gain",
    "scintillation_loss_db",
    "shadow_sigma_db",
    "shadow_linear_mean",
    "transmit_gain_linear",
]
