# Pipeline audit B — stages 6–7

[VERIFIED] Static, read-only audit only; no tests or simulations were executed. The map was treated as the specification and checked against the legacy, successor-snapshot, and provider-WIP implementations.

## Executive disposition

[VERIFIED] The map materially conflates two legacy pipelines:

- [VERIFIED] Online MODQN uses homogeneous 112-D transitions, a replay buffer, and Bellman bootstrapping.
- [VERIFIED] The deployed Catfish Q1/Q2 path uses heterogeneous 228-D/448-D pair rows, deterministic source batches, pairwise regression, and zero bootstrap.
- [VERIFIED] Twelve map clauses are refuted; the exact inventory appears below.
- [UNKNOWN] No implemented successor path currently connects primitive tapes → 21-field rows → training batches → learner → deployed selector.
- [VERIFIED] The strongest new basic assumption missed by the map is that the visible Q1 state must determine its label. It does not at episode start: hidden warm-start ages affect power and feasibility.

## Ranked findings

### 1. CRITICAL — hidden episode-start state makes Q1 labels non-functional in the visible state — NEW CORE RISK 1

- **Assumption — [VERIFIED; MAP INCOMPLETE]:** Every physical variable affecting a source label is either encoded in the deployed state or fixed independently of the example.
- **Where — [VERIFIED]:** Reset clears association, demand, radiating beams, link powers, and segments, so the visible historical fields are zero, but privately draws `_pending_segment_age` at [step.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/step.py:500). First-step physics uses that hidden age and historical geometry to reconstruct segment-start gain and hence recurrence power/feasibility at [step.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/step.py:754). OPS3 also reads the private ages for its opening surface at [ee_axis_ops3_live.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3_live.py:303).
- **What breaks — [INFERRED]:** Two byte-identical visible 228-D Q1 states can receive different C1 labels solely because their hidden pending-age vectors differ. Q1 therefore cannot represent a deterministic deployment mapping at step 0; the successor may preserve the same target leakage after removing recurrence/age fields.
- **Guard — [INFERRED]:** Construct two reset snapshots with identical visible state, masks, geometry, and keyed fading but different pending ages. Require identical C1 labels, or explicitly encode the complete pre-episode segment state, or impose a genuine cold-reset rule. Add a dependency allowlist requiring every target input to be deployably observable.
- **Owner — [INFERRED]:** Stages 0, 3, and 6.

### 2. CRITICAL — the map joins two unrelated learner/data paths

- **Assumption — [VERIFIED; MAP REFUTED]:** The 228-D/448-D source rows flow through `ReplayBuffer` into the Q1/Q2 heads in `modqn.py`.
- **Where — [VERIFIED]:** `TrainerEnvironment` only resets/steps the legacy environment and returns `UserState`, masks, and rewards at [trainer_env.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/trainer_env.py:166). The source generator replays authenticated worlds, constructs Q1/Q2 comparisons, and writes per-world `c1-…json`/`c2-…json` artifacts at [generate_v023_c1c2_targets.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py:1241). Adapters stack those into typed pair batches; the heterogeneous trainer consumes them directly with no next state at [v023_heterogeneous_trainer.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:239).
- **Where — [VERIFIED]:** The unrelated replay buffer stores one homogeneous `(state, action, reward_3, next_state, masks, done)` transition at [replay_buffer.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/replay_buffer.py:30); MODQN encodes the base 112-D state and owns three online/target networks.
- **What breaks — [INFERRED]:** “Same learner with common-action bootstrap” is undefined until the successor chooses fixed-target pairwise regression or transition-based Bellman learning. Dataset fields, update counts, checkpoint state, and scientific estimand differ.
- **Guard — [INFERRED]:** Require one versioned learner contract: either pair rows with no `next_state` and zero bootstrap, or transitions with a declared common scalarized bootstrap action. Reject mixed schemas.
- **Owner — [INFERRED]:** Stages 6–7.

### 3. CRITICAL — exact legacy source-to-row trace

