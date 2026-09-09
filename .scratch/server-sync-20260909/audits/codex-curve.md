# How many labels does the interaction component actually need? Measure it, do not guess.

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. Wait for `COALITION-CORPUS-2026-09-09.md` to appear in `/home/sat/mcrl-v025-coalgen-ws`; poll every 3 minutes for up to 75 minutes. If it never arrives, run the curve on the existing 180 rows alone and report only the part you can, saying clearly that the large-corpus points are missing.

## The question
The per-user components are trained on **176,223** rows across 180 anchors, about **979 rows per anchor**. The interaction component is trained on **180** rows, **one per anchor**. That is a density ratio near one to a thousand.

I do not know how many labels the interaction component needs, and nor does anyone else on this project. Matching the per-user density would need roughly 176,000 exact coalition evaluations, which is not affordable. So the useful question is not "what is the target" but **"are we data-limited, and by how much"**.

## What to measure
Train the interaction head on nested subsets of the available corpus and plot the curve. Use at least the sizes 180, 400, 800, 1600, 3200 and the full corpus, or whatever subset of those the corpus supports.

Subsample **by anchor**, not by row, so that each point is a coherent design and the held-out anchors are genuinely unseen. Report at each size:

* held-out R-squared against the exact interaction, using the same deterministic fold assignment throughout;
* **within-anchor selection quality**: how often the model picks the exactly-best candidate at a held-out anchor, and the regret against it. This matters more than the fit, because selection is what the coordinator does;
* the realised pooled energy efficiency of the selected configurations, since that is the outcome the owner cares about;
* the same three numbers for a **size-only baseline** and a **zero-interaction baseline**, so it is visible whether the model beats trivial alternatives at each corpus size.

## The answer I need
State plainly which of these the curve shows:

1. **still climbing at the largest size** — we are data-limited, and extrapolate roughly how many labels would be needed to reach a stated selection-quality target;
2. **flat from early on** — data volume is not the bottleneck, and my hypothesis that the interaction component is starved should be withdrawn;
3. **climbing then flat** — name the size at which it saturates, since that is the corpus target and everything beyond it is wasted compute.

Report the label cost too: wall time and physics-call count per new coalition label, with the baseline and singleton values cached per anchor so an additional coalition costs one evaluation. That converts the answer into a compute budget.

## Also split the curve by coalition size
If the corpus contains sizes 2 through 6, report the curve separately for coalitions of size 2 and for size 3 and above. The pairwise cross-gain structure should matter more at three and above, and a curve that saturates for pairs while still climbing for triples would locate the shortage precisely.

## Constraints
Workspace `/home/sat/mcrl-v025-curve-ws`: build with `cp -a /home/sat/mcrl-v025-coalgen-ws /home/sat/mcrl-v025-curve-ws` once the corpus exists, else from `/home/sat/mcrl-v025-pilot-ws`; then `rm -rf .git`, `git init`, commit. Never modify any other workspace. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or `/home/sat/mcrl-v025-codex-ws-engine`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here. At most 3 processes, `nice -n 12`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule. Subsampling a corpus for a learning curve is a diagnostic, not a change to the method.

Write `LABEL-BUDGET-CURVE-2026-09-09.md` in the workspace root and print it as your final message. Lead with which of the three answers the curve gives, then the table.
