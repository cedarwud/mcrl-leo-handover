# Learning an Anchored Coalition-Interaction Residual

## Decision

**Retain the anchored interaction residual as the target for the next diagnostic stage. Replace any unproved scalar aggregation of the relational inputs, audit the label definition, and test the selection rule before spending more training compute.** Switching from the residual to a full-value target is not, by itself, a remedy for missing information.

The formulation has a standard mathematical interpretation: it is the part of an anchored set-function decomposition remaining after the constant and singleton components have been removed. It is not inherently ill-defined or unlearnable. The more immediate risks are feature non-identifiability, incorrect assumptions about interaction order, insufficient within-anchor intervention coverage, and a selector whose behavior is not actually being driven by the learned residual.[^1][^2]

The strongest conclusion available from the scalar-sum discovery is conditional: **when two physically feasible inputs have the same complete encoded representation and different residuals, no deterministic predictor of that representation can be correct on both.** A larger model, different architecture, different regression target, or additional optimization cannot remove that information loss. Whether the actual implementation has such a collision requires inspection of the evaluator and the complete input representation.

The mathematical identities and counterexamples below are direct derivations. Published architecture and recovery results are identified separately. Recommendations are engineering judgments, not guarantees for an uninspected implementation.

## 1. What the residual actually represents

Fix the context, anchor assignment, and one proposed alternative action for each agent. Define a Boolean-mask value function

\[
v(S)=F(a_S,a^0_{-S}),\qquad S\subseteq N.
\]

This convention matters: the same agent must have the same proposed action when it appears in different subsets of this particular mask game. Otherwise the subset identities compare different interventions.

The Möbius coefficients, also associated with Harsanyi dividends in cooperative games, are

\[
m(T)=\sum_{S\subseteq T}(-1)^{|T|-|S|}v(S),
\qquad
v(A)=\sum_{T\subseteq A}m(T).
\]

Consequently,

\[
m(\varnothing)=v(\varnothing),\qquad
m(\{i\})=v(\{i\})-v(\varnothing)=d_i,
\]

and the specified residual is exactly

\[
\boxed{\Psi(A)=\sum_{\substack{T\subseteq A\\|T|\ge 2}}m(T).}
\]

Möbius representations of set functions and anchored decompositions are established constructions. Anchored decomposition is also closely related to cut-HDMR, or cut high-dimensional model representation.[^1][^2]

**For a two-agent coalition, the residual is a pure pair interaction. For a larger coalition, it is the sum of every contained interaction of order two and above.** It is not generally the single coefficient \(m(A)\), and it is not generally a purely second-order function.

This distinction has an immediate modeling consequence. Pairwise physical coupling does not imply pairwise coalition value. For example, a threshold applied to the sum of several incoming couplings can switch only when three or more agents move. That produces a higher-order membership interaction even though the physical inputs were pair-indexed. A nonlinear function of shared resource occupancy can do the same.

There is no algebraic identifiability problem when the full function, anchor, and proposed actions are specified: the coefficients and the residual are unique. However, this does not mean that sparse observations identify them, or that an arbitrary encoder preserves them. Nor does anchoring at empty and singleton sets make the residual mean-zero or orthogonal under the training distribution. Anchored and distribution-based ANOVA decompositions are different constructions.[^2]

### 1.1 When a pairwise residual is exact

Suppose the value itself truly has the pair-additive form

\[
F(a)=\sum_i f_i(a_i)+\sum_{i<j}g_{ij}(a_i,a_j).
\]

Then direct cancellation gives

\[
\Psi(A)=\sum_{i<j\in A}\delta g_{ij},
\]

where

\[
\delta g_{ij}=g_{ij}(a_i,a_j)-g_{ij}(a_i,a_j^0)
-g_{ij}(a_i^0,a_j)+g_{ij}(a_i^0,a_j^0).
\]

Edges between a moving agent and a nonmoving agent cancel in this genuinely pair-additive model. That cancellation cannot be assumed for nonlinear shared-resource effects: agents outside the coalition can still affect the interaction through their contribution to resource loads, interference, or operating thresholds.

An exact test of the degree-two approximation on a labeled coalition is

\[
R_{\ge3}(A)=\Psi(A)-\sum_{i<j\in A}\Psi(\{i,j\}).
\]

For a triple, this equals its third-order Möbius coefficient. For a larger coalition, it is the sum of all contained coefficients of order three and above. Measure it at operational coalition sizes and near nonlinear operating boundaries, not only on easy pairs and triples.

