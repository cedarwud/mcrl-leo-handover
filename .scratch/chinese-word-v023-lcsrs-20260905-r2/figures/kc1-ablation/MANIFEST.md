# k_c=1 Five-Arm Component-Ablation Figure Set — MANIFEST (2026-07-07)

CDRL-style line sweeps (metric on y, env parameter on x, one line per arm, **NO confidence-interval band**,
marker+line). Regenerate: `analysis/family-b-collapse-diagnosis/sweep_kc1_ablation.py <axis>` then
`scratch/final_figures/kc1_ablation/finalize_kc1.py`.

## The 5 arms (label → weights → decode)
| label | weights | decode | meaning |
|---|---|---|---|
| **MCCRL** | `A2_hybrid_k1_w503020_C1FIXED` (seed 42/137/271) | strict-k_c corrected, **k_c=1** | catfish + semi-coord + learning |
| **MCCRL w/o catfish** | `A1_hybrid_k1_w503020_C1FIXED` | strict-k_c corrected, k_c=1 | semi-coord + learning, no catfish |
| **MCCRL w/o coordinate** | `A2_hybrid_k1_w503020_C1FIXED` (SAME as MCCRL) | strict-k_c corrected, **k_c=0 = argmax** | remove coordination → collapse |
| **MCCRL w/o learning** | fixed-rule auction (AF) | strict-k_c corrected, k_c=1 | coordination, no learning |
| **MODQN** | B0 anchor `family-b-baseline-retrain-2026-06-14` | plain (base) argmax | plain MODQN (the baseline anchor) |

## Provenance — BOTH known EE traps closed (this set is CLEAN; setA/setB EE were buggy)
- **EE = angle-aware `family_b_eta_r1`, post ÷G_T fix** (eval-side commit `211a71a`). G1 fence
  `modqn.py = 10600c20…` asserted **pre==post** each run → NOT the ~1e4× inflated pre-fix EE (fence `aa877676`).
- **Decode = `decode_hybrid_corrected` (strict-k_c, codex-F5 fix)** for every hybrid arm AND AF → NOT the
  `decode_hybrid_auction` opened-set inflation. `k_c=0` resolves to `decode_a0_argmax` (the collapse ablation).
- EE display units = `family_b_eta_r1 / 1e6` (Baseline MODQN @ U=100 ≈ 100). Decode weight held constant `[0.5,0.3,0.2]`.
- Eval-only, **nominal-transfer** (weights trained @ U=100/k_cap=3/p_base=0.25, evaluated at each x-point; disclosed).
  Seed-level n=3 (learned arms); AF seed-invariant. RAW+CI kept in the CSV/JSON; the PNG is plain lines (USER standard).
- Groups: **Group A (4 arms, no AF) → `ablation/`** ; **Group B (5 arms, +AF) → `vs-nolearning/`**.

