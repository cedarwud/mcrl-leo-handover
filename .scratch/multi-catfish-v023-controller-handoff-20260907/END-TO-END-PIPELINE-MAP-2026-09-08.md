# End-to-end pipeline map — from TLE to claim (controller skeleton v0, 2026-09-08 ≈ 17:05 UTC; to be verified and extended by four fresh-context auditors, then maintained as the single source of truth)

Purpose: the last two late discoveries (segment-anchored power reset; missing real-world provider for the successor engine) were interface assumptions that were never written down as invariants. This map lists every stage, its inputs/outputs, the invariants at each handoff, which test (if any) guards them, known defects, and the owner. `?` = not yet verified by anyone; `!` = known defect; `→` = handoff.

## Stage 0 — Data and splits
- **Inputs:** Starlink TLE archive `~/demo/tle_data/starlink/tle/starlink_YYYYMMDD.tle` (373 daily files; one malformed record quarantined in 20260528). User scenario: 100 users, 30 km/h mobility, cell grid (~14 km radius), earth-fixed beams.
- **Outputs:** a world = (TLE date, world seed) → sampled users + satellite set. World seed rule: `int.from_bytes(sha256(domain).digest()[:8],'big') & ((1<<63)-1)`; lineages 2026092101–03 are training-seed lineages.
- **Invariants:** TRAIN/TEST date split is disjoint and TEST is never read (`?` where the split is defined and asserted — auditor A); nearest-in-time TLE rule and max age (`?`); 9000 episodes ↔ 166 dates, rung 100 ↔ 77 dates (independence unit = TLE date, register F).
- **Guarded by:** `?` (no single test asserts TRAIN-only across all runners).
- **Owner:** legacy `src/mcrl/env/scenario.py`, `tle.py`; successor provider `provider_legacy.py` (in progress) must inherit the same sampler.

## Stage 1 — Geometry and time base
- **Inputs:** world; step clock Δt = 30.08 s = 47 × 0.640 s; 48 boundaries per step (t + k·0.640 s, k = 0..47).
- **Outputs per boundary:** satellite ECEF (sgp4), user ECEF, elevation, slant range, off-axis angle vs the earth-fixed cell centre, 10° visibility, D2 eligibility (entry elevation ≈ 19.7/23.4/27.7° at 426/485/550 km; TTT; margin), dwell phase (step mod 4; candidate identities and cell re-key only at phase 0).
- **Invariants:** boundary alignment exactly t + k·0.640 s (`!` legacy D2 prime-seam 46-substep mismatch, register A; successor tape builder aligns 47 samples — KAT); event ledger keyed by physical (NORAD, beam-chain) identity, not slot index (`!` legacy `Segment.continues` keyed on cell_id → ≈ 9.6 % uncommanded renewals); N = 4 is a candidate-refresh period, not a residence constraint (verified by the cadence audit).
- **Guarded by:** successor time-base KAT (stage 2); provider parity KATs (pending).
- **Owner:** legacy `step.py`, `candidates.py`, `dwell.py`, `d2.py`; successor `tapes.py` + provider.

## Stage 2 — Channel
- **Inputs:** geometry per boundary; antenna patterns; fading tables.
- **Outputs:** direct gain (transmit gain at off-axis angle × FSPL × receive gain), cross-satellite interference gains (co-colour; S.465-6 receive pattern with θ_min = 2.0433° branch), shadow/scintillation draw (keyed, common random numbers per world).
- **Invariants:** nominal (no fading) vs realised (fading) separation; shadow drawn at the actual elevation (`!` legacy fixed 10°); receive-pattern floor applied (`!` legacy never applied; 2.4983° mis-recorded); Bessel series accuracy (`!` legacy 2.93e-6 worst bits error — tolerated).
- **Guarded by:** successor KATs at 1°, 2.0433°, 5° and 10° vs 60° shadow; differential audit (legacy, 270 steps < 1e-6).
- **Owner:** legacy `step.py` channel section; successor `channel.py`.

## Stage 3 — Power, service and energy (the physics model)
- **Legacy (declared, thesis eqs 3.11/3.12, deviation X-4):** per-segment recurrence p(t) = p⁰·G(θ(τ))/G(θ(t)) with p⁰ = 0.825 W reset on any association change (`!` renewal premium; confirmed by diag2: forced renewal +0.49 % → exactly 0 under ablation); in-segment budget 3.010 dB → outage; per-beam RF = max over users; equal bandwidth split W = 500/3 MHz; full-buffer Shannon; served = masked action ∧ p ≤ p_max (`!` feasibility, not decodability); PA √(p·p_sat)/0.35, circuit 0.338 W/beam, baseband 0.200 W/satellite; ZOH energy (`!` ≈ +2.27 % undercharge, segment-age dependent).
- **Successor (sealed v1.0–v1.3):** memoryless per-user rate-target TPC (r* = 50 Mbit/s; Γ_r from EN 302 307-1 Table 13; p_u = min(1.65 W, Γ_r·(N₀W + Î)/ĥ)); equal-airtime TDM (a′ = FDM sibling; b = fixed RF + ACM reference; a-γ = fixed SINR sensitivity); coupled capped fixed point; served ⇔ SINR ≥ −1.4418 dB after joint resolution; energy = per-slot PA + 0.338/active chain + 0.200/active satellite (+ P_idle sensitivity); 47-sub-interval integration; T = left-endpoint legacy snapshot.
- **Invariants:** same radiation for wanted signal, interference and PA draw; PA averaged per slot (not PA(max), not PA(Σ)); TDM noise N₀W, FDM W/n consistently; infeasible attempts stay in energy/interference; devices charged once. (Verified by controller code read; KATs added as stage-3 item 12.)
- **Guarded by:** 102 KATs (stage 2) + Opus stage-2 audit (running).
- **Owner:** successor `architectures.py`, `acm.py`, `energy.py`, `integration.py`, `resolution.py`.

