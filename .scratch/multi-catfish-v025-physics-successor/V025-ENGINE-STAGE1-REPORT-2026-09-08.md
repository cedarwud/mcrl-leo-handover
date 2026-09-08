# V025 engine stage-1 report — 2026-09-08

## Disposition

Stages 1 and 1b are implemented. No outcome run, TEST split, target generation, source regeneration, learner update, calibration-world selection, or training was performed. Under the sealed v1.1 amendment the primary architecture is `V025-ANGLE-RATE-TPC-TDM-ACM` (`a-r`); rate-target FDM (`a′-r`) is its sensitivity, the original controllers are relabelled `a-γ`/`a′-γ`, and fixed RF (`b`) remains the declared reference. `ALL_NEUTRAL_CONTROL` is never renamed.

Commit status: uncommitted. The requested `git add`/commit was attempted, but this managed sandbox mounts `.git` read-only and rejected creation of `.git/index.lock`; the controller must commit the listed source, test, and report paths.

Targeted pytest summary:

```text
77 passed in 0.21s
```

Command (using the already-installed dependency environment because this checkout initially had no pytest environment and network installation was unavailable):

```text
PYTHONPATH=/home/sat/mcrl-v025-codex-ws-engine/src /home/sat/mcrl-leo-handover/.venv/bin/pytest -q tests/physics_v025
```

The repository-wide suite is not green before considering V025: `tests/test_g6_forbidden_list.py` reports forbidden vocabulary in many pre-existing modules. With that test excluded, additional pre-existing W158/W184/W185/W190/W192, sealed-prereg, missing-R7-authority-file, and stale source-manifest tests fail. None names `physics_v025`; the stage-1/1b suite itself passes. Those failures were not repaired because they are outside this task's mutation boundary and some concern sealed/history material.

## Stage 1b — sealed v1.1 rate-target amendment

Stage 1b adds `AngleRateTPC_TDM` (`a-r`) and `AngleRateTPC_FDM` (`a′-r`) with the synthetic `r* = 50,000,000 bit/s` Track B L1 operating point. `Gamma_r(n_b)` is selected from the frozen ACM table using effective bandwidth `W/n_b`. The TDM controller uses full-band noise in each equal-airtime slot; FDM uses physical sub-band noise, overlap-scaled interference, equal `1.65/n_b` user caps, and summed per-beam RF. Both use the history-free coupled solver. A missing table mode or cap-limited target transmits at cap and retains actual ACM bits, interference, and energy; `rate_target_feasible`, realised `rate_target_attained`, and `served_PHY` are separate receipt fields.

Current focused pytest receipt:

```text
77 passed in 0.21s
```

The estimate covers exactly 20 uniquely digested cells in sealed order: `a-r0, a′-r0, a-γ0, b0, a′-γ0`; then S/H/SH/T, each in `a-γ, b, a′-γ` order; then diagnostic `a-γU, bU, a′-γU`. Five physical tapes times 48 boundary-equivalents produce 240 shared physical equivalents and 80.5333333333 reference core-hours before `q`.

Stage-1b parity hooks accept the same `StepEndpoint`/pooled `EndpointTotals` in `reward_core(endpoint, eta_ref=...)`, and the KAT proves `sum_t reward_core(step_t) = reward_core(pool(steps)) = B - eta_ref E`. `assert_same_energy_price(lambda_bits_per_j=..., eta_ref=...)` requires both explicit arguments and fails closed on mismatch; stage 2 must call it at each target/endpoint binding rather than inherit a runtime default.

Open stage-1b `CONTROLLER_DECIDE` items before stage 2:

- `CONTROLLER_DECIDE — 20-cell treatment interpretation`: the explicit 20-cell total means S/H/SH/T and U apply only to the three retained architectures; the two added rate-target architectures have treatment 0 only. Confirm this reading in the launcher schema.
- `CONTROLLER_DECIDE — rate-target status aggregation`: `rate_target_feasible` requires nominal feasibility at every integrated boundary, while `rate_target_attained` compares realised achieved decodable ACM bits with `r*` over the whole user-step. Confirm whether downstream QoS also needs a per-boundary attainment series.
- `CONTROLLER_DECIDE — lowest-mode rounding`: `Gamma_r(1)` clears both the derived QPSK 1/4 threshold and the separately frozen rounded `served_PHY` floor; the latter is a few parts in `1e10` higher. Confirm this conservative max convention in controller acceptance.
- `CONTROLLER_DECIDE — estimate charging`: the simulator-inert estimate charges one 48-boundary tape for each of five architectures, including rate-target architectures with only one declared cell. Replace this reference arithmetic only with a measured server rehearsal.
- `CONTROLLER_DECIDE — stage-2 price binding`: the new explicit lambda/eta assertion is present but no stage-2 target pipeline was modified in stage 1b. Every C1/C2/C3 generator and endpoint consumer must be routed through it before target generation.
- `CONTROLLER_DECIDE — synthetic target provenance`: `r*` remains an uncalibrated synthetic operating point, and `rate_target_physical_calibration` remains `VERIFY_SOURCE`; no demand or hardware claim is admitted.

## Implemented surface

- `src/mcrl/physics_v025/constants_v025.py`: frozen V025 constants, 28-row EN 302 307-1 Table 13 transcription, canonical table SHA-256 `4463331e621d778f4aa97d60ed5726c1e02bcf791e2be7b134ec29eace631627`, provenance, and source-verification register.
- `architectures.py`: immutable `Geometry`/`Link` inputs; `FixedRF`, relabelled `AngleTPC_TDM`/`AngleTPC_FDM`, and `AngleRateTPC_TDM`/`AngleRateTPC_FDM`; deterministic equal-airtime order; union TDM slot clock; FDM bandwidth/noise/PSD overlap; zero-initialized capped fixed point with discrete-threshold clearance for feasible rate targets; 1e-10-W residual certificate; 4096-iteration INVALID outcome.
- `channel.py`: FSPL/loss conversion, corrected Bessel routing near `mu=34`, retained transmit and receive patterns, explicit keyed component seed, unit-mean Rician draw, zero-mean-dB shadow mean, and retained clear-sky table helpers.
- `acm.py`: greatest-eligible-efficiency ACM selection, monotone occupancy-to-rate-target inversion, inclusive PHY service boundary, zero bits below it, and separately named uncapped/margin-off U diagnostic.
- `energy.py`: fixed physical `(NORAD, beam-chain)` inventory, nonlinear per-slot PA accounting, circuit/baseband/standby components, active-floor clamp, bus exclusion, and a separately named non-primary event-energy sensitivity helper.
- `integration.py`: 48 boundary samples defining 47 trapezoids over 30.08 s; explicit left/right discontinuity samples; terminal snapshot treatment; conditional useful-time interruption with interval-union clipping; initial-entry/re-entry logging without an inferred blackout; RF energy retained.
- `resolution.py`: assignment/schedule then radiation/joint interference then decoding. A failed decoding attempt is never removed from radiation, interference, or energy.
- `endpoint.py`: exact `Fraction` ratio-of-sums pooling, explicit undefined all-dark EE, exact reward core, calibration arithmetic, decoding/useful availability, and complete-service counts.
- `matrix.py` and `adapter.py`: 20 immutable settings and SHA-256 per setting; shared architecture tape; S/H/SH/U rescoring on the retained architectures; Track-B dependency-injection hook; simulator-inert `python -m mcrl.physics_v025.adapter --estimate [--q Q]` reporting five architectures times `(1 snapshot + 47 subintervals) = 240` shared equivalents.
- `tests/physics_v025/`: 77 independent scalar/synthetic KATs. Arithmetic is stated in each test docstring rather than established by calling the production helper twice.

The existing Track-B runner was read from `/home/sat/mcrl-v024-codex-iter2/.scratch/multi-catfish-v024-regime-b/probe/run_v024_lever_matrix_probe.py`. Its injected `REGENERATION_ADAPTER` seam is supported by `track_b_regeneration_adapter`; nothing was copied from the sealed checkout.

## Old-physics preservation

No file under `src/mcrl/env/`, and neither existing runtime endpoint/calibration file, was edited. Pre/post SHA-256 values are identical:

| File | SHA-256 |
|---|---|
| `src/mcrl/env/link_budget.py` | `8f5a48e068dd185f9ad043c8c5eac4ef76fd074af134890a432d92b96ba21890` |
| `src/mcrl/env/step.py` | `9548304bf5c9382004adc576f3c7540b22a130d95302d52534f409aa35f117b0` |
| `src/mcrl/env/interference.py` | `ccba36f647300af655c6d8abaa18f4a7c8d0b9a49f96f35f43d6719d75ed3f08` |
| `src/mcrl/env/service.py` | `1d96f97cf0e3d97b14c07252b5361d6cc4111914aaa21c281a359446838dcdd8` |
| `src/mcrl/env/antenna.py` | `436c73c26fbd0b84e9effd92d7d581ab07080f2788587ada4ba8c6abef935a6f` |
| `src/mcrl/env/d2.py` | `d9acc8c47f399f170c2dea7d69457606a17ec631896a8175c65bcee4d9a8ff0a5` |
| `src/mcrl/env/dwell.py` | `0528f395e777d42668efd907f5caa4dde38a631896a8175c65bcee4d9a8ff0a5` |
| `src/mcrl/env/constants.py` | `3b2c44ac3437c12e5db2861c4372ba9720136ec81a9a7a60a8a6b65b245188f5` |
| `src/mcrl/runtime/ee_axis_evaluation.py` | `24c97cf99f5b6158dc39a7538c67518d62a85e276c8b2531e5deb5320655b881` |
| `src/mcrl/runtime/ee_axis_calibration.py` | `3dbff1a781f0d3c50e90d180d77a15c309f54bdc8835d7c36bda18927361bda0` |

The KAT `test_old_system_and_recurrence_outputs_unchanged` additionally characterizes `recurrence_power_w([2],[1],p0=.825) = 1.65` and historical one-beam `system_power_w = 6.465900454219553 W`.

## `VERIFY_SOURCE` register

Every flag remains true/open; none was converted into a measurement claim.

1. `beam_rf_cap_flight_hardware`: 1.65 W is inherited benchmark compatibility, not a derived or measured flight cap.
2. `pa_curve_and_backoff_flight_hardware`: square-root PA efficiency, 5-dB backoff, and 0.35 maximum efficiency are engineering assumptions, not payload validation.
3. `beam_to_rf_chain_mapping`: one physical beam identity to one charged RF chain is a benchmark mapping not established by the component source.
4. `circuit_and_baseband_payload_mapping`: 0.338 W and 0.200 W are retained component coefficients; their exact V025 payload applicability remains open.
5. `standby_ground_hpa_proxy_flight_applicability`: `f=35/420=1/12` comes from a ground Ka-band HPA mute/active ratio and is only sensitivity S/SH.
6. `interruption_live_beam_cell_procedure_applicability`: 62/142 ms are conditional electronic-terminal scenarios; live beam/cell procedure applicability remains open.
7. `common_1p7_db_margin_complete_distortion_budget`: 1.7 dB is the prospective common allowance, not evidence of a complete satellite distortion budget.
8. `rate_target_physical_calibration`: 50 Mbit/s is a synthetic Track B L1 operating point, not calibrated demand or evidence of physical suitability.

## Ambiguities and frozen stage-1 choices

Each item below is `CONTROLLER_DECIDE` before stage-2 artifacts or outcomes are opened.

