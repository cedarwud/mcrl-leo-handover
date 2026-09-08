## Audit outcome

The source hash in the fix report matches the current provider (`7140f116…`). The provider-specific KAT file passes: 19 cases in 97.18 s. The full physics suite reached 120 passes and one environment-only error because the read-only sandbox cannot create pytest’s temporary directory; therefore I could not independently reproduce the report’s “121 passed” receipt.

I count 37 FIXED, one correctly REBUTTED, and 12 NOT ADDRESSED across 50 audited items. The main readiness blockers are:

- A canonical 30-step array tape has no memory/time receipt. The report measures only world state plus one step, while [build_world_tape](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/tapes.py:853) retains every requested step array.
- Public manifest attestation is incomplete: exact start UTC, provider hash, split-rule hash, role, learner seed, and mobility/fading stream identities are absent; `"TRAIN"` is hardcoded at [tapes.py:899](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/tapes.py:899).
- [PrimitiveStepArrays.__post_init__](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/tapes.py:288) validates only time finiteness, not all floating primitive arrays.
- The required total-interference KAT computes the legacy result but never compares the provider total to it.
- The provider report contains no requested UTC/frame approximation bounds.

Sources: [provider](/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py), [KATs](/home/sat/mcrl-v025-codex-ws-provider/tests/physics_v025/test_provider_legacy.py), [fix report](/home/sat/mcrl-v025-codex-ws-provider/V025-PROVIDER-FIX-REPORT-2026-09-08.md), [pre-audit](/home/sat/mcrl-hub/.scratch/multi-catfish-v023-controller-handoff-20260907/V025-PROVIDER-PREAUDIT-CLAUDE-OPUS-2026-09-08.md), [provider decisions](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-PROVIDER-2026-09-08.md), [pipeline decisions](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-PIPELINE-AUDIT-A-2026-09-08.md).

KAT labels below: I = independent oracle/behavioral check; T = tautological; M = mixed, weak, or non-probative; Ø = absent.

## Fourteen traps

| Item | Disposition and evidence | KAT assessment |
|---|---|---|
| T1 boresight | FIXED: aggressor’s own cell is used at P:699–742. | `test_aggressor_uses_own_cell_boresight_at_one_and_two_rings` — I |
| T2 scintillation | FIXED: legacy \(L_c\) removed at P:386–394; keyed fading applied once at P:653–660. | `test_scintillation_is_applied_exactly_once_against_hand_budget` — I |
| T3 inventory | FIXED: union of canonical legal identities at P:294–311. | `test_inventory_is_exact_realisable_union_and_standby_energy` — I |
| T4 vacuous mask | FIXED in the real action path: raw identities/predicates retained at P:242–277 and k=0 latch copied at P:471–473. | `test_mask_is_nonvacuous_and_matches_legacy_at_decision` — M: action-mask parity is independent, but false-row non-vacuity is manufactured by P:551–590/668–675. |
| T5 window/seam | FIXED in code: backward-history k=0 and forward k>0 at P:460–515; forward times P:636–640. | `test_forward_boundary_ecef_matches_direct_sgp4` — I; `test_nonzero_origin_and_forward_prime_seam_have_no_backward_jump` — M and does not oracle D2 latch transitions. |
| T6 horizon dependence | FIXED: requested length cannot alter canonical 30-step construction, P:168–176. | `test_canonical_horizon_is_invariant_to_requested_rehearsal_length` — I |
| T7 same-satellite interference | FIXED: physical identity indexing and P-10 override, P:699–785 and tapes:354–384. | `test_per_chain_colour_filter_and_same_satellite_p10_match_legacy` — I for terms/colour, but incomplete for controller’s exact total-oracle requirement. |
| T8 10° floor | FIXED as a controller-approved deviation, not legacy parity; floor at P:676 and below-floor census is zero in this world. | Mask KAT — M: census is independent for one world; legal comparison reuses provider `visible`. |
| T9 unhealthy SGP4 | FIXED for propagation: strict call P:285–292 plus NaN/subsurface rejection P:342–350. | `test_unhealthy_propagation_fails_closed` — I synthetic anchors, not end-to-end SGP4 code 6. |
| T10 units/apexes | FIXED: satellite-apex calls P:622–626/721–725; user-apex P:769–777; explicit linear path factors P:627–631. | Geometry KAT plus scintillation hand budget — I |
| T11 gain mismatch | FIXED by controller policy: V0.25 authoritative, legacy tolerance \(10^{-6}\). | `test_decision_geometry_and_scintillation_free_nominal_match_legacy` — I, but only actual wanted-link angles. |
| T12 split/seeds | FIXED operationally: exact sampler P:191–201, mobility child P:212–216, cross-process digest test. | `test_exact_train_timestamp_and_test_date_rejection` — M/T for timestamp redraw, I for TEST rejection; process KAT — I |
| T13 motion | FIXED as controller-approved approximation: motion between steps P:239–255; fixed inside each step; per-step layouts hashed. | `test_user_motion_is_recorded_per_step_and_user_count_is_sourced` — M; only first≠last. |
| T14 TLE/scale | NOT ADDRESSED overall: nearest-epoch selection and compact arrays landed, but a retained canonical 30-step tape remains unmeasured. | TLE/build KATs — M; structural checks only, no full-scale KAT. |

