# Pipeline audit A — worlds, splits, seeds, panels

VERIFIED — Scope covered stages 0–1, their successor successor-provider handoff, and the resulting evaluation-unit design. TheVERIFIED — I used read-only source inspection and deterministic schedule enumeration enumeration only; I ran no simulations or test suites.  
VERIFIED — The provider files are untracked WIP, so provider findings findings describe their state at audit time.  
VERIFIED — The research workflow’s independent pass confirmed the provider’s split-attestation and seed-semantics findings.

## Ranked findings

### 1. BLOCKER — [NEW CORE RISK 1/5] Domain-fresh worlds are not date-fresh-l oneself independent evaluation worlds

- Assumption — INFERRED: distinct seed domains are being treated as sufficient separation between calibration probe probe, calibration, training/development, and evaluation.
- Where — VERIFIED: V0.25 separates only 
  `V025_PROBE/world/{1..4}` and `V025_CAL/world/{1..2}` only by domain string names [tapes.py:36](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:36); calibration separation compares only only compares domain sets [calibration.py:257](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/calibration.py:257).
- Evidence — VERIFIED: the six current V0.25 worlds land on distinct TRAIN dates: probes `2026-01-07`, `2026-03-11`, `2025-11-16`, `2026-03-28`; calibrations `2026-01-09`, `2026-01-22`.
- Evidence — VERIFIED: the legacy 9,000-world schedule visits all 166 TRAIN dates, so every current probe/calibration date has already appeared at the date level in that ladder. The schedule is consecutive seeds [world-plan.py:87](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/build_v023_c1c2_successor_world_plan.py:87), sampled uniformly over available TRAIN dates [ephemeris.py:382](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/ephemeris.py:382).
- Evidence — UNKNOWN: no successor source/training-world manifest exists yet, so actual successor train-versus-final-evaluation date overlap cannot be counted.
- What breaks — INFERRED: “fresh world seed” does not establish held-out orbital conditions. A learner can be evaluated on different users/fading while seeing the same TLE-date regimes during development.
- Guard — INFERRED: seal role-specific manifests and assert disjoint `(TLE date, purpose)` sets for confirmation, or explicitly limit the result to TRAIN-development evidence. Domain-set inequality is insufficient.
- Owner — INFERRED: stages 0, 6, and 8.

### 2. BLOCKER — [NEW CORE RISK 2/5] The implemented “training seed” is a world seed, and `(date, seed)` cells are not independent clusters

- Assumption — VERIFIED: the map declares the uncertainty unit as TLE date × training seed [pipeline map:61](/home/sat/mcrl-v023-codex-audits/END-TO-END-PIPELINE-MAP-2026-09-08.md:61).
- Where — VERIFIED: the provider stores the physical `world_seed` in `_WorldState.training_seed` and returns it as the cluster seed [provider_legacy.py:335](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:335), [provider_legacy.py:354](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:354).
- Where — VERIFIED: the probe merger rejects repeated `(date, training_seed)` instead of aggregating worlds within a cluster [run_v025_matrix_probe.py:1251](/home/sat/mcrl-v025-stage2-snapshot-20260908/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1251), then submits each world row directly to the bootstrap [run_v025_matrix_probe.py:1262](/home/sat/mcrl-v025-stage2-snapshot-20260908/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1262).
- Finding — VERIFIED: because every physical world seed is unique, the current “cluster bootstrap” is operationally a world bootstrap even when several worlds share a TLE date.
- Finding — INFERRED: the proposed five learner initializations and roughly 161 dates form crossed dependence: worlds sharing a trained model are correlated across dates, and worlds sharing a date are correlated across learner seeds. Their Cartesian cells are not approximately 805 independent clusters.
- What breaks — INFERRED: confidence intervals can be materially too narrow, and five training seeds can be disguised as thousands of independent units.
- Guard — INFERRED: carry learner-lineage seed separately from world seed; aggregate all worlds by the declared cell; use two-way/multiway resampling over learner seed and TLE date, with arms paired inside each resample.
- Owner — INFERRED: stages 2 and 8.

### 3. BLOCKER — [NEW CORE RISK 3/5] TRAIN provenance is enforced inside one provider but not authenticated across the provider/tape seam

