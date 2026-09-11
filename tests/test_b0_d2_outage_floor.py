"""B0 D-2 — an outage must not score better than service on either bounded head.

**The inversion.**  ``runtime/outage_gate.py``'s own docstring states it: an
unserved user scores ``r2 = 0`` and ``r3 = 0``, while every *served* step
scores ``r2 ∈ {0, −φ1, −φ2}`` and ``r3 = −U_{b_u} <= −1`` (a served user
counts itself in its own beam's load).  A user that chose a valid action and
was then denied service by per-link power infeasibility enters replay with
that free ride.

**The floor (controller ruling 2026-09-11, replacing the first −num_users
bound).**  An unserved user scores:

  - ``r2 = −PHI2 = −1.0`` — the worst ``r2`` a served user can receive;
  - ``r3 = the worst r3 any SERVED user receives IN THE SAME STEP``, which is
    ``−max_b U_b(t)`` over the beams lit that step.

``eligible_load_by_beam`` counts served users only (post-feasibility), so
every beam with ``U_b > 0`` carries at least one served user scoring
``−U_b``: the per-step served minimum and ``−max_b U_b`` are the same number,
and the real-environment test below checks exactly that.  No magnitude is
invented and the floor cannot exceed the load actually present.

A step in which NOBODY is served has no served value to floor at; per the
ruling ("say so and stop rather than approximating") that raises.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NUM_ACTIONS, PHI1, PHI2
from mcrl.env.step_types import ActionMask, RewardComponents, StepResult
from mcrl.errors import MCRLContractError
from mcrl.runtime.outage_gate import (
    OUTAGE_R2_FLOOR,
    apply_outage_floor,
    per_step_outage_floor,
)
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv


def _trainer() -> MODQNTrainer:
    env = ScriptedEnv(
        np.ones((2, 2, NUM_ACTIONS), dtype=bool), num_beams=NUM_ACTIONS
    )
    return MODQNTrainer(env, TrainerConfig(batch_size=4, episodes=1))


def _served(r2: float, r3: float) -> RewardComponents:
    return RewardComponents(
        r1_system_ee_contribution=1.0, r1_throughput=1.0,
        r2_handover=r2, r3_load_balance=r3,
    )


UNSERVED_RAW = RewardComponents(
    r1_system_ee_contribution=0.0, r1_throughput=0.0,
    r2_handover=0.0, r3_load_balance=0.0,
)


def _step(rewards, served) -> StepResult:
    mask = ActionMask(mask=np.ones(NUM_ACTIONS, dtype=bool))
    return StepResult(
        time_s=1.0, step_index=0, done=False, user_states=[],
        action_masks=[mask] * len(rewards), rewards=list(rewards),
        served=tuple(served),
    )


def _mixed_step() -> StepResult:
    """Users 0-2 served on beams of load 3, 7, 1 (the worst is −7, a φ2
    handover); users 3 and 4 unserved with the environment's raw free ride."""
    return _step(
        [_served(0.0, -3.0), _served(-PHI2, -7.0), _served(-PHI1, -1.0),
         UNSERVED_RAW, UNSERVED_RAW],
        [True, True, True, False, False],
    )


# -- the inversion is gone --------------------------------------------------


def test_an_outage_never_scores_better_than_any_served_user_in_its_step():
    """**This is D-2.**  Fails on the unfixed trainer (0 > −1 and 0 > −7)."""
    trainer = _trainer()
    result = _mixed_step()
    vectors = [trainer.reward_vector_from_step_result(result, u) for u in range(5)]
    served = [vectors[u] for u in (0, 1, 2)]
    for u in (3, 4):
        for s in served:
            assert vectors[u][1] <= s[1], (vectors[u], s)
            assert vectors[u][2] <= s[2], (vectors[u], s)


def test_the_r3_floor_equals_the_per_step_served_minimum():
    trainer = _trainer()
    result = _mixed_step()
    unserved = trainer.reward_vector_from_step_result(result, 3)
    assert unserved[2] == min(-3.0, -7.0, -1.0) == -7.0
    assert unserved[1] == -PHI2 == OUTAGE_R2_FLOOR == -1.0


def test_the_floor_moves_with_the_step_not_with_the_population():
    """A lightly loaded step floors lightly: the old −num_users bound is gone."""
    trainer = _trainer()
    light = _step([_served(0.0, -1.0), _served(0.0, -2.0), UNSERVED_RAW],
                  [True, True, False])
    assert trainer.reward_vector_from_step_result(light, 2)[2] == -2.0


