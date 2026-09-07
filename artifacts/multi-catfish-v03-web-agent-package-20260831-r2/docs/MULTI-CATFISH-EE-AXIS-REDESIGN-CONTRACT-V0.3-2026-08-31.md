# Multi-Catfish MCRL EE-axis redesign contract V0.3

Date: 2026-08-31  
Status: **current formula-first candidate; no training or efficacy claim yet**

Post-gate amendment: the C2 target formula remains binding, while downstream
fixed-hold support loss is superseded by the V0.3B hold-while-legal,
monotone branch-local Main release rule in
`MULTI-CATFISH-MCRL-V03-C2-POSTGATE-DESIGN-DECISION-2026-08-31.md`.

## 1. Binding objective

The canonical endpoint is unchanged:

\[
\eta^N=\frac{\mathcal B}{\mathcal E},\qquad
\mathcal B=\sum_t\sum_{u\in\mathcal U}R_u(t)\Delta t,\qquad
\mathcal E=\sum_t P^N(t)\Delta t.
\]

The sums are taken over the finite evaluation window. The unadorned
\(\tau\) remains reserved for served-segment start time in the physical model.
The compact user rate is the selected-link aggregate

\[
R_u(t)=\sum_{s\in\mathcal S}\sum_{v\in\mathcal V}
x_{u,s,v}(t)R_{u,s,v}(t).
\]

Legacy `r2` and `r3` directions are not objectives. Their values may increase
or decrease. A role survives only if its unilateral contribution can improve
held-out Main-only ratio-of-sums EE without violating the service guard.

The algorithm keeps exactly three deployed Main Q outputs and assigns one
training-time Catfish route to each:

```text
C1 -> Q1: focal opening-step EE surplus
C2 -> Q2: downstream temporal EE surplus
C3 -> Q3: opening-step non-focal rate externality
```

The name remains **Multi-Catfish MCRL**. `SMC-ER` is not required as a new
algorithm name. No auction, coordinator, joint decoder, voting, pair matching,
or post-training override exists at deployment.

## 2. One frozen multiplier and one physical world

Freeze one TRAIN-only calibration value before inspecting Catfish outcomes:

\[
\lambda_0=\frac{\mathcal B_0^M}{\mathcal E_0^M}.
\]

The same hexadecimal floating-point value is used for every arm, window, head,
and candidate in one stage. Per-window, per-arm, and per-candidate multipliers
are forbidden.

For matched candidate and reference branches at offset \(k\), define

\[
g_k=\Delta\mathcal B_k-\lambda_0\Delta\mathcal E_k,
\]

with

\[
\Delta\mathcal B_k=\Delta t\sum_{i\in\mathcal U}
[R_i^C(k)-R_i^M(k)],\qquad
\Delta\mathcal E_k=\Delta t[P_C^N(k)-P_M^N(k)].
\]

Both branches use the same canonical multi-user physics. The V0.2
single-user isolated evaluator is removed: it changed bandwidth, interference,
load, beam activation, and marginal energy conventions, so its residual was not
a clean spatial effect.

## 3. Exact V0.3 three-role decomposition

At the opening anchor only focal user \(u\)'s physical action differs. Let
\(M\) be the reference action and \(C\) the unilateral candidate.

### C1/Q1: focal net-surplus route

