Multi-start spread (same-index pooled / maximum anchor) is `SEALED` 5.8464% / 30.7909% and `MARGIN_Q` 2.0864% / 15.5842%; 128/128 endpoints (100.0000%) are not 2-swap optimal; the nearest-start reference is 9.8698% (`SEALED`) and 3.0615% (`MARGIN_Q`) below the best value found.

# Multi-start ceiling diagnostic — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`. No learner, training run, or policy run was performed. No sealed constant, threshold, sign, seed, horizon, price, service guard, acceptance rule, sealed artefact, or frozen manifest was changed.

## Direct result

| rule | pooled nearest-start EE (Mbit/J) | pooled same-index start spread | maximum anchor spread | pooled best-of-8 EE (Mbit/J) | pooled best found incl. tested swaps (Mbit/J) | best found exceeds reference | reference below best found | endpoints not 2-swap optimal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `SEALED` | 34.570961 | 5.8464% | 30.7909% | 38.058640 | 38.356680 | 10.9506% | 9.8698% | 64/64 (100.0000%) |
| `MARGIN_Q` | 47.120580 | 2.0864% | 15.5842% | 48.415713 | 48.608741 | 3.1582% | 3.0615% | 64/64 (100.0000%) |

Here, pooled best-of-8 selects the best committed endpoint separately on each anchor and then pools summed bits over summed joules. It is a best-known value within these eight starts, not an upper bound. Every spread is `max/min - 1`. The pooled best-found column selects, per anchor, from those endpoints and the committed F-best one-swap configuration tested from each endpoint. “Best found exceeds reference” divides by the reference; “reference below best found” divides by the best found, so the denominators are explicit.

## Panel, starts, and invariant search

The real-anchor panel is `w1/s0`, `w1/s1`, `w2/s0`, `w2/s1`, `w3/s0`, `w3/s1`, `w4/s0`, and `w4/s1`: two consecutive anchors from each of the four published `V025_PROBE_R2` worlds, 100 users per anchor. Both provisioning rules use the same master seed and random draw construction.

Start 0 is the nearest-eligible baseline. Starts 1–7 use master seed `20260910`. For a start, Python's `random.Random` is initialized by the first 64 bits of `SHA256('mcrl-v025-multistart|20260910|world|step|start|attempt')`; each user appears once in a seeded shuffled order and receives a uniform draw from that user's ordered sealed legal-option tuple. Starting from nearest-eligible, a drawn change is retained only when its exact one-boundary profile is valid and meets the unchanged nearest-baseline served guard; the objective is never consulted. Whole-assignment duplicates are redrawn. `NULL` is used only when the user has no legal option. Because physical feasibility is rule-dependent, the random draw stream is shared but accepted start assignments can differ between provisioning rules.

The search is imported from `/home/sat/mcrl-v025-harness-ws/harness/anytime.py`, SHA-256 `003bdee1df908fddf652f2f8069c31a6297a7f7178bbb83338d09b3f4add9928`. Its algorithm is unchanged: deterministic cyclic first-improvement, users sorted, each user's sealed legal options in sealed order, 16-candidate native dense microbatches, strict exact-binary64 `F = B - eta_ref E` improvement, and the nearest-eligible baseline served-count guard. A narrow adapter changes only the initial incumbent; transition energy and the guard continue to reference the true nearest-eligible baseline. Start 0 and its endpoint are reused from today's digest-checked anytime receipts.

Committed endpoint efficiency uses the same 48 realised boundaries at `fading_quantile_alpha = 0.10`. Each newly found endpoint is committed-evaluated alone to avoid dense-batch-composition roundoff.

## M1 — endpoint efficiency and spread

### `SEALED`

