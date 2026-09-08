# V0.25 stages 6–8 specification v1 — DRAFT

Date: 2026-09-08. Status: pre-outcome, synthetic-only. Binding input: `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`, which supersedes v0. This draft does not authorize real/TLE source generation, successor training, or claim evaluation. Those remain behind the calibration freeze and PHYSICS-GO.

## 1. Information interfaces A1–A4

The executable records are `HeadsInformation`, `CoordinatorInformation`, `ReferenceProfiles`, and `ArmInformationInterface` in `stagec_v025/interfaces.py`.

- **A1 / I_heads:** for user *i*, the legal physical actions; current nominal geometry of those actions; *i*'s history; previous committed served set excluding *i*, projected to the decision instant; the frozen Q1/Q2 derived features below. Model access is `none`; compute is `one_forward_pass`.
- **A2 / I_coordinator:** global nominal geometry and beam-specific cross gains; every user's legal set; previous committed profile; proposal a0; bounded complete-profile catalogue C; nominal model M; and, for every profile, joint load, coupled powers, interference, activation, service, bits, energy, and continuation. Realised fading is unavailable and future TLE access is limited to the declared forecast horizon. Coordinator wall budget is 10 s.
- **A3:** `proposal_a0` is the validated profile formed from stable masked Q1+Q2 proposals plus deterministic conflict repair. `previous_committed` is the distinct physical profile used for Φ, handover, and event accounting. They MUST NOT be conflated.
- **A4:** FULL, every DROP, BASELINE, S0, and S_UNI share primitive access/timestamps, forecast method, physical identity, catalogue construction, joint search, guards, ties, validation, deadline, and fallback. `authenticate_matched_catalogues` requires an identical catalogue digest at each matched anchor. Learned pruning is either identical and declared or rejected. Removed scores cannot re-enter ranking, pruning, or guards.

## 2. Exact Q1 field list and scales

Schema `mcrl-v025-stagec-q1-action-v1`, SHA-256 `c002ea883a4ab727f9e00cc15866f5b9d37abca645963fd3db2f2db7c6cc887a`. Each legal action has 16 signed `raw / scale` values; booleans are 0/1.

| # | Field | Unit | Scale |
|---:|---|---|---:|
| 1 | `nominal_sinr_margin_at_rate_target` | dB | 20 |
| 2 | `nominal_required_power_over_cap` | ratio | 1 |
| 3 | `nominal_mode_spectral_efficiency` | bit/s/Hz | 4 |
| 4 | `background_occupancy_excluding_focal` | user | 10 |
| 5 | `beam_active_before_focal` | boolean | 1 |
| 6 | `satellite_active_before_focal` | boolean | 1 |
| 7 | `off_axis_angle` | rad | 1 |
| 8 | `remaining_d2_time` | s | 120 |
| 9 | `remaining_visibility_time` | s | 120 |
| 10 | `refresh_phase` | decision | 3 |
| 11 | `previous_served_association_for_action` | boolean | 1 |
| 12 | `previous_served_load_for_action` | user | 10 |
| 13 | `previous_beam_active_for_action` | boolean | 1 |
| 14 | `previous_satellite_active_for_action` | boolean | 1 |
| 15 | `previous_beam_max_rf_over_cap` | ratio | 1 |
| 16 | `missing_incumbent` | boolean | 1 |

The background is the previous committed served set excluding the focal user; occupancy excludes focal; activity is before focal insertion. `recurrence_power`, `entry_gain_ratio`, and `segment_age` are forbidden.

## 3. Exact Q2 field list and scales

Schema `mcrl-v025-stagec-q2-action-v1`, SHA-256 `a891dd9831d76bccd981cef054ff204fa1d49c3cf6e5f3265015f16f1057019c`. The frozen 21 fields plus `missing_incumbent` give 22 signed `raw / scale` values. The flag is after the nine current-action fields and before the offset blocks.

