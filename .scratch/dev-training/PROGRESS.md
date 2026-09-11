# DEVHARNESS PROGRESS (E0 development-training lane) — MCRL-Dev-v0.1

Governing: `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md`
(§2 kernel, §3 seed namespaces, §5 preflight, §6 frozen E0 batch, §7 what E0 may change) + owner direction `gpt8.md`
(2026-09-12 ~20:10 UTC): E0a canary = 3 arms only, versioned immutable short cycles, never hot-patch a live trajectory.

Development lane. Nothing here is formal evidence; no statistical claim; the formal evaluation (9_111_000+i / 9_112_000+i),
calibration (9_121_000+i / 9_122_000+i) and CONFIRM (9_311_000+i / 9_312_000+i) episodes are never touched.

Worktree `/home/u24/papers/mcrl-leo-handover-dev`, branch `dev/e0-harness-20260912`, base = B1 engineering core
`63b02dc030180b83889387b031bd1c7dff4754f5`.

## Steps
- [x] 0. Read Amendment 6, the pilot learner/launcher/eval code, the LP probe rule, T0REPR (tau = 3 on VAL), the addendum §Learner
- [x] 1. Worktree `/home/u24/papers/mcrl-leo-handover-dev` on `dev/e0-harness-20260912` @ 63b02dc0
- [x] 2. Minimum E0 surface (D0, D2-T0, D2-null, D3-T0; teacher labels on the raw state; launcher + driver + refs + proctest)
- [x] 3a. Preflight unit tests 20/20 green
- [x] 3b. Named mutants each red: 22/22 (`mutants2.log`)
- [x] 3c. Launcher dry-run + process-level stop/resume on sat: DEV PROCTEST PASS
- [x] 4. agy review r1: 0 INVALIDATES, 1 BIASES (already-fixed D3 test blind spot); r2 on the launch commit running
- [x] 5. E0a LAUNCHED 20:29:10 UTC (arms 1-3, DEV k = 0, --stop-after 100, DEVVAL 24 at 100)
- [x] 6. Report written; **E0a finished, DEVVAL@100 readout and E0b proposals appended** (awaiting confirmation before E0b)