- Assumption — VERIFIED: the map says TRAIN-only is asserted at world construction [pipeline map:71](/home/sat/mcrl-v023-codex-audits/END-TO-END-PIPELINE-MAP-2026-09-08.md:71).
- Where — VERIFIED: the WIP legacy provider rejects forced TEST/embargo starts and wraps archive loads with a TEST-file refusal [provider_legacy.py:118](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:118), [provider_legacy.py:163](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:163).
- Where — VERIFIED: it also exposes TLE filenames and hashes through `tle_binding` [provider_legacy.py:358](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:358).
- Handoff defect — VERIFIED: `PrimitiveWorldProvider` has no split or TLE-binding method [tapes.py:353](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:353). `build_world_tape` accepts the provider’s date, then hardcodes `"TRAIN"` [tapes.py:420](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:420), [tapes.py:446](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:446).
- Handoff defect — VERIFIED: the manifest contains neither exact start UTC nor TLE input hashes; it records only date and the misnamed seed [tapes.py:277](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:277).
- What breaks — INFERRED: an installed provider can supply TEST-derived or differently frozen geometry that the tape relabels TRAIN, while still producing a valid digest.
- Guard — INFERRED: make split identity, exact start UTC, archive/file hashes, split-rule digest, and provider-source digest mandatory protocol outputs; recompute and reject the manifest before any unit opens.
- Owner — INFERRED: stages 0–2/provider seal.

### 4. HIGH — Named runners are TRAIN-only, but the unqualified “TEST is never read” map claim is too broad

- Definition — VERIFIED: the active split is a 16-day cycle: seven TRAIN, one embargo, seven TEST, one embargo, anchored on the archive’s first date [ephemeris.py:182](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/ephemeris.py:182), [ephemeris.py:255](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/ephemeris.py:255).
- Counts — VERIFIED: the 373-file archive yields 166 TRAIN, 160 TEST, and 47 embargo files, with a minimum TRAIN–TEST calendar gap of two days. The split tests cover disjointness and the gap [test_w02_split.py:99](/home/sat/mcrl-v023-codex-ws-c3s-baselines/tests/test_w02_split.py:99), [test_w02_split.py:119](/home/sat/mcrl-v023-codex-ws-c3s-baselines/tests/test_w02_split.py:119).
- Named paths — VERIFIED: generic training constructs a TRAIN sampler [training_pipeline.py:736](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/training_pipeline.py:736); C3-S does likewise [run_v023_c3s_screen.py:881](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:881); E1 delegates to the same F1 server environment [run_v023_c3_existence_e1.py:1848](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:1848); the 9,000 runner verifies its sampler is the frozen TRAIN sampler [physical runner:1227](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:1227).
- Answer — VERIFIED: none of the named canonical C3-S, E1, 9,000-ladder, V025 probe, or V025 calibration paths reaches a TEST start date.
- Escape path — VERIFIED: `ScenarioDriver.reset(start_utc, …)` checks only timezone awareness and performs no split check [scenario.py:141](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/scenario.py:141). Direct callers can therefore run a TEST date.
- Guard coverage — VERIFIED: sampler-level and one provider forced-TEST test exist [test_w02_split.py:192](/home/sat/mcrl-v023-codex-ws-c3s-baselines/tests/test_w02_split.py:192), [test_provider_legacy.py:213](/home/sat/mcrl-v025-codex-ws-provider/tests/physics_v025/test_provider_legacy.py:213).
- Guard coverage — UNKNOWN: no single test enumerates every production runner and proves that its realized starts and all opened TLE files remain non-TEST.
- What breaks — INFERRED: a new direct runner can silently bypass the split while emitting a receipt that merely says `test_split_opened:false`.
- Guard — INFERRED: a shared world factory should be the only production entry point; record and validate every realized start date and opened source file.
- Owner — INFERRED: stage 0/runtime and provider.

### 5. HIGH — [NEW CORE RISK 4/5] Nearest TLE selection is causal look-ahead and the 24-hour ceiling applies only at the start

- Rule — VERIFIED: selection minimizes absolute epoch distance per NORAD over source files dated `date−1`, `date`, and `date+1`, then drops records older than 24 hours [ephemeris.py:97](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/ephemeris.py:97).
- Rule — VERIFIED: future epochs are intentionally permitted as “backward extrapolation” [ephemeris.py:111](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/ephemeris.py:111).
- Data effect — VERIFIED: read-only inspection of the six current V025 starts found 38%–89% of retained records had epochs later than the simulated start.
- Split nuance — VERIFIED: the provider refuses TEST-named files, but TRAIN starts may open adjacent embargo files; current probe 3 and calibration 1 also retained embargo-epoch records.
- Boundary effect — VERIFIED: element selection occurs once at reset [scenario.py:154](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/scenario.py:154), and the provider propagates that fixed set for the whole tape [provider_legacy.py:8](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:8). Each 0.640-second boundary changes age but never reselects.
- Ceiling defect — VERIFIED: the guard is evaluated only at the initial instant. Over a canonical 900-second provider world, current probe 3 ends with one selected record older than 24 hours and calibration 1 with seven.
- What breaks — INFERRED: future records leak information unavailable to a causal online predictor; the advertised maximum age is false if interpreted as a per-boundary invariant.
- Guard — INFERRED: declare past-only versus absolute-nearest causality; assert signed epoch offset and maximum age at every emitted boundary, or explicitly rename the rule “≤24 h at selection time.”
- Owner — INFERRED: stages 0–1/provider.