- **Assumption — [VERIFIED]:** Q1 has 228 values with causal predecision history.
- **Where — [VERIFIED]:** The dimension is `112 + 4×28 + 4` at [ee_axis_state.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_state.py:41). Its exact order is:

  - [VERIFIED] `[0:28]`: previous served association one-hot, expressed in the current candidate ordering; all zero when absent/out of table, [step.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/step.py:1124).
  - [VERIFIED] `[28:56]`: `log1p(max(SINR,0))`; current geometry/current observation draw, segment-start `p0` wanted power, but interference from the previous radiating set, [state_encoding.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/state_encoding.py:54), [step.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/step.py:1201).
  - [VERIFIED] `[56:84]`: current off-axis angle in raw radians, [state_encoding.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/state_encoding.py:74).
  - [VERIFIED] `[84:112]`: previous-step ungated demand keyed by physical `(NORAD, cell)`, divided by user count, [step.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/env/step.py:1162).
  - [VERIFIED] `[112:140]`: previous served load per candidate divided by user count; `[140:168]` previous beam-active bit; `[168:196]` previous satellite-active bit; `[196:224]` previous beam maximum RF power divided by `Pmax`, [ee_axis_state.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_state.py:217).
  - [VERIFIED] `[224:228]`: focal previous link power/`Pmax`, current incumbent gain/segment-start gain, segment age/episode length, and `missing_incumbent`, [ee_axis_state.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_state.py:282).

- **Assumption — [VERIFIED]:** Q2 has 448 values, `16×28`, flattened feature-major.
- **Where — [VERIFIED]:** Its feature contract is at [ee_axis_v014_q2_state.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_v014_q2_state.py:24), and the transpose/flatten is at [ee_axis_v014_q2_state.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_v014_q2_state.py:141):

  - [VERIFIED] Four 28-wide current blocks: frozen nonfocal served load/`U`, frozen background beam max power/`Pmax`, beam-active bit, satellite-active bit.
  - [VERIFIED] For each of `h=1,2,3`, four 28-wide blocks: valid/legal, absorbing persistence `χ`, required recurrence power/`Pmax`, and `log1p(projected SINR)`.
  - [VERIFIED] Background is the last committed served set, excluding the focal user, grouped by physical beam using maximum link power—not `_previous_demand`, [ee_axis_ops3_live.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3_live.py:254).
  - [VERIFIED] Future load is `1 + frozen nonfocal prior-served count`, [ee_axis_ops3_live.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3_live.py:723).
  - [VERIFIED] Q2 state explicitly excludes targets, reference actions, realized outcomes, selected actions, and Q1/Q3 values/ranks/actions, [ee_axis_v014_q2_state.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_v014_q2_state.py:49).

- **What breaks — [INFERRED]:** Conflating previous ungated demand, previous served load, and frozen nonfocal background changes congestion, activation, and persistence meanings.
- **Guard — [INFERRED]:** A hand fixture with one infeasible selected user must increment ungated demand but not served load; Q2 must exclude the focal user and use prior served max power.
- **Owner — [INFERRED]:** Stages 3 and 6.

### 4. CRITICAL — deployable-information gap is real and precisely identifiable

- **Assumption — [VERIFIED; MAP REFUTED]:** The learned heads and LITE exact evaluator operate on the same information.
- **Where — [VERIFIED]:** Q1/Q2 heads see user-local action rows based on current geometry plus lagged/frozen background. LITE uses Q1+Q2 only to retain one alternative per user at [c3s_policy.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:344).
- **Where — [VERIFIED]:** LITE then forms complete simultaneous action vectors, including multi-user evacuations, and evaluates each vector through `_resolve_physics` at [c3s_policy.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:520) and [c3s_policy.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:772). It receives all users’ current geometry, physical candidates, previous associations/segments, and physics configuration at [c3s_policy.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:636).
- **Definition — [INFERRED]:** The deployable-information gap is: independently scored per-user rows do not contain other users’ simultaneous proposed choices or their resulting current-profile joint interference, load/bandwidth, jointly resolved powers, active-beam/satellite costs, service, bits, or energy; the exact evaluator obtains these by model-based whole-profile recomputation.
- **What breaks — [INFERRED]:** Without exact rescoring, additive heads cannot generally reproduce the joint ranking. With it, the gain is partly an online nominal optimizer using information and computation absent from the heads, not purely learned coordination.
- **Guard — [INFERRED]:** Create two cases with identical per-action encoded rows but different cross-user cross-gains/simultaneous moves that reverse the exact best profile. Require the deployment claim to identify exact physics as an additional information source.
- **Owner — [INFERRED]:** Stage 7, with the Stage-6 schema producer.

