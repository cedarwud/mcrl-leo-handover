# MC2 seam: lane B independent code read (one pass, loss and data causality only)

Read 2026-09-12 ~05:30–05:50Z against lane A's **working tree** (the only commits so far are contract r0/r1/r2: `67e175bd`, `9d3625c4`, `b6573b58`). Files pinned by sha256 as read:

| file | sha256 |
|---|---|
| `src/mcrl/algorithms/cf_judge.py` (new) | `6a7bc187a78de4d3db7518ad76ded70371b6f9958cdc6c30fe4b169e79789239` (identities/ARB section re-read later at `5cabe52e`-era tree) |
| `src/mcrl/algorithms/cf_dev.py` | `0d83d8f9de7710002e2b6cca0998ff22ca2e04e000039261e6956a550a9c3bb9` |
| `scripts/dev_e0_common.py` | `b6f82b5d578fd55699d805b931d3b95038553611d7c0a7deab96af71b9af0a8e` |
| `scripts/run_dev_e0.py` | `987f87edfb5a9479ba96095f47fe70f8ba5b920bf1c6d97f8d3392ba5a4ba704` |
| `scripts/dev_e0_launch.py` | `a6b510bf90d45575ff79104fecf83b10373ed1cb4c2dbb36b8772f28c141068b` |
| `tests/test_mc2_judge.py` (new) | `5cabe52e00e5651be3c6cf8eeb1b41329b1fbab91e5f10f499da2631b94be22a` |

Lane A kept editing during the read: `cf_judge.py` gained the ARB-v2 and shared-B-only identities, `arb_labels` and `labeller_for`, and `dev_e0_common.py` moved from `--sources` to the cell label. The findings below are against the state above; re-check the two test items at commit.

## Verdict

**No loss or data-causality defect.** Nothing here must change before the first counted v1 run. Two items must land before the **v2** cells are counted (D-1), and three are nits (D-2 to D-4).

## Checked and correct

**Placement and isolation.**
- The judge runs after `select_actions` and before `env.step`, with `self._env_rng` (`cf_dev.py:1184-1193`, `_judge_step` at `:1057`), inside `frozen_driver_positions` via `StepJudge.__enter__` (`cf_judge.py:184-195`).
- Each evaluation deep-copies the generator (`step.py:700`), the segment write is snapshotted and restored (`step.py:701-705`), handovers are classified with `commit=False` (`step.py:706-708`).
- `assert_committed_parity` runs on every step after `env.step` (`cf_dev.py:1193`, `cf_judge.py:237-249`), so a generator or environment move fails loudly rather than silently biasing labels.
- `test_03` additionally pins env_rng, the mobility generator and a driver/ledger/segment fingerprint across the judge, and asserts the frozen-position evaluation equals the plain evaluator.

**Single target, weights, normaliser.**
- `weighted_margin_loss` (`cf_judge.py:393-415`) is `cf_teacher.d3_margin_loss` statement for statement, then `* w` and `.mean()` over the full batch. `w = 1[target exists]` (`cf_dev.py:985-995`), so target-less rows contribute exactly 0 and the vacated dose is not refilled.
- With every `w = 1` the value and gradient are D3's bit for bit (multiplying by 1.0 is exact); `test_10` checks loss, gradient and the not-refilled normaliser, and `test_02` checks the end-to-end parameter sha256 against `D3-T0` with the gate shut while the judge and the T_NEXT context still run.
- The placeholder target on `w = 0` rows is the executed action, which `push_judged` has already validated as legal (`cf_judge.py:486-499`).

**Rules.**
- `jgo_labels` (`cf_judge.py:281-322`): incumbent and target `a^A` when A is enabled, else `x_u` with no target; the challenger is compared only when `c != inc`; strict `strictly_better` with ties to the incumbent (`:150-157`).
- `arb_labels` (`cf_judge.py:325-376`) is a sequence of strict comparisons `x_u` → A → challenger, skipping any candidate equal to the running winner. I checked the four cases: it equals "max κ, ties `x_u` > A > challenger", and a tag of B implies `a^B != a^A` in every path, which is exactly what r2's (vi) numerator needs.
- `κ(x_u)` is the base evaluation, so v2 costs no extra evaluation for the learner's own action (`cf_judge.py:208-228`, `:353-365`).
- `labeller_for` routes the shared `{B}` cell to `jgo_labels(use_a=False)` (`:379-389`); on `{B}` that is label-for-label `arb_labels`, including the lead fields, so the shared cell is genuinely rule-independent.

