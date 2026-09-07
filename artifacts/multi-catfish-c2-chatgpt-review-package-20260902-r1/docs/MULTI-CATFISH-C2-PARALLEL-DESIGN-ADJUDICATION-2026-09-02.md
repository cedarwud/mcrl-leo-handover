# Multi-Catfish C2 parallel-design adjudication

Date: 2026-09-02  
Status: `PREOUTCOME_COMPARISON_RULES__NO_C2_SELECTED`  
Claim ceiling: design control only; no training or EE-efficacy claim

## Purpose

Compare two independent C2 design routes without allowing either route to
change the success definition after seeing its own result:

- `FABLE-CLEANROOM`: the fresh Fable 5.1 takeover route;
- `CODEX-PROJECTED-SHAPING`: a decision-time deterministic orbital-trajectory
  EE-shaping route that does not import downstream actions across branches.

The routes may change the C2 target, state, source mechanism, and learner. The
canonical network ratio-of-sums EE endpoint is frozen. C1 maps only to Q1, C2
only to Q2, and C3 only to Q3. Deployment remains one common safe mask, direct
unweighted `Q1 + Q2 + Q3`, one argmax, and one executed Main action.

## Evidence stages

### Stage 1: route-local feasibility

Each route must provide all of the following before a learner is fitted:

1. a physical path from current action to future delivered bits and/or network
   energy;
2. an exact target in the same fixed-`lambda0`, shared-`kappa` output units as
   Q1 and Q3;
3. decision-time, action-aligned inputs sufficient to predict the target;
4. no duplication of C1's focal opening surplus or C3's non-focal opening rate
   externality;
5. complete native current-action support with no post-outcome row deletion,
   fallback, sign clipping, or action import from another branch;
6. nonzero within-anchor action spread and an oracle action change on fresh
   TRAIN-design anchors.

A design that fails any item is revised or retired before training. Every
two-Catfish combination need not be positive at this stage.

### Stage 1b: no-training interaction screen

As soon as a candidate supplies a valid oracle Q2 surface on the common scale,
freeze Q1 and Q3 and evaluate matched, fresh development worlds using

`P13 = Q1 + Q3`, `P12 = Q1 + Q2*`, `P23 = Q2* + Q3`, and
`P123 = Q1 + Q2* + Q3`.

The binding directions are:

- `eta(P123) > eta(P13)` for a positive C2 marginal;
- `eta(P123) > eta(P12)` for C3 to remain positive with the new C2;
- `eta(P123) > eta(P23)` for C1 to remain positive with the new C2.

All use raw matched ratio-of-sums EE and the existing service guard. Pair and
singleton contrasts beyond these three are interaction diagnostics, not extra
requirements. A tiny screen establishes direction only, not efficacy.

### Stage 2: learnability and learned integration

Only a Stage-1/1b survivor may train a small Q2. It must beat zero and
action-only nulls under world/anchor-disjoint evaluation, then repeat the
three marginal directions with learned Q2 on fresh matched development worlds.

### Stage 3: confirmatory evidence

Only the selected learned candidate receives a preregistered held-out matched
evaluation with uncertainty and service guards. Episode trends follow only
after the bounded gates. No 9000-episode run may start without first informing
the user.

## Selection rule

Scientific validity outranks implementation convenience and narrative
simplicity. Among candidates passing the same gates, prefer in order:

1. stronger and more stable three-marginal EE directions;
2. better held-out ranking relative to the strongest null;
3. wider native coverage and fewer exclusions;
4. simpler state, target, and source mechanism;
5. lower compute cost.

Do not merge routes merely to preserve both stories. A hybrid is considered
only if each component has an independently identified causal role and the
combined formula remains on the common direct-sum scale.

## Current boundary

- Existing V0.7 C2 is retired as a learner candidate.
- Existing C1 is comparatively robust but must be rechecked with the selected
  C2.
- Existing C3 is confirmed only in its old-Q2 context and must pass the
  `P123 > P12` check before any long training.
- No new C2 is selected and no long training is authorized by this document.