| anchor | start 0 | start 1 | start 2 | start 3 | start 4 | start 5 | start 6 | start 7 | spread | best over start 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| w1/s0 | 31.386418 | 32.903485 | 31.465793 | 35.698588 | 34.970836 | 36.598663 | 37.211707 | 36.135692 | 18.5599% | 18.5599% |
| w1/s1 | 34.537456 | 29.811659 | 31.083531 | 34.023596 | 27.832194 | 34.653131 | 34.598255 | 36.401969 | 30.7909% | 5.3985% |
| w2/s0 | 32.919274 | 36.061327 | 36.986558 | 35.779339 | 31.835488 | 36.163093 | 32.314539 | 35.907849 | 16.1803% | 12.3553% |
| w2/s1 | 39.707476 | 38.568761 | 37.095419 | 39.805184 | 35.710493 | 33.396889 | 37.228115 | 37.532791 | 19.1883% | 0.2461% |
| w3/s0 | 28.616198 | 31.272842 | 32.869970 | 31.833516 | 31.784969 | 30.230689 | 35.156188 | 27.867421 | 26.1552% | 22.8542% |
| w3/s1 | 39.635471 | 33.928298 | 37.362396 | 37.215167 | 35.092208 | 37.506257 | 32.556723 | 35.140912 | 21.7428% | 0.0000% |
| w4/s0 | 32.327544 | 34.739402 | 36.984734 | 36.864463 | 35.567745 | 35.522087 | 38.831160 | 34.352177 | 20.1179% | 20.1179% |
| w4/s1 | 40.066071 | 36.196279 | 40.893018 | 31.405666 | 36.619739 | 35.883246 | 35.373937 | 39.897934 | 30.2090% | 2.0640% |
| **pooled same-index starts** | 34.570961 | 34.026760 | 35.463372 | 35.151314 | 33.504546 | 34.929931 | 35.288135 | 35.177991 | 5.8464% | 2.5814% |
| **pooled per-anchor best-of-8** | 38.058640 | — | — | — | — | — | — | — | — | 10.0885% |

### `MARGIN_Q`

| anchor | start 0 | start 1 | start 2 | start 3 | start 4 | start 5 | start 6 | start 7 | spread | best over start 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| w1/s0 | 46.177881 | 45.476935 | 45.017350 | 46.431889 | 47.590503 | 45.730757 | 46.021165 | 44.489958 | 6.9691% | 3.0591% |
| w1/s1 | 46.520219 | 43.954317 | 46.161566 | 45.326176 | 43.473658 | 43.987921 | 44.924818 | 44.866200 | 7.0078% | 0.0000% |
| w2/s0 | 44.694225 | 41.542573 | 47.626820 | 43.552601 | 43.131941 | 41.205317 | 42.989874 | 46.755881 | 15.5842% | 6.5615% |
| w2/s1 | 50.591786 | 48.807004 | 49.192631 | 49.971327 | 50.651649 | 50.617846 | 52.487692 | 50.129915 | 7.5413% | 3.7475% |
| w3/s0 | 45.661900 | 45.876798 | 46.215855 | 46.945636 | 45.173223 | 45.422972 | 45.822884 | 47.150041 | 4.3761% | 3.2590% |
| w3/s1 | 46.868685 | 46.367261 | 46.689170 | 44.933469 | 46.245608 | 46.667282 | 43.594864 | 46.292198 | 7.5096% | 0.0000% |
| w4/s0 | 47.816848 | 48.000794 | 46.426207 | 48.295873 | 48.571723 | 49.345252 | 47.682541 | 46.645721 | 6.2875% | 3.1964% |
| w4/s1 | 49.229119 | 50.371195 | 49.224498 | 50.273125 | 48.379085 | 49.291356 | 48.571393 | 47.984920 | 4.9730% | 2.3199% |
| **pooled same-index starts** | 47.120580 | 46.157533 | 47.029595 | 46.862121 | 46.508334 | 46.336214 | 46.324516 | 46.732332 | 2.0864% | 0.0000% |
| **pooled per-anchor best-of-8** | 48.415713 | — | — | — | — | — | — | — | — | 2.7486% |

## M2 — exact pairwise-swap test

A legal swap exchanges the two distinct, non-`NULL` assigned identities of an unordered user pair, provided each received identity is in the receiving user's sealed legal options. Every legal swap is evaluated at the exact one-boundary selection objective and must satisfy the unchanged nearest-baseline served guard. An endpoint is called 2-swap optimal only when none strictly improves `F`.

