**The predecessor did carry an opt-in intended per-beam `Cap25` user-assignment ceiling (central greedy reassignment, not an unconditional PHY admission invariant), V0.25 `a-r0` has no hard per-beam user cap, its representative isolated link first hits the 1.65 W RF cap at occupancy 12, and the 8-beam/12.5-user crowded EE optimum is physically meaningful as partial service rather than a no-cap modelling artefact.**

# BEAMCAP — design-phase determination, not a claim

## Decision in plain language

The current reference scale is not invalidated by the absence of an integer users-per-beam cap.

The decisive facts are:

- The predecessor's value was **25 users per beam**, but it was a project-created anti-collapse stress constraint, not a published commercial Ka-LEO capacity limit. Its action decoder tried to reassign an excess user to another legal action; it did not model a carrier bank, slot inventory, or modem admission queue. Its all-full fallback could exceed 25, so the code did not enforce an unconditional hard invariant.
- The exact predecessor `Cap25` would not bind the measured crowded endpoint anyway. Its eight beam occupancies are **5, 7, 10, 12, 14, 16, 17, and 19** at every one of the 12 anchors; the maximum is 19, not 25. `RSS_MAX` is still farther away: 47.75 mean active beams and modal occupancy 5 ([static-family result](/home/sat/mcrl-v025-rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md:42)).
- V0.25 already couples load to resource share, ACM target, required SINR, power, clipping, and partial delivery. On the specified representative isolated link, occupancy 12 requires 1.786591 W before clipping and therefore hits the **1.65 W** cap; at occupancy 13 no frozen ACM mode can meet the 50 Mbit/s setpoint.
- The crowded point gives every user an average **8% airtime share**, equivalent to **13.333333 MHz** of the 166.666667 MHz beam bandwidth. It delivers **29.716250 Mbit/s per user on average**, serves 1,200/1,200 at the PHY criterion, but only 30/1,200 (2.5%) attain the nominal 50 Mbit/s interval target.
- No official public maximum simultaneous-user count for an operational commercial Ka-band multibeam LEO beam was found. Official 3GPP study material explicitly uses at least 10 users per S/Ka beam, 10 simultaneous Ka VSATs, and related LEO cases with 15 or 20 users per cell. That does not calibrate this model, but it rules out declaring 12.5 physically impossible from headcount alone.

This conclusion does **not** rely on whether a cap would help any interaction route. It asks only whether the current occupied beam and delivered service can exist physically.

## Evidence classes and execution boundary

- **Verified by running current code:** the representative-link cap point; all 12 crowded endpoint profiles; pooled bits, joules, rate, service, attainment, occupancy, realised ACM counts, and RF-cap counts.
- **Verified by code/record inspection:** predecessor form/value/justification; V0.25's absence of a hard count cap; its dynamic TDM slots, finite bandwidth, ACM target, RF clipping, and objective; completed-measurement inventory and recorded costs.
- **Derived on paper:** airtime/bandwidth shares, per-user pooled rate, percentages, and cost sums.
- **Inferred:** the bounded physical-realism determination. It is explicitly limited to the declared synthetic, saturated, partial-service model; it is not flight-hardware validation or a commercial service guarantee.

The focused rerun used one Python process, the mandated interpreter, niceness 16, and all six BLAS/thread controls equal to one. It completed in 198.228 s and printed progress at all 12 anchors. Peak RSS was **1,780,850,688 bytes = 1.659 GiB**, below 5 GB. No learner or checkpoint was opened and no learned-arm EE was computed. Only the development world was used; no evaluation-only date was read. See the [runner](/home/sat/mcrl-v025-beamcap-ws/.scratch/beamcap/run_beamcap_probe.py) and [machine receipt](/home/sat/mcrl-v025-beamcap-ws/.scratch/beamcap/beamcap-probe-receipt.json).

## Part 1 — what the predecessor actually had

### 1.1 `Cap25`: intended hard user-assignment ceiling, opt-in