## Sixteen defects

| Item | Disposition and evidence | KAT assessment |
|---|---|---|
| D1 wrong boresight | FIXED, P:699–742. | Boresight KAT — I |
| D2 double \(L_c\) | FIXED, P:386–394/653–660. | Scintillation KAT — I |
| D3 missing colour filter | FIXED, tapes:369–375. | Per-chain KAT — I |
| D4 Cartesian inventory | FIXED, P:294–311. | Inventory KAT — I |
| D5 global caches | FIXED: instance-only state P:186–189; old global symbols absent. | Cross-process determinism KAT — I; bounded-memory absence is static only. |
| D6 always-true D2 | FIXED for preserved action rows. | Mask KAT — M; independent parity plus manufactured false audit rows. |
| D7 D2 distance=slant | REBUTTED; rebuttal is correct. Legacy explicitly defines Ml2 as UE–satellite slant at `env/d2.py:196,374–390`. | `test_entry_elevation_and_d2_distance_use_legacy_slant_definition` — T for `array_equal`; elevation anchors are independent but do not prove field identity. |
| D8 floor/literal TTT | FIXED in code: derived TTT P:475–482 and altitude floor P:495–514. | Cited mask/health KATs — M; neither exercises a sub-300-km forward latch or the TTT boundary. |
| D9 shrinking horizon | FIXED in production, P:786–835, with explicit censor flags. | `test_fixed_forward_horizon_has_explicit_right_censoring` — T/M: exact oracle exercises unused duplicate helper P:518–533, not production logic. |
| D10 frozen layout | FIXED: per-step layout API P:374–414 and digest binding P:893–919. | Motion KAT — M |
| D11 impossible replay guard | FIXED: removed at P:212–216. | Exact-TRAIN redraw — T; TEST rejection independently bites. |
| D12 zero-only origin | FIXED, P:535–547/636–640/923–953. | Nonzero-origin KAT — M; catches the old bug but restates the time formula and omits step>0/object-boundary coverage. |
| D13 unchecked propagation | FIXED for SGP4 outputs, P:285–292/342–350. | Health KAT — I |
| D14 hardcoded dimensions | FIXED, P:218/242–274/323. | Motion/count KAT — M; user count only. |
| D15 RF-chain terminology | FIXED by static inspection, P:3–6. | Inventory KAT cited by report — M/non-probative. |
| D16 noncanonical KAT worlds | FIXED: provider always builds 30 steps; oracle fixture explicitly builds 30. | Horizon KAT — I |

## Eleven provider decisions

| # | Disposition | Evidence and KAT |
|---|---|---|
| 1 | FIXED | Physical aggressor key and P-10 path P:699–785; per-chain KAT I, though adjacency is not asserted explicitly. |
| 2 | FIXED | Declared 10° floor and below-floor count; mask KAT M. |
| 3 | FIXED | \(10^{-6}\) legacy gain comparison in geometry KAT — I; failure output does not explicitly identify angle. |
| 4 | FIXED | Per-step movement/within-step hold P:239–255/612–660; motion KAT M. |
| 5 | FIXED | Inherited nearest-epoch selection P:226–237 and manifest TLE rows; TLE KAT M because it checks hash shape/binding, not selection optimality. |
| 6 | FIXED | Canonical 30/31 invariance P:168–176; horizon KAT I. |
| 7 | NOT ADDRESSED | Only propagated positions are validated. Other float arrays can contain NaN/inf because tapes:288–342 checks only `absolute_time_s`; health KAT does not inject a bad `PrimitiveStepArrays`. |
| 8 | NOT ADDRESSED | TEST rejection works, but split source/hash is not a public tape-manifest field. The standalone `split_binding()` KAT checks the wrong seam. |
| 9 | NOT ADDRESSED | Compact arrays landed, but digest hashes generator state rather than canonical k=0 boundary outputs, and no 30-step memory receipt exists. Process KAT proves repeatability, not digest coverage. |
| 10 | FIXED | Short providers construct the canonical universe; horizon KAT I, though it does not compare complete 3-step and 30-step tape prefixes. |
| 11 | NOT ADDRESSED | In the per-chain KAT, legacy `expected` is computed at K:279–282 but only checked `>0` at K:289; provider total is never asserted equal to it. |