| # | Field | Unit | Scale |
|---:|---|---|---:|
| 1 | `candidate_current_nominal_decoding_margin` | dB | 20 |
| 2 | `forecast_se_trend` | bit/s/Hz/s | 0.1 |
| 3 | `remaining_d2_time` | s | 120 |
| 4 | `remaining_visibility_time` | s | 120 |
| 5 | `refresh_phase` | decision | 3 |
| 6 | `background_occupancy_excluding_focal` | user | 10 |
| 7 | `beam_active_before_focal` | boolean | 1 |
| 8 | `satellite_active_before_focal` | boolean | 1 |
| 9 | `required_power_cap_margin` | W | 1.65 |
| 10 | `missing_incumbent` | boolean | 1 |
| 11 | `offset_1_valid` | boolean | 1 |
| 12 | `offset_1_survival` | boolean | 1 |
| 13 | `offset_1_minimum_decoding_margin` | dB | 20 |
| 14 | `offset_1_mean_acm_spectral_efficiency` | bit/s/Hz | 4 |
| 15 | `offset_2_valid` | boolean | 1 |
| 16 | `offset_2_survival` | boolean | 1 |
| 17 | `offset_2_minimum_decoding_margin` | dB | 20 |
| 18 | `offset_2_mean_acm_spectral_efficiency` | bit/s/Hz | 4 |
| 19 | `offset_3_valid` | boolean | 1 |
| 20 | `offset_3_survival` | boolean | 1 |
| 21 | `offset_3_minimum_decoding_margin` | dB | 20 |
| 22 | `offset_3_mean_acm_spectral_efficiency` | bit/s/Hz | 4 |

The background and timestamp rules equal Q1. Q1 field 1 is the rate-target SINR margin and Q2 field 1 is each action's own candidate-current nominal decoding margin. A separate row field, `incumbent_context_nominal_decoding_margin_db_hex`, carries the prior incumbent's per-user context and is broadcast unchanged across that user's candidate rows; the names and meanings are distinct. Missing incumbent uses raw incumbent-context margin zero and flag one. Forecasts use only nominal geometry/interference, hold background associations, recompute powers, and contain exactly offsets 1–3. `required_power_cap_margin = cap − uncapped required power`; non-rate architectures use zero.

## 4. Targets and identities

`NetworkOutcome.phi` is the inherited dimensionless signed preference: beam/satellite change values are −0.5/−1.0. Define `Phi_cost_bits = −κ phi`, so

`F(a) = B(a) − eta_ref E(a) − Phi_cost_bits(a) = B(a) − eta_ref E(a) + κ phi(a)`.

For proposal reference a0, `d_i = F(a_i,a0_-i) − F(a0)` and `Psi_A = F(a_A,a0_-A) − F(a0) − sum_i d_i`. C1 is `sum_i d_i`; C3 is scalar `Psi_A`; and C1+C3 exactly reconstructs the F delta. The second KAT removes Φ from every term and reconstructs the physical `B−eta_ref E` delta. Stage-4 calibration's κ in bits/user-second converts exactly to `kappa_normalization_bits = 30.08 * kappa_bits_per_user_s`; Stage C accepts only the converted user-step value and divides every deployed term once. C2 contains continuation only: three offsets and −κ for each absorbing lost offset after failure.

Event QoS uses Φ1 = 0.5κ for a same-satellite beam change and Φ2 = 1.0κ for a satellite change. After an outage, re-entry is priced as a satellite change when the new satellite differs from the pre-outage incumbent and otherwise as a beam change. A dwell-boundary cell re-key without a beam change costs zero handover Φ and is counted separately. Interruption blackouts follow the stage-1 decision-5 definition.

## 5. Exact row and shard schemas

### Q1/Q2 action row

Schema `mcrl-v025-stagec-source-row-v1`. Fields: `schema`, `split=TRAIN`, `world_id`, `world_seed`, nullable lineage-independent `learner_seed`, `anchor_id`, `anchor_index`, `decision_time_utc`, `decision_time_ns`, `user_id`, `action_index`, physical `action{norad_id,beam_chain_id}`, `reference_action`, complete `action_mask`, `q1_state[16]`, `q2_state[22]`, `incumbent_context_nominal_decoding_margin_db_hex`, both schema digests, `setting_id`, code/physics/launch/catalogue/setting/calibration/provider/archive/allocation digests, hexadecimal lambda/eta/κ, raw C1 physical surplus, C1 phi difference, C2 bits, normalized C1/C2, and terminal/null/outage flags. C3 fields are forbidden in this per-action schema; they exist only in the coalition schema below.

Action shard schema `mcrl-v025-stagec-source-shard-v1`: header fields are schema, TRAIN split, row count/digest, Q1/Q2 schema digests, setting/calibration inventories, and source-authority digest. JSONL and immediate SHA-256 sidecars are canonical/write-once.

### C3 coalition row

Schema `mcrl-v025-stagec-c3-coalition-row-v1`. Fields: schema/TRAIN; world and separate seeds; anchor ID/index/times; setting ID; complete `context`; original changed-user count and capped flag; hexadecimal lambda, eta_ref, κ, C1, Ψ, total F delta, physical C1, physical Ψ, physical total delta; and code/physics/catalogue/setting/calibration/allocation digests.

