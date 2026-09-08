# C3-S LITE latency engineering report — 2026-09-08

## Outcome

The engineering acceptance target is met without a scientific change. On the
requested world `8464287092499831892`, lineage `2026092101`, and the first ten
steps of a 30-step episode, the optimized LITE selector measured **5.680 s mean
wall with eight workers**, 81.1% below the 30.08 s control interval. The same
code with the process pool disabled measured 25.810 s mean.

The catalog, nominal metric, service guard, exact `Fraction` score,
BASE-first tuple tie-breaking, and injected `eta_ref` are unchanged. The
archived v1 selected profile, nominal tuple, and realised tuple matched at all
ten benchmarked steps. A separate physical replay covers five steps in each of
two archived units and also compares complete action vectors.

## Profiling and the missing wall time

All measurements used the canonical interpreter and
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1`.
Archive freezing and environment reset were outside decision-wall statistics.
The initial archive freeze was 26.9–30.2 s once per harness run; a physical
step was approximately 0.02 s in the minimized profile and 0.19–0.21 s in the
ten-step benchmark.

The cProfile sample drove one complete LITE `C3SPolicyAdapter.select_actions`
call before the fix. It used the requested world/lineage and a one-step
minimized environment so the pathological Python profiler overhead remained
tractable. The first three steps were additionally measured with the normal
30-step environment; their archived end-to-end and inner phase timings are in
the next table.

| cProfile entry | Calls | Cumulative seconds | Finding |
|---|---:|---:|---|
| `C3SPolicyAdapter.select_actions` | 1 | 198.181 | Profiled selector wall |
| `_structural_sha256` | 9 | 174.549 | Recursive authentication hashes |
| `_live_neutrality_fingerprint` | 2 | 174.529 | Both pre/post whole-environment hashes |
| recursive `visit` | 42,573,577 | 174.549 | Traversed immutable archive/static graph |
| `_real_decision` | 1 | 23.324 | Actual coordinator work |
| `build_s0_catalog` | 1 | 23.289 | Catalog plus nominal evaluations |
| `NominalSnapshotEvaluator.evaluate` | 2,046 | 22.475 | Independent nominal candidates |
| `StepEnvironment._resolve_physics` | 2,046 | 22.087 | Candidate physics |
| `beam_field_at_users` | 2,046 | 13.506 | Largest physics substage |
| `bessel_j_array` / `_series_array` | 4,093 | 11.948 / 11.725 | Largest numerical kernel |

The profiled call made 765,178,694 total function calls (693,781,573
primitive). cProfile inflated wall substantially, so it is used for attribution
only.

The normal v1 receipt for the requested 30-step environment shows exactly
where the unreported wall went on its first three steps:

| Step | Selector wall (s) | Recorded adapter inner (s) | Outside recorded phases (s) | Q inference (s) | Nominal evaluation (s) | Enumeration (s) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 224.429 | 188.502 | 35.927 | 2.388 | 185.977 | 0.011 |
| 1 | 38.827 | 7.842 | 30.984 | 1.596 | 6.214 | 0.012 |
| 2 | 36.693 | 5.437 | 31.255 | 1.782 | 3.624 | 0.011 |

The missing approximately 31–36 s was the pre/post live-state authentication.
`run_arm_trajectory` times only the selector as decision wall, so committed
physical execution was not hidden in that gap. The runner and adapter now emit
separate reset, initial authentication, action validation, physical step,
metric/transition, snapshot construction, input authentication, decision core,
and live pre/post authentication timers.

For context, all 360 archived v1 LITE decisions under 12-way contention were:
mean 49.431 s, median 43.133 s, nearest-rank p95 57.246 s, maximum 254.478 s.
Their phase means were Q inference 1.917 s, nominal evaluation 12.927 s, and
enumeration 0.0117 s.

## Changes

1. The live-neutrality guard now hashes every mutable environment/driver field
   used by snapshotting or capable of advancing, including the environment,
   mobility, warm-start, and supplied RNG states (including SeedSequence child
   census). The immutable TLE archive, grid, satellite set, keyed field, and
   current candidate object remain identity-bound and are never recursively
   rehashed. The coordinator still receives only detached capability-free
   values. The nested mobility-RNG mutation regression remains enforced.
2. Unique action vectors are collected once in first-catalog order. Duplicate
   physical aliases still retain every catalog row and still reuse the first
   nominal result.
3. The detached evaluator has a batch seam. Each worker chunk constructs its
   detached geometry/physics context once and resets the copied segment list
   before every counterfactual, caching only per-decision invariants.
4. Optional process execution uses at most eight persistent worker processes.
   Candidate work is split into fixed contiguous chunks. Each task receives
   its evaluator snapshot, interval, action vector, profile label, and complete
   canonical action key explicitly. Workers force all four OMP/BLAS variables
   to `1`. Futures and rows are reduced strictly in submission/catalog order;
   no result is selected by completion order and no mutable state is shared.
5. The default remains `evaluation_workers=1`, which follows the original
   sequential per-candidate path. FULL remains single-process regardless of
   the LITE flag.

## Uncontended benchmark

One process at a time was run on the 20-core host; the implementation limited
candidate evaluation to the worker count shown. Values cover the same first
ten decisions of the requested 30-step world/lineage. p95 is nearest-rank, so
with ten observations it equals the cold-start maximum.

| Implementation | LITE workers | Decisions | Mean (s) | Median (s) | p95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|---:|
| v1 whole-graph guard | 1 | 10 | 59.110 | 39.853 | 224.811 | 224.811 |
| optimized targeted guard, pool off | 1 | 10 | 25.810 | 7.012 | 190.465 | 190.465 |
| optimized targeted guard + deterministic pool | 8 | 10 | **5.680** | **2.633** | 32.664 | 32.664 |

Raw selector walls (seconds):

- v1/1: `224.811, 39.288, 37.052, 36.586, 47.835, 40.417, 36.506, 35.464, 45.368, 47.776`
- optimized/1: `190.465, 7.719, 5.208, 4.324, 14.737, 8.128, 4.472, 3.914, 12.828, 6.306`
- optimized/8: `32.664, 2.761, 2.418, 2.087, 3.653, 3.063, 2.109, 2.049, 3.494, 2.504`

The eight-worker cold step is still 2.584 s above one interval, but the stated
acceptance criterion is mean decision wall and the measured mean is 5.680 s.
The cold step falls from 224.811 s to 32.664 s; steady decisions are 2.0–3.7 s.

## Equivalence and determinism

The normal test suite passes with the physical replay disabled. The opt-in
test command is:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export C3S_RUN_ARCHIVED_EQUIVALENCE=1
/home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-c3s-screen/test_c3s_screen.py \
  -k archived_lite_replay -s
```

