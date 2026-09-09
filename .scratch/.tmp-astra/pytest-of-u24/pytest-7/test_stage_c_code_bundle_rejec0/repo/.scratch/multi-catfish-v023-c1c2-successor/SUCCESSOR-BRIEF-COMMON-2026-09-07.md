# V0.23 C1/C2 successor — common brief for all implementation tasks (2026-09-07 13:35 UTC)

Decision (controller + codex gpt-6-astra ultra, `ADJUDICATION-SUCCESSOR-ROUTE-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md` in
`.scratch/multi-catfish-v023-controller-handoff-20260907/`): **Route C**. The LC-SRS R7 gate is sealed `STOP_PHYSICS_R7`;
its five-arm 100E launch is closed permanently. A separate, prospectively declared C1/C2-only development experiment is
built now; C3 stays outside its critical path and may re-enter only through its own admission (the pre-outcome contingency
ladder `.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md`).

## Binding boundaries (all tasks)
- Work only inside your owned directory. Never edit `src/`, `docs/`, any frozen package, sealed artifact, manifest,
  authority, launcher or receipt. Never touch running or sealed server roots. No ssh, no simulator runs, no training.
- No TEST split. No formula/sign/threshold/seed/horizon/lambda/acceptance changes. No `sys.modules` aliasing.
  No relabelling: `ALL_NEUTRAL_CONTROL` is never `BASELINE`; there is no all-neutral learner in this successor.
- C2 targets are already normalised once (`target_unit = normalized-repriced-ops3-delta-over-kappa`): never divide by
  kappa again. C1 raw surplus goes through the existing single normalisation only.
- Tests: narrow positive + mutation-negative + producer-derived fixtures (build fixtures with the producer's own writer
  code or real excerpts; never hand-typed literals that mirror your own assumptions). Run tests with `./.venv/bin/python -m pytest -q <your dir>`.
- Report at the end: changed files with sha256, exact test command and result, open questions, and one line `TASK_EXIT=DONE|BLOCKED`.

## Fixed successor declarations (from the astra decision §3–§5; the contract document is being written in parallel)
- Schema prefix `multi-catfish-mcrl-v023-c1c2-successor-`. Claim ceiling for source training:
  `TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY`.
- Learners (three independent two-head models): `FULL2` = (C1 informed, C2 informed), `DROP_C1` = (C1 neutral, C2 informed),
  `DROP_C2` = (C1 informed, C2 neutral). Fixed arm order `FULL2, DROP_C1, DROP_C2`. Routes `C1 -> C2` per epoch.
  Drops are retrained source ablations, never inference-time head removal.
- Physical evaluation arms (later, separate launcher): `FULL2, DROP_C1, DROP_C2, BASELINE` where BASELINE is the unchanged,
  externally authenticated pre-Catfish MODQN artifact through the existing `.scratch/multi-catfish-v023-baseline-adapter/`.
- Source budget: exactly 100 epochs = 200 updates per learner; checkpoints/exports at epoch 0 (initial bytes) and epoch 100;
  budgets above 100 need a separately declared later authority. Train seed `2927175120652069826` (declared pre-outcome in
  the V2 100E contract; reused unchanged). Deployment: masked, unweighted `Q1+Q2` argmax with the existing fixed tie handling.
- Model: Q1 = existing 228-D action-shared head; Q2 = existing 448-D V0.14 OPS-3 action-set head (28 actions × 16 local
  features, feature-major). Reuse the existing network implementations by import (find them via
  `grep -rn "class EEAxisLCSRSThreeRoute" src .scratch`); do not copy-modify them; no Q3 anywhere.
- Targets: the r8 root `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8` (sealed later today; digests are bound at freeze
  time, before consumption). Root layout = producer `receipt.json` (schema/status/claim ceiling as in
  `.scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py`), `MANIFEST.sha256`, `COMPLETE`,
  16 mode×world shards (modes informed/neutral × 8 worlds). Loader = `.scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py`
  (authenticated loading, row stacking, merged-receipt fields). Real excerpt fixture:
  `.scratch/multi-catfish-v023-c1c2-target-generation-launch/fixtures-real-shard/`.
- Provider protocol: `DeterministicRouteBatchProvider` in `.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py`
  (`next_batch(*, route, source, update_cursor)`, `provider_identity`, `planned_epoch_budget`, sampler save/restore).
