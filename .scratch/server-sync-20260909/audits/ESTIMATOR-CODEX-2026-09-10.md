C1: `ESTIMATOR_ARTEFACT` | C2: `ESTIMATOR_ARTEFACT`

`DIAGNOSTIC_NOT_CLAIM`

# C1/C2 estimator audit — 2026-09-10

This is an estimator audit on the 26,345 already-defined valid non-reference rows. No production learner, policy, acceptance gate, or fallback flag was changed, and no threshold, sign, seed, horizon, price, guard, or acceptance rule was changed.

## A — unchanged replication

The prior diagnostic was run unchanged from `/home/sat/mcrl-v025-c1c2suff-ws` with 30 anchors. It reproduced the row count, split, selected neighbour count, held-out row count, target variances, explained variances, and RMSEs at full emitted precision:

| Route | Held-out EV | Held-out RMSE | Held-out target variance | Selected k |
|---|---:|---:|---:|---:|
| C1 | `-0.33554767986149203` | `3.468393728057137` | `8.34196834334199` | 31 |
| C2 | `0.21065167813231378` | `3.385646156133314` | `14.369004998057571` | 31 |

The reproduced split was train steps `{1,2,4,6,7,8,9}`, validation step `{5}`, and test steps `{0,3}`, with 5,280 test rows and seed `20260909`. This satisfies the replication prerequisite; the downstream audit uses those same route-specific encoded features and exact targets.

## B — predeclared estimator ladder

Before any ladder model was run, the complete list was declared as: training-mean constant, ordinary least squares, validation-selected ridge, modest-depth validation-early-stopped gradient-boosted trees, and the original k-NN. No sixth model was added, and every result is below.

| Route | Estimator | Held-out EV | Held-out RMSE | Selection detail |
|---|---|---:|---:|---|
| C1 | Constant predictor | `0.0000000000` | `2.9584953816` | strict training-split mean |
| C1 | Ordinary least squares | `0.0892133009` | `2.8688725007` | no hyperparameter |
| C1 | Ridge | `0.0892133009` | `2.8688725006` | penalty `1e-6` |
| C1 | Gradient-boosted trees | `0.0235123190` | `2.9187599056` | 151 trees |
| C1 | Original k-NN | `-0.3355476799` | `3.4683937281` | `k=31` |
| C2 | Constant predictor | `0.0000000000` | `3.8210027084` | strict training-split mean |
| C2 | Ordinary least squares | `0.3010404869` | `3.1702888107` | no hyperparameter |
| C2 | Ridge | `0.3010404862` | `3.1702888117` | penalty `1e-6` |
| C2 | Gradient-boosted trees | `0.2679215987` | `3.2856117817` | 112 trees |
| C2 | Original k-NN | `0.2106516781` | `3.3856461561` | `k=31` |

The C1 ridge/OLS difference is only numerical (`1.13e-11` EV); ridge is called the C1 winner solely because its emitted EV is fractionally higher. C2 OLS is the clear winner.

### Fitting and selection details

- Constant uses the mean of strict training steps only. EV is exactly zero for any constant; the training mean determines its reported RMSE.
- OLS is fit on train plus validation before the untouched test evaluation.
- Ridge uses standardized features, selects only on validation-step EV from the fixed positive penalty grid `{1e-6,1e-4,1e-2,1e-1,1,10,100,1e3,1e4,1e5,1e6}`, then refits on train plus validation with the selected penalty.
- The deterministic squared-error histogram gradient booster has depth 3, learning rate `0.05`, at most 500 trees, 64 bins, minimum leaf size 30, and patience 30. It is fit on strict training rows and retains the iteration with minimum validation RMSE: 151 trees for C1 and 112 for C2.
- k-NN is the original standardized inverse-squared-distance implementation, selects `k` from `{1,3,7,15,31}` by validation EV, and refits on train plus validation. It selects `k=31` for both routes and exactly reproduces A.

The environment contains NumPy `2.5.2` but no scikit-learn, XGBoost, or LightGBM, so the modest-depth histogram booster is implemented transparently in the retained audit script rather than substituting another model family.

## C — split sensitivity for the best ladder estimator

For C1, the numerically best estimator is ridge with the selected penalty frozen at `1e-6`. For C2 it is OLS; each leave-one-step-out fold fits that same estimator on the other nine whole physical steps.

### Original test steps separately

| Route / estimator | Test step | EV | RMSE |
|---|---:|---:|---:|
| C1 ridge | 0 | `0.2477220949` | `2.0983022008` |
| C1 ridge | 3 | `0.0203994950` | `3.4787541212` |
| C2 OLS | 0 | `0.2129546272` | `4.3548173815` |
| C2 OLS | 3 | undefined: target variance is zero | `1.0174266391` |

C1 is positive on each originally held-out step separately. The original negative aggregate C1 value is therefore not caused by one unlucky member of `{0,3}` under the better estimator.

