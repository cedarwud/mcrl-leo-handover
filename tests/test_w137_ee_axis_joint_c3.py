"""W-137 -- reusable V0.11 joint-C3 runtime mechanics."""

from __future__ import annotations

import copy
import datetime as dt
import math
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import NO_OP_ACTION
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_joint_c3 import (
    JointC3Error,
    build_ap_mone_surface,
    build_focal_joint_c3_row,
    select_masked_actions,
    solve_exact_o1_joint_c3,
    solve_m1d_joint_c3,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
LAMBDA = 1.25e8
KAPPA = 1.0e10


def _environment(*, users: int = 2):
    field = KeyedFadingField.from_components("w137-test", 1, users)
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=users)),
        ),
        fading_field=field,
    )
    rng = np.random.default_rng(2026090302)
    observation = environment.reset(START, rng)
    return environment, observation, rng


def _reference(observation) -> np.ndarray:
    result = np.full(observation.num_users, NO_OP_ACTION, dtype=np.int64)
    for uid, mask in enumerate(observation.masks):
        legal = np.flatnonzero(mask)
        if legal.size:
            result[uid] = int(legal[0])
    return result


def _live_state(environment: StepEnvironment, rng: np.random.Generator):
    return {
        "rng": copy.deepcopy(rng.bit_generator.state),
        "step": environment._step_index,
        "driver_step": environment.driver.step_index,
        "candidates": environment._candidates,
        "segments": copy.deepcopy(environment._segments),
        "associations": copy.deepcopy(environment._previous_association),
        "powers": np.asarray(environment._previous_link_power_w).copy(),
    }


def _assert_live_equal(left, right) -> None:
    assert left["rng"] == right["rng"]
    assert left["step"] == right["step"]
    assert left["driver_step"] == right["driver_step"]
    assert left["candidates"] is right["candidates"]
    assert left["segments"] == right["segments"]
    assert left["associations"] == right["associations"]
    np.testing.assert_array_equal(left["powers"], right["powers"])


@requires_archive
def test_focal_row_matches_exact_current_joint_physics_and_is_neutral() -> None:
    environment, observation, rng = _environment()
    reference = _reference(observation)
    uid = next(uid for uid, mask in enumerate(observation.masks) if np.count_nonzero(mask) >= 2)
    action = int(np.flatnonzero(observation.masks[uid])[1])
    interval = float(environment.driver.config.ephemeris.time_step_s)
    before = _live_state(environment, rng)
    row = build_focal_joint_c3_row(
        environment, observation=observation, reference_joint_actions=reference,
        focal_user=uid, rng=rng, lambda_bits_per_j=LAMBDA, interval_s=interval,
        kappa_bits=KAPPA,
    )
    baseline = environment.evaluate_actions(reference, rng)
    candidate = reference.copy()
    candidate[uid] = action
    evaluation = environment.evaluate_actions(candidate, rng)
    rates = np.asarray(evaluation.link_rate_bps) - np.asarray(baseline.link_rate_bps)
    focal = interval * float(rates[uid])
    nonfocal = interval * math.fsum(float(rates[v]) for v in range(reference.size) if v != uid)
    energy = interval * (float(evaluation.system_power_w) - float(baseline.system_power_w))
    assert row.z1_bits[action] == pytest.approx(focal - LAMBDA * energy)
    assert row.z3_bits[action] == pytest.approx(nonfocal)
    assert row.z1_bits[action] + row.z3_bits[action] == pytest.approx(row.system_surplus_bits[action])
    assert row.q3_values[int(reference[uid])] == 0.0
    assert not row.q3_values.flags.writeable
    _assert_live_equal(before, _live_state(environment, rng))


