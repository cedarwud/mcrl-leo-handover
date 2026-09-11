**Verdict: reject in its current form. The most damaging flaw is that the bits/energy/time decomposition was defined after the EE of each side's optimum had already been measured. That lets two non-learned configurations pass the necessity condition by construction, and against the stated BASE reference a random assignment passes it too. Meanwhile the only trained evidence shows the routes substituting for or dominating one another, not trading off.**

# Adversarial review of the proposed "three Catfish, three sides of EE" narrative, 2026-09-11

Reviewer stance: hostile but fair, no prior involvement. I read the primary reports myself (list in §0). I treat controller rulings and notes as one party's interpretation. I ran no experiments. The only arithmetic I did is ratio and log arithmetic on published aggregates, marked **[DERIVED]**.

## 0. Evidence read, and how to read numbers here

**Primary reports I read in full, on `sat`:**
- CLEANPATH: `rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH`
- CROWDCOST: `crowd-ws/CROWDING-COST`
- BEAMCAP: `beamcap-ws/BEAM-CAPACITY-REALISM`
- CEILING2: `ceiling2-ws/CEILING-CLEAN-AND-LEVERS`
- COORDVALUE: `coord-ws/COORDINATION-VALUE`
- ETAFIX: `etafix-ws/ETA-EXCHANGE-RATE`
- APPROACH: `approach-ws/APPROACHING-THE-INSTRUMENTS`
- C2TARGET: `c2target-ws/C2-TARGET-VALUE`
- Z-VIEW: `zscoring-ws/Z-VIEW-SCORING`
- CONVSCORE: `convscore-ws/CONVERGED-EXACT-SCORING`

**Workspaces with no report:**
- `solo-ws` has scripts only; the SOLO job was launched 2026-09-11 about 00:30Z.
- `triobj-ws` holds only `triobj-definitions.json`, with mtime **2026-09-11 00:40:02Z**.
- `c3reach-ws` and `hcell-ws` are empty.
- `multistep-ws` has a script and empty logs.

**Also read:**
- Headlines of MODQN-COLLAPSE, MODQN-BRIDGE and BASIN2.
- The predecessor MODQN reward code (`modqn-paper-exploration/.../env/step.py`).
- Locally: priority declaration v1.0, v1.1 and v1.9; the MODQN comparator binding; two controller rulings. I treated the rulings as interpretation, not evidence.

**Four fields for every EE figure unless a line says otherwise:**
- **Reference:** named in the sentence.
- **Information class:** learner-free, realised dense full-48 endpoint, development anchors of `V025_PROBE/world/1` (12 anchors for CLEANPATH, CROWDCOST, BEAMCAP, COORDVALUE and ETAFIX; 93 for C2TARGET).
- **Estimand:** pooled EE = Σbits/Σjoules.
- **Numerator:** full-buffer successfully decoded bits, no demand cap.

**Trained figures** are marked **[TRAINED · IN-SAMPLE · UNCONVERGED]**. They come from Z-VIEW: 16 seeds, 20 anchors, epoch 500. Every one of those 20 panel anchors is a training anchor (CONVSCORE §1: 20/20 overlap, 19,617/19,617 identical decision-state rows). The 500-update horizon was ruled inadmissible by the project's own convergence rule. **No out-of-sample figure exists for any learned arm. No MODQN figure on V0.25 exists.**

**Evidence tags:** **[EST]** = established by a primary report. **[SUG]** = suggested by a primary report. **[INF]** = my inference.

---

## 1. Circularity and outcome-fitting

### 1.1 The decomposition was written after its answers were known [EST]

The objectives the narrative calls the "three sides" are frozen in `triobj-definitions.json`, which was written at 00:40Z on 09-11. The file's own text:

- **LQ, the "bits side":** "*Its unconstrained per-user maximiser is RSS_MAX*."
- **BC, the "energy side":** −(number of distinct beams). Its optimum is the exact minimum legal-beam set cover. That is the construction CROWDCOST used for its "most crowded" endpoint: 8 beams at every step.
- **P, the "time side":** exactly the deployed `phi_qos` handover preference.

