**Neither Q1 v2 nor Q2 v2 contains per-option `nominal_gain` (or sufficient primitives), so the learned system structurally cannot represent the rule that reaches 41.622, regardless of training, schedule or corpus; median `a0→RSS_MAX` Hamming distance is 92.5/100, with features binding C1, the target binding C2, and candidates binding C3 (optimisation is secondary).**

`DESIGN_PHASE_DIAGNOSTIC_NOT_A_CLAIM`

The external `BASELINE`/MODQN arm remains the only acceptance gate. `RSS_MAX` and the crowded endpoint are instruments for finding missing capabilities; no result below is a pass/fail comparison against either one. Loss, level `R²`, ordering, and top-1 are not evidence about EE. All endpoint measurements use the full-buffer decoded-bit numerator with no demand cap.

## Executive finding

The two instruments expose two different omissions.

- `RSS_MAX` asks for a local fact: the wanted-link gain of **this candidate option** at the decision boundary. The physical RSS action is already in every learned action table (1,200/1,200 user-anchor tables), but neither current schema gives the heads that fact or enough geometry to reconstruct it. This is a feature/representation limitation.
- The crowded endpoint asks for a global move: coordinate many users onto very few beams. Relative to the learned proposal, that endpoint differs for a median 93 users. C3's bounded catalogue is overwhelmingly singleton/pair support, so it generally cannot offer that kind of move. This is primarily a candidate limitation.
- The learned selector's differences from the instruments are systematic, not a small tie-breaking effect: against `RSS_MAX`, every differing choice has lower nominal gain; against `CROWDCOST`, 99.13% of differing learned choices land on a less-occupied beam.

## Evidence classes and scope

- **[RUN:E500-16]** means newly verified by code over the 12 development anchors (`V025_PROBE/world/1`, steps 0–3 × the three carriers) and all 16 `FULL`, epoch-500 checkpoints listed below.
- **[RUN:SCHEMA]** means verified by importing/reading the versioned schema code with the mandated interpreter.
- **[DERIVED]** means arithmetic or a direct consequence of a verified construction.
- **[INFERRED]** means the design interpretation or proposed successor.

No 48-anchor evaluation-only claim dates were read. The frozen source tree, venv, checkpoints, schemas, arm definitions, and receipts were read-only.

## Part 1 — expressibility first

### Answer

**[RUN:SCHEMA] `nominal_gain` is absent as a per-option computable quantity.** It is not serialized directly, no serialized field is a monotone transform of it, and the union of Q1-v2 and Q2-v2 does not contain the required physical primitives. A field can vary by candidate row without being the focal wanted-link gain: several fields below are full-configuration aggregates copied into the candidate row.

The provider computes decision-boundary gain as

`TxGain(off_axis_angle) × nominal_path(slant_range, elevation, peak_rx_gain)`.

Q1 v2 has per-option off-axis angle and elevation, but not slant range, satellite position/altitude, or an equivalent path factor. Q2 v2 has future elevations but lacks current off-axis angle and slant/path factor. The exact formula is in [provider_legacy.py](/home/sat/mcrl-v025-retrain-ws/src/mcrl/physics_v025/provider_legacy.py:717) and [link_budget.py](/home/sat/mcrl-v025-retrain-ws/src/mcrl/env/link_budget.py:664).

Therefore: **the learned system structurally cannot represent the rule that reaches 41.622, regardless of training, schedule or corpus.** The minimal repair is one scalar on every legal-option row, such as `decision_boundary_log_nominal_gain_db = 10 log10(nominal_gain)`. It is strictly monotone, preserves `RSS_MAX`'s ranking, and is naturally a Q1 field. Supplying raw slant range would also complete Q1's primitive set, but is a larger and less robust interface because it asks the head to learn the antenna/path formula.

### Q1 v2: all 15 serialized fields, 14 effective

The authoritative order and digest are in [q1_schema_v2.py](/home/sat/mcrl-v025-design-ws/q1_schema_v2.py:73). **[RUN:SCHEMA]** The supplied `66ed4a3f9222ac7f20f4334ffab92f6164d2dad203cbac7f7d4e1728ae4ad654` is the canonical **schema-object** digest; the source-file byte digest is `300c74174efb4c518011a1bfc4186d5036c0ecfac809f6bdf0dcfe4744430c06`.