### 5. CRITICAL — successor κ is dimensionally inconsistent — NEW CORE RISK 2

- **Assumption — [VERIFIED; MAP INCOMPLETE]:** Successor normalized targets are dimensionless and commensurate.
- **Where — [VERIFIED]:** Successor calibration defines `κ=B_ref/(U·T_ref)` with units bits/(user·second) at [calibration.py](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/calibration.py:98) and [endpoint.py](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/endpoint.py:143).
- **Where — [VERIFIED]:** C1 divides a bit-valued surplus directly by κ at [targets.py](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/targets.py:153). C2 calls `κ×lost_offsets` “penalty bits” and divides its bit-valued core by κ at [targets.py](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/targets.py:248). No user-seconds or decision-duration factor is applied.
- **What breaks — [INFERRED]:** `bits/κ` has units user·seconds, not a dimensionless score; `κ×offset_count` is not bits. C1, C2, Φ, and any successor direct sum lack a coherent declared unit.
- **Guard — [INFERRED]:** Add a unit KAT carrying symbolic dimensions through calibration and C1/C2. Seal whether normalization is by a bit scale such as `κ·U·Δt`, by per-user rate, or by another explicitly named quantity; then test numeric equivalence.
- **Owner — [INFERRED]:** Stages 4–7.
- **Blocker — [INFERRED]:** Successor target generation should not open before this contract is resolved.

### 6. HIGH — legacy scale is commensurate, but the map states the units incorrectly

- **Assumption — [VERIFIED; MAP REFUTED]:** Deployed Q1 remains in bits while Q2 is converted “via κ.”
- **Where — [VERIFIED]:** Legacy C1 source target is `focal Δbits − λ·whole-system Δenergy` in native bits at [ee_surplus_targets.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_surplus_targets.py:236). C1 training divides it by κ exactly once at [v023_heterogeneous_trainer.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:265).
- **Where — [VERIFIED]:** Q2 forms native-bit terms `Δt(rate−λΔpower)−(1−χ)κ`, averages/centers them, and divides by κ at [ee_axis_ops3.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3.py:741) and [ee_axis_ops3.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3.py:779). The typed trainer consumes that normalized target without another division at [v023_heterogeneous_trainer.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:306).
- **Where — [VERIFIED]:** Deployment directly sums the normalized surfaces and performs one masked argmax at [ee_axis_lcsrs_three_route.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py:380).
- **Conclusion — [VERIFIED]:** No admitted heterogeneous path applies λ or κ twice or omits it. Both deployed heads output normalized “bits/κ” scores, not raw bits.
- **Caveat — [VERIFIED]:** `build_ops3_surface` retains stale λ/κ defaults at [ee_axis_ops3.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3.py:598), and the live builder reaches it without explicit prices at [ee_axis_ops3_live.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3_live.py:925). Formal repriced typed batches avoid a second κ conversion, but raw/live callers remain provenance hazards.
- **Guard — [INFERRED]:** Hand-calculate one C1 and C2 pair; assert C1 loss target is raw surplus/κ, C2 target is copied unchanged, and deployment selects their direct sum. Remove all default-price reachability in the successor.
- **Owner — [INFERRED]:** Stages 4, 6, and 7.

### 7. HIGH — MODQN bootstraps incompatible head-specific actions, but Catfish Q1/Q2 do not bootstrap

- **Assumption — [VERIFIED]:** Generic MODQN uses one independent argmax per objective head.
- **Where — [VERIFIED]:** The update loops over objectives at [modqn.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/algorithms/modqn.py:536), evaluates that head’s target network, masks it, and calls `.max(dim=1)` independently at [modqn.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/algorithms/modqn.py:544).
- **Qualification — [VERIFIED; MAP REFUTED]:** This defect does not describe heterogeneous Catfish Q1/Q2: C1 explicitly has no next-state term at [v023_heterogeneous_trainer.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py:272), and C2 is also direct pairwise regression.
- **What breaks — [INFERRED]:** Generic MODQN can combine future values belonging to mutually incompatible actions, so its vector target is not the value of the deployed scalarized policy.
- **Guard — [INFERRED]:** Give heads distinct legal maximizers. A successor Bellman learner must choose one masked scalarized action and gather every head at that same index.
- **Owner — [INFERRED]:** Stage 7.

