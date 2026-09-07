# V0.8 C2 Stage 1b oracle screen - result report

Generated from `stage1b-HA-20260902/result.json` and `stage1b-OPS3-20260902/result.json`.

Two pre-declared oracle routes evaluated on identical matched worlds, lineages and keyed fading field. Ratio-of-sums endpoints throughout. This report states measured quantities and the contract's own mechanical decision strings; it makes no claim beyond them.

## 0. Provenance

| item | value |
|---|---|
| runner file | `/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/d47a2ac0-70e1-49ca-b412-995b22bcb231/scratchpad/oracle/run_v08_c2_oracle_screen.py` |
| runner sha256 | `3cc504fd80047607e34cfd2a9c9c81a5167f4c3cff8f5ccc9b08688e66d91c92` |
| OPS-3 run runner sha256 | `3cc504fd80047607e34cfd2a9c9c81a5167f4c3cff8f5ccc9b08688e66d91c92` |
| H-A contract sha256 | `2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545` |
| OPS-3 addendum sha256 | `b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046` |
| evaluation split | TRAIN |
| TEST opened | False / False |
| episode training | False / False |
| learned Q2 used | False / False |
| lambda0 | 84994621.12635651 = `0x1.443a8f481639ap+26` |
| kappa | 10097071012.757404 = `0x1.2cea89d260f2ap+33` |
| worlds | [2026090221, 2026090222, 2026090223, 2026090224, 2026090225, 2026090226] |
| lineages | [2026092101, 2026092102, 2026092103] |
| episodes | H-A 132, OPS-3 72, total 204 |
| source-closure mode | receipt-only / receipt-only |

Checkpoint sha256 (H-A run):

| key | sha256 |
|---|---|
| `hybrid_2026092101` | `efc460a785194d189d085df794dc47292798b606871587beb36f073f91ea2171` |
| `hybrid_2026092101_path` | `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v04-c3-learnability-20260901-r2/hybrids/hybrid-2026092101-selected-rung-000100.pt` |
| `hybrid_2026092102` | `019e2160ed7c3802c142a92d4b391d63a0d2e3c0b7cfc0478ab6dbfd0b1178fc` |
| `hybrid_2026092102_path` | `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v04-c3-learnability-20260901-r2/hybrids/hybrid-2026092102-selected-rung-000100.pt` |
| `hybrid_2026092103` | `c0da537690a1ce1be1992ed62ea1972cf34cd6f86553bbe4e0065fd40d3fe377` |
| `hybrid_2026092103_path` | `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v04-c3-learnability-20260901-r2/hybrids/hybrid-2026092103-selected-rung-000100.pt` |
| `main` | `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b` |
| `v03_frozen_2026092101_head0` | `f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0` |
| `v03_frozen_2026092101_head1` | `f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0` |
| `v03_frozen_2026092102_head0` | `6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba` |
| `v03_frozen_2026092102_head1` | `6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba` |
| `v03_frozen_2026092103_head0` | `507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2` |
| `v03_frozen_2026092103_head1` | `507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2` |

Checkpoint sha256 (OPS-3 run):

| key | sha256 |
|---|---|
| `hybrid_2026092101` | `efc460a785194d189d085df794dc47292798b606871587beb36f073f91ea2171` |
| `hybrid_2026092101_path` | `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v04-c3-learnability-20260901-r2/hybrids/hybrid-2026092101-selected-rung-000100.pt` |
| `hybrid_2026092102` | `019e2160ed7c3802c142a92d4b391d63a0d2e3c0b7cfc0478ab6dbfd0b1178fc` |
| `hybrid_2026092102_path` | `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v04-c3-learnability-20260901-r2/hybrids/hybrid-2026092102-selected-rung-000100.pt` |
| `hybrid_2026092103` | `c0da537690a1ce1be1992ed62ea1972cf34cd6f86553bbe4e0065fd40d3fe377` |
| `hybrid_2026092103_path` | `/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v04-c3-learnability-20260901-r2/hybrids/hybrid-2026092103-selected-rung-000100.pt` |
| `main` | `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b` |
| `v03_frozen_2026092101_head0` | `f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0` |
| `v03_frozen_2026092101_head1` | `f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0` |
| `v03_frozen_2026092102_head0` | `6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba` |
| `v03_frozen_2026092102_head1` | `6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba` |
| `v03_frozen_2026092103_head0` | `507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2` |
| `v03_frozen_2026092103_head1` | `507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2` |

