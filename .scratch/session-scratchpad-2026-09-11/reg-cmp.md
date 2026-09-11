---

## 3. Comparability — which columns must match

Two numbers may be compared (subtracted, ratioed, called "consistent", ranked, or placed on one axis) only
if **all** of the following match. A mismatch on any line makes the comparison cross-condition; it must
then be labelled as such in the same sentence, or not made.

| column | must match | examples of a mismatch this project has already paid for |
|---|---|---|
| **quantity** | same quantity (EE with EE; not EE with a beam count, a win rate, a trained scalar) | 62.502712 Mbit/J vs 41.28 beams (erratum 23) |
| **physics / harness** (+ MDP modifiers) | same engine and panel; same cap / anchor / interruption treatment | V0.25 slope −425,009.885 applied to MODQN (erratum 28); capped vs uncapped MDP (CP-01) |
| **evaluation panel** | same anchors/episodes/seeds, same in-sample status; for V0.25, same boundary-0 vs full-48 scoring and same evaluator path | 12-anchor vs 93-anchor (62.502712 vs 62.5081); contaminated vs clean path (13.430253 vs 31.028111) |
| **estimand** | same estimator (ratio-of-sums vs mean-of-ratios vs per-user mean vs trained scalar) and same numerator (full-buffer vs demand-capped) | `r1_mean` +23.9 % read as EE (NO-DEMONSTRATOR "estimand defect"); demand-capped relabelling (RETRACTION-2) |
| **power accounting** | same denominator (consumed max / TDM_AIRTIME / radiated-only) | sibling radiated-only ×7.60 (EE-MAGNITUDE) |
| **host + TLE archive** | same archive hash; for the MODQN harness either both `e07f3e1e…` or both `427e6a91…` (placebo row matching) | sat CAPPENALTY vs local FEASFRONT (erratum 28:39-40) |
| **tree / flags** | same bootstrap mode, D-2 floor, D-3, penalty, z | FEASFRONT scalars (pre-D-2) vs CFSCREEN scalars (post-`c00aca3e`) |
| **policy / checkpoint** | same checkpoint class (frozen 9,000-ep vs 500-ep retrain vs training-time log at ε > 0); rule vs search winner | trained last-100 training episodes (ε≈0.01) vs greedy frozen-seed eval |
| **pairing** | a paired statistic requires cells that share episodes, not only seeds | CS-33, B0-12 |

A comparison that differs only in `n` is allowed if both sems are stated. A comparison across groups may be
shown **side by side** with the mismatch named (e.g. EE-MAGNITUDE's bridge, C1VSGAIN's "coincidence" note) —
those are listed in §4c as correctly handled.

---

## 4. Cross-condition comparisons currently made in documents

Status of the document per `.scratch/DOCUMENT-STATUS.md`: **IF** in force, **PS** partly superseded (the
cited line is in a part not withdrawn in place), **REV** external review text. None is fixed here.

### 4a. In force (IF / PS) — 30 comparisons