### 8. HIGH — DROP means neutral-source retraining, not head removal

- **Assumption — [VERIFIED; MAP REFUTED]:** A DROP arm zeroes, omits, stops training, or masks the named head.
- **Where — [VERIFIED]:** `SOURCE_ABLATION_MAP` keeps all routes and substitutes the named route’s informed batch with a neutral batch at [v023_five_arm_learner_orchestrator.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py:52). Every arm’s route is still updated at [v023_five_arm_learner_orchestrator.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py:376).
- **What breaks — [INFERRED]:** DROP estimates the effect of informative versus neutral source training for that route, not the marginal value of including the head in the deployed sum.
- **Q1 reuse — [VERIFIED]:** Q2 features contain no direct Q1 values, ranks, or actions.
- **Q1 reuse — [INFERRED]:** DROP_C1 nevertheless retains C1-like physical information through Q2’s load, power, activation, required-power, and SINR features. Q2 target centering also accepts a predecessor reference action at [ee_axis_ops3_live.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/src/mcrl/runtime/ee_axis_ops3_live.py:879). Therefore DROP_C1 is not an information-orthogonal removal of all C1 knowledge.
- **Guard — [INFERRED]:** Assert every DROP checkpoint still has all heads, the neutral-trained head changes from initialization, and it participates in deployment. Separately vary predecessor references while holding physical features fixed to expose target/provenance dependence.
- **Owner — [INFERRED]:** Stages 6–7.

### 9. HIGH — successor 21-field schema is C2-only, incomplete, and unwired — NEW CORE RISKS 3–4

- **Assumption — [VERIFIED; MAP PARTLY REFUTED]:** One completed 21-field successor schema replaces both legacy Q1/Q2 inputs.
- **Where — [VERIFIED]:** The module calls itself a “Frozen C2 observation schema” and defines `C2ActionState`, [state_v025.py](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/state_v025.py:1). No production source builder, dataset, learner, or deployment component calls `encode_c2_state`; inspected consumers are tests/manifests only.
- **Where — [VERIFIED]:** Per action it encodes nine values: incumbent nominal margin `/20 dB`, SE trend `/0.1`, D2 time `/120 s`, visibility time `/120 s`, refresh phase `/3`, occupancy `/10`, beam/satellite bits, and cap margin/beam cap. It then adds three offsets of valid, survival, minimum margin `/20`, and mean ACM SE `/4`, [state_v025.py](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/state_v025.py:18).
- **Missing-incumbent — [VERIFIED; NEW CORE RISK 3]:** The governing contract requires retaining `missing_incumbent` and migrating the historical tail into Q1 at [astra-physics-round3-final.md](/home/sat/mcrl-v023-astra-physics/astra-physics-round3-final.md:102). The 21 fields have no such flag, while the encoder requires a finite incumbent margin.
- **Background causality — [UNKNOWN; NEW CORE RISK 4]:** No producer defines whether a non-incumbent row receives its own margin or repeated incumbent margin; whether occupancy includes the focal user; whether activation is measured before or after focal insertion; or whether the background is previous committed, BASE, or candidate-profile state.
- **What breaks — [INFERRED]:** No-incumbent states can alias numerical margins, and inconsistent background timestamps can leak teacher/current-profile choices or train a state unavailable at deployment.
- **Guard — [INFERRED]:** A tape-to-row golden fixture must assert physical key, timestamp, focal inclusion, missing-incumbent encoding, occupancy, activation, margin, masks, and all three forecasts for every legal action.
- **Owner — [INFERRED]:** Stage 6.

### 10. HIGH — successor C3 target contradicts the map