## 2. Residual regression, numerical precision, and statistical noise

### 2.1 Subtraction does not create random noise in an exact deterministic label

Three different problems need separate treatment.

**Numerical cancellation.** A floating-point evaluator can lose a small interaction while calculating large counterfactual values. The important issue is error already present in the operands, not simply the act of subtracting similar numbers. A float64 audit should run through the evaluator, not merely cast already-rounded float32 outputs to float64. Where the value decomposes into physical contributions, cancel unchanged contributions before accumulating the contrast. Higher-precision spot checks and accurate summation can reveal whether the residual scale is numerically resolved.[^3]

**Stochastic estimation noise.** When each counterfactual is an estimated expectation, the noise depends on the joint evaluation protocol. Writing \(k=|A|\),

\[
\Psi(A)=v(A)-\sum_{i\in A}v(\{i\})+(k-1)v(\varnothing).
\]

For the vector of counterfactual errors with covariance matrix \(\Sigma\), the residual-error variance is

\[
\operatorname{Var}(\widehat\Psi-\Psi)=c^\top\Sigma c,
\]

with coefficients \(c=(1,-1,\ldots,-1,k-1)\). Under independent, equal-variance errors on the distinct evaluations and one reused baseline estimate,

\[
\operatorname{Var}(\widehat\Psi-\Psi)
=\{1+k+(k-1)^2\}\sigma^2
=(k^2-k+2)\sigma^2.
\]

This is a conditional calculation, not a claim about deterministic exact evaluations. Shared baseline estimates also correlate the errors of different training labels.

Paired simulations or common random numbers can reduce the variance of a contrast when the induced covariance supports cancellation. Their effectiveness is not guaranteed merely by using the same seed.[^4] Independent-noise formulas should not be applied to a coupled simulator without checking its covariance structure.

**Missing-feature uncertainty.** Deterministic residuals can appear noisy after encoding because several physically different states map to the same features. This is an information problem, not simulator noise. Its exact criterion is developed in Section 3.

### 2.2 Learned singleton values can change the meaning of the target

With exact baseline but learned singleton estimates \(\widehat d_i=d_i+\epsilon_i\), a label formed as

\[
v(A)-v(\varnothing)-\sum_i\widehat d_i
\]

equals

\[
\Psi(A)-\sum_i\epsilon_i,
\]

not the true interaction residual. A head trained on this quantity is also correcting singleton-model errors. This can be an intentional end-to-end predictor, but its interpretation has changed. Forcing the head to zero on singletons is inconsistent with using those noisy singleton-subtraction labels at singleton inputs unless their error is handled separately.

Use exact singleton differences for an interaction-identification experiment. When joint learning is necessary, supervise the baseline, singleton differences, and coalition contrasts explicitly. Empty/singleton anchoring alone does not uniquely separate arbitrary internal learned components.

### 2.3 Learning the full value is not automatically better

For exact fixed baseline and singleton terms, construct

\[
\widehat v(A)=v(\varnothing)+\sum_{i\in A}d_i+\widehat\Psi(A).
\]

Then, identically,

\[
(\widehat v(A)-v(A))^2=(\widehat\Psi(A)-\Psi(A))^2.
\]

Renaming this model a full-value regressor changes nothing about its squared-error objective.

A separately trained unrestricted full-value model is different. It can use extra raw-value observations, share useful physical representations, and potentially learn better. But a high full-value accuracy score need not imply accurate interactions. If its errors satisfy \(|e(S)|\le\epsilon\) on all counterfactuals needed for a coalition of size \(k\ge2\), the contrast error obeys

\[
|\widehat\Psi(A)-\Psi(A)|\le2k\epsilon.
\]

This is a worst-case bound. It is equally important that any modular error

\[
e(S)=b+\sum_{i\in S}u_i
\]

cancels exactly. Thus neither “full-value error always explodes” nor “accurate full-value regression guarantees accurate interaction” is correct. What matters is the nonadditive structure of the errors.

**Recommended parameterizations:** a directly supervised anchored residual with explicit pair/resource structure; a shared full-value model with explicit contrast supervision when additional raw-value data are genuinely available; or a validated low-order/sparse Möbius model. An orthogonal basis under a chosen mask distribution can improve linear-regression conditioning, but its components are not automatically the anchored coefficients. A basis change cannot recover discarded inputs or create missing observations.

## 3. A constructive feature-sufficiency test

