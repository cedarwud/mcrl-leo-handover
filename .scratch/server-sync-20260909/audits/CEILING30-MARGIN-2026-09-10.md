Corrected mean gain **+0.717%**, 95% CI **[+0.436%, +0.997%]**, with **4 negative dates**. The corrected gap is small and its interval includes practically immaterial values.

`DIAGNOSTIC_NOT_CLAIM`

This is a separate diagnostic evaluation on copied code. No sealed constant, source artefact, frozen manifest, sign, seed, horizon, price, service guard, cap, catalogue rule, or acceptance rule was changed. There was no training run, learner, or policy run.

## Direct answers

1. **No.** The corrected coordination gap is positive on **26/30** dates and negative on **4/30**. The negative dates are 2026-01-06 (-0.075%), 2026-01-19 (-0.070%), 2026-03-09 (-0.265%), 2026-04-30 (-0.230%).

2. The date-level mean corrected gain is **+0.717%** with sample SD **0.751%** and a two-sided 95% Student-t interval **[+0.436%, +0.997%]**. The minimum is **-0.265%** on 2026-03-09; the maximum is **+3.246%** on 2025-09-03.

3. **Yes: 4 dates change from favourable under the sealed rule to non-positive under `MARGIN_Q`.** Spearman rank correlation between the two sets of 30 per-date gains is **ρ=+0.006**. This reports ordering, not agreement in magnitude.

## Compatibility gate before the panel

Before any corrected date was run, the copied evaluator was compiled with its provisioning divisor set to one and three complete six-anchor dates were rerun. Every deterministic receipt field was canonical-JSON bit-identical to its existing sealed counterpart:

| Date | Anchors | Sealed/control deterministic SHA-256 | Bit-identical |
|---|---:|---|:---:|
| 2025-11-04 | 6 | `6e24568e1932a77f2c2e7f29243601d89b83e319759b519519e67cac819b469b` | yes |
| 2026-01-19 | 6 | `e9de4000373fb8bcb0da83f1e534d47440da64346c4ceb02ff8a084636cde37a` | yes |
| 2026-07-17 | 6 | `c6ccc437b244cbd0cd218530e547d7233018f498733df0b7ad125196b7364f48` | yes |

The compared payload includes world identity, seed, epoch, search paths and counts, terminal certificates, configuration IDs, committed bits/joules/served counts, and summaries. Only elapsed wall/CPU timing, per-anchor wall time, and the outer receipt hash covering those nondeterministic timing fields were excluded. The compatibility receipt is `.scratch/oracle-ceiling30-margin/divisor-one-receipt-compatibility.json`.

## Date-level paired result

Each date first pools bits and joules over its unchanged anchor set, computes each arm's pooled bit/J, and then forms `ORACLE_SET / UNILATERAL - 1`. Dates—not anchors, users, boundaries, or transmission attempts—are the 30 independent units for the mean and interval.

| Rule | Dates | Mean | Sample SD | Two-sided 95% t interval | Negative | Minimum | Maximum |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sealed | 30 | +5.888% | 1.747% | [+5.235%, +6.540%] | 0 | +3.205% (2026-07-17) | +9.652% (2025-09-30) |
| `MARGIN_Q` | 30 | +0.717% | 0.751% | [+0.436%, +0.997%] | 4 | -0.265% (2026-03-09) | +3.246% (2025-09-03) |
| Paired difference (`MARGIN_Q` − sealed) | 30 | -5.171% | 1.894% | [-5.878%, -4.464%] | 30 | -8.840% (2025-09-30) | -2.248% (2026-01-24) |

