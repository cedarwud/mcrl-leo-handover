The minimal design **partly matches the plan**. The amended power model supplies the required angle and load mechanisms. The larger gaps concern what C3 knows, whether component ablations measure distinct contributions, and whether the realised service and statistical endpoints support the claim.

Pass 1 was fixed before opening project files. I subsequently read all requested documents and verified that the four declaration hashes match their sidecars. I did not inspect the implementation or run its tests. **VERIFIED** below means directly verified arithmetic or documentary content; implementation findings from the supplied audit remain attributed findings. **INFERRED** means my deduction; **UNKNOWN** means the supplied evidence does not establish it.

Pass 1 derives the following system from the research question.

**(a) Minimal physics: association must change a conserved resource or an electrical cost.**

Let \(a_u\) identify a satellite and physical beam chain. For satellite position \(s\), user position \(x_u\), and earth-fixed beam centre \(c_b\),

\[
\theta_{bu}=\cos^{-1}\frac{(x_u-s)\cdot(c_b-s)}
 {|x_u-s|\,|c_b-s|},\qquad
g_{bu}=G_T(\theta_{bu})G_R\left(\frac{\lambda_c}{4\pi d_{bu}}\right)^2/L.
\]

Off-axis angle and elevation are different quantities. Elevation affects range, visibility and possibly atmospheric loss; beam-relative angle affects transmit gain. A non-flat, physically declared antenna pattern is sufficient for the mechanism. Operational antenna validation is a further requirement; the ITU reference itself identifies limitations in modelling spacecraft patterns. [ITU-R S.1528](https://www.itu.int/rec/R-REC-S.1528-0-200106-I/en)

Choose one resource allocator. Under equal-airtime TDM, \(n_b\) users share full bandwidth \(W\), so a per-user average target \(r_u\) requires instantaneous spectral efficiency \(n_br_u/W\). A minimal continuous-rate model gives

\[
\gamma_u=\Gamma_{\rm gap}(2^{n_br_u/W}-1),\qquad
p_u=\min\left[p_{\max},\frac{\gamma_u(N_0W+I_u)}{g_{a_u,u}}\right].
\]

An ACM staircase can replace this expression, provided its rate and SINR conventions are consistent.

For simultaneous transmissions, \(I_u=\sum_{v\ne u}\omega_{vu}g_{a_v,u}p_v\), where \(\omega\) represents actual resource overlap. Without caps, \(p=u+Fp\), giving \(p=(I-F)^{-1}u\) when the spectral radius of \(F\) is below one. Solve caps **inside** the coupled system. A capped fixed-point residual certifies the power solution, not successful service.

Use the same transmitted powers for wanted signals, interference and electrical consumption:

\[
E=\int\left[P_{\rm platform}+
 \sum_b\{z_bP_{\rm active}+(1-z_b)P_{\rm sleep}+f_{\rm PA}(p_b)\}\right]dt
 +E_{\rm switching}.
\]

The minimal PA model is \(f_{\rm PA}(p)=p/\eta\). A nonlinear curve is permissible, but changes the balancing argument. Charge physical devices once; integrate TDM PA draw over actual slots.

A minimal service rule holds offered traffic and user requirements fixed across arms. Delivered bits are achieved, decodable, useful bits after interruptions. With finite demand, \(B_{ut}=\min(Q_{ut},C_{ut})\), with queue conservation. Full-buffer traffic is also legitimate, but then the claim concerns saturated throughput and needs explicit per-user service constraints. Queueing and deadline machinery are necessary only if those services are claimed.

Failed transmissions still consume energy and cause interference. At an infeasible target, a frozen fallback must determine partial delivery, outage and any scheduling response.

Two numerical checks:

- With \(r=W=10^6\), \(\Gamma_{\rm gap}=1\), noise \(4\times10^{-14}\) W and gain \(10^{-12}\), required RF is \(0.04\) W. A 3.01 dB gain loss doubles RF to \(0.08\) W. With \(\eta=0.4\) and \(0.05\) W overhead, EE falls from **6.67 to 4.00 Mbit/J** at unchanged service.
- Two coupled links satisfying \(p_1=0.1+0.4p_2\), \(p_2=0.1+0.4p_1\) require **0.1667 W each**, versus 0.1 W without interference. Ignoring coupling understates total RF by 40%.

Neither load-dependent power nor interference alone guarantees all three components will help. That is an empirical hypothesis, not a simulator acceptance condition.

**(b) Balancing versus consolidation is an electrical-cost inequality.**

For identical links, equal demands and continuous rates, define \(A=N_0W/g\). A beam serving \(n\) users needs average RF

\[
P_{\rm RF}(n)=A(2^{nr/W}-1).
\]

With a linear PA, this convex load cost favours balancing. Activating additional chains or satellites favours consolidation. Moving from one active beam to two raises EE at matched delivered bits precisely when

\[
\text{PA energy saved}>
\text{additional activation, interference and switching energy}.
\]

For unequal delivered bits, the exact condition is

\[
\rho_{\rm new}>\rho_{\rm old}
\iff \Delta B>\rho_{\rm old}\Delta E,\qquad \rho=B/E.
\]

Numerical checks, using \(A=0.04\) W and \(r/W=1\):

- Two users consolidated require \(0.12\) W RF; splitting them requires \(0.08\) W. With \(\eta=0.4\) and activation cost \(0.03\) W per beam, electrical powers are **0.33 versus 0.26 W**: balancing raises EE by **26.9%**.
- With activation cost \(0.20\) W, powers become **0.50 versus 0.60 W**: consolidation raises EE by **20%**. The crossover is \(0.10\) W.

These results require matched bits. Channel asymmetry, discrete ACM modes, unequal demands, caps, interference and nonlinear PA behaviour can reverse them. At low spectral efficiency, the continuous RF cost becomes nearly linear and balancing headroom shrinks.

**(c) “Component X raises EE” needs an intervention and a population.**

For arm \(a\), world \(W\), and training randomness \(S\), define

\[
\rho_a=\frac{\mathbb E_{W,S}[B_a]}{\mathbb E_{W,S}[E_a]},\qquad
\Delta_x=\frac{\rho_{\rm FULL}}{\rho_{-x}}-1.
\]

The conditional claim is \(\Delta_x>0\) with the other two components enabled, and service non-inferiority against that same comparator. It is not an average main effect across every component combination.

The smallest policy experiment has **four arms**: FULL, DROP_C1, DROP_C2, DROP_C3.

Two interventions must be distinguished:

- **Retrained ablation:** train each arm under the same budget, selection procedure, common primitive information and fixed component definitions. This estimates the contribution of including the component in the learning system.
- **Checkpoint knockout:** disable one contribution in the trained FULL policy. This estimates reliance on that contribution at deployment.

I would use retrained ablations for the scientific algorithm claim and describe knockouts separately. Neither intervention substitutes automatically for the other.

All arms need the same physics, action space, catalogue construction rule, service guard, decision deadline and endpoint evaluator. Remove the selected component from the actual selector. Prevent its explicit target or score from remaining through a hidden evaluator. Shared physical inputs may remain; their presence limits claims that a particular representation is indispensable.

Evaluate complete, arm-specific trajectories. Pair exogenous geometry, mobility, traffic and fading using event-keyed randomness. Recompute \(\sum B/\sum E\) from raw endpoints in each bootstrap draw. Nominal target gains and oracle improvements are mechanism diagnostics.

A world is an independent exogenous scenario, not a user, decision or forecast offset. Repeated dates and reused trained models introduce additional dependence. For crossed date and training-seed effects,

\[
\operatorname{Var}(\widehat\Delta)\approx
 \sigma_{\rm date}^2/D+\sigma_{\rm seed}^2/S+\sigma_{\rm residual}^2/(DS).
\]

More test worlds cannot eliminate uncertainty from too few trained models.

There is no defensible universal “typical variance.” For planning, assume paired, cluster-level relative-effect SD of **3%, 5% or 10%**. These are sensitivity assumptions, not measurements. For unequal endpoint weights, estimate the SD from the pooled-ratio influence function, rather than substituting the variance of per-world ratios.

A conservative design supporting three separately reportable positive claims uses one-sided \(\alpha=0.05/3\). For 80% power per contrast,

\[
n\approx
\left[\frac{(2.128+0.842)\sigma}{\log(1+\Delta)}\right]^2.
\]

| Paired cluster SD | Detect 1% | Detect 2% | Detect 3% |
|---|---:|---:|---:|
| 3% | 81 | 21 | 10 |
| 5% | 223 | 57 | 26 |
| 10% | 891 | 225 | 101 |

These are normal-approximation planning counts; very small counts need finite-sample correction. They provide 80% power **per contrast**, not necessarily 80% probability that all three pass. The paired-power formulation is standard; the variance assumptions above are mine. [Statsmodels power documentation](https://www.statsmodels.org/dev/generated/statsmodels.stats.power.TTestPower.solve_power.html)

Thus roughly ten unusually stable clusters might detect a 3% effect; a 1% claim generally needs tens to hundreds, potentially more. If training-seed effect SD alone is 1%, approximately nine independent training seeds are needed under this approximation for a 1% contrast, even with unlimited evaluation worlds; at 2% SD, approximately 36.

A second sanity check shows why pooling matters. Arm A has \((B,E)=(9,1),(9,9)\); arm B has \((3,1),(18,9)\). Mean interval EE ranks A above B, **5 versus 2.5**. Pooled EE ranks B above A, **2.1 versus 1.8**.

**(d) C3 needs joint-action information or reasoning, not another unilateral score.**

Let \(F(a)=B(a)-\lambda E(a)\), with a common, training-calibrated \(\lambda\). Relative to reference configuration \(a^0\), define exact unilateral increments

\[
d_i=F(a_i,a^0_{-i})-F(a^0).
\]

For changed-user set \(A\), the immediate interaction residual is

\[
\Psi_A=F(a_A,a^0_{-A})-F(a^0)-\sum_{i\in A}d_i.
\]

C1 can contain \(d_i\); C3 can contain \(\Psi_A\). C2 supplies an explicitly defined continuation value that excludes the immediate term. If future joint interactions are also modelled, allocate them once.

A deployable coordinator needs enough information to estimate joint effects: candidate identities, demands/load, shared capacity and interference, activation state, and other users’ proposed or conditional actions—or a joint search that constructs those actions. Forecasts must derive from information available before the decision.

**No new sensor is inherently necessary.** Joint reasoning over the same global physical state can have value beyond exact unilateral evaluation. However, a scalar unilateral value alone does not identify joint interactions.

Two hand-checkable payoff tables, listing \(F_{00},F_{10},F_{01},F_{11}\):

- \((0,1,1,-2)\): individually attractive moves collide; \(\Psi=-4\). Coordination prevents a harmful simultaneous choice.
- \((0,-1,-1,2)\): neither unilateral move helps, but the joint move gains 2; \(\Psi=4\). Even iterated improving unilateral moves remain stuck.

In an additive world, \(\Psi=0\). A correct C3 should have zero value there. If an existing deployable evaluator already optimises the same joint objective over the same catalogue, C3 cannot claim additional exact optimisation value; any benefit must come from prediction, approximation, information or computation.

**(e) Five likely false-result mechanisms follow directly.**

1. **Incorrect causal physics or electrical boundary.** Angle changes a reported feature but not executed power; association resets a power anchor; PA draw is evaluated after inappropriate averaging; inactive devices disappear from accounting. These can manufacture gains or erase real ones.
2. **Service or ratio substitution.** Decodability replaces adequate throughput; difficult users disappear from denominators; interval ratios replace pooled EE. Losing 0.5% of bits while saving 2% of energy raises EE by **1.53%**, so a permissive service margin can account for the entire claimed effect.
3. **Non-identifiable or mismatched components.** Additive heads can exchange value without changing their sum. C3 may duplicate C1, while DROP_C3 may also lose joint search. The first can produce a false negative; the second a false attribution.
4. **Unavailable information or wrong rollout distribution.** An oracle sees realised fading or other users’ future actions; the learner sees lagged summaries. Fixed-carrier probes measure local effects at carrier states, while deployed policies visit different states and create future consequences.
5. **Selection and dependence mistakes.** Choose the favourable model, seed, checkpoint or service threshold; treat users or date–seed cells as independent; stop after noisy positive probes. For illustration, 31 independent null tests at 5% have a **79.6%** chance of at least one positive. Actual correlated settings require their own analysis.

Pass 2 compares that derivation with the sealed documents.

**The physical core substantially matches; the complete experiment does not yet.**

**VERIFIED:** v1.1 introduces \(r^*=50\) Mbit/s and \(\Gamma_r(n_b)\), explicitly connecting occupancy to required power. Angle enters through nominal channel gain. Capped failures retain partial delivery, radiation and energy. Those are the essential mechanisms. [v1.1, items 1–2](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:6)

**VERIFIED documentary evidence:** the audit reports substantial independent checks of power solving, bandwidth accounting, PA integration and endpoint arithmetic. It also reports invalid factor-arm selection, missing interruption wiring, incorrect interference identity and an unusable real-world catalogue. The controller prescribes repairs; this is evidence of identified requirements, not evidence that those repairs passed. [Engine audit](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-ENGINE-STAGE2-AUDIT-CLAUDE-OPUS-2026-09-08.md:11), [controller resolutions](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-ENGINE-AUDIT-2026-09-08.md:3)

**(i) Complexity the minimal design does not require.**

“Bomb surface” below estimates additional producer–consumer contracts whose disagreement could change a result. Counts overlap and are engineering estimates, not measured call-graph counts. Oracle status reflects the supplied audit.

| Optional element | Added interfaces, approximately | Independent oracle? | Minimal treatment |
|---|---:|---|---|
| Four extra architecture families beyond rate-TPC/TDM | 8–12 | Partial: power/resource fixtures; incomplete end-to-end channel evidence | One primary architecture |
| Separate S/H/SH factorial across five architectures | 5–8 | Partial; interruption path was disconnected | Declare one physical energy/service model; retain targeted fixtures |
| Five legacy snapshot T settings | 2–3 | Yes for elementary integration; not general convergence | Numerical-error test, not scientific arm |
| Six U-cap/U-margin settings | 3–4 | Partial analytic rate checks | Optional mechanism appendix |
| Twelve-arm probe system, including multiple oracle and control selectors | 6–9 | Tiny-world exhaustive oracle only | Four scientific arms; comparators in fixtures |
| Three carriers, repeated anchors, admission probes, screens and later ladders | 6–10 | No independent oracle for transport to deployed trajectories | Structural checks, training/validation, one confirmation |
| Φ pricing, κ conversions and per-user interaction allocation | 4–6 | Core arithmetic partly checked; magnitude/units unresolved | Common bit units; separate QoS constraints; scalar set interaction |
| Legacy-specific D2/N=4 semantics and compatibility adapters | 4–6 | Legacy parity is not an independent physical oracle | Preserve only explicitly required operational rules |
| Multiple overlapping manifests, schema stamps and seals | 2–4 | Hash integrity checks bytes, not semantics | One transitive manifest plus exercised invariants |

This does **not** make interference, physical identity, a credible geometry provider, service accounting or reproducibility optional. Nor does it justify deleting tests merely because a sensitivity setting is removed.

**(ii) Necessary elements missing, ambiguous, or still expressed as future work.**

1. **An explicit energy boundary for “constellation EE.”** The audited model hard-excludes bus power and uses synthetic active/idle costs. It can support a declared payload-energy benchmark. A whole-constellation claim needs the omitted energy included or its effect bounded.  
   **INFERRED numerical consequence:** policies with \((B,E)=(100,1)\) and \((110,2)\) rank 100 versus 55 before a common 10 J baseline; afterwards they rank **9.09 versus 9.17**, reversing. Common overhead can change rankings when bits differ. [Audited energy definition](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-ENGINE-STAGE2-AUDIT-CLAUDE-OPUS-2026-09-08.md:173)

2. **Service quality that addresses throughput.** The plan deliberately uses full-buffer ACM delivery and PHY service; target attainment is separately reported. Numeric guards cover complete-service availability and handovers/Φ, but do not establish non-inferior per-user rate or target attainment. Reporting a metric is not guarding it. Add a predeclared rate/service-floor or lower-tail throughput constraint; queues are unnecessary unless delay or finite-demand delivery is claimed. [Service declaration](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md:14), [QoS margins](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md:10)

3. **An executable, non-overlapping set-score definition.** The latest correction removes unilateral externality from C3, which is right. But “C1(config) is a whole-network difference” remains ambiguous for multiple changes. If it means \(F(config)-F(base)\), interaction is already present. Require \(C1(A)=\sum_i d_i\) and \(C3(A)=\Psi_A\), or another explicit decomposition with a reconstruction identity. Apply the same discipline to future value.

4. **Correct interaction credit.** Equal sharing is not generally Shapley allocation. For \(v(S)=1\) iff users 1 and 2 belong to \(S\), user 3 is a dummy: Shapley values are **(½,½,0)**, not **(⅓,⅓,⅓)**. Equal sharing is valid for a symmetric pure set interaction, not an arbitrary residual containing lower-order interactions. A scalar set-level C3 avoids unnecessary credit-allocation machinery. [Declared allocation](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md:9)

5. **A complete learner-information and training contract.** Specify each head’s inputs, target, normalization, training intervention and deployed decision path. The pipeline explicitly leaves the coordinator-information gap open and permits C3 to become an exact evaluator. That could be a useful system, but its result would not establish the value of a learned coordination component. [Pipeline, stages 6–7](/home/sat/mcrl-v023-codex-audits/END-TO-END-PIPELINE-MAP-2026-09-08.md:46)

6. **C2 units and temporal accounting.** If \(\kappa=B/(UT)\) with \(T\) in seconds, it is throughput per user. Losing a 30.08 s offset costs \(\kappa\times30.08\) bits under that interpretation, not \(\kappa\) bits. Alternatively declare another scale explicitly. Also specify whether C2 is directly supervised finite-horizon value or a bootstrapped reward: overlapping forecasts must not repeatedly count the same future benefit. The audit identifies the scale problem. [Audit M1–M2](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-ENGINE-STAGE2-AUDIT-CLAUDE-OPUS-2026-09-08.md:102)

7. **One coherent bootstrap action.** The proposed common-action correction is necessary. With \(Q_1=(10,0)\), \(Q_2=(0,10)\), separate maxima produce **20**, although the best executable summed action is worth **10**. A passing arithmetic helper is insufficient; the training update must exercise this case.

8. **Independent composed geometry and numerical accuracy.** Testing gain, path loss and receive pattern separately does not verify their composition. Test beam-specific cross gains and actual earth-fixed geometry. The declared within-step user freeze omits about **250.7 m** of motion; its small size relative to a cell does not bound errors near eligibility or ACM thresholds. [Provider decisions](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-PROVIDER-2026-09-08.md:5)

9. **Convergence evidence at the claimed effect scale.** Forty-seven subintervals define a grid, not an accuracy guarantee. Misplacing a service transition by half a 0.640 s interval changes that user-step’s availability by **1.06 percentage points**. Refine time and threshold crossings until component contrasts change by materially less than 1%.

10. **An untouched confirmation population and correct dependence model.** TRAIN-only is appropriate for probes, but is not itself a holdout protocol. Separate training, calibration, model selection and confirmation by authenticated memberships. The documents do not establish independence of Cartesian date × training-seed cells. [Evaluation map](/home/sat/mcrl-v023-codex-audits/END-TO-END-PIPELINE-MAP-2026-09-08.md:60)

**An additional model consequence deserves explicit testing.**

The plan uses \(f_{\rm PA}(p)=\sqrt{pp_{\rm sat}}/0.35\), not a constant-efficiency PA. Consequently, RF-balancing intuition cannot be transferred directly.

For continuous rates and identical links, putting two users together rather than on separate beams gives

\[
\frac{P_{\rm PA,consolidated}}{P_{\rm PA,split}}
 =\frac{\sqrt{2^{r/W}+1}}2.
\]

At \(r/W=1\), consolidation uses **50% more RF but 13.4% less PA electrical power**, before activation savings.

Using the plan’s low-load thresholds, if one-user RF is 0.10 W, two-user RF is approximately 0.1604 W. The declared PA and overheads give approximately **3.15 W consolidated versus 5.00 W split on the same satellite**. This is a power check, not an EE conclusion: full-buffer ACM bits can differ.

The ACM floor also matters. Its QPSK 1/4 efficiency, after the declared roll-off correction, gives approximately **68.1 Mbit/s** for one user, above the synthetic 50 Mbit/s target. The official table supports the efficiency; it does not validate the benchmark demand or hardware costs. [ETSI EN 302 307-1, Table 13](https://www.etsi.org/deliver/etsi_en/302300_302399/30230701/01.04.01_60/en_30230701v010401p.pdf)

**(iii) Estimand differences.**

| Plan quantity or procedure | Relation to the first-principles claim |
|---|---|
| Pooled FULL−DROP with the other components enabled | Correct conditional background |
| Realised endpoint after nominal-score selection | Correct separation, once actually wired |
| Oracle targets on fixed carrier anchors | Local mechanism/headroom estimand; not learned closed-loop policy value |
| C3 as exact set evaluator | Information/computation contribution; not necessarily learned-component contribution |
| Historical DROP_C3 also losing joint search | Confounded; latest controller correction appropriately separates it |
| Full-buffer PHY availability | Narrower service claim than adequate per-user delivery |
| Bus-excluded denominator | Payload benchmark, unless whole-constellation equivalence is demonstrated |
| Positive oracle/S0 admission gates | Selection procedure; neither a general impossibility proof nor confirmation |
| Bounded-catalogue optimum | Ceiling within that catalogue only; not a global physical optimum |
| \(\delta=0.5\), labelled “pp” | Audit says it means **0.5% relative EE improvement** |

The amended intersection–union claim is a valid simplification relative to my conservative Pass-1 separate-claims design: for the single assertion that **all three** gains exceed their margins, each constituent test can use level 5% without Bonferroni correction. Separate component discoveries or searching settings require additional care. [v1.2 uncertainty and claim](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.2-AMENDMENT-2026-09-08.md:8)

The positive margin substantially increases sample requirements. Assuming 5% paired cluster SD, 80% power per contrast and the lower endpoint of a two-sided 95% interval, detecting true gains of **1%, 2%, 3% above a 0.5% threshold** requires approximately **797, 90, 33 independent clusters**, respectively, before training-seed uncertainty.

Four probe worlds therefore support fixture-like mechanism exploration, not the advertised precision. Approximately 600 worlds over 161 dates and five reused trained models do not automatically yield 805 independent clusters.

**(iv) Smallest pre-outcome matrix: one physics setting × four policy arms.**

Keep one versioned rate-TPC/TDM primary derived from `a-r0`, with the mandatory energy, service and target contracts resolved before outcomes. Sample a prespecified world distribution containing low/high occupancy, overlap, mobility and joint-decision opportunities. These are world strata, not additional physics settings.

The sealed enumeration is correctly **25 + 6 = 31**. [v1.3 erratum](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.3-ERRATUM-2026-09-08.md:6)

| Cut from the 31-setting matrix | Settings removed | Claim or diagnosis lost |
|---|---:|---|
| All `a′-r` settings | 5 | Robustness to FDM scheduling |
| All `a-γ` settings | 5 | Isolation of rate-target versus constant-SINR power control |
| All `b` settings | 5 | Fixed-RF/ACM architecture comparison |
| All `a′-γ` settings | 5 | Combined FDM/constant-SINR comparison |
| Three `U-cap` settings | 3 | Contribution of the spectral-efficiency cap |
| Three `U-margin` settings | 3 | Contribution of the declared margin |
| `a-rT` | 1 | Legacy snapshot bias as an experimental result; retain convergence tests |
| `a-rS` | 1 | Standby-cost robustness |
| `a-rH` | 1 | Blackout-duration robustness |
| `a-rSH` | 1 | Joint standby/blackout robustness |
| **Total removed** | **30** | Broad regime-map claims |

The remaining four arms answer the conditional component question under one declared system model. They do not establish generality across power architectures or hardware assumptions.

Off-axis power fixtures, additive-world C3 placebos, joint-move witnesses and an exact unilateral comparator remain necessary checks; they do not each require a powered physics setting.

The original v1.0 additionally requires both architectures to appear beside each other. If that historical requirement remains binding, the minimum becomes **two physics settings**. Under the two hard requirements in this prompt, it is **one**. This is a proposed pre-outcome simplification, not an alteration of the seal.

Pass 3 locates the most likely remaining unknown defects.

The probabilities below are subjective engineering judgments that **at least one additional, result-changing defect remains after the already identified repairs are correctly implemented**. They are not measured frequencies, and categories overlap. Presently documented blockers do not need probabilistic speculation.

| Category | Probability and basis | Single cheapest exposing test | Result supporting a sound study |
|---|---|---|---|
| **Physics model** | **0.65 — INFERRED.** PA curvature, discrete rate transitions, zero-idle assumptions and quadrature can move a 1–3% effect. **VERIFIED:** the declared model contains these features. | One two-beam load/angle fixture, with independent power/PA arithmetic and time-grid refinement through an ACM transition. | Correct angle→RF→electrical-energy response; preserved service/energy accounting; refinement changes contrasts by **<0.1 percentage point**. |
| **Provider/geometry** | **0.80 — INFERRED.** Physical identity, beam boresight, coordinate/time conversion, reuse and eligibility meet here. **UNKNOWN:** completed provider parity and independent geometry results. | One oblique, moving two-satellite/two-beam golden world, computed independently and repeated after satellite/slot relabelling. | Direct/cross gains agree with independent geometry, relabelling changes no physical outcome, and 3/30/31-step constructions share their prescribed prefixes. |
| **Targets** | **0.80 — INFERRED.** Set-level C1/C3 overlap, κ units and future-value counting remain plausible defects. **VERIFIED:** ambiguity and scale concerns exist in the documents. | Exhaustive three-user, two-action, three-step fixture containing a dummy user, a synergistic pair and a future outage. | Scores reconstruct the declared objective exactly; no duplicate interaction/future reward; dummy gets no claimed Shapley credit; each DROP has the hand-predicted endpoint. |
| **Learner/information** | **0.90 — INFERRED; highest.** The pipeline expressly leaves the deployable-information path open. **UNKNOWN:** whether training and execution implement it. | One tiny end-to-end training slice with paired states having identical unilateral values but opposite joint interaction signs; poison all post-decision observations. | Observable joint context distinguishes the states; the trained C3 selects the correct joint actions; poisoning future data changes no current action; additive placebo gives no C3 gain. |
| **Evaluation/statistics** | **0.80 — INFERRED.** Crossed clustering, four-world probes, service denominators and confirmation separation are unresolved. | Feed the actual merger synthetic date/seed-correlated raw B/E/QoS receipts with known nulls and injected 1–3% effects. | Correct pooled estimand, **≤5% false success** for the declared global claim, intended power, and failure when service violates its margin. For 1,000 null replicates, roughly **94–96%** coverage is a useful 95%-coverage check. |
| **Process** | **0.60 — INFERRED.** Hashes can authenticate disconnected producers and stale contracts. **VERIFIED:** the supplied audit found both dead producers and tautological tests. | One miniature provider→target→training→deployment→receipt run with deliberate corruption of a split membership or component mask. | The real execution path rejects corruption; every claimed producer is exercised; the final manifest binds transitive code/data dependencies; identical arms yield identical complete receipts. |

One proposed repair itself needs refinement: requiring **all 31 settings to produce distinct receipts** is not a semantic invariant. Different settings can legitimately coincide when the affected mechanism is inactive—or when rate and SINR targets coincide. Require targeted discriminators: interruption changes useful bits when it overlaps service; standby changes energy when a device sleeps; other intended equalities remain valid. [Proposed duplicate-setting test](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-ENGINE-AUDIT-2026-09-08.md:5)

I would regard the study as sound when those contracts hold through the executed learner, the confirmation population is untouched, and uncertainty matches the actual dependence structure. A sound result may be negative. Each component’s positive EE effect must survive that experiment; it cannot be required of the fixtures or obtained by retaining favourable regimes.

VERDICT: MINIMAL_DESIGN_MATCHES_PLAN=PARTIAL | REMOVE=30 optional physics settings, duplicate scoring, unnecessary credit allocation, redundant screening layers | ADD=energy/service boundary, executable target decomposition, deployable C3 information contract, closed-loop ablations, independent vertical slice, powered crossed-cluster confirmation | SMALLEST_MATRIX=1 settings | HIGHEST_RESIDUAL_RISK=learner/information, 0.90