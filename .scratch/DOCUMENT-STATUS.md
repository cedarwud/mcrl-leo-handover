# Document status — which controller documents are in force (as of 2026-09-11 ~09:10 UTC)

Curated by CURATE, read-only. Companion files: `.scratch/RESULTS-REGISTRY.md` (every citable number
with the conditions that produced it) and `.scratch/curation/PROVENANCE-HEADER.md` (the header every
new report must carry). Nothing here edits or retracts any document; it records what the later
documents say about the earlier ones. Where I am inferring supersession rather than quoting a later
document that says so, the row says "(inferred)".

---

## 0. Reading list for anyone starting fresh — the in-force set, in reading order

All paths are in `.scratch/multi-catfish-v025-physics-successor/` unless stated.

| # | read | why |
|---:|---|---|
| 1 | `V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md` | **What is being run now.** New learner (three heads `Q_B`/`Q_E`/`Q_H`, Dinkelbach `eta`, dual `lambda` for C-H, shared bootstrap), three catfish (C1 `A m=2dB`→`Q_B`, C2 `A m=12dB`→`Q_H`, C3 `B1_NO_NEW_BEAM`→`Q_E`), arms A0 BASELINE / A1 OFF / A2 CF3 / A3 NULL3, 3 seeds × 1000 ep, pinned archive, eval seeds disjoint from training. Agent CF3PILOT, `.scratch/cf3-pilot/`. |
| 2 | `V025-CONTROLLER-DECLARATION-CONSTRAINED-ENDPOINT-2026-09-11.md` | **The endpoint** (owner decision): pooled EE s.t. C-H `H_inter ≤ 0.6016`/user-step and C-S service non-inferior (−0.5 pp). The unconstrained 19.8 % result is a *negative control*, never re-labelled. |
| 3 | `V025-CONTROLLER-PLAN-THREE-CATFISH-ON-THREE-HEADS-2026-09-11.md` | Why three catfish on three heads; physics-corrected meaning of C1/C2/C3. Read with §2's caveats (stage 1 folded into the pilot; kill-criterion 1 overtaken by erratum 27). |
| 4 | `V025-CONTROLLER-RULING-B0-THREE-QUESTIONS-2026-09-11.md` + `.scratch/b0-corrected/PROGRESS.md` (ROUND 2) | Baseline-MODQN arm = eq. (16) per-head max (B1 intact); D-1 behind a flag; D-2 per-step worst-served floor; final checkpoint, no selection; **local and sat numbers never compared**; TLE archive pinned `b924c8a0` (RANDOM_MASKED 52,420,510.0956937 on both hosts). |
| 5 | `V025-CONTROLLER-DECLARATION-EVALUATION-CONTRACT-AND-NULL-GUIDE-2026-09-11.md` rules 1–2 | Only the learned policy acts at evaluation; every mechanism arm carries a matched null control (now A3 NULL3). Rule 3 is withdrawn by its own amendment. |
| 6 | `V025-CONTROLLER-ERRATUM-27-A-HYSTERESIS-RULE-DOMINATES-THE-LEARNER-2026-09-11.md` + `.scratch/feasible-frontier/FEASIBLE-FRONTIER-2026-09-11.md` | The rule frontier on the MODQN harness; the frozen checkpoint is dominated; **success gate = beat baseline MODQN** (non-learned rules are diagnostic, not a bar); the three specialists. |
| 7 | `V025-CONTROLLER-RULING-THE-GAP-SURVIVES-THE-ANCHOR-ABLATION-2026-09-11.md`, `...-THE-GAP-SURVIVES-BEAM-POWER-ACCOUNTING-2026-09-11.md`, measurement table of `...-THE-TRAINED-OBJECTIVE-DISAGREES-WITH-THE-DECLARED-ONE-2026-09-11.md` | The negative-control headline and the two attacks it survived (+22.2 % ablated; 1.1916 under TDM_AIRTIME). |
| 8 | `V025-CONTROLLER-ERRATUM-28-THE-BEAM-SLOPE-IS-V025-ONLY-2026-09-11.md` + `.scratch/ee-magnitude/EE-MAGNITUDE-RECONCILIATION-2026-09-11.md` | Which numbers belong to which physics; why sibling EE (146–620) is not comparable (radiated-only denominator ×7.60, per-user estimand, `k_cap = 3`, lr). |
| 9 | `V025-CONTROLLER-RULING-PENALTY-TRACK-2026-09-11.md` (+ `.scratch/cap-penalty/`, `.scratch/penalty-arm/`) | Penalty is not a component; capacity penalty needs a cap; a cap breaks C-S. |
| 10 | `V025-CONTROLLER-ERRATUM-26-ACRM-HAS-A-PUBLISHED-LINEAGE-2026-09-11.md` | ACRM lineage (CER / CuSP / Sukhbaatar / Hughes / Minimax Exploiter), the tanh bound, containment, PBRS; ACRM reaches the main agent in the sibling implementation. |
| 11 | `V025-CONTROLLER-RULING-CATFISH-ATTACHES-TO-MODQN-NOT-STAGEC-2026-09-11.md` | Core ruling only: catfish = training-time experience streams in the MODQN DQN loop; C1/C2/C3-as-decomposition are not catfish. Its requirements table rows 1 and 3 are withdrawn (errata 23, 24). |
| 12 | `V025-CONTROLLER-RULING-C1VSGAIN-KILL-ALL-2026-09-11.md` | Why the V0.25 stage-C three-route design is closed (D2 CI negative → kill all; executed). |
| 13 | Errata 23, 24, 25 | The three error records most likely to recur: cross-quantity comparison (41.28 is a beam count; 62.502712 is a search winner); collapse is UNDETERMINED and z defaults OFF; the reward re-spec is rejected and `R_beam = B·mean SE`. |
| 14 | `.scratch/RESULTS-REGISTRY.md` and `.scratch/curation/PROVENANCE-HEADER.md` | Before quoting any number. |

