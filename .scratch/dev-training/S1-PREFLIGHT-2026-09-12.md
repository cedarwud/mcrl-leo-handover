# S1-PREP preflight — `T0-XEP` (Amendment 12) and the frozen S1 harness (Amendment 13)

Date 2026-09-12. Worktree `/home/u24/papers/mcrl-leo-handover-dev`, branch
`dev/e0-harness-20260912`, base `27f69edf` (code `05aadf1b`). Commits `500f824f` (harness) and
`a24b90b2` (manifest).

**Nothing here is evidence.** No formal evaluation, calibration or CONFIRM episode was touched.
S1 was **not launched**. All training in this document is 20 DEV episodes plus a 2-episode MODQN
smoke, both on DEV seeds.

---

## 1. `T0-XEP` — what was implemented

At the learner's step `t`, `T0-XEP` computes T0's ordinary frozen score
`log2(1 + max(γ_a, 0)) − c·[N_a == 0]` with `c = 1`, `m = 0`, **unmodified**, on the state recorded
at step `t` of a fixed pre-recorded reference episode, then takes the argmax **restricted to the
learner's current legal action mask**. The mechanism is unchanged D3 (`m = 0.15`, `λ_E = 1.0`), the
arm is `D3-XEP`.

| where | what |
|---|---|
| `src/mcrl/algorithms/cf_teacher.py` | `t0_score_matrix()` — the score half of `t0_scores()`, extracted so T0 and T0-XEP provably share **one** expression (a test asserts they are bit-equal). `t0_xep_labels(reference_states, current_mask)`. `MECHANISMS += "D3-XEP"`, `TEACHERS += "T0-XEP"`. |
| `src/mcrl/algorithms/cf_xep.py` (new) | The reference trajectory: record / seal / verify / load. Read-only arrays, no-overwrite writer, canonical-form check, fail-closed `states_at(t)` with no wraparound and no clamping. |
| `src/mcrl/algorithms/cf_dev.py` | The `D3-XEP` branch of `teacher_labels(..., step=t)`; the reference bound **once** in `__init__` (`_bind_xep_reference`) and checked against the configuration's declaration; the D3 loss dispatch extended; the resume guard; the DEVVAL probe. |
| `scripts/dev_e0_common.py` | Arm 8 = `D3-XEP`; the sealed reference constants; `load_xep_reference()`; the reference file added to `MANIFEST_FILES`. |
| `scripts/dev_e0_xep_reference.py` (new) | The one-shot recorder, with `--verify`. |

### The reference trajectory — sealed identity

```
file    <tree>/artifacts/dev-e0/t0-xep-reference.json          (597,722 bytes)
sha256  9bb0c01efdd403fb0e765bd133d718f7b07273a188c9f173b39fbb112ae1900c
schema  t0-xep-reference-v1
policy  T0            (cf_teacher.t0_policy(), the frozen teacher itself)
env seed        9_241_500      (DEV-NULL, Amendment 6 §3 range 9_241_000..999)
mobility seed   9_241_501      (DEV-NULL, same range)
shape   10 steps x 100 users x 2 x 28 float64, little-endian
        plane 0 = raw channel_quality, plane 1 = raw beam_loads
data sha256  efb75894faa234d9485e17967a784710a9c37173ce5b5dad333499d27fbe71a2
TLE     427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9
```

Sidecar `artifacts/dev-e0/t0-xep-reference-provenance.json` holds the volatile provenance (wall
clock, code manifest) and is deliberately **not** part of the identity, so the reference file is a
pure function of `(schema, policy, seeds, users, steps)`.
`dev_e0_xep_reference.py --verify` re-recorded it and got the **same sha256** — the reference is
byte-reproducible, and a reviewer can check it without destroying it.

It is recorded **once**: `write_reference` refuses to overwrite an existing file, `load_reference`
refuses any file whose sha256 is not the declared one, the sha256 is a `DevSettings` field and
therefore inside every `D3-XEP` configuration hash, and `load_training_state_dict` refuses a resume
written against a different reference.

### The slot-indexing caveat — stated plainly, not fixed

The 28 candidate slots are **satellite-major, beam-minor over the visible set**
(`UserState.channel_quality`/`beam_loads`, shape `L*K = 4*7`). Slot `k` in the reference episode is
therefore **not the same physical beam** as slot `k` in the learner's current episode, and user row
`u` is **not the same user** either. Both are intended: that decorrelation is what makes the null
uninformative while keeping the score scale, the margin-magnitude distribution and the
episode-phase statistics matched (step `t` is matched to step `t`). Nothing in the implementation
tries to re-align slots or users, and nothing should.