| Date | Anchors | Sealed gain | `MARGIN_Q` gain | Paired difference | Sealed served B/U/O | `MARGIN_Q` served B/U/O | Sealed target-attained B/U/O | `MARGIN_Q` target-attained B/U/O |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-07-31 | 10 | +5.481% | +0.320% | -5.161% | 425 / 983 / 983 | 614 / 1,000 / 1,000 | 0 / 0 / 0 | 242 / 719 / 712 |
| 2025-08-18 | 8 | +7.685% | +0.597% | -7.088% | 327 / 768 / 780 | 472 / 800 / 800 | 0 / 0 / 0 | 186 / 544 / 545 |
| 2025-09-03 | 8 | +6.023% | +3.246% | -2.777% | 406 / 790 / 791 | 495 / 800 / 800 | 0 / 0 / 0 | 131 / 556 / 572 |
| 2025-09-30 | 8 | +9.652% | +0.813% | -8.840% | 384 / 741 / 755 | 519 / 800 / 800 | 0 / 0 / 0 | 165 / 497 / 505 |
| 2025-10-17 | 6 | +6.238% | +1.435% | -4.802% | 256 / 588 / 591 | 374 / 600 / 600 | 0 / 0 / 0 | 131 / 431 / 422 |
| 2025-11-04 | 6 | +4.856% | +0.422% | -4.434% | 253 / 597 / 598 | 404 / 600 / 600 | 0 / 0 / 0 | 146 / 448 / 446 |
| 2025-11-20 | 6 | +3.973% | +0.761% | -3.212% | 228 / 593 / 593 | 375 / 600 / 600 | 0 / 0 / 0 | 164 / 423 / 428 |
| 2025-12-07 | 6 | +4.015% | +0.330% | -3.685% | 310 / 593 / 593 | 414 / 600 / 600 | 0 / 0 / 0 | 163 / 418 / 415 |
| 2025-12-24 | 6 | +5.957% | +0.557% | -5.401% | 337 / 584 / 586 | 401 / 600 / 600 | 0 / 0 / 0 | 136 / 436 / 436 |
| 2026-01-03 | 8 | +5.678% | +0.251% | -5.428% | 296 / 785 / 787 | 426 / 800 / 800 | 0 / 0 / 0 | 140 / 575 / 575 |
| 2026-01-04 | 8 | +7.470% | +0.972% | -6.497% | 369 / 787 / 789 | 456 / 800 / 800 | 0 / 0 / 0 | 155 / 592 / 592 |
| 2026-01-06 | 8 | +4.461% | -0.075% | -4.535% | 317 / 792 / 792 | 453 / 800 / 800 | 0 / 0 / 0 | 175 / 595 / 587 |
| 2026-01-07 | 6 | +8.214% | +0.586% | -7.628% | 288 / 582 / 589 | 371 / 600 / 600 | 0 / 0 / 0 | 103 / 389 / 380 |
| 2026-01-09 | 6 | +5.607% | +0.275% | -5.333% | 289 / 586 / 587 | 340 / 600 / 600 | 0 / 0 / 0 | 122 / 389 / 382 |
| 2026-01-19 | 6 | +3.437% | -0.070% | -3.506% | 311 / 586 / 588 | 448 / 600 / 600 | 0 / 0 / 0 | 179 / 430 / 425 |
| 2026-01-21 | 6 | +4.748% | +2.092% | -2.656% | 231 / 572 / 586 | 359 / 600 / 600 | 0 / 0 / 0 | 123 / 440 / 442 |
| 2026-01-22 | 6 | +5.280% | +0.006% | -5.274% | 258 / 591 / 592 | 380 / 600 / 600 | 0 / 0 / 0 | 132 / 420 / 422 |
| 2026-01-24 | 6 | +3.266% | +1.017% | -2.248% | 294 / 598 / 598 | 446 / 600 / 600 | 0 / 0 / 0 | 206 / 396 / 398 |
| 2026-01-25 | 6 | +8.899% | +0.355% | -8.544% | 287 / 584 / 589 | 389 / 600 / 600 | 0 / 0 / 0 | 141 / 385 / 382 |
| 2026-02-20 | 6 | +6.853% | +2.232% | -4.621% | 396 / 593 / 596 | 464 / 600 / 600 | 0 / 0 / 0 | 133 / 400 / 401 |
| 2026-03-09 | 6 | +6.377% | -0.265% | -6.642% | 225 / 594 / 595 | 402 / 600 / 600 | 0 / 0 / 0 | 158 / 406 / 405 |
| 2026-03-27 | 6 | +8.868% | +0.493% | -8.375% | 306 / 586 / 593 | 377 / 600 / 600 | 0 / 0 / 0 | 110 / 402 / 403 |
| 2026-04-13 | 6 | +4.395% | +0.893% | -3.502% | 233 / 586 / 589 | 311 / 600 / 600 | 0 / 0 / 0 | 93 / 419 / 422 |
| 2026-04-30 | 6 | +6.590% | -0.230% | -6.821% | 220 / 574 / 577 | 308 / 600 / 600 | 0 / 0 / 0 | 78 / 419 / 414 |
| 2026-05-16 | 6 | +4.236% | +0.526% | -3.710% | 302 / 581 / 583 | 406 / 600 / 600 | 0 / 0 / 0 | 158 / 422 / 418 |
| 2026-06-02 | 6 | +4.843% | +1.224% | -3.619% | 262 / 594 / 595 | 356 / 600 / 600 | 0 / 0 / 0 | 121 / 424 / 417 |
| 2026-06-29 | 6 | +7.714% | +0.478% | -7.236% | 278 / 597 / 597 | 387 / 600 / 600 | 0 / 0 / 0 | 142 / 423 / 416 |
| 2026-07-17 | 6 | +3.205% | +0.807% | -2.398% | 285 / 589 / 590 | 398 / 600 / 600 | 0 / 0 / 0 | 137 / 408 / 405 |
| 2026-08-02 | 6 | +7.131% | +0.567% | -6.563% | 285 / 595 / 596 | 410 / 600 / 600 | 0 / 0 / 0 | 135 / 409 / 411 |
| 2026-08-20 | 6 | +5.477% | +0.889% | -4.588% | 259 / 588 / 588 | 351 / 600 / 600 | 0 / 0 / 0 | 139 / 427 / 425 |

