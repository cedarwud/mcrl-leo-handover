# Engineering lane — stage-A fix pass 4 + V2-synthetic rerun #3 (2026-09-07 18:00–18:10 UTC)

Ceiling `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. NON-FORMAL; no edits, no bypasses. Losses not interpreted.

## Part 1 — fix pass 4 + defect C

### (a) Claimed status per id, re-checked against the live tree — all six confirmed

- **L3 FIXED.** `successor_launch_common.py:134` closed 3-name `ALLOWED_LATER_CONTRACT_DEFERRALS`, enforced `:400-407`.
  `:485 assert_predetermined_stage_c_bound` refuses a DEFERRED `evaluation_runner_manifest_sha256` and calls
  `:438 verify_stage_c_code_bundle`, which reads the stage-C `…-STAGEC-CODE-MANIFEST.sha256` + frozen pin and requires
  exact physical-package cover plus the stage-C verifier row. Callers `preflight_…:228`, `common:657`.
- **N1/L5 FIXED.** Preflight records `launch_manifest_path/sha256`, `execution_bindings_path/sha256`,
  `requested_output_root` (`preflight_…:334-344`); `common:619` re-verifies manifest, bindings sidecar, contract
  placeholders, stage-C pin, both digests and the root (`:684-694`); callers `run_…_formal.py:58`, `verify_…:253`.
- **R1 FIXED.** `ee_axis_two_route_model.py:177` pins the seed only when `formal` is True and records `formal` (`:360`,
  checked `:400`); `v023_two_route_learner_orchestrator.py:416` adds a non-formal rehearsal identity authenticator.
- **08 FIXED.** `test_v023_c1c2_provider_factory_v3.py:135` derives the closure by an independent AST import scan from a
  frozen donor list (`:59`); `:597` drops `src/mcrl/runtime/bessel.py` and expects "derived import graph".
- **L6 FIXED.** `test_…_launch.py:97` asserts the exact union: 246 byte-sorted closure paths ∪ `LAUNCH_MANIFEST_ADDITIONS`
  (`common:78`, incl. both stage-C authenticators), no duplicates.
- **defect C FIXED.** `preflight_…:363 --target-root` (default `TARGET_ROOT`); `:192 _verify_target_root` compares the
  request to the freeze-time value and adds `:203` "formal target root is not the declared target root"; test `:213-250`.

### (b) Tests — exit 0, **56 passed**, 0 failed, no traceback
23 launch + 13 factory + 12 runner + 8 rehearsal. Codex's "70 passed" came from a wider path set.

### (c) Chain checks
manifest `--write` and `--check` both `sha256=4176b8310d69361924390e9cb505b582168d02ef63378ce5c00f2e240f3fbe16`.
`sync_… --dry-run` exit 2, refusing **only** the absent r8 root:
`SUCCESSOR_EXECUTION_BINDINGS_FAIL: required r8 target root is absent: /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`
then `SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current`. `bind_… --help` exit 0.

### (e) Commit + sync
`dd2468eca8def6d81ff8ca646eef5975e52bc672`, 16 files, no `__pycache__`. Four packages rsynced to
`/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/`; spot files byte-identical local↔shadow.

## Part 2 — V2-synthetic rerun #3

Mini-repo `…/.tmp/stageA-synth-bundle-v3` (fresh shadow copy + `git init` + clean commit `a3a76a2`, `dirty=False`).
Target root reused: `…-target-root-r2`, MANIFEST `3775c257…`. Peak RSS < 1 GB throughout (limit 4 GB).

| # | step | result | wall | RSS |
|---|---|---|---|---|
| S1 | binder `--write`/`--check` ×2 | **PASS**, 4× identical `bindings fb9f55a4…` | 1.71–1.75 s | 783 MB |
| S2 | manifest `--check` before rebuild | drifts by design (binder just wrote the bindings) | 0.03 s | — |
| S3 | manifest `--write` + `--check` | **PASS** `fc25fdca…`, 265 paths | 0.03/0.04 s | 20 MB |
| S4 | preflight, non-formal, `--target-root` synth, absent output root | **PASS** `input_sha256=3775c257…`, `formal:false` | 1.11 s | 641 MB |
| S5 | one-epoch diagnostic + receipt gate | **PASS** / `DIAGNOSTIC_RECEIPT_PASS` | 2.02 s | 903 MB |
| S6 | formal runner via bundle wrapper, 100 epochs | **FAIL — defect N** | 0.94 s | 637 MB |
| S7 | interruption drill (SIGKILL ~epoch 40, resume) | **NOT REACHED** (S6); structurally unreachable — defect O | — | — |
| S8 | verifier, renamed engineering copy | **STOP** — PASS not reached, defect P | 0.03 s | 21 MB |
| S9 | verifier, ORIGINAL non-formal root | **REJECTS** as required | 0.03 s | 21 MB |

**Defect C is fixed** — S4 is exactly the step that failed in rerun #2.

### Defect N — the wrapper admits only `formal:true` receipts, which no rehearsal can produce (BLOCKER, class b)
`SUCCESSOR_FORMAL_RUN_FAIL: preflight receipt does not bind the requested formal run`, exit 3, output root never created.
First failing boundary `run_v023_c1c2_successor_formal.py:52-56` (`preflight.get("formal") is not True`). The defect-C fix
moved the boundary rather than removing it: `preflight_…:203` now refuses `--formal` on any non-declared root, so a
rehearsal receipt is necessarily `formal:false` and the only executor refuses it (rerun #1 masked this with bypass C).
**No end-to-end stage-A rehearsal is possible on any root but the literal r8 path.** Suggested fix: accept a
`formal:false` receipt and stamp `formal:false` into ledger/provenance (fields exist at `:123`/`:134`), keeping formal
admission tied to the declared root.

### Defect O — no resume entry point, no checkpoint between epoch 0 and 100 (BLOCKER for the drill, class c)
Neither `run_…_formal.py:33-43` nor `…runner.py:937-949` exposes a resume flag; `main:995` only `begin_new`, and
`preflight_from_args:955` refuses an existing output root. `resume_from_checkpoint` (`…runner.py:853`) is library-only.
`FORMAL_CHECKPOINT_EPOCHS = (0, 100)` (`:63`), so a SIGKILL at epoch 40 leaves only the epoch-0 checkpoint. The drill
cannot be run as specified without new code.

### Defect P — the verifier's positive path is unreachable for any rehearsal (class b, by-design consequence)
Renaming the copy clears `verify_…:198` but stops at `verify_…:246-248`:
`STOP_SOURCE_TRAINING_INTEGRITY: VerificationError: preflight receipt is not PASS`. Two gates follow — `:222`
`provenance formal is not True`, and `common:684-694`, which binds the receipt to the exact `requested_output_root`, so a
copy at any other path is refused even for a formal run. The root binding is right, but the copy-and-verify probe can
never reach PASS; only a real formally-named run exercises it. Copy deleted; original intact. S9 gave the required
rejection: `VerificationError: non-formal rehearsal roots cannot pass formal verification`.

Not updated (concurrent writer): `LATENCY-LEDGER-2026-09-07.md` — N/O/P need entries.
