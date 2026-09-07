# Engineering-lane rehearsal run report (2026-09-07)

Lane: ENGINEERING (non-formal). `formal:false`, claim ceiling
`ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. Result: **FAIL**, first
and only attempt. Per instructions, no retry with changed parameters was
made; step 3 (10-epoch confirmation run) was skipped since step 1 did not PASS.

## Command run (exactly as README step 1 specifies)

```
ssh sat true   # preflight: resolves fine, so host alias `sat` used directly
.scratch/multi-catfish-v023-two-route-rehearsal/sync_run_rehearsal_server.sh \
  sat 3 /home/sat/mcrl-v023-real-shards-rehearsal 2927175120652069826
```
Run from repo root `/home/u24/papers/mcrl-leo-handover`. Local required-path
preflight passed (`src` + six `.scratch/...` package dirs, all present,
non-symlink). rsync of code into `/home/sat/mcrl-v023-successor-shadow-20260907`
succeeded; the script then ran the rehearsal on the server with
`PYTHONPATH=<checkout>/src`, `OMP_NUM_THREADS=2`, `oom_score_adj=1000`, python
`/home/sat/mcrl-leo-handover/.venv/bin/python`. No fallback path was needed —
the primary launcher executed the actual rehearsal program, which failed on
its own input-validation logic (on-topic, not a sync/tooling refusal).

Output root created: `/home/sat/mcrl-v023-two-route-REHEARSAL-NONFORMAL-20260907T142523Z`
(empty — 0 entries, no `REHEARSAL-RECEIPT.json`, no `COMPLETE` marker; confirmed by directory listing).

## Result line and timings

```
REHEARSAL_TWO_ROUTE_FAIL {"claim_ceiling":"ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT","formal":false,"phase_timings_seconds":{},"status":"FAIL"}
NONFORMAL_REHEARSAL_ERROR RehearsalShardProviderError: mode directory contains a symlink: /home/sat/mcrl-v023-real-shards-rehearsal/informed/world-2026121705-r5
```
Remote exit code 2 (`main()`'s exception handler,
`rehearsal_two_route_training_real_shards.py:468-482`). Phase timings empty
(`{}`) — failure preceded `shard_load_seconds`. No worlds/shard digests
catalogued (provider never got past its first candidate). Peak RSS not
obtainable — launcher doesn't wrap the run in `/usr/bin/time -v`, and adding
one would be a changed parameter, disallowed after a FAIL. In-memory receipt
fields (`_base_receipt`; never written to disk, exception preceded the
write): `formal: false`, `claim_ceiling:
"ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"`, `scientific_claim: false`,
`episode_training: false`, `complete_marker_written: false`. No `COMPLETE`
marker anywhere, confirmed.

## First failing boundary

`rehearsal_real_shard_provider.py:282-283`, inside
`RehearsalRealShardProvider.__init__`'s per-mode directory scan (called from
`rehearsal_two_route_training_real_shards.py:279-281`):
```python
if candidate.is_symlink():
    _fail(f"mode directory contains a symlink: {candidate}")
```
Triggered by the alphabetically-first entry under `informed/`,
`world-2026121705-r5`, itself a symlink to
`/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r5-mode-shards/informed/world-2026121705`.
Verified this is not a one-off: **all 7 entries** under the given shard root
(2/2 in `informed/`, 5/5 in `neutral/`) are symlinks of the same shape, into
two different sealed `*-mode-shards` target roots. The guard fires
deterministically on the very first candidate before any epoch/seed-dependent
code runs, so this shard root cannot pass under the current provider code
regardless of epochs, seed, or retry.

## Classification: (b) producer <-> consumer mismatch

- **Producer**: the read-only rehearsal shard root
  `/home/sat/mcrl-v023-real-shards-rehearsal`, built and documented (per the
  operating charter) as a symlink farm referencing real, already-sealed
  shard directories, specifically so the rehearsal can reference sealed data
  without copying it.
- **Consumer**: `RehearsalRealShardProvider.__init__`'s mode-directory scan,
  which unconditionally rejects any symlink as a direct child of
  `informed/`/`neutral/` — no allowance for "symlink to an
  authenticatable, sealed shard directory," only for the four leaf files
  inside a shard directory not being symlinks (lines 291, 65).

Secondarily also (d): the README says it exercises "whatever completed,
individually sealed real shards currently exist under separate `informed/`
and `neutral/` directories" — exactly what this root provides — yet the
package's only validated shape (plain, non-symlink subdirectories) can never
be satisfied by the root its own charter mandates here. Not (a) — sync
succeeded, all required packages copied. Not (c) — no
environment/permissions/resource fault.

## Correction to Attempt 1

The Attempt-1 claim "output root ... empty, 0 entries" was based on a
directory-entry-size grep of `/home/sat/`, not an actual listing of the root.
A direct `find` now shows it holds exactly one file,
`REHEARSAL-RECEIPT.json`, written by `run_rehearsal`'s exception handler
(`rehearsal_two_route_training_real_shards.py:414-433`) before re-raising.
Content matches the printed FAIL line exactly. The "no `COMPLETE` marker"
part of the original claim stands, now directly confirmed.

## Attempt 2 (rerun after symlink fix, 2026-09-07 ~14:36 UTC)

**Result: FAIL**, first and only attempt at 3 epochs. The symlink defect is
confirmed fixed — a different, later error occurred, so step 3 (10-epoch
run) was not attempted; no retry with changed parameters was made.

Command (identical to Attempt 1; re-syncs the now-fixed package):
```
.scratch/multi-catfish-v023-two-route-rehearsal/sync_run_rehearsal_server.sh \
  sat 3 /home/sat/mcrl-v023-real-shards-rehearsal 2927175120652069826
