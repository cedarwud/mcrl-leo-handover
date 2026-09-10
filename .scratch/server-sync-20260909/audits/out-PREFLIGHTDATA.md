The report is written to `/home/sat/mcrl-v025-coverage-ws/PREFLIGHT-DATA-CENSUS-2026-09-10.md` (43 KB) and raw statistics to `.scratch/preflight-data/slot-census.json` (449 KB). The terminal truncated the print; it's on disk in full.

## Headline

**Every one of the 176,223 rows a C1/C2/C3 training run would consume was built by the fallback path; two of the sixteen slots are exactly constant so the design matrix has rank 14 and infinite condition number; the C1 and C2 targets are bounded `tanh` surrogates of a single gain ratio rather than the declared difference surplus and persistence forecast — and twelve of the thirteen defects would have been entirely silent in training.**

## Three corrections to the brief's premises, all toward more defect

1. **The fallback is not taken sometimes — it is the only path, unconditionally.** `PILOT_PRIMITIVE_SOURCE_FALLBACK = True` is a module constant and the first statement of the only entry point. Proved from the shipped bytes, not inferred: each path stamps a distinct `forecast_method_sha256`, and all 176,223 rows carry the fallback's. No occupancy breakdown is meaningful because there is no data predicate.
2. **There are two constant slots, not one.** `missing_incumbent` is also exactly 0.0 on all 176,223 rows — and on all 720 C3 member vectors, and it is the one constant slot of C2's 22 as well. It was not on the known-defect list.
3. **`off_axis_angle = 0.0` is hard-coded on *both* paths.** The mechanical diff confirms it: of the 16 slots, exactly 4 differ between paths, and both dead slots differ on zero rows. Repairing the fallback repairs neither geometry defect.

## The numbers that matter most

- **C1 target fidelity**: fallback is bounded to ±1κ; the declared surplus reaches +8.30κ and +11.40κ at the two diffed anchors. Pearson r = **0.486** and **0.035**. At the second anchor the surrogate carries essentially no linear information about what C1 is supposed to predict.
- **C2 target fidelity**: sign agreement **37.7%** — the surrogate disagrees about which action is better on ~3 rows in 5. `c2_persistence_forecast` is never called.
- **Conditioning**: `nominal_required_power_over_cap` is exactly `1e6` on 10.2143% of rows (every null-action row, no others). Excluding them, the learner-facing condition number falls from 9.14e6 to **77.7**.
- **Coalition identity differs at 2 of 2 anchors**, once with disjoint member sets; ψ = −3.036 vs +0.0008, and +36.015 vs +0.00002.
- **`|r| ≥ 0.98` is the wrong screen**: no pair reaches it, yet `beam_active_before_focal == 1[occupancy > 0]` and `previous_beam_active_for_action == 1[previous_load > 0]` are *exact* identities on every row. Effective input dimension is 12, not 16.

## Part C, in one line

Of thirteen defects, **one** (the `1e6` sentinel) might have surfaced in a training curve, and then only as unexplained instability. **Twelve are silent, and three make the loss look *better* than the declared targets would** — a bounded surrogate of one gain ratio is strictly easier to fit, and 31% of the C2 target is a constant floor.

## Stated limits

The both-ways diff covers **2 of 180 anchors**: the normal path costs 433–633 s per anchor against the fallback's 4.8–21 s (132× at anchor 0), so the full grid is 24–31 hours single-threaded. I did not substitute a proxy — the full field table is labelled as a code read, every measured count is per-anchor and not extrapolated, and two anchors establish that each divergence *can* occur, not its corpus-wide rate. Also explicitly unmeasured: the rekey-active Φ branch (all 30 anchors carry dense arrays, so `_rekeyed_users` is empty and **defect B4 is latent, not active** — `c1_phi_difference` is bit-identical on both paths), and whether the normal path's own targets are correct.

One deviation worth flagging: to build a normal-path row for the same anchor, the diagnostic process sets the fallback flag `False` on its own imported module object. The file on disk stayed byte-identical, and this is the only way the requested diff can exist, since the flag *is* the dispatch condition. Both protected trees verified untouched.
