**0 INVALIDATES, 1 BIASES: The E0 development training launch may proceed (arms 1–3 unconditionally; arm 4 after tightening one unit-test assertion).**

---

## Review Context & Scope

- **Repository Worktree**: `/home/u24/papers/mcrl-leo-handover-dev`
- **Diff Reviewed**: `git -C /home/u24/papers/mcrl-leo-handover-dev diff 63b02dc030180b83889387b031bd1c7dff4754f5..f90421502b87311ddf633a52ca54625c91cf530c` (commit [`f9042150`](file:///home/u24/papers/mcrl-leo-handover-dev))
- **Governing Specification**: `/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md` (§2 kernel, §3 seed namespaces, §5 preflight, §6 frozen E0 batch).
- **Target Work / Direction**: Minimum E0 development training surface: arms 1–4 (`D0`, `D2-T0`, `D2-null`, `D3-T0`), T0 raw state labels, DEV/DEVVAL seed isolation, frozen E0 hyperparameters, fail-closed launcher, and preflight test harness.

---

## Executive Summary of Findings

| ID | Severity | Item / Subject | File:Line | Status / Verification |
|---|---|---|---|---|
| **F-01** | **BIASES** | Unit test `test_d3_margin_loss_properties` passes under named mutant `d3_no_margin` (blind spot in D3 margin enforcement test) | [`tests/test_cf_dev.py:543-554`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L543-L554) | Verified by reading & execution |
| **F-02** | **COSMETIC** | `run_mutants.sh` regex pattern fails on `pytest -x` output, masking mutant results | `.scratch/dev-training/run_mutants.sh:36` | Verified by reading & execution |
| **F-03** | **COSMETIC** | `dev_e0_proctest.py` crashes with `KeyError` if passed a pre-pilot calibration artifact lacking `eta0_bit_per_J` | [`scripts/dev_e0_common.py:111`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L111) | Verified by reading & execution |

**Launch Gate Assessment**:
- **Arms 1–3 (`D0`, `D2-T0`, `D2-null`)**: **CLEAR TO PROCEED**. All kernel loss functions, data buffer labels, seed namespaces, resume logic, and preflight tests for D0, D2-T0, and D2-null are fully verified and bit-identical to spec.
- **Arm 4 (`D3-T0`)**: The algorithmic implementation of [`cft.d3_margin_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L170-L188) in `src/mcrl/algorithms/cf_teacher.py` is **mathematically and programmatically correct**; however, its preflight unit test has a blind spot (F-01) where the test does not turn red if the margin is zeroed out. Before launching arm 4 in a later batch, one assertion should be added to test the margin-sensitive region.

---

## Detailed Findings

### Finding F-01: Unit test `test_d3_margin_loss_properties` fails to turn red under named mutant `d3_no_margin`
- **Severity**: **BIASES** (Preflight verification blind spot for Arm 4 comparator)
- **Files & Lines**:
  - [`tests/test_cf_dev.py:542-555`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L542-L555)
  - [`tests/test_cf_dev.py:137-141`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L137-L141)
- **Status**: Verified by reading and verified by direct test execution.
- **Concrete Failure Scenario**:
  The test [`test_d3_margin_loss_properties`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L529-L561) claims to be red under mutant `d3_no_margin` (`lambda s, m, a, margin: real(s, m, a, 0.0)`). However:
  1. In the first assertion:
     ```python
     scores[0, 4] = 1.0; scores[0, 1] = 0.5; scores[0, 9] = 0.2; a_t = 4
     loss = float(cft.d3_margin_loss(scores, mask, a_t, 0.15))
     assert loss == pytest.approx(max(0.5 + 0.15, 0.2 + 0.15, 1.0) - 1.0, rel=1e-6)
     ```
     Here, the teacher score $S(s, 4) = 1.0$ is ahead of the closest candidate $S(s, 1) = 0.5$ by $0.50$, which is strictly greater than the margin $m = 0.15$. The runner-up with margin is $0.5 + 0.15 = 0.65 < 1.0$. The margin is already satisfied, so the loss is $0.0$. If the margin is zeroed out ($m = 0.0$), the loss is $\max(0.5, 0.2, 1.0) - 1.0 = 0.0$. Thus, `loss == pytest.approx(0.0)` passes identically under `d3_no_margin`.
  2. In the violated margin assertion:
     ```python
     s2 = scores.clone().requires_grad_(True)
     with torch.no_grad():
         s2[0, 1] = 1.1
     loss2 = cft.d3_margin_loss(s2, mask, a_t, 0.15)
     assert float(loss2) > 0.0
     loss2.backward()
     assert float(s2.grad[0, 4]) < 0.0
     assert float(s2.grad[0, 1]) > 0.0
     ```
     Here, the candidate score $1.1$ already strictly exceeds the teacher score $1.0$ without any margin ($1.1 > 1.0$). With $m = 0.0$, the loss is $1.1 - 1.0 = 0.10 > 0.0$, and the backward gradients on $S_4$ and $S_1$ have the exact same signs (-1 and +1).
  3. Consequently, the test never checks an input where the margin is load-bearing ($S(s, a) \le S(s, a_T) < S(s, a) + m$, e.g., $S(s, 4) = 1.0$ and $S(s, 1) = 0.95$). Under `DEV_MUTANT=d3_no_margin`, `test_cf_dev.py` reports `20 passed`, violating the preflight requirement that every named mutant turns its test red.
- **Production Code Status**:
  The implementation of [`cft.d3_margin_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L170-L188) in `src/mcrl/algorithms/cf_teacher.py` was inspected line-by-line and is **unaffected**:
  ```python
  marg = torch.full_like(scores, float(margin))
  marg.scatter_(1, a_col, 0.0)
  q = (scores + marg).masked_fill(~mask, MASK_FILL)
  return (q.max(dim=1).values - scores.gather(1, a_col).squeeze(1)).mean()
  ```
  The production code correctly adds $m$ to non-teacher actions and subtracts the teacher score.
- **Recommended Remediation**:
  In `tests/test_cf_dev.py`, add an explicit test row where $S(s, a_T) = 1.0$, $S(s, 1) = 0.90$, $m = 0.15$, and assert `loss == pytest.approx(0.05)`. Under `d3_no_margin`, that assertion will evaluate $0.0 == 0.05$ and turn strictly red.

---

### Finding F-02: `run_mutants.sh` regex flaw misreports mutant failures
- **Severity**: **COSMETIC** (Verification script outside git diff)
- **Files & Lines**: `.scratch/dev-training/run_mutants.sh:35-37`
- **Status**: Verified by reading and execution.
- **Concrete Failure Scenario**:
  `run_mutants.sh` uses:
  ```bash
  out=$(DEV_MUTANT="$m" $PY -m pytest tests/test_cf_dev.py -q -x -k "$t" 2>&1 | tail -3)
  if echo "$out" | grep -qE "[0-9]+ (failed|error)"; then ...
  ```
  When `pytest` encounters a failure under `-x`, it stops execution immediately and prints:
  ```text
  =========================== short test summary info ============================
  FAILED tests/test_cf_dev.py::test_... - AssertionError...
  !!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
  ```
  The regex `[0-9]+ (failed|error)` looks for a number followed by lowercase `failed` or `error`. The line contains uppercase `FAILED` with no preceding number, and `stopping after 1 failures` (plural `failures`). Thus `grep` returns exit code 1 on failed runs, leading `run_mutants.sh` to output:
  `MUTANTS: 0 red / 22 total; 22 did NOT turn their test red`.
  Testing all 22 mutants with standard process exit code check (`res.returncode != 0`) confirmed that 21 of 22 mutants genuinely turn red.
- **Remediation**:
  Check pytest's process exit code (`[ $? -ne 0 ]`) or grep for `FAILED` instead of `[0-9]+ (failed|error)` in `tail -3`.

---

### Finding F-03: `KeyError` on unexpected calibration JSON schema
- **Severity**: **COSMETIC** (Operator error safety / diagnostics)
- **Files & Lines**: [`scripts/dev_e0_common.py:111`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L111)
- **Status**: Verified by reading and execution.
- **Concrete Failure Scenario**:
  [`e0_cf_settings`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L99-L118) directly indexes `calib["eta0_bit_per_J"]`, `calib["bits_scale"]`, and `calib["joules_scale"]`. If an operator points `--calibration` to an earlier phase artifact (such as `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v07-c2-development-calibration-20260902-r1/calibration.json`), the script raises an unhandled `KeyError: 'eta0_bit_per_J'`.
- **Remediation**:
  Ensure the documentation and launch scripts explicitly pass the pilot calibration file containing `eta0_bit_per_J`, or add a validated schema check in `assert_environment()`.

---

## Detailed Code Audit against Specification Requirements

### 1. Mechanisms: D0, D2-T0, D2-null, D3-T0
- **D0 (No teacher)**:
  - In [`CFDevTrainer.update`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L522-L526), when `not self.dev.uses_teacher`, it immediately delegates to `super().update()` with zero modification to gradient flow or data collection.
  - In [`test_d0_development_run_reproduces_the_pilot_a1_learner`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L582-L600), a D0 development run is verified to reproduce `CFRatioTrainer` bit-identically across network weights, losses, rewards, and step statistics.
- **D2-T0 (Soft distillation on student-visited states)**:
  - Student score is computed via [`student_scores`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L139-L151) as $S(s, a) = Q_B(s, a) - \tilde{\eta} Q_E(s, a) - \lambda Q_H(s, a)$ with $\lambda = 0$ and $\tilde{\eta} = \eta_0 \cdot s_E / s_B$.
  - Soft targets are computed via [`soft_targets`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L121-L136) as $\text{softmax}(T_0 / \tau)$ over legal action masks with $\tau = 3.0$, exactly zero on illegal slots.
  - Distillation loss is computed via [`d2_ce_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L154-L168) as $-\sum p \log q$ over legal slots with $\tau_s = 1.0$ and illegal logits masked to `MASK_FILL = -1e9` (avoiding $-\infty \cdot 0 = \text{NaN}$).
  - Gradients flow jointly into $Q_B$ and $Q_E$ through the combined loss backward step.
- **D2-null (Matched permutation null)**:
  - Permutation is performed via [`permute_scores_among_legal`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L101-L119) exclusively among indices where `mask[u]` is True. Illegal slot values and masks are untouched.
  - Uses dedicated composite generator `(9_231_000, k)` from the `DEV-NULL` namespace; never touches `_train_rng` or `_env_rng`.
  - `teacher_action` is derived from the permuted scores via `masked_argmax_rows`, completely destroying correlation with T0's optimal action while preserving the probability distribution multiset and action mask. Tested on 4,000 states to agree with T0 at the chance rate ($p \approx 1 / |\mathcal{A}_{\text{legal}}|$).
- **D3-T0 (DQfD large margin)**:
  - Large margin loss is computed via [`d3_margin_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L170-L188) as $\max_{a \in \mathcal{A}_{\text{legal}}} [S(s, a) + m \cdot \mathbf{1}(a \ne a_T)] - S(s, a_T)$ with $m = 0.15$ and weight $\lambda_E = 1.0$.
  - Asserts legality of teacher action in student state mask before computing max.
- **Teacher weight = 0 reduction**:
  - In [`test_teacher_weight_zero_reproduces_d0_bit_identically`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L564-L580), setting $\alpha = 0$ for D2-T0 and D2-null, or $\lambda_E = 0$ for D3-T0, reproduces D0 network weights and episode logs bit-for-bit.

---

### 2. Teacher T0 = LP-prev(c=1, m=0)
- Computed in [`cft.t0_scores`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L56-L79) directly from the raw `UserState`:
  - `gain = np.asarray(s.channel_quality, dtype=np.float64)` (raw nominal SINR, NOT log1p decoded).
  - `load = np.asarray(s.beam_loads, dtype=np.float64)` (previous-step beam user counts).
  - `score = np.log2(1.0 + np.maximum(gain, 0.0)) - 1.0 * (load == 0.0)`.
  - Masked argmax: `acts[u] = int(ok[int(np.argmax(score[ok]))])`.
  - Tie-break: `np.argmax` selects the first occurrence, and `ok` is sorted ascending; thus ties break to the **lowest index**, matching the verified LP probe specification.
  - Tested bit-for-bit against `lp_common.lp_prev_rule_factory(1.0, 0.0)` in [`test_t0_actions_equal_the_lp_probe_rule_on_real_states`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L368-L393).
  - Labels ride with transitions in [`TeacherReplayBuffer`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L224-L323), verified in [`test_stored_labels_are_the_collection_time_labels_of_their_own_state`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L643-L670).

---

### 3. Seed Namespaces & Formal Set Isolation
- **Namespaces verified**:
  - DEV Training: triple $k$: `train = 9_201_000+k`, `env = 9_202_000+k`, `mobility = 9_203_000+k`.
  - DEVVAL Evaluation: $i = 0..23$: `env = 9_211_000+i`, `mobility = 9_212_000+i`, `RANDOM = 9_221_000+i`.
  - DEV-NULL Generators: composite identities `(9_231_000, k)` for D2-null, `(9_241_000, k)` for D3/D4-null.
- **Fail-closed seed validation**:
  - Enforced by [`assert_dev_seed`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L136-L158) and [`assert_dev_null_key`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L97-L134) at every initialization and rollout call.
  - Formal evaluation (`9_111_000+i / 9_112_000+i`), calibration (`9_121_000+i / 9_122_000+i`), and CONFIRM (`9_301_000+k / 9_311_000+i`) are strictly blacklisted in `FORBIDDEN_SEED_RANGES`.
  - [`measure_on_calibration`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L461-L465) and [`quarter_update`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L466-L470) raise `MCRLContractError` unconditionally.
  - [`test_no_development_path_produces_a_formal_seed`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L769-L808) intercepts all RNG instantiations during training, rollout, and reference generation, verifying that zero formal seeds are produced.

---

### 4. Frozen E0 Configuration & Hyperparameters
- Budget: 300 episodes.
- $\epsilon$-decay: linear 1.0 $\to$ 0.01 over $\text{round}(2000 \cdot 300 / 9000) = 67$ episodes, then flat.
- Dual variables: $\eta$ fixed at $\eta_0 = 110,507,234.83444457\text{ bit/J}$ (asserted at driver launch); $\lambda = 0.0$; no quarter updates.
- Credit assignment: `equal_share` for arms 1–4; `lighting_price` reserved for diagnostic arms 5–6.
- Architecture: DQN (100, 50, 50) tanh, 113-dim input, 28 actions, Adam 1e-3, batch size 128, replay capacity 50,000, target network update every 50 episodes.

---

### 5. Launcher, Manifest, Process Hygiene & Resume
- **Manifest**:
  - Written or validated at `<root>/RUN-MANIFEST.json`.
  - Includes code manifest (git commit, file SHA256 hashes, whole `src/` tree SHA256 digest), calibration hash, prereg digest, TLE file set hash (`427e6a91...`), and per-arm configuration hashes.
  - Fail-closed: both launcher and driver verify manifest and fingerprint before executing.
- **Process management**:
  - Launched via `systemd-run --user --scope -p MemoryMax=5G`, `nice -n 10`, 1 BLAS thread (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`), new session (`start_new_session=True`).
  - Liveness verification ([`is_live`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L47-L63)) verifies PID existence, command line arguments (`--arm`, `--seed-index`, `--root`), and working directory (`/proc/{pid}/cwd == REPO`).
- **Resume and State Persistence**:
  - Verified by [`scripts/dev_e0_proctest.py`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_proctest.py):
    - Arm 3 (`D2-null`) uninterrupted vs stopped at episode 2 and resumed to episode 3.
    - Final policy weights, DEV-NULL RNG state, and per-episode metrics are **bit-identical**.
    - Second launch while live correctly detects `live pid` and starts nothing.
    - Launcher and driver fail closed when configuration budget is modified.

---

## Preflight Test & Mutant Verification Results

All 20 test cases in [`tests/test_cf_dev.py`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py) pass cleanly in the target environment:
```text
============================== 20 passed in 102.50s ==============================
```

Individual named mutant validation results:
- `t0_from_encoded_observation` $\to$ **RED** (AssertionError in `test_t0_labels_reproduce_the_verified_rule`)
- `t0_tie_break_last` $\to$ **RED** (AssertionError in `test_t0_labels_reproduce_the_verified_rule`)
- `t0_no_prev_step_penalty` $\to$ **RED** (AssertionError in `test_t0_labels_reproduce_the_verified_rule`)
- `t0_argmax_ignores_mask` $\to$ **RED** (AssertionError in `test_t0_labels_reproduce_the_verified_rule`)
- `d2_sign_flipped` $\to$ **RED** (AssertionError in `test_d2_loss_shape_sign_mask_and_target`)
- `d2_ignores_mask` $\to$ **RED** (AssertionError in `test_d2_loss_shape_sign_mask_and_target`)
- `d2_target_not_normalised` $\to$ **RED** (AssertionError in `test_d2_loss_shape_sign_mask_and_target`)
- `d2_only_qb` $\to$ **RED** (AssertionError in `test_d2_gradient_reaches_the_deployed_score_heads`)
- `d3_margin_on_teacher_action` $\to$ **RED** (AssertionError in `test_d3_margin_loss_properties`)
- `d3_max_over_illegal` $\to$ **RED** (AssertionError in `test_d3_margin_loss_properties`)
- `d3_no_margin` $\to$ **GREEN** (Finding F-01: blind spot in `test_d3_margin_loss_properties`)
- `null_permutes_across_the_mask` $\to$ **RED** (AssertionError in `test_d2_null_preserves_dimensions_mask_and_schedule`)
- `null_keeps_the_argmax` $\to$ **RED** (AssertionError in `test_d2_null_carries_no_t0_action_information`)
- `null_uses_train_rng` $\to$ **RED** (AssertionError in `test_d2_null_uses_only_its_own_generator_and_ignores_the_t0_action`)
- `teacher_applied_at_zero_weight` $\to$ **RED** (AssertionError in `test_teacher_weight_zero_reproduces_d0_bit_identically`)
- `dev_loop_freezes_the_time_feature` $\to$ **RED** (AssertionError in `test_d0_development_run_reproduces_the_pilot_a1_learner`)
- `replay_labels_misaligned` $\to$ **RED** (AssertionError in `test_replay_sampling_matches_the_pilot_buffer_and_labels_follow_rows`)
- `resume_drops_teacher_labels` $\to$ **RED** (AssertionError in `test_resume_keeps_the_labels_and_is_bit_identical`)
- `devval_consumes_train_rng` $\to$ **RED** (AssertionError in `test_devval_does_not_consume_training_rng_and_is_deterministic`)
- `devval_uses_formal_evaluation_seeds` $\to$ **RED** (AssertionError in `test_no_development_path_produces_a_formal_seed`)
- `dev_trainer_reads_calibration` $\to$ **RED** (Failed: DID NOT RAISE MCRLContractError)
- `manifest_ignores_dev_settings` $\to$ **RED** (AssertionError in `test_config_hash_is_deterministic_and_covers_the_whole_configuration`)

---

## Verdict & Recommendation

1. **Launch Decision**:
   - The planned **E0a launch (Arms 1–3: D0, D2-T0, D2-null on DEV seed index $k=0$ stopped at episode 100)** is **APPROVED TO PROCEED**.
   - All code paths and mechanisms for arms 1–3 have passed rigorous line-by-line inspection, unit testing, mutant testing, process-level stop/resume validation, and DEVVAL rollouts.
2. **Follow-up Before Arm 4 Execution**:
   - Add a test assertion in [`test_d3_margin_loss_properties`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L529) to verify that `d3_no_margin` turns red (Finding F-01).
   - Fix the grep regex in `run_mutants.sh` (Finding F-02).
