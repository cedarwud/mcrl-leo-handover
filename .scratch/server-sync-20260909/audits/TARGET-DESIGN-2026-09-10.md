# C1/C2 target design review — 2026-09-10

**`c1_difference_surplus`: `TARGET_REFORMULATE` — `c2_persistence_forecast`: `TARGET_WELL_POSED`.**

`DIAGNOSTIC_NOT_CLAIM`. No training run and no policy run was performed. No constant, threshold, sign, seed, horizon, price, guard or acceptance rule was changed; no sealed artefact was modified. Nothing under `/home/sat/mcrl-leo-handover` was touched. This is a design analysis; the C1 verdict stops at the sealed boundary and proposes nothing that would cross it.

---

## 0. Where the definitions actually live, and one correction to the brief

The brief says both heads are defined in `src/mcrl/stagec_v025/`. They are not. Both are in `src/mcrl/physics_v025/targets.py`:

- `c1_difference_surplus` — `src/mcrl/physics_v025/targets.py:154-173`, returning `C1Label` (`targets.py:147-151`).
- `c2_persistence_forecast` — `src/mcrl/physics_v025/targets.py:251-310`, returning `C2Label` (`targets.py:242-248`) over `OffsetProjection` rows (`targets.py:176-209`).

`src/mcrl/stagec_v025/` holds the *consumers*: the 16-D and 22-D feature schemas (`state.py:29-46`, `state.py:48-66` + `state.py:82-86`), the row builder that normalises the labels (`state.py:436`, `state.py:475-481`), the learner (`learner.py`), and the coordinator (`deployment.py`).

The sealed objective is `F = B − η_ref·E` (`targets.py:130-144`), with `Φ` added separately and the whole thing divided by `κ` to be dimensionless (`targets.py:169-173`).

### 0.1 The single most consequential finding about the available evidence

**The 176,223 checked-in pilot training rows do not carry the production targets.** `scripts/run_v025_pilot_c3.py:89` sets `PILOT_PRIMITIVE_SOURCE_FALLBACK = True`, and `_build_anchor_rows` (`run_v025_pilot_c3.py:537-543`) therefore dispatches to `_build_anchor_rows_primitive`, which **never calls `c1_difference_surplus` or `c2_persistence_forecast`**. It substitutes:

- C1 → `κ · tanh(log(nominal_gain_ratio))`, or `κ · (−1)` for illegal/null (`run_v025_pilot_c3.py:406-409`, written at `:460`), plus the exact `Φ` difference (`:434`, `:461`);
- C2 → `κ · Σ_offsets tanh(log(future_gain_ratio))` under the same absorbing rule, `−1` per lost offset (`run_v025_pilot_c3.py:414-427`, written at `:462`).

Verified numerically: `c1_label_bits/κ ∈ [−1.000000, +0.999954]` with exactly 1000 of 9805 sampled rows sitting on the hard floor `−1.0`, and `c2_label_bits/κ ∈ [−3.0, +2.974]` with 1865 rows exactly at `−3.0`. Those are the signatures of the surrogate, not of a `B − ηE` difference.

Consequence: the surrogate C1 is a **per-user-local monotone squash of a per-user gain ratio** — it contains, by construction, no coupled-fixed-point content at all. Any learnability measured on those rows is measuring a different and far easier problem. Concretely, a plain 16-D linear model reaches **level R² = 0.598 and 0.801 within-group pairwise ordering** on the surrogate label, versus **held-out R² = 0.151 and 0.650 ordering** on the production target measured below. The pilot's apparent C1 learnability is an artefact of the fallback.

The 180 checked-in *coalition* rows are genuine (`_coalition_row`, `run_v025_pilot_c3.py:910-955`, via `build_coalition_row` → `coalition_identity`, `targets.py:568-618`), but they are all `|A| = 2`.

To answer Q1/Q2/Q3 on the real object I therefore ran a fresh probe (`scripts/probe_c1_production_target.py`) that evaluates every shortlisted **unilateral** configuration through the sealed engine's coupled boundary at 24 real anchors of `V025_PROBE/world/1`, and computes the exact `c1_difference_surplus` identity with a per-user-bits decomposition. 23,478 rows, 2,400 `(anchor, user)` groups, 100 users per anchor.

