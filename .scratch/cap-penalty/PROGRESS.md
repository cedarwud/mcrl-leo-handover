# CAPPENALTY progress

Started 2026-09-11. Agent CAPPENALTY. Every step checks for existing output first; an
interruption resumes at the first incomplete step. **No step is marked DONE before its
output exists. No result appears in this file before it was measured.**

Workspace (local): `/home/u24/papers/mcrl-leo-handover`, branch `wip/multi-catfish-v023-20260907`
Workspace (server): `sat:/home/sat/mcrl-v025-cap-penalty-ws` (fresh)
Python (server): `/home/sat/mcrl-leo-handover/.venv/bin/python`. **Never modify that tree.**
Caps: <=2 python procs, nice 16, BLAS/OMP threads 1, RSS < 5 GB, checkpoint every 100 ep.

## Step ledger (true state)

| # | Step | State | Output |
|---|------|-------|--------|
| 0 | Read PENALTYARM report / progress / declaration | DONE | (read) |
| 1 | Part 1: sibling records search (read-only subagent) | PENDING | |
| 2 | Read action_contract.py ruling; locate beam representation in env | PENDING | |
| 3 | Write declaration before any run | PENDING | |
| 4 | Implement cap flag (env/mask layer, off by default) + bit-identity test | PENDING | |
| 5 | Stage server ws from PENALTYARM snapshot + cap patch | PENDING | |
| 6 | Launch CAP3_OFF, CAP3_PENALTY (500 ep, detached) | PENDING | |
| 7 | Greedy eval of all four cells + rank readouts | PENDING | |
| 8 | Report | PENDING | |
