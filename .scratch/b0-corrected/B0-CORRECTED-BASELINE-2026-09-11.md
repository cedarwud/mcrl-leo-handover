**All three fixes landed, each with a test I saw fail on the unfixed code and then pass (D-3 needed one fixup, found when the first pilot crashed at episode 50), and the relaunched 500-episode pilot ran clean — every loss finite, no blowup — but D-1 overturns frozen ruling B1 / SDD §8 and D-2's r3 floor dominates the r3 head, and both need an owner ruling before B0 is used as a control.**

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
