Stage 4d is **not ready**. The stop itself was honest: the real anchor completed, but coordinator selection took 24.663217761 s against the binding 10 s gate. Formal calibration, rehearsal, stride, smoke, and R2 outcomes were consequently not opened.

I audited committed range `57353988..f6744ca9` and used the code-review workflow to keep specification closure separate from maintainability findings.

## Independent verification

| Check | Result |
|---|---|
| Committed-profile endpoint | **PASS.** Running the identical 48-boundary fixture against the stage-4b snapshot and stage-4d produced identical hex values: bits `0x0.0p+0`, energy `0x1.edbf06821a358p+5`. |
| Two-stage argmax | **PASS.** Independent 70-row fixture, `M=64`, optimum `c60` inside top-M: full-catalogue and two-stage argmax both `c60`. |
| Batch versus scalar solver | **PASS.** Forced spectral-radius-0.999 slow case: both certify `CONVERGED_SLOW`, 1,000 iterations, residual `3.6806348825924e-08`; all three powers match exactly, maximum difference `0.0 W`. |
| Anchor timing | **SELECTION FAIL; TOTAL PASS.** Recomputed phase sum: `1.772909427 + 4.010991145 + 18.328741991 + 0.008175172 + 0.542052921 = 24.662870656 s`. Timer difference is `0.000347105 s`. Stage 2 is 74.3161%. Provider plus enclosing anchor is exactly `21.482488605 + 34.459668001 = 55.942156606 s`. See [report](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-ENGINE-STAGE4D-REPORT-2026-09-08.md:96). |
| Calibration | **IMPLEMENTATION PASS; FORMAL RUN ABSENT.** `_calibrate` consumes two complete 30-step tapes and loops over all 30 steps, giving 60 reference decisions and `1,804.8 s` represented time. See [runner](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1059). |
| Smoke honesty | **HONESTLY NOT RUN.** Prospective receipts use `SMOKE_NOT_MATRIX`; smoke uses `V025_SMOKE/world/1`; merge accepts only fixed formal paths with status `COMPLETE`. No smoke receipt or SMOKE-number table exists, so there are no ΣB/ΣE rows to recompute. See [runner](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:3704) and [merge](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:4835). |
| Rehearsal/q/projection | **NOT RUN.** No valid stage-4d `q` exists. A lower bound from the measured after-tape anchor is `34.430552590 × 4 × 90 / 3600 = 3.443055259 core-hours`; ideal concurrency-20 wall time is at least `0.172152763 h` or `10.329165777 min`. This excludes construction of the full 33-step provider tapes. |
| Formal R2 outcome | **PASS.** Scanning JSON artifacts under `.tmp`, `.scratch`, the launch directory, and the controller registry found zero `V025_PROBE_R2` unit receipts. Temporary R2 world manifests are test fixtures, not outcomes. The only unit receipt found was development-domain `V025_PROBE/world/1`. |

The reported four-step provider construction is sufficient for the measured single anchor and its three forecast offsets, but it is not a measurement of constructing a full formal 33-step world tape.

## Prior stage-4 open-row disposition

The previous audit had 26 open rows: [rows 2–36](/home/sat/mcrl-v023-codex-audits/parallel-20260908/STAGE4-AUDIT-2026-09-08.md:18).

