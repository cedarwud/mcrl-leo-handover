# S1-MC2-PORT — what was ported, the unavoidable shared-file hunks, tests, preflight

Lane E, 2026-09-12. Worktree `/home/u24/papers/mcrl-leo-handover-mc2-s1`, branch
`mc2/s1-port-20260912`, base `67e175bd` (MC2 contract r0) → merged with lane A's mechanism commit
`11466998`.

**Nothing here is evidence and nothing was launched.** No formal evaluation, calibration, CONFIRM
or S1-TRAIN episode was stepped. All training in this document is 14 DEVELOPMENT episodes in a
session scratchpad, and every run's RNG constructions were audited independently of the harness's
own guards (§5).

---

## 1. What was ported, and the one structural change

Source: the accepted single-T0 S1 harness, `/home/u24/papers/mcrl-leo-handover-dev`, branch
`dev/e0-harness-20260912`, commits `500f824f` (harness) + `a24b90b2` (frozen manifest), on base
`27f69edf`. Acceptance record: `.scratch/dev-training/CONTROLLER-S1-PREP-ACCEPTANCE-2026-09-12.md`.

| accepted file | here | change |
|---|---|---|
| `scripts/s1_common.py` | same | rewritten for the MC2 cell table (parameterised by the frozen mechanism id); the `T0-XEP` constants moved in from `dev_e0_common` |
| `scripts/run_s1.py` | same | `--cell` instead of `--arm`; `--mechanism-id`; `--optional`; a DEV-lane `--preflight-dev` mode; the evaluation read wrapped in the deployment-purity guards |
| `scripts/s1_launch.py` | same | wave scheduling (`--max-live-workers 8`, `--launch-limit`, `--keep-filled`) with an anchored `/proc` worker count; the complete-matrix rule kept for the formal lane only |
| `scripts/s1_manifest.py` | same | `--mechanism-id`, `--optional`, and a **required** `--reading-rules` digest for a formal manifest |
| `scripts/s1_reference.py` | same | the rolled 9000-episode reference, now also under the purity guards |
| `scripts/dev_e0_xep_reference.py` | `scripts/s1_xep_reference.py` | constants from `s1_common`; otherwise the accepted file |
| `src/mcrl/algorithms/cf_xep.py` | same | byte-identical except four docstring cross-references |
| `artifacts/dev-e0/t0-xep-reference.json` (+ provenance) | same | **byte-identical**, sha256 `9bb0c01efdd403fb0e765bd133d718f7b07273a188c9f173b39fbb112ae1900c` (re-verified after copying) |
| Amendments 12 and 13 | `docs/dev-e0/…` | carried over unchanged |
| `tests/test_s1_harness.py` | same | rewritten for the new structure; 23 tests, 17 named mutants |

**The structural change.** In the accepted harness the S1 lane and `T0-XEP` were new *fields* on
`cf_dev.DevSettings` (`lane`, `xep_reference_*`) and new *branches* in `CFDevTrainer`. The
acceptance record notes the consequence: "the new `DevSettings` fields change **every** arm's
configuration hash". That was acceptable when the development screen was finished. **It is not
acceptable now**: the MC2 development screen is being launched from this same lineage, so S1 may
not move a single development configuration hash.

So the port puts the S1 lane in new modules and makes it a **subclass**:

- `src/mcrl/algorithms/cf_s1_lane.py` — a LEAF module (imports only `errors`): the S1 namespaces,
  `S1_ALLOWED/FORBIDDEN_SEED_RANGES`, `assert_s1_seed`, `assert_s1_null_key`, `s1_triple`,
  `s1_null_key`. `cf_dev` can import it at module scope, so the development kernel gains one
  dependency instead of a second copy of the seed contract.
- `src/mcrl/algorithms/cf_s1.py` — `S1DevSettings(DevSettings)` (adds `lane` + the three
  `xep_reference_*` fields), `S1Trainer(CFDevTrainer)` (binds the sealed reference, the `D3-XEP`
  labels and loss, the Amendment 12 diagnostics, the lane-aware evaluation read), the `T0-XEP`
  teacher, the leakage probe, and the deployment-purity context managers.

