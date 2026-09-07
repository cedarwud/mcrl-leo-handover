# C3 intra-satellite bottleneck shadow result

Status: complete exploratory legacy-narrow sensitivity. No implementation,
reward, preregistration, training, manuscript, or deployment authority.

Date: 2026-08-27

## Receipts

- Frozen protocol SHA-256:
  `570fd476c42733fc91b1691501c682e2f8dcc21209c627682886d2955d4461f3`
- Runner SHA-256:
  `c9558d4db702bc3a84efc00b92e809f9a190409a9b6f286cb225e5ce52a40706`
- JSON result SHA-256:
  `15c8399b22f027cc20f44bccb43b78b2d9feee48bfff23d53e39c52fde922a72`
- Evaluation seed: `2026082701`
- Reference: completed legacy Main checkpoint, masked-greedy Q1-only action.
- Current analysis source hash did **not** equal the launched training source
  hash; all findings are therefore sensitivity evidence only.

## Frozen classification

`SUPPORT_PRESENT_SHADOW_ONLY`

Across 100 users and ten steps:

| Quantity | Result |
|---|---:|
| user-steps censused | 1,000 |
| source-qualified focal states | 9 |
| candidate alternatives scanned | 21 |
| certified alternatives | 20 |
| candidate rejected for destination headroom | 1 |
| certificate failures | 0 |

The 20 certified alternatives came from nine distinct focal user-steps. Every
one changed `NONE` to `phi1`, preserved the complete served vector and active
beam set, and strictly reduced system power.

## Power certificate

For every retained candidate,

```text
Delta P_system
  = S(p_source_next) - S(p_source_max) < 0.
```

- mean power change: `-0.4747927373 W`
- median power change: `-0.2649297510 W`
- range: `[-1.1431034299, -0.0445413963] W`
- largest absolute identity residual: `8.97060203897e-14 W`

This closes the algebra/engineering support question for this one legacy seed,
not population coverage or learnability.

## Post-retention EE diagnostic

The outcome-blind certificate guarantees only the denominator direction. The
descriptive outcomes confirm that this is insufficient for EE:

| Outcome | Result |
|---|---:|
| candidates with positive immediate EE change | 5 / 20 |
| candidates with negative immediate EE change | 15 / 20 |
| mean immediate EE change | `-569629.0786 bit/J` |
| median immediate EE change | `-338605.2308 bit/J` |
| candidates with positive throughput change | 2 / 20 |
| candidates with negative throughput change | 18 / 20 |
| mean throughput change | `-258481089.7 bit/s` |

These rows were not selected by their outcomes, but the same seed may not now
be used to tune and validate a rate-safety rule. A physically justified
pre-outcome throughput proxy must be frozen and checked on different seeds.

## State and claim ceiling

The live 112-dimensional Main state omits segment-start gain and exact current
link/beam power. The certificate therefore needs an exact training-only mask,
and C3-to-Main transfer still requires a separate representability gate.

The valid conclusion is:

> A sparse one-user intra-satellite power-relief support exists and its live PA
> identity is exact, but a power-only candidate rule is not yet an EE mechanism.

Do not claim C3 effectiveness, R3 learnability, held-out EE gain, or
Multi-Catfish synergy from this result.
