# V0.23 LC-SRS observability and source-to-learner gate contract

Date: 2026-09-05  
Status: FROZEN PRE-OUTCOME METHOD CONTRACT / EXECUTION NO-GO  
Split: TRAIN development only. TEST is closed.

Promotion basis: `PASS_V023_METHOD_SPEC` after independent Astra Ultra and
structured-state reviews. The LC-SRS formula, deterministic-relational C3View,
learner, worlds, seeds, metrics, thresholds, and no-rescue rules are frozen.
Implementation and Section 17.1 tests remain required before a launch contract;
this document itself authorizes no simulation or training.

## 0. Question and hard boundary

This finite contract asks whether the two-user Local Coalition-Shapley Spatial
Residual Surplus (LC-SRS) can be observed from a deployable predecision state,
learned by a fixed student on unseen TRAIN worlds, and composed by the
unchanged one-pass Q1+Q2+Q3 deployment rule.

This is a gate design, not an efficacy result. It does not establish that C3,
C1, or C2 is qualified, or that FULL will beat every ablation.

Hard invariants:

1. Exactly three Q networks exist: Q1, Q2, and Q3.
2. Privileged physical evaluation, keyed fading outcomes, profile outcomes,
   and Shapley labels exist only in the training teacher.  The deterministic
   predecision relational-descriptor encoder is shared by training and inference;
   conditional on the already captured native predecision observation, it reads
   only committed state, native masks, candidate identities, and detached Q1+Q2
   reference scores and never chooses an action.  It draws no fresh randomness
   and never reads the teacher's matched profile fields.
3. Deployment is one native masked row-wise sum and one argmax:
   \[
   a_i^\star=\arg\max_{a\in{\cal A}_{i}^{\rm safe}}
   [Q_1(s_i,a)+Q_2(s_i,a)+Q_3(s_i,a)].
   \]
4. There is no coordinator, auction, vote, matching stage, joint decoder,
   iterative allocation, retry, fallback, or post-selection repair.
5. C2 remains a fixed, present, unqualified diagnostic; it is not retired or
   replaced.
6. This contract cannot authorize 100, 500, 1500, 3000, or 9000 episode
   training. Episode training requires a separate frozen contract.

All worlds, seeds, fields, features, metrics, thresholds, and stop rules are
frozen before an outcome is opened. Missing provenance is a gate failure.

## 1. Evidence basis and claim ceiling

This draft uses, read-only, the V0.22 result and verification, its mechanics
contract and formula source, deep-research-report.md, the
astra-adjudication-audit-bundle.zip, and
FABLE-51-V022-POSTGATE-ADJUDICATION-2026-09-05.md.

V0.22 supplied mechanics evidence only. Its first selected case was old TRAIN
world 2026121701, step 1, source key (62836,27), users 27 and 79, proposed
actions 20 and 2. It measured EE(00) 118.0067176 Mbit/J, EE(11)
118.1404140 Mbit/J, joint bits -3.1390865%, joint energy -3.2487015%,
source-beam removal without a newly opened destination, 100 served users, and
an identity residual about 9.5e-7 bit. These old worlds are not V0.23 inputs.

Expected-ZR is closed for the frozen V0.21 STOP_EXPECTED_ZR_FAST decision. This
contract does not increase K, reverse a sign, rescale, change a horizon, or
reopen that route.

LC-SRS is tested because a complete four-profile physical game can contain a
last-pair beam-extinction/shared-cost interaction that the old unilateral
zero-energy ZR label could not directly identify. A two-player identity is
exact only for its named current-slot game. It does not prove global
decentralized additivity, partial-adoption exactness, learned-Q exactness, or
population EE benefit.

The fixed thresholds below are an operational design basis from the Fable
eight-world leave-one-world-out recommendation and the Astra/deep-research
warnings about rare pivotal actions and world clustering. They are not
universal statistical constants and cannot be tuned after outcome.

## 2. Frozen authorities, worlds, seeds, and fields

### 2.1 Preflight bindings

Before any profile outcome, authenticate a SHA-256 preflight manifest for:

| binding | frozen object |
|---|---|
| multiplier | lambda = 0x1.c3c0a7b6b86d3p+26 = 118424222.8550065 bit/J |
| normalization | kappa = 0x1.2cea89d260f2ap+33 = 10097071012.757404 bit |
| Q1/Q2 background | V0.20 repriced lineage 2026092101, rung 003000, checkpoint SHA-256 d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc |
| formula | immutable V0.22 two-player formula source and hash |
| simulator | complete physical runtime/source closure and hashes |
| ephemeris | canonical TRAIN TLE set, file-set and receipt hashes |
| action | native safe mask, opening predicate, action order, lowest-index tie rule |
| field | V0.23 keyed common-field family and derivation manifest |
| learner | exact feature order, learner configuration, and config hash |

A result without the matching preflight manifest is invalid.

### 2.2 Fresh ordered worlds

Only these eight fresh ordered TRAIN worlds may be used:

| order | world |
|---:|---:|
| 1 | 2026121705 |
| 2 | 2026121706 |
| 3 | 2026121707 |
| 4 | 2026121708 |
| 5 | 2026121709 |
| 6 | 2026121710 |
| 7 | 2026121711 |
| 8 | 2026121712 |

The old V0.22 worlds 2026121701--2026121704 are explicitly excluded from
selection, fitting, validation, and gate arithmetic. World is the primary
physical cluster; student seeds are not independent worlds.

### 2.3 Student seeds

The only student seeds are 2026135101, 2026135102, and 2026135103. No seed
may be added, removed, replaced, or selected for performance.

### 2.4 Matched fading

For each retained pair/anchor use exactly 32 keyed fading draws.  One draw key
is a deterministic function of field family, world, anchor, draw index, and
the canonical physical-link identity used by the keyed-field runtime.  Pair
and profile are receipt metadata and MUST NOT enter the random-field key.
For a fixed world/anchor/draw, the same immutable common field is reused for
00, 10, 01, and 11, so a physical link that occurs in multiple profiles sees
the same variate.  For each draw, run the complete nonlinear physical
evaluator for all four profiles first and then compute the formula.  Never
average fading, SINR, rates, active sets, or outcomes before nonlinear
evaluation.  The draw count cannot change after a sign or variance is seen.

