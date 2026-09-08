# Full audit of the energy / bits / service / EE model — Claude Opus 5, 2026-09-08 (r2)

Fresh context, code-first, read-only. Every number recomputed with `.venv/bin/python` against `src/mcrl/env/link_budget.py` + `antenna.py`, or read
from `artifacts/probe-p4-2026-08-23.json` and `artifacts/probe-p7-*-2026-08-23.json`. Builds on
`PHYSICS-AUDIT-SEGMENT-ANCHORED-POWER-CLAUDE-OPUS-2026-09-08.md` (the recurrence is established there and not re-derived). r2 supersedes the 20:42
draft at this path, whose §E1/E2 antenna arithmetic was wrong (`p⁰·G(1.0)/G(1.4) = 1.0508 W`, not 0.9166; `p⁰·G(1.5)/G(0.5) = 0.4997 W`, not 0.7185).

**Three corrections to the brief's constants.** (1) **The per-beam bracket is `[0.349, 8.721] W`, not `[6.266, 8.721]`** — `p` has no floor at `p⁰`:
P7 reports `feasible_link_power_w.min = 2.93e-06 W` (54 dB **below** `p⁰`) ⇒ `6.5264√p + 0.338 = 0.349 W`; the span is **25×**, not 1.39×. (2) Hence
**"3.226 W ≈ 0.50 beams/step" is not identified**: it is 0.515 beams at `p⁰`, or ~9 beams re-anchored by 1 dB, or one beam moved to a −7 dB anchor —
the receipts carry neither `N_lit` nor `Σ√p`. (3) **The PA never saturates:** `p ≤ p_max = 0.3163·p_sat` ⇒ `ξ ≤ 0.19682 < ξ_max = 0.35`; the `min` in
(3.15a) is dead code and only `√p_sat/ξ_max = 6.526404` is identified.

**Operating point (probe P4, 80 steps, stay-if-possible, 100 users):** 41.75 lit beams/step (p05–p95 38–47), 7894 served links, SINR p50 **6.604 dB**,
interference cost p50 **7.345 dB** ⇒ `I/N = 4.43` (**82 % of the SINR denominator is interference**), intra fraction **0.946**. P7 main arm: outage
**7.6 %**, `feasible_link_power_w` p05 = p50 = p95 = **0.825 W exactly** (≥ 90 % of served links sit on a fresh anchor).

**Two framing identities.** (i) `P^p = p/ξ` with `ξ = ξ_max√(p/p_sat)` collapses to **`P^p = 6.526404·√p`**, so a lit beam costs `6.5264√p + 0.338 W`
— **6.2659 W at `p⁰`**, 8.7213 at `p_max`, 0.349 at the observed floor (PA 94.6 %, circuit 5.4 %, baseband 0.3 %); `41.75 × 6.2659 + 4×0.2 = 262.4 W`
matches the ≈260 W receipt. (ii) **Inside a segment the received wanted term `p·G^T(θ(t)) = p⁰·G^T(θ(τ))` is frozen** (`step.py:946-957`): bits are
geometry-independent while energy moves as `√p` over 54 dB — a **free option with zero bits cost**, the mirror image of the renewal premium.

## Summary — ranked by impact

