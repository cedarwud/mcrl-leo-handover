# E1 action-shared context screen (validation only)

Status: non-authoritative diagnostic. The held-out test and EE endpoint remain
unopened. Physical C1/C2/C3 source definitions are unchanged.

Three permutation-equivariant variants were compared on the same frozen
train/validation rows and three initialization seeds:

- `local`: eight features for the candidate action plus four temporal globals;
- `mean`: `local` plus the mean of each feature over the candidate set;
- `meanmax`: `local` plus candidate-set mean and maximum;
- `deepset`: `local` plus a learned 32-dimensional mean-pooled set encoding.

The prior local-only result is included for comparison. At common rung 30:

| Variant | C1 skill vs action-only | C2 skill vs action-only | C3 skill vs action-only | Interpretation |
|:---|---:|---:|---:|:---|
| local | 0.2711 | 0.2659 | 0.1298 | simplest; best C1 |
| mean | 0.2477 | 0.2681 | 0.1286 | no useful C3 gain |
| meanmax | 0.2440 | 0.2669 | 0.1532 | best C3, still below 0.20 |
| deepset | 0.2402 | 0.2656 | 0.1395 | slower without material gain |

For `meanmax`, every initialization has positive rung-30 skill:

| Initialization | C1 | C2 | C3 |
|---:|---:|---:|---:|
| 2026091101 | 0.2390 | 0.2661 | 0.1590 |
| 2026091102 | 0.2402 | 0.2651 | 0.1628 |
| 2026091103 | 0.2528 | 0.2694 | 0.1379 |

Train-to-validation action-main-effect fractions at `meanmax` rung 30 are
`-0.1369`, `0.2345`, and `0.0155` for C1/C2/C3 respectively, all below the
contract ceiling of `0.80`. Negative finite-sample estimates are interpreted
as no detected fixed-slot explanatory power, not as negative variance.

Narrow conclusion: set context does not justify the additional DeepSets
complexity. `meanmax` modestly improves C3 but does not by itself de-risk the
preregistered `skill >= 0.20` held-out point gate. Keep the test sealed while
distinguishing C3 coverage limitation from missing observable context.
