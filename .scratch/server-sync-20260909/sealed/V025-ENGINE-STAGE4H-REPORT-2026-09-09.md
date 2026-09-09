# V0.25 engine stage 4h report — 2026-09-09

Status: `IMPLEMENTED / 178 TESTS PASS / REAL-ANCHOR GATE PASS / FORMAL STEPS OPEN`. All work is TRAIN-only. No file under `src/mcrl/env/` was changed, and no TEST or claim-panel outcome was opened.

## 1. Interrupted stage-4e completion

The failing rekey-estimator test was caused by two mathematically equivalent availability values taking different floating-point routes. The runner passed `useful = fsum(receipt useful times)` but reconstructed `decoding = receipt availability * opportunity`; JSON round-tripping made these differ by one ULP (`31.040000000000013 < 31.040000000000017`), so `StepEndpoint` correctly rejected the apparent ordering violation. Both quantities now use the same receipt-ledger reconstruction. No test was deleted.

Stage 1 and stage 2 evaluate deterministic round-robin shards in four worker processes, then reduce results in catalogue order. The serial/parallel KAT checks profiles, invalid sets, forecasts, receipts and physical-evaluation counts for exact equality. The sealed stage-4e fallback is one forecast boundary per offset and M=48 after the five-boundary/M=64 and one-boundary/M=64 surfaces missed the ten-second selection gate.

## 2. Sealed v1.6-v1.9 amendments

- Predicted and executed RF power are derived from nominal gains. The complete-product fading quantile affects only wanted-link predicted reception; nominal interference is unchanged.
- The quantile implementation uses 200,000 deterministic draws of Rician power × lognormal shadow × deterministic scintillation, a SHA-256 domain-derived seed, nearest 0.5-degree elevation bins, and a `(bin, alpha)` cache. The direct/cached conformance KAT is within 1e-3 relative.
- Set selection, per-arm top-M pruning and deterministic tie handling use FULL=`C1+C3` then C2, DROP_C1=`C3` then C2, DROP_C2=`C1+C3` then configuration ID, and DROP_C3=`C1` then C2. A 1e-9 relative tolerance defines primary-score and C2 ties.
- C2's physics certificate is forecast validity. The receipt reports tie count/frequency and accepts the expected zero set-level selection marginal when the immediate maximiser is unique.
- Selection-time margin decomposition and realised 48-boundary outcome decomposition are separately named and never mixed. Every selected coalition receives its O(|A|) interaction label; only exact per-user Shapley reporting is capped at |A|<=4.
- The monotone `ADMIT_FULL` / `ADMIT_C1C2` / `NOT_ADMITTED` implementation has an eight-state truth-table KAT.
- Receipt headers carry the exact partial-payload energy-boundary sentence. They identify `eta_max` as saturation efficiency, the one-beam/one-chain and processing terms as assumptions, full-buffer throughput and rate target semantics, ideal simultaneous application, and receipt/publication-time causality.

## 3. Confirmed ACM correction

The audit finding is confirmed: the former engine selected credited MODCOD from realised post-fading SINR, while the power target and decoder used the same threshold, so the 1.7 dB implementation margin cancelled. The corrected path emits `m_target`, `m_tx` and `realised_outcome` separately. `m_target` sets nominal power; `m_tx` is chosen from the alpha=.10 wanted-link margin view; bits are credited at `m_tx` only when realised SINR clears `threshold(m_tx)`, otherwise zero.

Paired two-anchor quarantined SMOKE, same BASE profiles and powers:

| semantics | availability | bits | joules | pooled EE (bit/J) |
|---|---:|---:|---:|---:|
| old realised/genie ACM | 0.791277 | 240,072,304,316.296 | 12,675.247090 | 18,940,246.499 |
| corrected causal ACM | 0.453138 | 71,728,548,992.593 | 12,675.247090 | 5,658,946.803 |

