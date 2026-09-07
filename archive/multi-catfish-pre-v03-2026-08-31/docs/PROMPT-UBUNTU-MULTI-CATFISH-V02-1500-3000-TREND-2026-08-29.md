# Ubuntu worker prompt — Multi-Catfish MCRL V0.2 trend screen

> EXECUTED AND CLOSED: the single authorized R2 smoke completed with launcher
> exit 0 on 2026-08-29. Actual launcher wall time was 15:58.29. Do not paste or
> rerun this prompt; it does not authorize another smoke or any 1500/3000/9000
> training.

```text
[heavy | Ubuntu server required | this prompt authorizes only one five-arm
10EP launcher smoke; estimated wall time 15–20 min from the completed R2 receipt. Re-estimate later work from
the smoke receipts instead of promising a fixed finish time. No browser or GUI
is required.]

Before opening this worker

1. SSH to the Ubuntu training server.
2. Sync the explicitly listed current files and artifacts to the isolated
   checkout `/home/sat/mcrl-leo-handover-mc-v02-20260829`.
   Do not rely on git alone: `.scratch/smc-er-short-ep/`,
   `.scratch/catfish-stage0/`, the four intermediate authority JSONs, the R9
   portable support receipt, the R9 portable parity package, and the frozen C1 v2 corpus are
   untracked artifacts and must be copied byte-for-byte.
3. Confirm `/home/sat/mcrl-leo-handover-mc-v02-20260829/.venv` works and contains the current
   project dependencies.
4. Confirm the server TLE view is
   `/home/sat/mcrl-runtime/tle-frozen-20260820`, contains exactly 373 canonical
   files, and reproduces SHA-256
   `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`.
5. Open a Codex worker session in `/home/sat/mcrl-leo-handover-mc-v02-20260829` and paste the
   remainder of this prompt.

Objective

Run exactly one frozen five-arm Multi-Catfish MCRL V0.2 engineering launcher
smoke at 10EP, preserve its complete receipts, and stop. This prompt does not
authorize 1500EP, 3000EP, or 9000EP. Do not redesign roles, change parameters,
replace seeds, retry a failed arm, or convert smoke output into trend evidence.

Controlling files

- `docs/CATFISH-V0.2-OBSERVABLE-SUPPORT-SPEC-2026-08-28.md`
- `docs/CATFISH-V0.2-OBSERVABLE-SUPPORT-FREEZE-2026-08-28.json`
- `docs/MULTI-CATFISH-V02-INTERMEDIATE-TREND-PLAN-2026-08-28.md`
- `artifacts/multi-catfish-v02-intermediate-authority-20260828/1500-lr0p001.json`
- `artifacts/multi-catfish-v02-intermediate-authority-20260828/1500-lr0p01.json`
- the corresponding two 3000 authority JSONs

The only allowed arms are `B000/F111/A011/A101/A110`. Every 1500/3000 arm
must retain loadable Main snapshots at episodes 100, 200, …, endpoint; the
rolling full resume state is latest-only. Specialist bundle replay capacity is
exactly 2000. Evaluation is Main-only, TEST, ratio-of-sums EE.

Preflight

1. Record branch, HEAD, dirty status, Python/Torch/Numpy versions, CPU/RAM/disk,
   and TLE file count/hash. Preserve unrelated WIP; do not reset, stash, stage,
   commit, push, or delete anything.
2. Recompute and record hashes of the freeze, plan, four authority JSONs,
   `run_short_ep.py`, `smc_er_core.py`, `smc_er_roles.py`,
   `c1_exp_corpus.py`, `build_c1_exp_corpus.py`,
   `run_intermediate_trend_matrix.py`, `sweep_evaluation.py`,
   `checkpoint_trend_evaluation.py`, and `analyze_intermediate_trend.py`.
3. In a fresh process, validate all four authority JSONs. They must all return
   `PASS`, with checkpoint cadence 100 and bundle capacity 2000. Pass
   `/home/sat/mcrl-runtime/tle-frozen-20260820` explicitly as `tle_root` to
   `validate_intermediate_trend_authority`; receipts may not supply or retain a
   physical TLE path. Confirm R9 is support-census v2 and R9 is zero-dose parity
   v5 before accepting the result.
4. Run the focused suite covering core, roles, runner, authority, matrix,
   C1 builder/loader portability, checkpoint trajectory, analyser, and evaluate-actions purity. Any failure
   blocks launch.
5. Use `/usr/bin/time -v`; monitor RSS, disk, process state, log growth, and
   completed episodes. Use `tmux`. Never run more than two arms concurrently.

Stage 0 — exact launcher smoke

Run the five-arm launcher once with `1500-lr0p001.json`, `--smoke`, and
`--max-parallel 2`, writing a new absent output root such as:

`.venv/bin/python .scratch/smc-er-short-ep/run_intermediate_trend_matrix.py \
  --authority artifacts/multi-catfish-v02-intermediate-authority-20260828/1500-lr0p001.json \
  --output-root artifacts/multi-catfish-v02-server-smoke-20260829-r2-lr0p001 \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --max-parallel 2 \
  --smoke`

Do not treat the smoke EE as trend evidence. If it fails, preserve every log
and receipt, diagnose only, and stop before 1500EP. Do not retry silently.
Use its `/usr/bin/time -v` receipts to update the wall-time/RSS/disk estimate.

Future stages — explicitly not authorized by this prompt

Do not remove `--smoke`; do not invoke either 1500 authority, either 3000
authority, `checkpoint_trend_evaluation.py`, or `analyze_intermediate_trend.py`.
After the Stage 0 smoke completes, return its evidence to the controller and
wait for a new explicit launch gate and a separate worker prompt. A later
1500EP prompt will retain the frozen five arms, both learning rates, 100EP
checkpoint trajectories, deterministic LR rule, and no-retry policy, but none
of that long compute is authorized here.

Evidence and stop rules

- No 1500EP, 3000EP, or 9000EP process may be launched under this prompt. The
  user must be notified separately before any future 9000EP run.
- No retries, replacement seeds, changed user counts, Walker substitution,
  altered TLE root, changed beta/H/rewards/triggers, changed replay capacity,
  or changed checkpoint cadence.
- A process that is merely slow is not failed. Stop new launches only for a
  real nonzero exit, nonfinite state, authority/hash drift, missing checkpoint,
  zero-power guard, OOM/disk risk, or corrupt receipt. Let already running arms
  finish and preserve their evidence.
- Support census and parity are prerequisites, not efficacy evidence.
- 1500/3000 results are one-training-seed directional evidence, not Chapter 5,
  formal superiority, statistical significance, or permission for 9000EP.

Deliver after Stage 0

- process/running/completed status stated distinctly;
- exact commands, timestamps, exit codes, elapsed time, max RSS, disk use;
- matrix and authority hashes;
- five-arm command/exit/checkpoint and sweep receipt completeness;
- any smoke-only Main EE files, labelled engineering-only and not interpreted;
- served-fraction/zero-power/finite guards emitted by the launcher;
- explicit evidence ceiling and no hidden retries.

Proceed autonomously through Stage 0 only. Ask no ordinary operational
questions. Stop immediately after returning the smoke receipt, or earlier at a
real resource/safety blocker. Never continue into 1500/3000/9000.
```
