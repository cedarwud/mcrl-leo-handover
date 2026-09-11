**Clean pooled EE is `RANDOM` 11.233999, `ROUND_ROBIN` 3.441227, `RSS_MAX` 41.621560, `NEAREST_ELIGIBLE` 11.027760, `MYOPIC_GREEDY` 31.078504, and `FIRST_IMPROVEMENT_FP` 31.028111 Mbit/J; only the two search arms moved from their published values, and `RSS_MAX` remains highest.**

# Static baseline family on the clean evaluator path — 2026-09-10

`DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM`. No learner checkpoint, learner output, or loss value was read. Loss values are not evidence about EE. Only the 12 frozen development anchors were read; no evaluation-only claim date was read. No sealed artefact was changed, and the contaminated `STATIC-BASELINE-FAMILY-2026-09-10.md` remains untouched.

## Verified by running code

### Exact evaluator path

The final runner imported the sealed `PANELCEIL` construction helpers, reconstructed the same frozen anchors in declared order, built the same `V025_PROBE/world/1` tape, used the complete boundary-0 legal set, `a-r0` corrected provisioning, and each anchor's declared prior-step incumbent. The numerator is full-buffer successfully decoded forward-downlink information bits with no demand cap. Pooled EE is `sum(bits) / sum(joules)`.

For each objective-search arm at each anchor, `dense_search` constructed exactly one fresh `StepEvaluator` with `boundary_indices=(0,)` and the arm's declared field. It called `evaluate_many((BASE,))` before reading any profile; all ordered candidate microbatches then entered that same evaluator through `evaluate_many`. Profiles were read only from `StepEvaluator._evaluated`. `MYOPIC_GREEDY` used nominal field, exact best choice, and one ascending-user sweep. `FIRST_IMPROVEMENT_FP` used realised field, first strict guarded improvement, and repeated passes through its terminal zero-move certificate.

The runner replaced `StepEvaluator.evaluate` with a fail-closed function that increments a counter and raises `AssertionError`, then asserted at completion that the counter was zero. The verified count was **zero scalar `evaluate` calls** across selection and reporting.

After both searches and all four direct choices were fixed, endpoint scoring constructed one separate fresh realised `StepEvaluator` with all 48 boundary indices and made exactly one `evaluate_many` call containing the six selected configurations. Endpoint profiles were then read from that dense cache.

### Published versus clean scale

Differences use the exact published receipt values, not subtraction of six-decimal display strings.

| arm | touches selection evaluator? | published EE | clean EE | clean − published | published config IDs retained | value moved? |
|---|---|---:|---:|---:|---:|---|
| `RANDOM` | **No** — seeded legal-option draw only | 11.233999490 | 11.233999490 | +0.000000000 | 12/12 | no |
| `ROUND_ROBIN` | **No** — legal-beam load counts only | 3.441227181 | 3.441227181 | +0.000000000 | 12/12 | no |
| `RSS_MAX` | **No** — boundary-0 `nominal_gain` only | 41.621559817 | 41.621559817 | +0.000000000 | 12/12 | no |
| `NEAREST_ELIGIBLE` | **No** — reconstructed carrier-conditioned `BASE` only | 11.027760228 | 11.027760228 | +0.000000000 | 12/12 | no |
| `MYOPIC_GREEDY` | **Yes** — nominal boundary-0 objective search | 28.668530187 | 31.078503908 | **+2.409973721** | 8/12 | **yes** |
| `FIRST_IMPROVEMENT_FP` | **Yes** — realised boundary-0 objective search | 13.430252782 | 31.028111071 | **+17.597858289** | 0/12 | **yes** |

This verifies rather than assumes the split: all four direct-rule configurations and pooled endpoints are unchanged exactly in binary64 receipt arithmetic; only the two arms that consult the selection evaluator changed. `NEAREST_ELIGIBLE` retains the published parity label: it is the exact carrier-conditioned `BASE` across nearest-eligible, stay-if-possible, and random-masked anchors, not a nearest-only reassignment of all 12 rows.

### Clean pooled endpoints and diagnostics

`modal_frac`, active beams, and active satellites are reported as the 12-anchor mean followed by `[minimum, maximum]`. Served and target counts use all 1,200 anchor-users.

| arm | pooled bits | pooled joules | pooled EE (Mbit/J) | served PHY | rate-target attained | `modal_frac` | active beams | active satellites |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `RANDOM` | 1.288605626013e12 | 114705.864740 | 11.233999 | 1102/1200 (91.833%) | 141/1200 (11.750%) | 0.0333 [0.02, 0.05] | 81.750 [72, 86] | 8.583 [8, 9] |
| `ROUND_ROBIN` | 7.537530520000e11 | 219036.120671 | 3.441227 | 798/1200 (66.500%) | 48/1200 (4.000%) | 0.0100 [0.01, 0.01] | 100.000 [100, 100] | 4.750 [4, 5] |
| `RSS_MAX` | 1.653612586627e12 | 39729.712050 | 41.621560 | 1200/1200 (100.000%) | 297/1200 (24.750%) | 0.0500 [0.05, 0.05] | 47.750 [46, 50] | 5.000 [5, 5] |
| `NEAREST_ELIGIBLE` | 1.121297101614e12 | 101679.495970 | 11.027760 | 960/1200 (80.000%) | 127/1200 (10.583%) | 0.0425 [0.02, 0.05] | 57.333 [41, 90] | 5.333 [3, 9] |
| `MYOPIC_GREEDY` | 1.558660774521e12 | 50152.374745 | 31.078504 | 1200/1200 (100.000%) | 284/1200 (23.667%) | 0.0317 [0.01, 0.05] | 93.583 [86, 100] | 8.083 [7, 9] |
| `FIRST_IMPROVEMENT_FP` | 1.623572418390e12 | 52325.854277 | 31.028111 | 1200/1200 (100.000%) | 342/1200 (28.500%) | 0.0425 [0.03, 0.05] | 86.167 [75, 91] | 8.333 [8, 9] |

