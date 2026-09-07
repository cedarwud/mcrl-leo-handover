# C2 analysis-source drift manifest

Status: reviewed compatibility exception for the frozen C2 time-only
identity/scale gate only. It is not source-parity training evidence and gives no
reward, runtime, Main-transfer, timing-parameter, or effectiveness authority.

Date: 2026-08-27

## Bound inputs

- launched training code SHA-256 (55 paths):
  `544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4`;
- current analysis code SHA-256 (56 paths):
  `4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e`;
- checkpoint SHA-256:
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`;
- preregistration digest:
  `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`;
- preregistration byte SHA-256:
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`;
- frozen v2 state-only runner SHA-256:
  `7f26af5e56460ff297f16cd2de4bf208cbe0a51e7b94091529bd547e623b7b63`;
- frozen v2 receipt SHA-256:
  `cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658`.

The v2 receipt itself binds the same runner SHA and records its historical
analysis-code SHA
`baa87f938ed0fdbf3b3d1e0cd7b29bb6859e3b12dea77dcc66fcea430fc1ad6b`.
The new gate does not treat that historical source as current; instead it must
reproduce the exact focal schedule, census, eligible keys, 758 eligible rows,
and one unsafe key before any scale output is read.

## Exhaustive current-versus-launched classification

Ignoring bytecode caches, only these current-source differences exist:

- `env/step.py`: adds the non-committing `ActionEvaluation` /
  `evaluate_actions` path and `commit=False` handover classification. The
  committed `step` path retains `commit=True` and no existing physics formula
  changed.
- `runtime/collapse_metrics.py`, `runtime/trainer_spec.py`, and
  `runtime/training_pipeline.py`: diagnostic naming/aggregation changes only;
  none changes C2 state encoding, Q1 inference, counterfactual physics, or the
  time ledger implemented by this runner.
- `runtime/head_pivotality.py`: new analysis-only assertion/action-key helpers.

All MODQN, Q-network, state-encoding, action/candidate, scenario, service,
antenna, interference, link-budget, energy-efficiency, and reward-calibration
files are byte-identical to the launched snapshot. `run_server_training.py` and
`pyproject.toml` are also byte-identical.

## Dynamic compatibility evidence

The retained two-step source-parity probe
`.scratch/catfish-design-data/run_c3_source_parity_probe.py` uses only the
deployed committed path. Under the launched and current source trees, with the
same completed checkpoint, preregistration, TLE view, 100 users, and seed
`2026082801`, its canonical JSON outputs were byte-for-byte equal. Equality
covered both steps' 112-D encoded states, Q1 tensors, actions, candidate tables,
served sets, active beams, link powers, link rates, reward matrices, system
power, throughput, and EE.

The C2 runner adds a stronger local requirement: every baseline preview must
equal its following committed step, and every discarded stay preview must leave
the prestate plus environment RNG unchanged. The formal result is invalid if
any such check fails.

## Ruling

The current source is compatible with the launched checkpoint for this
evaluation-only C2 identity/scale gate, subject to all of the following
fail-closed conditions: byte-pin this manifest and both source fingerprints,
pin the checkpoint/preregistration/v2 runner/v2 receipt, reproduce the frozen
v2 census exactly, and pass preview/commit, RNG, state, event, unit, and algebra
checks on every branch. Any mismatch is an input or identity failure, not a new
scientific result.
