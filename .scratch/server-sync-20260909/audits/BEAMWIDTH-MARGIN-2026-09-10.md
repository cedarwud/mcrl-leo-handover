**No. Under margin provisioning, the coordination gap does not rise monotonically with beam width: the corrected curve is `−0.303%, +1.209%, +0.985%, +3.205%, +7.315%`, versus the sealed curve `+6.502%, +10.397%, +11.563%, +14.639%, +41.949%`.**

# Beam-width sweep under margin provisioning

`DIAGNOSTIC_NOT_CLAIM`

## Direct finding

The corrected five-point curve is not monotone: it rises from 1.66° to 2.40°, dips at the source-width point, and then rises at 4.50° and 6.65°. The sealed monotone rise therefore does not survive as stated. The corrected gap does not disappear, however: it remains materially positive at the two widest sampled points. These are curves over the fixed panel, not a ranking of antenna widths.

All five corrected points reached the required 8/8 anchors (40/40 total). No point was omitted. Each point uses 100 users at steps 0–3 from `V025_PROBE_R2/world/1` and `/2`, for 800 user-steps per point.

| One-sided angle | Full span used | Sealed joint/U gap | Negative anchors | Margin joint/U gap | Negative anchors |
|---:|---:|---:|---:|---:|---:|
| 1.66° | 3.32° | 6.50% | 0/8 | -0.30% | 5/8 |
| 2.40° | 4.80° | 10.40% | 0/8 | 1.21% | 0/8 |
| 3.32° | 6.64° | 11.56% | 1/8 | 0.98% | 2/8 |
| 4.50° | 9.00° | 14.64% | 0/8 | 3.21% | 2/8 |
| 6.65° | 13.30° | 41.95% | 0/8 | 7.32% | 3/8 |

Pooled EE is `sum(bits) / sum(joules)`. A negative-anchor count uses each anchor's independently committed 48-boundary EE; it can be nonzero even though the joint configuration has a positive boundary-0 selection-objective certificate.

## EE and service, both rules

`B`, `U`, and `J` mean neutral BASELINE, terminal iterated UNILATERAL, and bounded ORACLE_SET. Served means positive decoding time. Target means the count whose integrated achieved rate attains 50 Mbit/s. They are reported separately throughout.

| Rule | One-sided / full | EE B / U / J (Mbit/J) | Served B / U / J (of 800) | 50-Mbit/s target B / U / J (of 800) |
|:---|:---:|:---|:---|:---|
| SEALED | 1.66° / 3.32° | 3.861 / 26.762 / 28.502 | 313 / 779 / 790 | 0 / 0 / 0 |
| SEALED | 2.40° / 4.80° | 3.698 / 25.520 / 28.174 | 334 / 761 / 774 | 0 / 0 / 0 |
| SEALED | 3.32° / 6.64° | 1.387 / 28.956 / 32.304 | 203 / 701 / 729 | 0 / 0 / 0 |
| SEALED | 4.50° / 9.00° | 0.315 / 19.449 / 22.297 | 56 / 528 / 607 | 0 / 0 / 0 |
| SEALED | 6.65° / 13.30° | 0.149 / 3.146 / 4.466 | 19 / 158 / 220 | 0 / 0 / 0 |
| MARGIN | 1.66° / 3.32° | 8.122 / 42.298 / 42.170 | 452 / 800 / 800 | 174 / 550 / 541 |
| MARGIN | 2.40° / 4.80° | 6.410 / 42.637 / 43.153 | 413 / 800 / 800 | 131 / 487 / 474 |
| MARGIN | 3.32° / 6.64° | 2.775 / 44.029 / 44.462 | 230 / 800 / 800 | 60 / 443 / 434 |
| MARGIN | 4.50° / 9.00° | 0.961 / 42.094 / 43.443 | 77 / 781 / 781 | 24 / 338 / 337 |
| MARGIN | 6.65° / 13.30° | 0.376 / 34.334 / 36.846 | 28 / 694 / 722 | 9 / 258 / 269 |

Under the sealed rule, none of the 4,000 user-steps for any selector attains the rate target (`0/12,000` selector/user-step results), even though many are counted as served. Under margin provisioning the target count becomes nonzero at every width and for every selector.

## Boundary, interference, and occupancy diagnostics

A cap boundary is one of the 384 anchor-boundaries at a point where at least one active TDM transmission reaches the 1.65-W per-beam cap. A no-mode boundary is one where at least one active transmission has no eligible ACM mode. Brackets give the separate transmission-attempt share, preventing a single event from being confused with all attempts on that boundary. Interference-limited share is `interference-limited / infeasible user-steps`; top-1 is the weighted strongest-aggressor share over failing transmissions of those interference-limited user-steps. Mean occupancy is pooled across occupied realised beam-boundary cells; maximum is the realised maximum.

