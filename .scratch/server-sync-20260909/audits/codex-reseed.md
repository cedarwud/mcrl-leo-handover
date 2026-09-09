Workspace: the current directory, `/home/sat/mcrl-v025-harness-ws`. It holds the standing evaluation harness and the anytime work completed today: `EVAL-HARNESS-2026-09-10.md`, `ANYTIME-UNILATERAL-2026-09-10.md`, `bin/harness`, the twenty-anchor panel, the bit-identical `SEALED` variant and the `MARGIN_Q` variant, and receipts under `receipts/`. **Read both reports first and reuse everything.** Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed; no sealed artefact or frozen manifest is modified.

# The defect in every coordination figure the project holds

Today's anytime measurement found that accepting the **first** strict improvement, instead of completing a best-improvement sweep, changes the search path and the fixed point on **all twenty anchors under both provisioning rules**, and converges to a pooled efficiency **8.13 % above** the archived endpoint under `SEALED` and **1.62 % above** it under `MARGIN_Q`.

Every coordination figure the project holds — the archived `+6.359 %`, the corrected `+0.51 %`, the five-point beam-width curve, the thirty-date interval — compares a bounded joint selector against the **best-improvement** fixed point. Arithmetic on the archived numbers suggests the first-improvement fixed point alone may already exceed the joint selector's committed efficiency under `SEALED` (roughly 30.79 against 30.28) and possibly under `MARGIN_Q`.

**But the joint selector was seeded from the best-improvement fixed point.** Re-seeding it from the better endpoint should improve it too. The comparison as run is therefore not invalid in its arithmetic but invalid in its pairing, and the real coordination span is unknown.

# The task

**Re-run the twenty-anchor comparison with both the unilateral arm and the joint arm built from the first-improvement local search, and report all four combinations.**

For each provisioning rule, report these arms on the same anchors:

- **`U_best`** — the archived best-improvement unilateral fixed point.
- **`U_first`** — the first-improvement unilateral fixed point, as measured by the anytime work.
- **`J_from_best`** — the bounded joint selector seeded from `U_best`. This is the archived arm.
- **`J_from_first`** — the identical catalogue rules, caps, tie-break, objective, price and served-count guard, seeded from `U_first`.

The catalogue generation rules must be **identical** across the two joint arms; only the seed changes. State explicitly how the served-count guard's reference is set for each arm and keep it consistent.

# Report

- pooled efficiency for the neutral baseline and all four arms, under both rules;
- **the coordination span measured correctly**: `J_from_first` over `U_first`, with the number of anchors where it is negative, alongside the archived `J_from_best` over `U_best` for comparison;
- the cross pairings `J_from_best` over `U_first` and `J_from_first` over `U_best`, so the seed effect and the search-order effect can be separated;
- served counts **and, separately, rate-target attainment**, never merged;
- how often the two joint arms commit the same configuration, and the size distribution of the selected coalitions in each.

Then answer directly:

1. **What is the coordination span when both arms use the same, better local search?** This is the number every remaining decision depends on.
2. **Does the joint selector still beat its own seed?** Report the sign per anchor.
3. **How much of the archived span was search-order artefact rather than coordination?** Decompose it.

# Rules

- **If the correctly paired span is near zero or negative, say so in the first line.** That is the outcome that matters most, and it would mean the project's central quantity was an artefact of comparing against a suboptimal local-search order.
- Do not tune the local search further. Use exactly the first-improvement procedure the anytime work implemented, and cite its implementation digest.
- No deadline applies to these diagnostics; run both searches to convergence.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach.

Write `RESEEDED-SPAN-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the coordination span with both arms on the first-improvement search, under each provisioning rule.