\[
\zeta_{1,u}=\Delta t\,[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t\,[P_C^N(0)-P_M^N(0)].
\]

All opening-step energy change is assigned to C1 because the focal action is
the only intervention. This is a causal accounting choice, not a per-user
physical power allocation. C1 retains the RIS-lineage EXP/ACRM training route;
EXP/ACRM controls experience generation and auxiliary learning, not the EE
formula.

### C3/Q3: spatial externality route

\[
\zeta_{3,u}=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
[R_i^C(0)-R_i^M(0)].
\]

C3 learns the immediate effect of the focal action on other users through
eligible beam load, bandwidth sharing, co-channel interference, and shared
activation state. It is a unilateral effect: coordinated pairs may be reported
as diagnostics but may not generate or execute the deployed action.

`spatial externality` here deliberately means a non-focal rate externality.
Shared activation and PA energy caused at the opening step is already charged
to C1; duplicating it in C3 would double count.

### C2/Q2: temporal route

For an equal matched horizon with offsets \(0,\ldots,H^c-1\),

\[
\zeta_{2,u}=\sum_{k=1}^{H^c-1}
\left\{
\Delta t\sum_{i\in\mathcal U}[R_i^C(k)-R_i^M(k)]
-\lambda_0\Delta t[P_C^N(k)-P_M^N(k)]
\right\}.
\]

C2 learns only the downstream consequence of association timing: hold,
switch, release, recurrence-power evolution, interruption, and future
availability. With the current four-offset fork, offsets `1,2,3` all belong to
C2; omitting release offset `3` is an error.

C2 is continuation-policy dependent. The branch-local Main version, horizon,
candidate grammar, physical-ID binding, and random-field version are therefore
part of the frozen target definition. The V0.3B grammar holds the
opening candidate while it remains uniquely legal in the candidate branch and
then releases once to complete contemporaneous branch-local Main. The trigger
is reactive at the current offset, never look-ahead or outcome-dependent.

### Exact accounting identity

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}=\sum_{k=0}^{H^c-1}g_k.
\]

This identity proves non-overlapping bookkeeping only. It does not prove that
a head is learnable or that EE improves.

## 4. Learning semantics and deployed action

Pilot 1 uses fixed-horizon pairwise action-advantage regression with no Bellman
bootstrap:

\[
\widetilde\zeta_{j,u}=\frac{\zeta_{j,u}}{\kappa},\qquad
\kappa=\frac{\mathcal B_0^M}{n_0},
\]

Here \(n_0\) is the number of decisions in the TRAIN-only scale-calibration
window.

\[
\ell_j=w_j\left(
[Q_j(s_u(t),a_u^C(t))-Q_j(s_u(t),a_u^M(t))
-\widetilde\zeta_{j,u}]^2
+\beta Q_j(s_u(t),a_u^M(t))^2
\right).
\]

Use one shared positive output scale \(\kappa\), not three head-specific output
scales. Loss weights \(w_j=1/\nu_j^2\) may normalize optimization noise
but must not change output units. Freeze \(\kappa\), \(\nu_j\), and
\(\beta\) on the TRAIN-only calibration partition; the initial proposed
\(\beta\) is `0.1` and remains tunable before preregistration.

Do not add a redundant sum loss. Do not combine this estimator with the old
independent per-head `max Q_target` Bellman target. Old checkpoints cannot be
resumed.

The deployed score is

