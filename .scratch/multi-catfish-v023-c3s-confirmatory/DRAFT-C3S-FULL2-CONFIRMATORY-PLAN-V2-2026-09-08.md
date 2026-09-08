# C3-S FULL2 confirmatory plan v2 (draft, 2026-09-08)

Status: `DRAFT_PRE_OUTCOME_NOT_LAUNCH_AUTHORITY`. This v2 supersedes the Addendum-A-only arm binding in the earlier draft. The scientific selection function and attempt-3 export-provenance rule are sealed separately from execution code, acceptance, source eligibility, per-rung/per-chunk authorities, and launch.

## 1. Scope, evidence exposure, and claim ceiling

This is a frozen-policy TRAIN-development confirmation, not training, TEST efficacy, or real-time validation. S0, oracle diagnostics, v1 SUPPORT, and possibly the complete variant-matrix results were known before sealing. The design uses shared simulator equations/calibration, centralized telemetry, atomic execution, and matched simulator physics. Initialization dependence and persistence beyond 30 steps remain limitations. Controller computation energy and execution delay are excluded from network EE.

“We report both v1 contrasts and all eight matrix contrasts, representing nine distinct coordinator configurations across four exposed world clusters; repeated BASE/LITE evaluations and shared controls are dependent, no confirmatory multiplicity control applies to these screens, and one configuration selected by the prospectively reconciled rule receives separate fresh-world FULL2 confirmation.”

The v1 equality of 35,971 served opportunities does not establish identical served users, demand satisfaction, or fairness. The confirmatory receipts therefore retain committed service accounting, physical associations, tracking/handover events, and reversals. Coordinator overrides may repair FULL2 proposal errors and do not establish uniquely collective causation.

Claim ceiling: `TRAIN_DEVELOPMENT_FULL2_C3S_CONFIRMATION_NO_LEARNER_NO_TEST_NO_EFFICACY`.

## 2. Arm resolution and frozen policies

“Configuration c is the complete, valid matrix’s progression winner under its sealed mean-total-latency rule and tie order. If that matrix has no SUPPORTer, c is v1-qualified LITE under Addendum A; this fallback derives solely from v1. INVALID_RUN or INCOMPLETE leaves the arm unresolved.”

The matrix tie order is `V-J,V-U,V-M,V-C,V-H,V-P,V-L2,LITE`. The complete matrix receipt must contain all eight dispositions, complete mean total-decision latency, a passing LITE-equivalence audit, and no unexplained same-panel disagreement. Otherwise `ARM_UNRESOLVED` refuses preflight. Both matrix and v1 terminal-receipt SHA-256 digests are recorded.

The two arms, in fixed order, are `FULL2` and `FULL2+C3-S(c)`. They share exactly one digest-bound Q1/Q2 export pair from stage-A attempt #3. Admission requires stage-A `PASS_SOURCE_TRAINING_INTEGRITY`, its declared epoch-100/200-update export manifest, the exact FULL2 checkpoint SHA-256, Q1 and Q2 parameter SHA-256 values, and formal stage-B `PASS_PLUMBING_INTEGRITY`. Missing provenance refuses preflight. No retraining, checkpoint selection, attempt selection using evaluation outcomes, third learned head, fallback configuration, timeout-to-FULL2, adaptive pruning, or catalog expansion is permitted.

The selected configuration is executed through the frozen variant-policy hooks with its whole catalog, objective, guard, ties, policy state, cadence, margin, hysteresis, persistence penalty, and lookahead semantics. Cadence-inactive V-C decisions use FULL2’s own proposal. FULL retains the complete v1 full catalog. FULL2 remains float32 unweighted masked `Q1+Q2`, lowest legal slot tie, and `NOOP=-1` on an empty mask.

“Before the ladder, a speed improvement may receive an append-only implementation binding after independently verified semantic equivalence and bit-identical decisions, ties and policy-state transitions, with unchanged information access and RNG effects; preserve both versions and verification receipts.” Remeasurement cannot rerank the matrix winner.

## 3. Exact estimand, worlds, and accounting

“Compare frozen FULL2+C3-S(c) with the identical frozen FULL2 export pair on N distinct fresh TRAIN worlds, one episode/world/arm, 100 users, T=30, 902.4 simulated seconds. EE is Σbits/Σjoules; service is Σserved/(3,000N); require strictly greater pooled EE and service difference ≥−0.001.”

Rungs are cumulative `N=100,500,1500,3000`. Each arm runs one episode per distinct world; arms start from matched initial state, exogenous streams, and keyed field, then follow their own trajectories. Evaluator purity and exogenous matching are authenticated. Per-episode totals are reduced in episode-index order using `math.fsum`; episode EE values are not averaged.

