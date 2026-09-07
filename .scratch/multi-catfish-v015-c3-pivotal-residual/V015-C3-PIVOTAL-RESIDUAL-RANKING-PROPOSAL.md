# V0.15 C3 pivotal residual-ranking proposal

Status: exploratory proposal, now superseded for gate planning by
`V015-C3-REFERENCE-CONDITIONED-STATE-PRELIMINARY-REPORT.md`.  This file is
not shared authority and does not authorize a simulator run, a learner gate,
TEST access, or episode training.  The direct loss below is retained as an
auditable rejected-before-gate candidate, not as the current launch route.

## Purpose

The earlier V0.15 learned-context route is rejected before a production run.
One exploratory one-lineage run of the narrower *one pair + V0.14 pairwise
MSE* also failed to preserve decisions (base/teacher agreement `0.7877`,
student agreement `0.6290`, gain `-0.1587`).  The present proposal keeps the
useful frontier sampling but adds a decision-aligned stability constraint so
that a non-pivotal row is not treated as an ordinary positive/negative pair.

The proposal used the existing immutable V0.14 TRAIN/VALIDATION source shards,
the existing 287-dimensional V0.14 Q3 state, the existing 28-action
ActionSet network, and a frozen V0.14 learned Q2 checkpoint.  Q1 and Q2 are
background only; only Q3 is trainable.

## Frozen quantities and decision labels

For each source row, form the detached learned background

\[
B(a) = Q_1(a) + \widehat Q_2(a).
\]

The ZR target surface remains exactly the existing signed surface in native
bits, `z_3(a)`.  It is converted only at the learner boundary by the already
frozen `kappa`:

\[
a^0 = \arg\max_{a\in\mathcal A_{safe}} B(a),\qquad
a^T = \arg\max_{a\in\mathcal A_{safe}}
       \left[B(a)+z_3(a)/\kappa\right].
\]

Both argmax operations use the existing deterministic first-index tie break.
The background is never recomputed from the evolving Q3 and receives no
gradient.

## Source frontier

Each row with at least two legal actions contributes one retained frontier
pair:

* if `a^T != a^0` (pivotal), retain `(reference, candidate) = (a^0, a^T)`;
* if `a^T == a^0` (stable), retain `(a^0, a^R)`, where `a^R` is the highest
  non-base legal action under `B + z_3/kappa`;
* rows with only one legal action are recorded as non-pairable and omitted from
  the learner update, but remain in decision diagnostics.

For either retained pair the target is the unchanged signed residual

\[
\delta_3 = z_3(a^{candidate})-z_3(a^0).
\]

This is a source reduction, not a new reward or a sign filter.  It avoids
spending residual-MSE capacity on every legal action while preserving a
stable-row control surface.

## Q3 learner objective

Let `q(a)` be the trainable Q3 surface and `S(a)=B(a)+q(a)`.  The retained
frontier pair supplies the only residual regression:

\[
L_{pivot} = \operatorname{mean}_{a^T\ne a^0}
  \left[q(a^T)-q(a^0)-\delta_3/\kappa\right]^2.
\]

The actual deployment score is constrained on the same pair:

\[
L_{flip} = \operatorname{mean}_{a^T\ne a^0}
  \left[\max(0,S(a^0)-S(a^T))\right]^2.
\]

For stable rows, every legal non-base action is constrained not to overtake
the frozen base:

\[
L_{stable} = \operatorname{mean}_{a^T=a^0,,a\ne a^0}
  \left[\max(0,S(a)-S(a^0))\right]^2.
\]

The inherited pairwise gauge is retained:

\[
L_{gauge}=\operatorname{mean}\ q(a^0)^2.
\]

The fixed development objective is

\[
L = L_{pivot}+L_{flip}+L_{stable}+\beta L_{gauge},
\]

with both decision terms having fixed coefficient one.  `beta` is the
existing V0.14 gauge value.  There is no route weight, coordinator, learned
threshold, outcome-tuned margin, full-surface MSE, Q2 update, or Q1 gradient.
Equality is the exact teacher boundary; no artificial positive margin is
introduced.

## Why the design is narrower but addresses the failure

The rejected one-pair MSE taught a stable runner-up as though it were a
required improvement.  On a stable row the runner-up may have a positive ZR
residual but still lose to the background margin.  `L_stable` therefore asks
only that Q3 not change the already-correct base decision.  On a pivotal row,
`L_pivot` preserves the exact ZR residual between the teacher and base, while
`L_flip` measures the actual `B+Q3` ordering that deployment uses.

Existing VALIDATION descriptive statistics support this focus but are not
efficacy evidence: across the three frozen-Q2 initialisations the pivotal
rates were `21.23%`, `18.40%`, and `19.40%`; among pivotal rows the teacher
candidate had positive compatibility in `98.27%`, `98.91%`, and `98.97%` of
rows, with median ZR candidate-minus-base residuals `0.450`, `0.501`, and
`0.494` kappa.  Stable runner-up residuals had median about `-0.004` kappa
and were insufficient to overcome the learned-background margin.  These
figures motivate the loss; they do not establish trajectory EE improvement.

## Proposed source-only gate (not authorized)

After root freezes a new preregistration, the gate may use the existing
immutable V0.14 source closure and exactly three frozen learned-Q2 rung-3000
checkpoints.  It trains independent Q3 initialisations on TRAIN only and
reports validation-only diagnostics at fixed rungs:

* pivotal teacher agreement (`argmax(B+Q3)` equals `a^T` on `a^T != a^0`);
* stable preservation (`argmax(B+Q3)` equals `a^0` on `a^T == a^0`);
* all-row teacher agreement and retained-pair residual MAE;
* source row/pair/pivotal/stable counts and checkpoint hashes.

The gate has no simulator call, opens no TEST shard, and cannot make
an EE or deployment-efficacy claim.  A trajectory ablation, if later
authorized, is a separate post-gate step and must use a new contract.

## Immutable Q2 inputs currently available

The proposed runner validates the outer V0.14 gate checkpoint and its nested
Q2 payload, including exact file SHA-256 values:

| V0.14 initialization | checkpoint | SHA-256 |
|---|---|---|
| 2026108101 | `init-2026108101-rung-003000.pt` | `d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d` |
| 2026108102 | `init-2026108102-rung-003000.pt` | `9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef` |
| 2026108103 | `init-2026108103-rung-003000.pt` | `8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81` |

The current V0.14 source shards and the Q2 checkpoints are inputs only; this
proposal does not alter their files or any shared authority document.  A
subsequent exploratory 1000-update one-lineage run of this direct learner
also failed (pivotal agreement `0.2998`, stable preservation `0.2945`, 2204
student changes, support `0.2069`).  This reinforces that the missing
reference-conditioned cross-user state, rather than another loss tweak, must
be resolved first.  See the preliminary state report for the bounded R0
representation proposal.
