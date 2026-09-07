# Multi-Catfish C3 source-level derivation (working note)

Date: 2026-09-04  
Status: **NON-AUTHORITY / READ-ONLY DERIVATION / NO NEW OUTCOME**

This note records a formula-first check while the independent clean-room
reviews are pending.  It does not amend the current method, authorize a new
world, or authorize episode training.

## 1. Canonical endpoint

For a finite policy trace with positive energy,

\[
\eta(\pi)=\frac{\mathcal B_\pi}{\mathcal E_\pi}.
\]

For a matched reference policy \(M\), let
\(\lambda_M=\mathcal B_M/\mathcal E_M\).  Then

\[
\eta(C)>\eta(M)
\iff
\mathcal B_C-\lambda_M\mathcal E_C>0
\iff
\Delta\mathcal B-\lambda_M\Delta\mathcal E>0.
\]

This is exact only when the multiplier is the EE of the actual matched
reference trace.  A multiplier frozen from a separate calibration policy or
window is a common-unit surrogate, not an exact per-window equivalence.

## 2. Exact unilateral accounting

For one focal opening action and one frozen matched continuation, the V0.3
accounting is algebraically non-overlapping:

\[
z_1=\Delta B_{u,0}-\lambda_0\Delta E_0,
\qquad
z_3=\sum_{v\ne u}\Delta B_{v,0},
\qquad
z_2=\sum_{k\ge1}(\Delta B_k-\lambda_0\Delta E_k).
\]

Therefore \(z_1+z_2+z_3\) reconstructs the fixed-multiplier window surplus.
This identity proves bookkeeping for one matched intervention.  It does not
prove learnability, simultaneous-user additivity, or positive ablation
marginality after all users act.

## 3. Current ZR is not the exact V0.3 z3 surface

`src/mcrl/runtime/ee_axis_zero_marginal_c3.py` implements, for per-victim
opening effects \(e_{a,v}\),

\[
x_a=\sum_v\min(e_{a,v},0)
    +g_a\sum_v\max(e_{a,v},0),
\]

where \(g_a\) requires exact equality of service, active beams, active
satellites, RF allocation, and network power relative to the C3-free
reference.  The returned surface is reference-centred.

Consequently, positive non-focal bits are discarded whenever \(g_a=0\), while
negative non-focal bits are retained.  Except when every positive component is
compatible (or there is no positive component), this differs from the exact
\(z_3=\sum_v e_{a,v}\).  It is therefore a conservative spatial decision
surrogate, not the original exact partition term.  If it is retained, the
paper must not claim that the deployed ZR surface preserves the exact
three-term identity without an explicit residual term.

## 4. What V0.18 and V0.19 distinguish

- V0.18 supplies TRAIN-development existence evidence that an exact/nominal
  relational-ZR oracle can improve trajectory ratio-of-sums EE on its sampled
  frozen Q1+Q2 background.
- V0.19 repairs the output-unit defect but the uniform legal-action surface
  MSE learner still fails its fixed learner gate.
- The V0.19 TRAIN and VALIDATION positive target populations are sparse
  (roughly four percent of legal non-reference actions), while uniform MSE
  weights every legal non-reference action equally.

The present evidence rejects the V0.19 learner objective.  It does not alone
decide whether the best next method is (a) a decision-aligned learner for the
same ZR surrogate or (b) a new R3 target.

## 5. Feasibility boundary

Three independent heads can each have positive marginal ablation value when
they induce complementary action-order corrections around the same background
and the resulting multi-user interaction residual does not reverse those
corrections.  This is possible, not guaranteed.  Redundant heads can have zero
marginality; conflicting heads can make FULL worse than a DROP arm even when
each underlying unilateral target is locally positive.

The positive ZR oracle trajectory evidence makes structural impossibility an
unsupported conclusion.  Conversely, it is not proof that a deployable learned
Q3 exists or that all five desired arms will order correctly.

## 6. Opened-TRAIN decision geometry

The reproducible TRAIN-only census in
`v019-train-decision-geometry.json` loads all twelve V0.19 TRAIN shards and no
VALIDATION or TEST row.  It finds:

- 1,882/12,000 rows (15.683%) are pivotal under exact
  `Q1 + learned-Q2 + ZR`;
- the teacher action is positive and predecision-compatible on 100% of those
  pivotal rows;
- only 3.646% of legal non-reference action cells have a positive target;
- among compatible non-reference candidates, the action with the largest
  frozen background score is the teacher on 75.292% of pivotal rows;
- applying that candidate choice unconditionally is not safe: only 44.400% of
  its 7,036 changes have positive target support;
- the best-background compatible candidate's true decision margin has median
  `-0.35975` but 95th percentile `+0.50041` in normalized units.

Thus the target supplies many pivotal rows, and candidate identity is mostly
recoverable from the background ordering.  The unresolved learning problem is
principally whether a compatible candidate's ZR gain exceeds its background
gap.  Uniform regression over 306,486 legal non-reference cells dilutes this
row-level decision boundary.

## 7. Decision still open

The next decision must compare, before opening fresh outcomes:

1. retain the ZR physical surrogate and use a background-aware,
   decision-aligned learned Q3 objective;
2. restore or redesign an exact non-focal/interaction residual target while
   controlling simultaneous-user non-additivity;
3. redesign the additive interface only if neither target can be represented
   by one independent Q3 in the common normalized unit.

No paper, symbol-table, five-arm, or long-training authority follows from this
working note.
