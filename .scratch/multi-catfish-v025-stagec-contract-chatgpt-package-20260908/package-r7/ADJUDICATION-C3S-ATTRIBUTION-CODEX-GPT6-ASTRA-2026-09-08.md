The gain is reproducible; the controller’s causal attribution is too strong. Diag3 can test whether particular restricted policies retain the gain, but its declared reading cannot identify coordination versus exact rescoring.

I independently decoded and pooled all 27 receipts, checked step coverage and initial-state matching, and verified all 192 source-file hash bindings. I did not inspect diag3 outcomes.

| Arm | Anchored gain | Anchor-ablated gain |
|---|---:|---:|
| LITE | +2.921776% | +2.893833% |
| Forced renewal | +0.494376% | exactly 0 |
| Random renewal | −1.116708% | −1.252791% |
| NULL | 90/90 steps identical | — |

Forced renewal under ablation matches BASE in actions, bits, joules, service, beam count and nominal endpoints across all 360 steps, despite 3,027 explicit renewals.

For **A**, that strongly supports “the LITE advantage does not require segment anchoring.” It does **not** establish “the anchored gain contains no renewal contribution” or “harness/accounting defects are excluded.”

Several distinctions matter:

- **The ablation changes the physical regime.** It makes link power 0.825 W, removes opening power-infeasibility outages and changes subsequent trajectories. Similar pooled effects across these regimes do not identify the anchor-mediated share of the original effect. Individual unit gains change by approximately −1.079 to +0.549 percentage points; the pooled similarity conceals cancellation.
- **Random churn is a weak control for selective switching.** LITE makes 20,395 handovers versus BASE’s 20,076 under anchoring. Zero *explicit renewals* does not mean its ordinary association changes never open new power segments. Random renewal losing excludes a generic random-switching explanation, not selective trajectory effects.
- **Beam accounting remains a concrete model-bound explanation.** Under ablation, LITE uses 14,655 active beam-slots versus BASE’s 14,832. Using the declared PA curve and circuit charge, each active beam costs 6.265900454 W, plus 0.2 W per active satellite. These terms reproduce the ablated energy totals to floating-point precision: 177 fewer beam-slots save approximately 33,361 J, offset by 126 J from 21 additional satellite-slots. Thus the energy advantage is explained by activation counts under this model. That is internally consistent accounting, but its beam-to-hardware mapping, shutdown assumptions and payload boundary remain assumptions—not validated physical savings. The source itself identifies the beam-to-RF-chain mapping as a modelling assumption. [Power accounting](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/link_budget.py:270)
- **NULL tests unchanged-action execution.** It strongly disfavors counterfactual evaluation mutating BASE’s execution. It cannot detect a shared physics error whose effect depends on changed beam counts or associations.
- **Service counts are equal; served sets are not authenticated.** BASE and LITE each serve 35,971 anchored user-steps, with equal counts at every step. All 29 missing user-steps occur in eight initialization steps. Removing those eight paired steps leaves a descriptive gain of **+3.007009%**, so those immediate outage endpoints do not explain the gain. User identities and downstream counterfactual effects remain unrecorded.

Also, “approximately two users changed versus BASE” means changes against **the BASE proposal on LITE’s own state**, not against the separately evolved BASE trajectory.

Point 2 needs similar qualification. Both selectors run every step; the cadence-asymmetry hypothesis is ruled out. But the *cause* of the phase slope is unverified. Anchored BASE’s average active beams fall from 58.92 in phase 0 to 27.77 in phase 3, while its pooled EE falls from 129.46 million to 78.51 million bits/J. Phase changes geometry, occupancy, available opportunities and the comparison denominator together. Incumbent-dependent candidate selection also permits cross-arm candidate sets to diverge. Representation aging is plausible, not identified by eliminating cadence asymmetry. [Candidate assignment](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/action_contract.py:192)

For **B**, replace the ⅔/⅓ reading. Predeclaration prevents outcome-driven thresholds; it does not make an invalid decomposition valid.

