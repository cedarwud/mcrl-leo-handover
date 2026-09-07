# Q1/C1 lambda repricing source audit

Status: **PASS (offline source reconstruction only)**  
Claim ceiling: **no learner result, no episode result, and no EE efficacy claim**

## Scope

This audit reads only the seven explicitly named opening source files in the V0.3 E1 action-shared supplement. It uses rows whose top-level `admitted_route` is exactly `C1`; the C3 rows in the same files and all audit-only C1 route metadata on C3 rows are excluded. No simulator, TEST source, learner, or training process was invoked.

The source split is 2026092001--2026092004 = TRAIN and 2026092005--2026092007 = internal validation. The latter is an internal source split, not a TEST outcome.

## Formula and frozen constants

For every admitted C1 row, the reconstructed target is \(\zeta_1=\Delta t[(R_u^C-R_u^M)-\lambda(P_C^N-P_M^N)]\). The raw focal rates, full network powers, interval, action vectors, mask, and state are not changed.

- Old payload multiplier: `0x1.443a8f481639ap+26` = 84994621.12635651 bit/J.
- Fixed repricing multiplier: `0x1.c3c0a7b6b86d3p+26` = 118424222.8550065 bit/J.
- Multiplier increase: 33429601.72864999 bit/J.
- The new multiplier was fixed before this offline output was inspected; no sign, threshold, or source row was tuned after repricing.

## Source authentication and row counts

- Frozen source-manifest SHA-256: `9ec832c71b29ad84e37856db1f5d237f07d177c62cc93fbb66de06d808184a0a`.
- Authenticated source files: 7.
- Total rows read: 3542.
- Admitted C1 rows used: **1680** (968 TRAIN + 712 internal validation).
- Non-C1 rows excluded: 1862 (including 1862 admitted C3 rows).

| Seed | Split | Total rows | Admitted C1 | Excluded C3 | File SHA-256 |
|---:|:---|---:|---:|---:|:---|
| 2026092001 | train | 512 | 242 | 270 | `8c34b97c661b79569f1b5f4aca54187da0554f41baf06036bb95950e84dc0fd1` |
| 2026092002 | train | 491 | 235 | 256 | `35a1d7a3fc07fd3b28e6ae414b8a22ff5635d99656728ff43fe8bd74c860fed0` |
| 2026092003 | train | 526 | 256 | 270 | `fb4cc3d090b0f0db8daa355627021056423648f5275556e4126ad7f143282378` |
| 2026092004 | train | 491 | 235 | 256 | `265553bf8c917074b12abdaef1df50637ddf904a0a01e87ceb4d87237e9f8680` |
| 2026092005 | validation | 512 | 242 | 270 | `d17105376629205d8a75863e8ad5d568e4b68f8448241db33d1d8c3ad80d9933` |
| 2026092006 | validation | 512 | 242 | 270 | `2955d9de3ff889c888ea76ba571261ac94ba97609d26a101f10a151f58e7dd00` |
| 2026092007 | validation | 498 | 228 | 270 | `80dca48e337f6e816fa45bfd0f47f4cce512b4f9534d87273db4487a03aec5ed` |

## Old-target reconstruction

All 1680 persisted payload targets were recomputed from raw focal rates, raw candidate/reference system power, the raw interval, and the payload old multiplier. The maximum absolute error is `0x1.0000000000000p-18` bit; the frozen acceptance tolerance is `0.001` bit. **The reconstruction passes.**

Absolute-error summary: n=1680; +=705 (41.964%); -=0 (0.000%); 0=975; mean=5.82761380688e-07; median=0; min=0; max=3.81469726562e-06.

## Repriced target statistics

Old persisted C1 target: n=1680; +=595 (35.417%); -=1085 (64.583%); 0=0; mean=-3017951507.5; median=-2254209451.51; min=-29277694641.7; max=28891570367.9.

New C1 target at the fixed multiplier: n=1680; +=597 (35.536%); -=1083 (64.464%); 0=0; mean=-3941253206.74; median=-2696497759.34; min=-33139621794.5; max=35192324392.1.

New minus old target: n=1680; +=471 (28.036%); -=1031 (61.369%); 0=178; mean=-923301699.248; median=-140239673.746; min=-6501866508.21; max=6830162685.03.

Values above are target-label diagnostics in bits. They are not policy rollouts and do not establish that C1 improves canonical EE.

## Sign changes

Across all admitted C1 rows, 76 / 1680 (4.524%) changed sign when moving from the persisted old target to the fixed repriced target:

- old positive → new negative: 37
- old negative → new positive: 39
- old zero → new nonzero: 0
- old nonzero → new zero: 0

## Split and seed summaries

The standard deviation is population standard deviation; p05/p95 use nearest-rank quantiles. `+` and `-` count strict target signs.

| Group | n | Old + / - | New + / - | Sign flips | Old mean (bit) | New mean (bit) |
|:---|---:|---:|---:|---:|---:|---:|
| train | 968 | 302 / 666 | 292 / 676 | 26 | -3638768327.73 | -5084947642.71 |
| validation | 712 | 293 / 419 | 305 / 407 | 50 | -2173919650.77 | -2386342793.8 |
| 2026092001 | 242 | 81 / 161 | 78 / 164 | 5 | -2753948496.89 | -4305063023.38 |
| 2026092002 | 235 | 67 / 168 | 68 / 167 | 1 | -5321662337.69 | -6112065444.05 |
| 2026092003 | 256 | 66 / 190 | 60 / 196 | 6 | -4739109828.73 | -6926823438.91 |
| 2026092004 | 235 | 88 / 147 | 86 / 149 | 14 | -1668380593.56 | -2854476113.95 |
| 2026092005 | 242 | 123 / 119 | 125 / 117 | 22 | 253704843.051 | 526780286.786 |
| 2026092006 | 242 | 100 / 142 | 107 / 135 | 11 | -1637674012.98 | -1045885929.23 |
| 2026092007 | 228 | 70 / 158 | 73 / 155 | 17 | -5319781807.99 | -6901107472.42 |

## Interpretation and next gate

Verified fact: the existing C1 source rows can be deterministically re-labeled at the fixed new multiplier, and the persisted old labels reconstruct within tolerance.

Inference: changing the multiplier changes Q1's labels and therefore requires a matched Q1 retraining before using Q1 to rebuild Q1+Q2 references. This audit does not decide whether that retrained head improves EE.

Proposal: pair this C1 repricing with the separately specified Q2 offline repricing, then retrain Q1 and Q2 together under one frozen execution receipt. Do not reprice only Q1 and do not use these source-label signs as an efficacy endpoint.

Tool script SHA-256: `a0acfe53b59b91281dbdd3d9ec813f35f3ea5461c835274edb54869489cd54fe`.
The complete per-row evidence is in `receipt.json`; the runnable implementation is `reprice_c1.py` and its tests are in `test_reprice_c1.py`.

