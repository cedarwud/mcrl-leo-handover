Written to `/home/sat/mcrl-v025-strategic-fable-ws/STRATEGIC-REVIEW-fable-2026-09-10.md`. Full text follows.

---

# Strategic review — fable, 2026-09-10

Read-only review. Nothing in the project was changed. Sources read: the afternoon controller findings, the stages 6–8 contract v1, the priority declaration and pilot-track declaration, the design freeze and closure rule, the contingency ladder, and the ORACLE / PREVALENCE / PSI-WITNESS / C1C2 / CERTPROFILE / COALGEN / CURVE / DATEPOOL reports.

---

## Q2 first, in one line

**The mechanism is the contribution. The learned coordinator is not, and on the evidence already in hand it is not going to become one on this timeline.**

---

## The reasoning that produces that

Three facts, all already measured, decide it.

**One. The learned interaction head currently loses to predicting zero.** At the full 6,765-label training partition, on the outcome the paper is about — realised pooled EE — the head gets 10.3098 Mbit/J against 10.3178 for `psi_hat = 0` and 10.3174 for a two-parameter size-only OLS. It has 14.4 % more mean regret than the constant. On size-2 candidates it trails both trivial baselines on every metric. On size 3+ it wins exact-best frequency by 3 points and still loses on regret and on EE, because its rare wrong choices cost more than the baselines' wrong choices. `CURVE` reads this as "still climbing, data-limited," and the slope is real. But the honest statement of the current position is not "underpowered." It is: *after the full corpus, the learned component is worse than a constant on the primary endpoint.*

**Two. The reason it loses is structural, not statistical.** `COALGEN` measured `|R3| > 1e-3` on **38.50 %** of 5,003 coalitions of size ≥ 3. The deployed model is a pairwise-conditioned interaction head. That is a measured misspecification, not a suspicion. Buying the extrapolated 51,000–93,000 labels buys data for a model form that has been proven unable to represent the target on more than a third of the support. And the extrapolation itself is a log-linear fit through three points, to a 60 %-exact-best target that the diagnostic chose for itself, extended 6–11× beyond observed range. `CURVE` says this plainly and the controller should take it at its word.

**Three. The same structural problem exists one layer down, and there it is a proof.** `C1C2` constructed two physically distinct actions with exact targets of opposite sign (+100/+300 vs −10/−30) that the production encoder maps to **byte-identical Q1 and Q2 vectors**. That is not a training failure and no quantity of labels or epochs touches it. The declared feature interface cannot represent the declared target. On the realised side, the size-100 replay had 8 of 10 total signs wrong and a +241.6 one-sided C2 bias. C1 flips 0–4 decisions out of 500 contexts depending on seed; one seed had zero disagreement on either arm.

Now stack the work required to make the learner a contribution: exact C1/C2 labels replacing the proxy path, a feature interface that resolves the collisions, an interaction model that is not pairwise, a new corpus at ~10× scale, retraining, then the 10 s budget question, then a panel that (see Frame D) cannot currently be allocated. That is not the remainder of this project. That is the next one.

Against that, the mechanism result is finished. It is verified in the production engine on four separate constructions with exact score identities and an executed interference control that isolates the cause. It is present at 30/30 real anchors with a 9.1 % median gain. Its ceiling over a *certified* unilateral optimum is +6.36 % with served count up, and it survives 18 combinations of the disputed circuit constant, being **larger** at 0 W — which retires the one objection that was aimed at its throat. It is counter-intuitive: the load-balancing mechanism, the one everybody expects, fired at 0 of 30 anchors. And critically, **it does not depend on the learner at all.** It is stronger without one, because it is not contingent on an architecture choice that a reviewer can dispute.

There is a sharper version of this that the controller should sit with. The C3 design — a permutation-invariant set-conditioned interaction head over coalitions — is the right architecture for a load-balancing and interference-relief story. The mechanism that actually fires is consolidation: a threshold on summed beam occupancy. A permutation-invariant coalition encoder is an extremely expensive way to learn a step function of a scalar sum, and the label distribution confirms it is a hard regime — `occupancy-activation` has 3,842 positive against 2,969 negative labels with mean −0.24 and mean-abs 1.20, i.e. near-zero-mean with heavy two-sided tails, exactly where a constant-zero predictor is hard to beat. **The architecture was chosen for a mechanism that does not fire.** That is the finding of the day, and it has not yet been allowed to propagate to the design.

---

## Q1 — Is the three-component ablation still the right design?

**No. Retire it.** Four reasons, in ascending order of severity.