| # | Term (file:line) | Free option / comparison artifact | Pooled-EE order | Contrast (coord vs BASE) | Verdict |
|---|---|---|---|---|---|
| A1 | Anchored `p·G^T` + zero-joule handover (`link_budget.py:379`; `step.py:824-862`, `1101`) | re-association is unpriced power control; reward charges Φ, endpoint charges 0 | ±8 %/beam | **can account for all of +2.9 %** | **FIX** |
| A2 | No floor on the recurrence: hold an anchor through improving geometry (`link_budget.py:379`) | energy ↓ up to 25×, **bits exactly unchanged** | ×1.1–×17.9 per beam | pure gain to any endpoint-optimiser | **FIX** |
| A3 | Interference co-scales with the anchor (`interference.py:318` vs `step.py:946`) | **collective** renewal is superadditive: +6.3 % EE per 0.718 dB at I/N=4.4, vs −0.08 % for one beam | +6…+25 % if network-wide | **this is a coordinator-only lever** | **FIX/SENS** |
| A4 | `pa_efficiency` saturation branch unreachable (`link_budget.py:468`) | ξ_max, BO, p_sat not separately identified | sets 94.6 % of denominator | none (arm-symmetric) | **DECLARE** |
| A5 | Beam RF = **max** over users, never sum (`link_budget.py:439`, `step.py:886`) | 2nd..Uth user costs 0 W of RF *and* 0 W of circuit | sum form ⇒ +51 % `P^N` | favours packing arms | **DECLARE+SENS** |
| A6 | Instant on/off; no idle/standby/bus/re-steer/signalling floor (`link_budget.py:521,549`) | `P^N` ≡ 6.27 W × lit beams + 0.2 W × lit satellites | 100 % of denominator | favours beam-extinguishing arms | **DECLARE+SENS** |
| A7 | `p > p_max` admission gate is age×geometry dependent (`link_budget.py:411`, `step.py:812-820`) | a handover clears an outage for free | 7.6 % of links, 0.16 % w/o warm start (**47×**) | favours handover-happy arms | **FIX(doc)+SENS** |
| A8 | Warm start ages segments beyond their life (`step.py:142-175`) | amplifier, not option; declared anti-conservative | doubles A1/A2/A7 | inflates the contrast too | **SENSITIVITY** |
| A9 | Bits: uncapped Shannon, full buffer, `B^w/U` with full-`B^w` noise (`link_budget.py:590`, `step.py:215-217`) | no MODCOD/SE ceiling; TDM-only consistency | sets numerator scale | mild, arm-symmetric | **DECLARE** |
| A10 | Pooled EE = Σbits/Σjoules, joule-weighted (`ee_axis_evaluation.py:155,183-184`) | Δt cancels exactly; late-dwell steps down-weighted | 0 on level | conservative by ~3× vs phase 3 | **DECLARE** |
| A11 | Reward ≠ endpoint (Ω, c₁–c₃, Φ, κ; `action_contract.py:408-418`, `reward_calibration.py:43`) | BASE optimises `0.5r₁/c₁+0.3r₂+0.2r₃/c₃`; endpoint is `r₁` alone; C3-S optimises `bits − η_ref·J` (`c3s_policy.py:230`) | n/a | **the premise of the contrast** | **DECLARE** |
| A12 | Service saturates; G-8 guard vacuous (`service.py:185`, `energy_efficiency.py:187`) | served ≈ 92–100 %, so the service guard cannot bind | none | kill rule ⇒ bare EE test | **DECLARE** |
| A13 | Shadow fading is a lognormal **gain**, elevation-keyed (`link_budget.py:151`) | up to +1.5 dB free mean gain by elevation; 90° cliff | +0.4…+1.5 dB on bits | matters only if elevation mixes differ | **DECLARE** |
| A14 | F-2 regression guard is tautological (`step.py:998-1006`, `1476`) | ratio is 1.0 by algebra; the project believes it has a live guard | none | none | **FIX** |
| A15 | 30.08 s zero-order hold over a Bessel pattern (`constants.py:76`) | inter-sample excursions invisible; handover time cost diluted 47× | biases outage low | shared by arms | **SENSITIVITY** |
| A16 | Candidate γ prices every slot at `p⁰` (`step.py:1201-1260`) | state mis-prices the incumbent **in both directions** | none directly | mild, arm-symmetric | **DECLARE** |

---

