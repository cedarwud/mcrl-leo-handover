**Train/score anchor overlap is total: every one of the 20 panel anchors (`V025_PROBE/world/1`, steps 0–6, global 000–019) is a training anchor of every run checked. That covers the three converged-schedule runs (exact 22-anchor, Q1 v3, Q1 v3 control) and the three Z-VIEW runs, each 20/20, with zero non-overlapping panel anchors. Any score on these panels is therefore IN-SAMPLE, the Z-VIEW-SCORING numbers included. No run has been scored yet, because none has finished: at 00:04 UTC the exact run had 5/16 seeds at 4,000 updates, Q1 v3 had 4/16 and the v3 control 4/16, and none has a `training-result.json`. So this report gives no route marginals and no seed-sign counts.**

# CONVSCORE — converged-schedule scoring: leakage gate done, scoring pending — 2026-09-11

`DEVELOPMENT_SCORING_NOT_A_CLAIM`. I used development anchors 000–021 (world 1, date 2026-01-07) and did not read any of the 48 evaluation-only claim dates. The scorer was not invoked on any new checkpoint. I wrote nothing into another workspace or any training output directory, and I did not modify `/home/sat/mcrl-leo-handover` or its `.venv`.

## 0. Status per run (verified by running code, 2026-09-11 00:04 UTC)

| run | output dir | Q1 / Q2 schema SHA-256 (launch receipt) | seeds complete at 4,000 | in progress | `training-result.json` | job report with admissible checkpoint |
|---|---|---|---:|---|---|---|
| exact, 22 anchors (`exact22`) | `/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-step-decay-16seed-4000-20260910` | `c002ea88…` / `a891dd98…` | **5/16** | seed `6114226365011333154` at 3,400 | absent | `EXACT-CORPUS-TRAINING-V2-2026-09-10.md` **absent** |
| Q1 v3 (`q1v3`) | `/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-step-decay-16seed-4000-20260910` | `3850d23f…` / `a891dd98…` | **4/16** | seed `3155344545377116990` at 3,300 | absent | `Q1V3-TRAINING-2026-09-10.md` **absent** |
| Q1 v3 control (`q1v3_control`) | `/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-control-step-decay-16seed-4000-20260910` | `ee6baea9…` / `a891dd98…` | **4/16** | seed `3155344545377116990` at 2,900 | absent | same report **absent** |

The complete seeds are the first entries of the shared seed list: `6407676579069309528`, `925030429265975792`, `5166716249291843642`, `7234013715671416945`, plus `3155344545377116990` for exact22 only.

- **All three runs are PENDING.** The task rule is to score only completed runs, so none was scored.
- **The exact run was interrupted and has resumed.** At 23:48:40 UTC the codex session driving `EXACTTRAIN2` died (`Invalid prompt: … flagged as potentially violating our usage policy`), and its training child died with it at seed `6114226365011333154`, epoch 3,200. The wrapper `run_resumable2.sh` resumed the session at 23:53:40. Training restarted through `/home/sat/mcrl-v025-exacttrain-ws/.scratch/exacttrain2/resume_declared_run.py` and wrote epoch 3,300 at 23:59:49.
  - That seed now has a mid-schedule resume boundary. At scoring time, check that its epoch-4,000 checkpoint matches an uninterrupted trajectory, or label it as resumed.
- **Expected completion (derived from checkpoint mtimes).** Recent seeds took 54–58 min each; the first seed of each Q1 v3 run took 94 min (v3) and 103 min (control). All six runs share one 16-seed list (verified).
  - exact22: about 09:30–10:30 UTC.
  - Q1 v3 and v3 control: about 10:00–11:30 UTC.
  - Scoring each run afterwards: about 45–50 min. This is the Z-VIEW-measured wall time for 16 checkpoints on one panel.

## 1. Step 1 — train/score leakage check (verified by running code)

Scripts, all run on `sat` at `nice -n 16` with all six BLAS/OMP thread variables set to 1, one Python process at a time:

| script | SHA-256 | output | output SHA-256 | peak RSS |
|---|---|---|---|---:|
| `scripts/leakage_check.py` | `cd1375b7…` | `out/leakage-check.json` | `73fbe56b…` | 723,329,024 B |
| `scripts/state_identity.py` | `b9209034…` | `out/state-identity.json` | `9860fd8f…` | 77,881,344 B |
| `scripts/label_identity.py` | `0e76b188…` | `out/label-identity.json` | `97438756…` | 75,235,328 B |
| `scripts/coal_identity.py` | `5baef27e…` | `out/coalition-label-identity.json` | `4d96fc18…` | 35,237,888 B |

### 1.1 Anchor lists

**Training anchors.** All six runs have the same list: the launch-receipt `corpus.anchor_list` is equal across all six. Each list also agrees with the header of every source-view file the receipt binds, and 44/44 corpus-file SHA-256 values match their receipts in every run.

| global | world | step | carrier | in panel? |
|---:|---|---:|---|---|
| 000 | V025_PROBE/world/1 | 0 | nearest-eligible | yes |
| 001 | V025_PROBE/world/1 | 0 | stay-if-possible | yes |
| 002 | V025_PROBE/world/1 | 0 | random-masked | yes |
| 003 | V025_PROBE/world/1 | 1 | nearest-eligible | yes |
| 004 | V025_PROBE/world/1 | 1 | stay-if-possible | yes |
| 005 | V025_PROBE/world/1 | 1 | random-masked | yes |
| 006 | V025_PROBE/world/1 | 2 | nearest-eligible | yes |
| 007 | V025_PROBE/world/1 | 2 | stay-if-possible | yes |
| 008 | V025_PROBE/world/1 | 2 | random-masked | yes |
| 009 | V025_PROBE/world/1 | 3 | nearest-eligible | yes |
| 010 | V025_PROBE/world/1 | 3 | stay-if-possible | yes |
| 011 | V025_PROBE/world/1 | 3 | random-masked | yes |
| 012 | V025_PROBE/world/1 | 4 | nearest-eligible | yes |
| 013 | V025_PROBE/world/1 | 4 | stay-if-possible | yes |
| 014 | V025_PROBE/world/1 | 4 | random-masked | yes |
| 015 | V025_PROBE/world/1 | 5 | nearest-eligible | yes |
| 016 | V025_PROBE/world/1 | 5 | stay-if-possible | yes |
| 017 | V025_PROBE/world/1 | 5 | random-masked | yes |
| 018 | V025_PROBE/world/1 | 6 | nearest-eligible | yes |
| 019 | V025_PROBE/world/1 | 6 | stay-if-possible | yes |
| 020 | V025_PROBE/world/1 | 6 | random-masked | **no (train only)** |
| 021 | V025_PROBE/world/1 | 7 | nearest-eligible | **no (train only)** |

**Panel anchors.** All five panels have the same list. I read the `anchor_id` of every anchor in each panel JSON; each list equals the panel's receipt `run_identity.sources` and matches global 000–019 in the table above. The panels are `panel-q1v1` `dc5df10b…`, `panel-q1v2` `b5a2c365…`, `panel-q1v2z` `2a905423…`, `panel-q1v3` `90cf0181…` and `panel-q1v3-control` `bd5a967b…`; every file SHA-256 was re-hashed and equals its receipt's `panel_sha256`.

### 1.2 Overlap counts

| training run | its panel (by Q1/Q2 digest) | overlap | panel anchors not trained on | panel's source-view file SHA-256 = the training corpus's own file |
|---|---|---:|---:|---:|
| exact22 | panel-q1v1 | **20/20** | 0 | 0/20 (see 1.3: same rows, different embedded surrogate record) |
| q1v3 | panel-q1v3 | **20/20** | 0 | **20/20**: the panel was built from this run's training files |
| q1v3_control | panel-q1v3-control | **20/20** | 0 | **20/20** |
| Z-VIEW Q1 v1 (`firstrun-500ep-20260910T1355Z`) | panel-q1v1 | **20/20** | 0 | **20/20** |
| Z-VIEW Q1 v2 (`firstrun-v2-500ep-20260910T1425Z`) | panel-q1v2 | **20/20** | 0 | 0/20 (panel-q1v2 binds the Q1 v1 view files; its Q1 v2 state is a projection) |
| Z-VIEW z (`firstrun-v2z-500ep-20260910T1512Z`) | panel-q1v2z | **20/20** | 0 | **20/20** |

Every training-run × panel combination also gives 20/20, so the result does not depend on the panel pairing (`out/leakage-check.json`, key `overlap`).