`B/U/O` means BASELINE / UNILATERAL / ORACLE_SET. Served means at least some successful decoding in the endpoint; rate-target-attained means the user's integrated bits meet the unchanged per-user target. They are distinct and are not merged.

## Service and boundary-attempt diagnostics

The unit below is one active transmission in one native TDM slot at one evaluated boundary. Because a boundary can contain multiple slots and users, these are transmission-boundary-attempt shares, not a claim that the events are independent. `NO_MODE` means no eligible transmitted ACM mode; cap binding means RF power is within 1e-9 W of the unchanged per-beam cap.

| Rule | Arm | Served / 19,600 | Rate target attained / 19,600 | Cap binds / attempts (share) | `NO_MODE` / attempts (share) |
|---|---|---:|---:|---:|---:|
| SEALED | BASELINE | 8,917 / 19,600 | 0 / 19,600 | 4,626,307 / 11,574,240 (39.97%) | 8,967,026 / 11,574,240 (77.47%) |
| SEALED | UNILATERAL | 19,177 / 19,600 | 0 / 19,600 | 817,609 / 6,015,360 (13.59%) | 552,105 / 6,015,360 (9.18%) |
| SEALED | ORACLE_SET | 19,266 / 19,600 | 0 / 19,600 | 707,463 / 5,927,936 (11.93%) | 471,817 / 5,927,936 (7.96%) |
| MARGIN_Q | BASELINE | 12,306 / 19,600 | 4,344 / 19,600 | 3,288,599 / 5,849,664 (56.22%) | 2,675,847 / 5,849,664 (45.74%) |
| MARGIN_Q | UNILATERAL | 19,600 / 19,600 | 13,642 / 19,600 | 59,162 / 7,206,096 (0.82%) | 11,381 / 7,206,096 (0.16%) |
| MARGIN_Q | ORACLE_SET | 19,600 / 19,600 | 13,603 / 19,600 | 53,698 / 7,203,414 (0.75%) | 10,206 / 7,203,414 (0.14%) |

Per-date corrected attempt shares:

| Date | Cap-binding share B/U/O | `NO_MODE` share B/U/O |
|---|---:|---:|
| 2025-07-31 | 59.56% / 0.88% / 0.81% | 49.20% / 0.08% / 0.09% |
| 2025-08-18 | 59.63% / 0.75% / 0.78% | 50.64% / 0.18% / 0.20% |
| 2025-09-03 | 63.85% / 1.47% / 0.87% | 53.28% / 0.33% / 0.14% |
| 2025-09-30 | 53.95% / 0.84% / 0.78% | 41.04% / 0.03% / 0.06% |
| 2025-10-17 | 57.48% / 0.54% / 0.40% | 46.29% / 0.00% / 0.01% |
| 2025-11-04 | 49.80% / 0.29% / 0.31% | 38.05% / 0.07% / 0.08% |
| 2025-11-20 | 47.04% / 0.78% / 0.67% | 39.27% / 0.26% / 0.25% |
| 2025-12-07 | 50.03% / 0.57% / 0.58% | 39.60% / 0.07% / 0.05% |
| 2025-12-24 | 54.57% / 0.68% / 0.59% | 44.39% / 0.02% / 0.03% |
| 2026-01-03 | 59.76% / 1.27% / 1.31% | 51.52% / 0.48% / 0.50% |
| 2026-01-04 | 66.72% / 1.15% / 0.96% | 55.75% / 0.15% / 0.13% |
| 2026-01-06 | 60.12% / 1.28% / 1.29% | 50.90% / 0.11% / 0.13% |
| 2026-01-07 | 57.40% / 1.16% / 1.15% | 44.76% / 0.02% / 0.02% |
| 2026-01-09 | 59.35% / 1.57% / 1.36% | 49.52% / 0.26% / 0.25% |
| 2026-01-19 | 46.09% / 0.74% / 0.86% | 35.22% / 0.20% / 0.15% |
| 2026-01-21 | 57.50% / 0.71% / 0.49% | 49.11% / 0.24% / 0.07% |
| 2026-01-22 | 61.25% / 0.94% / 0.97% | 50.01% / 0.09% / 0.14% |
| 2026-01-24 | 44.11% / 0.32% / 0.24% | 34.07% / 0.09% / 0.03% |
| 2026-01-25 | 55.92% / 0.92% / 0.92% | 44.78% / 0.15% / 0.16% |
| 2026-02-20 | 53.88% / 1.32% / 0.71% | 38.18% / 0.33% / 0.12% |
| 2026-03-09 | 48.05% / 0.52% / 0.68% | 40.07% / 0.09% / 0.09% |
| 2026-03-27 | 60.80% / 0.48% / 0.46% | 49.89% / 0.09% / 0.09% |
| 2026-04-13 | 66.84% / 0.39% / 0.28% | 57.56% / 0.20% / 0.21% |
| 2026-04-30 | 69.30% / 1.01% / 0.99% | 59.78% / 0.13% / 0.15% |
| 2026-05-16 | 48.62% / 0.89% / 0.81% | 39.16% / 0.26% / 0.27% |
| 2026-06-02 | 61.34% / 0.72% / 0.58% | 50.90% / 0.37% / 0.39% |
| 2026-06-29 | 56.11% / 0.37% / 0.39% | 46.33% / 0.07% / 0.09% |
| 2026-07-17 | 58.38% / 1.21% / 1.16% | 47.78% / 0.15% / 0.16% |
| 2026-08-02 | 53.13% / 0.74% / 0.75% | 39.19% / 0.10% / 0.11% |
| 2026-08-20 | 60.76% / 0.46% / 0.38% | 51.88% / 0.24% / 0.18% |

## Scope, integrity, and reproduction

All **30/30** corrected receipt hashes verified; all **196/196** unilateral endpoints carry the same terminal no-strict-improvement certificate. The panel retains exactly **196 anchors**: the existing 10/8/6 per-date allocation was copied from the sealed receipts, so no anchor or date was cut. Every corrected receipt matches its sealed pair on world hash, training seed, epoch, date, and anchor count.

The corrected evaluator is an in-memory private copy of the sealed dense core. It checks that exactly one source expression is replaced and changes only `targets = gamma[...]` to `targets = gamma[...] / quantile`. The quantile alpha remains 0.10 and the existing quantile is still used later for mode selection. The runner additionally replays the three committed sealed configurations on the same tape solely to report the otherwise absent served/target/cap/`NO_MODE` diagnostics; these replays do not participate in selection.

Exact commands (from the workspace root, with the specified interpreter and niceness):

```bash
env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/oracle-ceiling30-margin/audit_variant.py
nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/oracle-ceiling30-margin/run_dates.py --formulation divisor-one --dates 2025-11-04 2026-01-19 2026-07-17
env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/oracle-ceiling30-margin/verify_receipt_compatibility.py
nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/oracle-ceiling30-margin/run_dates.py --formulation margin-q
env PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/oracle-ceiling30-margin/report_margin_ceiling30.py
```

Completed receipts are refuse-to-overwrite and live under `.scratch/oracle-ceiling30-margin/results/`; compatibility controls are separately under `.scratch/oracle-ceiling30-margin/compat-divisor-one/`. The paired aggregate is `.scratch/oracle-ceiling30-margin/ceiling30-margin-aggregate.json` with payload SHA-256 `c55bc29ae176c84b2a1bdee3ef657d3423ea9c37d3f469a3ed12ddd969821772`.

## Interpretation

This result compares two provisioning formulations; it does not rank or recommend either one. `UNILATERAL` remains a deterministic path-dependent coordinate-wise optimum, not a global optimum. `ORACLE_SET` remains the best exact-objective result only within the unchanged bounded hand-built catalogue, so its gain is catalogue-specific coordination headroom rather than a global coordination ceiling.

The interval is descriptive over these 30 fixed TRAIN dates, with date as the independent unit. No date or anchor was selected, removed, or reweighted based on its outcome.
