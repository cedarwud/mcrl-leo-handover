# V025 engine stage 4i report — reporting arms and CH5 sweep driver (2026-09-09)

Status: **IMPLEMENTED AND VERIFIED; FORMAL SWEEPS NOT OPENED**.

The sealed CH5 specification was implemented without changing a scientific score, guard, deadline, fallback, endpoint, certificate, or admission predicate. The existing stage-4h unit/calibration/world-manifest schemas remain authoritative so the sealed tapes and calibration can be reused.

## Reporting arms

`ONLY_C1` and `ONLY_C1C2` are now oracle set arms. They share the complete bounded catalogue, served-count guard, ten-second whole-path deadline, atomic BASE fallback, four-worker evaluation path, M=48 top pruning, and realised 48-boundary committed endpoint with `FULL` and the `DROP_*` arms.

- `ONLY_C1`: primary key C1_m; deterministic configuration ID breaks a C1 tie. C2 and C3 are absent from both ranking and top-M pruning.
- `ONLY_C1C2`: primary key C1_m; C2 is the secondary tie-break. C3 is absent from both ranking and top-M pruning.
- `FULL` and `DROP_*` retain their sealed v1.9 keys unchanged.

The reporting arms are absent from `MARGINALS`, the uncertainty contrasts, the scientific certificate builder, and `training_admission`. The conformance receipt explicitly records `reporting_arms_enter_certificates=false` and `reporting_arms_enter_admission=false`. A test supplies adversarial reporting-arm values to the admission function and proves byte-for-byte equal output with those values absent.

## Sweep driver

`run_v025_matrix_probe.py --sweep {A,B,E,F}` now binds and produces the specified panels:

| panel | sealed x-values | source |
|---|---|---|
| A | 25, 50, 100 Mbit/s | R7, a-r0, R1 |
| B | 0.1, 0.338, 1.0 W/active chain | R4, a-r0, R3 |
| E | a-r0, a′-r0, a-γ0, b0 | matrix settings |
| F | 0, 0.5, 1.0, 1.5, 2.0 degrees | quarantined fixed-occupancy 48-boundary fixture |

Every real-physics unit receipt embeds a sweep identity over panel, x-axis, x-value, run setting, world domain/digest, and catalogue digest. The pooled point identity additionally binds the ordered unit-identity digests. The driver caches each sealed world tape by digest across x-values and runs every arm on one shared catalogue within each anchor.

The primary figure curves are emitted in fixed order: `BASELINE`, `ONLY_C1`, `ONLY_C1C2`, `FULL`, `S_UNI`. `BASELINE` is the existing carrier-proposal `NULL` arm. The companion output adds `DROP_C1`, `DROP_C2`, `DROP_C3`. This is **eight** named series: the specification says “seven curves” but explicitly names five plus three `DROP_*`; the implementation follows the complete named set without dropping one. Panel F's sealed single-member fixed-occupancy catalogue makes all arm curves coincide; the receipt states this rather than inventing an arm distinction.

Panels A/B/E require the existing immutable `--calibration` and `--world-manifest` plus the provider import. Panel F is self-contained and executes the already sealed controlled fixture. All outputs remain TRAIN-only and carry `enters_certificate=false`, `enters_admission=false`.

## Pre-formal cost report

No formal or claim-panel outcome was opened. The measurement used panel A at 50 Mbit/s on `V025_SMOKE/world/1`, one real anchor, all 16 engine arms, four declared workers, the sealed one-boundary/M=48 selection path, and a realised 48-boundary endpoint.

Measured:

- provider construction: **16.295915 s** for the four-step quarantined tape;
- one 16-arm anchor: **17.608035 s**;
- physical boundary evaluations: **5,134**;
- quarantined world digest: `1402cc8a6aa368397abb212d8de49f4325e0db9606c61fffa050e4f80cd583dd`.

Projection assumptions: four workers per real unit; process concurrency 20 gives five concurrent units; A/B/E use four worlds and 90 anchors/world/x; their four world tapes are built once and reused across x-values. F uses five one-anchor controlled points. “Ideal wall” divides aggregate core cost by 20; the conservative wave bound preserves whole four-worker units.

| panel | x-values | units | anchors | projected core-hours | ideal wall @20 | whole-unit wave bound |
|---|---:|---:|---:|---:|---:|---:|
| A | 3 | 12 | 1,080 | **21.148** | **63.44 min** | **80.05 min** |
| B | 3 | 12 | 1,080 | **21.148** | **63.44 min** | **80.05 min** |
| E | 4 | 16 | 1,440 | **28.191** | **84.57 min** | **106.73 min** |
| F | 5 | 5 | 5 | **0.098** | **0.29 min** | **0.57 min** |

The sum for A+B+E+F is **70.585 core-hours** under this direct projection. These are capacity projections from one quarantined anchor, not completed formal run times.

Evidence:

- `.tmp/stage4i-cost/panel-A-x50-quarantined-unit-r2.json`, file SHA-256 `e14de344bff619fe336ba5da4c15726fed6af2d9de0efbbe994274a5dcf3ca7a`;
- `.tmp/stage4i-cost/panel-cost-projection-r2.json`, file SHA-256 `706fc0ecf3c0e67c99c10b8a6904205e5483c84959e4a040bed4a20ba2f67290`, embedded receipt `ba7f7eeb3bbd94244da5166f2ed4168f4a8d72d693e4d4f9c34f9cfa34c59d7f`.

## Verification

- `python -m py_compile .../run_v025_matrix_probe.py`: PASS.
- Stage-4i plus stage-4h focused tests: **10 passed**.
- Full `tests/physics_v025`: **182 passed**.
- Real tiny-provider dry run: PASS with all 16 arms.
- `--sweep F` execution smoke: PASS; five immutable x-point receipts plus panel receipt, all with distinct panel/x identities.

Modified implementation: `.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py` (SHA-256 `24cbe237f01be798289746b48837e0a54a579a913b369a8cdf5fb17573f1422a`). Focused tests: `tests/physics_v025/test_stage4i_reporting_sweeps.py` plus the extended stage-4h arm-key test.
