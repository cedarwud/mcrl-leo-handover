# Figure cleanup plan / classification — 2026-07-07

Reversible bucketing of every result-figure location, per USER task ("archive + manifest
now, delete on my instruction"). **Nothing live-referenced was deleted or moved.**

## KEEP — canonical (source of truth; never archive)
- `scratch/final_figures/cdrl_style/axis_*/cdrl_*_raw.csv` + `.json` — RAW means + bootstrap CI, the data authority behind every figure (setA, /mnt/d P1–P4, ch5 origin all read these).
- `scratch/final_figures/fig5_*_raw.csv` — nominal 2×2 + k_cap authority CSVs.
- **NEW** `thesis-mc/figures/setA-2026-07-07/` (8 PNG + 8 CSV + manifest) — the clean 4-arm honest set (this session). Mirror: `/mnt/d/origin-paper-figures/setA-2026-07-07/`.

## KEEP — live submission renders (referenced by ch5 / are the /mnt/d warehouse)
- `/mnt/d/origin-paper-figures/{P1-win-pareto,P2-decollapse,P3-ablation,P4-robustness,_appendix}/` — 31-fig Origin submission database, all sourced from the canonical CSVs above. **NOT broken.**
- `thesis-mc/figures/results-origin/*.png` — the Origin renders ch5 currently embeds (all 3 languages). **Live.**
- `thesis-mc/figures/results/fig5_1_nominal_bars.png` — referenced by ch5.

## DELETED this session — orphan buggy-generation renders (git rm; reversible via git history)
19 PNGs from the old buggy render scripts (`render_thesis_v3_server.py`, v_cap symbol), each
self-verified to have **zero references** anywhere. `results-v3/` 6.7M → 1.9M. Recover any via
`git checkout HEAD -- <path>`. List = all `results-v3/{cdrl_*,kcap_vcap_*,users_*}` except `panel4_*`.

## DELETE-BLOCKED — buggy/superseded BUT still referenced (needs a coordinated repoint first)
Deleting these now = broken ch5 embeds / dangling doc refs. Purge only AFTER repointing.
- **ch5-embedded (all langs):** `results-v3/panel4_ee.png`, `results-v3/panel4_min_cov.png` (ZH §5.5);
  `results-v2/qosfloor_min_qos_cov.png`, `results/fig5_1_nominal_bars.png` (EN+bi).
- **live-doc-referenced smoothed (σ=1.3) renders:** `results/fig5_4{a,c,d,e}_*.png` + `results/fig5_2_pareto.png`
  — cited by `thesis-mc/FIGURE-EXPLAINER.md`, `docs/data-catalog/CATALOG.md`, the 2026-07-05/07 web-agent packs,
  and `CH5-FIG-SMOOTHING-FIX-NOTE`. Repoint/retire those refs before deleting.
- **`results-origin/*` = NOT buggy** — current EN/bi ch5 Origin set from the canonical CSVs; retired only if the
  "取代 with Set A" repoint lands (Decision Q1=取代). Kept until then.

## ALREADY-PURGED by the other running process (do NOT fight it — git shows these as `D`)
- `thesis-mc/figures/result-v4/**` (semantic-dup of results-origin; CATALOG already archived a copy 2026-07-03).
- `scratch/final_figures/fig5_*.png` (PNG only; the `fig5_*_raw.csv` authority is kept).
- `dr/*.md` (deep-research engine dumps; moved to `docs/research/open-solutions-deepresearch-2026-07-06/`).

## ARCHIVED this session — unreferenced scratch smoke/debug (reversible)
- 44 files, 4.09 MB → `scratch/final_figures/_archive/2026-07-07/` (+ `ARCHIVE-MANIFEST.csv` with sha256 + per-file restore cmd). Sets: `axis_sat_speed_km_s/*smoke-vel*`, `axis_slot_duration_s/*smoke-ho*`+`*skipdbg*`, `axis_num_users/*ho-nousers*`. None referenced by any tracked doc; superseded by the dense sweeps.

## NOT MINE — repo-root strays from the other process (left untouched)
- Root-level `users.png`, `p_base.png`, `ee/`, `png_origin/`, `slides/`, and stray scripts
  (`dump_*.py`, `extract*.py`, `flat.py`, `verify.py`, `print_values.py`) — another session's working dumps. Flagged, not touched.

---
## Decisions needed (gate the rest of the purge)
- **A — ch5 figure source:** does the new 4-arm `setA-2026-07-07` REPLACE the 7-arm `results-origin`
  figures in ch5 main text, or COEXIST (setA = clean main-text story, results-origin/appendix = full 7-arm robustness)?
  Answer unblocks purging `results-v2/` + `results-v3/`.
- **B — hard-delete** the reversible `_archive/2026-07-07/` (44 smoke files) now, or keep archived?
