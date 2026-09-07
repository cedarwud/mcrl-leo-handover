# V0.23 source-shard artifact schema (fit-input contract)

This is the durable boundary between the physical/source worker and the fit
worker.  A source shard is one directory per world.  Its JSON index is the
canonical, human-readable receipt; its NPZ arrays carry the complete numeric
payload needed to reconstruct the immutable V0.23 objects without opening the
simulator again.

## Files

```text
source/world-<world>.json                 # canonical ASCII index/receipt
source/world-<world>.arrays.npz            # compressed numeric sidecar
source/world-<world>.arrays.npz.sha256     # hash of exact NPZ bytes
```

The runner's existing `source/world-<world>.json` remains the shard receipt
consumed by `run_source_stage`.  The `arrays` object inside it binds the
sidecar's relative path, byte SHA-256, NPZ format version, and each array's
dtype/shape/SHA-256.  The JSON receipt's existing
`enumeration_sha256`, `topology_sha256`, `teacher_sha256`, and
`surface_sha256` fields are canonical hashes of the corresponding JSON
objects below, not hashes standing in for the data.

## Index object

Top-level fields are the existing gate identity fields plus:

```text
schema, status, claim_ceiling, contract_sha256,
preflight_manifest_sha256, split, world,
learner_update=false, episode_training=false, test_split_opened=false,
source_artifact_schema="...-source-artifact-v1",
source_artifact_version=1,
world_receipt,
ephemeris_validation,
q12_background,
anchors,
enumeration,
topology,
teacher,
surface,
diagnostics,
arrays,
```

`world_receipt` records runtime identities and mutation guards:

```text
world, field_component, field_root_digest, phase_count=9,
anchor_ids, q1_parameter_sha256, q2_parameter_sha256,
environment_initial_digest, environment_final_digest,
rng_initial_digest, rng_final_digest,
source_rollout_state_transition_observed,
test_split_opened=false, learner_update=false, episode_training=false
```

`q12_background` records the frozen Q1/Q2 source and model provenance:

```text
lineage, checkpoint_path, checkpoint_sha256,
q1_model/config/update-count, q2_model/config/update-count,
lambda_hex, kappa_hex, q12_unit, state_schema, state_schema_sha256
q12_authority: authority/checkpoint/contract/source hashes, OPS-3 horizon,
target-free Q2 schema, historical runtime-default lambda, and an explicit
false receipt for use of that historical lambda in the diagnostic target
```

## Anchor table

`anchors` is ordered by phase 1 through 9.  Every anchor object contains:

```text
anchor_id, phase, predecision_sha256,
native_observation_provenance, state_schema, state_schema_sha256, state_sha256,
q12_snapshot_sha256, q12_model_sha256, q12_source_state_sha256,
q12_event_sha256, reference_actions_sha256,
topology_sha256, topology_status, retained_for_fitting, retention_status,
class_counts, pair_count, no_close_count,
enumeration_sha256, teacher_sha256, surface_sha256,
profile_count, draw_count=32,
nonmutation_receipt, c1_diagnostic, c2_diagnostic
```

The JSON index includes complete topology records, not merely their digest:

```text
topology.reference_source_occupancies
topology.pairs[]                    # pair id, users, actions, destinations,
                                    # eligible actions, digests
topology.no_close_controls[]        # all controls and optional actions
topology.exclusions[]               # every non-retained reason/count
```

All eligible exact-two pairs are present in source/user/action order.  No
first-qualified selection is allowed.  The index also records the declared
counts for exact-two candidates, opening-infeasible pairs, missing destination
pairs, occupancy-three controls, unsupported cells, reference cells, legal
controls, and masked cells.

## Numeric sidecar arrays

Every array is C-contiguous and named in the index.  Required arrays are:

```text
# one row per enumerated noninitial anchor, concatenated by phase order.  The
# boolean/status arrays identify which anchors have a fitting surface.
anchor_phase                  int64   (A,)
anchor_status                 uint8   (A,)         # 1=retained, 0=enumerated-only
anchor_retained               bool    (A,)
anchor_content_digest         ASCII   (A,64)
anchor_view_content_digest    ASCII   (A,64)
anchor_topology_content_digest ASCII  (A,64)

# per enumerated anchor Interface-A state; fit workers select rows where
# anchor_retained is true.
action_context                float32 (A,U,28,29)
tokens                        float32 (A,U,28,U+1,38)
token_mask                    bool    (A,U,28,U+1)
action_mask                   bool    (A,U,28)
opening_feasibility           bool    (A,U,28)
reference_actions             int64   (A,U)
q1_values                     float64 (A,U,28)
q2_values                     float64 (A,U,28)
q12_values                    float64 (A,U,28)
physical_keys                 int64   (A,U,28,2)

# target-free OPS-3 input and independently recomputable repriced C2
# diagnostic.  The feature surface/state do not contain targets.  Teacher
# values are recomputed at the frozen V0.20 lambda, never copied from the
# historical OPS-3 runtime default.
q2_state_matrix               float32 (A,U,448)
q2_feature_surface            float64 (A,U,28,16)
q2_teacher_values             float64 (A,U,28)
q2_persistence                float64 (A,U,3,28)
q2_rate_bps                   float64 (A,U,3,28)
q2_marginal_power_w           float64 (A,U,3,28)
q2_required_power_w           float64 (A,U,3,28)
q2_horizon                    int64   (A,)

# one row per enumerated pair and member (P,2); pair_retained identifies rows
# materialized in a fitting anchor surface.
pair_anchor_index             int64   (P,)
pair_id                       ASCII   (P,256)
pair_user_ids                 int64   (P,2)
pair_action_ids               int64   (P,2)
pair_target_by_draw           float64 (P,32,2)
pair_target_mean              float64 (P,2)
pair_class                    uint8   (P,2)       # SUPPORTED=3
pair_retained                 bool    (P,)

# all profile draws; one row per pair/draw, profile order 00/10/01/11
draw_pair_index               int64   (P*32,)
draw_pair_id                  ASCII   (P*32,256)
draw_index                    int64   (P*32,)
profile_actions               int64   (P*32,4,U)
profile_bits                  float64 (P*32,4,U)
profile_link_rate_bps         float64 (P*32,4,U)
profile_link_power_w          float64 (P*32,4,U)
profile_link_sinr             float64 (P*32,4,U)
profile_energy_j              float64 (P*32,4)
profile_g_bits                float64 (P*32,4)
profile_system_power_w        float64 (P*32,4)
profile_fixed_power_w         float64 (P*32,4)
profile_served                bool    (P*32,4,U)
profile_active_beam_keys      int64   (P*32,4,K,2)
profile_active_beam_counts     int64   (P*32,4)
profile_active_satellites      int64   (P*32,4,S)
profile_active_satellite_counts int64  (P*32,4)
profile_beam_power_w           float64 (P*32,4,K)

# exact formula and diagnostics, keyed by pair/draw/member
z3_bits_by_draw               float64 (P*32,2)
z3_normalized_by_draw         float64 (P*32,2)
formula_identity_residual_bits float64 (P*32,)
ratio_identity_value_bits     float64 (P*32,)
joint_ee_bits_per_j            float64 (P*32,)
nonmutation_flags             bool    (P*32,5)
common_field_digest            ASCII   (P*32,64)
action_digest                  ASCII   (P*32,4,64)
ratio_cross_product           float64 (P*32,)
ratio_sign                    int8    (P*32,)
ratio_tolerance               float64 (P*32,)
ratio_local_tolerance         float64 (P*32,)
formula_own_bits              float64 (P*32,2)
formula_nonfocal_bits         float64 (P*32,2)
formula_d_bits                float64 (P*32,2)
formula_joint_delta_bits      float64 (P*32,)
formula_joint_delta_energy_j  float64 (P*32,)
formula_joint_surplus_bits    float64 (P*32,)
formula_interaction_bits      float64 (P*32,)
formula_interaction_energy_j  float64 (P*32,)
formula_interaction_surplus_bits float64 (P*32,)
formula_equal_share_bits      float64 (P*32,)

# raw no-close controls, one row per declared control and draw.  Ineligible
# controls have control_evaluated=false and zero-filled numeric profile cells;
# their complete reason remains in the JSON index.
control_id                    ASCII   (C,256)
control_phase                 int64   (C,)
control_source_key             int64   (C,2)
control_member_users          int64   (C,3)
control_eligible              bool    (C,)
control_index                 int64   (C*32,)
control_draw_index            int64   (C*32,)
control_evaluated             bool    (C*32,)
control_profile_actions       int64   (C*32,4,U)
control_profile_bits          float64 (C*32,4,U)
control_profile_link_rate_bps float64 (C*32,4,U)
control_profile_link_power_w  float64 (C*32,4,U)
control_profile_link_sinr    float64 (C*32,4,U)
control_profile_energy_j      float64 (C*32,4)
control_profile_g_bits        float64 (C*32,4)
control_profile_system_power_w float64 (C*32,4)
control_profile_fixed_power_w float64 (C*32,4)
control_profile_served        bool    (C*32,4,U)
control_profile_active_beam_keys int64 (C*32,4,Kc,2)
control_profile_active_beam_counts int64 (C*32,4)
control_profile_active_satellites int64 (C*32,4,Sc)
control_profile_active_satellite_counts int64 (C*32,4)
control_profile_beam_power_w  float64 (C*32,4,Kc)
control_source_present        bool    (C*32,4)
control_nonmutation_flags     bool    (C*32,2)
control_common_field_digest    ASCII  (C*32,64)
control_action_digest          ASCII  (C*32,4,64)
```

