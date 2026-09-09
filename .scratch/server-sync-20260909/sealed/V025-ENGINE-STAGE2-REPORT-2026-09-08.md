# V025 engine stage-2 report — 2026-09-08

## Disposition

Stage 2 is implemented and the synthetic acceptance path is runnable. The formal v1.2 TRAIN matrix remains **HOLD** until the controller installs the server primitive-world provider and freezes the four probe-world manifests, the complete per-setting calibration manifest, the catalogue definition, and the cell order before opening a unit outcome. No TEST world, learner update, source regeneration, or formal successor outcome was opened.

The stage-1/1b controller decision record and sealed v1.2 amendment were applied without changing the scientific priority: `a-r0 > a′-r0 > a-γ0 > b0 > a′-γ0`, then S/H/SH/T, each in `a-r, a′-r, a-γ, b, a′-γ` order, then diagnostic U-cap/U-margin for the three original architectures. The explicit enumeration yields 25 primary-eligible plus 6 diagnostic settings = 31; v1.2's sentence “28 primary-eligible” conflicts arithmetically with its list and remains a pre-launch controller decision. Treatment T holds the **left decision-time sample** for 30.08 s. Rate-target receipts retain both step aggregation and all 48 per-boundary attainment values.

## Verification receipt

Focused suite:

```text
102 passed in 1.8s
```

Command:

```bash
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/physics_v025
```

`python -m compileall` and `git diff --check` also passed. A one-step smoke of every arm completed in all 31 explicitly enumerated settings; this was a tiny two-user synthetic check, not a matrix outcome.

A repository-wide pytest attempt completed with 57 failures outside this focused surface: stale older C3 fixture signatures, missing sealed R7 artefacts, historical source-manifest drift, and two global vocabulary/ruling tests already incompatible with the committed stage-1 tree. None was changed here. The Stage-2 acceptance line above is therefore the scoped executable receipt; the broader repository baseline is not green.

No file under `src/mcrl/env/` was edited. The ten old-system files checked in stage 1 are byte-identical to `HEAD`. In particular, the actual `src/mcrl/env/d2.py` SHA-256 is `d9acc8c47f399f170c2dea7d69457606a17ec631d5040ef56df97a29228c6d37`; the stage-1 report's different suffix was a transcription error, while the file itself has not changed.

## Implemented surface

- `tapes.py` applies the repository SHA-256 domain rule to `V025_PROBE/world/{1..4}` and disjoint `V025_CAL/world/{1..2}`. It freezes the sorted physical `(NORAD, beam-chain)` inventory before acquiring candidates, detaches primitive 48-boundary step snapshots, records the TLE-date × training-seed cluster identity, user layout, actual-elevation keyed fading, D2 and live 10° visibility state, and produces independent inventory/layout/tape/carrier/world digests. The three fixed carriers are nearest-eligible, stay-if-possible by physical identity, and SHA-keyed random-masked.
- `channel.py` now makes the S.465-6 `D/λ < 50` boundary (`2.043298703°`) explicit, retains the declared clipped analytic near-axis approximation below it, applies that gain in the interference helper, and samples shadow/scintillation at each link's actual elevation. Same-satellite interference retains the physical boresight override.
- `calibration.py` defines a causal deterministic nominal-greedy policy with no circular EE price, exact-rational pooling, `η_ref = λ = B_ref/E_ref`, and `κ = B_ref/(U·T_ref)`. Calibration consumes exactly the two disjoint calibration domains and serializes one immutable value per setting.
- `targets.py` implements whole-network C1 difference surplus plus explicit Φ, three-offset C2 with projected geometry/background-power recomputation and one `−κ` for every absorbing lost offset, a-r required-power/cap/service fields, the declared LC-SRS `Ψ = F11 − F10 − F01 + F00` on `F=B−η_refE`, and `z3,i=e_i+Ψ/2`. All target and state producers require explicit λ, η, and κ and fail closed on mismatch or omission.
- `state_v025.py` freezes a 21-value per-action schema: nine current/action fields and three groups of four offset fields. It removes recurrence power, entry-gain ratio, and segment age; binds units, normalization scales, shape, and schema SHA-256 `54ab6a82354949f4c25db230f24f79f000fc14327d3c5e7a0e14231f78cb428f`.
- The matrix runner evaluates complete legal configuration catalogues independently under each selected cell; reports E1 U1/J1/union certificates, deployable S0 top-two proposals plus frozen evacuations, FULL/DROP_C1/DROP_C2 set decoding, independent C1+C2 DROP_C3, ALL_NEUTRAL_CONTROL, NULL≡BASE, random-feasible, and nominal-greedy. Receipts include the requested bits/joules, activation/energy, availability, rate, outage, handover, changed-user, interaction, calibration, certificate, Φ, and timing fields and are write-once mode 0444 with SHA-256 sidecars.
- Merge reporting uses paired TLE-date × training-seed cluster bootstrap draws and recomputes pooled `ΣB/ΣE` inside every draw. Per-world log-EE intervals are supplementary. Each FULL−DROP gate requires its 95% pooled-EE lower bound above +0.5 percentage points and zero-margin non-inferiority for availability, Φ, and handover rate; FULL−ALL_NEUTRAL is supporting only, and no across-background main effect is claimed.
- Event classification uses `(NORAD, beam-chain)` and an explicit cell-rekey flag. `N=4` is named the declared candidate-refresh period, not dwell; the reporting estimator divides only by boundaries that could re-key and never counts step 0.

