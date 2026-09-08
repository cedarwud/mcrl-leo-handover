# Codex Sol Track-B iteration-2 lever-matrix implementation report

## Outcome

Implemented the declared parallel matrix `L1→L12→L2→L4` without running heavy
physics. The B-r2 4-world × 3-fixed-carrier × 10-anchor TRAIN panel is shared
by every lever. The finite-demand runner and receipts remain intact.

The package provides detached per-lever modules, a priority registry, explicit
r2 reuse/regeneration policy, a byte-identical no-lever seam, exact C1/OPS-3
C2/LC-SRS C3 target composition, literal DROP arms, privileged/nominal set
decoders, exact E1 U1/J1 solvers/certificates, immutable receipts, and Astra's
global/four-world/carrier/mechanism failure-analysis block.

L1/L12 register heavy replay hooks that preserve keyed fading event `physics`
and original-physics-only continuation. They refuse scalar r2 reinterpretation.
L2 reprices every active beam from stored RF/physical rows. L4 adds one
authenticated current-event ledger from physical `(NORAD,cell)` transitions.
No lever mutates the source tapes.

## Verification

Exact synthetic-only test CLI:

```bash
cd /home/sat/mcrl-v024-codex-iter2
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -o addopts='' -q .scratch/multi-catfish-v024-regime-b/probe/test_lever_matrix_probe.py .scratch/multi-catfish-v024-regime-b/probe/test_run_v024_regime_probe.py .scratch/multi-catfish-v024-regime-b/probe/test_iteration2_probe.py
```

Pytest summary line:

```text
41 passed in 1.05s
```

`git diff --check` also passed. A temporary preflight and exact per-lever
authority were built and validated; an authorized L1 unit stopped as
`REGEN_REQUIRED` without synthesizing a tape or opening TEST. L2 correctly
refused at its source-verification TODO.

The repository-wide suite is not green independently of this scratch-package
change: `pytest -x -vv` stopped at
`tests/test_g6_forbidden_list.py::test_no_new_module_mentions_a_forbidden_term`
after 39 passes and one skip because numerous pre-existing `src/` modules use
its forbidden vocabulary. No `src/` file is part of this implementation.

## Estimate

Exact CLI:

```bash
cd /home/sat/mcrl-v024-codex-iter2
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --estimate
```

Exact output:

```json
{
  "levers": {
    "L1": {
      "controller_todos": [],
      "execution_ready": false,
      "identity": "B2_L1_RATE_TARGET_SUM_POWER",
      "r2_raw_tapes_reused": false,
      "r2_tape_policy": "REGENERATE_PHYSICS_KEEP_TAPE_AS_PROVENANCE_CONTROL",
      "regeneration_hook": "levers.lever_l1_sum_power.regeneration_hook",
      "supplementary_acquisition_required": true,
      "unit_status": "REGEN_REQUIRED"
    },
    "L12": {
      "controller_todos": [
        "L2_VERIFY_GAIN_PAE_AND_BIAS_FLOOR_SOURCE",
        "L2_VERIFY_LOW_POWER_TEMPERATURE_20GHZ_BEAM_MAPPING_AND_MULTICARRIER_APPLICABILITY"
      ],
      "execution_ready": false,
      "identity": "B2_L12_RATE_TARGET_DEVICE_PA",
      "r2_raw_tapes_reused": false,
      "r2_tape_policy": "REGENERATE_L1_RF_THEN_APPLY_L2_PA",
      "regeneration_hook": "levers.lever_l12.regeneration_hook",
      "supplementary_acquisition_required": true,
      "unit_status": "REGEN_REQUIRED"
    },
    "L2": {
      "controller_todos": [
        "L2_VERIFY_GAIN_PAE_AND_BIAS_FLOOR_SOURCE",
        "L2_VERIFY_LOW_POWER_TEMPERATURE_20GHZ_BEAM_MAPPING_AND_MULTICARRIER_APPLICABILITY"
      ],
      "execution_ready": false,
      "identity": "B2_L2_PIACIBELLO_SURROGATE",
      "r2_raw_tapes_reused": true,
      "r2_tape_policy": "REUSE_RF_RATE_ROWS_REPRICE_EACH_ACTIVE_BEAM",
      "regeneration_hook": "levers.lever_l2_pa_curve.regeneration_hook",
      "supplementary_acquisition_required": true,
      "unit_status": "TODO_CONTROLLER_DECLARE"
    },
    "L4": {
      "controller_todos": [
        "L4_VERIFY_INCREMENTAL_RESOURCE_BOUNDARY_AND_EVENT_APPLICABILITY",
        "L4_VERIFY_SUBSYSTEM_EVENT_ENERGY_MEASUREMENTS"
      ],
      "execution_ready": false,
      "identity": "B2_L4_CONTROL_EVENT_ENERGY_PROXY",
      "r2_raw_tapes_reused": true,
      "r2_tape_policy": "REUSE_PAYLOAD_ROWS_ADD_AUTHENTICATED_EVENT_LEDGER",
      "regeneration_hook": "levers.lever_l4_handover_energy.regeneration_hook",
      "supplementary_acquisition_required": true,
      "unit_status": "TODO_CONTROLLER_DECLARE"
    }
  },
  "maximum_parallel_single_thread_workers": 2,
  "panel": {
    "anchors_per_lever": 120,
    "carriers": 3,
    "units_per_lever": 12,
    "worlds": 4
  },
  "priority": [
    "L1",
    "L12",
    "L2",
    "L4"
  ],
  "r2_tape_digests": {
    "world-1341435503386059806-nearest-eligible": "ff1bf2160046605c7bcd22ad48514331a93c6607fc93bd43b178916de53133ca",
    "world-1341435503386059806-random-masked": "ab88fbb9b4685786902c9be7f4e977013991b8db54baf62f0bedfdb7c38c35ce",
    "world-1341435503386059806-stay-if-possible": "6f9f01672a5f2713758e6d5013f40a5001f9fa563b6eed911b3a5910e4c856c1",
    "world-3226893802015760720-nearest-eligible": "7d6e24a702cb64aa899c255c4e5ec6494fa331637986d56db98f6f1e06ee5d0a",
    "world-3226893802015760720-random-masked": "28be1bfb43c6a0925f5830fd855d8f94c5d9a1152264d27832720b864eaceb0f",
    "world-3226893802015760720-stay-if-possible": "9a5dcd7f726cb05412f2ae6f5995d5645e9b44eadc9e46d2a84e4707576c76bd",
    "world-5683200792433982503-nearest-eligible": "12ddf2328d478897ead7bfaddfc9d63769ffd2301f4520646ef65cd2223dfdf5",
    "world-5683200792433982503-random-masked": "8893126c7a33e0d4a8489530bc4babf6ee5e424b6c1c3a5cb9437e1fd538d758",
    "world-5683200792433982503-stay-if-possible": "39043c4cfb4f6865194fbb05a3f309aa9d17846769d23fd156b912073fa47940",
    "world-7374843801585642838-nearest-eligible": "6877b1505fc2836906eb59d6ae68498f641f40c1ad844350b42438187ad0e1b4",
    "world-7374843801585642838-random-masked": "668382495b4fc3a8c2b8a745f1b228cae11f0017df27cebc5352d2edf38f96cf",
    "world-7374843801585642838-stay-if-possible": "5e4cda56e7a0c2af41c3928a6c255f0ce647cf1028630cd4464e251f8bc8b117"
  },
  "schema": "multi-catfish-mcrl-v024-trackb-lever-matrix-v1-estimate"
}
```

