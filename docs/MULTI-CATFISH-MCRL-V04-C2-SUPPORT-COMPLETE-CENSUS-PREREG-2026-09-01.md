# Multi-Catfish MCRL V0.4 support-complete C2 census preregistration

Date: 2026-09-01  
Status: `PREOUTCOME_WORK_ORDER`  
Claim ceiling: `FRESH_TRAIN_DESIGN_PROBE_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY`

## 1. Question

The sealed five-arm result found that the frozen C2 head reduced marginal EE.
The post-outcome forensic audit found that old Q2 was trained on one temporal
sibling per state although deployment ranks every legal action.  This probe
asks whether complete within-state temporal supervision is a physically
credible repair.

This work order cannot establish that rebuilt C2 improves EE.  It can only
establish the physical authorization gates for the bounded candidates frozen
before outcomes in
`MULTI-CATFISH-MCRL-V04-C2-PARALLEL-CANDIDATE-PREREG-2026-09-01.md`.

## 2. Frozen boundaries

The probe changes no training or deployment quantity:

- final endpoint: canonical ratio-of-sums EE;
- \(\lambda_0=84{,}994{,}621.12635651\) bit/J;
- \(\kappa=10{,}097{,}071{,}012.757404\) bit;
- \(H^c=4\), with downstream offsets \(k=1,2,3\);
- the existing downstream target \(\zeta_{2,u}\);
- hold-while-legal followed by one monotone release;
- the three frozen initialization lineages `2026092101`, `2026092102`, and
  `2026092103` at V0.3 Q2 rung 10;
- the selected V0.4 Q3 rung 100 and frozen Q1/Q3 bytes;
- direct unweighted `Q1 + Q2 + Q3`, one common mask, and one argmax.

No optimizer, replay insertion, learning-rate selection, checkpoint selection,
TEST row, or held-out EE endpoint is permitted.

## 3. Fresh world and anchor schedule

The ordered TRAIN-only candidate seeds are exactly
`2026092801`--`2026092810`.  All ten are design-only and may never enter a
later train, validation, or TEST split, whether or not their topology is
selected.

For each seed, replay frozen Main and inspect only predecision state.  Search
steps in increasing order, starting at step 1 and stopping at the last step
that leaves four complete forecast offsets.  The first step is eligible when:

1. at least four users are physical Main departures;
2. each selected user has a legal physical Main reference;
3. each selected user has all 28 legal action slots and exactly 27 unique
   legal non-Main physical alternatives; and
4. the opening candidate table has no physical aliases.

Select the four lowest eligible focal-user identifiers at that first eligible
step.  Select the first three eligible seeds in the fixed seed order.  If three
worlds cannot be scheduled, preparation fails without opening a detached
counterfactual outcome.

The resulting schedule has exactly three worlds, one anchor per world, four
focal clusters per anchor, and 27 non-Main siblings per cluster: 12 clusters
and 324 sibling comparisons.  The contemporaneous Main action is a shared
reference with physical target zero.  Every candidate, including negative and
support-expired outcomes, must be retained.

Before any forecast, the sealed schedule binds the complete sorted action
mask, Main action/key, incumbent key, candidate action/key list, source seed,
world/anchor/focal identity, evaluation seed, checkpoint/source/policy lineage,
and common keyed-fading root.  The source rule is exactly
`c2-support-complete-legal-nonmain-v1`.

## 4. Phase A: Main-continuation census

Each scheduled sibling is evaluated once with the existing branch-local Main
continuation and keyed common-random field.  Define

\[
\widetilde{\zeta}_{2,u}(a)=\frac{\zeta_{2,u}(a)}{\kappa},
\qquad
r_{i,u}=\max_{a\in\mathcal A_u}\widetilde{\zeta}_{2,u}(a)
-\widetilde{\zeta}_{2,u}(a^{Q_2_i}),
\]

where the Main reference is included in \(\mathcal A_u\) with target zero and
\(a^{Q_2_i}\) is the legal argmax of old Q2 initialization \(i\).

The old supervised pair is reconstructed pre-outcome using the frozen V0.3B
rule: incumbent hold when legal, otherwise the maximum-lagged-candidate-SINR
non-Main rival.

### G-S: sibling signal is non-degenerate

All conditions must pass:

1. among non-incumbent siblings, at least 70% pooled and at least 60% in each
   world have `release_offset >= 2`;
