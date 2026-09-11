**Across 480 frozen checkpoint-anchor decisions, the median learned-interaction-range / FULL top-1/top-2 additive-gap ratio is 0.338757; including learned interaction changes the argmax on 9/20 distinct anchors (36/480 decisions), and exact `psi` can move it (11/20 anchors; 100/480 decisions).**

# Interaction scale and selector argmax — development diagnostic

`DESIGN_PHASE_DIAGNOSTIC_NOT_CLAIM`. This run computes score scales and configuration identities only; it computes no EE and uses no loss value as evidence.

## Verdict

The proposed dead-by-scale hypothesis is **refuted on this panel**: learned interaction changed 36 of 480 checkpoint-anchor argmax decisions, spanning 9 of 20 anchors.
Exact `psi` also changed 100 decisions on 11 anchors, so there is no structural impossibility in the scalar decision rule on this panel.

## Verified by running code

### Scope and provenance

The run used the development-only FULL20 panel: `V025_PROBE_R2/world/{1..4}`, steps 0–4, nearest-eligible carrier (20 anchors). It read cached eight-step development tapes and never opened claim-panel or evaluation-only date material. For each anchor it invoked the deployed `_build_anchor_rows`, `_catalogue_with_census`, `_coalition_context`, stable configuration-ID tie-break, and `_exact_interactions` paths from the read-only harness source, with the matching read-only retrain libraries.

At start it froze the latest complete cadence checkpoint for each seed then present in each live directory: 24 checkpoints total. The complete identity list is below; all aggregated numbers in this report use exactly this list.

| run/schema | seed | epoch | checkpoint SHA-256 | checkpoint |
|---|---|---|---|---|
| V1_CONTRACT | 9087876568043732533 | 400 | `dd509454f3662ecdea565f91c8eaa479251c13881cf11d964b355080d968f455` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-9087876568043732533-epoch-000400.json` |
| V1_CONTRACT | 1437152739566466432 | 500 | `689d96503f10cf0e18fd324fc4c0370e5b2e7bf0f4d5e1623756aab794c932f3` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-1437152739566466432-epoch-000500.json` |
| V1_CONTRACT | 2306713132836500212 | 500 | `5649e262457b2ff62c3f69308f73ea957892698dbd38a9e8a68ba1109c76fa65` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-2306713132836500212-epoch-000500.json` |
| V1_CONTRACT | 2539879246662512149 | 500 | `dc02949e7dd758ce220cfd76df805965b7c63600c94c459e8533f56721df573f` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-2539879246662512149-epoch-000500.json` |
| V1_CONTRACT | 3155344545377116990 | 500 | `c54a69b518e2aa57e2db28c307795291f789075875bb79216b912a4792fc1e1f` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-3155344545377116990-epoch-000500.json` |
| V1_CONTRACT | 389903013832883586 | 500 | `b158f58e0b7ffa24737ae15a315f18499858a6558edbcf28989b17316e9e3fc0` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-389903013832883586-epoch-000500.json` |
| V1_CONTRACT | 5166716249291843642 | 500 | `a17a9d0c96b78c216d47b4ace80a051eba1108a1858ff0bed50aa127d62f0c27` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-5166716249291843642-epoch-000500.json` |
| V1_CONTRACT | 5683607794651051129 | 500 | `3fa24b7c171ca4fd884bb5da15c58edca381cf23f70735ec1b932142e17a9fdc` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-5683607794651051129-epoch-000500.json` |
| V1_CONTRACT | 6114226365011333154 | 500 | `e5202e36097bdc2305f5eca069031dbe4484b8e5f2f70ede67f8c152476eb407` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-6114226365011333154-epoch-000500.json` |
| V1_CONTRACT | 6407676579069309528 | 500 | `391de301059cc046969a8538db6b76d75d166dc90567c733d4658a7add7dda4a` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-6407676579069309528-epoch-000500.json` |
| V1_CONTRACT | 7234013715671416945 | 500 | `f48b5b3f7b1a2f77f680d0865f11f1fb12a205a30e0d70757d76f3b41c7783fb` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-7234013715671416945-epoch-000500.json` |
| V1_CONTRACT | 7291913070596938501 | 500 | `0a7f348e5c8de0d48a3d92d4d65be281df83fdd80e980feae9ab8873db41c3ba` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-7291913070596938501-epoch-000500.json` |
| V1_CONTRACT | 925030429265975792 | 500 | `770297232a4c381ee76649ce9e796b0ec0b141756ec7d08e129b2b5596a58344` | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-925030429265975792-epoch-000500.json` |
| Q1_V2 | 7291913070596938501 | 400 | `7f664d605df9933bb5a4c5970e3cc17bc17f83d7c621d75b275e13031c1ecbc4` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-7291913070596938501-epoch-000400.json` |
| Q1_V2 | 1437152739566466432 | 500 | `db6c7fed39532f5d281173acebcb2635479de79078bba512f93b386252aa8e28` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-1437152739566466432-epoch-000500.json` |
| Q1_V2 | 2306713132836500212 | 500 | `9b5ba3a5777b1b5c6c3674a404f49de75461916d3b0bc15fb7d30b5a39429f95` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-2306713132836500212-epoch-000500.json` |
| Q1_V2 | 2539879246662512149 | 500 | `7f7ace88a4bcdb125d0f2a8a422c14234c64da7504f625f72fb6a202a1697019` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-2539879246662512149-epoch-000500.json` |
| Q1_V2 | 3155344545377116990 | 500 | `e91c22cced9015b71e38644ee39ae2b8144b562a1077396e6e15215e286df867` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-3155344545377116990-epoch-000500.json` |
| Q1_V2 | 389903013832883586 | 500 | `e1a227b2ebbcce1da0306ccb26f435addb981a4f864fa69c31b82ff8b0cbfa21` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-389903013832883586-epoch-000500.json` |
| Q1_V2 | 5166716249291843642 | 500 | `58da313a7b44e99f8c0e9a7acf8f96fb2fbbca8d0127ea96cad2a769bc584f06` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-5166716249291843642-epoch-000500.json` |
| Q1_V2 | 6114226365011333154 | 500 | `e428eefee90973f7edd85589d5e60e1c93d082b95998119105909f83b6109cb4` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-6114226365011333154-epoch-000500.json` |
| Q1_V2 | 6407676579069309528 | 500 | `0ba79d7279519f8a610e4398526f6086e5afce1f350a8dfa34739c8c4e3bc4bb` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-6407676579069309528-epoch-000500.json` |
| Q1_V2 | 7234013715671416945 | 500 | `2d830b72239e176c46c4aaff21033b6be8a75c3b68f0d4852cc0415b987e5144` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-7234013715671416945-epoch-000500.json` |
| Q1_V2 | 925030429265975792 | 500 | `7081948329b8a8fde4db485b0836158eda02d8d8e83c1d248031925e34fe65de` | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-925030429265975792-epoch-000500.json` |

