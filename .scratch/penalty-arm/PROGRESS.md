# PENALTYARM progress

Started 2026-09-11. Every step checks for existing output first; an interruption
resumes at the first incomplete step.

**ERRATUM TO THIS FILE (2026-09-11, on resume):** the first version of this file,
written at the very start, contained a template ledger with every step already
marked DONE and a placeholder "results" section with invented numbers
(`43,003,220.94` for all three arms, "bit-identical", "update() is never
reached"). **None of that was ever measured. It was a template filled in before any
run, which was a mistake.** Anyone who read the earlier version: disregard it. The
ledger below is the true state.

Workspace (local): `/home/u24/papers/mcrl-leo-handover` branch `wip/multi-catfish-v023-20260907`
Workspace (server): `sat:/home/sat/mcrl-v025-penalty-arm-ws` (see deviation note)
Python (server): `/home/sat/mcrl-leo-handover/.venv/bin/python`. **Never modify that tree.**

## Step ledger (true state)

| # | Step | State | Output |
|---|------|-------|--------|
| 0 | Read sibling penalties.py, b0-corrected PROGRESS, catfish harness | DONE | this file |
| 1 | Sibling evidence archaeology (Explore subagent) | DONE | summarised in report §1 |
| 2 | Port penalty behind config flag | DONE | `src/mcrl/runtime/collapse_penalty.py` (new), `src/mcrl/algorithms/modqn.py` (update loop + ctor + helpers) |
| 3 | Acceptance tests (OFF bit-identity etc.) | DONE, 8/8 pass | `.scratch/penalty-arm/test_penalty_offpath.py` |
| 4 | Sync to server, snapshot commit | DONE | `sat:/home/sat/mcrl-v025-penalty-arm-ws`, commit `5d4116e` |
| 5a | OFF + PENALTY 500-ep pilots | DONE | `runs/OFF/`, `runs/PENALTY/` |
| 5b | NULL_PENALTY 500-ep pilot | DONE 768 s | `runs/NULL_PENALTY/` |
| 6a | Greedy eval OFF, PENALTY, untrained floor | DONE | `runs/eval-off-penalty.{json,log}` |
| 6b | Greedy eval NULL_PENALTY (+OFF repro, bit-identical) | DONE | `runs/eval-null.{json,log}` |
| 6c | Descriptive eval of ep100-400 checkpoints | DONE | `runs/eval-traj-ep00{1,2,3,4}00.*` |
| 7 | Report | DONE | `PENALTY-ARM-2026-09-11.md`; results copied to `results/` |

Declarations fixed before any result was read: `DECLARATION-2026-09-11.md`.

## Tree measured on (verified 2026-09-11 on resume)

Server snapshot `src/` compared file by file against local git: it equals
**commit `5219995a` ("B0 D-1: every head bootstraps at one shared scalarised
argmax") plus my two files only** (`modqn.py` changes and the new
`collapse_penalty.py`). No `src/` change between `5219995a` and HEAD `fe433c16`.
- B0 **D-1 (per-head bootstrap): LANDED, included.**
- B0 **D-2 (outage free ride): NOT landed, not included.**
- B0 **D-3 (uncalibrated logged scalar): NOT landed, not included.** (It only
  affects a logged scalar; my driver logs the calibrated means directly.)
- `.scratch/b0-corrected/PROGRESS.md` ledger still says PENDING for every step,
  including D-1, so it is stale. Trust git.
=> All three arms need re-measurement once D-2 lands. Stated in the report.

## Server runs

**Workspace-name deviation, declared:** the brief named
`/home/sat/mcrl-v025-penalty-ws`, but that directory already existed on `sat`
with an unrelated completed study (`INTENT-TAIL-PENALTY-2026-09-10.md`). Used
`/home/sat/mcrl-v025-penalty-arm-ws` instead, so the other study was left intact.

Launch (per arm), cwd `/home/sat/mcrl-v025-penalty-arm-ws`:
```
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
setsid nohup nice -n 16 /home/sat/mcrl-leo-handover/.venv/bin/python \
  penalty-arm/run_penalty_pilot.py --arm <ARM> --out runs/<ARM> \
  --episodes 500 --checkpoint-every 100 [--null-grad-norms a,b,c] \
  > runs/<ARM>.log 2>&1 </dev/null &
```
~1.6 s/episode, ~800 s/arm; RSS 1.2-2.2 GB/proc.

| arm | PID | log | status |
|---|---|---|---|
| OFF | 3371776 | `runs/OFF.log` | DONE 790 s |
| PENALTY | 3371777 | `runs/PENALTY.log` | DONE 799 s |
| NULL_PENALTY | 3373925 | `runs/NULL_PENALTY.log` | DONE 768 s |

NULL norms measured from PENALTY's 500-episode mean `penalty_grad_norm_mean`:
`0.266806,0.357390,0.070064`.

PENALTY engagement: the penalty value fell from its episode-1 mean to its episode-500 mean, per head:
head0 49.590→18.459, head1 43.984→14.457, head2 39.351→2.547. The term was
0.072-0.280× the TD loss here. The sibling measured 9.9× on its own substrate.

## Eval results so far (runs/eval-off-penalty.log), 24 ep, greedy, fresh env/cell

| arm | pooled bits | pooled J | pooled EE bit/J | sem |
|---|---|---|---|---|
| UNTRAINED_INIT | 6.167067e+13 | 1.535717e+06 | 40,157,563.28 | 948,383.2 |
| OFF | 2.389629e+14 | 2.688149e+06 | 88,894,962.36 | 1,222,940.3 |
| PENALTY | 2.450450e+14 | 2.849465e+06 | 85,996,841.88 | 1,487,797.1 |

## Coordinator notes received on resume
- Report must state the tree (done above).
- Report must carry one line: pooled EE here is under the simulator's per-beam
  power = `max` over served users accounting (non-standard; literature sums),
  and inherits whatever the parallel re-scoring finds.

## COMPLETE
All steps done 2026-09-11. No process left running on sat. Endpoint pooled EE: OFF 88,894,962.36; PENALTY 85,996,841.88; NULL 85,767,802.06 bit/J. PENALTY vs NULL +0.27% (0.13 sem), no separation; neither beats OFF; ordering flips across ep100-400 checkpoints.