2. the pooled median non-incumbent
   \(|\widetilde{\zeta}_{2,u}|\) is at least `0.5`; and
3. at least 9 of 12 clusters have sibling-target IQR at least `0.5`.

Any missing scheduled outcome is a failure; `support_expired` is a retained
physical outcome, not a missing row.

### G-R: the old Q2 has material physical regret

All conditions must pass:

1. over the 36 initialization/cluster observations, median \(r_{i,u}\) is at
   least `1.0`, at least 27/36 regrets are strictly positive, and each
   initialization has at least 8/12 positive regrets; and
2. in at least 8/12 clusters, the physical-best action lies outside the old
   supervised pair and exceeds the better member of that pair by at least
   `0.5` normalized units.

For diagnosis only, record Spearman correlation between physical targets and
the fixed predecision heuristic

\[
h(a)=R(\log(1+\mathrm{SINR}_a))-R(L_a)-R(P_a),
\]

where \(R\) is the within-cluster average percentile rank, \(L_a\) is eligible
served load, and \(P_a\) is maximum required link power from the frozen causal
state.  This is non-blocking because it tests whether a simpler ranker may
exist, not whether support-complete C2 can improve EE.

### G-V: delivered-bit protection

For each cluster, rank non-Main siblings by physical \(\zeta_2\).  At least one
of the top three must have nonnegative downstream total-delivered-bit delta
relative to Main.  This must hold in at least 9/12 clusters and in at least
three of four clusters in at least two of the three worlds.

Served fraction is reported but is not a gate because the sealed C2 failure
lost far more bits than served-user decisions.

If any Phase-A gate fails, the exact support-complete-temporal formulation is
`FORMULATION_REDESIGN_REQUIRED`; Phase B and retraining are forbidden.  C2
itself remains mandatory and returns to formula/physics redesign.

## 5. Phase B: continuation robustness

Phase B runs only when G-S, G-R, and G-V all pass.  It replays the same sealed
siblings under each of the three frozen DROP-C2 (`Q1 + Q3`) continuations.
Reference and candidate branches use that same frozen continuation; while the
candidate key remains legal, only the focal opening intervention is held, then
released once.  The keyed fading root is identical across Main and DROP-C2
continuations and excludes candidate action and initialization seed.

For each initialization/cluster, compute Spearman correlation between the 28
Main-continuation targets and the 28 DROP-C2-continuation targets, including
the shared zero reference.

### G-C: continuation ranking is stable

An initialization passes when its median cluster correlation is at least `0.6`
and at least 8/12 cluster correlations are at least `0.6`.  At least two of the
three initializations must pass.  In addition, at least two of three worlds
must have median correlation at least `0.6` over their four clusters and the
passing initializations.

The probe also reports, without gating, target-ranking correlation after
replacing \(\lambda_0\) by the already-observed DROP-C2 operating ratio
`105,010,574.08` bit/J.  This is sensitivity reporting only and cannot change
the canonical target or select a multiplier.

## 6. Decision and mandatory C2 invariant

- Any Phase-A gate fails: `FORMULATION_REDESIGN_REQUIRED`; no learner loss can
  repair an absent or unsafe physical temporal signal.
- Phase A and G-C all pass: P0 and the arm-specific Q13 candidates may enter
  `AUTHORIZE_PARALLEL_SUPPORT_COMPLETE_C2_SCREEN` under the separately frozen
  parallel-candidate preregistration.
- Phase A passes but G-C fails: P0 is ineligible, while the matched-Q13 P1/P2
  candidates are judged by their separately frozen arm-specific physical
  gates.  Failure of Main-versus-Q13 agreement cannot by itself reject a
  formulation expressly designed to remove that mismatch.
- No candidate passes its applicable physical gates:
  `FORMULATION_REDESIGN_REQUIRED` for this exact candidate batch.
- Thresholds may not be changed after outcomes, and this probe may not be
  rerun with replacement seeds.

There is no method-level `DROP_C2`, `RETIRE_C2`, or two-Catfish outcome.  The
eventual method must pass fresh, frozen marginal EE comparisons

```text
FULL > DROP-C1
FULL > DROP-C2
FULL > DROP-C3
FULL > Main
```

before it can be described as an effective Multi-Catfish algorithm.  A passing
probe authorizes only the bounded offline Q2 candidate screen fixed in the
parallel-candidate preregistration, not 1500/3000/9000 simulator-episode
training.  The user must be notified before any 9000-episode run.
