The owner’s requirement is **measurable after clarification, but ambiguous as stated**. “Individually improve” can mean **standalone benefit**—add one component to a common control—or **conditional contribution**—add that component when the other two are already present, measured by FULL versus leave-one-out. A stronger reading is **benefit in every background**: adding a component improves every subset that lacks it. These are different experiments, and interactions prevent one from establishing another. For the owner’s plain-language promise that each component works individually, singleton-versus-control is the scientifically direct test; leave-one-out is scientifically meaningful for the narrower conditional claim. The displayed ordering requires FULL to beat each pair, but does not require pairs to beat singletons. The control, component intervention, evaluation population, and meaning of “positive” must also be explicit.

`DIAGNOSTIC_NOT_CLAIM`. This is a prospective design note. I inspected workspace documents read-only, ran no experiments, and modified nothing.

Let \(S\) identify which routes receive informed rather than neutral training sources. Define each arm’s pooled efficiency and relative contrast as

\[
\eta_S=\frac{\sum B_S}{\sum E_S},
\qquad
\Delta_{S,R}=\frac{\eta_S}{\eta_R}-1.
\]

The sums must cover the same prescribed evaluation allocation. “Positive” here means a positive pooled effect with the required uncertainty evidence; it does not mean improvement in every world, seed, or decision.

There are three distinct references:

- **\(N=000\), all-neutral:** the matched control for the value of informed source training.
- **\(U\), certified unilateral policy:** the reference for whether learned coalition selection adds value beyond the shared optimization prefix.
- **\(G\), geometry-only baseline:** the reference for the complete system’s improvement over a weaker external policy.

They answer different questions. Neither \(G\) nor \(N\) should silently substitute for \(U\).

The source intervention also matters. The contract retains, trains, and deploys all routes; it substitutes neutral training data. Consequently, “C1 only” must mean **only C1’s source is informed**, with C2 and C3 trained on neutral sources. It does not mean deleting two predictors. The [stages 6–8 draft explicitly identifies this source-training estimand](/home/sat/mcrl-v025-ladder-ws/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md:14).

The following policies would test the literal standalone-plus-ordering requirement:

| Arm | C1 source | C2 source | C3 source | Required reference |
|---|---|---|---|---|
| `000` — all-neutral | Neutral | Neutral | Neutral | Common source control |
| `100` — C1 informed only | Informed | Neutral | Neutral | `000` |
| `010` — C2 informed only | Neutral | Informed | Neutral | `000` |
| `001` — C3 informed only | Neutral | Neutral | Informed | `000` |
| `110` — DROP_C3 | Informed | Informed | Neutral | `000`; also compared against FULL |
| `101` — DROP_C2 | Informed | Neutral | Informed | `000`; also compared against FULL |
| `011` — DROP_C1 | Neutral | Informed | Informed | `000`; also compared against FULL |
| `111` — FULL | Informed | Informed | Informed | Each pair; separately the required unilateral comparator |
| `U` — unilateral | — | — | — | Executes the certified fixed point at every anchor |
| `G` — geometry-only | — | — | — | External context |

The eight learned configurations hold fixed architecture, route budgets, initialization pairing, training procedure, checkpoint rule, physics, observations, selector, catalogue-generation rules, fallback, and all frozen constants. Only the designated source assignments change. Catalogue identity is required at an identical state; independently evolving policies need not visit identical states.

For the literal requirement, the necessary inequalities are:

- Three singleton-versus-`000` improvements.
- Three pair-versus-`000` improvements.
- Three FULL-versus-pair improvements.

FULL-versus-`000` then follows by transitivity. The separate contractual comparison with a unilateral-equipped policy remains necessary. If that specified comparator differs from \(U\), retain its exact definition; a convenient substitute would not discharge the clause.

Thus, **add the three singleton-source configurations**. That produces nine policies including geometry, or ten including a distinct unilateral comparator if it is not already evaluated elsewhere. The existing six arms can answer the narrower `FULL > each pair > all-neutral` question, provided those contrasts are actually evaluated. They cannot establish standalone efficacy or positivity of every nonempty subset.

If the owner instead means “every addition helps,” the same eight configurations support all **12 component-addition edges** of the factorial design, including pair versus constituent singleton. That is a stronger requirement. The displayed inequalities alone even allow a singleton to outperform FULL.

