The report is written to `/home/sat/mcrl-v025-prevalence-ws/C1C2-ESTIMATOR-INDEPENDENT-2026-09-10.md`. Printing it in full:

---

# Independent re-check of the C1/C2 held-out explainability numbers — 2026-09-10

**C1: `ESTIMATOR_ARTEFACT` — C2: `ESTIMATOR_ARTEFACT`**

`DIAGNOSTIC_NOT_CLAIM`. No training run, no policy run, no physics evaluation stage. No threshold, sign, seed, horizon, price, guard or acceptance rule was changed; no sealed artefact was written; `PILOT_PRIMITIVE_SOURCE_FALLBACK` was left at its existing value `True` and never touched.

---

## Verdicts

**C1 — `ESTIMATOR_ARTEFACT`.** Ridge regression on the same 16 standardised Q1 scalars beats the constant predictor on **10 of 10** leave-one-step-out folds (median EV `+0.1801`, worst fold `+0.0281`) and on the published split itself (`EV +0.0892`, `R² +0.0134`, against the constant's `EV 0.0000`, `R² −0.0530`). The published `−0.3355` is a k-nearest-neighbour failure concentrated on one held-out step — k-NN scores `+0.2300` on test step 0 and `−0.5765` on test step 3 — and it cannot be a collision effect, because the Q1 route has **zero** duplicate groups carrying more than one exact target, so its structurally unreachable variance is exactly `0.0`.

**C2 — `ESTIMATOR_ARTEFACT`.** The published value is positive but still understates: the same ridge reaches `EV +0.3010` against the published k-NN's `+0.2107` on the identical split, and is positive on **8 of 8** usable folds (median `+0.2013`); merely widening the k grid from `{1..31}` to include `k=511` lifts k-NN itself to `+0.2905`. The Q2 route does have real collisions — 879 duplicate groups carry conflicting exact targets — but they cap explainable variance at `0.9446`, so they account for about `0.055` of the roughly `0.70` that goes unexplained, not for the bulk of it.

Neither verdict says the heads are well-predicted. C1's features explain only ~9–18% of target variance and C2's ~20–30%. The finding is that the published `−0.3355` misattributes an estimator failure to the features, and that both routes carry real, repeatable, positive signal.

---

## 1. Replication — both published numbers reproduce exactly

Reproduced to 10 decimal places, so this report is not a dispute about the arithmetic.

| Route | Published | Reproduced | Absolute difference |
|---|---:|---:|---:|
| C1 Q1-only held-out EV | `-0.3355476799` | `-0.33554767986149203` | `3.85e-11` |
| C2 Q2-only held-out EV | `+0.2106516781` | `+0.21065167813231378` | `3.23e-11` |

Every structural quantity matches as well: **26,345** exact-relabelled valid non-reference rows from 30 source anchors; split by whole physical step into train `{1,2,4,6,7,8,9}` (18,419 rows), validation `{5}` (2,646), test `{0,3}` (**5,280**); `k=31` selected on validation for both routes; C1 held-out target variance `8.3419683433`, C2 `14.3690049981`; the discarded-structure OLS comparator returns `EV = 1.0` on both routes.

The row derivation is independent — I re-ran the exact evaluator relabel myself from the source shards — while the fitting code is the prior script's `_fit_route` called verbatim, so the replication isolates the estimator rather than re-deriving it.

**Provenance.** The prevalence workspace has no `stagec_v025` and an older `physics_v025`, so the prior workspace's code and rows were snapshotted read-only into `.scratch/c1c2-indep/` before any run. The snapshot reproduces the digests recorded *inside the shards themselves* — `physics_digest = 38e1998a…`, `launch_digest = 3137ce5b…` — and all 30 shards verified against their `.sha256` sidecars. The snapshot is pinned: it was taken at `scripts/diagnose_v025_c1c2_sufficiency.py` = `6aa5953ddffdb7c9…`, and that other workspace has since edited the file to `c36498afc7c5783a…` while I worked. Everything below is against the pinned copy, which reproduces the published numbers exactly. Interpreter `python 3.13.3`, `numpy 2.5.2`, `torch 2.13.0+cu130`; `sklearn` and `scipy` are absent from that venv, so ridge, the gradient-boosted trees and the k-NN were implemented directly against numpy in the sandbox.

---

## 2. Estimators were declared before any of them was fitted

`.scratch/c1c2-indep/DECLARED-ESTIMATORS.md`, sha256 `e86a74ab2ed3ad76643cab35b46b01b402dbb89dcaf8f9114281d3e0a6087554`, written before any estimator on the list was run. All eight are reported below, including the four that do worse than the constant. Nothing was added afterwards.

Hyperparameters were selected on the validation step only, then refitted on train+validation and scored once on the test steps. Test steps were never consulted for any selection.

### A metric note that matters for reading every table

The published metric is *explained variance*, `EV = 1 − Var(y − ŷ)/Var(y)`, computed on the **variance** of the residual. That is blind to a constant offset, so a constant predictor scores exactly `0.0` under it no matter which constant it uses. A split by physical step is precisely a mean shift, so EV systematically flatters every estimator here. I therefore also report `R² = 1 − mean((y − ŷ)²)/Var(y)`, which does penalise the shift. The constant predictor's R² is `−0.0530` (C1) and `−0.0247` (C2) — that, not zero, is the honest zero point.

---

## 3. Published split — all declared estimators

C1 route (Q1, 16 features → `c1_difference_surplus`), 5,280 held-out rows, target variance `8.3420`:

| id | estimator | selected | EV | R² | RMSE | MAE |
|---|---|---|---:|---:|---:|---:|
| E0 | CONSTANT | — | `+0.000000` | `−0.052996` | `2.9638` | `1.9570` |
| **E1** | **RIDGE-LINEAR** | `α=1e−6` | **`+0.089213`** | **`+0.013371`** | `2.8689` | `1.9247` |
| E2 | RIDGE-POLY2 | `α=1000` | `+0.090279` | `−0.021835` | `2.9196` | `2.0410` |
| E3 | KNN-PUBLISHED | `k=31` | `−0.335548` | `−0.442076` | `3.4684` | `2.4645` |
| E4 | KNN-EXTENDED | `k=31` | `−0.335548` | `−0.442076` | `3.4684` | `2.4645` |
| E5 | GBT | `d=3, lr=0.2, 84 trees` | `−0.054949` | `−0.157377` | `3.1072` | `2.1481` |
| E6 | MLP | `wd=0, epoch 34` | `−0.231969` | `−0.340718` | `3.3443` | `2.4931` |
| E7 | STRUCT-OLS *(ceiling ref, excluded from verdict)* | — | `+1.000000` | `+1.000000` | `2.7e−13` | — |

C2 route (Q2, 22 features → `c2_persistence_forecast`), target variance `14.3690`:

| id | estimator | selected | EV | R² | RMSE | MAE |
|---|---|---|---:|---:|---:|---:|
| E0 | CONSTANT | — | `+0.000000` | `−0.024674` | `3.8371` | `2.8291` |
| **E1** | **RIDGE-LINEAR** | `α=1e−6` | **`+0.301040`** | **`+0.300527`** | `3.1703` | `2.0369` |
| E2 | RIDGE-POLY2 | `α=0.1` | `−0.300629` | `−0.529333` | `4.6877` | `2.4837` |
| E3 | KNN-PUBLISHED | `k=31` | `+0.210652` | `+0.202269` | `3.3856` | `1.6547` |
| E4 | KNN-EXTENDED | `k=511` | `+0.290506` | `+0.281136` | `3.2139` | `1.5620` |
| E5 | GBT | `d=6, lr=0.05, 52 trees` | `+0.228931` | `+0.228309` | `3.3299` | `1.8149` |
| E6 | MLP | `wd=0, epoch 29` | `+0.126729` | `+0.121695` | `3.5525` | `1.7792` |
| E7 | STRUCT-OLS *(ceiling ref, excluded from verdict)* | — | `+1.000000` | `+1.000000` | `1.0e−14` | — |

On C1 the flexible estimators — the k-NN, the boosted trees, the network — all lose to a plain ridge, and three of them lose to a constant. That pattern is the signature of a distribution-shifted split with a weak, largely linear signal: flexible learners chase training-step structure that does not transport, while a heavily-regularised linear map keeps the part that does.

---

## 4. It is largely one unlucky held-out step (declared check S1)

Per-test-step EV on the published split:

| estimator | C1 step 0 | C1 step 3 | C2 step 0 | C2 step 3 |
|---|---:|---:|---:|---:|
| E0 CONSTANT | `+0.0000` | `+0.0000` | `+0.0000` | *undefined* |
| E1 RIDGE-LINEAR | `+0.2477` | `+0.0204` | `+0.2130` | *undefined* |
| E2 RIDGE-POLY2 | `+0.2708` | `+0.0271` | `−0.2545` | *undefined* |
| E3 KNN-PUBLISHED | `+0.2300` | **`−0.5765`** | `+0.0651` | *undefined* |
| E4 KNN-EXTENDED | `+0.2300` | **`−0.5765`** | `+0.1618` | *undefined* |
| E5 GBT | `+0.3558` | `−0.2131` | `+0.0951` | *undefined* |
| E6 MLP | `+0.2921` | `−0.4226` | `−0.0332` | *undefined* |

The published C1 `−0.3355` is not a uniform failure. On test step 0 the published estimator scores `+0.2300`; the whole negative sign comes from step 3, where it scores `−0.5765` and ridge still manages `+0.0204`. Step 3 is also where the C1 target variance jumps to `11.80` against a corpus median near `5.1`.

**A second, unrelated defect in the C2 held-out set.** On physical steps 3 and 7 the exact C2 target is the constant `−3.0` for **every** row, with variance exactly zero — all three forecast offsets are lost, so the target collapses to the `−1` per lost offset floor. Test step 3 is one of them. EV and R² are undefined on a zero-variance target, which is why the C2 step-3 column is blank above. The pooled C2 test variance of `14.3690` is therefore substantially *between-step* variance: a large part of the published `+0.2107` is earned by separating a live step from a dead one, not by resolving targets within a step. On test step 0 alone the published estimator scores only `+0.0651`, and ridge `+0.2130`.

## 5. Ten-step rotation (declared check S2)

Leave-one-step-out over all ten steps; fold `s` tests on step `s`, validates on step `(s+1) mod 10`, trains on the other eight. C2 folds for steps 3 and 7 are undefined (zero target variance), leaving eight usable folds on that route.

**C1 — EV by held-out step**

| estimator | s0 | s1 | s2 | s3 | s4 | s5 | s6 | s7 | s8 | s9 | median | IQR | min | folds > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0 CONSTANT | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0.0000` | `0.000` | `0.0000` | 0/10 |
| **E1 RIDGE-LINEAR** | `+.245` | `+.176` | `+.097` | `+.028` | `+.259` | `+.185` | `+.106` | `+.064` | `+.207` | `+.208` | **`+0.1801`** | `0.109` | **`+0.0281`** | **10/10** |
| E2 RIDGE-POLY2 | `+.276` | `+.199` | `+.105` | `−.059` | `+.315` | `+.212` | `−.006` | `+.102` | `+.208` | `+.273` | `+0.2033` | `0.154` | `−0.0586` | 8/10 |
| E3 KNN-PUBLISHED | `+.222` | `+.145` | `+.021` | **`−.605`** | `+.248` | `+.319` | `+.063` | `+.061` | `+.161` | `+.288` | `+0.1530` | `0.181` | `−0.6051` | 9/10 |
| E4 KNN-EXTENDED | `+.235` | `+.153` | `+.066` | `−.347` | `+.267` | `+.230` | `+.140` | `+.058` | `+.202` | `+.315` | `+0.1778` | `0.149` | `−0.3474` | 9/10 |
| E5 GBT | `+.332` | `+.206` | `+.076` | `−.270` | `+.383` | `+.326` | `+.102` | `+.021` | `+.227` | `+.107` | `+0.1567` | `0.219` | `−0.2702` | 9/10 |
| E6 MLP | `+.305` | `+.202` | `+.038` | **`−.628`** | `+.318` | `+.302` | `+.125` | `+.088` | `+.169` | `+.266` | `+0.1858` | `0.196` | `−0.6283` | 9/10 |

Every estimator except ridge goes negative on step 3, and only on step 3. Ridge never goes negative on any fold. On R² the same picture holds: ridge is positive on 9/10 folds (median `+0.1254`) while the constant predictor is negative on **0/10** — that is, negative on all ten.

**C2 — EV by held-out step** (steps 3 and 7 undefined)

| estimator | s0 | s1 | s2 | s4 | s5 | s6 | s8 | s9 | median | IQR | min | folds > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0 CONSTANT | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0.0000` | `0.000` | `0.0000` | 0/8 |
| **E1 RIDGE-LINEAR** | `+.215` | `+.187` | `+.037` | `+.293` | `+.341` | `+.129` | `+.235` | `+.126` | **`+0.2013`** | `0.121` | **`+0.0367`** | **8/8** |
| E2 RIDGE-POLY2 | `+.174` | `+.188` | `+.032` | `+.300` | `+.347` | `+.129` | `+.222` | `+.141` | `+0.1808` | `0.103` | `+0.0321` | 8/8 |
| E3 KNN-PUBLISHED | `+.068` | `+.120` | `−1.136` | `+.207` | `+.269` | `−1.551` | `+.247` | `+.119` | `+0.1191` | `0.450` | `−1.5512` | 6/8 |
| E4 KNN-EXTENDED | `+.186` | `+.192` | `−1.136` | `+.269` | `+.320` | `−1.551` | `+.255` | `+.123` | `+0.1894` | `0.451` | `−1.5512` | 6/8 |
| E5 GBT | `+.085` | `+.108` | `−.143` | `+.220` | `+.151` | `+.028` | `+.200` | `+.090` | `+0.0991` | `0.092` | `−0.1430` | 7/8 |
| E6 MLP | `+.131` | `+.184` | `−.049` | `+.238` | `+.333` | `+.140` | `+.245` | `+.128` | `+0.1618` | `0.110` | `−0.0495` | 7/8 |

**Caveat I should flag rather than bank.** The two C2 folds where k-NN collapses — test steps 2 and 6 — are exactly the two folds whose validation step under the declared `(s+1)` rule lands on a degenerate zero-variance step (3 and 7). Hyperparameter selection there had to fall back to validation MSE against a constant target, which is a weak selection signal. So those two `−1.1`/`−1.6` entries partly reflect my rotation's validation rule, not purely signal instability. The honest reading is that ridge is robust to that degeneracy and k-NN is not; I would not quote `−1.55` as a property of the data. Ridge's 8/8 and the C1 rotation, where no step is degenerate, carry the verdict.

## 6. Structurally unreachable variance (declared check S3)

Grouping rows by byte-identical feature vector and measuring the spread of exact targets inside each group:

| | C1 / Q1 (full corpus) | C1 / Q1 (held-out) | C2 / Q2 (full corpus) | C2 / Q2 (held-out) |
|---|---:|---:|---:|---:|
| rows | 26,345 | 5,280 | 26,345 | 5,280 |
| distinct feature vectors | 23,679 | 4,388 | 25,164 | 5,118 |
| duplicate groups | 2,666 | 892 | 1,181 | 162 |
| **groups with > 1 exact target** | **0** | **0** | **879** | **62** |
| rows in conflicting groups | 0 | 0 | 1,758 | 124 |
| pooled within-group variance | `0.0` | `0.0` | `0.8931` | `0.4310` |
| total target variance | `7.4429` | `8.3420` | `16.1199` | `14.3690` |
| **achievable EV ceiling** | **`1.0`** | **`1.0`** | **`0.9446`** | **`0.9700`** |
| largest within-group spread | `0.0` | `0.0` | `31.4331` | `16.7982` |

**C1: no such duplicates exist.** All 2,666 duplicate Q1 groups carry a single exact target. Per the instruction, that is the answer for this route: the Q1 route's structurally unreachable variance in this corpus is exactly zero, and its ceiling is `EV = 1.0`. Not one point of the published `−0.3355` is attributable to collisions. (This is the empirical complement to the prior report's C1 witness, which was a *constructed* admissible pair, not an observed one — consistent with, not contradicted by, this finding.)

