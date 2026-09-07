# Multi-Catfish MCRL V0.9 integrated oracle disposition

Date: 2026-09-02  
Status: **INVALIDATED BY POST-RUN CONTRACT AUDIT; NO LEARNER; NO TEST**

## Decision

The V0.9 execution is retained as development diagnosis, but it is not an
accepted oracle gate. The formal disposition is

`INVALID_CONTRACT__REDESIGN_C3_REMAINS_REQUIRED`.

No learner, short-episode training, TEST access, paper efficacy claim, or
active-method update is authorized from this run.

## What executed

- one previously unopened TRAIN world, seed `2026104501`;
- three frozen Q1 lineages: `2026092101`–`2026092103`;
- four arms and ten decisions per episode, for twelve independent episodes;
- exact source and runner copies sealed before execution;
- one common keyed fading field;
- zero optimizer or learner updates and zero TEST access.

All twelve server shards completed. An independent local merge reproduced the
same rows, summaries, decision, world identity, and field identity. The two
JSON files differ only in environment-specific path and timestamp receipts.

## Mechanically observed development directions

These values describe what the sealed V0.9 bytes produced; they do not repair
the contract defects below.

| Contrast | Pooled EE direction | Positive lineages | Service direction |
|---|---:|---:|---:|
| full minus drop-C1 | +14.7104% | 3/3 | 3/3 noninferior |
| full minus drop-C2 | +5.2745% | 3/3 | 3/3 noninferior |
| full minus drop-C3 | -11.0636% | 0/3 | 3/3 equal |

The full arm served 2,987 of 3,000 user-steps. Relative to drop-C3, adding
the V0.9 PNFE C3 changed roughly half of the decisions, reduced aggregate
delivered bits by 5.3951%, and increased aggregate energy by 6.3736%. Thus the
negative C3 direction is not a zero-exposure artifact or a service-count
collapse.

The simultaneous diagnostic exposed 36 samples and recorded zero joint-versus-
unilateral direction reversals. That observation does not rescue the failed C3
contrast.

## Contract defects found after execution

### D1 — h=0 diagnostic focal-action mismatch

The preregistration requires the arm-selected action plus the three smallest
other legal actions. The sealed runner instead used the Q1 gauge reference as
the focal action when forming the sampled set. Other users were fixed to the
arm-selected vector as intended. This invalidates the h=0 diagnostic's claimed
sampling contract, although it does not change executed arm actions or the
ratio-of-sums arithmetic.

The recorded, nonbinding ordering statistics were weak: pooled pairwise
agreement 51.39%, mean Spearman agreement approximately 0.0486, and top-action
agreement 20.14%. Because D1 changes the sampled action set, these figures are
diagnostic clues only.

### D2 — t=0 warm-start opening-service mismatch

The simulator uses `uniform-episode-length` segment warm starts. At (t=0),
the execution path reconstructs an action-specific historical segment-start
gain before applying recurrence power and the beam-power ceiling. The sealed
OPS-3 snapshot had no previous committed segment at the opening anchor and
therefore used the current gain as the start gain for every candidate. Its
opening-service surface was consequently cold-started at (t=0) and was not
execution-equivalent to the simulator's warm-start service gate.

D2 can change the first decision's C2/C3 oracle surfaces and selected actions.
It is therefore a gate-level contract violation, not merely a reporting
defect.

## Scientific interpretation

The run still supplies two useful falsification clues:

1. C1 and exact-persistence C2 remained mechanically positive in all three
   observed lineages even in the PNFE context.
2. The committed-background PNFE C3 did not complement them. Its action effect
   was large, but the realised numerator and denominator both moved in the
   wrong direction.

These clues support inspecting the C3 counterfactual background and
simultaneous-decision alignment. They do not authorize outcome-responsive
rescaling, sign reversal, route weighting, seed expansion, or reuse of the
V0.9 world for acceptance.

## Required next gate

Before another outcome is opened:

1. make the OPS-3 (t=0) start-gain and opening-service surface exactly match
   the simulator warm-start path;
2. fix the diagnostic action-set contract and add a regression test;
3. select and freeze one scientifically distinct C3 replacement or context
   correction from the failure analysis;
4. use a new TRAIN world, a new schema, and a new sealed artifact;
5. preserve the same three heads, common mask, unweighted sum, one masked
   argmax, one Main action, ratio-of-sums EE, and literal service guard.

The next gate must not rerun seed `2026104501` as confirmatory evidence.

## Receipts

- sealed package:
  `artifacts/multi-catfish-v09-integrated-oracle-20260902-r1/`;
- server merge:
  `artifacts/multi-catfish-v09-integrated-oracle-20260902-r1/merged/result.json`;
- independent local merge:
  `artifacts/multi-catfish-v09-integrated-oracle-20260902-r1/local-merge-verify/result.json`;
- sealed server result SHA-256:
  `35e20d1b0f3e16028619e1f80bcd046d25d2225d1761d07d1bb80073926e9b6c`.
