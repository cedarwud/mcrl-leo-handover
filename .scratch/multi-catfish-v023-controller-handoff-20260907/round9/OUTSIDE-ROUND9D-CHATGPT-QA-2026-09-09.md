**I would use bounded joint search with a small set-conditioned interaction scorer as C3.** Certified unilateral improvement is the essential comparator. A learned proposer plus exact evaluator is a sensible subsequent design if learning can demonstrably reduce search cost or find better joint moves.

Negative interactions justify collision-aware selection. They do **not** establish submodularity, an approximation guarantee, or a need for learning.

Two corrections to the supplied evidence matter:

* The [VERTICAL-SLICE-SMOKE-2026-09-08.md](sandbox:/workspace/scratch/d3d33c68a166/review/package-9D/VERTICAL-SLICE-SMOKE-2026-09-08.md), “Shortcuts and unimplemented decision items,” explicitly identifies `S_UNI` as a **bounded-catalogue ceiling proxy**, not a certified iterated unilateral optimum. That run also contains no trained S3 and no arm-specific closed-loop evaluation.
* The [DIAG-RESULT-SUMMARY-2026-09-08.md](sandbox:/workspace/scratch/d3d33c68a166/review/package-9D/DIAG-RESULT-SUMMARY-2026-09-08.md), “diag3 final,” establishes **catalogue sufficiency**: evacuation-only retained approximately 99–101%, and one-alternative unilateral-only 71–72%, of the legacy decoder’s gain. Because evacuation rows include broader singleton destination search, the remaining fraction is not a measured coordination contribution.

These are supplied development observations, not independently reproduced results.

