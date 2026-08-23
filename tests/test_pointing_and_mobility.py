"""Beam-pointing geometry (§3.1.2) and §IV mobility.

Both are fully determined by the paper, so they are built ahead of the
outstanding physics decisions (docs/CONTROLLER-QUESTIONS-2026-08-22.md).
Nothing here depends on the power model, the EE denominator, or the state
dimension.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcrl.env.cells import build_cell_grid
from mcrl.env.constants import AREA_EW_KM, AREA_NS_KM, R_E_KM
from mcrl.env.geometry import geodetic_to_ecef, look_angles
from mcrl.env.mobility import (
    MAX_TURN_RAD,
    USER_SPEED_KMH,
    MobilityConfig,
    RandomWanderingUsers,
)
from mcrl.env.pointing import (
    beam_off_axis_deg,
    candidate_geometry,
    off_axis_angle_deg,
    slant_range_from_elevation_km,
)
from mcrl.errors import MCRLContractError


# -- eq. (3.5): slant range ------------------------------------------------


def test_the_closed_form_equals_the_vector_norm():
    """(3.5) is the paper's form; both must give the same distance."""
    ground = geodetic_to_ecef(40.0, 116.0)
    up = ground / np.linalg.norm(ground)
    east = np.cross(np.array([0.0, 0.0, 1.0]), up)
    east /= np.linalg.norm(east)

    for altitude in (426.0, 483.0, 540.0):
        orbit_radius = R_E_KM + altitude
        for central_deg in (0.0, 3.0, 8.0, 15.0, 20.0):
            central = math.radians(central_deg)
            satellite = orbit_radius * (
                math.cos(central) * up + math.sin(central) * east
            )
            slant, elevation, _ = look_angles(satellite, ground)
            closed_form = float(
                slant_range_from_elevation_km(elevation, np.array(altitude))
            )
            assert closed_form == pytest.approx(float(slant), abs=1e-6)


def test_zenith_slant_range_is_the_altitude():
    assert float(
        slant_range_from_elevation_km(np.array(90.0), np.array(483.0))
    ) == pytest.approx(483.0, abs=1e-9)


def test_slant_range_grows_as_elevation_falls():
    values = slant_range_from_elevation_km(
        np.array([90.0, 45.0, 25.0, 10.0, 0.0]), np.array(483.0)
    )
    assert np.all(np.diff(values) > 0.0)


def test_a_non_positive_altitude_is_refused():
    with pytest.raises(MCRLContractError, match="altitude"):
        slant_range_from_elevation_km(np.array(30.0), np.array(0.0))


# -- eq. (3.6): off-axis angle --------------------------------------------


def test_a_user_at_the_beam_centre_is_on_boresight():
    """Zero to within arccos's conditioning, which is ~1e-6 deg here.

    ``arccos`` is ill-conditioned near 1: ``cos θ ≈ 1 − θ²/2``, so a 1e-16
    error in the cosine surfaces as ~1e-8 rad.  Harmless downstream —
    ``μ = 2.07123 sin θ / sin(θ_3dB/2)`` maps 1e-6 deg to μ ≈ 1e-6, where
    the pattern is 1 to fifteen digits.
    """
    ground = geodetic_to_ecef(40.0, 116.0)
    satellite = ground * ((R_E_KM + 483.0) / R_E_KM)
    angle = float(off_axis_angle_deg(satellite, ground, ground))
    assert angle == pytest.approx(0.0, abs=1e-5)

    from mcrl.env.antenna import G0_LINEAR, transmit_gain_linear

    assert float(transmit_gain_linear(np.array(angle))) == pytest.approx(
        G0_LINEAR, rel=1e-12
    )


def test_the_off_axis_angle_is_measured_at_the_satellite():
    """Not at the user: the same displacement subtends far less from orbit."""
    ground = geodetic_to_ecef(40.0, 116.0)
    satellite = ground * ((R_E_KM + 483.0) / R_E_KM)
    up = ground / np.linalg.norm(ground)
    east = np.cross(np.array([0.0, 0.0, 1.0]), up)
    east /= np.linalg.norm(east)

    offset_km = 14.0  # about one cell radius at 483 km
    user = ground + offset_km * east
    angle = float(off_axis_angle_deg(satellite, ground, user))
    # atan(14 / 483) = 1.66 deg — exactly the half-power half-angle.
    assert angle == pytest.approx(math.degrees(math.atan(offset_km / 483.0)), abs=0.02)
    assert angle == pytest.approx(1.66, abs=0.03)


