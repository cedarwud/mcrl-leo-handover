**Epoch 2000, exact targets + rebuilt corpus: FULL minus DROP_C3 = +15.555%; availability HELD (FULL 79.567021%, DROP_C3 77.842553%).**

# First repaired-feature C3 retraining measurement

**PILOT_NOT_CLAIM.** This is a minimal engineering pilot: one evaluation world, five anchors, nearest-eligible carrier, and two fixed learner seeds. It is not claim evidence.

The contracted exact-target result is positive in this minimal pilot and availability did not fall relative to DROP_C3; the scale is still too small for a general claim.

It is **not clean evidence for the intended size-2-to-3 mechanism**: at the exact/rebuilt epoch-2000 checkpoint, 6 of 10 FULL decisions select the all-user size-100 coalition, outside the rebuilt corpus's size-2-to-6 training support. At those 10 selected coalitions the head's Psi MAE is 50.077 normalized units and sign agreement is only 60%. The four in-support size-two choices have MAE 0.965, but four decisions are not enough to support a claim.

The inherited proxy-target result at epoch 2000 is negative (-4.893%) despite availability holding. The exact-target old-180 comparator is also negative (-19.310%) and has lower FULL availability than DROP_C3. The positive headline is therefore specific to exact targets plus the rebuilt corpus at this checkpoint.

## Energy efficiency and availability

Pooled EE is total realised bits divided by total realised joules across the 10 anchor-seed decisions. The relative contrast is `FULL / DROP_C3 - 1`.

S_UNI equals BASELINE in every row because all five inherited 5-second S_UNI calls missed their deadline after one iteration and executed the documented `DEADLINE_FALLBACK_BASE`; this run did not obtain a completed iterated unilateral optimum.

| Targets | C3 corpus | Epoch | Arm | Pooled EE (bit/J) | Availability | FULL−DROP_C3 | Availability held? |
|---|---|---:|---|---:|---:|---:|---|
| exact | rebuilt | 200 | FULL | 28122795.4 | 76.341489% | -2.421% | no |
| exact | rebuilt | 200 | DROP_C3 | 28820623.4 | 77.634043% | — | — |
| exact | rebuilt | 200 | BASELINE | 16987632 | 76.317021% | — | — |
| exact | rebuilt | 200 | S0 | 17949928.2 | 76.408511% | — | — |
| exact | rebuilt | 200 | S_UNI | 16987632 | 76.317021% | — | — |
| exact | rebuilt | 1000 | FULL | 27298387.2 | 79.211702% | -1.550% | yes |
| exact | rebuilt | 1000 | DROP_C3 | 27728033 | 78.247872% | — | — |
| exact | rebuilt | 1000 | BASELINE | 16987632 | 76.317021% | — | — |
| exact | rebuilt | 1000 | S0 | 17949928.2 | 76.408511% | — | — |
| exact | rebuilt | 1000 | S_UNI | 16987632 | 76.317021% | — | — |
| exact | rebuilt | 2000 | FULL | 28558803.9 | 79.567021% | +15.555% | yes |
| exact | rebuilt | 2000 | DROP_C3 | 24714514.9 | 77.842553% | — | — |
| exact | rebuilt | 2000 | BASELINE | 16987632 | 76.317021% | — | — |
| exact | rebuilt | 2000 | S0 | 17949928.2 | 76.408511% | — | — |
| exact | rebuilt | 2000 | S_UNI | 16987632 | 76.317021% | — | — |
| exact | old-180 | 200 | FULL | 23613486.3 | 78.361702% | -18.067% | yes |
| exact | old-180 | 200 | DROP_C3 | 28820623.4 | 77.634043% | — | — |
| exact | old-180 | 200 | BASELINE | 16987632 | 76.317021% | — | — |
| exact | old-180 | 200 | S0 | 17949928.2 | 76.408511% | — | — |
| exact | old-180 | 200 | S_UNI | 16987632 | 76.317021% | — | — |
| exact | old-180 | 1000 | FULL | 21500542.6 | 78.048936% | -22.557% | no |
| exact | old-180 | 1000 | DROP_C3 | 27763223.2 | 78.237234% | — | — |
| exact | old-180 | 1000 | BASELINE | 16987632 | 76.317021% | — | — |
| exact | old-180 | 1000 | S0 | 17949928.2 | 76.408511% | — | — |
| exact | old-180 | 1000 | S_UNI | 16987632 | 76.317021% | — | — |
| exact | old-180 | 2000 | FULL | 19943204.9 | 77.415957% | -19.310% | no |
| exact | old-180 | 2000 | DROP_C3 | 24715909.7 | 77.840426% | — | — |
| exact | old-180 | 2000 | BASELINE | 16987632 | 76.317021% | — | — |
| exact | old-180 | 2000 | S0 | 17949928.2 | 76.408511% | — | — |
| exact | old-180 | 2000 | S_UNI | 16987632 | 76.317021% | — | — |
| proxy | rebuilt | 200 | FULL | 36972218.4 | 77.843617% | +0.000% | yes |
| proxy | rebuilt | 200 | DROP_C3 | 36972218.4 | 77.843617% | — | — |
| proxy | rebuilt | 200 | BASELINE | 16987632 | 76.317021% | — | — |
| proxy | rebuilt | 200 | S0 | 17589687.7 | 77.070213% | — | — |
| proxy | rebuilt | 200 | S_UNI | 16987632 | 76.317021% | — | — |
| proxy | rebuilt | 1000 | FULL | 35158560.2 | 78.858511% | -2.529% | yes |
| proxy | rebuilt | 1000 | DROP_C3 | 36070897.4 | 76.832979% | — | — |
| proxy | rebuilt | 1000 | BASELINE | 16987632 | 76.317021% | — | — |
| proxy | rebuilt | 1000 | S0 | 17589687.7 | 77.070213% | — | — |
| proxy | rebuilt | 1000 | S_UNI | 16987632 | 76.317021% | — | — |
| proxy | rebuilt | 2000 | FULL | 34796706.6 | 77.573404% | -4.893% | yes |
| proxy | rebuilt | 2000 | DROP_C3 | 36586743.3 | 77.322340% | — | — |
| proxy | rebuilt | 2000 | BASELINE | 16987632 | 76.317021% | — | — |
| proxy | rebuilt | 2000 | S0 | 17589687.7 | 77.070213% | — | — |
| proxy | rebuilt | 2000 | S_UNI | 16987632 | 76.317021% | — | — |
| proxy | old-180 | 200 | FULL | 34733882.4 | 79.287234% | -6.054% | yes |
| proxy | old-180 | 200 | DROP_C3 | 36972218.4 | 77.843617% | — | — |
| proxy | old-180 | 200 | BASELINE | 16987632 | 76.317021% | — | — |
| proxy | old-180 | 200 | S0 | 17589687.7 | 77.070213% | — | — |
| proxy | old-180 | 200 | S_UNI | 16987632 | 76.317021% | — | — |
| proxy | old-180 | 1000 | FULL | 26723855.7 | 79.475532% | -25.913% | yes |
| proxy | old-180 | 1000 | DROP_C3 | 36070897.4 | 76.832979% | — | — |
| proxy | old-180 | 1000 | BASELINE | 16987632 | 76.317021% | — | — |
| proxy | old-180 | 1000 | S0 | 17589687.7 | 77.070213% | — | — |
| proxy | old-180 | 1000 | S_UNI | 16987632 | 76.317021% | — | — |
| proxy | old-180 | 2000 | FULL | 24013736.1 | 79.750000% | -35.049% | yes |
| proxy | old-180 | 2000 | DROP_C3 | 36972218.4 | 77.843617% | — | — |
| proxy | old-180 | 2000 | BASELINE | 16987632 | 76.317021% | — | — |
| proxy | old-180 | 2000 | S0 | 17589687.7 | 77.070213% | — | — |
| proxy | old-180 | 2000 | S_UNI | 16987632 | 76.317021% | — | — |