There is a particularly damaging implementation confound:

| Actual LITE selection | Anchored | Ablated |
|---|---:|---:|
| Unilateral-labelled, one changed user | 55 | 64 |
| Evacuation-labelled, one changed user | 125 | 127 |
| At least two changed users | 180 | 169 |

Thus exactly **half** the anchored selections are single-user moves. Moreover, unilateral-only retains one Q-ranked alternative per user, whereas singleton evacuations enumerate their commonly legal destinations. The average anchored catalogue contains 100 unilateral rows and 816 evacuation rows. Evacuation-only can outperform unilateral-only through broader **single-user search**, without multi-user coordination. [Catalogue construction](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:308)

Even without that defect, \(u=e=g\) is possible: both restrictions retain the entire gain, yet the declaration labels rescoring principal. These are sufficiency results, not causal shares. A factorial Shapley allocation,
\[
\phi_U=(u+g-e)/2,\qquad \phi_E=(e+g-u)/2,
\]
would sum to \(g\), but would allocate **catalogue availability**, not identify mechanisms.

My replacement statistic is a **signed singleton/interaction surplus decomposition on common frozen anchors**. For anchor \(t\), let \(a^0_t\) be BASE, \(a^*_t\) the deployably selected complete profile, \(M_t\) its physically changed users, and \(a^{(i)}_t\) BASE with only user \(i\)’s selected change. Evaluate every counterfactual with identical state, physical identities and exogenous randomness. Define
\[
F_t(a)=B_t(a)-\eta_0E_t(a),\qquad
\eta_0=\frac{\sum_tB_t(a^0_t)}{\sum_tE_t(a^0_t)},
\]
\[
A_t=\sum_{i\in M_t}[F_t(a^{(i)}_t)-F_t(a^0_t)],
\]
\[
I_t=F_t(a^*_t)-F_t(a^0_t)-A_t.
\]

Report
\[
g_A=\frac{\sum_tA_t}{\eta_0\sum_tE_t(a^*_t)},\qquad
g_I=\frac{\sum_tI_t}{\eta_0\sum_tE_t(a^*_t)}.
\]
Then \(g_A+g_I\) **exactly equals the matched-anchor relative pooled-EE gain**. Keep negative contributions; do not clip or force shares into \([0,1]\). The evaluation reference \(\eta_0\) must not feed back into profile selection.

This decomposes a new, explicit matched-anchor estimand—not the original closed-loop \(g\), which includes trajectory feedback. Pair it with
\[
\Delta_{\rm joint}
=\frac{\eta(U_{\rm all}\cup J_{\ge2})}{\eta(U_{\rm all})}-1,
\]
where \(U_{\rm all}\) includes BASE and **every legal unilateral alternative**, and \(J_{\ge2}\) requires at least two physically changed users. Use matched information, guards and evaluation conditions. Report paired world/date-cluster uncertainty, not 360 independent-step uncertainty.

Positive interaction alone does not establish practical coordination value; positive \(\Delta_{\rm joint}\) alone can reflect bundling independent improvements. Together they are substantially more informative than catalogue labels. Existing receipts cannot supply the missing singleton counterfactuals.

For **C**, I accept information parity and interaction-only credit as design principles. They do not make C3 unfalsifiable. **A zero residual marginal must be an allowed result that removes C3.**

Three corrections are necessary:

First, dropping \(e_i\) follows from whole-network C1 and applies **whether diag3 favors (b) or (d)**. Likewise, information parity remains necessary even if coordination dominates.

Second, “current-profile joint physics features” must identify whose proposed actions define the background. These are counterfactual computations, not simply fresher telemetry. Freeze that reference, the information interface and the computation budget. Otherwise, moving joint-model computation into head features can silently move C3 itself into BASE.