- **Assumption — [VERIFIED; MAP REFUTED]:** Successor C3 is interaction share only, `z3=Ψ/2`.
- **Where — [VERIFIED]:** The implementation computes `z3,i=e_i+Ψ/2` at [targets.py](/home/sat/mcrl-v025-stage2-snapshot-20260908/src/mcrl/physics_v025/targets.py:307). The stage-2 report says the binding of `e_i` remains unresolved at [V025-ENGINE-STAGE2-REPORT-2026-09-08.md](/home/sat/mcrl-v025-stage2-snapshot-20260908/.scratch/multi-catfish-v025-physics-successor/V025-ENGINE-STAGE2-REPORT-2026-09-08.md:95).
- **What breaks — [INFERRED]:** C1/C3 double-counting and DROP_C3 interpretation depend on the unresolved externality term; source generation cannot claim the map’s target.
- **Guard — [INFERRED]:** Freeze a scalar four-profile KAT specifying `e_i`, Ψ, each user’s z3, and the exact decomposition against C1 before producing data.
- **Owner — [INFERRED]:** Stages 5–7.

### 11. MEDIUM — checkpoint, seed, and CRN statements mix semantic units

- **Assumption — [VERIFIED; MAP REFUTED]:** Catfish source checkpoints occur every 100 simulator episodes.
- **Where — [VERIFIED]:** The five-arm source runner emits checkpoints every 100 complete source-training epochs, with three route updates per epoch, at [v023_five_arm_source_training_runner.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py:290) and [v023_five_arm_source_training_runner.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py:589). Only the unrelated online baseline checkpoints every 100 simulator episodes.
- **CRN — [VERIFIED]:** One serialized initialization is loaded into every arm at [v023_five_arm_learner_orchestrator.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py:256), and each route/source batch is fetched once and shared across applicable arms at [v023_five_arm_learner_orchestrator.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py:376).
- **Seeds — [VERIFIED; MAP REFUTED]:** The runner accepts one `--train-seed` per run at [v023_five_arm_source_training_runner.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py:860). The successor governing contract specifies three independent initializations, not five, at [astra-physics-round3-final.md](/home/sat/mcrl-v023-astra-physics/astra-physics-round3-final.md:199).
- **What breaks — [INFERRED]:** Calling epochs episodes corrupts budget/resume comparisons; confusing five arms with five seeds produces pseudoreplication.
- **Guard — [INFERRED]:** Checkpoint metadata must name `completed_source_epochs` and route-update count. An outer manifest must assert the chosen number of distinct lineage seeds and common initialization/source digests within each lineage.
- **Owner — [INFERRED]:** Stages 6–8.

### 12. MEDIUM — full-panel epoch semantics are an unsealed optimizer assumption — NEW CORE RISK 5

- **Assumption — [VERIFIED]:** One source epoch reuses deterministic aggregate batches rather than sampling transition replay.
- **Where — [VERIFIED]:** The provider stores one aggregate batch per route/source and the orchestrator sends the same supplied batch to all mapped arms in fixed route order, [v023_five_arm_learner_orchestrator.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py:376).
- **What breaks — [INFERRED]:** Introducing row shuffling, minibatching, or replay changes gradient noise, route weighting, optimizer dose, CRN matching, and the meaning of the inherited 100-epoch budget.
- **Guard — [INFERRED]:** Seal batch row counts/order/digests and epoch semantics; checkpoint the batch cursor if any sampling is introduced.
- **Owner — [INFERRED]:** Stages 6–7.

### 13. MEDIUM — exact evaluation assumes an undeclared deployment capability — NEW CORE RISK 6

- **Assumption — [INFERRED]:** A real controller can observe/authenticate all users’ current geometry and legal physical choices, construct a complete simultaneous proposal, recompute cross-gains/joint physics, and search the bounded catalogue before the action deadline.
- **Where — [VERIFIED]:** Legacy LITE’s detached evaluator depends on those inputs at [c3s_policy.py](/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/c3s_policy.py:390). The 21-field policy schema neither carries nor reconstructs them.
- **Provider status — [VERIFIED]:** A real `LegacyWorldProvider` now exists in the provider WIP at [provider_legacy.py](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py:134), including a TRAIN-only archive gate. It was untracked in the inspected worktree, and its controller decision still defers identity/digest/manifests to sealing at [V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md](/home/sat/mcrl-v025-codex-ws-provider/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08.md:5).
- **What breaks — [INFERRED]:** The exact-evaluator arm may be unrealizable or miss its deadline even though the learned per-action policy is deployable.
- **Guard — [INFERRED]:** Seal a deployment capability/dependency manifest and run an authenticated real-provider timing KAT with deadline fallback and BASE atomic commit.
- **Owner — [INFERRED]:** Stages 6–7.

