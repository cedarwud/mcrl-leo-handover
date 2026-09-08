"""Non-tautological KATs for the TRAIN-only legacy primitive provider."""

from __future__ import annotations

import datetime as dt
from dataclasses import fields, replace
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
    IDENTITY_REFRESH_DECISIONS,
    MINIMUM_ELEVATION_DEG,
    RX_GAIN_MAX_DBI,
    SPEED_OF_LIGHT_M_S,
    ZENITH_GASEOUS_LOSS_DB,
)
from mcrl.physics_v025.energy import SENSITIVITY_IDLE_POWER_W, EnergyInterval, HardwareInventory, interval_energy
from mcrl.physics_v025.provider_legacy import (
    CANONICAL_STEPS,
    DEFAULT_TLE_ROOT,
    LegacyWorldProvider,
)
from mcrl.physics_v025.tapes import (
    PrimitiveStepArrays,
    TinySyntheticProvider,
    build_world_tape,
    canonical_bytes,
    provider_allocation_manifest,
    seed_from_domain,
)
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


def _minimal_step_arrays() -> PrimitiveStepArrays:
    boundaries = 48
    return PrimitiveStepArrays(
        absolute_time_s=np.arange(boundaries, dtype=np.float64) * 0.640,
        users=np.asarray([0], dtype=np.int64),
        row_user_column=np.asarray([0], dtype=np.int64),
        legacy_action_index=np.asarray([0], dtype=np.int64),
        identities=np.asarray([[1, 1]], dtype=np.int64),
        colors=np.asarray([0], dtype=np.int64),
        elevations_deg=np.full((boundaries, 1), 30.0),
        d2_entry_elevations_deg=np.full((boundaries, 1), 20.0),
        slants_km=np.full((boundaries, 1), 1_000.0),
        d2_distances_km=np.full((boundaries, 1), 1_000.0),
        visible=np.ones((boundaries, 1), dtype=bool),
        d2_eligible=np.ones((boundaries, 1), dtype=bool),
        cell_reachable=np.ones((boundaries, 1), dtype=bool),
        nominal_gain=np.ones((boundaries, 1)),
        realised_gain=np.ones((boundaries, 1)),
        remaining_visibility_s=np.zeros((boundaries, 1)),
        remaining_d2_s=np.zeros((boundaries, 1)),
        visibility_right_censored=np.zeros((boundaries, 1), dtype=bool),
        d2_right_censored=np.zeros((boundaries, 1), dtype=bool),
        aggressor_identities=np.asarray([[1, 1]], dtype=np.int64),
        aggressor_colors=np.asarray([0], dtype=np.int64),
        aggressor_satellite_column=np.asarray([0], dtype=np.int64),
        row_wanted_slot=np.asarray([0], dtype=np.int64),
        cross_base_nominal=np.ones((boundaries, 1, 1)),
        fading_by_satellite=np.ones((boundaries, 1, 1)),
        receive_gain_by_wanted_slot=np.ones((boundaries, 1, 1, 1)),
    )


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
    provider, _driver, decisions, users, _start = real_world
    oracle = decisions[0]
    arrays = step0
    present = np.repeat(oracle.slot_occupied, NUM_BEAM_SLOTS, axis=1)
    legacy_false = {
        (int(user), int(action))
        for user, action in zip(*np.nonzero(present & ~oracle.masks), strict=True)
    }
    legacy_legal_below_ten = sum(
        int(candidate.masks[user, action] and candidate.elevation_deg[user, action // NUM_BEAM_SLOTS] < 10.0)
        for candidate in decisions
        for user in range(candidate.masks.shape[0])
        for action in range(candidate.masks.shape[1])
    )
    matched_false = set()
    for row in np.flatnonzero(arrays.legacy_action_index >= 0).tolist():
        user = int(arrays.users[int(arrays.row_user_column[row])])
        action = int(arrays.legacy_action_index[row])
        expected_mask = bool(oracle.masks[user, action])
        assert bool(arrays.d2_eligible[0, row] and arrays.cell_reachable[0, row]) == expected_mask
        if not expected_mask:
            matched_false.add((user, action))
        expected_legal = expected_mask and bool(arrays.visible[0, row])
        actual_legal = bool(
            arrays.visible[0, row]
            and arrays.d2_eligible[0, row]
            and arrays.cell_reachable[0, row]
        )
        assert actual_legal == expected_legal
    assert matched_false == legacy_false
    positions = dict(
        provider.satellite_ecef_km(
            world_seed=WORLD_SEED, step_index=0, boundary_index=0
        )
    )
    extra_rows = np.flatnonzero(arrays.legacy_action_index < 0).tolist()
    assert len(extra_rows) == len(users[0])
    for row in extra_rows[:3]:
        user = int(arrays.row_user_column[row])
        satellite = np.asarray(positions[int(arrays.identities[row, 0])])
        delta = satellite - users[0][user]
        slant = float(np.linalg.norm(delta))
        elevation = math.degrees(
            math.asin(
                float(
                    np.dot(delta, users[0][user] / np.linalg.norm(users[0][user]))
                    / slant
                )
            )
        )
        assert elevation < MINIMUM_ELEVATION_DEG
        assert slant - D2_HYSTERESIS_KM > D2_THRESHOLD_KM
        assert not arrays.visible[0, row]
        assert not arrays.d2_eligible[0, row]
    assert legacy_legal_below_ten == 0


def test_entry_elevation_and_d2_distance_use_legacy_slant_definition(real_world, step0) -> None:
    provider, _driver, _decisions, users, _start = real_world
    for boundary, row in ((0, 0), (17, 137), (47, 999)):
        user = int(step0.row_user_column[row])
        norad = int(step0.identities[row, 0])
        satellite = dict(
            provider.satellite_ecef_km(
                world_seed=WORLD_SEED,
                step_index=0,
                boundary_index=boundary,
            )
        )[norad]
        hand_slant = float(np.linalg.norm(np.asarray(satellite) - users[0][user]))
        assert step0.d2_distances_km[boundary, row] == pytest.approx(hand_slant, rel=1e-12)
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


def test_per_victim_total_interference_matches_legacy_for_three_victims(real_world, step0) -> None:
    provider, driver, _decisions, users, _start = real_world
    normal = np.flatnonzero(step0.legacy_action_index >= 0).tolist()
    chosen = None
    for color in range(3):
        by_satellite: dict[int, list[int]] = {}
        for row in normal:
            if int(step0.colors[row]) == color:
                by_satellite.setdefault(int(step0.identities[row, 0]), []).append(row)
        for norad, rows in by_satellite.items():
            same_rows = []
            used_users = set()
            used_cells = set()
            for row in rows:
                user = int(step0.row_user_column[row])
                cell = int(step0.identities[row, 1])
                if user not in used_users and cell not in used_cells:
                    same_rows.append(row); used_users.add(user); used_cells.add(cell)
                if len(same_rows) == 4:
                    break
            cross = next(
                (
                    row
                    for other, other_rows in by_satellite.items()
                    if other != norad
                    for row in other_rows
                    if int(step0.row_user_column[row]) not in used_users
                ),
                None,
            )
            if len(same_rows) >= 4 and cross is not None:
                chosen = same_rows + [cross]
                break
        if chosen is not None:
            break
    assert chosen is not None
    assignments = {
        int(step0.users[int(step0.row_user_column[row])]): tuple(map(int, step0.identities[row]))
        for row in chosen
    }
    geometry = step0.geometry_at(boundary_index=0, assignments=assignments)
    positions = dict(provider.satellite_ecef_km(world_seed=WORLD_SEED, step_index=0, boundary_index=0))
    ordered = list(geometry.links)
    aggressor_identities = [link.beam for link in ordered]
    radiating = build_radiating_beams(
        beam_norad_ids=np.asarray([identity[0] for identity in aggressor_identities]),
        beam_cell_ids=np.asarray([identity[1] for identity in aggressor_identities]),
        beam_power_w=np.ones(len(ordered)),
        satellite_ecef_by_norad=positions, grid=driver.grid,
    )
    victim_users = np.asarray([link.user_id for link in ordered], dtype=np.int64)
    victim_norads = np.asarray([link.beam[0] for link in ordered], dtype=np.int64)
    victim_cells = np.asarray([link.beam[1] for link in ordered], dtype=np.int64)
    terms = received_power_terms(
        beam_field_at_users(user_ecef_km=users[0][victim_users], radiating=radiating),
        radiating,
        user_ecef_km=users[0][victim_users],
        boresight_satellite_ecef_km=np.asarray([positions[norad] for norad in victim_norads]),
        boresight_norad_ids=victim_norads,
    )
    legacy_total = co_channel_interference(
        terms,
        radiating,
        wanted_norad_ids=victim_norads,
        wanted_cell_ids=victim_cells,
        wanted_colors=np.asarray([link.color for link in ordered]),
    ).total_w
    provider_legacy_equivalent = np.zeros(len(ordered))
    mixed_victims = []
    for victim_index, victim in enumerate(ordered):
        for aggressor_index, aggressor in enumerate(ordered):
            if victim_index == aggressor_index or victim.color != aggressor.color:
                continue
            delta = positions[aggressor.beam[0]] - users[0][victim.user_id]
            elevation = math.degrees(
                math.asin(
                    float(
                        np.dot(delta, users[0][victim.user_id] / np.linalg.norm(users[0][victim.user_id]))
                        / np.linalg.norm(delta)
                    )
                )
            )
            provider_legacy_equivalent[victim_index] += (
                geometry.nominal_cross_gain[victim_index, aggressor_index]
                * 10.0 ** (-float(scintillation_loss_db(elevation)) / 10.0)
            )
        same = any(
            other != victim_index
            and ordered[other].beam[0] == victim.beam[0]
            and ordered[other].beam != victim.beam
            for other in range(len(ordered))
        )
        cross = any(ordered[other].beam[0] != victim.beam[0] for other in range(len(ordered)))
        if same and cross:
            mixed_victims.append(victim_index)
    assert len(mixed_victims) >= 3
    assert provider_legacy_equivalent[mixed_victims] == pytest.approx(
        legacy_total[mixed_victims], rel=1e-9
    )


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


def test_fixed_forward_horizon_matches_direct_sgp4_crossings(real_world, step0) -> None:
    provider, driver, _decisions, users, start = real_world
    arrays = provider.step_arrays(world_seed=WORLD_SEED, step_index=29)
    decision_start = start + dt.timedelta(seconds=29 * 30.08)
    cap = math.ceil(900.0 / 0.640) * 0.640
    assert np.all(arrays.remaining_visibility_s <= cap)
    assert np.all(arrays.remaining_d2_s <= cap)
    samples = 48 + math.ceil(900.0 / 0.640)
    jd, fr = step_times(decision_start, samples, time_step_s=0.640)
    direct = driver._satellites.propagate_ecef(jd, fr, require_all_healthy=True)
    column = {int(norad): index for index, norad in enumerate(driver.tracked_norad_ids)}
    saw_visibility_crossing = saw_d2_crossing = False
    for row in np.flatnonzero(arrays.legacy_action_index >= 0).tolist():
        user = int(arrays.row_user_column[row])
        norad = int(arrays.identities[row, 0])
        delta = direct[column[norad]] - users[29][user]
        slant = np.linalg.norm(delta, axis=1)
        up = users[29][user] / np.linalg.norm(users[29][user])
        elevation = np.degrees(np.arcsin(np.clip((delta @ up) / slant, -1.0, 1.0)))
        if bool(arrays.visible[0, row]):
            failures = np.flatnonzero(elevation < MINIMUM_ELEVATION_DEG)
            expected = cap if failures.size == 0 else int(failures[0]) * 0.640
            assert arrays.remaining_visibility_s[0, row] == pytest.approx(expected)
            assert bool(arrays.visibility_right_censored[0, row]) == (failures.size == 0)
            saw_visibility_crossing |= bool(failures.size)
        if bool(arrays.d2_eligible[0, row]):
            failures = np.flatnonzero(
                slant - D2_HYSTERESIS_KM > D2_THRESHOLD_KM
            )
            expected = cap if failures.size == 0 else int(failures[0]) * 0.640
            assert arrays.remaining_d2_s[0, row] == pytest.approx(expected)
            assert bool(arrays.d2_right_censored[0, row]) == (failures.size == 0)
            saw_d2_crossing |= bool(failures.size)
        if saw_visibility_crossing and saw_d2_crossing:
            break
    assert saw_visibility_crossing and saw_d2_crossing
    assert not np.any(arrays.visibility_right_censored)
    assert not np.any(arrays.d2_right_censored)


def test_user_motion_is_recorded_per_step_and_user_count_is_sourced(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    first = provider.user_layout_at_step(world_seed=WORLD_SEED, step_index=0)
    last = provider.user_layout_at_step(world_seed=WORLD_SEED, step_index=29)
    assert len(first) == MobilityConfig().num_users
    assert first != last


def test_exact_train_timestamp_and_test_date_rejection(real_world) -> None:
    provider, _driver, _decisions, _users, start = real_world
    archive = TleArchive(DEFAULT_TLE_ROOT); split = BlockAlternatingSplit.for_archive(archive)
    frozen_known_answer = dt.datetime(
        2026, 1, 7, 9, 3, 56, 800_000, tzinfo=dt.timezone.utc
    )
    assert provider.start_utc(world_seed=WORLD_SEED) == start == frozen_known_answer
    assert split.part_for(start.date()) == TRAIN
    with pytest.raises(MCRLContractError, match="TRAIN-only"):
        LegacyWorldProvider(start_utc=split.available_dates(archive, TEST)[0])


def test_unhealthy_propagation_fails_closed() -> None:
    with pytest.raises(MCRLContractError, match="non-finite"):
        LegacyWorldProvider._validate_propagation(np.full((1, 1, 3), np.nan))
    with pytest.raises(MCRLContractError, match="sub-surface"):
        LegacyWorldProvider._validate_propagation(np.asarray([[[4_600.0, 0.0, 0.0]]]))


def test_every_float_primitive_array_rejects_nan_and_infinity() -> None:
    valid = _minimal_step_arrays()
    float_fields = [
        field.name
        for field in fields(valid)
        if np.issubdtype(np.asarray(getattr(valid, field.name)).dtype, np.floating)
    ]
    assert set(float_fields) == {
        "absolute_time_s",
        "elevations_deg",
        "d2_entry_elevations_deg",
        "slants_km",
        "d2_distances_km",
        "nominal_gain",
        "realised_gain",
        "remaining_visibility_s",
        "remaining_d2_s",
        "cross_base_nominal",
        "fading_by_satellite",
        "receive_gain_by_wanted_slot",
    }
    for name in float_fields:
        for nonfinite in (math.nan, math.inf):
            corrupted = np.array(getattr(valid, name), copy=True)
            corrupted.flat[0] = nonfinite
            with pytest.raises(MCRLContractError, match=name):
                replace(valid, **{name: corrupted})


def test_nonzero_origin_is_bound_across_steps_and_rejects_drift(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    first = provider.boundary(
        world_seed=WORLD_SEED, step_index=0, boundary_index=0, absolute_time_s=123.0
    )
    later_time = 123.0 + 30.08 + 17 * 0.640
    later = provider.boundary(
        world_seed=WORLD_SEED,
        step_index=1,
        boundary_index=17,
        absolute_time_s=later_time,
    )
    assert first.absolute_time_s == 123.0
    assert later.absolute_time_s == pytest.approx(later_time)
    with pytest.raises(MCRLContractError, match="origin"):
        provider.boundary(
            world_seed=WORLD_SEED,
            step_index=2,
            boundary_index=0,
            absolute_time_s=999.0,
        )


def test_canonical_horizon_is_invariant_to_requested_rehearsal_length(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    short = LegacyWorldProvider(steps=3); long = LegacyWorldProvider(steps=31)
    expected = tuple(provider.inventory(world_seed=WORLD_SEED))
    assert tuple(short.inventory(world_seed=WORLD_SEED)) == expected == tuple(long.inventory(world_seed=WORLD_SEED))
    for step_index in (0, 2):
        first = short.step_arrays(world_seed=WORLD_SEED, step_index=step_index)
        second = long.step_arrays(world_seed=WORLD_SEED, step_index=step_index)
        for field in fields(first):
            assert np.array_equal(getattr(first, field.name), getattr(second, field.name))


def test_manifest_and_boundary_arrays_are_deterministic_across_processes() -> None:
    script = """
import hashlib, json
from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
from mcrl.physics_v025.tapes import build_world_tape, seed_from_domain
p=LegacyWorldProvider(steps=3); s=seed_from_domain('V025_PROBE/world/1')
t=build_world_tape(domain='V025_PROBE/world/1', provider=p, steps=6, start_time_s=17.0)
a=t.steps[5].arrays; h=hashlib.sha256()
for k in (17,47):
    for value in (a.identities, a.elevations_deg[k], a.slants_km[k], a.nominal_gain[k], a.realised_gain[k], a.visible[k], a.d2_eligible[k]):
        h.update(value.tobytes(order='C'))
print(json.dumps({'manifest': t.tape_digest, 'arrays': h.hexdigest()}))
"""
    env = dict(os.environ); env["PYTHONPATH"] = "src"; command = [sys.executable, "-c", script]
    first = json.loads(subprocess.check_output(command, cwd=Path.cwd(), env=env, text=True))
    second = json.loads(subprocess.check_output(command, cwd=Path.cwd(), env=env, text=True))
    assert first == second


def test_manifest_digest_covers_k0_outputs_not_unused_generator_fields(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    tape = build_world_tape(domain=WORLD_DOMAIN, provider=provider, steps=1, start_time_s=41.0)
    assert tape.steps[0].arrays is not None and tape.steps[0].boundaries == ()
    assert tape.steps[0].arrays.absolute_time_s[0] == 41.0
    original_digest = tape.tape_digest
    arrays = tape.steps[0].arrays
    changed = np.array(arrays.nominal_gain, copy=True)
    changed.view(np.uint64).flat[0] ^= np.uint64(1)
    changed_arrays = replace(arrays, nominal_gain=changed)
    changed_tape = replace(
        tape,
        steps=(replace(tape.steps[0], arrays=changed_arrays),),
    )
    assert changed_tape.tape_digest != original_digest

    first_provider = TinySyntheticProvider()
    second_provider = TinySyntheticProvider()
    first_provider.unused_generator_field = "first"
    second_provider.unused_generator_field = "second"
    first = build_world_tape(
        domain=WORLD_DOMAIN, provider=first_provider, steps=1, start_time_s=0.0
    )
    second = build_world_tape(
        domain=WORLD_DOMAIN, provider=second_provider, steps=1, start_time_s=0.0
    )
    assert first.tape_digest == second.tape_digest
    assert tape.manifest()["cross_gain_key"] == "(NORAD,cell_id)"
    assert tape.manifest()["boundary_storage"] == "numpy-float64"
    assert tape.tle_files == provider.tle_binding(world_seed=WORLD_SEED)


def test_complete_provider_attestation_and_split_mismatch_guard(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    with pytest.raises(MCRLContractError, match="learner-free physics matrix"):
        LegacyWorldProvider(role="physics-matrix", learner_seed=1)
    attestation = provider.attestation(world_seed=WORLD_SEED, steps=33)
    payload = attestation.payload()
    assert payload["start_utc"] == "2026-01-07T09:03:56.800000+00:00"
    assert payload["tle_files"] == [list(row) for row in provider.tle_binding(world_seed=WORLD_SEED)]
    assert payload["split"] == TRAIN
    assert payload["split_rule"]["file"] == "ephemeris.py"
    assert payload["role"] == "physics-matrix"
    assert payload["learner_seed"] is None
    assert payload["world_seed"] == WORLD_SEED
    assert payload["candidate_refresh_period_n"] == 4
    assert payload["step_partition"] == {"executed": 30, "forecast": 3}
    assert payload["streams"]["mobility"].endswith("spawn(4)[1]:mobility")
    assert "absolute_time_ns" in payload["streams"]["fading"]
    assert payload["inference"] == {
        "date_panel_policy": (
            "allocation manifest must assert role-wise date disjointness before units open"
        ),
        "primary_resampling": "one-way bootstrap over TLE dates",
        "world_pooling": "pool worlds within each TLE-date x learner-seed cell",
    }
    assert payload["opened_tle_splits"] == [
        [file_date, provider._split.part_for(dt.date.fromisoformat(file_date))]
        for file_date in payload["opened_tle_dates"]
    ]
    assert all(part != TEST for _file_date, part in payload["opened_tle_splits"])
    independent_archive_index = hashlib.sha256(
        canonical_bytes(
            [
                [file_date.isoformat(), path.name]
                for file_date, path in sorted(provider._archive._paths.items())
            ]
        )
    ).hexdigest()
    assert payload["archive_sha256"] == independent_archive_index
    with pytest.raises(MCRLContractError, match="split mismatch"):
        replace(attestation, split=TEST)

    source = Path(inspect.getsourcefile(LegacyWorldProvider) or "")
    assert provider.provider_source_sha256() == hashlib.sha256(source.read_bytes()).hexdigest()

    # Reuse only the already-frozen primitive world so this KAT tests the
    # provider's learner-role attestation policy without opening another TLE
    # world or consuming a second rehearsal-scale propagation.
    learner_provider = LegacyWorldProvider(role="learner-evaluation", learner_seed=73)
    learner_provider._archive = provider._archive
    learner_provider._split = provider._split
    learner_provider._world_seed = WORLD_SEED
    learner_provider._world = provider._world
    learner = learner_provider.attestation(world_seed=WORLD_SEED, steps=33).payload()
    assert learner["learner_seed"] == 73
    assert learner["world_seed"] == WORLD_SEED
    assert learner["inference"]["primary_resampling"] == (
        "two-way pigeonhole bootstrap over TLE dates x learner seeds"
    )
    assert learner["inference"]["world_pooling"] == (
        "pool worlds within each TLE-date x learner-seed cell"
    )


def test_claim_panel_allocation_rejects_role_date_reuse(real_world) -> None:
    provider, _driver, _decisions, _users, _start = real_world
    physics = provider.attestation(world_seed=WORLD_SEED, steps=33)
    distinct_claim = replace(
        physics,
        role="claim",
        world_seed=WORLD_SEED + 1,
        start_utc="2026-01-09T09:03:56.800000+00:00",
    )
    allocation = provider_allocation_manifest((physics, distinct_claim))
    assert allocation["claim_dates_disjoint"] is True
    assert len(allocation["sha256"]) == 64

    reused_claim = replace(distinct_claim, start_utc=physics.start_utc)
    with pytest.raises(MCRLContractError, match="claim-panel UTC dates overlap"):
        provider_allocation_manifest((physics, reused_claim))


def test_identity_rows_refresh_only_at_phase_zero(real_world, step0) -> None:
    provider, _driver, _decisions, _users, _start = real_world

    def snapshot(arrays: PrimitiveStepArrays) -> tuple[tuple[int, int, int, int], ...]:
        return tuple(
            sorted(
                (
                    int(arrays.users[int(arrays.row_user_column[row])]),
                    int(arrays.legacy_action_index[row]),
                    int(arrays.identities[row, 0]),
                    int(arrays.identities[row, 1]),
                )
                for row in np.flatnonzero(arrays.legacy_action_index >= 0)
            )
        )

    previous = snapshot(step0)
    changed_at = []
    for step_index in range(1, 9):
        current = snapshot(
            provider.step_arrays(world_seed=WORLD_SEED, step_index=step_index)
        )
        if current != previous:
            changed_at.append(step_index)
            assert step_index % IDENTITY_REFRESH_DECISIONS == 0
        else:
            assert step_index % IDENTITY_REFRESH_DECISIONS != 0
        previous = current
    assert changed_at == [4, 8]