### A1 — Segment anchoring + zero-joule handover *(dominant, established)*
**Implemented.** `recurrence_power_w` (`link_budget.py:379`) `p(t)=p⁰·G^T(θ(τ))/G^T(θ(t))`; anchor committed only if served (`step.py:824-862`), else
`self._segments[uid]=None` ⇒ the next served step re-opens at `p⁰`. `HANDOVER_COST` (`action_contract.py:414-418`) has exactly one call site,
`step.py:1101` (`r2_handover`); zero hits for handover energy in `link_budget.py` / `ee_axis_evaluation.py` / `c3s_policy.py`. **Provenance.** Eqs
(3.11)/(3.12), C-2/F-1; `DEVIATION-REGISTER.md:195` (X-4); `ADR-004:78-82` (`E_HO = 0` is a *boundary* statement, not a physical claim);
`R2-PHYS-PROVENANCE-MATRIX:153-171` `R2_PHYS = NOT_CLOSED`. **Option.** Objective, not informational: a handover is free in joules, priced −0.5/−1.0
in the reward. **Size.** Resetting every beam from the documented max staleness (0.718 dB) saves 0.511 W/beam = **20.4 W ≈ 7.8 %**. **Fixture.** 2
users, 1 sat, 2 beams, fading off, anchors θ=1.0°, current θ=1.4°: hold ⇒ `p = 1.050835 W`, `P^N = 6.6902+0.338+0.200 = 7.2282 W`; hand over ⇒ `p =
0.825 W`, `P^N = 6.4659 W`, `r2 = −0.5` — assert the endpoint charges arm B **zero** extra joules while the reward charges 0.5. **FIX** — price `E_HO`
as a declared lower-bound sensitivity, or hold handover counts equal across arms.

### A2 — No floor: hold an anchor through *improving* geometry *(new, and larger than A1)*
**Implemented.** Same line; no clamp, min, max or projection (deliberate, C-2). Because `wanted =
link_power[u]·field_now.transmit_gain[u,col]·path·fade·G^R` (`step.py:946-957`), the transmit-gain factor **cancels**: received wanted power is frozen
at `p⁰·G^T(θ(τ))` for the segment's life. **Option.** θ(t) is unimodal in time (minimum at closest approach). Anchor while θ is large, hold while θ
shrinks: `p` falls with `G(τ)/G(t) < 1`, **bits do not move at all**, and the interference footprint falls too. **Size.** Anchor at θ=2.5°, ride to
boresight ⇒ `p = 0.1584 W`, beam **2.936 W vs 6.266 W (−53 %)**; at the observed P7 minimum the beam costs **0.349 W — EE ×17.9 at unchanged bits**.
The reference policy leaves it unexploited (`p05 = p50 = p95 = 0.825 W`); an endpoint-optimiser will not, and the reward *rewards* holding a segment.
**Contradicted claim.** `link_budget.py:213` and `:726` both assert "the recurrence only ever *raises* power inside a segment" — and that premise
**is** F-1's derivation of `p⁰ = p_max/2`; P7's `feasible_budget_fraction.mean = −0.018`, `.min = −18.10` falsify it. **Fixture.** 1 user, 1 beam, no
fading, θ(τ)=1.5°, θ(t)=0.5°: assert `recurrence_power_w = 0.499706 W < p⁰`, `system_power_w = 4.6135+0.338+0.200 = 5.1515 W`. No test asserts this
today. **FIX (doc + a floor test).**

### A3 — Interference co-scales with the anchor ⇒ renewal is *superadditive* *(new; sharpens the physics audit)*
**Implemented.** Aggressor term is `radiating.power_w[None,:] · field.transmit_gain · path · fading · receive` (`interference.py:318`, via
`received_power_terms:277`): the aggressor's **anchored** beam power times its **current** off-axis gain. The victim's own term is frozen (A2). So a
beam's interference output scales with *its* staleness. **Consequence.** Single-beam renewal loses bits at `dlnB/dlnSNR = γ/((1+γ)ln(1+γ))` and saves
energy at `0.4730·ln r`; at the P4 median (γ = 6.604 dB, SE = 2.479) these cancel to **−0.03 … −0.31 %** — **the per-beam renewal premium is ≈ 0 at
the measured operating point**, not +2.8 %. But when *many* beams re-anchor together `I` falls with the wanted signal and only noise stays:
`SINR'/SINR = (I+N)/(I+rN)`. At `I/N = 4.43` and 0.718 dB the SINR loss is **0.142 dB** while energy still falls 7.8 % ⇒ **ΔEE = +6.3 %**; at 1.5 dB
**+12.8 %**; at 3.0 dB **+24.6 %**. **Artifact.** The option is **superadditive in the number of beams re-anchored in the same step** — available to a
set-level coordinator, essentially absent to a single-user policy: exactly the C3-S shape, and a property of the price list rather than of
coordination. **Fixture.** Two co-colour beams both stale by 0.718 dB, fading off: renew one ⇒ ΔEE ≈ 0; renew both ⇒ ΔEE ≈ +6 %. Assert the two-beam
gain exceeds twice the one-beam gain. **FIX/SENSITIVITY** — a CPC arm (re-anchor every step) removes it identically.

