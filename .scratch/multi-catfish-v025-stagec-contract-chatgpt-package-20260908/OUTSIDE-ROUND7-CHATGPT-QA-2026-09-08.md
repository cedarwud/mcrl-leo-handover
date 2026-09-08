**REVISE before real source generation.** The package has the right safeguards in outline, but it does not yet establish an identifiable learned C3 or a powered confirmation experiment. I treat the audits as evidence about their inspected snapshots, not as proof that the prescribed repairs have passed.

Below, **Contract** means [V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md), **Amendment** means [the v1.5 amendment](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md), and **Review** means [FIRST-PRINCIPLES-REVIEW-CODEX-GPT6-ASTRA-2026-09-08.md](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/FIRST-PRINCIPLES-REVIEW-CODEX-GPT6-ASTRA-2026-09-08.md).

**1. FULL − DROP_C3 alone does not identify coordination.**

Let \(h_{t-1}\) denote committed history, \(G_t\) current geometry, \(m_{u,t}\) the legal-action mask, and \(\bar a_{-u}\) the frozen background excluding user \(u\). The learned-head information set is

$$
\mathcal I^Q_{u,t}
=\sigma\!\left(
m_{u,t},
\left\{
x^1(G_t,h_{t-1},\bar a_{-u},a_u),
x^2(G_t,h_{t-1},\bar a_{-u},a_u)
\right\}_{a_u}
\right).
$$

Here \(x^1\) contains the declared nominal margin/power/cap/mode, occupancy, activity, angle, eligibility and historical fields; \(x^2\) contains the completed C2 schema and causal nominal forecasts. Q2 explicitly uses the previous committed served set excluding the focal user. V1 must finish Q1’s corresponding background semantics and both schemas. **[Contract, Stage 6, items 2–3.]**

For the coordinator, write

$$
\mathcal I^C_t
=\sigma\!\left(
Z_t,a_t^0,\mathcal C_t,\mathcal M,
\{\widehat{\mathcal P}(a;Z_t,\mathcal M):a\in\mathcal C_t\}
\right),
$$

where \(Z_t\) contains global physical candidates and identities, current geometry and cross-gains, demands, committed activity, shared-resource constraints and eligibility; \(\mathcal M\) is the nominal model; and \(\widehat{\mathcal P}\) returns candidate-profile load, interference, powers, activation, service, bits, energy and declared continuation quantities. The candidate profile itself supplies other users’ simultaneous proposed choices. **[Amendment, item 6; [Audit B, §§4,13](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/PIPELINE-AUDIT-B-source-learner-deployment-2026-09-08.md).]**

An important distinction: deterministic model calculations add no information in the strict mathematical sense **if both methods already receive every primitive input**. They still add representation and computation unavailable to compressed per-user rows. The contract must separately declare observation access, derived features, model access and computational resources.

A coordination attribution requires these controls:

* **Match the intervention.** Learned FULL and neutral-DROP retain the same selector, catalogue construction, information interface, guards, deadline and fallback. The oracle interaction knockout separately removes only \(\Psi\), retaining joint search.
* **Prevent hidden restoration.** An exact evaluator must not silently reinsert the omitted interaction through a full-\(F\) score.
* **Implement \(S_{\rm UNI}\) fully.** At each internal iterate, evaluate every legal unilateral alternative with the same nominal joint physics, choose a deterministic improving move, and repeat until a unilateral local optimum or the declared budget limit. Commit only the final profile atomically; hypothetical intermediate moves must not create physical handovers. Report whether termination certified a local optimum.
* **Match resources and reference conventions.** Use the same accessible primitives, model fidelity, objective/continuation convention, initial proposal, physical event reference, hardware and deadline. Declare catalogue reachability and model-call counts. One Q-shortlisted alternative per user is insufficient.
* **Require complementary evidence.** Report held-out pooled EE and QoS against both DROP_C3 and the \(S_{\rm UNI}\)-equipped comparator, plus counterfactual evidence that nonadditivity changes decisions.

These requirements largely implement the already accepted [Controller Response, items 3–5](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/CONTROLLER-RESPONSE-TO-ASTRA-ATTRIBUTION-2026-09-08.md). Merely naming \(S_{\rm UNI}\) in Contract item 9 does not complete them.

I would revise Response item 4’s requirement \(g_I\ne0\): **nonzero selected aggregate interaction is not necessary for useful coordination.** Avoiding a harmful joint move may correctly select a singleton with \(\Psi=0\); signed interactions may also cancel across decisions. Require decision-relevant nonadditivity, including rejected alternatives.

