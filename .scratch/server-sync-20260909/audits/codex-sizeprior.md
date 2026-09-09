Workspace: the current directory, `/home/sat/mcrl-v025-selector-ws`. It contains today's parametrisation comparison: `PARAMETRISATION-COMPARISON-2026-09-10.md`, its scripts under `.scratch/parametrisation-comparison/`, its frozen split and its exact-label corpus. **Read that report first and reuse its harness, corpus, split, seed and estimator family exactly.** Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No production training run, no policy run, no acceptance test. No sealed contract, target, scorer, schema digest, manifest, constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is modified. Everything is fitted on copies for measurement only. **Use exact labels only; the pilot fallback labels at `scripts/run_v025_pilot_c3.py:89` substitute a per-user monotone squash with no coupled content and must never be read as targets.**

# The specific threat being tested

A design reviewer raised a concrete objection to the third route's contribution:

> The third route's correction is a large, nearly size-proportional term. Until the full system beats a variant in which that route is replaced by a **fixed per-size prior**, the honest description is that the sum needs a size penalty and that route supplies one.

This matters because the project owner's requirement is that each of three routes individually raise pooled energy efficiency. A route that passes an ordering test purely by supplying a size correction would satisfy the letter of that test while contributing nothing about interaction. **The objection has never been tested.**

Independent evidence that makes it plausible: the additive term grows roughly linearly in coalition size, with a median of 200.4 at the additive optimum against 8.02 for the best single move, so at size 100 the interaction term is about −440 against an additive +480.

# The experiment, declared in full before any fitting

Four scorers, on the same rows, same features where applicable, same frozen split, same seed, same estimator family and grid as the parametrisation comparison:

- **`LEARNED_PSI`** — the sealed form: the per-user deviation head plus the learned set-conditioned interaction head. This is the reference.
- **`SIZE_PRIOR`** — identical, except the interaction head is replaced by a function of **coalition size alone**, fitted on the same training rows by least squares on the same target. It sees no set context, no member identities, no features other than the integer size. State its fitted values per size.
- **`ZERO_PSI`** — identical, except the interaction term is identically zero. This brackets the other two from below.
- **`EXACT_PSI`** — identical, except the interaction term is the exact label. This brackets from above.

# Metrics, declared now; do not add any after seeing results

1. **Held-out selection regret** against the exact best row in each held-out anchor's labelled pool: mean, median, p95, and the fraction of anchors where the choice differs from the exact winner.
2. **The same, stratified by selected coalition size**, and the size distribution of each scorer's selections.
3. **Held-out value error** — explained variance and RMSE against the exact joint objective change.
4. **Pairwise agreement between `LEARNED_PSI` and `SIZE_PRIOR`**: how often they commit the same configuration, and the distribution of their score difference.
5. **Where they disagree, who is right** — the exact objective of each choice on those anchors.

# The question to answer directly

**Does the learned interaction head beat a scorer that knows nothing but coalition size?** Report the margin on selection regret with its sign, and say whether it is larger than the difference between `SIZE_PRIOR` and `ZERO_PSI`.

# Rules

- **If `SIZE_PRIOR` matches or beats `LEARNED_PSI`, say so in the first line.** That is the outcome that matters: it would mean the third route's measurable contribution is a size penalty, and the project needs to know before it spends a panel measuring that route's ablation.
- Do not tune either scorer. Fit the size prior once, by the stated rule, and report it.
- Do not treat a small margin as a win: report it with its magnitude and let the number speak.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach.

Write `SIZE-PRIOR-COMPARATOR-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the learned interaction head beats the size-only prior on held-out selection regret, and by how much.
