VERIFIED — **The successor does not yet form a connected TLE → learner → claim pipeline.** Its local physics calculations have meaningful tests, but the real-provider handoffs, temporal event accounting, forecast construction, and merge authentication have unguarded gaps. The 21-field encoder has no production caller.

VERIFIED — This audit used source inspection, hashes, and read-only Python AST inspection; no tests, training, or simulations were run. The historical stage-2 report records “102 passed”; current acceptance status is UNKNOWN.

VERIFIED — Evidence aliases:

- `S` = `/home/sat/mcrl-v025-stage2-snapshot-20260908`; bare physics filenames below mean `S/src/mcrl/physics_v025/`.
- `P` = `/home/sat/mcrl-v025-codex-ws-provider`; `provider` means [P/src/mcrl/physics_v025/provider_legacy.py](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:1).
- `L` = `/home/sat/mcrl-v023-codex-ws-c3s-baselines`; `env/...` and `algorithms/...` mean `L/src/mcrl/...`.
- `Q` = `S/tests/physics_v025`; `QP` = `P/tests/physics_v025`.
- `R` = [matrix probe runner](/home/sat/mcrl-v025-stage2-snapshot-20260908/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1).
- `D1` = [stage-1/1b decisions](/home/sat/mcrl-v025-stage2-snapshot-20260908/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-STAGE1-1B-2026-09-08.md:1); `D2` = [stage-2 decisions](/home/sat/mcrl-v025-codex-ws-provider/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md:1).
- `V0`, `V1`, `V2` = the original, v1.1, and v1.2 priority declarations under `S/.scratch/multi-catfish-v025-physics-successor/`.
- `A` = [round-3 consolidation](/home/sat/mcrl-v025-codex-ws-provider/.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-PHYSICS-EE-ROUND3-CONSOLIDATION-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md:144).
- `M` = [controller pipeline map](/home/sat/mcrl-v023-codex-audits/END-TO-END-PIPELINE-MAP-2026-09-08.md:1).

VERIFIED — Provider evidence describes untracked WIP, SHA-256 `ac6c7cd9444a3fa7315a5b7c08b7278e0769a8fcc550be4e084fb675cd988472`. The cited legacy scenario, ephemeris, action-contract, link-budget, D2, and MODQN files are byte-identical across L, S, and P.

VERIFIED — **Findings, ranked by severity.** `N1–N12` identify newly exposed core risks; `K` identifies already-declared work that remains unimplemented. Proposed guards below are recommendations, not executed tests.

VERIFIED — **P0 / N1 — A victim’s candidate list is assumed sufficient to describe every radiating aggressor.** The provider constructs cross gains only for that victim’s candidate NORADs, omits its own NORAD, and points each aggressor’s transmit pattern at the victim candidate’s cell centre (`provider:390,423–450,470–481`). `tapes.py:329–334` then looks up the selected aggressor by NORAD alone and substitutes zero for missing entries. The selected aggressor beam identity never enters that lookup.

INFERRED — This can erase interference from outside-shortlist satellites and same-satellite distinct beams, and gives the wrong gain when an aggressor changes beam. Power, service, energy, and C3 interaction consequently describe a different radiation field. **Guard:** independently compute three selected-link fixtures covering those cases and require missing gains to fail closed. **Owner:** stages 1–3. VERIFIED — `QP/test_provider_legacy.py:151` checks ordering/nonnegativity and explicitly expects own-NORAD exclusion; it does not guard this arrow.

VERIFIED — **P0 / N2 — Every user is assumed to have a legal option.** `_catalogue` takes the Cartesian product of each user’s legal-option tuple without inserting `None` for an empty tuple (`R:192–208`). One empty tuple makes the entire product empty; only BASE remains.

INFERRED — One disconnected user disables all other users’ unilateral and joint alternatives. **Guard:** three-user fixture with one disconnected user and two users having legal alternatives; retain the disconnected user’s no-op while enumerating the others’ moves. **Owner:** stages 3/5/8. VERIFIED — The all-false-mask KAT at `Q/test_contract_discriminators.py:86` does not exercise this catalogue.

VERIFIED — **P0 / N6 — An event classifier is assumed to constitute a temporal event ledger.** `StepEvaluator.evaluate` calls `score_setting` without interruptions (`R:273`); its default is empty (`adapter.py:156`). Handover reporting compares each selected configuration with the same-step carrier BASE, not that arm’s previous committed association (`R:664–674`). Cell-rekey flags and reported rekeys are hardcoded false/zero (`R:670,857–860`).

