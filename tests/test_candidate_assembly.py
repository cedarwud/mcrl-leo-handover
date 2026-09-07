"""Per-step candidate assembly against the real ephemeris (§4A).

Everything up to, but not including, the physics.  The link-feasibility mask
term is deliberately absent — it needs the power model, which is still open
— so the mask built here is an UPPER BOUND on the true candidate set.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import (
    CONTRACT_STATE_DIM,
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
)
from mcrl.env.candidates import resolve_candidates
from mcrl.env.cells import build_cell_grid
from mcrl.env.constants import (
    AREA_CENTER_LAT_DEG,
    AREA_CENTER_LON_DEG,
    R_E_KM,
    TLE_ROOT_DEFAULT,
)
from mcrl.env.d2 import D2Config, D2Tracker
from mcrl.env.dwell import DwellConfig, DwellController
from mcrl.env.ephemeris import (
    SatelliteSet,
    select_elements,
    service_area_center_ecef,
    step_times,
)
from mcrl.env.geometry import geodetic_to_ecef, range_rate_km_s
from mcrl.env.mobility import MobilityConfig, RandomWanderingUsers
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError

_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)

START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
ALTITUDE_KM = 483.0
NUM_USERS = 12


def _local_frame():
    centre = geodetic_to_ecef(AREA_CENTER_LAT_DEG, AREA_CENTER_LON_DEG)
    up = centre / np.linalg.norm(centre)
    east = np.cross(np.array([0.0, 0.0, 1.0]), up)
    east /= np.linalg.norm(east)
    north = np.cross(up, east)
    return centre, east, north


def _users_ecef(xy_km):
    centre, east, north = _local_frame()
    points = (
        centre[None, :] + xy_km[:, 0:1] * east[None, :] + xy_km[:, 1:2] * north[None, :]
    )
    return points * (R_E_KM / np.linalg.norm(points, axis=1, keepdims=True))


@pytest.fixture(scope="module")
def scene():
    archive = TleArchive(_ARCHIVE)
    config = D2Config()
    warmup = config.warmup_steps
    origin = START - dt.timedelta(seconds=warmup * config.time_step_s)
    jd, fr = step_times(origin, 2 + warmup)

    satellites = SatelliteSet(select_elements(archive, START).records)
    subset = satellites.subset(satellites.healthy_indices(jd, fr))
    position, velocity = subset.propagate_ecef_state(jd, fr)

    grid = build_cell_grid(altitude_km=ALTITUDE_KM)
    mobility = RandomWanderingUsers(MobilityConfig(num_users=NUM_USERS))
    xy = mobility.reset(np.random.default_rng(0))
    users = _users_ecef(xy)

    tracker = D2Tracker(subset.norad_ids, NUM_USERS, config)
    altitude = np.linalg.norm(position, axis=-1) - R_E_KM  # (S, T), not axis=1

    def measure(column):
        delta = position[None, :, column, :] - users[:, None, :]
        slant = np.linalg.norm(delta, axis=-1)
        rate = np.einsum(
            "usc,usc->us",
            np.broadcast_to(velocity[None, :, column, :], delta.shape),
            delta / np.maximum(slant[..., None], 1e-12),
        )
        return slant, rate

    # The warm-up window is TTT-sized and TTT now lives on the 640 ms
    # measurement clock, so it is more than one column (ruling 2026-08-23).
    warm = [measure(column) for column in range(warmup)]
    tracker.prime(
        slant_range_km=np.stack([s for s, _ in warm], axis=2),
        altitude_km=altitude[:, :warmup],
        range_rate_km_s=np.stack([r for _, r in warm], axis=2),
    )
    slant, rate = measure(warmup)
    snapshot = tracker.update(
        0,
        slant_range_km=slant,
        altitude_km=altitude[:, warmup],
        range_rate_km_s=rate,
    )

    dwell = DwellController(grid, NUM_USERS, DwellConfig(steps=3))
    dwell_snapshot = dwell.step(0, xy)

    return {
        "grid": grid,
        "xy": xy,
        "users": users,
        "tracked": position[:, warmup, :],
        "snapshot": snapshot,
        "dwell": dwell,
        "dwell_snapshot": dwell_snapshot,
    }


def _resolve(
    scene,
    incumbents=None,
    *,
    snapshot=None,
    dwell_snapshot=None,
    frozen_window_norad_ids=None,
):
    return resolve_candidates(
        step_index=0,
        user_xy_km=scene["xy"],
        user_ecef_km=scene["users"],
        tracked_satellite_ecef_km=scene["tracked"],
        grid=scene["grid"],
        dwell=scene["dwell"],
        d2_snapshot=scene["snapshot"] if snapshot is None else snapshot,
        dwell_snapshot=(
            scene["dwell_snapshot"]
            if dwell_snapshot is None
            else dwell_snapshot
        ),
        incumbent_norads=(
            np.full(NUM_USERS, -1, dtype=np.int64) if incumbents is None else incumbents
        ),
        frozen_window_norad_ids=frozen_window_norad_ids,
    )


# -- shape and completeness ------------------------------------------------


@requires_archive
def test_the_candidate_table_has_the_frozen_shape(scene):
    result = _resolve(scene)
    assert len(result.slot_tables) == NUM_USERS
    assert result.off_axis_deg.shape == (NUM_USERS, NUM_SATELLITE_SLOTS, NUM_BEAM_SLOTS)
    assert result.slant_range_km.shape == (NUM_USERS, NUM_SATELLITE_SLOTS)
    assert result.contract_fields.shape == (NUM_USERS, CONTRACT_STATE_DIM)
    assert result.masks.shape == (NUM_USERS, NUM_ACTIONS)


@requires_archive
def test_every_user_gets_four_occupied_slots_at_this_epoch(scene):
    """D2 leaves ~86 eligible satellites, so four slots always fill."""
    result = _resolve(scene)
    for assignment in result.assignments:
        assert all(assignment.occupied)


@requires_archive
def test_nobody_is_starved_of_candidates(scene):
    """With no link-feasibility term yet, the mask is an upper bound."""
    result = _resolve(scene)
    assert not result.starved_users.any()
    assert np.all(result.num_valid > 0)


# -- ★ windows are per user ------------------------------------------------


@requires_archive
def test_users_do_not_all_share_one_window(scene):
    """The paper writes b_u(c,t) with a u subscript for this reason."""
    result = _resolve(scene)
    windows = {tuple(row.tolist()) for row in result.window_norad_ids}
    assert len(windows) > 1, "all users got identical windows; margin is per-user"


@requires_archive
def test_a_users_slot_zero_is_their_own_best_margin(scene):
    result = _resolve(scene)
    for uid, assignment in enumerate(result.assignments):
        margins = [
            assignment.margin_km[slot]
            for slot in range(NUM_SATELLITE_SLOTS)
            if assignment.occupied[slot]
        ]
        assert margins == sorted(margins, reverse=True)


@requires_archive
def test_an_incumbent_takes_slot_zero_for_that_user_only(scene):
    plain = _resolve(scene)
    # Give user 3 an incumbent that is not currently their slot 0.
    other = int(plain.window_norad_ids[3, 2])
    incumbents = np.full(NUM_USERS, -1, dtype=np.int64)
    incumbents[3] = other
    withheld = _resolve(scene, incumbents=incumbents)

    assert withheld.window_norad_ids[3, 0] == other
    for uid in range(NUM_USERS):
        if uid != 3:
            assert np.array_equal(
                withheld.window_norad_ids[uid], plain.window_norad_ids[uid]
            )


@requires_archive
def test_a_frozen_dwell_window_defers_replacements_but_refreshes_d2_state(scene):
    """B6: slot identities freeze; eligibility and D2 fields do not.

    The test forces both sides of the ablation.  A cached identity loses D2
    eligibility while an outside satellite becomes the best candidate.  A
    within-dwell resolve must mask the old row and defer the replacement;
    an uncached boundary resolve must admit the replacement.  Merely seeing
    the same window on benign geometry would not test the boundary cache.
    """
    boundary = _resolve(scene)
    frozen = boundary.window_norad_ids.copy()
    uid = 0
    dropped = int(frozen[uid, 0])
    snapshot = scene["snapshot"]
    column_of = {
        int(norad): index
        for index, norad in enumerate(snapshot.norad_ids.tolist())
    }
    outside = next(
        int(norad)
        for norad in snapshot.norad_ids.tolist()
        if bool(snapshot.eligible[uid, column_of[int(norad)]])
        and int(norad) not in set(frozen[uid].tolist())
    )

    eligible = snapshot.eligible.copy()
    margin = snapshot.margin_km.copy()
    ttt = snapshot.ttt_elapsed.copy()
    rate = snapshot.range_rate_km_s.copy()
    eligible[uid, column_of[dropped]] = False
    margin[uid, column_of[outside]] = float(margin[uid].max() + 10_000.0)
    kept = int(frozen[uid, 1])
    margin[uid, column_of[kept]] = 123.0
    ttt[uid, column_of[kept]] = 17
    rate[uid, column_of[kept]] = -4.5
    changed = replace(
        snapshot,
        eligible=eligible,
        margin_km=margin,
        ttt_elapsed=ttt,
        range_rate_km_s=rate,
    )
    within_dwell = replace(
        scene["dwell_snapshot"],
        step_index=1,
        phase=1.0 / 3.0,
        is_boundary=False,
        rekeyed_users=np.zeros(NUM_USERS, dtype=bool),
    )

    within = _resolve(
        scene,
        snapshot=changed,
        dwell_snapshot=within_dwell,
        frozen_window_norad_ids=frozen,
    )
    rebuilt = _resolve(scene, snapshot=changed)

    assert np.array_equal(within.window_norad_ids, frozen)
    assert not bool(within.slot_occupied[uid, 0])
    assert not within.masks[uid, :NUM_BEAM_SLOTS].any()
    assert outside not in within.window_norad_ids[uid]
    assert outside in rebuilt.window_norad_ids[uid]
    assert within.assignments[uid].margin_km[1] == pytest.approx(123.0)
    assert within.assignments[uid].ttt_counter[1] == 17
    assert within.assignments[uid].radial_rate_km_s[1] == pytest.approx(-4.5)

    reentered_eligibility = eligible.copy()
    reentered_eligibility[uid, column_of[dropped]] = True
    reentered = _resolve(
        scene,
        snapshot=replace(changed, eligible=reentered_eligibility),
        dwell_snapshot=within_dwell,
        frozen_window_norad_ids=frozen,
    )
    assert np.array_equal(reentered.window_norad_ids, frozen)
    assert bool(reentered.slot_occupied[uid, 0])
    assert reentered.masks[uid, :NUM_BEAM_SLOTS].any()


@requires_archive
def test_a_frozen_window_is_rejected_on_a_dwell_boundary(scene):
    frozen = _resolve(scene).window_norad_ids
    with pytest.raises(MCRLContractError, match="boundary must rebuild"):
        _resolve(scene, frozen_window_norad_ids=frozen)


@requires_archive
def test_all_four_cached_identities_can_become_a_declared_no_op(scene):
    boundary = _resolve(scene)
    frozen = boundary.window_norad_ids.copy()
    snapshot = scene["snapshot"]
    column_of = {
        int(norad): index
        for index, norad in enumerate(snapshot.norad_ids.tolist())
    }
    eligible = snapshot.eligible.copy()
    for norad in frozen[0]:
        eligible[0, column_of[int(norad)]] = False
    within_dwell = replace(
        scene["dwell_snapshot"],
        step_index=1,
        phase=1.0 / 3.0,
        is_boundary=False,
        rekeyed_users=np.zeros(NUM_USERS, dtype=bool),
    )
    result = _resolve(
        scene,
        snapshot=replace(snapshot, eligible=eligible),
        dwell_snapshot=within_dwell,
        frozen_window_norad_ids=frozen,
    )
    assert result.starved_users[0]
    assert not result.masks[0].any()


# -- geometry --------------------------------------------------------------


@requires_archive
def test_the_off_axis_angles_are_finite_and_small_for_occupied_slots(scene):
    result = _resolve(scene)
    occupied = result.window_norad_ids >= 0
    angles = result.off_axis_deg[occupied]
    assert np.all(np.isfinite(angles))
    # A user's own seven cells subtend a narrow cone from 500-1000 km up.
    assert float(np.nanmax(angles)) < 15.0


@requires_archive
def test_unoccupied_slots_carry_nan_not_a_stale_position(scene):
    result = _resolve(scene)
    empty = result.window_norad_ids < 0
    if not empty.any():
        pytest.skip("every slot is occupied at this epoch")
    assert np.all(np.isnan(result.slant_range_km[empty]))


@requires_archive
def test_the_slant_ranges_agree_with_the_d2_measurement(scene):
    result = _resolve(scene)
    for uid in range(NUM_USERS):
        for slot in range(NUM_SATELLITE_SLOTS):
            norad = int(result.window_norad_ids[uid, slot])
            if norad < 0:
                continue
            margin = result.assignments[uid].margin_km[slot]
            implied = D2Config().thresh2_km - margin
            assert result.slant_range_km[uid, slot] == pytest.approx(
                implied, abs=1.0
            )


# -- the mask --------------------------------------------------------------


@requires_archive
def test_a_valid_action_always_has_both_identities(scene):
    result = _resolve(scene)
    for table in result.slot_tables:
        valid = table.mask
        assert np.all(table.norad_ids[valid] >= 0)
        assert np.all(table.cell_ids[valid] >= 0)


@requires_archive
def test_an_unoccupied_slot_masks_its_whole_row(scene):
    result = _resolve(scene)
    for uid, table in enumerate(result.slot_tables):
        for slot in range(NUM_SATELLITE_SLOTS):
            if result.window_norad_ids[uid, slot] >= 0:
                continue
            row = slice(slot * NUM_BEAM_SLOTS, (slot + 1) * NUM_BEAM_SLOTS)
            assert not table.mask[row].any()


@requires_archive
def test_a_cell_below_a_satellites_horizon_is_masked_out(scene):
    """The visibility term, forced by raising the elevation floor."""
    strict = resolve_candidates(
        step_index=0,
        user_xy_km=scene["xy"],
        user_ecef_km=scene["users"],
        tracked_satellite_ecef_km=scene["tracked"],
        grid=scene["grid"],
        dwell=scene["dwell"],
        d2_snapshot=scene["snapshot"],
        dwell_snapshot=scene["dwell_snapshot"],
        incumbent_norads=np.full(NUM_USERS, -1, dtype=np.int64),
        min_cell_elevation_deg=89.0,
    )
    assert int(strict.num_valid.sum()) < int(_resolve(scene).num_valid.sum())


@requires_archive
def test_a_missing_lattice_neighbour_masks_only_that_beam_slot(scene):
    snapshot = scene["dwell_snapshot"]
    cells = snapshot.neighborhood_cell_ids.copy()
    cells[0, 4] = -1
    patched = type(snapshot)(
        step_index=snapshot.step_index,
        anchor_cell_ids=snapshot.anchor_cell_ids,
        neighborhood_cell_ids=cells,
        phase=snapshot.phase,
        is_boundary=snapshot.is_boundary,
        rekeyed_users=snapshot.rekeyed_users,
    )
    result = resolve_candidates(
        step_index=0,
        user_xy_km=scene["xy"],
        user_ecef_km=scene["users"],
        tracked_satellite_ecef_km=scene["tracked"],
        grid=scene["grid"],
        dwell=scene["dwell"],
        d2_snapshot=scene["snapshot"],
        dwell_snapshot=patched,
        incumbent_norads=np.full(NUM_USERS, -1, dtype=np.int64),
    )
    table = result.slot_tables[0]
    for slot in range(NUM_SATELLITE_SLOTS):
        assert not table.mask[slot * NUM_BEAM_SLOTS + 4]


# -- the contract block ----------------------------------------------------


@requires_archive
def test_the_contract_block_carries_the_dwell_phase(scene):
    result = _resolve(scene)
    assert np.all(result.contract_fields[:, 12] == scene["dwell_snapshot"].phase)


@requires_archive
def test_the_contract_block_flags_the_incumbent(scene):
    incumbents = np.full(NUM_USERS, -1, dtype=np.int64)
    plain = _resolve(scene)
    incumbents[1] = int(plain.window_norad_ids[1, 2])
    result = _resolve(scene, incumbents=incumbents)
    assert result.contract_fields[1, 0] == 1.0
    assert result.contract_fields[0, 0] == 0.0


# -- validation ------------------------------------------------------------


@requires_archive
def test_shape_violations_fail_loud(scene):
    with pytest.raises(MCRLContractError, match=r"\(U, 2\)"):
        resolve_candidates(
            step_index=0,
            user_xy_km=scene["xy"][:, :1],
            user_ecef_km=scene["users"],
            tracked_satellite_ecef_km=scene["tracked"],
            grid=scene["grid"],
            dwell=scene["dwell"],
            d2_snapshot=scene["snapshot"],
            dwell_snapshot=scene["dwell_snapshot"],
            incumbent_norads=np.full(NUM_USERS, -1, dtype=np.int64),
        )
    with pytest.raises(MCRLContractError, match="incumbent_norads"):
        resolve_candidates(
            step_index=0,
            user_xy_km=scene["xy"],
            user_ecef_km=scene["users"],
            tracked_satellite_ecef_km=scene["tracked"],
            grid=scene["grid"],
            dwell=scene["dwell"],
            d2_snapshot=scene["snapshot"],
            dwell_snapshot=scene["dwell_snapshot"],
            incumbent_norads=np.zeros(3, dtype=np.int64),
        )
