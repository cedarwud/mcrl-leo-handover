The joint-over-unilateral gap does not grow systematically with load or rate alone; under their joint increase the strict-margin gap rises from +0.400% (U125/R65) to +0.644% (U150/R80) and +0.978% (U200/R80, 4 anchors), never crossing 1%, while the sealed joint sequence is non-monotone (+3.116%, +1.596%, +2.661%).

# Load-regime sweep — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`

This report answers only where bounded set-level association coordination has diagnostic value. It does not rank sweep points, recommend a setting, or adopt a new constant. Every row is a separate evaluation on a copied run setting. The sealed per-user rate remains **50 Mbit/s**, and **no sealed constant was changed**.

## Sweep design

Axis L holds the diagnostic rate at the sealed 50 Mbit/s and uses U100, U125, U150, and U200 on nested first-N population projections. Axis R holds population at U100 and uses 20, 35, 50, 65, and 80 Mbit/s. At a representative occupancy of seven and 166.67 MHz per beam, those rates imply required spectral efficiencies of approximately 0.84, 1.47, 2.10, 2.73, and 3.36 bit/s/Hz, spanning comfortably inside the unchanged table to near its approximately 3.71 bit/s/Hz maximum. Joint samples are U125/R65, U150/R80, and U200/R80.

## Curve

Pooled EE is `sum(decoded bits) / sum(joules)`. Every point except U200/R80 uses the same 8 anchors (4 TRAIN worlds × steps 0 and 1). The budget-limited U200/R80 corner uses 4 stratified anchors (the same 4 worlds × step 0); it is therefore a lower-precision tail, not directly equal-precision with the other points. `Joint` is the reused bounded `ORACLE_SET` selector; it includes the certified unilateral fixed point, but committed realised EE can still decline on an anchor because selection uses unchanged boundary-zero objective semantics.

The premise's prior strict-margin 20-anchor receipt is retained as a reference: joint/unilateral `+0.513%` and unilateral/baseline `+451.063%`. The curve below estimates its U100/R50 point on the common 8-anchor sweep subset, where those values are `-0.287%` and `+425.721%`. This is a sampling distinction, not a changed operating point; the 8 rows match the corresponding archived anchors exactly.

### Axis L — offered load at 50 Mbit/s

| Point | Users | Rate (Mbit/s) | Formulation | Baseline EE | Unilateral EE | Joint EE | Joint / unilateral | Negative anchors / N | Unilateral / baseline |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| L100 / R50 (current) | 100 | 50 | Sealed | 3.712113 | 33.113112 | 34.564261 | +4.382% | 0 / 8 | +792.029% |
| L100 / R50 (current) | 100 | 50 | Margin | 8.778906 | 46.152520 | 46.020052 | -0.287% | 2 / 8 | +425.721% |
| L125 | 125 | 50 | Sealed | 5.158458 | 36.787683 | 38.080195 | +3.513% | 0 / 8 | +613.153% |
| L125 | 125 | 50 | Margin | 9.517051 | 46.690309 | 46.720982 | +0.066% | 3 / 8 | +390.596% |
| L150 | 150 | 50 | Sealed | 6.129574 | 39.934632 | 40.879622 | +2.366% | 0 / 8 | +551.507% |
| L150 | 150 | 50 | Margin | 10.023845 | 47.925431 | 48.203727 | +0.581% | 1 / 8 | +378.114% |
| L200 | 200 | 50 | Sealed | 7.022782 | 39.820904 | 40.964717 | +2.872% | 0 / 8 | +467.025% |
| L200 | 200 | 50 | Margin | 10.246625 | 47.429344 | 47.569896 | +0.296% | 1 / 8 | +362.878% |

### Axis R — rate target at 100 users

