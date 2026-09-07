# Multi-Catfish MCRL V0.11 joint-C3 ordered oracle preregistration

Status: **FROZEN BEFORE OUTCOME ACCESS**  
Scope: TRAIN-development, no learner, no TEST, no efficacy claim  
Decision: choose at most one C3 teacher family by a frozen selection table,
without selecting whichever result happens to be positive.

## 1. Reason for this gate

V0.10 exact unilateral MONE failed closed.  Its six-arm receipt showed
`FULL / DROP-C3 - 1 = -2.6369725638161135%`, with all three lineage
directions negative.  The sum of selected unilateral opening surpluses was
positive in all 60 diagnostics, whereas the realised joint direction
reversed in 28.  About half of all users changed action at each step.  The
next gate therefore tests two predeclared depths of the same physical C3
idea: externality under anticipated joint response.

This file freezes the candidates and their selection order before opening the
new world.  V0.10 results motivate the hypothesis but cannot select a seed,
sign, scale, permutation count, sweep count, or acceptance threshold here.

## 2. Architecture and immutable quantities

The candidate production architecture remains exactly three independent
28-action Q functions, one common safe mask, the left-to-right unweighted sum
`Q1 + Q2 + Q3`, one smallest-native-index masked argmax, and one executed
Main action.  There is no deployed sweep, coordinator, auction, second
decoder, route weight, sign flip, or post-training override.

The final metric remains canonical ratio-of-sums EE,

\[
\eta=\frac{\sum_{e,t,u}\Delta t\,R_{e,t,u}}
           {\sum_{e,t}\Delta t\,P^N_{e,t}}.
\]

The following are inherited byte-for-byte from V0.10: three frozen Q1
checkpoints, corrected execution-equivalent OPS3 `O2`, `lambda0`, `kappa`,
`Delta t`, TLE files, physics, masks, and native action semantics.  Q1 and O2
are read-only.  Every counterfactual evaluation retains its sign and uses the
same keyed common-random field without mutating live simulator or RNG state.

## 3. Shared C3-free background

At each arm-owned decision state, compute Q1 and O2 once and define

\[
b^0_u=\min\arg\max_{a\in\mathcal A_u^{\rm safe}}
      \{Q_{1,u}(a)+O_{2,u}(a)\}.
\]

For a joint action `c`, focal user `u`, and legal action `a`, define the exact
current-slot non-focal externality

\[
z_{3,u}(a\mid c_{-u})=
\Delta t\sum_{v\ne u}
\left[R_v(c_{-u},a)-R_v(c)\right].
\]

The reference action `c_u` is exactly zero, illegal entries are zero behind
the common mask, and `O3 = z3 / kappa`.  C3 contains no focal rate, energy,
future term, clipping, or tunable scale.

## 4. Candidate M: self-consistent M1-D

Initialize `c = b0`.  Sweep users in the fixed order `0,1,...,99`.  When user
`u` is visited, evaluate every legal focal replacement against the current
mixed joint background and update

\[
c_u\leftarrow\min\arg\max_{a\in\mathcal A_u^{\rm safe}}
\{Q_{1,u}(a)+O_{2,u}(a)+z_{3,u}(a\mid c_{-u})/\kappa\}.
\]

At most five complete Gauss--Seidel sweeps are allowed.  Convergence means
one complete sweep with zero changes.  A repeated non-fixed joint vector, or
any change remaining after sweep five, is
`FAIL_M1D_NO_FIXED_POINT`.  The final iterate must never be executed merely
because the cap was reached.

To preserve a complete ten-step failure receipt, a mechanically failed M1-D
anchor executes `b0` only as a fail-closed recording action.  The entire arm
is then ineligible for `PASS_M1D`, and its episode EE is diagnostic only.
This is not an algorithm fallback and cannot rescue or partially pass M1-D.

On convergence, call the fixed point `bM` and rebuild one complete O3 surface
around it.  Recompute the production-form action

\[
a^M=\min\arg\max_{\rm mask}\{Q_1+O_2+O_3(\cdot\mid b^M)\}.
\]

