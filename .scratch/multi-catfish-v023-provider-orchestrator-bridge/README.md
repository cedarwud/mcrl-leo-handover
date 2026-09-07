# V0.23 provider/orchestrator bridge

Status: implementation-only plumbing. This directory is the deterministic
provider boundary between the authenticated C1/C2 target-batch adapter and the
isolated five-arm learner orchestrator. It does not run a simulator, launch
training, open `TEST`, load D40, write a checkpoint/artifact, use SSH, or
alter a learner objective.

`V023ProviderOrchestratorBridge` satisfies the existing
`DeterministicRouteBatchProvider` protocol. Its constructor takes a real
`V023TargetArtifact`, reopens that root through
`load_completed_target_artifact`, and uses the resulting authenticated
`V023ModeInputs` only. It uses the adapter's already verified aggregate C1/C2
pair batches, matching the frozen 500-epoch convention: one full-panel update
per route per source-training epoch. `ProvidedRouteBatch.file_id` is a
domain-separated panel digest over the typed batch and its ordered
manifest-listed member filenames; those member filenames remain bound in the
sampler state.

For C3 the caller supplies two `C3SourceBinding` values. Each binding contains
one fixed source label (`neutral` or `informed`), a nonempty stable source
identity, and actual typed `V023C3Inputs`. Both bindings, their surfaces, and
their already sampled `LCSRSC3SampledBatch` values are checked. The bridge
revalidates and retains each input's ordered
`normalized_targets_by_anchor` separately from the physical surfaces; thus a
neutral target selection can be consumed without manufacturing or mutating an
`LCSRSAnchorSurface`. Each source
must carry exactly one precomputed batch per declared source-training epoch.
The two source identities must differ. The bridge has no fallback from one C3
source to the other and never creates a sample or a surface.

## Determinism and resume

Calls are fail-closed in the only order used by the orchestrator:

```text
C1 neutral, C1 informed, C2 neutral, C2 informed, C3 neutral, C3 informed
```

Each source has its own `(route, source)` cursor. C1/C2 repeat the authenticated
full panel for the exact declared number of epochs; C3 consumes its precomputed
batch schedule without wrapping. Every route then exhausts. `sampler_state()`
records the epoch budget, all six cursors, the next route/source position, each
panel identity, and its manifest members. `load_sampler_state()` accepts only
an exact identity-compatible state whose source-local cursors agree with the
closed order.

Every returned C1/C2 or C3 batch is a fresh, read-only current typed object
with byte-identical values. This prevents a caller or one learner arm from
sharing mutable array storage with the authenticated source or a later
provider return. C3 surfaces are passed through as the already typed,
validated source surfaces; they are never copied, reordered, or retagged.

## Remaining real-artifact gaps

1. The current C1/C2 target root is authenticated and contains manifest-listed
   per-world files, which this bridge consumes directly. No completed real
   target root is supplied in this checkout, so its focused test uses the
   sibling adapter's tiny authenticated synthetic fixture.
2. Current `V023C3Inputs` has typed surfaces and sampled batches but no
   persistent producer receipt or canonical C3 sidecar filename. Therefore
   `C3SourceBinding.source_id` is explicit caller-provided provenance, not an
   inferred or invented filename. A production C3 handoff still needs an
   authenticated sidecar binding that identity to the surface order and every
   sampled batch.
3. This seam is not an execution authorization. A deterministic provider and
   its focused tests do not establish a simulator run, a training result, a
   TEST result, or any efficacy claim.

Run only the focused test file:

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-provider-orchestrator-bridge/test_v023_provider_orchestrator_bridge.py
```
