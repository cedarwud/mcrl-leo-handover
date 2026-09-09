**Test 1: with `Psi_hat` set exactly to zero, the selector still chose 100 users in 10/10 anchor-seed decisions.**

**A small feasible coalition does strictly beat the grand coalition:** at physical anchor 3, the best feasible size-2 coalition scores `65.249` exactly versus `7.217` for the grand coalition. This occurs for both learner seeds, hence 2/10 anchor-seed decisions. The universal size-100 symptom is therefore wrong, although the grand coalition is genuinely exact-best among the tested small sets at anchors 0, 1, and 4; anchor 2 has no feasible small candidate but the empty set (`0`) beats the harmful grand coalition (`-31.955`).

# Selector diagnosis — 2026-09-09

`DIAGNOSTIC_NOT_CLAIM`. This is quarantined engineering evidence. It does not change or select a threshold, sign, seed, horizon, price, service guard, or acceptance rule. No training was run.

## Bottom line

This is not an interaction-head explanation and not a search/tie/default explanation. It is principally a learned-score failure in the singleton/additive path, with a severe epoch-200 interaction error that amplifies but is not necessary for the size-100 choice.

- Removing C3 leaves the symptom unchanged: 10/10 size 100.
- The reconstructed epoch-200 score path reproduces all 10/10 original FULL choices exactly, so this diagnosis is on the observed path, not a nearby implementation.
- On the fixed panels, the model-score selector picks size 100 in 10/10. The same deterministic ranking rule fed exact scores picks the grand coalition in 6/10, the empty set in 2/10, and size 2 in 2/10. It never picks an inferior grand coalition when given exact scores. Stable argmax/tie handling is therefore behaving correctly on the panel.
- Every observed grand coalition is nominally valid and passes the sealed served-count guard. A mask or guard mistake does not explain why those grand candidates win.
- The pilot selection adapter nevertheless has a separate defect: `_select_for_anchor` does not invoke the production `ProfileSelector` and does not apply its joint-legality or service-guard callbacks. Its variable `legal_catalogue` only checks dictionary membership. That omission did not cause these ten grand choices—the winners themselves passed both checks—but the pilot path should not be treated as evidence that production masks were exercised.
- The inherited epoch-200 C3 head has a large positive size error: grand-coalition exact `Psi` averages `-440.079`, while `Psi_hat` averages `+2206.918`. However, the zero-C3 intervention proves that correcting only this head would not remove the all-users size symptom.

## 1. Zero-interaction intervention

The diagnostic used the original world (`V025_PROBE/world/3`), steps 0–4, nearest-eligible carrier, two learner seeds, epoch-200 FULL checkpoints, and the original bounded catalogue. Only the interaction callback was replaced with the constant zero.

| Result | Count |
|---|---:|
| Zero-C3 choices of size 100 | 10/10 |
| Same exact configuration as original FULL | 5/10 |
| Different configuration, still size 100 | 5/10 |

The seed-dependent zero-C3 scores and differing grand configurations rule out an unconditional grand-coalition default. The C1+C2 learned singleton sum alone ranks a grand candidate first on every decision.

## 2. Exact fixed-candidate panels

Each physical anchor panel contains the empty set, the exact-best valid catalogue coalition at every available size 2–6, and the observed grand coalition. Feasibility below includes nominal validity and the sealed no-served-count-decrease guard. Exact scores are normalized `F(A)-F(empty)` values at the same nominal boundary used by the pilot evaluator.

| Anchor | Best feasible small | Exact small | Exact grand | Grand passes guard | Exact panel winner | Model panel winner |
|---:|---:|---:|---:|:---:|---:|---:|
| 0 | 2 | 20.793 | 35.379 | yes | 100 | 100 |
| 1 | none | — | 85.004 | yes | 100 | 100 |
| 2 | none | — | -31.955 | yes | 0 | 100 |
| 3 | 2 | 65.249 | 7.217 | yes | 2 | 100 |
| 4 | 3 | 2.086 | 104.524 | yes | 100 | 100 |

The exact rows are duplicated across the two learner seeds, producing the requested ten comparisons. At anchors 1 and 2, all 208 valid small catalogue candidates fail the service guard. At anchor 4, only one small candidate passes it. Unconstrained best-small scores at anchors 1, 2, and 4 are `-11.017`, `-3.397`, and `5.244`, respectively; all three fail the guard.