The EE of the two optima was already on record before the file existed:

| optimum | pooled EE | recorded in | time |
|---|---:|---|---|
| `RSS_MAX` | 41.621560 Mbit/J | CLEANPATH | 09-10 16:48 |
| crowded endpoint | 46.110374 Mbit/J | CROWDCOST | 09-10 16:27 |
| crowded endpoint, 2.5 % attainment | — | BEAMCAP | 09-10 18:22 |

The file's flag `"frozen_before_measurement": true` is literally true of TRIOBJ's own run. It is false of what the proposers knew. Once the objectives' argmaxes are two configurations whose EE has been measured at 3.8× and 4.2× BASE, "the bits side alone raises EE" and "the energy side alone raises EE" are re-measurements, not tests. A pre-registration that freezes definitions whose outcomes are already known is not a pre-registration.

The proposers concede the decomposition "maps onto measurements already in hand". The timestamps show that it is *made of* those measurements.

### 1.2 The relabelling contradicts the sealed route definitions [EST from documents; the judgement is INF]

- **Sealed C1** (v1.1 §4) is the "whole-network difference surplus". The seal adds: "*its positive marginal is expected through energy and service, not surplus bits — accepted*." Calling C1 the "bits side" therefore contradicts what the project sealed about C1's mechanism before any outcome.
- **Sealed C3** is a "*set-level coordinator*". Its admission requires "*genuine joint headroom (a multi-user witness beating the unilateral alternative)*" and an S0 gain of at least 1 % (v1.0 and v1.9 §6). The clean evidence says that headroom is absent:
  - k = 1 moves improve EE from both `RSS_MAX` and the crowded point at 12/12 anchors (COORDVALUE).
  - BASIN2 finds guarded, F-improving single-user moves from BASE toward `RSS_MAX` at 12/12 anchors.
  - The clean coordination ceiling is +0.844 % (CEILING2).
  - Coalition support saturates at |A| ≤ 1 (CEILING2).
  - 0 of 5,814 improving multi-user moves lie inside catalogue support (COORDVALUE).

  Renaming C3 the "energy side" (beam concentration) replaces a failed admission condition with one that a known configuration already satisfies.
- **The sealed rule** (v1.0, "Rules that make … honest"): "*No target, standby, margin, service or priority change after outcomes are opened.*" Redefining a route's job after its outcome is negative is exactly the move that rule forbids. It can be done only as a declared successor, with the original C3 negative reported alongside it.

**Is "C3 = concentration" justified independently of its effect?** Not by the evidence.

- Concentration is a set-level *outcome*, but nothing shows that reaching it needs *interaction*.
- The per-beam cost that concentration saves is a property of each beam: 0.338 W per radiating chain and 0.200 W per active satellite (CROWDCOST). A per-user decision can price it, given occupancy context. Q1 already carries `background_occupancy_excluding_focal` (APPROACH Q1 field 4).
- Whether unilateral EE ascent from BASE reaches a concentrated configuration is **untested**. The unilateral fixed point in the record optimises the mispriced `F`, not EE. So the claim that concentration needs a coordinator is open. It is not established.

### 1.3 The estimand drifted after the marginals came back weak [EST for the timeline; INF for the motive]

- The sealed test is FULL/DROP marginals, that is, each route's contribution in combination (v1.1 §5, v1.9 §4).
- Z-VIEW reported at 23:49Z on 09-10. FULL − DROP_C3 was negative in all three runs, and the C2 and C1 marginals were unstable across schemas.
- SOLO was launched at about 00:30Z and TRIOBJ at 00:40Z. The narrative now states necessity as "*each route, on its own, must raise EE*".

"Alone" and "marginal in combination" are different estimands. A route can pass one and fail the other, and redundancy produces exactly that pattern. Switching to the weaker one after the stronger one came in weak is outcome-dependent unless it was declared in advance. I found no such declaration.

