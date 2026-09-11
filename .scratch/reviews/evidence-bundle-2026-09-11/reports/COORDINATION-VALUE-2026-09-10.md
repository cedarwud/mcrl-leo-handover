**From `RSS_MAX`, the smallest realised-EE-improving move is `k=1` at all 12/12 anchors; the best EE improvement rejected by `F` is +7.852367 Mbit/J; only 1/11,847 (0.0084%) improving anchor-moves—and 0/5,814 improving multiuser moves—lies inside exact current catalogue support.**

# COORDVALUE — coordination value at a good operating point

Status: **design-phase diagnostic, not a claim**. This run is learner-free, reads no checkpoint, uses only the 12 frozen development anchors, and does not read the 48 evaluation-only claim dates.

## Plain result

`k=1` improves realised pooled EE from `RSS_MAX` at **every anchor**. The exhaustive improving-singleton counts are 86, 145, 368, and 1,129 at physical steps 0, 1, 2, and 3 respectively; each count repeats across the three carrier anchors at that step because the full-48 physical mapping is carrier-invariant. Thus there is no local EE barrier requiring a coordinated move from `RSS_MAX`. On learner-free grounds, that is decisive against the interaction route as a claim of *necessity*.

The crowded endpoint gives the same contrast: `k=1` improves EE at 12/12 anchors, with 78, 64, 77, and 64 improving singletons at steps 0–3. Coordination can still produce larger moves and the supplied crowded construction still beats the supplied per-user rule in pooled endpoint EE; this diagnostic says that a joint move is not required to obtain the first EE improvement from either good point.

## Verified by running code

### Parity gate

The gate ran before candidate search and passed exactly at the requested rounded values.

| endpoint | pooled bits | pooled joules | pooled EE (Mbit/J) | served |
|---|---:|---:|---:|---:|
| `RSS_MAX` | 1,653,612,586,626.6667 | 39,729.71205047168 | **41.62155981714533** | **1200/1200** |
| crowded | 1,072,637,748,181.2688 | 23,262.395146143634 | **46.110374337746876** | **1200/1200** |
| `BASE` (context only) | 1,121,297,101,614.074 | 101,679.49597005111 | 11.027760227532433 | 960/1200 |

The numerator is full-buffer throughout; there is no demand cap.

### Search budget and evaluator contract

- `k=1`: **exhaustive**, 2,800 candidates per physical step and start, comprising every declared legal non-incumbent identity plus explicit null for every currently assigned user. Across 12 carrier anchors this is 33,600 scored rows per start.
- `k=2,3,4,6,8`: **sampled**, exactly 128 distinct candidates per anchor, start, and k. The deterministic mixture uses top-single combinations, subsets toward the opposite endpoint, common-destination consolidation, and uniform legal edits with a 5% null opportunity. `RSS_MAX` k=2–4 also includes subsets of the prior BASIN2 four-user witness, freshly rescored here. A sampled miss would not be an exhaustive nonexistence result.
- Full-48 physical candidates are carrier-invariant, so each candidate mapping is endpoint-evaluated once per physical step and reused across its three carriers. Every carrier anchor nevertheless receives its own fresh realised dense `StepEvaluator(boundary_indices=(0,))` for `F`, with that carrier's `BASE`, both good starts, and candidates entering through `evaluate_many` on the same evaluator.
- Each physical step uses one separate fresh realised dense full-48 endpoint evaluator. Its initial `evaluate_many` contains all three carrier `BASE` mappings, `RSS_MAX`, and crowded; candidate mappings are then added to that same endpoint evaluator after parity passes.
- `StepEvaluator.evaluate` was replaced class-wide by a raising stub. Final assertion: **PASS, zero scalar calls**. All profile retrievals were from the dense evaluator cache.

The tables below use `improving count / best ΔEE (Mbit/J) / ΔF (bit-score units)`. The best row in every cell is guarded and served **100/100**. `k=1` is exhaustive; every other k is a 128-candidate sample.

