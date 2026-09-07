# Multi-Catfish MCRL V0.15 C3 learned-context oracle preregistration

Status: `FROZEN_BEFORE_OUTCOME`

Claim ceiling: `TRAIN_DEVELOPMENT_ORACLE_ONLY`

## Question

Does the unchanged current-slot ZR C3 oracle add positive canonical
ratio-of-sums energy efficiency when its matched background is the actual
frozen learned `Q1 + Q2` policy rather than the exact OPS3 teacher surface?

This is the one remaining physical-context gate before another Q3 learner is
allowed. It is not learner training, held-out evaluation, or evidence of final
algorithm efficacy.

## Frozen design

- Split: `TRAIN`; the `TEST` split remains unopened.
- Arms: `DROP_C3` and `FULL_ZR` only.
- Users: 100.
- Episode length: 10 decisions.
- World seeds: `2026105001`, `2026105002`, `2026105003`, `2026105004`.
- Q1 lineages: `2026092101`, `2026092102`, `2026092103`, using the same frozen
  Q1 checkpoints as V0.13.
- Q2 initializations paired with those lineages: `2026108101`, `2026108102`,
  `2026108103`, using the sealed V0.14 rung-3000 checkpoints.
- Fading: one keyed common-random field per world, shared by both arms and all
  lineages.
- Action mask and deterministic native-index tie rule are identical in both
  arms.

At each predecision anchor, exact OPS3 projection may be constructed only to
encode the frozen learned Q2 input state. Its oracle `q2_values` must not enter
either arm's action score. The background is exactly

```text
b = masked_argmax(Q1 + Q2_hat)
```

where `Q2_hat` is the frozen learned Q2 checkpoint. `DROP_C3` executes `b`.
`FULL_ZR` measures the existing V0.13 current-slot ZR surface against that same
joint background and executes

```text
masked_argmax(Q1 + Q2_hat + O3_ZR)
```

No C3 formula, sign, scale, compatibility rule, energy rule, horizon, action
mask, or tie rule may change. There is no learner update, online tuning,
coordinator, auction, veto, route weight, or second executed action.

## Primary endpoint and gate

For every arm, accumulate canonical delivered bits and canonical network
energy over the full ten-step trajectories and compute exactly one pooled
ratio of sums:

```text
eta = sum(bits) / sum(energy)
```

Let `Delta = eta_FULL_ZR / eta_DROP_C3 - 1`. The gate passes only when all of
the following hold:

1. pooled `Delta > 0`;
2. at least 2 of 3 lineage-pooled directions are positive;
3. at least 3 of 4 world-pooled directions are positive;
4. pooled served user-steps for `FULL_ZR` are not below `DROP_C3`;
5. every changed FULL action has strictly positive compatible ZR credit;
6. all paired-world, common-field, state/RNG immutability, mask, reference-zero,
   and canonical-accounting checks pass.

The only decision tokens are:

- `GO_MATCHED_C3_LEARNER_SOURCE`
- `STOP_ZR_IN_LEARNED_Q2_CONTEXT`

## Consequence

On `GO_MATCHED_C3_LEARNER_SOURCE`, the next source panel must follow the same
frozen `Q1 + Q2_hat` behavior and construct C3 labels against its joint
background. A Q3 learnability gate then precedes any 100-episode rollout.

On `STOP_ZR_IN_LEARNED_Q2_CONTEXT`, do not add thresholds, coalition branches,
state blocks, or longer training to rescue this outcome. Report that the
current three-head design is not training-ready and return to method-level C3
design.