Two internal checks pass exactly: the decomposition identity residual is `3.6e-15`, and the target at the base action is **exactly `0.0` in all 2,400 groups** (so the C1 gauge is genuine, not approximate).

> **Incidental defect found while building the probe, reported not fixed.** The sealed engine's two evaluation paths disagree. `StepEvaluator.evaluate` (per-config, `.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:903`) and `StepEvaluator.evaluate_many` (dense batched `a-r0` path, `:793`) return different whole-network bits for the *same* `Configuration`. On the anchors visible in my run log the gap ranged from `−29.45` to `+54.08` κ-units of network bits. My first probe run mixed the two paths (reference through `evaluate`, candidates through `evaluate_many`) and produced a spurious constant offset in every label — `base_action_y_max_abs` was `78.17` instead of `0.0`. I corrected the probe to force both through `evaluate_many`. **All numbers below are from the corrected run.** I have not investigated which path is authoritative and I have changed nothing in the engine; this is flagged for the owners because `_build_anchor_rows_primitive` caches the reference through `evaluate` (`run_v025_pilot_c3.py:396`) while the catalogue goes through `evaluate_many`.

---

## Q1. Decomposition — is the expensive part small, slow, or common?

**Answer: no, on all three counts.** Measured, not argued.

The target is exactly `y(u,a) = [B(a)−B(0)]/κ − η[E(a)−E(0)]/κ + [Φ(a)−Φ(0)]` (`targets.py:169-173`). Split the bits term by per-user attribution (`NetworkOutcome.per_user_bits`, `targets.py:93`, `targets.py:125-126`):

| part | what it costs | sd | share of `var(y)` | corr with `y` |
|---|---|---:|---:|---:|
| `own` = focal user's own bits change / κ | needs the coupled solve, but is a *local* quantity | 1.146 | **0.187** | 0.389 |
| `ext` = Σ over the other 99 users / κ | **requires the coupled solve** | 1.161 | **0.375** | 0.771 |
| `energy` = −η·ΔE_network / κ | **requires the coupled solve** | 1.251 | **0.418** | 0.798 |
| `phi` = ΔΦ | **closed form, fully pre-decision** (`targets.py:72-81`) | 0.549 | **0.021** | 0.090 |

`sd(y) = 2.389`. Shares are covariance shares and sum to 1.

- **The cheap part is tiny.** The only genuinely pre-decision term is `Φ`, a deterministic function of the before/after physical identity pair. It carries **2.1%** of the variance. Ranking on `Φ` alone gives 0.196 within-group pairwise ordering (worse than the 0.5 coin) and 0.176 top-1.
- **The expensive part is not small.** The two whole-network terms carry **79.3%** of the variance, and `mean|ext| = 0.624` against `mean|own| = 0.982` — the cross-user externality is 45% of the magnitude of the total bits change, not a perturbation.
- **The expensive part is not common across candidates at one anchor.** This is the decisive number: a one-way decomposition of `ext` by anchor gives **between-anchor share 0.0109** — 98.9% of the externality's variance lives *within* an anchor. It therefore does not cancel in the ranking and cannot be dropped. It is not even common within one user's action list: by `(anchor, user)` the between share is 0.431, so `ext` genuinely depends on *which* action the focal user takes.
- **Dropping only the cross-user externality** (an oracle that still knows the coupled energy) gives R² = 0.754 against `y` and 0.911 within-group ordering. **Dropping everything expensive** (`own + Φ`) gives R² = 0.181 and 0.510 ordering — chance.

**There is no decomposition in which the expensive term is small, slowly varying, or common at an anchor.** The first head's target genuinely requires the coupled solve it exists to avoid.

### Q1b. The harder structural fact: even an exact C1 head does not fix the selector

The coordinator's score is `Σ_i [ĥ(a_i) − ĥ(b_i)]` over the changed set, plus the interaction term (`deployment.py:626-645`, `:717-736`). Its exact analogue is `Σ_{i∈A} d_i` — sealed as `C1(config)` in contract v1 §B4. From my probe, using the **exact** production target:

| | median over 24 anchors |
|---|---:|
| users with a strictly positive best unilateral surplus | **82 of 100** |
| `Σ` of those surpluses (the additive-optimal coalition's exact C1) | **200.4** |
| best single-user move | **8.02** |
| ratio | **20.5×** |

The exact additive term grows roughly linearly in `|A|`, so the additive path monotonically favours near-grand coalitions **with a perfect C1 head**. Every correction lives in `Ψ`. The prior diagnosis measured this at `|A| = 100`: exact singleton sum `+480.113`, exact `Ψ` `−440.079`, exact final `+40.034` (`SELECTOR-DIAGNOSIS-2026-09-09.md` §3). A ~10× cancellation between two large terms whose *sum* is the small quantity actually being ranked.

Honest counterweight: this cancellation is a large-`|A|` phenomenon. On the 180 real `|A| = 2` coalition rows there is no such benefit — median `|C1| = 4.126`, `|Ψ| = 15.831`, `|ΔF| = 15.072`, `corr(C1, Ψ) = −0.159`, and `sign(ΔF) ≠ sign(C1)` in 35.6% of rows. At `k = 2` predicting the sum is not easier than predicting `Ψ`.

---

## Q2. Level versus order

**The pipeline needs neither pure calibration nor pure per-user ordering. It needs per-user values that are correct at the zero point and share one common positive scale.** This is a sharper answer than "ordering suffices", and the distinction is exactly the failure mode.

### What the code does with the value

Downstream of the selector, the score value is inert. `SelectorDecision.score` (`deployment.py:66`) is written at `deployment.py:707` and `:736`, passed through unchanged at `:802`, and read nowhere else — not in `evaluation.py`, `merge.py`, `acceptance.py` or `experiments.py`. Every gate consumes exact physics on the *selected profile*: `clip_decision` (`merge.py:428-489`, thresholds at `:451-454`), `admission_decision` (`merge.py:394-425`, `:413`), and the pooled-EE metrics (`merge.py:178-212`). `masked_argmax` (`deployment.py:101-109`) breaks ties on `-index`, not on any level or tolerance. So: **no acceptance rule, gate, threshold or hypothesis test consumes the learned score value.** Only the chosen profile escapes.

### Why "ordering suffices" is nonetheless wrong here

Inside the selector the score is a **sum over a variable-size changed set** (`_additive_score`, `deployment.py:635-645`): unchanged users contribute exactly `0` because `selected == baseline`, and changed users contribute `ĥ(a_i) − ĥ(b_i)`. Ranking two candidate profiles compares sums over *different-sized* sets. Consequently:

- A constant added to the head cancels (it is differenced) — the level of `ĥ` itself is free, and the gauge terms exist to pin it (`learner.py:285-289` for the linear head, `learner.py:779`/`:785` for the deployed MLP, `gauge_beta = 0.2` for C1, `0.1` for C2, `learner.py:45-55`).
- A **monotone but non-affine** distortion of the per-user values changes the ranking of the sums. Only `y → c·y` with `c > 0` is safe, and `c` must be *shared* by C1, C2 and `Ψ̂` because they are added (`deployment.py:730`).
- A per-user bias `b` in the estimate of `d_i` inflates a size-`k` candidate by `k·b`. At `k = 100` a bias of `+0.03` κ-units per user is worth `+3` — comparable to a whole real coalition's value.

So a per-user *rank* target would be inadmissible without also replacing the coordinator's aggregation rule. The one place where ordering alone genuinely suffices is `ProfileSelector.repair_reference` (`deployment.py:511-546`) and `independent_two_head_profile` (`deployment.py:112-122`): these take a per-user `masked_argmax` of `C1 + C2` to build the reference proposal `a⁰` / repair joint conflicts, and there only the within-user ordering matters.

### How much easier is ordering, on real rows?

Held out by anchor (16 train / 8 test anchors, 15,684 / 7,794 rows), relu MLP, full-batch Adam, 6,000 steps, admissible 16-D Q1 vector only — `scripts/probe_c1_learnability.py`:

| model / target | test R² | within-user pairwise order | top-1 | sign accuracy |
|---|---:|---:|---:|---:|
| production C1 head shape `16→8→1`, regression on `y` | **0.151** | 0.650 | 0.196 | 0.676 |
| `16→64→64→1`, regression on `y` | −0.172 | 0.601 | 0.244 | 0.624 |
| `16→64→64→1`, **pairwise ranking loss** on `y` | n/a (scale-free) | **0.693** | 0.241 | n/a |
| oracle `own + energy + Φ` (no cross-user externality) | 0.754 (algebraic, full sample) | **0.902** | 0.675 | — |
| chance | 0 | 0.500 | ~0.10 | 0.500 |

(The `16→64→64→1` regression on `own + Φ` diverged — test R² `−2.4e4`. Reported for completeness; I draw nothing from it.)

Reading: **switching from a value objective to a pure ranking objective buys about 4 points of pairwise ordering (0.650 → 0.693) and nothing on top-1.** That is real but small, and it costs the scale the coordinator needs. Meanwhile the oracle that merely removes the cross-user externality reaches 0.902. The binding constraint is that the target contains whole-network coupled content the 16-D per-user vector cannot see — not the level-versus-order framing.

---

## Q3. Anchor-relative targets

**The premise does not hold for this target, and anchor-centring would additionally be unsafe.**

Production C1 target, 23,478 rows:

| grouping | between share | within share |
|---|---:|---:|
| by anchor (24 groups) | **0.080** | **0.920** |
| by `(anchor, user)` (2,400 groups) | 0.558 | 0.442 |

Only **8.0%** of the variance is between anchors. Centring the target within its anchor would remove one twelfth of the variance and would not concentrate the model's capacity anywhere useful. For comparison, the *surrogate* rows give a different and misleading picture (between-anchor 0.368 for C1, 0.645 for C2, 176,223 rows) — another reason not to design from them.

Beyond the arithmetic, anchor-centring is structurally wrong here. `y(base action) = 0` **exactly** (verified: max abs `0.0` over 2,400 groups), and the coordinator relies on that zero: for an unchanged user the contribution is exactly nil, so the zero point encodes "is it worth moving this user at all". Subtracting an anchor mean `m` would shift a size-`k` candidate by `−k·m` — it would *introduce* precisely the size bias the pipeline is currently suffering from. Ranking within the anchor's candidate pool has the same defect: ranks are not summable over variable-size sets.

**An absolute-value target is not the problem, and anchor-relative targets are not the fix.**

---

## Q4. The second head

**The persistence forecast's target is well posed, and the absorbing structure is not the obstacle it looks like.**

The target is `(core − κ·lost)/κ = core/κ − lost` (`targets.py:299-310`), where `core` accumulates `ΔB − η·ΔE` per offset **only while alive**, and `lost` counts the failing offset and every offset after it (`targets.py:289-308`). So the scalar is a bounded continuous part plus an integer in `{0,1,2,3}`.

Four findings:

1. **The discrete part is exactly computable from the head's own inputs.** `lost` is a function of the per-offset `valid`/`survives` flags, and those flags are in the 22-D Q2 vector (`state.py:61-66`, expanded at `state.py:82-86`, populated at `state.py:426-434`). In the production path they come from the *same* `OffsetProjection` rows that are fed to `c2_persistence_forecast` (`run_v025_pilot_c3.py:600-607` supplies the label; `:665-672` extracts the same `projections` into the feature vector). The head is handed the jump.
2. **On real data the absorbing rule is linear.** In principle `lost` is non-linear in the three failure bits: over the full cube, the best linear fit has max residual `0.75` and R² `0.831`. But over all **176,223** real rows only **4 of 8** patterns occur — `(0,0,0)→0`, `(0,0,1)→1`, `(0,1,1)→2`, `(1,1,1)→3` — and **zero rows** are non-monotone. On that support `lost = f₁+f₂+f₃` exactly (weighted linear fit residual `4.2e-12`). The absorbing rule imposes no representational barrier a smooth regressor cannot cross.
3. **A survival/hazard reformulation would therefore be a modelling convenience, not a well-posedness repair.** `lost` accounts for 38.5% of the target's variance and correlates `−0.919` with it, and 76.0% of rows lose at least one offset — so it dominates. But since it is a closed-form function of six input bits, a hazard head would be *learning something already known*. The residual estimation problem is the continuous `core/κ` either way.
4. **The non-zero base-action level is harmless.** Unlike C1, `y₂` at the reference action is not zero: on the checked-in rows the base row's normalised C2 label is non-zero in 88.9% of groups, mean `−1.380`, max magnitude `3.0` — it is minus the base action's own lost-offset count. This does not matter, because both training (`learner.py:247`, target = `label(candidate) − label(reference)`) and deployment (`deployment.py:641-644`) use only differences, and unchanged users cancel exactly. The effective per-user quantity is `core_a/κ − lost_a + lost_base`, which is the sensible thing: a user whose base association is about to die earns credit for any survivor.

**Caveat, stated plainly.** I could not measure the *production* C2 target on real rows — no artefact in this workspace carries it, for the reason in §0.1. What I verified for C2 is (a) the target algebra, from the code; (b) that the surrogate replicates the absorbing accounting verbatim, so the structural conclusions transfer; (c) the empirical monotonicity of the failure patterns. Point (c) was measured on the surrogate's `survives = legal at that offset`, which is monotone by construction of shrinking visibility/D2 windows. The production `OffsetProjection.valid`/`survives` (`targets.py:176-209`) can also fail on power-cap grounds and could in principle be non-monotone. If non-monotone patterns turn out to occur in production forecasts, finding 2 weakens — but finding 1 still holds, and finding 1 is the one that decides well-posedness.

---

## Q5. Verdict

### `c2_persistence_forecast` — `TARGET_WELL_POSED`

The object is bounded, gauge-consistent under the differences the pipeline actually takes, and its discrete component is a closed-form function of features the head already receives. There is no discontinuity a smooth regressor cannot represent on the observed support. **If the C2 head is underperforming, the problem is features or estimation, not what it is asked to predict.** I am not manufacturing a redesign for it.

### `c1_difference_surplus` — `TARGET_REFORMULATE`

Three measured facts, none of which an admissible feature set can repair:

1. 79.3% of the target's variance is in whole-network coupled terms that require exactly the solve the head exists to avoid, and 98.9% of the externality's variance is *within* an anchor, so none of it cancels in the ranking (Q1).
2. With the production head shape and the sealed 16-D vector, held-out `R² = 0.151` and pairwise ordering `0.650`; a ranking objective reaches only `0.693`, while an oracle that removes just the cross-user externality reaches `0.902` (Q2).
3. Even an **exact** C1 head does not produce the intended selector behaviour: the exact additive term grows ~linearly in `|A|` (median `200.4` at the additive optimum versus `8.02` for the best single move), so the whole correction sits in a `Ψ` term of opposite sign and comparable magnitude — `+480.113 / −440.079` for a `+40.034` result at `|A| = 100` (`SELECTOR-DIAGNOSIS-2026-09-09.md` §3). This is an ill-conditioned split, not a learning failure (Q1b).

**The specific alternative object.** Rank on a single set-conditioned prediction of the joint objective change, `ΔF(A)/κ = [F(a_A) − F(a⁰)]/κ`, instead of on `Σ_i d̂_i + Ψ̂_A`. The score already reconstructs exactly this quantity by the sealed identity (`targets.py:608-617`, `CoalitionIdentity.assert_exact` at `targets.py:561-565`), the permutation-invariant set head and coalition context that would carry it already exist (`learner.py:822-923`, `coalitions.py:231-281`), and predicting the sum removes the ~10× cancellation between two large opposing terms. The per-user Q1/Q2 heads would be retained for what they are demonstrably adequate at and what the contract already uses them for — generating the reference proposal `a⁰` and repairing joint conflicts (`deployment.py:511-546`), where only within-user ordering matters and the `k·b` accumulation cannot arise.

### Sealed boundary — I stop here

This reformulation **would touch sealed artefacts and frozen manifests**. Specifically:

- `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`, **sealed 2026-09-08 ≈ 18:45 UTC** — §B4 fixes `C1(config) = Σ_{i∈A} d_i`, `C3(config) = Ψ_A` and the identity `C1 + C3 = F(a_A) − F(a⁰)` as a KAT; §C1 fixes the Q1/Q2 head form and the per-user argmax deployment; §C2 fixes the deployed S3 score as `C1 + C2 + Ψ̂`. §C6 states in terms that a negative or inconclusive result does not permit changing features, catalogues, sources or regimes.
- `src/mcrl/physics_v025/targets.py` — `c1_difference_surplus`, `coalition_identity`, `set_score_decomposition` (the `C1 + C3 == joint/κ` assertion at `targets.py:523`).
- `src/mcrl/stagec_v025/deployment.py:626-736` — the additive-plus-interaction score form.
- `src/mcrl/stagec_v025/state.py` and `coalitions.py`/`shards.py` — the row label fields and the `Q1_SCHEMA_SHA256`/`Q2_SCHEMA_SHA256` digests carried in every shard header and re-checked on read (`shards.py:142`, `shards.py:214-215`, `shards.py:270`), plus the existing pilot rows-manifest and training-manifest digests.
- `tests/stagec_v025/test_contract_v1_acceptance.py` — the T1 exhaustive-decomposition KAT and the T2 information-twins KAT are written against exactly this identity.

**Per the terms of this review I stop at that boundary and propose nothing further.** The verdict is `TARGET_REFORMULATE` on the evidence; the decision to open contract v1 is not mine and I have not prepared a change to any of the files above.

### One thing that should be fixed regardless of the verdict, and is not sealed

The pilot's own training rows carry the surrogate labels, not the production targets (`scripts/run_v025_pilot_c3.py:89`). Whatever is decided about the target object, no conclusion about C1/C2 learnability should be drawn from `artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/rows/`. The 180 coalition rows in that run are genuine; the 176,223 source rows are not the production estimand.

---

## Method, provenance, and what is what

**Verified by running code.**

- All target and consumer definitions cited above were read in this workspace at the stated lines.
- The surrogate-label finding (§0.1): the fallback flag, the dispatch, and the numeric signature of the labels on disk.
- Everything in the Q1, Q2 ("how much easier"), Q3 and Q4 tables: computed from `artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/rows/` (176,223 rows) and from the fresh production probe (23,478 rows, 24 anchors).
- The two probe self-checks: decomposition identity residual `3.6e-15`, base-action target exactly `0.0`.
- The `evaluate` / `evaluate_many` discrepancy.

**Derived on paper from the code, not measured.**

- The `k·b` accumulation argument and the "affine-with-shared-scale, not monotone" characterisation in Q2, from `deployment.py:635-645` and `:717-736`.
- The C2 effective per-user quantity `core_a/κ − lost_a + lost_base`, from `targets.py:299-310` composed with `learner.py:247` and `deployment.py:641-644`.

**Inferred, and flagged as such.**

- That the production `OffsetProjection` failure patterns are monotone like the surrogate's. Not verified; see the Q4 caveat.
- That the `evaluate`/`evaluate_many` gap is a defect rather than an intended fast/exact split. Not investigated.

**Not reached.** Nothing. Q1–Q5 are all answered, with the C2 magnitude caveat stated in Q4.

**Reproduction** (three processes, no training, no policy run):

```bash
cd /home/sat/mcrl-v025-selector-ws

# Surrogate-row analysis: gauge, Q1 Phi split, Q3 variance, Q4 absorbing structure
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/analyse_c1c2_target_design.py

# Exact production C1 target on 24 real anchors (~4 min; tape build dominates)
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/probe_c1_production_target.py --anchors 24 --steps 30

# Absorbing-pattern support + production-target decomposition/variance/fits
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/analyse_c1c2_target_design2.py

# Held-out level-vs-order learnability (offline numpy fits; no pipeline learner invoked)
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/probe_c1_learnability.py
```

Machine-readable outputs: `.scratch/c1c2-target-design/results.json`, `results2b.json`, `learnability.json`, `production-c1.json`.

Scripts and this report are confined to `/home/sat/mcrl-v025-selector-ws`. No file under `src/`, `artifacts/`, `docs/` or `tests/` was modified, and no sealed artefact was written.
