**Held-out pairwise ordering is 0.619236 with admissible resource context versus 0.620817 without it (gain -0.001581): the gain is not material by the predeclared diagnostic convention.**

# C1 resource-context diagnostic — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`

No production training run, policy run, or acceptance test was performed. This is an offline fit on copies for measurement only. No sealed contract, target, scorer, schema digest, manifest, constant, threshold, sign, seed, horizon, price, service guard, or acceptance rule was modified.

## Direct answer

Adding the admissible singleton resource context changes ordering by -0.001581, closing -0.63% of the stated 0.252 gap. The leave-one-step-out context gain ranges from -0.006425 to +0.004496. Under the frozen rule (gain at least 0.0252 and positive for every omission), this is not material.

## Admissibility finding

The coordinate formulas are admissible, but the stored coalition-wide values are not valid C1 inputs as-is. `scripts/run_v025_pilot_c3.py:844-906` builds affected beams, before/after occupancies, active-state changes, capacity margins, pairwise cross-gains and six globals solely from the reference/selected assignments and the decision-time tape. `_cross_gain_terms` at `:806-841` reads static `cross_base_nominal` arrays; neither function accepts an evaluator or outcome. The interaction path consumes `CoalitionContext.invariant_vector` (`src/mcrl/stagec_v025/coalitions.py:231-280`) through `model.interaction`, and the selector calls it while scoring catalogue profiles (`src/mcrl/stagec_v025/deployment.py:717-736`).

A coalition-wide vector depends on the other proposed member actions, while the C1 interface is action-local (`deployment.py:626-645`). I therefore did not feed those stored values to C1. For every exact singleton receipt I rebuilt the same 163 coordinate formulas from the reference profile and that focal `(user, action)` alone. No coordinate family was excluded: all 28 affected-beam pool values, 129 pairwise-cross-gain values, and six globals pass the pre-decision/no-fixed-point rule in this singleton form. Only 28 of the 163 slots vary on held-out singleton actions; coalition-induced variation in the other slots is unavailable under the focal-action-only rule. The candidate outcome, label, power fixed point, and whole-network result are absent from feature construction.

## Frozen protocol and fit

The harness uses 10253 exact coalition fitting rows and 33670 unique singleton actions across the frozen split. It reuses seed `20260910`, the three-anchor-block split, the fixed-ReLU random-feature ridge family with raw linear skip, and the exact six-point grid from the parametrisation comparison. Each shared per-user scorer is fitted through the sum of its member differences on the original coalition rows. Exact singleton targets are read from Fraction receipts; the pilot fallback is never read as a target. Re-evaluated defining terms reconstruct those receipts with maximum residual 1.030e-13 on development and 7.749e-14 on test.

| arm | width | ridge | validation RMSE |
|---|---|---|---|
| Q1_ONLY | 64 | 0.01 | 11.417979 |
| Q1_PLUS_CONTEXT | 64 | 0.01 | 8.123461 |
| Q1_PLUS_CONTEXT_MINUS_EXTERNALITY | 128 | 0.01 | 5.356438 |
| LEAKY_ORACLE | 64 | 1e-06 | 0.000036 |

`Q1_PLUS_CONTEXT_MINUS_EXTERNALITY` is fitted to `own + energy + Φ`, then assessed against full exact C1. `LEAKY_ORACLE` uses the exact `own`, `externality`, `energy`, and `Φ` terms as input to the same estimator and grid and is `NOT_DEPLOYABLE`.

## Held-out first-route metrics

| scorer | rows incl. base | explained variance | RMSE | pairwise ordering | comparable pairs |
|---|---|---|---|---|---|
| Q1_ONLY | 9744 | 0.015222 | 2.256001 | 0.620817 | 11385 |
| Q1_PLUS_CONTEXT | 9744 | 0.077827 | 2.178662 | 0.619236 | 11385 |
| Q1_PLUS_CONTEXT_MINUS_EXTERNALITY | 9744 | 0.169234 | 2.068672 | 0.629952 | 11385 |
| LEAKY_ORACLE | 9744 | 1.000000 | 0.000011 | 1.000000 | 11385 |

