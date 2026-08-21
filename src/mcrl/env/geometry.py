"""Earth model, time, and coordinate transforms for the real-ephemeris layer.

SDD §3.1: "地球模型與座標轉換須與 ``family_b_geometry.py`` 現有的
``R_E_KM``/``OMEGA_E_RAD_S`` 一致".  Those two constants live in
``mcrl.env.constants``; everything here is built on them.

Frames
------
``TEME``  True Equator, Mean Equinox — what SGP4 outputs.  Inertial.
``ECEF``  Earth-centred, Earth-fixed.  ``r_ecef = Rz(GMST) · r_teme``.

Polar motion (TEME→PEF→ITRF) is omitted: it is below 0.5 m for LEO, two
orders under the G-1 budget of 1 km, and needs EOP tables this project does
not freeze.  Declared here rather than buried.
"""

from __future__ import annotations

import datetime as dt
import math

import numpy as np

from .constants import KM_PER_DEG_LAT, OMEGA_E_RAD_S, R_E_KM

_JD_J2000 = 2451545.0
_SECONDS_PER_JULIAN_CENTURY = 86400.0 * 36525.0

# Vallado's IAU-82 GMST polynomial, seconds of time (Astro Almanac 1992).
_GMST_C0 = 67310.54841
_GMST_C1 = 876600.0 * 3600.0 + 8640184.812866
_GMST_C2 = 0.093104
_GMST_C3 = -6.2e-6


def julian_date(when: dt.datetime) -> tuple[float, float]:
    """Return ``(jd, fraction)`` for a timezone-aware UTC datetime.

    Split into day and fraction the way SGP4 wants it, so the propagator
    keeps its full precision instead of losing it to a 2.4-million-sized
    float.
    """
    if when.tzinfo is None:
        raise ValueError("julian_date requires a timezone-aware datetime")
    utc = when.astimezone(dt.timezone.utc)
    year, month, day = utc.year, utc.month, utc.day
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    jd = (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )
    fraction = (
        utc.hour * 3600.0
        + utc.minute * 60.0
        + utc.second
        + utc.microsecond * 1e-6
    ) / 86400.0
    return float(jd), float(fraction)


def gmst_rad(jd: float, fraction: float = 0.0) -> float:
    """Greenwich Mean Sidereal Time in radians, IAU-82 polynomial.

    UT1 is approximated by UTC.  |UT1 − UTC| ≤ 0.9 s, which rotates the Earth
    by ≤ 66 µrad, i.e. ≤ 0.45 km at the equator — inside the G-1 budget but
    not negligible, so it is stated rather than assumed away.
    """
    tut1 = ((jd - _JD_J2000) + fraction) / 36525.0
    seconds = (
        _GMST_C3 * tut1**3 + _GMST_C2 * tut1**2 + _GMST_C1 * tut1 + _GMST_C0
    )
    # 240 s of time per degree of rotation.
    return math.radians(math.fmod(seconds / 240.0, 360.0)) % (2.0 * math.pi)


def gmst_rate_rad_s(jd: float = _JD_J2000, fraction: float = 0.0) -> float:
    """Analytic d(GMST)/dt, rad/s.  Must equal ``OMEGA_E_RAD_S``."""
    tut1 = ((jd - _JD_J2000) + fraction) / 36525.0
    d_seconds_d_tut1 = (
        3.0 * _GMST_C3 * tut1**2 + 2.0 * _GMST_C2 * tut1 + _GMST_C1
    )
    return math.radians(d_seconds_d_tut1 / 240.0) / _SECONDS_PER_JULIAN_CENTURY


def teme_to_ecef(r_teme_km: np.ndarray, gmst: np.ndarray) -> np.ndarray:
    """Rotate TEME positions into ECEF about the z-axis by ``gmst``.

    ``r_teme_km`` has shape ``(..., T, 3)`` and ``gmst`` shape ``(T,)``.
    Same rotation convention as ``family_b_geometry.py:288-291``.
    """
    r = np.asarray(r_teme_km, dtype=np.float64)
    g = np.asarray(gmst, dtype=np.float64)
    if r.shape[-1] != 3:
        raise ValueError(f"expected trailing axis of size 3, got {r.shape}")
    if g.shape != r.shape[-2:-1]:
        raise ValueError(
            f"gmst shape {g.shape} does not match time axis {r.shape[-2:-1]}"
        )
    cos_g = np.cos(g)
    sin_g = np.sin(g)
    x, y, z = r[..., 0], r[..., 1], r[..., 2]
    return np.stack(
        [cos_g * x + sin_g * y, -sin_g * x + cos_g * y, z], axis=-1
    )


def teme_velocity_to_ecef(
    v_teme_km_s: np.ndarray,
    r_ecef_km: np.ndarray,
    gmst: np.ndarray,
) -> np.ndarray:
    """Rotate a TEME velocity into the rotating ECEF frame.

    ``v_ecef = Rz(GMST)·v_teme − ω × r_ecef``.  The second term is not
    optional: a point fixed on the ground has zero ECEF velocity by
    definition, so the frame's own rotation has to come out of the
    satellite's velocity too.  At LEO it is ~0.35 km/s against ~7.5 km/s —
    5%, far too large to drop from a range rate.
    """
    v_rotated = teme_to_ecef(v_teme_km_s, gmst)
    r = np.asarray(r_ecef_km, dtype=np.float64)
    # ω × r with ω = (0, 0, OMEGA_E_RAD_S)
    omega_cross_r = np.stack(
        [
            -OMEGA_E_RAD_S * r[..., 1],
            OMEGA_E_RAD_S * r[..., 0],
            np.zeros_like(r[..., 2]),
        ],
        axis=-1,
    )
    return v_rotated - omega_cross_r


