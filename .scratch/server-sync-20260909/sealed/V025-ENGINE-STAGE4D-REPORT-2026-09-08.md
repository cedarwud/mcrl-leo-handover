# V0.25 engine stage-4d report — 2026-09-08

## Disposition

**HOLD / REAL-ANCHOR GATE FAILED.** The binding stage-4c gate changes were
implemented and independently exercised, but the required quarantined-world
real anchor still exceeds the one-worker coordinator budget. The complete
14-arm anchor took 34.430552590 s; the catalogue had 1,004 rows and therefore
passed the <=1,500 row-count check. The coordinator took 24.663217761 s
against the 10 s gate; the
five-boundary stage-2 forecast dominated at 18.328741991 s and by itself
exceeded the budget.

Decision item 6 therefore stops stage 4d here. No formal R2 manifest,
calibration, allocation, rehearsal, stride, smoke, or formal unit outcome was
opened. No additional approximation is proposed or applied.

## Binding 4c-gate changes

- Set-score decomposition now requires only empty, singleton, and complete-set
  outcomes: `|A|+2` rows, hence O(|A|). It always reports every `d_i` and the
  set-level `Psi_A`.
- Exact per-user Shapley interaction credit is reporting-only for `|A| <= 4`.
  Larger sets emit an empty per-user vector and
  `credit_split=NOT_COMPUTED_LARGE_SET`. Selection and validation do not depend
  on a split.
- Stage-1 immediate scoring uses boundary `k=0` only. Stage-2 continuation uses
  `{0,12,24,36,47}` for the shortlist; committed profiles and endpoints remain
  on all 48 boundaries.
- The bounded catalogue cap is 1,500 rows and the measured phase table carries
  `catalogue_row_count`.
- A deadline miss atomically commits validated BASE for every set-level arm;
  the large-coalition exception path is gone.
- The scalar `CONVERGED_SLOW` length mismatch is fixed, invalid forecasts emit
  `INVALID` rows rather than raising while constructing their margins, the
  batch full-grid endpoint again matches the frozen stage-4b value, smoke and
  nonformal runs no longer claim formal R2 namespaces, and receipt
  reaggregation/conformance checks were strengthened.
- S_UNI now exhausts the full legal unilateral option set at the same k=0
  nominal view and ranks `F + kappa*Phi` relative to the same incumbent. It has
  a separate 10 s comparator budget, reports its iteration count and
  termination certificate, and a coordinator miss cannot discard a successful
  comparator result.
- Formal world-manifest construction now writes one immutable, digest-bound
  prepared tape per world/profile; unit processes load that tape across
  settings. Calibration similarly constructs each calibration world/profile
  once and reuses it across settings.
- The calibration API/manifest key is now dimensionally correct:
  `kappa_bits_per_user_step`. Loading the former key remains supported, while
  new manifests emit only the corrected name.

## Independent KATs added in this pass

`tests/physics_v025/test_stage4d_gate.py` contains these non-self-derived
discriminators:

1. `test_large_set_decomposition_is_linear_and_has_no_credit_split`
2. `test_small_set_shapley_is_reporting_only_and_exact`
3. `test_full_48_boundary_endpoint_matches_frozen_stage4b_bits`
4. `test_batch_and_scalar_slow_certificates_agree`
5. `test_two_stage_top_m_reports_agreement_and_miss`
6. `test_stage1_is_k0_stage2_is_five_boundaries_and_rows_are_bounded`
7. `test_s_uni_searches_full_legal_set_and_receipts_termination`
8. `test_matched_anchor_ledger_emits_all_five_physical_event_kinds`
9. `test_reuse_mask_is_reciprocal_and_chain_colour_is_unique`
10. `test_zero_legal_user_is_null_in_every_nonbase_catalogue_row`
11. `test_conformance_rejects_opening_dependency_mutation`
12. `test_reaggregation_rejects_payload_mutation_even_with_rehashed_row`
13. `test_nonformal_and_smoke_world_indices_fail_closed`
14. `test_visibility_crossing_uses_the_exact_ten_degree_floor`
15. `test_invalid_forecast_row_has_negative_margins_without_constructor_error`
16. `test_live_legality_stops_at_boundary_17_for_visibility_and_d2`
17. `test_committed_48_boundary_trajectories_match_scalar_resolution`
18. `test_s_uni_uses_incumbent_relative_phi_in_k0_objective`
19. `test_reaggregation_recomputes_every_distribution_and_rekey_summary`
20. `test_formal_world_tape_is_built_once_and_reused_across_settings`
21. `test_dense_and_scalar_evaluation_enter_through_common_resolver`
22. `test_common_resolver_rejects_mixed_mode_arguments`

The focused stage-4d suite passed 22/22. The handover discriminator was also
expanded to `test_h_and_sh_treatments_change_both_rate_architecture_twins`,
covering both a-r and a-γ 0/H and S/SH pairs. An additional executed-receipt
KAT covers all 31 matrix settings on one provider-built tape and proves their
receipts pairwise distinct. The 15 functions classified by
the stage-4 audit as tautological/self-derived were removed; these behavioral
KATs replace that inventory rather than comparing production values to
production-derived expected values.

