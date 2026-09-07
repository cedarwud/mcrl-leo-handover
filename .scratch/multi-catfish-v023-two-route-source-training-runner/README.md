# V0.23 C1/C2 successor source-training runner

This isolated package implements the prospectively declared two-route source
learner. It constructs three independent models in fixed order `FULL2`,
`DROP_C1`, `DROP_C2`. Every source epoch is exactly `C1 -> C2`, so the only
supported budget is 100 epochs = 200 updates per model. The source mapping is:

| arm | C1 | C2 |
| --- | --- | --- |
| `FULL2` | informed | informed |
| `DROP_C1` | neutral | informed |
| `DROP_C2` | informed | neutral |

The model imports the existing `ActionSharedQNetwork` (228-D Q1) and
`V014ActionSetQNetwork` (448-D feature-major OPS-3 Q2). The orchestrator
inherits the existing heterogeneous trainer's C1 and C2 update methods, so the
losses, normalization, learning rates, and optimizer types are unchanged. Each
head has independent parameters and Adam state. Checkpoints use
`multi-catfish-mcrl-v023-c1c2-successor-two-route-checkpoint-v1`, carry exact
`routes: ["C1", "C2"]`, and digest initial bytes plus current head and optimizer
states. The loader rejects predecessor three-route checkpoints and Q3/C3 state.

The runner writes canonical status, epoch-0 and epoch-100 runner checkpoints,
three exports in fixed arm order at both epochs, checkpoint receipts, digest
sidecars, and a final receipt exactly once. Formal construction authenticates
the frozen model JSON and seed, admits only a digest-verifiable factory-v3
identity, and cross-binds the authority, learner-code manifest, r8 manifest,
provider-config and model-config digests before constructing any learner.
Resume validates complete arm/export state, route counts, consumed-file
history, exact Adam defaults and finite optimizer state before installation.
Before the terminal receipt, epoch 100 is restored into independent provider,
sampler, model and optimizer objects and all exports are reloaded exactly; the
receipt records that integrity decision. The CLI is:

```text
--output-root --epochs --provider-factory MODULE:CALLABLE
--model-config-json --train-seed --authority-sha256 --code-sha256
--input-sha256 --execute
```

This is TRAIN-development source learning only. It has no C3, no all-neutral
control, no `FULL` or `BASELINE` training arm, no simulator, no physical or TEST
evaluation, and no efficacy claim. The claim ceiling is
`TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY`.
Budgets above 100, including 500, are rejected pending later authority.

Exact test command:

```bash
./.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-two-route-source-training-runner
```