### 6. HIGH — The successor’s forward tape does not repair the inherited D2 prime seam

- Legacy defect — VERIFIED: typical warm-up samples occur at `t−1.28` and `t−0.64` [scenario.py:184](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/scenario.py:184). Step 0 then processes 47 samples from `t−29.44` through `t` [scenario.py:313](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/scenario.py:313), [scenario.py:343](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/scenario.py:343).
- Legacy defect — VERIFIED: tracker index advances from −1 to 0 while physical time jumps backward by 28.80 seconds; compared with adding only the new `t` sample after priming, step 0 performs 46 extra D2 updates.
- Successor clock — VERIFIED: `StepTape` correctly requires 48 boundaries forming 47 forward intervals, `t+k·0.640`, `k=0..47` [tapes.py:192](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:192).
- Handoff result — VERIFIED: provider boundary 0 takes its D2 latch/TTT values from the legacy decision state, then advances forward inside the tape [provider_legacy.py:380](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:380), [provider_legacy.py:574](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:574).
- Answer — VERIFIED: forward geometry avoids a time reversal inside the successor tape, but the initial D2 state already contains the legacy prime-seam contamination. The basic defect is not avoided.
- What breaks — INFERRED: step-0 eligibility and TTT credit can differ from a monotonically primed D2 reference and can influence all arms through the shared tape.
- Guard — INFERRED: construct an independent monotonic oracle over `… t−1.28, t−0.64, t, t+0.64 …`; compare every boundary latch and elapsed counter, especially step 0.
- Owner — INFERRED: stage 1/provider.

### 7. HIGH — [NEW CORE RISK 5/5] “World = (TLE date, world seed)” is not a complete legacy identity

- Horizon dependence — VERIFIED: legacy satellite shortlisting depends on `steps_per_episode ××30.08` [scenario.py:161](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/scenario.py:161). Thus the same seed under 10-step and 30-step runners need not yield the same tracked universe.
- Provider mitigation — VERIFIED: current WIP provider forces the canonical 30-step universe regardless of a shortened request [provider_legacy.py:149](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:149).
- History dependence — VERIFIED: `StepEnvironment._age_rng` is spawned once and persists across episode resets [step.py:414](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/step.py:414), [step.py:526](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/step.py:526).
- History dependence — VERIFIED: the 9,000 runner restores that stream from the preceding episode [physical runner:1253](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:1253). A world executed alone can therefore have different initial segment ages from the same seed at its scheduled panel position.
- What breaks — INFERRED: replay, deduplication, and “same world” comparisons are wrong unless identity includes runner configuration, horizon/universe rule, and persistent-prefix state or panel position.
- Guard — INFERRED: require “world B alone = world B after world A” for every physical field, or remove prefix state from world construction; compare 10/30/31-step common prefixes.
- Owner — INFERRED: stages 0–1/runtime and provider.

### 8. MEDIUM — Seed namespaces are mostly separated, but the pipeline is not domain-only and one panel is knowingly reused

- Rule — VERIFIED: V0.25 and C3-S use `sha256(ASCII domain)[:8]`, big-endian, masked to 63 bits [tapes.py:42](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:42), [run_v023_c3s_screen.py:169](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:169).
- Inventory — VERIFIED: the V0.25 probe/calibration seeds, C3-S seeds, and the consecutive 9,000 range have no numeric seed collision.
- Inventory — VERIFIED: current probe and calibration dates are mutually distinct, so those six worlds do not duplicate each other as `(date, world seed)`.
- Counterexample — VERIFIED: the 9,000 plan uses arithmetic seeds `2026090600+k`, not domains [world-plan.py:94](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/build_v023_c1c2_successor_world_plan.py:94).
- Reuse — VERIFIED: its first 100 seeds exactly equal the earlier 100-world DROP-C3 panel [dropc3 server:32](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-physical/run_v023_dropc3_evaluation_server.py:32).
- Distinction — VERIFIED: lineage seeds `2026092101–03` are learner/checkpoint seeds, not physical-world seeds; the provider currently conflates these concepts.
- What breaks — INFERRED: a future collision check limited to domain-derived inventories misses arithmetic allocations and repeated opened panels.
- Guard — INFERRED: maintain one authenticated global ledger of `(purpose, domain/formula, numeric seed, exact start UTC, date, lineage)` and reject unapproved reuse.
- Owner — INFERRED: stages 0, 6, and 8.