Everything dated 2026-09-10 is about the **V0.25 stage-C / rate-target panel** line, which the
2026-09-11 rulings closed (C1VSGAIN kill-all) and moved away from (catfish attaches to the MODQN
trainer). None of the 09-10 documents is needed to run the current pilot; §2 says which of their
physics/instrument findings still stand if the V0.25 line is ever reopened.

---

## 1. Status of every controller document dated 2026-09-11

Legend: **IN FORCE** · **PARTLY SUPERSEDED** (sections named) · **SUPERSEDED** (by what). "Needed
now" = needed to understand or run the current MODQN-harness pilot.

| document (`V025-CONTROLLER-…-2026-09-11.md` unless noted) | status | what supersedes what | needed now |
|---|---|---|---|
| `DECLARATION-THREE-CATFISH-PILOT` | **IN FORCE** | — (frozen before any pilot result; supersedes the arm structure of the plan and of the two-arm demo declaration, and the "backbone JSRL" decision of the evaluation contract — the pilot uses per-head replay mixing, `rho = 1/9`, no JSRL; inferred from content) | yes |
| `DECLARATION-CONSTRAINED-ENDPOINT` | **IN FORCE** | — (answers owner decision 1 of the plan and the "decision this forces" of the anchor-ablation ruling; also executes the kill of all current-design trainings incl. PID 3131678) | yes |
| `PLAN-THREE-CATFISH-ON-THREE-HEADS` | **PARTLY SUPERSEDED** | Owner decisions 1–3 taken by CONSTRAINED-ENDPOINT (names C1/C2/C3 kept for now). Stage table: stage 1 folded into the pilot as arm A1 (THREE-CATFISH-PILOT). Sources fixed by the pilot (C1 = `A m=2dB`, C2 = `A m=12dB`, C3 = `B1_NO_NEW_BEAM`). "What can still kill it" bullet 1 (a rule with memory dominates the learner ⇒ no job) is overtaken by erratum 27's in-place withdrawal: success gate is beating baseline MODQN, rules are diagnostic. | yes |
| `RULING-B0-THREE-QUESTIONS` | **IN FORCE** | Its own correction supersedes FINDING-PER-HEAD-BOOTSTRAP's "defect" label. Its §"B0's pilot" numbers are smoke **and** were not at matched conditions (shared-env `_age_rng`, b0 PROGRESS R6 note). | yes |
| `DECLARATION-EVALUATION-CONTRACT-AND-NULL-GUIDE` | **PARTLY SUPERSEDED** | Rule 3 withdrawn by its own amendment. Rule 2 re-framed (which-knob diagnostic) by its amendment; instantiated as A3 NULL3. "Decided: B0" bullet superseded by RULING-B0 (D-1 is a flag, default eq. 16 for the baseline arm). "Decided: backbone JSRL, DQfD + RIS catfish as comparators" superseded by THREE-CATFISH-PILOT (inferred). "Not decided: constrained EE" superseded by CONSTRAINED-ENDPOINT. Gates FEASFRONT and JSRL-coverage answered by erratum 27. Rules 1 and 2 stand. | yes (rules 1–2) |
| `ERRATUM-27-A-HYSTERESIS-RULE-DOMINATES-THE-LEARNER` | **IN FORCE** | Withdraws RULING-NO-DEMONSTRATOR's closure and ASK-3's "specification success, endpoint failure" framing. Its own "112.46M under C-H is the bar" is struck through in place (owner: success gate = beat baseline MODQN). | yes |
| `RULING-THE-GAP-SURVIVES-THE-ANCHOR-ABLATION` | **IN FORCE** | Its "decision this forces" answered by CONSTRAINED-ENDPOINT. Refutes erratum 25 objection 3 empirically. | yes |
| `RULING-THE-GAP-SURVIVES-BEAM-POWER-ACCOUNTING` | **IN FORCE** | Revises the r3-premise argument (zero joules on average under TDM_AIRTIME too). | yes |
| `RULING-THE-TRAINED-OBJECTIVE-DISAGREES-WITH-THE-DECLARED-ONE` | **PARTLY SUPERSEDED** | Measurement table stands (note: shared-env run, trained 93,137,893.02 / ho 0.2796 — later docs use the fresh-env 93,110,907.97 / 0.2799; see registry CONFLICT rows). "Does not reopen the demonstration line" superseded by erratum 27. The "danger" path (re-specify the reward) rejected by erratum 25; endpoint changed instead by CONSTRAINED-ENDPOINT, and the 19.8 % is now a negative control. "Two defects that must be fixed" executed by B0 (D-2, D-3). Addendum (V0.25 interruption not measurable on the dense path) stands. | yes (table) |
| `ERRATUM-28-THE-BEAM-SLOPE-IS-V025-ONLY` | **IN FORCE** | Withdraws, for the MODQN harness, every use of `−425,009.885` bit/J/beam (errata 24, 26 and statements to the owner); corrected in place by CAPPENALTY's measurement. | yes |
| `RULING-PENALTY-TRACK` | **IN FORCE** | Supersedes erratum 20's sequencing plan. | yes |
| `ERRATUM-26-ACRM-HAS-A-PUBLISHED-LINEAGE` | **PARTLY SUPERSEDED** | The CA-CPBR "transfers?" row that says `Psi^A` has the **wrong sign here** because of `d(EE)/d(active) = −425,009.885` is withdrawn by erratum 28 ("unsupported, not refuted"). Everything else stands. It withdraws the DQFDGROUND ACRM bullets carried in DECLARATION-TWO-ARM-DEMO-UTILISATION. | yes |
| `RULING-CATFISH-ATTACHES-TO-MODQN-NOT-STAGEC` | **PARTLY SUPERSEDED** | Core ruling stands. Requirements row 1 (`GAIN_IN_SET` 62.502712 vs learned `a0` 41.28) withdrawn by erratum 23 (cross-quantity; search winner). Row 3 (no collapse confound) withdrawn by erratum 24 (UNDETERMINED). "Count: one new catfish" overtaken by DQFDGROUND (one demo stream) and then by PLAN/PILOT (three measured sources). Its "Endpoint: pure per-user argmax-EE on the frozen 48-episode harness" overtaken by CONSTRAINED-ENDPOINT (pooled EE, constrained). Its failure mode "C1VSGAIN shows exact C1 does not beat GAIN_IN_SET → kill the 37 trainings" executed by C1VSGAIN-KILL-ALL (under the declared D1/D2 rule, not against GAIN_IN_SET). | core only |
| `RULING-C1VSGAIN-KILL-ALL` | **IN FORCE** | Executed (kill done with owner authorisation; PID 3131678 exclusion corrected by CONSTRAINED-ENDPOINT). | background |
| `ERRATUM-23-THE-DEMONSTRATOR-COMPARISON-WAS-CROSS-QUANTITY` | **IN FORCE** | Carries its own in-place correction (62.502712 reproduces at full-48; only the *selection* was boundary-0). Its "next measurement" was run → RULING-NO-DEMONSTRATOR → withdrawn by erratum 27. Its demonstrator table compares training-log last-100 figures with eval rollouts (see registry comparison list). | yes |
| `ERRATUM-24-THE-Z-LINE-WAS-CLOSED-ON-RECEIPTS` | **PARTLY SUPERSEDED** | The sentence that MODQNZ's −3.511 % is "the sign this project's `d(EE)/d(active) = −425,009.885` predicts, at ~2.2× the magnitude" applies a V0.25 slope to the MODQN harness — withdrawn by erratum 28. Collapse UNDETERMINED, z default OFF, `q_entropy` defect: stand. | yes |
| `ERRATUM-25-THE-RESPEC-PROPOSAL-IS-REJECTED` | **PARTLY SUPERSEDED** | Objection 3 (renewal premium) refuted empirically by the anchor-ablation ruling. "The review's own recommendation, recorded not adopted" → adopted by the owner as CONSTRAINED-ENDPOINT. Objections 1–2 stand. Its "spreading EE-negative" interference channel: sign later measured on a capped MDP by CAPPENALTY (erratum 28 correction). | yes |
| `RULING-NO-DEMONSTRATOR-ON-THE-TRAINED-OBJECTIVE` | **SUPERSEDED** | Closure withdrawn by erratum 27 (hysteresis rules beat the learner on its own objective; its search covered only myopic additive rules). Its R23HISTORY item "`R = (B/U)·log2(1+γ)` makes a beam's total rate independent of U" withdrawn by erratum 25 objection 2. Its numbers stand as scoped measurements (mean-of-ratios `r1_mean`, training-log last-100 for the trained arm). | no |
| `FINDING-PER-HEAD-BOOTSTRAP` | **PARTLY SUPERSEDED** | "Verified defect" corrected by RULING-B0 (published eq. 16, frozen as B1). Theory (sum of `Q*_i` is not a Q-function of the scalarised reward) stands. "+0.8859 … no expressible myopic rule beats it" scoped by erratum 27. | background |
| `DECLARATION-TWO-ARM-DEMO-UTILISATION` | **PARTLY SUPERSEDED** | Demonstrator (`GAIN_IN_SET` 62.502712 vs `a0` 41.28) superseded by erratum 23. DQFDGROUND amendment's three ACRM statements (no counterpart; SASR/Shen unresolvable; `r^CF` substitution moves the fixed point) withdrawn by erratum 26. Arm set D0/D1/D2 superseded by THREE-CATFISH-PILOT's A0–A3 (inferred). DQfD loss-term and demo-fraction grounding (e.g. Nair 11.1 %, R2D3 0.39 %) still informs the pilot's `rho = 1/9`. | background |
| `RULING-OBJECTIVE-IS-STRUCTURAL` | **PARTLY SUPERSEDED** | V0.25 findings stand (`eta_ref` = 10.943122 Mbit/J; no single `eta` orders the six clean arms; horizon and `Phi` mismatch). Its design direction for the stage-C decision score is moot after C1VSGAIN-KILL-ALL. Its "support the owner's multi-objective framing" paragraph was followed by six cross-model rejections of that framing (reviews/). | no |
| `DECLARATION-TRAINING-PAUSE` | **SUPERSEDED** (executed) | Rule applied by C1VSGAIN-KILL-ALL; kill executed per CONSTRAINED-ENDPOINT. | no |
| `DECLARATION-SCORED-CHECKPOINT` | **SUPERSEDED** | The stage-C runs it governs were killed (C1VSGAIN-KILL-ALL). | no |
| `NOTE-C1-C2-COMPETE` | **SUPERSEDED** | Its information-class line ("surrogate labels") is wrong per erratum 21 §2 (runs were on exact labels; scoring in-sample). Stage-C design killed. | no |
| `NOTE-C2-ENDPOINT-AND-GAIN-PREDICTION` | **SUPERSEDED** | Stage-C killed; MULTISTEP stopped (AGENT-REGISTRY). The C2 tie-break-vs-additive owner decision became moot. | no |
| `ERRATUM-21-IN-SAMPLE-AND-NOT-SURROGATE` | **IN FORCE** | Corrects NOTE-C1-C2-COMPETE, FINDING-CORPUS-IS-SURROGATE's scope, PREDECLARATION-C3-NEGATIVE's confound, DECLARATION-SCHEDULE-CHOICE (C1 start rate 10× below its literal). | background |
| `ERRATUM-22-CONCENTRATION-IS-RULE-SPECIFIC` | **PARTLY SUPERSEDED** | Its replacement-measurement row labels 62.502712 as "loose cap + max-gain within-set assignment"; erratum 23 re-labels it the `CAP_050` search winner (declared rule 52.042303). "C1VSGAIN told to add the 62.50 rule as the reference C1 must beat" withdrawn by erratum 23. The withdrawal of "this physics rewards concentration" stands (V0.25). | background |

