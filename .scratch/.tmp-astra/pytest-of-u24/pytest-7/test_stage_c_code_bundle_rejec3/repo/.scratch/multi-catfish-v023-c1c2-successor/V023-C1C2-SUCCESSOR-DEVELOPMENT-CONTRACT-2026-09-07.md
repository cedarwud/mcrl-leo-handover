# V0.23 C1/C2 successor development experiment — source training, plumbing and physical development evaluation

Status: `DRAFT_PRE_FREEZE_R2` — scientific sections sealed separately as `V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md` (SHA-256 `f27d0500525aa6569c42299d81d3debdc48ef32d79a140d31854dc31f79bb8ea`, 14:00 UTC); execution bindings remain open until the launch manifest is sealed (2026-09-07 14:00 UTC; the codex gpt-6-astra read-only review `REVIEW-C1C2-SUCCESSOR-CONTRACT-CODEX-GPT6-ASTRA-2026-09-07.md` returned `FREEZE_AFTER_FIXES`; all seven textual corrections are applied below and its missing declarations are enumerated in §9). This document authorises nothing until every
`<<BIND_AT_FREEZE:…>>` field is replaced by its digest, the codex gpt-6-astra read-only review is attached, and the
document's own SHA-256 is sealed in the launch manifest. No successor learner computation — not even the one-epoch
diagnostic — may run before that.

## 0. Provenance and disclosure

Following the pre-registered `STOP_PHYSICS_R7` (root `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`, sealed
2026-09-07 12:54 UTC, `integrity_status=VERIFIED`), the LC-SRS successor route and its conditional five-arm 100E launch
are closed. Decision authority: controller with codex gpt-6-astra ultra
(`.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-SUCCESSOR-ROUTE-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md`,
Route C), under the owner's delegation of 2026-09-07 13:12 UTC.

Disclosure carried by every receipt, the handoff and the paper:

> Following the pre-registered STOP_PHYSICS_R7, we closed the LC-SRS successor and prospectively declared a separate
> C1/C2-only development experiment with unchanged C1/C2 definitions; this outcome-informed scope change does not
> rescue R7 or establish three-Catfish efficacy, and R7 residuals and successor outcomes are not used to select
> formulas, signs, thresholds, seeds, horizons, lambda, budgets, or acceptance rules.

C3 is absent from this experiment by declaration (not neutral-stubbed, not zeroed). It may re-enter only through its
own admission: the pre-outcome contingency ladder
`.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md` (F1 → F2 →
F3 → F4), followed by a separately frozen five-arm contract. Neither R7 nor successor outcomes select or tune a C3; R7 contract §7 forbids automatic CSE/EC promotion. Ladder §4
permits separately authorised F0/F1 after `STOP_PHYSICS`, retaining the declared D-before-F priority and independent
admission; this contract authorises no C3 run and no C3 selection.

## 1. Purpose and admission

This is a bounded TRAIN-development experiment with three stages: (A) C1/C2 source training of three two-head
learners, (B) a one-world runtime plumbing diagnostic, (C) a fixed-policy physical development evaluation ladder.
None of the three stages opens `TEST`; none establishes deployment efficacy by itself. Stage A is genuine learner
training (source updates); stages B and C are fixed-policy evaluation, not episode-based learning.

Execution of stage A is admitted only when all of the following verify together, independently:

1. the C1/C2 target root `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8` is sealed `COMPLETE`, its `MANIFEST.sha256`
   is valid, its producer `receipt.json` carries `status=TARGETS_MATERIALIZED_TRAIN` and claim ceiling
   `TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_NO_EPISODE_TRAINING_NO_EFFICACY_NO_TEST`, and both typed modes load:
   `MANIFEST.sha256` digest `<<BIND_AT_FREEZE:r8_manifest_sha256>>`, `receipt.json` digest `<<BIND_AT_FREEZE:r8_receipt_sha256>>`,
   `COMPLETE` content `<<BIND_AT_FREEZE:r8_complete_line>>`;
2. the successor provider factory v3 (`.scratch/multi-catfish-v023-c1c2-provider-factory-v3/`, code manifest
   `<<BIND_AT_FREEZE:factory_v3_manifest_sha256>>`) authenticates the target root, the learner closure
   (`<<BIND_AT_FREEZE:learner_manifest_sha256>>`) and exposes a stable nonempty `provider_identity` listing exactly the
   routes `C1, C2`; any R7 field, C3 route or `TEST` path is a hard failure;