INFERRED — H/SH apply no handover blackout through this runner, and handover/Φ outcomes measure deviations from BASE rather than actual arm trajectories. **Guard:** two-step committed satellite change; require one temporal event, the declared 142-ms useful-time loss, unchanged RF energy, and consistent reward/reporting costs. **Owner:** stages 1/3/4/8. VERIFIED — `test_shared_tape_rescores_standby_handover_and_u_without_reradiation` injects an event manually (`Q/test_integration_matrix.py:150`); it does not test runner event production.

VERIFIED — **P0 / N4 — Initial legality is assumed to remain sufficient throughout the step.** Provider rows persist while visibility and D2 eligibility are recomputed (`provider:362–390,458–468`). `geometry_for` checks legality only at boundary zero and constructs `Link` without either flag (`tapes.py:318–345`).

INFERRED — A selected link can continue producing service after a live visibility/D2 transition because downstream code cannot see that transition. UNKNOWN — The inspected declarations do not settle whether mid-step D2 release terminates an attempt immediately or at the next decision. **Guard:** separate D2-release and 10°-crossing fixtures at boundary 17, asserting the declared allocation, bits, interference, and energy afterwards. **Owner:** stages 1/3. VERIFIED — No provider-to-service test covers either crossing.

VERIFIED — **P0 / N5 — “Realised gain = nominal gain × fading” assumes deterministic losses occur once.** Provider nominal gain uses `link_power_factor` (`provider:418–421`), whose `total_path_loss_db` already includes scintillation (`env/link_budget.py:354–358,679–685`). Provider then multiplies `keyed_fading_gain` (`provider:478,512`), which includes scintillation again (`channel.py:240–244`).

INFERRED — Realised direct and cross channels receive an extra elevation-dependent loss, misaligning nominal power control and realised decoding. **Guard:** independent direct/cross gain reconstruction with exactly one scintillation factor at two elevations and fixed component keys. **Owner:** stage 2/provider. VERIFIED — Existing decision-instant parity checks nominal gain only (`QP/test_provider_legacy.py:56–88`).

VERIFIED — **P1 / K — The declared C3 revision has not landed.** `D2:9` requires interaction-only shares, but `targets.py:322–334` accepts exactly two coalition users and returns `e_i + Ψ/2`; the runner supplies nonzero externalities (`R:507–530`). It then retains the maximum partner-dependent C3 value for each action (`R:537–542`).

INFERRED — Unilateral effects already inside whole-network C1 can be counted again; a selected action can receive a bonus derived from an unselected partner. Larger-set sharing is absent. **Guard:** zero-Ψ/nonzero-externality fixture, absent-partner fixture, and three-user share-conservation fixture. **Owner:** stage 5. VERIFIED — The existing C3 KAT explicitly asserts the superseded externality-inclusive values (`Q/test_stage2_tapes_targets_state.py:282–296`).

VERIFIED — **P1 / N8 — A forecast record is assumed to certify the forecast it names.** `_forecast_rows` uses realised future profiles, makes survival depend on every represented network user, and catches both contract errors and invalid-solver `ProbeError`s (`R:388–409`). Failure substitutes projected BASE energy with zero whole-network bits (`R:392–418`). “Required power” is the maximum already-capped transmitted power across all users/boundaries, paired with 1.65 W even for FDM (`R:287–296`).

INFERRED — C2 can absorb on a nonfocal user’s failure, turn an invalid solve into a scored surrogate, leak future fading into an allegedly deployable forecast, and never expose a negative uncapped power margin. **Guard:** focal/nonfocal survival discriminator; solver-invalid rejection; fading-blind forecast fixture; overloaded focal FDM link requiring power above its own sub-cap. **Owner:** stages 3/5/6. VERIFIED — The C2 KAT supplies hand-built projections, not this evaluator (`Q/test_stage2_tapes_targets_state.py:262`).

VERIFIED — **P1 / N3 — Freezing an inventory before actions is assumed to make it physical and horizon-independent.** Provider inventory is the Cartesian product of satellites visible somewhere in the prepared horizon and cells addressable somewhere in that horizon (`provider:253–284`). It explicitly equates an RF chain with a global earth-fixed cell (`provider:269–271`).