| Row | Disposition | Evidence / independent check |
|---:|---|---|
| 2 | **CLOSED** | Top-8 legal-option shortlist and top-10 user ordering use exact nominal unilateral surplus; independently hand-ranked fixture agrees. |
| 6 | **STILL OPEN** | Full-30 calibration code is fixed, but formal manifests, calibration receipt, rehearsal, `q`, projection, and stride were not run. |
| 7 | **STILL OPEN** | Smoke labelling and merge exclusion are correct, but no smoke receipt or numerical rows exist. |
| 8 | **STILL OPEN** | Seal remains HOLD, rehearsal fields are pending, and launch text still contains `STRIDE_PENDING`. See [seal](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/SEAL-PACKAGE-DRAFT-2026-09-08.md:277). |
| 10 | **CLOSED** | A, I, and Δjoint are emitted. Independent exact fixture gives `η₀=10`, `A=13`, `I=-3`, `Δjoint=10`. |
| 11 | **CLOSED** | S_UNI exhausts the full legal unilateral set, applies the service guard, uses the controller-clarified k=0 `F+κΦ` objective, and receipts its termination. Independent outsider-option and incumbent-relative-Φ fixtures pass. |
| 12 | **CLOSED** | The real anchor exercised the 10 s whole-path deadline and atomically fell back all set arms to validated BASE. |
| 13 | **CLOSED** | Configuration-level Ψ drives selection; Shapley is reporting-only for small sets. Independent two-user and six-user fixtures validate both branches. |
| 17 | **STILL OPEN** | H/SH behavior is independently distinguished for all four required twins, but the “31 distinct receipts” KAT merely compares whole-receipt hashes containing setting identity metadata. It cannot detect physics duplicates. |
| 18 | **CLOSED** | Ψ is configuration-local, decomposition is O(\|A\|), and small-set Shapley is reporting-only. Independent nonzero/zero interaction fixtures pass. |
| 19 | **CLOSED** | Reciprocal reuse and unique chain colour are independently checked; the real-provider anchor completed. |
| 20 | **STILL OPEN** | Production nulls zero-legal users, but the KAT only counts at least 11 catalogue rows and checks NULL assignments. It does not execute and prove 11 non-BASE arms differ from BASE. See [test](/home/sat/mcrl-v025-codex-ws-engine/tests/physics_v025/test_stage4d_gate.py:414). |
| 21 | **STILL OPEN** | The former 15 weak tests were removed, but two replacement discriminators remain self-fulfilling: 31 receipt hashes and dependency-allowlist mutation. |
| 22 | **STILL OPEN** | Common resolution and production forecast projection landed, but `assert_reward_core_identity` remains test-only rather than running in every unit dry-run. |
| 23 | **STILL OPEN** | Solver parity and slow certificates pass independently, but the mandated batched-three-offset-forecast versus per-row-forecast KAT at `1e-9` is absent. The existing endpoint comparison permits `2e-6` bit error and is not forecast-row parity. |
| 24 | **CLOSED** | API and serialization now use `kappa_bits_per_user_step`; legacy loading is explicitly tested, and an independent dimensional arithmetic fixture passes. |
| 25 | **STILL OPEN** | Opening-state certificate and allowlist exist, but the test edits the declared receipt list and asks the same checker to reject it. It does not inject an undeclared hidden dependency into selection. |
| 26 | **CLOSED** | Capability text now matches implementation: set arms and S_UNI apply the service guard; other arms are explicitly listed as not guarded. Deadline fallback KAT passes. |
| 27 | **STILL OPEN** | Required event vocabulary is stay/beam/satellite/re-entry/re-key. The KAT substitutes `initial_entry` and `exit`; moreover, re-entry is unreachable because `was_previously_served` is derived only from whether the immediately prior assignment is non-null. See [event builder](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:716) and [test](/home/sat/mcrl-v025-codex-ws-engine/tests/physics_v025/test_stage4d_gate.py:358). |
| 28 | **CLOSED** | Registry authority is `/home/sat/mcrl-records/ATTEMPT-REGISTRY-2026-09.jsonl`; append/hash-chain and STARTED/DONE rejection were independently exercised during the preceding closure audit. |
| 29 | **STILL OPEN** | Reaggregation now checks substantially more fields, but its KAT only mutates fields and calls the production reaggregator. There is still no independent implementation rebuilding every summary bit-for-bit from canonical rows. |
| 30 | **CLOSED** | `run_unit` invokes the shared conformance suite, covers all arms and authority fields, and the independent receipt test checks NULL=BASE and write-once sidecars. |
| 31 | **STILL OPEN** | Boundary-17 visibility/D2 KAT asserts decoding time only. It does not independently assert that both bits and energy cease at boundary 17 as required. See [test](/home/sat/mcrl-v025-codex-ws-engine/tests/physics_v025/test_stage4d_gate.py:596). |
| 32 | **CLOSED** | Production uses `project_three_offsets`; invalid solves emit INVALID rows with null power/cap margins and negative decoding margin. Independent invalid-row KAT passes. |
| 35 | **CLOSED** | Timer includes catalogue through validation; the measured miss commits BASE for every set arm without powerset validation. |
| 36 | **STILL OPEN** | No formal R2 unit was opened, but synthetic engine tests still use `V025_PROBE/world/1` instead of the mandated `V025_SYNTHETIC/*` or `V025_PROVIDER_KAT/*` namespaces. |

Thus the report’s claim that all rows 11–13, 17–32, 35, and 36 closed is overstated: rows 17, 20–23, 25, 27, 29, 31, and 36 remain open.

## Test execution

- Collected: 167 tests.
- Read-only full run: 165 passed; two setup errors solely because pytest could not create `tmp_path`:
  - `test_unit_receipt_is_complete_and_write_once`
  - `test_formal_world_tape_is_built_once_and_reused_across_settings`
- Re-running all non-writing tests completed successfully.
- Focused stage-4d file: 21 non-writing tests passed; its one `tmp_path` test had the same setup limitation.
- AST compilation and `git diff --check 57353988..f6744ca9` passed.
- The committed stage-4d test digest matches the report: `efff3b0bb41882173f12ca88427133e9dd5c67081ad677b8cd08ecb6adcf2acf`.

## Standards review

No hard documented-standard violation was found. The primary maintainability risk is the additional 876-line expansion of the already multi-responsibility probe runner, accompanied by a 695-line stage-4d test module. Secondary smells are duplicated immutable-output helpers and thin forwarding abstractions in batch/resolution code. These are engineering risks, not the reason for the readiness failure.

VERDICT: STAGE4D=NOT_READY:10S_GATE,ROWS_6-8_17_20-23_25_27_29_31_36 | CLOSED=13/26 | TAUTOLOGICAL_KATS=2 | AR0_PROJECTED_CORE_HOURS=>=3.443055259 | ANCHOR_SECONDS=34.430552590