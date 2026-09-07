# Current C2 diagnosis snapshot

Date: 2026-09-02  
Status: `OPS3_SELECTED_FOR_FORMULA_PROBE_ONLY__NO_C2_ACCEPTED`

## Short answer

C2 has a plausible physical path to final EE, but no attempted learned C2 has
yet demonstrated a positive marginal contribution. The historical failures do
not prove that temporal C2 is structurally impossible. They show that the
target must simultaneously be physically meaningful, available for every
current legal action, decision-time observable, action-discriminating, and
learnable without importing continuation-policy noise.

OPS-3 is the current pre-outcome attempt to satisfy all five conditions. Its
formula is frozen, but its code, mechanics tests, and no-training oracle outcome
were not available when this package was built.

## What is fixed

- final endpoint: canonical network ratio-of-sums EE, total delivered bits over
  total network energy;
- exactly `C1 -> Q1`, `C2 -> Q2`, and `C3 -> Q3`;
- one common legal mask, direct unweighted `Q1 + Q2 + Q3`, one argmax, one Main
  action;
- success: positive raw-EE `FULL - DROP-Cj` marginal for every route plus the
  service guard;
- C2 optimizes final EE from a distinct temporal perspective; improving an old
  handover metric is neither required nor sufficient.

## Why previous C2 designs failed

| Design | Verified problem | What it does not prove |
|---|---|---|
| old scalar handover `r2` | reward-only quantity; it changes neither physical bits nor network energy in the current simulator | temporal physics cannot affect EE |
| V0.4 old Q2 | harmful deployed marginal: `FULL - DROP-C2 = -30.397%` | every other C2 sign/formula is harmful |
| V0.5 controlled tape | common downstream actions lost native support in `7/48` shards | matched temporal comparisons are impossible; only this exact tape is invalid |
| V0.6 network-total next target | mixed focal physics with other-user policy cascades; learned result `-28.575%`; held-out skill weak | focal temporal effects are absent |
| V0.7 focal-next | R13 pooled `+0.046543%` was effectively zero/mixed; R14 had `0/3` lineages beat the strongest state-independent null | a richer but still observable current-action forecast cannot work |

The recurring tradeoff is the real C2 problem: realized downstream totals are
causally rich but policy-contaminated and hard to predict, while clean focal
targets have so far been weak or insufficiently action-specific.

## Why OPS-3 is now first

OPS-3 scores each current legal physical action using only a deterministic
three-offset projection of the link selected now:

- frozen-user TLE geometry and cloned future D2 eligibility;
- recurrence power for the current physical satellite/cell;
- frozen served non-focal background;
- focal projected rate and canonical marginal network power;
- absorbing service feasibility and a declared service-loss penalty;
- no future policy, future argmax, imported action, branch rollout, or RNG.

This directly addresses native-support and policy-cascade failures. It remains
an auxiliary model-based persistence prior, not an exact realized total effect.
Its most important open risks are:

1. the three-offset surrogate may be redundant with C1/C3 or may push the
   direct Q sum in a harmful direction;
2. frozen user/background and deterministic channel assumptions may rank
   current actions poorly under realized dynamics;
3. the `-kappa` service-loss term and mean-over-horizon scale may dominate or
   underweight the true EE tradeoff;
4. an analytic oracle can have useful action headroom yet still be difficult to
   distill into Q2;
5. C3 is positive only in its old-Q2 context and must be rechecked with OPS-3.

## Current evidence boundaries for C1 and C3

- C1 has `+254.596%` in the sealed V0.4 old-Q2 five-arm context and `+49.247%`
  for `Q1+Q3` versus `Q3` without old Q2. This is strong development evidence,
  not proof that C1 stays positive with every replacement Q2.
- C3 has `+21.970%` in the V0.4 five-arm context and `+21.216%` in its separate
  old-Q2 confirmation, but `Q1+Q3` versus `Q1 = -10.286%`. Therefore C3 is
  context-limited and must pass `P123 > P12` with a new Q2.

## The smallest unresolved decision

Before building a Q2 learner, determine whether the exact OPS-3 oracle surface
causes all three required current-context directions on unopened design worlds:

\[
\eta(P_{123})>\eta(P_{13}),\quad
\eta(P_{123})>\eta(P_{12}),\quad
\eta(P_{123})>\eta(P_{23}).
\]

These respectively test the C2, C3, and C1 marginal within the same new-Q2
context. Formula-unit tests precede a 12-episode no-training smoke; a fixed
36-episode three-world panel is mandatory before any learner if the smoke is
not a hard failure. Passing establishes only design direction, not efficacy.

## What the external reviewer must decide

1. Is C2 structurally plausible under the fixed direct-sum architecture?
2. Does OPS-3 genuinely target a distinct temporal EE mechanism rather than a
   renamed C1 or a reward-only preference?
3. Are its D2, recurrence-power, frozen-background, marginal-power, outage, and
   horizon definitions physically and mathematically defensible?
4. Is the service-loss term calibrated in shared units without becoming an
   arbitrary route weight?
5. Is the frozen 12/36-episode oracle probe the fastest valid falsification?
6. If OPS-3 should be revised, what exact pre-outcome formula change is needed?
7. If OPS-3 should be replaced, what formula-complete candidate has better
   support, observability, and learnability without changing the architecture?

The reviewer must return a concrete decision and must not infer final efficacy
from positive labels, action spread, oracle flips, or a tiny directional screen.
