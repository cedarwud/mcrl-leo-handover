## VERIFIED

1. **Imports & Logic Sharing:** [`run_v023_c3_contingency_f2.py:36`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L36) imports F1 directly. It reuses runtime modules, surface computation, candidate enumeration, physical profiles, and action keys (`:827–935`), F0 `compute_c3_targets` (`:878`), `masked_argmax_q12_plus_z` with $\kappa = 10097071012.757404$ (`:620, 633, 900`), and `evaluate_kill_rules` (`:666, 1029`). `build_f2_step_payload` (`:523`) reuses `f1.build_step_payload`. Duplicated logic is strictly limited to: (a) `_pooled_metrics` (`:484–509`), duplicating `f1._profile_metrics` because F1 hardcoded `len(profiles) != 2`; and (b) `_generate_unit_tape` (`:814–958`), parameterizing the 10-step outer loop across `(world, lineage)` and admitted survivors rather than F1's hardcoded single-world 2-step loop.
2. **Pass Thresholds:** Evaluated in [`run_v023_c3_contingency_f2.py:1057–1078`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L1057-L1078). Matches the ladder (§3) exactly: pooled ratio-of-sums EE strictly above BASE (`:1062, 1068`), strictly positive directions in $\ge 3/4$ worlds (`WORLD_DIRECTION_MIN = 3`, `:59, 1044, 1063`) and $\ge 2/3$ lineages (`LINEAGE_DIRECTION_MIN = 2`, `:60, 1054, 1064`), service non-inferiority margin $0.001$ (`:57, 1061, 1069`), and complete mechanics/provenance integrity (`:1006–1012, 1060`). No extra or missing conditions exist.
3. **Admission & Priority:** [`run_v023_c3_contingency_f2.py:425–426, 475–476, 585–586, 825–826, 1341–1343`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L425-L426) fails closed (`F2NotAdmitted`, exit code 3) without sealed F1 survivors. `adjudicate_panel` (`:1090–1093`) enforces D-before-F priority; `F2_PASS_F` is reachable only when D failed (or was unadmitted) and F independently passes.
4. **Integrity Propagation:** Failed unit runs fail closed without publishing staging directories (`:716–747`). Merge catches any missing or unauthenticated unit bundle and writes an immutable `INVALID_RUN` terminal receipt (`:1141–1164, 1274–1280`). In `evaluate_panel_candidate` (`:1006–1012`) and `adjudicate_panel` (`:1084–1089, 1120`), any `integrity is not True` across any admitted candidate or unit propagates globally to `INVALID_RUN`.
5. **Execution & Resume Semantics:** CLI enforces mutually exclusive `--unit WORLD:LINEAGE` and `--merge` (`:104–118, 1323–1338`). `write_unit_bundle` (`:716–744`) stages and atomically renames write-once units with `0444` permissions. `execute_unit` (`:1176–1184`) authenticates and skips existing units without recomputation. `execute_merge` (`:1231–1255`) authenticates existing terminal receipts without re-execution.
6. **Lineage Checkpoints & Authorities:** Rung-003000 checkpoints and authority bodies for lineages 2026092101–2026092103 are pinned by SHA-256 (`:67–81`). `_validate_lineage_authority` (`:289–322`) enforces exact single-glob matches, file digests, unsigned body seal verification, and semantic flags fail-closed with no fallback selection.
7. **No Hidden Manipulations:** Zero clipping, clamping, scaling, sign filtering, or outcome-dependent branches. Empty-mask users are preserved as NOOP via imported `f1.masked_argmax_q12_plus_z` and `f1.enumerate_unilateral_candidates`.
8. **Preflight Manifest Builder:** [`build_f2_preflight_manifest.py:15–22`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/build_f2_preflight_manifest.py#L15-L22) and [`run_v023_c3_contingency_f2.py:269–287`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L269-L287) derive code and formula digests directly from on-disk files via `file_sha256(path)` and `f1.formula_digests()`, not literals. The manifest (`F2-PREFLIGHT-MANIFEST.json`, SHA-256 `cbfe03cc...`) matches the repaired F0 formula file digest (`658e4072fb...`) and passes preflight validation (`:358–376`).

## DEFECTS

None.

## RECOMMENDATION

Implementation is faithful to specification ladder §2–§3 and adjudication rulings. Proceed to generate launch authority following sealed F1 receipt adjudication and dispatch server execution of the twelve F2 units.

AGY_F2_REVIEW=PASS
274-L1280)).
5. **Unit Sharding, Resumes, and Write-Once**: CLI supports `--unit world:lineage` and `--merge` ([`run_v023_c3_contingency_f2.py:1323-1325`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L1323-L1325)). [`write_unit_bundle`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L708-L752) stages in a hidden tempdir, writes `0444` artifacts, and atomically renames the directory. [`execute_unit`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L1176-L1184) authenticates existing bundles and skips generation without recomputing.
6. **Fail-Closed Lineage Authority**: Lineages `2026092101`–`2026092103` are bound fail-closed ([`run_v023_c3_contingency_f2.py:62-81`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L62-L81)). [`_validate_lineage_authority`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L289-L322) asserts single checkpoint file match, exact checkpoint and authority SHA-256 digests, recomputed canonical body seal, and contract flags with no fallback selection.
7. **No Discretionary Discrepancies**: Composition is strict `masked_argmax(Q1+Q2+z/κ)` with $\kappa = 10097071012.757404$ bits ([`run_v023_c3_contingency_f1.py:754`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py#L754)), 100 users ([`run_v023_c3_contingency_f2.py:54, 616`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L54)), empty-mask users select `NO_OP_ACTION` ([`run_v023_c3_contingency_f1.py:757-761`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py#L757-L761)), and shared field component is `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1` ([`run_v023_c3_contingency_f2.py:56, 837`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L56)). No clipping, scaling, or sign filters exist.
8. **Dynamic Preflight File Digests**: [`expected_code_bindings`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L269-L286) dynamically computes `file_sha256(path)` from files on disk rather than hardcoded literals. [`formula_digests`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py#L252) imports [`f1.formula_digests`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py#L392), which dynamically hashes [`c3_contingency_f0.py`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency/c3_contingency_f0.py). Re-running [`build_f2_preflight_manifest.py`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/build_f2_preflight_manifest.py) binds the repaired F0 file digest directly. The committed [`F2-PREFLIGHT-MANIFEST.json`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f2/F2-PREFLIGHT-MANIFEST.json) already binds the repaired F0 SHA-256 (`658e4072...`) and matches the `.sha256` sidecar.

---

## DEFECTS

None. All implementation components, tests, and preflight bindings adhere strictly to ladder §2/§3 and the controller adjudication.

---

## RECOMMENDATION

Proceed with launch authority creation once a valid F1 survivor receipt is sealed on the Ubuntu server. Before dispatching heavy units, run:
```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f2/run_v023_c3_contingency_f2.py --dry-run
```
to verify clean environment and manifest verification.

AGY_F2_REVIEW=PASS