### 9. MEDIUM — User layout is deterministic only under a larger frozen contract; motion is stepwise

- Initial layout — VERIFIED: 100 users are uniformly scattered in a 200×90 km rectangle and assigned random headings from the dedicated mobility RNG [mobility.py:44](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/mobility.py:44), [mobility.py:96](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/mobility.py:96).
- Seed dependence — VERIFIED: canonical evaluation creates independent child-0 epoch and child-1 mobility streams [training_pipeline.py:868](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/training_pipeline.py:868). Under frozen code/configuration, initial layout and subsequent mobility path are determined by the world seed.
- Qualification — VERIFIED: the layout is not mathematically a function of the integer alone; it also depends on NumPy RNG behavior, mobility constants, user ordering, and code version.
- Motion — VERIFIED: users move 0.2506667 km per 30.08-second step with bounded random turns and reflection [mobility.py:117](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/mobility.py:117).
- Grid — VERIFIED: the cell grid is deterministic, earth-fixed, and independent of the seed [cells.py:125](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/cells.py:125). Its fixed 483 km sizing gives radius 13.9976 km [scenario.py:53](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/scenario.py:53), [cells.py:55](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/cells.py:55).
- Handoff gap — VERIFIED: the tape schema publishes only the initial latitude/longitude layout and derived candidate quantities, not per-boundary user/satellite ECEF or off-axis angles [tapes.py:89](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:89), [tapes.py:103](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:103).
- Approximation — VERIFIED: the provider holds a user fixed across each step’s 48 boundaries and jumps to the moved position between steps [provider_legacy.py:380](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:380).
- What breaks — INFERRED: independent consumers cannot audit raw boundary geometry from the detached tape; seam continuity is one-sided rather than a single physical state.
- Guard — INFERRED: bind per-step user coordinates and raw geometry digests; assert the declared zero-order-hold convention and the permitted 0.2506667 km seam displacement.
- Owner — INFERRED: stage 1/provider.

### 10. MEDIUM — N=4 is refresh cadence only; action validation imposes no residence duration

- Assumption — VERIFIED: `DwellConfig.steps=4`; only `step_index % 4 == 0` reanchors the cell mapping [dwell.py:60](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/dwell.py:60), [dwell.py:156](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/dwell.py:156).
- Action semantics — VERIFIED: validation checks only the current mask or mandatory no-op; it has no age, lock, or minimum-residence condition [action_contract.py:574](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/action_contract.py:574).
- Answer — VERIFIED: N=4 freezes candidate/cell identity mapping between refreshes; it does not require an association to remain selected for four decisions.
- What breaks if misread — INFERRED: treating N as residence time changes legal trajectories, handover counts, and all policy comparisons.
- Guard — INFERRED: at phases 1–3, demonstrate that two different currently mask-valid actions can be selected on consecutive decisions while identities remain unchanged.
- Owner — INFERRED: stage 1/action contract.

### 11. MEDIUM — Panel arithmetic and CRN

- Legacy counts — VERIFIED: read-only enumeration of the exact schedule gives:
  - VERIFIED: rung 100 → 77 unique TRAIN dates, 1–3 worlds/date, mean 1.299 over occupied dates.
  - VERIFIED: 9,000 episodes → all 166 TRAIN dates, 34–71 worlds/date, mean 54.217.
- Proposed panel — UNKNOWN: no sealed list of approximately 600 successor evaluation domains/worlds was found in the supplied stage-2 snapshot.
- Approximation — INFERRED: for 600 independent uniform draws over 166 dates, expected occupied dates are `166×[1−(165/166)^600]=161.58`; this explains “≈161” but is not an exact panel count.
- Arithmetic — VERIFIED: six arms × five learner seeds × 600 worlds gives 18,000 arm-world evaluations and 3,000 learner-seed/world cells. The mean is 3.614 worlds per available date, or 3.713 per expected occupied date.
- CRN — VERIFIED: C3-S reconstructs each arm with the same world seed, mobility RNG ancestry, and fading-field root, then compares initial-state hashes [run_v023_c3s_screen.py:918](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py:918).
- CRN — VERIFIED: the 9,000 runner constructs the same keyed fading field for every arm/world and checks matched initial hashes [physical runner:1217](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:1217), [physical runner:2559](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:2559).
- CRN — VERIFIED: successor arms consume the same detached tape [tapes.py:1](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/tapes.py:1); fading is keyed by world, user, NORAD, absolute time, and actual elevation [provider_legacy.py:416](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:416).
- Qualification — UNKNOWN: the future six-arm/five-seed runner is not written, so CRN across its learner seeds cannot yet be verified.
- Guard — INFERRED: seal the exact 600-world manifest; assert byte-identical exogenous tape digests across all arms and learner seeds before outcomes.
- Owner — INFERRED: stage 8.

