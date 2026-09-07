# V0.23 LC-SRS gate relaunch decision R2

Status: **FROZEN EXECUTION GO — CODE-CORRECTED V0.23 GATE R2 ONLY**  
Date: 2026-09-05 (Asia/Taipei)  
Compute class: heavy CPU; execute only on the Ubuntu server.

## R1 invalid-run finding

The first authorized server invocation created
`/home/sat/mcrl-v023-lcsrs-gate-20260905-r1` and passed the local and remote
preflight and focused non-simulator test suite.  Its controller then stopped
at the first TRAIN-development source world with `FAILED` and exit status 2.
It did not publish a source JSON or sidecar, a fit, a composition, a
`result.json`, or `COMPLETE`.

A bounded deterministic reproduction on world `2026121705` exposed the
implementation error before any outcome receipt was admitted:

```text
AttributeError: 'StepResult' object has no attribute 'observation'
```

`TrainerEnvironment.step(...)` deliberately returns the trainer-facing
`StepResult`; the full successor `StepObservation` is available through
`TrainerEnvironment.last_outcome.observation`.  The V0.23 source and replay
adapters had incorrectly treated the trainer-facing result as the full
physics outcome.  R1 is therefore an `INVALID_RUN` caused by an API-shape
defect, not a C3 scientific decision.  Its server root must remain untouched.

## Authorized correction

Authorize only the minimal API-shape correction that reads the successor
observation from the environment's authenticated `last_outcome`.  The
correction must cover both source generation and literal composition replay
and must have focused regression tests in the preflight manifest.

The correction must not change the C3 target, topology, source enumeration,
feature schema, normalization, lambda, kappa, worlds, seeds, common-field
draws, learner configuration, thresholds, acceptance tokens, or any other
scientific or execution parameter.  No R1 outcome may be used for tuning;
none was produced.

## R2 execution boundary

After the corrected implementation and regression tests are sealed in a new
post-decision `PREFLIGHT-MANIFEST.sha256`, authorize exactly one fresh R2
execution through
`.scratch/multi-catfish-v023-c3-observability/sync_launch_v023_lcsrs_gate_server.sh`
using:

- server root `/home/sat/mcrl-v023-lcsrs-gate-20260905-r2`;
- tmux identity `mcrl-v023-lcsrs-gate-20260905-r2`; and
- result root
  `/home/sat/mcrl-v023-lcsrs-gate-20260905-r2/artifacts/multi-catfish-v023-lcsrs-gate-20260905-r2/server-run`.

The launcher must authenticate this decision, the original method contract,
the execution addendum, every implementation binding, and the complete test
set before source work.  R2 retains all original closed boundaries: TRAIN
development only, no TEST, no episode-policy training, and no efficacy claim.

## Controller token

`GO_V023_LCSRS_GATE_R2_ON_UBUNTU_SERVER`
