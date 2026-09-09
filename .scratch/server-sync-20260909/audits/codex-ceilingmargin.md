Workspace: the current directory, `/home/sat/mcrl-v025-ceiling30-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment; read-only access to sibling workspaces is fine, never write into them.

`DIAGNOSTIC_NOT_CLAIM`. No training run, no learner, no policy run. **No sealed constant is changed**: the variant is a separate diagnostic evaluation on a copy, exactly as previous variant work was. Change no sign, seed, horizon, price, service guard or acceptance rule; modify no sealed artefact or frozen manifest.

# What exists here — reuse it, do not rebuild

This workspace just completed a thirty-date coordination-headroom diagnostic: `CEILING30-CODEX-2026-09-10.md` (or the equivalently named report in the workspace root), the per-date runner, and thirty per-date receipts under `.scratch/oracle-ceiling30/results/`. It reported a mean gain of **+5.888 %** with a date-level 95 % interval of **[+5.235 %, +6.540 %]**, all thirty dates positive, minimum +3.205 %, maximum +9.652 %.

**Every one of those numbers was computed under a provisioning rule that has since been shown defective.** Under it, roughly 75 % of transmission instances are credited nothing and **zero** of 2,000 users attain the per-user rate target. A corrected rule that provisions against the mode threshold divided by the same fading quantile the mode selection is later judged at restores service, and on a separate twenty-anchor panel it reduced the coordination gap from about +6.36 % to about +0.51 %.

A reference implementation of the corrected rule is in `/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/` (read `margin_batch.py` and `oracle_runner.py`, read-only, and copy what you need here). A standing harness in `/home/sat/mcrl-v025-harness-ws` registers the same rule as a named variant `MARGIN_Q`; read its report if useful.

# The task

**Re-run the identical thirty-date panel under the corrected provisioning rule, and present the two sets of dates side by side.**

Everything else must be held: the same thirty dates, the same anchor counts per date, the same worlds and seeds, the same baseline, the same iterated unilateral procedure with its terminal certificate, the same bounded catalogue rules and caps, the same selection-then-commit separation, the same date-level aggregation with the date as the independent unit.

Before running the panel, assert that your corrected implementation **reproduces the existing sealed per-date receipts bit-identically when the quantile divisor is set to one**, on at least three dates. Report that assertion explicitly. Without it nothing below can be trusted.

# Report

For the corrected rule, and paired against the existing sealed numbers date by date:

- per-date pooled gain of the bounded joint selector over the certified unilateral fixed point, the date-level mean, sample SD, and two-sided 95 % interval with the date as the independent unit;
- **the number of dates with a negative gain**, and the minimum and maximum;
- served counts for all three arms **and, separately, the count attaining the per-user rate target** — these are different quantities and must never be merged;
- the share of boundaries where the per-beam power cap binds and where no eligible mode exists;
- the paired per-date difference between the two rules, with its own interval.

Then answer directly:

1. **Under the corrected rule, is the coordination gap still positive on every date?** If some dates go negative, how many and how far.
2. **How large is it, with its interval?** This is the number the project's remaining decisions rest on.
3. **Does the correction change which dates are favourable?** Report the rank correlation between the two sets of per-date gains.

# Rules

- If the corrected gap is small and its interval includes values the project would consider immaterial, say so in the first line. That is the outcome that matters most and it must not be softened.
- Do not rank or recommend a provisioning rule. Report both.
- Every number reproducible from a script left here with exact commands; keep the existing refuse-to-overwrite guard on completed receipts and write the corrected ones under a clearly distinct path.
- If the budget binds, reduce anchors per date before dropping dates, and say exactly what you cut.

Write `CEILING30-MARGIN-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the corrected mean gain, its interval, and the number of negative dates.
