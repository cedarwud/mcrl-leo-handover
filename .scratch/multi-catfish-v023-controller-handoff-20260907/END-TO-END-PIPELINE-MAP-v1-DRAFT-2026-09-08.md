# End-to-end pipeline map v1 — from TLE to claim  
_Controller integration, 2026-09-08; current-state evidence is audit-time code. Controller decisions are prospective unless a later audit verifies implementation._

Evidence keys:

- `A/B/C/D`: `PIPELINE-AUDIT-{A,B,C,D}-…-2026-09-08.md`.
- `E`: `V025-ENGINE-STAGE2-AUDIT-CLAUDE-OPUS-2026-09-08.md`.
- `P`: `V025-PROVIDER-PREAUDIT-CLAUDE-OPUS-2026-09-08.md`.
- `FP`: `FIRST-PRINCIPLES-REVIEW-CODEX-GPT6-ASTRA-2026-09-08.md`.
- `D-A`, `D-CD`, `D-E`, `D-P`, `D-S1`, `D-S2`, `D-CB`: corresponding `V025-CONTROLLER-DECISIONS-*.md` files.
- `V1.0`–`V1.5`: priority declaration and amendments/errata.
- `VERIFIED` means observed in audited code/data; `REFUTED→` corrects the v0 map; `DECIDED` is binding but not necessarily implemented; `OPEN` names its owner and closing guard.

OPEN O21 — The skeleton contains Stage 0 through Stage 8—nine numbered sections—while the request calls them “eight stages.” All nine are preserved. Owner: controller/docs. Guard: designate whether Stage 0 is pre-pipeline or one of the counted stages.

## Stage 0 — Data, world identity and splits

- Inputs — VERIFIED V1: the archive contains 373 daily files; the 16-day split yields 166 TRAIN, 160 TEST and 47 embargo dates. The user model has 100 users, a deterministic earth-fixed grid with 13.9976 km radius, and 0.2506667 km stepwise motion per 30.08 s. `[A:45–46,101–107 → ephemeris.py:182,255; mobility.py:44,96,117; cells.py:125; scenario.py:53]`
- Outputs — REFUTED→ R1: a legacy world is not fully identified by `(TLE date, world seed)`. Identity also depends on exact start UTC, TLE/file selection, horizon/universe rule, code/configuration and persistent age-stream or panel-prefix state. `[A:79–87,152 → scenario.py:161; step.py:414,526; physical runner:1253]`
- Seed invariant — REFUTED→ R2: domain-derived SHA-256 seeds govern V0.25/C3-S, but the legacy 9,000 plan uses arithmetic seeds and reuses its first 100 seeds from DROP-C3. Learner-lineage and physical-world seeds are different quantities. `[A:89–99,154 → tapes.py:42; world-plan.py:94; dropc3 server:32]`
- Split invariant — REFUTED→ R3: “TEST is never read” is true for the named canonical runners, not globally; direct `ScenarioDriver.reset` and an arbitrary tape provider bypass the split. `[A:43–54,153 → training_pipeline.py:736; run_v023_c3s_screen.py:881; scenario.py:141]`
- Current safe paths — VERIFIED V2: the named C3-S, E1, 9,000-ladder, V025 probe and V025 calibration paths resolve TRAIN start dates. `[A:45–50 → training_pipeline.py:736; physical runner:1227; test_provider_legacy.py:213]`
- Manifest contract — DECIDED D1: one shared successor world factory must emit and reverify split identity, exact start UTC, TLE filenames/hashes, split-rule digest, provider digest, layout/mobility/fading identities, role, learner seed and world seed; no hardcoded `TRAIN`. Implementation: pending stage 4b. `[D-A items 3,4,7]`
- TLE convention — DECIDED D2: retain nearest absolute epoch per NORAD over date−1/date/date+1, allow future epochs, and enforce the 24-hour limit at selection time; document it as non-causal `VERIFY_SOURCE`. `[D-A item 5; V1.5 §5]`
- Panel separation — DECIDED D3: quarantine `V025_PROBE/world/{1..4}`; formal domains become `V025_PROBE_R2/world/{1..4}` and `V025_CAL_R2/world/{1..2}`. Claim dates must be unused by successor development roles; legacy overlap is recorded. Pending provider fix/stage 4b. `[D-CD items 4,6; V1.5 §4]`
- Seed/statistical identity — DECIDED D4: persist separate `world_seed` and `learner_seed`; pool worlds inside a date×learner-seed cell. `[D-CD item 3; D-A item 2]`
- Guards — VERIFIED V3: split disjointness/gap and one forced-TEST provider test exist, but no all-runner/TLE-file guard exists. `[A:45–53,159–160 → test_w02_split.py:99,119,192; test_provider_legacy.py:213]`
- Known defect/status — OPEN O1: no exact successor claim allocation manifest or final runner exists. Owner: stages 0/8. Guard: seal every world/role membership and reject any undeclared or role-overlapping world before opening outcomes. `[A:123–136,158; C:101–110]`
- Known defect/status — OPEN O2: legacy horizon and persistent age-stream dependence can change a nominally identical world. Owner: provider/runtime. Guard: “world B alone = world B after A” plus 3/30/31-step common-prefix KAT. `[A:79–87]`
- Known defect/status — OPEN O3: pipeline-wide TRAIN enforcement remains absent. Owner: stage 0/provider. Guard: enumerate every production runner and verify realised starts and all opened files through the shared factory. `[A:43–54]`
- Owner: stage 0 runtime/provider; controller owns the allocation manifest and attempt registry.

