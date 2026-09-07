# Engineering lane — stage-C fix pass 4 verification

**Committed `b1aff0e2ac91cfc84fad45e8fab89ed1fdf7d8b6`** (tree `d2332f18`) on
`wip/multi-catfish-v023-20260907`. All seven work-list items verified; suite and manifests green.
Claim ceiling `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`.

## 1. Per-id status (all paths relative to repo root)

| id | status | site |
|---|---|---|
| E2 | FIXED | `…-physical-evaluation/v023_c1c2_successor_physical_runner.py:377-390` — when the admission record declares `PASS_SOURCE_TRAINING_INTEGRITY` the status is read from `epoch_100_integrity.decision` (:381); other declarations keep the top-level `status`/`overall_token` read, which is what the real Stage-B writer emits (`…-stagec-launch/run_v023_c1c2_successor_stage_b.py:113`). |
| E3 | FIXED | `…-stagec-launch/run_v023_c1c2_successor_stage_c_chunks.py:169-296` — exact contiguous chunk-id coverage, checkpoint/rung cadence, per-boundary digest bindings **and** full contents; producer emits `arm_order` + `barrier_artifacts` at `…physical_runner.py:2132,2158,2165`. Tests `…test_v023_c1c2_successor_stagec_launch.py:477,543,552`. |
| E4 | FIXED | `…-stagec-launch/verify_v023_c1c2_successor_stagec.py:369-380` (verify_finished authenticates + materialises the supplement), `:143-166` (formal admission Stage-A/B inputs must equal the supplement), `:840` (`--admission-supplement` now `required=True`). Test `:191`. |
| E5 | FIXED | `verify_…_stagec.py:346-352` — arm **set** plus explicit `arm_order`; producer writes `arm_order` at `…physical_runner.py:2256,2296,2323,2348`. Test `:585`. `stagec_common.py:393-398` was already order-independent. |
| E6 | FIXED | `…physical_runner.py:1762` — `len(receipts) != end - start` (chunk-local). Test `…-physical-evaluation/test_cadence_resume.py:560`. |
| E7 | FIXED | `…-stagec-launch/accept_stage_c_chunk_equivalence.py:199-272` — whole canonical checkpoint/rung compared; exclusion set is exactly the sealed 16 (`stagec_common.py:58` == addendum §2). Test `:334`. |
| E9 | FIXED (caveat) | `…-ch5-figure-pipeline/test_render_v023_development_curves.py:245` now calls `verify_finished()` at `:328`. |

**E2 fixture is producer-written, not hand-typed:** `…-physical-evaluation/test_world_plan_and_bindings.py:168`
`_write_producer_source_receipt()` calls the real writer
`v023_two_route_source_training_runner.py:1151 _write_final_receipt` (plus `_checkpoint_path`/`_write_sidecar`);
the receipt is consumed by the test at `:210`.

## 2. Gates

- Exact requested pytest (five packages, launch package run after regeneration):
  **140 passed, 1 skipped in 283.88 s, exit 0.** The skip is
  `test_v023_c1c2_successor_stagec_launch.py:882` "workspace already contains the required post-fix adapter".
- Stage-C manifest `--write` then `--check`: `STAGEC_CODE_MANIFEST_CURRENT entries=270
  sha256=675431fa4c7132af35f9c62c49c3265bc434aa9daaeee2afa2cdae1bccb68ad8`; pin agrees; sync list 273 paths
  (membership unchanged from `e8f4cc57`, only digests moved). Addendum `9673928f…` and sidecar `7738bfc9…`
  are members; **0/246 closure paths missing**.
- Launch manifest `--write` then `--check`: `SUCCESSOR_LAUNCH_MANIFEST_CURRENT
  sha256=e603106ddad8854ebf3fcc9244a42db6de5611e3a17a9ccb0a9ef16cdd1d02ee`; `file_count` 283
  (246 closure + 14 additions + 23 stage-C members).
- `sync_launch_v023_c1c2_successor_server.sh --dry-run` → exit 2, expected local refusal:
  `SUCCESSOR_EXECUTION_BINDINGS_FAIL: required r8 target root is absent: /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`
  then `SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current`.

## 3. Audit-reproduction re-probes (package fixtures; writes confined to `/tmp`)

- **E3** empty `chunk_receipts` + `{}` checkpoint/rung → refused, `previous barrier lacks chunk provenance`.
  Stronger variant (`{}` artifacts with `barrier_artifacts` digests re-sealed over them) → refused,
  `previous barrier checkpoint contents drifted`. Unmutated barrier → `AUTHENTICATED_CUMULATIVE_BARRIER`.
- **E5** canonical (sorted-key) serialisation yields `['BASELINE','DROP_C1','DROP_C2','FULL2']`; accepted with
  explicit `arm_order`, refused with a reversed one. `verify_stage_c_admission_mapping` likewise accepts
  BASELINE-first and normalises to ARMS order.
- **E7** flipping `scientific_disposition_emitted` in the merged rung →
  `bitwise chunk equivalence differs first at rungs[100].scientific_disposition_emitted`.
- **E2** producer receipt carries no top-level `status`/`overall_token`; PASS accepted. Same writer with
  `decision="STOP_SOURCE_TRAINING_INTEGRITY"` → `predecessor PASS status disagrees with receipt`.

## 4. Findings (non-blocking, no code touched)

1. **(d) procedural** `…-stagec-launch/sync_launch_v023_c1c2_successor_stagec_server.sh:40-42` now skips the
   stage-C manifest `--check` under `--dry-run`. The manifest is current, so the skip buys nothing and lets a
   dry-run pass over a drifted manifest — against charter rule 11. Recommend reverting.
2. **(b) test gap** E9's `verify_finished()` call stubs seven boundary functions, including
   `_verify_formal_admission` itself, so the figure test does not exercise the E4 admission path.
3. **(b) minor, pre-existing** `…-engineering-lane/SHA256SUMS` (20 rows) omits the tracked
   `partial_merge_dryrun.py` and `test_partial_merge_dryrun.py`.

## 5. Sync

Five packages rsynced local → `sat:/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/` with
`--exclude __pycache__`; shadow copies of `verify_…_stagec.py` (`35e74755…`) and
`v023_c1c2_successor_physical_runner.py` (`d65ea18b…`) match local and codex's declared digests.