### A4 — `pa_efficiency`: shape, back-off, saturation, reachable regime
`ξ = min{ξ_max, ξ_max√(p/p_sat)}` (`link_budget.py:468`), `ξ_max = 0.35` (`:254`, **S**), `BO = 5 dB` (`:257`, **S**), `p_sat = p_max·10^(BO/10) =
5.217758 W` (`:260`, **D**); C-5: the √ law is why `r1` is an efficiency. **Reachable regime:** `p ∈ [2.9e-06, 1.65] W` ⇒ `ξ ∈ [4.1e-04, 0.19682]`,
live ≈ 0.139 at `p⁰` — **the saturation branch is unreachable and the three constants are not separately identified**; only `6.526404` enters.
**Fixture.** `pa_efficiency([1.65]) == 0.1968187…`, `pa_efficiency([5.217758]) == 0.35`, `supply_power_w(p, pa_efficiency(p)) == 6.526404√p` to 1e-12
at p ∈ {0.1, 0.825, 1.65}. **DECLARE** — the PA runs at 14–20 %; 0.35 is a curve parameter.

### A5 — PA input is the **max** over users, not the sum
`beam_power_w` (`link_budget.py:439`) `p_{s,v} = max_{u:x=1} p_{u,s,v}`, consumed at `step.py:886` and re-used as the radiated power for interference.
Ruling C-10, quoted verbatim; consequence undocumented. **Artifact.** The 2nd..Uth user on a beam is served at **zero marginal RF and zero marginal
circuit power** — EE-neutral under `B^w/U` sharing only if SE is homogeneous (mean load 2.36). **Size / fixture.** link powers `(0.825, 1.050835)` on
one beam ⇒ `beam_power_w → 1.050835` (not 1.875835 sum, not 0.937918 mean) ⇒ `P^N = 7.2282 W`; the sum form gives 9.4766 W (**+31 % on that beam**, ≈
+51 % at network mean load). **DECLARE + SENSITIVITY.**

### A6 — `system_power_w`: indicator semantics, instant on/off, missing floors, P_BB guard
`fixed_power_w` (`:521`) `= Σ_s N^act_s·0.338 + 0.200·#{s : N^act_s > 0}`; `system_power_w` (`:549`) adds `Σ_b P^p_b` and **guards only that `Σ_s
N^act_s == len(supply)`** — a shape check, not a double-count check. On the live path `beams_by_satellite` is built from `beam_keys`
(`step.py:985-991`), so every count is > 0 and the `1{·}` indicator is **vacuous**; `P_BB` is 0.3 % of `P^N`. Activation is `z = 1{U>0}`
(`service.py:149`), derived, no ceiling, no hysteresis: a beam with no served user costs **exactly 0 W** and radiates nothing, in the same 30.08 s
step. **Provenance.** `P_cir`/`P_BB` cited to You et al. Table II (`:270,273`), but `BEAM_TO_RF_CHAIN_IS_SOURCED = False` (`:276`, C-6) and the model
is *partial* (LO + phase shifters excluded). Idle / standby / bus / re-steering / signalling energy: **zero mentions anywhere in `docs/`**;
`ADR-004:20-24` names the boundary but claims no physics. **Artifact / size.** `P^N` **is** a lit-beam counter, so any arm lighting fewer beams wins
joules outright; a 1 W idle floor per illuminated beam moves `P^N` 262 → ≈418 W and makes extinction nearly worthless. **Fixture.**
`fixed_power_w([2,1]) == 1.414`; drop satellite B's only user ⇒ `fixed_power_w([2]) == 0.876` — a satellite's baseband disappears in one step at zero
cost. **DECLARE + SENSITIVITY.**

