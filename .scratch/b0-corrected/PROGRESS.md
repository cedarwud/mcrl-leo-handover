# B0CORRECT progress

Started 2026-09-11. Every step checks for existing output first; an interruption
resumes at the first incomplete step.

## Step ledger

**Where the code is:** D-1 `5219995a` is on the SHARED branch
`wip/multi-catfish-v023-20260907`. D-2 `832471ca`, D-3 `0acd146c` and the pilot
scripts `923d68b0` are ONLY on branch `b0/corrected-baseline-20260911`
(worktree `/home/u24/papers/mcrl-leo-handover-b0`) — see Concurrency Incident.

| # | Step | State | Output to check |
|---|------|-------|-----------------|
| 0 | Locate the three defect sites | DONE | this file, section Step 0 |
| 1 | D-1 test (fails first) | DONE — 3/4 red pre-fix | `tests/test_b0_d1_scalarised_bootstrap.py` |
| 2 | D-1 fix + commit | DONE `5219995a` | git log grep `B0 D-1` |
| 3 | D-2 test (fails first) | DONE — 2/7 red pre-fix, on substance | `tests/test_b0_d2_outage_floor.py` |
| 4 | D-2 fix + commit | DONE `832471ca` | git log grep `B0 D-2` |
| 5 | D-3 test (fails first) | DONE — 5/6 red pre-fix | `tests/test_b0_d3_calibrated_scalar_log.py` |
| 6 | D-3 fix + commit | DONE `0acd146c` + fixup `ccbbb048` | git log grep `B0 D-3` |
| 7 | Full regression sweep | DONE — 55 fail, IDENTICAL IDs to pre-D-1 baseline `e3f3503e` | id lists: session scratchpad `ids-*.txt` (not durable; the result is recorded here) |
| 8 | Sync to `sat:/home/sat/mcrl-v025-b0-ws` | DONE — 348 files sha256-verified; both trees server-smoked | `sat:/home/sat/mcrl-v025-b0-ws/STAGE.sha256` |
| 9 | Launch 500-episode pilot detached | RUNNING — B0 **relaunched** 07:50:07 UTC PID 3383079 (first attempt died ep 50, see below); UNFIXED PID 3381656 since 07:45:10; NOT done until `status.json` says complete | `sat:/home/sat/mcrl-v025-b0-ws/pilot-{b0,unfixed}-500/status.json` |
| 10 | Harvest pilot + greedy eval | PENDING | report md |
| 11 | Write report | PENDING | `B0-CORRECTED-BASELINE-2026-09-11.md` |

## Step 0 — defect sites, verified by reading

- **D-1** `src/mcrl/algorithms/modqn.py:535-552` (`MODQNTrainer.update`). Confirmed:
  inside `for obj_idx in range(3)`, `q_next_all = self.target_nets[obj_idx](ns)`,
  `q_next_max = q_next_all.max(dim=1).values`. Per-head argmax. Verified by reading.
- Deployed selector weights: `TrainerConfig.objective_weights`, default `(0.5,0.3,0.2)`,
  declared at `src/mcrl/runtime/trainer_spec.py:52`; read by
  `MODQNTrainer.select_actions` at `modqn.py:383` (`w = objective_weights or
  self.config.objective_weights`) and scalarised in `scalarized_q_values`.
  **The fix reads `self.config.objective_weights`, not a literal.**
- **D-2** the prose site the brief cites (`runtime/outage_gate.py:10-27`) is the module
  docstring, which *describes* `r2 = 0`, `r3 = 0` for an unserved user. The values are
  actually produced at:
  - `src/mcrl/env/action_contract.py:446-447` — `classify_handover` returns
    `HandoverClass.NONE` when `current` is `UNSERVED`, and `HANDOVER_COST[NONE] = 0.0`,
    so `r2_handover = -0.0`;
  - `src/mcrl/env/service.py:164-182` — `ServiceResolution.user_beam_load()` returns
    `0.0` for an unserved user, so `r3_counting` gives `r3 = -0.0`.
  - assembled at `src/mcrl/env/step.py:1094-1104` (`_rewards`).
  Served ranges: `r2 in {0, -PHI1=-0.5, -PHI2=-1.0}`; `r3 = -U_{b_u} <= -1` because a
  served user counts itself in its own beam's load. Verified by reading.
