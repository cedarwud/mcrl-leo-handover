# C3 after eight target families: what the failures establish and what remains worth studying

**Independent research review • 8 September 2026**  
**Audience:** authors of the Multi-Catfish LEO handover paper.  
**Decision:** whether a third coordination/externality head merits the remaining week of the current paper.

## Decision

**Close the existing C3 direction for this paper. There are legitimate research paths left, but the strongest ones change the target horizon, the intervention interface, or joint-action selection enough to belong in a follow-up.** Preserve the separate C1/C2 experiment and report its results at their actual evidence level; the supplied declaration is not evidence that C1/C2 have already demonstrated efficacy.

I would assign **about 10% probability, with a subjective range of 5–20%,** that a genuinely new, prospectively fixed C3 produces a reproducible positive pooled-EE effect within one week while retaining sealed C1/C2 and the per-user additive argmax. This overall estimate includes implementation and evaluation failing to finish in time. For a useful effect large enough to support the current paper’s three-route claim, my estimate is **below 5%**. These are judgments, not frequencies estimated from eight independent trials: the families are related, several stops were not efficacy tests, and no effect-size/power analysis is available.

The central scientific result is a separation between **predicting a counterfactual target, aligning an individual intervention with EE, and executing a beneficial joint policy**. R7 directly separates the first from the other two. The literature explains why these are different requirements; it does not supply a theorem that another auxiliary target will repair this controller.

Four distinct candidates are specified below. Two retain the algebraic deployment sum but redefine C3; two change composition. **None is a repair or authorized continuation of R7/F1.** No candidate, simulation, training job, or TEST evaluation was run for this review.

## What was actually supplied and established

The reviewed attachment is `multi-catfish-c3-chatgpt-review-package-20260908-r1(1).zip`. All **35 file hashes listed in `SOURCES.md` match the shipped bytes**. The package contains reports, one direct F1 receipt, contracts, and selected source code. It does **not** contain the physical F1 tape, raw R7 arrays, or the full original execution environment. Consequently, this review verifies supplied-file integrity, receipt arithmetic, and code semantics—not a fresh replay of server results.

Package references below use these short identifiers:

| Reference | Supplied evidence |
|---|---|
| P1 | `01-CHRONOLOGY.md`, especially the eight-family grouping and §§3–4. A derived historical index, not raw experimental data. |
| P2 | `02-R7-STOP-PHYSICS-RESULT.md`, source, composition and fit panels; appended adjudication. |
| P3 | `03b-F1-r2-receipt.json`; final r2 section of `03-F1-KILL-SCREEN-RESULT.md`; `03c-F1-ULTRA-ADJUDICATION.md`. |
| P4 | `04-CONTINGENCY-LADDER.md` §§1–5; `05-R7-CONTRACT.md` §§2–8; `06-COMPOSITION-RULING.md`. |
| P5 | `07-C1C2-SUCCESSOR-DECLARATION.md`; `08-F3-DESIGN-R2.md`. F3 was not launched. |
| P6 | `09-PRIOR-DESIGN-ADJUDICATIONS/`, especially the V0.14 Q3-support and V0.20 repricing notes. Historical adjudications with their stated provenance. |
| P7 | `10-PHYSICS-AND-CODE/`: `c3_contingency_f0.py::compute_c3_targets`, `ee_axis_coalition_residual_c3.py`, and `v023_lcsrs_source_adapter.py`. |
| P8 | Same directory: `F1-README.md`, `run_v023_c3_contingency_f1.py::_generate_physical_tape`, `step.py::ActionEvaluation`, `ee_axis_ops3.py`, `ee_axis_ops3_live.py`, `action_contract.py`, and `link_budget.py`. |

Three corrections to an overly broad reading of the record matter:

1. **These are eight grouped families, not eight independent, uniformly learnable failures.** The chronology has 18 numbered entries, including successful oracle stages, representation/loss revisions, and an instrument stop. Several ZR learners failed their learning gates. Family A remains unresolved rather than scientifically refuted. [P1, P6]
2. **R7 is a development-gate failure with several distinct denominators.** The 688-pair source panel has 11-versus-00 pooled EE **−0.0493%, 2/8 worlds positive**. The composition panel separately reports teacher **+0.335%** and learned **−0.660%** versus BASE; topology consistency is **379/707 = 0.536**. Held-out balanced accuracy is **0.705 versus 0.626** and Spearman **0.839**. The positive teacher-composition result must be disclosed; it does not annul the binding physical-signature failure. [P2]
3. **F1 is a two-anchor intervention screen along BASE’s trajectory.** BASE, D and F pool bits/joules over the same two anchors; only BASE is committed between anchors. D loses **1.327883% EE** and one of 200 service opportunities; F loses **4.536265% EE** with service unchanged. This is valid negative screening evidence for the specified D/F policies, not a two-step autonomous rollout of each candidate and not universal externality impossibility. [P3, P8]

## The eight-family mapping requested

“Demonstrated” below means demonstrated at the record’s stated development/provenance level. An observed pattern and its proposed causal explanation are distinguished.

