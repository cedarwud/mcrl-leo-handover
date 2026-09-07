# Reciprocal nominal-support receipt

## Material Passport

- Status: `LEGACY_NARROW_NOMINAL_SUPPORT_ONLY`
- Input: `.scratch/catfish-oracle-gate/arlp-shadow-confirmation-seeds-10-k10-v4.json`
- Input SHA-256: `8efb3068537a10dd8896d07d5410986976b40a6181532ded876648c4474e01a2`
- Analysis: `.scratch/catfish-design-data/analyze_reciprocal_nominal_support.py`
- Analysis SHA-256: `751f587ebca2f2720458569aa8dc5c3cd0604241a6ea293898a1aed070d390a0`
- Runtime/reward/training authority: none

## Question and method

Does the existing legacy-narrow, read-only receipt contain any nominal support
for the proposed reciprocal C3 exchange, before collecting a new outcome?

For each seed/step, the input contains ten previously sampled focal users. A
sampled pair counts only when both reference links were served, their reference
physical beams differ, each user's stored valid candidate keys contain the
other's reference beam, and the swap preserves each user's handover class as
derived from the stored visible incumbent. No action is newly evaluated.

## Reproduced result

```text
sampled steps                          100
sampled users per step                  10
nominal reciprocal pairs               198
steps with at least one pair             69
fraction of sampled steps              0.69
mean pairs per sampled step            1.98
maximum pairs in one sampled step        10
```

Pair-count histogram:

```text
0:31, 1:18, 2:14, 3:16, 4:14, 5:2, 6:2, 7:1, 9:1, 10:1
```

## Interpretation and claim ceiling

The reciprocal hypothesis is not eliminated by zero nominal candidate support
in this sampled legacy subset. This is not a pass of the C3 gate. The receipt
does not evaluate the swapped joint action, execution-time feasibility,
realised load/activation/handover invariants, power, service, EE, the proposed
primary geometry, learnability, or Catfish effectiveness. No population
support estimate is extrapolated from the ten-user-per-step sample.
