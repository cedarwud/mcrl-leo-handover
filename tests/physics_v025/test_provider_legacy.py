"""KATs for the read-only legacy primitive-world binding."""

from __future__ import annotations

import datetime as dt
import gc

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.env.antenna import transmit_gain_linear as legacy_transmit_gain
from mcrl.env.d2 import elevation_for_slant_range
from mcrl.env.ephemeris import (
    TEST,
    BlockAlternatingSplit,
    EpisodeStartSampler,
    step_times,
)
from mcrl.env.link_budget import link_power_factor
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.tle import TleArchive
from mcrl.physics_v025.channel import transmit_gain_linear
from mcrl.physics_v025.constants_v025 import (
    D2_HYSTERESIS_KM,
    D2_THRESHOLD_KM,
    RX_GAIN_MAX_DBI,
)
from mcrl.physics_v025.provider_legacy import DEFAULT_TLE_ROOT, LegacyWorldProvider
from mcrl.physics_v025.tapes import build_world_tape, seed_from_domain
from mcrl.runtime.training_pipeline import _evaluation_rngs


WORLD_DOMAIN = "V025_PROBE/world/1"
WORLD_SEED = seed_from_domain(WORLD_DOMAIN)


@pytest.fixture(scope="module")
def real_world():
    archive = TleArchive(DEFAULT_TLE_ROOT)
    split = BlockAlternatingSplit.for_archive(archive)
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(WORLD_SEED)
    start = EpisodeStartSampler.for_archive(archive, split, "train").draw(env_rng)
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=100), steps_per_episode=30),
    )
    candidates = [driver.reset(start, mobility_rng)]
    candidates.extend(driver.step(mobility_rng) for _ in range(2))
    provider = LegacyWorldProvider(steps=3)
    assert provider.cluster_identity(world_seed=WORLD_SEED)[0] == start.date().isoformat()
    return provider, driver, tuple(candidates), start


def test_decision_instant_geometry_and_gain_parity(real_world) -> None:
    provider, _driver, oracle, _start = real_world
    peak = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
    for step, candidates in enumerate(oracle):
        boundary = provider.boundary(
            world_seed=WORLD_SEED,
            step_index=step,
            boundary_index=0,
            absolute_time_s=step * 30.08,
        )
        actual = {(row.user_id, row.identity): row for row in boundary.candidates}
        norads = np.repeat(candidates.window_norad_ids, 7, axis=1)
        cells = np.stack([table.cell_ids for table in candidates.slot_tables])
        for user, action in zip(*np.nonzero(candidates.masks), strict=True):
            sat_slot, beam_slot = divmod(int(action), 7)
            identity = (int(norads[user, action]), int(cells[user, action]))
            row = actual[(int(user), identity)]
            elevation = float(candidates.elevation_deg[user, sat_slot])
            slant = float(candidates.slant_range_km[user, sat_slot])
            off_axis = float(candidates.off_axis_deg[user, sat_slot, beam_slot])
            old_tx = float(legacy_transmit_gain(np.asarray([off_axis]))[0])
            new_tx = float(transmit_gain_linear(off_axis))
            path = float(
                link_power_factor(
                    np.asarray([slant]),
                    np.asarray([elevation]),
                    np.asarray([peak]),
                )[0]
            )
            assert row.elevation_deg == pytest.approx(elevation, rel=1e-9)
            assert row.slant_km == pytest.approx(slant, rel=1e-9)
            assert new_tx == pytest.approx(old_tx, rel=1e-9)
            assert row.nominal_gain == pytest.approx(new_tx * path, rel=1e-9)