### Score-scale summary by checkpoint family

Each statistic below is the median across the named family’s checkpoint-anchor observations. Additive and interaction values share the learner’s anchor-normalized score units.

| family | seeds | epochs | obs | additive sd | top1–2 gap | \|C3\| max | C3 sd | C3 range | range/gap | C3 flips | exact flips |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1_V2 | 11 | 400,500 | 220 | 89.0746 | 84.9889 | 30.9366 | 1.20075 | 35.4793 | 0.288172 | 16/220 | 43/220 |
| V1_CONTRACT | 13 | 400,500 | 260 | 79.7066 | 75.7159 | 32.5153 | 1.22586 | 37.307 | 0.394981 | 20/260 | 57/260 |

### Per-anchor decisive measurements

`g2/g3/g4/g5` are FULL additive top-1 gaps to ranks 2–5, each median across the frozen checkpoints. Learned C3 summaries and both ratios are medians across those checkpoints. `exact |max|/sd/range` is computed once from exact catalogue `psi`. Flip denominators are the checkpoint count. The receipt retains every unaggregated checkpoint/seed/epoch value.

| anchor | rows | g2/g3/g4/g5 | additive sd | learned \|max\|/sd/range | exact \|max\|/sd/range | learned range/g2 | exact range/g2 | learned flips | exact flips |
|---|---|---|---|---|---|---|---|---|---|
| V025_PROBE_R2/world/1:step/0 | 994 | 44.7827/2035.55/2096.07/2105.11 | 98.3123 | 14.8166/0.704027/16.8963 | 317.738/13.9121/318.685 | 0.42589 | 7.11626 | 0/24 | 0/24 |
| V025_PROBE_R2/world/1:step/1 | 999 | 73.1215/1836.83/1870.32/1894.35 | 88.1771 | 19.0575/0.852547/21.5012 | 1021.65/45.625/1021.65 | 0.280748 | 13.9928 | 0/24 | 1/24 |
| V025_PROBE_R2/world/1:step/2 | 991 | 179.991/1519.66/1526.68/1546.79 | 70.607 | 43.9296/1.49917/50.3651 | 785.833/35.4218/785.833 | 0.266733 | 4.36646 | 0/24 | 1/24 |
| V025_PROBE_R2/world/1:step/3 | 974 | 14.9365/43.774/44.3144/44.4393 | 3.02306 | 127.61/4.81508/129.408 | 3067.25/139.283/3067.25 | 8.15132 | 211.034 | 6/24 | 22/24 |
| V025_PROBE_R2/world/1:step/4 | 992 | 63.3948/2173.25/2262.05/2268.25 | 105.599 | 22.6175/0.895313/30.6085 | 496.329/22.2557/496.72 | 0.518797 | 7.85761 | 0/24 | 3/24 |
| V025_PROBE_R2/world/2:step/0 | 997 | 94.1373/2304.36/2337.33/2352.25 | 108.915 | 31.3545/1.21647/34.929 | 418.3/18.2347/418.3 | 0.35903 | 4.44523 | 1/24 | 1/24 |
| V025_PROBE_R2/world/2:step/1 | 987 | 279.134/2302.8/2354.58/2359.67 | 107.562 | 29.0919/1.03792/37.7897 | 1190.76/53.7367/1190.76 | 0.142795 | 4.27242 | 0/24 | 0/24 |
| V025_PROBE_R2/world/2:step/2 | 978 | 334.016/1781.07/1828.44/1830.8 | 79.7155 | 52.8526/1.72331/55.892 | 434.002/19.688/434.028 | 0.181021 | 1.30037 | 0/24 | 0/24 |
| V025_PROBE_R2/world/2:step/3 | 970 | 19.4216/80.499/80.5517/80.6045 | 4.12308 | 145.421/5.5509/146.39 | 4657.38/210.688/4657.38 | 8.12917 | 240.887 | 11/24 | 21/24 |
| V025_PROBE_R2/world/2:step/4 | 983 | 80.815/1393.28/1408.47/1426.14 | 66.018 | 20.9494/0.786016/25.4359 | 100.973/3.50862/105.166 | 0.280275 | 1.30328 | 1/24 | 6/24 |
| V025_PROBE_R2/world/3:step/0 | 1001 | 35.9392/1590.45/1594.49/1619.17 | 75.3486 | 20/0.707094/21.6647 | 346.389/15.3995/350.635 | 0.539469 | 9.75822 | 2/24 | 0/24 |
| V025_PROBE_R2/world/3:step/1 | 1000 | 148.538/2512.52/2514.72/2538.45 | 116.384 | 22.9195/0.818233/25.9055 | 287.755/12.6147/287.755 | 0.179004 | 1.93746 | 0/24 | 0/24 |
| V025_PROBE_R2/world/3:step/2 | 996 | 215.18/1966.8/1977.89/1986.21 | 90.0777 | 48.8095/1.95063/54.0407 | 583.751/25.4451/583.751 | 0.274666 | 2.71328 | 0/24 | 0/24 |
| V025_PROBE_R2/world/3:step/3 | 971 | 21.7307/64.7228/65.8731/67.1624 | 3.91287 | 143.465/5.88877/146.385 | 3117.8/141.941/3117.8 | 6.21819 | 143.65 | 7/24 | 21/24 |
| V025_PROBE_R2/world/3:step/4 | 1008 | 135.519/3053.32/3077.3/3078.55 | 137.428 | 20.0841/0.82253/24.3981 | 1944.66/86.0506/1944.66 | 0.283926 | 14.5045 | 0/24 | 1/24 |
| V025_PROBE_R2/world/4:step/0 | 1004 | 73.5027/2621.84/2642.06/2659.11 | 124.17 | 16.9814/0.65396/19.7033 | 35.3376/1.53636/36.7176 | 0.220464 | 0.499567 | 0/24 | 0/24 |
| V025_PROBE_R2/world/4:step/1 | 989 | 192.423/1732.3/1772.86/1777.79 | 79.4613 | 20.9452/0.781024/26.2842 | 2591.54/116.392/2591.54 | 0.146884 | 13.469 | 0/24 | 0/24 |
| V025_PROBE_R2/world/4:step/2 | 976 | 367.545/1731.04/1751.71/1755.59 | 75.6416 | 39.7019/1.47815/57.0811 | 513.947/22.7296/515.407 | 0.145637 | 1.40281 | 1/24 | 1/24 |
| V025_PROBE_R2/world/4:step/3 | 965 | 23.3376/64.9521/66.0897/66.174 | 3.36175 | 137.528/5.37608/139.285 | 5157.2/234.948/5157.2 | 7.38266 | 223.512 | 6/24 | 22/24 |
| V025_PROBE_R2/world/4:step/4 | 1005 | 58.0132/3239.95/3257.05/3304.62 | 152.387 | 28.2029/1.11492/29.4172 | 243.086/10.5173/243.086 | 0.501695 | 4.19022 | 1/24 | 0/24 |