`DevSettings` therefore gains **no field**, and `D3-XEP` is not in `cf_teacher.MECHANISMS` — a plain
development configuration cannot even name it, and a plain `CFDevTrainer` handed an `S1DevSettings`
fails closed at its first teacher loss instead of silently training `D3-T0`.

Two consequences worth stating, because they are the cost of this choice:

1. `S1DevSettings.__post_init__` validates the generic part of the configuration by constructing a
   **development-lane shadow** of itself and letting `DevSettings.__post_init__` run on that. So
   every rule the development kernel has — including rules added to it later — applies to the S1
   lane automatically, rather than being copied and drifting. The lane-specific parts (formal
   evaluation bases, S1 null keys, the reference identity) are validated by the subclass.
2. `S1Trainer` reads the `D3-XEP` step index from the **training-only `TeacherContext` seam** the
   frozen loop already maintains (`step_index` is one of its declared fields), instead of a new
   `step=` keyword threaded through `train_cf`. That removed two hunks from files lane A is editing
   (`cf_dev.train_cf` and `tests/test_cf_dev.py`'s mutant wrappers). If the seam is ever not built,
   the `D3-XEP` labels raise instead of scoring the wrong reference step (tested).

---

## 2. The shared-file hunks — all of them, and why each is unavoidable

**Only `src/mcrl/algorithms/cf_dev.py` is touched.** `cf_teacher.py`, `dev_e0_common.py`,
`dev_e0_launch.py`, `run_dev_e0.py` and `tests/test_cf_dev.py` are **not** modified by this lane at
all — which is why the merge with lane A's mechanism commit had exactly one trivial conflict.

### Phase 1 (six hunks, lane plumbing only)

| # | location | hunk | why it cannot live in an S1 file |
|---|---|---|---|
| 1 | imports | `from . import cf_s1_lane as s1l` | the dispatcher below needs the S1 guard |
| 2 | after `assert_dev_seed_pairs` | `DEV_LANE`, `lane_of(dev)`, `assert_lane_seed`, `assert_lane_seed_pairs` (~25 lines) | the trainer and `dev_rollout` are in this file; `assert_dev_seed` stays the development entry point, so a mutant that neutralises it still neutralises the development path |
| 3 | `dev_rollout` signature | `lane: str = DEV_LANE` | the rollout IS the estimand; giving S1 its own copy would let the two drift, and a drifted estimand is exactly the kind of "not like-for-like" a reviewer must be able to rule out |
| 4 | `dev_rollout` body | `assert_dev_seed_pairs(...)` → `assert_lane_seed_pairs(..., lane=lane)` | same |
| 5 | `CFDevTrainer.__init__` | the three `assert_dev_seed(...)` calls → `assert_lane_seed(..., lane=lane_of(dev))` | the base `__init__` runs before any subclass code, so an S1 trainer cannot get past them otherwise |
| 6 | `devval_seeds` / `devval` | lane-aware guard; pass `lane=` to `dev_rollout` | the S1 read is the inherited read with the lane's episodes |

### Phase 2 (three hunks, after merging `11466998`)

| # | location | hunk | why |
|---|---|---|---|
| 7 | `FORBIDDEN_SEED_RANGES` | `+ (9_263_000, 9_263_999, "S1-NULL-MC2 (the formal B-null stream)")` | so a development path that built the formal B-null stream is told *which* namespace it hit, not merely "undeclared" — the same courtesy lane A gave S1-TRAIN and S1-NULL |
| 8 | `JudgeSpec.__post_init__` | the B-null key is validated by **its base's own lane guard**: `(9_263_000, k)` → `cf_s1_lane.assert_s1_null_key`, otherwise the development check unchanged | the B-null's stream is a lane fact, and `judge_spec_from_payload` must be able to rebuild an S1 spec on resume |
| 9 | `CFDevTrainer.__init__` | `assert_lane_seed(judge.null_key, …, lane=lane)` before the judge null generator is built | JudgeSpec now accepts either lane's base, so the **run** must refuse the other lane's: a development run can never draw the formal null and an S1 run can never reuse the development one |

### Merge conflicts resolved

One: both lanes added an import on the same line of `cf_dev.py` (`from . import cf_judge as cfj` vs
`from . import cf_s1_lane as s1l`). Resolved by keeping both, alphabetically. Lane A's semantics are
untouched; all six Phase-1 hunks survived the merge verbatim (verified by grep after merging).

### Lane A API facts the port had to follow (and did not assume)

- Every judge cell's `DevSettings.mechanism` is the single name **`MC2`**; the rule lives in
  `JudgeSpec.mechanism_id`. (My Phase-1 draft assumed `MC2-JGO` / `MC2-ARB`; corrected.)
- There are **three** rule ids: `MC2-JGO-v1`, `MC2-ARB-v2`, and **`MC2-B-ONLY-SHARED-v1`** — the
  rule-independent shared identity of `B-only`. The S1 table uses the shared id for `B-only`, so
  that cell's configuration hash does not depend on which version is frozen (the method owner's
  co-sign requires exactly that).