### A7 — The `p ≤ p_max` gate
`classify_link_power_feasibility` (`link_budget.py:411`) is per link, outside the recurrence; failures leave `served`, load, activation, power and
bits (`service.py:185`). Budget `10log10(p_max/p⁰) = 3.0103 dB` (`:737`), i.e. a gain ratio of exactly 2. **Measured:** outage 7.6 % (warm start) vs
0.1625 % (no warm start) — a **47×** swing from segment age alone; `infeasible_required_power_w` p50 = 8.67 W, p95 = 828 W, max 140.8 kW. **Option.**
An outaged user earns 0 bits; a handover resets τ and restores service at once, at zero endpoint cost. **Fixture.** One user with `G(τ)/G(t) > 2`
(θ(τ)=2.5°, θ(t)=3.0° ⇒ ratio 2.30, p = 1.901 W): assert `outage_infeasible`, `served_count == 0`, `system_power_w == 0.0`, `zero_over_zero = True`;
hand over at the same step and assert service resumes at exactly 0.825 W. **FIX (the in-code claim, D2) + SENSITIVITY** (per-arm outage).

### A8 — Warm start
`segment_warm_start = "uniform-episode-length"` (`step.py:142-175`), age ~ `U{0..H−1}`, H = 10 (`constants.py:102`); the frozen sensitivity arm uses L
= 5. The docstring states the main arm's bias is **not** conservative: it "makes the mechanism look **more** active, in exactly the direction we are
trying to establish". **SENSITIVITY** — run arm 2.

### A9 — Bits
`shannon_rate_bps` (`link_budget.py:590`) `R = (B^w/U)·log₂(1+γ)`, `B^w = 500/3 = 166.6667 MHz` (`:24,:28`), zero-load beam ⇒ 0. Noise is `σ² =
k_B·T_sys·B^w` over the **full** `B^w` (`step.py:215-217`; `T_sys = 242.29 K`, `σ² = 5.575e-13 W`), **independent of load** — consistent only under
TDM; an FDM reading over-counts noise by `U`. No MODCOD table, no SE ceiling, full buffer. Endpoint bits are `Σ_u R_u × 30.08 s`
(`ee_axis_evaluation.py:183`). **Fixture.** `shannon_rate_bps([3.0], beam_load=[2]) == 1.6666667e8` exactly; `beam_load=[0] ⇒ 0.0`. **DECLARE.**

### A10 — Pooled EE aggregation
`total_bits += Σ_u R_u·Δt`, `total_energy += P^N·Δt`, `η = total_bits/total_energy`, re-checked as ratio-of-sums
(`ee_axis_evaluation.py:155,183-184,85-92`); the V0.23 screen re-derives it over rows (`ee_axis_v023_episode_screen.py:602-626`). Δt = 30.08 s
**cancels exactly** (the endpoint is interval-free), and ratio-of-sums is **joule-weighted**, so the dwell phases where the option is largest carry
the fewest joules: pooled +2.9 % is a conservative read of phase-3 +9.3 %. **Fixture.** Steps (10 bits, 1 J) and (1 bit, 10 J): ratio-of-sums = 1.0
(mean-of-ratios would be 5.05). **DECLARE** — publish phase-stratified EE beside the pooled number.

### A11 — Reward vs endpoint: is the reward's energy the same function?
**Yes, identically.** `r1 = R_u / P^N` (`energy_efficiency.py:251` → `:226`) consumes `physics["system_power_w"]` (`step.py:1068`) — the same function
the endpoint integrates. The differences are elsewhere: (a) **extra terms** — `r2 = −HANDOVER_COST` (Φ₁ = 0.5, Φ₂ = 1.0, class **S**,
`action_contract.py:408-418`), `r3 = −U_{b_u}` (`service.py:264`), scalarised `Σ ω_j r_j/c_j`, `Ω = (0.5,0.3,0.2)`, `c₁ = 2029238.4329`
(`reward_calibration.py:43`), `c₂ = 1`, `c₃ = 6`; **r₂ is 14–20 % of training and 0 % of the endpoint**; (b) **aggregation** — training sums per-step
per-user ratios (mean-of-ratios), the endpoint is ratio-of-sums (A10); (c) **κ withdrawn** (ruling C-7, `energy_efficiency.py:218-226`) — no per-link
private-power share is on the live path; (d) **λ** appears only in the formula-only surplus decomposition (`ee_surplus_targets.py:100,193`, fixed,
positive, no trainer integration) and, in deployment shape, as `nominal_score = bits − η_ref·energy_J` in the C3-S coordinator
(`c3s_policy.py:230-235`) — **a Dinkelbach linearisation of the endpoint with no handover term at all**. The coordinator therefore optimises exactly
the quantity carrying A1–A3's free options while BASE is penalised for using them. **DECLARE** — score BASE on the scalarised objective too; if it
wins there and loses on EE, the contrast is a re-weighting.

