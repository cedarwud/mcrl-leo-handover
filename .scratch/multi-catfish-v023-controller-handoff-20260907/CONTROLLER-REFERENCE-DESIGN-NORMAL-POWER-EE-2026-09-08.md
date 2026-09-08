# Reference design from first principles — what a normal power / EE model, reward and training stack look like for a LEO multi-beam forward link (controller, 2026-09-08 13:20 UTC)

Written from the controller's own domain knowledge, deliberately *without* taking the existing simulator as the reference. Purpose: a yardstick against which the current implementation is measured (§6), and the baseline that astra round 2 must critique. Owner's instruction: "跳出 context 跟 prompt，用原生知識檢視 power/ee 公式設計與實作／訓練應該怎樣才是正常合理的方式".

## 1. Forward-link physics (what operators actually do)
1. **Transmit side.** Each active beam radiates a fixed RF power P_b set by the payload's PA operating point (a fixed output back-off from saturation). EIRP toward a user at off-axis angle θ is P_b·G_tx(θ) with a declared beam pattern (e.g. TR 38.811 Bessel pattern or a Gaussian roll-off with a stated 3 dB beamwidth). The power does **not** ramp during a pass to hold a user's received level; *rate* adapts instead. Flexible payloads can re-share power between beams, but per-beam power is then a slow, declared allocation — never an implicit per-user gain inversion.
2. **Receive side.** C/N₀ = EIRP(θ) − FSPL(d) − L_atm − L_shadow + (G/T)_terminal − k. Small-scale fading (Rician with elevation-dependent K) and shadowing are exogenous random processes, sampled from the current geometry at each step, identical across the arms being compared (common random numbers).
3. **Interference.** Co-channel beams (same colour under the frequency-reuse plan) interfere with pattern gain toward the user; SINR = C / (N + Σ I). With frequency reuse 3 and 500 MHz, each beam has W = 166.67 MHz.
4. **Rate.** ACM maps SINR to a spectral efficiency SE(SINR) from a MODCOD table (DVB-S2X or NR NTN MCS), bounded above by SE_max (≈ 5–6 bit/s/Hz) and below by the lowest MODCOD threshold SINR_min; Shannon-with-gap-and-cap is an acceptable smooth surrogate. Users in a beam share W by TDM (time fractions f_u, Σ f_u ≤ 1) or FDM; equal share is the usual baseline. Per-user rate R_u = f_u·W·SE(SINR_u). Rate follows geometry **every step**; staying on a degrading beam loses bits, not energy.
5. **Service.** A user is served iff SINR_u ≥ SINR_min (and, if modelled, a minimum-rate guarantee). "Served" is a function of the current link, not of a power-feasibility recurrence.
6. **Handover.** A change of serving beam/satellite. Its costs are QoS costs — an interruption gap (tens to hundreds of ms), signalling — and for the payload they are energetically negligible at a 30 s decision cadence. Handover is therefore a *constraint or QoS term*, not a joule term; and nothing in the physics may hand a policy an energy reward for handing over.
7. **Time base.** Association decisions every Δt (30 s is reasonable for LEO); ACM and scheduling act within the step and are modelled as instantaneous per-step averages. In-step drift of elevation/gain is computed from ephemeris at the step boundary (or mid-step) — consistently for all quantities.

## 2. Energy model (what the joules are)
P_payload(t) = Σ_{b ∈ active} [ P_PA(P_b) + P_cir ] + Σ_{s ∈ active sats} P_BB + P_bus
- P_PA(P_b) = P_b / η_PA(P_b), with η_PA from a declared curve (class-AB/B ≈ η_max·√(P_b/P_sat); Doherty flatter). **At fixed P_b this is a constant per active beam.**
- P_cir: per-active-beam circuitry (up/down conversion, filters). P_BB: per-satellite baseband when at least one beam is active. P_bus: platform power (thermal, attitude, TT&C) — constant, policy-independent; including it lowers every EE number equally and does not reorder policies, but it caps the *relative* gains a beam-sleeping policy can show. Standby power of a switched-off PA (bias kept warm) is a small declared constant or 0 with a sensitivity.
- **Consequences.** Energy is (i) a lit-beam counter (dominant), (ii) weakly dependent on which beams are lit (if P_b varies by beam class), and (iii) independent of how many users a beam serves and of how long they have been served. The only decisions that change energy are beam activation/deactivation (which requires emptying a beam — a joint action) and, in flexible payloads, per-beam power allocation.

## 3. The EE objective and its decomposition
η = Σ_t Σ_u bits_u(t) / Σ_t P_payload(t)·Δt — a ratio of sums over the whole panel (never a mean of per-episode ratios). Fractional programming (Dinkelbach): the optimum of the ratio is the optimum of B − η*·E at η* = the optimal ratio, so a linear surrogate B − η_ref·E with η_ref close to the achievable EE is the correct one-step objective, and improving the surrogate at a fixed η_ref implies improving the ratio only when η_ref ≈ the compared policy's realised η (report both).
Levers, in order of magnitude for this architecture: (1) number of active beams — consolidation; (2) association quality — SINR/rate per user; (3) interference — avoiding co-channel collisions; (4) power allocation if flexible. **"Load balancing" is not an EE lever**: spreading users lights more beams; EE wants consolidation subject to QoS (rate, fairness, handover rate).

