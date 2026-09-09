# Architecture alternatives — 2026-09-09

`DIAGNOSTIC_NOT_CLAIM`

## Selection quality

| Model | Anchors | Realised pooled EE (bit/J) | Mean regret | p95 regret | Exact best | Exact top 3 | Selected sizes |
|---|---:|---:|---:|---:|---:|---:|---|
| pairwise baseline | 180 | 1.09397e+07 | 7.0028 | 17.7150 | 9.4% | 15.6% | 2:110, 3:57, 4:11, 5:1, 6:1 |
| resource anchored | 180 | 1.11217e+07 | 5.6821 | 16.9471 | 14.4% | 23.9% | 2:40, 3:115, 4:23, 5:1, 6:1 |
| same-anchor ranker | 180 | 1.11542e+07 | 5.2535 | 17.7352 | 13.9% | 33.3% | 2:66, 3:86, 4:26, 5:1, 6:1 |

Regret is the anchor-local exact nominal score gap to the best candidate in the same panel, in the corpus's normalized units. Realised pooled EE is the ratio of summed realised bits to summed realised joules after replaying each selected configuration through the unchanged keyed-fading evaluator. The selected-size entries are `coalition size:anchor count`.

## Material-|R3| population

| Model | Anchors | Realised pooled EE (bit/J) | Mean regret | p95 regret | Exact best | Exact top 3 | Selected sizes |
|---|---:|---:|---:|---:|---:|---:|---|
| pairwise baseline | 180 | 1.08844e+07 | 4.7372 | 16.9872 | 19.4% | 51.1% | 3:152, 4:27, 5:1 |
| resource anchored | 180 | 1.10824e+07 | 3.2237 | 12.3202 | 26.1% | 59.4% | 3:143, 4:37 |
| same-anchor ranker | 180 | 1.10566e+07 | 3.5297 | 13.1203 | 31.7% | 62.8% | 3:131, 4:47, 5:1, 6:1 |

This restriction retains only size-three-or-larger candidates with exact `|R3| > 0.001`; anchors without such a candidate are absent. On mean regret, the overall leader is **same-anchor ranker** and the material-R3 leader is **resource anchored**.

Both alternatives beat the pairwise baseline on the primary selection-regret comparison. This is diagnostic evidence only; neither model is adopted here.

## Within coalition size

Every choice below is made within one held-out anchor and one fixed coalition size; there is no cross-anchor candidate comparison.

| Size | Model | Anchors | Realised pooled EE (bit/J) | Mean regret | p95 regret | Exact best | Exact top 3 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2 | pairwise baseline | 180 | 1.08396e+07 | 6.5981 | 17.7439 | 7.8% | 23.9% |
| 2 | resource anchored | 180 | 1.09748e+07 | 5.2791 | 17.2082 | 13.9% | 34.4% |
| 2 | same-anchor ranker | 180 | 1.11035e+07 | 3.9942 | 15.3715 | 28.9% | 50.6% |
| 3 | pairwise baseline | 180 | 1.09455e+07 | 6.2611 | 18.9956 | 15.0% | 33.9% |
| 3 | resource anchored | 180 | 1.10844e+07 | 4.8008 | 15.8419 | 19.4% | 42.8% |
| 3 | same-anchor ranker | 180 | 1.10556e+07 | 5.2668 | 16.8174 | 18.3% | 43.9% |
| 4 | pairwise baseline | 180 | 1.08712e+07 | 0.0277 | 0.0000 | 97.2% | 98.9% |
| 4 | resource anchored | 180 | 1.08746e+07 | 0.0173 | 0.0000 | 97.8% | 98.9% |
| 4 | same-anchor ranker | 180 | 1.08579e+07 | 0.1097 | 0.0000 | 96.7% | 97.2% |
| 5 | pairwise baseline | 6 | 1.03371e+07 | 0.4255 | 1.6387 | 33.3% | 83.3% |
| 5 | resource anchored | 6 | 1.03371e+07 | 0.4255 | 1.6387 | 33.3% | 83.3% |
| 5 | same-anchor ranker | 6 | 1.03096e+07 | 1.2883 | 4.0035 | 16.7% | 83.3% |
| 6 | pairwise baseline | 6 | 1.04029e+07 | 0.0000 | 0.0000 | 100.0% | 100.0% |
| 6 | resource anchored | 6 | 1.04029e+07 | 0.0000 | 0.0000 | 100.0% | 100.0% |
| 6 | same-anchor ranker | 6 | 1.04029e+07 | 0.0000 | 0.0000 | 100.0% | 100.0% |

### Material |R3|, within size

| Size | Model | Anchors | Realised pooled EE (bit/J) | Mean regret | p95 regret | Exact best | Exact top 3 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 3 | pairwise baseline | 180 | 1.08905e+07 | 4.4707 | 15.2602 | 27.2% | 60.0% |
| 3 | resource anchored | 180 | 1.10313e+07 | 3.2278 | 12.3202 | 31.1% | 66.1% |
| 3 | same-anchor ranker | 180 | 1.10172e+07 | 3.5066 | 12.6582 | 33.3% | 67.8% |
| 4 | pairwise baseline | 177 | 1.0915e+07 | 0.0036 | 0.0000 | 98.9% | 99.4% |
| 4 | resource anchored | 177 | 1.0915e+07 | 0.0036 | 0.0000 | 98.9% | 99.4% |
| 4 | same-anchor ranker | 177 | 1.09133e+07 | 0.0163 | 0.0000 | 98.9% | 99.4% |
| 5 | pairwise baseline | 4 | 1.06246e+07 | 0.1161 | 0.2803 | 50.0% | 100.0% |
| 5 | resource anchored | 4 | 1.06246e+07 | 0.1161 | 0.2803 | 50.0% | 100.0% |
| 5 | same-anchor ranker | 4 | 1.05234e+07 | 1.7554 | 4.2935 | 0.0% | 100.0% |
| 6 | pairwise baseline | 4 | 1.06718e+07 | 0.0000 | 0.0000 | 100.0% | 100.0% |
| 6 | resource anchored | 4 | 1.06718e+07 | 0.0000 | 0.0000 | 100.0% | 100.0% |
| 6 | same-anchor ranker | 4 | 1.06718e+07 | 0.0000 | 0.0000 | 100.0% | 100.0% |

