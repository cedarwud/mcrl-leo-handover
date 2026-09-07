# V0.23 five-arm learner orchestrator

Status: **implementation-only / no-efficacy**. This isolated directory contains
no simulator call, SSH launcher, training job, TEST path, D40 load, real target
root, output writer, head removal, zeroing, sign flip, rescaling, coordinator,
or replacement model objective.

`v023_five_arm_learner_orchestrator.py` creates five independent current
`EEAxisLCSRSThreeRoute` instances from one serialized initialization byte
stream. Each model owns independent Q1/Q2/Q3 parameter storage and optimizer
state. Every update goes exclusively through the existing scratch
`V023HeterogeneousTrainer`.

## Closed source-ablation mapping

| arm | C1 source | C2 source | C3 source |
| --- | --- | --- | --- |
| `ALL_NEUTRAL_CONTROL` | neutral | neutral | neutral |
| `FULL` | informed | informed | informed |
| `DROP_C1` | neutral | informed | informed |
| `DROP_C2` | informed | neutral | informed |
| `DROP_C3` | informed | informed | neutral |

The schedule is always `C1 -> C2 -> C3`. At one route cursor the provider is
called once for `neutral` and once for `informed`; the resulting typed batch is
shared only among arms assigned that exact `(route, source)`. Therefore the
ablation is source-only and cannot silently become a topology or parameter
ablation.

## Provider contract

The orchestrator accepts no data path and has no default provider. An adapter
must implement `DeterministicRouteBatchProvider`:

```python
next_batch(*, route: str, source: str, update_cursor: int) -> ProvidedRouteBatch
sampler_state() -> Mapping[str, Any]
load_sampler_state(state: Mapping[str, Any]) -> None
```

`ProvidedRouteBatch` must carry the exact existing type:

| route | required batch | additional field |
| --- | --- | --- |
| C1/C2 | `EEAxisPairBatch` | none |
| C3 | `LCSRSC3SampledBatch` | nonempty `tuple[LCSRSAnchorSurface, ...]` |

It also carries a nonempty stable `file_id`. The orchestrator records the exact
route/source/file consumption order but does not open, decode, aggregate, or
manufacture target data.

Every public update receipt and checkpoint carries
`IMPLEMENTATION_ONLY_NO_EFFICACY_NO_SIMULATOR_NO_TEST`; losses in those
receipts are plumbing diagnostics, not results or efficacy evidence.

## Checkpoint boundary

`checkpoint_state()` returns an in-memory mapping only. It deep-copies:

- all five current model and optimizer states;
- initialization bytes and digest, arm order, route order, and closed mapping;
- global update and next-route cursors;
- exact consumed route/source/file order; and
- provider sampler state.

`load_checkpoint_state()` validates all of those before loading the five
existing trainer checkpoints and restoring the provider state. One
source-training epoch is exactly one complete `C1 -> C2 -> C3` cycle, i.e.
three route updates. The only
`V023FiveArmOrchestratorConfig.formal(...)` cadence is **100 complete
source-training epochs = 300 route updates**. It sets `formal_use=True`, which
rejects any other update cadence. The plain config permits another positive
cadence solely for bounded implementation tests; it is not a formal run
setting. This is a source-training epoch, not one simulator episode.

## Exact target-batch adapter gaps

The current `.scratch/multi-catfish-v023-target-batch-adapter` supplies typed
C1/C2 mode inputs and an unlabelled C3 input container, but it does **not** yet
provide this protocol. A real adapter needs exactly these additional fields and
methods:

1. `next_batch(route, source, update_cursor)` with both `source="neutral"`
   and `source="informed"` for **each** of C1, C2, and C3. Its current C3
   inputs have no source-mode identity, so it must expose separately verified
   neutral and informed C3 `LCSRSC3SampledBatch` plus surfaces.
2. A stable authenticated `file_id` on every returned batch. For C1/C2 it must
   identify the manifest-listed source file(s) in their exact aggregation
   order; for C3 it must identify the authenticated source-artifact
   record/arrays and sampled-batch source in the same order.
3. `sampler_state()` and `load_sampler_state(state)`. The state must include
   every source-local file/batch cursor and any C3 class-balanced sampler RNG
   or draw position needed for the next `next_batch` result to be bitwise
   identical after resume.
4. A per-return source identity that is checked against the requested route
   and source, with no retagging or mixing of informed and neutral rows.

The existing adapter's aggregate `c1_pair_batch` / `c2_pair_batch` and static
dispatch metadata are not enough by themselves to recover source-local file
order or a C3 sampler position. No connection is made here until those fields
exist.

## Fast tests

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-five-arm-learner-orchestrator/test_v023_five_arm_learner_orchestrator.py
```

The tests use small in-memory actual-class fixtures only. They neither read a
real target artifact nor represent training/effectiveness evidence.