| # | where (file:line) | the numbers | mismatched column(s) | doc |
|---:|---|---|---|---|
| 1 | `V025-CONTROLLER-RULING-CATFISH-ATTACHES-TO-MODQN-NOT-STAGEC-2026-09-11.md:57` | `GAIN_IN_SET` 62.502712 Mbit/J "beats" learned `a0` 41.28 | **quantity** (EE vs mean active-beam count), panel (12-anchor vs 22 TRAIN), class (b0 search winner vs policy) | PS — withdrawn by reference in erratum 23, row text unchanged |
| 2 | `V025-CONTROLLER-DECLARATION-TWO-ARM-DEMO-UTILISATION-2026-09-11.md:18-20` | same 62.502712 vs 41.28, fixed as "the demonstrator held fixed across arms" | as #1 + **physics** (a V0.25-panel rule as demonstrator for the MODQN trainer; no shared action space) | PS |
| 3 | `.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md:387` (quoted by the two-arm amendment) | 62.50 vs 41.28 used to size the `J_E` risk | as #1 | PS |
| 4 | `V025-CONTROLLER-ERRATUM-23-…-2026-09-11.md:78-84` (from `catfish-surface/…:373,380`) | `MAX_NOMINAL_GAIN` r1_mean 1.107376e7 (+23.9 %), scalar +0.0013, r1/random 1.998 **vs** trained 8.938629e6, +0.8859, 1.650 | **host + archive** (local unpinned greedy eval vs sat pinned training log), **policy mode** (ε 0 vs ε≈0.01 training rollouts), episodes (stream 0–7 vs 8900–8999), **estimand** (mean-of-ratios) | IF |
| 5 | `V025-CONTROLLER-FINDING-PER-HEAD-BOOTSTRAP-2026-09-11.md:46`; `.scratch/deep-research/00-EVIDENCE-LEDGER.md:57-60` | "deployed argmax scores +0.8859 … no expressible myopic rule beats it" — +0.8859 (training log) vs rules' +0.8750 (local greedy eval) | as #4 | PS / IF (DR context) |
| 6 | `V025-CONTROLLER-ERRATUM-24-…-2026-09-11.md:39-41`; `zclose/Z-CLOSURE-…:189-192, 575` | MODQNZ −3.511 % (−3,190,295 bit/J) "the sign −425,009.885 bit/J predicts, at ~2.2×" | **physics** (V0.25 12-anchor coverage-first slope vs MODQN harness); slope also rule-specific (erratum 22) | PS — withdrawn by erratum 28 §1, sentence unamended |
| 7 | `V025-CONTROLLER-ERRATUM-26-…-2026-09-11.md:238` | CA-CPBR entropy potential "wrong sign here" because of −425,009.885 bit/J | **physics** | PS — withdrawn by erratum 28 ("unsupported"), line unamended |
| 8 | `V025-CONTROLLER-ERRATUM-28-…-2026-09-11.md:39-40` | CAPPENALTY 103,295,432.52 vs 88,894,962.36 (sat, 500-ep retrains, D-1 on, **capped** MDP) called "consistent with" FEASFRONT B1 103.47M vs learner 93.11M (local unpinned, frozen checkpoint, uncapped) | **host + archive**, **checkpoint**, MDP (cap), tree (D-1) | IF |
| 9 | `V025-CONTROLLER-ERRATUM-24-…-2026-09-11.md:61-68` | G-3 `active_beam` 7.470 (distinct **slots**) in a column set against "+3.38 active **physical** beams" (MODQNZ 72.24 → 75.62) | **quantity** (slots vs physical beams; z lowers slots while raising physical beams) | IF |
| 10 | `V025-CONTROLLER-ERRATUM-25-…-2026-09-11.md:22-24` | "the 0.2506 pp cross-arm figure SPECPROFILE gave me was exactly this number" (V0.25 blackout time-fraction spread) = MODQN 0.24 pp EE-ratio closure | **physics**, **estimand** (derived time fraction vs pp of an EE ratio) | IF |
| 11 | `V025-CONTROLLER-ERRATUM-25-…-2026-09-11.md:50` (from `catfish-surface/…:487`) | paired `GREEDY_R1R2 − GREEDY_SCALARIZED = +0.0091`, sem 0.0034, "~2.7 sem" | **pairing** — cells share seeds, not episodes after ep 0 → INVALID-AS-PAIRED | IF |
| 12 | `.scratch/b0-corrected/B0-CORRECTED-BASELINE-2026-09-11.md:135, 191-194` | paired t −0.42 / +2.96 / −2.29 for −0.96 % / +6.75 % / −4.02 % | **pairing** (as #11) | IF (smoke) |
| 13 | `V025-CONTROLLER-ERRATUM-22-…-2026-09-11.md:26-31, 44-50` | 62.502712 vs `RSS_MAX` 41.621560 vs crowded 46.110374 read as "a per-user gain assignment beats the jointly constructed profile by ~35 %" + Pareto dominance | **class** (b0 search winner vs declared rules; declared comparator is 52.042303) | PS — corrected by reference in erratum 23 §3 |
| 14 | `V025-CONTROLLER-ERRATUM-27-…-2026-09-11.md:24`; `feasible-frontier/…:1, 11-24` | `A m=12dB` fresh-env 101,467,361.95 / 0.2258 vs trained **shared-env** 93,137,893.02 / 0.2796 ("+8.9 %") while the table shows fresh-env 93,110,907.97 / 0.2799 | **evaluation construction** (shared env, arm-order affected, vs fresh env); 0.03 % | IF (disclosed in FEASFRONT §4; magnitude small) |
| 15 | `V025-CONTROLLER-RULING-THE-TRAINED-OBJECTIVE-DISAGREES-…-2026-09-11.md:26-27` | "the stream-position caveat from the previous round is gone" for the 19.8 % table | **evaluation construction** — the table ran on one shared env; only RANDOM was at positions 0–23 (B0 R.5) | PS (measurement table kept) |
| 16 | `V025-CONTROLLER-DECLARATION-CONSTRAINED-ENDPOINT-2026-09-11.md:28-31`; `PLAN-THREE-CATFISH…:69-70`; `deep-research/CONSOLIDATED-RULING-…:117-118,136` | C-H 0.6016/user-step = Sun–Zhu–Peng 2024 `H̄ = 0.004` per 0.2 s epoch × 30.08 s | **physics/system** (a different constellation and epoch) — declared as a stipulated budget | IF (declared; low severity) |
| 17 | `deep-research/CONSOLIDATED-RULING-2026-09-11.md:122-130`; `ask2.md:66-71` | `MAX_NOMINAL_GAIN` 1.420 handovers/min (**total**, MODQN) vs literature **inter-satellite** cap 1.2/min → "~18 % above" | **quantity** (total vs inter-satellite), physics | IF |
| 18 | `catfish-facts/CATFISH-MECHANISM-FACTS-2026-09-11.md:235` | MODQN r1_mean 9.64e6 (training episode) vs V0.25 η_ref 1.0943e7 bit/J as a magnitude cross-check | physics, estimand, power accounting, host | IF (labelled "corroboration") |
| 19 | `acrm-provenance/ACRM-PROVENANCE-2026-09-11.md:392-393`; erratum 26:69-70 | ACRM margin 1.15–1.21× (max ~6×) of the catfish's own reward, presented as "in this project's environment" | **physics** (sibling ABL9K, family_b, radiated-only r1) | IF |
| 20 | `reviews/REVIEW-SYNTHESIS-2026-09-11.md:51-53` | "the baseline's load-balance objective (r3) works against EE in this physics" from V0.25 CROWDCOST | **physics** | PS |
| 21 | `deep-research/00-EVIDENCE-LEDGER.md:87-88`; `design-state/DESIGN-STATE-2026-09-10.md:39` | "PA ~94.8 % of consumption" stated for the MODQN harness | **physics / operating point** (94.8 % is the V0.25 crowded endpoint; V0.25 family 90.8–94.9 %; MODQN measured 94.28–94.35 %, BP-07) | IF (DR context) / PS |
| 22 | `deep-research/00-EVIDENCE-LEDGER.md:76-80` | "Spreading is EE-negative, the opposite sign to what r3 rewards" (MODQN) | sign asserted, not measured on the uncapped MODQN MDP (erratum 28: net sign not measured; CAPPENALTY measured a capped variant) | IF (DR context) |
| 23 | `V025-CONTROLLER-RULING-C1VSGAIN-KILL-ALL-2026-09-11.md` (`GAIN_IN_SET` 50.3435) vs `RULING-CATFISH-ATTACHES…:57,67` (`GAIN_IN_SET` 62.502712) | one name for two objects | **object/panel** (93-anchor per-anchor b0 pick of three declared rules vs 12-anchor search winner) | IF / PS |
| 24 | `V025-CONTROLLER-ERRATUM-23-…:25-33` vs `/home/sat/mcrl-v025-design-ws/ZSCORE-VIEW-AND-TRAINING-2026-09-10.md:17-19` | erratum: "the learner's EE on that panel was never measured … the gap did not exist in either direction"; ZSCORE-VIEW measured learned `a0` 26.829317 (q1-v1) / 29.176924 (q1-v2) / 29.948640 (z) Mbit/J on the same 12-anchor panel (in-sample, epoch 500, path unstated) | **CONFLICT about whether a number exists** | IF — flagged, not resolved |
| 25 | `V025-DECLARATION-MODQN-COMPARATOR-BINDING-2026-09-10.md:96-98` | instructs reporting `RSS_MAX` 41.621560, clean FP 31.028111, `RANDOM` 11.233999 "every time the gate is reported" | **physics** once the gate moved to the MODQN harness (these are V0.25 12-anchor numbers) | PS (prospective) |
| 26 | `V025-CONTROLLER-DESIGN-PHASE-2026-09-10.md:50` | "1.66° gives +0.899 %; 3.32° gives +8.16 %" | **pairing + width** — +8.1628 % is the strict *mispaired* value at **6.65°**; correctly paired 3.32° is +1.154601 % (CT-09) | PS |
| 27 | `concept-harvest/CONCEPT-HARVEST-2026-09-11.md:305` | "+19.8 % / +20.8 % over the learner" | two trained denominators (93,137,893.02 shared env vs 93,110,907.97 fresh env) | IF (0.03 %) |
| 28 | `concept-harvest/CONCEPT-HARVEST-2026-09-11.md:57` vs `:46-47` | H-PEN OFF 88.89 M (sat, 500-ep retrain, D-1 on) in the same local-fact panel as 93.11 M (local unpinned, frozen) | host + archive, checkpoint, tree | IF (juxtaposed, not subtracted) |
| 29 | `catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md:361-365, 547` | local RANDOM r1 5.543606e6 vs frozen run episodes 0–7 5.416029e6 ("same harness", +2.4 %); local trained scalar +0.9063 "consistent with" training log +0.8859 | **host + archive** (local unpinned vs sat pinned), ε, episodes | IF |
| 30 | `PLAN-THREE-CATFISH-ON-THREE-HEADS-2026-09-11.md:38` (amendment table) and `DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md:34`; `concept-harvest/…:305` | C1 source `A m=2dB` labelled "gain only (block 2)" | **information set** mislabelled — `A m=2dB` reads the incumbent (block 1); only `MAX_NOMINAL_GAIN` is memoryless (CFSCREEN; RECORD-CATFISH-SCREENS:24-25) | IF |

### 4b. In superseded documents or withdrawn sections (for awareness; not counted above)

`RULING-NO-DEMONSTRATOR…:23-31, 44, 48` (as #4, #11; the 2.9× handover ratio is training-log vs eval) ·
`NOTE-C1-C2-COMPETE…:6-7, 10-14, 26` (information class "surrogate" wrong per erratum 21; two different
panels) · `PREDECLARATION-C3-NEGATIVE…:25-36` (surrogate premise) · `ERRATUM-18…:31, 41, 66` (clean
`RSS_MAX` vs contaminated FP, 3.099×) · `OUTCOME-PLAN…:23-24, 40` and `DESIGN-PHASE…:82` (contaminated
PANELCEIL ceilings; +0.899 % vs +8.16 %) · `FEASIBILITY…:49, 62, 81` and `CONSOLIDATED-0950Z:37`
(demand-capped band vs full-buffer; mixed panels) · `STRATEGIC-ENERGY-IS-IN-THE-CONTROL-LAW…:9`
(28.47 → 43.71 "+53 %": search order and provisioning both changed) · `design-state:239-241` and
`thesis-deltas/DELTA-CH5…:177-182` (3.099× contaminated; TDM panel explained with the `max` model) ·
`zscore-transfer/…:386-406, 499-539` (V0.25 slope used on sibling/MODQN; three physics read as one
"collapse absent" verdict) · `/home/sat/mcrl-v025-design-ws/ZSCORE-VIEW-AND-TRAINING-2026-09-10.md:30-48`
(learned `a0` vs contaminated references, "657–787 % recovery").

### 4c. External reviews (REV) and correctly handled juxtapositions

Reviews carrying the V0.25→MODQN slope transfer or cross-panel/cross-quantity arithmetic:
`reviews/ADVERSARY-NARRATIVE-2026-09-11.md:227-234`, `reviews/agy-adversary/ADVERSARY-REVIEW.md:29`,
`reviews/agy-blind/BLIND-REVIEW.md:21, 85-86, 101, 132` (12-anchor `RSS_MAX` vs 20-anchor learned FULL;
coverage-first 46.11 vs 7.75 read as "spreading drops EE"),
`reviews/endpoint-decision/agy/ENDPOINT-REVIEW-AGY.md:112-114` (+14.6 % policy bits − 0.472 % per-event
interruption). Correctly handled (side by side, mismatch named): EE-MAGNITUDE / erratum 28 bridge 693.87
vs sibling 428–620 ("a formula comparison, not a project ranking"); C1VSGAIN 62.5081 vs 62.502712
("coincidence"); OBJECTIVE-IS-STRUCTURAL:31 (~11 vs ~41, quoted as withdrawn); PREDECLARATION-C3-NEGATIVE:
72-74 (43.21 vs 41.62 "not comparable"); erratum 17 (C3-S V0.23 "does not transfer numerically");
TRAINED-OBJECTIVE-DISAGREES addendum (V0.25 blackout arithmetic scoped as not a measurement).

### 4d. Value conflicts (same quantity, two values, neither withdrawn)

| quantity | values | sources |
|---|---|---|
| trained checkpoint pooled EE (local unpinned) | 93,137,893.02 vs 93,110,907.97 | shared-env vs fresh-env rounds (§0 trap 3) |
| V0.25 `eta_ref` | 10.943122 Mbit/J vs 19.720681 Mbit/J | ETAFIX / OBJECTIVE-IS-STRUCTURAL:10 vs `reward-history:312-313` (branch `16e3d486`) |
| V0.23 exchange rate | 124.08 Mbit/J vs 84.99 Mbit/J | OBJECTIVE-IS-STRUCTURAL:11 vs `reward-history:326-327` |
| handover interruption provenance | 62 / 142 ms "verified against TS 38.133 A.14.2" vs "142 ms not located" | erratum 25:94-95 vs deep-research CONSOLIDATED:79-88 |
| sibling `argmax_EE` estimand | system EE ÷ U vs R_u·N_b/P_b (radiated) | zscore-transfer:208-218 vs EE-MAGNITUDE §0 / erratum 28 §2 (the latter verified by `git show`) |
| a0 learned EE on the 12-anchor panel | "never measured" vs 26.83 / 29.18 / 29.95 Mbit/J | erratum 23 §2 vs ZSCORE-VIEW (§4a #24) |
| Q1 v1 C2 marginal | +6.13 Mbit/J vs +22.83 % | NOTE-C1-C2-COMPETE vs BLIND-CLAIM:77 (units differ; same run) |

### 4e. The three worst

1. **§4a #1–3 — 62.502712 Mbit/J vs 41.28.** An EE subtracted from a mean active-beam count, across two
   V0.25 panels, with a boundary-0 search winner labelled as a rule — and in the two-arm declaration offered
   as a demonstrator for a different physics. Withdrawn by reference (erratum 23) but still verbatim in two
   in-force 09-11 documents and in the DQfD grounding report.
2. **§4a #4–5 — the "no demonstrator on the trained objective" comparison.** Rule arms scored greedily on
   the local **unpinned** archive at stream positions 0–23, against the frozen run's own **training-time**
   last-100 episodes (ε≈0.01, positions 8900–8999) produced on the **pinned** archive, with `r1_mean`
   (a mean of ratios) read as EE. Host, archive, policy mode, episodes and estimand all differ; it carried
   the closure that erratum 27 later withdrew for other reasons, and it is still quoted in erratum 23 and
   the per-head-bootstrap finding. (Same family: #8 — erratum 28 corroborates sat CAPPENALTY with local
   FEASFRONT across host, archive, checkpoint and MDP; #11–12 — paired statistics across unpaired cells.)
3. **§4a #6–7 — the V0.25 beam slope −425,009.885 bit/J used on the MODQN harness** (erratum 24's "2.2×"
   consistency check and erratum 26's CA-CPBR sign argument), withdrawn by erratum 28 but unamended in both
   errata and in the zclose report.