`context` contains anchor; complete physical a0; changed set A; for each member its user ID, reference/selected physical actions, selected Q1 row, incumbent Q1 row, and `missing_incumbent`; affected-beam rows with occupancy before/after, activation before/after, shared capacity, interference summary, and capacity margin; and global resource features. Trainable A has size 2–4. Larger evacuation sets use a declared ≤4 capped decomposition and set `capped_decomposition=true`. Pair reporting credit is Ψ/2 each; Shapley credit is exact over all subsets for |A|≤4 and reporting-only.

Coalition shard `mcrl-v025-stagec-c3-coalition-shard-v1` authenticates row count/digest, row schema, TRAIN, and maximum coalition size four. `CoalitionBatch` stores invariant vectors, scalar Ψ/κ targets, stable identities, source identity, and authority digest.

## 6. Learner, neutral sources, and seeds

Q1/Q2 use deterministic pairwise zero-bootstrap regression with a BASE-zero gauge. The claim is a supervised surrogate claim, not a Bellman-value or optimality claim. C3 is `PsiHat_theta(Z_t,a0,A,a_A)`: one scalar set-conditioned head. Its input is symmetric sum/max pooling over changed-user vectors (selected Q1 row, incumbent row, `missing_incumbent`) concatenated with masked/padded ≤4 affected-resource rows (occupancy before/after, activation change, shared capacity, interference summary, cap margin). A two-layer MLP consumes that vector. Physical IDs remain authenticated in rows but are not arbitrary numeric features. The output is multiplied by `1[|A|>=2]`, giving exact empty/singleton zeros.

One source epoch is C1 → C2 → C3. Checkpoints every 100 epochs store completed epochs, `route_update_count=3*epochs`, batch/schema/neutral digests, learner seed, shared initialization, all retained heads, source map, optimizer state, and `zero_bootstrap=true`.

The 12 learner seed domains are exactly `V025_LEARNER/seed/{1..12}` and use the repository domain-SHA seed rule. Their derived integers are `6407676579069309528, 925030429265975792, 5166716249291843642, 7234013715671416945, 3155344545377116990, 6114226365011333154, 2539879246662512149, 2306713132836500212, 1437152739566466432, 389903013832883586, 7291913070596938501, 5683607794651051129` in domain order. Each lineage serializes one initialization and clones it into all learned arms. World and learner seeds remain separate; BASELINE's implementation SHA is bound in the allocation manifest.

Every neutral source seal has exactly: `generator`, `labels`, `support`, `strata`, `overlap`, `row_weights`, and `optimization_dose`, plus route and digest. "Identical batches" means identical within a route/source identity. DROP checkpoints retain/update/deploy all heads; the neutral-trained head must differ from initialization.

## 7. Four named experiments (separate schemas)

| Experiment | Schema | Definition |
|---|---|---|
| Learned neutral-source | `mcrl-v025-learned-neutral-source-experiment-v1` | FULL, DROP_C1, DROP_C2, DROP_C3, ALL_NEUTRAL_CONTROL, external BASELINE. Route DROP substitutes its sealed neutral source; all heads remain. Primary wording is the contract's informative-source wording. |
| Oracle factor-score removal | `mcrl-v025-oracle-factor-score-removal-v1` | Same selector/catalogue; remove exactly one exact C1/C2/C3 score. Physics regime map only. |
| Checkpoint knockout | `mcrl-v025-checkpoint-knockout-v1` | Zero one deployed checkpoint contribution with machinery fixed. Reliance/hidden restoration only. |
| Architecture removal | `mcrl-v025-architecture-removal-v1` | Named `NAMED_NOT_RUN`; outside build 2. |

Zero C3 marginal ends the positive C3 claim in this scope. An upper interval excluding the margin supports no practically relevant benefit; lower-bound failure alone is inconclusive. No outcome-contingent redesign is allowed.

## 8. Shared selectors and operational budget

`ProfileSelector` supplies S3, S0, and S_UNI modes. S3 optimizes complete normalized C1+C2+PsiHat over the common catalogue. S0 substitutes exact Ψ. S_UNI starts at BASE, evaluates every legal unilateral alternative with the same nominal physics at each iterate, takes the stable strict improvement, atomically commits only the final profile, and reports local-optimum certification.

BASE/a0 is constructed, conflict-repaired, resolved, and validated before the coordinator begins. The runner owns a 10.0 s wall timer and cancellation; the remaining 20.08 s is reserved for sensing, transport, validation, and commit. Timeout executes the prevalidated a0; misses and their B/E/QoS remain in the endpoint.

