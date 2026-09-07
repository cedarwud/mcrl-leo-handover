# V0.23 DROP_C3 development evaluation contract

Status: `PRE_OUTCOME_DEVELOPMENT_CONTRACT`

This is a bounded fixed-policy physical evaluation contract.  It is not a
learner gate, a policy efficacy claim, or an authorization to open TEST or to
train an episode policy.

## Scope

The run has exactly one emitted arm: `DROP_C3`.  The label means the frozen
V0.20 Q1+Q2 decision is evaluated without evaluating or calling any C3
component.  No BASELINE receipt is emitted by this contract.  Since the
current BASELINE and DROP_C3 carriers intentionally select the same Q1+Q2
action, this run is a timing/physical-evaluation development check only; it
does not manufacture a between-arm distinction or a comparative claim.

## Frozen execution

| field | value |
|---|---|
| schema | `multi-catfish-mcrl-v023-drop-c3-development-evaluation-contract-v1` |
| status | `PROVISIONAL_PRE_GATE` |
| receipt split | `EVALUATION_DEVELOPMENT` |
| simulator data split | `TRAIN` only |
| episodes | 100 |
| users per episode | 100 |
| committed steps per episode | 10 |
| checkpoint cadence | every 100 episodes |
| action width | 28 |
| keyed fading component | `MCRL_V020_REPRICED_C3_GATE_V1` |
| policy lineage | `2026092101` |
| Q1 updates | 10 |
| Q2 initialization | `2026108101` |
| Q2 updates | 3000 |

The 100 world bindings are `world-000001` through `world-000100` with world
seeds `2026090601` through `2026090700`, respectively.  Every world seed is
bound to the keyed-fading root derived from the component above.  The same
world seed and field root are used whenever the paired two-arm adapter is
used; this contract itself executes only `DROP_C3`.

The physical endpoint pools realised `link_rate_bps` and
`system_power_w` from `TrainerEnvironment.last_outcome` using additive
bits/energy and one ratio of sums.  Service counts are pooled from each
outcome's committed service resolution.  The reduced `StepResult` is not used
as a physical receipt.

## Authenticated inputs

The policy is loaded from the current authenticated V0.20 repriced Q1/Q2
checkpoint and must carry all of these exact bindings in every receipt and
checkpoint:

* checkpoint SHA-256:
  `d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc`;
* authority body SHA-256:
  `50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48`;
* authority file SHA-256:
  `a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e`;
* source execution contract SHA-256:
  `ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48`;
* repricing contract SHA-256:
  `34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9`;
* canonical TRAIN-development PREREG bytes SHA-256:
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`;
* canonical PREREG record digest:
  `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`.

The launch entrypoint freezes only the PREREG-listed TLE files into a fresh
temporary archive, verifies every listed byte hash, then constructs the real
`TrainerEnvironment` with the `TRAIN` sampler.  A missing file, changed byte,
wrong TLE root, checkpoint, contract, field root, state shape, action mask,
physical outcome, or resume state aborts before a receipt is accepted.

## Resume and claim boundary

The checkpoint at episode 100 contains the complete receipt list, fixed plan
hash, exact input bindings, frozen Q1/Q2 parameter hashes, both environment
resume states when the paired adapter is used, all per-episode RNG states,
torch RNG state, and the four forbidden-boundary flags.  Resume is accepted
only at episode 100 and only when the checkpoint hash and all identities match
the current contract.

Every receipt and final result must keep these flags false:
`q3_evaluated`, `test_split_opened`, `episode_training`, and `learner_update`.
The claim ceiling is
`EVALUATION_PROVISIONAL_PRE_GATE_NO_C3_NO_TEST_NO_EFFICACY`.

No gate verdict, BASELINE comparison, C3 result, TEST result, or 9000-episode
training decision may be inferred from this development run.
