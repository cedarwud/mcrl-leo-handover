**The evidence supports no three-route claim: the strongest defensible claim is that informative per-user training (C1, with C2 acting as a partial substitute) makes the catalogue selector pick higher-EE whole-network profiles than neutral-source training on in-sample development anchors, while the interaction route C3 lowers EE in every learned run — the three routes are one misaligned scalar objective viewed three ways, and the structure that fits is a one-route method with an unresolved C2 and a negative C3 result, not three additive EE routes, and it has not yet been shown to beat a one-line max-RSS rule or the MODQN baseline.**

Status: COMPLETE · independent blind review · 2026-09-11 · development evidence only, nothing claim-grade

# BLIND — what claim structure does the evidence support?

## 0. How to read this review

**Evidence classes.** Each statement carries one of these tags:
- **[EST]** Established. A primary measurement report states it, and I checked it against the report body, or against code or contract text.
- **[SUG]** Suggested. The evidence points this way but does not settle it.
- **[INF]** My inference.

Every EE figure is pooled Σ decoded full-buffer bits / Σ modelled partial-payload joules, reported in Mbit/J. None of them is demand-capped (see §6.1). Each figure also carries its **reference**, its **information class** and its **panel**.

**Learner-free vs trained, in-sample vs out-of-sample.**
- **Learner-free.** These reports read no learner, run the physics, and use 12 development anchors unless stated otherwise:
  - STATICS2 (`STATIC-BASELINE-FAMILY-CLEANPATH`)
  - CROWDCOST, BEAMCAP, CEILING2, COORDVALUE, BASIN2, ETAFIX
  - C2TARGET (an exact-label oracle on 93 anchors)
  - The 12 anchors are only **4 distinct physical instants**: world 1, steps 0–3. The three carriers share the full-48 physical mapping (COORDVALUE §"Search budget"). They all come from one synthetic world on one date.
- **Trained.** These reports read 500-update checkpoints:
  - Z-VIEW-SCORING (16 seeds × 3 runs × 5 arms, 20 anchors = world 1 steps 0–6)
  - APPROACH (16 checkpoints)
  - INTERACTION-SCALE (24 checkpoints, on the separate R2 panel)
  - Q-ROW-COLLINEARITY (no EE)
- **Every trained-model EE number is in-sample.** CONVSCORE §1 verified 20/20 panel anchors as training anchors, row-for-row, for every run. The runs are also unconverged: the LR sweep, relayed in Z-VIEW §8 and design state U2, found no admissible learning rate at 500 updates. No out-of-sample EE measurement of any route exists.

**Reports used beyond the list I was given.** For these I read only the first-line summaries:
- `BASELINE-MODQN-REFERENCE` and `MODQN-BRIDGE`: gate status.
- `EXACT93-TRAINING`, `Q1-SCHEMA-V3/V4`, `RAW-DUP-CONTROL`, `C3-DECLARED-TARGET-LEARNABILITY`, `Q2-SCHEMA-V2-AND-RETEST`.

**Pending workspaces, not used.** `solo`, `triobj`, `c3reach`, `hcell` and `multistep` had **no report** as of 00:42 UTC. They contain only scripts, logs and a definitions file, and I did not treat partial logs as evidence.

**Not read.** I read no controller ruling, note or erratum. The design-state summary was read and treated as one party's interpretation. Two of its statements are contradicted by measurements (§6).

## 1. The strongest defensible claim

### 1.1 The claim, as a careful reviewer would accept it

> On one synthetic V0.25 world and date (development anchors, in-sample, 500-update unconverged heads), a bounded-catalogue selector whose per-user heads are trained on informative targets picks whole-network profiles with far higher pooled EE than the same selector trained on neutral targets. Informative-vs-neutral gives +10.7, +22.0 and +19.2 Mbit/J in the three runs, 16/16 seeds positive in each.
>
> The gain is not attributable route by route. It is carried by the immediate per-user view C1, for which C2 is a partial substitute. Replacing the interaction route's informative training with neutral training *raises* EE in all three runs.
>
> In learner-free terms, exact C1 scoring captures about 87% of the within-catalogue boundary-0-best EE improvement over the geometric carrier base. That improvement comes almost entirely from the catalogue's gain-ranked whole-network proposals. Exact C2 adds nothing measurable at the only endpoint that exists.
>
> No route, and not the full method, has been compared with the one-line `RSS_MAX` rule (41.62 Mbit/J on its 12-anchor panel) or with MODQN on a common, held-out panel.

