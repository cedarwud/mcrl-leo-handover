Round 9B — Operational deployability of the set-level LEO coordinator

Review date: 9 September 2026. Scope: the six readable Markdown files in `multi-catfish-r9B-package-20260909.zip`, plus the primary sources cited below. Package measurements are supplied development evidence, not independently reproduced measurements or operational results. Recommendations and the proposed budget below are engineering judgments, not standards requirements.

**The defensible placement is a ground controller beside the gateway's gNB-CU-CP, integrated with the operator's NTN resource-control system. A 10 s solver allowance is plausible for advance supervisory planning; the supplied implementation has not demonstrated that allowance, and Rel-17/18 handover does not supply atomic multi-user execution.**

For package citations, **Contract** means `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`; **Approximations** means `V025-CONTROLLER-DECISIONS-SELECTION-TIME-APPROXIMATIONS-2026-09-08.md`; **4D gate** means `V025-CONTROLLER-DECISIONS-4D-GATE-2026-09-09.md`; **Amendment** means `V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md`; **Smoke** means `VERTICAL-SLICE-SMOKE-2026-09-08.md`. The sixth file is `01-QA-PROMPT.md`. Referenced v1.5 and stage-C specification files are not included; I do not treat their contents as inspected.

**1. Placement and the actual information contract**

I would put the optimizer in the ground RAN/NTN control domain, close to the CU-CP and gateway resource manager, with one authority over the affected cells and payload resources. The core can supply policy and participate in mobility procedures, but is an awkward owner of detailed association and PA decisions. A transparent satellite has no onboard RRC decision endpoint. A regenerative implementation is a separate architecture requiring an explicit onboard functional split, compute qualification and resource-control interface.