| # | field | locality | gain status |
|---:|---|---|---|
| 1 | `nominal_sinr_margin_at_rate_target` | per-option full-configuration aggregate | Not sufficient: profile-wide minimum margin, confounded by all active users/interference. |
| 2 | `nominal_required_power_over_cap` | per-option full-configuration aggregate | Not sufficient: profile-wide maximum required power/cap. |
| 3 | `nominal_mode_spectral_efficiency` | per-option full-configuration aggregate | Not sufficient: profile mean ACM SE. |
| 4 | `background_occupancy_excluding_focal` | per-option beam | Occupancy, not wanted-link gain. |
| 5 | `satellite_active_before_focal` | per-option satellite indicator | Not gain. |
| 6 | `off_axis_angle` | per-option wanted-link primitive | Partial only; missing slant/path factor. |
| 7 | `focal_link_elevation` | per-option wanted-link primitive | Partial only; missing slant/path factor. |
| 8 | `remaining_d2_time` | per-option lifetime | Future eligibility does not determine current gain. |
| 9 | `remaining_visibility_time` | per-option lifetime | Future visibility does not determine current gain. |
| 10 | `refresh_phase` | per-user value repeated over options | Cannot rank options. |
| 11 | `previous_served_association_for_action` | per-option incumbency indicator | Not gain. |
| 12 | `previous_served_load_for_action` | per-option previous-beam load | Not gain. |
| 13 | `previous_satellite_active_for_action` | per-option previous-satellite indicator | Not gain. |
| 14 | `previous_beam_max_rf_over_cap` | per-option previous-beam statistic | Not current gain. |
| 15 | `missing_incumbent` | per-user value repeated over options | Cannot rank options; structurally zero on the measured panel, hence the 14 effective dimensions. |

### Q2 v2: all 21 serialized fields, 18 effective

The authoritative order is in [q2_schema_v2.py](/home/sat/mcrl-v025-c1c2suff-ws/q2_schema_v2.py:66). It removes four exact redundancies from Q2 v1 and adds three forecast-offset elevations.

| # | field | locality | gain status |
|---:|---|---|---|
| 1 | `candidate_current_nominal_decoding_margin` | per-option full-configuration aggregate | Not sufficient: network-profile minimum, not focal direct gain. |
| 2 | `forecast_se_trend` | per-option projected-configuration aggregate | Not current focal gain. |
| 3 | `remaining_d2_time` | per-option lifetime | Not current gain. |
| 4 | `remaining_visibility_time` | per-option lifetime | Not current gain. |
| 5 | `refresh_phase` | per-user value repeated over options | Cannot rank options. |
| 6 | `background_occupancy_excluding_focal` | per-option beam | Occupancy, not gain. |
| 7 | `satellite_active_before_focal` | per-option satellite indicator | Not gain. |
| 8 | `required_power_cap_margin` | per-option full-configuration aggregate | Not sufficient: cap minus profile-wide maximum power; constant on this panel. |
| 9 | `missing_incumbent` | per-user value repeated over options | Cannot rank options; constant on this panel. |
| 10 | `offset_1_survival` | per-option future indicator | Not current gain. |
| 11 | `offset_1_minimum_decoding_margin` | per-option future configuration aggregate | Not current focal gain. |
| 12 | `offset_1_mean_acm_spectral_efficiency` | per-option future configuration aggregate | Not current focal gain. |
| 13 | `offset_1_focal_link_elevation` | per-option future geometry | Future elevation alone is insufficient. |
| 14 | `offset_2_survival` | per-option future indicator | Not current gain. |
| 15 | `offset_2_minimum_decoding_margin` | per-option future configuration aggregate | Not current focal gain. |
| 16 | `offset_2_mean_acm_spectral_efficiency` | per-option future configuration aggregate | Not current focal gain. |
| 17 | `offset_2_focal_link_elevation` | per-option future geometry | Future elevation alone is insufficient. |
| 18 | `offset_3_survival` | per-option future indicator | Not current gain; constant zero on this panel. |
| 19 | `offset_3_minimum_decoding_margin` | per-option future configuration aggregate | Not current focal gain. |
| 20 | `offset_3_mean_acm_spectral_efficiency` | per-option future configuration aggregate | Not current focal gain. |
| 21 | `offset_3_focal_link_elevation` | per-option future geometry | Future elevation alone is insufficient. |