| rule | non-optimal endpoints | best-swap selection ΔF (Mbit), non-optimal endpoints | committed EE change of the F-best swap |
|---|---:|---|---|
| `SEALED` | 64/64 (100.0000%) | min 18.4414, median 557.916, mean 592.501, max 1360.56 | min -0.727015, median 0.89473, mean 1.00417, max 2.72879% |
| `MARGIN_Q` | 64/64 (100.0000%) | min 35.3277, median 166.493, mean 194.487, max 564.108 | min -0.081084, median 0.249379, mean 0.346188, max 1.39877% |

Per endpoint:

| rule | anchor | start | legal swaps | improving swaps | 2-swap optimal | best ΔF (Mbit) | committed EE change |
|---|---|---:|---:|---:|---|---:|---:|
| `SEALED` | w1/s0 | 0 | 283 | 7 | no | 335.269312 | 0.7588% |
| `SEALED` | w1/s0 | 1 | 340 | 12 | no | 260.284144 | 0.7315% |
| `SEALED` | w1/s0 | 2 | 264 | 11 | no | 947.634973 | 0.7585% |
| `SEALED` | w1/s0 | 3 | 324 | 14 | no | 592.090712 | 0.7644% |
| `SEALED` | w1/s0 | 4 | 333 | 7 | no | 673.609626 | 1.1009% |
| `SEALED` | w1/s0 | 5 | 300 | 12 | no | 732.964934 | 1.1942% |
| `SEALED` | w1/s0 | 6 | 349 | 16 | no | 792.801470 | 0.9754% |
| `SEALED` | w1/s0 | 7 | 307 | 12 | no | 1121.657171 | 2.3855% |
| `SEALED` | w1/s1 | 0 | 305 | 15 | no | 897.646826 | -0.1066% |
| `SEALED` | w1/s1 | 1 | 217 | 14 | no | 1026.412551 | 1.5367% |
| `SEALED` | w1/s1 | 2 | 279 | 12 | no | 500.459615 | 0.2207% |
| `SEALED` | w1/s1 | 3 | 272 | 17 | no | 497.183707 | 0.7646% |
| `SEALED` | w1/s1 | 4 | 254 | 4 | no | 644.068177 | 1.5786% |
| `SEALED` | w1/s1 | 5 | 269 | 4 | no | 673.654770 | 1.2067% |
| `SEALED` | w1/s1 | 6 | 361 | 16 | no | 835.519830 | -0.2380% |
| `SEALED` | w1/s1 | 7 | 305 | 31 | no | 659.356243 | 0.1022% |
| `SEALED` | w2/s0 | 0 | 284 | 13 | no | 303.128709 | 1.1922% |
| `SEALED` | w2/s0 | 1 | 317 | 16 | no | 360.435889 | 0.8595% |
| `SEALED` | w2/s0 | 2 | 282 | 16 | no | 563.903881 | -0.4560% |
| `SEALED` | w2/s0 | 3 | 296 | 23 | no | 942.802592 | -0.4365% |
| `SEALED` | w2/s0 | 4 | 325 | 8 | no | 414.077451 | 0.7521% |
| `SEALED` | w2/s0 | 5 | 294 | 1 | no | 51.818890 | 0.4236% |
| `SEALED` | w2/s0 | 6 | 226 | 11 | no | 526.756846 | 2.3879% |
| `SEALED` | w2/s0 | 7 | 306 | 12 | no | 248.926528 | 1.8589% |
| `SEALED` | w2/s1 | 0 | 307 | 5 | no | 401.547698 | 0.4811% |
| `SEALED` | w2/s1 | 1 | 284 | 7 | no | 482.295804 | 1.9263% |
| `SEALED` | w2/s1 | 2 | 299 | 5 | no | 452.701054 | 1.1405% |
| `SEALED` | w2/s1 | 3 | 305 | 10 | no | 587.904794 | 1.2533% |
| `SEALED` | w2/s1 | 4 | 252 | 7 | no | 551.928014 | 2.1609% |
| `SEALED` | w2/s1 | 5 | 298 | 8 | no | 397.382919 | 0.7607% |
| `SEALED` | w2/s1 | 6 | 274 | 7 | no | 363.129889 | -0.7270% |
| `SEALED` | w2/s1 | 7 | 266 | 4 | no | 667.999066 | 1.9900% |
| `SEALED` | w3/s0 | 0 | 284 | 12 | no | 1300.147152 | 1.9942% |
| `SEALED` | w3/s0 | 1 | 214 | 16 | no | 705.667195 | 1.4827% |
| `SEALED` | w3/s0 | 2 | 292 | 13 | no | 883.622433 | 1.2956% |
| `SEALED` | w3/s0 | 3 | 258 | 10 | no | 306.779233 | 0.6980% |
| `SEALED` | w3/s0 | 4 | 256 | 14 | no | 1360.561840 | 0.8950% |
| `SEALED` | w3/s0 | 5 | 232 | 12 | no | 461.122368 | 0.5930% |
| `SEALED` | w3/s0 | 6 | 286 | 6 | no | 384.019236 | 0.6241% |
| `SEALED` | w3/s0 | 7 | 233 | 28 | no | 1146.031322 | 0.2240% |
| `SEALED` | w3/s1 | 0 | 275 | 20 | no | 520.306401 | 1.0539% |
| `SEALED` | w3/s1 | 1 | 253 | 18 | no | 832.348916 | 2.3735% |
| `SEALED` | w3/s1 | 2 | 262 | 11 | no | 265.458502 | 0.6045% |
| `SEALED` | w3/s1 | 3 | 302 | 10 | no | 456.233371 | 2.3135% |
| `SEALED` | w3/s1 | 4 | 286 | 23 | no | 932.689321 | 2.7288% |
| `SEALED` | w3/s1 | 5 | 281 | 29 | no | 635.597882 | 1.1510% |
| `SEALED` | w3/s1 | 6 | 210 | 17 | no | 833.606796 | 0.1696% |
| `SEALED` | w3/s1 | 7 | 254 | 34 | no | 971.334355 | 1.8058% |
| `SEALED` | w4/s0 | 0 | 271 | 11 | no | 594.354227 | 1.0999% |
| `SEALED` | w4/s0 | 1 | 254 | 18 | no | 518.222641 | 1.4602% |
| `SEALED` | w4/s0 | 2 | 291 | 17 | no | 587.286981 | 2.6267% |
| `SEALED` | w4/s0 | 3 | 262 | 7 | no | 230.319086 | 0.3110% |
| `SEALED` | w4/s0 | 4 | 239 | 12 | no | 511.868791 | 0.8944% |
| `SEALED` | w4/s0 | 5 | 283 | 27 | no | 1065.152838 | 0.4452% |
| `SEALED` | w4/s0 | 6 | 302 | 5 | no | 321.919976 | 0.7326% |
| `SEALED` | w4/s0 | 7 | 275 | 14 | no | 667.552075 | 1.1040% |
| `SEALED` | w4/s1 | 0 | 323 | 1 | no | 18.441393 | 0.1130% |
| `SEALED` | w4/s1 | 1 | 250 | 8 | no | 235.489699 | 0.7957% |
| `SEALED` | w4/s1 | 2 | 237 | 5 | no | 480.239603 | 1.6456% |
| `SEALED` | w4/s1 | 3 | 254 | 10 | no | 596.847924 | 0.9524% |
| `SEALED` | w4/s1 | 4 | 259 | 13 | no | 305.509848 | 0.5403% |
| `SEALED` | w4/s1 | 5 | 278 | 11 | no | 637.954584 | 0.7424% |
| `SEALED` | w4/s1 | 6 | 236 | 7 | no | 350.572022 | 0.5650% |
| `SEALED` | w4/s1 | 7 | 314 | 7 | no | 295.452908 | 0.9299% |
| `MARGIN_Q` | w1/s0 | 0 | 605 | 10 | no | 120.611133 | 0.7602% |
| `MARGIN_Q` | w1/s0 | 1 | 575 | 20 | no | 335.120149 | 0.4789% |
| `MARGIN_Q` | w1/s0 | 2 | 589 | 21 | no | 97.872001 | 0.2773% |
| `MARGIN_Q` | w1/s0 | 3 | 579 | 21 | no | 63.307691 | 0.2248% |
| `MARGIN_Q` | w1/s0 | 4 | 596 | 11 | no | 35.327683 | 0.2368% |
| `MARGIN_Q` | w1/s0 | 5 | 596 | 10 | no | 59.942933 | 0.1870% |
| `MARGIN_Q` | w1/s0 | 6 | 569 | 11 | no | 341.216337 | 0.3568% |
| `MARGIN_Q` | w1/s0 | 7 | 584 | 24 | no | 194.113344 | 0.2722% |
| `MARGIN_Q` | w1/s1 | 0 | 550 | 3 | no | 359.531414 | 0.5632% |
| `MARGIN_Q` | w1/s1 | 1 | 563 | 14 | no | 219.882143 | 0.2079% |
| `MARGIN_Q` | w1/s1 | 2 | 513 | 20 | no | 104.429120 | 0.1727% |
| `MARGIN_Q` | w1/s1 | 3 | 500 | 12 | no | 125.612067 | 0.1974% |
| `MARGIN_Q` | w1/s1 | 4 | 542 | 16 | no | 291.249971 | 0.3285% |
| `MARGIN_Q` | w1/s1 | 5 | 523 | 14 | no | 163.619945 | 0.1744% |
| `MARGIN_Q` | w1/s1 | 6 | 577 | 13 | no | 65.750792 | -0.0811% |
| `MARGIN_Q` | w1/s1 | 7 | 536 | 13 | no | 82.809962 | 0.5120% |
| `MARGIN_Q` | w2/s0 | 0 | 548 | 13 | no | 224.918640 | -0.0468% |
| `MARGIN_Q` | w2/s0 | 1 | 499 | 5 | no | 564.107806 | 1.3988% |
| `MARGIN_Q` | w2/s0 | 2 | 523 | 11 | no | 135.927682 | 0.1178% |
| `MARGIN_Q` | w2/s0 | 3 | 526 | 7 | no | 125.214431 | 0.1611% |
| `MARGIN_Q` | w2/s0 | 4 | 575 | 8 | no | 71.900212 | 0.2489% |
| `MARGIN_Q` | w2/s0 | 5 | 516 | 9 | no | 327.234381 | 0.3577% |
| `MARGIN_Q` | w2/s0 | 6 | 520 | 14 | no | 296.033969 | 0.2753% |
| `MARGIN_Q` | w2/s0 | 7 | 524 | 5 | no | 256.737133 | 0.4893% |
| `MARGIN_Q` | w2/s1 | 0 | 549 | 8 | no | 99.588349 | 0.0899% |
| `MARGIN_Q` | w2/s1 | 1 | 458 | 9 | no | 461.281426 | 0.7721% |
| `MARGIN_Q` | w2/s1 | 2 | 523 | 8 | no | 114.852945 | 0.1605% |
| `MARGIN_Q` | w2/s1 | 3 | 498 | 5 | no | 39.332641 | 0.0249% |
| `MARGIN_Q` | w2/s1 | 4 | 509 | 9 | no | 401.202182 | 0.7018% |
| `MARGIN_Q` | w2/s1 | 5 | 524 | 3 | no | 493.619800 | 0.8962% |
| `MARGIN_Q` | w2/s1 | 6 | 502 | 7 | no | 318.565881 | 0.4395% |
| `MARGIN_Q` | w2/s1 | 7 | 527 | 7 | no | 161.528266 | 0.2499% |
| `MARGIN_Q` | w3/s0 | 0 | 460 | 8 | no | 130.531666 | 0.3122% |
| `MARGIN_Q` | w3/s0 | 1 | 478 | 14 | no | 198.114746 | 0.3291% |
| `MARGIN_Q` | w3/s0 | 2 | 401 | 9 | no | 49.905543 | 0.1558% |
| `MARGIN_Q` | w3/s0 | 3 | 483 | 6 | no | 122.014147 | 0.3956% |
| `MARGIN_Q` | w3/s0 | 4 | 422 | 13 | no | 382.927090 | 1.1568% |
| `MARGIN_Q` | w3/s0 | 5 | 428 | 15 | no | 396.236597 | 1.0675% |
| `MARGIN_Q` | w3/s0 | 6 | 459 | 12 | no | 205.052724 | 0.2401% |
| `MARGIN_Q` | w3/s0 | 7 | 449 | 7 | no | 275.737734 | 0.2129% |
| `MARGIN_Q` | w3/s1 | 0 | 442 | 7 | no | 44.424052 | 0.7757% |
| `MARGIN_Q` | w3/s1 | 1 | 387 | 7 | no | 203.914652 | 0.1330% |
| `MARGIN_Q` | w3/s1 | 2 | 459 | 7 | no | 255.202287 | 0.3290% |
| `MARGIN_Q` | w3/s1 | 3 | 408 | 9 | no | 120.627909 | 0.0935% |
| `MARGIN_Q` | w3/s1 | 4 | 397 | 4 | no | 215.805326 | 0.2688% |
| `MARGIN_Q` | w3/s1 | 5 | 437 | 6 | no | 206.544321 | 0.1880% |
| `MARGIN_Q` | w3/s1 | 6 | 449 | 6 | no | 169.365581 | 1.2870% |
| `MARGIN_Q` | w3/s1 | 7 | 472 | 6 | no | 138.952737 | 0.1977% |
| `MARGIN_Q` | w4/s0 | 0 | 486 | 12 | no | 105.865002 | 0.2328% |
| `MARGIN_Q` | w4/s0 | 1 | 450 | 18 | no | 322.124293 | 0.4629% |
| `MARGIN_Q` | w4/s0 | 2 | 479 | 11 | no | 94.036909 | 0.1029% |
| `MARGIN_Q` | w4/s0 | 3 | 471 | 17 | no | 117.716648 | 0.2103% |
| `MARGIN_Q` | w4/s0 | 4 | 503 | 10 | no | 199.166014 | 0.3580% |
| `MARGIN_Q` | w4/s0 | 5 | 446 | 13 | no | 200.605146 | 0.4812% |
| `MARGIN_Q` | w4/s0 | 6 | 485 | 20 | no | 101.769880 | 0.2242% |
| `MARGIN_Q` | w4/s0 | 7 | 461 | 7 | no | 145.827295 | 0.0499% |
| `MARGIN_Q` | w4/s1 | 0 | 423 | 12 | no | 61.152352 | 0.0616% |
| `MARGIN_Q` | w4/s1 | 1 | 461 | 16 | no | 238.071348 | 0.3673% |
| `MARGIN_Q` | w4/s1 | 2 | 455 | 15 | no | 144.126471 | 0.1220% |
| `MARGIN_Q` | w4/s1 | 3 | 441 | 9 | no | 71.621743 | 0.1968% |
| `MARGIN_Q` | w4/s1 | 4 | 465 | 12 | no | 183.360688 | 0.0944% |
| `MARGIN_Q` | w4/s1 | 5 | 429 | 12 | no | 199.235159 | 0.3076% |
| `MARGIN_Q` | w4/s1 | 6 | 446 | 28 | no | 142.600282 | 0.2167% |
| `MARGIN_Q` | w4/s1 | 7 | 454 | 11 | no | 252.098150 | 0.3185% |

