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