### Part 1A — from `RSS_MAX`

| anchor | start EE | min k | k=1 | k=2 | k=3 | k=4 | k=6 | k=8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 (s0, nearest) | 71.838507 | **1** | 86 / +1.395291 / +3.801e8 | 36 / +2.550903 / +2.673e9 | 37 / +3.731228 / +6.155e9 | 32 / +3.750155 / +6.831e9 | 32 / +5.774083 / +7.979e9 | 32 / +7.724753 / +6.997e9 |
| A2 (s0, stay) | 71.838507 | **1** | 86 / +1.395291 / +3.801e8 | 36 / +2.550903 / +2.673e9 | 37 / +3.731228 / +6.155e9 | 32 / +3.750155 / +6.831e9 | 32 / +5.774083 / +7.979e9 | 32 / +7.724753 / +6.997e9 |
| A3 (s0, random) | 71.838507 | **1** | 86 / +1.395291 / +3.801e8 | 36 / +2.550903 / +3.100e9 | 37 / +3.731228 / +5.728e9 | 32 / +3.750155 / +6.404e9 | 32 / +5.774083 / +8.406e9 | 32 / +7.724753 / +6.997e9 |
| A4 (s1, nearest) | 65.792380 | **1** | 145 / +1.405188 / +1.639e9 | 35 / +2.725867 / +1.602e9 | 35 / +3.871808 / +1.877e9 | 37 / +5.028051 / +1.232e9 | 33 / +6.026514 / +2.830e9 | 35 / +7.868036 / +8.747e8 |
| A5 (s1, stay) | 65.792380 | **1** | 145 / +1.405188 / +1.639e9 | 35 / +2.725867 / +1.602e9 | 35 / +3.871808 / +1.877e9 | 37 / +5.028051 / +1.232e9 | 33 / +6.026514 / +2.830e9 | 35 / +7.868036 / +8.747e8 |
| A6 (s1, random) | 65.792380 | **1** | 145 / +1.405188 / +1.639e9 | 35 / +2.725867 / +1.602e9 | 35 / +3.871808 / +1.877e9 | 37 / +5.028051 / +1.232e9 | 33 / +6.026514 / +2.830e9 | 35 / +7.868036 / +4.477e8 |
| A7 (s2, nearest) | 49.718426 | **1** | 368 / +4.951313 / +1.796e9 | 45 / +6.426768 / +1.753e9 | 41 / +6.551727 / +1.473e9 | 51 / +6.032479 / +2.694e9 | 49 / +5.338020 / +7.741e8 | 47 / +6.718188 / +2.817e9 |
| A8 (s2, stay) | 49.718426 | **1** | 368 / +4.951313 / +1.796e9 | 45 / +6.426768 / +1.326e9 | 41 / +6.551727 / +1.046e9 | 51 / +6.032479 / +5.256e9 | 49 / +5.338020 / +3.470e8 | 47 / +6.718188 / +2.817e9 |
| A9 (s2, random) | 49.718426 | **1** | 368 / +4.951313 / +1.796e9 | 45 / +6.426768 / +1.326e9 | 41 / +6.551727 / +1.046e9 | 51 / +6.032479 / +4.829e9 | 49 / +5.338020 / +3.470e8 | 47 / +6.718188 / +3.244e9 |
| A10 (s3, nearest) | 19.836770 | **1** | 1,129 / +1.870268 / +5.833e9 | 78 / +3.635504 / +7.850e9 | 79 / +4.749465 / +8.161e9 | 74 / +5.821658 / +7.185e9 | 79 / +7.520112 / +6.232e9 | 71 / +8.115156 / +8.713e9 |
| A11 (s3, stay) | 19.836770 | **1** | 1,129 / +1.870268 / +6.687e9 | 78 / +3.635504 / +8.277e9 | 79 / +4.749465 / +8.588e9 | 74 / +5.821658 / +8.893e9 | 79 / +7.520112 / +8.368e9 | 71 / +8.115156 / +9.994e9 |
| A12 (s3, random) | 19.836770 | **1** | 1,129 / +1.870268 / +5.833e9 | 78 / +3.635504 / +7.423e9 | 79 / +4.749465 / +7.734e9 | 74 / +5.821658 / +7.185e9 | 79 / +7.520112 / +6.659e9 | 71 / +8.115156 / +8.286e9 |

