**Verdict:** defensible as a bounded development kill screen, with qualified claims. The supplied version is still **DRAFT/UNSEALED**, not a completed preregistration (`01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §8; `02-CONTROLLER-REVIEW.md`, opening status).

1. **DEPLOYABILITY**

“Uses decision-time information” is defensible; unqualified “deployable” is premature. Excluding realised fading prevents that particular oracle leak, but sharing the simulator’s structural equations and exact calibration still grants **model privilege**. These are separate issues (`01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §§2–3).

The paper must state that evaluation assumes a centralized controller with timely geometry and committed-state telemetry, correctly calibrated channel/interference/power models, and atomic configuration execution. Describe it as a **nominal model-based coordinator evaluated under matched simulator physics**. Neither real-system prediction accuracy nor computational deployability has been demonstrated.

A cheap, non-decisional diagnostic should cross:

* Unilateral-only versus joint-move catalogs.
* Original nominal physics versus one predeclared degraded channel/power estimator, with fixed error magnitudes, correlation structure and seeds.

Keep estimation errors consistent across candidates involving the same physical link. This separates dependence on model fidelity from the additional benefit of joint moves. Matched-anchor evaluation is cheap but cannot establish closed-loop robustness.

This distinction matters: S0-U already achieves **+1.523%**, compared with S0’s **+1.813%** (`04-S0-PROBE-RESULT.md`, opening results table). Much of the observed benefit requires no evacuation. A learned S3 predictor would be a separate learner experiment; simulator-trained S3 would not automatically remove model privilege.

2. **CLOSED-LOOP VALIDITY**

State drift is a **treatment-mediated effect**, not a confound to eliminate. Maintaining each arm’s trajectory correctly tests the consequences of intervention (`01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §4; Addendum A, §B).

Remaining threats are initialization dependence, limited horizon, and imperfect exogenous matching. Equal seeds alone are insufficient if action-dependent execution consumes mobility/environment RNG streams differently. Verify physical-time/entity keying and evaluator purity. Different channels encountered because policies select different links are legitimate treatment consequences. There are **four world clusters**, not twelve independent worlds or 36,000 independent observations.

The kill rule is appropriate as an **operational progression criterion**, not statistical proof or universal falsification. Arbitrarily small positive EE passes; the service allowance permits 36 fewer served user-steps and does not establish fairness. Report effect magnitude, all world-level differences, and cumulative trajectories without adding retrospective gates (§5).

The biggest downstream weakness is explicit: `03-FULL2-CONFIRMATORY-PLAN-DRAFT.md`, §3, reduces the horizon from **30 to 10 steps**. More short episodes cannot confirm 30-step persistence. Retain 30 before freezing, or clearly identify confirmation as addressing a different, shorter-horizon estimand.

3. **η_ref**

It is transparent historical calibration, not inherently a hidden tuning knob. Nevertheless, freezing a number does not guarantee objective alignment (`01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §3; `03-FULL2-CONFIRMATORY-PLAN-DRAFT.md`, §2).

For realised trajectory totals,

$$
\eta_C>\eta_B
\iff
\Delta B-\eta_B\Delta E>0.
$$

The coordinator instead prices energy at the **old E1** value, using immediate nominal outcomes. If FULL2 has higher EE, an increment can clear the old price while reducing FULL2’s ratio. Furthermore, local improvements relative to proposals on C3-S’s own trajectory do not guarantee improvement over the separate BASE trajectory.

**Require a predeclared sensitivity report**, for example at \(0.8,1.0,1.2\) times the frozen reference. Fix diagnostic coverage, seeds, outputs and reporting obligations before outcomes; report every value. None may replace the primary reference, alter progression, or rescue failure. Cached-candidate rescoring establishes choice stability only; claims about closed-loop EE sensitivity require diagnostic rollouts.

4. **COST AND PROGRESSION**

The existing phase timings and mean/median/p95/max requirements are sensible (`01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §6; Addendum A, §§B–D). Add hardware, thread allocation, cache conditions, unique configuration counts, and latency relative to the **30.08-second control interval**. Explicitly state whether controller computation energy and execution delay are excluded from reported network EE.

Approximately 100 seconds per decision exceeds that interval by **3.3×**. Parallelizing independent episodes improves experiment throughput; it does not reduce a single controller’s decision latency. Lite’s estimated ten seconds remains unmeasured.

Addendum A §C is **outcome-dependent qualification, but not post-hoc rule selection**, provided it is sealed before outcomes. Both pass → lite; one passes → that arm; neither passes → stop is auditable. Report both attempts, including failures, and acknowledge two opportunities to qualify against a shared BASE. “Non-decisional” should describe direct full-versus-lite rankings, not their eligibility outcomes. Fresh FULL2 confirmation remains necessary; never select the larger gain or change selection after seeing latency.

5. **FRAMING**

Calling it the third Catfish is honest only as an explicitly disclosed architectural redefinition. The three contrasts establish staged contributions; they do **not** establish C1/C2’s positive marginal within the final coordinated system (`01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §7).

The paper should carry these two sentences:

> “C1 and C2 remain training-time Catfish mechanisms producing two learned per-user heads, while C3-S is a newly defined deployment-time model-based set-level coordinator, with no third learned Q-head.”

> “The tested additive C3 target/composition showed no positive oracle-level marginal in G0–G3; any claim of three positive contributions requires successful FULL2-versus-DROP_C1, FULL2-versus-DROP_C2, and FULL2+C3-S-versus-FULL2 comparisons, and does not establish each component’s positive marginal within the final coordinated system.”

The closure is target/composition-specific, not an impossibility theorem for every additive encoding (`05-ORACLE-MARGINALS-RESULT.md`, sections “G0”–“G3”; `01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §1).

6. **MOST LIKELY NO_SUPPORT MECHANISM**

My leading hypothesis is **myopic reconfiguration eroding the small immediate benefit through accumulated tracking/handover costs and changed occupancy or downstream proposals**. S0 already obtained realised gains with the nominal selector; repeated policy-induced state evolution is the major newly tested mechanism (`04-S0-PROBE-RESULT.md`, opening table and “Information-gap diagnostic”; `01-C3S-CONTRACT-WITH-ADDENDUM-A.md`, §4).

First inspect the failure code, then cumulative bits, joules and service alongside action reversals and tracking events. Compare nominal and realised selected-minus-BASE residuals **at the same C3-S state**, using isolated descriptive replay if necessary. Immediate realised losses implicate model ranking error; immediate gains followed by cumulative deterioration implicate deferred costs. Such diagnosis must not become outcome-driven retuning or a rescue rerun (§8).