Source-closure note, verbatim:

```
source closure re-check FAILED and was not required: source authority is not ready; exact missing/invalid source artifact: prepared source authority failed: current source closure differs from sealed V0.4 manifest
```
```
source closure re-check FAILED and was not required: source authority is not ready; exact missing/invalid source artifact: prepared source authority failed: current source closure differs from sealed V0.4 manifest
```

## 1. World-identity check (H-A block vs OPS-3 block)

The keyed field root is `(component, evaluation_seed)` and mobility depends only on the seed, so the two blocks must draw byte-identical worlds.

| seed | initial_world_sha256 | identical across blocks |
|---|---|---|
| 2026090221 | `b6c02da4eb68105d...` | YES |
| 2026090222 | `ceaa68a8eeae6bf7...` | YES |
| 2026090223 | `e3f779472e1c6c33...` | YES |
| 2026090224 | `b37a767ed96d78cf...` | YES |
| 2026090225 | `d02d516f982f0928...` | YES |
| 2026090226 | `fa08a9548a8eb01e...` | YES |

All five fields ('initial_world_sha256', 'initial_state_sha256', 'initial_mask_sha256', 'fading_field_sha256', 'start_epoch') matched for every seed: **PASS**

## 2a. H-A arm table

Pooled over all rows of the arm.

| arm | episodes | EE bit/J | total bits | total energy J | served | hold | infeasible-hold |
|---|---|---|---|---|---|---|---|
| P1 | 18 | 1.17819e+08 | 2.29976e+14 | 1.95193e+06 | 0.9973 | 0.4288 | 48 |
| P2 | 18 | 1.18671e+08 | 2.29179e+14 | 1.9312e+06 | 0.9978 | 0.1468 | 39 |
| P3 | 18 | 7.10943e+07 | 1.14107e+14 | 1.60501e+06 | 0.9663 | 0.0651 | 606 |
| P12 | 18 | 1.19397e+08 | 2.31737e+14 | 1.9409e+06 | 0.9978 | 0.1748 | 39 |
| P13 | 18 | 1.06372e+08 | 2.57512e+14 | 2.42085e+06 | 0.9977 | 0.3612 | 41 |
| P23 | 18 | 1.18058e+08 | 2.36623e+14 | 2.00431e+06 | 0.9977 | 0.1491 | 42 |
| P123 | 18 | 1.18818e+08 | 2.38617e+14 | 2.00825e+06 | 0.9977 | 0.1816 | 42 |
| MAIN | 6 | 9.32669e+07 | 7.07922e+13 | 759028 | 0.9983 | 0.6245 | 10 |

Per lineage (MAIN has no lineage axis and repeats its world-pooled rows):

