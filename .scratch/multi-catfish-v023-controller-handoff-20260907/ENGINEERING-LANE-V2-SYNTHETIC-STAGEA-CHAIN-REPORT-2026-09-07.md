# Engineering lane — V2 synthetic stage-A chain (2026-09-07 15:47–16:05 UTC)

**NON-FORMAL.** Every root is `*REHEARSAL-NONFORMAL*`. The bundle's formal runner wrote formal-looking receipts
(`formal:true` ledger, provenance, canonical receipt) **inside a `REHEARSAL-NONFORMAL` root never sealed as an
experiment root**, never bound into a manifest, never cited as evidence. The sealed declaration and contract were
untouched. Ceiling `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. Losses not interpreted.

Work tree `…successor-shadow-20260907/.tmp/stageA-synth-bundle` (shadow copy + current local bundle + `git init`; the
repo bundle copy stays clean); 10 key package files byte-identical shadow↔local.
Log `/home/sat/mcrl-v023-stageA-SYNTH-REHEARSAL-NONFORMAL-20260907T154653Z.log`.

## Step 1 — producer-written synthetic sealed 16-shard root — **PASS**
`/tmp/build_synth_target_root.py` imports the factory-v3 test module and calls its `_write_artifact()`: 16 shards via
`generate_v023_c1c2_targets._write_outputs` → `run_v023_c1c2_targets_server._merge` → `seal_v023_c1c2_target_output.seal`.
No hand-written receipt. 35 files, 16 schedule keys (8 worlds × 2 modes).
`MANIFEST.sha256 = 3775c257f9505ce73d9c4a3557d0f8954406a90ee09a7f9d260e2fad4988a334`, COMPLETE agrees.
Target `/home/sat/mcrl-v023-stageA-SYNTH-REHEARSAL-NONFORMAL-target-root-r2`. Pre-existing `…-target-root` (sealed
15:28 UTC by the terminated predecessor, `3b79c157…`) differs in all 33 entries (pre-L-fix code); untouched, hence `-r2`.

## Step 2 — full chain (wall / peak RSS)
| component | result | wall | RSS |
|---|---|---|---|
| binder `--write` | PASS | 2.1 s | 783 MB |
| binder `--check` | **FAIL A** → retry PASS | 2.1 s | 783 MB |
| manifest `--write`/`--check` | **FAIL B** → bypass → PASS | 1.2 s | 637 MB |
| preflight, absent root | PASS `input_sha256=3775c257…` | 1.30 s | 640 MB |
| one-epoch diagnostic | PASS | 2.48 s | 903 MB |
| diagnostic-receipt gate | `DIAGNOSTIC_RECEIPT_PASS` | <1 s | — |
| formal runner, 100 epochs | **FAIL D** → **FAIL E** → PASS | 4.93 s | 910 MB |
| verifier | **BLOCKED (by design)** | 0.02 s | 21 MB |
| `sync_launch --dry-run` | refuses: r8 root absent (correct gate) | — | — |

Output: 200 ledger rows, route order C1→C2, arms `FULL2, DROP_C1, DROP_C2` with `SOURCE_MAP` sources, epoch-0/100
exports, checkpoints + receipts, `formal-provenance.json` binding authority `989b374f…`, learner manifest `242ae64e…`,
r8-slot digest = synth root digest. Only that digest changes for the real r8 root.

## Step 3 — V6 negatives — **PASS (L5 REFUTED)**
On `…two-route-REHEARSAL-NONFORMAL-20260907T143655Z`, exit 3 both ways:
`STOP_SOURCE_TRAINING_INTEGRITY: VerificationError: non-formal rehearsal roots cannot pass formal verification`;
with `--no-reconstruct`, `…: independent reconstruction is required for PASS` (`verify_…:193` rejects
`reconstruct is not True` first). L5 no longer reproduces.

## Defects (first failing boundary)
- **A — freeze is not idempotent on a clean tree (BLOCKER, class b).** `bind_…freeze.py:83 _git_identity()['dirty']`
  from `git status --untracked-files=all`; `--write` itself creates the untracked bindings, flipping `dirty` False→True,
  so `successor_launch_common.py:203 write_reproducible(check=True)` reports
  `frozen file drifted: …EXECUTION-BINDINGS.json` (exit 3). Binder writer vs binder checker: README step 3 fails
  deterministically on a clean checkout, masked only if the tree was already dirty at write time.
- **B — closure list sorted as strings, validated as `Path` (BLOCKER, class b).**
  `successor_launch_common.py:233-241 required_sync_closure` asserts `paths == sorted(paths)` over `Path`;
  `SHADOW-CLOSURE-LIST-2026-09-07.txt` is byte-sorted. Divergence at index 12
  (`…-successor-physical-evaluation/README.md` vs `…-successor/ENGINEERING-LANE-CHARTER…`; `-`<`/` by byte, opposite by
  parts). Blocks manifest builder **and** preflight. L6's 179 missing paths are fixed (246/246).
- **D — factory identity field set vs orchestrator closed set (BLOCKER, class b).**
  `v023_two_route_learner_orchestrator.py:316` requires exactly the 18 fields at lines 259-267; the factory emits 22
  (extra `predecessor_manifest_sha256`, `prereg_sha256`, `scientific_declaration_sha256`, `tle_file_set_sha256`) →
  `SUCCESSOR_FORMAL_RUN_FAIL: provider identity failed factory-v3 authentication` before update 0. Preflight cannot
  catch it (`preflight_…:66-86` checks only routes/budget/seed): green preflight, immediate abort.
- **E — forbidden-token scan rejects the mandatory learner closure (BLOCKER, class b).**
  `v023_two_route_learner_orchestrator.py:296-300` splits identity strings and rejects token `C3`; the factory's
  mandatory closure includes `ee_axis_lcsrs_c3_{head,dataset,learner,state}.py` (12 offending path/module/loaded_from
  values). L2's class, surviving in the orchestrator.
- **Verifier positive path — BLOCKED by design.** `verify_…:198` rejects any root path containing
  `REHEARSAL-NONFORMAL`, which this rehearsal must use, so `PASS_SOURCE_TRAINING_INTEGRITY` is unreachable here.
  Disabling the guard was refused by the permission classifier and **not attempted**; the launcher (line 128) verifies
  the formally-named root, so its positive path needs a formally-named slice — a controller call.
- **Note.** The shadow checkout has no `.git`, so `_git_identity` fails there; the launch checkout must be a git tree.

Known-item status: **L1, L2 (bundle), L3, L4, L7 not reproduced; L5 refuted; L6 coverage fixed** (new ordering defect B).

## Engineering-only bypasses (marked, never for the formal launch)
B: re-sorted the closure list `Path`-wise. C: retargeted `.tmp` `TARGET_ROOT` to the synth root. D: added the 4 fields
to `_FACTORY_V3_IDENTITY_FIELDS` (consumer aligns to producer). E: excluded `learner_runtime` code paths from the token
scan. All in `.tmp` copies only; each forced a re-freeze (bind → manifest → preflight → diagnostic) before the runner.