1. **Local search is the strongest optimisation foundation; the other families require additional structure.**

   | Family                                                    | Actual guarantee                                                                                                                                                                                                                    | What it promises here                                                                                                                                                                                                                                                                                                                |
   | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
   | **Coordination graphs / max-plus**                        | Exact maximisation for an exact acyclic factorisation, with sufficient message propagation and consistent recovery of tied actions. Ordinary loopy max-plus has no general convergence or global-optimality guarantee.              | Pairwise collision penalties are representable, but shared activation, ACM transitions and coupled interference can require higher-order factors. Negative residuals do not establish a sparse pairwise factorisation. [Böhmer et al., §2.2](https://www.cs.ox.ac.uk/people/shimon.whiteson/pubs/boehmericml20.pdf)                  |
   | **Matching / auction**                                    | Fixed-weight assignment admits optimal solutions; an ε-auction provides an \(n\epsilon\) objective-gap certificate under its assignment assumptions.                                                                                | Useful if user–resource values can be fixed independently of the completed assignment. Here occupancy changes rates, powers and interference, so an assignment solver would generally optimise a surrogate. [Bertsekas, §§1–2](https://arxiv.org/html/2310.03159v2)                                                                  |
   | **Submodular greedy / curvature**                         | For normalised, nonnegative, monotone submodular maximisation: cardinality greedy gives \(1-1/e\), strengthened to \((1-e^{-c})/c\) using total curvature \(c\). Ordinary greedy under a general matroid instead gives \(1/(1+c)\). | None follows from the package. The signed surplus objective, activation thresholds and service constraints need separate structural proofs. These guarantees concern the specified set objective, not realised pooled EE. [Vondrák, §§1–3](https://theory.stanford.edu/~jvondrak/data/submod-curv.pdf)                               |
   | **Unilateral improvement followed by joint local search** | Strict improvement of one common objective on a finite feasible space terminates at a neighbourhood optimum, if allowed to finish.                                                                                                  | The most defensible baseline and search organisation. It guarantees neither global quality nor completion within 10 s. Personal-utility best responses are not automatically equivalent to improving the common surplus.                                                                                                             |
   | **Learned proposer + exact evaluator**                    | Retaining the incumbent and accepting only verified improvements prevents deterioration of the evaluated selection objective. Optimality extends only to candidates actually evaluated.                                             | A clean way to learn search allocation. It does not guarantee realised EE improvement, global optimality, or a positive learned marginal. Learned neighbourhood selection has established precedents, but their empirical gains do not transfer automatically to this simulator. [Sonnerat et al.](https://arxiv.org/abs/2107.10201) |

   “Substitutes” needs mathematical qualification. For example, a cardinality-dependent set function with values \(0,1,1,2\) at set sizes \(0,1,2,3\) has negative pair and triple residuals relative to the empty set, yet its marginal increments \(1,0,1\) violate diminishing returns.

   Stronger substitutes structure can support stronger guarantees: for an \(M^\natural\)-concave objective, absence of improving additions, deletions **and exchanges** characterises global optimality. That is a substantive exchange axiom, not a consequence of observed congestion. [Murota, Theorem 5.3](https://www.keisu.t.u-tokyo.ac.jp/data/2008/METR08-32.pdf)

   Consequently, I would not introduce max-plus or a curvature-bound narrative merely because most measured interactions are negative.

2. **The minimal learned component is one scalar per candidate set; its irreducibility to best response must be demonstrated.**

   Your [V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md](sandbox:/workspace/scratch/d3d33c68a166/review/package-9D/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md), §C2—hereafter **Contract**—already specifies a reasonable minimum:

   $$
   \widehat{\Psi}_\theta(Z_t,a^0,A,a_A),
   \qquad
   \widehat{\Psi}(\varnothing)=\widehat{\Psi}(\{i\})=0.
   $$

   There is no demonstrated need for another independent per-user Q-agent.

   However, **no architecture is intrinsically “not replaceable by best response.”** It must establish either:

   * Better decisions because it selects useful joint moves unavailable to unilateral improvement; or
   * Comparable decision quality at materially lower end-to-end computation.

   Predicting congestion accurately while selecting the same profiles as affordable unilateral search establishes neither additional coordination capability nor a necessary third component.

   **“Learn where best response gets stuck” is legitimate**, but the useful target identifies an escape, rather than merely classifying an anchor as difficult. At TRAIN anchors, obtain a certified unilateral optimum \(u\), enumerate a declared bounded joint neighbourhood, and label

   $$
   \Delta_m(A;u)=F_m(u\oplus A)-F_m(u).
   $$

   Supervise a set ranker using these signed gains, feasibility labels and a no-op candidate. Include unsuccessful exchanges and anchors with no available improvement; training only on successful escapes would distort the task. Predicting neighbourhood improvement and delegating selected neighbourhoods to a solver has a direct precedent in [Li, Yan and Wu](https://proceedings.neurips.cc/paper/2021/hash/dc9fa5f217a1e57b8a6adeb065560b38-Abstract.html).

   The key diagnostic is:

   $$
   \Delta_m(A;u)=\sum_{i\in A}d_i^u+\Psi_A^u.
   $$

   When every constituent singleton is feasible, certification gives \(d_i^u\leq0\). An improving joint escape therefore requires **positive re-anchored interaction sufficient to overcome the singleton losses**. Positive \(\Psi_A^u\) alone is insufficient.

   This does not contradict negative interactions around the original carrier. Indeed, if the compatible edit-set function around \(u\) were globally submodular, then

   $$
   \Delta_m(A;u)\leq\sum_{i\in A}d_i^u\leq0,
   $$

   so there would be no such escape. Useful escapes reveal contextual complementarities, exchange barriers or other departures from that pure-substitutes model.

   A qualification: a jointly feasible swap can have infeasible singleton intermediates. Such constraint-enabled exchanges require separate accounting; unilateral certification does not establish nonpositive raw gains for counterfactuals outside its feasible neighbourhood.

   The [v1.6 amendment](sandbox:/workspace/scratch/d3d33c68a166/review/package-9D/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md), §3—hereafter **Amendment**—already requests re-anchored diagnostics. It does **not** replace the sealed learner with an escape proposer. Changing training anchors, candidate support or pruning would require a disclosed prospective amendment.

3. **Residual supervision is feasible without joint physics at inference, provided the encoder receives sufficient information.**

   Per-user rows alone are generally insufficient. Identical focal-user features can accompany different destination overlaps, background interference or activation consequences. A set encoder can distinguish those situations only if the distinguishing information reaches it.

   At minimum, the representation needs proposed and incumbent associations, relevant background occupancy and activation, shared-resource relationships, and sufficient desired/cross-gain information to represent interference coupling. “Interference summary” is not automatically sufficient: it may hide precisely the differences that change a coupled fixed point.

   Permutation-invariant architectures provide an appropriate representation mechanism; they do not prove feature sufficiency or out-of-sample accuracy. [Set Transformer](https://proceedings.mlr.press/v97/lee19d.html) specifically models interactions among set elements. Contract §G, T2’s information-twin test is therefore valuable: the full context should separate opposite interactions, while removing that context should expose the ambiguity.

   Four implementation distinctions are essential:

   * **Teacher computation is not inference computation.** Exact physics can generate training labels offline; the trained head need not repeat the solver.
   * **Candidate features can conceal the solver.** If obtaining each candidate’s input powers, interference or service already requires its coupled physics evaluation, the main computational cost has already been paid. Report that dependency and its runtime.
   * **The total residual does not require all subsets.** Given baseline and singleton evaluations, exact \(\Psi_A\) requires one additional evaluation of the joint profile. The \(2^{|A|}\) expense concerns exact Shapley allocations or other subset decompositions. Contract §B5’s size-cap rationale needs clarification; large-coalition total residuals should not be approximated merely because Shapley attribution is expensive.
   * **The target and selection objective must agree.** Amendment §1 switches selection to margin-adjusted \(F_m\) while saying labels remain unchanged. To preserve the decomposition, \(d_i^m\) and \(\Psi_A^m\) must both derive from \(F_m\). A nominal or realised residual is a different target. The wording needs resolution before source generation; it does not establish that the implementation is already wrong.

   If exact joint evaluation remains necessary at inference, the honest learned claim is **search allocation**, **reduced evaluation count**, or another explicitly measured residual task. If exact \(F_m\) is already available for every candidate, recomputing its ranking with a learned approximation cannot improve its exact maximum over that same catalogue. A realised-EE improvement could still occur through different choices under model mismatch, but that would require a separate explanation.

   Finally, the two interventions must remain distinct: exact reranking after a learned proposer is legitimate; exact reranking that restores \(\Psi\) after a residual-head knockout invalidates that knockout. Contract §A4 explicitly prohibits hidden restoration.

4. **The main anti-pattern is crediting learning for advantages supplied by information, search support or the evaluator.**

   | Mistake                                                                       | Statistic or comparison that exposes it                                                                                     |
   | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
   | Treating negative selected \(\Psi\) as proof that coordination hurts—or helps | Net collision-avoidance value, decomposed into interaction loss avoided and singleton value sacrificed                      |
   | Calling the legacy 28–29% remainder a coordination share                      | Equal destination breadth, coalition-size census and an exhaustive unilateral comparator                                    |
   | Calling a catalogue ceiling or timed-out search a unilateral optimum          | Final complete-neighbourhood termination certificate, certificate rate and maximum remaining improvement                    |
   | Crediting C3 for exact rescoring unavailable to the baseline                  | Information- and budget-matched `S_UNI`; learned S3 versus exact S0                                                         |
   | Reporting good residual MSE as successful coordination                        | Selection regret, harmful acceptance rate, top-choice agreement and escape recall, stratified by coalition size             |
   | Calling central set-conditioned inference decentralised MARL                  | Explicit deployment information and communication requirements                                                              |
   | Treating nominal surplus improvement as an EE guarantee                       | Realised pooled \(\sum B/\sum E\), with bits, joules and QoS reported separately                                            |
   | Hiding computation behind “one forward pass” or excluding failures            | Full latency distribution, feature-construction time, physics-call count, timeout frequency and fallback-inclusive outcomes |
   | Treating knockout, retraining and oracle removal as interchangeable           | Separate estimates for the four experiments in Contract §C3                                                                 |

   Amendment §3 supplies the right mechanism statistic. Using its matched catalogue and objective,

   $$
   \kappa V_{\rm CA}
   =F(a_C)-F(a_D)
   =\underbrace{\Psi(a_C)-\Psi(a_D)}_{\text{interaction loss avoided}}
   -\underbrace{[D(a_D)-D(a_C)]}_{\text{singleton value sacrificed}}.
   $$

   Report both terms unclipped. A selector can avoid substantial interaction loss while sacrificing still more singleton value.

   Also report the frequency of additive reversals,

   $$
   D(a_D)>0,\qquad D(a_D)+\Psi(a_D)<0,
   $$

   and whether S3 actually prevents them. These statistics explain collision avoidance; superiority over certified `S_UNI` establishes the additional search question.

5. **For this already-sealed study, I recommend retaining the scalar residual head as the primary C3.**

   Keep the declared catalogue, set-conditioned head, neutral-source intervention, service guard and fallback. Apply the Amendment’s margin-consistent immediate scoring and C2 tie-break rule. Resolve the target-consistency ambiguity before training. This directly tests the existing hypothesis without turning an interaction-learning experiment into a different search-learning experiment.

   Make the conclusions depend on three separate comparisons:

   | Comparison                                                                  | Supported conclusion                                                                      |
   | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
   | FULL versus neutral-source DROP_C3                                          | Informative C3 source training helps under the specified intervention                     |
   | FULL versus certified `S_UNI`, with QoS and decision-relevant nonadditivity | Additional coordination value beyond exhaustive unilateral improvement                    |
   | S3 versus matched exact S0                                                  | Learned-surrogate quality; matching outcomes with lower computation supports acceleration |

   Before interpreting any coordination marginal, establish whether useful joint escapes exist in the bounded support. This is a diagnostic of available headroom, not permission to keep changing the catalogue until C3 wins.

   The 10 s budget must include all decision-bearing work, including feature construction, catalogue generation and validation. The supplied smoke timing does not establish operational compliance. A budget-limited `S_UNI` remains a useful operational comparator, but Amendment §4 correctly makes an uncertified contrast insufficient for its stronger admission claim. An offline certified reference can diagnose headroom, provided its different computational status is explicit.

   **I would defer a learned escape proposer unless profiling establishes a reason for it.** If all approximately 1,000 configurations can already be evaluated exactly within budget, learned nominal ranking over identical support has little algorithmic justification. If evaluation is the bottleneck, a prospective learned-proposer experiment should compare learned ordering against deterministic and random ordering over the same master catalogue and evaluation budget.

   Report the outcome without forcing a positive narrative:

   * **Positive coordination marginal:** the registered source contrast passes, and FULL also clears the certified unilateral comparison and QoS requirements.
   * **Conditional benefit:** source training helps, but superiority beyond unilateral optimisation is unestablished; alternatively, comparable outcomes require less computation. Name the demonstrated benefit precisely.
   * **Non-positive or inconclusive:** an interval excluding the practical margin supports no practically relevant benefit within scope. A failed lower-bound test alone is inconclusive. Contract §§C6 and D2–D4 already preserve this distinction.

VERDICT: FAMILY=bounded joint search | MINIMAL_LEARNED=set-conditioned scalar residual head | SUPERVISION=feasible | RECOMMENDED_C3=Retain the sealed residual-head selector and require separate evidence for source-training benefit, value beyond certified unilateral search, and computational savings.