| arm | lineage | episodes | EE bit/J | served | hold | infeasible-hold |
|---|---|---|---|---|---|---|
| P1 | 2026092101 | 6 | 1.17543e+08 | 0.9973 | 0.3898 | 16 |
| P1 | 2026092102 | 6 | 1.17516e+08 | 0.9973 | 0.4567 | 16 |
| P1 | 2026092103 | 6 | 1.18402e+08 | 0.9973 | 0.4400 | 16 |
| P2 | 2026092101 | 6 | 1.18671e+08 | 0.9978 | 0.1468 | 13 |
| P2 | 2026092102 | 6 | 1.18671e+08 | 0.9978 | 0.1468 | 13 |
| P2 | 2026092103 | 6 | 1.18671e+08 | 0.9978 | 0.1468 | 13 |
| P3 | 2026092101 | 6 | 6.75078e+07 | 0.9513 | 0.0667 | 292 |
| P3 | 2026092102 | 6 | 7.09392e+07 | 0.9660 | 0.0505 | 204 |
| P3 | 2026092103 | 6 | 7.48358e+07 | 0.9817 | 0.0782 | 110 |
| P12 | 2026092101 | 6 | 1.19481e+08 | 0.9978 | 0.1673 | 13 |
| P12 | 2026092102 | 6 | 1.1938e+08 | 0.9978 | 0.1817 | 13 |
| P12 | 2026092103 | 6 | 1.19329e+08 | 0.9978 | 0.1753 | 13 |
| P13 | 2026092101 | 6 | 1.05459e+08 | 0.9978 | 0.2747 | 13 |
| P13 | 2026092102 | 6 | 1.07595e+08 | 0.9977 | 0.4223 | 14 |
| P13 | 2026092103 | 6 | 1.06021e+08 | 0.9977 | 0.3867 | 14 |
| P23 | 2026092101 | 6 | 1.18253e+08 | 0.9977 | 0.1537 | 14 |
| P23 | 2026092102 | 6 | 1.17959e+08 | 0.9977 | 0.1420 | 14 |
| P23 | 2026092103 | 6 | 1.1796e+08 | 0.9977 | 0.1517 | 14 |
| P123 | 2026092101 | 6 | 1.18634e+08 | 0.9977 | 0.1733 | 14 |
| P123 | 2026092102 | 6 | 1.19076e+08 | 0.9977 | 0.1875 | 14 |
| P123 | 2026092103 | 6 | 1.18745e+08 | 0.9977 | 0.1838 | 14 |
| MAIN | 2026092101 | 6 | 9.32669e+07 | 0.9983 | 0.6245 | 10 |
| MAIN | 2026092102 | 6 | 9.32669e+07 | 0.9983 | 0.6245 | 10 |
| MAIN | 2026092103 | 6 | 9.32669e+07 | 0.9983 | 0.6245 | 10 |

## 2b. OPS-3 arm table

Pooled over all rows of the arm.

| arm | episodes | EE bit/J | total bits | total energy J | served | hold | infeasible-hold |
|---|---|---|---|---|---|---|---|
| O2 | 18 | 1.13355e+08 | 2.18161e+14 | 1.92458e+06 | 0.9978 | 0.1395 | 39 |
| O12 | 18 | 1.19673e+08 | 2.33744e+14 | 1.95319e+06 | 0.9979 | 0.2517 | 38 |
| O23 | 18 | 1.09977e+08 | 2.18883e+14 | 1.99026e+06 | 0.9980 | 0.1228 | 36 |
| O123 | 18 | 1.16457e+08 | 2.47348e+14 | 2.12395e+06 | 0.9978 | 0.2523 | 40 |

Per lineage (MAIN has no lineage axis and repeats its world-pooled rows):

| arm | lineage | episodes | EE bit/J | served | hold | infeasible-hold |
|---|---|---|---|---|---|---|
| O2 | 2026092101 | 6 | 1.13355e+08 | 0.9978 | 0.1395 | 13 |
| O2 | 2026092102 | 6 | 1.13355e+08 | 0.9978 | 0.1395 | 13 |
| O2 | 2026092103 | 6 | 1.13355e+08 | 0.9978 | 0.1395 | 13 |
| O12 | 2026092101 | 6 | 1.1984e+08 | 0.9980 | 0.2230 | 12 |
| O12 | 2026092102 | 6 | 1.19188e+08 | 0.9978 | 0.2757 | 13 |
| O12 | 2026092103 | 6 | 1.19995e+08 | 0.9978 | 0.2563 | 13 |
| O23 | 2026092101 | 6 | 1.10114e+08 | 0.9980 | 0.1283 | 12 |
| O23 | 2026092102 | 6 | 1.09816e+08 | 0.9980 | 0.1193 | 12 |
| O23 | 2026092103 | 6 | 1.10002e+08 | 0.9980 | 0.1208 | 12 |
| O123 | 2026092101 | 6 | 1.15819e+08 | 0.9980 | 0.2168 | 12 |
| O123 | 2026092102 | 6 | 1.16717e+08 | 0.9977 | 0.2812 | 14 |
| O123 | 2026092103 | 6 | 1.1683e+08 | 0.9977 | 0.2588 | 14 |

