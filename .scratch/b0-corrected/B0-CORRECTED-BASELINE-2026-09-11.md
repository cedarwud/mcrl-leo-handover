**All ruling items 1–5 have landed on `wip/multi-catfish-v023-20260907`, each with tests that failed first and then passed, and the full test suite shows no regressions. D-1 is now a flag whose default is MODQN eq. (16) (bit-identical to the pre-`5219995a` code), D-2 floors an outage at the worst served value of its own step, and the TLE archive is pinned by hash with a random-arm placebo that is bit-identical on both hosts. `READY FOR PILOT: 363845e8` is posted. The item-6 reruns were cancelled by controller instruction, but they had already finished when that instruction arrived, so their results are recorded below as smoke only.**

2026-09-11. Worker: B0CORRECT. Ledger: `.scratch/b0-corrected/PROGRESS.md`. Controller ruling: `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-RULING-B0-THREE-QUESTIONS-2026-09-11.md`.

> **Smoke only.** Every pilot number here comes from **500 of 9,000 episodes**, at ε = 0.753, on one seed set. None of it is an experimental arm or a claim, and none of it may be compared with any checkpoint's *final* performance.

---

# ROUND 2 — the controller ruling, items 1–6

## R.0 Status at a glance

| ruling item | state | commit(s) on `wip/multi-catfish-v023-20260907` |
|---|---|---|
| 5a. PENALTYARM's port, as its own commit | done; its 8 off-path tests pass | `f531ff99` |
| 5b. B0 commits brought onto the shared branch | done via `cherry-pick -x`, no conflicts | D-2 v1 `ee0ffa60`, D-3 `698f20d8`, D-3 fixup `6939fc78`, pilot scripts `ff01f84d` |
| 1. D-1 as a flag, default eq. (16), W-08 restored | done; bitwise placebo passes | `57fb40b4` |
| 2. D-2 per-step worst-served floor | done; 4 sub-tests failed first | `c00aca3e` |
| 3. Checkpoint selection | none; selection is unreachable (see R.3) | — |
| 4. TLE archive pinned by hash, placebo | done; bit-identical on both hosts | `b924c8a0`; eval harness `363845e8` |
| 5c. Throwaway worktree `/home/u24/papers/mcrl-b0-baseline` | removed after confirming it held nothing unique | — |
| 6. 500-episode reruns | **cancelled by controller instruction; both runs and their eval had already finished when it arrived**, so the results are recorded in R.6 as smoke only (they duplicate CF3PILOT's 1000-episode eq. (16) arm) | — |

**`READY FOR PILOT: 363845e8`** is written at the top of `PROGRESS.md`. Every commit listed above is an ancestor of it.

**Full regression at the shared-branch head** (after `363845e8`): 55 failures, exactly the same test IDs as the pre-D-1 baseline `e3f3503e`, so round 2 introduced **zero** regressions. The pre-existing failures are all in stage-C `ee_axis_*`, the R7 control plane, v03b and G-6; my touched files contain none of G-6's forbidden tokens.

## R.1 D-1 is a flag, and the default is MODQN eq. (16)

- **The flag:** `TrainerConfig.td_bootstrap_mode`.
  - `"eq16-per-head-max"` is the **default** (B1 / SDD §8, the published MODQN baseline).
  - `"shared-continuation-argmax"` is the successor learner's target.
  - Any other value is refused by `validate_trainer_config`.
- **Default path.** Inside `update()`, the per-objective target block is statement-for-statement the pre-`5219995a` code, and nothing else runs on that path. The shared rule lives in `MODQNTrainer._shared_continuation_action` and is called only when the flag is on. Weights come from `cfg.objective_weights`, never a literal.
- **Tests:**
  - `tests/test_w08_vanilla_td_target.py` is restored byte for byte from `5219995a^`, so the three amended assertions are back and guard the default path's source.
  - `tests/test_b0_d1_scalarised_bootstrap.py` runs the D-1 tests with the flag on, and adds default-path tests:
    - eq. (16) is the default;
    - on the disagreeing fixture, each head takes its own max;
    - `_shared_continuation_action` is never called (monkeypatched to raise);
    - an unknown mode is refused.
- **Bitwise placebo.** Identical replay contents, 25 `update()` calls including one target sync:

  | comparison | parameters and losses |
  |---|---|
  | current code, flag **off**, against pre-`5219995a` | **bit-identical** |
  | current code, flag **on**, against `5219995a` | **bit-identical** |
  | flag on against pre-`5219995a` (teeth check) | **different** |

- **PENALTYARM's arms ran on `5219995a`**, so they are the shared-bootstrap variant, not the eq. (16) baseline. This is recorded in the commit message of `f531ff99` and of `57fb40b4`.

## R.2 D-2: the floor is the worst served value of the same step

**Rule.** An unserved user scores:
- **r2 = −PHI2 = −1.0**;
- **r3 = the minimum r3 over served users in that step**, which equals **−max_b U_b(t)**.

**Why those two r3 expressions are the same number (verified by reading and by test).**
- `ServiceResolution.eligible_load_by_beam` counts **served users only**, after the feasibility check.
- So every lit beam carries at least one served user whose r3 is −U_b.
- The floor is cheaply available where the reward is formed: the whole step's `RewardComponents` and its `served` tuple are on the `StepResult`. It is computed once per step and cached on the result object's identity.
- A step in which **nobody** is served has no served value to floor at, so it **raises** rather than approximating one. That never happened in either pilot.

**Other changes in this commit.**
- The −num_users path is removed.
- `EpisodeLog.outage_user_steps` records the floored user-steps, so the floor's share of the signal is now measured rather than inferred. The stdout progress line prints it as `out=`.

**Tests** (`tests/test_b0_d2_outage_floor.py`, rewritten).
- Four sub-tests failed first against the −100 trainer:
  - the floor did not equal the per-step minimum;
  - an outage beat a served user (−2 against −3 in the fixture);
  - a step with nobody served did not raise;
  - on real physics, −100 did not equal −max_b U_b.
- 9/9 pass after the fix. They include:
  - a real-environment check that on every outage step the floor equals −max_b U_b from the physics' own loads, and that every unserved user scores at or below every served user on both heads;
  - a test that the episode log counts exactly the floored user-steps.

**Effect, measured in the 500-episode logs.** The floor no longer dominates the r3 head.
- Calibrated r3, episodes 400–500: **−2.58** (BASELINE_EQ16) against **−2.36** for the unfloored frozen run. That is about 9% of the head, down from about 78% under the −100 floor.
- r3 loss is back to frozen-run scale: 0.05–0.07, against 0.048 for the frozen run and 5.7 under the −100 floor.
- **Training-time outages: 27,331 of 500,000 user-steps (5.47%) in BASELINE_EQ16, and 27,382 (5.48%) in SHARED_BOOTSTRAP.**

## R.3 Checkpoint selection: none

- The best-eval path only switches on if something passes `evaluation_seed_set` to `train()`. **Nothing in `src/`, `scripts/` or `tests/` does**, so it cannot be reached.
- The primary checkpoint is `final-episode-policy`, and `prereg_draft.py:497` already keeps selection out of the headline.
- Scoring in the selection path was left as it is, per the ruling. **Every arm is evaluated at its final checkpoint.**

## R.4 The TLE archive is pinned by content hash

**Cause of the host disagreement (verified by hashing both archives):**

| host | `~/demo/tle_data/starlink/tle` | files | `file_set_sha256` | status |
|---|---|---|---|---|
| sat | symlink to `/home/sat/mcrl-runtime/tle-frozen-20260820` | 373, from 2025-07-27 to 2026-08-20 | **`427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`** | equals the frozen R2 prereg's `ephemeris.file_set_sha256`. The frozen run validated against it. **Pinned.** |
| local | real directory | 392: the same 373 files, byte-identical, **plus 19 later days** (2026-08-21 to 2026-09-08) | **`e07f3e1e879dafd28863e2b0178acc3186e3eea70e319e1046b56b4329a093e4`** | not the frozen archive |

- The extra days move the archive's date range. That shifts the block-alternating split and the episode-start sampler, so the same seed draws different epochs.
- **The ruling asked for "the archive both the frozen run and the catfish-surface harness used". There is no such archive: they used different ones.** I pinned the frozen run's archive, because it is the one the prereg freezes.

**The pin.**
- `training_pipeline.resolve_tle_root()` uses `MCRL_TLE_ROOT` if it is set, otherwise the previous default. Behaviour is unchanged when the variable is unset.
- `assert_tle_archive_pinned()` refuses any archive whose `file_set_sha256` is not the canonical prereg's value. The value is read from the prereg, not written out a second time.
- The pilot driver and the eval harness both call it, and both record the hash.

**Pinned copies** (the shared originals were never modified):
- sat: `/home/sat/mcrl-v025-b0-ws/tle-pinned-427e6a91`
- local: `/home/u24/mcrl-runtime/tle-pinned-427e6a91`

Both contain 373 files, each sha256-checked against the frozen rows. Both give `file_set_sha256` `427e6a91…` and `sha256sum starlink_*.tle | sha256sum` = `c0f02cc784683d2fc08ae3d4542fb43c5129b74b254a17b458ddef31d8c78317`.

A side effect: with the pinned root, the full `validate_server_setup` now passes locally too. It used to fail there because of the 392-file archive.

**Placebo, verified: RANDOM_MASKED is bit-for-bit identical on both hosts** (N_EP = 24, seeds 42/1337/7). Every field matches exactly:
- pooled EE **52,420,510.0956937 bit/J**, bits 181,834,363,529,850.12, joules 3,468,763.7185886074;
- all 24 per-episode EEs;
- served fraction 0.9358333…;
- outages 1,540;
- φ1 = 4,472 and φ2 = 16,395 handovers;
- all six head means;
- the archive hash.

## R.5 A defect in the inherited eval harness driver: arms were not at matched conditions

- **The defect.** The catfish-surface `pooled_ee.py` driver built **one** module-level `env` and ran every arm on it. `StepEnvironment` owns a persistent cross-episode stream, `_age_rng` (the segment warm-start ages). It is spawned once per environment object and is **not** reset by `reset()`. So only the first arm ran at age-stream positions 0–23; every later arm ran further along the stream.
- **The fix, `363845e8`.** `_fresh_env()` builds a new environment before every run. The harness core, lines 53–143, is still byte for byte.
- **A new check.** `run_extended()` adds the φ1/φ2 split, the outage count and the greedy head means. For every arm the driver also re-runs the verbatim `run()`, and aborts unless every shared field agrees exactly and φ1 + φ2 equals the verbatim handover count. This held for all 5 arms.
- **Size of the effect (measured).** Re-scoring the round-1 episode-500 checkpoints with fresh environments:

  | checkpoint | round 1 (shared env) | fresh env | change |
  |---|---|---|---|
  | UNFIXED_EP500 | 79,567,896 | 80,539,818 | +1.22% |
  | B0_EP500 | 77,365,317 | 77,302,059 | −0.08% |

  The round-1 gap (−2.77%, unpaired) becomes **−4.02% (paired t = −2.29)**. Arm order moved numbers by about 1%, which is the same order as the differences being compared.
- **This affects the catfish-surface document's five-arm table.** It ran RANDOM, then MAX_NOMINAL_GAIN, GREEDY_SCALARIZED, GREEDY_R1R2 and TRAINED, on one environment, so only RANDOM was at positions 0–23. Its "no age-stream caveat applies" statement for the trained arm is therefore wrong. I have not re-measured that table.

## R.6 Item-6 reruns: cancelled by controller instruction, recorded as smoke only

Both runs and their eval had completed before the cancellation arrived, and no further server runs were started.

**Setup.** Both arms used:
- sat, the pinned archive, and a server validation that passed;
- 500 episodes, seeds 42/1337/7, learning rate 0.001, with D-2 (per-step floor) and D-3;
- checkpoints every 100 episodes, under `sat:/home/sat/mcrl-v025-b0-ws/r2-pilot-{BASELINE_EQ16,SHARED_BOOTSTRAP}-500/`.

The only difference is the bootstrap mode: BASELINE_EQ16 has the flag off, SHARED_BOOTSTRAP has it on.

**Stability: clean.** Every log value was finite in all 500 episodes of both arms, and no no-op or all-invalid-next transitions were dropped. Peak loss per head:

| arm | r1 | r2 | r3 |
|---|---|---|---|
| BASELINE_EQ16 | 0.365 | 0.436 | 0.061 |
| SHARED_BOOTSTRAP | 0.298 | 0.481 | 0.088 |

**Checking the trajectories (verified).**
- At episode 0 (ε = 1), BASELINE_EQ16's r1 and handover count equal the frozen run's exactly. The r2/r3 gap is exactly the floor on 62 outages.
- BASELINE_EQ16's r1 first departs from the frozen run at episode 6, as the floor starts to change learning.
- SHARED_BOOTSTRAP's r1 first departs from BASELINE_EQ16 at episode 11.

**Training-time head means.** ε-greedy behaviour policy; calibrated by `(2029238.43, 1, 6)`; per user per episode. The reference is the frozen run's own logs over the same episodes, which have no D-2 floor, so their r2/r3 are not like-for-like.

| arm | episodes | r1c | r2c | r3c | calibrated scalar | handovers per user-step | outages per user-step |
|---|---|---|---|---|---|---|---|
| BASELINE_EQ16 | 0–100 | 2.707 | −8.313 | −2.486 | −1.638 | 0.866 | 0.0615 |
| BASELINE_EQ16 | 400–500 | 3.096 | −7.464 | −2.582 | −1.208 | 0.809 | 0.0494 |
| SHARED_BOOTSTRAP | 0–100 | 2.707 | −8.318 | −2.485 | −1.639 | 0.866 | 0.0615 |
| SHARED_BOOTSTRAP | 400–500 | 3.135 | −7.502 | −2.579 | −1.199 | 0.813 | 0.0491 |
| frozen `e6b063ef` (no floor) | 400–500 | 3.128 | −6.993 | −2.362 | −1.006 | 0.811 | not logged |

**Greedy evaluation of the episode-500 checkpoints.**
- Method: `scripts/b0_pooled_ee_eval.py` at `363845e8`, run on sat on the pinned archive, with a fresh environment per arm. ε = 0, 24 episodes, seeds 42/1337/7, no `update()` calls.
- Estimand: pooled EE = Σ bits / Σ joules over 24 × 10 steps, divided once. Bits and joules come from `env.last_outcome.energy`.
- Handovers are counted from the environment's own φ classes.
- Head means and the scalar are calibrated, and use the **per-step-floor definition for every arm**.

| arm | pooled EE (bit/J) | bits (numerator) | joules (denominator) | vs RANDOM | served fraction | outage user-steps of 24,000 | handover rate | φ1 rate | φ2 rate | r1c | r2c | r3c | calibrated scalar ± sem |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RANDOM_MASKED | 52,420,510.10 | 1.818344e14 | 3.46876e6 | 1.000 | 0.93583 | 1,540 | 0.8695 | 0.1863 | 0.6831 | 2.695 | −8.405 | −2.472 | −1.668 ± 0.012 |
| **BASELINE_EQ16_EP500** | **85,976,978.04** | 2.068290e14 | 2.40563e6 | 1.640 | 0.99817 | 44 | 0.1845 | 0.0014 | 0.1831 | 4.168 | −1.856 | −4.487 | +0.630 ± 0.035 |
| **SHARED_BOOTSTRAP_EP500** | **85,155,822.09** | 2.371863e14 | 2.78532e6 | 1.624 | 0.99867 | 32 | 0.1720 | 0.0005 | 0.1715 | 4.146 | −1.731 | −3.720 | +0.810 ± 0.031 |
| round-1 B0_EP500 (−100 floor, D-1 on) | 77,302,059.46 | 1.807943e14 | 2.33880e6 | 1.475 | 0.99958 | 10 | 0.1517 | 0.0015 | 0.1502 | 3.758 | −1.514 | −4.634 | +0.498 ± 0.042 |
| round-1 UNFIXED_EP500 (= frozen run at episode 500) | 80,539,817.53 | 1.943160e14 | 2.41267e6 | 1.536 | 0.99608 | 94 | 0.1727 | 0.0000 | 0.1727 | 3.953 | −1.766 | −4.383 | +0.570 ± 0.033 |

Four fields for every row:
- **Reference:** RANDOM_MASKED, and the pairs compared below.
- **Information class:** deployed greedy policy on realised physics, pinned archive, one development seed set.
- **Estimand:** ratio of sums. The ± value is per-episode sem, n = 24.
- **Numerator and denominator:** in their own columns.

Paired comparisons use the same 24 episodes and seeds with fresh environments.
- **SHARED_BOOTSTRAP against BASELINE_EQ16:** EE **−0.96%**, paired t = −0.42, **not resolved**. SHARED draws 14.7% more bits and 15.8% more joules.
- **BASELINE_EQ16 against round-1 UNFIXED (the frozen run at episode 500):** EE **+6.75%**, paired t = +2.96. This isolates what the per-step D-2 floor does to the eq. (16) learner by episode 500. It is **one seed, early training (ε 0.753), and not a claim.**
- **Round-1 B0 against round-1 UNFIXED:** EE −4.02%, paired t = −2.29. This is the corrected version of round 1's −2.77% (see R.5). Its floor definition has since been superseded.
- φ1 handovers are rare under every greedy policy (≤ 0.15% of user-steps). Almost all handovers are φ2, because the policies pick across satellites.

---

# Which figures were measured on the UNPINNED archive — do not compare with pinned-archive numbers

The unpinned archive is local `~/demo/tle_data/starlink/tle`, `file_set_sha256` `e07f3e1e…`, 392 files. The pinned one is `427e6a91…`.

| figure | archive | notes |
|---|---|---|
| **Every harness number in `.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md`**: the pooled-EE table (RANDOM 53,060,175.56; GREEDY_SCALARIZED 75,272,421.21; GREEDY_R1R2 75,817,283.47; **TRAINED `e6b063ef` 93,137,893.02**; MAX_NOMINAL_GAIN 111,553,182.85; the 1.1977× ratio and the 13.2-sem gap), the κ sweep, the five-arm panel, the n = 24 reruns, and every calibrated scalar measured by running that harness | **UNPINNED** | Run locally. Everything after the first arm is also affected by the arm-order defect (R.5). |
| Everything derived from the catfish-surface harness, including FEASFRONT's local 93.11M / 112.46M (per the ruling) and any comparison against them | **UNPINNED** | |
| My round-1 local harness check (RANDOM 53,060,175.56) and my round-1 local smoke runs | **UNPINNED** | |
| The frozen run `e6b063ef` itself and its `episode-logs.json` (including the catfish document's quotes from those logs: +0.8859 over the last 100 episodes, and the plateau windows) | pinned | Trained on sat, validated against the frozen record. |
| Round-1 sat pilots (B0, UNFIXED) and the round-1 sat eval | pinned (sat's default is the frozen archive) | The round-1 eval's B0 and UNFIXED arms carry the arm-order defect. Re-scored in R.6. |
| Everything in round 2 | pinned (`427e6a91…`), fresh environment per arm | |

---

# Round-1 statements that are superseded

- **"D-1 makes every head bootstrap at the shared argmax"** is superseded by R.1: D-1 is now a flag, and the default is eq. (16).
- **"D-2 floors r3 at −num_users = −100"** is superseded by R.2 (per-step floor). The round-1 B0 pilot trained under the −100 floor.
- **"B0 against UNFIXED at episode 500: −2.77%, −1.32 sem"** is superseded by R.5/R.6: with fresh environments it is −4.02% paired, and it describes a floor definition that no longer exists.
- **Open questions 1–3 at the end of round 1** are answered by the ruling. Question 4, the worktree cleanup, is done. Branch `b0/corrected-baseline-20260911` and its worktree `/home/u24/papers/mcrl-leo-handover-b0` still exist. All their content is on the shared branch via cherry-pick `-x`, so they are safe to remove.

---

# ROUND 1 (original text, kept for the record; see the superseded list above)


2026-09-11. Worker: B0CORRECT. Progress ledger: `.scratch/b0-corrected/PROGRESS.md`.

> **Read this before quoting any number below.** The pilot is **500 episodes, not 9,000**. At episode 500 the frozen recipe's ε is still **0.753**, and the frozen run's own calibrated scalar was **−1.006** over episodes 400–500 against **+0.886** over 8900–9000. So nothing measured here says anything about a trained policy. It is a smoke and sanity run, **not an experimental arm, and not a claim**. Comparing any number here with the frozen checkpoint's *final* performance is **invalid**, and this report does not do it.

---

## 0. Where the code is, and a concurrency incident

| commit | branch | content |
|---|---|---|
| `5219995a` | **shared** `wip/multi-catfish-v023-20260907` | D-1 fix + test + three amended W-08 assertions |
| `832471ca` | `b0/corrected-baseline-20260911` only | D-2 fix + test |
| `0acd146c` | same | D-3 fix + test + fixture updates |
| `ccbbb048` | same | D-3 fixup (the stdout progress line); revert together with `0acd146c` |
| `923d68b0` | same | pilot driver `scripts/run_b0_pilot.py` + eval `scripts/b0_pooled_ee_eval.py` |

Worktree: `/home/u24/papers/mcrl-leo-handover-b0`. Each fix is its own commit and can be reverted on its own.

**Incident, verified.** While I worked, another agent (PENALTYARM) was writing `src/mcrl/algorithms/modqn.py` and `src/mcrl/runtime/collapse_penalty.py` in the shared tree. One of my pytest runs caught its file half-written (`NameError: PenaltyConfig`), and it committed `ec1f29d3` on top of my D-1 commit. My response:
- I moved all later work to the isolated worktree above. D-2 and D-3 are therefore **not on the shared branch**.
- `git show 5219995a -- modqn.py | grep -ci penalty` returns 0, so none of PENALTYARM's code is attributed to a defect fix.
- I never staged, reverted or edited PENALTYARM's hunks.
- One stray uncommitted line of mine was left in the shared tree: a `num_users` kwarg, in its own hunk with no overlap. I removed it. The shared tree's remaining `modqn.py` diff is entirely PENALTYARM's.

**Relay to PENALTYARM:** it measured on `5219995a`. That means its OFF arm already bootstraps at the shared scalarised argmax (D-1), so it is **not** the frozen per-head-max MODQN of `e6b063ef`. It does not include D-2 or D-3.

---

## 1. The three fixes

### D-1: every head bootstraps at one shared scalarised argmax

- **Site (verified):** in `MODQNTrainer.update`, inside `for obj_idx in range(3)`, the target was `target_nets[obj_idx](ns)` followed by `.max(dim=1)`. That is head *i*'s own maximiser.
- **Fix:** before the loop, compute `a' = argmax_a Σ_i ω_i Q^target_i(s', a)` once, over the masked next actions. Head *i*'s target is then `Q^target_i(s', a')`.
  - The argmax and the gather both use the **target** networks. The online networks are read only at the current state, so this is still vanilla, not Double-DQN.
  - **Weights:** `ω` is read from `cfg.objective_weights`. The default is `(0.5, 0.3, 0.2)`, declared at `runtime/trainer_spec.py:52`. It is the same field `select_actions` reads (`modqn.py`, `w = objective_weights or self.config.objective_weights`). There is no literal.
- **Test** (`tests/test_b0_d1_scalarised_bootstrap.py`): three fixed target rows whose individual argmaxes (actions 0, 1, 2) all differ from the scalarised argmax (action 3). It also covers a masked variant and a variant with changed weights.
  - **Seen failing on the unfixed code: 3 of 4 sub-tests.** The 4th asserts that the fixture really does make the two rules disagree, so it has to pass either way.
- ⚠ **Departure from a frozen ruling. The owner must decide.**
  - SDD §8's forbidden list names "Double-DQN 共用純量化動作" (`README.md:108`, `docs/IMPLEMENTATION-PROMPT.md:41`).
  - `tests/test_w08_vanilla_td_target.py` asserted the per-head max as the **B1** contract, including `"objective_weights" not in update`.
  - B0 keeps the vanilla half and reverses the shared-action half. **B0 is therefore not the published-MODQN control arm that B1 froze.**
  - I amended three W-08 assertions in place and wrote the reason into each. The G-6 grep gate is unaffected: no forbidden token was added, and its existing failure predates D-1.
  - I did not run an adversarial review of B1 before overturning it. The brief ordered the fix and its math is right, but whether §8 still stands is a design ruling, not mine to make.

### D-2: an outage no longer beats service on either bounded head

- **Site.** The brief cites `outage_gate.py:10-27`, which is the docstring that *describes* the inversion. The values themselves come from two places:
  - `env/action_contract.py`: `classify_handover` returns `NONE` for an unserved user, so r2 = 0.
  - `env/service.py`: `user_beam_load()` is 0 for an unserved user, so r3 = 0.

  Every served step instead has r2 ∈ {0, −0.5, −1.0} and r3 = −U_b ≤ −1. (Verified by reading.)
- **Fix, with the exact values.** An unserved user scores the **worst value each bounded head can take for a served user**:
  - **r2 floor = −PHI2 = −1.0**, derived from the frozen `PHI2`.
  - **r3 floor = −num_users = −100.0**, from the declared config value. This is a *loose* bound. A tighter one would need W-13 to freeze a value, and it has not.
  - r1 is left alone.
- No penalty magnitude was invented. The module's deferred re-entry penalty and its "S, PROPOSED" threshold are still undeclared.
- **Placement:** in `MODQNTrainer.reward_vector_from_step_result`, the path into replay and into episode logs, via `outage_gate.apply_outage_floor`.
  - `RewardComponents` and the handover counters are untouched.
  - `StepResult` gains a `served` tuple, filled from `StepOutcome.resolution.served`. If it is `None` the floor is not applied, because the rewards alone cannot tell an outage apart from a served r2 = 0.
- **Test** (`tests/test_b0_d2_outage_floor.py`): one served user at the floor of both heads, one unserved user.
  - **Seen failing on the unfixed code** on the substance: `outage r2=0.0 beats the worst served r2=-1.0` and `assert 0.0 <= -0.5`. That is 2 of 7 sub-tests; the other 5 check values and back-compatibility.
- ⚠ **Effect size. Verified in the pilot, and the owner should look at it.** The loose r3 floor dominates the r3 head while exploration is high:
  - At episode 0 (ε = 1) the raw r3 mean is **−75.28 in B0 against −13.28 unfixed**.
  - Over episodes 400–500 the calibrated r3 is **−10.50 against −2.36**.
  - The r3 loss is about **120–570× larger** than in the unfixed run.
  - *Inferred, not measured:* about 5–6% of training user-steps are outages, so roughly 80% of the r3 signal is the outage floor rather than load balancing.
  - The brief pre-authorised this option. Whether an outage-avoidance effect of this size is acceptable is a design decision.

### D-3: the headline scalar is now the calibrated one

- **Site (verified):** `train()` logged `scalarize_objectives(avg_reward, …)` on the **uncalibrated** means as `EpisodeLog.scalar_reward`, while replay received the calibrated vector.
- **Fix:**
  - `EpisodeLog.scalar_reward_calibrated` is the new headline, Σ ω_j r_j / c_j.
  - `scalar_reward_uncalibrated_deprecated` holds the old number. It was renamed, not repurposed.
  - `scalar_reward` survives only as a read-only property returning the deprecated number.
  - The three `r{1,2,3}_mean_calibrated` fields **already existed** and are now what the headline is computed from.
  - The live `status.json` gains the calibrated scalar and all three calibrated heads.
  - Old resume logs are read into the deprecated field, never into the headline.
- **Test** (`tests/test_b0_d3_calibrated_scalar_log.py`): **seen failing on the unfixed code, 5 of 6 sub-tests.** The one that passed checks that the three calibrated head means are present, and those fields existed before.
- **Fixup `ccbbb048`, found by the pilot.**
  - The stdout progress line in `train()` still read the removed `scalar` variable. No test enabled progress printing, so the first B0 pilot **died at episode 50** with `NameError`. The frozen pipeline's main run prints every 100 episodes, so it would have died at episode 100.
  - I added a test and saw it fail with that same `NameError`. The line now prints `scalar_cal r1c r2c r3c`.
  - The failed run is kept at `sat:…/pilot-b0-500.FAILED-ep50-scalar-nameerror{,.log}`.
- **Not fixed, reported instead.** `_evaluate_one_seed` also scalarises the *uncalibrated* means, and `EvalSummary.mean_scalar_reward` **drives best-eval checkpoint selection**. So any eval-selected checkpoint has been picked on 0.5·r1. Fixing it changes which checkpoint gets selected, which goes beyond the named defect. It is worth a ruling.

### Regression

I ran the full `tests/` suite on B0 and on a clean worktree of pre-D-1 `e3f3503e`. Both fail on the **same 55 test IDs** (a set diff comes out empty), all in stage-C `ee_axis_*`, the R7 control plane, v03b and G-6. **Zero regressions introduced.**

---

## 2. Pilot setup

- **Recipe.** Frozen main-run recipe on sat:
  - R2 prereg (`validate_server_setup` passed on both trees: prereg bytes, probe refreeze, P6 protocol, ephemeris), learning rate 0.001, seeds 42/1337/7.
  - The **only departure is episodes 9000 → 500**. The ε schedule is left frozen.
  - One Python process per arm, `nice -n 16`, threads = 1, systemd `MemoryMax=5G`, peak RSS 2.04 GB.
  - Checkpoints at episodes 100, 200, 300, 400 and 500 are kept under `sat:/home/sat/mcrl-v025-b0-ws/pilot-{b0,unfixed}-500/`.
- **Two arms:**
  - **B0**: commit `ccbbb048`, wall time 785 s.
  - **UNFIXED**: pre-D-1 `e3f3503e`, same driver, wall time 780 s. I added this arm because **no episode-500 checkpoint of `e6b063ef` exists** (only `final-checkpoint.pt`, and the P6 arms use other seeds).
- **UNFIXED reproduces the frozen run: verified.** On all 500 episodes, `r1/r2/r3_mean`, their calibrated versions, `scalar_reward`, `total_handovers`, `replay_size` and `epsilon` are **exactly equal** to `artifacts/training-2026-08-25-rerun01/main/episode-logs.json[0:500]`.
  - Losses differ by at most 3.6e-7 relative.
  - The integer collapse fields are exact. The Q-derived floats differ by about 1e-6 relative or less.
  - No action differed in 500 episodes.
  - *Inferred:* UNFIXED's episode-500 weights equal the frozen run's episode-500 weights to within float noise. I cannot check this directly, because no such weights were ever saved.
  - **UNFIXED_EP500 is therefore the frozen run at the same episode count**, as close as can be had.

## 3. Stability: clean

| arm | NaN or inf in any log | loss max per head (r1, r2, r3) | mean loss over eps 0–100 → 400–500 |
|---|---|---|---|
| B0 | none in 500 episodes | 0.294, 0.481, **37.14** (episode 0) | r1 0.107→0.256; r2 0.075→0.159; **r3 10.30→5.68** |
| UNFIXED (= frozen) | none | 0.432, 0.380, 0.057 | r1 0.113→0.386; r2 0.081→0.079; r3 0.018→0.048 |

- The fail-loud finiteness battery (loss, gradients, parameters) never tripped, and the driver's own finiteness and RSS guards never tripped.
- B0's r3 loss is **large but falling**. It is the Q3 head fitting the −100/6 floor targets, not a divergence.
- **Limit:** gradient *norms* were not logged. "No blowup" rests on finite gradients plus loss trajectories, not on measured norms.

## 4. The three calibrated head means, now visible

Source: ε-greedy **training-time** means from the episode logs (behaviour policy, not greedy). Units: per user per episode, divided by `REWARD_SCALES = (2029238.43, 1, 6)`.

| arm | window | ε at end | r1c | r2c | r3c | calibrated scalar | handovers per user-step |
|---|---|---|---|---|---|---|---|
| B0 | 0–100 | 0.951 | 2.704 | −8.318 | −12.514 | −3.646 | 0.866 |
| B0 | 400–500 | 0.753 | 3.109 | −7.491 | −10.505 | −2.794 | 0.813 |
| UNFIXED = frozen | 0–100 | 0.951 | 2.702 | −7.702 | −2.264 | −1.412 | 0.866 |
| UNFIXED = frozen | 400–500 | 0.753 | 3.128 | −6.993 | −2.362 | −1.006 | 0.811 |

**What D-3 exposes.** Over episodes 400–500:
- The deprecated uncalibrated curve reads **3.154e6 for B0 and 3.174e6 for UNFIXED**. That equals 0.5·r1_raw to within 4.7e-6 and 1.6e-6 relative, so r2 and r3 are invisible in it, exactly as the brief said.
- The calibrated curve reads **−2.79 against −1.01**.
- Weighted contributions for B0: 0.5·r1c = **+1.55**, 0.3·r2c = **−2.25**, 0.2·r3c = **−2.10**. The early objective is dominated by the handover term (exploration churn) and, under D-2, by the outage floor. The old curve could show neither.
- The B0 and UNFIXED **scalars and r2/r3 means are not comparable to each other**, because D-2 changes the reward definition. r1 and handovers are comparable, and they are nearly equal: r1c 3.109 against 3.128, handovers 0.813 against 0.811.

## 5. Greedy evaluation of the episode-500 checkpoints

- **Method:** the catfish-surface harness (`pooled_ee.py` lines 53–143, copied byte for byte and hash-checked). ε = 0 (the deployed policy), 24 episodes, seeds 42/1337/7, no `update()` calls. All arms were scored by the B0 tree on sat, and cross-schema checkpoint loading was verified.
- **Estimand:** pooled EE = Σ bits / Σ joules over 24 × 10 steps, divided once. Both totals come from `env.last_outcome.energy`.
- **Harness validity, verified.** Run locally, the RANDOM arm reproduces the catfish doc exactly: 53,060,175.56 bit/J, served 0.9360, handovers 0.8680. On sat it gives 52,420,510.10, because **sat's TLE archive (the frozen one) is not the local one.** So **none of these sat numbers can be compared with the catfish doc's local numbers, including its `e6b063ef` final of 93,137,893 bit/J.**

| arm | pooled EE (bit/J) | bits (numerator) | joules (denominator) | vs RANDOM | served fraction | outage user-steps (out of 24,000) | handover rate | calibrated scalar (B0 reward definition) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RANDOM_MASKED (harness check) | 52,420,510.10 | 1.818344e14 | 3.468764e6 | 1.000× | 0.93583 | 1540 | 0.8695 | −3.761 ± 0.068 |
| **B0_EP500** | **77,365,317.43** | 1.808679e14 | 2.337842e6 | 1.476× | **0.99950** | **12** | 0.1518 | +0.483 ± 0.042 |
| **UNFIXED_EP500 (= frozen at ep 500)** | **79,567,895.67** | 2.011509e14 | 2.528041e6 | 1.518× | 0.99579 | 101 | 0.1650 | +0.471 ± 0.036 |

Four fields for every row:
- **Reference:** RANDOM_MASKED, and B0 against UNFIXED.
- **Information class:** deployed greedy policy on realised physics, sat frozen archive, development seeds.
- **Estimand:** ratio of sums as above. The ± values are per-episode sem, n = 24.
- **Numerator and denominator:** in their own columns.

**Comparison with the frozen run at the same episode count** (it is available, via the log-identical reproduction):
- **B0 against UNFIXED at episode 500:** pooled EE **−2.77%** (−2,202,578 bit/J). That is **−1.32 unpaired sem**, which does **not** resolve at n = 24. I did not run a paired test.
- B0 produces 10.1% fewer bits and draws 7.5% fewer joules.
- B0 has **fewer outages: 12 against 101 user-steps**. The direction matches what D-2 is for, but it is not a claim, because user-steps within an episode are correlated.
- Handover rate: 0.152 against 0.165.
- Calibrated scalar, scored under the same B0 definition for both: +0.012 difference, 0.2 sem. Not resolved.
- **Do not read any of this as B0 against the trained frozen checkpoint.** It is two policies at ε-schedule position 0.753, with 500 of 9,000 episodes.

---

## 6. Verified versus inferred

**Verified by running code:**
- Each test failing on the unfixed code, then passing.
- The regression set being identical by test ID.
- Server-setup validation passing on both trees.
- The 500-episode log identity between UNFIXED and the frozen run.
- Finiteness over all 500 episodes.
- Every number in the eval table.
- The harness reproducing locally.
- The 346–348 synced files being sha256-verified.

**Verified by reading:** the defect sites, the placement of the weights, the served ranges of r2 and r3, and the §8/B1 text.

**Inferred:**
- That UNFIXED's episode-500 weights equal the frozen run's (from exact actions and rewards, but no saved weights to compare).
- That training-time outages are about 5–6% of user-steps and make up about 80% of B0's r3 magnitude. This comes from the gap to the log-identical control; the outage count was not logged directly.

**Not measured:** gradient norms, a paired B0−UNFIXED test, and anything past episode 500.

## 7. For the owner

1. **Is B1 / §8 overturned?** D-1 is committed on the shared branch and PENALTYARM's OFF arm already contains it.
2. **Is the loose r3 floor of −100 acceptable?** It roughly quadruples the early r3 signal. The alternative is a state-dependent worst case, such as −max_b U_b(t), or a W-13-frozen value.
3. **Should the eval-path scalar that drives best-checkpoint selection be calibrated too?**
4. **Cleanup:** the detached baseline worktree `/home/u24/papers/mcrl-b0-baseline` at `e3f3503e` exists only for the regression comparison and is safe to remove. Branch `b0/corrected-baseline-20260911` is not merged anywhere.