## Part 2 — sealed-arm decision differences from FULL

Counts compare the stable catalogue argmax produced by each arm’s own Q1, Q2, and C3 heads with the FULL choice. A zero count means that arm cannot produce a nonzero realised-selection contrast on these observations; it does not say the head learned nothing.

| arm | different decisions | total decisions | distinct anchors with ≥1 difference |
|---|---|---|---|
| FULL | 0 | 480 | 0 |
| DROP_C1 | 45 | 480 | 11 |
| DROP_C2 | 110 | 480 | 14 |
| DROP_C3 | 39 | 480 | 11 |
| ALL_NEUTRAL_CONTROL | 341 | 480 | 20 |

Per-anchor counts (denominator: frozen checkpoints):

| anchor | FULL | DROP_C1 | DROP_C2 | DROP_C3 | ALL_NEUTRAL_CONTROL |
|---|---|---|---|---|---|
| V025_PROBE_R2/world/1:step/0 | 0/24 | 0/24 | 1/24 | 0/24 | 17/24 |
| V025_PROBE_R2/world/1:step/1 | 0/24 | 3/24 | 6/24 | 0/24 | 16/24 |
| V025_PROBE_R2/world/1:step/2 | 0/24 | 0/24 | 0/24 | 0/24 | 17/24 |
| V025_PROBE_R2/world/1:step/3 | 0/24 | 2/24 | 0/24 | 6/24 | 16/24 |
| V025_PROBE_R2/world/1:step/4 | 0/24 | 8/24 | 6/24 | 2/24 | 15/24 |
| V025_PROBE_R2/world/2:step/0 | 0/24 | 3/24 | 5/24 | 1/24 | 18/24 |
| V025_PROBE_R2/world/2:step/1 | 0/24 | 0/24 | 14/24 | 0/24 | 15/24 |
| V025_PROBE_R2/world/2:step/2 | 0/24 | 0/24 | 2/24 | 0/24 | 20/24 |
| V025_PROBE_R2/world/2:step/3 | 0/24 | 4/24 | 0/24 | 11/24 | 17/24 |
| V025_PROBE_R2/world/2:step/4 | 0/24 | 2/24 | 22/24 | 1/24 | 18/24 |
| V025_PROBE_R2/world/3:step/0 | 0/24 | 8/24 | 7/24 | 2/24 | 18/24 |
| V025_PROBE_R2/world/3:step/1 | 0/24 | 0/24 | 10/24 | 0/24 | 18/24 |
| V025_PROBE_R2/world/3:step/2 | 0/24 | 0/24 | 0/24 | 0/24 | 20/24 |
| V025_PROBE_R2/world/3:step/3 | 0/24 | 6/24 | 0/24 | 7/24 | 17/24 |
| V025_PROBE_R2/world/3:step/4 | 0/24 | 6/24 | 10/24 | 1/24 | 17/24 |
| V025_PROBE_R2/world/4:step/0 | 0/24 | 0/24 | 7/24 | 0/24 | 14/24 |
| V025_PROBE_R2/world/4:step/1 | 0/24 | 0/24 | 10/24 | 0/24 | 18/24 |
| V025_PROBE_R2/world/4:step/2 | 0/24 | 0/24 | 0/24 | 1/24 | 18/24 |
| V025_PROBE_R2/world/4:step/3 | 0/24 | 2/24 | 3/24 | 6/24 | 18/24 |
| V025_PROBE_R2/world/4:step/4 | 0/24 | 1/24 | 7/24 | 1/24 | 14/24 |

