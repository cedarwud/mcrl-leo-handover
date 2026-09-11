# CF3PILOT — declaration addendum (implementation choices), written before launch

Date: 2026-09-11, ~10:05 UTC. Written **before any pilot training or evaluation result exists.** The only numbers
measured at the time of writing are the pre-launch no-training calibration rollouts, which are in flight and are not
cited here.

Governing documents, in order of precedence:
1. `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md`
   (supersedes the conflicting parts of 2.)
2. `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md`
3. Coordinator messages to CF3PILOT of 2026-09-11: the episode-500 learning check, progress readings at 250/500/750,
   and the CFSCREEN pairing fact (per-episode reseeded evaluation).

Everything below is a choice the documents leave open. Where a choice was needed, I took the simplest reading.
Nothing here changes an arm, a constant, C-H, C-S or the declared reading.

**Name.** Per Amendment 1 item 8, this is a **three-source catfish-inspired off-policy replay pilot**. It is not
faithful RIS catfish, DQfD or ACRM.

## Code and hosts
- Isolated worktree `/home/u24/papers/mcrl-leo-handover-cf3`, branch `cf3/pilot-20260911`, based on `363845e8` (the
  `READY FOR PILOT` commit). New files only: `src/mcrl/algorithms/cf_ratio.py`, `src/mcrl/algorithms/cf_sources.py`,
  `tests/test_cf_ratio.py`, `scripts/cf3_*.py`, `scripts/run_cf3_pilot.py`. `modqn.py` and every other existing file
  are unchanged.
- Training and evaluation run on `sat` in `/home/sat/mcrl-v025-cf3-pilot-ws/tree`, which is a `git archive` of the
  worktree commit. The report records the commit. The pinned TLE archive is copied into the workspace
  (`ws/tle-pinned-427e6a91`), and every process asserts `file_set_sha256 = 427e6a91…8fe9` before running.

## Seeds (all disjoint)
| role | seeds |
|---|---|
| training, seed index 0/1/2, identical across arms | `(train, env, mobility)` = `(42,1337,7)`, `(43,1338,8)`, `(44,1339,9)`. Index 0 is the frozen main-run triple. |
| calibration (eta_0, s_B, s_E, RANDOM reference, quarter readings, learning check) | 24 episodes; episode i uses `env = 9_121_000+i`, `mobility = 9_122_000+i` |
| evaluation | 24 episodes; episode i uses `env = 9_111_000+i`, `mobility = 9_112_000+i` |
| RANDOM_MASKED action draws | episode i uses `default_rng(9_131_000+i)`, uniform over legal actions |

## Evaluation protocol (declaration §Evaluation; CFSCREEN pairing fact)
- **Per-episode reseeding.** Every evaluation episode i runs on a **fresh environment**, reset with freshly seeded
  generators `default_rng(9_111_000+i)` / `default_rng(9_112_000+i)`. So every arm meets episode i at the same start
  epoch, population, warm-start ages and fading-stream start. This is a pure harness change: the environment's reset
  API is called with generators, and no physics or RNG contract is touched. It applies equally to calibration readings
  and to the learning check.
- **Estimand, identical to B0's harness** (`scripts/b0_pooled_ee_eval.py` core). Pooled EE = Σ bits / Σ joules over
  24 × 10 steps, divided once, with bits = `system_throughput_bps·dt` and joules = `system_consumed_power_w·dt` from
  `env.last_outcome.energy`. **I do not run B0's `run()` verbatim.** It hard-codes the stream `42/1337/7`, which is
  training seed 0, and its carried stream pairs arms only at episode 0. **Placebo:** my rollout function run in the
  harness's stream mode (one env, `42/1337/7`, `MODQNTrainer(train_seed=42).select_actions(eps=1)`) must reproduce
  B0's pinned RANDOM figure **52,420,510.0956937 bit/J bit-for-bit** (`HARNESS_PLACEBO` in the pre-measurement).
  **Pairing placebo at evaluation:** the same checkpoint evaluated twice must give bit-identical per-episode results,
  and all arms must share each episode's start epoch and t=0 observation hash. Both checks are recorded in the eval JSON.