Final verification: `python -m pytest -q tests/physics_v025` passed all 167
collected cases; the runner compiles cleanly and `git diff --check` passes.
The stage-4d KAT source digest is
`efff3b0bb41882173f12ca88427133e9dd5c67081ad677b8cd08ecb6adcf2acf`;
the current code-authority aggregate is
`e026fc7a3fd0ddf9a6fe3d501973ec8aca09505da9e3f2f49a88963f94356297`.

## Real-anchor gate

Development namespace: quarantined `V025_PROBE/world/1`. Setting: `a-r0`.
Carrier: `nearest-eligible`. Declared arms: 14. Worker count: 1. The same
timing-only calibration fixture used by stage 4c was retained so this measures
the code-path change rather than a changed price. Provider construction was
timed separately and no artifact was written.

| Phase | Seconds | Gate note |
|---|---:|---|
| provider, four-step diagnostic tape | 21.482488605 | constructed once for the world |
| catalogue | 1.772909427 | 1,004 rows; PASS <=1,500 |
| stage-1 k=0 scores | 4.010991145 | binding decision-instant view |
| stage-2 five-boundary forecasts | **18.328741991** | **dominant; alone FAILS 10 s** |
| selection | 0.008175172 | deployable set-arm argmax |
| validation / BASE fallback | 0.542052921 | bounded; no powerset expansion |
| named coordinator-phase sum | 24.662870656 | FAIL >10 s |
| measured coordinator path | **24.663217761** | **FAIL >10 s** |
| S_UNI comparator | 9.749503436 | own 10 s budget; 2 iterations; deadline certificate |
| ledger and receipts | 0.015543681 | completed for all 14 arms |
| measured anchor after tape exists | **34.430552590** | PASS <=60 s |
| enclosing anchor call | 34.459668001 | includes Python call overhead |
| provider plus enclosing anchor | **55.942156606** | conservative one-worker total; PASS <=60 s |

The phase sum differs from the coordinator timer by 0.000347105 s of timing
bookkeeping between phase probes. Stage 2 is 74.32% of the measured coordinator
path. The pre-fallback stage-1 and stage-2 top choices disagreed on this anchor;
the timer correctly committed BASE for all set arms.

The measured selected receipt consequently reports `EXACT_TRIVIAL` credit for
the committed BASE. The independent six-user KAT is the evidence that a
non-fallback large set uses `|A|+2` outcomes and reports
`NOT_COMPUTED_LARGE_SET` without attempting Shapley expansion.

## Stage-4c audit rows

The pass closes the pre-gate defects and discriminator gaps for rows 11–13,
17–32, 35, and 36: full-legal S_UNI, atomic BASE fallback,
reporting-only Shapley, both handover twins, reciprocal reuse, zero-legal
nulling, independent KAT replacement, executed 31-setting receipts, top-M
post-forecast reporting, provider reuse, corrected kappa units, dependency
mutation, five-event matched-anchor ledger, field-by-field reaggregation,
conformance, boundary-17/10° stopping, invalid forecasts, and development
namespace fail-closure are now exercised. Dense catalogue and scalar execution
both enter through the public `resolve_configuration` seam, and production
forecast rows pass through `project_three_offsets`; because no encoded C2
feature rows are emitted, the C2 state-schema digest is not stamped. The dense
kernel also retains an independently checked scalar trajectory equivalence KAT
(three configurations, 48 boundaries; energy within 1e-9 J and bits within
2e-6). Rows 6–8 are formal-execution rows and remain unopened by the gate.

## Not run after the gate

| Item | Result |
|---|---|
| six immutable `V025_PROBE_R2` / `V025_CAL_R2` manifests | `NOT_RUN_REAL_ANCHOR_GATE` |
| allocation manifest and claim-date reservation | `NOT_RUN_REAL_ANCHOR_GATE` |
| exact 30-step × two-world a-r0 calibration | `NOT_RUN_REAL_ANCHOR_GATE` |
| three-anchor rehearsal / q / concurrency-20 projection | `NOT_RUN_REAL_ANCHOR_GATE` |
| sealed stride | `NOT_RUN_REAL_ANCHOR_GATE` |
| 10-anchor development smoke and SMOKE table | `NOT_RUN_REAL_ANCHOR_GATE` |

R7 remains exposed beside R1–R6 as the exploratory 25 Mbit/s regime, digest
`3685bedd3abfb4dc4ca6f363b4a396422ee2d87892ba0473faad356156a24c0b`. No R2
receipt or claim-panel data was opened.

## Required controller decision

The 5-boundary stage-2 forecast needs a newly authorized implementation design
or approximation that brings its 18.33 s below the remaining coordinator
budget. The current 5-boundary rule, top-M plus mandatory rows, three offsets,
and one-worker constraint are retained unchanged pending that decision.
