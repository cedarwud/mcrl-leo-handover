**On the same 93 development anchors and the same full-48 realised endpoint, exact C1 alone reaches pooled EE 35.2347 Mbit/J (98.58% served, 26.78% attaining) while the one-line gain heuristic `RSS_MAX` reaches 37.6639 (99.84%, 27.61%) and the catalogue's own unconditional first `s0` proposal reaches 37.5256 (99.81%, 27.66%), so exact C1 is −2.4292 Mbit/J, −6.450% against `RSS_MAX` (step-cluster 95% interval −11.52% to −1.26%, better at only 19 of 93 anchors) and −2.2909 Mbit/J, −6.105% against `S0_TOP1_UNCONDITIONAL` (interval −11.24% to −0.86%, better at 5 of 93); against the strongest declared beam-set rule it is −12.3445 Mbit/J (−25.945%, interval −36.80% to −11.39%) and against the reproduced search winner −27.2734 Mbit/J (−43.632%, interval −54.32% to −29.20%); C3's oracle EE marginal, exact C1+Psi minus exact C1_ONLY, is −0.6253 Mbit/J, −1.775% (interval −8.99% to +4.00%, indistinguishable from zero and pointing down); exact C1 does not beat the gain heuristic it mostly selects.**

`DIAGNOSTIC_NOT_CLAIM` · C1VSGAIN · 2026-09-11 (UTC) · learner-free, development anchors only

## Answer in six lines

1. **Exact C1 loses to a one-line gain heuristic on every axis at once.** Pooled EE, PHY service and rate-target attainment are all worse than `RSS_MAX` and worse than always taking the catalogue's first `s0` proposal without scoring anything. The EE intervals exclude zero.
2. **The loss is not carried by a few anchors.** Where `C1_ONLY` and `RSS_MAX` choose differently (65 of 93 anchors), C1 is better at 19 and worse at 46. Against `S0_TOP1_UNCONDITIONAL` the choice differs at 31 anchors: C1 better at 5, worse at 26.
3. **C1's own distinctive picks are where it loses most.** At the 10 of 93 anchors where `C1_ONLY` selects something other than an `s0` proposal (3 beam evacuations, 7 pairwise moves), those picks pool to 11.8597 Mbit/J at 86.8% served against 18.0821 Mbit/J at 100% served for the unconditional `s0` proposal on the same 10 anchors: **−34.4% EE and −13.2 points of service for the privilege of being selective.**
4. **C3 adds nothing.** The exact interaction term moves pooled EE by −1.775%, an interval that covers zero, changes the choice at 46 of 93 anchors and is worse at 28 of those 46. Attainment falls (26.78% → 25.26%) while service rises (98.58% → 99.66%).
5. **The binding constraint is the sealed catalogue, not the scorer.** The best member of the catalogue by realised full-48 EE — a within-catalogue ceiling no score can beat — is 39.2898 Mbit/J. Every in-set gain rule measured here is above it: the best single declared rule 47.5792, the boundary-0 pick among the three max-gain declared rules 50.3435, the reproduced search winner 62.5081, which beats the catalogue ceiling at 79 of 93 anchors. **No selector over `bounded-union-v2` can reach the numbers the non-catalogue gain rules already reach.**
6. **Reference classes are kept apart.** The declared-rule number and the search-winner number are reported separately below and are never pooled into one comparator, per controller erratum 23.

## Reporting conventions

Evidence classes: `[RUN]` verified by running code on `sat` in this work; `[DERIVED]` arithmetic or a direct consequence of quoted code; `[TRANSCRIBED]` copied from another report and not re-derived here; `[INFERRED]` interpretation.

Every EE figure carries field block **[E]** unless another block is named:

- **Reference:** the arm named in the row. Every headline marginal is taken against `C1_ONLY`, exact C1 used alone as the selection score.
- **Information class:** development, learner-free, exact-label oracle. 93 development anchors — world 1 steps 0–29 and world 2 step 0, each with carriers nearest-eligible / stay-if-possible / random-masked — from the read-only corpus `/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910`, corpus digest `db2b4007…c94b` per its builder. All 93 shard SHA-256 sidecars were re-verified in this run. No checkpoint was read; no learner exists in this measurement; no evaluation-only claim date was read.
- **Estimand:** the pooled EE of the configuration each rule commits at the anchor step, open loop, step *t* only.
- **Numerator:** Σ saturated full-buffer decoded bits ÷ Σ joules, from ONE fresh realised **dense full-48** `StepEvaluator` batch per anchor. No demand cap.

Selection-side label statistics carry block **[L]**: reference as named; information class the same 93-anchor exact labels (90,938 rows, 9,300 (anchor, user) groups); estimand the sealed additive set score; numerator the summed per-user label deltas against the incumbent row.

Served and attainment are fractions of the 9,300 user slots and are printed beside every EE number, as required.

## 1. Parity gates, reported before anything else `[RUN]`

| quantity | target | measured here | delta |
|---|---:|---:|---:|
| `BASE` pooled EE, 93 anchors (C2TARGET) | 10.146875431594404 | 10.146875431594404 | 0 (bit-identical) |
| `C1_ONLY` pooled EE, 93 anchors (C2TARGET) | 35.23470844487427 | 35.23470844487427 | 0 (bit-identical) |
| catalogue members over 93 anchors (C2TARGET) | 91,547 | 91,547 | 0 |
| `RSS_MAX` full-48 EE, anchor `world 1 \| step 0 \| nearest-eligible` (BEAMCOUNT log) | 71.8385 | 71.8385 | 0 to 4 dp |
| BEAMCOUNT `CAP_050` winner, same anchor | 76.5938 | 76.5938 | 0 to 4 dp |
| BEAMCOUNT `CAP_050` winner, `world 1 \| step 2 \| nearest-eligible` | 61.1655 | 61.1655 | 0 to 4 dp |
| BEAMCOUNT `CAP_050` winner, `world 1 \| step 3 \| nearest-eligible` | 50.1200 | 50.1200 | 0 to 4 dp |
| BEAMCOUNT `S2\|A2` declared rule, `world 1 \| step 0 \| nearest-eligible` | 62.0071 | 62.0071 | 0 to 4 dp |
| `RSS_MAX` pooled EE, main harness vs the separate declared-rule pass | — | 37.66389871330207 both | 0 (bit-identical, two independent passes) |

The C2TARGET reproduction is exact to the last float bit, which is the strongest available check that this harness measures the same quantity on the same anchors. `[RUN]`

**One parity miss, disclosed.** At `world 1 | step 1 | nearest-eligible` BEAMCOUNT's `CAP_050` winner is 64.9012 and mine is 61.7024 (−4.9%). Cause: my cap ladder is truncated to caps {8, 20, 30, 50} for budget, while BEAMCOUNT ran {8, 9, 10, 15, 20, 30, 50} and its cap-50 winner at that anchor was inherited from a rung I did not run. **So the `GAIN_IN_SET_LADDER` arm is a lower bound on BEAMCOUNT's search winner, not an upper bound.** It is a lower bound that already beats exact C1 by 43.6%. `[RUN]`, `[DERIVED]`

## 2. The arms, exactly as constructed

All eight rules and the ceiling below are scored identically at the endpoint: one fresh realised dense full-48 `StepEvaluator` per anchor, `transition_from` = the carrier's step *t*−1 configuration, `BASE` inside the first `evaluate_many` call.