The S.465 KAT independently evaluates interferers at 1°, 2.043298703°, and 5°. The time-base KAT integrates linearly drifting power and bits against closed forms on `t+k·0.640 s`, `k=0..47`. It does not use the legacy helpers or a snapshot as its oracle.

## CLIs

The simulator-inert estimate and the mandatory synthetic execution checks are:

```bash
PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --estimate --q Q
PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --dry-run
PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --rehearsal
```

Formal execution deliberately requires an installed `module:factory` provider that returns primitive inventory/layout/boundary snapshots. The pre-outcome order is:

```bash
PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --manifest --provider PACKAGE:FACTORY --output OUT
PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --calibrate --provider PACKAGE:FACTORY --output OUT
PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --unit 'a-r0:1' --provider PACKAGE:FACTORY --world-manifest OUT/world-manifest.json --calibration OUT/calibration-manifest.json --output OUT
PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --merge --output OUT
```

`--unit` rebuilds the requested tape and refuses execution if its digest differs from the immutable pre-outcome world manifest. Under the explicit v1.2 enumeration, `--merge` requires all 124 immutable `CELL:WORLD` receipts and preserves the declared cell order.

## Rehearsal and projected overnight cost

The bounded rehearsal ran a-r0, probe world 1, three steps (one anchor for each fixed carrier), and every one of the 12 arms. It used 0.841 s inside the measured runner section (1.10 s total process wall time including calibration setup), 1.08 user CPU seconds, and 52,772 KiB peak RSS. It counted 6,048 physical boundary evaluations, including per-cell nominal scoring and every three-offset background-power recomputation.

Against the receipted reference `302 s × 4 workers / 3,840 evaluations`, the measured synthetic `q` is **0.00044185435404002173**. The five-architecture shared plan is 240 reference equivalents = 80.5333 core-hours before q; the added treatment settings rescore those same architecture tapes. Including the frozen 30% orchestration/rescore reserve gives a projected **0.046259205172296675 core-hours** for the explicitly enumerated 31-setting plan, below 160 core-hours.

This number is a code-path rehearsal measurement, not a server-runtime claim: the required rehearsal world is intentionally tiny (two users, nine complete configurations) and the formal ephemeris provider is not installed in this checkout. The controller must replace this projection with the same CLI using the sealed server provider before launch. Because the measured projection did not exceed 160 core-hours, the conditional over-budget time-attribution clause did not trigger; if a server rerun exceeds it, the runner's report names geometry/channel/coupled-power catalogue construction, three-offset forecast recomputation, and arm rescoring separately and requires shared-computation optimization without truncation.

## Channel/time findings carried into the model

- The legacy fixed-10° shadow elevation fallback is not used. Actual elevation changes both the shadow sigma and scintillation term under common keyed variates.
- The S.465 receive pattern and interference path use the 2.043298703° branch plus the separately declared near-axis approximation. The old unused 2.498° floor is not copied.
- The unreceipted 16.4 dB / 700 Mb/s statements are excluded from calibration. The approximately 6.6 dB median SINR and 7.3 dB median interference penalty remain context from a prior receipt, not a calibration constant.
- Treatment 0 integrates power and bits. The reported legacy zero-order-hold energy undercharge (about 2.27%, with about 0.5 percentage-point segment-age dependence) is not corrected by a scalar multiplier.
- The approximately 0.482 dB recurrence excursion per 30.08-s step explains an old renewal premium but is irrelevant to this memoryless controller and is absent from state/targets.
- `N=4` is inherited and declared as a candidate-refresh period, not re-derived from the corrected boundary-conditional re-key rate. D2 eligibility and the live 10° visibility gate are separate and both are reported.

