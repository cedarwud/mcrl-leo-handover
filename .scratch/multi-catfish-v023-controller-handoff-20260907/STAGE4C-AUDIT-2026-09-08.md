## Outcome

Stage 4c is **not ready**. Only 3 of the 26 previously open audit rows are fully closed: **2, 10, and 28**.

The real-anchor stop was substantively honest, but its phase-sum arithmetic is wrong, no complete anchor/rehearsal/smoke exists, the committed endpoint changed at the bit level, and scalar/batch `CONVERGED_SLOW` behavior diverges.

## Independent verification

| Check | Result | Evidence |
|---|---|---|
| Committed endpoint unchanged | **FAIL** | Comparing stage-4b and stage-4c full-48-boundary batch paths on the same three-user fixture produced identical bits but energy changed from `0x1.2b8cbc1c4887bp+6` to `0x1.2b8cbc0f1d39ep+6`, a `1.962357e-7 J` difference. |
| Two-stage argmax | **PASS** | Independent 70-row fixture: full-catalogue and top-64 stage-2 argmax both selected `c60`; the optimum was inside top-M. The required landed agreement/miss-reporting KAT is nevertheless absent. |
| Batch/scalar equivalence | **FAIL** | Ordinary fixture matched exactly: power `0.0004999996086811407 W`, 63 iterations, `CONVERGED`. Forced slow fixture: batch returned `CONVERGED_SLOW`; scalar raised `ValueError` because [`zip(..., strict=True)`](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/architectures.py:373) combines sequences of lengths 1000 and 999. |
| Real-anchor timing | **FAIL** | Named phases sum to **59.697988739 s**, not `59.698283185 s`; discrepancy is `0.000294446 s`, not under 1 μs. The whole selection path therefore misses 10 s. The complete-anchor ≤60 s claim is untestable: Shapley, ledger, receipts, and valid provider amortisation were not completed. |
| Full calibration rollout | **PASS in code** | [`_calibrate`](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1055) executes 30 steps in each of two worlds. A synthetic receipt records `decision_steps_ref=60` and `time_ref=1804.8 s`. Formal calibration was not run. |
| Smoke honesty | **NOT RUN** | No stage-4c smoke receipt or SMOKE table exists, so ΣB/ΣE cannot be recomputed. The prospective path labels smoke `SMOKE_NOT_MATRIX` and merge rejects that status, but `run_unit` still selects an R2 domain even in smoke mode. |
| Rehearsal/q/projection | **NOT RUN** | No stage-4c q or sealed projection exists. From the incomplete anchor alone, a-r0 is already **>5.969833128 core-hours**, or **>0.2984916564 h** ideal wall time at concurrency 20, excluding provider amortisation and unfinished work. |
| Formal R2 opening | **PASS, with namespace defect** | The controller registry is absent and no admissible formal unit receipt exists. Three pytest artifacts are synthetic (`SYNTHETIC.tle`, `attempt_id=null`) but incorrectly claim `status=COMPLETE`, `SMOKE_NOT_MATRIX=false`, and `V025_PROBE_R2/world/1`; they cannot merge, but keep namespace item 36 open. |

## Prior open-row closure audit