3. the two-route runner and model (`.scratch/multi-catfish-v023-two-route-source-training-runner/`, code manifest
   `<<BIND_AT_FREEZE:runner_manifest_sha256>>`) verify byte-for-byte. The final contract's file SHA-256 is sealed in an
   external launch manifest, and that manifest is sealed externally (`.sha256` sidecar); neither file embeds its own
   digest or creates a reciprocal file-hash dependency;
4. the one-epoch real-artifact diagnostic (v3 load → one `C1 → C2` epoch on a scratch copy → export/reload → exact
   continuation) passes on the server immediately before launch, with its phase timings recorded; and
5. the output root is absent and is created write-once by the launcher.

An invalid run permits only the repair of the demonstrated execution defect. Nothing in this document may be changed
against an observed loss, direction, timing or physical outcome.

## 2. Frozen source-training design (stage A)

- Learners: exactly three independent two-head models; arm order closed as `FULL2, DROP_C1, DROP_C2`.

| arm | C1 source | C2 source |
| --- | --- | --- |
| `FULL2` | informed | informed |
| `DROP_C1` | neutral | informed |
| `DROP_C2` | informed | neutral |

  Drops are retrained source ablations (equal-budget neutral-source replacement), never inference-time head removal.
  There is no all-neutral learner and no arm named `ALL_NEUTRAL_CONTROL`, `FULL`, `DROP_C3` or `BASELINE` in stage A.
- One epoch: exactly `C1 -> C2`; epoch budget exactly `100`; hence `200` route updates per learner. Larger budgets
  (`500, 1500, 3000, 9000` source epochs) require a separately declared later authority digest and are not opened here.
- Checkpoints/exports: the identical serialised initial bytes (epoch 0) and the epoch-100 state of every arm, in arm
  order, each with digest sidecars; exact resume verification at the epoch-100 boundary.
- Train seed: `2927175120652069826` — reused unchanged from the pre-outcome derivation
  (first 64 SHA-256 bits of domain `MCRL_V023_FIVE_ARM_100E_TRAIN_SEED_V1`, sign bit cleared). No C3 schedule seed exists.
- Sampling: the provider's deterministic per-route sampler with recorded consumed-file order; both modes of all 16
  mode×world shards of the r8 root are the only inputs. Split `SOURCE_TRAIN`; `TEST` closed.
- Model and optimiser constants are exactly the V2 100E values for Q1 and Q2 (§3); no learning-rate, width, kappa or
  beta variant exists. Q1 and Q2 have separate configuration records, heads, update paths and optimiser states.
- Deployment rule for all later stages: learned arms deploy masked, unweighted `Q1+Q2`, choosing the lowest legal
  action index on ties; no per-head weights. `BASELINE` deploys exclusively through its unchanged authenticated MODQN
  adapter.
- Intended server roots: checkout `/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout`, output
  `/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1`, tmux `mcrl-v023-c1c2-successor-100e-r1`.
- Claim ceiling: `TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY`.

## 3. Frozen learner configuration

Q1 (action-shared): state/action `228/28`, hidden `(100, 50, 50)` with `tanh`, Adam `0.001`, shared normalisation
`kappa = 10097071012.757404 bit`, gauge `beta = 0.1`. C1 provider labels are raw surplus and pass through the existing
single normalisation only.