It passed for:

- world `8464287092499831892`, lineage `2026092101`, steps 0–4;
- world `7305539127129390835`, lineage `2026092102`, steps 0–4.

For each unit it compares sequential old-path and pooled actions, selected
`profile_id`, nominal `(bits, energy, served)`, and realised
`(bits, energy, served)`; the latter three are also checked directly against
the read-only v1 receipt. It then executes the pooled path a second time and
asserts byte-identical canonical timing-free semantic rows and SHA-256 digest.
Timing fields are deliberately excluded from this digest because wall-clock
receipts are inherently non-identical between runs; the action/decision/outcome
receipt is what determinism governs.

No selected decision, complete action vector, nominal result, or realised
result differed in the 10 archived replay steps or the 10 benchmark steps.

## Residual risk

- Process scheduling changes wall timing only. Fixed chunk membership and
  canonical reduction prevent scheduling order from reaching selection.
- The pool uses Linux `fork`, matching this runner's Linux-only environment.
  Moving the runner to a platform without `fork` requires a separately tested
  transport choice.
- A worker crash fails the decision and therefore the unit closed; there is no
  partial-result fallback that could silently change a selection.
- Timing/RSS receipt fields remain nondeterministic observations. Scientific
  fields and the timing-free semantic digest are deterministic.

## Enabling the pool

The controller must first rebuild/rebind the preflight and launch authority
because the runner and policy code digests changed. Then add
`--lite-workers 8` to the otherwise authorized unit command, for example:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
/home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py \
  --preflight-manifest /path/to/rebound/C3S-PREFLIGHT-MANIFEST.json \
  --launch-authority /path/to/rebound/unit-launch-authority.json \
  --output /path/to/new-run-output \
  --horizon 30 \
  --unit 8464287092499831892:2026092101 \
  --lite-workers 8
```

Omitting the flag, or passing `--lite-workers 1`, keeps the old
single-process candidate-evaluation path. Valid values are 1 through 8. No
sealed contract, receipt, sidecar, or `*.sha256` file was changed.
