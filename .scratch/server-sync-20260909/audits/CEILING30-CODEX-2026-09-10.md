# Coordination headroom diagnostic across 30 TRAIN dates: mean +5.888%, 95% CI [+5.235%, +6.540%]

`DIAGNOSTIC_NOT_CLAIM`

Across 30 dates, the arithmetic mean of the per-date pooled ORACLE_SET-over-UNILATERAL gains is **+5.888%** (date-level sample SD **1.747%**, two-sided 95% Student-t CI **[+5.235%, +6.540%]**). The date is the independent unit: each date first pools bits and joules across its anchors, computes each arm's pooled bit/J, and then forms the ORACLE_SET/UNILATERAL relative gain. This interval is descriptive over the selected dates, not a population-randomization interval.

## Result

| Panel | Dates | Mean gain | Date SD | 95% t CI over dates | Minimum | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| All dates | 30 | +5.888% | 1.747% | [+5.235%, +6.540%] | +3.205% (2026-07-17) | +9.652% (2025-09-30) |
| Full archive span | 20 | +5.978% | 1.696% | [+5.185%, +6.772%] | +3.205% (2026-07-17) | +9.652% (2025-09-30) |
| Single month (January 2026) | 10 | +5.706% | 1.925% | [+4.329%, +7.083%] | +3.266% (2026-01-24) | +8.899% (2026-01-25) |

As a separate weighting—not the headline—the ratio after pooling all 196 anchors across all dates is **+5.926%**. It weights dates by their bits/joules and by the deliberately unequal anchor counts, so it is not used for the date-level CI.

The full-span panel runs from 2025-07-31 to 2026-08-20. Satellite count grows from **8,044** on 2025-07-31 to **10,746** on 2026-08-20; every selected daily file has zero quarantined records. The descriptive Pearson correlation between date gain and satellite count is **r=-0.122** over all 30 dates and **r=-0.166** within the 20-date full-span panel. These correlations do not separate constellation growth from time-varying geometry and are not causal adjustments; the separate January panel is the cleaner check with much less growth mixing.

## Every date

Served counts are sums over that date's anchors and are shown for all three arms. `Q` is the number/share of anchors with at least one qualifying catalogue coalition at the selection boundary.

