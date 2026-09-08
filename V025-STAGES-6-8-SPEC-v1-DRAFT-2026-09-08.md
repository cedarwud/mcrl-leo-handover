# V0.25 stages 6–8 specification v1 — DRAFT

Date: 2026-09-08. Status: pre-outcome draft; synthetic execution only. Authority: the sealed v1.0–v1.4 declarations, controller decisions, and V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md. This draft does not authorize source generation, training, or evaluation on a real/TLE world. PHYSICS-GO remains the sole real-source trigger.

Normative words SHALL, MUST, and MUST NOT are binding within this draft. Every unresolved choice is visibly labelled CONTROLLER_DECIDE.

## 1. Scope and invariants

The implemented chain is:

per-anchor engine evaluation → action rows → authenticated TRAIN shards → deterministic pair batches → five matched learner lineages × six arms → deployed profile → per-step receipts → independent cluster merge → terminal decision.

The chain MUST preserve physical identity (NORAD, beam-chain), never candidate slot identity; separate world_seed and learner_seed; provider/archive/launch/code/physics/setting/calibration/schema/catalogue/allocation digests; explicit lambda = eta_ref and positive normalization bit scale; complete user roster including null actions; per-arm committed history; TRAIN only; common batches and initialization inside a lineage; and pooled Σbits/Σjoules.

## 2. Exact Q1 action-row schema

Q1 is one 16-value vector per (anchor, focal user, legal physical action). Legacy candidate blocks become the value belonging to this action. Normalization is signed raw/scale; booleans are 0/1. Version is mcrl-v025-stagec-q1-action-v1-draft.

| # | Exact field | Unit | Scale | Semantics |
|---:|---|---|---:|---|
| 1 | nominal_sinr_margin_at_rate_target | dB | 20 | Candidate current nominal SINR minus rate-target threshold; uncapped and signed. |
| 2 | nominal_required_power_over_cap | ratio | 1 | Uncapped required RF/applicable cap; may exceed one. Non-rate architectures use declared zero. |
| 3 | nominal_mode_spectral_efficiency | bit/s/Hz | 4 | Current nominal selected ACM-mode SE. |
| 4 | background_occupancy_excluding_focal | users | 10 | Previous committed served users on action beam, focal excluded. |
| 5 | beam_active_before_focal | bool | 1 | Background beam-chain activity before focal insertion. |
| 6 | satellite_active_before_focal | bool | 1 | Background satellite activity before focal insertion. |
| 7 | off_axis_angle | rad | 1 | Current candidate transmit off-axis angle. |
| 8 | remaining_d2_time | s | 120 | Causal remaining D2 eligibility at decision instant. |
| 9 | remaining_visibility_time | s | 120 | Causal remaining 10-degree visibility at decision instant. |
| 10 | refresh_phase | decisions | 3 | decision_index mod 4, represented 0…3. |
| 11 | previous_served_association_for_action | bool | 1 | Action identity equals prior committed served identity. |
| 12 | previous_served_load_for_action | users | 10 | Prior committed served load on action beam. |
| 13 | previous_beam_active_for_action | bool | 1 | Prior beam-chain activity. |
| 14 | previous_satellite_active_for_action | bool | 1 | Prior satellite activity. |
| 15 | previous_beam_max_rf_over_cap | ratio | 1 | Prior beam maximum RF/applicable beam cap. |
| 16 | missing_incumbent | bool | 1 | Prior incumbent absent from current physical candidate table. |

recurrence_power, entry_gain_ratio, and segment_age are forbidden. Draft schema SHA-256: cea0b30095457cf25ced24fd384bd53f93623a95b95fed42d32169b8913dd436.

CONTROLLER_DECIDE Q1-SCALES: v0 binds the field concepts but says v1 seals scales. The proposed 20 dB, 4 bit/s/Hz, 10-user, 1-rad, 120-s, and phase-3 scales require sealing before real rows.

## 3. Completed Q2 schema