The mechanical selector verdict is clean: exact argmax chooses the exact winner in every panel. There is no exact-score assembly, feasibility, masking, or tie failure that promotes an inferior grand coalition on these panels. The divergence occurs before argmax, in the values supplied to it.

## 3. Score components by size and checkpoint

There is no standalone cost subtraction in the pilot's learned selector. It sums learned C1 and C2 deltas and adds `Psi_hat`; the energy/QoS cost is embedded in the C1 training label. To avoid double-counting, the tables use both exact identities in parallel:

`exact final = exact singleton sum + exact Psi = delta_bits/kappa - cost`, where `cost = eta*delta_energy/kappa - delta_Phi`.

Epoch-200 means over the five physical panels and two learner seeds:

| k | n | Exact singleton | Exact `Psi` | Cost | Exact final | Learned singleton | `Psi_hat` | Model final |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 0 | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 2 | 10 | 19.770 | -4.396 | -8.819 | 15.374 | 2.120 | 2.519 | 4.639 |
| 3 | 10 | 16.687 | -5.583 | -4.142 | 11.104 | 3.398 | 6.238 | 9.636 |
| 4 | 10 | 17.241 | -9.900 | -1.773 | 7.340 | 5.513 | -3.935 | 1.578 |
| 5 | 10 | 23.936 | -14.322 | -4.072 | 9.614 | 5.054 | 2.264 | 7.318 |
| 6 | 10 | 26.329 | -22.462 | -0.297 | 3.867 | 4.745 | 4.303 | 9.048 |
| 100 | 10 | 480.113 | -440.079 | 12.143 | 40.034 | 106.501 | 2206.918 | 2313.418 |

The exact grand score is modest because large singleton and interaction terms cancel. The learned path does not reproduce that cancellation. Even without `Psi_hat`, its grand singleton sum (`106.501` on this panel average) remains much larger than the small-coalition learned sums.

Grand-coalition checkpoint trend; the exact columns are checkpoint-invariant and are shown to expose scale and sign drift:

| Epoch | Exact singleton | Exact `Psi` | Cost | Exact final | Learned singleton | `Psi_hat` | Model final |
|--:|--:|--:|--:|--:|--:|--:|--:|
| 100 | 480.113 | -440.079 | 12.143 | 40.034 | 114.267 | 53.370 | 167.638 |
| 200 | 480.113 | -440.079 | 12.143 | 40.034 | 106.501 | 2206.918 | 2313.418 |
| 300 | 480.113 | -440.079 | 12.143 | 40.034 | 102.332 | 2317.906 | 2420.238 |
| 400 | 480.113 | -440.079 | 12.143 | 40.034 | 99.505 | 1904.999 | 2004.504 |
| 500 | 480.113 | -440.079 | 12.143 | 40.034 | 97.793 | 1167.651 | 1265.445 |
| 600 | 480.113 | -440.079 | 12.143 | 40.034 | 96.298 | 20.853 | 117.151 |
| 700 | 480.113 | -440.079 | 12.143 | 40.034 | 95.569 | -957.422 | -861.853 |
| 800 | 480.113 | -440.079 | 12.143 | 40.034 | 94.224 | -1812.470 | -1718.247 |
| 1000 | 480.113 | -440.079 | 12.143 | 40.034 | 92.410 | -3278.197 | -3185.787 |
| 1400 | 480.113 | -440.079 | 12.143 | 40.034 | 89.864 | -5735.339 | -5645.475 |
| 2000 | 480.113 | -440.079 | 12.143 | 40.034 | 84.718 | -9421.330 | -9336.612 |

This is not early-epoch shrinkage. It is a transient positive C3 overshoot peaking around epochs 200–300, followed by a sign reversal and growing negative magnitude. The additive grand score declines slowly but remains positive. All 20 checkpoints and all panel sizes are retained in `.scratch/selector-diagnosis/full.json`.

## 4. Bias accumulation

At epoch 200, the mean signed interaction error divided by the number of pairs is `+2.637777` normalized score units per pair over 60 panel observations. If treated as a constant pair bias, it contributes `+2.638` at size 2 and `+13056.995` at size 100, so that bias alone favors the largest coalition.

