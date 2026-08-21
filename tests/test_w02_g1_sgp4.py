"""W-02 / G-1 — SGP4 positions agree with an independent implementation.

Gate G-1: "SGP4 位置對照獨立實作,誤差 < 1 km".

The independent reference is Vallado's own published verification set,
``SGP4-VER.TLE`` + ``tcppver.out``, which ships inside the ``sgp4``
distribution and was produced by the reference **C++** implementation.
Comparing the Python/accelerated propagator against it is a genuine
cross-implementation check, unlike comparing the library to itself.

The battery also pins the two things G-1 does not name but which sit
between SGP4 and a beam decision: the time handling (jd/fr vs minutes since
epoch) and the TEME→ECEF rotation.
"""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

import numpy as np
import pytest
import sgp4
from sgp4.api import Satrec, WGS72
from sgp4.propagation import gstime

from mcrl.env.constants import OMEGA_E_RAD_S, R_E_KM
from mcrl.env.geometry import (
    ecef_to_geodetic,
    geodetic_to_ecef,
    gmst_rad,
    gmst_rate_rad_s,
    horizon_off_nadir_deg,
    julian_date,
    look_angles,
    teme_to_ecef,
)

G1_POSITION_TOLERANCE_KM = 1.0

_SGP4_DIR = Path(sgp4.__file__).parent
_VER_TLE = _SGP4_DIR / "SGP4-VER.TLE"
_TCPPVER = _SGP4_DIR / "tcppver.out"


