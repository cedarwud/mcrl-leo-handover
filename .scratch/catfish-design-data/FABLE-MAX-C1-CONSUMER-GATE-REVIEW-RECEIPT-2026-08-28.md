# Fable Max C1 consumer-gate review receipt

Date: 2026-08-28  
Mode: read-only; no file edits, subagents, web use, or training  
Resolved model: `claude-fable-5`  
Effort: `max`  
Session: `5b3ae895-6be0-496a-899a-d4a13aa520f4`  
API duration: `866879 ms`  
Stop reason: `end_turn`

Command contract:

```text
claude -p <bounded C1 consumer-gate scientific/code review> \
  --model fable --effort max --output-format json \
  --dangerously-skip-permissions
```

The reviewer inspected the current C1 consumer specification/runner and their
direct Main, routing, corpus, parity, and evaluation dependencies. It ran 27
relevant tests and reported no P0 implementation bug for the narrow claim
ceiling `C1_ROUTE_FOR_ONE_SEED_4EP_DEVELOPMENTAL_PREVIEW_ONLY`.

Verified strengths:

- F111 and A011 are dose-matched informed versus neutral C1 carriers; the
  contrast is source informativeness, not C1 presence versus absence.
- C2/C3 shadow trajectories cannot reach Main replay, gradients, or Main RNG.
- Main receives one complete unshaped C1 bundle unit beside one complete Main
  unit; ACRM and corpus prefill remain specialist-private.
- evaluation reconstructs a fresh Main-only trainer/environment per paired
  seed and reports ratio-of-sums EE with the frozen service guard.

Required before seed freeze:

1. bind `sweep_evaluation.py` and `check_zero_dose_parity.py` hashes;
2. define and recompute a deterministic gate-seed derivation rule; and
3. add the corpus-generating checkpoint's embedded train/environment/mobility
   seeds to the forbidden seed set.

Recorded limitations, not P0 bugs:

- four episodes and one training seed support only a developmental screen;
- the five paired evaluations are new seeds on the TRAIN ephemeris split, not
  temporal TEST-split generalization;
- informed C1 is a composite EXP/source-selection/ACRM treatment;
- routed Main uses atomic bundle units rather than the baseline row-replay
  learning unit; and
- a later preview must use a separately frozen seed namespace or explicitly be
  identified as the gate's selected informed branch.

This model review is advisory evidence, not scientific acceptance or a route
authorization.
