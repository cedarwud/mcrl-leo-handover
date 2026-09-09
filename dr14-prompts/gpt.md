## Recommendation

**Change the design before launching the confirmatory experiment.** My judgment is that your current evidence does not justify spending the compute on an unchanged run—or simply increasing from sixteen to twenty-four seeds.

The leading candidate is **the same ablation structure, with more independent evaluation-date blocks, validated confidence bounds, and an explicit distinction between deadline-constrained performance and performance without fallback**. That preserves your scientific question. Your numbers do not yet identify how many additional dates are needed.

Two qualifications matter immediately. First, **0.86–0.92 coverage is not necessarily undercoverage**: that depends on whether you measured coverage separately for each contrast or simultaneously across contrasts. Second, **0.68 power is conditional on the particular effect sizes and data-generating assumptions used in your simulation**. It is not the probability of detecting any “real effect.”

Below, I distinguish statistical results, calculations under stated assumptions, and my design recommendations.

## 1. The conjunction is demanding, but it is not an avoidable multiplicity mistake

Let \(R_a\) denote the population pooled energy efficiency for arm \(a\), and define

$$
r_k=\frac{R_{\mathrm{FULL}}}{R_{\mathrm{DROP}_k}}-1,
\qquad m=0.005.
$$

Your energy-efficiency claim is

$$
H_1:\quad r_1>m,\quad r_2>m,\quad r_3>m.
$$

Its null is that **at least one** component fails to exceed the margin.

### Established result: no Bonferroni penalty is required for this single all-pass claim

An intersection–union test rejects only when every constituent null is rejected at level \(\alpha\). If constituent null \(j\) is true,

$$
P(\text{all tests reject})
\leq P(\text{test }j\text{ rejects})
\leq \alpha.
$$

This does not require independence. Equivalently, valid constituent p-values give a valid global p-value \(p_{\mathrm{IUT}}=\max_j p_j\). The same logic extends to your QoS requirements when they are additional necessary conditions for the single success claim. This is the established co-primary-endpoint structure. ([Project Euclid][1])

Therefore, **do not additionally Bonferroni-adjust the three energy-efficiency tests just because there are three of them**. Separate confirmatory claims about whichever components happen to pass would be a different multiple-testing problem.

But removing an unnecessary adjustment does not eliminate the genuine requirement to establish every contribution.

### The failure probabilities do not generally multiply

They multiply under independence. Your contrasts share FULL, so their dependence must be measured rather than assumed.

For constituent powers \(p_1,p_2,p_3\),

$$
P(\text{all pass})\leq \min(p_1,p_2,p_3).
$$

Under independence, three tests with 90% power each have only \(0.9^3=72.9\%\) conjunction power. Achieving 90% conjunction power with equal, independent tests requires approximately \(0.9^{1/3}=96.55\%\) power per test. Correlated co-primary-endpoint sample-size methods explicitly account for this dependence. ([PubMed][2])

**Your complete success event has at least six conditions:** three EE superiority conditions and three QoS non-inferiority conditions, assuming one QoS criterion per DROP comparison. If the reported 0.68 includes only the EE tests, then 0.68 is an upper bound on power for the complete claim.

### There is no general statistical shortcut that preserves the unrestricted meaning

An average component effect, an omnibus test, or a FULL-versus-neutral comparison can succeed while one component contributes nothing. They do not establish your conjunction.

You could express the EE question as

$$
\min_k r_k>0.005,
$$

but merely renaming it a “minimum contribution” endpoint does not create information. Using the minimum of the constituent lower bounds reproduces the existing all-pass decision.

Joint modelling, better pairing, or justified covariate adjustment can improve precision. Stronger structural assumptions can sometimes improve testing efficiency. But there is no general-purpose replacement that lets strong components compensate for an unestablished weak component while retaining the same unrestricted claim and error control.

One further distinction follows directly from your arm definitions: your ablations establish **the contribution of each component when the other two are present**. They do not establish that each works alone, that the contributions are additive, or that FULL beats the all-neutral control. Those are different claims.

**My recommendation:** retain the conjunction if “each component contributes more than 0.5% in the complete system” is essential. Change the claim only if that is not actually the scientific conclusion you need.

## 2. The power plateau is consistent with a date bottleneck—but does not prove one

A useful analysis scale is

$$
\theta_k=\log R_{\mathrm{FULL}}-\log R_{\mathrm{DROP}_k},
$$

