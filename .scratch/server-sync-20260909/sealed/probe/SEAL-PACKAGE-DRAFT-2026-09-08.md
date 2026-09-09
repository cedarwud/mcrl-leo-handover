# V0.25 probe seal package — stage-4h refreshed draft (2026-09-09)

Status: **FORMAL STEPS OPEN / NOT YET CONTROLLER-SIGNED**. This is a TRAIN-only pre-freeze package. The real-anchor compute gate passed before the formal manifests, allocation, calibration, rehearsal and development smoke were opened. No TEST data or claim-panel outcome was opened. The ten-anchor smoke is diagnostic and cannot establish admission.

The executable schema is `multi-catfish-mcrl-v025-matrix-probe-v1.9-stage4h`. The primary setting remains `a-r0`; alpha=.10 remains the selection quantile regardless of the robustness sweep. The controller-owned hash-chained attempt registry remains `/home/sat/mcrl-records/ATTEMPT-REGISTRY-2026-09.jsonl`.

## Governing amendments and implementation

| authority | SHA-256 |
|---|---|
| v1.6 amendment | `915484bcde9b207ba44c1b4bc958e423526f967ea91494287d437942408b4eb5` |
| v1.7 erratum | `a16504f0b04e3df662f451596e016c6a0b2a6936b924ae7086294a4795e75aa3` |
| v1.8 amendment | `bfed9b3e73679eaece942bb158b5b3e816a836de6ad64d5600c4ad85d2b5be51` |
| v1.9 amendment | `95064e561bc5a1b8a5be02cf11a5b71607c97786a6d26f88e8a5d76918fba911` |
| current launcher | `f4122d6784cb56de7743c55d51dc80a6c968ccea601d637cd1b41a8b5604c76c` |
| current code-authority aggregate | `5a0f927bb3798e3adef62f2608fe709b8a23037a51b59261c799b9a32de38c33` |

The v1.9 margin implementation preserves nominal predicted/executed power and nominal interferers. A sealed 200,000-draw cached quantile of the complete fading product affects only wanted-link predicted reception and transmitted-mode choice. ACM emits `m_target`, `m_tx` and realised decode outcome separately and credits the transmitted mode only on a realised threshold pass. Selection-time and realised endpoint decompositions remain separate; every coalition receives its interaction label, while Shapley attribution alone is capped at four users.

Per-arm ranking and top-M keys are FULL C1+C3 then C2, DROP_C1 C3 then C2, DROP_C2 C1+C3 then deterministic ID, and DROP_C3 C1 then C2. C2 is a tie-break only and its physics certificate is forecast validity. The admission rule is the monotone `ADMIT_FULL` / `ADMIT_C1C2` / `NOT_ADMITTED` trichotomy from v1.9.

## Compute gate and sealed selection surface

The declared four-process evaluator uses deterministic round-robin sharding and catalogue-order reduction. Serial/parallel results and receipt counts are exact-equality tested. The predeclared fallback sequence ended at one boundary per forecast offset and M=48.

On three real quarantined a-r0 decisions, catalogue counts were 997, 997 and 966. Decision times were 9.920572, 8.879807 and 5.949833 s: mean 8.250071 s, p95 9.816495 s, maximum 9.920572 s. Complete-anchor totals were 21.315449, 20.119099 and 20.540675 s: mean 20.658408 s, p95 21.237972 s. Thus both the <10 s selection and <60 s per-anchor gates pass. Provider construction was 20.222051 s once/world.

The host exposed one runnable CPU, so four workers were time-sliced. This is a conservative execution of the declared process topology, not evidence of four physically simultaneous cores.

## Formal immutable world and calibration manifests

All listed files are mode 0444 with SHA-256 sidecars.

| domain | file SHA-256 | embedded receipt SHA-256 |
|---|---|---|
| `V025_PROBE_R2/world/1` | `49daadf842e89ed2d539ca94bd29f51db619a4c709467b4a657dd3afba3dd657` | `564161362bb87b742e4fd2a0f0648032ba5e1fea9061cbb25026963f7c8567dd` |
| `V025_PROBE_R2/world/2` | `18eededb2b219da7231b55280be583e40cf19d49ebf6c55e6e8d4350a9e90671` | `e412796b7429e68f26a8dc60263c97848f4730201845ede0195c8a933d0ee088` |
| `V025_PROBE_R2/world/3` | `c82286b4e2e330c430880067e917d3682c32448b0b710f208f2c9d267b006232` | `43676e11c355c112db76ada552927c1fa4af7ec1fe14c3fa3b51efa8ff1649c4` |
| `V025_PROBE_R2/world/4` | `d7505093b0fe8da3ea126b10a0d38fe200a2ed2f0c4415af90badeecf51720fa` | `9b455bc58db3184a82f3d64131d230af152b2d1cec8bf24a945385d6acc0e7bc` |
| `V025_CAL_R2/world/1` | `30c4b378d7058a5608fc0326279f05277bda9a1806c43526548ccdbd4d247f9a` | `61d73944d9e5ad7f30948dc1c7428bfaca14bd7e83df6e6864cf8e8c736407f0` |
| `V025_CAL_R2/world/2` | `ec69cf35eb92fc40429ed8c49b8b7d6a450cbaf122734abcb2e8de5ccd4dfaff` | `3d528f924051488c51c7277a06213961f2275b96e29599d05502b190c479fe3e` |

Aggregate probe manifest SHA-256: `e7bdb1d4d59d68a05f2b30437ff3c4c9fbcb20ae7e6d28613843ed3bc3fe7165`. Aggregate calibration manifest SHA-256: `fecc09ebcf1ee89a05183df905d65c851018a53f4dcd7dbcc1719a1328460aa0`.

