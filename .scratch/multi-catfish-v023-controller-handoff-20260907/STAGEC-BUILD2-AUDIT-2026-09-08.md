Build 2 is not ready for seal. The implementation contains useful scaffolding, but key contract guarantees are declarations or caller conventions rather than enforced properties. Most importantly, S3’s score source is unbound, the acceptance tests splice together parallel paths, experiment identity is forgeable, and feature provenance does not prevent future-information leakage.

### Attack findings

1. **S3 can silently collapse to S0 or the additive decoder.**

   - `DeploymentAdapter` accepts an arbitrary `coordinator` callback, allowing exact Ψ, learned Ψ, or constant zero without recording which was used ([deployment.py:232](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:232)).
   - `ProfileSelector("S3")` accepts `knockout_route="C3"` without experiment/checkpoint authority ([deployment.py:525](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:525)).
   - Coalition contexts are not authenticated against their catalogue profile. A multi-user profile can be paired with an empty/singleton context, forcing the hard-zero interaction ([learner.py:628](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/learner.py:628), [deployment.py:572](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:572)).
   - Read-only probe confirmed an S3 joint profile accepted falsely empty contexts and reduced to its additive score.

2. **T1/T2 do not exercise one production builder→training→deployment path.**

   - T1 builds coalition rows, fits a test model using `fit_closed_form`, then separately performs one orchestrator update ([test_contract_v1_acceptance.py:297](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:297), [test_contract_v1_acceptance.py:348](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:348)).
   - T2 again uses `fit_closed_form` on the same three contexts it evaluates, not the production epoch trainer or held-out cases ([test_contract_v1_acceptance.py:384](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:384)).
   - Its Q1/Q2 tables are handwritten; the source extractor is invoked only in an unrelated poison check.
   - Repair and timeout assertions use legacy `ThreeRouteModel`/`DeploymentAdapter`, not the v1 `ProfileSelector` interaction path ([test_contract_v1_acceptance.py:489](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:489)).
   - The separate synthetic E2E test does connect extraction, training and deployment, but does not exercise the T1/T2 reversal/intervention assertions ([synthetic.py:425](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/synthetic.py:425)).

3. **T3 touches the real merger, but its calibration does not pass raw receipts through it.**

   - The raw-receipt portion uses three dates and two learner-seed values; it does not contain controlled 3/5/10% date/seed effects ([test_contract_v1_acceptance.py:594](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:594)).
   - The 3/5/10% calibration starts from already aggregated `AdditiveTotals` and calls `infer_cluster_totals`, bypassing `EvaluationRunner`, receipt validation, raw-row reaggregation and `merge_receipts` ([acceptance.py:83](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/acceptance.py:83)).
   - It does report coverage, component power, conjunction power and binomial Monte Carlo uncertainty at 5 and 12 seeds. However, this report is not produced by the terminal merger.
   - Reported 12-seed conjunction power was 0.422 ± 0.121, versus the contract’s approximate 0.64; the test passes because its tolerance is two very wide Monte Carlo half-widths ([test_contract_v1_acceptance.py:659](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:659), [build report:35](/home/sat/mcrl-v025-codex-ws-stagec/V025-STAGEC-BUILD2-REPORT-2026-09-08.md:35)).

4. **The four experiment dataclasses are separate; executions are not.**

   The four literal schemas exist ([experiments.py:11](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/experiments.py:11)), but `AllocationUnit.experiment_id` is unrestricted text and neither the runner nor merger requires an experiment object/digest ([evaluation.py:38](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/evaluation.py:38)). A read-only probe successfully labelled an otherwise generic synthetic allocation as `mcrl-v025-checkpoint-knockout-v1`. Neutral-source, oracle and knockout executions can therefore be mislabelled.

5. **BASE-first and timeout enforcement are split across paths.**

   - `select_runner_timed` and `select_with_preparation` validate BASE before starting an outer future timeout ([deployment.py:341](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:341)).
   - The inner solver also polls its own clock ([deployment.py:261](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:261)).
   - Python `future.cancel()` cannot stop an already-running worker, so this is return-time fallback, not guaranteed cancellation.
   - The contract’s v1 `ProfileSelector` has no timer at all. Therefore runner enforcement exists only around the parallel adapter route, not as a property of the canonical selector.