## Direct old-corpus versus rebuilt-corpus contrast

The old comparator is exactly the 180 `pair-catalogue` action selections, all size two, reconstructed as v2 rows and evaluated with the same repaired encoder and canonical exact C3 labels. This isolates corpus coverage; it does not reuse the legacy call-order-dependent labels.

| Targets | Epoch | Old-180 FULL−DROP_C3 | Rebuilt FULL−DROP_C3 | Old availability gap | Rebuilt availability gap |
|---|---:|---:|---:|---:|---:|
| exact | 200 | -18.067% | -2.421% | +0.728% | -1.293% |
| exact | 1000 | -22.557% | -1.550% | -0.188% | +0.964% |
| exact | 2000 | -19.310% | +15.555% | -0.424% | +1.724% |
| proxy | 200 | -6.054% | +0.000% | +1.444% | +0.000% |
| proxy | 1000 | -25.913% | -2.529% | +2.643% | +2.026% |
| proxy | 2000 | -35.049% | -4.893% | +1.906% | +0.251% |

## FULL selected coalition sizes

Counts are across five anchors × two learner seeds.

| Targets | C3 corpus | Epoch | Size distribution |
|---|---|---:|---|
| exact | rebuilt | 200 | size 1: 2; size 2: 2; size 100: 6 |
| exact | rebuilt | 1000 | size 1: 1; size 2: 4; size 3: 1; size 100: 4 |
| exact | rebuilt | 2000 | size 2: 4; size 100: 6 |
| exact | old-180 | 200 | size 1: 4; size 2: 3; size 100: 3 |
| exact | old-180 | 1000 | size 1: 4; size 2: 3; size 6: 1; size 100: 2 |
| exact | old-180 | 2000 | size 1: 3; size 6: 4; size 100: 3 |
| proxy | rebuilt | 200 | size 100: 10 |
| proxy | rebuilt | 1000 | size 4: 3; size 100: 7 |
| proxy | rebuilt | 2000 | size 3: 1; size 4: 1; size 100: 8 |
| proxy | old-180 | 200 | size 2: 2; size 5: 1; size 100: 7 |
| proxy | old-180 | 1000 | size 2: 1; size 3: 1; size 5: 2; size 6: 2; size 100: 4 |
| proxy | old-180 | 2000 | size 2: 2; size 3: 1; size 5: 1; size 6: 3; size 100: 3 |