The equality `aM == bM` must hold bit-for-bit for every user.  The binding arm
executes `aM`, never a cached sweep output.  Any mismatch is
`FAIL_M1D_ONE_PASS_EQUIVALENCE`.  The sweep is a training-time oracle/source
construction only; a passing oracle does not authorize a deployed sweep.

## 5. Candidate A: antithetic-permutation MONE

First build the V0.10 unilateral MONE surface around `b0` and construct the
teacher-only proposal

\[
p=\min\arg\max_{\rm mask}\{Q_1+O_2+O_3(\cdot\mid b^0)\}.
\]

Generate exactly one keyed permutation `pi` of users and its reverse.  Its key
contains only the field component, new world seed, and step index; it excludes
arm, lineage, actions, target values, and outcomes.  For order `rho`, the
background for focal `u` puts predecessors at `p` and successors at `b0`.
For every legal action,

\[
z^A_{3,u}(a)=\frac{\Delta t}{2}
\sum_{\rho\in\{\pi,\pi^{-1}\}}\sum_{v\ne u}
\left[R_v(c^{-u}_{\rho,u}\oplus a)
-R_v(c^{-u}_{\rho,u}\oplus b^0_u)\right],
\qquad O^A_3=z^A_3/\kappa.
\]

The proposal and permutations exist only inside target generation.  The
binding arm executes exactly one production-form action

\[
a^A=\min\arg\max_{\rm mask}\{Q_1+O_2+O^A_3\}.
\]

For each order, also compute the matching focal term `z1` from focal bits and
network energy.  At `a = p_u`, the sum of `z1 + z3` along the order must
equal the exact fixed-`lambda0` joint opening surplus `G(p)-G(b0)` within the
declared floating-point tolerance.  This identity is a mechanics assertion,
not an EE acceptance condition.

## 6. Exact-O1 diagnostic family

A nonbinding diagnostic removes frozen-Q1 approximation while retaining O2.
It uses the same per-user counterfactual evaluations and

\[
O_{1,u}(a\mid c_{-u})=
\frac{\Delta t\,[R_u(c_{-u},a)-R_u(c)]
-\lambda_0\Delta t\,[P^N(c_{-u},a)-P^N(c)]}{\kappa}.
\]

`DIAG-O-DROP` finds a five-sweep fixed point under `O1 + O2`.
`DIAG-O-FULL` starts from that point and finds a five-sweep fixed point under
`O1 + O2 + O3`.  Each must pass the same convergence and final one-pass
equivalence checks before its action can be executed.  Along the full exact
`O1 + O2 + O3` sweep, the fixed-`lambda0` opening surplus plus the separable
O2 score must not decrease beyond floating-point tolerance.

This diagnostic may identify a C1-alignment blocker.  It cannot rescue a
failed binding arm, provide deployed actions, authorize Q1 replacement, or
change the frozen candidate order.

If either diagnostic solver fails mechanically, that arm likewise executes
the shared `b0` only to finish a fail-closed receipt; `PASS_O` is then
impossible and all resulting EE values are nonbinding.

## 7. Frozen panel and arms

- split: TRAIN only;
- world seed: `2026104701`;
- seed freshness: a repository-wide text search immediately before this file
  was created returned no occurrence;
- lineages: `2026092101`, `2026092102`, `2026092103`;
- users: 100;
- steps per episode: 10;
- common field component: `MCRL_V011_JOINT_C3_ORDERED_ORACLE_V1` plus the
  world seed; field excludes arm and lineage;
- five arms, one episode for every arm-lineage pair, 15 episodes total:

| Arm | Executed score/action | Role |
|---|---|---|
| `DROP_C3` | `Q1 + O2` / `b0` | shared binding comparator |
| `FULL_M1D` | one-pass `Q1 + O2 + O3(bM)` / `aM` | candidate M binding arm |
| `FULL_AP` | one-pass `Q1 + O2 + O3A` / `aA` | candidate A binding arm |
| `DIAG_O_DROP` | converged one-pass `O1 + O2` | nonbinding diagnostic |
| `DIAG_O_FULL` | converged one-pass `O1 + O2 + O3` | nonbinding diagnostic |

