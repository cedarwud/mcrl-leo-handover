# Engineering lane — stage-A fix pass 6 + V2-synthetic rerun #5

**NOT `V2_RERUN5_CLEAN`.** Q and R are fixed and every mandated step passes, but two new publication defects
(**S**, **T**) remain, one again unrecoverable-root class. Ceiling
`ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. NON-FORMAL; no edits, no bypasses; losses not interpreted.

## Part 1 — fix pass 6

### (a) Claimed status, re-checked against the live tree — both confirmed
- **Q FIXED.** `…runner.py:792` `_write_checkpoint` computes bytes+digest first (`:796-797`), then
  `_clear_unsealed_checkpoint_prefix:798` → `_write_exports:799` → receipt `:813` → checkpoint `:814` → sidecar
  `:815` **last**. Codex cited `:667`; the real site is `:792` (`:667` is `_checkpoint_prefix_paths`).
- **R FIXED.** `CHECKPOINT_SCHEMA` `…-checkpoint-v1.1` `:57`; canonical encode/decode `:125`, `:157`, `:217`, `:221`,
  consumed at `:656/658/661/662`; tensors stay native `:657`. Verifier `verify_v023_c1c2_successor.py:370` (schema),
  `:377` (`decode_checkpoint_orchestrator_state`).

### (b) Tests — exit 0, **72 passed**, 0 failed, no traceback, 213 s
24 runner + 27 launch + 8 rehearsal + 13 factory.

### (c) Chain checks
Manifest `--write`/`--check` agree: `ab3fdf9da5ae6978416577e6c256059de55aa7b8d66ce84244b7117d851dcb40`, 260 paths
(246 closure + 14 additions) — codex's digest exactly; all six changed-file SHA-256 match. `sync_… --dry-run`
exit 2, refusing **only** the absent r8 root:
`SUCCESSOR_EXECUTION_BINDINGS_FAIL: required r8 target root is absent: /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`
/ `SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current`.

### (d) Spot-checks
`_atomic_write_once:291` = O_EXCL temp `:299` + fsync `:304` + `os.rename:309`; export dir renamed `:771`; sidecar uses
the same helper `:324`. `_has_complete_sealed_prefix:679` requires export dir + manifest + receipt + checkpoint +
sidecar and re-verifies the digest `:695`; `resume_from_root:1264` takes `max(sealed)` `:1286-1295`. Unsealed epochs
replaced (`_write_exports:735` rmtree, `:737` unlink), sealed refused (`:719`, `_clear_unsealed_checkpoint_prefix:700`).
Formal cadence unchanged: `(0,100)` `:65`, 200 updates `:68`.

### (e) Commit + sync
`dca2e2a7afe8b1c1e5a1963e13b511d5799c9d1b`, 6 files, no `__pycache__`. Four packages rsynced local → shadow; digests
re-checked equal on both sides.

## Part 2 — V2-synthetic rerun #5
Mini-repo `.tmp/stageA-synth-bundle-v5` (fresh shadow copy, `git init`, clean commit `35aef7c`). Target
`…-target-root-r2`, `input_sha256=3775c257…`. Roots `…-NONFORMAL-20260907T194951Z*`. **Peak RSS 892 MB** (limit 4 GB).

| # | step | result | wall | RSS |
|---|---|---|---|---|
| S1 | binder `--write`/`--check` ×2 | **PASS**, 4× `c11b3433…` | 1.69 s | 783 MB |
| S2 | manifest `--write`/`--check` | **PASS** `35c81311…`, 265 paths | 0.04 s | 20 MB |
| S3 | non-formal preflight ×6 (one receipt per root) | **PASS** `formal:false` | 1.07 s | 643 MB |
| S4 | one-epoch diagnostic + receipt gate | **PASS** / `DIAGNOSTIC_RECEIPT_PASS` | 1.96 s | 905 MB |
| S5 | wrapper `--nonformal`, 100 epochs | **PASS** `SUCCESSOR_NONFORMAL_RUN_COMPLETE` | 4.36 s | 890 MB |
| S6 | control: 2nd uninterrupted run | **113/114 byte-identical** | 4.28 s | 890 MB |
| S7a | SIGKILL non-boundary (seal+0.130 s, ≈ epoch 44) → `--resume` | **PASS**, byte-identical | 3.48 s | 892 MB |
| S7b | SIGKILL inside the checkpoint write (epoch-40 exports+receipt published, checkpoint+sidecar absent) → `--resume` | **PASS**, byte-identical **but one orphan — S** | 3.65 s | 890 MB |
| S7c | SIGKILL at the sealed boundary (epoch 40) → `--resume` | **PASS**, byte-identical | 3.44 s | 890 MB |
| S7d | selection proof on a fresh S7b-shaped kill | `SEALED_EPOCHS [0,10,20,30]` → `RESUME_SELECTED epoch-0030.runner.pt` | 2.3 s | — |
| S8 | verifier `--nonformal`, base + 3 drills | **PASS** `NONFORMAL_RECONSTRUCTION_PASS updates=200 arms=3 exact_resume=True` | 3.68 s | 800 MB |
| S9 | verifier without the flag | **REJECTS** `STOP_SOURCE_TRAINING_INTEGRITY: … non-formal rehearsal roots cannot pass formal verification` | 0.05 s | — |
| S10 | both laundering negatives, exit 3, no root created | **PASS** — `preflight receipt does not bind the requested formal run`; `formal preflight receipt cannot be laundered into a non-formal rehearsal` | — | — |

(i) holds — S7d is direct proof. (ii) holds — in all three drills every checkpoint, sidecar, checkpoint receipt,
export, export manifest, `update-ledger.json` and `canonical-receipt.json` is byte-identical to the uninterrupted run.
The lone differing file, `nonformal-provenance.json`, differs in the *control* run too: it carries
`requested_output_root` and `preflight_receipt_sha256` — root identity, not content.

### Defect S — the checkpoint's own temp file survives resume forever (class d, non-fatal)
S7b left `checkpoints/.epoch-0040.runner.pt.c9ab30f7….tmp` (1 015 808 B, truncated). `_atomic_write_once` cleans its
temp only in `finally` (`:313`), which SIGKILL skips; `_clear_unsealed_checkpoint_prefix:700` unlinks only
sidecar/checkpoint/receipt, and the sole stale-temp sweep (`_write_exports:743`) is scoped to `exports/`. The resumed
root carries 115 files to the reference's 114 and **the verifier passes it silently** — an unexplained artifact in a
write-once root goes undetected.

### Defect T — a stale temp *file* in `exports/` makes the root permanently unresumable (class d, fatal)
`_write_exports:743-748` globs `exports/.epoch-NNNN.*.tmp` and raises for anything that is not a directory. But the
export manifest's own atomic temp is `exports/.epoch-NNNN.json.<32 hex>.tmp` (`_atomic_write_once:296` on
`_export_manifest_path:472`) — a regular file matching that glob. A SIGKILL inside the manifest write leaves a root no
`--resume` can advance. Reproduced by injecting that filename onto a real S7b-shaped kill prefix:
`SUCCESSOR_FORMAL_RUN_FAIL: unsealed temporary export path is invalid`, exit 3, boundary `:745-748`. Same
unrecoverable class as Q, different kill point.

### Unchanged limitation
On target r2 all three arms still share one epoch-100 export digest, so this rehearsal cannot detect a numeric
arm-crossing defect. Not updated (concurrent writer): `LATENCY-LEDGER-2026-09-07.md` — Q, R, S, T need entries.
