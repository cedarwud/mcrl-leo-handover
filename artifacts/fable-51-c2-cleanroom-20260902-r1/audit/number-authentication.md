# Agent C — Number Authentication Report

Repository: `/home/u24/papers/mcrl-leo-handover` (read-only audit; nothing in the repo was modified).
Interpreter: `.venv/bin/python3` (Python 3.12.3), numpy `default_rng`.
Pooled convention used everywhere: `EE = sum(total_bits) / sum(total_energy_j)` over the rows in the
group ("ratio of sums"); percentage contrast `X vs Y` = `(EE_X / EE_Y - 1) * 100`.

Scripts used (kept for reference, not part of the repo):
`/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/d47a2ac0-70e1-49ca-b412-995b22bcb231/scratchpad/audit.py` (Claim A),
`audit_b.py` (Claim B), `audit_c.py` (Claim C), `audit_de.py` (Claims D, E).

---

## 0. Artifact integrity (file size, seal, schema/status)

| Artifact | result file size | Seal file | Seal `result_file_sha256` matches `sha256sum`? | schema | status | scientific_status / claim_ceiling |
|---|---:|---|---|---|---|---|
| A `artifacts/multi-catfish-v04-five-arm-ablation-20260901-r1/result.json` | 975,779 B | `result-seal.json` present | **YES** (`9142da31…08224`) | `multi-catfish-mcrl-v04-five-arm-ablation-result-v1` | `FIVE_ARM_COMPLETE` | `MULTI_CATFISH_NOT_ALL_CONFIRMED` / `FROZEN_FIVE_ARM_TRAIN_EE_NO_TEST_NO_TRAINING` |
| B `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json` | 9,227 B | `result-seal.json` present | **YES** (`4f424427…fc7613`) | `multi-catfish-mcrl-v04-route-interaction-diagnostic-v1` | `DIAGNOSTIC_COMPLETE` | claim_ceiling `INTERACTION_DIAGNOSIS_ONLY_NO_ROUTE_EFFICACY_CONFIRMATION` |
| C `artifacts/multi-catfish-v04-c3-confirmatory-20260901-r1/result.json` | 207,260 B | `result-seal.json` present | **YES** (`bb1a46a8…d396dd`) | `multi-catfish-mcrl-v04-c3-confirmatory-result-v1` | `CONFIRMATORY_COMPLETE` | `CONFIRM_C3` / `FROZEN_C3_CONFIRMATORY_TRAIN_EE_NO_TEST` |
| D `.../multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-one-native28-balanced-sixanchor-sixseed-r13.json` | 587,505 B | **none in directory** | N/A — no seal exists for the entire v07-c2-fast-iteration directory | `multi-catfish-mcrl-v07-c2-fast-train-eval-v1` | *(no top-level `status` key)* | `efficacy_established: false` / `DEVELOPMENT_100_UPDATE_FRESH_SCREEN_ONLY__NOT_EFFICACY` |
| E `.../multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-native28-sixanchor-loao-r14.json` | 24,068 B | **none in directory** | N/A | `multi-catfish-mcrl-v07-c2-motion-loao-diagnostic-v1` | `DEVELOPMENT_DIAGNOSTIC_ONLY_NOT_A_GATE` | claim_ceiling `EXISTING_SOURCE_LEARNABILITY_FALSIFICATION_ONLY` |

All three `sha256sum` checks were run directly (`sha256sum result.json`) and compared byte-for-byte
against the `result_file_sha256` field of the matching `result-seal.json`; all three matched exactly
(64/64 hex characters identical). B's seal also carries `source_five_arm_result_sha256` which was
checked against A's `result.json` sha256sum — matches. The entire `multi-catfish-v07-c2-fast-iteration-20260902-r1`
directory (23 files) contains no file with "seal" in its name, so D and E have no sealed integrity
receipt at all — this is a **process gap**, not a hash mismatch: there is nothing to check against.

---

