# V0.23 100-epoch five-arm source-to-learner screen

Date frozen: 2026-09-07 (Asia/Taipei), before opening any terminal R7 outcome
and before either C1/C2 target mode completed.

Status: `FROZEN_PREOUTCOME_PARAMETERS / CONDITIONAL_EXECUTION`

Claim ceiling:
`TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_AND_ONE_WORLD_PLUMBING_ONLY_NO_TEST_NO_EFFICACY`

## 1. Purpose and admission

This is the first bounded current-model learner screen after the V0.23 source
work.  It is not simulator-episode training and it does not establish that any
Catfish improves energy efficiency.

Execution is admitted only when all of the following are independently
verified together:

1. the R7 result directory is sealed `COMPLETE`, its whole-tree manifest is
   valid, its final integrity is `PASS_FINAL_INTEGRITY`, and its only admitted
   scientific token is `GO_FIXED_LEARNER_SCREEN_CONTRACT_R7`;
2. the C1/C2 target root is sealed `COMPLETE`, its whole-tree manifest is
   valid, and both typed `informed` and `neutral` modes load without retagging;
3. the post-R7 provider factory authenticates both inputs, reconstructs the
   exact R7 record panel, builds the paired C3 schedule, and exposes a stable
   nonempty `provider_identity`; and
4. the launch code manifest and this contract verify byte-for-byte before a
   new, absent output root is created.

A valid R7 non-GO ends this LC-SRS launch path.  An invalid run permits only a
repair of the demonstrated execution defect; it does not permit a formula,
seed, threshold, horizon, or acceptance-rule change.

## 2. Frozen source-training design

- Epoch budget: exactly `100` complete source-training epochs.
- One epoch: exactly `C1 -> C2 -> C3`, hence `300` route updates total.
- Checkpoint cadence: every `100` complete epochs.  The initial shared bytes
  and the epoch-100 checkpoint are both bound in the receipts.
- Train seed: `2927175120652069826`, derived before outcome from the first
  64 SHA-256 bits of domain `MCRL_V023_FIVE_ARM_100E_TRAIN_SEED_V1` with the
  sign bit cleared.
- C3 schedule seed: `1113171504590631764`, derived before outcome from the
  first 64 SHA-256 bits of domain (with the sign bit cleared)
  `MCRL_V023_FIVE_ARM_100E_C3_SCHEDULE_SEED_V1`.
- Split: `SOURCE_TRAIN`; `TEST` is closed.
- Intended server output root:
  `/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1`.

The arm order and source-only ablation mapping are closed:

| arm | C1 | C2 | C3 |
| --- | --- | --- | --- |
| `ALL_NEUTRAL_CONTROL` | neutral | neutral | neutral |
| `FULL` | informed | informed | informed |
| `DROP_C1` | neutral | informed | informed |
| `DROP_C2` | informed | neutral | informed |
| `DROP_C3` | informed | informed | neutral |

All five current `EEAxisLCSRSThreeRoute` learners begin from identical
serialized initial bytes and thereafter own independent parameters and
optimizers.  No score head is removed, zeroed, sign-flipped, rescaled, or
post-hoc coordinated.

`ALL_NEUTRAL_CONTROL` is a source-training diagnostic and must never be
relabeled as the physical `BASELINE`.  The latter remains the separately
authenticated pre-Catfish MODQN policy.

## 3. Frozen learner configuration

The runner model file is `V023-100E-MODEL-CONFIG.json`, SHA-256
`2fab1e4a0b61bf88a428709815d078d9b613b06b645c4d9cef7e46b2220b78ec`.

Q1 and Q2 retain the accepted action-shared configuration:

- state/action dimensions `228/28`;
- hidden widths `(100, 50, 50)` with `tanh`;
- Adam learning rate `0.001`;
- shared normalization `kappa = 10097071012.757404 bit`;
- gauge coefficient `beta = 0.1`; and
- route loss weights `(1, 1, 1)`.

Q3 retains the frozen V0.23 structured head and optimizer defaults:

- action/action-context/token dimensions `28/29/38`;
- shared `67-64-64-1` scorer with `ReLU`;
- config SHA-256
  `c406a6a2a0da78a855c8f850c45803cfa1763a3e7e40823693b39207f14c3324`;
- Adam learning rate `0.001`, betas `(0.9, 0.999)`, epsilon `1e-8`, and zero
  weight decay.

There is no learning-rate sweep in this screen.  In particular, `0.01` is not
an outcome-selected parallel arm.

## 4. Mechanical screen decision

The source-training stage returns `PASS_SOURCE_TRAINING_INTEGRITY` only if:

1. exactly five epoch-100 current-model exports exist in the closed arm order;
2. the common initialization digest is identical across arms while parameter
   and optimizer storage remain independent;
3. all `300` route updates per arm are finite and follow the exact route/source
   mapping and consumed-file order;
4. the provider state, sampler cursors, model state, and optimizer state pass
   exact resume verification at the epoch-100 boundary;
5. all output hashes, source identities, input manifests, configuration, code,
   and authority receipts verify; and
6. no simulator episode or `TEST` input was opened.

Any integrity failure is `STOP_SOURCE_TRAINING_INTEGRITY`.  Training loss sign
or magnitude alone is not an EE decision and cannot be used to select another
seed, formula, scale, or budget.

## 5. Immediate one-world runtime diagnostic

Only after `PASS_SOURCE_TRAINING_INTEGRITY`, route the five exported current
diagnostic policies through one matched ten-step TRAIN/TLE world using fresh
environments, one common initial state, and one common keyed field:

- world index `1`;
- world id `train-v023-100e-plumbing-001`;
- world seed `2818138104890398344`, derived before outcome from the first
  64 SHA-256 bits of domain `MCRL_V023_FIVE_ARM_100E_WORLD_SEED_V1` with the
  sign bit cleared;
- frozen TLE root `/home/sat/mcrl-runtime/tle-frozen-20260820`.

This diagnostic passes only on complete five-arm coverage, mask-safe actions,
unchanged policy bytes, identical initial-world and keyed-field digests, ten
completed steps per arm, and finite bits/energy receipts.  Its EE directions
are descriptive only: one world cannot promote, reject, or tune a Catfish.

The authenticated pre-Catfish `BASELINE` is intentionally absent from this
one-world plumbing diagnostic.  It enters the separately frozen primary
physical evaluation, whose five curves are exactly `BASELINE`, `FULL`,
`DROP_C1`, `DROP_C2`, and `DROP_C3`.

## 6. Next boundary

After both mechanical stages pass, freeze and run the first matched
100-episode TRAIN-development physical evaluation with a receipt every 100
episodes.  Do not skip directly to 500, 1500, 3000, or 9000 episodes.  Do not
choose a learner checkpoint from physical outcomes.  The later 3000-episode
and 9000-episode paths remain governed by the user's conditional execution
authorization; notify the user immediately before 9000 episodes.

The older rapid-contingency F3 `2000`-update ladder is not the R7-GO path.  It
applies only to the predeclared CSE/EC contingency families after an eligible
LC-SRS physics stop.  It therefore does not compete with or silently replace
this current 100-epoch five-arm screen.