| k | Mean signed error per pair | Implied total interaction error |
|--:|--:|--:|
| 2 | 6.914545 | 6.915 |
| 3 | 3.940245 | 11.821 |
| 4 | 0.994182 | 5.965 |
| 5 | 1.658608 | 16.586 |
| 6 | 1.784335 | 26.765 |
| 100 | 0.534747 | 2646.997 |

The head is set-conditioned, not a literal sum of pair predictions, so the constant-bias extrapolation is diagnostic rather than a fitted model. The observed grand error itself is still decisive: `0.534747 * 4950 = 2646.997`. Empty/singleton hard zeros do not constrain this error.

## 5. No-op invariant

The physical invariant passes on all five anchors. Adding a no-op user to an exact coalition identity leaves exact `Psi` bit-for-bit equal, and all 4,905 catalogue rows report a `changed_users` count equal to the actual mapping differences.

| Anchor | Probe k | Exact physical equal | `Psi_hat` before | `Psi_hat` after illegal no-op insertion | Catalogue count mismatches |
|---:|---:|:---:|---:|---:|---:|
| 0 | 3 | yes | -25.531 | -39.133 | 0 |
| 1 | 3 | yes | -13.990 | -19.419 | 0 |
| 2 | 3 | yes | 15.098 | 14.060 | 0 |
| 3 | 3 | yes | 48.703 | 49.382 | 0 |
| 4 | 3 | yes | 5.614 | -1.578 | 0 |

`Psi_hat` itself is not dummy-user invariant if handed an illegal context containing an unchanged member. That is a robustness gap, but it is not active here: `_coalition_context` constructs members strictly from mapping differences, and the catalogue audit found no mismatch. Therefore the no-op bookkeeping defect does not explain the observed size preference.

## 6. Label evaluation accounting and estimand

The code evaluates exactly `k + 2` distinct configurations: reference, one unilateral configuration for each of the `k` members, and the joint configuration. A size-3 probe issued five distinct `evaluate` calls on every anchor. Because the evaluator cache had already been warmed by the exact panel, these calls caused zero new physical boundary evaluations; this demonstrates how physical-call telemetry can be below `k + 2` without missing a label term.

All 180 inherited full-run training rows have `k=2`; consequently each one happens to require four configurations. The five-row minimal copy also contains only pairs. Four is an observed consequence of that training-row support, not the implementation's general accounting rule.

The label subtracts exact evaluator singletons, not learned C1/C2 predictions. `build_coalition_row` receives exact reference, unilateral, and coalition `NetworkOutcome` values and computes the identity through `coalition_identity`. The C3 estimand is therefore exact `Psi`, not `Psi - sum_i eps_i`.

## 7. Higher-order residual `R3`

For the exact-best valid size-3 through size-6 panel candidates, all constituent pair configurations were evaluated through the same cache and score identity. `R3(A) = Psi(A) - sum_pairs Psi(pair)` is material in every tested row: median `|R3|/|Psi| = 1.324`, range `0.299–2.240` across 20 coalitions.

| Anchor | k | Exact `Psi(A)` | Sum pair `Psi` | `R3(A)` | `|R3|/|Psi|` |
|---:|---:|---:|---:|---:|---:|
| 0 | 3 | -12.283 | -28.373 | 16.089 | 1.310 |
| 0 | 4 | -29.712 | -62.242 | 32.530 | 1.095 |
| 0 | 5 | -37.017 | -96.682 | 59.665 | 1.612 |
| 0 | 6 | -46.755 | -151.485 | 104.730 | 2.240 |
| 1 | 3 | 50.438 | 71.174 | -20.736 | 0.411 |
| 1 | 4 | 73.034 | 139.411 | -66.377 | 0.909 |
| 1 | 5 | 94.488 | 236.573 | -142.084 | 1.504 |
| 1 | 6 | 115.509 | 355.624 | -240.114 | 2.079 |
| 2 | 3 | 27.057 | 39.770 | -12.713 | 0.470 |
| 2 | 4 | 40.458 | 74.801 | -34.343 | 0.849 |
| 2 | 5 | 57.546 | 134.604 | -77.058 | 1.339 |
| 2 | 6 | 62.452 | 190.349 | -127.896 | 2.048 |
| 3 | 3 | -109.534 | -163.584 | 54.051 | 0.493 |
| 3 | 4 | -152.467 | -314.104 | 161.636 | 1.060 |
| 3 | 5 | -208.576 | -546.111 | 337.536 | 1.618 |
| 3 | 6 | -267.608 | -839.711 | 572.103 | 2.138 |
| 4 | 3 | 16.409 | 21.308 | -4.899 | 0.299 |
| 4 | 4 | 19.186 | 31.764 | -12.578 | 0.656 |
| 4 | 5 | 21.949 | 55.533 | -33.583 | 1.530 |
| 4 | 6 | 24.091 | 67.146 | -43.054 | 1.787 |