- **Greedy** = the deployed rule, masked argmax, first index on ties, with no RNG consumed. A0 uses `Σ ω_i Q_i` with
  `(0.5, 0.3, 0.2)`. A1-A3 use `Q_B − eta·Q_E − lambda·Q_H` with the final checkpoint's eta and lambda.
- **Checkpoint = the final one** (`policy-ep01000.pt`). There is no selection.

## Reported quantities
- `H_inter` = inter-satellite handovers (`HandoverClass.INTER_SATELLITE`, which includes re-entry after an outage)
  per user-step. `H_intra` = intra-satellite handovers per user-step.
- Served fraction = served user-steps / user-steps (`energy.served`). Mean active beams = mean over steps of
  `energy.eff_beams`.
- **C-H**: an arm meets it if its seed-mean `H_inter` ≤ 0.6016. Every seed is also shown.
- **C-S** (vs A1, per the declaration): the difference in served fraction (arm − A1), pooled over each arm's 3 seeds.
  The 95% interval is a **cluster bootstrap with clusters = the 24 evaluation episodes**, which are paired across arms
  because of per-episode reseeding: 10,000 resamples, percentile interval. The arm is non-inferior iff the lower bound
  is > −0.5 pp. The per-seed differences are also shown. With 3 seeds this interval does not capture seed-to-seed
  variation, and the report says so.
- **Operational "X > Y" for the declared reading** (pilot = direction only): X > Y iff the seed-mean pooled EE of X is
  higher **and** X beats Y on at least 2 of the 3 same-index seed pairs. Otherwise X ≈ Y (no direction established).
  Branches:
  - (1) A2 > A3 and A2 > A1, C-H met, C-S non-inferior → directional signal.
  - (2) A2 ≈ A3, with A2 > A1 and A3 > A1 → extra experience.
  - (3) not (A2 > A1), i.e. "A1 ≥ A2" → no catfish effect at pilot scale.
  - Any other combination is reported as "none of the declared branches", with the pattern described.
  - A1 vs A0 and A2 vs A0 are read separately with the same rule.

## Learner (A1/A2/A3)
- Heads, fixed order `(B, E, H)`: `B_u = R_u·dt` (forced to 0 for an unserved user); `E_u = P_sys·dt/U` for every
  user, served or not (the declared D-2 adaptation, kept per Amendment 1 item 7); `H_u = 1` iff the user's class is
  `INTER_SATELLITE`. An unserved user's own step is class NONE (0); its re-entry is charged by the environment as
  inter-satellite.
- **gamma = 1.0, true terminal at step 10** (Amendment 1 item 1). The 112-dim encoding carries **no step index**, so
  A1-A3 append **one feature, the normalised remaining steps `(T − t)/T`** (1.0 at t = 0, 0.1 at t = 9). The state is
  113-dim. A0 stays 112-dim, eq. (16), gamma 0.9.
- **Units.** Replay stores raw `(B, E, H)`. At sample time rewards are divided by fixed units `(s_B, s_E, 1)`, where
  `s_B`, `s_E` = MAX_NOMINAL_GAIN's pooled bits and joules per user-step on the calibration seeds, measured once
  before training together with `eta_0`. The score is `Q̃_B − η̃ Q̃_E − λ Q̃_H` with `η̃ = eta·s_E/s_B`, a positive
  rescaling of `Q_B − eta Q_E − λ s_B Q_H`. So `eta` stays in bit/J, and **λ is in units of `s_B` bits per
  inter-satellite handover** ("λ in the units of `Q_H`"). With these units `η̃_0 = 1` exactly.
- Targets: `y_k = r_k/s_k + Q^tgt_k(s', a*)·(1 − done)`, `a* = argmax_legal [Q^tgt_B − η̃ Q^tgt_E − λ Q^tgt_H](s')`
  with the **current** eta and lambda. Target networks are used, never Double-DQN.
