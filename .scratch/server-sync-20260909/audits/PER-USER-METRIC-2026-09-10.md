**Yes. At the source's 3.32° one-sided beam width under the corrected rule, the joint selector retains a +1.030% activity-attributed summed-per-user advantage (+0.389 Gbit/J in the sum).**

# Per-user energy-efficiency diagnostic for the beam-width sweep

`DIAGNOSTIC_NOT_CLAIM`

## Direct answer

The sealed pooled objective is unchanged. This report adds unweighted summed individual-link EE (a sum of ratios) and user-level service/distribution diagnostics beside it; it does not replace, reopen, or retune the sealed ratio of sums.

A summed-metric advantage *survives* in a cell only when `sum_u EE_u(J) / sum_u EE_u(U) - 1 > 0`. The primary answer uses activity/airtime attribution. The second attribution is a fixed-cost sensitivity fixed before results were computed.

| Rule | One-sided / full | Pooled U / J (Mbit/J) | Pooled J−U | Summed U / J, activity (Gbit/J) | Activity J−U (Gbit/J; %) | Summed U / J, account (Gbit/J) | Account J−U (Gbit/J; %) | Pooled/activity disagree? |
|:---|:---:|---:|---:|---:|---:|---:|---:|:---:|
| SEALED | 1.66° / 3.32° | 26.762 / 28.502 | +6.502% | 26.524 / 27.663 | +1.139; +4.295% | 26.509 / 27.649 | +1.140; +4.300% | no |
| SEALED | 2.40° / 4.80° | 25.520 / 28.174 | +10.397% | 25.396 / 27.382 | +1.986; +7.820% | 25.371 / 27.357 | +1.987; +7.830% | no |
| SEALED | 3.32° / 6.64° | 28.956 / 32.304 | +11.563% | 30.099 / 32.209 | +2.110; +7.011% | 30.052 / 32.164 | +2.112; +7.027% | no |
| SEALED | 4.50° / 9.00° | 19.449 / 22.297 | +14.639% | 25.049 / 27.729 | +2.680; +10.699% | 25.007 / 27.684 | +2.677; +10.707% | no |
| SEALED | 6.65° / 13.30° | 3.146 / 4.466 | +41.949% | 8.043 / 10.681 | +2.639; +32.807% | 8.012 / 10.650 | +2.638; +32.921% | no |
| MARGIN | 1.66° / 3.32° | 42.298 / 42.170 | -0.303% | 36.422 / 36.289 | -0.133; -0.365% | 36.377 / 36.244 | -0.133; -0.365% | no |
| MARGIN | 2.40° / 4.80° | 42.637 / 43.153 | +1.209% | 36.651 / 37.016 | +0.365; +0.996% | 36.607 / 36.969 | +0.362; +0.988% | no |
| MARGIN | 3.32° / 6.64° | 44.029 / 44.462 | +0.985% | 37.760 / 38.149 | +0.389; +1.030% | 37.713 / 38.100 | +0.387; +1.026% | no |
| MARGIN | 4.50° / 9.00° | 42.094 / 43.443 | +3.205% | 37.584 / 38.138 | +0.554; +1.473% | 37.525 / 38.077 | +0.552; +1.470% | no |
| MARGIN | 6.65° / 13.30° | 34.334 / 36.846 | +7.315% | 34.265 / 35.629 | +1.364; +3.982% | 34.199 / 35.565 | +1.366; +3.994% | no |

The pooled and activity-attributed summed-per-user signs disagree in **no cell**; the pooled and equal-account signs disagree in **no cell**.

## Joule attribution fixed before measurement

For each 0.640-s boundary sample I reconstruct the exact equal-airtime TDM slot schedule and integrate the allocated user powers with the same 47-interval trapezoid as the sealed endpoint. Failed transmissions are charged: decoding success never controls the energy denominator. Both rules allocate exactly 100% of PA, active-chain circuit, and active-satellite baseband energy; standby and bus energy are zero in this primary V0.25 setting.