## 3. Deep module seam

The implementation must expose three byte-addressable interfaces.

### 3.1 Interface A: immutable deployable predecision state

Interface A is one row for each native `(user, action)` cell.  It is captured
immediately before any profile is evaluated and is immutable for the
four-profile comparison.  It separates two causal namespaces:

* **committed context** is the actual previous-slot association, load,
  radiating state, and power already available in the native observation; and
* **detached reference context** is the current-anchor hypothetical profile
  `x0 = argmax_masked(Q1+Q2)`, computed once from fixed inference-mode Q1/Q2.
  Its occupancies and action identities are descriptors, not committed state
  and not physical outcomes.

The versioned C3View has the exact structured layout

```text
action_context:   (U,28,29)     float32
tokens:           (U,28,U+1,38) float32
token_mask:       (U,28,U+1)    bool
action_mask:      (U,28)        bool
reference_actions:(U,)          int64
```

Token slots 0,...,U-1 are ordinary user-relation tokens. Slot U is exactly one
typed pair-context token for every legal cell. Q1 and Q2 retain their
authenticated 228-dimensional inputs; only Q3 consumes C3View and it still
returns one native `(U,28)` scalar surface.

Define `b(x)=x/(1+|x|)` and `b+(x)=x/(1+x)` for x>=0. Distances use
`d/(d+6371 km)`, angles use radians divided by pi, elevations use degrees
divided by 90, counts use division by U, beam counts use division by the fixed
number of cells, and powers use division by the configured beam-power maximum.
Detached Q1+Q2 values are already in their authenticated normalized unit and
use `tanh`; they are not divided by kappa again.  The exact action-context
order is:

| index | action-context field |
|---:|---|
| 1--3 | focal candidate off-axis angle, bounded slant range, elevation |
| 4 | focal opening feasibility |
| 5--10 | candidate/reference physical relation: same sat+cell; same sat/different cell same color; same sat/different cell different color; different sat/same cell; different sat/different cell same color; different sat/different cell different color |
| 11 | candidate equals the actual committed incumbent key |
| 12--15 | committed destination load, active beam, active satellite, RF power |
| 16--19 | committed context at the detached-reference source: load, active beam, active satellite, RF power |
| 20--23 | committed recurrence power, bounded current/start gain ratio, segment age, missing-incumbent flag |
| 24 | `tanh(Q12(a)-Q12(a_ref))` |
| 25 | descending legal-action Q12 rank divided by `max(1,L-1)`, top rank zero |
| 26--27 | detached source occupancy and opening-feasible served-load |
| 28--29 | detached destination occupancy and opening-feasible served-load |

An absent physical endpoint uses an all-zero physical-relation one-hot. Raw
NORAD, cell, world, anchor, user, action, and pair identifiers remain receipt
metadata and never enter the learner.

Every token has the following common 38-position layout. For an ordinary
user-relation token the fields are:

| index | ordinary-token field |
|---:|---|
| 1--2 | type `[1,0]` |
| 3--4 | victim-is-focal and victim-is-partner flags |
| 5--7 | victim reference key equals common source, focal destination, partner destination |
| 8 | victim reference opening feasibility |
| 9--10 | victim detached-reference occupancy and opening-feasible served-load |
| 11--13 | victim reference-beam geometry seen by that victim |
| 14--16 | common source-beam geometry seen by that victim |
| 17--19 | focal destination-beam geometry seen by that victim |
| 20--22 | partner destination-beam geometry seen by that victim, zero when unsupported |
| 23--25 | structural co-channel flags: source, focal destination, partner destination versus victim reference beam |
| 26--28 | exact same-physical-beam flags for the same three comparisons |
| 29 | focal-only reference-beam load change divided by U |
| 30 | two-member joint reference-beam load change divided by U, zero when unsupported |
| 31--33 | focal reference, focal candidate, and partner designated opening flags |
| 34--36 | `b+` of deterministic source, focal-destination, and partner-destination received coupling at the victim, each multiplied by segment-start power and divided by noise |
| 37 | `b+` of deterministic wanted-signal-to-noise at the victim reference |
| 38 | `tanh(Q12_v(a_ref)-mean_legal Q12_v)` |

These geometry/coupling descriptors are computed only from the captured
satellite positions, cell centers, user positions, colors, and fixed link
constants. They evaluate no rate, branch, active set, or hypothetical power.

For the pair-context token the same positions mean:

| index | pair-token field |
|---:|---|
| 1--2 | type `[0,1]` |
| 3--5 | source-occupancy-two, pair-supported, current-cell-is-designated flags |
| 6--7 | focal and partner designated opening flags |
| 8 | focal and partner destinations are the same physical key |
| 9--11 | source occupancy and nonmember occupancy at focal/partner destinations |
| 12--13 | opening-ready nonmember counts at focal/partner destinations |
| 14--16 | other committed active-beam fractions on source/focal-destination/partner-destination satellites |
| 17--19 | committed active-beam flags for source/focal destination/partner destination |
| 20--22 | committed RF power for those three beams |
| 23--25 | committed active-satellite flags for those three satellites |
| 26--28 | partner designated-action geometry from the partner view |
| 29--31 | partner destination geometry from the focal view |
| 32--36 | `tanh` of focal margin, partner margin, and partner legal-destination margin minimum, maximum, mean |
| 37--38 | `tanh` of focal and partner reference Q12 scores |

In both tables, a Q12 **margin** is exactly
`Q12(candidate)-Q12(reference)` in the authenticated normalized unit. The
partner minimum/maximum/mean are over its fixed legal opening destinations to
an occupied nonmember key. Section 7's nonnegative placebo `base gap` is the
explicit reverse quantity `Q12(reference)-Q12(candidate)`; the two names must
not be interchanged.

Under x0, a user has a unique partner iff its reference physical source key
has occupancy exactly two. For each member, the designated member action is
its highest detached-Q12 legal opening action to a different physical key
already occupied under x0 by at least one nonmember; ties use the lowest native
action index. `pair_supported` is true only when both members have designated
actions. For a supported pair, the ordinary relation set for every member cell
is the union of users whose x0 reference beam is the common source, focal
destination, partner destination, or structurally co-channel with any of those
three beams, plus both pair members. For an unsupported cell it uses the focal
source/focal-candidate union and the focal user. No realised served/outcome
filter enters this mask. Thus the relation set covers heterogeneous nonfocal
effects and the two members needed to represent the joint residual.

