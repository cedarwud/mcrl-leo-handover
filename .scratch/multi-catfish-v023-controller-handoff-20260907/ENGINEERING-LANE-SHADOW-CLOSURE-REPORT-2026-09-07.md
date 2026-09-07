# Engineering-lane shadow closure report — 2026-09-07

**Note:** `c1c2-provider-factory-v3` and `two-route-source-training-runner` were edited concurrently by another process mid-audit (2 tests added). Re-synced both and re-ran Task 2 last; figures below are that final, re-verified (246/246 byte-identical local↔shadow) pass.

## Task 1 — closure

Traced the 9 packages for `HERE.parent(s)`/`REPO /`/`spec_from_file_location`/`.scratch|docs|artifacts|src` literals and `_output_code_closure`/`CODE_BINDING_PATHS`-style hash lists, one level into every sibling file loaded, to a 246-path closure in `SHADOW-CLOSURE-LIST-2026-09-07.txt`. Beyond the 9 packages and all of `src/` (156 files, one `sys.path` unit), it needed:

- `c1c2-neutral-materialization/materialize_v023_c1c2.py`, `c1c2-predecision-capture/v023_c1c2_predecision_capture.py` — loaded by `generate_v023_c1c2_targets.py`'s `_load_module`.
- `r6-fit-binding-fix/{v023_lcsrs_source_adapter.py, PREFLIGHT-MANIFEST.json+.sha256, preflight_v023_lcsrs_r6.py, SOURCE-ARTIFACT-SCHEMA.md}` and the same 5 files' R7 equivalents — R6's manifest is real-read-and-hashed by `audit_v023_c1c2_checkpoint_closure.py`, not just a fixture string.
- The D40 checkpoint (394KB) + `authority.json` + two contract docs — hashed in F1's `validate_static_bindings()`.
- F1's `CODE_BINDING_PATHS`: `c3-contingency/c3_contingency_f0.py`, `100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json` (binds κ), `v022-c3-coalition-residual/run_v022_coalition_residual_probe.py`, the ladder/ruling docs, and the sealed `r7-sealed-receipts/{result.json,MANIFEST.sha256,COMPLETE}` triple (read-only reference, never written).
- `physical/{v023_physical_episode_runner.py, run_v023_dropc3_evaluation_server.py}`, `five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py`, `baseline-adapter/baseline_adapter.py`.

Excluded: R6's own 96-binding manifest (`docs/`, `tests/test_w181-205*.py`, more `src/`) — only read by `validate_nested_r6_runtime_closure()`, gated on `require_r6_runtime_closure=True`, never set in this chain. Also excluded: guard-clause strings checked for *absence* (`.scratch/c2-v03`, `artifacts/training-2026-08-25-rerun01/...`).

Verified all 246 paths hash-identical, repo↔shadow, after syncing (`__pycache__`/`.pytest_cache` excluded). No `artifacts/` file exceeds 50MB (largest is the 394KB checkpoint).

## Task 2 — server test results

`cd .../shadow-20260907 && PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 PYTHONPATH=.../shadow-20260907/src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q -p no:cacheprovider <6 dirs>` → **85 passed, 3 failed** (88 total, 7.5s), final pass after the concurrent edits above. No round 2/3 needed — every failure traced to a genuine code defect, none to a missing file.

| Suite | Passed | Failed |
|---|---|---|
| c1c2-provider-factory-v3 | 11 | 0 |
| two-route-source-training-runner | 7 | 0 |
| c1c2-successor-physical-evaluation | 24 | 0 |
| c3-contingency-f1 | 22 | 0 |
| heterogeneous-trainer | 3 | 3 |
| target-batch-adapter | 18 | 0 |

Genuine defect (reproduces identically on the local venv, not server/torch-specific): `test_v023_heterogeneous_trainer.py:61`'s `_pair_batch()` builds a plain `EEAxisPairBatch`, but `v023_heterogeneous_trainer.py:316`'s `update_c2` requires `EEAxisV014NormalizedPairBatch` and raises `TypeError: C2 update requires an EEAxisV014NormalizedPairBatch`. Fails: `test_c1_c2_pair_updates_are_finite_and_diagonal[C2-1]`, `test_malformed_action_shared_and_structured_batches_are_rejected`, `test_existing_three_route_checkpoint_and_resume_have_exact_parity`. Not fixed — out of mandate (see below).

## Task 3 — F1 correction verification

| Item | Result | Evidence |
|---|---|---|
| (a) masked_argmax(Q1+Q2+z/κ) | PASS | `run_v023_c3_contingency_f1.py:75` rule token; `:236-256` binds κ=10097071012.757404 from `V023-100E-MODEL-CONFIG.json` cross-checked against V0.22 hex; `:753-754` `composed = values + target / KAPPA_BITS`; `:310,356` `kappa_bits_hex` in `F1Bindings`/`authority_bindings`; re-derived independently in `verify_tape_payload:995-1004`. Test: `test_composition_matches_v022_masked_q12_plus_z_over_kappa_convention`. |
| (b) integrity=False → INVALID_RUN | PASS | `adjudicate_outcome:1142-1146` returns `INVALID_RUN` if *either* bundle's own `rules[name]["integrity"]` is not `True`, independent of the caller's `integrity_ok` kwarg. Test `test_invalid_d_integrity_prevents_passing_f_sibling_from_surviving` (the exact D-invalid/F-passing probe the ruling flagged) now asserts `INVALID_RUN`. |
| (c) 100 users/interval match | PASS | Enforced twice: build (`build_step_payload:893-894, 913-914`) and verify (`verify_tape_payload:984-985, 1006-1013`). Tests `test_tape_validation_requires_exactly_100_base_users`, `test_tape_validation_requires_deployments_to_match_base`. |
| (d) empty-mask → NOOP | PASS | `enumerate_unilateral_candidates:695` and `target_surfaces_from_step:802` both only raise if an empty-mask user's reference action *isn't* NOOP; otherwise skipped/defaulted, matching `action_contract.py:580`. `masked_argmax_q12_plus_z:756-758` defaults ineligible users to `NO_OP_ACTION`. Test `test_empty_mask_user_is_noop_and_has_no_unilateral_candidate`. |
| (e) preflight manifest rebuilt, .sha256 matches | PASS | Ran `validate_preflight_manifest(DEFAULT_PREFLIGHT)` read-only (no writes): recomputes bindings+code hashes fresh and diffs against the frozen JSON — passed, digest `495d90d2...` matches the `.sha256` sidecar and the file on disk. |
| (f) local tests + `--dry-run` pass, local and server | PASS | Local: `pytest .../c3-contingency-f1` → 22 passed; `run_v023_c3_contingency_f1.py --dry-run` → `F1_DRY_RUN_PASS`. Server (post-sync): same 22 passed (see table); `--dry-run` → `F1_DRY_RUN_PASS`. |

## Open issues

1. Heterogeneous-trainer's 3 failures are real and pre-existing — not caused by this closure work, not fixed (out of mandate).
2. R6's `require_r6_runtime_closure=True` path (96 bindings incl. `docs/`, `tests/test_w181-205`) stays unsynced; add it only if a launcher turns that flag on.
3. No write race: final full-closure hash check (246/246) after the concurrent edits landed is byte-identical local↔shadow.
4. Supplementary, outside the assigned 6 suites: `c1c2-target-generation`+`-launch` closure also verified (86/86 pass locally); 2 fail only on the server — they assert `REPO/.venv/bin/python` exists, which this shadow checkout intentionally lacks (shares the main checkout's `.venv`). Environment-topology defect, not a closure gap; not fixed.
