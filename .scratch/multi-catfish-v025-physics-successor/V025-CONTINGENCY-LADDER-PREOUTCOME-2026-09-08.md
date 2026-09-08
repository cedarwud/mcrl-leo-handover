# V025 contingency ladder — declared before the a-r0 regime map exists (controller, 2026-09-08 ≈ 19:00 UTC; sealed)

Purpose: if the primary path fails at any rung, the next step is already declared, so no choice is made after seeing an outcome. Nothing here changes the primary (`a-r0`, v1.1–v1.5) or its admission rule. Each rung names the failure it answers, the pre-declared response, and what runs in parallel now.

## Rung 0 — claim ladder for C3 (pre-registered; both levels are always measured)
- **Level B (the owner's requirement, primary):** the C3 layer raises realised pooled EE over the C1 + C2 policy under the same deployable information, catalogue and 10 s compute budget: FULL(S3 or S0) vs DROP_C3, relative gain lower bound > +0.5 %, QoS margins met. Mechanism is reported, not required: the S_UNI comparison and the matched-anchor singleton/interaction decomposition say how much is exact joint re-evaluation of single-user alternatives and how much is multi-user coordination.
- **Level A (secondary, stricter):** in addition, FULL > the information-matched S_UNI comparator with decision-relevant nonadditivity — the "coordination beyond exact unilateral re-evaluation" claim.
- **Level C (tertiary):** learned S3 matches S0 at lower compute (acceleration), reported only if A/B hold for S0.
Wording is fixed now: a Level-B-only result is described as "exact/learned joint re-evaluation layer", never as "coordination".

## Rung 1 — a-r0 shows no joint headroom or negative factor marginals (physics regime)
- **Response:** the pre-declared **regime sensitivities** R1–R6 (system-model parameters, not tuning), run in this order as the first exploratory settings after a-r0, each with the full 13 arms and the same admission certificates reported: R1 rate target r* = 100 Mbit/s (occupancy pressure); R2 users = 150 (density); R3 circuit power 1.0 W per active chain (activation cost high → consolidation regime); R4 circuit power 0.1 W (activation cost low → balancing regime); R5 `a′-r0` (FDM sibling, already in the matrix); R6 `a-γ0` (fixed-SINR sibling, already in the matrix). Admission may be granted on a regime setting **only** if declared here and only for the claim "in regime R_k"; the primary remains a-r0 for the paper's main result unless a-r0 fails and R_k passes, in which case the paper states the regime condition explicitly.
- **In parallel now:** the synthetic mechanism map R2 (occupancy × density × coupling grid, five architectures) runs on the stage-4b engine and scores expectations E1–E4 before any real regime setting opens; stage 4b exposes R1–R4 as sealed settings with digests; the a-r0 launcher queues R1–R6 immediately after `AR0-DONE` within the budget.

## Rung 2 — headroom exists but the learned S3 fails (T2 or held-out comparison)
- **Response:** C3 is delivered as the exact coordinator S0 (declared alternative in contract v1 §C2); the claim is Level B/A with S0; the learned contribution is the C1/C2 heads; a learned proposer for S0's catalogue is optional and reported as Level C. No redesign of features or catalogues after seeing S3 fail.

## Rung 3 — C2 fails in the corrected physics (its old-physics sign was regime-dependent)
- **Response:** C2 sensitivity on the forecast horizon (offsets {1, 2, 3} steps; sealed now) as exploratory settings; the primary C2 definition stays three offsets. A negative C2 at the primary horizon is reported as such; a positive one at another horizon is a regime/horizon statement, not a replacement.

## Rung 4 — compute or timeline failure
- **Response:** the sealed thinning order (compute-budget decisions) and concurrency 20; the vertical slice numbers (SMOKE) never substitute for the matrix.

## Rung 5 — no regime in the model gives Level B
- **Response:** the study reports C1 and C2 with the retained three-Catfish architecture and C3 as an evaluated layer with its measured (non-positive) marginal under the declared scope; no further legacy diagnostics; the owner is consulted before any change to the system model.

Seal: sha256 in the companion `.sha256` file.
