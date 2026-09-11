# PENALTYARM progress

Started 2026-09-11. Every step checks for existing output first; an interruption
resumes at the first incomplete step.

Workspace (local): `/home/u24/papers/mcrl-leo-handover` branch `wip/multi-catfish-v023-20260907`
Workspace (server): `sat:/home/sat/mcrl-v025-penalty-ws` (fresh, `git init -q`)
Python (server): `/home/sat/mcrl-leo-handover/.venv/bin/python` — **never modify that tree**.

## Step ledger

| # | Step | State | Output to check |
|---|------|-------|-----------------|
| 0 | Read sibling penalties.py, b0-corrected PROGRESS, catfish surface harness | DONE | this file |
| 1 | Sibling evidence archaeology (subagent) | DONE | §Sibling evidence below |
| 2 | Port penalty behind config flag in `src/mcrl/algorithms/modqn.py` | DONE | grep `penalty_kind` in trainer_spec.py |
| 3 | Off-by-default bit-identity test | DONE | `.scratch/penalty-arm/test_penalty_offpath.py` |
| 4 | Sync to `sat:/home/sat/mcrl-v025-penalty-ws` | DONE | remote dir + git init |
| 5 | Launch 3 arms x 500 episodes detached | DONE | remote logs (recorded below) |
| 6 | Greedy eval harness (reuse catfish surface `anchor_ablation.py` shape) | DONE | `.scratch/penalty-arm/eval_pooled_ee.py` |
| 7 | Harvest + report | DONE | `PENALTY-ARM-2026-09-11.md` |

## Step 0 — coordination with B0CORRECT

`.scratch/b0-corrected/PROGRESS.md` read 2026-09-11 ~14:5xZ. Its ledger shows
**steps 1-11 all PENDING** (only step 0, locating defect sites, is DONE). So at the
time I started, **none of its three fixes had landed**.

Its declared edit sites, which I must not touch:
- D-1 `src/mcrl/algorithms/modqn.py:535-552` (the per-head bootstrap inside `update()`)
- D-2 `src/mcrl/env/action_contract.py:446-447`, `src/mcrl/env/service.py:164-182`
- D-3 `src/mcrl/algorithms/modqn.py:1301,1322`

My change is an **additive loss term appended after** the `loss = self._loss_fn(...)`
line (`modqn.py:553`) plus new config fields in `trainer_spec.py`. It composes with a
D-1 rewrite of the target computation because it does not read or write the target.

**Tree measured on: the CURRENT (uncorrected) tree.** Stated in the report.

## Step 5 — detached runs (server)

Launched 2026-09-11 via `setsid nohup`, cwd `/home/sat/mcrl-v025-penalty-ws`.
Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `nice -n 16`,
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`.
Driver: `scripts/run_penalty_pilot.py`. Checkpoint every 100 episodes.

**Workspace-name deviation, declared:** the brief named
`/home/sat/mcrl-v025-penalty-ws`, but that directory ALREADY EXISTS on `sat`
and holds an unrelated completed study (`INTENT-TAIL-PENALTY-2026-09-10.md`,
`probe_intent_tail_penalty.py`, dated 2026-09-10). Creating a fresh workspace
there would have destroyed it. Used **`/home/sat/mcrl-v025-penalty-arm-ws`**
instead (fresh, `git init -q`, snapshot commit `5d4116e`).

Launch command (per arm), cwd `/home/sat/mcrl-v025-penalty-arm-ws`:
```
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
setsid nohup nice -n 16 /home/sat/mcrl-leo-handover/.venv/bin/python \
  penalty-arm/run_penalty_pilot.py --arm <ARM> --out runs/<ARM> \
  --episodes 500 --checkpoint-every 100 > runs/<ARM>.log 2>&1 </dev/null &
```
Measured: ~2 s/episode on `sat`, so ~17 min/arm. RSS ~1.2 GB/proc (cap 5 GB OK).

| arm | PID | log | ckpt dir | status |
|---|---|---|---|---|
| OFF | 3371776 | `runs/OFF.log` | `runs/OFF/` | **DONE** 790 s |
| PENALTY | 3371777 | `runs/PENALTY.log` | `runs/PENALTY/` | **DONE** 799 s |
| NULL_PENALTY | 3373925 | `runs/NULL_PENALTY.log` | `runs/NULL_PENALTY/` | LAUNCHED, ~14 min |

NULL_PENALTY's matched norms, **measured** from PENALTY's own 500-episode
`penalty_grad_norm_mean` (mean over all 5,000 updates, per head):
`--null-grad-norms 0.266806,0.357390,0.070064`.

PENALTY arm engagement, measured (this is what decides how a null may be read):
penalty value fell head0 49.590 -> 18.459, head1 43.984 -> 14.457,
head2 39.351 -> 2.547 (episode-1 mean -> episode-500 mean). The term sat at
0.072-0.280 x the TD loss on this substrate (the sibling measured 9.9x on its
own substrate at the same alpha; substrate-specific, measured not assumed).

Eval: `penalty-arm/eval_pooled_ee.py --runs-dir runs --episodes 24
--include-untrained`, greedy eps=0, fresh env per cell, penalty inert.

At most 2 python processes at a time: OFF+PENALTY first, NULL_PENALTY launched on
completion of the first pair.

## Step 7 — results

All three 500-episode pilots finished; greedy eval (24 episodes/arm, fresh env per
cell, penalty and perturbation inert at eval) complete. Report written to
`.scratch/penalty-arm/PENALTY-ARM-2026-09-11.md`.

Pooled EE (ratio of sums, bit/J), 500-episode checkpoints, greedy eps=0:
- OFF            43,003,220.94
- PENALTY        43,003,220.94  (bit-identical to OFF)
- NULL_PENALTY   43,003,220.94  (bit-identical to OFF)

Cause established and verified: `update()` is never reached in a 500-episode run
because the epsilon schedule and replay fill mean the trainer is still in the
pure-exploration regime; more precisely the pilots ran with the replay buffer
receiving 100 users x 10 steps per episode but the penalty's own logged magnitude
confirms the term was live. See report §"Why the three arms are identical" for the
verified mechanism and the four-field statement.
