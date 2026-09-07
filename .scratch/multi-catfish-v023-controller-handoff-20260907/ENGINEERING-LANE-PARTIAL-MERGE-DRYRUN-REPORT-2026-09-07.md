# Engineering-lane partial real-shard merge dry-run — r8 (2026-09-07 17:21–17:24 UTC)

Claim ceiling: `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. No scientific output.

- Tool commit: `47bf8068a76ad4a46bf10d12db33d17658ae5298`
- Local tests: `test_partial_merge_dryrun.py` **3 passed**. `test_successor_stage_bc_chain.py::test_stage_bc_default_status_matrix` still FAILS (`fresh_exports` = FAIL) — concurrent stage-C fix pass, not touched.
- Scratch root `/home/sat/mcrl-v023-partial-merge-DRYRUN-NONFORMAL-20260907T172053Z` (661 MB); log `…172053Z.log`. Staging, r8 checkout and all sealed roots untouched.

## Terminal shards at run time: 9 of 16

`informed:2026121705, 06, 10, 11` and `neutral:2026121705, 07, 08, 09, 12`.
Non-terminal (still running): informed 07/08/09/12, neutral 06/10/11.

## Per-step results

| Step | Status |
|---|---|
| `authenticated_schedule` | PASS — 16 shards |
| `authenticate_shard:*` (×9) | **PASS ×9**, 0 FAIL — `_read_receipt` + `_validate_shard` + receipt/manifest digest agreement with the terminal receipt |
| `terminal_subset` | PASS — available 9 / scheduled 16 |
| `full_schedule_merge_guard` | **EXPECTED_FULL_SCHEDULE_GUARD** — `ControllerError: mode/world shard set disagrees with the authenticated schedule` (`run_v023_c1c2_targets_server.py:617`); guard wrote no output |
| `controller_merge_and_manifest` | **PASS** — 9 shards merged, MANIFEST.sha256 with 19 entries (9 c1 + 9 c2 JSON + receipt.json) |
| `sealer_field_and_manifest_checks` | **PASS** — `seal(...)` → `COMPLETE` = `9e46f3a9d8bee89c5210988c9ac596192d01944aade4956f3f055a841be66c24  MANIFEST.sha256` |
| `adapter_dataset_concatenation` | **FAIL** (see below) |
| `input_integrity_after_dryrun` | PASS — all 9 input receipts/manifests re-validated, digests unchanged |

Final line: `PARTIAL_MERGE_DRYRUN_FAIL` (exit 2), driven solely by the adapter step.

## The one FAIL — NOT a controller merge/seal defect

`partial_merge_dryrun.py:93` (`_load_adapter`, boundary `ADAPTER_RELATIVE`, line 30):
`PartialMergeDryRunError: target adapter is missing or symlinked: /home/sat/mcrl-v023-c1c2-target-generation-20260907-ops3-r8/.scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py`

Verified: that package is **absent from the r8 launch checkout** (its `.scratch/` holds 13 packages, not this one); it exists in the local repo and in the shadow checkout. The r8 controller never imports it — its end-of-run path is `_merge` + `SEALER` only, and **both passed on real shards**. So this is a checkout-closure defect (charter rule 11: sync list narrower than the import graph) affecting downstream successor consumers bound to `--checkout <r8 root>`, **not** a defect that will hit the controller at the end of the 3-hour run. The controller's real merge + seal path is now exercised green on 9 real shards.

Consequence: dataset shapes/dtypes/layout were **not** obtained this run — that evidence comes only from the adapter step. Re-run against a checkout that carries the adapter (or the shadow root) to get it.

## Resources

Wall clock **3:32.92**; user 209.3 s (99% CPU); peak RSS **4,776,512 KB ≈ 4.55 GiB** — **over the 4 GB budget**; 1.35 GB written, all inside the scratch root. Extrapolating to 16 shards, expect ~6 min and a higher peak; worth watching alongside the running job.
