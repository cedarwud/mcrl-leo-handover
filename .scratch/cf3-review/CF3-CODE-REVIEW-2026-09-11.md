**0 INVALIDATES and 1 BIASES finding: the worst is that the report aggregator in the tree deployed on `sat` (e8a04ccf) still applies the pre-Amendment-2 reading (C-H required for branch 1, seeds 3-4 dropped, C2 labelled "INACTIVE"), so a report run from that tree would misread the result. The training math, the A0 baseline and the evaluation implement the declaration.**

**The most consequential point for interpretation is not a code defect.** The declared equal-share energy label
(caveat C1) gives each user 1/U of its own action's energy consequence. In a counterfactual probe the `η·E` term
changed the one-step argmax in 0 of 240 decisions. So whatever A1-A3 learn, they do not make an energy trade-off in
the argmax, and "CF3 taught energy-aware decisions" cannot be the reading.

# CF3REVIEW: does the CF3 pilot trainer implement what was declared?

Date: 2026-09-11. Reviewer: CF3REVIEW (read-only; no file edited, nothing committed, no `sat` process touched).

## What I reviewed

- **Worktree HEAD at the time of reading: `ca678414`** on `cf3/pilot-20260911` (base `363845e8`). Training code read at
  `aa77be8a`, then re-diffed: `aa77be8a..ca678414` touches only `scripts/cf3_diag100.py` and `scripts/cf3_report.py`.
- **Deployed tree on `sat`: `e8a04ccf`** (`ws/tree/COMMIT`, and PROGRESS "LAUNCH 10:25:45 UTC, tree e8a04ccf").
  PROGRESS step 5 names `b270592f` (premeasure) and `c9df1f93` (smoke, diag100); those are superseded, since the
  production launch is on `e8a04ccf`. **Deployed vs HEAD** (sha256 read over ssh, prefix shown):
  `cf_ratio.py 6f57edd5`, `cf_sources.py c4906a7d`, `run_cf3_pilot.py a78dfef2`, `cf3_common.py 0d10596d`,
  `cf3_eval.py b361ea09`, `modqn.py e10796b4` are all **identical** to the worktree. The one file that differs is
  **`scripts/cf3_report.py`**: sat has the `e8a04ccf` version (`1b527a06`), HEAD has the Amendment-2 rewrite
  (`ca678414`). See finding F1.
- Governing documents: the declaration, Amendment 1, Amendment 2, and `.scratch/cf3-pilot/DECLARATION-ADDENDUM.md`
  including its post-Amendment-2 sections A-G (seeds 3-4, readings/AUC, shared archive, fresh launch).
- **Tests: 15/15 pass** at `ca678414` (`.venv/bin/python -m pytest tests/test_cf_ratio.py`, local pinned archive,
  no skips).
- **Configs actually running** (read from `sat:ws/runs/*/status.json` fingerprints: config fields only, no metrics):
  - A0 s0: `discount_factor 0.9`, `td_bootstrap_mode eq16-per-head-max`.
  - A1 s0, A2 s3, A3 s4: `discount_factor 1.0`, `shared-continuation-argmax`.
  - All four: lr 0.001, batch 128, ε 1.0→0.01 over 222 episodes, target sync every 50, replay 50,000, (100,50,50)
    tanh.
  - All CF settings identical except `source_kind`: `eta0 110507234.83`, `bits_scale 1.3329e10`,
    `joules_scale 120.617`, `lambda0 0.0`, `dual_ascent False`, `rho 1/9`, buffer 50,000.
  - Same calibration sha `59952214…` and TLE sha `427e6a91…` in every run.

## Findings

### F1: BIASES (the reading). The deployed report aggregator is pre-Amendment-2.

`sat:ws/tree/scripts/cf3_report.py` is the `e8a04ccf` blob. Nothing in `eval.sh` runs it, so whoever aggregates
will reach for it by hand. Verified by reading `git show e8a04ccf:scripts/cf3_report.py`:

- `:117`: **branch 1 requires `ch["A2"]["met"]`** (A2's seed-mean `H_inter` ≤ 0.6016). Amendment 2 item 1 removed
  C-H from the reading.
  - Failure scenario: A2 > A3 and A2 > A1 with C-S non-inferior, but A2's `H_inter` is above 0.6016. That is now
    plausible, because λ = 0 and MAX_NOMINAL_GAIN already runs at 0.655. The old script falls through to "none of
    the declared branches" (`:115-124`) instead of branch 1.
- `:39, 56, 80, 83, 95`: **only seeds 0-2 are read**. The five-seed rule of addendum D (≥ 3 of 5 for A1/A2/A3) is
  silently replaced by a 2-of-3 rule on a subset.
- `:58, 125-128`: it reads `e.get("c2_activation")`. The deployed `cf3_eval.py` no longer writes that key; it writes
  `c2_lambda_star`. So `c2_changed_fraction` is `None` → treated as 0. With λ ≡ 0, **every A2 seed is labelled
  `c2_head_inactive_A2 = True`**, which is the classification Amendment 2 item 3 abolished.

HEAD `ca678414` fixes all three: `scripts/cf3_report.py:22` gives the seed sets, `:30-34` the majority rule, and
`:148` the branch without C-H. **Fix: run HEAD's `cf3_report.py`, not the sat copy** (or re-deploy it), and record
the report script's commit in the output (the report records only the eval JSONs' commits). Verified.

### F2: COSMETIC. `diag100` "term share" measures level, not decision influence.

`scripts/cf3_diag100.py:71-72, 87` computes `|Q_B(a*)|` against `|η̃ Q_E(a*)|` at the greedy action. PROGRESS
reports this as "B ~0.49-0.52, E ~0.48-0.51". That number is the share of the score's **magnitude**. Because
`E_u = P_sys·dt/U` is the same for every user in a step, most of `Q_E(s,a)` is state value common to all of a
user's legal actions. The share says nothing about how much `Q_E` moves the argmax. Do not read it as "the energy
term steers half the decision"; see C1 for the decision-level number. Verified (code).

### F3: COSMETIC. The λ* diagnostic can report a λ that does not meet the bound.

In `scripts/cf3_eval.py:86-98` the doubling search stops at `hi > 1e4` even if `H_inter` is still above 0.6016.
Bisection then runs between two infeasible values, and `lambda_star = hi` plus `changed_fraction` are reported for a
λ that never met the bound. The `search` list exposes this, but the headline field does not. Diagnostic only.
Verified (code).

### F4: COSMETIC. A stray `StopIteration` is recorded as a clean stop.

`scripts/run_cf3_pilot.py:287-291`: any `StopIteration` escaping training is recorded as `status: stopped-at` with
`stopped_at: None`, and the process exits 0. In production `--stop-after` is unset, so only a library bug could
raise it. The relaunch would then resume, so nothing is lost silently beyond the exit code. Verified (code).

### F5: COSMETIC (declared). A0 has 3 seeds, A1-A3 have 5.

