"""The §4A.5a(4) outage gate.

SDD §4A.5a defines what happens when a user has no valid action: execute a
no-op, and drop the transition (PATCH P-03).  Clause (4) then said the
outage rate "must be measured", and that if it is not negligible the drop
"introduces bias" and a semi-MDP transition would be needed.

**Author ruling, 2026-08-22 — this is upgraded from a caveat to a gate.**

The reason is stronger than bias.  During an outage every reward component
reads as neutral::

    r1 ≈ 0   (no throughput, so no energy-efficiency credit)
    r2  = 0   (§4A.4: an unserved step is no association change)
    r3  = 0   (the user is on no beam, so U_{b_u} contributes nothing)

Truncating the future on top of that makes outage **free**: the agent never
sees the cost of going dark.  That is precisely the hole the re-entry ``φ2``
of §4A.4 exists to close — a policy that can go offline to clear its
handover cost.  Dropping the transition re-opens it from the other side.

So when outage is not rare, the semi-MDP form — accumulate reward across
the outage and connect the transition to the step where service resumes —
is **mandatory, not optional**.  Below the threshold, dropping is
admissible because the hole is too small to be worth exploiting.

The threshold itself is **S**-level and must be frozen in the W-13 PREREG
before probe P1 runs (§7.1: thresholds are frozen in advance, or the choice
is made after seeing the data and leaks).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from ..env.action_contract import PHI2
from ..errors import MCRLContractError

# -- B0 D-2: the outage floor ---------------------------------------------
#
# The docstring above states the inversion and this is the minimal change
# that removes it.  An unserved user used to score ``r2 = 0`` and
# ``r3 = 0``, while every SERVED step scores ``r2 <= 0`` and
# ``r3 = -U_{b_u} <= -1`` (a served user counts itself in its own beam's
# load).  So outage strictly dominated service on ``r3`` and tied the best
# served value on ``r2``.  Those steps are not no-ops: a user that chose a
# valid action and was then denied service by per-link power infeasibility
# or by contention enters replay carrying that free ride.
#
# **No penalty magnitude is invented here.**  The deferred discounted
# re-entry penalty this module's docstring describes, and the threshold it
# marks "S, PROPOSED -- Not yet frozen", remain undeclared, and nothing in
# the repository declares one.  What is used instead is a quantity the
# objective already fixes: **the worst value each bounded head can take for
# a SERVED user**.  Scoring an outage there makes service never worse than
# outage -- which is exactly the inversion and no more -- without choosing
# any number the objective does not already contain.
#
# It is a LOOSE bound on r3, deliberately: the tightest honest value would
# need W-13 to freeze one, and it has not.

OUTAGE_R2_FLOOR: float = -PHI2
"""``r2`` for an unserved user: the worst ``r2`` a served user can take.

``HANDOVER_COST`` (``env/action_contract.py:414-418``) ranges over
``{0, PHI1, PHI2}``, so a served ``r2`` lies in ``{0, -PHI1, -PHI2}`` and
``-PHI2 = -1.0`` is its minimum.  Derived from the frozen ``PHI2``, not
chosen.
"""


def outage_r3_floor(num_users: int) -> float:
    """``r3`` for an unserved user: the worst ``r3`` a served user can take.

    ``r3 = -U_{b_u}`` in whole users (B13/PATCH P-13), and the eligible load
    of one beam cannot exceed the population, so a served ``r3`` lies in
    ``[-num_users, -1]`` and ``-num_users`` is its minimum.  ``num_users``
    is a declared configuration value, not an invented magnitude.
    """
    return -float(int(num_users))


def apply_outage_floor(
    reward_vector: np.ndarray | tuple[float, float, float],
    *,
    num_users: int,
) -> np.ndarray:
    """Return the reward vector an **unserved** user scores.

    ``r1`` is passed through: it is already ``~0`` for an unserved user and
    it is not a bounded head, so flooring it would be an objective change
    rather than a defect fix.  ``r2`` and ``r3`` are replaced by the worst
    value each can take for a served user.

    Call this only for users the environment reports as unserved.
    """
    rewards = np.asarray(reward_vector, dtype=np.float64)
    if rewards.shape != (3,):
        raise ValueError(
            "apply_outage_floor requires a shape-(3,) reward vector, "
            f"got {rewards.shape}"
        )
    floored = rewards.copy()
    floored[1] = OUTAGE_R2_FLOOR
    floored[2] = outage_r3_floor(num_users)
    return floored


OUTAGE_RATE_NEGLIGIBLE_DEFAULT: float = 1e-3
"""**S, PROPOSED** — proposed ceiling on the dropped-transition fraction.

