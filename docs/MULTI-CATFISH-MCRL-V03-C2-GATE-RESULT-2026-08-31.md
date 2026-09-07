# Multi-Catfish MCRL V0.3 C2 keyed gate result

Date: 2026-08-31  
Status: **sealed G-C2 result; INDETERMINATE; no training authorization**

## 1. Frozen authority

- Gate preregistration: `artifacts/c2-v03-gate-20260831/prereg.json`
- Preregistration SHA-256:
  `3bb277ac5e50c32a4a45499e675dd40cdf1231ffec88d60464355e5dda70828f`
- Result: `artifacts/c2-v03-gate-20260831/result.json`
- Result SHA-256:
  `f8fa59c3b274e730c0029d4b2ecfacf9c1c9f041f29863a3983bda02d904a2bd`
- Baseline preregistration digest:
  `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`
- Ephemeris file-set SHA-256:
  `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`
- Checkpoint SHA-256:
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`
- Fixed TRAIN-only multiplier:
  `lambda_0 = 84,994,621.12635651 bit/J`, hex
  `0x1.443a8f481639ap+26`.
- Fading authority: `keyed-branch-independent-v1`.

All five seed schedules were sealed before any temporal target was scored.
The result embeds per-file source receipts and their aggregate manifest digest.

## 2. Prospective adjudication

The preregistered gate outcome is:

`INDETERMINATE`

| Quantity | Observed | Frozen requirement | Status |
|---|---:|---:|---|
| seeds with a service-safe positive complete trace | 5/5 | at least 4/5 | pass |
| distinct positive seed-anchor digests | 10 | at least 4 | pass |
| service-safe positive complete traces | 15 | diagnostic count only | not a decision threshold |
| total attempts | 41 | at least 30 | pass |
| complete traces | 27/41 = 0.6585366 | at least 2/3 | fail by one complete trace |
| right-censored traces | 14/41 = 0.3414634 | at most 1/3 | fail by one complete trace |
| complete traces per seed | 4 to 7 | at least 3 | pass |
| service-safe complete traces per seed | 4 to 7 | at least 2 | pass |
| instrument errors | 0 | 0 | pass |
| Main networks/replay/checkpoint unchanged | yes | required | pass |

The positive-replication condition passed, but the completion and censoring
conditions did not. The old gate must not be relabelled `GO`, and its frozen
thresholds must not be relaxed after observing the outcomes.

## 3. Censor diagnosis

All 14 censored traces have the same declared support-loss reason:
`focal_hold_expired`.

- six expired at forecast offset 1;
- eight expired at forecast offset 2;
- every censor occurred on the candidate branch;
- there were no numeric, seal, keyed-fading, replay, checkpoint, or other
  instrument errors.

This is evidence that the fixed-length incumbent-hold intervention is too
rigid for a material share of departure anchors. It is not evidence that the
fixed-lambda temporal surplus is absent. All 27 complete traces preserved the
service guard, and service-safe positive \(\zeta_2\) occurred in every seed.

All completed branches used the `incumbent-hold` opening rule. The
`max-lagged-candidate-sinr-rival` fallback was not naturally exercised by this
gate, so this result cannot validate that fallback route.

## 4. Claim ceiling

This result supports only the following statement:

> Under the frozen Main checkpoint, TLE scene contract, fixed TRAIN-only
> multiplier, and keyed common fading, the C2 incumbent-hold fork exhibits
> repeatable service-safe positive downstream EE-surplus headroom in all five
> inspected seed worlds, but the preregistered fixed-hold viability gate is
> indeterminate because physical support censoring narrowly exceeds its limit.

It does **not** prove target observability, learnability, Q2 pivotality,
held-out ratio-of-sums EE improvement, superiority over a neutral source,
deployment safety, or overall Multi-Catfish efficacy.

## 5. Current consequence

- Do not start a 10--20 EP learnability pilot, short-EP ablation, or longer
  training from this receipt alone.
- Do not discard C2 as ineffective: its positive replication condition passed
  in 5/5 seed worlds.
- Select and preregister a prospective response to physical hold expiry before
  collecting another decision dataset. The old schedules and outcomes remain
  immutable evidence and cannot be pooled into the next decision rule unless
  that use is declared prospectively.
