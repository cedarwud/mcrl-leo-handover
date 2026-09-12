# LANE-A — the MC2 training-only judge, `MC2-JGO-v1`, `MC2-ARB-v2`, and the ep-100 launch

Date: 2026-09-12. Worktree `/home/u24/papers/mcrl-leo-handover-mc2`, branch
`mc2/judge-override-20260912`, base `6136c514` (Lane M k = 8 code `f129e340` + results).
Commit **`11466998843d94424298d3a6dac0cb3eb5d38279`** (read back from git).

**Development lane.** Nothing here is Amendment 4 screening evidence, nothing supports a
statistical claim, and no formal / calibration / CONFIRM / S1 seed is constructed. A judge
win is **not** an EE improvement: `B − η₀E` is a fixed-price surrogate used only as a gate.

---

## 1. What was built

### 1.1 The judge (contract §2) — `src/mcrl/algorithms/cf_judge.py`

```
ev(a)    = StepEnvironment.evaluate_actions((a, x_-u), deepcopy(env_rng))   # pre-step
κ_u(a)   = ( n_served(ev(a)) , B(ev(a)) − η₀·E(ev(a)) )                     # lexicographic
η₀       = 110_507_234.83444457     ≻ = STRICT, ties → incumbent
```

`B, E = cf_credit.evaluation_bits_joules`; `n_served` = served users of the step. All of one
step's evaluations run inside `cf_credit.frozen_driver_positions` (the B1 / T_DELTA path) and
each deep-copies the environment generator inside `evaluate_actions`.

Two properties are load-bearing and both are tested on the real 100-user environment:

* **exactly one reuse**: `κ_u(x_u)` IS the evaluation of the joint vector `x`, computed once
  per step and served for every such query (`evaluate_actions` is a pure function of the
  action vector and a deep copy of `rng`);
* **parity, asserted every step**: after `env.step`, the base evaluation's bits, joules and
  served flags must equal the committed step's, or the run fails loudly (the ruling-2 parity
  guard of the difference credit). A judge that advanced a generator cannot survive it.

Proposals are restricted to `{x_u, a^A, a^B}` — no all-action and no joint-action search.

### 1.2 Arm 10 = `("MC2", equal_share)`, parameterised over (rule, source set)

| cell | rule id | sources | rule |
|---|---|---|---|
| `v1-A+B` | `MC2-JGO-v1` | A+B | incumbent = target = `a^A`; `c` overrides only if `κ(c) ≻ κ(a^A)` |
| `v1-A+R` | `MC2-JGO-v1` | A+R | same, `a^R` replaces `a^B` |
| `v2-A` | `MC2-ARB-v2` | A | candidates `{x_u, a^A}` |
| `v2-A+B` | `MC2-ARB-v2` | A+B | candidates `{x_u, a^A, a^B}`, ties `x_u` → A → B |
| `v2-A+R` | `MC2-ARB-v2` | A+R | candidates `{x_u, a^A, a^R}` |
| `B` | `MC2-B-ONLY-SHARED-v1` | B | **rule-independent**: target `a^B` iff `κ(a^B) ≻ κ(x_u)` |

`A-only-v1` is arm 4 (`D3-T0`) itself and is refused as an arm-10 cell, so no second A-only-v1
identity can exist. `A` = T0 via `cf_teacher.t0_scores`; `B` = T_NEXT through the existing
`TeacherContext` seam and `cf_multi_sources` (**`cf_tnext.py` untouched**, sha256
`86f0d6ee…`); `R` = one uniform legal action per user with a legal action at `t < T−1` from a
fresh generator at the new declared DEV-NULL key `(9_243_000, k)`. **B and R are absent at
`t = T−1`**; under v2 the anchor still competes there.

### 1.3 The loss (contract §3)

`L = Σ_heads TD_k + λ_E·(1/|batch|) Σ_rows w_row·[max_{a legal}(S + m·1(a≠target)) − S(target)]`,
`w_row = 1[target exists]`, `m = 0.15`, `λ_E = 1.0`, batch 128 — the frozen single-target D3
margin, statement for statement, times `w`. A row without a target contributes **exactly 0**
and the vacated dose is **not refilled** (its `a_target` is only a legal placeholder under
weight 0). With every `w = 1` the value and the gradient are `d3_margin_loss`'s bit for bit.

### 1.4 Identity, seeds, diagnostics

`JudgeSpec` (versioned rule id, canonical source set, source identities incl. the pinned
`cf_tnext.py` sha256, judge id + frozen η₀, null id + composite key) and the rule definition
text are in the configuration hash. `MAX_DEV_SEED_INDEX` 9 → 19; DEV-NULL base `9_243_000`
declared; the S1 namespaces (`9_251_000–9_253_999`, `9_261_000–9_261_999`) are now refused **by
name**; the launcher refuses `k = 9`. Per-episode diagnostics (no loss, gradient or target
reads any of them): `decision_rows_all_t` (the denominator, all `t` including `T−1`),
challenger rows, disagreements vs `a^A`, comparisons, overrides and **winner counts per tag per
step**, `judge_challenger_wins_c_ne_a` (lane B R1-3), served-decisive overrides and judge leads
**split by tag**, judge evaluations and wall, per-update sampled rows and margin-loss sum per
tag, and the margin dose.

