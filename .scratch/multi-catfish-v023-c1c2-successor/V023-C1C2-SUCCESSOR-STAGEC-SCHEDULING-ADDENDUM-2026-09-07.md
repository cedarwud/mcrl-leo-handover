# V0.23 C1/C2 successor — stage-C execution-only scheduling addendum (DRAFT, 2026-09-07 17:50 UTC)

Status: `DRAFT_PRE_FREEZE`. Execution-only. It changes no scientific declaration: arms, plan, estimand, prediction,
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
- Episode outcomes are NOT seed-only independent: the environment's warm-start age RNG stream (`_age_rng`) persists
  across episodes. Fresh-start chunks are therefore not equivalent. Chunks must start from the exact boundary state
  produced by replaying the original RNG draws (cheap; no physics), authenticated against a boundary table.
- Chunks are contiguous, 100-aligned ranges with exclusive write-once roots, cadence checkpoints and authenticated
  boundary states; merge by episode index in frozen arm order, re-applying the unchanged per-episode aggregation and
  `math.fsum` over individual episode totals at each cumulative boundary (100/500/1500/3000); only the complete 3000
  boundary adjudicates. Receipts bind arm/range/chunk id, plan/schedule digests, provenance, boundary-state hashes,
  threads/runtime, parent checkpoint, ordered episode-record digest.
- Mandatory acceptance BEFORE formal use: on the server, sequential 200 episodes versus 2×100 chunks for every arm →
  identical episode/pool/rung values (bitwise), identical boundary states and receipts modulo enumerated provenance fields;
  interruption/resume and duplicate-chunk refusal tested.
- Forbidden: episode reordering, per-chunk scientific stopping, outcome-selected chunks, altered policies, TEST; workers
  ≤ cores−2, one numerical thread each; cumulative barriers enforced.

## 3. Cost basis (measured 2026-09-07)
Per episode: learned arms ≈ 13.6 s, BASELINE 1.66 s (V4). 3 learned arms × 3000 ≈ 34 CPU-h → ≈ 2.2–3.3 h wall on 16
workers with barriers; BASELINE 3000 ≈ 1.4 h single worker.

## 4. Freeze
This addendum is sealed (sha sidecar) together with the stage-C code manifest before any successor computation; it is
referenced by the stage-A and stage-C execution bindings.
