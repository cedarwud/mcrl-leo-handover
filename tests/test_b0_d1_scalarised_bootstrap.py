"""B0 D-1 — every head bootstraps from ONE common policy's action.

**The defect.** ``MODQNTrainer.update`` took ``q_next_all.max(dim=1).values``
inside ``for obj_idx in range(3)``, i.e. head *i*'s **own** maximiser.  Head
*i* then converges toward ``Q*_i`` — the optimum of objective *i* alone — and
``Σ_i ω_i Q*_i`` is **not** the Q-function of ``Σ_i ω_i r_i``: each ``Q*_i`` is
attained by a *different* policy, so the weighted sum is an optimistic bound
no single policy reaches.  The deployed rule is
``argmax_a Σ_i ω_i Q_i(s,a)`` (``MODQNTrainer.select_actions``), so the object
the trainer must fit is the successor-feature ``ψ^π``: all three heads
evaluated under **one** policy.

**The fix.** Take the argmax of the **scalarised** sum of the three target
networks once over the masked next actions, then gather head *i*'s target at
that shared action.

⚠ **This departs from frozen ruling B1 / SDD §8.**  §8's forbidden list names
"Double-DQN 共用純量化動作", and ``tests/test_w08_vanilla_td_target.py``
asserted the per-head max as the contract.  B0 keeps the *vanilla* half
(argmax **and** gather both on the target networks — never the online ones)
and changes only the shared-action half.  See
``.scratch/b0-corrected/B0-CORRECTED-BASELINE-2026-09-11.md``.

Weights are read from ``TrainerConfig.objective_weights``
(``runtime/trainer_spec.py:52``), never hardcoded in the trainer.
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

BATCH = 4
DISCOUNT = 0.9
WEIGHTS = (0.5, 0.3, 0.2)


class _FixedRow(nn.Module):
    """A network that returns one frozen Q row for every state."""

    def __init__(self, row: np.ndarray) -> None:
        super().__init__()
        self.register_buffer("row", torch.tensor(row, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.row.unsqueeze(0).expand(x.shape[0], -1).clone()


def _disagreeing_rows() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Three rows whose individual argmaxes all disagree with the scalarised one.

    head 0 peaks at action 0, head 1 at action 1, head 2 at action 2 — but
    ``0.5·Q0 + 0.3·Q1 + 0.2·Q2`` peaks at action **3**, which no head picks.
    """
    rows = [np.zeros(NUM_ACTIONS, dtype=np.float32) for _ in range(3)]
    rows[0][0] = 10.0
    rows[0][3] = 6.0
    rows[1][1] = 10.0
    rows[1][3] = 9.0
    rows[2][2] = 10.0
    rows[2][3] = 9.0
    return rows[0], rows[1], rows[2]


def _trainer(weights: tuple[float, float, float] = WEIGHTS) -> MODQNTrainer:
    env = ScriptedEnv(
        np.ones((2, 2, NUM_ACTIONS), dtype=bool), num_beams=NUM_ACTIONS
    )
    return MODQNTrainer(
        env,
        TrainerConfig(
            batch_size=BATCH,
            episodes=1,
            discount_factor=DISCOUNT,
            objective_weights=weights,
        ),
    )


def _fill(trainer: MODQNTrainer, next_mask: np.ndarray) -> None:
    mask = np.ones(NUM_ACTIONS, dtype=bool)
    for _ in range(BATCH):
        trainer.replay.push(
            np.zeros(trainer.state_dim, dtype=np.float32),
            0,
            np.zeros(3, dtype=np.float32),  # r = 0, so target is pure bootstrap
            np.zeros(trainer.state_dim, dtype=np.float32),
            mask.copy(),
            next_mask.copy(),
            False,
        )


def test_the_fixture_actually_makes_the_two_rules_disagree():
    """Teeth: without this the test would pass under the defective code."""
    q0, q1, q2 = _disagreeing_rows()
    scalarised = WEIGHTS[0] * q0 + WEIGHTS[1] * q1 + WEIGHTS[2] * q2
    shared = int(np.argmax(scalarised))
    assert shared == 3
    for head, row in enumerate((q0, q1, q2)):
        assert int(np.argmax(row)) != shared, f"head {head} agrees; fixture is blunt"
        assert float(row[shared]) < float(row.max()), (
            f"head {head} is indifferent between the two rules"
        )


