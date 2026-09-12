# LANE-M — the generic N-teacher set-valued MULTI-D3 and its matched null

Date: 2026-09-12. Worktree `/home/u24/papers/mcrl-leo-handover-cf2s-multi`, branch
`catfish2/multid3-20260912`, base **`27f69edf`** (deliberately not the dev tip
`a24b90b2`, whose new `DevSettings` fields would change every arm's config hash and
break the singleton bit-identity against the frozen E0/E1 lineage).

**Development lane. No learner arm was launched by this lane, and nothing here is
screening evidence.** Every seed constructed is DEV / DEVVAL / DEV-NULL; DEV k = 8
and k = 9 were not consumed (they appear only as *identity strings* in config-hash
assertions, never as a run).

---

## 1. What was built

`L_multi = max_{a legal} [ S(s,a) + m·1(a ∉ A_CF) ] − max_{a ∈ A_CF} S(s,a)`
with `A_CF(s) = unique({a_T0, a_Ti, …})` restricted to the **currently legal**
actions, the frozen `m = 0.15`, the unchanged `λ_E = 1.0` and the learner's existing
deployed score `S = Q̃_B − η̃ Q̃_E − λ Q̃_H`. **No teacher weights of any kind.**

### The one design decision everything else follows from

`A_CF` is carried as a **boolean membership mask over the 28 actions**, never as a
list of teacher actions. That makes three of the twelve required properties
*structural* rather than incidental:

| property | why it cannot be violated |
|---|---|
| deduplication | two teachers naming the same action set the same bit |
| order invariance | the mask does not record which slot set which bit |
| legality | a bit is only ever set for an action legal in that state |

The loss therefore cannot see how many teachers there were, in what order they ran,
or which of them proposed what — which is exactly the property "no teacher weights"
needs, and it is why the mechanism is agnostic to the sources.

### Files (worktree `…-cf2s-multi`)

