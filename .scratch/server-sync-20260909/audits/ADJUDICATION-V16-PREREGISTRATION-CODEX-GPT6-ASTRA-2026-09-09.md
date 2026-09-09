**v1.6 can remain preregistered for a fresh, independent confirmation, but it does not preserve the original intervention or admission gate unchanged.** The controller’s “uniformly stricter” argument is false, and the margin rule and trichotomy need revision.

I read the requested documents and verified v1.6’s companion checksum. This review does not certify actual panel separation or establish margin robustness.

**A. The changes are development-informed tuning; that does not automatically invalidate independent confirmation.**

The strongest example is **[v1.6 §2](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md:9)**. It replaces additive continuation scoring with lexicographic tie-breaking after the development slice showed FULL/DROP_C2 −9.28% and FULL/DROP_C3 −9.24%. Suppressing continuation’s ability to sacrifice immediate value can remove an observed FULL disadvantage and improve subsequent component contrasts. That is structural tuning even if nobody searched numerically over margins. The reports do not establish whether the sacrificed immediate value would have been repaid in closed-loop operation. [SMOKE evidence and limitations](/home/sat/mcrl-hub/.scratch/multi-catfish-v023-controller-handoff-20260907/VERTICAL-SLICE-SMOKE-2026-09-08.md:49)

**§1 also selects a remedy after observing nominal–realised disagreement.** The channel model determines the quantile *conditional on choosing 10%*; it does not determine that 10% should be chosen, or that quantile scoring should replace nominal scoring. Applying the same formula to every arm does not make its effect on arm contrasts neutral.

**§4’s ADMIT_C1C2 branch relaxes admission.** Previously, retained factors required positive oracle marginals beyond numerical error. Now C3 training and a positive learned C3 result remain possible without that certificate. Some previously rejected outcomes therefore become admissible. [Original gate](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md:18)

Conversely, demoting **J1 − U_all** is scientifically justified: multiple additive improvements can beat the best single improvement without demonstrating interaction value. It was also positive in the SMOKE report, so this particular change is not simply discarding an observed failed certificate.