- `dev_e0_common.judge_cell(label)` is the authority for what a cell label means, and
  `cf_judge.DECLARED_CELLS` for which (rule, source set) pairs exist. `s1_common.judge_spec` calls
  both and refuses any cell the development screen would not accept.

---

## 3. The new formal namespace

`S1-NULL-MC2 = default_rng((9_263_000, k))`, k = 0, 1, 2 — the MC2 `B-null`'s proposal-replacement
stream in the formal lane. Declared in `cf_s1_lane.py` **before any S1 run**.

Why this value: the development B-null draws from `(9_243_000, k)` (contract §6) and Amendment 13 §5
forbids reusing a development stream at S1, so the formal base is the same +20 000 image that takes
the development `D3-null` key `9_241_000` to its formal `9_261_000`. `9_263_000` occurs nowhere else
in the project (grepped across every worktree in both the `9_263_000` and `9263000` spellings).

**A silent numpy hazard, recorded because it nearly bites here.** `default_rng((B, 0))` is the SAME
stream as `default_rng(B)`: `SeedSequence` pads entropy with zeros, so `[B]` and `[B, 0]` mix
identically (verified on numpy 2.5.2 for all four null bases). Every composite key's `k = 0` member
therefore aliases the integer seed `B`. In the S1 lane this is structurally harmless because
`9_261_000` and `9_263_000` are **not legal S1 integer seeds** — `assert_s1_seed` refuses both. In
the **development** lane the DEV-NULL bases *are* legal integer seeds (they sit inside the declared
DEV-NULL ranges), so there the aliasing is harmless only because no declared development
construction produces one; the test asserts that rather than assuming it. Worth a NOTE to the
development lane, not a change: nothing today constructs them.

The non-collision test is at **stream level**, not argument level: it builds every stream either
lane can construct (S1-TRAIN × 3, derived substreams, both S1 null keys, DEV triples k = 0…19
except 9, all three DEV-NULL bases × k, DEVVAL and the formal evaluation episodes), draws 8 values
from each and asserts all are pairwise distinct.

---

## 4. Tests

| suite | result |
|---|---|
| `tests/test_s1_harness.py` | **23 passed** (clean GREEN), on the merged tree with real judge cells |
| `scripts/s1_mutants.sh` | **17 named mutants, all individually RED** (see the table below) |
| `tests/test_mc2_judge.py` (lane A) | **passed** on the merged tree |
| `tests/test_cf_dev.py`, `test_cf_multid3.py`, `test_cf_tnext.py` | **passed** (67 tests) — the development lane behaves exactly as before |

Mutants, and what each would break if it survived:

