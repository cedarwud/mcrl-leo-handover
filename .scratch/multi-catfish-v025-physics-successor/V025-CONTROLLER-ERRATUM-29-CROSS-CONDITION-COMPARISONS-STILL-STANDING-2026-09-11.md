# Erratum 29 — cross-condition comparisons still standing in in-force documents

Date: 2026-09-11. Source: CURATE — `.scratch/RESULTS-REGISTRY.md` (503 rows; §2 lists 30 cross-condition
comparisons in in-force documents) and `.scratch/DOCUMENT-STATUS.md` (status of every document, in-force
reading list at the top). **Those two files are now the authority for whether a number may be used and
whether a document is in force.** Affected documents carry a provenance banner; their text is not rewritten.

## The three worst

1. **62.502712 Mbit/J vs 41.28** — an EE against a mean beam count, across panels, with a search winner read
   as a rule. Withdrawn by erratum 23, but still verbatim in the catfish-attaches ruling (line ~57), the
   two-arm demo declaration (lines ~18-20) and the DQfD grounding report.
2. **"No demonstrator beats the learner"** (erratum 23 table; per-head-bootstrap finding) — scripted rules
   scored greedily on the **unpinned local** archive vs the trained reference **+0.8859 taken from the frozen
   run's own ε-greedy training log on the pinned archive**. Host, archive, exploration, episodes and estimand
   all differ. (Already withdrawn by erratum 27 on other grounds; now also known to be cross-condition.)
   Same class: erratum 28 calling `sat` CAPPENALTY results "consistent with" local FEASFRONT ones.
3. **The V0.25 slope −425,009.885 bit/J applied to the MODQN harness** (erratum 24, erratum 26) — withdrawn
   by erratum 28, text unchanged.

## Also invalid: two paired statistics

On this harness only evaluation episode 0 is paired across arms (CFSCREEN). So the paired `+0.0091, ~2.7 sem`
(`GREEDY_R1R2 − GREEDY_SCALARIZED`) in erratum 25 and B0's paired t values are invalid as paired statistics.
Erratum 25's use of that number as independent support for "r3 mildly hurts" is withdrawn; the r3 point
rests on the power-model argument (itself now model-dependent, erratum 28).

## Conflict resolved: the V0.25 learner's EE on the 12-anchor panel *was* measured

Erratum 23 said the learner's EE on that panel was never measured (BEAMCOUNT's Part 3 did not complete). A
server report, `ZSCORE-VIEW-AND-TRAINING`, measured it: **26.83 / 29.18 / 29.95 Mbit/J, in-sample, epoch 500**.
Erratum 23's statement is corrected to: *not measured by BEAMCOUNT; measured elsewhere in-sample at epoch
500*. This concerns the V0.25 stage-C learner, a closed line; no in-force decision depends on it.

## Process failure, recorded

I committed CURATE's in-progress drafts with a blanket `git add .scratch/` — the practice I said after the
fabricated-placeholder incident I would stop. From now on the controller stages only named paths.
