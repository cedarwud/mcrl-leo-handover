**REVISE before real source generation.** The amendments improve the oracle experiment, but v0 does not yet define a falsifiable learned-C3 intervention or demonstrate adequate power.

`git pull` returned “Already up to date.” I read the requested documents, the referenced stage-4 requirements and statistical erratum, and inspected the legacy trainer/orchestrator. This was a read-only review with independent numerical power calculations; I did not execute successor training.

**A. The information sets remain incompletely specified.**

Let \(b^-_{-i,t}\) denote the previous committed served set, excluding user \(i\), projected to decision time \(t\). Let \(L_{i,t}\) be that user’s candidate table and legal mask, with its physical-action mapping.

The most specific reconstruction supported by v0 is:

\[
I_{\mathrm{heads},i,t}
=\sigma\!\left(L_{i,t},X^1_{i,t},X^2_{i,t};
\text{frozen schemas, scales, prices}\right).
\]

Q1 and Q2 receive their respective inputs; this notation does **not** imply that either head receives every other user’s rows.

| Input | Declared contents |
|---|---|
| \(X^1_{i,t}\), per candidate | Nominal rate-target SINR margin; required power/cap; mode SE; occupancy excluding focal; beam/satellite activation before insertion; off-axis angle; remaining D2/visibility time; refresh phase |
| Q1 history | Previous served association one-hot; previous served candidate loads; previous beam/satellite activity; previous beam maximum RF/cap; `missing_incumbent` |
| \(X^2_{i,t}\), per candidate | Incumbent nominal decoding margin; forecast SE trend; remaining D2/visibility time; refresh phase; background occupancy; beam/satellite activation; required-power cap margin |
| Q2 continuation | For each of three offsets: validity, focal survival, minimum decoding margin, mean ACM SE; plus `missing_incumbent` |

Q2’s background is explicitly \(b^-_{-i,t}\). Q1’s nominal background computation, candidate-versus-incumbent margin semantics, physical-identity encoding and final scales are not completely frozen. Thus **an exact executable \(I_{\mathrm{heads}}\) cannot honestly be recovered from v0**. The deferred schema is substantive, not clerical. [Contract, items 2–3](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md:7)

For an exact coordinator, the implied interface is approximately:

\[
I_{\mathrm{coordinator},t}
=\sigma\!\left(
G_t^{\rm nominal},\{L_{i,t}\}_i,b^-_t,H_t,
\text{demands, capacities, inventory, prices},
a^0_t,\mathcal C_t,\mathcal M_{\rm nominal}
\right),
\]

where \(G_t^{\rm nominal}\) includes all required direct and beam-specific cross gains, \(a^0_t\) is the reference proposal, and \(\mathcal C_t\) contains complete candidate profiles. It computes, for each profile, joint occupancy, resource sharing, coupled powers/interference, activation, nominal service, bits, energy and forecasts.

These computations do not create new information relative to complete global primitives. They **do** expose information and perform reasoning unavailable from the compressed unilateral rows. The learned S3 input interface remains unspecified. [Capability requirement](/home/sat/mcrl-hub/.scratch/multi-catfish-v023-controller-handoff-20260907/prompts/codex-sol-v025-engine-stage4.md:43)

Consequently, a positive FULL−DROP_C3 currently identifies neither interaction value nor learned coordination.

The necessary equalisation is between experimental arms—not necessarily identical architectures for heads and coordinator:

- Freeze common primitive access, observation timestamps, forecast method and physical identities. Distinguish observed telemetry, nominal counterfactual calculations and realised outcomes.
- Name \(a^0_t\) precisely. The mathematical reference proposal and the previous committed association used for handover accounting are different objects.
- Keep the same catalogue construction, joint search, guards, tie-breaking, validation, deadline and fallback across FULL and DROP_C3. At matched anchors, authenticate identical catalogues; any learned pruning must be declared as part of the intervention.
- Prevent an exact evaluator from silently restoring the removed score through ranking, pruning or a score-dependent “guard.”
- Evaluate information-matched \(S_{\rm UNI}\) and matched \(S0\), with computation costs included.

The admissible claim is conditional: frozen successor heads and interfaces; joint selection improves held-out pooled EE over DROP_C3 and exact unilateral selection; QoS passes; decision-relevant nonadditivity exists. Additional **learning** value requires comparison with S0; matching S0 faster supports acceleration.

A zero residual marginal must remove the demonstrated C3 contribution under that scope. A wide interval means inconclusive evidence; a narrow interval excluding worthwhile gains is informative evidence of redundancy. Neither permits changing features, catalogues or regimes until C3 becomes positive. [Falsifiable attribution wording](/home/sat/mcrl-v023-astra-attribution/ADJUDICATION-C3S-ATTRIBUTION-CODEX-GPT6-ASTRA-2026-09-08.md:74)

