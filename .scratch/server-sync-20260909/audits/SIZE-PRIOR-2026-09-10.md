**LEARNED_PSI beats SIZE_PRIOR on held-out mean selection regret: 3.618038 vs 13.113764; signed margin LEARNED_PSI − SIZE_PRIOR = -9.495726 normalized objective units.**

# Size-prior comparator — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`

No production training run, policy run, or acceptance test was performed. This is an offline fit on copies for measurement only. No sealed contract, target, scorer, schema digest, manifest, constant, threshold, sign, seed, horizon, price, service guard, or acceptance rule was modified.

## Direct answer

The learned interaction head's gain over the size prior is +9.495726 (`SIZE_PRIOR − LEARNED_PSI`). The size prior's gain over zero is -0.569283 (`ZERO_PSI − SIZE_PRIOR`). The learned-head gain is **larger** than the size-prior-versus-zero gain. In the requested signed left-minus-right convention, `LEARNED_PSI − SIZE_PRIOR` is -9.495726, and `SIZE_PRIOR − ZERO_PSI` is +0.569283; negative means the left scorer has lower regret.

## Frozen protocol and fitted size prior

The comparator reuses the exact-label loaders, frozen three-anchor-block split, seed `20260910`, Q1 feature construction, fixed-ReLU random-feature ridge family, grid choices, final train+validation refit, selection pools, and configuration-ID tie-break from `scripts/compare_target_parametrisations.py`. Neither scorer was tuned here: the learned heads use the already frozen hyperparameters, while the size prior is a single categorical least-squares fit to the exact interaction label on the same 8,231 final fitting rows.

For a one-hot categorical size design, least squares sets each coefficient to that size's training-label mean. It sees only the integer coalition size; there is no interpolation, regularization, set context, member identity, or other feature.

| coalition size | fit rows | fitted interaction prior |
|---|---|---|
| 2 | 4628 | 0.347744 |
| 3 | 3155 | 0.218414 |
| 4 | 180 | 0.327740 |
| 5 | 24 | -0.170625 |
| 6 | 4 | -0.307387 |
| 100 | 240 | -12.402189 |

## Held-out selection regret

| scorer | mean | median | p95 | choice differs | selection sizes |
|---|---|---|---|---|---|
| LEARNED_PSI | 3.618038 | 0.000000 | 19.824570 | 23.33% | `{'100': 28, '3': 2}` |
| SIZE_PRIOR | 13.113764 | 0.000000 | 61.897974 | 43.33% | `{'100': 27, '2': 1, '4': 2}` |
| ZERO_PSI | 12.544480 | 0.000000 | 61.897974 | 40.00% | `{'100': 28, '4': 2}` |
| EXACT_PSI | 9.647125 | 0.000000 | 42.838154 | 43.33% | `{'100': 28, '2': 1, '4': 1}` |

Exact-winner size distribution: `{'100': 26, '2': 1, '3': 3}`.

### Selection regret by selected coalition size

| scorer | selected k | n | mean | median | p95 | differs |
|---|---|---|---|---|---|---|
| LEARNED_PSI | 3 | 2 | 4.598220 | 4.598220 | 8.736618 | 50.00% |
| LEARNED_PSI | 100 | 28 | 3.548025 | 0.000000 | 20.541614 | 21.43% |
| SIZE_PRIOR | 2 | 1 | 17.078504 | 17.078504 | 17.078504 | 100.00% |
| SIZE_PRIOR | 4 | 2 | 64.586440 | 64.586440 | 67.514093 | 100.00% |
| SIZE_PRIOR | 100 | 27 | 9.154131 | 0.000000 | 44.001045 | 37.04% |
| ZERO_PSI | 4 | 2 | 64.586440 | 64.586440 | 67.514093 | 100.00% |
| ZERO_PSI | 100 | 28 | 8.827197 | 0.000000 | 43.863608 | 35.71% |
| EXACT_PSI | 2 | 1 | 16.623675 | 16.623675 | 16.623675 | 100.00% |
| EXACT_PSI | 4 | 1 | 69.030189 | 69.030189 | 69.030189 | 100.00% |
| EXACT_PSI | 100 | 28 | 7.277138 | 0.000000 | 37.051260 | 39.29% |

