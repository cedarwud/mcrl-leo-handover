# Multi-Catfish MCRL V0.7 C2 focal-next design decision

Date: 2026-09-02  
Status: `IMPLEMENTATION_AUTHORIZED__PILOT_NOT_FROZEN__NO_EE_CLAIM`  
Supersedes as a learner candidate: V0.6 C2-k1 network-total first-successor  
Does not supersede: canonical ratio-of-sums EE, frozen C1/C3 candidates, or the
three-Q/one-argmax deployment boundary

## 1. Decision

The V0.6 network-total first-successor target is retired as a learnable C2
candidate.  C2 remains mandatory and retains a distinct temporal role, but its
V0.7 public target is the **focal-attributable next-slot EE surplus** under a
matched continuation.

V0.7 combines two changes that address different demonstrated failures:

1. the target excludes non-focal next-slot continuation cascades that were
   attributed to one focal action but were poorly predictable from its causal
   state; and
2. source rows are generated at actual predecision states with native legal
   masks, followed by one fixed on-policy refresh, rather than fitting 12
   complete-mask opening states and applying the result everywhere.

This is not a scalar reversal, route weight, harm veto, coordinator, auction,
or post-training correction.

## 2. Evidence that closes V0.6

The sealed V0.6 learned deployment remains a valid negative result:

- `FULL - DROP_C2 = -28.57542691414722%` pooled EE;
- `0/3` positive lineages and `0/10` positive DESIGN-EVAL worlds;
- service non-inferiority failed; and
- mean action-flip rate was `0.7607`.

Two post-outcome diagnostics used only the already sealed TRAIN/T1 material.
They opened no TEST split, no new world, and no replacement evaluation gate.

### D0: continuation-cascade and oracle-content diagnosis

Authority:
`artifacts/multi-catfish-v06-c2-k1-postresult-diagnostics-20260902-r1/d0-diagnostic.json`  
File SHA-256:
`b32e53cbca8c77932743f0a9fc969841845868820957a05c2fd1e6ed8c9a3496`

- `810/1008` rows changed at least one non-focal user's offset-1 action;
- changed non-focal users: median `2`, mean `3.1478`, maximum `42`;
- bounded absolute non-focal rate-component share: median `0.44195`;
- absolute non-focal rate divided by absolute total target: median `1.0`;
- cross-lineage within-anchor target-rank Spearman: median `0.30089`; and
- after removing offset 1 from the already selected oracle traces, the oracle
  contrast becomes `-0.412289%`, `0/3` positive lineages, and `2/12` positive
  worlds.

The last result shows that T1 was an exact realized-label headroom check, not a
learnability check.  It remains useful mechanics evidence but cannot authorize
another learner with the same target.

### D1: leave-one-anchor-out learnability diagnosis

Authority:
`artifacts/multi-catfish-v06-c2-k1-postresult-diagnostics-20260902-r1/loowo-diagnostic.json`  
File SHA-256:
`3e66a9a30e91d8fab10995ed8f4365b42c536f94c80de409e56d7b3fa83cc048`

Using the same V0.6 network and 100 updates, each fold trained on 11 anchors and
scored the omitted anchor:

| Lineage | Skill vs action-only pairwise null | Skill vs zero | Held-out Spearman | Calibration slope |
|---|---:|---:|---:|---:|
| `q13-a` | -0.11499 | -0.20415 | -0.21810 | -0.38710 |
| `q13-b` | +0.08221 | -0.03623 | +0.08572 | +0.27644 |
| `q13-c` | -0.10296 | -0.37134 | -0.08933 | -0.18847 |

Only `1/3` lineages beat the action-only null and `0/3` beat the zero predictor.
The network-total target therefore lacks demonstrated out-of-anchor
predictability.  More updates, sign reversal, or rescaling the three failed
checkpoints is not an admissible rescue.

## 3. Preserved deployment invariant

There are exactly three independent learned surfaces and one executed Main
action:

\[
S(s,a)=Q_1(s_1,a)+Q_2(s_2,a)+Q_3(s_3,a),
\]

\[
a^*=\arg\max_{a\in\mathcal A(s)}S(s,a).
\]

All three surfaces use the same native safe-action mask.  An empty mask emits
the existing no-op and does not evaluate Q2.  There is no route weight, second
argmax, vote, veto, coordinator, or deployment-time Catfish agent.

## 4. V0.7 public C2 estimand

Let branch (b\in\{C,M\}), focal user (u), and offset (1) denote the
successor slot.  Define focal marginal network power

\[
p_{b,u}(1)=P_b^N(1)-P_{b,-u}^N(1),
\]

where (P_{b,-u}^N(1)) is evaluated by keeping every non-focal successor
action fixed and replacing only user (u)'s successor action by a
physics-only no-op.  This evaluation cannot commit environment state, segment
state, counters, or random-number state.

The C2 target is

\[
\boxed{
\zeta_{2,u}(s,a)
=\Delta t\,[R_u^C(1)-R_u^M(1)]
-\lambda_0\Delta t\,[p_{C,u}(1)-p_{M,u}(1)]
}.
\]

Every term is in native bits after the fixed multiplier.  Positive, zero, and
negative rows are retained.  There is no clipping or sign filter.

The old full-window identity is deliberately narrowed:

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}=g_0+g_{1,u},
\]

where (g_{1,u}) is the focal-attributable successor surplus.  The residual
(g_1-g_{1,u}) is an unmodelled next-slot externality and may be reported as a
diagnostic, but it supplies no gradient.  This is preferable to presenting an
exact full-network decomposition whose C2 component has no held-out
learnability.

## 5. Matched source construction

An anchor is a predecision tuple `(world, step, user)` with its V0.3 causal
state and native Boolean action mask.  Empty-mask anchors are counted for
coverage but produce no Q2 rows.

For every non-empty anchor and every legal candidate action (a):

1. the reference action vector is the fixed behavior policy's direct
   three-surface masked argmax;
2. the candidate opening vector differs only at user (u), which plays (a);
3. both branches use the same keyed exogenous random field;
4. each branch commits its own opening action and reaches its own successor
   state;
5. at the successor, every user re-decides using the same frozen behavior
   policy on that branch's own state and mask;
6. the full successor vector is evaluated without commit;
7. the same vector is re-evaluated with only user (u) removed, also without
   commit; and
8. the four power values and two focal rates reconstruct
   (zeta_{2,u}(s,a)).

The candidate-equals-reference row is retained and must reconstruct exact zero.
Every legal action appears exactly once; illegal actions never receive a row.
No source row is selected by target, EE, service, cascade count, or later
evaluation outcome.

At a terminal predecision with no physical successor, rows are explicit
absorbing-zero controls and may not be described as measured successor effects.

## 6. One fixed on-policy refresh

The learner uses exactly two source captures, declared before any new outcome:

1. **bootstrap capture:** behavior uses (Q_1+0+Q_3); a provisional Q2 is fit
   only to establish a behavior policy; and
2. **refresh capture:** behavior uses
   (Q_1+Q_2^{(0)}+Q_3); the final Q2 is initialized afresh and trained only on
   this refresh corpus.

There is no third capture, outcome-triggered retry, replacement world, or union
of bootstrap and refresh rows.  The refresh makes the state and mask
distribution correspond to an actual three-head policy while preventing an
unbounded policy-feedback loop.

## 7. Learner and calibration

The first implementation keeps the V0.3 228-D causal state and the existing
mask-explicit mean/max action scorer.  A legal-mask mean is subtracted from the
raw Q2 surface before loss and deployment:

\[
Q_2(s,a)=q_2(s,a)-
\frac{1}{|\mathcal A(s)|}\sum_{c\in\mathcal A(s)}q_2(s,c).
\]

This fixes the action-independent gauge without changing any pairwise action
difference or introducing a route weight.  The pairwise loss is

