# V0.25 provider fix pass 2 report — 2026-09-08

## Result

All 12 `NOT ADDRESSED` rows in the fresh-context audit of fix pass 1 are
closed as `FIX`, and the five named tautological/misleading KATs now use
independent oracles.  The canonical `V025_PROBE/world/1` tape was built once
at its full retained scale: 30 executed steps plus three forecast steps.  It
stayed below the 4 GiB RSS limit.  The coupled-solve controller decision was
also applied and the bounded rehearsal completed all 12 arms.

No file under `src/mcrl/env/` changed.  The real provider remains TRAIN-only.
No TEST world, learner training, or formal successor outcome was opened.

## Verification receipt

- Branch/base: `v025/provider`, fix-pass-1 base `d4b749e8`
- Final command: `PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/bin/time -f 'PYTEST_TIME wall=%e user=%U sys=%S peak_rss_kib=%M' /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/physics_v025`
- Pytest: **127/127 passed**, exit 0
- Timing: `wall=322.24 s user=315.45 s sys=6.68 s peak_rss_kib=1,398,196`
- Provider SHA-256: `eb2b25c367c52cb1f93d78c4289306b7baef90afd0ffd4cdaf69eee8f716050f`
- Generic tape/seam SHA-256: `02fd36096049d63ae019b003e875f45a2cc342489668223fc3e4918adf7a08bf`
- `git diff --check`: pass
- `git diff -- src/mcrl/env`: empty

The first final-suite attempt reached 126 passes and exposed one incorrect
new expected string in the attestation KAT.  The implementation had emitted
the intended, more specific policy text.  The expectation was corrected and
the complete 127-test suite above was rerun from a fresh process.

## Audit closure table

