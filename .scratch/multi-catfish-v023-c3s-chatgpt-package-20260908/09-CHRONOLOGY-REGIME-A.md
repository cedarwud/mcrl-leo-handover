# 01 — C3 design chronology and sealed stop tokens (2026-08-31 → 2026-09-07)

Scope and claim ceiling of this file: it is a **derived index**, not a new result. Every row is
transcribed from a sealed receipt, a frozen design document under `docs/`, or a dated project
memory note; no number here was recomputed, and nothing here is EE efficacy evidence. Where a
number appears it is quoted with the artifact or memory note that carries it. Sources are listed
in `SOURCES.md`; the memory notes for V0.14/V0.15/V0.15-R/V0.20 are shipped verbatim in
`09-PRIOR-DESIGN-ADJUDICATIONS/`.

Two weeks, eight target families, seventeen dated design attempts. Every one of them ended in a
pre-registered non-GO except V0.22, whose GO opened the V0.23 LC-SRS gate that then stopped on
physics.

---

## 1. Chronology — every C3 design attempt and its sealed token

| # | Date (2026) | Design | Target family (one line) | Gate / screen | Sealed token | One-line reason |
|---|---|---|---|---|---|---|
| 1 | 08-31 → 09-01 | **V0.3 / V0.4 masked mean/max C3** | Exact matched-opening non-focal externality ζ3: others held at the behavioural joint action, focal user deviates in the current slot | V0.4 C3 source + learnability gate (fresh Q3 rung 100, mean stronger-null skill 0.1236, 3/3 inits) → 500-update bounded screen → 30-world confirmatory block | `SCREEN_COMPLETE` → `CONFIRM_C3` → then `STOP_MASKED_MEANMAX_VALIDATION` | The five-arm route ablation's C3 arm was deployment-only leave-one-head-out on the *same* checkpoint, so its estimand was not the mechanism; the binding blocker was the rung working point (model-to-action-only MAE ratio: rung 10 = 0.893, 100 = 1.025, 1000 = 1.249, 10000 = 1.140 — only rung 10 beats baseline). Adjudicated 09-01 as ruling A, scientific STOP; C3 recorded **unresolved, not refuted** |
| 2 | 09-02 | **V0.9 integrated C2/C3 oracle (PNFE)** | Prospective non-focal externality against a *committed* "others hold" background | Integrated oracle prereg (09-02) → disposition (09-02) → fresh-context review (09-03) | `RETRY_MATCHED_OPENING_C3` | C3 arm −11.0636% EE (FULL vs DROP_C3: bits −5.3951%, energy +6.3736%, 0/3 positive lineages). The "others hold" counterfactual does not hold when oracle-arm handover rates are 0.6–1.0; this is estimator misspecification, so seeds, scale and the two identified defects D1/D2 cannot repair it |
| 3 | 09-03 | **V0.10 MONE-C3 oracle** | Exact matched-opening **unilateral** non-focal externality, `z3,u(a|c−u) = Δt Σ_{v≠u}[R_v(c−u,a) − R_v(c)]`, `O3 = z3/κ` | Six-arm oracle receipt, prereg frozen before outcome | Failed closed: `FULL/DROP-C3 − 1 = −2.6370%`, all 3 lineage directions negative | The sum of selected unilateral opening surpluses was positive in all 60 diagnostics while the realised joint direction reversed in 28 — unilateral externalities are not additive at the realised joint action |
| 4 | 09-03 | **V0.11 joint-C3 ordered oracle** | Same current-slot non-focal externality, evaluated against an *anticipated joint response* (self-consistent M1-D sweep, fixed user order 0…99) | Frozen selection table over two pre-declared depths, ordered before the new world was opened | Not selected; recorded later inside the "V0.10/V0.11 −1.5% to −4.4%" activation-expansion band | Deepening the background from unilateral to self-consistent joint did not reverse the sign; the dominant mechanism is beam-activation expansion |
| 5 | 09-03 | **V0.12 zero-energy-supported C3 oracle (ZR)** | Same non-focal externality, but positive credit only where the unilateral alternative has *exactly the same* current network-energy support as the C3-free reference — energy is a Boolean gate `g`, never added numerically | Oracle prereg frozen before outcome | Positive — the first C3 family to survive an oracle gate | (motivating census: 28/30 AP, 22/22 M1-D, 21/21 exact-O1 cases) |
| 6 | 09-03 | **V0.13 ZR-C3 fresh-world confirmation** | As V0.12, fresh worlds | Fresh-world confirmation prereg | PASS: **+0.94% EE, 4/4 worlds** | Later diagnosed (09-03 Q3-probe ruling): the gain is downstream beam consolidation, not the labelled current-slot positive externality — over steps 1–9 FULL had lower bits *and* lower energy than DROP_C3 at every step (totals: bits −5.7%, energy −6.6%, beam-steps −322) |
| 7 | 09-03 | **V0.14 three-head learner** | First learner-side step since V0.4: Q2 = 448-D OPS-3 state, Q3 = 287-D ZR decision-time state, shared masked mean/max head | Route review → route audit → learner gate → Q3 support probe | `PROCEED_TO_LEARNER_IMPLEMENTATION` → `CORRECT_BEFORE_HARVEST` → gate STOP (Q2 passed, mean skill 0.835 3/3; **Q3 skill −0.061975**) → **`STOP_THREE_HEAD`** | Two distinct failures: (a) z3 is 90% negative / 4% positive / 6% zero and bimodal, so an MSE-trained head learns the conditional mean and must lose under an MAE-vs-median metric; (b) support events (`g ∧ z3>0`) are **coordination** events set by *other* users' same-slot b0 actions and are not observable in the deployable per-user state — best single-feature AUC 0.72–0.75, finest conjunction precision 0.47 at recall 0.23, 39% of support destinations not active in the previous slot. Gate construction was cleared: learned Q2 + *perfect* z3 reaches support rate 0.851 and recovers 90.8% of teacher changes |
| 8 | 09-03 | **V0.15 learned-context oracle (two-arm)** | Hypothesis rescue: that labels generated/centred in the exact-O2 context were the cause of the learner failure | Two-arm oracle gate (no learner) | `REJECT_HYPOTHESIS` | The learned background `b′ = argmax(Q1+Q̂2)` equals the exact background `b` at 89–92% of anchors; perfect z3 with Q̂2 agrees with the exact teacher's argmax 94–95% and recovers 90–93% of teacher changes; the ZR reference row is identically 0, so centring is a no-op and both argmax and pairwise loss are shift-invariant. Neither token could discriminate the hypothesis; GO would have authorised rerunning a learner that already failed in-distribution on ~90%-identical labels |
| 9 | 09-03 | **V0.15-R reference-conditioned C3** | Representation rescue: 371-D reference-conditioned state, three contexts h=12/1/2, pivotal-residual learner | Source-only mechanical gate, five frozen clauses, launch audit before the server run | Launch audit `GO_SERVER_GATE` → result **FAIL** (3/3 initialisations) → structural ruling `NEXT_B`, with FAIL branch pre-declared as `STOP_C3_STRUCTURALLY` | h=12 consistency 0.84 → 0.64/0.68/0.67; pivotal 0.65/0.57/0.55; stable 0.64/0.69/0.69; support 0.34/0.32/0.31. Descriptive statistics on the sealed shards located the missing variable: the focal user's **origin** under the reference joint (occupancy `o_c`, power leadership `s_c`, `gap_c`, identity) — `P(pivotal | origin has no peer) = 0.0%` in all three contexts, and a 25-cell (origin peers, dest peers) binning policy fitted on TRAIN passed all five frozen clauses on VAL in 3/3 lineages |
| 10 | 09-03 | **V0.16 origin gate (402-D)** | The pre-declared `NEXT_B`: 371-D plus the origin identity block and the three origin globals; learner, loss, 3000 updates and clauses unchanged | Frozen origin gate, fresh worlds `2026111001`–`06`, inits `2026111101`–`03` | **`FAIL_ORIGIN_GATE`** | Symptom recorded in the V0.17 spec: a learned C3 can fit pivotal reference pairs while corrupting more than half of the decisions the exact ZR teacher leaves *stable* |
| 11 | 09-03 → 09-04 | **V0.17 Soft-KL gate** | Loss-side response to the V0.16 symptom: soft-KL stability objective over the teacher-stable decisions, seven declared rungs × three initialisations | Frozen contract with independent re-adjudication (`verify_v017_softkl_result.py`), outcome forced to exactly `PASS_SOFTKL_GATE` or `FAIL_SOFTKL_GATE` | **`FAIL_SOFTKL_GATE`** | Changing the loss did not recover the decisions the representation could not distinguish |
| 12 | 09-04 | **V0.18 relational ZR** | Relational Q3 over the ZR target; R2 incremental-interference cache to make the panel affordable | (a) pre-launch audit of the R2 cache-equivalence check; (b) relational-Q3 learner gate | (a) **`STOP_R2_EQUIVALENCE`** (b) **`STOP_LEARNER_GATE`** | (a) An **instrument** stop, not a science stop: the runner treated an R1/R2 content-digest inequality as a hard failure, but the sixth victim token (asinh interference difference) is structurally never bit-exact (equal only at 1e-22…1e-50); 9/9 fixture pairs disagreed, so the gate would have produced a certain false STOP. The design itself passed the audit. (b) Per-initialisation validation skill −0.0785124, −0.0558140, … |
| 13 | 09-04 | **V0.19 relational ZR (normalised output)** | V0.18 with a normalised head output | Frozen source panel + independent learner gate closure | **`STOP_LEARNER_GATE`** (`V019_FROZEN_PANEL_CLOSURE_VERIFIED`) | Normalising the output did not move the learner past the gate |
| 14 | 09-04 → 09-05 | **V0.20 repriced-C3 λ-confound gate** | Same ZR mechanism, re-priced so the λ used in the target matches the realised system price; two arms — EXACT_ZR (uses realised fading of physics events) and NOMINAL_ZR (deployable) | 36 shards, four frozen clauses, independent recomputation of receipts | EXACT_ZR **PASS** (+0.985%, 4/4 worlds, 3/3 lineages); NOMINAL_ZR **`REVISE_NOMINAL_Q3`** (+0.424%, 3/4 worlds, **2/3** lineages; lineage `2026092103` = −0.10%) | The λ confound was falsified for the exact arm (λ′/η_BASE 0.72 → 1.03 moved the effect only +1.031% → +0.985%), but the exact arm reads the *realised* fading of physics events, which no deployable Q3 can see. Nominal is the honest learner ceiling and it did not clear the tightened 3/3 rule. Mechanism remains joint beam consolidation (bits −5.3%, energy −6.2%). Service rate 1.000 in all three arms — the service clause was a no-op on this panel |
| 15 | 09-05 | **V0.21 EXPECTED_ZR fast screen** | The proposed "deployable-information ceiling" of the ZR family: the same live counterfactual, averaged over K draws of the auxiliary keyed fading instead of its realised value | Fresh-world fast screen with independent verifier | **`STOP_EXPECTED_ZR_FAST`** | Removing the un-observable realised fading removed the effect |
| 16 | 09-05 | **V0.22 C3 coalition-residual mechanics probe** | New family: two-user **local coalition-Shapley spatial residual surplus** over four matched current-slot profiles 00/10/01/11 — `z3,i = e_i + Ψ/2` with `Σ_i (ℓ_i + z3,i) = G(11) − G(00)`; `z3,i/κ` written only to member `u_i`'s proposed action, every other cell exactly zero | Mechanics + physical-signature probe with a literal deployment-composition diagnostic `x* = masked_argmax(Q1 + Q2 + z3/κ)` | **`GO_LC_SRS_OBSERVABILITY_GATE`** (PASS) — the only GO in this chronology | Independent post-gate adjudication accepted the two-player formula as an *exact Shapley allocation* of the explicitly named surplus, under a narrow contract that established mechanics only |
| 17 | 09-05 → 09-07 | **V0.23 LC-SRS successor gate (R1…R7)** | V0.22's LC-SRS promoted to a learner: deterministic relational C3View, one shared 67-64-64-1 token scorer, one reference-centred scalar Q3, unchanged single masked argmax of Q1+Q2+Q3 | Method freeze 09-05 (`METHOD_CORE_FROZEN`, `PASS_V023_IMPLEMENTATION_BOUND`, gate execution `NO-GO`) → observability gate contract 09-05 → relaunch decisions R2–R6 → balanced successor contract + launch decision 09-06 → sealed 09-07 12:54 UTC | `integrity_status=VERIFIED`, `status=PASS_FINAL_INTEGRITY`, **`c3_decision=STOP_PHYSICS_R7`**, `no_rescue=true` | Decided by `physical_signature`: pooled ratio-of-sums EE of the 11 profile vs 00 is **−0.049%** (`pooled_joint_direction=-1`) with only **2 of 8** development worlds positive (threshold: strictly positive **and** ≥4). `mechanics` 688/688 and `teacher_composition` (+0.335%, 5 worlds) passed; `learned_composition` (−0.660%, 2 worlds), `topology_consistency` (379/707 = 0.536 < 0.8) and `harmful_partial` also failed, so a physics pass would have yielded `REDESIGN_INTERFACE_R7`, **not** GO. The held-out learner **passed** (balanced accuracy 0.705 vs placebo 0.626, Spearman 0.839, 8/8 world wins). The deciding source arrays existed from 09-06 15:10 and were hidden ~22 h by six verifier-side defects |
| 18 | declared 09-06, run 09-07 | **V0.23 contingency D (cost-shared externality, CSE) and F (energy-share correction, EC)** | `z_D(u,a) = dt·Σ_{v≠u}[R_v(c) − R_v(b)] − λ([share_u(c) − share_u(b)] − [E(c) − E(b)])`, where `share_u` is per-beam energy / beam occupancy plus satellite baseband energy / served-satellite occupancy; `z_F` is the energy-only term of `z_D` | Ladder frozen 09-06 01:15 UTC **before any R7 outcome**; order L → D → F fixed, D has priority over F, explicitly not a best-score contest. F0 formula/tape feasibility (local) → F1 two-step kill screen (server) | r1 15:14 UTC `INVALID_RUN` (F0 conservation check, pure floating-point rounding; the fix touched tolerance only) → r2 16:40 UTC (383 s) → **`FAST_SCREEN_NO_SUPPORT`**, upheld as `ASTRA_F1_R2=NO_SUPPORT` | World `2026121721`, lineage `2026092101`, 2 canonical steps, 100 users, tape digest `738f9f01…`. BASE **118,630,258.51** bits/J; **D 117,054,987.34 (−1.327883%)**, service 0.995 below the 0.999 non-inferiority floor; **F 113,248,875.75 (−4.536265%)**, service 1.000. Survivor set empty → no F2 launch authority, F3 stays unlaunched. The ladder states this is `FAST_SCREEN_NO_SUPPORT`, **not** a structural-impossibility claim, and forbids proposing a new candidate from these residuals |

