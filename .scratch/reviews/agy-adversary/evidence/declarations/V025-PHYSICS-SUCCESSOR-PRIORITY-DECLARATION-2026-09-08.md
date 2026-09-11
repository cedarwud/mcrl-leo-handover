# V025 physics successor — priority declaration (controller, sealed before any successor outcome; 2026-09-08, server clock ≈ 13:50 UTC)

## Owner's requirements (verbatim intent, 2026-09-08 ≈ 13:48 UTC)
1. The off-axis / elevation angle must genuinely influence transmit power and energy efficiency.
2. C1, C2 and C3 must each genuinely raise pooled EE; C3 is the current blocker.
3. Both successor architectures are to be developed and tested in parallel; they are not in conflict.

## Declaration
- **Primary system model: architecture (a) `V025-ANGLE-TPC-TDM-ACM`** — memoryless angle-aware power control (per 30.08 s step, per simultaneous slot configuration: p_u = min(1.65 W, γ*·(N + Î_u)/ĥ_u), ĥ_u = G^T(θ_u)·L_u·G^R, γ* = the 8PSK 2/3 threshold of EN 302 307-1 Table 13 with the 1.7 dB margin and roll-off 0.20 correction, i.e. 7.528 dB nominal; equal-airtime TDM; coupled nominal powers solved from a history-independent initialisation with frozen tolerance and residual certification; no segment memory). Chosen because it is the only candidate that satisfies requirement 1 by construction. This choice is made **before** any successor outcome and is independent of C3's result.
- **Declared reference model: architecture (b) `V025-FIXED-EIRP-ACM`** — fixed 1.65 W RF per active beam with ACM (astra round-3 §2). Reported in every table beside (a).
- **Architectural sensitivity: (a′)** — same target with equal FDM sub-bands (per-user RF ceiling 1.65/n_b, beam RF = Σ p_u, sub-band-consistent noise/PSD/overlap).
- **Priority order of the 18-cell physics-settings matrix (fixed now):** `a0 > b0 > a′0 > aS > bS > a′S > aH > bH > a′H > aSH > bSH > a′SH > aT > bT > a′T`; U cells (uncapped Shannon) are diagnostic only and ineligible as primary. Treatments per astra round 3 §4 (0 = 47-subinterval integration, standby 0, interruption off, ACM cap + margin; T = snapshot; S = standby f = 1/12; H = conditional 62/142 ms useful-time interruption; SH = both; U = uncapped).
- **Everything else** follows astra round 3 §2 (items 1, 3, 5–31 unchanged: ACM table, margin, served ⇔ SINR ≥ −1.4418 dB after joint resolution, energy accounting with P_idle = 0 primary, clock/integration, geometry/10° visibility, actions, observable information, calibration λ = η_ref and κ on a nominal-greedy reference, reward core R = B − η_ref·E, Φ as QoS, C1 full-network difference surplus, C2 feature migration and forecast schema, C3 as set-level consolidation coordinator, learning contract, history seal) and §3 (known-answer suite, extended for (a) with coupled-power convergence/saturation and slot-consistent interference fixtures).
- **Service definition:** PHY decodability with QoS co-primaries (astra §2 item 10, 23). A guaranteed-rate service endpoint is not declared; if the owner later requires one it is a separate, additional endpoint.

## Rules that make "whichever helps C3" honest
- The primary is (a) by requirement 1, not by C3's outcome. C3's marginal is measured under every cell and reported as a regime map ("where does coordination change EE"). A positive C3 under (b) with a non-positive C3 under (a) is a reported finding, not grounds to swap the primary after the fact.
- Training admission (astra §4): retained factors need positive oracle marginals beyond certified numerical error and acceptable QoS; C3 additionally needs genuine joint headroom (a multi-user witness beating the unilateral alternative) and a deployable S0 gain ≥ the pre-existing 1 % practical threshold. If C3's set-level oracle marginal is ≤ 0 in every completed, physically defensible cell, C3 training/screens/confirmation close and a bounded negative is reported; C1/C2 proceed under their own gates.
- No target, standby, margin, service or priority change after outcomes are opened. Any defect found later is repaired and re-run, never demoted by outcome.

## Ordering
1. Codex implements one versioned radiation/rate/energy engine with the three architectures behind a declared switch, the known-answer suite, and the matrix runner reusing Track B's shared-tape lever-matrix runner. Nothing runs before the KAT suite passes.
2. Rehearsal to measure q; overnight matrix (≤ 160 core-hours); every cell reported.
3. Stage A regenerated sources + training (FULL2, DROP_C1, DROP_C2, ALL_NEUTRAL; three initialisations) only for factors admitted by the probes; stage C ladder; C3-S screens and confirmatory on fresh worlds.
4. Stage A real launch stays HOLD until step 2 admits the factors; `PHYSICS-GO.txt` names `V025-ANGLE-TPC-TDM-ACM`.

Seal: this file's sha256 is recorded in `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.sha256`; the astra round-3 consolidation it binds is `ADJUDICATION-PHYSICS-EE-ROUND3-CONSOLIDATION-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md` (sha256 recorded in the same sidecar).
