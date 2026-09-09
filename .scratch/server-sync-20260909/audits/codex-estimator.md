Workspace: /home/sat/mcrl-v025-replay-ws (its previous job finished; reuse it). Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify /home/sat/mcrl-leo-handover or its venv.

# Task: audit one diagnostic number before the project acts on it

`DIAGNOSTIC_NOT_CLAIM`. No training run, no policy run, no physics evaluation. This is an estimator audit on rows that already exist.

## The number under audit
A prior diagnostic (`/home/sat/mcrl-v025-c1c2suff-ws/C1C2-SUFFICIENCY-2026-09-09.md`, and its script `scripts/diagnose_v025_c1c2_sufficiency.py`) reported held-out explained variance for a scalar head's own encoded features:

- C1 route: EV = -0.3355476799, RMSE 3.4683937281, target variance 8.3419683433
- C2 route: EV = +0.2106516781, RMSE 3.3856461561, target variance 14.3690049981

Estimator: standardized inverse-distance k-nearest-neighbour regression, k chosen from {1,3,7,15,31} on a validation split, k=31 selected for both. Data: 26,345 valid non-reference rows from 30 source anchors, split by whole physical step — train {1,2,4,6,7,8,9}, validate {5}, test {0,3}, 5,280 held-out rows, seed 20260909.

The project has taken the negative C1 number to mean the encoded features carry no predictive value for that target. **That inference is only safe if the estimator is not the binding constraint.** k-NN in 16 dimensions with seven training steps, under a by-step split that is also a distribution shift, is a weak estimator. Your job is to determine whether the finding is about the FEATURES or about the ESTIMATOR.

## Tasks

### A — replicate
Re-run the existing diagnostic unchanged and confirm you reproduce both numbers. If you cannot, stop and report that; everything downstream depends on it.

### B — estimator ladder, declared in advance
On the SAME rows, SAME split, SAME seed, SAME targets, fit this fixed list and report held-out EV and RMSE for each, for C1 and C2 separately. Declare the whole list before you run any of it, and report every entry, including the ones that do worse:
1. constant predictor (the training mean) — this is the EV = 0 reference;
2. ordinary least squares on the encoded features;
3. ridge with the penalty chosen on the validation split only;
4. gradient-boosted trees, modest depth, early stopping on the validation split only;
5. k-NN as originally run (the replication from A).
Do not add a sixth model after seeing results. If you want a sixth, you may not have it.

### C — is the split doing the damage?
The by-step split is also a temporal/distributional split. Report, for the best estimator from B:
- held-out EV on test steps 0 and 3 **separately**;
- EV under a leave-one-step-out rotation across all ten steps, reporting the per-step values and their spread.
State plainly whether the negative number is a property of one unlucky held-out step or holds across the rotation.

### D — how much variance is structurally unreachable?
Using exact duplicate encoded rows within the corpus (byte-identical feature vectors with differing exact targets), compute the irreducible variance floor implied by those collision groups on these 26,345 rows, and express it as a fraction of total target variance for C1 and for C2. If there are no exact duplicates for a route, say so — that is itself the answer for that route.

## Verdict required
End with one of exactly these three, for C1 and for C2 separately, and justify it in two sentences:
- `FEATURES_UNINFORMATIVE` — every estimator on the ladder fails to beat the constant predictor;
- `ESTIMATOR_ARTEFACT` — at least one estimator on the ladder clearly beats the constant predictor, so the original negative value understates what the features carry;
- `INDETERMINATE` — the ladder disagrees or the rotation is too unstable to call.

Report honestly. A verdict of `ESTIMATOR_ARTEFACT` would mean the controller overstated a finding to the project owner, and that correction is more valuable than a tidy story.

## Rules
- Change no threshold, sign, seed, horizon, price, guard or acceptance rule. Do not modify sealed artefacts or the fallback flag.
- Leave every script you used in the workspace and give exact command lines.
- Write `C1C2-ESTIMATOR-AUDIT-2026-09-10.md` in the workspace root and print it as your final message. Lead with the two verdicts on one line.