## Exact launch CLIs

First build the common preflight (controller supplies the actual exposure time):

```bash
cd /home/sat/mcrl-v024-codex-iter2
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_preflight.py --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --reviewer controller
```

Per-lever unit authority and unit launch, using the first declared unit as the
exact example (repeat for all 12 units; no more than two processes):

```bash
# L1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L1-5683200792433982503-nearest-eligible.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L1 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L1-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L1 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L1-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1

# L12 (after its TODO declarations are resolved)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L12-5683200792433982503-nearest-eligible.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L12 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L12-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L12 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L12-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1

# L2 (after its TODO declarations are resolved)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L2-5683200792433982503-nearest-eligible.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L2 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L2-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L2 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L2-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1

# L4 (after its TODO declarations are resolved)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L4-5683200792433982503-nearest-eligible.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L4 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L4-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L4 --unit 5683200792433982503:nearest-eligible --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L4-5683200792433982503-nearest-eligible.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
```

Exact per-lever merge authority and launch commands:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L1-MERGE.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L1 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L1-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L1 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L1-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L12-MERGE.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L12 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L12-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L12 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L12-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L2-MERGE.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L2 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L2-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L2 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L2-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_lever_matrix_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --output-root /home/sat/mcrl-v024-lever-matrix-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L4-MERGE.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --lever L4 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L4-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L4 --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-AUTHORITY-L4-MERGE.json --output /home/sat/mcrl-v024-lever-matrix-20260908-r1
```

Each merge authority must first be built with the authority builder and the
identical runner arguments shown above. Dry-run example:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py --lever L1 --merge --dry-run --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-LEVER-MATRIX-PREFLIGHT.json
```

## Open items and honest status

- `L1`, `L12`: `REGEN_REQUIRED`. The server executor must install the registered
  replay/acquisition adapter and regenerate RF/interference/rates/energy,
  OPS-3, LC-SRS pairs and composed profiles. No scalar tape was fabricated.
- `L2`, `L12`: `TODO_CONTROLLER_DECLARE` for gain/PAE and bias source checks,
  omitted currents, low-power/temperature/20 GHz interpolation,
  amplifier-to-beam mapping, and CW/multicarrier applicability.
- `L4`: `TODO_CONTROLLER_DECLARE` for the incremental resource boundary,
  event applicability, and actual subsystem measurements.
- `L2`, `L4`: authenticated supplementary OPS-3/LC-SRS/composed/event inputs
  remain required even though r2 RF/rate rows are reusable.
- Controller must seal the declaration, supply actual exposure timestamp and
  known Track A result hashes/access times, then build the common preflight and
  separate authority for each unit/merge.
- No matrix outcome, `NO_SUPPORT`, selected lever, or efficacy claim exists.
