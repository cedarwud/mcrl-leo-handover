# What coalition sizes has the learner ever been trained on?

`DIAGNOSTIC_NOT_CLAIM`. Budget 45 minutes. This is a data audit, not an experiment. It may be the cheapest possible explanation for a long-standing failure, so do it quickly and report the histogram even if nothing else finishes.

## The hypothesis
The mechanism this project has verified is a coalition of **two or three** users. If the training shards contain almost no coalitions of that size, the interaction head never saw the mechanism, and no amount of training or feature repair would have helped. Uniform sampling over subsets of one hundred users concentrates coalition size near fifty, so this failure mode is easy to create by accident.

## What to measure
The existing pilot shards are in `/home/sat/mcrl-v025-pilot-ws/artifacts/` (the full-scale run reported 176,223 source rows and coalition shards alongside them). Find the coalition training rows and report:

1. **The histogram of coalition size** over every training row, as counts and as a share. Give the minimum, the 5th, 25th, 50th, 75th and 95th percentiles, and the maximum. **This single histogram is the deliverable; report it first.**
2. **How many rows have size 2, 3, 4, 5 and 6.** These are the sizes the verified mechanism occupies. Give absolute counts, not only percentages, since a small share of a large corpus may still be enough.
3. **How the coalitions were generated.** Find the code that produces them and state the sampling rule in one paragraph: uniform over masks, top-K by some score, a fixed family, or something else. Quote the relevant lines.
4. **The exact interaction value by size.** For the rows that carry an exact label, report the distribution of the interaction target within each size bucket: mean, spread, and the share that is positive. If small coalitions are both rare and carry most of the positive interaction, that is the finding.
5. **Whether the evaluation-time candidate generator can even propose a small coalition.** A head that never saw size 2 is one failure; a selector that is never offered size 2 is a different and simpler one. Check both and say which apply.

## Also check the within-anchor coverage
More anchors do not substitute for varied coalitions at the same anchor. Report how many distinct coalitions exist per anchor and how many distinct sizes, since identifying interaction coefficients needs variation within an anchor, not across anchors.

## Workspace
Read-only analysis is preferred. If you must write, use `/home/sat/mcrl-v025-coverage-ws`: `mkdir -p` it, `git init`, commit an empty baseline. **Never modify `/home/sat/mcrl-v025-pilot-ws`, `/home/sat/mcrl-v025-selector-ws`, `/home/sat/mcrl-v025-harness-ws` or any other workspace; several jobs are editing them.** Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or `/home/sat/mcrl-v025-codex-ws-engine`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Two processes maximum, `nice -n 15`.

Write `COALITION-COVERAGE-2026-09-09.md` in the coverage workspace and print it as your final message. Lead with the size histogram and one sentence saying whether sizes two to six are adequately represented.
