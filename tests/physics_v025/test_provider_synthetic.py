from __future__ import annotations

import math

import pytest

from mcrl.physics_v025.provider_synthetic import (
    MAP_LAST_BOUNDARY_S,
    ParametricSyntheticProvider,
    entry_elevation_deg,
    slant_range_km,
)
from mcrl.physics_v025.architectures import RadiationConfig, architecture_for
from mcrl.physics_v025.tapes import PROBE_WORLD_DOMAINS, build_world_tape, seed_from_domain


@pytest.mark.parametrize("occupancy", [1.5, 4.0, 8.0])
@pytest.mark.parametrize("satellites", [2, 4])
def test_requested_occupancy_and_satellite_inventory_are_realised(occupancy, satellites) -> None:
    provider = ParametricSyntheticProvider(occupancy, satellites, -25.0, 7)
    boundary = provider.boundary(
        world_seed=11, step_index=15, boundary_index=0, absolute_time_s=MAP_LAST_BOUNDARY_S / 2
    )
    counts = provider.occupancy_by_beam(boundary)
    assert sum(counts.values()) / len(counts) == pytest.approx(occupancy, rel=0.10)
    assert all(count == int(occupancy) for count in counts.values()) if occupancy != 1.5 else sorted(set(counts.values())) == [1, 2]
    assert all(
        len({row.identity[0] for row in boundary.candidates if row.user_id == user}) == satellites
        for user in range(provider.user_count)
    )
    assert set(row.identity for row in boundary.candidates) <= set(provider.inventory(world_seed=11))


@pytest.mark.parametrize("coupling_db", [-25.0, -12.0])
def test_requested_co_colour_coupling_is_realised(coupling_db) -> None:
    provider = ParametricSyntheticProvider(4.0, 4, coupling_db, 8)
    boundary = provider.boundary(
        world_seed=12, step_index=15, boundary_index=0, absolute_time_s=MAP_LAST_BOUNDARY_S / 2
    )
    for row in boundary.candidates:
        ratios = [gain / row.nominal_gain for _, gain in row.nominal_cross_gain_by_norad]
        assert all(10.0 * math.log10(ratio) == pytest.approx(coupling_db, abs=0.5) for ratio in ratios)


def test_pass_elevation_is_monotone_up_then_down_and_range_is_550km_consistent() -> None:
    provider = ParametricSyntheticProvider(1.5, 2, -25.0, 9)
    samples = [
        provider.boundary(
            world_seed=13,
            step_index=0,
            boundary_index=index,
            absolute_time_s=index * MAP_LAST_BOUNDARY_S / 100,
        ).candidates[0]
        for index in range(101)
    ]
    peak = max(range(len(samples)), key=lambda index: samples[index].elevation_deg)
    assert [row.elevation_deg for row in samples[: peak + 1]] == sorted(
        row.elevation_deg for row in samples[: peak + 1]
    )
    assert [row.elevation_deg for row in samples[peak:]] == sorted(
        (row.elevation_deg for row in samples[peak:]), reverse=True
    )
    assert samples[0].elevation_deg == samples[-1].elevation_deg == pytest.approx(10.0)
    assert samples[peak].elevation_deg == pytest.approx(60.0, abs=0.6)
    assert all(row.slant_km == pytest.approx(slant_range_km(row.elevation_deg)) for row in samples)
    assert entry_elevation_deg() == pytest.approx(27.65, abs=0.05)


def test_provider_and_tape_digests_are_deterministic() -> None:
    provider_a = ParametricSyntheticProvider(4.0, 2, -12.0, 10)
    provider_b = ParametricSyntheticProvider(4.0, 2, -12.0, 10)
    domain = PROBE_WORLD_DOMAINS[0]
    tape_a = build_world_tape(domain=domain, provider=provider_a, steps=2, start_time_s=0.0)
    tape_b = build_world_tape(domain=domain, provider=provider_b, steps=2, start_time_s=0.0)
    assert provider_a.parameter_digest == provider_b.parameter_digest
    assert tape_a.digest == tape_b.digest
    assert tape_a.inventory_digest == tape_b.inventory_digest
    assert tape_a.seed == seed_from_domain(domain)


def test_rate_target_fixed_point_accepts_power_tolerance_scale_clearance() -> None:
    """KAT for the large-world ulp-at-clearance iteration-cap pathology."""

    provider = ParametricSyntheticProvider(8.0, 4, -12.0, 10_000)
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0], provider=provider, steps=1, start_time_s=435.0
    )
    first = tape.steps[0].boundaries[0]
    by_user = {
        user: sorted(row.identity for row in first.candidates if row.user_id == user and row.legal)
        for user in range(provider.user_count)
    }
    assignments = {
        user: identities[0 if user < 2 else -1] for user, identities in by_user.items()
    }
    geometry = tape.geometry_for(step_index=0, assignments=assignments)[1][1]
    result = architecture_for("a-r").radiate(RadiationConfig(), geometry, "nominal")
    assert result.valid
    assert result.certificate.iterations < RadiationConfig().solver_iteration_cap