At 1e-3 an outage appears in roughly one episode in a hundred (100 users ×
10 steps = 1,000 decision steps per episode), which is too rare for a policy
to find and exploit within 9,000 episodes.  **Not yet frozen** — W-13 must
freeze it, and probe P1 must not be run against an unfrozen threshold.
"""


@dataclass(frozen=True)
class OutageGateVerdict:
    """What the measured outage rate obliges."""

    decision_steps: int
    no_op_dropped: int
    all_invalid_next_dropped: int
    threshold: float

    @property
    def total_dropped(self) -> int:
        return self.no_op_dropped + self.all_invalid_next_dropped

    @property
    def no_op_rate(self) -> float:
        return self.no_op_dropped / self.decision_steps if self.decision_steps else 0.0

    @property
    def dropped_rate(self) -> float:
        return (
            self.total_dropped / self.decision_steps if self.decision_steps else 0.0
        )

    @property
    def semi_mdp_required(self) -> bool:
        return self.dropped_rate > self.threshold

    @property
    def verdict(self) -> str:
        return "semi-mdp-required" if self.semi_mdp_required else "drop-admissible"

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_steps": self.decision_steps,
            "no_op_dropped": self.no_op_dropped,
            "all_invalid_next_dropped": self.all_invalid_next_dropped,
            "total_dropped": self.total_dropped,
            "no_op_rate": self.no_op_rate,
            "dropped_rate": self.dropped_rate,
            "threshold": self.threshold,
            "verdict": self.verdict,
        }


def evaluate_outage_gate(
    diagnostics: Mapping[str, int],
    *,
    threshold: float = OUTAGE_RATE_NEGLIGIBLE_DEFAULT,
) -> OutageGateVerdict:
    """Apply the gate to ``MODQNTrainer.get_masking_diagnostics()`` output."""
    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must be in (0,1)")
    required = (
        "decision_steps_seen",
        "no_op_transitions_skipped",
        "all_invalid_next_transitions_skipped",
    )
    missing = [key for key in required if key not in diagnostics]
    if missing:
        raise MCRLContractError(f"masking diagnostics missing {missing}")
    return OutageGateVerdict(
        decision_steps=int(diagnostics["decision_steps_seen"]),
        no_op_dropped=int(diagnostics["no_op_transitions_skipped"]),
        all_invalid_next_dropped=int(
            diagnostics["all_invalid_next_transitions_skipped"]
        ),
        threshold=float(threshold),
    )


def assert_drop_is_admissible(
    diagnostics: Mapping[str, int],
    *,
    threshold: float = OUTAGE_RATE_NEGLIGIBLE_DEFAULT,
) -> OutageGateVerdict:
    """Raise unless plain dropping is still admissible at this outage rate.

    Call this from the probe and from any training run that keeps PATCH
    P-03's plain drop.  Failing here is not a bug in the run — it is the
    gate telling you the semi-MDP transition has become mandatory.
    """
    verdict = evaluate_outage_gate(diagnostics, threshold=threshold)
    if verdict.semi_mdp_required:
        raise MCRLContractError(
            "SDD §4A.5a(4): dropped-transition rate "
            f"{verdict.dropped_rate:.3e} exceeds the frozen ceiling "
            f"{verdict.threshold:.3e}.  Plain dropping makes outage free "
            "(r1~0, r2=0, r3=0, future truncated), which re-opens the hole "
            "re-entry phi2 closes.  The semi-MDP transition — accumulate "
            "reward across the outage to the step service resumes — is now "
            "mandatory."
        )
    return verdict