## Stage 1 — Geometry, time base, identities and legality

- Inputs/outputs — VERIFIED V4: successor `StepTape` requires 48 boundaries at `t+k·0.640 s`, `k=0…47`, spanning 30.08 s; the provider derives candidate geometry and D2 state from the legacy world. `[A:68–74 → tapes.py:192; provider_legacy.py:380,574]`
- Refresh invariant — VERIFIED V5: `N=4` refreshes candidate/cell identities only; action validation imposes no four-step residence constraint. `[A:114–121 → dwell.py:60,156; action_contract.py:574]`
- Handoff content — REFUTED→ R4: raw per-boundary user/satellite ECEF and off-axis geometry do not all cross the detached tape; the audited schema exposes initial layout and derived candidate quantities. `[A:101–112,155 → tapes.py:89,103]`
- D2 chronology — REFUTED→ R5: the forward successor tape removes time reversal inside the emitted interval but inherits the contaminated legacy boundary-0 D2 latch/TTT state. `[A:68–77,156 → scenario.py:184,313,343; provider_legacy.py:380,574]`
- Within-step motion — DECIDED D5: users are frozen at their decision-instant position for the 48 forward boundaries, move between steps as in legacy, and every physical discontinuity supplies explicit left/right values. Pending provider fix/stage 4. `[D-P item 4; D-S1 items 7,8]`
- Live legality — DECIDED D6: when a link crosses below 10° or loses D2 eligibility at boundary `k`, radiation, interference and decoding stop from `k` onward. Pending stage 4. `[D-CD item 8]`
- Event identity — DECIDED D7: association events use physical `(NORAD, beam-chain)` identities and distinguish stay, beam change, satellite change, re-entry and dwell-boundary cell re-key. Pending stage 4. `[D-CD item 1]`
- Guards — VERIFIED V6: satellite ECEF parity exists at boundaries 17/47; no raw-user seam, monotonic D2 initialization or full geometry-attestation guard exists. `[A:159–160 → test_provider_legacy.py:56,91]`
- Known defect/status — VERIFIED V7: the provider pre-audit found tautological D2 flags, slant copied into D2 distance, omitted altitude floor, hard-coded TTT, shrinking/censored horizons, step-0-only layout, zero-start-time assumptions and unhealthy-satellite leakage. Status: pending provider fix, not fixed. `[P:203–213 → provider_legacy.py:384,507–508,527–557,589]`
- OPEN O4: UTC/UT1, leap seconds, TEME→ECEF, spherical-Earth error and threshold-near user-motion effects are not independently bounded end to end. Owner: stage 1/provider. Guard: an independent oblique moving-world geometry oracle at 10°/D2/ACM thresholds and time-grid refinement. `[A:138–148; FP:212–214]`
- Owner: provider plus stage-1 tape/action-contract maintainers.

## Stage 2 — Channel and fading

- Inputs/outputs — VERIFIED V8: the local engine implements transmit gain, S.465 receive gain, FSPL, nominal/realised channels, ACM constants and nominal coupled power; local sign and dB/linear conventions are consistent. `[E:149–171 → channel.py:109–145; acm.py:32–33,95–101; architectures.py:345–372]`
- Control/fading invariant — VERIFIED V9: controller powers use nominal geometry/interference; realised fading enters received fields only. `[E:149–171,291–297 → architectures.py:345–372]`
- Cross-channel identity — REFUTED→ R6: audited cross gains are keyed by aggressor NORAD, omit same-satellite distinct beams and can silently substitute zero; they do not represent the selected aggressor beam’s radiation. `[D:21–23,91–93 → provider_legacy.py:390,423–450; tapes.py:329–334]`
- Correction — DECIDED D8: key cross gains by physical aggressor `(NORAD, beam-chain)`, bind one colour to each beam-chain, include same-satellite P-10 interference and require a reciprocal reuse mask. Pending provider fix + stage 4. `[D-P items 1,11; D-E item 3]`
- Fading composition — REFUTED→ R7: current provider nominal gain already includes scintillation and then multiplies by V0.25 fading that includes it again. `[D:37–39; P:34–41,198–200 → link_budget.py:354–358; channel.py:240–244]`
- Provider correction — DECIDED D9: every P-audit trap/defect is FIX-or-REBUT with a non-tautological KAT; non-finite primitives fail closed, horizons are prefix-invariant, and dense NumPy tapes replace Python-object materialization. Status: pending provider fix. `[D-P items 6–11]`
- Receive-pattern wording — REFUTED→ R8: the legacy 2.4983° constant is wrong for the stated branch, but neither implementation actually holds peak receive gain below θ_min; the audited patterns are algebraically identical and the floor becomes active near 47.86°, not exactly 48°. `[P:114–124; E:142–145]`
- Guards — VERIFIED V10: independent S.465, transmit boresight/half-power, FSPL, Rician and shadow tests exist; cross-gain composition, keyed-fading composition and gaseous absorption lack independent production-path oracles. `[E:265–289 → test_channel_legacy.py:32–46]`
- OPEN O5: provider source/report/KAT completion and composed direct/cross-channel parity are unverified. Owner: provider/stage 2. Guard: K1–K13 from the provider audit, especially legacy interference parity, single-scintillation fade ratio, co-colour zero and cross-process determinism. `[P:154–186,225]`
- Owner: `channel.py`, provider, and the stage-4 engine integration.