| Point | Users | Rate (Mbit/s) | Formulation | Baseline EE | Unilateral EE | Joint EE | Joint / unilateral | Negative anchors / N | Unilateral / baseline |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| R20 | 100 | 20 | Sealed | 0.111899 | 15.817595 | 17.563989 | +11.041% | 0 / 8 | +14035.631% |
| R20 | 100 | 20 | Margin | 6.810032 | 34.335567 | 34.373437 | +0.110% | 0 / 8 | +404.191% |
| R35 | 100 | 35 | Sealed | 1.923524 | 29.707026 | 30.824255 | +3.761% | 0 / 8 | +1444.406% |
| R35 | 100 | 35 | Margin | 8.070938 | 36.093401 | 35.792550 | -0.834% | 8 / 8 | +347.202% |
| L100 / R50 (current) | 100 | 50 | Sealed | 3.712113 | 33.113112 | 34.564261 | +4.382% | 0 / 8 | +792.029% |
| L100 / R50 (current) | 100 | 50 | Margin | 8.778906 | 46.152520 | 46.020052 | -0.287% | 2 / 8 | +425.721% |
| R65 | 100 | 65 | Sealed | 4.699943 | 35.447338 | 37.234128 | +5.041% | 0 / 8 | +654.208% |
| R65 | 100 | 65 | Margin | 9.307216 | 51.994566 | 52.397826 | +0.776% | 1 / 8 | +458.648% |
| R80 | 100 | 80 | Sealed | 6.701556 | 38.956339 | 40.000931 | +2.681% | 1 / 8 | +481.303% |
| R80 | 100 | 80 | Margin | 9.951598 | 53.806901 | 53.986495 | +0.334% | 4 / 8 | +440.686% |

### Joint load/rate samples

| Point | Users | Rate (Mbit/s) | Formulation | Baseline EE | Unilateral EE | Joint EE | Joint / unilateral | Negative anchors / N | Unilateral / baseline |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| J125-65 | 125 | 65 | Sealed | 6.258070 | 38.710679 | 39.916871 | +3.116% | 0 / 8 | +518.572% |
| J125-65 | 125 | 65 | Margin | 10.069115 | 52.921609 | 53.133209 | +0.400% | 1 / 8 | +425.583% |
| J150-80 | 150 | 80 | Sealed | 8.629026 | 42.379345 | 43.055916 | +1.596% | 0 / 8 | +391.125% |
| J150-80 | 150 | 80 | Margin | 11.236207 | 53.668340 | 54.013863 | +0.644% | 0 / 8 | +377.638% |
| J200-80 | 200 | 80 | Sealed | 8.620267 | 41.969165 | 43.086018 | +2.661% | 0 / 4 | +386.866% |
| J200-80 | 200 | 80 | Margin | 10.825954 | 53.604566 | 54.128698 | +0.978% | 0 / 4 | +395.149% |

## Finding

Neither one-axis curve is monotone. Strict-margin load gaps are `-0.287%, +0.066%, +0.581%, +0.296%` from U100 through U200, and strict-margin rate gaps are `+0.110%, -0.834%, -0.287%, +0.776%, +0.334%` from 20 through 80 Mbit/s. Sealed load gaps are `+4.382%, +3.513%, +2.366%, +2.872%`, and sealed rate gaps are `+11.041%, +3.761%, +4.382%, +5.041%, +2.681%`. Independently increasing offered load or rate target therefore does not produce sustained joint-over-unilateral growth on this panel.

The combined strict-margin sequence does rise (`+0.400%, +0.644%, +0.978%`). For its joint selector, cap-binding beam-boundary shares are `7.252%, 7.987%, 11.889%`, no-eligible-mode shares are `0.000%, 0.000%, 0.000%`, and interference-limited shares of infeasible user-steps are `89.216%, 97.059%, 95.890%`. At U200/R80 the top-one aggressor share is `84.867%`, with occupancy `3.089` mean / `6` maximum. The sampled rise thus coincides with cap/interference pressure, not a table-maximum event in the selected strict-margin mappings. It remains below the 1% and 2% thresholds, and U200/R80 has only four anchors.

The sealed combined sequence is non-monotone even as its joint-selector cap shares rise from `26.301%` to `39.075%` and `53.708%`, and its no-mode shares rise from `1.878%` to `13.178%` and `24.667%`. All sealed selector rows have zero users attaining the diagnostic rate target despite separate nonzero served counts; the strict-margin rows do not. The absolute sealed gaps therefore do not supply formulation-independent evidence of constraint-driven growth.

## One- and two-per-cent crossings

These are first observed crossings along each ordered one-axis sweep or the ordered joint sequence, not interpolated thresholds. Binding columns report the joint selector at that sampled point; table/cap categories can overlap when different boundaries bind for one user-step.