## Files (all new; `cf_ratio.py`, `cf_credit.py`, `modqn.py` are NOT edited)
- `src/mcrl/algorithms/cf_teacher.py` — T0 = LP-prev(c=1,m=0) scores/action from the RAW user state (verbatim the LP-probe /
  T0REPR arithmetic), the DEV-NULL legal-only permutation, `soft_targets` (= T0REPR's), the D2 CE loss and the D3 margin loss
  on the deployed score `S = Q~_B - eta~ Q~_E - lambda Q~_H`.
- `src/mcrl/algorithms/cf_dev.py` — seed guard (FORBIDDEN / ALLOWED ranges + composite DEV-NULL key validator),
  `DevSettings`, `TeacherReplayBuffer` (labels ride their transitions, same sampling arithmetic and generator as the pilot
  buffer), `dev_rollout` (pooled EE + per-served-user rates + T0 agreement), `CFDevTrainer` (D0 = the inherited update
  untouched; teacher path = one joint backward; calibration and the eta quarter refused outright).
- `scripts/dev_e0_common.py` — DEV/DEVVAL/DEV-NULL seeds, the frozen E0 config, per-arm config payload + hash, code manifest.
- `scripts/run_dev_e0.py` — driver: idempotent, resumable, fail-closed on manifest/config/fingerprint, DEVVAL readings.
- `scripts/dev_e0_launch.py` — launcher: RUN-MANIFEST (code digest + per-arm config hash), plan, liveness by PID+cmdline+cwd,
  `--dry-run`, `--verify`, systemd-run scope + nice 10 + 1 BLAS thread + setsid.
- `scripts/dev_e0_refs.py` — the four DEVVAL rule references rolled once (A m=2dB, LP-prev(1,0), MAX_NOMINAL_GAIN, RANDOM 9_221_000+i).
- `scripts/dev_e0_proctest.py` — process-level stop/resume + fail-closed test through the real launcher and driver.
- `tests/test_cf_dev.py` — 20 preflight tests, each with named mutants.
- `docs/dev-e0/V025-CONTROLLER-AMENDMENT-6-...md` — the governing document, inside the manifest.

## Log
- 2026-09-12T02:07+08:00 step 0: read Amendment 6 in full; pilot worktree `cf_ratio.py` / `cf_sources.py` / `run_cf3_pilot.py` /
  `cf3_launch.py` / `cf3_common.py` / `cf3_eval.py` / `cf3_proctest.py` / `tests/test_cf_ratio.py`; `.scratch/h4-probe/scripts/lp_common.py`
  (T0 = LP-prev(1,0) exactly); `.scratch/t0-repr/PROGRESS.md` + `t0_common.py` / `t0_clone.py` / `t0_collect.py` / `t0_select_tau.py`
  (28-score vector, soft target `softmax(score/tau)`, tau = 3 selected on VAL); `.scratch/cf3-pilot/DECLARATION-ADDENDUM.md` §Learner.
  Not read (instructed): `.scratch/validity-audit/`, `.scratch/reviews/`.
- 2026-09-12T02:35+08:00 step 1: worktree created at 63b02dc0 (B1 engineering core: `cf_credit.py`, `credit_mode` wiring, its tests).
- 2026-09-12T02:38-03:10+08:00 step 2: the eight files above written; `py_compile` clean.
- (session killed by the daily cost limit ~03:15+08:00; resumed 04:10+08:00 on controller instruction)
- 2026-09-12T04:12+08:00 CONFIG/CODE CHANGE (engineering-only, no seed semantics changed): `assert_dev_seed` treated the declared
  composite DEV-NULL identity `(9_231_000, k)` as two independent seeds and rejected the index `0`. Fix: `assert_dev_null_key`
  validates the pair as *declared base namespace + legal seed index* (0 <= k <= 9) and still rejects any formal namespace in either
  component; `assert_dev_seed` delegates for tuples. Reason: 5 tests red for that reason only (controller-verified). New test
  `test_composite_dev_null_keys_are_validated_as_base_plus_index` (formal bases AND formal indices rejected; the recorder in
  `test_no_development_path_produces_a_formal_seed` now checks composite keys as keys).
- 2026-09-12T04:14+08:00 step 3a: `pytest tests/test_cf_dev.py` **20 passed** (venv python, PYTHONPATH=worktree/src,
  MCRL_TLE_ROOT=/home/u24/mcrl-runtime/tle-pinned-427e6a91).

## Detached processes
- 2026-09-12T04:15:07+08:00 PID 699600 `run_mutants.sh` (cwd `/home/u24/papers/mcrl-leo-handover/.scratch/dev-training`,
  22 named mutants x their own test), log `.scratch/dev-training/mutants.log`, expected finish ~04:35+08:00.

## Config changes (versioned; nothing overwritten silently)
- **MCRL-Dev-v0.1** (this run set): the frozen Amendment 6 §6 E0 configuration — 300-episode budget, epsilon 1.0 -> 0.01 over
  round(2000*300/9000) = 67 episodes then flat, eta fixed at eta_0 = 110,507,234.83444457 bit/J (no eta update), lambda = 0,
  units s_B / s_E from the pilot `calibration.json`, credit `equal_share`, everything else as CF3 A1 (Adam 1e-3, batch 128,
  replay 50,000, hard target sync every 50 episodes, one update per decision step, P-03 filtering, gamma 1 with the
  remaining-steps feature), alpha = 1.0, tau = 3, tau_s = 1, m = 0.15, lambda_E = 1.0, DEV triple k = 0 for every arm.
  **E0a runs this configuration and stops at episode 100** (`--stop-after 100`), so the epsilon schedule and the config hash are
  the frozen ones and a later continuation to 300 is an intentional resume of the SAME version, not a new trajectory.
- 2026-09-12T04:20+08:00 step 3b/3c: first mutant runner mis-classified every result (its regex read `pytest -x` tail lines, not the
  summary); re-run with exit-code detection (`run_mutants2.sh`, `mutants2.log`) gave 21/22 red and found ONE real preflight gap:
  `d3_no_margin` left `test_d3_margin_loss_properties` green because the fixture's best legal alternative sat 0.5 below the teacher
  action, outside the 0.15 margin, so the margin term never bound. TEST FIX (test-only, no production path): the alternative now sits
  0.05 below the teacher action and the loss is exactly the margin violation (0.1) -> mutant red. **22/22 red**, file 20/20 green.
- 2026-09-12T04:21+08:00 process-level preflight on sat (`dev_e0_proctest.py`, smoke, arm 3 = the arm with the extra DEV-NULL
  generator): DEV PROCTEST PASS -- stop at episode 2, resume, policy bit-identical to the uninterrupted run, identical DEV-NULL
  generator state and per-episode bits/losses/teacher losses, logs [0,1,2] with no duplicate, a second launch while live started
  nothing, and the launcher refused a changed configuration against the same manifest (its T2 selector was also fixed: --smoke pins
  the budget, so the mismatch is now made by dropping --smoke).
- 2026-09-12T04:22+08:00 commit `772481c4dbdcb69d729168d513366a4a5ecddf46` (preflight fixes; the reviewed commit was
  `f90421502b87311ddf633a52ca54625c91cf530c`, and the only delta between them is these two test-harness files).
- 2026-09-12T04:25+08:00 staged sat workspace `/home/sat/mcrl-v025-dev-e0-ws/`: `git archive` of 772481c4 shipped with
  `cat | ssh sat 'cat > ...'` (never scp), tar sha256 `12936b2b42b978cca44b80430d583d1d1a8526864c528cd788b152b0ba15e77c` identical on
  both ends, `tree/COMMIT` written; import check: `mcrl` = ws tree, TLE file set `427e6a91...8fe9`, prereg digest `3a920671...73f4`,
  config 300 / eps decay 67 / lr 0.001 / batch 128 / replay 50,000 / sync 50 / gamma 1 / (100,50,50) tanh, eta_0 110,507,234.83444457.
- 2026-09-12T04:26+08:00 launcher dry-run on the real E0a root: manifest written, three distinct config hashes, nothing started.
- 2026-09-12T04:26-04:29+08:00 DEVVAL rule references rolled once (one process): T0 = LP-prev(1,0) 1.176642e8, A m=2dB 1.115812e8,
  MAX_NOMINAL_GAIN 1.100346e8, RANDOM 5.199857e7 bit/J; T0 reference agrees with the stored T0 labels 100.00 %, RANDOM 3.76 % (chance).
- 2026-09-12T04:29:10+08:00 (20:29:10 UTC) **E0a LAUNCHED**, three arms, see `E0-BATCH-1-2026-09-12.md`.
- 2026-09-12T04:30+08:00 optimizer steps confirmed at episode 25 in all three arms (non-zero TD losses on all three heads,
  non-zero teacher loss in arms 2-3, replay 25,000): D0 agreeT0 0.277, D2-T0 0.457, D2-null 0.281 -- proof of life only.
- CARRIED FORWARD to E0b: the review's BIASES item is closed for arms 1-3 (fixed before launch); D3-T0 (arm 4) enters E0b only with
  the strengthened D3 margin test in place, which it now is.

## Detached processes (current)
- sat PID 3570617 `run_dev_e0.py --arm 1 --seed-index 0 --root /home/sat/mcrl-v025-dev-e0-ws/runs-e0a ... --stop-after 100`,
  cwd `/home/sat/mcrl-v025-dev-e0-ws/tree`, log `runs-e0a/E0-1-k0.log`, cfg `5d4f54e019a4e44f`, expected finish ~20:36-20:40 UTC.
- sat PID 3570618 same with `--arm 2`, log `runs-e0a/E0-2-k0.log`, cfg `3dd5e6f1d14922da`.
- sat PID 3570619 same with `--arm 3`, log `runs-e0a/E0-3-k0.log`, cfg `c19d2596c5a745a7`.
- local PID 705869 agy review pass 2 (BASE 63b02dc0, HEAD 772481c4), log `agy-e0-r2.log`, output `AGY-E0-REVIEW.md`.
- finished: local mutant runners (`mutants.log`, `mutants2.log`); sat DEVVAL references (`results/DEVVAL-REFERENCES.json`).
- 2026-09-12T04:33+08:00 (20:33 UTC) all three E0a arms finished: `stopped-at`, 100 episodes, wall 216-217 s, RSS ~1.96 GB,
  10 updates/episode, replay full at 50,000. No development process alive on sat.
- 2026-09-12T04:38+08:00 agy review pass 2 on the launch commit `772481c4` finished: **0 INVALIDATES, 0 BIASES**, "the E0
  development training launch may proceed" (`AGY-E0-REVIEW.md`; pass 1 on `f9042150` kept as `AGY-E0-REVIEW-r1-f9042150.md`).
- 2026-09-12T04:50+08:00 DEVVAL@100 readout written into `E0-BATCH-1-2026-09-12.md`: D0 1.03059357e8, D2-T0 1.07431853e8,
  D2-null 1.00956333e8 bit/J against the DEVVAL references T0 1.176642e8 / A m=2dB 1.115812e8 / MAX_NOMINAL_GAIN 1.100346e8 /
  RANDOM 5.199857e7. Paired per-episode: D2-T0 > D0 23/24, D2-T0 > D2-null 24/24, D0 > D2-null 18/24. Greedy agreement with T0:
  0.3805 / 0.5382 / 0.3760; in-run stored-teacher-action agreement with T0: 1.0 / 1.0 / 0.0386 (chance). Direction only.
- 2026-09-12T04:52+08:00 E0b proposals appended with config hashes (B1 resume to 300 at unchanged hashes; B2 add D3-T0
  `9a1a67c498376d32`; B3 tau sweep `cd424977244eedea` / `b2c124ae12ce477f`; B4 alpha sweep `5679ddb2931a70ca` /
  `3d7743a644990ca3`; B5 k = 1 replicate `50c9d4a0e19f1931` / `67d3dc6eba2ef687` / `28b99027bda43d2e`). NOT launched: the
  coordinator confirms first.

## Wave 1 of E0b — launched 2026-09-11 20:53:52-20:54:43 UTC (controller-authorised 20:55 UTC message; B4 deferred, B3 = wave 2)
Gate re-verified immediately before arm 4 started: `DEV_MUTANT=d3_no_margin pytest -k test_d3_margin_loss_properties` -> **RED**
(and the clean D3 + teacher-weight tests green) at commit `772481c4`. 7 development processes; the B2-representability lane may
hold up to 3 more; limit 8 for this lane's own processes was respected (7).

| arm | version / status | config hash | PID | root | boundary | DEVVAL reads |
|---|---|---|---|---|---|---|
| D0 k0 | MCRL-Dev-v0.1, **intentional resume** from ep 100 | `5d4f54e019a4e44f` | 3577210 | `runs-e0a` | to 300 | 200, 300 |
| D2-T0 k0 | MCRL-Dev-v0.1, **intentional resume** from ep 100 | `3dd5e6f1d14922da` | 3577211 | `runs-e0a` | to 300 | 200, 300 |
| D2-null k0 | MCRL-Dev-v0.1, **intentional resume** from ep 100 | `c19d2596c5a745a7` | 3577212 | `runs-e0a` | to 300 | 200, 300 |
| D3-T0 k0 | MCRL-Dev-v0.1 arm 4, **fresh start** | `9a1a67c498376d32` | 3577336 | `runs-e0b-d3` | to 300 | 100, 200, 300 |
| D0 k1 | MCRL-Dev-v0.1 k=1, **fresh start** | `50c9d4a0e19f1931` | 3577470 | `runs-e0b-k1` | `--stop-after 100` | 100 |
| D2-T0 k1 | MCRL-Dev-v0.1 k=1, **fresh start** | `67d3dc6eba2ef687` | 3577471 | `runs-e0b-k1` | `--stop-after 100` | 100 |
| D2-null k1 | MCRL-Dev-v0.1 k=1 (DEV-NULL key (9_231_000, 1)), **fresh start** | `28b99027bda43d2e` | 3577472 | `runs-e0b-k1` | `--stop-after 100` | 100 |

- cwd for all seven: `/home/sat/mcrl-v025-dev-e0-ws/tree`; commit `772481c4`, code digest `ccbcb02d5b7c`; `nice -n 10`,
  `systemd-run --user --scope -p MemoryMax=5G`, OMP/MKL/OPENBLAS/NUMEXPR = 1, `setsid nohup ... </dev/null`, pinned TLE
  `427e6a91...8fe9`, `calibration.json` read-only from the pilot premeasure (sha256 `59952214...4562d`).
- The three k=0 arms logged `resuming at episode 100`; their configuration hash is unchanged, so this is the SAME trajectory
  continued (the process test showed a resumed run is bit-identical to an uninterrupted one), not a new version.
- k = 1 uses the same frozen 300-episode configuration stopped at 100 (exactly as E0a did), which is what keeps its config
  hashes equal to the authorised ones; a later continuation to 300 would again be an intentional resume.
- Expected finish (7 processes contending, ~2.2-6 s/episode): k = 1 arms ~21:10-21:15 UTC, the k = 0 resumes (200 more
  episodes + 2 DEVVALs) ~21:20-21:35 UTC, D3-T0 (300 episodes + 3 DEVVALs) ~21:30-21:45 UTC.
- Wave 2 (authorised, launch as slots free): B3 tau sweep on D2-T0 at k = 0 -- v0.2a tau = 1 `cd424977244eedea`, v0.2b
  tau = 0.3 `b2c124ae12ce477f`, 100 episodes each, fresh start, new versions. B4 (alpha) deferred by the controller.

## Wave 1 finished (2026-09-11 ~21:50 UTC) and wave 2 launched (21:56 UTC)
- Wave 1 results are in `E0-BATCH-1-2026-09-12.md` (DEVVAL tables for k = 0 at 100/200/300, D3-T0 at 100/200/300, k = 1 at 100,
  paired per-episode counts, end-of-run training summaries). Headline directions, no statistical claim:
  ordering **D2-T0 > D0 > D2-null holds at 100, 200 and 300 on k = 0** and **at 100 on k = 1** (D2-T0 > D0 24/24 paired,
  +8.33 %); **D3-T0 sits above both at every depth** (113.1e6 bit/J at 300 = 1.028 of MAX_NOMINAL_GAIN, 0.961 of T0,
  agreement 0.716, regret 0.146, margin loss 0.099). Non-monotonicity worth naming: D2-T0's EE peaked at 200 and dipped
  0.34 % at 300 while its agreement kept rising; D2-null dipped at 200 and recovered at 300, never reaching D0.
- **Wave 2 (authorised)** launched from a SEPARATE tree so v0.1 stays resumable:
  - MCRL-Dev-v0.2a tau = 1, hash `cd424977244eedea`, PID 3594388, root `runs-e0b-tau1`, fresh start, `--stop-after 100`, DEVVAL 100.
  - MCRL-Dev-v0.2b tau = 0.3, hash `b2c124ae12ce477f`, PID 3594430, root `runs-e0b-tau0p3`, fresh start, `--stop-after 100`, DEVVAL 100.
  - cwd for both `/home/sat/mcrl-v025-dev-e0-ws/tree-v0.2`, commit `52d253c48476de96d286df0069bad04c62c1720f`, code digest
    `a8fbe1d330eb`; tar sha256 `9543e05bc959d3f555d880d51d1d2d95e65461974ea76fd54a6f2d06824bdd60` identical on both ends.
  - CODE CHANGE (additive, default-preserving): `--tau` on the driver and the launcher, threaded into `e0_dev_settings` /
    `arm_config_payload`. With no `--tau` the payload and hash are unchanged (arm 2 k0 -> `3dd5e6f1d14922da`, verified), and
    both authorised prospective hashes reproduce exactly. Reason: the CE analysis above plus wave 1's D3 result. Tests run on
    the change: config-hash, launcher dry-run, seed-namespace and composite-key tests green; the two dry-runs printed the
    authorised hashes before launch.
  - B4 (alpha) remains deferred by the controller; learning rate, clipping and target cadence remain unproposed (no DEV
    evidence of instability: all losses finite, Q_E TD loss ~1.5-2.6e-2 at the end of every run, RSS <= 2.26 GB).

## Convergence funnel (controller directive 2026-09-11 22:15 UTC)
- **tau sweep landed and is closed.** v0.2a tau = 1 `cd424977244eedea` DEVVAL@100 112,317,765; v0.2b tau = 0.3
  `b2c124ae12ce477f` 112,325,427; both +4.55 % / +4.56 % over tau = 3 (24/24 paired) and both -0.11 % against D3-T0 at the same
  depth (9/24 and 10/24). **ADOPTED: tau = 1 (v0.2a) is the D2 soft-comparator configuration from here on**; tau = 3 is never
  presented as D2's representative result again. Reason on record: tau = 3 was T0REPR's VAL choice for a clone with 28 free
  logits, and at tau = 3 only ~0.11 nats of the target is learnable for a scalar score pinned by the TD objective.
  No alpha sweep, no learning-rate / clipping / target-cadence sweep (directive item 1).
- **Item 2 done: D3-T0 at DEV k = 1** (`2f92f0c496866ff4`, PID 3596787, root `runs-e0b-d3-k1`, tree-v0.2, fresh start,
  `--stop-after 100`) finished in 194 s: DEVVAL@100 **112,551,340** bit/J, +13.34 % over the paired D0 (24/24) and +4.63 % over
  the paired D2-T0 tau = 3 (24/24), served 0.99850, agreement with T0 0.7077, regret 0.160.
- **Item 5 done: the frozen baseline MODQN eq-(16) on DEVVAL** (`results/DEVVAL-BASELINE-MODQN.json`, checkpoint sha256
  `e6b063ef...c28b`, episode 8999, greedy, no training): **94,413,179** bit/J, served 0.99846, beams 66.72, H_inter 0.2212,
  p10 8.146e7, agreement with T0 0.2787. Development champion vs the paper baseline: D3-T0 +19.8 % (k0/300) and +19.2 %
  (k1/100); D2-T0 tau = 1 +19.0 %; D0 +11.7 % / +5.2 %. Script `scripts/dev_e0_baseline.py`, commit `fc4f5bc7`.
- **Item 3 implemented: D3-null** (commit `05aadf1bb24a9e3a730975227fbf27ab7760deb9`, minimal additive diff on top of
  `fc4f5bc7`): the same D3 loss / margin / lambda_E / schedule / masks / gradient path with the teacher action replaced by a
  seeded uniform LEGAL action from the declared DEV-NULL namespace `(9_241_000, k)`; the null stores zeros where the T0 arms
  store T0's scores, so no T0 quantity enters any loss input. Arm 7 = D3-null / equal_share. Tests: whole file **22 passed**;
  named mutants for the new properties all RED (`mutants-d3null.log`: d3null_target_is_t0_action,
  d3null_target_may_be_illegal, d3null_uses_train_rng, d3null_scores_carry_t0, d3null_key_dropped_from_hash,
  plus teacher_applied_at_zero_weight on the extended zero-weight test, which now covers D3-null at lambda_E = 0).
  Fresh-context review of the minimal diff (`fc4f5bc7..05aadf1b`) running -> `AGY-D3NULL-REVIEW.md`; the D3-null runs launch
  only after it comes back.
- 2026-09-11T22:24 UTC D3-null review (delta only, `fc4f5bc7..05aadf1b`): **0 INVALIDATES, 0 BIASES, PROCEED**
  (`AGY-D3NULL-REVIEW.md`). Clean file 22/22; every named D3-null mutant red individually (`mutants-d3null.log`).
- 2026-09-11T22:26:20 UTC launched **D3-null k = 0** (`43848246efa4`, PID 3603588) and **k = 1** (`42fea0984d11`, PID 3603589),
  root `runs-e0b-d3null`, tree-v0.4 (commit `05aadf1b`, digest `7440236979d6`), fresh starts, `--stop-after 100`. Both finished
  in ~197 s: EE 57,469,863 (k0, -44.24 % vs paired D0, 0/24) and 60,547,627 (k1, -39.03 %, 0/24), served 0.923 / 0.926,
  agreement 0.124 / 0.049, regret 2.91 / 2.81.
- **PROMOTION APPLIED (rule fixed before the numbers): D3-T0 = PROVISIONAL PRIMARY INJECTION MECHANISM** -- it beats the paired
  D0 (+9.11 % k0, +13.34 % k1, 24/24 both) and the matched D3-null (x1.96, x1.86, 24/24 both) in the same direction on both
  seeds with no QoS collapse (served 0.9985+, p10 40-50 % above D0, minimum served-user rate above D0's).
- 2026-09-11T22:39:29 UTC launched the **k = 2 trio** to 100 episodes, root `runs-e0b-k2`, tree-v0.4, fresh starts,
  `--stop-after 100`: D0 `076cd491ad83` PID 3607936, D3-T0 `a46c770653b4` PID 3607937, D3-null `d2bd70c8bdcf` PID 3607938.
- **Item A applied**: the strongest soft comparator is **D2-T0 tau = 0.3** (`b2c124ae12ce477f`) under the outcome-independent
  rule; tau = 1 and tau = 0.3 are tied (+0.007 %) and no superiority claim is made; the earlier "adopt tau = 1" line in the
  report is explicitly superseded. D2 tuning stays closed.
- **Item D applied**: `scripts/dev_e0_aggregate.py` (commit `27f69edf84eefeb8874339bc6c8c533469fa7f4b`) keys every result by
  `(run_root, config_hash, seed_index, checkpoint_episode)`, refuses to merge two differing records with the same identity and
  prints the identity in each row; shipped to sat as `tools/dev_e0_aggregate.py` (sha256 identical both ends) and re-emitted
  all 20 existing results into `results/DEV-AGGREGATE.{json,md}`.
- 2026-09-11T22:43:52 UTC **k = 2 trio landed and preserves direction and QoS**: D0 103,531,085; **D3-T0 113,082,503
  (+9.23 % vs paired D0, 24/24, served 0.99813, p10 1.246e8, min 6.79e6, agreement 0.697, regret 0.153, +19.77 % over the
  frozen baseline)**; D3-null 46,917,434 (-54.68 %, 0/24, served 0.929). Config hashes `076cd491ad83` / `a46c770653b4` /
  `d2bd70c8bdcf`, root `runs-e0b-k2`.
- **FREEZE APPLIED** (rule fixed before the numbers): `.scratch/dev-training/E0-FREEZE-PROVISIONAL-ALGORITHM-2026-09-12.md` --
  B1 execution contract + the current ratio learner + T0 + D3 large-margin injection (m = 0.15, lambda_E = 1.0), with
  D2-T0 tau = 0.3 as the strongest soft comparator and D3-null as the matched null; code commit `05aadf1b`. Development
  freeze only; not formal evidence. The aggregator now holds 23 results under the collision-safe identity
  (`results/DEV-AGGREGATE.{json,md}`).
- No development process is running on sat after this point; no E1 run is launched (E1's design is the controller's to declare).

## E1 launched (Amendment 10, read in full before launch) — 2026-09-11 23:07 UTC
Nine fresh-start runs, 300 episodes, DEVVAL 100/200/300, code `05aadf1b` (the frozen provisional algorithm), cwd
`/home/sat/mcrl-v025-dev-e0-ws/tree-v0.4`. Details and the pre-declared reading rule: `E1-LAUNCH-2026-09-12.md`.
- `runs-e1-d0-d3`: D0 k3 `945927542022` PID 3616542, k4 `673611ca6da3` 3616543, k5 `ddd5bab02457` 3616544;
  D3-T0 k3 `ccca3463753d` 3616545, k4 `ce689b57833f` 3616546, k5 `9bf13b57e608` 3616547.
- `runs-e1-d2tau0p3` (`--tau 0.3`): D2-T0 k3 `87e8fce4b4d8` PID 3616588, k4 `9905fcc0a2f1` 3616589, k5 `bab4ac8d4656` 3616590.
- Two roots because `--tau` is per launcher call and tau is inside the config hash: D0 and D3-T0 keep the frozen default
  (which neither mechanism reads), only D2 carries tau = 0.3. D3-null is NOT re-run (Amendment 10 §2). Seeds k = 3, 4, 5 only;
  k = 0-2 are spent, k = 6-9 reserved. 9 processes, leaving the Catfish-2 lane its 3.
- Decision checkpoint is ep 300 only; 100 and 200 are divergence / bug / QoS-collapse tripwires. No configuration may change
  on an intermediate reading.
