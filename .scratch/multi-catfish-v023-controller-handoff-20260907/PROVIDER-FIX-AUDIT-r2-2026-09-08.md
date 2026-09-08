## Audit outcome

The core provider physics is repaired, and the D7 rebuttal is correct. However, 3 of the 50 audited requirements remain incomplete:

- Pipeline A1: the claim-date check only compares attestations supplied by the caller; it neither proves the allocation is complete nor records overlap with legacy development dates.
- Pipeline A2: two-way bootstrap and within-cell pooling are text fields, not implemented or enforced behavior.
- Pipeline A9: the `<0.461 km` frame bound omits the documented spherical-Earth versus WGS-72 discrepancy (~1.7 km) and has no leap-second policy.

Counts: 46 FIXED, 1 correctly REBUTTED, 3 NOT ADDRESSED.

The current hashes match the fix-pass-2 report. I independently ran all provider tests read-only: **22/22 passed**. The report records **127/127** for the full physics suite.

Links: [provider](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py), [provider KATs](/home/sat/mcrl-v025-codex-ws-provider/tests/physics_v025/test_provider_legacy.py), [tape protocol](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/tapes.py), [fix-pass-2 report](/home/sat/mcrl-v025-codex-ws-provider/.scratch/multi-catfish-v025-physics-successor/V025-PROVIDER-FIX2-REPORT-2026-09-08.md).

KAT labels: **I** = independent/behavioral oracle; **T** = tautological; **I-partial** = independent but does not cover the entire claim; **Ø** = no direct KAT.

## Fourteen traps

| Item | Disposition and evidence | KAT |
|---|---|---|
| T1 aggressor boresight | FIXED. Aggressor cell centres drive transmit angles at P:787–813. | `test_aggressor_uses_own_cell_boresight_at_one_and_two_rings` — I |
| T2 scintillation ownership | FIXED. P:473–482 removes legacy scintillation; P:741–748 supplies the sole keyed fade. | `test_scintillation_is_applied_exactly_once_against_hand_budget` — I-partial: independently anchors both components, but not the final real-tape ratio. |
| T3 inventory cardinality | FIXED. P:328–345 unions legal identities from 30 decisions. | `test_inventory_is_exact_realisable_union_and_standby_energy` — I |
| T4 vacuous eligibility | FIXED in production: frozen identity, occupancy and reachability are retained separately at P:274–309 and P:530–560. | `test_mask_is_nonvacuous_and_matches_legacy_at_decision` — I-partial: exact action-mask comparison is real; its extra lowest-elevation rows are synthetic audit rows. |
| T5 backward/forward seam | FIXED per controller policy. Boundary zero inherits legacy state; k=1…47 advances at P:548–604; times are forward at P:724–728. | Forward SGP4 and origin KATs — I-partial; no independent forward D2-latch sequence oracle. |
| T6 horizon dependence | FIXED. P:207–209 and P:271 always build the canonical universe. | `test_canonical_horizon_is_invariant_to_requested_rehearsal_length` — I |
| T7 same-satellite interference | FIXED. Physical aggressor identities, own-cell pointing and P-10 receive gain are at P:787–872 and tapes:575–599. | `test_per_victim_total_interference_matches_legacy_for_three_victims` — I |
| T8 successor 10° floor | FIXED as an approved deviation, not legacy parity. P:764 applies it; the canonical-world below-floor census is zero. | Mask KAT — I-partial, one-world census |
| T9 unhealthy SGP4 output | FIXED. Strict propagation and NaN/subsurface checks are P:325–326 and P:375–384. | `test_unhealthy_propagation_fails_closed` — I synthetic |
| T10 units/apex order | FIXED. Satellite-apex and user-apex calls are P:710–714 and P:809–813; path units are explicit at P:716–719. | Geometry and hand-FSPL KATs — I |
| T11 transmit-gain mismatch | FIXED by controller decision: V0.25 is authoritative with `1e-6` legacy comparison tolerance. | `test_decision_geometry_and_scintillation_free_nominal_match_legacy` — I |
| T12 split/seeds | FIXED operationally. Exact sampler and independent mobility child are P:223–248; cross-process determinism exists. | Frozen timestamp/TEST rejection and process KATs — I |
| T13 moving users | FIXED under the declared zero-order hold. Per-step ECEF/XY is captured at P:284–309 and exposed at P:484–501. | `test_user_motion_is_recorded_per_step_and_user_count_is_sourced` — I-partial |
| T14 TLE rule/tape scale | FIXED. Nearest selection is inherited, and production uses compact `PrimitiveStepArrays`; a full 33-step measurement now exists. | SGP4/digest KATs — I; scale receipt exists only in the report. |

