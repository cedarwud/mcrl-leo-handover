**0 INVALIDATES, 0 BIASES: The D3-null development runs may proceed.**

---

# Fresh-Context Engineering Review: D3-null Matched Null Harness

- **Review Date**: 2026-09-12 (Local)
- **Reviewer**: Fresh-Context Independent Engineering Reviewer (Alternative Model Family)
- **Repository Worktree**: `/home/u24/papers/mcrl-leo-handover-dev`
- **Diff Reviewed**: `git -C /home/u24/papers/mcrl-leo-handover-dev diff fc4f5bc7445271c6a52073963f2a6181b2db0a03..05aadf1bb24a9e3a730975227fbf27ab7760deb9`
- **Commit Reviewed**: [`05aadf1b`](file:///home/u24/papers/mcrl-leo-handover-dev): `DEVHARNESS: D3-null, the matched null for the large-margin injection`
- **Governing Specification**: `/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md` (§2 kernel, §3 seed namespaces, §6 frozen E0 batch).
- **Scope**: Matched null arm `D3-null` (Arm 7, `equal_share`) paired with large-margin teacher injection `D3-T0`.

---

## Executive Summary & Findings Matrix

| Severity | Count | Status / Impact |
|:---|:---:|:---|
| **INVALIDATES** | **0** | No correctness, leakage, seed contamination, illegal draw, or contract violations found. |
| **BIASES** | **0** | No non-uniform action distribution, T0 correlation, gradient distortion, or uncalibrated leakage detected. |
| **COSMETIC** | **1** | 1 minor CLI docstring comment out of sync with expanded arm vocabulary. |

### Findings Log

| ID | Severity | File:Line | Subject | Verification Method |
|:---|:---|:---|:---|:---|
| **F-01** | **COSMETIC** | [`scripts/dev_e0_launch.py:22`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L22) | Docstring usage example states `SPEC = ARM:K (1:0 .. 6:0)` while arm 7 is now in `ARMS` and accepted by parser | Verified by reading & dry-run execution |

---

## Detailed Findings

### F-01 (COSMETIC): Launcher Docstring Example Omits Arm 7
- **File:Line**: [`scripts/dev_e0_launch.py:22`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L22)
- **Severity**: **COSMETIC**
- **Verification**: Verified by reading and dry-run execution.
- **Description**: The module docstring usage comment in [`dev_e0_launch.py`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L22) lists `SPEC = ARM:K (1:0 .. 6:0); default = arms 1-4 on DEV triple k = 0`. However, commit `05aadf1b` added Arm 7 (`7: ("D3-null", "equal_share")`) to [`dev_e0_common.py:ARMS`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L52).
- **Concrete Failure Scenario**: An operator reading only the top docstring might believe that `7:0` is an unrecognized arm spec. However, at runtime, the argument parser and validator dynamically check `if arm not in D.ARMS` ([`dev_e0_launch.py:100`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_launch.py#L100)) and accept `7:0` cleanly without error. This is purely cosmetic and does not impede execution.

---

## Systematic Audit Against Required Properties

### Property 1: Identical D3 Loss, Margin, Weight $\lambda_E$, Schedule, Legal-Action Mask, and Gradient Path
- **Loss Formulation**: Both `D3-T0` and `D3-null` route to [`cft.d3_margin_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L191-L208):
  $$\mathcal{L}_{D3} = \frac{1}{|\mathcal{B}|} \sum_{s \in \mathcal{B}} \left( \max_{a \in \mathcal{A}_{\text{legal}}(s)} \left[ S(s, a) + m \cdot \mathbf{1}(a \ne a_{\text{target}}) \right] - S(s, a_{\text{target}}) \right)$$
- **Weight $\lambda_E$ & Multiplier**:
  - In [`DevSettings.teacher_weight`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L228-L229):
    ```python
    if self.mechanism in ("D3-T0", "D3-null"):
        return float(self.lambda_e)
    ```
  - In [`CFDevTrainer._teacher_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L531-L534):
    ```python
    if d.mechanism in ("D3-T0", "D3-null"):
        a_t = torch.tensor(np.asarray(batch["teacher_action"], dtype=np.int64),
                           dtype=torch.long, device=self.device)
        return d.lambda_e * cft.d3_margin_loss(scores, mask, a_t, d.margin)
    ```
- **Schedule**: In E0, $\lambda_E = 1.0$ and $m = 0.15$ are held constant throughout training across all arms. There is no adaptive or annealing schedule.
- **Legal-Action Masking**: Illegal action logits are masked with `MASK_FILL = -1e9` prior to `max()`, preventing any illegal action from receiving gradient or satisfying the margin. If $a_{\text{target}}$ is illegal, [`cft.d3_margin_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L203-L204) immediately raises `MCRLContractError("D3: the teacher action is illegal in its state")`.
- **Gradient Path**: In [`CFDevTrainer.update()`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L558-L566), `total = td_losses[0] + td_losses[1] + td_losses[2] + teacher_loss` is backpropagated jointly into all three Q-heads ($Q_B, Q_E, Q_H$) in a single backward pass, with finite gradient assertions [`assert_finite_gradients`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L565).
- **Verification**: Verified by reading source code and verified by execution of unit tests.

### Property 2: Uniform Random Legal Action Drawn from Declared DEV-NULL Namespace
- **Seed Namespace**: Declared in Amendment 6 §3 as `default_rng((9_241_000, k))`.
  - In [`scripts/dev_e0_common.py:38,122-125`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L38): `DEV_NULL_D3_BASE = 9_241_000`, `_null_key_for("D3-null", k)` yields `(9_241_000, int(k))`.
  - In [`src/mcrl/algorithms/cf_dev.py:193-205`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L193-L205): `DevSettings.__post_init__` enforces that `D3-null` carries base `9_241_000` and validates the composite key via `assert_dev_null_key`.
- **Uniformity & Legality**: Implemented in [`cft.random_legal_actions`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_teacher.py#L125-L139):
  ```python
  def random_legal_actions(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
      mask = np.asarray(mask, dtype=bool)
      out = np.asarray(no_op_actions(mask.shape[0]), dtype=np.int64)
      for u in range(mask.shape[0]):
          valid = np.flatnonzero(mask[u])
          if valid.size:
              out[u] = int(rng.choice(valid))
      return out
  ```
  - For each user $u$, `valid` contains all indices where `mask[u]` is True.
  - `rng.choice(valid)` without probability weights samples uniformly at random over the legal subset with exact probability $1 / |\text{valid}|$.
  - Under no circumstances can an action outside `valid` be chosen.
  - If `valid.size == 0`, `out[u]` is `NO_OP_ACTION (-1)`. During data collection, transitions where the user took `NO_OP` are skipped ([`cf_dev.py:666`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L666)). If an illegal action were somehow pushed to replay, [`push_labeled`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L262-L263) fails closed with `MCRLContractError`.
- **Independence of T0**: `random_legal_actions` takes only `(mask, rng)`. It has no access to `states`, `channel_quality`, `beam_loads`, or T0 scores.
- **Verification**: Verified by reading and confirmed by test [`test_d3_null_target_is_legal_independent_of_t0_and_seeded`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L926-L991).

### Property 3: T0's Action Enters No Loss Input of the Null Arm
- **Storage Isolation**: In [`CFDevTrainer.teacher_labels`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L496-L504):
  ```python
  elif self.dev.mechanism == "D3-null":
      used = np.zeros_like(scores)
      used_acts = cft.random_legal_actions(legal, self._null_rng)
  ```
  - `used_scores` is overwritten with zeros: `used = np.zeros_like(scores)`.
  - `used_acts` is the random legal action.
- **Replay Storage**: [`self.replay.push_labeled`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L673-L680) stores `t0_action=t0_acts[uid]`, `teacher_action=used_acts[uid]`, `teacher_scores=used_scores[uid]`.
- **Batch Unpacking & Loss Evaluation**:
  - In [`_teacher_loss`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L531-L534), `a_t` is taken exclusively from `batch["teacher_action"]` (which holds `used_acts`).
  - Neither `batch["t0_action"]` nor `batch["teacher_scores"]` is read anywhere in the D3 loss path.
  - In [`update()`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L547-L557) and [`head_targets`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_ratio.py#L654-L665), TD targets evaluate greedy student actions over `batch["next_masks"]` and ignore teacher labels completely.
- **Diagnostic Safety**: `t0_acts` is only read for telemetry tracking (`t0_greedy_agree`, `t0_behaviour_agree`, `used_agree_t0`). In D3-null, `used_agree_t0` tracks agreement between the random legal action and T0 at chance ($1/26 \approx 3.8\%$).
- **Verification**: Verified by reading and confirmed by mutant tests `d3null_target_is_t0_action` and `d3null_scores_carry_t0`.

### Property 4: Null Generator Consumes No Trainer Stream and Survives Stop/Resume
- **Generator Isolation**:
  - Trainer streams are initialized in [`CFDevTrainer.__init__`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L455-L457) as `train_seed=9_201_000+k`, `env_seed=9_202_000+k`, `mobility_seed=9_203_000+k`.
  - `self._null_rng` is initialized separately as `np.random.default_rng((9_241_000, k))` ([`cf_dev.py:465`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L465)).
  - Rollout actions are sampled using `self._train_rng` (for $\epsilon$-greedy exploration); env steps consume `self._env_rng`; `random_legal_actions` consumes exclusively `self._null_rng`.
  - Test [`test_d3_null_target_is_legal_independent_of_t0_and_seeded`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L952-L953) explicitly verifies:
    ```python
    assert tr._train_rng.bit_generator.state == before_train
    assert tr._env_rng.bit_generator.state == before_env
    ```
- **Stop/Resume Persistence**:
  - In [`CFDevTrainer.training_state_dict`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L750-L757):
    ```python
    state["dev"] = {
        "settings": dataclasses.asdict(self.dev),
        "null_rng": (None if self._null_rng is None
                     else copy.deepcopy(self._null_rng.bit_generator.state)),
        "teacher_updates": int(self._teacher_updates),
    }
    ```
  - In [`CFDevTrainer.load_training_state_dict`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L759-L771):
    ```python
    if (dev["null_rng"] is None) != (self._null_rng is None):
        raise MCRLContractError("resume state DEV-NULL generator does not match")
    if self._null_rng is not None:
        self._null_rng.bit_generator.state = copy.deepcopy(dev["null_rng"])
    ```
  - `TeacherReplayBuffer` serializes `teacher_labels` with format version 1 ([`cf_dev.py:306-333`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L306-L333)).
- **Bit-Identical Resume Test**: An independent test stopping D3-null at episode 1 and resuming to episode 3 was executed against an uninterrupted 3-episode run. Model parameters, TD losses, and teacher losses matched bit-for-bit (`D3-null stop/resume bit-identical PASS!`).
- **Verification**: Verified by reading and live script execution.

### Property 5: Teacher Weight Zero Reduces to D0 Exactly
- When $\lambda_E = 0.0$, `_teacher_loss` evaluates to $0.0 \times \mathcal{L}_{D3} = 0.0$.
- In [`CFDevTrainer.update()`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L560), `total` contains only TD loss contributions. Backpropagation produces identical gradients to `D0`.
- Because `random_legal_actions` does not advance `_train_rng`, minibatch sampling and exploration sequences remain identical to `D0`.
- Unit test [`test_teacher_weight_zero_reproduces_d0_bit_identically`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L610-L625) was updated in this diff to include `("D3-null", {"lambda_e": 0.0})` and passes with `assert torch.equal(x, y)` across all parameters.
- Mutant `teacher_applied_at_zero_weight` turns strictly red.
- **Verification**: Verified by reading and test execution.

### Property 6: Configuration Hash Covers Null Identity
- In [`scripts/dev_e0_common.py:150-168`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L150-L168), `arm_config_payload` serializes:
  - `"arm": 7`
  - `"arm_name": "E0-7-D3-null-equal_share"`
  - `"mechanism": "D3-null"`
  - `"seed_index": k`
  - `"dev_settings"`: includes `"null_key": (9_241_000, k)`, `"teacher": "random"`, `"mechanism": "D3-null"`.
- [`config_hash`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L171-L175) performs SHA-256 over key-sorted JSON.
- Test [`test_d3_null_version_hash_covers_the_null_identity`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L994-L1019) verifies:
  - `config_hash(D3-null k=0) != config_hash(D3-null k=1)`
  - `config_hash(D3-null k=0) != config_hash(D3-T0 k=0)`
  - Rejection of invalid bases (e.g. `(9_231_000, 0)`), wrong teacher (`"T0"`), or missing `null_key=None`.
- Mutants `d3null_key_dropped_from_hash` and `manifest_ignores_dev_settings` turn strictly red.
- **Verification**: Verified by reading and test execution.

### Property 7: Formal Seeds Strictly Unreachable
- In [`src/mcrl/algorithms/cf_dev.py:136-164`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L136-L164), `assert_dev_seed` and `assert_dev_null_key` fail closed against all formal namespaces:
  - Formal evaluation: `[9_111_000, 9_112_999]`
  - Formal calibration: `[9_121_000, 9_122_999]`
  - Formal CONFIRM: `[9_301_000, 9_312_999]`
- In [`scripts/dev_e0_common.py:101-120`](file:///home/u24/papers/mcrl-leo-handover-dev/scripts/dev_e0_common.py#L101-L120), `e0_cf_settings` explicitly zeroes calibration bases (`calibration_env_seed_base=0`, `calibration_mobility_seed_base=0`, `calibration_episodes=0`).
- [`CFDevTrainer.measure_on_calibration`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L471-L474) and [`quarter_update`](file:///home/u24/papers/mcrl-leo-handover-dev/src/mcrl/algorithms/cf_dev.py#L476-L479) raise `MCRLContractError` if invoked.
- Tests [`test_dev_namespaces_are_disjoint_from_every_formal_set`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L766-L787), [`test_no_development_path_produces_a_formal_seed`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L815-L853), and [`test_formal_sets_are_refused_by_the_development_trainer`](file:///home/u24/papers/mcrl-leo-handover-dev/tests/test_cf_dev.py#L855-L866) pass completely.
- **Verification**: Verified by reading and test execution.

---

## Independent Verification of Named Mutants

All named mutants relating to D3-null and the teacher weight zero reduction were independently executed with `pytest`:

| Mutant Name | Target Test | Expected Failure Mode | Observed Result | Status |
|:---|:---|:---|:---|:---:|
| `d3null_target_is_t0_action` | `test_d3_null_target_is_legal_independent_of_t0_and_seeded` | Agreement with T0 reaches 1.0 (fails `< 0.25`) | `AssertionError: the null agrees with T0 at 1.0` | **RED** |
| `d3null_target_may_be_illegal` | `test_d3_null_target_is_legal_independent_of_t0_and_seeded` | Unmasked draw selects illegal action in tight mask | `AssertionError: an illegal null draw` | **RED** |
| `d3null_uses_train_rng` | `test_d3_null_target_is_legal_independent_of_t0_and_seeded` | `_train_rng` bit generator state modified during labels | `AssertionError: bit_generator.state == before_train` | **RED** |
| `d3null_scores_carry_t0` | `test_d3_null_target_is_legal_independent_of_t0_and_seeded` | `used_scores` carries non-zero T0 scores | `AssertionError: the null carries a T0 quantity` | **RED** |
| `d3null_key_dropped_from_hash` | `test_d3_null_version_hash_covers_the_null_identity` | `dev_settings` lacks `null_key` | `KeyError: 'null_key'` | **RED** |
| `manifest_ignores_dev_settings` | `test_d3_null_version_hash_covers_the_null_identity` | Config payload drops `dev_settings` block | `KeyError: 'dev_settings'` | **RED** |
| `teacher_applied_at_zero_weight`| `test_teacher_weight_zero_reproduces_d0_bit_identically` | Teacher loss applied when weight is 0.0 | `AssertionError: ... at zero weight moved the weights` | **RED** |

In clean (unmutated) conditions, all 22 tests in `tests/test_cf_dev.py` pass cleanly (`22 passed in 118s`).

---

## Final Review Verdict

The changes introduced in commit `05aadf1bb24a9e3a730975227fbf27ab7760deb9` for **D3-null** are sound, strictly compliant with Amendment 6, completely isolated from teacher quantities and student RNG streams, covered by the configuration hash, and fully verified by both unit tests and named mutation testing.

**The D3-null development training runs may proceed.**
