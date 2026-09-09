I recommend **(a), with an explicit provenance disclosure and a fully specified, standards-informed model**. Frame C3 as an evaluated joint re-evaluation layer whose added value is tested, rather than promised.

I read all six files. They support a design review, not an empirical verdict: the smoke report explicitly lacks trained heads, arm-specific closed-loop trajectories and formal QoS inference; its `S_UNI` column is a catalogue-based proxy, not a certified unilateral local optimum. The ≈0.89 interval coverage appears only in the question, without a calibration receipt. These limits materially constrain the wording below. ([SMOKE, “Shortcuts and unimplemented decision items”](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/VERTICAL-SLICE-SMOKE-2026-09-08.md); [QA prompt, question 3](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/01-QA-PROMPT.md).)

**For question 1, option (a) is honest if the old model was an internal development implementation.** A paper need not narrate every discarded simulator design. It must make the current assumptions and the provenance of its evidence auditable.

Option **(b)** becomes appropriate if the old model underpins published claims, a public predecessor or the manuscript being revised. Then identify the affected conclusions and correct them explicitly. A before/after comparison should isolate the modelling difference; changing physics, training and selection together cannot establish which change caused a performance difference. TWC explicitly requires disclosure of related prior publications and submissions. ([TWC policies](https://www.comsoc.org/publications/journals/ieee-twc/policies-guidelines).)

Option **(c)** is weakest here. A two-model study needs two defensible operating models. Presenting a diagnosed association-reset artefact as an equally legitimate alternative risks looking like an attempt to retain favourable legacy evidence.

For acceptable **(a)**, the system-model section needs:

* **The load-to-energy mechanism:** how equal-airtime allocation changes the required instantaneous rate, MODCOD feasibility and required RF power as beam occupancy changes. State whether the rate target is averaged over the decision interval or applies during transmission.
* **Complete physical accounting:** interference coupling, power limits, infeasibility/outage behaviour, PA efficiency and airtime integration, active-chain consumption, switching energy and shared overhead. Distinguish continuing circuit power in watts from transition energy in joules.
* **Information and time conventions:** what selection knows, what realised evaluation uses, the 48-boundary integration, forecasting assumptions and the non-causal TLE convention.
* **The optimisation–evaluation distinction:** the frozen-multiplier surplus is a selection surrogate; success is measured using realised pooled \(\sum B/\sum E\). A positive surplus alone does not establish superiority to an arbitrary comparator. ([v1.5, item 5](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md); [v1.6, §§1, 5](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md).)
* **Assumption-specific sources:** identify standardized elements, conventional abstractions and author-selected design choices.

In particular, DVB-S2X supports discrete MODCODs and ACM procedures; it does not standardize this entire scheduler/controller/energy model. Likewise, the sources checked do not establish v1.6’s asserted universal “90%-availability link-budget convention.” Call it a **pre-specified tenth-percentile channel-gain scoring rule**. Per-link quantiles do not establish 90% network availability. ([ETSI EN 302 307-2, §§5–6 and Annex D.5](https://www.etsi.org/deliver/etsi_en/302300_302399/30230702/01.04.01_60/en_30230702v010401p.pdf); [ITU-R P.618-14, Annex 1 §§2.5, 8](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.618-14-202308-I!!PDF-E.pdf).)

A suitable main-text provenance sentence is:

During simulator development, an association-history-dependent power rule was replaced by the present memoryless rate-target model. The deviation register documents the replacement, the development evidence available when subsequent amendments were made, and the exclusion of legacy-model numerical evidence from the present performance claims.

The disclosure must acknowledge that v1.6 followed inspection of development smoke, as its opening paragraph already does.

**For question 2, organise the paper around an engineering question: when does joint re-evaluation add value to learned association decisions?** The scientific contribution can include establishing where a component is unnecessary, provided that conclusion is precise, well controlled and useful beyond this implementation.

A compact structure would be:

| Section                                            | Responsibility                                                                                                                    |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| I. Introduction and related work                   | State the association/energy problem, contributions and actual outcome—including a qualified C3 outcome.                          |
| II. System model and objective                     | Establish load, airtime, interference, ACM and energy accounting; distinguish selection information from realised evaluation.     |
| III. Controller and comparators                    | Explain C1/C2, the candidate catalogue, exact S0 and learned S3, component removals and certified `S_UNI`.                        |
| IV. Evaluation protocol                            | Define primary configuration, data allocation, retraining, compute budget, endpoints, margins, uncertainty and contingency rules. |
| V. Primary results                                 | Report realised EE, QoS, component contrasts and operational costs before discussing mechanisms.                                  |
| VI. Mechanisms, regime sensitivity and limitations | Explain collision avoidance, unilateral headroom and nominal–realised discrepancies; report every attempted regime.               |
| VII. Conclusion                                    | State the supported operating conditions and the simplest controller justified by the evidence.                                   |

My minimal visual set is **four figures and three tables**, with detailed receipts in supplementary material:

| Item                            | Essential content                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Figure 1: physical mechanism    | Airtime/occupancy-to-power accounting and required power/EE versus off-axis angle.                                                   |
| Figure 2: decision architecture | Learned proposals, joint evaluation and execution, with information availability and exact/learned operations visibly distinguished. |
| Figure 3: primary effects       | Component EE contrasts with zero and +0.5% references; aligned QoS contrasts with their non-inferiority margins.                     |
| Figure 4: mechanism diagnosis   | Net collision avoidance and sacrificed singleton value; nominal prediction versus realised outcome.                                  |
| Table I: model assumptions      | Parameters, primary configuration, sources and author choices.                                                                       |
| Table II: comparator contract   | Observations, catalogue, training status, computation, stopping certificates and fallback accounting.                                |
| Table III: regime outcomes      | Primary and all attempted regimes, component estimates, QoS decision and completed/skipped status.                                   |

Two framing rules are essential:

First, **“C1 and C2 raise EE” remains a hypothesis here**. Their smoke factor removals are not retrained learned ablations. Moreover, v1.6 makes set-level C2 a tie-break while retaining Q2’s proposal role; the architecture description must reflect that final definition. ([v1.5, items 2, 6](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md); [v1.6, §2](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md).)

Second, follow the ladder’s own terminology. **Level B supports a “joint re-evaluation layer”; Level A additionally supports coordination beyond exact unilateral re-evaluation.** Negative interaction residuals around the carrier do not themselves refute useful coordination: avoiding those losses can be valuable. If S3 fails and S0 succeeds, describe learned C1/C2 plus an exact coordinator. ([Ladder, Rungs 0, 2](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-CONTINGENCY-LADDER-PREOUTCOME-2026-09-08.md); [v1.6, §3](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md).)

If C3 adds no established benefit, recommend the simpler supported controller. Retaining an unsupported deployed component merely to preserve the “three-Catfish” identity would weaken the paper.

**For question 3, distinguish the hypothesis, an observed criterion pass and a calibrated statistical claim.**

For the documented Level-B contrast, define

$$
\widehat\eta_a=\frac{\sum B_a}{\sum E_a},
\qquad
\widehat\Delta_3=
\frac{\widehat\eta_{\mathrm{FULL}}}
{\widehat\eta_{\mathrm{DROP\_C3}}}-1.
$$

Let \(q_\ell\) denote each population QoS contrast, oriented so larger is better, with registered non-inferiority margin \(m_\ell\). The conjunction is

$$
H_1:\quad
\Delta_3>0.005
\quad\text{and}\quad
q_\ell>-m_\ell\ \text{for every required QoS endpoint}.
$$

Its null is the union of failures of those conditions. The supplied ladder establishes the +0.5% threshold for Level B; it does **not** establish that the same threshold applies to every C1/C2 contrast. Do not silently expand the registered hypothesis.

Exact prospective wording:

The primary hypothesis concerns configuration a-r0: adding the C3 joint re-evaluation layer increases realised pooled energy efficiency by more than 0.5% relative to the retrained DROP_C3 policy while satisfying every pre-specified QoS non-inferiority margin. The intersection–union criterion requires the EE lower bound to exceed 0.005 and every QoS bound to satisfy its registered margin. Evaluation is restricted to the designated confirmation subset of TRAIN and the declared simulation conditions; overlap with legacy-model development dates is disclosed.

Calling that subset “held out” additionally requires verifying exclusion from successor fitting, tuning, early stopping and repeated selection—not merely noting the `TRAIN` label. The allocation manifest is required by v1.5 but absent here. ([v1.5, items 3–4](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md).)

For one fixed conjunction, valid level-\(\alpha\) component tests yield a level-\(\alpha\) IUT without a Bonferroni penalty merely because all conditions must pass. Independence is unnecessary. **This does not repair miscalibrated tests, provide simultaneous coverage of every displayed interval, or control searching for any successful regime.** ([Berger’s explanation of the IUT result](https://errorstatistics.com/2014/07/31/roger-berger-on-senns-blood-simple-with-a-response-by-s-senn-guest-posts/).)

Adjacent to every interval—directly or in its immediately accompanying caption—state:

* The contrast, endpoint, units and decision margin.
* Method, sidedness and nominal construction level; whether coverage is marginal or simultaneous.
* Numbers of dates and learner seeds, pairing and confirmation-panel scope.
* The measured calibration coverage, its calibration setting and number of replications, and its Monte Carlo uncertainty.

For learned contrasts, v1.5 specifies paired **two-way pigeonhole resampling over dates × learner seeds**, recomputing pooled ratios per draw. This addresses the crossed structure; the method’s name alone does not validate coverage for this particular nonlinear endpoint. ([v1.5, item 3](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md); [Owen, 2007](https://arxiv.org/abs/0712.1111).)

If the numerical criterion passes but nominal calibration remains unestablished, use this wording **only after supplying the coverage receipt**:

The observed bounds satisfy the pre-specified joint criterion on the internal confirmation panel. The interval procedure achieved approximately 0.89 empirical coverage in the reported calibration experiment. This supports reporting the criterion pass under that procedure, but does not establish a nominal-level confidence guarantee or generalisation beyond the declared panel and simulation regime.

A measured 0.89 could be compatible with a 0.90 target given simulation uncertainty; it would be concerning for a 0.95 target. Neither the target nor the calibration sample size is supplied. Two-sided coverage of 0.89 also does not identify the error rate of the one-sided bound used for admission.

Unsupportable claims include validated 95% confidence without supporting calibration, universal “89% confidence,” untouched-TEST/OOD generalisation, all three components helping without their required contrasts, and coordination from Level B alone. **Failure to pass +0.5% means that benefit was not established.** It does not prove a non-positive effect; that stronger statement requires an appropriately calibrated upper bound at or below zero.

**For question 4, disclose both prospective specification and outcome-dependent branching.** A predeclared list reduces discretion; it does not make a selected winner an unselected primary result.

The package needs an explicit precedence clarification:

* v1.5 item 1 says other settings cannot change admission or the claim.
* The later ladder’s Rung 1 permits regime-specific admission and a qualified main result after primary failure.
* v1.6 §4 references R1–R7, whereas the supplied ladder defines R1–R6. The smoke’s `b0` is not thereby established as R7.

Resolve this in a dated amendment before formal outcomes are inspected; retain the original documents. ([v1.5, item 1](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md); [Ladder, Rung 1](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-CONTINGENCY-LADDER-PREOUTCOME-2026-09-08.md); [v1.6, §4](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md).)

Use the following vocabulary precisely:

| Term                                               | Appropriate use                                                                                                                               |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pre-specified / prospectively frozen**           | A dated protocol identifies the choices and what development evidence already existed.                                                        |
| **Pre-registered**                                 | Provide an independently timestamped registration or archived protocol, including amendments. “Sealed” text alone does not verify chronology. |
| **Pre-specified exploratory sensitivity analysis** | Regimes were declared in advance but do not carry protected confirmatory inference. This matches v1.5’s designation.                          |
| **Confirmatory regime-conditional analysis**       | The selection/testing procedure controls the relevant error, or the selected regime receives untouched confirmation.                          |
| **Post-hoc exploratory analysis**                  | The analysis or explanation was introduced after inspecting its outcomes.                                                                     |

These are methodological descriptions, not venue-issued certifications. Preregistration clarifies prediction versus postdiction; it does not confer validity by itself. ([Nosek et al., 2018](https://pubmed.ncbi.nlm.nih.gov/29531091/).)

Keep `a-r0` first and retain its failed status if it fails. Report every attempted regime in declared order, with estimates, uncertainty, QoS and stopping reasons. R2 was **skipped**, not negative. A predetermined “continue until something passes” order still needs selection-aware inference; absent that, report the selected finding as a pre-specified exploratory regime result. ([Regime SMOKE, “Decision items not honoured”](sandbox:/workspace/scratch/7e15cf8f5338/r9a/package-9A/VERTICAL-SLICE-REGIMES-SMOKE-2026-09-08.md).)

**For question 5, these are the three objections I would expect first.** The responses below are defensible positions; the corresponding evidence still has to exist.

| Likely objection                                                                                                           | Shortest defensible response                                                                                                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **“You changed the physics and regimes until the architecture worked.”**                                                   | “We disclose development-informed amendments, exclude legacy numerical evidence, preserve the primary outcome and report every attempted regime; selected sensitivities do not replace the primary inferential claim.” |
| **“C3 is an optimiser with additional information or computation, not a demonstrated learned coordination contribution.”** | “We distinguish learned S3 from exact S0, use retrained information- and budget-matched ablations, and reserve coordination beyond unilateral re-evaluation for comparison with certified `S_UNI`.”                    |
| **“Your narrow TRAIN panel and uncertain coverage cannot support the claimed guarantee.”**                                 | “We restrict the conclusion to the declared internal panel, report empirical coverage and its uncertainty, and withhold nominal-level guarantees unless the relevant bounds are calibrated.”                           |

The present package cannot yet close the second or third objection. Better positioning makes those limitations clear; it cannot substitute for the missing comparator certificate or calibration evidence.

`VERDICT: MODEL_PRESENTATION=a | C3_FRAMING=C3 is an evaluated joint re-evaluation layer, with coordination claimed only beyond certified unilateral re-evaluation. | CLAIM_WORDING=Any positive claim is conditional on the declared regime and panel, a greater-than-0.5% relative EE lower bound, all registered QoS margins, and validated inferential calibration. | TOP_RISK=Unverified inferential calibration`
