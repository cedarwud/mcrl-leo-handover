# Results registry — every citable number, and the conditions that produced it

Curated 2026-09-11 by CURATE (read-only; no number here was re-measured). Companion files:
`.scratch/DOCUMENT-STATUS.md` (which documents are in force) and
`.scratch/curation/PROVENANCE-HEADER.md` (the block every new report must carry).

> Owner instruction this file serves: *"要小心不要把舊專案的一些結果混進來了，新專案本身的很多結果也是基於
> 不同的條件生成的，全部都要備註清楚不能誤用."* A number here is a property of the procedure that produced
> it. Before comparing two rows, check §3.

**How the rows were built.** Each row records what its source document *says*. Where two documents
disagree about a number's conditions, both are listed and the row says `CONFLICT`. Rows marked with
prefixes `AP/CF/RH/DQ/LF/DR/RV/TD/DS` (grounding, reviews, deltas), `CS/ZC/ZT/CH/SC` (catfish-surface,
zclose, zscore-transfer, concept-harvest, catfish-screens) and `SV` (V0.25 server reports, read over
read-only ssh) were extracted by three read-only extraction passes and spot-checked; `FF/BP/B0/PA/CP/EM/CT`
were written directly from the reports and controller documents. Several rows bundle 2–6 values that
share every condition. `UNKNOWN` means the source does not say.

---

## 0. Read this first — the five condition traps

1. **Two TLE archives on the MODQN harness (B0 ruling §4; `.scratch/b0-corrected/PROGRESS.md:1-17`).**
   - **Pinned** archive: `file_set_sha256 427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`
     (373 files, 2025-07-27…2026-08-20; pin commit `b924c8a0`; == the frozen R2 prereg's ephemeris hash).
     Placebo signature: **RANDOM_MASKED = 52,420,510.0956937 bit/J** (24 ep, seeds 42/1337/7), bit-identical
     on local and sat. The frozen checkpoint `e6b063ef…` and its `episode-logs.json` were produced on this
     archive (sat's default before the pin; same content).
   - **Unpinned** local archive `~/demo/tle_data/starlink/tle`, `file_set_sha256 e07f3e1e879dafd2…093e4`
     (392 files). Placebo signature: **RANDOM_MASKED = 53,060,175.56 bit/J**. The catfish-surface harness and
     **everything built on it — FEASFRONT, CFSCREEN, the anchor-ablation and beam-power-accounting runs, the
     EEGAP bridge, the pooled-EE rulings** — ran here.
   - **These two groups are NOT-COMPARABLE to each other.** In the tables the host column reads
     `local, unpinned e07f3e1e…` / `L-unpinned` vs `sat, pinned 427e6a91…` / `S-frozen` (sat before the pin;
     same content as the pin) / `S-2026-08-25` (the frozen run's own training logs; pinned content).
2. **Same seeds ≠ same episodes (CFSCREEN; `V025-CONTROLLER-RECORD-CATFISH-SCREENS-2026-09-11.md:47-52`).**
   On the MODQN harness only **episode 0** is paired across cells; for episodes ≥ 1 the start epoch comes from
   `env_rng` and the number of fading draws depends on actions, so t=0 SNR/θ differ in 100 % of rows. Every
   between-arm difference in FEASFRONT, CATFISHSURFACE, POWERACCT, the anchor ablation and B0 is therefore an
   **unpaired** comparison (unpaired per-episode sems are valid; **any paired statistic across cells is
   INVALID-AS-PAIRED** — rows CS-33 and B0-12). Within-run re-pricings (POWERACCT's three accountings of one
   recorded run; same-state rule queries such as SC-09) *are* paired. The P6-scenario harness used on sat
   (MODQN-COLLAPSE, MODQNZ, zclose) re-seeds each scenario; whether its cells are paired was not checked.
3. **Shared env vs fresh env (B0 R.5).** The original catfish-surface driver ran every arm on one
   environment; `_age_rng` carries across episodes, so only the first arm (RANDOM) ran at age-stream
   positions 0–23. Hence **two "trained EE" values circulate**: 93,137,893.02 (shared env, arm-order
   affected; CS-02) and **93,110,907.97** (fresh env; CS-16 = FF-04 = BP-01 = EM bridge). Cite with the round.
4. **Physics / harness vocabulary.** `MODQN-harness` = the `src/mcrl/env` step environment the frozen
   checkpoint was trained in (dt 30.08 s, 100 users, 10 steps/episode, 28 user-relative actions, per-beam
   power = **max over served users**, consumed = PA supply + 0.338 W/beam + 0.200 W/active sat, no cap, no
   rate target). `V025-a-r0-panel` = the V0.25 successor engine, cell `a-r0`, interruption off, full-buffer,
   **time-division (TDM) per-beam accounting**, global `(norad_id, cell_id)` options with an explicit capped
   active set; panels: **12-anchor dev** (`V025_PROBE/world/1` steps 0–3 × 3 carriers; effective n = 4
   steps), **93-anchor**, **22 TRAIN**, **20-anchor scoring** (all 20 are training anchors — in-sample,
   erratum 21). `V025 rate-target probe panel` = the 20-/8-anchor and 30-date panels of the morning of
   2026-09-10 (sealed vs corrected provisioning). `V0.23` = the predecessor engine (C3-S, S0).
   `SIBLING-familyb-JULY` / `SIBLING-post-2026-08-05` = the old project (§2). The two harnesses share no
   action or observation space (erratum 23 §4; SV-BR-01).
5. **Estimand vocabulary.** `pooled ratio-of-sums` = Σ bits / Σ joules, divided once (the declared EE);
   `mean-of-ratios` = mean over steps/episodes of per-step EE (e.g. `r1_mean`); `per-user mean` = the
   sibling's `argmax_EE`; `trained calibrated scalar` = Σ ω_j r_j / c_j with ω (0.5, 0.3, 0.2), c
   (2029238.43, 1, 6) — **tree-dependent** (the D-2 per-step outage floor `c00aca3e` shifts it by
   −0.005…−0.016); `uncalibrated 0.5·r1` = the frozen run's logged `scalar_reward` (r2, r3 move it by 1e-6);
   counts (beams, slots, users) are never EEs — **G-3 `active_beam_count` is distinct relative slots out of
   28, not physical beams** (7.47 vs 67.90 physical for the same checkpoint).

Other conditions every MODQN-harness row must state: tree flags (bootstrap `eq16-per-head-max` vs
`shared-continuation` — commit `5219995a` had it unconditional, `57fb40b4` made it a flag defaulting to
eq. 16; D-2 floor off / −100 / per-step; D-3; cap flag), checkpoint (frozen 9,000-ep `e6b063ef…` vs a
500-ep retrain at training ε 0.753), and whether the number is a greedy evaluation or a training-time log.

---
