# Controller position — the power/EE model must move to the normal forward-link physics (draft for discussion with gpt-6-astra, 2026-09-08 13:00 UTC)

Author: controller (Claude Fable 5.1). Status: DRAFT position, not a ruling. Owner's framing (12:55 UTC): if the normal physics is the right treatment, adopt it as the system model — it needs no "special declaration"; and the controller must take part in the discussion rather than delegate the judgement.

## 1. What the code does today (verified by the red-team; I checked the cited lines)
- `recurrence_power_w` (`src/mcrl/env/link_budget.py:379`): p(t) = p⁰ · G^T(θ(τ)) / G^T(θ(t)); p⁰ = 0.825 W (ruling F-1) at every segment start τ; the in-segment budget is 3.010 dB, beyond which the link is infeasible (service rule).
- Wanted signal (`step.py:946-957`): P_rx ∝ p(t)·G^T(θ(t)) = p⁰·G^T(θ(τ)) — the received level is *held* at the segment-start value; bits therefore do not follow geometry within a segment; energy rises as the user drifts.
- Any association change resets τ and p⁰ (`step.py:829-861`); handover costs no joules (`system_power_w`, `link_budget.py:549`) but the training reward charges Φ₁ = 0.5 / Φ₂ = 1.0.
- Per-beam RF power = max over the beam's users; PA supply from `pa_efficiency` with 5 dB back-off (saturation 5.218 W, cap 1.65 W); circuit 0.338 W per active beam, baseband 0.200 W per active satellite; nothing for inactive beams; bits = full-buffer Shannon over an equal bandwidth split.