| mutant | defect it models |
|---|---|
| `xep_reference_state_not_substituted` | scores the CURRENT state instead of the reference's (the null becomes the teacher) |
| `xep_current_mask_not_applied` | argmax over all 28 instead of the learner's legal set |
| `xep_reference_regenerated_per_episode` | re-records the sealed reference inside the run |
| `xep_agreement_against_itself` | scores `T0-XEP` against `T0-XEP` instead of the real T0 |
| `xep_reference_missing_from_config_hash` | the reference identity drops out of the hash |
| `s1_null_uses_dev_stream` | `D3-null` at S1 draws from `(9_241_000, k)` |
| `s1_bnull_uses_dev_stream` | the MC2 `B-null` at S1 draws from `(9_243_000, k)` |
| `s1_reuses_dev_training_triple` | S1 trains on the DEV triple |
| `s1_evaluates_on_calibration` | S1 reads the calibration episodes |
| `s1_preflight_runs_the_formal_lane` | the DEV preflight quietly constructs formal seeds |
| `s1_modqn_uses_shared_bootstrap` | the win-gate arm silently stops being eq-(16) |
| `s1_manifest_drops_arm_configs` | the declaration loses its per-run hashes |
| `s1_partial_matrix_allowed` | a subset can open the formal set |
| `s1_v1_duplicates_a_only` | v1 grows a second A-only cell (two names, one configuration) |
| `s1_v2_drop_one_is_d3t0` | under v2 "FULL vs A-only" silently means "FULL vs D3-T0" |
| `s1_eval_read_keeps_the_sources` | a specialist could be consulted on the published read |
| `s1_eval_at_adds_an_intermediate_read` | the formal set is read more than once |

The load-bearing test of the whole port is `test_the_s1_port_changed_no_development_identity`: the
`DevSettings` field tuple is asserted literally, and arms 1–9 of the development lane are hashed and
compared against **goldens recomputed from the untouched base tree** at `6136c514`
(`/home/u24/papers/mcrl-leo-handover-cf2s-multi`), so a field or payload change anywhere in the port
fails here rather than at the next development resume.

---

## 5. The preflight — 14 DEVELOPMENT episodes, and what each one proves

Python: `/home/u24/papers/mcrl-leo-handover/.venv/bin/python`. `MCRL_TLE_ROOT` pinned to
`/home/u24/mcrl-runtime/tle-pinned-427e6a91` (TLE file set `427e6a91…38fe9` asserted per run).
Calibration `.scratch/catfish2-successor/premeasure/calibration.json`, sha256 `59952214…4562d`.
Result roots in the session scratchpad; **no sat compute, no `runs-s1-*` root opened**.

| run | cells | episodes | wall (local WSL) | what it proves |
|---|---|---|---|---|
| `--preflight-dev` | `D3-XEP` k0 | 2 | 16 s | the ported second null trains, logs the sealed sha and Amendment 12's collection-time leakage counters, and reads once at the end |
| `--preflight-dev` | `D3-T0` k0, `--stop-after 1` then resumed | 1 + 1 | 12 s | the resume path: fingerprint match, contiguous logs, the single read happens at ep 2 only |
| `--preflight-dev` | `MODQN-eq16` k0 | 2 | 18 s | the eq-(16) path end to end; **reproduces the accepted harness's DEV smoke exactly** (`ee 8.867427e7`, `served 0.999`, `t0_agreement 0.2575`) |
| `--preflight-dev` | `FULL` k0 (v1) | 2 | 98 s | the judge arm through the formal driver: 39 judge fields per episode, dose 1.0, override rate 0.365 |
| `--preflight-dev` | `B-null` k0 (v1) | 2 | 107 s | the B-null draws **`(9_243_000, 0)`** — the DEVELOPMENT key, because the preflight is the development lane — and nothing else |
| `--preflight-dev` | `B-only` k0 | 2 | 107 s | the rule-independent shared cell; dose 0.598, front-loaded as the contract predicts |
| `--preflight-dev` | `A-only-v2` k0 (v2) | 2 | 66 s | the v2 drop-one of B exists and runs; dose 0.582, rule id `MC2-ARB-v2` |
| `--construct-only` | every non-judge cell × k = 0,1,2 (18) | 0 | — | 18/18 build on the **S1** seeds, **18 distinct configuration hashes**, S1-TRAIN triples `9_251/9_252/9_253 + k`, derived streams `9_321_00x` / `9_341_21x`, `D3-null` key `(9_261_000, k)`, eval `(9_111_000, 9_112_000)`, ε-decay 222, eq-(16) on the MODQN cell only |
| `--construct-only` | judge cells, both versions (7) | 0 | — | `FULL`/`B-only`/`B-null` under v1 and `A-only-v2`/`FULL`/`B-null` under v2 build on the S1 seeds with the **`(9_263_000, k)`** B-null key and the shared `MC2-B-ONLY-SHARED-v1` id for `B-only` |

