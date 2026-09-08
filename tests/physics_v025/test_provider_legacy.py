"""Non-tautological KATs for the TRAIN-only legacy primitive provider."""

from __future__ import annotations

import datetime as dt
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.env.action_contract import NUM_BEAM_SLOTS, NUM_SATELLITE_SLOTS
from mcrl.env.antenna import transmit_gain_linear as legacy_transmit_gain
from mcrl.env.d2 import elevation_for_slant_range
from mcrl.env.ephemeris import TEST, TRAIN, BlockAlternatingSplit, EpisodeStartSampler, step_times
from mcrl.env.interference import beam_field_at_users, build_radiating_beams, co_channel_interference, received_power_terms
from mcrl.env.link_budget import link_power_factor
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.tle import TleArchive
from mcrl.physics_v025.channel import (
    keyed_component_seed,
    keyed_fading_gain,
    rician_power_gain,
    scintillation_loss_db,
    shadow_sigma_db,
    transmit_gain_linear,
)
from mcrl.physics_v025.constants_v025 import (
    CARRIER_FREQUENCY_HZ,
    D2_HYSTERESIS_KM,
    D2_THRESHOLD_KM,
    RX_GAIN_MAX_DBI,
    SPEED_OF_LIGHT_M_S,
    ZENITH_GASEOUS_LOSS_DB,
)
from mcrl.physics_v025.energy import SENSITIVITY_IDLE_POWER_W, EnergyInterval, HardwareInventory, interval_energy
from mcrl.physics_v025.provider_legacy import CANONICAL_STEPS, DEFAULT_TLE_ROOT, LegacyWorldProvider
from mcrl.physics_v025.tapes import build_world_tape, seed_from_domain
from mcrl.runtime.training_pipeline import _evaluation_rngs


WORLD_DOMAIN = "V025_PROBE/world/1"
WORLD_SEED = seed_from_domain(WORLD_DOMAIN)


@pytest.fixture(scope="module")
def real_world():
    archive = TleArchive(DEFAULT_TLE_ROOT)
    split = BlockAlternatingSplit.for_archive(archive)
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(WORLD_SEED)
    start = EpisodeStartSampler.for_archive(
        archive, split, TRAIN, time_step_s=30.08
    ).draw(env_rng)
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(), steps_per_episode=CANONICAL_STEPS),
    )
    decisions = []
    user_ecef = []
    candidate = driver.reset(start, mobility_rng)
    for step in range(CANONICAL_STEPS):
        if step:
            candidate = driver.step(mobility_rng)
        decisions.append(candidate)
        user_ecef.append(driver.user_ecef_km().copy())
    provider = LegacyWorldProvider(steps=3)
    assert provider.start_utc(world_seed=WORLD_SEED) == start
    return provider, driver, tuple(decisions), tuple(user_ecef), start


@pytest.fixture(scope="module")
def step0(real_world):
    provider, _driver, _decisions, _users, _start = real_world
    return provider.step_arrays(world_seed=WORLD_SEED, step_index=0, start_time_s=0.0)


def _row_lookup(arrays):
    return {
        (int(arrays.users[int(arrays.row_user_column[row])]), int(arrays.legacy_action_index[row])): row
        for row in range(arrays.identities.shape[0])
        if int(arrays.legacy_action_index[row]) >= 0
    }