## `VERIFY_SOURCE` additions

The eight stage-1/1b flags remain open except that the controller's independent ACM-row comparison clears development use; an official-PDF paper check remains documentary verification. Stage 2 adds:

1. `formal_primitive_world_provider_and_tle_binding`: the server provider module, TLE archive, TRAIN sampler, and provider source digest are not present in this checkout and must be authenticated before manifest generation.
2. `shadow_scintillation_table_live_terminal_applicability`: actual-elevation use fixes the software defect; applicability of the retained benchmark tables remains unverified.
3. `s465_near_axis_approximation`: the branch boundary is source-correct, but extending `32−25log10θ` below it is explicitly an engineering approximation, not ITU prescription.
4. `d2_entry_elevation_by_altitude_receipt`: approximately 19.7/23.4/27.7° at 426/485/550 km must be reproduced by the installed provider; they are not hard calibration anchors.
5. `synthetic_rehearsal_cost_transfer`: the tiny-provider q cannot be promoted to a full server overnight-cost receipt.
6. `prior_sinr_rate_anchor`: 16.4 dB / 700 Mb/s is unreceipted and forbidden as a calibration anchor; 6.6/7.3 dB remains contextual only.

## `CONTROLLER_DECIDE` additions

These are declared implementation choices or missing external bindings; they are not silently outcome-tuned:

- `formal provider identity`: seal `PACKAGE:FACTORY`, its source SHA-256, TLE/TRAIN inputs, user count, start-time derivation, and its primitive cross-gain construction before `--manifest`.
- `v1.2 matrix arithmetic`: the amendment explicitly lists 25 primary-eligible settings and six diagnostics, while its prose says 28 primary-eligible. The engine follows the explicit priority list (31 total); correct or expressly accept that count before sealing the launcher.
- `world duration`: the current probe unit executes three anchors (nearest, stay, random) and materializes three extra physical steps solely for the three-offset forecast. Confirm this one-anchor-per-carrier reading.
- `catalogue census`: complete Cartesian legal physical assignments are the union catalogue; a unilateral changes exactly one user, and J1 searches genuine changed-user-count >1 configurations. Confirm before sealing the catalogue digest.
- `LC-SRS e_i binding`: `targets.py` requires explicit `e_i`; the runner currently computes it as unilateral whole-network objective change less that focal user's bit change, then adds `Ψ/2`. Bind this to the unavailable fresh-context §C source before a formal calibration/manifest.
- `QoS guard`: Φ is explicit in C1 and the common event ledger. The merge gate uses the literal zero-margin meaning of non-inferiority for availability/Φ/handover count; seal another prospectively numeric margin before outcomes if intended. Catalogue/service exclusion thresholds likewise need a seal if they are to exclude configurations rather than only score/report them.
- `nominal-greedy lexicographic rule`: maximize nominal served users, then nominal bits, then lower nominal energy, then configuration ID. It intentionally uses no λ to avoid circular calibration.
- `normalization scales`: the 21-field state scales and the treatment of non-rate required-power margin as a zero placeholder must be sealed with schema SHA-256 before source generation.
- `snapshot report correction`: accept the left-snapshot implementation/KAT and record that the stage-1 report's terminal-snapshot prose is superseded by the controller decision record, without editing the historical report.
- `formal calibration freeze`: run `--calibrate` once with the authenticated provider, seal all 31 exact η/λ/κ values under the explicit enumeration, and require that immutable file in every unit. Synthetic values/digests in dry-run output are not admissible.

## Controller seal required before launch

The controller must seal, in this order:

1. the provider/TLE/TRAIN binding and four `V025_PROBE/world/{1..4}` world manifests, including inventory, layout, tape, carrier, and aggregate digests;
2. the two calibration-world manifests and all per-setting exact `η_ref=λ`, `κ`, selected nominal-greedy configuration, and calibration receipt digests;
3. the union/S0 catalogue definition, top-two/evacuation rule, LC-SRS `e_i` interpretation, service/QoS guard, and catalogue digest;
4. the exact v1.2 setting list/order, the 25-versus-28 eligible-count resolution, and each setting digest;
5. the measured server-provider rehearsal q and projected cost, retaining all cells/worlds/catalogue entries if optimization is required.

Only after those seals should the formal units be opened (124 under the current explicit 31-setting enumeration). Stage A remains HOLD pending the matrix admissions.
