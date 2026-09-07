# HANDOFF — ch5 result-figure Origin switch (EN-only) + retire superseded lineages

> Paste as the FIRST message of a NEW Claude Code conversation in `/home/u24/papers/modqn-paper-reproduction`.
> READ-ONLY-first, then a RED-LINE-sensitive thesis-figure edit. **No training, no server, no Origin drawing.**
> This is the deferred deliverable-3 of the semantic figure-dedup task; the read-only analysis + the R3 decision
> are already done — do NOT redo them.

## Decided upstream (do NOT relitigate)
- **R3 = Option A** (2026-07-03, USER): **Origin (`scratch/final_figures/paper-figures/`) is the final canonical
  render set** for the paper's result figures.
- **Figure scheme = EN-only** (2026-07-03, USER): the **English** thesis is the deliverable. The **ZH** ch5
  figure scheme (`thesis-mc/ch5-experimental-result.md` → `figures/results-v3/panel4_{ee,min_cov}`) is **NOT
  preserved** — do not spend effort re-pointing ZH figures.
- **Phase-1 dedup archive already DONE** (reversible `mv` → `paper-figures/_archive/2026-07-03/`, 69 files:
  whole `result-v4` + `paper_figs` + loose `fig5_*.png` + 2 conf-demo `panel4` orphans). Full identity map +
  build-safety = **`scratch/final_figures/paper-figures/SEMANTIC-FIGURE-INDEX.md`** (read §5 build-safety + §6
  matrix + the R3-execution block). `rm` of `_archive/` is pending USER confirm — NOT this task.

## Goal (this conversation)
Switch the **EN ch5** result-figure embeds from the matplotlib lineages (`results/`, `results-v2/`) to the
matching **Origin** PNGs, resolve the 4 coverage gaps WITH the USER, re-verify every touched caption stays
RED-LINE-honest, rebuild + verify the EN docx, then archive the now-superseded matplotlib lineages
(reversible, build-safe, approval-gated).

