# H4PROBE — PROGRESS

Task: does the energy head of the pilot's ratio learner (CF3PILOT, commit `102b2d4d`, branch
`cf3/pilot-20260911`) ever change a decision, and where does an explicit own-bits rule sit.
Measurement only, no training. Report target: `.scratch/h4-probe/H4-PROBE-2026-09-11.md`.

Governing docs read: `.scratch/cf3-pilot/TAKEOVER.md`, `.scratch/cf3-pilot/DECLARATION-ADDENDUM.md`,
`.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`, `.scratch/curation/PROVENANCE-HEADER.md`, plus in the
pilot worktree (`/home/u24/papers/mcrl-leo-handover-cf3`, commit `102b2d4d`): `scripts/cf3_eval.py`,
`scripts/cf3_common.py`, `scripts/cf3_premeasure.py`, `src/mcrl/algorithms/cf_ratio.py`,
`src/mcrl/algorithms/cf_sources.py`, `src/mcrl/runtime/state_encoding.py`.

Noted: `.scratch/AGENT-REGISTRY.md` lists a prior `H4PROBE` dispatch (agentId `a721c0c4171804491`,
13:15 UTC) with the same deliverable, but `.scratch/h4-probe/` did not exist on disk when this
session started (checked first) — so there is no PROGRESS to resume from; treating this as that
work's first actual execution.

## Design decisions locked before any measurement (write here BEFORE running anything)

- **eta vs lambda knobs**: `CFRatioTrainer.combined_q_values(enc, lam=...)` exposes `lam` as a
  parameter but not `eta` (fixed to `self.eta` via the `eta_tilde` property). To vary eta at
  inference time we mutate `tr.eta` immediately before each `tr.greedy_actions(...)` call and
  restore/reset it explicitly on the next call — this is safe because `eta_tilde` is a `@property`
  read fresh every call, `greedy_actions` consumes no RNG, and we never call `save_policy`/anything
  that persists the mutated value.
- **(i) and (iv) are counted on the DEPLOYED trajectory**: actions that actually step the env come
  from `tr.greedy_actions(enc, masks, lam=0.0)` at `tr.eta = eta_deployed` (matches `tr.lam == 0`
  for all A1-A3 per Amendment 2, asserted, not assumed). At every decision we ALSO compute the
  counterfactual `tr.greedy_actions` at `(eta=0, lam=0)` [-> flip fraction for (i)] and at
  `(eta=eta_deployed, lam=1)` [-> flip fraction for (iv)], using the SAME `tr.greedy_actions`
  function throughout (never mixing in `cf3_common.masked_argmax`) so a "flip" can never be a
  tie-break implementation artifact. "Decision" = user-step with `masks[u].mask.any()`, matching
  `cf3_eval.py`'s own `cf_policy` counting convention exactly.
- **(ii)/(iii) closed-loop rollouts** actually re-simulate with the modified eta as the real behaviour
  policy (`tr.eta` mutated for the whole rollout, `lam` fixed 0), so divergent actions compound
  through the trajectory — a separate `pooled_rollout` call per variant, same eval seeds.
  "Deployed" baseline for the vs.-comparison is read from the pilot's own read-only
  `eval/<ARM><seed>.json` (validated bit-for-bit by mandatory placebo (b) for A1s0, and
  additionally cross-checked per-checkpoint against my own from-scratch deployed rollout for all
  9 checkpoints, as a bonus check beyond the mandatory placebo).
