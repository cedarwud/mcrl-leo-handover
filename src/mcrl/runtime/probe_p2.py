"""Probe P2 — sensitivity of the results to the dwell length ``N``.

**P2 no longer closes Q-E, and that is deliberate.**  The frozen mapping
needs only the re-key rate, which is scenario characterisation available
before any policy is evaluated, so Q-E closed at ``N = 3`` without a probe.
Running one whose conclusion is already settled would dress a decided
number as an experimental result.

**But Q-E closing elsewhere does not discharge P2's measurements.**  SDD §4
asks P2 for the ``P^N`` swing amplitude and the angle-aware EE dynamic
range per ``N``; both were dropped when P2 was rebased, and the W-24 audit
put them back.  They are the two below.

⚠ **Each ``N`` gets its own streams, spawned from one seed.**  Sweeping the
dwell length while the sampling shares a generator would move the users and
the fading along with ``N``, and the sweep would be measuring "``N`` and a
different sample".  ``ProbeStreams.spawn(seed)`` is re-derived per arm, so
every arm sees the same population and the same fading realisation.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

from ..env.dwell import DWELL_N_CANDIDATES
from ..env.reference_policy import ReferencePolicyRunner
from ..env.step import StepEnvironment
from ..errors import MCRLContractError
from .prereg import PreregRecord
from .probe_harness import ProbeStreams, assert_probe_is_frozen, drive, quantiles


@dataclass
class P2ArmAccumulator:
    """One dwell length's tallies."""

    system_power_w: list[float] = field(default_factory=list)
    link_ee: list[float] = field(default_factory=list)
    rekeys: int = 0
    boundaries: int = 0
    handovers: int = 0
    decision_steps: int = 0

    def observe(self, observation, outcome) -> None:
        from ..env.action_contract import HandoverClass

        users = len(observation.user_states)
        self.decision_steps += users
        self.system_power_w.append(outcome.system_power_w)

        served = outcome.resolution.served
        if np.any(served):
            self.link_ee.extend(outcome.reward_matrix[served, 0].tolist())

        dwell = observation.candidates.dwell
        if dwell.is_boundary:
            self.boundaries += users
            self.rekeys += dwell.rekey_count
        self.handovers += sum(
            1 for handover in outcome.handovers if handover is not HandoverClass.NONE
        )

    def summarise(self) -> dict[str, object]:
        power = np.array(self.system_power_w, dtype=np.float64)
        ee = np.array(self.link_ee, dtype=np.float64)
        return {
            # SDD §4's two required outputs, restored 2026-08-23.
            "system_power_swing_w": (
                float(power.max() - power.min()) if power.size else 0.0
            ),
            "system_power_w": quantiles(power),
            "angle_aware_ee_dynamic_range": (
                float(np.percentile(ee, 95) - np.percentile(ee, 5))
                if ee.size
                else 0.0
            ),
            "link_ee": quantiles(ee),
            # And the quantity the Q-E rule actually used.
            "rekey_rate": (
                self.rekeys / self.boundaries if self.boundaries else 0.0
            ),
            "handover_rate_per_decision": (
                self.handovers / self.decision_steps if self.decision_steps else 0.0
            ),
            "decision_steps": self.decision_steps,
        }


def run_probe_p2(
    *,
    prereg: PreregRecord,
    policy_factory: Callable[[], ReferencePolicyRunner],
    environment_factory: Callable[[int], StepEnvironment],
    epochs: Sequence[dt.datetime],
    seed: int,
    dwell_candidates: Sequence[int] = DWELL_N_CANDIDATES,
) -> dict[str, object]:
    """Sweep ``N`` with every arm on identical streams.

    ``environment_factory(n)`` builds an environment at dwell length ``n``;
    ``policy_factory()`` a fresh runner.  Both are callables rather than
    instances because an arm must not inherit the previous arm's state —
    a policy holding an association from ``N = 2`` would carry it into
    ``N = 3`` and the sweep would measure the carry-over.
    """
    assert_probe_is_frozen(prereg, "P2", policy_factory())
    if not dwell_candidates:
        raise MCRLContractError("P2 needs at least one dwell candidate")

    arms: dict[str, object] = {}
    for n in dwell_candidates:
        accumulator = P2ArmAccumulator()
        # Re-derived, not continued: every arm sees the same users and the
        # same fading, so the only difference between arms is N.
        streams = ProbeStreams.spawn(seed)
        for observation, _actions, outcome in drive(
            environment_factory(int(n)), policy_factory(), epochs, streams
        ):
            accumulator.observe(observation, outcome)
        arms[f"N={int(n)}"] = accumulator.summarise()

    return {
        "probe": "P2",
        "prereg_digest": prereg.digest,
        "policy": policy_factory().declaration.as_dict(),
        "epochs": [epoch.isoformat() for epoch in epochs],
        "seed": seed,
        "closes": [],
        "note": (
            "Q-E closed at N = 3 by the frozen re-key mapping without a "
            "probe; P2 reports sensitivity and the two SDD outputs that the "
            "rebasing had dropped"
        ),
        "arms": arms,
    }