`token_mask[...,0:U]` is this deterministic relation mask and
`token_mask[...,U]` equals the native action mask. Illegal action rows and all
their tokens are exactly zero. A no-partner pair token retains only type
`[0,1]` and status `(0,0,0)`; occupancy-two but unsupported retains type and
status `(1,0,0)`; supported rows carry the declared partner fields and mark the
designated cell separately. Missing ordinary references are masked and zero.
Missing committed incumbents use temporal `(0,0,0,1)` and zero committed
relation/power fields. No NaN or infinity sentinel is allowed.

The immutable capture seam supplies native masks and physical keys, candidate
and cross-user geometry, opening feasibility, committed context, the color
map, and detached Q12/reference actions. Cross-user geometry is derived once
from captured satellite positions, cell centers, and user positions before the
teacher runs. The encoder cannot query the live environment or RNG after this
capture. It creates features only; it is not a coordinator, matcher, decoder,
or action-selection stage.

Units, normalization, missing values, feature order, and schema hash are
frozen. No fold-fitted normalization is needed for the already bounded C3View.
World, anchor, and row identifiers are provenance metadata only.

Interface A must not directly contain or derive a new feature from delivered
bits, rates, energy, served status, outage, post-action active sets or power,
profile outcomes, teacher fading/shadowing fields, fresh encoder random draws,
labels, future returns, future actions, future associations, future load/power,
future policy queries, or post-hoc selection flags.  The one explicit ancestry
exception is authenticated detached Q1+Q2 output from the already captured
native predecision observation: the frozen Q1/Q2 checkpoint consumes the native
observation-time SINR block, which may contain its ordinary observation draw.
Detachment removes gradients but not that ancestry.  The encoder may use only
the detached scores/margins/ranks, never the raw observed SINR as a C3 token,
never redraw the native observation, and never substitute a deterministic Q1/Q2
input.  The native observation RNG/event digest is captured before Interface A
and must be identical across source generation and deployment replay.

Every occupancy/load/power field is explicitly tagged as committed context or
detached-reference combinatorial context; detached-reference fields may use
action identities and counts but may not contain a hypothetical profile's
physical rate, energy, active set, or power.

### 3.2 Interface B: teacher/source

Interface B accepts immutable Interface-A state, its predeclared two-member
descriptor, and the keyed field manifest. It may access full simulator/fading
and profile outcomes only to produce a teacher record. It returns pair
identity, 00/10/01/11 vectors, per-draw and aggregate physical receipts, exact
formula terms, normalized member targets, and provenance hashes.  An
anchor-level assembler, defined in Section 5, merges all disjoint pair records
into one unique target surface.  Privileged values never enter Interface A or
the learner input.

Interface B must reject any topology whose member count is not exactly two
before profile evaluation. In particular, it must not generalize the residual
share to Psi divided by the coalition size, and it must not claim a general
m-player Shapley implementation. The V0.23 seam is intentionally a strict
two-member interface even if an inherited V0.22 formula helper accepts a
broader input shape.

### 3.3 Interface C: one learner output surface

The only learned C3 output is the scalar surface Q3(s_i,a_i). It has no opaque
pair identifier, coalition decoder, allocation vector, profile selector, or
second C3 head.  It may read the frozen detached Q1+Q2 descriptors in
Interface A, but those values are inference-only inputs and carry no gradient
into Q1 or Q2.

The fixed gate learner uses one shared token scorer for ordinary and pair
tokens:
\[
f_\theta:[c_{ia},t_{iar}]\in\mathbb R^{67}
\longrightarrow 64_{\rm ReLU}\longrightarrow64_{\rm ReLU}
\longrightarrow1,
\]
\[
F_i(a)=\sum_{r:\,m_{iar}=1}f_\theta(c_{ia},t_{iar}),
\qquad
Q_{3,i}(a)=F_i(a)-F_i(a_i^{\rm ref}).
\]
The scorer emits the normalized bits-per-kappa unit directly; the target is
divided by kappa exactly once at source assembly and the head performs no
second division.  Illegal outputs are zeroed by the native mask. There is no
positive-credit input, sign clamp, supported-action output clamp, separately
supervised e/Psi head, dropout, batch normalization, target network, Bellman
bootstrap, or trainable cross-route path. Internal token contributions are
latent; the only public result is the single scalar Q3 surface.

The scorer uses Adam with learning rate 1e-3, beta values (0.9,0.999), epsilon
1e-8, zero weight decay, batch size 256 and exactly 2000 optimizer updates.
For each retained anchor h let
S_h be the unique designated supported cells, R_h the unique x0 reference
cell of every native user, and C_h all remaining unique legal nonreference
cells after supported cells are removed.
Masked cells are receipt-only.  Each anchor and each class has fixed unit
weight:
\[
L_3=
\operatorname{mean}_{h}\left\{
\operatorname{mean}_{r\in S_h}[Q_3(r)-\bar y_r]^2+
\operatorname{mean}_{r\in R_h}Q_3(r)^2+
\operatorname{mean}_{r\in C_h}Q_3(r)^2
\right\}.
\]
Reference centering makes every R prediction exactly zero; R is nevertheless
retained as a structural integrity class and any nonzero reference output is
an implementation failure. Each unique cell occurs once in its class, so
neither 32 fading draws nor the number of legal cells or pairs at an anchor
silently changes that anchor's weight. Each 256-row optimizer batch is drawn
with replacement by the frozen student RNG: choose a retained fitting anchor
uniformly, choose S/R/C uniformly, then choose a row uniformly within that
anchor/class. Multiply each sampled squared error by three, making this an
unbiased estimator of the displayed sum of three class means. An R draw has
an exact zero loss and gradient. Empty classes are an integrity failure rather
than a renormalization.
INFORMED and MATCHED-PLACEBO use the identical row universe and weights; no
sign, inverse-variance, pair-count, or outcome-dependent weighting is allowed.
Initialization uses
exactly one of the three declared student seeds per fold/seed receipt. There is no early
stopping, architecture search, best-checkpoint selection, or
outcome-dependent rescaling. The serialized config and initial parameter
digest must be in preflight.