## Refuted map-claim inventory

1. [VERIFIED; MAP REFUTED] “Source NPZ shards” are not the immediate 228/448 training rows; authenticated replay-generated JSON is converted into typed batches.
2. [VERIFIED; MAP REFUTED] Legacy labels are not the successor Stage-5 labels: legacy C1 uses focal Δbits minus whole-system energy price and lacks successor whole-network C1+Φ.
3. [VERIFIED; MAP REFUTED] The heterogeneous Q1/Q2 rows do not enter `ReplayBuffer`.
4. [VERIFIED; MAP REFUTED] Source checkpoints are every 100 source epochs, not episodes.
5. [VERIFIED; MAP REFUTED] The heterogeneous Q1/Q2 heads are not the heads in `modqn.py`.
6. [VERIFIED; MAP REFUTED] MODQN’s per-head bootstrap does not describe current Catfish Q1/Q2, which use zero bootstrap.
7. [VERIFIED; MAP REFUTED] The 21-field schema does not yet replace both Q1/Q2 inputs; it is C2-only, misses a sealed flag, and has no production consumer.
8. [VERIFIED; MAP REFUTED] Deployed legacy Q1 is not in raw bits; both Q1 and Q2 are normalized by κ.
9. [VERIFIED; MAP REFUTED] Independent masked per-user argmax produces individually legal actions, not a guaranteed jointly feasible profile.
10. [VERIFIED; MAP REFUTED] DROP arms do not differ by removal of a head; they substitute neutral source training while retaining the head at deployment.
11. [VERIFIED; MAP REFUTED] “Seeds 5” is not implemented in stages 6–7 and conflicts with the successor’s declared three initializations.
12. [VERIFIED; MAP REFUTED] Successor C3 code is `e_i+Ψ/2`, not the map’s interaction-only `Ψ/2`.

## Filled `?` entries and missing successor Stage-6/7 specification

- [VERIFIED] Stage-6 invariant “state carries the information the coordinator uses” is false; the deployable-information gap is open.
- [VERIFIED] No schema-to-information sufficiency test exists; existing successor state tests establish shape/hash and price-argument presence only.
- [VERIFIED] No end-to-end guard covers tape → successor row → both heads → common action → exact/set deployment.
- [UNKNOWN] Successor Q1 schema, shape, and migrated historical tail.
- [UNKNOWN] The production builder for 21-field rows and its background/focal/timestamp semantics.
- [UNKNOWN] Whether successor FULL2 uses pairwise zero-bootstrap regression or Bellman replay.
- [UNKNOWN] If Bellman learning is selected, the precise scalarized common-action bootstrap and next-mask rule.
- [UNKNOWN] Transition/pair shard schema, outage/NOOP retention, physical-key alignment, and TRAIN-only assertion.
- [UNKNOWN] Corrected κ unit and the Q1/Q2/Φ composition contract.
- [UNKNOWN] Neutral-source construction and matched strata for DROP_C1, DROP_C2, and ALL_NEUTRAL.
- [UNKNOWN] Whether source epochs remain full deterministic aggregate updates or become sampled/minibatched.
- [UNKNOWN] Successor checkpoint cadence, resume contents, artifact authentication, and old-checkpoint transfer boundary.
- [UNKNOWN] Resolution of three declared initializations versus the map/evaluation’s five seeds, plus seed-domain and CRN rules.
- [UNKNOWN] The deployed selector: exact S0, learned S3, or Q12-pruned LITE; its allowed information, catalogue, service guard, deadline, and fallback.
- [UNKNOWN] C3 set-training examples and the binding of `e_i`.
- [UNKNOWN] Formal provider source digest, world/calibration manifests, and real-provider rehearsal remain unsealed.

VERDICT: STAGE=B | REFUTED_MAP_CLAIMS=12 | NEW_CORE_RISKS=6 | BLOCKERS=HIDDEN_T0_WARM_START,SUCCESSOR_KAPPA_UNITS,MISSING_INCUMBENT,NO_STATE_SOURCE_LEARNER_BRIDGE,C3_EI_BINDING,UNSEALED_PROVIDER_CALIBRATION