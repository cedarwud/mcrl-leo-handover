# V025 engine — controller resolutions of the stage-1 / stage-1b `CONTROLLER_DECIDE` items (2026-09-08, server clock ≈ 15:20 UTC; before any successor outcome)

Each item below is a declared choice for the successor. Where the resolution differs from what codex implemented, it is marked **CHANGE** and goes to the next engine pass; otherwise **ACCEPT** (the implemented behaviour becomes the declaration).

## Stage 1
1. **Authority ordering conflict** — ACCEPT: the sealed v1.1 amendment governs (primary a-r; order `a-r0 > a′-r0 > a-γ0 > b0 > a′-γ0`, then S/H/SH/T in `a-γ, b, a′-γ` order; U diagnostic). Launcher and admission artefacts reject the round-3 order.
2. **U placement** — ACCEPT: `a-γU, bU, a′-γU` appended, diagnostic-only, never primary-eligible.
3. **Snapshot timestamp (treatment T)** — **CHANGE**: treatment T exists to reproduce the legacy convention, and the legacy environment evaluates rates and power at the decision-time state and holds them for 30.08 s (the zero-order hold measured by register A). T therefore uses the **left endpoint** sample at t, not the terminal t + 30.08 s sample. The round-1/round-3 fixture "R(t) = t ⇒ 904.8064" was mis-specified as a terminal snapshot; the correct KAT is the round-1 one: R(t) = 2 + t over 2 s → true integral 6, left snapshot 4. Fix the KAT and the implementation in the next pass.
4. **FDM unequal-load alignment** — ACCEPT as declared: sub-bands start at the low band edge, frozen ascending user-id order, aggressor uniform PSD × exact victim/aggressor frequency overlap.
5. **Interruption mapping** — ACCEPT: 62 ms same-satellite beam change, 142 ms satellite change (both `VERIFY_SOURCE` per ADR-004:118), initial entry / re-entry logged with no inferred blackout, overlaps unioned and clipped once.
6. **Availability naming** — ACCEPT: decoding availability (PHY threshold, interruption-independent), useful availability (minus H blackout), complete-service user-step, and — distinct — `rate_target_attained`.
7. **Discontinuity ownership** — ACCEPT: the tape builder supplies left/right samples at every known event discontinuity; the integrator refuses a single ambiguous value.
8. **Nominal / realised split** — ACCEPT: controller powers solved from nominal current geometry and nominal interference only; realised fading enters received fields only.
9. **Saturated fixed point** — ACCEPT: cap-binding solutions certified by the capped-map residual are CONVERGED (rate architectures additionally flag `rate_target_infeasible`); 4096 iterations or a failed residual → INVALID, never a synthetic zero-effect outcome.
10. **Table hash representation** — ACCEPT: canonical ASCII JSON of ordered (name, efficiency, ideal Es/N0); roll-off and margin frozen separately.
11. **Inventory adapter** — ACCEPT: stage 2 generates and seals the physical (NORAD, beam-chain) manifest before actions; candidate slots never expand it.
12. **Track-B envelope** — ACCEPT: explicit `v025_setting`, `v025_geometry_samples`, `v025_inventory` context; launcher wiring in stage 2; no old tape reinterpreted.
13. **Source access (ACM table)** — RESOLVED: the controller compared all 28 frozen rows against an independent transcription of EN 302 307-1 V1.4.1 Table 13 (see the check recorded in the ledger); an official-PDF re-check remains a `VERIFY_SOURCE` note for the paper, not a blocker for development probes.

## Stage 1b
14. **20-cell treatment interpretation** — ACCEPT: S/H/SH/T/U apply to `a-γ, b, a′-γ`; `a-r` and `a′-r` carry treatment 0 only (as sealed). Additional rate-target treatment cells may be added only by a further pre-outcome amendment.
15. **Rate-target status aggregation** — ACCEPT + **CHANGE**: keep `rate_target_feasible` (nominal feasibility at every integrated boundary) and `rate_target_attained` (realised decodable bits ≥ r* per user-step); additionally persist the per-boundary attainment series in the receipts for QoS reporting (cheap; no decision use).
16. **Lowest-mode rounding** — ACCEPT: conservative max convention (Γ_r(1) must clear both the derived QPSK 1/4 threshold and the frozen rounded `served_PHY` floor).
17. **Estimate charging** — ACCEPT: the simulator-inert estimate is planning only; the stage-2 rehearsal replaces it before any launch decision.
18. **Stage-2 price binding** — ACCEPT (mandatory in stage 2): every C1/C2/C3 generator and endpoint consumer passes through the explicit λ/η/κ assertion; a test fails if any producer can fall back to a default.
19. **Synthetic target provenance** — ACCEPT: r* = 50 Mbit/s is a synthetic operating point (`VERIFY_SOURCE`); no demand or hardware claim.

## Carry-over for the next engine pass (after stage 2)
- Item 3 (T = left endpoint; fix KAT) and item 15 (per-boundary attainment series).
- Channel defects from register B (shadow at actual elevation; S.465 θ_min branch in the receive pattern and interference) and the time-base items from register A (tape alignment; event ledger keyed by physical identity) — already in the stage-2 prompt; verify they landed.
