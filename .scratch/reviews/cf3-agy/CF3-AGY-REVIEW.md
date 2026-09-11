**Found 0 INVALIDATES and 0 BIASES findings in the CF3 pilot implementation (2 COSMETIC observations noted).**

---

# Independent Expert Review: Three-Catfish (CF3) Pilot Implementation

**Reviewer Model**: Antigravity (Independent Context / Different Model Family)  
**Date**: 2026-09-11  
**Target Repository**: `/home/u24/papers/mcrl-leo-handover-cf3`  
**Git Branch / Diff Range**: `cf3/pilot-20260911` (`363845e8..HEAD`, commits up to `ca678414`)  
**Governing Documents**:
- `V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md`
- `V025-CONTROLLER-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md`
- `V025-CONTROLLER-AMENDMENT-2-EE-ONLY-2026-09-11.md`
- `DECLARATION-ADDENDUM.md` and `PROGRESS.md`

---

## 1. Executive Summary

A comprehensive, line-by-line static analysis and dynamic test execution was performed across all newly added and modified files in the worktree:
- `src/mcrl/algorithms/cf_ratio.py`
- `src/mcrl/algorithms/cf_sources.py`
- `scripts/run_cf3_pilot.py`
- `scripts/cf3_common.py`
- `scripts/cf3_eval.py`
- `scripts/cf3_report.py`
- `scripts/cf3_premeasure.py`
- `scripts/cf3_diag100.py`
- `scripts/cf3_de_diag.py`
- `tests/test_cf_ratio.py`

The implementation faithfully satisfies the declared mathematical formulations, design constraints, and amendments. No defects were identified that would invalidate the experimental results or introduce methodological bias between arms A0, A1, A2, and A3. The test suite (`15/15` tests passed in 241.7s) rigorously checks the intended behaviors against specific failure mutants. Two minor cosmetic observations are documented for completeness.

---

## 2. Review Methodology & Verification Matrix

| Area | Status | Verification Method |
| :--- | :---: | :--- |
| **Arm Fairness** | **PASS** | Verified by code reading (`cf_ratio.py:602-622`, `run_cf3_pilot.py:98-131`, `modqn.py:1506-1510`) and dynamic batch inspection (`cf3_diag100.py`). |
| **TD-Target Mechanics** | **PASS** | Verified by code reading (`cf_ratio.py:540-601`) and automated unit tests (`test_three_heads_share_the_combined_continuation_action`, `test_target_recomputed_when_eta_changes_and_stored_rewards_do_not`). |
| **Reward Sum Identity** | **PASS** | Verified by code reading (`cf_ratio.py:88-109`, `energy_efficiency.py:114-184`) and unit test (`test_reward_vector_sums_to_evaluator_bits_and_joules`). |
| **Outage Credit Assignment** | **PASS** | Verified by mathematical derivation from code (`cf_ratio.py:100-108`, `action_contract.py:446-456`) under Amendment 2 ($\lambda = 0$). |
| **Seed & Eval Hygiene** | **PASS** | Verified by checking seed constants in `cf3_common.py:26-33`, `DECLARATION-ADDENDUM.md`, and greedy evaluation rollout code (`cf3_eval.py:33-45, 120-137`). |
| **Exception & Guard Policies** | **PASS** | Verified by tracing all exception blocks (`run_cf3_pilot.py:287-303`, `finiteness.py:25-60`). |
| **Test Integrity** | **PASS** | All 15 tests executed and verified against mutants (`PROGRESS.md` and `test_cf_ratio.py:37-173`). |

---

## 3. Detailed Technical Audit

### 3.1 Fairness Between Arms (Updates, Schedules, and Environments)
*Verified by reading code and runtime diagnostics.*
- **Gradient Update Cadence**: In `train_cf` (`cf_ratio.py:737-745`), each main environment step executes `step_losses = self.update()`. The three catfish source environments are stepped via `src.step()`, which only generates and stores transitions in `src.buffer`. They perform zero network updates and zero backward passes.
- **Minibatch Composition**: Batch size is strictly 128 across all arms. For A1, minibatches draw 128 rows from the main replay buffer. For A2 and A3, minibatches draw exactly 113 rows from main replay and 5 rows from each of the 3 source buffers (`113 + 5*3 = 128`). A2 and A3 have identical buffer capacities (50,000) and sampling schedules.
- **Hyperparameter Parity**: Learning rate is identical ($10^{-3}$) across all arms. Target network synchronization occurs every 50 episodes across all arms. Epsilon decay follows the identical compressed schedule (222 episodes) across all arms.