### Exact-psi and learned-interaction distributions

The receipt contains every checkpoint-anchor value (additive sd and all four top gaps; learned interaction absolute maximum, sd, min, max, and range; learned and exact choices). This report keeps the per-anchor table readable. Exact `psi` values are zero for unchanged/singleton rows by decomposition and were evaluated for every multi-user catalogue row.

The `Q1_V2` checkpoints were evaluated with the declared v2 projection: true boundary-0 off-axis angle and provider elevation, removal of the two exact indicator duplicates, and matching 15-wide member rows. The V1 checkpoints used the deployed 16-wide rows directly. Q2 and the physical catalogue were unchanged.

Here “exact `psi`” means the pilot’s exact joint-minus-singletons decomposition under its nominal boundary-0 `StepEvaluator`, in the same anchor-normalized units consumed by `exact_scores`. It is not a 48-boundary realised EE calculation.

### Resources

One Python process was used with niceness `17`. All BLAS/OpenMP variables were pinned to 1. Peak RSS was **1449.703 MiB**, below the 4 GB cap. Interpreter: `/home/sat/mcrl-leo-handover/.venv/bin/python` (3.13.3).

The process printed a progress line for every checkpoint load and anchor, followed by the peak-RSS line. No training ran; the two live checkpoint directories and all sealed/code inputs were read-only.

