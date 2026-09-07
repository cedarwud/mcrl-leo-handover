# Multi-Catfish C2 Fable 5.1 clean-room review

Date: 2026-09-02  
Status: `INDEPENDENT_REVIEW_COMPLETE__LOCAL_ADJUDICATION_PENDING`  
Claim ceiling: reviewer analysis; no implementation, training, or efficacy claim

## Provenance

- model: Claude Fable 5.1;
- effort: max;
- session: `2bbcc549-517e-4650-ba1b-b6d6dbbec522`;
- mode: read-only clean-room review;
- duration: about 34.8 minutes of API time;
- file edits: none;
- simulator or learner runs: none;
- TEST split: not opened by the review.

The review inspected current formula, simulator physics, frozen C1/C3 evidence,
V0.5 through V0.7 C2 failures, and existing TRAIN-development artifacts. Its
conclusions remain reviewer findings until reproduced or adjudicated locally.

## Bottom line

Fable classified a positive third Catfish as **possible but unproved**: neither
physically established nor structurally impossible. It agreed that V0.7
focal-next C2 should be retired.

Its central diagnosis was:

1. the old scalar handover penalty does not enter final delivered bits or
   network energy;
2. switching has no explicit interruption cost in the current simulator;
3. the clean temporal physical channel is the focal user's carried power
   segment and its future recurrence-power/feasibility consequence;
4. large network-wide successor effects are continuation-policy cascades and
   were not identifiable from the focal state in V0.6/V0.7;
5. C3 is positive only in the old-Q2 context and must be rechecked with any new
   C2 before training.

## Evidence emphasized by the review

- C1 is the strongest current route. Its reported marginal is positive in all
  three available route contexts, although those are not new confirmatory data.
- C3 is learnable, but `Q1+Q3` versus `Q1` is `-10.286%` pooled EE because bits
  rise about `13.5%` while energy rises about `26.6%`.
- V0.7 R13 is effectively zero: pooled `+0.0465%` with mixed lineages and a
  bootstrap interval crossing zero.
- V0.7 R14 fails leave-one-anchor-out generalization against the strongest
  null in all three lineages.
- In a read-only recomputation over the existing R11 files, the same-anchor
  Q2 state bytes/reference action were identical across lineages, while the
  28-action target rankings were nearly unrelated: median cross-lineage
  Spearman `0.085`; median sign disagreement `71%` on rows above `0.05*kappa`.
  This is a reviewer recomputation and should be independently reproduced
  before it becomes project authority.

## Ranked candidate recommendation

Fable ranked three ideas:

1. orbital look-ahead option value;
2. deterministic hold-life surplus;
3. next-slot held-beam interference externality.

Only the first received `GO_FORMULA_CENSUS_ONLY`. None received learner or
episode-training authority.

### Proposed top target

At a predecision anchor `(world,t,u)`, let `m` be the frozen `Q1+Q3` Main
action and let `a` enumerate every current native legal action. Commit opening
candidate/reference branches differing only for focal user `u`. At offset one,
use a common declared background for non-focal users and define each branch's
focal native option set `O_b`. For branch `b` and option `o`, Fable proposed

\[
e_b(o)=\Delta t\left[R_u^b(1;o)-\lambda_0
\left(P_b^N(1;o)-P_{b,-u}^N(1)\right)\right],
\]

\[
V_b=\max_{o\in O_b} e_b(o),\qquad
z_{2,u}(a)=V_C-V_M.
\]

The reference row must be exactly zero and every sign must be retained. The
maximum is a training-target operator, not an extra deployed argmax. Deployment
would still use the direct `Q1+Q2+Q3` score.

### Proposed state and source

- start from the V0.7 Q2 state;
- add one action-aligned 28-value next-slot candidate-SINR forecast block;
- select all predecisions with at least three legal actions along frozen
  `Q1+Q3` trajectories;
- enumerate all native legal current actions;
- stratify only by deterministic ephemeris features such as remaining D2
  legality and dwell phase;
- retain all target signs and all predeclared rows.

## Proposed fail-fast ladder

Fable recommended, before any learner:

1. mechanics invariants and exact reference zero;
2. 24 fresh TRAIN anchors for target spread, positive alternatives, scale, and
   oracle pivotality;
3. 12-anchor agreement between a closed-form forecast and exact target;
4. 20 fresh matched worlds times three lineages for the three directions:
   `FULL>DROP-C2`, `FULL>DROP-C3`, and `FULL>DROP-C1`;
5. only then a world-disjoint observability test and bounded learner.

The review suggested a `+1%` pooled C2 directional threshold at the oracle
interaction screen, service non-inferiority, and positive support in at least
two of three lineages. These numerical thresholds are proposals, not frozen
project rules.

## Issues requiring local adjudication

The proposal is not implementation-ready until all of these are resolved:

1. **Native-support semantics.** “Hold if legal, otherwise physical no-op” must
   be defined without importing an action across branches, skipping a row, or
   reintroducing the V0.5 controlled-tape support defect.
2. **Background equality.** The non-focal offset-one physical vector must be
   demonstrably the same in candidate/reference branches or the estimand again
   includes policy cascades.
3. **Option-set causality.** A branch-local next-slot maximum may measure future
   opportunity rather than a causal consequence of the opening action; its
   scientific interpretation must be explicit.
4. **Decision-time observability.** The proposed next-slot SINR block must be
   computable from ephemeris plus committed lagged state, using declared fading
   and shadow assumptions.
5. **Scale.** The target must use the same frozen `lambda0` and shared `kappa`
   as Q1/Q3; final sign must still be measured from raw matched ratio-of-sums.
6. **C3 interaction.** Passing C2's own marginal is insufficient if the new Q2
   makes `FULL-DROP-C3` nonpositive.

## Current authorization

- formula and source-design census: allowed;
- bounded no-training oracle screen: allowed after a written contract;
- Q2 learner: not yet allowed;
- 500/1500/3000/9000-episode training: not allowed by this review.