### 1.4 Forking paths on the time side [EST for the definitions; INF for the risk]

TRIOBJ freezes two time-side objectives: P (handover preference) and a "secondary" S (next-step legality survival). §2.3 argues that P has no physical channel into EE. If P fails and S passes, reporting "the time side raises EE" through S would be selecting a definition by its outcome. **P must be binding. S may only be reported as secondary.**

---

## 2. Consistency with the evidence

### 2.1 No trained route has ever been measured alone [EST]

The five-arm inventory is FULL, DROP_C1, DROP_C2, DROP_C3 and ALL_NEUTRAL_CONTROL. There is no C1_ONLY, C2_ONLY or C3_ONLY trained arm. Every statement that "route X alone raises EE" is either learner-free (TRIOBJ and SOLO, both unreported) or untested. In particular, the narrative has **zero trained-model evidence for claim 1 or claim 2**.

### 2.2 Against BASE, the necessity condition does not discriminate [EST]

- **BASE is weak.** It is the carrier-conditioned geometric control: 11.027760 Mbit/J, 960/1200 served.
- **A random assignment passes the test.** RANDOM gets 11.233999 Mbit/J and 1,102/1,200 served, which is at least BASE's 960 (CLEANPATH). A seeded random legal assignment therefore raises EE under the service guard. That is the narrative's necessity condition, satisfied by noise.
- **A zero-target head passes too [TRAINED · IN-SAMPLE · UNCONVERGED].** ALL_NEUTRAL_CONTROL, an unconverged head trained on zero targets, reaches 20.3–22.2 Mbit/J against the zero-score knockout's 11.495 (Z-VIEW §3).
- **The catalogue does the work in the oracle.** C2_ONLY reaches 27.68 Mbit/J against BASE's 10.15 on 93 anchors, but it is **−21.43 %** against C1_ONLY (interval [−31.0 %, −9.6 %]) (C2TARGET). The catalogue is almost a binary choice between two whole-network `s0-top-two` proposals, which are near-RSS profiles. They are picked at 83 to 93 of 93 anchors. So "beats BASE" credits the candidate set, not the route.

A necessity condition is informative only against a strong reference that uses the same information. Candidates are `RSS_MAX`, the crowded construction, the retrained MODQN, or at the least the best non-learned rule available at decision time.

### 2.3 The three "sides" are not three mechanisms of B/E [DERIVED from EST aggregates, then INF]

Pooled EE has exactly two primitives, bits and joules. Split each instrument's log-EE gain over BASE into its two parts:

| configuration | bits vs BASE | joules vs BASE | EE vs BASE | share of log-EE gain from joules |
|---|---:|---:|---:|---:|
| `RSS_MAX` ("bits side") | ×1.475 | ×0.391 | ×3.774 | **70.8 %** |
| crowded ("energy side") | ×0.957 | ×0.229 | ×4.181 | **103.1 %** (bits fall) |

- **The "bits side" is mostly an energy lever.** This matches the sealed expectation for C1 quoted in §1.2 and the angle-aware power-control design: a better link needs less RF power. Both sides lower joules. They differ in what they do to per-user rate: `RSS_MAX` keeps 1.65×10¹² bits, while the crowded point falls to 1.07×10¹². Crowded against `RSS_MAX` is −35 % bits, −41 % joules, +10.8 % EE. That makes this an EE-versus-*throughput* axis. It is not a bits side versus an energy side.
- **The time side has no channel into EE in the primary cell [EST from documents]:**
  - Treatment 0 has "*interruption off*" and standby 0 (v1.0 matrix).
  - Power control is memoryless and history-independent (v1.0, v1.1).
  - `Phi` is absent from the metric. ETAFIX §1 and the CROWDCOST Part 4 code quote show that `Phi` counts only satellite and beam changes, and ETAFIX finds its weight is 27–99 % of pooled bits in the decision score.
  - The endpoint is open-loop and single-step, so value at steps t+1..t+3 is **unmeasurable** (C2TARGET §2 "Reading").
  - [INF] Under memoryless physics with no interruption cost, a persistence objective can raise EE only by holding a configuration that is good on B and E anyway. **Time is an index, not a third component of B/E.**
