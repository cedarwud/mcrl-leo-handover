# Multi-Catfish EE-axis Opus Max co-design adjudication

Date: 2026-08-31  
Reviewer route: `claude --model opus --effort max`  
Mode: read-only adversarial review and alternative design  
Verdict: **REDESIGN**

## Decisive findings

1. A multiplier computed from each short candidate window proves only local
   window-ratio improvement. It does not target the episode ratio-of-sums and
   destroys cross-window additivity when the multiplier changes by window.
2. Summing the unchanged per-step `r1` is a sum of ratios, not the reported
   ratio of sums. The two orderings can reverse.
3. `Full - noT` removes recurrence physics and changes service/load/rate, so it
   is not cleanly separate from the direct EE pathway.
4. `Full - noS` is incompatible with the simulator guard requiring beam load
   to equal the load implied by served associations.
5. The live 112-dimensional state omits segment-start state for Q2 and current
   spatial marginal-cost context for Q3. Training longer cannot repair this
   information loss.
6. The proposed common bootstrap used incompatible successor horizons. The
   initial redesign should use fixed-H pairwise targets with zero bootstrap.

## Co-designed replacement

The reviewer proposed one fixed global Dinkelbach multiplier and the exact
partition adopted in V0.2:

\[
z_1=g_0^{\mathrm{iso}},\qquad
z_3=g_0^{\mathrm{sys}}-g_0^{\mathrm{iso}},\qquad
z_2=\sum_{k=1}^{H-1}g_k^{\mathrm{sys}}.
\]

Therefore

\[
z_1+z_2+z_3=g_{0:H}^{\mathrm{sys}}.
\]

This removes legacy handover/load direction gates, avoids a second inconsistent
physics account, and gives direct, temporal, and spatial routes a common EE
unit. It remains a candidate until the isolated evaluator, state sufficiency,
unilateral support, and action-headroom gates pass.

## Reusable R6 work

- one-step copied-RNG `evaluate_actions` and preview/commit parity;
- C2 common anchor, branch-local Main, sealed candidate schedule, physical-ID
  binding, trace lineage, transaction, and resume machinery;
- head-pivotality tools and ratio-of-sums evaluation;
- service, zero-power, and single-load-semantics guards.

Legacy positive `r2/r3` gates, old target scales, independent per-head max
bootstrap, fading-disabled target twins, and previous support counts are not
reusable as scientific evidence.

No training was run and the reviewer did not modify the worktree.
