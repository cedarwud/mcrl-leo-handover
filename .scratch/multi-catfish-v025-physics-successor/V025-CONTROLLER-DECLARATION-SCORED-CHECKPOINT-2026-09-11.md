# Declaration — which checkpoint is scored, fixed before any exact-corpus EE exists

Date: 2026-09-11 ~00:25Z · Controller
**No EE has been computed from the 93-anchor exact corpus. CONVSCORE (22-anchor exact and Q1 v3
runs) has been dispatched but has not reported.**

## The gap

`EXACT93-TRAINING-2026-09-10.md` applied the unchanged stopping rule offline to seed 1:
first admissible update **C1 800, C2 2,200, C3 2,200**. Two problems with using that directly:

1. **The rule is per route, but a checkpoint carries all three routes.** There is no single
   checkpoint that is "the first admissible one" for every route at once.
2. **C1's admissibility is not persistent**: admissible at 800, fails again at 900 and 1,900,
   with in-sample level R2 `-0.034` — "stable without fitting well".

And a stated deviation: **the corpus has no held-out split**, so the rule's R2 / ordering / top-1
were measured in-sample. That makes the stability test weaker, not stronger. It remains a
convergence check, never a quality claim.

## Declared now

- **Primary scored checkpoint: the final update, 4,000.** Under the declared step decay the rate
  is `1e-5` from update 3,000; every route is past its first admissible point; one checkpoint
  serves all routes.
- **Secondary, reported alongside:** the first cadence point at which **all three routes are
  simultaneously admissible and remain admissible at every later cadence point**. If no such
  point exists for a seed, report that seed as non-persistent and score only the primary.
- **Neither choice may be revised after seeing EE.** If they disagree, both are reported.

This applies to every exact-label, step-decay run: the 22-anchor exact run, Q1 v3, Q1 v3
control, and the 93-anchor run.

## Why this is not outcome-selection

The evidence used — non-persistence of C1 admissibility and the per-route/shared-checkpoint
mismatch — comes from loss and in-sample fit diagnostics, **never EE**. No EE from these runs
exists at the time of writing.