## Stage 3 — Power, service, energy and integration

- Primary physics — VERIFIED V11: `a-r0` implements memoryless rate-target TDM, `r*=50 Mbit/s`, occupancy-dependent `Γ_r(n)`, capped coupled power from zero, residual certification, full-band TDM and post-resolution ACM service. `[E:149–170 → acm.py:95–101; architectures.py:278–294,345–372,644–714]`
- Failure invariant — VERIFIED V12: target-infeasible transmissions retain capped RF, interference, partial decodable bits and energy; non-converged solves are INVALID. `[E:149–169 → architectures.py:364–372; resolution.py:60–76]`
- Energy output — VERIFIED V13: TDM integrates `PA(p)` over actual slots; circuit is per active chain, baseband per active satellite, bus power is hard-zero, and 48 samples produce 47 intervals. `[E:173–190 → energy.py:87–159; integration.py:175–182]`
- PA invariant — REFUTED→ R9: “never `PA(Σp)`” is correct for TDM but false for FDM, where simultaneous user RF is summed before one beam-PA evaluation. `[D:176–182 → architectures.py:765–780]`
- Interruption treatment — REFUTED→ R10: H/SH are no-ops in the audited runner because no `InterruptionEvent` is constructed; ten settings duplicate non-H counterparts on the audited fixture. `[E:13–22 → run_v025_matrix_probe.py:273; adapter.py:156]`
- Interruption correction — DECIDED D10: derive 62/142 ms blackout events from each arm’s committed trajectory, union/clip once, and apply them to useful time without changing RF energy. Pending stage 4. `[D-E item 1; D-CD item 1]`
- Legality — REFUTED→ R11: boundary-0 legality is currently treated as sufficient; downstream `Geometry` cannot see later 10°/D2 transitions. Status: pending stage 4. `[D:33–35 → provider_legacy.py:362–390; tapes.py:318–345]`
- Standby inventory — DECIDED D11: P_idle sensitivity uses a declared 12-chain-per-satellite census; idle chains are `12−active beams`, never the horizon-dependent realisable-cell count. Pending stage 4. `[D-CD item 11]`
- Guards — VERIFIED V14: fixed-point, saturation, TDM/FDM bandwidth, PA, circuit/baseband and integration KATs are independently arithmetic; production interruption/live-legality paths remain uncovered. `[E:265–289 → test_energy_endpoint.py:127–138; test_architectures.py:247,291,336]`
- OPEN O6: the denominator is a declared payload-energy benchmark because bus/whole-constellation energy is excluded; ranking sensitivity is unbounded. Owner: controller/physics. Guard: seal the claim boundary or add a common-overhead sensitivity capable of detecting rank reversal. `[FP:195–200]`
- OPEN O7: PHY decodability and complete-service availability do not guard per-user throughput or rate-target attainment. Owner: controller/stages 3–8. Guard: predeclare and test a lower-tail throughput or target-attainment non-inferiority margin. `[FP:199–200]`
- OPEN O8: 47 subintervals define a grid, not accuracy at the claimed effect scale. Owner: integration. Guard: refine the time grid and threshold crossings until component contrasts change by less than a prespecified tolerance, suggested `<0.1 percentage point`. `[FP:212–214,286–289]`
- Owner: `architectures.py`, `resolution.py`, `energy.py`, `integration.py`.

## Stage 4 — Endpoint, reward, prices and calibration