**It decomposes the wrong thing.** C1/C2/C3 is a decomposition of the *learner's architecture*. The value ladder in the physics is: geometry-only carrier → exact joint objective evaluation of single-user moves → multi-user coordination. That is a decomposition you can measure exactly, today, with no learner and no ablation arms. The project has been treating an engineering module boundary as if it were a scientific one.

**One conjunct is already known to fail.** C1 changes 0, 2, or 4 decisions out of 500 production-row contexts across four seeds, and one seed shows zero disagreement for either C1 or C2. A component that pivots under 1 % of decisions cannot move pooled EE by +0.5 % with a lower bound above it. You do not need the panel to learn this; you have measured it. Running six arms × 16 seeds × ~160 dates to confirm a known negative is the most expensive way available to acquire information you already have.

**The conjunction is a self-inflicted multiplicity penalty.** The intersection–union structure means the single primary claim fails if any one of three contrasts misses. Declared power was ≈ 0.64 for the conjunction *assuming independence*, planning against Δ\* = +2 %, at 160 dates — and you do not have 160 dates (below). You have volunteered to fail. The reviewer objection this design was built to preempt — "you didn't show each part matters" — is not the objection a mechanism paper receives. The objection a mechanism paper receives is "is it real and does it generalise," and the answer to that is dates and worlds, not ablations.

**The proportions make the conjunction look worse than it is, and the +664 % is not usable.** `C1C2` §6 verified the baseline: across 6,000 cases the `nearest-eligible` carrier action was the best action *even within the already-truncated 9-item shortlist* **49 times — 0.817 %**, mean rank 8.255 of 9. The +664 % is the distance from a geometry-only, near-worst-ranked reference to an exact joint optimiser. Publishing it as a headline will read as inflation and will cost credibility on the +6.36 % that is the actual result. Report it once, with the rank statistics attached, and never as an achievement.

---

## Q3 — What I would stop

Named, with the reason each one cannot change what the paper can claim.

1. **The DROP_C1 and DROP_C2 neutral-source arms.** Effect measured at ~0.4 % decision pivotality for C1, on heads trained against proxy targets, one of which has the wrong sign. Cancel the arms, not just the interpretation.

2. **The acceptance-test remediation programme (T1/T2/T3 vacuity fixes).** T2's additive-placebo clause passes vacuously when both arms return the anchor; T1 rejects no wrong C1/C2 label generation; T3's evaluator hard-codes bits and energies by arm. These are real defects — in gates for a training run that should not happen. Fixing a gate on a cancelled run is pure cost. Record them in the register; do not repair them.

3. **The S_UNI two-arm engineering.** `CERTPROFILE` closed this. The budget-limited arm returns BASE at 90/90 by construction (non-anytime commit + a 2,748-solve first sweep). The certified arm needs up to 1,213 s, 91.55 % of it in irreducible exact oracle solves, and the report shows the engine admits **no valid pruning bound** because ACM hard thresholds break any Lipschitz enclosure. There is nothing left to engineer. Both facts are results — publish them (see Q4 item 5) and stop building.

4. **The label-budget expansion to 93,000.** See Q2, fact two.

5. **The CH5 sweep panels as currently framed** (70.6 projected core-hours, 8 named arm series). Panel F is explicitly degenerate — all arm curves coincide by construction, and the report says so. The arm-curve framing plots unvalidated learned arms. Keep panel B (circuit power 0.1 / 0.338 / 1.0 W) and panel E (architecture siblings) as **physics** sensitivities for the mechanism claim; drop the arm decomposition from all of them.

6. **The constant-provenance audit as a blocker.** The beamwidth attribution error is real and the sensitivity is large (endpoint moves to 0 or 13.08 Mbit/J), but it is a comment fix, a wording obligation, and one sensitivity figure. It does not touch +6.36 %, which is a ranking result invariant across the 18-point rescoring.

7. **Amending the contract.** Nine amendments and errata to the priority declaration in roughly 26 hours; a stages 6–8 contract at v1.2; a design-freeze-and-closure rule sealed at 02:18 that has itself been overtaken by the day's findings. The sealing discipline is genuinely good and has caught real things — the degenerate comparator, the proxy labels, the vacuous gates. But it is now producing artefacts faster than it retires uncertainty. **The freeze rule's own §5 is the right instrument: stop adding scope, run on the last audited configuration, report every unresolved item as a declared limitation.** Invoke it against the review loop itself.

---

## Q4 — The smallest credible result, if the learned components never work

There is one, it is good, and almost all of it is already measured.

