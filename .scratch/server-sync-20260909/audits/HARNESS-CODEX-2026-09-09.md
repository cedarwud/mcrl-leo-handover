**Verdict: The harness can report assertion and scientific failures, but it cannot be trusted as a green scientific verdict: both requested baselines are non-green, one Stage-C test did not complete within 12 minutes, and parts of the suite depend on pre-existing disk artefacts.**

# Harness audit — 2026-09-09

`DIAGNOSTIC_NOT_CLAIM`: this is a harness diagnosis, not a scientific-result claim.

## Isolation and execution

The destination was already a populated, clean Git repository when the audit began. Its initial commit was:

```text
1dfc6e07a10d045d5d4ba598d0368038e4787804
2026-09-09T11:23:16Z
harness audit copy
```

All test invocations used `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, and `nice -n 15`. Tests were run serially. `/home/sat/mcrl-v025-pilot-ws` was not modified.

## 1. Baseline truth

| Subset | Collected | Passed | Failed | Skipped | Xfailed | Errors | Exit status | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `tests/physics_v025` | 167 | 162 | 5 | 0 | 0 | 0 | 1 | Completed in 160.50 s. |
| `tests/stagec_v025` | 15 | 13 | 1 | 0 | 0 | 0 observed | 130 | Full run emitted `F.` and made no further progress; interrupted after 12 minutes. The other 14 tests were then run without T3: 13 passed, 1 failed, exit 1 in 23.30 s. T3 has no result. |
| Known combined outcomes | 182 | 175 | 6 | 0 | 0 | 0 observed | non-zero/incomplete | One collected Stage-C test has no terminal outcome. |

Skipped or xfailed: **0 skipped and 0 xfailed** in both requested subsets. No skip/xfail markers were found in those directories. The concern is therefore not hidden skips; it is real baseline failure plus a non-completing test.

The Stage-C no-result test is:

- `tests/stagec_v025/test_contract_v1_acceptance.py::test_T3_crossed_cluster_real_merger_coverage_and_power`

The Stage-C baseline failure is:

- `tests/stagec_v025/test_contract_v1_acceptance.py::test_T1_exhaustive_decomposition_and_intervention` — `StageCContractError: coalition context is absent from the sealed capped decomposition`.

The five physics baseline failures are:

- `test_provider_legacy.py::test_inventory_is_exact_realisable_union_and_standby_energy`
- `test_provider_legacy.py::test_canonical_horizon_is_invariant_to_requested_rehearsal_length`
- `test_provider_legacy.py::test_manifest_and_boundary_arrays_are_deterministic_across_processes`
- `test_provider_legacy.py::test_build_world_tape_uses_array_storage_and_input_digest`
- `test_stage2_tapes_targets_state.py::test_every_downstream_producer_has_no_default_energy_price[c2_persistence_forecast]`

Three provider failures report that `LegacyWorldProvider` has no `manifest_input_digest`; the inventory test reports a different inventory from the expected realizable union. The target-state failure reports that `c2_persistence_forecast.kappa_bits_per_user_step` incorrectly has a default of `None`.

## 2. Failure visibility probes

I inserted `assert False, "harness probe"` at the start of each test, one test at a time, ran only that node, confirmed `AssertionError: harness probe`, recorded the exit code, and restored the file before the next probe.

| Probe test | Result | Exit |
|---|---|---:|
| `tests/physics_v025/test_stage4b_contract.py::test_v15_set_decomposition_and_factor_identity_are_exact` | 1 failed | 1 |
| `tests/physics_v025/test_stage2_tapes_targets_state.py::test_reward_core_identity_is_exact` | 1 failed | 1 |
| `tests/physics_v025/test_stage4_contract.py::test_qos_gate_can_fail_only_availability_margin` | 1 failed | 1 |
| `tests/stagec_v025/test_stagec_pipeline.py::test_two_user_independent_argmax_cannot_commit_jointly_infeasible_profile` | 1 failed | 1 |
| `tests/physics_v025/test_energy_endpoint.py::test_physical_identity_mismatch_fails_closed` | 1 failed | 1 |

All five selected tests execute, pytest displays an injected failure, and the shell receives a non-zero status. This does not establish that their original assertions are scientifically sufficient.

## 3. Code location under test

With the required interpreter and `PYTHONPATH=src`:

```text
mcrl.__file__=/home/sat/mcrl-v025-harness-ws/src/mcrl/__init__.py
```

The imported package therefore resolves to the audit workspace, not `/home/sat/mcrl-leo-handover/src`.

There is a related diagnostic hazard: the copied tree contained 104 `.pyc` files, 27 of which embed `/home/sat/mcrl-v025-pilot-ws` as their compile-time filename. Consequently, some tracebacks displayed `../mcrl-v025-pilot-ws/tests/...` even though package resolution was local. This is misleading provenance in diagnostics, not evidence that the pilot package was imported.

## 4. Stale or disk-backed artefacts

The following tests in the two audited subsets consume pre-existing disk content rather than constructing all inputs in the test.

### External TLE fixture

`tests/physics_v025/test_provider_legacy.py` constructs its module-scoped `real_world` fixture from `DEFAULT_TLE_ROOT`, which is `~/demo/tle_data/starlink/tle`. These 15 tests consume that disk archive directly or through `real_world`/`step0`:

- `test_decision_geometry_and_scintillation_free_nominal_match_legacy`
- `test_forward_boundary_ecef_matches_direct_sgp4`
- `test_mask_is_nonvacuous_and_matches_legacy_at_decision`
- `test_entry_elevation_and_d2_distance_use_legacy_slant_definition`
- `test_aggressor_uses_own_cell_boresight_at_one_and_two_rings`
- `test_per_chain_colour_filter_and_same_satellite_p10_match_legacy`
- `test_inventory_is_exact_realisable_union_and_standby_energy`
- `test_fixed_forward_horizon_has_explicit_right_censoring`
- `test_user_motion_is_recorded_per_step_and_user_count_is_sourced`
- `test_exact_train_timestamp_and_test_date_rejection`
- `test_nonzero_origin_and_forward_prime_seam_have_no_backward_jump`
- `test_canonical_horizon_is_invariant_to_requested_rehearsal_length`
- `test_manifest_and_boundary_arrays_are_deterministic_across_processes`
- `test_build_world_tape_uses_array_storage_and_input_digest`
- `test_tle_split_and_provider_source_hashes_are_recorded`

### Precomputed result fixture

- `tests/physics_v025/test_stage4b_contract.py::test_sealed_off_axis_kat_uses_a_r0_and_changes_power_and_ee` reads `.scratch/multi-catfish-v025-physics-successor/probe/figures/a-r0-off-axis-kat.json` (SHA-256 `87e8bb4598c1212c823469f33775dc8650dbc7667c2e2623c3ef44d4ad8e7d03`) rather than generating that receipt during the test. It also computes fresh `off_axis_rows()`, but the asserted receipt fields come from the stored JSON.

### Disk-loaded `.scratch` implementation modules

These tests load the pre-existing `.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py` by file path (SHA-256 `d430baf38eee7973aa56a503e905548bbf55ae4a5eb6f2435c2a2543d4786196`) instead of importing a package-owned implementation:

- All 3 tests in `tests/physics_v025/test_stage2_runner.py`.
- Ten tests in `test_stage3_parity_uncertainty.py`, covering the dry-run, shortlist, receipt, treatment, 31-setting, rekey, and interval checks.
- `test_stage4_contract.py::test_qos_gate_can_fail_only_availability_margin`.
- Four tests in `test_stage4b_contract.py`: the QoS pooling, zero-bit cluster, admission, and provider-protocol tests.
- Twelve tests in `test_stage4d_gate.py`: the tests that call `_load_runner`.
- `test_contract_discriminators.py::test_deadline_fallback_is_frozen_base`.

`test_stage4b_contract.py::test_sealed_off_axis_kat_uses_a_r0_and_changes_power_and_ee` additionally loads `.scratch/.../build_off_axis_figure.py` by path. These are stale-code seams rather than cached feature/checkpoint files, but they carry the same risk: a test can validate a preserved scratch implementation instead of the current package path.

The Stage-C shard and checkpoint reads in `test_contract_v1_acceptance.py` and `test_stagec_pipeline.py` were excluded because those files are created in that same test under `tmp_path` before being read.

Outside the requested subsets, the service-guard mutation test loads `.scratch/c3-v04/run_v04_c3_500_update_screen.py`. A project-wide static scan also found persisted `artifacts/` inputs in:

- `test_w29_prereg_frozen.py`
- `test_w39_c2_keyed_gate.py`
- `test_w41_c2_v03b_reactive_gate_integrity.py`
- `test_w52_c2_real_temporal_pair_smoke.py` — real checkpoint; normally skipped
- `test_w98_v05_c2_controlled_tape_mechanics_verifier.py`
- `test_w179_v018_analytic_r2_provenance.py`

These should not be interpreted as proof that their producing code ran in the test invocation.

## 5. Extreme mutations

Each mutation was applied alone, run against the closest critical tests, then restored. The final restoration check was `5 passed`, exit 0.

| Scientific path/helper | Extreme mutation | Tests run | Outcome |
|---|---|---|---|
| Coalition feature path: `CoalitionContext.invariant_vector` | Returned an all-zero vector of the correct shape. | `test_T2_information_twins_reversal_and_additive_placebo` | **Caught:** 1 failed, exit 1; learned interaction was `0.33046` instead of `> 1.0`. |
| Score decomposition: `set_score_decomposition` | Returned a constant zero/empty `SetScoreDecomposition`. | Exact v1.5, large-set, and small-set Shapley tests | **Caught:** 3 failed, exit 1. |
| Service guard: `enforce_zero_loss_service_guard` | Became an always-pass constant result. | `test_pooled_ratio_of_sums_and_zero_loss_service_guard_are_explicit` | **Caught:** 1 failed, exit 1; the negative case expected `pass is False`. |

None of these three helpers is pseudo-tested under the targeted tests: an extreme semantic deletion made the relevant checks fail. This finding is narrower than saying the full scientific contract is adequately tested.

## Bottom line

The basic failure channel works: five independent injected assertions and all three extreme mutations surfaced with exit 1. Nevertheless, the current harness baseline is already failing, Stage-C cannot produce a complete terminal result within the audit cap, traceback provenance is polluted by copied bytecode, and multiple tests depend on disk-resident fixtures or scratch implementations. A future all-green line is meaningful only after these baseline and provenance problems are resolved and the non-completing Stage-C test is made bounded.
