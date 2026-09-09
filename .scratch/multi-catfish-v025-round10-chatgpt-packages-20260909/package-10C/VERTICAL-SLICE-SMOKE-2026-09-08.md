# V0.25 primary-cell vertical slice — SMOKE — 2026-09-08

Label: `SMOKE_NOT_MATRIX`. Scope: TRAIN-only development data; `a-r0`; `V025_PROBE/world/1`; nearest-eligible carrier; first 10 decision steps. This is not a matrix result.

## Provisional five-step calibration

| quantity | value |
|---|---:|
| bits_ref | 5.357829656e+11 |
| joules_ref | 3.247192490e+04 |
| eta_ref = lambda (bit/J) | 1.649988312e+07 |
| kappa (bits/user-step) | 1.071565931e+09 |

## Per-anchor numbers

| anchor | rows | U1 gain (kappa) | J1-U_all (kappa) | S0 score gain (kappa) | g_A FULL (kappa) | g_I FULL (kappa) | FULL EE | S_UNI EE | sec/row | sec/anchor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 3106 | 11.195 | 58.3107 | 309.995 | 278.311 | -208.805 | 2.48914e+07 | 2.48914e+07 | 0.00138729 | 19.8116 |
| 1 | 3108 | 12.1764 | 22.5724 | 102.313 | 158.764 | -126.221 | 2.12083e+07 | 2.17262e+07 | 0.00144595 | 19.7725 |
| 2 | 3108 | 7.18707 | 11.2811 | 25.536 | 50.9359 | -34.2082 | 2.49163e+07 | 2.70341e+07 | 0.00155357 | 19.0449 |
| 3 | 3108 | 8.88127 | 16.0472 | 5.88127 | 10.9281 | 2.26727 | 1.46481e+07 | 1.88532e+07 | 0.00267847 | 18.5236 |
| 4 | 3107 | 13.1427 | 77.4748 | 436.214 | 446.506 | -360.501 | 3.11882e+07 | 3.295e+07 | 0.00141059 | 23.6811 |
| 5 | 3108 | 14.4172 | 76.2933 | 139.233 | 295.752 | -229.73 | 2.21257e+07 | 3.42832e+07 | 0.00137821 | 18.2274 |
| 6 | 3108 | 11.6078 | 27.9737 | 56.9238 | 131.011 | -97.3552 | 2.45009e+07 | 2.50638e+07 | 0.00143689 | 17.5637 |
| 7 | 3108 | 9.80241 | 7.35619 | 6.80241 | 6.72609 | 7.19588 | 1.20989e+07 | 1.23974e+07 | 0.00214364 | 16.1805 |
| 8 | 3107 | 12.5239 | 47.7216 | 341.794 | 429.596 | -372.048 | 3.08564e+07 | 3.56644e+07 | 0.00136031 | 17.5517 |
| 9 | 3107 | 8.0315 | 126.671 | 524.373 | 201.508 | -68.6564 | 5.10977e+07 | 4.78506e+07 | 0.00130372 | 16.1542 |

`U_all` in this receipt is the maximum over BASE plus every declared unilateral row, so its value is the U1 ceiling; both names are retained because the request names `J1 - U_all` while the sealed decisions name `J1 - U1`.

## Pooled realised endpoint

| arm | pooled EE (bit/J) | availability | mean lit beams | plateau share | cap-hit share |
|---|---:|---:|---:|---:|---:|
| U1 | 12646730.6 | 0.597287 | 42.7 | 9.96562e-06 | 0.38448 |
| J1 | 25582319.5 | 0.758883 | 46.8 | 0.000433123 | 0.111738 |
| UNION_CEILING | 25582319.5 | 0.758883 | 46.8 | 0.000433123 | 0.111738 |
| S0 | 23111576.1 | 0.740266 | 46.1 | 0.000352907 | 0.146407 |
| FULL | 23208824.2 | 0.744138 | 46.1 | 0.000352907 | 0.145597 |
| DROP_C1 | 16122736.7 | 0.664436 | 42.8 | 0.000167954 | 0.295413 |
| DROP_C2 | 25582319.5 | 0.758883 | 46.8 | 0.000433123 | 0.111738 |
| DROP_C3 | 25571252.5 | 0.744117 | 52.1 | 0.000349797 | 0.0767485 |
| UNI | 12680600.9 | 0.60117 | 42.8 | 9.94233e-06 | 0.37925 |
| S_UNI | 25582319.5 | 0.758883 | 46.8 | 0.000433123 | 0.111738 |
| NULL | 11989252.9 | 0.587074 | 43 | 9.89609e-06 | 0.402768 |
| RANDOM_FEASIBLE | 13313803.8 | 0.614053 | 43.8 | 0.000204022 | 0.353754 |
| NOMINAL_GREEDY | 25801922.4 | 0.739862 | 51.9777 | 0.000366972 | 0.0773763 |

### Factor arms and marginals