1. **Activity/airtime attribution (primary).** A slot's nonlinear PA supply draw and 0.338-W active-chain circuit draw go to the user transmitting on that chain. The active satellite's 0.200-W baseband draw is divided equally among its concurrently active chain-users. Equal airtime within each beam therefore gives each beam member an equal share of that chain's fixed circuit time while retaining its own PA draw.
2. **Equal-account fixed-cost attribution (sensitivity).** PA draw still follows the actual transmitter. At each boundary, the chain circuit draw is divided equally over all transmitting accounts assigned to that beam, and satellite baseband draw is divided equally over all transmitting accounts assigned to that satellite. This treats shared fixed infrastructure as an account obligation rather than an instantaneous-use obligation.

The field's usual unweighted WSEE/summed-individual-EE object is the first form: each link's rate is divided by its own PA-adjusted transmit power plus an attributed/static link circuit term. Matthiesen, Yang and Jorswieck write it explicitly as a sum of `r_k/(phi_k p_k + P_c,k)`, while Efrem and Panagopoulos contrast that link-level sum of ratios with global EE and likewise put PA inefficiency plus static transmitter/receiver circuitry in each link denominator. The satellite baseband term has no unique owner in this downlink simulator, which is why the second, energy-conserving sensitivity is also reported. Sources: [Matthiesen et al., WCNC 2018](https://www.ant.uni-bremen.de/sixcms/media.php/102/14089/WCNC.2018.8377255.pdf); [Efrem and Panagopoulos, 2019](https://arxiv.org/abs/1911.12419).

The metric universe is all 800 matched user-steps in each cell. An unassigned user has zero bits and zero attributed joules and is assigned EE 0; an attempted but unsuccessful user has zero bits, positive attributed joules, and EE 0. Thus the sum is identical whether written over all users or only positive-bit users, while the distribution honestly retains non-service. Quantiles use NumPy's linear method (Hyndman–Fan type 7). `Q1–Q3` is the interquartile interval.

## Per-arm distributions: activity/airtime attribution

All efficiency distribution entries are Mbit/J over all 800 matched user-steps.

| Rule | Width | Arm | Sum (Gbit/J) | P5 | Q1–Q3 | Median | P95 | Zero-bit users |
|:---|---:|:---:|---:|---:|---:|---:|---:|---:|
| SEALED | 1.66° | B | 6.237 | 0.000 | 0.000–14.922 | 0.000 | 35.074 | 487 |
| SEALED | 1.66° | U | 26.524 | 6.090 | 21.566–44.422 | 32.641 | 59.909 | 21 |
| SEALED | 1.66° | J | 27.663 | 10.005 | 23.373–45.280 | 34.823 | 59.933 | 10 |
| SEALED | 2.40° | B | 6.000 | 0.000 | 0.000–14.056 | 0.000 | 32.556 | 466 |
| SEALED | 2.40° | U | 25.396 | 0.249 | 19.696–43.646 | 33.634 | 58.565 | 39 |
| SEALED | 2.40° | J | 27.382 | 4.273 | 22.889–45.630 | 35.073 | 59.489 | 26 |
| SEALED | 3.32° | B | 2.329 | 0.000 | 0.000–0.202 | 0.000 | 19.958 | 597 |
| SEALED | 3.32° | U | 30.099 | 0.000 | 21.539–52.861 | 43.699 | 65.149 | 99 |
| SEALED | 3.32° | J | 32.209 | 0.000 | 28.011–53.241 | 45.848 | 64.630 | 71 |
| SEALED | 4.50° | B | 0.711 | 0.000 | 0.000–0.000 | 0.000 | 3.271 | 744 |
| SEALED | 4.50° | U | 25.049 | 0.000 | 0.000–55.654 | 40.584 | 63.937 | 272 |
| SEALED | 4.50° | J | 27.729 | 0.000 | 3.228–56.006 | 43.875 | 64.002 | 193 |
| SEALED | 6.65° | B | 0.426 | 0.000 | 0.000–0.000 | 0.000 | 0.000 | 781 |
| SEALED | 6.65° | U | 8.043 | 0.000 | 0.000–0.000 | 0.000 | 58.548 | 642 |
| SEALED | 6.65° | J | 10.681 | 0.000 | 0.000–16.686 | 0.000 | 62.540 | 580 |
| MARGIN | 1.66° | B | 9.817 | 0.000 | 0.000–22.609 | 4.655 | 41.962 | 348 |
| MARGIN | 1.66° | U | 36.422 | 30.044 | 37.607–52.847 | 44.453 | 65.672 | 0 |
| MARGIN | 1.66° | J | 36.289 | 29.891 | 37.495–52.768 | 44.248 | 65.600 | 0 |
| MARGIN | 2.40° | B | 7.908 | 0.000 | 0.000–16.124 | 0.581 | 40.013 | 387 |
| MARGIN | 2.40° | U | 36.651 | 27.700 | 37.479–54.184 | 45.304 | 64.292 | 0 |
| MARGIN | 2.40° | J | 37.016 | 28.206 | 38.164–54.329 | 45.793 | 64.565 | 0 |
| MARGIN | 3.32° | B | 3.180 | 0.000 | 0.000–1.575 | 0.000 | 23.939 | 570 |
| MARGIN | 3.32° | U | 37.760 | 29.248 | 40.203–54.327 | 47.114 | 65.178 | 0 |
| MARGIN | 3.32° | J | 38.149 | 29.578 | 40.624–54.731 | 47.495 | 65.852 | 0 |
| MARGIN | 4.50° | B | 1.164 | 0.000 | 0.000–0.000 | 0.000 | 9.073 | 723 |
| MARGIN | 4.50° | U | 37.584 | 23.125 | 39.218–55.989 | 48.708 | 67.072 | 19 |
| MARGIN | 4.50° | J | 38.138 | 26.233 | 39.490–56.332 | 49.334 | 67.220 | 19 |
| MARGIN | 6.65° | B | 0.739 | 0.000 | 0.000–0.000 | 0.000 | 0.000 | 772 |
| MARGIN | 6.65° | U | 34.265 | 0.000 | 35.015–56.523 | 48.491 | 68.198 | 106 |
| MARGIN | 6.65° | J | 35.629 | 0.000 | 37.152–57.086 | 49.459 | 67.948 | 78 |

## Per-arm distributions: equal-account fixed-cost attribution

| Rule | Width | Arm | Sum (Gbit/J) | P5 | Q1–Q3 | Median | P95 | Zero-bit users |
|:---|---:|:---:|---:|---:|---:|---:|---:|---:|
| SEALED | 1.66° | B | 6.228 | 0.000 | 0.000–14.915 | 0.000 | 35.036 | 487 |
| SEALED | 1.66° | U | 26.509 | 6.092 | 21.572–44.153 | 32.556 | 59.563 | 21 |
| SEALED | 1.66° | J | 27.649 | 10.009 | 23.428–45.217 | 34.795 | 59.759 | 10 |
| SEALED | 2.40° | B | 5.988 | 0.000 | 0.000–14.045 | 0.000 | 32.498 | 466 |
| SEALED | 2.40° | U | 25.371 | 0.249 | 19.705–43.512 | 33.710 | 58.661 | 39 |
| SEALED | 2.40° | J | 27.357 | 4.276 | 22.941–45.431 | 35.050 | 59.383 | 26 |
| SEALED | 3.32° | B | 2.321 | 0.000 | 0.000–0.202 | 0.000 | 19.918 | 597 |
| SEALED | 3.32° | U | 30.052 | 0.000 | 21.510–52.738 | 43.596 | 64.969 | 99 |
| SEALED | 3.32° | J | 32.164 | 0.000 | 28.007–53.231 | 45.813 | 64.417 | 71 |
| SEALED | 4.50° | B | 0.706 | 0.000 | 0.000–0.000 | 0.000 | 3.253 | 744 |
| SEALED | 4.50° | U | 25.007 | 0.000 | 0.000–55.484 | 40.627 | 63.770 | 272 |
| SEALED | 4.50° | J | 27.684 | 0.000 | 3.225–55.737 | 44.026 | 63.790 | 193 |
| SEALED | 6.65° | B | 0.421 | 0.000 | 0.000–0.000 | 0.000 | 0.000 | 781 |
| SEALED | 6.65° | U | 8.012 | 0.000 | 0.000–0.000 | 0.000 | 58.323 | 642 |
| SEALED | 6.65° | J | 10.650 | 0.000 | 0.000–16.730 | 0.000 | 62.242 | 580 |
| MARGIN | 1.66° | B | 9.813 | 0.000 | 0.000–22.608 | 4.654 | 41.934 | 348 |
| MARGIN | 1.66° | U | 36.377 | 30.074 | 37.652–52.655 | 44.232 | 65.537 | 0 |
| MARGIN | 1.66° | J | 36.244 | 30.037 | 37.529–52.658 | 43.983 | 65.398 | 0 |
| MARGIN | 2.40° | B | 7.903 | 0.000 | 0.000–16.124 | 0.581 | 39.929 | 387 |
| MARGIN | 2.40° | U | 36.607 | 27.683 | 37.643–54.033 | 45.295 | 64.041 | 0 |
| MARGIN | 2.40° | J | 36.969 | 28.234 | 38.338–54.206 | 45.712 | 64.474 | 0 |
| MARGIN | 3.32° | B | 3.176 | 0.000 | 0.000–1.574 | 0.000 | 23.928 | 570 |
| MARGIN | 3.32° | U | 37.713 | 29.262 | 40.342–54.026 | 46.943 | 64.972 | 0 |
| MARGIN | 3.32° | J | 38.100 | 29.856 | 40.736–54.529 | 47.437 | 65.839 | 0 |
| MARGIN | 4.50° | B | 1.160 | 0.000 | 0.000–0.000 | 0.000 | 9.062 | 723 |
| MARGIN | 4.50° | U | 37.525 | 23.115 | 39.270–55.647 | 48.622 | 66.739 | 19 |
| MARGIN | 4.50° | J | 38.077 | 26.285 | 39.529–56.270 | 49.296 | 67.070 | 19 |
| MARGIN | 6.65° | B | 0.734 | 0.000 | 0.000–0.000 | 0.000 | 0.000 | 772 |
| MARGIN | 6.65° | U | 34.199 | 0.000 | 35.163–56.303 | 48.529 | 67.930 | 106 |
| MARGIN | 6.65° | J | 35.565 | 0.000 | 37.255–56.859 | 49.359 | 67.743 | 78 |

The machine-readable receipt also contains the same five-number distributions restricted to served user-steps. They are not substituted here because excluding unserved users would hide the very allocation failure this diagnostic is meant to expose.

## Service and rate-target attainment

Served means positive integrated decoding time. Target attainment means integrated credited bits at least `50 Mbit/s × 30.08 s`; it is not inferred from served status.

| Rule | Width | Arm | Served count (share) | Target count (share) | Zero credited bits |
|:---|---:|:---:|---:|---:|---:|
| SEALED | 1.66° | B | 313 (39.125%) | 0 (0.000%) | 487 |
| SEALED | 1.66° | U | 779 (97.375%) | 0 (0.000%) | 21 |
| SEALED | 1.66° | J | 790 (98.750%) | 0 (0.000%) | 10 |
| SEALED | 2.40° | B | 334 (41.750%) | 0 (0.000%) | 466 |
| SEALED | 2.40° | U | 761 (95.125%) | 0 (0.000%) | 39 |
| SEALED | 2.40° | J | 774 (96.750%) | 0 (0.000%) | 26 |
| SEALED | 3.32° | B | 203 (25.375%) | 0 (0.000%) | 597 |
| SEALED | 3.32° | U | 701 (87.625%) | 0 (0.000%) | 99 |
| SEALED | 3.32° | J | 729 (91.125%) | 0 (0.000%) | 71 |
| SEALED | 4.50° | B | 56 (7.000%) | 0 (0.000%) | 744 |
| SEALED | 4.50° | U | 528 (66.000%) | 0 (0.000%) | 272 |
| SEALED | 4.50° | J | 607 (75.875%) | 0 (0.000%) | 193 |
| SEALED | 6.65° | B | 19 (2.375%) | 0 (0.000%) | 781 |
| SEALED | 6.65° | U | 158 (19.750%) | 0 (0.000%) | 642 |
| SEALED | 6.65° | J | 220 (27.500%) | 0 (0.000%) | 580 |
| MARGIN | 1.66° | B | 452 (56.500%) | 174 (21.750%) | 348 |
| MARGIN | 1.66° | U | 800 (100.000%) | 550 (68.750%) | 0 |
| MARGIN | 1.66° | J | 800 (100.000%) | 541 (67.625%) | 0 |
| MARGIN | 2.40° | B | 413 (51.625%) | 131 (16.375%) | 387 |
| MARGIN | 2.40° | U | 800 (100.000%) | 487 (60.875%) | 0 |
| MARGIN | 2.40° | J | 800 (100.000%) | 474 (59.250%) | 0 |
| MARGIN | 3.32° | B | 230 (28.750%) | 60 (7.500%) | 570 |
| MARGIN | 3.32° | U | 800 (100.000%) | 443 (55.375%) | 0 |
| MARGIN | 3.32° | J | 800 (100.000%) | 434 (54.250%) | 0 |
| MARGIN | 4.50° | B | 77 (9.625%) | 24 (3.000%) | 723 |
| MARGIN | 4.50° | U | 781 (97.625%) | 338 (42.250%) | 19 |
| MARGIN | 4.50° | J | 781 (97.625%) | 337 (42.125%) | 19 |
| MARGIN | 6.65° | B | 28 (3.500%) | 9 (1.125%) | 772 |
| MARGIN | 6.65° | U | 694 (86.750%) | 258 (32.250%) | 106 |
| MARGIN | 6.65° | J | 722 (90.250%) | 269 (33.625%) | 78 |

## Paired joint-minus-unilateral user effects

Pairs are exact `(anchor_id, user_id)` matches over all 800 user-steps. Better/worse/tied uses the deterministic binary64 sign of `EE_u(J) − EE_u(U)`; the five-number change distributions are Mbit/J and include zeros.

| Rule | Width | Attribution | Better / worse / tied | P5 | Q1–Q3 | Median | P95 |
|:---|---:|:---|---:|---:|---:|---:|---:|
| SEALED | 1.66° | activity/airtime | 296 / 452 / 52 | -0.512 | -0.008–0.003 | -0.000 | 10.076 |
| SEALED | 1.66° | equal-account fixed cost | 361 / 374 / 65 | -0.484 | -0.007–0.033 | 0.000 | 10.083 |
| SEALED | 2.40° | activity/airtime | 337 / 382 / 81 | -0.184 | -0.006–0.067 | 0.000 | 20.662 |
| SEALED | 2.40° | equal-account fixed cost | 384 / 333 / 83 | -0.173 | -0.005–0.078 | 0.000 | 20.657 |
| SEALED | 3.32° | activity/airtime | 284 / 342 / 174 | -0.762 | -0.008–0.010 | 0.000 | 28.677 |
| SEALED | 3.32° | equal-account fixed cost | 287 / 344 / 169 | -0.778 | -0.010–0.019 | 0.000 | 28.659 |
| SEALED | 4.50° | activity/airtime | 207 / 241 / 352 | -0.154 | -0.003–0.000 | 0.000 | 34.088 |
| SEALED | 4.50° | equal-account fixed cost | 204 / 237 / 359 | -0.135 | -0.003–0.000 | 0.000 | 34.088 |
| SEALED | 6.65° | activity/airtime | 141 / 40 / 619 | -0.000 | 0.000–0.000 | 0.000 | 42.686 |
| SEALED | 6.65° | equal-account fixed cost | 140 / 40 / 620 | -0.000 | 0.000–0.000 | 0.000 | 42.686 |
| MARGIN | 1.66° | activity/airtime | 318 / 375 / 107 | -2.008 | -0.005–0.005 | 0.000 | 0.456 |
| MARGIN | 1.66° | equal-account fixed cost | 369 / 365 / 66 | -1.848 | -0.017–0.007 | 0.000 | 0.458 |
| MARGIN | 2.40° | activity/airtime | 348 / 404 / 48 | -0.269 | -0.004–0.006 | -0.000 | 3.969 |
| MARGIN | 2.40° | equal-account fixed cost | 392 / 371 / 37 | -0.273 | -0.016–0.024 | 0.000 | 3.816 |
| MARGIN | 3.32° | activity/airtime | 291 / 363 / 146 | -0.582 | -0.002–0.000 | 0.000 | 3.678 |
| MARGIN | 3.32° | equal-account fixed cost | 351 / 368 / 81 | -0.554 | -0.006–0.009 | 0.000 | 3.635 |
| MARGIN | 4.50° | activity/airtime | 356 / 267 / 177 | -0.149 | -0.000–0.003 | 0.000 | 4.565 |
| MARGIN | 4.50° | equal-account fixed cost | 372 / 265 / 163 | -0.186 | -0.000–0.007 | 0.000 | 4.506 |
| MARGIN | 6.65° | activity/airtime | 305 / 269 / 226 | -1.193 | -0.002–0.005 | 0.000 | 4.967 |
| MARGIN | 6.65° | equal-account fixed cost | 316 / 272 / 212 | -1.161 | -0.003–0.010 | 0.000 | 4.818 |

These counts make the composition visible even when a summed or pooled scalar is positive: a zero median does not mean no effect; it means at least half of matched user-steps have no signed change at the reported precision/order statistic.

## Reproduction and integrity checks

The existing configurations—not the selector search—were replayed. For every arm/anchor, dense replay had to match the recorded total bits and joules in binary64 and the recorded served count. An independent scalar reconstruction then had to match dense per-user bits and total energy within declared floating-point tolerances. At every boundary and full endpoint, both attribution rules had to conserve total energy.

Run from `/home/sat/mcrl-v025-beam-ws`: 

```bash
nice -n 15 env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/beamwidth/per_user_metric.py \
  --receipt .scratch/beamwidth/per-user-metric.json \
  --report PER-USER-METRIC-2026-09-10.md
```

Detailed receipt: `.scratch/beamwidth/per-user-metric.json` (`SHA-256 63c068c93ee13ca11885507d8dc21c47f7d15ec57bb2aa4d0965aa172cb0ebf7`). It contains all 24,000 selector/user-step rows (10 cells × 3 arms × 800), including bits, decoding time, target status, and both attributed joule/EE values.

Input and script SHA-256 values:

```text
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
550b9abdb5f80658f3756233fed8b41f5fa56da20848366c1843e454ddc61ca0  .scratch/beamwidth/per_user_metric.py
```

## Scope and limits

Reached: all ten requested width/rule cells, all three arms, both fixed-cost attributions, all 800 user-step observations per cell, target attainment, and exact U/J pairing. No physics selection, learner, policy, training, sealed objective, constant, threshold, sign, seed, horizon, price, guard, acceptance rule, sealed artefact, or frozen manifest was changed.

Not reached: this remains the same eight-anchor TRAIN-only diagnostic panel. It supplies no uncertainty interval, population-level claim, test-split evidence, unconstrained joint optimum, causal claim about unsampled widths, or empirical authority for choosing one accounting convention over another. Shared fixed-cost ownership is inherently conventional; that is why both predeclared, energy-conserving allocations are shown.
