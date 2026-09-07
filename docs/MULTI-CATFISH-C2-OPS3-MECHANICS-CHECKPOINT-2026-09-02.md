# Multi-Catfish C2 OPS-3 mechanics checkpoint

Date: 2026-09-02  
Recorded at: 2026-09-02T20:09:31+08:00  
Status: `MECHANICS_GATE_COMPLETE__PAUSED_FOR_CROSS_SESSION_MERGE`  
Outcome status: `NO_OUTCOME_OPENING__NO_LEARNER__NO_TRAINING`

## Scope and claim ceiling

This checkpoint closes only the bounded formula and live TLE/D2 adapter
mechanics for the provisional OPS-3 C2 candidate. It establishes that the
implemented projection follows the frozen mechanics contract and is safe to
hand to a later adjudication step. It does **not** establish that C2 improves
energy efficiency, that Q2 is learnable, or that the three-Catfish system is
ready for an episode run.

Per the controller instruction, work pauses here until the independently
running Fable session is merged and adjudicated. The 12-episode oracle screen,
the 36-episode expansion, learner construction, and 500/1500/3000/9000-episode
runs remain unopened.

## Implemented boundary

The live path is split into three explicit operations:

1. `snapshot_ops3_anchor(environment, observation)` detaches a predecision
   anchor and the native D2/TLE state without consuming RNG or advancing live
   state.
2. `project_ops3_anchor(anchor)` advances only a cloned D2 tracker and a
   detached tracked TLE set on the native measurement clock.
3. `build_ops3_live_surfaces(anchor, projection, reference_actions)` verifies
   the projection receipt and applies the pure OPS-3 formula to each native
   28-action surface.

The projection preserves current physical `(NORAD, cell)` action identities,
uses the frozen-user and frozen-served-background convention, and delegates
target, recurrence-power, network-power, persistence, gauge, and feature
equations to the pure formula module.

## Defects found and corrected in this stage

1. A decimal `30.08` literal differed by one ULP from the simulator's actual
   `47 * 0.64` decision clock. `OPS3_INTERVAL_S` now imports canonical
   `DECISION_STEP_S`; both are exactly
   `0x1.e147ae147ae15p+4`.
2. Terminal `H_t=0` previously required an otherwise-unused positive segment
   start gain. The terminal path now consumes no projection/recurrence input
   and emits a complete all-zero surface.
3. The live adapter previously accepted a non-native clock factorization such
   as `94 * 0.32 s` when its product happened to equal the decision interval.
   It now exact-locks both native components: 47 D2 substeps and 0.640 seconds
   per substep, as well as their product.
4. A real-TLE regression now explicitly witnesses that distinct physical cell
   identities are not collapsed into one projected gain geometry.

## Verification evidence

Command:

```text
.venv/bin/pytest -q tests/test_w129_ee_axis_ops3.py tests/test_w130_ee_axis_ops3_live.py
```

Result: `29 passed` (`18` pure-formula cases and `11` live-adapter cases).

The live cases exercise real TLE data and cover native D2 indices, three future
decision blocks, action identity preservation, deterministic repeatability,
live environment/driver/tracker/RNG non-mutation, exact reference zero, native
mask safety, frozen background sourcing, `_previous_demand` exclusion,
terminal no-propagation behavior, native-clock rejection, distinct-cell
geometry, finite legal rows, and zero-filled illegal rows.

Command:

```text
.venv/bin/pytest -q tests/test_scenario_driver.py tests/test_w02_tle.py \
  tests/test_w17_step_environment.py tests/test_w17_interference.py \
  tests/test_w38_keyed_fading.py tests/test_w32_counterfactual_step.py
```

Result: all `92` collected nearby canonical-physics tests passed.

Command:

```text
.venv/bin/python -m py_compile \
  src/mcrl/runtime/ee_axis_ops3.py \
  src/mcrl/runtime/ee_axis_ops3_live.py \
  tests/test_w129_ee_axis_ops3.py \
  tests/test_w130_ee_axis_ops3_live.py
```

Result: passed.

## Frozen file receipts

```text
87366170c43ecd5f1154b2fdde635fabc45afe190fc53f2119196e5d877d66c7  src/mcrl/runtime/ee_axis_ops3.py
8d7b32ae5587e86ab9c28afe06d2ab1e36d2616b6ce1f874e1d8414255f543d2  src/mcrl/runtime/ee_axis_ops3_live.py
7753e86e918ca810d39f6f709374d922a1efbae4f5cf701cd56294725314f427  tests/test_w129_ee_axis_ops3.py
c42417e3d8ab3aca94fc23b2c815ea8ced192eaa23f8c07753fbe0060433d2af  tests/test_w130_ee_axis_ops3_live.py
e2606d74860170d7eb71ea4494f418102e35c5ec912ecd7b48eec23ef0caacf5  docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md
```

## Required cross-session merge adjudication

Before any outcome is opened, compare the independent Fable result against
this provisional OPS-3 contract and implementation. The merge must explicitly
decide:

1. retain OPS-3, replace it, or run a fixed same-protocol comparison of no more
   than two predeclared candidates;
2. whether projected persistence is conditional on successful service of the
   opening action at `h=0`. The current frozen formula initializes persistence
   on the current native legal mask and begins physical feasibility at `h=1`;
   changing that is a formula decision, not an adapter repair;
3. whether constructor-level receipt hardening is needed before an oracle
   runner, without treating that hardening as efficacy evidence.

No formula, coefficient, sign, horizon, seed, or outcome rule may be changed
after opening the declared worlds.