These adaptations could produce a larger later effect because the **method being tested changed**. They do not necessarily bias estimation of that revised method on untouched data. The defensible description is “development-informed v1.6, frozen before independent confirmation.” Development/holdout separation is compatible with preregistration; disclosure alone cannot replace separation. [COS guidance](https://www.cos.io/initiatives/prereg)

**B. Approximate selection plus exact evaluation is legitimate, but §1 leaves a substantive policy mismatch.**

Exact 48-boundary evaluation measures what the selected policy actually achieves. It does not validate the selection surrogate or remove asymmetries introduced by that surrogate.

- **Re-solving power can cancel the intended fading protection.** Consider one uncapped, interference-free link with target SINR Γ. Nominal execution uses \(p_N=\Gamma N/h_N\). Recomputing required power under \(h_m=qh_N\) gives \(p_m=p_N/q\), so the margin-scored link still achieves Γ. But unchanged execution at that same hypothetical fading level achieves only \(q\Gamma\). Thus §1 can predict bits using increased power that execution never supplies. This follows from the declared rate-target policy, and the archived implementation solves power from nominal gains. [Rate-target declaration](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:6), [implementation](/home/sat/mcrl-v025-stage4d-snapshot-20260909/src/mcrl/physics_v025/architectures.py:668)

  **Fix:** distinguish the nominal gains used to determine executed power from the attenuated gains used to predict reception. Alternatively, explicitly describe the current construction as a surrogate involving hypothetical power adaptation; it is not a prediction of the unchanged executed policy.

- **“Every link” includes interfering links.** Lowering unwanted cross gains can improve predicted reception. With identical attenuation \(q\) and fixed powers, SINR becomes \(S/(N/q+I)\): interference-limited signal-to-interference ratios barely change. With unequal link quantiles, the distortion can differ by configuration. Componentwise lower gain quantiles are not automatically lower SINR quantiles or a 90% service guarantee.

- **The immediate-ranking key must respect each oracle ablation.** The intended lexicographic keys should be explicit:

  | Oracle arm | Primary ranking key | Secondary key |
  |---|---|---|
  | FULL | \(C1_m+C3_m\) | C2 |
  | DROP_C1 | \(C3_m\) | C2 |
  | DROP_C2 | \(C1_m+C3_m\) | Fixed deterministic rule |
  | DROP_C3 | \(C1_m\) | C2 |

  Using the full \(F_m\) for every arm’s immediate maximisation would restore removed C1/C3 contributions. The same problem can occur through top-M pruning or an objective-improvement guard. Exact evaluation may measure outcomes; it must not silently reject or rerank DROP decisions using the removed score. This is already prohibited by [contract A4](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:9).

- **Tie-only C2 can legitimately have zero oracle effect.** At matched anchors with a unique immediate maximiser, FULL and DROP_C2 should select identically. Q2’s separate effect on proposal construction does not demonstrate a positive set-level continuation marginal. Report tie frequency and accept zero; do not subsequently widen the tolerance to obtain C2 positivity.

**C. q₁₀ is defensible as a declared engineering choice, not as a uniquely model-determined or universally standard choice.**

The assertion “standard 90%-availability link-budget convention” needs qualification. For example, ETSI’s satellite implementation guidance uses different availability objectives, including 99.0% and 99.9%, with corresponding margins. That does not prohibit 90%; it establishes that the availability target needs its own rationale. [ETSI TR 102 376-2, Table 27](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237602/01.01.01_60/tr_10237602v010101p.pdf)

There is also a **distribution-definition problem**. The archived successor channel generates

\[
G=R\,10^{-(X+L_c(e))/10},
\]

where \(R\) is Rician power fading, \(X\) is Gaussian shadow loss, and \(L_c(e)\) is deterministic scintillation loss. v1.6’s “shadow + scintillation” wording omits Rician fading. A shadow-only closed-form quantile does not specify the quantile of this full product. Seal the complete CDF/quantile procedure, its numerical tolerance, and which losses are already inside nominal gain. [Successor channel](/home/sat/mcrl-v025-stage4d-snapshot-20260909/src/mcrl/physics_v025/channel.py:221)

**Different quantiles can change arm rankings materially.** Elevation-dependent attenuation, discrete ACM transitions, power saturation, and coupled interference prevent any rank-invariance argument. The supplied reports contain no experiment establishing whether those reversals actually occur.

**The single decisive test:** a prospectively frozen, paired **quantile-by-arm closed-loop sweep** at α ∈ {0.05, 0.10, 0.25}, plus the unchanged nominal selector. Re-select actions under each rule, use common exogenous worlds, retain each arm’s own trajectory and deadline/fallback accounting, and evaluate every outcome at 48 boundaries. Report whether the load-bearing contrast signs, arm ordering, and admission/claim threshold decisions remain stable; predefine acceptable effect variation.

The existing top-1 agreement diagnostic is insufficient: a few consequential disagreements can dominate pooled EE, and fixed-anchor agreement misses trajectory divergence. A sweep establishes robustness over its declared grid, not every possible quantile. Its results must not select a replacement primary margin.

**D. The learned-test rationale is sound; the trichotomy’s executable logic is not.**

Oracle removal and retrained neutral-source substitution were already declared as different experiments. An exact nominal residual can hurt realised performance while a learned approximation regularizes that error; a neutral-trained head also need not behave like zero. Consequently, one frozen learned-source test on untouched dates can legitimately succeed after a negative oracle signal. [Contract C3](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:21)

However, **[§4’s current branch condition](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md:18) is non-monotone**. Hold BASE gain, C1/C2 positivity, QoS, validity and deadlines passing; let C3’s oracle marginal fail:

| Certified S0 superiority over S_UNI | Current outcome |
|---|---|
| Not established | ADMIT_C1C2 |
| Established | NOT_ADMITTED |

Improving one certificate makes admission worse: FULL still fails C3 positivity, while C1C2 becomes unavailable.

After mandatory execution-validity checks, define:

- \(G\): BASE gain ≥1%, C1/C2 marginals **beyond certified numerical error**, and QoS/validity/deadline requirements pass.
- \(O\): C3 oracle marginal passes.
- \(H\): superiority over certified S_UNI passes.
- `ADMIT_FULL = G ∧ O ∧ H`.
- `ADMIT_C1C2 = G ∧ ¬(O ∧ H)`.
- `NOT_ADMITTED = ¬G`.

Preserve separate reason codes for evaluated non-superiority, statistical uncertainty, and budget-limited/uncertified S_UNI. Missing mandatory receipts are an incomplete experiment, not a negative scientific finding.

The partial branch must explicitly authorize a **learned-source test**, without overturning the oracle result. A learned Level-B positive cannot establish Level-A coordination without its additional S_UNI evidence. Nor can a failed C3 contrast be removed from the three-component primary conjunction to manufacture a reduced confirmatory success. [Claim ladder](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-CONTINGENCY-LADDER-PREOUTCOME-2026-09-08.md:5), [primary conjunction](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:31)

**E. A referee can correctly identify changed estimands and claim conditions.**

The observable endpoint, realised pooled ΣB/ΣE, remains unchanged. Nevertheless, §1 changes the policy whose performance is estimated; §2 changes the C2 intervention from temporal trade-off scoring to tie-breaking; §4 changes which evidence permits further testing. These are substantive prospective amendments.

There is an additional unresolved mapping between **margin-based selection residuals and unchanged training labels**. Specify whether S3 estimates \(\Psi_m\) or the original 48-boundary residual. Otherwise S0 versus S3 changes both approximation and target, despite being described as replacing an exact residual with its learned estimate.

The collision-avoidance decomposition and §5’s ratio clarification are reasonable. Re-anchoring only implies \(d_i^u\le0\) for individually feasible moves, under the same objective used to certify \(u\), and allowing numerical tolerance; it does not imply non-positive realised increments.

Finally, an inherited issue independently threatens positive inference: contract v1.1 reports roughly 89–92% coverage for nominal 95% intervals. Disclosure preserves transparency, not nominal error control. Calibrate the actual conjunction and QoS decision procedure under relevant nulls before treating its positives as adequately controlled. [Contract v1.1](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md:16)

Here, **PREREGISTRATION=INTACT means prospective confirmation of the disclosed amended protocol on genuinely untouched data**. It does not mean v1.0–v1.5’s intervention or gate survived unchanged.

VERDICT: PREREGISTRATION=INTACT | MARGIN_RULE=REVISE:execution-consistent scoring, complete fading quantile, explicit ablation keys | TRICHOTOMY=REVISE:monotone partial-admission branch and separate oracle/source claim boundaries | REQUIRED_TESTS=seal-and-panel-separation audit; paired closed-loop quantile sweep; power/interference/48-boundary invariance KATs; ablation-and-label conformance including unique-max C2; admission truth table with certificate states; conjunction-and-QoS null calibration