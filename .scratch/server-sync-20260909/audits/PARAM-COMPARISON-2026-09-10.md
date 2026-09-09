**DIRECT beats ADDITIVE on held-out mean selection regret: 2.426850 vs 3.618038, a reduction of 1.191188 normalized objective units (32.92%).**

# Parametrisation comparison — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`

No production training run and no policy run was performed. This is an offline fit on copies for measurement only. No sealed contract, target, scorer, schema digest, manifest, acceptance test, constant, threshold, sign, seed, horizon, price, service guard, or acceptance rule was modified.

## Experiment and corpus

Both arms predict the same normalized exact joint objective change, `ΔF/κ`. ADDITIVE fits a shared per-user unilateral-surplus head and a set-conditioned interaction-residual head, then sums them. DIRECT fits one set-conditioned head to `ΔF/κ`. All learned scalars use the same fixed-ReLU random-feature ridge family, split, seed, and grid.

The corpus combines the read-only mechanism corpus `/home/sat/mcrl-v025-coalgen-ws/artifacts/v025-mechanism-coalition-corpus-20260909-PILOT_NOT_CLAIM` with exact large S0 catalogue rows generated locally. The mechanism rows contribute sizes 2–6; the added rows contribute size 100. Selection is evaluated against the exact best row in each held-out anchor's same labelled pool. These are legal, exactly evaluated catalogue/mechanism proposals; no additional service-guard filter was invented. The pre-existing corpus does not carry a per-row served-count receipt, so this experiment neither reapplies nor alters that guard.

Exact-label audit: 11924 mechanism rows were checked against their Fraction numerator/denominator receipts; maximum encoded residual `0.000e+00`. The family-index SHA-256 is `b8f55dc15e91155a32aa706a4908aff3bf6ee281565f9ca0644d76679e7da047`. All 300 large rows passed `joint = Σ exact singleton differences + exact interaction` and the `k+2` distinct-evaluation receipt. Their baseline, singletons, and joint were all prepared through one fresh `evaluate_many` path. The pilot fallback labels were never read as targets: source shards supplied Q1 features only.

The split was frozen before fitting: seed 20260910, three-anchor blocks, independently shuffled within each world; 90 train, 30 validation, and 30 test anchors. A loader smoke test had opened the initially assigned 30 test anchors before fitting; no model or outcome summary used them, but they were quarantined rather than claimed as untouched. The final test set was drawn from previously unopened blocks and its shards and large rows were loaded only after hyperparameters were selected and recorded in `.scratch/parametrisation-comparison/tuning.json`.

### Corpus size distribution

| partition | anchors | rows | size histogram |
|---|---|---|---|
| train | 90 | 6167 | `{'100': 180, '2': 3493, '3': 2360, '4': 120, '5': 12, '6': 2}` |
| validation | 30 | 2064 | `{'100': 60, '2': 1135, '3': 795, '4': 60, '5': 12, '6': 2}` |
| test | 30 | 2022 | `{'100': 60, '2': 1138, '3': 772, '4': 45, '5': 6, '6': 1}` |
| all | 150 | 10253 | `{'100': 300, '2': 5766, '3': 3927, '4': 225, '5': 30, '6': 5}` |

## Estimator and feature control

Estimator: `standardized fixed-ReLU-random-feature ridge with raw linear skip`. Grid: `[{'ridge': 1e-06, 'width': 64}, {'ridge': 0.0001, 'width': 64}, {'ridge': 0.01, 'width': 64}, {'ridge': 1e-06, 'width': 128}, {'ridge': 0.0001, 'width': 128}, {'ridge': 0.01, 'width': 128}]`. Each component chose hyperparameters only by validation RMSE; final refits used train+validation.

| component | width | ridge | validation RMSE |
|---|---|---|---|
| direct | 128 | 0.01 | 5.776450 |
| interaction | 64 | 0.01 | 7.018252 |
| member_only_interaction_ablation | 128 | 0.01 | 6.602077 |
| per_user_additive | 64 | 0.01 | 11.417979 |

Feature information is matched at the arm level. DIRECT and ADDITIVE's interaction head both receive the same 384-D vector: the existing 240-D invariant set context plus the same 144-D summed per-user deviation bank used by the additive head. The per-user head itself does not see 163 resource-context coordinates (affected-beam pooling, pairwise cross-gains, and globals); ADDITIVE's interaction head does. That is the sealed decomposition's architecture, not an information advantage over DIRECT.

The predeclared member-only ablation quantifies those resource coordinates:

| quantity | full context | member-only | full minus member-only |
|---|---|---|---|
| interaction RMSE | 9.180977 | 9.003617 | 0.177361 |
| ADDITIVE mean selection regret | 3.618038 | 4.684871 | -1.066833 |

## Held-out selection regret

