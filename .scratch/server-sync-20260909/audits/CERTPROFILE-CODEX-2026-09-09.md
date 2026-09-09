# CERT-PROFILE-2026-09-09

`DIAGNOSTIC_NOT_CLAIM`

## Decisive result

**After the eventual winner was first fully evaluated, certification took 8.788 s at p50, 41.094 s at p95, and 46.770 s at maximum.** For comparison, `t_winner` itself was 1.028 s at p50, 1,073.126 s at p95, and 1,166.562 s at maximum.

| Monotonic offset or interval (s) | n | p50 | p95 | max |
|---|---:|---:|---:|---:|
| `t_certified - t_winner` | 20 | 8.788 | 41.094 | 46.770 |
| `t_winner` | 20 | 1.028 | 1,073.126 | 1,166.562 |
| `t_certified` | 20 | 9.831 | 1,093.770 | 1,213.332 |
| `t_total` | 20 | 9.831 | 1,093.770 | 1,213.332 |
| `t_first`, where a feasible non-BASE candidate existed | 10 | 1.645 | 2.369 | 2.699 |

This is a mixed result. Twelve of 20 anchors found their eventual winner early and spent longer eliminating competitors than finding the winner. Eight of 20 found the winner late. The extreme tail is unambiguously the second group: its winners appeared only after 534.862–1,166.562 s, while certification after that took 11.440–46.770 s. Thus the ordinary/short decisions are mostly **winner found early, certified late**, but the slow tail that motivated this diagnostic is **winner found late**.

The classification rule in this report is mechanical: “winner late” means `t_winner > t_certified - t_winner`; otherwise it is “certification late.” Quantiles use linear interpolation over this deliberately tail-enriched diagnostic panel, so they are not estimates of the full anchor population.

## Scope and clocks

The measured reference procedure is the independently budgeted `S_UNI` exact unilateral best-response selector. It is the path with the 10.0 s production compute budget and 0.5 s guard. All offsets use `time.perf_counter()` from entry to `_s_uni_select`, which is also where its production budget clock starts. The clock therefore includes legal-option construction and the initial BASE solve; tape loading and evaluator construction are outside both the production budget and these offsets.

I screened all 90 available anchors (30 steps × three carriers) under the unchanged production cutoff. Seventy-nine were cut off. The uncensored panel contains all 11 production completions, the two misses with the largest observed cutoff-screen wall times, and seven additional deterministic cutoff misses spanning zero- and multi-iteration outcomes and all three carrier policies. No anchor was sampled randomly, and uncensored timing was not used to choose the panel. I then reran those 20 anchors with cutoff enforcement disabled and made no other rule or parameter change. All 20 ran to the reference procedure's normal `NO_IMPROVING_LEGAL_UNILATERAL` completion. One process was used throughout, under `nice -n 10`; there were no parallel intervals to sum.

The timestamps mean:

- `t_first`: completion of the first legal, valid, non-BASE candidate satisfying the served-user guard. A dash means no feasible new candidate was found; it is not missing telemetry.
- `t_winner`: first complete evaluation of the assignment returned at normal completion. This can be the initially evaluated BASE assignment.
- `t_certified`: completion of the no-improvement pass that establishes that no remaining unilateral candidate in the reference procedure can beat the returned assignment.
- `t_total`: full selector wall time. Here it equals `t_certified` at the shown precision because the selector returns immediately after writing its trace.

## Per-anchor timestamps and classification

| Step / carrier | `t_first` (s) | `t_winner` (s) | certify-after-win (s) | `t_total` (s) | case |
|---|---:|---:|---:|---:|---|
| 23 / nearest-eligible | 1.660 | 1,166.562 | 46.770 | 1,213.332 | winner late |
| 14 / nearest-eligible | 2.699 | 1,068.208 | 19.269 | 1,087.477 | winner late |
| 15 / nearest-eligible | 1.866 | 893.446 | 24.437 | 917.882 | winner late |
| 1 / random-masked | 1.088 | 860.711 | 15.695 | 876.406 | winner late |
| 0 / nearest-eligible | 1.630 | 756.941 | 22.292 | 779.233 | winner late |
| 9 / nearest-eligible | 1.966 | 728.076 | 11.440 | 739.516 | winner late |
| 6 / stay-if-possible | 1.327 | 590.259 | 40.795 | 631.054 | winner late |
| 25 / nearest-eligible | 0.867 | 534.862 | 13.697 | 548.559 | winner late |
| 13 / nearest-eligible | — | 1.752 | 9.336 | 11.088 | certification late |
| 17 / nearest-eligible | — | 0.994 | 9.413 | 10.408 | certification late |
| 6 / nearest-eligible | — | 1.015 | 8.239 | 9.254 | certification late |
| 1 / nearest-eligible | — | 0.949 | 7.930 | 8.879 | certification late |
| 29 / nearest-eligible | — | 1.019 | 7.428 | 8.447 | certification late |
| 5 / stay-if-possible | — | 0.935 | 6.969 | 7.904 | certification late |
| 21 / nearest-eligible | — | 1.038 | 6.713 | 7.750 | certification late |
| 5 / nearest-eligible | — | 0.914 | 6.183 | 7.097 | certification late |
| 28 / stay-if-possible | — | 0.799 | 5.791 | 6.589 | certification late |
| 28 / nearest-eligible | — | 0.787 | 5.606 | 6.393 | certification late |
| 28 / random-masked | 1.308 | 1.001 | 5.316 | 6.318 | certification late |
| 26 / nearest-eligible | 1.828 | 0.804 | 5.384 | 6.188 | certification late |