Pairwise ordering is micro-accuracy over unequal exact pairs within each `(world, anchor, user)` candidate pool, with the exact zero/base action included and predicted ties counted as incorrect. The `0.620817` Q1-only reference is not expected to equal the earlier `0.650`: this run obeys the requested comparator corpus, split, random-feature estimator and grid, while `0.650` came from the separate 24-anchor production-head-shape probe.

## By held-out anchor

| anchor | Q1_ONLY EV | Q1_ONLY RMSE | Q1_ONLY order | Q1_PLUS_CONTEXT EV | Q1_PLUS_CONTEXT RMSE | Q1_PLUS_CONTEXT order | Q1_PLUS_CONTEXT_MINUS_EXTERNALITY EV | Q1_PLUS_CONTEXT_MINUS_EXTERNALITY RMSE | Q1_PLUS_CONTEXT_MINUS_EXTERNALITY order | LEAKY_ORACLE EV | LEAKY_ORACLE RMSE | LEAKY_ORACLE order |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V025_PROBE/world/1\|15 | 0.319944 | 1.531954 | 0.732704 | 0.177186 | 1.686127 | 0.688679 | 0.372641 | 1.482811 | 0.757862 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/1\|16 | 0.468407 | 1.297482 | 0.726415 | 0.284446 | 1.473505 | 0.713836 | 0.416905 | 1.364600 | 0.770440 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/1\|17 | -0.044828 | 2.597759 | 0.569388 | 0.180243 | 2.302172 | 0.559184 | 0.207725 | 2.262621 | 0.567347 | 1.000000 | 0.000011 | 1.000000 |
| V025_PROBE/world/1\|39 | -0.188254 | 1.844364 | 0.547855 | 0.019115 | 1.676505 | 0.600660 | 0.114281 | 1.668392 | 0.640264 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/1\|40 | 0.246105 | 1.937079 | 0.592593 | 0.259881 | 1.863093 | 0.609687 | 0.336409 | 1.876789 | 0.683761 | 1.000000 | 0.000011 | 1.000000 |
| V025_PROBE/world/1\|41 | -0.283429 | 1.903152 | 0.486900 | -0.204029 | 1.843891 | 0.543668 | -0.054200 | 1.694628 | 0.515284 | 1.000000 | 0.000009 | 1.000000 |
| V025_PROBE/world/1\|48 | 0.331414 | 1.516598 | 0.736508 | 0.286943 | 1.572817 | 0.692063 | 0.482928 | 1.366199 | 0.730159 | 1.000000 | 0.000011 | 1.000000 |
| V025_PROBE/world/1\|49 | 0.331414 | 1.516598 | 0.736508 | 0.286943 | 1.572817 | 0.692063 | 0.482928 | 1.366199 | 0.730159 | 1.000000 | 0.000011 | 1.000000 |
| V025_PROBE/world/1\|50 | 0.262050 | 2.153660 | 0.562771 | 0.274265 | 2.129060 | 0.534632 | 0.283077 | 2.121756 | 0.562771 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/1\|6 | 0.194225 | 1.217944 | 0.642202 | -0.221595 | 1.517296 | 0.657492 | 0.090795 | 1.293773 | 0.642202 | 1.000000 | 0.000009 | 1.000000 |
| V025_PROBE/world/1\|63 | 0.081474 | 1.643281 | 0.692308 | 0.161408 | 1.632242 | 0.669872 | 0.263791 | 1.585624 | 0.698718 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/1\|64 | -0.499296 | 1.786821 | 0.692073 | 0.148399 | 1.318942 | 0.631098 | 0.076439 | 1.382104 | 0.637195 | 1.000000 | 0.000009 | 1.000000 |
| V025_PROBE/world/1\|65 | -0.074967 | 3.169568 | 0.575926 | 0.105289 | 2.903303 | 0.542593 | 0.102100 | 2.913524 | 0.527778 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/1\|7 | 0.247287 | 1.295099 | 0.614286 | 0.089472 | 1.428782 | 0.628571 | 0.328582 | 1.272264 | 0.654286 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/1\|8 | -0.023805 | 2.559629 | 0.544922 | 0.045109 | 2.472487 | 0.587891 | 0.044812 | 2.475243 | 0.539062 | 1.000000 | 0.000012 | 1.000000 |
| V025_PROBE/world/2\|0 | -0.776487 | 1.690500 | 0.712418 | -0.342764 | 1.490562 | 0.696078 | 0.206123 | 1.222951 | 0.725490 | 1.000000 | 0.000009 | 1.000000 |
| V025_PROBE/world/2\|1 | -0.776487 | 1.690500 | 0.712418 | -0.342764 | 1.490562 | 0.696078 | 0.206123 | 1.222951 | 0.725490 | 1.000000 | 0.000009 | 1.000000 |
| V025_PROBE/world/2\|2 | -0.409995 | 3.123371 | 0.549323 | 0.287082 | 1.970030 | 0.595745 | 0.312000 | 1.952012 | 0.572534 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/2\|54 | 0.178000 | 1.344237 | 0.767974 | 0.048691 | 1.433989 | 0.647059 | 0.195840 | 1.321721 | 0.728758 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/2\|55 | -0.383094 | 1.712577 | 0.630682 | -0.371822 | 1.706083 | 0.627841 | -0.140544 | 1.574049 | 0.590909 | 1.000000 | 0.000011 | 1.000000 |
| V025_PROBE/world/2\|56 | 0.179637 | 2.904209 | 0.662626 | 0.144076 | 2.976611 | 0.610101 | 0.177265 | 2.927000 | 0.573737 | 1.000000 | 0.000012 | 1.000000 |
| V025_PROBE/world/2\|57 | -0.020896 | 2.664411 | 0.587459 | -0.058980 | 2.730223 | 0.544554 | 0.131441 | 2.461363 | 0.646865 | 1.000000 | 0.000013 | 1.000000 |
| V025_PROBE/world/2\|58 | -0.307090 | 1.697838 | 0.752688 | -0.282983 | 1.692990 | 0.739247 | 0.177625 | 1.373812 | 0.755376 | 1.000000 | 0.000009 | 1.000000 |
| V025_PROBE/world/2\|59 | 0.086856 | 3.260887 | 0.574689 | 0.040499 | 3.327778 | 0.614108 | 0.079491 | 3.231872 | 0.599585 | 1.000000 | 0.000015 | 1.000000 |
| V025_PROBE/world/2\|66 | 0.123353 | 1.445660 | 0.628931 | 0.170112 | 1.346715 | 0.657233 | 0.410762 | 1.150201 | 0.676101 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/2\|67 | 0.154372 | 1.433520 | 0.641745 | 0.199045 | 1.361850 | 0.694704 | 0.304014 | 1.280236 | 0.694704 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/2\|68 | 0.009612 | 2.584083 | 0.526978 | -0.096509 | 2.689045 | 0.537770 | 0.012938 | 2.519174 | 0.516187 | 1.000000 | 0.000012 | 1.000000 |
| V025_PROBE/world/2\|69 | 0.004364 | 4.298476 | 0.679487 | 0.075501 | 4.121523 | 0.618590 | 0.097334 | 4.136458 | 0.631410 | 1.000000 | 0.000015 | 1.000000 |
| V025_PROBE/world/2\|70 | -0.362782 | 2.317492 | 0.581662 | -0.227289 | 2.174859 | 0.659026 | 0.044700 | 1.912261 | 0.636103 | 1.000000 | 0.000010 | 1.000000 |
| V025_PROBE/world/2\|71 | -0.043634 | 2.874357 | 0.491049 | -0.276064 | 3.207244 | 0.542199 | -0.050095 | 2.838627 | 0.578005 | 1.000000 | 0.000014 | 1.000000 |

