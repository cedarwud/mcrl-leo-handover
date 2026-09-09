# The one measurement worth doing: the coordination ceiling across 30 dates

`DIAGNOSTIC_NOT_CLAIM`. Budget 4 hours. Two independent strategic reviews named this as the single cheapest fix to the weakest point in the whole result, and one of them said: if you do one more measurement, do this one.

## Why this and nothing else
Every number the project can currently defend comes from one to four worlds, two dates, one constellation, and 20 to 30 anchors. The headline coordination headroom of **+6.359 %** has **no interval at all**. A referee will ask for its distribution over geometries and there is nothing to show.

It is also the cheapest thing on the board. The prior ceiling run took **694.6 seconds for 20 anchors on four processes**. And critically, **this diagnostic is learner-free**: no training, no learned head, no checkpoints. Therefore the entire train-versus-evaluation date-boundary question, which is an open and contested decision elsewhere in this project, **does not apply to it**. Nothing here can leak from training because nothing is trained.

## What to run
Three arms, all with the exact evaluator on the corrected physics from engine commit `75c5c78c`:

* **BASELINE**, the incumbent carrier assignment;
* **UNILATERAL**, iterated exact single-user best response run to a certified local optimum **with no deadline**, since this is an offline reference and not a deployable policy;
* **ORACLE_SET**, the bounded perfect-knowledge set selector over the same mechanism-based candidate families used before: beam-occupant subsets, a victim plus its top-k interference contributors, and complete beam evacuations.

Cover **at least 30 distinct ephemeris dates**, roughly 20 anchors each. Dates must be TRAIN-partition only and must avoid the 17 calendar dates missing from the archive. Choose them **spread across the full archive span** and record the satellite count per date, because the constellation grows from 8,044 to 10,746 across it and a variance estimated over widely separated dates mixes geometry with growth.

## What to report, and this is the point of the exercise
1. **The pooled ORACLE-over-UNILATERAL gain per date**, and its **distribution**: mean, standard deviation, min, max, and a confidence interval over dates. That interval is the deliverable.
2. **The same statistic computed within a single month** and **across the full span**, reported separately, so geometric variation is separable from constellation growth.
3. Served counts for all three arms at every date, so it stays visible that no gain comes from serving fewer users.
4. The share of anchors admitting a qualifying coalition, per date.
5. Wall time and core hours consumed, so the cost of extending further is known.

## Two wording obligations to carry into the report
Do **not** call the unilateral arm a ceiling or an upper bound on unilateral reasoning. An unlimited-compute fixed point reached by one deterministic greedy path is an arbitrary local optimum. The licensed phrasing is "not reachable by exhaustive single-user best response from the carrier anchor", and the path dependence should be stated.

Do **not** present the oracle gain as the headroom of coordination in general. It is the headroom of a hand-built candidate catalogue and is therefore a **lower bound**. Say so explicitly rather than leaving it for a referee.

## Constraints
Workspace `/home/sat/mcrl-v025-ceiling30-ws`, built with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C` it, then `git init` and commit. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. **World tapes are about 800 MB each: build them one at a time under `/home/sat/bigtmp`, never `/tmp`, which is RAM-backed here, and delete each tape after its evaluation.** At most 4 processes, `nice -n 10`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule. Report every date you generate, including any whose gain is unfavourable.

Write `CEILING-30-DATES-2026-09-10.md` in the workspace root and print it as your final message. Lead with the mean gain and its interval across dates.