There is no hidden action-identity escape hatch: the C1 and C2 heads receive only their numeric state vectors. A per-user summary also would not fix this because `RSS_MAX` requires a value for **each legal option**.

One provenance nuance strengthens rather than weakens this answer. **[RUN:E500-16]** The named frozen run is `V025_CONTRACT_V1`: Q1 width 16/digest `c002…` and Q2 width 22/digest `a891…`, not the later schema successors. Its exact builder put a literal zero in the off-axis slot and had no focal-elevation field. Thus the measured `a0` heads have even less direct-link geometry than the v2 schemas audited above; this report does not mislabel them as v2 checkpoints. See [launch-receipt.json](/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/launch-receipt.json:353).

## Part 2 — structural diff

### User-level distances across anchors

Each cell is `median [min,max]` users over the 16 frozen epoch-500 checkpoints (`E500-16`), out of 100 users per anchor.

| development anchor | `a0→RSS_MAX` | `a0→CROWDCOST` |
|---|---:|---:|
| step 0 / nearest | `97 [88,100]` | `92 [85,96]` |
| step 0 / stay | `94.5 [91,98]` | `92 [90,97]` |
| step 0 / random | `80 [73,93]` | `94 [92,99]` |
| step 1 / nearest | `100 [100,100]` | `92 [91,98]` |
| step 1 / stay | `76 [75,79]` | `90 [82,92]` |
| step 1 / random | `95 [79,99]` | `92.5 [87,95]` |
| step 2 / nearest | `100 [98,100]` | `93 [87,100]` |
| step 2 / stay | `73 [70,79]` | `91 [87,95]` |
| step 2 / random | `63 [58,74]` | `98 [95,99]` |
| step 3 / nearest | `99 [88,99]` | `96 [89,97]` |
| step 3 / stay | `75 [70,87]` | `91 [91,100]` |
| step 3 / random | `98.5 [72,100]` | `98.5 [84,100]` |
| pooled checkpoint-anchor observations | **`92.5 [58,100]`**, IQR `76–99` | **`93 [82,100]`**, IQR `91–96` |

**[RUN:E500-16]** These are large changes at every anchor, not isolated users. The raw 16-value distributions keyed to exact seeds are in Appendix B and the machine evidence contains every seed-anchor record.

### What separates the differing choices

The cleanest separators are gain/geometry for `RSS_MAX` and occupancy/concentration for `CROWDCOST`. Rows below pool only users where `a0` differs from the named instrument, over all 192 checkpoint-anchor observations.

| property of `a0` relative to instrument | versus `RSS_MAX` (`n=16,758`) | versus `CROWDCOST` (`n=17,895`) |
|---|---:|---:|
| nominal-gain direction | **lower in 100.00%** | lower in 24.91%; higher in 75.09% |
| nominal-gain delta, median (IQR) | **−1.626 dB** (`−2.676,−0.728`) | `+2.115 dB` (`+0.492,+5.233`) |
| chosen-option nominal-gain rank, median | `a0=5`, RSS=`1` | `a0=4`, crowded=`11` |
| chosen-beam occupancy direction | less occupied in 34.27% | **less occupied in 99.13%** |
| occupancy delta, median users | `0` | **−12** |
| elevation delta, median | **−11.45°** | `0.00°` |
| slant-range delta, median | **+61.23 km** | `0.00 km` |
| learned choice is incumbent | 5.10% | 4.58% |
| instrument choice is incumbent | 0.85% | 1.77% |
| learned choice served in full-48 realised batch | **89.10%** | **89.80%** |
| instrument choice served in same batch | **100.00%** | **100.00%** |

**[INFERRED] Systematic bias.**

- When `a0` disagrees with `RSS_MAX`, it is unambiguously a **lower-direct-gain bias**: every disagreement moves away from nominal rank 1, typically toward rank 5, with lower elevation and longer slant. Incumbency and occupancy do not explain it. The step-3/random anchor also shows checkpoint instability: median learned active beams fall to 5.5 and median served users to 8.5, while other seeds remain much less collapsed; this is why its pooled learned rank can be effectively the null-action rank.
- When `a0` disagrees with the crowded endpoint, it is a **load-spreading bias**: almost every learned choice goes to a beam with fewer co-assigned users. The learned choice usually has more direct gain than the crowded choice, showing the trade: the endpoint gives up local link rank to concentrate fixed beam/circuit costs. It is not an incumbency bias.