\[
\mathcal L_2=
\frac{1}{N}\sum_n
\left[
Q_2(s_n,a_n)-Q_2(s_n,a_n^M)-
\frac{\zeta_{2,u,n}}{\kappa}
\right]^2.
\]

The update ladder is `100, 500, 1500`, with a checkpoint every 100 updates.
The rung is selected only by world-disjoint validation pairwise MSE.  A free
deployment multiplier is forbidden; calibration is accepted only if the
validation slope of target on predicted pair difference is in `[0.5, 1.5]`.

## 8. Evidence ladder before any episode training

### D2: 20-physical-anchor / 60-lineage-cell formula/source pilot

Use fresh TRAIN-design worlds and enumerate every native legal action.

All must pass:

- exact matched mechanics and zero controls;
- median cross-lineage within-anchor target-rank Spearman at least `0.6`;
- median ratio of target within-anchor standard deviation to Q1+Q3
  within-anchor standard deviation at most `3.0`; and
- target IQR at least `0.05 kappa` in at least 30 of 60 lineage cells; and
- at least 6 of 20 physical anchors have a positive non-reference alternative
  in at least 2 of the 3 lineages.

This is heavy non-GUI simulation and must run on the Ubuntu server.  Estimated
wall time after implementation: 1--2 hours, subject to a mandatory one-anchor
runtime calibration.

### D3: 300--400-anchor learnability gate

Use a world-disjoint TRAIN/validation split and the fixed one-refresh schedule.

All must pass:

- held-out pair skill strictly above the strongest state-independent
  action-only null in at least `2/3` lineages;
- validation calibration slope in `[0.5, 1.5]` in at least `2/3` lineages;
- complete native legal-action coverage; and
- no Q1/Q3 update or resident legacy-Q2 access.

Expected Ubuntu wall time is 2--4 hours for a 300--400 anchor source, but the
one-anchor calibration is binding.  A full every-user/every-step two-capture
corpus may require 6--24 hours and is not authorized before D2/D3 establish
that the focal target is learnable.

### D4: fresh matched deployment screen

Only a D3 pass permits one fresh, pre-registered FULL versus DROP-C2 screen.
It must reuse the V0.6 G-L/G-E/G-S logic on previously unopened worlds.  Only a
D4 pass permits a larger confirmation.

No 1500-, 3000-, or 9000-episode training is authorized by this document.  The
user must be told before any 9000-episode launch.

## 9. Cross-model adjudication

Fresh Fable Max ranked the V0.6 network-total estimand and absent held-out
learnability as the main failures and recommended focal-next marginal surplus.
An independent code-path review ranked deployment/source-distribution mismatch
first and recommended native-mask on-policy rows plus explicit calibration.

D0 falsified Fable's strongest quantitative cascade prediction (median changed
non-focal users was `2`, not at least `5`), so the decision does not treat that
review as authority.  D0 nevertheless found continuation cascades in `810/1008`
rows, while D1 directly established non-learnability.  V0.7 therefore adopts
the intersection that is supported by receipts: a focal-attributable target,
native-mask every-predecision source support, held-out skill, and one fixed
on-policy refresh.

## 10. Retain and retire

Retain:

- frozen C1/C3 candidates and Q1+Q3 lineages;
- canonical EE and service guard;
- T1 and V0.6 artifacts as mechanics and negative-result evidence;
- freeze/attempt/seal infrastructure, direct `compose_actions`, and matched
  evaluator patterns; and
- W102--W110 as regression coverage.

Retire from all future deployment, fine-tuning, and rescaling:

- the three V0.6 update-100 Q2 checkpoints;
- the network-total C2-k1 target as a learner candidate;
- opened TRAIN/DESIGN-EVAL worlds as future C2 evidence; and
- the V0.6 paper/figure C2 delta as current method content.

Archiving here means semantic retirement, not destructive deletion.  Existing
receipts remain immutable evidence of what was tried.