**C2: collisions are real but small.** 879 conflicting groups covering 1,758 rows (6.7% of the corpus) cap explainable variance at `0.9446`. The 62 conflicting groups on the held-out steps independently corroborate the prior report's "62 exact C2 collision groups". The largest observed within-group target spread is `31.43`, larger than the prior report's `13.94` witness. But `0.055` of unreachable variance cannot explain the roughly `0.70` that no declared estimator reaches.

## 7. One more instability worth recording

While reconciling my suite against the published pipeline I found that the k-NN's held-out EV moves with the **order of the training rows**, holding data, split, `k` and standardisation fixed:

| route | `k` | EV, corpus row order | EV, train-block-then-validation order | delta |
|---|---:|---:|---:|---:|
| C1 | 31 | `−0.3355476799` | `−0.3634369136` | `0.0279` |
| C2 | 31 | `+0.2106516781` | `+0.2100770197` | `0.0006` |

98.7% of held-out C1 predictions change. The cause is that byte-identical duplicate rows sit at distance ≈ 0, where the inverse-distance weight `1/max(d², 1e-12)` reaches `1e12` and swamps the other neighbours; which of the tied duplicates lands in the k-set is then decided by `argpartition` ordering. On C1 that nuisance sensitivity alone is `0.028` EV — about a third of the entire ridge-vs-constant effect, and larger than several of the differences the published table invites the reader to compare. The published numbers in section 1 are the corpus-row-order values, and my suite matches that ordering so the comparison is like-for-like.