| Row | Status | Evidence / independent KAT |
|---:|---|---|
| 2 | **CLOSED** | Top-8 shortlist and top-10 exact nominal-surplus ranking are implemented at [`runner:469`](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:469) and [`runner:585`](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:585). Independent KAT retained exactly 8/10 options and ranked users `[11…2]` by supplied surplus rather than option count. |
| 6 | **STILL OPEN** | Full-rollout calibration code landed, but six formal manifests, calibration execution, rehearsal, q, projection, and stride remain `PENDING_NOT_RUN`. |
| 7 | **STILL OPEN** | No smoke receipt or numbers exist. Prospective labelling/exclusion alone does not complete the row. |
| 8 | **STILL OPEN** | Seal remains HOLD/`STRIDE_PENDING`; it says both schema v1.6 and v1.5, claims 148 receipts although the executable inventory is 38×4=152, and its code-authority digest `ff672f…` disagrees with the current `399d63…`. See [seal draft](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/SEAL-PACKAGE-DRAFT-2026-09-08.md:20). |
| 10 | **CLOSED** | Per-anchor A/I/Δjoint and unit aggregation are emitted at [`runner:2488`](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:2488) and [`runner:2810`](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:2810). Independent hand oracle obtained `η0=10, A=13, I=-3, Δjoint=10, denominator=110`. |
| 11 | **STILL OPEN** | Guard coverage improved, but no independent exact best-response/S_UNI oracle landed; S_UNI operates through the selection shortlist/coarse evaluator. |
| 12 | **STILL OPEN** | The constant is 10 s, but enforcement happens only after committed Shapley validation. A coalition over ten users raises before fallback rather than executing validated BASE. |
| 13 | **STILL OPEN** | Selection-time rows explicitly store empty `shapley_interaction_by_user`; exact Shapley is attempted only after FULL selection. It is not wired into evacuation/proposal selection. |
| 17 | **STILL OPEN** | Required a-γ twin and executed pairwise-distinct 31-setting receipts/KATs remain absent. |
| 18 | **STILL OPEN** | Configuration-local Ψ replaced per-action maxima, but exact selected-coalition Shapley is only attempted for FULL, is absent during selection, and fails for the observed 100-user coalition. |
| 19 | **STILL OPEN** | No reciprocal reuse-mask KAT or real rehearsal rerun landed. |
| 20 | **STILL OPEN** | Zero-legal BASE nulling landed, but the required 11-non-BASE-arm discriminator did not. |
| 21 | **STILL OPEN** | The same **15 tautological/self-derived tests** remain; stage 4c added no closure KATs. |
| 22 | **STILL OPEN** | Dense batch still bypasses `resolve_configuration`; `project_three_offsets`, `encode_c2_state`, and trajectory identity remain test-only/dead on production paths. |
| 23 | **STILL OPEN** | Coarse/two-stage/batch code landed, but the scalar slow path crashes, provider construction remains per setting-unit rather than once per world across settings, and no top-M miss/agreement KAT landed. |
| 24 | **STILL OPEN** | Arithmetic remains correct, but no symbolic unit-carrying KAT landed and `kappa_bits_per_user_s` still misnames a per-user-step quantity. |
| 25 | **STILL OPEN** | Opening-state certificate and allowlist text exist, but the allowlist is declarative rather than enforced and has no dependency-mutation KAT. |
| 26 | **STILL OPEN** | Guard-arm listing is now accurate, but the capability statement that all set arms fall back to BASE is false for the observed large-coalition exception. |
| 27 | **STILL OPEN** | No five-event three-step KAT; more importantly, every step reconstructs one carrier incumbent rather than maintaining each arm’s own closed-loop trajectory. |
| 28 | **CLOSED** | Registry path is exactly `/home/sat/mcrl-records/ATTEMPT-REGISTRY-2026-09.jsonl`. Independent in-memory KAT accepted a valid STARTED→DONE chain and rejected a mutated record. |
| 29 | **STILL OPEN** | Reaggregation now checks bits, joules, four energy components, Φ, changed users, and handovers, but not every receipt field such as availability, service counts/rates, identities, tails, modes, or certificates. |
| 30 | **STILL OPEN** | A conformance helper exists, but it does not check NULL≡BASE, write-once behavior, complete authority, or every comparative harness as required. |
| 31 | **STILL OPEN** | Live-mask stopping code exists; boundary-17 D2-release and 10°-crossing regression KATs remain absent. |
| 32 | **STILL OPEN** | Rows/schema landed, but an invalid batch forecast calls `_projection_from_profile(profile=None)` with `required_power=None` and a non-null cap, causing `MCRLContractError` instead of emitting `INVALID`. |
| 35 | **STILL OPEN** | Timer begins correctly, but large-coalition validation raises before deadline fallback; the complete catalogue→validation→fallback contract is therefore unenforced. |
| 36 | **STILL OPEN** | Namespaces were declared and cluster pooling was added, but `run_unit` unconditionally uses `PROBE_WORLD_DOMAINS`; synthetic pytest receipts therefore carry formal R2 identities. |

## Suite result

`159` tests collected. Under the required read-only environment, `158` executed successfully; the sole remaining test could not set up because pytest’s `tmp_path` fixture found no writable temporary directory. This is an environment-only setup error, not a code assertion failure. The suite also lacks the required stage-4c discriminator tests.

The report is appropriately conservative about not fabricating calibration, rehearsal, or smoke results, but its timing arithmetic and “bit-identical endpoint” premise are false, and the seal draft is internally stale.

VERDICT: STAGE4C=NOT_READY:ENDPOINT,6-8,11-13,17-27,29-32,35-36 | CLOSED=3/26 | TAUTOLOGICAL_KATS=15 | AR0_PROJECTED_CORE_HOURS=>5.969833128 | ANCHOR_SECONDS=>59.698331280