In `cf3_common.py:26-28`, `cf3_report.py:22, 30-34`, the A2-vs-A0 comparison (the owner's success gate) and A1 vs
A0 compare **means over different seed sets**: 5 against 3. Only the pair-majority is on the matched seeds 0-2.
This is declared (addendum D) and unbiased in expectation, since seeds are exchangeable. The declaration's "3
training seeds per arm, same seeds across arms" no longer holds for A0, though. Suggest also printing the matched
(seeds 0-2) means whenever A0 is involved. Verified (code).

## Known, assigned (coordinator list): confirm or refute

1. **Learning-check failure path off-by-one**: **confirmed, narrower than the name.** At `run_cf3_pilot.py:293`,
   `done = len(logs)+1 = 500` is the right episode count. But the gate raises inside `quarter_update`
   (`cf_ratio.py:667-668`) before the episode-499 log is appended (`cf_ratio.py:797`, callback). So `save(500)`
   writes a resume payload with `next_episode=500` and 499 logs. It cannot be resumed ("not contiguous"), and the
   ep-499 row is lost. `policy-ep00500.pt` holds the right weights, and the pass path is unaffected.
2. **`DECISION.json` multi-writer race**: **confirmed, and it can crash a run, not just a record.**
   - `run_cf3_pilot.py:240-242` does a check-then-write, and `cf3_common.py:82-86` writes through a fixed
     `DECISION.json.tmp`.
   - If two processes collide, the loser's `tmp.replace` raises `FileNotFoundError`. That propagates through the
     gate to `except Exception` (`:299-303`), so the run is marked `failed` and exits.
   - It is recoverable: a relaunch resumes from ep 400 and finds `DECISION.json` present. The odds are low, because
     the processes poll on independent 20 s phases. The decision each process applies comes from the A1 files, so
     it is never corrupted.
3. **Resume fingerprint lacks code identity**: **confirmed.** The fingerprint (`run_cf3_pilot.py:132-137`) holds
   arm, seeds, config, settings, calibration sha, TLE sha and prereg digest; there is no commit or file hash.
4. **No process-level resume test**: **confirmed.** `test_resume_does_not_repeat_episodes_and_is_bit_identical`
   exercises the in-process `training_state_dict` round trip only. Nothing covers `run_cf3_pilot.py`'s payload,
   logs, status or `readings.jsonl` (which gets duplicate rows on a mid-interval resume; the report takes the first,
   which is identical under deterministic resume).
5. **Launcher PID reuse**: **confirmed.** `launch.sh` skips a run if `kill -0 $(cat PIDF)` succeeds, so a recycled PID
   hides a dead run. (`eval.sh` skips on the eval JSON existing, not on PIDs.)
6. **5 GB per-process margin at full buffers**: **plausible, not yet measurable.**
   - A1 was at 1.84-1.92 GB at ep 100 (status `rss_gb`).
   - A2/A3 had not reached their first save when I looked.
   - In diag100 (four archive copies), A2/A3 peaked at 4.4 GB during save. The archive is now shared, but the
     `TleArchive` parse cache still grows without bound as new TRAIN-split days are drawn.
   - `save()` deep-copies all four 50k buffers.
   - An OOM kill mid-save is safe: `resume.pt` is replaced atomically. It is not self-healing, though: someone has
     to re-run `launch.sh`. Additionally, an A1 seed 0-2 that dies before ep 500 and is not relaunched within 4 h
     makes every waiting CF run time out into `stopped-learning-check` (`:231-233`). `launch.sh` then treats that as
     finished forever; only the `reason` string tells a timeout from a real failure.

## Checklist 1-10 (what I verified, with file:line)

### 1. Reward vector: verified correct

- `cf_ratio.py:100-108`:
  - `B_u = r1_throughput·dt` (bit/s × s), forced to 0 if unserved.
  - `E_u = P_sys·dt/U` for every user.
  - `H_u = [INTER_SATELLITE]`.
- `r1_throughput` really is bit/s:
  - `env/step.py:1100` fills it with `rate[uid]`.
  - `step.py:965-971` sets `rate = 0` for unserved users.
  - `runtime/energy_efficiency.py:144` gives `system_throughput_bps = rates.sum()`.
  - So `Σ_u B_u` equals the evaluator's bits exactly, not just approximately: the forced 0 is redundant.
- `served` is `resolution.served` (`runtime/trainer_env.py:237`), the same flag the energy block uses.
- `Σ_u E_u = P_sys·dt` (to 1 ulp). Units match `pooled_rollout` (`cf_ratio.py:368-369`), which reads
  `energy.system_throughput_bps·dt` and `system_consumed_power_w·dt`.
- **D-2 adapted**: within a step every user carries the same `E_u`, and `B_unserved = 0 ≤ B_served`. So an unserved
  user's `B − ηE = −ηE_u` is never better than a served user's; at worst it ties, for a served user at rate 0.
- The one channel by which an outage could lower E is that user u's own action changes `P_sys` by one beam. That
  reaches u's own label only as `ΔP·dt/U`: about 1.9 J against a lost `B_u` of order `s_B`. There is no free ride.
- `H` counts re-entry after an outage as inter-satellite (addendum), the same as the evaluator.

### 2. TD target: verified correct

- **γ = 1 with a true terminal**:
  - `run_cf3_pilot.py:103` sets `discount_factor=1.0` for A1-A3 (confirmed in the running fingerprints).
  - `cf_ratio.py:600` computes `r + γ·Qtgt(s',a*)·(1−done)`, with `done` from the environment at the 10th step.
- **Remaining-steps feature**:
  - `cf_ratio.py:502-507` gives `(T−t)/T`; it is 1.0 at t=0, 0.1 at t=9 and 0.0 at the terminal next state.
  - It is used for the main env (`:698, 722`), the sources (`:195, 205, 214`), calibration (`:633`) and
    evaluation (`cf3_eval.py:58`).
  - A0 uses MODQN's 112-dim `_encode_states` (`modqn.py:766-771`) with no time feature.
  - The networks are rebuilt 113-wide from the same seed (`cf_ratio.py:454-466`). `_predict_objective_q_values`
    and `sync_targets` read `self.q_nets`/`self.target_nets` dynamically, so no stale 112-dim reference survives.
- **One shared continuation action**:
  - `cf_ratio.py:540-549` takes `argmax[Qtgt_B − η̃ Qtgt_E − λ Qtgt_H]` with `masked_fill(~next_mask, −1e9)`.
  - It uses **target** networks for both selection and evaluation (not Double-DQN), as the addendum declares.
  - The same `a*` is gathered for all three heads (`:598-599`). It is recomputed per head, but the target nets and
    η are unchanged inside `update()`, so it is the identical action.
  - Online action selection is masked (`modqn.py:414-451` via `cf_ratio.py:522-528`; greedy at `:530-538`).
- **λ exactly 0**:
  - `CFRatioSettings.lambda0 = 0.0` and `dual_ascent = False` (`cf_ratio.py:150-151`). The launcher passes neither
    (`run_cf3_pilot.py:114-124`).
  - `quarter_update` keeps `self.lam` (`cf_ratio.py:659-662`).
  - `_combine` subtracts `0·Q_H`, which is bit-identical to `Q_B − η̃Q_E` for finite `Q_H`. Parameters are
    asserted finite (`:620`).
- **Nothing stale**:
  - Replay stores the raw `(B,E,H)` (`:733`).
  - Normalisation by fixed units happens at sample time (`:552-553, 593-596`), and η̃ is read live (`:510-512`).
  - The one lossy step is that `ReplayBuffer.sample` casts rewards to float32 (`runtime/replay_buffer.py:50`).
    That is a relative 6e-8 on bits of order 1e10, which is negligible.

### 3. Scaling: verified correct

- `s_B`, `s_E` and `η_0` come from one calibration JSON (MAX_NOMINAL_GAIN on the calibration seeds;
  `cf3_premeasure.py:74-80`). They are frozen in `CFRatioSettings` and are identical in all 15 CF fingerprints
  (sha `59952214…`).
- `η̃ = η·s_E/s_B` (`cf_ratio.py:510-512`), so `η̃_0 = 1`.
- The units array is fixed at construction (`:492-494`); η updates change `η` only.
- There is no per-arm adaptation.

### 4. η schedule: verified correct

- `quarter_update` runs at 250/500/750/1000 (`cf_ratio.py:790-793`).
- `eta_due = episode_done ≥ 500` (`:663`). The update applies at 500 (after the gate, `:667-671`) and at 750.
  The 1000 reading is recorded, not applied (`final=True`, `:666, 673`).
- The measurement is a **fresh greedy rollout on the 24 calibration seeds**, one new environment per episode
  (`:624-639`, `:344-347`). It never touches replay, and it gives pooled `Σbits/Σjoules` from the environment
  (`:385-396`).
- The learning check (`run_cf3_pilot.py:222-245`) waits for A1 seeds 0-2 and passes if ≥ 2 beat
  `random_reference_ee`. Seeds 3-4 obey the same decision. A0 is not gated.
- Readings at 100 (`:205-220`) and at the quarters consume no training RNG. The greedy rule draws nothing
  (`cf_ratio.py:530-538`), and the rollouts use their own generators.

### 5. Replay mixing: verified correct

- The batch is `n_per_source = round(1/27·128) = 5` rows from each source plus 113 main rows
  (`cf_ratio.py:488-491`; diag100 counted 113:5:5:5 exactly).
- One batch trains all three heads (`:602-619`).
- An update needs main ≥ 128 and every source buffer ≥ 5 (`:561-566`). In practice that is the same step for A1-A3.
- Source rows are drawn with a separate `_catfish_rng` (`:472-474, 571`) seeded identically for CF3 and NULL3, so
  their batch indices are matched.
- NULL3 differs only in the policy (`build_sources`, `:281-294`): uniform over the legal set from its own
  generator (`cf_sources.py:119-130`).
- Buffer capacity is `config.replay_capacity` for every source in both arms (`run_cf3_pilot.py:117`).
- Each source environment is its own `TrainerEnvironment` with its own `default_rng(env_seed)`/`(mobility_seed)`
  (`cf_ratio.py:189-192`). Only the immutable `TleArchive` parse cache is shared: `TleDailyFile`/`TleRecord` are
  frozen dataclasses (`env/tle.py:79-80, 192-193`), and `Satrec`s are built per driver (`env/ephemeris.py:479-482`).
- **Gradient steps**: exactly one `update()` per main-environment step in every arm (`cf_ratio.py:739`;
  `modqn.py:1506`). The three source environments add data, never updates (diag100: 999 updates in 100 episodes
  for A1, A2 and A3 alike).

### 6. Sources: verified correct

- `cf_sources.py:43-101` matches FEASFRONT `frontier.py:65-123` statement for statement. That covers
  `incumbent_slot`, `pick` with the fixed fallback (at `m ≤ 0`, plain restricted argmax with no incumbent hold), and
  `r_no_new_beam = load > 0.5`.
- The rules are C1 = `make_rule(2.0)`, C2 = `make_rule(12.0)`, C3 = `make_rule(restrict=r_no_new_beam)`
  (`cf_sources.py:145-150`).
- Parity is checked by an exec of `frontier.py`'s own functions (`tests/test_cf_ratio.py:415-445`).
- Both files carry the same docstring inaccuracy: `pick`'s docstring says the fallback order includes "then
  incumbent", but the code has no incumbent fallback in either file. It is harmless.
- Each source steps once per main step on its own environment copy, reset every main episode (`cf_ratio.py:699-700,
  737-738`).

### 7. A0: verified correct

- A0 is `MODQNTrainer` (`run_cf3_pilot.py:129-130`) with `td_bootstrap_mode = eq16` (the D-1 flag off) and γ 0.9
  (confirmed in the fingerprint).
- Per-head target max is at `modqn.py:689-693`. Weights `(0.5, 0.3, 0.2)` come from the frozen record. Rewards
  `r1/r2/r3` carry the D-2 floor (`modqn.py:814-838`) and the frozen calibration scales `(2029238.43, 1, 6)`.
- D-3 calibrated logging is at `modqn.py:1529-1541`.
- A0 shares the ε schedule (222), episode count, seeds 0-2, calibration readings and the evaluation path.
- `modqn.py` is untouched by the branch (`git diff 363845e8..e8a04ccf -- src/` lists only the two new files).

### 8. Evaluation: verified correct

- `cf3_eval.py` asserts the pinned archive (`:117`).
- It loads `policy-ep01000.pt`, only for runs whose status is `complete` (`eval.sh`).
- Greedy runs with no RNG: `greedy_actions` for CF (`cf_ratio.py:530-538`) and `masked_argmax` over the scalarised
  Q for A0 (`cf3_common.py:90-108`).
- Every episode gets a fresh environment with `default_rng(9_111_000+i)` / `(9_112_000+i)`
  (`cf_ratio.py:344-347`). These are disjoint from training (1337-1341 / 7-11) and calibration
  (9_121_000+ / 9_122_000+).
- Pooled `Σbits/Σjoules` is summed left to right. Served, `H_inter`, `H_intra`, beams, handovers per user-minute and
  the determinism placebo are all reported.
- The pairing check hashes the arm-independent 112 columns (`:356-358`).

### 9. Resume: verified in process; process level not tested (known item 4)

- The CF state holds the MODQN state (replay, three NumPy generators, torch RNG, optimisers, environment `_age_rng`)
  plus η, λ, `dual_trajectory`, `_catfish_rng`, and for each source the env/mobility/policy generators, environment
  `_age_rng` and buffer (`cf_ratio.py:812-836`, `237-261`).
- The epsilon, target-sync and quarter cadence all key on the absolute episode number.
- `launch.sh` skips `complete`/`stopped-learning-check` runs and live PIDs.
- Resume restarts at the last 100-episode boundary and re-runs the tail deterministically. That is bit-identical
  in-process (tested), so no episode is skipped and none counts twice in the final state.

### 10. Other fairness: nothing material found

- Identical lr, Adam, MSE loss, batch, target sync, ε and episodes in every arm.
- One gradient step per main-environment step in every arm.
- No gradient clipping in either trainer.
- No exception is swallowed in `cf_ratio.py`: the finiteness asserts are fail-loud, and non-finite log values
  raise (`:794-796`).
- Single-threaded (`torch.set_num_threads(1)`, OMP=1), so runs are deterministic under contention.

## Declared-design caveats that bear on interpreting the result (not implementation defects)

**C1: the equal-share energy label gives each user 1/U of the energy consequence of its own action.** This was chosen
knowingly (Amendment 1 item 7), but its size should sit next to any A1/A2 reading.

- Each user's return is `Σ_t (B_u − η E_u)`. User u's action moves its own `B_u` fully, but moves its `E_u` only by
  `ΔP_sys·dt/U`, and it ignores its effect on other users' bits.
- The learned greedy rule is therefore a per-user decomposition of `ΣB − ηΣE`, not its maximiser, and the Dinkelbach
  update is applied to that rule.
- **Probe** (read-only, this review: `scratchpad/probe_contrast.py`, local pinned archive, 2 calibration episodes,
  MAX_NOMINAL_GAIN background, one user's legal alternatives scored by counterfactual `evaluate_actions` with common
  random numbers, normalised units, η̃ = 1), over **240 decisions**:
  - A user's own-bits spread over its legal actions: median **1.85**, p90 2.36.
  - Its own-energy-label spread (`ΔP·dt/U/s_E`): median **0.0156**, p90 0.0169, max 0.0217. The median ratio of the
    two is **0.0087**.
  - **The E term changed the one-step argmax in 0 of 240 decisions.**
  - The per-user objective's argmax differed from the system objective's argmax (`ΔΣB − ηΔP`, one step, others
    fixed) in **104 of 240 (43%)**. That is identical to own-bits vs system, because the E term never flips anything.
  - This is a one-step, fixed-background measurement. Over the horizon, `Q_E`'s action spread still carries the 1/U
    factor, so the conclusion does not depend on γ.
- The reading this supports: the energy head can barely move a decision through `Q_E`. If A2 or A3 differ from A1,
  the channel is replay coverage acting on `Q_B`/`Q_E` values, not an energy trade-off the argmax makes. A null C3
  result is consistent with this structure; it is not evidence that "consolidation fails".

**C2: evaluation epochs come from the TRAIN block split.** `make_env_on` uses `EpisodeStartSampler(..., TRAIN)`
(`cf_ratio.py:130-131`), exactly like `make_training_environment` and the B0 harness (`scripts/b0_pooled_ee_eval.py:56`).
Evaluation seeds are disjoint, but evaluation epochs are drawn from the same time blocks as training. The pilot
measures in-distribution EE, not held-out-epoch generalisation. A2/A3's source environments diverge from the main
stream after episode 0 and visit about 4× as many start epochs as A1. That extra coverage is part of "extra
experience", which A3 controls for, so A2 vs A3 stays fair.

## Verified vs inferred

- **Verified** (read the code, ran it, or read the running config):
  - F1 through F5.
  - Known items 1-5.
  - Checklist 1-10.
  - Deployed-vs-HEAD hashes.
  - The running fingerprints.
  - The 15/15 test pass.
  - The C1 probe numbers.
- **Inferred**:
  - The race probability in known item 2 (from the polling design).
  - The memory trajectory in known item 6: A2/A3 RSS at full length was not yet observable.
  - That a report would be run from the sat copy in F1 (depends on who aggregates and where).
