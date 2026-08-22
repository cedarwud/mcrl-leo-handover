"""W-17 — (3.12a)/(3.12b) and the unique SINR (3.13).

Archive-free by construction: the interference sums are a function of
geometry and identity, so the geometry here is built by hand and put where
each property is decidable by inspection.  Anything that needed the real
ephemeris to show would be testing the ephemeris.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.antenna import (
    RX_GAIN_MAX_DBI,
    receive_gain_dbi,
    transmit_gain_linear,
)
from mcrl.env.cells import build_cell_grid
from mcrl.env.constants import R_E_KM
from mcrl.env.geometry import angle_between_deg
from mcrl.env.interference import (
    RadiatingBeams,
    beam_field_at_users,
    build_radiating_beams,
    candidate_interference_w,
    candidate_received_power_terms,
    co_channel_interference,
    empty_radiating_beams,
    received_power_terms,
)
from mcrl.env.link_budget import noise_power_w, sinr
from mcrl.env.pointing import beam_off_axis_deg
from mcrl.errors import MCRLContractError

ALTITUDE_KM = 483.0


@pytest.fixture(scope="module")
def grid():
    return build_cell_grid(altitude_km=ALTITUDE_KM)


def _overhead(grid, cell: int, *, altitude_km: float = ALTITUDE_KM):
    """A satellite directly above a cell centre."""
    centre = grid.centers_ecef_km[cell]
    return centre * ((R_E_KM + altitude_km) / R_E_KM)


def _cells_of_colour(grid, colour: int, count: int) -> list[int]:
    return [
        int(cell)
        for cell in np.flatnonzero(grid.colors == colour)[:count]
    ]


def _beams(grid, entries, *, power_w=2.0):
    """``entries`` is a list of ``(norad_id, cell_id, satellite_ecef)``."""
    return RadiatingBeams(
        norad_ids=np.array([e[0] for e in entries], dtype=np.int64),
        cell_ids=np.array([e[1] for e in entries], dtype=np.int64),
        satellite_ecef_km=np.stack([e[2] for e in entries]),
        cell_centre_ecef_km=grid.centers_ecef_km[
            np.array([e[1] for e in entries], dtype=np.int64)
        ],
        colors=grid.colors[np.array([e[1] for e in entries], dtype=np.int64)],
        power_w=np.full(len(entries), float(power_w)),
    )


def _terms(grid, users, beams, *, serving_norad, serving_ecef):
    field = beam_field_at_users(user_ecef_km=users, radiating=beams)
    return received_power_terms(
        field,
        beams,
        user_ecef_km=users,
        boresight_satellite_ecef_km=serving_ecef,
        boresight_norad_ids=serving_norad,
    )


# -- the colour gate -------------------------------------------------------


def test_only_co_colour_beams_interfere(grid):
    """"干擾只來自與服務波束同色且已啟用的其他波束"."""
    same = _cells_of_colour(grid, 0, 2)
    other = _cells_of_colour(grid, 1, 1)[0]
    sat_a, sat_b, sat_c = (
        _overhead(grid, same[0]),
        _overhead(grid, same[1]),
        _overhead(grid, other),
    )
    users = grid.centers_ecef_km[same[0]][None, :]

    beams = _beams(grid, [(1, same[0], sat_a), (2, same[1], sat_b), (3, other, sat_c)])
    terms = _terms(
        grid,
        users,
        beams,
        serving_norad=np.array([1]),
        serving_ecef=sat_a[None, :],
    )
    split = co_channel_interference(
        terms,
        beams,
        wanted_norad_ids=np.array([1]),
        wanted_cell_ids=np.array([same[0]]),
        wanted_colors=np.array([grid.colors[same[0]]]),
    )
    # The different-colour beam is orthogonal: it contributes exactly zero,
    # not "a small amount".
    without_other = _beams(grid, [(1, same[0], sat_a), (2, same[1], sat_b)])
    terms2 = _terms(
        grid,
        users,
        without_other,
        serving_norad=np.array([1]),
        serving_ecef=sat_a[None, :],
    )
    split2 = co_channel_interference(
        terms2,
        without_other,
        wanted_norad_ids=np.array([1]),
        wanted_cell_ids=np.array([same[0]]),
        wanted_colors=np.array([grid.colors[same[0]]]),
    )
    assert split.total_w[0] == split2.total_w[0]
    assert split.total_w[0] > 0.0


# -- z-gated, never load-weighted -----------------------------------------


def test_the_sum_is_gated_by_z_and_never_weighted_by_load(grid):
    """"求和以啟用指示 z 為門檻,而不是以其上載有幾位使用者為權重".

    The radiating set carries no load at all, which is the structural
    guarantee: there is no field a load could be read from.  What this pins
    is that the *power* it does carry is the beam's single ``p_{s,v}`` — so
    an eight-user beam and a one-user beam radiating the same power produce
    identical interference.
    """
    assert not hasattr(RadiatingBeams, "load")
    same = _cells_of_colour(grid, 0, 2)
    sat_a, sat_b = _overhead(grid, same[0]), _overhead(grid, same[1])
    users = grid.centers_ecef_km[same[0]][None, :]
    beams = _beams(grid, [(1, same[0], sat_a), (2, same[1], sat_b)])
    terms = _terms(
        grid, users, beams, serving_norad=np.array([1]), serving_ecef=sat_a[None, :]
    )
    fields = [name for name in RadiatingBeams.__dataclass_fields__]
    assert "power_w" in fields
    assert not any("load" in name or "count" in name for name in fields)
    assert terms.shape == (1, 2)


# -- (3.12a) excludes v'=v; (3.12b) does not ------------------------------


def test_the_same_cell_on_another_satellite_is_the_dominant_term(grid):
    """(3.12b)'s inner sum has no ``v' ≠ v``, and dropping it would be fatal.

    Two satellites pointing at one cell put a victim on both boresights at
    once: full ``G^T`` from the interferer and full ``G^R`` at the terminal.
    That is the worst co-channel case there is, and it is legal.
    """
    same = _cells_of_colour(grid, 0, 2)
    victim_cell, neighbour_cell = same[0], same[1]
    sat_a = _overhead(grid, victim_cell)
    sat_b = _overhead(grid, neighbour_cell)
    users = grid.centers_ecef_km[victim_cell][None, :]

    beams = _beams(
        grid,
        [
            (1, victim_cell, sat_a),      # the wanted beam
            (2, victim_cell, sat_b),      # SAME cell, different satellite
            (1, neighbour_cell, sat_a),   # same satellite, different cell
        ],
    )
    terms = _terms(
        grid, users, beams, serving_norad=np.array([1]), serving_ecef=sat_a[None, :]
    )
    split = co_channel_interference(
        terms,
        beams,
        wanted_norad_ids=np.array([1]),
        wanted_cell_ids=np.array([victim_cell]),
        wanted_colors=np.array([grid.colors[victim_cell]]),
    )
    # The wanted beam itself never appears in its own interference.
    assert split.intra_w[0] == pytest.approx(terms[0, 2])
    # The same-cell, different-satellite beam is the whole inter term.
    assert split.inter_w[0] == pytest.approx(terms[0, 1])
    assert split.inter_w[0] > 0.0


def test_a_beam_never_interferes_with_itself(grid):
    cell = _cells_of_colour(grid, 0, 1)[0]
    sat = _overhead(grid, cell)
    users = grid.centers_ecef_km[cell][None, :]
    beams = _beams(grid, [(1, cell, sat)])
    terms = _terms(
        grid, users, beams, serving_norad=np.array([1]), serving_ecef=sat[None, :]
    )
    split = co_channel_interference(
        terms,
        beams,
        wanted_norad_ids=np.array([1]),
        wanted_cell_ids=np.array([cell]),
        wanted_colors=np.array([grid.colors[cell]]),
    )
    assert split.total_w[0] == 0.0


# -- each term uses the INTERFERER's own angle ----------------------------


def test_each_term_uses_the_interferers_own_off_axis_angle(grid):
    """"每一項都以該干擾波束自己的偏軸角與線性鏈路因子計算".

    Point one satellite at two different cells while everything else is held
    fixed.  Only the interferer's own boresight moved, so only its own
    ``G^T`` may change — and it must, or the angle is not being read.
    """
    colour_cells = _cells_of_colour(grid, 0, 3)
    victim_cell = colour_cells[0]
    users = grid.centers_ecef_km[victim_cell][None, :]
    sat_wanted = _overhead(grid, victim_cell)
    sat_other = _overhead(grid, colour_cells[1])

    first = _beams(grid, [(9, colour_cells[1], sat_other)])
    second = _beams(grid, [(9, colour_cells[2], sat_other)])
    kwargs = dict(
        serving_norad=np.array([1]), serving_ecef=sat_wanted[None, :]
    )
    first_term = _terms(grid, users, first, **kwargs)[0, 0]
    second_term = _terms(grid, users, second, **kwargs)[0, 0]

    # Everything but the interferer's boresight is identical, so the ratio
    # must be EXACTLY the ratio of its own G^T at the two off-axis angles.
    # Stated as an identity rather than as "the nearer one is stronger":
    # cell ids order the lattice, not the distance to this victim, and the
    # side lobes are not monotonic in theta anyway.
    angles = beam_off_axis_deg(
        user_ecef_km=users,
        satellite_ecef_km=np.stack([sat_other, sat_other]),
        beam_centre_ecef_km=grid.centers_ecef_km[
            np.array([colour_cells[1], colour_cells[2]])
        ],
    )
    gains = transmit_gain_linear(angles[0])
    assert first_term / second_term == pytest.approx(gains[0] / gains[1], rel=1e-12)
    assert first_term != second_term


# -- P-10 through the interference path -----------------------------------


def test_a_co_satellite_interferer_gets_boresight_receive_gain(grid):
    """P-10, and *why* this implementation satisfies it structurally.

    The receive envelope is evaluated on the angle **at the user between two
    satellites**.  For two beams of one satellite that angle is zero by
    construction, so they get ``G_R,max`` whether or not the override fires
    — the override is a belt-and-braces against a caller that supplies
    identities and positions that disagree.

    What P-10 warns about is evaluating the envelope on the **inter-beam**
    angle instead, which is what a reader reaching for "the angle between
    the wanted beam and the interferer" would compute.  The size of that
    mistake is measured here rather than asserted.
    """
    cells = _cells_of_colour(grid, 0, 2)
    sat = _overhead(grid, cells[0])
    users = grid.centers_ecef_km[cells[0]][None, :]

    term = _terms(
        grid,
        users,
        _beams(grid, [(1, cells[1], sat)]),
        serving_norad=np.array([1]),
        serving_ecef=sat[None, :],
    )[0, 0]
    without_override = _terms(
        grid,
        users,
        _beams(grid, [(1, cells[1], sat)]),
        serving_norad=np.array([-1]),  # no boresight -> no override
        serving_ecef=sat[None, :],
    )[0, 0]
    assert term == pytest.approx(without_override), (
        "the separation is already zero between two beams of one satellite"
    )

    # The error P-10 names: the inter-BEAM angle at the user.
    inter_beam_deg = float(
        angle_between_deg(
            users[0],
            grid.centers_ecef_km[cells[0]],
            grid.centers_ecef_km[cells[1]],
        )
    )
    shortfall_db = RX_GAIN_MAX_DBI - float(
        receive_gain_dbi(np.array([inter_beam_deg]))[0]
    )
    assert shortfall_db > 10.0, (
        "using the inter-beam angle would under-state this interferer by "
        f"{shortfall_db:.1f} dB"
    )


def test_p10_matters_once_the_interferer_is_somewhere_else(grid):
    """The 15-45 dB error, exhibited through the sum rather than asserted."""
    cells = _cells_of_colour(grid, 0, 2)
    sat_serving = _overhead(grid, cells[0])
    sat_far = _overhead(grid, cells[1], altitude_km=ALTITUDE_KM * 1.4)
    users = grid.centers_ecef_km[cells[0]][None, :]

    kwargs = dict(serving_norad=np.array([1]), serving_ecef=sat_serving[None, :])
    as_co_satellite = _terms(
        grid, users, _beams(grid, [(1, cells[1], sat_far)]), **kwargs
    )[0, 0]
    as_cross_satellite = _terms(
        grid, users, _beams(grid, [(2, cells[1], sat_far)]), **kwargs
    )[0, 0]

    separation_db = RX_GAIN_MAX_DBI - float(
        receive_gain_dbi(
            np.array(
                [
                    np.degrees(
                        np.arccos(
                            np.dot(
                                (sat_serving - users[0])
                                / np.linalg.norm(sat_serving - users[0]),
                                (sat_far - users[0])
                                / np.linalg.norm(sat_far - users[0]),
                            )
                        )
                    )
                ]
            )
        )[0]
    )
    assert separation_db > 0.0
    ratio_db = 10.0 * np.log10(as_co_satellite / as_cross_satellite)
    assert ratio_db == pytest.approx(separation_db, abs=1e-9)


# -- global scope ----------------------------------------------------------


def test_an_interferer_outside_the_victims_window_still_counts(grid):
    """(3.12b) sums over ``s' ∈ 𝒮``, not over the four-slot candidate table.

    The window is a representation device for a fixed-width network output;
    a satellite does not stop radiating because it fell out of somebody's
    table.
    """
    cells = _cells_of_colour(grid, 0, 2)
    sat_serving = _overhead(grid, cells[0])
    stranger = _overhead(grid, cells[1])
    users = grid.centers_ecef_km[cells[0]][None, :]

    beams = _beams(grid, [(1, cells[0], sat_serving), (77777, cells[1], stranger)])
    terms = _terms(
        grid,
        users,
        beams,
        serving_norad=np.array([1]),
        serving_ecef=sat_serving[None, :],
    )
    split = co_channel_interference(
        terms,
        beams,
        wanted_norad_ids=np.array([1]),
        wanted_cell_ids=np.array([cells[0]]),
        wanted_colors=np.array([grid.colors[cells[0]]]),
    )
    assert split.inter_w[0] > 0.0


# -- the empty and unserved cases -----------------------------------------


def test_an_all_dark_system_has_exactly_zero_interference(grid):
    beams = empty_radiating_beams()
    users = grid.centers_ecef_km[:3]
    field = beam_field_at_users(user_ecef_km=users, radiating=beams)
    terms = received_power_terms(
        field,
        beams,
        user_ecef_km=users,
        boresight_satellite_ecef_km=users,
        boresight_norad_ids=np.full(3, -1, dtype=np.int64),
    )
    split = co_channel_interference(
        terms,
        beams,
        wanted_norad_ids=np.full(3, -1, dtype=np.int64),
        wanted_cell_ids=np.full(3, -1, dtype=np.int64),
        wanted_colors=np.full(3, -1, dtype=np.int64),
    )
    assert split.total_w.tolist() == [0.0, 0.0, 0.0]
    # And the SINR of a link against pure noise is finite, not a divide by 0.
    assert float(sinr(np.array(1e-12), np.array(0.0), noise_power_w())) > 0.0


def test_an_unserved_user_gets_no_interference_rather_than_the_whole_sum(grid):
    cells = _cells_of_colour(grid, 0, 2)
    sat = _overhead(grid, cells[0])
    users = grid.centers_ecef_km[cells[:2]]
    beams = _beams(grid, [(1, cells[0], sat), (1, cells[1], sat)])
    terms = _terms(
        grid,
        users,
        beams,
        serving_norad=np.array([1, -1]),
        serving_ecef=np.stack([sat, users[1]]),
    )
    split = co_channel_interference(
        terms,
        beams,
        wanted_norad_ids=np.array([1, -1]),
        wanted_cell_ids=np.array([cells[0], -1]),
        wanted_colors=np.array([grid.colors[cells[0]], -1]),
    )
    assert split.total_w[0] > 0.0
    assert split.total_w[1] == 0.0


# -- the candidate-table view agrees with the realised one -----------------


def test_the_candidate_view_reproduces_the_realised_sum(grid):
    """The two paths through the same sums must not drift apart.

    ``candidate_interference_w`` exists so (4.1) can ask about all 28
    candidates at once; if it disagreed with :func:`co_channel_interference`
    on the one candidate that was actually taken, the state and the reward
    would describe different systems.
    """
    cells = _cells_of_colour(grid, 0, 3)
    sat_a, sat_b = _overhead(grid, cells[0]), _overhead(grid, cells[1])
    users = grid.centers_ecef_km[cells[0]][None, :]
    beams = _beams(
        grid, [(1, cells[0], sat_a), (1, cells[1], sat_a), (2, cells[2], sat_b)]
    )
    field = beam_field_at_users(user_ecef_km=users, radiating=beams)

    realised = co_channel_interference(
        received_power_terms(
            field,
            beams,
            user_ecef_km=users,
            boresight_satellite_ecef_km=sat_a[None, :],
            boresight_norad_ids=np.array([1]),
        ),
        beams,
        wanted_norad_ids=np.array([1]),
        wanted_cell_ids=np.array([cells[0]]),
        wanted_colors=np.array([grid.colors[cells[0]]]),
    )

    # One satellite slot, two beam slots: the taken candidate and another.
    candidate_terms = candidate_received_power_terms(
        field,
        beams,
        user_ecef_km=users,
        candidate_satellite_ecef_km=sat_a[None, None, :],
        candidate_norad_ids=np.array([[1]]),
    )
    candidate = candidate_interference_w(
        candidate_terms,
        beams,
        candidate_norad_ids=np.array([[1, 1]]),
        candidate_cell_ids=np.array([[cells[0], cells[1]]]),
        candidate_colors=grid.colors[np.array([[cells[0], cells[1]]])],
    )
    assert candidate[0, 0] == pytest.approx(realised.total_w[0], rel=1e-12)
    # The other candidate sees a different sum: its own beam drops out and
    # the one it would have left joins.
    assert candidate[0, 1] != candidate[0, 0]


# -- fail-closed -----------------------------------------------------------


def test_one_beam_may_not_appear_twice(grid):
    cell = _cells_of_colour(grid, 0, 1)[0]
    sat = _overhead(grid, cell)
    with pytest.raises(MCRLContractError, match="twice"):
        _beams(grid, [(1, cell, sat), (1, cell, sat)])


def test_a_radiating_satellite_with_no_position_is_refused(grid):
    cell = _cells_of_colour(grid, 0, 1)[0]
    with pytest.raises(MCRLContractError, match="no position"):
        build_radiating_beams(
            beam_norad_ids=np.array([42], dtype=np.int64),
            beam_cell_ids=np.array([cell], dtype=np.int64),
            beam_power_w=np.array([1.0]),
            satellite_ecef_by_norad={},
            grid=grid,
        )