- Endpoint — VERIFIED V15: both legacy and audited successor reducers compute pooled EE as `ΣB/ΣE`; bootstrap draws recompute the ratio after summing. `[C:64–70 → physical runner:878–904; matrix runner:898–916]`
- Merge invariant — REFUTED→ R12: current merge trusts `failure_analysis.arms` and does not independently rebuild summaries from sealed step rows. `[C:71–74; D:61–63 → matrix runner:1263–1279,1302–1327]`
- Current κ — VERIFIED V16: audited calibration defines `κ=B_ref/(U·T_ref)` in bits/(user·second), while C1/C2 use it as a bit normalization/penalty without multiplying by duration. `[B:69–77 → calibration.py:98; endpoint.py:143; targets.py:153,248]`
- OPEN O9: κ and Φ units remain inconsistent across sealed/audited sources; the stage-4 work order proposes `κ=B_ref/(U·N_ref)` and Φ in κ-bits, but no supplied `V025-CONTROLLER-DECISIONS-*` item seals that change. Owner: controller/stage 4. Guard: seal one dimensional contract and pass a symbolic-unit KAT through calibration, C1, C2, Φ and deployment.
- Price API — VERIFIED V17: successor target producers have no reachable default λ/η/κ path, although `reward_core` and the runner forecast path remain explicit but ungated. Defect status: explicit-default hazard fixed locally; integrated gate pending stage 4. `[E:192–202 → endpoint.py:112; targets.py:153–170,248–294]`
- Reward connection — REFUTED→ R13: exact `R=B−η_refE` arithmetic exists only on hand-built endpoints; the audited runner uses separate `CellScore`/`NetworkOutcome` paths and never exercises the trajectory identity. `[D:99; E:75–83 → endpoint.py:33–149; matrix runner:152–163]`
- Temporal endpoint — DECIDED D12: canonical per-step rows carry hex bits/joules and energy components, full-roster opportunities/served counts, prior/current physical identities, event type, Φ numerator/denominator and authority digests; merge reaggregates bit-for-bit. Pending stage 4. `[D-CD items 1,5,10]`
- QoS margins — DECIDED D13: FULL is non-inferior when the central-95% lower bound for complete-service availability exceeds −0.5 pp and upper bounds for relative handover rate and Φ-cost changes are below +5%. Pending stage 4. `[D-S2 item 6; D-CD item 3; V1.4 §2]`
- Calibration — DECIDED D14: authenticated `--calibrate` runs once; all 31 exact `η_ref=λ` and κ values are sealed in one immutable required file. Synthetic values are inadmissible. Pending stage 4/4b. `[D-S2 item 10]`
- Guards — VERIFIED V18: exact-rational endpoint and reward-core identity tests exist, but no production trajectory-to-reward test exists. `[E:192–202; D:99]`
- Owner: `endpoint.py`, `calibration.py`, stage-4 runner/merge.

## Stage 5 — C1/C2/C3 target construction

- Current C3 — REFUTED→ R14: audited code is pair-only and computes `e_i+Ψ/2`; this double-counts unilateral effects already present in whole-network C1 and can credit an unselected partner. `[B:120–126; D:41–43 → targets.py:307–335; matrix runner:496–542]`
- Target decomposition — DECIDED D15: for changed set `A`, define unilateral increments `d_i`, interaction residual `Ψ_A=F(a_A)−F(a⁰)−Σd_i`, `C1=Σd_i(+Φ)`, `C3=Ψ_A`, and C2 as continuation excluding the immediate term; require `C1+C3=F(a_A)−F(a⁰)`. Pending stage 4b. `[V1.5 §2]`
- Factor arms — DECIDED D16: FULL=`C1+C2+C3`; each DROP removes one additive term inside the same selector class/catalogue; joint search remains in DROP_C3; exact-F is a ceiling, not a factor arm. Pending stage 4/4b. `[D-E item 2; V1.5 §2]`
- C2 execution — REFUTED→ R15: current forecasts use realised future profiles, network-wide rather than focal survival, capped power, and a zero-bits surrogate after INVALID. `[D:45–47 → matrix runner:287–296,388–418]`
- C2 correction — DECIDED D17: forecasts use nominal geometry/interference only; survival is focal; INVALID propagates; negative uncapped required-power margins remain reportable. Pending stage 4. `[D-CD item 9]`
- Guards — VERIFIED V19: C1/C2/C3 arithmetic fixtures exist, but use hand-built values; the current C3 test asserts the superseded e-inclusive formula and no physics-to-label parity guard exists. `[D:101–104; E:273–287]`
- OPEN O10: the exact larger-set interaction game and Shapley allocation require a dummy-user/share-conservation definition; “equal share” is not generally Shapley. Owner: stage 5/controller. Guard: asymmetric three-user fixture where a dummy receives zero and credits sum exactly to `Ψ_A`. `[FP:202–204]`
- OPEN O11: C2’s unit, overlap and finite-horizon accounting are not sealed sufficiently to prove future value is counted once. Owner: stages 4–6. Guard: three-step exhaustive fixture with a future outage and explicit no-double-count reconstruction. `[FP:206–210]`
- Owner: `targets.py`, stage-4b target parity suite.

## Stage 6 — Source tapes and training data

