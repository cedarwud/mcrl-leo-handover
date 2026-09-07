# Multi-Catfish MCRL V0.6 clean C2-k1 T1 preregistration

Date: 2026-09-01  
Status: `PREOUTCOME_FROZEN_AUTHORIZED_FOR_TARGET_FREE_PREPARE`  
Claim ceiling: `TRAIN_DESIGN_FALSIFICATION_ONLY_NO_LEARNING_NO_TEST_NO_EE_EFFICACY`

## Material Passport

- Origin skill: `academic-research-suite / experiment-agent`
- Origin mode: `plan`
- Verification status: `LOCAL_REMOTE_53_PASS_SOL_FRESH_PASS_OPUS_FINAL_IN_PARALLEL`
- Version label: `c2_k1_t1_plan_v3`
- Current stage: clean source and oracle-headroom falsification
- Next gate: mandatory; Q2 learning remains forbidden until T1 passes

## 1. Decision question

T1 asks one bounded question:

> If an exact clean first-successor C2 value is inserted into the required
> unweighted three-head score, can it select focal opening actions whose raw
> four-offset ratio-of-sums EE is better than the same frozen policy without
> C2, while preserving service?

This is a necessary-condition oracle screen.  Inserting the exact
\(z_{2,u}^{1}\) removes Q2 estimation error, but \(a_O\) is not an EE-maximising
action because it maximises only the declared partial score.  A failure
therefore falsifies only the **single-application opening-step C2-k1
formulation** at full-28-support physical-Main-departure anchors, under a
Q2-excluded frozen continuation and over a four-offset observation window.  It
does not falsify C2 as a mandatory route, a Q2 used at every deployment step,
sparse-support states, or horizons beyond four offsets.  Passing permits one
bounded learner screen; it does not establish learned-C2 efficacy.

The hypothesis under test is `C2_K1_PLAUSIBLE_GATED`.  The strongest failure
mode is **surrogate reversal**: the one-step temporal surplus may be real, yet
its direct-sum action can have worse omitted effects at offsets 2 and 3 and
therefore worse finite-window EE.

## 2. Why old k1 data cannot answer T1

The sealed T0 diagnostic is:

- result:
  `artifacts/multi-catfish-v06-c2-k1-t0-20260901-r1/diagnostic-result.json`;
- result file SHA-256:
  `7e2c30f9aeddb16c93a447954a96dcd9cf86b582bb307a87c4a9c3ba5631e356`;
- seal file SHA-256:
  `56c973d42ed303a2dff45810e96769a187265acbc65737d5be496c23454da0de`.

T0 shows that the old Q1+Q3 cross-initialization action-rank Spearman improves
from median `0.116585` over offsets 1--3 to `0.408867` at offset 1.  The mean
absolute normalized Q1+Q3 target scale falls from `5.83765` times the sealed C3
scale to `2.32694` times it.  This motivates a first-offset pivot only.

It is not clean evidence.  Every one of the 972 old Q1+Q3 rows still held the
opening focal candidate at offset 1, and the hold overrode the computed focal
Q1+Q3 action in 670 rows.  These two counts are derived from the Phase-B shard
rows bound under `inputs.phase_b_shards` by the T0 result; they are not fields
inside `diagnostic-result.json` itself.  Their derivation is motivational only
and is deliberately excluded from the T1 launch authority; the T1 prepare
receipt must not consume those old shards.  Old k1 values may not train Q2,
set a T1 threshold, or count toward a T1 gate.

## 3. Frozen algorithm boundary

Contract amendment: the V0.3 statement that offsets 1--3 all belong to C2
governs the retired four-offset hold/release formulation.  For this C2-k1
successor, C2 contains offset 1 only; offsets 2 and 3 are outcomes used to test
surrogate reversal, not target terms.  This amendment is registered as E-5 in
`docs/DEVIATION-REGISTER.md`.

T1 preserves all of the following:

- the canonical final ratio-of-sums EE;
- \(\lambda_0=84{,}994{,}621.12635651\) bit/J, with binding binary64 literal
  `0x1.443a8f481639ap+26`;
- \(\kappa=10{,}097{,}071{,}012.757404\) bit, with binding binary64 literal
  `0x1.2cea89d260f2ap+33`;
- exactly three independent networks \(Q_1,Q_2,Q_3\);
- one common safe-action mask;
- one direct, unweighted decision
  \(\arg\max_a[Q_1(s,a)+Q_2(s,a)+Q_3(s,a)]\);
