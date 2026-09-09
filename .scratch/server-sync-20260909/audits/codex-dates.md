# Measure the paired-contrast date variance, which has never been measured

`DIAGNOSTIC_NOT_CLAIM`. Budget 3 hours. This is the item with the longest lead time and it is independent of every learner defect, so it runs in parallel with all of them.

## Why
The confirmatory design clusters on `(world start date, learner seed)` and treats date as the dominant variance term. **There is exactly one completed evaluation date**, `2025-11-16`, on one world. With one date the sample standard deviation of the paired contrast across dates is undefined, so the `0.05` assumed by the power simulation has never been measured against anything.

The archive at `~/demo/tle_data/starlink/tle` holds **373 daily ephemeris files**, and normal world construction derives its epoch from `world_seed` without any special handling, so more dates need no new machinery.

## Task
1. **Enumerate what exists.** Report which dates the sealed world manifests already use, which TLE dates are available, and confirm the split convention so that no evaluation date can collide with a training date. **Do not open, sample from, or generate anything on a date reserved for TEST.** If the split convention is unclear from the code, stop and report that rather than guessing.
2. **Generate world tapes on at least 12 distinct dates**, spread across the archive rather than clustered in one month, using the existing provider and the corrected physics from `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c`. Keep every other world parameter identical to the existing worlds so date is the only thing that varies. Record each world's digest and start time.
3. **On each date, evaluate a small fixed arm set** with the exact evaluator: BASELINE, the certified iterated unilateral optimum, and the bounded perfect-knowledge set selector, at a handful of anchors. These need no learner and no training, so they isolate the date axis cleanly.
4. **Report the paired log contrast per date**, `log(EE_oracle) - log(EE_unilateral)`, and give its **sample standard deviation across dates**. That single number is the deliverable: it is the quantity the power simulation assumes to be 0.05 and which nobody has measured.

Also report the mean contrast, the minimum and maximum, and whether any date is an outlier, since a design sized from a variance driven by one unusual date would be wrong in a different way.

## What not to do
Do not size the confirmatory experiment; that needs effect sizes and margins this task does not have. Do not change any threshold, sign, seed, horizon, price, service guard or acceptance rule. Do not touch the sealed manifests; write new ones under your own workspace. Generating candidate worlds does not commit the project to using them, and nothing here selects a date by its outcome: the dates are chosen by spread across the archive before any result is seen, and **every generated date must be reported**, including any whose contrast is unfavourable.

## Constraints
Workspace `/home/sat/mcrl-v025-dates-ws`, built from the archive command above, then `git init` and commit. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. **World tapes are about 800 MB each: write them under `/home/sat/bigtmp`, never `/tmp`, which is a RAM-backed tmpfs on this host and has already caused one out-of-memory stall today.** Build tapes sequentially, not in parallel, and delete each one after its evaluation unless you need it again. At most 3 processes, `nice -n 12`.

Write `DATE-VARIANCE-2026-09-09.md` in the workspace root and print it as your final message. Lead with the measured standard deviation of the paired log contrast across dates, and how many dates it is computed from.

## Wider scope, added before you started
The date shortage is not only a statistics problem. **The training corpus is also derived from two worlds**, `V025_PROBE/world/1` and `world/2`, while the archive holds 373 ephemeris days. The coalition corpus of 180 rows is 90 anchors times those two worlds. Ten times the worlds would give ten times the anchors from the same generation rule, with real geographic and geometric variety rather than synthetic augmentation.

So report two things beyond the variance measurement:

**A. Constellation-size confound.** Report the satellite count in each ephemeris file you use. The constellation grew across the archive, so variance measured across dates ten months apart partly reflects a larger constellation rather than different geometry. Say how much of the spread that could account for, and report the variance both across widely separated dates and across dates within one month so the two are separable.

**B. The cost of generating many worlds.** Measure and report the wall time, core time and peak disk for building **one** world tape end to end. Then state what 20, 50 and 100 worlds would cost in wall time and storage, given that tapes are about 800 MB each and must be written under `/home/sat/bigtmp`. This converts "we should use more of the archive" into a number the owner can decide on.

Prefer **recent** dates for anything intended to represent the current constellation, and a deliberate spread only for the variance measurement. State which dates you used for which purpose.