The predecessor's pre-registration enables `capacity-aware-greedy-assignment` and sets `anti_collapse_max_users_per_beam` to **25** ([pre-registration](/home/sat/modqn-paper-exploration/artifacts/phase04-route-alpha-gate-b-pre-registration-2026-05-26.json:140)). The record's exact labels are “**單波束最大 25 人容量限制 (`Cap25`)**” and “**極限壓力測試約束 (`Stress-Test Constraint`)**”; it says the purpose was to address shared-Q geometric-attractor collapse ([literature grounding](/home/sat/modqn-paper-exploration/artifacts/literature_grounding.md:9)). It immediately says this is not a commercial deployment value specified by the baseline paper or 3GPP ([literature grounding](/home/sat/modqn-paper-exploration/artifacts/literature_grounding.md:11)); lines 20–22 repeat both the value and justification.

Its exact action-decoder form was:

```python
max_users_per_beam = int(self.config.anti_collapse_max_users_per_beam)
...
selected = ranked[0]
for action in ranked:
    if assigned_counts[action] < max_users_per_beam:
        selected = action
        break
actions[uid] = int(selected)
assigned_counts[int(selected)] += 1
```

([predecessor `modqn.py`](/home/sat/modqn-paper-exploration/src/modqn_paper_reproduction/algorithms/modqn.py:308), especially lines 320–350). Dispatch to this decoder occurs only when the opt-in flag and named mode are enabled ([predecessor `modqn.py`](/home/sat/modqn-paper-exploration/src/modqn_paper_reproduction/algorithms/modqn.py:501), lines 524–545). The default builder otherwise sets `enabled=False`, mode `disabled`, and value 0 ([trainer config builder](/home/sat/modqn-paper-exploration/src/modqn_paper_reproduction/trainer_config_builder.py:136)).

Exact classification: this was a **centralized action-assignment guard intended to keep the count below 25 by reassignment**, not a physical-layer admission/rejection mechanism. If every legal action was already full, `selected` remained `ranked[0]` and its count was incremented. There is no fail/deny branch. Thus it behaved as a hard cap when an under-cap legal alternative existed, but the function itself did not prove or enforce `count <= 25` in all feasible-mask states.

### 1.2 The three commonly conflated mechanisms

| Mechanism | Predecessor status | Exact role |
|---|---|---|
| Per-beam user admission cap | **Present only as the opt-in intended `Cap25` action decoder above** | Reassigned users among ranked legal actions. No carrier/slot admission object; no guaranteed rejection when all legal choices were full. |
| Soft load term | **Present, separately** | `r3 = -(max_beam_thr - min_beam_thr) / U` is documented at [step.py](/home/sat/modqn-paper-exploration/src/modqn_paper_reproduction/env/step.py:18) and implemented at [step.py](/home/sat/modqn-paper-exploration/src/modqn_paper_reproduction/env/step.py:829), especially lines 864–865. It changes reward, not admissibility. |
| Implicit occupancy coupling | **Present, separately** | Per-user rate used `B/N_b * log2(1+SINR)` ([step.py](/home/sat/modqn-paper-exploration/src/modqn_paper_reproduction/env/step.py:18)). More users reduce each user's share even without `Cap25`. |

There was also a different sealed-lineage constraint that must not be misreported as `Cap25`: Family B hard-limited each satellite to **three simultaneously radiating beams/RF chains**, `k_cap=3`, explicitly called a “scenario-capacity assumption” ([Family-B code](/home/sat/mcrl-figures-deps/papers/modqn-paper-reproduction/src/modqn_paper_reproduction/env/family_b_step.py:54)). It activates only the top three demanded physical cells per satellite ([Family-B code](/home/sat/mcrl-figures-deps/papers/modqn-paper-reproduction/src/modqn_paper_reproduction/env/family_b_step.py:702), lines 716–726). The sealed ADR maps that to 12 RF accounting slots, `4 × 3`, and explicitly says the earlier derivation from a 10 Mbit/s floor is invalid ([ADR-003](/home/sat/mcrl-figures-deps/papers/modqn-paper-reproduction/docs/ADR-003-canonical-ee-closure.md:131), [ADR-003](/home/sat/mcrl-figures-deps/papers/modqn-paper-reproduction/docs/ADR-003-canonical-ee-closure.md:212)). That is a hard **active-beam-per-satellite** cap, not a users-per-beam cap.

## Part 2 — what V0.25 `a-r0` has now

### 2.1 No hard users-per-beam cap