### Part 1B — from the crowded endpoint

| anchor | start EE | min k | k=1 | k=2 | k=3 | k=4 | k=6 | k=8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 (s0, nearest) | 52.690012 | **1** | 78 / +1.053328 / -4.295e8 | 36 / +1.576739 / +2.115e9 | 42 / +2.300307 / +3.437e9 | 40 / +2.566239 / +3.516e9 | 51 / +3.731623 / +6.990e9 | 43 / +4.081755 / +1.412e10 |
| A2 (s0, stay) | 52.690012 | **1** | 78 / +1.053328 / -4.295e8 | 36 / +1.576739 / +2.115e9 | 42 / +2.300307 / +3.437e9 | 40 / +2.566239 / +3.516e9 | 51 / +3.731623 / +6.990e9 | 43 / +4.081755 / +1.412e10 |
| A3 (s0, random) | 52.690012 | **1** | 78 / +1.053328 / -4.295e8 | 36 / +1.576739 / +1.261e9 | 42 / +2.300307 / +2.583e9 | 40 / +2.566239 / +2.662e9 | 51 / +3.731623 / +6.135e9 | 43 / +4.081755 / +1.284e10 |
| A4 (s1, nearest) | 51.906746 | **1** | 64 / +1.163562 / -3.260e8 | 39 / +1.959105 / +1.078e9 | 45 / +2.195816 / +1.300e9 | 49 / +3.022933 / +3.453e9 | 47 / +3.393517 / +1.013e10 | 59 / +3.769169 / +1.808e10 |
| A5 (s1, stay) | 51.906746 | **1** | 64 / +1.163562 / -3.260e8 | 39 / +1.959105 / +1.078e9 | 45 / +2.195816 / +1.300e9 | 49 / +3.022933 / +3.453e9 | 47 / +3.393517 / +1.013e10 | 59 / +3.769169 / +1.808e10 |
| A6 (s1, random) | 51.906746 | **1** | 64 / +1.163562 / -3.260e8 | 39 / +1.959105 / +1.078e9 | 45 / +2.195816 / +1.300e9 | 49 / +3.022933 / +3.453e9 | 47 / +3.393517 / +1.013e10 | 59 / +3.769169 / +1.723e10 |
| A7 (s2, nearest) | 44.453563 | **1** | 77 / +0.999901 / +1.415e9 | 44 / +1.818595 / +1.536e9 | 49 / +2.203075 / +2.066e8 | 52 / +2.482762 / +6.626e8 | 56 / +3.434485 / +5.961e9 | 57 / +3.999213 / +3.545e9 |
| A8 (s2, stay) | 44.453563 | **1** | 77 / +0.999901 / +1.842e9 | 44 / +1.818595 / +1.963e9 | 49 / +2.203075 / +1.061e9 | 52 / +2.482762 / +1.090e9 | 56 / +3.434485 / +8.950e9 | 57 / +3.999213 / +2.691e9 |
| A9 (s2, random) | 44.453563 | **1** | 77 / +0.999901 / +1.842e9 | 44 / +1.818595 / +1.963e9 | 49 / +2.203075 / +6.337e8 | 52 / +2.482762 / +1.090e9 | 56 / +3.434485 / +1.066e10 | 57 / +3.999213 / +2.691e9 |
| A10 (s3, nearest) | 36.434890 | **1** | 64 / +0.782081 / -2.197e8 | 39 / +1.569240 / +1.973e9 | 57 / +2.410632 / +2.073e9 | 57 / +2.664139 / +1.691e9 | 60 / +3.350228 / +9.156e9 | 58 / +3.821836 / +1.030e10 |
| A11 (s3, stay) | 36.434890 | **1** | 64 / +0.782081 / +2.074e8 | 39 / +1.569240 / +2.400e9 | 57 / +2.410632 / +4.208e9 | 57 / +2.664139 / +3.400e9 | 60 / +3.350228 / +1.044e10 | 58 / +3.821836 / +9.873e9 |
| A12 (s3, random) | 36.434890 | **1** | 64 / +0.782081 / +2.074e8 | 39 / +1.569240 / +2.400e9 | 57 / +2.410632 / +3.354e9 | 57 / +2.664139 / +2.973e9 | 60 / +3.350228 / +1.001e10 | 58 / +3.821836 / +9.873e9 |

