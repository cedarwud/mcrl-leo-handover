# B0CORRECT progress

Started 2026-09-11. Every step checks for existing output first; an interruption
resumes at the first incomplete step.

## Step ledger

| # | Step | State | Output to check |
|---|------|-------|-----------------|
| 0 | Locate the three defect sites | DONE | this file |
| 1 | D-1 test (fails first) | DONE — 3/4 red pre-fix | `tests/test_b0_d1_scalarised_bootstrap.py` |
| 2 | D-1 fix + commit | DONE `5219995a` | git log grep `B0 D-1` |
| 3 | D-2 test (fails first) | DONE — 2/7 red pre-fix, on substance | `tests/test_b0_d2_outage_floor.py` |
| 4 | D-2 fix + commit | DONE `832471ca` | git log grep `B0 D-2` |
| 5 | D-3 test (fails first) | DONE — 5/6 red pre-fix | `tests/test_b0_d3_calibrated_scalar_log.py` |
| 6 | D-3 fix + commit | DONE `0acd146c` | git log grep `B0 D-3` |
| 7 | Full regression sweep | DONE — 55 fail, IDENTICAL IDs to pre-D-1 baseline `e3f3503e` | pytest output in this dir |
| 8 | Sync to `sat:/home/sat/mcrl-v025-b0-ws` | PENDING | remote dir + git init |
| 9 | Launch 500-episode pilot detached | PENDING | remote log path (recorded below) |
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