Because active-beam and satellite vectors have variable cardinality, the NPZ
uses fixed K/S dimensions equal to the largest complete vector in this shard
(and Kc/Sc for controls) and stores the corresponding counts; unused slots
are filled with -1 for keys/IDs and 0 for powers.  The JSON sidecar metadata
records K/S/Kc/Sc and sentinel rules.

For a simpler implementation, the same arrays may be emitted per anchor in
`anchor-<phase>.npz`; the index must then contain one relative path and hash
per anchor.  A fit worker must support either only after the schema version is
explicitly raised.  Version 1 uses one world-level NPZ.

## Recomputability and safety rules

1. JSON is canonical ASCII (`sort_keys`, compact separators, no NaN/Infinity).
2. NPZ is loaded with `allow_pickle=False`; object arrays are forbidden.
3. Arrays are hashed with dtype, shape, and C-order bytes.  No digest-only
   representation is accepted as a fit input.
4. The fit worker reconstructs `C3View`, `LCSRSAnchorCapture`, topology,
   `LCSRSPairTargets`, `LCSRSAnchorSurface`, and `LCSRSAnchorRecord` from the
   sidecar and independently verifies every runtime digest before fitting.
5. Profile rows retain all 32 draws and all 00/10/01/11 profiles.  Partial,
   no-close, negative, unsupported, reference, and masked records are not
   silently removed; only the frozen surface class mask excludes them from
   the learner loss.
6. The artifact does not contain TEST rows, learner updates, a post-selection
action, or a sign-filtered subset.  It is development evidence only.

## Fit-side handoff (V0.23 adapter v1)

The source directory is consumed by
`v023_lcsrs_fit_adapter.V023LearnerAdapter` only after
`source-manifest.json` has sealed all eight child byte hashes.  The adapter
reopens every child with `load_v023_world_source_artifact`, prepares the exact
seven-world LOO training source plus one untouched held-out world, and builds
one fold-local `MCRL_V023_LCSRS_MATCHED_PLACEBO_V1` mapping.  The held-out
world is never used to construct the learner targets or the placebo.

One fit receipt is written beside the runner-owned
`fit/world-<world>/seed-<seed>/<arm>.json` as these write-once sidecars:

```text
<arm>.model.npz              # state_dict tensors, no pickle/object dtype
<arm>.model.npz.sha256
<arm>.fit-receipt.json       # complete 2,000-loss learner receipt
<arm>.metrics.npz            # identities, predictions, true targets, losses
<arm>.metrics.npz.sha256
<arm>.metrics.json            # metric values and every held-out denominator
<arm>.placebo.json            # complete fold mapping and coverage
```

The model NPZ binds both per-tensor dtype/shape/content digests and the
logical `lcsrs_c3_network_sha256`.  The metrics NPZ uses fixed-width ASCII
anchor IDs and numeric world/user/action columns, so loading always uses
`allow_pickle=False`.  Metrics are recomputed by the adapter with the frozen
`evaluate_lcsrs_heldout_rows` function against unchanged true SUPPORTED rows;
an injected fit function may return only a network and a valid 2,000-loss fit
receipt and cannot provide held-out metrics.  Every fit payload retains the
source-manifest hash, LOO identities, placebo key/hash/coverage, model and
metrics sidecar hashes, fit receipt, sign/Spearman denominators, and closed
TEST/episode flags.  This is a fit artifact boundary, not a scientific PASS
or an efficacy result.  Full-roster composition and independent gate
recomputation remain outside this schema.
