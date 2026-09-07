# Multi-Catfish MCRL V0.4 parallel C2 candidate preregistration

Date: 2026-09-01  
Status: `PREOUTCOME_WORK_ORDER`  
Claim ceiling: `DESIGN_SCREEN_ONLY_NO_FINAL_TEST_NO_EE_EFFICACY_CLAIM`

## 1. Purpose

C2 is mandatory.  The workflow therefore does not wait for one temporal
learner to fail before considering the next one.  This addendum freezes three
bounded C2 candidates before the support-complete counterfactual outcomes are
opened.  All candidates reuse the same sealed physical sibling census; the
expensive trajectory generation is performed once.

This addendum does not weaken the physical gates in
`MULTI-CATFISH-MCRL-V04-C2-SUPPORT-COMPLETE-CENSUS-PREREG-2026-09-01.md`.
It separates two questions that were previously handled sequentially:

1. which continuation gives Q2 the physically relevant downstream target;
2. which fixed loss learns that 28-action target without unstable amplitude.

## 2. Shared source and immutable boundaries

Every arm uses:

- the exact sealed 12-cluster, 324-sibling legal-action schedule;
- the same candidate/reference interventions and keyed common-random fields;
- the same canonical ratio-of-sums EE linearization, \(\lambda_0\), \(\kappa\),
  \(H^c=4\), and downstream offsets \(k=1,2,3\);
- the same Q2 state, action mask, network family, initialization seeds,
  optimizer, update budget, minibatch order, and checkpoint cadence;
- frozen Q1 and Q3; only Q2 may receive gradients;
- direct unweighted `Q1 + Q2 + Q3`, one common mask, and one argmax at
  deployment.

No arm may discard a legal sibling, select only positive targets, inspect a
final TEST row, or tune a multiplier from EE outcomes.

The Phase-A artifact must retain raw per-offset rate, network-power, served,
release, and delivered-bit quantities.  Derived targets are regenerated from
those sealed rows rather than by rerunning or replacing worlds.

## 3. Three frozen candidates

Let \(a^M\) be the contemporaneous Main action and let

\[
y^{\pi}_{u}(a)=\frac{\zeta^{\pi}_{2,u}(a)}{\kappa}
\]

be the normalized downstream matched surplus when both branches use the same
continuation \(\pi\) after the focal opening intervention.

### P0 — Main-value

`C2-P0-MAIN-VALUE` uses the existing branch-local frozen Main continuation and
the existing squared pairwise loss:

\[
\mathcal L_{\mathrm{P0}}=
\left[Q_2(s,a)-Q_2(s,a^M)-y^{\mathrm{Main}}_u(a)\right]^2
+\beta Q_2(s,a^M)^2.
\]

This is the simplest support-complete repair and preserves the original
formula-level story.

### P1 — continuation-matched value

`C2-P1-Q13-VALUE` replaces only the continuation.  For initialization \(i\),
both matched branches re-decide with that initialization's frozen
`Q1 + Q3` policy.  It uses the same squared pairwise loss with
\(y^{Q_{1,i}+Q_{3,i}}_u(a)\).

This arm directly tests the surviving Opus-review concern that a Main rollout
may give Q2 a ranking different from the policy context in which Q2 is later
deployed.  It does not introduce a cross-route gradient: Q1 and Q3 are frozen
trajectory generators only.

### P2 — continuation-matched robust value

`C2-P2-Q13-HUBER` uses the same continuation-matched physical target as P1,
but replaces the squared residual by a Huber penalty with the fixed normalized
threshold \(\delta=1\):

\[
\mathcal L_{\mathrm{P2}}=
\operatorname{Huber}_{\delta=1}
\left(Q_2(s,a)-Q_2(s,a^M)-y^{Q_{1,i}+Q_{3,i}}_u(a)\right)
+\beta Q_2(s,a^M)^2.
\]

The Huber arm keeps Q2 in the same normalized surplus units while limiting
the leverage of the extreme temporal targets observed in the failed C2 head.
Its exact penalty is \(\rho_1(r)=r^2\) for \(|r|\leq1\) and
\(\rho_1(r)=2|r|-1\) otherwise, so its local curvature matches the P1 squared
loss.  No clipping or sign filtering is permitted.

## 4. Physical authorization

Phase A is shared by all three candidates.  `G-S`, `G-R`, and `G-V` must pass
before any learner is rebuilt.

Phase B materializes both Main-continuation and the three matched frozen
`Q1 + Q3` continuation target surfaces.  Its disposition is arm-specific:

- P0 is eligible only if the existing `G-C` Main-versus-Q13 ranking-stability
  gate passes.
- P1 and P2 do not require agreement with Main, because disagreement is the
  physical mismatch they are designed to remove.  Instead, each
  initialization must independently retain a non-degenerate target surface
  and delivered-bit protection under its matched Q13 continuation using the
  same `G-S` and `G-V` thresholds.  At least two of three initializations must
  pass.
- if neither continuation family is physically authorized, no learner loss
  can repair the target; the next C2 batch must change temporal
  formula/physics rather than silently dropping C2.

## 5. Parallel design screen

Every physically eligible arm is trained for the same bounded offline update
ladder: `100`, `500`, and `1500` Q2 updates, with a write-once checkpoint and
metrics receipt every `100` updates.  These are replay updates, not MODQN
episodes.  The three initialization lineages are retained.  Eligible arms may
run concurrently on the Ubuntu server.

All arms use the same TRAIN corpus and the same unopened DESIGN-EVAL worlds.
For every rung report:

- full-action target regret and Spearman rank correlation;
- Q2 surface magnitude relative to frozen `Q1 + Q3`;
- action-flip rate relative to `DROP-C2`;
- total delivered bits and canonical ratio-of-sums EE;
- paired marginal EE for `FULL - DROP-C2` and `FULL - Main`.

An arm is design-positive only when, at one fixed rung, all of the following
hold:

1. pooled paired `FULL - DROP-C2` EE is strictly positive;
2. at least two of three initialization lineages have positive paired
   `FULL - DROP-C2` EE;
3. downstream total delivered bits do not decrease in at least two of three
   lineages; and
4. no lineage has non-finite values, invalid actions, incomplete traces, or a
   broken source/continuation receipt.

Rung selection is by DESIGN-EVAL only.  Among design-positive candidates,
select the largest pooled paired `FULL - DROP-C2` EE; an exact tie is resolved
by the fixed simplicity order `P0`, `P1`, `P2`.  Final TEST remains unopened.

## 6. Decision boundary

The parallel screen may select at most one C2 formulation for the later frozen
confirmation.  A design-positive result is not an EE efficacy claim.  The
eventual algorithm must still establish, on fresh frozen evaluation:

```text
FULL > DROP-C1
FULL > DROP-C2
FULL > DROP-C3
FULL > Main
```

If all P0/P1/P2 arms fail, the result is
`NEXT_C2_FORMULA_PHYSICS_BATCH_REQUIRED`.  It is never permission to retire
C2, keep a knowingly harmful Q2 head, or relabel a two-Catfish method as
Multi-Catfish.