### 3.2 TD-Target Mechanics and Shared Continuation Bootstrap
*Verified by reading code and automated tests.*
- **Action Masking on Target Network**: In `cf_ratio.py:540-550`, `_shared_continuation_action` applies `score = score.masked_fill(~nm, -1e9)` before computing `score.argmax(dim=1, keepdim=True)`. Invalid actions are never selected. Non-terminal transitions in replay are filtered by `if not bool(result.done) and not bool(next_mask.any()): continue`, guaranteeing that `nm` has at least one valid action.
- **Terminal Handling**: In `cf_ratio.py:598-600`, target calculation is `r + gamma * q_next * (1.0 - dn)`. For terminal transitions ($t=9$, the 10th step), `dn = 1.0` and `(1.0 - dn) = 0.0`, correctly zeroing the continuation bootstrap. For intermediate steps, $\gamma = 1.0$ and $dn = 0.0$.
- **Shared Continuation Bootstrap**: In `head_targets(batch, head)`, `a_star = self.continuation_actions(batch)` is computed once and shared by all three heads (`HEAD_B`, `HEAD_E`, `HEAD_H`). Target networks are not mutated during the per-head update loop.
- **Freshness of $\eta$ in Stored Rewards**: Replay buffers store raw physical quantities $(B_u, E_u, H_u)$ without scaling. Units normalization $(s_B, s_E, 1)$ and $\tilde{\eta}$ evaluation occur dynamically at sample time. Changes to $\eta$ at episodes 500 and 750 immediately govern future targets without stale reward contamination.
- **Remaining-Steps State Feature**: Because $T=10$ with $\gamma=1.0$ is a finite-horizon MDP without time in the 112-dim observation, `encode_at(states, t)` appends normalized remaining steps $\frac{T - t}{T}$ ($1.0$ at $t=0$, $0.1$ at $t=9$, and $0.0$ at terminal next-state $t=10$). A0 retains the 112-dim encoding with $\gamma=0.9$.

### 3.3 Reward Sum Identity vs. Evaluator Estimand
*Verified by reading code and test verification.*
- **Bit Consistency**: User decoded bits are defined as $B_u = R_u \cdot \Delta t$ for served users and $0.0$ for unserved users. By additive decomposition in `SystemEnergyEfficiency` (`energy_efficiency.py:144`), $\text{throughput} = \sum_u R_u$, so $\sum_u B_u = \text{system\_throughput\_bps} \cdot \Delta t$ bit-for-bit.
- **Joule Consistency**: System energy is partitioned equally: $E_u = \frac{P_{sys} \cdot \Delta t}{U}$. Summed over all $U$ users, $\sum_u E_u = P_{sys} \cdot \Delta t$, matching the evaluator denominator exactly.
- **Evaluator Estimand**: `pooled_rollout` in `cf_ratio.py:385-396` accumulates bits and joules left-to-right (matching B0 harness convention without floating point compensated summation drift) and performs a single division $\frac{\sum \text{bits}}{\sum \text{joules}}$ at the end. The placebo test reproduces B0's pinned reference `52,420,510.0956937` bit/J bit-for-bit.

### 3.4 Outage Credit Assignment & Anti-Inversion Guarantee
*Verified by mathematical derivation from code.*
- In `cf_reward_matrix` (`cf_ratio.py:88-109`), an unserved user receives $B_u = 0.0$ and $E_u = \frac{P_{sys} \cdot \Delta t}{U}$. Per `action_contract.py:446`, an unserved step has handover class `NONE` ($H_u = 0.0$).
- Under Amendment 2, $\lambda = 0.0$. Thus, an unserved user receives immediate scalarized reward $R_{unserved} = - \tilde{\eta} \frac{E_u}{s_E} < 0$.
- Any served user receives $B_u = R_u \cdot \Delta t > 0$ and $E_u = \frac{P_{sys} \cdot \Delta t}{U}$, yielding immediate reward $R_{served} = \frac{B_u}{s_B} - \tilde{\eta} \frac{E_u}{s_E}$.
- The difference $R_{served} - R_{unserved} = \frac{B_u}{s_B} > 0$ is strictly positive for all served users under all conditions. An unserved user cannot score better than a served user.