- byte-frozen Q1 and Q3 during T1; and
- Q2 exclusion from every T1 decision, including the opening decision.

There is no auction, coordinator, vote, gate, route weight, fallback,
post-training override, target clipping, sign filter, or positive-only row
selection.

## 4. Clean C2-k1 estimand

At sealed anchor \(s\), focal user \(u\), opening candidate \(a\), candidate
branch \(C\), reference branch \(M\), and frozen Q1+Q3 continuation policy
\(\pi\), the displayed C2 target is

\[
z_{2,u}^{1}(a)=
\Delta t\sum_{i\in\mathcal U}
\left[R_i^C(1;a,\pi)-R_i^M(1;\pi)\right]
-\lambda_0\Delta t
\left[P_C^N(1;a,\pi)-P_M^N(1;\pi)\right].
\]

The reference branch \(M\) plays the frozen Main opening action \(a_M\) at
offset 0 and the frozen \(\pi\) thereafter.  \(a_M\) is one of the 28
enumerated actions, is identical for all 28 rows of a world-lineage cell, and
is the same gauge used by the frozen C1 and C3 opening targets.  Every row in a
cell binds one common reference-trace digest.  The row \(a=a_M\) is the
reference-equals-reference control and has bitwise-identical traces and exactly
zero target.

At offset 0, only focal action \(a\) differs.  At offset 1, both branches use
identical frozen \(\pi\) bytes but independently compute the safe masked
Q1+Q3 argmax on their own contemporaneous state and mask.  Their downstream
action differences are mediators of the opening intervention.

No focal hold survives offset 0.  No reference action tape, release grammar,
cross-branch action import, or branch-specific repair exists in this
formulation.  Matched exogenous randomness is mandatory.

C1 plus C3 plus this C2 exactly decomposes the two-offset linearized surplus,
not the old four-offset surplus:

\[
z_{1,u}+z_{3,u}+z_{2,u}^{1}=g_0+g_1.
\]

G-M verifies this identity from persisted offset-0 and offset-1 physical arrays
for every opening row to relative tolerance \(10^{-9}\).  Offsets 2 and 3 are
retained only to test whether this shorter surrogate reverses the final
physical direction.

## 5. Outcome-blind fresh schedule

Use only these fresh TRAIN-design seed pools:

| Stratum | Eligible step | Frozen ordered seed pool | Selection |
|---|---:|---|---|
| early | 1 or 2 | 2026101001--2026101010 | first four eligible worlds |
| mid | 3 or 4 | 2026101011--2026101020 | first four eligible worlds |
| late | 5 or 6 | 2026101021--2026101030 | first four eligible worlds |

There is exactly one anchor per selected world.  Within a selected world use
the first eligible step and the lowest eligible focal-user ID.  Eligibility
may inspect only predecision quantities: enough fixed episode slots to execute
offsets 0--3, physical Main departure, the common safe mask, 28 uniquely bound
legal opening actions, and alias absence.  It may not execute a counterfactual
or inspect a target.

If any stratum yields fewer than four eligible worlds, preparation is
`T1_INVALID_NO_TRAINING`; no seed, step, focal user, or stratum may be added or
replaced after outcomes.  The 12 selected worlds form this TRAIN-design block;
their 1008 rows may be used only as Q2 labels in the single learner screen that
Section 9 may authorise, and never to choose a threshold, loss, checkpoint,
lineage, or hyperparameter.  The 18 unselected seeds are excluded from all later
blocks.  All 30 are excluded from validation, DESIGN-EVAL, confirmation, and
TEST.

The frozen cardinality is

\[
12\times28\times3=1008
\]

matched source pairs: 12 independent physical worlds, all 28 focal opening
actions, and the three already-frozen Q1+Q3 initialization lineages.  Each
lineage uses its own fixed policy bytes; no lineage is selected by its result.
Every physical trace contains the frozen 100 users at each of its four offsets;
user-pool truncation or a shape mismatch makes G-M fail.  Every positive, zero,
negative, and all-dark complete row is retained.

Before any counterfactual outcome, a write-once v2 prepare receipt must bind the
ordered schedule, anchor digests, action keys, Q1 and Q3 parameter digests,
each cell's frozen 28-entry Q1+Q3 score vector and resulting \(a_D\), Q2-exclusion
assertion, keyed common-random-field rule, \(\lambda_0\), \(\kappa\), formulas,
gates, and this preregistration's SHA-256.  The receipt must keep two source
authorities separate: `simulator_source_manifest_sha256` authenticates the
current simulator/reward closure and is the only source digest used to root the
physical common-random field; `q13_gate_source_manifest_sha256` authenticates
the frozen Q1+Q3 gate closure and must never be substituted for the simulator
digest.  Both fields, and every anchor's simulator-manifest binding, are covered
by the prepare digest and seal.  These score vectors are target-free and cannot
be changed after outcomes.

