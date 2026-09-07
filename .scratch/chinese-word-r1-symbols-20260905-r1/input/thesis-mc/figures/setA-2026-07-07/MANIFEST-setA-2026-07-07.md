# Set A result figures — MANIFEST (2026-07-07)

**Set A** = the 4-arm honest CDRL-style line set for the framework-wins narrative.
Arms (4): **B0_MODQN** (plain baseline), **A1_Auction_Only** (MCCRL w/o catfish),
**A2_MCCRL** (proposed), **AF** (coordinated, no-learning). Plain lines, **NO CI band**
(USER figure standard 2026-07-07 — RAW+CI stay in the source `*_raw.csv`, the PNG is clean).
Symbol = **v_max** (`$v_{\max}$`), not the code id `k_cap`.

Renderer: `scratch/render_2set_ee.py <raw_csv> <arms> <out_stem> <metric>`
(eval-free re-plot of measured means — no fabrication, no smoothing, no deleted points).
8 figures live in `scratch/final_figures/cdrl_style/axis_*/setA_*` and are mirrored to
`/mnt/d/origin-paper-figures/setA-2026-07-07/` (USER view) + this tracked dir.

## Honest RED LINES (apply to every caption; from `CURRENT-STATE.md` + G6-confirmed)
- **(a) A2 ≈ A1** across all axes → catfish is a **subsumed component**, NOT the win driver.
- **(b) On EE, A1/A2 track AF; AF is the matched-coverage EE ceiling.** Learning leads AF only
  at tight capacity (low v_max); at high capacity AF overtakes. Not an EE win over AF.
- **(c) The deployable win is HANDOVER:** AF churns beams hard (handover rate up to ~0.35/user/step
  on power/users, ~0.92 at high v_max); the learned arms hold ~0.09–0.10 at the **same coverage/EE**
  → 3–10× fewer handovers. **The "10×" is the HIGH-`v_max` end only** (≈0.92/0.10); on the power/users
  axes it is ≈0.35/0.10 ≈ **3.5×**. Never quote the top of the range unqualified.
  > ⚠ **RESET-ARTIFACT DISCLOSURE (2026-07-09, `grounded`).** `env.reset` zeroes `_assignments_slot`
  > (`family_b_step.py:347`) and `_handover_penalty` has no first-step guard (`:803`) ⟹ **step 1 counts
  > initial acquisition as a handover**, and the inflation is **policy-dependent** (step-1 share: AF 24.7 % ·
  > argmax 13.5 % · RSS_max 71.8 % · round_robin 100 % · myopic-`J_w` 99.3 %). Excluding step 1 removes a
  > roughly common offset and **widens** the learned-vs-AF gap ⟹ the quoted ratios are **conservative**.
  > Figures NOT regenerated: correcting in the direction that flatters our own arms is the documented MR trap.
  > A step-1-excluded ratio requires a data-blind prereg + cross-model G6 first.
- **(d) B0 handover is also low (~0.10) — but that is COLLAPSE, not skill.** Read every handover
  panel WITH the coverage/EE panels (B0 EE sits far below A1/A2/AF everywhere).

## Figures (8) — provenance + per-fig note

| # | file | metric×axis | source raw CSV | mode / pts / x-range |
|---|---|---|---|---|
| 1 | `setA_ee_vs_bandwidth` | EE × bandwidth | `axis_bandwidth_hz/cdrl_bandwidth_hz_nominal_dense-2026-07-01_raw.csv` | nominal-transfer / 12 / 5e7–1e9 Hz |
| 2 | `setA_ee_vs_kcap_af` | EE × v_max | `axis_k_cap/cdrl_k_cap_matched_dense-2026-07-01_raw.csv` | **matched retrain per-k** / 13 / 3–15 |
| 3 | `setA_ho_vs_kcap` | handover × v_max | `axis_k_cap/cdrl_k_cap_nominal_nrt-2026-07-03_raw.csv` | **nominal-transfer** / 5 / {3,5,8,12,15} |
| 4 | `setA_ee_vs_noise` | EE × noise PSD | `axis_noise_psd_dbm_hz/cdrl_noise_psd_dbm_hz_nominal_dense-2026-07-01_raw.csv` | nominal-transfer / 12 / −184…−140 dBm/Hz |
| 5 | `setA_ee_vs_users_af` | EE × users | `axis_num_users/cdrl_num_users_nominal_dense-2026-07-01_raw.csv` | nominal-transfer / 12 / 50–200 |
| 6 | `setA_ho_vs_users` | handover × users | `axis_num_users/cdrl_num_users_nominal_dense-ee-2026-07-03_raw.csv` | nominal-transfer / 12 / 40–200 |
| 7 | `setA_ee_vs_power` | EE × power | `axis_p_base_w/cdrl_p_base_w_nominal_nrt-2026-07-03_raw.csv` | nominal-transfer / 5 / 0.1–2.0 W |
| 8 | `setA_ho_vs_power` | handover × power | `axis_p_base_w/cdrl_p_base_w_nominal_nrt-2026-07-03_raw.csv` | nominal-transfer / 5 / 0.1–2.0 W |

## QA notes / honesty caveats (binding — read before landing any of these in ch5)

1. **v_max protocol mismatch (fig 2 vs fig 3).** EE-vs-v_max is the **13-pt matched-retrain**
   sweep (fairest, per-k retrained B0/A1/A2). Handover-vs-v_max is the **5-pt nominal-transfer**
   sweep — the matched-kcap CSV carries no `ho_rate`, so the HO panel is forced onto the
   transfer policies. Disclose if the two v_max panels appear together; do not imply one protocol.
2. **users EE vs HO come from two different nominal sweeps.** EE-vs-users = `dense-2026-07-01`
   (U 50–200); HO-vs-users = `dense-ee-2026-07-03` (U 40–200). Both are nominal-transfer evals of
   the same nominal policies; grids differ slightly. (A perfectly-matched EE+HO users pair could be
   regenerated from `dense-ee-2026-07-03` alone — USER call; not done, to avoid re-touching the
   already-approved EE-vs-users fig.)
3. **B0 EE undefined at p_base < 0.5 W (fig 7).** `B0_MODQN_ee_mean` is empty at 0.1/0.25 W in the
   raw CSV (collapse → no served users → EE not computable), so the B0 line starts at 0.5 W. This is a
   genuine data gap, NOT a deleted losing point. Note it in the caption if the fig is used.
4. **bandwidth tick fix (fig 1).** The renderer previously forced a tick at every swept point;
   on the dense low-bandwidth cluster the labels collided. `render_2set_ee.py` now falls back to auto
   ticks when the tightest point-gap < 6 % of the axis range (only the bandwidth axis trips this; the
   other 7 figs' ticks are unchanged). Re-verified clean.
5. **OOD high-load crossover is NOT in this set** (w503020 @ p_base ≥ 1.0 beating AF on EE) — that is
   un-matched-retrain + un-G6'd; excluded from thesis figures per USER.

## Suggested thesis-vs-slides split (PROPOSAL — pending USER confirm; does not edit ch5)
- **Main text (ch5):** #2 `ee_vs_kcap` + #8 `ho_vs_power` (the two headline axes: EE-ceiling story + deployable handover win).
- **Secondary / robustness (ch5 or appendix):** #1 `ee_vs_bandwidth`, #4 `ee_vs_noise` (generalization envelope).
- **Slides:** #3 `ho_vs_kcap` (AF→0.92 is the most vivid handover contrast) + #5/#6 users pair.