| Date | Panel | Satellites | Anchors | Gain | Served B / U / O | Q | Wall min | Core h |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025-07-31 | span | 8,044 | 10 | +5.481% | 425 / 983 / 983 | 10/10 (100.0%) | 8.48 | 0.326 |
| 2025-08-18 | span | 8,080 | 8 | +7.685% | 327 / 768 / 780 | 8/8 (100.0%) | 8.23 | 0.318 |
| 2025-09-03 | span | 8,138 | 8 | +6.023% | 406 / 790 / 791 | 8/8 (100.0%) | 8.17 | 0.306 |
| 2025-09-30 | span | 8,390 | 8 | +9.652% | 384 / 741 / 755 | 8/8 (100.0%) | 9.44 | 0.353 |
| 2025-10-17 | span | 8,523 | 6 | +6.238% | 256 / 588 / 591 | 6/6 (100.0%) | 3.93 | 0.150 |
| 2025-11-04 | span | 8,645 | 6 | +4.856% | 253 / 597 / 598 | 6/6 (100.0%) | 3.39 | 0.123 |
| 2025-11-20 | span | 8,885 | 6 | +3.973% | 228 / 593 / 593 | 6/6 (100.0%) | 4.21 | 0.161 |
| 2025-12-07 | span | 9,038 | 6 | +4.015% | 310 / 593 / 593 | 6/6 (100.0%) | 3.77 | 0.113 |
| 2025-12-24 | span | 9,307 | 6 | +5.957% | 337 / 584 / 586 | 6/6 (100.0%) | 6.27 | 0.213 |
| 2026-01-03 | Jan | 9,320 | 8 | +5.678% | 296 / 785 / 787 | 8/8 (100.0%) | 5.95 | 0.224 |
| 2026-01-04 | Jan | 9,318 | 8 | +7.470% | 369 / 787 / 789 | 8/8 (100.0%) | 7.26 | 0.282 |
| 2026-01-06 | Jan | 9,316 | 8 | +4.461% | 317 / 792 / 792 | 8/8 (100.0%) | 7.30 | 0.279 |
| 2026-01-07 | Jan | 9,315 | 6 | +8.214% | 288 / 582 / 589 | 6/6 (100.0%) | 6.61 | 0.251 |
| 2026-01-09 | Jan | 9,344 | 6 | +5.607% | 289 / 586 / 587 | 6/6 (100.0%) | 3.34 | 0.119 |
| 2026-01-19 | Jan | 9,363 | 6 | +3.437% | 311 / 586 / 588 | 6/6 (100.0%) | 2.84 | 0.103 |
| 2026-01-21 | Jan | 9,362 | 6 | +4.748% | 231 / 572 / 586 | 6/6 (100.0%) | 4.67 | 0.168 |
| 2026-01-22 | Jan | 9,391 | 6 | +5.280% | 258 / 591 / 592 | 6/6 (100.0%) | 7.01 | 0.237 |
| 2026-01-24 | Jan | 9,419 | 6 | +3.266% | 294 / 598 / 598 | 6/6 (100.0%) | 6.82 | 0.230 |
| 2026-01-25 | Jan | 9,447 | 6 | +8.899% | 287 / 584 / 589 | 6/6 (100.0%) | 5.61 | 0.207 |
| 2026-02-20 | span | 9,544 | 6 | +6.853% | 396 / 593 / 596 | 6/6 (100.0%) | 3.47 | 0.122 |
| 2026-03-09 | span | 9,792 | 6 | +6.377% | 225 / 594 / 595 | 6/6 (100.0%) | 5.99 | 0.230 |
| 2026-03-27 | span | 9,984 | 6 | +8.868% | 306 / 586 / 593 | 6/6 (100.0%) | 4.58 | 0.169 |
| 2026-04-13 | span | 10,156 | 6 | +4.395% | 233 / 586 / 589 | 6/6 (100.0%) | 3.28 | 0.122 |
| 2026-04-30 | span | 10,283 | 6 | +6.590% | 220 / 574 / 577 | 6/6 (100.0%) | 4.96 | 0.195 |
| 2026-05-16 | span | 10,364 | 6 | +4.236% | 302 / 581 / 583 | 6/6 (100.0%) | 4.32 | 0.157 |
| 2026-06-02 | span | 10,475 | 6 | +4.843% | 262 / 594 / 595 | 6/6 (100.0%) | 4.69 | 0.180 |
| 2026-06-29 | span | 10,667 | 6 | +7.714% | 278 / 597 / 597 | 6/6 (100.0%) | 4.86 | 0.189 |
| 2026-07-17 | span | 10,785 | 6 | +3.205% | 285 / 589 / 590 | 6/6 (100.0%) | 3.51 | 0.128 |
| 2026-08-02 | span | 10,767 | 6 | +7.131% | 285 / 595 / 596 | 6/6 (100.0%) | 7.19 | 0.278 |
| 2026-08-20 | span | 10,746 | 6 | +5.477% | 259 / 588 / 588 | 6/6 (100.0%) | 6.11 | 0.237 |

No date or anchor was removed for a negative endpoint gain, low service count, slow convergence, or failed catalogue improvement. The table therefore keeps the unfavorable committed endpoints visible inside their date pools.

## Interpretation boundaries

UNILATERAL is a deterministic ascending-user cyclic exact single-user best-response run from the carrier anchor. It stops only after a complete pass has no strict improving legal move; there is no deadline. All anchors passed that terminal check. Its endpoint is an **arbitrary path-dependent coordinate-wise local optimum**, not a ceiling and not an upper bound. A qualifying ORACLE_SET result demonstrates only that the selected coordination move was **not reachable by exhaustive single-user best response from the carrier anchor** along this deterministic path.

ORACLE_SET searches the same bounded, hand-built mechanism catalogue used previously: within-beam occupant subsets of sizes 2–4 (1,024-family cap), a victim plus its top-2 or top-3 positive physical-interference contributors, and complete beam evacuations to a common legal destination, under a 4,096-candidate cap. It is perfect-knowledge only within this catalogue. Therefore the observed ORACLE_SET gain is a **lower bound from this catalogue on coordination headroom**, not a general coordination optimum or upper bound.