- Pipeline identity — REFUTED→ R16: the v0 map conflates online homogeneous 112-D MODQN transitions with heterogeneous Catfish 228-D/448-D pair rows. Catfish source rows do not enter `ReplayBuffer`. `[B:5–13,25–32,155–164 → replay_buffer.py:30; heterogeneous trainer:239]`
- Legacy path — VERIFIED V20: authenticated replay-generated JSON becomes typed Q1/Q2 pair batches; training is direct pairwise regression with zero next-state bootstrap. `[B:25–57 → generate_v023_c1c2_targets.py:1241; heterogeneous trainer:239]`
- Successor schema — REFUTED→ R17: the 21-field object is C2-only, lacks `missing_incumbent`, and has no production source-builder, learner or deployment consumer. `[B:109–118,163–176 → state_v025.py:1,18,131–171]`
- Current guard state — VERIFIED V21: schema tests check shape/hash/finiteness and price presence only; no tape→row extraction or schema-to-information sufficiency test exists. `[B:170–179; D:104–106]`
- Information contract — DECIDED D18: before successor training, stages 6–8 must state exactly what each head observes and what the coordinator computes, including candidate identity, load, capacity/interference, activation and proposed/joint actions. Pending stage C. `[V1.5 §6]`
- Estimands — DECIDED D19: oracle factor arms and learned neutral-source ablations are separate experiments and schemas; neither may be reported as the other. Pending stage C. `[D-CD item 13]`
- OPEN O12: hidden episode-start ages can change legacy C1 labels while visible Q1 states remain identical. Owner: stages 0/3/6. Guard: identical-visible-state/different-hidden-age fixture must give identical successor targets or fail a dependency allowlist. `[B:17–23 → step.py:500,754; ee_axis_ops3_live.py:303]`
- OPEN O13: successor Q1 fields, row producer, shard schema, physical-key/timestamp semantics, masks, NOOP/outage retention and provenance are absent. Owner: stage C. Guard: one golden tape-to-row-to-shard fixture covering every legal action and missing incumbent. `[B:170–187]`
- OPEN O14: neutral-source construction, deterministic/minibatch epoch semantics, checkpoint contents/cadence and resume authentication are unsettled. Owner: stage C. Guard: matched-strata digest test plus checkpoint/resume equivalence at an exact update boundary. `[B:99–107,128–144,181–184]`
- Owner: future `stagec_v025` source/state/shard modules.

## Stage 7 — Learner and deployment

- Learner identity — REFUTED→ R18: generic `modqn.py` has independent per-head Bellman maxima, but deployed Catfish Q1/Q2 are separate heterogeneous regressors and do not bootstrap. `[B:90–97,161–162 → modqn.py:536–544; heterogeneous trainer:272,306]`
- Legacy learner — VERIFIED V22: Catfish Q1/Q2 use zero-bootstrap pair regression; a future Bellman learner would require one scalarized legal next action shared across heads. `[B:90–97]`
- Action invariant — REFUTED→ R19: independent masked per-user argmax makes each user action legal but does not guarantee a jointly feasible physical profile. `[B:155–167]`
- DROP semantics — REFUTED→ R20: legacy DROP arms substitute neutral-source training while retaining and updating every head; they do not remove the head at deployment. `[B:99–107 → five-arm orchestrator.py:52,376]`
- Scale — VERIFIED V23: legacy deployed Q1 and Q2 are both normalized by κ and directly summed; Q1 is not raw bits. `[B:79–88 → heterogeneous trainer:265,306; ee_axis_lcsrs_three_route.py:380]`
- Learned-ablation contract — DECIDED D20: successor scientific comparisons use retrained neutral-source ablations; checkpoint knockouts, if reported, are separate reliance diagnostics. Pending stage C. `[V1.5 §6; D-CD item 13]`
- Deployment manifest — DECIDED D21: every set-level arm must declare information, catalogue, service guard, deadline, worker count and deterministic BASE fallback. Pending stage C/stage 4 timing integration. `[V1.5 §6; D-CD item 12]`
- OPEN O15: no implemented successor adapter connects state/labels to learner, common action, set coordinator and closed-loop deployment. Owner: stage C. Guard: tiny end-to-end training slice with opposite joint-interaction signs and an additive C3 placebo. `[B:170–187; FP:286–293]`
- OPEN O16: sources disagree on learner initialization count: V1.0 specifies three; the v0 map says five, and audit B found no implemented successor seed contract. Owner: controller/stage C. Guard: seal the exact lineage list and verify common initialization/source digests within each lineage. `[B:128–136,167,184 → astra round-3 contract:199]`
- OPEN O17: exact set evaluation assumes global geometry, legal actions, cross-gains and enough computation before 30.08 s; audited timers exclude proposal/forecast/selection work. Owner: stages 4/7. Guard: authenticated real-provider deadline KAT covering the entire decision path and atomic BASE fallback. `[B:146–153; D:69–71]`
- Owner: stage-C learner/orchestrator/deployment adapter.

## Stage 8 — Evaluation, statistics and claim