Any pairwise-only interaction model is therefore misspecified on these cached values. The inherited model is nominally a set head, so this result does not prove it is pairwise-only; it does prove that a pair-only replacement would be invalid.

## 8. The scalar-collapse assumption

The inherited checkpoints do use the old 117-D aggregate encoder: 38-D member rows are reduced by sum/max, seven beam features by sum/max/min/mean, and physical-ID/cross-gain relation rows by sum/max into six scalars, followed by six global scalars and coalition size. The current source's padded top-32 relation block is a later 240-D schema and is incompatible with these checkpoints.

The aggregate collapse is real and can contribute to misspecification. It is not the cause of the all-100 symptom, because C3 can be removed completely without changing any selected coalition size. The diagnostic reconstructs the 117-D path and exactly reproduces all ten original FULL configuration IDs before drawing model-score conclusions.

## Causal disposition

| Explanation | Verdict | Evidence |
|---|---|---|
| C3 feature collapse causes size 100 | Rejected as necessary cause | `Psi_hat=0` still gives 10/10 size 100 |
| Learned C3 is healthy/irrelevant numerically | Rejected | epoch-200 grand `Psi` error is +2646.997 on average |
| Learned singleton path drives the symptom | Supported | zero-C3 C1+C2 argmax is size 100 in 10/10 |
| Search/tie/default picks a non-argmax | Rejected on fixed panels | exact-score ranking returns exact winner; model-score ranking returns model winner; no default signature |
| Feasibility/mask makes grand win | Rejected for observed winners | all ten grand winners are valid and pass the guard |
| Pilot exercised production masks/guard | Rejected | `_select_for_anchor` bypasses `ProfileSelector` and omits callbacks |
| No-op bookkeeping causes size bias | Rejected on observed path | exact invariant 5/5; 0/4,905 changed-count mismatches |
| Four evaluations suffice generally | Rejected | implementation and probes use `k+2`; four only because all training rows are pairs |
| C3 target contains learned singleton error | Rejected | singleton outcomes used in the label are exact evaluator outcomes |
| Pairwise interaction is structurally sufficient | Rejected | cached `R3` is material in 20/20 size-3–6 panels |
| Symptom is entirely a non-problem | Rejected | feasible size 2 beats grand at anchor 3; empty beats harmful grand at anchor 2 |

## Reproduction

One process, no training:

```bash
PYTHONPATH=src nice -n 10 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/diagnose_v025_selector.py --phase all
```

Machine-readable evidence is in `.scratch/selector-diagnosis/zero-c3.json` and `.scratch/selector-diagnosis/full.json`. The script and report are confined to `/home/sat/mcrl-v025-selector-ws`; no source or artifact in the pilot workspace was modified.

## Verification caveat

The machine-readable diagnostic assertions pass: 10 zero-C3 rows, 10/10 original-model reproductions, 2 small-over-grand comparisons, five physical no-op invariants, five `k+2` accounting probes, and 20 `R3` rows.

A targeted check of the existing Stage-C acceptance suite produced `T2: PASS` and `T1: FAIL`. The failure is outside the diagnostic changes: the checked-in v2 uncapped decomposition rejects T1's older capped-subset fixture (`coalition context is absent from the sealed capped decomposition`). The baseline commit already contains both sides of that inconsistency, and this task does not alter either file.

The requested initialized baseline is commit `7fc615b` (`pilot snapshot for selector diagnosis`). The managed environment mounts `.git` read-only, so the completed diagnostic files remain uncommitted; `git commit` failed while creating `.git/index.lock` with `Read-only file system`.