| Rule | Width | Selector | Cap boundaries [attempts] | No-mode boundaries [attempts] | Interference-limited | Top-1 aggressor | Mean / max occupancy |
|:---|---:|:---:|---:|---:|---:|---:|---:|
| SEALED | 1.66° | B | 100.00% [41.28%] | 100.00% [78.81%] | 76.34% | 66.66% | 2.462 / 7 |
| SEALED | 1.66° | U | 98.70% [15.17%] | 91.15% [9.47%] | 91.18% | 71.83% | 4.324 / 11 |
| SEALED | 1.66° | J | 97.40% [13.05%] | 91.15% [6.72%] | 91.37% | 75.31% | 4.444 / 11 |
| SEALED | 2.40° | B | 100.00% [57.78%] | 100.00% [83.38%] | 100.00% | 49.78% | 2.462 / 7 |
| SEALED | 2.40° | U | 100.00% [32.88%] | 93.49% [21.74%] | 81.15% | 65.22% | 4.848 / 21 |
| SEALED | 2.40° | J | 100.00% [29.27%] | 87.76% [18.71%] | 74.53% | 62.57% | 4.969 / 21 |
| SEALED | 3.32° | B | 100.00% [66.05%] | 100.00% [89.27%] | 100.00% | 39.85% | 2.462 / 7 |
| SEALED | 3.32° | U | 100.00% [29.00%] | 88.80% [18.42%] | 63.81% | 56.70% | 5.926 / 17 |
| SEALED | 3.32° | J | 100.00% [26.31%] | 82.03% [14.86%] | 55.09% | 59.91% | 6.061 / 17 |
| SEALED | 4.50° | B | 100.00% [81.27%] | 100.00% [96.81%] | 100.00% | 31.34% | 2.462 / 7 |
| SEALED | 4.50° | U | 100.00% [40.31%] | 100.00% [35.80%] | 58.46% | 31.93% | 5.755 / 15 |
| SEALED | 4.50° | J | 100.00% [38.27%] | 100.00% [28.54%] | 53.20% | 30.85% | 5.753 / 15 |
| SEALED | 6.65° | B | 100.00% [85.54%] | 100.00% [97.74%] | 100.00% | 22.73% | 2.462 / 7 |
| SEALED | 6.65° | U | 100.00% [77.06%] | 100.00% [80.51%] | 92.87% | 26.51% | 4.103 / 13 |
| SEALED | 6.65° | J | 100.00% [70.96%] | 100.00% [72.29%] | 92.47% | 26.88% | 4.124 / 13 |
| MARGIN | 1.66° | B | 100.00% [57.63%] | 100.00% [48.49%] | 64.05% | 66.16% | 2.462 / 7 |
| MARGIN | 1.66° | U | 32.29% [0.67%] | 11.20% [0.09%] | 90.00% | 86.99% | 2.121 / 7 |
| MARGIN | 1.66° | J | 35.42% [0.86%] | 9.90% [0.12%] | 91.92% | 82.65% | 2.121 / 7 |
| MARGIN | 2.40° | B | 100.00% [67.06%] | 100.00% [55.45%] | 97.89% | 54.14% | 2.462 / 7 |
| MARGIN | 2.40° | U | 51.56% [2.83%] | 8.59% [0.10%] | 99.32% | 91.21% | 2.667 / 7 |
| MARGIN | 2.40° | J | 41.41% [2.63%] | 7.55% [0.09%] | 99.24% | 91.89% | 2.684 / 7 |
| MARGIN | 3.32° | B | 100.00% [85.06%] | 100.00% [78.84%] | 100.00% | 42.69% | 2.462 / 7 |
| MARGIN | 3.32° | U | 59.38% [5.61%] | 12.24% [0.12%] | 82.39% | 95.56% | 3.149 / 13 |
| MARGIN | 3.32° | J | 55.21% [5.38%] | 13.54% [0.16%] | 84.02% | 95.93% | 3.174 / 13 |
| MARGIN | 4.50° | B | 100.00% [91.24%] | 100.00% [88.48%] | 100.00% | 32.98% | 2.462 / 7 |
| MARGIN | 4.50° | U | 71.61% [10.13%] | 18.49% [2.80%] | 76.53% | 60.92% | 3.652 / 11 |
| MARGIN | 4.50° | J | 68.75% [8.31%] | 22.66% [2.21%] | 75.49% | 54.75% | 3.685 / 11 |
| MARGIN | 6.65° | B | 100.00% [96.28%] | 100.00% [95.67%] | 100.00% | 23.72% | 2.462 / 7 |
| MARGIN | 6.65° | U | 79.95% [18.83%] | 55.21% [12.13%] | 63.44% | 61.95% | 3.981 / 11 |
| MARGIN | 6.65° | J | 78.39% [15.62%] | 50.52% [7.87%] | 62.74% | 53.24% | 4.041 / 13 |