## FULL interaction prediction versus exact Psi

All values are normalized by kappa and are computed at the coalitions actually selected by FULL. Exact Psi is recomputed from the anchor, exact singleton changes, and selected joint configuration; it is not copied from the training corpus.

| Targets | C3 corpus | Epoch | Predicted mean | Exact mean | MAE | RMSE | Sign agreement | Predicted range | Exact range |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| exact | rebuilt | 200 | 7.17746 | -9.49886 | 17.5215 | 26.9513 | 50.0% | [-4.78007, 32.0243] | [-30.7947, 3.24385] |
| exact | rebuilt | 1000 | -6.22184 | -1.55575 | 7.61751 | 14.3752 | 70.0% | [-34.9795, 9.36326] | [-10.3464, 3.24385] |
| exact | rebuilt | 2000 | 9.81311 | 21.8027 | 50.077 | 78.9306 | 60.0% | [-86.7454, 91.9555] | [-10.3464, 205.4] |
| exact | old-180 | 200 | -22.1549 | -1.7449 | 20.41 | 36.4416 | 60.0% | [-83.4455, 0] | [-10.3464, 3.24385] |
| exact | old-180 | 1000 | -28.914 | -0.476686 | 30.6114 | 66.047 | 70.0% | [-163.436, 5.39066] | [-10.3464, 3.24385] |
| exact | old-180 | 2000 | -30.0148 | 16.9022 | 52.0847 | 98.8942 | 60.0% | [-130.527, 7.93341] | [-30.7947, 205.4] |
| proxy | rebuilt | 200 | 13.1718 | 23.4125 | 32.3629 | 61.2291 | 60.0% | [-2.86908, 34.7724] | [-30.7947, 205.4] |
| proxy | rebuilt | 1000 | 4.38095 | 3.17273 | 29.0509 | 38.5064 | 50.0% | [-36.8243, 63.0797] | [-16.0272, 21.2627] |
| proxy | rebuilt | 2000 | 47.9459 | 19.5647 | 69.5157 | 102.603 | 50.0% | [-41.0411, 186.393] | [-16.0272, 205.4] |
| proxy | old-180 | 200 | -31.2672 | 0.563149 | 33.6487 | 42.2145 | 40.0% | [-55.5965, 5.27662] | [-16.0272, 17.9937] |
| proxy | old-180 | 1000 | -41.7135 | 2.35496 | 50.8651 | 78.2909 | 50.0% | [-145.511, 10.9197] | [-3.47842, 9.36924] |
| proxy | old-180 | 2000 | -24.7913 | 1.94001 | 38.2541 | 62.7928 | 20.0% | [-139.099, 13.0953] | [-4.55922, 9.36924] |

## Exact-target cost and scope

The full 180-anchor C1/C2 source rebuild was reduced to 5 matched training anchors for both exact and proxy modes. The exact path produced 4402 paired action targets (8804 scalar C1-or-C2 labels) in 591.494 wall seconds: 0.134369 s per paired C1/C2 action target, or 0.067185 s per scalar label. This timing includes exact feature/outcome construction and the three frozen forecast offsets.

The rebuilt C3 corpus contained 11924 rows in 180 shards. The repaired old comparator contained 180 rows with histogram {2: 180}.

Evaluation retained the requested world 3, five anchors, nearest-eligible carrier, two learner seeds, FULL, DROP_C3, BASELINE, S0, and the iterated unilateral optimum. It used the same 8-step tape prefix (five anchors plus three forecast steps). Exact and proxy modes were both run; no threshold, sign, seed, horizon, price, service guard, acceptance rule, or optimizer literal was changed.

Training used at most four worker processes and every launched Python process was run under `nice -n 10` with BLAS thread counts fixed to one.

## Artifacts and limitations

Raw receipts: `artifacts/v025-retrain-measurement-20260909-PILOT_NOT_CLAIM/evaluation/PILOT_NOT_CLAIM-raw-receipts.jsonl` (600 rows; SHA-256 `c04fee47e3ae02a65c956704f8fe9382df4b0c4a263308a67472f0c758cc357c`).
Run manifest: `artifacts/v025-retrain-measurement-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-manifest.json`.

This is a 10-decision-per-condition pilot, so it has no useful claim-level power or uncertainty estimate. The exact/proxy comparison also changes the feature values produced by the inherited fallback, not only its scalar labels, because that flag bypasses the evaluator path that supplies both contracted outcomes and their derived state fields.

**PILOT_NOT_CLAIM.**