INFERRED — Extending the horizon can alter standby energy for an unchanged prefix; moving to another cell is treated as using another physical chain without an independent hardware mapping. **Guard:** identical-prefix/different-horizon inventory and S-energy comparison, plus an independently declared satellite RF-chain census. **Owner:** stages 1/3. VERIFIED — `HardwareInventory` claims independence from horizons (`energy.py:46–47`), but the provider test checks only a sampled candidate superset (`QP/test_provider_legacy.py:197`).

VERIFIED — **P1 / N7 — Equal boundary timestamps are assumed to mean equal world state.** Satellite position uses `step*47+boundary`, but user position is frozen at the decision-step snapshot (`provider:362–372`). Users move when `ScenarioDriver.step` executes (`env/scenario.py:217–219`). Provider initial D2 state also inherits the legacy prime-then-earlier-window sequence (`env/scenario.py:189–206,321–349`).

INFERRED — Adjacent `(step,47)` and `(step+1,0)` samples can have identical satellite time but different user geometry; correct sample counts do not cure the D2 chronology defect. UNKNOWN — Piecewise-constant user motion may be intended, but its left/right convention is not sealed here. **Guard:** shared-boundary continuity or explicitly paired discontinuities, independent chronological D2 oracle, and a step-4 refresh fixture. **Owner:** stage 1. VERIFIED — Provider tests cover steps 0–2 and satellite-only sub-boundary parity (`QP/test_provider_legacy.py:45–51,92`).

VERIFIED — **P1 / N9 — Scheduled-user outputs are assumed sufficient for endpoint denominators and service semantics.** `None` assignments disappear from Geometry (`tapes.py:312–313`). `EvaluatedProfile.outcome` divides availability by the number of represented users, while `_arm_row` uses the full assignment roster (`R:153,662–689`). Adapter boundary decoding requires every scheduled slot to pass (`adapter.py:130–141`); step `served_phy` then means any positive integrated decoding time (`adapter.py:179–181`).

INFERRED — Target and receipt availability can disagree for disconnected users; rate tails omit zero-rate absent users; decoding availability, partial service, and complete-service user-steps are not interchangeable. **Guard:** fixed-roster fixture containing disconnected, partially decoding, and fully decoding users, reconciled through resolution, adapter, endpoint, and receipt. **Owner:** stages 3/4/8. VERIFIED — The runner never constructs `StepEndpoint` or calls its reward-identity assertion.

VERIFIED — **P1 / N10 — Internally consistent hashes are assumed to authenticate the approved experiment.** Merge checks sidecars, self-digests, setting identity, and cross-unit agreement (`R:1302–1336`), but does not load authoritative launch/world/calibration seals. It trusts `failure_analysis` rather than rebuilding summaries from step rows (`R:1264–1278`).

INFERRED — A consistently wrong batch can pass despite wrong anchors, catalogue, provider/code provenance, missing arms, NULL drift, or summary disagreement. **Guard:** recomputed-self-hash mutations must fail against an independent launch seal; separately reject incomplete arms/anchors and inconsistent summaries. **Owner:** stage 8. VERIFIED — `Q/test_stage2_runner.py:64–81` tests writing/overwrite refusal, not merge.

VERIFIED — **P1 / N11 — A world seed is assumed to be a learner seed, and positive energy is assumed sufficient for relative EE inference.** Provider stores the world seed as `training_seed` (`provider:299–301,317–319`). Merge rejects repeated date×seed clusters instead of pooling worlds within them (`R:1251–1259`). Bootstrap permits zero bits but divides by comparator EE and takes log EE (`R:893–909`).

INFERRED — Future confirmation can misidentify its replication unit, reject legitimate repeated-cluster worlds, or produce undefined statistics for zero-delivery arms. **Guard:** two worlds sharing one date×learner-seed cluster; independent world/learner seed fields; zero-bit and all-dark fixtures with a sealed disposition. **Owner:** stages 0/8. UNKNOWN — The required zero-baseline convention for relative handover/Φ-cost margins is also unspecified.