### A12 — Service definition and saturation
`resolve_service` (`service.py:185`): served ⇔ a valid non-no-op action **and** `p ≤ p_max`; two gates (`x = a·z`, C-11), `m^e` and `γ_req(U)`
deleted. `U_{s,v}` is the **post-feasibility** eligible load and drives activation, the beam max, the `B^w/U` divisor and `r3` — pinned by
`assert_single_load_semantics` (`energy_efficiency.py:71`). Served is 92.4–99.8 % in every measured arm, so the G-8 guard (`energy_efficiency.py:187`,
built after the 3.9× / 33.7 %-coverage scandal) **can never bind here**: a kill rule conditioned on it is a bare one-sided EE test. **DECLARE** +
effect-size floor.

### A13 — Shadow fading is a mean **gain** *(slice B's territory; listed because it enters the bits term)*
`shadow_fading_db` (`link_budget.py:151`) draws a zero-mean **dB** Gaussian (σ from TR 38.811 Table 6.6.2-3) applied as a dB loss, so `E[10^(−L/10)] =
exp((σ ln10/10)²/2) > 1`: +0.30 dB @20°, +1.11 @60°, +1.49 @80°, **+0.02 @90°** (the published σ cliff). Keyed `(event, step, NORAD)`, i.i.d. across
steps, `"observation"` draw independent of `"physics"` — no policy can chase a draw, only the elevation-keyed mean. **DECLARE** (per-arm elevation
histogram).

### A14 — The F-2 "live regression" is tautological
`step.py:998-1006` recomputes `beam_charged_power = fixed + supply_power_w(beam_power, pa_efficiency(beam_power)).sum()` and calls it "an INDEPENDENT
recomputation", but `system_power_w` (`link_budget.py:549`) returns the same expression from the same `beam_power`, so `link_over_beam_power_ratio`
(`step.py:1476`) is **1.0 by algebra**. A real guard must rebuild `P^N` from `resolution` + `link_power` alone. **FIX.**

### A15 — Time discretisation
`Δt = 47 × 0.640 = 30.08 s` (`constants.py:76`), H = 10, dwell N = 4, D2 on the 0.640 s clock. `G^T(θ)` is a Bessel pattern **sampled every 30.08 s
and held**, during which a satellite moves ≈222 km against a ≈15.9 km cell radius — so within-step excursions past the 3.0103 dB budget are invisible
(outage biased low) and any handover *time* cost is diluted 47×. Δt cancels from the endpoint (A10), not from the physics. **SENSITIVITY** — one
sub-sampled episode.

### A16 — Candidate γ prices every slot at `p⁰`
`_candidate_sinr` (`step.py:1201-1260`): `wanted = p⁰ · transmit · path · fade` for **all 28 slots including the incumbent**, against the previous
step's radiating set (`CANDIDATE_SINR_PROVENANCE`). The realised incumbent term is `p⁰·G(θ(τ))`, the state's `p⁰·G(θ(t))`: the state **under**-states
a stale-high incumbent and **over**-states one riding into boresight — the error changes sign, contrary to the earlier draft. Repaired separately in
the EE-axis state by `segment_age` / `current_to_segment_start_gain_ratio` (`ee_axis_state.py:50-52`). **DECLARE.**

---

## Code-vs-docs disagreements (13)