### 3.4 Detached reference and gradient boundary

At each anchor, the fixed sequence is:

1. capture the committed causal context and construct native current masks;
2. evaluate Q1 and Q2 in inference mode;
3. detach both and compute x0 by native row-wise argmax of Q1+Q2;
4. build the deterministic detached-reference descriptors and freeze
   Interface-A features;
5. enumerate the disjoint supported pairs without profile outcomes;
6. generate teacher rows; and
7. fit/evaluate Q3 from Interface-A rows only.

At deployment the same sequence stops after Step 5, evaluates Q3 once on the
frozen rows, and applies the single masked Q1+Q2+Q3 argmax.  Q1/Q2 are never
recomputed after labels, profiles, fading, or Q3. Q3 loss cannot update Q1,
Q2, masks, topology, or simulator. There is no cross-route gradient.

## 4. Outcome-blind topology enumeration

For each fresh world, follow frozen Q1+Q2 from the initial anchor. At every
noninitial native anchor t = 1,...,9:

1. compute native masks, opening feasibility, detached Q1/Q2, and x0;
2. map reference actions to physical satellite/cell keys;
3. enumerate every source key with exactly two reference users;
4. retain it only if both member opening predicates are true pre-outcome;
5. enumerate legal member actions to a different key already occupied by at
   least one reference user outside the pair;
6. choose each member's highest Q1+Q2 destination in that fixed set, ties by
   lowest native action index; and
7. serialize all pairs in world, anchor, source-key, and user-id order.

An anchor is retained for fitting only when this outcome-blind enumeration
produces at least one closure-eligible pair and leaves nonempty S, R, and C
classes under the unique anchor-level surface.  This retention decision is made
and hashed before any profile evaluation.  An anchor without those three
classes is an enumerated coverage receipt, not a fitting anchor; it is never
rescued by an observed sign or target.

No bits, energy, service, fading, label, Q3, post-action set, or observed EE
enters selection. A **closure-eligible pair** has detached-reference source
occupancy two and two designated feasible moves to occupied destinations.
Because x0 assigns each user to one reference source, closure-eligible pairs
at one anchor are disjoint.  A user/cell collision or duplicate supported-cell
assignment is an integrity failure, not a merge heuristic.

For a no-close control, use detached-reference source occupancy exactly three, select the first
two users in user-id order, and apply the same destination rule; the third
reference user remains on the source by construction. Enumerate all positive
pairs and no-close controls. Do not keep only the best observed pair.

If fewer than 24 closure-eligible pairs are enumerated before physical
evaluation, or any fresh world has zero closure-eligible pair, emit
INSUFFICIENT_PAIRS.  No pair is removed because its measured target or EE
contrast is negative.

## 5. Exact V0.22 two-player LC-SRS teacher

For every matched fading draw let B_v(x) be delivered bits for user v and
E(x) total current-interval network energy:
\[
G(x)=\sum_v B_v(x)-\lambda E(x).
\]
Set x0=00, x1=10, x2=01, and x12=11. For ordered members i=1,2:
\[
\begin{aligned}
\ell_i&=B_i(x_i)-B_i(x_0)-\lambda[E(x_i)-E(x_0)],\\
e_i&=\sum_{v\ne i}[B_v(x_i)-B_v(x_0)],\\
d_i&=\ell_i+e_i,\\
\Psi_B&=[\sum_vB_v(x_{12})-\sum_vB_v(x_0)]
-\sum_{i=1}^{2}[\sum_vB_v(x_i)-\sum_vB_v(x_0)],\\
\Psi_E&=[E(x_{12})-E(x_0)]
-\sum_{i=1}^{2}[E(x_i)-E(x_0)],\\
\Psi&=\Psi_B-\lambda\Psi_E,\\
z_{3,i}&=e_i+\Psi/2,\qquad y_i=z_{3,i}/\kappa.
\end{aligned}
\]
The required identity is:
\[
\sum_{i=1}^{2}[\ell_i+z_{3,i}]=G(x_{12})-G(x_0).
\]

This identity is exact only for the named two-member current-slot game. It is
not a general coalition, partial-adoption, all-roster, future-trajectory, or
learned-policy decomposition.

The runner must fail closed for m != 2. There is no Psi/|C| fallback and no
alternative m-player attribution in this contract.

The formula is evaluated separately after every one of the 32 complete
four-profile draws.  The sole learner label for member cell r is the arithmetic
mean
\[
\bar y_r={1\over32}\sum_{d=1}^{32} y_r^{(d)}.
\]
The 32 values and their mean are serialized, but they are not expanded into
32 learner rows.

There is exactly one anchor-level teacher surface.  Initialize every cell to
zero, mark the x0 cells as REFERENCE, the remaining legal cells as CONTROL,
and illegal cells as MASKED.  Then write each pair's two averaged labels only
to its two unique designated member cells and mark them SUPPORTED.  A second
write to any cell invalidates the anchor.  Thus a supported cell is never
reintroduced as a nonmember zero by another pair.  Pair-specific full-roster
zero surfaces do not exist.  Zero-fill is not a sign filter: measured positive,
negative, and zero supported targets remain in S.  MASKED cells are stored and
checked but do not enter the learner loss.

Retain bits and energy separately. Ratio-of-sums EE
\[
\eta(x)=\frac{\sum_vB_v(x)}{E(x)}
\]
is an evaluation diagnostic, not a target redefinition. The fixed sign check is
\(\eta(x_{12})>\eta(x_0)\) iff
\(\Delta B-\eta(x_0)\Delta E>0\), up to recorded floating-point tolerance.
Never replace lambda with a post-outcome price.

## 6. Profiles, controls, and negative rows

Evaluate these exact profiles for every pair and matched draw:

| profile | action change |
|---|---|
| 00 | both members retain x0 |
| 10 | member 1 moves; member 2 retains x0 |
| 01 | member 2 moves; member 1 retains x0 |
| 11 | both members move |