A qualifying coalition existed on **196/196 anchors (100.0%)**. At the committed 48-boundary endpoint, ORACLE_SET served fewer users than UNILATERAL on **1/196** anchors, the same number on **158/196**, and more on **37/196**. There were **7/196** negative committed ORACLE_SET-over-UNILATERAL gains; they remain in the pools. The selection-time guard is served count >= BASELINE, not >= UNILATERAL, so the served-count columns and this audit are essential when interpreting gains.

This diagnostic is learner-free: no training, learned head, checkpoint, or TEST-partition tape was opened. Consequently the contested train/evaluation date-boundary question does not apply to this measurement. All 30 dates are nevertheless from the TRAIN partition, are distinct, and avoid the archive's 17 missing calendar dates.

## Exact evaluation and provenance

All three arms use the exact evaluator and corrected causal ACM physics from engine source tree `1728f6b0462f86d85618a4c73f4d1dd2d2c07376`, the tree of engine commit `75c5c78c`. The workspace wrapper commit recorded by the receipts is `36ee19b9c918d9ae1881226b14b37fa54279a499`. Selection uses exact binary64 `F = B - eta_ref E` at realised boundary 0 with `eta_ref = 19,720,681.00172232` bit/J and a 30.08 s held snapshot; committed reporting uses the corrected causal realised endpoint at boundary 48.

All **30/30** receipt hashes verified, all **196/196** unilateral endpoints were terminal-certified, every receipt records at most four processes (one coordinator plus three selection workers), and BLAS/OpenMP thread variables were fixed to one. The aggregate JSON is [`.scratch/oracle-ceiling30/ceiling30-aggregate.json`](.scratch/oracle-ceiling30/ceiling30-aggregate.json) with embedded payload SHA-256 `94bf5c1c20e7f8b42da742f8781d62c2b63b148921aaa6f9c9f53a74d62d41ba`; individual signed receipts are in [`.scratch/oracle-ceiling30/results/`](.scratch/oracle-ceiling30/results/). The runner is [`.scratch/oracle-ceiling30/run_oracle_ceiling30.py`](.scratch/oracle-ceiling30/run_oracle_ceiling30.py).

## Compute cost and deviations

The completed 30-date measurement consumed **2.771 sequential wall hours** and **6.168 core-hours** as summed from the date receipts, including **18.85 minutes** of tape construction. Mean cost was **5.54 wall minutes/date** and **0.206 core-hours/date**. At this observed mix, ten additional dates project to about **0.92 wall hours** and **2.06 core-hours**. A fresh 30-date run at 20 anchors/date projects mechanically to about **7.82 wall hours** and **17.40 core-hours**; this is a linear planning extrapolation, not a benchmark guarantee.

The 30-date plan and panel membership were fixed before outcome inspection and never changed. The requested date coverage was achieved, but the observed exact-search tails made roughly 20 anchors/date Rutime? Sorry, must correct. 
The final design has **196 anchors**: 10 on 2025-07-31, eight on the next six completed dates, and six on each remaining 23 dates. This lower and unequal within-date density is the main precision limitation; no completed anchor was discarded and the headline gives equal weight to each date.

The sandboxilho ... Wait must print exact no corruption. I need final carefully. Continue from exact report:
The sandbox returned `EROFS` for `/home/sat/bigtmp`, so tape files could not be serialized there. No tape was written to `/tmp`. Instead, each detached tape was built and held in RAM, shared unchanged across the three arms for one date, released before the next date, and recorded as `NOT_SERIALIZED_SANDBOX_EROFS` in every receipt. This changes persistence/audit convenience, not the evaluated tape or arm comparison. Receipt timing excludes aborted sizing/preflight attempts made before the final anchor allocation was frozen.

## Bottom line

The original +6.359% point estimate is now accompanied by a 30-date distribution: **mean +5.888%, 95% CI [+5.235%, +6.540%]**, with the full-span and single-month panels reported separately above. The result supports catalogue-specific coordination headroom beyond one exact unilateral path; it does not establish a global coordination ceiling.
