I have scheduled a timer to wait for the test suite to complete. I will proceed with the final review report once the execution finishes.
Waiting for the final test cases in `tests/test_mc2_judge.py` to finish execution.
Waiting for the remaining 4 tests in `tests/test_mc2_judge.py` to complete.
Waiting for the final test cases to finish.
VERDICT: NO-INVALIDATES

### Findings Summary
1. **[NON-BLOCKING] `judge_override_rate` semantics diverge between rules.** In `src/mcrl/algorithms/cf_judge.py:372-376`, `arb_labels` sets `override = True` for *any* non-$x_u$ winner (including Catfish-A wins). Consequently, `judge_override_rate` in `cf_judge.py:667` measures any non-$x_u$ intervention under v2, but only challenger overrides of A under v1. The contract's clause-(vi) activity reading correctly uses `judge_challenger_wins_c_ne_a / decision_rows_all_t` (`cf_judge.py:659`), and `B/b_readout.py` consumes this field.  
   *Fix:* Purely cosmetic/reporting. Keep `as_log()` unchanged for running runs; document the distinction in downstream reporting or rename the v2 diagnostic field to `judge_intervention_rate`.
2. **[NON-BLOCKING] `test_03` lacks an explicit negative parity mutation test.** While `tests/test_mc2_judge.py:360-417` checks that `judge.assert_committed_parity(out)` passes when parity holds, and mutant `judge_advances_rng` catches parity breakage in `test_02`, `test_03` itself does not assert that `assert_committed_parity` raises when given an artificially perturbed outcome (e.g., flipping a bit in `outcome.resolution.served`).  
   *Fix:* Add a 3-line check in `test_03` calling `assert_committed_parity` on a corrupted outcome and asserting `pytest.raises(MCRLContractError)`.
3. **[NON-BLOCKING] Formal 1000-episode harness wiring deferred to post-confirmation.** The judge mechanism (`JudgeSpec`, `cf_judge.py`, arm 10) is currently integrated solely into `src/mcrl/algorithms/cf_dev.py` and `scripts/dev_e0_*.py`. `scripts/run_cf3_pilot.py` and `CFRatioTrainer` have not yet been wired for formal evaluation episodes, and `CFDevTrainer` intentionally guards against formal seed ranges (`cf_dev.py:70-80`) and raises on `quarter_update` (`:874`). Additionally, $\epsilon$-decay will automatically scale to 222 episodes (`round(2000 * 1000 / 9000)`) in a 1000-episode run versus 67 in DEV (`round(2000 * 300 / 9000)`).  
   *Fix:* Required only when transitioning from DEV to formal evaluation after ep-300 confirmation. Wire `JudgeSpec` into `CFRatioTrainer` and `run_cf3_pilot.py`.

---

### Detailed Evaluation Against Contract r2

#### A. Judge Fidelity
- **Formula & Constants:** $\kappa = (n_{\text{served}}, B - \eta_0 E)$ is computed in `cf_judge.py:143-148` (`kappa_of`) using frozen $\eta_0 = 110\,507\,234.83444457$ (`cf_judge.py:75`, `ETA0_JUDGE`). Strict lexicographic comparison with ties awarded to the incumbent is enforced by `strictly_better(a, b)` in `cf_judge.py:150-156` (strict inequality on `served`, fallback to strict inequality on `surrogate`).
- **Placement:** The judge is invoked in `src/mcrl/algorithms/cf_dev.py:1193` (`_judge_step`) after action selection (`cf_dev.py:1166`) and teacher label generation (`:1167`), immediately before `self.env.step(actions, self._env_rng)` (`:1200`).
- **Isolation & Side-Effect Freedom:** In `src/mcrl/env/step.py:700`, `StepEnvironment._evaluate_selected_actions` deep-copies the RNG (`local_rng = copy.deepcopy(rng)`). `StepJudge` executes within `cf_credit.frozen_driver_positions` (`cf_judge.py:186`), snapshots and restores segment state (`step.py:701-705`), and classifies handovers with `commit=False` (`step.py:707`). `tests/test_mc2_judge.py:380-408` (`test_03`) confirms that `env_rng`, `mobility_rng`, and the environment fingerprint are byte-identical across evaluations.
- **TD Target Protection:** Transitions stored in `JudgeReplayBuffer.push_judged` (`cf_judge.py:453-472`) store the executed action $x_u$, true transition reward, and next observation. The Bellman target calculation (`cf_ratio.py:90-115`, `cf_dev.py:1019-1029`) queries only standard transition keys. `judge_target` and `judge_tag` are read exclusively inside `_teacher_loss` (`cf_dev.py:987-1006`).
- **Parity Assertion:** `step_judge.assert_committed_parity(outcome)` is explicitly called on every step in `cf_dev.py:1204`. If committed $(B, E)$ or `served` bitmasks deviate from `judge.base()`, it raises `MCRLContractError` (`cf_judge.py:245-248`).

