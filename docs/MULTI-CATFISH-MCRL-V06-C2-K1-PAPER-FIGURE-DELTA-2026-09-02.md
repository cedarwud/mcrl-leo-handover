# Multi-Catfish MCRL V0.6 C2-k1 paper and figure delta

Date: 2026-09-02  
Status: `PRE_RESULT_METHOD_FROZEN_SOURCE_GATE_PENDING`  
Claim ceiling: method, notation, and figure authoring only; no C2 efficacy claim

## 1. Purpose and authority boundary

This delta supplies the paper-facing form of the frozen C2-k1 hypothesis while
its preregistered T1 source-oracle gate is pending.  It does not modify the
frozen preregistration, implementation, seed schedule, gate, or result.  It may
be used to prepare editable method text and figures, but it must remain visibly
result-pending until T1 and the separately authorised learner and marginal
evaluation have completed.

For C2, this delta supersedes the former hold/release, common-action-tape, and
all-later-offset Temporal-Fork descriptions in the V0.3 algorithm, paper,
presentation, and figure documents.  Those documents remain authoritative for
the invariant single-EE, exactly-three-Q, route-local learning, and one-argmax
architecture.  C1 and C3 remain frozen under their current V0.4 authorities.

The executable and experimental authority remains:

- `docs/MULTI-CATFISH-MCRL-V06-C2-K1-T1-PREREG-2026-09-01.md`;
- `docs/MULTI-CATFISH-MCRL-V06-C2-K1-T1-FINAL-AUDIT-2026-09-02.md`;
- `src/mcrl/runtime/ee_axis_v06_c2_k1.py`;
- `.scratch/c3-v04/run_v06_c2_k1_t1.py`; and
- `.scratch/c3-v04/v06_c2_k1_live_adapter.py`.

## 2. One objective and three causal views

The final objective remains the canonical network ratio-of-sums EE

\[
\eta^N=\frac{\mathcal B}{\mathcal E}.
\]

C1, C2, and C3 are not three competing rewards.  They are three training-time
views of one unilateral opening intervention:

| Route | Paper-facing role | Learner |
|---|---|---|
| C1 | focal user's opening net surplus, including the complete opening network-energy difference | \(Q_1\) |
| C3 | non-focal users' opening rate externality, without duplicating opening energy | \(Q_3\) |
| C2-k1 | the whole network's first-successor temporal net surplus caused by the opening intervention | \(Q_2\) |

The three roles are therefore focal-now, non-focal-now, and network-next.  C2
does not attempt to improve a legacy `r2` metric.  Its only purpose is to teach
\(Q_2\) which opening actions create helpful or harmful first-successor
consequences for the same final EE objective.

## 3. Matched C2-k1 comparison

At a sealed state, reference branch \(M\) plays the frozen Main opening action.
Candidate branch \(C\) differs only in focal user \(u\)'s opening action.  At
the first successor, both branches use the same frozen continuation policy
\(\pi\), but each evaluates it on its own state and legal-action set.  The two
branches share matched exogenous randomness.

The paper-facing C2 target is

\[
\zeta_{2,u}=
\Delta t\sum_{i\in\mathcal U}
\left[R_i^C(1)-R_i^M(1)\right]
-\lambda_0\Delta t
\left[P_C^N(1)-P_M^N(1)\right].
\]

Positive, zero, and negative complete comparisons are all retained.  A
negative value is useful evidence: it teaches \(Q_2\) to suppress an opening
action with harmful first-successor consequences.

The implementation receipt field `z2_k1` and the preregistration's
\(z_{2,u}^{1}\) both map to the single paper symbol \(\zeta_{2,u}\).  The
superscript is omitted from the public method because the active C2 definition
contains only successor offset \(1\); it is not a tunable horizon label.

## 4. Non-overlap identity

For the two offsets represented by the current method,

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}=g_0+g_1.
\]

This identity prevents double counting:

- C1 owns the focal opening rate difference and all opening energy difference;
- C3 owns the non-focal opening rate difference and no energy term; and
- C2 owns all users' rate difference and the network-energy difference at the
  first successor.

Offsets after \(1\) are evaluation outcomes for detecting surrogate reversal;
they are not C2 labels and must not be drawn inside the C2 target band.  The
identity proves bookkeeping only, not learnability or EE efficacy.

## 5. Route-local learning and deployment

C2 comparisons belong to \(D^t\) and update only \(Q_2\).  The common
paper-facing pairwise relation remains

