# V0.23 heterogeneous three-route learner seam

Status: implementation-only scratch seam. It does not launch a simulator,
open `TEST`, run a training job, or make a scientific claim.

`v023_heterogeneous_trainer.py` accepts an already constructed current
`EEAxisLCSRSThreeRoute` and does not create replacement heads, optimizers, or a
checkpoint format.

The update boundary is:

| route | input | model state used |
| --- | --- | --- |
| C1 | existing `EEAxisPairBatch` | `model.q1`, `model.optimizers[0]` |
| C2 | existing `EEAxisPairBatch` | `model.q2`, `model.optimizers[1]` |
| C3 | existing `LCSRSC3SampledBatch` plus `Sequence[LCSRSAnchorSurface]` | `model.q3`, `model.optimizers[2]` |

C1/C2 use the current Q12 configuration values directly: `kappa_bits`,
`beta`, and the route entry in `loss_weights`. The objective is the existing
action-shared pairwise residual plus reference gauge, with no next-state or
bootstrap value. C3 calls the current `lcsrs_c3_training_step` directly, so
its frozen learner constants remain owned by the current runtime module.

Every update clears stale gradients, checks that off-route gradients remain
empty, and verifies that off-route parameters are bitwise unchanged. Checkpoint
and resume call `EEAxisLCSRSThreeRoute.checkpoint_state` and
`load_checkpoint_state` unchanged; the seam adds no update schedule or sampler
state.

Fast proof command:

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-heterogeneous-trainer/test_v023_heterogeneous_trainer.py
```

## Exact real-target JSON loader gaps

This seam intentionally accepts typed in-memory learner inputs. The remaining
loader work for a real target root is exactly:

1. Authenticate the target root's `receipt.json` and `MANIFEST.sha256`, then
   bind every per-world file hash and the receipt's source/formula constants
   before constructing learner batches. The target-generation output pattern
   is `c1-{informed|neutral}-world-<world>.json` and
   `c2-{informed|neutral}-world-<world>.json`.
2. For C1, call the existing `read_opening_dataset(path)` and then
   `dataset.c1_batch().pair_batch`; reject any dataset whose route batch is not
   C1. For C2, call the existing `read_temporal_dataset(path)`, then
   `dataset.route_batch().pair_batch`; reject any route other than C2. No
   direct JSON-to-array decoder belongs in this seam.
3. Stack the verified per-world C1 files into one route-local
   `EEAxisPairBatch`, and do the same separately for C2. The loader still needs
   to preserve the source-manifest/checkpoint/common-field identities while
   preventing informed and neutral files from being mixed or silently
   relabelled. This directory currently provides no aggregation or mode
   scheduler.
4. Materialize C3 from the separate V0.23 source-artifact panel, not from the
   C1/C2 target files: reopen `source/world-<world>.json` with its
   `world-<world>.arrays.npz` sidecar (`allow_pickle=False`), reconstruct and
   authenticate `LCSRSAnchorRecord`/`LCSRSAnchorSurface`, then draw the
   existing `LCSRSC3SampledBatch` with the declared class-balanced sampler.
   This seam does not implement that source-artifact loader or sampler-state
   persistence.
5. Bind the real run's declared route order, learner seeds, batch/update
   schedule, and sampler state around these typed objects. The existing
   three-route checkpoint stores heads and optimizers only; it does not store
   a JSON-loader cursor, C1/C2 file order, or C3 sampler RNG state, so resume
   parity for a real sampled stream remains an integration gap.

The focused tests use only small in-memory actual classes and do not consume a
real target root.