### The eight target families, grouped

| Family | Rows | Terminal token |
|---|---|---|
| A. Matched-opening ζ3 / masked mean-max | 1 | `STOP_MASKED_MEANMAX_VALIDATION` (unresolved, not refuted) |
| B. PNFE — committed "others hold" background | 2 | `RETRY_MATCHED_OPENING_C3` |
| C. Exact unilateral MONE, then its joint-response deepening | 3, 4 | failed closed (−2.64%; −1.5% to −4.4% band) |
| D. Zero-energy-supported (ZR) oracle → three-head learner | 5, 6, 7 | `STOP_THREE_HEAD` |
| E. Reference-conditioned representation (learned context → 371-D → 402-D origin → soft-KL) | 8, 9, 10, 11 | `REJECT_HYPOTHESIS`, FAIL/`NEXT_B`, `FAIL_ORIGIN_GATE`, `FAIL_SOFTKL_GATE` |
| F. Relational / normalised ZR learner | 12, 13 | `STOP_R2_EQUIVALENCE` (instrument), `STOP_LEARNER_GATE` ×2 |
| G. Repriced and expected ZR | 14, 15 | `REVISE_NOMINAL_Q3`, `STOP_EXPECTED_ZR_FAST` |
| H. Coalition-Shapley residual (LC-SRS) and the pre-declared contingencies D/F | 16, 17, 18 | `GO_LC_SRS_OBSERVABILITY_GATE` → `STOP_PHYSICS_R7` → `FAST_SCREEN_NO_SUPPORT` |