Capability manifest `mcrl-v025-stagec-deployment-capability-v1` fields are: schema; code/physics/catalogue digests; coordinator wall budget and decision interval; reserved interval use; inputs/capabilities; timer enforcement; BASE-first rule; deadline fallback; telemetry sources and ages; roster and beam-specific cross-gain coverage; model assumptions; calibration source; worker hardware/count (`sat`, four processes); cache policy (`cold_per_anchor_no_warm_cache`); catalogue bounds; solver limits; memory limit; missing-data handling; measured end-to-end latency samples/count/p50/max; manifest digest.

## 9. Panel, estimator, and decision

D1 claim panel: six arms × 12 learner seeds × two worlds per TRAIN date over approximately 160 dates (150–170 accepted by the manifest validator), approximately 30 steps/world, no TEST. Claim dates are disjoint from probe, calibration, rehearsal, and KAT activity; legacy overlap is disclosed.

D2 endpoint is pooled ΣB/ΣE. Primary interval is the arms-paired two-way pigeonhole bootstrap: independently resample date and learner-seed levels, apply product weights, recompute additive numerators/denominators and ratios in every draw, then take central 2.5/97.5 percentiles with NumPy linear interpolation. One-way cluster bootstrap and delta method are supplementary. Seedwise paired effects are reported. EE margin is a strictly greater than +0.5% lower endpoint. QoS uses additive numerators/denominators inside draws.

D3 `B=0,E>0` is defined EE zero. A zero E denominator makes EE undefined and is counted without substitution. For relative QoS margins, DROP zero with FULL positive is `FAIL_UNDEFINED_DENOMINATOR`; both zero is non-inferior by rule. D4 is one conditional intersection–union conjunction for `a-r0`: all three FULL−DROP EE/QoS components pass. Component intervals are descriptive; no component-wise discovery is claimed. All other cells are exploratory and reports say TRAIN-only.

## 10. Harness and mandatory synthetic gate

STARTED precedes outcome work in an append-only hash chain. Canonical write-once receipts carry raw steps and additive ledgers; merge reaggregates from rows. Conformance proves NULL≡BASE per step, every arm's real-step dry run when authorized, receipt hashes, authority completeness, and one terminal adjudication.

T1 is the exhaustive three-user/two-action/three-step decomposition/intervention KAT. T2 is the information-twin interaction reversal, leakage/relabel/repair/timer/additive-placebo production-path KAT. T3 feeds raw receipts through `merge_receipts` and runs Monte Carlo calibration through the identical production `infer_cluster_totals` core for 3/5/10% date SD, 1% seed SD, five and 12 seeds, least-favourable null, undefined cells, and QoS rejection. All are synthetic and must finish together in less than five minutes.

## 11. Remaining CONTROLLER_DECIDE items

Every remaining item is unresolved before real source generation:

1. `CONTROLLER_DECIDE FORMAL-LEARNER-LITERALS`: copy the V0.23 heterogeneous Catfish trainer's frozen architecture, optimizer, batch, epoch-budget, stopping, and serialization values into the seal without retuning; change only sealed input dimensions and give the set head the same optimizer settings.
2. `CONTROLLER_DECIDE COALITION-FEATURE-SCALES`: freeze numeric scales for the now-fixed selected/incumbent Q1 rows, missing flag, and affected/global resource inputs.
3. `CONTROLLER_DECIDE LARGER-EVACUATION-CAP`: freeze which ≤4 subsets/decompositions label each larger evacuation and their row weights.
4. `CONTROLLER_DECIDE NEUTRAL-SOURCE-SEALS`: bind real generators, labels, support, strata, overlap, row weights, optimization dose, and digests for C1/C2/C3.
5. `CONTROLLER_DECIDE CATALOGUE-CB2`: seal decision 4/CB-2 profile construction, bounds, authentication, and any learned pruning.
6. `CONTROLLER_DECIDE FORMAL-ALLOCATION-MANIFEST`: the assembler must seal exact dates, worlds, starts, 12 derived seed values, 30-anchor coverage, stride, roles, legacy overlap, bootstrap draws/seed, external BASELINE implementation SHA-256, and manifest digest.
7. `CONTROLLER_DECIDE OPERATIONAL-CAPABILITY-VALUES`: seal real telemetry provenance/ages, roster/cross-gain coverage, calibration/model assumptions, catalogue bounds, solver/memory limits, missing-data handling, and measured cold-cache latency distribution on `sat` with four processes.
8. `CONTROLLER_DECIDE CAUSAL-OPERATIONAL-VARIANT`: if an operational claim is made, seal causal ephemeris/forecast inputs and action-effective-time convention; the retrospective nearest-TLE benchmark alone cannot support it.

Until these are sealed and the controller issues PHYSICS-GO, admission is HOLD and no real source generation or successor training is permitted.