def test_one_cell_radius_lands_on_the_half_power_point():
    """R_b = h·tan(θ_3dB/2) is exactly the offset that gives θ = θ_3dB/2."""
    grid = build_cell_grid(altitude_km=483.0)
    ground = geodetic_to_ecef(40.0, 116.0)
    satellite = ground * ((R_E_KM + 483.0) / R_E_KM)
    up = ground / np.linalg.norm(ground)
    east = np.cross(np.array([0.0, 0.0, 1.0]), up)
    east /= np.linalg.norm(east)

    user = ground + grid.cell_radius_km * east
    assert float(off_axis_angle_deg(satellite, ground, user)) == pytest.approx(
        3.32 / 2.0, abs=0.01
    )


def test_the_angle_is_returned_in_degrees():
    """G-7: the S.465 envelope and mu_of are both defined on degrees."""
    ground = geodetic_to_ecef(0.0, 0.0)
    satellite = ground * 2.0
    far = geodetic_to_ecef(0.0, 40.0)
    angle = float(off_axis_angle_deg(satellite, ground, far))
    assert angle > math.pi, "a radian-valued answer would be <= pi"
    assert 0.0 < angle < 180.0


# -- the candidate block ---------------------------------------------------


@pytest.fixture(scope="module")
def grid():
    return build_cell_grid(altitude_km=483.0)


def _scenario(grid, num_users=6, num_slots=4):
    rng = np.random.default_rng(0)
    xy = rng.uniform([-100.0, -45.0], [100.0, 45.0], size=(num_users, 2))
    anchors = grid.anchor_cell_ids(xy)
    hood = grid.neighborhood_cell_ids(anchors)

    ground = geodetic_to_ecef(40.0, 116.0)
    up = ground / np.linalg.norm(ground)
    east = np.cross(np.array([0.0, 0.0, 1.0]), up)
    east /= np.linalg.norm(east)
    north = np.cross(up, east)
    users = (
        ground[None, :]
        + xy[:, 0:1] * east[None, :]
        + xy[:, 1:2] * north[None, :]
    )
    users *= (R_E_KM / np.linalg.norm(users, axis=1, keepdims=True))

    orbit = R_E_KM + 483.0
    satellites = np.stack(
        [
            orbit * (math.cos(math.radians(a)) * up + math.sin(math.radians(a)) * east)
            for a in (0.0, 5.0, -7.0, 11.0)[:num_slots]
        ]
    )
    return users, satellites, hood


def test_the_candidate_block_has_the_right_shape(grid):
    users, satellites, hood = _scenario(grid)
    geometry = candidate_geometry(
        user_ecef_km=users,
        satellite_ecef_km=satellites,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=hood,
    )
    assert geometry.off_axis_deg.shape == (6, 4, 7)
    assert geometry.slant_range_km.shape == (6, 4)
    assert geometry.elevation_deg.shape == (6, 4)


def test_the_slant_range_carries_no_beam_index(grid):
    """The paper: "對同一顆衛星的不同波束,它的數值可以相同"."""
    users, satellites, hood = _scenario(grid)
    geometry = candidate_geometry(
        user_ecef_km=users,
        satellite_ecef_km=satellites,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=hood,
    )
    assert geometry.slant_range_km.ndim == 2
    # And it agrees with the closed form at the measured elevation.
    closed = slant_range_from_elevation_km(
        geometry.elevation_deg, np.array(483.0)
    )
    assert np.allclose(closed, geometry.slant_range_km, atol=0.5)


def test_the_anchor_is_the_ground_nearest_cell_not_the_smallest_angle(grid):
    """§4A.2 defines ``j = 0`` by GROUND proximity, and that is not the same
    thing as the smallest off-axis angle.

    The angle is measured at the satellite, so an oblique view foreshortens
    ground distance along the line of sight: a cell displaced toward the
    satellite subtends less than an equally distant one displaced across it.
    For a satellite near nadir the two coincide; off nadir they need not.

    This is a property of the definition, not a defect — but it is the kind
    of thing that gets "fixed" by someone assuming j = 0 must be the best
    beam, so it is pinned here.
    """
    users, satellites, hood = _scenario(grid)
    geometry = candidate_geometry(
        user_ecef_km=users,
        satellite_ecef_km=satellites,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=hood,
    )
    # The anchor is always CLOSE to the minimum — within a fraction of the
    # half-power half-angle — but not always equal to it.
    disagreements = 0
    for uid in range(users.shape[0]):
        for slot in range(satellites.shape[0]):
            angles = geometry.off_axis_deg[uid, slot]
            excess = float(angles[0] - np.nanmin(angles))
            assert excess >= -1e-9
            assert excess < 3.32 / 2.0
            if excess > 1e-9:
                disagreements += 1
    assert disagreements > 0, (
        "expected foreshortening to separate the two definitions at least once"
    )


