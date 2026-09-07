# V0.23 server launch-glue note

Date: 2026-09-05  
Scope: non-heavy launch plumbing only.  This note records the boundary of the
new Ubuntu-server entrypoints; it is not an execution receipt or a scientific
decision.

## Added entrypoints

`run_v023_lcsrs_source_server.py` is import-inert.  It loads the staged runner
and `v023_lcsrs_source_adapter.py` only after an explicit CLI invocation,
constructs the adapter's frozen `V023SourceAdapterConfig` from the declared
TLE/preregistration/preflight/addendum/key/lineage/family arguments, and calls
the runner's `run_source_stage` with one typed `SourceShardSpec`.  It performs
an early write-once check and has no simulator/TLE/NumPy/PyTorch/TEST import at
module import time.  The runner remains the owner of source validation and the
receipt seal.

`run_v023_lcsrs_full_gate_server.sh` is a resumable, fail-closed stage driver:

1. authenticate the existing preflight and require the supplied TLE root to
   equal the root recorded by that preflight;
2. source exactly eight frozen worlds with bounded parallelism;
3. emit the runner-owned source manifest;
4. fit exactly eight leave-one-world-out folds x three student seeds x two arms
   (48), with bounded parallelism;
5. compose exactly those 48 keys through the existing composition server and
   `build_runtime` callback; and
6. invoke the independent final verifier over all 8/48/48 paths.

All generated paths are below the caller's new/resumable run root.  Existing
shards are never overwritten; downstream stages and the final verifier reopen
and authenticate skipped receipts.  No TEST split, episode-policy training,
coordinator, fallback, repair, or post-selection action edit is reachable.

## Closed integration findings

1. **Preflight byte closure is now explicit.**  The manifest binds the current
   source, fit, composition, callback-runtime, final-verifier, and focused-test
   bytes.  Any later drift again stops before source execution.

2. **Composition uses the frozen TLE path from preflight.**  The composition
   server's `CompositionServerSpec` has no TLE-root field; its existing runtime
   reconstructs the TLE root from `configuration.tle.root_default`.  The shell
   launcher consequently rejects a `--tle-root` that resolves differently from
   that frozen value.  This prevents source/composition from silently using
   different ephemeris roots.  Supporting a different root requires a new
   pre-outcome contract/preflight, not a launcher override.

3. **The composition callback is named by the preflight closure.**  The shell
   passes the runtime module/factory explicitly and the manifest hashes the
   exact callback bytes.

4. **Process success is not integrity success.**  The launcher reopens the
   final JSON and requires `PASS_FINAL_INTEGRITY`, exact 8/48/48 counts, and
   closed TEST/episode boundaries before writing `RESULTS.sha256` and
   `COMPLETE`.  An `INVALID_RUN` JSON cannot publish completion.

No simulator, source generation, fit, composition, TEST, or episode training
command was run while creating or updating this note.
