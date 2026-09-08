# Pipeline audit C — evaluation, statistics, leakage, and harness discipline

## Scope and method

[VERIFIED] This was a read-only source audit; no simulations or files were changed. The code-review workflow split specification/statistics, leakage, and harness checks into parallel reviews, followed by source-level reconciliation.

[VERIFIED] Path abbreviations used below:

- `MAP` = `/home/sat/mcrl-v023-codex-audits/END-TO-END-PIPELINE-MAP-2026-09-08.md`
- `MATRIX` = `/home/sat/mcrl-v025-stage2-snapshot-20260908/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py`
- `PROVIDER` = `/home/sat/mcrl-v025-codex-ws-provider/src/mcrl/physics_v025/provider_legacy.py`
- `STAGEC` = `/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py`
- `FIGURES` = `/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py`
- `C3S` = `/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_screen.py`
- `DIAG` = `/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_diagnostic_arms.py`
- `E1` = `/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py`

[VERIFIED] The most basic newly exposed assumption is: a temporal QoS endpoint requires a stateful trajectory per arm. The successor probe does not satisfy it.

## Critical findings

### 1. NEW CORE RISK — successor handover and Φ endpoints are not temporal

- [VERIFIED] **Assumption:** Each arm’s handover count and Φ are computed from that arm’s previously committed physical association.
- [VERIFIED] **Where:** `MATRIX:659-700` sets `before = base.assignments`, compares it with the same-step selected configuration, and hard-codes `cell_rekey=False`. `MATRIX:715-759,985-994` rebuilds BASE each step and carries no prior per-arm association.
- [VERIFIED] **Map/declaration status:** The claimed “common physical event ledger” at `MATRIX:870-875` is refuted for this runner.
- [INFERRED] **What breaks:** Φ and handover noninferiority measure counterfactual edits versus that step’s BASE, not stay/change/re-entry/re-key events over time. Persistent non-BASE assignments can be repeatedly counted, actual churn can be missed, and cell rekeys are always zero.
- **Guard test:** A three-step fixture per arm containing a stay, physical beam change, satellite change, re-entry, and cell re-key; assert exact event kinds and Φ from persisted prior physical identities.
- **Owner:** Stages 1, 4, and 8.

### 2. NEW CORE RISK — write-once receipts do not prevent outcome-selected reruns

- [VERIFIED] **Assumption:** Immutable terminal receipts enforce exactly one attempt for each prespecified unit.
- [VERIFIED] **Where:** Matrix physics completes before its receipt is created (`MATRIX:1425-1433`). C3-S and diagnostics likewise execute before publication (`C3S:1312-1342`; `DIAG:961-987`). A crash or SIGKILL can therefore leave no evidence that outcomes were opened.
- [VERIFIED] **Where:** Matrix accepts arbitrary output roots and has no launch/code/provider authority (`MATRIX:1355-1369,1413-1438`). Its write-once check is local to one pathname (`MATRIX:1216-1234`).
- [VERIFIED] **Where:** C3-S authorities bind one root, but `build_c3s_launch_authority.py:14-84` can mint another root without an append-only issuance ledger. Legacy Stage-C is stronger because it writes an attempt marker before episode work (`STAGEC:1788-1813`).
- [INFERRED] **What breaks:** Multiple internally valid roots may be generated and only a favorable one reported. SHA-256 establishes integrity, not uniqueness or outcome blindness.
- **Guard test:** Atomically register `STARTED` before any outcome-producing call in a controller-owned append-only registry keyed by experiment, panel, cell, and unit. Merge must reject duplicate or abandoned unadjudicated attempts.
- **Owner:** Stage 8/controller.

### 3. NEW CORE RISK — the bootstrap’s “training seed” is the environmental world seed

