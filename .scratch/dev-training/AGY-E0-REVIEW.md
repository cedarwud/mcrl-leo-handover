**0 INVALIDATES, 0 BIASES: The E0 development training launch may proceed.**

---

# Fresh-Context Engineering Review: E0 Development-First Training Harness

- **Review Date**: 2026-09-12 (Local)
- **Reviewer**: Fresh-Context Independent Engineering Reviewer (Alternative Model Family)
- **Repository Worktree**: `/home/u24/papers/mcrl-leo-handover-dev`
- **Diff Reviewed**: `git -C /home/u24/papers/mcrl-leo-handover-dev diff 63b02dc030180b83889387b031bd1c7dff4754f5..772481c4dbdcb69d729168d513366a4a5ecddf46`
- **Commits Included**:
  - [`f9042150`](file:///home/u24/papers/mcrl-leo-handover-dev): `DEVHARNESS: minimum E0 development-training surface (D0 / D2-T0 / D2-null / D3-T0)`
  - [`772481c4`](file:///home/u24/papers/mcrl-leo-handover-dev): `DEVHARNESS preflight fixes (test harness only, no production path)`
- **Governing Specification**: `/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md` (§2 kernel, §3 seed namespaces, §5 preflight, §6 frozen E0 batch).
- **Target Surface**:
  1. Mechanisms: `D0` (unadorned ratio learner), `D2-T0` (soft distillation on student states), `D2-null` (legal score permutation matched null), `D3-T0` (DQfD large margin comparator).
  2. Teacher `T0`: `LP-prev(c=1, m=0)` computed strictly from raw `UserState` at collection time and stored with transitions.
  3. Seeds: DEV training triples (`9_201_000+k`, `9_202_000+k`, `9_203_000+k`), DEVVAL evaluation (`9_211_000+i`, `9_212_000+i`), DEVVAL random (`9_221_000+i`), DEV-NULL composite generator keys (`(9_231_000, k)`, `(9_241_000, k)`). Formal evaluation (`9_111_000+i` / `9_112_000+i`), calibration (`9_121_000+i` / `9_122_000+i`), and CONFIRM (`9_311_000+i` / `9_312_000+i`) sets are strictly unreachable.
  4. Frozen E0 config: 300 episodes, $\epsilon$ linear $1.0 \to 0.01$ over 67 episodes, $\eta$ fixed at $\eta_0 = 110,507,234.83444457\text{ bit/J}$ (no $\eta$ updates), $\lambda = 0$, credit `equal_share` (diagnostic `lighting_price` on arms 5–6).
  5. Launcher & Driver: deterministic `RUN-MANIFEST.json` with code digest and per-arm configuration hash, idempotent, fail-closed on any mismatch, process liveness by PID + cmdline + cwd, dry-run capability, and bit-identical resume.

---

## Executive Summary & Findings Matrix

| Severity | Count | Status / Impact |
|:---|:---:|:---|
| **INVALIDATES** | **0** | No correctness, leakage, seed contamination, or contract violations found. |
| **BIASES** | **0** | No systematic biases, gradient distortion, or uncalibrated leakage detected. |
| **COSMETIC** | **4** | 4 operational / documentation notes (harmless warning, shell regex detail, env prerequisites). |

### Findings Log

| ID | Severity | File:Line | Subject | Verification Method |
|:---|:---|:---|:---|:---|
| **F-01** | **COSMETIC** | `.scratch/dev-training/run_mutants.sh:35-37` | Bash grep regex pattern in scratch runner script fails to match pytest `-x` summary string | Verified by reading & test execution |
| **F-02** | **COSMETIC** | [`tests/test_cf_dev.py:555`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L555) | Direct float conversion of gradient-requiring tensor triggers PyTorch `UserWarning` | Verified by reading & test execution |
| **F-03** | **COSMETIC** | [`scripts/dev_e0_common.py:107-117`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L107-L117) | `e0_cf_settings` requires merged pilot calibration dictionary with `eta0_bit_per_J` | Verified by reading & schema inspection |
| **F-04** | **COSMETIC** | [`scripts/dev_e0_launch.py:178`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L178) | Launcher spawns driver using `sys.executable`, requiring invocation under the project venv | Verified by reading & process inspection |

---

## Systematic Audit Against Requirements

### 1. Mechanisms: D0, D2-T0, D2-null, D3-T0

- **D0 (Ratio Learner Baseline)**:
  - In [`CFDevTrainer.update()`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L521-L525), when `self.dev.uses_teacher` is `False`, the method executes `return super().update()` untouched.
  - Test [`test_d0_development_run_reproduces_the_pilot_a1_learner`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L583-L601) proves that an unadorned `D0` development run reproduces the pilot `CFRatioTrainer` bit-identically across all model weights and episode logs.
- **Teacher Weight = 0 Identity**:
  - In [`CFDevTrainer.update()`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L542-L547), when $\alpha = 0.0$ (`D2`) or $\lambda_E = 0.0$ (`D3`), `teacher_loss` evaluates to $0.0$, contributing zero gradient to any head.
  - Test [`test_teacher_weight_zero_reproduces_d0_bit_identically`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L565-L581) confirms that `D2-T0` ($\alpha=0$), `D2-null` ($\alpha=0$), and `D3-T0` ($\lambda_E=0$) land on identical weights and metrics as `D0`.
- **D2-T0 (Soft Distillation on Student States)**:
  - Scalar deployed score: [`cft.student_scores`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L139-L151) computes $S = Q_B - \tilde{\eta} Q_E - \lambda Q_H$, exactly matching the ratio learner's deployed combination [`CFRatioTrainer._combine`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_ratio.py#L579-L581).
  - Cross-entropy loss: [`cft.d2_ce_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L154-L168) masks illegal logits with `MASK_FILL = -1e9` and computes $-\sum_{a \in \text{legal}} p_{\text{target}}(a) \log q_{\text{student}}(a)$.
  - Gradients: Test [`test_d2_gradient_reaches_the_deployed_score_heads`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L442-L460) confirms that loss minimization propagates positive gradients into $Q_B$ and negative gradients into $Q_E$ (scaled by $\tilde{\eta}$), properly pulling up $S$.
  - Illegal actions: Since $p_{\text{target}}$ is $0$ on illegal actions and illegal logits are masked to $-1e9$, illegal actions receive zero gradient.
- **D2-null (Matched Null Distillation)**:
  - Permutation: [`cft.permute_scores_among_legal`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L101-L119) permutes score values strictly among the indices where `mask` is `True`. Illegal slots keep their sentinel values and are never swapped with legal actions.
  - Action destruction: Test [`test_d2_null_carries_no_t0_action_information`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L483-L499) statistically verifies over 4,000 states that the permuted argmax agrees with T0 only at the random chance rate ($1 / |\mathcal{A}_{\text{legal}}|$).
  - Generator isolation: `D2-null` consumes exclusively `self._null_rng = np.random.default_rng(dev.null_key)`. Test [`test_d2_null_uses_only_its_own_generator_and_ignores_the_t0_action`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L501-L526) confirms `_train_rng` and `_env_rng` bit-generator states are unchanged.
- **D3-T0 (DQfD Large Margin)**:
  - Large margin formula: [`cft.d3_margin_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L170-L188) computes $\max_{a \in \text{legal}} [S(s, a) + m \cdot \mathbf{1}(a \ne a_T)] - S(s, a_T)$.
  - Legality assertion: If $a_T$ is illegal in $s$, it raises [`MCRLContractError`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/errors.py) rather than masking or clipping silently.
  - Tightened unit test: Commit [`772481c4`](file:///home/u24/papers/mcrl-leo-handover-dev) revised [`tests/test_cf_dev.py:536-544`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L536-L544) so that runner-up action score $0.95$ sits within margin $m=0.15$ of teacher score $1.0$ ($0.95 + 0.15 = 1.10 > 1.0$). The margin is directly load-bearing (loss $0.10$), and mutant `d3_no_margin` turns strictly red.

---

### 2. Teacher T0 = LP-prev(c=1, m=0) on Raw States

- **Exact Arithmetic**:
  - Score definition: $\text{score}(a) = \log_2(1 + \max(\gamma_a, 0)) - 1.0 \cdot \mathbf{1}(N_a == 0)$.
  - Inputs: Read strictly from raw `s.channel_quality` ($\gamma_a$) and `s.beam_loads` ($N_a$) from `UserState`.
  - Tie-breaking: `int(ok[int(np.argmax(score[ok]))])` where `ok = np.flatnonzero(legal)` is sorted in increasing index order (0..27). In NumPy, `np.argmax` returns the first index among ties. Thus, the lowest candidate index wins on ties, matching the verified rule.
  - Parity: Test [`test_t0_actions_equal_the_lp_probe_rule_on_real_states`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L368-L393) checks statement-for-statement equality with `lp_common.lp_prev_rule_factory(1.0, 0.0)` on real ephemeris environment states.
  - Replay storage: Teacher labels (`t0_action`, `teacher_action`, `teacher_scores`) are computed at collection step $t$ on raw `states` and stored with $(s_t, a_t, r_t, s_{t+1}, m_t, m_{t+1}, d_t)$ via [`TeacherReplayBuffer.push_labeled`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L247-L260).

---

### 3. Seed Namespaces & Isolation

- **Namespace Partitioning**:
  - `DEV` training triples: `train = 9_201_000+k`, `env = 9_202_000+k`, `mobility = 9_203_000+k` ($k \in [0, 9]$).
  - `DEVVAL` evaluation: `env = 9_211_000+i`, `mobility = 9_212_000+i`, `RANDOM = 9_221_000+i` ($i \in [0, 23]$).
  - `DEV-NULL` keys: composite identities `(9_231_000, k)` (D2 permutations) and `(9_241_000, k)` (D3/D4 actions).
- **Formal Boundary Enforcement**:
  - `FORBIDDEN_SEED_RANGES`: Formal eval (`9_111_000–9_112_999`), calibration (`9_121_000–9_122_999`), and CONFIRM (`9_301_000–9_312_999`) ranges are declared in [`cf_dev.py:61-70`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L61-L70).
  - [`assert_dev_seed`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L136-L158) and [`assert_dev_null_key`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L97-L134) fail closed with [`MCRLContractError`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/errors.py) if any formal seed or invalid base/index is constructed.
  - In `CFDevTrainer`, [`measure_on_calibration`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L461-L465) and [`quarter_update`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L466-L470) raise errors unconditionally.
  - Test [`test_no_development_path_produces_a_formal_seed`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L770-L808) intercepts every `np.random.default_rng` invocation during a full training and DEVVAL rollout cycle and proves zero formal seeds are constructed.

---

### 4. Frozen E0 Configuration

- **Parameters Verified**:
  - Episodes: 300.
  - Epsilon schedule: Linear $1.0 \to 0.01$ over $\text{round}(2000 \times 300 / 9000) = 67$ episodes, then flat at $0.01$.
  - Dual parameters: $\eta$ fixed at $\eta_0 = 110,507,234.83444457\text{ bit/J}$ (checked to $10^{-6}$ relative tolerance in [`run_dev_e0.py:109`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/run_dev_e0.py#L109)); $\lambda$ fixed at $0.0$.
  - Credit mode: `equal_share` for arms 1–4; `lighting_price` for diagnostic arms 5–6.
  - Distillation parameters: $\alpha = 1.0$, $\tau = 3.0$ (selected from VAL in T0REPR), $\tau_s = 1.0$.
  - Margin parameters: $m = 0.15$, $\lambda_E = 1.0$.
  - Evaluation schedule: DEVVAL (24 fresh episodes) evaluated at episodes 100, 200, and 300.

---

### 5. Launcher, Driver & Process Management

- **Manifest & Config Hashing**:
  - [`dev_e0_launch.py`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py) generates `RUN-MANIFEST.json` containing the whole-`src` SHA256 digest, individual manifest file hashes, calibration SHA256, and per-arm configuration hashes.
  - Both launcher and driver fail closed if an existing manifest does not match the live code or configuration.
- **Process Liveness**:
  - [`is_live(pidfile, arm, k, root)`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L47-L64) reads `/proc/{pid}/cmdline` and `/proc/{pid}/cwd`, checking that the PID matches `scripts/run_dev_e0.py`, `--arm {arm}`, `--seed-index {k}`, `--root {root}`, and `cwd == C.REPO`.
  - Execution uses `systemd-run --user --scope -p MemoryMax=5G nice -n 10` with single BLAS threads (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`).
- **Idempotency & Bit-Identical Resume**:
  - Completed runs (`status: complete`) exit 0 immediately without re-training.
  - Interrupted runs save `resume.pt` at episode boundaries (every 100 episodes, or at `--stop-after`). Resuming restores the replay buffer (with teacher labels), model weights, optimizer states, and `_null_rng` generator state.
  - Direct test execution of [`dev_e0_proctest.py`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_proctest.py) confirmed:
    - `T1`: An arm 3 (`D2-null`) run interrupted at episode 2 and resumed through the launcher matches an uninterrupted run bit-identically (`resume_bit_identical: true`, `next_episode: 3`).
    - `T2`: A launch against an altered configuration budget is refused fail-closed by the launcher (`launcher_refused_changed_config: true`).

---

## Detailed Review Checklist

| Check Item | Verdict | Evidence / Code Reference |
|:---|:---:|:---|
| **Teacher loss actually applied?** | **PASS** | [`cf_dev.py:542-547`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L542-L547): `total = td_losses[0] + td_losses[1] + td_losses[2] + teacher_loss`; single backward pass updates all networks. |
| **Loss sign and mask correct?** | **PASS** | [`cf_teacher.py:165-167`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L165-L167): Cross-entropy minimizes $-\sum p \log q$; gradients pull up $Q_B$ and pull down $Q_E$. Masked logits set to $-1e9$. |
| **Loss isolated from illegal actions?** | **PASS** | `p_target` is strictly zero on illegal actions; $-1e9$ logit yields zero probability and zero gradient. In D3, max excludes illegal actions. |
| **Null teacher destroys T0 action?** | **PASS** | [`cf_teacher.py:111-118`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L111-L118): Scores permuted randomly among legal indices only; agreement rate equals chance ($1/k$). |
| **Null teacher generator isolated?** | **PASS** | `_null_rng` draws strictly from `(9_231_000, k)` without advancing `_train_rng` or `_env_rng`. |
| **Zero teacher weight reduces to D0?** | **PASS** | [`test_cf_dev.py:565-581`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L565-L581): Bit-identical weights and logs under $\alpha=0$ and $\lambda_E=0$. |
| **T0 labels match verified probe?** | **PASS** | Computed on raw `UserState` (`channel_quality` and `beam_loads`), tie-break first legal index. Bit parity verified against `lp_common.py`. |
| **No formal seeds reachable?** | **PASS** | [`assert_dev_seed`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L136-L158) blocks all formal evaluation, calibration, and CONFIRM ranges. |
| **Manifest covers code and config?** | **PASS** | `src_tree_sha256`, commit, calibration SHA256, and per-arm config hash in `RUN-MANIFEST.json`. |
| **Resume cannot mix versions?** | **PASS** | `resume.pt` stores full `fingerprint` (code digest, config hash, seeds); driver exits on mismatch. |
| **Failures swallowed?** | **PASS** | [`run_dev_e0.py:219-223`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/run_dev_e0.py#L219-L223): Status updated to `"failed"` and exception explicitly re-raised. Non-finite values raise `FloatingPointError`. |
| **Named mutants turn tests red?** | **PASS** | All 22 named mutants verified RED (22/22) under isolated test execution. |

---

## Detailed Notes & Cosmetic Observations

### Finding F-01: Shell Grep Regex Flaw in Scratch Script `run_mutants.sh`
- **Severity**: **COSMETIC** (Not part of the git diff / repository worktree)
- **File & Line**: `/home/u24/papers/mcrl-leo-handover/.scratch/dev-training/run_mutants.sh:35-37`
- **Context**:
  In `.scratch/dev-training/run_mutants.sh`, the mutant verification loop executes:
  ```bash
  out=$(DEV_MUTANT="$m" $PY -m pytest tests/test_cf_dev.py -q -x -k "$t" 2>&1 | tail -3)
  if echo "$out" | grep -qE "[0-9]+ (failed|error)"; then ...
  ```
- **Analysis**:
  When `pytest` halts after a test failure under `-x`, its trailing output lines are:
  ```text
  =========================== short test summary info ============================
  FAILED tests/test_cf_dev.py::test_... - AssertionError: ...
  !!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
  ```
  The regex `[0-9]+ (failed|error)` looks for lowercase `failed` or `error` preceded by digits. The word in pytest's `-x` notice is `failures` (plural), and `FAILED` has no preceding digit. Consequently, `grep` returned exit code 1, causing the runner to report `GREEN(BAD)` in `.scratch/dev-training/mutants.log` ("0 red / 22 total") even though the tests genuinely failed.
- **Verification**:
  A fresh verification harness checking `pytest` process exit codes (`res.returncode != 0`) was executed across all 22 mutant/test pairs. **All 22 named mutants turned their designated unit tests RED (22/22)**.

### Finding F-02: PyTorch `UserWarning` in `test_cf_dev.py`
- **Severity**: **COSMETIC** (Test code warning)
- **File & Line**: [`tests/test_cf_dev.py:555`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L555)
- **Context**:
  In [`test_d3_margin_loss_properties`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L529-L562):
  ```python
  loss2 = cft.d3_margin_loss(s2, mask, a_t, 0.15)
  assert float(loss2) > 0.0
  loss2.backward()
  ```
- **Analysis**:
  Because `s2` has `requires_grad=True`, `loss2` is a grad-tracking tensor. Directly converting it via `float(loss2)` before `loss2.backward()` triggers a PyTorch `UserWarning` recommending `tensor.detach()` first.
- **Recommendation**:
  Change to `assert float(loss2.detach()) > 0.0` to eliminate the warning.

### Finding F-03: Merged Calibration Artifact Requirement
- **Severity**: **COSMETIC** (Operational guidance)
- **File & Line**: [`scripts/dev_e0_common.py:107-117`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L107-L117)
- **Context**:
  [`e0_cf_settings`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L99-L118) reads `calib["eta0_bit_per_J"]`, `calib["bits_scale"]`, and `calib["joules_scale"]`.
- **Analysis**:
  These keys are generated by `scripts/cf3_premeasure.py --merge` when producing the pilot calibration bundle. If an operator accidentally provides an unmerged premeasure JSON or a Catfish calibration file (which uses a different schema), the launcher will terminate with a clear `KeyError`. Operators should ensure the canonical merged pilot `calibration.json` is passed.

### Finding F-04: Launcher Python Interpreter Path
- **Severity**: **COSMETIC** (Operational guidance)
- **File & Line**: [`scripts/dev_e0_launch.py:178`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L178)
- **Context**:
  `dev_e0_launch.py` builds the subprocess invocation with `sys.executable`.
- **Analysis**:
  If an operator invokes `python scripts/dev_e0_launch.py` using system Python (`/usr/bin/python3`), the driver processes will fail closed immediately because `torch` and `mcrl` are installed in the workspace virtual environment.
- **Recommendation**:
  Always launch via `/home/u24/papers/mcrl-leo-handover/.venv/bin/python scripts/dev_e0_launch.py ...`.

---

## Verdict & Launch Gate Assessment

The code in diff `63b02dc0..772481c4` has been thoroughly read and verified by test execution.
1. The kernel implementations of mechanisms `D0`, `D2-T0`, `D2-null`, and `D3-T0` are mathematically and programmatically faithful to Amendment 6.
2. Teacher `T0` is computed strictly from the raw `UserState` at collection time and bit-identically matches the verified LP probe rule.
3. Seed namespaces are strictly separated; runtime guards prevent formal evaluation, calibration, or CONFIRM seeds from being constructed or accessed.
4. Process management, manifest hashing, liveness verification, and bit-identical resume have been verified through actual execution of [`dev_e0_proctest.py`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_proctest.py).
5. All 20 unit tests pass (20/20 green), and all 22 named mutants fail their tests (22/22 red).

**The E0 development training launch may proceed.**