6. **TEST is rejected nominally, but provenance laundering and future leakage remain possible.**

   - Explicit `split="TEST"` is rejected by tapes, source extraction and allocation ([tapes.py:246](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/physics_v025/tapes.py:246), [state.py:251](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/state.py:251), [evaluation.py:110](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/evaluation.py:110)).
   - But Stage C is not actually connected to a tape-derived adapter. It trusts caller-supplied `split`, forecasts, labels and opaque authority digests.
   - `CoordinatorInformation.future_tle_access` is declared but never validated. A probe accepted `UNRESTRICTED_FUTURE_TLE` ([interfaces.py:119](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/interfaces.py:119)).
   - Replacing `ActionEvaluation.forecasts` with arbitrary “realised future” values changes Q2 features; there is no provenance or dependency-allowlist check ([state.py:303](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/state.py:303)).
   - T2 poisons unused extra attributes instead of the forecast values actually consumed, so its leakage assertion is not decisive ([test_contract_v1_acceptance.py:409](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:409)).

### Clause-by-clause audit

| Clause | Status | Evidence and test |
|---|---|---|
| A1 | PARTIAL | Information record constrains strings/digests, but is not wired to source/deployment provenance ([interfaces.py:18](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/interfaces.py:18)); T2 only constructs it. |
| A2 | CONTRADICTS | Catalogue/output coverage exists, but future-TLE value is unchecked ([interfaces.py:104](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/interfaces.py:104)); no negative test. |
| A3 | IMPLEMENTED | Separate reference fields, deterministic Q1+Q2 repair and distinct committed-history event accounting ([deployment.py:118](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:118)); T2 repair test. |
| A4 | PARTIAL | Equality authenticator exists, but selector/runner never requires its digest ([interfaces.py:185](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/interfaces.py:185)); T2 tests utility only. |
| B1 | PARTIAL | TRAIN and lineage checks exist, but no tape→row production adapter or dependency-allowlist KAT; labels are caller supplied ([state.py:303](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/state.py:303)); `test_train_assertion…`. |
| B2 | IMPLEMENTED | Exact 16-field Q1 schema and forbidden-field list ([state.py:29](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/state.py:29)); `test_golden_tape_to_row…`. |
| B3 | IMPLEMENTED | Exact 22-field Q2 schema and three offset blocks ([state.py:48](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/state.py:48)); `test_golden_tape_to_row…`. |
| B4 | IMPLEMENTED | Φ-inclusive and physical identities built exactly before serialization ([targets.py:385](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/physics_v025/targets.py:385)); T1 lines 228–237. |
| B5 | PARTIAL | Coalition schema/context and reporting credit exist; >4 decomposition and weights are not implemented—only an unverifiable count/flag ([coalitions.py:274](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/coalitions.py:274)); T1 checks flag only. |
| C1 | CONTRADICTS | Pairwise zero-bootstrap exists, but the implemented linear/full-batch learner is not the required frozen legacy heterogeneous design; literals remain undecided ([learner.py:223](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/learner.py:223), [draft:143](/home/sat/mcrl-v025-codex-ws-stagec/V025-STAGES-6-8-SPEC-v1-DRAFT-2026-09-08.md:143)). |
| C2 | PARTIAL | Set head and three selector modes exist, but contexts/scores are unauthenticated and timing is a separate path ([learner.py:604](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/learner.py:604), [deployment.py:496](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:496)); T2 misses bypasses. |
| C3 | CONTRADICTS | Four schema classes exist but have no binding to allocations, execution or receipts; mislabelling is accepted ([experiments.py:11](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/experiments.py:11), [evaluation.py:38](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/evaluation.py:38)). |
| C4 | MISSING | Merger gives S0/S_UNI pooled B/E only—no paired FULL>S_UNI inference, QoS comparison, compute comparison or decision-nonadditivity statistic ([merge.py:784](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/merge.py:784)); no test. |
| C5 | PARTIAL | Complete synthetic declaration fields and retained-head updates exist, but real seals remain unresolved ([learner.py:448](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/learner.py:448)); T1 covers only synthetic C3. |
| C6 | MISSING | Wording exists only in the draft; no terminal rule binds a zero C3 marginal to claim termination or freezes redesign. |
| C7 | PARTIAL | Twelve seeds/shared initialization/batch digests exist; v1 trainer neither writes/loads nor automatically emits 100-epoch checkpoints ([learner.py:716](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/learner.py:716)); cadence test covers legacy orchestrator. |
| D1 | PARTIAL | TRAIN, 12 seeds, ≈160 dates and two worlds are validated for `role=claim`; baseline SHA and globally disjoint development history are absent ([evaluation.py:144](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/evaluation.py:144)). |
| D2 | IMPLEMENTED | Product-weight date×seed bootstrap, arm pairing, pooled ratio, supplementary methods and seedwise effects ([merge.py:262](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/merge.py:262)); T3 and pooled-ratio test. |
| D3 | IMPLEMENTED | B=0/E>0 is zero EE; zero E or zero comparator EE produces counted undefined draws ([merge.py:164](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/merge.py:164)); `test_unequal_energy…`. |
| D4 | IMPLEMENTED | One three-component intersection–union claim and TRAIN-only wording ([merge.py:418](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/merge.py:418)); T3 QoS rejection. |
| D5 | PARTIAL | Registry, raw-row reaggregation and receipt hashes exist, but “real-step” is an arbitrary evaluator callback and training/evaluation physics digests are not cross-bound ([evaluation.py:550](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/evaluation.py:550), [merge.py:741](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/merge.py:741)). |
| E | PARTIAL | Sensitivities and MC uncertainty are reported, but calibration bypasses the real receipt merger and is too imprecise to confirm the advertised conjunction power ([acceptance.py:83](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/acceptance.py:83)); T3. |
| F1 | PARTIAL | Left-boundary benchmark application exists, but retrospective TLE provenance and any causal operational variant are not executable Stage-C contracts ([adapter.py:167](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/physics_v025/adapter.py:167)); no Stage-C test. |
| F2 | CONTRADICTS | Outer timeout exists only around the adapter; running threads are not actually cancelled and `ProfileSelector` is untimed ([deployment.py:341](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:341)); T2 times legacy path. |
| F3 | PARTIAL | All named fields exist, but empty latency samples and synthetic defaults are accepted; operational values remain unresolved ([deployment.py:143](/home/sat/mcrl-v025-codex-ws-stagec/src/mcrl/stagec_v025/deployment.py:143)); E2E checks only digest presence. |
| G/T1 | PARTIAL | Most isolated mechanics exist, but it is not one executed three-step production fixture and knockout is not checkpoint-bound ([test_contract_v1_acceptance.py:223](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:223)). |
| G/T2 | PARTIAL | Reversal/placebo assertions exist, but training is closed-form/in-sample and repair/timer use a parallel legacy path ([test_contract_v1_acceptance.py:384](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:384)). |
| G/T3 | PARTIAL | Raw receipts reach `merge_receipts`, while power/coverage scenarios bypass it via preaggregated totals ([test_contract_v1_acceptance.py:594](/home/sat/mcrl-v025-codex-ws-stagec/tests/stagec_v025/test_contract_v1_acceptance.py:594)). |

H is not included in the contract’s enumerated 28-clause denominator. It is only partially enforced: documentation and synthetic reports retain HOLD, but source builders do not require calibration-freeze or PHYSICS-GO authority ([build report:61](/home/sat/mcrl-v025-codex-ws-stagec/V025-STAGEC-BUILD2-REPORT-2026-09-08.md:61)).

Fresh execution was constrained by the requested read-only environment: normal pytest could not create a temporary directory. Collection found the expected 35 targeted tests; 27 tests not requiring writable temporary paths passed. The build report records a previous 35/35 run, but green pytest results do not cure the semantic path gaps above.

VERDICT: BUILD2=NOT_READY:S3-path-binding,T1/T2-production-path,T3-raw-merger-calibration,experiment-schema-binding,F2-cancellation,feature-provenance,unsealed-production-literals | IMPLEMENTED=7/28 | T1=FAIL T2=FAIL T3=FAIL