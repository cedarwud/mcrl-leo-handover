# Multi-Catfish MCRL V0.3 algorithm specification

Date: 2026-08-31  
Status: **C1/C3 current; C2 V0.7 section retained only as superseded
provenance; clean-room C2 redesign pending; no three-route efficacy claim**

> **Post-R14 C2 warning (2026-09-02).** The focal-next `motion-one` C2 text in
> this document is not a current method lock. R13 was statistically compatible
> with zero and R14 found `0/3` Q2 lineages better than the strongest held-out
> null. Use the C1/C3 sections only; do not use the existing C2 section to
> implement, train, draw, or author the final method. A replacement C2 must
> first pass formula-first headroom and decision-time observability gates.

This is the clean algorithm-level entry point for figures, slides, and the
Chapter 4 method description. The formula authority remains
`MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`. Anything under
`archive/multi-catfish-pre-v03-2026-08-31/` is historical and must not be used
to launch or explain V0.3.

For the paper main text and main presentation, use
`MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md`. It compresses this
complete specification into one intervention, three views, three route-local
estimators, and one deployed action. Its omissions are authoring choices only;
this full specification remains the reproducibility and implementation
authority.

## 1. Objective and invariant

The only scientific endpoint is canonical ratio-of-sums energy efficiency:

\[
\eta^N=\frac{\mathcal B}{\mathcal E},\qquad
\mathcal B=\sum_t\sum_{u\in\mathcal U}R_u(t)\Delta t,\qquad
\mathcal E=\sum_tP^N(t)\Delta t.
\]

The old directions of `r2` and `r3` are not objectives. V0.3 uses three
training-time views of how one focal action can change the same final EE. A
route survives only when its informed source improves held-out Main-only EE
over its equal-budget neutral replacement without violating the service guard.

## 2. Exactly three Q functions

V0.3 contains exactly three independent online Q functions:

```text
C1 source route -> Q1(s_u(t),a) --\
C2 source route -> Q2(s_u(t),a) ----> Phi_u=Q1+Q2+Q3 -> one masked argmax
C3 source route -> Q3(s_u(t),a) --/
```

- Each Q has independent parameters and its own optimizer; no trainable trunk
  is shared.
- Pilot 1 is zero-bootstrap pairwise regression. It has no target networks.
- A route-\(j\) row may change only \(Q_j\).
- Catfish routes generate and schedule training comparisons; they are not
  three extra networks. A six-Q interpretation is invalid for V0.3.
- Legacy Bellman replay, old `r1/r2/r3` targets, old target networks, and old
  checkpoints are unit-incompatible and fail closed.

## 3. One matched intervention, three scoped targets

Freeze one TRAIN-only multiplier before Catfish outcomes are inspected:

\[
\lambda_0=\frac{\mathcal B_0^M}{\mathcal E_0^M},\qquad
g_k=\Delta\mathcal B_k-\lambda_0\Delta\mathcal E_k,
\]
\[
\Delta\mathcal B_k=\Delta t\sum_{i\in\mathcal U}
[R_i^C(k)-R_i^M(k)],\qquad
\Delta\mathcal E_k=\Delta t[P_C^N(k)-P_M^N(k)].
\]

At an anchor, candidate branch \(C\) and reference branch \(M\) initially
differ only in focal user \(u\)'s physical action.

### C1: focal now

\[
\zeta_{1,u}=\Delta t[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t[P_C^N(0)-P_M^N(0)].
\]

C1 assigns the complete opening-step energy difference to the only mover. It
is the direct immediate net-surplus path.

### C3: others now

\[
\zeta_{3,u}=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
[R_i^C(0)-R_i^M(0)].
\]

C3 captures the focal action's immediate non-focal rate externality through
load, bandwidth sharing, co-channel interference, and shared activation.
Opening energy is not repeated here because it already belongs to C1.

### C2: focal next-slot attributable surplus (motion-one, provisional post-R13 amendment)

At each predecision anchor, identify the eligible users under the native legal
action masks and select one focal user \(u\) by the largest signed-motion
opportunity. Ties go to the lowest user index. Enumerate the native 28 legal
action slots for that user under the native mask. Each slot defines a matched
candidate branch \(C\) against the Main reference branch \(M\), and C2 records
only the focal user's attributable effect at successor slot 1.

For branch \(b\in\{C,M\}\), focal-user marginal network power is

\[
p_{b,u}(1)=P_b^N(1)-P_{b,-u}^N(1),\qquad b\in\{C,M\}.
\]

The focal next-slot EE surplus is

\[
\zeta_{2,u}=\Delta t[R_u^C(1)-R_u^M(1)]
-\lambda_0\Delta t[p_{C,u}(1)-p_{M,u}(1)].
\]

All native legal slots are retained exactly once, including zero and negative
targets. Each C2 row updates only \(Q_2\). C2 is a focal next-slot target, not
an all-user temporal aggregate. This motion-one rule is provisionally locked
after R13; the earlier D2 preregistration predates it and does not validate
this amendment.

The old full-window identity is retired. The scoped bookkeeping identity is

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}=g_0+g_{1,u}.
\]