- Current runner — REFUTED→ R21: the audited physics matrix is 12 arms × 4 worlds across 31 settings, with three default anchors; it is not the prospective 6-arm × learner-seed × confirmation-world runner. `[C:101–110,182–185 → matrix runner:93–107,1302–1308]`
- Primary scope — DECIDED D22: `a-r0` alone controls PHYSICS-GO and the conditional claim; the other 30 settings are exploratory sensitivities and cannot change admission. `[V1.5 §1]`
- Confirmation population — DECIDED D23: claim dates must be unused by successor probe, calibration, rehearsal, KAT and synthetic-real development; legacy overlap is disclosed. `[V1.5 §4; D-A item 1]`
- Uncertainty — DECIDED D24: learner experiments use a two-way pigeonhole bootstrap over dates×learner seeds, pairing arms and recomputing `ΣB/ΣE`; the learner-free physics matrix uses one-way date bootstrap. `[V1.5 §3]`
- Existing estimator — VERIFIED V24: the audited reducer correctly recomputes the pooled EE ratio inside each draw, while paired log-EE is explicitly supplementary. `[C:64–70,186–188 → matrix runner:898–916,939–944]`
- Merge — REFUTED→ R22: current merge authenticates self-consistent files but trusts summaries and does not bind an independent launch/provider/world/calibration authority. `[C:64–85; D:61–63 → matrix runner:1242–1337]`
- Merge correction — DECIDED D25: rebuild every statistic from canonical step rows and reject summary disagreement, missing arms/anchors, authority mismatch or incomplete provenance. Pending stage 4/stage C. `[D-CD item 5]`
- Receipts — REFUTED→ R23: existing harness receipts are inconsistent and omit enough temporal/event detail to prevent exact independent reaggregation. `[C:76–86 → matrix runner:679–703; legacy Stage-C:767–857]`
- Attempt control — DECIDED D26: append `STARTED` before any outcome-producing call to a controller-owned hash-chained registry; merge rejects duplicates and unadjudicated abandonment. Pending stage 4/stage C. `[D-CD item 2]`
- Harness controls — REFUTED→ R24: no audited harness has all four claimed controls—complete NULL≡BASE, real-step all-arm dry-run, immediate write-once SHA receipt and complete authority. `[C:112–127]`
- Conformance correction — DECIDED D27: every comparative harness must pass one shared four-control conformance suite before opening outcomes. Pending stage 4/stage C. `[D-CD item 7]`
- Rerun claim — REFUTED→ R25: path-local write-once files do not prevent multiple roots or outcome-selected reruns. `[C:31–39,198 → matrix runner:1216–1234,1355–1438]`
- Margin/interval rule — DECIDED D28: EE margin is relative, `EE_FULL/EE_DROP−1≥0.5%`; intervals are central 95% percentile intervals with NumPy’s default linear quantile interpolation and strict corresponding endpoint gates. `[V1.4 §§1–2]`
- Zero outcomes — DECIDED D29: zero-bit/all-dark draws remain undefined for ratio/log supplements, are counted and reported, and cannot be silently replaced; the sealed analysis must name the disposition. `[D-CD item 3]`
- Terminal decision — REFUTED→ R26: current merge emits completion plus a Boolean, not an experiment-global terminal authority, and does not implement the full admission certificate. `[C:191; D:153–162]`
- Admission — DECIDED D30: executable admission uses `a-r0` only and emits each physics/integrity, U1/J1, S0, numerical-error, QoS and FULL−DROP certificate. Pending stage 4b/stage C. `[V1.5 §1; D-E item 2]`
- Statistical claim — VERIFIED V25: a single prespecified global intersection–union assertion that all three conditional contrasts pass does not require multiplicity correction; separate discoveries or selected sensitivity cells would. Evidence remains TRAIN-only. `[C:168–176; FP:248–254]`
- OPEN O18: the exact confirmation panel, six-arm learned runner, allocation manifest and transitive physics/endpoint identity do not exist. Owner: stage C/controller. Guard: synthetic claim-plan test asserting exact arms, fixed learner lineages, full world allocation, shared physics digest and terminal adjudication. `[C:101–110,182–194]`
- OPEN O19: zero comparator rates/costs and final permissible wording are not sealed; no final runner/report proves TRAIN-only conditional wording. Owner: stage 8/reporting. Guard: report-schema test that forbids generalization, selected-cell or component-wise claims and defines zero-denominator comparisons. `[C:168–176; D:65–67]`
- Owner: stage-C evaluation runner/merge; controller owns allocation, attempts and terminal authority.

## Cross-cutting invariants

