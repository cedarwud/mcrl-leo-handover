# Source path map

This package is a read-only review snapshot, not a runnable repository. Copied
documents may retain absolute paths and line links from the original checkout.
Resolve them as follows.

| Original repository location | Packaged location |
|---|---|
| `docs/<name>` | `docs/<name>` |
| `docs/decisions/ADR-007-action-shared-three-q-instrument.md` | `docs/ADR-007-action-shared-three-q-instrument.md` |
| `src/mcrl/env/<name>` | `source/env/<name>` |
| `src/mcrl/runtime/<name>` | `source/runtime/<name>` |
| `src/mcrl/algorithms/<name>` | `source/algorithms/<name>` |
| `tests/test_w129_ee_axis_ops3.py` | `tests/test_w129_ee_axis_ops3.py` |
| `.scratch/c3-v04/v06_c2_k1_live_adapter.py` | `source/runners/v06_c2_k1_live_adapter.py` |
| `.scratch/c3-v04/run_v04_five_arm_ablation.py` | `source/runners/run_v04_five_arm_ablation.py` |
| `.scratch/c3-v04/run_v04_c3_confirmatory.py` | `source/runners/run_v04_c3_confirmatory.py` |
| `.scratch/c3-v04/run_v07_c2_fast_iteration.py` | `source/runners/run_v07_c2_fast_iteration.py` |

## Renamed sealed receipts

| Original repository path | Packaged path |
|---|---|
| `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json` | `evidence/v04-route-interaction-result.json` |
| `artifacts/multi-catfish-v04-c2-failure-forensics-20260901-r1/result.json` | `evidence/v04-c2-failure-result.json` |
| `artifacts/multi-catfish-v04-c2-failure-forensics-20260901-r1/result-seal.json` | `evidence/v04-c2-failure-result-seal.json` |
| `artifacts/multi-catfish-v05-c2-controlled-tape-support-failure-20260901-r1/receipt.json` | `evidence/v05-support-failure-receipt.json` |
| `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/design-eval/evaluation-result.json` | `evidence/v06-bounded-evaluation-result.json` |
| `artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze/design-eval/evaluation-seal.json` | `evidence/v06-bounded-evaluation-seal.json` |
| `artifacts/multi-catfish-v06-c2-k1-postresult-diagnostics-20260902-r1/d0-diagnostic.json` | `evidence/v06-d0-diagnostic.json` |
| `artifacts/multi-catfish-v06-c2-k1-postresult-diagnostics-20260902-r1/loowo-diagnostic.json` | `evidence/v06-loowo-diagnostic.json` |
| `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-one-native28-balanced-sixanchor-sixseed-r13.json` | `evidence/v07-r13-balanced.json` |
| `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-native28-sixanchor-loao-r14.json` | `evidence/v07-r14-loao.json` |

The SHA-256 manifest records the exact contents of every packaged file. A
missing unlisted auxiliary path in an older document is an evidence limitation,
not permission to infer its contents.