## Resource-sufficiency check

Occupancy accounting passed for all 11,924 rows: for every affected beam, `occupancy_after = occupancy_before + sum_i d_l_ir`. The anchored formula also returned an exact structural zero whenever no beam was touched by two or more coalition members.

That structural-zero condition occurs in 386/11,924 rows (3.24%) and in 26/1,926 material-R3 rows (1.35%). Among structural-zero rows, 200 have exact `|Psi| > 1e-3`; their mean absolute Psi is 0.3577. These are direct failures of occupancy-only per-resource sufficiency: cross-beam coupling can create interaction even when every beam's load is changed by only one member.

The fitted `g` is shared across beams and conditioned on occupancy, activation, shared capacity, and the recorded incoming/outgoing interference summaries. The prediction is always evaluated as `g(l0+sum d)-g(l0)-sum_i[g(l0+d_i)-g(l0)]`; no cardinality gate or free coalition intercept exists.

## Design and provenance

The authenticated corpus has 11,924 rows at 180 anchors, with size histogram `{'2': 6921, '3': 4691, '4': 270, '5': 36, '6': 6}` and family-index digest `b8f55dc15e91155a32aa706a4908aff3bf6ee281565f9ca0644d76679e7da047`. Five deterministic SHA-256 folds hold out complete anchors; each row is scored once by a model that saw no row from that anchor. Fold counts are `[(145, 35), (144, 36), (138, 42), (143, 37), (150, 30)]`.

The common singleton component is a production-shaped 8-unit ReLU score-difference head trained on the exact singleton receipts. The baseline interaction is `sum h(i,j)`, where `h` is trained on exact atomic pair receipts and cannot represent a nonzero higher-order residual. Alternative A is the resource formula above. Alternative B is a 96/48-unit RankNet score trained only on ordered pairs from the same training anchor; it never sees cross-anchor pairs. All feature scaling and the rank score's secondary affine calibration are fit on training folds only.

The diagnostic seed starts from the unchanged first sealed learner seed `6407676579069309528`; fold-local initialization is a deterministic offset recorded in the machine receipt. Physics field, threshold, sign, horizon, prices, service guards, corpus labels, and acceptance rules are unchanged. This task trains copies only and adopts no architecture.

## Held-out R-squared (secondary)

R-squared is computed after demeaning exact targets and predictions within each held-out anchor × coalition-size cell. It therefore cannot be inflated by between-anchor level differences. Ranker scores receive one training-only positive scale per fold; ranking itself is unchanged.

| Population | Model | Within-anchor × size R² |
|---|---|---:|
| All candidates | pairwise baseline | 0.0480 |
| All candidates | resource anchored | 0.2171 |
| All candidates | same-anchor ranker | 0.0624 |
| Material |R3| | pairwise baseline | -0.1286 |
| Material |R3| | resource anchored | 0.2406 |
| Material |R3| | same-anchor ranker | 0.1430 |

### R-squared within coalition size

| Size | Population | Model | R² |
|---:|---|---|---:|
| 2 | All | pairwise baseline | 0.0902 |
| 2 | All | resource anchored | 0.2211 |
| 2 | All | same-anchor ranker | 0.1237 |
| 3 | All | pairwise baseline | -0.0167 |
| 3 | All | resource anchored | 0.2088 |
| 3 | All | same-anchor ranker | -0.0086 |
| 3 | Material |R3| | pairwise baseline | -0.1324 |
| 3 | Material |R3| | resource anchored | 0.2379 |
| 3 | Material |R3| | same-anchor ranker | 0.1486 |
| 4 | All | pairwise baseline | 0.6341 |
| 4 | All | resource anchored | 0.5548 |
| 4 | All | same-anchor ranker | -1.6286 |
| 4 | Material |R3| | pairwise baseline | 0.5420 |
| 4 | Material |R3| | resource anchored | 0.7478 |
| 4 | Material |R3| | same-anchor ranker | 0.1716 |
| 5 | All | pairwise baseline | 0.6025 |
| 5 | All | resource anchored | 0.5537 |
| 5 | All | same-anchor ranker | -4.5497 |
| 5 | Material |R3| | pairwise baseline | 0.5363 |
| 5 | Material |R3| | resource anchored | 0.5361 |
| 5 | Material |R3| | same-anchor ranker | -4.8481 |
| 6 | All | pairwise baseline | n/a |
| 6 | All | resource anchored | n/a |
| 6 | All | same-anchor ranker | n/a |
| 6 | Material |R3| | pairwise baseline | n/a |
| 6 | Material |R3| | resource anchored | n/a |
| 6 | Material |R3| | same-anchor ranker | n/a |
