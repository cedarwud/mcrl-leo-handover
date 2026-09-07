# V0.23 C1/C2 successor physical evaluation

This directory implements the contract-draft Stage B plumbing diagnostic and
Stage C four-arm fixed-policy TRAIN-development evaluation.  The fixed arm
order is `FULL2, DROP_C1, DROP_C2, BASELINE`.  The three learned arms consume
producer `multi-catfish-mcrl-v023-c1c2-successor-two-route-checkpoint-v1`
exports and deploy masked, unweighted `Q1+Q2` with the lowest legal index on a
tie.  `BASELINE` is admitted and invoked only through the existing baseline
adapter and carries `routes = []`.

`build_v023_c1c2_successor_world_plan.py` writes one deterministic 9000-world
plan (`world-{k:06d}`, seed `2026090600 + k`) and verifies it with `--check`.
`v023_c1c2_successor_physical_runner.py` pools additive bits and positive
energy from `TrainerEnvironment.last_outcome`, divides once after pooling, and
uses pooled served count over pooled opportunity.  It writes a checkpoint and
non-terminal rung receipt every 100 episodes, supports cumulative pauses at
100/500/1500/3000, rejects plan/policy drift, and writes `result.json` only at
the declared terminal boundary.  A 9000 terminal requires a separate
continuation-authority digest.

`v023_c1c2_successor_plumbing_diagnostic.py` is the exact one-world Stage B
check: world index 1, id
`train-v023-c1c2-successor-plumbing-001`, seed `936547238915053535`, 100 users,
ten steps, and TLE root `/home/sat/mcrl-runtime/tle-frozen-20260820`.  Its
physical directions are stored only under `descriptive_physical_endpoints`;
there is no scientific decision field.

This is not a server launcher, simulator replacement, learner, source trainer,
TEST evaluator, C3/Q3 carrier, efficacy result, or authority to execute any
stage.  Imports are inert.  No run starts without an explicit caller.

## Tests

From the repository root, the exact unit-only command is:

```bash
./.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c1c2-successor-physical-evaluation
```

The tests use deterministic synthetic episode records and a checkpoint fixture
written by the concurrent two-route producer's own `checkpoint_state` method.
They do not construct a TLE archive or run the simulator.

## BIND_AT_FREEZE inputs still open

The contract remains `DRAFT_PRE_FREEZE_R2`; this directory does not fill or
change its placeholders.  Before execution, the external freeze/launch
manifest must bind the items enumerated by contract section 9, including:

- the three learned checkpoint/export digests, initialization bytes, source
  runner/factory/launcher/policy-adapter/verifier manifests, sampler/file-order
  policy, and predecessor authorities;
- the distinct BASELINE status/authentication digest and adapter closure (the
  policy digest is already fixed as
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`);
- PREREG and frozen-TLE manifests, the generated 9000-world plan digest, RNG
  policy, deterministic process/resource limits, and absent output roots;
- this evaluation runner, diagnostic, independent verifier, and complete
  Stage-C execution configuration manifests; and
- a later continuation-authority digest before declaring a 9000 terminal.

Until those bindings are sealed, Stage B and Stage C remain implementation
artifacts only.