### 3.5 Evaluation Protocol, Pinned Archive, and Seed Isolation
*Verified by reading code and configuration.*
- **Seed Disjointness**:
  - Training seeds: `(42, 1337, 7)` to `(46, 1341, 11)` (all $\le 1341$).
  - Internal RNG offsets: NULL sources `train_seed + 80_000 + k`, Catfish sampling `train_seed + 70_001`.
  - Calibration seeds: base `9_121_000` (env), `9_122_000` (mobility) for 24 episodes.
  - Evaluation seeds: base `9_111_000` (env), `9_112_000` (mobility) for 24 episodes.
  - Evaluation random action seeds: base `9_131_000` for 24 episodes.
  - All seed spaces are completely disjoint with zero overlap.
- **Exploration in Evaluation**: Both `CFRatioTrainer.greedy_actions` and `C.modqn_greedy` perform pure masked argmax. They consume zero random numbers from `_train_rng` and enforce `eps = 0.0`.
- **TLE Pinning**: All processes assert SHA-256 digest `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9` prior to running.
- **Per-Episode Reseeding**: Fresh environments are re-instantiated with paired generators for every evaluation episode $e \in \{0..23\}$, ensuring identical start epochs, ephemeris positions, and warm-start ages across all arms.

### 3.6 Exception Handling & Finiteness Battery
*Verified by reading code.*
- Training errors in `run_cf3_pilot.py:299-303` catch `Exception`, record status `"failed"` with error type to `status.json`, and explicitly re-raise the exception (`raise`).
- `assert_finite_loss`, `assert_finite_gradients`, and `assert_finite_parameters` enforce strict termination on non-finite values rather than skipping updates.
- In `cf_ratio.py:794-796`, episode log metrics check `np.isfinite` and raise `FloatingPointError` on non-finite values.

### 3.7 Test Suite Verification & Mutant Sensitivity
*Verified by running the test suite.*
- Executed `pytest tests/test_cf_ratio.py` in the workspace environment. All 15 tests passed in 241.70s.
- Each test exercises a designated failure mutant (e.g. `e_not_divided_by_u`, `per_head_max_bootstrap`, `eta_frozen_at_init`, `source_uses_main_env_rng`, `null_smaller_buffer`, `b1_incumbent_fallback`, `dual_ascent_on_by_default`, `shared_env_test_split`).

---

## 4. List of Findings

### Finding 1 (COSMETIC): Resume State Metadata Mismatch on Learning-Check Stop
- **Severity**: COSMETIC
- **Location**: `scripts/run_cf3_pilot.py:293-294`
- **Description**: If the episode-500 learning check fails, `LearningCheckStop` is caught in `run_cf3_pilot.py:292`. The handler executes:
  ```python
  done = len(logs) + 1 if cf_arm else len(logs)
  save(done)
  ```
  Because `quarter_update(500)` raises before `logs.append(log)` occurs in the trainer loop, `len(logs)` is 499, while `done` is passed as 500. `save(500)` writes `resume.pt` with `next_episode: 500` and `logs` containing 499 entries.
- **Failure Scenario / Impact**: If an operator attempted to resume a stopped run via `--root`, line 152 would raise `SystemExit("resume logs are not contiguous")`. However, status is set to `stopped-learning-check`, line 86 skips runs with that status, and the declaration states that a run failing the learning check is never debugged or relaunched. There is zero impact on training or reporting validity.

### Finding 2 (COSMETIC): NumPy 2.0 `np.trapezoid` Dependency in Report Script
- **Severity**: COSMETIC
- **Location**: `scripts/cf3_report.py:82`
- **Description**: `cf3_report.py` computes learning-speed AUC using `np.trapezoid(...)`. In NumPy 2.0+, `np.trapezoid` replaces the deprecated `np.trapz`. While the project virtualenv runs NumPy 2.5.2 (where `np.trapezoid` is present and `np.trapz` is removed), invoking `cf3_report.py` with an older system Python (e.g., Python 3.12 with NumPy 1.26.4) will fail with an `AttributeError`.
- **Failure Scenario / Impact**: Running the aggregation script outside the project virtualenv fails with `AttributeError: module 'numpy' has no attribute 'trapezoid'`. The script functions correctly when invoked within the designated virtualenv.

---

## 5. Conclusion & Pilot Readiness Assessment

The CF3 pilot codebase has been thoroughly audited and found to be free of invalidating defects or bias-inducing discrepancies. The experimental design is sound, the four arms (A0, A1, A2, A3) are paired and controlled, and the data contract faithfully implements the governing declarations and amendments. The multi-hour training batch currently in flight can proceed with confidence.