def range_rate_km_s(
    sat_ecef_km: np.ndarray,
    sat_velocity_ecef_km_s: np.ndarray,
    ground_ecef_km: np.ndarray,
) -> np.ndarray:
    """Signed slant-range rate: negative approaching, positive receding.

    ``d|r|/dt = <v, r/|r|>`` for the relative vector.  The ground point is
    stationary in ECEF, so the relative velocity is the satellite's.
    """
    delta = np.asarray(sat_ecef_km, dtype=np.float64) - np.asarray(
        ground_ecef_km, dtype=np.float64
    )
    distance = np.maximum(np.linalg.norm(delta, axis=-1), 1e-12)
    unit = delta / distance[..., None]
    return np.sum(np.asarray(sat_velocity_ecef_km_s, dtype=np.float64) * unit, axis=-1)


def geodetic_to_ecef(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    """Spherical-Earth surface point(s) to ECEF km.  Shape ``(..., 3)``."""
    lat = np.radians(np.asarray(lat_deg, dtype=np.float64))
    lon = np.radians(np.asarray(lon_deg, dtype=np.float64))
    return np.stack(
        [
            R_E_KM * np.cos(lat) * np.cos(lon),
            R_E_KM * np.cos(lat) * np.sin(lon),
            R_E_KM * np.sin(lat),
        ],
        axis=-1,
    )


def ecef_to_geodetic(r_ecef_km: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Spherical sub-point latitude/longitude in degrees."""
    r = np.asarray(r_ecef_km, dtype=np.float64)
    x, y, z = r[..., 0], r[..., 1], r[..., 2]
    lat = np.degrees(np.arctan2(z, np.hypot(x, y)))
    lon = np.degrees(np.arctan2(y, x))
    return lat, lon


def local_km_to_geodetic(
    east_km: np.ndarray,
    north_km: np.ndarray,
    *,
    center_lat_deg: float,
    center_lon_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Flat local offsets at the area centre to lat/lon degrees.

    Same small-area approximation as ``family_b_geometry.py:225-239``.
    """
    km_per_deg_lon = KM_PER_DEG_LAT * math.cos(math.radians(center_lat_deg))
    lat = center_lat_deg + np.asarray(north_km, dtype=np.float64) / KM_PER_DEG_LAT
    lon = center_lon_deg + np.asarray(east_km, dtype=np.float64) / km_per_deg_lon
    return lat, lon


def look_angles(
    sat_ecef_km: np.ndarray,
    ground_ecef_km: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(slant_range_km, elevation_deg, off_nadir_deg)``.

    ``sat_ecef_km`` broadcasts against ``ground_ecef_km`` on all leading
    axes.  Elevation is measured from the local horizontal plane at the
    ground point; off-nadir is measured at the satellite from its own nadir.
    """
    sat = np.asarray(sat_ecef_km, dtype=np.float64)
    gnd = np.asarray(ground_ecef_km, dtype=np.float64)

    delta = sat - gnd
    slant = np.linalg.norm(delta, axis=-1)
    up = gnd / np.linalg.norm(gnd, axis=-1, keepdims=True)
    sin_el = np.sum(delta * up, axis=-1) / np.maximum(slant, 1e-12)
    elevation = np.degrees(np.arcsin(np.clip(sin_el, -1.0, 1.0)))

    # Angle at the satellite between "down to the ground point" (-delta) and
    # its own nadir (-sat/|sat|):
    #   cos(off_nadir) = <-delta, -sat/|sat|> / slant = <delta, sat> / (|sat|*slant)
    sat_norm = np.maximum(np.linalg.norm(sat, axis=-1), 1e-12)
    cos_off = np.sum(delta * sat, axis=-1) / (sat_norm * np.maximum(slant, 1e-12))
    off_nadir = np.degrees(np.arccos(np.clip(cos_off, -1.0, 1.0)))
    return slant, elevation, off_nadir


def angle_between_deg(
    vertex_ecef_km: np.ndarray,
    first_ecef_km: np.ndarray,
    second_ecef_km: np.ndarray,
) -> np.ndarray:
    """Angle at ``vertex`` subtended by two points, in **degrees**.

    Degrees, not radians, and the name says so: this feeds the ITU-R S.465
    receive envelope, whose logarithm is defined on degrees.  Passing
    radians inflates the gain by ``25·log₁₀(180/π) ≈ 43.95 dB``
    (SDD §6 G-7).
    """
    vertex = np.asarray(vertex_ecef_km, dtype=np.float64)
    first = np.asarray(first_ecef_km, dtype=np.float64) - vertex
    second = np.asarray(second_ecef_km, dtype=np.float64) - vertex
    first = first / np.maximum(
        np.linalg.norm(first, axis=-1, keepdims=True), 1e-12
    )
    second = second / np.maximum(
        np.linalg.norm(second, axis=-1, keepdims=True), 1e-12
    )
    cosine = np.clip(np.sum(first * second, axis=-1), -1.0, 1.0)
    return np.degrees(np.arccos(cosine))


def horizon_off_nadir_deg(altitude_km: np.ndarray | float) -> np.ndarray:
    """Off-nadir angle to the geometric horizon: ``asin(R_E / (R_E + h))``."""
    h = np.asarray(altitude_km, dtype=np.float64)
    return np.degrees(np.arcsin(R_E_KM / (R_E_KM + h)))