**Verified by bounded code inspection:** a case-insensitive audit for `max_users`, `users_per_beam`, `beam_capacity`, `admission_cap`, `carrier_count`, `slot_count`, `occupancy_cap`, and `load_cap` over `src/mcrl/physics_v025` and the current matrix runner returned no match. Positive path tracing is stronger than that absence alone:

1. `StepEvaluator.evaluate_many` identifies itself as the dense real-world `a-r0` path and calls `evaluate_ar_tdm_catalogue` ([matrix runner](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:793), lines 798–824).
2. It marks every selected legal row as a valid assignment; occupancy is simply the count of live same-beam users ([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:187), lines 191–216). There is no count comparison followed by rejection.
3. The object path likewise groups every link by beam and constructs slot boundaries from `len(members)` ([architectures.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/architectures.py:268), lines 278–294). Any positive membership count becomes a schedule.

The 28 association actions, four cached satellites, and seven local cells are an action inventory ([constants](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/constants_v025.py:63)); they do not cap beam occupancy. Likewise, `REFERENCE_BEAMS_PER_SATELLITE=39` and the 100 W HOBS reference are explicitly “not a hardware ceiling” and “not a live clamp” ([constants](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/constants_v025.py:88)).

### 2.2 The existing implicit occupancy coupling

The current target law is exactly:

```python
required_se = rate_target_bps * occupancy / full_bandwidth_hz
```

It selects the lowest-threshold frozen ACM mode whose spectral efficiency meets that value; otherwise it returns `None` ([acm.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/acm.py:77), especially lines 95–101). The dense solver indexes that target by live occupancy, forces target-infeasible transmissions to the cap, and clips every update to 1.65 W ([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:247), lines 251–266). Declaration v1.1 requires exactly this behavior: if no MODCOD meets the target, transmit at the RF cap, retain partial delivery, and do not prune or repack ([v1.1 amendment](/home/sat/mcrl-records/decisions/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:6), lines 6–8).

**Verified by running code at the requested representative geometry:** isolated boresight link, 750 km slant range, 30° elevation, current 20 GHz channel, receiver, 166.666667 MHz beam bandwidth, and no co-channel interference.

| Occupancy | Required SE | Target mode | Uncapped RF needed | Result |
|---:|---:|---|---:|---|
| 10 | 3.000 bit/s/Hz | 32APSK 3/4 | 0.903702 W | below cap |
| 11 | 3.300 bit/s/Hz | 32APSK 5/6 | 1.291294 W | below cap |
| **12** | **3.600 bit/s/Hz** | **32APSK 8/9** | **1.786591 W** | **1.65 W cap binds** |
| **13** | **3.900 bit/s/Hz** | **none** | n/a | **50 Mbit/s target outside frozen ACM table; force cap** |

Thus the requested effective soft-cap number is **12 users for first RF clipping** on this representative isolated link, with a second target-feasibility edge at **13**. It is “soft” because neither edge rejects a user: the engine continues transmission and credits whatever the realised PHY decodes. Geometry and co-channel interference can make the RF cap bind sooner; 12 is not a universal network-wide threshold.

### 2.3 Bandwidth, carrier, and slot limits

- Finite beam bandwidth is present: 500 MHz total, reuse three, hence **166.666667 MHz per colour/beam** ([constants](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/constants_v025.py:21), lines 23–25).
- Equal-airtime full-band TDM is present. Each beam member gets one `1/n` time share; while active it uses the full beam bandwidth ([architectures.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/architectures.py:278), [architectures.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/architectures.py:697)).
- A **fixed number of user carriers or slots is absent**. The slot grid is generated dynamically from the maximum observed occupancy ([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:65), lines 65–70 and 209–216). Frequency reuse three is spectrum colouring, not three admitted users or three carriers per beam.

## Part 3 — realism of the crowded endpoint

### 3.1 Delivered service, verified by running the dense path

The rerun reproduces the standing crowded totals to binary64 rounding: 1.072637748181269×10¹² bits, 23,262.395146 J, and **46.110374 Mbit/J** across the 12 development anchors.

