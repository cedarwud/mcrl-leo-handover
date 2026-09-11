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

## H4 PROBE FINAL STATUS: DONE. No open steps. No live processes on `sat` belonging to this probe.

---

# LP PROBE (new task from coordinator, received while H4 probe report was being returned)

Reuses: `sat` workspace `/home/sat/mcrl-v025-h4-probe-ws/` (same staged tree, commit `102b2d4d`),
the same placebo-tied rollout machinery, and the `cf_sources.py`-style rule pattern. No training.
Resource budget now: **<= 4 processes** (coordinator says sat is idle now), `nice -n 16`, 1 thread,
< 5 GB each. Results in `.scratch/h4-probe/results-lp/`. Report:
`.scratch/h4-probe/LP-PROBE-2026-09-11.md`. Forbidden reading (unchanged): `.scratch/validity-audit/`,
`.scratch/ee-ceiling/`.

## Physics motivation (as given by coordinator, not re-derived here)

Joules ~ constant per lit beam => pooled EE ~ bits per lit beam. Per-user unilateral score:
`score(a) = log2(1+gamma_a) - c*[N_a==0]`, `c = eta*P_beam/B_w ~ 4.2 bit/s/Hz`. `c=0` <-> `MAX_NOMINAL_GAIN`;
`c -> inf` <-> `B1_NO_NEW_BEAM`. Adding the `A m` hysteresis hold (dB margin, on GAIN not on the
LP score, exactly as `cf_sources.pick()` structures it: rank candidates by the family's own
selection criterion, but gate the incumbent-vs-challenger SWITCH by comparing raw gain with the
multiplicative `10^(m/10)` threshold) gives the two-parameter family LP(c, m).

## CRITICAL implementation finding (investigated before writing any code)

Candidate slot index `a` (0..27) is **per-user**: `src/mcrl/env/candidates.py`'s own docstring —
"Windows are per user... Two users 100 km apart... can order the same satellites differently, and a
shared window would silently give some of them somebody else's four." So for LP-seq ("N_a counts
users already assigned to beam a in this step"), a plain `UserState`-only `SourcePolicy` (the H4
own-bits pattern) CANNOT tell whether two different users' candidate slots refer to the same
physical beam — `UserState` never exposes a beam identity, only per-candidate `channel_quality`/
`beam_loads` values the environment has ALREADY correctly aggregated per physical beam internally.

Traced the real key: `src/mcrl/env/step.py` `_observe()` builds block 4 exactly as
`loads[uid, action] = self._previous_demand.get((norad, cell), 0)` where `norad =
norad_ids[uid, action]`, `cell = cell_ids[uid, action]` — i.e. the physical beam key IS
`(norad_id, cell_id)`, read per (user, candidate) from `StepCandidates.slot_tables[uid].norad_ids /
.cell_ids` (length-28 arrays; `action_contract.SlotTable` asserts `mask => norad_ids>=0 and
cell_ids>=0`, so every LEGAL candidate has a valid key, no defensive fallback needed).

This table is NOT reachable from `UserState`/`ActionMask` alone, but IS reachable, by design, at the
`TrainerEnvironment` seam: `env.reset(...)` returns `(states, masks, observation)` and its own
docstring says why — "a probe or a run logger wants the candidate table... returning the object
costs nothing"; after a step, `env.last_outcome.observation.candidates` gives the same for the next
decision. LP-seq's rollout therefore is NOT a plain `(states,masks)->actions` `SourcePolicy`; it is a
custom loop (`pooled_rollout_lp_seq` in `lp_common.py`) that additionally reads
`observation.candidates.slot_tables[u].norad_ids/.cell_ids` to build a step-local
`{(norad,cell): count}` tracker as it decides users 0..99 in order, then steps the env ONCE with the
completed joint action vector. `gamma_a` is untouched (still each user's own unchanged
`channel_quality` from the observation, per the task). No RNG is consumed by this bookkeeping. This
is disclosed prominently in the report, not left implicit.

## Design decisions locked before any counted run

