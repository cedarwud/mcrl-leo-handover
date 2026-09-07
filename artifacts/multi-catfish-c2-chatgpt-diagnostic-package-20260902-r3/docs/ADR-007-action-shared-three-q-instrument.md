# ADR-007: Use an action-shared scorer for the three-Q instrument

## Status

Accepted

## Date

2026-09-01

## Context

The first E1 ladder used a free `228 -> 28` output surface for each route-local
Q function. Validation diagnostics found that 90--96% of the held-out score
variation could be explained by fixed output-slot effects. The original
action-only comparison also overstated C2 and C3 skill because, on those
routes, it was weaker than a parameter-free zero predictor.

The physical C1, C2, and C3 interventions were not invalidated. Replacing only
the learner surface with a shared scalar scorer produced positive
train-to-validation skill for every route and every initialization at a
common 30-update rung while reducing the fixed-slot explanatory fraction to
near zero for C1 and C3 and about 0.22 for C2. This is design evidence only;
test data and the EE endpoint remained unopened.

## Decision

Use exactly three independent action-shared Q functions:

`Q_j(s,a) = f_{theta_j}(x_a, g),  j in {1,2,3}`.

Here `x_a` contains the eight action-aligned state features and `g` contains
the four temporal global features. One scalar MLP is shared across all action
slots within a head; parameters are not shared across C1, C2, and C3. The
deployment rule remains one masked argmax of `Q_1 + Q_2 + Q_3`.

Keep the calibrated pair loss, `beta = 0.1`, learning rate `0.001`, hidden
widths `(100, 50, 50)`, and common surplus normalization. A sealed beta screen
over `{0, 0.01, 0.1}` showed no material C2/C3 benefit from changing beta and
favoured `0.1` overall. Do not promote DeepSets. A masked mean/max context
scorer is allowed once as a predeclared fallback only if fresh validation
passes C1 and C2 but fails C3.

The old validation split is design-only because it was used to choose the
repair. Generate a fresh four-seed train and three-seed validation supplement.
It generates no test outcomes; the existing E1 test split remains sealed and
unopened.

## Alternatives considered

### Keep the free 28-output network

Rejected. More updates do not remove its state-independent slot shortcut.

### Remove the gauge penalty

Rejected as an unnecessary change. The beta screen produced almost identical
C2/C3 results and slightly better C1 results at the retained `beta = 0.1`.

### Add learned set context or a fourth Main Q

Rejected. DeepSets added runtime and parameters without material C3 gain. A
fourth Q violates the requested three-Q topology and mixes incompatible units.

## Consequences

- The physical three-Catfish story and all three surplus targets are unchanged.
- The learner is permutation-equivariant to a consistent action-slot
  permutation, preventing a free output neuron from representing action
  identity.
- Existing free-output E1 receipts remain negative diagnostics, not training
  authority.
- No EE efficacy claim follows from this decision.
- A bounded matched ablation may start only after the amended fresh validation
  screen passes.  It first evaluates the sealed selected-rung Q3, then may
  checkpoint 500 additional source-training epochs every 100 updates; these
  update counts are not simulator episodes.

See
`docs/MULTI-CATFISH-MCRL-V03-E1-ACTION-SHARED-AMENDMENT-2026-09-01.md`.
