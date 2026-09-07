"""W-112 -- non-committing focal-removal physics for V0.7 C2."""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _environment(users: int = 20) -> StepEnvironment:
    return StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=users)),
        ),
        fading_field=KeyedFadingField.from_components(
            "test-w112-v07-focal-removal", "a" * 64, users
        ),
    )


def _first_valid_actions(masks: np.ndarray) -> np.ndarray:
    return np.asarray(
        [int(np.flatnonzero(mask)[0]) for mask in masks], dtype=np.int64
    )


def _semantic_state(environment: StepEnvironment) -> dict[str, object]:
    radiating = environment._previous_radiating
    return {
        "segments": tuple(environment._segments),
        "ledger_previous": tuple(
            ledger.previous for ledger in environment._ledgers
        ),
        "previous_association": tuple(environment._previous_association),
        "previous_demand": dict(environment._previous_demand),
        "previous_radiating_norads": radiating.norad_ids.copy(),
        "previous_radiating_cells": radiating.cell_ids.copy(),
        "previous_radiating_power": radiating.power_w.copy(),
        "candidate_identity": id(environment._candidates),
        "step_index": environment._step_index,
        "driver_start_utc": environment.driver._start_utc,
        "driver_step_index": environment.driver.step_index,
        "driver_user_ecef": environment.driver.user_ecef_km().copy(),
    }


def _assert_semantic_state_equal(
    before: dict[str, object], after: dict[str, object]
) -> None:
    assert before.keys() == after.keys()
    for key in before:
        left = before[key]
        right = after[key]
        if isinstance(left, np.ndarray):
            assert np.array_equal(left, right), key
        else:
            assert left == right, key


@requires_archive
def test_focal_removal_is_state_and_rng_neutral_and_removes_only_focal_rate() -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090201)
    observation = environment.reset(START, rng)
    actions = _first_valid_actions(observation.masks)
    focal = 3

    state_before = _semantic_state(environment)
    rng_before = copy.deepcopy(rng.bit_generator.state)
    full = environment.evaluate_actions(actions, rng)
    removed = environment.evaluate_actions_without_user(
        actions,
        rng,
        focal_user=focal,
    )

    _assert_semantic_state_equal(state_before, _semantic_state(environment))
    assert rng.bit_generator.state == rng_before
    assert bool(full.resolution.served[focal])
    assert not bool(removed.resolution.served[focal])
    assert removed.link_rate_bps[focal] == 0.0
    assert removed.link_power_w[focal] == 0.0
    assert np.array_equal(actions, _first_valid_actions(observation.masks))


@requires_archive
def test_keyed_full_and_removed_evaluations_are_order_independent() -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090204)
    observation = environment.reset(START, rng)
    actions = _first_valid_actions(observation.masks)
    focal = 4

    full_first = environment.evaluate_actions(actions, rng)
    removed_second = environment.evaluate_actions_without_user(
        actions, rng, focal_user=focal
    )
    removed_first = environment.evaluate_actions_without_user(
        actions, rng, focal_user=focal
    )
    full_second = environment.evaluate_actions(actions, rng)

    assert environment._fading_field is not None
    assert np.array_equal(full_first.link_rate_bps, full_second.link_rate_bps)
    assert full_first.system_power_w == full_second.system_power_w
    assert np.array_equal(
        removed_first.link_rate_bps, removed_second.link_rate_bps
    )
    assert removed_first.system_power_w == removed_second.system_power_w


@requires_archive
def test_focal_removal_does_not_make_noop_a_public_deployment_action() -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090202)
    observation = environment.reset(START, rng)
    actions = _first_valid_actions(observation.masks)
    actions[0] = -1

    with pytest.raises(MCRLContractError, match="no-op with"):
        environment.evaluate_actions(actions, rng)
    with pytest.raises(MCRLContractError, match="no-op with"):
        environment.evaluate_actions_without_user(actions, rng, focal_user=1)


@requires_archive
@pytest.mark.parametrize("focal", [-1, 20, 1.5])
def test_focal_removal_rejects_invalid_user_indices(focal: int | float) -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090203)
    observation = environment.reset(START, rng)
    actions = _first_valid_actions(observation.masks)

    with pytest.raises(MCRLContractError, match="focal_user"):
        environment.evaluate_actions_without_user(
            actions,
            rng,
            focal_user=focal,  # type: ignore[arg-type]
        )
