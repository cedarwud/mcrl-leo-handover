# Multi-Catfish MCRL V0.4 C3 confirmatory result

Date: 2026-09-01  
Status: `CONFIRM_C3`

## Sealed authority

- preregistration:
  `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-PREREG-2026-09-01.md`;
- result artifact:
  `artifacts/multi-catfish-v04-c3-confirmatory-20260901-r1`;
- evaluator SHA-256:
  `299fd7733c96b14b609137d70dd09c49c32176f301027c0c4c8ab6d1b735c3e4`;
- result SHA-256:
  `bb1a46a8a782a5fb6d3c37391c17866ac0dbbb9bcc7c42bd2c9d8a9f0dd396dd`;
- result-seal SHA-256:
  `d569049cf648d5d261306ad27d850755070b851a8aecf723f0ebd60d085ee54b`;
- receipt-only verification: pass locally and on the Ubuntu server;
- TEST opened: no;
- episode or source training: no.

The block used the frozen gate-selected rung-100 hybrids, evaluation seeds
`2026092501`--`2026092530`, three initialization seeds, 100 users, and ten
decision steps.  Each of the 30 physical worlds used the same environment,
mobility, episode start, and keyed-fading field for both arms and all three
initializations.  The result therefore contains exactly 90 rows per arm and
180 simulator episodes.

## Confirmatory endpoint

| Measure | FULL | DROP-C3 | FULL relative to DROP-C3 |
|---|---:|---:|---:|
| Pooled ratio-of-sums EE (bits/J) | 72,350,498.70 | 59,687,093.60 | +21.216% |
| Total delivered bits | 595,943,407,146,917.9 | 530,190,845,338,943.6 | +12.402% |
| Total energy (J) | 8,236,894.26 | 8,882,839.04 | -7.272% |
| Served fraction | 97.2522% | 97.0056% | +0.2467 percentage points |

Initialization-level EE contrasts were `+150.800%`, `-6.298%`, and
`+12.734%`.  Thus two of three initialization-specific contrasts were
positive; all three initialization-specific served-fraction contrasts were
nonnegative.

All 30 physical-world pooled EE contrasts were positive.  The median absolute
per-world difference was `12,812,574.83` bits/J.  The deterministic 10,000-
replicate paired-world bootstrap interval for the pooled percentage contrast
was `[+18.619%, +23.996%]`, with median `+21.234%`.  One physical world had a
negative served-count difference; this is the preregistered nonfatal
diagnostic, while pooled and initialization-level service non-inferiority both
passed.

## Frozen decision

All preregistered conditions passed:

1. pooled FULL EE was greater than DROP-C3;
2. at least two of three initialization EE contrasts were positive;
3. median per-world EE contrast was positive;
4. the paired-world bootstrap 95% lower bound was positive;
5. pooled served fraction was non-inferior and at least two of three
   initialization served-fraction contrasts were nonnegative.

The scientific status is therefore `CONFIRM_C3`, not merely promising.  This
confirms the marginal contribution of the frozen C3 head under the declared
fresh TRAIN-only physical-world block.  It is not a TEST-split result and does
not by itself establish the contributions of C1 or C2.

## Promotion boundary

This result authorizes one separately sealed frozen-policy evaluation with
`FULL`, frozen Main baseline, `DROP_C1`, `DROP_C2`, and `DROP_C3`.  It does not
authorize additional Q3 updates or a 1500/3000/9000 training run.  The exact
evaluator named above must remain byte-frozen so that this result continues to
pass receipt-only verification; any operational improvements belong in a new
versioned evaluator.