## Exclusive wall-time ledger

The ledger reconciles exactly to `t_total` for every decision (maximum absolute reconciliation error 0.0 s). “Oracle” is wall time in unique physical evaluations; since this path is serial, its critical path is that same wall time. Cache lookups and score comparisons are in search bookkeeping. Validation/output is the small residual after the explicitly timed input, generation, oracle, and search sections; it includes trace/count bookkeeping and result finalization. Waiting is zero.

| Exclusive bucket (s) | p50 | p95 | max | pooled seconds | pooled share |
|---|---:|---:|---:|---:|---:|
| Input and precompute | 0.003 | 0.003 | 0.003 | 0.054 | 0.001% |
| Candidate generation | 0.091 | 6.120 | 6.299 | 36.341 | 0.527% |
| Search bookkeeping | 0.004 | 88.062 | 93.294 | 539.982 | 7.837% |
| Unique oracle solves, critical path | 9.726 | 1,015.313 | 1,152.345 | 6,307.735 | 91.552% |
| Validation and output | 0.013 | 0.811 | 0.956 | 5.663 | 0.082% |
| Waiting | 0.000 | 0.000 | 0.000 | 0.000 | 0.000% |
| **Total** | — | — | — | **6,889.775** | **100.000%** |

The tail is not candidate-object construction: 91.552% of pooled wall time is in exact physical oracle solves. The late-winner anchors require 41–86 completed best-response improvements and repeatedly solve large candidate sets before reaching the assignment that ultimately wins.

## Counts

“Unique assignments” counts distinct proposed mappings, excluding the separately evaluated BASE mapping. “Exact solves” counts boundary-level physical solves; the initial BASE evaluation accounts for 48 solves and each dense candidate evaluation uses the decision boundary. Cache hits include batch and scalar cache lookups.

| Step / carrier | proposed | unique assignments | cache hits | exact solves | fixed-point iterations | BR iterations |
|---|---:|---:|---:|---:|---:|---:|
| 23 / nearest-eligible | 143,100 | 141,646 | 144,607 | 141,694 | 323,403,101 | 52 |
| 14 / nearest-eligible | 175,500 | 173,710 | 177,355 | 173,758 | 194,644,087 | 64 |
| 15 / nearest-eligible | 113,400 | 112,254 | 114,588 | 112,302 | 224,594,030 | 41 |
| 1 / random-masked | 234,900 | 232,494 | 237,393 | 232,542 | 230,117,127 | 86 |
| 0 / nearest-eligible | 137,700 | 136,302 | 139,149 | 136,350 | 156,839,252 | 50 |
| 9 / nearest-eligible | 234,900 | 232,494 | 237,393 | 232,542 | 102,882,003 | 86 |
| 6 / stay-if-possible | 126,900 | 125,614 | 128,233 | 125,662 | 127,632,317 | 46 |
| 25 / nearest-eligible | 218,700 | 216,462 | 221,019 | 216,510 | 75,750,125 | 80 |
| 13 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 1,590,615 | 0 |
| 17 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 1,822,229 | 0 |
| 6 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 1,554,413 | 0 |
| 1 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 1,639,053 | 0 |
| 29 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 1,811,401 | 0 |
| 5 / stay-if-possible | 2,700 | 2,700 | 2,701 | 2,748 | 986,738 | 0 |
| 21 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 894,473 | 0 |
| 5 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 703,364 | 0 |
| 28 / stay-if-possible | 2,700 | 2,700 | 2,701 | 2,748 | 934,360 | 0 |
| 28 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 934,360 | 0 |
| 28 / random-masked | 2,700 | 2,700 | 2,701 | 2,748 | 1,358,906 | 0 |
| 26 / nearest-eligible | 2,700 | 2,700 | 2,701 | 2,748 | 777,557 | 0 |

