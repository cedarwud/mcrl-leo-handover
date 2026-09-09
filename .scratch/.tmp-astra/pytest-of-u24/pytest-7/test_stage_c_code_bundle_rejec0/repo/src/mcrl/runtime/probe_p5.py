"""Probe P5 — is S.465-6's envelope evaluated where it is defined?

**This is SDD §4's own P5, restored on 2026-08-23.**  It had been displaced
by the action-set-contraction probe (now P7), which left its obligation
with no owner at all.

Eq. (3.10c) takes the receive pattern from ITU-R S.465-6, and ch3 discloses
its **frequency** range (2–31 GHz).  The recommendation also carries an
**angular** floor, ``θ^R_min = max(1°, 100λ/D)`` — 2.498° for this work's
0.6 m Ka VSAT at 20 GHz — below which the reference envelope simply does
not apply and (3.10c) is held at ``G_R,max`` by its clip.  Nothing in the
paper says how often that happens.  P5 measures it.

**Two numbers, because one of them can mislead.**  A fraction of
*evaluations* below the floor says how often the clip is reached; a
fraction of *interference power* carried by those evaluations says whether
it matters.  A floor hit rarely but by the dominant terms reads completely
differently from one hit often by negligible ones, and only reporting the
count would not distinguish them.

⚠ **Co-satellite terms sit at exactly 0° and are not a finding.**  P-10:
the terminal cannot resolve two beams of one satellite, so their at-user
separation is zero by construction and every one of them is "below the
floor" trivially.  They are counted separately rather than folded in,
because burying them in the headline fraction would manufacture a
disclosure out of a modelling assumption.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ..env.antenna import RX_ENVELOPE_MIN_DEG, RX_TERMINAL_DIAMETER_M
from ..env.reference_policy import ReferencePolicyRunner
from ..env.step import StepEnvironment
from ..errors import MCRLContractError
from .prereg import PreregRecord
from .probe_harness import ProbeStreams, assert_probe_is_frozen, drive, quantiles


@dataclass
class P5Accumulator:
    """Running tallies for one P5 run."""

    separations: list[float] = field(default_factory=list)
    """Cross-satellite separations only; co-satellite zeros are counted apart."""
    below_floor_power_w: float = 0.0
    total_power_w: float = 0.0
    co_satellite_terms: int = 0
    cross_satellite_terms: int = 0
    contributing_terms: int = 0
    """Cross-satellite AND co-colour: the ones that actually enter ``I``."""

    def observe(self, outcome) -> None:
        served = outcome.resolution.served
        if not np.any(served) or outcome.radiating.count == 0:
            return
        separation = outcome.separation_deg[served]
        power = outcome.interference_terms_w[served]

        # A term is co-satellite iff it comes from the victim's own serving
        # satellite; those are exactly 0 deg by P-10 and are not evidence.
        serving = outcome.resolution.serving_satellite[served]
        co_satellite = outcome.radiating.norad_ids[None, :] == serving[:, None]
        self.co_satellite_terms += int(np.count_nonzero(co_satellite))

        cross = ~co_satellite
        self.cross_satellite_terms += int(np.count_nonzero(cross))
        self.separations.extend(separation[cross].tolist())

        # ⚠ The POWER fraction must be weighted over the terms that actually
        # enter I -- co-colour ones.  ``interference_terms_w`` is the raw
        # p*G^T*H for every radiating beam, BEFORE the colour mask, so
        # weighting by all of it would count power that (3.12) discards and
        # the disclosure would be about a sum the model never forms.
        cells = outcome.resolution.serving_cell[served]
        grid = outcome.radiating
        wanted_colour = np.array(
            [grid.colors[grid.cell_ids.tolist().index(int(c))]
             if int(c) in grid.cell_ids.tolist() else -1
             for c in cells.tolist()],
            dtype=np.int64,
        )
        co_colour = grid.colors[None, :] == wanted_colour[:, None]
        contributing = cross & co_colour
        self.contributing_terms += int(np.count_nonzero(contributing))

        below = contributing & (separation < RX_ENVELOPE_MIN_DEG)
        self.below_floor_power_w += float(power[below].sum())
        self.total_power_w += float(power[contributing].sum())

    def summarise(self) -> dict[str, object]:
        if self.cross_satellite_terms == 0:
            raise MCRLContractError(
                "P5 saw no cross-satellite interference term; there is "
                "nothing for the receive envelope to be evaluated on"
            )
        separations = np.array(self.separations, dtype=np.float64)
        below = separations < RX_ENVELOPE_MIN_DEG
        return {
            "probe": "P5",
            "theta_r_min_deg": RX_ENVELOPE_MIN_DEG,
            "terminal_diameter_m": RX_TERMINAL_DIAMETER_M,
            "cross_satellite_terms": self.cross_satellite_terms,
            "co_satellite_terms": self.co_satellite_terms,
            "contributing_terms": self.contributing_terms,
            "separation_deg": quantiles(separations),
            # The disclosure ch5 §5.1 owes for (3.10c).
            "fraction_of_evaluations_below_theta_r_min": float(np.mean(below)),
            "fraction_of_interference_power_below_theta_r_min": (
                self.below_floor_power_w / self.total_power_w
                if self.total_power_w > 0.0
                else 0.0
            ),
            "power_weighting_note": (
                "weighted over CO-COLOUR cross-satellite terms only -- the "
                "ones that actually enter I.  Weighting over all radiating "
                "beams would count power (3.12) discards, and the disclosure "
                "would be about a sum the model never forms"
            ),
            "co_satellite_note": (
                "co-satellite terms sit at exactly 0 deg by P-10 (the "
                "terminal cannot resolve two beams of one satellite) and are "
                "excluded from both fractions: counting them would "
                "manufacture a disclosure out of a modelling assumption"
            ),
        }


def run_probe_p5(
    *,
    prereg: PreregRecord,
    policy: ReferencePolicyRunner,
    environment: StepEnvironment,
    epochs: Sequence[dt.datetime],
    streams: ProbeStreams,
) -> dict[str, object]:
    entry = assert_probe_is_frozen(prereg, "P5", policy)
    frozen_floor = (
        prereg.sections.get("antenna_and_link_budget", {})
        .get("rx_envelope_min_deg")
    )
    if frozen_floor is None:
        raise MCRLContractError(
            "theta^R_min is not in the frozen record; P5 would be measuring "
            "against a threshold nobody committed to"
        )
    if abs(float(frozen_floor) - RX_ENVELOPE_MIN_DEG) > 1e-9:
        raise MCRLContractError(
            f"the frozen theta^R_min ({frozen_floor}) and the code's "
            f"({RX_ENVELOPE_MIN_DEG}) disagree"
        )

    accumulator = P5Accumulator()
    for _observation, _actions, outcome in drive(
        environment, policy, epochs, streams
    ):
        accumulator.observe(outcome)
    del entry
    return {
        "prereg_digest": prereg.digest,
        "policy": policy.declaration.as_dict(),
        "epochs": [epoch.isoformat() for epoch in epochs],
    } | accumulator.summarise()
