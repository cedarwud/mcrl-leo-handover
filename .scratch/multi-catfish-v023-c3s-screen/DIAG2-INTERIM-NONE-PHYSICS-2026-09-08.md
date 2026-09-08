# Decisive diagnostic set — interim read on the 12 `physics_override=none` units (controller, 2026-09-08, server clock ≈ 15:30 UTC; development diagnostic, old physics)

Pooled over the 12 units of the v1 panel (4 worlds × 3 lineages × 30 steps, 100 users):

| Arm | pooled EE vs BASE | bits | joules | served | handovers/step | lit beams | users changed vs BASE/step |
|---|---|---|---|---|---|---|---|
| BASE | — | — | — | 35 971 | 55.77 | 41.21 | 0 |
| LITE (coordinator) | **+2.922 %** | +1.551 % | −1.331 % | 35 971 | 56.65 | 40.62 | 2.04 |
| BASE_FORCED_RENEW_4 (renew every user at segment age 4, no intelligence) | +0.494 % | −0.364 % | −0.854 % | 36 000 | 55.83 | 41.24 | 0 (3 064 explicit renewals) |
| RANDOM_RENEW (one random legal renewal per decision) | −1.117 % | +0.430 % | +1.564 % | 35 961 | 57.00 | 41.85 | 0.98 |

EE advantage vs BASE by dwell phase (t mod 4 = 0…3): LITE +1.36 / +1.70 / +3.86 / +9.84 %; FORCED_RENEW +1.21 / +0.23 / 0.00 / −0.26 %; RANDOM_RENEW −0.68 / −0.81 / −1.62 / −1.37 %.

Reading (provisional until the 12 `ablate_anchor` units and the 3 NULL units merge):
- LITE replicates v1 exactly (+2.922 %) — the run is reproducible.
- Renewal per se is a small lever (+0.49 % when everyone is renewed at age 4) and random renewal is harmful (−1.12 %); LITE makes only ≈ 0.9 more handovers per step than BASE and lights ≈ 0.6 fewer beams. So LITE's gain is not "churn"; it is selective: its advantage grows with segment age while forced renewal's does not — consistent with LITE choosing which aged, high-power links to move (an intelligent exploitation of the anchored price list) plus consolidation.
- Whether that selectivity survives without the anchor is exactly what the `ablate_anchor` units measure; nothing here yet separates "genuine set-level coordination" from "informed exploitation of the anchoring artefact".
