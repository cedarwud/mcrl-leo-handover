# V0.23 non-heavy composition-adapter implementation worker

Compute class: **non-heavy implementation/test-only**. Work in the current
environment. Do not run a real simulator, TLE world, learner fit, matched
physical pilot, episode training, or TEST split.

Repository: `/home/u24/papers/mcrl-leo-handover`

## Goal

Implement the missing V0.23 LC-SRS held-out full-roster composition seam so a
future Ubuntu-server gate can, after each fold model is fitted, replay the
authenticated Q1+Q2 anchor, evaluate Q3 once, take exactly one native masked
argmax of Q1+Q2+Q3, and measure the selected action physically without any
second decision, repair, coordinator, or policy rollout.

This worker must create code and deterministic fake-based tests only. No
scientific outcome may be opened.

## Read first

1. `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`, especially Sections 0, 3.4, 8, 10--14, 17.1, 18.
2. `docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md`.
3. `.scratch/multi-catfish-v023-c3-observability/ADAPTER-GAP-MAP.md`.
4. `.scratch/multi-catfish-v023-c3-observability/SOURCE-ARTIFACT-SCHEMA.md`.
5. `.scratch/multi-catfish-v023-c3-observability/v023_lcsrs_source_adapter.py`.
6. `.scratch/multi-catfish-v023-c3-observability/v023_lcsrs_fit_adapter.py`.
7. `.scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_observability_gate.py`.
8. `src/mcrl/algorithms/ee_axis_lcsrs_three_route.py`.
9. `src/mcrl/runtime/ee_axis_lcsrs_c3_gate_metrics.py` and
   `src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py`.
10. Relevant W182--W196 tests.

## Exclusive write ownership

You may create/edit only:

- `.scratch/multi-catfish-v023-c3-observability/v023_lcsrs_composition_adapter.py`
- `.scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_composition_server.py`
- `tests/test_w197_ee_axis_lcsrs_composition_adapter.py`
- `.scratch/multi-catfish-v023-c3-observability/V023-COMPOSITION-ADAPTER-NOTE.md`

Do not edit source adapter, fit adapter, runner, verifier, preflight manifest,
shared docs, or any other file. The root controller will integrate later.

## Required design

Build a deep, typed adapter with explicit injectable seams. Production may
reuse the authenticated source-replay/runtime helpers, but tests must use
small immutable fakes and must never construct a real environment.

At minimum support these four surfaces:

1. **Reopen/authenticate held-out source and fit artifacts**
   - exact declared world/seed/arm; source-manifest/preflight hashes;
   - fit model bytes and fit-side receipt verification;
   - no pickle/object dtype, unsafe paths, or overwrite.

2. **Replay and bind each held-out anchor**
   - injected production callback replays the frozen Q1+Q2 source trajectory;
   - callback returns an immutable anchor handle plus freshly reconstructed
     Interface-A/C3View and Q1/Q2 surface;
   - require world/phase/anchor/predecision/state/event/Q1/Q2/reference-action
     digests to equal the source artifact before Q3 or physical evaluation;
   - never infer or silently substitute a different anchor.

3. **Literal one-pass selection and measurement**
   - load one fitted Q3 model and evaluate it exactly once on the bound C3View;
   - select the lowest native action index only on an exact score tie from
     native safe mask over Q1+Q2+Q3;
   - separately construct ZERO-SURFACE B=Q1+Q2 and privileged TEACHER-ORACLE
     diagnostics; teacher labels never enter the learned inference input;
   - use an injected physical evaluator to evaluate complete selected vectors
     on the frozen matched draw panel and return raw per-user bits, energy,
     service, active beams/satellites/power, action hash, common-field and
     nonmutation receipts;
   - no second argmax, retry, fallback, matching, repair, or action editing.

4. **Persist independently recomputable numeric sidecars**
   - one write-once canonical JSON index and numeric NPZ per
     held-out-world/seed/arm, with SHA-256 file and per-array dtype/shape/C-byte
     digest metadata;
   - retain all anchors and draws, baseline/informed/placebo selections,
     pair-local class (00/10/01/11/OTHER), full-roster collateral actions,
     topology measurement (including selected-11 denominator), raw total and
     per-user bits, energy, served flags, active-beam counts, and every
     direction/service denominator required by Sections 10--12;
   - do not emit a scientific decision. `test_split_opened=false`,
     `episode_training=false`; fitting is already completed upstream and this
     stage must not perform additional optimizer updates.

The adapter should be able to produce the exact raw evidence from which a
separate verifier can recompute:

- ratio-of-sums EE by world/seed/arm using cross products;
- service noninferiority against B;
- action_change, literal_11, harmful_partial, OTHER, selected-11 topology
  consistency and collateral-action denominators;
- teacher-oracle vs B and informed vs B composition directions;
- all tie counts and missing/NA denominators.

Do not trust or persist only summary booleans. Preserve raw arrays.

If a contract detail cannot be implemented without changing an upstream
schema, fail closed and document the exact missing field in the note; do not
invent an interpretation.

## Tests

Use TDD/fake fixtures and test at least:

- exact one Q3 call and one argmax;
- exact-tie lowest-index behavior and illegal masking;
- no post-selection mutation/repair;
- source/fit/hash/identity mismatch rejection;
- teacher data cannot enter learned input;
- all pair classes including OTHER retained;
- topology consistency denominator zero -> explicit NA/false-ready receipt;
- write-once and tamper rejection;
- object dtype rejected and `allow_pickle=False`;
- closed TEST/episode flags;
- no real environment or optimizer invoked.

Run focused tests with `.venv/bin/python -m pytest -q`. Report changed files,
test command/result, exact unresolved upstream gaps, and stop. Do not launch
anything heavy.
