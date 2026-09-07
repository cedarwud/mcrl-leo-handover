"""W-135 -- exact matched-opening O1/O3 surfaces for the C3 redesign."""

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
from mcrl.runtime.ee_axis_matched_opening import (
    MatchedOpeningError,
    build_matched_opening_surfaces,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _environment(*, keyed: bool = True, users: int = 4):
    field = (
        KeyedFadingField.from_components("w135-test", 1, users)
        if keyed
        else None
    )
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=users)),
        ),
        fading_field=field,
    )
    rng = np.random.default_rng(2026090301)
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
        "users": environment.driver.user_ecef_km().copy(),
    }


def _assert_live_equal(left, right) -> None:
    assert left["rng"] == right["rng"]
    assert left["step"] == right["step"]
    assert left["driver_step"] == right["driver_step"]
    assert left["candidates"] is right["candidates"]
    assert left["segments"] == right["segments"]
    assert left["associations"] == right["associations"]
    np.testing.assert_array_equal(left["powers"], right["powers"])
    np.testing.assert_array_equal(left["users"], right["users"])


@requires_archive
def test_every_legal_surface_entry_matches_canonical_unilateral_physics() -> None:
    environment, observation, rng = _environment()
    reference = _reference(observation)
    interval = float(environment.driver.config.ephemeris.time_step_s)
    multiplier = 1.25e8
    kappa = 1.0e10
    before = _live_state(environment, rng)

    surfaces = build_matched_opening_surfaces(
        environment,
        observation=observation,
        reference_joint_actions=reference,
        rng=rng,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        kappa_bits=kappa,
    )
    reference_evaluation = environment.evaluate_actions(reference, rng)

    for uid, mask in enumerate(observation.masks):
        for action in np.flatnonzero(mask).tolist():
            candidate = reference.copy()
            candidate[uid] = int(action)
            evaluation = environment.evaluate_actions(candidate, rng)
            rate_delta = (
                np.asarray(evaluation.link_rate_bps)
                - np.asarray(reference_evaluation.link_rate_bps)
            )
            focal = interval * float(rate_delta[uid])
            nonfocal = interval * math.fsum(
                float(rate_delta[v])
                for v in range(observation.num_users)
                if v != uid
            )
            energy = interval * (
                float(evaluation.system_power_w)
                - float(reference_evaluation.system_power_w)
            )
            assert surfaces.focal_delta_bits[uid, action] == pytest.approx(focal)
            assert surfaces.nonfocal_delta_bits[uid, action] == pytest.approx(
                nonfocal
            )
            assert surfaces.network_delta_energy_j[uid, action] == pytest.approx(
                energy
            )
            assert surfaces.z1_bits[uid, action] == pytest.approx(
                focal - multiplier * energy
            )
            assert surfaces.z3_bits[uid, action] == pytest.approx(nonfocal)
            assert surfaces.q1_values[uid, action] == pytest.approx(
                surfaces.z1_bits[uid, action] / kappa
            )
            assert surfaces.q3_values[uid, action] == pytest.approx(nonfocal / kappa)

    np.testing.assert_allclose(
        surfaces.z1_bits + surfaces.z3_bits,
        surfaces.system_surplus_bits,
        rtol=0.0,
        atol=1.0e-5,
    )
    _assert_live_equal(before, _live_state(environment, rng))


@requires_archive
def test_reference_rows_and_unsafe_entries_are_exact_zero_and_immutable() -> None:
    environment, observation, rng = _environment()
    reference = _reference(observation)
    surfaces = build_matched_opening_surfaces(
        environment,
        observation=observation,
        reference_joint_actions=reference,
        rng=rng,
        lambda_bits_per_j=1.25e8,
    )
    for uid, action in enumerate(reference.tolist()):
        if action >= 0:
            assert surfaces.q1_values[uid, action] == 0.0
            assert surfaces.q3_values[uid, action] == 0.0
    assert np.all(surfaces.q1_values[~observation.masks] == 0.0)
    assert np.all(surfaces.q3_values[~observation.masks] == 0.0)
    assert not surfaces.q1_values.flags.writeable
    assert not surfaces.q3_values.flags.writeable
    assert not surfaces.reference_joint_actions.flags.writeable
    with pytest.raises(ValueError):
        surfaces.q3_values[0, 0] = 1.0


@requires_archive
def test_builder_rejects_non_keyed_or_illegal_backgrounds() -> None:
    environment, observation, rng = _environment(keyed=False)
    reference = _reference(observation)
    with pytest.raises(MatchedOpeningError, match="keyed fading"):
        build_matched_opening_surfaces(
            environment,
            observation=observation,
            reference_joint_actions=reference,
            rng=rng,
            lambda_bits_per_j=1.25e8,
        )

    environment, observation, rng = _environment()
    invalid = _reference(observation)
    served = next(uid for uid, action in enumerate(invalid.tolist()) if action >= 0)
    invalid[served] = 28
    with pytest.raises(MatchedOpeningError, match="not safe"):
        build_matched_opening_surfaces(
            environment,
            observation=observation,
            reference_joint_actions=invalid,
            rng=rng,
            lambda_bits_per_j=1.25e8,
        )