`judge_override_rate` is kept but is **not comparable across rules** (under v2 it counts A
wins); the contract's clause (vi) quantity is `judge_challenger_wins_c_ne_a /
decision_rows_all_t`.

---

## 2. Tests — 87 green, 6 mutants red

`pytest tests/test_mc2_judge.py tests/test_cf_dev.py tests/test_cf_multid3.py
tests/test_cf_tnext.py -q -p no:randomly` → **87 passed**, WALL 326.5 s, rc = 0
(`.scratch/mc2/logs/clean-suite-r1.log`). 20 of them are new; the 67 pre-existing tests are
untouched apart from one pinned `MAX_DEV_SEED_INDEX` expectation in `test_cf_dev.py`
(`(9_231_000, 10)` → `(9_231_000, 20)`, stated because the bound moved 9 → 19).

| contract §5 | test | receipt |
|---|---|---|
| 1 arms 1–9 hashes | `test_01` | equal to the base commit's harness for arms 1–7 × k ∈ {0,1,8,10,11} and arms 8/9 with their specs; **and** equal to the five config hashes actually launched at k = 8 (`ed4e507e…`, `0cf6f6a1…`, `c4654661…`, `1737d123…`, `17b048b2…`) |
| 2 gate shut ≡ `D3-T0` | `test_02` | parameter sha256 equal, every shared log field equal, judge ran (`compared > 0`) and overrode nothing |
| 2 (v2) | `test_02b` | v2 with the gate shut keeps `x_u` everywhere → zero dose → **bit-identical to `D0`** |
| 3 base = committed step | `test_03` | bits, joules, served count equal; reuse is the same object; frozen-position evaluation equals the plain evaluator; env_rng, mobility rng and an environment fingerprint (driver, users, segments, ledgers, previous association / power) unchanged |
| 4 gate semantics | `test_04` | served-first, tie → incumbent, no call when `c = inc`, B abstains at `T−1` (table + real B-only run: `compared_per_step[-1] = 0`, T_NEXT never asked at `T−1`) |
| 4 (v2) | `test_04b` | winner = max κ with ties `x_u` → A → B; `a^A = a^B` is an A win; margin only if winner ≠ `x_u`; leads split by tag |
| shared cell | `test_04c` | v1 and v2 labellers give identical labels on `{B}`, identical replay rows and **identical parameter sha256** after 3 episodes; the payload carries no `JGO`/`ARB` string; `v1-B`, `v2-B`, `B` hash identically |
| 5 the null | `test_05` (both B-null cells) | reads no T_NEXT (a raising stub is registered), exactly one draw call per step at `t < T−1` and none at `T−1`, every draw legal, replay from a fresh `(9_243_000,3)` reproduces every draw and the stream's end state, and `(9_243_000,3)` is the **only** composite generator built |
| 6 seeds | `test_06` | k = 10…17 train/env/mobility/+70_001/+90_211 all inside declared DEV ranges, disjoint from P0 (`9_202_500+i`, `9_203_500+i`), the T0-XEP reference (`9_241_500/1`), formal, calibration, CONFIRM and S1; no collision between constructed streams |
| 7 hash coverage | `test_07` | rule id, source set, judge id, η₀, null id and null key each move the hash; the six cells are six hashes; undeclared cells refused |
| 8 deployment | `test_08` | a FULL checkpoint runs `greedy_actions` and a 2-episode `dev_rollout` with every source unregistered, `t0_scores` raising, `StepJudge.__init__` raising and `evaluate_actions` raising; `cf_ratio.py`, `modqn.py`, `cf_credit.py`, `cf_tnext.py`, `cf_teacher.py`, `cf_multi_sources.py`, `trainer_env.py`, `env/step.py` byte-identical to `6136c514` |
| 9 resume | `test_09` × 6 cells | weights, losses, judge labels and the B-null's own stream bit-identical across a stop/resume; a different cell's state is refused |
| 10 zero-margin rows | `test_10` | `w = 0` rows give exactly 0 loss and 0 gradient; `w ≡ 1` is `d3_margin_loss` bit for bit; the mixed case is strictly below the refilled value; a real B-only run's target-less rows carry zero margin and the per-tag loss shares sum to the teacher loss |

Mutants (`MC2_MUTANT=<name>`, monkeypatch only, `.scratch/mc2/logs/mutants-lane-a.log`):

| mutant | red at |
|---|---|
| `gate_ge` (ties admitted) | `test_04` |
| `judge_advances_rng` | `test_02` (parameter sha differs / parity raises) |
| `b_no_abstain_final` | `test_04` |
| `null_reads_tnext` | `test_05[v1-A+R]` |
| `margin_refilled` | `test_02b` |
| `arb_ties_to_a` (v2 tie order) | `test_02b` |

---

## 3. Smoke on the real 100-user environment (local, 3 episodes, sequential)

`.scratch/mc2/logs/smoke-lane-a.log`. ε = 1.0 at episode 0, then 0.01 (smoke budget), so the
two ends bracket the cost range of a real run.

| cell | training wall (3 ep) | judge evals / ep | judge wall / ep | dose | challenger wins / 1000 rows |
|---|---:|---:|---:|---:|---:|
| `v1-A+B` | 84.4 s | 1288 → 902 | 26.4 → 15.4 s | 1.000 | 366 → 330 |
| `v1-A+R` | 104.2 s | 1675 → 1401 | 34.0 → 24.6 s | 1.000 | 249 → 176 |
| `v2-A+B` | 99.5 s | 1605 → 1176 | 34.0 → 19.9 s | 0.79 → 0.67 | 292 → 225 (B wins) |
| `v2-A+R` | 112.8 s | 1806 → 1579 | 36.2 → 27.7 s | 0.79 → 0.61 | 182 → 113 (R wins) |
| `v2-A` | 62.0 s | 969 → 672 | 19.4 → 12.0 s | 0.68 → 0.53 | — (A wins 695 → 388) |
| `B` (shared) | 60.4 s | 867 → 670 | 17.7 → 11.0 s | 0.69 → 0.54 | 471 → 341 |
| `D3-T0` (arm 4) | 18.9 s | — | — | 1.000 | — |

Every run held ≈ 1.9 GB RSS locally and ≈ 1.0 GB on sat. The v1 cells' dose is exactly 1.000
(the anchor is unconditional); every v2 cell and the shared cell sit below 1 and the vacated
dose is not refilled. B's realised win rate (29.2 % of decision rows in `v2-A+B`, 36.6 %
overrides in `v1-A+B`) is far above the contract's 1 % inertness floor and is consistent with
the controller probe's 30.8 % approval of `a^B` at a trained `D3-T0` background.

---

## 4. The ep-100 selection matrix as launched

Root `/home/sat/mcrl-v025-mc2-ws/runs-ep100`, one `RUN-MANIFEST.json` with **all 16 specs**
(code digest `ede2c580aaa9`, commit `11466998…`, calibration `59952214…`, pinned TLE
`427e6a91…`), **`--episodes 300 --stop-after 100`** in every run (never `--episodes 100`:
`epsilon_decay_episodes(300) = 67` vs `(100) = 22`).

| cell | k = 10 | k = 11 |
|---|---|---|
| `1` (`D0`) | `6af44774fd3a` | `84b6fbbb701a` |
| `4` (`D3-T0`) | `37c20ed54cdb` | `e36d33607755` |
| `10:B` | `312332b3ca1e` | `1177c18d954f` |
| `10:v1-A+B` | `a201a9e44cb4` | `169f13453e4f` |
| `10:v1-A+R` | `1ba3f9020ddc` | `b9d8aadd4408` |
| `10:v2-A` | `393d21220ebd` | `c9193432fdaa` |
| `10:v2-A+B` | `5d685d6336b2` | `24accd3dc029` |
| `10:v2-A+R` | `7f0401b7ed8d` | `4f7db0743fb4` |

16 distinct configuration hashes. Wave 1 (the judge-heavy cells) started
2026-09-12T05:59:03Z as PIDs 3777064–3777071, each verified from `/proc/<pid>/exe`, `cwd`
(`…/tree`) and the full `cmdline`, and each fingerprint checked against the manifest (config
hash, code digest, commit, calibration, TLE). The remaining 8 are filled into free slots by
`.scratch/mc2/fill_waves.sh` (local wait loop, short ssh calls only), never exceeding **8**
scientific workers, which the launcher re-counts itself from an anchored `/proc` scan.

`ep300.sh` is prepared and validated for both primary options (33 specs each: the primary
version's cells at k = 12, 13, 14 and the fixed-order fallback at k = 15, 16, 17) and **is not
launched**.

---

## 5. Deviations and things a reader must not over-read

1. **One commit for both rules.** r1 made v2 concurrent with v1; the 16-spec manifest needs
   every hash from one code identity, so `MC2-ARB-v2` is in the same commit as v1. The
   ordering rule (v2 committed before any selection cell's ep-100 DEVVAL) therefore holds by
   construction.
2. **`test_cf_dev.py` pinned expectation moved** — the only edit to a pre-existing test, and
   only because `MAX_DEV_SEED_INDEX` moved 9 → 19.
3. **The `+80_000+j` NULL-source seed ladders overlap between adjacent k** upstream in
   `cf_ratio.py`. No E0 / MC2 arm can construct them (`source_kind = "none"`, and
   `CFDevTrainer` refuses source pools outright), which `test_06` asserts; the collision check
   is therefore applied to the streams a run actually builds.
4. **`judge_override_rate` is rule-dependent** (see §1.4). Use
   `judge_challenger_wins_c_ne_a / decision_rows_all_t`.
5. **The judge is privileged training compute.** Evaluations and wall are counted per episode
   and reported; matched in kind between FULL and its B-null; **no sample-efficiency claim.**
6. **No gate was evaluated by this lane.** `MC2-EP100-RESULT.json` carries raw per-cell
   numbers and pairwise relative pooled EE with paired per-episode counts, and no verdict
   wording.