VERIFIED — **P1 / N12 — Cached lookup time and per-evaluation q are assumed to measure deployment and campaign cost.** Catalogue evaluation, forecasts, and selections precede the arm timer (`R:718–754`); the timed evaluation returns cached data (`R:264–265,757–759`). World construction precedes the unit timer (`R:972–983`). Sharing is advertised (`R:1041`), but caches belong to individual setting/step evaluators (`R:245–260`).

INFERRED — Reported decision tails cannot validate the 30.08-s deadline; the estimate does not establish the 160-core-hour budget for the declared catalogue and anchor panel. **Guard:** counted provider/power calls across treatments and timing that includes proposal generation, forecasts, selection, validation, and fallback. **Owner:** stages 3/7/8. VERIFIED — The estimate test asserts advertised flags rather than executed sharing (`Q/test_stage2_runner.py:41–47`).

VERIFIED — **P1 / K — Oracle arms and learned ablations are different estimands.** FULL/DROP_C1/DROP_C2 receive exact whole-network objective plus factor bonuses (`R:574–595`); DROP_C3 uses independent proposals (`R:748`). This decoder change is explicitly prescribed for the oracle screen at `A:174`, which distinguishes learned neutral-source retraining.

INFERRED — This runner cannot establish “only the dropped learned head changed,” and its outputs must not be presented as that experiment. **Guard:** separate oracle/learned experiment schemas; matched learned decoder, information, budgets, seeds, and checkpoint rules. **Owner:** stages 5/7/8.

VERIFIED — **P2 — The synthetic fixture does not enforce one colour per physical beam.** With three users, `TinySyntheticProvider` assigns users 0 and 2 the same beam but different colours (`tapes.py:489–491,531`). Geometry validates individual colours without checking beam consistency (`architectures.py:40–45,66–90`).

INFERRED — Synthetic scheduling and interference can disagree about the same physical beam. **Guard:** reject conflicting colours for an identical beam. **Owner:** stages 1/3. This fixture defect is not counted among the twelve core risks.

VERIFIED — **One user-step, traced statically.** Take `V025_PROBE/world/1`, seed `5261619120743994529`, user 0, step 0, nearest-eligible carrier, architecture `a-r0`. Its selected beam is denoted `(s,c)` because no world was simulated. The interval is episode-relative `[0,30.08]` seconds, with 48 samples. The user must travel with the complete network configuration because powers and interference are coupled.

VERIFIED — In the ledger below, “NO guard” means no test asserts the semantic handoff; a broad synthetic smoke may execute it. Named tests were inspected, not run.