### Specification gap in Amendment 12, resolved and declared (ratified by the controller)

Amendment 12 §2 does not say **which policy rolls the reference episode**, and the states visited
depend on it. Resolved by rolling it under **T0 itself**: a T0-rolled reference has a realistic
lit-set and beam-load structure, so the null delivers the structural prior §1(b) exists to test,
whereas a random-legal reference would scramble the loads and make the null less plausible under
§4. Declared before recording, in `dev_e0_common.XEP_REF_POLICY`, and in the reference file's own
identity (`policy: "T0"`), so it is inside the configuration hash.

Second, smaller reading: Amendment 12 §2 says "recorded once under the **DEV-NULL** seed namespace".
The declared DEV-NULL namespaces (Amendment 6 §3) are RNG-draw namespaces, not env/mobility
namespaces. The closest compliant reading — two values inside the D3-family DEV-NULL range
`9_241_000..999`, clear of the `k = 0..9` composite keys `(9_241_000, k)` that `D3-null` draws
from — was used. No new namespace was created.

## 2. The residual-leakage diagnostic

`D3-XEP` DEVVAL records now carry, on the same states as the existing `t0_agreement` /
`t0_score_regret`:

| field | meaning |
|---|---|
| `t0xep_agreement` | fraction of decisions where **T0-XEP** advised what the **real** T0 would have done |
| `t0xep_score_regret` | mean `T0score(a_T0) − T0score(a_XEP)`, in T0's own units |
| `t0xep_random_legal_agreement_expected` | the **exact** uniform-random-legal expectation `mean(1/\|legal\|)` on the same rows — computed in closed form, no draw, no seed |
| `t0xep_decisions`, `xep_reference` | the row count and the reference's full identity |

The comparison lives in one named function, `cf_dev.xep_leakage(xep_actions, t0_actions, legal,
t0_scores)`, whose two action arguments are two different teachers — the mutant that passes the
null's own actions as both is individually red. The probe **advises but never acts**: a test asserts
that a rollout with and without it produces bit-identical `ee`, `bits`, `joules`, `served`,
`t0_agreement` and `t0_score_regret`.

The training log gained the same three quantities at collection time
(`teacher_action_agrees_with_t0`, `teacher_action_t0_score_regret`,
`random_legal_agrees_with_t0_expected`) for every arm, plus `xep_reference_sha256` on `D3-XEP`.

## 3. What was verified, not re-invented

### `D3-null` against Amendment 8 §3b — matches verbatim, nothing changed

| §3b requirement | frozen tree | verdict |
|---|---|---|
| same D3 loss, margin, `λ_E`, schedule, masks, gradient path | `_teacher_loss` calls the same `cft.d3_margin_loss(scores, mask, a_t, d.margin)` scaled by `d.lambda_e`; `e0_dev_settings` gives it `MARGIN0 = 0.15`, `LAMBDA_E0 = 1.0` like `D3-T0` | matches |
| target = seeded uniform random **legal** action from `(9_241_000, k)` | `_null_key_for("D3-null", k) → (9_241_000, k)`; `_null_rng = default_rng(key)`; `cft.random_legal_actions(legal, self._null_rng)` draws `rng.choice(valid)` per row | matches |
| T0 computable for diagnostics only; neither its action nor its scores in any loss input | `teacher_labels` stores `used_scores = zeros_like(scores)` and a random `used_acts`; the D3 loss reads only `teacher_action`; `t0_action` is stored for diagnostics and no loss reads it | matches |
| config hash covers mechanism, teacher identity and null key | all three are `DevSettings` fields and `dev_settings` is inside `arm_config_payload` | matches |

**Nothing was changed in `D3-null`'s development-lane behaviour.** Amendment 13 §5 moves only its
seed: at S1 it draws from `S1-NULL = (9_261_000, k)` and the development stream is refused outright
in that lane. That is seed isolation, not a mechanism change, and the two arms' losses are
identical.

### `MODQN eq-(16)` — trainable at an arbitrary budget

- `S.s1_config(record, 6, N)` returns `td_bootstrap_mode = eq16-per-head-max`, the prereg's own
  discount (`0.9`), objective weights `(0.5, 0.3, 0.2)`, `episodes = N`, and the budget-scaled
  epsilon schedule `round(2000 N / 9000)` (222 at N = 1000).