---

## 2. Design documents under `docs/` matching `MULTI-CATFISH-MCRL-V0*`

Fifty-four files; titles as written in each file's `# ` heading, dates as recorded in the file
name or its `Date:` field. The C3-relevant ones are marked **C3**.

| File | Date | Title | C3 |
|---|---|---|---|
| `MULTI-CATFISH-MCRL-V03-10EP-ABLATION-AUDIT-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 10-EP matched-ablation audit | |
| `MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 algorithm specification | |
| `MULTI-CATFISH-MCRL-V03-C2-GATE-CROSS-MODEL-REVIEW-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 C2 gate cross-model review | |
| `MULTI-CATFISH-MCRL-V03-C2-GATE-RESULT-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 C2 keyed gate result | |
| `MULTI-CATFISH-MCRL-V03-C2-POSTGATE-DESIGN-DECISION-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 C2 post-gate design decision | |
| `MULTI-CATFISH-MCRL-V03-C2-REACTIVE-RELEASE-IMPLEMENTATION-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3B C2 reactive-release implementation receipt | |
| `MULTI-CATFISH-MCRL-V03-OPUS-MAX-SOURCE-CONTROL-REVIEW-2026-08-31.md` | 2026-08-31 | Opus Max source/control co-design record for V0.3 | |
| `MULTI-CATFISH-MCRL-V03-FIGURE-DECK-HANDOFF-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 figure and deck handoff | |
| `MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 paper-authoring contract | |
| `MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 presentation layer | |
| `MULTI-CATFISH-MCRL-V03-E1-INSTRUMENT-VALIDITY-CONTRACT-2026-08-31.md` | 2026-08-31 | Multi-Catfish MCRL V0.3 E1 instrument-validity contract | |
| `MULTI-CATFISH-MCRL-V03-C2-COVERAGE-OPUS-MAX-ADJUDICATION-2026-09-01.md` | 2026-09-01 | C2 action-graph coverage: Opus Max adjudication | |
| `MULTI-CATFISH-MCRL-V03-E1-ACTION-SHARED-AMENDMENT-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.3 E1 action-shared amendment | |
| `MULTI-CATFISH-MCRL-V03-E1-MASKED-MEANMAX-FALLBACK-CONTRACT-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.3 E1 Masked Mean/Max Fallback Contract | **C3** |
| `MULTI-CATFISH-MCRL-V04-C3-VICTIM-BURDEN-DECISION-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 C3 victim-burden decision | **C3** |
| `MULTI-CATFISH-MCRL-V04-C3-SCREEN-RESULT-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 C3 bounded screen result | **C3** |
| `MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-PREREG-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 C3 confirmatory preregistration | **C3** |
| `MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 C3 confirmatory result | **C3** |
| `MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-PREREG-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 five-arm frozen-policy ablation preregistration | **C3** |
| `MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 five-arm frozen-policy ablation result | **C3** |
| `MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 route-interaction diagnostic | **C3** |
| `MULTI-CATFISH-MCRL-V04-C2-DESIGN-EVAL-AMENDMENT-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 C2 DESIGN-EVAL amendment | |
| `MULTI-CATFISH-MCRL-V04-C2-FAILURE-FORENSICS-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 C2 failure forensics | |
| `MULTI-CATFISH-MCRL-V04-C2-PARALLEL-CANDIDATE-PREREG-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 parallel C2 candidate preregistration | |
| `MULTI-CATFISH-MCRL-V04-C2-SUPPORT-COMPLETE-CENSUS-PREREG-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 support-complete C2 census preregistration | |
| `MULTI-CATFISH-MCRL-V04-C2-SUPPORT-COMPLETE-OPUS-MAX-REVIEW-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.4 support-complete C2 review | |
| `MULTI-CATFISH-MCRL-V05-C2-CONTROLLED-TAPE-EXPANSION-PREREG-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.5 C2 controlled-tape expansion preregistration | |
| `MULTI-CATFISH-MCRL-V05-C2-CONTROLLED-TAPE-DISPOSITION-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.5 controlled-tape disposition | |
| `MULTI-CATFISH-MCRL-V06-C2-K1-T1-PREREG-2026-09-01.md` | 2026-09-01 | Multi-Catfish MCRL V0.6 clean C2-k1 T1 preregistration | |
| `MULTI-CATFISH-MCRL-V06-C2-K1-BOUNDED-LEARNER-PREREG-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.6 C2-k1 bounded learner preregistration | |
| `MULTI-CATFISH-MCRL-V06-C2-K1-T1-FINAL-AUDIT-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.6 C2-k1 T1 final pre-outcome audit | |
| `MULTI-CATFISH-MCRL-V06-C2-K1-PAPER-FIGURE-DELTA-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.6 C2-k1 paper and figure delta | |
| `MULTI-CATFISH-MCRL-V07-C2-D2-FORMULA-SOURCE-PREREG-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.7 C2 D2 formula/source preregistration | |
| `MULTI-CATFISH-MCRL-V07-C2-FOCAL-NEXT-DESIGN-DECISION-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.7 C2 focal-next design decision | |
| `MULTI-CATFISH-MCRL-V07-C2-PARALLEL-CANDIDATE-CONTRACT-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.7 C2 parallel-candidate contract | |
| `MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.7 C2 balanced development-gate result | |
| `MULTI-CATFISH-MCRL-V09-INTEGRATED-ORACLE-PREREG-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.9 integrated C2/C3 oracle preregistration | **C3** |
| `MULTI-CATFISH-MCRL-V09-INTEGRATED-ORACLE-DISPOSITION-2026-09-02.md` | 2026-09-02 | Multi-Catfish MCRL V0.9 integrated oracle disposition | **C3** |
| `MULTI-CATFISH-MCRL-V010-MONE-C3-ORACLE-PREREG-2026-09-03.md` | 2026-09-03 | Multi-Catfish MCRL V0.10 MONE-C3 oracle preregistration | **C3** |
| `MULTI-CATFISH-MCRL-V011-JOINT-C3-ORDERED-ORACLE-PREREG-2026-09-03.md` | 2026-09-03 | Multi-Catfish MCRL V0.11 joint-C3 ordered oracle preregistration | **C3** |
| `MULTI-CATFISH-MCRL-V012-ZERO-ENERGY-C3-ORACLE-PREREG-2026-09-03.md` | 2026-09-03 | Multi-Catfish MCRL V0.12 zero-energy-supported C3 oracle preregistration | **C3** |
| `MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md` | 2026-09-03 | Multi-Catfish MCRL V0.13 ZR-C3 fresh-world confirmation preregistration | **C3** |
| `MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` | 2026-09-05 | Multi-Catfish MCRL V0.23 C3 method freeze | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` | 2026-09-05 | V0.23 LC-SRS observability and source-to-learner gate contract | **C3** |
| `MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md` | 2026-09-05 | V0.23 LC-SRS execution-parameter addendum | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md` | 2026-09-05 | V0.23 LC-SRS gate launch decision | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R2-2026-09-05.md` | 2026-09-05 | V0.23 LC-SRS gate relaunch decision R2 | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R3-2026-09-05.md` | 2026-09-05 | Multi-Catfish MCRL V0.23 LC-SRS gate relaunch decision R3 | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R4-2026-09-06.md` | 2026-09-06 | Multi-Catfish MCRL V0.23 LC-SRS gate relaunch decision R4 | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R5-DEFECT-CORRECTION-2026-09-06.md` | 2026-09-06 | Multi-Catfish MCRL V0.23 LC-SRS gate defect-correction relaunch decision R5 | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R6-FIT-BINDING-2026-09-06.md` | 2026-09-06 | Multi-Catfish MCRL V0.23 LC-SRS gate relaunch decision R6 | **C3** |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md` | 2026-09-06 | Multi-Catfish MCRL V0.23 LC-SRS one-shot successor Gate contract | **C3** (shipped as `05-R7-CONTRACT.md`) |
| `MULTI-CATFISH-MCRL-V023-LC-SRS-R7-LAUNCH-DECISION-2026-09-06.md` | 2026-09-06 | Multi-Catfish MCRL V0.23 LC-SRS R7 launch decision | **C3** |

Note on version coverage: `docs/` carries V0.3–V0.13 and V0.23. The V0.14–V0.22 designs were
worked in per-version lanes under `.scratch/` (`multi-catfish-v014-learner/`,
`multi-catfish-v015-c3-{learned-context,pivotal-residual,reference-gate}/`,
`multi-catfish-v016-c3-origin-gate/`, `multi-catfish-v017-c3-softkl-gate/`,
`multi-catfish-v018-relational-zr/`, `multi-catfish-v019-relational-zr-normalized/`,
`multi-catfish-v020-c3-{source-audit,candidate-screen}/`, `multi-catfish-v021-expected-zr/`,
`multi-catfish-v022-c3-coalition-residual/`) with their frozen contracts inside those lanes; their
rulings are the memory notes shipped in `09-PRIOR-DESIGN-ADJUDICATIONS/`.

---

## 3. What every design shared

Factual observations read off the frozen design documents and the composition ruling, stated as
observations rather than conclusions.

1. **Unilateral one-step deviation targets.** Every C3 target from V0.3 through the V0.23
   contingency candidates is defined by evaluating what happens when *one* focal user replaces its
   action in the *current* slot, against a background joint action. V0.11 states it explicitly:
   `z3,u(a | c−u) = Δt Σ_{v≠u} [R_v(c−u, a) − R_v(c)]`. V0.12 restates the ownership boundary —
   "C3 may use current-slot non-focal delivered-bit effects only. It contains no focal rate,
   numerical power or energy, `lambda0`, outage penalty, handover reward, or **future term**."
   What varied between designs was the *background* (behavioural joint / committed hold /
   self-consistent joint sweep / reference `b0 = argmax(Q1+O2)` / four matched profiles), never
   the fact that the deviation is one user for one slot. The V0.23 contingency `z_D` and `z_F`
   keep the same shape, and the F1 tape is explicitly a "physical **unilateral** evaluation tape".
   The one design that reaches beyond a single deviating user is V0.22/V0.23 LC-SRS, which
   evaluates a *two-user* coalition over four matched profiles — still one slot, still one step.

2. **Additive masked argmax composition.** Every prereg from V0.10 onward repeats the same
   sentence almost verbatim: "exactly three independent 28-action Q functions, one common safe
   mask, the left-to-right unweighted sum `Q1 + Q2 + Q3`, one smallest-native-index masked argmax,
   and one executed Main action. There is no deployed sweep, second mask, coordinator, auction,
   vote, route weight, sign flip, mixer, or post-training override." V0.23's method freeze repeats
   it for LC-SRS ("the unchanged single masked argmax of Q1+Q2+Q3 … no coordinator, auction, joint
   decoder, fallback, or post-selection repair"), and the V0.22 contract writes the deployment
   diagnostic literally as `x* = masked_argmax(Q1 + Q2 + z3/kappa)`.

3. **κ-normalised third term.** The third term always enters the sum divided by the frozen system
   constant κ (`V023-100E-MODEL-CONFIG.json` fixes κ = 10097071012.757404). The composition ruling
   in `06-COMPOSITION-RULING.md` traces this across the whole lineage: V0.9 divides by κ in
   `ee_axis_pnfe.py:253`; V0.11 produces `z3/kappa` in `ee_axis_joint_c3.py:262`; V0.13/V0.15 add
   normalised zero-marginal surfaces; the V0.22 contract *requires* `masked_argmax(Q1+Q2+z3/kappa)`
   and `ee_axis_coalition_residual_c3.py:433` implements the conversion. The 2026-09-07 ruling
   `ASTRA_F1_COMPOSITION=Z_OVER_KAPPA` applies the same convention to the contingency candidates.

4. **Per-user targets.** The target is always a value written into one focal user's action row:
   28 actions × one focal user, illegal entries zero behind the common mask, the reference action
   exactly zero. V0.22 makes the sparsity explicit even for the coalition family — "`z3_i/kappa`
   is written **only** to member `ui`'s proposed action. Reference, illegal, nonmember, and every
   other action cell is exactly zero." No design ever wrote a target onto a set of actions or onto
   a joint configuration as such.

## 4. What was never varied

Again, observations, not conclusions.

1. **The composition rule.** Across all eighteen attempts the deployment rule is one masked argmax
   over `Q1 + Q2 + Q3/κ` with unit coefficients. No design tried C3 as a veto, a constraint, a
   tie-breaker, a gate on an ε-band, a re-ranker, or a weighted term; the preregs affirmatively
   forbid coordinator, auction, vote, route weight, sign flip, mixer, second decoder, and
   post-selection repair. The V0.23 composition ruling records that the *only* live question ever
   raised about composition was unit conversion (`z/κ` versus raw bits), and it explicitly notes
   that "candidate-only `argmax(z)` lacks comparable support".

2. **The deviation horizon.** Always the current slot. C2 owns the projected offsets h = 1, 2, 3;
   C3's ownership statement bars any future term. The V0.15-R gate varied the *context* h = 12/1/2
   at which the reference joint was taken, not the horizon of the deviation being priced. Nothing
   in the record evaluates a multi-slot externality or a deviation carried through the D2 substep
   structure.

3. **Set-level targets.** No design produced a target over the OPS-3 action *set*, over a group of
   users jointly, or over a topology as a unit. The closest is LC-SRS, which allocates a two-user
   coalition surplus back to the two members individually (`z3,i = e_i + Ψ/2`, summing to
   `G(11) − G(00)`) and writes each member's share into that member's own proposed action. C2 is
   the head that carries an action-set state (448-D OPS-3); C3 never did.

4. **The evaluation objective and regime.** Every gate's final quantity is the canonical
   ratio-of-sums EE `η = Σ Δt·R / Σ Δt·P^N` with a service constraint, evaluated under a
   fixed policy with matched worlds, mobility, episode start and keyed-fading fields across arms.