## 4. Reward design for per-user RL agents (normal practice)
1. **Global step reward** R_t = B_t − η_ref·E_t, with **the same E_t function as the evaluation endpoint** (same beam aggregation, same activation semantics, same constants). η_ref is fixed for a training run (or updated Dinkelbach-style between epochs from the realised EE), never fitted to outcomes.
2. **Credit assignment.** Difference reward r_u = R_t(a) − R_t(a with u at its default) — the "surplus" idea — or a declared shared-cost split of beam energy across the beam's users. Additive per-user surpluses cannot represent the joint gain of emptying a beam (the saving appears only when the last user leaves): that gain must be given to a coordinator or a shaped joint term, not hidden in per-user Q-heads.
3. **QoS/handover.** Either a Lagrangian penalty Φ per handover (with the multiplier tied to a declared handover-rate or interruption budget) or a hard constraint. If Φ is in the reward, the evaluation must report handover rate and outage as co-primary metrics; and the physics must contain **no** hidden incentive that contradicts Φ.
4. **Persistence / lookahead.** A finite-horizon term valuing the future rate/outage of staying vs moving (what OPS-3 tries to be) is normal, provided the underlying physics does not itself reward churn.
5. **Coordination.** Beam consolidation is a set-level decision: a centralised coordinator (or a market/auction) over per-user proposals is the normal architecture; it uses the *nominal* channel (no realised fading), the same energy function, and is judged against a strong non-learned nominal-physics baseline as well as the learned one.

## 5. Implementation and training discipline (normal practice)
- Physics recomputed from the current state at every step; the only per-link state is explicitly modelled controllers with a declared algorithm and cadence (ACM state; power control only if the payload has it, on the return link).
- **One energy function** shared by env reward, evaluation endpoint and any model-based coordinator (with an information restriction for the coordinator: nominal vs realised channel).
- Known-answer unit tests: 2-user/1-beam joules and bits by hand; energy independent of handover count; energy monotone in lit-beam count; SE cap binding; served ⇔ SINR ≥ SINR_min; a fixture where ratio-of-sums ≠ mean-of-ratios; reward–endpoint consistency: Σ_t r_t (at η_ref) = B − η_ref·E from the endpoint function on the same trajectory.
- Matched comparisons by common random numbers; fresh independent worlds for evaluation; placebo (NULL) and random-feasible arms in every screen; independent recomputation of headline numbers from raw receipts.
- λ/κ-type constants derived from a reference run *of the same physics*, by a rule fixed in advance.

## 6. Where the current stack departs from this (ranked by consequence)
| # | Current implementation | Normal | Consequence | Handling |
|---|---|---|---|---|
| 1 | Per-user power recurrence p(t) = p⁰·G^T(θ(τ))/G^T(θ(t)), p⁰ reset at every handover; received level frozen at segment start | Fixed P_b per beam; rate follows geometry | Energy rises with segment age for no bits; churn is free for the endpoint → renewal premium; training signal contradicts physics | FIX (successor physics) |
| 2 | Reward energy term and Φ vs endpoint: handover penalised in reward, free in joules; energy attribution per user unclear | One energy function; Φ as QoS with co-primary reporting | Learned BASE avoids the endpoint-optimal behaviour; coordinator harvests the gap | FIX (reward = endpoint function; Φ stays as QoS + reported) |
| 3 | Service = power feasibility within the 3.01 dB in-segment budget (p ≤ p_max) | Served ⇔ SINR ≥ SINR_min | Service saturates by construction; guards vacuous | FIX with the physics |
| 4 | Full-buffer Shannon, no SE cap | ACM/MODCOD cap SE_max + margin | Rewards concentration with unphysical SE | FIX (cap + margin, cited) |
| 5 | Per-beam RF power = max over users | Fixed P_b per beam (moot) | Under (1) it made occupancy energy-free; under fixed P_b the question disappears | Retire with (1) |
| 6 | No standby / bus floor; instant on/off | Declared constants; standby small | Overstates relative gains of beam sleeping; ranking unchanged | DECLARE + SENSITIVITY |
| 7 | "C3 = load balancing / observability" framing; additive per-user Q3 | Coordinator for consolidation; per-user heads for surplus and persistence | Two weeks of ≤ 0 oracle marginals were structural | Reframe (C3-S shape is the normal one) |
| 8 | λ = 118 424 222.86 bits/J derived under the old physics | η_ref from a reference run of the successor physics | Constants carry the artifact | Re-derive by the same rule |

## 7. What the switch costs and what it buys
- Implementation: physics successor module (fixed P_b, ACM cap, SINR service, one energy function, reward wiring) with known-answer tests — codex, about a day; probes (E1 U₁/J₁, S0 decoder, oracle marginals) — hours; stage A retrain — hours; stage C ladders — days.
- It buys a system model that a reviewer recognises, a reward that agrees with the endpoint, a C3 that is tested on a real lever (beam consolidation), and an end to hunting artifacts that the model itself planted.