- [VERIFIED] **Assumption:** Cluster identity really is TLE date × one of five fixed learner/training seeds.
- [VERIFIED] **Where:** `physics_v025/tapes.py:42-49` creates a unique seed from each world domain. `PROVIDER:298-319` stores that world seed as `training_seed`. `MATRIX:1251-1259` treats it as the statistical training-seed coordinate.
- [VERIFIED] **Where:** If two receipts actually share a declared `(date, learner_seed)` cluster, `MATRIX:1251-1259` rejects them as duplicates rather than pooling their additive totals.
- [VERIFIED] **Map status M1:** Refuted. The implemented coordinate is date × environmental-world-seed, and there is no five-model-seed dimension.
- [INFERRED] **What breaks:** Shared-date orbital inputs can be treated as independent, learner-seed variation is absent, and uncertainty can be materially too narrow.
- **Guard test:** Use two dates × two learner seeds × multiple episode seeds. First aggregate `ΣB`, `ΣE`, and QoS numerators within `(date, learner_seed)`, then assert that only four clusters are resampled.
- **Owner:** Stage C/8 and provider interface.

### 4. NEW CORE RISK — a real formal probe outcome was opened before the declared seals

- [VERIFIED] **Assumption:** Dry-run, rehearsal, and provider KATs cannot touch formal probe domains before provider/world/analysis seals.
- [VERIFIED] **Where:** Provider installation occurs before mode dispatch (`MATRIX:1373-1376`). Dry-run and rehearsal evaluate `V025_PROBE/world/1` without formal manifests (`MATRIX:1052-1093,1380-1396`).
- [VERIFIED] **Actual path:** `/home/sat/mcrl-v025-codex-ws-provider/.tmp-prompts-v025/provider.log:76955-76968,79552-79558` records `LegacyWorldProvider`, `V025_PROBE/world/1`, `StepEvaluator(a-r0)`, and a printed real outcome: bits `138034644600.74075`, joules `6255.138642826578`, served `100`.
- [VERIFIED] **Report status:** This refutes the statement that no real formal successor outcome had opened in `V025-ENGINE-STAGE2-REPORT-2026-09-08.md:5`.
- [VERIFIED] **Where:** The default synthetic provider and real provider use the same `V025_PROBE/world/*` domains and seeds (`MATRIX:115-117,961-1008`; `PROVIDER:163-173,299-319`), while receipts do not bind provider source identity.
- [INFERRED] **What breaks:** The formal-world freshness claim is already lost for world 1; synthetic and real worlds can be conflated; provider, catalogue, and anchors could be changed after observing formal geometry or outcomes.
- **Guard test:** Quarantine probe world 1; allocate replacement domains prospectively. Require distinct `V025_SYNTHETIC/*` and `V025_PROVIDER_KAT/*` namespaces plus provider source, archive, split, and allocation-manifest digests in every world identity.
- **Owner:** Stages 0, 4, and 8.

## High findings

### 5. Endpoint pooling is correct, but merge does not independently enforce it

- [VERIFIED] **Assumption:** The endpoint is exactly `ΣB/ΣE`, including every bootstrap draw.
- [VERIFIED] **Legacy:** Step rates and power become additive episode totals at `STAGEC:954-987`; `pool_receipts` sums episode bits and energy and divides once at `STAGEC:878-904`; adjudication consumes that field at `STAGEC:907-951`.
- [VERIFIED] **Legacy reporting:** `FIGURES:383-409` reconstructs pooled totals. Its descriptive bootstrap resamples matched episode indices and recomputes both sums inside each draw (`FIGURES:920-966`); it does not average episode EE.
- [VERIFIED] **Successor:** Per-unit aggregation sums step bits/joules then divides (`MATRIX:786-801`). Each bootstrap draw samples paired rows, sums columns, and computes the two ratios afterward (`MATRIX:898-916`).
- [VERIFIED] **Potential sum-of-ratios path:** `MATRIX:909-910,939-944` averages per-cluster log EE ratios only for the explicitly supplementary log interval. It is marked as not substituting for the pooled estimator.
- [VERIFIED] **Where enforcement fails:** Merge trusts `failure_analysis.arms` (`MATRIX:1263-1279`) after checking only hashes and identities (`MATRIX:1302-1327`); it never rebuilds summaries from the sealed `steps`. Unkeyed hashes can faithfully authenticate an inconsistent or buggy summary.
- [INFERRED] **What breaks:** An alternate unit writer or reduction bug could introduce per-episode means into the adjudicated summary without merge detecting disagreement with raw steps.
- **Guard test:** Unequal-energy fixtures for observed estimates and known bootstrap draws; mutate the summary while leaving steps unchanged, recompute hashes, and require merge to reject by independently reaggregating.
- **Owner:** Stage 8.

