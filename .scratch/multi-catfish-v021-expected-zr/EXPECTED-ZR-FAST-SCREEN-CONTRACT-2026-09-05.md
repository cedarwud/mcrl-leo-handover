# V0.21 EXPECTED-ZR fast screen contract

Status: frozen before any V0.21 outcome is opened  
Split: `TRAIN_DEVELOPMENT` only  
Claim ceiling: mechanics and one-anchor directional triage; no efficacy, no learner, no episode training, no TEST

## Question

Can a deployable conditional expectation of the complete nonlinear ZR label retain action-specific C3 value on the repriced Q1+Q2 background, without reading the evaluation fading realization?

## Frozen panel

- Fresh world: `2026121601`; absent from the local and Ubuntu-server project evidence before freeze.
- Q1/Q2 lineage: `2026092101`, using the authenticated V0.20 repriced checkpoint.
- Anchor: the initial predecision anchor only (`step_index = 0`).
- Integration draws: `K = 8`, roots derived from `(MCRL_V021_EXPECTED_ZR_FAST_V1, integration, world, draw)`.
- Evaluation draws: `L = 8`, roots derived from `(MCRL_V021_EXPECTED_ZR_FAST_V1, evaluation, world, draw)`.
- Integration and evaluation root digests must be pairwise disjoint.
- Every draw computes the full exact nonlinear ZR label first; labels are averaged only afterward. Averaging fading, SINR, or rate before applying the ZR formula is forbidden.

## Arms on the fixed anchor

- `B`: detached `Q1 + Q2` background action.
- `N`: current deterministic nominal-ZR surface added to the same background.
- `E`: privileged pathwise exact-ZR action for each evaluation draw; diagnostic only.
- `R`: the fixed `K=8` conditional-expected ZR surface added to the same background.
- `P`: deterministic within-row permutation of `R` scores over compatible legal non-reference actions, with reference fixed at zero; action-specificity control. For each user, compatible legal non-reference indices are sorted ascending and their values are cyclically rotated by one position; all other cells remain unchanged.

`B`, `N`, `R`, and `P` actions are fixed before any evaluation draw is opened. Only `E` may depend on its own evaluation draw and is never deployable evidence.

## Required mechanics

1. The native action mask and reference actions are byte-identical across integration draws.
2. Compatibility is byte-identical across integration draws; otherwise the screen stops as `COMPATIBILITY_NOT_STATE_IDENTIFIED`.
3. Each draw and the mean have exact-zero reference cells, exact-zero illegal cells, finite values, and no positive value outside compatibility after reference centering.
4. The live environment and caller RNG are unchanged by all counterfactual measurements.
5. `K=4` versus `K=8` is reported as a numerical-stability diagnostic only; it cannot change the frozen formula or seeds.
6. Evaluation uses only the independent evaluation roots.

## Directional triage

For each arm, aggregate bits and energy across the eight evaluation draws on the fixed anchor and compute ratio-of-sums EE. Service is the pooled served-user fraction.

`GO_FULL_EXPECTED_ZR_GATE` requires all of:

- all mechanics pass;
- `R` changes at least one background action;
- pooled `EE_R > EE_B`, `EE_R > EE_N`, and `EE_R > EE_P`;
- `service_R >= service_B - 0.001`;
- the `R` direction versus `B` is positive on at least six of eight evaluation draws.

Any other outcome is `STOP_EXPECTED_ZR_FAST`. This fast screen may reject the route but may not establish efficacy or authorize a learner. If it passes, the only next step is a separately frozen fresh 4-world x 3-lineage gate. No threshold, seed, horizon, draw count, formula, lambda, compatibility rule, or sign may be tuned against this outcome.
