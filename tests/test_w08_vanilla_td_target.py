"""W-08 / B1 — the TD target is MODQN eq. (16) vanilla, and there is one of it.

B1: "TD target 改回 MODQN 式 (16) vanilla,**每目標各自在自己的目標網路取 max**".
§8 forbids "Double-DQN + 三目標共用純量化動作", because with it the control
arm is no longer the published MODQN.

The behavioural checks (masked max, done term, per-objective target network)
live with T4/T10 in ``test_w03_td_target_masking.py``.  What W-08 adds is the
structural half: exactly one TD-target implementation exists, and it is not
Double-DQN.
"""

from __future__ import annotations

import inspect
import re

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


def _trainer():
    env = ScriptedEnv(
        np.ones((2, 2, NUM_ACTIONS), dtype=bool), num_beams=NUM_ACTIONS
    )
    return MODQNTrainer(
        env, TrainerConfig(batch_size=BATCH, episodes=1, discount_factor=DISCOUNT)
    )


def _fill(trainer, reward=1.0, action=0):
    mask = np.ones(NUM_ACTIONS, dtype=bool)
    for _ in range(BATCH):
        trainer.replay.push(
            np.zeros(trainer.state_dim, dtype=np.float32),
            action,
            np.full(3, reward, dtype=np.float32),
            np.zeros(trainer.state_dim, dtype=np.float32),
            mask.copy(),
            mask.copy(),
            False,
        )


# -- exactly one TD target ------------------------------------------------


def test_there_is_a_single_update_path():
    """The dormant batch twin is gone; ``update()`` is the only one."""
    assert not hasattr(MODQNTrainer, "_update_from_arrays")
    update_methods = [
        name
        for name in dir(MODQNTrainer)
        if "update" in name and callable(getattr(MODQNTrainer, name, None))
    ]
    assert update_methods == ["update"]


def test_the_bellman_target_appears_exactly_once_in_the_source():
    """Two copies of an equation drift; B1 needs it unambiguous."""
    source = inspect.getsource(MODQNTrainer)
    occurrences = len(re.findall(r"discount_factor \* q_next_max", source))
    assert occurrences == 1, f"found {occurrences} TD-target implementations"


def test_the_only_finiteness_policy_is_the_fail_loud_one():
    """The deleted twin skipped silently, which G-11 forbids.

    The absence of a skip is checked on the parsed tree, not the text — the
    word "continue" appears in the comment explaining why there is none.
    """
    import ast
    import textwrap

    source = inspect.getsource(MODQNTrainer.update)
    assert "assert_finite_loss" in source
    assert "assert_finite_gradients" in source
    assert "assert_finite_parameters" in source
    assert "nan_detected" not in source

    tree = ast.parse(textwrap.dedent(source))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Continue)]
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Break)]


# -- it is vanilla, not Double-DQN ----------------------------------------


def test_the_max_is_taken_on_the_target_network_not_the_online_one():
    """Double-DQN would argmax on the ONLINE net and gather on the target.

    ⚠ **Amended 2026-09-11 by B0 D-1.**  The ``"argmax" not in source``
    assertion is gone: the corrected target *does* argmax, but on the
    **scalarised sum of the three TARGET networks** and gathers on the target
    networks too.  The anti-Double-DQN content of this test is that the online
    networks (``self.q_nets``) never appear in the next-state computation, and
    that half is asserted here more directly than before.
    """
    source = inspect.getsource(MODQNTrainer.update)
    assert "self.target_nets[objective](ns)" in source
    # Not Double-DQN: nothing reads an ONLINE net at the NEXT state.
    assert "self.q_nets[obj_idx](ns)" not in source
    assert "self.q_nets[objective](ns)" not in source
    # The online net is read at the CURRENT state only.
    assert "self.q_nets[obj_idx](st)" in source


