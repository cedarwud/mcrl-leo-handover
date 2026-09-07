# Multi-Catfish EE-axis redesign contract V0.2

Date: 2026-08-31  
Status: **superseded by V0.3 after active Opus Max co-design; retained for audit only**

The isolated/direct split in this version is not the implementation target.
See `MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`.

## 1. Binding objective and topology

Only the canonical EE quantity is frozen:

\[
\eta(\tau)=\frac{B(\tau)}{E(\tau)},\qquad
B(\tau)=\sum_t R_t\Delta t,\qquad
E(\tau)=\sum_t P_t^N\Delta t.
\]

The definitions and signs of legacy `r2` and `r3` are not objectives. Handover,
load, throughput, energy, service, activation, and interference remain measured
diagnostics. They may improve or worsen; acceptance depends on held-out
Main-only ratio-of-sums EE and service safety.

The scientific topology has exactly three deployed Main Q values and one
training-time Catfish route per value:

```text
C1 -> Q1: immediate isolated/direct EE surplus
C2 -> Q2: future temporal EE surplus
C3 -> Q3: immediate shared-system spatial externality
```

At deployment, all Catfish branches, counterfactual evaluators, and private
training scorers are removed. Each user independently selects from the three
Main Q surfaces. There is no auction, voting, pair negotiation, coordinator,
decoder, or post-training override.

This document supersedes V0.1 and the unchanged-canonical-`r2/r3` learning
semantics in the R6 authoring documents. Old R6 runs remain engineering
evidence only and are not evidence for this algorithm.

## 2. One fixed global EE multiplier

For the first oracle and short-pilot stages, obtain one multiplier from a
frozen reference Main policy on the TRAIN-only calibration partition:

\[
\lambda_0=\frac{B^{M}_{\mathrm{cal}}}{E^{M}_{\mathrm{cal}}}.
\]

Seal \(\lambda_0\) before any Catfish candidate outcomes are inspected and use
the same value for every treatment arm. It must not be recomputed separately
inside an option window or separately per arm.

For a matched candidate/reference interval \(k\), define the additive EE
surplus

\[
g_k(C,M;\lambda_0)
=\bigl(B_k^C-B_k^M\bigr)
-\lambda_0\bigl(E_k^C-E_k^M\bigr).
\]

For any fixed \(\lambda_0\), the window surplus is additive:

\[
g_{0:H}=\sum_{k=0}^{H-1}g_k.
\]

Positive total surplus means the candidate improves the Dinkelbach objective
relative to the frozen reference EE. The canonical reported endpoint remains
\(B/E\); \(g\) is a training and attribution transform, not a new EE formula.

The all-dark case is retained rather than rejected: \(B=E=0\) is a valid zero
candidate contribution under the existing EE guard, and \(g\) is computed
directly with the fixed \(\lambda_0\). No division by candidate energy occurs.

## 3. Exact non-overlapping three-axis target

At one pre-outcome anchor, let candidate and reference initially differ only in
the focal user's physical action. Non-focal current actions, exogenous draws,
horizon, and continuation-policy version are matched.

### 3.1 C1/Q1 direct component

Run the focal action and reference action through a canonical single-user
isolated evaluator with the same geometry and exogenous draw. It retains the
real link, service, beam PA, circuit, and satellite baseband accounting for that
isolated served path.

\[
z_{1,u}=g^{\mathrm{iso}}_0(C,M;\lambda_0).
\]

This is an immediate isolated EE-surplus target. The unchanged per-step
\(r_{1,u}=R_u/P^N\) remains a reported canonical EE contribution, but it is not
summed across time as a substitute for the ratio-of-sums endpoint.

C1 retains the RIS-lineage EXP/ACRM concept as a training-data and auxiliary-
loss mechanism. EXP/ACRM may improve coverage and learning dynamics, but the
Main Q1 output remains calibrated to \(z_1\); ACRM cannot silently change its
physical units or fixed point.