| predictor | mean | median | p95 | choice differs | selection sizes |
|---|---|---|---|---|---|
| CONSTANT | 45.345240 | 41.175600 | 117.086078 | 83.33% | `{'100': 14, '2': 7, '3': 9}` |
| ADDITIVE | 3.618038 | 0.000000 | 19.824570 | 23.33% | `{'100': 28, '3': 2}` |
| DIRECT | 2.426850 | 0.000000 | 10.476772 | 30.00% | `{'100': 27, '3': 2, '4': 1}` |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 9.042506 | 0.000000 | 46.233489 | 46.67% | `{'100': 21, '2': 4, '3': 3, '4': 2}` |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 9.647125 | 0.000000 | 42.838154 | 43.33% | `{'100': 28, '2': 1, '4': 1}` |
| ORACLE | 0.000000 | 0.000000 | 0.000000 | 0.00% | `{'100': 26, '2': 1, '3': 3}` |

Exact-winner size distribution: `{'100': 26, '2': 1, '3': 3}`.

### Selection regret by selected coalition size

| predictor | selected k | n | mean | median | p95 | differs |
|---|---|---|---|---|---|---|
| CONSTANT | 2 | 7 | 78.526410 | 107.271365 | 123.267877 | 100.00% |
| CONSTANT | 3 | 9 | 61.407090 | 56.976756 | 111.775230 | 100.00% |
| CONSTANT | 100 | 14 | 18.429179 | 11.286189 | 48.982405 | 64.29% |
| ADDITIVE | 3 | 2 | 4.598220 | 4.598220 | 8.736618 | 50.00% |
| ADDITIVE | 100 | 28 | 3.548025 | 0.000000 | 20.541614 | 21.43% |
| DIRECT | 3 | 2 | 10.386245 | 10.386245 | 10.481418 | 100.00% |
| DIRECT | 4 | 1 | 6.770047 | 6.770047 | 6.770047 | 100.00% |
| DIRECT | 100 | 27 | 1.676406 | 0.000000 | 10.359134 | 22.22% |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 2 | 4 | 14.568953 | 17.235220 | 22.216857 | 100.00% |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 3 | 3 | 18.089485 | 2.917927 | 45.127481 | 100.00% |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 4 | 2 | 21.545987 | 21.545987 | 34.844332 | 100.00% |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 100 | 21 | 5.506617 | 0.000000 | 41.853115 | 23.81% |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 2 | 1 | 16.623675 | 16.623675 | 16.623675 | 100.00% |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 4 | 1 | 69.030189 | 69.030189 | 69.030189 | 100.00% |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 100 | 28 | 7.277138 | 0.000000 | 37.051260 | 39.29% |
| ORACLE | 2 | 1 | 0.000000 | 0.000000 | 0.000000 | 0.00% |
| ORACLE | 3 | 3 | 0.000000 | 0.000000 | 0.000000 | 0.00% |
| ORACLE | 100 | 26 | 0.000000 | 0.000000 | 0.000000 | 0.00% |

## Held-out value error

| predictor | explained variance | RMSE |
|---|---|---|
| CONSTANT | 0.000000 | 12.711269 |
| ADDITIVE | 0.653592 | 7.490230 |
| DIRECT | 0.802729 | 5.646332 |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 0.481958 | 9.180977 |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 0.089163 | 12.184264 |
| ORACLE | 1.000000 | 0.000000 |

### Value error by coalition size

| predictor | k | n | explained variance | RMSE |
|---|---|---|---|---|
| CONSTANT | 2 | 1138 | 0.000000 | 4.947524 |
| CONSTANT | 3 | 772 | 0.000000 | 4.936755 |
| CONSTANT | 4 | 45 | -0.000000 | 6.356266 |
| CONSTANT | 5 | 6 | 0.000000 | 8.361220 |
| CONSTANT | 6 | 1 | N/A | 10.842442 |
| CONSTANT | 100 | 60 | 0.000000 | 68.029590 |
| ADDITIVE | 2 | 1138 | -0.008948 | 4.327964 |
| ADDITIVE | 3 | 772 | -0.146325 | 5.267059 |
| ADDITIVE | 4 | 45 | -0.278301 | 6.648508 |
| ADDITIVE | 5 | 6 | -59.311009 | 8.803597 |
| ADDITIVE | 6 | 1 | N/A | 0.690140 |
| ADDITIVE | 100 | 60 | 0.401437 | 33.727782 |
| DIRECT | 2 | 1138 | 0.239728 | 3.742834 |
| DIRECT | 3 | 772 | 0.179113 | 4.460008 |
| DIRECT | 4 | 45 | 0.024331 | 5.803845 |
| DIRECT | 5 | 6 | -14.100412 | 4.290514 |
| DIRECT | 6 | 1 | N/A | 3.148543 |
| DIRECT | 100 | 60 | 0.725111 | 22.923406 |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 2 | 1138 | 0.693353 | 2.406341 |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 3 | 772 | 0.620477 | 3.074945 |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 4 | 45 | 0.359484 | 4.807163 |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 5 | 6 | -58.801111 | 8.501567 |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 6 | 1 | N/A | 5.009783 |
| EXACT_ADDITIVE_LEARNED_INTERACTION | 100 | 60 | -0.332848 | 50.834270 |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 2 | 1138 | -0.313830 | 4.977581 |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 3 | 772 | -0.763610 | 6.550148 |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 4 | 45 | 0.015005 | 5.876491 |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 5 | 6 | -1.962467 | 5.095693 |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 6 | 1 | N/A | 5.699923 |
| LEARNED_ADDITIVE_EXACT_INTERACTION | 100 | 60 | -0.987985 | 62.864760 |
| ORACLE | 2 | 1138 | 1.000000 | 0.000000 |
| ORACLE | 3 | 772 | 1.000000 | 0.000000 |
| ORACLE | 4 | 45 | 1.000000 | 0.000000 |
| ORACLE | 5 | 6 | 1.000000 | 0.000000 |
| ORACLE | 6 | 1 | N/A | 0.000000 |
| ORACLE | 100 | 60 | 1.000000 | 0.000000 |

