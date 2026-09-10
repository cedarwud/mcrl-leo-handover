Workspace: the current directory, `/home/sat/mcrl-v025-prevalence-ws`. Read-only elsewhere. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment. **At most 3 concurrent workers. Aim to finish within twenty minutes; speed is the point.**

`DIAGNOSTIC_NOT_CLAIM`, `FAST_DIAGNOSIS`. Pure evaluation of the existing law; no search, no optimiser, no learner, no training. No sealed constant, threshold, sign, seed, horizon, price, guard, acceptance rule or control law is changed.

# The one-line hypothesis to test

A fast look minutes ago found that, at **fixed user assignment**, better power and mode settings raised pooled efficiency by about **113 %**, with integrated bits up **115 %** while joules rose only **0.87 %**. Almost all of the gain therefore came from **choosing better modes at essentially unchanged power**.

There is an obvious candidate explanation, and it can be checked without any search:

> The declared law provisions power to meet the **minimum-threshold mode that satisfies the required spectral efficiency** `r*·n/W`, and then transmits that mode. **It never asks whether the power it is already spending could support a higher mode.**

If true, the link is routinely operating far above the threshold of the mode it actually transmits, and the wasted headroom is visible directly.

# What to measure

On at least four real anchors under the **corrected `MARGIN_Q`** rule, for the configuration the pipeline commits, at every realised boundary and every active transmission slot:

1. the **transmitted mode** the declared law selects, and its threshold;
2. the **realised signal-to-interference-and-noise ratio** actually achieved in that slot;
3. the **highest mode in the sealed table** whose threshold that realised ratio clears;
4. the **gap in rungs** between 2 and 3, and the **gap in decibels** between the realised ratio and the transmitted mode's threshold.

Report the distribution of the rung gap and the decibel gap: mean, median, the fraction of slots where the gap is zero rungs, and the fraction where it is three or more. Break it down by **beam occupancy**, because the required spectral efficiency scales with occupancy and the hypothesis predicts the gap is largest at **low** occupancy.

Then state, in one line: **how many extra bits per joule would be available from mode selection alone, holding every transmit power exactly as the declared law sets it.** That is an upper bound on the mode-choice component of the fast look's gain, obtained without changing any power.

# Rules

- **If the transmitted mode is usually already the highest the realised ratio supports, say so in the first line.** That would refute the hypothesis and send the search for the fast look's gain elsewhere, which is just as useful.
- Do not change any power. This isolates mode choice alone.
- Report both the delivered-capacity view and a demand-capped view where each user is credited at most its contracted rate, since a companion job is establishing that the distinction matters greatly here.
- Every number reproducible from a script left here with exact commands.

Write `MODE-SELECTION-GAP-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the median rung gap and decibel gap, and the bits-per-joule available from mode choice alone.