These are selection-structure observations. They do not say either instrument is an acceptance target.

## Part 3 — reachability inside the bounded catalogue

The declared support is 36,788 rows: 78.72% `|A|=1`, 19.31% `|A|=2`, and 98.13% `|A|≤2`; the complete size census is recorded in [C3-DECLARED-TARGET-LEARNABILITY-2026-09-10.md](/home/sat/mcrl-v025-coalgen-ws/C3-DECLARED-TARGET-LEARNABILITY-2026-09-10.md:6).

**[RUN:E500-16]** `a0→RSS_MAX` has median Hamming distance 92.5, IQR 76–99, range 58–100. Zero of 192 cases are within size 2; zero are even within size 8. Therefore none of the ordinary singleton, pairwise, or beam-evacuation-sized support can contain the RSS move.

There is one important exception to state honestly: the catalogue has two fixed `|A|=100` S0 profiles per anchor. An exact structural membership check found:

| anchor | reachable checkpoint count / 16 | route into catalogue |
|---|---:|---|
| step 0 / nearest | `1/16` | S0 rank-0 full profile |
| step 1 / nearest | `16/16` | S0 rank-0 full profile |
| step 2 / nearest | `11/16` | S0 rank-0 full profile |
| step 3 / random | `3/16` | S0 rank-0 full profile |
| other eight anchors | `0/16` | none |
| total | **`31/192` reachable; `161/192` unreachable** | no beam evacuation matched RSS |

Why the exception occurs: RSS is already the first nominal-gain proposal for every user. The rank-0 full profile equals RSS exactly when all 100 users must move (`d=100`). It does not rescue distances 58–99. This check enumerated the catalogue's only nonlocal forms—both full S0 profiles and every beam evacuation—rather than inferring absence from the 98.13% statistic alone.

**[INFERRED] Binding constraint.** At 161/192 checkpoint-anchor cases, including every seed at eight of the twelve anchors, the candidate set is binding: the heads cannot select a configuration that is not offered. In the 31 exceptional cases where the rank-0 full profile is exactly RSS, candidate reachability is not the blocker; feature/target/optimisation and C3 scoring can still be. Thus “candidate” is the correct primary diagnosis for C3, but not a universal claim over every seed-anchor case.

## Part 4 — smallest route-specific changes (proposals only)

| route | smallest useful successor | class | why this is the smallest relevant change | sealed-inventory effect |
|---|---|---|---|---|
| **C1** | Add one per-legal-option `decision_boundary_log_nominal_gain_db` scalar to the Q1 action row. | **feature** | The RSS action is already present for all 1,200 user-anchor tables; the head lacks only the value needed to rank it. A scalar is smaller and safer than adding slant and relearning the link budget. | **Yes.** New schema width/digest and new checkpoints create a successor learned arm; do not mutate the sealed five-arm inventory in place. Owner declaration required. |
| **C2** | Redefine the label as *incremental future value after conditioning/subtracting the current-slot C1 contribution*, rather than letting the absolute persistence label veto current direct-link quality. | **target** | Q2-v2 feature repair did not move top-1 materially, and the prior diagnostic's fixed reading is “target or head,” not missing Q2 geometry. This residual target lets C2 add genuine horizon value after C1 can see gain, instead of competing to relearn the current choice. | **Yes.** This changes the declared route meaning and requires a newly named target/checkpoints/arm successor. Owner declaration required. |
| **C3** | Add one deterministic whole-profile `RSS_MAX` proposal to the bounded catalogue; separately, if pursuing the crowding mechanism, add the exact minimum-cover crowded proposal as a diagnostic candidate. | **candidate** | One row makes the observed 58–99-user RSS moves reachable without expanding combinatorially. The crowd result likewise needs a coordinated profile, not more singleton/pair scoring. Candidate inclusion does not imply acceptance or selection. | **Yes.** Either added profile changes the sealed catalogue and therefore the learned-arm inventory/provenance. This is an owner decision, not a repair. |

