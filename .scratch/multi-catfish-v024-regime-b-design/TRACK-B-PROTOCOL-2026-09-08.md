# Track B protocol — owner's goal and the fast-iteration loop (controller, 2026-09-08 06:20 UTC)

Owner's goal (verbatim intent, 2026-09-08 06:15 UTC): after the design, iterate FAST to test whether the regime change helps C3 and what it
does to C1/C2; the end goal is that C1, C2 and C3 EACH improve pooled EE (C1/C2 gains may shrink); the point is three positive
contributions, not "the sum of three is best".

Binding design authority: `V024-REGIME-B-DESIGN-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md` (astra ultra, pre-outcome) + the Gemini physics
proposal (`REGIME-B-PHYSICS-GEMINI-3.8-FLASH-HIGH-2026-09-08.md`, independent; converges on finite traffic demand as the primary axis).
Minimal physics change: finite per-user demand / delivered-goodput accounting (B_u = min(Δt·R_u, Δt·d_u)); grid G0 = ∞ (control),
G1 = 200 Mbit/s, G2 = 50 Mbit/s, G3 = 10 Mbit/s; all four run and reported; selection = first qualifying point in G1→G2→G3 order.

Fast-iteration loop (each iteration is a declared, sealed unit; no tuning inside an iteration):
1. Regime-map probe per grid point (E1 exact machinery under the physics override; reference carriers = three fixed rules; worlds
   `V024_REGIME_B/world/{1..4}`): U₁, J₁, interaction surplus, per-world direction → coordination-relevant test (memo §4 thresholds).
2. Oracle marginal probe per qualifying point (before any training): exact one-step targets substituted for learners, arms
   {BASE-carrier, +C1, +C1+C2, +C1+C2+C3(additive), set-decoder with privileged oracle}, plus DROP arms {C2+C3, C1+C3, C1+C2}; pooled
   EE and service per arm → the three oracle marginals (C1, C2, C3). A point whose oracle marginals are not all positive does not
   proceed to training (reported, not hidden).
3. Full campaign on the selected point (memo §5): M0 MODQN-B, M12 FULL2-B, M123 additive three-Catfish, S0/S3 set decoder, PLUS the
   per-head DROP arms (DROP_C1-B, DROP_C2-B, DROP_C3-B) so that each head's learned marginal is measured, not only C3's.
Owner's success criterion (declared now): every learned marginal (FULL vs each DROP) > 0 in pooled EE with the service and demand
guards of memo §3; the paper reports all arms relative to M0 regardless of outcome.

Separation: branch `v024/regime-b` (own checkout `/home/sat/mcrl-v024-regime-b`, own artifacts `artifacts/v024-regime-b/`), new
`PREREG-V024-REGIME-B`; nothing flows back into track A's sealed artifacts; regime A's C3 negative result stays in the paper.
