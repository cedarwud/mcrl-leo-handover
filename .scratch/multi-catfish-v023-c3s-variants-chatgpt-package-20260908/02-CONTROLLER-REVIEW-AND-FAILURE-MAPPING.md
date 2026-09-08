# Controller review — C3-S variant matrix kill-screen contract (2026-09-08 10:45 UTC) — UNSEALED
Draft: `V023-C3S-VARIANT-MATRIX-KILL-SCREEN-CONTRACT-2026-09-08.md` (astra, read-only). ACCEPTED as the pre-outcome declaration, pending
(i) the nine-arm runner landing + one implementation review, (ii) outside round-4 design evaluation (ChatGPT Q&A + Deep Research) — admissible
amendments only BEFORE sealing, (iii) preflight binding. Lever values fixed by the draft and accepted as declared: V-J evacuation-only;
V-U unilateral-only lite; V-M margin m_t = B̂_t(b_t)/1000 (0.1 % of BASE's nominal bits at that decision); V-C cadence t ≡ 0 (mod 3), BASE
otherwise; V-H hysteresis lock 3 steps after a coordinator override that differs from both b_t and the previous committed association;
V-P persistence penalty κ·Σ_u(1 − χ̂_u) with the OPS-3 median/no-fading projection over H = min(3, T−1−t); V-L2 one projected BASE interval
added to the objective. Arms: BASE, lite (reference), seven variants = nine trajectories per unit; same panel/kill rule as the sealed v1
screen; progression among SUPPORTers = lowest mean total decision latency over 360 decisions, ties by the declared order; any INVALID_RUN/
INCOMPLETE voids the matrix's progression; multiplicity disclosed (nine arms vs one BASE, four world clusters; development screen only).
Failure-mechanism grounding (owner requirement): each lever targets one documented mechanism — S0-U/S0-J decomposition (V-J, V-U); MONE
28/60 joint reversals + R7 −0.049 % (V-M); accumulated handover/tracking cost and oscillation named by the global views and round-3 red team
(V-C, V-H); V0.14 coordination/support events and OPS-3 pricing (V-P); PNFE/C-B one-step myopia (V-L2).
Execution order: after the v1 screen's 12 units finish (server capacity); estimated 1.5–2 h on 12 workers.
