# V0.23 five-arm source-training runner

This is an implementation-only lifecycle around the adjacent
`multi-catfish-v023-five-arm-learner-orchestrator` seam.  It consumes only its
`DeterministicRouteBatchProvider`, trains no simulator or episode policy, has
no learner-evaluation path, and rejects `TEST`.

One source-training epoch is exactly the complete `C1 -> C2 -> C3` cycle:
three route updates.  A formal checkpoint is therefore exactly every 100
complete epochs (300 updates), never a simulator episode count.  The fixed arm
order is `ALL_NEUTRAL_CONTROL`, `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`; the runner exports
five complete current `EEAxisLCSRSThreeRoute` checkpoints in that order at each
formal checkpoint.

`canonical-status.json`, `canonical-receipt.json`, each runner checkpoint,
digest sidecar, export, export manifest, and checkpoint receipt are published
write-once.  A resume verifies the runner and current-model schemas, SHA-256,
epoch/update cadence, source map, initialization, provider identity, sampler
state, consumed-file order, and all five model/optimizer states before it
restores anything.

The only supported frozen epoch budgets are `100`, `500`, `1500`, `3000`, and
`9000`.  Budgets above 100 require a separately declared later-budget authority
digest.  Nothing in this directory grants that later authority.

## Still-required integration inputs

No real run has been started.  Before an authorized invocation, the operator
must supply:

- an **absent, explicit** output root;
- an explicit supported epoch budget and (when above 100) its later frozen
  budget-authority SHA-256;
- a `MODULE:CALLABLE` provider factory that returns the existing
  `DeterministicRouteBatchProvider`, exposes a stable `provider_identity`, and
  declares a positive integer `planned_epoch_budget` exactly equal to the
  runner's frozen `--epochs` value;
- immutable C1/C2/C3 source batches for both `neutral` and `informed`, with
  resume-safe sampler state and stable consumed `file_id` values;
- an exact current-model JSON configuration, train seed, and the frozen
  authority, code, and input SHA-256 declarations; and
- an explicit `--execute` acknowledgement.

The CLI requires all of those declarations, builds the real current model
configuration, and starts a new write-once root only after preflight.  It was
not invoked here.

Focused proof:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider \
  .scratch/multi-catfish-v023-five-arm-training-runner/test_v023_five_arm_source_training_runner.py
```