## Sixteen defects

| Item | Disposition and evidence | KAT |
|---|---|---|
| D1 wrong boresight | FIXED; P:787–813. | Boresight KAT — I |
| D2 double scintillation | FIXED; P:473–482 and P:741–748. | Scintillation KAT — I-partial |
| D3 missing colour filter | FIXED; tapes:587–590 returns zero before coupling. | No direct real-provider off-colour KAT; total-interference KAT uses one colour. Downstream synthetic architecture KAT is I-partial. |
| D4 Cartesian inventory | FIXED; P:328–345. | Inventory KAT — I |
| D5 global caches | FIXED; only instance-bound world/origin state remains at P:219–221. | Cross-process determinism KAT — I |
| D6 always-true D2 | FIXED in code; frozen ineligible slots survive through P:274–309 and P:530–560. | Mask KAT — I-partial |
| D7 D2 distance equals slant | REBUTTED correctly. Legacy `d2.py:196` explicitly defines Ml2 as UE–satellite slant range. | `test_entry_elevation_and_d2_distance_use_legacy_slant_definition` — I |
| D8 altitude floor/literal TTT | FIXED. TTT derives from constants at P:563–570; altitude floor is applied at P:583–602. | Mask/health KATs — I-partial; neither directly exercises a forward sub-300-km TTT transition. |
| D9 shrinking/unlabelled horizon | FIXED. P:874–922 uses fixed 900.48-s sampling and explicit censor flags. | `test_fixed_forward_horizon_matches_direct_sgp4_crossings` — I |
| D10 frozen layout | FIXED; P:484–501 plus tape layout digests. | Motion KAT — I-partial |
| D11 impossible replay guard | FIXED; guard removed and timestamp frozen independently. | Exact-TRAIN/TEST KAT — I |
| D12 zero-only tape origin | FIXED; P:963–986 binds one origin and rejects drift. | `test_nonzero_origin_is_bound_across_steps_and_rejects_drift` — I |
| D13 unchecked propagation | FIXED; P:325–326 and P:375–384. | Health KAT — I |
| D14 hardcoded dimensions | FIXED; mobility population and slot constants are used at P:250–309. | Motion/count KAT — I-partial |
| D15 forbidden RF-chain vocabulary | FIXED by static inspection; the module consistently says physical beam identity. | Ø |
| D16 noncanonical KAT universes | FIXED; fixture and provider construct the 30-step universe regardless of requested truncation. | Horizon-invariance KAT — I |

## Eleven provider decisions

| # | Disposition and evidence | KAT |
|---|---|---|
| 1 | FIXED: per-beam physical keys and P-10 path are implemented. | Total-interference KAT — I |
| 2 | FIXED: 10° floor is explicit and canonical below-floor count is reported. | Mask KAT — I-partial |
| 3 | FIXED: `1e-6` V0.25/legacy gain policy is exercised. | Geometry KAT — I |
| 4 | FIXED: users move between steps and are held within each step. | Motion KAT — I-partial |
| 5 | FIXED: date±1 absolute-nearest TLE selection and input hashes are retained. | Attestation/SGP4 KATs — I-partial; no independent nearest-record search. |
| 6 | FIXED: horizon parameter cannot alter the 30-step universe. | Horizon-invariance KAT — I |
| 7 | FIXED: every float array is enumerated and checked at tapes:551–557. | `test_every_float_primitive_array_rejects_nan_and_infinity` — I |
| 8 | FIXED: public attestation carries split identity/rule hash/opened-date classifications; generic tape no longer invents TRAIN. | Complete-attestation and TEST rejection KATs — I |
| 9 | FIXED: k=0 bytes for every retained step enter `tape_digest`; full-scale tape is measured. | Digest mutation KAT — I; scale receipt report-only |
| 10 | FIXED: short consumers truncate the canonical world. | Horizon-invariance KAT — I |
| 11 | FIXED: three mixed victims’ full interference totals are compared to legacy helpers. | Total-interference KAT — I |

