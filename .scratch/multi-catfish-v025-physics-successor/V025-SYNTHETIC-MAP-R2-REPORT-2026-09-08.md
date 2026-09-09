# V0.25 synthetic mechanism map R2 — budget-abort report

**Experiment label:** `SYNTHETIC_MECHANISM_MAP_R2`  
**Disposition:** `FINAL_RECONCILIATION_CORE_HOUR_CEILING_EXCEEDED`  
**Formal E1–E4 score:** **NOT SCORED — binding 36-world grid incomplete**

## Executive result

The stage-4b engine and matrix runner were imported, the synthetic provider and sweep runner were adapted to the stage-4b interfaces, and all compatibility/KAT checks pass. The run was interrupted when 135 of 180 setting-world units had sealed because a defect in the original cost estimator omitted the three reference carriers executed at every anchor. Two already-running worker world-groups then finished and sealed during `ProcessPoolExecutor` shutdown. The final state is therefore **145/180 units (29/36 worlds)** and an accounted lower bound of **10.3864 core-hours**, exceeding the binding ceiling by **0.3864 core-hours**. The corrected full-run projection is **25.3731 core-hours**.

The 145 completed unit receipts and 60 calibration receipts are sealed under `SYNTHETIC_MECHANISM_MAP_R2`, but they are quarantined as partial diagnostic evidence. There is no merged map receipt and no formal E1–E4 score. The missing worlds are seeds 3 for `HIGH-SPARSE-STRONG` and all three seeds for `HIGH-DENSE-WEAK` and `HIGH-DENSE-STRONG`; their omission is strongly non-random with respect to the registered occupancy and coupling comparisons.

The earlier R1 sweep is explicitly marked `SUPERSEDED_B2`. Its factor-arm selector optimized the exact realised objective instead of the v1.5 §2 `C1 + C2 + C3` target sum.

## Stage-4b integration and receipts

- `src/mcrl/physics_v025/` matches the immutable stage-4b snapshot byte-for-byte, apart from the retained local `provider_synthetic.py` and generated `__pycache__` directories.
- The imported stage-4b matrix runner's source SHA-256 was `785cd8ede1d2717e5ea6058ea55b8060a37dd3c9eb951b5a36fd7308da172351`. R2 adds receipt-only architecture, nominal-selector, required-power, and fixed-point diagnostics; the resulting runner SHA-256 is `afa188ac0f56b7b256c9dc5d2f109493fd1a7ccbb5cd862dfa39164ca6c3ff3d`.
- The synthetic provider now supplies the stage-4b TRAIN protocol attestation and nominal/realised cross gains keyed by complete `(NORAD, chain)` identity. Its SHA-256 is `6166489b96f8b7fc986dbac34436605b8241f3154e06badabcffc2e75d0e6151`.
- The R2 sweep runner delegates bounded-catalogue construction, radiation-ledger accounting, v1.5 target-sum factor selection, and κ-normalisation to stage 4b. The unsafe occupancy-only evaluation cache is disabled so per-chain physical identities remain visible.
- All 145 completed units report `COMPLETE`, use common-random worlds across settings, and carry the R2 label. Their 13,050 executed anchors have zero S0 nominal-service-guard violations. All completed units happened to use stage 4b's complete-Cartesian branch; the bounded branch is covered by the stage-4b contract KAT.
- The partial execution recorded 873 anchors with at least one deadline fallback in 13,050 anchors (6.69%). This is another reason not to promote the partial table to a formal map.
- The final stage-4b regression run passed all **176 collected tests**, including the synthetic protocol/per-chain cross-gain KAT, TDM/FDM dispatch KAT, S0 nominal-service-guard/power-ledger KAT, corrected three-carrier budget-gate KAT, bounded-catalogue contracts, ledger contracts, and κ-unit contracts.

## Budget-gate defect

The first final-schema dry run measured one `(step, setting)` execution and projected that number over legal steps, but each unit actually executes **three** sealed reference carriers per anchor. The missing multiplier made the gate report 8.6256 core-hours. After adding `len(REFERENCE_CARRIERS)`, the same method projects 25.3731 core-hours.

At the first abort marker, the accounted lower bound was 7.8135 core-hours. During executor shutdown, two in-flight worlds completed and sealed. Final reconciliation gives **10.3864 core-hours**: 9.8208 in sealed unit execution, 0.0909 in sealed calibration, and 0.4747 in two dry probes. KAT time remains excluded, so this is still a lower bound. Concurrency never exceeded four workers, but the shutdown behavior caused the binding core-hour ceiling to be exceeded before the workers exited. The immutable first marker is retained and a second immutable reconciliation receipt records the final state.

## Required anomaly explanations

### (a) TDM/FDM dispatch

There is no architecture-dispatch defect in stage 4b. Across all **29 completed paired worlds**:

- every `a-r0` anchor dispatches `a-r` to `AngleRateTPC_TDM`;
- every `a′-r0` anchor dispatches `a′-r` to `AngleRateTPC_FDM`;
- 29/29 paired receipt digests differ;
- 29/29 paired ACM histograms differ; and
- 29/29 paired mean required-power values differ.

Some pooled outcome columns remain identical: 13 of the 29 pairs match on the aggregate numeric summary. This is a symmetry of this synthetic construction, not shared execution: users within a chain are exchangeable, subbands divide bandwidth and the applicable cap equally, and there is no intra-beam interference. The receipt-level architecture class, per-chain power ledger, ACM distribution, and fixed-point iteration trace distinguish TDM from FDM even where the pooled bits/score cancel to the same value.

### (b) Availability and the 50 Mbit/s target

The roster accounting is correct. Users remain in the full roster when outside the D2 legal window; for the completed LOW rate-target worlds, partial-service availability is exactly 2/3, hence the reported unserved-roster share is 1/3. Across the synthetic geometry, D2 entry is at **27.646°**. For D2-eligible candidate-boundary samples, the elevation 0/5/50/95/100% quantiles are **27.649/29.265/43.823/58.384/59.997°**, slant range is **626.9/636.4/762.7/1009.9/1049.9 km** (range reverses with elevation), and nominal end-to-end gain is **−112.84/−111.83/−109.24/−107.36/−106.93 dB**.

The extra rate-target loss is not a cap failure. Over the 12 completed LOW worlds, mean FULL availability is 0.4201 for both rate-target architectures versus 0.6373 for `a-γ0`/`a′-γ0` and 0.6375 for `b0`. TDM rate-target selected power averages about 0.046–0.049 W and peaks at 0.114–0.128 W; FDM averages 0.031–0.033 W and peaks at 0.077–0.083 W, all far below the 1.65 W beam cap, with zero cap hits. By contrast `b0` intentionally sits at the cap (cap-hit share 1.0).

The 50 Mbit/s controller targets the lowest ACM threshold nominally. Realised keyed fading often moves a transmission just below QPSK 1/4, producing `NO_MODE` shares of 0.336–0.395 in LOW rate-target transmissions. Thus approximately one third of opportunity is unavailable geometrically, and a further decoding-threshold loss reduces realised availability from about 0.637 to about 0.420. `UNSERVED` is not being dropped from the denominator.

### (c) S0 nominal versus realised

The stage-2 B2 selector defect is absent. At each of all 13,050 completed anchors, S0's receipt contains a nominal certificate and the selected configuration is nominally non-inferior to BASE under the service guard: **0 violations**. This is the required construction KAT.

The S0 column in the map is nevertheless a *realised* comparison. Selection uses nominal gains; evaluation uses separately keyed realised fading. A nominal winner can therefore underperform BASE after realisation without contradicting the selector invariant. Stage 4b's κ units also correct R1's scale: completed-cell realised S0 differences range from approximately **−103.3 to 0 normalised units**, rather than R1's −350 to −550. The negative values are realised selection regret, not a nominal selector failure.

### (d) Normalised and relative pooled-EE views

The table below supplies both requested views. `J1−U1 norm` and `S0 norm` divide the calibrated surplus difference by the setting-specific κ (bits per user-second). The percentage columns compare pooled energy efficiency (`sum(bits)/sum(joules)`) across the three paired seeds: J1 against U1, and S0 against BASE/NULL. This is **non-binding partial diagnostic evidence**, not an E1–E4 score.