with threshold \(\log(1.005)\). This is an exact reformulation of your relative-margin test, not a new estimand.

For a balanced crossed design, a first-order random-effects approximation to the covariance of the estimated contrast vector has the form

$$
\operatorname{Var}(\widehat{\boldsymbol\theta})
\approx
\frac{\Sigma_{\mathrm{date}}}{D}
+
\frac{\Sigma_{\mathrm{seed}}}{S}
+
\frac{\Sigma_{\mathrm{date}\times\mathrm{seed}}}{DS}.
$$

Here \(D\) is the number of independent date blocks, \(S\) is the number of independent training-seed blocks, and within-cell evaluation variation can be incorporated into the final term. This is a diagnostic approximation, not an assertion that your data obey a homoscedastic random-effects model. Crossed dependence is precisely the setting motivating multiway inference. 

Under this approximation, at fixed \(D\),

$$
S\rightarrow\infty
\quad\Longrightarrow\quad
\operatorname{Var}(\widehat{\boldsymbol\theta})
\rightarrow
\frac{\Sigma_{\mathrm{date}}}{D}.
$$

Thus, additional seeds cannot remove a genuine date-level variance floor. More anchors within existing dates cannot remove it either.

### The important variance is date variation in the paired treatment contrast

Your “5% standard deviation across dates” needs a precise definition.

A 5% date-to-date fluctuation in **raw EE** might largely cancel when FULL and DROP encounter the same difficult dates. Conversely, the component’s benefit might itself vary substantially across dates.

The relevant quantity is therefore not merely

> How much does EE vary between dates?

It is

> How much does the FULL-versus-DROP contrast vary between dates, after preserving the intended pairing and accounting for seed variation?

A model containing only a common date intercept can miss this distinction. You need date-specific treatment effects, or the equivalent decomposition of the paired contrast’s influence scores.

### What to extract from the data you already have

I would construct one analysis table containing arm, date, world, training seed, bits, joules, QoS sufficient statistics, and fallback information. Then perform three diagnostic comparisons:

| Diagnostic                                                                         | What it would tell you                                                                                                     |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Crossed variance decomposition of the **paired pooled-contrast influence scores**  | Whether date, seed, or interaction variation dominates each contrast and their joint covariance                            |
| Leave-one-date-out versus leave-one-seed-out recomputation of the pooled contrasts | Whether a few dates or seeds determine the effect or the success decision                                                  |
| Date-only, seed-only, and full two-way resampling                                  | Which resampled dimension changes uncertainty most; these are diagnostic comparisons, not interchangeable primary analyses |

Because the target is pooled EE, do not silently replace it with a mean of cell-level ratios while doing this decomposition. Ratio-metric linearization provides a way to diagnose variation while retaining the original target. ([arXiv][3])

Also distinguish “more worlds” from “more dates.” Additional worlds sharing the same ephemeris-date effect mainly supply within-date information. They need not substitute for genuinely new date blocks. Conversely, genuinely random world-level variation may require another level of dependence to be represented.

### Check whether the plateau exceeds simulation noise

For \(N_{\mathrm{sim}}\) independent outer simulation repetitions,

$$
\operatorname{MCSE}(\widehat p)
\approx
\sqrt{\frac{\widehat p(1-\widehat p)}{N_{\mathrm{sim}}}}.
$$

At \(\widehat p=0.68\) and \(N_{\mathrm{sim}}=1{,}000\), this is about **1.48 percentage points**. Two estimates rounded to 0.68 do not establish an exact ceiling. Use paired simulation repetitions when comparing designs and report uncertainty for their difference. Monte Carlo uncertainty is a central part of evaluating simulated coverage and power. ([Wiley Online Library][4])

**My diagnosis:** a date bottleneck is plausible and should be investigated first. But rounding, simulation error, a single weak contrast, or an effect attenuated below the margin by fallback could also produce the apparent plateau.

## 3. The coverage result needs an audit before choosing a remedy

### First: marginal coverage and simultaneous coverage are different

Suppose each of three intervals has correct 95% coverage. Under independence, the probability that **all three** cover is

$$
0.95^3=0.857375.
$$

Consequently, **simultaneous coverage of 0.86–0.92 can be compatible with correctly calibrated marginal intervals**. Your IUT does not require an ordinary collection of marginal intervals to have 95% simultaneous coverage.

If 0.86–0.92 is instead the coverage of **each individual nominal-95% interval**, then it is a genuine calibration problem, assuming the simulation uncertainty is sufficiently small.