## 8. What I did not establish

- These are finite-sample scores on ten physical steps of one world tape. They bound nothing about every possible architecture, in either direction.
- The prior report's formal insufficiency argument rests on the collision witnesses and their squared-loss lower bounds, not on this regression. Section 6 corroborates the C2 collisions and quantifies them as small; it does not touch the constructed C1 contract witness, which is an admissibility proof rather than an empirical claim, and which this corpus scan neither confirms nor refutes.
- I did not re-derive the targets from first principles; I re-ran the production evaluator relabel. If that relabel path is wrong, both the published numbers and mine are wrong together.
- E6 (MLP) is not bit-reproducible across thread counts; two runs of the same configuration differed by `0.002` EV on a synthetic check. It is the weakest-evidence entry in the tables and no verdict rests on it.

## 9. Verdicts, restated

**C1 — `ESTIMATOR_ARTEFACT`.** A plain ridge on the identical 16 features beats the constant predictor on the published split (`EV +0.0892` vs `0.0000`; `R² +0.0134` vs `−0.0530`) and on 10 of 10 rotation folds with median `EV +0.1801` and no negative fold, while the published k-NN is negative on exactly one step and positive on the other nine. Since the Q1 route has zero conflicting duplicate groups and therefore a ceiling of `EV = 1.0`, the published `−0.3355` measures the estimator, not the features.

