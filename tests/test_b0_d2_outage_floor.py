"""B0 D-2 — an outage must not dominate service on either bounded head.

**The defect.**  ``runtime/outage_gate.py``'s own docstring (:10-27) states it:
during an outage ``r2 = 0`` and ``r3 = 0``.  Every *served* step scores
``r2 <= 0`` (0, −φ1, or −φ2; ``env/action_contract.py:414-418``) and
``r3 = −U_{b_u} <= −1`` — a served user counts itself in its own beam's load
(``env/service.py:164-182``).  So on ``r3`` an outage strictly dominates every
served step, and on ``r2`` it ties the best one.  These steps are **not**
no-ops: a user that chose a valid action and was then denied service by
per-link power infeasibility or contention enters replay carrying that free
ride (``modqn.py`` train loop — the no-op branch ``continue``s, this one does
not).

**The fix, stated so the magnitude is auditable.**  The module's docstring
describes a deferred discounted re-entry penalty and a threshold marked
"**S, PROPOSED** — Not yet frozen" (:39-46).  Nothing in the repository
declares a penalty magnitude, so none is invented.  The minimal change that
removes the inversion and no more is the one the brief names as defensible:
score an unserved user on each bounded head at **the worst value that head can
take for a served user**, so that service is never worse than outage.

  - ``r2`` floor = ``−PHI2`` = **−1.0** — the worst served ``r2``, an
    inter-satellite handover (``action_contract.py:411``).
  - ``r3`` floor = ``−num_users`` = **−100.0** at the standard 100-user
    configuration — the worst served ``r3``, total collapse onto one beam.
    ``num_users`` is a declared configuration value, not an invented
    magnitude; it is a *loose* bound and a tighter one would require W-13 to
    freeze a value, which it has not.

``r1`` is untouched: it is already ``≈0`` for an unserved user and it is not a
bounded head.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NUM_ACTIONS, PHI1, PHI2
from mcrl.env.step_types import ActionMask, RewardComponents, StepResult
from mcrl.runtime.outage_gate import (
    OUTAGE_R2_FLOOR,
    apply_outage_floor,
    outage_r3_floor,
)
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv

NUM_USERS = 100

SERVED_USER = 0
UNSERVED_USER = 1


def _trainer() -> MODQNTrainer:
    env = ScriptedEnv(
        np.ones((2, 2, NUM_ACTIONS), dtype=bool), num_beams=NUM_ACTIONS
    )
    return MODQNTrainer(env, TrainerConfig(batch_size=4, episodes=1))


def _worst_served_step_result() -> StepResult:
    """One served user at the worst served value, one unserved user.

    The served user takes ``r2 = −φ2`` (an inter-satellite handover) and
    ``r3 = −U`` with the whole population on its beam — the floor of both
    bounded heads.  The unserved user carries the environment's raw
    ``r2 = 0``, ``r3 = 0``: the free ride D-2 is about.
    """
    mask = ActionMask(mask=np.ones(NUM_ACTIONS, dtype=bool))
    return StepResult(
        time_s=1.0,
        step_index=0,
        done=False,
        user_states=[],
        action_masks=[mask, mask],
        rewards=[
            RewardComponents(
                r1_system_ee_contribution=1.0,
                r1_throughput=1.0,
                r2_handover=-PHI2,
                r3_load_balance=-float(NUM_USERS),
            ),
            RewardComponents(
                r1_system_ee_contribution=0.0,
                r1_throughput=0.0,
                r2_handover=0.0,
                r3_load_balance=0.0,
            ),
        ],
        served=(True, False),
    )


# -- the inversion itself -------------------------------------------------


def test_an_outage_is_not_better_than_the_worst_served_step_on_either_head():
    """**This is D-2.**  Fails on the unfixed trainer: 0.0 > −1.0 and 0.0 > −100."""
    trainer = _trainer()
    result = _worst_served_step_result()

    served = trainer.reward_vector_from_step_result(
        result, SERVED_USER, num_users=NUM_USERS
    )
    unserved = trainer.reward_vector_from_step_result(
        result, UNSERVED_USER, num_users=NUM_USERS
    )

    assert unserved[1] <= served[1], (
        f"outage r2={unserved[1]} beats the worst served r2={served[1]}"
    )
    assert unserved[2] <= served[2], (
        f"outage r3={unserved[2]} beats the worst served r3={served[2]}"
    )


def test_the_fixture_is_the_worst_case_and_therefore_has_teeth():
    """If the served user were not at the floor the assertion would be weak."""
    result = _worst_served_step_result()
    served = result.rewards[SERVED_USER]
    assert served.r2_handover == -PHI2 < -PHI1 < 0.0
    assert served.r3_load_balance == -float(NUM_USERS)
    unserved = result.rewards[UNSERVED_USER]
    # The environment really does hand out the free ride; the trainer floors it.
    assert unserved.r2_handover == 0.0
    assert unserved.r3_load_balance == 0.0


def test_service_is_never_worse_than_outage_across_the_whole_served_range():
    """Not just at the floor: every legal served value must survive."""
    trainer = _trainer()
    result = _worst_served_step_result()
    unserved = trainer.reward_vector_from_step_result(
        result, UNSERVED_USER, num_users=NUM_USERS
    )
    for r2 in (0.0, -PHI1, -PHI2):
        assert unserved[1] <= r2
    for load in range(1, NUM_USERS + 1):
        assert unserved[2] <= -float(load)


# -- the magnitudes, asserted so a silent change cannot happen -------------


def test_the_declared_floor_values():
    assert OUTAGE_R2_FLOOR == -PHI2 == -1.0
    assert outage_r3_floor(NUM_USERS) == -100.0
    assert outage_r3_floor(7) == -7.0


def test_the_floor_leaves_r1_alone():
    floored = apply_outage_floor(np.array([0.25, 0.0, 0.0]), num_users=NUM_USERS)
    assert floored[0] == pytest.approx(0.25)
    assert floored[1] == pytest.approx(-1.0)
    assert floored[2] == pytest.approx(-100.0)


def test_a_served_user_is_returned_byte_for_byte_unchanged():
    """The floor applies to outages only — the served objective is untouched."""
    trainer = _trainer()
    result = _worst_served_step_result()
    served = trainer.reward_vector_from_step_result(
        result, SERVED_USER, num_users=NUM_USERS
    )
    raw = result.rewards[SERVED_USER]
    assert served[0] == raw.r1_system_ee_contribution
    assert served[1] == raw.r2_handover
    assert served[2] == raw.r3_load_balance


def test_a_step_result_without_served_information_is_left_alone():
    """Back-compat: fixtures that do not carry ``served`` are not guessed at."""
    trainer = _trainer()
    result = _worst_served_step_result()
    result.served = None
    unfloored = trainer.reward_vector_from_step_result(
        result, UNSERVED_USER, num_users=NUM_USERS
    )
    assert unfloored[1] == 0.0
    assert unfloored[2] == 0.0
