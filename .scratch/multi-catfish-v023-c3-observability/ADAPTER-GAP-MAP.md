# V0.23 adapter closure map (pre-outcome)

Status: implementation map only.  This file does not authorize simulator
access, learner fitting, TEST access, or a scientific decision.

The staged runner has live Python adapter seams, a deterministic source
manifest stage, a production full-roster composition runtime, and an
independent final verifier.  The tables retain the original work breakdown;
their current status is summarized in Section D.  No physical outcome has been
opened.

## A. Per-world physical/source generation (8 shards)

| required operation | existing reusable implementation | adapter work still required |
|---|---|---|
| Authenticate inherited input closure | V0.20 `run_v020_repriced_c3_gate._validate_global_inputs`, `load_repriced_heads`; V0.22 `run._validate_inherited_sources` | Bind the frozen V0.23 manifest and selected lineage before opening a simulator. |
| Freeze TRAIN TLE and environment | V0.22 `run`: `_frozen_archive`, `assert_ephemeris_matches_record`, `_make_environment`, `_evaluation_rngs` | Run once per declared world and persist the ephemeris receipt; no old V0.22 worlds. |
| Capture native Q1/Q2 anchor | V0.22 `_q12_anchor`: `encode_ee_axis_state`, `_q1_values`, `snapshot_ops3_anchor`, `project_ops3_anchor`, `build_ops3_live_surfaces`, `_q2_values` | Materialise `DetachedQ12Snapshot` with authenticated state/event/model digests and preserve the native keyed-observation provenance. |
| Enumerate all outcome-blind pairs/controls | V0.23 `capture_lcsrs_c3_predecision`, `enumerate_lcsrs_c3_anchor`, `enumerate_lcsrs_c3_world`, `enumerate_lcsrs_c3_schedule` | Serialize all 9 noninitial anchors, exclusions, S/R/C class counts, no-close controls, and pre-profile retention decisions. |
| Build deployable C3View | V0.23 `capture_lcsrs_c3_predecision` / `encode_lcsrs_c3_view` | Persist the exact Interface-A schema and verify no post-outcome fields are passed. |
| Evaluate matched profiles | V0.22 `StepEnvironment.evaluate_actions`, `_evaluation_record`; keyed field `KeyedFadingField.from_components` | Add draw-indexed common-field derivation, evaluate 00/10/01/11 completely before formula aggregation, and record mutation/RNG/field receipts. |
| Compute and bind labels | V0.23 `build_lcsrs_topology_teacher`, `build_lcsrs_two_user_teacher`, `bind_lcsrs_c3_anchor` | Convert every teacher/surface/record to durable shard artifacts and independently recomputable hashes. |
| Emit one atomic source receipt | Runner `write_source_shard` | Fill the receipt with complete physical records, topology, teacher, surface, C1/C2 diagnostics, and provenance rather than a digest-only adapter summary. |

The source adapter protocol is intentionally explicit and is bound by
`run_v023_lcsrs_source_server.py`; no silent fallback or first-qualified-pair
selection remains.  Physical execution is reserved for the Ubuntu server.

## B. 48 fold × seed × arm fit/evaluation shards

| required operation | existing reusable implementation | adapter work still required |
|---|---|---|
| Read complete source panel | `v023_lcsrs_fit_adapter.load_v023_source_panel`; typed `load_v023_world_source_artifact` | **Implemented (non-heavy):** authenticate the exact eight source-manifest children and reconstruct every retained `LCSRSAnchorRecord`; reject path, byte-hash, JSON/NPZ, schema, identity, and placebo-count drift. |
| Build matched placebo | V0.23 `build_lcsrs_matched_placebo` through `prepare_lcsrs_loo_fold` | **Implemented (non-heavy boundary):** build one fold-local frozen permutation, enforce >=80% coverage, and persist the complete mapping/strata receipt; no held-out target enters it. |
| Fit INFORMED / MATCHED_PLACEBO | V0.23 `fit_lcsrs_loo_arm` (default), injectable audited fit seam for tests | **Implemented (execution seam):** enforce exact 2,000-update receipt, one declared seed, source-anchor/target digest binding, initial/final model hashes, no early/best selection, and atomic numeric model/metrics sidecars. Real updates remain server-only and unrun. |
| Held-out inference | `evaluate_lcsrs_heldout_rows`; C3 head `forward_view` | **Implemented (non-heavy boundary):** adapter evaluates unchanged true held-out SUPPORTED rows itself and persists fixed-width identities, predictions, targets, sign/Spearman denominators, and hashes. Full-roster composition remains an independent verifier gap. |
| Compose and measure | V0.23 three-route methods plus native `StepEnvironment.evaluate_actions` | Compute teacher oracle, informed, placebo, zero-surface diagnostics, topology consistency, service and EE cross-product predicates without post-selection repair. |
| Resume independently | Runner `FitShardSpec`, `write_fit_shard`, source-manifest hash | The worker must consume `source-manifest.json`; it may not infer a source hash retroactively from a future merge. |

The runner's fit seam is now live through the explicit server entrypoint
`run_v023_lcsrs_fit_server.py` and `V023LearnerAdapter`; the safe CLI remains
plan-only.  Its W-196 synthetic tests exercise source loading, LOO isolation,
receipt sealing, atomic numeric sidecars, tamper rejection, and the fit branch
without performing an optimizer update.  No scientific outcome is claimed.

## C. Independent scientific recomputation

| required operation | existing reusable implementation | adapter/verifier gap |
|---|---|---|
| Recompute 00/10/01/11 totals and formula identity | V0.22 `_evaluation_record`; V0.22/V0.23 `build_coalition_residual_c3` | A separate verifier must recompute from raw profile receipts, not trust booleans or aggregate hashes. |
| Recompute Interface-A leakage and topology | V0.23 state/encoder/topology `verify()` methods and deterministic topology enumerator | A verifier fixture must independently perturb RNG/raw SINR, action slots, token order and geometry, then check Sections 3/17.1. |
| Recompute learner/placebo predicates | V0.23 learner/placebo modules; `v023_lcsrs_fit_adapter.verify_v023_fit_sidecars` | Fit-side re-opening of model/metrics/loss/placebo sidecars and hash bindings is **implemented and non-heavy**; an independent gate verifier still must reopen all 48 receipts, recompute held-out metrics/world-seed denominators, and evaluate composition predicates. |
| Emit one hard token | Frozen contract Section 14 | Add a complete verifier that emits `INVALID_RUN` before any scientific token and never promotes scaffold status to efficacy. |

## D. Current gate state

All implementation gaps named above are closed by the source server, typed
source artifact, learner adapter, composition server/runtime, scientific and
fit-independent verifiers, final verifier, and full Ubuntu-server launcher.
The manifest binds their current bytes, and the W190--W202 focused suite is the
non-heavy launch-readiness check.

What remains open is empirical rather than architectural: run the frozen
8-source/48-fit/48-composition TRAIN-development gate on Ubuntu and accept only
the final verifier's literal C3 and C1/C2-context tokens.  Until that run
completes there is no efficacy claim and no authorization for episode-policy
training.