| arm | what selects the configuration | information it uses at decision time |
|---|---|---|
| `BASE` | nothing; the carrier reference a⁰ | — |
| `C1_ONLY` | argmax over the sealed catalogue of Σ_u [C1(u,a_u) − C1(u,a⁰_u)], tie-break lowest configuration id | exact C1 labels (oracle) |
| `C1_PSI` | argmax of Σ_u ΔC1 + Ψ(a), the exact set interaction of `targets.py:set_score_decomposition` | exact C1 and exact C3 (oracle) |
| `S0_TOP1_UNCONDITIONAL` | the catalogue's **first** `s0-top-two` proposal, always, no scoring | none |
| `S0_TOP2_BEST` | the better of the two `s0-top-two` proposals by exact C1 | exact C1 (oracle), over 2 options |
| `RSS_MAX` | per user, the legal option of greatest boundary-0 nominal gain (basin2 rule, `run_basin2.py:198-215`) | nominal gain only |
| `GAIN_IN_SET` | BEAMCOUNT **declared rules** S1/S2/S3 × A2 max-nominal-gain-in-set at cap C = 50; the one of the three with the best boundary-0 EE meeting the carrier-`BASE` served guard | nominal gain, legal graph, boundary-0 EE |
| `GAIN_IN_SET_LADDER` | BEAMCOUNT **search winner** at C = 50: nine declared rules, `RSS_MAX` seeded when it fits, first-improvement boundary-0 polish of the two best starts (4 passes), smaller-cap winners inherited over caps {8, 20, 30, 50} | as above plus a boundary-0 local search |
| `CATALOGUE_ORACLE` | the catalogue member with the highest **realised full-48** EE — a ceiling, not a policy | the endpoint itself (not deployable) |

**Ψ is the sealed exact interaction, not a re-definition.** For a catalogue member *a*, Ψ(a) = [F(a) − F(a⁰)]/κ + ΔΦ(a) − Σ_u [C1(u,a_u) − C1(u,a⁰_u)], with F the nominal boundary-0 Φ-inclusive objective — exactly the field the sealed C1 labels live in (`targets.py:154-173`, `c1_difference_surplus`, normalised total = core/κ + Φ). The identity was checked, not assumed: over every single-user catalogue member at all 93 anchors, where Ψ must be exactly 0, the largest residual is **7.89e-14** in κ units. `[RUN]` That residual also certifies that this harness reproduces the sealed C1 labels from physics rather than merely reading them.

`GAIN_IN_SET` and `GAIN_IN_SET_LADDER` lie **outside** the sealed catalogue at 93 of 93 anchors; `RSS_MAX` is inside it at 46 of 93; `S0_TOP1_UNCONDITIONAL`, `S0_TOP2_BEST`, `C1_ONLY`, `C1_PSI` and `CATALOGUE_ORACLE` are inside by construction. `[RUN]`

## 3. Pooled result, 93 anchors, full-48 realised endpoints `[RUN]`

Block [E]. `catalogue oracle` is a ceiling, not a rule; the two `GAIN_*` rows are reference classes explained in §6.

| arm | pooled EE (Mbit/J) | Σ bits | Σ joules | served | attainment | vs `C1_ONLY` |
|---|---:|---:|---:|---:|---:|---:|
| `BASE` | 10.1469 | 8.3616e12 | 824,052.3 | 0.7992 | 0.1201 | −71.20% |
| `C1_PSI` (exact C1 + exact Ψ) | 34.6094 | 1.24619e13 | 360,072.8 | 0.9966 | 0.2526 | **−1.78%** |
| **`C1_ONLY`** | **35.2347** | 1.23541e13 | 350,622.3 | 0.9858 | 0.2678 | reference |
| `S0_TOP2_BEST` | 37.1590 | 1.25954e13 | 338,959.0 | 0.9998 | 0.2689 | +5.46% |
| `S0_TOP1_UNCONDITIONAL` | 37.5256 | 1.24957e13 | 332,991.4 | 0.9981 | 0.2766 | **+6.50%** |
| `RSS_MAX` | 37.6639 | 1.24964e13 | 331,787.0 | 0.9984 | 0.2761 | **+6.89%** |
| `CATALOGUE_ORACLE` (ceiling) | 39.2898 | 1.26620e13 | 322,270.5 | 0.9983 | 0.2794 | +11.51% |
| `GAIN_IN_SET` (declared class) | 50.3435 | 1.27914e13 | 254,082.9 | 1.0000 | 0.3113 | +42.88% |
| `GAIN_IN_SET_LADDER` (search class) | 62.5081 | 1.29088e13 | 206,513.4 | 1.0000 | 0.3271 | +77.40% |

