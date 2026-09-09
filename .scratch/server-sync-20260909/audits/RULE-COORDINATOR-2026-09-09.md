# Rule coordinator diagnostic — 2026-09-09

Status: `DIAGNOSTIC_NOT_CLAIM`. No learning, model, head, training, or TEST/claim-panel data were used.

## Pooled energy efficiency

| arm | pooled bits | pooled joules | pooled EE (bit/J) |
|---|---:|---:|---:|
| **BASELINE** | 96,388,100,537.037 | 39,267.042371 | **2,454,681.960** |
| **UNILATERAL** | 371,960,912,321.058 | 15,034.418884 | **24,740,624.509** |
| **RULE** | 98,674,170,990.370 | 38,670.437360 | **2,551,669.382** |

**RULE versus UNILATERAL: -89.686318%.** RULE versus BASELINE: +3.951120%.

The RULE-over-UNILATERAL contrast is service-valid at every anchor: **no**; RULE served fewer users on at least one anchor, so the EE gain does not count.

## Served counts at every anchor

Counts are users with any realised PHY service during the exact 48-boundary interval. Parentheses show decision-instant guard counts.

| world | anchor | step | carrier | BASELINE | UNILATERAL | RULE | RULE family |
|---:|---:|---:|---|---:|---:|---:|---|
| 2 | 0 | 0 | nearest-eligible | 33 (30) | 93 (91) | 34 (31) | occupancy_activation |
| 2 | 1 | 0 | stay-if-possible | 33 (30) | 93 (91) | 34 (31) | occupancy_activation |
| 2 | 2 | 0 | random-masked | 3 (2) | 88 (85) | 6 (5) | occupancy_activation |
| 2 | 3 | 1 | nearest-eligible | 44 (39) | 97 (96) | 44 (39) | occupancy_activation |
| 2 | 4 | 1 | stay-if-possible | 31 (29) | 88 (93) | 32 (30) | occupancy_activation |

## Per-family breakdown

`generated` is every deterministic candidate scored by the exact engine; the rule commits the first strict improvement in family/key order.

| family | generated | guard-passed | improving | fired | Δ bits vs BASELINE | Δ J vs BASELINE | EE vs BASELINE on fired anchors | EE vs UNILATERAL on fired anchors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| occupancy_activation | 109 | 99 | 74 | 5 | +2,286,070,453.333 | -596.605011 | +3.951120% | -89.686318% |

### Occupancy correction and elevation-dependent threshold

Only beams with **starting occupancy exactly 1** seed activation candidates. Starting-occupancy-2 activation coalitions are not mixed into this family. Across 119 singleton-beam observations at actual elevations 34.361–82.538°, the required occupancy ranged from 3 to 4 (variation 1; counts {"3": 108, "4": 11}).

The threshold is recomputed as the first `n` for which the engine's actual-elevation `q_0.10(elevation) × Gamma_r(n)` reaches the lowest frozen ACM threshold; the 10° known-answer test requires `n=3`.

## Rule decision times

Declared budget: **10.0 s**, unchanged. Classification: **DEPLOYABLE**. Mean 2.405057 s; p50 1.742412 s; p95 5.535962 s; max 6.478659 s; 5/5 anchors within budget.

| world | anchor | RULE decision (s) | within 10 s | UNILATERAL convergence (s) | iterations |
|---:|---:|---:|---|---:|---:|
| 2 | 0 | 1.742412 | yes | 231.068115 | 58 |
| 2 | 1 | 0.759166 | yes | 240.337499 | 58 |
| 2 | 2 | 6.478659 | yes | 386.718720 | 67 |
| 2 | 3 | 1.765172 | yes | 231.026151 | 54 |
| 2 | 4 | 1.279875 | yes | 738.871664 | 59 |

## Method and integrity

- Evaluated 5 real TRAIN anchor/carrier contexts from worlds [2] under sealed `a-r0` calibration. Every RULE candidate used the full 48-boundary realised engine. UNILATERAL used the sealed C1 decision-instant exact-engine score over the unchanged top-8 live-legal action shortlist, and its committed configuration then received the same full 48-boundary realised evaluation. No proxy, learned value, model, or head selected either arm.
- BASELINE is the incumbent fixed reference assignment at that anchor. UNILATERAL repeatedly chooses the best strict exact-objective single-user move in the sealed C1 action surface until none improves, with no deadline fallback. RULE scores all generated candidates, applies the unchanged decision-instant served-count guard, and commits the first strict exact-objective improvement in the declared family order.
- Per the scope reduction, only occupancy activation was implemented and timed. Multi-aggressor relief and beam evacuation were not run.
- Merged receipt SHA-256: `09f923eafb420f36a0e56f9cee77a52131621430cb8c3374b464c670fe356652`. Raw receipts are under `/home/sat/mcrl-v025-rule-ws/.scratch/multi-catfish-v025-rule-coordinator/results`. No large intermediate was created: immutable multi-gigabyte tapes were read in place, and `/tmp` was not used.
