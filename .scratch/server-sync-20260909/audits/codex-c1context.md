Workspace: the current directory, `/home/sat/mcrl-v025-selector-ws`. It contains today's parametrisation comparison and size-prior comparator with their scripts, frozen split, seed and exact-label corpus under `.scratch/`. **Read `PARAMETRISATION-COMPARISON-2026-09-10.md` and `SIZE-PRIOR-COMPARATOR-2026-09-10.md` first and reuse their harness, corpus, split, seed, estimator family and grid exactly.** Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. Offline fit on copies for measurement only. No production training run, no policy run, no acceptance test. No sealed contract, target, scorer, schema digest, manifest, constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is modified. **Use exact labels only**; the pilot fallback at `scripts/run_v025_pilot_c3.py:89` substitutes a per-user monotone squash with no coupled content and must never be read as a target.

# The hypothesis, assembled from three of today's reports

The first route is the project's identified bottleneck. A design review found that with the production head shape and the sealed sixteen-scalar vector it reaches held-out `R² = 0.151` and pairwise ordering `0.650`, that **79.3 %** of its target's variance sits in whole-network coupled terms, and that **98.9 %** of the externality's variance is *within* an anchor so none of it cancels in ranking. Critically, it also found that **an oracle which removes only the cross-user externality reaches ordering `0.902`**.

Separately, a feature-sufficiency diagnostic established that the interaction head **already receives 163 resource-context coordinates** — affected-beam pooling, pairwise cross-gains, and globals — that the per-user head does **not** see, and that this is the sealed decomposition's architecture rather than an information advantage. The parametrisation comparison then measured those same 163 coordinates as **worth 1.067 in mean selection regret**, while making pointwise interaction calibration slightly *worse*.

**Hypothesis: the information the first route is missing already exists in the codebase, is already consumed at decision time by another head, and is admissible — the per-user head simply does not receive it.**

This has never been tested.

# Admissibility, which governs everything below

A feature is admissible only if it is computable from the pre-decision network state and the focal candidate action alone, **without** evaluating the candidate configuration's coupled power fixed point or its whole-network outcome, and without any label, oracle or future information. The 163 resource-context coordinates are believed admissible because the interaction head already consumes them at decision time — **verify that claim in code before relying on it**, and say what you found. If any coordinate is not admissible, exclude it and say which.

# The experiment, declared in full before any fitting

Four per-user scorers, same rows, same frozen split, same seed, same estimator family and grid:

- **`Q1_ONLY`** — the sealed sixteen-scalar vector. The reference.
- **`Q1_PLUS_CONTEXT`** — the same, plus the admissible subset of the 163 resource-context coordinates.
- **`Q1_PLUS_CONTEXT_MINUS_EXTERNALITY`** — the same as the previous arm, evaluated against a target from which the cross-user externality has been removed. This measures how much of the remaining gap is the externality itself rather than the features.
- **`LEAKY_ORACLE`** — the target's own defining terms, labelled `NOT_DEPLOYABLE`, to bracket from above.

# Metrics, declared now; none added after seeing results

1. Held-out explained variance and RMSE against the exact first-route target.
2. **Held-out pairwise ordering within each anchor's candidate pool** — this is the quantity the design review measured at 0.650 and 0.902, and it is the one that matters for ranking.
3. Both stratified by anchor, with the leave-one-step-out spread.
4. Which context coordinates carry the gain, by a single declared attribution method chosen before fitting.
5. The end-to-end effect: mean selection regret of the full sealed scorer with and without the added coordinates, on the same pools as the parametrisation comparison.

# The question

**Does giving the per-user head the resource context that the interaction head already sees close any material part of the gap between ordering 0.650 and 0.902?**

# Rules

- **If it does not, say so in the first line.** That closes the cheapest remaining repair for the project's identified bottleneck, and the project needs to know before it designs a harder one.
- Do not tune. Fit once with the frozen grid and report.
- Verify admissibility in code; do not assume it.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach.

Write `C1-RESOURCE-CONTEXT-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the held-out pairwise ordering with and without the added context, and whether the gain is material.
