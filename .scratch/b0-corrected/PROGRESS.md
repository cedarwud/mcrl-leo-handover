# B0CORRECT progress

Started 2026-09-11. Every step checks for existing output first; an interruption
resumes at the first incomplete step.

## Step ledger

| # | Step | State | Output to check |
|---|------|-------|-----------------|
| 0 | Locate the three defect sites | DONE | this file |
| 1 | D-1 test (fails first) | PENDING | `tests/test_b0_d1_scalarised_bootstrap.py` |
| 2 | D-1 fix + commit | PENDING | git log grep `B0 D-1` |
| 3 | D-2 test (fails first) | PENDING | `tests/test_b0_d2_outage_floor.py` |
| 4 | D-2 fix + commit | PENDING | git log grep `B0 D-2` |
| 5 | D-3 test (fails first) | PENDING | `tests/test_b0_d3_calibrated_scalar_log.py` |
| 6 | D-3 fix + commit | PENDING | git log grep `B0 D-3` |
| 7 | Full-ish regression sweep of touched modules | PENDING | pytest output in this dir |
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