def test_each_objective_uses_its_own_target_network():
    """Each head's TD target is still its OWN target network's value.

    ⚠ **Amended 2026-09-11 by B0 D-1.**  What changed is the *action* the
    value is read at: one shared ``argmax_a Σ ω_i Q^target_i(s',a)`` instead
    of three per-head maximisers.  What did NOT change is that head ``i``'s
    target value comes from ``target_nets[i]`` and from no other network.
    The original form of this test asserted ``"objective_weights" not in
    source``, i.e. that the scalarising weights never reach the target —
    B1 / SDD §8.  **B0 deliberately reverses that**; see the module docstring
    of ``tests/test_b0_d1_scalarised_bootstrap.py``.
    """
    source = inspect.getsource(MODQNTrainer.update)
    assert "for obj_idx in range(3)" in source
    assert "q_next_by_objective[obj_idx]" in source
    # The weights come from the config — the same field select_actions reads —
    # and never from a literal in the trainer.
    assert "cfg.objective_weights" in source
    assert "(0.5, 0.3, 0.2)" not in source
    assert "_scalarize_q_values" not in source


def test_a_double_dqn_target_would_give_a_different_answer():
    """Show the two rules are distinguishable, so the check has teeth."""

    class _Fixed(nn.Module):
        def __init__(self, row):
            super().__init__()
            self.register_buffer("row", torch.tensor(row, dtype=torch.float32))

        def forward(self, x):
            return self.row.unsqueeze(0).expand(x.shape[0], -1).clone()

    trainer = _trainer()
    # Target net's best action is 5; the online net would pick 2.
    target_row = np.zeros(NUM_ACTIONS, dtype=np.float32)
    target_row[5] = 10.0
    target_row[2] = 1.0
    online_row = np.zeros(NUM_ACTIONS, dtype=np.float32)
    online_row[2] = 99.0

    for objective in range(3):
        trainer.target_nets[objective] = _Fixed(target_row)

    vanilla_target = float(target_row.max())
    double_dqn_target = float(target_row[int(online_row.argmax())])
    assert vanilla_target != double_dqn_target

    _fill(trainer, reward=0.0, action=1)
    states = torch.zeros(BATCH, trainer.state_dim)
    with torch.no_grad():
        q_current = float(trainer.q_nets[0](states)[0, 1])
    losses = trainer.update()

    assert losses[0] == pytest.approx(
        (q_current - DISCOUNT * vanilla_target) ** 2, rel=1e-4
    )
    assert losses[0] != pytest.approx(
        (q_current - DISCOUNT * double_dqn_target) ** 2, rel=1e-2
    )


def test_the_target_and_the_selector_read_the_same_weights():
    """⚠ **Amended 2026-09-11 by B0 D-1 — this test was inverted.**

    It used to assert ``"objective_weights" not in update``: the scalarising
    weights belong to selection only, because §8 forbids a shared scalarised
    action.  B0 D-1 establishes the opposite requirement — the bootstrap must
    evaluate all three heads under the **deployed** policy, and the deployed
    policy is the scalarised argmax — so the invariant that replaces it is
    that both sites read the *same* config field, so they can never drift.
    """
    selection = inspect.getsource(MODQNTrainer.select_actions)
    assert "objective_weights" in selection
    assert "scalarized_q_values" in selection
    diagnostic_surface = inspect.getsource(MODQNTrainer.scalarized_q_values)
    assert "objective_weights" in diagnostic_surface
    assert "_scalarize_q_values" in diagnostic_surface
    update = inspect.getsource(MODQNTrainer.update)
    assert "cfg.objective_weights" in update


# -- the surviving selection path is single too ---------------------------


def test_action_selection_has_one_path():
    """W-09 removed the two opt-in selectors; nothing dispatches any more."""
    assert not hasattr(MODQNTrainer, "_select_capacity_constrained_actions")
    assert not hasattr(
        MODQNTrainer, "_select_qos_sticky_overflow_reassignment_actions"
    )
    source = inspect.getsource(MODQNTrainer.select_actions)
    assert source.count("return") == 1