A zero C3 marginal must terminate the positive claim without redesigning the source or regime around the result. It means no demonstrated incremental benefit under the specified information, learner, catalogue and budget. A confidence interval whose upper bound excludes the practical margin supports a stronger “no practically relevant benefit” conclusion; failure of the lower-bound gate alone remains inconclusive.

**2. The proposed independent-row learner cannot generally represent \(\Psi_A\).**

“Pairwise zero-bootstrap regression” specifies the training loss, not an architecture capable of representing interactions. Shapley allocation does not eliminate dependence on coalition membership and other users’ actions. **[Contract, Stage 6 items 1,4; Stage 7 item 6; Review, Pass 1(d).]**

Consider two contexts with identical exposed per-user rows:

| Context      | \(F_{00}\) | \(F_{10}\) | \(F_{01}\) | \(F_{11}\) | \(\Psi_{\{1,2\}}\) |
| ------------ | ---------: | ---------: | ---------: | ---------: | -----------------: |
| Synergistic  |          0 |          1 |          1 |          3 |                 +1 |
| Antagonistic |          0 |          1 |          1 |         −2 |                 −4 |

The same local action requires different interaction shares and a different joint decision. A deterministic local head cannot distinguish these contexts. Moreover, a sum \(q_1(a_1)+q_2(a_2)\) has zero mixed difference,

$$
Q_{11}-Q_{10}-Q_{01}+Q_{00}=0,
$$

so it cannot represent either nonzero interaction exactly.

Regression can still learn a **conditional mean** from aliased inputs. Therefore “unlearnable at all” is too strong; the correct objection is that decision-specific interaction is not identifiable. More samples cannot recover omitted coalition context.

My minimal recommendation is a **set-conditioned scalar interaction head**:

$$
\widehat\Psi_\theta(Z_t,a^0,A,a_A),
$$

with explicit physical identities, selected actions and sufficient global resource context. Train directly on the scalar residual, enforce permutation invariance and \(\widehat\Psi(\varnothing)=\widehat\Psi(\{u\})=0\), and optimize the complete C1+C2+C3 score. This avoids unnecessary Shapley bookkeeping. Pairwise difference regression remains possible, but needs reference anchoring and connected comparison support so arbitrary offsets do not corrupt comparisons across sets.

A sum of pairwise factors is sufficient only if higher-order interactions are absent or their approximation error is explicitly accepted and measured. Occupancy thresholds, ACM transitions, shared activation and joint feasibility provide no such guarantee. **[Review, Pass 2(ii), items 3–5.]**

A learned proposer plus exact evaluator is another legitimate S3: learning determines which candidates are evaluated within a fixed budget. If every candidate is already evaluated exactly, the proposer cannot improve the attained optimum merely by proposing it again.

For

$$
S_0=\arg\max_{a\in\mathcal C}S(a),
$$

no S3 can attain a larger **same exact score over the same catalogue**. “S3 beats matched S0” must instead mean one predeclared outcome:

* better realized closed-loop EE through improved prediction or model-error correction;
* better realized EE under equal computational limits, including timeouts;
* comparable quality with less computation—an acceleration claim.

An exact nominal immediate selector is not necessarily optimal for realized closed-loop EE. Nevertheless, any improvement must identify what learning adds. Also distinguish the **target-sum factor oracle** from the separate **exact-\(F\) ceiling**, as required by [Engine Decisions, item 2](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/V025-CONTROLLER-DECISIONS-ENGINE-AUDIT-2026-09-08.md).

One algebraic repair is mandatory: Amendment item 2 defines \(C1=\sum_i d_i+\Phi\), but then claims \(C1+C3=\Delta F\). As written,

$$
C1+C3=\Delta F+\Phi.
$$

Either state this identity or incorporate the signed \(\Phi\) contribution consistently into \(F\) and its increments. Charge it once.

**3. Neutral-source DROP estimates a training-source intervention.**

Let \(\pi_{z,s}\) be the policy trained with source assignment \(z\) and learner seed \(s\), conditional on the frozen source datasets and training procedure. Define

$$
\rho_z=
\frac{\mathbb E_{S,W}[B(\pi_{z,S},W)]}
     {\mathbb E_{S,W}[E(\pi_{z,S},W)]},
\qquad
\Delta^{\rm source}_3=\frac{\rho_{111}}{\rho_{110}}-1,
$$