- Trained for real: 2 episodes on **DEV** seeds `9_201_000 / 9_202_000 / 9_203_000` in 7.9 s, then
  rolled greedily through the S1 evaluation code path on 2 DEVVAL episodes
  (`ee 8.867e7`, `served 0.999`, `t0_agreement 0.2575`). Path works end to end.
- Construct-only at the real S1 budget: all three seeds build at `episodes = 1000` with the correct
  recipe and the S1-TRAIN triple. **No S1-TRAIN training was run.**
- Frozen 9000-episode reference: the checkpoint exists on `sat` at
  `/home/sat/mcrl-v025-cf3-pilot-ws/tree/artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`
  with sha256 `e6b063ef…c28b`, the declared one. `scripts/s1_reference.py` rolls it once on the
  formal evaluation episodes with no optimizer; **it was not run** (that would spend the formal set).

**Two findings a future launcher must know.**

1. `scripts/run_b0_pilot.py`, the existing MODQN driver, leaves `epsilon_decay_episodes` at the
   frozen **2000**, so a 1000-episode run under it would still be exploring at the end. That would
   confound the same-budget win gate. The S1 harness therefore does **not** use it: `run_s1.py`
   gives the MODQN arm the same compressed schedule (222) as the CF arms. This is a real choice, not
   a detail — it is the only sane way to read "same budget", and it is recorded in the manifest.
2. `scripts/run_cf3_pilot.py --arm A0`, the other existing MODQN path, reads the **calibration**
   episodes at 100/250/500/750/1000 for its `readings.jsonl`. It must not be used for S1.

## 4. The S1 harness (Amendment 13)

New: `scripts/s1_common.py`, `scripts/run_s1.py`, `scripts/s1_launch.py`,
`scripts/s1_reference.py`, `scripts/s1_manifest.py`.

- **Six trained arms**, exactly Amendment 13 §3: `D0`, `D3-T0`, `D3-null`, `D3-XEP`,
  `D2-T0 τ = 0.3`, `MODQN eq-(16)`. Plus the rolled frozen reference. D1 / D4 / B2 / exact-DR are
  not resurrected.
- **`S1-TRAIN`** `9_251_000 / 9_252_000 / 9_253_000 + k`, the same-index triple for all six arms.
- **`S1-NULL`** `(9_261_000, k)` for `D3-null`.
- **Formal evaluation** `9_111_000+i / 9_112_000+i`, read **once**, at episode 1000. Intermediate
  reads would spend the formal set repeatedly for no declared purpose, so `S1_EVAL_AT = (1000,)`.
  *(Declared choice; flag it if the controller wants a learning curve on the formal set instead.)*
- **A separate lane guard.** `DevSettings.lane` selects between the development seed contract and
  `assert_s1_seed` / `assert_s1_null_key`. The S1 whitelist is the S1-TRAIN triple, the formal
  evaluation episodes and the trainer's derived substreams; **every** DEV / DEVVAL / DEV-NULL /
  calibration / CONFIRM value is named in the forbidden list so a reused development seed reports as
  seed isolation broken rather than "outside every namespace". The development guard
  `assert_dev_seed` is untouched and still refuses the S1 namespaces.
- **Complete matrix or nothing.** `s1_launch.assert_complete_matrix` refuses any partial spec list
  outside `--dry-run` / `--i-am-resuming`, before the manifest is written and before any process
  starts.

### Derived substreams — the part the controller could not check from outside the trainer

With `S1-TRAIN train = 9_251_000 + k`, the trainers build exactly these integer streams (enumerated
from the constructed objects, not read off the source):

| stream | value at k = 0,1,2 | in a reserved namespace? |
|---|---|---|
| `_train_rng = default_rng(train)` | 9_251_000 / 001 / 002 | no — S1-TRAIN |
| `_env_rng` | 9_252_000 / 001 / 002 | no — S1-TRAIN |
| `_mobility_rng` | 9_253_000 / 001 / 002 | no — S1-TRAIN |
| `_catfish_rng = default_rng(train + 70_001)` | 9_321_001 / 002 / 003 | no |
| `_penalty_rng.manual_seed(train + 90_211)` (torch) | 9_341_211 / 212 / 213 | no |
| `NULL_RNG_OFFSET = 80_000` (train + 80_000 → 9_331_00x) | **not constructed** — the constant is unused in this tree, and the E0/S1 kernel refuses source pools | n/a |

None collides with `9_111`/`9_112` (evaluation), `9_121`/`9_122` (calibration),
`9_301`–`9_303`/`9_311`/`9_312` (CONFIRM) or any DEV / DEVVAL / DEV-NULL range. `run_s1.py` asserts
this at construction for every arm (`assert_seed_isolation`), so a future change to the trainer's
internals fails closed instead of silently colliding.