Here \(g_{1,u}\) is the focal-attributable part of the successor surplus. The
residual next-slot non-focal externality is diagnostic only and supplies no
gradient. This scoped identity proves accounting consistency, not learnability
or efficacy.

## 4. The three Catfish source mechanisms

All informed and neutral schedules are sealed from predecision information
before targets are evaluated. Positive, zero, negative, and all-dark complete
outcomes are retained. For C2, source generation selects one eligible focal
user by signed-motion opportunity, enumerates the native 28 legal action slots
under its mask, compares each candidate with Main, and records the focal
next-slot attributable target. Every C2 row updates only \(Q_2\).

| Route | Informed mechanism | Equal-budget neutral replacement | Update |
|---|---|---|---|
| C1 Energy-Frontier | RIS-lineage dull-rollout EXP schedules lower-frontier anchors and users, then compares every sealed legal alternative with frozen Main | uniformly sample eligible Main anchors, users with at least two legal actions, and legal alternatives | only \(Q_1\) with \(\zeta_1\) |
| C2 Focal-Next | select one eligible focal user by largest predecision signed-motion opportunity (lowest user index on a tie), enumerate its native 28 legal action slots under the native mask, and compare each candidate with Main at successor slot 1 | uniformly sample eligible anchors and apply the same native-mask 28-slot enumeration | only \(Q_2\) with \(\zeta_2\) |
| C3 Spatial-Externality | use lagged competitive-load anchors, choose users spanning multiple physical alternatives, and enumerate sealed unilateral legal actions | uniformly sample eligible anchors/users and the same number of legal alternatives | only \(Q_3\) with \(\zeta_3\) |

### C1 EXP/ACRM lineage

V0.3 preserves the two ideas without changing output units:

1. **EXP** is informed source construction and stratification on disjoint
   TRAIN-only dull-rollout data.
2. **ACRM** is the reference-anchored candidate-versus-Main comparison inside
   the C1 pairwise advantage. It is a unit-safe adaptation of competitive
   learning, not an additive shaped reward.

The superseded formula that added an ACRM reward directly to a Bellman target is
not used: it would make \(Q_1\) incomparable with \(Q_2\) and \(Q_3\). A later
C1 component study may compare EXP-only and EXP-plus-source-priority variants,
but no component may alter the canonical EE formula or the deployed Q unit.

## 5. Phase-I data products

V0.3 separates cheap opening comparisons, expensive temporal comparisons, and
identity auditing:

| Set | Contents | Gradient use |
|---|---|---|
| \(D^o\) | offset-0 matched pair; raw per-user rates and system power; both \(\zeta_1\) and \(\zeta_3\); source tag C1 or C3 | source C1 updates only \(Q_1\); source C3 updates only \(Q_3\) |
| \(D^t\) | matched C2 candidate/Main rows at successor slot 1; focal rate and branch-power terms; \(\zeta_2\); native mask and source lineage | updates only \(Q_2\) |
| \(D^a\) | held-out matched traces with the opening terms and scoped focal next-slot identity | never enters a loss; identity/distinctness/deployment audit only |

Every row binds at least:

```text
row id, source j, data-set version, seed, anchor and focal user,
reference/candidate physical keys and action slots, native decision mask,
observation-schema version, policy version, branch-matching version,
successor-slot rate/power terms, target(s), outcome, and trace identity
```

The source quota and exact observation representation remain preregistration
parameters. They may change before the first claim-bearing run without changing
the public C2 mechanism.

## 6. Pairwise learning

Use one shared positive scale:

\[
\widetilde\zeta_{j,u}=\frac{\zeta_{j,u}}{\kappa},\qquad
\kappa=\frac{\mathcal B_0^M}{n_0}.
\]

For a route-\(j\) comparison:

\[
\ell_j=w_j\left(
[Q_j(s_u(t),a_u^C(t))-Q_j(s_u(t),a_u^M(t))
-\widetilde\zeta_{j,u}]^2
+\beta Q_j(s_u(t),a_u^M(t))^2
\right).
\]

- \(w_j\) normalizes loss noise only; deployment weights remain one.
- \(\beta\) is a numerical gauge, provisionally 0.1 and frozen before the
  claim-bearing run.
- No Bellman bootstrap, target net, voting loss, redundant sum loss, or
  cross-route gradient is permitted.
- Swap of reference/candidate reverses the target sign; an identical pair has
  zero target.

## 7. Deployment

Only Main executes:

\[
\Phi_u(t,a)=Q_1(s_u(t),a)+Q_2(s_u(t),a)+Q_3(s_u(t),a),\qquad
a_u^\star(t)=\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

At each predecision state, the signed-motion rule selects at most one focal
user. Q2 contributes only to that motion-selected user's score; it is absent
from every other user's score. For the selected user, deployment still uses
the unweighted \(Q_1+Q_2+Q_3\) score and one native masked argmax. There is no
Catfish action at evaluation time, no auction, coordinator, matching, voting,
joint decoder, or post-training override.

## 8. Initial ablation matrix

Every V0.3 pairwise arm retains the same three-Q topology. Replacing a Catfish
means replacing its informed source with its equal-budget neutral source; it
does not delete the Q head or reallocate its gradient budget.

| Arm | C1 source | C2 source | C3 source | Purpose |
|---|---|---|---|---|
| \(N000\) | neutral | neutral | neutral | pairwise-learning control |
| \(F111\) | informed | informed | informed | full Multi-Catfish MCRL |
| \(A011\) | neutral | informed | informed | C1 conditional contribution |
| \(A101\) | informed | neutral | informed | C2 conditional contribution |
| \(A110\) | informed | informed | neutral | C3 conditional contribution |

The original frozen MODQN policy \(M0\) is evaluated as a separate external
baseline under the same fresh seeds and canonical ratio-of-sums EE. It is not
renamed \(N000\). Singleton arms may be added later for full interaction
estimation, but they do not block the first full/leave-one-out trend screen.

## 9. Evaluation and survival rule

For each fresh evaluation seed report:

\[
\eta^N=\frac{\sum_t\sum_{u\in\mathcal U}R_u(t)\Delta t}
{\sum_tP^N(t)\Delta t},
\]

plus total bits \(\mathcal B\), total energy \(\mathcal E\), served fraction, and outage. Reward
means are not substitutes for this endpoint.

- Full mechanism screen: \(F111>N000\) and \(F111>M0\).
- C1 contribution: \(F111>A011\).
- C2 contribution: \(F111>A101\).
- C3 contribution: \(F111>A110\).
- Each comparison is paired by training/evaluation seeds and must satisfy the
  preregistered service guard.

A failed route is reported as a failed mechanism. It is not rescued by
improving its private target, by changing thresholds after reveal, or by a
post-training coordinator.

## 10. Minimal algorithm

```text
freeze TRAIN-only lambda0, kappa, source rules, seeds, and schemas
build D^o from sealed C1/C3 opening pairs
build D^t from sealed C2 native-mask candidate/Main rows at successor slot 1
build held-out D^a and verify the scoped opening/next-slot identity

initialize three independent online functions Q1, Q2, Q3
for each scheduled source update:
    read one version-compatible pair batch from route j
    compute paper target zeta_j/kappa
    update only Qj with the pairwise advantage and gauge loss
    reject any legacy replay/checkpoint/target schema

at evaluation/deployment:
    compute Q1+Q2+Q3
    execute one safe masked argmax
    report fresh-seed ratio-of-sums EE and service measures
```

## 11. Current evidence and remaining gates

- Formula and new pairwise-trainer targeted tests: passed.
- The retained pre-V0.3 C1 lineage has a sealed one-seed, four-episode
  developmental-screen decision of `STOP_AND_REDESIGN_C1`, under the strict
  ceiling `ONE_SEED_4EP_DIRECTIONAL_SCREEN_NOT_ROUTING_AUTHORITY_NOT_CHAPTER5`.
  It is diagnostic history, not current V0.3 held-out efficacy evidence and
  not authority to route or train any Catfish branch.
- C3 single-seed opportunity census: supports implementation, not efficacy.
- Earlier C2 temporal-fork and release-path receipts are superseded design
  evidence only; they are not the current public C2 mechanism or efficacy
  evidence.
- The balanced R13 C2 development screen is recorded in
  [`MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md`](MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md).
  Its provisional core lock passed the aggregate-sign and two-of-three-lineage
  mean rule, under the claim ceiling **DEVELOPMENT ONLY, NOT FORMAL EFFICACY**.
  The b-lineage variability and a-lineage small service loss require longer
  trend and held-out validation.
- The first 10EP matched ablation is
  `VOID_UNINTERPRETABLE_INSTRUMENT`; state-independent action bias dominated
  the summed Q score, several ablation arms produced identical deployed
  actions, and the C1 neutral control did not match cluster geometry. None of
  its directional route flags are evidence.
- Before another EE ablation, a preregistered E1 instrument-validity gate must
  establish state-conditional action resolution and held-out pair
  generalization without using EE as a decision input.
- Every eventual training run checkpoints at least every 100 episodes. The
  user must be notified before any 9000-episode run, which belongs on the
  Ubuntu server.
