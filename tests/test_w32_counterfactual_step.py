"""W-32 — matched-state, common-random-number action evaluation."""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive


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
        )
    )


def _first_valid_actions(masks: np.ndarray) -> np.ndarray:
    return np.asarray(
        [int(np.flatnonzero(mask)[0]) for mask in masks], dtype=np.int64
    )


def _semantic_state(environment: StepEnvironment) -> dict[str, object]:
    """State a current-step evaluator is forbidden to change."""
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
def test_action_evaluation_is_neutral_and_matches_the_committed_step():
    environment = _environment()
    rng = np.random.default_rng(2026082401)
    observation = environment.reset(START, rng)
    actions = _first_valid_actions(observation.masks)

    state_before = _semantic_state(environment)
    rng_before = copy.deepcopy(rng.bit_generator.state)
    preview = environment.evaluate_actions(actions, rng)

    _assert_semantic_state_equal(state_before, _semantic_state(environment))
    assert rng.bit_generator.state == rng_before

    outcome = environment.step(actions, rng)
    assert np.array_equal(preview.reward_matrix, outcome.reward_matrix)
    assert preview.handovers == outcome.handovers
    assert np.array_equal(preview.resolution.served, outcome.resolution.served)
    assert np.array_equal(preview.link_power_w, outcome.link_power_w)
    assert np.array_equal(preview.link_sinr, outcome.link_sinr)
    assert np.array_equal(preview.link_rate_bps, outcome.link_rate_bps)
    assert np.array_equal(
        preview.interference.total_w, outcome.interference.total_w
    )
    assert np.array_equal(preview.radiating.norad_ids, outcome.radiating.norad_ids)
    assert np.array_equal(preview.radiating.cell_ids, outcome.radiating.cell_ids)
    assert np.array_equal(preview.radiating.power_w, outcome.radiating.power_w)
    assert preview.energy == outcome.energy
    assert preview.system_power_w == outcome.system_power_w
    assert preview.fixed_power_w == outcome.fixed_power_w


def test_action_evaluation_fails_before_reset():
    environment = _environment(users=1)
    with pytest.raises(Exception, match="has not been reset"):
        environment.evaluate_actions(np.zeros(1, dtype=np.int64), np.random.default_rng(0))