Also establish what “95% lower confidence bound” means in the implementation. A one-sided 95% bound uses a 5% lower-bound error allowance. The lower endpoint of an equal-tailed two-sided 95% interval corresponds to a 2.5% allowance. Confusing these changes both calibration and power.

### Second: undercoverage does not uniquely imply intervals are too narrow

Coverage can fail because of estimator bias, incorrect width, inappropriate distributional approximation, or combinations of these. For your superiority decision, the particularly relevant error is

$$
P(L_k>\theta_k),
$$

where \(L_k\) is the lower bound. Two-sided coverage alone does not identify which tail is failing. Simulation-methodology work explicitly recommends separating miscentring from incorrect interval width. ([Oxford Academic][5])

### Audit the bootstrap’s dependence structure

For date–seed totals, a pigeonhole resample should have the structure

$$
R_a^*=
\frac{\sum_{d,s}W_dV_s B_{a,ds}}
     {\sum_{d,s}W_dV_s E_{a,ds}},
$$

where date multiplicities \(W_d\) and seed multiplicities \(V_s\) are sampled independently, and the **same joint resampling weights** are applied to all paired arms, their bits and joules, and their QoS data. This implements the row-and-column resampling idea. 

Potential mistakes include treating each combined `date_seed` identifier as an independent cluster, resampling anchors independently, or failing to preserve cross-arm pairing. A combined identifier alone does not capture dependence between different seeds sharing a date or different dates sharing a trained policy.

Then audit the assumptions beyond the code: overlapping evaluation trajectories, omitted world-level dependence, highly unequal cluster contributions, and too few independent clusters.

### Neither “ratio” nor “pigeonhole bootstrap” is automatically the culprit

With positive, sufficiently stable denominators, a ratio of sums is a smooth function of means. Delta-method and suitable bootstrap inference are standard options. A random denominator must be accounted for, but its existence does not make the estimator intrinsically unsuitable. ([arXiv][3])

Nor is the pigeonhole bootstrap inherently anti-conservative. Owen’s analysis finds mildly conservative variance estimates in important crossed-random-effects settings. Later work establishes validity for nonlinear estimators under multiway asymptotics. Those results are not a guarantee for an arbitrary handful of dates; the asymptotic framework requires the relevant cluster counts to grow. 

My leading concerns would be **few effective date clusters, incorrect dependence representation, influential clusters, and mismatch between the simulated truth and the estimator’s target**, before blaming the pooled ratio itself.

### What remedy I would evaluate

After correcting any implementation or target mismatch, compare the current method with a **studentized, genuinely multiway procedure**, such as an appropriately constructed wild-bootstrap test based on linearized estimating equations. Multiway wild-bootstrap methods have supporting theory and simulation evidence, but their validity depends on the specific construction and assumptions; “use a wild bootstrap” is not a sufficient implementation specification. ([Pure][6])

A model-based crossed-effects analysis is another candidate, but it trades robustness for modelling assumptions. A handful of dates makes those assumptions consequential. No off-the-shelf interval modification manufactures the missing independent dates.

Two non-remedies deserve explicit mention:

**Increasing bootstrap repetitions** reduces numerical error in bootstrap quantiles, not the finite-cluster problem.

**Taking logs alone** does not repair a percentile bootstrap. Quantiles transform monotonically, so logging the pooled ratio and transforming the percentile endpoints back essentially reproduces the same interval.

### Validate the decision at the right null configurations

The most informative false-positive checks are not just “all components have zero effect.”

For the EE conjunction, simulate one component **at the +0.5% boundary**, with the other two effects clearly above their boundaries and QoS safely non-inferior. Repeat with each component as the boundary case. Similarly, place each QoS condition at its non-inferiority boundary while the remaining conditions are easy to pass.

Otherwise, an insensitive second gate can hide a liberal first gate. Testing only zero EE effects is also easier than testing the +0.5% boundary relevant to your claim.

Finally, make sure the simulation’s “truth” is the population pooled-ratio contrast—not a mean of episode ratios or a conditional parameter from the generator. Assessing the wrong target can create apparent bias or coverage failure. ([Wiley Online Library][4])

**Re-estimate power only after this calibration audit.** Power from a test with inflated false-positive rates is not an acceptable basis for selecting the confirmatory sample size.

## 4. Pooled EE is defensible; denominator concentration is a diagnostic, not an automatic indictment

For blocks \(i\), write \(R_i=B_i/E_i\). Then