```
rsync succeeded (fixed `rehearsal_real_shard_provider.py` copied into the
shadow checkout). Output root:
`/home/sat/mcrl-v023-two-route-REHEARSAL-NONFORMAL-20260907T143655Z`. Remote
exit code 2.

```
REHEARSAL_TWO_ROUTE_FAIL {"claim_ceiling":"ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT","formal":false,"phase_timings_seconds":{},"status":"FAIL"}
NONFORMAL_REHEARSAL_ERROR RehearsalShardProviderError: rehearsal requires at least one authenticated shard in each mode
```
Output root contains exactly `REHEARSAL-RECEIPT.json`; no `COMPLETE` marker
(confirmed by `find`). Receipt fields verified by direct read: `formal:
false`, `claim_ceiling: "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"`,
`scientific_claim: false`, `episode_training: false`,
`complete_marker_written: false`, `status: "REHEARSAL_FAIL"`. Phase timings
all empty (`phases: {}`, `per_update: []`, `per_epoch: []`) — failure
precedes shard-load completion, so no shard-load/per-update/per-epoch/
export/reload/resume timing exists. Worlds used per mode: 0/0 (both
`informed` and `neutral` ended with zero authenticated shards). Shard digest
count: 0.

### First failing boundary (Attempt 2)

`rehearsal_real_shard_provider.py:300-305`, in the same per-mode scan, now
past symlink resolution: it requires `COMPLETE`, `MANIFEST.sha256`,
`receipt.json` as plain files directly under the resolved directory; any
candidate missing one is pushed to `_skipped_incomplete` and skipped (no
immediate raise). Every candidate in both modes was skipped this way, so
`mode_inputs["informed"]` and `mode_inputs["neutral"]` were both empty,
tripping the aggregate guard at line 330-331:
`_fail("rehearsal requires at least one authenticated shard in each mode")`.

Verified directly on the server: all 7 real shard directories reachable
through the given shard-root's symlinks (2 under `...-r5-mode-shards/informed/`,
4 under `...-r5-mode-shards/neutral/`, 1 under `...-r6-mode-shards/neutral/`)
contain `MANIFEST.sha256`, `receipt.json`, and the `c1-*.json`/`c2-*.json`
data files, but **none contain `COMPLETE`** anywhere in either `-mode-shards`
tree (`find -iname "*complete*"` returned nothing). Each has a separate
`shard-status/<mode>-world-<id>.terminal.json` sibling file outside the
per-world directory instead.
`.scratch/multi-catfish-v023-c1c2-target-generation-launch/seal_v023_c1c2_target_output.py:78`
(`complete = root / "COMPLETE"`) shows `COMPLETE` is this codebase's own
real write-once seal marker, so the rehearsal's requirement matches the
pipeline's documented sealing contract rather than inventing one. The
`shard-status/` listing also records more worlds "terminal" (through
world-2026121712) than have been materialized as per-world directories with
data (only through 2026121711 for r5-informed), consistent with this batch
still being mid-pipeline rather than a finished, sealed archive.

### Classification (Attempt 2): primarily (a), sync/closure gap

The given shard-root's symlinks reference real shard directories that are
generation-terminal (`terminal.json`, full data + manifest + receipt) but
have not yet been through the pipeline's separate `COMPLETE`-sealing step —
the charter's own description of this root ("read-only input: symlinks to
real completed shards") is not yet actually satisfied for any of the 7
referenced worlds at this point in time. That reads as a timing/closure gap
in what the shard-root currently points at, not a code defect. If instead
this `-ops3-r5/r6-mode-shards` pipeline variant never runs
`seal_v023_c1c2_target_output.py` per world, this would instead be (b):
producer (real pipeline's actual completion signal = `terminal.json`) vs.
consumer (`RehearsalRealShardProvider`'s hard `COMPLETE` requirement) — not
fully ruled out without going beyond this lane's read-only, no-code-change
scope. Not (c) — no environment fault. Not (d) — the provider's requirement
matches the codebase's own documented sealer, so it is not self-contradictory.

## Attempt 3 (2026-09-07, r8 root — both runs PASS)

The blocker recorded in the previous version of this section is resolved:
the controller created the read-only root itself rather than this session
doing so. Before running anything, this session independently verified (read
only) that `/home/sat/mcrl-v023-real-shards-rehearsal-r8/` contains exactly
three entries and nothing else — `informed/world-2026121711`,
`neutral/world-2026121707`, `neutral/world-2026121708` — each a plain
symlink (`lrwxrwxrwx`) resolving to the matching directory under
`/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8-mode-shards/`. No file was
written into the r8 tree. This session's own write footprint stayed exactly
where it always was: the shadow checkout and new `REHEARSAL-NONFORMAL`
output roots.

Package changes since Attempt 2, observed in the synced code and confirmed
by the run: `rehearsal_real_shard_provider.py` now authenticates a shard via
manifest + canonical receipt + the sibling `shard-status/*.terminal.json`
(no per-shard `COMPLETE`), and
`rehearsal_two_route_training_real_shards.py` now hard-checks the loaded
model config's sha256 against an imported `FROZEN_MODEL_CONFIG_SHA256` and
the `--train-seed` against an imported `FORMAL_TRAIN_SEED` before running
(`DEFAULT_TRAIN_SEED = FORMAL_TRAIN_SEED`); both checks passed silently
(no mismatch raised) using the same model-config path and seed as
Attempts 1-2.

### Run 1 — 3 epochs

Command:
```
.scratch/multi-catfish-v023-two-route-rehearsal/sync_run_rehearsal_server.sh \
  sat 3 /home/sat/mcrl-v023-real-shards-rehearsal-r8 2927175120652069826
```
Output root: `/home/sat/mcrl-v023-two-route-REHEARSAL-NONFORMAL-20260907T154338Z`. Exit code 0.
```
REHEARSAL_TWO_ROUTE_PASS {"claim_ceiling":"ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT","formal":false,"phase_timings_seconds":{"export_seconds":0.0152,"initial_training_seconds":3.9709,"reload_seconds":36.5530,"resumed_epoch_seconds":1.2567,"shard_load_seconds":36.0523},"status":"PASS"}
```

### Run 2 — 10 epochs (rerun, second root, per PASS)

Command: identical, `3` replaced with `10`. Output root:
`/home/sat/mcrl-v023-two-route-REHEARSAL-NONFORMAL-20260907T154523Z`. Exit code 0.
```
REHEARSAL_TWO_ROUTE_PASS {"claim_ceiling":"ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT","formal":false,"phase_timings_seconds":{"export_seconds":0.0152,"initial_training_seconds":12.5316,"reload_seconds":36.6580,"resumed_epoch_seconds":1.2303,"shard_load_seconds":35.2202},"status":"PASS"}
```

### Combined findings (both runs identical except epoch count)

- **Phase timings (seconds):** shard_load ~35.2-36.1 and reload ~36.6 are
  flat regardless of epoch count (one-time cost: typed-adapter authentication
  of 3 shards, then a second provider construction for reload); export is
  ~0.015 both times; resumed_epoch is ~1.23-1.26 both times.
  initial_training scales with epoch count: 3.97 s / 3 epochs (~1.32 s/epoch)
  vs. 12.53 s / 10 epochs (~1.25 s/epoch) — steady.
- **Per-epoch (`timings.per_epoch`):** 1.22-1.38 s each, both runs, no drift
  across 10 epochs.
- **Per-update (`timings.per_update`):** steady in both runs — route C1
  ~0.84 s/update, route C2 ~0.38-0.52 s/update.
- **Worlds used per mode (`worlds_used_by_mode`):** `informed: [2026121711]`
  (1), `neutral: [2026121707, 2026121708]` (2) — identical both runs.
- **Shard digest count:** 3 (`shard_catalogue`/`shard_digests_used`), all
  `is_symlink: true`, `status_state: "PASS"`; `skipped_incomplete_shard_dirs`
  and `skipped_shards` both empty in both runs.
- **Receipt fields (both runs):** `formal: false`, `claim_ceiling:
  "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"`, `scientific_claim:
  false`, `episode_training: false`, `complete_marker_written: false`,
  `status: "REHEARSAL_PASS"`, `exact_continuation_verified: true`
  (`BITWISE_TREE_EQUAL_AFTER_ONE_EPOCH`). `model_config_sha256` identical
  across both runs (`9eafcd18...b1d5d`); `train_seed`
  `2927175120652069826` in both. Note: `planned_epoch_budget` now reads
  `100` in both receipts (new orchestrator-side value, unlike Attempts 1-2
  where it was `epochs + 1`) — recorded as observed, not interpreted.
- **`finite_loss_checks`:** `all_finite: true` in both (30 checks at 3
  epochs, 72 at 10 epochs) — a structural finiteness check only; loss values
  themselves are not reported or compared here per the non-decisional rule.
- **No `COMPLETE` marker:** confirmed by full `find` listing of both output
  roots — each contains only `REHEARSAL-RECEIPT.json`,
  `REHEARSAL-NONFORMAL-CHECKPOINT.pt`, `REHEARSAL-NONFORMAL-RESUMED-ONE-EPOCH.pt`,
  and a `REHEARSAL-EXPORT-EPOCH-NNNN/` directory with the three arms'
  `.pt` exports. No sealed/formal marker of any kind.