## 3. Primary directions (percentage contrasts, EE_X/EE_Y - 1)

### H-A

| direction | contrast | pooled | 2026092101 | 2026092102 | 2026092103 | positive lineages | passes |
|---|---|---|---|---|---|---|---|
| D-C2 | P123 vs P13 | +11.7000 | +12.4921 | +10.6704 | +12.0015 | 3/3 | YES |
| D-C3 | P123 vs P12 | -0.4848 | -0.7095 | -0.2548 | -0.4886 | 0/3 | NO |
| D-C1 | P123 vs P23 | +0.6441 | +0.3222 | +0.9469 | +0.6657 | 3/3 | YES |

(values are percent)

### OPS-3

| direction | contrast | pooled | 2026092101 | 2026092102 | 2026092103 | positive lineages | passes |
|---|---|---|---|---|---|---|---|
| D-C2 | O123 vs P13 | +9.4800 | +9.8231 | +8.4782 | +10.1950 | 3/3 | YES |
| D-C3 | O123 vs O12 | -2.6873 | -3.3558 | -2.0728 | -2.6375 | 0/3 | NO |
| D-C1 | O123 vs O23 | +5.8916 | +5.1806 | +6.2841 | +6.2076 | 3/3 | YES |

(values are percent)

## 4. Service guard S

S as stated: pooled served fraction of the top arm is not below that of each comparator, AND at least two of three lineage served-fraction contrasts are nonnegative for each pair.

### H-A (top arm P123)

| pair | pooled delta served | pooled not below | nonneg lineages | passes |
|---|---|---|---|---|
| P123 vs P13 | -0.000056 | NO | 2/3 | FAIL |
| P123 vs P12 | -0.000167 | NO | 0/3 | FAIL |
| P123 vs P23 | +0.000000 | YES | 3/3 | PASS |

S overall: **FAIL**

### OPS-3 (top arm O123)

| pair | pooled delta served | pooled not below | nonneg lineages | passes |
|---|---|---|---|---|
| O123 vs P13 | +0.000056 | YES | 3/3 | PASS |
| O123 vs O12 | -0.000111 | NO | 1/3 | FAIL |
| O123 vs O23 | -0.000222 | NO | 1/3 | FAIL |

S overall: **FAIL**

## 5. Mechanical decision (contract section 4, applied literally)

### H-A

- D-C2 pooled positive: True; positive lineages 3/3
- D-C3 pooled positive: False; positive lineages 0/3; passes: False
- D-C1 pooled positive: True; positive lineages 3/3; passes: True
- S passes: False

**Decision string: `C3_CONTEXT_FAIL`**  (D-C2 passes; D-C3 fails)

### OPS-3

- D-C2 pooled positive: True; positive lineages 3/3
- D-C3 pooled positive: False; positive lineages 0/3; passes: False
- D-C1 pooled positive: True; positive lineages 3/3; passes: True
- S passes: False

**Decision string: `C3_CONTEXT_FAIL`**  (D-C2 passes; D-C3 fails)

Notes on the rule application, stated so nothing is read into it:

- The section 4 branches are evaluated in the order the contract writes them: the D-C2 branches first, then `PASS_STAGE1B`, then the `C3_CONTEXT_FAIL` / `C1_CONTEXT_FAIL` branch. Under that ordering `C3_CONTEXT_FAIL` fires on the D-C3 result alone; the state of the service guard S does not change the string. S is measured and reported above regardless, and it FAILS for both routes.
- `D-C3 fails` is read as the negation of the contract's own pass condition, i.e. NOT (strictly positive pooled AND positive in 3/3 lineages).
- Both routes produced the same decision string. Addendum A's "exactly one route passes" and "both pass" clauses therefore do not apply; its "if neither passes" clause is the one whose precondition is met.

