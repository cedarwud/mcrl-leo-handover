# V025 priority declaration — v1.3 erratum (controller, sealed before any successor outcome; 2026-09-08, server clock ≈ 16:30 UTC)

v1.0 (sha e45f2f02…), v1.1 (sha 6851d04b…) and v1.2 (sha cd1922fb…) are preserved unchanged. This erratum corrects one arithmetic statement in v1.2 §1 and changes no design, order, constant or claim.

## Erratum
v1.2 §1 says "Total: 28 primary-eligible cells + diagnostic U cells". The explicit list in the same paragraph governs and yields **25 primary-eligible settings** (5 architecture baselines `a-r0, a′-r0, a-γ0, b0, a′-γ0` + S, H, SH, T for each of the five = 5 + 4 × 5) plus **6 diagnostic U settings** (`U-cap`, `U-margin` for `a-γ, b, a′-γ`; v1.2 §2), i.e. **31 settings in total**. The number 28 was a counting error; the explicit enumeration, its sealed priority order and the matrix digests of engine stage 2 (31 settings) are the authority. Flagged by the stage-2 engine report before any setting was evaluated on a real world.

Seal: sha256 of this file is recorded in `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.3-ERRATUM-2026-09-08.sha256`.