$$
R_{\mathrm{pool}}
=\frac{\sum_i B_i}{\sum_i E_i}
=\sum_i w_iR_i,
\qquad
w_i=\frac{E_i}{\sum_jE_j}.
$$

Thus pooled EE is indeed energy-weighted. But that follows from the operational question:

> How many total bits are delivered per total joule consumed over the target workload?

For that question, giving a tiny-energy block the same weight as a large-energy block would answer something else.

### A paired mean-log contrast targets something different

The block-average quantity

$$
\frac1n\sum_i
\log\!\left(\frac{B_{\mathrm{FULL},i}/E_{\mathrm{FULL},i}}
{B_{\mathrm{DROP},i}/E_{\mathrm{DROP},i}}\right)
$$

describes a geometric-average relative effect over the chosen blocks. In general, it is not

$$
\log\!\left(
\frac{R_{\mathrm{FULL,pool}}}
{R_{\mathrm{DROP,pool}}}
\right).
$$

Neither is universally correct. The choice is between a system-total efficiency target and a block-average proportional-improvement target—not merely between two estimators with different power.

There is also a distinction between pooling across training seeds and averaging each trained policy’s EE: pooling can energy-weight the seed-specific policies. Specify which deployment interpretation you intend.

### Diagnostics I would require

**Energy concentration.** Report each date’s and seed’s share of total joules, separately by arm, including the largest shares. A useful descriptive concentration measure is

$$
D_{\mathrm{eff},E}=\frac{1}{\sum_d w_d^2}.
$$

This is an energy-weight concentration index, **not** a complete statistical effective sample size.

**Contrast influence.** Large energy share does not necessarily mean large influence on the treatment contrast. A first-order date contribution to the pooled log contrast is proportional to

$$
u_{d,k}=
\frac{B_{\mathrm{FULL},d}}{B_{\mathrm{FULL}}}
-\frac{E_{\mathrm{FULL},d}}{E_{\mathrm{FULL}}}
-\frac{B_{\mathrm{DROP}_k,d}}{B_{\mathrm{DROP}_k}}
+\frac{E_{\mathrm{DROP}_k,d}}{E_{\mathrm{DROP}_k}}.
$$

The terms can cancel. This follows by differentiating the four log totals and is the ratio-metric analogue of an influence diagnostic. ([Alex Deng][7])

**Deletion sensitivity.** Recompute the actual pooled contrasts after deleting each date and each seed. Report changes in estimates and uncertainty, rather than just whether significance changes. Cluster leverage and influence can compromise inference even when the nominal cluster count is not especially small. ([arXiv][8])

**My recommendation:** keep pooled EE primary if network-total bits per joule is the intended scientific target. Report a prespecified date-balanced contrast as a secondary heterogeneity analysis. Do not choose between them after seeing which passes, and do not silently discard zero-bit blocks to make block-level logs computable.

If a few high-energy dates genuinely represent most deployed energy consumption, their weight is meaningful. If they dominate only because the evaluation oversampled unusual workloads or used unequal exposure lengths, repair the sampling design or prespecify appropriate population weights.

## 5. Fallback can destroy detectability—but its interpretation depends on the target

Your concern is substantively important. Under your simplified additive model,

$$
G=(1-M)\Delta,
$$

so

$$
\mathbb E[G]
=
(1-p_M)\mathbb E[\Delta]
-
\operatorname{Cov}(M,\Delta).
$$

This is an exact identity. Positive covariance between fallback and potential gain causes additional attenuation beyond multiplying by the completion rate.

But it does **not** follow that the primary observed comparison is statistically biased.

### Deployment performance: fallback is part of the outcome

For the question

> Does the implemented system improve EE under its real-time operating constraint?

fallback is part of the policy being evaluated. Its bits, joules, and QoS outcomes belong in the primary analysis.

This corresponds conceptually to a **treatment-policy estimand**: evaluate the assigned system including what happens when the intended intervention is not delivered. The estimands literature distinguishes this from hypothetical performance without such events. The analogy is useful here, although the cited framework was developed for clinical trials. ([European Medicines Agency (EMA)][9])

If the mechanism is excellent but routinely cannot execute when useful, then low deployment benefit is not something an estimator should “correct away.”

### Mechanism performance: the no-fallback outcome is counterfactual

For the different question

> What would the same decision procedure achieve if it completed and its decision were exercised?

you need a precisely defined hypothetical estimand.