No other user changes in pair-local profiles. Record action hash, per-user and
total bits, energy components, service, active beams/satellites, RF powers,
EE, G, and before/after live-state, network, and RNG digests.

Controls are:

1. unique exact-zero reference rows in R;
2. unique exact-zero legal unsupported rows in C;
3. masked/illegal zero receipts, excluded from fitting;
4. retained partial profiles 10 and 01, used in the teacher identity and
   physical diagnostics but not as separate learner rows;
5. source-occupancy-three no-close physical controls, stored as diagnostics
   and never merged into the closure-eligible teacher surface;
6. matched-support action-identity placebo;
7. equal-budget neutral-source replacement; and
8. privileged sparse teacher surface, diagnostic only.

No negative row is manufactured by sign flipping. Reference and legal-control
zeros are exact source controls. No-close is a negative topology control for
the closure mechanism because the source remains occupied, not because a
measured physical target is forced negative. Informed and neutral source arms
have the same S/R/C cells, seeds, class-balanced loss, model, updates, and
three-network slots. A neutral source is retrained, not edited post hoc.

## 7. Matched-placebo strata

For each SUPPORTED member cell, the exact predecision stratum is:
\[
z(a)=\{\text{world},\text{phase},\text{legal/opening},
\text{detached destination occupancy},
\text{committed destination active},\text{base gap}\}.
\]

Fixed categories are:

* phase t=1--3, 4--6, or 7--9;
* world = the row's own TRAIN world, so no permutation crosses a world;
* legal/opening = legal-and-opening for every eligible member row;
* detached-reference destination occupancy = 1 or 2+ nonmember users;
* committed-context destination active = inactive or active; and
* base gap is
  `Q12(s,a_ref)-Q12(s,a)`, clipped to exact zero only within the frozen
  floating-point tie tolerance, and binned as [0,0.01), [0.01,0.05),
  [0.05,0.20), or >=0.20 in the authenticated Q1+Q2 unit.

Only a stratum with at least two SUPPORTED cells is permuted.  Sort its cells
by `(world, anchor, user, action)` and apply one deterministic nonzero cyclic
shift keyed only by the frozen placebo key and stratum.  Move only the
aggregated target values among those fixed feature/action rows.  Feature
vectors, masks, identities, row classes, weights, R/C zeros, and sample counts
remain fixed.  This preserves the within-stratum target histogram while
breaking its action-specific association.  Single-cell strata are
placebo-ineligible.

For fold w, the placebo training source is constructed solely within each of
the seven fitting worlds.  No target, transform, permutation, or statistic
from held-out world w enters fitting.  Both learners are evaluated against the
unchanged true labels of w; held-out labels are never permuted.  All three
student seeds use the same frozen fold-specific source.  At least 80% of
SUPPORTED training rows in every fold must be placebo-eligible.  Generic
destination-activity or base-gap propensity therefore cannot by itself count
as action-specific LC-SRS evidence.

## 8. Teacher rows, LOO splits, and source learner

For every retained anchor, materialize the one unique S/R/C surface from
Section 5 plus MASKED receipts.  No-close and partial-profile records remain
separate diagnostic tables.  Every row retains class, pair id when supported,
profile hashes, target hash, state-schema hash, and world/anchor provenance.
Never remove a supported row because its target, joint surplus, or EE contrast
is negative.

There are exactly eight leave-one-world-out folds. Fold w fits on the other
seven worlds and evaluates only on w. C3View has no data-fitted feature
normalization; any reported learner statistic uses only the seven fitting
worlds and cannot alter the fixed transforms. Each fold uses all three frozen
student seeds, producing 24 fold/seed bundles and eight physical clusters.
Every bundle contains two separately initialized and fitted models, INFORMED
and MATCHED-PLACEBO, so the gate fits exactly 48 models. ZERO-SURFACE and
TEACHER-ORACLE are deterministic diagnostics and are not additional fitted
models.

The source panel is:

| arm | meaning |
|---|---|
| INFORMED | LC-SRS rows and exact controls |
| MATCHED-PLACEBO | same S/R/C rows; training-world S targets cyclically permuted within frozen strata |
| ZERO-SURFACE | Q3 fixed to zero, equivalent to Q1+Q2 for composition |
| TEACHER-ORACLE | privileged sparse formula surface, diagnostic only |

Primary evidence is INFORMED versus MATCHED-PLACEBO under equal budgets,
evaluated on unchanged true held-out targets. ZERO-SURFACE and TEACHER-ORACLE
are diagnostics, not episode-policy comparators.

A source ablation replaces informed rows with equal-budget neutral rows and
re-trains Q3 while retaining all three networks and update opportunities. A
post-hoc head drop sets a trained contribution to zero at composition time.
They answer different questions. Later FULL/DROP-C1/DROP-C2/DROP-C3 efficacy
claims require retrained source ablations under a new contract.

## 9. Independent C1 and C2 context diagnostics

These diagnostics guard the fixed background used to interpret composition;
they do not redefine the C3 physics or learner result.  The result therefore
contains one primary `c3_decision` from Section 14 and one independent
`context_status`.  A C1/C2 diagnostic failure blocks any later episode-run
contract, but it cannot turn a passed or failed C3 observability test into a
different C3 result.

### 9.1 C1 oracle-l versus Q1 calibration

For each retained positive member compare:
\[
\ell_i/\kappa
\quad\text{with}\quad
\Delta Q_{1,i}=Q_1(s_i,a_i)-Q_1(s_i,a_i^{\rm ref}).
\]
Report finite/mask validity, tie-aware Spearman correlation, sign agreement
where |\ell_i/\kappa| >= 0.02, zero crossings, a fixed no-intercept slope,
and closure-eligible/no-close splits. The slope is diagnostic only; no
rescaling is used.

The fixed C1 diagnostic threshold is Spearman >=0.20 and sign agreement
>=0.55 on >=24 nontrivial member rows. Failure sets the C1 component of
`context_status` to HOLD.  It does not permit a new lambda, rescaling,
relabel, or C1 formula against this outcome.

### 9.2 C2 fixed diagnostic