Evidence: `probe/ACM-CAUSAL-BEFORE-AFTER-SMOKE-2026-09-09.md` and immutable `.tmp/stage4h/acm-before-after.json` (receipt `5fa975a282bfb319933ab01eb31c0430c0af904987d05593b53c3efdfd48e2c9`).

## 4. Independent link closure

`probe/build_stage4h_link_ledger.py` imports no `mcrl` module and evaluates the scalar link equation. At the 1.65 W cap, C/N is 19.196747 dB at 550-km boresight and 9.851770 dB at the 1,100-km half-power edge. The isolated TDM fixture has C/I=+infinity; occupancy changes airtime and target MODCOD, not instantaneous intra-beam interference. Its n=1/2/4 target power, q10 wanted-link mode, lowest-mode and simulator-flag reconciliation are in `probe/LINK-CLOSURE-LEDGER-2026-09-09.md`.

The independent maximum is 618.475972 Mbit/s per colour beam. Twelve 50-Mbit/s users are mode-feasible; 13 users require 650 Mbit/s and are infeasible at any SINR, exactly matching the audit.

## 5. Closed-loop quantile robustness SMOKE

The corrected immutable sweep is `.tmp/stage4h/quantile-sweep-corrected.json` (file SHA-256 `288f87a42df57e111d4f6bee7a94c04e6b9292a123e95106c72e9ab2d9cf2565`, receipt `4b8bb4ce3f106127ad2f03cf610047685a408aa845f9124086a0f747a4f898a6`). It uses common `V025_SMOKE/world/1` exogenous data, two closed-loop anchors, 14 independently carried arm states, four workers, deadline/fallback accounting and realised 48-boundary endpoints.

| selector | trajectory agreement with alpha=.10 | difference |
|---|---:|---|
| alpha=.05 | 13/14 | E1_U1, +38,019.128 bit/J |
| alpha=.10 primary | 14/14 | reference |
| alpha=.25 | 14/14 | none |
| unchanged nominal | 13/14 | NOMINAL_GREEDY, -10,027,588.356 bit/J |

Alpha=.10 remains primary by preregistration; the sweep does not select it. Full detail is in `probe/QUANTILE-SWEEP-SMOKE-2026-09-09.md`.

## 6. Real-anchor gate

Final gate surface: declared four worker processes, deterministic one-boundary/M=48 fallback, real legacy provider, quarantined world 1, a-r0, all 14 arms. The host exposed one physical CPU to the sandbox, so the four processes were time-sliced; this makes the passing result conservative relative to four simultaneously runnable cores.

| anchor | catalogue rows | stage-2 rows | quantile cache | catalogue | stage 1 | stage 2 | selection | validation | coordinator decision | total anchor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 997 | 102 | 1.0546 | 3.4282 | 4.1288 | 0.6930 | 0.0095 | 0.6039 | 9.9206 | 21.3154 |
| 2 | 997 | 102 | 0.0008 | 3.2874 | 4.3057 | 0.6941 | 0.0103 | 0.5794 | 8.8798 | 20.1191 |
| 3 | 966 | 156 | 0.0008 | 1.9174 | 1.9038 | 1.0916 | 0.0159 | 1.0178 | 5.9498 | 20.5407 |

Decision wall time: mean 8.250071 s, p95 9.816495 s, maximum 9.920572 s (`PASS`, all <10 s). Complete-anchor time: mean 20.658408 s, p95 21.237972 s, maximum 21.315449 s (`PASS`, all <60 s). Provider construction was 20.222051 s once. The earlier immutable evidence file accidentally labelled the aggregate 62.115 s for three anchors as `FAIL`; that is not the declared per-decision or per-anchor gate. Its raw times and receipt remain evidence, while this report records the corrected gate interpretation.

## 7. Formal opening

The gate passed before formal opening work began. All six requested domain manifests are open and immutable:

| domain | manifest file SHA-256 | receipt SHA-256 |
|---|---|---|
| V025_PROBE_R2/world/1 | `49daadf842e89ed2d539ca94bd29f51db619a4c709467b4a657dd3afba3dd657` | `564161362bb87b742e4fd2a0f0648032ba5e1fea9061cbb25026963f7c8567dd` |
| V025_PROBE_R2/world/2 | `18eededb2b219da7231b55280be583e40cf19d49ebf6c55e6e8d4350a9e90671` | `e412796b7429e68f26a8dc60263c97848f4730201845ede0195c8a933d0ee088` |
| V025_PROBE_R2/world/3 | `c82286b4e2e330c430880067e917d3682c32448b0b710f208f2c9d267b006232` | `43676e11c355c112db76ada552927c1fa4af7ec1fe14c3fa3b51efa8ff1649c4` |
| V025_PROBE_R2/world/4 | `d7505093b0fe8da3ea126b10a0d38fe200a2ed2f0c4415af90badeecf51720fa` | `9b455bc58db3184a82f3d64131d230af152b2d1cec8bf24a945385d6acc0e7bc` |
| V025_CAL_R2/world/1 | `30c4b378d7058a5608fc0326279f05277bda9a1806c43526548ccdbd4d247f9a` | `61d73944d9e5ad7f30948dc1c7428bfaca14bd7e83df6e6864cf8e8c736407f0` |
| V025_CAL_R2/world/2 | `ec69cf35eb92fc40429ed8c49b8b7d6a450cbaf122734abcb2e8de5ccd4dfaff` | `3d528f924051488c51c7277a06213961f2275b96e29599d05502b190c479fe3e` |

Aggregate probe manifest file SHA-256 is `e7bdb1d4d59d68a05f2b30437ff3c4c9fbcb20ae7e6d28613843ed3bc3fe7165`; aggregate calibration manifest file SHA-256 is `fecc09ebcf1ee89a05183df905d65c851018a53f4dcd7dbcc1719a1328460aa0`.

The a-r0 calibration is the complete 30-step nominal reference rollout on both calibration worlds (60 decision steps, 100 users): `eta_ref = lambda = 19,720,681.00172232 bit/J`, `kappa = 818,607,346.8586777 bit/user-step`, reference bits `4,911,644,081,152.066` and energy `249,060.571525 J`. Its exact rational fields, selected-trajectory digests and receipt `b9fef5bc60849df103679f5d99becda9151106ec0673b79e7162ec3db2d698e0` are frozen in `.tmp/stage4h-formal/calibration-manifest.json`.

Aggregate probe manifest: `.tmp/stage4h-formal/world-manifest.json`, file SHA-256 `e7bdb1d4d59d68a05f2b30437ff3c4c9fbcb20ae7e6d28613843ed3bc3fe7165`.

The allocation manifest contains 24 identities: PROBE 4, CALIBRATION 2, REHEARSAL 1, KAT 8, SYNTHETIC_REAL 4, SMOKE 1 and CLAIM_PANEL 4. It is immutable at `.tmp/stage4h-formal/allocation-manifest.json`, file SHA-256 `2d3e2cb3e34e67f321127e568a8d2d6714c9f5bb4ad8e2fe6ef2d111470fd369`. The initial `V025_CLAIM_PANEL/world/1` reservation resolved to 2026-08-05, already used by calibration world 1, and was rejected. It was replaced prospectively by `V025_CLAIM_PANEL/world/5` (2025-12-05); claim domains 2-5 are fresh from every listed development date. Development-development date overlap remains recorded and permitted. No claim-panel boundary or arm outcome was requested.

The authoritative three-anchor, 14-arm rehearsal took 67.030349 s, 4.468690 core-minutes at four workers, and 15,566 physical boundary evaluations. It records `q = 0.01368859093`. The direct 4 worlds x 90 anchors projection is 8.937380 core-hours; with four workers/unit and concurrency 20, five units run concurrently for an ideal wall time of 26.812140 minutes. Both the 10-core-minute rehearsal and 160-core-hour projection gates pass, so the smallest sealed stride is `k=1`. The immutable receipt is `.tmp/stage4h-formal-q/rehearsal.json`, file SHA-256 `06d6a0dd292b6ac7f37efe47bf0fccccb8f56fa39395a7f0a2b7e584d701fcf7`, unit receipt `3090021b89e254c0cbc45ad53fc77dc6d1e0696a40698e8e4fb23d08a7338f03`. The earlier `.tmp/stage4h-formal/rehearsal.json` is superseded only because its schema computed but omitted `q`.

