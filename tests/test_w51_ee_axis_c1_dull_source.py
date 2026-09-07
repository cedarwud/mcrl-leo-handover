"""W-51 — real keyed C1 dull-rollout source capture."""

from __future__ import annotations

import copy
import datetime as dt
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
from mcrl.runtime.ee_axis_c1_dull_source import (
    C1_DULL_POLICY,
    C1DullSourceContractError,
    capture_c1_dull_rollout_sample,
)
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM, EE_AXIS_STATE_SCHEMA


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _environment(*, keyed: bool = True):
    field = KeyedFadingField.from_components("w51", 1, 4) if keyed else None
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=4)),
        ),
        fading_field=field,
    )
    rng = np.random.default_rng(2026083151)
    observation = environment.reset(START, rng)
    return environment, observation, rng


def _reference(observation) -> np.ndarray:
    actions = np.full(observation.num_users, NO_OP_ACTION, dtype=np.int64)
    for uid, mask in enumerate(observation.masks):
        valid = np.flatnonzero(mask)
        if valid.size:
            actions[uid] = int(valid[0])
    return actions


@requires_archive
def test_capture_binds_current_state_main_reference_and_dull_frontier_without_mutation():
    environment, observation, rng = _environment()
    before_rng = copy.deepcopy(rng.bit_generator.state)
    before_step = environment.driver.step_index
    sample = capture_c1_dull_rollout_sample(
        environment,
        observation=observation,
        reference_actions=_reference(observation),
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        source_seed=17,
        rng=rng,
    )
    sample.verify()
    assert sample.record.policy_name == C1_DULL_POLICY
    assert sample.record.state_schema == EE_AXIS_STATE_SCHEMA
    assert sample.state_observation.state_matrix.shape[1] == EE_AXIS_STATE_DIM
    assert sample.record.frontier_score == pytest.approx(
        sum(sample.record.user_frontier_scores)
    )
    assert environment.driver.step_index == before_step
    assert rng.bit_generator.state == before_rng


@requires_archive
def test_capture_is_deterministic_and_rejects_plain_or_stale_environment():
    first_env, first_obs, first_rng = _environment()
    second_env, second_obs, second_rng = _environment()
    first = capture_c1_dull_rollout_sample(
        first_env,
        observation=first_obs,
        reference_actions=_reference(first_obs),
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        source_seed=17,
        rng=first_rng,
    )
    second = capture_c1_dull_rollout_sample(
        second_env,
        observation=second_obs,
        reference_actions=_reference(second_obs),
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        source_seed=17,
        rng=second_rng,
    )
    assert first.record.anchor_sha256 == second.record.anchor_sha256
    assert first.record.source_record_sha256 == second.record.source_record_sha256

    plain, plain_observation, plain_rng = _environment(keyed=False)
    with pytest.raises(C1DullSourceContractError, match="keyed fading"):
        capture_c1_dull_rollout_sample(
            plain,
            observation=plain_observation,
            reference_actions=_reference(plain_observation),
            source_manifest_sha256="b" * 64,
            checkpoint_sha256="c" * 64,
            source_seed=17,
            rng=plain_rng,
        )

    first_env.step(_reference(first_obs), first_rng)
    with pytest.raises(C1DullSourceContractError, match="current predecision anchor"):
        capture_c1_dull_rollout_sample(
            first_env,
            observation=first_obs,
            reference_actions=_reference(first_obs),
            source_manifest_sha256="b" * 64,
            checkpoint_sha256="c" * 64,
            source_seed=17,
            rng=first_rng,
        )