### 6. NEW CORE RISK — receipts are not sufficient for exact independent reaggregation

- [VERIFIED] **Assumption:** Every receipt records per-step bits, joules, served/opportunities, handovers, and Φ using canonical hex floats.
- [VERIFIED] **Matrix:** Step rows contain aggregate values but use ordinary JSON floats and omit physical transition identities (`MATRIX:679-703`). A hex-capable profile exists at `src/mcrl/physics_v025/adapter.py:66-91` but is unused here.
- [VERIFIED] **Legacy Stage-C:** Ten steps are discarded into episode totals; receipts use decimal floats and contain neither handovers nor Φ (`STAGEC:767-857,954-987`).
- [VERIFIED] **C3-S:** Per-step bits and energy are hex with served/opportunities, but handovers and Φ are absent (`C3S:801-878`).
- [VERIFIED] **Diagnostics:** Per-step bits/energy are hex and handover/renewal counts exist, but Φ and event identities are absent (`DIAG:450-481`).
- [VERIFIED] **E1:** Hex profile bits/energy and served are present, but no temporal handover/Φ ledger (`E1:751-764`).
- [INFERRED] **What breaks:** A referee cannot independently reconstruct the event classification, Φ pricing, or all claimed aggregations from sealed receipts; hashes authenticate lossy summaries.
- **Guard test:** One canonical per-step schema containing hex endpoint and energy-component values, additive opportunities, prior/current physical identities, event type, and exact Φ numerator/denominator; require independent bit-for-bit reaggregation.
- **Owner:** Stages 4 and 8.

### 7. Legacy selection and diagnostic panels are TRAIN-reused, not fresh date clusters

- [VERIFIED] **Assumption:** “Fresh world” seed checks imply fresh statistical clusters.
- [VERIFIED] **Exact reuse:** S0 authenticates and replays E1 tapes (`run_probe_s0.py:285-350`). Diag2 imports the C3-S worlds, domains, and lineages (`DIAG:32-37`); diag3 explicitly reuses the same 4×3 panel.
- [VERIFIED] **Selection path:** C3-S binds E1 and S0 result artifacts before choosing its screen (`C3S:65-68,99-108`). Its claim ceiling is explicitly TRAIN-development/no-efficacy/no-TEST (`C3S:56`).
- [VERIFIED] **Date reuse:** E1 and C3-S exclude prior integer seeds, not resolved TLE dates (`E1:614-623`; `C3S:451-554`). The sampler draws from the common TRAIN date pool (`src/mcrl/env/ephemeris.py:382-427`).
- [VERIFIED] **Read-only date resolution:** The fixed 9,000-world legacy Stage-C plan reaches all 166/166 TRAIN dates; hence every E1/C3-S TRAIN date is already a Stage-C date cluster even though exact seeds differ.
- [INFERRED] **Current successor probe:** Its four dates are incidentally different from the eight E1/C3-S dates, but no assertion seals that separation.
- [UNKNOWN] **Future successor claim:** No successor Stage-C panel exists, so overlap with E1, S0, C3-S, diag2/3, calibration, or provider KAT worlds cannot be determined. A proposed ≈161-date TRAIN panel cannot be date-disjoint from a prior panel covering all 166 TRAIN dates.
- [INFERRED] **What breaks:** Selection and evaluation share the orbital-date factor while uncertainty treats date as part of the independence unit.
- **Guard test:** Persist resolved start UTC, TLE date, split, role, archive digest, learner seed, and world seed in a single pre-outcome allocation manifest; assert role-wise date disjointness.
- **Owner:** Stages 0 and 8.

