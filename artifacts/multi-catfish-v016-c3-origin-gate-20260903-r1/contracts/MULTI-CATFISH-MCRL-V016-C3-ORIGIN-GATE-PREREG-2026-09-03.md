# Multi-Catfish MCRL V0.16 C3 origin-aware learnability gate

Status: PRE-OUTCOME CONTRACT. This file becomes frozen when its SHA-256 is
written beside it and before any V0.16 source world is opened.

Claim ceiling: TRAIN/VALIDATION source-only representation and learnability
evidence. This contract opens no TEST split, simulator-episode training, or
trajectory-EE efficacy claim.

## 1. Post-failure disposition and one live hypothesis

The sealed V0.15-R gate failed in all three initializations with integrity and
split checks passing. Its 371-dimensional architecture is rejected and must
not be retried or tuned. The post-result diagnosis found a decision-relevant
input omission: the action-shared scorer could observe destination-local
reference burden but could not observe the focal user's detached origin.

Two independent clean-context reviews selected the same bounded successor:
retain the existing action-shared Q3 learner and add only the focal origin
identity and the three already-computed origin summaries. The live hypothesis
is that this 402-dimensional carrier is sufficient to learn the unchanged ZR
C3 decision frontier.

The following are closed in this gate:

1. a C3 reward, target, sign, scale, compatibility, or horizon change;
2. a loss, optimizer, learning-rate, weight, seed, rung, or threshold sweep;
3. a deterministic deployment support mask or second decision stage;
4. a pair-token, full-peer-token, attention, recurrent, or coordinator model;
5. any C1, C2, canonical-EE, Q1, or frozen-Q2 change;
6. reuse of the already opened V0.15 worlds as confirmation evidence.

The retrospective V0.15 collision and count-bin analyses are post-outcome
development diagnostics only. They are neither learner evidence nor an input
to the mechanical decision below.

## 2. Detached reference and one executed action

For context (h\in\{12,1,2\}), retain

\[
B^{12}_u(a)=Q_{1,u}(a)+\widehat Q_{2,u}(a),\qquad
B^1_u(a)=Q_{1,u}(a),\qquad
B^2_u(a)=\widehat Q_{2,u}(a),
\]

and materialize every focal reference before evaluating Q3:

\[
c^h_u=\arg\max_{a\in\mathcal A^{\rm safe}_u}B^h_u(a).
\]

Q1 and Q2 remain detached and immutable. Q3 cannot change or recompute the
reference. The environment receives only

\[
a_u^*=\arg\max_{a\in\mathcal A^{\rm safe}_u}
       [B^h_u(a)+Q_{3,u}(s^h_u,a)].
\]

FULL uses (h=12), DROP-C1 uses (h=2), and DROP-C2 uses (h=1).
DROP-C3 does not evaluate Q3. There is one Q3, one native mask, and one final
argmax; no Catfish action, coordinator, auction, iteration, or override exists
at deployment.

## 3. Fixed 402-dimensional origin-aware state

Start from the frozen V0.15 feature-major layout

\[
[x^{15}_{1:13,1:28},\ x^{15}_{1:7}],
\]

whose 13 local blocks contain the V0.14 ten-block prefix followed by

\[
\rho^b_{u,a},\quad \rho^s_{u,a},\quad \rho^p_{u,a}.
\]

The meanings, normalization, focal exclusion, opening-service rule, current
required-power calculation, and physical-identity rules of these three blocks
remain byte-identical to V0.15.

For a nonempty reference, let

\[
k_u(a)=(n_u(a),j_u(a)),\qquad
m^o_{u,a}=\mathbf 1\{k_u(a)=k_u(c^h_u)\}.
\]

The comparison uses the exact physical `(norad_id, cell_id)` key, not flat
action index, so duplicate native slots on the same beam receive the same
indicator. For (c^h_u=-1), every (m^o_{u,a}) is zero.

Append the three origin summaries already present in the V0.15 action blocks:

\[
o^b_u=\rho^b_{u,c^h_u},\qquad
o^s_u=\rho^s_{u,c^h_u},\qquad
o^p_u=\rho^p_{u,c^h_u}.
\]

They are zero when (c^h_u=-1). The fixed state is

\[
s^{16}_u=
[x^{15}_{1:13,1:28},\ m^o_{u,1:28},\ x^{15}_{1:7},\
 o^b_u,o^s_u,o^p_u],
\]

with dimension

\[
14\times 28+10=402.
\]

The encoder may use only the same current predecision observation,
slot tables, detached joint reference, opening-service bits, and required
power already accepted by V0.15. It must not call `evaluate_actions`, read a
realized outcome, consume RNG, inspect Q values/ranks, use a target or its
sign, or access future information. Illegal focal entries are zero and all
arrays are immutable.

The network remains one independent action-shared scorer. Its configuration is
fixed to 28 actions, 14 local features, 10 globals, hidden widths
`(100, 50, 50)`, `tanh`, learning rate `0.001`, shared frozen \(\kappa\),
`beta=0.1`, and a zero-initialized final layer. Q1, Q2, and Q3 share neither
parameters nor optimizers.

## 4. Unchanged target and learner

The exact ZR C3 surface, compatibility bit, and scale remain unchanged. For
each row, the teacher is

\[
T^h_u(a)=B^h_u(a)+z^h_{3,u}(a)/\kappa.
\]

Retain the existing V0.15 pivotal residual source and loss without alteration:
a pivotal row uses `(base, teacher)`; a stable row uses `(base,
teacher-surface runner-up)`; the signed residual is unchanged; the decision
and stability weights remain one; the gauge weight remains `0.1`.

Every update draws exactly 170 rows from each of (h=12,1,2). Context code is
not a learner input. Train three independent Q3 initializations for exactly
3000 source updates. Persist immutable checkpoints at updates
`3, 10, 30, 100, 300, 1000, 3000`; update 3000 is the only decision rung.

## 5. Fresh TRAIN source block

Use only these previously unopened TRAIN worlds:

- learner source: `2026111001`, `2026111002`, `2026111003`;
- validation source: `2026111004`, `2026111005`, `2026111006`.

Use Q3 initializations `2026111101`, `2026111102`, and `2026111103`.

Use the same three frozen Q1 lineages and their matched frozen Q2 rung-3000
checkpoints as V0.15. Each world-lineage shard contains ten canonical steps,
all three contexts, the common keyed fading field, and complete causal and
digest receipts. No TEST world may be opened. No source or result path may be
overwritten.

## 6. Mechanical decision and hard stop

At update 3000, report for every initialization and context:

- background and learned teacher agreement;
- pivotal teacher-action agreement;
- stable base-action preservation;
- student change count and rate;
- fraction of changes with positive compatible ZR support;
- change rate among rows with (o^b_u=0).

The final item is a preregistered falsifiable diagnostic with expected value
at most `0.02`; it is not an extra pass clause and cannot rescue a failed
gate.

The gate passes only if every original V0.15 clause passes at update 3000:

1. full-context learned teacher agreement is strictly above background for
   all three initializations;
2. full-context pivotal agreement is at least `0.50` and stable preservation
   is at least `0.95` for every initialization;
3. every initialization changes at least one full-context action and at least
   `0.80` of those changes have positive compatible ZR support;
4. learned teacher agreement is noninferior to background in both (h=1) and
   (h=2) for every initialization;
5. all source, state, mask, parameter, split, code, and receipt checks pass.

PASS authorizes only a separately preregistered 100-episode TRAIN-world
five-arm trajectory screen with a checkpoint at episode 100. It does not
authorize 500, 1500, 3000, or 9000 episodes.

FAIL produces `STOP_C3_B402_STRUCTURALLY`. It authorizes no state expansion,
loss adjustment, retry, seed replacement, pair/full-token model, or episode
training. A different route would require an explicit new user decision and
new independent evidence.
