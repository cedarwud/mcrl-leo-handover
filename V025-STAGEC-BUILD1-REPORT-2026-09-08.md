# V0.25 Stage C build 1 report

Date: 2026-09-08. Scope: specification v1 draft and synthetic-only executable scaffolding for stages 6–8. No real/TLE world was constructed, opened, or trained. No file under src/mcrl/env was changed.

## Outcome

Build 1 now connects an engine-neutral per-anchor boundary to versioned Q1/Q2 rows, write-once TRAIN shards, deterministic zero-bootstrap pair regression, five matched learner lineages and six evaluation arms, legal joint deployment, write-once temporal receipts, independent merge/statistics, and an admission/claim decision. The synthetic fixture runs that complete chain.

Important evidence ceiling: IMPLEMENTATION_AND_SYNTHETIC_KAT_ONLY. The synthetic PHYSICS-GO value exercises the decision function and is not authority for real source generation.

The requested hub refresh was attempted first with `git -C /home/sat/mcrl-hub pull --ff-only`; the environment rejected creation of `.git/FETCH_HEAD` because the hub is read-only. All named controller records, declarations, pipeline audits, and legacy references were then read from the existing local hub/audit/workspace snapshots before implementation.

## Tests

Focused acceptance:

    PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest tests/stagec_v025 -q
    ............                                                             [100%]
    12 passed

Executable smoke:

    PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m mcrl.stagec_v025.synthetic --output /tmp/<fresh-dir> --epochs 3 --bootstrap-draws 32

This produces the source shard/sidecar, allocation and deployment-capability manifests/sidecars, a separately registered conformance receipt/sidecar, twenty evaluation unit receipts/sidecars pooling as ten date×seed clusters, append-only attempt registries, and terminal report/sidecar.

The full repository suite collected 2,408 tests before the final temporal-event and malformed-shard KATs and ended with 57 failed, 2,347 passed, 4 skipped. With those two added green KATs the collection is 2,410 tests. The failures are outside this change and already present in the inherited snapshot categories: repository-wide legacy vocabulary/cap guards, stale legacy C3 constructor tests, one prior balanced-BCE expectation, missing git-excluded R7 authority artifacts, and a previously drifted sealed V0.3B source manifest. The focused new suite is green and no failure names src/mcrl/stagec_v025.

Required KAT coverage:

- tiny fixture → rows → shard reopen → five seeds × five learned arms plus external BASELINE → deployment → 20 worlds pooled into 10 date×seed clusters → merge → claim decision;
- NULL exactly equals BASE in conformance and every arm executes a physical synthetic step;
- conformance has its own STARTED-before-outcome/DONE chain and write-once receipt;
- two individually legal argmax picks forming an illegal joint profile are never committed and fall back to BASE;
- coordinator/resolver validation failure atomically commits BASE;
- DROP_C1/C2/C3 retain, update, checkpoint, and deploy all C1/C2/C3 heads;
- summary mutation with unchanged rows is rejected even after a fresh receipt SHA and matching fresh STARTED/DONE registry;
- checkpoint cadence at epoch 100, completed_source_epochs, route-update count, sidecar, and authenticated resume;
- source construction rejects TEST;
- the golden tape-to-row KAT checks all 16 Q1 and 22 Q2 values plus masks, labels, and authority digests;
- malformed shard rows are rejected for vector dimensions, selected-mask consistency, lambda/eta mismatch, and forged normalized labels;
- temporal initial-entry/stay events, a noncontiguous disconnected/partial-service roster, multiple worlds per cluster, and unequal-energy pooled-ratio arithmetic are covered.

## Implemented files

- V025-STAGES-6-8-SPEC-v1-DRAFT-2026-09-08.md — proposed exact Q1/Q2 schemas and full stage 6–8 contract.
- src/mcrl/stagec_v025/state.py — schemas, engine-neutral protocol, extractor.
- src/mcrl/stagec_v025/shards.py and canonical.py — canonical JSONL, digests, TRAIN assertion, write-once publication.
- src/mcrl/stagec_v025/learner.py and arms.py — typed pair batches, deterministic epochs, neutral-source arms, checkpoints/resume.
- src/mcrl/stagec_v025/deployment.py — Q1+Q2 masked proposals, joint validation, coordinator/deadline/fallback, capability manifest, S_UNI.
- src/mcrl/stagec_v025/evaluation.py — allocation, attempt chain, conformance, temporal receipt rows.
- src/mcrl/stagec_v025/merge.py — re-aggregation, pooled ratios, cluster/delta/two-way inference, decisions.
- src/mcrl/stagec_v025/synthetic.py — executable no-TLE end-to-end fixture.
- tests/stagec_v025/test_stagec_pipeline.py — twelve acceptance/KAT tests.

## physics_v025 interface assumptions

The package deliberately imports no physics_v025 runtime type. A future thin adapter must make these assumptions true:

1. The engine publishes one complete per-anchor result per focal user, with a stable BASE index and stable legal physical-action order.
2. A physical action is null or exactly (NORAD integer, beam-chain integer); candidate slot/cell indexes are not physical identity.
3. Every user has an explicit disposition; a user with no radio candidate has a legal null action and does not collapse other users' catalogue.
4. One beam-chain has one colour/hardware identity and selected aggressor cross-gains are keyed by full beam identity.
5. Current fields and labels are causal functions of visible primitives, legal masks, keyed fading, declared prior committed state, and sealed prices; hidden warm-start age is absent.
6. Background means previous committed served users, excluding focal, at the decision instant; activation is before focal insertion.
7. The engine supplies uncapped signed rate-target SINR margin, uncapped required-power/cap, selected nominal ACM SE, angle, D2/visibility remaining time, and refresh phase.
8. A missing incumbent has zero incumbent-margin placeholder plus explicit missing_incumbent=true.
9. Exactly three ordered C2 offsets are supplied. They are nominal/fading-blind; focal survival is absorbing within the forecast; INVALID is not replaced; required-power margin is uncapped and signed.
10. The engine supplies C1 whole-network difference-surplus bits and Φ difference separately, C2 post-penalty bits, and interaction-only C3 share bits. No C3 e_i survives.
11. lambda and eta_ref are identical, positive, and explicit. Stage 4 supplies a positive κ bit normalization scale, not merely an unconverted bits/(user·s) rate.
12. Code/physics/launch/catalogue/setting/calibration/provider/archive/allocation/deployment-capability identities are immutable lowercase SHA-256 values.
13. Source rows and final outcomes use the same physics/endpoint code digest.
14. The bounded catalogue is stage-4 authoritative, has the ≤4096 synthetic/full-product branch and declared real-world unilateral/top-two/top-K/evacuation branch, and includes BASE.
15. A profile resolver is deterministic, reports the same proposed physical profile, includes the complete roster, enforces live D2/10-degree legality, and distinguishes decoding, partial service, and complete-service user-steps.
16. The resolved energy component ledger sums bit-for-bit to endpoint joules and includes every setting-specific PA/circuit/baseband/standby contribution exactly once.
17. The host supplies an InitialTemporalState per unit and arm containing the committed `t-1` physical profile and ever-served users; the evaluator exposes each arm's new profile, and Stage C advances that arm's history rather than reusing same-step BASE.
18. Cell re-key is explicitly reported. Event identity is enough to distinguish stay, beam change, satellite change, re-entry, exit, and re-key.
19. Interruption timing and Φ use the same engine event ledger. Stage C receipt accounting must reconcile with it.
20. Formal evaluation fading/physics randomness is keyed by world/time and common across arms, never by arm or evaluation order.
21. BASELINE and NULL call the identical authenticated baseline implementation and produce identical complete StepOutcome values.
22. S0/S3 has authenticated access to all-user geometry/actions/cross-gains/forecasts and can complete proposal-to-fallback inside the declared timer.
23. The allocation resolves TLE date independently from start UTC; TLE date × learner seed is the cluster and multiple worlds in a cluster are valid.
24. A formal panel provides the date×learner-seed rectangle needed by the two-way supplement; the primary one-way cluster bootstrap does not require a rectangle.
25. The controller supplies a writable, single-authority registry path. Build 1 injects a local path because the hub is read-only here.
26. Write-once publication relies on regular files and same-filesystem hard links; production storage must preserve O_EXCL/link/fsync/read-only semantics.
27. The current stage-2 state_v025 module remains an observation reference only. The future adapter must not stamp its old 21-field SHA on completed 22-field rows.

## CONTROLLER_DECIDE inventory

1. Q1-SCALES — seal all proposed normalization scales.
2. Q2-MISSING-PLACEMENT — seal field order.
3. Q2-SCHEMA-SEAL — seal full manifest and new SHA.
4. Q2-INCUMBENT-MARGIN — repeated incumbent versus candidate-current semantics.
5. KAPPA-BIT-SCALE — resolve current unit mismatch and provide κ in bits.
6. C3-SET-REPRESENTATION — formal S3 input/padding/order and larger-set Shapley method.
7. FORMAL-LEARNER — network, optimizer, hyperparameters, budgets, serialization, stopping.
8. LEARNER-SEED-VALUES — five exact seeds/domains and external BASELINE authentication.
9. COORDINATOR-MODE — learned S3 or exact S0 primary and corresponding information claim.
10. DEADLINE-CLOCK — production host/clock/concurrency/cache timing contract.
11. FORMAL-ALLOCATION — exact worlds/dates/starts/seeds/anchors/thinning and manifest.
12. EVENT-QOS — re-entry and cell-rekey handover/Φ treatment.
13. ZERO-BIT-DISPOSITION — formal undefined bootstrap draw rule.
14. ZERO-QOS-BASELINE — relative handover/Φ rule when DROP is zero.

## Before real source generation

Real source generation remains blocked until all of the following are complete:

- engine stage 4 lands and passes its independent KATs for targets, beam-specific cross-gains, bounded catalogue, event ledger/interruptions, live legality, roster, forecasts, calibration, and endpoint identity;
- the authenticated provider, archive, TRAIN split, catalogue, calibration file, code/physics digest, and deployment capability are sealed;
- every CONTROLLER_DECIDE item above is resolved and schema hashes regenerated if any choice changes;
- the concrete adapter from stage-4 per-anchor output to PerAnchorEvaluation is implemented and its golden tape-to-row KAT passes;
- the formal nonlinear Q1/Q2 and chosen S3/S0 implementation replaces synthetic linear heads and passes resume/determinism tests;
- five formal learner seeds, the external BASELINE, exact allocation, attempt-registry authority, zero dispositions, and report root are sealed;
- real-provider conformance runs only on allocated KAT/rehearsal worlds and passes NULL≡BASE, all-arm step, timing/fallback, and receipt checks;
- PHYSICS-GO is issued by the matrix admission decision.

## Environment limitations

The required git -C /home/sat/mcrl-hub pull --ff-only was attempted first and failed because the sandbox cannot write /home/sat/mcrl-hub/.git/FETCH_HEAD. All controller records were read from the local hub snapshot. Commit status is reported at handoff after the sandbox commit attempt.
