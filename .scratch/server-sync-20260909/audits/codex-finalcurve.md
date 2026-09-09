Workspace: the current directory, `/home/sat/mcrl-v025-beam-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment; read-only on sibling workspaces.

`DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed; the declared sealed provisioning rule is not replaced. The sealed one-sided beam half-power angle remains 1.66°; the other widths are diagnostic points, as in the two sweeps already completed here.

# Two corrections that must now be applied together

This workspace holds `BEAMWIDTH-MARGIN-2026-09-10.md` and `STRICT-CLEARANCE-CURVE-2026-09-10.md`. Read both. Two independent defects have since been established in how those curves were produced:

**1. Numerical clearance.** Simple division of the target by the quantile leaves occupancy-one attempts a few times 1e-9 dB below threshold. The strict-clearance implementation fixes this and changes the curve's shape from non-monotone to increasing, without changing any sign. **Use the strict implementation throughout.**

**2. Pairing.** Every gap in both curves compares a joint selector **seeded from the best-improvement unilateral fixed point** against that same fixed point. A separate measurement, `RESEEDED-SPAN-2026-09-10.md` in `/home/sat/mcrl-v025-harness-ws` (read-only), established that accepting the **first** strict improvement instead of completing a best-improvement sweep reaches a better fixed point on all twenty anchors of that panel, and that re-pairing both arms onto it changes the corrected-rule span from `+0.5448 %` to `+1.2913 %` — an understatement of 0.75 percentage points — while the sealed-rule span falls from `+6.3590 %` to `+4.6046 %`. **The two errors run in opposite directions, so no ratio may be extrapolated to the beam-width curve. It must be measured.**

# The task

**Produce the five-width curve with the strict-clearance implementation and correct pairing: both the unilateral arm and the joint arm built from the first-improvement local search.**

Hold everything else as the two existing sweeps did: the same eight anchors, `V025_PROBE_R2` worlds 1 and 2, steps 0–3, 100 users, the same seeds, the same neutral baseline, the same bounded catalogue rules and caps, the same tie-break, objective, price and served-count guard, the same selection-then-commit separation over all 48 realised boundaries, the same pooled aggregation. The first-improvement procedure is implemented in the harness workspace; reuse it and cite its implementation digest rather than reimplementing it.

Report, at each width, under **both** provisioning rules and for **all four** arms — `U_best`, `U_first`, `J_from_best`, `J_from_first`:

- pooled efficiency, and the joint-over-unilateral gap for each pairing;
- **the correctly paired gap, `J_from_first` over `U_first`**, with the number of anchors where it is negative;
- served counts **and, separately, rate-target attainment** — never merged;
- the decomposition of the change from the previously published gap into the search-order part and the seed part.

Then answer directly:

1. **With strict clearance and correct pairing, is the corrected-rule gap still negative at the sealed 1.66° width?** This is the question that decides whether the currently modelled design point is viable.
2. **What is the gap at the source's own 3.32° one-sided width?**
3. **Is the curve monotone under correct pairing?**

# Rules

- **If the gap at 1.66° is still negative under correct pairing, say so in the first line.** Do not soften it, and do not present a positive value at a wider width as a remedy — any antenna change is a separate design decision that is explicitly out of scope here.
- Do not tune anything. Both implementations already exist; compose them.
- Every number reproducible from a script left here with exact commands.
- Eight anchors per width; say how many you reached. Reduce anchors before dropping widths.

Write `FINAL-BEAMWIDTH-CURVE-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line answering question 1, and give the corrected-rule gap at 1.66° and at 3.32°.