def _hex_distance(grid, first: int, second: int) -> int:
    dq, dr = (grid.axial[first] - grid.axial[second]).tolist()
    return int((abs(dq) + abs(dr) + abs(dq + dr)) // 2)


def test_decision_geometry_and_scintillation_free_nominal_match_legacy(real_world, step0) -> None:
    _provider, _driver, decisions, _users, _start = real_world
    oracle = decisions[0]
    rows = _row_lookup(step0)
    peak = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
    for user, action in zip(*np.nonzero(oracle.masks), strict=True):
        row = rows[(int(user), int(action))]
        satellite_slot, beam_slot = divmod(int(action), NUM_BEAM_SLOTS)
        elevation = float(oracle.elevation_deg[user, satellite_slot])
        slant = float(oracle.slant_range_km[user, satellite_slot])
        off_axis = float(oracle.off_axis_deg[user, satellite_slot, beam_slot])
        legacy_path = float(link_power_factor(np.asarray([slant]), np.asarray([elevation]), np.asarray([peak]))[0])
        no_scint = legacy_path * 10.0 ** (float(scintillation_loss_db(elevation)) / 10.0)
        assert step0.elevations_deg[0, row] == pytest.approx(elevation, rel=1e-9)
        assert step0.slants_km[0, row] == pytest.approx(slant, rel=1e-9)
        assert float(transmit_gain_linear(off_axis)) == pytest.approx(
            float(legacy_transmit_gain(np.asarray([off_axis]))[0]), rel=1e-6
        )
        assert step0.nominal_gain[0, row] == pytest.approx(
            float(transmit_gain_linear(off_axis)) * no_scint, rel=1e-9
        )


@pytest.mark.parametrize("elevation", (10.0, 60.0))
def test_scintillation_is_applied_exactly_once_against_hand_budget(elevation: float) -> None:
    slant_km = 1_000.0
    receive = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
    wavelength = SPEED_OF_LIGHT_M_S / CARRIER_FREQUENCY_HZ
    free_space = (wavelength / (4.0 * math.pi * slant_km * 1_000.0)) ** 2
    atmosphere_db = ZENITH_GASEOUS_LOSS_DB / math.sin(math.radians(elevation))
    hand_nominal = free_space * 10.0 ** (-atmosphere_db / 10.0) * receive
    provider_nominal = float(
        LegacyWorldProvider._nominal_path_without_scintillation(
            np.asarray([slant_km]), np.asarray([elevation]), np.asarray([receive])
        )[0]
    )
    assert provider_nominal == pytest.approx(hand_nominal, rel=1e-12)

    world, user, norad, time_ns = 7, 3, 99, 123_000_000
    shadow_rng = np.random.default_rng(keyed_component_seed(world, user, norad, time_ns, "shadow"))
    rician_rng = np.random.default_rng(keyed_component_seed(world, user, norad, time_ns, "rician"))
    shadow_db = float(shadow_sigma_db(elevation)) * float(shadow_rng.standard_normal())
    rician = float(rician_power_gain(rician_rng, (1,))[0])
    hand_fade = rician * 10.0 ** (-(shadow_db + float(scintillation_loss_db(elevation))) / 10.0)
    assert keyed_fading_gain(
        world=world, user=user, norad=norad, absolute_time_ns=time_ns, elevation_deg=elevation
    ) == pytest.approx(hand_fade, rel=1e-12)


@pytest.mark.parametrize("boundary_index", (17, 47))
def test_forward_boundary_ecef_matches_direct_sgp4(real_world, boundary_index: int) -> None:
    provider, driver, _decisions, _users, start = real_world
    detached = dict(provider.satellite_ecef_km(world_seed=WORLD_SEED, step_index=0, boundary_index=boundary_index))
    when = start + dt.timedelta(seconds=boundary_index * 0.640)
    jd, fr = step_times(when, 1, time_step_s=0.640)
    direct = driver._satellites.propagate_ecef(jd, fr, require_all_healthy=True)
    for index, norad in enumerate(driver.tracked_norad_ids.tolist()):
        error_m = np.linalg.norm(np.asarray(detached[int(norad)]) - direct[index, 0]) * 1_000.0
        assert error_m <= 1.0


def test_mask_is_nonvacuous_and_matches_legacy_at_decision(real_world, step0) -> None:
    _provider, _driver, decisions, _users, _start = real_world
    oracle = decisions[0]
    assert np.any(step0.d2_eligible) and np.any(~step0.d2_eligible)
    assert np.any(step0.visible) and np.any(~step0.visible)
    legacy_legal_below_ten = sum(
        int(candidate.masks[user, action] and candidate.elevation_deg[user, action // NUM_BEAM_SLOTS] < 10.0)
        for candidate in decisions
        for user in range(candidate.masks.shape[0])
        for action in range(candidate.masks.shape[1])
    )
    for row in np.flatnonzero(step0.legacy_action_index >= 0).tolist():
        user = int(step0.users[int(step0.row_user_column[row])])
        action = int(step0.legacy_action_index[row])
        expected_mask = bool(oracle.masks[user, action])
        assert bool(step0.d2_eligible[0, row] and step0.cell_reachable[0, row]) == expected_mask
        expected_legal = expected_mask and bool(step0.visible[0, row])
        actual_legal = bool(step0.visible[0, row] and step0.d2_eligible[0, row] and step0.cell_reachable[0, row])
        assert actual_legal == expected_legal
    assert legacy_legal_below_ten == 0


def test_entry_elevation_and_d2_distance_use_legacy_slant_definition(step0) -> None:
    assert np.array_equal(step0.d2_distances_km, step0.slants_km)
    measured = tuple(
        elevation_for_slant_range(D2_THRESHOLD_KM - D2_HYSTERESIS_KM, altitude)
        for altitude in (426.0, 485.0, 550.0)
    )
    assert measured == pytest.approx((19.6865, 23.3959, 27.6465), abs=5e-4)


def test_aggressor_uses_own_cell_boresight_at_one_and_two_rings(real_world, step0) -> None:
    provider, driver, _decisions, users, _start = real_world
    grid = driver.grid
    positions = dict(provider.satellite_ecef_km(world_seed=WORLD_SEED, step_index=0, boundary_index=0))
    found: dict[int, float] = {}
    aggressors = [tuple(map(int, row)) for row in step0.aggressor_identities]
    for victim_row, victim in enumerate(step0.identities):
        user = int(step0.row_user_column[victim_row])
        victim_norad, victim_cell = map(int, victim)
        for aggressor_index, (aggressor_norad, aggressor_cell) in enumerate(aggressors):
            if aggressor_norad != victim_norad:
                continue
            rings = _hex_distance(grid, victim_cell, aggressor_cell)
            if rings not in (1, 2) or rings in found:
                continue
            radiating = build_radiating_beams(
                beam_norad_ids=np.asarray([aggressor_norad]), beam_cell_ids=np.asarray([aggressor_cell]),
                beam_power_w=np.asarray([1.0]), satellite_ecef_by_norad={aggressor_norad: positions[aggressor_norad]}, grid=grid,
            )
            field = beam_field_at_users(user_ecef_km=users[0][user : user + 1], radiating=radiating)
            terms = received_power_terms(
                field, radiating, user_ecef_km=users[0][user : user + 1],
                boresight_satellite_ecef_km=np.asarray([positions[victim_norad]]),
                boresight_norad_ids=np.asarray([victim_norad]),
            )
            sat = positions[aggressor_norad]
            delta = sat - users[0][user]
            elevation = math.degrees(math.asin(float(np.dot(delta, users[0][user] / np.linalg.norm(users[0][user])) / np.linalg.norm(delta))))
            legacy_no_scint = float(terms[0, 0]) * 10.0 ** (float(scintillation_loss_db(elevation)) / 10.0)
            actual = float(
                step0.cross_base_nominal[0, user, aggressor_index]
                * step0.receive_gain_by_wanted_slot[
                    0, user, int(step0.row_wanted_slot[victim_row]), int(step0.aggressor_satellite_column[aggressor_index])
                ]
            )
            assert actual == pytest.approx(legacy_no_scint, rel=1e-9)
            wrong = build_radiating_beams(
                beam_norad_ids=np.asarray([aggressor_norad]), beam_cell_ids=np.asarray([victim_cell]),
                beam_power_w=np.asarray([1.0]), satellite_ecef_by_norad={aggressor_norad: positions[aggressor_norad]}, grid=grid,
            )
            wrong_term = received_power_terms(
                beam_field_at_users(user_ecef_km=users[0][user : user + 1], radiating=wrong), wrong,
                user_ecef_km=users[0][user : user + 1], boresight_satellite_ecef_km=np.asarray([positions[victim_norad]]),
                boresight_norad_ids=np.asarray([victim_norad]),
            )[0, 0]
            found[rings] = 10.0 * math.log10(float(wrong_term) / float(terms[0, 0]))
            if set(found) == {1, 2}:
                break
        if set(found) == {1, 2}:
            break
    assert set(found) == {1, 2}
    assert found[1] > 2.0
    assert found[2] > found[1] + 10.0


def test_per_chain_colour_filter_and_same_satellite_p10_match_legacy(real_world, step0) -> None:
    provider, driver, _decisions, users, _start = real_world
    normal = np.flatnonzero(step0.legacy_action_index >= 0).tolist()
    chosen = None
    for victim in normal:
        vu = int(step0.row_user_column[victim]); vn, vc = map(int, step0.identities[victim]); color = int(step0.colors[victim])
        same = next((row for row in normal if int(step0.row_user_column[row]) != vu and int(step0.identities[row, 0]) == vn and int(step0.identities[row, 1]) != vc and int(step0.colors[row]) == color), None)
        used = {vu, -1 if same is None else int(step0.row_user_column[same])}
        inter = next((row for row in normal if int(step0.row_user_column[row]) not in used and int(step0.identities[row, 0]) != vn and int(step0.colors[row]) == color), None)
        if same is not None and inter is not None:
            chosen = (victim, same, inter); break
    assert chosen is not None
    victim, same, inter = chosen
    assignments = {int(step0.row_user_column[row]): tuple(map(int, step0.identities[row])) for row in chosen}
    geometry = step0.geometry_at(boundary_index=0, assignments=assignments)
    assert geometry.nominal_cross_gain[0, 1] > 0.0
    assert geometry.nominal_cross_gain[0, 2] > 0.0
    different = next(row for row in normal if int(step0.row_user_column[row]) != int(step0.row_user_column[victim]) and int(step0.colors[row]) != int(step0.colors[victim]))
    assert step0._cross(0, victim, tuple(map(int, step0.identities[different]))) == (0.0, 0.0)

    positions = dict(provider.satellite_ecef_km(world_seed=WORLD_SEED, step_index=0, boundary_index=0))
    victim_user = int(step0.row_user_column[victim]); victim_identity = tuple(map(int, step0.identities[victim]))
    aggressor_rows = (same, inter)
    aggressor_identities = [tuple(map(int, step0.identities[row])) for row in aggressor_rows]
    radiating = build_radiating_beams(
        beam_norad_ids=np.asarray([identity[0] for identity in aggressor_identities]),
        beam_cell_ids=np.asarray([identity[1] for identity in aggressor_identities]), beam_power_w=np.ones(2),
        satellite_ecef_by_norad=positions, grid=driver.grid,
    )
    terms = received_power_terms(
        beam_field_at_users(user_ecef_km=users[0][victim_user : victim_user + 1], radiating=radiating), radiating,
        user_ecef_km=users[0][victim_user : victim_user + 1], boresight_satellite_ecef_km=np.asarray([positions[victim_identity[0]]]),
        boresight_norad_ids=np.asarray([victim_identity[0]]),
    )
    expected = co_channel_interference(
        terms, radiating, wanted_norad_ids=np.asarray([victim_identity[0]]),
        wanted_cell_ids=np.asarray([victim_identity[1]]), wanted_colors=np.asarray([int(step0.colors[victim])]),
    ).total_w[0]
    corrected = 0.0
    for term, row in zip(terms[0], aggressor_rows, strict=True):
        sat = positions[int(step0.identities[row, 0])]; delta = sat - users[0][victim_user]
        elevation = math.degrees(math.asin(float(np.dot(delta, users[0][victim_user] / np.linalg.norm(users[0][victim_user])) / np.linalg.norm(delta))))
        corrected += float(term) * 10.0 ** (float(scintillation_loss_db(elevation)) / 10.0)
    assert geometry.nominal_cross_gain[0, 1:].sum() == pytest.approx(corrected, rel=1e-9)
    assert expected > 0.0


def test_inventory_is_exact_realisable_union_and_standby_energy(real_world) -> None:
    provider, _driver, decisions, _users, _start = real_world
    expected = set()
    for candidate in decisions:
        norads = np.repeat(candidate.window_norad_ids, NUM_BEAM_SLOTS, axis=1)
        cells = np.tile(candidate.dwell.neighborhood_cell_ids, (1, NUM_SATELLITE_SLOTS))
        for user, action in zip(*np.nonzero(candidate.masks), strict=True):
            expected.add((int(norads[user, action]), int(cells[user, action])))
    inventory = tuple(provider.inventory(world_seed=WORLD_SEED))
    assert set(inventory) == expected
    assert len(inventory) == 2_758
    duration = 30.08
    receipt = interval_energy(
        HardwareInventory.fixed(inventory), EnergyInterval(duration, {}), idle_power_w=SENSITIVITY_IDLE_POWER_W
    )
    assert receipt.joules == pytest.approx(len(inventory) * SENSITIVITY_IDLE_POWER_W * duration, rel=1e-12)


def test_fixed_forward_horizon_has_explicit_right_censoring(step0) -> None:
    cap = math.ceil(900.0 / 0.640) * 0.640
    assert np.all(step0.remaining_visibility_s <= cap)
    assert np.all(step0.remaining_d2_s <= cap)
    mask = np.ones((48 + math.ceil(900.0 / 0.640), 1, 1), dtype=bool)
    active = np.ones((48, 1, 1), dtype=bool)
    durations, censored = LegacyWorldProvider._durations_from_mask(mask, active)
    assert np.all(censored)
    assert np.all(durations == cap)


def test_user_motion_is_recorded_per_step_and_user_count_is_sourced(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    first = provider.user_layout_at_step(world_seed=WORLD_SEED, step_index=0)
    last = provider.user_layout_at_step(world_seed=WORLD_SEED, step_index=29)
    assert len(first) == MobilityConfig().num_users
    assert first != last


def test_exact_train_timestamp_and_test_date_rejection(real_world) -> None:
    provider, _driver, _decisions, _users, start = real_world
    archive = TleArchive(DEFAULT_TLE_ROOT); split = BlockAlternatingSplit.for_archive(archive)
    independently_drawn = EpisodeStartSampler.for_archive(
        archive, split, TRAIN, time_step_s=30.08
    ).draw(_evaluation_rngs(WORLD_SEED)[0])
    assert provider.start_utc(world_seed=WORLD_SEED) == independently_drawn == start
    assert split.part_for(start.date()) == TRAIN
    with pytest.raises(MCRLContractError, match="TRAIN-only"):
        LegacyWorldProvider(start_utc=split.available_dates(archive, TEST)[0])


def test_unhealthy_propagation_fails_closed() -> None:
    with pytest.raises(MCRLContractError, match="non-finite"):
        LegacyWorldProvider._validate_propagation(np.full((1, 1, 3), np.nan))
    with pytest.raises(MCRLContractError, match="sub-surface"):
        LegacyWorldProvider._validate_propagation(np.asarray([[[4_600.0, 0.0, 0.0]]]))


def test_nonzero_origin_and_forward_prime_seam_have_no_backward_jump(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    shifted = provider.step_arrays(world_seed=WORLD_SEED, step_index=0, start_time_s=123.0).absolute_time_s
    assert shifted[0] == 123.0
    assert np.all(np.diff(shifted) > 0.0)
    assert shifted[-1] == pytest.approx(123.0 + 47 * 0.640)


def test_canonical_horizon_is_invariant_to_requested_rehearsal_length(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    short = LegacyWorldProvider(steps=3); long = LegacyWorldProvider(steps=31)
    expected = tuple(provider.inventory(world_seed=WORLD_SEED))
    assert tuple(short.inventory(world_seed=WORLD_SEED)) == expected == tuple(long.inventory(world_seed=WORLD_SEED))
    assert short.manifest_input_digest(world_seed=WORLD_SEED) == long.manifest_input_digest(world_seed=WORLD_SEED)


def test_manifest_and_boundary_arrays_are_deterministic_across_processes() -> None:
    script = """
import hashlib, json
from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
from mcrl.physics_v025.tapes import seed_from_domain
p=LegacyWorldProvider(steps=3); s=seed_from_domain('V025_PROBE/world/1')
a=p.step_arrays(world_seed=s, step_index=5, start_time_s=17.0); h=hashlib.sha256()
for k in (17,47):
    for value in (a.identities, a.elevations_deg[k], a.slants_km[k], a.nominal_gain[k], a.realised_gain[k], a.visible[k], a.d2_eligible[k]):
        h.update(value.tobytes(order='C'))
print(json.dumps({'manifest': p.manifest_input_digest(world_seed=s), 'arrays': h.hexdigest()}))
"""
    env = dict(os.environ); env["PYTHONPATH"] = "src"; command = [sys.executable, "-c", script]
    first = json.loads(subprocess.check_output(command, cwd=Path.cwd(), env=env, text=True))
    second = json.loads(subprocess.check_output(command, cwd=Path.cwd(), env=env, text=True))
    assert first == second


def test_build_world_tape_uses_array_storage_and_input_digest(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    tape = build_world_tape(domain=WORLD_DOMAIN, provider=provider, steps=1, start_time_s=41.0)
    assert tape.steps[0].arrays is not None and tape.steps[0].boundaries == ()
    assert tape.steps[0].arrays.absolute_time_s[0] == 41.0
    assert tape.tape_digest == provider.manifest_input_digest(world_seed=WORLD_SEED)
    assert tape.manifest()["cross_gain_key"] == "(NORAD,cell_id)"
    assert tape.manifest()["boundary_storage"] == "numpy-float64"
    assert tape.tle_files == provider.tle_binding(world_seed=WORLD_SEED)


def test_tle_split_and_provider_source_hashes_are_recorded(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    files = provider.tle_binding(world_seed=WORLD_SEED)
    assert files and all(name and len(digest) == 64 for name, digest in files)
    split_name, split_hash = provider.split_binding()
    assert split_name == "ephemeris.py" and len(split_hash) == 64
    source = Path(inspect.getsourcefile(LegacyWorldProvider) or "")
    assert provider.provider_source_sha256() == hashlib.sha256(source.read_bytes()).hexdigest()