@pytest.mark.parametrize("boundary_index", (17, 47))
def test_sub_boundary_ecef_matches_direct_sgp4(real_world, boundary_index: int) -> None:
    provider, driver, _oracle, start = real_world
    detached = dict(
        provider.satellite_ecef_km(
            world_seed=WORLD_SEED,
            step_index=0,
            boundary_index=boundary_index,
        )
    )
    when = start + dt.timedelta(seconds=boundary_index * 0.640)
    jd, fr = step_times(when, 1, time_step_s=0.640)
    direct = driver._satellites.propagate_ecef(jd, fr, require_all_healthy=False)
    for index, norad in enumerate(driver.tracked_norad_ids.tolist()):
        error_m = (
            np.linalg.norm(np.asarray(detached[int(norad)]) - direct[index, 0])
            * 1000.0
        )
        assert error_m <= 1.0


def test_visibility_d2_and_entry_elevation_consistency(real_world) -> None:
    provider, _driver, oracle, _start = real_world
    boundary = provider.boundary(
        world_seed=WORLD_SEED,
        step_index=0,
        boundary_index=0,
        absolute_time_s=0.0,
    )
    assert all(
        row.visible == (row.elevation_deg >= 10.0)
        for row in boundary.candidates
    )
    candidates = oracle[0]
    norads = np.repeat(candidates.window_norad_ids, 7, axis=1)
    cells = np.stack([table.cell_ids for table in candidates.slot_tables])
    occupied_rows = np.repeat(candidates.slot_occupied, 7, axis=1)
    occupied = {
        (user, int(norad), int(cell)): bool(flag)
        for user in range(100)
        for norad, cell, flag in zip(
            norads[user].tolist(),
            cells[user].tolist(),
            occupied_rows[user].tolist(),
            strict=True,
        )
        if int(norad) >= 0 and int(cell) >= 0
    }
    for row in boundary.candidates:
        assert row.d2_eligible == occupied[(row.user_id, *row.identity)]

    measured = tuple(
        elevation_for_slant_range(
            D2_THRESHOLD_KM - D2_HYSTERESIS_KM, altitude
        )
        for altitude in (426.0, 485.0, 550.0)
    )
    assert measured == pytest.approx((19.7, 23.4, 27.7), abs=0.08)


def test_cross_gains_are_sorted_and_keyed_by_other_satellites(real_world) -> None:
    provider, _driver, _oracle, _start = real_world
    boundary = provider.boundary(
        world_seed=WORLD_SEED,
        step_index=0,
        boundary_index=0,
        absolute_time_s=0.0,
    )
    direct = {
        (row.user_id, row.identity): row.nominal_gain
        for row in boundary.candidates
    }
    for row in boundary.candidates:
        assert (
            tuple(sorted(row.nominal_cross_gain_by_norad))
            == row.nominal_cross_gain_by_norad
        )
        assert row.identity[0] not in dict(row.nominal_cross_gain_by_norad)
        assert all(
            gain >= 0.0 for _norad, gain in row.nominal_cross_gain_by_norad
        )
        for aggressor, gain in row.nominal_cross_gain_by_norad:
            aggressor_direct = direct.get(
                (row.user_id, (aggressor, row.identity[1]))
            )
            if aggressor_direct is not None:
                assert gain <= aggressor_direct * (1.0 + 1.0e-12)

    by_cell: dict[int, list[object]] = {}
    for row in boundary.candidates:
        by_cell.setdefault(row.identity[1], []).append(row)
    first, peer = next(
        (row, other)
        for group in by_cell.values()
        for row in group
        for other in group
        if other.user_id != row.user_id
        and other.identity[0] == row.identity[0]
        and tuple(n for n, _ in other.nominal_cross_gain_by_norad)
        == tuple(n for n, _ in row.nominal_cross_gain_by_norad)
    )
    assert tuple(n for n, _ in first.nominal_cross_gain_by_norad) == tuple(
        n for n, _ in peer.nominal_cross_gain_by_norad
    )


def test_inventory_is_a_superset_of_every_sampled_legal_identity(real_world) -> None:
    provider, _driver, _oracle, _start = real_world
    inventory = set(provider.inventory(world_seed=WORLD_SEED))
    for step in range(3):
        for boundary_index in (0, 17, 47):
            boundary = provider.boundary(
                world_seed=WORLD_SEED,
                step_index=step,
                boundary_index=boundary_index,
                absolute_time_s=step * 30.08 + boundary_index * 0.640,
            )
            assert {
                row.identity for row in boundary.candidates if row.legal
            } <= inventory


