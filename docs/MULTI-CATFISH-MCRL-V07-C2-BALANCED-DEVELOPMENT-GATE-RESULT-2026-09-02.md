# Multi-Catfish MCRL V0.7 C2 balanced development-gate result

Date: 2026-09-02  
Status: `SUPERSEDED_BY_R14__V07_LEARNER_RETIRED`  
Claim ceiling: **HISTORICAL DEVELOPMENT RESULT ONLY; NOT A CURRENT C2**

> **Later-evidence override.** The provisional-lock language below is
> superseded. The subsequent R14 leave-one-anchor-out diagnostic, using the
> same six-anchor sources, found all three learned Q2 surfaces worse than the
> strongest held-out state-independent null (`0/3`). Independent review found
> no split, target-normalization, or null-leakage bug that reverses the result.
> R13 therefore records harm reduction to a near-zero effect; it does not lock
> `motion-one` or authorize longer training.

## 1. Scope and decision

This record reports the balanced R13 development screen for the V0.7 C2
focal-next candidate. The screen provisionally locks **motion-one** as the
post-R13 C2 public amendment. The earlier D2 preregistration predates this
amendment; this result does not retroactively validate D2. It is a development
gate result, not a formal efficacy result, a held-out confirmation, or a
Chapter 5 result. The artifact reports
`formal_training: false`, `efficacy_established: false`, and
`test_split_opened: false`.

The provisional core lock **passed its development gate**: the aggregate mean
and median were both positive, and two of the three lineage means were
positive. This does not establish EE efficacy. Longer trend and held-out
validation remain required, especially because q13-b is variable and q13-a
has a small service loss.

## 2. Balanced R13 result

The screen contains 18 lineage cells: 11 positive, 7 negative, and 0 zero.
The signed EE-improvement summary is:

| Statistic | Result |
|---|---:|
| Cells | 18 |
| Positive / negative / zero | 11 / 7 / 0 |
| Aggregate mean cell fraction | +0.04702566987904043% |
| Aggregate median cell fraction | +0.04582315918312263% |
| Pooled ratio-of-sums EE across all 18 cells | +0.04654311637537757% |
| Minimum | -1.1684185345256282% |
| Maximum | +1.0972712427983478% |

Per-lineage results, with positive and negative counts taken from the exact
18-cell artifact, are:

| Lineage | Mean cell fraction | Pooled ratio-of-sums EE | Positive cells | Negative cells | Service delta (user-steps) | Negative service pairs |
|---|---:|---:|---:|---:|---:|---:|
| q13-a | +0.026391098696652387% | -0.010883828446252037% | 4/6 | 2/6 | -3 | 3 |
| q13-b | -0.17085113407029523% | -0.15441903910283497% | 3/6 | 3/6 | +1 | 0 |
| q13-c | +0.28553704501076416% | +0.30641311325401116% | 4/6 | 2/6 | 0 | 0 |

The aggregate mean and median above are unweighted summaries of the 18
cell-level `ee_improvement_fraction` values. The pooled values instead sum
full and DROP-C2 total bits and total energy before taking each ratio; pooled
ratio-of-sums is the final EE convention. Thus the positive q13-a mean cell
fraction does not make its pooled ratio-of-sums positive. The q13-b spread
includes the global minimum, so its negative mean is not treated as a stable
direction. q13-a's service total is a small loss spread across three negative
service pairs; q13-b has one net positive service user-step and no negative
service pair; q13-c has no service delta.

## 3. Interpretation boundary

The result supports only this provisional development statement: the balanced
R13 screen meets the aggregate-sign and two-of-three-lineage-mean rule for a
provisional core lock. It does not support “the method improves EE,” a C2
efficacy claim, formal superiority, or any Chapter 5 numerical claim.

Before a formal claim, repeat the trend over a longer pre-registered screen
and evaluate on held-out matched data with the service guard. The q13-b
variability and q13-a service loss are explicit reasons that the development
lock is not a final scientific decision.

## 4. Immutable provenance

Balanced R13 artifact:

```text
artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-one-native28-balanced-sixanchor-sixseed-r13.json
SHA256: 277d8c2ae38541dba8148ba374a5196fbfcdb615e9a2c1112523bb8bcb44abb5
```

The three source artifacts and their SHA-256 digests are:

| Lineage | Source artifact | SHA-256 |
|---|---|---|
| q13-a | `p0-motion-native28-sixanchor-q13-a-r11.json` | `238715624eeb4ad435e91e5e4045799016f5771b62a8ce62362d33705770e0dd` |
| q13-b | `p0-motion-native28-sixanchor-q13-b-r11.json` | `93fc0fe4e2336be5694cdc0ec2084bde910e49fedbe5c0e07d5a452df0cf96e4` |
| q13-c | `p0-motion-native28-sixanchor-q13-c-r11.json` | `579fc247d1bf9d139b192ced993994e4fa088e21c8c093452fda21f12e4be738` |

All three source files are under
`artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/`.