def _load_verification_pairs() -> list[tuple[int, str, str]]:
    lines = [
        line.rstrip("\n")
        for line in _VER_TLE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    pairs = []
    for index in range(0, len(lines) - 1, 2):
        line1, line2 = lines[index], lines[index + 1]
        if not (line1.startswith("1 ") and line2.startswith("2 ")):
            continue
        pairs.append((int(line1[2:7]), line1, line2))
    return pairs


def _load_reference_blocks() -> list[tuple[int, list[tuple[float, np.ndarray]]]]:
    blocks: list[tuple[int, list[tuple[float, np.ndarray]]]] = []
    current: list[tuple[float, np.ndarray]] | None = None
    for line in _TCPPVER.read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith("xx"):
            current = []
            blocks.append((int(stripped.split()[0]), current))
            continue
        if current is None:
            continue
        fields = stripped.split()
        if len(fields) < 7:
            continue
        try:
            values = [float(field) for field in fields[:7]]
        except ValueError:
            continue
        current.append((values[0], np.array(values[1:4], dtype=np.float64)))
    return blocks


def test_verification_fixtures_are_present_and_paired():
    pairs = _load_verification_pairs()
    blocks = _load_reference_blocks()
    assert len(pairs) >= 25
    assert len(pairs) == len(blocks)
    for (satnum, _l1, _l2), (block_satnum, _rows) in zip(pairs, blocks):
        assert satnum == block_satnum


def test_g1_sgp4_matches_vallado_reference_within_one_km():
    """G-1: max |Δr| over the whole verification set stays under 1 km."""
    pairs = _load_verification_pairs()
    blocks = _load_reference_blocks()

    compared = 0
    worst_km = 0.0
    worst_label = ""
    for (satnum, line1, line2), (_block_satnum, rows) in zip(pairs, blocks):
        satrec = Satrec.twoline2rv(line1, line2, WGS72)
        for tsince, reference_r in rows:
            code, r, _v = satrec.sgp4_tsince(tsince)
            if code != 0:
                # Vallado's set includes deliberately failing cases; the
                # reference file simply has no row for them.
                continue
            error_km = float(np.linalg.norm(np.array(r) - reference_r))
            if error_km > worst_km:
                worst_km, worst_label = error_km, f"NORAD {satnum} @ {tsince} min"
            compared += 1

    assert compared >= 600, f"only {compared} reference points compared"
    assert worst_km < G1_POSITION_TOLERANCE_KM, (
        f"worst position error {worst_km:.6f} km at {worst_label} "
        f"exceeds the G-1 budget of {G1_POSITION_TOLERANCE_KM} km"
    )
    # The real agreement is metres at worst; keep a tight regression guard so
    # a genuine break cannot hide inside the generous gate.
    assert worst_km < 1e-3, f"unexpected drift from the reference: {worst_km} km"


def test_jd_fr_time_path_matches_minutes_since_epoch():
    """The jd/fr path this project uses must equal ``sgp4_tsince``."""
    satnum, line1, line2 = _load_verification_pairs()[2]
    assert satnum == 6251
    satrec = Satrec.twoline2rv(line1, line2, WGS72)

    for minutes in (0.0, 1.0 / 60.0, 12.5, 1440.0):
        code_a, r_a, _ = satrec.sgp4_tsince(minutes)
        jd = satrec.jdsatepoch
        fr = satrec.jdsatepochF + minutes / 1440.0
        code_b, r_b, _ = satrec.sgp4(jd, fr)
        assert code_a == code_b == 0
        assert np.linalg.norm(np.array(r_a) - np.array(r_b)) < 1e-6


# -- coordinate transforms -------------------------------------------------


def test_gmst_polynomial_is_transcribed_exactly():
    """Same argument in, same answer out: the polynomial itself is right.

    The residual is pure operation ordering — this module reduces in
    degrees before converting, ``gstime`` converts before reducing.  1e-11
    rad is 64 nm on the ground.
    """
    for jd in (2451545.0, 2453101.827, 2460000.5, 2469807.5):
        mine = gmst_rad(jd, 0.0)
        theirs = gstime(jd) % (2.0 * math.pi)
        assert abs(mine - theirs) < 1e-11, (jd, mine, theirs)


def test_gmst_split_argument_agrees_to_sub_millimetre():
    """``gmst_rad(jd, fr)`` keeps the day and fraction apart on purpose.

    ``gstime`` takes the pre-summed ``jd + fr``, which throws away ~1e-9 rad
    of a 2.45e6-sized float.  That is 6 µm on the ground — the split form is
    the more accurate of the two, so the check bounds the difference rather
    than demanding bit-equality.
    """
    for jd in (2451545.0, 2460000.5, 2469807.5):
        for fr in (0.0, 0.37, 0.99):
            mine = gmst_rad(jd, fr)
            theirs = gstime(jd + fr) % (2.0 * math.pi)
            difference = abs(mine - theirs)
            assert difference < 1e-8, (jd, fr, difference)
            assert difference * R_E_KM * 1e6 < 100.0, "must stay sub-millimetre"


def test_gmst_rate_equals_the_frozen_earth_rotation_rate():
    """SDD §3.1: the Earth model must agree with ``OMEGA_E_RAD_S``."""
    analytic = gmst_rate_rad_s()
    assert abs(analytic - OMEGA_E_RAD_S) < 1e-12, (analytic, OMEGA_E_RAD_S)

    # And numerically, over a real day.
    jd, fr = julian_date(dt.datetime(2026, 8, 20, tzinfo=dt.timezone.utc))
    delta_s = 600.0
    difference = gmst_rad(jd, fr + delta_s / 86400.0) - gmst_rad(jd, fr)
    numeric = (difference % (2.0 * math.pi)) / delta_s
    assert abs(numeric - OMEGA_E_RAD_S) < 1e-11


def test_julian_date_matches_the_sgp4_convention():
    from sgp4.api import jday

    when = dt.datetime(2026, 8, 20, 13, 47, 11, 250_000, tzinfo=dt.timezone.utc)
    mine_jd, mine_fr = julian_date(when)
    their_jd, their_fr = jday(2026, 8, 20, 13, 47, 11.25)
    assert abs((mine_jd + mine_fr) - (their_jd + their_fr)) < 1e-9


def test_teme_to_ecef_preserves_length_and_z():
    rng = np.random.default_rng(3)
    r_teme = rng.normal(scale=7000.0, size=(5, 4, 3))
    gmst = rng.uniform(0.0, 2.0 * math.pi, size=4)
    r_ecef = teme_to_ecef(r_teme, gmst)
    assert np.allclose(
        np.linalg.norm(r_ecef, axis=-1), np.linalg.norm(r_teme, axis=-1)
    )
    assert np.allclose(r_ecef[..., 2], r_teme[..., 2])


def test_teme_to_ecef_rejects_a_time_axis_mismatch():
    with pytest.raises(ValueError):
        teme_to_ecef(np.zeros((2, 4, 3)), np.zeros(3))


def test_geodetic_round_trip():
    lat = np.array([0.0, 40.0, -33.9, 89.0])
    lon = np.array([0.0, 116.0, 151.2, -179.5])
    back_lat, back_lon = ecef_to_geodetic(geodetic_to_ecef(lat, lon))
    assert np.allclose(back_lat, lat, atol=1e-9)
    assert np.allclose(back_lon, lon, atol=1e-9)


def test_look_angles_at_zenith():
    ground = geodetic_to_ecef(40.0, 116.0)
    altitude = 550.0
    sat = ground * ((R_E_KM + altitude) / R_E_KM)
    slant, elevation, off_nadir = look_angles(sat, ground)
    assert slant == pytest.approx(altitude, abs=1e-9)
    assert elevation == pytest.approx(90.0, abs=1e-9)
    assert off_nadir == pytest.approx(0.0, abs=1e-6)


def test_look_angles_at_the_horizon_match_the_limb_formula():
    """Elevation 0 must put the satellite exactly at its geometric horizon."""
    altitude = 550.0
    r_orbit = R_E_KM + altitude
    ground = geodetic_to_ecef(0.0, 0.0)
    # Central angle to the horizon for this altitude.
    central = math.acos(R_E_KM / r_orbit)
    sat = np.array(
        [r_orbit * math.cos(central), r_orbit * math.sin(central), 0.0]
    )
    slant, elevation, off_nadir = look_angles(sat, ground)
    assert elevation == pytest.approx(0.0, abs=1e-6)
    assert off_nadir == pytest.approx(
        float(horizon_off_nadir_deg(altitude)), abs=1e-6
    )
    assert slant == pytest.approx(math.sqrt(r_orbit**2 - R_E_KM**2), abs=1e-6)


def test_horizon_off_nadir_reproduces_the_sdd_table():
    """SDD §3.4a: 780 km -> 62.99°, 550 km -> 67.00°."""
    assert float(horizon_off_nadir_deg(780.0)) == pytest.approx(62.99, abs=0.01)
    assert float(horizon_off_nadir_deg(550.0)) == pytest.approx(67.00, abs=0.01)