## 6. Diagnostics (reported, never decisional)

### 6.1 All lattice contrasts, pooled

| left | right | EE contrast % | served delta |
|---|---|---|---|
| P1 | P2 | -0.7179 | -0.000500 |
| P1 | P3 | +65.7227 | +0.031000 |
| P1 | P12 | -1.3212 | -0.000500 |
| P1 | P13 | +10.7612 | -0.000389 |
| P1 | P23 | -0.2017 | -0.000333 |
| P1 | P123 | -0.8404 | -0.000333 |
| P1 | O2 | +3.9383 | -0.000500 |
| P1 | O12 | -1.5485 | -0.000556 |
| P1 | O23 | +7.1309 | -0.000667 |
| P1 | O123 | +1.1703 | -0.000444 |
| P1 | MAIN | +26.3250 | -0.001000 |
| P2 | P3 | +66.9210 | +0.031500 |
| P2 | P12 | -0.6077 | +0.000000 |
| P2 | P13 | +11.5621 | +0.000111 |
| P2 | P23 | +0.5199 | +0.000167 |
| P2 | P123 | -0.1234 | +0.000167 |
| P2 | O2 | +4.6899 | +0.000000 |
| P2 | O12 | -0.8366 | -0.000056 |
| P2 | O23 | +7.9055 | -0.000167 |
| P2 | O123 | +1.9018 | +0.000056 |
| P2 | MAIN | +27.2384 | -0.000500 |
| P3 | P12 | -40.4555 | -0.031500 |
| P3 | P13 | -33.1647 | -0.031389 |
| P3 | P23 | -39.7799 | -0.031333 |
| P3 | P123 | -40.1654 | -0.031333 |
| P3 | O2 | -37.2818 | -0.031500 |
| P3 | O12 | -40.5926 | -0.031556 |
| P3 | O23 | -35.3554 | -0.031667 |
| P3 | O123 | -38.9521 | -0.031444 |
| P3 | MAIN | -23.7733 | -0.032000 |
| P12 | P13 | +12.2442 | +0.000111 |
| P12 | P23 | +1.1345 | +0.000167 |
| P12 | P123 | +0.4872 | +0.000167 |
| P12 | O2 | +5.3299 | +0.000000 |
| P12 | O12 | -0.2304 | -0.000056 |
| P12 | O23 | +8.5652 | -0.000167 |
| P12 | O123 | +2.5248 | +0.000056 |
| P12 | MAIN | +28.0163 | -0.000500 |
| P13 | P23 | -9.8978 | +0.000056 |
| P13 | P123 | -10.4744 | +0.000056 |
| P13 | O2 | -6.1600 | -0.000111 |
| P13 | O12 | -11.1137 | -0.000167 |
| P13 | O23 | -3.2776 | -0.000278 |
| P13 | O123 | -8.6591 | -0.000056 |
| P13 | MAIN | +14.0517 | -0.000611 |
| P23 | P123 | -0.6400 | +0.000000 |
| P23 | O2 | +4.1484 | -0.000167 |
| P23 | O12 | -1.3495 | -0.000222 |
| P23 | O23 | +7.3474 | -0.000333 |
| P23 | O123 | +1.3747 | -0.000111 |
| P23 | MAIN | +26.5803 | -0.000667 |
| P123 | O2 | +4.8193 | -0.000167 |
| P123 | O12 | -0.7141 | -0.000222 |
| P123 | O23 | +8.0388 | -0.000333 |
| P123 | O123 | +2.0277 | -0.000111 |
| P123 | MAIN | +27.3956 | -0.000667 |
| O2 | O12 | -5.2789 | -0.000056 |
| O2 | O23 | +3.0715 | -0.000167 |
| O2 | O123 | -2.6632 | +0.000056 |
| O2 | MAIN | +21.5384 | -0.000500 |
| O12 | O23 | +8.8159 | -0.000111 |
| O12 | O123 | +2.7615 | +0.000111 |
| O12 | MAIN | +28.3119 | -0.000444 |
| O23 | O123 | -5.5638 | +0.000222 |
| O23 | MAIN | +17.9165 | -0.000333 |
| O123 | MAIN | +24.8637 | -0.000556 |

