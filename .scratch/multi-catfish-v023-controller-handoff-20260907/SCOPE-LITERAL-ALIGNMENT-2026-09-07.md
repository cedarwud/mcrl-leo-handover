# V0.23 C1/C2 short-benchmark scope-literal alignment (2026-09-07)

Status: execution-contract correction only. No producer, formula, data,
selection, seed, threshold, or claim-ceiling change.

## Failure being corrected

- Attempt root (preserved, never overwritten):
  `/home/sat/mcrl-v023-c1c2-target-generation-20260907-ops3-r4`
- Receipt: `short-benchmark-receipts/c2-informed-single.json`,
  status `SHORT_BENCHMARK_FAILED`, error `short benchmark scope drifted`.
- The wrapper had already accepted producer schema
  (`multi-catfish-mcrl-v023-c1c2-target-generation-benchmark-v1`), status
  `BENCHMARK_PASS`, and the benchmark claim ceiling before rejecting the
  descriptive `scope` string.

## Adjudication

- Producer (`benchmark_v023_c1c2_targets.py`, SHA-256
  `d2ca43cb53e76e966bb6f4214e6f32af0c05f0fb59dfac121ee284a876988cb3`, role
  `short_benchmark`, unchanged) emits:
  `C2 repriced OPS-3 selected-pair generation only; no C1 timing, learner, TEST, or efficacy claim`
- Wrapper (`run_v023_c1c2_short_benchmarks.py`, previously
  `06cc477a389e82ea1136d986fb405ead7e4720cf14d8ae7a09e5a7e3e1b461af`) expected:
  `C2 physical target generation only; no C1 timing, learner, TEST, or efficacy claim`
- The wrapper's own test fixture used the old wording, so the wrapper tests
  passed against a synthetic payload and never against the real producer.
- The two strings differ only in the activity descriptor; the disclaimer tail
  is identical, the producer wording is the more precise current description
  of the adopted repriced OPS-3 selected-pair route, and the substantive claim
  boundary is enforced separately by the claim-ceiling check that already
  passed. Nothing else in `docs/`, `artifacts/`, `src/`, or `.scratch/`
  references either literal. Ruling: legitimate execution-contract
  correction; align the wrapper literal to the producer's exact string once.

## Changes (only these)

1. `run_v023_c1c2_short_benchmarks.py` line 504: expected scope literal set to
   the producer's exact string.
2. `test_v023_c1c2_short_benchmarks.py`: fixture literal aligned; added
   `test_wrapper_accepts_exact_frozen_producer_scope_literal` (positive; also
   asserts the literal occurs exactly once in the frozen producer source) and
   `test_wrapper_rejects_any_other_scope_literal` (mutation-negative, 9
   variants incl. the previous wording, dropped disclaimers, added claim,
   case/whitespace change, empty, missing).
3. `CODE-MANIFEST.json`: only the `short_benchmark_runner` and
   `short_benchmark_tests` digests updated
   (`06cc477a…` -> `7adcb4957a40…`, `ae237038…` -> `1cf23533935c…`);
   manifest SHA-256 `93d5f03d…` -> `8a290eeea1bc6534e7d57c63327c9212e3a911daf5e4299bea0f3ae7315ef2e9`;
   `CODE-MANIFEST.sha256` sidecar regenerated.

## Local evidence before relaunch

- 43 passed (two launch test files, incl. 10 new scope tests).
- `preflight_v023_c1c2_targets.py`: `PASS_LOCAL_CODE_AND_R6_D40_BINDING`,
  R6 manifest still `761436f0…`.
- `audit_v023_c1c2_checkpoint_closure.py --require-ready`: PASS.
- `sync_launch … --dry-run` with r5 names: PASS.

## Relaunch

- Server root `/home/sat/mcrl-v023-c1c2-target-generation-20260907-ops3-r5`
- Output root `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r5`
- tmux `mcrl-v023-c1c2-target-generation-20260907-ops3-r5`
- Gate: the runner executes informed-single first; if that receipt fails, the
  attempt is stopped and reported (no further repair versions).