C2 remains the current OPS-3 implementation and checkpoint context. It is not
redesigned or retired. For the same actions report detached Q2 deltas/margins,
Q1-to-Q1+Q2 argmax changes, exposure by transition class, the fraction with
|Delta Q2| >= 0.02 in its native unit, and, when authenticated, sign/rank
comparison to its OPS-3 target. Verify opening feasibility, absorbing
persistence, terminal zero, frozen-background semantics, masks, and
target-free inference.  A sign/rank comparison to an OPS-3 target is valid
only when the target formula, multiplier, horizon, and checkpoint lineage are
authenticated as the source of this Q2; a runtime default from a different
multiplier is reported as a provenance mismatch and is not silently used.

Minimum Q2 exposure is 0.10 of retained member rows, plus finite,
provenance, mask, timing, and target-free checks. Failure sets the C2
component of `context_status` to HOLD. Passing leaves C2 an unqualified
diagnostic and does not upgrade it. No older C2 oracle improvement, source-fit
score, or Q2+Q3 agreement substitutes for these diagnostics.

The serialized context status is exactly one of
`CONTEXT_DIAGNOSTICS_PASS`, `HOLD_C1`, `HOLD_C2`, or `HOLD_C1_C2`.

## 10. Physical mechanics and service

For every closure-eligible pair and all 32 draws require:

1. profile action vectors match 00/10/01/11;
2. 00, 10, and 01 retain the source beam;
3. 11 removes exactly the source beam and opens no new destination beam;
4. both members are served in all profiles and served users in 11 are not
   below 00;
5. all values are finite;
6. the identity residual is at most
   1e-12 times one plus the sum of absolute identity terms;
7. the exact ratio sign identity uses the local price eta(00):
   `sign(eta(11)-eta(00)) = sign(Delta B-eta(00) Delta E)` within the frozen
   numerical tolerance; the separately recorded fixed-lambda surplus is not
   required to have that sign; and
8. the common-field digest is identical for all four profiles and the
   environment, Q1/Q2 parameters, and RNG digests are unchanged.

For no-close controls, replace source removal with the predeclared nonclosure
invariant: a source user remains and the source is not removed solely by the
two moves.

If fewer than 90% of enumerated closure-eligible pairs pass all mechanics, emit
STOP_PHYSICS. If pair coverage is insufficient first, emit
INSUFFICIENT_PAIRS.

For the fixed physical exposure threshold, the eight-world pooled
ratio-of-sums 11-versus-00 EE contrast must be positive and at least four of
eight world-level pooled contrasts must be positive.  The pool includes every
enumerated closure-eligible pair and every draw; no sign filter is allowed.
There is deliberately no requirement that a majority of individual pairs be
positive, because negative pair examples are valid avoidance evidence.
Partial profiles need not be positive; their signs are retained.

For each held-out current-slot composition arm report ratio-of-sums EE, total
bits, total energy, served fraction, user-rate lower tail, active-beam count,
and collateral actions.  Do not report these independent anchors as future
outage duration or a trajectory metric.  The fixed service margin is
delta_S=0.01 absolute served fraction versus matched B=Q1+Q2:
\[
S_{\rm I,w}\ge S_{\rm B,w}-0.01
\]
for every world, where I is the one-pass INFORMED learner arm.  Lower-tail
metrics remain secondary safety receipts and do not form a new objective.

## 11. Literal composition and post-selection topology check

Construct the complete Interface-A row surface from frozen x0, evaluate Q3
once, and apply one native masked argmax of Q1+Q2+Q3. For each enumerated pair
classify its two selected member actions as 00, 10, 01, 11, or OTHER. Hold
nonmembers at x0 only for pair-local measurement; separately evaluate the
same one-pass argmax over the full roster and report collateral changes.
Neither path performs a second decision or coordination.

After literal full-roster selection, rebuild topology facts for measurement
only; do not reevaluate Q3 and do not run a second argmax.  For every selected
11, `topology_consistent` means the reference source is empty under the fixed
selected vector and each designated destination remains occupied by at least
one **nonmember of that pair** after all simultaneous selections.  The incoming
member cannot satisfy this persistence condition by itself. Source occupancy changing from
two to zero is the intended mechanism and is never counted as descriptor
disagreement.  Report the topology-consistent fraction over selected 11,
harmful partial-adoption fraction, collateral action rate, bits, energy, and
service.  This is a post-selection measurement, not an iterative repair.

## 12. Fixed gate thresholds

For reported floating comparisons define
\[
\tau(x,y)=\max\{10^{-12},1024\epsilon_{64}\max(1,|x|,|y|)\}.
\]
`x` is strictly above `y` only when `x-y > tau(x,y)`; absolute differences at
or below tau are ties and are counted separately.  Ratio-of-sums EE direction
is decided by the cross product `B_1 E_0 - B_0 E_1` with the corresponding
scale-aware tolerance, not by subtracting two rounded ratios.  These reporting
tolerances never change native action selection: masked argmax uses the exact
stored score order and the lowest native action index only for exact ties.

For a held-out SUPPORTED row r, define the policy-relevant prediction
\[
\widehat y_r=Q_3(s_r,a_r)-Q_3(s_r,a_r^{\rm ref}).
\]
INFORMED and MATCHED-PLACEBO metrics always compare their separately fitted
predictions with the same unchanged true held-out `bar y_r`.  Spearman uses
midranks for ties.  A constant vector, fewer than two rows, or a nonfinite
correlation is a failed predicate.  Sign accuracy uses only rows with
`|bar y_r| >= 0.02`, maps strictly positive/negative values to +1/-1, and
reports all excluded zeros and denominators.  The pooled learner metrics stack
each world's held-out rows exactly once for a student seed and then average
the three seed metrics.  World metrics are computed within a held-out world
and averaged over the three seeds; a tie is not an INFORMED win.

For every composition and service predicate, first pool complete matched
bits/energy/service receipts separately for each of the three student seeds.
The reported arm value is the arithmetic mean of the three seed-level values;
an arm is directionally above its comparator only when the mean is strictly
above under the frozen tolerance.  A world direction is computed the same way:
one complete ratio-of-sums per seed in that world, followed by the arithmetic
mean across the three declared seeds.  All individual seed values and ties are
serialized; seeds are never treated as independent physical worlds.

