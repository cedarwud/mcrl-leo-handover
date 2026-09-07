"""Probe P7 — does anything actually constrain the action set?

⚠ **This was P5 until 2026-08-23.**  It had displaced SDD §4's own P5 (the
receive-angle disclosure), so it was renumbered and the original restored.
The content is unchanged; only the slot moved.

W-17 measured all three geometric mask terms and the power-feasibility gate
as non-binding — 28/28 actions valid, outage 0/12000 — **at one hand-picked
epoch**.  W-19 then found the power gate does fire once segments are
warm-started.  P7 turns both into numbers over the frozen sampling
distribution instead of one lucky afternoon.

**The three mask terms are reported apart, because an AND cannot be
attributed.**  ``mask = occupied ∧ cell_exists ∧ reachable``, and "28/28
valid" says nothing about which of the three did no work.  One of them —
``cell_exists`` — is structurally true inside the service area because the
lattice carries a guard ring; the other two can bind and do not, here.
Reporting a single attrition number would hide that distinction.

**Both warm-start arms, because they disagree about whether the gate
exists at all** (0.94% vs 0.81% firing, against 0.00% with no warm start).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..env.link_budget import SEGMENT_GAIN_BUDGET_DB
from ..env.reference_policy import ReferencePolicyRunner
from ..env.step import StepEnvironment
from ..errors import MCRLContractError
from .prereg import PreregRecord
from .probe_harness import ProbeStreams, assert_probe_is_frozen, drive, quantiles


@dataclass
class P7Accumulator:
    """Running tallies for one P7 run."""

    decision_steps: int = 0
    valid_actions: list[float] = field(default_factory=list)
    starved: int = 0
    outage: int = 0
    served: int = 0
    # Per-term attrition: how many of the 28 slots each term alone kills.
    killed_by_slot: list[float] = field(default_factory=list)
    killed_by_cell: list[float] = field(default_factory=list)
    killed_by_reachable: list[float] = field(default_factory=list)
    feasible_power_w: list[float] = field(default_factory=list)
    infeasible_power_w: list[float] = field(default_factory=list)

    def observe(self, observation, outcome) -> None:
        candidates = observation.candidates
        users = candidates.slot_occupied.shape[0]
        self.decision_steps += users
        self.valid_actions.extend(candidates.masks.sum(axis=1).tolist())
        self.starved += int(np.count_nonzero(candidates.masks.sum(axis=1) == 0))

        # Each term's own kill count, over the flat 28 slots.  Deliberately
        # NOT mutually exclusive: a slot can fail two terms at once, and
        # forcing a partition would invent a precedence the model has not.
        slots, beams = candidates.slot_occupied.shape[1], candidates.cell_exists.shape[1]
        occupied = np.repeat(candidates.slot_occupied, beams, axis=1)
        exists = np.tile(candidates.cell_exists, (1, slots))
        reachable = candidates.cell_reachable.reshape(users, slots * beams)
        self.killed_by_slot.extend((~occupied).sum(axis=1).tolist())
        self.killed_by_cell.extend((~exists).sum(axis=1).tolist())
        self.killed_by_reachable.extend((~reachable).sum(axis=1).tolist())

        resolution = outcome.resolution
        self.outage += int(np.count_nonzero(resolution.outage_infeasible))
        self.served += resolution.served_count
        self.feasible_power_w.extend(
            outcome.link_power_w[resolution.served].tolist()
        )
        self.infeasible_power_w.extend(
            outcome.link_power_w[resolution.outage_infeasible].tolist()
        )

    def summarise(self, *, p0_w: float, p_max_w: float) -> dict[str, object]:
        if self.decision_steps == 0:
            raise MCRLContractError("P7 consumed no steps")
        feasible = np.array(self.feasible_power_w, dtype=np.float64)
        infeasible = np.array(self.infeasible_power_w, dtype=np.float64)

        def budget_fraction(power: np.ndarray) -> dict[str, float]:
            if power.size == 0:
                return {"count": 0.0}
            return quantiles(10.0 * np.log10(power / p0_w) / SEGMENT_GAIN_BUDGET_DB)

        return {
            "probe": "P7",
            "decision_steps": self.decision_steps,
            "valid_actions_per_user": quantiles(np.array(self.valid_actions)),
            "mask_is_ever_binding": bool(
                float(np.min(self.valid_actions)) < NUM_ACTIONS
            ),
            "starvation_rate": self.starved / self.decision_steps,
            # Per-term, and overlapping on purpose.
            "slots_killed_by_unoccupied_slot": quantiles(
                np.array(self.killed_by_slot)
            ),
            "slots_killed_by_absent_cell": quantiles(np.array(self.killed_by_cell)),
            "slots_killed_by_unreachable_cell": quantiles(
                np.array(self.killed_by_reachable)
            ),
            "term_attrition_note": (
                "the three counts OVERLAP: a slot can fail more than one "
                "term, and partitioning them would invent a precedence the "
                "model does not have"
            ),
            "outage_rate": self.outage / self.decision_steps,
            "served_rate": self.served / self.decision_steps,
            "feasible_link_power_w": quantiles(feasible),
            "feasible_budget_fraction": budget_fraction(feasible),
            "infeasible_required_power_w": quantiles(infeasible),
            "infeasible_budget_fraction": budget_fraction(infeasible),
            "power_gate_is_binding": bool(self.outage > 0),
            "ceiling_w": p_max_w,
        }


def run_probe_p7(
    *,
    prereg: PreregRecord,
    policy: ReferencePolicyRunner,
    environment: StepEnvironment,
    epochs: Sequence[dt.datetime],
    streams: ProbeStreams,
) -> dict[str, object]:
    assert_probe_is_frozen(prereg, "P7", policy)
    accumulator = P7Accumulator()
    for observation, _actions, outcome in drive(
        environment, policy, epochs, streams
    ):
        accumulator.observe(observation, outcome)
    physics = environment.physics
    return {
        "prereg_digest": prereg.digest,
        "policy": policy.declaration.as_dict(),
        "epochs": [epoch.isoformat() for epoch in epochs],
        "segment_warm_start": physics.segment_warm_start,
    } | accumulator.summarise(
        p0_w=physics.segment_start_power_w, p_max_w=physics.beam_power_max_w
    )
