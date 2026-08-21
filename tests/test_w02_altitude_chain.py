"""W-02 — the altitude-dependent chain, recomputed rather than quoted.

SDD §2.4 (F3) and §3.4a publish two altitude rows, 780 km and 550 km, and
every downstream number in the design hangs off them.  ``docs/
EPHEMERIS-NOTES.md`` adds a third row at the altitude actually measured in
the TLE corpus (~485 km).  These tests reproduce the published rows from
first principles, which is what makes the third row trustworthy: the same
formulas, applied to a measured input.

This also discharges the re-verification the live source demanded:

    ``angle_aware_ee.py:938-953``: "a future scenario change that lowers
    altitude ... must re-verify mu_ceiling < _BESSEL_SERIES_MAX_ABS_X"
"""

from __future__ import annotations

import math

import pytest

from mcrl.env.geometry import horizon_off_nadir_deg

THETA_3DB_DEG = 3.32
"""**P'** — HOBS full HPBW.  SDD §3.4b: the pattern takes the HALF angle."""

HALF_HPBW_RAD = math.radians(THETA_3DB_DEG / 2.0)

BESSEL_SERIES_MAX_ABS_X = 34.0
"""``angle_aware_ee.py``: above this the ascending series cancels catastrophically."""

RING_TILT_DEG = 2.0
SERVICE_AREA_KM2 = 200.0 * 90.0
COVERAGE_TARGET = 0.95
GUARD_RING_FACTOR = 1.5

# Measured from the corpus; see docs/EPHEMERIS-NOTES.md §5.
MEASURED_VISIBLE_ALTITUDE_P50_KM = 485.0


def beam_radius_km(altitude_km: float) -> float:
    return altitude_km * math.tan(HALF_HPBW_RAD)


def hex_cell_area_km2(altitude_km: float) -> float:
    """Hexagon of inradius ``R_b``: ``2√3 R_b²`` (reproduces SDD's 1770/880)."""
    return 2.0 * math.sqrt(3.0) * beam_radius_km(altitude_km) ** 2


def cells_for_coverage(altitude_km: float) -> tuple[float, float]:
    bare = SERVICE_AREA_KM2 * COVERAGE_TARGET / hex_cell_area_km2(altitude_km)
    return bare, bare * GUARD_RING_FACTOR


def mu_ceiling(altitude_km: float, *, ring_tilt_deg: float = RING_TILT_DEG) -> float:
    """Worst-case Bessel argument in this paper's HALF-angle convention."""
    horizon = float(horizon_off_nadir_deg(altitude_km))
    return (
        2.07123 * math.sin(math.radians(horizon + ring_tilt_deg)) / math.sin(HALF_HPBW_RAD)
    )


@pytest.mark.parametrize(
    "altitude_km, r_b_km, area_km2, cells, guarded",
    [
        (780.0, 22.60, 1770.0, 9.7, 14.5),
        (550.0, 15.94, 880.0, 19.4, 29.1),
    ],
)
def test_reproduces_the_published_coverage_table(
    altitude_km, r_b_km, area_km2, cells, guarded
):
    """SDD §2.4 F3's table, recomputed."""
    assert beam_radius_km(altitude_km) == pytest.approx(r_b_km, abs=0.01)
    assert hex_cell_area_km2(altitude_km) == pytest.approx(area_km2, rel=1e-3)
    bare, with_guard = cells_for_coverage(altitude_km)
    assert bare == pytest.approx(cells, abs=0.05)
    assert with_guard == pytest.approx(guarded, abs=0.05)


@pytest.mark.parametrize(
    "altitude_km, horizon_deg, mu",
    [(780.0, 62.99, 64.80), (550.0, 67.00, 66.75)],
)
def test_reproduces_the_published_bessel_table(altitude_km, horizon_deg, mu):
    """SDD §3.4a's table, recomputed."""
    assert float(horizon_off_nadir_deg(altitude_km)) == pytest.approx(
        horizon_deg, abs=0.01
    )
    assert mu_ceiling(altitude_km) == pytest.approx(mu, abs=0.02)


def test_p1_miller_routing_still_mandatory_at_the_measured_altitude():
    """P-1 / W-15 / G-10 re-verification at the altitude actually measured.

    Lowering the altitude widens the horizon cone, so ``μ`` goes **up**.
    The conclusion is therefore stronger than the SDD's, not weaker.
    """
    measured = mu_ceiling(MEASURED_VISIBLE_ALTITUDE_P50_KM)
    assert measured > BESSEL_SERIES_MAX_ABS_X
    assert measured > mu_ceiling(550.0) > mu_ceiling(780.0)
    assert measured == pytest.approx(67.32, abs=0.02)


def test_v_39_still_covers_the_measured_altitude_but_barely():
    """F5 derived ``V=39`` from 29.1 cells at 550 km.  At 485 km it is 37.5."""
    _bare_550, guarded_550 = cells_for_coverage(550.0)
    bare, guarded = cells_for_coverage(MEASURED_VISIBLE_ALTITUDE_P50_KM)
    assert bare == pytest.approx(25.0, abs=0.1)
    assert guarded == pytest.approx(37.5, abs=0.1)
    assert guarded < 39.0, "V=39 would no longer cover the service area"
    assert guarded > guarded_550, "lower altitude must need more cells"
    # The margin F5 relied on has all but gone: 34% -> 4%.
    assert (39.0 - guarded) / 39.0 < 0.05


def test_beam_radius_uses_the_half_angle_convention():
    """SDD §3.4b: passing the full HPBW would double the footprint."""
    half = beam_radius_km(550.0)
    full = 550.0 * math.tan(math.radians(THETA_3DB_DEG))
    assert full > 1.99 * half
    assert half == pytest.approx(15.94, abs=0.01)