**Independent RNG audit.** Every preflight training run was executed through a spy that patched
`numpy.random.default_rng` and `torch.manual_seed` and recorded every seed argument — an audit of
the harness's guards, not a use of them. Receipts: `rng-audit-*.json` in the session scratchpad.
Every run's distinct seed arguments were exactly
`9_201_000 / 9_202_000 / 9_203_000` (DEV triple), `9_211_000+i / 9_212_000+i` (DEVVAL),
`9_271_001` (the DEV derived catfish stream) and, for `B-null` only, `(9_243_000, 0)`.
**Forbidden hits: none**, in any run — no formal evaluation, calibration, CONFIRM, S1-TRAIN, S1-NULL
or S1-NULL-MC2 value was ever constructed.

**Measured judge cost (machine-independent call counts), at ε ≈ 1, per episode / per decision step:**
`FULL` 995 / 110, `B-null` 1442 / 160, `B-only` 779 / 87, `A-only-v2` 637 / 71. These are used in
`S1-MC2-MANIFEST-PLAN.md` §2 in place of the ≈ 200 calls/step early-regime estimate, which was about
1.6× pessimistic because the judge evaluates `κ(a^A)` only on rows where the challenger differs and
reuses the base evaluation whenever `a^A = x_u`.

---

## 6. Things a launcher must know (silent failures)

1. **`run_b0_pilot.py` leaves ε-decay at 2000.** A 1000-episode S1 run through it would still be
   exploring at the end and would confound the win gate. S1 gives both sides of the gate 222. Do not
   launch S1 through that script.
2. **`run_cf3_pilot.py --arm A0` reads the calibration episodes.** It must never be used for S1.
3. **Fresh roots only.** The new modules and the new lane change every code digest, so no existing
   development or E1 root can be resumed against this tree. A resume attempt would look like a
   harmless restart and would not be one.
4. **`--preflight-dev` and a formal root are never the same root.** The driver and the launcher both
   refuse a root that already holds the other manifest, and the lane is inside every configuration
   hash, so a preflight configuration can never hash to a formal one.
5. **A formal manifest requires `--reading-rules`.** `s1_manifest.py` and `s1_launch.py` refuse to
   write one without the digest of the controller's frozen reading rules.
6. **The evaluation read unregisters every teacher source and disables the judge.** If a future
   DEVVAL diagnostic is implemented *inside* the read and asks `T_NEXT` for an action, the read will
   raise rather than answer. That is deliberate — such a diagnostic belongs in a separate read-only
   pass (lane B's `b_output_change.py` already computes the formal-set `a^A` / `a^B` agreement from
   the raw files) — but it is the one place where a later addition to `devval()` would fail loudly.
7. **The `sat` venv's editable install points at a stale tree**: any new script must
   `sys.path.insert(0, "<tree>/src")`; `cf3_common` does, and `s1_common` / `run_s1` import it first
   for exactly that reason.
8. **`S1_EVAL_AT = (episodes,)`** — one terminal read, therefore exactly one checkpoint. Changing it
   re-opens the peeking question and is a different declaration.

---

## 7. What is NOT done here (and is not lane E's to do)

- No S1 launch, no sat compute, no formal / calibration / CONFIRM / S1-TRAIN episode stepped.
- The mechanism id is **not** chosen, the optional cells are **not** chosen, the reading rules are
  **not** frozen — all three are controller decisions, and the manifest writer refuses to produce a
  formal declaration until the third exists.
- The fresh-context review is **not** dispatched; `S1-MC2-REVIEW-BRIEF.md` is the brief for it, with
  placeholders for the final commit and manifest hash.