At N=3,000 there are 6,000 arm-episodes, 180,000 committed steps, 9,000,000 opportunities per arm, and a 9,000-opportunity service allowance. All episodes use TRAIN only. The frozen 9,000-world plan supplies the first 3,000 worlds after a complete freshness/collision census against used and allocated inventories. World-level variation and the actual number of distinct worlds are reported; lineages are not multiplied into the estimand.

Per committed step, `B=30.08*Σ link_rate_bps`, `E=30.08*system_power_w`, and served comes from the committed native resolution. No demand cap or additional energy integral is introduced.

## 4. Chunking, stopping, and closure

Chunks are contiguous 100-episode ranges with authenticated boundary state, write-once episode records, a checkpoint every 100 episodes, exact episode ordering, immutable resume provenance, and per-arm then matched two-arm merge. Both arms must first pass isolated sequential-200 versus 2×100 equivalence. Each rung and each chunk receives its own exact launch authority; only the current released interval may run.

“At independently verified matched N=100 and N=500, failure of either declared EE/service criterion emits FALSIFIED with `EARLY_FUTILITY` and closes progression; otherwise `RUNG_HELD` releases the next interval only. Overall CONTRIBUTION_HELD requires N=3,000.”

This aggressive futility rule may reject a configuration that would recover later. N=1,500 remains a nonterminal release boundary and cannot rescue or falsify. At N=3,000, `C3S_CONTRIBUTION_HELD` requires both criteria; otherwise `C3S_CONTRIBUTION_FALSIFIED` lists every failed criterion and closes progression. `INCOMPLETE` and `INVALID_RUN` never emit HELD/FALSIFIED. Valid FALSIFIED has no rescue.

## 5. Persistent decision records and η diagnostic

Every episode persists 30 decision records, each binding the pre-decision state digest, FULL2 proposal and physical associations, committed profile/actions/configuration, nominal B/E/served, realised B/E/served, phase timing, full decision wall, active-step flag, policy-state transition, action digests, candidate census, RSS, and η diagnostic. Episode receipts bind their ordered decision-record digest.

“Primary η_ref 保持 binary64 `0x1.d94fb72305d6ap+26`。在首個100-episode rung 的全部預定 worlds、lineages、30 steps，對主 C3-S 軌跡既有 nominal candidate cache，以 exact rational 倍率4/5、1、6/5重評；沿用同一 guard、catalog、ties，不新增 seeds 或 physics evaluations。逐值報 selected ID、相對primary的choice agreement、nominal B/E/service及score；全數保留。此為 non-decisional choice-stability diagnostic，不估 closed-loop EE sensitivity，不改 primary、progression 或救援失敗。Rescoring 與輸出成本另記。”

Under matrix-first binding, rescoring applies the selected configuration’s complete frozen objective/history rules with every other constant fixed. It is never decisional and cannot rescue a failure.

## 6. Latency and cost

“逐臂報完整 decision latency（state取得至action返回）及phase mean／median／p95／max、latency/30.08、超時次數／分母；附hardware、CPU allocation、threads、worker concurrency、cache scope／cold-warm條件、catalog／unique evaluations與cache hits。Lite與同態memoization可能降低成本，仍須實測；保留全部evacuations及固定開銷，不保證十倍加速或低於30.08 s。跨episode並行只代表throughput。Latency不是gate，不觸發fallback、pruning或改選。”

“Repeat a prospectively fixed benchmark without competing workers; report all-step and active-step latency separately for cadence variants.” The timer is the full decision wall, not the v1 inner nominal-evaluation timer. No real-time feasibility is claimed. Controller computation energy and execution delay remain excluded from network EE.

The following non-executing `--estimate` table uses v1 terminal receipt `a66b4813…`, complete-decision means FULL2=1.8848 s, LITE=49.4308 s, FULL=66.7924 s. Values are worker-hours; main includes both arms, acceptance is both arms’ sequential-200 versus 2×100 work. Matrix-selected V-* rows must be regenerated from their matrix receipt.