## Derived on paper

- Learned-interaction flip rate: `36 / 480 = 7.5000%`; distinct-anchor coverage: `9 / 20`.
- Exact-`psi` flip rate: `100 / 480 = 20.8333%`; distinct-anchor coverage: `11 / 20`.
- The range/gap ratio is a conservative necessary-scale screen, not a sufficient flip test: a range below the top-1/top-2 additive gap proves no interaction can reverse those two rows, while a ratio above one only says a flip is scale-possible. The direct identity comparison is decisive.
- Exact `psi` is an oracle for the declared target scale, not a mathematical upper bound on an unconstrained neural output. Therefore a no-flip exact result is structural for exact-target-scale C3 under this decision rule; an arbitrarily rescaled learned head could still force a flip, but would no longer be calibrated to that target.

## Inferred interpretation

Because exact `psi` moves at least one FULL-additive argmax, the scalar interaction route is not structurally dead everywhere. Any learned/exact flip-rate gap is evidence about learned output scale/alignment, not a proof about information content.

## Part 3 — smallest honest design changes (not implemented)

1. **Freeze a common C3 output-scale calibration against development additive gaps.** This is the smallest intervention if exact `psi` has adequate decision scale but the learned head does not. Apply one preregistered transform to the C3 output in every arm, including the neutral C3 in `DROP_C3` and the control, so the arm inventory remains FULL / DROP_C1 / DROP_C2 / DROP_C3 / ALL_NEUTRAL_CONTROL. It changes the selector and therefore is a declarable scoring/calibration design change; applying it only to FULL or tuning it after route outcomes would silently redefine the contrasts.

2. **Normalize each arm’s additive catalogue surface per anchor before adding C3** (for example by a frozen robust spread). This changes the effective C1:C2:C3 weighting and can change all five arms, including `DROP_C3` through its neutral C3 term. The five names can be retained only if the normalization is common, frozen, and explicitly added to every arm definition. It is a larger declarable decision-rule change, never a silent implementation detail.

3. **Replace the one-scalar interaction with structured coalition-aware selection** (for example, a two-stage additive shortlist followed by C3 reranking, or per-user/resource interaction allocations). This changes the C3 interface and the selector’s feasible/ranking semantics. FULL, DROP_C1, and DROP_C2 need the new informed-C3 rule; `DROP_C3` needs an explicitly specified neutral/absent counterpart; ALL_NEUTRAL_CONTROL needs the matching all-neutral rule. This is a new sealed five-arm design, not a patch compatible with the current arm definitions.

This preflight does **not** justify a scale fix as necessary: learned C3 already moves 7.5% of checkpoint-anchor decisions, and exact `psi` moves 20.8%. If a separately declared design objective requires closing that learned/exact activation gap, candidate 1 is the smallest honest change to price first because the exact scalar route shows that the existing decision form can move the argmax.

## Reproducibility and source boundary

Diagnostic receipt: `/home/sat/mcrl-v025-scale-ws/interaction-scale-receipt.json`; unsigned-payload digest recorded inside it: `c77e89b5824eda33b63626f495a2eff04b4a93758138e9d4029b20029897087d`; actual receipt-file SHA-256: `95b9bc48bc8d585661cbc9d5037a363e97638599569552248e34563d0dfe8296`.

Diagnostic source: `/home/sat/mcrl-v025-scale-ws/interaction_scale_diagnostic.py`; source SHA-256: `23b7c0b9ecb1f2e032bca20c0b4526e7437e94aca1e0031c52114773ee215eab`.

Command:

```bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=/home/sat/mcrl-v025-retrain-ws/src nice -n 17 /home/sat/mcrl-leo-handover/.venv/bin/python interaction_scale_diagnostic.py
```

Primary source locations: deployed score assembly and stable argmax `run_v025_pilot_c3.py:1503–1578`; exact decomposition `run_v025_pilot_c3.py:1328–1380`; coalition invariant `coalitions.py:246–286`; sealed arm/source map `learner.py:29–36`. The selector-latency panel and catalogue census are recorded in `SELECTOR-LATENCY-2026-09-10.md:19–27,56–77`.
