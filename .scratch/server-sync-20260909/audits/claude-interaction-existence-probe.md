# Interaction-existence probe across the pre-declared regimes (Claude Opus 5, headless) — PROBE_NOT_CLAIM

**The one question:** in which of the pre-declared regimes, if any, does a *positive* interaction term exist at all? Answer it in under two hours, at oracle level, with no learning.

Why this framing: around the carrier anchor a⁰ the interaction residual is necessarily mostly negative (users collide on the same good beams). Re-anchored at a certified iterated unilateral optimum u, every single-user move satisfies dᵢ^u ≤ 0 by construction, so **any strictly improving joint move from u must have Ψ_A^u > 0**. The existence of such moves is therefore the cleanest possible test of whether a coordination layer can have any value in this physics.

Workspace: `/home/sat/mcrl-v025-probe-ws` (the launcher copies the stage-4d engine snapshot plus the fixed provider — the same base the pilot uses). Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Quarantined development worlds only (`V025_PROBE/world/{1,2}`). Budget ≤ 4 core-hours, ≤ 8 concurrent. Label every artefact `PROBE_NOT_CLAIM`.

Regimes to test, all pre-declared (see `V025-CONTINGENCY-LADDER-PREOUTCOME-2026-09-08.md` and its amendment 1, copied into the workspace):
| tag | change from the primary |
|---|---|
| `a-r0` | none (primary: r* = 50 Mbit/s, circuit 0.338 W/chain, TDM) |
| `R3` | circuit power 1.0 W per active chain — **the regime where consolidation should dominate and joint evacuations should pay** |
| `R4` | circuit power 0.1 W per active chain — the opposite extreme (balancing should dominate) |
| `R1` | rate target 100 Mbit/s |
| `R7` | rate target 25 Mbit/s |
| `R6` | fixed-SINR architecture `a-γ0` |

For each regime, on 10 anchors per world (20 anchors total), do exactly this:
1. Compute the certified iterated exact unilateral optimum `u` (same evaluator, guards and objective as the coordinator; record whether termination was certified or budget-limited).
2. Enumerate the bounded joint neighbourhood **around u**: all pairwise moves among the top-10 users by |dᵢ^u|, per-beam evacuations from u, and the S0 proposals. For every candidate compute dᵢ^u for its members and Ψ_A^u = F(a_A) − F(u) − Σᵢ dᵢ^u.
3. Report per regime: the **fraction of anchors with at least one strictly improving joint move from u**; the distribution of Ψ_A^u for the best candidate at each anchor (min, median, max, and the share > 0); the size distribution of the improving coalitions; the realised pooled EE of the best joint profile versus u versus the carrier baseline; and for contrast the same statistics anchored at a⁰.
4. Also report the cheap descriptive context per regime: mean users per active beam, cap-hit share, ACM mode distribution, and how many beams could be evacuated entirely.

Write `V025-INTERACTION-EXISTENCE-PROBE-2026-09-09.md`: one table with a row per regime and the columns above, then a short section per regime saying plainly whether positive interaction exists there and how large it is. **Draw no scientific conclusion and do not rank regimes as recommendations** — report the numbers. Note in the header that this runs on the engine snapshot that still has the genie-ACM defect (credited mode chosen from the realised SINR), so absolute EE is optimistic; the interaction-sign question is comparative and is the purpose here. Include a `DEFECTS` section for anything you hit.