The run is heavy no-training oracle work.  Execute 15 independent shards on
the Ubuntu server.  From the observed V0.10 seven-minute six-shard wall time,
budget 45--75 minutes for the slowest five-sweep shards, plus implementation
and receipt verification.  No browser or GUI is required.

## 8. Candidate gates

For candidate `X` in `{M1D, AP}`, define `PASS_X` only if all of the following
hold against the shared `DROP_C3` arm:

1. all source/runtime/contract/checkpoint/TLE hashes authenticate;
2. no TEST access, learner, optimizer, target network, or future-policy query;
3. masks, reference zeros, focal-only branch mutation, keyed field identity,
   Q1 immutability, and simulator/RNG immutability pass;
4. candidate legal-action spread and executed-action exposure are nonzero;
5. pooled ratio-of-sums EE is strictly `FULL_X > DROP_C3`;
6. at least two of three lineage EE contrasts are strictly positive;
7. pooled served user-steps are not below DROP-C3 and at least two of three
   lineage service contrasts are nonnegative;
8. every required M1-D fixed point converges within five sweeps and passes
   exact final one-pass equivalence; and
9. all candidate-specific identities pass; and
10. among exposed anchors, a strict majority must not have negative realised
    fixed-`lambda0` joint opening surplus relative to `b0`.

Item 8 applies only to M1-D.  AP must additionally record the distance of its
executed profile from both `b0` and `p`, and the realised joint opening
surplus versus its antithetic credited sum.  M1-D must record sweep counts,
cycles, `G(bM)-G(b0)`, and learned-Q1 versus exact-O1 action/rank agreement.
The item-10 sign census is frozen as a hard stop; its magnitude is diagnostic
only.  Diagnostics cannot rescue an EE or service failure.

Define `PASS_O` analogously for `DIAG_O_FULL > DIAG_O_DROP`, including exact
convergence/equivalence, pooled and two-of-three positive EE, and the same
service guard.  It is diagnostic only.

## 9. Frozen ordered selection table

Let `A = PASS_AP`, `M = PASS_M1D`, and `O = PASS_O`.  Directly comparing the
magnitudes of `FULL_AP` and `FULL_M1D` is report-only and never selects a
candidate.

| Frozen condition | Mechanical decision |
|---|---|
| `A and (M or O)` | `GO_AP_MONE_LEARNABILITY_PREREG_ONLY` |
| `(not A) and M` | `GO_M1D_LEARNABILITY_PREREG_ONLY` |
| `A and (not M) and (not O)` | `INCONSISTENT_AP_ONLY_NO_LEARNER_REVIEW` |
| `(not A) and (not M) and O` | `C1_ALIGNMENT_BLOCKS_C3_NO_LEARNER` |
| `(not A) and (not M) and (not O)` | `JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED` |

There is no post-outcome AP fallback, M1-D fallback, candidate rescaling, user
order search, extra permutation, seed expansion, threshold change, or horizon
change.  The two candidates run as one preregistered ordered experiment.

## 10. Claim ceiling and next action

A GO decision establishes only that one C3 teacher is worth a separately
preregistered state-only source/learnability/reproduction gate.  It does not
establish a learned Q3, held-out performance, C3 efficacy, three-head efficacy,
or permission for 100/500/1500/3000/9000-episode training.

The later Q3 learner may consume only decision-time physical state: focal and
action geometry, segment status, candidate beam/satellite lagged load and
rate burden, RF maximum and activation, cochannel victim/interference
summaries, mask-derived contender pressure, and the existing safe mask.  It
must not consume Q1/O2 values, rankings or actions, `b0`, `bM`, `p`, sweep or
permutation position, arm identity, outcomes, future information, or target
signs.  Frozen Q1/O2 may be queried only by the training-time teacher.

If a GO occurs, the next gate must test held-out TRAIN state/action skill and
whether one state-only Q3, used through one `Q1 + Q2 + Q3` argmax, reproduces
the selected teacher sufficiently to retain EE and service direction.  Only
after that gate passes may a short-episode learner experiment be proposed,
with checkpoints every 100 episodes and clean frozen-Q3 subset ablations.
