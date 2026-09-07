# Multi-Catfish MCRL V0.17 C3 masked soft-KL learnability gate

Status: PRE-OUTCOME CONTRACT. This file becomes frozen only when its SHA-256
is written beside it and before any V0.17 source world is opened.

Claim ceiling: TRAIN/VALIDATION source-only decision-distribution and
learnability evidence. This contract opens no TEST split, simulator-episode
training, or trajectory-EE efficacy claim.

## 1. Frozen post-failure disposition

The sealed V0.16 origin gate returned `FAIL_ORIGIN_GATE` for all three
initializations with integrity and split checks passing. V0.16's composite
hypothesis -- the 402-dimensional B402 carrier plus the V0.15 pivotal-pair
loss -- is retired and must not be retried, early-stopped, or tuned.

The observed failure has a bounded structural explanation. The stable loss
averaged squared violations over all legal non-base actions even though a
single positive violation changes the deployed argmax. On pivotal rows it
constrained teacher versus base but did not require the teacher to beat every
other legal action. The result learned many pivotal pairs while corrupting
more than half of the stable decisions.

The V0.12/V0.13 ZR physical teacher remains unchanged: it previously produced
positive TRAIN-only oracle trajectory evidence but has not been learned
successfully. V0.17 tests exactly one new hypothesis: keep the physical
teacher, B402 state, and action-shared network, and replace only the
pair/hinge objective by a masked full-action soft-distribution objective that
uses the actual final deployment scores.

Closed in this gate are:

1. any C1, C2, Q1, frozen-Q2, canonical-EE, ZR target, compatibility, sign,
   scale, or horizon change;
2. any B402 feature, architecture, width, activation, learning-rate, beta,
   batch size, update count, seed, rung, temperature, or threshold sweep;
3. hard-label cross-entropy, target clipping, margin tuning, action support
   vetoes, loss reweighting, early stopping, or checkpoint selection;
4. reuse of V0.16 source worlds, source arrays, checkpoints, or results as
   V0.17 confirmation evidence;
5. a second decoder, Catfish action, coordinator, auction, vote, iteration,
   or deployment override.

## 2. Unchanged three-head deployment semantics

For context \(h\in\{12,1,2\}\), retain

\[
B^{12}_u(a)=Q_{1,u}(a)+\widehat Q_{2,u}(a),\qquad
B^1_u(a)=Q_{1,u}(a),\qquad
B^2_u(a)=\widehat Q_{2,u}(a).
\]

The detached reference is materialized before Q3:

\[
c^h_u=\arg\max_{a\in\mathcal A^{\rm safe}_u}B^h_u(a).
\]

The environment receives exactly one action:

\[
a_u^*=\arg\max_{a\in\mathcal A^{\rm safe}_u}
       [B^h_u(a)+Q_{3,u}(s^{16}_u,a)].
\]

FULL uses \(h=12\), DROP-C1 uses \(h=2\), and DROP-C2 uses \(h=1\).
DROP-C3 does not evaluate Q3. Q1, Q2, and Q3 remain three independent
parameter and optimizer owners.

## 3. Frozen state, target, and network

Use the unchanged V0.16 B402 state

\[
s^{16}_u=
[x^{15}_{1:13,1:28},\ m^o_{u,1:28},\ x^{15}_{1:7},\
 o^b_u,o^s_u,o^p_u],
\qquad 14\times 28+10=402.
\]

All V0.16 encoder restrictions remain binding: current predecision inputs
only; exact physical `(norad_id, cell_id)` origin identity; no outcome, RNG,
Q-value/rank, target/sign, or future input; illegal focal entries zero; and
immutable arrays.

For every source row and legal action, retain the exact ZR surface
\(z^h_{3,u}(a)\), its compatibility receipt, shared frozen \(\kappa\), and
the centered reference identity

\[
z^h_{3,u}(c^h_u)=0.
\]

The Q3 network remains the one V0.16 action-shared scorer: 28 actions, 14
local features, 10 globals, hidden widths `(100, 50, 50)`, `tanh`, learning
rate `0.001`, beta `0.1`, and a zero-initialized final layer. Context code,
Q1 values, Q2 values, and targets are labels/loss inputs, never Q3 state
features.

## 4. New masked soft-KL objective

For legal actions define fixed-temperature teacher and student logits

