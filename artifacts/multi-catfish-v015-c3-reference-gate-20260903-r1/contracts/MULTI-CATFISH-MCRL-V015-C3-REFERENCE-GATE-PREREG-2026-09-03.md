# Multi-Catfish MCRL V0.15 C3 reference-conditioned learnability gate

Status: PRE-OUTCOME CONTRACT, REVISION R2. This contract becomes frozen only
after its SHA-256 is written beside it and before any V0.15-R source world is
opened. R1 was rejected before source access because its contiguous-prefix
layout was incompatible with the existing feature-major ActionSet scorer;
the intended features, targets, worlds, learner, and gates are unchanged.

Claim ceiling: TRAIN/VALIDATION source-only representation and learnability
evidence. No trajectory-EE efficacy claim, no TEST split, and no episode
training are authorized by this contract.

## 1. Closed routes and single hypothesis

The following routes are closed and must not be rerun in this gate:

1. an oracle-only change from exact OPS-3 context to learned-Q2 context;
2. another loss, threshold, rescaling, or margin sweep on the 287-dimensional
   V0.14 Q3 state;
3. another C3 target formula or compatibility-gate change;
4. another state block beyond the three declared below.

The one live hypothesis is that the unchanged ZR C3 target is physically
useful but not learnable from the focal user's 287-dimensional state because
that state omits the joint background induced by the deployed base heads.

## 2. Detached preliminary reference

For base-head context \(h\in\{12,1,2\}\), define

\[
B^{12}_u(a)=Q_{1,u}(a)+\widehat Q_{2,u}(a),\qquad
B^1_u(a)=Q_{1,u}(a),\qquad
B^2_u(a)=\widehat Q_{2,u}(a).
\]

For every user, compute all reference actions before evaluating Q3:

\[
c^h_u=\arg\max_{a\in\mathcal A^{\rm safe}_u}B^h_u(a).
\]

The native safe mask is used exactly. Link-power service feasibility must not
silently replace that mask. An all-empty native row uses \(c^h_u=-1\); all
other references must be legal. Q1 and Q2 parameters and outputs are detached
and immutable at this seam. Q3 cannot change or iteratively recompute any
\(c^h_u\).

The reference is a non-executed context pass. The environment receives only
one final action vector:

\[
a_u^*=\arg\max_{a\in\mathcal A^{\rm safe}_u}
       \left[B^h_u(a)+Q_{3,u}(s^h_u,a)\right].
\]

For FULL, \(h=12\). For DROP-C1, \(h=2\). For DROP-C2, \(h=1\).
DROP-C3 executes \(B^{12}\) and does not evaluate Q3. Thus an ablation may
not expose Q3 to an output from the head being omitted.

## 3. Fixed 371-dimensional Q3 state

The V0.14 state contains 280 action-local coordinates followed by seven
global coordinates. Preserve both sets byte-identically, insert exactly three
28-action-aligned blocks between them, and retain the feature-major learner
layout:

\[
[\,x^{\rm local}_{0:280},\ \rho^b_{1:28},\ \rho^s_{1:28},\
\rho^p_{1:28},\ x^{\rm global}_{1:7}\,].
\]

The total dimension remains

\[
287+3\times 28=371.
\]

For legal focal action \(a\), let
\(k_u(a)=(n_u(a),j_u(a))\) be the exact physical beam and
\(s_u(a)=n_u(a)\) its satellite. A peer reference is physically active only
when its native reference is also opening-service-feasible under the
canonical predecision recurrence-power calculation. Let
\(d_u=\max(U-1,1)\). The fixed blocks are:

\[
\rho^b_{u,a}=\frac{1}{d_u}\sum_{v\ne u}
\mathbf 1\{c^h_v\ne-1,\ o_v(c^h_v)=1,\ k_v(c^h_v)=k_u(a)\},
\]

\[
\rho^s_{u,a}=\frac{1}{d_u}\sum_{v\ne u}
\mathbf 1\{c^h_v\ne-1,\ o_v(c^h_v)=1,\ s_v(c^h_v)=s_u(a)\},
\]

and