The ten-anchor development run is immutable at `.tmp/stage4h-formal/smoke/a-r0-world-1.json`, status `SMOKE_NOT_MATRIX`, file SHA-256 `f772877da8fb2fcd45d626c92a3bf8725fc47326c90ad8529977cac0695dceed`, receipt `a39b0c174118374bfb04640affed08e80b243d1f4b28353fa42e038cb42e82d9`. It took 233.028850 s, or 15.535257 four-worker core-minutes, below the 60-core-minute limit. Catalogue counts were 966-997 with zero coarse-shortlist misses.

| arm | Gbit | J | Mbit/J | availability | lit-beam s | RF-cap share | deadline misses | certificate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| E1_U1 | 275.490219 | 72,393.667 | 3.805446 | 0.342064 | 16,243.2 | 0.198787 | 0 | CONVERGED 10/10 |
| E1_J1 | 403.520119 | 31,552.274 | 12.788939 | 0.497691 | 14,468.5 | 0.028431 | 0 | CONVERGED 10/10 |
| UNION_CATALOGUE_OPTIMUM | 403.520119 | 31,552.274 | 12.788939 | 0.497691 | 14,468.5 | 0.028431 | 0 | CONVERGED 10/10 |
| S0_DEPLOYABLE | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 10 | CONVERGED 10/10 |
| FULL | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 10 | CONVERGED 10/10 |
| DROP_C1 | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 10 | CONVERGED 10/10 |
| DROP_C2 | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 10 | CONVERGED 10/10 |
| DROP_C3 | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 10 | CONVERGED 10/10 |
| UNI | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 10 | CONVERGED 10/10 |
| S_UNI | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 6 | CONVERGED 10/10 |
| ALL_NEUTRAL_CONTROL | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 0 | CONVERGED 10/10 |
| NULL | 267.471671 | 76,593.489 | 3.492094 | 0.325160 | 16,483.8 | 0.256705 | 0 | CONVERGED 10/10 |
| RANDOM_FEASIBLE | 268.960317 | 76,761.436 | 3.503847 | 0.331766 | 16,694.4 | 0.218562 | 0 | CONVERGED 10/10 |
| NOMINAL_GREEDY | 410.925199 | 39,948.089 | 10.286479 | 0.503383 | 13,927.0 | 0.088996 | 0 | CONVERGED 10/10 |

`E1_J1 - E1_U1 = +8.983493 Mbit/J`. S0, FULL, all DROP arms, UNI and the carrier controls coincide because every coordinator decision missed its ten-second deadline and fell back to BASE; S_UNI also fell back on 6/10 anchors. Consequently C1/C2/C3 realised marginals and matched `g_A/g_I` are all zero in this SMOKE. C2 forecast validity is false with tie frequency zero; its zero set-level marginal is explicitly accepted, but its certificate does not pass. The causal ACM census, mode counts, decoded/outage totals, rate tails, handovers and full certificate distributions are retained in the immutable receipt. Overall plateau share is 0 and RF-cap transmission share is 0.256705.

## 8. Verification and explicit limitations

- Targeted stage-4d/e/h conformance after the final nominal-control fix: pass.
- Full `tests/physics_v025` result: 178 passed, exit 0.
- `git diff --check`: pass.
- `src/mcrl/env/`: unchanged.
- Commit: complete at Git HEAD (`Finish V0.25 stage 4h physics gate`).
- The prompt names `V025-ACM-DEFECT-CONFIRMATION-2026-09-09.md`, but that file is absent from the workspace. The available `ACM-CAUSALITY-AUDIT-2026-09-09.md` contains the confirmed Q1-Q6 verdict summarized above; implementation follows the user's explicit confirmed disposition.