That is the ceiling of what the record supports. It is a **development-stage, single-signal result with one negative result (C3) and one unresolved route (C2)**. It is not a three-route method result.

### 1.2 What supports each part

1. **Informative vs neutral: joint effect [EST, in-sample].** Z-VIEW §4 gives `FULL − ALL_NEUTRAL_CONTROL`:

   | run | Mbit/J | relative | seeds |
   |---|---:|---:|---:|
   | Q1 v1 | +10.719 | +48.2% | 16/16 |
   | Q1 v2 | +21.969 | +108.3% | 16/16 |
   | z view | +19.233 | +90.2% | 16/16 |

   - Reference: the same-checkpoint `ALL_NEUTRAL_CONTROL`. This is an unconverged zero-target selector, not a no-information knockout: it differs from the knockout at 20/20 anchors (Z-VIEW §3).
   - Information class: in-sample development panel, 20 anchors.
   - This is the only contrast that meets the contract's own survival reading, "combined deployed score improves EE" (V0.3 authoring contract §1). It meets it only in-sample, and the contract requires *held-out* EE.

2. **C3's informative training lowers EE [EST for direction, in-sample].** `FULL − DROP_C3`:

   | run | relative | seeds negative | status |
   |---|---:|---:|---|
   | Q1 v1 | −23.35% | 16/16 | sign-consistent |
   | Q1 v2 | −2.76% | 14/16 | sign flips |
   | z view | −5.26% | 15/16 | sign flips |

   `DROP_C3` (C1 and C2 informative, C3 neutral) is the highest-EE arm within its own panel in all three runs: 43.00, 43.46 and 42.81 Mbit/J.

3. **C1 carries the step-t signal and C2 substitutes for it [EST for the numbers, SUG for the reading].**
   - `FULL − DROP_C1` is positive pooled in all three runs: +7.56% (15/16), +42.92% (16/16), +3.45% (14/16).
   - `FULL − DROP_C2` swings with the C1 schema on identical labels: +22.83% (16/16), −2.65% (15/16 negative), +1.91% (13/16).
   - CONVSCORE §2 verified that all six corpora carry byte-identical exact C1, C2 and C3 labels. The C1↔C2 trade-off therefore cannot be a surrogate-label artefact.

4. **C1 learner-free [EST, 93 anchors, exact labels, no learner].** C2TARGET §2:

   | arm | EE |
   |---|---:|
   | `BASE` | 10.1469 |
   | `C1_ONLY` | 35.2347 |
   | `EE_B0_BEST` (within-catalogue ceiling) | 38.9767 |

   - Derived: (35.2347 − 10.1469) / (38.9767 − 10.1469) = **0.870** of the within-catalogue headroom.
   - The selected profile is one of the two `s0-top-two` whole-network proposals in 83/93 `C1_ONLY` picks and in 93/93 `EE_B0_BEST` picks.
   - I verified in code (`run_v025_matrix_probe.py`, `_selection_shortlist` and `_catalogue_with_census`) that these proposals are built by giving every user its best, or second-best, **non-incumbent option ranked by decision-instant nominal link margin**. That margin is monotone in nominal gain, so each proposal is a near-`RSS_MAX` profile.
   - **[INF]** Most of C1's oracle gain over `BASE` is therefore the catalogue's gain heuristic, with C1 acting as a near-binary switch between two heuristic profiles. C1's value beyond that heuristic is **unmeasured**. The discrete, repeated per-seed EE values in Z-VIEW point the same way (for example `DROP_C3` Q1 v2 = 43.413694 in 5 of 16 seeds): the learned arms choose among very few catalogue profiles.

5. **C2 learner-free [EST].**
   - Under the stage-C additive reading, exact C2 adds +0.68% relative to `C1_ONLY`. The 95% step-cluster interval is **[−3.60%, +5.73%]**. Where C2 changes the pick it is worse at 20 of 30 anchors, and the result is −2.10% on the 22-anchor subset.
   - Under the sealed tie-break reading (v1.6 §2, v1.9 §5) the effect is exactly 0, at 0/93 anchors changed.
   - The endpoint is single-step and open-loop, so C2's declared horizon value (t+1..t+3) is **unobservable**. It has not been measured and found absent; it cannot be seen at this endpoint (C2TARGET §2 "Reading").

## 2. The claim structure the evidence fits

### 2.1 Verdict