| quantity | value |
|---|---:|
| FULL realised pooled EE (bit/J) | 23208824.2 |
| DROP_C1 realised pooled EE (bit/J) | 16122736.7 |
| DROP_C2 realised pooled EE (bit/J) | 25582319.5 |
| DROP_C3 realised pooled EE (bit/J) | 25571252.5 |
| FULL / DROP_C1 - 1 | 0.439508969 |
| FULL / DROP_C2 - 1 | -0.092778738 |
| FULL / DROP_C3 - 1 | -0.0923861005 |
| S0 / NULL - 1 | 0.927691092 |
| S_UNI / FULL - 1 | 0.102266935 |
| FULL / S_UNI - 1 | -0.092778738 |
| sum g_A for FULL (kappa) | 2010.03854 |
| sum g_I for FULL (kappa) | -1488.06278 |
| sum U1 gain (kappa) | 108.965275 |
| sum J1-U_all headroom (kappa) | 471.702032 |
| sum S0 score gain (kappa) | 1949.06537 |

### FULL ACM mode distribution (airtime-seconds)

| ACM mode | airtime-seconds |
|---|---:|
| 16APSK 2/3 | 81.5845541 |
| 16APSK 3/4 | 37.9595152 |
| 16APSK 4/5 | 17.9254026 |
| 16APSK 5/6 | 22.3731255 |
| 32APSK 3/4 | 10.1548052 |
| 32APSK 4/5 | 5.18898701 |
| 32APSK 5/6 | 8.01364502 |
| 32APSK 8/9 | 1.74157576 |
| 32APSK 9/10 | 4.89371429 |
| 8PSK 2/3 | 233.014338 |
| 8PSK 3/4 | 111.955602 |
| 8PSK 3/5 | 245.505489 |
| NO_MODE | 4832.32118 |
| QPSK 1/2 | 1247.63546 |
| QPSK 1/3 | 1522.39591 |
| QPSK 1/4 | 1807.66611 |
| QPSK 2/3 | 558.73787 |
| QPSK 2/5 | 1732.26594 |
| QPSK 3/4 | 291.78826 |
| QPSK 3/5 | 770.534996 |
| QPSK 4/5 | 175.187394 |
| QPSK 5/6 | 99.7512727 |
| QPSK 9/10 | 48.2848485 |

## Timing

Calibration provider seconds: 52.2307.
Probe provider seconds: 100.138.
Probe anchor seconds: 186.511 total; 18.6511 mean.
Selection-snapshot catalogue seconds/row: 0.00160986 mean.
Selected-arm full-boundary seconds/row: 0.134223 mean.

## Shortcuts and unimplemented decision items

- Provisional calibration uses only `V025_CAL/world/1` for five steps and BASE-plus-all-unilateral nominal-greedy candidates ranked at the nominal decision-instant snapshot; the selected row is then scored with the full realised 48-boundary step. It does not implement the formal two-world, all-31-setting immutable calibration registry.
- `kappa` uses the requested unit contract `bits_ref / (users * decision steps)` (bits per user-step), not the stage-3 field name/formula that divided by seconds.
- The S0 proposal cap is instantiated as deterministic cumulative profiles from each user's top-two unilateral options (at most 200), plus all per-base-beam evacuations. No learned S3 proposer is present.
- C2 is the sum of per-move three-offset nominal continuations. Each offset uses its decision-instant physical state held for one 30.08-s user-step rather than 48-boundary within-offset integration. The focal action is absorbing on loss/invalidity and receives `-kappa` for that and later offsets; no learned Q2 head or encoded Q2 row is built.
- Catalogue selection, factor decomposition, U1/J1/union ceilings, S0, random-feasible, and nominal-greedy use the nominal decision-instant state held for 30.08 seconds. Full configuration-by-boundary selection was stopped after measured anchor costs of 83.945, 123.523, and 380.604 seconds. Every selected arm is still rescored with the full 48-boundary realised evaluator; exact full-boundary catalogue selection is not implemented.
- Pair coalitions report exact `Psi/2` credit. Larger catalogued sets use the exact total set residual for selection but do not compute per-user Shapley credits.
- Iterated-exact S_UNI is not implemented in the outcome run: measured attempts could not fit the compute cap. The `S_UNI` result column is an explicitly marked proxy equal to the exact-`F` union ceiling over the bounded catalogue; it is not a unilateral-local-optimum certificate.
- Anchors are matched, open-loop nearest-eligible comparisons; arm-specific closed-loop event-ledger trajectories are not implemented. Treatment H/SH/T/S/U, interruption blackout, per-boundary rate-target-attainment receipts, re-key events and handover-energy sensitivities are not implemented.
- The selector's deployable service guard is nominal served-count non-decrease. The formal QoS bootstrap margins, deadline cancellation/fallback timing, capability manifest, attempt registry, write-once permissions, merge re-aggregation, claim-panel allocation, synthetic T1-T3 suite, source generation, learners, and training are not implemented.
- The provider's matching compact/per-chain `tapes.py` seam was integrated because the fixed provider cannot import against the stage-3 copy. No file under `src/mcrl/env/` was edited.
- Fixed-point validity is certified by the capped-map residual. The stage-3 scalar target-clearance comparison that returned INVALID after a converged residual is not used.
- Only `a-r0`, the two named development worlds, and the requested 5 calibration plus 10 probe anchors (with three forecast offsets) were opened.

## Verification and receipt digests

Targeted tests: 23 passed: test_provider_legacy.py + test_smoke_slice.py.
No-env diff receipt: 0 edited files.
Successful-run compute: 371.312 CPU seconds. Prior-attempt accounting upper bound: 2768.91 CPU seconds. Post-run verification accounting upper bound: 95 CPU seconds. Accounted total upper bound: 3235.22 CPU seconds (53.9204 core-minutes).

No thresholds are applied in this report.