## M3 — no genuine upper bound reached

The smallest real anchor in this panel is w1/s0 under the raw assignment-space measure. It still has 100 users, 309 distinct satellite/beam identities, and 2800 user-option edges. The Cartesian legal assignment space is between `10^144` and `10^145` configurations before the physical feasibility and service tests.

Exhaustion of that real instance was not affordable, and the evaluator exposes no relaxation giving a certified global bound. Reducing the user count, beam inventory, horizon, or physics would change sealed inputs or define a synthetic subproblem, so it was not done. The following are therefore **best-known values, not bounds**:

- `SEALED`: 37.574655 Mbit/J (F-best one-swap associated with start 6).
- `MARGIN_Q`: 47.703187 Mbit/J (F-best one-swap associated with start 4).

## M4 — implication for the reference fixed point

- `SEALED`: on this panel, the pooled nearest-eligible reference is 9.8698% below the pooled per-anchor best value found; equivalently, the best found exceeds the reference by 10.9506% (34.570961 vs 38.356680 Mbit/J).
- `MARGIN_Q`: on this panel, the pooled nearest-eligible reference is 3.0615% below the pooled per-anchor best value found; equivalently, the best found exceeds the reference by 3.1582% (47.120580 vs 48.608741 Mbit/J).

These are measured local-search gaps. No claim is made about what a learner could recover, and the best-found values are not global optima.