---

## 2. Status of every controller document dated 2026-09-10

Anchors used below: **K** = `RULING-C1VSGAIN-KILL-ALL-2026-09-11` (closes the V0.25 stage-C
three-route design); **M** = `RULING-CATFISH-ATTACHES-TO-MODQN-NOT-STAGEC-2026-09-11` (moves the
catfish to the MODQN trainer); **DP** = `DESIGN-PHASE-2026-09-10` (re-frames every earlier 09-10
record as design evidence without retracting measurements); **R1/R2** = `RETRACTION-2026-09-10` /
`RETRACTION-2-NUMERATOR-AND-CONTRAST-2026-09-10`. None of these is needed for the MODQN-harness
pilot; the last column says what survives if the V0.25 line is reopened.

| document (`V025-CONTROLLER-…-2026-09-10.md` unless noted) | status | superseded by / sections | survives (V0.25 only) |
|---|---|---|---|
| `STRATEGIC-REFRAMING` | SUPERSEDED | mechanism-paper reframing closed by FINDING-NOVELTY-CLOSED; its +6.359 % ceiling is on the defective provisioning rule (DERATING-SLIP) and mispaired (SEARCH-ORDER) | nothing numeric |
| `FINDING-LITERATURE` | SUPERSEDED | FINDING-NOVELTY-CLOSED; ERRATA items 1, 4 | the "run the anti-thesis" convention |
| `FINDING-C1C2-NOT-IDENTIFIABLE` | SUPERSEDED | C1C2-TARGET-NOT-FEATURES, CORPUS-IS-SURROGATE, C1REALV2 (QUEUE), K | contract-level collision witnesses |
| `FINDING-PAIR-INSUFFICIENCY` | SUPERSEDED | K | 27.8 % pairwise reversals (V0.25 pools) |
| `ADJUDICATION-STRATEGIC-STOPLIST` | SUPERSEDED | K | — |
| `FINDING-SUNI-OFFLINE-ARM` | SUPERSEDED | best-improvement fixed point superseded by first-improvement (SEARCH-ORDER, SPAN-AND-C3); K | the vacuous-T2 fix |
| `FINDING-C1C2-TARGET-NOT-FEATURES` | SUPERSEDED | K; C1 verdict reversed on repaired schema (QUEUE: top-1 0.1711 → 0.3381) | C2 adapter defect (822/1,784 rows) |
| `FINDING-DERATING-SLIP` | PARTLY SUPERSEDED | "artefact, not physics" framing overturned by ADJUDICATION-PROVISIONING-NOT-YET (sealed v1.9 §1: margin not re-solved into power); QUEUE records PROVFIX outcome **B (sealed rule stands, closed)** | 75.32 % no-mode census as a fact about the sealed rule |
| `OPEN-DECISION-PROVISIONING-FIX` | SUPERSEDED | ADJUDICATION-PROVISIONING-NOT-YET; QUEUE (outcome B) | — |
| `ADJUDICATION-CONVEXITY-ADVERSARIAL` | IN FORCE (V0.25 physics; not needed) | — | interior occupancy optimum exists; geometry acts through feasibility |
| `FINDING-NOVELTY-CLOSED` | PARTLY SUPERSEDED | closes the mechanism paper (stands); its "numerator non-standard" point may not be acted on by relabelling (R2 item 1) | Chen et al. VTC2024 prior art |
| `OPEN-DECISION-ADDITIVE-SPLIT` | SUPERSEDED | DECISION-CLOSED-NO-DIRECT; the 22.99× / +480/−440/+40 arithmetic "not established" (CONSOLIDATED, FEASIBILITY erratum); K | surrogate-label facts (scope per erratum 21) |
| `OPEN-DECISION-ARM-SET` | SUPERSEDED | DECISION-ARMS-ADDED; K | — |
| `FINDING-DR17-CORRECTIONS` | SUPERSEDED | conditioning figure not established (CONSOLIDATED); K | "time to convergence ≠ time to a useful decision" |
| `FINDING-CEILING-INTERVAL` | SUPERSEDED | CORRECTED-PICTURE (defective rule, old pairing) | 30-date method |
| `FINDING-BEAMWIDTH-CORRECTED` | SUPERSEDED | CORRECTED-PICTURE (simple-division numerics), DECISION-BEAMWIDTH-NO-CHANGE (correct pairing) | — |
| `FINDING-PARAMETRISATION` | SUPERSEDED | DECISION-CLOSED-NO-DIRECT; K | ranking ≠ calibration caution |
| `ERRATA-2026-09-10` (items 1–13) | IN FORCE (historical correction record) | subject closed by K / NOVELTY-CLOSED | the corrections themselves |
| `ERRATUM-14-CONFLATION` | IN FORCE (historical) | subject closed by K | §C3 vs §C4 distinction |
| `ADJUDICATION-PROVISIONING-NOT-YET` | IN FORCE (V0.25) | — | sealed v1.9 §1 stands; simple vs strict clearance |
| `DECISION-CLOSED-NO-DIRECT` | IN FORCE (historical; moot after K) | — | — |
| `DECISION-CLOSED-NO-DEADLINE` | IN FORCE (historical; moot after K) | — | anytime unilateral holds 81.7 %/87.9 % at 30.08 s; first-improvement +8.13 %/+1.62 % |
| `FINDING-SEARCH-ORDER` | SUPERSEDED | FINDING-SPAN-AND-C3 (re-measured with correct pairing) | — |
| `FINDING-PREFIX-IS-THE-VALUE` | IN FORCE (historical; moot after K) | — | prefix creates most of the uplift |
| `FINDING-SPAN-AND-C3` | PARTLY SUPERSEDED | span figures carried forward by CORRECTED-PICTURE / BEAMWIDTH-NO-CHANGE; C3 size-prior test moot after K | +1.2913 % corrected 20-anchor span |
| `FINDING-CORRECTED-PICTURE` | PARTLY SUPERSEDED | DECISION-BEAMWIDTH-NO-CHANGE (strict + correct pairing at 8 anchors); 30-date interval is old pairing (R1) | strict-clearance width curve (mispaired) |
| `STATUS-2026-09-10` (written 08:03, titled "end of day") | SUPERSEDED | later 09-10 records and K | — |
| `DECISION-ARMS-ADDED` | SUPERSEDED | K | zero cross-arm catalogue reuse |
| `FINDING-LOAD-REGIME-CLOSED` | IN FORCE (historical V0.25) | — | no regime enlarges the ~1 % span |
| `FINDING-C1-INTERFACE` | SUPERSEDED | C1REALV2 (QUEUE); K | interface is action-local |
| `PREDECLARATION-DEGENERACY-SCREEN` | SUPERSEDED | panel never built (AUDIT-AND-SPLIT, K) | — |
| `DESIGN-C3-PANEL-SPINE` | SUPERSEDED | ERRATUM-16 (move set sterilises C3); K | — |
| `FINDING-GEOMETRY-FEATURES` | SUPERSEDED | repaired in Q1 v2 (RULING-CONCEPT-TRANSFER); K | — |
| `PREDECLARATION-GEOMETRY-TEST` | SUPERSEDED | Q1 v2; K | — |
| `DECISION-BEAMWIDTH-NO-CHANGE` | PARTLY SUPERSEDED | DP withdrew "beam width may not be promoted by outcome" (design parameter; BEAMSWEEP dispatched); moot after K | 1.66° corrected-rule span +0.899421 % (8 anchors, strict, correctly paired) |
| `CONSOLIDATED-2026-09-10-0950Z` | PARTLY SUPERSEDED | R2 withdraws items "numerator discipline" and "routes vs neutral (−1.745 %)"; C1REAL superseded by C1REALV2 | "not established" list |
| `PREDECLARATION-C3-SCREEN` | SUPERSEDED | AUDIT-AND-SPLIT (screen stopped, both-rules design broken); K | — |
| `TERMINOLOGY` | IN FORCE (historical) | — | vocabulary (interaction term, inter-user coupling) |
| `OBSERVATION-C1-IS-SEARCH-GUIDANCE` | SUPERSEDED | K (direction never adopted) | — |
| `STRATEGIC-ENERGY-IS-IN-THE-CONTROL-LAW` | SUPERSEDED | control-law pillar deflated to +1.93 % (WHERE-THE-EE-LIVES; CTRLCAP); K | — |
| `AUDIT-AND-SPLIT` | IN FORCE (historical) | — | corrected rule never engaged by the bridge |
| `FINDING-CORPUS-IS-SURROGATE` | PARTLY SUPERSEDED | erratum 21 §2: the surrogate finding covers the 176,223-row pilot corpus only, not the v1/v2/z trainings; owed-repair register moot after K | 13-defect census of that corpus |
| `PREDECLARATION-RESIDUAL-READING` | SUPERSEDED | R1 (RESIDTOGGLE clairvoyant, withdrawn) | — |
| `DECLARATION-ULP-TOLERANCE` | IN FORCE (instrument rule) | — | 2-ULP replay gate |
| `ERRATUM-15-WRONG-SELECTOR` | IN FORCE (historical) | — | learned arms select by catalogue argmax |
| `ERRATUM-16-PANEL-SPINE-STERILISED-C3` | IN FORCE (historical) | — | — |
| `PREDECLARATION-DECOMPOSITION-BAKEOFF` | SUPERSEDED | K | — |
| `REQUIREMENT-CHANGE` | SUPERSEDED | REQUIREMENT-SHARPENED; then the owner success gate quoted in erratum 27 (beat baseline MODQN) and CONSTRAINED-ENDPOINT | — |
| `OPEN-CONTRADICTION-RESIDUAL-SIGN` | SUPERSEDED | R1 withdrew the RESIDTOGGLE side; SIGNFORK never completed; moot after K | — |
| `STATE-2026-09-10-0745Z` | SUPERSEDED | R1 (FULLSPAN, FACTORIAL, 9.8698 %, +78.02 % withdrawn) | — |
| `PREDECLARATION-TRAINING-GATE` | SUPERSEDED | R1 ("G1 is void as written"); DP | — |
| `REQUIREMENT-SHARPENED` | SUPERSEDED | R1 (FACTORIAL is not the contract's routes); owner success gate (erratum 27) | — |
| `V025-CONTROL-PLAN-2026-09-10` (no "CONTROLLER") | SUPERSEDED | R1; K | standing obligations list (§D) |
| `RETRACTION` | IN FORCE (historical) | — | the six withdrawals |
| `WHERE-THE-EE-LIVES` | PARTLY SUPERSEDED | R2 (demand-capped rows are a forbidden relabelling; −1.745 % is not a neutral-source contrast) | layer map shape |
| `RETRACTION-2-NUMERATOR-AND-CONTRAST` | IN FORCE (historical; demand-cap rule still binds V0.25) | — | full-buffer numerator per v1.8 item 5 |
| `FEASIBILITY` | SUPERSEDED | own erratum (22.985× withdrawn); wall 1 by C1REALV2; wall 2 by the v1.1 amendment (QUEUE) | — |
| `PREDECLARATION-ACCELERATION-ABLATION` | SUPERSEDED | CORRECTIONS-PREEXECUTION C1/C2 (axes are one axis; acceleration not available); DP (PANELCEIL acceleration ceiling, itself later withdrawn by errata 18/19); K | — |
| `DECISION-DATE-ALLOCATION-CLOSED` | IN FORCE (V0.25) | — | 116 / 48 / 2 date split; 48 eval dates untouched |
| `QUEUE` | SUPERSEDED (state snapshot) | later state | — |
| `FIGURE-PLAN` | SUPERSEDED | CORRECTIONS-PREEXECUTION C1 (42.91 % vs 49.82 % labels); K | F1–F5 specs if V0.25 figures are ever drawn |
| `PREDECLARATION-FIRST-TRAINING` | SUPERSEDED | CORRECTIONS-PREEXECUTION C3–C6; DP; K | — |
| `PIPELINE-CONTRACT` | SUPERSEDED | K | "run the reader" rule |
| `CORRECTIONS-PREEXECUTION` | IN FORCE (historical; moot) | — | incremental prize vs absolute fraction |
| `WHAT-IS-ACTUALLY-SEALED` | IN FORCE | — | three layers: sealing / compatibility pinning / implementation default |
| `DESIGN-PHASE` | PARTLY SUPERSEDED | its PANELCEIL figures (+1.944795 %, +1.045609 %) withdrawn by errata 18/19; its "3.32° gives +8.16 %" is a mis-attribution (see registry comparisons) | design vs confirmation split; 48 dates untouched |
| `OUTCOME-PLAN` | SUPERSEDED | stage-C runs killed (K); PANELCEIL figures withdrawn (errata 18/19) | — |
| `ERRATUM-17-S0-NOT-DEPLOYABLE` | IN FORCE | — | S0 +1.812631 % retired; C3-S v1 is V0.23-only |
| `ERRATUM-18-CEILING-WAS-A-BASIN` | PARTLY SUPERSEDED | its mechanism corrected in its own appended section (KILLTRIAGE); 3.099× withdrawn by erratum 19; RANDOM/ROUND_ROBIN results provisional pending STATICS2 | ceilings are local to a ~1,159-row catalogue |
| `ERRATUM-19-REFERENCE-SCALE-CONTAMINATED` (file 09-11 00:11) | IN FORCE | provisional items resolved by STATICS2 (see registry SV- rows) | contaminated vs clean path table |
| `ERRATUM-20-WRONG-PENALTY` (file 09-11 02:27) | PARTLY SUPERSEDED | sequencing (QCOLLINEAR first) overtaken by PENALTYARM, CAPPENALTY, RULING-PENALTY-TRACK | decorrelation stationary-point warning |
| `PREDECLARATION-ZSCORE-AND-HORIZON` | SUPERSEDED | stage-C killed (K); z line: erratum 24 | "eta_ref is highest-risk" note |
| `RULING-C3-ENCODER-CONTRACT` (file 09-11) | SUPERSEDED | K | derive-and-fail-closed rule |
| `SYNTHESIS-THE-HEAD-DOES-NOT-FIT` (file 09-11) | SUPERSEDED | DECLARATION-SCHEDULE-CHOICE; K | "beat plain linear first" preflight |
| `DECLARATION-SCHEDULE-CHOICE` (file 09-11) | SUPERSEDED | K; amended by erratum 21 §3 (C1 starts 10× below its literal) | step decay 1e-3, ×0.1 at 2,000/3,000 |
| `V025-DECLARATION-MODQN-COMPARATOR-BINDING-2026-09-10` (no "CONTROLLER") | PARTLY SUPERSEDED | primary gate "MODQN retrained on V0.25 physics" / secondary "frozen replay on V0.25" overtaken by M + erratum 27 + RULING-B0 (causal comparison is catfish-MODQN vs catfish-off MODQN on the same corrected tree and physics; frozen checkpoint = external historical reference). Fairness bindings 1–4 and 6 are not withdrawn anywhere (inferred still applicable to A0 vs A2). Evaluator rule and disclosure numbers are V0.25-only. | fairness bindings |
| `DECLARATION-RUNNER-V2` (file 09-11) | SUPERSEDED | K | — |
| `PREDECLARATION-C3-NEGATIVE` (file 09-11) | SUPERSEDED | erratum 21 (runs were on exact labels; in-sample); K | — |
| `RULING-THREE-BINDINGS` (file 09-11) | SUPERSEDED | K | Q1 gain-feature finding (APPROACH) |
| `RULING-CONCEPT-TRANSFER` (file 09-11) | SUPERSEDED | K; ETAFIX outcome = RULING-OBJECTIVE-IS-STRUCTURAL | 40-of-44 rejection ledger |
| `RULING-OBJECTIVE-IS-THE-BINDING` (file 09-11 07:46, dated 09-10 23:55Z) | PARTLY SUPERSEDED | V0.25 learner-free rulings 1–3 stand; priority order superseded by K/M | clean coordination ceiling +0.844250 %; `F` rejects +7.852367 Mbit/J from RSS_MAX |
| `FINDING-ARCHIVE-AND-GROWTH-2026-09-09` (mtime 09-10) | out of scope (dated 09-09) | — | — |

---

## 3. Other `.scratch/` report directories — one line each

"In registry" = whether its numbers appear in `.scratch/RESULTS-REGISTRY.md`.

### 3a. 2026-09-11 work (MODQN-harness line and its grounding)

| directory | what it answered | status | in registry |
|---|---|---|---|
| `feasible-frontier/` | Is the frozen checkpoint on the rule frontier? No — `A m=12dB` dominates it; JSRL coverage gate passes (step shape) | IN FORCE (local unpinned archive) | yes (FF-) |
| `beam-power-accounting/` | Does the 19.8 % gap depend on the `max` beam-power operator? No (1.1916 TDM_AIRTIME, 1.1629 ADDITIVE) | IN FORCE (local unpinned archive) | yes (BP-) |
| `b0-corrected/` | B0 fixes D-1/D-2/D-3 with fail-first tests; 500-ep smoke; round 2: D-1 flag, per-step floor, TLE pin `b924c8a0`; R8/R9 pilots pending | IN FORCE; round-1 eval numbers not at matched conditions | yes (B0-) |
| `penalty-arm/` | Does the ported Kumar srank penalty help? Null at 500 ep, 1 seed (D-1 tree, sat) | IN FORCE (pilot); fabricated placeholder in history → see `NOTICE-FABRICATED-PLACEHOLDER-IN-HISTORY.md` | yes (PA-, incl. WITHDRAWN placeholder) |
| `cap-penalty/` | Owner's remembered penalty = sibling L_cap; a k=3 cap causes no collapse here; cap raises pooled EE 1.162× by darkening beams (58 % served) | IN FORCE (pilot, capped MDP) | yes (CP-) |
| `ee-magnitude/` | Why sibling EE reads 146–620 vs 93 here: radiated-only denominator ×7.60, per-user estimand ×0.98, lr; bridge 693.87 | IN FORCE | yes (EM-, sibling section) |
| `catfish-surface/` | Where catfish can attach in the MODQN trainer (bounded code, ~430–620 lines for DQfD); scripted-arm panels; anchor ablation | IN FORCE; its "no better-than-learner source on the trained objective" verdict scoped to myopic additive rules (erratum 27) | yes (CS-, fork B) |
| `zclose/` | MODQNZ had no report; G-3 indicators cannot decide collapse; z lowers pooled EE −3.511 % (n=1) | IN FORCE (= erratum 24) | yes (ZC-, fork B) |
| `zscore-transfer/` | Why the sibling's z-score win (146.6 → 357.1) does not transfer | IN FORCE (sibling reference-only) | yes (ZT-, sibling section) |
| `concept-harvest/` | Old-project concepts worth retrying; owner's penalty recollection = capacity penalty | IN FORCE (sibling reference-only numbers) | yes (CH-) |
| `catfish-screens/` | CFSCREEN: representability (BC probe), action/state distinctness, margin scale of the three sources | IN FLIGHT (no report yet; intermediate numbers only) | yes, as SMOKE-ONLY (SC-) |
| `cf3-pilot/` | CF3PILOT: the three-catfish pilot | IN FLIGHT (step 0; no numbers) | no |
| `acrm-provenance/` | ACRM lineage; SASR citation resolves; implementation faithful | IN FORCE (= erratum 26) | yes (AP-) |
| `dqfd-grounding/` | DQfD-family grounding of the five catfish mechanisms | PARTLY SUPERSEDED (ACRM bullets by erratum 26) | yes (DQ-) |
| `catfish-facts/` | Catfish = five training-time mechanisms; C1/C2/C3 are a decomposition; frozen checkpoint trained on system-EE r1 | IN FORCE | yes (CF-) |
| `reward-history/` | r2/r3 change history; zero-joule handover; r3 premise | PARTLY SUPERSEDED (r3 "U-invariant rate" algebra withdrawn by erratum 25) | yes (RH-) |
| `lfd-family-screen/` | LfD family screen; JSRL strongest; per-head bootstrap surfaced | PARTLY SUPERSEDED (JSRL backbone not used by the pilot — inferred) | yes (LF-) |
| `deep-research/` | DR-1 ratio-objective RL, DR-2 LEO handover physics provenance, DR-3 landscape; ASK-1/2/3; consolidated ruling | IN FORCE as literature grounding | yes (DR-) |
| `reviews/` | Six cross-model reviews rejecting the bits/energy/time narrative; objective re-spec adversary (→ erratum 25); endpoint-decision prompt | IN FORCE (verdicts) | yes (RV-) |
| `thesis-deltas/` | Ch4/Ch5 thesis deltas | DELTA-CH5 marked DO NOT USE (erratum 19); DELTA-CH4 V0.25 stage-C (superseded by K, inferred) | yes (TD-) |
| `design-state/` | Design state given to the owner 2026-09-10 | SUPERSEDED (S0 claim withdrawn by erratum 17; stage-C closed by K) | yes (DS-) |
| `conversation-watch/` | watcher state, no findings | n.a. | no |

### 3b. 2026-09-08 / 09-09 V0.23–V0.25 successor work (historical; numbers not in registry unless a current document cites them)

| directory | what it answered | status | in registry |
|---|---|---|---|
| `multi-catfish-v025-paper-lane-20260909/` | paper-lane packaging for V0.25 | SUPERSEDED (K) | no |
| `multi-catfish-v025-round9-chatgpt-packages-20260909/`, `-round10-…/` | outside-review packages for V0.25 | historical | no |
| `multi-catfish-v025-stagec-contract-chatgpt-package-20260908/` | outside review of the stage-C contract | historical; stage-C closed by K | no |
| `multi-catfish-v024-regime-b-design/`, `multi-catfish-v024-regime-b-chatgpt-package-20260908/` | Track B regime study prereg draft | historical (never run as Track A) | no |
| `multi-catfish-v023-c3s-screen/`, `-c3s-variants/`, `-c3s-confirmatory/`, `-c3s-*-chatgpt-package-20260908/` | C3-S set-level coordinator kill screens (V0.23 physics) | historical; erratum 17: "V0.23 physics, development screen, does not transfer numerically" | only C3-S +2.883167 % / +2.921776 % and S0 +1.812631 % (cited by erratum 17) |
| `multi-catfish-v023-c3-probe-results-20260908/`, `-c3-probe-oracle-marginals/`, `-c3-probe-s0/` | V0.23 oracle marginals; S0 decoder | historical; S0 retired (erratum 17); oracle-marginals at risk (KILLTRIAGE #15) | C2 demand-cap sign sweep (cited by R2) |
| `multi-catfish-v023-c3-existence-e1/` | E1 existence screen (U1/J1 ceilings) | historical | U1 1.992311 / J1 2.222094 (cited by erratum 17) |
| `multi-catfish-v023-c3-candidate-ca/`, `-cc/`, `-c3-contingency*/`, `-c3-source-schedule/`, `-c3-observability/`, `-c3-outside-opinions-20260908/`, `-c3-core-problem-chatgpt-package-20260908/`, `-c3-chatgpt-review-package-20260908/` | V0.23 C3 candidate / contingency ladder (F1 kill screen etc.) | historical; C3 F1 `FAST_SCREEN_NO_SUPPORT` at risk per KILLTRIAGE #19 | no |
| `multi-catfish-v023-c1c2-*` (successor, -launch, -physical-evaluation, -stagec-launch, -target-generation(-launch), -provider-factory-v3, -predecision-capture, -neutral-*, -live-artifact-audit) | V0.23 C1/C2 successor development | historical | no |
| `multi-catfish-v023-server-pipeline/`, `-engineering-lane/`, `-controller-handoff-20260907/`, `-ch5-figure-pipeline/`, `-two-route-*`, `-real-one-world-plumbing/`, `-target-batch-adapter/`, `-training-readiness/`, `-baseline-adapter/` | V0.23 pipeline, handoff, plumbing | historical | no |
| `multi-catfish-v023-r5-*`, `-r6-*`, `-r7-*` | V0.23 R5–R7 relaunches and final-verifier repairs; R7 = STOP_PHYSICS_R7 | historical (sealed outcome) | no |
| `multi-catfish-v023-100e-screen-preoutcome(-v2)/`, `-five-arm-*`, `-heterogeneous-trainer/`, `-episode-screen/`, `-e2e-vertical-slice/`, `-d40-current-loader/`, `-current-c3view-provider/`, `-provider-orchestrator-bridge/`, `-post-r7-provider-factory/`, `-postgate/`, `-physical/`, `-ablation-prep/`, `-flow-audit-20260906/` | V0.23 five-arm screen machinery | historical | no |

### 3c. Pre-2026-09-05 (V0.3–V0.22, catfish v1 design era, P6)

`c2-v03/`, `c2-v03a-fast500/`, `c2-v03a-trend/`, `c3-v04/`, `pnfe-v09/`, `mone-v010/`, `joint-c3-v011/`,
`zero-energy-c3-v012/`, `zero-energy-c3-v013/`, `zero-energy-c3-v013-verifier/`, `multi-catfish-v014-learner/`,
`multi-catfish-v015-*` (3), `multi-catfish-v016-c3-origin-gate/`, `multi-catfish-v017-c3-softkl-gate/`,
`multi-catfish-v018-relational-zr/`, `multi-catfish-v019-relational-zr-normalized/`,
`multi-catfish-v020-c3-candidate-screen/`, `multi-catfish-v020-c3-source-audit/`, `multi-catfish-v021-expected-zr/`,
`multi-catfish-v022-c3-coalition-residual/`, `ee-axis-redesign/`, `catfish-*` (cross-model-audit, design-data,
factorial, geometry, literature, opus-review, oracle-gate, pivotality-probe, stage0, waiting-gate),
`smc-er-short-ep/`, `multi-catfish-v3-dev-pilot-20260828/`, `corrected-postrun/`, `p6-server-reliability/`,
`chinese-word-*` (2), `server-sync-20260909/`, `tle-frozen-20260820-authority-v1/`, `.tmp-astra/`:
**historical**, each superseded by the next version in the chain and all by the 2026-09-11 pivot; their
verdicts are summarised in the auto-memory index. **No number from them is in the registry** except where
a current document still cites one (the registry says so row by row). `tle-frozen-20260820-authority-v1/`
is a data authority, not a report.