1. DECIDED D31 — Constants and units carry provenance labels; synthetic `r*`, energy costs, 10° visibility, timing and hardware counts must not be presented as validated operational facts. `[V1.2 §7; D-P item 2]`
2. REFUTED→ R27 — `(NORAD, beam-chain)` is not currently used everywhere; audited cross gains remain NORAD-keyed. Corrected invariant is physical identity end to end, pending provider fix/stage 4. `[D:176–182 → tapes.py:118–120,329–334]`
3. DECIDED D32 — One 0.640 s clock, explicit left/right discontinuities, left-endpoint T treatment and 47-interval integration govern tapes through endpoints. `[D-S1 items 3,7; D-CD items 8,12]`
4. DECIDED D33 — λ/η/κ are explicit at every producer/consumer; missing or mismatched prices fail closed. `[D-S1 item 18; D-S2 item 10]`
5. DECIDED D34 — TRAIN membership and role allocation are authenticated at construction; `world_seed` and `learner_seed` are distinct; exogenous tapes are CRN-paired across arms. `[D-A items 2–4,7]`
6. DECIDED D35 — NULL placebo, real-step dry-run, immediate receipt sealing, authority verification and pre-outcome attempt registration are mandatory for every harness. `[D-CD items 2,7]`
7. DECIDED D36 — Priority, constants, margins, catalogue, allocation, estimator, concurrency and thinning are sealed before outcomes; only `a-r0` is confirmatory. `[V1.5 §§1,3–5; D-CB items 3–5]`
8. OPEN O20 — Multiple hashes do not yet form one exercised transitive manifest. Owner: controller/process. Guard: miniature provider→target→training→deployment→receipt run where corruption of split/component/provider authority must fail before outcome use. `[FP:286–293]`

## Appendix A — Audit-D user-step arrow trace with decision-updated guards

OPEN O22 — The requested “22-arrow” trace is labelled `A0` through `A22` in audit D, which is 23 rows. All source-labelled rows are retained. Owner: controller/docs. Guard: confirm whether one row is metadata or renumber the canonical trace. `[D:85–109]`

| Arrow | Current handoff and audit evidence | Guard after controller decisions |
|---|---|---|
| VERIFIED V26 — A0 domain→epoch | Domain→63-bit seed→aware UTC. `[D:87 → tapes.py:42–49; provider.py:163–173]` | Existing seed-domain test; DECIDED shared factory/allocation attestation `[D-A items 3–7]`. |
| VERIFIED V27 — A1 TLE→satellite set | Nearest per-NORAD element, age checked at start. `[D:88 → ephemeris.py:97–158]` | No existing provider source/age guard; DECIDED mandatory TLE hashes and non-causal convention `[D-A items 3,5]`. |
| VERIFIED V28 — A2 world→48-boundary geometry | Candidate identity and `step·30.08+k·0.640`. `[D:89 → provider.py:344–396; tapes.py:198–207]` | Existing satellite k=17/47 KAT; planned moving-user/seam/D2 oracle in provider fix. |
| REFUTED→ R28 — A3 world→inventory | Current inventory is horizon-derived Cartesian satellite×cell, not physical hardware. `[D:90; P:201 → provider.py:253–284]` | DECIDED realisable candidate inventory plus separate 12-chain standby census `[D-P item 9; D-CD item 11]`. |
| REFUTED→ R29 — A4 geometry→channels | Current victim rows carry aggressor-NORAD gains and may double scintillation. `[D:91; D:21–39 → provider.py:398–450]` | DECIDED per-chain gains, single scintillation owner, co-colour/P-10 parity KATs `[D-P items 1,11]`. |
| VERIFIED V29 — A5 candidates→carrier action | User→beam-or-None at boundary zero. `[D:92 → tapes.py:375–407]` | No exact carrier retention guard; DECIDED zero-legal user gets explicit null action `[D-E item 4]`. |
| REFUTED→ R30 — A6 assignment+cross→Geometry | Current selected aggressor lookup can omit/wrongly identify interference and only checks initial legality. `[D:93 → tapes.py:297–350]` | DECIDED per-chain fail-closed lookup and boundary-live legality `[D-P item 1; D-CD item 8]`. |
| VERIFIED V30 — A7 Geometry→powers | Capped coupled radiation with residual certificate. `[D:94 → architectures.py:319–385,644–714]` | Existing coupled-solve KAT; planned real composed-link oracle `[D-E item 5]`. |
| VERIFIED V31 — A8 power→ACM/service | SINR, ACM rate, PHY and target flags. `[D:95 → acm.py:47–61,77–118; resolution.py:54–91]` | Existing infeasible-cap KAT; DECIDED distinct full-roster service fields `[D-CD item 10]`. |
| VERIFIED V32 — A9 radiation→energy | PA/circuit/standby/baseband joules with device deduplication. `[D:96 → energy.py:87–159]` | Existing TDM/FDM energy KAT; DECIDED 12-chain standby census `[D-CD item 11]`. |
| REFUTED→ R31 — A10 transition→blackout | Event types exist but runner supplies no committed-history conversion. `[D:97; E:13–22 → integration.py:70–99]` | DECIDED temporal five-kind ledger and H/SH discriminator `[D-CD item 1; D-E item 1]`. |
| VERIFIED V33 — A11 boundaries→integrated result | Boundary rates/power→bits/J/user-seconds. `[D:98 → adapter.py:118–176; integration.py:165–197]` | Existing injected-event integration test; DECIDED production discontinuity wiring `[D-S1 item 7; D-CD item 8]`. |
| REFUTED→ R32 — A12 integration→endpoint/reward | Runner and endpoint library are disconnected; full-roster/service semantics differ. `[D:99 → matrix runner:152–163; endpoint.py:33–149]` | DECIDED canonical rows, roster and independent reward/reaggregation KAT `[D-CD items 5,10]`. |
| VERIFIED V34 — A13 reference→calibration | Formula produces `η=λ`, κ and setting binding, but only from supplied totals. `[D:100 → calibration.py:203–235]` | Existing deterministic arithmetic test; DECIDED authenticated one-time calibration freeze `[D-S2 item 10]`. |
| VERIFIED V35 — A14 outcomes→C1 | Local arithmetic creates whole-network surplus plus Φ. `[D:101 → targets.py:153–170]` | Existing hand-built test; DECIDED v1.5 reconstruction identity and production parity KAT. |
| REFUTED→ R33 — A15 assignments→C2 | Current evaluator leaks realised future fields, misdefines survival and substitutes after INVALID. `[D:102; D:45–47]` | DECIDED nominal-only, focal-survival, INVALID-propagating forecast KATs `[D-CD item 9]`. |
| REFUTED→ R34 — A16 coalitions→C3 | Current code is pair-only and e-inclusive. `[D:103 → targets.py:307–335]` | DECIDED interaction-only set decomposition and asymmetric Shapley KAT `[V1.5 §2]`. |
| VERIFIED V36 — A17 outputs→21-field state | C2 encoder normalizes supplied values but binds no world/user/action/time identity. `[D:104 → state_v025.py:131–171]` | Existing shape/finiteness test only; OPEN O13 golden extraction test required in stage C. |
| OPEN O13 — A18 state/labels→shards | No successor producer or transition schema. `[D:105]` | Planned stage-C shard schema and round-trip provenance mutation tests. |
| OPEN O15 — A19 shards→learner→joint action | No successor learner/decoder path. `[D:106]` | Planned stage-C tiny training slice, common-action/joint-feasibility and DROP-retains-heads KATs. |
| VERIFIED V37 — A20 profiles→unit receipt | Current writer is write-once but incomplete semantically. `[D:107 → matrix runner:961–1027,1216]` | DECIDED canonical rows, authority digests, conformance and attempt registry `[D-CD items 2,5,7]`. |
| REFUTED→ R35 — A21 receipts→cluster inputs | Merge trusts summaries and misnames world seed as learner seed. `[D:108 → matrix runner:1242–1337]` | DECIDED raw-row reaggregation, separate seed fields and within-cell pooling `[D-CD items 3,5]`. |
| REFUTED→ R36 — A22 cluster inputs→claim | Current output is a four-world physics-probe Boolean, not the final learned claim. `[D:109 → matrix runner:864–945,1283–1297]` | DECIDED `a-r0`-only admission, two-way learner bootstrap and stage-C terminal authority `[V1.5 §§1,3; D-CD item 13]`. |

