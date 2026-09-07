# Multi-Catfish MCRL V0.4 C3 bounded screen result

Date: 2026-09-01  
Status: `SCREEN_COMPLETE`; promising primary signal, not confirmatory efficacy

## Sealed authority

- source: `artifacts/multi-catfish-v04-c3-source-20260901-r2`
- learnability gate: `artifacts/multi-catfish-v04-c3-learnability-20260901-r2`
- bounded screen: `artifacts/multi-catfish-v04-c3-500-update-screen-20260901-r1`
- screen result SHA-256:
  `ab232f72e562e5a9aa4b68ec8074c5556691ffb1272ae92ec5efd651e76a2177`
- primary receipt SHA-256:
  `822630c75aaa2681bcda23eb007df62128b818a6fde63d050acfe90c18e1e9d5`
- TEST opened: no

The gate selected fresh Q3 rung 100 with mean stronger-null skill
`0.12362866324697346`, positive in all three initializations.  The bounded
screen used 10 fresh TRAIN evaluation seeds, three initialization seeds,
100 users, 10 decision steps, and matched environment, mobility, and keyed-
fading randomness for `FULL = Q1 + Q2 + Q3` versus `DROP_C3 = Q1 + Q2`.

## Primary selected-rung result

The primary result evaluates the sealed gate-selected hybrid before any
additional Q3 source-training update.

| Measure | FULL | DROP-C3 | FULL relative to DROP-C3 |
|---|---:|---:|---:|
| Pooled ratio-of-sums EE (bits/J) | 71,929,644.06 | 59,580,102.86 | +20.73% |
| Total delivered bits | 196,490,491,250,667.4 | 172,973,337,841,228.34 | +13.60% |
| Total energy (J) | 2,731,703.93 | 2,903,206.43 | -5.91% |
| Served fraction | 97.207% | 96.963% | +0.243 percentage points |

Initialization-level EE contrasts were `+147.22%`, `-7.56%`, and `+11.70%`.
Nineteen of 30 matched episode pairs were EE-positive; the median paired
episode contrast was `+13.00%`.  All three initialization-level pooled served
fractions increased.  The preregistered zero-loss service guard nevertheless
failed because one of 30 matched pairs served 916 rather than 920 user-steps;
the pooled service guard passed, 29,162 versus 29,089 served user-steps.

This is a promising positive C3 signal, but it is not a robust or paper-level
efficacy claim: one initialization is EE-negative, 11/30 episode pairs are
negative, the strict per-pair service guard fails, and no TEST split was
opened.

## Additional-update trend

The following points are exploratory diagnostics.  They start from the sealed
rung-100 Q3 and apply the stated number of additional complete Q3 TRAIN-batch
updates.  They are not simulator episodes.

| Additional Q3 updates | Pooled EE contrast | Initialization EE contrasts | Positive pairs | Median pair contrast | Served-fraction difference | Service guard |
|---:|---:|---|---:|---:|---:|---|
| 100 | +3.70% | +197.34%, -25.75%, -6.98% | 11/30 | -9.19% | -4.800 pp | fail |
| 200 | +5.91% | +188.29%, -17.28%, -6.72% | 11/30 | -6.83% | -4.747 pp | fail |
| 300 | +13.03% | +179.76%, -8.96%, -5.53% | 12/30 | -4.74% | -2.440 pp | fail |
| 400 | +10.60% | +192.93%, -9.79%, -12.56% | 12/30 | -7.22% | -2.613 pp | fail |
| 500 | +4.24% | +209.73%, -20.35%, -9.25% | 11/30 | -6.92% | -5.167 pp | fail |

The positive pooled values after additional training are driven by one
initialization.  Two of three initializations are negative at every additional
checkpoint, the median matched episode is negative, and service degrades.
Therefore the 100--500 additional-update checkpoints are rejected as
deployment candidates.

## Decision and claim boundary

1. Retain only the sealed gate-selected rung-100 Q3 as the V0.4 C3 candidate.
2. Do not perform further Q3 source training and do not select an exploratory
   checkpoint using these EE outcomes.
3. Do not claim that C3 has proven EE efficacy.  The allowed statement is that
   the redesigned C3 passed its learnability screen and produced a promising
   positive marginal-EE signal in the first bounded matched screen.
4. The next scientific step is a preregistered confirmatory evaluation of the
   frozen rung-100 hybrid on a larger fresh non-TEST seed block, followed by a
   separately authorized three-route ablation.  It is evaluation, not another
   C3 redesign or additional Q3 training.
5. No 1500/3000/9000 promotion follows from this result.
