"""W-16 / L-1 — no invalid action ever falls back to index 0.

Covers PATCH P-01 and P-02 in ``docs/PATCH-LEDGER.md`` and the first half of
SDD §4A.7 T12 ("``mask_s`` all zero ⇒ no fallback index is executed").
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, is_no_op
from mcrl.env.step_types import ActionMask
from mcrl.errors import MCRLContractError
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv

NUM_BEAMS = 28
NUM_USERS = 4


def _trainer(**overrides) -> MODQNTrainer:
    script = np.ones((1, NUM_USERS, NUM_BEAMS), dtype=bool)
    env = ScriptedEnv(script, num_beams=NUM_BEAMS)
    config = TrainerConfig(batch_size=4, episodes=1, **overrides)
    return MODQNTrainer(env, config)


def _masks(rows: list[list[bool]]) -> list[ActionMask]:
    return [ActionMask(mask=np.array(row, dtype=bool)) for row in rows]


def test_empty_mask_yields_no_op_not_index_zero_greedy():
    trainer = _trainer()
    rows = [[True] * NUM_BEAMS, [False] * NUM_BEAMS]
    masks = _masks(rows)
    encoded = np.zeros((2, trainer.state_dim), dtype=np.float32)

    actions = trainer.select_actions(encoded, masks, eps=0.0)

    assert not is_no_op(actions[0])
    assert is_no_op(actions[1]), "empty mask must give NO_OP_ACTION, not 0"
    assert int(actions[1]) == NO_OP_ACTION


def test_empty_mask_yields_no_op_under_full_exploration():
    """P-9: exploration is masked, so eps=1.0 cannot rescue an empty mask."""
    trainer = _trainer()
    masks = _masks([[False] * NUM_BEAMS])
    encoded = np.zeros((1, trainer.state_dim), dtype=np.float32)

    actions = trainer.select_actions(encoded, masks, eps=1.0)

    assert int(actions[0]) == NO_OP_ACTION


def test_index_zero_is_never_emitted_when_it_is_masked_out():
    """The pre-patch bug: beam 0 invalid, yet action 0 was returned."""
    trainer = _trainer()
    row = [False] * NUM_BEAMS
    row[5] = True
    masks = _masks([row])
    encoded = np.zeros((1, trainer.state_dim), dtype=np.float32)

    for eps in (0.0, 1.0):
        actions = trainer.select_actions(encoded, masks, eps=eps)
        assert int(actions[0]) == 5


def test_selected_action_is_always_valid_or_no_op():
    trainer = _trainer()
    rng = np.random.default_rng(0)
    rows = []
    for _ in range(32):
        row = rng.random(NUM_BEAMS) < 0.2
        rows.append(row.tolist())
    masks = _masks(rows)
    encoded = rng.standard_normal((len(rows), trainer.state_dim)).astype(
        np.float32
    )

    actions = trainer.select_actions(encoded, masks, eps=0.3)

    for uid, action in enumerate(actions.tolist()):
        if is_no_op(action):
            assert not masks[uid].mask.any()
        else:
            assert masks[uid].mask[action]


def test_diagnostics_path_also_returns_no_op(monkeypatch):
    """PATCH P-02: the exporter-side selector had the same index-0 fallback."""
    trainer = _trainer()
    rows = [[False] * NUM_BEAMS, [True] * NUM_BEAMS]
    masks = _masks(rows)
    encoded = np.zeros((2, trainer.state_dim), dtype=np.float32)

    actions, diagnostics = trainer.select_actions_with_diagnostics(
        encoded, masks
    )

    assert int(actions[0]) == NO_OP_ACTION
    assert diagnostics[0] is None
    assert not is_no_op(actions[1])
    assert diagnostics[1] is not None


def test_unreachable_none_from_helper_fails_loud(monkeypatch):
    """A None greedy result on a non-empty mask must raise, not return 0."""
    trainer = _trainer()
    masks = _masks([[True] * NUM_BEAMS])
    encoded = np.zeros((1, trainer.state_dim), dtype=np.float32)
    monkeypatch.setattr(
        trainer, "_select_masked_greedy_action", lambda *_a, **_k: None
    )

    with pytest.raises(MCRLContractError):
        trainer.select_actions(encoded, masks, eps=0.0)


def test_no_op_sentinel_is_not_a_beam_index():
    assert NO_OP_ACTION < 0