| Axis | Form | Threshold | First sampled crossing | Gap | Cap-binding beam-boundaries | No-mode beam-boundaries | I-limited / infeasible user-steps |
|---|---|---:|---|---:|---:|---:|---:|
| Load | Sealed | 1% | U100/R50 | +4.382% | 22.141% | 0.000% | 105 / 141 |
| Load | Sealed | 2% | U100/R50 | +4.382% | 22.141% | 0.000% | 105 / 141 |
| Load | Margin | 1% | Not reached | — | — | — | — |
| Load | Margin | 2% | Not reached | — | — | — | — |
| Rate | Sealed | 1% | U100/R20 | +11.041% | 17.346% | 0.000% | 40 / 75 |
| Rate | Sealed | 2% | U100/R20 | +11.041% | 17.346% | 0.000% | 40 / 75 |
| Rate | Margin | 1% | Not reached | — | — | — | — |
| Rate | Margin | 2% | Not reached | — | — | — | — |
| Joint sequence | Sealed | 1% | U125/R65 | +3.116% | 26.301% | 1.878% | 168 / 275 |
| Joint sequence | Sealed | 2% | U125/R65 | +3.116% | 26.301% | 1.878% | 168 / 275 |
| Joint sequence | Margin | 1% | Not reached | — | — | — | — |
| Joint sequence | Margin | 2% | Not reached | — | — | — | — |

## Endpoint and constraint metrics at every point

EE is Mbit/J. Served and target-attained counts are separate sums; each denominator is `N anchors × users`. Constraint shares use occupied beam-boundaries. `I-limited` is the share of infeasible user-steps meeting the declared interference counterfactual, and `top-1` is its aggressor share. Occupancy is mean / maximum over occupied beam-boundaries.