| Audit item | Disposition | Evidence | Independent KAT |
|---|---|---|---|
| T14 / full-world tape scale | FIX | `LegacyWorldProvider` always constructs the 30-step universe and now retains three explicit forecast steps; `PrimitiveStepArrays` is the only production boundary representation.  The full 33-step receipt below asserts RSS `< 4 GiB`. | Standalone full-scale receipt: constructs `V025_PROBE/world/1`, measures every retained ndarray, hashes k=0/17/47 across all 33 steps, and asserts `ru_maxrss < 4*1024*1024 KiB`. |
| Provider decision 7 / all non-finite primitives | FIX | `PrimitiveStepArrays.__post_init__` enumerates every float-typed dataclass array and rejects any non-finite element with the field name. | `test_every_float_primitive_array_rejects_nan_and_infinity` discovers the float fields independently, injects both NaN and +inf into each of 12 array kinds, and requires a raise naming that field. |
| Provider decision 8 / split source at the public seam | FIX | `ProviderAttestation` exposes realised and expected split, full split identity, split-rule filename/SHA, exact start, and every opened TLE date with its split.  `ExogenousWorldTape` accepts the provider's split; `tapes.py` no longer supplies a literal TRAIN split. | `test_complete_provider_attestation_and_split_mismatch_guard` independently hashes `ephemeris.py`, classifies opened dates, and proves `replace(attestation, split=TEST)` raises. |
| Provider decision 9 / digest coverage and scale | FIX | `ExogenousWorldTape.tape_digest` hashes generating inputs plus `_step_array_digest(..., boundary_index=0)` for every retained step.  Generator object state is not traversed. | `test_manifest_digest_covers_k0_outputs_not_unused_generator_fields`: one-bit k=0 ndarray mutation changes the digest; changing an unused generator attribute does not.  Full-scale receipt is below. |
| Provider decision 11 / total interference | FIX | Provider cross gains are keyed by physical `(NORAD, cell_id)` and include same-satellite P-10 plus cross-satellite co-colour terms. | `test_per_victim_total_interference_matches_legacy_for_three_victims` builds a mixed same-/cross-satellite assignment and compares provider totals with legacy `beam_field_at_users` + `co_channel_interference` for at least three victims at relative tolerance `1e-9`. |
| Pipeline A1 / date-fresh claim panel | FIX | `provider_allocation_manifest` seals `(role, UTC date, world_seed, split)` and rejects reuse of a claim UTC date by any non-claim role before units open. | `test_claim_panel_allocation_rejects_role_date_reuse` accepts independently constructed disjoint dates and rejects an overlapping claim date. |
| Pipeline A2 / learner identity and resampling | FIX | Attestation records `world_seed` and `learner_seed` separately.  Physics matrix requires `learner_seed=None`; learner-bearing roles attest the two-way TLE-date × learner-seed pigeonhole bootstrap and within-cell world pooling. | `test_complete_provider_attestation_and_split_mismatch_guard` checks the learner-free matrix identity and exact inference policy fields; constructor validation rejects a learner seed on the physics-matrix role. |
| Pipeline A3 / complete provider/tape attestation | FIX | `ProviderAttestation` is required by `build_world_tape` and contains split identity/rule digest, exact UTC, TLE hashes, archive digest, provider source digest, role, separate seeds, stream identities, N=4, and executed/forecast partition. | `test_complete_provider_attestation_and_split_mismatch_guard` computes archive/source digests by independent filesystem reads and exercises the mismatch guard. |
| Pipeline A4 / shared factory and opened dates | FIX | `build_world_tape` is the common detachment path and requires provider attestation.  The real provider names `mcrl.physics_v025.provider_legacy.factory`; `_TrainOnlyArchive` records all opened dates and refuses TEST reads, while attestation reclassifies every opened date and rejects TEST. | Exact known TEST-date construction raises in `test_exact_train_timestamp_and_test_date_rejection`; all actually opened dates are independently classified in `test_complete_provider_attestation_and_split_mismatch_guard`. |
| Pipeline A7 / world identity | FIX | Tape manifest carries exact UTC, layout and moving-layout digests, stream identities, TLE hashes, split, role, learner seed, and world seed through its attestation and layout fields. | Complete-attestation KAT plus `test_manifest_and_boundary_arrays_are_deterministic_across_processes`; two fresh processes agree on manifest and forward arrays. |
| Pipeline A8 / N=4 refresh | FIX | Attestation and tape manifest both bind `candidate_refresh_period_n=4`; step tapes bind `refresh_phase=step_index % 4`. | `test_identity_rows_refresh_only_at_phase_zero` compares real physical-identity rows for steps 0..8: changes occur exactly at steps 4 and 8 and never at phases 1, 2, or 3. |
| Pipeline A9 / UTC and frame approximation | FIX | The `VERIFY_SOURCE` computation below bounds UTC quantisation, UTC-for-UT1 Earth rotation, and omitted polar motion at the exact decision instant. | `test_forward_boundary_ecef_matches_direct_sgp4` independently propagates the selected legacy satellite set at k=17 and k=47 and requires provider ECEF error ≤1 m; refresh-phase behavior has the dedicated KAT above. |
| Tautological mask KAT | FIX | Provider now preserves each legacy action index and separate visibility/D2/reachability predicates, including false rows. | Rewritten `test_mask_is_nonvacuous_and_matches_legacy_at_decision` compares every action row with the legacy mask, proves equality of the entire false-row set, and directly recomputes slant/elevation for additional false rows. |
| Tautological D2-distance KAT | FIX | D2's `Ml2` is the UE-to-satellite slant definition, but the expected value is no longer copied from the provider field. | Rewritten `test_entry_elevation_and_d2_distance_use_legacy_slant_definition` computes three Euclidean ECEF norms and independently inverts the legacy slant threshold to elevation. |
| Tautological TRAIN redraw KAT | FIX | The expected epoch is frozen, not obtained by replaying the provider's RNG path. | Rewritten `test_exact_train_timestamp_and_test_date_rejection` checks `2026-01-07T09:03:56.800000+00:00` and separately constructs a provider on a known TEST date to require failure. |
| Dead-helper horizon KAT | FIX | Fixed future samples begin at canonical step 29 and censorship is explicit. | Rewritten `test_fixed_forward_horizon_matches_direct_sgp4_crossings` invokes SGP4 directly, scans visibility/D2 crossings, derives expected first-passage times, and compares production arrays and censor flags without the provider helper. |
| Formula-restating origin KAT | FIX | The provider binds one non-zero absolute origin for all later step/boundary views. | Rewritten `test_nonzero_origin_is_bound_across_steps_and_rejects_drift` checks object boundaries at step 0 and step 1, then supplies an inconsistent origin and requires failure. |