@requires_archive
def test_m1d_uses_fixed_order_and_requires_one_pass_equivalence() -> None:
    environment, observation, rng = _environment()
    reference = _reference(observation)
    q1 = np.zeros((observation.num_users, 28), dtype=np.float64)
    o2 = np.zeros_like(q1)
    # Pin every reference at a scale safely beyond the normalized C3 surface.
    for uid, action in enumerate(reference.tolist()):
        if action >= 0:
            q1[uid, action] = 1.0e12
    result = solve_m1d_joint_c3(
        environment, observation=observation, initial_actions=reference,
        q1_values=q1, o2_values=o2, rng=rng, lambda_bits_per_j=LAMBDA,
        kappa_bits=KAPPA, max_sweeps=5,
    )
    assert result.status == "CONVERGED"
    assert result.sweep_count == 1
    assert result.changed_per_sweep.tolist() == [0]
    np.testing.assert_array_equal(result.final_iterate_actions, reference)
    np.testing.assert_array_equal(result.production_actions, reference)
    assert result.surfaces is not None
    assert not result.final_iterate_actions.flags.writeable


@requires_archive
def test_exact_o1_drop_and_full_converge_with_one_pass_and_full_receipts() -> None:
    environment, observation, rng = _environment()
    reference = _reference(observation)
    o2 = np.zeros((observation.num_users, 28), dtype=np.float64)
    # A fixed separable O2 margin gives both diagnostics a known fixed point;
    # C3's coordinate receipt must still be non-decreasing at every visit.
    for uid, action in enumerate(reference.tolist()):
        if action >= 0:
            o2[uid, action] = 1.0e12
    drop = solve_exact_o1_joint_c3(
        environment, observation=observation, initial_actions=reference,
        o2_values=o2, include_c3=False, rng=rng, lambda_bits_per_j=LAMBDA,
        kappa_bits=KAPPA, max_sweeps=5,
    )
    full = solve_exact_o1_joint_c3(
        environment, observation=observation, initial_actions=reference,
        o2_values=o2, include_c3=True, rng=rng, lambda_bits_per_j=LAMBDA,
        kappa_bits=KAPPA, max_sweeps=5,
    )
    for result in (drop, full):
        assert result.status == "CONVERGED"
        assert result.sweep_count == 1
        np.testing.assert_array_equal(result.final_iterate_actions, reference)
        np.testing.assert_array_equal(result.production_actions, reference)
        assert result.surfaces is not None
    assert full.coordinate_objective_deltas.size == observation.num_users
    assert not np.any(full.monotonicity_violations)
    assert np.all(full.coordinate_objective_deltas >= -1.0e-12)
    assert not full.coordinate_objective_deltas.flags.writeable


@requires_archive
def test_ap_mone_has_reference_zeros_and_exact_two_order_telescoping() -> None:
    environment, observation, rng = _environment()
    reference = _reference(observation)
    q1 = np.zeros((observation.num_users, 28), dtype=np.float64)
    o2 = np.zeros_like(q1)
    # Make a nontrivial proposal where a second legal action exists.
    changed = 0
    for uid, mask in enumerate(observation.masks):
        legal = np.flatnonzero(mask)
        if legal.size >= 2:
            q1[uid, int(legal[1])] = 1.0
            changed += 1
    assert changed > 0
    surface = build_ap_mone_surface(
        environment, observation=observation, reference_actions=reference,
        q1_values=q1, o2_values=o2,
        permutation=np.arange(observation.num_users, dtype=np.int64), rng=rng,
        lambda_bits_per_j=LAMBDA, kappa_bits=KAPPA,
    )
    assert np.any(surface.proposal_actions != reference)
    for uid, action in enumerate(reference.tolist()):
        if action >= 0:
            assert surface.z1_bits[uid, action] == 0.0
            assert surface.z3_bits[uid, action] == 0.0
            assert surface.q3_values[uid, action] == 0.0
    np.testing.assert_allclose(surface.order_identity_residual_bits, 0.0, rtol=0.0, atol=1.0e-5)
    assert not surface.permutation.flags.writeable


def test_selector_rejects_non_boolean_mask_and_keeps_lowest_native_tie() -> None:
    q = np.zeros((2, 28), dtype=np.float64)
    mask = np.zeros((2, 28), dtype=np.bool_)
    mask[0, [3, 7]] = True
    mask[1, [2, 9]] = True
    assert select_masked_actions(q, q, q, mask).tolist() == [3, 2]
    with pytest.raises(JointC3Error, match="Boolean"):
        select_masked_actions(q, q, q, mask.astype(np.int8))