For composition, percentages use the full set of enumerated closure-eligible
pairs as denominator except `topology_consistent`, whose denominator is exactly
the selected-11 pairs and is reported with its count. If that count is zero,
the topology fraction is reported as NA and its predicate is false. `action_change` means at least one
member differs from x0.  `literal_11` means both members choose their two
designated actions.  `harmful_partial` means the selected pair-local profile
is 10 or 01 and its 32-draw ratio-of-sums EE is below 00; OTHER is serialized
separately and is not silently classified as a partial.  A world-level EE
direction is the ratio of summed bits to summed energy over its complete
matched current-slot receipt, never a mean of per-row EE values.

All C3 conditions below are required for
GO_FIXED_LEARNER_SCREEN_CONTRACT:

| area | fixed condition |
|---|---|
| pair coverage | >=24 closure-eligible pairs, >=1 in each world, and >=80% of SUPPORTED training rows placebo-eligible in every fold |
| mechanics | >=90% of closure-eligible pairs pass all per-draw checks; no unresolved formula, common-field, mask, or mutation error |
| physical signature | eight-world pooled 11-versus-00 ratio-of-sums EE positive and >=4/8 world directions positive |
| target support | >=24 SUPPORTED held-out rows with `|bar y| >= 0.02` after each row appears exactly once |
| held-out learner | informed Spearman >=0.20, sign accuracy >=0.60, informed-minus-placebo sign accuracy >=0.05 |
| world stability | mean-seed informed Spearman strictly exceeds placebo in >=6/8 held-out worlds; each informed seed has nonnegative Spearman in >=5/8 worlds |
| action exposure | INFORMED action_change in >=10% of closure-eligible pairs |
| pair composition | INFORMED literal_11 in >=25% of closure-eligible pairs and in >=4/8 worlds; harmful_partial <=5% of all closure-eligible pairs |
| topology consistency | >=80% of INFORMED selected-11 pairs meet the post-selection source/destination condition from Section 11 |
| teacher composition | one-pass TEACHER-ORACLE full-roster EE exceeds B pooled and in >=4/8 worlds |
| learned composition | one-pass INFORMED full-roster EE exceeds B pooled and in >=4/8 worlds |
| service | every world meets `S_I,w >= S_B,w - 0.01` |

Every rank/sign denominator, tie, missing row, world, and seed value is
serialized. Thresholds are predicates, not a search space.  The independent
C1/C2 `context_status` is reported beside this table but is not substituted
for any C3 predicate.  Even when the C3 decision is GO, a HOLD context status
prevents any later episode-run contract until separately resolved.

## 13. Immutable outputs and verification

One immutable result directory must contain:

1. contract copy and hash;
2. preflight manifest and all binding hashes;
3. complete world/anchor/pair/control enumeration, including exclusions;
4. Interface-A schema, order, units, and normalization manifest;
5. raw per-draw teacher rows and target hashes;
6. 00/10/01/11 receipts with physical and mutation digests;
7. zero, partial, no-close, and placebo receipts;
8. placebo permutation map and stratum coverage;
9. C1/C2 diagnostic receipts;
10. all 24 LOO fold/seed bundles and their 48 INFORMED/placebo model receipts;
11. literal composition and post-selection topology-consistency metrics;
12. held-out world service and ratio-of-sums metrics;
13. canonical sorted-key result.json;
14. independently recomputed verification.json; and
15. SHA-256 MANIFEST.sha256 over every result file.

The canonical result includes `c3_decision`, `context_status`,
contract/preflight hashes, all
thresholds and design-basis labels, all denominators, world/seed metrics,
physical/source/learner/composition/service/leakage checks, claim ceiling, and
no-rescue statement. Verification recomputes profile totals, formula identity,
zero-fill, permutation membership, LOO membership, seed list, action
selection, service guards, and decision predicates without trusting booleans.

Any hash mismatch, omitted denominator, missing world, undeclared filter, or
unrecomputable decision yields `INVALID_RUN` before a scientific token exists.
It cannot be repaired by editing the result or rerunning one failed world.

## 14. Hard decisions and precedence

Exactly one primary C3 scientific token is emitted only after all integrity
checks pass.  `context_status` is serialized separately and does not alter the
primary token.

### INSUFFICIENT_PAIRS

Use if fewer than 24 closure-eligible pairs are enumerated before outcome, any
world has none, or fold-level SUPPORTED placebo coverage is below 80%. This is
insufficient exposure, not a proof that LC-SRS is impossible.

### STOP_PHYSICS

Use if coverage is sufficient but four-profile mechanics, common-field use,
source-beam signature, service mechanics, formula identity, mutation checks,
the fixed physical signature, or TEACHER-ORACLE composition fails. No lambda,
kappa, horizon, sign, or target rescue is allowed.

### STOP_OBSERVABILITY

Use if physical mechanics pass but Interface A is leaky/insufficient, target
support is insufficient, the informed learner is not better than placebo, or
held-out rank/sign/world-stability thresholds fail.

### REDESIGN_INTERFACE

Use if the physical teacher and placebo-separated held-out learner signal pass
but action exposure, literal 11 adoption, harmful-partial, post-selection
topology, learned current-slot EE, or service composition fails. This
authorizes only a new pre-outcome state/topology-interface design; never a
coordinator, joint decoder, iterative repair, or episode run.

### GO_FIXED_LEARNER_SCREEN_CONTRACT

Use only when every fixed C3 condition in Section 12 passes. It authorizes
drafting and freezing one separate learner-screen contract. It does not
authorize episode training or claim C1/C2/C3/EE efficacy.  If
`context_status` is not `CONTEXT_DIAGNOSTICS_PASS`, the C3 result remains GO
but no episode contract may launch until the context hold is separately
resolved.

Precedence is deterministic: `INVALID_RUN` before scientific adjudication;
then INSUFFICIENT_PAIRS, STOP_PHYSICS, STOP_OBSERVABILITY,
REDESIGN_INTERFACE, and finally GO_FIXED_LEARNER_SCREEN_CONTRACT. Serialize
every predicate, including predicates after the first failure, so the token is
independently recomputable.  Independently compute the Section-9 context
status after authenticated Q1/Q2 checks; missing authentication is an
integrity failure, while a valid but weak diagnostic produces a HOLD status.