## Stage 4 — Endpoint and reward
- **Endpoint:** pooled EE = ΣB/ΣE over the panel (ratio of sums, never sum of ratios); QoS co-primaries: availability, handover rate, Φ-priced handover cost.
- **Reward core:** R_t = B_t − η_ref·E_t (identity test); λ = η_ref from the nominal-greedy reference; κ = B_ref/(U·T_ref).
- **Invariants:** explicit λ/η/κ everywhere (`!` legacy stale default 84 994 621 at `ee_axis_ops3.py:66`, `…_live.py:925`; 25 call sites could reach it); reward energy = endpoint energy (`!` legacy endpoint paid a negative handover cost via the p⁰ reset); Φ prices signalling/QoS preference only.
- **Guarded by:** explicit-price assertion helper + test (stage 2); reward/endpoint identity test.
- **Owner:** successor `endpoint.py`, `targets.py`, `calibration.py`.

## Stage 5 — Targets (C1/C2/C3 labels)
- **C1:** whole-network difference surplus (+ Φ). **C2:** three-offset forecasts (−κ per absorbing lost offset). **C3:** interaction share only (stage-2 decision 5: z₃ = Ψ/2, Ψ = F₁₁ − F₁₀ − F₀₁ + F₀₀ on F = B − η_ref·E, per regime) — `!` legacy executed C3 ≠ declared LC-SRS Ψ; J reused across regimes.
- **Invariants:** no double counting between C1 and C3 (KAT in stage 4); targets computed from the same physics as the endpoint; catalogue used for Ψ is the sealed bounded catalogue (decision 4).
- **Guarded by:** target parity suite (12 tests) + stage-3 end-to-end DeclaredTarget × Decoder parity (item 9).
- **Owner:** `targets.py`; parity suite.

## Stage 6 — Source tapes and training data
- **Legacy:** source NPZ shards from carrier rollouts; Q1 state 228-D, Q2 state 448-D (hetero); labels from stage 5; replay buffer; checkpoints every 100 episodes.
- **Successor:** 21-field per-action state schema (sha 54ab6a82…) replaces recurrence power / entry-gain ratio / segment age; source generation only after the calibration freeze.
- **Invariants:** state carries the information the coordinator uses (`?` — the diag2/cadence result says LITE's edge is exact current-profile joint physics; the learned heads see lagged/frozen-background interaction features: this is the deployable-information gap and is NOT yet closed by design — auditor B); label prices bound to the sealed calibration; no TEST worlds in shards.
- **Guarded by:** `?` (no schema-to-information test exists).
- **Owner:** legacy runtime `ee_axis_*`, `trainer_env.py`; successor `state_v025.py` + stage C generator (not yet written).

## Stage 7 — Learner and deployment
- **Legacy:** Q1/Q2 heads (modqn), per-head bootstrap loops heads (`!` but per-head next-action maxima may be incompatible — needs the common-action bootstrap fixture, stage-3 item 9); deployment = masked argmax(Q1 + Q2); DROP_Cx arms; ALL_NEUTRAL_CONTROL retrained, external BASELINE.
- **Successor plan:** same learner with the 21-field state and scalarised common-action bootstrap; C3 as set-level coordinator over a bounded catalogue (or, under a (d)-dominant diag3, an exact-evaluator layer whose claim is information).
- **Invariants:** scale commensurability of Q1 (bits) and Q2 (bits via κ) in the sum; the deployed action is one joint legal action; DROP arms differ only in the dropped head; seeds 5 with CRN init.
- **Guarded by:** `?` (auditor B).
- **Owner:** `src/mcrl/algorithms/modqn.py`, runtime; stage C spec (to write).

## Stage 8 — Evaluation and claim
- **Design (sealed):** 6 arms × 5 seeds × ≈ 600 worlds over ≈ 161 TLE dates; independence unit = TLE date × seed; pooled ΣB/ΣE with cluster bootstrap; supplementary paired log-EE and delta-method; δ = +0.5 pp lower-bound rule for each FULL − DROP; QoS non-inferiority margins (decision 6); one terminal decision; no TEST split; conditional intersection-union claim.
- **Invariants:** the same physics/endpoint code as training; receipts write-once with sha256; NULL ≡ BASE placebo on every harness; dry-run executes one real step of every arm; no rerun selected by outcome.
- **Guarded by:** runner tests; diag2 placebo (legacy harness OK).
- **Owner:** `probe/run_v025_matrix_probe.py` (matrix) and the stage-C runner (to write); pipeline session on `sat` (staged/held until PHYSICS-GO).

## Cross-cutting invariants nobody owned until now
1. **Units and constants** travel with provenance labels (`VERIFY_SOURCE`) — one table, one source of truth (`constants_v025.py`).
2. **Identity keys:** (NORAD, beam-chain) everywhere from stage 1 to stage 8; never slot indices.
3. **Time base:** one clock (0.640 s), one alignment rule, one integration rule (treatment 0) from tapes to endpoint.
4. **Prices:** λ/η/κ explicit at every producer/consumer; a test fails on any default.
5. **Splits and seeds:** TRAIN-only asserted at world construction; seed derivation from domains only; CRN across arms.
6. **Placebo and dry-run** on every harness before any unit opens.
7. **Sealed before outcome:** priority order, constants, margins, catalogue, anchors, concurrency (operational) — amendments only pre-outcome.

## Open `?` items for the auditors (2026-09-08)
A (worlds/splits/panels), B (source → learner → deployment information path and scale), C (evaluation/statistics/harness leakage), D (integrator: one user-step traced end to end through the successor implementation; list every untested interface).