| Arrow | Structure and units | Identity and timestamp | Validation owner | Exact arrow coverage |
|---|---|---|---|---|
| VERIFIED A0: domain → sampled epoch | Domain string → 63-bit seed → aware UTC datetime | World domain/seed; sampled start UTC | `tapes.py:42–49`; provider TRAIN gate `:163–173` | Hash rule: `test_project_and_calibration_seed_domains_are_exact_and_disjoint`, Q/state-test:86; no all-runners TRAIN guard |
| VERIFIED A1: TLE files → satellite set | `TleRecord`/`ElementSelection`; epochs and age hours | NORAD plus selected element epoch; age measured at episode start | `env/ephemeris.py:97–158` | NO provider guard asserting selected records/files/ages |
| VERIFIED A2: world → 48 boundary geometry | Internal ECEF arrays in km → `PrimitiveBoundary`/`PrimitiveCandidate`; degrees, km, seconds | `(world,user,(NORAD,cell))`; `step*30.08+k*.640` | Provider `:344–396`; `StepTape` `tapes.py:198–207` | Satellite arrow: `test_sub_boundary_ecef_matches_direct_sgp4`, QP/provider-test:92; NO moving-user/seam guard |
| VERIFIED A3: physical world → inventory | `HardwareInventory.chains`, identity tuples | `(NORAD,cell)`; frozen before actions, derived from prepared horizon | Provider `:253–284`; tape membership `:251–255` | Sampled superset: `test_inventory_is_a_superset_of_every_sampled_legal_identity`, QP/provider-test:197; NO physical/horizon guard |
| VERIFIED A4: geometry → direct/realised channels | Positive scalar received W/RF W; cross-gain tuples | Victim candidate; aggressor NORAD; fading key adds world/user/time-ns/component | Provider `:398–450`; candidate checks `tapes.py:124–145` | Nominal only: `test_decision_instant_geometry_and_gain_parity`, QP/provider-test:56; NO realised composition guard |
| VERIFIED A5: candidates → carrier assignment | `CarrierAction.assignments`: user → beam or None | Carrier, step, user; decision boundary zero | `fixed_carrier_actions`, `tapes.py:375–407` | NO exact assignment/retention/empty-user guard; manifest test only checks carrier inventory |
| VERIFIED A6: assignment + cross gains → scheduled Geometry | `Geometry(links, nominal_cross, realised_cross)`; matrices W/W | Ordered users; selected beam; outer `(time_s,Geometry)` pairs | `geometry_for`, `tapes.py:297–350`; Geometry shape checks | NO selected-aggressor, missing-cross, or live-legality guard |
| VERIFIED A7: Geometry → coupled rate-target powers | `RadiationResult`, slots, transmissions, certificate; RF W, bandwidth Hz, slot fractions | User and beam; time remains in outer `RadiationBoundary` | `architectures.py:319–385,644–714`; zero-start capped solve | `test_rate_target_coupled_solve_clears_discrete_threshold`, Q/architectures-test:336 |
| VERIFIED A8: powers/interference → ACM/service | SINR dimensionless; `ACMMode`; rate bit/s; service/target flags | User within normalized slot; boundary time external | `acm.py:47–61,77–118`; `resolution.py:54–91` | `test_rate_target_cap_marks_infeasible_but_keeps_phy_bits_and_energy`, Q/architectures-test:247 |
| VERIFIED A9: slot radiation → energy | `EnergyReceipt`; PA/circuit/standby/baseband joules | Beam and satellite deduplication; explicit duration seconds | `energy.py:87–159` | `test_rate_target_tdm_slot_pa_and_fdm_summed_rf_fixture`, Q/architectures-test:291 |
| VERIFIED A10: committed transitions → blackout events | `HandoverEvent` has identities but no time; `InterruptionEvent` has user/time/kind | Needs arm history and physical transition time | Intended caller owns conversion; `integration.py:70–99` validates/merges intervals | NO runner conversion; only manually injected-event tests |
| VERIFIED A11: radiation boundaries → integrated bits/energy | `BoundarySample`: bit/s, W, decoding bool → `IntegrationReceipt`: bits, J, user-seconds | User; 48 episode-relative timestamps | Adapter rescoring `:118–176`; integrator `:165–197` | `test_shared_tape_rescores_standby_handover_and_u_without_reradiation`, Q/integration-test:150; NO event-discontinuity production guard |
| VERIFIED A12: integrated score → endpoint/reward | Runner uses `CellScore` → floats/`NetworkOutcome`; endpoint library separately offers `StepEndpoint`/`Fraction` totals | Runner context carries world/step; endpoint objects contain neither | `R:152–163,659–703`; `endpoint.py:33–149` | NO connected guard; `test_reward_core_identity_is_exact`, Q/state-test:299, uses hand-built endpoints |
| VERIFIED A13: nominal reference → calibration | `NominalConfiguration` → `CalibrationObservation/Values`; η=λ bit/J, κ bit/(user·s) | Setting digest, two CAL domains, selected configuration IDs | `R:309–340`; `calibration.py:203–235` | `test_nominal_greedy_and_calibration_are_deterministic_per_setting`, Q/state-test:181, uses supplied totals; NO real-provider freeze guard |
| VERIFIED A14: physical outcomes → C1 | Two `NetworkOutcome`s → `C1Label`; surplus bits, Φ, normalized total | Candidate/default IDs retained only by caller; anchor time absent in label | `targets.py:153–170`; caller `R:461–468` | Arithmetic: `test_c1_is_whole_network_difference_plus_explicit_phi`, Q/state-test:231; NO physics-to-label parity guard |
| VERIFIED A15: persisted assignments → C2 | Three `OffsetProjection`s → `C2Label`; bits, W, dB, SE, validity/survival | Caller’s assignments; offsets +30.08/+60.16/+90.24 s | `R:373–433`; `targets.py:248–294` | Arithmetic-only `test_c2_charges_failed_attempt_then_applies_absorbing_three_offset_penalty`, Q/state-test:262; NO evaluator-contract guard |
| VERIFIED A16: coalition outcomes → C3 | Four whole-network outcomes → Ψ and per-user shares in bits | Pair user IDs; regime prices explicit; no stored world/time/catalogue key | `targets.py:307–335`; caller `R:496–542` | Existing test asserts old e-inclusive formula; NO current-declaration guard |
| VERIFIED A17: physical/forecast outputs → 21-field state | `C2ActionState` → `EncodedC2State`; normalized tuple, schema SHA, price fractions | No user/action/world/time fields in encoded object | Encoder shape/finiteness/price checks, `state_v025.py:131–171` | Hand-built-row test `test_c2_schema_has_new_features_frozen_shape_and_price_binding`, Q/state-test:320; NO extraction arrow |
| UNKNOWN A18: encoded state/labels → shards/replay | No successor producer/transition schema found | Required world/user/action/time/calibration lineage unbound | Stage 6 owner absent | NO test |
| UNKNOWN A19: replay → learner → deployed joint action | No successor adapter/common-action bootstrap/checkpoint decoder found | Required learner seed, checkpoint, legal joint-action identity | Stage 7 owner absent | NO successor test |
| VERIFIED A20: evaluated profiles → unit receipt | JSON dictionaries; bits, J, availability, handover rates, hashes | Cell/world/cluster; per-row step/carrier; no explicit boundary UTC | `R:961–1027`; write-once helper `R:1216` | `test_unit_receipt_is_complete_and_write_once`, Q/runner-test:64; only selected completeness/placebo assertions |
| VERIFIED A21: receipts → merged cluster inputs | Immutable JSON → trusted `failure_analysis` summaries | Cell and four world indices; date×“training_seed” | `R:1242–1337` | NO merge guard |
| VERIFIED A22: cluster inputs → evaluation claim | Pooled EE ratios, bootstrap bounds, QoS gates | Per-cell contrasts; bootstrap seed; panel time span not represented | `R:864–945,1283–1297` | Ratio estimator only: `test_cluster_bootstrap_recomputes_pooled_ratio_not_mean_world_ee`, Q/runner-test:50; NO sealed-gate/admission guard |