- **A physically grounded decomposition exists and is different [INF].** It would split joules into PA (90.8–94.9 % of modelled energy, CROWDCOST Part 1 §3) and circuit plus baseband, and split bits into spectral efficiency × airtime. The narrative's decomposition was not built from the energy account. It was built from the two instruments.
- **The energy side's advantage depends on the numerator [SUG, then INF].** Under full-buffer TDM, every beam with at least one user transmits in every slot (CROWDCOST Part 1 §1). Energy therefore tracks the number of open beams, and concentration buys EE by cutting each user's airtime:
  - crowded point: 8 % airtime per user;
  - mean rate 29.7 Mbit/s, minimum 0.65 Mbit/s;
  - 75.5 % of transmissions at the RF cap (BEAMCAP §3.1).

  The "EE versus service" tension is largely *created* by the full-buffer, no-demand-cap numerator that v1.8 made primary. That choice is legitimate and declared. But the paper must say that the energy side's EE advantage is contingent on it, and show the ranking under a demand-limited numerator. Otherwise a reviewer will.

### 2.4 The Pareto pair is about non-learned configurations, and it undercuts claim 3 [EST, then INF]

**The pair itself:**
- Crowded: 46.11 Mbit/J, 2.5 % attainment, 1200/1200 served (BEAMCAP).
- `RSS_MAX`: 41.62 Mbit/J, 24.75 % attainment, 1200/1200 served (CLEANPATH).

**Four problems:**

1. **Neither point is a route or a learned policy.** Each is the argmax of exactly one TRIOBJ objective: LQ gives `RSS_MAX`, BC gives the minimum cover. So the example exhibits two non-dominated points, **each reached by a single side alone**. That is the opposite of "*the method's value is reaching Pareto points no single route reaches*". No combined point exists anywhere in the evidence.
2. **The "front" is two points, not a curve.** On the crowding family, the intermediate members serve 1,144–1,170, not 1,200. `RSS_MAX`, with 47.75 active beams, sits far above the family member of similar beam count (Q60: 44.25 beams, 18.23 Mbit/J) (CROWDCOST Part 2). No evidence shows a combination tracing points between them.
3. **The service axis was declared not to be service.**
   - The 50 Mbit/s target is "*a synthetic operating point … explicitly not calibrated demand*" (v1.1) and "*a power-control setpoint, not a demand model*" (v1.8 item 5, quoted in CROWDCOST).
   - "Served" means PHY decodability at SINR ≥ −1.44 dB.

   The narrative cannot use rate attainment as the service-quality axis of its trade-off while the sealed record says it is not a service requirement. If it *is* the service axis, then the EE-best configuration leaves 97.5 % of users below target, and so does 75 % of the "link side" point. Either way the paper must pick one reading and live with it.
4. **Attainment is where the pair differs; served is identical.** The narrative says both serve all users. True, but that shows the served-count guard does not bind between them. The only axis carrying the "trade-off" is the undeclared one from point 3.

---

## 3. The single-judge problem

The project's primary is a single metric, EE. Under a single primary:

- **A combination worse than its best constituent is a loss.** This holds unless service is a declared constraint with a pre-fixed threshold. In that case configurations below the threshold are *infeasible*, not Pareto points.
- **The threshold alone decides the pair's winner.** Any required attainment above 2.5 % excludes the crowded point, and then `RSS_MAX` is the constrained optimum. The narrative must declare the constraint and its value before any learned result. Otherwise the trade-off language lets any EE shortfall be relabelled "service bought".

**What the trained and oracle evidence actually shows is dominance and override, not trade-off:**