#### B. Rule Fidelity
- **`MC2-JGO-v1`:** In `cf_judge.py:302-322` (`jgo_labels`), the incumbent and default target are $a^A$. Challenger $c$ is evaluated only if $c \ne inc$ (`:311`). Target overrides to $c$ iff `strictly_better(k_c, k_i)` (`:318`); ties remain with $a^A$.
- **`MC2-ARB-v2`:** In `cf_judge.py:325-376` (`arb_labels`), running winner $w$ initializes to $x_u$. Candidate evaluation follows the strict sequence $x_u \to A \to \text{challenger}$. A candidate replaces $w$ only on strict superiority (`strictly_better(k_a, k_w)` at `:364`). If $c = w_{\text{act}}$, evaluation is skipped (`:356`), ensuring exact action ties between $a^A$ and $a^B$ preserve $a^A$. Target is assigned only when $w \ne x_u$ (`:372-375`); otherwise `target = NO_TARGET` and `tag = TAG_NONE`.
- **Single Target & Normalisation:** Batch loss assembly (`cf_dev.py:995-1006`) extracts single targets $a_t$, assigns weights $w_{\text{row}} = \mathbf{1}[\text{target} \ne \text{NO\_TARGET}]$, and substitutes executed action placeholders where $w_{\text{row}} = 0$. `cf_judge.py:393-415` (`weighted_margin_loss`) multiplies the unreduced margin loss by $w_{\text{row}}$ and normalises across the full minibatch (`.mean()`). Targetless rows yield zero loss and zero gradient without refilling vacated dose (`tests/test_mc2_judge.py:932-956`).
- **Final-Step Abstention:** In `cf_dev.py:1055-1056` (`_challenger_actions`), `is_final` ($t \ge T-1$) immediately returns `None`. Neither T_NEXT nor the uniform null is evaluated or injected at $t = T-1$ across any cell (`tests/test_mc2_judge.py:480-498`).
- **Shared B-Only Invariance:** `cf_judge.py:385-388` maps `BONLY_MECHANISM_ID` directly to `jgo_labels(use_a=False)`. `tests/test_mc2_judge.py:575-622` (`test_04c`) asserts identical label output, identical replay rows, and identical model parameter SHA-256 between the v1 and v2 code paths.