## 1. Claim A — Five-arm frozen-policy result

Artifact: `artifacts/multi-catfish-v04-five-arm-ablation-20260901-r1/result.json`. Structure confirmed:
top-level `full`/`drop_c1`/`drop_c2`/`drop_c3`/`main`, each `{rows: [...], summary: {...}}`, 90 rows for
`full`/`drop_c1`/`drop_c2`/`drop_c3` (30 evaluation_seeds × 3 initialization_seeds) and 30 rows for `main`
(initialization_seed is `null` for all MAIN rows — MAIN is not split by initialization). Every row's
`total_bits`/`total_energy_j` reproduced `summary.total_bits`/`summary.total_energy_j`/`summary.pooled_ratio_of_sums_ee_bits_per_j`/`summary.served_fraction`
exactly by direct row summation (`served_fraction = sum(served_user_steps)/sum(decision_count)`).

### 1.1 Pooled contrasts

| Comparison | Claimed | Recomputed | Match |
|---|---:|---:|---|
| FULL vs DROP-C1 | +254.596% | +254.595969% | YES |
| FULL vs DROP-C2 | -30.397% | -30.396910% | YES |
| FULL vs DROP-C3 | +21.970% | +21.970172% | YES |
| FULL vs Main | -21.582% | -21.581985% | YES |

### 1.2 Per-initialization pooled contrasts (pool the 30 worlds within each initialization_seed)

| Route | init 2026092101 | init 2026092102 | init 2026092103 | positive count | Claimed | Match |
|---|---:|---:|---:|---:|---|---|
| C1 (FULL vs DROP_C1) | +95.238% | +317.335% | +294.673% | 3/3 | 3/3 | YES |
| C2 (FULL vs DROP_C2) | -62.961% | -17.466% | -20.249% | 0/3 | 0/3 | YES |
| C3 (FULL vs DROP_C3) | +145.123% | -5.666% | +14.111% | 2/3 | 2/3, values +145.123%/-5.666%/+14.111% | YES (exact) |

### 1.3 Per-physical-world contrasts (pool the 3 initializations within each evaluation_seed; 30 worlds)

| Route | Positive worlds | Claimed | Match |
|---|---:|---|---|
| C1 | 30/30 (range +203.8% to +346.6%) | 30/30 | YES |
| C2 | 0/30 (range -36.4% to -24.7%) | 0/30 | YES |
| C3 | 30/30 (range +10.8% to +40.1%) | 30/30 | YES |

Cross-check: recomputed per-world pooled values for world `2026092601` reproduce the artifact's own stored
`comparisons.C1.per_world[0]` (`full_ee_bits_per_j=71912872.21970598`, `drop_ee_bits_per_j=20036394.81936244`)
exactly, confirming the pooling convention used by the pipeline matches "pool the 3 initializations per
physical world."

### 1.4 Served fraction per arm (recomputed = `sum(served_user_steps)/sum(decision_count)`)

| Arm | Served fraction |
|---|---:|
| FULL | 97.1567% |
| DROP_C1 | 91.2411% |
| DROP_C2 | 99.8122% |
| DROP_C3 | 96.9111% |
| MAIN | 99.8100% |

All identical to the stored `summary.served_fraction` fields.

### 1.5 Paired-world bootstrap (resample 30 evaluation_seeds with replacement, 10,000 replicates; each
resampled world brings all 3 initializations; `numpy.random.default_rng(seed).integers(0, 30, size=30)`
per replicate; worlds ordered by ascending `evaluation_seed`)

| Route | Seed | Recomputed 95% interval | Claimed interval | Match |
|---|---:|---|---|---|
| C1 (FULL vs DROP_C1) | 2026092691 | [+243.956%, +266.153%] | [+243.956%, +266.153%] | YES |
| C2 (FULL vs DROP_C2) | 2026092692 | [-31.474%, -29.301%] | [-31.474%, -29.301%] | YES |
| C3 (FULL vs DROP_C3) | 2026092693 | [+19.753%, +24.260%] | [+19.753%, +24.260%] | YES |

