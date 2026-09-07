# V0.23 post-Gate C3 source-update checkpoint plumbing

This isolated area is implementation-only. It preserves the current V0.23
source artifact and learner modules, including the frozen `2,000`-update Gate;
it does not change Gate authority or launch a run.

The ladder contract is:

```text
source arm:       INFORMED or externally supplied NEUTRAL_SOURCE
student seeds:    2026135101, 2026135102, 2026135103
learner updates:  0, 100, 200, ..., 2000
device:           CPU
```

`AuthenticatedV023SourceProvider` is intentionally an input seam. A future
caller may adapt the existing authenticated V0.23 source panel with
`authenticated_source_from_v023_panel`, or provide an external source bundle
directly. This area does not construct a neutral dataset or infer a deployment
policy.

`v023_sealed_source_provider.py` is the path-backed adapter for the future
sealed Gate output. `SealedV023SourceProvider` lazily reopens the exact source
manifest and eight JSON/NPZ shards, then verifies `result.json`,
`MANIFEST.sha256`, and `COMPLETE`. Every call re-authenticates the trees and
returns either `INFORMED` or `NEUTRAL_SOURCE`; the latter is produced only by
the existing frozen `MCRL_V023_LCSRS_MATCHED_PLACEBO_V1` permutation over the
same retained rows. It never invents neutral rows or reads outcome metrics.

The resulting source attestation binds the source-manifest body and byte
hashes, result and result-manifest byte hashes, fixed source-artifact schema,
all anchor hashes, the exact SUPPORTED-row count, and the frozen 2,000-update
budget. The adapter rejects symlinked/missing files, malformed or cross-world
placebo mappings, TEST/episode flags, source/result hash drift, schema drift,
and target/mask shape drift. The current Gate runner, authority, source code,
and Luna contingency area are unchanged.

Each `checkpoint-XXXXXX.json` receipt is paired with a `.state.pt` sidecar and
binds the source-manifest digest, source attestation, frozen learner config and
hash, seed, initial/current model hashes, exact update count, optimizer state,
sampler RNG state, and torch RNG state. The receipt and sidecar explicitly mark
the boundary as a learner update, not an episode checkpoint. All axis points
are retained; there is no early stopping, best-checkpoint selection,
outcome-dependent selection, TEST split, physical episode, evaluation, or
deployment action.

## Focused checks

Run the isolated tests with the project training environment:

```text
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-postgate/test_postgate_c3_update_ladder.py
```

The tests cover the fixed axis/seed contract, learner-versus-episode
checkpoint identity, deterministic resume, state hash fail-closed behavior,
and the requirement that `NEUTRAL_SOURCE` is supplied externally. The sealed
provider tests cover matched-placebo arm binding, equal row/update budgets,
result-manifest/COMPLETE binding, source/result boundary rejection,
cross-world leakage, shape drift, symlink rejection, and lazy arm/seed input
validation.

Run both isolated suites with:

```text
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-postgate/test_postgate_c3_update_ladder.py \
  .scratch/multi-catfish-v023-postgate/test_v023_sealed_source_provider.py
```