Q2 (V0.14 OPS-3 action-set head, heterogeneous, not projected into Q1's state): 28 actions × 16 local features =
`448` state values, feature-major layout, hidden `(100, 50, 50)` with `tanh`, Adam `0.001`, `kappa = 10097071012.757404`,
`beta = 0.1`. C2 provider labels have target unit `normalized-repriced-ops3-delta-over-kappa`; they are consumed as the
typed normalised field without another division.

Model configuration file: `.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json`, SHA-256
`9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d` — the `q1` and `q2` records of `V023-100E-MODEL-CONFIG.json` (sha
`81e30b716ce996fb69e57ec9c1c3a4806f93598e6c009216287dd6a7dbde5df7`) copied unchanged, the `q3` record removed, nothing else changed.
There is no Q3 record, no `C3View`, no structured token anywhere in the successor learner.

## 4. Mechanical stage-A decision

`PASS_SOURCE_TRAINING_INTEGRITY` only if: exactly three epoch-100 exports exist in arm order; the common initialisation
digest is identical across arms while parameter and optimiser storage are independent; all `200` updates per arm are
finite and follow the exact route/source mapping and consumed-file order; provider state, sampler cursors, model and
optimiser state pass exact resume verification at epoch 100; every output hash, source identity, input manifest,
configuration, code and authority receipt verifies; no simulator episode or `TEST` input was opened. Any failure is
`STOP_SOURCE_TRAINING_INTEGRITY`. Training loss sign or magnitude is never an EE decision and selects nothing.

## 5. One-world runtime plumbing diagnostic (stage B)

Only after `PASS_SOURCE_TRAINING_INTEGRITY`: route the three exported policies and the authenticated pre-Catfish
`BASELINE` through one matched ten-step TRAIN/TLE world with fresh environments, one common initial state and one
common keyed field: world index `1`, world id `train-v023-c1c2-successor-plumbing-001`, world seed `936547238915053535` (first 64
SHA-256 bits of domain `MCRL_V023_C1C2_SUCCESSOR_PLUMBING_WORLD_SEED_V1`, sign bit cleared, derived 2026-09-07 13:50 UTC
before any successor outcome), frozen TLE root `/home/sat/mcrl-runtime/tle-frozen-20260820`. Passes only on complete
four-arm coverage, mask-safe actions, unchanged policy bytes, identical initial-world and keyed-field digests, ten
completed steps per arm, finite bits/energy receipts, and recorded per-phase wall times. Its EE directions are
descriptive only; one world promotes, rejects or tunes nothing.

## 6. Physical development evaluation ladder (stage C)

- Arms: exactly `FULL2, DROP_C1, DROP_C2, BASELINE`. `BASELINE` is the unchanged, externally authenticated pre-Catfish
  MODQN policy admitted through `.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py`
  (`EXPECTED_CHECKPOINT_SHA256` there; bound as `<<BIND_AT_FREEZE:baseline_checkpoint_sha256>>`). It carries no C1/C2
  source and is never a trained arm. No arm is renamed.
- Episode structure: 100 users, 10 committed decision steps per episode, `TRAIN` simulator split only, one lineage.
- World binding rule (declared now, extends the 2026-09-06 development-evaluation scheme): episode `k` (1-based,
  cumulative across rungs) runs world `world-{k:06d}` with world seed `2026090600 + k`; the same worlds and keyed
  fields are shared by all four arms (matched design). No world is replaced after opening.
- Ladder: freeze one `9000`-world plan (world ids, seeds, keyed fields, arm order, plan digest) before any computation;
  execute it with authenticated every-`100`-episode checkpoints and write-once outputs, pausing cumulatively at `100`,
  `500`, `1500` and `3000` under the unchanged plan identity. Intermediate boundaries publish rung receipts only, never a
  terminal `result.json`. Continuation beyond `3000` toward `9000` happens only after `C1C2_DEVELOPMENT_PREDICTION_HELD`
  and after notifying the owner; it continues the same four arms and the same plan unchanged.
- Estimand: pooled ratio-of-sums energy efficiency (additive bits over additive energy) per arm over the completed
  episodes, with pooled service counts; the paired between-arm comparison uses the matched worlds.
- Prediction (declared before any outcome): `FULL2 > DROP_C1`, `FULL2 > DROP_C2`, and each of the three learned arms
  `> BASELINE` in pooled ratio-of-sums EE, with service not lower than `BASELINE` by more than `0.001` in served
  fraction for any learned arm.
- Falsifier and dispositions: at `3000` complete matched episodes, emit exactly one overall result:
  `C1C2_DEVELOPMENT_PREDICTION_HELD` iff `FULL2` exceeds both drops, every learned arm exceeds `BASELINE`, and every
  learned arm's served fraction is at least `BASELINE` minus `0.001`; otherwise `C1C2_DEVELOPMENT_PREDICTION_FALSIFIED`.
  Record all applicable, non-exclusive reasons alongside the result: `FULL2_NOT_ABOVE_BASELINE`,
  `DROP_C1_NOT_ABOVE_BASELINE`, `DROP_C2_NOT_ABOVE_BASELINE`, `DROP_C1_NOT_BELOW_FULL2` (C1 contribution unsupported),
  `DROP_C2_NOT_BELOW_FULL2` (C2 contribution unsupported), and `SERVICE_NONINFERIORITY_FAILED:<arm>`. Invalid or
  incomplete receipts produce an integrity STOP (`STOP_PHYSICAL_EVALUATION_INTEGRITY`), never a scientific result.
  Earlier rungs are reported but cannot select or stop scientifically; `FALSIFIED` ends continuation (no rescue; a later
  experiment needs its own declaration). These tokens are development results on `TRAIN`; they are not efficacy claims
  and do not open `TEST`.
- Claim ceiling: `TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_PHYSICAL_EVALUATION_NO_C3_NO_TEST_NO_EFFICACY`.
- Runner: a four-arm variant of `.scratch/multi-catfish-v023-physical/v023_physical_episode_runner.py` (currently
  `BASELINE`/`DROP_C3` only) — new code, manifest `<<BIND_AT_FREEZE:evaluation_runner_manifest_sha256>>`. The four-arm
  runner, its independent verifier and the complete scientific/execution configuration of stage C are bound before any
  successor computation; after stage B, the stage-C preflight only authenticates predetermined outputs and mechanical
  receipts and cannot change the sealed contract.

## 7. Authority, roles and prohibitions

- Compute: server `sat` only, project `.venv`; every consumer exercised offline against real artifacts before any long
  run; receipts over polling.
- Decision authority for execution questions: controller with codex gpt-6-astra (read-only adjudication); the owner is
  notified before the `9000`-episode continuation and at every STOP token.
- Prohibited: `TEST`; any change to formulas, signs, thresholds, seeds, horizons, lambda, budgets or acceptance rules
  after freeze; reruns selected by outcome; rewriting sealed artifacts or frozen manifests; `sys.modules` aliasing;
  relabelling arms; reading R7 residuals or any successor outcome to choose a C3 mechanism.
- Reuse permitted byte-identical: sealed r8 targets, the target loader, the Q1/Q2 network implementations, simulator
  components, the baseline adapter. New code: factory v3, two-route model/orchestrator/runner, launcher/preflight/sealer,
  diagnostic, four-arm evaluation runner. Every frozen predecessor package stays untouched.

## 8. Next boundary

Freeze order: bind r8 digests → attach the astra review → seal this document's SHA-256 and the launch manifest → server
one-epoch diagnostic → stage A → stage B → freeze stage C preflight → stage C rungs with receipts every 100 episodes →
owner notification before 9000. A valid scientific stop ends this experiment's schedule and does not authorise another attempt under this document;
an `INVALID_RUN` permits only documented infrastructure repair and replay of the smallest invalid unit, preserving valid
outcomes and every scientific declaration.

## 9. Bindings required before seal (from the astra review; none may be filled from an outcome)

- r8: `MANIFEST.sha256` digest, `receipt.json` digest, literal `COMPLETE` line (§1).
- `BASELINE`: checkpoint SHA-256 `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b` (adapter
  `EXPECTED_CHECKPOINT_SHA256`), state dimension `112`, `9000`-episode checkpoint, status/authentication digest distinct
  from the policy digest, adapter closure digest, and empty source routes (`routes = []`).
- Learner: initialisation bytes digest; sampler and consumed-file order policy; C1/C2 formulas, objectives and
  optimiser defaults (digest of the model configuration record without Q3); factory v3, runner, launcher, diagnostic,
  policy adapters and the independent verifier code manifests; predecessor authority digests that the loaders check.
- Physical: PREREG and frozen-TLE manifests, the `9000`-world plan digest (deterministic from the §6 rule; built by
  `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/build_v023_c1c2_successor_world_plan.py`, first derivation
  2026-09-07 14:20 UTC = `866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb`, to be re-derived and compared at
  freeze), keyed-field namespace
  `MCRL_V020_REPRICED_C3_GATE_V1`, RNG policy, deterministic process environment (BLAS/OpenMP threads) and resource
  limits, absent diagnostic/evaluation output roots.
- Aggregation: physical endpoint pooled from `TrainerEnvironment.last_outcome` (additive bits, additive positive energy,
  one ratio of sums), pooled served over pooled opportunity as the service denominator, stage B's `100` users, and
  explicit integrity-failure dispositions for stages B and C (`STOP_PLUMBING_INTEGRITY`, `STOP_PHYSICAL_EVALUATION_INTEGRITY`).
