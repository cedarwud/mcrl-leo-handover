# V025 stages 6–8 contract — v1.1 amendment (controller; sealed 2026-09-09 ≈ 00:35 UTC; before any successor training)

v1 (sha ba867d0d…) is preserved unchanged. This amendment applies the real-merger T3 calibration of stage C build 3 (`V025-STAGEC-BUILD3-REPORT-2026-09-08.md`: 200 Monte-Carlo replications per cell, 160 dates, two unequal-energy worlds per date × learner-seed cell, planning alternative +2 %, claim margin +0.5 %, 49 two-way bootstrap draws per replication, 7.3 M authenticated receipts):

| date SD | seed SD | learner seeds | interval coverage | three-contrast conjunction power |
|---:|---:|---:|---:|---:|
| 5 % | 1 % | 5 | 0.863 ± 0.028 | 0.380 ± 0.067 |
| 5 % | 1 % | 12 | 0.878 ± 0.026 | 0.495 ± 0.069 |
| 5 % | 1 % | 16 | 0.893 ± 0.025 | 0.675 ± 0.065 |
| 5 % | 1 % | 24 | 0.908 ± 0.023 | 0.675 ± 0.065 |
| 3 % | 1 % | 12 | 0.893 ± 0.025 | 0.920 ± 0.038 |
| 3 % | 1 % | 16 | 0.920 ± 0.022 | 0.980 ± 0.019 |

1. **§C7 / §D1 — learner seeds: 16** (from 12). Beyond 16 the conjunction power does not improve at a 5 % date SD (the date component caps precision); 16 seeds give 0.68 (5 % date SD) to 0.98 (3 % date SD) measured conjunction power at Δ* = +2 %. Seeds are derived from `V025_LEARNER/seed/{1..16}`. Panel: 6 arms × 16 seeds × 2 worlds per date over ≈ 160 claim dates (≈ 320 worlds per arm-seed); training cost 96 arm-seed lineages.
2. **§E — power statement replaced by the measured table above.** The analytic estimate of v1 §E is withdrawn; the claim wording carries the measured power at the assumed variance components and states that the actual date/seed SDs are estimated from the run and reported beside it.
3. **§D2 — coverage disclosure.** The two-way pigeonhole percentile interval under-covers at these seed counts (0.89–0.92 measured against 0.95 nominal). The sealed decision rule is unchanged (declared before any outcome), and the report states the measured coverage next to every interval; no post-hoc widening is applied.
4. Everything else in v1 stands. Remaining `CONTROLLER_DECIDE` from build 3 (coalition feature scales, neutral-source seals, catalogue CB-2 construction, formal allocation manifest, operational capability values, causal operational variant) are seal-time items resolved with the launch package and the stage-C spec v1 seal.

Seal: sha256 in the companion `.sha256` file.
