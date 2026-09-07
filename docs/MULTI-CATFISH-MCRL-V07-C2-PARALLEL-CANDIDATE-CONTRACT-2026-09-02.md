# Multi-Catfish MCRL V0.7 C2 parallel-candidate contract

Date: 2026-09-02  
Status: `PREOUTCOME_CANDIDATES_DEFINED__SOURCE_REVIEW_PENDING__DO_NOT_LAUNCH`  
Claim ceiling: `FORMULA_AND_PROTOCOL_ONLY__NO_C2_EFFICACY`

## 1. Decision

C2 development is no longer sequential.  Three candidates are defined before
any formal target-bearing screen is opened:

| Arm | Temporal question | Current implementation state |
|---|---|---|
| P0 | What focal-attributable EE surplus is realised at the next slot? | formula, Q2-specific state, dataset, policy, live adapter, and formula/source runner implemented; runner integration audit open |
| B1 | Does the opening action preserve an EE-efficient focal association over the remaining short segment? | pure formula implemented; source adapter pending |
| B2 | Does the opening action preserve a better EE-efficient successor option set? | pure formula implemented; source adapter pending |

P0, B1, and B2 are screened from a predeclared common anchor block.  A P0
failure is not a trigger to invent B1 or B2; both backups already exist and
their definitions cannot be changed after any formal outcome is read.

## 2. Shared scientific boundary

All arms optimize one canonical ratio-of-sums EE endpoint and use the same
TRAIN-only multiplier

\[
\lambda_0=\frac{\mathcal B_0^M}{\mathcal E_0^M}.
\]

Every target is in native bit-equivalent EE-surplus units.  Each target starts
at successor offset \(k=1\), so it cannot double count C1's focal-now or C3's
non-focal-now opening effects.  A candidate updates only \(Q_2\); deployment
remains

\[
\Phi_u(t,a)=Q_1(s_u,t,a)+Q_2(s_u,t,a)+Q_3(s_u,t,a),
\qquad
a_u^*(t)=\arg\max_{a\in\mathcal A_u(t)}\Phi_u(t,a).
\]

There is one native mask, one unweighted sum, and one argmax.  No candidate may
introduce a route weight, veto, second decoder, coordinator, auction, or
post-training override.

All physical measurements use the canonical multi-user environment.  An
"evaluate without focal user" call is only a non-committing marginal-power
measurement inside that environment; it is not the retired isolated-world
simulator.

## 3. P0: realised focal-next surplus

For branch \(b\in\{C,M\}\), let

\[
p_{b,u}(1)=P_b^N(1)-P_{b,-u}^N(1).
\]

P0 is

\[
\zeta_{2,u}^{P}(s,a)=
\Delta t[R_u^C(1)-R_u^M(1)]
-\lambda_0\Delta t[p_{C,u}(1)-p_{M,u}(1)].
\]

The successor action vector is produced separately on each branch by the same
frozen direct policy.  P0 therefore values the one-step consequence that would
actually be realised by that policy.  Its risk is policy/cascade noise; the
formula/source gate must establish that the label is stable and observable.

## 4. B1: focal segment-continuation surplus

B1 isolates the persistence value of the focal opening association over the
same four-offset counterfactual window used by the method: opening offset zero
is excluded and successor offsets are \(k=1,2,3\).

At every successor offset, non-focal physical actions come from one
precommitted common tape and are held identical across the matched branches.
The focal branch holds its opening physical association while it remains legal;
after loss of legality it uses the physics-only no-op for the remaining B1
offsets.  Slot indices may not stand in for physical satellite/beam identity.
Any common-tape action that cannot be replayed in both branches makes the
source cell structurally unsupported; it may not trigger a fallback or
replacement anchor.

For every supported offset,

\[
p_{b,u}(k)=P_b^N(k)-P_{b,-u}^N(k),
\]

and

\[
\boxed{
\zeta_{2,u}^{B1}(s,a)=
\sum_{k=1}^{3}\left\{
\Delta t[R_u^C(k)-R_u^M(k)]
-\lambda_0\Delta t[p_{C,u}(k)-p_{M,u}(k)]
\right\}.
}
\]

B1 asks whether an opening action creates an EE-efficient *durable link*, not
whether a continuation policy happens to react well.  It is distinct from P0
because it removes branch-local non-focal action cascades and integrates link
persistence over the short segment.

The formula receipt accepts and retains the four raw network-power vectors
— branch full and branch without-focal for both candidate and reference — and
reconstructs every marginal power internally.  It accepts exactly the three
registered successor offsets; a shorter or longer vector is not B1.

## 5. B2: successor option-set surplus

B2 values temporal flexibility instead of committing to one realised
successor action.  At successor offset one, keep a precommitted non-focal
physical action vector fixed and enumerate every native legal focal action in
each branch.  Define