def test_served_users_are_returned_unchanged_and_r1_is_never_touched():
    trainer = _trainer()
    result = _mixed_step()
    for u in (0, 1, 2):
        raw = result.rewards[u]
        v = trainer.reward_vector_from_step_result(result, u)
        assert (v[0], v[1], v[2]) == (
            raw.r1_system_ee_contribution, raw.r2_handover, raw.r3_load_balance
        )
    assert trainer.reward_vector_from_step_result(result, 3)[0] == 0.0


def test_a_step_with_nobody_served_has_no_floor_and_raises():
    """The ruling: no served value exists, so do not approximate one."""
    trainer = _trainer()
    dark = _step([UNSERVED_RAW, UNSERVED_RAW], [False, False])
    with pytest.raises(MCRLContractError):
        trainer.reward_vector_from_step_result(dark, 0)


def test_a_step_result_without_served_information_is_left_alone():
    """Pre-D-2 fixtures carry no ``served``; nothing is guessed from rewards."""
    trainer = _trainer()
    result = _mixed_step()
    result.served = None
    v = trainer.reward_vector_from_step_result(result, 3)
    assert (v[1], v[2]) == (0.0, 0.0)


def test_the_helpers_directly():
    result = _mixed_step()
    assert per_step_outage_floor(result.rewards, result.served) == (-1.0, -7.0)
    floored = apply_outage_floor(np.array([0.25, 0.0, 0.0]), r3_floor=-7.0)
    assert list(floored) == [0.25, -1.0, -7.0]


# -- on the real environment: the floor IS −max_b U_b -------------------------


def test_on_real_physics_the_floor_is_minus_the_most_loaded_lit_beam():
    """Random masked actions on the real environment until outages occur.

    For every step, the trainer's r3 floor must equal ``−max_b U_b`` read
    from the physics' own ``eligible_load_by_beam``, and every unserved user
    must score at or below every served user on both bounded heads.
    """
    from mcrl.runtime.training_pipeline import make_training_environment

    env = make_training_environment(users=100)
    trainer = MODQNTrainer(env, TrainerConfig(learning_rate=0.001, episodes=1),
                           train_seed=42, env_seed=1337, mobility_seed=7)
    states, masks, _ = env.reset(trainer._env_rng, trainer._mobility_rng)
    enc = trainer._encode_states(states)
    outage_steps = 0
    for _t in range(env.config.steps_per_episode):
        actions = trainer.select_actions(enc, masks, 1.0)
        result = env.step(actions, trainer._env_rng)
        resolution = env.last_outcome.resolution
        assert result.served == tuple(bool(x) for x in resolution.served)
        vectors = np.array([
            trainer.reward_vector_from_step_result(result, u)
            for u in range(env.config.num_users)
        ])
        served = np.asarray(result.served)
        if (~served).any():
            outage_steps += 1
            max_load = max(resolution.eligible_load_by_beam.values())
            assert np.all(vectors[~served, 2] == -float(max_load))
            assert vectors[~served, 2].max() <= vectors[served, 2].min()
            assert vectors[~served, 1].max() <= vectors[served, 1].min()
        states, masks = result.user_states, result.action_masks
        enc = trainer._encode_states(states)
    assert outage_steps > 0, "no outage occurred; the check had nothing to test"


def test_the_episode_log_counts_exactly_the_floored_user_steps():
    """``EpisodeLog.outage_user_steps`` = unserved user-steps actually seen."""
    from mcrl.runtime.training_pipeline import make_training_environment

    env = make_training_environment(users=100)
    trainer = MODQNTrainer(
        env,
        TrainerConfig(learning_rate=0.001, episodes=1, batch_size=100_000,
                      replay_capacity=100_000),
        train_seed=42, env_seed=1337, mobility_seed=7,
    )
    seen: list[int] = []
    real_step = env.step

    def recording_step(actions, rng):
        result = real_step(actions, rng)
        seen.append(sum(1 for flag in result.served if not flag))
        return result

    env.step = recording_step
    (log,) = trainer.train()
    assert log.outage_user_steps == sum(seen)
    assert log.outage_user_steps > 0  # epsilon = 1: outages do occur