## Honest RED LINES (bind every caption / any downstream use)
1. **MCCRL ≈ MCCRL w/o catfish** → catfish is SUBSUMED by the coordinated decode (NOT the win driver).
2. On **EE, MCCRL tracks AF; AF is the matched-coverage EE ceiling** — no learned arm beats AF on EE (G6-SOUND).
3. **w/o coordinate + baseline COLLAPSE** (argmax → low EE, min_cov = 0) → **coordination is the de-collapse engine**.
4. **Deployable win = handover**: AF churns beams hard (ho_rate ~0.3–0.5); learned arms ~0.09 at the SAME coverage
   → 3–5× fewer handovers. Read handover WITH min_cov (Baseline's low handover = collapse, not stability).
   > ⚠ **RESET-ARTIFACT DISCLOSURE (2026-07-09, `grounded`).** `env.reset` sets `_assignments_slot = zeros`
   > (`family_b_step.py:347`) and `_handover_penalty` has **no first-step guard** (`:803`), so **step 1 charges
   > a handover against an artificial all-zero start** — i.e. *initial acquisition is counted as a handover*.
   > The inflation is **NOT symmetric across policies** (step-1 share of an episode's handovers: AF 24.7 % ·
   > argmax 13.5 % · RSS_max 71.8 % · round_robin 100 % · myopic-`J_w` 99.3 %), so **absolute `ho_rate` is
   > inflated and any AF-vs-learned RATIO shifts once step 1 is excluded.** Direction: excluding step 1 removes
   > a roughly common offset and **widens** the learned-vs-AF gap → the "3–5×" quoted here is **conservative**,
   > not optimistic. The figures are NOT regenerated: correcting in the direction that flatters our own arms is
   > the documented MR trap. **Quote the ratio as-is, with this caveat; never quote a step-1-excluded ratio
   > without a data-blind prereg + cross-model G6.**
5. **p_base ≥ 1.0 EE crossover** (learned > AF) = **OOD nominal-transfer, NOT matched-retrain, NOT G6'd** →
   caption must mark it "non-win / under test" (matched-retrain @ p_base=1.0 is the separate go-server experiment).
6. **v_max (k_cap) = TRANSFER-only** — nominal weights (k_cap=3) evaluated at other k_cap; a DIFFERENT protocol
   than setA's matched-retrain `ee_vs_vmax`. Symbol = `v_max` (not the code id k_cap).

## Per-axis summary (seed-pooled means; full RAW+CI in the CSV/JSON)
### num_users  (values = 40, 60, 80, 100, 120, 140, 160, 180, 200, 220; n_ep=200, seeds=[42, 137, 271])

EE (η_EE, ÷1e6) / ho_rate / min_cov, seed-pooled means:

| arm | 40 | 60 | 80 | 100 | 120 | 140 | 160 | 180 | 200 | 220 |
|---|---|---|---|---|---|---|---|---|---|---|
| MCCRL | 540/0.098/0.78 | 489/0.099/0.75 | 447/0.099/0.69 | 413/0.098/0.73 | 398/0.099/0.72 | 376/0.099/0.73 | 361/0.098/0.76 | 349/0.098/0.76 | 333/0.098/0.77 | 324/0.098/0.78 |
| MCCRL w/o catfish | 540/0.099/0.68 | 483/0.099/0.60 | 442/0.099/0.61 | 410/0.099/0.63 | 391/0.098/0.62 | 371/0.099/0.64 | 353/0.099/0.67 | 340/0.099/0.66 | 326/0.099/0.69 | 319/0.099/0.68 |
| MCCRL w/o coordinate | 180/0.100/0.00 | 155/0.100/0.00 | 136/0.100/0.00 | 116/0.100/0.00 | 119/0.100/0.00 | 103/0.100/0.00 | 98/0.100/0.00 | 93/0.100/0.00 | 91/0.100/0.00 | 88/0.100/0.00 |
| MCCRL w/o learning | 565/0.412/0.97 | 499/0.399/0.98 | 464/0.362/0.98 | 432/0.359/0.98 | 405/0.369/0.98 | 374/0.384/0.98 | 369/0.344/0.98 | 355/0.341/0.97 | 345/0.327/0.98 | 332/0.319/0.97 |
| MODQN | 162/0.100/0.00 | 140/0.101/0.00 | 122/0.100/0.00 | 106/0.100/0.00 | 108/0.100/0.00 | 94/0.100/0.00 | 89/0.100/0.00 | 84/0.101/0.00 | 82/0.100/0.00 | 80/0.100/0.00 |

### p_base_w  (values = 0.1, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5; n_ep=48, seeds=[42, 137, 271])

EE (η_EE, ÷1e6) / ho_rate / min_cov, seed-pooled means:

| arm | 0.1 | 0.25 | 0.5 | 0.75 | 1 | 1.25 | 1.5 | 1.75 | 2 | 2.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| MCCRL | 444/0.098/0.68 | 413/0.098/0.68 | 371/0.098/0.68 | 338/0.098/0.68 | 311/0.098/0.68 | 288/0.098/0.68 | 269/0.098/0.68 | 252/0.098/0.68 | 237/0.098/0.68 | 213/0.098/0.68 |
| MCCRL w/o catfish | 429/0.097/0.60 | 400/0.097/0.60 | 359/0.097/0.60 | 327/0.097/0.60 | 301/0.097/0.60 | 279/0.097/0.60 | 260/0.097/0.60 | 244/0.097/0.60 | 230/0.097/0.60 | 206/0.097/0.60 |
| MCCRL w/o coordinate | 129/0.100/0.00 | 117/0.100/0.00 | 103/0.100/0.00 | 92/0.100/0.00 | 83/0.100/0.00 | 76/0.100/0.00 | 70/0.100/0.00 | 65/0.100/0.00 | 61/0.100/0.00 | 54/0.100/0.00 |
| MCCRL w/o learning | 472/0.311/0.97 | 448/0.307/0.99 | 391/0.376/1.00 | 347/0.417/1.00 | 306/0.482/1.00 | 293/0.440/1.00 | 272/0.468/1.00 | 253/0.487/1.00 | 235/0.502/1.00 | 210/0.521/1.00 |
| MODQN | 116/0.100/0.00 | 106/0.100/0.00 | 93/0.100/0.00 | 83/0.100/0.00 | 76/0.100/0.00 | 69/0.100/0.00 | 64/0.100/0.00 | 59/0.100/0.00 | 56/0.100/0.00 | 49/0.100/0.00 |

### p_max_w  (values = 2, 4, 6, 8, 10, 15, 20, 30, 40, 50; n_ep=48, seeds=[42, 137, 271])

EE (η_EE, ÷1e6) / ho_rate / min_cov, seed-pooled means:

| arm | 2 | 4 | 6 | 8 | 10 | 15 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|---|---|---|---|---|
| MCCRL | 417/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 | 413/0.098/0.68 |
| MCCRL w/o catfish | 405/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 | 400/0.097/0.60 |
| MCCRL w/o coordinate | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 | 117/0.100/0.00 |
| MCCRL w/o learning | 487/0.301/0.99 | 448/0.307/0.99 | 448/0.307/0.99 | 448/0.307/0.99 | 448/0.307/0.99 | 448/0.307/0.99 | 448/0.307/0.99 | 448/0.307/0.99 | 448/0.307/0.99 | 448/0.307/0.99 |
| MODQN | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 | 106/0.100/0.00 |

### bandwidth_hz  (values = 1e+08, 2e+08, 3e+08, 4e+08, 5e+08, 6e+08, 7e+08, 8e+08, 9e+08, 1e+09; n_ep=48, seeds=[42, 137, 271])

EE (η_EE, ÷1e6) / ho_rate / min_cov, seed-pooled means:

| arm | 1e+08 | 2e+08 | 3e+08 | 4e+08 | 5e+08 | 6e+08 | 7e+08 | 8e+08 | 9e+08 | 1e+09 |
|---|---|---|---|---|---|---|---|---|---|---|
| MCCRL | 114/0.098/0.68 | 201/0.098/0.68 | 278/0.098/0.68 | 348/0.098/0.68 | 413/0.098/0.68 | 474/0.098/0.68 | 532/0.098/0.68 | 587/0.098/0.68 | 640/0.098/0.68 | 690/0.098/0.68 |
| MCCRL w/o catfish | 111/0.097/0.60 | 195/0.097/0.60 | 269/0.097/0.60 | 337/0.097/0.60 | 400/0.097/0.60 | 459/0.097/0.60 | 515/0.097/0.60 | 568/0.097/0.60 | 619/0.097/0.60 | 668/0.097/0.60 |
| MCCRL w/o coordinate | 32/0.100/0.00 | 57/0.100/0.00 | 79/0.100/0.00 | 99/0.100/0.00 | 117/0.100/0.00 | 135/0.100/0.00 | 152/0.100/0.00 | 168/0.100/0.00 | 183/0.100/0.00 | 198/0.100/0.00 |
| MCCRL w/o learning | 120/0.341/1.00 | 216/0.329/1.00 | 297/0.330/1.00 | 380/0.305/0.99 | 448/0.307/0.99 | 514/0.314/0.99 | 577/0.322/0.98 | 629/0.344/0.97 | 693/0.333/0.98 | 744/0.342/0.98 |
| MODQN | 30/0.100/0.00 | 52/0.100/0.00 | 72/0.100/0.00 | 90/0.100/0.00 | 106/0.100/0.00 | 122/0.100/0.00 | 136/0.100/0.00 | 150/0.100/0.00 | 164/0.100/0.00 | 176/0.100/0.00 |

### noise_psd_dbm_hz  (values = -180, -176, -172, -168, -164, -160, -156, -152, -148, -144, -140; n_ep=48, seeds=[42, 137, 271])

EE (η_EE, ÷1e6) / ho_rate / min_cov, seed-pooled means:

| arm | -180 | -176 | -172 | -168 | -164 | -160 | -156 | -152 | -148 | -144 | -140 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MCCRL | 549/0.098/0.68 | 458/0.098/0.68 | 368/0.098/0.68 | 279/0.098/0.68 | 195/0.098/0.68 | 122/0.098/0.68 | 67/0.098/0.68 | 32/0.098/0.68 | 14/0.098/0.68 | 6/0.098/0.68 | 2/0.098/0.68 |
| MCCRL w/o catfish | 532/0.097/0.60 | 444/0.097/0.60 | 356/0.097/0.60 | 270/0.097/0.60 | 189/0.097/0.60 | 119/0.097/0.60 | 66/0.097/0.60 | 32/0.097/0.60 | 14/0.097/0.60 | 6/0.097/0.60 | 2/0.097/0.60 |
| MCCRL w/o coordinate | 154/0.100/0.00 | 130/0.100/0.00 | 105/0.100/0.00 | 81/0.100/0.00 | 57/0.100/0.00 | 36/0.100/0.00 | 20/0.100/0.00 | 9/0.100/0.00 | 4/0.100/0.00 | 2/0.100/0.00 | 1/0.100/0.00 |
| MCCRL w/o learning | 579/0.336/1.00 | 490/0.331/0.99 | 395/0.343/0.97 | 314/0.284/0.97 | 233/0.201/0.97 | 157/0.133/0.97 | 89/0.119/0.96 | 46/0.102/0.97 | 21/0.101/0.98 | 9/0.099/0.97 | 4/0.097/0.97 |
| MODQN | 142/0.100/0.00 | 118/0.100/0.00 | 94/0.100/0.00 | 71/0.100/0.00 | 48/0.100/0.00 | 29/0.100/0.00 | 15/0.100/0.00 | 7/0.100/0.00 | 3/0.100/0.00 | 1/0.100/0.00 | 1/0.100/0.00 |

### k_cap  (values = 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15; n_ep=48, seeds=[42, 137, 271])

EE (η_EE, ÷1e6) / ho_rate / min_cov, seed-pooled means:

| arm | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MCCRL | 413/0.098/0.68 | 383/0.098/0.73 | 337/0.099/0.73 | 296/0.099/0.75 | 259/0.099/0.78 | 230/0.099/0.81 | 198/0.099/0.82 | 168/0.100/0.82 | 148/0.100/0.83 | 130/0.100/0.83 | 114/0.100/0.85 | 101/0.100/0.85 | 89/0.100/0.87 |
| MCCRL w/o catfish | 400/0.097/0.60 | 368/0.098/0.64 | 338/0.098/0.65 | 302/0.099/0.65 | 265/0.099/0.70 | 236/0.099/0.70 | 208/0.099/0.72 | 179/0.100/0.76 | 159/0.100/0.76 | 143/0.100/0.78 | 128/0.100/0.83 | 113/0.100/0.85 | 101/0.100/0.87 |
| MCCRL w/o coordinate | 117/0.100/0.00 | 119/0.100/0.00 | 120/0.100/0.00 | 111/0.100/0.00 | 106/0.100/0.00 | 102/0.100/0.00 | 93/0.100/0.00 | 88/0.100/0.00 | 85/0.100/0.00 | 82/0.100/0.00 | 81/0.100/0.00 | 79/0.100/0.00 | 78/0.100/0.00 |
| MCCRL w/o learning | 448/0.307/0.99 | 341/0.601/0.99 | 278/0.736/1.00 | 228/0.840/1.00 | 198/0.887/1.00 | 176/0.920/1.00 | 175/0.935/1.00 | 176/0.952/1.00 | 178/0.958/1.00 | 181/0.949/1.00 | 192/0.941/1.00 | 197/0.954/1.00 | 210/0.946/1.00 |
| MODQN | 106/0.100/0.00 | 104/0.100/0.00 | 103/0.100/0.00 | 95/0.100/0.00 | 91/0.100/0.00 | 87/0.100/0.00 | 79/0.100/0.00 | 74/0.100/0.00 | 72/0.100/0.00 | 70/0.100/0.00 | 68/0.100/0.00 | 67/0.100/0.00 | 66/0.100/0.01 |