Q2 appends missing_incumbent to the existing 21-field schema, for 22 values. Version: mcrl-v025-stagec-q2-action-v1-draft. Draft SHA-256: b622fc172b8cabecf40a3aad364dbd66baeb9c9c79e3ed7f60eb60a44ae761ae.

| # | Current field | Unit / scale |
|---:|---|---|
| 1 | incumbent_nominal_decoding_margin | dB / 20 |
| 2 | forecast_se_trend | bit/s/Hz/s / 0.1 |
| 3 | remaining_d2_time | s / 120 |
| 4 | remaining_visibility_time | s / 120 |
| 5 | refresh_phase | decision / 3 |
| 6 | background_occupancy_excluding_focal | users / 10 |
| 7 | beam_active_before_focal | bool / 1 |
| 8 | satellite_active_before_focal | bool / 1 |
| 9 | required_power_cap_margin | W / 1.65 |
| 10 | missing_incumbent | bool / 1 |

For each offset h = 1,2,3 append valid (bool/1), survival (bool/1), minimum_decoding_margin (dB/20), and mean_acm_spectral_efficiency (bit/s/Hz/4), in that order.

Background is the previous committed served set excluding the focal user. Timestamp is the decision instant. Occupancy excludes focal. Activation is measured before focal insertion. Forecasts use nominal geometry/interference only, hold background associations, recompute physics, charge a failed attempted offset, and retain later absorbing loss. INVALID has no surrogate. A missing incumbent uses zero margin plus flag one. required_power_cap_margin = cap − uncapped required power; non-rate architectures use declared zero.

CONTROLLER_DECIDE Q2-MISSING-PLACEMENT: build 1 puts the flag after nine current fields, before offsets.  
CONTROLLER_DECIDE Q2-SCHEMA-SEAL: the earlier 21-field SHA 54ab6a82… cannot identify this 22-field schema.  
CONTROLLER_DECIDE Q2-INCUMBENT-MARGIN: confirm repeated incumbent margin across candidate rows versus candidate-current margin.

## 4. Labels and dependency boundary

- C1 stores whole-network difference surplus bits and Φ separately; learner target is surplus/κ + phi_difference.
- C2 stores forecast core minus one κ bit scale per absorbing lost offset, then divides by κ.
- C3 is interaction share only: Ψ/2 for pairs and Shapley allocation for larger sets over the sealed bounded catalogue. No e_i term.
- BASE is the gauge/reference; pair target is candidate normalized label minus BASE normalized label.
- Allowed inputs are visible primitives, masks, keyed current fading, nominal forecasts, prior committed state, event ledger, sealed catalogue, and explicit prices. Hidden warm-start age and TEST are forbidden.

CONTROLLER_DECIDE KAPPA-BIT-SCALE: Stage C requires positive kappa_normalization_bits. The current engine exposes kappa_bits_per_user_s; stage 4 must seal the conversion required by the bits/κ equations.  
CONTROLLER_DECIDE C3-SET-REPRESENTATION: seal learned-S3 set features/order/padding and larger-set Shapley method. The synthetic linear head is scaffolding only.

## 5. Source rows and shards

Every row contains row/split and Q1/Q2 schema identities; world ID and world_seed; nullable learner_seed (null in lineage-independent sources); anchor ID/index and exact time; focal user; stable action index and physical identity or null; BASE flag and complete legal mask; terminal/null/outage flags; normalized vectors; code/physics/launch/catalogue/setting/calibration/provider/archive/allocation digests; hexadecimal lambda, eta_ref, κ; raw labels, C1 Φ difference, and normalized labels.

Construction asserts split == TRAIN with no override. The JSONL header authenticates row count, schemas, setting/calibration inventories, and canonical rows digest. File and immediate SHA sidecar are write-once and reopened through digest/schema/TRAIN validation.

A golden tape-to-row KAT MUST hand-check all 16 Q1 and 22 Q2 values, focal exclusion, identities, masks, forecasts, label normalization, time, and lineage.

## 6. Learner

Typed PairwiseBatch holds reference states, candidate states, fixed deltas, stable row identities, source-authority digest, and batch digest. There is no next_state, discount, replay sampling, target network, Bellman term, or bootstrap.

