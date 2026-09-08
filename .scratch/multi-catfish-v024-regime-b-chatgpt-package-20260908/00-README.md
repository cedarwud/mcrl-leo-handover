# Multi-Catfish — Track B (V024 regime-B) outside-review package, 2026-09-08

Context: Track A (frozen physics) is the paper's primary result: two Catfish (C1, C2) plus a negative result for C3 after 18 attempts.
E1 (file 04) showed that even in the frozen physics there is ≈ 2 % exact-oracle EE headroom (U₁ +1.99 %, J₁ +2.22 %), so the failure
is in converting headroom through deployable information and the independent per-user additive argmax, not in the absence of headroom.
Track B is a SEPARATE, pre-registered study: a constructed "coordination-relevant" regime (finite per-user traffic demand, grid
G0 = ∞ control / G1 = 200 / G2 = 50 / G3 = 10 Mbit/s per user), a regime-map probe (exact ceilings), an oracle marginal probe, then a
full campaign with arms M0 (retrained MODQN), M12 (C1+C2), M123 (additive three heads), S0/S3 (set-level coordinator), and DROP arms.
Owner's criterion: C1, C2 and C3 EACH improve pooled EE (their gains may shrink). Integrity rules: everything declared before outcomes,
all grid points reported, no tuning against results, regime A's negative result stays, TEST never opened.
Files: 01 astra design memo · 02 Gemini physics proposal · 03 protocol · 04 E1 result · 05 E1 sealed contract · 06/07 global-view
examinations · 08 regime-A chronology (18 attempts) · 09–11 physics code excerpts (constants, energy/activation model, power/rate).