def test_provider_rejects_a_test_date_without_sampling_it() -> None:
    archive = TleArchive(DEFAULT_TLE_ROOT)
    split = BlockAlternatingSplit.for_archive(archive)
    test_date = split.available_dates(archive, TEST)[0]
    with pytest.raises(MCRLContractError, match="TRAIN-only"):
        LegacyWorldProvider(start_utc=test_date, steps=1)


def test_short_rehearsal_and_long_request_share_canonical_30_step_world() -> None:
    short = LegacyWorldProvider(steps=3)
    long = LegacyWorldProvider(steps=31)
    assert tuple(short.inventory(world_seed=WORLD_SEED)) == tuple(
        long.inventory(world_seed=WORLD_SEED)
    )
    assert tuple(short.user_layout(world_seed=WORLD_SEED)) == tuple(
        long.user_layout(world_seed=WORLD_SEED)
    )
    assert short.boundary(
        world_seed=WORLD_SEED,
        step_index=2,
        boundary_index=17,
        absolute_time_s=2 * 30.08 + 17 * 0.640,
    ) == long.boundary(
        world_seed=WORLD_SEED,
        step_index=2,
        boundary_index=17,
        absolute_time_s=2 * 30.08 + 17 * 0.640,
    )


def test_short_rehearsal_uses_the_canonical_thirty_step_universe(real_world) -> None:
    provider, _driver, _oracle, _start = real_world
    full = LegacyWorldProvider(steps=30)
    longer_request = LegacyWorldProvider(steps=31)
    assert tuple(provider.inventory(world_seed=WORLD_SEED)) == tuple(
        full.inventory(world_seed=WORLD_SEED)
    )
    assert tuple(longer_request.inventory(world_seed=WORLD_SEED)) == tuple(
        full.inventory(world_seed=WORLD_SEED)
    )
    assert provider.boundary(
        world_seed=WORLD_SEED,
        step_index=2,
        boundary_index=17,
        absolute_time_s=2 * 30.08 + 17 * 0.640,
    ) == full.boundary(
        world_seed=WORLD_SEED,
        step_index=2,
        boundary_index=17,
        absolute_time_s=2 * 30.08 + 17 * 0.640,
    )


def test_short_rehearsal_does_not_change_the_canonical_world(real_world) -> None:
    provider, _driver, _oracle, _start = real_world
    longer = LegacyWorldProvider(steps=31)
    assert tuple(provider.inventory(world_seed=WORLD_SEED)) == tuple(
        longer.inventory(world_seed=WORLD_SEED)
    )
    assert tuple(provider.user_layout(world_seed=WORLD_SEED)) == tuple(
        longer.user_layout(world_seed=WORLD_SEED)
    )
    left = provider.boundary(
        world_seed=WORLD_SEED,
        step_index=0,
        boundary_index=17,
        absolute_time_s=17 * 0.640,
    )
    right = longer.boundary(
        world_seed=WORLD_SEED,
        step_index=0,
        boundary_index=17,
        absolute_time_s=17 * 0.640,
    )
    assert left == right


def test_world_tape_digest_is_deterministic_and_seed_sensitive() -> None:
    digest1 = build_world_tape(
        domain=WORLD_DOMAIN,
        provider=LegacyWorldProvider(steps=1),
        steps=1,
        start_time_s=0.0,
    ).digest
    gc.collect()
    digest1_again = build_world_tape(
        domain=WORLD_DOMAIN,
        provider=LegacyWorldProvider(steps=1),
        steps=1,
        start_time_s=0.0,
    ).digest
    assert digest1 == digest1_again

    other_domain = "V025_PROBE/world/2"
    digest2 = build_world_tape(
        domain=other_domain,
        provider=LegacyWorldProvider(steps=1),
        steps=1,
        start_time_s=0.0,
    ).digest
    assert digest2 != digest1