def test_the_anchor_is_the_nearest_cell_on_the_ground(grid):
    """The definition §4A.2 actually gives."""
    rng = np.random.default_rng(0)
    xy = rng.uniform([-100.0, -45.0], [100.0, 45.0], size=(20, 2))
    anchors = grid.anchor_cell_ids(xy)
    for point, anchor in zip(xy, anchors.tolist()):
        distances = np.linalg.norm(grid.centers_km - point, axis=1)
        assert distances[anchor] == pytest.approx(distances.min())


def test_the_off_axis_angle_depends_on_the_satellite(grid):
    """§4A.2's orthogonality is about the CELL, not about theta."""
    users, satellites, hood = _scenario(grid)
    geometry = candidate_geometry(
        user_ecef_km=users,
        satellite_ecef_km=satellites,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=hood,
    )
    # The same cell seen from two satellites subtends different angles.
    assert not np.allclose(
        geometry.off_axis_deg[:, 0, :], geometry.off_axis_deg[:, 1, :]
    )


def test_a_missing_lattice_neighbour_yields_nan_not_cell_zero(grid):
    users, satellites, hood = _scenario(grid, num_users=2)
    hood = hood.copy()
    hood[0, 3] = -1
    geometry = candidate_geometry(
        user_ecef_km=users,
        satellite_ecef_km=satellites,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=hood,
    )
    assert np.all(np.isnan(geometry.off_axis_deg[0, :, 3]))
    assert np.all(np.isfinite(geometry.off_axis_deg[0, :, 2]))


def test_shape_violations_fail_loud(grid):
    users, satellites, hood = _scenario(grid, num_users=2)
    with pytest.raises(MCRLContractError, match=r"\(U, 3\)"):
        candidate_geometry(
            user_ecef_km=users[:, :2],
            satellite_ecef_km=satellites,
            cell_centres_ecef_km=grid.centers_ecef_km,
            neighborhood_cell_ids=hood,
        )
    with pytest.raises(MCRLContractError, match="exceeds the lattice"):
        candidate_geometry(
            user_ecef_km=users,
            satellite_ecef_km=satellites,
            cell_centres_ecef_km=grid.centers_ecef_km,
            neighborhood_cell_ids=np.full_like(hood, grid.count),
        )


# -- the interference-side companion --------------------------------------


def test_interfering_beams_use_their_own_angles(grid):
    """(3.12a)/(3.12b): each term uses the INTERFERER's own theta."""
    users, satellites, _hood = _scenario(grid, num_users=3)
    beam_satellites = np.repeat(satellites, 2, axis=0)
    beam_centres = grid.centers_ecef_km[:8]
    angles = beam_off_axis_deg(
        user_ecef_km=users,
        satellite_ecef_km=beam_satellites,
        beam_centre_ecef_km=beam_centres,
    )
    assert angles.shape == (3, 8)
    assert np.all(np.isfinite(angles))
    assert np.all((angles >= 0.0) & (angles <= 180.0))


def test_the_interference_helper_validates_its_shapes(grid):
    users, satellites, _hood = _scenario(grid, num_users=2)
    with pytest.raises(MCRLContractError, match=r"both be \(B, 3\)"):
        beam_off_axis_deg(
            user_ecef_km=users,
            satellite_ecef_km=satellites,
            beam_centre_ecef_km=grid.centers_ecef_km[:2],
        )


# -- mobility --------------------------------------------------------------


def test_the_scatter_is_the_section_IV_rectangle():
    """Not the ported 50 km circle."""
    users = RandomWanderingUsers(MobilityConfig(num_users=5000))
    xy = users.reset(np.random.default_rng(1))
    assert np.all(np.abs(xy[:, 0]) <= AREA_EW_KM / 2.0)
    assert np.all(np.abs(xy[:, 1]) <= AREA_NS_KM / 2.0)
    # It fills the corners, which a 50 km circle could not.
    assert xy[:, 0].max() > 95.0 and xy[:, 1].max() > 43.0
    assert np.hypot(xy[:, 0], xy[:, 1]).max() > 50.0


def test_the_step_length_is_thirty_kilometres_per_hour():
    config = MobilityConfig()
    assert config.speed_kmh == USER_SPEED_KMH == 30.0
    # Derived from the clock, not hard-coded: Delta-t became 30.08 s on
    # 2026-08-23 and a literal here would have asserted the old scenario
    # while claiming to assert the speed.
    assert config.step_km == pytest.approx(
        config.speed_kmh / 3600.0 * config.time_step_s
    )
    # 8.333 m was the per-step distance at Delta-t = 1 s; at 30.08 s it is
    # 250.7 m.  The invariant is the speed, so it is the speed that is
    # asserted in metres per second.
    assert config.step_km * 1000.0 / config.time_step_s == pytest.approx(
        8.333, abs=0.001
    )