## Leave-one-step-out spread

Each range below is the min–max across the ten recomputations that omit one held-out `(world, anchor_index // 3)` block (three carrier anchors).

| scorer | explained variance | RMSE | pairwise ordering |
|---|---|---|---|
| Q1_ONLY | -0.013472–0.063069 | 2.120856–2.302457 | 0.614054–0.629904 |
| Q1_PLUS_CONTEXT | 0.056792–0.091429 | 2.029000–2.226371 | 0.615835–0.623479 |
| Q1_PLUS_CONTEXT_MINUS_EXTERNALITY | 0.148239–0.183379 | 1.927936–2.119142 | 0.624622–0.633288 |
| LEAKY_ORACLE | 1.000000–1.000000 | 0.000011–0.000011 | 1.000000–1.000000 |

## Context-coordinate attribution

The single predeclared attribution is held-out, no-refit, seeded cyclic permutation within each non-base candidate pool. Importance is the full-context ordering minus ordering after permuting that one coordinate. The 15 largest values are:

| resource index | coordinate | ordering importance | permuted ordering |
|---|---|---|---|
| 14 | affected_beam.min.occupancy_before | 0.101801 | 0.517435 |
| 21 | affected_beam.mean.occupancy_before | 0.100747 | 0.518489 |
| 9 | affected_beam.max.active_delta | 0.097409 | 0.521827 |
| 0 | affected_beam.sum.occupancy_before | 0.097058 | 0.522178 |
| 28 | pair[00].source_hash | 0.095740 | 0.523496 |
| 15 | affected_beam.min.occupancy_after | 0.094862 | 0.524374 |
| 19 | affected_beam.min.capacity_margin | 0.094862 | 0.524374 |
| 22 | affected_beam.mean.occupancy_after | 0.094598 | 0.524638 |
| 1 | affected_beam.sum.occupancy_after | 0.093456 | 0.525780 |
| 2 | affected_beam.sum.active_delta | 0.093105 | 0.526131 |
| 33 | pair[01].target_hash | 0.092578 | 0.526658 |
| 7 | affected_beam.max.occupancy_before | 0.092051 | 0.527185 |
| 23 | affected_beam.mean.active_delta | 0.090997 | 0.528239 |
| 12 | affected_beam.max.capacity_margin | 0.090821 | 0.528415 |
| 32 | pair[01].source_hash | 0.090294 | 0.528942 |

