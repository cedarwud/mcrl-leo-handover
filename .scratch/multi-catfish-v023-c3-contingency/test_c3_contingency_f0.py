"""Focused F0 mechanics tests; no simulator or learner is imported."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.env.link_budget import (
    fixed_power_w,
    pa_efficiency,
    supply_power_w,
    system_power_w,
)

from c3_contingency_f0 import (
    BASEBAND_POWER_PER_SATELLITE_W,
    C3F0Error,
    PhysicalProfile,
    compute_c3_targets,
    compute_cost_shares,
)


def _profile(
    *,
    rates: list[float] | np.ndarray,
    served: list[bool] | np.ndarray,
    serving_satellite: list[int] | np.ndarray,
    serving_cell: list[int] | np.ndarray,
    active_beam_satellites: list[int] | np.ndarray,
    active_beam_cells: list[int] | np.ndarray,
    beam_power_w: list[float] | np.ndarray,
    interval_s: float = 2.0,
    fixed_power_override: float | None = None,
    system_power_override: float | None = None,
) -> PhysicalProfile:
    """Build a valid profile with receipts from the canonical power functions."""

    beam_satellites = np.asarray(active_beam_satellites, dtype=np.int64)
    powers = np.asarray(beam_power_w, dtype=np.float64)
    supply = supply_power_w(powers, pa_efficiency(powers))
    active_satellites = np.unique(beam_satellites)
    counts = np.asarray(
        [np.count_nonzero(beam_satellites == satellite) for satellite in active_satellites],
        dtype=np.float64,
    )
    fixed = fixed_power_w(counts)
    system = system_power_w(supply, counts)
    return PhysicalProfile(
        link_rate_bps=np.asarray(rates, dtype=np.float64),
        served=np.asarray(served, dtype=np.bool_),
        serving_satellite=np.asarray(serving_satellite),
        serving_cell=np.asarray(serving_cell),
        active_beam_satellites=beam_satellites,
        active_beam_cells=np.asarray(active_beam_cells, dtype=np.int64),
        beam_power_w=powers,
        fixed_power_w=fixed if fixed_power_override is None else fixed_power_override,
        system_power_w=system if system_power_override is None else system_power_override,
        interval_s=interval_s,
    )


def _one_user_profile(*, satellite: int = 10, cell: int = 1, power: float = 1.0) -> PhysicalProfile:
    return _profile(
        rates=[100.0],
        served=[True],
        serving_satellite=[satellite],
        serving_cell=[cell],
        active_beam_satellites=[satellite],
        active_beam_cells=[cell],
        beam_power_w=[power],
    )


def test_one_user_receives_the_full_beam_and_satellite_share() -> None:
    profile = _one_user_profile()

    result = compute_cost_shares(profile)

    assert result.beam_occupancy.tolist() == [1]
    assert result.satellite_occupancy.tolist() == [1]
    assert result.beam_share_power_w[0] == pytest.approx(result.beam_cost_power_w[0])
    assert result.satellite_share_power_w[0] == pytest.approx(
        BASEBAND_POWER_PER_SATELLITE_W
    )
    assert result.sum_share_power_w == pytest.approx(profile.system_power_w)
    assert result.sum_share_energy_j == pytest.approx(profile.network_energy_j)


def test_shared_beam_splits_beam_and_satellite_costs_by_served_occupancy() -> None:
    profile = _profile(
        rates=[100.0, 90.0],
        served=[True, True],
        serving_satellite=[10, 10],
        serving_cell=[1, 1],
        active_beam_satellites=[10],
        active_beam_cells=[1],
        beam_power_w=[1.5],
    )

    result = compute_cost_shares(profile)

    assert result.beam_occupancy.tolist() == [2]
    assert result.satellite_occupancy.tolist() == [2]
    assert result.beam_share_power_w[0] == pytest.approx(
        result.beam_cost_power_w[0] / 2.0
    )
    assert result.beam_share_power_w[1] == pytest.approx(
        result.beam_cost_power_w[0] / 2.0
    )
    assert np.allclose(
        result.satellite_share_power_w,
        BASEBAND_POWER_PER_SATELLITE_W / 2.0,
    )
    assert result.sum_beam_share_power_w == pytest.approx(
        result.beam_cost_power_w[0]
    )


def test_shared_satellite_splits_only_the_satellite_baseband_charge() -> None:
    profile = _profile(
        rates=[100.0, 90.0],
        served=[True, True],
        serving_satellite=[10, 10],
        serving_cell=[1, 2],
        active_beam_satellites=[10, 10],
        active_beam_cells=[1, 2],
        beam_power_w=[1.0, 1.5],
    )

    result = compute_cost_shares(profile)

    assert result.beam_occupancy.tolist() == [1, 1]
    assert result.satellite_occupancy.tolist() == [2]
    assert result.beam_share_power_w == pytest.approx(result.beam_cost_power_w)
    assert result.satellite_share_power_w.tolist() == pytest.approx(
        [BASEBAND_POWER_PER_SATELLITE_W / 2.0] * 2
    )
    assert result.sum_share_power_w == pytest.approx(profile.system_power_w)


def test_beam_extinction_removes_the_extinguished_beam_from_the_profile_bill() -> None:
    reference = _one_user_profile(satellite=10, cell=1, power=1.0)
    candidate = _one_user_profile(satellite=10, cell=2, power=0.8)

    reference_share = compute_cost_shares(reference)
    candidate_share = compute_cost_shares(candidate)

    assert (10, 1) not in [tuple(row) for row in candidate.active_beam_keys.tolist()]
    assert reference_share.total_share_power_w[0] != pytest.approx(
        candidate_share.total_share_power_w[0]
    )
    assert candidate_share.sum_share_power_w == pytest.approx(candidate.system_power_w)


def test_new_beam_and_new_satellite_receive_new_canonical_charges() -> None:
    reference = _one_user_profile(satellite=10, cell=1, power=1.0)
    candidate = _one_user_profile(satellite=20, cell=9, power=1.0)

    result = compute_cost_shares(candidate)

    assert result.active_satellite_ids.tolist() == [20]
    assert result.beam_occupancy.tolist() == [1]
    assert result.satellite_occupancy.tolist() == [1]
    assert result.total_share_power_w[0] == pytest.approx(candidate.system_power_w)
    assert result.sum_share_power_w == pytest.approx(candidate.system_power_w)
    assert compute_cost_shares(reference).sum_share_power_w == pytest.approx(
        reference.system_power_w
    )


def test_unserved_user_has_no_beam_or_satellite_share_and_mask_is_preserved() -> None:
    profile = _profile(
        rates=[100.0, 0.0],
        served=[True, False],
        serving_satellite=[10, -1],
        serving_cell=[1, -1],
        active_beam_satellites=[10],
        active_beam_cells=[1],
        beam_power_w=[1.0],
    )

    result = compute_cost_shares(profile)

    assert np.array_equal(result.served, np.asarray([True, False], dtype=np.bool_))
    assert result.total_share_power_w[1] == 0.0
    assert result.beam_share_power_w[1] == 0.0
    assert result.satellite_share_power_w[1] == 0.0
    assert not result.total_share_power_w.flags.writeable
    assert not result.served.flags.writeable


def test_reference_centering_and_deterministic_replay_are_exact() -> None:
    reference = _profile(
        rates=[100.0, 80.0],
        served=[True, True],
        serving_satellite=[10, 10],
        serving_cell=[1, 2],
        active_beam_satellites=[10, 10],
        active_beam_cells=[1, 2],
        beam_power_w=[1.0, 1.5],
    )
    candidate = replace(
        reference,
        link_rate_bps=np.array(reference.link_rate_bps, copy=True),
        served=np.array(reference.served, copy=True),
        serving_satellite=np.array(reference.serving_satellite, copy=True),
        serving_cell=np.array(reference.serving_cell, copy=True),
        active_beam_satellites=np.array(reference.active_beam_satellites, copy=True),
        active_beam_cells=np.array(reference.active_beam_cells, copy=True),
        beam_power_w=np.array(reference.beam_power_w, copy=True),
    )

    first = compute_c3_targets(
        reference,
        candidate,
        focal_user=0,
        lambda_bits_per_j=1.25,
    )
    second = compute_c3_targets(
        reference,
        candidate,
        focal_user=0,
        lambda_bits_per_j=1.25,
    )

    assert first.d_bits == 0.0
    assert first.f_bits == 0.0
    assert first == second
    assert first.nonfocal_delta_bits == 0.0
    assert first.share_delta_energy_j == 0.0
    assert first.network_delta_energy_j == 0.0


def test_permuting_active_beam_rows_does_not_change_user_shares() -> None:
    profile = _profile(
        rates=[100.0, 80.0, 70.0],
        served=[True, True, True],
        serving_satellite=[10, 20, 10],
        serving_cell=[1, 3, 2],
        active_beam_satellites=[10, 20, 10],
        active_beam_cells=[1, 3, 2],
        beam_power_w=[1.0, 1.4, 0.7],
    )
    permutation = np.asarray([2, 0, 1], dtype=np.int64)
    permuted = replace(
        profile,
        active_beam_satellites=profile.active_beam_satellites[permutation],
        active_beam_cells=profile.active_beam_cells[permutation],
        beam_power_w=profile.beam_power_w[permutation],
    )

    original = compute_cost_shares(profile)
    reordered = compute_cost_shares(permuted)

    assert reordered.sum_share_power_w == original.sum_share_power_w
    assert reordered.sum_share_energy_j == original.sum_share_energy_j
    assert np.array_equal(reordered.beam_share_power_w, original.beam_share_power_w)
    assert np.array_equal(
        reordered.satellite_share_power_w,
        original.satellite_share_power_w,
    )
    assert np.array_equal(reordered.total_share_energy_j, original.total_share_energy_j)


def test_conservation_reports_beam_and_satellite_components_separately() -> None:
    profile = _profile(
        rates=[100.0, 90.0, 80.0, 70.0],
        served=[True, True, True, True],
        serving_satellite=[10, 10, 10, 20],
        serving_cell=[1, 1, 2, 4],
        active_beam_satellites=[10, 10, 20],
        active_beam_cells=[1, 2, 4],
        beam_power_w=[1.0, 1.5, 0.8],
    )

    result = compute_cost_shares(profile)

    assert result.sum_beam_share_power_w == pytest.approx(
        float(result.beam_cost_power_w.sum())
    )
    assert result.sum_satellite_share_power_w == pytest.approx(
        2.0 * 0.200
    )
    assert result.sum_share_power_w == pytest.approx(
        result.canonical_network_power_w
    )
    assert result.conservation_residual_power_w == pytest.approx(0.0, abs=1.0e-12)
    assert result.sum_share_energy_j == pytest.approx(profile.network_energy_j)
    assert result.conservation_residual_energy_j == pytest.approx(0.0, abs=1.0e-12)


def test_frozen_d_and_f_formulas_keep_signed_values_without_filtering() -> None:
    # The focal user leaves a private beam and joins the other user's beam.
    # The fair share rises by less than the network saving, making F negative.
    reference = _profile(
        rates=[100.0, 100.0],
        served=[True, True],
        serving_satellite=[10, 10],
        serving_cell=[1, 2],
        active_beam_satellites=[10, 10],
        active_beam_cells=[1, 2],
        beam_power_w=[1.0, 2.0],
    )
    candidate = _profile(
        rates=[80.0, 50.0],
        served=[True, True],
        serving_satellite=[10, 10],
        serving_cell=[2, 2],
        active_beam_satellites=[10],
        active_beam_cells=[2],
        beam_power_w=[2.0],
    )

    targets = compute_c3_targets(
        reference,
        candidate,
        focal_user=0,
        lambda_bits_per_j=1.0,
    )
    reference_share = compute_cost_shares(reference)
    candidate_share = compute_cost_shares(candidate)
    expected_f = -(
        float(candidate_share.total_share_energy_j[0])
        - float(reference_share.total_share_energy_j[0])
        - (candidate.network_energy_j - reference.network_energy_j)
    )
    expected_d = 2.0 * (50.0 - 100.0) + expected_f

    assert targets.f_bits == pytest.approx(expected_f)
    assert targets.d_bits == pytest.approx(expected_d)
    assert targets.f_bits < 0.0
    assert targets.d_bits < 0.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("link_rate_bps", np.asarray([np.inf])),
        ("beam_power_w", np.asarray([np.nan])),
        ("fixed_power_w", np.inf),
        ("system_power_w", np.nan),
        ("interval_s", np.inf),
    ],
)
def test_nonfinite_profile_fields_are_rejected(field: str, value: object) -> None:
    valid = _one_user_profile()

    with pytest.raises(C3F0Error):
        replace(valid, **{field: value})


def test_nonfinite_lambda_is_rejected_before_target_arithmetic() -> None:
    profile = _one_user_profile()

    with pytest.raises(C3F0Error):
        compute_c3_targets(
            profile,
            profile,
            focal_user=0,
            lambda_bits_per_j=np.inf,
        )


def test_shape_and_integer_identity_validation_is_fail_closed() -> None:
    with pytest.raises(C3F0Error):
        _profile(
            rates=[100.0, 90.0],
            served=[True],
            serving_satellite=[10, 10],
            serving_cell=[1, 1],
            active_beam_satellites=[10],
            active_beam_cells=[1],
            beam_power_w=[1.0],
        )
    with pytest.raises(C3F0Error):
        _profile(
            rates=[100.0],
            served=[True],
            serving_satellite=[10.0],
            serving_cell=[1],
            active_beam_satellites=[10],
            active_beam_cells=[1],
            beam_power_w=[1.0],
        )


def test_deliberately_forged_nonconserving_profile_is_rejected() -> None:
    valid = _one_user_profile()
    forged = replace(valid, system_power_w=valid.system_power_w + 0.5)

    with pytest.raises(C3F0Error, match="declared system power"):
        compute_cost_shares(forged)
