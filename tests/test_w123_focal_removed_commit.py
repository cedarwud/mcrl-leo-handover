"""W-123 -- committing focal-removal seam for V0.7 C2 B1 branches."""

from __future__ import annotations

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
from mcrl.runtime.trainer_env import TrainerEnvironment


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
            "test-w123-v07-focal-removal-commit", "a" * 64, users
        ),
    )


def _first_valid_actions(masks: np.ndarray) -> np.ndarray:
    return np.asarray(
        [int(np.flatnonzero(mask)[0]) if np.any(mask) else -1 for mask in masks],
        dtype=np.int64,
    )


@requires_archive
def test_committing_removal_advances_once_and_clears_focal_service() -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090211)
    observation = environment.reset(START, rng)
    actions = _first_valid_actions(observation.masks)
    focal = 3

    outcome = environment.step_without_user(actions, rng, focal_user=focal)

    assert outcome.step_index == 0
    assert environment._step_index == 1
    assert not bool(outcome.resolution.served[focal])
    assert outcome.link_rate_bps[focal] == 0.0
    assert outcome.link_power_w[focal] == 0.0
    assert environment._previous_association[focal] is None
    assert environment._ledgers[focal].previous is not None


@requires_archive
def test_committing_removal_can_be_repeated_as_caller_owned_absorbing_policy() -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090212)
    observation = environment.reset(START, rng)
    focal = 4

    for expected_step in range(3):
        actions = _first_valid_actions(observation.masks)
        outcome = environment.step_without_user(actions, rng, focal_user=focal)
        assert outcome.step_index == expected_step
        assert not bool(outcome.resolution.served[focal])
        assert outcome.link_rate_bps[focal] == 0.0
        observation = outcome.observation

    assert environment._step_index == 3
    assert environment._previous_association[focal] is None


@requires_archive
def test_committing_removal_preserves_public_noop_rejection_and_user_checks() -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090213)
    observation = environment.reset(START, rng)
    actions = _first_valid_actions(observation.masks)
    actions[0] = -1

    with pytest.raises(MCRLContractError, match="no-op with"):
        environment.step_without_user(actions, rng, focal_user=1)

    valid = _first_valid_actions(observation.masks)
    with pytest.raises(MCRLContractError, match="focal_user"):
        environment.step_without_user(valid, rng, focal_user=20)


@requires_archive
def test_trainer_wrapper_records_committing_removal_outcome() -> None:
    environment = _environment()

    class _Sampler:
        @staticmethod
        def draw(_rng: np.random.Generator) -> dt.datetime:
            return START

    wrapped = TrainerEnvironment(environment, _Sampler())  # type: ignore[arg-type]
    env_rng = np.random.default_rng(2026090214)
    mobility_rng = np.random.default_rng(2026090215)
    _states, masks, _observation = wrapped.reset(env_rng, mobility_rng)
    actions = np.asarray(
        [int(np.flatnonzero(mask.mask)[0]) for mask in masks], dtype=np.int64
    )

    result = wrapped.step_without_user(actions, env_rng, focal_user=2)

    assert result.step_index == 0
    assert wrapped.last_outcome.step_index == 0
    assert wrapped.last_outcome.link_rate_bps[2] == 0.0
    assert not bool(wrapped.last_outcome.resolution.served[2])
