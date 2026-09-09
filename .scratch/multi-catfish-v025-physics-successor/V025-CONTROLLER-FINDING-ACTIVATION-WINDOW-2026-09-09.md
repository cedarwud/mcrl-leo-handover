# Controller finding — the C3 mechanism is real and verified, and it is a product of the defective rule
Recorded 2026-09-09, server clock about 09:05 UTC. Computed from the engine's own 28-mode table and its own `channel.fading_product_quantile`. **No probe or matrix outcome exists.**

## 1. The condition, and the result
Round 11A derives an exact condition for a beam holding one or two users to select no transmitted mode while three users activate one: `q·Γ(n) < γ_min` for `n = 1, 2` and `q·Γ(n) >= γ_min` for `n = 3`. Expanded against the mode table this is a window on the fading quantile alone, because the implementation margin and roll-off shifts cancel in the ratio.

The engine's own table reproduces round 11A's window to ten decimal places:

`0.3483373150 <= q < 0.6237348355`, that is `2.0500 dB < M <= 4.5800 dB` with `M = −10·log10(q)`.

**The engine's actual quantile falls inside that window at every realistic elevation.**

| elevation | q10 | M, dB | inside |
|---:|---:|---:|---|
| 10 | 0.42923539 | 3.6730 | yes |
| 20 | 0.53431848 | 2.7220 | yes |
| 30 | 0.51210438 | 2.9064 | yes |
| 40 | 0.46632501 | 3.3131 | yes |
| 50 | 0.42017210 | 3.7657 | yes |
| 60 | 0.37823375 | 4.2224 | yes |
| 90 | 0.77494862 | 1.1073 | no |

At the 10-degree elevation the mechanism figure uses, `q10 = 0.42923539` and `γ_min = 0.7174947935`:

| occupancy | Γ(n), dB | q·Γ(n) | vs γ_min | outcome |
|---:|---:|---:|---|---|
| 1 | −1.441812 | 0.30797 | below | no transmitted mode |
| 2 | +0.608188 | 0.49382 | below | no transmitted mode |
| 3 | +3.138188 | 0.88407 | above | **mode selected** |

## 2. Why this matters for C3
Two arrivals are required to activate the beam and one arrival achieves nothing. Moving either user alone contributes nothing to the objective through this channel; moving both together takes the beam from zero credited bits to positive. The individual marginals are flat and the joint move is not, so the entire difference lands in the interaction term.

**This is a super-additive pair verified against the engine's own numbers, not a conjecture.** It is the first concrete mechanism in this project for which the arithmetic has been checked rather than argued.

It also explains an observation that had no explanation. The census reports `NO_MODE` for 76.5551 % of transmissions at a mean beam occupancy of 2.016 with a maximum of 6. Under this condition every beam holding one or two users is `NO_MODE` **by construction**, and those are the majority.

## 3. The finding that must travel with it
**This mechanism exists because of the margin rule that round 11B showed to be mathematically misjustified.**

If the rule is amended so that reserve is carried in transmit power, a lone user closes its link at roughly 0.634 W at boresight, inside the 1.65 W cap. Low occupancy stops producing `NO_MODE`, and **this mechanism disappears entirely**.

So the strongest C3 mechanism found to date is a product of a defect. Stating that plainly is not optional. A coordination gain measured inside a controller-induced outage is a finding about our controller, not about satellites, and it would not survive review.

## 4. What survives an amendment
Round 11A names mechanisms that do not depend on the margin rule at all:
* **Complete hardware evacuation.** A beam's circuit power is saved only when every occupant leaves. That is a unanimity contribution with strictly positive interaction and it needs no decode threshold. The same holds for the final users leaving a satellite with a switchable common processing term.
* **Shared opening cost.** Several movers opening one previously inactive beam pay the opening charge once jointly and once each in their singleton counterfactuals.
* **Swaps and exchange cycles**, which preserve occupancy and avoid the transient congestion a unilateral move creates.

These are real and they are weaker. A four-user evacuation dividend is also invisible to any neighbourhood capped at three movers, which the current search families are.

## 5. Three corrections to the search design, from round 11A
1. **The interference-rescue premise holds only for cap-bound links.** For an uncapped exactly target-tracking link, `p = Γ(n)(N+I)/h` gives `SINR_nominal = Γ(n)` independent of `I`, so relieving interference lowers power and does not change the selected mode. The mechanism survives only because 93.675 % of failing transmissions sit at the cap, and the reasoning in the fifth-family declaration must be rewritten to say so.
2. **Ranking candidates by `|d_i|` is unjustified in both directions.** Adding a modular per-user cost changes every singleton gain and no mixed difference whatsoever, so neither the most negative nor the least negative singleton is the correct interaction ranking. Search must be organised by **mechanism**, not by score order. My neighbourhood declaration argued for the least negative and that argument is withdrawn.
3. **`Ψ_A` for three or more movers is the sum of every interaction order above one**, not a pair effect. A zero can hide cancellation between positive and negative orders, and it must be reported as an aggregate rather than as a pairwise quantity.

## 6. Standing
This records a verified calculation and its consequence. It authorises no run, changes no threshold, sign, seed, horizon, price or acceptance rule, and creates no gate. Whether the margin rule is amended remains the owner's decision, and this finding must not be used to argue against amending it.