## 1.66° model point versus the source-width point

The evaluated source-width grid point is the requested rounded one-sided `3.32°`, so its runtime full span is `6.64°`. The paper's exact Table-I value is `0.058 rad`, implying one-sided `3.323155°` and full span `6.646310°`; the exact-value distinction is provenance context, not an extra sixth sweep point.

At corrected 3.32° one-sided, pooled EE is **2.775 / 44.029 / 44.462 Mbit/J** for B/U/J, and the joint-over-unilateral gap is **+0.985%**, with **2/8** negative anchors. Served counts are **230 / 800 / 800**; the separate 50-Mbit/s target counts are **60 / 443 / 434**.

Compared with corrected 1.66° one-sided, served changes by **−222 / 0 / 0** for B/U/J (`452/800/800 → 230/800/800`), while target attainment changes by **−114 / −107 / −107** (`174/550/541 → 60/443/434`). Thus the optimized selectors still touch every user-step at the source-width point, but substantially fewer attain the requested rate.

At 3.32°, cap-boundary shares are **100.00% / 59.38% / 55.21%**, no-mode-boundary shares are **100.00% / 12.24% / 13.54%**, interference-limited shares are **100.00% / 82.39% / 84.02%**, top-1 shares are **42.69% / 95.56% / 95.93%**, and mean/max occupancies are **2.462/7, 3.149/13, 3.174/13** for B/U/J.

## Does wider beam buy coordination value by degrading service?

**In the wide-beam regime, yes; across all five points, not as a monotone one-for-one law.** The corrected gap falls slightly from +1.209% at 2.40° to +0.985% at 3.32° while target attainment also falls, so every service loss does not buy more set-level value. From 3.32° through 4.50° to 6.65°, however, the gap rises `0.985% → 3.205% → 7.315%` as optimized service degrades and cap/no-mode exposure increases.

| One-sided width | Corrected gap | Served U / J | Target U / J | Cap-boundary U / J | No-mode-boundary U / J |
|---:|---:|:---:|:---:|:---:|:---:|
| 1.66° | -0.30% | 800 / 800 | 550 / 541 | 32.29% / 35.42% | 11.20% / 9.90% |
| 2.40° | 1.21% | 800 / 800 | 487 / 474 | 51.56% / 41.41% | 8.59% / 7.55% |
| 3.32° | 0.98% | 800 / 800 | 443 / 434 | 59.38% / 55.21% | 12.24% / 13.54% |
| 4.50° | 3.21% | 781 / 781 | 338 / 337 | 71.61% / 68.75% | 18.49% / 22.66% |
| 6.65° | 7.32% | 694 / 722 | 258 / 269 | 79.95% / 78.39% | 55.21% / 50.52% |

For U/J, cap-boundary exposure rises overall from `32.29%/35.42%` at 1.66° to `79.95%/78.39%` at 6.65°. Target attainment falls `550/541 → 258/269`; served falls `800/800 → 694/722`. At the widest point, the joint selector serves 28 more user-steps and has 11 more target-attaining user-steps than unilateral, while retaining a +7.315% pooled EE gap. This quantifies the service/coordination regime without ranking a width.

## Controls and trust checks

Before any margin point was run, the private margin evaluator was set to an all-ones provisioning divisor. Across all five sealed receipts it matched **every ndarray field bit-for-bit** for all 40 anchors and all 120 recorded committed configurations, both at boundary 0 and over the complete 48-boundary grid. The receipt-recorded bits, joules, and served counts also matched exactly. The machine-readable assertion is `.scratch/beamwidth/divisor-one-identity.json`.

Only the provisioning target changes in the margin runs: `Gamma(n)` becomes `Gamma(n) / q_0.10(e)`. The same quantile remains in transmitted-mode selection. All signs, seeds, horizons, prices, service guard, acceptance rule, rate target, per-beam cap, anchor identities, 100-user populations, unilateral ordering and strict-improvement rule, terminal certificate, joint families and catalogue caps, and 48-boundary committed scoring are unchanged. The two deterministic seeds are `3525272352645343090` and `3445540383109071487`; the corresponding TLE dates are `2026-05-30` and `2025-07-28`. The override is private and runtime-only; no sealed constant, sealed artefact, frozen manifest, source engine file, or other workspace was modified.