- **Q1 v1 [TRAINED · IN-SAMPLE · UNCONVERGED].** DROP_C3, the C1+C2 system, beats FULL on every reported axis. FULL − DROP_C3 is −23.35 %, sign-consistent 16/16, pooled relative to DROP_C3.

  | arm | EE (Mbit/J) | served | attainment |
  |---|---:|---:|---:|
  | FULL | 32.96 | 0.9858 | 0.2473 |
  | DROP_C3 | 43.00 | 0.9891 | 0.2759 |

  Adding the "energy-side" route did not trade EE for service. It lost both.
- **Q1 v2 [TRAINED · IN-SAMPLE · UNCONVERGED].** DROP_C2 is at least as good as FULL on EE (43.41 vs 42.26), served (0.9989 vs 0.9988) and attainment (0.2747 vs 0.2720). The EE sign flips across seeds (15/16), so this is not a result. But it is no trade-off either.
- **Oracle C2 (C2TARGET, learner-free).** In the additive selector:
  - FULL equals C2_ONLY at all 30 changed anchors.
  - C2 overrides C1: median 154 κ of C2 score against 16.7 κ of C1 score given up.
  - C2 picks the lower-EE proposal at 20 of 30 changed anchors.

  That is one route overwriting another, not a negotiated trade-off.
- **Substitution across runs [TRAINED · IN-SAMPLE · UNCONVERGED].**
  - C2's marginal goes from +22.8 % (16/16) in Q1 v1 to −2.6 % in Q1 v2 *on identical labels* (CONVSCORE §2) once C1 can see more.
  - C1's marginal falls from +42.9 % (16/16) to +3.45 % (not a result) when C2 and C3 get z-features (Z-VIEW §5).

  Routes that absorb each other's signal are **redundant**, not in tension. This is the strongest available answer to "trade-off or redundancy?", and it answers "redundancy".

**Claim 4's own evidence contradicts claim 3's "not EE against EE" [EST from ETAFIX].**
- The single-price failure is a conflict *between anchors' EE*. One pooled η* is "*too low for the step-0 to step-2 anchors … and too high for step 3*". At η*, EE falls at 9 of 12 anchors and rises at 3.
- The pooled and per-anchor estimators can disagree in sign. C2TARGET's pooled +0.68 % becomes −1.39 % as an unweighted per-anchor geometric mean.

That is EE traded against EE, across anchors, inside the pooled ratio.

---

## 4. Claim 4: "the combination must be ratio-consistent (Dinkelbach)"

1. **The motivating failure does not touch the argmax [EST, ETAFIX §4].** `RSS_MAX` has strictly more bits and strictly less energy than every other arm, so it is argmax of B − ηE at *every* η ≥ 0.
   - The ordering failure is among non-argmax arms. One pair is RANDOM against NEAREST_ELIGIBLE, which also differ in service (1,102 vs 960); the other is MYOPIC against FP.
   - A selector needs the argmax, not the full order. On the six-arm evidence, the linear price already selects the EE-best arm.
2. **The version that removes every disagreement is tautological, and the deployable version is untested [EST].**
   - Pricing each start at its own realised full-48 EE zeroes the disagreements only because it is ranking by the metric itself (ETAFIX §6).
   - The nominal, deployable version has not been measured.
   - The residual mismatch is attributed to the selection horizon, boundary 0 against 48 boundaries (ETAFIX §5 "Mechanism", inferred there). Dinkelbach does not address that.
3. **In the proposers' own frozen design, the ratio-consistent rule does not combine the routes [EST, triobj-definitions.json].**
   - `"ratio_consistent"` is Dinkelbach on B − ηE over the candidate pool. It uses no LQ, BC or P value.
   - The only rule that combines LQ, BC and P is `"fixed_objective_space"`: a min-max-normalised weighted sum with one weight vector for all anchors. That is exactly the fixed linear weighting claim 4 says fails.

   So either the routes are combined linearly, and claim 4 condemns it, or the selection is ratio-consistent, and the routes are only candidate generators. The narrative's text, "each route optimises its own reward … combined by a ratio-consistent rule", describes neither.
