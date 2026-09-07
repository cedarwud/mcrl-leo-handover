# k_cap SWEEP — SMOOTHING ARTIFACT + HIGH-k NOISE FINDINGS (2026-06-29)

> **Load-bearing, grounded (CSV-direct). Surfaced by USER spotting the r2 cliff in `fig5_4e_kcap_r2.png`.**
> Authority data = `scratch/final_figures/fig5_4_kcap_sweep_raw.csv` (raw per-point) +
> `fig5_4_kcap_sweep.csv` (Gaussian σ=1.3 smoothed, what the PNGs plot).
> **Action owners:** result-fig session (fix the plots) + paper ch5/ch6 session (re-derive verdicts from RAW+CI).
> Do NOT ship the misleading smoothed curves / the over-clean "k≤12 win, flip k=13" wording without this fix.

---

## 1. `fig5_4e` r2 (handover penalty) "cliff at k=15" = SMOOTHING ARTIFACT (not real) `grounded`

A2 (Proposed MCCRL) `r2_mean`:

| k | RAW | SMOOTHED (plotted) |
|---|---|---|
| 12 | −0.0871 | −0.0863 |
| 13 | **−0.1007** | −0.0845 |
| 14 | **−0.0520** (CI −0.057,−0.047 — tight, isolated good point) | −0.0838 |
| 15 | **−0.1001** | **−0.1001** |

- **Smoking gun:** smoothed k=15 == raw k=15 (−0.1001, unchanged) while smoothed k=12–14 were pulled up to ~−0.084.
  Gaussian σ=1.3 smeared the **isolated k=14 good point (−0.052)** into k=12–14 (false plateau) but the **boundary point
  k=15 has no right-neighbour → barely smoothed → stays at its raw −0.10** → a **false cliff**.
- **Truth:** r2 is **noisy across all k** (raw bounces −0.06…−0.10); k=13 and k=15 are BOTH ≈ −0.10. There is no
  physical "plateau then collapse". r2 is the 0.3-weight axis + NOT a headline, but the curve as drawn is misleading.
- **FIX (result-fig session):** do not over-smooth r2 (and re-check every sweep metric for the same boundary effect):
  options = plot RAW points + CI band, OR boundary-aware smoothing (`mode='nearest'`, and/or shrink σ), OR mark it
  noisy. Whatever is chosen, the LAST point must be smoothed on the same footing as the interior (no raw boundary leak).

## 2. `fig5_4c` min-coverage "2 flat lines" = REAL, NOT an artifact — KEEP `grounded`

- A2 `min_cov` ≈ **1.0 at every k** (0.9998–1.0); B0 ≈ **0.0 at every k** (tiny rise 0→0.008 by k=15).
- This is the **cleanest + strongest headline** (MCCRL full coverage at all capacities; MODQN starves the tail at all
  capacities). Genuine data, not smoothing. Keep. (Optional: show markers / annotate values so it doesn't read as a
  placeholder; widen-y not needed.)

## 3. HIGH-k Jw is NOISIER than the smoothed curve shows — RE-DERIVE win-zone from RAW + CI `grounded`

A2 vs B0 `jw_mean` (RAW):

| k | A2 jw (raw) | B0 jw (raw) | RAW+CI verdict |
|---|---|---|---|
| 3 | **4.82e-4** | −1.0e-5 | A2 CI-win (huge) |
| 4–7 | 4.38e-4 → 1.34e-4 | ~0 | A2 CI-win |
| 8–10 | 6.3e-5 → 3.8e-5 | ~7e-6–1.3e-5 | A2 CI-win (k=10: A2 lo 2.69e-5 > B0 hi 1.46e-5) |
| **11** | 1.53e-5 [4.2e-6, 2.65e-5] | **6.2e-5 [4.66e-5, 7.80e-5]** | **B0 CI-WINS** (raw) |
| 12 | 5.79e-5 | 2.01e-5 | A2 raw-higher (check CI) |
| 13 | −6.04e-5 | 7.6e-6 | B0 |
| 14 | 5.56e-5 | 1.67e-5 | A2 |
| 15 | −6.85e-5 | 2.15e-5 | B0 |

- **CI-separated A2 win holds k=3…k=10.** At **k=11 the RAW data has B0 CI-separating ABOVE A2** — but the SMOOTHED
  csv turns k=11 into A2≈B0 "tie" (smoothed A2 2.85e-5 ≈ B0 2.71e-5, CIs overlap). **Smoothing changed the verdict.**
- k=12–15 raw = small + **zigzag** (A2 and B0 trade sub-1e-4 wins inside the noise). The smoothed "clean win-zone
  k≤12, monotone flip at k=13" is an **over-clean reading of noisy data**.