Note the mechanism: the arms differ far more in **joules** than in bits. `C1_ONLY` buys its bits with 350.6 kJ; the gain-in-set rules buy slightly more bits with 254.1 kJ and 206.5 kJ. `[DERIVED]`

### The nine declared BEAMCOUNT rules at C = 50, scored at full 48, no selection at all `[RUN]`

Separate pass, one fresh full-48 realised evaluator per anchor with `BASE` in the single batch; scalar `evaluate` stubbed, 0 calls. Mean active beams is per anchor.

| declared rule | pooled EE (Mbit/J) | served | attainment | mean active beams |
|---|---:|---:|---:|---:|
| **S2 descending coverage \| A2 max nominal gain** | **47.5792** | 0.9981 | 0.2894 | 31.45 |
| S3 descending nominal gain \| A2 max nominal gain | 46.4829 | 0.9997 | 0.3229 | 31.16 |
| `RSS_MAX` (no beam set) | 37.6639 | 0.9984 | 0.2761 | 47.58 |
| S1 ascending coverage \| A2 max nominal gain | 36.6411 | 0.9990 | 0.0532 | 18.65 |
| S3 descending nominal gain \| A1 coverage first | 20.8010 | 0.9677 | 0.1513 | 50.00 |
| S3 descending nominal gain \| A3 least loaded | 20.7385 | 0.9497 | 0.1406 | 50.00 |
| S2 descending coverage \| A3 least loaded | 18.5101 | 0.9316 | 0.1184 | 50.00 |
| S2 descending coverage \| A1 coverage first | 17.8817 | 0.9358 | 0.1523 | 50.00 |
| S1 ascending coverage \| A3 least loaded | 17.3382 | 0.9600 | 0.1139 | 47.03 |
| S1 ascending coverage \| A1 coverage first | 15.8875 | 0.9616 | 0.1116 | 50.00 |
| `BASE` | 10.1469 | 0.7992 | 0.1201 | 56.05 |

The assignment rule, not the beam-set rule, is what separates these: the three max-nominal-gain assignments occupy the top four rows with the coverage-first and least-loaded assignments 2.3–3.0× lower. That is the same direction BEAMCOUNT reported on its 12-anchor panel, reproduced here on 93 anchors. `[RUN]`

## 4. The numbers this job exists for `[RUN]`

Cluster bootstrap: 31 clusters, one per (world, step) decision instant holding its three carrier anchors, 2,000 replicates, seed 20260911. Per-anchor counts are exact ties broken as ties (identical configuration ⇒ identical EE).