At 10-decimal precision the recomputed lower/upper/median bounds agree with the artifact's own stored
`comparisons.<route>.bootstrap` block to 9-10 significant figures; the handful of cases that fail Python's
exact `==` do so only in the last 1-2 ULPs (floating-point summation-order noise between `sum()` and
`numpy` vectorized sum, not a methodological difference). **The bootstrap procedure was reproduced exactly**,
i.e., resampling unit = physical-world seed carrying all 3 initializations, `default_rng(seed)`, worlds
in ascending `evaluation_seed` order.

---

## 2. Claim B — Route-interaction diagnostic

Artifact: `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json`. Top-level
keys: `action_trace_diversity, c1_conditional_margins, claim_ceiling, diagnostic_interpretation, elapsed_s,
episode_count, episode_training, evaluation_seeds, evaluation_split, existing_five_arm_summaries,
held_out_ee_evaluated, initialization_seeds, per_initialization, schema, selected_q3_rung,
single_route_arms, single_route_summaries, source_five_arm_result_sha256, source_five_arm_seal_sha256,
source_manifest, status, test_split_opened`.

**Important limitation**: this artifact stores **only pooled summaries** (`total_bits`, `total_energy_j`,
`pooled_ratio_of_sums_ee_bits_per_j`, `served_fraction`, `served_user_steps`, `decision_count`, `rows`
[a *count*, not a list]) for `C1_ONLY`/`C2_ONLY`/`C3_ONLY` (= Q1/Q2/Q3), both pooled and per-initialization.
**No per-episode row list exists anywhere in this file or its directory** (the directory holds only
`result.json` and `result-seal.json`) for the single-route arms. `action_trace_diversity` confirms 90
episodes were run per single-route arm (`distinct_action_traces: 90, rows: 90`), so the underlying
per-episode data existed at run time but was **not persisted**. Per the task's instruction:
**Q1/Q2/Q3 (C1_ONLY/C2_ONLY/C3_ONLY) total_bits/total_energy_j are NOT independently recomputable from
any stored artifact — the stored summary numbers had to be taken as given** (their internal arithmetic
`EE = total_bits/total_energy_j` was verified and is self-consistent).
`existing_five_arm_summaries` in this file is byte-identical to arm summaries in artifact A (verified),
and `DROP_C2` (= Q1+Q3) rows **do** exist in artifact A, so DROP_C2 pooling below is fully recomputed from
raw rows.

### 2.1 Claimed contrasts

| Comparison | Claimed | Recomputed | Formula | Match |
|---|---:|---:|---|---|
| (Q1+Q3) vs (Q3) pooled | +49.247% | +49.246989% | EE(DROP_C2 rows in A) / EE(C3_ONLY summary in B) | YES |
| (Q1+Q3) vs (Q1) pooled | -10.286% | -10.285558% | EE(DROP_C2 rows in A) / EE(C1_ONLY summary in B) | YES |

The stored `c1_conditional_margins.with_Q3` field already contains the first comparison
(`difference_percent_of_right: 49.246988582727155`) — matches. **No precomputed field exists anywhere in
the artifact for "(Q1+Q3) vs (Q1)"** (only C1-margin-framed comparisons are stored); this number was
derived independently from the stored summary sums and matches the claim.

Per-initialization directions for (Q1+Q3) vs (Q1): **2026092101: -11.927%, 2026092102: -8.482%,
2026092103: -10.530% — all three negative**, matching the claim "all three initialization-specific
directions negative." (For completeness, per-init (Q1+Q3) vs (Q3): +50.395%, +54.336%, +43.293% — all
three positive, matching stored `per_initialization.<seed>.c1_conditional_margins.with_Q3` exactly.)

