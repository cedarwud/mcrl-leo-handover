# V0.23 C1/C2 successor — stage-C execution-only scheduling addendum, R2 (2026-09-08 02:55 UTC)

R2 is the versioned successor of the sealed 2026-09-07 addendum (predecessor body sha256 `9673928f20fae6d347b848e09d351ddd9bf0197a71b975ddc0106d0bdbf74d1e`, preserved unchanged beside this file).
§1 (withdrawn) and §2 (result-equivalent episode chunking; acceptance-procedure digest `b6d6ab8baa07011d3d72ea6b54efa9f25d6f666ca47c837af75cc359c10b17ff`)
are byte-identical to the predecessor; §3 is new (administrative closure without continuation; authorised chunked continuation), the
former §3–§4 are renumbered §4–§5. Ruling: `.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-STAGEC-PREBIND-PROCEDURE-CODEX-GPT6-ASTRA-2026-09-08.md`.


Status: `SEALED_EXECUTION_ONLY` (sealed 2026-09-07 22:05 UTC by the controller under the owner's delegation; §2 operative, §1 withdrawn and non-operative; acceptance-procedure digest re-derived after chunking fix pass 3). Execution-only. It changes no scientific declaration: arms, plan, estimand, prediction,
falsifier, dispositions, thresholds and claim ceilings remain exactly those of the sealed
`V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md` (sha `f27d0500…`) and contract §6. Basis: astra ruling
`ADJUDICATION-STAGEC-BASELINE-DECOUPLING-AND-EPISODE-CHUNKING-CODEX-GPT6-ASTRA-2026-09-07.md`
(`ASTRA_BASELINE_DECOUPLING=ALLOWED_WITH_CONDITIONS`, `ASTRA_EPISODE_CHUNKING=EQUIVALENT_WITH_CONDITIONS`).

## 1. Early BASELINE materialisation — WITHDRAWN 19:10 UTC
(Controller decision after the implementation audit: BASELINE runs with the learned arms after stage A/B; the all-four-arm acceptance requirement stands and no ruling amendment is sought. The text below is retained for the record and is NOT part of the sealed addendum.)

### 1 (withdrawn). Early BASELINE materialisation (episodes 1–3000 only)
- BASELINE (frozen pre-Catfish MODQN, checkpoint `e6b063ef…`, adapter with `contract_fields_excluded`, `routes=[]`) has no
  dependency on stage A. Its episodes 1–3000 may be executed BEFORE the learned arms' exports exist, under the same plan
  identity (`866d28e0…`), the same per-episode keyed-field derivation and the same runner code as the four-arm run.
- Preconditions (all before any successor computation, including stage A's one-epoch diagnostic): the complete stage-C
  runner, independent verifier, configuration, plan, RNG/boundary policy, baseline checkpoint/status/adapter closure and
  THIS addendum are bound and sealed; the whole-contract admission requirements are resolved explicitly (early binding of
  baseline inputs waives nothing).
- Early BASELINE outputs are per-arm evidence with actual execution dates and provenance. Four-arm rung receipts are
  published only after stage-A integrity, stage-B plumbing and complete matched coverage pass. The claim is numerical
  equivalence to a simultaneous run, never simultaneous execution. No reselection or tuning from early outcomes.
- **Early BASELINE 9000 is disallowed.** Episodes 3001–9000 for any arm require `C1C2_DEVELOPMENT_PREDICTION_HELD` at
  3000 and the owner notification of contract §6.

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
  `b6d6ab8baa07011d3d72ea6b54efa9f25d6f666ca47c837af75cc359c10b17ff`.
- Forbidden: episode reordering, outcome-selected chunks, per-chunk scientific
  stopping, altered policies, TEST, computation without authenticated
  acceptance, and continuation beyond 3000 without the existing separately
  sealed continuation authority.

## 3. Administrative closure without continuation (new in R2; astra ruling `ASTRA_Q1=ADMISSIBLE`, 2026-09-08)

After independently verified complete four-arm coverage at 3000 and `C1C2_DEVELOPMENT_PREDICTION_HELD`, the owner may
explicitly decline continuation, or defer it and explicitly request closure of this reporting root. A written decision, recorded
verbatim with notification/reply timestamps, channel and controller identity, shall be authenticated by a named SHA-256 sidecar
and bound to the execution bindings, plan, policy mapping, preserved 3000 result, HELD token and checkpoint. Silence, an
unanswered notification, or deferral without closure instruction is insufficient. After confirming that no continuation episodes
have executed and no continuation is active, the controller may publish an administrative-closure receipt and whole-tree seal.
The original result, token and scientific interpretation remain unchanged. Every resulting figure shall state "continuation to
9000 not performed". Closure does not authorize reopening or modifying the sealed root. Any later continuation requires
separately declared authority preserving this root and its provenance. FALSIFIED continues to prohibit continuation.

Implementation binding (execution-only): `seal_stage_c_declined_continuation.py` in the stage-C launch bundle publishes
`ADMINISTRATIVE-CLOSURE.json` (+ `.sha256`) and then `MANIFEST.sha256` and `COMPLETE` (last); the figure pipeline authenticates
the closure receipt and renders the mandatory caption; the figure manifest carries the HELD disposition and result digest,
completed boundary 3000, planned maximum 9000, `continuation_performed=false`, the decision reason, marker and receipt hashes,
bindings/plan/policy/tree-seal identities, rung coverage, the caption text, the unchanged TRAIN-development claim ceiling and the
renderer digest. This section declares no new scientific gate and changes no falsifier, arm, plan, seed, horizon or acceptance rule.

Continuation path (astra `ASTRA_Q2=BUILD_NOW`): an authorised continuation 3001–9000 may run through the result-equivalent
chunk assembler of §2 (barriers 6000 and 9000) under the contract's notification + continuation-authority chain, preserving the
sealed ≤ 3000 prefix bytes, the plan `866d28e0…`, the four arms, the numerical kernel, the boundary-state stream replay, the
resource limits and the 100-episode cadence; it emits `continuation-result.json` at 9000, never a second disposition, and seals
only after independent verification. The §2 acceptance definition is unchanged; the four-arm 200-vs-2×100 acceptance is re-run
against the final bound code before any formal chunk.

## 4. Cost basis (measured 2026-09-07)
Per episode: learned arms ≈ 13.6 s, BASELINE 1.66 s (V4). 3 learned arms × 3000 ≈ 34 CPU-h → ≈ 2.2–3.3 h wall on 16
workers with barriers; BASELINE 3000 ≈ 1.4 h single worker.

## 5. Freeze
This addendum is sealed (sha sidecar) together with the stage-C code manifest before any successor computation; it is
referenced by the stage-A and stage-C execution bindings.