**One scalar objective, decomposed into three views.** Empirically:
- the immediate per-user view (C1) carries all the measurable EE value;
- the continuation view (C2) is null at the only available endpoint, and its declared value is untestable there;
- the interaction view (C3) is a negative result.
- At the learned, deployed level the views behave as **substitutes**, not complements: any two informative heads recover, or beat, the three-head system.

In the user's example vocabulary, this is closest to **"a one-route method plus negative results"**, with the C2 result recorded as *indeterminate / instrument missing* rather than negative. It is **not**:
- three additive routes;
- three distinct objectives with trade-offs;
- a two-route method. C2's positive leg is not established.

### 2.2 The candidate structures, and the evidence that decides each one

| candidate structure | verdict | deciding evidence |
|---|---|---|
| **Three routes that each add EE additively** | **Rejected** | (a) C3 lowers EE in 3/3 learned runs, and `DROP_C3` is the best arm in each. (b) C2's learned sign depends on the C1 schema, and its oracle value is null. (c) **Non-additivity** (derived from Z-VIEW §4): the sum of the three single-route marginals is −1.600 (Q1 v1), +10.342 (Q1 v2) and −0.136 (z) Mbit/J. The joint contrasts are +10.719, +21.969 and +19.233. The marginals sum to roughly zero or much less than the joint effect. Ratio arithmetic cannot turn +19 into −0.1. This is substitution. |
| **Genuinely distinct objectives with trade-offs** | **Rejected by definition** | Stages 6–8 contract v1 §B4: "C1(config) = Σᵢ∈A dᵢ; C3(config) = Ψ_A; identity C1 + C3 = F(a_A) − F(a⁰) exactly (KAT)". C2 is the continuation of the same F over three offsets. The V0.3 authoring contract §1 says the same thing: "training-time views of one physical counterfactual". There is one target metric and one scalar objective, so there is no second objective to trade against. The three-objective structure belongs to the **baseline MODQN** (r1 = EE, r2 = −Ψ, r3 = −U_{b_u}), not to the routes. |
| **Redundant estimators of one quantity** | **Partly supported, at deployment only** | Substitution at the deployed level is clear from the non-additivity above. The **labels are not redundant**, though: exact C1 and exact C2 per-user argmaxes agree on only 29.56% of 9,300 decisions, and their correlation is about 0.39–0.49 (C2TARGET §3). C3 is not an estimator of C1's quantity. It is the residual left after C1 (identity above). The accurate phrase is "complementary pieces of one objective whose learned heads act as substitutes at the selector". |
| **Two-route method (C1 + C2) plus a C3 negative result** | **Not supported yet** | C2's oracle marginal is null at the only endpoint. Its learned marginal is sign-consistent positive in one run (Q1 v1, 16/16), sign-flipping positive in another (z, 13/16) and negative in the third (Q1 v2, 15/16 negative). The sign follows the C1 schema, on identical labels. A two-route claim needs the multi-step endpoint (§3). |
| **One-route method (C1) plus C2 unresolved and C3 negative** | **Fits the evidence** | §1.2. Even this leg is measured only against `BASE` and against neutral-source training, never against `RSS_MAX` or MODQN. |

### 2.3 Why "each route raises EE" is not a property this design can promise, even with a perfect oracle

1. **The one objective does not rank pooled EE [EST, learner-free, 12 anchors].** ETAFIX §3 shows:
   - No single η makes the order of F = B − ηE (with or without Φ) match the pooled-EE order of the six clean arms. The minimum is one discordant pair, never zero.
   - Dinkelbach converges to η* = 41.6216 Mbit/J. At η*, first-improvement on F from `RSS_MAX` still lowers EE at 9/12 anchors.

   BASIN2 shows first-improvement on F from `RSS_MAX` descends 41.62 → 31.81 Mbit/J at 1200/1200 served. COORDVALUE shows the deployed F rejects 3,671 service-guarded EE improvements and accepts 24,278 EE decreases (36.5% sign disagreement). Its best rejected gain, +7.85 Mbit/J, is a sampled lower bound.

   Every route target is defined in F units. So **an oracle-perfect route can still select a lower-EE profile.** C2TARGET is exactly this: an exact C2 picks the lower-EE whole-network proposal in 20 of 30 changed anchors.
