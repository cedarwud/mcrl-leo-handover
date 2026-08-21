"""W-16 / L-2 — the training step aborts loudly on non-finite values.

Covers PATCH P-04 in ``docs/PATCH-LEDGER.md``, SDD §3.7 P-3 and §6 G-11.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.errors import NonFiniteTrainingError
from mcrl.runtime.finiteness import (
    all_parameters_finite,
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv

NUM_BEAMS = 8
NUM_USERS = 2
BATCH = 4


def _trainer() -> MODQNTrainer:
    script = np.ones((2, NUM_USERS, NUM_BEAMS), dtype=bool)
    env = ScriptedEnv(script, num_beams=NUM_BEAMS)
    config = TrainerConfig(batch_size=BATCH, episodes=1)
    return MODQNTrainer(env, config)


def _fill_replay(trainer: MODQNTrainer, *, reward: float = 1.0) -> None:
    mask = np.ones(NUM_BEAMS, dtype=bool)
    for _ in range(BATCH):
        trainer.replay.push(
            np.zeros(trainer.state_dim, dtype=np.float32),
            0,
            np.full(3, reward, dtype=np.float32),
            np.zeros(trainer.state_dim, dtype=np.float32),
            mask.copy(),
            mask.copy(),
            False,
        )


def test_finite_batch_updates_normally():
    trainer = _trainer()
    _fill_replay(trainer)
    losses = trainer.update()
    assert all(np.isfinite(value) for value in losses)


def test_nonfinite_reward_raises_instead_of_training_on_nan():
    trainer = _trainer()
    _fill_replay(trainer, reward=float("nan"))
    with pytest.raises(NonFiniteTrainingError, match="nonfinite TD loss"):
        trainer.update()


def test_nonfinite_parameter_raises():
    trainer = _trainer()
    _fill_replay(trainer)
    with torch.no_grad():
        first = next(trainer.q_nets[0].parameters())
        first[0] = float("inf")
    with pytest.raises(NonFiniteTrainingError):
        trainer.update()


def test_update_does_not_silently_skip_an_objective():
    """The dormant twin's ``continue`` is not acceptable behaviour here."""
    trainer = _trainer()
    _fill_replay(trainer, reward=float("inf"))
    with pytest.raises(NonFiniteTrainingError):
        trainer.update()


def test_assert_finite_loss_helper():
    assert_finite_loss(torch.tensor(0.5), objective=0)
    with pytest.raises(NonFiniteTrainingError, match="objective 2"):
        assert_finite_loss(torch.tensor(float("nan")), objective=2)


def test_assert_finite_gradients_helper():
    layer = torch.nn.Linear(2, 2)
    layer(torch.ones(1, 2)).sum().backward()
    assert_finite_gradients(layer.parameters(), objective=1)
    with torch.no_grad():
        next(layer.parameters()).grad[0, 0] = float("nan")
    with pytest.raises(NonFiniteTrainingError, match="nonfinite gradient"):
        assert_finite_gradients(layer.parameters(), objective=1)


def test_assert_finite_parameters_helper():
    layer = torch.nn.Linear(2, 2)
    networks = [layer]
    assert all_parameters_finite(networks)
    assert_finite_parameters(networks)
    with torch.no_grad():
        next(layer.parameters())[0, 0] = float("inf")
    assert not all_parameters_finite(networks)
    with pytest.raises(NonFiniteTrainingError, match="parameter"):
        assert_finite_parameters(networks)
