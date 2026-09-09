"""Probe P4 — does the interference model bind, and which term dominates?

⚠ **The number P4 is genuinely vacant, and this probe is unrelated to what
used to hold it.**  SDD §4 retired the old P4 series at r5 (dispersion vs
EE, the EE-optimal beam count, the source of the 3.9x) as *post-baseline
analysis* questions.  Saying so is the point of this paragraph: a reused
number with no note is how the W-24 audit's P5 defect happened.

**The ablation needs no second run, and that is worth stating.**  "SINR
without the co-colour sum" is not a separate rollout — ``γ = W/(I + σ²)``
and both ``W`` and ``I`` are reported, so ``γ_noiseonly = γ·(I + σ²)/σ²``
is exact arithmetic on the same step.  Re-running with interference
disabled would change the *served set* (feasibility is unaffected, but the
policy and every downstream count are not necessarily), and then the two
arms would differ by more than the thing being ablated.  The cheapest
correct ablation is the one that does not re-sample.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ..env.reference_policy import ReferencePolicyRunner
from ..env.step import StepEnvironment
from ..errors import MCRLContractError
from .prereg import PreregRecord
from .probe_harness import ProbeStreams, assert_probe_is_frozen, drive, quantiles


@dataclass
class P4Accumulator:
    """Running tallies for one P4 run."""

    served_links: int = 0
    intra_w: list[float] = field(default_factory=list)
    inter_w: list[float] = field(default_factory=list)
    intra_fraction: list[float] = field(default_factory=list)
    sinr_db: list[float] = field(default_factory=list)
    sinr_no_interference_db: list[float] = field(default_factory=list)
    interference_to_noise_db: list[float] = field(default_factory=list)
    radiating_beams: list[float] = field(default_factory=list)
    shared_cell_events: int = 0
    """Steps where two satellites illuminated one cell — (3.12b)'s ``v' = v``."""
    shared_cell_steps: int = 0

    def observe(self, outcome, *, noise_w: float) -> None:
        resolution = outcome.resolution
        served = resolution.served
        self.radiating_beams.append(float(outcome.radiating.count))

        # (3.12b)'s v' = v: the same cell lit by two different satellites.
        cells = outcome.radiating.cell_ids.tolist()
        self.shared_cell_steps += 1
        if len(cells) != len(set(cells)):
            self.shared_cell_events += 1

        if not np.any(served):
            return
        self.served_links += int(np.count_nonzero(served))
        intra = outcome.interference.intra_w[served]
        inter = outcome.interference.inter_w[served]
        total = intra + inter
        self.intra_w.extend(intra.tolist())
        self.inter_w.extend(inter.tolist())
        self.intra_fraction.extend(
            np.where(total > 0.0, intra / np.where(total > 0.0, total, 1.0), 0.0).tolist()
        )

        sinr = outcome.link_sinr[served]
        positive = sinr > 0.0
        if np.any(positive):
            self.sinr_db.extend((10.0 * np.log10(sinr[positive])).tolist())
            # Exact, not a second rollout: gamma_no_I = gamma * (I + s2)/s2.
            scale = (total[positive] + noise_w) / noise_w
            self.sinr_no_interference_db.extend(
                (10.0 * np.log10(sinr[positive] * scale)).tolist()
            )
            self.interference_to_noise_db.extend(
                (10.0 * np.log10(np.maximum(total[positive], 1e-300) / noise_w)).tolist()
            )

    def summarise(self) -> dict[str, object]:
        if self.served_links == 0:
            raise MCRLContractError("P4 saw no served link to measure")
        with_i = np.array(self.sinr_db, dtype=np.float64)
        without_i = np.array(self.sinr_no_interference_db, dtype=np.float64)
        return {
            "probe": "P4",
            "served_links": self.served_links,
            "radiating_beams_per_step": quantiles(np.array(self.radiating_beams)),
            "intra_interference_w": quantiles(np.array(self.intra_w)),
            "inter_interference_w": quantiles(np.array(self.inter_w)),
            "intra_fraction_of_total": quantiles(np.array(self.intra_fraction)),
            "interference_to_noise_db": quantiles(
                np.array(self.interference_to_noise_db)
            ),
            "sinr_db": quantiles(with_i),
            "sinr_db_without_co_colour_sum": quantiles(without_i),
            "sinr_cost_of_interference_db": quantiles(without_i - with_i),
            "interference_is_binding": bool(
                float(np.median(without_i - with_i)) > 1.0
            ),
            "two_satellites_one_cell_step_fraction": (
                self.shared_cell_events / self.shared_cell_steps
                if self.shared_cell_steps
                else 0.0
            ),
            "ablation_method": (
                "arithmetic on the same step (gamma * (I + sigma^2)/sigma^2), "
                "not a second rollout -- a re-run would change the served "
                "set and the two arms would differ by more than the ablated "
                "term"
            ),
        }


def run_probe_p4(
    *,
    prereg: PreregRecord,
    policy: ReferencePolicyRunner,
    environment: StepEnvironment,
    epochs: Sequence[dt.datetime],
    streams: ProbeStreams,
) -> dict[str, object]:
    assert_probe_is_frozen(prereg, "P4", policy)
    accumulator = P4Accumulator()
    noise = environment.physics.noise_power_w
    for _observation, _actions, outcome in drive(
        environment, policy, epochs, streams
    ):
        accumulator.observe(outcome, noise_w=noise)
    return {
        "prereg_digest": prereg.digest,
        "policy": policy.declaration.as_dict(),
        "epochs": [epoch.isoformat() for epoch in epochs],
    } | accumulator.summarise()
