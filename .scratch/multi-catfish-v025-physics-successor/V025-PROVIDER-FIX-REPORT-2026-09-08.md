# V0.25 provider fix report — 2026-09-08

## Result

The pre-audit's 16 defects and 14 traps have an explicit disposition below.
Twenty-nine are fixed. D7 is rebutted because the legacy D2 contract itself
defines `Ml2` as UE-to-satellite slant range, so equal `slant_km` and
`d2_distance_km` values are intentional rather than a collapsed quantity.
All provider line references below were re-resolved against the final file,
not copied from the audited 602-line `2ae94c7b…` in-progress snapshot.

No file under `src/mcrl/env/` changed. The provider remains TRAIN-only. No
learner, TEST world, calibration outcome, matrix outcome, or formal successor
outcome was opened.

## Verification receipt

- Final command: `PYTHONPATH=src /usr/bin/time -f 'wall=%e user=%U sys=%S rss_kib=%M' /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/physics_v025`
- Pytest: **121 passed**
- Provider SHA-256: `7140f116cff04f3614b5bedb5145949804eaad43df8a1cf56339b9d8d6e266d1`
- Reproducible world: `V025_PROBE/world/1`, seed `5261619120743994529`, exact TRAIN start `2026-01-07T09:03:56.800000+00:00`
- Realisable inventory: **2,758 `(NORAD, cell_id)` identities**. The pre-audit's 2,760 was measured against its moving in-progress snapshot; the final KAT independently reconstructs the union from all 30 legacy decision masks.
- Legacy-legal candidates below the declared V0.25 10° floor in this canonical world: **0** across all 30 decision instants.
- One-world-state plus one compact 48-boundary step peak RSS: **934,512 KiB** in the array construction receipt; the rehearsal process peaked at **937,368 KiB**.

The final representation is `PrimitiveStepArrays`: float fields are `float64`,
identities are integer arrays, masks are boolean arrays, and engine geometry
uses physical aggressor `(NORAD, cell_id)` keys. The old NORAD-keyed fields
remain only as aggregated compatibility views on KAT-created
`PrimitiveCandidate` objects. `ExogenousWorldTape` consumes the
identity-keyed factorized arrays directly; Python candidate objects are created
only by the KAT view, and the arrays are never JSON-serialized.

The manifest tape digest binds the exact TLE filenames/hashes, full sampled
instant, world seed, source file/hash, per-step moving layouts, provider
source hash, rule constants, inventory, and canonical k=0 primitive-input
bytes for all 30 canonical steps. Full k=1..47 arrays are regenerated inside a
unit.

## Audit dispositions