\[
e_{b,u}(1,a')=\Delta t
\left[R_{b,u}(1,a')-\lambda_0p_{b,u}(1,a')\right].
\]

The physics-only no-op is an outside option with value zero.  It is not added
to the 28-action mask.  The branch value and B2 target are

\[
V_{b,u}(1)=\max\left(0,\max_{a'\in\mathcal A_{b,u}(1)}e_{b,u}(1,a')\right),
\]

\[
\boxed{
\zeta_{2,u}^{B2}(s,a)=V_{C,u}(1)-V_{M,u}(1).
}
\]

B2 asks whether the opening action preserves a better EE-efficient *future
choice set*.  It is distinct from P0 because it is policy-free, and distinct
from B1 because it values successor flexibility rather than one held link.
Its formula receipt likewise retains full and without-focal power for all
exactly 28 native action slots; a compact or prefiltered surface is not B2.

## 6. Common source schedule

Before formal execution, one manifest freezes:

- the same physical seeds and outcome-blind early/late anchor selector;
- the same 20 physical anchors and three frozen Q1/Q3 lineages;
- the exact hexadecimal \(\lambda_0\) and \(\kappa\);
- the state schema, keyed-random-field version, physical-ID mapping, horizon,
  and common non-focal tape grammar;
- the three target-schema hashes and code authority hashes; and
- all mechanics, variation, observability, learning, and EE decision rules.

The capture layer may share replayed prefixes and opening branches, but it
must persist arm-specific raw terms.  A formula for one arm may not consume a
scalar target produced by another arm.  Identical candidate/reference branches
must reconstruct exact zero for all three arms.  Positive, zero, and negative
rows are retained without clipping or sign filtering.

Formal execution is parallel in the scientific sense: every registered arm is
evaluated on the common block regardless of another arm's result.  Runtime
shards may execute concurrently on the Ubuntu server.  Failure of one arm does
not cancel or redefine the others.

## 7. Fixed evidence ladder and selection

### Stage A: formula/source screen

Each arm receives an independent verdict using the same anchors:

1. complete provenance and exact formula reconstruction;
2. native legal-action coverage and exact equal-action zero controls;
3. non-degenerate within-anchor target variation;
4. positive alternatives on multiple physical anchors;
5. target scale compatible with the frozen Q1+Q3 surface; and
6. no persistent opposite-sign labels for effectively identical Q2
   observations and actions.

Thresholds must be frozen in the run manifest.  A failing arm does not enter
learning but does not stop the remaining registered arms.

### Stage B: 100-update TRAIN/VALIDATION

Every Stage-A passer independently receives the same Q2 architecture,
initialization count, update budget, checkpoint at update 100, world-disjoint
TRAIN/VALIDATION split, and strongest action-only null.  Pass requires
held-out pair skill and calibrated action differences; TRAIN fit alone is not
sufficient.

### Stage C: fresh directional EE screen

Every Stage-B passer receives an equal-budget fresh-seed FULL versus DROP-C2
screen.  The primary selection statistic is held-out ratio-of-sums EE subject
to the frozen service guard.  The candidate with the greatest registered
median EE improvement is selected; differences inside a predeclared practical
tie band use the simplicity order P0, B1, B2.  All arm results are reported.
The selected arm then receives a fresh confirmatory block, so Stage C is not
the final efficacy claim.

If no arm passes, the entire P0/B1/B2 generation is sealed negative before a
new candidate generation is designed.  Thresholds, seeds, and arms may not be
changed in response to partial results.

## 8. Observation gate

Every candidate predicts a future consequence.  A feed-forward Q2 observation
must therefore distinguish future-relevant states such as an approaching and
a receding candidate at otherwise similar current angle/range.  The sealed
V0.3 228-dimensional state fails this condition: signed range rate is present
in `StepCandidates.contract_fields` but the live encoder intentionally omits
that dormant 13-dimensional ablation block.

Q2 therefore uses the separate 228-dimensional schema
`multi-catfish-mcrl-v07-c2-q2-signed-range-rate-state-v1`, SHA-256
`70cef9bd525ded7df76138364afd31b2e804446b9d199d01ccef845e5a09d2c0`.
It preserves the complete 112-dimensional base, including access.  Of the four
appended 28-action blocks, only `beam_active` is replaced: under canonical
service commit semantics a beam radiates iff its retained
`eligible_served_load` is positive.  The encoder verifies that exact identity
before replacing the redundant bits with the current signed range rate,
repeated over the seven legal beam actions of each satellite slot and zero on
illegal actions.  Q1 continues to consume V0.3 state and Q3 continues to
consume V0.4 C3 state.  This is a representation correctness fix, not an extra
reward or a new Catfish mechanism.

No target-bearing formal screen launches until that question and the open P0
runner audit are closed.  This does not block formula/source implementation of
B1 and B2.

## 9. Current verification and launch boundary

Formula implementation:

- `src/mcrl/runtime/ee_axis_v07_c2_state.py`
- `src/mcrl/runtime/ee_axis_v07_c2_parallel_targets.py`
- `tests/test_w121_ee_axis_v07_c2_state.py`
- `tests/test_w120_ee_axis_v07_c2_parallel_targets.py`

The nine W120 tests cover signed and raw-term-reconstructible B1 arithmetic,
its exact three-offset horizon, exact-zero identity, malformed physical
vectors, native-28 B2 legal-option maximization, the no-op zero floor, exact
equal-surface zero, and strict Boolean masks.  The four W121 tests cover the
legacy approach/recede collision, signed-motion separation with byte-preserved
base access, the frozen state-schema digest, and the beam-active redundancy
guard, including one canonical committed-environment smoke.

P0's W111--W119 suite and B1/B2's W120 suite are implementation evidence only.
They do not establish source viability, learnability, or EE improvement.

The formula/source screens and all later rollouts are heavy non-GUI work and
belong on the Ubuntu server.  No 1500-, 3000-, or 9000-episode training is
authorized here.  The user must be notified before a future 9000-episode
launch, and every episode-training run must checkpoint every 100 episodes.
