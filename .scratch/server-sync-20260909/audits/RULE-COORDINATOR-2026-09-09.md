# Rule coordinator diagnostic — 2026-09-09

Status: `DIAGNOSTIC_NOT_CLAIM`. No learning, model, head, training, or TEST/claim-panel data were used.

## Pooled energy efficiency

| arm | pooled bits | pooled joules | pooled EE (bit/J) |
|---|---:|---:|---:|
| **BASELINE** | 147,389,571,635.238 | 53,144.373946 | **2,773,380.524** |
| **UNILATERAL** | 511,891,582,624.180 | 21,281.861487 | **24,052,951.521** |
| **RULE** | 151,786,618,970.053 | 52,153.715538 | **2,910,370.189** |

**RULE versus UNILATERAL: -87.900154%.** RULE versus BASELINE: +4.939447%.

The RULE-over-UNILATERAL contrast is service-valid at every anchor: **no**; RULE served fewer users on at least one anchor, so the EE gain does not count.

## Served counts at every anchor

Counts are users with any realised PHY service during the exact 48-boundary interval. Parentheses show decision-instant guard counts.

| world | anchor | step | carrier | BASELINE | UNILATERAL | RULE | RULE family |
|---:|---:|---:|---|---:|---:|---:|---|
| 1 | 3 | 1 | nearest-eligible | 37 (27) | 83 (83) | 38 (27) | occupancy_activation |
| 1 | 4 | 1 | stay-if-possible | 45 (38) | 92 (93) | 49 (40) | occupancy_activation |
| 2 | 0 | 0 | nearest-eligible | 33 (30) | 93 (91) | 34 (31) | occupancy_activation |
| 2 | 1 | 0 | stay-if-possible | 33 (30) | 93 (91) | 34 (31) | occupancy_activation |
| 2 | 2 | 0 | random-masked | 3 (2) | 88 (85) | 6 (5) | occupancy_activation |
| 2 | 3 | 1 | nearest-eligible | 44 (39) | 97 (96) | 44 (39) | occupancy_activation |
| 2 | 4 | 1 | stay-if-possible | 31 (29) | 88 (93) | 32 (30) | occupancy_activation |

## Per-family breakdown

`generated` is every deterministic candidate scored by the exact engine; the rule commits the first strict improvement in family/key order.

| family | generated | guard-passed | improving | fired | Δ bits vs BASELINE | Δ J vs BASELINE | EE vs BASELINE on fired anchors | EE vs UNILATERAL on fired anchors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| occupancy_activation | 133 | 118 | 84 | 7 | +4,397,047,334.815 | -990.658407 | +4.939447% | -87.900154% |

### Occupancy correction and elevation-dependent threshold

Only beams with **starting occupancy exactly 1** seed activation candidates. Starting-occupancy-2 activation coalitions are not mixed into this family. Across 146 singleton-beam observations at actual elevations 34.361–82.538°, the required occupancy ranged from 3 to 4 (variation 1; counts {"3": 132, "4": 14}).

The threshold is recomputed as the first `n` for which the engine's actual-elevation `q_0.10(elevation) × Gamma_r(n)` reaches the lowest frozen ACM threshold; the 10° known-answer test requires `n=3`.

## Rule decision times

Declared budget: **10.0 s**, unchanged. Classification: **DEPLOYABLE**. Mean 2.413571 s; p50 1.765172 s; p95 5.401365 s; max 6.478659 s; 7/7 anchors within budget.

| world | anchor | RULE decision (s) | within 10 s | UNILATERAL convergence (s) | iterations |
|---:|---:|---:|---|---:|---:|
| 1 | 3 | 1.982035 | yes | 328.790898 | 48 |
| 1 | 4 | 2.887680 | yes | 1052.443470 | 58 |
| 2 | 0 | 1.742412 | yes | 231.068115 | 58 |
| 2 | 1 | 0.759166 | yes | 240.337499 | 58 |
| 2 | 2 | 6.478659 | yes | 386.718720 | 67 |
| 2 | 3 | 1.765172 | yes | 231.026151 | 54 |
| 2 | 4 | 1.279875 | yes | 738.871664 | 59 |

## Method and integrity

- Evaluated 7 real TRAIN anchor/carrier contexts from worlds [1, 2] under sealed `a-r0` calibration. Every RULE candidate used the full 48-boundary realised engine. UNILATERAL used the sealed C1 decision-instant exact-engine score over the unchanged top-8 live-legal action shortlist, and its committed configuration then received the same full 48-boundary realised evaluation. No proxy, learned value, model, or head selected either arm.
- BASELINE is the incumbent fixed reference assignment at that anchor. UNILATERAL repeatedly chooses the best strict exact-objective single-user move in the sealed C1 action surface until none improves, with no deadline fallback. RULE scores all generated candidates, applies the unchanged decision-instant served-count guard, and commits the first strict exact-objective improvement in the declared family order.
- Per the scope reduction, only occupancy activation was implemented and timed. Multi-aggressor relief and beam evacuation were not run.
- Merged receipt SHA-256: `9bdae91f4d2aead7d026495290ea9a4a4669103ce20fef7ad925e0228ff4ce97`. Raw receipts are under `/home/sat/mcrl-v025-rule-ws/.scratch/multi-catfish-v025-rule-coordinator/results`. No large intermediate was created: immutable multi-gigabyte tapes were read in place, and `/tmp` was not used.
