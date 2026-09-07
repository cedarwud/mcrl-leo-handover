# Engineering lane — stage-A fix pass 5 + V2-synthetic rerun #4

**NOT `V2_RERUN4_CLEAN`.** N/O/P are fixed and the chain now runs end to end non-formally, but the
interruption drill exposed two new package defects (**Q**, **R**). Ceiling
`ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. NON-FORMAL; no edits, no bypasses; losses not interpreted.

## Part 1 — fix pass 5

### (a) Claimed status, re-checked against the live tree — all three confirmed
- **N FIXED.** `run_v023_c1c2_successor_formal.py:43` `--nonformal`; `:57-63` mode-matched receipt admission;
  `:64-69` biconditional `REHEARSAL-NONFORMAL` basename rule; `:113`/`:128` stamp `formal`; `:146`
  `nonformal-provenance.json`; `:152` `SUCCESSOR_NONFORMAL_RUN_COMPLETE`. Runner receipts carry `formal` at
  `…runner.py:414`/`498`/`550`/`570`/`648`; no `COMPLETE`/`MANIFEST.sha256` writer outside the verifier's `_seal`.
- **O FIXED.** `…runner.py:64` formal cadence still `(0, 100)`; `:65` non-formal `0,10,…,100`; `:401` selects by mode.
  CLI `--resume` `:1116`/`:1200`, wrapper `:34`/`:102` → `resume_from_root:1024` → `resume_from_checkpoint:991`
  (sidecar `:1005`, `_validate_checkpoint:1007`, status equality `:1008`, `_validate_exports:1010`, exact `:1015`).
- **P FIXED.** `verify_v023_c1c2_successor.py:194` `nonformal=`; `:196` still requires reconstruction (shared loop
  `:465-478`); `:489`/`:554`/`:558` emit only `NONFORMAL_RECONSTRUCTION_PASS|FAIL`; `:207-208` still rejects a
  non-formal root without the flag; `:210` rejects a formal seal; `_seal` only on the formal branch (`:553`).

### (b) Tests — exit 0, **63 passed**, 0 failed, no traceback (110 s)
27 launch + 13 factory + 15 runner + 8 rehearsal.

### (c) Chain checks
Manifest `--write` and `--check` agree: `bb6a1f9612c9c5c2a8faad8ec4a1ce68eb8596f2e151dbb79218bb2268a74294`, 260 paths.
Differs from codex's `11528207…` only because the manifest covers the concurrently-edited stage-C package
(`…-stagec-launch/V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST{,-FROZEN}.sha256`, 02:46 UTC, other writer); all eight
fix-pass-5 files hash exactly as codex reported. `sync_… --dry-run` exit 2, refusing **only** the absent r8 root:
`SUCCESSOR_EXECUTION_BINDINGS_FAIL: required r8 target root is absent: /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`.

### (e) Commit + sync
`e19224911d365428aef89b2e6a2e8d71be244bec`, 10 files, no `__pycache__`. Four packages rsynced local → shadow.

## Part 2 — V2-synthetic rerun #4
Mini-repo `.tmp/stageA-synth-bundle-v4` (fresh shadow copy + `git init` + clean commit `0166b4e`, `dirty=False`).
Target `…-target-root-r2`, `input_sha256=3775c257…`. Peak RSS 911 MB (limit 4 GB).

| # | step | result | wall | RSS |
|---|---|---|---|---|
| S1 | binder `--write`/`--check` ×2 | **PASS**, 4× `48a2c4e5…` | 1.70–1.71 s | 783 MB |
| S2 | manifest `--check` pre-rebuild | drifts by design (binder just wrote) | 0.03 s | 20 MB |
| S3 | manifest `--write`/`--check` | **PASS** `4863397b…`, 265 paths | 0.03/0.04 s | 20 MB |
| S4 | preflight non-formal, synth `--target-root`, absent root | **PASS** `formal:false` | 1.08 s | 639 MB |
| S5 | one-epoch diagnostic + receipt gate | **PASS** / `DIAGNOSTIC_RECEIPT_PASS` | 2.01 / 0.02 s | 903 MB |
| S6 | **wrapper `--nonformal`, 100 epochs** | **PASS** `SUCCESSOR_NONFORMAL_RUN_COMPLETE`; every receipt `formal:false`, no `COMPLETE`/`MANIFEST.sha256` | 4.29 s | 911 MB |
| S6c | control: 2nd uninterrupted run | **byte-identical** to S6 everywhere | 4.54 s | 911 MB |
| S7a | SIGKILL non-boundary (≈epoch 44), `--resume` | completes; bitwise **partial** — see **R** | 2.62 / 3.65 s | 911 MB |
| S7b | SIGKILL inside the checkpoint write, `--resume` | **FAIL — defect Q** | 2.52 / 1.77 s | 784 MB |
| S7c | SIGKILL at a sealed boundary (epoch 40), `--resume` | completes; same partial equality | 4.02 s | 910 MB |
| S8 | verifier `--nonformal` (base, S7a, S7c roots) | **PASS** `NONFORMAL_RECONSTRUCTION_PASS updates=200 arms=3 exact_resume=True` | 4.2 s | 797 MB |
| S9 | verifier without the flag, same root | **REJECTS** `STOP_SOURCE_TRAINING_INTEGRITY: … non-formal rehearsal roots cannot pass formal verification` | 0.03 s | 21 MB |
| S10 | negatives (both refuse, exit 3, no root created) | **PASS** — no flag on a `formal:false` receipt → `preflight receipt does not bind the requested formal run`; `--nonformal` on a formal-shaped receipt (flipped + resealed sidecar) → `formal preflight receipt cannot be laundered into a non-formal rehearsal` | — | — |

### Defect Q — a kill inside the checkpoint critical section makes the root unresumable (class d)
`…runner.py:565-566` publishes `epoch-0040.runner.pt` **and its sidecar** before `_write_exports:567` and the receipt
`:581`. Killing there left ckpt+sidecar with no `exports/epoch-0040.json` and no `checkpoint-receipts/epoch-0040.json`.
First failing boundary: `resume_from_root:1056` takes `max(existing)`=40 (no fallback) → `resume_from_checkpoint:1057`
→ `_validate_exports:864` → `_read_json:678` `JSON artifact is not a regular file`, exit 3. Epoch 30 is no escape:
`_write_exports:523` refuses the existing `exports/epoch-0040` dir. **The root is unrecoverable.** Fix: exports +
receipt first, checkpoint sidecar last, and `resume_from_root` selects the newest *fully sealed* epoch.

### Defect R — checkpoints are not byte-reproducible across `--resume` (class d)
Two uninterrupted runs are byte-identical (S6c), so the format is reproducible; after a resume every checkpoint past
the resume point differs. Inside `epoch-0050.runner.pt` only `archive/data.pkl` (+5 696 B) and
`archive/.data/serialization_id` differ — all 386 tensor storage records are identical and the deserialized trees
compare exactly equal (`_tree_equal` True, deep diff 0). Growth is confined to the str/list-heavy keys
(`update_ledger_rows`, `provider_sampler_state`, `consumed_file_order`, `orchestrator_state`); `models_and_optimizers`
is byte-equal. Cause: unpickling destroys string-object identity, so re-pickling loses memo back-references.
Write site `…runner.py:565`. Consequence: `canonical-receipt.json` (`checkpoints[]`, `epoch_100_integrity`) and
`checkpoint-receipts/epoch-*.json` differ from an uninterrupted run of the same seed. `update-ledger.json`,
`exports/epoch-0100.json` and the three exported arm `.pt` files **are** bitwise equal, and the verifier still passes
(trees, not bytes). "Bitwise equality at epoch 100" therefore holds for the ledger and the exported models, not for
the runner container or its digests.

### Drill-coverage limitation (fixture, not code)
On synthetic target r2 informed and neutral panels yield bit-identical metrics, so all three arms' epoch-100 exports
share one digest `3f63c3ad…`. Routing is still separated at file identity (`DROP_C1` consumes `c1-neutral-panel-…`),
but this rehearsal cannot detect a numeric arm-crossing defect.

Not updated (concurrent writer): `LATENCY-LEDGER-2026-09-07.md` — Q and R need entries.
