# Controller finding — the mechanism paper has no room, and our own cited source is why
Recorded 2026-09-10 from a reading of twelve papers, commissioned with the instruction that if the honest answer was "very little is left, say that". `DIAGNOSTIC_NOT_CLAIM`. No code, no run.

## The provisioning construction is an error, confirmed a third time
No paper in the corpus provisions power to a nominal, unfaded threshold. Every one puts the fade **inside** the quantity that must clear the threshold. Applying a fade quantile downstream of the power solve appears nowhere. And the 1.7 dB implementation margin is a different kind of quantity that cannot stand in for a fade margin.

Three independent lines now agree — an ultra-effort adjudication, an independent model given a neutral prompt, and the field's own conventions. This is settled.

## Our numerator is non-standard, and in the direction that flatters us
The field credits `min(capacity, demand)`: delivered capacity above the contracted rate is explicitly **not** counted. Ours counts it, and the surplus is rung-dependent — occupancy three receives 10.03 % above contract. That is the same defect the adversarial review found from the other direction.

Pooled efficiency is a genuine convention, described in the corpus as having the strongest physical interpretation, but reporting **only** pooled is against convention: the papers that care about heterogeneity report the summed-per-user form alongside and criticise pooled for hiding per-link allocation.

A per-chain fixed power cost is standard. **The square-root amplifier law appears nowhere in this corpus** — I had told the owner it was standard practice; it is a recognised model but it is not what this literature uses, and I overstated it.

## The prior art is our own source paper
Chen, Shen, Feng, Yang and Wu, VTC2024-Spring — the paper we cite for the beam pattern — already does, in Ka-band multi-beam LEO: joint handover and beam switching, per-beam transmit power as a decision variable, **bandwidth shared equally among a beam's users so the achievable rate is an explicit function of beam occupancy**, an occupancy-coupled power loop that steps power up whenever a user in the beam falls below threshold, a per-user rate floor, intra- and inter-satellite interference, and **pooled energy efficiency as the reported objective**.

That is our contribution list, in a 2024 conference paper, and it is a paper already inside our own repository.

The occupancy-to-rate dependence is older still: Ye and colleagues, 2013, where equal sharing is not merely assumed but **proved optimal** for logarithmic utility. Adopting it is adopting a known-correct default, not a modelling advance.

## The one element that is genuinely ours
**A discrete mode table inside an energy-efficiency and handover loop is absent from all twelve papers.** Every rate expression in the corpus is Shannon; this was verified mechanically across the directory. Two papers cite the standard, one only for its channel-update rate and one only as motivation for beam hopping, and both then use Shannon.

But this cuts against us twice. The corpus reviewer judges a discrete mode table to be standard industrial practice rather than a research contribution. And the consequence we had built on — that the ladder inverts the sign of the occupancy term — turned out to be the reference-frame slip, while the interior occupancy optimum was shown by adversarial review to exist without any ladder at all, at continuous occupancy 7.6637.

So our only novel modelling element's main observable consequence was a defect.

## What this closes and what it does not
**It closes the mechanism paper.** Two independent strategic reviews recommended making the physical mechanism the contribution and treating the learned coordinator as a follow-on. That route is now shut on novelty grounds, and the owner's decision on that reframing no longer needs taking.

**It does not close the learned route**, which is what the owner wanted throughout. This corpus does not address a learned multi-component coordinator evaluated under a decision-time budget. That question is with a separate reading, still running. The field is not empty there either — a 2026 paper does handover jointly with power under deep reinforcement learning with a split discrete-continuous action — so the room has to be found, not assumed.

## Standing
No decision is taken here. The obligation this creates is to stop investing in the mechanism framing.
