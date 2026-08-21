"""W-03 / G-9 — SDD §4A.7 T4 and T10, the TD target's two rules.

T4  an action valid in ``s_t`` but invalid in ``s_{t+1}`` must not enter the
    target's max.
T10 the last step of an episode bootstraps nothing: ``y = r``.

Both are properties of ``MODQNTrainer.update()``, so they are checked
against the real update by pinning the target network to a known table and
recomputing the expected MSE by hand.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch
import torch.nn as nn

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv

NUM_USERS = 2
BATCH = 4
DISCOUNT = 0.9

HIGH_Q = 1_000.0
LOW_Q = 1.0


class _FixedQ(nn.Module):
    """Target-network stand-in returning one fixed row per sample."""

    def __init__(self, row: np.ndarray) -> None:
        super().__init__()
        self.register_buffer("row", torch.tensor(row, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.row.unsqueeze(0).expand(x.shape[0], -1).clone()


def _trainer() -> MODQNTrainer:
    script = np.ones((2, NUM_USERS, NUM_ACTIONS), dtype=bool)
    env = ScriptedEnv(script, num_beams=NUM_ACTIONS)
    config = TrainerConfig(
        batch_size=BATCH, episodes=1, discount_factor=DISCOUNT
    )
    return MODQNTrainer(env, config)


def _fill(trainer, *, next_mask: np.ndarray, done: bool, reward: float, action: int):
    mask = np.ones(NUM_ACTIONS, dtype=bool)
    for _ in range(BATCH):
        trainer.replay.push(
            np.zeros(trainer.state_dim, dtype=np.float32),
            action,
            np.full(3, reward, dtype=np.float32),
            np.zeros(trainer.state_dim, dtype=np.float32),
            mask.copy(),
            next_mask.copy(),
            done,
        )


def _q_current(trainer, objective: int, action: int) -> float:
    states = torch.zeros(BATCH, trainer.state_dim)
    with torch.no_grad():
        return float(trainer.q_nets[objective](states)[0, action])


def _pin_targets(trainer, row: np.ndarray) -> None:
    for objective in range(3):
        trainer.target_nets[objective] = _FixedQ(row)


def test_T4_an_action_invalid_at_t_plus_one_is_excluded_from_the_max():
    """The high-Q action is valid now and invalid next; it must not be used."""
    trainer = _trainer()
    row = np.full(NUM_ACTIONS, LOW_Q, dtype=np.float32)
    row[5] = HIGH_Q
    _pin_targets(trainer, row)

    next_mask = np.ones(NUM_ACTIONS, dtype=bool)
    next_mask[5] = False  # valid at t, invalid at t+1
    reward, action = 2.0, 3
    _fill(trainer, next_mask=next_mask, done=False, reward=reward, action=action)

    q_current = _q_current(trainer, 0, action)
    losses = trainer.update()

    masked_target = reward + DISCOUNT * LOW_Q
    unmasked_target = reward + DISCOUNT * HIGH_Q
    assert losses[0] == pytest.approx((q_current - masked_target) ** 2, rel=1e-4)
    assert losses[0] != pytest.approx((q_current - unmasked_target) ** 2, rel=1e-2)


def test_T4_the_masked_max_is_taken_over_the_valid_actions_that_remain():
    trainer = _trainer()
    row = np.arange(NUM_ACTIONS, dtype=np.float32)
    _pin_targets(trainer, row)

    next_mask = np.zeros(NUM_ACTIONS, dtype=bool)
    next_mask[[2, 9]] = True  # best remaining value is row[9] = 9.0
    reward, action = -1.0, 0
    _fill(trainer, next_mask=next_mask, done=False, reward=reward, action=action)

    q_current = _q_current(trainer, 0, action)
    losses = trainer.update()

    expected = reward + DISCOUNT * 9.0
    assert losses[0] == pytest.approx((q_current - expected) ** 2, rel=1e-4)


def test_T10_a_terminal_transition_does_not_bootstrap():
    """SDD §4A.5 r6 fix: without the done term, 1 transition in 10 leaks."""
    trainer = _trainer()
    _pin_targets(trainer, np.full(NUM_ACTIONS, HIGH_Q, dtype=np.float32))

    reward, action = 5.0, 1
    _fill(
        trainer,
        next_mask=np.ones(NUM_ACTIONS, dtype=bool),
        done=True,
        reward=reward,
        action=action,
    )

    q_current = _q_current(trainer, 0, action)
    losses = trainer.update()

    assert losses[0] == pytest.approx((q_current - reward) ** 2, rel=1e-4)


def test_non_terminal_transition_does_bootstrap():
    """The mirror of T10: the done term must not suppress a live bootstrap."""
    trainer = _trainer()
    _pin_targets(trainer, np.full(NUM_ACTIONS, LOW_Q, dtype=np.float32))

    reward, action = 5.0, 1
    _fill(
        trainer,
        next_mask=np.ones(NUM_ACTIONS, dtype=bool),
        done=False,
        reward=reward,
        action=action,
    )

    q_current = _q_current(trainer, 0, action)
    losses = trainer.update()

    expected = reward + DISCOUNT * LOW_Q
    assert losses[0] == pytest.approx((q_current - expected) ** 2, rel=1e-4)


def test_each_objective_maxes_over_its_own_target_network():
    """SDD B1: vanilla MODQN eq. (16), not a shared scalarised argmax."""
    trainer = _trainer()
    for objective in range(3):
        row = np.full(NUM_ACTIONS, float(objective + 1), dtype=np.float32)
        trainer.target_nets[objective] = _FixedQ(row)

    reward, action = 0.0, 4
    _fill(
        trainer,
        next_mask=np.ones(NUM_ACTIONS, dtype=bool),
        done=False,
        reward=reward,
        action=action,
    )

    q_current = [_q_current(trainer, objective, action) for objective in range(3)]
    losses = trainer.update()

    for objective in range(3):
        expected = reward + DISCOUNT * float(objective + 1)
        assert losses[objective] == pytest.approx(
            (q_current[objective] - expected) ** 2, rel=1e-4
        )