### 1.3 The overlap is row-for-row, not just by anchor name

I compared the panel's source rows with each run's training rows over all 20 panel anchors. Each panel's source rows are the file whose bytes carry the view SHA-256 recorded in the panel receipt. The comparison key is anchor, user, action, action mask, `q1_state`, `q2_state`, decision time and world seed.

| run vs panel | rows compared | rows with identical decision state | fields that differ |
|---|---:|---:|---|
| exact22 vs panel-q1v1 | 19,617 | **19,617** | only the embedded, unread surrogate comparison record: `exact_source_view.surrogate.method` (all rows) and `exact_source_view.surrogate.c2_normalized_total_hex` (1,822 rows) |
| q1v3 vs panel-q1v3 | 19,617 | **19,617** | none |
| q1v3_control vs panel-q1v3-control | 19,617 | **19,617** | none |
| Z-VIEW Q1 v1 vs panel-q1v1 | 19,617 | **19,617** | none |

So the heads are scored on exactly the decision states they were trained on.

**Provenance defect (non-blocking for the overlap verdict).** For 20/20 anchors, the view path recorded in `panel-q1v1.receipt.json` (`/home/sat/mcrl-v025-datepool-ws/artifacts/v025-exact-source-20260910-BUILD_NOT_CLAIM/views/world-1/…`) now holds different bytes from the recorded SHA-256. The file at that path was replaced after panel-q1v1 was built. The recorded bytes still exist as the coalgen corpus files, where the SHA-256 matches (for example `ea0e2f59…` for anchor 000). The replacement differs only in the surrogate comparison record above. The other four panels have no such drift (0/20 each).

### 1.4 Verdict for this job and for Z-VIEW-SCORING