Strict ordering mathematically means an effect above zero. The sealed +0.5% lower-bound requirement remains a separate, stronger obligation wherever the contract applies it. Extending that margin to every new comparison would be an additional requirement, not a clarification already implied by the ordering.

Several failure modes would limit interpretation.

**A large leave-one-out gap can mostly measure recovery from a damaged comparator.** On the absolute bit/J scale,

\[
\eta_{\mathrm{FULL}}-\eta_{\mathrm{DROP}}
=
(\eta_{\mathrm{FULL}}-\eta_U)
+
(\eta_U-\eta_{\mathrm{DROP}}).
\]

The first term is improvement beyond unilateral performance; the second is damage in DROP. Report both, along with every learned arm’s efficiency relative to \(U\). Fallback-selection frequency alone is insufficient: measure the frequency and severity of selected coalitions doing worse than their fallback under matched evaluation.

If the +0.51% ceiling and +15.6% FULL/DROP gap applied to the same pooled endpoint and domain, then

\[
\eta_{\mathrm{DROP}}/\eta_U
\leq 1.0051/1.156 \approx 0.8695.
\]

DROP would be roughly 13% below unilateral performance. That would still identify a potentially real benefit of informed over neutral training within this architecture. It would not establish 15.6% of new joint-search opportunity or standalone component usefulness.

**The geometry baseline can make “beats control” largely attributable to the prefix.** The shared +442% improvement makes comparisons with geometry weak evidence about learned components. It does not mathematically guarantee that every learned arm wins—sufficiently bad ranking could erase the gain—but it supplies a huge inherited advantage. All-neutral controls that attribution problem for source training. However, all-neutral may itself rank badly, so beating it does not establish improvement over a healthy unilateral policy. That is why the separate unilateral clause is substantive.

**Cancellation can make apparent component necessity an artifact of a coupled representation.** With \(480.1-440.1=40.0\), a 1% calibration error in either large term changes the net by approximately 11–12%. Ranking nearly tied candidates can be still more sensitive. A component may chiefly compensate for another term’s overstatement. That can be useful engineering, but the result supports the coupled scoring system, not three independent mechanisms.

Neutral-source substitution preserves the score’s structure better than deleting terms, but does not guarantee calibration across the substituted predictors. Diagnostics should examine combined-score error, candidate ranking, and realized loss relative to fallback across coalition sizes. Good individual regression losses are insufficient. Nothing here justifies changing the score, signs, or guards.

**The headroom and materiality margin are uncomfortably close.** If +0.51% is a valid upper bound for the *same pooled rollout endpoint*, clearing +0.5% against unilateral requires about 98% of available improvement, leaving only 0.01 percentage point for performance loss and uncertainty. If two successive comparisons above unilateral each required +0.5%, their compounded requirement would exceed +1.0025%, incompatible with that ceiling.

Those are conditional statements. A bounded search result at sampled anchors is not automatically a ceiling on full trajectory efficiency: states, support, horizon, objective, and workload must match. Also, **do not divide the headroom by three or sum the three leave-one-out margins**. All three compare the same FULL policy with different alternatives; complementarity can make each contrast reflect the same opportunity.

**Multiplicity depends on the claim being made.** For one prespecified conjunctive decision—“all required inequalities pass”—an intersection–union test is appropriate: require every constituent test to pass at its prescribed level. Bonferroni is not automatically necessary for that single global acceptance decision. The [contract expressly adopts conditional intersection–union wording](/home/sat/mcrl-v025-ladder-ws/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.2-AMENDMENT-2026-09-08.md:9).

However, individual intervals are not thereby simultaneous confidence intervals. Reporting selected component successes when the conjunction fails, or asserting jointly valid component-specific bounds, needs the corresponding multiplicity treatment. Adding singleton requirements also lowers the probability that everything passes; the weakest contrast matters.

**Dependence, selection, and endpoint mismatch can invalidate otherwise attractive results.** Preserve arm pairing and the crossed date-by-learner-seed structure. Thousands of anchors do not create thousands of independent trained learners. Recompute pooled bits/joules in each bootstrap draw; averaging episode efficiencies or relative gains changes the endpoint. The [later amendment specifies a paired two-way bootstrap and development-disjoint confirmation dates](/home/sat/mcrl-v025-ladder-ws/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md:7).