def test_every_head_bootstraps_at_the_scalarised_argmax():
    """The TD target for head i is Q^target_i(s', a') with a' SHARED."""
    q0, q1, q2 = _disagreeing_rows()
    rows = (q0, q1, q2)
    scalarised = WEIGHTS[0] * q0 + WEIGHTS[1] * q1 + WEIGHTS[2] * q2
    shared = int(np.argmax(scalarised))

    trainer = _trainer()
    for objective in range(3):
        trainer.target_nets[objective] = _FixedRow(rows[objective])
    _fill(trainer, np.ones(NUM_ACTIONS, dtype=bool))

    states = torch.zeros(BATCH, trainer.state_dim)
    with torch.no_grad():
        q_current = [float(trainer.q_nets[j](states)[0, 0]) for j in range(3)]

    losses = trainer.update()

    for objective in range(3):
        shared_target = DISCOUNT * float(rows[objective][shared])
        own_max_target = DISCOUNT * float(rows[objective].max())
        assert losses[objective] == pytest.approx(
            (q_current[objective] - shared_target) ** 2, rel=1e-4
        ), f"head {objective} did not bootstrap at the scalarised action"
        assert losses[objective] != pytest.approx(
            (q_current[objective] - own_max_target) ** 2, rel=1e-2
        ), f"head {objective} still bootstraps at its own argmax (D-1)"


def test_the_shared_argmax_respects_the_next_action_mask():
    """The scalarised argmax is taken over VALID next actions only."""
    q0, q1, q2 = _disagreeing_rows()
    rows = (q0, q1, q2)
    next_mask = np.ones(NUM_ACTIONS, dtype=bool)
    next_mask[3] = False  # forbid the unmasked scalarised winner
    scalarised = WEIGHTS[0] * q0 + WEIGHTS[1] * q1 + WEIGHTS[2] * q2
    masked_shared = int(np.argmax(np.where(next_mask, scalarised, -np.inf)))
    assert masked_shared == 0  # 0.5*10 = 5.0 is the best remaining

    trainer = _trainer()
    for objective in range(3):
        trainer.target_nets[objective] = _FixedRow(rows[objective])
    _fill(trainer, next_mask)

    states = torch.zeros(BATCH, trainer.state_dim)
    with torch.no_grad():
        q_current = [float(trainer.q_nets[j](states)[0, 0]) for j in range(3)]

    losses = trainer.update()
    for objective in range(3):
        assert losses[objective] == pytest.approx(
            (q_current[objective] - DISCOUNT * float(rows[objective][masked_shared]))
            ** 2,
            rel=1e-4,
        )


def test_the_weights_come_from_the_config_not_a_literal():
    """Changing the deployed weights must move the bootstrap action with them."""
    q0, q1, q2 = _disagreeing_rows()
    rows = (q0, q1, q2)
    # Put all the weight on head 2: the shared action becomes head 2's own
    # argmax (action 2), which the default weights never select.
    weights = (0.0, 0.0, 1.0)
    scalarised = sum(weights[j] * rows[j] for j in range(3))
    shared = int(np.argmax(scalarised))
    assert shared == 2

    trainer = _trainer(weights)
    for objective in range(3):
        trainer.target_nets[objective] = _FixedRow(rows[objective])
    _fill(trainer, np.ones(NUM_ACTIONS, dtype=bool))

    states = torch.zeros(BATCH, trainer.state_dim)
    with torch.no_grad():
        q_current = [float(trainer.q_nets[j](states)[0, 0]) for j in range(3)]

    losses = trainer.update()
    for objective in range(3):
        assert losses[objective] == pytest.approx(
            (q_current[objective] - DISCOUNT * float(rows[objective][shared])) ** 2,
            rel=1e-4,
        )