This placement follows two useful boundaries. TS 38.401 §8.2.1.1 assigns the CU a central role in measurement handling and inter-DU mobility execution. TS 38.300 Annex B.4, which is informative, describes the NTN control function and explicitly leaves its control-data provision to the gNB outside 3GPP scope. It does not standardize this optimizer or a payload-control API. [TS 38.401 v18.3.0](https://www.etsi.org/deliver/etsi_ts/138400_138499/138401/18.03.00_60/ts_138401v180300p.pdf); [TS 38.300 v18.8.0, Annex B.4](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/18.08.00_60/ts_138300v180800p.pdf).

In O-RAN terms, the 30 s planner fits a **Non-RT RIC/rApp**, paired with a faster CU-CP executor or capable xApp. Near-RT control is normally 10 ms–1 s. A1 supplies policies/enrichment and related services; it is not a multi-UE profile-commit API. Hosting software in an xApp container would not make a blocking 10 s operation a near-RT control loop. E2 access depends on the node's exposed capabilities. [O-RAN Architecture, ETSI TS 103 982 v8.0.0, §§6.2, 6.3.1.2.3, 6.4.2–5](https://www.etsi.org/deliver/etsi_ts/103900_103999/103982/08.00.00_60/ts_103982v080000p.pdf); [E2 General Aspects, ETSI TS 104 038 v4.1.0, §5.1.1](https://www.etsi.org/deliver/etsi_ts/104000_104099/104038/04.01.00_60/ts_104038v040100p.pdf).

The following is the information boundary I would require for Contract §A2 and the capability manifest in §F3:

| Input | Realistic availability | Standardized boundary and remaining integration |
|---|---|---|
| Ephemeris, gateway location, service windows | Operator orbit products can reach the ground controller; retain epoch, issue/receipt time, validity and uncertainty. | TS 38.300 §§16.14.7 and 16.14.3.1 address O&M provision and SIB19 assistance. The operator-to-gNB control feed is outside scope. |
| User positions | Terminal inventory or an explicitly provisioned positioning/telemetry service; mobile users require updates and uncertainty. | UE possession of GNSS does not give the controller exact coordinates. TS 38.300 §16.14.8 supports requested coarse location, approximately 2 km, if available and after AS security. |
| Load and demand | Local scheduler/bearer counters and queues; neighbour reports where admitted. | XnAP has cell/SSB-area load and capacity reporting. A full per-user queue vector, future demand and its mapping onto satellite resources require additional integration. |
| Interference and cross gains | Serving/neighbour measurements plus calibrated antenna, pointing, propagation and resource-use models. | SS/CSI-RS measurements are standardized. The all-user/all-beam gain matrix and interference under an unexecuted profile are predictions, not measurements. |
| Activation and PA energy | Readback from the actual resource/payload controller; calibrated power-efficiency, switching and thermal models. | XnAP supports cell/SSB activation and an Energy Cost index. Neither is a per-beam RF-chain joule meter or a counterfactual PA-energy evaluator. |
| Neighbour proposals | Available inside the same controller or through an agreed operator API, with version and reservation status. | Mobility negotiation and handover preparation exist; the algorithm's complete simultaneous proposal vector is not a generic standardized exchange. |

The standardized elements in this table are supported by [TS 38.300 v18.8.0, §§16.14.3.1, 16.14.7–8 and Annex B.4](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/18.08.00_60/ts_138300v180800p.pdf), [TS 38.423 v18.3.0, §§8.4.3, 8.4.9–14](https://www.etsi.org/deliver/etsi_ts/138400_138499/138423/18.03.00_60/ts_138423v180300p.pdf), and [TS 38.215 v18.2.0, §§5.1.1–6](https://www.etsi.org/deliver/etsi_ts/138200_138299/138215/18.02.00_60/ts_138215v180200p.pdf). XnAP's Energy Cost is a node-level measured index, 0–10000, in DATA COLLECTION UPDATE; it does not encode the package's physical energy function.

**Unavailable as facts at decision time:** future realized fading, future arrivals and other controllers' unannounced decisions. Their distributions can be estimated. Exact outcome values for every counterfactual profile remain a simulator/model capability even when all its inputs could be acquired operationally. Missing neighbour results must remain unknown, rather than becoming zero interference or spare capacity.

There is also a concrete protocol-mapping issue in this package. Smoke's ACM table includes 8PSK and 16/32APSK. NR PDSCH uses its own MCS tables, transport-block and CSI procedures. A satellite spot beam, NR cell, SSB beam and PA chain also need an explicit mapping. Thus this is presently a satellite resource-control model with a possible NTN control-plane mapping; an NR conformance claim would require adapting and validating that mapping. [TS 38.214 v18.4.0, §§5.1.3.1 and 5.2](https://www.etsi.org/deliver/etsi_ts/138200_138299/138214/18.04.00_60/ts_138214v180400p.pdf).

**2. Timing: plausible allocation, unproven compliance**

There is no universal 3GPP budget allocating 30 seconds among sensing, optimization and handover. The deciding constraint is the **remaining safe service/overlap horizon**, together with data age and execution latency. Ten seconds can be acceptable when computing an advance plan for sufficiently persistent associations. It cannot be the only response to an imminent serving-link loss.

An illustrative commissioning budget for a bounded cohort under one ground control domain is below. These are proposed allocation caps, not measured operator values. Measurements arrive continuously; the first row describes the aggregation/freshness allowance, not a requirement to stop serving traffic and wait for sensing.

| Activity | Allocation | What must fit |
|---|---:|---|
| Measurement refresh and aggregation | 3.00 s | A timestamped snapshot with explicit age limits and missing-data status |
| Telemetry transport and ingestion | 0.50 s | Ground transport, queues and serialization; include satellite paths where applicable |
| State assembly and baseline preparation | 0.50 s | Construct, jointly validate and repair the baseline before the solver starts |
| Coordinator computation | 10.00 s | Catalogue, immediate/continuation scoring, reduction and selection validation |
| Final freshness check and resource preparation | 1.00 s | Detect state changes; confirm target capacity, reservations and transition legality |
| Command/configuration delivery | 2.00 s | Prepare affected nodes and deliver UE configurations while source service continues where feasible |
| Execution and completion observation | 2.00 s | A bounded execution window with per-UE completion and payload-state readback |
| Residual guard | 11.08 s | Timing uncertainty, bounded recovery, or waiting for the planned activation boundary |
| Total planning envelope | **30.08 s** | Must be validated against the actual topology and cohort |

The guard is not permission to start an urgent handover late. Nor is the 2 s execution window an assumed 2 s blackout for every UE. If target preparation, UE signaling or payload warm-up cannot meet these caps, prepare earlier, reduce the cohort, or reject/defer the plan. Do not assume the full 30.08 s interval is available just because it is the simulator's cadence.

A useful deadline rule is

\[
D_{\rm solve}\leq\min\!\left(10\,\mathrm{s},\;t_{\rm last\ safe\ start}-t_{\rm now}-L_{\rm prepare+deliver}-m\right),
\]

where the last safe start already accounts for the execution window and service-loss risk. A nonpositive allowance invokes local mobility protection immediately. Keep the gNB's local mobility safeguards and already configured UE CHO active throughout optimization.

Standards constrain the design without choosing that budget:

- TS 38.331's `ReportInterval` offers 120, 240, 480, 640 ms; 1.024, 2.048, 5.120, 10.240, 20.480, 40.960 s; and 1, 6, 12, 30 min. There is no 30.08 s choice. Reporting intervals are not synchronized sampling guarantees; event filtering, time-to-trigger, measurement opportunities and transport affect age.
- CHO evaluates configured conditions at the UE. `TimeToTrigger` spans configured values up to 5.120 s. A time-based condition defines an execution window, not a multi-UE barrier. T304 is an execution/recovery timer; its 10 s option does not authorize 10 s of central optimization. [TS 38.331 v18.6.0, §§5.3.5.13, 5.5, 6.3.2 and 7.1.1](https://www.etsi.org/deliver/etsi_ts/138300_138399/138331/18.06.00_60/ts_138331v180600p.pdf).
- TR 38.821 v16.0.0 Table 4.2-2 gives reference **propagation-only RTTs** of 25.77/41.77 ms for transparent LEO at 600/1200 km. These exclude controller computation, queuing and procedure completion. §§7.3.2.1.1–2 identify mobility latency and stale measurements; §7.3.2.2.2 studies CHO triggers. A study report is not an operational timing SLA. [TR 38.821, ATIS primary publication](https://atisorg.s3.amazonaws.com/archive/3gpp-documents/Rel16/ATIS.3GPP.38.821.V1600.pdf).

Published timing evidence is useful only with its experimental boundary intact:

| Source | Actual evidence | What it cannot establish |
|---|---|---|
| *Accelerating Handover in Mobile Satellite Network*, §§IV, V-A/B | A Skyfield/UERANSIM/Open5GS software prototype reports 20.87 ms mean handover versus its 250 ms NTN baseline, and uses a 5 s prediction update period. | A live LEO control-plane deadline or runtime for this joint-physics optimizer. [Primary paper](https://arxiv.org/html/2403.11502v2). |
| Seeram et al., *Handover challenges in disaggregated open RAN for LEO Satellites*, §4.3, Table 3, §6.2.2 | Its simulation assumes 20 ms synchronization, 50 ms core and 1 ms/message. The studied moving-beam scenario has about 3 s between intra-satellite handovers and 15–20 s between inter-satellite handovers. | These are modeled delays and handover frequencies, respectively—not measured commercial budgets or 3–20 s handover execution times. [Primary analysis](https://www.frontiersin.org/journals/space-technologies/articles/10.3389/frspt.2025.1580005/full). |

I did not verify a published production measurement covering this exact measurement → approximately 1,000-profile optimization → validation → multi-UE execution chain. The literature therefore does not validate the proposed 10 s allowance.

The package itself gives a more precise runtime diagnosis than the prompt summary: **4D gate** reports **24.7 s for coordinator selection**, including 18.3 s continuation, and **34.4 s for a complete 14-arm experimental anchor**. Its §§1–5 prescribe four processes, then fewer continuation boundaries, then M = 64 → 48 if necessary. They do not contain a completed four-worker pass. The prompt's fast immediate-scoring figure is insufficient to establish full-path compliance.

Contract §F2 correctly includes externally enforced cancellation and timeout outcomes. Measure baseline preparation and online forecast/provider construction too, even if they sit outside the 10 s solver timer. Approximations §5's once-per-world tape reuse is benchmark amortization; it is not evidence of a free operational future-state feed. Record full-chain and stage p50/p95/p99, deadline-miss rate, cold-start behavior, worker contention and load/cohort scaling. A single-worker smoke measurement is not a latency distribution.

Finally, Contract §F1's information-at-t/application-from-t convention grants zero decision latency. An operational variant must score the expected state at its future execution window and charge service/energy accumulated under the old and intermediate configurations. Finishing a calculation before the next simulator tick does not remove this discrepancy.

**3. Atomic commitment: distinguish an atomic plan record from radio execution**

**Rel-17/18 does not provide a general all-or-nothing transaction across arbitrary UEs, gNBs and satellite PA resources.** Existing mechanisms can prepare and coordinate a transition:

| Mechanism | What it provides | Limit for this profile |
|---|---|---|
| CHO with multiple candidates | Advance preparation; each UE executes when its conditions permit. | Multiple candidates are alternatives for one UE. If several trigger, UE selection can differ from the optimizer's desired profile. |
| NTN time/location CHO | Predictive conditions: Rel-17 pairs time/location with measurement triggers; Rel-18 permits independent conditions in some scenarios and supports time-based RACH-less execution. | An execution window does not guarantee identical completion times or successful access by every UE. |
| RRC reconfiguration batching | An implementation can dispatch multiple per-UE transactions together. | Parallel dispatch does not create one cross-UE acknowledgment or rollback operation. |
| Group handover | Can aggregate preparation, authentication or signaling. | Group signaling is not atomic application. Zhang et al.'s proposal still sends individual configurations and each UE performs random access. |
| Satellite switch with resynchronization | Can preserve a cell through a qualifying satellite change without L3 mobility. | A shared physical switch does not implement arbitrary redistribution of individual UEs across destination cells. |

The CHO limits follow [TS 38.331 v18.6.0, §5.3.5.13.5](https://www.etsi.org/deliver/etsi_ts/138300_138399/138331/18.06.00_60/ts_138331v180600p.pdf). Compare [TS 38.300 v17.8.0, §16.14.3.2.2](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/17.08.00_60/ts_138300v170800p.pdf) with the NTN additions and same-cell switch in [v18.8.0, §§16.14.3.2.2–3](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/18.08.00_60/ts_138300v180800p.pdf). Group-protocol evidence is [Zhang et al., §IV-B](https://arxiv.org/html/2403.13936v1), a research proposal evaluated in a discrete-event simulator, not a normative atomicity guarantee. Do not propose DAPS as the default repair: the reviewed Rel-18 NTN specification explicitly excludes it (§16.14.3.2.1).

My implementation recommendation is **prepare–reserve–execute–reconcile**, with a versioned controller transaction:

1. Snapshot current associations and pending handovers; assign a unique plan version and expiry. The optimization phase has no external actuation side effects.
2. Prepare targets and reserve transition resources; verify feeder/payload readiness. Validate a feasible sequence of intermediate profiles, including allowed CHO alternatives. A jointly feasible endpoint is insufficient.
3. Commit the plan in the controller's own state store, then issue time-windowed configurations where supported. Use staggered cohorts when simultaneous random access or temporary resource overlap would overload a target.
4. Track actual per-UE completion and payload readback. Release source resources only when the corresponding transition is confirmed or a defined recovery procedure resolves it. Reconcile failures against the actual mixed profile.

Controller-state commitment can be atomic. Air-interface completion remains asynchronous and fallible. A two-phase protocol cannot retroactively undo a UE that has already moved. For a proprietary scheduler under one controller, a time-tagged frame-boundary resource-map update may be implementable, but that requires vendor confirmation and still does not prove multi-UE handover atomicity.

This distinction directly affects the paper's objective. A two-user swap may fit both endpoints but overload a beam when only one move executes. A planned beam evacuation may save no activation energy if one UE stays; switching the beam off nevertheless causes outage. Temporary source/target overlap changes interference and energy. Therefore Contract §B4's score identity for the selected complete profile does not establish its realized transition benefit, and §C2's final-profile atomic commit remains a benchmark assumption until this execution layer is represented.

The minimum operational amendment is: **require a feasible transition schedule with bounded partial completion, or explicitly retain ideal atomic application as a limitation.** Apply any new execution semantics equally across operational comparison arms, consistent with Contract §A4.

**4. Fallback should preserve a valid running service state**

The question's description slightly understates the existing safeguard: Contract §§C1 and F2 already require the per-user baseline to be **jointly validated and repaired before** coordinator execution. That fixes simultaneous infeasibility at the snapshot. It does not establish validity ten seconds later.

| Failure | Why prevalidation does not suffice | Deployable response I recommend |
|---|---|---|
| Stale legal masks or capacity | Visibility, feeder state, admissions, beam mode or UE capability context changes during computation. | Expire proposals; revalidate against current state and the execution window; renew/check reservations. |
| Partial application | A prior plan or autonomous CHO is already in flight when timeout occurs. | Reconcile first; prohibit a second full-profile command over unresolved transitions. |
| Late solver result | Cancellation races with a result or queued command. | Fence every command with plan version, expiry and current-state precondition; reject obsolete results. Killing a worker alone is insufficient. |
| Oscillation | Intermittent deadlines alternate optimized and baseline associations. | Preserve current feasible service; use dwell/hysteresis and a persistent degraded mode after repeated misses. |
| Invalid “hold” | A LEO serving link may disappear before the next cycle. | Local mobility protection and valid preconfigured CHO continue independently; hold only while safe. |
| Baseline unavailable or unsafe | Preparation fails, metadata are missing, or nominal served-count protection misses per-user service risks. | Use a bounded local admission/repair policy, prioritize users facing loss, and preserve hardware/service constraints. |

The preferred deadline action is: **expire the optimization, retain the currently confirmed feasible configuration where safe, and let the local mobility executor complete necessary protected transitions.** Use the cached baseline only if fresh revalidation and transition preparation succeed. It remains a candidate action, not an unconditional fail-safe.

This is consistent with E2's design: an E2 node must function independently after RIC/E2 failure; INSERT procedures have explicit expiry behavior, and CONTROL requests undergo validation with acknowledgment/failure. These are useful primitives, not a ready-made implementation of the fallback above. [ETSI TS 104 038 v4.1.0, §§5.1.1 and 5.3.2.3–4](https://www.etsi.org/deliver/etsi_ts/104000_104099/104038/04.01.00_60/ts_104038v040100p.pdf).

Keep the sealed benchmark's baseline fallback for that benchmark. Implement this stronger operational fallback as a separately declared variant; count its actual bits, joules, outages, partial-completion events and timeouts. Changing the runtime fallback can change the measured method effect.

**5. Retrospective TLEs and defensible claim wording**

Contract §F1 already states the correct limitation: nearest-epoch TLE use is retrospective, and an operational claim needs causal inputs plus an explicit action-effective-time convention. Amendment item 4 still lists the causal operational variant and capability values as seal-time items. No such completed variant is supplied here.

The causal test is **availability**, not just reference epoch:

\[
\mathcal E(t_d)=\{e:t_{\rm received}(e)\le t_d\},\qquad
\widehat x(t_{\rm effective})=\operatorname{propagate}(e,t_{\rm effective}),\ e\in\mathcal E(t_d).
\]

Space-Track documents `gp_history.CREATION_DATE` as a publication-time discriminator and separately notes that element sets can have future epochs. Thus a future epoch alone is not proof of leakage; a past epoch alone is not proof of causal availability. Retrospective nearest-epoch selection without availability filtering does not establish a deployable information set. A forecast-horizon restriction cannot repair use of a later-published element set. [Space-Track official documentation, GP history and epoch FAQs](https://www.space-track.org/documentation).

**Suggested paper wording:**

> We evaluate a candidate ground-based supervisory association coordinator using retrospective orbital reconstruction, a nominal joint-resource model and idealized simultaneous profile application; operation with causally available telemetry and delayed, partially successful handover execution remains unvalidated.

“No realized fading access” is a narrower property than “operationally available information.” Similarly, standardized ephemeris signaling does not prove the provenance, accuracy or publication timing of the TLEs used in this experiment. Equal retrospective inputs across arms preserve that comparison's convention; they do not establish live performance or make the resulting EE an operational bound.

For an operational claim, I would require four concrete changes:

1. **Causal replay or prospective collection.** Archive product source, publication and controller receipt times, version, epoch and expiry. Select only received products; handle missing updates, maneuvers and orbit/position uncertainty. Retrospective truth can still be used for evaluation, never as an online feature.
2. **Execution-aware simulation.** Propagate to the intended execution window, retain the pre-existing profile during computation, and account for asynchronous movement, failures, transition energy and realized service. Identify each UE's action-effective time.
3. **An implemented interface contract.** Specify UE/cell/beam/PA identities, authorized telemetry and command APIs, measurement age, admission ownership, reservations, and PHY/MCS mapping. Calibrate the nominal model against the intended equipment.
4. **Full-chain evidence.** Demonstrate bounded computation on declared hardware and end-to-end timing under representative cohorts, contention, signaling bursts, telemetry loss and partial execution. Start with causal shadow mode and then a controlled integration test; report the actual fallback and completion distribution.

These operational changes should be versioned separately from the sealed scientific benchmark and applied symmetrically across its operational arms. Neither the 10 s number nor the presence of NTN-compatible inputs, by itself, warrants a deployment claim.

VERDICT: PLACEMENT=ground gateway-side gNB-CU-CP/NTN controller | COMPUTE_BUDGET_PLAUSIBLE=yes | ATOMICITY=controller-state commit plus prepare-reserve-execute-reconcile; UE execution remains non-atomic | DEPLOYABILITY_CLAIM=The study evaluates a candidate controller with retrospective inputs and idealized profile application; operational deployment remains unvalidated.
