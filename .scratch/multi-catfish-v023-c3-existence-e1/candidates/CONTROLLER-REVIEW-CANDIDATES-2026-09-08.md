# Controller review of the three pre-outcome candidate contracts (2026-09-08 00:30 UTC) — UNSEALED, NO_LAUNCH

Drafted by astra (gpt-6-astra high, read-only) BEFORE any E1 outcome exists; verbatim copies of the handoff-directory drafts.
All three are ACCEPTED as pre-outcome declarations. None is sealed; none is implemented; none may run unless (a) E1 seals
and completes, (b) E1's certified cell authorises the candidate's family per E1 §3, (c) the candidate body is sealed and its
implementation reviewed, (d) separate launch authority is written. Nothing here changes a formula, threshold, seed, horizon,
λ, κ or acceptance rule of any draft.

| id | name | family (E1 cells that admit it) | new simulation needed for its kill screen |
|---|---|---|---|
| C-A | OPS-3 action-set coalition value, exact Shapley allocation, minus declared C1/C2 overlap | joint catalog: (H,H) or (CLOSED,H) | yes — subset profiles (≤ 2^m per proposal) × 3 OPS-3 offsets |
| C-B | adaptive trajectory surplus residual, H = 3 (branch vs BASE-continuation) | unilateral: (H,H) or (H,CLOSED) | yes — cloned 3-interval branches per legal unilateral change |
| C-C | exact-primary-tie network-energy selector (ε = 0, ≤ 1 user per anchor) | unilateral: (H,H) or (H,CLOSED) | possibly none — if the E1 tape stores q (float32 Q1+Q2), masks, physical keys and per-profile energy, the C-C decision at steps 0–1 is a pure function of the E1 tape |

## Interpretations flagged by the drafts — controller decision: ACCEPT ALL, with one recorded caveat
- C-A: ≥ 1 three-member proposal required for higher-order exposure; catalogue built from detached BASE action-key occupancy with
  `INTERFACE_CATALOG_MISMATCH` blocking support; OPS-3 extended to complete joint profiles with H_p = min(3, T−1−t); overlap
  d_{12,u} as defined; exact Shapley (no sampling); pooled ratio-of-sums without votes; 16 worker-hour cap.
- C-B: three complete intervals, no discount; comparator = BASE-continuation trajectory; entire initial C2 delta subtracted once;
  F1's single realised field; pooled 72-interval endpoint; 4–8 worker-hour provisional budget.
  **Caveat (recorded, not a change):** the mapping "C-B requires `E1_UNILATERAL_HEADROOM`" is conservative. U₁ bounds one
  interval; a three-interval surplus could exist with a first-interval loss, so `E1_UNILATERAL_CLOSED` closes C-B *under this
  contract* without settling the trajectory question. A separate three-interval existence test would need its own prospective
  contract; it is not declared now and E1 is not widened (cost ≈ 3× and an overlapping-window estimand).
- C-C: focal user = lowest native index with ≥ 2 physically distinct exact maximisers; non-focal actions reserved at BASE before
  the focal decision; target = −(interval network energy) in joules, no κ; `NO_EXACT_TIE_EXPOSURE` is a recorded NO_SUPPORT reason.

## Order of work if E1 authorises a family
unilateral cell → C-C first (cheapest; may need no new simulation), then C-B; joint cell → C-A. One candidate at a time per
family; a NO_SUPPORT closes that candidate permanently; no residual ranking across candidates.

## Follow-up for the E1 implementation (engineering, before E1 seal)
Confirm the E1 tape schema records per anchor: float32 Q1+Q2 surface per user, native masks, action→physical-key table,
BASE vector, and per unilateral profile (user, action, B, E, served count, F0 checks). If absent, add it in the E1 core
before sealing — it is provenance, not a scientific choice, and it lets C-C run without re-simulation.