**B. Q1+Q2 estimates a supervised surrogate, not the deployed policy’s Bellman value.**

The inspected legacy losses have the form

\[
L_k(q_k)=
\mathbb E_{\widehat P_k}
\left[
(q_k(X_k,a)-q_k(X_k,r)-Y_k)^2
+\beta_k q_k(X_k,r)^2
\right].
\]

C1 converts surplus bits to bits/\(\kappa\); C2 consumes an already normalised target. There is no next-state value. [Actual trainer](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:239)

Therefore:

- Each head fits a regularised projection of source target differences under its source-row distribution.
- With sufficient capacity and consistent targets, differences approximate conditional mean target differences given that head’s information.
- Q1+Q2 combines immediate nominal surplus/Φ and the declared finite-horizon continuation surrogate. With different input sets, it is not automatically the conditional expectation of their sum given all available information.
- Repeated deterministic epochs add optimisation, not independent physical evidence.
- Zero bootstrap correctly removes the incompatible-head bootstrap problem. It does not establish long-horizon value learning, policy consistency or optimality for pooled EE.

The per-user argmax is a deployable **proposal policy**. It maximises the additive surrogate over a Cartesian action space only when constraints factorise. Joint feasibility, coordination, repair and fallback change the executed policy.

The contract must define the actual learned score, for example

\[
S_\theta(a)=
\sum_i\!\left[
q_{1i}(a_i)-q_{1i}(a_i^0)
+q_{2i}(a_i)-q_{2i}(a_i^0)
\right]
+g_\theta(I_{\mathrm{coordinator}},a,a^0),
\]

followed by the complete catalogue/guard/deadline/commit algorithm. Closed-loop evaluation then tests that algorithm empirically; low regression loss does not validate its EE claim.

**C3’s training signal requires joint counterfactuals.** For fixed context and reference,

\[
d_i=F(a_i,a^0_{-i})-F(a^0),\qquad
\Psi_A=F(a_A,a^0_{-A})-F(a^0)-\sum_{i\in A}d_i.
\]

Pair labels require matching \(00/10/01/11\) evaluations. General Shapley shares require the interaction game on relevant subsets.

A row keyed only by `(anchor,user,action)` is insufficient: the same action can have different interaction shares depending on its partners and their actions. Marginalising omitted partners learns an average over the source partner distribution; taking the best partner learns credit potentially unavailable in the executed set.

Per-user storage is possible **if each row carries the complete conditional coalition context**. Otherwise train a scalar set predictor on `(anchor,reference,complete profile,context,Ψ/κ)`. Specify the loss, sampling weights, coalition support and deployment aggregation. The legacy C3 route already requires structured anchor surfaces; it is not interchangeable with the Q1/Q2 batch contract. [Legacy C3 update](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:355)

Two further blockers:

- **“Learned S3 or exact S0” is not one learner contract.** If S0 ignores trained C3, FULL and DROP_C3 source retraining cannot change its decisions with other inputs fixed. Removing \(\Psi\) from S0 instead changes the intervention to an oracle factor ablation.
- **v1.5’s reconstruction identity omits Φ.** With \(C1=\sum d_i+\Phi_{\rm signed}\), the identity is \(C1+C3=\Delta F+\Phi_{\rm signed}\). Alternatively state the physical identity using \(C1_{\rm physical}\). Both identities need separate tests. [Amendment](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md:6)

**C. Neutral-source substitution has a valid, narrower estimand.**

Let \(T_z(s)\) train the complete retained architecture with source configuration \(z\), and let \(\pi_z(s)\) include its full deployed controller. Conditional on the frozen source corpus and protocol,

\[
\rho_z=\frac{\mathbb E_{W,s}[B(\pi_z(s),W)]}
{\mathbb E_{W,s}[E(\pi_z(s),W)]},\qquad
\Delta_x^{\rm source}
=\frac{\rho_{\rm informed,informed,informed}}
{\rho_{\text{route }x\text{ neutral; others informed}}}-1.
\]

This measures the benefit of the specified informative source treatment relative to the specified neutral source treatment.

It does **not** measure removal of component \(x\), removal of its physical information, or a decomposition of total gain.

The orchestrator retains and updates every route. Legacy C1/C2 neutral sources change example selection while retaining the physical learning task. Shared load, power, activation and forecast features can retain component-relevant information. [Source mapping](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py:52), [neutral construction](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-neutral-adapters/README.md:14)