**Abstention and the null.**
- B and R are not even asked at `t = T-1` (`cf_dev.py:1036-1055`), so T_NEXT's frozen T0 fallback can never reach a B-only or FULL label. `test_04` spies on the source to prove T_NEXT is never called at the final step.
- The null draws from its own fresh `(9_243_000, k)` generator, one uniform legal action per user with a legal action, unconditioned on the judge (`cf_dev.py:1053-1054`, `cf_teacher.random_legal_actions`), and builds no `TeacherContext` (`cf_dev.py:835-844`). `test_05` pins the composite key, the draw count, the stream identity and the final-step silence.
- Resume saves and restores the B-null stream and refuses a different spec (`cf_dev.py:1357-1396`); `test_09` covers it per cell.

**Causality of the stored row.** The transition is the executed `x_u` with its real reward and next state (`cf_dev.py:1221-1231`); judge output enters only the label columns. Nothing in the TD path reads a judge field, and the margin reads `judge_target` with its weight only (`cf_dev.py:979-998`). `JudgeReplayBuffer.sample` consumes the same single `rng.choice` as `ReplayBuffer` (`cf_judge.py:473-481`), so a judge cell draws the same minibatch indices as `D3-T0` on the same trajectory.

**Identity and hash.** `JudgeSpec` carries the versioned rule id, canonical source set, source identities, judge id, definition and frozen η₀, and the null id and key (`cf_dev.py:374-470`); the payload adds `judge_source_identities` and `judge_rule_definition` (`dev_e0_common.py:409`), so the v2 tie order is hashed and not merely documented. Arms 1–9 payloads are untouched and `test_01` compares them against the base commit and against the five launched k = 8 hashes.

**Arms 1–9 untouched.** `teacher_labels_ext` sends `MC2` down the unchanged `else` branch, the replay class is swapped only when a `JudgeSpec` is present (`cf_dev.py:846-849`), and `test_08` asserts the frozen files (`cf_ratio`, `modqn`, `cf_credit`, `cf_tnext`, `cf_teacher`, `cf_multi_sources`, `trainer_env`, `step`) are byte-identical to the base commit and that the deployment methods are the inherited ones.

## D-1. v2 test coverage — RAISED, THEN CLOSED by lane A during this read

Raised when the suite had 11 tests and covered only v1 and the shared cell: r2 test (11) was missing, and `arb_labels` had no table test.

**Closed.** At `tests/test_mc2_judge.py` sha256 `0327b597c7c292cb301b3029973c0fc99b7cbdb1dbd4bfe1d95f50f9bc746644` (14 tests) lane A added:
- `test_02b_v2_full_with_the_gate_forced_shut_is_d0` — the right v2 analogue: with the gate shut, v2 has no margin row at all, so it must be `D0`, not `D3-T0`;
- `test_04b_v2_arbitration_order_is_x_then_a_then_b`;
- `test_04c_the_shared_b_only_cell_is_rule_independent` — contract r2 test (11);
- `test_05` parameterised over `v1-A+R` and `v2-A+R`, and `test_09` over all six cells.

I re-checked that the core semantics are unchanged at the new hashes (`cf_judge.py` `e904abaf…`, `cf_dev.py` `85dda740…`): the `arb_labels` skip / strict-compare / winner lines and `weighted_margin_loss`'s `(per_row * weight).mean()` with `w = 1[target exists]` are as reviewed above.

## D-2 to D-4 (nits, no effect on a run)

- **D-2 (cosmetic).** In `dev_e0_common.py` the docstring `"""The MULTI-D3 arms of :data:`ARMS`, …"""` now sits after `JUDGE_ARMS` / `JUDGE_RULE_IDS` / `TNEXT_FILE_SHA256` (around `:73-82`), so it documents nothing and is a dangling string statement. Move it back under `MULTI_ARMS`.
- **D-3 (reporting clarity).** `judge_override_rate` = `overrides / decision_rows` counts, in v2, A wins as well as challenger wins (`cf_judge.py:641`, `override` set for any non-`x_u` winner at `:372-375`). A reader comparing "override rate" across versions would compare different things. The contract's (vi) and `B/b_readout.py` both use `judge_challenger_wins_c_ne_a`, which is correct. Suggest a one-line note in `as_log`, or a v2-specific name.
- **D-4 (verified, keep).** `override_lead_surrogate` / `_served` mix A-win and B-win leads in v2. Diagnostics only; worth a sentence where the doses are reported.

## Not defects (checked because they would have been)

- `add_step` runs after the judge context closes but never forces an evaluation: it reads the cached base and calls `judge.kappa` only where `judge.evaluated` is already true (`cf_judge.py:576-620`).
- `challenger_wins` is gated on `challenger_tag != TAG_NONE`, so `A-only-v2` cannot accumulate challenger wins.
- `_needs_teacher_context` is true exactly for the cells that use B (`cf_dev.py:835-844`), so B-null and `A-only-v2` build no context and the historical arms are untouched.
- T_NEXT is evaluated outside the judge context; its lookahead is side-effect-free and the frozen-position cache is keyed by offset, so the order cannot change a value.