## Reproduction and receipts

From `/home/sat/mcrl-v025-ladder-ws`:

```console
$ env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python scripts/multistart_ceiling.py run --workers 2 --resume
$ env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python scripts/multistart_ceiling.py report --out MULTISTART-CEILING-2026-09-10.md
```

The run uses at most two concurrent worker processes, one numerical thread each. The runner SHA-256 is `c07561052d2ce564cd87ce17a917b64ee4ed7a59aa16aab3128164265322bdd9` and the verified sealed manifest SHA-256 is `d5e94654510225aaf6ca7f8422ecd12ba64e8f3b8690c55a55d791063db8b916`. There is one digest-protected JSON receipt per rule/anchor in `.scratch/multistart-ceiling-20260910/`. The runner verifies the signed source receipts, the sealed manifest, each cached world digest, and the imported anytime implementation digest before evaluation.

| rule | anchor | receipt SHA-256 |
|---|---|---|
| `SEALED` | w1/s0 | `133252b499d86c6cc3402223b4056f70a3f4010db2619a2f46e3501a2a7b49a2` |
| `SEALED` | w1/s1 | `06ab3e0595ab1cb9b39704f688f49bcad37956b026d3108918fa64a3a9b74519` |
| `SEALED` | w2/s0 | `125827371a16293f19ae535818372b3212abf7ae8f36f5a7db23eb94f7e80797` |
| `SEALED` | w2/s1 | `b046bbb5930957dd0c5d4c4b7ab605daec4c8b217380645f9902b30428eff637` |
| `SEALED` | w3/s0 | `2c2d562b27bd1f3dec410f04fc3580b43023ed17e25aca394e45cc87aec9aadd` |
| `SEALED` | w3/s1 | `b0b19b1af8cac029c5713f71a811122577e5f7d39c23ba4416576da70cbb54f1` |
| `SEALED` | w4/s0 | `21374658aa196f185f2a14f699a9b7cf004c117a029e8b86ffaf02fd00212e54` |
| `SEALED` | w4/s1 | `37dfb90847d85887d24ec0c9ece38e2eb57742729e097dc19f1d20b4feddcddd` |
| `MARGIN_Q` | w1/s0 | `81cf3d2648f41a869e5c115c6504c679c3e7fb66594e380cdd552f78df692776` |
| `MARGIN_Q` | w1/s1 | `a455118209e16c52efb40728a7d0761a007b035d369165995b3828fce9365fd9` |
| `MARGIN_Q` | w2/s0 | `a1badc08b6bf171f981417dfd8c9c9376ec393a0cf0a5fecd13088579aa68252` |
| `MARGIN_Q` | w2/s1 | `ae89a441b06d7e64689944d36aab26f4c08ef06f6f03f741d012607b6b346215` |
| `MARGIN_Q` | w3/s0 | `3becc866a65943f2d33c2c523357ca4882ba5aff31f7eaa76aeb3bebbb7d29f5` |
| `MARGIN_Q` | w3/s1 | `ade4aab7e07ece8077f5b86deb086bd9c0fe9175a4f8be72dd397c0d91148639` |
| `MARGIN_Q` | w4/s0 | `b06a6d186e53a3b675570cc21090ac59a40ae207198b8d600330b8ddff1500fe` |
| `MARGIN_Q` | w4/s1 | `eaaa973593a1fd6f551fe683c0af6e2e60fb29d12f7a627d7e3f23fc709bccdc` |

## What was not reached

No exact global optimum or certified upper bound was obtained. No learner, training, policy, timing claim, search tuning, new traversal order, altered neighbourhood, changed provisioning rule, reduced synthetic instance, or statistical inference was attempted. The diagnostic covers eight declared real anchors and eight starts per anchor, not all twenty anchors or all possible starts. A 2-swap test is still a local certificate; passing it would not establish global optimality.