Dropping fallback cases estimates performance among completed cases, not generally the hypothetical full-population performance. Inverse-probability weighting requires appropriate measured predictors of completion and outcome, plus positivity: relevant cases must have some chance of completing. If the hard instances deterministically time out, weighting cannot recover their unobserved gains. Research on non-adherence and censoring corrections makes these assumptions explicit. ([Sage Journals][10])

### Three complications are particularly relevant here

First, FULL and DROP can have different fallback probabilities. Even under a common additive baseline,

$$
Y_{\mathrm{FULL}}-Y_{\mathrm{DROP}}
=
(1-M_F)\Delta_F-(1-M_D)\Delta_D.
$$

The net distortion need not always be toward zero.

Second, your primary outcome is a **ratio of aggregate bits and joules**, not an additive average of gains. The identity for \(G\) diagnoses a mechanism, but it is not a valid shortcut for correcting pooled EE. Recompute the numerator and denominator under the relevant policies.

Third, common fallback can make QoS look similar. That can make non-inferiority easier while making EE superiority harder. Non-adherence-induced similarity is a recognized concern for non-inferiority analyses. ([European Medicines Agency (EMA)][9])

### My proposed design

Keep **deadline-constrained, all-anchor performance** as the deployment primary. In a small repaired pilot, log the intended arm, invocation status, actual executed action, deadline miss, fallback reason, end-to-end runtime, and outcome totals. Also measure how often FULL actually executes a different decision from its DROP comparisons. An enabled component is not necessarily an exercised treatment.

Add a separate **shadow/offline mechanism evaluation** on saved states and controlled exogenous inputs, including fallback cases—not just easy completed cases. Define what completion means: the original stopping rule without the deadline is different from granting unlimited additional optimization or future information.

For cumulative EE, replaying isolated decisions at states visited by the fallback policy is insufficient to establish the full no-fallback trajectory effect. That requires corresponding counterfactual rollouts, because earlier actions can change later states.

Finally, control the timing environment: comparable hardware allocation, no uncontrolled competition between arms, and a frozen deadline/fallback implementation. This is my engineering recommendation for ensuring that the evaluated treatment is well defined.

**The key diagnostic outcome is the separation between “the mechanism has value” and “the deadline-constrained implementation delivers that value.”** More dates help estimate either quantity; they do not turn a below-margin deployed effect into an above-margin effect.

## 6. The smallest defensible change—and what “adequate” should mean

### My power target

For this expensive, all-or-nothing claim, I would target **90% power for the complete success event**, including QoS, at prespecified scientifically worthwhile alternatives.

That is a judgment about the cost of another inconclusive experiment, not a statistical law. An 80% target could be a defensible resource compromise if its implications are accepted explicitly. I would not call 68% adequate for the confirmatory objective you describe.

Crucially, “all effects are real” is insufficient to define the alternatives. A true +0.3% contribution is real but fails your +0.5% requirement. At the boundary itself, a correctly calibrated test rejects only at its allowed error rate. For planning, the important gap is

$$
\delta_k=
\log(1+r_k^{\mathrm{alternative}})
-\log(1.005).
$$

The weakest gap relative to its uncertainty matters most.

### Why I cannot responsibly give you a date count

You have not supplied the exact number of independent dates, the three assumed effect sizes, the QoS margins and alternative values, the joint covariance, or the precise meaning of the 5% date SD.

Those quantities can change the answer dramatically.

For illustration only, suppose date SD is **0.05 on the paired log-contrast scale**, seed variance is negligible, all three tests have equal independent normal errors, each uses a one-sided 5% test, and QoS adds no power loss. Then approximately

$$
D\approx
\left[
\frac{0.05\{z_{0.95}+z_{0.90^{1/3}}\}}
{\log(1+r)-\log(1.005)}
\right]^2.
$$

Under those assumptions, a true 2% contribution requires about **137 independent dates** for 90% EE conjunction power; a true 3% contribution requires about **50**. These are illustrative normal-approximation calculations, not proposed sample sizes.

They show why it is essential to learn whether “5%” describes the paired contrast or merely raw EE. They also show why a handful of dates and a small superiority margin cannot be declared adequate without knowing the alternative effects.

### The minimal redesign I would pursue first

**Preserve the five arms and the pooled-EE target.** There is no need to expand to a full factorial experiment just to answer the current leave-one-component-out question.

**Treat the repaired-system pilot and existing debugged data as development evidence.** Use them to establish treatment exercise, estimate the contrast covariance, inspect concentration, and audit the simulation. Historical nuisance estimates from defective code may not transfer unchanged to the repaired system.