- `src/mcrl/algorithms/cf_teacher.py`
  - `MULTI_MECHANISM_ID = "MULTI-D3-SETVALUED-v1"`, `MULTI_NULL_ID =
    "RANDOM-LEGAL-SET-NO-REPLACEMENT-v1"`, `MULTI_NULL_BERNOULLI_ID` (§5, not selected);
  - teacher-source registry — `register_teacher_source` / `unregister_teacher_source`
    / `teacher_source` / `registered_teachers` / `canonical_teacher_set` /
    `teacher_action_slots`. A source is just
    `(states, masks) -> (U,) int64 legal actions`. **Only `T0` ships registered**;
    Lane N (`T_NEXT`) and Lane Q (`T_TAIL`) register theirs;
  - `membership_from_slots` (the `A_CF` builder above), `random_legal_action_slots`
    (the matched null's draw), `set_cardinalities` / `cardinality_histogram` /
    `duplicate_slot_fraction` (Amendment 15 §7 report fields);
  - `d3_set_margin_loss` — the mechanism.
- `src/mcrl/algorithms/cf_dev.py` — `MultiD3Spec` (the hashed identity),
  `EXPECTED_TEACHER`, `NULL_BASE_FOR`, `D3_MECHANISMS`, `_null_generator`,
  mechanisms `D3-multi` / `D3-multi-null`, replay label format **v2** carrying
  `A_CF`, `teacher_labels_ext`, the multi branch of `_teacher_loss`, the §7
  diagnostics in the episode log, resume / checkpoint / policy-payload plumbing.
- `scripts/dev_e0_common.py` — arms **8** and **9**, `MULTI_ARMS`,
  `MATCHED_NULL_ARM`, `multi_spec`, `spec_key`, `arm_name(arm, teachers)`,
  `multi_spec` in the config payload.
- `scripts/run_dev_e0.py`, `scripts/dev_e0_launch.py` — `--teachers` /
  `--n-proposals` and the `ARM:K:T0+Ti` / `ARM:K:nN` spec grammar. **Not launched.**
- `tests/test_cf_multid3.py` — the twelve tests, the null evidence, the mutants.
- `tests/test_cf_dev.py` — two lines updated where the internal replay-label tuple
  arity leaked into an existing test; all 22 pre-existing tests stay green.

**Not touched:** `cf_ratio.py`, `modqn.py`, `cf_credit.py` — byte-identical to
`27f69edf` (asserted in test 11).

---

## 2. The twelve required tests

`pytest tests/test_cf_multid3.py` — **16 passed** (the twelve, plus the
no-weights test, the two null tests and the arm-registration test).

| # | requirement | test | result |
|---|---|---|---|
| 1 | singleton `{T0}` bit-identical to the current `D3-T0` | `test_01_singleton_multi_arm_is_bit_identical_to_the_frozen_d3_t0` | **PASS** |
| 2 | singleton generic path bit-identical to the single-teacher D3 | `test_02_singleton_generic_loss_is_bit_identical_loss_and_gradient` | **PASS** |
| 3 | teacher-order permutation invariance | `test_03_teacher_order_is_a_permutation_invariance` | PASS |
| 4 | duplicate teacher actions collapse | `test_04_duplicate_teacher_actions_collapse_to_one_action` | PASS |
| 5 | only currently legal teacher actions enter `A_CF` | `test_05_only_currently_legal_teacher_actions_enter_a_cf` | PASS |
| 6 | an illegal action can never become a target | `test_06_an_illegal_action_can_never_become_a_target` | PASS |
| 7 | deterministic first-index tie behaviour | `test_07_tie_behaviour_is_deterministic_first_index` | PASS |
| 8 | a disabled multi path reproduces the frozen control | `test_08_a_disabled_multi_path_reproduces_the_frozen_control` | PASS |
| 9 | config hash carries teacher / mechanism / null identity | `test_09_config_hash_covers_teacher_mechanism_and_null_identity` | PASS |
| 10 | resume / stop determinism | `test_10_resume_and_stop_are_deterministic` | PASS |
| 11 | the multi code changes no inference or deployment path | `test_11_the_multi_code_changes_no_inference_or_deployment_path` | PASS |
| 12 | no teacher is required at deployment | `test_12_no_teacher_is_required_at_deployment` | PASS |

### 2.1 Bit-identity receipts (the load-bearing pair)

**Test 2 — the loss function.** 60 cases (20 random 20-row batches × margins
`0.15`, `0.0`, `0.7`), `torch.equal` on the loss tensor **and** on the gradient
w.r.t. the score tensor, plus one sha256 over every loss byte and every gradient
byte produced by each implementation:

```
d3_margin_loss      (frozen, single-teacher)  loss+grad sha256 =
d3_set_margin_loss  (generic, |A_CF| = 1)     loss+grad sha256 =
  631b09919603553294ef39834015991d7e8a2e64a4bccd5e002656e793866b6c
```

Identical, not "close". The argument the code is written to keep:

* the margin tensor is the same `torch.full_like(scores, float(margin))`, with the
  zeros written by `masked_fill_(member, 0.0)` instead of `scatter_(1, a_col, 0.0)`
  — for one member these write the same float32 at the same position;
* the first term is the **same** `(scores + marg).masked_fill(~mask, MASK_FILL)
  .max(dim=1)`;
* the second term replaces `scores.gather(1, a_col)` with
  `scores.masked_fill(~member, MASK_FILL).max(dim=1)`. With one member the `max`
  returns that member's score exactly (everything else is exactly `-1e9`) and its
  backward routes the same unit gradient to the same index; `masked_fill`'s backward
  passes gradient through unmasked positions and zeros the rest, so the gradient into
  `scores` is `e_{a_T}` in both.

**Test 1 — the arm.** Two full training runs on the real pinned-TLE environment
(6 users, 2 episodes, same DEV triple `9_201_000 / 9_202_000 / 9_203_000`, frozen
`m = 0.15`, `λ_E = 1.0`): `D3-T0` versus `D3-multi` with `teachers = ("T0",)`.
sha256 over every learner parameter byte after training:

```
D3-T0     parameter sha256 = 8889f45e388403189a079a0e858cbcc57cabf1e52fe3da17207bb187341d300d
FULL{T0}  parameter sha256 = 8889f45e388403189a079a0e858cbcc57cabf1e52fe3da17207bb187341d300d
```

plus, element by element: every `torch.equal` on the parameters; the replay's stored
labels equal transition for transition (and the multi arm's `A_CF` is the one-hot of
the frozen arm's teacher action); and **every shared episode-log field equal**,
including `losses`, `teacher_loss`, `bits`, `joules`, `served`, `updates`. The only
fields that differ are `mechanism` / `teacher` — the arm's own label — and the
multi-only `A_CF` diagnostics, which no loss reads.

### 2.2 Notes on the other ten

* **7 (ties).** Both reductions are `torch.max(dim=1)`, whose CPU rule is the first
  maximal index — the same convention as `np.argmax` in the frozen T0 rule and in
  `masked_argmax_rows`. Verified on the outer max, on the max over `A_CF` (with two
  exactly tied members: the gradient lands on the lower index and is exactly zero on
  the other) and across repeated calls.
* **8 (disabled path).** `λ_E = 0` on both multi mechanisms reproduces `D0` bit for
  bit, and — the stronger half — arms 1–7 hash to **exactly** what the base commit's
  `dev_e0_common.py` produces: the test `git show 27f69edf:scripts/dev_e0_common.py`,
  execs it, and compares `config_hash` for arms 1–7 at k = 0 and k = 1. The multi
  identity block is added to the payload **only** for arms 8 and 9.
* **11 (inference).** `cf_ratio.py` / `modqn.py` / `cf_credit.py` sha256-equal to
  `27f69edf`; `CFDevTrainer.greedy_actions`, `select_actions`, `encode_at` and
  `save_policy` are the *same function objects* as `CFRatioTrainer`'s (never
  overridden); and a multi trainer and a `D3-T0` trainer holding the same weights
  choose the same greedy actions on the same observations.
* **12 (deployment).** A checkpoint saved from a two-teacher arm is loaded after the
  teacher registry has been emptied and `cft.t0_scores` replaced with a function that
  raises; `greedy_actions` and a two-episode `dev_rollout` both run. A teacher exists
  only inside the training loop; the checkpoint's `multi_spec` block is provenance
  that nothing in the inference path reads.

---

## 3. Mutants

`bash .scratch/catfish2-successor/run_mutants_lane_m.sh` — each mutant is applied
with `monkeypatch` (no source file is edited) and must turn the suite red on its own.

MUTANT_TABLE_PLACEHOLDER

One honest note on `A_CF` deduplication. With `A_CF` as a boolean mask, a
*non-deduplicated set* is **unrepresentable in the loss** — `max_{a∈A_CF} S` and
`1(a ∉ A_CF)` are both insensitive to multiplicity. So there is no loss-level
"not deduplicated" mutant to write; the two things that *can* go wrong are covered
instead: a loss that combines per-teacher terms (`teacher_weights_reintroduced`,
`acf_summed_over_members`) and a cardinality report that counts duplicates
(`acf_cardinality_counts_duplicates`), which is what the null-matching argument
rests on.

---

## 4. The matched set-valued null — and a defect the controller must rule on

### 4.1 What is implemented and registered

Arm 9, `D3-multi-null`, identity `RANDOM-LEGAL-SET-NO-REPLACEMENT-v1`: the **same**
set-valued margin loss, same `m`, same `λ_E`, same masks, same schedule, same
gradient path; `A_CF` is `n` **distinct** legal actions drawn **without replacement**
from the arm's own declared DEV-NULL stream `(9_241_000, k)`, cardinality one when
only one legal action exists. Exactly one generator call per row with a legal action.
No teacher quantity enters it: the stored score vector is zeros, and multiplying T0's
scores by −7 does not move a single draw (tested).

`MATCHED_NULL_ARM = {4: 7, 8: 9}` records the pairing in code: the set-valued FULL
arm's null is arm 9 and **never** arm 7.

### 4.2 The cardinality measurement, and the defect

Task: "test that the null's set-cardinality distribution matches the FULL arm's".
Measured on 400 synthetic states (every one with ≥ 2 legal actions), DEV-NULL key
`(9_241_000, 8)`:

```
declared 2-null            |A_CF| hist [card0, card1, card2] = [0,   0, 400]
FULL{T0, T_LASTLEGAL}                                        = [0,  49, 351]   collapse 0.1225
FULL{T0, T_MINLOAD}                                          = [0,  19, 381]   collapse 0.0475
FULL{T0, T_ECHO_T0}   (teachers always agree)                = [0, 400,   0]   collapse 1.0
```

**The declared two-proposal null is cardinality-matched only when the teachers never
agree.** Structurally, `|A_CF|(FULL) = 2 − 1(the teachers named the same action)`
while `|A_CF|(null) = min(2, n_legal)`. Amendment 15 §5 admits a candidate at
`disagreement ≥ 0.25`, i.e. **agreement up to 0.75**, so a FULL arm could be a
size-one set three-quarters of the time while its null is always size two — and a
size-two set is mechanically easier to satisfy, so the *null* would then be flattered
relative to FULL (the opposite direction from the one-action `D3-null` problem, but
the same failure of matching).

Amendment 15 §6 pre-authorises exactly this: the two-proposal semantics hold
"unless a test demonstrates an actual matching defect". The **mechanism** of the
defect is demonstrated above; its **magnitude** for the real candidate cannot be
known until `T_NEXT` or `T_TAIL` exists, because it is that candidate's agreement
rate with T0 on the frozen P0 collection.

### 4.3 What a launcher must do, and the remedy that is implemented but NOT selected

1. Before k = 8, on the frozen P0 collection, compute the FULL arm's `|A_CF|`
   histogram and compare it with the declared null's using
   `tests/test_cf_multid3.py::cardinality_mismatch`. It returns the cardinalities
   whose share differs by more than 2 pp.
2. A non-empty result goes **to the controller**, before any learner arm starts —
   never after.

`MULTI_NULL_BERNOULLI_ID = "RANDOM-LEGAL-SET-BERNOULLI-MATCHED-v1"` is implemented
and tested as the remedy: a row with ≥ 2 legal actions collapses to cardinality one
with a **declared marginal** `p_singleton`, measured on the frozen P0 collection
before any training and carried in the configuration hash. It leaks only that one
pre-declared marginal — never per-state teacher information, which would put teacher
content back into the null. Demonstrated: with `p_singleton = 0.1225` against
`FULL{T0, T_LASTLEGAL}` the histograms line up (`[0, 48, 352]` vs `[0, 49, 351]`,
mismatch empty).

**It is not registered as an arm and I have not selected it.** Registering it would
be one line (`10: ("D3-multi-null", "equal_share")` plus a `MULTI_ARMS` entry). The
choice belongs to the controller and must be made before any k = 8 learner result
exists.

---

## 5. Arm indices claimed

| arm | identity | parameterised over | run directory |
|---|---|---|---|
| **8** | `D3-multi` — FULL set-valued MULTI-D3 | the **teacher set** (canonical, sorted, duplicate-free) | `E0-8-D3-multi-T0+T_NEXT-equal_share-k8` |
| **9** | `D3-multi-null` — matched set-valued null | the **cardinality only** | `E0-9-D3-multi-null-n2-equal_share-k8` |

Arm 9 names no teacher on purpose: it is matched to a cardinality, so **one physical
`n = 2` null run is shared by every two-teacher candidate**, which is what
Amendment 15 §7 means by "shared arms are physically run once at the same exact
identity".

RUN-MANIFEST keys: `spec_key` is unchanged `"4:8"` for arms 1–7, and
`"8:8:T0+T_NEXT"` / `"9:8:n2"` for the multi arms. Launcher grammar:
`ARM:K:T0+Ti` (FULL) and `ARM:K:nN` (null); the driver takes `--teachers` /
`--n-proposals`.

**Collision to resolve at merge.** The now-closed `TDELTA-CANARY-PREP` lane
(`catfish2/tdelta-canary-prep-20260912`, `ef8c866f`) also registered an arm 8, as
`D3-T_DELTA`, and mapped it to arm 7 as its matched null. `T_DELTA` is closed
(adjudication `f747de86`) and that lane's own comment says a successor "should
REPLACE this entry, not extend past it". This branch does exactly that: arm 8 is
`D3-multi` and `D3-T_DELTA` is not carried over. If both branches are merged, arm 8
must resolve to `D3-multi`.

---

## 6. What a launcher must know

1. **Register the teacher source first.** `cft.register_teacher_source("T_NEXT", fn)`
   before building the config. The identity string is what goes in the hash;
   `canonical_teacher_set` sorts and rejects duplicates, so `{T0,Ti}` and `{Ti,T0}`
   are the same run.
2. **Arms 1–7 are untouched.** Their config hashes are proven byte-identical to
   `27f69edf` (test 8). The multi identity block appears only for arms 8/9.
3. **`FULL{T0}` is arm 4.** The singleton is bit-identical to `D3-T0`, so the k = 8
   matrix's `T0-only` cell may be run as arm 4 — cheaper and already validated — and
   arm 8 with `teachers=("T0",)` is available as the equivalence check.
4. **`Ti-only`** is not a MULTI-D3 arm: it is the single-teacher `D3-Ti`, which needs
   one line in `D3_MECHANISMS` + `EXPECTED_TEACHER` (the pattern the closed prep lane
   used for `D3-T_DELTA`). LANE-M did not add it, because the candidate's identity is
   not mine to declare.
5. **Replay format v2.** `TeacherReplayBuffer` labels are now 4-tuples; a `resume.pt`
   written by pre-v2 code is refused. This is moot in practice because any edit to
   `cf_dev.py` already changes `code_manifest()` and the driver refuses to resume
   across a code change.
6. **Report fields** required by Amendment 15 §7 are emitted per episode for multi
   arms: `multi_set_cardinality_hist`, `multi_set_cardinality_mean`,
   `multi_duplicate_fraction`, `multi_set_rows`, plus the mechanism / teacher / null
   identities. They are diagnostics; no loss, gradient or target reads any of them.
7. **Cost.** LANE-M adds one membership build per step (28-wide boolean, `O(U·n)`)
   and one extra `max` in the loss. It is negligible; the arm's cost is whatever the
   candidate teacher's own evaluation costs. The `T_DELTA` figures from the closed
   prep lane (2,901 evals/step, ~8 h per arm) are **historical and must not be quoted
   for `T_NEXT` or `T_TAIL`**.
8. **`series_memo()`** from the prep lane (`ef8c866f`, docstring corrected in
   `372214df`) is **not used by this lane** and is not enabled anywhere here. It has
   no parity receipt; it must not be enabled for any counted use until
   `cf2s_prep_cost.py --mode parity` returns 100 % action identity on a sealed sample.

---

## 7. Reproduction

```bash
cd /home/u24/papers/mcrl-leo-handover-cf2s-multi
export MCRL_TLE_ROOT=/home/u24/mcrl-runtime/tle-pinned-427e6a91
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
/home/u24/papers/mcrl-leo-handover/.venv/bin/python -m pytest \
    tests/test_cf_multid3.py tests/test_cf_dev.py -q -p no:randomly
bash .scratch/catfish2-successor/run_mutants_lane_m.sh
```

Pinned TLE file set `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`.
All work local; `sat` was not used and Phase B0's four J shards were not disturbed.
