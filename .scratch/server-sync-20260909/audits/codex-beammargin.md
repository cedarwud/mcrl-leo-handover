Workspace: the current directory, `/home/sat/mcrl-v025-beam-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment, and never write into any other `mcrl-v025-*-ws`.

`DIAGNOSTIC_NOT_CLAIM`. No training run, no policy run, no learner. **No sealed constant is changed**: every point is a separate diagnostic evaluation on a copy. Do not change any sign, seed, horizon, price, service guard or acceptance rule, and do not modify sealed artefacts or frozen manifests.

# What already exists — reuse it, do not rebuild

This workspace contains a completed five-point beam-width network sweep: `BEAMWIDTH-READING-2026-09-09.md` and `.scratch/beamwidth/run_beamwidth_network.py`, with receipts `.scratch/beamwidth/sweep-one-sided-{1.66,2.40,3.32,4.50,6.65}.json`. Read them first.

A different workspace, `/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/`, contains a margin-provisioning variant of the physics: it provisions the power solver against the mode threshold divided by the same fading quantile the mode selection is later judged at, instead of against the bare threshold. Read `margin_batch.py` and `oracle_runner.py` there (read-only; another agent may be writing in that workspace). Copy what you need into this workspace.

# The problem

The existing sweep was measured under the **sealed** provisioning rule. That rule has since been shown, by two independent adjudications, to credit nothing on about 75 % of transmission instances, and to attain the per-user rate target for **zero** of 2,000 users. Under the margin rule, on a separate twenty-anchor panel, the joint-over-unilateral gap fell from `+6.359 %` to about `+0.51 %`.

So every number in the existing beam-width sweep may be an artefact of the defect, including its central finding that the coordination gap rises monotonically with beam width from `6.50 %` to `41.95 %`.

# The task

**Re-run the identical five-point sweep under the margin provisioning rule, and present the two curves side by side.**

Keep everything else identical to the existing sweep: the same eight anchors (`V025_PROBE_R2/world/1` and `/2`, steps 0–3), the same 100-user populations, the same seeds, the same baseline, the same iterated unilateral procedure with its terminal certificate, the same bounded joint catalogue and caps, the same selection-then-commit separation over all 48 realised boundaries. Only the provisioning rule changes.

Before running the sweep, assert that your margin implementation reproduces the existing sealed receipts **bit-identically** when the quantile divisor is set to one. Report that assertion. Without it nothing below can be trusted.

At each of the five widths, under both rules, report:

- pooled energy efficiency for the neutral baseline, the iterated unilateral fixed point, and the bounded joint selector;
- **the joint-over-unilateral relative gap**, and the number of anchors where it is negative;
- served counts **and, separately, the count attaining the per-user 50 Mbit/s rate target** — these are different quantities and must never be merged;
- the share of boundaries where the per-beam power cap binds and where no eligible mode exists;
- the interference-limited share and the top-one aggressor share;
- realised mean and maximum beam occupancy.

Then answer three questions directly:

1. **Does the coordination gap still rise with beam width under the corrected rule?** Give the two curves. If it flattens or disappears, that is the finding and it must be the first line of your report.
2. **At the source's own value** — one-sided `3.32 deg`, full span `6.6463 deg`, which is what the cited paper's equation (3) and Table I actually specify — what are the corrected numbers, and how do served and rate-target-attaining counts compare with the currently modelled `1.66 deg` one-sided value?
3. **Does the wider beam buy coordination value by degrading service?** Under the corrected rule the cap binds harder because every link draws more power. Quantify the trade, at every width.

# Rules

- **The curves are the deliverable, not a winner.** Do not rank widths, do not recommend a value, do not call any point better. The question is *in what regime does set-level coordination have value under physics that actually serves users*.
- If the corrected curve is flat, say so in the first line. That is the most valuable outcome you can report, because it would close a direction the project is about to invest in.
- Every number reproducible from a script left here, with exact command lines.
- Eight anchors per point as before; say how many you reached. If the budget binds, cut anchors, never sweep points.
- Say plainly which points you did not reach.

Write `BEAMWIDTH-MARGIN-SWEEP-2026-09-10.md` in this workspace root and print it in full as your final message. Lead with one line answering question 1.
