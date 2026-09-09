# Interaction label-budget curve — 2026-09-09

**Answer 1 — still climbing at the largest size. The interaction component is data-limited, most clearly for coalitions of size 3 and above.** From the 3,200 point to the full non-held-out training partition, the interaction head's all-size held-out R² rose from -0.116 to 0.147, exact-best selection rose from 42.9% to 47.1%, and mean exact regret fell 15.3%. For size 3+, exact-best selection rose 6.7 percentage points and regret fell 23.4% over the same last segment. This is not a plateau.

`DIAGNOSTIC_NOT_CLAIM`

## Main curve: all coalition sizes

Each nominal point is a whole-anchor sample, so the table gives the actual mean and fold range. “Full” means every non-held-out anchor in each five-fold fit, not leakage of the held-out fold.

| Point: actual train labels (fold range) | Method | Held-out R² | Exact-best | Mean regret | Realised pooled EE (Mbit/J) |
|---|---|---:|---:|---:|---:|
| 180: 202.4 (184–220) | interaction head | -2.235 | 31.5% | 2.815 | 10.2211 |
| 180: 202.4 (184–220) | size-only | -0.040 | 45.0% | 1.549 | 10.3260 |
| 180: 202.4 (184–220) | zero interaction | -0.047 | 46.7% | 1.552 | 10.3178 |
| 400: 415.0 (403–436) | interaction head | -1.336 | 30.7% | 2.951 | 10.2207 |
| 400: 415.0 (403–436) | size-only | -0.010 | 45.6% | 1.534 | 10.3179 |
| 400: 415.0 (403–436) | zero interaction | -0.047 | 46.7% | 1.552 | 10.3178 |
| 800: 813.6 (801–832) | interaction head | -0.936 | 32.2% | 2.743 | 10.2200 |
| 800: 813.6 (801–832) | size-only | -0.010 | 45.0% | 1.597 | 10.3150 |
| 800: 813.6 (801–832) | zero interaction | -0.047 | 46.7% | 1.552 | 10.3178 |
| 1,600: 1,649.8 (1,632–1,668) | interaction head | -0.338 | 39.4% | 2.188 | 10.2863 |
| 1,600: 1,649.8 (1,632–1,668) | size-only | 0.001 | 47.2% | 1.527 | 10.3174 |
| 1,600: 1,649.8 (1,632–1,668) | zero interaction | -0.047 | 46.7% | 1.552 | 10.3178 |
| 3,200: 3,221.2 (3,217–3,226) | interaction head | -0.116 | 42.9% | 2.095 | 10.2825 |
| 3,200: 3,221.2 (3,217–3,226) | size-only | 0.004 | 46.7% | 1.548 | 10.3154 |
| 3,200: 3,221.2 (3,217–3,226) | zero interaction | -0.047 | 46.7% | 1.552 | 10.3178 |
| full: 6,764.8 (6,429–6,924) | interaction head | 0.147 | 47.1% | 1.775 | 10.3098 |
| full: 6,764.8 (6,429–6,924) | size-only | 0.005 | 47.2% | 1.527 | 10.3174 |
| full: 6,764.8 (6,429–6,924) | zero interaction | -0.047 | 46.7% | 1.552 | 10.3178 |

The learned curve is moving in the right direction, but the current head is not yet decision-useful against the trivial controls. At full size it essentially ties their exact-best rate, has 14.4% more mean regret than zero interaction, and has 0.0778% lower realised pooled EE. It also has 0.0741% lower EE than size-only. Thus the data-starvation hypothesis is supported as a diagnosis of continued improvement, but labels alone are not yet shown to solve the coordinator's selection problem.

## Split curve: coalition size 2

The same mixed-size head is evaluated only among held-out size-2 candidates (plus no-change). This isolates pair selection without changing training.