- **LP-prev(c, m) rule** (simultaneous, plain `SourcePolicy`, patterned exactly on
  `cf_sources.make_rule`/`pick`): `ok = legal` (no restrict-set — the c-penalty applies continuously
  to every legal candidate, unlike B1's hard restriction); `gain_floor = max(channel_quality, 0)`
  (mirrors `state_encoding.py`'s precedent; H4 probe's own diagnostics already showed
  `n_gain_negative=0` on both episode sets, so this is provably inert here, not just assumed);
  `score = log2(1+gain_floor) - c*(beam_loads==0)`; `best = argmax(score[ok])` (first index on ties);
  hysteresis EXACTLY as `cf_sources.pick()`: `m<=0 => best`; else if incumbent legal:
  `gain[best] > gain[inc]*10**(m/10) => best else inc`; else `best`. Reuses
  `cf_sources.incumbent_slot` directly.
- **Mandatory internal placebos** (must both pass before the grid counts): LP-prev(c=0,m=0) must
  reproduce `MAX_NOMINAL_GAIN` bit-for-bit, and LP-prev(c=0,m=2) must reproduce `C1_A_m2dB`
  bit-for-bit, both on calibration seeds, checked against `calibration.json`. At c=0 the penalty
  term is always 0, so `score` is a monotonic transform of `gain_floor`, so
  `argmax(score)==argmax(gain_floor)==argmax(gain)` given no negative gains exist; at m=0 the
  hysteresis block is skipped entirely (matches `MAX_NOMINAL_GAIN` having none); at m=2 the
  hysteresis block is structurally IDENTICAL to `make_rule(margin_db=2.0)` with `allowed=None`.
  Run these two cells FIRST, standalone, before launching the full grid — if either fails, STOP per
  the task's explicit instruction (do not launch the grid; report the failure instead).
- **LP-seq(c, m)**: see "critical implementation finding" above. N_a is reset to empty at the START
  of every step (not seeded from last step's `beam_loads` — the task's wording "not yet chosen this
  step by an earlier user" is about THIS step only), and incremented for whichever physical beam key
  each user ends up on (post-hysteresis, since a held incumbent still physically occupies its beam
  this step).
- **Per-served-user rate stats** (mean/p10/min, both variants): the FULL list of
  `RewardComponents.r1_throughput` (bit/s) over served user-steps is collected (not just a running
  sum, since percentiles need the distribution), matching the field `cf_reward_matrix` already
  reads. p10 = numpy default (linear-interpolation) 10th percentile.
- **Paired per-episode SEM vs `C1_A_m2dB`**: every cell's rollout also records per-episode
  bits/joules (=> per-episode EE, 24 values), matching `cf_ratio.pooled_rollout`'s own `ee_ep`/
  `episodes` fields. `C1_A_m2dB` is RE-ROLLED (not reused from the H4 probe's own-bits JSONs, which
  lack per-episode/percentile detail) through the SAME instrumented function so every comparison
  uses data produced identically. Per-episode relative difference `(cellee_i - c1ee_i)/c1ee_i`,
  `i=0..23`; SEM = `std(diff, ddof=1)/sqrt(24)`. Never mixes calibration and evaluation episodes.
- **Grid**: `c in {0,1,2,3,4.2,6,8,12}` x `m in {0,2,6} dB` = 24 cells, x2 variants (prev/seq) x2
  episode sets (evaluation primary, calibration tie-in) = 96 rollouts total. All 96 reported, no
  cherry-picking.

## Declared reading (written BEFORE any counted grid run, per the task)

Comparison object: `C1_A_m2dB` ("A m=2dB") on the SAME episode set, paired per-episode SEM (defined
above). On the EVALUATION set (primary):
- **(i)** if the best LP-prev cell exceeds `A m=2dB` by >= +3.3% AND served >= 0.995 =>
  "a deployable simultaneous per-user rule already pulls the lever."
- **(ii)** else if the best LP-seq cell does (same thresholds) =>
  "the lever needs current-step visibility of others' choices (sequential decoding), not a
  coordinator."
- **(iii)** else => "simultaneous/sequential per-user information is insufficient at one-step
  myopia."
- In every case: flag any cell (either variant, either episode set) whose p10 per-user rate is
  below 50% of `A m=2dB`'s p10 **on the same episode set** as throughput-degenerate.
- Rules are diagnostics/candidate sources here, never a success gate (this is DIAGNOSTIC status,
  same as the H4 probe, not a pilot/pass-fail report).

## LP probe steps (idempotent)

- [ ] 0. Server precheck (idle, no stray processes) + `results-lp/` dir.
- [ ] 1. Write + copy `lp_common.py` (shared rule/rollout code) and `lp_grid.py` (CLI driver) to
      `sat:/home/sat/mcrl-v025-h4-probe-ws/scripts/`; sha256 verify both ends.
- [ ] 2. MANDATORY placebo gate: LP-prev(0,0) and LP-prev(0,2) on calibration seeds vs
      `calibration.json`'s `MAX_NOMINAL_GAIN`/`C1_A_m2dB`, bit-for-bit. Stop-and-report if either
      fails.
- [ ] 3. Re-roll `C1_A_m2dB` (enriched: per-episode EE + rate percentiles) on both episode sets, for
      the declared comparison.
- [ ] 4. Full grid: LP-prev x {evaluation, calibration}, LP-seq x {evaluation, calibration} = 4
      batches x 24 cells, <=4 concurrent detached processes.
- [ ] 5. Aggregate: whole-grid tables, best-cell+neighbours, paired SEM vs `C1_A_m2dB`, declared
      reading (i)/(ii)/(iii), throughput-degenerate flags.
- [ ] 6. Write `.scratch/h4-probe/LP-PROBE-2026-09-11.md`.
- [ ] 7. Final PROGRESS update; return first line + wall time.

## Detached processes (LP probe)

All on `sat`, `setsid nohup nice -n 16 ... </dev/null > log 2>&1 &`, `OMP_NUM_THREADS=1`,
`torch.set_num_threads(1)`, `MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91`, cwd
`/home/sat/mcrl-v025-h4-probe-ws/tree`.

1. **Placebo gate — COMPLETED, PASSED.** PID 3480961 (`lp_grid.py --placebo-check --results-dir
   .../results-lp`). Both LP-prev(0,0) vs `MAX_NOMINAL_GAIN` and LP-prev(0,2) vs `C1_A_m2dB` bit-
   for-bit identical on all 7 shared fields (`results-lp/PLACEBO-CHECK.json`, `ok: true`). Wall
   ~90s. **Grid proceeds.**
2. **Full grid, launched right after the gate passed, 4 concurrent processes (<=4 limit):**
   - PID 3482477: `--variant prev --episode-set evaluation --grid`. Log
     `logs/lp-prev-evaluation.log`. 24 cells -> `results-lp/LP-prev-evaluation-c*-m*.json`.
   - PID 3482530: `--variant prev --episode-set calibration --grid`. Log
     `logs/lp-prev-calibration.log`. 24 cells (2 already done by the placebo gate, idempotent
     skip) -> `results-lp/LP-prev-calibration-c*-m*.json`.
   - PID 3482583: `--variant seq --episode-set evaluation --grid`. Log
     `logs/lp-seq-evaluation.log`. 24 cells -> `results-lp/LP-seq-evaluation-c*-m*.json`.
   - PID 3482636: `--variant seq --episode-set calibration --grid`. Log
     `logs/lp-seq-calibration.log`. 24 cells -> `results-lp/LP-seq-calibration-c*-m*.json`.
   - Expected finish: ~24 cells x ~40-50s/cell (LP-seq's per-user Python loop adds some overhead
     over LP-prev's vectorised-ish loop, so budgeting a bit more) ~= 16-20 min per process, all
     concurrent -> done roughly 20-25 min after launch (~14:40-14:45 UTC; launched ~14:20 UTC).
   - Still to run after these finish (only 2 processes, well within the limit, run after so
     concurrency never exceeds 4): `--reference-c1 --episode-set evaluation` and
     `--reference-c1 --episode-set calibration` -> `results-lp/REF-C1_A_m2dB-{evaluation,
     calibration}.json` (enriched: per-episode EE + rate percentiles, needed for the paired-SEM
     comparison; the H4 probe's own-bits-run C1_A_m2dB JSONs lack per-episode/percentile detail).

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

---

# TAKEOVER 2 — LP finish + oracle cells (2026-09-11, from 16:13 UTC)

Fresh agent, took over from the sonnet agent that hit a weekly API limit. Brief:
`.scratch/h4-probe/LP-AND-ORACLE-TASK.md`. Also read
`.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-1-ORACLE-FIRST-SCREEN-2026-09-11.md`.
Measurement only: no training, no weight change, no new arm. <= 4 procs on sat, nice -n 16, 1 BLAS
thread, < 5 GB each, `setsid nohup`, own workspace `/home/sat/mcrl-v025-h4-probe-ws/` only.

## T2-0. State check on takeover (16:13 UTC) — verified, nothing relaunched

- `ps -eo ... | grep lp_grid` on sat: **no live lp_grid process** (the coordinator saw one at 16:12;
  it exited in the interim). Checked by cwd + cmdline, not by name alone.
- `results-lp/` holds 97 files = 96 grid cells (24 cells x {prev,seq} x {evaluation,calibration})
  + `PLACEBO-CHECK.json`. All four grid logs end `DONE variant=... cells=24` at 14:47-14:48 UTC.
  **The whole 8x3 grid is complete for both variants and both episode sets; nothing was relaunched.**
- `PLACEBO-CHECK.json` `ok: true`: LP-prev(0,0) vs `MAX_NOMINAL_GAIN` and LP-prev(0,2) vs
  `C1_A_m2dB` bit-identical on all 7 shared fields (calibration set, vs read-only `calibration.json`).
- Missing: the two enriched `REF-C1_A_m2dB-{evaluation,calibration}.json` reference rolls
  (per-episode EE + rate percentiles) the paired-SEM comparison needs.

## T2-1. Launched the two missing reference rolls (16:14 UTC), detached

Wrapper/python PIDs 3500176 (`--reference-c1 --episode-set evaluation`) and 3500177
(`--reference-c1 --episode-set calibration`); cwd `/home/sat/mcrl-v025-h4-probe-ws/tree`; cmdline
`.../python /home/sat/mcrl-v025-h4-probe-ws/scripts/lp_grid.py --reference-c1 --episode-set <tag>
--results-dir /home/sat/mcrl-v025-h4-probe-ws/results-lp`; logs `logs/lp-ref-<tag>.log`; outputs
`results-lp/REF-C1_A_m2dB-<tag>.json`. Expected finish ~40-45 s each (single rollout of 24 episodes).
2 processes, within the <= 4 cap. `--reference-c1` is idempotent (skips if the output exists).

## T2-2. Reference rolls DONE (16:14 UTC)

`REF-C1_A_m2dB-evaluation.json` ee=107,000,983.53 served=0.99862 p10=1.014e+08 (wall 40.7 s);
`REF-C1_A_m2dB-calibration.json` ee=112,195,917.54 served=0.99775 p10=1.114e+08 (wall 42.4 s).
Both equal the H4 probe's independently-run `C1_A_m2dB` EE to the cent on the same set, and the
calibration one is the bit-for-bit placebo value from `calibration.json`. No lp_grid process remains.

## T2-3. ORACLE CELLS — design decisions locked BEFORE any counted run

Source read (pilot worktree, commit `102b2d4d`): `src/mcrl/env/step.py` (`evaluate_actions`,
`_evaluate_selected_actions`, `ActionEvaluation`), `src/mcrl/env/action_contract.py`
(`assert_selected_actions_valid`, `NO_OP_ACTION`), `src/mcrl/env/service.py` (`ServiceResolution`),
`src/mcrl/runtime/energy_efficiency.py` (`SystemEnergyEfficiency`), `scripts/cf3_de_diag.py` (the
existing counterfactual-evaluator usage pattern), `scripts/cf3_common.py`, `scripts/lp_common.py`.
Env: 100 users, **10 steps/episode**, DT_S = 30.08 s.

1. **Candidate set for "every legal a"** = `np.flatnonzero(masks[u].mask)`. `NO_OP_ACTION` is NOT a
   candidate: `assert_selected_actions_valid` (SDD §3.7 P-4) accepts a no-op *only* when the user's
   mask is empty. So the oracle structurally cannot switch a user off to save energy — that is the
   action contract's rule, not a choice of mine. Users with an empty mask keep NO_OP; users with
   exactly one legal action have no alternative and cost 0 evaluations.
2. **eta** = the reference action's own step `bits/joules`, from ONE evaluation of R at that step
   (Dinkelbach price at the reference, per the amendment). Consequence stated explicitly rather than
   left implicit: `F(R) = bits_R - eta*joules_R` is **identically 0**, so
   `D_u(a) = F(R_{-u},a) - F(R_{-u},R_u) = F(R_{-u},a)` and "this move improves the objective" is
   exactly the Dinkelbach test "this move raises the step's EE above the reference's EE". Exact, not
   an approximation.
3. **Disallow rule** ("a move that would unserve a served user is disallowed"): candidate `a` is
   rejected iff `any(served_R & ~served(R_{-u},a))` — it unserves ANY user the reference served (the
   mover or a third party via interference/admission). The same rule, always measured against the
   **reference's** served set, is used in A-real and B-real so the constraint cannot drift along a
   sweep. Rejections are counted and reported.
4. **Ties keep the reference action**: the incumbent's F is the initial best, candidates are scanned
   in ascending index order, and a move is taken only on strict `F > F_best` — so "ties keep R_u"
   and "first index on ties" both hold.
5. **B-real F(V) reuse**: after user k moves, `F(V)` for the running vector equals the `F` already
   computed for that exact `alt` vector, so it is carried forward instead of re-evaluated. Exact
   reuse of an evaluation already made, not an approximation (saves ~100 evaluations/step).
6. **Parity check (built in, read first)**: at every committed step the chosen joint action is
   evaluated once more with `evaluate_actions` immediately BEFORE `env.step` (which advances the
   rng), and |Δbits|, |Δjoules| against the committed `env.last_outcome.energy` are recorded.
   Per-episode and global max |Δ| reported; a non-~0 value stops the read.
7. **Pooled statistics are computed by the same accumulators as `lp_common.pooled_rollout_rates`**
   (bits = `system_throughput_bps`*DT_S, joules = `system_consumed_power_w`*DT_S, served from
   `energy.served`, beams from `eff_beams`, handovers from `last_outcome.handovers`, rates from
   `res.rewards[uid].r1_throughput` where `res.served[uid]`), so oracle cells and LP cells are
   comparable because they are measured identically, not because they look similar.
8. **Sharding**: work item = (cell, reference, episode set, order, episode index); one JSON per item;
   4 processes take `index % 4 == shard` from ONE priority-ordered global list, so all four advance
   through the priority order together and an interruption never loses a whole cell. Idempotent:
   an existing output file is skipped, never recomputed.

## T2-4. Oracle smoke (16:18-16:23 UTC) — parity exactly 0; step-0 cost found and diagnosed

Four smoke runs (A/B x R1/R2, evaluation episode 0, 2 steps; output `results-oracle-smoke/`, never a
cell): **parity |Δbits| = |Δjoules| = 0.0 exactly on every step of all four code paths.**
Timing: step t=0 = ~89 ms/evaluation (~240 s/step, 1,503 of 2,702 candidates disallowed); t=1 =
7-9 ms/evaluation (~20 s/step, 0 disallowed) — t>=1 matches the ceiling agent's 7.5 ms guide.
cProfile (`scripts/oracle_profile.py`, diagnostic, writes nothing): at t=0, 4.8 of 5.7 s over 60
evaluations is `StepEnvironment._warm_start_gain` -> `antenna.transmit_gain_linear` -> Bessel
series, ~200 calls per evaluation; it is called ONLY when `_step_index == 0` (segment warm start).

## T2-5. Decision (locked before the counted run): exact memo of `_warm_start_gain` at step 0

Why exact: `_warm_start_gain(uid, association, historical)` reads `_pending_segment_age[uid]` (set
once at reset from `_age_rng`, step.py:536, constant for the episode), `historical` (satellite
positions from `driver.satellite_ecef_at(-age)`, deterministic), the cell centre (fixed) and the
user's position at the current step (fixed within the step). So within one step it is a pure
function of `(uid, norad_id, cell_id)`; the memo key is `(step_index, uid, norad_id, cell_id, age)`
and stores `None` returns too. Without it the run is ~4.5 h wall on 4 processes; with it ~2.4 h.
Verification is strengthened, not relaxed:
- the **committed `env.step` always runs with the memo OFF** (pristine code path), so the per-step
  parity check compares memo-evaluator vs pristine commit on every committed step;
- at **every step 0**, the reference evaluation and the first 20 candidate evaluations are repeated
  with the memo OFF and compared bitwise (bits, joules, full served vector); any mismatch raises and
  stops the process. Counts and max |Δ| are recorded per episode.
Disclosed in the report. No environment source file is modified (instance-level wrapper only).

## T2-6. Coordinator addition (16:2x UTC): save learner observations + oracle actions

Per decision: the learner's 113-dim observation `cf_ratio.encode_with_time(states, t, 100, cfg, 10)`
(112-dim MODQN encoding + `(T - t)/T`), `cfg` taken from the pilot's own A1-OFF-s0 final checkpoint
payload via `cfr.trainer_config_from_payload` (config only; weights never used; checkpoint sha256
and the four encoding fields `snr_encoding`, `theta_encoding`, `offset_scale_km`,
`load_normalization` recorded), the oracle's chosen action, plus — cheap and needed for a masked BC
probe — the legal mask (bool x28) and the reference action. Per-episode `.npz` written beside each
episode JSON; assembled per cell into `results-oracle/<cell>-<set>-obs-actions.npz` (float32 obs,
int16 actions, int16 episode/step/user indices) after the cell completes; sha256 recorded here.
Every per-episode JSON also stores the chosen and the reference joint action per step (for replay).
No counted oracle cell had run before this addition, so nothing needs reconstruction.

## T2-7. Memo smoke (16:29-16:31 UTC) — memo is bit-identical; counted run launched

`results-oracle-smoke2/` (A-real R1, B-real R1; eval ep 0, 2 steps; script sha256
`850f0e77…19ddf`): step 0 = 41 s (was 240 s), step 1 = 23.6 s; 48 step-0 bitwise memo-vs-pristine
verifications, max |Δ| 0.0; parity 0.0. **Compared with the memo-free smoke (`results-oracle-smoke/`):
identical on all 15 per-step fields (bits, joules, served, lit beams, moved, disallowed, changed,
eta, ref bits/joules, rate mean/p10/min, sum of accepted move gains, n_eval) at both steps, and
identical episode bits/joules/full rate lists — for both A and B.** Obs encoding cfg from
`A1-OFF-s0/policy-ep01000.pt` (sha256 `d7048d59…15cb`): snr_encoding=log1p,
theta_encoding=raw_radians, offset_scale_km=100.0, load_normalization=divide_by_num_users; obs
shape (100, 113) per step asserted.

**LP extra identity found while aggregating**: LP-prev(12, 0) is bit-identical (7 fields) to
`C3_B1_NO_NEW_BEAM` in read-only `calibration.json` (sha256 `59952214…562d`) — the c->inf end of the
family. Also LP-seq(0, m) == LP-prev(0, m) bit-for-bit (12 fields) for m in {0,2,6} on both sets.

### Detached processes — ORACLE counted run (launched 16:31:40 UTC)

cwd `/home/sat/mcrl-v025-h4-probe-ws/tree`; env `MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91`,
`OMP/MKL/OPENBLAS_NUM_THREADS=1`; `setsid nohup nice -n 16`; script sha256 `850f0e77…19ddf`.
cmdline `/home/sat/mcrl-leo-handover/.venv/bin/python /home/sat/mcrl-v025-h4-probe-ws/scripts/oracle_cells.py
--shard K --nshards 4 --results-dir /home/sat/mcrl-v025-h4-probe-ws/results-oracle`.
- shard 0 PID 3509431, log `logs/oracle-shard0.log`
- shard 1 PID 3509432, log `logs/oracle-shard1.log`
- shard 2 PID 3509433, log `logs/oracle-shard2.log`
- shard 3 PID 3509434, log `logs/oracle-shard3.log`
Work list: 150 episode items in priority order (A-real R1 eval 24, B-real R1 eval 24, A-real R2
eval 24, B-real R2 eval 24, B-real R1 rev eval ep 0-5, A-real R1 cal 24, B-real R1 cal 24), item k
to shard k % 4. Output per item `results-oracle/<kind>-real-<ref>-<set>-<order>-epNN.json` +
`...-obs-actions.npz` (JSON written last = item complete). Idempotent: existing JSON -> skip. To
resume after an interruption: relaunch the same 4 commands (never while any shard is alive).
Expected: ~240 s/episode -> 4 eval cells done ~18:10 UTC, everything ~19:05 UTC. Then run
`oracle_cells.py --assemble --results-dir .../results-oracle` (per-cell npz) and aggregate.

## T2-8. LP report WRITTEN (16:36 UTC) — deliverable (1) done

`.scratch/h4-probe/LP-PROBE-2026-09-11.md` (supersedes the draft; draft's declarations kept). Reading
**(i)** on evaluation (and on calibration). Aggregation `scripts/lp_aggregate.py` (sha256 `4564128d…86b1`);
every best-cell table number re-checked programmatically against the aggregate (14 rows, 0
mismatches); prose claims re-checked (peak-at-c=2 wording corrected for m=6; LP-seq(1,6) served
<0.995 added). `results-lp/SHA256SUMS` (99 files, sha256 `9ded3ef4…84ac`), all 99 identical both ends.
First line: best LP-prev(2,0) 115,091,222.48 bit/J = +7.56 % vs A m=2dB (paired +7.73 ± 0.74 %,
24/24), served 0.99850, p10 97.25 Mbit/s; best LP-seq(2,0) +8.92 % but served 0.98796, p10 degenerate;
best served-OK LP-seq(1,0) +6.65 %.

## T2-9. Post-run tooling staged (~16:42 UTC), run after the shards exit (process cap)

- `scripts/ref_b1.py` (sha256 `380e02b3…bb7e`): enriched roll of the R2 rule `C3_B1_NO_NEW_BEAM`
  through `lp_common.pooled_rollout_rates` on both sets -> `results-lp/REF-C3_B1_NO_NEW_BEAM-<set>.json`;
  calibration checked bit-for-bit vs `calibration.json` (placebo; stops on mismatch).
- `scripts/oracle_replay.py`: replays every oracle item from its saved joint actions; asserts the
  reference is reproduced each step, the committed bits/joules equal the saved ones bitwise, the
  re-encoded observation and the action equal the saved npz rows bitwise, and evaluator per-user
  rates == committed rates; measures the ruling's per-user rate floor ("no served user below 50 %
  of its rate under `A m=2dB` at the same step") as a share of served user-steps.
  Why: the ruling (`V025-CONTROLLER-RULING-CEILING-PARITY-...` §2) defines the rate floor per user
  per step, which the oracle JSONs do not store; the replay measures it exactly and also proves the
  saved joint actions are sufficient for the coordinator's later BC-pair reconstruction.
- `scripts/oracle_aggregate.py`: per-cell pooled stats, paired vs `A m=2dB`, B-vs-A, order
  sensitivity, per-step-index profile, amendment rules 1-4 (both the "relative to A-real" and the
  "points over the rule" reading of "A-real + 3.3 %").
- Early observation (4-8 episodes of A-real R1 only; NOT citable): A-real moves 66-99 of 100 users
  per step and oscillates with a ~4-step period (lit beams and per-step p10 collapse at t=2-3, 6-7;
  committed step EE below the reference action's step EE at the same state on those steps) — the
  simultaneous-best-response herding that the declared definition permits; B-real is monotone per
  step by construction (F(V) >= F(R) = 0).

## T2-10. Scope: R2 calibration tie-ins appended (decided ~16:44 UTC; runs AFTER the current shards)

The brief says "Both cells on the 24 evaluation episodes (primary) and the 24 calibration episodes
(tie-in)" with A/B each run for R1 and R2, and the coordinator's addition says "(A-real and B-real,
both references, both episode sets)"; the cost guide's "6 cells" suggests R1 only on calibration.
Resolved toward the wider reading at the LOWEST priority: `oracle_cells.py` v2 appends
("A","R2","calibration") and ("B","R2","calibration") to CELLS (diff = 5 added lines, no other
change; v1 kept as `scripts/oracle_cells.v1-850f0e77.py`). **Deploy v2 to sat only after all four
current shards (PIDs 3509431-3509434) have exited** — relaunching while they run could start an
item a live shard is computing. Relaunch = same 4 commands; existing items are skipped, only the
48 new items run (~46 min on 4 processes). Report is written on the declared cells first if
needed; R2-calibration rows are added when done.

## T2-11. First complete oracle cell (16:55 UTC): A-real(R1) evaluation — 24/24 episodes

Pooled EE 113,342,542.25 bit/J = +5.927 % vs A m=2dB (paired +5.67 ± 0.88 %, 23/24), served
0.99925, lit beams 58.05, rate mean/p10/min 418.8 / 27.47 / 2.864 Mbit/s -> p10 0.271 x the rule's
(LP-style throughput-degenerate flag fires). Parity max |Δ| = 0.0 (bits and joules), 1,152 memo
verifications max |Δ| 0.0, 224 s/episode. 82.6 users moved per step; 4-step cycle in every
episode (t=2-3 and t=6-7: lit beams 42-53, per-step p10 14-58 Mbit/s, committed step EE 0.67-0.99 x
the reference action's step EE at the same state; and the reference's own step EE at the oracle's
state falls to ~0.5 x at t=3/7). Committed step EE < reference step EE on 37.5 % of steps. Pulled to
local `results-oracle/` (JSONs). Aggregator run OK on it.

## T2-12. Coordinator addition 2 (~17:00 UTC): per-decision 28-action advantage vectors — v3

Request: save for every decision `F(base_{-u}, a) - F(base_{-u}, base_u)` for all legal a (NaN for
illegal), float32, in the per-cell npz (Amendment 3 to Ruling 2 §3, soft-advantage distillation);
base = R (A-real) or the running vector when u decides (B-real). Do not interrupt v1 shards.
Implemented as `oracle_cells.py` **v3** (local `scripts/oracle_cells.py`; v2 kept as
`scripts/oracle_cells.v2-2977a70b.py`, v1 as `scripts/oracle_cells.v1-850f0e77.py`): npz gains
`adv` float32 [N,28] and `adv_disallowed` bool [N,28] (legal candidates the disallow rule rejected
keep their computed advantage and are flagged — so a consumer can see the teacher's constraint);
`adv[u, base_u] = 0`; users with an empty mask: all NaN. Decision logic and evaluation count
unchanged (`f` now computed before the disallow test — pure arithmetic). JSON gains
`oracle_cells_version: "v3-adv"`. `--assemble` includes `adv`/`adv_disallowed` only if every
episode of the cell has them (fails loudly on a mixed cell).
**Vector coverage (to be confirmed at the end):** the 150 items of the running v1 shards
(A-real R1 eval, B-real R1 eval, A-real R2 eval, B-real R2 eval, B-real R1 rev eval ep0-5, A-real R1
cal, B-real R1 cal) have actions/observations/masks/reference actions/joint actions ONLY — no
advantage vectors. The 48 R2-calibration items run by v3 will have vectors. Reconstructing vectors
for v1 items by replay costs the same ~2,500 evaluations/step as the original run (not cheap).
Deploy order after the v1 shards exit: v3 smoke (2 steps A-R1 and B-R1, compare bitwise vs
`results-oracle-smoke2/` and check adv consistency with the chosen actions) -> then launch.

## T2-13. Controller priority (~17:19 UTC, Amendment 4 to Ruling 2 §2): rate-floored cells first — v4

Request: the B1/B2 decision waits on (1) rate-floored A-real and B-real (a move disallowed if it drops
any served user below 50 % of its rate under the reference `A m=2dB` action at that step) and (2)
the complete B-real(R1) evaluation cell; order the remaining work so these land first; apply
Amendment 1 rules 1-4 to the rate-floored cells; state Amendment 4 §2's B2 condition (B-real − A-real
in percentage points over `A m=2dB`, after the floor). <= 4 processes.

- B-real(R1) evaluation was complete (24/24) at 17:18 UTC.
- **v1 shards stopped at 17:20:40 UTC** by exact PID (3509431-3509434; cmdline and cwd verified
  immediately before `kill`). Items complete at that moment: A-real R1 eval 24/24, B-real R1 eval
  24/24, A-real R2 eval 2 (JSON+npz each, counts consistent); the four in-flight A-real R2 items
  (started 1-4 min earlier) were lost and will be recomputed (no partial output: JSON is written
  last; no `.tmp` left). These 50 v1 items have NO advantage vectors.
- **v4** `scripts/oracle_cells.py` sha256 `7c12ae9a…5e97` (v3 kept as `oracle_cells.v3-21b428c9.py`;
  v1 copy on sat as `scripts/oracle_cells.v1-850f0e77.py`). Changes vs v3: kinds `Af`/`Bf`
  (labels `A-real-floor`, `B-real-floor`, R1 only) whose disallow test adds
  `any(served_R & (rate_cand < 0.5 * rate_R))`, rates = `link_rate_bps` masked by served
  (identical to `r1_throughput`, step.py:1100); floor-only rejections counted separately
  (`n_disallowed_floor_only`); memo verification also compares the per-user rate vector; JSON
  `kind` = label, `floor` flag, `oracle_cells_version: "v4-floor"`. Non-floor logic unchanged.
- **v4 work order**: A-real-floor R1 eval (24), B-real-floor R1 eval (24), [A/B-real R1 eval: done,
  skipped], A-real R2 eval, B-real R2 eval, B-real R1 rev eval ep0-5, A-real R1 cal, B-real R1 cal,
  A-real R2 cal, B-real R2 cal. All v4 items carry advantage vectors.
- v4 smoke launched 17:21 UTC (`results-oracle-smoke4/`, kinds A, B, Af, Bf on R1, 2 steps).

## T2-14. v4 smoke passed; v4 shards launched (17:23 UTC); B-real(R1) eval result

v4 smoke (`results-oracle-smoke4/`, R1, eval ep 0, 2 steps): A and B **identical to the v2 smoke on
all 15 per-step fields and the full rate lists** (non-floor logic unchanged); `adv_check.py` on all
four smoke npz: **0 inconsistent decisions**, NaN exactly on illegal actions; parity 0.0; 48 memo
verifications each, max |Δ| 0. Af/Bf: floor-only rejections ~450-660 at t=0 and ~1,600-1,940 at t=1
(most t>=1 candidates fail the floor); committed step EE still > reference (Af 1.07/1.03, Bf 1.19/1.21).

### Detached processes — ORACLE v4 run (launched 17:23:10 UTC)
cwd `/home/sat/mcrl-v025-h4-probe-ws/tree`; same env/nice/threads as before; script sha256
`7c12ae9a…5e97`; cmdline `.../python /home/sat/mcrl-v025-h4-probe-ws/scripts/oracle_cells.py --shard K
--nshards 4 --results-dir /home/sat/mcrl-v025-h4-probe-ws/results-oracle`; logs `logs/oracle-v4-shardK.log`.
- shard 0 PID 3529259 · shard 1 PID 3529260 · shard 2 PID 3529261 · shard 3 PID 3529262
Remaining 196 items at ~235 s -> floor cells (48) ~18:10 UTC; R2 eval ~18:55; rev ~19:00; R1 cal
~19:45; R2 cal ~20:35. Resume after interruption: relaunch the same 4 commands once none is alive.

**B-real(R1) evaluation, complete (24/24), v1 item set (no adv vectors):** pooled EE
138,591,214.31 bit/J = +29.523 % vs A m=2dB (paired +29.95 ± 1.03 %, 24/24), served 0.99913, lit
beams 64.91, bits ratio 1.323, rate mean/p10/min 570.15 / 115.65 / 0.000 Mbit/s (p10 1.141 x rule),
parity 0.0. B-real − A-real = +23.6 points over the rule (unfloored).

Post-run tooling (staged): `scripts/ref_rules.py` (sha256 `956b6d45…c0aa`) supersedes `ref_b1.py`
(not run): per-episode rolls of both reference rules on both sets with bit-for-bit cross-checks vs
REF-C1 and calibration.json -> `results-lp/REF-EPISODES-<rule>-<set>.json`; aggregator adds served
non-inferiority (paired cluster bootstrap over episodes, 10,000 draws, seed 20260911, lo95 >= −0.5
pp), bits ratio, Amendment 4 rate floor (p10 >= 0.5 x rule and bits ratio >= 0.95), rules 1-4 on
the floored cells and Amendment 4 §2 condition 1 (B-floor − A-floor >= +3.3 points).

## T2-15. LP report amended (~17:30 UTC): bits-ratio condition

Ruling 2 §2 (scenario B: "... served >= 0.995 and bits ratio >= 0.95") and Amendment 4 §1.3 (rate floor
= p10 >= 50 % and bits ratio >= 0.95) use a bits-ratio condition the LP declared reading did not. Added
a section + first-line clause: LP-prev(2,0) has bits 0.887 x (fails); best qualifying = LP-prev(1,0)
+6.662 % eval (+4.753 % cal), bits 0.954/0.952, p10 1.016/0.968; no LP-seq cell qualifies. Declared
reading (i) unchanged. B-real(R1) min rate 152.9 bit/s is one user-step (ep 16); 2 user-steps < 1
Mbit/s, 9 < 10 Mbit/s (A-real: 423 < 10 Mbit/s).

## CONTROLLER NOTE (17:40 UTC) — independent aggregate of A-real(R1) / B-real(R1) evaluation, PROVISIONAL
Recomputed by the controller from the raw per-episode JSONs (not this agent's aggregator): identical to T2-11 / T2-14 to the
printed digit — A-real(R1) +5.927 % (paired +5.67 ± 0.88, 23/24), p10 0.271 x rule; B-real(R1) +29.523 % (paired +29.95 ±
1.03, 24/24), p10 1.141 x rule, bits ratio 1.323; B − A = +23.60 points (unfloored); parity 0.0 in both. Details:
`.scratch/h4-probe/CONTROLLER-INDEPENDENT-AGGREGATE-2026-09-12.md`. Provisional until the oracle report; no gate decided.

## T2-16. Controller 17:40 UTC — v5, calibration-floor priority, masks, B2 context rule

**(2) Order.** v5 `scripts/oracle_cells.py` sha256 `a20cb6c4…3670` (v4 kept as `oracle_cells.v4-7c12ae9a.py`
locally and on sat). CELLS: Af-R1-eval, Bf-R1-eval (indices 0-47, identical to v4), **Bf-R1-cal, then
Af-R1-cal**, then A/B-R1-eval (done), A-R2-eval, B-R2-eval, B-R1-rev-eval ep0-5, A-R1-cal, B-R1-cal,
A-R2-cal, B-R2-cal. v4 and v5 list offsets differ by multiples of 4 (48), so shard K owns the same
items in both versions — no cross-shard duplicate is possible. The v4 launcher's queue is static, so
the running v4 shards are NOT interrupted mid-floor-item: a local monitor switches each shard at its
own boundary — when `logs/oracle-v4-shardK.log` shows its 12th floor item, `scripts/switch_shard.sh K`
(sha256 `e696d536…f039`) kills v4 shard K (exact PID, cmdline+cwd verified, refuses otherwise) and
starts v5 shard K (log `logs/oracle-v5-shardK.log`); the LAST shard to switch first runs
`ref_rules.py` (log `logs/ref-rules.log`) and `oracle_replay.py` (log `logs/oracle-replay-1.log`) in its
slot, then execs v5 shard K. Loss per switch: <= 20 s of an R2 item. Always <= 4 compute processes.

**(3) Masks.** In the **Af/Bf kinds, `adv_disallowed` is the UNION of service-floor rejections (the
candidate unserves a user R served) and rate-floor rejections (some user R served falls below 50 %
of its rate under R)**; in A/B kinds it is the service-floor rejections only. v5 adds
`adv_disallowed_floor` = the **rate-floor-only** subset (rejected by the rate floor while unserving
nobody); `adv_disallowed_floor ⊆ adv_disallowed` and its count equals the step's
`n_disallowed_floor_only`. v5 unit test vs v4 with a mock evaluator (1,600 cases: 4 kinds x 2 orders x
200 random instances): decisions, stats, adv and adv_disallowed identical; floor mask subset/count
invariants hold; non-floor kinds carry no floor flags. Coverage: **Af/Bf evaluation items (v4) have
`adv` + union mask but NOT the floor-only mask** (cannot be derived afterwards without re-evaluation);
all v5 items have all three. `--assemble` fills missing arrays (NaN / False) in mixed-version cells and
adds per-row `has_adv` / `has_adv_floor` flags (tested locally on a synthetic mixed cell).

**(4) B2 student context rule for B-real / B-real-floor items (exact).** In one sweep each user decides
exactly once, in the item's `order` ("fwd" = users 0,1,…,99; "rev" = 99,98,…,0). At step t, when user u
decides, the running joint action is
`context_t(u)[v] = joint_chosen[t][v]` if v precedes u in the order, else `joint_ref[t][v]` (v = u and all
users after u still hold the reference action). This is exactly the vector the oracle evaluated for u
(its base action is `joint_ref[t][u]`, so `adv[u, joint_ref[t][u]] = 0`). Users that did not move have
`joint_chosen == joint_ref`, so the rule is well defined for all. Verified: every finished B item (24/24
so far, all B-real R1 eval) stores `order` ∈ {fwd, rev}, `joint_ref` and `joint_chosen` as 10 x 100
lists; the aggregator/report re-checks all B items at the end.

## T2-17. Controller 18:12 UTC (Amendment 6 to Ruling 2 §4): lane shortened — v6 with HELD cells

Direction: finish B-real-floor R1 evaluation to 24/24 -> aggregate the two floored R1 evaluation cells,
write "BRANCH NUMBERS (floored R1 evaluation)" here and in `.scratch/h4-probe/BRANCH-NUMBERS-FLOOR-R1-EVAL.md`,
end the turn with those numbers; the only next dataset is B-real-floor R1 calibration; HOLD the rest.
- **v6** `scripts/oracle_cells.py` sha256 `40307da6…4abdc` (v5 kept as `oracle_cells.v5-a20cb6c4.py`
  locally and on sat), deployed atomically on sat at 18:07 UTC, BEFORE any v4->v5 switch fired (all four
  v4 shards were on their 12th floor item). v6 = v5 + `HELD` set, applied AFTER the shard partition
  (ownership unchanged; queue entries kept). **HELD (recorded, not deleted): A-real-floor R1
  calibration; A-real R2 evaluation (2 v1 items done, 22 held); B-real R2 evaluation; B-real R1
  reverse order (evaluation ep 0-5); A-real R1 calibration; B-real R1 calibration; A-real R2
  calibration; B-real R2 calibration.** Runs: A-real-floor R1 eval, B-real-floor R1 eval (v4, finishing),
  B-real-floor R1 calibration (v6). To resume a HELD cell later: remove it from `HELD`, relaunch.
- The switch monitor's `switch_shard.sh` launches whatever `oracle_cells.py` is on disk -> v6 (its log
  file is still named `logs/oracle-v5-shardK.log`). v6 shards exit by themselves after their 6
  B-real-floor calibration items each (no kill needed); the last-switched shard first runs
  `ref_rules.py` + `oracle_replay.py` in its slot.

## T2-18. Switch done (18:07-18:11 UTC); floored R1 evaluation complete (B-floor 24/24 at 18:10:37)

Switch log (monitor, `switch_shard.sh`): v4 shard 0 pid 3529259 killed 18:07:58 -> v6 shard 0 pid 3552072;
v4 shard 1 pid 3529260 killed 18:10:11 -> v6 shard 1 pid 3554551; v4 shard 2 pid 3529261 killed 18:10:34 ->
v6 shard 2 pid 3554776; v4 shard 3 pid 3529262 killed 18:10:57 -> pid 3555066 = `bash -c` chain:
`ref_rules.py` (log `logs/ref-rules.log`) -> `oracle_replay.py` (log `logs/oracle-replay-1.log`) -> exec v6
shard 3 (log `logs/oracle-v5-shard3.log`). All kills right after each shard's 12th floor item (<= 20 s of
a HELD R2 item lost each). v6 shard logs confirm "HELD, skipped: 44"; each v6 shard runs its 6
B-real-floor R1 calibration items, then exits. cwd `/home/sat/mcrl-v025-h4-probe-ws/tree` for all.

## T2-19. RESUMED 18:31 UTC — cross-check of the controller's BRANCH-NUMBERS: CONFIRMED

Re-derived independently with `scripts/oracle_aggregate.py` (aggregate saved as
`results-oracle/AGGREGATE-oracle.json`) from the 48 per-episode JSONs re-pulled from sat.
**Every field the controller's `BRANCH-NUMBERS-FLOOR-R1-EVAL.md` prints matches mine at its printed
precision — 11/11 for each cell, and B − A = +19.2499 pp vs their +19.25.** No correction is needed.
- A-real-floor R1 eval: ee 113,531,833.45821163 (+6.103542 %), paired +5.7201 ± 0.9472 % (23/24),
  served 0.99925, beams 59.1292, bits ratio 0.99154, p10 28.6040 Mbit/s = 0.28209 x rule, parity 0.0.
- B-real-floor R1 eval: ee 134,129,417.19281109 (+25.353443 %), paired +25.7107 ± 0.9538 % (24/24),
  served 0.998875, beams 66.9292, bits ratio 1.32076, p10 165.4643 Mbit/s = 1.63181 x rule, parity 0.0.
- One clarification, not a discrepancy: the controller's 316,073 / 415,758 are the **total** disallowed
  counts (as their file says) — my totals are identical. The **floor-only** counts are **277,407**
  (A-floor) and **377,093** (B-floor); `n_disallowed_floor_only` IS present in every v4 item, inside
  `steps_detail[*]` (not at the top level), so it need not be listed as unavailable.

### New measurements from the replay (99 items, `logs/oracle-replay-1.log`, all replay_ok)
Replay = fresh env on each item's seeds, reference reproduced every step, committed bits/joules equal
the saved ones **bitwise**, re-encoded observation and action equal the saved npz rows bitwise,
evaluator per-user rates equal committed rates bitwise. Ruling 2 §2 per-user floor ("no served user
below 50 % of its rate under `A m=2dB` at the same step"), share of served user-steps violating:
| cell (24 eval episodes) | floor violations | share | worst rate ratio |
|---|---:|---:|---:|
| A-real (unfloored) | 7,963 / 23,982 | 33.204 % | 0.0063 |
| **A-real-floor** | 7,717 / 23,982 | **32.178 %** | 0.0085 |
| B-real (unfloored) | 3,193 / 23,979 | 13.316 % | 0.0000 |
| **B-real-floor** | **0 / 23,973** | **0.000 %** | 0.5000 |
The per-move floor removes essentially none of A-real's violations (32.2 % vs 33.2 %): each move is
legal against R with the others held at R, but 72-96 of 100 users move simultaneously, so the
committed joint action lands far from any of the tested unilateral deviations. B-real-floor satisfies
the floor exactly (0 violations, minimum ratio exactly 0.5000) — as the sequential construction
implies, since its final vector is the last accepted, fully evaluated candidate.
Served non-inferiority vs the rule (paired cluster bootstrap over episodes, 10,000 draws, seed
20260911): A-real-floor Δ +0.062 pp (lo95 +0.021), B-real-floor Δ +0.025 pp (lo95 −0.008) — both
non-inferior at −0.5 pp. Amendment 4 §1.3 rate floor (p10 ≥ 0.5 x rule and bits ratio ≥ 0.95):
A-real-floor **fails** (p10 0.282 x), B-real-floor **passes** (p10 1.632 x, bits 1.321).

## T2-20. Extra identity (18:36 UTC): the LP c→∞ endpoint equals B1 on BOTH sets

`ref_rules.py`'s independent roll of `C3_B1_NO_NEW_BEAM` is bit-identical to LP-prev(12, 0) on all 12
compared fields (ee, bits, joules, served, h_inter, h_intra, beams, all 24 per-episode EEs, rate
mean/p10/min, served user-steps) on the **evaluation** set as well as calibration (where both also
match `calibration.json`). Added to the LP report's identity table as check 7. On evaluation the R2
rule itself scores 102,738,840.61 bit/J = −3.983 % vs `A m=2dB`, served 0.99825, 38.33 lit beams,
bits 0.586 x, p10 38.39 Mbit/s — i.e. **the R2 reference rule is itself below the R1 rule**, which is
the context for reading any A-real(R2)/B-real(R2) cell (all HELD).
`ref_rules.py` cross-checks: C1 evaluation 13/13 fields vs REF-C1, C1 calibration 20/20 (REF-C1 +
calibration.json), B1 calibration 7/7 vs calibration.json, B1 evaluation no prior reference to
compare (0 checks) — its identity is established by check 7 above instead.

## T2-21. Per-cell npz assembled (18:37 UTC) + advantage-vector check on the full cells

`oracle_cells.py --assemble` on sat (`results-oracle/<cell>-obs-actions.npz`, 24,000 rows = 24 ep x 10
steps x 100 users, obs (24000, 113) float32):
| cell | sha256 | advantage vectors |
|---|---|---|
| A-real-floor-R1-evaluation | `4961b6d07e39e0e8bbeb5ba2cdf6d8dcea22363715c2a6d4834d1e2e502053b0` | yes (v4) |
| B-real-floor-R1-evaluation | `1cd4ec79dac06b37ffdaffb9d6831f71c4373aa4292eec74edf5fc6de2959dd7` | yes (v4) |
| A-real-R1-evaluation | `84823f5b7b88155496bcef1ad3090d5da74c9bce566488d3e888f91dac68f6d2` | no (v1) |
| B-real-R1-evaluation | `44add380850d659ff10b10cc50f28eb33fad250d6d012dda2f410cb60641c153` | no (v1) |
`adv_check.py` on the two floored cells: **0 inconsistent decisions out of 24,000 each**, NaN exactly on
illegal actions, disallowed flags 316,073 (A-floor) / 415,758 (B-floor) — i.e. every committed oracle
action is reproducible from the stored 28-action advantage vector under the declared decision rule.
Incomplete cells are skipped by the assembler and reported as such (B-real-floor-R1-calibration 22/24 at
that moment; all HELD cells 0/24 except A-real-R2-evaluation 2/24).

## T2-22. Artefacts pulled and B2-context fields verified (18:38 UTC)

- The four assembled evaluation per-cell npz were copied to `.scratch/h4-probe/results-oracle/` and
  **sha256-verified identical on both ends** (7.4 MB each for the floored cells, which carry the
  advantage arrays; 5.1 MB for the unfloored ones).
- **B2 context fields**: all **67** B-type items present (B-real R1 eval 24, B-real-floor R1 eval 24,
  B-real-floor R1 calibration 19 at check time) store `order` ∈ {fwd, rev} and `joint_ref` /
  `joint_chosen` as 10 x 100 lists with every action in [−1, 27]; 0 invalid. The reconstruction rule
  recorded in T2-16 (4) is therefore applicable to every B item, including all floored ones.

## T2-23. B-real-floor R1 CALIBRATION complete (18:40:48 UTC) — all four shards exited by themselves

24/24 items; `DONE shard 0..3/4` in `logs/oracle-v5-shard*.log`; **no process of this agent remains on sat**
(nothing had to be killed — the v6 HELD filter ended each shard after its 6 calibration items).
**B-real-floor R1, 24 calibration episodes** (vs `A m=2dB` on the calibration set = 112,195,917.54 bit/J,
served 0.99775, 62.98 lit beams, p10 111.39 Mbit/s): pooled EE **137,497,201.09 bit/J = +22.551 %**
(paired +22.639 ± 0.591 %, **24/24**), served 0.99871 (Δ +0.096 pp, bootstrap lo95 +0.021), lit beams
67.95, bits ratio 1.3172, rate mean/p10/min 592.91 / 177.07 / 22.151 Mbit/s (p10 **1.590 x** the rule),
parity max |Δ| 0.0, 1,152 memo verifications (max dev 0), 605,549 evaluations (2,523/step), 234 s/episode,
committed step EE below the reference's at the same state on **0.0 %** of steps.
Replay of the 24 calibration items: **0 per-user rate-floor violations**, replay bits/joules exact,
observations/actions bit-identical to the saved npz (122 replay items in total now).
Assembled `B-real-floor-R1-calibration-obs-actions.npz` (24,000 rows, obs (24000, 113)) sha256
`a8ee80fc59034d6c608a73966b4e059d2e6fed53ff85e3980ac6935d99d20daa`; `adv_check.py`: **0 inconsistent
decisions**, NaN exactly on illegal actions, 414,761 disallowed flags. This is the out-of-evaluation
teacher dataset the T_SEQ / B2 representability screen (Amendment 4 §2 condition 3) needs.
Global over all completed cells: parity max |Δ| **0.0**, memo verifications **5,760**, max dev **0.0**.

## T2-24. HELD inventory (nothing deleted; queue entries kept in `oracle_cells.py` v6 `HELD`)

| cell | items done / planned | note |
|---|---|---|
| A-real-floor R1 calibration | 0 / 24 | HELD (controller 18:12: only if the chosen branch needs it) |
| A-real R2 evaluation | 2 / 24 | HELD; the 2 done items are v1 (no advantage vectors) |
| B-real R2 evaluation | 0 / 24 | HELD |
| B-real R1 reverse order (evaluation ep 0-5) | 0 / 6 | HELD — the order-sensitivity check of the brief is therefore NOT measured |
| A-real R1 calibration | 0 / 24 | HELD |
| B-real R1 calibration (unfloored) | 0 / 24 | HELD |
| A-real R2 calibration | 0 / 24 | HELD |
| B-real R2 calibration | 0 / 24 | HELD |
To resume any of them: remove its tuple from `HELD` in `scripts/oracle_cells.py` (v6) and relaunch the
four shard commands (idempotent; completed items are skipped). Cost guide from the measured cells:
~230 s per episode per shard, i.e. ~23 min per 24-episode cell on 4 processes.

## T2-25. CLOSE-OUT (20:15 UTC) — deliverable (2) written; lane idle

Owner direction (20:10 UTC): stop expanding the matrix, close out with a minimal branch-adjudication
artefact. Done:
1. **Re-derivation vs the controller's `BRANCH-NUMBERS-FLOOR-R1-EVAL.md`: MATCHES exactly** at its
   printed precision (9 re-checked fields per cell in this pass, 11/11 in the 18:35 pass, and
   B − A = +19.2499 pp vs its +19.25). That file needs no correction; the only clarification is the
   total-vs-floor-only disallowed counts recorded in T2-19.
2. `.scratch/h4-probe/ORACLE-CELLS-2026-09-11.md` written (300 lines): first line, provenance,
   definitions, validity machinery, cross-check, evaluation + calibration tables, per-step profiles,
   Amendment 1 rules 1-4 on the floored cells, Amendment 4 §2's three B2 conditions, the herding
   analysis, the B2 teacher dataset + context rule, the HELD inventory with what each cell would have
   answered, files and scope limits. Every headline number re-checked programmatically against
   `results-oracle/AGGREGATE-oracle.json`.
3. B2 dataset confirmed independently on `B-real-floor-R1-calibration-fwd-ep00-obs-actions.npz`
   (10 arrays incl. `adv` (1000,28), `adv_disallowed`, `adv_disallowed_floor`; NaN exactly on illegal;
   `adv[u, ref_action[u]] = 0`; floor mask a strict subset). All **72** B-type items carry `order`,
   `joint_ref`, `joint_chosen`.
4. HELD recorded in T2-24 and in the artefact with what each would answer; **no new compute started**;
   **no oracle process alive on sat** (all shards exited normally).

### Lane state for whoever resumes
Complete cells (24 episodes each): A-real R1 eval, B-real R1 eval, A-real-floor R1 eval,
B-real-floor R1 eval, B-real-floor R1 **calibration**. Parity 0.0 everywhere; 5,760 memo checks at
0.0; 122 replays exact; 72,000 advantage-vector decisions reproduced with 0 inconsistencies.
Open from the original brief: the **order-sensitivity** cell (B-real R1 reverse order, ep 0-5) and all
R2 cells — HELD, not measured. Nothing in the oracle matrix blocks the learner lane.
