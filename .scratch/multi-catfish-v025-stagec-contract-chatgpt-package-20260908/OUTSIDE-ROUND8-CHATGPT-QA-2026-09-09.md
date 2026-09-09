**I would not admit the learned coordinator from this package yet.** My recommendation is fixed SINR-margin-aware immediate scoring, with C2 restricted to tie-breaking, followed by an `a-r0` admission screen against genuine iterated `S_UNI`. These are proposed amendments—not changes already authorised by the sealed contract.

Three qualifications matter. The slice uses a decision-instant nominal snapshot but evaluates outcomes over 48 boundaries; its `S_UNI` column is a union-ceiling proxy; and the regime table contains a positive R6 C2 marginal, so the deterioration is not universal across the reported rows. All are development observations, not performance results. Sources: [VERTICAL-SLICE-SMOKE-2026-09-08.md](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/VERTICAL-SLICE-SMOKE-2026-09-08.md), “Shortcuts”; [VERTICAL-SLICE-REGIMES-SMOKE-2026-09-08.md](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/VERTICAL-SLICE-REGIMES-SMOKE-2026-09-08.md), “Cross-regime numbers.”

**1. Nominal versus realised divergence**

An exact nominal optimiser need not maximise realised EE. There are three distinct gaps here:

* **Model gap:** nominal fading and realised fading can rank configurations differently.
* **Integration gap:** snapshot scoring and within-step integration can disagree even with fading disabled.
* **Objective gap:** the contract maximises a surplus involving frozen \(\eta_{\rm ref}\), preferences and continuation—not the realised pooled ratio itself. Positive \(\Delta B-\eta_{\rm ref}\Delta E\) does not generally imply higher EE than an arbitrary comparator.