### 3.2 C3/Q3 spatial component

Evaluate the same unilateral focal action in the complete multi-user system.
Let the full-system immediate surplus be

\[
g^{\mathrm{sys}}_0(C,M;\lambda_0).
\]

The spatial externality is the difference between the full-system and isolated
effects:

\[
z_{3,u}=g^{\mathrm{sys}}_0(C,M;\lambda_0)-z_{1,u}.
\]

It contains only the additional effect of shared mediators: bandwidth sharing,
eligible load, other-user rates, active beams/satellites, shared maximum beam
power, PA/fixed-power changes, and interference.

C3 candidate grammar must enumerate unilateral balancing and consolidation,
already-active and newly-active destinations, without filtering on the sign of
legacy \(r_3=-U_b\). Reciprocal pairs are diagnostic-only. If positive C3 value
exists only when two users coordinate, the local Q3 role fails.

### 3.3 C2/Q2 temporal component

From the same full-system branch pair, exclude the opening offset and sum only
future surplus:

\[
z_{2,u}=\sum_{k=1}^{H-1}g_k^{\mathrm{sys}}(C,M;\lambda_0).
\]

C2 candidate grammar is restricted to association timing: stay, switch,
hold/release, and future-availability alternatives. This makes \(z_2\) the
downstream consequence of a temporal intervention without inventing a second
physics engine or requiring the old handover reward to improve.

The existing C2 V0.3A branch-local Main, common anchor, physical-ID binding,
sealed candidate schedule, retain-all traces, RNG lineage, transaction, and
resume infrastructure remain reusable. The old positive `r2` margin,
window-local EE multiplier, useful-bits nonloss, and fading-disabled target
gates do not remain.

### 3.4 Sum identity

The three targets are non-overlapping by construction:

\[
z_{1,u}+z_{3,u}+z_{2,u}
=\sum_{k=0}^{H-1}g_k^{\mathrm{sys}}(C,M;\lambda_0).
\]

This identity is a mandatory machine check on every retained candidate and
reference pair. It is an attribution identity, not an efficacy result.

## 4. Q semantics and deployment score

The first implementation learns fixed-horizon pairwise action advantages,
not three incompatible infinite-horizon Bellman optima:

\[
Q_j(s,a_C)-Q_j(s,a_M)\approx z_j(C,M)/c_j.
\]

Use zero bootstrap for the first formula/learnability pilot:

\[
L_j^{\mathrm{pair}}=
\left[
c_j\{Q_j(s,a_C)-Q_j(s,a_M)\}-z_j
\right]^2.
\]

Add a consistency term:

\[
L_{\Sigma}=\left[
\sum_{j=1}^{3}c_j\{Q_j(s,a_C)-Q_j(s,a_M)\}
-g_{0:H}^{\mathrm{sys}}(C,M;\lambda_0)
\right]^2.
\]

The physical deployment score restores native units before addition:

\[
S(s,a)=\sum_{j=1}^{3}c_jQ_j(s^{(j)},a),
\qquad
a^*=\arg\max_{a\in\mathcal A(s)}S(s,a).
\]

Therefore the scientific weights are \((1,1,1)\) in EE-surplus units. The old
arbitrary \((0.5,0.3,0.2)\) scalarization is not retained. Per-head scales
\(c_j\) are numerical normalization only and must be multiplied back before
selection.

An SMDP bootstrap may be considered only after the fixed-H pairwise pilot. It
must use candidate-minus-reference successor values and one masked deployed
policy; it cannot reuse the old independent per-head `max Q_j` targets.

## 5. Required deployment observations

The current 112-dimensional observation is insufficient for the new targets.
Before learning:

- Q2 must observe or reconstruct the previous physical association, segment
  start gain or current recurrence power, segment age, dwell/TTT, interruption
  state, and a motion/history feature;