\[
Q_j(s_{j,u},a_u^C)-Q_j(s_{j,u},a_u^M)
\approx\frac{\zeta_{j,u}}{\kappa},
\qquad j\in\{1,2,3\}.
\]

At deployment, the three independently learned values are combined only once:

\[
\Phi_u(t,a)=
Q_1(s_{1,u}(t),a)+Q_2(s_{2,u}(t),a)+Q_3(s_{3,u}(t),a),
\]

\[
a_u^\star(t)=
\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

Exactly one Main action executes.  There is no auction, coordinator, vote,
learned gate, route weight, second argmax, or post-training override.

## 6. Public notation amendment

This table amends Section 10.12 of the active symbol table.  Primary symbols
and every semantic subscript or superscript remain one letter or one numeral.

| Symbol | Current public meaning | Unit or restriction |
|---|---|---|
| \(i\) | generic user index | \(i\in\mathcal U\) |
| \(u\) | focal user index | one unilateral opening mover |
| \(k\) | matched offset | C2 label uses \(k=1\) only |
| \(M,C\) | reference and candidate branch labels | single-letter roles |
| \(\pi\) | one frozen continuation policy shared by both branches | applied branch-locally |
| \(\lambda_0\) | frozen TRAIN-only EE multiplier | bit/J |
| \(\kappa\) | shared Q-output scale | bit |
| \(g_k\) | fixed-multiplier system surplus at offset \(k\) | bit |
| \(\zeta_{1,u}\) | C1 focal opening surplus | bit |
| \(\zeta_{2,u}\) | C2 first-successor network surplus | bit |
| \(\zeta_{3,u}\) | C3 non-focal opening rate externality | bit |
| \(D^o,D^t,D^a\) | opening, temporal, and held-out identity datasets | \(D^a\) never produces a gradient |
| \(Q_j\) | route-\(j\) value surface | \(j\in\{1,2,3\}\) |
| \(s_{j,u}\) | route-\(j\) causal state view for user \(u\) | two single-symbol indices |
| \(A_u\) | common legal and service-safe action set | shared by the three Q outputs |
| \(\Phi_u\) | direct unweighted three-Q deployment score | one argmax |

Retire from the public C2 surface:

- \(\sum_{k=1}^{H^c-1}\) as the C2 target;
- the statement that offsets \(1,2,3\) all belong to C2;
- hold, release, expiry, reference action tape, and branch repair symbols; and
- multi-letter implementation labels such as `q13`, `k1`, `z2_k1`, and
  `NO_OP` inside paper equations.

Those labels may remain in code, receipts, and experiment appendices when
needed for provenance.

## 7. Figure and slide amendment

The smallest accurate C2 figure has five stages:

1. one sealed opening state and frozen Main reference;
2. one focal opening intervention in candidate branch \(C\);
3. two matched branches using the same \(\pi\) on their own successor states;
4. first-successor rates and network power forming \(\zeta_{2,u}\); and
5. \(D^t\rightarrow Q_2\rightarrow Q_1+Q_2+Q_3\rightarrow\) one masked
   argmax.

Do not draw a hold interval, release event, action tape, offsets \(2\) or \(3\)
inside the target, a second agent, or a deployment coordinator.  Gate-only
details such as 12 worlds, 28 actions, three lineages, hashes, controls, and
oracle actions belong in an experiment-validation figure or appendix, not in
the main algorithm overview.

## 8. Claim boundary and promotion

Allowed before the T1 result:

- “C2-k1 is the frozen first-successor temporal-surplus hypothesis.”
- “Its source-oracle gate is pending.”
- “A passing source gate would authorise one bounded Q2 learner screen.”

Forbidden before later evidence:

- “C2 improves EE” or “all three Catfish mechanisms are effective”;
- any C2 result value, long-training claim, or Chapter 5 curve;
- treating a T1 pass as learned-Q2 efficacy; and
- restoring a retired C2 formulation after observing T1 outcomes.

If T1 is structurally valid but fails its EE or service gate, this entire
C2-k1 delta becomes a falsified candidate record and must not be promoted into
the final paper package.  If T1 passes, the method text may remain, but final
acceptance still requires a bounded learner and fresh matched evidence that
`FULL > DROP-C2`; final whole-method acceptance additionally requires
`FULL > DROP-C1`, `FULL > DROP-C3`, and `FULL > Main` under the same service
guard.