| Package design family | Literature analogue | Known failure mode relevant here | Already demonstrated in this record? |
|---|---|---|---|
| **A. V0.3/V0.4 matched-opening ζ3; masked mean/max** | Difference-reward-like externality prediction; learner-independent reward diagnostics in [Agogino–Tumer, 2008](https://link.springer.com/article/10.1007/s10458-008-9046-9). | Favorable learning summaries do not establish the deployed mechanism’s marginal contribution; null/working-point comparisons can fail. | **Yes:** gate/working-point and inference-only ablation-estimand problems. **No:** a general physical misalignment result. The terminal status explicitly leaves C3 unresolved. [P1] |
| **B. V0.9 PNFE, committed “others hold”** | Counterfactual difference utilities; resembles the fixed-other-actions operation of [COMA](https://www.cs.ox.ac.uk/people/shimon.whiteson/pubs/foersteraaai18.pdf), not COMA’s algorithm. | Counterfactual background is inconsistent with the actions eventually executed. A non-focal rate difference is not a full-global difference reward. | **Yes:** −11.0636% EE, 0/3 positive lineages, high simultaneous handover; background misspecification is the package’s diagnosis. Its exclusive causal contribution was not isolated by this review. [P1] |
| **C. V0.10 MONE and V0.11 joint-response deepening** | Unilateral difference utility / anticipated local best response; [COIN factoredness](https://arxiv.org/html/cs/9905005v1). | Simultaneous improvements calculated against separate backgrounds need not compose; anticipated response can remain wrong or settle on poor joint behavior. | **Directly yes:** all 60 selected-unilateral sums were positive, but 28 realized joint directions reversed; V0.10 EE −2.637%. Deeper background evaluation did not reverse the negative band; activation expansion is the recorded mechanism diagnosis. [P1] |
| **D. V0.12–V0.14 ZR oracle → learner** | Gated counterfactual teacher; privileged-information supervision. | Gate/support depends on hidden joint commitments; an instantaneous label may be correlated with a different downstream benefit. | **Yes:** fresh oracle +0.94%, 4/4 worlds, followed by Q3 learning failure. Support observability and downstream consolidation explanations are supported by the supplied diagnostic notes. Not a proof that every deployable representation is inadequate. [P1, P6] |
| **E. V0.15/V0.15-R/V0.16/V0.17 context, origin, soft-KL** | Representation augmentation and teacher imitation; related to auxiliary-transfer limitations in [Du et al.](https://arxiv.org/html/1812.02224v2). | Better features or loss fit need not preserve the teacher’s stable decisions or provide missing decision-time information. | **Yes:** successive declared gates failed; stable-decision corruption is reported. **No:** a formal Bayes-error lower bound for every possible C3 state was established. [P1, P6] |
| **F. V0.18/V0.19 relational and normalized ZR** | Relational approximation of counterfactual utilities. | More expressive structure or numerical normalization does not itself establish action-value consistency. | **Yes:** learner gates failed. **Separate:** `STOP_R2_EQUIVALENCE` was a faulty instrument criterion, not evidence against the scientific target. [P1] |
| **G. V0.20 repriced and V0.21 expected ZR** | Fractional-surplus pricing and conditional expectation; [fractional RL](https://proceedings.mlr.press/v139/suttle21a.html). | Realized-fading oracle advantage can disappear under deployable information; repricing does not repair all other mismatches. | **Yes:** exact repriced +0.985% survived; nominal +0.424% missed the frozen 3/3 lineage requirement; expected-ZR stopped. **No:** every possible λ or conditional estimand is thereby refuted. [P1, P6] |
| **H. V0.22/V0.23 LC-SRS, then predeclared D/CSE and F/EC** | LC-SRS: exact two-player Shapley allocation of a specified surplus, related to [Shapley Q-value](https://arxiv.org/pdf/1907.05707). D/F: budget-balanced energy cost allocation and correction. | Allocation conservation is different from incentive alignment, favorable coalition physics, and coordinated execution. Cost shares are not marginal network costs. | **Yes:** R7 learns the target but fails physics and learned composition; harmful-partial/topology guards fail. D/F both fail F1. **No:** universal Shapley, cost-sharing, or coordination impossibility. [P2–P4, P7] |

## Credit assignment: the precise distinctions the literature supports

Write the joint action as **a**, the focal user as $u$, legal mask as $m_u$, and the fixed Q1+Q2 reference as **b**. Let

\[
B(x)=\Delta t\sum_v R_v(x),\quad E(x)=\Delta t P^N(x),\quad
G_\lambda(x)=B(x)-\lambda E(x),\quad q_u(a)=Q_{1,u}(a)+Q_{2,u}(a).
\]

Throughout this report $z_3$ is in bits and $Q_3=z_3/\kappa$. A learned Q3 already in normalized units must **not** be divided by κ again. The fixed selector is $\arg\max_{a:m_u(a)}[q_u(a)+Q_{3,u}(a)]$, with the native tie rule. [P4, P5]

**Difference rewards and WLU.** For a full-global utility $G$, a standard difference reward is

\[
D_u(\mathbf a)=G(\mathbf a)-G(c_u,\mathbf a_{-u}),
\]

where $c_u$ is focal-action-independent. Algebraically, its baseline cancels when comparing focal actions at fixed other actions, for arbitrary $G$; neither additivity nor $\sum_uD_u=G$ is required. WLU instead clamps part of a trajectory. Wolpert, Wheeler and Tumer distinguish unilateral factoredness, simultaneous changes, and subtraction’s signal-to-noise benefit; their alignment result depends on the coupling partition. [*General Principles of Learning-Based Multi-Agent Systems*, 1999](https://arxiv.org/html/cs/9905005v1)

Thus **PNFE ≈ difference reward is an analogy, not an identity**. PNFE/MONE subtract non-focal current-slot bits. They only complete a global surplus difference if the other terms supplied by the controller exactly provide the missing focal bits and network energy, under the same background and horizon. The packet does not establish this equality for learned Q1+Q2. R7 balanced accuracy measures held-out prediction; it is related to, but not the same statistic as, COIN’s mathematical learnability. [P1, P2, P7]

Agogino and Tumer separate a reward’s coordination properties from the difficulty of learning it and advocate inspecting reward properties independently of a learner. This supports an inexpensive kill screen. Their final criterion remains system performance; reward diagnostics do not establish that performance. [*Analyzing and Visualizing Multiagent Rewards in Dynamic and Stochastic Domains*, AAMAS journal, 2008](https://link.springer.com/article/10.1007/s10458-008-9046-9)

**COMA.** Its advantage is

\[
A_u^\pi(s,\mathbf a)=Q^\pi(s,\mathbf a)
-\sum_{a'_u}\pi_u(a'_u\mid\tau_u)Q^\pi(s,(a'_u,\mathbf a_{-u})).
\]

This is a training-time policy-gradient baseline: its expected baseline contribution to that gradient vanishes. The central critic estimates team return; decentralized actors execute. That argument does not apply to adding an independently learned current-slot externality to two sealed action-score surfaces. A COMA-inspired third training route would require actor/critic and update changes, not merely a new name for PNFE. [Foerster et al., *Counterfactual Multi-Agent Policy Gradients*, AAAI 2018](https://www.cs.ox.ac.uk/people/shimon.whiteson/pubs/foersteraaai18.pdf)

**Shapley allocation.** Define $v(T)=G_\lambda(\mathbf c^T)-G_\lambda(\mathbf b)$ for subsets of the named two-user coalition. Then

\[
\phi_1=\tfrac12[v(\{1\})+v(\{1,2\})-v(\{2\})],
\qquad \phi_2=v(\{1,2\})-\phi_1.
\]

The packet’s $\ell_i+z_{3,i}=\phi_i$ is exact for this game. It is not a Shapley value over all 100 users or over long-run EE. The identity says how an already specified gain is allocated; it does not say the gain is positive or ensure both members adopt their designated actions. Shapley Q-value research uses additional coalition and long-term decision assumptions. Those assumptions cannot be imported into LC-SRS’s sparse unary cells. [Wang et al., *Shapley Q-value*, AAAI 2020](https://arxiv.org/pdf/1907.05707); [P7]

**Potential games and smoothness.** An exact potential aligns unilateral payoff changes with changes in that potential. Finite improvement-path results concern one-player-at-a-time moves and termination at an equilibrium, not global optimality or simultaneous best responses. Smoothness can bound equilibrium inefficiency, but requires a proved inequality for the specific game. Cost-share conservation alone proves neither a suitable potential nor smoothness constants for this EE controller. No applicable monotonicity/submodularity result is established for its interference and beam-activation model. [Monderer–Shapley, *Potential Games*, 1996](https://doi.org/10.1006/game.1996.0044); [Roughgarden, *Intrinsic Robustness of the Price of Anarchy*, STOC 2009](https://www.cs.cmu.edu/~odonnell/hits09/roughgarden-intrinsic-robustness-price-of-anarchy.pdf)

**Team versus local rewards and mean field.** A common team utility preserves the intended objective but can give each user a weak, noisy credit signal; local rewards improve signal strength at the risk of changing incentives. Mean-field MARL replaces individual neighbors with average action effects under substantive approximation/convergence assumptions. For this package, diffuse interference may admit such compression; last-user beam extinction, max-power leadership, and identity-specific visibility are much less naturally represented by averages. That concern follows from the code’s physics, not from an unperformed mean-field experiment. [Yang et al., *Mean Field Multi-Agent Reinforcement Learning*, ICML 2018](https://proceedings.mlr.press/v80/yang18d.html); [P6–P8]

**Reward shaping and score addition are not interchangeable.** Potential-based shaping uses $F(s,s')=\gamma\Phi(s')-\Phi(s)$, with appropriate terminal treatment. The telescoping construction preserves policy/equilibrium ordering under its assumptions. An action-dependent externality added only to an inference score is not that construction. A state-only potential added equally to every action would not change the argmax at all. [Ng, Harada and Russell, ICML 1999, original attribution](https://ai.stanford.edu/~ang/papers.php); [Lu, Schwartz and Givigi, *Policy Invariance under Reward Transformations for General-Sum Stochastic Games*, JAIR 2011, primary proof](https://arxiv.org/pdf/1401.3907)

There is a second composition problem even before the multi-user problem. For rewards that actually decompose and one common continuation policy, linearity gives $Q_{r_1+r_2}^{\pi}=Q_{r_1}^{\pi}+Q_{r_2}^{\pi}$. In general, $Q_{r_1+r_2}^{*}\ne Q_{r_1}^{*}+Q_{r_2}^{*}$. HRA deliberately trades optimality for easier component learning; the Multi-Advisor analysis shows how incompatible local planning can create overestimation and attractors. The package’s current-slot C1/C3 and averaged future-offset C2 are not shown to be a common-policy Bellman decomposition. This is an applicability warning, not evidence that the package uses the precise local-max update studied by Multi-Advisor. [van Seijen et al., *Hybrid Reward Architecture*, NeurIPS 2017](https://proceedings.neurips.cc/paper_files/paper/2017/file/1264a061d82a2edae1574b07249800d6-Paper.pdf); [Laroche et al., *Multi-Advisor Reinforcement Learning*, 2017 preprint](https://arxiv.org/pdf/1704.00756)

## Ratio objectives: feasible, but the reference price and decomposition matter

The evaluation quantity is

\[
\eta(\pi)=\frac{\mathbb E_\pi\sum_t B_t}{\mathbb E_\pi\sum_t E_t},
\qquad
\widehat\eta=\frac{\sum_{w,t}B_{w,t}}{\sum_{w,t}E_{w,t}},
\]

with the specified episode/world distribution and a separate service constraint. It is neither $\mathbb E[B/E]$, a sum of user EEs, nor an average of slot EEs. The population expression above corresponds to pooling independent equal-protocol episodes; the finite estimator is the packet’s actual metric.

Dinkelbach’s transformation studies $F(\lambda)=\max_{\pi\in\Pi_{\mathrm{service}}}\{B_\pi-\lambda E_\pi\}$; at the optimal ratio $\lambda^*=\eta^*$, the maximum is zero, assuming positive denominators and attainable optima. Exact optimization of the inner problems is a substantive condition, not something provided by an arbitrary deep learner. [Dinkelbach, *On Nonlinear Fractional Programming*, Management Science, 1967](https://pubsonline.informs.org/doi/10.1287/mnsc.13.7.492)

RL algorithms for this problem do exist. Suttle et al. formulate a ratio of long-run average reward to cost and develop two-timescale value/ratio learning and actor–critic methods, with tabular or specified function-approximation assumptions. Jin et al. extend fractional RL to multi-agent age-minimization; their game convergence analysis imposes strong conditions on the equilibria of intermediate games. Neither theorem covers sealed heterogeneous neural heads deployed by the packet’s sum. [Suttle et al., ICML 2021](https://proceedings.mlr.press/v139/suttle21a.html); [Jin et al., *Asynchronous Fractional Multi-Agent Deep Reinforcement Learning for Age-Minimal Mobile Edge Computing*, inspected 2024 author manuscript](https://arxiv.org/html/2409.16832v2)

Wireless EE papers also distinguish solving the physical fractional problem from approximating a useful decision rule. Jiao, Fang and Ding compare fractional programming with DDPG for energy-efficient WPT-assisted D2D/NOMA beamforming, with performance depending on channel-estimation error. This establishes a relevant wireless precedent, not a proof for satellite handover or additive auxiliary decomposition. [*Joint Robust Beamforming Design for WPT-assisted D2D Communications in MISO-NOMA*, 2022 author manuscript](https://arxiv.org/abs/2209.12253)

### Exact identities in the package’s notation

The following are algebraic deductions, not new empirical results. For matched alternatives with positive energy,

\[
\eta_c-\eta_b
=\frac{\Delta B-\eta_b\Delta E}{E_c}.
\]

For **two complete pooled policy panels**, the identical equation holds with pooled totals. Therefore $\lambda=\eta_b\$ is the exact price for the *sign of improvement over that baseline*. It need not equal the globally optimal price. Maximizing the numerator at a baseline price can provide an improvement direction, but does not generally rank all candidate ratios correctly; the denominator $E_c$ still varies.

If a frozen price differs,

\[
\Delta B-\lambda_0\Delta E
=(\Delta B-\eta_b\Delta E)+(\eta_b-\lambda_0)\Delta E.
\]

Underpricing energy therefore favors expansions; overpricing favors contractions. For a particular comparison, a sign reversal requires the pricing-error term to overcome the true surplus margin. **A sign error is possible; its occurrence cannot be inferred from price mismatch alone.** Moreover, a per-anchor price (B$b_t$/E$b_t$) aligns that anchor’s ratio, not automatically the pooled multi-step objective.

A genuine ratio-consistent instantaneous team counterfactual is

\[
D_{u,\lambda}(s,a;\mathbf b)
=\mathbb E[\Delta B-\lambda\Delta E\mid\mathcal I_t,
\mathbf c=\mathbf b[u\leftarrow a]],
\]

where $\mathcal I_t$ contains only deployable predecision information. A full-horizon analogue must include the changed future state distribution. Additivity of $B_t-\lambda E_t$ across time does **not** make its dependence on the users’ joint action additive. Nor does distributing one realization’s energy among users make their unilateral marginal differences add up.

If $\ell_u=\Delta B_u-\lambda\Delta E$ is exactly the focal component at the same background, the missing instantaneous physical term is $\sum_{v\ne u}\Delta B_v$. This explains the motivation for MONE. It does not establish that learned Q1+Q2 equals $\ell_u/\kappa$, or that all users may simultaneously take their separately assessed changes. [P1, P7]

### Does the record implicate a mispriced λ?

**It does not support λ adjustment as a current rescue.** Direct conversion of the F1 receipt’s hexadecimal constant gives

\[
\lambda_0=118{,}424{,}222.8550\ \mathrm{bits/J},\qquad
\eta_{\mathrm{BASE,F1}}=118{,}630{,}258.5068\ \mathrm{bits/J},
\]

so $\lambda_0/\eta_{\mathrm{BASE,F1}}=0.9982632$: only **0.174% below** that pooled baseline price. D/F nevertheless lose 1.33%/4.54% EE. This is an arithmetic diagnostic, not a re-evaluation of alternative λ values. It does not prove that the small discrepancy changes no individual action. [P3]

The V0.20 note independently reports that shifting the price-to-baseline ratio from 0.72 to 1.03 left the exact ZR benefit nearly unchanged (+1.031% to +0.985%). Nominal and expected-information versions remained the obstacle. This weakens the price-only explanation for that family; it does not certify the price for all future policies. [P6]

One code trap deserves explicit exclusion: `ee_axis_ops3.py` retains a legacy default λ of approximately 84,994,621.13 bits/J, but `v023_lcsrs_source_adapter.py::_repriced_ops3_context` explicitly recomputes the context at the bound repriced λ. The existence of the old default is **not** evidence that R7/F1 accidentally used it. [P7, P8]

A future fractional-learning design may predeclare an adaptive λ update such as $\lambda_{k+1}=B_{\pi_k}/E_{\pi_k}$ on designated TRAIN calibration rollouts. That is an algorithmic rule, not a post-hoc search for a favorable multiplier. With C1/C2 sealed at λ₀, however, changing only C3’s price does not make the aggregate controller consistently repriced. I do not nominate a λ-only variant below.

### A stronger concern in D/F: what their correction actually incentivizes

Let $s_u(x)=share_u(x)$, so the declared accounting conserves total energy: $\sum_u s_u(x)=E(x)$. The actual formulas are

\[
z_F=\lambda_0(\Delta E-\Delta s_u),\qquad
z_D=\Delta B_{-u}+\lambda_0(\Delta E-\Delta s_u).
\]

Thus an action with $\Delta E>\Delta s_u$ receives a **positive energy correction**, even if it expands total network energy. This is the literal declared design, not a newly discovered implementation sign bug. [P4, P7]

For the packet’s physical own-surplus component $\ell_u=\Delta B_u-\lambda_0\Delta E$, algebra gives

\[
\ell_u+z_F=\Delta B_u-\lambda_0\Delta s_u,
\qquad
\ell_u+z_D=\Delta B-\lambda_0\Delta s_u.
\]

The combined expression charges the **focal allocated share** rather than the entire marginal network energy. Since the learned Q12 surface is not exactly this physical ℓ, these equations are a semantic audit, not an exact reconstruction of F1 scores. Nevertheless, they show why conservation is insufficient evidence that D/F complete the global surplus.

The observed directions are consistent with that concern: D increases pooled bits **6.93%** but energy **8.37%**; F increases bits **14.75%** but energy **20.20%**. Those percentages are recomputed solely from the supplied receipt totals. They do not isolate the correction as the cause of the loss; simultaneous-response and surrogate-error mechanisms remain possible. Flipping the sign after seeing these results would violate the requested integrity boundary. [P3]

## Composition rules and coordination events

### What alternative selectors can legitimately offer

| Rule | Defensible interpretation | Limitation for this package |
|---|---|---|
| Constraint/veto | Reject a proposal that violates a separately specified property. Formal shields require a model/specification adequate to establish that property. | Legal actions are not automatically service-safe or EE-improving. A negative-externality classifier is not a formal shield. |
| Near-tie band | Restrict to $\mathcal A_u^\epsilon=\{a:m_u(a),\ q_u(a)\ge q_u(b_u)-\epsilon\}\$, then use C3 to choose within it. | Guarantees at most ε loss in **Q12 score**, not in true return or EE. At ε=0, useful exact ties may be rare. |
| Lexicographic | Give service or baseline-score preservation priority, then optimize a secondary criterion within a declared slack. | Changes the policy objective/ordering; existing convergence theorems require their own assumptions. It is not equivalent to optimizing EE under the original architecture. |
| Whole-proposal gate/switch | Compare a complete candidate joint action with BASE and accept or reject the entire vector. | Avoids assembling independently approved pieces, but requires a new joint predictor/interface and adequate uncertainty control. |

The primary foundations are Wray, Zilberstein and Mouaddib’s conditional lexicographic MDPs (AAAI 2015), Skalse et al.’s lexicographic RL (IJCAI 2022), Alshiekh et al.’s shielding (AAAI 2018), and Laroche et al.’s baseline-bootstrapped safe policy improvement (ICML 2019). Their guarantees attach to explicit preferences, models, uncertainty/coverage, or limiting learning assumptions—not to an arbitrary auxiliary score. [Conditional lexicographic MDPs](https://ojs.aaai.org/index.php/AAAI/article/view/9647), [lexicographic RL](https://www.ijcai.org/proceedings/2022/0476.pdf), [shielding](https://ojs.aaai.org/index.php/AAAI/article/view/11797), [SPIBB](https://proceedings.mlr.press/v97/laroche19a.html)

A directly relevant wireless example is Aumayr et al.’s antenna-tilt controller, where a safety architecture compares RL proposals with safe baselines. It supports studying a predictor as a selector or switch rather than a score bonus. Its cellular KPI setting, baseline dependence, and prediction errors limit transfer to LEO pooled EE; its tuning procedures cannot be copied as an outcome-driven search here. [*A Safe Reinforcement Learning Architecture for Antenna Tilt Optimisation*, revised 2021 author manuscript](https://arxiv.org/abs/2012.01296)

Service should remain a separately measured condition. Constrained Policy Optimization is another example of treating expected costs explicitly; adding a cost term to frozen action scores is not an implementation of that algorithm. [Achiam et al., ICML 2017](https://proceedings.mlr.press/v70/achiam17a.html)

**Integrity ruling:** any of these selectors is legitimate as a *new, prospectively declared controller design*. The current R7/F1 contracts do not permit it as a rescue. Its formula, proposal generator, information interface, thresholds, training rule, exclusions, primary estimand, and falsifier must precede computation. Since this report has read the outcomes, the redesign must be disclosed as outcome-informed research; a fresh timestamp cannot turn it into an outcome-blind original hypothesis. Its independent motivation is the theory and architecture, not fitted R7/F1 residuals. [P4]

### Why a set-valued target is more substantive than another unary share

Coordination graphs model a joint payoff using local factors and perform coordinated inference over them. Kok and Vlassis develop payoff propagation and sparse cooperative Q-learning; Deep Coordination Graphs learns pairwise factors and uses message passing, addressing relative overgeneralization in tested coordination tasks. Exact tree-graph inference and approximate cyclic inference must be distinguished. These methods include an action-selection mechanism absent from LC-SRS. [Kok–Vlassis, JMLR 2006](https://jmlr.org/papers/v7/kok06a.html); [Böhmer–Kurin–Whiteson, ICML 2020](https://proceedings.mlr.press/v119/boehmer20a.html)

Deep Implicit Coordination Graphs learns interaction structure through attention, providing a concrete analogue of “who should move together.” Centralized graph execution and training-only graph critics have different information requirements. A graph used only in training does not make an unobserved current-slot commitment available during inference. [Li et al., AAMAS 2021](https://archive.illc.uva.nl/AAMAS-2021/pdfs/p764.pdf)

For fixed-state additive unary value factors, the mixed difference is zero:

\[
F(11)-F(10)-F(01)+F(00)=0.
\]

A physical coalition with nonzero interaction cannot be represented exactly by those factors over all four profiles. **This is not proof that independent argmax cannot ever coordinate:** adequate shared observations, identities, and deterministic roles can encode a coordinated optimal policy. It is a statement about arbitrary joint-value representation. The packet additionally presents an empirical information/interface problem: even when LC-SRS targets are predictable, designated joint topology is frequently not realized. [P2, P7]

### What OPS-3 and the tape actually support

The 28 actions are **four satellite slots × seven beam slots for one user**, with changing physical identities. The 16 local features comprise four background features plus four features at each of three projected offsets. A 448-D action-set state is not a collection of 28 user coalitions. The **47 × 0.64 s** D2 substeps implement geometry/latch evolution within a roughly 30.08 s decision interval; they are not 47 intervention opportunities or independent observations. [P8]

| Proposed operation | Existing F1 tape bytes | Additional computation required |
|---|---|---|
| Recalculate a declared instantaneous unary target from recorded rates/energy | Sufficient in principle; tape itself was not attached here | Pure arithmetic once the tape is supplied/authenticated |
| Calculate a new unary head’s selected action vector, given its score surface | Recorded Q12/masks/identities suffice for selection, not arbitrary new-head inference | Pure selection arithmetic; missing predictor features require replay/live-anchor capture |
| Score a selector that changes at most one user from BASE | Covered by the unilateral rows at those BASE anchors | No new physics at those anchors |
| Score a new selector changing multiple users | Only if its entire vector coincides with an already recorded BASE/D/F profile | Otherwise one new matched physical evaluation per selected vector/anchor |
| Evaluate all subsets of one triplet with one proposed move per user | BASE plus its three unilateral profiles are covered | Four missing profiles: three pairs and the triplet |
| Measure autonomous multi-step consequences | Not covered | Cloned state, committed branch trajectories, matched randomness, and new records |

For a triplet, one binary proposal per member gives $2^3=8$ profiles; all 28 alternatives give $28^3=21{,}952$. Restricting an independently specified neighborhood/proposal is therefore material. But wireless interference and shared satellite overhead may couple those neighborhoods; sparsity must be established, not assumed. A positive interaction term alone is insufficient: the whole event’s total EE effect may still be negative. [P7, P8]

## Published negative results: the closest matches and their limits

| Primary evidence | What the authors actually showed | Appropriate use in this paper |
|---|---|---|
| Lambert et al., [*Objective Mismatch in Model-based Reinforcement Learning*, L4DC 2020](https://proceedings.mlr.press/v120/lambert20a.html) | Validation likelihood of learned dynamics need not track controller return; their analysis includes further prediction improvement after reward plateaus. | Strong published prediction/control mismatch analogue for R7. The learned object is a dynamics model, not an auxiliary Q-head. Authors frame a limitation of decoupled model learning and control. |
| Karwowski et al., [*Goodhart’s Law in Reinforcement Learning*, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/6ad68a54eaa8f9bf6ac698b02ec05048-Paper-Conference.pdf) | Further optimization of imperfect proxy rewards can reduce true reward; theory and experiments examine that divergence. | Supports a proxy-alignment interpretation. R7 does not establish the same training-time curve, and the packet’s EE is precisely specified rather than an unknown human preference. |
| Du et al., [*Adapting Auxiliary Losses Using Gradient Similarity*, inspected extended 2020 preprint](https://arxiv.org/html/1812.02224v2) | Fixed auxiliary distillation can accelerate initial learning but plateau below pure RL when the teacher remains an inappropriate influence. | A closer auxiliary-teacher failure analogue. This is training-gradient interference, not additive inference, and extended results are not represented here as an archival conference result. |
| Wolpert–Wheeler–Tumer, [COIN leader–follower experiments, 1999](https://arxiv.org/html/cs/9905005v1) | Incorrect WLU grouping produces poor global outcomes. | A negative reward-design precedent, not an impossibility result. |

For balance, published auxiliary-task work does **not** imply that auxiliary prediction generally fails. Voelcker et al. report no-worse-than-DQN auxiliary performance in their main original-observation setting, alongside differences between standalone feature-learning predictions and jointly trained behavior. That is evidence to evaluate the actual composition, not evidence to ban auxiliary tasks. [*When Does Self-Prediction Help? Understanding Auxiliary Tasks in Reinforcement Learning*, RLC 2024](https://tisl.cs.utoronto.ca/publication/202407-rlc-aux_tasks_in_rl/rlc2024-aux_tasks_in_rl.pdf)

**No exact published replica of “learned externality Q3 predicts well but reduces satellite network EE” was verified.** The report uses adjacent primary results with their limits stated; it does not manufacture an exact precedent.

## Four genuinely new candidates

These are **research proposals with explicit rejection conditions**, not implementation-ready launch contracts. They are derived from the objective and interface analysis; no residual plots, favorable subsets, λ sweeps, seeds, or target recalculations were used to select them. All use only predecision inputs at deployment and preserve the final pooled EE/service evaluation. They retain λ₀ for their surplus targets: positive surplus at that price is not a certificate of positive EE on a new panel. “Fixed sum” below refers to arithmetic, not permission to reopen the frozen method.

### N1. Serialized full-surplus correction

**New element:** permit C3 to alter at most one user per decision, according to a public schedule fixed independently of physical outcomes. This removes simultaneous C3 unilateral composition by construction, unlike V0.11’s prediction of simultaneous responses.

Let $n$ be a public monotonically increasing decision counter and $\sigma(n)=n\bmod100$, using the immutable user roster. Define $\Delta q_u(a)=q_u(a)-q_u(b_u)$ and

\[
d_u^{(1)}(a)=\mathbb E[G_{\lambda_0}(\mathbf b[u\leftarrow a])-G_{\lambda_0}(\mathbf b)\mid\mathcal I_t],
\]
\[
z^{\mathrm{N1}}_{3,u}(a)
=\mathbf1\{u=\sigma(n)\}\,[d_u^{(1)}(a)-\kappa\Delta q_u(a)].
\]

Enforce exact zero output for nonscheduled users structurally; do not merely hope the learner predicts zeros. Reference targets are zero. If the scheduled user has no legal action, retain native NOOP and do not reschedule to a favorable user. For a perfect scheduled-user prediction, the total score becomes $q_u(b_u)+d_u^{(1)}(a)/\kappa$; all other users execute BASE.

**Motivation:** full-global difference utilities align a unilateral intervention at a fixed background; serialization ensures the actual intervention has that shape. The residual subtraction makes the composed score’s intended quantity explicit.

**Limitation:** this is a score-completion target, not a pure non-focal externality. On scheduled decisions, exact completion replaces Q12’s ordering; it does not prove an independent three-Catfish mechanism. It deliberately misses beneficial multi-user events and may sacrifice useful C2 lookahead. A positive result would need source-replacement ablations before any three-route claim.

**Cheapest falsifier:** use an independently frozen fresh TRAIN tape with the same unilateral format, additionally capturing the declared C3 inputs or running the frozen predictor at each live anchor. Apply the declared schedule and selector; every selected joint action is a recorded unilateral profile. Kill if no action changes, pooled EE fails to exceed BASE, or service falls more than 0.001. A perfect realized-tape selector is a hindsight oracle; separately require a learner using deployable inputs to pass the same physical comparison. The already opened F1 tape is only a retrospective implementation example, never a promotion panel. Passing an anchor screen still requires separate autonomous matched trajectories before any policy-level EE claim.

**Predeclare additionally:** counter initialization/continuation across episodes, user roster, κ/λ₀, information view, exact-zero enforcement, terminal checkpoint, all worlds and learner seeds, and the null-source construction. No alternative schedules compete. **Fixed additive arithmetic: yes. Unchanged C3 method: no.**

### N2. Common-policy, remaining-episode surplus completion

**New element:** price the entire remaining trajectory following a unilateral opening intervention, with both branches thereafter following the same frozen policy $\pi_{12}$.

For the remaining $H=T-t$ decisions, without introducing discounting into the pooled objective, define

\[
d_u^{(H)}(a)=\mathbb E\!\left[
\sum_{h=0}^{H-1}(B^{u,a}_{t+h}-\lambda_0E^{u,a}_{t+h})
-\sum_{h=0}^{H-1}(B^{b}_{t+h}-\lambda_0E^{b}_{t+h})
\;\middle|\;\mathcal I_t,\ \pi_{12}\text{ after the opening}\right],
\]
\[
z^{\mathrm{N2}}_{3,u}(a)=d_u^{(H)}(a)-\kappa\Delta q_u(a).
\]

**Motivation:** this targets future beam persistence, energy, interference and association consequences using one common continuation policy. It supplies an explicit residual to the actual sealed scores instead of assuming those scores form the correct return decomposition. It is distinct from C2’s frozen-background average over three projected offsets and from all current-slot ZR/LC-SRS labels. [P8; fractional-RL and value-composition sources above]

**Limitation:** at the exact-target limit, $q_u(a)+z^{\mathrm{N2}}_{3,u}(a)/\kappa=q_u(b_u)+d_u^{(H)}(a)/\kappa$: the deployment ordering of Q12 is completely replaced for every user. Q12 remains the reference/continuation policy and training context. This relaxes “C3 owns no future term” and is particularly weak evidence for three independently useful additive mechanisms. Simultaneous independent deployment still combines unilateral action-values without a joint policy-improvement guarantee. A common continuation policy fixes one mismatch, not every mismatch.

**Cheapest falsifier:** there is **no valid temporal-effect test using only existing F1 bytes**. Freeze a small fresh TRAIN panel and a proposal rule based solely on predecision masks/identities/scores. Clone each chosen anchor, evaluate the reference plus specified opening interventions through the remaining episode under π12 with matched keyed randomness, and store transitions and pooled totals. Failure of the declared learned composed policy to beat BASE in EE/service kills the candidate even if the return predictor fits well. An oracle screen may stop spending first; its gains never admit a learner by themselves.

**Predeclare additionally:** remaining-episode horizon, no discount, future continuation policy, clone/termination semantics, fading integration rule, proposal coverage, treatment of omitted actions, and budget. Do not shorten/extend the horizon after inspecting gains. **Fixed additive arithmetic: yes. Unchanged ownership/target: no.**

### N3. Complete-beam coordination-event factor

**New element:** keep the group payoff attached to a jointly executed event rather than allocating it back into unary Shapley shares.

Let $S$ be the full set of users on an eligible reference source beam, with $3\le |S|\le k_{\max}$. The eligibility and fixed bound are declared from model/compute considerations before outcomes. Give each member one legal destination proposal from an explicit geometry/physical-identity rule. For $T\subseteq S$, let $\mathbf c^T=(\mathbf a_T,\mathbf b_{-T})$ and learn

\[
Z_S(T)=\mathbb E[G_{\lambda_0}(\mathbf c^T)-G_{\lambda_0}(\mathbf b)\mid\mathcal I_t].
\]

An explanatory diagnostic is the irreducible event interaction

\[
I_S=\sum_{T\subseteq S}(-1)^{|S|-|T|}
\mathbb E[G_{\lambda_0}(\mathbf c^T)\mid\mathcal I_t].
\]

Learn the complete action-set payoff, including partial subsets. In the first design, select only **BASE or the complete S-migration**, and execute the event atomically; partial subsets are diagnostics and learning information, not selectable alternatives. Allow **one** structurally chosen event per decision so that unmeasured interactions between simultaneously selected groups are not silently ignored. A factor-graph decoder selecting overlapping events would be a separate declared extension.

**Motivation:** complete beam extinction is a set event; satellite baseband extinction can require a still larger set. Non-focal interference and maximum-power changes remain in the measured network surplus. These follow directly from the canonical physical model, independently of favorable residuals. This is not another two-player LC-SRS split. [P7, P8; coordination-graph sources above]

**Cheapest falsifier:** a structurally selected three-user source beam, one fixed alternative each, needs eight subset profiles. The unilateral infrastructure supplies BASE plus three singles; add four joint evaluations per anchor and fading draw. Kill if the prescribed full event lacks positive pooled EE/service support, if it requires unavailable deployment information, or if the learned selector loses the gain. **Positive $I_S$ alone does not pass.** If the declared topology is absent, report insufficient support; do not substitute a favorable group.

**Predeclare additionally:** full membership/eligibility rule, destination rule, maximum group size, all subset profiles, joint decoding/atomic adoption, graph/message budget if used, and proposal-conflict handling. **Fixed per-user additive deployment: no.** OPS-3 is a feature source, not a ready-made joint decoder. This is the strongest conceptual follow-up, but a different controller.

### N4. Whole-proposal surplus/service gate

**New element:** use C3 to judge whether an entire proposed joint move should be accepted, with BASE as fallback.

Freeze a target-independent proposal generator $\mathbf c_t=\mathcal P(\mathcal I_t,\mathbf b_t)$. It may propose a geometry-defined beam migration or a predeclared near-tie action-set alternative; it may not use a list of historically favorable actions. Learn two outputs of one C3 predictor for that proposal:

\[
z_{3,G}=\mathbb E[\Delta B-\lambda_0\Delta E\mid\mathcal I_t,\mathbf c_t,\mathbf b_t],
\qquad z_{3,S}=\mathbb E[\Delta\mathrm{service}\mid\mathcal I_t,\mathbf c_t,\mathbf b_t].
\]

For a prospectively specified uncertainty procedure producing lower bounds $L_G,L_S$, execute

\[
\mathbf a_t=
\begin{cases}
\mathbf c_t,& L_G>0\ \land\ L_S\ge-0.001,\\
\mathbf b_t,&\text{otherwise}.
\end{cases}
\]

The service target’s denominator and horizon must match the declared gate; a per-slot tolerance is not automatically an episode guarantee. Even a valid bound on the frozen-λ₀ surplus certifies only that surrogate. A formal baseline-EE guarantee additionally requires the relevant baseline ratio as price and the appropriate policy horizon/state distribution. If valid bounds cannot be established, call these calibrated prediction thresholds and make **no formal safety claim**; actual EE remains an empirical terminal test.

**Motivation:** benchmark a whole proposal against BASE, preserving its joint physical meaning. A large auxiliary score does not automatically override Q12, and independently accepted fragments cannot form an unexamined hybrid. SPIBB and wireless baseline-switching supply methodological precedent, not an inherited guarantee.

**Cheapest falsifier:** record BASE and one prescribed joint proposal per fresh anchor, alongside unilateral data already generated. Purely unilateral proposals need no new current-slot physics; general joint proposals need one matched evaluation per anchor/draw. Fit/calibrate only on declared fitting worlds; evaluate accepted complete proposals on separate fresh worlds. Kill if the rule never acts, its held-out EE fails to beat BASE, service fails, or its declared uncertainty coverage fails. A real policy-level claim additionally needs autonomous trajectories.

**Predeclare additionally:** proposal generator, optional tolerance ε and its non-outcome derivation, output horizon, uncertainty family/coverage level, calibration split, fallback, threshold, and terminal model. This is a whole-vector gate, not a new β/τ working point on the already failed ZR classifier. **Fixed additive deployment: no; scalar-Q3 interface: no.** It is a distinct controller proposal.

## What can reasonably fit in the remaining week?

The estimates below concern **a reproducible positive expected pooled-EE effect, with service noninferiority**, not a lucky positive two-step screen. The individual rows are subjective judgments **conditional on successful, timely implementation and completion of the declared evaluation**, with fresh development worlds and a fixed terminal model. Unlike the overall one-week estimate, they exclude failure to finish the work. They are not independent probabilities and must not be added.

| Candidate | Retains per-user additive argmax? | My probability judgment | Current-paper assessment |
|---|---|---|---|
| N1 serialized correction | Yes, with a new hard schedule and residual target | **5–10%** for a reproducible positive effect within one week; lower for a material three-route contribution | Cheapest scientific diagnostic, but deliberately excludes coalition gains and can replace Q12 ordering for the selected user. Do not make paper delivery depend on it. |
| N2 full remaining-episode completion | Yes, with new horizon/ownership | **10–20%** within one week if branch infrastructure is already reliable | More aligned temporal target, but expensive and still unilaterally composed; not a quick source-label substitution. |
| N3 atomic complete-beam events | No | **25–40%** for a positive follow-up development result with adequate implementation time | Most credible way to investigate the physical coordination hypothesis; not evidence for the frozen three-head rule. |
| N4 whole-proposal gate | No | **15–30%** for a positive follow-up development result with adequate implementation time | May preserve a baseline while exploiting sparse opportunities; proposal quality and uncertainty are unresolved. |

The overall **~10% one-week fixed-sum estimate is unconditional on finishing implementation/evaluation**, whereas the candidate rows are conditional. It concerns a feasible, prospectively selected program within that week, not unlimited completed trials of every design. Observability and joint-response risks also correlate the candidate outcomes. If “fixed deployment” additionally means **unchanged current-slot externality ownership and unchanged information/output restrictions**, N1/N2 are ineligible and I put the chance of a legitimate same-design rescue below 5%. No existing admitted route remains open.

I recommend spending this paper’s remaining week on the already declared C1/C2 evaluation and a careful C3 negative-result section. Parallel compute cannot remove the sequential dependencies of a new target: physical support, deployable prediction, actual composition, autonomous evaluation, and source ablation. The F1 runtime of 383 seconds shows that a tiny current-slot screen was cheap; it is not a benchmark for temporal cloning or joint-factor training. [P3, P5]

If the authors nevertheless reserve a small independent research allocation, **N1 is the only candidate here whose new selected profiles are guaranteed to lie in a unilateral tape**. Its value would be a sharply bounded test of serialization/completion, not a promised C3 rescue. N3 is the preferred follow-up direction if changing the controller is acceptable. A larger learner, another loss, another conditional-ZR average, and λ/κ/sign variants are not the recommendation.

### Integrity requirements shared by any future experiment

Before computing any candidate targets or decisions, freeze its full formula and units; information availability; background/continuation policy; worlds and excluded historical worlds; seeds; fitting/calibration/held-out roles; masks/tie rules; proposal enumeration; horizon; terminal checkpoint; compute budget; primary pooled-EE/service estimands; minimum actionable effect if one is claimed; uncertainty method; falsifier; and invalid-run handling. Missing support must have a predetermined disposition.

Use fresh TRAIN development panels; TEST stays closed. Previously opened F1/R7 or older residuals cannot become acceptance data or choose the mechanism, threshold, sign, scale, subgroup, horizon, or seed. Any old-tape exercise is explicitly retrospective. State the independent mathematical/physical motivation and disclose that the research question was prompted by prior failure.

For parallel candidates, seal a priority rule or a multiplicity-controlled selection/confirmation protocol **before** outcomes. Do not launch all candidates, report the best positive score as confirmation, or invent a successor after its predecessor fails. A failure at the candidate’s terminal gate ends that experiment; an invalid run permits only demonstrated infrastructure repair. Learner seeds are not independent physical worlds. Preserve separate model-fit, teacher/oracle, deployment, and retrained neutral-source ablation results. [P4, P5]

This report specifies candidate-level formulas and falsifiers, but does not manufacture missing seed lists, hardware budgets, fitting schedules, or uncertainty assumptions. Those execution bindings must be concretely frozen in a later handoff before any run; none of the proposals is currently launch-ready.

## Paper framing: four sentences

We investigated eight families of training-time coordination/externality signals for an auxiliary third head under a fixed additive deployment rule, and no candidate completed the prescribed progression to three-route efficacy evaluation. In the LC-SRS development gate, the learner passed the held-out prediction criteria (balanced accuracy 0.705 versus 0.626 for the matched placebo), while the prescribed coalition physical signature and learned composition decreased pooled energy efficiency by 0.049% and 0.660%, respectively. Separately preregistered cost-shared and energy-share corrections decreased EE by 1.328% and 4.536% in a two-anchor TRAIN kill screen, with the former also failing service noninferiority. These bounded negative results show that predictive auxiliary credit did not establish beneficial composition in the tested controller; they do not establish that cooperative credit assignment or alternative coordination interfaces are intrinsically ineffective.

## Research and access limits

Research covered primary COIN/difference-reward, counterfactual actor–critic, Shapley, potential-game/smoothness, fractional RL, coordination-graph, constrained/lexicographic selection, wireless EE, and prediction/control-mismatch sources. Follow-up reads checked theorem assumptions and the package’s actual price, cost-share, action, and tape semantics. Searching stopped when each requested decision slot had primary support or an explicit unresolved limitation; this is not an exhaustive historical census.

The strongest literature claims were checked in original papers or publisher records. The Agogino–Tumer discussion is limited to its accessible publisher abstract. Ng’s original metadata was verified, while the readable Lu et al. primary proof supports the shaping discussion. Preprints and adjacent-domain analogies are labeled. There is no verified theorem or empirical literature estimate of the success probability for this exact LEO architecture.

The report is delivered as editable Markdown with equations, exact-comparison tables, and descriptive source links. Structural checks cover the full document; no paginated visual-layout claim is made.