def test_each_step_moves_exactly_one_step_length():
    users = RandomWanderingUsers(MobilityConfig(num_users=200))
    rng = np.random.default_rng(2)
    before = users.reset(rng)
    after = users.step(rng)
    moved = np.linalg.norm(after - before, axis=1)
    # Reflection can shorten the chord; away from the edge it is exact.
    interior = (np.abs(before[:, 0]) < 99.0) & (np.abs(before[:, 1]) < 44.0)
    assert np.allclose(moved[interior], users.config.step_km, atol=1e-12)


def test_the_turn_is_bounded():
    users = RandomWanderingUsers(MobilityConfig(num_users=500))
    rng = np.random.default_rng(3)
    users.reset(rng)
    before = users.headings_rad
    users.step(rng)
    after = users.headings_rad
    delta = np.abs((after - before + math.pi) % (2.0 * math.pi) - math.pi)
    interior = delta < math.pi  # reflection flips a heading, excluded below
    assert np.all(delta[interior] <= MAX_TURN_RAD + 1e-9)


def test_users_never_leave_the_service_area():
    users = RandomWanderingUsers(MobilityConfig(num_users=300))
    rng = np.random.default_rng(4)
    users.reset(rng)
    for _ in range(5000):
        xy = users.step(rng)
        assert np.all(np.abs(xy[:, 0]) <= AREA_EW_KM / 2.0 + 1e-9)
        assert np.all(np.abs(xy[:, 1]) <= AREA_NS_KM / 2.0 + 1e-9)


def test_reflection_does_not_pile_users_on_the_boundary():
    """Why clamping was rejected: it would bias U_{s,v} and so r3 and P3."""
    users = RandomWanderingUsers(MobilityConfig(num_users=4000))
    rng = np.random.default_rng(5)
    users.reset(rng)
    for _ in range(2000):
        users.step(rng)
    xy = users.positions_km
    near_edge = np.mean(np.abs(xy[:, 0]) > 0.95 * AREA_EW_KM / 2.0)
    # A uniform population puts 5% in the outer 5% of the width.
    assert near_edge < 0.12, f"users are hugging the edge: {near_edge:.3f}"


def test_a_long_walk_stays_roughly_uniform():
    users = RandomWanderingUsers(MobilityConfig(num_users=4000))
    rng = np.random.default_rng(6)
    users.reset(rng)
    for _ in range(3000):
        users.step(rng)
    xy = users.positions_km
    counts, _ = np.histogram(xy[:, 0], bins=10, range=(-100.0, 100.0))
    assert counts.min() > 0.6 * counts.mean()


def test_stepping_before_reset_fails_loud():
    users = RandomWanderingUsers()
    with pytest.raises(MCRLContractError, match="not been reset"):
        users.step(np.random.default_rng(0))
    with pytest.raises(MCRLContractError, match="not been reset"):
        _ = users.positions_km


def test_reset_is_deterministic_given_a_seed():
    first = RandomWanderingUsers(MobilityConfig(num_users=50)).reset(
        np.random.default_rng(7)
    )
    second = RandomWanderingUsers(MobilityConfig(num_users=50)).reset(
        np.random.default_rng(7)
    )
    assert np.array_equal(first, second)


def test_the_configuration_discloses_every_S_level_choice():
    payload = MobilityConfig().as_dict()
    assert payload["boundary"] == "reflection"
    assert "200 x 90" in str(payload["scatter"])
    assert "random wandering" in str(payload["mobility"])


# -- the angle has two consumers in two units -----------------------------


def test_theta_is_offered_in_both_units_explicitly(grid):
    """Degrees for the gain layer, radians for the state (§4.1 / G-7).

    Crossing them inflates every angle by 180/pi with nothing to catch it,
    so the conversion is a named property rather than a caller's job.
    """
    users, satellites, hood = _scenario(grid, num_users=4)
    geometry = candidate_geometry(
        user_ecef_km=users,
        satellite_ecef_km=satellites,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=hood,
    )
    assert np.allclose(
        geometry.off_axis_rad, np.radians(geometry.off_axis_deg), equal_nan=True
    )
    assert float(np.nanmax(geometry.off_axis_rad)) < float(
        np.nanmax(geometry.off_axis_deg)
    )


def test_the_state_contract_wants_radians_and_the_gain_layer_wants_degrees(grid):
    from mcrl.env.antenna import mu_of
    from mcrl.runtime.trainer_spec import TrainerConfig

    # The state encoder accepts only raw radians.
    assert TrainerConfig().theta_encoding == "raw_radians"

    # And mu_of is defined on degrees: feeding radians would shrink mu ~57x.
    degrees = np.array(3.0)
    assert float(mu_of(degrees)) > 50.0 * float(mu_of(np.radians(degrees)))