| Point: actual train labels (fold range) | Method | Held-out R² | Exact-best | Mean regret | Realised pooled EE (Mbit/J) |
|---|---|---:|---:|---:|---:|
| 180: 202.4 (184–220) | interaction head | -1.532 | 35.8% | 2.285 | 10.1728 |
| 180: 202.4 (184–220) | size-only | -0.001 | 53.3% | 1.263 | 10.2480 |
| 180: 202.4 (184–220) | zero interaction | -0.026 | 53.3% | 1.263 | 10.2480 |
| 400: 415.0 (403–436) | interaction head | -1.164 | 37.4% | 2.347 | 10.1818 |
| 400: 415.0 (403–436) | size-only | -0.004 | 53.3% | 1.263 | 10.2480 |
| 400: 415.0 (403–436) | zero interaction | -0.026 | 53.3% | 1.263 | 10.2480 |
| 800: 813.6 (801–832) | interaction head | -0.624 | 40.4% | 1.991 | 10.1935 |
| 800: 813.6 (801–832) | size-only | -0.004 | 53.3% | 1.263 | 10.2480 |
| 800: 813.6 (801–832) | zero interaction | -0.026 | 53.3% | 1.263 | 10.2480 |
| 1,600: 1,649.8 (1,632–1,668) | interaction head | -0.195 | 43.5% | 1.712 | 10.2266 |
| 1,600: 1,649.8 (1,632–1,668) | size-only | -0.006 | 53.3% | 1.263 | 10.2480 |
| 1,600: 1,649.8 (1,632–1,668) | zero interaction | -0.026 | 53.3% | 1.263 | 10.2480 |
| 3,200: 3,221.2 (3,217–3,226) | interaction head | 0.075 | 48.5% | 1.499 | 10.2489 |
| 3,200: 3,221.2 (3,217–3,226) | size-only | -0.002 | 53.3% | 1.263 | 10.2480 |
| 3,200: 3,221.2 (3,217–3,226) | zero interaction | -0.026 | 53.3% | 1.263 | 10.2480 |
| full: 6,764.8 (6,429–6,924) | interaction head | 0.209 | 49.4% | 1.397 | 10.2463 |
| full: 6,764.8 (6,429–6,924) | size-only | -0.003 | 53.3% | 1.263 | 10.2480 |
| full: 6,764.8 (6,429–6,924) | zero interaction | -0.026 | 53.3% | 1.263 | 10.2480 |

Pairs are closer to flattening, but they have not met a saturation test: on the last segment R² rose by 0.135 and regret fell 6.8%, although exact-best selection moved only 1.0 point. The learned head still trails both trivial baselines on pair selection and regret.

## Split curve: coalition size 3 and above

The same mixed-size head is evaluated only among held-out size-3+ candidates (plus no-change).

| Point: actual train labels (fold range) | Method | Held-out R² | Exact-best | Mean regret | Realised pooled EE (Mbit/J) |
|---|---|---:|---:|---:|---:|
| 180: 202.4 (184–220) | interaction head | -4.209 | 41.5% | 2.206 | 10.0120 |
| 180: 202.4 (184–220) | size-only | -0.207 | 51.7% | 1.008 | 10.1356 |
| 180: 202.4 (184–220) | zero interaction | -0.169 | 53.9% | 0.950 | 10.1299 |
| 400: 415.0 (403–436) | interaction head | -1.924 | 41.9% | 1.857 | 10.0613 |
| 400: 415.0 (403–436) | size-only | -0.094 | 52.8% | 1.041 | 10.1317 |
| 400: 415.0 (403–436) | zero interaction | -0.169 | 53.9% | 0.950 | 10.1299 |
| 800: 813.6 (801–832) | interaction head | -1.843 | 41.7% | 1.796 | 10.0637 |
| 800: 813.6 (801–832) | size-only | -0.093 | 51.7% | 1.066 | 10.1322 |
| 800: 813.6 (801–832) | zero interaction | -0.169 | 53.9% | 0.950 | 10.1299 |
| 1,600: 1,649.8 (1,632–1,668) | interaction head | -0.782 | 47.9% | 1.394 | 10.0917 |
| 1,600: 1,649.8 (1,632–1,668) | size-only | -0.050 | 55.6% | 0.951 | 10.1404 |
| 1,600: 1,649.8 (1,632–1,668) | zero interaction | -0.169 | 53.9% | 0.950 | 10.1299 |
| 3,200: 3,221.2 (3,217–3,226) | interaction head | -0.668 | 50.3% | 1.382 | 10.0844 |
| 3,200: 3,221.2 (3,217–3,226) | size-only | -0.048 | 52.2% | 1.077 | 10.1308 |
| 3,200: 3,221.2 (3,217–3,226) | zero interaction | -0.169 | 53.9% | 0.950 | 10.1299 |
| full: 6,764.8 (6,429–6,924) | interaction head | -0.066 | 56.9% | 1.058 | 10.1269 |
| full: 6,764.8 (6,429–6,924) | size-only | -0.042 | 55.6% | 0.935 | 10.1412 |
| full: 6,764.8 (6,429–6,924) | zero interaction | -0.169 | 53.9% | 0.950 | 10.1299 |

The shortage is located most sharply at size 3+. Over the last segment, R² improved by 0.602, exact-best selection improved 6.7 points, regret fell 23.4%, and pooled EE rose 0.422%. The learned head finally beats both baselines on exact-best frequency, but it still loses on regret and realised EE. Its rare wrong choices are more costly than the baselines' wrong choices.