For route r, loss is MSE of Qr(candidate) − Qr(BASE) − target_delta plus a declared BASE-zero gauge. One source epoch is exactly one deterministic pass C1 → C2 → C3 over sealed aggregate batches. Order/count/digests stay fixed between epochs and arms.

Checkpoints at completed source epochs 100, 200, … contain completed_source_epochs, route_update_count = 3×epochs, batch and schema digests, learner seed, common initialization payload/digest, arm order/source map, all three heads for every learned arm, optimizer/hyperparameters/state, cadence, and zero_bootstrap=true. Resume reauthenticates all fixed fields. Old checkpoints are controls only.

CONTROLLER_DECIDE FORMAL-LEARNER: seal architecture, optimizer, hyperparameters, epoch budgets, serialization, and stopping. Build 1 uses full-batch linear heads only for synthetic execution.

## 7. Arms, seeds, and CRN

| Arm | C1 | C2 | C3 |
|---|---|---|---|
| FULL | informed | informed | informed |
| DROP_C1 | neutral | informed | informed |
| DROP_C2 | informed | neutral | informed |
| DROP_C3 | informed | informed | neutral |
| ALL_NEUTRAL | neutral | neutral | neutral |
| BASELINE | external | external | external |

ALL_NEUTRAL is the serialized shorthand for ALL_NEUTRAL_CONTROL. Neutral source means zero pair target while the head is retained, updated, checkpointed, and deployed. It never removes/masks a head.

Each of five learner-seed lineages clones one initialization into all five learned arms and shares identical batch identities/order. Evaluation RNG is isolated. BASELINE is external and authenticated.

CONTROLLER_DECIDE LEARNER-SEED-VALUES: seal exact five integers, seed domains, and BASELINE authentication. 101/202/303/404/505 are synthetic only.

## 8. Deployment, coordinator, and S_UNI

Each user's proposal is stable masked argmax of normalized Q1+Q2. The vector is not a commit until complete-roster masks, joint legality, resolved physical identity, and the no-served-count-decrease versus BASE guard pass.

The coordinator evaluates one sealed bounded catalogue containing BASE, all unilateral moves, S0 top-two proposals, frozen beam evacuations, top-K=10 pair moves, and active-beam evacuation sets. BASE is first and wins ties. Learned S3 or exact S0 adds set score. The 30.08-s timer covers proposal, forecasts, catalogue, selection, validation, and fallback. Deadline or validation failure commits BASE atomically.

S_UNI always accompanies the arm: start BASE, evaluate all legal unilateral moves with exact deployable nominal physics, commit strict best improvement with stable ties, iterate to fixed point.

Deployment-capability manifest binds code/physics/catalogue digests and declares all-user geometry, legal physical actions, prior profile, beam-specific cross-gains, forecasts/calibration, complete-profile construction, joint resolution, catalogue search, service guard, atomic commit, timing, and fallback.

CONTROLLER_DECIDE COORDINATOR-MODE: seal learned S3 or exact S0 and its information claim. Build 1 exposes a hook and synthetic learned default.  
CONTROLLER_DECIDE DEADLINE-CLOCK: seal hardware, clock, concurrency, caching, and timing evidence.

## 9. Allocation and evaluation

Formal target: six arms × five learner seeds × approximately 600 TRAIN worlds over approximately 161 TLE dates, approximately 30 steps/world; no TEST.

The pre-outcome manifest records experiment/panel/cell/unit; world, resolved start UTC, TLE date, TRAIN split, role; archive/provider/launch/code/physics/catalogue/deployment-capability/setting/calibration digests; separate seeds; and the bootstrap draw count/seed. Roles are probe, calibration, rehearsal, KAT, claim; synthetic is scaffolding only. Probe/calibration dates are disjoint from claim. Legacy-panel overlap is recorded. Acceptance uses disjoint rehearsal worlds or blinded hashes.

CONTROLLER_DECIDE FORMAL-ALLOCATION: seal exact worlds/dates/starts/seeds, 30-anchor coverage, prospective thinning k, and manifest digest.

