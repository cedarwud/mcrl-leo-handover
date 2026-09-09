Workspace: the current directory, `/home/sat/mcrl-v025-beam-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment; read-only access to sibling workspaces is fine, never write into them.

`DIAGNOSTIC_NOT_CLAIM`. No training run, no learner, no policy run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed; no sealed artefact or frozen manifest is modified. **No metric is being replaced** — an additional metric is being reported alongside the sealed one.

# What exists here

This workspace just completed `BEAMWIDTH-MARGIN-2026-09-10.md`: a five-point beam-width sweep under both the sealed and the corrected margin provisioning rules, eight anchors per point, 100 users at steps 0–3 from `V025_PROBE_R2/world/1` and `/2`, with receipts under `.scratch/beamwidth/`. Read that report and reuse its runner and receipts. Re-running the physics is only necessary if the per-user quantities you need were not retained.

# Why this task exists

The project's declared objective is **pooled** energy efficiency: total bits over total joules. A reading of twelve papers in the field established two things about that choice. Pooled efficiency is a genuine convention and is described as having the strongest physical interpretation. But **reporting only the pooled form is against convention**: papers that care about heterogeneity report a summed-per-entity form alongside it, and criticise the pooled form for hiding how the allocation is distributed across links.

The corrected sweep gives a concrete reason to worry. At the two narrowest widths the bounded joint selector attains **fewer** users at the per-user rate target than the certified unilateral fixed point — 541 against 550, and 434 against 443 — while still winning on pooled efficiency. It is buying energy while leaving more users below target, and the pooled metric cannot see that.

The remaining positive result on this axis is **+0.985 %** at the source's own beam width. **The question is whether that survives a metric the field would also require.**

# The task

For every one of the ten cells already measured — five widths by two provisioning rules — and for all three arms, compute and report **alongside** the existing pooled figure:

1. **Summed per-user efficiency.** For each served user, its own delivered bits over its own attributed joules, summed across users. State precisely and defend how you attribute joules to a user under equal-airtime multiplexing within a beam and per-chain and per-satellite fixed costs; if more than one attribution is defensible, report the two you consider most defensible and say which the field uses.
2. **The per-user efficiency distribution** — median, interquartile range, 5th and 95th percentiles, and the count of users with zero credited bits.
3. **Rate-target attainment as a first-class metric**, not a footnote: the count and share attaining the per-user target, separately from the count merely served.
4. **A per-user paired comparison** between the joint selector and the unilateral fixed point: how many users are better off, how many worse off, and the distribution of the per-user change. A pooled win composed of a small gain to many users and a large loss to a few is a different result from a uniform gain.

Then answer directly:

**Does the joint selector's advantage over the certified unilateral fixed point survive under the summed-per-user metric, at each width and under each rule?** Report the sign and magnitude in every cell, and say explicitly where the two metrics disagree.

# Rules

- **If the advantage vanishes or reverses under the per-user metric, say so in the first line.** That is the outcome that matters and it must not be softened. It would mean the remaining positive result is a property of the metric rather than of the mechanism.
- Do not recommend replacing the sealed objective. The sealed objective is the sealed objective; this is an additional diagnostic reported beside it.
- Do not tune the joules attribution to produce a particular sign. Fix the rule, state it, then measure.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach.

Write `PER-USER-METRIC-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the joint selector's advantage survives the per-user metric at the source's beam width under the corrected rule.
