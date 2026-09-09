# Rule coordinator diagnostic — 2026-09-09

Status: `DIAGNOSTIC_NOT_CLAIM`. No learning, model, head, training, or TEST/claim-panel data were used.

## Pooled energy efficiency

| arm | pooled bits | pooled joules | pooled EE (bit/J) |
|---|---:|---:|---:|
| **BASELINE** | 207,173,936,424.021 | 78,325.820493 | **2,645,027.337** |
| **UNILATERAL** | 782,448,797,601.621 | 29,741.834645 | **26,308,020.569** |
| **RULE** | 214,412,552,659.577 | 77,002.265383 | **2,784,496.685** |

**RULE versus UNILATERAL: -89.415788%.** RULE versus BASELINE: +5.272889%.

RULE served at least as many users as BASELINE at every anchor: **yes**; its gain over BASELINE was not bought by serving fewer users.  
RULE served fewer users than UNILATERAL at **10/10 anchors**; it also has lower EE, so there is no RULE-over-UNILATERAL coordination gain.

## Served counts at every anchor

Counts are users with any realised PHY service during the exact 48-boundary interval. Parentheses show decision-instant guard counts.

| world | anchor | step | carrier | BASELINE | UNILATERAL | RULE | RULE family |
|---:|---:|---:|---|---:|---:|---:|---|
| 1 | 0 | 0 | nearest-eligible | 43 (40) | 92 (92) | 45 (43) | occupancy_activation |
| 1 | 1 | 0 | stay-if-possible | 43 (40) | 92 (92) | 45 (43) | occupancy_activation |
| 1 | 2 | 0 | random-masked | 8 (5) | 97 (97) | 8 (5) | occupancy_activation |
| 1 | 3 | 1 | nearest-eligible | 37 (27) | 95 (95) | 38 (27) | occupancy_activation |
| 1 | 4 | 1 | stay-if-possible | 45 (38) | 97 (97) | 49 (40) | occupancy_activation |
| 2 | 0 | 0 | nearest-eligible | 33 (30) | 100 (99) | 34 (31) | occupancy_activation |
| 2 | 1 | 0 | stay-if-possible | 33 (30) | 100 (99) | 34 (31) | occupancy_activation |
| 2 | 2 | 0 | random-masked | 3 (2) | 96 (96) | 6 (5) | occupancy_activation |
| 2 | 3 | 1 | nearest-eligible | 44 (39) | 99 (98) | 44 (39) | occupancy_activation |
| 2 | 4 | 1 | stay-if-possible | 31 (29) | 93 (92) | 32 (30) | occupancy_activation |

## Per-family breakdown

`generated` is every deterministic candidate scored by the exact engine; the rule commits the first strict improvement in family/key order.

| family | generated | guard-passed | improving | fired | Δ bits vs BASELINE | Δ J vs BASELINE | EE vs BASELINE on fired anchors | EE vs UNILATERAL on fired anchors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| occupancy_activation | 221 | 194 | 136 | 10 | +7,238,616,235.556 | -1,323.555109 | +5.272889% | -89.415788% |

### Occupancy correction and elevation-dependent threshold

Only beams with **starting occupancy exactly 1** seed activation candidates. Starting-occupancy-2 activation coalitions are not mixed into this family. Across 243 singleton-beam observations at actual elevations 34.361–86.457°, the required occupancy ranged from 3 to 4 (variation 1; counts {"3": 207, "4": 36}).

The threshold is recomputed as the first `n` for which the engine's actual-elevation `q_0.10(elevation) × Gamma_r(n)` reaches the lowest frozen ACM threshold. At 10°, the engine returns `q_0.10=0.42923539` and the lowest threshold is `0.7174947935`, requiring `n=3`.

## Rule decision times

Declared budget: **10.0 s**, unchanged. Classification: **DEPLOYABLE**. Mean 3.013054 s; p50 2.145878 s; p95 6.959470 s; max 7.455743 s; 10/10 anchors within budget.

| world | anchor | RULE decision (s) | within 10 s | UNILATERAL convergence (s) | iterations |
|---:|---:|---:|---|---:|---:|
| 1 | 0 | 3.204819 | yes | 2487.886216 | 50 |
| 1 | 1 | 2.198178 | yes | 2405.795518 | 50 |
| 1 | 2 | 7.455743 | yes | 2702.536155 | 82 |
| 1 | 3 | 2.093579 | yes | 2263.837521 | 60 |
| 1 | 4 | 3.022769 | yes | 3681.103809 | 64 |
| 2 | 0 | 1.803659 | yes | 1351.030054 | 69 |
| 2 | 1 | 0.860560 | yes | 1164.995121 | 69 |
| 2 | 2 | 6.352915 | yes | 3645.118711 | 77 |
| 2 | 3 | 1.827703 | yes | 1008.479616 | 54 |
| 2 | 4 | 1.310619 | yes | 2486.012997 | 58 |

## Method and integrity

- Evaluated 10 real TRAIN anchor/carrier contexts from worlds [1, 2] under sealed `a-r0` calibration. Every RULE candidate used the full 48-boundary realised engine. UNILATERAL used the exact decision-instant engine score over all live legal actions, matching the engine's iterated single-user comparator, and its committed configuration then received the same full 48-boundary realised evaluation. No proxy, learned value, model, or head selected either arm.
- BASELINE is the incumbent fixed reference assignment at that anchor. UNILATERAL repeatedly chooses the best strict exact-objective single-user move in the sealed C1 action surface until none improves, with no deadline fallback. RULE scores all generated candidates, applies the unchanged decision-instant served-count guard, and commits the first strict exact-objective improvement in the declared family order.
- Per the scope reduction, only occupancy activation was implemented and timed. Multi-aggressor relief and beam evacuation were not run.
- Merged receipt SHA-256: `f5f24cb76b55becce64538ecc823bf27026fbd300ded708b6001ee805a2d71a8`. Raw receipt paths and their digests are recorded in the merged JSON receipt. No large intermediate was created: immutable multi-gigabyte tapes were read in place, and `/tmp` was not used.
- The workspace bootstrap commit's tree matches engine commit `75c5c78c`. The final diagnostic files could not be committed because this session mounts `.git` read-only (`index.lock: Read-only file system`); they remain written in the workspace.