Other material confounds include:

- Arm-dependent training budgets, source leakage, or checkpoint selection.
- Candidate generation or observable information changing with the source intervention beyond the declared mechanism.
- Using FULL’s logged trajectory to evaluate alternative policies whose actions would change subsequent states.
- Treating accuracy for a fixed-price surplus score as proof of improvement in pooled bits/joules.
- Inconsistent energy or handover accounting, or efficiency gains accompanied by unacceptable service loss. The frozen QoS obligations remain relevant.

There are meaningful cost reductions, but they should preserve the experiment rather than omit missing contrasts.

The most promising is **reusing identical route training**. The [legacy model uses separate route networks and optimizers](/home/sat/mcrl-v025-ladder-ws/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:258). If the successor retains mask-independent training, there are only six distinct route/source fits per seed: three routes, each informed or neutral. These can compose all eight configurations. Naively, five learned arms repeat 15 route fits per seed; eight repeat 24.

That equivalence requires identical route initialization, batches, ordering, optimizer state, randomness, normalization, update counts, and checkpoint choice. It fails with shared trainable parameters, arm-dependent source generation, on-policy training, or mask-specific selection. The workspace supports investigating this optimization; it does not prove successor equivalence. All eight resulting policies still require evaluation.

Also share immutable geometry, exogenous random fields, and physical calculations with identical inputs. Share prefix and catalogue computation only when their full input state matches. Once different policies commit different associations, their histories and future anchor states can diverge. Reusing a common prefix algorithm is not permission to reuse another policy’s trajectory. Offline acceleration must also preserve any declared deployment deadline and fallback behavior.

Geometry and unilateral policies need no learner training. If learner seed has no effect on their world inputs or policy, evaluate them once per distinct world and reuse the paired result. Those copies are not independent observations.

**Fewer seeds may suffice for ordering than for a material-margin test, but no particular reduction follows from the word “ordering.”** Power depends on variability and the distance between the true effect and the tested threshold. An effect of 0.6% is much easier to distinguish from zero than from 0.5%, all else equal. Yet a tiny ordering effect can demand many seeds, and twelve seeds may already provide fragile tail estimation. More worlds do not eliminate uncertainty from training randomness. A seedwise sign test would also answer a different question from pooled-efficiency improvement.

The authorized twelve seeds and acceptance rules remain unchanged. Any alternative allocation would need a separate prospective design justified by variance information and the weakest required contrast.

No factorial configuration is redundant for the literal subset requirement without additional structural assumptions. Geometry is unnecessary for identifying source effects, but retains its external comparison role and contractual status. FULL-versus-neutral is a redundant *acceptance contrast* once the relevant chain passes; the neutral *arm* is indispensable.

I would clarify the requirement before spending more compute. If the intended scientific claim is “each informed source contributes within the complete architecture,” the existing conditional design is appropriate, supplemented by the required unilateral comparison. If the intended claim is “each source is useful alone and all combinations remain beneficial,” the singleton configurations are required. Weakening that promise to conditional contribution would change the requirement; it would not merely make the same question cheaper.

I would not impose universal monotonicity merely because the design has three named components. Complementary predictors can be valuable together without being valuable alone. That is a design judgment, not an assertion that monotonicity is unmeasurable. Likewise, the source paper’s two ablation styles motivate distinguishing the questions; its reported 0.6% contribution supplies neither a transferable effect size nor a justification for this simulator’s margin.

Even if every ordering held comfortably, I would refuse to conclude that:

- Contributions are additive, independent, or beneficial in every untested context.
- The three-part architecture is uniquely necessary or superior to a simpler, fairly trained ranker.
- Learned components deserve credit for the prefix’s +442%.
- Large ablation gaps represent equally large physical headroom.
- Every selected coalition improves its fallback, or every user and world benefits.
- The system generalizes beyond the evaluated simulator regime, information convention, and energy accounting.

A successful factorial experiment would establish effects of precisely defined source-training interventions in this deployed selector. That is a worthwhile result, provided the claim stays that precise.