### 8. The declared Stage-8 panel is not an implemented evaluation runner

- [VERIFIED] **Assumption:** The referenced matrix runner implements the sealed 6-arm × 5-seed × ≈600-world claim design.
- [VERIFIED] **Where:** `MATRIX:93-107` has 12 arms. `MATRIX:1302-1308` hard-codes four worlds. Units default to three steps. The merge spans 31 physics settings, not five learner seeds.
- [UNKNOWN] **Map status:** The future 6×5×≈600 design may be prospective, but there is no successor source/training/Stage-C runner with which to verify it. `MAP:64` itself says that runner is “to write.”
- [UNKNOWN] **Same-code invariant:** Whether training and final evaluation use the same physics/endpoint implementation cannot be verified until the source generator, learner deployment adapter, and final runner exist.
- [INFERRED] **What breaks:** Probe admission can be mistaken for confirmatory evaluation; the promised seed, panel, endpoint, and selection/evaluation boundaries remain unenforceable.
- **Guard test:** End-to-end synthetic claim-plan test asserting exact arm set, five fixed learner seeds, full predeclared world allocation, common physics digest, and complete terminal adjudication.
- **Owner:** Stages 6–8.
- [VERIFIED] **Blocker:** The missing successor Stage-C runner is a release blocker.

### 9. No inspected harness has all four claimed controls

- [VERIFIED] **Assumption:** Every harness has mandatory NULL≡BASE, a real-step dry-run, immediate write-once SHA receipts, and a complete authority manifest.

| Harness | NULL placebo | Real-step dry-run | Receipt discipline | Authority |
|---|---|---|---|---|
| C3-S v1 | [VERIFIED] Absent; only BASE/FULL/LITE (`C3S:69-80`) | [VERIFIED] No step (`C3S:1829-1835`) | [VERIFIED] Yes: exclusive create, SHA sidecar, fsync, 0444 (`C3S:672-697`) | [VERIFIED] Yes |
| Diagnostic | [VERIFIED] Optional flag (`DIAG:126-146,1075-1077`) | [VERIFIED] No step (`DIAG:1089-1103`) | [VERIFIED] Yes | [VERIFIED] Yes |
| E1 | [VERIFIED] Absent/N/A | [VERIFIED] Simulator-inert (`E1:2-7,2381-2397`) | [VERIFIED] Partial: atomic/0444/internal digest, not every-file sidecars (`E1:1333-1497`) | [VERIFIED] Yes |
| Legacy Stage-C | [VERIFIED] Absent; four non-NULL arms | [VERIFIED] No physical all-arm step | [VERIFIED] Partial: collision protection and terminal tree seal, but writable/no immediate sidecar (`STAGEC:260-282`; `stagec_common.py:802-848`) | [VERIFIED] Yes |
| Successor matrix | [VERIFIED] Partial: same BASE object, limited equality test (`MATRIX:740-753`; `test_stage2_runner.py:64-80`) | [VERIFIED] Partial: all arms only in synthetic `a-r0` (`MATRIX:1380-1391`) | [VERIFIED] Yes (`MATRIX:1216-1234`) | [VERIFIED] Partial: no launch/code/provider authority |

- [VERIFIED] **Map status M4–M6:** Universal write-once/SHA, NULL placebo, and real-step dry-run claims are refuted.
- [INFERRED] **What breaks:** Arm-specific plumbing, provider, state, RNG, and reporting failures can first surface after outcomes open.
- **Guard test:** One shared conformance suite that runs each comparative harness and verifies all four controls, including complete per-step NULL equality.
- **Owner:** Stage 8/provider.

### 10. Legacy Stage-C also has a claim-panel acceptance peek