- Q3 must receive a predecision broadcast summary of prior eligible load,
  active beam/satellite state, beam maximum and second-maximum required power,
  PA/fixed marginal cost, and co-channel occupancy/interference;
- Q1 must receive the direct power variables required to predict the isolated
  surplus.

The broadcast is computed before simultaneous actions and contains no action
negotiation. If identical deployment observations/actions carry stable
opposite-sign targets, expand the state or reject that role before training.

State dimensions, replay schema, checkpoint schema, and trainer inputs must be
versioned together. Old checkpoints cannot be resumed into this redesign.

## 6. Pre-outcome, retention, and safety rules

1. Trigger and proposal use only pre-outcome state, masks, physical IDs, frozen
   models, and domain-separated RNG.
2. Every scheduled candidate is sealed before any outcome selects a row.
3. All valid favourable, unfavourable, and all-dark outcomes are retained.
4. Candidate/reference use equal horizons and common random numbers, including
   the same stochastic model rather than disabling fading for one target path.
5. Only a source's matching \(z_j\) updates its matching Q route.
6. Service/outage safety is retained as a separate guard. Throughput, energy,
   handover, and load directions cannot be Catfish admission gates.

## 7. No-training gates before implementation

### F1: global-multiplier reversal

On frozen anchors, retain \((B^M,E^M,B^C,E^C)\). Compare the signs produced by
the old window-local multiplier and \(\lambda_0\). Any reversal proves the old
support decision is ineligible for reuse.

### F2: exact three-target identity

For every candidate, require

\[
z_1+z_2+z_3=g_{0:H}^{\mathrm{sys}}
\]

within a preregistered numerical tolerance, including zero-energy/all-dark
branches.

### F3: C2 physical support and observability

Require service-safe temporal candidates with nonzero positive \(z_2\), measure
how often the focal user determines its beam's maximum power, and construct the
segment-history alias test. Opposite target signs for identical observations
block training until state revision.

### F4: C3 unilateral headroom

For each anchor, compare the action maximizing isolated \(z_1\) with the action
maximizing \(z_1+z_3\). C3 has physical headroom only when the latter provides
additional full-system surplus on held-out anchors. Repeat with simultaneous
top-k unilateral proposals to detect crowding or oscillation.

### F5: role distinctness and action headroom

Reject a role if its target is always zero, a fixed affine copy of another
target, unobservable from the proposed state, or unable to change the final
masked action after native-unit restoration.

## 8. Empirical acceptance after the gates

Use eight matched arms: `B000`, `C100`, `C010`, `C001`, `F111`, `A011`,
`A101`, and `A110`. Freeze training seeds, evaluation seeds, environment steps,
updates, replay budgets, state/schema version, \(\lambda_0\), and target scales
before training.

The role-level EE conditions are:

\[
C100>B000,\quad C010>B000,\quad C001>B000,
\]

\[
F111>A011,\quad F111>A101,\quad F111>A110.
\]

The preferred full-system result is \(F111\) best among all frozen arms. Final
thresholds, seed count, paired interval, multiplicity control, service margin,
and minimum important effect must be preregistered after development variance
is known and before held-out results are opened. Strict point inequalities
alone are not sufficient.

All evaluation is Main-only ratio-of-sums EE and separately reports useful
bits, system energy, service, active resources, and zero-power/all-dark counts.
A role that improves its private target but not held-out Main-only EE fails.

## 9. Current authorization

Current verdict: **formula-level REDESIGN, conditional GO**.

- The three-role target now has an exact additive identity under one global
  multiplier.
- C2's carrier and C3's one-step counterfactual seam are reusable.
- The isolated evaluator, state expansion, target/replay schema, and F1--F5
  gates are not yet complete.

No new training is authorized yet. In particular, no 1500-, 3000-, or
9000-episode run may use this V0.2 label until F1--F5 and the implementation
tests pass. The user must be notified before any 9000-episode launch.