That is not a confound for the narrowly stated source estimand. It is a confound for the stronger component-removal interpretation. Positive gains may reflect useful example coverage; zero gains may mean neutral examples teach the same function.

Seal each neutral generator, labels, support, strata, overlap, row weights and optimisation dose. “Identical source batches across arms” must mean identical batches **within a given route/source identity**, not identical informed and neutral examples.

**Yes: retain checkpoint knockouts as a secondary experiment**, as v1.5 requests. Zero the named score contribution while keeping the decision machinery fixed. This measures deployment reliance and exposes hidden score restoration. It does not replace retrained ablations; a stronger component-inclusion claim also needs retraining with that contribution explicitly absent.

**D. Five seeds and 161 dates are not a demonstrated powered design.**

The later erratum already settles the rule: relative EE gain, with the lower endpoint of a central 95% percentile interval strictly above 0.5%. Those are no longer unresolved ambiguities. [v1.4](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.4-ERRATUM-2026-09-08.md:5)

**At a true gain of exactly 0.5%, no finite sample gives 80% probability of clearing a valid 0.5% lower-bound rule.** That is the null boundary. A planning alternative \(\Delta_*>0.005\) is essential.

Using the review’s 3/5/10% SD assumptions, central-95% lower bound and 80% power per contrast,

\[
n\approx
\left[
\frac{(1.960+0.842)\sigma}
{\log(1+\Delta_*)-\log(1.005)}
\right]^2.
\]

These are normal-approximation counts of independent paired clusters, before adding another variance component:

| Paired cluster SD | Detect 0.5% over zero¹ | True 1% over 0.5% | True 2% over 0.5% | True 3% over 0.5% |
|---|---:|---:|---:|---:|
| 3% | 284 | 287 | 33 | 12 |
| 5% | 789 | 797 | 90 | 33 |
| 10% | 3,156 | 3,187 | 358 | 131 |

¹A different, weaker hypothesis test—not the sealed claim.

The crossed design instead requires approximately

\[
\operatorname{Var}(\widehat{\log(\rho_F/\rho_D)})
=
\frac{\sigma_d^2}{D}
+\frac{\sigma_s^2}{S}
+\frac{\sigma_{ds}^2}{DS},
\]

using variance components of the paired pooled-ratio influence function. The table’s SDs do not tell us how variance splits between these terms. [Review’s planning assumptions](/home/sat/mcrl-v023-astra-first-principles/FIRST-PRINCIPLES-REVIEW-CODEX-GPT6-ASTRA-2026-09-08.md:104)

For a true 1% gain:

- Even with **zero seed variance**, 161 dates give approximately **56%, 24%, 9%** power at date SDs of 3%, 5%, 10%.
- Even with unlimited dates, seed SDs of **0.5%, 1%, 2%** require at least **8, 32, 128 seeds**, respectively, under the optimistic normal approximation.
- The separate date and seed minima cannot simply be combined: both consume the same variance budget.