Third, interaction is a mathematical property of a specified objective and reference—not synonymous with “whatever the trained heads cannot express.” Pairwise \(\Psi/2\) is appropriate when singleton contributions use the matching \(00/10/01/11\) convention. The decoder must still optimize the **complete objective**, not \(\Psi\) alone. For larger sets, equal splitting of aggregate interaction is not generally Shapley allocation; asymmetric subset interactions require their corresponding allocations. [Stage-2 item 5](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md:9)

A falsifiable claim would be:

> With successor heads, features, catalogue and budgets frozen, atomic joint selection improves held-out pooled EE over both DROP_C3 and an information-matched exact unilateral decoder, satisfies the declared QoS margins, and demonstrates decision-relevant nonadditivity. A learned S3 additionally beats matched S0.

Retain the sealed FULL−DROP margin of +0.5 percentage points with its required confidence bound. Failure means no demonstrated C3 contribution under that scope. If learning merely approximates S0 faster, claim acceleration at matched quality and cost—not additional EE.

For **D**, these certificates have different roles; demanding that every named number be positive would itself be incorrect.

| Certificate | Requirement before the relevant training is admitted |
|---|---|
| **U1** | Complete, authenticated unilateral opportunity census and certified optimum. **U1 need not exceed BASE for C3:** pure coordination can exist with no improving single move. C1 requires its own positive factor-oracle marginal. |
| **J1 / union** | Genuine multi-user headroom beyond BASE and the complete unilateral alternative, exceeding certified numerical error under matched QoS. Catalogue names are insufficient. |
| **S0** | Deployable nominal selection clears the sealed **1% practical gain threshold**, with acceptable QoS and operational execution. For a coordination claim, establish its residual advantage over full unilateral rescoring. |
| **Usable-energy range** | Authenticate feasible opportunities under actual occupancy, ACM, caps and integrated DC accounting. An **energy-saving** mechanism needs accessible savings beyond numerical error with acceptable delivery/QoS; positivity is not required for every beam or every matrix setting. |
| **Factor-oracle contrasts** | Each retained component has positive FULL−DROP marginal beyond numerical error and acceptable QoS; positive U1/J1 alone cannot substitute. |

A zero energy-saving range does not logically prohibit EE improvement through more bits at unchanged energy; it falsifies the claimed energy-saving mechanism. Conversely, a broad energy range does not establish independent C3 value.

All certificates depend on passing physics, target-to-execution, accounting, catalogue, calibration and NULL checks. Training uses the already designated **a-r0 primary**, not whichever secondary cell happens to win. Recheck C3 headroom after successor heads are trained. [Admission rules](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:13)

A (d)-dominant legacy result changes **none** of those physical admission requirements. It changes expectations and the interpretation of comparator gaps. Operational deployability also remains unproved by information admissibility: recorded LITE selection times exceed 30.08 seconds on 12/360 anchored and 20/360 ablated decisions.

For **E**, my subjective pre-diag3 probabilities, conditional on the evidence above, are:

1. **Mixed: 45%.**
2. **Exact rescoring dominant (d): 40%.**
3. **Multi-user coordination dominant (b): 15%.**

The single observation that would most move me is LITE’s residual pooled gain after a complete, iterated exact-unilateral decoder with matched information and deadline. A substantial residual supported by joint improvements at unilateral local optima would move me toward (b); collapse would move me toward (d).

I accept ending legacy diagnostics after diag3 **provided its conclusion remains catalogue sufficiency, with mechanism attribution unresolved**. Put the stronger discrimination into V025. “No more legacy experiments” is defensible; “diag3 will decide the mechanism” is not.

VERDICT: ATTRIBUTION=UNSOUND:anchor independence is supported but blanket artefact exclusion is not | DIAG3_READING=REPLACE:matched-anchor signed singleton/interaction surplus decomposition plus complete-unilateral versus union contrast | DESIGN_UNDER_D=ACCEPT | ADMISSION_CERTIFICATES=physics-and-integrity PASS; certified U1 census; genuine J1 beyond BASE/U1; deployable S0 gain≥1%; usable-energy opportunity for energy-saving claims; positive retained-factor oracle marginals; QoS PASS