### 12. MEDIUM — UTC/frame approximations are explicit but incompletely bounded at the handoff

- Timezone — VERIFIED: TLE epochs are parsed as timezone-aware UTC [tle.py:125](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/tle.py:125); selection and Julian conversion reject naive datetimes and normalize zones to UTC [ephemeris.py:116](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/ephemeris.py:116), [geometry.py:36](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/geometry.py:36).
- Leap seconds — VERIFIED: Julian fractions and sampler days use exactly 86,400 seconds [geometry.py:59](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/geometry.py:59), [ephemeris.py:421](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/ephemeris.py:421).
- Leap seconds — UNKNOWN: there is no explicit leap-second policy or test. Python `datetime` cannot represent `23:59:60`.
- Frame — VERIFIED: SGP4 TEME positions are rotated directly to ECEF using IAU-82 GMST [geometry.py:68](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/geometry.py:68), [geometry.py:92](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/geometry.py:92).
- Frame — VERIFIED: UTC substitutes for UT1, with a documented bound of approximately 0.45 km at the equator; polar motion is omitted [geometry.py:9](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/geometry.py:9), [geometry.py:71](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/geometry.py:71).
- Earth model — VERIFIED: ground/user/cell ECEF uses a 6,371 km sphere while SGP4 uses WGS-72; the documented radius difference at 40°N is approximately 1.7 km [constants.py:20](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/constants.py:20).
- What breaks — INFERRED: boundary-near visibility/D2 decisions can change under UT1, ellipsoid, or leap-second convention changes even when seed and TLE are unchanged.
- Guard — INFERRED: freeze time-scale/EOP policy and compare representative boundary geometry against an independent TEME→ITRF/WGS reference, including points near 10° visibility and D2 thresholds.
- Owner — INFERRED: stage 1.

## Controller-map reconciliation

- VERIFIED — Refuted claim 1: a legacy world is fully identified by `(TLE date, world seed)`; horizon and persistent age-stream position also matter.
- VERIFIED — Refuted claim 2: “TEST is never read” as a global invariant; named runners are safe, but direct `ScenarioDriver` and an arbitrary tape provider are not guarded.
- VERIFIED — Refuted claim 3: all seeds derive from domains; the 9,000 plan uses an arithmetic sequence.
- VERIFIED — Refuted claim 4: raw per-boundary satellite ECEF, user ECEF, and off-axis geometry cross the successor tape handoff; only derived candidate quantities do.
- VERIFIED — Refuted claim 5: successor forward alignment eliminates the legacy D2 prime defect; it fixes the emitted clock but inherits the contaminated boundary-0 latch.
- VERIFIED — Refuted claim 6: the implemented independence unit is TLE date × learner seed; the provider supplies world seed, and the probe bootstrap treats each world as its own cluster.
- UNKNOWN — “6 arms × 5 seeds × ≈600 worlds over ≈161 dates” is a sealed executable design; no exact 600-world manifest or six-arm/five-seed runner exists in the supplied trees.
- VERIFIED — Filled stage-0 guard `?`: split-level tests and runner-local assertions exist, but no all-runners TRAIN/TLE-file test exists.
- VERIFIED — Filled stage-1 guard `?`: current provider tests cover decision-instant parity and satellite ECEF at boundaries 17/47, but not raw user-ECEF parity, monotonic D2 initialization, or full split/TLE attestation [test_provider_legacy.py:56](/home/sat/mcrl-v025-codex-ws-provider/tests/physics_v025/test_provider_legacy.py:56), [test_provider_legacy.py:91](/home/sat/mcrl-v025-codex-ws-provider/tests/physics_v025/test_provider_legacy.py:91).
- UNKNOWN — Test execution status in this audit; tests were intentionally not run.

VERDICT: STAGE=A | REFUTED_MAP_CLAIMS=6 | NEW_CORE_RISKS=5 | BLOCKERS=TRAIN_EVAL_DATE_SEPARATION_OR_CLAIM_LIMIT,CLUSTER_KEY_AND_MULTIWAY_BOOTSTRAP,PROVIDER_SPLIT_TLE_ATTESTATION,D2_PRIME_STATE,EXACT_600_WORLD_MANIFEST