### Search movement by anchor

Each cell is `accepted moves / total passes`. For the fixed point, total passes includes the terminal zero-move certificate. The one-sweep myopic arm has one pass by definition. “Published” comes from the validated published static receipt; “clean” was rerun here.

| anchor | carrier | myopic published | myopic clean | fixed point published | fixed point clean |
|---:|---|---:|---:|---:|---:|
| 0 | nearest-eligible | 96 / 1 | 96 / 1 | 0 / 1 | **377 / 10** |
| 1 | stay-if-possible | 96 / 1 | 96 / 1 | 0 / 1 | **377 / 10** |
| 2 | random-masked | 94 / 1 | 94 / 1 | 0 / 1 | **386 / 11** |
| 3 | nearest-eligible | 0 / 1 | **97 / 1** | 0 / 1 | **346 / 9** |
| 4 | stay-if-possible | 92 / 1 | **95 / 1** | 0 / 1 | **377 / 11** |
| 5 | random-masked | 92 / 1 | **94 / 1** | 0 / 1 | **377 / 11** |
| 6 | nearest-eligible | 90 / 1 | 90 / 1 | 0 / 1 | **316 / 9** |
| 7 | stay-if-possible | 98 / 1 | 98 / 1 | 345 / 10 | **346 / 10** |
| 8 | random-masked | 90 / 1 | 90 / 1 | 0 / 1 | **345 / 14** |
| 9 | nearest-eligible | 84 / 1 | 84 / 1 | 0 / 1 | **315 / 9** |
| 10 | stay-if-possible | 98 / 1 | 98 / 1 | 354 / 12 | **346 / 9** |
| 11 | random-masked | 71 / 1 | **84 / 1** | 0 / 1 | **302 / 9** |
| **total** | — | **1,001 / 12** | **1,116 / 12** | **699 / 32** | **4,210 / 122** |

The clean myopic sweep changed configuration at 4/12 anchors relative to the publication and retained 8/12 configuration IDs. The clean fixed point changed configuration at 12/12 anchors, moved at all 12, and required 9–14 passes per anchor. The published fixed point moved at only 2/12 anchors. Therefore the published “barely moved” description does not survive the clean path: accepted moves rise from 699 to 4,210 and total passes from 32 to 122.

### Execution and machine evidence

The successful run emitted `anchor 1/12` through `anchor 12/12`, used one Python process at niceness 15, and pinned `OMP`, `OPENBLAS`, `MKL`, `NUMEXPR`, `VECLIB`, and `BLIS` threads to 1. It completed in 865.372 s including 179.790 s of shared tape construction. Peak RSS was **2.629 GiB (2,822,586,368 bytes)**, below 5 GB. The run finished before the stated training landings.

```text
eb0963732d15873d09247a11ecd53cd7a9a2e27bbc2bfb25c9d21635a1c9f6a0  .scratch/cleanpath/run_cleanpath.py
06285db20ee885700a0cfbf74c550f539d94bf2a9114c68ba7ac7df44a9f7fe7  .scratch/cleanpath/cleanpath-receipt.json  [file SHA-256]
d5f298df3e863ee77b37bffa56e5f8675a06dfd905ef84585cb0eefdd3d77530  .scratch/cleanpath/cleanpath-receipt.json  [canonical content digest]
dd81d45b6cc81291518aaa5fd1276be99d2f0f9d818c4445054620d3f0dc93a5  published static receipt [read-only file SHA-256]
```

World tape: domain `V025_PROBE/world/1`, seed `5261619120743994529`, digest `43718040fd7157edc158a8f8cd32418c619dacae1ef1114094f115805f027bf0`.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/cleanpath/run_cleanpath.py
```

## Derived on paper from verified aggregates

- `RSS_MAX / FIRST_IMPROVEMENT_FP = 1.341414555x`: `RSS_MAX` is still highest by **10.593448746 Mbit/J**, or **34.141456%** over the clean fixed point. The relevant clean margin is therefore **1.341x**, not the contaminated 3.099x comparison.
- `RANDOM - NEAREST_ELIGIBLE = 0.206239263 Mbit/J`; `RANDOM / NEAREST_ELIGIBLE = 1.018701827x`. Thus `RANDOM` still beats `NEAREST_ELIGIBLE`, by **1.870183%**.
- `MYOPIC_GREEDY` increases by 2.409973721 Mbit/J, or 8.406% relative to its exact published value.
- `FIRST_IMPROVEMENT_FP` increases by 17.597858289 Mbit/J, or 131.031% relative to its exact published value.

These are arithmetic relations among the verified full-buffer pooled aggregates. They are not learner claims and are not inferred from losses.

## Inferred

The clean measurement sharply localises what survives. The published values for the four non-objective direct rules survive exactly; the published values and movement story for both objective-search arms do not. The reference family still spans a wide 3.441227–41.621560 Mbit/J, but its two clean search points now form a tight pair near 31.0 Mbit/J rather than the published 28.7-versus-13.4 split.

`RSS_MAX` remains the strongest of these six measured static arms, though its advantage over the clean fixed point is much smaller than today's contaminated comparison suggested. `RANDOM` also remains above the carrier-conditioned base. These development-anchor observations rank no learned arm and establish no evaluation-only claim.