where \(0\) means **the precisely specified neutral source**, not an absent head. Analogous contrasts define C1 and C2. These are conditional contributions with the other informative sources enabled, not factorial average main effects. **[Contract, Stage 7 items 7–8; Review, Pass 1(c).]**

The apparent “removal” confound is that neutral-trained routes retain physical predictors, while other routes can retain overlapping physical knowledge. Neutral supervision may also introduce harmful training rather than merely remove useful information. Thus a positive contrast can reflect improved source alignment or avoidance of harmful neutral updates.

This does **not** invalidate a properly controlled source-treatment estimand. It invalidates wording that claims removal of the head, all associated physical information, or the physical mechanism. Seal neutral-label construction, feature/stratum matching, pairing, centering, update dose and deployment participation. **[Audit B, §8 and “Filled ? entries.”]**

**Yes, report checkpoint knockouts separately.** Amendment item 6 already requires them. They estimate reliance of the trained FULL policy on a deployed contribution; they do not estimate what retraining without that contribution would achieve.

The package already recognizes the distinction: [CD Decisions, item 13](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/V025-CONTROLLER-DECISIONS-PIPELINE-AUDITS-CD-2026-09-08.md) separates oracle factor arms from learned neutral-source experiments. V1 must explicitly map Amendment item 2’s literal term removal to the oracle experiment, and Contract item 7 to source substitution.

The defensible claim is: **“Informative C3-source training improved pooled EE relative to the specified neutral-source training, with all heads retained.”** Coordination attribution requires the additional controls in answer 1.

**4. Power is not established; five seeds can impose a binding precision limit.**

The contract supplies a margin but does not specify a true alternative effect or crossed variance components. Consequently, no unconditional claim of adequate power is justified. **[Contract, Stage 8 items 11–12; Amendment, item 3.]**

For true relative gain \(\Delta^*>0.005\), 80% power per contrast and the stated 97.5% lower bound, the review’s normal approximation becomes

$$
n\approx
\left[
\frac{(1.960+0.842)\sigma}
{\log(1+\Delta^*)-\log(1.005)}
\right]^2.
$$

Using its SD sensitivities gives:

| Paired cluster SD | True gain 1% | True gain 2% | True gain 3% |
| ----------------- | -----------: | -----------: | -----------: |
| 3%                |          287 |           33 |           12 |
| 5%                |          797 |           90 |           33 |
| 10%               |        3,187 |          358 |          131 |

These are approximate **independent-cluster counts for 80% power per contrast**, not date×seed cell counts. They reproduce Review Pass 2(iii)’s corrected 5% SD calculation. Pass 1(c)’s zero-margin table does not answer this design.

For crossed effects, the relevant planning condition is approximately

$$
\frac{\sigma_D^2}{D}
+\frac{\sigma_S^2}{S}
+\frac{\sigma_R^2}{DS}
\le
\left[
\frac{\log(1+\Delta^*)-\log(1.005)}{2.802}
\right]^2,
$$

with the residual term adapted to the actual world allocation. **161 dates × five reused models are not 805 independent replicates.** More worlds reduce residual variation; they do not eliminate date or learner-seed effects. **[Review, Pass 1(c).]**

The minimal defensible change is to specify the alternative and variance-component sensitivities prospectively, then increase **independent seeds and, where necessary, dates** to meet this inequality. There is no universal “add four seeds” repair.

For illustration only: with a true 2% gain, date SD 5%, seed SD 1%, 161 dates and negligible residual variance, increasing from five to **nine seeds** raises normal-approximation per-contrast power from about 70% to 82%. For a true 1% gain and date SD 5%, 161 dates are insufficient even with infinitely many seeds; 797 dates is only the date-component lower bound.

The seed floor is substantial. With five seeds and seed SD 1%, the irreducible SE is approximately **0.447%**, giving an optimistic normal half-width of **0.877%**. For a true 1% gain to clear 0.5% with 80% power, the seed component alone requires approximately **32 seeds** at 1% SD, or **128** at 2% SD, before adding other uncertainty.