- [VERIFIED] **Assumption:** Acceptance testing is outcome-inert or uses worlds disjoint from the claim panel.
- [VERIFIED] **Where:** `accept_stage_c_chunk_equivalence.py:100-139` executes 200 episodes per arm from the same 9,000-world plan. Stage-C authenticates those receipts as launch prerequisites (`stagec_common.py:631-668`).
- [UNKNOWN] **Human use:** Source cannot determine whether those outcomes influenced a later choice.
- [INFERRED] **What breaks:** The first 200 claim-world outcomes are available before the formal root begins.
- **Guard test:** Use disjoint acceptance worlds or compare blinded hashes only; prove all scientific choices were sealed before acceptance output.
- **Owner:** Stages 0 and 8.

## Statistical and referee findings

### 11. QoS pooling relies on an unvalidated equal-opportunity assumption

- [VERIFIED] **Assumption:** Every cluster has the same users, horizon, and decision opportunities.
- [VERIFIED] **Where:** `MATRIX:904-908` divides sampled QoS totals by the number of clusters. Bootstrap rows contain no opportunity denominators (`MATRIX:880-891,1267-1279`), and provider installation checks callable names rather than panel dimensions (`MATRIX:1189-1202`).
- [VERIFIED] **Mismatch:** Φ is a cluster total averaged by cluster count, while handover values are rates; neither is reconstructed from additive event/opportunity counts inside each draw.
- [INFERRED] **What breaks:** Variable users, horizons, missing decisions, or censoring produce incorrect weights and margins.
- **Guard test:** Unequal-opportunity clusters; carry additive numerators and denominators and recompute the pooled QoS estimators inside every resample.
- **Owner:** Stage 8/provider.

### 12. The percentile rule is conservative but ambiguously named; δ units are unresolved

- [VERIFIED] **Rule implemented:** EE, availability, and Φ use the 2.5th percentile; handovers use the 97.5th (`MATRIX:917-920`). EE passes only when `lower > 0.5`; zero QoS margins use the correct directions (`MATRIX:929-938`).
- [VERIFIED] **Off-by-one assessment:** These are endpoints of a central 95% interval, equivalent to 97.5% one-sided bounds—not conventional 95% one-sided bounds at 5%/95%. This is conservative, not anti-conservative.
- [VERIFIED] **Method:** `np.quantile`’s default linear interpolation is used and not sealed by name or tested.
- [UNKNOWN] **δ semantics:** `100*(EE_FULL/EE_DROP−1)` is a relative percent, but the declaration and receipt call it “percentage points” (`MATRIX:870-875,901-903,927-930`). EE itself has no percentage-point scale.
- [VERIFIED] **Map status M2:** The promised delta-method supplement is absent; `MATRIX:921-945` returns only percentile bootstrap and paired log-EE results.
- [INFERRED] **What breaks:** A referee cannot reproduce the intended alpha convention or know whether δ is 0.5% relative versus 0.5 absolute normalized-score points.
- **Guard test:** Freeze interval sidedness, quantile method, strict boundary behavior, and δ units with deterministic draws; either implement a named delta-method result or remove it from the declaration/map.
- **Owner:** Stage 8/controller.

### 13. A valid all-outage cluster can abort the supplementary calculation

- [VERIFIED] **Assumption:** The supplementary log-EE statistic is defined for every physically permitted receipt.
- [VERIFIED] **Where:** Validation allows zero bits (`MATRIX:892-896`), but `MATRIX:909-910` unconditionally takes each cluster’s log EE ratio.
- [INFERRED] **What breaks:** A legitimate zero-throughput cluster creates infinity/NaN and may prevent the otherwise valid pooled primary result from merging.
- **Guard test:** Include a zero-bit cluster; require the primary interval to complete and the log supplement to be marked undefined under a prespecified rule.
- **Owner:** Stage 8.

### 14. Multiplicity is defensible only for the narrow conditional IUT claim