- **Bidirectional honesty (NOT deflation):** the CORE win is **solid + unaffected** — low/tight capacity (k=3…~10,
  CI-separated) + the factorial k=3 headline (A2 4.82e-4 vs B0 −1e-5). The EE + coverage axes have A2 **dominating at
  ALL k**. Only the **high-k weighted-scalar (Jw) tail is noisy**, and the win-zone boundary is within the noise.
- **FIX (paper ch5/ch6 session):**
  1. Report TABLE-5.5 values + the win/lose verdict from **RAW means + bootstrap CI**, NOT the smoothed mean
     (smoothed curve = visual only). Verify whether TABLE-5.5 currently uses smoothed values — if so, switch to raw+CI.
  2. Reframe the narrative: **"win is strong + CI-separated at tight capacity (k≤~10); at high capacity both methods
     converge toward zero on the weighted scalar and trade small wins within the noise — MCCRL keeps its EE + coverage
     dominance throughout."** Drop the crisp "win zone k≤12 / clean flip at k=13" wording.
  3. Re-check `CURRENT-STATE.md` + `mc-modqn-base.md` abstract/ch1 + ch5/ch6 for the "k≤12 / flip 13–15" phrasing and
     align to the raw+CI scope. The k=11 raw-B0-win in particular contradicts "A2 wins k≤12".

---

## 4. Process note (anti-MR)
The earlier result-fig QA pass ("data locked / verified") did **not** catch this — it checked values-vs-RESULT.json
but not the **smoothing transform** or the **raw-vs-smoothed verdict drift**. Lesson: verify the SMOOTHING/transform +
the boundary handling + verdicts-on-raw, not just point values. Cross-model review (gemini, codex off this round) must
be fed THIS note + RAW csv, not the smoothed curve.

---

## RESOLUTION — ch5/ch6/abstract/CURRENT-STATE re-derived from RAW+CI (2026-06-29, paper-text session)

**Done (text only; `thesis-mc/` + `CURRENT-STATE.md` + `.agent-memory/MEMORY.md`; figures = result-fig session's job; G1/EUV untouched).**

- **Self-verified the RAW+CI verdict programmatically** from `fig5_4_kcap_sweep_raw.csv` (A2 wins ⇔ A2 ci_lo > B0 ci_hi):
  - **J_w CI-separated winner per k:** A2 at k=3,4,5,6,7,8,9,10,12,14 · B0 at k=11,13,15.
  - So: **A2 CI-separated win for k=3–10 (8 consecutive).** At **k≥11 every point's CI still separates, but the winner ALTERNATES** (B0 11/13/15, A2 12/14), all magnitudes **sub-1e-4 → 0**, driven by per-point independent training ⇒ **no stable trend** (NOT "tie", NOT "noise" — see Gemini catch below).
  - **min_cov:** A2 ≈1.0 ALL k; B0 ≈0 ALL k (only k=15 → ~0.008). **EE (r1): A2 CI-separated > B0 at EVERY k.**
- **TABLE-5.5 switched from SMOOTHED→RAW.** Confirmed the old table used smoothed values (matched `fig5_4_kcap_sweep.csv`), incl. B0 min_cov k=13/14 = smoothed 0.001/0.003 while RAW = 0.0. New table = raw means + raw-CI winner col + caption explaining smoothing is visual-only.
- **§5.5 / §5.6 / ch6 §6.1-6.3 / abstract / ch1-contrib reframed:** dropped "win zone k≤12 / clean flip k=13"; new framing = "**CI-separated J_w win at tight capacity k≤10; at k≥11 both →0 on J_w and trade tiny (<1e-4) point-wise wins with no stable ordering; coverage + EE dominate ALL k**". Also fixed the **dimension-ablation r2 prose** (removed an unsupported "no_handover consistently worsens handover k=9–12" directional claim — raw r2 bounces with no consistent direction; kept the real k=14 single-point contrast) + FIG-5.4 caption flags r2 as the noisy axis.
- **Cross-model review = agy Gemini 3.1 Pro (High), refute-by-default, fed THIS note + RAW data (not the smoothed curve) ⇒ OVERALL SOUND.** One legitimate catch folded (MAJOR→resolved): do **not** call CI-*separated* high-k differences "雜訊/noise" (disjoint CIs ≠ noise) → reworded to "信賴區間仍分開，但勝方逐點互換 + 差距 <1e-4 + 反映各自獨立訓練的起伏 → 無穩定方向". Q3 over-deflation nudge folded too (the J_w hedge no longer buries the all-k coverage/EE dominance). Review log: `/tmp/.../scratchpad/gemini_review_out.txt`.
- **Bidirectional MR guard:** the CORE win is intact + unflattened — k=3 factorial A2 4.82e-4 vs B0 −1e-5 (CI-sep, huge) + coverage/EE all-k dominance are SOLID; this is an honest boundary fix, NOT win-death.
