You are independently checking a diagnostic number that a project is about to make a decision on. Work in the current directory. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No training run, no policy run, no physics evaluation. Change no threshold, sign, seed, horizon, price, guard or acceptance rule, and do not touch any sealed artefact or the `PILOT_PRIMITIVE_SOURCE_FALLBACK` flag.

# Background

A learner in this project has two scalar heads. Each receives one fixed-length numeric feature vector — 16 values for the first, 22 for the second — and nothing else. Their regression targets are exact quantities computed by the simulator's evaluator: `c1_difference_surplus` and `c2_persistence_forecast`, defined in the stage-C source under `src/mcrl/stagec_v025/`.

A prior diagnostic estimated how much of those targets the feature vectors can explain, held out. It reported held-out explained variance of `-0.3355476799` for the first head and `+0.2106516781` for the second, using inverse-distance k-nearest-neighbour regression with k chosen from {1,3,7,15,31} on a validation split (k=31 selected), on 26,345 valid non-reference rows from 30 source anchors, split by whole physical step: train {1,2,4,6,7,8,9}, validate {5}, test {0,3}, 5,280 held-out rows, seed 20260909.

Its implementation is `scripts/diagnose_v025_c1c2_sufficiency.py` and its report `C1C2-SUFFICIENCY-2026-09-09.md`, both in `/home/sat/mcrl-v025-c1c2suff-ws` (another agent is writing in that workspace right now — read from it, never write to it, and copy anything you need here first). The rows are under `artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/rows/world-1`; locate a readable copy.

# What you must determine

**Do those feature vectors carry usable predictive information about their targets, or not?**

A negative explained variance means the predictor did worse than predicting the training mean. That can happen because the features are genuinely uninformative, or because the estimator was a poor fit for the data — k-nearest-neighbour in 16 standardised dimensions, trained on seven physical steps, evaluated under a split that is itself a distributional shift, is not a strong estimator. Separate those two explanations.

Build your own evaluation. You may reuse the prior script to replicate its number, but do not simply rerun it and stop.

Requirements:
- First replicate both published numbers. If you cannot reproduce them, that is the headline; say so and stop there.
- Then fit a set of estimators you declare in writing **before** running any of them, including a constant-predictor reference so the explained-variance zero point is anchored, at least one linear model, and at least one flexible model. Report every estimator you declared, including the ones that did worse. Do not add an estimator after seeing results; if you want one you did not declare, you may not have it.
- Choose any hyperparameter on the validation split only, never on the test steps.
- Check whether the result is a property of one unlucky held-out step: report per-test-step values separately, and a leave-one-step-out rotation over all ten steps with its spread.
- Quantify how much target variance is structurally unreachable, using groups of byte-identical feature vectors that carry different exact targets. If a route has no such duplicates, report that; it is the answer for that route.

# Verdict

End with one of exactly these, separately for each head, justified in two sentences:
- `FEATURES_UNINFORMATIVE` — nothing on your declared list beats the constant predictor;
- `ESTIMATOR_ARTEFACT` — something on your declared list clearly beats the constant predictor, so the published negative value understates what the features carry;
- `INDETERMINATE` — your estimators disagree, or the rotation is too unstable to call.

Report what you find. Both outcomes are useful and neither is preferred; a wrong number corrected is worth more than a number confirmed.

Write `C1C2-ESTIMATOR-INDEPENDENT-2026-09-10.md` in this workspace root and print it in full as your final message, leading with the two verdicts on one line.