- [VERIFIED] **Implementation:** `MATRIX:1283-1292` requires all three FULL−DROP EE and QoS gates, labels the claim conditional, and disclaims main effects. `MATRIX:1293-1299` fixes `a-r0` as primary.
- [INFERRED] **Multiplicity:** No multiplicity adjustment is required for the single prespecified global conjunction. The three component intervals are not simultaneous 95% intervals, and “at least one component works,” regime selection, or choosing among the other 30 cells would require multiplicity/selective-inference treatment.
- [VERIFIED] **Evidence ceiling:** E1, S0, C3-S, diagnostics, legacy Stage-C, and the current successor matrix are TRAIN-only. No generalization or external-efficacy claim is supported.
- [UNKNOWN] **Final wording:** There is no final successor report/runner, so compliance with the conditional TRAIN-panel language cannot be verified.
- [INFERRED] **What breaks:** Reporting component-wise discoveries, a selected sensitivity cell, or general efficacy would exceed the prespecified estimand and evidence.
- **Guard test:** Report-schema test permitting only the fixed `a-r0` conditional conjunction as primary; label all other cells exploratory and forbid TEST/generalization wording unless untouched evidence is added.
- **Owner:** Stage 8/reporting.

## Controller-map disposition

[VERIFIED] Stage 8 contains no literal `?`, but its unguarded assertions resolve as follows:

| Map assertion | Disposition |
|---|---|
| 6 arms × 5 seeds × ≈600 worlds/≈161 dates | [UNKNOWN] Prospective design; final runner absent. Current matrix is 12 arms × 4 worlds, not this evaluation. |
| Independence unit = TLE date × training seed | [VERIFIED — REFUTED M1] Second coordinate is environmental world seed; repeated true clusters are rejected. |
| Pooled `ΣB/ΣE`, including bootstrap draws | [VERIFIED] Correct in legacy and current successor reductions, subject to merge trusting summaries. |
| Supplementary paired log-EE | [VERIFIED] Present and explicitly non-primary. |
| Supplementary delta method | [VERIFIED — REFUTED M2] Missing. |
| δ=+0.5 pp lower-bound rule | [VERIFIED] Strict code gate exists; [UNKNOWN] unit/“pp” meaning. |
| QoS noninferiority margins | [VERIFIED] Zero-margin directions implemented; [VERIFIED] handover/Φ estimands are invalid. |
| One terminal decision | [VERIFIED — REFUTED M3] Merge emits `COMPLETE` plus a primary Boolean, with no experiment-global terminal authority. |
| No TEST | [VERIFIED] Current evidence is TRAIN-only. |
| Conditional intersection–union claim | [VERIFIED] Implemented for three FULL−DROP contrasts in `a-r0`. |
| Same physics/endpoint as training | [UNKNOWN] Successor training and Stage-C runner do not exist. |
| Receipts write-once with SHA on every harness | [VERIFIED — REFUTED M4] Controls are inconsistent and sometimes only terminal/tree-level. |
| NULL≡BASE on every harness | [VERIFIED — REFUTED M5] Absent or optional in most legacy harnesses; incomplete in matrix tests. |
| Dry-run performs a real step for every arm | [VERIFIED — REFUTED M6] Only partially true for the synthetic matrix `a-r0` path. |
| No outcome-selected rerun | [VERIFIED — REFUTED M7] No experiment-global registry or durable pre-step attempt record. |
| Runner tests/diag2 placebo guard the invariants | [VERIFIED — REFUTED M8] Existing tests omit trajectory QoS, full NULL equality, bootstrap quantiles, authority uniqueness, receipt reaggregation, and real-provider dry-run. |

VERDICT: STAGE=C | REFUTED_MAP_CLAIMS=8 | NEW_CORE_RISKS=5 | BLOCKERS=SUCCESSOR_STAGE_C_RUNNER_MISSING,FORMAL_WORLD_1_OPENED_PRESEAL,TEMPORAL_QOS_LEDGER_INVALID,EXPERIMENT_GLOBAL_ATTEMPT_REGISTRY_MISSING,SEALED_PANEL_PROVIDER_AUTHORITY_MISSING