| Quantity | Crowded endpoint |
|---|---:|
| Assigned / PHY-served | 1,200 / **1,200** |
| Active beams | 8 at every anchor |
| Beam occupancies | 5, 7, 10, 12, 14, 16, 17, 19 at every anchor |
| Mean occupancy | **12.5 users/beam** |
| Mean per-user airtime | **8.000%** |
| Equivalent mean bandwidth share | **13.333333 MHz/user** |
| Actual share range | 20.000% / 33.333333 MHz at n=5 to 5.263% / 8.771930 MHz at n=19 |
| Mean delivered user rate | **29.716250 Mbit/s** |
| Per-user interval range | **0.650045–54.369661 Mbit/s** |
| Nominal-target attainment | **30/1,200 = 2.500%** |
| Mean rate / nominal 50 Mbit/s setpoint | **59.4325%** |
| RF-cap observations | **417,396/552,960 = 75.4839%** |

The 50 Mbit/s value is not a traffic demand or an SLA. It was sealed as a “synthetic operating point” that was “explicitly not calibrated demand” ([v1.1 amendment](/home/sat/mcrl-records/decisions/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:3), [v1.1 amendment](/home/sat/mcrl-records/decisions/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:6)). The same amendment explicitly retains actual partial delivery and reports target attainment separately ([v1.1 amendment](/home/sat/mcrl-records/decisions/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:7)). Therefore 2.5% attainment is not a contract violation. It does show that the EE optimum is a **partial-service operating point**, not “100 users each receiving 50 Mbit/s.”

### 3.2 Which ACM mode is selected

There is no honest single-mode answer because realised SINR changes by user, slot, boundary, and interference state.

- **Target/control mode by occupied beam:** n=5 → 8PSK 2/3; n=7 → 16APSK 2/3; n=10 → 32APSK 3/4; n=12 → 32APSK 8/9. At n=14, 16, 17, and 19 there is no target-feasible mode, so the controller forces 1.65 W. Half of the 96 beam-anchor occupancies are therefore beyond the 50 Mbit/s ACM target ceiling.
- **Realised decoder selection:** all frozen modes appear. The modal outcome is 32APSK 9/10 at 58,038/552,960 transmission observations (**10.4959%**), followed by 8PSK 2/3 at 8.9752%, 16APSK 2/3 at 8.4576%, and 16APSK 5/6 at 7.5222%. `NO_MODE` occurs in 5,469 observations (**0.9890%**). The decoder selects the highest-efficiency mode cleared by realised SINR ([acm.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/acm.py:55)); rate is its spectral efficiency times allocated bandwidth ([acm.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/acm.py:129)).

### 3.3 External-practice check and determination

No defensible published commercial hard maximum simultaneous-terminal count was found for an operational Ka-band multibeam LEO beam. A number is therefore not invented here.

The strongest official comparison is [3GPP TR 38.821 V16.2.0](https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3525): Table 6.1.1.1-5 uses at least 10 UEs per beam for S/Ka calibration; its LEO-600 Ka throughput case uses 10 UEs/cell with proportional-fair scheduling; and Table 6.1.3.2-1 averages a Ka VSAT case over **10 simultaneously transmitting UEs**, each allocated one tenth of beam bandwidth. The same study contains related LEO cases with 15 and 20 UEs/cell, though that passage does not establish Ka band. Local checked conversions are [Table 6.1.1.1-5](/home/sat/modqn-paper-exploration/paper-source/official-markdown/38821-g20/part-000.md:1625), [LEO-600 Ka throughput](/home/sat/modqn-paper-exploration/paper-source/official-markdown/38821-g20/part-001.md:45), [simultaneous Ka VSATs](/home/sat/modqn-paper-exploration/paper-source/official-markdown/38821-g20/part-001.md:320), and [15/20-UE LEO cases](/home/sat/modqn-paper-exploration/paper-source/official-markdown/38821-g20/part-001.md:940).