### 2.2 Eight-policy ranking by pooled EE (all values `bits/J`; sources: B's `single_route_summaries` for
Q1/Q2/Q3, A's raw rows pooled for the four combined arms and MAIN)

| Rank | Policy | Pooled EE (bits/J) | Total bits | Total energy (J) | Served fraction |
|---:|---|---:|---:|---:|---:|
| 1 | Q1 (C1_ONLY) | 117,049,799.51 | 1,114,538,755,403,521.50 | 9,521,919.39 | 99.7844% |
| 2 | Q1+Q3 (DROP_C2) | 105,010,574.08 | 1,265,446,744,504,998.50 | 12,050,660.19 | 99.8122% |
| 3 | Main | 93,206,395.06 | 360,314,952,969,558.94 | 3,865,775.01 | 99.8100% |
| 4 | Q1+Q2+Q3 (FULL) | 73,090,604.82 | 599,841,220,121,686.38 | 8,206,817.03 | 97.1567% |
| 5 | Q3 (C3_ONLY) | 70,360,263.26 | 582,946,709,084,929.12 | 8,285,169.53 | 96.7322% |
| 6 | Q1+Q2 (DROP_C3) | 59,924,982.89 | 520,064,257,440,155.44 | 8,678,588.33 | 96.9111% |
| 7 | Q2 (C2_ONLY) | 22,221,771.61 | 188,617,893,683,771.41 | 8,487,977.33 | 91.3656% |
| 8 | Q2+Q3 (DROP_C1) | 20,612,362.03 | 137,410,074,326,112.92 | 6,666,391.46 | 91.2411% |

### 2.3 Eight-policy ranking per initialization seed

**init = 2026092101**

| Rank | Policy | Pooled EE (bits/J) | Served fraction |
|---:|---|---:|---:|
| 1 | Q1 (C1_ONLY) | 117,313,338.08 | 99.8000% |
| 2 | Q1+Q3 (DROP_C2) | 103,321,753.43 | 99.8267% |
| 3 | Main* | 93,206,395.06 | 99.8100% |
| 4 | Q3 (C3_ONLY) | 68,700,387.90 | 95.1467% |
| 5 | Q1+Q2+Q3 (FULL) | 38,269,671.20 | 91.8400% |
| 6 | Q2 (C2_ONLY) | 22,670,815.30 | 91.3700% |
| 7 | Q2+Q3 (DROP_C1) | 19,601,522.00 | 91.2633% |
| 8 | Q1+Q2 (DROP_C3) | 15,612,449.90 | 91.3700% |

**init = 2026092102**

| Rank | Policy | Pooled EE (bits/J) | Served fraction |
|---:|---|---:|---:|
| 1 | Q1 (C1_ONLY) | 116,666,559.26 | 99.7733% |
| 2 | Q1+Q3 (DROP_C2) | 106,771,087.78 | 99.8000% |
| 3 | Q1+Q2 (DROP_C3) | 93,415,342.74 | 99.7633% |
| 4 | Main* | 93,206,395.06 | 99.8100% |
| 5 | Q1+Q2+Q3 (FULL) | 88,122,026.11 | 99.8167% |
| 6 | Q3 (C3_ONLY) | 69,180,959.62 | 96.8167% |
| 7 | Q2 (C2_ONLY) | 23,124,948.62 | 91.3700% |
| 8 | Q2+Q3 (DROP_C1) | 21,115,428.67 | 91.2867% |

**init = 2026092103**

| Rank | Policy | Pooled EE (bits/J) | Served fraction |
|---:|---|---:|---:|
| 1 | Q1 (C1_ONLY) | 117,166,012.57 | 99.7800% |
| 2 | Q1+Q3 (DROP_C2) | 104,828,560.48 | 99.8100% |
| 3 | Main* | 93,206,395.06 | 99.8100% |
| 4 | Q1+Q2+Q3 (FULL) | 83,601,842.11 | 99.8133% |
| 5 | Q1+Q2 (DROP_C3) | 73,263,626.55 | 99.6000% |
| 6 | Q3 (C3_ONLY) | 73,156,657.22 | 98.2333% |
| 7 | Q2+Q3 (DROP_C1) | 21,182,573.35 | 91.1733% |
| 8 | Q2 (C2_ONLY) | 20,849,813.88 | 91.3567% |