The best sampled gain at a larger k is not evidence that all k-user moves are needed or that the sample is globally optimal. The exhaustive fact that decides the barrier question is the nonzero k=1 count at every anchor.

### Service guard

Every raw candidate row records `served` and `start_served`; all starts are 100/100 per anchor. A candidate counts as improving only if `served >= start_served` and ΔEE > 0.

| start | all candidates | guarded | service-dropping | service-dropping with raw ΔEE > 0 |
|---|---:|---:|---:|---:|
| `RSS_MAX` | 41,280 | 39,276 | 2,004 | 456 |
| crowded | 41,280 | 37,395 | 3,885 | 609 |
| combined | 82,560 | 76,671 | 5,889 | 1,065 |

The 1,065 drop-assisted raw EE increases are reported separately and excluded from all improving counts.

## Part 2 — EE/F disagreement

For every one of the 82,560 candidate-anchor rows, the raw log reports:

- full-48 realised bits, joules, EE, ΔEE, and served count;
- boundary-0 realised bits and joules;
- exact rational `F`, physical `B - eta_ref E`, positive `Phi` cost, and exact rational ΔF;
- both sign-disagreement flags and exact catalogue membership.

The deployed score used here is exactly

`F(config) = B - eta_ref E - Phi_cost = runner._objective(profile, calibration) + kappa * runner._phi_for(incumbent, config)`.

`runner._objective` alone is only the physical `B - eta_ref E` core; `Phi` was added explicitly with the fixed prior-step carrier incumbent.

`eta_ref` is exactly

`14235186615308645000000 / 1300834130903823 = 10943122.01465532 bit/J`.

It is loaded as a `Fraction` from [PILOT_NOT_CLAIM-calibration.json](/home/sat/mcrl-v025-c1c2suff-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-calibration.json:1). Its construction is set in [run_v025_pilot_c3.py](/home/sat/mcrl-v025-c1c2suff-ws/scripts/run_v025_pilot_c3.py:274) as realised full-grid `BASE` bits/joules at development step 0.

### Sign-disagreement counts

| start | k | candidates | guarded | EE up | EE up, F down | F up, EE down | drops | drops with raw EE up |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `RSS_MAX` | 1 | 33,600 | 31,959 | 5,184 | 2,544 | 7,638 | 1,641 | 402 |
| `RSS_MAX` | 2 | 1,536 | 1,503 | 582 | 145 | 238 | 33 | 9 |
| `RSS_MAX` | 3 | 1,536 | 1,479 | 576 | 120 | 211 | 57 | 9 |
| `RSS_MAX` | 4 | 1,536 | 1,488 | 582 | 136 | 191 | 48 | 6 |
| `RSS_MAX` | 6 | 1,536 | 1,434 | 579 | 167 | 156 | 102 | 12 |
| `RSS_MAX` | 8 | 1,536 | 1,413 | 555 | 129 | 95 | 123 | 18 |
| **`RSS_MAX` total** | — | **41,280** | **39,276** | **8,058** | **3,241** | **8,529** | **2,004** | **456** |
| crowded | 1 | 33,600 | 30,816 | 849 | 245 | 13,190 | 2,784 | 573 |
| crowded | 2 | 1,536 | 1,413 | 474 | 125 | 598 | 123 | 0 |
| crowded | 3 | 1,536 | 1,353 | 579 | 40 | 533 | 183 | 6 |
| crowded | 4 | 1,536 | 1,326 | 594 | 16 | 552 | 210 | 9 |
| crowded | 6 | 1,536 | 1,251 | 642 | 4 | 439 | 285 | 3 |
| crowded | 8 | 1,536 | 1,236 | 651 | 0 | 437 | 300 | 18 |
| **crowded total** | — | **41,280** | **37,395** | **3,789** | **430** | **15,749** | **3,885** | **609** |
| **combined** | — | **82,560** | **76,671** | **11,847** | **3,671** | **24,278** | **5,889** | **1,065** |

