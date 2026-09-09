# Four numbers the experiment design turns on, and I have never checked any of them

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. This is an audit of our own statistical machinery, not an experiment. Every question below is answerable from artefacts already on disk.

An outside statistical review said it could not responsibly recommend a design without these, and warned that one of our supposed defects may not be a defect at all.

## Q1. Was the measured coverage marginal or simultaneous?
We report measured bootstrap coverage of **0.86 to 0.92** against a nominal 0.95, and I have been calling it undercoverage. That may be wrong. If the figure is the probability that **all three** contrast intervals cover simultaneously, then even perfectly calibrated marginal intervals give `0.95^3 = 0.857`, so 0.86 to 0.92 would be **correct behaviour**. If it is the coverage of **each individual** interval, it is a genuine calibration failure.

Find the simulation or calibration code that produced those numbers and determine which quantity it computes. **This is the most important question here.** Report the code location and quote the lines that decide it.

While you are there, establish what "95 % lower bound" means in the implementation: a one-sided bound with a 5 % lower-tail allowance, or the lower endpoint of an equal-tailed two-sided 95 % interval with a 2.5 % allowance. Confusing these changes both calibration and power.

## Q2. Is the "5 % date standard deviation" raw efficiency or the paired contrast?
The power figures assume a 5 % date standard deviation. Those are very different quantities. A 5 % date-to-date swing in **raw** energy efficiency may largely cancel in the FULL-minus-DROP contrast when both arms meet the same hard dates. What drives power is the variation of the **paired contrast**, not of the raw metric.

Find where the 5 % enters the power simulation and report which it is. Then, from whatever real evaluation data exists, estimate the actual standard deviation of the paired log contrast `log(EE_FULL) - log(EE_DROP)` across dates, and compare it with the assumed value.

## Q3. How many independent date blocks do we actually have?
Count them. Not anchors, not worlds, not date-by-seed cells: **independent ephemeris dates**. Then report how many distinct worlds share each date, because worlds sharing a date supply within-date information and do not substitute for new date blocks.

Also report the share of total joules contributed by each date and by each seed, per arm, and the concentration index `1 / sum(w^2)` over the date energy weights. This says whether the pooled ratio is effectively an average over a few dates.

## Q4. Does the power plateau exceed simulation noise?
Conjunction power is reported as 0.68 at both 16 and 24 seeds, which I read as a ceiling. With `N` simulation repetitions the Monte Carlo standard error at p = 0.68 is `sqrt(0.68*0.32/N)`, about 1.5 percentage points at N = 1000. Two values that both round to 0.68 may not differ.

Report `N`, the Monte Carlo standard error, and whether the two estimates are distinguishable. Also state whether the 0.68 covers only the three efficiency contrasts or the complete success event including the three quality-of-service non-inferiority conditions. If it is efficiency only, it is an **upper bound** on the power of the real claim.

## What to write
`DESIGN-AUDIT-2026-09-09.md` in the workspace root, printed as your final message. Answer the four questions in order, each with the code location and the quoted lines that settle it. Where an artefact does not exist to answer a question, say so plainly rather than estimating; "we never measured this" is a valid and useful answer.

End with one paragraph: given the four answers, is the design's problem calibration, date count, seed count, or the claim structure? Do not recommend a sample size; the inputs for that are what this audit is collecting.

## Constraints
Workspace `/home/sat/mcrl-v025-design-ws`: `mkdir -p`, `git init`, commit empty. Read from `/home/sat/mcrl-v025-codex-ws-engine` and `/home/sat/mcrl-v025-pilot-ws` **read-only**; several jobs are editing them, so copy anything you need to run. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or any other workspace. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`. Two processes maximum, `nice -n 15`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here.
