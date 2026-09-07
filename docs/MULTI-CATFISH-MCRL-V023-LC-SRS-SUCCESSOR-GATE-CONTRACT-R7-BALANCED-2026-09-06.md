# Multi-Catfish MCRL V0.23 LC-SRS one-shot successor Gate contract

Date: 2026-09-06  
Status: `DRAFT_PRE_OUTCOME / NO_LAUNCH / ONE_SUCCESSOR_ONLY`  
Split: TRAIN development only; TEST remains closed

## 1. Decision being tested

R6 remains failed under its frozen raw informed-minus-placebo sign-accuracy
predicate.  This document cannot relabel, recompute, or rescue R6.  It defines
one prospective successor experiment motivated by the observed class
imbalance in the R6 sign-labelled rows.

The paper-visible LC-SRS teacher, four matched profiles, deterministic C3View,
fixed learner, literal one-pass `Q1 + Q2 + Q3` deployment, and every physical,
composition, topology, service, provenance, and no-coordination condition from
`MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`
remain unchanged except where this document explicitly replaces a world,
learner-seed, metric, token, or execution identifier.

This is not an efficacy experiment and cannot authorize episode training.

## 2. Disclosure and non-retroactivity

The revision is outcome-informed method development: R6 used 1,038 positive
and 286 negative sign-labelled rows, and its frozen raw accuracy advantage was
0.03776435045317217 against a required 0.05.  R6 remains a failed development
Gate.  Its rows, worlds, fitted parameters, composition receipts, and
diagnostics are excluded from every R7 fit and decision denominator.

Balanced accuracy is introduced prospectively because raw accuracy weights
classes by their observed prevalence.  It is not evidence that LC-SRS works,
and it is not substituted into the R6 decision.

## 3. Fresh immutable panel

The only R7 physical world seeds, in order, are:

```text
2026121801 2026121802 2026121803 2026121804
2026121805 2026121806 2026121807 2026121808
```

The only R7 learner initialization/sampling seeds are:

```text
2026135201 2026135202 2026135203
```

Before opening any source outcome, preflight must bind the initial parameter
digest for each seed.  No R6 world `2026121705`--`2026121712`, R6 learner seed
`2026135101`--`2026135103`, older world, TEST world, replacement seed, or
extra seed may enter R7.  World remains the physical cluster; learner seeds
are not independent physical replicates.

All other execution constants remain those of the original Gate: 100 users,
10 steps, 28 actions, 32 matched keyed-fading draws, the authenticated d40
Q1/Q2 checkpoint, lambda, kappa, source selection, placebo construction,
leave-one-world-out folds, network architecture, 2,000 updates, batch size
256, Adam learning rate 0.001, and lowest-index exact-tie rule.

## 4. Frozen sign estimands

For every held-out SUPPORTED row, keep the original eligible-set rule

\[
\left|\bar y_r\right|\geq 0.02.
\]

Let positive and negative eligible denominators be `n+` and `n-`.  For a
prediction difference `yhat`, define

\[
T_+=\frac{\#\{r:\bar y_r>0,\ \widehat y_r>0\}}{n_+},\qquad
T_-=\frac{\#\{r:\bar y_r<0,\ \widehat y_r<0\}}{n_-},
\]

and

\[
A=\frac{T_++T_-}{2}.
\]

Strict zero predictions are incorrect for either class.  Rows below the
unchanged magnitude threshold are excluded and counted exactly as in R6.
Missing, non-finite, or zero class denominators fail the metric.  Every `n+`,
`n-`, correct-positive count, correct-negative count, class recall, balanced
accuracy, raw sign accuracy, exclusion count, learner seed, and world is
serialized.

For each learner seed, pool its eight held-out-world rows exactly once and
compute INFORMED and MATCHED-PLACEBO `A` independently.  The primary balanced
values are arithmetic means over the three declared learner seeds.  Raw sign
accuracy is recomputed and reported with the original definition but is
secondary in R7 and cannot replace the balanced decision after outcomes open.

## 5. Fixed learner predicate

The original held-out Spearman and world-stability predicates remain binding.
The R7 held-out learner predicate is true only when all of the following hold:

1. mean INFORMED Spearman is at least 0.20;
2. mean INFORMED balanced accuracy `A` is at least 0.60;
3. mean INFORMED `A` minus mean MATCHED-PLACEBO `A` is at least 0.05;
4. the pooled eligible set contains at least 24 positive and 24 negative rows;
5. mean-seed INFORMED Spearman strictly exceeds MATCHED-PLACEBO in at least
   six of eight held-out worlds; and
6. each INFORMED learner seed has nonnegative Spearman in at least five of
   eight held-out worlds.

No threshold is a search space.  The result must also report the R6-style raw
INFORMED and placebo sign accuracies and their gap, but those values neither
rescue nor veto the R7 balanced predicate.

## 6. Unchanged full-Gate predicates

R7 is not a fit-only Gate.  It must recompute and pass every unchanged
coverage, mechanics, matched-field, physical-signature, leakage, action
exposure, literal-11, harmful-partial, topology-consistency, teacher
composition, learned full-roster composition, service, and independently
authenticated C1/C2 context predicate from the original contract on the new
panel.

The composition runtime must execute with a predeclared deterministic process
environment, including fixed BLAS/OpenMP thread settings, and must prove replay
identity before an outcome is admitted.  A replay digest mismatch is
`INVALID_RUN`, not a scientific sign.

## 7. One-shot decisions and hard stop

After all integrity checks pass, emit exactly one of:

- `INSUFFICIENT_PAIRS_R7`
- `STOP_PHYSICS_R7`
- `STOP_OBSERVABILITY_R7`
- `REDESIGN_INTERFACE_R7`
- `GO_FIXED_LEARNER_SCREEN_CONTRACT_R7`

Use the same precedence as the original Gate.  The GO token requires every
unchanged full-Gate predicate plus Section 5.  A valid non-GO result ends the
LC-SRS successor route.  There will be no second metric revision, threshold
relaxation, seed/world replacement, rerun selected by outcome, or automatic
promotion of CSE/EC.  A later CSE/EC experiment requires its own already
declared formula and falsifier; it cannot reuse R7 outcomes for selection.

An `INVALID_RUN` may repair only a demonstrated infrastructure defect and
replay the smallest unopened or invalid unit.  It cannot change a scientific
predicate or discard a valid outcome.

## 8. Execution and claim boundary

This full eight-world, three-seed Gate is heavy CPU work and belongs on the
Ubuntu server.  Before launch, freeze this document's bytes, code/preflight
manifest, initial learner digests, TLE file-set digest, process environment,
output root, and independent verifier.  The draft status itself authorizes no
launch.

Even a GO establishes only that the fixed source is mechanically valid,
held-out observable under the declared estimands, and composable under this
Gate.  It does not establish that C3, C1, C2, FULL, or Multi-Catfish improves
EE.  That question begins with a separately frozen 100-episode matched
five-arm development screen.