*Main's rows carry `initialization_seed = null` (not split by initialization); the same overall pooled
MAIN value is shown in all three per-init tables as the only available reference point (this mirrors how
the artifacts themselves treat MAIN in `per_initialization` blocks — the same MAIN summary repeated per init key).

---

## 3. Claim C — C3 confirmatory result

Doc: `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md` points to artifact
`artifacts/multi-catfish-v04-c3-confirmatory-20260901-r1/` (result SHA-256 `bb1a46a8…d396dd`, matches
`sha256sum` — see §0). This artifact **does** contain per-episode `rows` for both `full` and `drop_c3`
(90 rows each = 30 evaluation_seeds × 3 initializations; evaluation seeds `2026092501`-`2026092530`, a
**different** physical-world block than Claim A's `2026092601`-`2026092630`, consistent with the doc's
description of this as an earlier, separately-sealed confirmatory run).

| Measure | Claimed | Recomputed | Match |
|---|---:|---:|---|
| Pooled FULL vs DROP-C3 | +21.216% | +21.216321% | YES |
| Paired-world bootstrap 95% (seed 2026092599, stored in artifact) | [+18.619%, +23.996%] | [+18.619%, +23.996%] | YES (exact, same procedure as §1.5) |
| Positive physical worlds | 30/30 | 30/30 | YES |
| Positive initializations | 2/3 | 2/3 (+150.800%, -6.298%, +12.734%) | YES |
| Served fraction FULL / DROP-C3 (doc table) | 97.2522% / 97.0056% | 97.2522% / 97.0056% | YES |
| Median absolute per-world diff (doc) | 12,812,574.83 bits/J | 12,812,574.83 bits/J | YES |

---

## 4. Claim D — C2 V0.7 balanced R13

Artifact: `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-one-native28-balanced-sixanchor-sixseed-r13.json`
(no seal file exists for this directory — see §0).

**Structure**: top-level keys `claim_ceiling, efficacy_established, elapsed_evaluation_wall_seconds,
evaluation_seeds (6 seeds), evaluation_steps_cap, evaluations (list of 18 cell dicts), formal_training,
q2_user_scope, schema, source_paths, summary, target, test_split_opened, training`. Each of the 18
`evaluations` entries ("cells" = one of 3 lineages `q13-a/q13-b/q13-c` × one of 6 `evaluation_seed`s) has
fields: `action_flip_count, drop_c2 {actions (large nested per-user/per-step action-index array, irrelevant
to EE), ratio_of_sums_ee_bits_per_j, served_user_steps, steps, total_bits, total_energy_j}, ee_improvement_fraction,
evaluation_seed, full {same shape as drop_c2}, lineage, q2_user_scope, service_delta_user_steps, target`.
`summary` holds `cells, maximum/mean/median/minimum_improvement_fraction, negative_cells, positive_cells, zero_cells`
— **no pooled ratio-of-sums figure is pre-stored anywhere in this file**; it had to be derived from the
18 cells' `total_bits`/`total_energy_j`, which are present, so it is fully recomputable.

| Comparison | Claimed | Recomputed | Formula | Match |
|---|---:|---:|---|---|
| Pooled (all 18 cells) | +0.0465% | +0.046543% | sum(full.total_bits)/sum(full.total_energy_j) vs sum(drop_c2.total_bits)/sum(drop_c2.total_energy_j) | YES |
| Per-lineage q13-a | -0.0109% | -0.010884% | same, 6 cells for q13-a | YES |
| Per-lineage q13-b | -0.1544% | -0.154419% | same, 6 cells for q13-b | YES |
| Per-lineage q13-c | +0.3064% | +0.306413% | same, 6 cells for q13-c | YES |
| 18 cells positive/negative | 11 / 7 | 11 / 7 | per-cell sign of (full_EE/drop_c2_EE - 1), each cell = its own 1-row-vs-1-row ratio | YES (matches both independent per-cell recompute and stored `ee_improvement_fraction`/`summary.positive_cells`/`negative_cells`) |

