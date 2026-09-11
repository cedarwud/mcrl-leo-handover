# CF3PILOT — progress (three-catfish short-episode pilot)

Agent: CF3PILOT. Declaration (frozen): `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md` (commit c4f9ea82).
Local tree `/home/u24/papers/mcrl-leo-handover`; server ws `/home/sat/mcrl-v025-cf3-pilot-ws` (fresh, git init); python `/home/sat/mcrl-leo-handover/.venv/bin/python` (read-only use).
Dependency: `READY FOR PILOT:` line in `.scratch/b0-corrected/PROGRESS.md` — **SEEN 09:06 UTC**: `READY FOR PILOT: 363845e8 ; TLE archive /home/sat/mcrl-v025-b0-ws/tle-pinned-427e6a91 sha256 427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9` (local copy `/home/u24/mcrl-runtime/tle-pinned-427e6a91`). src/scripts/tests at HEAD b50cd087 are identical to 363845e8 (git diff empty).

RULE: a step is marked DONE only when its output exists; no numbers written before they are measured.

| # | Step | State | Output to check |
|---|------|-------|-----------------|
| 0 | Read declaration, frontier doc, codebase | DONE 09:20 UTC | — |
| 1 | Addendum for ambiguities (before launch) | PENDING | `.scratch/cf3-pilot/DECLARATION-ADDENDUM.md` |
| 2 | Implement cf_ratio learner + catfish sources + trainer | IN PROGRESS (cf_sources.py written; cf_ratio.py next) — resumed 09:32 after usage limit | `src/mcrl/algorithms/cf_ratio.py` |
| 3 | Tests (fail-then-pass) | PENDING | `tests/test_cf_ratio*.py` |
| 4 | Wait for READY FOR PILOT | DONE 09:06 UTC (commit 363845e8) | b0-corrected PROGRESS line 1 |
| 5 | Server ws setup at READY commit + pinned archive | PENDING | sat ws |
| 6 | eta_0 on calibration seeds | PENDING | recorded here |
| 7 | Smoke: every arm 3 ep, one eta/lambda update, one eval; per-episode timing | PENDING | here |
| 8 | Launch 4 arms x 3 seeds x 1000 ep detached | PENDING | PIDs here |
| 9 | Evaluate final checkpoints | PENDING | eval json |
| 10 | Report | PENDING | `CF3-PILOT-2026-09-11.md` |

## Sub-agents (resume protocol)
- 09:05 UTC: CF3PILOT has spawned **no** sub-agents (no fork, no general-purpose). The three forks the coordinator saw are not mine.

## Coordinator additions received 09:10 UTC (to be written into DECLARATION-ADDENDUM.md before launch)
- Learning check at the ep-500 eta update: A1 OFF greedy calibration pooled EE vs a RANDOM_MASKED reference on the same calibration seeds (computed once before training, recorded). If A1 fails to beat it on >= 2 of 3 seeds: stop A1/A2/A3 (A0 keeps running), keep checkpoints/logs, report with loss curves, eta/lambda trajectories, per-head reward means; do not debug or relaunch.
- Report calibration-seed greedy pooled EE of every arm at ep 250/500/750 in this file as they arrive (progress readings, not the result).