- `CONTROLLER_DECIDE — authority ordering conflict`: superseded for engine enumeration by the sealed v1.1 amendment, which makes `a-r` primary and fixes `a-r0 > a′-r0 > a-γ0 > b0 > a′-γ0`; launcher/admission artifacts must reject the old order.
- `CONTROLLER_DECIDE — U placement`: U remains appended as diagnostic-only `a-γU, bU, a′-γU` and cannot participate in primary selection.
- `CONTROLLER_DECIDE — snapshot timestamp`: “decision snapshot” could mean the left endpoint `t`, while the round-1/round-3 KAT explicitly gives the terminal result `R(t)=t => 904.8064`. Treatment T therefore holds the terminal `t+30.08` sample.
- `CONTROLLER_DECIDE — FDM unequal-load alignment`: equal subbands do not state how unequal partitions on different beams align. Every beam starts at the low band edge, users use frozen ascending user-ID order, and interference is aggressor uniform PSD times exact victim/aggressor frequency overlap.
- `CONTROLLER_DECIDE — interruption mapping`: same-satellite beam change receives 62 ms and satellite change receives 142 ms. Initial entry and re-entry are logged but receive no inferred blackout. Overlaps are unioned and clipped once.
- `CONTROLLER_DECIDE — availability naming`: decoding availability reports the PHY threshold independent of interruption; useful availability additionally removes H blackout. Complete-service means every allocated sample in the user-step decoded. These remain distinct from the new `rate_target_attained` status.
- `CONTROLLER_DECIDE — discontinuity ownership`: the tape builder must provide two same-time left/right samples for every known event discontinuity. The integrator refuses a single ambiguous event value and never interpolates across the zero-duration jump.
- `CONTROLLER_DECIDE — nominal/realised split`: `a-γ`/`a′-γ`/`a-r`/`a′-r` power is always solved from nominal current geometry/interference. `nominal_or_realised` changes received wanted/interference fields only; it never gives realized fading to the controller.
- `CONTROLLER_DECIDE — saturated fixed point`: a cap-binding solution is certified by the residual of the capped map and remains CONVERGED; rate architectures separately mark its target infeasible. Exhausting 4096 updates or failing the final residual check yields INVALID, never a synthetic zero-effect outcome.
- `CONTROLLER_DECIDE — table hash representation`: the ACM digest binds compact canonical ASCII JSON of ordered `(name, efficiency, ideal Es/N0)` rows. Derived roll-off/margin columns are not duplicated into the table hash; they are independently frozen constants.
- `CONTROLLER_DECIDE — inventory adapter`: stage 1 requires the caller to provide a pre-action sorted physical `(NORAD, beam-chain)` manifest. Candidate/action slots cannot silently expand it. How the server world manifest is generated and sealed belongs to stage 2.
- `CONTROLLER_DECIDE — Track-B envelope`: the existing runner has a generic injected replay callable but no V025 cell schema. The adapter requires explicit `v025_setting`, `v025_geometry_samples`, and `v025_inventory` context keys and returns a versioned profile receipt. Controller-side launcher wiring remains stage 2; no old tape is reinterpreted.
- `CONTROLLER_DECIDE — source access`: the 28 table rows follow the named EN 302 307-1 V1.4.1 Table 13 authority. Network access to the official PDF was unavailable in this sandbox, so controller acceptance should independently compare the frozen rows/hash before outcomes.

## Stage-2 work and estimates

These are excluded from stage 1 and remain HOLD until the controller accepts the engine/KAT receipt.

| Work item | Bounded estimate | Required output |
|---|---:|---|
| C2 schema migration | 1–2 engineering days | Replace recurrence/entry/age semantics in Q1 tail and all Q2 consumers; freeze units, shapes, normalization, and schema hashes. |
| Teacher targets | 1–2 engineering days | Full-network C1 difference surplus, three-offset C2 forecast, set-level C3 objective/QoS terms, explicit outage attempts. |
| Calibration reference policy | 0.5–1 engineering day plus a TRAIN-only rehearsal | Freeze nominal-greedy policy and disjoint worlds; compute positive per-setting `eta_ref`, lambda, and kappa once. |
| Source regeneration | 1 engineering day of plumbing plus measured physics compute | Regenerate every physics-dependent target/dataset/cache/normalizer under bound engine/setting/world manifests; old sources remain transfer controls. |
| Comparator training | 1–2 engineering days orchestration plus campaign compute | Retrain scalar-objective MODQN and admitted FULL2/DROP/ALL_NEUTRAL lineages; three initializations. Old-speed 3000-world evaluation reference is about 140 core-hours, but integration/forecasts/C3 require a new rehearsal estimate. |

Before any of that: independently verify the official ACM table transcription, resolve every `CONTROLLER_DECIDE`, wire/authenticate the server world-inventory and D2-boundary tape generator, then rerun these KATs in the controller environment. No physics outcome should be opened before that gate.