\[
T^h_u(a)=B^h_u(a)+z^h_{3,u}(a)/\kappa,
\qquad
S^h_u(a)=B^h_u(a)+Q_{3,u}(s^{16}_u,a).
\]

With temperature fixed to one, let

\[
p^h_T(a)=\operatorname{softmax}_{\mathcal A^{\rm safe}_u}T^h_u(a),
\qquad
p^h_S(a)=\operatorname{softmax}_{\mathcal A^{\rm safe}_u}S^h_u(a).
\]

The only learner objective is

\[
\mathcal L_3=
\frac{1}{N}\sum_{i=1}^{N}
D_{\rm KL}(p_{T,i}\Vert p_{S,i})
+0.1\,\frac{1}{N}\sum_{i=1}^{N}Q_3(s_i,c_i)^2.
\]

The KL is summed over legal actions within each row and then averaged over
rows; it is not averaged over action count. Illegal logits have exactly zero
probability, zero contribution, and zero KL gradient. Teacher/background
tensors are detached. Computation uses numerically stable masked
`log_softmax`; direct `log(softmax(...))` and `0*(-inf)` are forbidden.

At a realizable row-wise optimum, the KL permits
\(Q_3=z_3/\kappa+d_i\); because the reference target is zero, the inherited
gauge selects \(d_i=0\). Thus the loss preserves the additive residual scale
and meaning rather than training an unbounded hard-label classifier.

Every update draws exactly 170 complete source rows from each context in the
fixed order \(h=12,1,2\), including one-action rows. Train three independent
Q3 initializations for exactly 3000 updates. Persist immutable checkpoints at
updates `3, 10, 30, 100, 300, 1000, 3000`; update 3000 alone decides.

## 5. Fresh TRAIN source block

Use only these previously unopened proposed TRAIN worlds:

- learner source: `2026112001`, `2026112002`, `2026112003`;
- validation source: `2026112004`, `2026112005`, `2026112006`.

Use new Q3 initializations `2026112101`, `2026112102`, and `2026112103`.

Use the same three frozen Q1 lineages and their matched frozen Q2 rung-3000
checkpoints as V0.16. Each world-lineage shard contains ten canonical steps,
all three contexts, one common keyed fading field per world, and complete
causal/digest receipts. Use a new V0.17 field-component namespace. No TEST
world may be opened; no V0.16 source shard or result-informed filtering may
enter.

Before freezing this contract, repeat the seed census on the exact local and
Ubuntu-server checkouts. Any prior occurrence as an opened experimental world
invalidates the proposed seed before outcome access and requires a documented
replacement range.

## 6. Mechanical decision

At every rung, report masked validation KL, gauge, teacher entropy, student
entropy, and the same exact decision metrics as V0.16. At update 3000 report,
for every initialization and context:

- background and learned teacher-action agreement;
- pivotal teacher-action agreement;
- stable base-action preservation;
- student change count and rate;
- fraction of changes with positive compatible ZR support;
- change rate among rows with \(o^b_u=0\).

Persist exact B402 identical-state/mask target and teacher-action collision
counts as diagnostics. They have no new post-outcome threshold and cannot
rescue a failed gate.

The gate passes only if every V0.16 decision clause passes at update 3000:

1. full-context learned teacher agreement is strictly above background for
   all three initializations;
2. full-context pivotal agreement is at least `0.50` and stable preservation
   is at least `0.95` for every initialization;
3. every initialization changes at least one full-context action and at least
   `0.80` of those changes have positive compatible ZR support;
4. learned teacher agreement is noninferior to background in both \(h=1\)
   and \(h=2\) for every initialization;
5. all source, state, mask, parameter, split, code, checkpoint, and receipt
   checks pass.

`PASS_SOFTKL_GATE` authorizes only preparation and separate freezing of the
100-episode TRAIN-world five-arm trajectory screen. It does not authorize
500, 1500, 3000, or 9000 episodes.

`FAIL_SOFTKL_GATE` produces `STOP_C3_B402_ACTION_SHARED_STRUCTURALLY`. It
authorizes no Soft-KL retry, longer training, early checkpoint selection,
seed/lr/beta/temperature/weight tuning, clipping, margin, support mask, or
further B402 feature expansion. A different C3 target or architecture would
require an explicit new route decision and independent pre-outcome evidence.