The current objective would reject 3,671 service-guarded EE improvements and would accept 24,278 service-guarded EE decreases in this considered set.

### Best EE gain that `F` rejects

The largest is at A6 (`world/1`, step 1, `random-masked`), from `RSS_MAX`, sampled k=8:

- changed users: `[14, 52, 53, 57, 77, 80, 81, 99]`;
- realised EE: 73.64474711099503 Mbit/J;
- **ΔEE: +7.852366658894908 Mbit/J**;
- exact **ΔF: `-17842408563170872853488684058111 / 26016682618076460000000`** = -685,806,442.9311184 bit-score units;
- service: **100/100**;
- proposal method: top-single combination;
- exact current-catalogue membership: **outside**.

This +7.852367 Mbit/J is the observed cost of the current objective in the metric the project reports, under the stated sampled search. It is a found lower bound on that cost, not a global maximum over all k-user configurations.

For the crowded start, the largest rejected gain is +3.306674982182585 Mbit/J at A7, sampled k=6, ΔF exactly `-262911438195310007899386362769 / 21680568848397050000000`, served 100/100, and outside catalogue support.

## Part 3 — exact current-catalogue reachability

Support was not approximated by `k <= 2`. For every carrier anchor, the deployed bounded-union-v2 catalogue was reconstructed exactly around that carrier's `BASE`: top-8 nominal shortlist, all shortlisted unilaterals, two full-profile proposals, top-10-user/top-2 pair cross-product, and active-beam evacuations. The reconstructed catalogues contain 963–1,007 unique profiles per anchor. Candidate membership is exact full-configuration-ID membership.

For reference, the declared 36,788-row catalogue census is `|A|=1`: 28,960 (78.72%), `|A|=2`: 7,104 (19.31%), and `|A|<=2`: 98.13%. Those declared `|A|` values are `BASE`-relative action sizes; the k below is the changed-set size relative to the good start. Exact full-profile membership, rather than equating those two sizes, is therefore the decisive reachability test.

### Changed-set distribution of improving moves

| k from good start | `RSS_MAX` improving | crowded improving | combined | combined share | inside exact support |
|---:|---:|---:|---:|---:|---:|
| 1 | 5,184 | 849 | 6,033 | 50.9243% | 1 |
| 2 | 582 | 474 | 1,056 | 8.9136% | 0 |
| 3 | 576 | 579 | 1,155 | 9.7493% | 0 |
| 4 | 582 | 594 | 1,176 | 9.9266% | 0 |
| 6 | 579 | 642 | 1,221 | 10.3064% | 0 |
| 8 | 555 | 651 | 1,206 | 10.1798% | 0 |
| **total** | **8,058** | **3,789** | **11,847** | **100%** | **1** |

- `RSS_MAX`: 1/8,058 = 0.012410% of improving rows is in exact support.
- crowded: 0/3,789 = 0% is in exact support.
- combined: 1/11,847 = **0.008441%** is in exact support.
- multiuser only: 0/5,814 = **0%** is in exact support.