## Canonical 33-step scale receipt

The measured world is `V025_PROBE/world/1`, world seed
`5261619120743994529`, exact start
`2026-01-07T09:03:56.800000+00:00`, role `physics-matrix`,
`learner_seed=None`, 30 executed + 3 forecast steps, 48 boundaries per
step, refresh period N=4.

- Tape SHA-256: `a2821328cfed0fd8185ba2ef3fe9a2bad41f708e38cb1e434e7723576e94f4c4`
- All-step boundary digest, k=0: `0e4185c4a849e341753a5b89892d7c8805483c1ef2ed1749325e5a8451773280`
- All-step boundary digest, k=17: `24c55696a273e569542f3ea657c59220e12027ba32be8bb797bafb7aaf3d5074`
- All-step boundary digest, k=47: `a1b913a01a7a23b89c6551afa2606ef3624adb2c4f3dfe75c90562db91da4d71`
- Retained ndarray bytes: **835,939,072** (797.214 MiB)
- Static ndarray bytes across steps: **4,984,000**
- Step ndarray bytes: min **24,040,160**, max **27,575,328**
- Peak RSS: **1,724,892 KiB** (1,684.465 MiB, 1.645 GiB), below the asserted **4,194,304 KiB** ceiling
- Python construction timer: **246.707583169 s**
- Process timing: `wall=247.85 s user=245.38 s sys=2.42 s peak_rss_kib=1,724,892`