VERIFIED — `state-test`, `architectures-test`, `integration-test`, `runner-test`, and `provider-test` in that table abbreviate `test_stage2_tapes_targets_state.py`, `test_architectures.py`, `test_integration_matrix.py`, `test_stage2_runner.py`, and `test_provider_legacy.py`, respectively.

INFERRED — **(a) Arrows lacking a semantic guard, ranked by basicness:**

1. A5–A6: one disconnected user must not erase other users’ actions; every radiating selected beam must have its correct cross gain.
2. A2/A6/A10: one physical instant and one committed transition must propagate consistently into legality, service, and blackout accounting.
3. A4: each antenna/path/fading factor must appear exactly once.
4. A3: physical hardware must not change with forecast length, catalogue construction, or user-cell indexing.
5. A11–A12: preserve the full user roster and distinguish airtime decoding, partial service, complete service, and useful availability.
6. A15: preserve focal identity, invalidity, causal information, uncapped required power, and absorbing-loss semantics.
7. A14/A16: physical candidate/default/coalition outcomes must implement the currently declared labels and selected-set interaction.
8. A0–A1/A13: bind actual source files, element epochs, TRAIN split, setting, and frozen calibration—not merely domain names and equal prices.
9. A17–A19: derive observable state, serialize provenance, construct transitions, train, and decode through one declared information/scale contract.
10. A20–A22: authenticate the launched protocol, recompute summaries, group true clusters, handle zero outcomes, and apply the sealed terminal gates.

INFERRED — **(b) Three likely “next week” discoveries; five-line reproduction plans, not executed:**

INFERRED — **Disconnected-user catalogue collapse**
1. Construct three primitive users at one decision boundary.
2. Give user 0 no legal candidate and users 1/2 two legal candidates each.
3. Construct BASE with user 0 assigned `None`.
4. Invoke only the catalogue builder and inspect its assignments.
5. Require moves for users 1/2; current Cartesian construction returns BASE alone.

INFERRED — **Interference unchanged when the transmitting beam moves**
1. Construct a fixed victim and a co-colour aggressor with two different beam centres.
2. Hold the aggressor NORAD and RF power fixed while changing its selected beam.
3. Independently calculate transmit off-axis gain from each aggressor beam centre to the victim.
4. Compare those gains with the two `geometry_for` matrices.
5. Repeat with a same-NORAD distinct beam and an aggressor outside the victim shortlist; require correct nonzero contributions.