## Nine pipeline-A decisions

| # | Disposition and evidence | KAT |
|---|---|---|
| 1 | NOT ADDRESSED fully. `provider_allocation_manifest` checks claim/nonclaim overlap only among rows handed to it; it cannot establish that all prior successor roles are present, and it does not record permitted legacy overlap as v1.5 §4 requires. | `test_claim_panel_allocation_rejects_role_date_reuse` — I for the local check, incomplete for the decision |
| 2 | NOT ADDRESSED. Separate seeds are now recorded, but “two-way pigeonhole bootstrap” and pooling are only literal strings at P:454–459; no estimator or enforcement exists in the inspected implementation. | Complete-attestation KAT’s policy-string assertions — T |
| 3 | FIXED. Mandatory attestation includes exact UTC, split identity/rule hash, TLE/archive/provider hashes, role and seeds; tape binds it at tapes:807–815 and 842–873. | Complete-attestation and digest KATs — I |
| 4 | FIXED for the formal successor path. Tape construction requires attestation; real provider records/reclassifies opened dates and refuses TEST. | TEST rejection/opened-date KATs — I |
| 5 | FIXED. Absolute-nearest, future-epoch-permitted selection is retained and documented as non-causal in the controller declaration/source. | TLE/SGP4 KATs — I-partial |
| 6 | FIXED according to the controller decision: k=0 inherits legacy backward state and subsequent boundaries move forward. | Mask plus forward-SGP4 KATs — I-partial |
| 7 | FIXED. Manifest contains exact UTC, layout digests, stream identities, TLE hashes, split, role and both seeds. | Complete-attestation/process KATs — I |
| 8 | FIXED. N=4 is named as refresh cadence and real identity changes occur at steps 4 and 8. | `test_identity_rows_refresh_only_at_phase_zero` — I |
| 9 | NOT ADDRESSED correctly. The report bounds clock quantisation, UTC-for-UT1 and polar motion, but omits the audit’s leap-second policy and ~1.7-km spherical-Earth/WGS-72 discrepancy. Therefore its claimed total `<0.461 km` is not a complete reference-frame/geometry bound. The cited direct-SGP4 KAT uses the same local conversion stack and cannot validate that external bound. | Forward-SGP4 KAT — I for indexing, non-probative for this decision |

## Independent recomputations

Using read-only Python and the legacy `ScenarioDriver`, without calling `LegacyWorldProvider`:

- Cross gain, TRAIN world `V025_PROBE/world/1`, user 0, NORAD 65028, victim cell 55, one-ring aggressor cell 56:

  - Aggressor aimed at its own served cell: `7.82210739316483e-14` W/W.
  - Aggressor incorrectly aimed at the victim cell: `2.1331078096716847e-11` W/W.
  - Inflation: `272.702445×`, or `+24.356890 dB`.

- Scintillation applied once:

  - 10°: `1.08 dB`, factor `0.779830110523259`; twice would be `0.608135001278718`.
  - 60°: `0.13 dB`, factor `0.970509967245490`; twice would be `0.941889596522841`.

- Canonical TRAIN world, seed `5261619120743994529`, start `2026-01-07T09:03:56.800000+00:00`:

  - Realisable union: `2,758`.
  - Old cross product: `767` visible satellites × `75` addressable cells = `57,525`.
  - Inflation: `20.857505×`.

## Array-tape scale

From the fix-pass-2 report:

- Retained 33-step ndarray payload: **835,939,072 bytes** = **797.214 MiB**.
- Static arrays: **4,984,000 bytes**.
- Per-step retained arrays: **24,040,160–27,575,328 bytes**.
- Peak RSS: **1,724,892 KiB** = **1.645 GiB**.
- Python construction time per full world: **246.708 s**; process wall time **247.85 s**.
- Short rehearsal provider builds: **19.063 s**, **15.898 s**, and **38.197 s** for the two calibration worlds and one probe world, respectively.

One unique current KAT is tautological for the claim assigned to it: the complete-attestation test verifies bootstrap/pooling policy strings rather than executing those procedures.

VERDICT: PROVIDER=NOT_READY:claim-panel-ledger,bootstrap-enforcement,complete-UTC-frame-bound | FIXED=46/50 | TAUTOLOGICAL_KATS=1