4. **Not a contribution of the three-route structure [INF; literature not verified in this review].** Dinkelbach's method (Dinkelbach, 1967) is the standard way to maximise a single ratio such as B/E. It is widely used for wireless EE; see e.g. Zappone and Jorswieck's fractional-programming monograph, cited from memory and not verified here. It is not a multi-objective combination rule, and nothing stops the MODQN baseline from using it. ETAFIX relays "Calvo-Fullana et al. 2023, Prop. 1" on the limits of fixed linear scalarisation; I did not verify it. Note also that, as I understand the multi-objective RL literature (not verified here), fixed linear weights cannot reach non-convex parts of a Pareto front. That cuts *against* claim 3 if the combination is linear. It is irrelevant if the combination is Dinkelbach, because Dinkelbach is not a Pareto method.

---

## 5. Relation to the baseline

**What the baseline's objectives actually are [EST from predecessor code; the brief differs in part].** From `modqn-paper-exploration/.../env/step.py`:
- **r1:** the paper's Eq. 3 throughput, `B/N_b·log2(1+γ)`, by default. EE variants exist and are selectable; the Catfish-era factorial runner hard-asserts `r1_reward_mode = angle_aware_ee`. **I did not verify which r1 the frozen checkpoint `e6b063ef…` used.** The brief's "r1 = EE" should be checked against that checkpoint's config before it goes into a paper.
- **r2:** the handover penalty.
- **r3:** `−(max_beam_thr − min_beam_thr)/U`, a throughput gap, not "−U occupancy". Reachable empty beams count as zero throughput on the min side, so r3 reduces to penalising high-throughput beams. Either way it is a **spreading** term.

**The proposal maps almost one-to-one onto MODQN's structure [INF]:**
- "time side" P = the deployed `phi_qos` handover preference = MODQN r2, the same 1.0/0.5 lineage;
- "energy side" BC = MODQN r3 with its **sign flipped** (concentrate instead of spread);
- "bits side" LQ = a per-user link-margin proxy standing where MODQN's r1 stands. If the brief is right that r1 is already EE, the proposal *replaces the target with a proxy*.

A reviewer will conclude the distinguishing content is "the load-balancing term has the wrong sign for EE in this physics". That is a finding about the reward and the physics, testable on MODQN itself. It is not evidence for a three-route architecture.

**r3 conflicts with EE here [EST, SUG].**
- On the development panel, EE falls monotonically as assignments spread: −0.92 % per added mean-active beam over 8–98 beams. The one exception is the N = 2 low-load case (CROWDCOST Part 3).
- CROWDCOST Part 4: "*an explicit load-balancing term would be actively harmful to EE*".
- MODQN does spread: 68.7 active physical beams per 100 users. That was measured on V0.23 TRAIN profiles, not V0.25 (MODQN-COLLAPSE).

**Consequence [INF]:** any Catfish-over-MODQN EE gap may be carried largely by r3's sign. The comparator binding fixes MODQN's budget, seeds, information and tuning procedure. It does **not** require an r3-ablated MODQN. Without that arm, the comparison cannot separate "three routes help" from "MODQN was told to spread".

**The gate does not exist yet [EST].**
- The primary gate is MODQN retrained on V0.25. It is unmeasured.
- MODQN-BRIDGE found that 84 of the 112 legacy observation fields cannot be derived "without invention".
- Nothing in the narrative can currently be stated relative to the baseline.

---

## 6. What a reviewer would demand before accepting any version

