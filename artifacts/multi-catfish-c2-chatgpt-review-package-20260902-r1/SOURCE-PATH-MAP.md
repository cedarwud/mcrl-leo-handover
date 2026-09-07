# Source path map

This package is a review snapshot, not a runnable repository. Resolve original
repository paths through this table before declaring evidence missing.

## General mappings

| Original repository location | Packaged location |
|---|---|
| `docs/<name>` | `docs/<name>` |
| `docs/decisions/ADR-007-action-shared-three-q-instrument.md` | `docs/ADR-007-action-shared-three-q-instrument.md` |
| `src/mcrl/env/<name>` | `source/env/<name>` |
| `src/mcrl/runtime/<name>` | `source/runtime/<name>` |
| `src/mcrl/algorithms/<name>` | `source/algorithms/<name>` |
| `tests/test_w129_ee_axis_ops3.py` | `source/tests/test_w129_ee_axis_ops3.py` |
| `tests/test_w130_ee_axis_ops3_live.py` | `source/tests/test_w130_ee_axis_ops3_live.py` |
| `.scratch/c3-v04/v06_c2_k1_live_adapter.py` | `source/runners/v06_c2_k1_live_adapter.py` |
| `.scratch/c3-v04/run_v04_five_arm_ablation.py` | `source/runners/run_v04_five_arm_ablation.py` |
| `.scratch/c3-v04/run_v04_c3_confirmatory.py` | `source/runners/run_v04_c3_confirmatory.py` |
| `.scratch/c3-v04/run_v07_c2_fast_iteration.py` | `source/runners/run_v07_c2_fast_iteration.py` |

## Fable clean-room lane mappings

| Original repository path | Packaged path |
|---|---|
| `docs/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md` | `fable-cleanroom-lane/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/oracle/stage1b-report.md` | `fable-cleanroom-lane/oracle/stage1b-report.md` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/oracle/run_v08_c2_oracle_screen.py` | `fable-cleanroom-lane/oracle/run_v08_c2_oracle_screen.py` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/oracle/make_stage1b_report.py` | `fable-cleanroom-lane/oracle/make_stage1b_report.py` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/census/census-report.md` | `fable-cleanroom-lane/census/census-report.md` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/census/run_census.py` | `fable-cleanroom-lane/census/run_census.py` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/census/analyze.py` | `fable-cleanroom-lane/census/analyze.py` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/audit/<name>` | `fable-cleanroom-lane/audit/<name>` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/contracts/<name>` | `fable-cleanroom-lane/contracts/<name>` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/receipt.json` | `fable-cleanroom-lane/receipt.json` |

The original large raw census NPZ and Stage 1b row JSONL files were not copied.
Their hashes remain listed in
`fable-cleanroom-lane/RECEIPT-DIR-MANIFEST.sha256`. The three packaged result
JSON files below contain the machine-readable summaries needed for this review;
both Stage 1b result JSON files also contain the raw per-episode rows.

## Renamed evidence receipts

| Original repository path | Packaged path |
|---|---|
| `artifacts/fable-51-c2-cleanroom-20260902-r1/oracle/stage1b-HA-20260902/result.json` | `evidence/v08-stage1b-ha-result.json` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/oracle/stage1b-OPS3-20260902/result.json` | `evidence/v08-stage1b-fable-ops3-reading-result.json` |
| `artifacts/fable-51-c2-cleanroom-20260902-r1/census/census-result.json` | `evidence/v08-ha-census-result.json` |
| `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json` | `evidence/v04-route-interaction-result.json` |
| `artifacts/multi-catfish-v05-c2-controlled-tape-support-failure-20260901-r1/receipt.json` | `evidence/v05-support-failure-receipt.json` |
| `artifacts/multi-catfish-v06-c2-k1-postresult-diagnostics-20260902-r1/d0-diagnostic.json` | `evidence/v06-d0-diagnostic.json` |
| `artifacts/multi-catfish-v06-c2-k1-postresult-diagnostics-20260902-r1/loowo-diagnostic.json` | `evidence/v06-loowo-diagnostic.json` |
| `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-one-native28-balanced-sixanchor-sixseed-r13.json` | `evidence/v07-r13-balanced.json` |
| `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-native28-sixanchor-loao-r14.json` | `evidence/v07-r14-loao.json` |

The package-wide `MANIFEST.sha256` records the exact contents of every other
packaged file. A missing unlisted auxiliary path is an evidence limitation, not
permission to infer its contents.