2. **C3 is a reference-dependent residual [EST].** Ψ_A is defined relative to a⁰. In BASIN2 Part 4, the sign of the historical exact interaction marginal depends on the reference profile: pooled −0.527 Mbit/J around `BASE` and −0.0014 around `RSS_MAX`, over 4 cells. A route whose sign changes with the reference cannot carry an unconditional "raises EE" claim.
3. **Pooled EE is a ratio of sums [derived].** Route ablation contrasts on a ratio are well defined, but they do not add up to the joint effect. The owner's requirement is a set of three separate contrasts, and they must be reported that way, never as shares of one gain.

### 2.4 Physics that bears on C3's prospects [EST, learner-free, 12 anchors; INF where marked]

- **No coordination barrier.**
  - k = 1 F-improving moves exist from `BASE` toward `RSS_MAX` at 12/12 anchors (BASIN2).
  - k = 1 EE-improving moves exist from `RSS_MAX` and from the crowded endpoint at 12/12 anchors (COORDVALUE; k = 1 is exhaustive).
- **The F-defined coordination headroom is small.**
  - Clean PANELCEIL coordination ceiling: +0.844% over the clean fixed point.
  - Nested production-shaped support: +0.338%. It is already saturated at `|A| ≤ 1 +` evacuations and flat through `|A| ≤ 6` (CEILING2).
  - The catalogue best around `RSS_MAX` adds +0.072 Mbit/J, about +0.17% (BASIN2).
- **The catalogue cannot express the multi-user moves that do raise EE.** It contains 0 of the 5,814 sampled EE-improving multi-user moves from good starts (COORDVALUE Part 3). **[INF]** The large multi-user EE gains found from `RSS_MAX` (up to +7.85 Mbit/J at k = 8) are "top-single combinations". Nothing shows they are *non-additive*, which is what Ψ would have to capture. What blocks them is objective alignment and reachability, not an interaction term.
- **Exact Ψ is decision-relevant [EST] with unmeasured EE sign.** It flips the additive argmax in 100/480 decisions on 11/20 anchors (INTERACTION-SCALE, R2 panel). The flips concentrate at step-3 anchors, where additive gaps are small. Their EE sign was not measured.
- **EE on this physics rises with beam concentration.** CROWDCOST: every adjacent slope over 8–98 active beams is negative. The only exception is a controlled N = 2 case. The EE-best construction is a partial-service operating point (2.5% rate-target attainment, BEAMCAP). **[INF]** Any set-level route that reduces load would push against EE here. The baseline MODQN's r3 = −U_{b_u} load-balance term is anti-EE on V0.25 physics, and CROWDCOST Part 4 says so explicitly.

## 3. Missing evidence, and the one measurement that would most change the answer

### 3.1 What the strongest (three-route) claim would need, none of which exists

1. **Held-out scoring.** Every learned EE number is in-sample (CONVSCORE). A panel on development anchors outside 000–021 (for example 022–092), and ultimately the unopened evaluation dates, is required.
2. **Converged heads.** The exact22, Q1 v3 and v3-control 4,000-update runs were 4–5/16 seeds complete at 00:04 UTC, so none has been scored. Even once scored, their panels overlap training 20/20.
3. **A common reference panel.** `RSS_MAX` (41.62), the clean fixed point (31.03) and the crowded endpoint (46.11) were measured on the 12-anchor panel. The learned arms were measured on a different 20-anchor panel, and the C1/C2 oracle on 93 anchors. **No learned arm and no oracle arm has ever been scored beside `RSS_MAX` on the same anchors.**
4. **The MODQN gate.** It is unmeasured. MODQN-BRIDGE found 84 of the 112 legacy state fields missing without invention, so the primary gate declared on 2026-09-10 is not yet constructible.
5. **An oracle C3 marginal in pooled EE on the 93 anchors.** This is exact C1 + exact Ψ, i.e. argmax of exact ΔF, against `C1_ONLY`, the counterpart of C2TARGET for C3. Only BASIN2's four-cell historical estimator exists.
6. **A multi-step realised continuation endpoint (T1 in C2TARGET §4c).** It is the only instrument on which C2's declared value is observable. `mcrl-v025-multistep-ws` is building it and has no report yet.
7. **Robustness of the numerator.** Every measurement uses the full-buffer numerator required by sealed declaration v1.8 item 5. The design-state summary says all efficiency "now uses the demand-capped numerator". No demand-capped EE exists for any arm, and the EE-best points are partial-service points, so the ranking could move.
8. **Sample breadth.** The physics diagnostics rest on 4 physical instants of one world. The learned panel is 7 steps of one world on one date. The 93-anchor oracle is 31 decision instants over 2 worlds.
9. **Closed loop.** Every endpoint is open-loop and single-step. v1.2 amendment item 3 says the only admissible learned claims are closed-loop EE under model mismatch, equal quality at lower measured compute, or a measured residual task. None of the three has been measured.

