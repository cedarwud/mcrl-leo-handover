# Addendum A to the Stage 1b contract — pre-declared OPS-3 variant arms

Date frozen: 2026-09-02, before any Stage 1b outcome is opened.
Parent contract: V08-C2-STAGE1B-ORACLE-SCREEN-CONTRACT-2026-09-02.md
(sha256 2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545).
Status: `PRE_OUTCOME_ADDENDUM`

## Why

Three independent design routes were produced today. `docs/MULTI-CATFISH-C2-OPS3-FRESH-REVIEW-2026-09-02.md`
(Codex/Sol "Projected-Persistence Catfish") converges on the same deterministic
hold-horizon segment target as H-A, differing in three declared details. The
parallel-design adjudication (`docs/MULTI-CATFISH-C2-PARALLEL-DESIGN-ADJUDICATION-2026-09-02.md`)
requires routes to be compared on identical gates. Evaluating both oracle
surfaces on the same matched worlds, lineages and keyed field is the cleanest
such comparison. This addendum pre-declares the second surface so that neither
route can change its success definition after seeing a result.

## OPS-3 variant as read by this controller (owners should verify the reading)

With H_t = min(3, 9 - t) for a 10-step episode (Z = 0 when H_t = 0), and the
same frozen background, median channel, p_a(h), R_a(h), and marginal power
P_a(h) as the parent contract's H-A:

  chi_a(h) = 1[G_a(h) > 0] * 1[p_a(h) <= 1.65 W] * 1[projected elevation of s_a toward u at t+h > 0 deg]
  Z_a      = (1/H_t) * sum_{h=1..H_t} [ chi_a(h) * dt * (R_a(h) - lambda0 * P_a(h)) - (1 - chi_a(h)) * kappa ]
  Q2*_OPS3(s,a) = Z_a / kappa

The reference-row subtraction Z_a - Z_{a^M} in OPS-3 is a per-state constant and
does not change any argmax; it is therefore omitted from the deployed oracle
surface and reported only as a diagnostic.

Differences from H-A, all declared here: (1) 1/H_t averaging instead of a sum
over offsets; (2) an explicit -kappa term per projected-outage offset instead of
censoring to zero; (3) offsets beyond the episode end are truncated; (4) an
above-horizon indicator inside chi. No other difference is permitted.

## Additional arms

  O2 = Q2*_OPS3, O12 = Q1 + Q2*_OPS3, O23 = Q2*_OPS3 + Q3, O123 = Q1 + Q2*_OPS3 + Q3

evaluated on the identical six worlds, three lineages, and keyed field as the
parent contract (P1, P3, P13 and MAIN are shared).

## Pre-declared reading

- Each route is judged by the parent contract's directions D-C2, D-C3, D-C1 and
  service guard S, substituting O-arms for P-arms for OPS-3.
- If exactly one route passes `PASS_STAGE1B`, that route proceeds; the other
  stops as formulated.
- If both pass, selection follows the adjudication document's order: stronger
  and more stable three-marginal directions (pooled and per lineage), then
  coverage, simplicity, compute. The controller records the choice with the
  numbers; no hybrid is formed.
- If neither passes, both stop; no third variant, rescaling, horizon change or
  outage-term change may be introduced against these outcomes.

Projected extra cost: 4 arms x 3 lineages x 6 worlds = 72 ten-step episodes.