## Read first (authority)
- `CURRENT-STATE.md` — LIVE LINE + the 3 RED LINES (binding narrative).
- `scratch/final_figures/paper-figures/SEMANTIC-FIGURE-INDEX.md` — the identity map (this task's spine).
- `scratch/final_figures/paper-figures/PAPER-FIGURE-CATALOG.md` — Origin inventory (31 figs) + the ★ guardian caveats.
- `thesis-mc/FIGURE-EXPLAINER.md` — figure↔data↔claim + per-figure RED LINES.
- `thesis-mc/figures/results-v2/INDEX.md` + `results-v3/INDEX.md` — the honest-framing notes the current EN figs encode.
- `thesis-mc/WRITING-RULES.md` (R3 结果文字↔图 coupling, R16 Word format) + the EN ch5 files below.

## The EN ch5 embed set → Origin mapping (the core table)
Files: `thesis-mc/en/ch5-experimental-result.en.md` **and** `thesis-mc/en/bilingual/bi-ch5-experimental-result.md`
(both embed the same 12 — re-point BOTH). Origin PNGs live at
`paper-figures/<project>/origin_out/png/<name>_origin.png` (+ SVG vector siblings).

| EN Fig | current embed | Origin target (`…_origin.png`) | status |
|---|---|---|---|
| 5-1 | `results/fig5_1_nominal_bars.png` | `P3-ablation/…/nominal_ablation_4cell_origin` | ⚠ **different cut** — matplotlib = 4-metric × 5-arm (B0/B1/B2/A1/A2); Origin 4cell = min_cov+Jw × 4-cell (B0/B2/A1/A2). Decide (below). |
| 5-2 | `results/fig5_2_pareto.png` | `P1-win-pareto/…/pareto_jw_vs_mincov_origin` | ✅ direct |
| 5-3 | `results-v2/bandwidth_min_user_rate.png` | `_appendix/…/min_user_rate_vs_bandwidth_origin` | ✅ direct |
| 5-4 | `results-v2/bandwidth_ee.png` | `P4-robustness/…/ee_vs_bandwidth_origin` | ✅ direct |
| 5-5 | `results-v2/bandwidth_total_thr.png` | `P4-robustness/…/throughput_vs_bandwidth_origin` | ✅ direct (total_thr = throughput) |
| 5-6 | `results-v2/bandwidth_min_cov.png` | `P4-robustness/…/min_cov_vs_bandwidth_origin` | ✅ direct |
| 5-7 | `results-v2/noise_min_user_rate.png` | **— none —** | ✗ **HARD GAP** (Origin `_appendix` has min_user_rate vs bandwidth/vmax/num_users, **not noise**) |
| 5-8 | `results-v2/noise_ee.png` | `P4-robustness/…/ee_vs_noise_origin` | ✅ direct |
| 5-9 | `results-v2/noise_total_thr.png` | `P4-robustness/…/throughput_vs_noise_origin` | ✅ direct |
| 5-10 | `results-v2/noise_min_cov.png` | `P4-robustness/…/min_cov_vs_noise_origin` | ✅ direct |
| 5-11 | `results-v2/kcap_le10_min_cov.png` | `P4-robustness/…/min_cov_vs_vmax_origin` | ⚠ **framing** — matplotlib = k_cap **≤10 crop**; Origin = **full 13-pt** (k=3..15) |
| 5-12 | `results-v2/qosfloor_min_qos_cov.png` | **— none —** | ✗ **HARD GAP** (no Origin qos_floor figure at all) |

→ **8 map directly**, 2 need a framing call (5-1, 5-11), **2 have no Origin twin** (5-7, 5-12).

## ★★ THE #1 HONESTY ITEM (RED LINE c — do this or the switch is dishonest)
**Origin line plots DROP `DQN_scalar` (7-arm); the current `results-v2` bandwidth/noise EE/throughput figures
SHOW it.** `DQN_scalar` tops EE/throughput **by starving coverage** (min_cov≈0.15) — RED LINE (c) requires that
weakness stay disclosed. After switching to Origin's 7-arm EE/throughput panels, **verify `DQN_scalar`'s
efficiency-by-starvation is STILL disclosed** (it remains in the P1 Pareto `pareto_jw_vs_mincov` + the §5.3/§5.5
text). **No efficiency figure may end up reading as an unqualified "ours is most efficient."** (See
`results-v3/INDEX.md` "SCOPED no-DQN_scalar variants" — same trap.)

## Decisions to get from the USER BEFORE editing (AskUserQuestion)
1. **Gap 5-7 (noise×min_user_rate)** and **5-12 (qos_floor):** per gap — (a) **drop the figure** (5-7 is
   arguably redundant with 5-3 bandwidth×min_user_rate; 5-12 is a niche robustness cut), OR (b) **keep the
   matplotlib fig as a documented exception** (breaks the "all-Origin" cleanliness), OR (c) **commission a new
   Origin figure** — that is an Origin-driver job on `/mnt/d/*` which is **USER-owned; do NOT fake it** — the
   `cdrl_style` noise + `cdrl_qos_floor_bps_sweep_raw.csv` data exist, so it is producible, but only the USER
   runs the Origin side.
2. **Fig 5-1 (nominal):** (a) adopt Origin `nominal_ablation_4cell` and rewrite the §5.2 text/caption to the
   4-cell (min_cov+Jw) content, OR (b) keep matplotlib `fig5_1_nominal_bars` as an exception, OR (c) commission
   an Origin 4-metric nominal (USER `/mnt`).
3. **Fig 5-11 (kcap):** (a) adopt Origin full-13 `min_cov_vs_vmax` and adjust the caption to the full range, OR
   (b) keep the ≤10 crop as an exception.
4. **ZH ch5 disposition:** confirm — deprecate ZH ch5 figures (leave `thesis-mc/ch5-experimental-result.md` as
   ZH-source but stop treating its `panel4` embeds as a build target), OR mirror the same Origin switch into ZH.
   Since USER said "EN-only," default = **deprecate ZH figs** → then `results-v3` (all 21) becomes retirable.

## Deliverables (in order)
1. Confirm the mapping + the 4 gap resolutions + ZH disposition with the USER (one AskUserQuestion round).
2. **Re-point the EN embeds:** copy the chosen Origin PNGs into `thesis-mc/figures/` (suggest a new
   `figures/results-origin/` dir so provenance is obvious; `build_ris.sh` copies all of `figures/` into the
   build, so any subdir works) and update the `![…](figures/…)` paths in **both** `en/ch5-experimental-result.en.md`
   and `en/bilingual/bi-ch5-experimental-result.md`. Renumber `Fig 5-x` + fix cross-refs if any figure is dropped.
3. **Re-verify captions** against the Origin render: arm count (7 vs 8), units (Origin bandwidth = **MHz**),
   what-is-on-top, and the RED LINES (esp. the DQN_scalar disclosure item above). Update caption text to match
   what the Origin figure actually shows.
4. **Rebuild + verify:** build the EN docx **via the `build-mc-thesis-docx` skill only** (a guard hook blocks
   raw pandoc); confirm every image embeds + renders + no dangling embed (`grep` the EN ch5 embeds resolve).
5. **Archive the superseded lineages** (reversible `mv` → `paper-figures/_archive/2026-07-03/`): the
   now-unused `results-v2/*`, `results/*` leftovers, and (per ZH decision) `results-v3/*`. **grep-before-retire**
   every file; retire a file only AFTER its embed is re-pointed. Reconcile `CLEANUP-REPORT.md` +
   `SEMANTIC-FIGURE-INDEX.md` + `CURRENT-STATE.md`.
6. **Cross-model G6** on the honesty of the switched captions (codex + gemini per `feedback_codex_review_required`
   / `reference_agy_gemini_cli_invocation`) BEFORE declaring done — the caption rewrites are load-bearing.

## HARD constraints (binding)
- **RED LINES (from `THESIS-FRAMING-DECISION-2026-06-28` / `FIGURE-EXPLAINER §RED LINES`):** (a) ablation numbers
  accurate + present; (b) NO false causal claim ("catfish drives the win" / "removing catfish → collapse" — the
  de-collapse engine is the **coordinated allocation step**, A1≈A2); (c) **NO false raw-scalar win over
  DQN_scalar** — win framed on fairness/coverage (min_cov≈1.0 + EE at tight capacity); (d) tag load-bearing
  claims `grounded`/`hypothesis`/`ruled-out`; (e) no "root cause solved", no "2.8× / beats-Sun2024".
- **Never break a build:** `grep thesis-mc/ conf-demo/` for a figure's embed path BEFORE retiring it. conf-demo
  (`figs/ee_users`,`ee_bw`,`fig4`,`fig8`,`fig_sysmodel`) is a **separate** build — out of scope, do not touch.
- **Reversible only:** archive→hold (`_archive/2026-07-03/`); `rm` only after USER confirms the archived set.
- **Source CSVs stay put** (`fig5_*.csv`, `cdrl_style/axis_*/*_raw.csv`+`.json`) — never delete (feed Origin + thesis).
- **`/mnt/*` HANDS-OFF (USER-owned):** any NEW Origin figure = a USER Origin-driver task; do NOT draw/fake one.
- **G1** `src/…/algorithms/modqn.py` (`aa877676`) + **EUV** `src/…/env/family_b_step.py` (`389eaaef`) untouched
  (task doesn't go near them; assert pre==post anyway).
- **Commit** direct-to-main **only if the USER asks** (do not auto-branch, do not auto-commit).

## Stop rules
- STOP + ask before: any deletion, any move of a build-referenced file, any `/mnt` or cross-repo action, any
  gap resolved by "commission a new Origin figure" (that's a USER `/mnt` task — hand it back).
- If the USER has not answered the gap/ZH decisions, STOP after deliverable 1.
- **Reply in Traditional Chinese** (prose); code / paths / identifiers stay English.