**Compare date expansion against seed expansion before buying either.** Simulate a grid of candidate \(D,S\) designs using the same complete success rule, with calibrated inference and plausible effect/fallback scenarios. If date variance dominates, the first candidate should be sixteen seeds evaluated on more independent date blocks—not twenty-four seeds on the same dates.

A useful design approximation is

$$
V_k(D,S)\approx \frac{a_k}{D}+\frac{b_k}{S}+\frac{c_k}{DS}.
$$

For a target variance \(v_k^*\), fixed \(S\) would require approximately

$$
D\geq
\frac{a_k+c_k/S}{v_k^*-b_k/S},
$$

provided the denominator is positive. If it is not positive, the seed floor is itself too high. This algebra explains why neither “always add dates” nor “always add seeds” is a universal rule.

Choose the least-cost design that meets the joint-power target and acceptable calibration across the prespecified planning scenarios. Include uncertainty in nuisance estimates; a single optimistic pilot fit is not enough.

### When to change the claim instead

If the available budget cannot support the conjunction, a legitimate alternative is to make **FULL versus all-neutral** the primary system-level claim and treat the component ablations as secondary evidence, with an appropriate prespecified testing strategy where formal secondary claims are intended. Hierarchical endpoint strategies are established, but they must match the claims being made. ([U.S. Food and Drug Administration][11])

That is a different scientific claim—not a statistical trick that proves every component contributes.

Likewise, restricting inference to the observed benchmark dates could reduce the target uncertainty, but it changes the conclusion from generalization across dates to performance on a fixed benchmark.

## Bottom line

**Your design is not demonstrably incapable of detecting an effect, but it is not ready for an unchanged confirmatory run.**

The smallest promising change is to retain the ablation question, verify that coverage is genuinely deficient rather than merely non-simultaneous, separate deployed and no-fallback performance, and allocate additional evaluation to independent dates **if the paired-contrast variance decomposition confirms the suspected bottleneck**.

Do not automatically buy eight more seeds. Do not switch estimands merely to obtain significance. And predefine a failed conjunction as **“the complete claim was not established,”** not “the components have no effect.” Valid intervals can distinguish an excluded worthwhile gain from unresolved uncertainty; a binary all-pass flag alone cannot.

[1]: https://projecteuclid.org/journals/statistical-science/volume-11/issue-4/Bioequivalence-trials-intersection-union-tests-and-equivalence-confidence-sets/10.1214/ss/1032280304.full?utm_source=chatgpt.com "Bioequivalence trials, intersection-union tests and ..."
[2]: https://pubmed.ncbi.nlm.nih.gov/21516562/?utm_source=chatgpt.com "Sample size determination in superiority clinical trials with ..."
[3]: https://arxiv.org/html/1803.06336 "Applying the Delta Method in Metric Analytics: A Practical Guide with Novel Ideas"
[4]: https://onlinelibrary.wiley.com/doi/10.1002/sim.8086 "Using simulation studies to evaluate statistical methods - Morris - 2019 - Statistics in Medicine - Wiley Online Library"
[5]: https://academic.oup.com/ije/article/53/1/dyad134/7313663 "oup.silverchair-cdn.com"
[6]: https://pure.au.dk/portal/en/publications/wild-bootstrap-and-asymptotic-inference-with-multiway-clustering-2/ "Wild Bootstrap and Asymptotic Inference With Multiway Clustering - Aarhus University"
[7]: https://alexdeng.github.io/public/files/kdd2018-dm.pdf?utm_source=chatgpt.com "Applying the Delta Method in Metric Analytics: A Practical ..."
[8]: https://arxiv.org/html/2205.03288v3?utm_source=chatgpt.com "Reliable Inference Using summclust"
[9]: https://www.ema.europa.eu/en/documents/scientific-guideline/ich-e9-r1-addendum-estimands-and-sensitivity-analysis-clinical-trials-guideline-statistical-principles-clinical-trials-step-5_en.pdf "E9 (R1) Step 5 addendum on estimands and Sensitivity Analysis in Clinical Trials to the guideline on statistical principles for clinical trials"
[10]: https://journals.sagepub.com/doi/10.1177/09622802241289559?utm_source=chatgpt.com "Is inverse probability of censoring weighting a safer choice ..."
[11]: https://www.fda.gov/media/162416/download "Multiple Endpoints in Clinical Trials - Guidance for Industry"
