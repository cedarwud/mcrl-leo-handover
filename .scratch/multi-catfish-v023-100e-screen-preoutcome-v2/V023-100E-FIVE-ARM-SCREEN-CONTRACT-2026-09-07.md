# V0.23 100-epoch five-arm source-to-learner screen (V2 execution correction)

Date frozen: 2026-09-07 (Asia/Taipei), V2 correction issued before opening any
terminal learner outcome. V1 is retained as provenance only; this bundle
corrects the execution closure and does not alter the scientific design.

Status: `FROZEN_PREOUTCOME_PARAMETERS / CONDITIONAL_EXECUTION`

## 0. V2 execution corrections (execution only; no scientific change)

The following statements are binding for the V2 launch and change no seed,
epoch budget, threshold, formula, learning rate, or acceptance rule of §2–§5:

1. Q1 is the 228-D action-shared head; Q2 is the 448-D V0.14 OPS-3
   action-set head (28 actions × 16 local features, Boolean action masks).
   Q1 and Q2 are separate configuration records (`q1`, `q2`) in the model
   config; the legacy shared `q12` record is refused.
2. C2 labels arrive already normalized exactly once (target unit
   `normalized-repriced-ops3-delta-over-kappa`); no consumer divides by
   `kappa` again.
3. The target root is the corrected r8 output
   `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`; the R7 root remains
   the existing sealed R7-I1 root `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`.
4. Per DECISION A, R7 code-closure authentication uses the immutable R7 seed
   checkout identified by `r7_code_root`, while the successor learner tree is
   bound separately by this bundle's launch manifest.
5. The fixed sealed R7 C3 view/target is an offline source while each arm's
   Q1/Q2 learners update. This creates a later deployment covariate-shift
   diagnostic; it is not permission to rebuild C3 targets online.
6. The launcher requires a bounded remote startup acknowledgement: the
   controller writes a write-once startup marker before invoking the runner
   and the launcher waits at most 120 s for that marker plus a live tmux
   session; tmux creation alone is not an acknowledgement.
7. `TEST` stays closed; no scientific parameter changes; the separate
   non-formal one-epoch provider diagnostic (`run_v023_one_epoch_provider_diagnostic.py`)
   precedes the formal run and cannot create a formal result.

Claim ceiling:
`TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_AND_ONE_WORLD_PLUMBING_ONLY_NO_TEST_NO_EFFICACY`

## 1. Purpose and admission

This is the first bounded current-model learner screen after the V0.23 source
work.  It is not simulator-episode training and it does not establish that any
Catfish improves energy efficiency.

Execution is admitted only when all of the following are independently
verified together:

1. the R7 result directory `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1` is
   sealed `COMPLETE`, its whole-tree manifest is
   valid, its final integrity is `PASS_FINAL_INTEGRITY`, and its only admitted
   scientific token is `GO_FIXED_LEARNER_SCREEN_CONTRACT_R7`;
2. the C1/C2 target root `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`
   is sealed `COMPLETE`, its whole-tree manifest is valid, and both typed
   `informed` and `neutral` modes load without retagging;
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
- Intended server checkout root:
  `/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout`.
- Intended server output root:
  `/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2`.
- Intended tmux session:
  `mcrl-v023-five-arm-source-training-20260907-100e-r2`.

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
`81e30b716ce996fb69e57ec9c1c3a4806f93598e6c009216287dd6a7dbde5df7`.

Q1 retains the accepted action-shared configuration:

- state/action dimensions `228/28`;
- hidden widths `(100, 50, 50)` with `tanh`;
- Adam learning rate `0.001`;
- shared normalization `kappa = 10097071012.757404 bit`;
- gauge coefficient `beta = 0.1`; and
- route loss weights `(1, 1, 1)`.

Q2 is deliberately heterogeneous and is not projected into Q1's state:

- current V0.14 OPS-3 action-set head;
- 28 actions and 16 local features per action, hence `448` state values;
- hidden widths `(100, 50, 50)` with `tanh`;
- Adam learning rate `0.001`, `kappa = 10097071012.757404`, and `beta = 0.1`.

The C2 provider labels have target unit
`normalized-repriced-ops3-delta-over-kappa`. They are already divided by
`kappa` exactly once at source generation. The C2 learner consumes that typed
normalized field without another division. Q1 and Q2 have separate model
configuration records, network heads, update paths, and optimizer state.

Q3 retains the frozen V0.23 structured head and optimizer defaults:

- action/action-context/token dimensions `28/29/38`;
- shared `67-64-64-1` scorer with `ReLU`;
- config SHA-256
  `c406a6a2a0da78a855c8f850c45803cfa1763a3e7e40823693b39207f14c3324`;
- Adam learning rate `0.001`, betas `(0.9, 0.999)`, epsilon `1e-8`, and zero
  weight decay.

There is no learning-rate sweep in this screen.  In particular, `0.01` is not
an outcome-selected parallel arm.

### C3 source disclosure

The fixed sealed R7 C3 view/target is an offline source artifact. During this
screen each arm's Q1 and Q2 learners update, but the C3 source view is not
silently rebuilt online. Any deployment covariate shift between that fixed
source and updated Q1/Q2 state is measured later by the separately frozen
physical diagnostic; this source-training screen does not claim deployment
efficacy.

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