**C2 — `ESTIMATOR_ARTEFACT`.** Ridge reaches `EV +0.3010` where the published k-NN reaches `+0.2107` on the same split, and simply extending the declared `k` grid to `k=511` lifts k-NN itself to `+0.2905`; ridge is positive on all 8 usable rotation folds (median `+0.2013`) where the published estimator fails on 2. The route's genuine collisions cap it at `EV 0.9446`, far above anything observed, so the published figure understates what Q2 carries rather than revealing a structural limit — with the caveat that part of it is earned on a held-out step whose target variance is exactly zero.

---

### Reproduction

```text
SANDBOX=.scratch/c1c2-indep      # read-only snapshot of the prior workspace's code and rows
cd $SANDBOX && nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=2 \
  /home/sat/mcrl-leo-handover/.venv/bin/python -u scripts/build_exact_rows_cache.py    # ~14 min
cd $SANDBOX && nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python \
  -u scripts/replicate_published.py        # -> replication.json
cd $SANDBOX && nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=2 \
  /home/sat/mcrl-leo-handover/.venv/bin/python -u scripts/independent_estimators.py    # -> independent_main.json
cd $SANDBOX && nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=2 \
  /home/sat/mcrl-leo-handover/.venv/bin/python -u scripts/rotation.py                  # -> rotation.json
```

Artefacts, all under `.scratch/c1c2-indep/`: `DECLARED-ESTIMATORS.md` (pre-registration, sha256 `e86a74ab…`), `descriptives.json`, `replication.json`, `independent_main.json`, `rotation.json`, `exact_rows_30anchor.npz`. Nothing was written to `/home/sat/mcrl-leo-handover`, to `/home/sat/mcrl-v025-c1c2suff-ws`, or to any sealed artefact.
