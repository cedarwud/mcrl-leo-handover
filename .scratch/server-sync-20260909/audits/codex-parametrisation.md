Workspace: the current directory, `/home/sat/mcrl-v025-selector-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment. Read-only access to sibling `mcrl-v025-*-ws` workspaces is fine; never write into them.

`DIAGNOSTIC_NOT_CLAIM`. No production training run and no policy run. **Nothing sealed may be modified**: not the contract, not `targets.py`, not the deployed scorer, not any schema digest, manifest or acceptance test. Everything below is fitted on copies for measurement only. Do not change any constant, threshold, sign, seed, horizon, price, service guard or acceptance rule.

# Why this exists

A design review in this workspace produced `C1C2-TARGET-DESIGN-2026-09-10.md`. Read it first. Its central finding is that the sealed additive parametrisation is ill-conditioned: at coalition size 100 the additive term is `+480.113` and the interaction term `−440.079`, producing `+40.034`, so any relative error in either is amplified roughly tenfold at the decision.

It proposes ranking on a single set-conditioned prediction of the joint objective change instead of on a sum of per-user deviations plus an interaction correction.

**That proposal has not been measured. Measuring it is this task.** A decision to open a sealed contract should not rest on an argument alone.

# The experiment, fully declared before you run anything

Two target parametrisations of the same quantity, fitted on the same rows, the same features, the same estimator family, the same split, the same seed:

- **`ADDITIVE`** — the sealed form. Fit a per-user head for the unilateral deviation surplus and a set head for the interaction residual; score a coalition as the sum of its per-user predictions plus the predicted interaction.
- **`DIRECT`** — fit one set-conditioned head for the joint objective change itself; score a coalition as that prediction.

Use the exact labels, never the pilot surrogate. `scripts/run_v025_pilot_c3.py:89` sets a fallback that substitutes a per-user monotone squash carrying no coupled content; rows built through that path are not the production estimand and must not be used for either arm. State which corpus you used and how you verified its labels are exact.

Both arms must use the same feature information. If the set head has access to context the per-user head does not, say so explicitly and quantify what that adds, because otherwise the comparison is confounded.

## Metrics, declared now

Report all of these for both arms. Do not add a metric after seeing results.

1. **Selection regret on held-out anchors** — the exact objective value of the chosen coalition against the exact best in the same labelled pool. This is the decision-level metric and it is the one that matters. Report mean, median, p95, and the fraction of anchors where the choice differs from the exact winner.
2. **Value error** — held-out explained variance and RMSE against the exact joint objective change.
3. **Both broken down by coalition size**, because the cancellation grows with size. Report the size distribution of the corpus and of the selections.
4. **For `ADDITIVE` only, the realised amplification.** Measure the error of the additive part, the error of the interaction part, and **the correlation between them**. Then report the realised relative error of their sum against the relative error of the additive part. The review's argument assumes the errors do not cancel; if they largely do, the conditioning objection is weaker than stated and you must say so.
5. **Out-of-support behaviour.** Report, for each arm, how often the selected coalition size lies outside the training support, and the error there separately.

## Controls you must include

- A **constant predictor** and an **exact-label oracle** on the same pools, to bracket both arms.
- **`ADDITIVE` with exact per-user terms and only the interaction learned**, and **`ADDITIVE` with exact interaction and only the per-user terms learned**. These two isolate which half carries the damage.

# Rules

- Declare the estimator family and any hyperparameter grid **before** fitting, choose hyperparameters on a validation split only, and never touch the test anchors until the end.
- **Do not tune either arm to win.** If `DIRECT` does not beat `ADDITIVE` on selection regret, say so in the first line. That result would close the reformulation proposal and save the project from opening a sealed contract for nothing, which is worth more than confirming the review.
- Every number reproducible from a script left here, with exact command lines.
- Say plainly what you did not reach.

Write `PARAMETRISATION-COMPARISON-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether `DIRECT` beats `ADDITIVE` on held-out selection regret, and by how much.
