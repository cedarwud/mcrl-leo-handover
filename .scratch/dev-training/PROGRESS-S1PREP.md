# S1-PREP progress

Agent: S1-PREP. Task: prepare the S1 formal screen (implement `T0-XEP` / arm `D3-XEP`
per Amendment 12). **Does not launch S1. Never touches formal / calibration / CONFIRM
episode sets.**

## Step log

- [x] 00. Created this file. Read Amendment 12.
- [x] 01. Read E1-FREEZE-AND-S1-PROPOSAL, E0-FREEZE-PROVISIONAL-ALGORITHM, E1-RESULT,
      Amendment 8 §3b.
- [x] 02. Read frozen dev tree: scripts/run_dev_e0.py, dev_e0_common.py (arm table),
      dev_e0_launch.py, dev_e0_baseline.py, cf_teacher.py, cf_dev.py, tests/test_cf_dev.py,
      run_b0_pilot.py, run_cf3_pilot.py.
- [ ] 03. Implement T0-XEP + D3-XEP arm.
- [ ] 04. Record the reference trajectory once (DEV-NULL namespace); record identity+sha256.
- [ ] 05. Residual-leakage diagnostic (agreement of T0-XEP vs real T0).
- [ ] 06. Verify D3-null vs Amendment 8 §3b; verify MODQN eq-(16) trainable.
- [ ] 07. Tests: clean green; each named T0-XEP mutant red individually.
- [ ] 08. Preflight <= 20 DEV episodes in own result root.
- [ ] 09. Commit named paths only.
- [ ] 10. Write .scratch/dev-training/S1-PREFLIGHT-2026-09-12.md.

## Notes
(append below as work proceeds)

### Design decisions taken (2026-09-12), before any code was written

1. **Reference-trajectory seed identity.** Amendment 12 says "recorded once under the
   DEV-NULL seed namespace". The declared DEV-NULL bases (Amendment 6 §3) are
   `9_231_000` (D2-null permutations) and `9_241_000` (D3/D4-null random actions), and
   `cf_dev.ALLOWED_SEED_RANGES` admits nothing else. `D3-XEP` is a D3-family null, so the
   reference episode is rolled on **env seed `9_241_500`, mobility seed `9_241_501`** —
   inside the declared `9_241_000..9_241_999` DEV-NULL range, well clear of the
   `k = 0..9` composite keys `(9_241_000, k)` that `D3-null` draws from. No new namespace
   is created. (Flagged in the report: the namespace is declared for RNG draws; using two
   of its values as an env/mobility pair is the closest compliant reading.)
2. **Policy that generates the reference trajectory.** Amendment 12 does not say which
   policy the reference episode is rolled under, and the visited states depend on it.
   Chosen: **T0 itself** (`cf_teacher.t0_policy()`), because §2 requires the null to be
   *plausible* — same score scale, same margin-magnitude distribution, same
   episode-phase statistics. A T0-rolled reference has a realistic lit-set / beam-load
   structure, so the structural prior the null carries is the one Amendment 12 wants
   tested. A random-legal reference would scramble the loads and make the null less
   plausible. **Flagged as a specification gap, resolved this way and declared.**
3. **Reference stored as one self-contained file** (JSON metadata + base64 float64 blob
   of the raw `channel_quality` / `beam_loads` per step per user), committed, with one
   sha256 over the whole file. Recorded once by a fail-closed recorder that refuses to
   overwrite.

### 2026-09-12: T0-XEP reference SEALED

- File: `<dev worktree>/artifacts/dev-e0/t0-xep-reference.json`
- **sha256 `9bb0c01efdd403fb0e765bd133d718f7b07273a188c9f173b39fbb112ae1900c`**
- Identity: schema `t0-xep-reference-v1`, policy `T0`, env seed `9_241_500`,
  mobility seed `9_241_501`, 10 steps x 100 users x 2 x 28 float64,
  data sha256 in the file; TLE `427e6a91...38fe9`.
- `dev_e0_xep_reference.py --verify` re-recorded it and got the same sha256 (MATCH):
  the file is byte-reproducible from its declared identity.
- Sealed into `dev_e0_common.XEP_REFERENCE_SHA256` and added to `MANIFEST_FILES`.

### 2026-09-12: Amendment 13 landed mid-task (controller message)

Scope grew: six-arm frozen S1 harness, S1-TRAIN (9_251/9_252/9_253 + k),
S1-NULL `(9_261_000, k)`, MODQN eq-(16) @1000 as a real arm, frozen `e6b063ef…`
rolled once, committed+hashed manifest, new mutant for DEV-null-stream reuse.
T0-XEP reference stays DEV-NULL (explicit Amendment 13 §5 exception) - unchanged.

### 2026-09-12: implementation + verification status

Done:
- `cf_teacher.t0_score_matrix` extracted (ONE T0 expression), `t0_xep_labels` added,
  `MECHANISMS += D3-XEP`, `TEACHERS += T0-XEP`.
- New `src/mcrl/algorithms/cf_xep.py`: reference record / seal / verify / load,
  read-only arrays, no-overwrite, canonical-form check.
- `cf_dev`: `D3-XEP` branch (`teacher_labels(..., step=t)`), reference bound ONCE in
  `__init__`, `xep_leakage()` diagnostic, DEVVAL `t0xep_*` fields, resume guard,
  S1 lane (`DevSettings.lane`, `assert_s1_seed`, `assert_s1_null_key`, `s1_triple`,
  S1 allowed/forbidden namespace tables), lane-aware `dev_rollout`.
- `dev_e0_common`: arm 8 = D3-XEP, sealed reference constants, `load_xep_reference`.
- New S1 harness: `scripts/s1_common.py`, `run_s1.py`, `s1_launch.py`,
  `s1_reference.py`, `s1_manifest.py`, `dev_e0_xep_reference.py`, `s1_mutants.sh`.
- `tests/test_s1_harness.py`: 20 tests, clean GREEN; all 11 named mutants RED
  individually (`scripts/s1_mutants.sh`).
- `tests/test_cf_dev.py`: 22 tests GREEN (4 mutant wrappers + 1 test helper updated
  for the new `step=` keyword; no behaviour change).
- S1 construct-only preflight: all 18 runs build, seeds/bootstrap/hashes verified.
- MODQN eq-(16): trains at arbitrary budget (2-episode DEV smoke) + rollout path.
- Frozen `e6b063ef…` checkpoint verified present on sat with the declared sha256.

Pending: D3-XEP DEV preflight (running), manifest artefact, commit, report.

### 2026-09-12: DONE (parked per controller Amendment 14 supplement)

- D3-XEP DEV preflight: 20 episodes, arm 8, k=0, own root in the session scratchpad.
  DEVVAL ee 9.6337e7, served 0.99633, t0xep_agreement 0.19567 vs exact random-legal
  expectation 0.03871. **No conclusion drawn** — Amendment 12 §3 applies at S1 only.
- Commits on `dev/e0-harness-20260912`:
  - `500f824f` harness (T0-XEP + S1 lane + tests)
  - `a24b90b2` `artifacts/s1/S1-MANIFEST-2026-09-12.json`,
    sha256 `7646bb00ab52778d60a48501933308c03ee1d6c39e8a9d0e1d809163983726fd`
- Report: `.scratch/dev-training/S1-PREFLIGHT-2026-09-12.md`.
- PARKED. Not dispatching the fresh-context review; no further S1 cycle; no sat compute.
