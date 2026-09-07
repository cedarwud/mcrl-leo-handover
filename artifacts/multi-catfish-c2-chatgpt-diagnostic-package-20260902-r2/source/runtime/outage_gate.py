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

from ..errors import MCRLContractError

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