Caution for future readers: the stored `summary.mean_improvement_fraction` (0.047026%) and
`median_improvement_fraction` (0.045823%) are a **different statistic** (mean/median of the 18 per-cell
fractions) that is numerically close to, but not identical to, the pooled ratio-of-sums figure
(+0.046543%) that the claim's "+0.0465%" actually matches. This is a units/convention note, not a
mismatch — the claim is consistent with the pooled convention specified in the task.

---

## 5. Claim E — C2 R14 leave-one-anchor-out

Artifact: `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-native28-sixanchor-loao-r14.json`
(no seal file — see §0).

**Structure**: top-level keys `boundaries, by_lineage, claim_ceiling, diagnostic_sha256, method, schema,
sources, status, summary`. `by_lineage.<q13-a|q13-b|q13-c>` each has: `action_only` / `model` / `zero`
(lineage-level aggregate metrics: `calibration_slope, mae, mse, sign_accuracy_nonzero, spearman`),
`folds` (list of 6 fold dicts, each with its own `action_only`/`model`/`zero` mse plus `focal_user, fold,
rows (=27), source_seed, target_step, train_final_loss, train_initial_loss, window`),
`folds_model_better_than_action_only`, `folds_model_better_than_zero`, `skill_vs_action_only`,
`skill_vs_strongest_null`, `skill_vs_zero`, `strongest_null` (the label of whichever null has lower MSE).
`method.folds_per_lineage = 6`, `updates_per_fold = 100`, split = leave-one-of-six-anchors-out.

Per-fold values are present, so the lineage aggregate was independently recomputed as the mean of the 6
per-fold `mse` values (folds have equal `rows=27`, so simple mean = rows-weighted mean) and matched the
stored lineage-level `mse` exactly for all three lineages and all three model types (model/action_only/zero).

| Lineage | model MSE | action_only MSE | zero MSE | strongest null MSE | model worse than strongest null? |
|---|---:|---:|---:|---:|---|
| q13-a | 1.867550 | 1.349865 | 0.741268 | 0.741268 (zero) | YES |
| q13-b | 1.233008 | 1.545193 | 0.889413 | 0.889413 (zero) | YES |
| q13-c | 1.162254 | 0.494633 | 0.757970 | 0.494633 (action_only) | YES |

| Claim | Claimed | Recomputed | Match |
|---|---:|---:|---|
| Count of lineages where model beats strongest null | 0/3 | 0/3 (all three worse) | YES |

Per-fold "model better than X" counts (`folds_model_better_than_action_only` / `folds_model_better_than_zero`)
were also independently recomputed by comparing each fold's `model.mse` to its own `action_only.mse`/`zero.mse`
and matched the stored counts exactly: q13-a (0,0), q13-b (4,2), q13-c (2,3).

---

## Master claims table