| # | Where | Disagreement |
|---|---|---|
| D1 | `link_budget.py:213` and `:726` | "the recurrence only ever **raises** power inside a segment" — false. P7: `feasible_budget_fraction.mean = −0.018`, `.min = −18.10` (54 dB below `p⁰`); my recomputation gives `p = 0.4997 W` at θ(τ)=1.5°→θ(t)=0.5°. **This premise is F-1's derivation of `p⁰ = p_max/2`.** |
| D2 | `link_budget.py:748-751` | "largest in-segment loss **0.718 dB** … the gate is currently **non-binding**: outage **0 of 12,000**" — superseded: P7 main arm outage **7.6 %**, required power up to 140.8 kW. |
| D3 | `docs/LINK-BUDGET-NOTES.md:232` | Same claim as a **table entry**: `outage 0.0000`. Instructs ch5 to write it up as a result. |
| D4 | `docs/LINK-BUDGET-NOTES.md:234` vs `probe-p4` | SINR p05/p50/p95 = 11.7/**16.4**/19.0 dB vs measured −5.80/**6.60**/19.61 dB; intra 0.979 vs 0.946. A 9.8 dB gap in the median: at 16.4 dB single-beam renewal pays +3.6 %/0.718 dB, at 6.6 dB it pays ≈ 0 (A3). |
| D5 | `docs/LINK-BUDGET-NOTES.md:249` vs `step.py:167` | mean segment length **6.0 steps** vs the warm-start docstring's measured **L = 5**. |
| D6 | `link_budget.py:254,257` | `ξ_max = 0.35` / `BO = 5 dB` presented as the PA's efficiency and back-off; ξ_max is **unreachable** (max 0.19682) and only `√p_sat/ξ_max` is identified. Stated in no tracked doc. |
| D7 | `link_budget.py:175` vs `:260`, ruling B4 | `p_max` "pinned by the amplifier through `p_sat`" while `p_sat` is **computed from** `p_max`; B4 then records that `p_max` has no source. Circular. |
| D8 | `link_budget.py:270,273` vs ruling C-6 | `P_cir`/`P_BB` cited "You et al. Table II" while `BEAM_TO_RF_CHAIN_IS_SOURCED = False`; the model's partiality (LO + phase shifters excluded) appears only in a code docstring, not in `DEVIATION-REGISTER.md`. |
| D9 | `step.py:998` + `link_budget.py:549` | "INDEPENDENT recomputation" is the identical expression; the F-2 guard reads 1.0 by algebra (A14). |
| D10 | `action_contract.py:408-411` vs `R2-PHYS-PROVENANCE-MATRIX` | Φ₁/Φ₂ carry only "the paper gives `0 < φ1 < φ2`"; `R2_PHYS = NOT_CLOSED` and Φ₁ `UNSOURCED_PRIMARY` are not referenced from the code. |
| D11 | `docs/PREREG-DRAFT.md:145,189` | Still `time_step_s 1.0 (P, Table I)` and `ttt_steps 1 (= 1 s)`; superseded by 30.08 s / 1280 ms. |
| D12 | `interference.py:402-417` | Discloses the link-power-vs-beam-power asymmetry and calls it conservative; the **frozen-wanted vs live-interference** asymmetry (A3) is disclosed nowhere. |
| D13 | endpoint contracts (C1/C2 successor §6, C3-S §5) vs `action_contract.py` | `E_t = 30.08·P_system,t` with **zero** mentions of handover, Φ, segment or anchor, while the reward prices Φ₁/Φ₂. The gap is named only in `FABLE-51-…-2026-09-02.md:241-244`, which says it "**must be disclosed in any paper**". |

## Next steps, in order
1. **Instrument the contrast** (replay only): log `N_lit_beams`, `Σ_b √p_b`, mean/p95 `p_u/p⁰`, mean `segment.age_steps`,
   handover-class and outage counts per arm per step. Then `ΔJ/Δt = 6.5264·Δ(Σ√p) + 0.338·ΔN_beams + 0.200·ΔN_sat`
   **partitions the energy half exactly**; without it "0.5 beams extinguished" and "beams re-anchored" are degenerate.
2. **CPC sensitivity arm** (`start_gain = transmit_gain[uid]` unconditionally) kills A1–A3 at once. If the
   coordinator's advantage survives, it is coordination — report it as a named sensitivity, never as a re-score.
3. **Add the fixtures above (A1–A7, A9)** — none exists today, which is how D1, D2 and D9 survived.