- **Own-bits rule** reads `UserState.channel_quality` and `UserState.beam_loads` directly (the raw
  fields `cf_sources.py`'s own rules read), NOT the log1p/normalised values `state_encoding.py`
  bakes into the 112-dim NN input:
  - `gamma_a = channel_quality[a]` (raw nominal SINR/gain; `state_encoding.encode_state` applies
    `log1p` only when building the NN's block-2 input — this rule bypasses that, exactly like
    `cf_sources.make_rule`'s `gain = np.asarray(s.channel_quality, ...)`).
  - `load_a = beam_loads[a]` (raw previous-step user COUNT on beam `a`; `state_encoding.encode_state`
    divides by `num_users` only when building the NN's block-4 input — this rule does not divide,
    exactly like `cf_sources.r_no_new_beam`'s `load = np.asarray(s.beam_loads, ...)`), matching the
    task's own wording "previous-step user count."
  - Negative `channel_quality` (if any occur) is floored at 0 before `log2(1+gamma)`, mirroring
    `state_encoding.py`'s own `np.maximum(snr, 0.0)` precedent before its `log1p`. Observed
    min/max of `channel_quality`/`beam_loads` over the actual rollouts will be logged and reported
    (so the floor's activation, if any, is documented rather than assumed).
  - Ties broken by first index (`np.argmax`), matching the project-wide "masked argmax, first index
    on ties" convention.
- **Per-served-user rate mean** (own-bits rule only, per the task) is NOT derivable bit-exactly from
  `pooled_rollout`'s returned aggregates without assuming `system_throughput_bps` decomposes exactly
  into `sum(rewards[u].r1_throughput for u served)` (an assumption we will not silently make — see
  `imported-diagnostics-flip-direction` / `near-tautological-results` lessons). Instead a small
  rollout-loop EXTENSION (`pooled_rollout_with_user_rate` in `h4_ownbits.py`) duplicates
  `cf_ratio.pooled_rollout`'s loop verbatim and additionally accumulates
  `result.rewards[uid].r1_throughput` over steps where `result.served[uid]` is true — same fields
  `cf_reward_matrix` already reads, no new physics. Its shared fields (ee/bits/joules/h_inter/
  h_intra/served/beams) are cross-checked bit-for-bit against `cfr.pooled_rollout` itself (via the
  calibration.json comparison for MAX_NOMINAL_GAIN and C1_A_m2dB on calibration seeds) before its
  own-bits numbers are trusted.

## Steps (idempotent — check output exists before recomputing)

- [x] 0. Server precheck (workspace absent, no stray h4 processes, confirm run/eval paths, sha256 of
      calibration.json 59952214…562d matches DECLARATION-ADDENDUM, TLE dir present, python 3.13.3,
      load 3.74/20 cores — low, no other job to worry about besides CEILING2's separate ws).
- [x] 1. Stage server workspace `/home/sat/mcrl-v025-h4-probe-ws/{tree,scripts,results,logs}`;
      `git archive 102b2d4d` of `src scripts tests` untarred into `tree/`; verified sha256 of
      `cf_ratio.py`/`cf_sources.py`/`state_encoding.py`/`cf3_eval.py`/`cf3_common.py`/
      `cf3_premeasure.py` identical between local worktree and staged tree.
  - **Gap found and fixed**: `cf3_premeasure.py`/`cf3_eval.py` call
    `training_pipeline.assert_tle_archive_pinned()`, which reads
    `REPO/artifacts/PREREG-FROZEN-2026-08-25-R2.json` (`REPO` = tree root, `parents[3]` from
    `training_pipeline.py`) to get the pinned TLE file_set_sha256 to check against — this file is
    NOT under `src scripts tests` so the literal archive command in the task omits it (the full
    `artifacts/` dir is 749 MB, not something to stage wholesale). Fix: staged ONLY that one 133 KB
    file at `tree/artifacts/PREREG-FROZEN-2026-08-25-R2.json`, sha256
    `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`, verified identical both
    ends. `TRAINED_CKPT` (`artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`) is
    NOT needed (only used for `--arm TRAINED`, which this probe never runs) and was not staged.
- [x] 2. Write + copy scripts (`h4_sensitivity.py`, `h4_ownbits.py`); sha256 verified both ends
      (`cc934b7f…3057` / `701c85d2…0ff73`); `py_compile` OK on sat's venv.
- [x] 3. Placebo (a) **PASSED bit-for-bit**: `cf3_premeasure.py --arm RANDOM_MASKED --out
      results/placebo-premeasure` (unmodified, staged tree) on the 24 calibration seeds gave
      `ee = 51866475.48532767` bit/J — exact match to the declared target
      `51,866,475.48532767` bit/J. Wall ~41 s. Log `logs/placebo-a-random-masked.log`, output
      `results/placebo-premeasure/RANDOM_MASKED.json`.
- [x] 4. Placebo (b) **PASSED bit-for-bit**: `cf3_eval.py --label A1s0 --checkpoint
      /home/sat/mcrl-v025-cf3-pilot-ws/runs/A1-OFF-s0/policy-ep01000.pt --kind cf --repeat --out
      results/placebo-eval/A1s0.json` (unmodified, staged tree). Compared against the read-only
      `/home/sat/mcrl-v025-cf3-pilot-ws/eval/A1s0.json`: ee/bits/joules/h_inter/h_intra/served/
      beams/user_steps all bit-identical, full per-episode `episodes` list bit-identical,
      `checkpoint_sha256` identical, own determinism placebo (`--repeat`) True. Log
      `logs/placebo-b-a1s0.log`.
      **Both placebos pass — proceeding to the main measurement per the task's gate.**
- [x] 5. Main measurement **COMPLETE**: all 9 checkpoints (A1/A2/A3 x s0-2), 3 concurrent detached
      processes (one per arm, 3 seeds each sequentially), all finished ~13:27:43 UTC, all 9/9
      cross-checks against the pilot's read-only eval JSON PASSED bit-for-bit
      (`any_cross_check_failed=False` for all 3 arms). Argmax-flip fraction (eta->0) range across
      the 9 checkpoints: **11.02% - 42.15%** (mean 24.56%); (lambda->1, report-only): 44.22% -
      62.39% (mean 55.29%). Closed-loop relative EE change (eta->0): -8.089% to +3.067% (mean
      -1.460%); (eta doubled): -15.920% to +1.078% (mean -4.919%). Full per-checkpoint numbers in
      `results/A{1,2,3}s{0,1,2}-h4sensitivity.json` and in the report.
- [x] 6. Own-bits rule + MAX_NOMINAL_GAIN + C1_A_m2dB (="A m=2dB") on both calibration and
      evaluation episode sets **COMPLETE** (ran first, ~13:17-13:20 UTC, single process, 6
      rollouts). Cross-check of the two references against `calibration.json` **PASSED
      bit-for-bit** on all 7 shared fields, both rules. Own-bits diagnostics: n_gain_negative=0,
      min_gain=0.0 on both sets (the floor-at-0 never activated on this data) -- see report §3.
      Own-bits sits BELOW both references and below A1/A2/A3 on both episode sets, above only A0
      -- see report §4.
- [x] 7. Pulled all results back to local `.scratch/h4-probe/results/`; spot-verified sha256 of one
      file matches the remote copy exactly.
- [x] 8. Wrote `.scratch/h4-probe/H4-PROBE-2026-09-11.md` with provenance header ([A] this probe's
      own measurements, [P] numbers quoted verbatim from the pilot report for A0 only), per-
      checkpoint tables (flip fractions, closed-loop full stats, own-bits+references, same-
      episode-set ranking tables), first-line summary, validity-checks table, scope/caveats. Caught
      and fixed during review: (i) two aggregate cells that mixed "ratio of means" with "mean of
      ratios" conventions (now consistently mean-of-ratios, matching the "all 9 mean" rows); (ii) an
      out-of-order ranking row in the evaluation-episodes table (A2/A3/MAX_NOMINAL_GAIN were not
      actually in ascending EE order); (iii) an arithmetic-labelling slip in the own-bits gain-
      diagnostics paragraph (672,000 observations is PER episode set, not combined total); (iv) six
      `ho/user-min` cells off by ~0.001 from hand-rounding instead of using the precise stored
      values. All four fixed; every number in the final file was either pasted verbatim from a
      script's own stdout/JSON or recomputed by a script and checked, not hand-derived.
- [x] 9. This file is the final PROGRESS update. Total wall time, server workspace staged
      (13:05:20 UTC) through last sensitivity result written (13:27:43 UTC): **~22.4 minutes** of
      on-server measurement wall time (placebos + own-bits/references + 9-checkpoint sensitivity,
      including the ~4 min ssh-channel-closing quirk on the first launch, which did not block the
      remote work). Report drafting/review after that added additional (non-compute) session time.
      No detached process is still running; nothing left to resume.

## FINAL STATUS: DONE. No open steps. No live processes on `sat` belonging to this probe.

First line of the report (verbatim):

> **Across the 9 final A1/A2/A3 checkpoints, the deployed rule's η→0 counterfactual flips
> 11.0–42.2% of decisions relative to the deployed action (mean 24.6%; a second, report-only
> counterfactual at λ→1 flips 44.2–62.4%), yet the resulting closed-loop pooled-EE change stays
> within −8.1% to +3.1% (mean −1.5%) with no consistent sign across arms; the explicit own-bits
> rule scores *below* both `A m=2dB` and every ratio-learner arm (A1/A2/A3) on both episode sets,
> though above the A0 MODQN baseline on both.**

## Process orchestration plan (respect <= 3 concurrent processes on sat)

Batch 1 (1 process): `h4_ownbits.py` — own-bits rule + MAX_NOMINAL_GAIN + C1_A_m2dB on both
episode sets (6 rollouts, no NN, cheap). Wait for completion before Batch 2.

Batch 2 (3 processes concurrent): `h4_sensitivity.py --arm A1|A2|A3` — each handles its own 3
seeds sequentially internally (9 checkpoints total / 3 processes = 3 each). Each checkpoint does 3
rollouts of 24 episodes (deployed+counts, eta->0 closed loop, eta-doubled closed loop).

## Detached processes (fill in PID / cwd / cmdline / output / expected finish as launched)

All on `sat`, all `setsid nohup nice -n 16 … </dev/null > log 2>&1 &`, `OMP_NUM_THREADS=1`, `torch.set_num_threads(1)` inside each script, `MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91`.

1. **Batch 1 (own-bits + references) — COMPLETED 13:20 UTC.** PID 3462301 (wrapper 3462300, already
   exited). cwd `/home/sat/mcrl-v025-h4-probe-ws/tree`. cmdline
   `/home/sat/mcrl-leo-handover/.venv/bin/python /home/sat/mcrl-v025-h4-probe-ws/scripts/h4_ownbits.py
   --results-dir /home/sat/mcrl-v025-h4-probe-ws/results`. Output log
   `/home/sat/mcrl-v025-h4-probe-ws/logs/ownbits.log`; result JSONs
   `results/{OWN_BITS,MAX_NOMINAL_GAIN,C1_A_m2dB}-{calibration,evaluation}-h4ownbits.json` +
   `results/calibration_cross_check.json`. Finished in ~4 min wall (6 rollouts x ~35-41s). Exit
   status 0, `any_cross_check_failed=False`. (Note: the ssh *wrapper* shell that launched it took
   an unexplained ~4 min to itself return control locally even though the log showed the actual
   python job progressing normally throughout and finishing quickly — a local ssh-channel-closing
   quirk, not a remote problem; the remote job was always correctly detached. Switched to
   `run_in_background: true` on the Bash tool for subsequent launches to avoid blocking on it.)
2. **Batch 2 (per-arm sensitivity), launched ~13:21 UTC, RUNNING.** 3 processes, one per arm, each
   looping its 3 seeds internally (idempotent per-seed — checks `<label>-h4sensitivity.json` first).
   - **A1**: PID 3464694 (wrapper 3464693). cwd `/home/sat/mcrl-v025-h4-probe-ws/tree`. cmdline
     `.../python scripts/h4_sensitivity.py --arm A1 --results-dir /home/sat/mcrl-v025-h4-probe-ws/results`.
     Output `logs/sensitivity-A1.log`; results `results/A1s{0,1,2}-h4sensitivity.json`.
   - **A2**: PID 3464747 (wrapper 3464746). Same cwd/pattern, `--arm A2`. Output
     `logs/sensitivity-A2.log`; results `results/A2s{0,1,2}-h4sensitivity.json`.
   - **A3**: PID 3464800 (wrapper 3464799). Same cwd/pattern, `--arm A3`. Output
     `logs/sensitivity-A3.log`; results `results/A3s{0,1,2}-h4sensitivity.json`.
   - Expected finish: each checkpoint runs 3 rollouts of 24 episodes (~35-40s each per the own-bits
     timings above) plus checkpoint-load overhead => roughly 2-3 min/checkpoint x 3 seeds/arm =>
     ballpark 6-10 min per arm process; all 3 run concurrently (= 3 processes, within the <=3
     limit), so expected wall clock to all-done is ~10-15 min from launch (~13:21 UTC), i.e. done
     by roughly 13:35 UTC. Poll via `pgrep -af h4_sensitivity.py` and the three log files; each
     process prints `DONE arm=... any_cross_check_failed=...` on completion and exits
     0 (pass) / 1 (a checkpoint's deployed rollout failed to bit-match the pilot's read-only eval
     JSON — would need investigation, not expected).
   - **Interim (13:26 UTC): 3/9 done (A1s0, A2s0, A3s0), all bit-for-bit cross-check against the
     pilot's read-only eval JSON PASSED for all three** (measured independently through the
     3x-scoring `combined_policy` path, not just the simpler placebo path — an extra validity check
     beyond the mandated placebo). Observed so far (deployed vs eta->0, on THIS agent's own
     from-scratch rollouts, evaluation episode set): A1s0 flip_eta0=0.1914, flip_lam1=0.6181,
     eta0 relative EE change=-0.00098, eta2x=-0.01639; A2s0 flip_eta0=0.2018, flip_lam1=0.4422,
     eta0 relative EE change=+0.03067, eta2x=-0.15920; A3s0 flip_eta0=0.3011, flip_lam1=0.5048,
     eta0 relative EE change=-0.05287, eta2x=+0.01078. All 3 processes still running (seed 1/2 in
     progress), 99.9% CPU each, no errors. **These are interim single-seed numbers, not the final
     9-checkpoint range — do not cite until all 9 are in.**
   - **Own-bits vs references, both episode sets (from Batch 1, already final):**
     calibration: OWN_BITS ee=98,699,868.60, MAX_NOMINAL_GAIN ee=110,507,234.83,
     C1_A_m2dB("A m=2dB") ee=112,195,917.54; evaluation: OWN_BITS ee=93,755,623.19,
     MAX_NOMINAL_GAIN ee=104,673,598.35, C1_A_m2dB ee=107,000,983.53. On BOTH episode sets
     (never mixed), OWN_BITS < MAX_NOMINAL_GAIN < C1_A_m2dB, and (comparing against the
     CF3-PILOT report's own arm numbers on the SAME respective episode set) OWN_BITS sits above
     A0 (BASELINE MODQN: 84.21 M eval / ~86.37 M cal) but below all three ratio-learner arms
     A1/A2/A3 (~98.6-106.2 M) on both sets.

## Log

- (timestamp pending) Session start; read governing docs; read `cf3_eval.py`, `cf3_common.py`,
  `cf3_premeasure.py`, `cf_ratio.py`, `cf_sources.py`, `state_encoding.py`. Confirmed
  `.scratch/h4-probe/` did not exist yet (fresh start). Created directory skeleton + this file.
