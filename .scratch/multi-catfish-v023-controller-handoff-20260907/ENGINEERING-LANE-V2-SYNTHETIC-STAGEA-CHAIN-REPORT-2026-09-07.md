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

## Rerun after fix passes 2+3 (commit `1e6310e`, 2026-09-07 16:41–16:47 UTC)

Same rules, **no edits and no bypasses**. Local → shadow sync of the three packages verified byte-identical
(`successor_launch_common.py 87e2257d…`, factory `87a1e980…`, orchestrator `c14728e3…`). Fresh mini-repo
`…/.tmp/stageA-synth-bundle-v2` (shadow copy + `git init`, committed clean: `dirty=False` — the exact condition that
broke defect A). Target root reused: `…-target-root-r2`, `MANIFEST 3775c257…`.
Log `/home/sat/mcrl-v023-stageA-SYNTH-REHEARSAL-NONFORMAL-20260907T164144Z.log`.

| # | step | result | wall |
|---|---|---|---|
| R1 | binder `--write` #1 | **PASS** `bindings 37f3bd4a…` | 2.03 s |
| R2 | binder `--check` #1 | **PASS** identical | 2.04 s |
| R3 | binder `--write` #2 | **PASS** identical | 2.03 s |
| R4 | binder `--check` #2 | **PASS** identical | 2.04 s |
| R5 | manifest `--write` | **PASS** `e1fceb97…` | 1.18 s |
| R6 | manifest `--check` | **PASS** identical | 1.20 s |
| R7 | preflight (absent output root) | **FAIL — remaining defect C** | 0.04 s |
| R8 | one-epoch diagnostic | **PASS** (903 MB peak RSS) | 2.40 s |
| R9 | formal runner via bundle wrapper | **BLOCKED** by R7 (no receipt) | 1.12 s |
| R10 | verifier positive path | **NOT REACHED** — no output root exists | — |

**A FIXED** — write→check→write→check on a *clean* git tree is now byte-identical four times over;
`_git_identity` excludes `GENERATED_BUNDLE_NAMES` from the dirty probe (`bind_…freeze.py:84-98`).
**B FIXED** — `required_sync_closure` now compares `rows != sorted(rows)` (string order,
`successor_launch_common.py:241`), matching the unmodified byte-sorted 246-path list; 246/246 present.
**D and E FIXED** — the diagnostic constructed a real factory-v3 provider and passed all seven behavioural checks, so
the closed identity field set and the token scan (`_reject_forbidden_identity_fields` now field-aware with a
`closure_context` exemption, orchestrator:319-357) both admit the current 22-field payload and the mandatory
`ee_axis_lcsrs_c3_*` closure. **L5 unchanged** (reconstruction still required).

### Remaining defect C — preflight pins the target root while the binder parameterises it (BLOCKER, class b)
`SUCCESSOR_PREFLIGHT_FAIL: factory-v3 config drifted: target_root` (exit 3, 0.04 s).
First failing boundary: `preflight_v023_c1c2_successor.py:221` asserts
`provider_config["target_root"] == str(TARGET_ROOT)`, the module constant
`successor_launch_common.py:66 = /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`, against the provider config the
binder legitimately wrote from its own `--target-root` flag (`bind_…freeze.py:421`). The two sides are the binder's
parameterised freeze and the preflight's hard-coded expectation. Consequence: **no stage-A rehearsal is possible on any
root other than the literal r8 path** — and that path does not exist yet (0/16 shard `COMPLETE` markers at 16:45 UTC),
so today the pinned root is absent. Suggested fix: give preflight the same `--target-root` argument (defaulting to
`TARGET_ROOT`) and/or compare against the freeze-time value, keeping the r8 constant as the check that a *formal*
launch is on the declared root.

### Minor — wrapper error contract not honoured for preflight-receipt faults
R9 exited **1** with an uncaught traceback ending
`SuccessorLaunchError: preflight receipt is not canonical ASCII JSON`, instead of the wrapper's documented
`SUCCESSOR_FORMAL_RUN_FAIL: …` / exit 3. Two issues at `run_v023_c1c2_successor_formal.py:47`: the
`read_canonical_json` call sits outside the `try`, and `successor_launch_common.py:145` maps an *absent* file to empty
bytes, so "missing receipt" is reported as "malformed receipt". Gate behaviour is correct (the run was refused); only
the diagnosis and exit code are wrong.

### Verifier positive path
Not exercised. It needs a finished output root, which R7 prevented; reusing the 15:46 UTC root would mix code states
(that root was produced under the now-removed D/E patches, so its learner-manifest digests cannot match the current
freeze) and would test code drift rather than the positive path. `…/.tmp/v2-verify-copy/` was therefore never created.
Once defect C is fixed this rerun reaches the runner and the copy-and-verify probe becomes meaningful in one pass.