### Leave-one-step-out rotation

| Step | C1 ridge EV | C1 RMSE | C2 OLS EV | C2 RMSE |
|---:|---:|---:|---:|---:|
| 0 | `0.2453421372` | `2.1688393983` | `0.2166562220` | `4.3447396555` |
| 1 | `0.1759196119` | `2.2076662595` | `0.2026798344` | `3.8062953661` |
| 2 | `0.0993443344` | `2.2170766128` | `0.0273528908` | `3.6200239619` |
| 3 | `0.0167254145` | `3.5099767348` | undefined: variance zero | `0.9719879724` |
| 4 | `0.2589366346` | `1.7397096330` | `0.2931457791` | `3.8670086432` |
| 5 | `0.2663861088` | `2.1290793127` | `0.3432062777` | `3.3842954104` |
| 6 | `0.1061865968` | `1.8917579735` | `0.1597012127` | `3.1748312741` |
| 7 | `0.0765833532` | `4.6941377409` | undefined: variance zero | `1.1687533139` |
| 8 | `0.1908808533` | `1.6572850427` | `0.2534634301` | `4.2321130401` |
| 9 | `0.2076794012` | `2.0039039074` | `0.1264856122` | `3.9779951042` |

C1 EV is positive in all ten rotations: mean `0.1643984446`, standard deviation `0.0810787281`, minimum `0.0167254145`, maximum `0.2663861088`, and range `0.2496606943`. Thus the original negative C1 number does not hold across the rotation for the better estimator; it is estimator-specific, not a single-step accident.

C2 has positive EV in all eight folds where EV is defined: mean `0.2028364074`, standard deviation `0.0929369032`, minimum `0.0273528908`, maximum `0.3432062777`, and range `0.3158533869`. Steps 3 and 7 have exactly zero within-step C2 target variance, so EV is mathematically undefined there; their finite RMSEs are reported rather than inventing an EV.

## D — exact encoded-row collision floor

For route-specific feature vector `x`, the empirical irreducible floor was computed as

`(1/N) * sum_over_collision_groups sum_i (y_i - group_mean)^2`,

where grouping keys are the byte-identical big-endian binary64 feature vectors and target disagreement is checked using the exact rational target strings. The fraction reported is that floor divided by the population variance of the exact targets converted at the row boundary.

| Route | All exact duplicate groups | Groups with differing exact targets | Rows in differing-target groups | Variance floor | Corpus target variance | Floor / variance |
|---|---:|---:|---:|---:|---:|---:|
| C1 | 2,666 | 0 | 0 | `0.0` | `7.4428962868` | `0.0%` |
| C2 | 1,181 | 879 | 1,758 | `0.8931142961` | `16.1198592400` | `5.5404596456%` |

C1 has exact duplicate encoded rows, but none of its duplicate groups has differing exact C1 targets, so this corpus implies no positive C1 collision floor. C2 has 879 differing-target collision groups, implying that at least 5.54% of its corpus target variance is unreachable by any deterministic predictor using only the 22 encoded C2 features.

## Reproduction files and exact commands

Retained files:

- `scripts/audit_v025_c1c2_estimators.py` — the complete ladder, rotation, and collision-floor audit.
- `artifacts/c1c2-estimator-audit-20260910.json` — full-precision machine-readable results, including every validation candidate.
- `C1C2-ESTIMATOR-AUDIT-2026-09-10.md` — this report.

Unchanged replication, with working directory `/home/sat/mcrl-v025-c1c2suff-ws`:

```bash
nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python scripts/diagnose_v025_c1c2_sufficiency.py --anchors 30
```

Estimator audit, with working directory `/home/sat/mcrl-v025-replay-ws`:

```bash
nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python scripts/audit_v025_c1c2_estimators.py --output artifacts/c1c2-estimator-audit-20260910.json
```

The source diagnostic and `/home/sat/mcrl-leo-handover/.venv` were read/executed but never modified. No sealed artifact or fallback flag was modified.

## Required verdicts

**C1 — `ESTIMATOR_ARTEFACT`.** Positive-penalty ridge achieves held-out EV `0.0892133009` against the constant's `0.0` and the original k-NN's `-0.3355476799`, so the encoded C1 features do carry recoverable predictive value. Its EV is positive on both original test steps and all ten leave-one-step-out folds, so the correction is stable enough to reject the “features carry no predictive value” inference.

**C2 — `ESTIMATOR_ARTEFACT`.** OLS achieves held-out EV `0.3010404869`, improving on both the constant's `0.0` and the original k-NN's `0.2106516781`, so the original estimator understates what the encoded C2 features carry. Every finite leave-one-step-out EV is positive, while the other two folds are undefined only because their targets have zero variance, so the estimator conclusion is not driven by an unstable negative rotation.
