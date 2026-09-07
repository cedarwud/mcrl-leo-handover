# R2 conditional time-only overlay receipt

## Material Passport

- Status: `LEGACY_NARROW_CONDITIONAL_SENSITIVITY_ONLY`
- Input: `.scratch/catfish-oracle-gate/arlp-shadow-confirmation-seeds-10-k10-v4.json`
- Input SHA-256: `8efb3068537a10dd8896d07d5410986976b40a6181532ded876648c4474e01a2`
- Analysis: `.scratch/catfish-design-data/analyze_r2_time_overlay.py`
- Analysis SHA-256: `8984d103dadb1524d4632ba654b2abb15029fff058806ec5cd32261375bc4d4b`
- Runtime/reward/training authority: none

## Conditional overlay

The read-only overlay applies the proposed time-only special case

```text
r2_temporal,u = -R_u*T_u / (P_system*30.08)
```

to 1,000 previously sampled legacy-narrow reference user-decisions. It uses
`62/142 ms` interruption and `72/152 ms` full-delay sensitivity values, sets no
`E_HO`, and excludes `phi2` rows without a visible incumbent as unsourced
re-entry.

## Reproduced result

```text
sampled user-decisions                                  1000
conditionally scored                                     965
none / phi1 / served-to-served phi2                220 / 45 / 700
unsourced re-entry excluded                               35
mean interruption r2 over scored rows             -3301.991588 bit/J
mean full-delay r2 over scored rows                -3539.145423 bit/J
mean |nonzero interruption r2|                      4277.076353 bit/J
mean reference r1 over the same scored rows       1009716.365872 bit/J
mean |r2| / mean r1                                    0.00327022
```

## Interpretation and claim ceiling

The direct time pathway is nonzero in the existing sampled data, but its mean
magnitude is about 0.327% of mean focal R1 on the scored rows. This supports
testing a calibrated temporal specialist rather than assuming the old event
count is sufficient. It does not establish that C2 can change decisions or
improve EE.

The event-to-procedure mapping is conditional, `E_HO=0` is only a lower-bound
sensitivity, re-entry remains unscored, and all rows use legacy-narrow geometry.
No causal, primary-parameter, training, or Catfish-effectiveness claim follows.