| Item | Disposition | Evidence | Non-tautological KAT |
|---|---|---|---|
| T1 interference boresight | FIX | `provider_legacy.py:699-742` indexes the aggressor's own cell centre; legacy oracle is `env/interference.py:149,214-218`. | `test_aggressor_uses_own_cell_boresight_at_one_and_two_rings` |
| T2 scintillation ownership | FIX | `provider_legacy.py:386-394` removes legacy `L_c`; `keyed_fading_gain` is the sole owner. | `test_scintillation_is_applied_exactly_once_against_hand_budget` (10° and 60° hand budgets) |
| T3 inventory cardinality | FIX | `provider_legacy.py:294-311` unions actual legal identities; no Cartesian product remains. | `test_inventory_is_exact_realisable_union_and_standby_energy` |
| T4 vacuous mask | FIX | `provider_legacy.py:242-277` preserves window/cell identities and predicates; tracked false rows are emitted at `552-590`; `tapes.py:195-196` includes reachability in legality. | `test_mask_is_nonvacuous_and_matches_legacy_at_decision` |
| T5 window direction / prime seam | FIX | Module contract `provider_legacy.py:16-21`; boundary zero copies legacy history at `471-473`, only k>0 advances at `500-515`; array time is forward at `636-640`. | `test_nonzero_origin_and_forward_prime_seam_have_no_backward_jump`; `test_forward_boundary_ecef_matches_direct_sgp4` |
| T6 horizon changes world | FIX | `provider_legacy.py:173-176` always builds 30 canonical steps regardless of requested rehearsal length. | `test_canonical_horizon_is_invariant_to_requested_rehearsal_length` |
| T7 NORAD map loses same-satellite beams | FIX | `tapes.py:219-225,347-384,451-504`; provider applies P-10 at `744-785`; legacy oracle `env/interference.py:314-316,385-392`. | `test_per_chain_colour_filter_and_same_satellite_p10_match_legacy` |
| T8 10° floor differs from legacy 0° | FIX | Declared successor predicate remains at `tapes.py:195-196`; legacy mask parity is evaluated separately and the below-floor count is reported (0). | `test_mask_is_nonvacuous_and_matches_legacy_at_decision` |
| T9 unhealthy sgp4 values | FIX | Propagation is strict at `provider_legacy.py:290-291`; finite sub-surface values and NaNs fail at `342-350`. | `test_unhealthy_propagation_fails_closed` |
| T10 units and apex order | FIX | km/degree/linear-gain calls are explicit at `provider_legacy.py:622-633,719-741`; vertex-first calls match the two legacy apex conventions. | `test_decision_geometry_and_scintillation_free_nominal_match_legacy`; hand FSPL in `test_scintillation_is_applied_exactly_once_against_hand_budget` |
| T11 transmit implementations differ | FIX | V0.25 remains authoritative; parity tolerance is 1e-6 as decided. | `test_decision_geometry_and_scintillation_free_nominal_match_legacy` |
| T12 split/seeds/self-check | FIX | Exact TRAIN draw at `provider_legacy.py:190-200`; tautological redraw removed; source binding at `366-372,879-893`. | `test_exact_train_timestamp_and_test_date_rejection`; `test_manifest_and_boundary_arrays_are_deterministic_across_processes` |
| T13 users move | FIX | Per-step positions captured at `provider_legacy.py:253-255`, exposed at `396-414`, and hashed at `898-913`. Within-step holding is the declared approximation. | `test_user_motion_is_recorded_per_step_and_user_count_is_sourced` |
| T14 TLE selection and tape scale | FIX | Legacy selection remains `env/ephemeris.py:97-159`; exact source files recorded at `provider_legacy.py:228-237`; compact array protocol is `tapes.py:252-504,678-689,853-868`. | `test_tle_split_and_provider_source_hashes_are_recorded`; `test_build_world_tape_uses_array_storage_and_input_digest` |
| D1 aggressor points at victim cell | FIX | Audit lines 429-436 moved to own-cell construction at final `provider_legacy.py:699-742`. | `test_aggressor_uses_own_cell_boresight_at_one_and_two_rings` |
| D2 `L_c` counted twice | FIX | Final `provider_legacy.py:386-394`; keyed realized fade at `653-660`. | `test_scintillation_is_applied_exactly_once_against_hand_budget` |
| D3 no co-colour filter | FIX | `tapes.py:376-378` returns exact zero for different colours before coupling. | `test_per_chain_colour_filter_and_same_satellite_p10_match_legacy` |
| D4 Cartesian inventory | FIX | Final `provider_legacy.py:294-311`; final count 2,758, not 51,282/57,525. | `test_inventory_is_exact_realisable_union_and_standby_energy` |
| D5 process-global caches | FIX | `LegacyWorldProvider` has instance fields only at `provider_legacy.py:186-188`; there are no `_STATE_CACHE`/`_BOUNDARY_CACHE` symbols. | `test_manifest_and_boundary_arrays_are_deterministic_across_processes` |
| D6 boundary-zero D2 always true | FIX | False tracked candidates use `legacy_action_index=-1` at `provider_legacy.py:552-590`; action rows preserve the independent legacy predicates. | `test_mask_is_nonvacuous_and_matches_legacy_at_decision` |
| D7 D2 distance equals slant | REBUT | Legacy `env/d2.py:196` states `ml2_definition = "slant range UE to satellite"`; the same module computes D2 from slant at `374-390`. Equal values are required. | `test_entry_elevation_and_d2_distance_use_legacy_slant_definition` |
| D8 altitude floor / literal TTT | FIX | `provider_legacy.py:475-514` derives TTT steps from constants and applies `MINIMUM_ALTITUDE_KM`; legacy oracle is `env/d2.py:92-107,374-390`. | `test_mask_is_nonvacuous_and_matches_legacy_at_decision`; `test_unhealthy_propagation_fails_closed` |
| D9 shrinking/unlabelled remaining horizon | FIX | Fixed `_FUTURE_INTERVALS` and censored flags at `provider_legacy.py:787-835`; tape fields at `tapes.py:226-227,276-279`. | `test_fixed_forward_horizon_has_explicit_right_censoring` |
| D10 layout frozen at step 0 | FIX | Per-step layout API and manifest binding at `provider_legacy.py:375-414,898-913`. | `test_user_motion_is_recorded_per_step_and_user_count_is_sourced` |
| D11 replay guard cannot fail | FIX | Guard removed; exact external draw is compared including intra-day offset. | `test_exact_train_timestamp_and_test_date_rejection` |
| D12 ignores non-zero tape origin | FIX | Origin is supplied to arrays at `provider_legacy.py:535-547,636-640` and consistently bound by object view at `923-952`; builder passes it at `tapes.py:853-868`. | `test_nonzero_origin_and_forward_prime_seam_have_no_backward_jump`; `test_build_world_tape_uses_array_storage_and_input_digest` |
| D13 unhealthy propagation unchecked | FIX | Strict propagation plus explicit validation at `provider_legacy.py:290-291,342-350`. | `test_unhealthy_propagation_fails_closed` |
| D14 hard-coded 100 and 7 | FIX | Population comes from `MobilityConfig`; action dimensions use `NUM_BEAM_SLOTS`/`NUM_SATELLITE_SLOTS` at `provider_legacy.py:242-274`. | `test_user_motion_is_recorded_per_step_and_user_count_is_sourced` |
| D15 invented RF-chain terminology | FIX | Provider contract consistently calls `(NORAD, cell_id)` a physical beam identity (`provider_legacy.py:3-6`; `tapes.py:144-156`). | `test_inventory_is_exact_realisable_union_and_standby_energy` |
| D16 KAT worlds used 1/3-step universes | FIX | Both legacy oracle and provider fixtures build the canonical 30-step universe; shorter consumer request is only truncation. | `test_canonical_horizon_is_invariant_to_requested_rehearsal_length` |

## Rehearsal

The one authorized real-provider rehearsal used TRAIN probe world 1, one
compact step, the nearest-eligible 100-user base configuration, `a-r0`, and a
one-row bounded catalogue (the stage-2 runner still requests the impossible
`28^100` Cartesian catalogue). It failed closed before arm selection:

```text
ProbeError: invalid power certificate for BASE:nearest-eligible
wall 17.80 s; user 16.80 s; system 0.99 s; peak RSS 937,368 KiB
```

This is a meaningful consequence of the fix: after physical per-beam keys
and same-satellite P-10 interference were restored, the coupled `a-r0` base
configuration was infeasible. No q or 12-arm timing is reported because zero
arms completed; inventing either would be a false receipt. The integration
state therefore remains **HOLD** pending controller handling of an infeasible
base configuration and the already-known bounded/batched catalogue change.

## Final checks

- `git diff --check`: pass
- `git diff -- src/mcrl/env`: empty
- Fresh-process manifest plus step-5 k=17/k=47 array digest: identical
- Full suite final timing: `wall=101.19 s user=95.39 s sys=5.62 s rss_kib=1,303,544`
