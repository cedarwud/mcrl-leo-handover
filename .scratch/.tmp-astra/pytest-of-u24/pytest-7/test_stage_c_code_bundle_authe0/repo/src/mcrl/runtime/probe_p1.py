"""Probe P1 — visibility and D2 event rate under a fixed policy (W-11).

SDD §4: P1 reports the per-step visible-satellite distribution, the handover
event rate, and the elevation / angular-rate distributions, and it is what
closes Q-A and Q-B.

**It enforces §7.1 rather than describing it.**  ``run_probe_p1`` demands a
frozen :class:`PreregRecord` and re-verifies its digest, and it pushes the
policy through ``assert_data_blind``.  A probe that could be run before the
freeze would make "the threshold was chosen in advance" an honour system,
and §7.1 exists precisely because that is not good enough:

    在觀察 P1 之後才選門檻即為洩漏,除非該映射事先凍結。

What it measures, per user rather than at the service-area centre, because
the four-slot window is per user (``b_u(c,t)``):

* how many satellites are D2-eligible;
* how often a user has **no** valid action — the §4A.5a(4) outage input,
  which is the number that decides whether plain dropping is admissible or
  the semi-MDP transition becomes mandatory;
* the handover event rate, split by ``φ1``/``φ2``/re-entry, classified from
  realised associations and never from indices;
* elevation and its rate of change.

⚠ **The mask carries three terms and link feasibility is not one of them —
and that is now correct rather than incomplete.**  This paragraph used to
say the feasibility term was missing and the starvation rate was therefore
a lower bound.  Ruling C-11 moved feasibility out of the mask entirely: the
decision-time mask ``m`` decides what a user may *choose*, and whether the
chosen link can actually be served is a separate, execution-time test whose
failure is an **outage**, not an invalid action.

So the two populations are genuinely different and P1 reports both:
``starvation_rate`` is "no valid action existed" and belongs to the mask,
while the outage rate belongs to ``ServiceResolution.outage_infeasible``
and is what the §4A.5a(4) gate consumes.  Folding one into the other would
put an executed action back into the decision mask, which is precisely the
three-gate form C-11 withdrew.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..env.action_contract import HandoverClass, HandoverLedger, NO_OP_ACTION
from ..env.candidates import StepCandidates
from ..env.reference_policy import ReferencePolicyRunner
from ..errors import MCRLContractError
from .prereg import PreregRecord, assert_data_blind


@dataclass
class P1Accumulator:
    """Running tallies for one probe run."""

    decision_steps: int = 0
    starved_steps: int = 0
    eligible_counts: list[int] = field(default_factory=list)
    valid_action_counts: list[int] = field(default_factory=list)
    elevation_deg: list[float] = field(default_factory=list)
    handover_events: dict[str, int] = field(
        default_factory=lambda: {
            HandoverClass.NONE.value: 0,
            HandoverClass.INTRA_SATELLITE.value: 0,
            HandoverClass.INTER_SATELLITE.value: 0,
        }
    )
    reentry_events: int = 0
    unserved_steps: int = 0

    def observe(
        self,
        candidates: StepCandidates,
        actions: np.ndarray,
        classes: list[HandoverClass],
        previously_unserved: np.ndarray,
    ) -> None:
        num_users = len(candidates.slot_tables)
        self.decision_steps += num_users
        self.starved_steps += int(candidates.starved_users.sum())
        self.valid_action_counts.extend(candidates.num_valid.tolist())
        self.eligible_counts.extend(
            candidates.d2.eligible_counts.astype(int).tolist()
        )
        finite = candidates.elevation_deg[np.isfinite(candidates.elevation_deg)]
        self.elevation_deg.extend(finite.tolist())

        for uid, handover in enumerate(classes):
            self.handover_events[handover.value] += 1
            if int(actions[uid]) == NO_OP_ACTION:
                self.unserved_steps += 1
            elif (
                handover is HandoverClass.INTER_SATELLITE
                and previously_unserved[uid]
            ):
                self.reentry_events += 1

    def summarise(self) -> dict[str, object]:
        eligible = np.array(self.eligible_counts, dtype=np.float64)
        valid = np.array(self.valid_action_counts, dtype=np.float64)
        elevation = np.array(self.elevation_deg, dtype=np.float64)
        steps = max(self.decision_steps, 1)
        handovers = (
            self.handover_events[HandoverClass.INTRA_SATELLITE.value]
            + self.handover_events[HandoverClass.INTER_SATELLITE.value]
        )
        return {
            "decision_steps": self.decision_steps,
            "d2_eligible_per_user": _quantiles(eligible),
            "valid_actions_per_user": _quantiles(valid),
            "elevation_deg": _quantiles(elevation),
            "starvation_rate": self.starved_steps / steps,
            "unserved_rate": self.unserved_steps / steps,
            "handover_rate": handovers / steps,
            "phi1_rate": self.handover_events[
                HandoverClass.INTRA_SATELLITE.value
            ]
            / steps,
            "phi2_rate": self.handover_events[
                HandoverClass.INTER_SATELLITE.value
            ]
            / steps,
            "reentry_rate": self.reentry_events / steps,
            "handover_events": dict(self.handover_events),
            "mask_scope": (
                "three decision-time terms (slot occupied, cell exists, cell "
                "visible); link feasibility is an execution-time outage under "
                "ruling C-11, not a mask term, and is reported separately"
            ),
        }


def _quantiles(values: np.ndarray) -> dict[str, float]:
    if values.size == 0:
        return {"count": 0.0}
    return {
        "count": float(values.size),
        "min": float(values.min()),
        "p05": float(np.percentile(values, 5)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "max": float(values.max()),
    }


def run_probe_p1(
    *,
    prereg: PreregRecord,
    policy: ReferencePolicyRunner,
    steps: iter,
    rng: np.random.Generator,
) -> dict[str, object]:
    """Drive a fixed policy over pre-built candidate tables and tally P1.

    ``steps`` yields one :class:`StepCandidates` per time step.  The probe
    does not build them itself: constructing the geometry is the
    environment's job, and keeping it outside means the probe cannot
    accidentally reach for something the environment would not have given a
    trained policy either.
    """
    prereg.verify()
    assert_data_blind(policy=policy.declaration)
    if not prereg.sections.get("probe_grid", {}).get("P1"):
        raise MCRLContractError(
            "the frozen PREREG has no P1 entry in its probe grid; §7.1 "
            "requires the complete grid to be frozen before the first probe"
        )

    accumulator = P1Accumulator()
    ledgers: list[HandoverLedger] | None = None
    policy.reset()

    for candidates in steps:
        num_users = len(candidates.slot_tables)
        if ledgers is None:
            ledgers = [HandoverLedger() for _ in range(num_users)]
        elif len(ledgers) != num_users:
            raise MCRLContractError("the population changed mid-probe")

        previously_unserved = np.array(
            [ledger.incumbent_norad is None for ledger in ledgers], dtype=bool
        )
        actions = policy.act(candidates, rng)
        classes = [
            ledgers[uid].observe(
                candidates.slot_tables[uid].association(actions[uid])
            )
            for uid in range(num_users)
        ]
        accumulator.observe(candidates, actions, classes, previously_unserved)

    if accumulator.decision_steps == 0:
        raise MCRLContractError("the probe consumed no steps")

    return {
        "probe": "P1",
        "prereg_digest": prereg.digest,
        "policy": policy.declaration.as_dict(),
    } | accumulator.summarise()