Two-way pigeonhole resampling is the appropriate structural correction: independently resample date and seed levels, apply their product weights to cells, pair all arms and recompute pooled B/E. It does not manufacture additional seeds or guarantee calibrated percentile coverage with five seeds. The foundational results are for crossed structures under stated conditions, not a universal small-sample guarantee. [Owen](https://arxiv.org/abs/0712.1111), [Owen–Eckles](https://arxiv.org/abs/1106.2125)

**The minimal repair depends on the declared alternative and measured variance components.** Concrete planning examples, assuming negligible interaction residual:

| Assumptions | Approximate sufficient allocation |
|---|---|
| True gain 2%; date SD 5%; seed SD 1%; 80% per EE contrast | **161 dates × 9 seeds** |
| Same assumptions; ≥80% probability all three EE tests pass, using a conservative failure-probability bound | **161 dates × 36 seeds** |
| True gain 1%; date SD 3%; seed SD 1%; 80% per EE contrast | **572 dates × 64 seeds** |
| Same 1% assumptions; ≥80% EE-conjunction probability by that bound | **876 dates × 98 seeds** |

These are planning examples, not guarantees for the actual bootstrap or QoS conjunction. QoS gates require their own power assumptions and joint simulation.

Thus adding seeds alone cannot rescue a 1% alternative at the stated date SDs. More worlds on the same dates cannot remove the date-effect floor. If additional dates are unavailable, the honest options are a larger detectable alternative, demonstrated lower variance, or a narrower finite-panel claim.

The intersection–union argument correctly avoids Bonferroni inflation for the single conjunction. **It does not make 80% per-contrast power equal 80% global power.**

**E. A central controller could implement the architecture, but the contract does not yet establish deployability.**

Four operational declarations are necessary:

- **Causal inputs.** v1.5 explicitly permits future-epoch TLE selection and calls it non-causal. That benchmark convention cannot substantiate literal online deployability. A deployable variant must use information available by decision time and propagate forecasts from it; restricting the forecast horizon alone does not ensure this.
- **Action effective time.** State observed at \(t\), computation lasting up to 30.08 s, and an action credited from \(t\) are incompatible without an explicit advance-planning convention. Account for the action held during computation, communication delay and actual commit time.
- **Guaranteed fallback.** Compute and validate BASE early; reserve time for cancellation, validation and transmission. Define behavior when BASE is itself jointly illegal or stale. A timer checked only after a solver returns cannot enforce the deadline.
- **Concrete capability manifest.** Identify telemetry sources/ages, complete roster and cross-gain coverage, model assumptions, worker hardware/count, catalogue bounds, solver limits, memory, missing-data handling and measured end-to-end latency.

The stated target of 0.02 s per row still permits **64 s for 3,200 rows**, before other work, on serial execution. Vectorisation or parallelism may solve this; a declared performance target is not a timing result. [Compute requirement](/home/sat/mcrl-hub/.scratch/multi-catfish-v023-controller-handoff-20260907/prompts/codex-sol-v025-engine-stage4.md:38)

Exact Shapley labels for an \(m\)-user evacuation can require \(2^m\) subset evaluations. A bounded action catalogue does not bound this cost. Cap coalition size, declare an approximation, or train scalar set residuals. Online S0 need not compute Shapley allocations at all.

Finally, “all label dependencies are visible on the tape” is weaker than deployment observability. Realised future outcomes may be supervised targets for an explicitly defined expectation; they cannot become current features or nominal forecast inputs.

**F. Demand these three decisive synthetic tests before real source generation.**

1. **Information twins, interaction reversal and additive placebo.**  
   Construct contexts with identical Q1/Q2 inputs and unilateral values, but an observable joint-context variable controlling this independently specified payoff table:

   | Context | \(F_{00}\) | \(F_{10}\) | \(F_{01}\) | \(F_{11}\) | \(\Psi\) | Optimum |
   |---|---:|---:|---:|---:|---:|---|
   | Synergy | 0 | −1 | −1 | 2 | 4 | 11 |
   | Collision | 0 | −1 | −1 | −4 | −2 | 00 |
   | Additive | 0 | −1 | −1 | −2 | 0 | 00 |

   Run the actual builder→training→deployment path. S3 must distinguish the first two using declared context; removing that context must expose the representation failure. Poison future observations and hidden legacy state: current features/actions must remain invariant. Add a dummy third user and verify interaction shares \((\Psi/2,\Psi/2,0)\). Require exact additive equality for oracle/knockout controls and no systematic learned C3 gain within a predeclared tolerance.

2. **Training intervention through atomic execution.**  
   Use a hand-computed, multi-step fixture with separately decisive C1, C2 and C3 terms, nonzero Φ, and individually legal but jointly infeasible proposals. Verify actual pair-loss targets/gauges/scales, selected-set credit, immediate-versus-continuation accounting and both reconstruction identities. Trace informative and neutral batches into updates; unchanged routes must remain identical under the isolated deterministic design. Show source substitution and score knockout produce their separately predicted interventions. Force slow solving, stale/invalid proposals and empty candidate sets; require timely legal fallback and independently reconciled committed actions, event ledger, B/E and QoS receipts.

3. **Crossed-cluster inference through the real merger.**  
   Generate raw unequal-energy/opportunity receipts with known date, seed and interaction effects, covering the 3/5/10% SD scenarios. Include repeated worlds per cell, zero-bit positive-energy cells and genuinely undefined denominators. Exercise the actual product-weight bootstrap and terminal rule. Test least-favourable nulls—one component at the 0.5% boundary while others pass—not merely an easy all-zero null. Across predeclared Monte Carlo repetitions, check coverage/type-I error with binomial tolerances, ≥80% power for the chosen **complete** claim, and failure when any QoS margin fails. Repeated seeds/dates must not count as new independent replication; altered summaries must fail raw-row reaggregation.

VERDICT: CONTRACT=REVISE:information interfaces, S3/S0 intervention, coalition training schema, Φ identity, neutral-source definition, powered allocation, causal timing/fallback | C3_IDENTIFIABLE=NO:source treatment and joint-information/computation effects are not separated | POWERED=NO:at true 1% gain, illustrative EE-conjunction plan needs 98 seeds/876 dates with 3% date and 1% seed SD; QoS power additional | DECISIVE_TESTS=information twins/additive placebo; training-to-atomic-execution intervention; crossed-cluster coverage/power merger