INFERRED — **H treatment reports handovers but removes no useful time**
1. Construct two consecutive carrier/arm assignments containing one satellite change.
2. Keep channel quality high and independently record the committed before/after identities.
3. Score the step through the runner under 0 and H.
4. Reconcile event count, Φ, useful bits/time, and energy with a 142-ms blackout.
5. Require one temporal event and reduced useful service; current runner supplies no interruption events.

VERIFIED — **(c) Sealed requirements that current code cannot implement as written:**

| Requirement | Evidence and current disposition |
|---|---|
| VERIFIED Matrix count | `V2:6` says 28 eligible; its explicit enumeration and `matrix.py:93–104` give **25 eligible + 6 diagnostic = 31**, hence 124 four-world units. `D2:6` says v1.3 corrects this. UNKNOWN — Actual v1.3 file/sidecar was absent from all four supplied trees; its seal cannot be authenticated here. |
| VERIFIED Real-world bounded catalogue | `D2:8` requires the >4096 branch, every unilateral, top-K=10 pairs, and evacuations. `R:192–208` always materializes the full product, including calibration. With two options for 100 users the product has 2¹⁰⁰ assignments. No bound is implemented. |
| VERIFIED Anchor panel | `D2:7` requires 30 anchors per carrier, 90 per world, with prospectively selected thinning if needed. `R:965,985–995` defaults to three total anchors and rotates carriers between them; CLI exposes neither this panel nor thinning. |
| VERIFIED Forecast horizon | Thirty executed steps require tape indices through step 32 (`R:975`). Provider’s zero-argument factory prepares 30 steps (`provider:66,136,598–601`). Simply changing `executed_steps` to 30 would exceed its prepared decision-state horizon. |
| VERIFIED Interaction-only/larger-set C3 | `D2:9` requires the revised shares; `targets.py:322–334` remains pair-only and externality-inclusive. |
| VERIFIED Event discontinuities | `D1:12` makes the builder supply left/right limits. `StepTape` accepts exactly 48 boundaries, and adapter scoring never supplies `discontinuities` to integration (`tapes.py:198–205`; `adapter.py:171–176`). The integrator’s separate capability is unwired. |
| VERIFIED QoS margins | `D2:10` specifies complete-service availability −0.5 pp and relative handover/Φ-cost +5% bounds. `R:873–875,906–938` implements decoding availability and absolute zero-margin bounds instead. |
| VERIFIED Training admission | `V0:18`, `V1:10`, and `A:181–185` require certified positive headroom, a genuine joint witness, and deployable S0 gain ≥1%. Runner merge emits intersection-union results without implementing that admission decision (`R:1283–1297`). |
| VERIFIED Cost budget | `A:187–197` requires a complete-workload rehearsal including tape construction and actual shared computation. Current timers/cache ownership do not establish it; N12 applies. |
| UNKNOWN Confirmatory inventory | The map’s six arms × five seeds × ≈600 worlds/≈161 dates and supplementary delta-method plan were not authenticated in the supplied successor seals. `V0:24` and `A:201` specify three initializations for Stage A. Current matrix code has 12 arms and four worlds; it is not that confirmatory runner. |

VERIFIED — Original/v1.1/v1.2 declaration files match their own sidecar hashes: prefixes `e45f2f02`, `6851d04b`, and `cd1922fb`. This does not authenticate the missing v1.3 artifact or prove execution of the declarations.

VERIFIED — **Map verification and every `?` disposition:**

