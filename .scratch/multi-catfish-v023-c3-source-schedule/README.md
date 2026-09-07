# V0.23 C3 paired source schedule

Status: bounded implementation-only plumbing. This directory performs no SSH,
simulator call, model construction, optimizer step, fit, episode training,
`TEST` access, or real artifact write.

`v023_c3_source_schedule.py` builds the post-R7 C3 source schedule in memory.
It accepts only actual current `LCSRSAnchorRecord` values and an explicit
`R7GoDecisionBinding` copied from an independently authenticated final R7
result. A preflight or `AUTHORIZED_ONE_SHOT` launch receipt is not a GO.

## Frozen construction

1. Reauthenticate and canonically order records by
   `(world_id, phase, anchor_id)`. Their world set must be exactly
   `2026121801..2026121808`, and their schedule-specific record-panel digest
   must match the GO binding.
2. Call the current `build_lcsrs_matched_placebo` exactly once over the global
   record panel with `MCRL_V023_LCSRS_MATCHED_PLACEBO_V1`. World is part of the
   frozen stratum, so every cyclic mapping remains within one world. Global
   SUPPORTED coverage must be at least the frozen `0.80` threshold.
3. Retain the original typed `LCSRSAnchorSurface` objects. Expose separate
   read-only `informed_targets_by_anchor` and `neutral_targets_by_anchor`; no
   neutral surface is constructed because a surface's pair targets are the
   measured physical targets.
4. Derive one PCG64 seed from the caller's explicit unsigned 64-bit seed under
   the frozen domain
   `MCRL_V023_LCSRS_C3_PAIRED_SOURCE_SCHEDULE_PCG64_V1`. Draw each 256-row
   coordinate batch once, then construct the informed and neutral
   `LCSRSC3SampledBatch` values from those same coordinates. Only SUPPORTED
   labels can differ; REFERENCE, CONTROL, and MASKED target surfaces remain
   exact zero.
5. Precompute exactly the declared 100 or 500 source-training epochs. There is
   no wraparound: `batch_for(source, epoch_index)` fails at `N`.

The canonical in-memory receipt binds the full ordered record list, informed
and neutral target-surface hashes, frozen placebo digest and mapping hash,
per-epoch paired-draw and arm-batch hashes, distinct arm source identities,
R7 result/source/launch/code/preflight/contract hashes, epoch budget, seed
domain and derived seed, learner configuration, and all closed execution
boundaries. `receipt_sha256` is the SHA-256 of the canonical body before the
seal field is added.

`context_status` is retained exactly in the GO binding. The base contract says
that an R7 C3 GO can coexist with a C1/C2 context HOLD, but such a HOLD still
blocks any later episode contract. This schedule itself is only offline source
plumbing and does not reinterpret that status.

## Current target-adapter/provider integration

The current target adapter's `V023C3Inputs` now retains
`normalized_targets_by_anchor` separately from `(surfaces, sampled_batches)`.
It validates the selected target count, float32 shape/finiteness, exact-zero
non-SUPPORTED cells, original surface/class order, and every sampled label.
Consequently both arms can reuse the same physical surfaces without mutating
`LCSRSAnchorSurface.normalized_targets`:

1. informed inputs use `informed_targets_by_anchor` with
   `informed_batches`;
2. neutral inputs use `neutral_targets_by_anchor` with `neutral_batches`; and
3. the provider bridge receives those two descriptors in distinct
   `C3SourceBinding` values carrying `informed_source_id` and
   `neutral_source_id`.

The provider keeps the exact-N check, source-local cursors, defensive batch
copies, and no-sampling rule.  Focused adapter and provider-bridge tests cover
the selected-target path.  No orchestrator/model change is needed.  In
particular, do not retag a neutral batch as informed, rewrite a physical
surface target, or create placebo `LCSRSPairTargets`.

## Remaining real inputs

No persisted final R7 GO receipt is present in this checkout. A real handoff
still needs:

- the independently verified final R7 result and its exact byte digest,
  containing `PASS_FINAL_INTEGRITY`, `VERIFIED`, and
  `GO_FIXED_LEARNER_SCREEN_CONTRACT_R7`;
- its authenticated launch/code/preflight/source-manifest digests and exact
  reconstructed R7 `LCSRSAnchorRecord` panel;
- the source-manifest-to-record-panel binding computed with
  `canonical_record_panel_sha256`;
- a separately frozen learner-screen choice of 100 or 500 epochs and its
  explicit schedule seed; and
- for end-to-end five-arm use, the separately authenticated C1/C2 informed and
  neutral target root expected by the existing provider bridge.

Those inputs are not invented by this implementation.

Run only the focused tests:

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-c3-source-schedule/test_v023_c3_source_schedule.py
```