**Title frame:** *Consolidation, not load balancing — coordination headroom for energy-efficient LEO handover under a rate target with equal-airtime multiplexing.*

**Contents, all in hand:**

1. **Mechanism.** Under a rate target with equal-airtime TDM and ACM, raising beam occupancy enlarges back-off room so that a lower-order mode clears its SINR threshold; adding load to a beam can make it servable. Four constructive witnesses in the production scoring path with exact score identities, and a reuse-colour control that drives Ψ to −5.9e−6 bits and isolates interference as necessary in mechanism 1.
2. **Prevalence.** Qualifying coalitions at 30/30 real anchors; median EE gain 9.118 %, range 4.156–22.756 %. Occupancy activation 28/30, complete beam evacuation 29/30, multi-aggressor relief **0/30**. 35.3 % of active beam-anchor incidences sit at occupancy 1 and 25.7 % at occupancy 2 — 61 % of active beams in the wasteful regime.
3. **Ceiling.** A perfect-knowledge bounded set selector beats an exhaustively certified unilateral optimum by **+6.359 %** pooled EE over 20 anchors, with served counts *up* (1,957 / 1,939 / 826), robust across 18 circuit-accounting combinations (+4.84 % to +6.59 %) and **larger at 0 W per chain**, which is the architecture an outside hardware review called fatal.
4. **Structure.** The interaction is a threshold on summed occupancy; the pairwise decomposition is measurably misspecified (|R3| > 1e−3 on 38.50 % of 5,003 coalitions).
5. **Unreachability — this is the result that makes the paper matter.** The certified unilateral comparator needs up to 1,213 s against a 10 s budget; 91.55 % is irreducible coupled-power solves; iteration counts are bimodal at {0, 46, 50, 80, 86, 86} with nothing between 1 and 45, so no realistic budget increase converts an anchor; and the engine admits no valid pruning certificate because ACM thresholds defeat enclosure. **Real headroom exists that exhaustive search cannot reach in budget.** That is the motivation for approximate coordination, stated as a measurement rather than an assumption.
6. **Negative result, reported as such.** A set-conditioned pairwise interaction head trained on the full exact-label corpus does not beat a constant-zero predictor on realised pooled EE, with (4) as the diagnosis. This is publishable and it is honest, and it is far better than a thin positive.

**The weakest point under review, named precisely: N.**

Every number above comes from one to four worlds, two dates, one constellation, 20–30 anchors. There is **no interval on +6.36 %**. A referee will ask for the distribution over geometries and you will have nothing. This is the thing that sinks the paper, and it is the cheapest thing on the board to fix: the ORACLE run was 694.6 s for 20 anchors on four processes, the whole diagnostic is **learner-free**, and therefore the entire train/eval date-boundary problem does not apply to it. Thirty dates × 20 anchors is on the order of single-digit core-hours. **If you do one more measurement, do this one.**

Secondary weak points, in order:

- **The +6.36 % is a headroom of a hand-built catalogue** (beam-occupant subsets, victim + top-k, complete evacuations), not of coordination in general. It is a valid lower bound; say so explicitly rather than letting a referee say it.
- **"Certified unilateral optimum" must not be called a ceiling.** Both adjudications already made this correction: an unlimited-compute fixed point reached by one greedy path is an arbitrary local optimum. The licensed wording is "not reachable by exhaustive single-user best response from the carrier anchor." Report the path dependence.
- **The +664 %.** Delete it as a headline; keep it once with the 0.817 % rank statistic attached.
- **The beamwidth.** `TX_FULL_HPBW_DEG = 3.32°` asserts a HOBS convention the source does not support. Fix the comment, present as a declared geometry, publish the 0 / 9.17 / 13.08 Mbit/J sensitivity.
- **The circuit constants.** Already handled correctly by v1.8's wording plus the 18-point sweep. Keep the wording obligation.

---

## Q5 — Frames not considered

Five. The first is the one I would act on tomorrow.

### A. The unit of analysis is the beam, and nobody has tried the obvious heuristic

Everything in this project is decomposed per-user and per-anchor, credited to C1/C2/C3. But the measured mechanism is a property of a **beam**: occupancy 1 or 2 is a transmitter burning fixed power for nothing, occupancy ≥ 3 activates a servable mode. Sixty-one percent of active beam-anchor incidences are in that wasteful regime. The natural policy object is not a coalition — it is a rule: *no beam operates below occupancy 3; consolidate or empty.*

**Has anyone measured what that one-line heuristic captures of the +6.36 %?** I can find no such measurement in the record. This is the single highest-information cheap experiment available and both outcomes are valuable:

- If a hand-written occupancy floor captures most of the headroom, that is a **better paper** than a neural coordinator — a physically motivated, deployable, sub-millisecond rule that beats an exhaustive unilateral optimiser — and it retires the learner question entirely.
- If it captures little, you have a rigorous argument that the coordination structure is genuinely non-trivial, which is exactly the setup a learned coordinator needs and which the project currently *asserts* rather than shows.

Right now the project cannot say which. That is a strange gap for a day spent auditing the learner.

### B. The objective may be the wrong one, and 0/30 is the tell

Pooled EE = ΣB/ΣE with QoS as non-inferiority *guards*. The load-balancing mechanism firing at 0 of 30 anchors should be read as information about the objective, not only about the physics: as posed, it has no per-user rate or fairness term with teeth, so the optimiser has no reason to spread load ever. A referee in this area will ask what consolidation does to worst-decile user rate and to handover churn, and "the guard was satisfied" is a weaker answer than a reported frontier. Consider making QoS an **outcome**: report the (pooled EE, worst-decile rate) frontier. Consolidation that improves both is a substantially stronger claim than consolidation that improves one subject to not-degrading the other — and the served counts (1,957 vs 1,939, and 30/30 anchors with served counts flat or rising) suggest you may already have the stronger version and are reporting the weaker one.

### C. The comparator should be the operating point, not the optimum

The project has been asking "does coordination beat the exhaustive unilateral optimum," which is a theory question you have now answered: yes, by 6.36 %, and the optimum costs 1,213 s. The question the 10 s budget actually supports is a **deployability** question, and it wants a different comparator set: carrier default; one-pass greedy unilateral within 10 s; occupancy-floor heuristic within 10 s; oracle. That frame uses `CERTPROFILE` as a load-bearing result rather than an obstacle, needs no learner, and is where the remaining headroom in the *paper* lives.

### D. The panel is infeasible as sealed — and this is independent of everything else the day was spent on

From `DATEPOOL`: the archive holds **166 TRAIN dates**. The design (contract D1 + v1.1) wants **≈160 claim dates**, two worlds each, six arms, sixteen seeds. Reserving 160 for evaluation leaves **at most six dates for training**. Removing the 24 used-or-reserved leaves 142 candidates; requiring the three-calendar-day separation that actually gives disjoint TLE filename windows leaves **87**. And 87 dates from a 390-day window of one constellation are not 87 independent draws of anything — the two-way pigeonhole bootstrap treats the date as the independent cluster, but the constellation is fixed and the geometry is correlated across nearby dates by construction.

The controller has spent the day optimising a learner for a panel that cannot be allocated. This is worth stating flatly because it is a *second, independent* argument for the same conclusion as Q2: **the mechanism claims are learner-free and therefore not subject to the train/eval date boundary at all.** Choosing the mechanism paper does not just avoid the learner's problems; it avoids the panel's.

### E. Replace the intersection with one primary and a reported decomposition

One primary claim, one interval, everything else descriptive. The intersection–union with three conjuncts is a structure that maximises the probability of concluding nothing, adopted to preempt an objection that a mechanism paper does not receive. If the primary becomes the mechanism ceiling with an interval over dates, the claim structure collapses to something a referee can actually evaluate, the power problem largely dissolves (the effect is 6.36 %, not 0.5 %), and the learned components move to where the evidence puts them: a reported negative with a diagnosed cause.

---

## What I would do, if it were mine

Tomorrow: (1) run the occupancy-floor heuristic against the oracle catalogue — Frame A; (2) run ORACLE over ~30 dates to put an interval on +6.36 % — Q4's weak point. Both are learner-free, both are hours not days, and between them they determine whether the paper's headline is "a simple physical rule captures most of a 6 % coordination headroom" or "a 6 % coordination headroom exists that neither exhaustive search nor a learned head can reach."

Either of those is a paper. The three-component ablation, at this point, is not.

One last thing, said plainly because you asked for blunt. The record shows an unusually disciplined project that has been wrong in a specific, repeating way: it keeps investing in the *governance* of a claim whose *substance* was drifting away underneath it. Nine declaration amendments, a freeze rule, a contingency ladder, three acceptance tests — while the thing being governed turned out to be trained on proxy labels with a wrong sign, compared against a comparator that returns the anchor 90 out of 90 times, and beaten by a constant. The audits that found all of that were excellent. Trust them one step further than has been comfortable today: they are not telling you the learner needs more work. They are telling you the learner is not the result.