## 6. Oracle-headroom statistic

For world \(w\), initialization \(r\), and all safe actions, let

\[
y_{w,r}(a)=z_{2,u}^{1}(a)/\kappa.
\]

The no-C2 and oracle actions are fixed as

\[
a_D=\arg\max_a\left[Q_1(s,a)+Q_3(s,a)\right],
\]

\[
a_O=\arg\max_a\left[Q_1(s,a)+Q_3(s,a)+y_{w,r}(a)\right].
\]

Both use the same safe mask and deterministic tie rule: the lowest legal action
index in the frozen 0--27 enumeration, matching NumPy `argmax`.  If \(a_D=a_O\),
the same physical trace is used by both arms and the cell contrast is exactly
zero; choosing or executing a second-best oracle action is forbidden.  A tied
cell is retained in pooled sums.  A world whose three lineages all tie has zero
world contrast and is not positive.  Even if ties make the 8-of-12 clause
unreachable, the result is a substantive G-E failure, not an instrument
failure; no tied cell may be deleted, replaced, or rescored.

After the 1008 clean k1 rows are sealed, continue only \(a_D\) and \(a_O\)
through offsets 2 and 3.  Both paths use the same lineage's frozen branch-local
Q1+Q3 policy and matched exogenous randomness.  Oracle outcomes cannot select
source rows, policy lineages, loss functions, checkpoints, or hyperparameters.

For arm \(j\in\{D,O\}\), compute raw pooled four-offset EE as

\[
\eta_j=\frac{\sum B_j}{\sum E_j}.
\]

For any declared pool of world-lineage cells,

\[
B_j=\Delta t\sum_c\sum_{k=0}^{3}\sum_{i\in\mathcal U}R_{i,c}^{j}(k),
\qquad
E_j=\Delta t\sum_c\sum_{k=0}^{3}P_{j,c}^{N}(k).
\]

The canonical realised rate is summed unmodified over every user; it is not
masked a second time by the served indicator.  Pooled means all 36 cells,
initialisation-specific means that lineage's 12 cells, and a physical-world
contrast pools that world's three fixed lineages before forming
\(\eta_O-\eta_D\).  G-E comparisons are strict; exactly zero is not positive.

Report pooled, initialization-specific, and physical-world paired contrasts.
A physical-world contrast pools its three fixed initialization lineages before
forming the ratio difference, so the independent gate unit remains the world,
not the 28 enumerated actions.

## 7. Necessary gates

All gates must pass.

### G-M — mechanics and source integrity

- exactly 1008/1008 clean pairs are complete;
- exactly 36/36 reference-equals-reference controls are bitwise identical and
  have zero target;
- both \(a_D\) and \(a_O\) traces contain valid realised physics for offsets
  0--3 in every cell; a terminal result at offset 3 is valid, while termination
  before offset 3 makes the sealed run `T1_INVALID_NO_TRAINING` without retry or
  replacement;
- the recorded k1 executed action equals that branch's recorded Q1+Q3 decision
  for every user in both branches;
- the Main-gauge identity
  \(z_{1,u}+z_{3,u}+z_{2,u}^{1}=g_0+g_1\) holds for every row to relative
  tolerance \(10^{-9}\);
- zero policy-hash, Q2-exclusion, mask, action, randomness, arithmetic,
  finiteness, or trace violation occurs; and
- no row, seed, world, or lineage is deleted, replaced, or retried by outcome.

### G-E — source-oracle EE headroom

- pooled four-offset \(\eta_O>\eta_D\);
- at least two of three initialization-specific contrasts are positive; and
- at least 8 of 12 physical-world contrasts are positive.

### G-S — service protection

- pooled oracle served fraction is not below no-C2 served fraction, where the
  fraction is the count of served user-offset pairs divided by all user-offset
  pairs over offsets 0--3 and the same cell pool used by \(\eta\); and
- at least two of three initialization-specific served-fraction contrasts are
  nonnegative.

No target-sign, positive-action count, IQR, Spearman, or magnitude threshold is
a hard gate.  A useful Q2 may operate by assigning negative evidence that
suppresses harmful actions.

## 8. Mandatory diagnostics

Report, but do not use to rescue or veto G-M/G-E/G-S:

- cross-initialization action-rank Spearman;
- k1 versus offsets-1--3 action-rank Spearman;
- target IQR, positive/zero/negative shares, and scale relative to Q1+Q3 and C3;
- Main-versus-Q1+Q3 target correlation;
- oracle action-flip rate;
- delivered bits, energy, served fraction, and outage by lineage and world; and
- source-oracle versus Main.

Also report the within-cell across-action spread of \(|Q_1+Q_3|\) versus the
spread of \(y\), because this target-free baseline scale determines whether the
exact C2 term can change the opening argmax.  The Main diagnostic uses the
shared four-offset reference trace \(a_M\) followed by \(\pi\); no third
outcome-selected policy is introduced.

Cross-initialization Spearman is diagnostic because each initialization is a
different frozen continuation policy and therefore defines a different valid
potential-outcome surface.  It is not a causal-validity test.

## 9. Stop and promotion rules

- Any structural failure yields `T1_INVALID_NO_TRAINING`.  Only mechanics may
  be corrected under a new pre-outcome sealed receipt; outcomes from the
  invalid run remain unusable.
- A structurally valid failure of G-E or G-S yields
  `C2_K1_SOURCE_FALSIFIED_NO_TRAINING`.  No replacement seed, revised
  threshold, alternate loss, sign filter, selected lineage, Q2 training, or
  TEST access is allowed.  The falsified object is only the scoped formulation
  in Section 1; C2 remains mandatory and returns to a new formula/physics
  redesign.
- Passing all gates yields `AUTHORIZE_ONE_BOUNDED_C2_K1_LEARNER_SCREEN` with Q1
  and Q3 frozen.  It is not an EE-efficacy or Chapter 5 claim.

Final C2 acceptance still requires fresh frozen evidence that
`FULL > DROP-C2`; final Multi-Catfish acceptance still requires
`FULL > DROP-C1`, `FULL > DROP-C2`, `FULL > DROP-C3`, and `FULL > Main` under
the canonical ratio-of-sums EE and service guard.

## 10. Compute and monitoring boundary

T1 source generation is a **heavy** non-GUI simulation and must run on the
Ubuntu server, not the local WSL/browser environment.  Estimated wall time is
1--2 hours after implementation conformance.  Preparation, code review,
contract tests, receipt verification, and document authoring remain local.

The frozen Ubuntu boundary is:

- checkout: `/home/sat/mcrl-leo-handover-v06-c2-k1-20260901`;
- interpreter: `/home/sat/mcrl-leo-handover/.venv/bin/python`, Python `3.13.3`;
- interpreter binary SHA-256:
  `b40f256663e21cd40985c79fde2328f68fb4710a1071e37b953099c188fce901`;
- immutable launcher:
  `.scratch/c3-v04/launch_v06_c2_k1_t1_server.sh`;
- final target-free preparation:
  `artifacts/multi-catfish-v06-c2-k1-t1-prepare-live-final-20260902-r1`;
- three lineage shards and merge:
  `artifacts/multi-catfish-v06-c2-k1-t1-source-gate-20260902-r1`;
- stdout, stderr, and one-attempt exit receipts:
  `artifacts/multi-catfish-v06-c2-k1-t1-launch-20260902-r1`.

The only permitted invocations, executed from the frozen checkout, are:

```text
.scratch/c3-v04/launch_v06_c2_k1_t1_server.sh prepare
.scratch/c3-v04/launch_v06_c2_k1_t1_server.sh shard q13-a
.scratch/c3-v04/launch_v06_c2_k1_t1_server.sh shard q13-b
.scratch/c3-v04/launch_v06_c2_k1_t1_server.sh shard q13-c
.scratch/c3-v04/launch_v06_c2_k1_t1_server.sh merge
.scratch/c3-v04/launch_v06_c2_k1_t1_server.sh verify
```

Preparation has a 3600-second timeout, each shard a 14400-second timeout, and
merge and verification each a 600-second timeout.  The three lineage shards
may run concurrently after the target-free preparation is sealed.  Every
outcome-bearing stage has exactly one attempt: no retry, replacement, output
overwrite, seed substitution, or lineage substitution is permitted.  A
timeout, nonzero exit, missing shard, or premature termination is
`T1_INVALID_NO_TRAINING`; it may not be rescued from partially produced
outcomes.  The launcher bytes are part of `PREPARE_LIVE.code_authority`, while
the preparation independently binds this preregistration's file SHA-256.  The
prepare digest is deliberately not written back into this document, avoiding
a circular hash dependency.