- **Overlap: 20 of 20 panel anchors, for every run.** Restricting to non-overlapping panel anchors is impossible: there are none. The only non-panel anchors (global 020 and 021) are training anchors.
- **Z-VIEW-SCORING-2026-09-10.md.** Its three runs trained on all 20 panel anchors (20/20 each; for Q1 v1 and z, the panels were built from the runs' own training files). Every marginal in that report is IN-SAMPLE.
- **What "in-sample" means here (inferred).** The heads were fitted to boundary-0 decision-objective labels at exactly these states. The scored quantity is 48-boundary realised pooled EE, which is not a training target. The overlap therefore does not make a score tautological. It does mean no number on these panels measures generalisation to unseen anchors, so any marginal is expected to be optimistic relative to held-out anchors by an unknown amount.
- **To get an out-of-sample development score**, a panel must be built on development anchors outside 000–021. The EXACTGEN2 exact-source corpus admits 93 prefix anchors (per `EXACT-CORPUS-TRAINING-2026-09-10.md`, Part 1; relayed). A panel on anchors 022–092 would not overlap the 22-anchor training set. The separate `exact93` run now training in `/home/sat/mcrl-v025-exact93-ws` would overlap such a panel; I did not inspect that run.

## 2. A premise the task relies on is contradicted: the Z-VIEW runs were not trained on surrogate labels (verified by running code)

The task (and Z-VIEW-SCORING §8) frames the new exact run as "exact labels" against "surrogate-label" Z-VIEW runs. The bytes say otherwise.

- **C1/C2 source labels are the same in all six training corpora.** Every one of the 21,532 source rows matches exact22's corpus, keyed by (anchor_id, user_id, action_index), with 0 mismatches in `c1_label_bits_hex`, `c1_label_normalized_hex`, `c1_phi_difference_hex`, `c2_label_bits_hex` and `c2_label_normalized_hex`. The six corpora are exact22, Q1 v3, the v3 control, and Z-VIEW Q1 v1, Q1 v2 and z (`out/label-identity.json`).
- **C3 coalition labels are the same too.** All 4,552 coalition rows match in file order and as per-file multisets, with 0 differing rows across `c1_normalized_hex`, `psi_normalized_hex`, `objective_delta_normalized_hex`, the three `physical_*` fields, `decomposition_weight_hex`, `credit_split`, `original_changed_users` and `capped_decomposition`. For Z-VIEW Q1 v1 against exact22, the 22 coalition files are byte-identical (`out/coalition-label-identity.json`).
- **Both runners read those same fields** (verified by reading code).
  - `run_stagec_training.py` (`4885570b…`, used by all three Z-VIEW runs) and `run_stagec_training_v2.py` (`47313ed0…`) both strip the `exact_source_view` extension (`base = {key: value … if key != "exact_source_view"}`) and read the base row fields.
  - `diff` shows v2 differs from v1 only in the 4,000-update budget and the step-decay schedule.
  - Identical input rows plus identical reading code give identical training targets.
- **Where the "surrogate" disagreement figures come from.** The figures Z-VIEW §8 quotes (C1 51.68%, C2 55.27%, C3 81.82%) compare the exact labels against the sealed provider-primitive fallback. No corpus used by these six runs carries that fallback as its training label. The surrogate-label finding in memory (`176,223` pilot rows via `PILOT_PRIMITIVE_SOURCE_FALLBACK`) concerns a different corpus.

**Consequence for Step 3.2 (derived).** On the anchors shared with panel-q1v1, exact22 differs from Z-VIEW Q1 v1 only in two ways: the training schedule, and the unread surrogate comparison record. The training rows, labels, feature schema (`6a584896…`) and panel (`dc5df10b…`) are the same. The schedule change is also larger than "longer training":

- The legacy constant schedule trains C1 at 0.01 and C2/C3 at 0.001 (launch-receipt `head_literals`) for 500 updates.
- v2's `_set_learning_rate` sets **one** rate for all three heads: 1e-3, then ×0.1 after 2,000 and again after 3,000, for 4,000 updates.
- C1 therefore starts 10× slower than in the Z-VIEW runs.

So an exact22-vs-Z-VIEW-Q1-v1 contrast, once available, is a **schedule contrast on identical labels**, not an exact-vs-surrogate label contrast. The "C1 and C2 compete" pattern (Q1 v1 → v2 flipped C2 from +6.13 Mbit/J, 16/16, to −1.15 Mbit/J, 15/16 negative, while C1 went to +12.69 Mbit/J, 16/16) was **already observed on the same labels**. It cannot be a surrogate-label artefact. Whether it persists under the converged schedule is the open question.

For that question, the nearest converged-schedule analogue of Q1 v2 is `q1v3_control`: Q1 v2's 15 fields plus a constant-zero 16th coordinate (per `SCORING-PANEL-V3-2026-09-10.md`; relayed). The comparison is exact22 (v1) against q1v3_control (v2 plus a zero coordinate). It is cross-panel, so only within-panel marginals can be paired by seed, not EE levels.

## 3. Step 2 — scoring: NOT RUN (all runs pending)

### 3.1 Panel pairing by schema digest (verified by running code; never by width)

| run | launch-receipt Q1 / Q2 SHA-256 | matching panel receipt `encoder_binding` | panel SHA-256 | widths C1/C2/C3 |
|---|---|---|---|---|
| exact22 | `c002ea88…` / `a891dd98…` | panel-q1v1 | `dc5df10b17250f298ab7bbaa2a099c895204a83f3b2f8d2c93ef73cc94e50134` | 16/22/240 |
| q1v3 | `3850d23f…` / `a891dd98…` | panel-q1v3 | `90cf0181a997a12202912c59dc294ae14567eed2d7e654e464e1de0eb9319f94` | 16/22/240 |
| q1v3_control | `ee6baea9…` / `a891dd98…` | **panel-q1v3-control** (its own panel) | `bd5a967b9e013bc74dd52c321ffed06835c2361ad28fd4c370b1bb0d4434e8c8` | 16/22/240 |

Each run matched exactly one panel. All three runs have width 16/22/240, which is the hazard the task names: width alone would have matched q1v3 and q1v3_control to panel-q1v1. `SCORING-PANEL-V3-2026-09-10.md` states that the control needs its own panel, because the scorer sees the different last Q1 coordinate in C1 and in pooled C3 member coordinates 16, 32, 54 and 70. `panel-q1v3-control` exists and passed an unmodified-scorer real-checkpoint exit 0 (relayed from that report). I tested the gate below against both combinations: it refuses exact22 against panel-q1v3 and q1v3_control against panel-q1v3 (`DIGEST_MATCH False`).

### 3.2 Ready-to-run, gated scorer invocation (verified by running code)

`scripts/score_run.sh` (`97c518da…`) calls the unmodified scorer `/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py` (SHA-256 `8a83bc9865fdbf665fe3815197059fc68c11efd73c319d96bcc412b5a8c5ed9d`, checked at run time). Before scoring, it refuses unless all of the following hold:

- `training-result.json` exists;
- the launch-receipt Q1/Q2 digests equal the panel receipt's `encoder_binding`;
- the panel SHA-256 matches;
- all 16 launch-receipt seeds have a checkpoint at the requested epoch;
- every sidecar verifies.

Run now, it exited **10** (`GATE_FAIL run incomplete: no training-result.json`) for all three runs, and nothing was scored. Logs: `logs/gate-*-epoch-004000.log`.

`scripts/analyse.py` (`870678d6…`) does the Step 2 and 3 arithmetic:

- pooled EE = Σbits/Σjoules across seeds;
- served counts;
- `FULL − X` marginals, with the relative denominator equal to comparator X's pooled EE;
- per-seed range and sign counts;
- seed-paired differences of marginals, plus arm levels when both runs share a panel.

It does not read F8 (certified-fixed-point and anytime axes). As a validation, I ran it on the existing Z-VIEW scorer outputs and it reproduced every Z-VIEW-SCORING §3–§5 figure exactly: all 15 arm pooled EEs, all 12 marginals, sign counts and the paired z − Q1 v2 table (`out/validate-zscoring-reproduction.json`, `a1a763f2…`). No new EE was computed.

### 3.3 Admissible checkpoint

Neither training job has written its report yet, so neither has stated a first admissible checkpoint under the stopping rule. It is **PENDING** for all three runs. When the reports appear, score at 4,000 and at the stated checkpoint.

## 4. Step 3 — PENDING

When the runs complete, these are the planned comparisons, all IN-SAMPLE:

1. **v3 against v3_control, paired by seed.** Each run is scored on its own panel. These are equal-width, capacity-controlled panels with identical outcomes and reference IDs (per PANELV3; relayed). Compare the four marginals seed by seed and count how many seeds have v3 larger.
2. **exact22 against Z-VIEW Q1 v1.** Same panel `dc5df10b…` and the same 16 seeds (verified in launch receipts), so both arm levels and marginals pair by seed. Per §2, this is a schedule contrast on identical labels.
3. **The C1/C2 competition check.** Compare the sign pattern of `FULL − DROP_C1` and `FULL − DROP_C2` in exact22 (v1) and in q1v3_control (v2 plus a zero coordinate), then set it against Z-VIEW's v1 → v2 flip. Only the marginals are cross-panel paired.

## 5. What must not be concluded, and caveats carried

- **No route is stated dead or alive.** Nothing was scored. When scores exist, they will be development measurements on in-sample anchors.
- **The certified_fixed_point and anytime_incumbent axes are contaminated on every panel** (panel-q1v3 reports 40/40 contaminated reference objects). This job does not use them, and `analyse.py` does not read them. Per-arm pooled EE does not depend on them.
- **Objective caveat.** The deployed decision objective `F = B − η_ref·E − Φ` does not track pooled EE. `F` rejects an EE improvement worth +7.852367 Mbit/J from `RSS_MAX` (`/home/sat/mcrl-v025-coord-ws/COORDINATION-VALUE-2026-09-10.md`, line 1; I read that line but did not re-derive it). That report calls the value a sampled lower bound on the objective's cost. Every route target (C1/C2/C3 labels) is defined relative to `F`, so a route marginal measured in pooled EE is scoring heads against a metric they were not trained to move. A separate job is testing the objective.
- **Wording for `FULL − ALL_NEUTRAL_CONTROL`.** It means "informative vs neutral source training", never "vs no information". Neutral-trained heads output nonzero scores. At epoch 500, ALL_NEUTRAL differed from the zero-score knockout at 20/20 anchors in every Z-VIEW checkpoint (relayed from Z-VIEW §3).

## 6. Four fields for the numbers in this report

- **Overlap counts, row counts and label mismatch counts.**
  - Reference: the named training corpus against the named panel or against exact22's corpus.
  - Information class: serialized corpus and panel bytes.
  - Estimand: counts of equal anchor identities, equal decision-state rows, or equal label fields.
  - Numerator: the matched count shown, over the stated total.
  - No epoch, seed or checkpoint is involved.
- **The only EE numbers quoted** are the Z-VIEW epoch-500 figures in §2 (+6.13, −1.15 and +12.69 Mbit/J).
  - Reference: same-checkpoint dropped arm.
  - Information class: panel causal decision-instant state; outcomes are realised 48-boundary full-buffer; 16 seeds × 20 anchors, all IN-SAMPLE per §1.
  - Estimand: pooled Σbits/Σjoules.
  - Numerator: saturated full-buffer decoded forward-downlink bits.
  - These were re-computed by `analyse.py` from Z-VIEW's scorer outputs and matched that report exactly.
- **The +7.852367 Mbit/J objective caveat** is relayed. Its reference is `RSS_MAX` on that report's 12 anchors.

## 7. Evidence classification

- **Verified by running code:**
  - run completion status and seed counts;
  - the exact run's interruption and resume (process table, chain log, checkpoint mtimes);
  - the six training anchor lists, the five panel anchor lists and the 20/20 overlap for every pair;
  - 19,617/19,617 identical decision-state rows;
  - the panel-q1v1 recorded-path drift (20/20);
  - identical C1/C2 labels (21,532 rows) and C3 labels (4,552 rows) across all six corpora;
  - panel and scorer SHA-256 values and the schema-digest pairing;
  - gate refusals, including both wrong-panel refusals;
  - exact reproduction of the Z-VIEW tables.
- **Verified by reading code or artefacts:**
  - both runners strip the extension and read the base label fields, and v1 → v2 adds only budget and step decay;
  - the step decay applies one rate to all three heads, against legacy C1 at 0.01;
  - the +7.852367 line.
- **Derived:** the completion ETAs, and that exact22 vs Z-VIEW Q1 v1 is a schedule contrast on identical labels.
- **Inferred:** what "in-sample" does and does not imply here (§1.4), and that an anchor 022–092 panel would give an out-of-sample development score.
- **Relayed, not re-verified:**
  - PANELV3's statement that the control needs its own panel, and its control-panel exit-0 acceptance;
  - the 93-anchor EXACTGEN2 admission count;
  - Z-VIEW's knockout finding.

## 8. Resources and scope

- Every Python invocation used `/home/sat/mcrl-leo-handover/.venv/bin/python` at `nice -n 16`, with `OMP`, `OPENBLAS`, `MKL`, `NUMEXPR`, `VECLIB` and `BLIS` threads set to 1. Only one of my Python processes ran at a time. The maximum peak RSS was **723,329,024 B** (`leakage_check.py`), under the 5 GB limit.
- `rg` is not installed on `sat`, so no `rg` was used.
- I wrote only inside `/home/sat/mcrl-v025-convscore-ws` (`git init -q` done; nothing committed).

## 9. Follow-up (one command per run, once `training-result.json` exists)

```bash
cd /home/sat/mcrl-v025-convscore-ws
bash scripts/score_run.sh exact22 /home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-step-decay-16seed-4000-20260910 /home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v1.json /home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v1.receipt.json dc5df10b17250f298ab7bbaa2a099c895204a83f3b2f8d2c93ef73cc94e50134 4000 > logs/score-exact22-4000.log 2>&1 &
bash scripts/score_run.sh q1v3 /home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-step-decay-16seed-4000-20260910 /home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3.json /home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3.receipt.json 90cf0181a997a12202912c59dc294ae14567eed2d7e654e464e1de0eb9319f94 4000 > logs/score-q1v3-4000.log 2>&1 &
bash scripts/score_run.sh q1v3_control /home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-control-step-decay-16seed-4000-20260910 /home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3-control.json /home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3-control.receipt.json bd5a967b9e013bc74dd52c321ffed06835c2361ad28fd4c370b1bb0d4434e8c8 4000 > logs/score-q1v3_control-4000.log 2>&1 &
# then: analyse.py with runs {exact22, q1v3, q1v3_control, zq1v1 (Z-VIEW score-q1v1)} and
# pairs [[q1v3, q1v3_control], [exact22, zq1v1], [exact22, q1v3_control]]
```

That is three Python processes, which meets the cap only if no other job of this workspace is running. Repeat at the admissible epoch once the training reports state it.