## 15. No rescue ladder

After outcome opening, do not change worlds, return to 2026121701--1704,
add/replace seeds, change 32 draws, lambda, kappa, formula, profiles,
topology, anchors, tie rule, destination rule, placebo strata, permutation,
feature order, architecture, optimizer, update count, service margin,
threshold, or source weights.

Do not discard negative, partial, no-close, placebo, or inconvenient rows; use
post-action information in Interface A; choose the best seed/world/fold/
checkpoint; or replace one-pass argmax with a joint mechanism.

An infrastructure or hash failure before a complete outcome is an invalid run,
not a scientific result. A new attempt requires a new pre-outcome contract and
hash.

## 16. Future execution class and Ubuntu server recommendation

The V0.23 scan plus 48 leave-one-world-out student fits is **heavy CPU work**,
estimated at approximately **3--5 hours wall time**. Run it on the Ubuntu
server, not the current WSL/browser environment.

After the implementation gate passes and a separate launch contract is frozen:

1. SSH to the server with ssh sat.
2. Sync the exact repository revision, contract, authenticated artifacts,
   runtime, checkpoint, and TLE archive.
3. Confirm Python environment, dependencies, CPU/RAM, and every preflight hash.
4. Open a Codex worker on the server and paste the frozen launch prompt.
5. Run only preflight and this V0.23 gate in tmux with append-only logs;
   confirm TEST and episode-training commands are unreachable.
6. Preserve raw receipts, verification, and manifest; never hand-edit a
   returned summary.

This is routing guidance, not launch authorization.

## 17. Promotion completion criterion

An independent reviewer must be able to verify before outcome:

* every input, world, seed, field, anchor, action, profile, feature, and
  normalization rule;
* the Interface-A boundary, including the declared detached-Q12 ancestry, and
  absence of direct observed-SINR tokens, fresh encoder draws, teacher/profile
  fading, outcomes, labels, and future actions;
* the V0.22 formula and identity for every V0.23 profile;
* equal-budget INFORMED versus MATCHED-PLACEBO fitting in this gate, plus the
  separately declared neutral-source replacement semantics for later ablation;
* source ablation versus post-hoc head drop;
* every negative, partial, no-close, and placebo row;
* every LOO fold and all three student seeds;
* C1 l-versus-Q1 and C2 target-free contribution/adoption diagnostics;
* literal one-pass composition and post-selection topology checks without
  coordination;
* every physical, learner, placebo, composition, service, leakage, and
  integrity predicate;
* exactly one hard decision with no rescue ladder; and
* no route to 100/500/1500/3000/9000 episode training.

If any item is not checkable, this frozen method remains execution-NO-GO and
no run is authorized. If all are checkable, launch still requires a fresh
preflight hash and a separate explicit launch decision.

### 17.1 Minimum pre-outcome interface tests

Before method-core freeze, the implementation suite must prove:

1. identical captured inputs produce a bit-identical immutable C3View without
   an RNG or post-capture environment call;
2. changing live RNG state or raw `candidate_sinr` while holding authenticated
   detached Q12 fixed leaves C3View unchanged;
3. no outcome, rate, energy, post-action active/power state, profile fading,
   label, or future field is accepted by Interface A;
4. physical-key relations survive native action-slot permutation and raw IDs
   are absent from numeric features;
5. opening flags equal the pure predecision opening predicate;
6. ordinary relation masks cover focal/partner roles and the source/focal-
   destination/partner-destination exact-key and co-channel union;
7. occupancy 0/1/2/3, partner identity, destination, tie, disjointness, and
   unsupported-sentinel rules are exact;
8. every legal cell has exactly one pair token; illegal and unmasked token
   slots obey their declared zero rules;
9. permuting ordinary-token order leaves the aggregate score unchanged;
10. reference centering is exact and illegal Q3 outputs are zero;
11. positive and negative token contributions both survive, with no inherited
    compatibility/sign gate;
12. Q3 loss sends no gradient to Q1/Q2 or the captured state;
13. the checkpoint contains exactly Q1(228), Q2(228), and one structured Q3,
    with three optimizers and authenticated schema/config hashes;
14. deployment performs one Q1+Q2+Q3 sum and one native masked argmax; and
15. two fixtures with equal aggregate occupancy but different victim geometry
    produce different ordinary relational tokens.

## 18. Paper-method freeze boundary

The candidate Chapter-4 method core may be frozen after this contract is
promoted and the shared descriptor, exactly-two-member wrapper,
anchor-surface assembler, common-field, placebo-isolation, loss, and one-pass
argmax interfaces pass implementation tests.  That freeze does not require
opening the 3--5 hour V0.23 outcome.  Its paper-visible core is limited to:

1. one final Main-only ratio-of-sums EE objective;
2. the exact two-player current-slot game and
   `z3_i = e_i + Psi/2` residual label;
3. a training-only four-profile teacher with common random numbers;
4. the deterministic relational C3View, shared token scorer, reference-
   centred scalar Q3 learner; and
5. the unchanged single masked Q1+Q2+Q3 argmax.

Hashes, seeds, optimizer details, placebo bins, decision tokens, receipt
schemas, and server routing belong in implementation or experimental
appendices, not the main algorithm narrative.

The empirical claims do require the V0.23 outcome.  STOP_PHYSICS reopens the
C3 source/mechanism claim; STOP_OBSERVABILITY retains the exact scoped formula
but reopens the state/learner subsection; REDESIGN_INTERFACE retains the
formula and learner signal but reopens composition descriptors; GO permits a
fully fixed C3 implementation subsection.  None of these outcomes alone fills
Chapter 5 or proves FULL exceeds every ablation.

## 19. Frozen method status

FROZEN METHOD DECISION: retain LC-SRS as the sole live C3 candidate for this bounded
observability question; preserve the V0.22 exact two-player formula; use only
worlds 2026121705--2026121712 and student seeds 2026135101--2026135103; hold
C1/C2 qualification open as diagnostics; and do not begin episode training.

CLAIM CEILING: this contract defines a falsifiable source/observability gate.
It does not establish three positive Catfish mechanisms, FULL greater than
every ablation, or successful deployment EE.