### 3.2 The single measurement that would most change the answer

**A learner-free, same-endpoint comparison on the 93-anchor exact set.** The arms: `C1_ONLY`, exact `C1 + Ψ` (argmax exact ΔF), and "always take the catalogue's `s0` rank-0 gain-ranked proposal", scored next to `RSS_MAX`, with the existing C2TARGET harness and evaluator rule.

Why this one:
- It tests the **only positive leg** of the current answer. If `C1_ONLY` does not beat `RSS_MAX` or the unconditional `s0` proposal by a margin outside its step-cluster interval, no route has shown EE value beyond a one-line heuristic that uses less information. The answer would fall from "one-route method plus negative results" to "a negative result with a diagnostic contribution".
- The same run gives C3's oracle EE marginal (item 5) at no extra cost.
- It needs no training, only the harness C2TARGET already ran in 7–10 s per anchor.
- It also tests my inference in §1.2(4): that the learned arms' repeated levels near 43 Mbit/J are the catalogue's near-`RSS_MAX` proposal rather than learned value.

The measurement that could move the structure **upward**, towards a two-route method plus a C3 negative, is the multi-step endpoint of item 6. It must be a pre-declared oracle C2 marginal on t+1..t+3 with a step-cluster interval, run before any learned C2 is scored.

## 4. What the project must not claim

