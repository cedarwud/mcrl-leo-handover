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
| 2 | Read action_contract.py ruling; locate beam representation in env | DONE | ruling reasons in DECLARATION §1; insertion point `step.py:822` |
| 3 | Write declaration before any run | DONE | `DECLARATION-2026-09-11.md` |
| 4 | Implement cap flag (env/mask layer, off by default) + bit-identity test | DONE, 7/7 pass on server | `beam_cap.py`, `test_beam_cap.py` (outside `src/`: ruling §7.1-7.2 + gate test) |
| 5 | Stage server ws from PENALTYARM snapshot + cap patch | DONE | snapshot `c46091d` (src .py sha256 identical to penalty-arm-ws, 157 files); cap + driver commit `6f4c162`; 2-ep smoke OK then deleted |
| 6 | Launch CAP3_OFF, CAP3_PENALTY (500 ep, detached) | RUNNING | PIDs 3386760 (CAP3_OFF), 3386761 (CAP3_PENALTY); logs `runs/<ARM>.log` |
| 7 | Greedy eval of all four cells + rank readouts | PENDING | |
| 8 | Report | PENDING | |

## Server runs

Launch (per arm), cwd `/home/sat/mcrl-v025-cap-penalty-ws`:
```
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
setsid nohup nice -n 16 /home/sat/mcrl-leo-handover/.venv/bin/python \
  cap-penalty/run_cap_pilot.py --arm <ARM> --out runs/<ARM> --episodes 500 --checkpoint-every 100 \
  > runs/<ARM>.log 2>&1 </dev/null &
```
On resume: check `ps -eo pid,args | grep "[c]ap-penalty/run_cap_pilot"` before relaunching; if a
run died, it must be relaunched from scratch (the driver does not resume mid-run; checkpoints
are for evaluation).
