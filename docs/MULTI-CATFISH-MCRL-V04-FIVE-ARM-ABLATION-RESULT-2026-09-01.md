# Multi-Catfish MCRL V0.4 five-arm frozen-policy ablation result

Date: 2026-09-01  
Status: `MULTI_CATFISH_NOT_ALL_CONFIRMED`

## Sealed authority

- preregistration:
  `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-PREREG-2026-09-01.md`;
- result artifact:
  `artifacts/multi-catfish-v04-five-arm-ablation-20260901-r1`;
- evaluator SHA-256:
  `d58a75a902db121f0ccacaf26a80e72582069a84b86c7a7f95345cfcba0c4609`;
- W89 contract-test SHA-256:
  `b19d1a02870c2aef34901cd5764f16fc12693cb896612763818406e058a1b5e5`;
- work-order SHA-256:
  `d58224c63e8a09e82b44e455af9c34454596660d15ddd1e91bad1ec4bb5a3eac`;
- result SHA-256:
  `9142da31690927fe853765b9dfc0c807d4202738784961b44be393a77c608224`;
- result-seal SHA-256:
  `1e554bf5997d4571193b7f04312c60d11a7d7e5f497128ba1c6bd45ce32d84e0`;
- receipt-only verification: pass on the Ubuntu server and locally;
- TEST opened: no;
- episode, route, or source training: no.

The frozen block used 30 fresh TRAIN-only physical-world seeds, three frozen
initializations, 100 users, and ten decision steps.  `FULL`, `DROP-C1`,
`DROP-C2`, and `DROP-C3` each contain 90 matched rows.  The frozen Main
baseline contains 30 rows and is comparison-weighted exactly as preregistered.
The run completed all 390 simulator episodes in 890.92 seconds.

## Arm summaries

| Arm | Pooled ratio-of-sums EE (bits/J) | Served fraction | Rows |
|---|---:|---:|---:|
| FULL | 73,090,604.82 | 97.1567% | 90 |
| DROP-C1 | 20,612,362.03 | 91.2411% | 90 |
| DROP-C2 | 105,010,574.08 | 99.8122% | 90 |
| DROP-C3 | 59,924,982.89 | 96.9111% | 90 |
| Main | 93,206,395.06 | 99.8100% | 30 |

## Preregistered comparisons

| Comparison | Pooled EE contrast | Paired-world bootstrap 95% interval | Positive initializations | Positive worlds | Frozen decision |
|---|---:|---:|---:|---:|---|
| FULL vs DROP-C1 | +254.596% | [+243.956%, +266.153%] | 3/3 | 30/30 | `CONFIRM_C1` |
| FULL vs DROP-C2 | -30.397% | [-31.474%, -29.301%] | 0/3 | 0/30 | `C2_NOT_CONFIRMED` |
| FULL vs DROP-C3 | +21.970% | [+19.753%, +24.260%] | 2/3 | 30/30 | `CONFIRM_C3` |
| FULL vs Main | -21.582% | [-23.442%, -19.706%] | 0/3 diagnostic | 0/30 | `FULL_NOT_BETTER_THAN_MAIN` |

C1 initialization contrasts were `+95.238%`, `+317.335%`, and `+294.673%`.
C3 initialization contrasts were `+145.123%`, `-5.666%`, and `+14.111%`.
The negative C3 initialization is explicitly permitted by the frozen rule:
two of three initializations, the median physical world, the bootstrap lower
bound, and the service conditions passed.  This is direct evidence that the
gate does not require every individual contrast to be positive.

C2 failed for a qualitatively different reason.  Its initialization contrasts
were `-62.961%`, `-17.466%`, and `-20.249%`; all 30 physical-world EE
contrasts were negative, its entire bootstrap interval was negative, and all
30 physical worlds recorded a served-count loss.  This is a stable adverse
effect of the frozen Q2 deployment head in this block, not a rejection caused
by one noisy negative sample.

## Frozen decision

The scientific status is `MULTI_CATFISH_NOT_ALL_CONFIRMED`.  C1 and C3 are
confirmed and must remain frozen.  C2 is not confirmed, and the complete
three-Catfish policy is not better than the frozen Main baseline.  The present
candidate therefore cannot be promoted to a parameter sweep or a
1500/3000/9000 training run.

The result tests the marginal deployment contribution of the three frozen Q
heads.  It does not, by itself, identify whether C2's failure originates in
its target, source distribution, learned scale, state view, or interaction in
the unweighted score sum.  Those mechanisms require bounded diagnostic
evidence before any change.

## Bounded continuation and stop rule

Only one formula-first C2 remediation cycle is authorized:

1. diagnose C2 against the sealed matched rows without changing C1 or C3;
2. preregister one falsifiable short C2 probe and its decision rule;
3. if the probe supports a specific mechanism, implement one bounded C2
   correction and repeat a fresh frozen gate;
4. if that corrected candidate remains stably EE-negative, stop and archive
   the C2 formulation instead of changing seeds, checkpoints, thresholds, or
   repeatedly tuning to this outcome.

No passed route may be retrained merely to increase its observed effect.  Any
later 1500/3000 training requires a separate launch authority; the user must
be notified before any 9000-episode run.
