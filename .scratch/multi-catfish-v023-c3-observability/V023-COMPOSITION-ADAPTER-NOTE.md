# V0.23 composition adapter/server boundary note

Status: non-heavy implementation boundary only.  This worker opens no
simulator, TLE world, TEST split, learner fit, optimizer, episode, matched
pilot, or scientific decision.

## Server seam

`run_v023_lcsrs_composition_server.py` is deliberately inert on import.  A
deliberate command supplies one exact held-out world, student seed, learner arm,
source directory/manifest, preflight/source/fit/model hashes, fit receipt,
output path, device, and a runtime callback module/factory.  Only then does it
load the sibling composition adapter and callback module.

The adapter exposes production-safe source authentication, fit authentication,
the default Q3 evaluator, the model digestor, the typed composition engine, and
write-once JSON/NPZ persistence.  The runtime factory must return exactly named
`replay_anchor` and `evaluate_physical` callbacks.  The server supplies no
fallback selector, replay, physical evaluator, repair, coordinator, or action
editor.  Each returned declared anchor is replayed and composed in phase order;
the adapter owns all immutable identity, one-pass, mutation, and raw-evidence
checks.

The success line is an evidence receipt only:
`scientific_claim=false`, `decision=null`, `test_split_opened=false`, and
`episode_training=false`.  It is not a gate verdict.

## Upstream limitations and fail-closed status

1. `src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py:45-66` defines
   `_RECONSTRUCTION_ARRAYS` only for C3View/Q1/Q2/pair fitting inputs.  Although
   `SOURCE-ARTIFACT-SCHEMA.md:136-178` specifies raw pair-local draw arrays,
   `load_v023_world_source_artifact()` returns reconstructed records rather
   than those raw arrays.  This adapter bridges that API limitation by first
   requiring the typed loader to pass and then reopening the loader-authenticated
   NPZ itself with `allow_pickle=False`; it does not treat the reconstructed
   fit records as full-roster measurements.

2. `v023_lcsrs_fit_adapter.verify_v023_fit_sidecars()` reopens and verifies
   the model NPZ and reconstructs a typed network internally
   (`v023_lcsrs_fit_adapter.py:1176-1307`), but its public result is only a
   verification receipt (`:1365-1372`).  This adapter therefore calls that
   verifier and then independently reopens the bound model NPZ, rechecks every
   tensor receipt, and reconstructs the native network in eval mode.  The
   server does not deserialize model bytes or run an optimizer itself.

3. No upstream schema defines the replay callback’s immutable anchor handle or
   a complete full-roster physical evaluator receipt.  The gap map explicitly
   leaves compose/measure open (`ADAPTER-GAP-MAP.md:29-38`) and keeps the gate
   execution NO-GO (`:55-63`).  Missing world/phase/anchor/predecision/state/
   event/Q1/Q2/reference-action fields, action hashes, common-field receipts,
   nonmutation receipts, or raw per-user/energy/service/topology fields must
   reject the shard.

4. The source schema gives `nonmutation_flags` shape `(P*32,5)` but does not
   name the five columns.  The current source writer initially records
   `[live_state_unchanged, rng_unchanged, network_unchanged, field_restored,
   True]`, then rewrites columns 3--5 to literal `True` after its Q1/Q2 check.
   The composition adapter can authenticate and retain those exact five bytes,
   but cannot turn the unnamed/partly literal source flags into independently
   recomputable before/after receipts without an upstream schema change.  It
   therefore keeps them as `pair_source_nonmutation_flags` and does not assign
   stronger semantics.  By contrast, the injected full-roster physical result
   must supply named before/after digests for environment, RNG, Q1, Q2, Q3,
   and matched field; omission rejects the shard.

5. `v023_lcsrs_source_adapter.py:630-650` `_composition_record()` is not a
   valid shortcut: it consumes the privileged teacher target surface, performs
   another masked argmax for the reference, has no fitted Q3 model, and does no
   physical full-roster measurement.  It must not be used as composition
   evidence.

6. Existing source profile rows are pair-local 00/10/01/11
   (`SOURCE-ARTIFACT-SCHEMA.md:136-178`).  They cannot replace the required
   complete selected-vector full-roster measurements or collateral-action
   denominators.  Those values are accepted only from the typed injected
   `PhysicalEvaluation` seam and are persisted as raw arrays; a missing field
   rejects the shard rather than falling back to pair-local data.

7. The two fitted arms are separate immutable fit shards.  Consequently one
   composition file is keyed by `(held_out_world, student_seed, arm)` and
   carries B, that exact fitted arm, and TEACHER-ORACLE.  The separately keyed
   INFORMED and MATCHED-PLACEBO files must be joined by a future independent
   verifier; this worker does not invent a cross-arm aggregate schema or load a
   second model into one arm-keyed artifact.

The remaining live-integration blockers are therefore exact: no upstream
production callback yet implements `ReplayAnchorRequest -> ReplayedAnchor`,
and no upstream production callback yet implements
`PhysicalEvaluationRequest -> PhysicalEvaluation` with all 32 draw-level raw
arrays, native action hash, field digest, and nonmutation fields.  In addition,
the root controller still must join the separately keyed INFORMED/placebo
shards and provide the independent recomputation/manifest stage.  Until those
pieces exist and pass review, the server is only a fail-closed composition
entrypoint and the overall gate remains execution-NO-GO.

## Implemented evidence boundary

`v023_lcsrs_composition_adapter.py` now reuses the authenticated source-panel
loader, then independently reopens its NPZ with `allow_pickle=False` to recover
all raw 00/10/01/11 profiles.  It calls the fit-side verifier, independently
reopens the model NPZ without pickle, validates every tensor dtype/shape/digest,
reconstructs the native head in eval mode, and performs no optimizer update.

For every phase it binds a fresh replay receipt to source world, phase, anchor,
predecision, state schema/state, Q12 snapshot/model/source-state/event, C3View,
topology-content, Q1, Q2, mask, and reference actions before Q3.  It evaluates
Q3 once and performs one native learned masked argmax.  B uses the stored source
reference vector without another argmax; TEACHER-ORACLE has a separate
diagnostic argmax and no route into `Q3InferenceInput`.

The writer keeps complete selected vectors and all 32 physical draws for B,
the keyed learner arm, and TEACHER-ORACLE.  It also retains the source
`pair_target_by_draw`/mean, normalized and bit-scale Z3 rows, every 00/10/01/11
action/bits/link-rate/link-power/SINR/energy/G/system-power/fixed-power/service
profile, padded active-beam/satellite identities and beam powers, action and
common-field digests, ratio identities/directions/tolerances, and every raw
coalition-formula term.  Learned and teacher 00/10/01/11/OTHER classes,
topology, collateral actions, physical bits/energy/service/topology, exact
argmax ties, ratio ties, missing counts, and explicit denominators remain
separate arrays/receipts.  The canonical JSON, numeric NPZ, and NPZ digest file
are write-once and independently reopened before success.  A zero selected-11
topology denominator is serialized as explicit NA with
`predicate_ready=false` and `predicate=false`; no scientific decision is
emitted.

## Frozen claim ceiling

`TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`

The governing contract remains the frozen pre-outcome method contract and
execution NO-GO (`docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md:3-11`).