\[
\rho^p_{u,a}=\bar p_u(a)-
\max_{v\ne u:\,k_v(c^h_v)=k_u(a),\,o_v(c^h_v)=1}
\bar p_v(c^h_v),
\qquad
\bar p_u(a)=\min\!\left(\frac{\widehat p_u(a)}{P_{\max}},1\right).
\]

The maximum of an empty peer set is zero. Illegal focal entries are exactly
zero. Fractions lie in \([0,1]\) and the power gap lies in \([-1,1]\).
Physical identities, not flat action indices, define every match.

Both \(o\) and \(\widehat p\) are computed from the current gain, committed
segment-start gain, canonical recurrence-power rule, and frozen
\(P_{\max}\). They must not call `evaluate_actions`, read a realised outcome,
consume an RNG, or use a future trace. No target, ZR compatibility bit, or
teacher action enters the state.

The network remains the independent 28-output ActionSet scorer with the first
`13 * 28 = 364` coordinates interpreted as 13 feature-major action-local
blocks and the final seven coordinates interpreted as globals. It uses hidden
widths `(100, 50, 50)`, `tanh`, learning rate `0.001`, and a zero-initialised
final residual layer. Q1, Q2, and Q3 keep separate parameters and optimizers;
no gradient crosses the reference seam.

## 4. One learner objective

Only the V0.15 decision-frontier residual objective is permitted. For each
context-row, form the unchanged teacher

\[
T^h_u(a)=B^h_u(a)+z^h_{3,u}(a)/\kappa.
\]

If the teacher action differs from the base action, retain the `(base,
teacher)` pair. Otherwise retain `(base, teacher-surface runner-up)`. The
fixed loss is the existing exact residual term plus unit-weight pivotal
decision and stable-decision constraints and the existing gauge term. No
alternative learner, loss coefficient, threshold, margin, route weight, or
normalization is compared in this gate.

Training draws must be balanced across \(h=12,1,2\), so the same Q3 can be
evaluated without hidden use of an omitted head. The context identifier is
not an input: the physical reference blocks encode the resulting context.

## 5. Fresh source block and fixed compute

Use six previously unopened TRAIN worlds:

- learner source: `2026110001`, `2026110002`, `2026110003`;
- validation source: `2026110004`, `2026110005`, `2026110006`.

Use the three already sealed Q1 lineages and their matched, frozen V0.14 Q2
rung-3000 checkpoints. Each world-lineage harvest contains ten canonical
steps and all three base-head contexts. One common keyed fading field is used
within each world. No TEST world may be opened.

Train exactly three Q3 initializations `2026110101`, `2026110102`, and
`2026110103` for 3000 updates. Emit immutable checkpoints at updates
`3, 10, 30, 100, 300, 1000, 3000`; update 3000 is the only decision rung.
All source arrays, parameter states, optimizer states, masks, context counts,
and file digests must be receipted.

## 6. Mechanical decision

For each initialization and each context, report:

- background-to-teacher agreement;
- learned `(B+Q3)`-to-teacher agreement;
- pivotal teacher-action agreement;
- stable base-action preservation;
- student action-change exposure;
- fraction of changed actions with positive compatible ZR support.

The gate passes only if all conditions hold at update 3000:

1. in full context \(h=12\), learned all-row teacher agreement is strictly
   greater than background agreement for all three initializations;
2. full-context pivotal agreement is at least `0.50` and stable preservation
   is at least `0.95` for every initialization;
3. every initialization has nonzero full-context change exposure and at
   least `0.80` of those changes have positive compatible ZR support;
4. in both ablation contexts \(h=1\) and \(h=2\), learned all-row teacher
   agreement is not below background agreement for any initialization;
5. every digest, mask, causal-state, frozen-parameter, and split check passes.

PASS authorizes only a separately preregistered 100-episode TRAIN-world
five-arm trajectory ablation with a checkpoint at episode 100. It does not
authorize 1500, 3000, or 9000 episodes. FAIL rejects the reference-conditioned
C3 architecture. On FAIL, no state-block addition, loss/threshold sweep,
oracle rerun, or episode experiment may be started under this contract.