Pigeonhole resampling appropriately treats crossed factors, but does not guarantee exact finite-sample inference; five seed levels particularly require calibration of the actual procedure. [Owen, *The pigeonhole bootstrap*](https://arxiv.org/abs/0712.1111).

Finally, intersection–union testing removes a multiplicity penalty for the single conjunction; it does not turn 80% constituent power into 80% all-three success. Independent constituent successes would yield \(0.8^3=51.2\%\). Verify date independence or temporal blocking, and calculate the available date count **after** source-training, selection and confirmation separation.

**5. The deadline and manifest do not yet establish deployability.**

A real controller needs the following declarations and evidence:

* **Observation provenance and age:** where global user positions, physical beam identities, cross-channel estimates, service/load state and equipment state originate; their update latency, uncertainty and missing-data behavior.
* **Model availability:** how antenna patterns, interference/resource overlap, power caps, PA behavior and activation costs are calibrated and updated. A simulator’s nominal model is an assumption about controller knowledge.
* **Execution ownership:** gateway versus onboard placement, communication paths, resource reservations, synchronization and atomic application across affected beams/users.
* **An operational timing budget:** sensing, transport, feature extraction, forecasts, catalogue construction, model calls, selection, validation and command delivery. A 30.08 s decision interval does not automatically provide 30.08 s of computation before the action must become effective.
* **A jointly feasible fallback:** independent BASE choices may themselves conflict. Declare safe repair or fallback behavior for stale masks, invalid solves, missing telemetry and deadline misses, and include the resulting endpoints in evaluation.

These requirements follow from **Contract items 9–10**, [Audit D, finding N12](sandbox:/workspace/scratch/e4373577c7c3/review/package-r7/PIPELINE-AUDIT-D-integrator-user-step-trace-2026-09-08.md), and **CD Decisions item 12**, which already rejects cached lookup time as decision time.

There is also an explicit causal limitation: **Amendment item 5 permits future-epoch TLEs** under a non-causal benchmark convention. That is acceptable when labelled accordingly, but an operational claim needs ephemeris available by the decision time. Causal orbital forecasts are permissible; unavailable future-issued records are not operational inputs.

**6. Require these three synthetic acceptance tests before real source generation.**

1. **Exhaustive decomposition and intervention test.**
   Use a hand-computed three-user, two-action, three-step fixture containing additive, synergistic and antagonistic cases, a dummy user, and a future outage. Exercise the production target builder and selectors. Require exact reconstruction with \(\Phi\) charged once, zero dummy Shapley credit, no interaction credit from an unselected partner, correct continuation accounting, and hand-predicted oracle DROP behavior. Separately verify that neutral-source DROP retains and trains the route, while checkpoint knockout removes its deployed contribution.
   **Exposes:** double counting, incorrect Shapley allocation, absent-partner bonuses, scale/time errors and conflated estimands. **[Amendment item 2; Audit D, C3 finding; Review, Pass 3 “Targets.”]**

2. **Information-to-action learner test.**
   Run a tiny production source→training→deployment path using paired contexts with identical legacy-style unilateral rows but opposite joint interactions. Require the revised joint input to distinguish them and S3 to select the correct profiles on held-out synthetic cases. Poison post-decision outcomes and realized future fading; current decisions must remain unchanged. Include an additive placebo, physical-identity relabelling, jointly infeasible individual proposals and an injected timeout that exercises the actual fallback.
   **Exposes:** irreducible input aliasing, future leakage, memorized identity, disconnected learner wiring and unexecuted legality/deadline safeguards. **[Audit B §4; Contract item 10; Review, Pass 3 “Learner/information” and “Process.”]**

3. **Crossed-receipt inference test.**
   Feed the actual merger synthetic raw B/E/QoS receipts with controlled date, seed and world effects. Include unequal energy weights that distinguish pooled EE from mean world EE, identical arms, undefined-ratio cases, injected alternatives, and the least-favourable conjunction null: one component at the 0.5% boundary while the others exceed it. Verify paired resampling, interval calibration, intended conjunction power and rejection when QoS fails. Test the actual five-seed design explicitly.
   **Exposes:** pseudoreplication, wrong ratio aggregation, miscalibrated bootstrap tails, inflated success rates and inadequate power. Under the stated one-sided EE rule, the nominal constituent level is 2.5%; assess simulation uncertainty rather than demanding an exact empirical percentage. **[Amendment item 3; CD Decisions items 3,5; Review, Pass 3 “Evaluation/statistics.”]**

`VERDICT: CONTRACT=REVISE:information-and-budget matching, learner schema, score identity, arm mapping, power, operational manifest | C3_IDENTIFIABLE=NO:local rows omit joint context and source marginal alone does not isolate coordination | POWERED=NO:specify alternative and crossed variance, then increase independent seeds/dates | LEARNER_FORM=set-conditioned scalar interaction head with anchored zero empty/singleton residuals`