#### C. Nulls and Identity
- **Null Proposal Generation:** When `uses_r` is active, `cf_dev.py:1062-1063` samples one uniform legal action per legal user via `cf_teacher.random_legal_actions` driven exclusively by `_judge_null_rng`. This generator is seeded at `(9_243_000, k)` (`cf_dev.py:859-862`). `TeacherContext` is disabled (`cf_dev.py:844-849`). State persistence is enforced in `training_state_dict` (`cf_dev.py:1368-1372`) and verified on resume (`cf_dev.py:1399-1406`, `tests/test_mc2_judge.py:918-920`).
- **Configuration Hash:** `scripts/dev_e0_common.py:409-413` includes in the arm configuration payload `judge_spec` (mechanism id, canonical sources, judge id, $\eta_0$, null id, null key), `judge_rule_definition` (containing tie order `x_u > A > c`), and `judge_source_identities` (containing pinned `cf_tnext.py` SHA-256). Modifying any of these fields alters the configuration hash (`tests/test_mc2_judge.py:761-780`).
- **Base Arm Payloads:** For arms 1–9, `judge_spec` is omitted (`dev_e0_common.py:399-413`). `tests/test_mc2_judge.py:272-297` (`test_01`) confirms bit-for-bit payload identity against commit `6136c514` and matches the five launched $k=8$ hashes.

#### D. Readings Support
- **Per-Episode Logging:** `cf_judge.py:651-714` (`EpisodeJudgeLog.as_log`) exports all required contract clause-(vi) metrics:
  - Denominator: `decision_rows_all_t` (`cf_judge.py:657`) accumulates legal decision user-steps over all $t \in [0, T-1]$.
  - Numerator (v1): `judge_tag_counts["B"]` (`cf_judge.py:675`).
  - Numerator (v2): `judge_challenger_wins_c_ne_a` (`cf_judge.py:659`).
  - Sampled rows per tag: `judge_sampled_rows_by_tag` (`:708`).
  - Margin loss mass: `judge_margin_loss_by_tag` (`:709`).
  - Margin dose: `judge_margin_dose` (`:710`).
  - Compute overhead: `judge_evaluations` (`:701`) and `judge_wall_s` (`:702`).
- **Readout Autonomy:** `scripts/run_dev_e0.py:204` persists `episode-logs.json`, and `:220` outputs `devval-ep*.json`. `b_readout.py` computes all declared ep-100 and ep-300 selection and survival metrics exclusively from these saved files.

#### E. Test Verification
All 11 required contract tests are implemented in `tests/test_mc2_judge.py` (20 test cases total, all passing in 398.35s):
1. Arms 1–9 hash invariance (`test_01`).
2. Gate-shut equivalence: v1 matches `D3-T0` (`test_02`); v2 matches `D0` (`test_02b`).
3. Evaluator step-parity and generator immobility (`test_03`).
4. Gate semantics and final-step abstention: v1 (`test_04`), v2 arbitration order (`test_04b`), and shared B-only identity (`test_04c`).
5. B-null stream independence and non-access of T_NEXT (`test_05`).
6. Seed disjointness across DEV, P0, XEP, and formal namespaces (`test_06`).
7. Configuration hash sensitivity to rule, sources, $\eta_0$, and null specifications (`test_07`).
8. Policy deployment independence with judge and teacher stubs raising (`test_08`).
9. Checkpoint save/resume bit-level reproducibility across all 6 cells (`test_09`).
10. Margin loss zeroing on targetless rows and dose non-refill (`test_10`).

#### F. DEV Validity and Long-Run Hazards
- **Accumulated Generator State:** The judge consumes only ephemeral deep-copies of `self._env_rng` via `local_rng = copy.deepcopy(rng)` in `step.py:700`. The generator state is never advanced or contaminated. The B-null generator `_judge_null_rng` advances solely by $U_{\text{legal}}$ draws at $t < T-1$ and restores bit-identically on resume.
- **Memory & Resource Stability:** `StepJudge._cache` is instantiated within step contexts and freed upon exit (`cf_judge.py:184-196`). `JudgeReplayBuffer` maintains fixed capacity through `deque(maxlen=50000)` (`cf_judge.py:442-444`). RSS remains bounded at ~1.0 GB on sat and 1.9 GB locally, well below the 4.5 GB cap.
- **Confirmation Readiness:** The running development experiment is completely interpretable. No defects invalidate ep-100 selection or ep-300 confirmation. Wiring for the formal 1000-episode run can proceed after confirmation.