## Held-out value error

| scorer | explained variance | RMSE |
|---|---|---|
| LEARNED_PSI | 0.653592 | 7.490230 |
| SIZE_PRIOR | -0.316743 | 14.646651 |
| ZERO_PSI | -0.452560 | 15.384872 |
| EXACT_PSI | 0.089163 | 12.184264 |

## LEARNED_PSI versus SIZE_PRIOR

They commit the same configuration on 22 of 30 held-out anchors (73.33%). Score differences below are `LEARNED_PSI − SIZE_PRIOR` over all held-out rows, as fixed before fitting.

| n | mean | population SD | min | p05 | median | p95 | max |
|---|---|---|---|---|---|---|---|
| 2022 | -0.967000 | 11.878455 | -136.519910 | -5.003828 | -0.380579 | 3.079218 | 152.504841 |

### Where their selections disagree

Each objective below is the exact normalized joint objective change of that scorer's selected configuration. `higher exact choice` is based only on those two committed configurations; `TIE` means their different configurations have equal exact objective.

| world | anchor | learned k | learned exact objective | size-prior k | size-prior exact objective | higher exact choice |
|---|---|---|---|---|---|---|
| V025_PROBE/world/1 | 8 | 3 | 6.462274 | 100 | -10.169502 | LEARNED_PSI |
| V025_PROBE/world/1 | 65 | 100 | 5.993018 | 100 | 0.555357 | LEARNED_PSI |
| V025_PROBE/world/2 | 55 | 100 | 40.774641 | 100 | 28.660431 | LEARNED_PSI |
| V025_PROBE/world/2 | 57 | 100 | 73.611904 | 4 | 12.278412 | LEARNED_PSI |
| V025_PROBE/world/2 | 67 | 100 | 113.070305 | 100 | 70.993382 | LEARNED_PSI |
| V025_PROBE/world/2 | 69 | 100 | 25.252309 | 2 | 8.173805 | LEARNED_PSI |
| V025_PROBE/world/2 | 70 | 100 | 69.923755 | 4 | 2.084367 | LEARNED_PSI |
| V025_PROBE/world/2 | 71 | 3 | 13.209326 | 100 | -49.150496 | LEARNED_PSI |

## Exact-label and reuse checks

The source exact-label audit checked 11924 mechanism rows against Fraction receipts with maximum encoded residual 0.000e+00; all 300 local size-100 rows were loaded through the prior harness's exact receipt checks. Source shards supplied features only; the pilot fallback labels were never read as targets. The family-index SHA-256 is `b8f55dc15e91155a32aa706a4908aff3bf6ee281565f9ca0644d76679e7da047`.

The recomputed `LEARNED_PSI` selection mean, median, p95, mismatch fraction, explained variance, and RMSE reproduce the frozen comparison's `ADDITIVE` values within `1e-12`, and its selection-size histogram matches exactly.

## What this did not reach

This is not a production training run, policy run, or acceptance test, and it does not estimate downstream policy value or establish that any route individually raises pooled energy efficiency. It tests only whether the learned interaction head improves held-out selection within the available exact-labelled pools relative to a fitted size-only correction. Those pools are catalogue/mechanism candidates, not the full combinatorial action space. The mechanism corpus has no per-row served-count receipt, so this does not stratify by that sealed guard. Sizes 7–99 are absent, so the size-only curve is observed only at 2–6 and 100. No confidence interval or repeated-seed result was reached because the experiment fixes one split and seed and forbids adding metrics after seeing results.

## Reproduction

```bash
cd /home/sat/mcrl-v025-selector-ws
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_size_prior.py
```

Machine-readable output: `.scratch/parametrisation-comparison/size-prior-results.json`.
