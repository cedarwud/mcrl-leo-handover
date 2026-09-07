# Multi-Catfish V0.23 training-readiness map

Updated: 2026-09-07 01:10 (Asia/Taipei)

This is an implementation control note, not paper authority or scientific
evidence.  `TEST` remains closed.

## Completion signal for the next stage

The 100-source-training-epoch five-arm screen may start only after all of the following are
true and rechecked together:

1. C1/C2 target root is sealed `COMPLETE` and loads into typed informed and
   neutral batches.
2. The one-shot R7 C3 successor Gate has a valid terminal decision under its
   frozen balanced metric.  Only its contract-authorized passing token admits
   the C3 source/learner into the episode screen.
3. Five independent source-training policies are trained from identical initial
   bytes with the exact source-ablation mapping and no head drop.  Their first
   diagnostic label is `ALL_NEUTRAL_CONTROL`, never `BASELINE`.
4. One real TRAIN/TLE world completes the five source-training diagnostic arms
   through the current three-route policy and structured C3View, with no
   learner update during evaluation and no TEST access.  The later primary
   physical evaluation separately binds `BASELINE` to the authenticated
   pre-Catfish MODQN policy and excludes `ALL_NEUTRAL_CONTROL` from its five
   Chapter-5 curves.
5. The runner persists a checkpoint every 100 complete `C1 -> C2 -> C3`
   source-training epochs and the
   five-arm receipts bind the exact policy/source/world identities.

## Verified complete

| Item | Current evidence | Boundary |
| --- | --- | --- |
| Three-route learner update seam | `.scratch/multi-catfish-v023-heterogeneous-trainer`; 6 tests pass | Implementation only |
| Target-to-batch adapter | `.scratch/multi-catfish-v023-target-batch-adapter`; 9 tests pass | Synthetic authenticated fixtures; real root pending |
| Current opening-feasibility provider | `.scratch/multi-catfish-v023-current-c3view-provider`; 3 tests plus actual dependency import pass | Plumbing only |
| D40 compatibility disposition | `.scratch/multi-catfish-v023-d40-current-loader`; 10 tests pass | D40 Q1/Q2 are not current learner initialization |
| Five-arm learner orchestrator | `.scratch/multi-catfish-v023-five-arm-learner-orchestrator`; 5 tests pass | Implementation only; schema v3 uses `ALL_NEUTRAL_CONTROL`; formal checkpoint cadence is 100 complete C1/C2/C3 epochs |
| Five-arm source-training runner | `.scratch/multi-catfish-v023-five-arm-training-runner`; 4 tests pass | Implementation only; schema v2 checkpoints/exports the all-neutral model only as `ALL_NEUTRAL_CONTROL`; a cross-layer invariant prevents it from aliasing physical `BASELINE` |
| Runner/provider epoch-horizon binding | focused runner test is red-capable and now passes | The provider must declare `planned_epoch_budget`; a 100/500 mismatch is rejected before any learner is constructed |
| Provider/orchestrator bridge | `.scratch/multi-catfish-v023-provider-orchestrator-bridge`; 9 tests pass, including a complete synthetic 100-epoch/300-update formal schedule | Implementation only; full authenticated C1/C2 panels repeat for the declared epoch budget, while C3 requires an exact precomputed schedule; real inputs pending |
| Post-R7 provider factory | `.scratch/multi-catfish-v023-post-r7-provider-factory`; implementation and independent audit completed, hardening tests in progress | Reconstructs a provider only from sealed R7 GO plus sealed C1/C2 targets; no simulator or learner update |
| Frozen 100-epoch learner screen | `.scratch/multi-catfish-v023-100e-screen-preoutcome/`; exact model/provider configs and source-arm mapping frozen before terminal outcomes | Conditional execution only; every 100 source-training epochs is a formal checkpoint |
| Real one-world source-training diagnostic plumbing | `.scratch/multi-catfish-v023-real-one-world-plumbing`; 3 focused tests pass | Implementation only; schema/domain v2 use `ALL_NEUTRAL_CONTROL`; exact diagnostic order, current complete three-head checkpoints, shared keyed TRAIN world, fresh environment per arm, and fixed-policy evaluation are enforced; real checkpoints pending |
| Primary physical source/evaluation binding | `.scratch/multi-catfish-v023-ablation-prep` and `.scratch/multi-catfish-v023-five-arm-evaluation`; 29 combined tests pass | `BASELINE` remains the external authenticated pre-Catfish MODQN policy; the primary five curves exclude `ALL_NEUTRAL_CONTROL` |
| Real five-arm episode-runner seam | `.scratch/multi-catfish-v023-episode-screen`; 6 focused tests pass | Pre-execution implementation only; no physical episode was opened |
| Baseline namespace adjudication | `.scratch/multi-catfish-flow-audit-20260906/BASELINE-SEMANTICS-ADJUDICATION-20260906.md`; controller cross-layer checks pass | Namespace correction only; no scientific outcome |

## Running now

| Item | Live handle | Current meaning |
| --- | --- | --- |
| C1/C2 target generation | server root `/home/sat/mcrl-v023-c1c2-target-generation-20260906-d40-r4`; controller PID 1222738, informed PID 1222739, neutral PID 1222740 | Target generation, not episode training |
| R7 balanced successor Gate | run root `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`; controller PID 1773147 | At the 2026-09-07 01:10 poll, source and fit artifacts were complete and 16 of 48 composition JSON results existed; the whole result was not yet sealed, so no outcome was opened |

## Current hard dependencies

- C1/C2 real batch admission waits for the running target root to emit
  `COMPLETE`, `receipt.json`, and `MANIFEST.sha256`.
- C3 episode admission waits for the one-shot R7 Gate result.  R7 must not be
  silently replaced by another metric revision after its outcome is opened.
- A valid R7 non-GO ends the LC-SRS route.  A valid GO admits exactly one
  separately frozen learner screen; it is not itself an efficacy result.
- The five-arm orchestrator and provider bind sampler/file cursors, the exact
  epoch budget, panel membership, model state, and optimizer state so
  continuation after checkpoint is bit-identical.
- A real five-arm policy artifact must be produced by learner execution.  D40
  remains source/background provenance and may not be relabelled as a current
  trained policy.

## Explicitly removed from the critical path

- Loading the full D40 Q1/Q2 checkpoint into `EEAxisLCSRSThreeRoute`.
  Authenticated D40 uses historical scorer widths and its Q2 is a retired
  representation; exact loading is structurally impossible and prohibited.
- Further C3 formula redesign before the single R7 outcome.
- Thesis, symbol-table, slide, and figure updates before the method/training
  evidence stabilizes.
- Any use of the all-neutral current three-route policy as the primary physical
  `BASELINE`; that policy is now named `ALL_NEUTRAL_CONTROL` and is diagnostic
  only.
- Any TEST split, 1500/3000/9000 run, or efficacy statement before the
  100-source-training-epoch five-arm screen.