Per-boundary ndarray bytes for steps 0..32 (static bytes excluded; multiply
each entry by 48 and add that step's static bytes for its retained total):

```text
[553708, 553708, 553708, 553708,
 528108, 528108, 528108, 528108,
 497708, 497708, 497708, 497708,
 571308, 571308, 571308, 571308,
 511308, 511308, 511308, 511308,
 508108, 508108, 503308, 503308,
 506508, 506508, 506508, 506508,
 524108, 524108, 524108, 524108,
 517708]
```

The 33 per-boundary entries sum to 17,311,564 bytes; ×48 gives
830,955,072 dynamic bytes, and adding 4,984,000 static bytes reproduces the
835,939,072-byte total.

### Manifest attestation captured by the scale run

- Split: `train`; expected split: `train`
- Split rule: `ephemeris.py`, SHA-256 `59494d85937ba9099982d49c6b435e03cc88b62553fde33bf755ceed3cb9efff`
- Archive-index SHA-256: `7fe064c71aa03e890a7f8c925475de64e6c8517bb08187bb2694854966b460db`
- Provider: `provider_legacy.py`, SHA-256 `eb2b25c367c52cb1f93d78c4289306b7baef90afd0ffd4cdaf69eee8f716050f`
- Opened TLE dates/classifications: `2026-01-06/train`, `2026-01-07/train`, `2026-01-08/train`
- TLE `starlink_20260106.tle`: `13077704521e385a4891ec69e6cf490e70c48534c7bc2b876b4b5d5e320f4008`
- TLE `starlink_20260107.tle`: `3788498fb71ce8abc578cb3ebae6d3c09181d75204e5619bd261bca3e48e51c9`
- TLE `starlink_20260108.tle`: `3e0a2209f1a2964bc534eef2696093397f7b9fdc566633cb4f292bd7b25fbbef`
- Mobility stream: `numpy.SeedSequence(5261619120743994529).spawn(4)[1]:mobility`
- Fading stream: `sha256-keyed:5261619120743994529|user|norad|absolute_time_ns|component`

## UTC/frame bound (`VERIFY_SOURCE`)

The decision instant is the exact timezone-aware UTC value
`2026-01-07T09:03:56.800000+00:00`.  `julian_date` preserves the day and
fraction separately.  Python's microsecond clock quantisation contributes at
most `0.5 us × 7.8 km/s = 0.0039 m` of satellite displacement.

The material approximation is `UT1 := UTC` in the IAU-82 GMST conversion.
The source contract bounds `|UT1-UTC| <= 0.9 s`.  A scan of the three frozen
TLE inputs gives maximum two-body apogee radius 6,965.838 km (NORAD 55948);
rounding outward to 7,000 km gives the hand bound

```text
delta_theta <= 7.2921159e-5 rad/s × 0.9 s = 6.56290431e-5 rad
TEME/ECEF position error <= 7,000 km × delta_theta = 0.459403 km
omitted polar motion <= 0.000500 km
UTC quantisation <= 0.0000039 km
total worst-case geometry error < 0.460 km  (report conservatively: < 0.461 km)
```

This is below the 1 km geometry budget.  It applies at k=0 and remains the
same envelope over the 30.08 s decision interval.  Candidate identities are
not refreshed inside that interval: N=4 means refresh only at decision phase
0, demonstrated at real steps 4 and 8 by the dedicated KAT.

## Coupled solve and bounded rehearsal

The controller decision is implemented as follows: iteration budget 65,536;
convergence checked on the update at absolute `1e-10 W` or relative `1e-9`;
the last 1,000 monotone changes below `1e-6 W` certify `CONVERGED_SLOW` at
budget; `INVALID` is reserved for non-finite input/update or monotonicity
failure.  Cap-bound users remain physical outputs and are separately marked
`rate_target_infeasible`.  Receipts now record certificate counts and
`converged_slow_share` per profile.

Independent solver KATs are
`test_three_user_spectral_radius_point_999_reaches_analytic_fixed_point`,
`test_jointly_unattainable_targets_converge_at_cap_and_are_flagged`, and
`test_nonfinite_coupled_power_input_is_invalid`.

The authorized rehearsal was single-threaded and bounded to one catalogue
row.  It used `a-r0`, two calibration worlds at one retained step each, and
`V025_PROBE/world/1` at one executed plus three forecast steps.  This is a
pipeline/certificate rehearsal, not a formal matrix result.

- Status: `COMPLETE`; all 12 arms completed
- Physical boundary evaluations: 96
- Provider build wall times: CAL/world/1 **19.062743 s**; CAL/world/2 **15.897902 s**; PROBE/world/1 **38.197331 s**; total **73.157976 s**
- End-to-end measured elapsed: **81.907502 s**
- Process: `wall=82.98 s user=79.97 s sys=2.99 s peak_rss_kib=1,034,468`
- Single-core CPU consumption: **79.97 s = 1.333 core-minutes**, below 10 core-minutes
- Certificates: CAL/world/1 `CONVERGED=96`; CAL/world/2 `CONVERGED=48`; PROBE/world/1 `CONVERGED=96`; `CONVERGED_SLOW=0` throughout
- Maximum reported solver update/residual: `7.835431192759756e-10` under the relative convergence criterion
- BASE nearest-eligible: `85,411,119,691.85187` bits; `7,805.004783100964` joules; 46/100 users rate-target feasible
- Rehearsal receipt SHA-256: `59f9910fc04af56e8d3949569519d4f179c895e349b4efd517ad40103424996c`

## Final disposition

`PROVIDER_FIX2=READY_FOR_FRESH_CONTEXT_AUDIT | NOT_ADDRESSED_CLOSED=12/12 | TAUTOLOGICAL_KATS_REWRITTEN=5/5 | PYTEST=127/127 | SCALE_RSS_LT_4_GIB=PASS | REHEARSAL_LT_10_CORE_MIN=PASS`
