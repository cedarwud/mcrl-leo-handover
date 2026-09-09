# Is the "always picks all 100 users" symptom a learning failure or a selection failure?

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. Several of these tests take minutes and can reject an implementation without training anything. Do the cheap decisive ones first and report them as soon as you have them.

## The symptom
At the epoch-200 checkpoint the FULL arm selected the all-users coalition at all ten anchor-seeds and never a size between 2 and 6, and 2 of the 10 were harmful by exact joint delta. I have been assuming this is caused by the coalition features having been collapsed to scalars. **That assumption is untested and there are at least four other explanations.** Separate them.

## First, establish that the behaviour is even wrong
The selector maximises a total score, roughly `G(A) = sum_i d_i + Psi(A) - cost(A)`, not the interaction alone. A profitable small coalition can coexist with a still-better grand coalition. So find, at the sampled anchors, whether there exists a **small feasible coalition that strictly beats the grand coalition under the intended score**. If none exists, the symptom is not a defect and the rest of this task is a diagnostic of a non-problem. Report that plainly if so.

## The decisive cheap tests, in this order
1. **Zero out the interaction head.** Replace `Psi_hat` with exactly zero and re-run the same selection on the same anchors. **If it still picks all users, the learned interaction is irrelevant to the symptom** and the cause is in the singleton terms, the cost term, the search, the masks, the tie-break or a default. This single test is the highest-value item here.
2. **Score a fixed candidate panel exactly.** Build a panel per anchor containing the empty set, a known-good small coalition, a few intermediate sizes and the grand coalition. Score them with the exact evaluator and separately with the model, and run the real selector over the same panel. If a strictly inferior grand coalition still wins under exact scores, the fault is in score assembly, feasibility, masking or ties, not in interaction learning.
3. **Log the score components separately by coalition size and by checkpoint**: `Psi_hat`, exact `Psi`, the singleton sum, the cost term and the final score. Report them as a table. This separates early-epoch shrinkage, accumulated bias and unit errors.
4. **Bias accumulation check.** A constant upward bias `b` on each pair term contributes `b * k*(k-1)/2`, so a bias of 0.01 per pair is 0.01 at size two and 49.5 at size one hundred. Estimate the mean signed error of `Psi_hat` per pair and report what coalition size that bias alone would favour. Anchored zeros at the empty set and singletons do **not** prevent this.
5. **The no-op invariant.** Adding a member whose proposed action equals its anchor action must not change the physical interaction at all. Test it. A violation is a masking or bookkeeping defect and would explain size preference directly.

## Two label-accounting items to verify while you are there
* The residual for a coalition of size `k` needs `k + 2` distinct evaluations, not four. Four suffices only for a pair. Check what the code actually evaluates and whether cached baselines and singletons explain any shortfall.
* If the singleton terms subtracted to form the label are **learned** rather than exact, then the head is being trained on `Psi - sum_i eps_i`, which is interaction plus singleton-error correction, a different estimand. Report which convention the code uses.

## One structural fact to check, not to assume
For a coalition of three or more, the residual is **not** a pairwise quantity: it is the sum of every interaction order above one. A threshold on shared beam occupancy, which is exactly the mechanism this project has verified, produces a genuine **third-order** term. So measure `R3(A) = Psi(A) - sum over pairs of Psi(pair)` on cached values and report its size. If it is material, any pairwise-only interaction model is misspecified regardless of its features.

## Workspace
`/home/sat/mcrl-v025-selector-ws`: build with `cp -a /home/sat/mcrl-v025-pilot-ws /home/sat/mcrl-v025-selector-ws`, then `rm -rf .git`, `git init`, commit. **Never modify `/home/sat/mcrl-v025-pilot-ws`; other jobs are editing it.** Also never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. At most 3 processes, `nice -n 10`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule. The zeroing of the interaction head is a diagnostic intervention on a copy, not a change to the method.

Write `SELECTOR-DIAGNOSIS-2026-09-09.md` in the workspace root and print it as your final message. Lead with the answer to test 1 in one line, then whether a small coalition strictly beats the grand coalition at all, then the rest.
