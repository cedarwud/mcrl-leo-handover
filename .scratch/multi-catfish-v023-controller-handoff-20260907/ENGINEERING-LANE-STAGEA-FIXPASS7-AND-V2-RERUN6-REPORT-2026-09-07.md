# Engineering lane — stage-A fix pass 7 + V2-synthetic rerun #6

`V2_RERUN6_CLEAN`

S and T are fixed, every mandated step passes, **no defect remains open**. Ceiling
`ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. NON-FORMAL; no edits, no bypasses; losses not interpreted.

## Part 1 — fix pass 7

### (a) Both claims confirmed against the live tree; all three codex citations accurate
- **T FIXED** — root-wide policy, not an `exports/` glob. `inspect_output_root:796` rglobs every `.*.tmp` (`:826`);
  `_classify_stale_temp:715` types each into the eight known artifact classes (`:89`) and refuses non-file/dir
  kinds, unknown artifacts, unauthorized epochs, sealed epochs (`:781`), sealed roots.
  `_sweep_stale_temps:920` raises before any unlink if anything is refused (`:934`), removes deepest-first, logs via
  `_write_resume_receipt:878` (append-only, contiguous `resume-NNNN.json`). Wired at `resume_from_root:1544`
  (sweep `:1577`) before `resume_from_checkpoint`. The old fatal `_write_exports` glob check is gone.
- **S FIXED** — `_validate_root_schema:246` builds the exact expected name set per mode, rejects
  `observed − expected − optional` (`:292` "unaccounted artifact") and any symlink; `_validate_resume_receipts:180`
  checks schema/sequence/field-set/epoch lists and requires each logged removal to be a well-formed temp name
  **absent** from the root (`:241`). Called at `verify_output:339`, both modes.
- **`--check-root`** `build_parser:1638`, exclusive with `--output-root`/`--resume`; `main:1731` refuses every
  execution argument (`:1744`) and only prints `inspect_output_root`. The seven formerly `required=True` flags moved
  to `preflight_from_args:1666`, which still refuses them. Both refusals verified live.

### (b) Tests — exit 0, **81 passed**, 0 failed, no traceback, 272 s
29 runner + 31 launch + 8 rehearsal + 13 factory.

### (c) Chain checks
Manifest `--write`/`--check` agree: `b3a8ef84b2d8a44bd42daebf3c85d17469bb74c66719c49c3dacddc5870fa8f5`, 260 paths
(246 closure + 14 additions) — codex's digest; all seven changed-file SHA-256 match. `sync_… --dry-run` exit 2,
refusing **only** the absent r8 root:
`SUCCESSOR_EXECUTION_BINDINGS_FAIL: required r8 target root is absent: /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`
/ `SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current`.

### (d) Spot-checks (live, rerun #6)
T — every drill's `--check-root` listed the sealed epochs and the exact stale temps; files **and** directories removed
(S7b swept a temp dir *and* its nested member, both logged). A temp planted on the **sealed** epoch 40 came back
`safe_to_remove:false / "stale temp belongs to a sealed epoch"`; `--resume` refused before mutating anything (digest
`56a7eec8…` unchanged, no receipt).
S — the verifier rejected a stray `.tmp`, an unknown file and a nested stray in non-formal mode; the formal branch
rejected all three plus a still-present removal and a malformed removal name (direct
`_validate_root_schema(expected_formal=True)` probe, 7/7) and accepted a well-formed logged removal.
`--check-root` read-only: whole-tree digest (paths+kinds+contents) unchanged on all seven drilled roots.

### (e) Commit + sync
A concurrent operator's `git commit` swept my staged files: content landed in
**`d0afd18913e6dd4fe1edbd1dfd5d44e1bbe8c4b3`**; the mandated message was recorded as marker commit **`11dabf8`**.
No history rewritten; the four packages are clean against HEAD and rsynced local → shadow with equal digests.

## Part 2 — V2-synthetic rerun #6
Mini-repo `.tmp/stageA-synth-bundle-v6` (fresh shadow copy, `git init`). Target `…-target-root-r2`,
`input_sha256=3775c257…`. Roots `…-NONFORMAL-20260907T204043Z*`. **Peak RSS 894 MB** (limit 4 GB); 94.5 s timed wall;
239 MB disk. No `*r8*`, `*lcsrs-gate*`, `*-r7-*`, `codex-ws-*`, `c3-contingency-f1-*`, `stageC-*` or sealed root
touched.

| # | step | result | wall | RSS |
|---|---|---|---|---|
| S1 | binder ×2 | **PASS** 4× `1b09fc89…` | 1.71 s | 783 MB |
| S2 | manifest | **PASS** `9eda1d1d…`, 265 paths | 0.04 s | 20 MB |
| S3 | preflight ×8 | **PASS** `formal:false` | 1.07 s | 644 MB |
| S4 | diagnostic + gate | **PASS** `DIAGNOSTIC_RECEIPT_PASS` | 1.96 s | 905 MB |
| S5 | wrapper `--nonformal` 100 epochs | **PASS** `SUCCESSOR_NONFORMAL_RUN_COMPLETE` | 4.30 s | 913 MB |
| S6 | 2nd uninterrupted run | **113/114 identical** | 4.27 s | 914 MB |
| S7a | kill: export-dir rename | **PASS** | 2.42+3.69 s | 914 MB |
| S7b | kill: export member | **PASS** dir+member swept | 2.40+3.70 s | 912 MB |
| S7c | kill: export manifest (old fatal T) | **PASS** | 2.43+3.72 s | 913 MB |
| S7d | kill: checkpoint receipt | **PASS** | 2.39+3.70 s | 911 MB |
| S7e | kill: checkpoint | **PASS** | 2.45+3.69 s | 915 MB |
| S7f | kill: sidecar | **PASS** | 2.41+3.71 s | 914 MB |
| S7g | kill: non-boundary (seal+0.130 s) | **PASS** no temps, no receipt | 2.53+3.48 s | 913 MB |
| S8 | verifier `--nonformal` ×9 | **PASS** `NONFORMAL_RECONSTRUCTION_PASS updates=200 arms=3 exact_resume=True` | 3.70 s | 800 MB |
| S9 | verifier, no flag | **REJECTS** `STOP_SOURCE_TRAINING_INTEGRITY: … cannot pass formal verification` | 0.05 s | — |
| S10 | strays, both modes | **REJECTS**; restored, re-verify PASS | — | — |
| S11 | laundering ×2 | **PASS** exit 3, no root created | — | — |
| S12 | sealed-epoch temp | **REFUSED**, non-mutating | — | — |

Every drill fired on attempt 1 and its post-kill state was asserted to be the intended one. Every resume succeeded;
each receipt logged exactly the removed temps with `resumed_from_checkpoint: checkpoints/epoch-0030.runner.pt` and
`sealed_epochs_before_resume [0,10,20,30]`. All final artifacts are byte-identical to the uninterrupted run; the only
differences are `nonformal-provenance.json` (root identity — it differs in the control run too) and, where temps
existed, `resume-receipts/resume-0001.json`.

### Unchanged limitation
On target r2 all three arms still share one epoch-100 export digest, so this rehearsal cannot detect a numeric
arm-crossing defect. `LATENCY-LEDGER-2026-09-07.md` not updated (concurrent writer): S and T need closing entries.
