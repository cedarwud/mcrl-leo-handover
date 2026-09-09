# Controller-owned scheduling-addendum section 2 completion

This is the exact replacement text for section 2 of
`V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md`. The Stage-C
implementation owner does not own that authority file and has not sealed it.
The controller applies this text, removes section 1 from the operative sealed
content (the withdrawal record may remain clearly non-operative), and seals the
completed addendum.

## 2. Result-equivalent episode chunking

- Persisted cross-episode stream list: `StepEnvironment._age_rng` only.
  Environment RNG and `_mobility_rng` are recreated or replaced per episode;
  keyed fading is world-derived. Boundary construction is valid only while
  `segment_warm_start == "uniform-episode-length"` and replays the actual
  `integers(0, 10, size=100)` draws from the episode-1-spawned age stream.
- Formal chunks are contiguous 100-aligned ranges with exclusive root locks,
  write-once episode records, authenticated resume states, complete checkpoints
  published before chunk-complete receipts, and append-only execution attempts.
  Merge verifies every indexed file hash, checkpoint, boundary transition,
  provenance binding, and execution date. It orders by episode and frozen arm
  order and applies the unchanged per-episode aggregation and `math.fsum` over
  individual episode totals. Only complete four-arm coverage at 3000 may emit a
  scientific disposition.
- Cumulative release barriers are exactly 100, 500, 1500, and 3000. Only chunks
  in the current interval may launch. Shared capacity is
  `(logical cores - 2) - occupied Stage-C workers` across arms and sessions;
  OMP, OpenBLAS, MKL, and NumExpr threads are each one.
- Stage-A and Stage-B PASS receipts enter through a separately sealed,
  append-only supplement that references the prospective execution bindings.
  All four arms, including BASELINE, authenticate that supplement and the same
  runtime admission. There is no early-BASELINE admission mode.
- Mandatory server acceptance compares direct sequential execution with
  chunked execution for all four arms, including actual merged episode, rung,
  checkpoint, receipt, and resume-state artifacts by bitwise binary64 value.
  The explicit provenance exclusion list is: `schema`, `status`, `chunk_id`,
  `range`, `start_boundary`, `end_boundary`,
  `start_boundary_state_sha256`, `end_boundary_state_sha256`, `threads`,
  `runtime`, `parent_checkpoint`, `ordered_episode_records`,
  `ordered_episode_record_digest`, `started_utc`, `ended_utc`, and
  `execution_mode`. No other field is excluded.
- Acceptance procedure:
  `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/ACCEPTANCE-SERVER-EQUIVALENCE.md`,
  SHA-256
  `6d3785efc206073dd2b8b1e299113614997dd558e33a32a4b9cf1dce822e0f68`.
- Forbidden: episode reordering, outcome-selected chunks, per-chunk scientific
  stopping, altered policies, TEST, computation without authenticated
  acceptance, and continuation beyond 3000 without the existing separately
  sealed continuation authority.