### 6.2 Per-world paired contrasts and sign counts

- H-A D-C2 (P123 vs P13): 2026090221:+10.995%, 2026090222:+15.708%, 2026090223:+14.699%, 2026090224:+9.719%, 2026090225:+8.517%, 2026090226:+11.346%  -> positive in 6/6 worlds
- H-A D-C3 (P123 vs P12): 2026090221:-0.631%, 2026090222:+0.249%, 2026090223:-0.771%, 2026090224:-1.900%, 2026090225:-0.614%, 2026090226:+0.806%  -> positive in 2/6 worlds
- H-A D-C1 (P123 vs P23): 2026090221:+0.685%, 2026090222:+1.345%, 2026090223:+0.398%, 2026090224:-0.167%, 2026090225:-0.065%, 2026090226:+1.770%  -> positive in 4/6 worlds
- OPS-3 D-C2 (O123 vs P13): 2026090221:+11.321%, 2026090222:+10.117%, 2026090223:+11.644%, 2026090224:+8.385%, 2026090225:+7.576%, 2026090226:+8.299%  -> positive in 6/6 worlds
- OPS-3 D-C3 (O123 vs O12): 2026090221:-1.140%, 2026090222:-5.112%, 2026090223:-2.923%, 2026090224:-2.745%, 2026090225:-3.054%, 2026090226:-1.225%  -> positive in 0/6 worlds
- OPS-3 D-C1 (O123 vs O23): 2026090221:+7.401%, 2026090222:+2.592%, 2026090223:+5.666%, 2026090224:+6.328%, 2026090225:+4.316%, 2026090226:+8.985%  -> positive in 6/6 worlds

### 6.3 Paired-world bootstrap of the primary contrasts

2000 replicates, `numpy.default_rng(2026090299)`, resampling worlds with replacement, statistic = percentage contrast of the pooled ratio of sums. Report only.

| contrast | mean % | 2.5% | 97.5% | P(>0) |
|---|---|---|---|---|
| H-A D-C2 P123 vs P13 | +11.7104 | +9.8544 | +13.8056 | 1.000 |
| H-A D-C3 P123 vs P12 | -0.4883 | -1.1660 | +0.2260 | 0.080 |
| H-A D-C1 P123 vs P23 | +0.6442 | +0.0846 | +1.2603 | 0.991 |
| OPS-3 D-C2 O123 vs P13 | +9.4942 | +8.3263 | +10.8011 | 1.000 |
| OPS-3 D-C3 O123 vs O12 | -2.6830 | -3.7118 | -1.7313 | 0.000 |
| OPS-3 D-C1 O123 vs O23 | +5.8983 | +4.2542 | +7.4930 | 1.000 |

### 6.4 OPS-3 internal self-check and reference row

- Q2*_OPS3 == Q2*_HA / 3 where H_t = 3 and every chi = 1: max relative error 2.610e-16 over 1319624 legal actions, tolerance 1e-12, passed = True
- `Z_a - Z_(a^M)` diagnostic over 72 episodes: median of per-episode medians -4.77017e+09 bits, mean |delta| 7.37972e+09 bits. Not subtracted in the deployed surface (per-state constant).
- H_t by decision step: [3, 3, 3, 3, 3, 3, 3, 2, 1, 0]

### 6.5 Timings

| block | episodes | wall s | mean s/episode |
|---|---|---|---|
| H-A | 132 | 1149.4 | 8.27 |
| OPS-3 | 72 | 969.5 | 12.65 |

## 7. Contract files

| file | sha256 |
|---|---|
| `V08-C2-STAGE1B-ADDENDUM-OPS3-VARIANT-2026-09-02.md` | `b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046` |
| `V08-C2-STAGE1B-ORACLE-SCREEN-CONTRACT-2026-09-02.md` | `2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545` |