1. **A strong reference for necessity.** Route-alone EE must be measured against `RSS_MAX`, the crowded construction and the retrained MODQN, not against BASE. A RANDOM row must be shown passing or failing the same test as a calibration.
2. **Trained single-route arms**, out of sample: a panel disjoint from the training anchors (CONVSCORE: anchors 022–092 are available), multiple worlds, converged schedule, seed-sign consistency. Include C1_ONLY, C2_ONLY and C3_ONLY in addition to the DROP arms.
3. **Declared primaries before results.** Either EE with a stated attainment floor as a constraint, which dissolves the Pareto language, or an owner-sealed amendment making rate attainment a co-primary, with a stated reason why a "synthetic setpoint" now counts as service.
4. **Evidence of a combined point.** At least one learned configuration that is non-dominated in (EE, attainment) and not reachable by any single route's argmax, out of sample, with the frontier of each single route drawn on the same axes.
5. **A mechanism audit tied to the energy account.** For each route, show its effect on PA joules, circuit plus baseband joules, spectral efficiency and airtime. Drop "bits side" if its gain is 70 % joules.
6. **A physical channel for the time side.** Either an H or S cell with interruption or standby cost, where persistence has an EE channel, or a closed-loop multi-step endpoint (C2TARGET's T1). Otherwise persistence is a constraint, not an EE route.
7. **Baseline ablations:**
   - MODQN with w₃ = 0;
   - MODQN with BC substituted for r3;
   - MODQN with a Dinkelbach-priced r1.

   Each gets the same budget, seeds and information as the Catfish arms, plus the frozen replay.
8. **A redefinition ledger.** Any change of C1 or C3 from their sealed meanings must be declared as a successor, with the sealed-C3 negative (no joint headroom) reported next to it.
9. **Robustness of the estimand.** Pooled ratio of sums *and* a per-anchor summary, with the sign agreement between them reported.
10. **A second numerator.** A demand-limited result, to show the energy side's advantage is not purely a full-buffer artefact.

## 7. What the narrative must not claim, on current evidence

- That any route, learned or oracle, has been shown to raise EE "on its own" against a meaningful reference.
- That the three routes correspond to three mechanisms of EE. There are two primitives, and the time side has no channel in the primary cell.
- That the 46.11/2.5 % versus 41.62/24.75 % pair is evidence about routes or about combination. It is two non-learned single-objective optima.
- That combining routes produces a trade-off. The trained evidence available shows dominance (Q1 v1) and substitution. The oracle shows override.
- That the method "reaches Pareto points no single route reaches". No such point has been produced.
- That the combination rule is "ratio-consistent" while the routes are also combined, unless the rule actually consumes the route outputs.
- Any comparison with MODQN. It is unmeasured on V0.25.
- That C3, renamed "energy side", passes the sealed C3 admission. It does not (no joint headroom).
- Any learned EE figure as generalisation. All learned figures are in-sample and unconverged.

## 8. What, if anything, survives

**Version A, supported now, learner-free: a diagnostic contribution.** On this physics and development panel:
1. EE gains from good configurations are dominated by the joules denominator.
2. Spreading load is EE-negative, so a MODQN-style load-balancing reward is anti-aligned with EE.
3. A fixed linear scalarisation B − ηE on a boundary-0 horizon mis-ranks configurations and descends from the EE-best rule at 9/12 anchors even at the corrected price.
4. The non-learned rules expose an EE-versus-rate-attainment frontier. Any EE claim must therefore be reported with attainment.

Each of these rests on primary, parity-checked, learner-free measurements. Each is falsifiable on other worlds. It is a narrower paper, but an honest one.

**Version B, a method *hypothesis*, not a result.**
- **Two physical levers as proposal generators:** link gain for power, and beam count for fixed and PA cost.
- **Selection:** by a *nominal*, deployable ratio-consistent score on the commitment horizon.
- **Persistence and rate attainment:** explicit constraints with pre-declared floors.
- **Necessity:** tested as "removing a generator lowers selected EE out of sample" against retrained MODQN, with and without r3.

This is close to what TRIOBJ's `ratio_consistent` rule and APPROACH Part 4 already point toward. It survives because it drops the three claims the evidence contradicts: three EE mechanisms, necessity against BASE, and a Pareto value of combination. It still needs every item in §6 (1, 2, 4, 7, 9) before it is a claim.

**The proposed narrative as stated does not survive:** three sides of EE, each necessary, combined for Pareto points under a Dinkelbach rule. It survives only if one presents the post hoc definition as a test, treats beating BASE as necessity, reads two hand-built configurations as evidence about learned routes, and calls dominance a trade-off.