- Networks, optimiser and hyperparameters come from the frozen R2 record, unchanged: 3 × `DQNNetwork` (100, 50, 50)
  tanh; Adam; lr 0.001 (the frozen main run's value); batch 128; replay 50,000; hard target sync every 50 episodes;
  one update per decision step; P-03 transition filtering exactly as MODQN (no-op and empty-next-mask transitions are
  not stored).
- **Epsilon, identical for all four arms including A0**: the baseline shape (linear 1.0 → 0.01, then flat) compressed
  by 1000/9000, so the decay spans `round(2000·1000/9000) = 222` episodes.

## Sources (A2 CF3, A3 NULL3)
- C1 `A m=2dB`, C2 `A m=12dB`, C3 `B1_NO_NEW_BEAM` are FEASFRONT's `frontier.py` rules **including its fallback
  fix**: at m = 0 the rule is a plain restricted argmax, so no incumbent hold undoes the B1 restriction. Parity with
  `frontier.py` is tested. NULL3 draws uniform legal actions from its own generator `default_rng(train_seed+80_000+k)`.
- Each source has its **own environment copy**, built fresh, reset every main episode with generators seeded with the
  **same seed values** as the main (`env_seed`, `mobility_seed`). After episode 0 the streams diverge from the main's,
  because fading draws depend on the actions taken. The source steps once per main step in lockstep, and pushes
  unshaped raw `(B, E, H)` transitions into **its own buffer (capacity 50,000)**.
- **Common vector replay (Amendment 1 item 2).** One minibatch trains all three heads: **113 main rows + 5 rows from
  each of C1, C2, C3**. Integerisation: `round(128/27) = round(4.74) = 5` per source, and the main replay takes the rest
  (source share 15/128 = 11.7% against a nominal 1/9). Main rows are drawn with the trainer's generator exactly as
  MODQN draws them. Source rows are drawn with a separate generator `default_rng(train_seed+70_001)`, so with rho = 0
  the trainer is bit-identical to A1 (tested). An update runs once the main replay holds ≥ 128 and each source buffer
  holds ≥ 5. The C1↔Q_B, C2↔Q_H, C3↔Q_E association is each source's objective, **not** a data restriction.

## eta / lambda schedule (declaration + Amendment 1 item 3)
- Calibration readings at episodes 250, 500, 750 and 1000: greedy deployed rule, 24 calibration episodes,
  per-episode reseeded.
- **lambda**: `λ ← max(0, λ + 1.0·(H_inter − 0.6016))`, applied at 250, 500 and 750, starting from `λ_0 = 0`.
- **eta**: held at `eta_0` through episode 500. It is updated to the measured pooled EE at **500** (only after the
  learning check passes) and again at **750**.
- The reading at 1000 is **recorded, not applied**. The final checkpoint deploys the eta and lambda that were in force
  during episodes 750-1000, i.e. the ones its networks were trained under.

## Learning check (coordinator, pre-launch)
- The reference is `RANDOM_MASKED` pooled EE on the 24 calibration episodes, computed once before training on the
  same host and pinned archive, and recorded in `PROGRESS.md`.
- At the episode-500 reading, each A1 seed writes its greedy calibration pooled EE to `<root>/learning-check/`. Every
  A1/A2/A3 process waits until all three A1 values exist, and then applies the check.
  - If A1 beats RANDOM on ≥ 2 of 3 seeds, all CF processes continue and apply the eta update.
  - Otherwise every A1/A2/A3 process saves its policy and logs and exits with status `stopped-learning-check`. A0 is
    not gated and keeps running.
  - I then report and wait. I do not debug or relaunch.

## Pre-launch source screen (Amendment 1 item 4; no training)
Rollouts of `TRAINED e6b063ef`, `A m=2dB`, `A m=12dB`, `B1_NO_NEW_BEAM`, `RANDOM_MASKED` (plus MAX_NOMINAL_GAIN for
eta_0), 24 calibration episodes each, per-episode reseeded, pinned archive. Operational stop rule:
- A source violates **C-H** if its `H_inter` > 0.6016.
- A source violates **C-S** if its served fraction is more than 0.5 pp below TRAINED's on the same episodes. This is a
  point estimate: there is no no-catfish reference before training, so the frozen learned policy stands in.

## C2 activation (Amendment 1 item 5)
The report gives:
- the lambda trajectory per seed;
- the fraction of training episodes with λ > 0;
- the fraction of evaluation decisions (users with a non-empty mask, all 24 × 10 × 100) whose greedy argmax changes
  when the `−λ Q_H` term is removed.

If λ = 0 throughout and that fraction is < 1%, C2's head is classified **INACTIVE** in this pilot.

## ΔE_sys diagnostic (Amendment 1 item 7; no training)
- Roll out C3 (`B1_NO_NEW_BEAM`) on 3 calibration episodes.
- At every step, for every user whose incumbent is legal and differs from C3's choice, evaluate the step twice with
  the environment's counterfactual `evaluate_actions` (common random numbers, no state committed):
  - once with C3's action vector;
  - once with that user moved back to its incumbent, holding every other user's action fixed.
- Record `ΔE_sys = E(C3 choice) − E(incumbent)` in joules per step, and report its distribution (quantiles, share
  within ±1% of the step's joules). This is reported only; it gates nothing.

## Smoke and the 100-episode diagnostic
- **Smoke** (every arm, 3 episodes, separate root): quarter length 1, eta from episode 2, 2 calibration episodes. This
  exercises one lambda update, one eta update, the learning-check barrier and one evaluation. The smoke timings project
  the wall time.
- **100-episode diagnostic**: the real A1/A2/A3 seed-0 runs, with the production config, stop cleanly at episode 100.
  From their state I report:
  - per-head Q scale;
  - each term's share of the transformed score;
  - C2 activation;
  - CF3 vs NULL3 batch composition.

  This is a check, not a result. The full launch then **resumes** those three runs from their episode-100 boundary
  (resume is bit-identical, tested) and starts the other nine from 0.

## Compute
- 12 concurrent training processes (4 arms × 3 seeds) on `sat`, `nice -n 10`, BLAS/OMP threads 1, `systemd-run
  --scope -p MemoryMax=5G`, plus an in-process RSS check at 5 GB. `setsid nohup`, detached.
- Checkpoints every 100 episodes: a resume state plus a preserved policy checkpoint.

---

## Additions after Amendment 2 and later coordinator messages (still before launch, ~10:25 UTC server time)

Governing: `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-2-EE-ONLY-2026-09-11.md`
(supersedes the C-H and lambda parts of everything above), plus coordinator messages of ~10:15-10:22 UTC (readings at
100/250/500/750/1000 with AUC, `H_intra` beside every EE, seeds 3-4).

**A. lambda fixed at 0 for A1/A2/A3 (Amendment 2 item 1).**
- `CFRatioSettings.dual_ascent = False` (the default): lambda stays exactly `λ_0 = 0`. The action rule is
  `argmax_a [Q_B − eta·Q_E]`. `Q_H` is still trained on `H` and logged, but it is out of the argmax.
- Tested: lambda is exactly 0 in every log and every trajectory row even with the cap set to 0. The mutant
  "dual ascent on" goes red.
- The lambda paragraphs above (λ update at 250/500/750, the C2 INACTIVE classification) are **void**. eta is
  unchanged: held at eta_0 through 500, then updated at 500 (after the learning check) and at 750.

**B. C-H is information only (Amendment 2 item 1).**
- Every EE figure is reported beside `H_inter`, `H_intra` and handovers per user-minute. Handovers per user-minute =
  `(H_inter + H_intra) · 60 / 30.08`.
- For each arm and seed I state whether it would have met 0.6016. It is not a pass/fail.
- The declared reading drops C-H: **branch (1) = A2 > A3 and A2 > A1 and C-S non-inferior.** Branches (2) and (3)
  are unchanged.

**C. C2 diagnostic replacing INACTIVE (Amendment 2 item 3).**
- This runs offline, on each A1-A3 final checkpoint, on the evaluation episodes.
- If `H_inter ≤ 0.6016` at lambda = 0, then `λ* = 0` and no decision changes.
- Otherwise I find `λ*` (in the heads' units): the smallest lambda whose greedy rule has `H_inter ≤ 0.6016`, by
  doubling from 0.01 and then 12 bisection steps. I report the fraction of the lambda = 0 rollout's decisions whose
  argmax differs at `λ*`. This is not a gate.

**D. Training seeds 3 and 4 for A1, A2, A3.**
- The new triples are `(45,1340,10)` and `(46,1341,11)`. A1-A3 have 5 seeds each; A0 stays at seeds 0-2. That makes
  18 processes.
- **The learning check stays as declared, over A1 seeds 0-2.** Seeds 3-4 wait on and obey the same decision.
- **The reading rule with unequal seed counts:**
  - X > Y iff the mean over all of X's seeds exceeds the mean over all of Y's seeds, **and** X beats Y on a majority
    of the same-index seed pairs both arms have: ≥ 3 of 5 for A1/A2/A3 comparisons, ≥ 2 of 3 when A0 is involved.
  - The C-S bootstrap pools each arm over all its seeds, with the same episode clusters.
  - Every seed is reported individually.

**E. Learning-speed readings (coordinator).**
- For every arm and seed I report the greedy calibration-seed pooled EE, with `H_inter`, `H_intra` and served beside
  it, at episodes **100, 250, 500, 750 and 1000**:
  - 100 is a read-only reading, taken in-process at the end of episode 100; it consumes no training RNG.
  - 250/500/750 are the quarter readings.
  - 1000 is the recorded-not-applied final reading. For A0 all five are read-only readings.
- The **area under that curve** is taken by trapezoid over episodes 100→1000, and also reported divided by 900
  (= the time-averaged EE over the window). I give it per seed and per arm mean.
- These are reported **beside** the declared final-checkpoint reading, which is still the only one the declared
  reading applies to.

**F. One TLE archive instance per process (memory, no number changes).**
- In the 100-episode diagnostic stage, A2/A3 reached 3.9 GB RSS at episode 100, still rising. The cause:
  `TleArchive` caches every parsed daily file without bound, per instance, and each of the 4 envs had its own
  instance.
- All envs in a process (main, sources, calibration/evaluation envs) now share one `TleArchive`.
  `cf_ratio.make_env_on` is `make_training_environment` statement for statement, with the archive passed in.
- Parsed files are immutable (tuples). **Tested bit-identical:** rollouts on a shared, warm archive equal
  `make_training_environment` rollouts (epochs, bits, joules, handover classes). A split mutant goes red.

**G. What happens to the 100-episode diagnostic runs.**
- The A1/A2/A3 seed-0 runs that stopped at episode 100 ran on code before Amendment 2. The difference is the settings
  fingerprint; λ was 0 throughout, since there was no quarter before 100. They also used unshared archives.
- The diagnostic report is computed from them (a check, not a result). The runs are then moved aside to
  `ws/runs-diag100-preA2/`.
- **The full launch starts all 18 runs from episode 0** on the final tree. Nothing is resumed across the code change.

---

## Additions after the 10:40 hold (before the fresh launch; no result of any launch exists)

**H. 12 runs, not 18 (compute; coordinator, 10:45 UTC). This reverts D.**
- The fresh launch is A0/A1/A2/A3 × seeds 0-2. Seeds 3-4 are deferred to a possible second wave.
- The reason is compute: 18-way contention on this CPU (8 P + 12 E cores) slowed each process about 3×.
- The declared reading uses seeds 0-2 with the **original 2-of-3 rule**: X > Y iff the seed-mean pooled EE is higher
  and X beats Y on ≥ 2 of the 3 same-index seed pairs. C-S is pooled over seeds 0-2.
- The learning check is unchanged (A1 seeds 0-2).
- The 10:25 launch (stopped at 10:40) is not a result and is not resumed.

**I. Amendment 3 — pre-generated source pools replace streaming source environments.**
(`V025-CONTROLLER-AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md`)
- **Generation.** Before training, for each training seed k ∈ {0,1,2} and each of the six sources (C1/C2/C3 for A2;
  NULL1/2/3 for A3), the source is rolled for **100 episodes**. Each episode runs on a fresh env (shared archive),
  with pool seeds `env = 9_141_000 + 1000k + i` and `mobility = 9_161_000 + 1000k + i`, i = 0..99.
  - These are disjoint from training, calibration, evaluation and RANDOM seeds. No pool env seed equals any pool
    mobility seed. A first generation with mobility base 9_142_000 collided with the k = 1 env seeds; it was stopped
    before any pool finished and discarded (`ws/pools-superseded-seed-overlap-99252ef8`).
  - NULL source j draws uniform legal actions from `default_rng((9_151_000, k, j, i))`.
  - Transitions carry raw `(B, E, H)`, the 113-dim observation, and the same P-03 filtering as the main replay.
  - **A2 and A3 pools of the same k use identical seeds and differ only in the policy** (tested). Each pool is
    ≈ 100,000 transitions.
- **Use.** Each source buffer is an immutable `PoolBuffer` (read-only arrays), loaded once per run and never
  appended. Rows are sampled uniformly without replacement by the separate source generator. The minibatch is still
  113 main + 5 × 3 sources. Pool sha256 values are in `RUN-MANIFEST.json` and in every run's fingerprint, and both
  launch and resume fail closed on any mismatch.
- **The one declared behavioural difference:** with streaming, source buffers started empty and filled over roughly
  the first 50 episodes. With pools, **source rows are available from the first update** (episode 0). This holds
  equally for A2 and A3.
- No source environment exists in any training process any more, so A2/A3 should run near A1's speed.

**J. Launch control (external review; each item verified real before fixing).**
- **Gate failure path.**
  - `train_cf` now appends the gate episode's log and runs the callback before re-raising `LearningCheckStop`. A
    stopped run therefore ends at exactly the gate episode: completed = 500, next_episode = 500, 500 logs.
  - Forced-failure test at gate episode 2 → logs `[0, 1]`, eta not updated. The old ordering is kept as a mutant,
    and that mutant fails the test.
- **DECISION.json.**
  - A single writer: whichever process first creates `DECISION.lock` with `O_EXCL` computes the decision, writes a
    PID-unique temp file, and renames it into place.
  - The decision and each A1 reading carry a gate fingerprint (code digest, calibration sha, TLE sha, gate episode,
    RANDOM reference, gate seeds). Any mismatch fails closed.
- **Missing A1 readings or decision** = a loud failure (`GateUnavailable` → status `failed`, relaunchable), never a
  stop. A run's `stopped-learning-check` is terminal (for both the launcher and the driver) **only** if
  `DECISION.json` exists and records `pass = false`.
- **Code identity.**
  - The fingerprint and root `RUN-MANIFEST.json` carry the tree commit, sha256 of `cf_ratio.py`, `cf_sources.py`,
    `modqn.py`, the driver, `cf3_common.py`, the launcher, the declaration and Amendments 1-2 (copied into the tree
    under `docs/cf3-pilot/`), plus a whole-`src` hash.
  - Launch and resume fail closed on mismatch.
  - The manifest also covers Amendment 3 and `cf3_pools.py`; each pool's sha256 is listed separately.
- **Launcher `scripts/cf3_launch.py`.** It replaces `launch.sh`:
  - it plans exactly the expected unique set (12) and prints the plan first;
  - liveness = the PID exists **and** its cmdline is this driver with the same arm/seed/root **and** its cwd is the
    tree;
  - it fails loudly if any launched process is not alive after 10 s;
  - `--verify` checks every status fingerprint's code digest.
- **`--stop-after`** raises its own exception. An unexpected `StopIteration` is no longer reported as a clean stop.

**K. Memory.**
- The separate saturated-buffer check is **not run**. With pools there are no source environments in a training
  process: a CF process holds 1 env, the shared archive cache, 3 read-only pools of about 100 MB each, and the main
  replay.
- As the coordinator allowed, A2/A3 get `MemoryMax=7G` and an in-process RSS cap of 6.5 GB. A0/A1 keep 5G / 5 GB.
- RSS is logged at every checkpoint.

---

## Post-launch note (11:25 UTC; after the 11:14:42 launch and before any result of it)

The coordinator corrected Amendment 3 after an external review (`gpt5.md`). The correction is in the header of
`V025-CONTROLLER-AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md`. **The sentence in section I above, "source
rows are available from the first update (episode 0)", is imprecise.**
- The streaming buffers already held about 200 rows by the first update.
- The real difference is that a pool offers its **full 100-episode support from update one**, where streaming
  offered only the first one or two source episodes. It is a change from online streaming (a moving FIFO) to
  **static offline source replay**.
- The pool size of 100,000 is a chosen size, not one derived from the draw count.

The report reads A2 vs A1 as "does static directed-data prefill help", not as online catfish. Nothing in the running
design changed. Pool sidecar hashes were bound and are re-verified at evaluation (PROGRESS, 11:25 UTC).
