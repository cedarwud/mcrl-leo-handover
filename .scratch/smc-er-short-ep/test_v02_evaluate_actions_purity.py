"""V0.2 prerequisite: C1 comparator evaluation is state/RNG neutral."""

from __future__ import annotations

import copy
import datetime as dt
import os
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive


TLE_ROOT = Path(
    os.environ.get(
        "MCRL_V02_TLE_ROOT", "/tmp/mcrl-tle-frozen-20260820-v1"
    )
).expanduser()
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


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


def _assert_state_equal(
    before: dict[str, object], after: dict[str, object]
) -> None:
    assert before.keys() == after.keys()
    for key, left in before.items():
        right = after[key]
        if isinstance(left, np.ndarray):
            assert np.array_equal(left, right), key
        else:
            assert left == right, key


@pytest.mark.skipif(not TLE_ROOT.is_dir(), reason="frozen V0.2 TLE missing")
def test_evaluate_actions_uses_copied_rng_and_does_not_mutate_environment():
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(TLE_ROOT),
            ScenarioConfig(mobility=MobilityConfig(num_users=20)),
        )
    )
    rng = np.random.default_rng(2026082804)
    observation = environment.reset(START, rng)
    actions = np.asarray(
        [int(np.flatnonzero(mask)[0]) for mask in observation.masks],
        dtype=np.int64,
    )
    state_before = _semantic_state(environment)
    rng_before = copy.deepcopy(rng.bit_generator.state)

    preview = environment.evaluate_actions(actions, rng)

    _assert_state_equal(state_before, _semantic_state(environment))
    assert rng.bit_generator.state == rng_before
    committed = environment.step(actions, rng)
    assert np.array_equal(preview.reward_matrix, committed.reward_matrix)
    assert np.array_equal(preview.link_rate_bps, committed.link_rate_bps)
    assert preview.system_power_w == committed.system_power_w