## ADDITIVE realised amplification

On held-out rows, additive-part error RMSE is 12.184264; interaction-part error RMSE is 9.180977; their Pearson correlation is -0.787923. Opposite error signs occur in 68.00% of rows. The combined-error RMSE is 7.490230, or 0.490968 times the root-sum-square component error. A value below one means realised error cancellation.

RMS-relative error is 0.625207 for the additive part, 0.741044 for the interaction part, and 0.554501 for their sum. Thus the realised relative error of the sum is 0.886909 times the additive part's relative error. Median rowwise absolute relative errors (excluding exact magnitudes <=1e-8) are 1.036726, 1.544812, and 0.856719, respectively.

The component errors cancel materially; the review's conditioning objection is weaker on these realised fits than an independence assumption would imply.

## Out-of-support behaviour

Final training size support was `[2, 3, 4, 5, 6, 100]`.

| arm | OOS selections | fraction | selected-value RMSE there | mean regret there | OOS test-row RMSE |
|---|---|---|---|---|---|
| ADDITIVE | 0 | 0.00% | N/A | N/A | N/A |
| DIRECT | 0 | 0.00% | N/A | N/A | N/A |

## Interpretation

DIRECT wins the declared decision metric: mean regret falls by 1.191188 normalized objective units (32.92% relative). Its exact-winner mismatch rate is nevertheless higher (30.00% versus 23.33%); the win is a reduction in the severity of mistakes, not their frequency. This supports keeping the reformulation proposal open for a sealed-contract decision; it does not itself authorize that change.

The oracle-isolation controls do not support blaming only one half. With exact per-user terms and only the interaction learned, mean regret is 9.042506; with exact interaction and only the per-user terms learned, it is 9.647125. The learned per-user half is slightly worse by 0.604618, and its value RMSE is also larger (12.184264 versus 9.180977), but both isolated controls are worse than the fully learned ADDITIVE arm because the two realised component errors strongly cancel.

The 163 resource-context coordinates make interaction RMSE worse by 0.177361, while improving ADDITIVE mean selection regret by 1.066833. They therefore add decision-relevant ranking information in this fit even though they do not improve pointwise interaction calibration.

The exact oracle brackets zero regret and zero value error; the constant predictor supplies the non-informative bracket on the same held-out pools.

## What this did not reach

This is not a production training run, not a policy run, and not an acceptance test. It does not estimate downstream policy value. The held-out pools are the exact labelled mechanism/S0 candidates available here, not the full combinatorial action space. The mechanism corpus lacks per-row served-count receipts, so the experiment cannot stratify by whether that sealed guard would bind; it makes no change to the guard. Coalition sizes 7–99 are absent, so the size curve is observed at 2–6 and 100 rather than continuously.

## Reproduction

```bash
cd /home/sat/mcrl-v025-selector-ws

# Build development labels only; test anchors remain unevaluated.
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/build_parametrisation_comparison_large_rows.py \
  --anchor-part development \
  --output .scratch/parametrisation-comparison/s0-large-development.jsonl

# Freeze hyperparameters using train/validation only.
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_target_parametrisations.py --phase tune

# Only now build held-out large rows and perform the final audit/refit/test.
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/build_parametrisation_comparison_large_rows.py \
  --anchor-part test \
  --output .scratch/parametrisation-comparison/s0-large-test.jsonl

PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_target_parametrisations.py --phase final
```

Machine-readable outputs: `.scratch/parametrisation-comparison/tuning.json` and `.scratch/parametrisation-comparison/results.json`.