The neutral baseline is nearest-eligible. UNILATERAL is deterministic cyclic exact best response under `F = B − eta_ref E`, with `eta_ref = 19,720,681.00172232 bit/J`, until a full pass contains no strictly improving legal move. ORACLE_SET is the same bounded catalogue: same-beam occupant subsets of size 2–4 (1,024-generation cap), victim plus top-2/top-3 physical contributors, and complete-beam evacuations, under the 4,096 global cap. UNILATERAL remains the included reference and the selection-time served count may not fall below the point's baseline.

## Exact reproduction commands

Run from `/home/sat/mcrl-v025-beam-ws`:

```bash
nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/beamwidth/assert_divisor_one.py \
  .scratch/beamwidth/sweep-one-sided-{1.66,2.40,3.32,4.50,6.65}.json \
  --output .scratch/beamwidth/divisor-one-identity.json

for hp in 1.66 2.40 3.32 4.50 6.65; do
  nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/beamwidth/run_beamwidth_network.py \
    --worlds 2 --anchors-per-world 4 --one-sided-hp-deg "$hp" --provisioning-rule margin \
    --output ".scratch/beamwidth/margin-sweep-one-sided-${hp}.json"
done

nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/beamwidth/replay_sealed_diagnostics.py \
  .scratch/beamwidth/sweep-one-sided-{1.66,2.40,3.32,4.50,6.65}.json \
  --output-dir .scratch/beamwidth

nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/beamwidth/build_margin_report.py
```

The margin receipts are `.scratch/beamwidth/margin-sweep-one-sided-{1.66,2.40,3.32,4.50,6.65}.json`; the sealed diagnostic replays are `.scratch/beamwidth/sealed-diagnostics-one-sided-{1.66,2.40,3.32,4.50,6.65}.json`. Each receipt embeds the anchor rows, exact selector configurations, selection certificates, physical evaluation counts, source/tree identifiers, and internal receipt digest where applicable.

## Receipt file SHA-256

```text
6f95606027044659c5663e60df17ae1c5fc07b280bebb590ebfa905aedea2bae  .scratch/beamwidth/divisor-one-identity.json
6c59865691761d43b15c33559c663e515d6ef34bef75aa6f62c122543abd2e2e  .scratch/beamwidth/sealed-diagnostics-one-sided-1.66.json
c62694552e8067bd3f012692daa7e7fbb955b502a5fefb240870712192acf84d  .scratch/beamwidth/sealed-diagnostics-one-sided-2.40.json
11aed2f2eade418be7ae57196c2e46e49bdbc1c20170323ac0aee8188c68dd5c  .scratch/beamwidth/sealed-diagnostics-one-sided-3.32.json
d0f6ad3f7e84ee62c56ff9759299a27f2ab3f3f63a738c5ae79b4fa1940aba5a  .scratch/beamwidth/sealed-diagnostics-one-sided-4.50.json
af8400e6ace98261f10f5b21dde69100df9421ab5bbe8cbd22f1447035b866a3  .scratch/beamwidth/sealed-diagnostics-one-sided-6.65.json
b393b027386536faac640472479bf38d6307fd252a7d215aadf372ceeb7f48dd  .scratch/beamwidth/margin-sweep-one-sided-1.66.json
22fd4fa25e5b3007ac24d9c96b282679909a0a21af109cebc209aac495837b55  .scratch/beamwidth/margin-sweep-one-sided-2.40.json
12325852aa2b5ddc23b0051538f25ee85ab7c46d88db87d508cc46401acbc4a5  .scratch/beamwidth/margin-sweep-one-sided-3.32.json
29e884cd20656d41462e9ba791639bbff23af341dd1fe2d11a761c63ab4d08ba  .scratch/beamwidth/margin-sweep-one-sided-4.50.json
4777eb7f363a7e9a3a7af3527358532b11519cd746d657bd5b06ba75b30dd59f  .scratch/beamwidth/margin-sweep-one-sided-6.65.json
23caf911e865a9da053f5fd617c48f08556594e951a6aec653d06ed75f3cbd32  .scratch/beamwidth/margin_batch.py
1904bbb127afdf5fd597d142be7d7bc32cacf6be47ae8e56b932f47bde91fa34  .scratch/beamwidth/run_beamwidth_network.py
51d78a5c2d19306284d2b2f9308cab9627725307e73b7f08d6bb45f3a1aaf2c0  .scratch/beamwidth/assert_divisor_one.py
281383db62134d25284dd3e59df4a7c50939df4eba77c2c7854d1ec35b4df54b  .scratch/beamwidth/replay_sealed_diagnostics.py
d5e8974f97c9b42d65368781fd1d07186dcfa9f572ef1aab39f1e617e9673189  .scratch/beamwidth/build_margin_report.py
```