- **D-3** `src/mcrl/algorithms/modqn.py:1301` computes
  `scalar = scalarize_objectives(avg_reward, cfg.objective_weights)` from the
  **uncalibrated** `avg_reward`, and `:1322` logs it as `scalar_reward`, while
  `:1304 calibrated = apply_reward_calibration(avg_reward, cfg)` is what training uses.
  Note: `EpisodeLog` **already carries** `r1/r2/r3_mean_calibrated`
  (`trainer_spec.py:231-233`), populated at `modqn.py:1326-1328`. So the missing piece
  is the calibrated scalar plus surfacing the three calibrated means in the human-facing
  log record / status file. Verified by reading.

## CONCURRENCY INCIDENT (2026-09-11 ~06:58 UTC) — read before resuming

Another agent was writing `src/mcrl/algorithms/modqn.py` and
`src/mcrl/runtime/collapse_penalty.py` (PENALTYARM) in the SHARED tree
`/home/u24/papers/mcrl-leo-handover` while I worked. A pytest run caught its
file mid-write (`NameError: PenaltyConfig`). It also committed `ec1f29d3` on top
of my D-1 commit on `wip/multi-catfish-v023-20260907`.

Response: D-1 was already committed on the shared branch (`5219995a`). I reverted
my uncommitted D-2 work out of the shared tree (my three files only; their
modqn.py edits left untouched — except one stray harmless line, see below) and
moved ALL further work to an isolated worktree:

  **worktree** `/home/u24/papers/mcrl-leo-handover-b0`
  **branch**   `b0/corrected-baseline-20260911` (from `ec1f29d3`, contains D-1)

A second detached worktree `/home/u24/papers/mcrl-b0-baseline` at `e3f3503e`
(pre-D-1) exists only to produce the regression baseline. Safe to remove.

Stray line: the shared tree's `modqn.py` still carries my one-line
`num_users: int | None = None,` kwarg on `reward_vector_from_step_result`
(additive, unused there). Left in place to avoid writing into a file another
agent is actively editing. Flag to the user.

## Step 1-7 detail

- D-1 test `tests/test_b0_d1_scalarised_bootstrap.py`: 3 of 4 FAILED on unfixed
  code (the 4th is a fixture-teeth check that must pass). Green after fix.
  Three W-08 assertions amended (they encoded the defect as the B1 contract).
- D-2 test `tests/test_b0_d2_outage_floor.py`: with plumbing but no floor,
  2 of 7 FAILED on substance: `outage r2=0.0 beats the worst served r2=-1.0`,
  `assert 0.0 <= -0.5`. Green after fix.
- D-3 test `tests/test_b0_d3_calibrated_scalar_log.py`: 5 of 6 FAILED on unfixed
  code; the passer is the head-means-present check (fields pre-existed).
- Regression: full `tests/` sweep, 55 failures, set-identical by test ID to the
  pre-D-1 baseline. Zero regressions introduced.

## Step 8 — sync (DONE 2026-09-11 ~07:40 UTC)

- Workspace `sat:/home/sat/mcrl-v025-b0-ws` created fresh, `git init -q`.
  `/home/sat/mcrl-leo-handover` and its venv untouched (read-only use of its python).
- Two trees, built with `git archive` from exact commits, sha256-verified on sat
  (`STAGE.sha256`, 348 files, all OK):
  - `b0/`      = B0 branch commit `923d68b0` (D-1 + D-2 + D-3 + pilot scripts)
  - `unfixed/` = pre-D-1 commit `e3f3503e` + the SAME two driver scripts from `923d68b0`
- Server smoke, 1 episode each, REAL `validate_server_setup` (prereg bytes, probe
  refreeze, P6 protocol, ephemeris): both `complete validated=True`, ~2.1 s/episode.
- `mcrl` resolves to the workspace `src/`, not the stale editable install (verified).
- Ep-0 check vs frozen `main/episode-logs.json[0]`: `unfixed` IDENTICAL on
  r1/r2/r3 means, handovers, replay size, epsilon; losses differ at ~8th sig. digit.
  `b0` identical on r1 (ε=1, actions do not depend on Q); r2 -8.435 vs -7.815,
  r3 -75.28 vs -13.28 -> the D-2 floor at ~6.2% outage rate.

## Step 9 — PILOT LAUNCHED 2026-09-11 07:45:10 UTC