## Ranked OPEN list — controller to-do

1. O9 — Seal dimensionally coherent κ and Φ units; block target generation until the unit KAT passes.
2. O15 — Complete the successor state→learner→joint-deployment path and synthetic vertical slice.
3. O13 — Freeze Q1/Q2/C3 row and shard schemas with causal extraction semantics.
4. O5 — Complete provider FIX/REBUT report and independent composed channel/interference KATs.
5. O18 — Implement and seal the final learned confirmation runner and exact panel.
6. O12 — Eliminate or expose hidden episode-start state affecting labels.
7. O10 — Freeze the larger-set interaction game and genuine Shapley allocation.
8. O11 — Freeze C2 finite-horizon units and no-double-count temporal semantics.
9. O17 — Prove whole-decision deadline compliance with the real provider and BASE fallback.
10. O7 — Add a rate/throughput service guard or narrow the claim explicitly to PHY service.
11. O1 — Seal the allocation manifest and role-wise date separation before any claim outcome.
12. O20 — Bind all code/data/provider/calibration/analysis authorities through one exercised transitive manifest.
13. O3 — Make the shared world factory the only production path and prove no TEST file is opened.
14. O2 — Remove or authenticate horizon/panel-prefix dependence in world identity.
15. O8 — Establish time-grid convergence below the claimed effect scale.
16. O6 — Declare payload-only EE or bound omitted whole-constellation energy.
17. O14 — Freeze neutral-source, epoch, checkpoint and resume contracts.
18. O16 — Resolve three versus five learner initializations and seal exact lineage domains.
19. O19 — Define zero-denominator comparisons and enforce permissible TRAIN-only report wording.
20. O4 — Bound UTC/frame/user-motion errors with an independent geometry oracle.
21. O22 — Resolve the Audit-D trace count: “22 arrows” versus labels A0–A22.
22. O21 — Clarify whether Stage 0 is outside the stated eight-stage count.

MAP: VERIFIED=37 REFUTED=36 DECIDED=36 OPEN=22