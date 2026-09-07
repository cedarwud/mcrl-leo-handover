# V0.23 composition runtime implementation note

Date: 2026-09-05

## Implemented boundary

`v023_lcsrs_composition_runtime.py` now exposes the production
`build_runtime(*, spec, adapter)` factory required by
`run_v023_lcsrs_composition_server.py`.  The returned object exposes exactly
`replay_anchor(request)` and `evaluate_physical(request)`.

The module import is inert.  It imports neither `mcrl` nor the V0.23 source
adapter, opens no TLE data, constructs no simulator, and loads no model.  The
production backend is opened lazily by the first replay callback.

The replay callback:

- requires the frozen world, student seed, arm, preflight, source manifest,
  source index, and fit receipt identities; derives an omitted contract digest
  from the authenticated adapter and omitted model digests from an independent
  fit authentication, while strictly cross-checking any supplied values;
- authenticates the canonical source manifest and the exact held-out source
  index before opening the world;
- derives only the frozen preregistration and TLE paths declared by the
  preflight manifest;
- delegates inherited V0.20/V0.18/V0.15/V0.14 and Q1+Q2 authority checking to
  the source adapter's existing fail-closed authentication;
- reconstructs the world field and follows only the frozen Q1+Q2 masked
  background trajectory from `t=0`;
- computes Q1/Q2 inference from deployable state/features without calling the
  repriced target builder or reading teacher/target/profile outcomes;
- captures each exact `t=1..9` predecision once and binds every typed replay
  request digest to both the authenticated source declaration and the fresh
  capture; and
- rejects mutable or teacher/target-bearing C3 views.

The physical callback:

- accepts the three roles only in the exact order `ZERO_SURFACE_B`, the
  declared learned arm, `TEACHER_ORACLE`;
- checks the opaque handle plus world/phase/anchor, full-roster action vector,
  legality, draw vector, and action digest;
- invokes `evaluate_actions` exactly once for each draw `0..31` with one field
  keyed only by the frozen family, world, anchor, and draw;
- restores the original field in `finally` and checks environment, RNG, Q1,
  Q2, declared Q3 identity, matched field, and action bytes before accepting a
  draw;
- pads and returns the complete typed per-user, served, energy, active-beam,
  active-satellite, beam-power, action, common-field, and named nonmutation
  arrays; and
- poisons the runtime after any mismatch or partial callback, preventing a
  retry from turning a partial pass into accepted evidence.

There is no TEST access, optimizer, learner update, episode training,
coordinator, repair, second decision, or action-editing path in this module.

## Focused verification

The non-heavy synthetic/monkeypatched W-200 tests cover inert import, lazy
factory behavior, every `ReplayAnchorRequest` identity/digest, immutable and
target-free replay, unique one-pass handles, strict role/phase sequencing,
exact 32-draw invocation, production field-call arguments, unchanged complete
actions, full output arrays and padding, common fields across roles, all six
named mutation guards, target/tamper rejection, and required model/contract
bindings.

Commands run:

```text
pytest -q tests/test_w200_ee_axis_lcsrs_composition_runtime.py
33 passed

pytest -q tests/test_w200_ee_axis_lcsrs_composition_runtime.py tests/test_w197_ee_axis_lcsrs_composition_adapter.py
52 passed, 1 skipped
```

The skip is the pre-existing optional W-197 Torch availability case;
the W-200 runtime suite itself has no skips.

No production simulator rollout was run.

## Exact remaining blockers and authority limitations

### 1. The physical callback cannot independently observe the live fitted Q3 object

`PhysicalEvaluationRequest` contains only handle, world, phase, anchor, role,
actions, and draw index
(`v023_lcsrs_composition_adapter.py:1186-1215`).  The runtime factory receives
only `spec` and `adapter`
(`run_v023_lcsrs_composition_server.py:173-221`); the server-authenticated
`fitted` object is not passed to it.  Supplying an independently reconstructed
model would not prove that the callback observed the same object.

The safe implementation independently authenticates the fit identity and
places that authenticated logical model digest in the required Q3 before/after
column (`v023_lcsrs_composition_runtime.py:810-859,1142-1161`).  It does not
claim that this independently reconstructed fit is the same live object held
by the server.  The composition adapter does observe the actual object: it
hashes it before and after the sole Q3 inference
(`v023_lcsrs_composition_adapter.py:1130-1156`) and again after all physical
callbacks (`v023_lcsrs_composition_adapter.py:1545-1552`).  Independent Q3
observation inside the physical callback would require the server/factory or
`PhysicalEvaluationRequest` API to carry the authenticated fitted object (or a
typed digest callback over that exact object).

### 2. The new callback module is not part of the frozen preflight byte closure

The current preflight's required roles and exact paths end at the existing
runtime/source/learner closure
(`preflight_v023_lcsrs_observability.py:238-327`).  They do not name this new
runtime module.  The server loads the operator-supplied runtime path
(`run_v023_lcsrs_composition_server.py:206-221`), but no runtime-module digest
exists in `CompositionServerSpec` (`run_v023_lcsrs_composition_server.py:40-59`).

Consequently, this implementation can fail closed on all identities it is
given, but a scientifically frozen production launch still needs a separately
authorized preflight/server update that binds these callback bytes.  That
update is outside the three-path ownership granted for this task.

### 3. The current preflight and source-adapter bytes disagree

At the final local check in this task, the preflight declared the
`runtime_source_adapter` SHA-256 as:

```text
2c1c9f7ace6b9a9159937c943eedc991ea77e6ba92d2bc69321fdc216f5591f4
```

The current source-adapter bytes hashed to:

```text
d0f9edc576d1d8612e7af5cb6cefec5f339b62d7a4bdd2ef91ce9ff6475b78c4
```

The preflight validator compares every declared binding to current bytes and
rejects a mismatch (`preflight_v023_lcsrs_observability.py:220-235`), and the
source adapter explicitly requires its own live byte hash to equal that
binding (`v023_lcsrs_source_adapter.py:1618-1661`).  Thus a production replay
correctly fails before simulator construction until the source adapter and
preflight are re-frozen together by their owner.  This task did not modify
either file.

### 4. Physical override/snapshot operations are not typed public APIs

The simulator's public `evaluate_actions` is nonadvancing and internally
copies the RNG/restores segment state (`src/mcrl/env/step.py:643-722`), but it
has no typed keyed-field override or complete environment snapshot receipt.
The existing source adapter therefore swaps private `_fading_field` and uses
external live/RNG/network checks.  This runtime follows that frozen pattern and
adds `finally` restoration plus named before/after receipts.  A future public
`evaluate_actions(..., fading_field=...)` and typed state digest would remove
this private seam; inventing either locally would not be evidence-compatible.