| configuration | N | coordinator only | FULL2 control | main pair | acceptance | main+acceptance |
|---|---:|---:|---:|---:|---:|---:|
| LITE | 100 | 41.192 | 1.571 | 42.763 | 171.052 | 213.815 |
| LITE | 500 | 205.962 | 7.853 | 213.815 | 171.052 | 384.867 |
| LITE | 1,500 | 617.885 | 23.560 | 641.445 | 171.052 | 812.497 |
| LITE | 3,000 | 1,235.770 | 47.120 | 1,282.890 | 171.052 | 1,453.942 |
| FULL | 100 | 55.660 | 1.571 | 57.231 | 228.924 | 286.155 |
| FULL | 500 | 278.302 | 7.853 | 286.155 | 228.924 | 515.079 |
| FULL | 1,500 | 834.905 | 23.560 | 858.465 | 228.924 | 1,087.389 |
| FULL | 3,000 | 1,669.810 | 47.120 | 1,716.930 | 228.924 | 1,945.854 |

These are contention-based planning estimates, not bounds for FULL2 or an optimized winner. Capacity or deadline failure yields delay/INCOMPLETE, never a shortened positive ladder.

## 7. Failure decomposition and descriptive reporting

“On valid FALSIFIED, replay each completed-prefix coordinator state’s FULL2 proposal once under identical realised keys, using isolated archived states.” With `G_p=B-pE` and `p=η_FULL2` for that matched prefix, report `I=Σ[G_p(s_C,a_C)-G_p(s_C,b_C)]` and `R=Σ[G_p(s_C,b_C)-G_p(s_F,a_F)]`; `I+R=ΔB-pΔE`. Separately report nominal/realised paired residuals at η_ref, service differences, and physical reversals. This mode is isolated, non-decisional, has no progression feedback, and cannot rescue.

“Screen有四physical-world clusters、三條重用lineages及每臂36,000 user-step opportunities；不得作36,000獨立觀測。Confirmatory panel報實際distinct-world數。所有結果均報failure codes、全部world／lineage差異、逐步累積bits／joules／served與opportunities。記錄physical association A→B→A（連續三步、A≠B）reversals及native tracking／handover events，勿以slot變號代替。”

“同態residual診斷固定為首rung第一個預定world、全部lineages、steps 0–29；commit後以隔離的predecision-state clone及相同keyed realised field，比較selected action與該C3-S state的BASE proposal。報nominal／realised ΔB、ΔE、Δserved、Δ(B−η_refE)及其差，不拿另一臂state代替。不得回饋selector、調參或rescue；無可驗證state則報不可得。”

“本plan不納入degraded-estimator實驗。未來如執行，須在其outcomes前另封non-decisional協定，固定catalog cross、error magnitudes、bias／correlation、physical-link keying、seeds、coverage及成本；同link跨candidate共用誤差，matched-anchor結果不宣稱closed-loop robustness。”

## 8. Paper language

“C1 and C2 remain training-time Catfish mechanisms producing two learned per-user heads, while C3-S is a newly defined deployment-time model-based set-level coordinator, with no third learned Q-head.”

“The tested additive C3 target/composition showed no positive oracle-level marginal in G0–G3. Three positive staged contributions require FULL2-versus-DROP_C1, FULL2-versus-DROP_C2, and FULL2+C3-S-versus-FULL2 each to satisfy its declared EE/service criteria; these contrasts do not establish C1/C2’s positive marginal within the final coordinated system.”

If HELD: “The prospectively selected frozen C3-S configuration increased pooled network EE relative to frozen FULL2 across 3,000 fresh TRAIN worlds with 100-user, 30-step episodes and met the declared 0.001 served-fraction margin.” “This is development-panel confirmation under matched simulator physics, with controller computation energy and execution delay excluded; TEST efficacy, real-time feasibility and three positive staged contributions require their separate evidence.”

If FALSIFIED: “At the reported predeclared terminal or futility boundary, the selected configuration failed its EE/service criterion and its progression closed.” “S0’s local headroom and v1’s development SUPPORT remain valid evidence, but a positive FULL2 C3-S contribution is unconfirmed; this neither proves coordination universally impossible nor reopens the tested additive-C3 route.”

## 9. Scientific seal, launch gate, and forbidden actions

Seal this plan and its selection function before mechanically appending the matrix/v1 receipt digests, resolved configuration/hash, and exact attempt-3 export provenance. Append-only engineering rebinding requires its independently verified receipt. No science changes follow arm resolution.

Launch remains forbidden until preflight authenticates plan v2, both contracts, both arm-resolution receipts, stage-A attempt #3 PASS/export/checkpoint/parameter hashes, stage-B PASS, frozen code/config/dependencies, 9,000-world census, TRAIN-only eligibility, both arms’ acceptance receipts, and absent output root. Formal authority is issued separately for every rung and every 100-episode chunk.

No TEST, learner update, outcome-driven constant, seed/horizon/regime search, policy fallback, favorable-subset selection, valid-result rerun, or relabelling of `ALL_NEUTRAL_CONTROL` as `BASELINE` is permitted.