The sole supported improvement is A7 (`step 2`, `nearest-eligible`) from `RSS_MAX`, k=1, user 79 to `(63319,49)`: ΔEE +0.5316606604898837 Mbit/J, exact ΔF `-7186059442601371454296726349861 / 2601668261807646000000`, served 100/100. Even that supported move is rejected by `F`.

The improving moves are **not** systematically large relative to the good start: 7,089/11,847 = 59.8379% have k=1 or k=2. Because good-start-relative k is not the catalogue's `BASE`-relative `|A|`, the failure cannot be explained merely by comparing this distribution with the declared 98.13% mass at `|A| <= 2`. Nevertheless, **the catalogue is the binding constraint on the interaction route in exact-support terms**: it contains none of the 5,814 improving multiuser moves considered. The binding mechanism is the catalogue's `BASE` anchoring and restricted identities/combinations, not changed-set size alone.

## Derived on paper

- The exact-support percentages and changed-set shares above are arithmetic over verified integer counts.
- The combined sign counts are sums of the two verified start-specific counts.
- “k=1 at 12/12” follows directly from the exhaustive nonzero singleton counts. It does not depend on any sampled higher-k result.
- The +7.852367 Mbit/J objective cost is the maximum over the verified `EE up, F down` rows that were considered; because k>1 is sampled, it is a lower bound on the maximum possible objective cost.

## Inferred

1. **No coordination barrier at the good point.** Since exhaustive k=1 improves EE at all 12 anchors from `RSS_MAX`, joint action is not necessary to move uphill locally in reported EE. This closes the proposed interaction route if its premise is that a good point creates a k>1 escape barrier.
2. **Objective mismatch is operationally large.** `F` rejects 3,241/8,058 RSS-relative EE improvements and accepts 8,529 EE decreases; the best rejected EE gain is large enough that objective alignment is a first-order issue, not a ranking footnote.
3. **Exact catalogue support is nearly absent.** The current catalogue cannot express the sampled interaction improvements and can express only one of all found improvements. This is a support/anchoring problem even though many improvements have k≤2.
4. **What is not established.** This diagnostic does not show where repeated best singleton steps converge, does not compare their terminal EE with the crowded construction, and does not prove a global best k for sampled k>1. It only answers the local good-point barrier question and records the observed objective/support disagreement.

## Execution receipt

- Python: `/home/sat/mcrl-leo-handover/.venv/bin/python`
- Python processes: 1; niceness: 15
- `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, `BLIS_NUM_THREADS`: all 1
- Peak RSS: **1,787,314,176 bytes = 1.665 GiB**, below 5 GB
- Wall time: 8,159.743316 s
- Progress contract: printed `anchor 1/12` through `anchor 12/12`, plus peak RSS
- Scalar assertion: **PASS — raising stub installed, zero calls**
- Raw candidates: [candidates.jsonl](/home/sat/mcrl-v025-coord-ws/.scratch/coordvalue/candidates.jsonl), 82,560 rows, SHA-256 `79546806b891b73fefe56ae708f9c61972062fefb2eb2787ad7f931c7955a1a2`
- Receipt: [coordvalue-receipt.json](/home/sat/mcrl-v025-coord-ws/.scratch/coordvalue/coordvalue-receipt.json), SHA-256 field `c8a2ffc72204a42926dd7dc3e0a09f41dec656319c8b8e84be8d8af37c57cdce`
- Driver: [run_coordvalue.py](/home/sat/mcrl-v025-coord-ws/.scratch/coordvalue/run_coordvalue.py), SHA-256 `12aed1e0dbadcb0a7b895b0ff6f5ce4cb37b446e6a3c0e392dcf7d48848b47cc`

The validation pass independently parsed all raw rows, checked required EE/F/service fields, matched candidate and driver hashes, reconstructed the receipt's pre-JSON integer histogram keys for its self-digest, and reasserted status COMPLETE, 12 anchors, zero scalar calls, and RSS below 5 GB.