\[
\Phi_u(t,a)=Q_1(s_u(t),a)+Q_2(s_u(t),a)+Q_3(s_u(t),a),\qquad
a_u^\star(t)=\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

Thus each head is in the same normalized EE-surplus unit and the scientific
weights are exactly `(1,1,1)`. Only the masked Main action executes.

## 5. Phase-I source generation and bounded refresh

Expensive counterfactual physics must not run inside every ordinary training
step. The first implementation uses a source-generation phase:

1. C1 retains the RIS-lineage dull-rollout/EXP stratification and private ACRM
   preparation.
2. C2 evaluates a sealed, bounded set of temporal anchors and stores matched
   hold-while-legal/release pairs with their precomputed \(\zeta_2\), release
   offset/reason, and held-key support labels in \(D^t\).
3. C3 enumerates unilateral opening actions at sealed anchors and stores
   matched pairs with their precomputed \(\zeta_3\) labels in \(D^o\).
4. Pairwise Q pretraining and ordinary Main training read these datasets; they
   do not rerun the oracle physics for every gradient step.

Every source row binds the reference policy digest, \(\lambda_0\), state schema,
candidate grammar, horizon, random-field version, and physical IDs. Since C2
labels are continuation-policy dependent, source datasets may be refreshed
only at declared checkpoint boundaries. The initial runtime design allows a
bounded refresh at a 100-episode boundary, never an outcome-triggered refresh.
Old and new policy-version rows must not be silently mixed.

Before a 500/1500-episode run, a 10--20 episode benchmark must show that replay
training, checkpointing, and any scheduled refresh fit the preregistered runtime
budget. A runtime failure blocks the longer run rather than relaxing the
scientific contracts.

## 6. Minimum observation/schema changes

The 112-dimensional legacy state is insufficient. Before learning, version the
state, replay, trainer input, and checkpoint schemas together.

Q2 minimally needs:

- previous recurrence power normalized by the power budget;
- current-to-segment-start gain ratio;
- segment age;
- one bit distinguishing no previous association from an incumbent that fell
  outside the current candidate table.

Q3 minimally needs lagged, predecision values for each candidate beam:

- eligible served load;
- active-beam/satellite state;
- maximum required link power.

These fields are lagged because current gated load does not exist before the
simultaneous action is selected. They are broadcast observations, not action
coordination. The exact dimension is frozen only after a state-schema test
shows every field is causal and action-slot aligned.

## 7. Branch, retention, and service contracts

1. Candidate and reference initially differ only in the focal physical action.
2. Candidate schedules are sealed before outcomes are evaluated.
3. Positive, zero, negative, and all-dark outcomes are retained.
4. Service/outage protection is a hard mask or separate acceptance guard, not a
   fourth optimized reward.
5. Opening C1/C3 uses the canonical action evaluator without state mutation.
6. C2 uses equal horizons, branch-local frozen Main continuation, and a
   branch-independent keyed common-random field under canonical fading.
7. A completed C2 trace is scored regardless of the old r2/useful-bits/EE
   certificate. Downstream held-key support expiry triggers the sealed
   monotone release and remains a complete outcome. Opening support failure is
   right-censored, never silently dropped or imputed.
8. The old fixed-hold keyed gate is sealed `INDETERMINATE`; its 5/5
   positive-seed observation is bounded headroom evidence only. The
   reactive-release amendment requires its own fresh-seed gate.

## 8. Formula-first gates before learning

- **P1, no interaction:** unchanged non-focal rates imply \(\zeta_3=0\).
- **P2, identical branches:** same action with matched randomness gives all
  three targets exactly zero.
- **P3, trace integrity:** stored per-user rates sum to stored system bits at
  every offset.
- **P4, multiplier separation:** changing \(\lambda_0\) cannot change C3.
- **G-C3, unilateral headroom:** on held-out anchors, the action maximizing
  \(\zeta_1+\zeta_3\) must sometimes differ from and outperform the action
  maximizing \(\zeta_1\).
- **G-C2, temporal headroom:** service-safe completed branches must contain
  positive \(\zeta_2\) under the fixed global multiplier across distinct fresh-seed
  anchors; release-offset incidence and any remaining censoring are reported
  separately.
- **G-D, distinctness:** no target may be always zero or a near-affine copy of
  another target, and each must sometimes alter the final masked argmax.
- **G-O, observability:** identical proposed observations/actions must not carry
  persistent opposite-sign targets. If they do, expand the state or reject the
  role before training.

Thresholds and seed counts must be sealed before the multi-seed gate run. A
small smoke run is engineering evidence only and cannot set the threshold from
the same outcomes.

## 9. Training authorization boundary

No 1500/3000/9000-episode run is authorized from this document alone. The next
sequence is:

1. pass unit-level P1-P4;
2. run no-training C3 unilateral census;
3. run deterministic C2 plumbing probe; completed;
4. run the fixed-hold keyed-CRN census; completed as `INDETERMINATE`;
5. implement and test the hold-while-legal release amendment; completed
   (256/256 targeted tests), then freeze its new source manifest and
   preregistration;
6. run its fresh-seed keyed physical-headroom gate;
7. complete the versioned state/replay/checkpoint schema;
8. run a bounded matched learnability pilot;
9. only then authorize matched short-EP ablations.

Before any 9000-episode training, notify the user explicitly. Every eventual
training run must checkpoint every 100 episodes. Heavy training and sweeps run
on the Ubuntu server, not the local WSL/browser environment.

## 10. Claim boundary

V0.3 is a coherent mechanism proposal because its three roles are an exact
partition of one fixed-\(\lambda_0\), single-mover EE-surplus counterfactual:
focal now, others now, and everyone later. At this stage it is **not yet proven
effective**. The formula tests establish accounting correctness; the censuses
establish available physical headroom; only matched held-out ratio-of-sums EE
ablation can establish efficacy.