## 2. My reading of the physics
1. The gain-inversion recurrence is a *return-link* (uplink) power-control idea transplanted to the forward link. Operational LEO forward links run each carrier/beam at a fixed, backed-off RF power and let ACM change the MODCOD as the terminal's SNR drifts; the transmitter does not ramp power to freeze the received level across a 30 s orbital drift. Three independent reviews (Opus, Gemini, and the harness audit's accounting reading) converge on this; I agree.
2. The consequence is not cosmetic: (a) staying on a beam is charged rising energy for *no* extra bits; (b) re-anchoring is free in the endpoint but penalised in the reward; (c) a coordinator that evaluates the endpoint directly harvests the renewal premium (v1's advantage grows +1.35 → +9.26 % with segment age). So the +2.9 % is, until the ablation says otherwise, largely a property of the model, and the learned heads were trained against an inconsistent objective.
3. The same review pass flags four further terms that decide *comparisons between policies*: per-beam power = max over users (with fixed EIRP this question disappears: an active beam radiates a constant P_b whatever its occupancy); no idle/standby floor for inactive PAs and no bus power (a realism parameter that scales every "fewer lit beams" gain); Shannon without a MODCOD ceiling (rewards concentration with unphysical spectral efficiency); instantaneous on/off of circuit and baseband power (harmless at 30 s granularity for beam hopping, but must be the stated assumption).

## 3. Position
Adopt a **fixed-EIRP + ACM physics successor** as *the* system model of the paper, not as a disclosed deviation:
- **RF**: an active beam radiates constant P_b (I propose P_b = p_max = 1.65 W, the declared legal cap, so that PA operating point and supply power are constants per active beam; alternative p⁰ = 0.825 W — to be argued on provenance, not outcome).
- **Rate**: per-user SINR follows the current geometry every step (current G^T, path, fading, interference); bits = W/n · min(log₂(1+SINR), SE_max) · Δt with a MODCOD ceiling SE_max and an implementation margin (values from DVB-S2X / NR NTN tables, cited; fixed before any run).
- **Service**: served iff SINR ≥ SINR_min (the lowest MODCOD threshold), replacing the p ≤ p_max feasibility test; handover forced only through the existing dwell/candidate rules.
- **Energy**: E = Δt · [ Σ_active beams (P_PA(P_b) + P_cir) + Σ_active sats P_BB ]; no handover energy in the denominator (physically negligible for the payload); standby power for inactive PAs enters as a *declared constant with provenance* if a source supports it, otherwise 0 with a pre-declared sensitivity — this is ordinary system-model reporting, not a special disclosure.
- **Reward**: C1's λ·energy uses the successor energy; Φ stays as a QoS penalty (its purpose is interruption, not joules); κ unchanged; λ re-derived by the same rule as before from the successor reference run (never from outcomes).
- **What is re-run**: cheap probes first (E1 existence U₁/J₁, S0 one-step decoder, oracle marginals; hours) — if a set-level coordinator has no headroom without the renewal premium, we know before training; then stage A (C1/C2 source training) on the successor, stage C ladder, C3-S screens and confirmatory ladder. Sealed old-physics artifacts are kept as history and cited in the internal record; the paper describes the successor physics as its model.

## 4. Why this is not outcome-driven tuning
The change removes an artifact that *favoured* our own positive result; it is motivated by forward-link practice and by three independent code reviews; it is fixed before any confirmatory run; every constant is chosen by provenance. The internal continuation record documents the history; the paper needs only its system-model section.

## 5. Ordering
- Hold stage-A attempt #4 at the step-3 dry-run (everything landed and gated; relaunch is one file away) until the successor spec is fixed — training on a model we are about to replace is the only wasted path. Target: spec agreed today, implementation + known-answer tests by codex within hours, probes tonight, training tomorrow.
- The C3-S ablation (`ablate_anchor`) and churn-null arms still run on the old physics: they attribute the v1 result and calibrate how much of "coordination" survives; cheap and informative for the paper's history.

## 6. Questions for astra (discussion, not delegation)
1. Fixed P_b = p_max or p⁰? What provenance decides it, and does the PA operating point (5 dB back-off) stay?
2. SE_max and implementation margin: which table (DVB-S2X, NR NTN) and which single value pair, cited?
3. Standby power for an inactive PA: is there a citable number, or is 0 + sensitivity the honest choice?
4. Service by SINR_min vs the current dwell/feasibility semantics: does replacing the p ≤ p_max rule change the action contract or masks in a way that breaks C2's OPS-3 persistence machinery?
5. Does anything in the old-physics chronology (R7 negative, F1 kill screen, E1/S0 positives) remain interpretable, or is it all "old model" history?
6. Is there any reason to keep the gain-inversion model as a *secondary* scenario, or should it be retired entirely?

## Addendum 13:30 UTC — after the Opus anchored-power audit (`PHYSICS-AUDIT-SEGMENT-ANCHORED-POWER-CLAUDE-OPUS-2026-09-08.md`)
- Precision: power is recomputed every step; what is frozen is the reference gain G^T(θ(τ)); the in-segment invariant is the product p·G^T (received level). Path loss, fading, interference and the beam max are current. The only in-segment change is the p > p_max feasibility test → outage → forced re-anchor. Documentation status: IMPLIED — the recurrence is declared (paper eqs 3.11/3.12, DEVIATION-REGISTER X-4) but open/closed-loop semantics, cadence and "handover = 0 J" are absent from PREREG-FROZEN ×4 and the V0.23 endpoint contracts. Verdict (ii): declared ≠ standard; no power-control reference updates only at handover.
- Magnitude: renewal raises EE whenever SE > 2.52 bit/s/Hz (panel SE ≈ 3.67–4.59); a single beam re-anchored at 0.744 dB staleness yields exactly the observed +2.883 %; the receipts cannot exclude that 100 % of the energy-side gain is renewal. Per-beam power bracket is [6.266, 8.721] W (the red-team's [6.27, 6.78] used a stale 0.718 dB line; probe P7 shows the power gate binds with 7.6 % outage).
- **C2 is built on the anchor**: its temporal state features are `previous_recurrence_power`, `current_to_segment_start_gain_ratio` (= p⁰/p), `segment_age`, `missing_incumbent`; under per-step physics three of them become constants. Therefore the successor must redefine C2's persistence/service-risk state from geometry and rate forecasts (future SINR/rate trajectory, outage risk, remaining visibility), not from the recurrence. This is a design change to C2, not only to the physics — add to the successor spec and to astra's question 4.
- P_b choice matters: P_b = p⁰ vs p_max changes per-beam total power 6.266 W vs 8.721 W (39 %); decide by provenance (declared legal cap and PA operating point) before any run.
- Cheapest exact energy decomposition (no new physics): replay one unit's three arms logging N_lit_beams and Σ_b √p_b per step; ΔJ/Δt = 6.5264·Δ(Σ√p) + 0.338·ΔN_beams + 0.200·ΔN_act_sat, bit-verifiable against `energy_j_hex`. Fold into the churn-null instrumentation.
