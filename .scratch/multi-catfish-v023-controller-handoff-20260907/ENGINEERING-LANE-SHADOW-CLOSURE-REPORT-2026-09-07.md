# Engineering-lane shadow-closure report — 2026-09-07

Scope: `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. All writes confined to the shadow checkout; no sealed root touched; no training/simulation started.

## Task 1 — closure

Full resolved list (41 entries): `.scratch/multi-catfish-v023-controller-handoff-20260907/SHADOW-CLOSURE-LIST-2026-09-07.txt`. Method: traced every `HERE.parent(s)`/`REPO /`/`spec_from_file_location`/`.scratch|docs|artifacts|src` literal in the 9 named packages, then one level into every sibling file they load, cross-checked against `CODE-MANIFEST.json`'s own 30 bindings and `run_v023_c3_contingency_f1.py`'s `CODE_BINDING_PATHS`/`validate_static_bindings`. No `artifacts/` file in the closure exceeds 50 MB (largest is the 133 KB PREREG); nothing was skipped.

**Actual gaps found and synced** (checksum-verified before/after, everything else in the 41-entry closure was already correct on the shadow):
- `.scratch/multi-catfish-v023-r6-fit-binding-fix/` — whole directory was missing; synced only the 5 files actually referenced (`v023_lcsrs_source_adapter.py`, `PREFLIGHT-MANIFEST.json`+`.sha256`, `preflight_v023_lcsrs_r6.py`, `SOURCE-ARTIFACT-SCHEMA.md`), not the full ~25-file R6 gate directory.
- `.scratch/multi-catfish-v023-c3-contingency-f1/` — 5 files updated (today's F1 fix): `F1-PREFLIGHT-MANIFEST.json`, `.sha256`, `README.md`, `run_v023_c3_contingency_f1.py`, `test_run_v023_c3_contingency_f1.py`.
- `.scratch/multi-catfish-v023-c1c2-successor/ENGINEERING-LANE-CHARTER-2026-09-07.md` — 1 file, out of date.

Explicitly **not touched**: `.scratch/multi-catfish-v023-controller-handoff-20260907/r7-sealed-receipts/{result.json,MANIFEST.sha256,COMPLETE}` — already present on the shadow and byte-identical (sha256 verified both sides) to the local copy; this is a sealed triple (`COMPLETE`+`MANIFEST.sha256`), so it was verified read-only and excluded from sync per the hard rule. Excluded from the closure entirely: R6's own 96-binding `PREFLIGHT-MANIFEST.json` transitive set — it's only read by `preflight_v023_c1c2_targets.py::validate_nested_r6_runtime_closure`, which nothing in this consumer chain calls (`require_r6_runtime_closure` is never set `True` anywhere in the test suites).

## Task 2 — server test suites

`pytest -q -p no:cacheprovider` over the 6 named suites, server venv, `PYTHONPATH=.../src`: **86 collected, 83 passed, 3 failed**, no collection errors, no closure-caused failures (0 rounds needed).

| Suite | Result |
|---|---|
| c1c2-provider-factory-v3 | 10/10 |
| two-route-source-training-runner | 6/6 |
| c1c2-successor-physical-evaluation | 24/24 |
| c3-contingency-f1 | 22/22 |
| heterogeneous-trainer | 3/6 — 3 failed |
| target-batch-adapter | 18/18 |

All 3 failures are in `test_v023_heterogeneous_trainer.py` (`test_c1_c2_pair_updates_are_finite_and_diagonal[C2-1]`, `test_malformed_action_shared_and_structured_batches_are_rejected`, `test_existing_three_route_checkpoint_and_resume_have_exact_parity`), same traceback on server and locally (reproduced against the local `.venv`, byte-identical `v023_heterogeneous_trainer.py`): `update_route`/`_resume_sequence` calls `update_c2` with a raw `EEAxisPairBatch` instead of `EEAxisV014NormalizedPairBatch`, so `update_c2` (line 316) raises `TypeError: C2 update requires an EEAxisV014NormalizedPairBatch`. Genuine pre-existing code defect, not an environment or closure artifact — not fixed, per instruction.

## Task 3 — F1 correction verification

| # | Item | Verdict | Evidence |
|---|---|---|---|
| a | `masked_argmax(Q1+Q2+z/κ)`, κ=10097071012.757404 from model config, cross-bound to V0.22, rule token, `kappa_bits_hex` in bindings | PASS | `run_v023_c3_contingency_f1.py:743-761` (`masked_argmax_q12_plus_z`, `composed = values + target/KAPPA_BITS`); `:236-256` (`KAPPA_BITS` bound from `V023-100E-MODEL-CONFIG.json`); `:427` (cross-checks V0.22's literal `KAPPA_BITS` hex); `:75` (`F1_DEPLOYMENT_RULE = "MASKED_ARGMAX_Q1_PLUS_Q2_PLUS_Z_OVER_KAPPA"`); `:310,:356` (`kappa_bits_hex`). Independently re-verified end-to-end at read-back in `verify_tape_payload:988-1005`. |
| b | integrity=False → INVALID_RUN | PASS | `:1127` (`integrity = integrity_ok is True and finite`); `:1142-1146` (`adjudicate_outcome`: `if integrity_ok is not True or any(rules[name].get("integrity") is not True for name in ("D","F")): return "INVALID_RUN"`) — now checks per-bundle integrity, not just the top-level flag. |
| c | 100 users / interval enforced | PASS | `:895,:914` (`build_step_payload`) and independently `:986,:1009-1013` (`verify_tape_payload`) both raise on `users != USERS` or D/F profile users/interval mismatching BASE. |
| d | empty-mask → NOOP | PASS | `:693-695` (`enumerate_unilateral_candidates`: empty mask + non-NOOP reference action errors, empty mask + NOOP `continue`s, no longer an unconditional reject) and `:800-802`; matches `src/mcrl/env/action_contract.py:576-580`. |
| e | preflight manifest rebuilt, `.sha256` matches | PASS | Ran `validate_preflight_manifest()` live (not just diffed): payload equals fresh `validate_static_bindings()+expected_code_bindings()`, digest `495d90d2...96e24` matches sidecar exactly. |
| f | local tests pass; `--dry-run` passes locally and on server post-sync | PASS | Local: 22/22 (`pytest`), `F1_DRY_RUN_PASS` (exit 0). Server (post-sync, this session): 22/22 in the Task 2 run, `F1_DRY_RUN_PASS` (exit 0). |

## Open issues
1. Heterogeneous-trainer's 3 C2-dispatch failures (above) are left unfixed per this task's explicit instruction to record rather than fix genuine code defects; this reads as a real bug (not environment-specific), and the engineering-lane charter otherwise expects lane failures fixed immediately — the owner should say which rule wins here.
2. R6's 96-binding strict closure (`require_r6_runtime_closure=True`) remains unsynced by design (see Task 1) — needed only if a future launcher turns that flag on.