## 10. Attempt registry and receipts

The controller-owned append-only hash chain records STARTED before outcome work for (experiment,panel,cell,unit), including authority digests and UTC. Exactly one DONE with receipt SHA follows. Failure records ABANDONED. Duplicates, absent STARTED, multiple terminals, unadjudicated ABANDONED, or unallocated receipts make merge fail.

Each write-once unit receipt and immediate sidecar contains all arms and canonical steps. Every step has world/unit/date/seeds/arm/index/time; hexadecimal bits/joules/components; complete-service, decoding/useful/opportunity, handover, and exact Φ additive numerators/denominators; every user's prior/current physical identity, event type, re-key and complete-service; plus provider/launch/code/physics/catalogue/deployment-capability/setting/calibration digests. The receipt binds an initial committed `t-1` physical profile and ever-served set for every arm; subsequent rows advance that arm's own committed history.

Events: unchanged, beam change, satellite change, cell re-key, initial entry, re-entry, exit.

CONTROLLER_DECIDE EVENT-QOS: seal re-entry/cell-rekey handover and Φ treatment. Build 1 matches current Φ: beam/satellite changes only, priced 0.5/1.0.

## 11. Conformance

Before formal outcomes, shared conformance on KAT/rehearsal allocation MUST prove NULL ≡ BASE per physical step, one real-provider step per arm, write-once receipts/sidecars, complete authority, reward-endpoint identity, and joint-profile validation. It never runs on a claim unit. Synthetic conformance proves plumbing only.

## 12. Merge and inference

Merge authenticates allocation, attempts, receipts, and authorities; reconstructs every summary from rows; and rejects disagreement. Worlds first pool inside cluster (TLE date, learner_seed) by additive values.

Primary EE is ΣB/ΣE. Each paired cluster-bootstrap draw recomputes arm ratios and relative gain EE_FULL/EE_DROP−1. Central 95% percentile intervals use 2.5/97.5% with NumPy linear interpolation. Date×seed two-way bootstrap and multivariate cluster delta method are supplementary.

Availability pools complete-service numerator/denominator. Handover and Φ cost also pool additive values. Each FULL−DROP passes iff:

- relative EE 2.5th percentile is strictly above +0.5%;
- complete-service difference 2.5th percentile is strictly above −0.5 percentage points;
- handover and Φ relative-change 97.5th percentiles are each strictly below +5%.

`B = 0, E > 0` is defined EE zero. A relative-EE draw is undefined only when the comparator EE is zero; zero QoS denominators are likewise undefined. Undefined draws are counted and build 1 conservatively fails the affected gate.

CONTROLLER_DECIDE ZERO-BIT-DISPOSITION: seal formal undefined-draw rule.  
CONTROLLER_DECIDE ZERO-QOS-BASELINE: seal relative handover/Φ behavior when DROP denominator is zero; build 1 marks undefined/fail.

## 13. Admission and claim

admission_decision returns PHYSICS-GO only when acceptance passes, all retained oracle factors are certified positive, QoS passes, C3 has genuine joint headroom, deployable S0 gain ≥1%, and zero-outcome disposition is sealed. Otherwise HOLD. This precedes real source generation.

claim_decision is one conditional intersection–union conjunction: all three FULL−DROP contrasts must pass EE and QoS. No per-contrast multiplicity inflation applies to this one global conjunction. FULL−ALL_NEUTRAL and S_UNI are supportive; sensitivities exploratory. Wording is TRAIN-panel conditional and forbids TEST/generalization/efficacy claims.

## 14. Terminal report schema

The terminal report contains schema/authorities; panel/world/date/cluster/arm/seed inventory; state/shard/batch/checkpoint/deployment digests; additive totals; every contrast's point estimate, central interval, undefined draws, delta and two-way supplements, gates; zero dispositions; admission and claim decisions; conformance and registry head; anomalies/abandonments; evidence ceiling TRAIN_ONLY_NO_TEST_NO_GENERALIZATION; interface assumptions; and CONTROLLER_DECIDE inventory. Exactly one terminal adjudication is emitted per sealed experiment root.