| Point | Form | Selector | EE | Served | Target attained | Cap binds | No eligible mode | Infeasible user-steps | I-limited | Top-1 | Occupancy mean / max | Occupancy distribution (n: beam-boundaries) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| R20 | Sealed | BASELINE | 0.111899 | 24 / 800 | 0 / 800 | 40.408% | 0.000% | 262 / 800 | 88.931% | 89.791% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R20 | Sealed | UNILATERAL | 15.817595 | 452 / 800 | 0 / 800 | 16.379% | 0.000% | 69 / 800 | 46.377% | 95.578% | 5.517 / 16 | 1:192, 2:768, 3:2304, 4:1296, 5:624, 7:336, 8:48, 10:240, 11:96, 12:48, 14:720, 16:288 |
| R20 | Sealed | ORACLE_SET | 17.563989 | 502 / 800 | 0 / 800 | 17.346% | 0.000% | 75 / 800 | 53.333% | 93.640% | 5.797 / 16 | 1:192, 2:720, 3:2160, 4:1008, 5:480, 7:432, 8:96, 9:96, 10:288, 11:96, 12:48, 14:720, 16:288 |
| R20 | Margin | BASELINE | 6.810032 | 518 / 800 | 386 / 800 | 57.750% | 0.000% | 413 / 800 | 82.082% | 86.064% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R20 | Margin | UNILATERAL | 34.335567 | 800 / 800 | 800 / 800 | 0.154% | 0.000% | 15 / 800 | 100.000% | 95.622% | 1.000 / 1 | 1:38400 |
| R20 | Margin | ORACLE_SET | 34.373437 | 800 / 800 | 800 / 800 | 0.154% | 0.000% | 15 / 800 | 100.000% | 95.623% | 1.000 / 1 | 1:38400 |
| R35 | Sealed | BASELINE | 1.923524 | 232 / 800 | 0 / 800 | 48.810% | 0.000% | 341 / 800 | 86.804% | 88.859% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R35 | Sealed | UNILATERAL | 29.707026 | 762 / 800 | 0 / 800 | 31.042% | 0.000% | 139 / 800 | 64.748% | 91.215% | 5.714 / 13 | 1:480, 2:384, 3:144, 4:1248, 5:864, 6:1200, 7:288, 8:1440, 9:432, 11:144, 12:48, 13:48 |
| R35 | Sealed | ORACLE_SET | 30.824255 | 763 / 800 | 0 / 800 | 28.543% | 0.000% | 128 / 800 | 62.500% | 89.322% | 5.839 / 13 | 1:480, 2:384, 3:144, 4:1104, 5:768, 6:1152, 7:288, 8:1488, 9:432, 10:96, 11:144, 12:48, 13:48 |
| R35 | Margin | BASELINE | 8.070938 | 498 / 800 | 294 / 800 | 63.672% | 0.000% | 486 / 800 | 74.486% | 85.991% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R35 | Margin | UNILATERAL | 36.093401 | 800 / 800 | 796 / 800 | 0.204% | 0.000% | 19 / 800 | 100.000% | 96.865% | 1.088 / 4 | 1:33984, 2:384, 4:912 |
| R35 | Margin | ORACLE_SET | 35.792550 | 800 / 800 | 798 / 800 | 0.193% | 0.000% | 18 / 800 | 100.000% | 96.868% | 1.061 / 4 | 1:35040, 2:624, 4:528 |
| L100 / R50 (current) | Sealed | BASELINE | 3.712113 | 323 / 800 | 0 / 800 | 53.776% | 0.000% | 405 / 800 | 79.753% | 88.480% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| L100 / R50 (current) | Sealed | UNILATERAL | 33.113112 | 782 / 800 | 0 / 800 | 22.328% | 0.000% | 150 / 800 | 75.333% | 89.005% | 4.520 / 9 | 1:576, 2:48, 3:1824, 4:1152, 5:2784, 6:1536, 7:192, 8:288, 9:96 |
| L100 / R50 (current) | Sealed | ORACLE_SET | 34.564261 | 784 / 800 | 0 / 800 | 22.141% | 0.000% | 141 / 800 | 74.468% | 88.598% | 4.651 / 9 | 1:528, 2:48, 3:1296, 4:1392, 5:2736, 6:1632, 7:240, 8:288, 9:96 |
| L100 / R50 (current) | Margin | BASELINE | 8.778906 | 482 / 800 | 186 / 800 | 66.995% | 0.000% | 549 / 800 | 68.488% | 85.924% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| L100 / R50 (current) | Margin | UNILATERAL | 46.152520 | 800 / 800 | 551 / 800 | 0.554% | 0.000% | 11 / 800 | 90.909% | 97.791% | 1.818 / 5 | 1:12624, 2:672, 3:7344, 5:480 |
| L100 / R50 (current) | Margin | ORACLE_SET | 46.020052 | 800 / 800 | 555 / 800 | 0.713% | 0.000% | 17 / 800 | 88.235% | 90.658% | 1.814 / 5 | 1:12912, 2:528, 3:7104, 5:624 |
| R65 | Sealed | BASELINE | 4.699943 | 337 / 800 | 0 / 800 | 59.418% | 0.000% | 468 / 800 | 74.786% | 88.108% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R65 | Sealed | UNILATERAL | 35.447338 | 780 / 800 | 0 / 800 | 32.016% | 2.162% | 240 / 800 | 52.083% | 89.822% | 4.324 / 12 | 1:624, 2:144, 3:2496, 4:1968, 5:2448, 6:240, 7:96, 8:288, 9:384, 10:144, 12:48 |
| R65 | Sealed | ORACLE_SET | 37.234128 | 783 / 800 | 0 / 800 | 28.506% | 2.186% | 216 / 800 | 43.519% | 88.740% | 4.372 / 12 | 1:576, 2:144, 3:2304, 4:2064, 5:2496, 6:240, 7:96, 8:288, 9:384, 10:144, 12:48 |
| R65 | Margin | BASELINE | 9.307216 | 463 / 800 | 79 / 800 | 70.412% | 0.000% | 606 / 800 | 56.106% | 86.379% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R65 | Margin | UNILATERAL | 51.994566 | 800 / 800 | 284 / 800 | 4.821% | 0.000% | 78 / 800 | 96.154% | 76.270% | 2.888 / 5 | 1:912, 2:5088, 3:4416, 4:336, 5:2544 |
| R65 | Margin | ORACLE_SET | 52.397826 | 800 / 800 | 292 / 800 | 5.069% | 0.000% | 81 / 800 | 95.062% | 76.414% | 2.963 / 5 | 1:864, 2:4752, 3:4080, 4:528, 5:2736 |
| R80 | Sealed | BASELINE | 6.701556 | 424 / 800 | 0 / 800 | 62.853% | 0.000% | 535 / 800 | 67.850% | 87.574% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R80 | Sealed | UNILATERAL | 38.956339 | 791 / 800 | 0 / 800 | 30.967% | 3.398% | 251 / 800 | 65.737% | 87.373% | 3.883 / 8 | 1:192, 2:1056, 3:1824, 4:5376, 5:432, 6:432, 7:240, 8:336 |
| R80 | Sealed | ORACLE_SET | 40.000931 | 795 / 800 | 0 / 800 | 29.421% | 3.902% | 245 / 800 | 62.449% | 86.827% | 3.902 / 8 | 1:192, 2:1056, 3:1824, 4:5280, 5:432, 6:432, 7:240, 8:384 |
| R80 | Margin | BASELINE | 9.951598 | 449 / 800 | 76 / 800 | 74.492% | 0.000% | 640 / 800 | 46.406% | 87.247% | 2.381 / 7 | 1:4992, 2:4944, 3:2736, 4:2448, 5:720, 6:96, 7:192 |
| R80 | Margin | UNILATERAL | 53.806901 | 800 / 800 | 480 / 800 | 5.837% | 0.000% | 93 / 800 | 93.548% | 85.720% | 2.477 / 4 | 1:6000, 2:2544, 3:528, 4:6432 |
| R80 | Margin | ORACLE_SET | 53.986495 | 800 / 800 | 479 / 800 | 6.165% | 0.000% | 88 / 800 | 94.318% | 83.848% | 2.516 / 4 | 1:5808, 2:2352, 3:528, 4:6576 |
| L125 | Sealed | BASELINE | 5.158458 | 475 / 1000 | 0 / 1000 | 59.271% | 0.000% | 552 / 1000 | 74.457% | 86.621% | 2.849 / 7 | 1:3696, 2:4464, 3:3552, 4:2640, 5:1344, 6:624, 7:528 |
| L125 | Sealed | UNILATERAL | 36.787683 | 991 / 1000 | 0 / 1000 | 18.607% | 0.490% | 188 / 1000 | 73.936% | 88.751% | 4.902 / 13 | 1:192, 2:96, 3:1632, 4:1248, 5:4224, 6:1440, 7:480, 8:240, 10:96, 11:48, 12:48, 13:48 |
| L125 | Sealed | ORACLE_SET | 38.080195 | 993 / 1000 | 0 / 1000 | 16.677% | 0.495% | 163 / 1000 | 69.939% | 87.879% | 4.950 / 13 | 1:144, 2:96, 3:1536, 4:1104, 5:4416, 6:1488, 7:432, 8:240, 10:96, 11:48, 12:48, 13:48 |
| L125 | Margin | BASELINE | 9.517051 | 586 / 1000 | 180 / 1000 | 71.201% | 0.000% | 737 / 1000 | 62.822% | 84.882% | 2.849 / 7 | 1:3696, 2:4464, 3:3552, 4:2640, 5:1344, 6:624, 7:528 |
| L125 | Margin | UNILATERAL | 46.690309 | 1000 / 1000 | 690 / 1000 | 0.639% | 0.000% | 33 / 1000 | 96.970% | 77.266% | 1.992 / 5 | 1:12960, 2:768, 3:9168, 5:1200 |
| L125 | Margin | ORACLE_SET | 46.720982 | 1000 / 1000 | 688 / 1000 | 0.792% | 0.000% | 38 / 1000 | 97.368% | 78.068% | 2.000 / 5 | 1:13104, 2:528, 3:8976, 4:48, 5:1344 |
| L150 | Sealed | BASELINE | 6.129574 | 612 / 1200 | 0 / 1200 | 62.403% | 0.000% | 724 / 1200 | 71.271% | 85.470% | 3.279 / 9 | 1:3312, 2:3648, 3:3552, 4:2736, 5:2064, 6:1056, 7:960, 8:144, 9:96 |
| L150 | Sealed | UNILATERAL | 39.934632 | 1192 / 1200 | 0 / 1200 | 19.125% | 0.000% | 212 / 1200 | 80.189% | 83.013% | 5.405 / 12 | 1:384, 2:48, 3:1200, 4:480, 5:3888, 6:2832, 7:624, 8:768, 9:48, 10:48, 11:288, 12:48 |
| L150 | Sealed | ORACLE_SET | 40.879622 | 1193 / 1200 | 0 / 1200 | 16.883% | 0.000% | 185 / 1200 | 74.595% | 83.912% | 5.430 / 12 | 1:336, 2:48, 3:1200, 4:480, 5:3840, 6:2880, 7:624, 8:768, 9:48, 10:48, 11:288, 12:48 |
| L150 | Margin | BASELINE | 10.023845 | 696 / 1200 | 175 / 1200 | 73.281% | 0.000% | 915 / 1200 | 54.317% | 85.337% | 3.279 / 9 | 1:3312, 2:3648, 3:3552, 4:2736, 5:2064, 6:1056, 7:960, 8:144, 9:96 |
| L150 | Margin | UNILATERAL | 47.925431 | 1200 / 1200 | 829 / 1200 | 1.465% | 0.000% | 64 / 1200 | 98.438% | 73.986% | 2.239 / 5 | 1:11712, 2:480, 3:11376, 5:2160 |
| L150 | Margin | ORACLE_SET | 48.203727 | 1200 / 1200 | 824 / 1200 | 1.138% | 0.000% | 54 / 1200 | 98.148% | 73.367% | 2.230 / 5 | 1:11808, 2:480, 3:11424, 5:2112 |
| L200 | Sealed | BASELINE | 7.022782 | 831 / 1600 | 0 / 1600 | 67.812% | 0.509% | 1119 / 1600 | 62.824% | 84.397% | 4.071 / 13 | 1:2976, 2:2880, 3:3408, 4:2400, 5:2112, 6:1632, 7:1440, 8:864, 9:912, 10:144, 13:96 |
| L200 | Sealed | UNILATERAL | 39.820904 | 1594 / 1600 | 0 / 1600 | 30.053% | 4.215% | 502 / 1600 | 55.378% | 76.805% | 6.130 / 13 | 1:192, 3:960, 4:720, 5:4320, 6:2976, 7:1008, 8:720, 9:432, 11:240, 12:432, 13:528 |
| L200 | Sealed | ORACLE_SET | 40.964717 | 1594 / 1600 | 0 / 1600 | 28.089% | 4.247% | 478 / 1600 | 52.510% | 76.158% | 6.178 / 13 | 1:192, 3:816, 4:720, 5:4320, 6:2880, 7:1152, 8:720, 9:432, 11:240, 12:432, 13:528 |
| L200 | Margin | BASELINE | 10.246625 | 860 / 1600 | 160 / 1600 | 74.995% | 0.509% | 1305 / 1600 | 41.839% | 86.062% | 4.071 / 13 | 1:2976, 2:2880, 3:3408, 4:2400, 5:2112, 6:1632, 7:1440, 8:864, 9:912, 10:144, 13:96 |
| L200 | Margin | UNILATERAL | 47.429344 | 1600 / 1600 | 1039 / 1600 | 2.201% | 0.000% | 126 / 1600 | 98.413% | 72.727% | 2.512 / 7 | 1:11760, 2:720, 3:13728, 5:4080, 7:288 |
| L200 | Margin | ORACLE_SET | 47.569896 | 1600 / 1600 | 1041 / 1600 | 2.064% | 0.000% | 125 / 1600 | 99.200% | 72.604% | 2.512 / 7 | 1:11664, 2:672, 3:13872, 4:48, 5:4128, 7:192 |
| J125-65 | Sealed | BASELINE | 6.258070 | 473 / 1000 | 0 / 1000 | 63.954% | 0.000% | 646 / 1000 | 68.731% | 85.883% | 2.849 / 7 | 1:3696, 2:4464, 3:3552, 4:2640, 5:1344, 6:624, 7:528 |
| J125-65 | Sealed | UNILATERAL | 38.710679 | 987 / 1000 | 0 / 1000 | 27.971% | 1.852% | 282 / 1000 | 60.638% | 87.935% | 4.630 / 10 | 1:432, 2:48, 3:2304, 4:2112, 5:3600, 6:768, 7:144, 8:336, 9:432, 10:192 |
| J125-65 | Sealed | ORACLE_SET | 39.916871 | 988 / 1000 | 0 / 1000 | 26.301% | 1.878% | 275 / 1000 | 61.091% | 88.115% | 4.695 / 10 | 1:432, 2:48, 3:2064, 4:1968, 5:3744, 6:864, 7:144, 8:336, 9:432, 10:192 |
| J125-65 | Margin | BASELINE | 10.069115 | 559 / 1000 | 74 / 1000 | 74.703% | 0.000% | 792 / 1000 | 48.737% | 85.521% | 2.849 / 7 | 1:3696, 2:4464, 3:3552, 4:2640, 5:1344, 6:624, 7:528 |
| J125-65 | Margin | UNILATERAL | 52.921609 | 1000 / 1000 | 445 / 1000 | 7.160% | 0.000% | 100 / 1000 | 89.000% | 79.783% | 3.165 / 5 | 1:528, 2:5664, 3:4176, 4:384, 5:4416 |
| J125-65 | Margin | ORACLE_SET | 53.133209 | 1000 / 1000 | 442 / 1000 | 7.252% | 0.000% | 102 / 1000 | 89.216% | 79.035% | 3.185 / 5 | 1:576, 2:5568, 3:3984, 4:384, 5:4560 |
| J150-80 | Sealed | BASELINE | 8.629026 | 647 / 1200 | 0 / 1200 | 69.820% | 1.366% | 900 / 1200 | 49.556% | 85.940% | 3.279 / 9 | 1:3312, 2:3648, 3:3552, 4:2736, 5:2064, 6:1056, 7:960, 8:144, 9:96 |
| J150-80 | Sealed | UNILATERAL | 42.379345 | 1197 / 1200 | 0 / 1200 | 40.189% | 13.953% | 549 / 1200 | 41.530% | 81.718% | 4.651 / 10 | 1:48, 2:912, 3:1296, 4:6336, 5:480, 6:960, 7:624, 8:1632, 9:48, 10:48 |
| J150-80 | Sealed | ORACLE_SET | 43.055916 | 1198 / 1200 | 0 / 1200 | 39.075% | 13.178% | 530 / 1200 | 41.321% | 81.353% | 4.651 / 9 | 1:48, 2:768, 3:1392, 4:6384, 5:480, 6:960, 7:720, 8:1584, 9:48 |
| J150-80 | Margin | BASELINE | 11.236207 | 650 / 1200 | 62 / 1200 | 77.419% | 1.366% | 1022 / 1200 | 29.843% | 86.760% | 3.279 / 9 | 1:3312, 2:3648, 3:3552, 4:2736, 5:2064, 6:1056, 7:960, 8:144, 9:96 |
| J150-80 | Margin | UNILATERAL | 53.668340 | 1199 / 1200 | 726 / 1200 | 8.294% | 0.000% | 176 / 1200 | 97.159% | 86.824% | 2.817 / 4 | 1:5328, 2:3648, 3:912, 4:10560 |
| J150-80 | Margin | ORACLE_SET | 54.013863 | 1200 / 1200 | 723 / 1200 | 7.987% | 0.000% | 170 / 1200 | 97.059% | 87.258% | 2.810 / 4 | 1:5472, 2:3456, 3:1056, 4:10512 |
| J200-80 | Sealed | BASELINE | 8.620267 | 396 / 800 | 0 / 800 | 72.569% | 10.101% | 654 / 800 | 29.052% | 82.940% | 4.040 / 13 | 1:1440, 2:1536, 3:1824, 4:1104, 5:1008, 6:912, 7:720, 8:432, 9:432, 10:48, 13:48 |
| J200-80 | Sealed | UNILATERAL | 41.969165 | 794 / 800 | 0 / 800 | 55.569% | 24.667% | 464 / 800 | 29.095% | 78.930% | 5.333 / 14 | 1:48, 2:240, 3:624, 4:2976, 5:240, 6:864, 7:432, 8:1632, 9:48, 11:48, 14:48 |
| J200-80 | Sealed | ORACLE_SET | 43.086018 | 796 / 800 | 0 / 800 | 53.708% | 24.667% | 455 / 800 | 28.352% | 81.115% | 5.333 / 14 | 1:48, 2:240, 3:624, 4:2976, 5:240, 6:864, 7:432, 8:1632, 9:48, 11:48, 14:48 |
| J200-80 | Margin | BASELINE | 10.825954 | 399 / 800 | 37 / 800 | 82.207% | 10.101% | 719 / 800 | 19.193% | 84.021% | 4.040 / 13 | 1:1440, 2:1536, 3:1824, 4:1104, 5:1008, 6:912, 7:720, 8:432, 9:432, 10:48, 13:48 |
| J200-80 | Margin | UNILATERAL | 53.604566 | 800 / 800 | 452 / 800 | 12.332% | 0.000% | 149 / 800 | 96.644% | 83.591% | 3.077 / 6 | 1:2448, 2:2016, 3:240, 4:7728, 6:48 |
| J200-80 | Margin | ORACLE_SET | 54.128698 | 800 / 800 | 454 / 800 | 11.889% | 0.000% | 146 / 800 | 95.890% | 84.867% | 3.089 / 6 | 1:2400, 2:1968, 3:288, 4:7728, 6:48 |