## Rough label target and compute budget

For a concrete target, use **60% held-out exact-best selection over all candidate sizes**. A straight line fitted to exact-best percentage versus log2(training labels) over the last three points gives 3.75 percentage points per doubling and reaches 60% at about **74,000 training labels per fold**. Under the same 80/20 five-fold geometry, that corresponds to about **93,000 total corpus labels**. Using the last four points instead gives about 41,000 training labels, or 51,000 corpus labels. Therefore the honest rough target is **51,000–93,000 total labels; budget against 93,000**. This is a 6–11× extrapolation beyond the observed 8,456-row corpus, so it is a planning estimate, not a measured guarantee.

The size-3+ last-segment trend reaches 60% exact-best at roughly 11,000–12,000 training labels, corresponding to about **14,000–15,000 total labels** at the current size mix. The pair curve extrapolates much farther, roughly **71,000–90,000 total labels**, but pair selection already trails a 53.3% trivial baseline and its last-step exact-best gain is small. A sensible next corpus tranche should therefore enrich size 3+ first and remeasure before purchasing the full 93,000-label upper budget.

The corpus generator measured 637.880 s for 28,011 physical configuration evaluations and 8,456 delivered coalition rows:

| Cost view | Wall time | Physics calls per new label |
|---|---:|---:|
| Incremental label, anchor baseline and required singleton values cached | **0.0228 s/label** (measured mean call time) | **1** |
| Gross completed corpus job, including cache construction and the R3 pair audit | 0.0754 s/delivered row | 3.313 |

Growing from 8,456 to the conservative 93,000-label corpus target would add about **84,500 labels**, **84,500 physics calls**, and **32 minutes** at the measured incremental rate, provided baseline and singleton values really are retained per anchor. The 51,000-label lower sensitivity estimate would add about 42,500 labels and take about 16 minutes. Cache construction, serialization, and any changed anchor mix are outside those incremental estimates.

## Measurement protocol

- Corpus: 8,456 exact interaction rows over 180 anchors; size histogram 2: 6,856, 3: 1,288, 4: 270, 5: 36, 6: 6.
- Fold assignment: SHA-256 of the anchor identity, sorted and assigned round-robin to five fixed folds; 36 held-out anchors per fold. No held-out anchor contributes any training row.
- Nested sampling: SHA-256 deterministic anchor order inside each training partition; complete anchors are added until each label target is met.
- Learner: the existing 240-feature permutation-invariant C3 encoding, 64×64 ReLU head, learning rate 0.001, Adam (0.9, 0.999), epsilon 1e-8, and exactly 2,000 full-batch updates. The four existing learner seeds are used. No threshold, sign, seed, horizon, price, service guard, or acceptance rule changed.
- Fit metric: out-of-fold R² against exact `psi_normalized`; the table reports the mean over the four learner seeds.
- Selection metric: exact additive C1 plus predicted interaction. The exact oracle uses exact C1 plus exact interaction. No-change is present in every candidate set at score and delta zero. Ties use deterministic configuration identity. Mean regret is in kappa-normalized exact-objective units.
- Size-only baseline: out-of-fold ordinary least squares `psi ~ intercept + coalition_size` on the identical whole-anchor training subset. Zero interaction uses `psi_hat = 0`.
- Outcome: selected configurations were re-evaluated with the unchanged 48-boundary realised `StepEvaluator`; pooled EE is `sum(bits) / sum(joules)`. Across deduplicated selected configurations this required 75,168 realised boundary evaluations. The full diagnostic took 1,513.7 s wall time.

![Learning curve](artifacts/label-budget-curve-20260909-DIAGNOSTIC_NOT_CLAIM.png)

Machine-readable results: `artifacts/label-budget-curve-20260909-DIAGNOSTIC_NOT_CLAIM.json` (SHA-256 `abef7c55abffd9a25f1fe29e15fe2362d5552d3e508f72ffb7df2040533ae6c6`). Figure SHA-256: `c8a03671b11fa3db3dcf045c39e8203194334803cf9d87e2b9f8fa226b1cdc75`.

## Workspace provenance limitation

The source corpus report and manifest in `/home/sat/mcrl-v025-coalgen-ws` were byte-identical to the copies used here, and the requested `cp -a` was attempted without writing to the source. This managed sandbox exposes this workspace's `.git` as read-only, so it refused the requested removal, reinitialization, and commit. The measurement artifacts and this report are in the requested curve workspace, but a fresh Git commit could not be produced under the available permissions.