## 5. The committed, hashed manifest

```
artifacts/s1/S1-MANIFEST-2026-09-12.json
sha256 7646bb00ab52778d60a48501933308c03ee1d6c39e8a9d0e1d809163983726fd
code commit 500f824f6df3d391fa0bd40fe9b3e1c549ffad6a, code digest 55e4051dc511
calibration 59952214a68469d9eccef292fa0eadf41e897ff74abd4b6cbff0635ee1a4562d
```

18 runs, 18 distinct configuration hashes. It carries the arm list and roles, the namespaces plus an
explicit never-touched list, the sealed T0-XEP reference sha256, the 1000-episode depth, the single
terminal read, the frozen hyperparameters (η fixed at η₀, λ = 0, `equal_share`, D3 `m = 0.15` /
`λ_E = 1.0`, D2 `τ = 0.3`, ε decay 222), the rolled reference and its checkpoint sha256, and the
reading rules of Amendments 4, 12 and 13. `s1_manifest.py --check` regenerates it byte for byte.

## 6. Tests

`tests/test_s1_harness.py` — 20 tests, clean **green**. `tests/test_cf_dev.py` — 22 tests, green
(four mutant wrappers and one helper updated for the new `step=` keyword; no behaviour change).

`bash scripts/s1_mutants.sh` runs the suite once per named mutant. **All 11 red, individually:**

| mutant | what it breaks | tests that go red |
|---|---|---|
| `xep_reference_state_not_substituted` | scores the CURRENT state instead of the reference's | `test_the_d3_xep_loss_is_the_d3_loss_pointed_at_the_reference_action` |
| `xep_current_mask_not_applied` | argmax over all 28 instead of the learner's legal set | `test_t0_xep_scores_the_reference_state_and_argmaxes_the_current_mask` (+2) |
| `xep_reference_regenerated_per_episode` | re-records the reference at each episode start | `test_the_bound_reference_is_fixed_for_the_whole_run` (+1) |
| `xep_agreement_against_itself` | scores T0-XEP against T0-XEP instead of the real T0 | `test_xep_leakage_scores_the_null_against_the_real_teacher`, `test_devval_reports_t0_xep_agreement_with_the_real_t0` |
| `xep_reference_missing_from_config_hash` | drops the reference identity from the payload | `test_the_reference_identity_is_in_the_configuration_hash` |
| `s1_null_uses_dev_stream` | `D3-null` at S1 draws from `(9_241_000, k)` | `test_s1_null_draws_from_the_fresh_formal_namespace` (+1) |
| `s1_reuses_dev_training_triple` | S1 trains on the DEV triple | `test_s1_trains_on_the_s1_triple_and_evaluates_on_the_formal_set` |
| `s1_evaluates_on_calibration` | S1 reads the calibration episodes | 3 tests |
| `s1_modqn_uses_shared_bootstrap` | the win-gate arm silently stops being eq-(16) | `test_the_modqn_arm_keeps_the_eq16_recipe_at_the_shared_budget` |
| `s1_manifest_drops_arm_configs` | the declaration loses its per-run hashes | `test_the_frozen_manifest_carries_everything_that_must_be_hashed` |
| `s1_partial_matrix_allowed` | a subset of arms can open the formal set | `test_the_formal_set_is_opened_with_the_complete_matrix_or_not_at_all` |

The launcher's complete-matrix rule is tested as a **pure function**, deliberately: a mutant that
removes it must not be able to start a formal run from inside the test suite.

**Pre-existing failure, unrelated:** `tests/test_g6_forbidden_list.py::test_no_new_module_mentions_a_forbidden_term`
already fails on the untouched tree — it lists `cf_credit.py`, `cf_ratio.py`, `cf_sources.py`
(none of which I modified) because their docstrings cite the governing `multi-catfish-…` document
path. `cf_xep.py` joins that list for the same reason. Not introduced here, not fixed here.

## 7. The preflight I ran, and on which episode sets

Every command below. Python is the `.venv` with torch (`/home/u24/papers/mcrl-leo-handover/.venv`);
the dev worktree's own `.venv` has numpy but no torch. `PYTHONPATH=<tree>/scripts` and
`cf3_common` inserts `<tree>/src` first, so `mcrl` resolves to the dev tree (asserted by
`assert_environment`). TLE pinned to `427e6a91…38fe9` on every run.

