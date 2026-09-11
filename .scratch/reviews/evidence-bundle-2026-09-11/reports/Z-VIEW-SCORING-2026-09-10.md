**Pooled across 16 seeds × 20 development anchors at epoch 500, each run on its own panel, relative to the dropped arm's pooled EE: the z view's route marginals are FULL−DROP_C1 +1.353181 Mbit/J (+3.4513%, 14/16 seeds positive), FULL−DROP_C2 +0.762113 Mbit/J (+1.9149%, 13/16 positive) and FULL−DROP_C3 −2.251681 Mbit/J (−5.2593%, 15/16 negative); Q1-v2's are +12.691200 Mbit/J (+42.9183%, 16/16 positive), −1.148719 Mbit/J (−2.6462%, 15/16 negative) and −1.200528 Mbit/J (−2.7622%, 14/16 negative).**

# Z-VIEW-SCORING — all 48 epoch-500 checkpoints, five arms, three runs — 2026-09-10

`DEVELOPMENT_SCORING_NOT_A_CLAIM`. Development anchors only (global prefix 000–019, world `V025_PROBE/world/1`, date 2026-01-07). I read none of the evaluation-only claim dates. I changed no sealed artefact, wrote nothing into another workspace or training-output directory, and ran the scorer unmodified. The panels carry the label "development, not claim-grade", and `EVALPATH-2026-09-10` leaves evaluator-path authority UNDETERMINED.

## 0. How to read every number here

Unless a row says otherwise, every EE number carries these four fields:

| field | value |
|---|---|
| **reference** | Arm rows have no reference; they are levels. For a marginal `FULL − X`, the reference is the **same-checkpoint** arm X. DROP_Cn is the same five-arm checkpoint's head set trained with route Cn on exact-zero (neutral) targets and the other routes informed; it is *not* the FULL heads with one term deleted. The scorer labels these rows `route_source_substitution_contrast`. |
| **information class** | From the panel: causal decision-instant exact C1/C2 state and physical C3 state. Outcomes come from a realised 48-boundary full-buffer evaluation. The heads were trained on **surrogate labels** (§8). |
| **estimand** | Pooled EE = Σ decoded bits / Σ modelled partial-payload DC joules. **Per seed**, the sum runs over 20 anchors × 48 realised boundaries of that seed's selections; this is what the scorer emits. **Pooled across seeds**, it runs over 16 seeds × 20 anchors (Σ of the scorer's per-seed bits / Σ of its per-seed joules), so seeds are weighted by joules. The arithmetic mean of the per-seed values is given next to it. |
| **numerator** | Sum of saturated full-buffer successfully decoded forward-downlink information bits. The rate target is a power-control setpoint. No demand cap. |
| **relative marginal denominator** | **The comparator (dropped) arm's pooled EE**: `(EE_FULL − EE_X) / EE_X`. This matches the scorer's `relative_difference`. It is the incremental change **relative to the ablated arm**. It is *not* a fraction of FULL's EE, of any headroom, or of any ceiling. |

Units: Mbit/J = 10⁶ bit/J. Every checkpoint is at **epoch 500** (`completed_source_epochs = 500`). Each of the three runs contains the same 16 learner seeds (listed in §5).

## 1. What was run

### Verified by running code

- Scorer: `/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py`, SHA-256 `8a83bc9865fdbf665fe3815197059fc68c11efd73c319d96bcc412b5a8c5ed9d`. This is the digest recorded at the PANELZ and PANELFIX acceptance runs. The scorer was run unmodified without `--smoke-fixture`.
- One invocation per run. Each received all 16 `*epoch-000500.json` checkpoints of that run and only that run's panel:

| run | output dir (Stage-C checkpoints) | panel | panel SHA-256 (re-hashed) | scorer exit | checkpoints | F6/F7/F8 rows | wall | peak RSS (scorer) |
|---|---|---|---|---:|---:|---|---:|---:|
| Q1 v1 | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z` | `panel-q1v1.json` | `dc5df10b17250f298ab7bbaa2a099c895204a83f3b2f8d2c93ef73cc94e50134` | **0** | 16 | 144/80/80 | 44:51 | 619,413,504 B |
| Q1 v2 | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z` | `panel-q1v2.json` | `b5a2c365a1c1936399530dd98e509a464a56d88bb9857f03d611c3fde3643638` | **0** | 16 | 144/80/80 | 43:50 | 613,728,256 B |
| z view | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z` | `panel-q1v2z.json` | `2a905423c8b9b573bef56398ad4b36ce671cc1a41bf232df07d359e81b69e203` | **0** | 16 | 144/80/80 | 49:01 | 846,012,416 B |

- Before scoring, the job script re-hashed all 48 checkpoints and compared each against its sealed `.sha256` sidecar. All 48 matched (`SIDECARS_VERIFIED_OK` in each log).
- Resources: three concurrent scorer processes, at most 3 Python processes at any time, `nice -n 16`, all six BLAS/OMP thread variables set to 1. Every peak RSS stayed under 5 GB. The maximum was 846,012,416 B. Earlier I ran a serial one-checkpoint probe (`artifacts/PROBE-z-seed1437152739566466432`, exit 0, peak 735,195,136 B, 2:39 wall) to establish timing and memory. That probe is not used in any number below. The analysis scripts peaked at 27,123,712 B.
- Outputs (workspace `/home/sat/mcrl-v025-zscoring-ws`):
  - `artifacts/score-q1v1/dual-axis-scores.json` `e60bb02dc486dbd4d357f954ba846410eeafe24e2fae451d65c8bdb8fca22d7f`
  - `artifacts/score-q1v2/dual-axis-scores.json` `c93136b733143c2d59fd79f985c0bcbdfacd247a12ba8b69e7e24f31dd8e4027`
  - `artifacts/score-q1v2z/dual-axis-scores.json` `07cce7db6d221498b2a180db0df9aeee1e73adb015427bf2beef7648dd443042`
  - The scorer also emitted `F6-ablation.csv`, `F7-training-trajectory.csv`, `F8-recovered-fraction.csv` and `report.md` in each directory.
  - Derived tables: `artifacts/analysis.json` `944dd371fb2824bbdad226090f1095fb702b43d89d0ab4a9df7c059aa3b0239d`, produced by `scripts/analyse.py` (`2ff1ace4…`), and `artifacts/per-seed-tables.md`, produced by `scripts/tables.py` (`a582c856…`). Logs are in `logs/`.

## 2. Each run matched to its own panel — by schema digest, not by width

### Verified by reading receipts

Widths alone do not identify a schema. Q1 v1 and Q1 v2 have the **same** C2 width (22) and the **same** Q2 schema digest, so C2 width cannot tell them apart. The match below uses the Q1/Q2 schema SHA-256 that each training launch receipt declares (`feature_schema`), compared with the `encoder_binding` in each panel's construction receipt:

| run | launch-receipt feature schema | Q1 schema SHA-256 / width | Q2 schema SHA-256 / width | panel receipt `encoder_binding` | C3 full / member width (receipt = checkpoint) |
|---|---|---|---|---|---|
| Q1 v1 | `V025_CONTRACT_V1` | `c002ea88…` / 16 | `a891dd98…` / 22 | `panel-q1v1`: q1 `c002ea88…`/16, q2 `a891dd98…`/22 | 240 / 38 |
| Q1 v2 | `CORPUS_Q1_V2_READER_ADAPTER` | `66ed4a3f…` / 15 | `a891dd98…` / 22 | `panel-q1v2`: q1 `66ed4a3f…`/15, q2 `a891dd98…`/22 | 236 / 36 |
| z view | `MCRL_V025_STAGEC_Q1_V2_Q2_V1_RAW_PLUS_LIVE_USER_Z` | `bd33e460…` / 30 | `c2dab920…` / 44 | `panel-q1v2z`: q1 `bd33e460…`/30, q2 `c2dab920…`/44 | 296 / 66 |

The digests match pairwise, and each scorer invocation then passed its own width checks (exit 0). All three launch receipts name the same runner (`run_stagec_training.py`, `4885570b…`), `epochs = 500` and the same 16-seed list.

## 3. Per run, per arm — pooled across all 16 seeds (epoch 500)

### Verified by running code (the scorer's per-seed pooled sums), aggregated by derived arithmetic

"Served" means service availability = `service_available / service_opportunities`, where opportunities = 16 seeds × 20 anchors × 100 users = 32,000. Rate-target attainment and handover rate use the same pooling. Deadline-miss rate is **UNAVAILABLE** in every row: the panels carry `decisions = 0`, a structural "not recorded" pair, and the scorer emits `None`.

**Q1 v1** (panel `panel-q1v1`)

| arm | pooled EE (Mbit/J) | per-seed EE range | per-seed mean | pooled bits | pooled joules | served | rate-target attainment | handover rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FULL | 32.961077 | [30.150081, 34.762172] | 33.007356 | 4.296257e13 | 1,303,433.54 | 31,546/32,000 = 0.985812 | 0.247312 | 0.970187 |
| DROP_C1 | 30.644630 | [28.381871, 33.087825] | 30.672054 | 4.264623e13 | 1,391,637.81 | 31,503 = 0.984469 | 0.240469 | 0.975812 |
| DROP_C2 | 26.835671 | [25.009104, 28.312081] | 26.858678 | 4.175738e13 | 1,556,039.99 | 31,339 = 0.979344 | 0.232625 | 0.945375 |
| DROP_C3 | 43.003083 | [39.886875, 44.776216] | 43.028407 | 4.405374e13 | 1,024,432.03 | 31,652 = 0.989125 | 0.275938 | 0.919344 |
| ALL_NEUTRAL_CONTROL | 22.242007 | [17.868076, 28.626090] | 22.500424 | 3.834169e13 | 1,723,841.09 | 29,420 = 0.919375 | 0.205937 | 0.766437 |

**Q1 v2** (panel `panel-q1v2`)

| arm | pooled EE (Mbit/J) | per-seed EE range | per-seed mean | pooled bits | pooled joules | served | rate-target attainment | handover rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FULL | 42.261789 | [39.869116, 45.689745] | 42.321514 | 4.438982e13 | 1,050,353.63 | 31,962 = 0.998812 | 0.272031 | 0.992156 |
| DROP_C1 | 29.570589 | [26.911866, 30.927627] | 29.605830 | 4.250895e13 | 1,437,541.53 | 31,491 = 0.984094 | 0.237031 | 0.969688 |
| DROP_C2 | 43.410508 | [39.038560, 47.484623] | 43.509424 | 4.447696e13 | 1,024,566.58 | 31,965 = 0.998906 | 0.274656 | 0.990094 |
| DROP_C3 | 43.462317 | [43.207932, 44.392214] | 43.463604 | 4.434031e13 | 1,020,201.32 | 31,828 = 0.994625 | 0.274562 | 0.946719 |
| ALL_NEUTRAL_CONTROL | 20.293188 | [12.409350, 31.169919] | 21.022110 | 3.740556e13 | 1,843,256.98 | 29,114 = 0.909813 | 0.194062 | 0.699875 |

**z view** (panel `panel-q1v2z`)

| arm | pooled EE (Mbit/J) | per-seed EE range | per-seed mean | pooled bits | pooled joules | served | rate-target attainment | handover rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FULL | 40.561495 | [38.627686, 43.048629] | 40.593901 | 4.400772e13 | 1,084,962.94 | 31,850 = 0.995313 | 0.265531 | 0.975656 |
| DROP_C1 | 39.208314 | [35.020405, 41.340285] | 39.257405 | 4.382190e13 | 1,117,668.56 | 31,724 = 0.991375 | 0.265813 | 0.946750 |
| DROP_C2 | 39.799382 | [37.707368, 44.780907] | 39.853128 | 4.397898e13 | 1,105,016.62 | 31,897 = 0.996781 | 0.263313 | 0.977094 |
| DROP_C3 | 42.813175 | [42.278974, 43.772088] | 42.817440 | 4.416742e13 | 1,031,631.57 | 31,751 = 0.992219 | 0.267906 | 0.916844 |
| ALL_NEUTRAL_CONTROL | 21.328671 | [17.059472, 33.690571] | 21.842045 | 3.812435e13 | 1,787,469.38 | 29,422 = 0.919438 | 0.203187 | 0.705219 |

**Knockout check** (the scorer runs it before the primary contrast). In all three runs, at every one of the 48 checkpoints, ALL_NEUTRAL_CONTROL's selection **differs** from the FULL-checkpoint all-terms-removed knockout at **20/20 anchors**. Scorer label: `neutral_source_substitution_contrast_decision_separated_from_knockout`. The knockout picks the catalogue-order-0 base at every anchor. Its pooled EE is 11.495472 Mbit/J in all three runs and at every seed. After 500 updates, the neutral-trained heads therefore do not output zero: ALL_NEUTRAL_CONTROL is an unconverged zero-target selector, not a no-information selector. Its per-seed EE ranges are the widest of any arm (up to [12.41, 31.17] in Q1 v2). Every `FULL − ALL_NEUTRAL_CONTROL` row below is a source-substitution contrast, not a knockout.

## 4. Route marginals per run

### Derived (arithmetic on verified pooled sums); the sign counts are counts of verified per-seed values

Reference = same-checkpoint named arm. **Relative denominator = that comparator arm's pooled EE.** A marginal is marked **RESULT** only when all 16 seeds share its sign. Any marginal whose sign flips across seeds is **NOT A RESULT**.

| run | marginal | pooled Δ EE (Mbit/J) | relative (÷ comparator) | per-seed mean Δ | per-seed range Δ | per-seed relative range | seeds + / − / 0 | status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Q1 v1 | FULL − DROP_C1 | +2.316447 | +7.5591% | +2.335302 | [−0.564748, +6.380301] | [−1.8387%, +22.4802%] | 15 / 1 / 0 | **NOT A RESULT — sign flips** |
| Q1 v1 | FULL − DROP_C2 | +6.125406 | +22.8256% | +6.148678 | [+3.080310, +9.753069] | [+11.3792%, +38.9981%] | 16 / 0 / 0 | RESULT (at this budget) |
| Q1 v1 | FULL − DROP_C3 | −10.042006 | −23.3518% | −10.021051 | [−13.369126, −7.637382] | [−30.2338%, −18.7130%] | 0 / 16 / 0 | RESULT (at this budget) |
| Q1 v1 | FULL − ALL_NEUTRAL | +10.719070 | +48.1929% | +10.506932 | [+2.684617, +15.128593] | [+9.5316%, +84.6683%] | 16 / 0 / 0 | RESULT (source substitution, §3) |
| Q1 v2 | FULL − DROP_C1 | +12.691200 | +42.9183% | +12.715684 | [+8.941489, +16.711107] | [+28.9110%, +60.6909%] | 16 / 0 / 0 | RESULT (at this budget) |
| Q1 v2 | FULL − DROP_C2 | −1.148719 | −2.6462% | −1.187910 | [−2.820640, +1.292329] | [−6.5880%, +3.3104%] | 1 / 15 / 0 | **NOT A RESULT — sign flips** |
| Q1 v2 | FULL − DROP_C3 | −1.200528 | −2.7622% | −1.142091 | [−4.183894, +2.261903] | [−9.4248%, +5.2084%] | 2 / 14 / 0 | **NOT A RESULT — sign flips** |
| Q1 v2 | FULL − ALL_NEUTRAL | +21.968602 | +108.2560% | +21.299404 | [+8.823944, +28.291420] | [+28.3092%, +221.2829%] | 16 / 0 / 0 | RESULT (source substitution, §3) |
| z view | FULL − DROP_C1 | +1.353181 | +3.4513% | +1.336496 | [−1.237875, +3.939059] | [−3.0396%, +10.3005%] | 14 / 2 / 0 | **NOT A RESULT — sign flips** |
| z view | FULL − DROP_C2 | +0.762113 | +1.9149% | +0.740773 | [−2.472878, +2.961108] | [−6.0167%, +7.7294%] | 13 / 3 / 0 | **NOT A RESULT — sign flips** |
| z view | FULL − DROP_C3 | −2.251681 | −5.2593% | −2.223539 | [−3.870110, +0.717352] | [−9.0713%, +1.6946%] | 1 / 15 / 0 | **NOT A RESULT — sign flips** |
| z view | FULL − ALL_NEUTRAL | +19.232824 | +90.1736% | +18.751856 | [+7.611899, +24.211254] | [+22.5936%, +141.9226%] | 16 / 0 / 0 | RESULT (source substitution, §3) |

These marginals have different served counts behind them. In every run, ALL_NEUTRAL_CONTROL serves 0.910–0.919 of user-slots, while FULL serves 0.986–0.999. Most of the EE movement is in the joules denominator rather than in bits. For example, in Q1 v1, DROP_C3 uses 1.02×10⁶ J against FULL's 1.30×10⁶ J, while their bits differ by 2.5%.

## 5. The comparison this job exists for: z-view marginals next to the non-z runs'

### Derived: same-seed paired contrasts of within-panel marginals

Each run's marginal is computed only on that run's own panel. What is paired below is the **marginal**, seed by seed. The three runs have identical 16-seed lists (verified), an identical budget (500 updates each, verified in the launch receipts), and none of them is converged (§8). **Pairing between runs is valid. No statement about converged behaviour is.** I do not compare EE *levels* across panels. The subtraction below is a difference of two within-panel differences.

`Δ(z − base)` is the z run's per-seed marginal minus the base run's marginal for the same seed:

| marginal | vs | mean Δ over seeds (Mbit/J) | per-seed range | seeds z larger / smaller | difference of pooled marginals | reading |
|---|---|---:|---:|---:|---:|---|
| FULL − DROP_C1 | Q1 v2 | **−11.379188** | [−17.570920, −7.484139] | **0 / 16** | −11.338019 | **z differs: its C1 marginal is smaller at every seed** |
| FULL − DROP_C2 | Q1 v2 | +1.928683 | [−1.486309, +4.689955] | 12 / 4 | +1.910832 | indistinguishable (sign flips) |
| FULL − DROP_C3 | Q1 v2 | −1.081448 | [−4.567802, +2.987053] | 7 / 9 | −1.051153 | indistinguishable (sign flips) |
| FULL − ALL_NEUTRAL | Q1 v2 | −2.547548 | [−11.304260, +14.311046] | 4 / 12 | −2.735778 | indistinguishable (sign flips) |
| FULL − DROP_C1 | Q1 v1 | −0.998805 | [−7.618176, +3.851030] | 5 / 11 | −0.963266 | indistinguishable (sign flips) |
| FULL − DROP_C2 | Q1 v1 | −5.407905 | [−10.398465, −1.636148] | 0 / 16 | −5.363293 | z smaller at every seed (confounded, see below) |
| FULL − DROP_C3 | Q1 v1 | +7.797512 | [+4.637265, +11.351621] | 16 / 0 | +7.790325 | z larger (less negative) at every seed (confounded) |
| FULL − ALL_NEUTRAL | Q1 v1 | +8.244924 | [−2.559418, +20.489044] | 15 / 1 | +8.513754 | indistinguishable (sign flips) |

Q1 v2 is the like-for-like baseline. The z view is Q1-v2 raw features plus live-user population-z features appended to C1 and C2, and to the C3 member blocks. Against Q1 v1, z changes two things at once: the Q1 schema (v1 to v2) and the z block. The z − Q1 v1 rows therefore cannot be attributed to the z view.

**What the z view changes, at equal and unconverged budget:**

- **C1: yes.** Paired against Q1 v2, the z view shrinks FULL − DROP_C1 at all 16 seeds, from a sign-consistent +12.691200 Mbit/J (16/16 positive) to +1.353181 Mbit/J, which flips sign (14/16). The z view turns C1 from a sign-consistent marginal into a non-result on its panel.
- **C2: no distinguishable change.** Both within-run marginals flip sign (Q1 v2: 15/16 negative; z: 13/16 positive), and the paired difference flips sign too (12/4).
- **C3: no distinguishable change.** Both are negative in the pooled sense, and both flip sign across seeds (Q1 v2: 14/16 negative; z: 15/16 negative). The paired difference is 7/9.
- **FULL − ALL_NEUTRAL: no distinguishable change** (paired 4/12).

### Inferred

- Looked at arm by arm, the C1 change goes mostly through DROP_C1 rather than FULL. On its own panel, z's DROP_C1 sits 1.353 Mbit/J below its FULL, while Q1 v2's DROP_C1 sits 12.691 Mbit/J below its FULL. One candidate reading: when C1 is neutralised, the z-augmented C2 inputs and C3 member blocks carry part of the per-user signal that C1 otherwise supplies. I did not test this; no head-attribution experiment was run. PANELFIX and PANELZ report that the catalogue and outcomes are identical field for field across all three panels. I relayed that and did not re-verify it here. It is consistent with the certified, anytime and knockout pooled EE being bit-identical across my three runs. It is still not a licence to read EE levels across panels as a result.

## 6. Per-seed values (every seed, epoch 500) and F8 rows

Every cell is pooled EE in Mbit/J over 20 anchors for that seed. Reference, information class, estimand and numerator are as in §0. Marginal columns are FULL minus the named same-checkpoint arm. The F8 tables are reproduced for completeness only; **they are contaminated (§7)**.

#### Q1 v1 — per-seed, epoch 500

All-terms-removed knockout (FULL checkpoint, every deployed score set to 0, so the catalogue-order-0 base profile wins at every anchor) pooled EE, identical across all 16 seeds: 11.495472 Mbit/J.

| learner seed | checkpoint SHA-256 (first 16) | FULL | DROP_C1 | DROP_C2 | DROP_C3 | ALL_NEUTRAL | FULL−DROP_C1 | FULL−DROP_C2 | FULL−DROP_C3 | FULL−ALL_NEUTRAL |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 389903013832883586 | `b158f58e0b7ffa24` | 30.150081 | 30.714829 | 27.069771 | 39.886875 | 22.232714 | -0.564748 | +3.080310 | -9.736794 | +7.917366 |
| 925030429265975792 | `770297232a4c381e` | 34.749447 | 30.072364 | 27.928850 | 43.210572 | 21.313045 | +4.677083 | +6.820597 | -8.461125 | +13.436402 |
| 1437152739566466432 | `689d96503f10cf0e` | 32.996668 | 30.405159 | 27.278128 | 43.026523 | 17.868076 | +2.591509 | +5.718541 | -10.029854 | +15.128593 |
| 2106858948530091040 | `54c195a49c474cdd` | 33.962111 | 30.712516 | 28.312081 | 43.815031 | 20.964360 | +3.249595 | +5.650031 | -9.852920 | +12.997751 |
| 2306713132836500212 | `5649e262457b2ff6` | 33.568183 | 30.187031 | 25.647527 | 42.555194 | 22.477880 | +3.381152 | +7.920656 | -8.987011 | +11.090303 |
| 2539879246662512149 | `dc02949e7dd758ce` | 33.175854 | 33.087825 | 27.336596 | 40.813235 | 20.817975 | +0.088029 | +5.839258 | -7.637382 | +12.357878 |
| 2914121027624601215 | `ccdf416a2245ae64` | 33.038589 | 30.681082 | 28.244665 | 44.168337 | 27.015550 | +2.357508 | +4.793924 | -11.129748 | +6.023040 |
| 2947922203589416513 | `7de1ad6187bae7b5` | 33.267675 | 30.824347 | 26.784919 | 44.539894 | 20.282128 | +2.443328 | +6.482756 | -11.272220 | +12.985547 |
| 3155344545377116990 | `c54a69b518e2aa57` | 30.850086 | 30.802499 | 26.291364 | 44.219212 | 28.165469 | +0.047587 | +4.558722 | -13.369126 | +2.684617 |
| 5166716249291843642 | `a17a9d0c96b78c21` | 32.937796 | 30.024805 | 26.960089 | 42.692112 | 22.766479 | +2.912991 | +5.977706 | -9.754317 | +10.171316 |
| 5683607794651051129 | `3fa24b7c171ca4fd` | 33.159179 | 30.189161 | 27.272081 | 42.223032 | 19.311173 | +2.970018 | +5.887098 | -9.063853 | +13.848006 |
| 6114226365011333154 | `e5202e36097bdc23` | 34.534849 | 30.834072 | 26.609262 | 43.011997 | 22.308435 | +3.700777 | +7.925588 | -8.477147 | +12.226414 |
| 6407676579069309528 | `391de301059cc046` | 33.255431 | 32.476038 | 25.991598 | 43.211826 | 23.469363 | +0.779394 | +7.263833 | -9.956395 | +9.786069 |
| 7234013715671416945 | `f48b5b3f7b1a2f77` | 34.762172 | 28.381871 | 25.009104 | 44.776216 | 28.626090 | +6.380301 | +9.753069 | -10.014044 | +6.136082 |
| 7291913070596938501 | `0a7f348e5c8de0d4` | 32.649300 | 30.820381 | 26.208730 | 43.092630 | 23.046467 | +1.828920 | +6.440571 | -10.443330 | +9.602833 |
| 9087876568043732533 | `a224c9886b854fc6` | 31.060268 | 30.538887 | 26.794079 | 43.211826 | 19.341573 | +0.521381 | +4.266189 | -12.151558 | +11.718695 |

F8 rows for Q1 v1 (pooled across seeds; **CONTAMINATED reference axes — see §7**): certified fixed point pooled EE 12.947467 Mbit/J, 10 s anytime incumbent 12.867610 Mbit/J (anytime/fixed point 0.993832).

| arm | arm / certified fixed point (pooled) | per-seed range of arm / fixed point | arm − anytime (Mbit/J, pooled) | budget status |
|---|---:|---:|---:|---|
| FULL | 2.545755 | [2.328647, 2.684863] | +20.093467 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C1 | 2.366844 | [2.192079, 2.555544] | +17.777020 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C2 | 2.072658 | [1.931583, 2.186689] | +13.968061 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C3 | 3.321351 | [3.080670, 3.458299] | +30.135473 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| ALL_NEUTRAL_CONTROL | 1.717866 | [1.380044, 2.210941] | +9.374397 | UNAVAILABLE_RUNNER_NOT_RECORDED |

#### Q1 v2 — per-seed, epoch 500

All-terms-removed knockout (FULL checkpoint, every deployed score set to 0, so the catalogue-order-0 base profile wins at every anchor) pooled EE, identical across all 16 seeds: 11.495472 Mbit/J.

| learner seed | checkpoint SHA-256 (first 16) | FULL | DROP_C1 | DROP_C2 | DROP_C3 | ALL_NEUTRAL | FULL−DROP_C1 | FULL−DROP_C2 | FULL−DROP_C3 | FULL−ALL_NEUTRAL |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 389903013832883586 | `e1a227b2ebbcce1d` | 43.051894 | 29.248818 | 45.795986 | 43.413694 | 25.459305 | +13.803076 | -2.744092 | -0.361800 | +17.592589 |
| 925030429265975792 | `7081948329b8a8fd` | 39.993863 | 29.973488 | 42.814503 | 43.207932 | 31.169919 | +10.020375 | -2.820640 | -3.214068 | +8.823944 |
| 1437152739566466432 | `db6c7fed39532f5d` | 40.330889 | 29.917186 | 39.038560 | 43.435033 | 19.139729 | +10.413703 | +1.292329 | -3.104143 | +21.191161 |
| 2106858948530091040 | `bcde11e4843c3ece` | 39.869116 | 30.927627 | 41.019249 | 43.207932 | 12.409350 | +8.941489 | -1.150132 | -3.338815 | +27.459767 |
| 2306713132836500212 | `9b5ba3a5777b1b5c` | 44.479756 | 27.768649 | 45.983946 | 43.427841 | 20.735435 | +16.711107 | -1.504190 | +1.051915 | +23.744322 |
| 2539879246662512149 | `7f7ace88a4bcdb12` | 43.051894 | 29.732473 | 43.884757 | 43.218180 | 21.590539 | +13.319420 | -0.832863 | -0.166286 | +21.461355 |
| 2914121027624601215 | `625cbf5ffdcbdcd5` | 43.051894 | 30.254336 | 43.491132 | 43.218180 | 14.760473 | +12.797558 | -0.439239 | -0.166286 | +28.291420 |
| 2947922203589416513 | `caa8ac6272d44255` | 45.689745 | 30.136893 | 47.484623 | 43.427841 | 26.891456 | +15.552852 | -1.794878 | +2.261903 | +18.798288 |
| 3155344545377116990 | `e91c22cced9015b7` | 43.244911 | 29.827483 | 44.317883 | 43.413694 | 27.598102 | +13.417428 | -1.072972 | -0.168782 | +15.646809 |
| 5166716249291843642 | `58da313a7b44e99f` | 40.330889 | 30.780845 | 41.448313 | 43.413694 | 21.414730 | +9.550044 | -1.117424 | -3.082804 | +18.916159 |
| 5683607794651051129 | `a1a51fe639958923` | 41.247436 | 30.034396 | 41.555265 | 43.598712 | 16.773967 | +11.213040 | -0.307829 | -2.351276 | +24.473468 |
| 6114226365011333154 | `e428eefee90973f7` | 43.051894 | 30.852688 | 44.038462 | 43.400304 | 20.635315 | +12.199206 | -0.986569 | -0.348410 | +22.416578 |
| 6407676579069309528 | `0ba79d7279519f8a` | 43.244911 | 28.250920 | 43.333938 | 43.413694 | 19.271877 | +14.993991 | -0.089027 | -0.168782 | +23.973034 |
| 7234013715671416945 | `2d830b72239e176c` | 43.244911 | 26.911866 | 45.337867 | 43.413694 | 18.581870 | +16.333045 | -2.092956 | -0.168782 | +24.663041 |
| 7291913070596938501 | `c4ef63d6d2810e60` | 40.208320 | 29.904650 | 40.929393 | 44.392214 | 18.679642 | +10.303670 | -0.721073 | -4.183894 | +21.528677 |
| 9087876568043732533 | `02888486c10317ca` | 43.051894 | 29.170956 | 45.676901 | 43.815031 | 21.242041 | +13.880938 | -2.625007 | -0.763137 | +21.809853 |

F8 rows for Q1 v2 (pooled across seeds; **CONTAMINATED reference axes — see §7**): certified fixed point pooled EE 12.947467 Mbit/J, 10 s anytime incumbent 12.867610 Mbit/J (anytime/fixed point 0.993832).

| arm | arm / certified fixed point (pooled) | per-seed range of arm / fixed point | arm − anytime (Mbit/J, pooled) | budget status |
|---|---:|---:|---:|---|
| FULL | 3.264097 | [3.079299, 3.528856] | +29.394179 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C1 | 2.283890 | [2.078543, 2.388701] | +16.702979 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C2 | 3.352819 | [3.015150, 3.667484] | +30.542898 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C3 | 3.356820 | [3.337173, 3.428641] | +30.594707 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| ALL_NEUTRAL_CONTROL | 1.567348 | [0.958438, 2.407414] | +7.425578 | UNAVAILABLE_RUNNER_NOT_RECORDED |

#### z view (Q1v2z) — per-seed, epoch 500

All-terms-removed knockout (FULL checkpoint, every deployed score set to 0, so the catalogue-order-0 base profile wins at every anchor) pooled EE, identical across all 16 seeds: 11.495472 Mbit/J.

| learner seed | checkpoint SHA-256 (first 16) | FULL | DROP_C1 | DROP_C2 | DROP_C3 | ALL_NEUTRAL | FULL−DROP_C1 | FULL−DROP_C2 | FULL−DROP_C3 | FULL−ALL_NEUTRAL |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 389903013832883586 | `891a1b3447810523` | 39.151530 | 38.766582 | 37.707368 | 42.278974 | 26.555173 | +0.384948 | +1.444162 | -3.127444 | +12.596357 |
| 925030429265975792 | `a536dfa2ffebc9ff` | 41.669824 | 41.340285 | 39.905975 | 43.772088 | 18.534834 | +0.329539 | +1.763849 | -2.102264 | +23.134990 |
| 1437152739566466432 | `64b150d1b9f20348` | 41.008873 | 40.991732 | 39.724920 | 42.386563 | 18.388055 | +0.017140 | +1.283953 | -1.377690 | +22.620818 |
| 2106858948530091040 | `dce0a5a37a9ed4d0` | 39.213661 | 39.360957 | 38.950461 | 42.451101 | 20.101872 | -0.147296 | +0.263201 | -3.237440 | +19.111790 |
| 2306713132836500212 | `d99bbd54695b96e3` | 39.855715 | 39.695825 | 39.350289 | 43.371602 | 20.320735 | +0.159890 | +0.505426 | -3.515887 | +19.534980 |
| 2539879246662512149 | `e1fe9d89ced75ba5` | 43.048629 | 39.109570 | 44.780907 | 42.331277 | 25.044447 | +3.939059 | -1.732278 | +0.717352 | +18.004182 |
| 2914121027624601215 | `a3ae092b4b7b6870` | 41.270726 | 39.054546 | 40.863120 | 43.371602 | 21.687199 | +2.216181 | +0.407606 | -2.100876 | +19.583528 |
| 2947922203589416513 | `015a91e76df8928d` | 41.590121 | 39.695825 | 38.695044 | 43.371602 | 23.974746 | +1.894296 | +2.895077 | -1.781481 | +17.615375 |
| 3155344545377116990 | `f75ca97aba8320a9` | 41.354097 | 39.230148 | 39.905975 | 43.371602 | 18.180436 | +2.123949 | +1.448122 | -2.017505 | +23.173661 |
| 5166716249291843642 | `44dfc23c83cfce7e` | 41.302470 | 40.370489 | 40.214414 | 43.371602 | 33.690571 | +0.931981 | +1.088057 | -2.069132 | +7.611899 |
| 5683607794651051129 | `20240bf7219c333e` | 40.866552 | 38.509134 | 39.212196 | 42.467568 | 18.026804 | +2.357418 | +1.654356 | -1.601016 | +22.839749 |
| 6114226365011333154 | `cabce6b769212eb5` | 38.627686 | 35.020405 | 41.100564 | 42.467568 | 21.812678 | +3.607281 | -2.472878 | -3.839882 | +16.815008 |
| 6407676579069309528 | `77d2661bbb5efd8e` | 38.793077 | 38.196714 | 39.888740 | 42.663187 | 25.710963 | +0.596363 | -1.095663 | -3.870110 | +13.082114 |
| 7234013715671416945 | `97c97977575c7929` | 39.486446 | 40.724321 | 38.235328 | 42.467568 | 19.775752 | -1.237875 | +1.251118 | -2.981122 | +19.710694 |
| 7291913070596938501 | `da0d25a755e0f1b3` | 41.270726 | 38.451196 | 38.309619 | 42.467568 | 17.059472 | +2.819531 | +2.961108 | -1.196842 | +24.211254 |
| 9087876568043732533 | `08043063fc49855f` | 40.992281 | 39.600746 | 40.805132 | 42.467568 | 20.608980 | +1.391535 | +0.187149 | -1.475287 | +20.383302 |

F8 rows for z view (Q1v2z) (pooled across seeds; **CONTAMINATED reference axes — see §7**): certified fixed point pooled EE 12.947467 Mbit/J, 10 s anytime incumbent 12.867610 Mbit/J (anytime/fixed point 0.993832).

| arm | arm / certified fixed point (pooled) | per-seed range of arm / fixed point | arm − anytime (Mbit/J, pooled) | budget status |
|---|---:|---:|---:|---|
| FULL | 3.132775 | [2.983416, 3.324869] | +27.693885 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C1 | 3.028261 | [2.704807, 3.192925] | +26.340704 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C2 | 3.073913 | [2.912336, 3.458662] | +26.931772 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| DROP_C3 | 3.306684 | [3.265424, 3.380745] | +29.945566 | UNAVAILABLE_RUNNER_NOT_RECORDED |
| ALL_NEUTRAL_CONTROL | 1.647324 | [1.317592, 2.602098] | +8.461061 | UNAVAILABLE_RUNNER_NOT_RECORDED |


## 7. F8 reference axes are CONTAMINATED — do not read them as sound

The scorer emits F8 (arm / certified fixed point, arm − 10 s anytime incumbent) for every checkpoint. In each of the three runs, the pooled fixed-point EE is 12.947467 Mbit/J and the pooled anytime-incumbent EE is 12.867610 Mbit/J. Every learned arm comes out at 1.57–3.36× the "fixed point" (table above). **These axes are not sound**, and I do not report any F8 fraction as a result.

### Verified by reading source artefacts

- All three panel receipts bind the same `panelceil_receipt`: `anchor_count = 12`, file SHA-256 `52400cf180cd55f4b004be785ba4ff8021e09e38eba20cec7321fbad9999cf7d`. PANELFIX states that the certified fixed point and the anytime incumbent for global anchors **000–011** came from PANELCEIL, and that 012–019 were recomputed by the producer. PANELZ reads "12 PANELCEIL plus 8 complete producer certificates". So **12 of the 20 panel anchors** carry PANELCEIL reference endpoints.
- `/home/sat/mcrl-v025-rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md` (table at lines 24–30) shows the published PANELCEIL `FIRST_IMPROVEMENT_FP` moving from **13.430252782 to 31.028111071 Mbit/J** on the clean evaluator path, with **0/12 configuration IDs retained**. `/home/sat/mcrl-v025-probe-ws/EVALPATH-2026-09-10.md` documents the mechanism: a scalar-cached `BASE` survives the later dense batch calls, because the evaluator cache is keyed only by `configuration_id`.
- The anytime incumbent comes from the same PANELCEIL traversal on the same evaluator, so it falls in the same contaminated class for those 12 anchors.

Consequence: `certified_fixed_point` and `anytime_incumbent` are contaminated for the 12 PANELCEIL-reused anchors in **all three** panels. So the pooled 12.947467 and 12.867610 Mbit/J figures, and every "arm / fixed point" and "arm − anytime" value above, are unsound. The published clean value (31.028111 Mbit/J) is on a 12-anchor set, not these 20, so it cannot stand in for the pooled fixed point here. Axis A (F6/F7, the arm levels and marginals in §3–§5) does not use these reference objects.

## 8. What must not be concluded

- **No route is dead.** These are **500 constant-rate updates**. A predeclared convergence rule found that horizon inadmissible for all three architectures: `/home/sat/mcrl-v025-c1c2-ws/LR-CONVERGENCE-SWEEP-2026-09-10.md`, line 1, "no grid learning rate is admissible by epoch 500" for C1, C2 and C3. The heads were trained on **surrogate labels**. Their argmax disagrees with the exact labels on **C1 1,137/2,200 (51.6818%), C2 1,216/2,200 (55.2727%) and C3 18/22 (81.8182%)** of anchors (`/home/sat/mcrl-v025-exacttrain-ws/EXACT-CORPUS-TRAINING-2026-09-10.md`, line 1; verified by reading). The sign-consistent negative FULL − DROP_C3 in Q1 v1 (16/16) says only this: at this budget, on these labels, the informed C3 head selects profiles with lower pooled EE than the neutral-target C3 head. It says nothing about C3 as a route.
- **No cross-panel comparison.** Each EE level belongs to its own panel. §5 pairs within-panel marginals; it does not compare levels.
- **No converged-behaviour statement.** None of the runs is converged, so no marginal here predicts converged behaviour.
- **No F8 claim.** See §7.
- **Not claim-grade.** These are development anchors, and evaluator-path authority is UNDETERMINED.

## 9. Evidence classification

- **Verified by running code:** the 48 scorer runs (exit 0, unmodified scorer, digests above). This covers every per-seed arm pooled EE, bits, joules, served / rate-target / handover counts, the knockout comparison (20/20 differing anchors at every checkpoint) and every F6/F7/F8 row. It also covers the 48 checkpoint sidecar verifications, the three panel SHA-256s, the resource receipts and the per-seed sign counts.
- **Verified by reading artefacts:** the panel-to-run schema-digest match (§2); identical seed lists, runner and `epochs = 500` across the launch receipts; PANELCEIL binding and the 13.430253 → 31.028111, 0/12 contamination (§7); the surrogate-label disagreement rates and the convergence-rule verdict (§8).
- **Derived:** pooled-across-seeds EE (Σ bits / Σ joules over the scorer's per-seed sums), marginals, relative marginals (÷ comparator arm), per-seed means and ranges, and the paired z − base differences.
- **Inferred:** the §5 reading of where the C1 change comes from, and the carry-over of contamination to the anytime incumbent.
- **Relayed, not re-verified here:** that catalogue and outcomes are identical field for field across the three panels (PANELFIX/PANELZ verifiers).

## 10. What this closes and what it leaves open

- Closes cheaply: at equal, unconverged budget, the z view's **C2 and C3 marginals are indistinguishable** from Q1 v2's (paired sign flips), and so is FULL − ALL_NEUTRAL.
- Leaves open: the z view's **C1 marginal is smaller than Q1 v2's at 16/16 seeds**. That is a real paired difference at this budget. Whether it survives convergence or exact labels is untested.
- Not done: a deliberate cross-panel mismatch run to exercise the scorer's width guard. The schema-digest match in §2 made it unnecessary for identification. Nothing was committed to the workspace git.