| Completed cell | Setting | J1−U1 norm | pooled EE Δ | S0 norm | pooled EE Δ | FULL avail. | unserved roster | NO_MODE | mean RF W | max RF W | cap-hit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HIGH-SPARSE-WEAK | a-r0 | 21.296 | +4.613% | 0.000 | +0.000% | 0.633 | 0.333 | 0.022 | 0.4532 | 1.3877 | 0.0000 |
| HIGH-SPARSE-WEAK | a′-r0 | 21.296 | +4.613% | -27.318 | -4.455% | 0.635 | 0.333 | 0.005 | 0.0708 | 0.1735 | 0.0000 |
| LOW-DENSE-STRONG | a-r0 | 11.843 | +6.951% | -42.212 | -21.097% | 0.423 | 0.333 | 0.387 | 0.0491 | 0.1188 | 0.0000 |
| LOW-DENSE-STRONG | a′-r0 | 11.843 | +6.951% | -42.212 | -21.097% | 0.423 | 0.333 | 0.337 | 0.0333 | 0.0832 | 0.0000 |
| LOW-DENSE-WEAK | a-r0 | 11.770 | +7.210% | -36.278 | -18.221% | 0.416 | 0.333 | 0.395 | 0.0463 | 0.1139 | 0.0000 |
| LOW-DENSE-WEAK | a′-r0 | 11.770 | +7.210% | -36.278 | -18.221% | 0.416 | 0.333 | 0.347 | 0.0316 | 0.0774 | 0.0000 |
| LOW-SPARSE-STRONG | a-r0 | 3.512 | +2.108% | -48.113 | -24.791% | 0.423 | 0.333 | 0.386 | 0.0482 | 0.1282 | 0.0000 |
| LOW-SPARSE-STRONG | a′-r0 | 3.512 | +2.108% | -48.113 | -24.791% | 0.423 | 0.333 | 0.336 | 0.0327 | 0.0832 | 0.0000 |
| LOW-SPARSE-WEAK | a-r0 | 3.332 | +2.141% | -42.193 | -21.850% | 0.419 | 0.333 | 0.392 | 0.0456 | 0.1236 | 0.0000 |
| LOW-SPARSE-WEAK | a′-r0 | 3.332 | +2.141% | -42.193 | -21.850% | 0.419 | 0.333 | 0.344 | 0.0309 | 0.0771 | 0.0000 |
| MID-DENSE-STRONG | a-r0 | 27.914 | +18.238% | -103.285 | -42.816% | 0.617 | 0.333 | 0.045 | 0.1439 | 0.3079 | 0.0000 |
| MID-DENSE-STRONG | a′-r0 | 27.914 | +18.238% | -103.285 | -42.816% | 0.617 | 0.333 | 0.033 | 0.0386 | 0.0781 | 0.0000 |
| MID-DENSE-WEAK | a-r0 | 24.409 | +16.539% | -90.009 | -39.013% | 0.611 | 0.333 | 0.061 | 0.1394 | 0.3079 | 0.0000 |
| MID-DENSE-WEAK | a′-r0 | 24.409 | +16.539% | -90.009 | -39.013% | 0.611 | 0.333 | 0.042 | 0.0382 | 0.0770 | 0.0000 |
| MID-SPARSE-STRONG | a-r0 | 14.811 | +7.808% | -56.793 | -21.895% | 0.620 | 0.333 | 0.037 | 0.1412 | 0.3344 | 0.0000 |
| MID-SPARSE-STRONG | a′-r0 | 14.811 | +7.808% | -56.793 | -21.895% | 0.620 | 0.333 | 0.029 | 0.0373 | 0.0836 | 0.0000 |
| MID-SPARSE-WEAK | a-r0 | 13.383 | +7.113% | -50.520 | -19.504% | 0.619 | 0.333 | 0.038 | 0.1407 | 0.3344 | 0.0000 |
| MID-SPARSE-WEAK | a′-r0 | 13.383 | +7.113% | -50.520 | -19.504% | 0.619 | 0.333 | 0.030 | 0.0371 | 0.0836 | 0.0000 |

## E1–E4 scorecard

| Expectation | Formal R2 score | Reason |
|---|---|---|
| E1: rate-target joint headroom grows with occupancy and coupling | **NOT SCORED** | `HIGH-SPARSE-STRONG` has only two seeds and both HIGH-DENSE cells are missing. |
| E2: LOW consolidation dominates and C3 marginal is approximately zero | **NOT SCORED** | The declaration binds the score to the complete 36-world map; partial evidence is not substituted. |
| E3: `b0` headroom is flat across occupancy | **NOT SCORED** | Both HIGH-DENSE cells are absent and `HIGH-SPARSE-STRONG` is incomplete. |
| E4: FDM rate target has weaker occupancy coupling than TDM | **NOT SCORED** | The missing HIGH cells prevent the registered LOW→HIGH comparison. |

No expectation is marked met or failed. Finishing under the stated stage-4b execution method would require either raising the budget above the corrected 25.37-core-hour projection or changing the binding design/execution method in a new declaration.

## Evidence index

- Budget abort: `synthetic-map-r2/BUDGET-ABORT.json` (`842d714c04303fa0d77f59f1795591a7ec8e31d39b94a3dad1b776ba83b5b315`)
- Final budget reconciliation: `synthetic-map-r2/BUDGET-ABORT-RECONCILIATION.json` (`983cf15899c1484871e8a8871dddc02e14bd2c3e6b0668fe6511cc6197c93b81`)
- Corrected estimate: `synthetic-map-r2/corrected-estimate.json` (`403c6221aa4b76f3995233b9a1ab2649e6e4e0c5fa3f5430a4e0a4e111e1cfce`)
- Sealed partial units and calibration: `synthetic-map-r2/units/` and `synthetic-map-r2/calibration/`
- R1 supersession: `synthetic-map/SUPERSEDED_B2.json` (`89b108a7e3f6e04daec67b889649c92c7ea8bfd5c2562f784189e7f9149cb601`)
