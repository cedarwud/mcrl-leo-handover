# Erratum 22 — "this physics rewards concentration" is withdrawn; it was a property of one assignment rule

Date: 2026-09-11 ~01:40Z · Controller · Found by BEAMCOUNT, not by me
Source: `/home/sat/mcrl-v025-beamcount-ws/BEAM-COUNT-CAP-2026-09-10.md` (parity to 6 dp on both
targets; `scalar_evaluate_calls = 0` asserted in all three shards)

## What I said, repeatedly, for most of a day

> `d(EE)/d(active) = -425,009.885` bit/J per added active beam, **no sign flip**; spreading costs up
> to 83% of EE; **this physics rewards concentration**; `ROUND_ROBIN` is worst because it spreads.

I used it to explain the z result, to reject load balancing, to frame an "energy side" objective,
and to argue that a jointly constructed crowded profile is where coordination's value lives.

## What is true

BEAMCOUNT **reproduced CROWDCOST's monotone decline exactly** under CROWDCOST's own coverage-first
assignment rule (46.110374 -> 17.478088 Mbit/J). Then, **holding the same beam sets and changing only
the within-set assignment to max-nominal-gain, the sign reverses at every cap.**

**CROWDCOST's arithmetic is intact. What it measured is crowding under one assignment rule, not a
property of beam count.** "This physics rewards concentration" is withdrawn.

## The measurement that replaces it

| construction | pooled EE (Mbit/J) | served | rate-target attainment |
|---|---:|---:|---:|
| **loose cap + max-gain within-set assignment (C=50, 23.25 beams realised)** | **62.502712** | **1200/1200** | **354/1200 (29.5%)** |
| `RSS_MAX` | 41.621560 | 1200/1200 | 297/1200 (24.75%) |
| crowded endpoint (coverage-first, 8 beams) | 46.110374 | 1200/1200 | 30/1200 (2.5%) |

Pooled EE rises **monotonically** as the cap loosens over {8,9,10,15,20,30,50}, from 46.876 to
62.503, with attainment rising 3 -> 354. **No interior peak; no measured cap raises EE**, and at
C = 50 the cap is slack, so the peak is not a cap effect.

- **The feasibility floor is exactly 8 active beams at all 12 anchors**, so a literal 3-beam cap is
  infeasible here. The sibling's `k_cap = 3` is moreover **per satellite**, not system-wide
  (`family_b_step.py:86,725`, `k_universe = l_w * k_cap`, verified on this server).

## What this destroys, including my own arguments

1. **The "energy side / concentration" objective is dead.** What matters is *which option each user
   takes* (gain), not how many beams end up open.
2. **Coordination's last measured justification is gone.** I argued the crowded endpoint's +10.78%
   over `RSS_MAX` was coordination's value. **A per-user gain assignment inside loose beam sets beats
   that jointly constructed profile by ~35%.** There is now no measured configuration where a joint
   construction beats the best per-user rule.
3. `ROUND_ROBIN`'s 3.441227 is explained by **ignoring gain**, not by spreading.
4. The Pareto pair I offered (46.11 / 2.5% vs 41.62 / 24.75%) is **dominated** on both axes by the
   62.50 / 29.5% point, which further undermines the rejected narrative.

## A separate instrumentation warning from the same report

**Boundary-0 selection systematically overstates the full-48 endpoint**: one search raised boundary-0
EE from 71.84 to 114.06 while full-48 EE *fell* to 65.38. Every declared rule must be scored at full
48. This independently confirms ETAFIX's horizon finding.

## Consequences applied

- `C3REACH` stopped: its premise was "can per-user climbing reach the joint 46.11?" — 46.11 is no
  longer the target and a per-user rule already exceeds it.
- `C1VSGAIN` told to add the 62.50 rule as the reference C1 must beat.
- Also corrected: `a0 = 49.07` beams is the **q1-v2** figure; **q1-v1 is 41.28**.

## The error shape, again

I took a measurement made under one construction rule and stated it as a property of the physics,
then built four arguments on it. The same shape as `run-nonlearned-baselines-first` and
`imported-diagnostics-flip-direction`: **a number is a property of the procedure that produced it
until a second procedure reproduces it.**