- VERIFIED — `M:8–9`, split location: `env/ephemeris.py:211–278` defines seven TRAIN days, one embargo day, seven TEST days, one embargo day, anchored to the archive start. Provider asserts TRAIN at `provider:145–149,167–172`; `test_provider_rejects_a_test_date_without_sampling_it` exists at `QP/provider-test:213`. UNKNOWN — No single all-runners TRAIN assertion/test was established. Generic `build_world_tape` itself stamps `"TRAIN"` (`tapes.py:449`).
- VERIFIED — `M:8`, nearest-TLE/max-age: per-NORAD nearest absolute epoch over available date−1/date/date+1 files; age ≤24 h at episode start (`env/ephemeris.py:97–158`). UNKNOWN — No end-boundary age guard was found.
- VERIFIED — The archive contains 373 daily files. UNKNOWN — This audit did not authenticate the malformed-record quarantine, 9000→166-date/100→77-date counts, or historical effect-size receipts.
- VERIFIED — `M:49–50`, information/schema guard: no production calls to `encode_c2_state` exist in inspected source/runner ASTs. UNKNOWN — Equality of learner/coordinator information cannot be established without the missing extractor and decoder. No schema-to-information guard exists.
- VERIFIED — `M:57`, learner guard: no successor common-action/bootstrap/information test was found. Existing MODQN independently maximizes each head’s next Q (`algorithms/modqn.py:536–550`).
- VERIFIED — Memoryless zero-start power solving, nominal-control/realised-field separation, ACM target selection, failed-attempt energy retention, slot PA averaging, and left-snapshot treatment are implemented locally (`architectures.py:319–385,644–714`; `acm.py:77–118`; `resolution.py:60–76`; `adapter.py:167–176`).
- VERIFIED — Explicit target/state price signatures and exact arithmetic identity tests exist. UNKNOWN — Those tests establish neither physical correctness nor the missing integrated trajectory-to-reward connection.

VERIFIED — **Five map statements require correction as descriptions of current execution:**  
VERIFIED — M1: `M:68` “(NORAD, beam-chain) everywhere” is false for cross gains, which are NORAD-keyed.  
VERIFIED — M2: `M:29`’s unqualified rejection of `PA(Σ)` is false for FDM: FDM must sum simultaneous user RF before one beam PA calculation (`architectures.py:765–780`; Q/architectures-test:291).  
VERIFIED — M3: `M:41` interaction-only C3 describes the pending declaration, not current code.  
VERIFIED — M4: `M:42` the sealed bounded catalogue describes the pending declaration, not current code.  
VERIFIED — M5: `M:56` “DROP arms differ only in the dropped head” does not describe this oracle runner; its deliberate decoder change must be distinguished from learned ablations.  
VERIFIED — Pending declarations remain valid requirements; these refutations concern their presentation as current implementation.

INFERRED — **Additional invariants the controller should record:** every user has an explicit disposition; every scheduled aggressor has a beam-specific channel; one physical beam has one colour and hardware identity; each deterministic loss appears once; shared boundary times have a declared left/right state; legality and event history survive geometry conversion; solver INVALID never becomes a forecast surrogate; all metrics retain the same opportunity roster; world seeds and learner seeds are distinct; and receipt hashes bind an independently sealed protocol.

VERIFIED — **(d) Stages 6–8 are prose plus reusable legacy infrastructure, not an executable successor training/evaluation pipeline.** `state_v025.py:131–171` only normalizes supplied values. The runner imports/emits schema metadata, not observations (`R:57,1020`). Legacy trainer wiring still targets `StepEnvironment` (`S/src/mcrl/runtime/trainer_env.py:1–13,46–49`); MODQN still uses legacy state encoding and independent head maxima (`algorithms/modqn.py:68,536–550`).

INFERRED — To start when the matrix admits training, the following must already exist:

- A successor environment/state extractor with causal current/forecast information and a declared Q1/Q2/C3 representation; the 21 fields presently describe C2 only.
- Versioned source shards binding world, user, physical action, time, schema, physics setting, calibration digest, labels, masks, next state, and terminal/no-op status.
- A transition/replay adapter and common legal next-action bootstrap; explicit scaling from surplus bits and κ-normalized labels into commensurate learned scores.
- A selected-set C3 decoder, service guard, measured deadline, and deterministic fallback.
- Matched source/retraining budgets, initialization streams, DROP definitions, external comparator, and checkpoint-selection rules.
- Fresh inventoried evaluation panels, true date×learner-seed clustering, sealed QoS/zero-baseline conventions, launch/resume/merge validation, and an executable terminal admission/claim decision.
- Tests connecting these interfaces, including one fully reconciled primitive-world trajectory through source generation, learning, deployment, endpoint accounting, and receipt merge.

VERDICT: STAGE=D | REFUTED_MAP_CLAIMS=5 | NEW_CORE_RISKS=12 | BLOCKERS=joint-channel,empty-user-catalogue,live-legality,event-ledger,double-scintillation,C2-contract,C3-revision,bounded-catalogue,anchor-horizon,endpoint-QoS,seal-authentication,cost-validation,stages6-8