| contrast | absolute (Mbit/J) | relative | 95% interval (relative) | 95% interval (absolute) | C1 better / worse / tied, of 93 |
|---|---:|---:|---:|---:|---:|
| `C1_ONLY` − `RSS_MAX` | **−2.4292** | **−6.450%** | **[−11.52%, −1.26%]** | [−4.833, −0.442] | 19 / 46 / 28 |
| `C1_ONLY` − `S0_TOP1_UNCONDITIONAL` | **−2.2909** | **−6.105%** | **[−11.24%, −0.86%]** | [−4.734, −0.315] | 5 / 26 / 62 |
| `C1_ONLY` − `S0_TOP2_BEST` | −1.9243 | −5.179% | [−9.50%, −0.98%] | [−3.737, −0.384] | 2 / 8 / 83 |
| `C1_ONLY` − best **declared rule** (S2\|A2) | **−12.3445** | **−25.945%** | **[−36.80%, −11.39%]** | [−16.424, −5.870] | 44 / 49 / 0 |
| `C1_ONLY` − `GAIN_IN_SET` (declared class, per-anchor boundary-0 pick of three) | −15.1088 | −30.011% | [−40.66%, −15.09%] | [−19.113, −8.176] | 42 / 51 / 0 |
| `C1_ONLY` − `GAIN_IN_SET_LADDER` (**search class**) | **−27.2734** | **−43.632%** | **[−54.32%, −29.20%]** | [−31.938, −19.375] | 6 / 87 / 0 |
| `C1_ONLY` − `CATALOGUE_ORACLE` (ceiling) | −4.0551 | −10.321% | [−15.04%, −5.79%] | [−6.444, −2.207] | 0 / 34 / 59 |
| **`C1_PSI` − `C1_ONLY`** (**C3's oracle EE marginal**) | **−0.6253** | **−1.775%** | **[−8.99%, +4.00%]** | [−3.861, +1.231] | 18 better / 28 worse / 47 unchanged |

**Plainly: exact C1 does not beat the gain heuristic.** Both intervals against the two heuristics named in the brief exclude zero and lie entirely below zero. Adding a perfect C3 does not rescue it: `C1_PSI` − `RSS_MAX` is −3.0545 Mbit/J, −8.110%, interval [−14.73%, −2.53%]. `[RUN]`

Service and attainment move the same way as EE, so this is not an EE-for-service trade: `C1_ONLY` 0.9858 served / 0.2678 attaining, against `RSS_MAX` 0.9984 / 0.2761, `S0_TOP1_UNCONDITIONAL` 0.9981 / 0.2766, best declared rule 0.9981 / 0.2894, search winner 1.0000 / 0.3271. `[RUN]`

Per world: world 1 (90 anchors) `C1_ONLY` 34.617 against `RSS_MAX` 37.054 and the search winner 62.266; world 2 (3 anchors) 68.351 against 68.566 and 70.236. The sign is the same in both. `[RUN]`

## 5. How often `C1_ONLY` picks something other than an `s0` proposal, and what those picks are worth `[RUN]`

`C1_ONLY` selects an `s0-top-two` whole-network proposal at **83 of 93** anchors, a `pairwise-top10-top2` move at 7 and a `beam-evacuation` at 3. `C1_ONLY` coincides with `S0_TOP1_UNCONDITIONAL` at 62 anchors, with `S0_TOP2_BEST` at 83, and with `RSS_MAX` at 28.

The 10 non-`s0` picks, in Mbit/J, all full-48:

| world | anchor | step | carrier | C1 pick | changed users | `C1_ONLY` EE (served) | `RSS_MAX` | `S0_TOP1` | catalogue ceiling |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|
| 1 | 006 | 2 | nearest-eligible | beam-evacuation | 5 | 21.326 (0.94) | 49.718 | 50.250 | 50.250 |
| 1 | 009 | 3 | nearest-eligible | pairwise | 2 | 14.794 (0.87) | 19.837 | 19.800 | 19.800 |
| 1 | 021 | 7 | nearest-eligible | beam-evacuation | 4 | 12.074 (0.91) | 17.001 | 16.861 | 18.303 |
| 1 | 022 | 7 | stay-if-possible | beam-evacuation | 3 | 7.760 (0.87) | 17.001 | 16.861 | 18.535 |
| 1 | 033 | 11 | nearest-eligible | pairwise | 2 | 10.607 (0.73) | 22.050 | 22.050 | 22.050 |
| 1 | 045 | 15 | nearest-eligible | pairwise | 2 | 13.318 (0.90) | 20.484 | 20.484 | 21.524 |
| 1 | 067 | 22 | stay-if-possible | pairwise | 2 | 19.009 (0.94) | 37.463 | 37.463 | 37.463 |
| 1 | 069 | 23 | nearest-eligible | pairwise | 2 | 7.514 (0.90) | 9.403 | 8.941 | 8.941 |
| 1 | 070 | 23 | stay-if-possible | pairwise | 2 | 9.715 (0.84) | 9.403 | 9.403 | 10.691 |
| 1 | 081 | 27 | nearest-eligible | pairwise | 2 | 8.832 (0.78) | 14.638 | 14.232 | 14.232 |

Pooled over exactly those 10 anchors: `C1_ONLY` **11.8597** Mbit/J at **0.868** served and 0.072 attaining, against `S0_TOP1_UNCONDITIONAL` **18.0821** at **1.000** / 0.068, `RSS_MAX` 18.2842 at 1.000 / 0.070, the catalogue ceiling 18.7811, `GAIN_IN_SET` 35.1854 and the search winner 50.1587. **C1 beats the unconditional proposal at 1 of those 10 anchors (070, +3.3%) and loses at 9, by up to −57.5%.** `[RUN]`

`[INFERRED]` These are the anchors at which C1's per-user ranking overrides the "move everyone" proposal in favour of a small, surgical move, and it is exactly where the score is worth least. The small moves also leave 13.2 points of service on the table.

## 6. Two reference classes, kept apart (controller erratum 23)

- **Declared rule.** A fixed construction from the step's legal graph with no search: the nine BEAMCOUNT rules in §3. The best of them here is **47.5792** Mbit/J (S2 | A2). `GAIN_IN_SET`, at 50.3435, is *not* one declared rule — it is a per-anchor boundary-0 choice among the three max-gain declared rules, which is deployable (its selector uses only decision-time boundary-0 information) but is a slightly richer class than a single fixed rule. Both are reported; C1 loses to both.
- **Search winner.** `GAIN_IN_SET_LADDER`, **62.5081** Mbit/J, is the output of BEAMCOUNT's cap-50 procedure: nine starts, a first-improvement local search, and inherited smaller-cap winners. It is a search result, not a rule, and it is not pooled with the declared class anywhere in this report.
- The two BEAMCOUNT panel figures 52.042303 and 62.502712 are `[TRANSCRIBED]` from a **12-anchor** panel; the numbers here are on **93** anchors, so they are not parity targets for each other. The parity targets I did check are the per-anchor ones in §1, and four of five match exactly.
- That my 93-anchor search-winner pooled EE, 62.5081, lands within 0.01 of BEAMCOUNT's 12-anchor 62.502712 is a coincidence of two different panels. It is not a parity check and must not be quoted as one. `[DERIVED]`

## 7. Boundary-0 versus full-48 `[RUN]`

Every EE reported here is full-48. The internal selectors of `GAIN_IN_SET` and `GAIN_IN_SET_LADDER` rank on boundary 0, exactly as their source rule does, and the gap is large and one-signed: the cap-50 winner's boundary-0 EE exceeds its own full-48 EE at **93 of 93** anchors (mean 83.807 against 64.129 Mbit/J). At anchor 000 the polished winner scores boundary-0 101.0175 and full-48 76.5938. `[RUN]` A second instance of the same effect: C2TARGET's boundary-0-selected within-catalogue best scores 38.9767 at the full-48 endpoint, while the true full-48 catalogue best measured here is 39.2898 — boundary-0 selection gives up 0.31 Mbit/J of the ceiling. `[RUN]`, `[TRANSCRIBED]` for the 38.9767.

## 8. Why C1 loses, mechanically `[DERIVED]` from §3 and §5

1. The sealed catalogue is the ceiling. Its best member by realised full-48 EE pools to 39.2898 Mbit/J. Every max-gain-in-set rule measured here exceeds it, and the search winner exceeds it at 79 of 93 anchors while using 26.55 active beams on average against `RSS_MAX`'s 47.58 and `BASE`'s 56.05. So the decision that matters — how many beams to light and who shares them — is not in the catalogue's action set at all.
2. Inside that action set, the decision is nearly binary: 83 of 93 `C1_ONLY` picks are one of the two `s0-top-two` whole-network proposals, and `S0_TOP2_BEST` (perfect C1 over exactly those two) is worth 37.1590 against 37.5256 for taking the first one unconditionally. **Choosing between the two proposals with a perfect C1 is worth −0.37 Mbit/J against not choosing at all.**
3. C1's remaining freedom — the 10 small moves of §5 — is where its selectivity is expressed, and it is negative there.
4. `C1_ONLY` already sits at the top of the catalogue's own full-48 ranking at 59 of 93 anchors, so it is not a weak maximiser of what it is scored on. The score is doing its job; the job is not worth much on this action set. `[RUN]`

## 9. Mandatory evaluator rule: compliance `[RUN]`

- **Selection comparison.** ONE fresh dense `StepEvaluator(field="nominal", boundary_indices=(0,))` per anchor — the nominal boundary-0 field is where the sealed C1/Ψ labels are defined — with `BASE` and every covered catalogue member in a single `evaluate_many` call. Profiles were read only from that evaluator's own `_evaluated` dict, and `BASE`'s presence was asserted. 91,547 catalogue members over 93 anchors, all covered by exact corpus rows, 0 uncovered, 0 invalid.
- **Endpoints.** ONE separate fresh realised dense full-48 `StepEvaluator` per anchor. `BASE` and all eight arm configurations entered in the **first** `evaluate_many` call; the remaining catalogue members were then added to that same fresh evaluator in further `evaluate_many` chunks of 64 so the realised full-48 catalogue ceiling could be measured under the 5 GB cap. **Disclosed deviation:** the endpoint evaluator is one fresh instrument per anchor but is populated by more than one batch. Every arm sits in the first batch together with `BASE`; no arm's endpoint depends on the chunking.
- **Stub.** On the nominal selection evaluator, on the endpoint evaluator, and on every boundary-0 search evaluator inside the BEAMCOUNT ladder, the bound method `evaluate` was replaced by a raising, counting stub. **Result: 0 scalar `evaluate` calls, in all three counters, in all three workers, and 0 in the separate declared-rule pass.** No foreign cache was read; nothing was reused across anchors.
- **Disclosure, unchanged from C2TARGET.** The sealed catalogue builder `_catalogue_with_census` constructs its own internal nominal boundary-0 evaluator and calls scalar `evaluate` on its own freshly populated cache. That is sealed code, left unmodified; it is catalogue construction, not a selection comparison of mine, and it never touches the stubbed evaluators. The same applies to nothing else: the BEAMCOUNT search evaluators are mine and are stubbed.
- **The GAIN arms' internal evaluators.** BEAMCOUNT's declared discipline is one fresh dense realised boundary-0 evaluator per (anchor, cap), with `BASE` in the first batch; that is what its `Boundary0Search` class does and I used its class unmodified. 442,992 boundary-0 configurations were submitted across the 93 anchors, all through `evaluate_many`.

## 10. Scope, resources, reproducibility `[RUN]`

- **Constraints honoured.** Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python` only; that tree was never modified. Everything written lives in `/home/sat/mcrl-v025-c1vsgain-ws` (`git init`-ed, uncommitted). At most 3 python processes of mine ran at once, each `nice -n 16`, all six BLAS/OMP thread variables pinned to 1, each with a 4.9 GB `RLIMIT_AS`. Peak RSS: main workers 1,829,628 / 1,839,380 / 1,820,572 KiB; declared-rule pass ≤ 1,725,088 KiB; merge and combine trivial. `anchor k/N` was printed for every anchor.
- **Wall time.** Main run 3 workers × 31 anchors, 01:17Z–02:45Z (1 h 26–28 min each), mean 167.0 s per anchor of which 30.6 s is the BEAMCOUNT ladder; world-tape builds 176–187 s each. Declared-rule pass ≈ 12 min. Every step checks for existing output first, and each worker writes a per-anchor `.partial` file it resumes from.
- **Development only.** Worlds are `TRAIN_WORLDS = DEVELOPMENT_WORLD_DOMAINS[:2]`. No evaluation-only claim date was read. No sealed artefact was modified. No checkpoint was read anywhere in this work.
- **Interruption, disclosed.** The controlling session hit a usage limit at about 02:00Z; the three detached workers ran to completion untouched (exit status 0 each) and were re-attached by inspection of cwd and command line at 04:33Z. Nothing was relaunched.

### Sources read (SHA-256)

| file | SHA-256 |
|---|---|
| `run_v025_pilot_c3.py` (pilot) | `95103bb96caaa130659fa0d509f19409574b406798a173e278a7d9dac12b7435` |
| `run_v025_matrix_probe.py` (engine) | `d430baf38eee7973aa56a503e905548bbf55ae4a5eb6f2435c2a2543d4786196` |
| `physics_v025/targets.py` | `e951aa2a73dcf1156632a18fb9c022fb007fd810412493d61f66333a2ed6b4ab` |
| `basin2/run_basin2.py` (`RSS_MAX` rule) | `0135d54c4c3a9a0731c653f58eac6e77e469a510aa0089a53c4d3f0a959c43d0` |
| `beamcount/run_beamcount_sweep_frozen.py` (rules imported, not reimplemented) | `0b9818f31a58a0b34acca50bc98379f9143af0867d04cbeae911ef1bb427fd58` |
| `BEAM-COUNT-CAP-2026-09-10.md` | `973e81e161042a5c518d71944671cd8818f1ef370f45145290d07c3d8ca18420` |
| `C2-TARGET-VALUE-2026-09-10.md` | `6efc40a1f3e018c6b4589a17f931d65c5095ddeb3a48c9c312d6128c6a230370` |
| `c2target/oracle_ee.py` (harness this one derives from) | `3a1ca6b40849ac0498fdb770ab8042c0447c743370a7838a74b76e7101a9bcdb` |

### Evidence written, in `/home/sat/mcrl-v025-c1vsgain-ws/.scratch/c1vsgain/`

`c1vsgain.py` (main harness), `merge.py`, `declared_rules.py`, `combine.py`;
`c1vsgain-93-w{0,1,2}.json`, `c1vsgain-93-merged.json`, `declared-93-w{0,1,2}.json`,
`declared-93-pooled.json`, `combined-93.json`, `smoke-1.json`, `smoke-2.json`, and the run logs.
Reproduce with `c1vsgain.py <corpus> <worker> 3 c1vsgain-93-w<worker>.json` for workers 0–2, then
`merge.py c1vsgain-93 3 93`, then `declared_rules.py <corpus> <worker> 3 declared-93-w<worker>.json`,
then `combine.py`.

**Known defect in `combine.py`, disclosed:** its per-anchor win counter compares the main pass's
`C1_ONLY` against the declared pass's independently recomputed `RSS_MAX`, so the 28 anchors where
the two arms commit the identical configuration are resolved by ~1e-16 float noise and it reports
27 C1 wins instead of 19. Every win/loss count in this report is the verified one, recomputed
directly from the worker records (§4). The pooled EE values and bootstrap intervals in
`combine.py` are unaffected — its `RSS_MAX` pooled EE is bit-identical to the main pass's.

## 11. What this measurement does not settle

- It is a step-*t*, open-loop measurement, like every panel in this project. It says nothing about horizon value, and it is not a claim about any learned head — no checkpoint was read.
- The verdict rule is not mine to apply: the pre-declared rule in `V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md` governs what follows from these numbers. This report is the measurement.
- The `GAIN_IN_SET_LADDER` arm is a lower bound on BEAMCOUNT's procedure (§1), so the C1 deficit against the search class is if anything understated.
- QoS guards other than PHY service and rate-target attainment (handover and availability guards, which SPECPROFILE reports all nine declared rules failing at C = 50) were **not** measured here and are not in any number above.
