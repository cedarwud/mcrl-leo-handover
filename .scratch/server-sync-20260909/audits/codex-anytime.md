Workspace: the current directory, `/home/sat/mcrl-v025-harness-ws`. It contains a standing evaluation harness completed today: `EVAL-HARNESS-2026-09-10.md`, `bin/harness`, a twenty-anchor panel, a `SEALED` variant proved bit-identical, and a `MARGIN_Q` variant. **Read that report first and reuse the harness.** Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed; no sealed artefact or frozen manifest is modified.

# The question

The decision interval is **30.08 seconds**. The iterated unilateral best-response search converges in about **65 seconds on average**, and its converged fixed point is worth roughly **+442 %** in pooled efficiency over the geometry-only baseline. A project is considering claiming that a learned method wins *within the interval* because the exact search does not fit.

That argument has never been tested, and an external review identified the gap precisely: **time to convergence is not time to a useful decision.** A search taking 65 seconds to certify convergence may have obtained almost all of its eventual improvement far earlier. If most of the value is available by 30 seconds, the deadline argument fails.

**Measure the anytime quality curve of the unilateral search.**

# What to build

Instrument the existing unilateral selector so that it maintains a **feasible incumbent from the first instant** and records, as a function of wall-clock time, the configuration it would commit if interrupted at that instant. Implement it in good faith as an anytime algorithm:

- start from the legal base configuration, which is immediately committable;
- accept each strictly improving single-user move as soon as it is found, and never discard accepted improvements because a sweep was interrupted;
- prefer **first-improvement** over completing a best-improvement sweep, and say what difference that makes;
- use incremental or cached evaluation where the same quantity is recomputed;
- **do not run the final complete-neighbourhood certification sweep**, which proves optimality but changes no action. Report separately how long that sweep costs.

These are ordinary implementation improvements, not a new algorithm. If any of them changes the fixed point reached, say so explicitly and report both.

# Deliverables

**D1 — the anytime curve.** For each anchor, the true pooled objective of the committed-if-interrupted configuration at wall-clock 1, 2, 5, 10, 20, **30.08**, 45, 60 seconds and at convergence. Pool across the panel the way the project does — summed bits over summed joules — and also give the paired per-anchor distribution. **The reported value must be the true objective of the action it would actually return**, never the best candidate seen with hindsight.

**D2 — the fraction of the prize available at the deadline.** State what fraction of the converged unilateral improvement over baseline is already attained at 30.08 seconds, with the per-anchor spread and the worst anchor.

**D3 — the certification cost, separated.** How much of the 65 seconds is finding improvements and how much is proving none remain. Report the distribution.

**D4 — the seed question.** The bounded joint search is currently seeded from the *converged* unilateral fixed point. Measure what the joint search achieves when seeded instead from the unilateral incumbent available at 10, 20 and 30.08 seconds, with the joint search's own time counted inside the same budget. State the total end-to-end time for each configuration. This is the measurement that determines whether a learned ranker can be given its seed for free.

**D5 — both provisioning rules.** Run everything under `SEALED` and `MARGIN_Q`. A conclusion that holds only under the defective rule is worthless.

# Rules

- **If most of the prize is available well before the deadline, say so in the first line.** That result closes a direction the project is about to invest in, and it is the more valuable outcome.
- Do not tune the anytime implementation to lose. It is the comparator a referee will demand, and a weak one invalidates the whole comparison.
- Timing must be honest end-to-end wall clock on the stated hardware, single process, with feature construction and candidate generation counted. State the hardware and thread settings.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach.

Write `ANYTIME-UNILATERAL-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the fraction of the converged unilateral improvement already available at 30.08 seconds, under each provisioning rule.