## Point-by-point sealed-value declaration

- U100/R20: diagnostic target 20 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U100/R35: diagnostic target 35 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U100/R50: diagnostic target 50 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U100/R65: diagnostic target 65 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U100/R80: diagnostic target 80 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U125/R50: diagnostic target 50 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U150/R50: diagnostic target 50 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U200/R50: diagnostic target 50 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U125/R65: diagnostic target 65 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U150/R80: diagnostic target 80 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.
- U200/R80: diagnostic target 80 Mbit/s; the sealed value is 50 Mbit/s and no sealed constant was changed. Both formulations are separate copied evaluations.

## Definitions and interpretation

- Beam-boundary: one occupied physical beam at one of 48 realised endpoint boundaries.
- Cap-binding: any slot transmission on that beam is within 1e-9 W of the unchanged beam cap.
- No eligible mode: the occupancy/rate target has no target ACM mode in the unchanged table (m_target is None).
- Infeasible user-step: assigned user is target-infeasible at one or more of its 48 boundaries.
- Interference-limited: a finite-target cap-infeasible exposure would fit the unchanged cap with nominal noise alone and has positive cochannel interference.
- Top-one aggressor share: duration-weighted strongest nominal cochannel aggressor term divided by total nominal cochannel interference over interference-limited exposures.
- Occupancy: distribution over occupied beam-boundaries after realised eligibility filtering. The full realised distribution is printed in every selector row, rather than merging selectors.

