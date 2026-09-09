# V0.23 target-batch adapter

This is a bounded, read-only plumbing seam for the heterogeneous V0.23
learner inputs.  It owns only `target_batch_adapter.py` and its fast contract
tests.  It does not run a simulator, train a network, open `TEST`, or make a
scientific claim.

## C1/C2 loader

`load_completed_target_artifact(root)` accepts only the final output of the
V0.23 C1/C2 target-generation controller.  The root must contain:

* a regular `COMPLETE` marker whose bytes authenticate `MANIFEST.sha256`;
* a filename-sorted SHA-256 manifest covering `receipt.json` and every target
  JSON file, with no unlisted files or symlinks;
* canonical ASCII `receipt.json` with the current schema, closed no-training
  flags, source/formula/code-closure digests, both `parallel_modes`, both
  shard receipts, and C1/C2 dataset and row-binding metadata;
* every `c1-{mode}-world-{world}.json` and
  `c2-{mode}-world-{world}.json` referenced by that receipt.

Each dataset is then decoded by the current
`EEAxisOpeningDataset`/`EEAxisTemporalDataset` readers and verified again.
The loader checks world/path/row counts, source lineage, formula constants,
row bindings, route provenance, and mode identity.  Informed and neutral
inputs remain separate in `V023ModeInputs`; its `c1_pair_batch` and
`c2_pair_batch` fields are actual immutable `EEAxisPairBatch` objects.  The
per-world typed route envelopes remain available through
`c1_route_batches`/`c2_route_batches`.

`load_completed_target_batches(root, mode="informed")` is the convenience
entry point when one mode is explicitly selected.  The loader never invokes
`update_three_route_cycle` or any other learner operation.

## C3 input seam and schedule

`load_lcsrs_c3_inputs` accepts current typed `LCSRSAnchorSurface` (or
`LCSRSAnchorRecord`) values and current typed `LCSRSC3SampledBatch` values.
It retains the supplied positional anchor order, verifies every sampled
anchor/class/cell/target against the selected target surface, and returns
`V023C3Inputs`.  By default the selected targets are the physical surface
targets (the informed path).  A caller may instead pass
`normalized_targets_by_anchor` as an ordered sequence or an exact integer-keyed
mapping `{0: target_for_surface_0, ...}`.  Each selected array is copied to
read-only `float32`, must match its corresponding physical surface shape, must
be finite, and must be exactly zero outside `SUPPORTED` cells.  The physical
surfaces are never rewritten or replaced; only sampled labels may use the
explicit selected target arrays.
`load_lcsrs_c3_source_artifact` is a thin wrapper around the existing
authenticated C3 source-artifact loader and then applies the same typed
validation; it does not duplicate the NPZ/index serializer.

`build_route_schedule(mode_inputs, c3_inputs, episodes=1)` returns only
`RouteDispatch(episode_index, route, batch_index)` records.  For each episode
it emits all C1 batches, then all C2 batches, then all C3 sampled batches.  The
same deterministic schedule shape supports a one-episode plumbing slice or a
later 100-episode runner; this directory does not execute either one.

## Real-artifact gaps recorded at this boundary

No completed target root or persisted C3 sampled-batch receipt is present in
this checkout, so the tests use tiny synthetic authenticated receipts only.
The following are deliberately not guessed or fabricated by this adapter:

1. The upstream predecision materialization receipt's C2 informed *family*
   rule is `c2-hold-or-max-lagged-sinr-rival-predecision-v1`; the completed
   target-generation receipt may carry that family metadata alongside rows
   whose `source_rule` is a concrete current typed value such as
   `incumbent-hold` or `max-lagged-candidate-sinr-rival`.  The adapter accepts
   that combination and keeps checking the row-level typed rule.  A target row
   carrying the family name itself is rejected explicitly by the current
   `EEAxisTemporalPair` boundary.  No formula is changed here to work around
   that distinction.
2. The C1/C2 target-generation output schema contains dataset files and row
   bindings, but no serialized C3 `LCSRSC3SampledBatch` stream.  A real C3
   learner handoff still needs an authenticated sampled-batch sidecar (or an
   equivalent producer receipt) containing the positional anchor indices,
   row classes, user/action indices, normalized targets, and the surface
   identity/order to which those indices refer.  Until then this seam accepts
   only already-materialized current typed C3 objects.
3. The target receipt's C2 `candidate_physical_key` binding is retained and
   digest-checked, but the current temporal-pair type does not carry that key;
   the adapter therefore cannot derive it from a temporal row and only checks
   the row's authenticated anchor, step, focal user, common field, and
   comparison identity.  This is an explicit provenance limit, not an
   inferred candidate identity.

Run the bounded checks with:

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-target-batch-adapter/test_target_batch_adapter.py
```