1. **That each of C1, C2 and C3 raises EE.** C3 lowers EE in 3/3 learned runs. C2 is null as an oracle and schema-dependent when learned. This is the owner's standing requirement, and the evidence contradicts it for C3 and does not support it for C2.
2. **Any three-way split of the method's EE gain,** or any statement that the routes "each contribute" to `FULL − ALL_NEUTRAL`. The single-route marginals sum to about zero while the joint effect is +10 to +22 Mbit/J.
3. **That C3 captures coordination value, or that joint moves are needed.** There is no barrier, the F-defined ceiling is below 1%, and the learned C3 is harmful. Also, under contract C6, a C3 that turns positive only after catalogue or feature changes (for example APPROACH's proposal to add an `RSS_MAX` row) must **not** be presented as confirmatory. The contract forbids iterating features, catalogues, sources or regimes "until C3 becomes positive".
4. **That C2 delivers persistence or horizon value.** The learned C2 marginals (+22.8% here, and the published +27.9%) were measured on an open-loop single-step endpoint, so they can only be step-t effects.
5. **Any generalisation or claim-grade EE.** All learned numbers are in-sample and unconverged, on development anchors from one world and one date. The evaluation-only dates are unread.
6. **That the method beats MODQN** (unmeasured) **or non-learned rules** (never compared on a common panel). Also not the design-state motivation that learning is needed to reach the search's fixed point inside the deadline. `RSS_MAX` needs no search and beats the clean fixed point by 34.1% (STATICS2), and the fixed point itself is a local optimum of a misaligned F (BASIN2).
7. **That F = B − η_ref·E − Φ is an EE objective,** or that re-pricing η repairs it. ETAFIX shows no η orders the arms by EE, and the per-anchor descent survives at η*.
8. **That any route is dead or alive** on these 500-update runs, or anything about converged behaviour.
9. **EE under a demand-capped numerator, or at constellation scope.** Neither has been measured, and v1.8 item 4 says omitted common energy does not cancel. EE must not be reported without rate-target attainment beside it: the EE-best points reach 2.5–28.5% attainment.
10. **The contaminated reference axes.** This covers the F8 "arm / certified fixed point" ratios (the 12.947 Mbit/J fixed point), the published 13.430 fixed-point figure and the "3.099×" comparison. The +1.94% and +0.905% ceilings are also superseded by CEILING2's clean values.
11. **Physics statements the measurements refuted.** "Per-beam power is a max over served users" is refuted for the `a-r0` path, which uses TDM time-averaging (CROWDCOST Part 1). "PA is 94.8% of system power" holds only at the crowded endpoint; the range is 90.8–94.9%. Both appear as stable facts in the design-state summary.
12. **That load balancing helps EE on this physics.** The measured slope is the opposite.

## 5. Literature: what I could and could not ground

- **Fractional programming / Dinkelbach (1967, *Management Science* 13(7)).** For max B(x)/E(x) with E > 0, the ratio optimum maximises B − λ*E with λ* equal to the optimal ratio. A fixed λ ≠ λ* generally has a different maximiser.
  - *Citation from memory, not re-checked against the source in this review.*
  - The identity the argument needs, F(x; EE(s)) − F(s; EE(s)) = E(x)·(EE(x) − EE(s)), I re-derived by hand, and ETAFIX §4 verified it numerically.
  - Consequence for the claim: a route target defined by a frozen-η linear score is not an EE target except at η*. ETAFIX shows that even η* fails per anchor, because anchor EEs span 19.8–71.8 Mbit/J.
  - Zappone & Jorswieck's fractional-programming monograph for wireless EE (Foundations and Trends, 2015) is the standard reference. *Unverified here.*
- **Multi-objective RL and linear scalarisation limits.** Examples are Vamplew et al. on scalarisation and Pareto fronts, and the Roijers et al. 2013 JAIR survey. *From memory, unverified.* They bear on the **baseline MODQN's** three distinct rewards, not on the routes: the routes are a single objective (§2.2), so MORL trade-off framing does not apply to them.
- **Calvo-Fullana et al. 2023, Prop. 1**, cited in project records. *I did not read it; unverified.*
- **Interaction decompositions (main effects plus residual, Harsanyi/Shapley style) depend on the reference point.** I state this as a general property. *Citation unverified.* It is **verified in the project's own evidence**: BASIN2 Part 4 shows the C3 sign changes with the reference.
- **3GPP TR 38.821 user-per-beam figures** were used by BEAMCAP from local copies. *I did not verify them.*

## 6. Discrepancies found while reading (all verified against primary text)

1. **Numerator.** Design state §3 says every reported EE uses the demand-capped numerator. Sealed declaration v1.8 item 5, and every measurement report above, say the numerator is full-buffer with "no demand cap". The measurements are what they say they are, so the design-state sentence is wrong about the current record, or states an intention nobody has implemented. Any paper claim must name the numerator it uses.
2. **Per-beam power law.** Design state §1 and §U5 attribute the concentration benefit to "per-beam power is a max over served users". CROWDCOST Part 1 refutes this for the measured `a-r0` path, which uses TDM slot time-averaging. The concentration benefit itself is real and is measured directly.
3. **"Surrogate labels".** Z-VIEW §8 says the heads were trained on surrogate labels. CONVSCORE §2 verified byte-identical exact C1, C2 and C3 labels across all six corpora, and a runner that reads those fields. I side with CONVSCORE: it checked bytes, while Z-VIEW relayed a figure that compares the exact labels against the sealed fallback.
4. **Survival criterion.** The contract says the combined score must improve held-out EE (V0.3 authoring contract §1). The owner requires that each route improve EE. These are different claims.
   - The in-sample evidence meets the contract's reading against neutral-source training, and would meet it better without informative C3.
   - The evidence fails the owner's reading for C3.
   - Neither reading has held-out evidence.

## 7. Evidence classification summary

| statement | class | learner-free / trained | in / out of sample |
|---|---|---|---|
| Routes are one objective (C1 + C3 = ΔF; C2 is F's continuation) | EST (contract text) | definitional | n/a |
| F misranks pooled EE for every η | EST | learner-free, 12 anchors | n/a |
| No coordination barrier; F-coordination ceiling below 1% | EST | learner-free, 12 anchors | n/a |
| Exact C1 captures 87% of within-catalogue headroom over `BASE`, mostly via gain-ranked proposals | EST (numbers), INF (attribution) | learner-free, 93 anchors | n/a |
| Exact C2: +0.68% [−3.60, +5.73] additive; 0 under tie-break | EST | learner-free, 93 anchors | n/a |
| Informative vs neutral training: +10.7 / +22.0 / +19.2 Mbit/J, 16/16 each | EST | trained, 500 updates | **in-sample** |
| Learned C3 lowers EE (3/3 runs; sign-consistent in 1) | EST | trained | **in-sample** |
| Route marginals are substitutes, not additive | EST (arithmetic), SUG (interpretation) | trained | **in-sample** |
| Learned arms pick among a few near-`RSS_MAX` catalogue profiles | INF | trained plus code reading | in-sample |
| Method vs `RSS_MAX` / MODQN | **unmeasured** | — | — |