Let \(X\) denote the full physical input: context, anchor, coalition membership, proposed actions, couplings, resource state, and relevant nonmember information. Let \(T(X)\) be the **complete representation actually available to the predictor**, including every auxiliary branch and context channel.

The exact criterion is

\[
\boxed{\exists q:\ \Psi(X)=q(T(X))
\iff
T(x)=T(x')\Rightarrow\Psi(x)=\Psi(x')\quad\text{for all feasible }x,x'.}
\]

Necessity follows because a deterministic function gives the same output for the same input. For sufficiency, define \(q(t)\) to be the common residual of the inputs mapping to \(t\). The implication makes that definition unambiguous.

This establishes information sufficiency, not a guarantee that a finite neural network can learn the resulting function efficiently. Regularity, architecture, coverage, and sample complexity remain separate questions. Preserving everything needed to reconstruct \(F\) is sufficient but may be unnecessarily strong: discarded information that affects only constant and singleton components need not matter to \(\Psi\).

### 3.1 An opposite-sign collision from the same scalar sum

Consider three binary agents, all anchored at zero, with a coalition proposing to set all three to one. Let

\[
F_W(x)=\sum_{i<j}(W_{ij}^2-1)x_ix_j.
\]

The baseline and every singleton value are zero. Compare two nonnegative coupling arrays:

| Case | \((W_{12},W_{13},W_{23})\) | Scalar sum | Exact residual |
|---|---|---:|---:|
| P | \((2,0,0)\) | 2 | +1 |
| Q | \((1,1,0)\) | 2 | −1 |

The coalition size, proposed actions, singleton effects, and scalar sum agree, but the target changes sign. A representation retaining only this coupling sum, with all other inputs equal, cannot predict both correctly.

This is a mathematical counterexample for the stated class of pair-coupled values, **not evidence that the actual evaluator has precisely this functional form**. It also does not establish a collision when another context channel already encodes the coupling array.

The caveat is substantive. If the summed terms are already the exact pair contributions and the residual is exactly their sum, the scalar is sufficient. If the target is \(\Psi(A)=\sum_{i<j\in A}W_{ij}\), there is no information loss for that target. The audit must establish what was summed: raw couplings, transformed pair effects, already-correct interaction contributions, or quantities that still need resource-dependent processing.

Even retaining the unordered multiset of all edge weights may be insufficient when endpoint identity or shared-resource incidence matters. Preserve which relation connects which entities, including direction where the coupling is asymmetric.

### 3.2 A quantitative lower bound

For square-integrable targets, the least possible population squared error using features \(T\) is

\[
\inf_q\mathbb E[(\Psi-q(T))^2]
=\mathbb E[\operatorname{Var}(\Psi\mid T)].
\]

This follows by expanding the squared error around \(\mathbb E[\Psi\mid T]\). If two indistinguishable inputs occur with equal probability and their target values differ by \(\Delta\), their minimum average squared error is \(\Delta^2/4\). Any single prediction also has worst-case absolute error at least \(|\Delta|/2\) on the pair. The example above therefore has irreducible mean squared error 1 on its equally weighted two-case distribution.

### 3.3 How to prove sufficiency or discover failure before training

**Use the evaluator as a dependency graph.** Trace every quantity that can affect the residual: endpoint-specific couplings, resource occupancy, nonlinear transformations, thresholds, and effects of nonmoving agents. Construct a representation from which those required computations can be reproduced. Where inputs are discarded, demonstrate algebraic cancellation in the contrast rather than assuming the information is irrelevant.

**Search for feasible feature collisions.** Redistribute coupling mass while preserving its sum, swap endpoints while preserving aggregate statistics, or redistribute demand across resources while preserving total demand. Hold the entire encoded input fixed and evaluate the residual in both cases. A single valid collision disproves sufficiency. A search that finds none is not a general proof unless it exhausts the relevant domain.

**Use small exhaustive domains.** Four to eight agents can expose feature collisions, higher-order effects, and counterfactual inconsistencies cheaply enough to diagnose the representation before a large training run. A sufficiently expressive model should fit a small deterministic dataset when its features separate the targets. Successful memorization is not a sufficiency proof, but failure on such a dataset is a useful implementation or representation warning.

Near-collisions require extra assumptions. Two close feature vectors do not prove impossibility for unrestricted predictors. For an \(L\)-Lipschitz predictor, however, a target difference exceeding \(L\|T(x)-T(x')\|+2\epsilon\) rules out uniform error \(\epsilon\) on that pair. Exact collisions require no regularity assumption.

## 4. Architecture: preserve relationships, then choose the model

### 4.1 Deep Sets do not exclude pairwise interactions

A nonlinear Deep Sets model has the form

\[
f(A)=\rho\!\left(\sum_{i\in A}\phi(x_i)\right).
\]

It is not the same as an additive scalar model \(\sum_i f_i(x_i)\). A direct counterexample to the claimed limitation is

\[
\sum_{i<j}x_ix_j
=\frac12\left[\left(\sum_i x_i\right)^2-\sum_i x_i^2\right].
\]

Taking \(\phi(x)=(x,x^2)\) represents this pair interaction exactly with a nonlinear readout. Deep Sets have universality results under specified domain and representation assumptions. Their latent dimensionality can be a real worst-case limitation; the continuous scalar-set lower bounds in Wagstaff and colleagues should not be interpreted as a universal practical width prescription for every vector-valued problem.[^5][^6]

The important distinction is **a learned multidimensional aggregate versus a fixed scalar compression before learning**. Neither Deep Sets nor a transformer can reconstruct arbitrary external edge data that no input channel contains.

### 4.2 First baseline: explicit signed pair factors

A useful degree-two baseline is

\[
\widehat\Psi_2(A)
=\sum_{i<j\in A}h_\theta(z_i,a_i^0,a_i,z_j,a_j^0,a_j,e_{ij},Z).
\]

The output must allow both signs. This structure gives exact empty/singleton zeros without multiplying a generic scalar output by a cardinality gate. Directional relations need the appropriate ordered-pair treatment or a symmetrization that preserves their meaning.

For the terms to represent true pair-order coefficients, their inputs may include fixed anchor context but should not change with the rest of the selected coalition. Once a factor receives messages from all selected members, it can carry higher-order effects; that may improve prediction, but its output is no longer an identifiable pair Möbius coefficient. An anchored four-term construction from a learned pair potential also enforces zero contribution when one endpoint makes a no-op move.

For 100 agents, one fixed set of proposed actions has 4,950 unordered pairs. This is manageable for some models, but candidate-coalition search and many alternatives per agent multiply the cost. Parameter sharing and low-rank action-pair representations can therefore matter.

Relation Networks provide a primary example of explicit relational computation.[^7] More directly relevant, Deep Coordination Graphs factor multi-agent action values into learned pair payoffs, using parameter sharing and low-rank approximations, with demonstrations in predator–prey and StarCraft micromanagement. Those results support the structural approach, not a guarantee for a 100-agent anchored-residual learner.[^8]

### 4.3 Shared resources: use agent–resource structure

A pair sum is not the natural representation when nonlinear resource loading is the dominant mechanism. An agent–resource graph or factor graph can preserve occupancy, capacity, interference neighborhoods, and relevant nonmember load.

For an illustrative resource model with additive load changes, an anchored residual can be built as

\[
\widehat\Psi_{\mathrm{res}}(A)=\sum_r\left[
 g_r\!\left(\ell_r^0+\sum_{i\in A}\delta\ell_{ir}\right)-g_r(\ell_r^0)
 -\sum_{i\in A}\{g_r(\ell_r^0+\delta\ell_{ir})-g_r(\ell_r^0)\}
\right].
\]

This has exact empty/singleton zeros and can express interactions above order two through nonlinear \(g_r\). It is appropriate only when the specified resource variables are sufficient and load changes have the assumed additive form. It is a proposed parameterization, not a claim that every shared-resource system reduces to one scalar load per resource.

Combining unrestricted edge factors and unrestricted resource factors can introduce non-unique internal decompositions. The total predictor may still be useful, but individual learned components should not automatically receive causal or Möbius interpretations.

### 4.4 Set Transformers and graph networks: evidence and limitations

Set Transformers provide attention-based interaction modeling. Their original experiments favored attention on some relational tasks, but not uniformly: simple max pooling performed better in the reported maximum-regression comparison. This supports task-matched inductive bias rather than a universal transformer ranking.[^9]

For this application, attention should receive the actual pair attributes through an edge-aware mechanism, edge tokens, or a graph representation. Standard attention over member features does not reveal unavailable physical couplings.

Graph networks also have expressivity limits. Standard message-passing families can fail to distinguish structures beyond their Weisfeiler–Leman discrimination power.[^10] For example, with identical initial node features, a six-cycle and two disjoint triangles have identical node degrees and can remain indistinguishable to ordinary message passing, although a triangle-dependent target differs. Supplying the graph and choosing an architecture capable of using its relevant structure are separate requirements.

Variable-size processing is also not a size-generalization guarantee. Published work identifies failures associated with changes in local graph structure between training and larger test graphs.[^11] Coalition size, resource saturation, and coupling density should therefore appear explicitly in validation design.

**Architecture judgment:** start with signed shared pair factors plus the smallest justified resource representation. Add an edge-aware graph or set transformer when measured higher-order/context dependence requires it. No primary study identified here establishes a best architecture for this exact sparse-label, contextual, approximately 100-agent residual problem.

## 5. Getting more information from expensive evaluations

### 5.1 Audit the statement “four counterfactuals per coalition”

For \(k\ge2\), the stated residual requires the baseline, \(k\) singleton values, and the coalition value: **\(k+2\) distinct values before reuse**. Four suffice for a pair. With a valid cached baseline and singleton values, an additional coalition can require only one new evaluator call.

Four calls can instead calculate an interaction between two disjoint blocks:

\[
D(B,C)=v(B\cup C)-v(B)-v(C)+v(\varnothing).
\]

But

\[
D(B,C)=\Psi(B\cup C)-\Psi(B)-\Psi(C).
\]

Thus a two-block interaction is not the entire residual of their union unless within-block interactions vanish or are added back. This is an accounting question to check in the implementation, not sufficient evidence that its labels are wrong.

The cache key must include the anchor, context, proposed actions, evaluator configuration, and any randomness relevant to the estimand. Reusing singleton values after their intervention or context changes does not preserve the identity.

### 5.2 Overlapping subsets reuse evaluations, not independent information

A practical design is to fix proposed actions for a small block and evaluate all its subset masks, with nonmembers fixed at the anchor. For six agents, 64 values supply:

- 57 nontrivial residual targets: \(2^6-1-6\).
- Every Möbius coefficient within that block.
- 240 conditional pair contrasts: \(\binom62 2^{6-2}\).

The conditional contrast is

\[
\Delta_{ij}v(S)=v(S\cup\{i,j\})-v(S\cup\{i\})
-v(S\cup\{j\})+v(S),
\]

and its exact expansion is

\[
\Delta_{ij}v(S)=\sum_{U\subseteq S}m(U\cup\{i,j\}).
\]

These contrasts can expose context dependence and higher-order effects. However, they still derive from only 64 scalar observations; they are not hundreds of independent measurements. Loss weighting and uncertainty estimates should respect their shared origin.

When an expensive evaluation already computes per-agent or per-resource contributions, retaining these outputs can add supervision at little additional evaluation cost. This is valid only when those contributions correspond to the intended physical or algebraic decomposition.

### 5.3 One coalition evaluation does not label all its subsets

A coalition observation provides the equation

\[
\Psi(A_t)=\sum_{\substack{T\subseteq A_t\\|T|\ge2}}m(T).
\]

It constrains the sum of the contained interactions, not each one separately. In an exact pairwise model, this becomes

\[
y=X\theta,\qquad X_{t,ij}=\mathbf 1\{i,j\in A_t\}.
\]

There are 4,950 unconstrained pair coefficients for 100 agents with one fixed alternative action each. Dense per-anchor identification requires adequate design rank. Repeated grand-coalition observations alone give only one row pattern and cannot identify the pair coefficients.

Under exact pair-additivity, the baseline, all singletons, and all pairs determine the entire mask game: \(1+100+4,950=5,051\) values before caching. Fewer observations can suffice with a justified structure such as shared parametric dependence, sparsity, or low rank. More anchors help only insofar as that structure ties their functions together; independent arbitrary games do not identify one another.

### 5.4 Sparse Möbius learning is established, but its assumptions matter

Kang and colleagues’ NeurIPS 2024 work, *Learning to Understand: Identifying Interactions via the Möbius Transform*, gives recovery algorithms with sample bounds including \(O(Kn)\) and, in a low-degree regime, \(O(Kt\log n)\). Its theorems impose specific sparsity, support-distribution, coefficient, and asymptotic assumptions; the noise result uses a specified measurement-noise model. They are not blanket guarantees for every approximately sparse physical system.[^12]

This is a credible alternative when measured interaction spectra are sparse and query access matches the recovery design. It is not a reason to fit an unrestricted table of all \(2^{100}\) Möbius coefficients. Substantial high-order but structured resource effects may be better represented by a small nonlinear resource model than by a sparse interaction table.

SHAP-IQ and SVARM-IQ are relevant examples of reusing sampled values for interaction estimation, but Shapley-style indices average interactions over contexts. They are not interchangeable with a fixed-anchor residual.[^13][^14] SHAP zero similarly illustrates amortizing explanation work across future inputs after constructing a shared function sketch; its biological-sequence results and global-function assumptions do not establish sample efficiency for unrelated games at different anchors.[^15]

### 5.5 Make labels informative for selection

A large number of independently sampled anchors does not substitute for informative variation among candidate coalitions at each anchor. Include multiple coalitions at comparable sizes, overlapping subsets, and targeted variation near nonlinear resource boundaries. Under uniform sampling over all masks of 100 agents, cardinality concentrates near 50; such a design does not cover small profitable coalitions well.

Evaluate residual prediction against both a zero-residual baseline and a size-only baseline. Report errors by coalition size and resource regime, and assess ranking within the same anchor and size. For selection, measure realized gain, regret against an exactly scored candidate panel, and recovery of known profitable small coalitions. Full-value accuracy or pooled residual correlation can hide the distinctions the coordinator needs.

Target normalization is permissible, but predictions must be returned to physical score units before selection. Dividing the deployed score by coalition size is an objective change, not merely a numerical stabilization. Avoid percentage-error metrics on residuals that frequently cross zero.

## 6. Diagnosing an always-grand-coalition selector

### 6.1 Establish what the selector should maximize

When the intended objective is total improvement with an optional execution cost, the correct score is

\[
G(A)=\sum_{i\in A}d_i+\Psi(A)-c(A),
\]

not the residual alone. If the scientific objective is specifically to find strongest interaction, maximizing \(\Psi\) is a different, legitimate task, but it should not be described as maximizing total value improvement.

The existence of a profitable small coalition does **not** show that choosing the grand coalition is wrong. A decisive example requires a feasible small coalition with a strictly better intended score than the grand coalition, or a genuine size preference or budget in that objective. The empty coalition should score zero improvement when no execution cost is incurred; a singleton can be profitable even though its interaction is zero.

### 6.2 A size-correlated aggregate is a plausible mechanism, not a diagnosis

A sufficient conditional explanation is: every added member makes the encoded aggregate nondecreasing; the fitted score is nondecreasing in that aggregate; no other score term or feasibility constraint offsets the increase; and the grand coalition is available. Under those assumptions, the grand coalition maximizes the predicted score.

The presence of a scalar sum establishes none of the monotonicity assumptions by itself. A network can learn a decreasing or nonmonotone function of a scalar. It can also choose the grand coalition for reasons unrelated to the residual representation.

**Near-zero head at early epochs.** If \(\widehat\Psi\approx0\), a total-value selector behaves approximately as \(\arg\max_A\sum_{i\in A}d_i\). With all singleton gains positive and no restricting costs or constraints, the grand coalition is exactly what this score selects.

**Accumulating bias.** An upward error \(b\) per predicted pair contributes \(b\binom{k}{2}\). A bias of 0.01 per pair gives 49.5 at size 100 and 0.01 at size two. A generic head multiplied by \(k(k-1)\) can have analogous scale effects. Empty/singleton zeros do not prevent this.

**Selection or implementation rules.** An append-only search without a stop option, a candidate generator lacking small coalitions, deterministic tie-breaking, an incorrect coalition mask, missing costs, inconsistent inverse normalization, or clipping a signed residual to nonnegative values can all create size bias. These are possibilities to test, not claims about the implementation.

**Model exploitation.** Maximizing estimated scores can select favorable prediction errors; offline model-based optimization can also push toward poorly supported inputs. The optimizer’s curse and conservative objective-model literature document related phenomena.[^16][^17] Neither phenomenon alone predicts that the selected coalition must specifically have size 100.

### 6.3 The highest-information selector checks

| Check | Interpretation |
|---|---|
| Exactly score a fixed candidate panel containing the empty set, known-good small sets, intermediate sizes, and the grand coalition; run the same selector | If a strictly inferior grand coalition still wins, investigate score assembly, feasibility, search, indexing, or ties rather than residual learnability. If the grand coalition is truly best in the panel, the symptom is not a failure on that panel. |
| Replace only the residual head with exact zero | If behavior remains all-agents, the learned interaction is not required to explain the behavior. Inspect singleton gains, costs, defaults, and search. |
| Log predicted residual, exact residual, singleton sum, cost, and final score separately by size and checkpoint | Distinguishes undertrained shrinkage, accumulating bias, unit errors, and actual size preference. |
| Compare size-only, scalar-aggregate, explicit-pair, and resource-aware models on matched within-anchor/within-size cases | Separates a cardinality shortcut from usable relational information. A favorable pooled metric alone is insufficient. |
| Test candidate ordering, permutation consistency, no-op members, and calibrated head-scale changes | Exposes tie-breaking, masking errors, unjustified cardinality effects, and sensitivity to head scale. Scale changes are diagnostics, not permission to alter the objective arbitrarily. |

For a nested addition, the relevant predicted marginal is

\[
\widehat G(A\cup\{i\})-\widehat G(A)
=d_i+\widehat\Psi(A\cup\{i\})-\widehat\Psi(A)
-[c(A\cup\{i\})-c(A)].
\]

Compare this quantity with the exact marginal. The sign of the total residual is not the same question as whether adding the next member is beneficial.

A useful no-op identity is that adding a member whose proposed action equals its anchor action must not change the physical residual. An explicit membership cost can change the total score, but not the underlying counterfactual interaction. This test is particularly informative for cardinality-gated models.

## 7. Decision before further compute

The immediate decision is not “Deep Sets versus transformer” or “residual versus full value.” It is whether the current encoded representation identifies the target and whether the selector uses the intended score.

**First, verify the labels and numerical scale.** Resolve the four-evaluation issue; check the exact versus learned singleton convention; check precision inside the evaluator; and use an exactly scored candidate panel to test selection independently of learning.

**Second, establish relational sufficiency.** Produce a real feasible collision or demonstrate the evaluator’s factorization through the retained features. Preserve edge endpoints, direction, relevant resource state, and anchor context. A change from one scalar sum to a list of unlabeled values may still omit necessary incidence information.

**Third, measure the interaction order.** Use cached baseline/singleton values and overlapping small subsets to test whether pairwise reconstruction leaves an operationally important higher-order tail. Include the congested or threshold-adjacent cases that are most likely to challenge the approximation.

**Fourth, compare the smallest justified models.** Train a signed anchored pair-factor residual and the minimal resource-aware extension supported by the order audit. Evaluate within-anchor selection quality, not only regression fit. Add an edge-aware transformer or a multi-task full-value surrogate when the observed failure mode justifies its additional flexibility.

The established mathematics does not reject the residual formulation. What remains unresolved without the actual evaluator and dataset is whether the current scalar aggregation is sufficient for this particular target, whether its higher-order structure is simple enough for economical learning, and which architecture will generalize best. Those are meaningful application-specific research questions, but the low-cost tests above can distinguish information loss, model mismatch, and selection errors before another expensive training run.

## Appendix: Interpretation and reproducibility boundaries

The feature-collision example is deliberately synthetic; it proves an impossibility for a class of encoders and targets, not the existence of that exact collision in a satellite or other physical evaluator. Its two residuals are obtained by direct arithmetic: \((4-1)+(0-1)+(0-1)=1\), versus \((1-1)+(1-1)+(0-1)=-1\).

The six-agent subset counts and the 100-agent pair-reconstruction count are combinatorial identities, not measured runtime or sample-efficiency results. Multiple derived contrasts from one set of oracle values must not be reported as independent evaluator calls or independent information.

The exact feature-factorization criterion proves representability by some function. It does not imply continuity, finite-network realizability, useful approximation rates, or out-of-distribution generalization. A feature set can be information-sufficient and still yield a difficult learning problem.

The pairwise value identity assumes the entire value is pair-additive. Merely observing that interference or another physical input is indexed by pairs does not establish that assumption. Thresholds, nonlinear resource transformations, and action-dependent environmental responses must be included in the order audit.

The selector diagnostics identify behavior on the tested candidate panel. They do not claim that panel contains the global optimum over all subsets and action proposals. Such a claim would require a separate optimization guarantee or exhaustive verification on a sufficiently small instance.

## Sources

[^1]: Michel Grabisch, Jean-Luc Marichal, and Marc Roubens. “Equivalent Representations of Set Functions.” *Mathematics of Operations Research* 25(2), 157–178, 2000. DOI: 10.1287/moor.25.2.157.12225. `https://pubsonline.informs.org/doi/10.1287/moor.25.2.157.12225`

[^2]: Frances Y. Kuo, Ian H. Sloan, Grzegorz W. Wasilkowski, and Henryk Woźniakowski. “On Decompositions of Multivariate Functions.” *Mathematics of Computation* 79, 953–966, 2010. DOI: 10.1090/S0025-5718-09-02319-9. Author-hosted preprint, especially Example 2.3: `https://web.maths.unsw.edu.au/~fkuo/pubs/preprint/ksww09-decomp.pdf`

[^3]: David Goldberg. “What Every Computer Scientist Should Know About Floating-Point Arithmetic.” *ACM Computing Surveys* 23(1), 5–48, 1991. Author article reproduced in Oracle documentation: `https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html`

[^4]: Paul Glasserman and David D. Yao. “Some Guidelines and Guarantees for Common Random Numbers.” *Management Science* 38(6), 884–908, 1992. DOI: 10.1287/mnsc.38.6.884. `https://pubsonline.informs.org/doi/10.1287/mnsc.38.6.884`

[^5]: Manzil Zaheer et al. “Deep Sets.” *Advances in Neural Information Processing Systems* 30, 2017. `https://papers.nips.cc/paper/6931-deep-sets`

[^6]: Edward Wagstaff et al. “Universal Approximation of Functions on Sets.” *Journal of Machine Learning Research* 23, 2022. `https://jmlr.org/papers/v23/21-0730.html`

[^7]: Adam Santoro et al. “A Simple Neural Network Module for Relational Reasoning.” *Advances in Neural Information Processing Systems* 30, 2017. `https://proceedings.neurips.cc/paper/2017/hash/e6acf4b0f69f6f6e60e9a815938aa1ff-Abstract.html`

[^8]: Wendelin Böhmer, Vitaly Kurin, and Shimon Whiteson. “Deep Coordination Graphs.” *Proceedings of ICML*, PMLR 119, 980–991, 2020. `https://proceedings.mlr.press/v119/boehmer20a.html`

[^9]: Juho Lee et al. “Set Transformer: A Framework for Attention-based Permutation-Invariant Neural Networks.” *Proceedings of ICML*, PMLR 97, 3744–3753, 2019. Tables 1 and 2 and architecture discussion. `https://proceedings.mlr.press/v97/lee19d.html`

[^10]: Keyulu Xu, Weihua Hu, Jure Leskovec, and Stefanie Jegelka. “How Powerful Are Graph Neural Networks?” *ICLR*, 2019. `https://openreview.net/forum?id=ryGs6iA5Km`

[^11]: Gilad Yehudai et al. “From Local Structures to Size Generalization in Graph Neural Networks.” *Proceedings of ICML*, PMLR 139, 11975–11986, 2021. `https://proceedings.mlr.press/v139/yehudai21a.html`

[^12]: Justin Singh Kang et al. “Learning to Understand: Identifying Interactions via the Möbius Transform.” *Advances in Neural Information Processing Systems* 37, 2024. Published version, Theorems 5.1–5.2 and Assumptions 2.1–2.2. `https://proceedings.neurips.cc/paper_files/paper/2024/file/520b379123d16e41f85472e766846486-Paper-Conference.pdf`

[^13]: Fabian Fumagalli et al. “SHAP-IQ: Unified Approximation of any-order Shapley Interactions.” *Advances in Neural Information Processing Systems*, 2023. `https://arxiv.org/abs/2303.01179`

[^14]: Patrick Kolpaczki, Maximilian Muschalik, Fabian Fumagalli, Barbara Hammer, and Eyke Hüllermeier. “SVARM-IQ: Efficient Approximation of Any-order Shapley Interactions through Stratification.” *Proceedings of AISTATS*, PMLR 238, 3520–3528, 2024. `https://proceedings.mlr.press/v238/kolpaczki24a.html`

[^15]: Darin Tsui et al. “SHAP zero Explains Biological Sequence Models with Near-zero Marginal Cost for Future Queries.” *Advances in Neural Information Processing Systems*, 2025. `https://proceedings.neurips.cc/paper_files/paper/2025/hash/78d002ebdbdfe4791c462d211fafdafd-Abstract-Conference.html`

[^16]: James E. Smith and Robert L. Winkler. “The Optimizer’s Curse: Skepticism and Postdecision Surprise in Decision Analysis.” *Management Science* 52(3), 311–322, 2006. DOI: 10.1287/mnsc.1050.0451. `https://pubsonline.informs.org/doi/10.1287/mnsc.1050.0451`

[^17]: Brandon Trabucco, Aviral Kumar, Xinyang Geng, and Sergey Levine. “Conservative Objective Models for Effective Offline Model-Based Optimization.” *Proceedings of ICML*, PMLR 139, 10358–10368, 2021. `https://proceedings.mlr.press/v139/trabucco21a.html`