28 of 163 coordinates vary on held-out singleton actions; zero/negative importance means this fitted model did not rely beneficially on that coordinate under the declared perturbation.

## End-to-end selection effect

On the parametrisation comparison's same 30 held-out pools, its frozen one-step scorer formula (learned C1 per-user sum plus the already-frozen learned interaction head) has mean selection regret 3.618038 without context and 7.448846 with context. The change is +3.830808 normalized objective units (negative is better). The Q1-only route reproduces the prior ADDITIVE mean regret to 0.000e+00.

## Interpretation

The hypothesis is not supported as a material repair in this diagnostic. Admissible resource context changes held-out ordering by only -0.001581. The externality-removed arm reaches 0.629952, and the `NOT_DEPLOYABLE` defining-term oracle reaches 1.000000; the remaining gap is therefore not closed merely by exposing these encoded resource summaries to the fitted per-user head.

The fitted externality-removed arm is likewise not the earlier algebraic `0.902` oracle: it must estimate `own + energy + Φ` from Q1 plus admissible context. Its `0.629952` result says that removing externality from the fitting target does not make those remaining terms learnable enough in this estimator. The defining-term `LEAKY_ORACLE` verifies the upper bracket at `1.000000`, but is not deployable.

## What this did not reach

This does not authorize a production feature or interface change. It does not run the policy, estimate downstream policy value, search the full combinatorial action space, or establish an acceptance result. The end-to-end comparator is the parametrisation harness's one-step `C1 + Ψ` score, not the production three-route `C1 + C2 + Ψ` policy score; exact C2 labels are not part of these pools, so that full-policy effect was not reached. It does not test sizes 7–99, because they are absent from the frozen corpus. The mechanism rows still lack per-row served-count receipts, so no service-guard stratification was reached. The context arm tests a diagnostic singleton reconstruction; the current sealed C1 interface does not accept these coordinates, and the stored coalition-wide context cannot simply be wired into it. No confidence interval, repeated seed, alternate split, alternate estimator, or post-test tuning was performed.

## Reproduction

```bash
cd /home/sat/mcrl-v025-selector-ws

PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_c1_resource_context.py --phase build --anchor-part development --overwrite

PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_c1_resource_context.py --phase tune --overwrite

PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_c1_resource_context.py --phase build --anchor-part test --overwrite

PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_c1_resource_context.py --phase final
```

Machine-readable outputs: `.scratch/c1-resource-context/tuning.json`, `.scratch/c1-resource-context/results.json`, and the two authenticated unilateral-term caches in that directory.