The a-r0 calibration rolled all 30 nominal-reference decisions on each of the two disjoint calibration worlds. Exact manifest fields give `eta_ref=lambda=491164408115206640000000/24906057152504541`, `kappa=6139555101440083/7500000` bit/user-step, 60 decision steps and 100 users. The aggregate calibration receipt is `b9fef5bc60849df103679f5d99becda9151106ec0673b79e7162ec3db2d698e0`.

## Allocation and claim reservation

`.tmp/stage4h-formal/allocation-manifest.json` contains 24 canonical identities: PROBE 4, CALIBRATION 2, REHEARSAL 1, KAT 8, SYNTHETIC_REAL 4, SMOKE 1 and CLAIM_PANEL 4. File SHA-256: `2d3e2cb3e34e67f321127e568a8d2d6714c9f5bb4ad8e2fe6ef2d111470fd369`.

The initial `V025_CLAIM_PANEL/world/1` reservation resolved to calibration date 2026-08-05 and failed the claim-freshness invariant. It was not opened for outcomes. The panel inventory is now worlds 2, 3, 4 and replacement 5; world 5 resolves to 2025-12-05. All four claim dates are absent from every listed successor-development role. Development-development date reuse is recorded but is not claim leakage.

The TLE rule remains nearest epoch from date-1/date/date+1 at episode start, absolute age <=24 h. Future epochs are allowed. Causality is determined by receipt/publication availability, not epoch sign; this retrospective benchmark does not support an operational deployment claim.

## Rehearsal, q and stride

The authoritative schema-corrected rehearsal is `.tmp/stage4h-formal-q/rehearsal.json`: 3 anchors, 14 arms, 15,566 physical boundary evaluations, 67.030349 s and 4.468690 four-worker core-minutes. `q=0.013688590926973465`. File SHA-256: `06d6a0dd292b6ac7f37efe47bf0fccccb8f56fa39395a7f0a2b7e584d701fcf7`; unit receipt: `3090021b89e254c0cbc45ad53fc77dc6d1e0696a40698e8e4fb23d08a7338f03`.

The direct 4×90-anchor projection is 8.937380 core-hours. At process concurrency 20 and four workers/unit, five units run concurrently and ideal projected wall time is 26.812140 minutes. The rehearsal is below 10 core-minutes and the projection is below 160 core-hours, so the smallest sealed anchor stride is `k=1`; no thinning rung is invoked.

## Development SMOKE and diagnostics

The 10-anchor, 14-arm run is explicitly `SMOKE_NOT_MATRIX`: `.tmp/stage4h-formal/smoke/a-r0-world-1.json`, file SHA-256 `f772877da8fb2fcd45d626c92a3bf8725fc47326c90ad8529977cac0695dceed`, receipt `a39b0c174118374bfb04640affed08e80b243d1f4b28353fa42e038cb42e82d9`. It used 15.535257 core-minutes. The full arm table, causal ACM census, factor marginals, `g_A/g_I`, availability, lit-beam time, cap/plateau shares and certificate distributions are in `../V025-ENGINE-STAGE4H-REPORT-2026-09-09.md` and the immutable receipt.

Paired ACM before/after evidence is `.tmp/stage4h/acm-before-after.json` (receipt `5fa975a282bfb319933ab01eb31c0430c0af904987d05593b53c3efdfd48e2c9`). The corrected two-anchor availability is 0.453138 and pooled EE 5.658947 Mbit/J, down from genie values 0.791277 and 18.940246 Mbit/J at identical energy.

The closed-loop alpha=.05/.10/.25/nominal diagnostic is `.tmp/stage4h/quantile-sweep-corrected.json` (file SHA-256 `288f87a42df57e111d4f6bee7a94c04e6b9292a123e95106c72e9ab2d9cf2565`). Alpha=.05 and nominal each differ from primary on one of 14 arm trajectories; alpha=.25 agrees on all 14. Alpha=.10 remains primary.

The independent validity ledger is `LINK-CLOSURE-LEDGER-2026-09-09.md`; it closes 19.196747 dB C/N at boresight and 9.851770 dB at the half-power edge and reproduces 618.475972 Mbit/s beam capacity with n=13 as the first 50-Mbit/s occupancy infeasible at any SINR.

## Metric and deployability boundary

Pooled successfully decoded forward-downlink information bits per joule of modelled partial-payload DC energy, comprising user-link PA supply, the declared per-beam chain circuitry and a declared common processing increment, with explicitly stated idle states; spacecraft bus, unmodelled payload functions, feeder and inter-satellite links, and ground/terminal energy are outside this metric.

`eta_max` is saturation efficiency, not realised efficiency. One beam to one switchable RF chain and the common processing increment are modelling assumptions. Traffic is full-buffer decodable throughput; the 50-Mbit/s target is a power-control setpoint, not demand. Profile application is ideal and simultaneous; partial execution can reverse an evacuation benefit.

## Remaining signature conditions

- Final `tests/physics_v025`: 178 passed; `git diff --check`: pass. Launcher and code-authority hashes are recorded above.
- The controller must review and sign this package; opening artifacts is not a launch signature.
- Formal a-r0 units must use the frozen manifests, calibration, allocation and `k=1`; exploratory settings remain downstream of the primary result.
- The named `V025-ACM-DEFECT-CONFIRMATION-2026-09-09.md` was not present in this workspace. The available audit plus the user's confirmed disposition are the implementation authority.