Operator/standard material describes finite scheduling resources rather than a universal integer headcount: [Telesat Lightspeed's official resiliency paper](https://www.telesat.com/wp-content/uploads/2022/05/Telesat-Lightspeed-Resiliency.pdf) describes dynamic terminal burst-time and beam-hop slots; [ETSI DVB-RCS2](https://www.etsi.org/deliver/etsi_en/301500_301599/30154502/01.04.01_60/en_30154502v010401p.pdf) defines network-assigned dynamic MF-TDMA time slots; and the [Kuiper Ka-LEO technical appendix](https://fcc.report/IBFS/SAT-LOA-20190704-00057/1773885.pdf?raw=1) describes multiple active customers, variable channel bandwidth, and FDMA/TDMA sharing without publishing a user cap.

**Inference:** the crowded EE optimum is physically meaningful **within the declared model boundary**. Twelve and a half simultaneous users per beam is not contradicted by the official material, the exact predecessor `Cap25` does not bind it, finite bandwidth is actually shared, and the measured output is nonzero broadband service averaging 29.7 Mbit/s/user. It would become a modelling artefact only if represented as full 50 Mbit/s-per-user service or if a separately sourced hardware/scheduler constraint below the observed maximum occupancy 19 were established. Neither is true in the available record. Accordingly, the present `RSS_MAX` and crowded reference scale stands against this specific objection.

## Part 4 — change price, without a recommendation

Introducing any count cap as a new physical/admission rule would change legal configurations, selection paths, target occupancies, calibration inputs, and corpus labels. Even a value of 25—which does not exclude the two cited endpoints—would require rerunning searches that may visit occupancies above 25. The following is the reproducibility blast radius, not an argument for or against the change.

### Inventory that must be re-measured

| Class | Count | Required work | Recorded like-for-like cost |
|---|---:|---|---:|
| Non-learned static comparison | **6 arms × 12 anchors = 72 arm-anchors** | `RANDOM`, `ROUND_ROBIN`, `RSS_MAX`, `NEAREST_ELIGIBLE`, `MYOPIC_GREEDY`, `FIRST_IMPROVEMENT_FP`, including every ceiling/reference calibration that consumes them | **865.372 s = 0.240 h** ([record](/home/sat/mcrl-v025-rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md:71)) |
| Crowding diagnostic family | **11 pooled levels; 356 retained anchor rows** | Rebuild its feasible family, service guards, endpoint slope, mode/cap/service diagnostics | **985.644 s = 0.274 h** ([record](/home/sat/mcrl-v025-crowd-ws/CROWDING-COST-2026-09-10.md:19)) |
| Ceiling products | **7 distinct studies** | (1) 20-anchor oracle; (2) 12-anchor coordination/acceleration/traversal ceilings; (3) 30-date SEALED ceiling; (4) 30-date `MARGIN_Q`; (5) three-width ceiling sweep and cap audit; (6) control-law ceiling; (7) two-rule multistart ceiling | **8.895 h recorded elapsed/worker-time sum**, detailed below |
| Exact physical corpora | **2 families** | Rebuild the 93-anchor exact C1/C2 source corpus and the 22-anchor/4,552-row C3 coalition corpus, then rebuild their 22-anchor common view, raw and z-score views, and all manifests/hashes | C1/C2 measured build: **21,271.574 s = 5.909 h** ([record](/home/sat/mcrl-v025-datepool-ws/EXACT-SOURCE-BUILD-2026-09-10.md:11)); C3 measured components: **101.513 s joint evaluation + 18.697 s reader**, with total build wall unrecorded |
| Panel scopes | **6 scopes** | 12-anchor development; 20-anchor R2 oracle; 8-anchor R2 control/multistart; 30 TRAIN-date/196-anchor; 93/22 corpus panels; later formal 48 evaluation-only dates | Included where already measured; the formal 48-date cost is **unknown and not yet incurred**. No one of those dates was read here. |
| Completed production training | **3 runs** | Rebuild all Q1-v1, Q1-v2, and Q1-v2z five-arm, 16-seed, 500-epoch runs from the new corpora; old checkpoints cannot be reused | **27,062.784 s = 7.517 h sequential**; **2.716 h** if the three measured-duration runs alone can execute concurrently under the three-process/resource envelope |

The seven ceiling-cost components are:

- 20-anchor oracle: 694.562 s, but its old run used four processes, so a compliant at-most-three-process rerun needs a fresh timing ([oracle record](/home/sat/mcrl-v025-oracle-ws/ORACLE-CEILING-2026-09-09.md:114)).
- 12-anchor three-ceiling PANELCEIL pass: 704.283 s ([receipt](/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/panelceil-receipt.json)).
- 30-date SEALED: 2.771 wall hours over 196 anchors ([record](/home/sat/mcrl-v025-ceiling30-ws/CEILING-30-DATES-2026-09-10.md:76)).
- 30-date `MARGIN_Q`: 10,690.414 s = 2.970 h summed from its 30 result receipts ([aggregate](/home/sat/mcrl-v025-ceiling30-ws/.scratch/oracle-ceiling30-margin/ceiling30-margin-aggregate.json)).
- Three-width main sweeps plus their selected-profile cap audits: 5,260.204 s = 1.461 h from the six machine receipts cited in the [beam-width report](/home/sat/mcrl-v025-beam-ws/BEAM-WIDTH-CEILING-SWEEP-2026-09-10.md:111).
- Control-law ceiling: 79.046 s ([receipt](/home/sat/mcrl-v025-arch-ws/.scratch/control-law-ceiling/control-law-ceiling.json)).
- Multistart: 4,616.153 worker-seconds = 1.282 worker-hours across 16 receipts; it used at most two workers, so worker-time is not identical to elapsed wall time ([record](/home/sat/mcrl-v025-ladder-ws/MULTISTART-CEILING-2026-09-10.md:216)).

The corpus timing boundary matters. The later build did complete **4,552 coalition rows over 22 anchors** ([C3 coalition build](/home/sat/mcrl-v025-coalgen-ws/C3-COALITION-BUILD-2026-09-10.md:1)). Its timer covers only the joint `evaluate_many` calls: mean 4.614247 s/anchor, **101.513 s total**; reader verification took **18.697 s** ([C3 coalition build](/home/sat/mcrl-v025-coalgen-ws/C3-COALITION-BUILD-2026-09-10.md:73), lines 102–113). Tape construction, parsing, context construction, serialization, and other verification were excluded, and no total build wall was recorded. Those 120.211 measured seconds may be added to the ledger; the excluded overhead cannot honestly be priced from the receipt.

The three completed training receipts are [Q1-v1](/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/training-result.json), [Q1-v2](/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/training-result.json), and [Q1-v2z](/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z/training-result.json), at 9,777.869, 9,117.896, and 8,167.019 s. Each is five arms × 16 seeds = 80 arm-seed lineages and wrote 80 cadence checkpoints; total affected is **240 arm-seed lineages and 240 checkpoints**. The five-arm/16-seed/500-epoch contract is independently stated in the [training report](/home/sat/mcrl-v025-design-ws/ZSCORE-VIEW-AND-TRAINING-2026-09-10.md:141).

### Cost number for the owner

Summing the recorded static, crowding, seven ceiling, 93-anchor corpus-build, the two timed C3 components, and three training durations gives **22.868 hours of known replay work**. That sum mixes elapsed time with the explicitly labelled multistart worker-time and is therefore a workload ledger, not a guaranteed critical-path wall clock. If only the three light training runs overlap perfectly, it becomes **18.067 hours**. Both figures exclude:

1. the unrecorded end-to-end overhead around the measured 22-anchor C3 joint evaluation and reader check;
2. any implementation, tests, migration, resealing, and calibration-design work for the cap itself;
3. formal evaluation on the unopened 48-date panel; and
4. the slowdown needed to make the old four-process oracle obey a three-process cap.

Consequently the defensible planning envelope for the known replay is **18.067–22.868 hours, plus unrecorded C3-build overhead and formal-evaluation time**. Giving a single smaller “exact wall-clock” number would fabricate costs the records do not contain.

## Final determination

The lineage once had an opt-in, project-invented `Cap25` user-assignment guard, but neither its value nor its implementation establishes a physical maximum for V0.25. The present model has no hard user-count cap and does have genuine finite-resource coupling. Its representative RF soft edge is occupancy 12; its ACM target edge is 13; its observed crowded beams reach 19 and deliver broad partial service.

On the available code, measurements, and primary-source practice, **the no-cap V0.25 crowded optimum is physically plausible as a saturated partial-service operating point**. It is not evidence of 50 Mbit/s service to every user, but it is also not an impossible state created merely by omitting `Cap25`. No recommendation about changing the model is made.