**[INFERRED] Optimisation is secondary but real in all three routes.** On level calibration, the sealed head loses to a plain linear reference in the relevant held-out checks: C1 cross-world `−0.1605` versus `−0.0896`; Q2-v2 LOAO `−34.6314` versus `−1.8406`; C3-v2 LOAO `−0.0685` versus `0.0365`. See [C1 v2](/home/sat/mcrl-v025-c1c2-ws/C1-DECLARED-TARGET-LEARNABILITY-V2-2026-09-10.md:100), [Q2 v2](/home/sat/mcrl-v025-c1c2suff-ws/Q2-SCHEMA-V2-AND-RETEST-2026-09-10.md:200), and [C3 v2](/home/sat/mcrl-v025-coalgen-ws/C3-DECLARED-TARGET-LEARNABILITY-2026-09-10.md:124). A calibrated linear head is therefore the first optimisation control to run after each binding feature/target/candidate change. It cannot by itself create absent gain information or absent configurations.

No proposal above is implemented here, and no arm definition or sealed artifact was changed.

## Evaluator and resource compliance

**[RUN:E500-16]** The executable analysis is [analyze.py](/home/sat/mcrl-v025-approach-ws/.scratch/approaching-instruments/analyze.py:1), with machine evidence in [results.json](/home/sat/mcrl-v025-approach-ws/.scratch/approaching-instruments/results.json:1) (SHA-256 `e41db0726b3d9f8477eac1cb9a4071ff98f0e4370c2073e606dc38cf7ae1d56f` at report time). Exact nonlocal catalogue membership is checked in [check_reachability.py](/home/sat/mcrl-v025-approach-ws/.scratch/approaching-instruments/check_reachability.py:1).

The mandatory evaluator rule is asserted in code at [analyze.py](/home/sat/mcrl-v025-approach-ws/.scratch/approaching-instruments/analyze.py:156):

- Per anchor, selection comparison used **one fresh dense** `StepEvaluator(boundary_indices=(0,))`; `BASE` was first in the single `evaluate_many` batch alongside `RSS_MAX`, `CROWDCOST`, and all unique `a0` candidates.
- Scalar `evaluate` was replaced in the instance with a function that raises, and the recorded scalar-call count is zero for all 12 comparisons.
- Endpoints used **one separate fresh realised dense full-48** evaluator per anchor, again one `evaluate_many` call with BASE and all candidates, then cache access only.
- All 24 evaluator assertions passed; there were zero invalid configurations. RSS and crowded endpoint bits/joules reproduced their frozen receipts at `rel_tol=1e-12`, `abs_tol=1e-6`.

The main run used one Python process, the mandated interpreter, niceness 15, every BLAS/thread pin equal to 1, wall time 671.16 s, and peak RSS **1,837,711,360 bytes (1.712 GiB)**, below 5 GB. It printed `anchor k/12` at every anchor and a final peak-RSS line. The reachability audit used one process and peak RSS 151,158,784 bytes. No live training or job was started.

## Appendix A — checkpoint identity (`E500-16`)

Every numeric result labelled `[RUN:E500-16]` uses the `FULL` C1+C2 heads at epoch 500 from exactly these checkpoints. `S01…S16` is the order used in Appendix B.