## Nine pipeline decisions

| # | Disposition | Evidence and KAT |
|---|---|---|
| 1 | NOT ADDRESSED | No role-wise date-fresh claim panel in inspected provider/report/tests. Ø |
| 2 | NOT ADDRESSED | No learner-seed identity or two-way bootstrap/pooling attestation. Ø |
| 3 | NOT ADDRESSED | Public manifest omits exact start, provider hash, and split-rule hash; `"TRAIN"` is hardcoded. Existing binding KAT checks only opaque digest/standalone methods. |
| 4 | NOT ADDRESSED | `_TrainOnlyArchive` protects this provider, but no shared-factory-only production enforcement or manifest check of every opened date is demonstrated. TEST KAT covers only forced-date rejection. |
| 5 | FIXED | Nearest absolute epoch date±1 with max-age guard is inherited at P:226–237 and documented in `env/ephemeris.py:97–159`. TLE KAT M. |
| 6 | FIXED | k=0 comes from legacy backward state and k>0 advances forward, P:460–515. SGP4/time KATs are I/M but do not directly oracle the D2 state sequence. |
| 7 | NOT ADDRESSED | Manifest lacks exact start UTC, role, learner seed, and mobility/fading stream identities. Ø |
| 8 | NOT ADDRESSED for this fix pass | N=4 exists in constants and manifest, but the provider report does not address the decision and no dedicated KAT exists. |
| 9 | NOT ADDRESSED | No UTC/frame error bounds or `VERIFY_SOURCE` disposition appears in the report. Ø |

## Independent recomputations

Using a separate read-only Python construction from the legacy `ScenarioDriver`, without calling `LegacyWorldProvider`:

- Cross gain, one-ring same-satellite example: user 0, NORAD 57507, victim cell 211, aggressor cell 220.
  - Aggressor aimed at its own cell: `3.006612859632116e-21` W/W.
  - Aggressor incorrectly aimed at victim cell: `6.145926856541792e-21` W/W.
  - Wrong/correct ratio `2.044145`; error `+3.105 dB`.

- Isolated scintillation multiplier applied once:
  - 10°: loss `1.08 dB`; factor `0.779830110523259` (twice would be `0.608135001278718`).
  - 60°: loss `0.13 dB`; factor `0.970509967245490` (twice would be `0.941889596522841`).

- TRAIN world `V025_PROBE/world/1`, seed `5261619120743994529`, start `2026-01-07T09:03:56.800000+00:00`:
  - Realisable union: `2,758`.
  - Legacy-style cross product: `767 visible satellites × 75 addressable cells = 57,525`.
  - Inflation: `20.8575×`.

## Memory and timing

The report provides:

- `934,512 KiB` peak RSS for one world state plus one compact 48-boundary step.
- `937,368 KiB` for the failed one-step rehearsal.
- `17.80 s` rehearsal wall time, but that includes catalogue/certificate work and is not pure world/tape construction.
- `101.19 s` and `1,303,544 KiB` for the full test suite.

It provides no measurable canonical 30-step array-tape memory or per-world construction time. This omission matters because each `PrimitiveStepArrays` copies every field at tapes:339–342 and `build_world_tape` retains all requested steps.

The five unique misleading/tautological KAT functions counted are the mask non-vacuity, D2-distance equality, exact-TRAIN redraw, dead-helper horizon test, and formula-restating origin test. Mixed tests may still contain useful independent assertions.

VERDICT: PROVIDER=NOT_READY:full-world-scale,manifest-attestation,nonfinite-array-validation,total-interference-KAT,UTC-frame-bounds | FIXED=37/50 | TAUTOLOGICAL_KATS=5