| Claim | Claimed value | Recomputed value | Match? | Formula | Artifact path |
|---|---:|---:|---|---|---|
| A: FULL vs DROP-C1 pooled | +254.596% | +254.595969% | YES | ratio-of-sums contrast, 90 rows each | `artifacts/multi-catfish-v04-five-arm-ablation-20260901-r1/result.json` |
| A: FULL vs DROP-C1 inits/worlds positive | 3/3, 30/30 | 3/3, 30/30 | YES | grouped pooled contrast, sign count | same |
| A: FULL vs DROP-C2 pooled | -30.397% | -30.396910% | YES | same | same |
| A: FULL vs DROP-C2 inits/worlds positive | 0/3, 0/30 | 0/3, 0/30 | YES | same | same |
| A: FULL vs DROP-C3 pooled | +21.970% | +21.970172% | YES | same | same |
| A: FULL vs DROP-C3 inits (values) | 2/3 (+145.123/-5.666/+14.111%) | 2/3 (+145.123/-5.666/+14.111%) | YES | same | same |
| A: FULL vs DROP-C3 worlds positive | 30/30 | 30/30 | YES | same | same |
| A: FULL vs Main pooled | -21.582% | -21.581985% | YES | same | same |
| A: served_fraction per arm | (see summary fields) | identical | YES | sum(served)/sum(decisions) | same |
| A: bootstrap C1 95% CI | [+243.956%,+266.153%] | [+243.956%,+266.153%] | YES (exact) | paired-world resample, seed 2026092691, 10k reps | same |
| A: bootstrap C2 95% CI | [-31.474%,-29.301%] | [-31.474%,-29.301%] | YES (exact) | seed 2026092692 | same |
| A: bootstrap C3 95% CI | [+19.753%,+24.260%] | [+19.753%,+24.260%] | YES (exact) | seed 2026092693 | same |
| B: (Q1+Q3) vs (Q3) pooled | +49.247% | +49.246989% | YES | ratio-of-sums; Q3=summary only (NOT recomputable from raw rows — none stored) | `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json` (+ A for DROP_C2 rows) |
| B: (Q1+Q3) vs (Q1) pooled, all 3 inits negative | -10.286%, 3/3 negative | -10.286% (-10.285558%), 3/3 negative (-11.93%,-8.48%,-10.53%) | YES | ratio-of-sums; Q1=summary only (NOT recomputable from raw rows) | same |
| B: 8-policy pooled ranking | n/a (not previously tabulated) | table in §2.2 | n/a | ratio-of-sums per policy | A + B |
| B: 8-policy per-init ranking | n/a | table in §2.3 | n/a | same, grouped by initialization_seed | A + B |
| C: FULL vs DROP-C3 pooled | +21.216% | +21.216321% | YES | ratio-of-sums, 90 rows each | `artifacts/multi-catfish-v04-c3-confirmatory-20260901-r1/result.json` |
| C: bootstrap 95% CI | [+18.619%,+23.996%] | [+18.619%,+23.996%] | YES (exact) | paired-world resample, seed 2026092599 (stored in artifact), 10k reps | same |
| C: worlds/inits positive | 30/30, 2/3 | 30/30, 2/3 | YES | grouped pooled contrast, sign count | same |
| D: pooled contrast (18 cells) | +0.0465% | +0.046543% | YES | ratio-of-sums over 18 cells (not pre-stored; derived from raw per-cell totals) | `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-one-native28-balanced-sixanchor-sixseed-r13.json` |
| D: per-lineage q13-a/b/c | -0.0109%/-0.1544%/+0.3064% | -0.010884%/-0.154419%/+0.306413% | YES | ratio-of-sums per lineage (6 cells) | same |
| D: 18 cells positive/negative | 11/7 | 11/7 | YES | per-cell sign, cross-checked vs stored `ee_improvement_fraction` and `summary` | same |
| E: lineages with model beating strongest null | 0/3 | 0/3 | YES | mean of 6 per-fold MSE per lineage; strongest_null=min(action_only,zero); compare | `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-native28-sixanchor-loao-r14.json` |

**No numeric mismatches were found.** Two items are explicitly NOT independently recomputable from raw
per-episode data because no row-level file exists anywhere in the repository for them: the Q1 (`C1_ONLY`)
and Q3 (`C3_ONLY`) pooled totals used throughout Claim B (only pooled summary sums are stored; verified
internally consistent, and cross-checked wherever a precomputed comparison field existed in the artifact
itself — all matched). Claims D and E also lack any seal file for their entire artifact directory, so
their file integrity rests on this audit's direct `sha256sum`/structural inspection rather than a stored
receipt.