| alias | learner seed | epoch | checkpoint SHA-256 |
|---|---:|---:|---|
| S01 | `389903013832883586` | 500 | `b158f58e0b7ffa24737ae15a315f18499858a6558edbcf28989b17316e9e3fc0` |
| S02 | `925030429265975792` | 500 | `770297232a4c381ee76649ce9e796b0ec0b141756ec7d08e129b2b5596a58344` |
| S03 | `1437152739566466432` | 500 | `689d96503f10cf0e18fd324fc4c0370e5b2e7bf0f4d5e1623756aab794c932f3` |
| S04 | `2106858948530091040` | 500 | `54c195a49c474cddb86e660e8944f685455d6cedf0029275869d5712f4cb120a` |
| S05 | `2306713132836500212` | 500 | `5649e262457b2ff62c3f69308f73ea957892698dbd38a9e8a68ba1109c76fa65` |
| S06 | `2539879246662512149` | 500 | `dc02949e7dd758ce220cfd76df805965b7c63600c94c459e8533f56721df573f` |
| S07 | `2914121027624601215` | 500 | `ccdf416a2245ae640b40933ac2f6b5edfc0a3ec7e647e364436c7dfc9280549b` |
| S08 | `2947922203589416513` | 500 | `7de1ad6187bae7b5e875eb7b93f0be7bafce3885d9e61a70b802a925b3010e42` |
| S09 | `3155344545377116990` | 500 | `c54a69b518e2aa57e2db28c307795291f789075875bb79216b912a4792fc1e1f` |
| S10 | `5166716249291843642` | 500 | `a17a9d0c96b78c216d47b4ace80a051eba1108a1858ff0bed50aa127d62f0c27` |
| S11 | `5683607794651051129` | 500 | `3fa24b7c171ca4fd884bb5da15c58edca381cf23f70735ec1b932142e17a9fdc` |
| S12 | `6114226365011333154` | 500 | `e5202e36097bdc2305f5eca069031dbe4484b8e5f2f70ede67f8c152476eb407` |
| S13 | `6407676579069309528` | 500 | `391de301059cc046969a8538db6b76d75d166dc90567c733d4658a7add7dda4a` |
| S14 | `7234013715671416945` | 500 | `f48b5b3f7b1a2f77f680d0865f11f1fb12a205a30e0d70757d76f3b41c7783fb` |
| S15 | `7291913070596938501` | 500 | `0a7f348e5c8de0d48a3d92d4d65be281df83fdd80e980feae9ab8873db41c3ba` |
| S16 | `9087876568043732533` | 500 | `a224c9886b854fc616726b113cfdbf4717a58bcd81c5dcccc0618455873cfe24` |

## Appendix B — exact Hamming distributions by checkpoint

Values in each list correspond in order to `S01…S16` above; therefore every value states checkpoint, seed, and epoch without repeating 16 long digests per row.

| anchor | `a0→RSS_MAX` by S01…S16 | `a0→CROWDCOST` by S01…S16 |
|---|---|---|
| `0/nearest` | `97,97,98,94,98,95,99,91,100,88,90,97,91,98,93,99` | `88,85,93,92,93,96,90,92,94,93,94,90,90,93,90,91` |
| `0/stay` | `94,97,94,93,97,92,95,94,95,92,91,95,96,98,95,93` | `92,92,93,93,92,91,91,92,91,91,97,91,90,94,93,94` |
| `0/random` | `83,77,79,81,81,78,77,78,81,73,84,83,76,93,78,89` | `93,96,93,94,93,94,94,94,93,96,93,93,98,92,99,96` |
| `1/nearest` | `100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100` | `92,92,93,92,94,92,92,92,92,98,92,92,94,92,92,91` |
| `1/stay` | `75,78,78,76,75,76,75,75,76,76,79,76,78,75,75,76` | `90,86,90,91,90,86,88,90,90,86,92,82,90,90,85,89` |
| `1/random` | `98,91,95,96,94,96,95,95,94,95,87,99,95,93,81,79` | `93,87,95,94,91,94,94,92,92,88,93,92,94,94,90,91` |
| `2/nearest` | `100,100,100,99,100,100,100,100,99,100,99,100,100,100,98,99` | `98,93,93,90,92,94,96,98,92,90,90,100,93,98,87,93` |
| `2/stay` | `70,72,70,74,70,79,73,79,74,73,73,74,74,72,77,73` | `89,89,91,87,91,95,91,93,89,91,91,87,91,93,91,91` |
| `2/random` | `74,72,61,69,60,62,67,72,62,62,64,69,59,62,72,58` | `99,98,98,98,99,99,98,99,98,98,95,98,98,98,99,95` |
| `3/nearest` | `98,99,99,99,96,99,99,99,99,99,99,99,99,99,88,99` | `94,96,96,96,96,96,97,96,96,94,95,94,96,95,89,96` |
| `3/stay` | `82,76,74,74,86,74,70,74,86,77,70,82,74,87,86,70` | `100,91,91,91,100,91,91,91,100,91,91,100,91,100,100,91` |
| `3/random` | `88,99,87,99,72,100,97,99,100,100,99,81,86,99,98,98` | `90,100,87,100,84,100,92,100,100,100,99,90,91,100,95,98` |

## Completion criterion

Met: all four requested parts are present; all 12 development anchors and all 16 final frozen checkpoints are traceable; the evaluator/resource assertions are machine-checkable; the report separates run, derived, and inferred statements; no evaluation-only dates or sealed artifacts were changed.