The last distinction follows directly from the contract’s definitions and standard fractional programming: the ratio-equivalent multiplier is updated in Dinkelbach’s procedure, whereas this package freezes a calibration value. Sources: [Contract](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md), §§B4, D2; [Shen and Yu, §II-A](https://arxiv.org/pdf/1802.10192).

Selection can also preferentially choose optimistic model errors. That explains disappointment relative to predictions; it does **not**, by itself, establish inferiority to another policy. [Smith and Winkler](https://scholars.duke.edu/publication/798952).

| Remedy                                | Information and computational cost                                                                                                                                                               | Legitimacy under frozen §A                                                                                                                                                                              |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Fading-margin-aware scoring**       | Apply a fixed margin to nominal decoding SINR; recompute predicted service, bits and corresponding energy consistently. Modest additional arithmetic or model evaluation; no new live telemetry. | Can preserve the primitive information set. The margin, scoring rule and calibration provenance still require a prospective amendment.                                                                  |
| **Expected-value selection**          | Score \(\mathbb E[B-\eta_{\rm ref}E-\Phi\mid I_{\rm coordinator}]\). Requires a declared conditional channel distribution; scenario evaluation can multiply model cost by the scenario count.    | No realised-fading access is necessary, but a distribution known to the simulator is not automatically declared controller knowledge. Add and freeze its provenance explicitly.                         |
| **Chance-constrained selection**      | Impose a specified service/outage probability. Requires distributional assumptions, dependence information and either scenarios or conservative analytical approximations.                       | Legitimate with declared statistical knowledge and budget. It introduces a new guard, which must be equalised and cannot restore a removed factor.                                                      |
| **Robust or percentile SINR**         | Use a lower SINR quantile or an uncertainty set. Scalar approximations are cheap; joint robust evaluation can be expensive and conservative.                                                     | Requires a declared quantile model or uncertainty envelope. Separate per-link percentiles do not automatically certify joint service.                                                                   |
| **Shrink nominal gains**              | Candidate-dependent reliability weighting, Bayesian correction or an acceptance threshold; cheap online, but requires a justified calibration rule.                                              | Possible from existing inputs after amendment. Multiplying **every complete gain**, including BASE’s zero gain, by the same positive constant changes neither ranking nor acceptance.                   |
| **Conservative ACM back-off**         | Choose more robust MODCODs; can improve decoding reliability while increasing airtime or reducing throughput.                                                                                    | A scoring-only approximation can preserve the physical experiment. Changing executed ACM changes the physical policy and requires a broader amendment.                                                  |
| **Learn realised-outcome correction** | Fit predicted model error from separate development data using deployment-available features; adds training, calibration and inference cost.                                                     | Possible without live fading, but changes the target and experiment. It must not silently replace C3’s interaction-residual target. New ACK/NACK or channel history would expand the present interface. |

These remedies have established precedents, but no transferable guarantee for this simulator. ETSI compares fixed, variable and adaptive ACM margins; probabilistic and worst-case beamforming methods explicitly pay for uncertainty assumptions and conservatism. Feedback-based adaptation such as SALAD illustrates the additional information required by an online correction. [ETSI TR 102 376-1, Annex E.3](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237601/01.02.01_60/tr_10237601v010201p.pdf), [Wang et al.](https://www.se.cuhk.edu.hk/~manchoso/papers/cctxbeam-icassp11.pdf), [Mutapcic et al.](https://web.stanford.edu/~boyd/papers/pdf/rob_downlink_bf.pdf), [SALAD](https://arxiv.org/abs/2510.05784).

**My primary choice is fixed SINR-margin-aware immediate scoring.** Apply one independently justified, sealed decoding margin and form an internally consistent score

$$
F_m(a)=B_m(a)-\eta_{\rm ref}E_m(a)-\Phi(a).
$$

Keep the executed physical policy and realised endpoint definition fixed. This targets threshold-sensitive optimism without requiring new live observations, a learned correction or repeated fading scenarios. Its cost matters because the later gate reports selection exceeding the deadline, principally through continuation evaluation. It is a conservative approximation, not a certified outage guarantee. [4D-GATE decisions](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-CONTROLLER-DECISIONS-4D-GATE-2026-09-09.md), opening paragraph and items 1–5.

Do not choose the margin by finding which value rescues this SMOKE world. Specify its uncertainty rationale independently, disclose that the amendment followed development inspection, and freeze it before the clean admission screen. Version the scoring/decomposition consistently across arms; preserve the distinction between approximate selection and exact labels. **Preserving inputs is not permission to silently change the sealed objective.** [Contract, §§A2–A4, B4, F3](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md).

**2. Continuation: plausible degradation, but the cause is undiagnosed**

Adding C2 changes what is optimised. An immediate sacrifice can be intentional, but a three-offset surrogate supplies no guarantee that future realised benefits repay it. The contract explicitly identifies the learned quantities as supervised surrogates rather than Bellman values. Short model rollouts are an established response to model error, although that literature does not establish the correct horizon here. [Contract, §C1](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md); [Janner et al.](https://arxiv.org/abs/1906.08253).

The diagnostic should use **decision contrasts**, not only prediction RMSE.

**(a) Implementation defect.** At a matched anchor, let \(x_0\) maximise immediate nominal score \(I_N\), and \(x_3\) maximise \(I_N+\sum_{h=1}^3 c_h^N\), over identical feasible candidates. Verify:

$$
\Delta I_N=I_N(x_3)-I_N(x_0)\le0,\qquad
\Delta I_N+\sum_{h=1}^3\Delta c_h^N\ge0.
$$

If either fails, inspect candidate support, guards, timeouts and ranking before blaming forecasts.

Reconstruct \(C1+C3=F(a)-F(a^0)\); check \(\Phi\) once, κ normalisation once, bits versus bit/s, exclusion of offset zero, terminal truncation and the specified absorbing \(-\kappa\) penalties. Keep decomposition reference \(a^0\) separate from the previous association used for event accounting. [Contract, §§A3–A4, B4, G/T1](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md).

**(b) Forecast error.** For each candidate pair and offset, compute:

$$
\Delta F_{R,48}-\Delta F_{N,\mathrm{snapshot}}
=
\underbrace{\Delta F_{N,48}-\Delta F_{N,\mathrm{snapshot}}}_{\text{integration error}}
+
\underbrace{\Delta F_{R,48}-\Delta F_{N,48}}_{\text{fading error}}.
$$

Here \(\Delta\) compares the same two profiles; future background and continuation policy must also match. Report the decomposition by offset, alongside service errors, MODCOD transitions and cap binding.

There is another concrete suspect: **SMOKE C2 sums per-move continuations.** Compute joint future continuation minus the sum of singleton continuations. Immediate C3 corrects current interactions; it does not automatically remove optimistic singleton addition at every future offset. Repeated negative future interactions could explain C2 overvaluation even without fading. [Slice, “Shortcuts”](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/VERTICAL-SLICE-SMOKE-2026-09-08.md).

**(c) Genuine temporal trade-off.** From the same anchor, evaluate both decisions under the declared subsequent policy, physically keyed common fading and complete event accounting. Separate current realised sacrifice from future repayment, then recompute pooled \(\sum B/\sum E\) over the prescribed horizon and episode.

* Reliable later repayment supports a genuine temporal trade-off.
* Predicted repayment that disappears supports model error.
* An absorbing-action forecast followed by actual reselection is a continuation-policy mismatch.

**The supplied ZIP cannot complete this diagnosis:** it contains summaries rather than the required candidate/per-offset receipts, and the slice explicitly lacks arm-specific closed-loop trajectories. The later approximation decisions prescribe additional agreement checks; they do not retroactively validate the snapshot run. [Slice, “Shortcuts”](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/VERTICAL-SLICE-SMOKE-2026-09-08.md); [Selection-time decisions, items 2–4 and 8](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-CONTROLLER-DECISIONS-SELECTION-TIME-APPROXIMATIONS-2026-09-08.md).

**C2 entry:** use it only among maximisers of the immediate score, with deterministic tie-breaking. Discounting or horizon 1 merely reduces exposure to an unreliable forecast; neither diagnoses the problem. Use a future-survival constraint only if independently required by service specifications, without restoring a removed C2 route through the guard. This recommendation concerns the **set-level continuation term**; Q2’s existing role in constructing \(a^0\) is a separate intervention. [Contract, §§A3–A4, C1–C3](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md).

**3. Negative interactions support a collision-avoidance hypothesis—not demonstrated coordination value**

Negative \(\Psi_A\) says that singleton gains overstate a particular joint move around \(a^0\). It does not prove global submodularity or establish that a coordinator beats sequential optimisation.

A genuine `S_UNI` recomputes joint physics after every accepted unilateral improvement, so it already avoids many collisions caused by simultaneous independent choices. Additional value requires coordinated rearrangements, escaping unilateral local optima, or a separately established computational advantage. [Contract, §§B4, C2, C4](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md).

The falsifiable claim should be:

> Interaction-aware selection prevents enough harmful combinations of individually attractive moves to improve held-out realised pooled EE over both the matched additive selector and genuine iterated S_UNI, while meeting the same QoS and computational requirements.

Let \(D(a)=\sum_i d_i(a)\), \(a_D\) be the additive selection and \(a_C\) the interaction-aware selection, with identical anchors, catalogue and C2 treatment. Report the signed **net collision-avoidance value**:

$$
V_{\rm CA}(t)=
\frac{
\underbrace{\Psi(a_C)-\Psi(a_D)}_{\text{interaction loss avoided}}
-
\underbrace{[D(a_D)-D(a_C)]}_{\text{singleton value sacrificed}}
}{\kappa}
=
\frac{F(a_C)-F(a_D)}{\kappa}.
$$

Report both components and their net, without clipping negative anchors. Also report the frequency of ranking reversals, especially rejection of proposals satisfying

$$
D(a_D)>0,\qquad D(a_D)+\Psi(a_D)<0.
$$

The operational certificate remains realised pooled EE against `S_UNI`; a nominal \(V_{\rm CA}>0\) is only a mechanism certificate. The slice’s negative \(\sum g_I^{FULL}\) measures interaction loss **incurred**, not loss **avoided**. Its printed summaries lack the comparator decompositions needed to calculate this statistic. [Slice, “Factor arms and marginals”](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/VERTICAL-SLICE-SMOKE-2026-09-08.md).

A particularly useful witness is to re-anchor at a certified unilateral optimum \(u\). For individually feasible constituent moves, \(d_i^u\le0\); therefore an improving joint escape must satisfy

$$
\Psi_A^u=F(a)-F(u)-\sum_i d_i^u>0.
$$

Thus negative interactions around the carrier can coexist with positive complementarity around `S_UNI`. This is a mathematical consequence of the decomposition, not an observed finding.

Comparing only with nearest-eligible/NULL risks attributing ordinary association improvement to coordination. Moreover, the reported proxy’s lead over FULL cannot establish any numerical comparison with genuine `S_UNI`. The later gate states that exhaustive `S_UNI` was implemented, but supplies no corresponding outcome or termination receipts. [Slice, “Shortcuts”](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/VERTICAL-SLICE-SMOKE-2026-09-08.md); [4D-GATE decisions, opening paragraph](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-CONTROLLER-DECISIONS-4D-GATE-2026-09-09.md).

**4. What should carry admission**

For the proposed **coordination-performance route**, I would use this hierarchy:

| Certificate                                                            | Admission role                                                                                                                                                                                                                                |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **S0 realised gain, alongside its nominal prediction**                 | **Load-bearing:** gains selected by the final deployable rule must survive realised evaluation against a declared meaningful reference. Nominal positivity alone is insufficient.                                                             |
| **S0 versus genuine S_UNI**                                            | **Load-bearing:** establishes opportunity beyond exhaustive sequential improvement. Match information, objective, operational budget and fallback accounting; require termination evidence or label the comparator budget-limited.            |
| **Corrected factor-oracle marginals**                                  | **Load-bearing mechanistic support for the architecture being admitted:** require a decision-relevant C3 effect under the final C2 rule. For an admission claiming all three factors are viable, all three corrected factor contrasts matter. |
| **Realised availability/QoS, physics validity and deadline behaviour** | **Mandatory admissibility conditions:** nominal served-count non-decrease is insufficient; timeout/fallback outcomes must enter B/E.                                                                                                          |
| **\(J1-U_{\rm all}\)**                                                 | **Informative, not decisive:** two entirely additive beneficial moves can exceed the best single move. This neither identifies interaction value nor establishes superiority over iterated `S_UNI`.                                           |
| **Cap-hit, plateau, ACM distribution and lit beams**                   | **Mechanism diagnostics:** useful for explaining losses and saturation, not standalone benefit certificates. In b0, cap-hit \(=1\) is part of the fixed-RF construction.                                                                      |

These roles follow the distinctions in [Contract, §§C2–C4, F2, G–H](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md). The cap-hit interpretation is explicitly recorded in [the synthetic report, “DEFECTS”](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-SYNTHETIC-MAP-R1-REPORT-SUPERSEDED-B2-2026-09-08.md).

Two limits prevent overclaiming:

First, **oracle factor removal and retrained neutral-source substitution are different estimands**. Positive oracle marginals do not prove learned source benefits; negative oracle marginals are not mathematical impossibility proofs, because approximation can sometimes correct nominal-model bias. The proposed gate is a conservative engineering admission rule. A correction or acceleration study would need its own declared claim. [Contract, §§C3–C6](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md).

Second, **only `a-r0` can determine admission**, and the README explicitly marks the synthetic factor arms as superseded. Neither favourable sensitivity cells nor superseded factor marginals can rescue the primary gate. The bundle also omits the underlying complete PHYSICS-GO threshold specification, so its existing numerical admission rule cannot be certified here. [v1.5 amendment, §1](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md); [00-README-r8.md](sandbox:/workspace/scratch/2d7e6ca6f1d6/r8-review/package-r8/00-README-r8.md).

The immediate disposition should therefore be **admission unestablished**, with a clean, prospectively sealed test of the amended selector. A tie-only C2 may legitimately yield no C2 benefit; retaining a promise of three positive contributions would require evidence, not another adjustment.

`VERDICT: REMEDY_PRIMARY=FIXED_SINR_MARGIN_SCORING_PROSPECTIVE_AMENDMENT | C2_ENTRY=IMMEDIATE_SCORE_TIES_ONLY | COORDINATION_CLAIM=NET_COLLISION_AVOIDANCE_PLUS_REALISED_EE_VS_S_UNI | LOAD_BEARING=S0_REALISED_GAIN,S0_VS_CERTIFIED_S_UNI,CORRECTED_FACTOR_ORACLE_EFFECTS,REALISED_QOS,VALIDITY_AND_DEADLINE`