| arm | PID | cwd | out dir | log |
|-----|-----|-----|---------|-----|
| B0 | 3381654 | `/home/sat/mcrl-v025-b0-ws/b0` | `/home/sat/mcrl-v025-b0-ws/pilot-b0-500` | `/home/sat/mcrl-v025-b0-ws/pilot-b0-500.log` |
| UNFIXED | 3381656 | `/home/sat/mcrl-v025-b0-ws/unfixed` | `/home/sat/mcrl-v025-b0-ws/pilot-unfixed-500` | `/home/sat/mcrl-v025-b0-ws/pilot-unfixed-500.log` |

Command (per arm, from `launch_pilots.sh`, idempotent — skips complete or live arms):
`setsid nohup systemd-run --user --scope -p MemoryMax=5G --quiet nice -n 16
/home/sat/mcrl-leo-handover/.venv/bin/python scripts/run_b0_pilot.py
--out-dir <out> --episodes 500 --label <ARM>` with OMP/MKL/OPENBLAS threads = 1.

Expected finish: ~2.1 s/ep x 500 = ~18 min -> **~08:05 UTC**, allow to 08:20.
Checkpoints: `<out>/checkpoint-ep00100.pt` ... `checkpoint-ep00500.pt`; resume
checkpoint overwritten every 100. **To resume after interruption:** re-run
`/home/sat/mcrl-v025-b0-ws/launch_pilots.sh`.

## Coordinator items (2026-09-11 ~07:50 UTC) — addressed

1. Attribution: D-1 commit `5219995a` contains **zero** PENALTYARM lines
   (`git show 5219995a -- modqn.py | grep -ci penalty` = 0); it was committed
   before PENALTYARM's hunks existed. D-2/D-3 were committed in the isolated
   worktree, so PENALTYARM's hunks were never staged by me. My one stray
   uncommitted line in the shared tree (`num_users` kwarg, its own hunk
   `@@ -636,4 +767,5 @@`, no overlap) has been **removed**; the shared tree's
   remaining `modqn.py` diff is entirely PENALTYARM's. Nothing of theirs was
   reverted or edited.
2. PROGRESS.md brought to true state (this file). Pilot is RUNNING, not DONE.

**For PENALTYARM (relay):** its measurements on `5219995a` include D-1, so its
OFF arm bootstraps at the shared scalarised argmax — it is NOT the frozen
per-head-max MODQN of `e6b063ef`. It does NOT include D-2 or D-3.

## B0 first attempt FAILED at episode 50 (07:46:55 UTC) — fixed, relaunched

`NameError: name 'scalar' is not defined` at `modqn.py:1452`, the stdout
progress line in `train()`. D-3 removed the local `scalar`; no test enabled
progress printing, and the 1-2 episode smokes never reached `progress_every=50`.
(The frozen pipeline's own main run uses `progress_every=100` and would have died
at episode 100 on the D-3 code.)
- Test added (`test_the_stdout_progress_line_prints_the_calibrated_headline_and_three_heads`),
  seen RED with the same NameError, then fix -> green. Commit `ccbbb048`
  ("B0 D-3 fixup"), revert together with `0acd146c`.
- Failed run preserved as `sat:/home/sat/mcrl-v025-b0-ws/pilot-b0-500.FAILED-ep50-scalar-nameerror{,.log}`.
- `b0/` tree resynced from `ccbbb048`, sha256-verified, B0 relaunched:
  **PID 3383079, 07:50:07 UTC, expected finish ~08:10 UTC** (allow to 08:25).
  UNFIXED untouched (PID 3381656, still running its `e3f3503e` tree).

## Harness validity — VERIFIED locally (B0 tree, 2026-09-11 ~07:55 UTC)

`scripts/b0_pooled_ee_eval.py --random`, N_EP=24, seeds 42/1337/7, local TLE archive:
pooled EE **53,060,175.56 bit/J**, bits 1.842866e14, joules 3.473162e6, served 0.9360,
ho 0.8680 — **exact match** to the catfish-surface table. Scalar -3.734 vs doc's
-1.4104: the difference is entirely the D-2 floor (6.4% outage user-steps).
NOTE: the local TLE archive fails `validate_server_setup` (archive/file_set/split
differ from the frozen record); all pilot evals therefore run on sat, and sat's
numbers are not expected to equal local ones.
