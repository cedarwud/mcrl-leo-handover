"""W-16 / L-3 — which transitions may enter replay.

Covers PATCH P-03 in ``docs/PATCH-LEDGER.md``, SDD §4A.5a(2)-(4), and the
second half of §4A.7 T12 ("no fallback index is *trained on* either").
"""

from __future__ import annotations

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv

NUM_BEAMS = 8
NUM_USERS = 2


def _run(script: np.ndarray, *, steps: int) -> MODQNTrainer:
    env = ScriptedEnv(script, num_beams=NUM_BEAMS, steps_per_episode=steps)
    config = TrainerConfig(
        batch_size=10_000,  # keep update() from firing; this test is about replay
        episodes=1,
        epsilon_start=0.0,
        epsilon_end=0.0,
        epsilon_decay_episodes=1,
    )
    trainer = MODQNTrainer(env, config)
    trainer.train()
    return trainer


def _all_valid(steps: int) -> np.ndarray:
    return np.ones((steps + 1, NUM_USERS, NUM_BEAMS), dtype=bool)


def test_fully_valid_episode_stores_every_transition():
    steps = 3
    trainer = _run(_all_valid(steps), steps=steps)

    assert len(trainer.replay) == steps * NUM_USERS
    assert trainer.get_masking_diagnostics() == {
        "no_op_transitions_skipped": 0,
        "all_invalid_next_transitions_skipped": 0,
    }


def test_no_op_step_is_not_written_to_replay():
    """§4A.5a(2): the all-invalid decision step contributes no transition."""
    steps = 3
    script = _all_valid(steps)
    script[1, 0, :] = False  # user 0 has no valid action at step 1
    trainer = _run(script, steps=steps)

    diagnostics = trainer.get_masking_diagnostics()
    assert diagnostics["no_op_transitions_skipped"] == 1
    # user 0 loses the step-1 transition; the step-0 transition also goes,
    # because its successor mask is the empty one (see next test).
    assert len(trainer.replay) == steps * NUM_USERS - 2


def test_no_op_action_reaches_the_environment_as_no_op():
    steps = 2
    script = _all_valid(steps)
    script[0, 1, :] = False
    env = ScriptedEnv(script, num_beams=NUM_BEAMS, steps_per_episode=steps)
    config = TrainerConfig(
        batch_size=10_000,
        episodes=1,
        epsilon_start=0.0,
        epsilon_end=0.0,
        epsilon_decay_episodes=1,
    )
    MODQNTrainer(env, config).train()

    assert int(env.observed_actions[0][1]) == NO_OP_ACTION
    assert int(env.observed_actions[0][0]) != NO_OP_ACTION


def test_transition_into_an_all_invalid_successor_is_not_stored():
    """The bootstrap target would be ``r + beta * (-1e9)`` — drop it instead.

    SDD §4A.5a(3) asserts this branch is unreachable once no-op transitions
    are dropped.  Dropping the *outgoing* transition does not by itself make
    the *incoming* one unreachable, so P-03 drops that one too and counts it
    separately.
    """
    steps = 3
    script = _all_valid(steps)
    script[2, 0, :] = False  # successor of user 0's step-1 transition
    trainer = _run(script, steps=steps)

    diagnostics = trainer.get_masking_diagnostics()
    assert diagnostics["all_invalid_next_transitions_skipped"] == 1
    assert diagnostics["no_op_transitions_skipped"] == 1


def test_terminal_step_with_empty_successor_mask_is_still_stored():
    """T10: on ``done`` the target is ``y = r``, so no successor is needed."""
    steps = 2
    script = np.ones((steps, NUM_USERS, NUM_BEAMS), dtype=bool)
    trainer = _run(script, steps=steps)  # script runs out -> empty final mask

    assert trainer.get_masking_diagnostics()[
        "all_invalid_next_transitions_skipped"
    ] == 0
    assert len(trainer.replay) == steps * NUM_USERS
    *_, dones = trainer.replay.sample(steps * NUM_USERS, np.random.default_rng(0))
    assert float(dones.max()) == 1.0


def test_no_stored_transition_carries_the_no_op_sentinel():
    steps = 4
    rng = np.random.default_rng(7)
    script = rng.random((steps + 1, NUM_USERS, NUM_BEAMS)) < 0.5
    trainer = _run(script, steps=steps)

    if len(trainer.replay) == 0:
        return
    _s, actions, _r, _ns, masks, next_masks, dones = trainer.replay.sample(
        len(trainer.replay), np.random.default_rng(0)
    )
    assert (actions >= 0).all()
    for index, action in enumerate(actions.tolist()):
        assert masks[index][action], "stored action must be valid in s_t"
        assert bool(next_masks[index].any()) or bool(dones[index])
