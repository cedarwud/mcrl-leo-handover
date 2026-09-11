# Task file — finish the LP probe, then the realised-information oracle cells (A-real ×2 references, B-real, order sensitivity)

Written 2026-09-11 ~14:50 UTC by the controller for a fresh agent taking over from the sonnet agent that hit a weekly API
limit mid-task. Everything below is measurement only: **no training, no change to any trained weight, no new arm.**
Keep `/home/u24/papers/mcrl-leo-handover/.scratch/h4-probe/PROGRESS.md` updated after every step (new heading
"TAKEOVER 2 — LP finish + oracle cells"; detached PIDs with cwd/cmdline/output/expected finish; steps idempotent).

## 0. Where things are (verified read-only at 14:38 UTC)

- Harness: the previous agent's workspace `sat:/home/sat/mcrl-v025-h4-probe-ws/` (`tree/` = pilot worktree commit `102b2d4d`
  `src scripts tests`; `scripts/h4_sensitivity.py`, `h4_ownbits.py`, `lp_grid.py`; `results/`, `results-lp/`, `logs/`), local
  mirror `.scratch/h4-probe/` (scripts, results, `H4-PROBE-2026-09-11.md`). Read `PROGRESS.md` first: it records the
  placebo-tied rollout machinery (`pooled_rollout_with_user_rate`), the rule pattern, and the LP grid's declared reading.
- The LP grid: 4 detached `lp_grid.py` processes (PIDs 3482477, 3482530, 3482583, 3482636) were writing cells into
  `sat:…/results-lp/` (35 of 96 at 14:38 UTC). Check whether they are still alive (by cwd + cmdline) or finished; **never
  relaunch a live or finished cell**; if some cells are missing after the processes exit, run only the missing ones.
- Pinned archive `MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91` (assert sha256 `427e6a91…8fe9`);
  python `/home/sat/mcrl-leo-handover/.venv/bin/python` (read-only); `sys.path.insert(0, "<tree>/src")` first.
- Server rules: ≤ 4 processes for you (the ceiling agent runs many; do not touch `/home/sat/mcrl-v025-ceiling-ws/`),
  `nice -n 16`, 1 BLAS thread, < 5 GB each, detached with `setsid nohup … </dev/null > log 2>&1 &`, intermediates under your
  workspace never `/tmp`, exact-PID kills only after checking `/proc/<pid>/cmdline` and cwd. Copy files with
  `ssh sat 'bash -s'` heredocs or `cat f | ssh sat 'cat > path'` and verify sha256 both ends.
- Do not read `.scratch/validity-audit/`, `.scratch/ee-ceiling/`, `.scratch/reviews/`. Rules are diagnostics and candidate
  sources, never a success gate (owner: success = beat baseline MODQN only).

## 1. Finish the LP probe (spec restated; the previous agent's PROGRESS.md has its own declared reading — keep it)

Family **LP(c, m)**: score(a) = log2(1+γ_a) − c·[N_a == 0] with the `A m` hysteresis hold at m dB; γ_a = raw block-2 nominal
SINR, N_a = raw block-4 previous-step user count (LP-prev, simultaneous) or the count of users already assigned to a this
step in fixed order 0..99 (LP-seq, sequential). Grid c ∈ {0, 1, 2, 3, 4.2, 6, 8, 12} × m ∈ {0, 2, 6} dB, both variants, both
episode sets (evaluation env 9_111_000+i / mobility 9_112_000+i; calibration 9_121_000+i / 9_122_000+i; i = 0..23; fresh env
per episode; greedy; masked argmax first index on ties). In-family placebos: LP-prev(0,0) = `MAX_NOMINAL_GAIN` and
LP-prev(0,2) = `C1_A_m2dB` bit-for-bit on the calibration set (`sat:/home/sat/mcrl-v025-cf3-pilot-ws/premeasure/calibration.json`,
read-only). Per cell: pooled EE (bits, joules), lit beams, served, H_inter, H_intra, handovers per user-minute, per-served-
user rate mean / p10 / min, wall.

Declared reading (already in PROGRESS.md; restated): reference `C1_A_m2dB` on the same set, paired per-episode sem.
(i) best LP-prev ≥ +3.3 % with served ≥ 0.995 → a simultaneous per-user rule already pulls the lever; (ii) only LP-seq does →
the lever needs current-step visibility; (iii) neither → per-user one-step information is insufficient. Flag cells with
p10 < 50 % of the rule's p10 on the same set as throughput-degenerate. Report the **whole grid**, both sets, never mixed.

Write `.scratch/h4-probe/LP-PROBE-2026-09-11.md`: first line = one bold sentence with the best LP-prev and LP-seq cells
(c, m, pooled EE, % vs `A m=2dB`, served, p10) on the evaluation set and which of (i)/(ii)/(iii) holds; provenance header
(as in `H4-PROBE-2026-09-11.md`); grids as tables; JSON in `results-lp/` copied back with sha256 verification.

## 2. The realised-information oracle cells (`V025-CONTROLLER-AMENDMENT-1-ORACLE-FIRST-SCREEN-2026-09-11.md` §2, plus the
##    owner's additions of 14:45 UTC — read that amendment first; its §3 rules are the declared reading)

Objective at a step: `F(joint) = bits − η·joules`, both from the environment's counterfactual evaluator
(`StepEnvironment.evaluate_actions(actions, rng)`, common random numbers, no state committed; see `src/mcrl/env/step.py`
~643-723 and the pattern in `scripts/cf3_de_diag.py`). **Parity check built in**: for every committed step record
max |Δ| between the evaluator's bits/joules for the chosen joint action and the committed step's actual bits/joules; if it
is not ~0 (float tolerance), stop and report that first.

- **Reference actions (two, per the owner)**: R1 = `A m=2dB`'s joint action at the step; R2 = `B1_NO_NEW_BEAM`'s joint
  action at the step (both from `cf_sources.py` rules on the current observation). η = the reference action's own step
  bits / step joules (evaluated once).
- **A-real(R)** — simultaneous best response: for every user u and every legal a, compute
  `F(R_{−u}, a) − F(R_{−u}, R_u)` with the others fixed at R; each user moves to its argmax **simultaneously** (a move that
  would unserve a served user is disallowed; ties keep R_u); commit the resulting joint action; step; continue. Run for
  R1 and R2.
- **B-real(R)** — one sequential sweep: users 0..99 in order, user k best-responds to R updated by users < k's choices
  this step; commit after the sweep. Run for R1 (primary) and R2; on evaluation episodes 0–5 also the reverse order 99..0
  (order sensitivity) for R1.
- Both cells on the 24 evaluation episodes (primary) and the 24 calibration episodes (tie-in). Per step record bits,
  joules, served, lit beams, per-served-user rate mean/p10/min, evaluations used, wall; per episode the pooled values.
  Cost guide: one user sweep ≈ 2,700 evaluations ≈ 20 s warm (the ceiling agent measured 7.5 ms per evaluation); A-real
  needs the same count; ≈ 200 s per episode per cell → 24 episodes on 4 processes ≈ 20 min per cell; 6 cells ≈ 2 h.
  Order: A-real(R1), B-real(R1), A-real(R2), B-real(R2), order-sensitivity, then calibration tie-ins.

Report `.scratch/h4-probe/ORACLE-CELLS-2026-09-11.md`: first line = A-real(R1), B-real(R1) pooled EE on the evaluation
set, % vs `A m=2dB` (paired sem), served, p10, parity max |Δ|, the R2 values, and which of the amendment's rules 1–4 the
cells satisfy; provenance header; both episode sets named on every table, never compared; every number with its
conditions. Return the first lines of both reports.
