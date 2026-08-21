"""W-06 / G-7 / G-10 — antenna patterns and their unit conventions.

G-7 exists because a parity test between two implementations cannot catch a
shared unit error: both sides would be wrong together.  So every assertion
here is an **absolute** anchor or a structural property, never a comparison
against another implementation of the same formula.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcrl.env.antenna import (
    G0_DBI,
    G0_LINEAR,
    RX_ENVELOPE_FLOOR_DEG,
    RX_ENVELOPE_SATURATION_DEG,
    RX_GAIN_FLOOR_DBI,
    RX_GAIN_MAX_DBI,
    THETA_3DB_DEG,
    apply_same_satellite_override,
    assert_degrees_not_radians,
    mu_of,
    receive_gain_dbi,
    receive_gain_linear,
    transmit_gain_dbi,
    transmit_gain_linear,
)
from mcrl.env.geometry import angle_between_deg, geodetic_to_ecef
from mcrl.errors import MCRLContractError
from mcrl.runtime.bessel import uses_miller_recursion

RADIAN_INFLATION_DB = 25.0 * math.log10(180.0 / math.pi)
"""43.95 dB — what feeding radians into the S.465 envelope buys you."""


# ---------------------------------------------------------------------------
# G-10(a) — transmit boresight anchor
# ---------------------------------------------------------------------------


def test_G10a_transmit_gain_at_boresight_is_G0():
    assert float(transmit_gain_linear(np.array(0.0))) == pytest.approx(G0_LINEAR)
    assert float(transmit_gain_dbi(np.array(0.0))) == pytest.approx(33.010, abs=1e-3)
    assert G0_DBI == pytest.approx(33.010, abs=1e-3)


# ---------------------------------------------------------------------------
# G-10(b) — the half-angle convention (P-2)
# ---------------------------------------------------------------------------


def test_G10b_the_half_power_point_falls_at_half_the_registered_HPBW():
    """The convention check that validates itself.

    ``θ_3dB = 3.32°`` is the FULL beamwidth, so the pattern must be down
    exactly 3.01 dB at ``±1.66°``.  This is stronger than asserting the code
    divides by two: it asserts the *physics* the division is there for.
    """
    half_power_deg = THETA_3DB_DEG / 2.0
    relative_db = float(transmit_gain_dbi(np.array(half_power_deg))) - G0_DBI
    assert relative_db == pytest.approx(-3.01, abs=0.02)


def test_G10b_passing_the_full_HPBW_as_the_half_angle_fails_the_anchor():
    """Feeding the full HPBW doubles the beamwidth — the P-2 failure mode."""
    wrong = float(
        transmit_gain_dbi(
            np.array(THETA_3DB_DEG / 2.0), theta_3db_deg=2.0 * THETA_3DB_DEG
        )
    ) - G0_DBI
    # Still nearly at boresight instead of 3 dB down.
    assert wrong > -1.0
    assert not (-3.03 < wrong < -2.99), "the wrong convention must not pass"

    # And the -3 dB point moves out to the full HPBW.
    doubled = float(
        transmit_gain_dbi(
            np.array(THETA_3DB_DEG), theta_3db_deg=2.0 * THETA_3DB_DEG
        )
    ) - G0_DBI
    assert doubled == pytest.approx(-3.01, abs=0.02)


def test_mu_uses_the_half_angle():
    """``μ = 2.07123·sin θ / sin(θ_3dB/2)``; at the half-power point μ = 2.07123."""
    assert float(mu_of(np.array(THETA_3DB_DEG / 2.0))) == pytest.approx(
        2.07123, rel=1e-6
    )


# ---------------------------------------------------------------------------
# G-10(c) — the numerical domain reaches Miller in real geometry
# ---------------------------------------------------------------------------


def test_G10c_the_horizon_evaluation_routes_through_miller():
    """P-1: the pattern's own worst case is past the series' safe domain."""
    horizon_plus_tilt_deg = 70.32  # 485 km horizon + 2° ring tilt
    mu = float(mu_of(np.array(horizon_plus_tilt_deg)))
    assert mu == pytest.approx(67.32, abs=0.02)
    assert uses_miller_recursion(mu)
    # And the gain that comes back is a side lobe, not an astronomical number.
    gain_db = float(transmit_gain_dbi(np.array(horizon_plus_tilt_deg))) - G0_DBI
    assert -100.0 < gain_db < -30.0


def test_transmit_gain_never_exceeds_boresight():
    angles = np.linspace(0.0, 90.0, 2000)
    gains = transmit_gain_linear(angles)
    assert np.all(gains <= G0_LINEAR * (1.0 + 1e-9))
    assert np.all(gains >= 0.0)
    assert np.all(np.isfinite(gains))


def test_the_main_lobe_falls_monotonically_to_the_first_null():
    angles = np.linspace(0.0, 1.6, 200)
    gains = transmit_gain_linear(angles)
    assert np.all(np.diff(gains) < 0.0)


def test_non_finite_angles_are_refused():
    with pytest.raises(MCRLContractError, match="finite"):
        transmit_gain_linear(np.array([0.0, float("nan")]))


# ---------------------------------------------------------------------------
# G-7 — receive envelope anchors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "separation_deg, expected_dbi",
    [(1.0, 32.0), (48.0, -10.0), (RX_ENVELOPE_SATURATION_DEG, 35.0)],
)
def test_G7_absolute_anchors(separation_deg, expected_dbi):
    assert float(receive_gain_dbi(np.array(separation_deg))) == pytest.approx(
        expected_dbi, abs=0.05
    )


def test_G7_the_saturation_and_floor_angles_are_where_the_algebra_says():
    assert RX_ENVELOPE_SATURATION_DEG == pytest.approx(0.759, abs=0.001)
    assert RX_ENVELOPE_FLOOR_DEG == pytest.approx(47.86, abs=0.01)


def test_G7_monotonicity_including_both_plateaus():
    """Non-increasing everywhere, with a flat top and a flat floor."""
    angles = np.linspace(0.0, 180.0, 4000)
    gains = receive_gain_dbi(angles)
    assert np.all(np.diff(gains) <= 1e-12)

    inside = angles <= RX_ENVELOPE_SATURATION_DEG * 0.9
    assert np.allclose(gains[inside], RX_GAIN_MAX_DBI)

    beyond = angles >= RX_ENVELOPE_FLOOR_DEG * 1.1
    assert np.allclose(gains[beyond], RX_GAIN_FLOOR_DBI)

    # And the sloped section really is 25 dB per decade.
    slope = float(receive_gain_dbi(np.array(2.0)) - receive_gain_dbi(np.array(20.0)))
    assert slope == pytest.approx(25.0, abs=0.01)


def test_G7_boresight_is_the_maximum_not_an_infinity():
    assert float(receive_gain_dbi(np.array(0.0))) == RX_GAIN_MAX_DBI
    assert float(receive_gain_linear(np.array(0.0))) == pytest.approx(
        10.0 ** (35.0 / 10.0)
    )


def test_negative_separations_are_refused():
    with pytest.raises(MCRLContractError, match="non-negative"):
        receive_gain_dbi(np.array(-1.0))


# ---------------------------------------------------------------------------
# G-7(b) — an end-to-end vector proving the geometry layer emits degrees
# ---------------------------------------------------------------------------


def test_G7b_geometry_layer_emits_degrees_end_to_end():
    """A helper-only anchor cannot catch an upstream unit regression.

    Build a real user-satellite-satellite configuration whose separation is
    known by construction, push it through the geometry layer, and require
    the answer in degrees.
    """
    user = geodetic_to_ecef(0.0, 0.0)
    # Two points 60° apart as seen from the user, by construction.
    first = user + np.array([500.0, 0.0, 0.0])
    second = user + np.array([500.0 * math.cos(math.radians(60.0)),
                              500.0 * math.sin(math.radians(60.0)), 0.0])
    separation = float(angle_between_deg(user, first, second))
    assert separation == pytest.approx(60.0, abs=1e-9)
    assert separation > math.pi, "a radian-valued answer would be <= pi"

    # 60° is past the envelope floor, so the gain must be pinned at -10 dBi.
    assert float(receive_gain_dbi(np.array(separation))) == pytest.approx(-10.0)

    # The bug this guards: the same angle in radians is 25*log10(180/pi)
    # = 43.95 dB too high, before clipping.
    in_radians = math.radians(separation)
    wrong = float(receive_gain_dbi(np.array(in_radians)))
    assert wrong - (-10.0) > 40.0

    # Below ~43.5 deg the radian value lands inside the saturation plateau,
    # so the pattern goes flat at G_R,max and loses all directivity.
    for degrees in (5.0, 20.0, 40.0):
        radians_version = float(receive_gain_dbi(np.array(math.radians(degrees))))
        assert radians_version == pytest.approx(RX_GAIN_MAX_DBI)
        assert radians_version > float(receive_gain_dbi(np.array(degrees)))


def test_G7b_a_wide_angle_set_in_radians_is_rejected_as_a_unit_error():
    wide_degrees = np.array([0.5, 12.0, 47.0, 120.0])
    assert_degrees_not_radians(wide_degrees)
    with pytest.raises(MCRLContractError, match="not an angle"):
        assert_degrees_not_radians(np.array([200.0]))


def test_the_radian_inflation_constant_is_what_the_spec_says():
    assert RADIAN_INFLATION_DB == pytest.approx(43.95, abs=0.01)


# ---------------------------------------------------------------------------
# P-10 — the same-satellite receive override
# ---------------------------------------------------------------------------


def test_P10_co_satellite_beams_get_full_boresight_gain():
    """Every beam of the serving satellite arrives from the same direction."""
    # Two satellites, three beams each; user 0 is served by slot 0.
    satellite_of_beam = np.array([0, 0, 0, 1, 1, 1])
    serving_slot = np.array([0])
    # Envelope computed from inter-BEAM angles — the wrong thing to do.
    inter_beam_angles = np.array([[0.0, 3.0, 6.0, 30.0, 33.0, 36.0]])
    envelope = receive_gain_linear(inter_beam_angles)

    corrected = apply_same_satellite_override(
        envelope, satellite_of_beam, serving_slot
    )
    full = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
    assert np.allclose(corrected[0, :3], full)
    # Cross-satellite beams keep the envelope.
    assert np.allclose(corrected[0, 3:], envelope[0, 3:])


def test_P10_the_error_it_prevents_is_15_to_45_dB():
    """Quantify the under-estimate SDD §3.7 P-10 warns about."""
    one_cell_away = float(receive_gain_dbi(np.array(3.0)))
    far_side_lobe = float(receive_gain_dbi(np.array(60.0)))
    assert RX_GAIN_MAX_DBI - one_cell_away == pytest.approx(15.0, abs=1.0)
    assert RX_GAIN_MAX_DBI - far_side_lobe == pytest.approx(45.0, abs=0.5)


def test_P10_leaves_unserved_users_alone():
    satellite_of_beam = np.array([0, 0, 1, 1])
    envelope = receive_gain_linear(np.array([[0.0, 3.0, 30.0, 33.0]] * 2))
    corrected = apply_same_satellite_override(
        envelope, satellite_of_beam, np.array([0, -1])
    )
    assert np.allclose(corrected[1], envelope[1])
    assert not np.allclose(corrected[0], envelope[0])


def test_P10_shape_mismatches_fail_loud():
    with pytest.raises(MCRLContractError, match="shape"):
        apply_same_satellite_override(
            np.ones((2, 4)), np.array([0, 0, 1]), np.array([0, 0])
        )
    with pytest.raises(MCRLContractError, match="serving_slot"):
        apply_same_satellite_override(
            np.ones((2, 4)), np.array([0, 0, 1, 1]), np.array([0])
        )