```
# 1. record the reference (DEV-NULL 9_241_500 / 9_241_501), once
scripts/dev_e0_xep_reference.py
scripts/dev_e0_xep_reference.py --verify                       # MATCH, byte-reproducible

# 2. clean tests + all 11 mutants
pytest tests/test_s1_harness.py                                # 20 passed
pytest tests/test_cf_dev.py                                    # 22 passed
bash scripts/s1_mutants.sh                                     # clean GREEN, 11/11 RED

# 3. S1 construct-only: build, check seeds, train nothing, write nothing
scripts/run_s1.py --arm {1..6} --seed-index {0,1,2} --construct-only ...   # 18/18 OK

# 4. MODQN eq-(16) at an arbitrary budget, DEV seeds only
<scratchpad>/modqn_dev_smoke.py     # 2 episodes trained on 9_201_000/9_202_000/9_203_000,
                                    # then greedy rollout on 2 DEVVAL episodes

# 5. the D3-XEP training preflight, DEV depth, own result root
scripts/dev_e0_launch.py --root <scratchpad>/s1prep-devroot --init-manifest --dry-run \
    --episodes 20 --devval-episodes 24 8:0
scripts/run_dev_e0.py --arm 8 --seed-index 0 --root <scratchpad>/s1prep-devroot \
    --episodes 20 --devval-episodes 24                          # 20 episodes, 179 s, RSS 0.90 GB
```

Episode sets used: **DEV** `9_201_000 / 9_202_000 / 9_203_000` (training), **DEVVAL**
`9_211_000+i / 9_212_000+i` (evaluation), **DEV-NULL** `9_241_500 / 9_241_501` (the reference
episode). Nothing else. Result root is the session scratchpad, not `/home/sat/...runs-e1-*`, which
was never opened. No `sat` compute was used for training; `sat` was contacted read-only three times
(the calibration file — verified sha256 `59952214…` on both ends — the E1 manifest's calibration
path, and the frozen checkpoint's sha256).

### The 20-episode `D3-XEP` DEVVAL record — numbers, no conclusion

```
arm E0-8-D3-XEP-equal_share k0, config 736f35dfd789, DEVVAL 24 episodes, ep 20
ee                                     9.6337e7 bit/J
served                                 0.99633
beams                                  53.5625
t0_agreement (policy vs T0)            0.33675
t0_score_regret (policy)               1.1601
t0xep_agreement (null vs REAL T0)      0.19567
t0xep_score_regret                     1.7669
t0xep_random_legal_agreement_expected  0.03871
t0xep_decisions                        24000
xep_reference sha256                   9bb0c01e… (identical in all 20 episode logs)
```

**Twenty episodes is not evidence and I draw no conclusion from any of it.** The reading rule is
Amendment 12 §3 and it applies at S1 only. One thing is worth the controller's attention *as a
prospective note*, because it is structural rather than a training outcome: `t0xep_agreement`
(0.196) sits about **5×** the exact uniform-random-legal expectation (0.039) on the same rows. That
is the residual leakage Amendment 12 §2 anticipated — T0-XEP and T0 both prefer an already-lit slot
with a good nominal link, and that preference survives the change of episode. If the S1 reading
shows the same, `ρ_info` is a **lower bound** on T0's information share and §2's last paragraph
requires it to be reported as such. Whether the S1 figure resembles this one is unknown: this is a
20-episode, undertrained state distribution.

## 8. Things a future launcher must know

1. `dev_e0_common.MANIFEST_FILES` now includes `artifacts/dev-e0/t0-xep-reference.json`. The
   deployed tree must contain it or `code_manifest()` raises. It is committed.
2. Adding the `lane` and `xep_reference_*` fields to `DevSettings` changes **every** arm's
   configuration hash, including `D0`, `D3-T0` and `D3-null`. Existing E1 roots therefore cannot be
   resumed against this code — correct behaviour (this is a new code version), and no existing root
   was touched. Fresh roots only.
3. `s1_launch.py` verifies the sealed reference before it plans anything, and refuses a partial
   matrix. `run_s1.py --construct-only` is the way to re-check the harness without spending an
   episode.
4. The MODQN arm's epsilon schedule is compressed to match the CF arms (§3 finding 1). If the owner
   wants the frozen 2000-episode schedule instead, that is a manifest change and a new hash.
5. `S1_EVAL_AT = (1000,)` — one terminal read. Changing it re-opens the peeking question.
6. The `sat` venv's editable install points at a stale tree: any new script must
   `sys.path.insert(0, "<tree>/src")`. `cf3_common` already does; `s1_common` / `run_s1` import it
   first for exactly that reason.
