# Multi-Catfish MCRL V0.23 C3 method freeze

Date: 2026-09-05  
Decision: `METHOD_CORE_FROZEN`  
Implementation boundary: `PASS_V023_IMPLEMENTATION_BOUND`  
Gate execution: `NO-GO`

## Frozen paper-visible method

Chapter 4 may now describe C3 as the two-user Local Coalition-Shapley Spatial
Residual Surplus (LC-SRS) mechanism defined by the four matched current-slot
profiles 00, 10, 01, and 11. Its target remains

\[
z_{3,i}=e_i+\frac{\Psi}{2},
\qquad
\sum_{i=1}^{2}(\ell_i+z_{3,i})=G(11)-G(00).
\]

The privileged four-profile evaluator and common random field exist only in
the training teacher. Deployment uses a deterministic relational C3View, one
shared 67-64-64-1 token scorer, one reference-centred scalar Q3 surface, and
the unchanged single masked argmax of Q1+Q2+Q3. There is no coordinator,
auction, joint decoder, fallback, or post-selection repair.

The binding method contract is
`docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`.

## Verified at freeze

1. Independent specification audit returned `PASS_V023_METHOD_SPEC`.
2. Independent final implementation audit returned
   `PASS_V023_IMPLEMENTATION_BOUND` after resolving its three major findings:
   committed-temporal semantics, full-profile action binding, and fit-receipt
   SHA validation.
3. Native observation provenance, detached Q1/Q2 state/event/model binding,
   the physical predecision encoder, outcome-blind topology, exact four-profile
   teacher, unique source assembler, fold-safe placebo, fixed learner, and
   three-route deployment seam are implemented.
4. Exact feature-order tuples, transforms, masks, sentinels, architecture, and
   content/config/schema digests are code-bound.
5. Focused W182--W192 tests report 62 passed, including the exact missing-
   incumbent temporal sentinel, teacher-baseline drift rejection, post-fit
   receipt construction, and same-occupancy/different-victim-geometry behavior.

## Still open before any gate or episode training

1. Build the V0.23 gate runner, preflight manifest, and independent verifier
   around the now-bound modules.
2. Execute the frozen eight-world, three-seed, 48-fit TRAIN-only gate on the
   Ubuntu server and verify its common-field and leave-one-world-out receipts.
3. Freeze a separate episode-screen contract only if the gate permits it.

## Claim ceiling

This freezes the C3 method for Chapter 4; it does not establish learnability,
composition benefit, C1/C2 qualification, FULL-over-ablation ordering, or EE
efficacy. Those remain Chapter 5 evidence questions.
