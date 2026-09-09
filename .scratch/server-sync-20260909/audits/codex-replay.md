# Exact-pair selection replay: does omitting higher-order structure actually cost decisions?

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. **This needs no new model and no new physics evaluation.** The pair values were already computed when the order audit produced `R3`. If they were retained, this is arithmetic on existing numbers.

## Why this comes before any architecture change
An order audit found the third-and-above remainder material on 38.5 % of coalitions of size three or more, and the corpus report concluded the pairwise interaction model is misspecified. An outside review has now corrected what that measurement proves:

> It establishes failure of the exact, pair-calibrated **value** reconstruction. It does **not** establish a 38.5 % ranking error, nor a lower bound on selection regret.

The selector needs an ordering, not a value. For two candidates at one anchor the ordering reverses only when `R3(B) - R3(A)` exceeds the margin `Q2(A) - Q2(B)`. So what matters is **the difference of omitted residuals relative to the comparison gap**, not how many residuals are individually non-zero. Large residuals affecting both contenders alike change nothing; small ones can flip a near tie.

## What to compute
For each anchor, over its labelled feasible candidate pool including the no-move baseline where legal:

* `A*` maximising the exact `F`;
* `A2` maximising the exact pair-calibrated reconstruction `Q2(A) = F(a0) + sum_i d_i + sum over pairs in A of Psi(pair)`;
* the selection regret `F(A*) - F(A2)`.

Use the production tie-breaking rule and record consequential ties separately.

## Report, in this order
1. **The distribution of per-anchor selection regret**, and the fraction of anchors where it exceeds the project's +0.5 % relative margin. That single number decides whether higher-order structure is a decision-level problem or only a value-fitting one.
2. **How often `A2` equals `A*`**, and how often `A2` is in the exact top three.
3. **The true-value gap after exact re-ranking of the top K under `Q2`**, for K = 3, 5 and 10. If a small exact shortlist recovers nearly everything, a pairwise proposal score is still useful even when its top-one choice is wrong, and that changes the design.
4. **A rigorous bound.** Within each anchor, `F(A*) - F(A2) <= max_A R3(A) - min_A R3(A)` over that pool. Report the **within-anchor range** of `R3`, which bounds truncation regret, rather than the pooled magnitude which does not. Report the largest such range and the anchors that carry it.
5. Restrict every statistic to the coalitions whose selection actually changed, since those are the only ones that matter.

## Two limits to state in the report
This concerns the **labelled candidate pools**, not the best coalition in the whole action space. And it is an oracle for exact pair calibration, **not** an upper bound on every possible refitted pairwise ranker: a scorer that deliberately sacrifices pair-value accuracy could rank better.

## Naming correction to adopt
Call the quantity `R>=3`, not "the third-order share". For coalitions larger than three it contains every order from three up to the coalition size. The six size-six observations do not on their own demonstrate a sixth-order effect.

## Constraints
Workspace `/home/sat/mcrl-v025-replay-ws`: `cp -a /home/sat/mcrl-v025-coalgen-ws` to inherit the corpus and the order-audit artefacts, then `rm -rf .git`, `git init`, commit. Never modify any other workspace; several jobs are running. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or `/home/sat/mcrl-v025-codex-ws-engine`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Two processes maximum, `nice -n 15`. If the pair values were not retained, say so and report what recomputing them would cost rather than recomputing them silently.

Write `PAIR-REPLAY-2026-09-10.md` in the workspace root and print it as your final message. Lead with the fraction of anchors whose selection regret exceeds the +0.5 % margin.
