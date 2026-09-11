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