| Count distribution | p50 | p95 | max | panel total |
|---|---:|---:|---:|---:|
| Proposed candidates | 2,700 | 234,900 | 234,900 | 1,417,500 |
| Unique assignments | 2,700 | 232,494 | 232,494 | 1,403,376 |
| Cache hits | 2,701 | 237,393 | 237,393 | 1,432,149 |
| Exact solves | 2,748 | 232,542 | 232,542 | 1,404,336 |
| Fixed-point iterations | 1,725,227 | 234,781,426 | 323,403,101 | 1,450,869,511 |
| Best-response iterations | 0 | 86 | 86 | 505 |

## What the production cutoff hid

The production cutoff uses an effective deadline of 9.5 s (10.0 s budget minus the unchanged 0.5 s guard), including a predictive “do not start another batch” check. Nine panel anchors were actually truncated during screening. Their uncensored replay completion times were:

| Step / carrier | cutoff-screen wall (s) | uncensored completion (s) |
|---|---:|---:|
| 25 / nearest-eligible | 9.975 | 548.559 |
| 9 / nearest-eligible | 9.661 | 739.516 |
| 1 / random-masked | 9.424 | 876.406 |
| 1 / nearest-eligible | 9.412 | 8.879 |
| 6 / stay-if-possible | 9.362 | 631.054 |
| 0 / nearest-eligible | 9.327 | 779.233 |
| 14 / nearest-eligible | 9.311 | 1,087.477 |
| 15 / nearest-eligible | 9.307 | 917.882 |
| 23 / nearest-eligible | 9.239 | 1,213.332 |

Eight of those nine needed 548.559–1,213.332 s. Step 1 / nearest-eligible completed in 8.879 s on uncensored replay; its earlier cutoff is consistent with the predictive batch guard plus run-to-run wall-time variation, rather than a claim that the replay must exceed 10 s. Conversely, steps 13 and 17 completed during screening but took 11.088 s and 10.408 s on uncensored replay. On the replay timings, 10 of 20 decisions crossed the 9.5 s effective deadline. This is why the censoring outcome and a single replay's `t_total` are reported separately.

## Requirement for a valid pruning bound

The engine's structure admits a conservative bound in principle, but it does not currently produce one that can certify pruning. For a fixed active set, target-mode branch, caps, and forced-cap mask, the power update is a nonnegative capped affine map initialized at zero. A useful certificate could bound its least fixed point with a proven contraction/resolvent argument or with monotone lower and valid supersolution upper iterates, then propagate interval SINR, energy, service-guard, score, and tie-order bounds. Crucially, the ACM selection and decode functions contain hard SINR thresholds: if an enclosure crosses any transmit-mode or realized-decode threshold, the bound must branch on that crossing or retain both outcomes and use the score-favourable endpoint. A Lipschitz enclosure around the current fixed-point iterate alone is therefore invalid. Safe pruning would require a competitor's threshold-aware score upper bound to be strictly below a certified incumbent lower bound, including the exact tie rule. The finite candidate set, monotone capped interference map, finite threshold set, and piecewise score make such a bound possible; however, the current residual is explicitly not treated as an error upper bound without a contraction proof, so the present engine has no valid pruning certificate to use.

## Reproducibility and verification

- Baseline workspace commit: `17dbde4` (`stage-4h baseline for cert profiling`), archived from requested source commit `75c5c78c`.
- Prepared tape: `V025_PROBE_R2/world/1`, SHA-256 `a7d222eab02789c26de423f7cd87d7e2f677c574f64fb181bd98ec799fdec704`.
- Raw per-decision data: `.scratch/cert-profile/s-uni-profile.json`, SHA-256 `efd2da7659b5a3ab198963a6b2b153a349aa5210daf1189513eb257fb0feaee1`.
- Driver: `scripts/profile_s_uni_certification.py`.
- Runtime: `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, one process, `nice -n 10`.
- Verification: runner and driver compile; `tests/physics_v025/test_stage4d_gate.py` passes (22 tests). The ledger reconciles exactly for all 20 rows and all uncensored timestamp orders satisfy `t_winner <= t_certified <= t_total`.

Trace emission and uncensored execution are opt-in. The production cutoff remains the default, and no threshold, sign, seed, horizon, price, service guard, acceptance rule, 10 s budget, or 0.5 s guard was changed.
