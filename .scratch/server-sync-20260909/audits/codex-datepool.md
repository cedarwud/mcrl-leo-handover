# Adjudicate: there is no rule keeping evaluation dates off training dates

A parallel review is being done by a different model. Give your own independent judgement; do not try to anticipate theirs.

Read `/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-OPEN-DECISION-EVAL-DATE-POOL-2026-09-09.md` and the report that found the gap, `/home/sat/mcrl-v023-codex-audits/parallel-20260909/DATES-CODEX-2026-09-09.md`. Verify the four code claims yourself rather than accepting them; the files are named in the report.

## Established
The executable ephemeris split is a 16-day cycle from 2025-07-27: seven TRAIN, one embargo, seven TEST, one embargo. The provider is fail-closed against TEST starts and TEST reads, and the embargo means a TRAIN start's element window cannot reach a TEST date. That protection is about TEST only. Nothing separates evaluation dates from training dates.

Archive: 373 daily files, 2025-07-27 to 2026-08-20, 166 of them TRAIN, with seventeen dates missing inside the span. The satellite count rises from 8,044 to 10,746, about 34 percent, across it.

A sealed non-negotiable says "no TEST split". The controller now reads that as "the headline must not rely on the held-out set" rather than "no partition exists". Check that reading against the sealed documents.

## Options
A. Carve a declared evaluation-only pool from the 166 TRAIN dates, never used for source generation, with its own embargo against training dates.
B. Use TEST as the evaluation pool.
C. Keep the arrangement, declare the overlap, and quantify it by comparing overlapping against non-overlapping dates.

The controller favours A and believes the cost is small because training dates are abundant.

## What I want
1. Which option, and why. **Attack the controller's reasoning rather than confirming it.**
2. A fourth option, if one exists: a different splitting variable, or a design where overlap is provably harmless.
3. How much does date overlap actually matter for this model class? The learner sees geometry derived from ephemeris. Is memorising one date's geometry a realistic failure mode or a theoretical worry? The constellation grew 34 percent across the span, so distant dates differ in size as well as geometry.
4. If A is chosen: how to size and spread the pool, given that date variance has never been measured and seventeen dates are missing.
5. Every place the controller's framing is wrong or overstated, quoting the sentence.

Read-only. Change nothing. Write `DATEPOOL-ADJUDICATION-2026-09-09.md` in the workspace root and print it as your final message, leading with your choice in one line.