The load sweep is genuinely nested. For each domain, the script builds one immutable 250-user master tape, preserving the sealed RNG consumption for users 0–99 and placing only added users on a deterministic split stream, then takes first-N projections. Retained users therefore keep identical geometry, fading, epoch, satellite inventory, seed, horizon, and 48 boundary times across L points. Rate points reuse the same projected tape. Population changes only which prefix users participate. As an exact check, the U100/R50 selections, configuration IDs, bits, joules, and served counts match the prior 20-anchor runner's corresponding 8 sealed and strict-margin anchors field-for-field.

The initial source audit materially determined two safeguards in this design: the margin arm calls the already implemented strict clearance formulation directly, and the nested master tape preserves the sealed first-100-user RNG trajectory instead of regenerating a superficially similar geometry.

`Sealed` uses the unchanged production batch formulation. `Margin` uses the prior strict private margin-provisioning copy (`cleared_margin_batch.py`), including its numerical clearance check; it does not edit production physics. The price, sign, seed mapping, 30.08 s horizon, circuit price, 1.65 W cap, mode table, fading quantile, baseline served-count guard, and acceptance/tie rules are unchanged.

The bounded joint catalogue is mechanism-limited (occupant subsets through size four, victim plus top contributors, and complete beam evacuation; 4,096-candidate ceiling). Results describe that selector, not a global combinatorial optimum.

## Reproduction and verification

Exact commands, from the workspace root:

```bash
bash .scratch/load-regime-sweep-20260910/run_all_points.sh
bash .scratch/load-regime-sweep-20260910/run_all_diagnostics.sh
/home/sat/mcrl-leo-handover/.venv/bin/python .scratch/load-regime-sweep-20260910/build_report.py
```

The two run scripts expand every evaluation command to `PYTHONPATH=src`, one BLAS/OpenMP thread per process, the required interpreter, and `nice -n 15`; the point runner uses four selection workers and checkpoints each anchor. Each point receipt records the copied setting, four master/projected tape digests, source commit/tree, reused-runner hash, wrapper hash, no TEST access, and no learner/policy/training run. Diagnostics use three batches with a process-local cache of the same immutable master tapes, assert projected digest identity, replay every committed profile through the independent scalar path, and require bits/joules relative error below `1e-8` with exact served-count parity. Caching changes construction work only, not replay inputs or arithmetic.

Evidence directory: `.scratch/load-regime-sweep-20260910/` (`results/`, `diagnostics/`, `logs/`, source audit, scripts, and completion criterion). The Git tree remains `1728f6b0462f86d85618a4c73f4d1dd2d2c07376`.

## Coverage

Reached all 11 distinct parameter points under both formulations: 22 point-formulation runs. Ten points use 8 anchors per formulation and only U200/R80 uses the budget fallback of 4 anchors per formulation, for 168 anchor evaluations and 504 independent committed-profile scalar replays. **Unreached points: none.** The requested 8-anchor minimum was not reached at U200/R80; it uses 4 stratified anchors rather than dropping the point. No training run, policy run, or learner was used.
