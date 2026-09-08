# Physics audit — segment-anchored transmit power and the price of a handover (Claude Opus 5, 2026-09-08)

Read-only audit of `src/mcrl/env/`, the successor physical evaluation, the frozen contracts and the thesis
source (`~/papers/modqn-paper-reproduction/thesis-mc/`); numbers recomputed from
`.scratch/multi-catfish-v023-c3s-screen/runs/c3s-20260908-r1/` and `artifacts/probe-p7-*.json`. Answers the
five questions put after `FRESH-ROOT-REVIEW-C3S-V1-CLAUDE-OPUS-2026-09-08.md`.

## A. What is actually anchored, and what moves every step

**Transmit power `p_u` is recomputed every 30.08 s step. What is frozen is the *reference gain*.**
`link_budget.py:379-410` — `recurrence_power_w(start, now) = p⁰·start/now`, eq. (3.12)
`p(t) = p⁰·G^T(θ(τ))/G^T(θ(t))`. Docstring `:387-396`: *"The invariant inside one served segment is the
**product** `p·G^T`, not `p` itself … No target-SINR inversion, no cap, no clamp, no min/max projection"*.

| quantity | within a segment | source |
|---|---|---|
| `G^T(θ(τ))` — the anchor | **frozen** (the only carried state) | `step.py:225-243` `Segment.start_transmit_gain` |
| `p_u(t)` | **recomputed every step** from current geometry | `step.py:770-810` |
| `p_u·G^T(θ(t))` (wanted transmit term) | **frozen** = `p⁰·G^T(θ(τ))` | `step.py:943-957` |
| path/atmospheric/scintillation/shadow/Rician, interference, load, bandwidth | current every step | `step.py:900-970` |
| `p_{s,v}` = max over served users | recomputed every step | `link_budget.py:439-462`, `step.py:886` |

**Re-anchor rule (five declared triggers):** any change of `(norad_id, cell_id)` (`step.py:240-243`), outage,
unserved/no-op, re-entry, episode reset. `step.py:824-862` commits the segment *only if served*, else
`self._segments[uid] = None` → the next served step opens fresh at `p = p⁰` exactly.
**The only in-segment ceiling** is the per-link admission test `p > p_max = 1.65 W` (`link_budget.py:411-436`,
called at `step.py:812-820`) — *outside* the recurrence, per link → outage → segment dropped → forced
re-anchor. Budget `10log10(p_max/p⁰) = 3.010 dB` (`link_budget.py:736-751`).

**⚠ Correction to the red-team review.** Its per-beam bracket `[6.27, 6.78] W` rests on
`link_budget.py:745-750` ("largest in-segment loss **0.718 dB** … outage 0 of 12,000") — **stale**, already
flagged in `docs/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md:397-399`.
`artifacts/probe-p7-main-arm-2026-08-23.json` (frozen scenario, warm start on) reports
`feasible_budget_fraction.max = 0.9942` of the 3.010 dB budget (≈ **2.99 dB**), `outage_rate = 0.076`,
`power_gate_is_binding = true`, `feasible_link_power_w.min = 2.9e-06 W` (current gain 54 dB *above* anchor).
The no-warm-start arm has `outage_rate = 0.001625` — a **47×** difference from segment age alone. Staleness
routinely spans the full budget; the true per-beam bracket is **[6.266, 8.721] W**, and "ΔP → Δbeams safe to
±4 %" is not safe (±16 %).

## B. Is it declared? — three objects, three answers

**B1. The recurrence and its re-anchor rule: DECLARED, including in the abstract.**
`~/papers/modqn-paper-reproduction/thesis-mc/mc-modqn-base.md:239` — *"令 $\tau_{u,s,v}$ 為目前 uninterrupted
served physical link segment 的起始時間步。episode reset、handover、outage、unserved 與 re-entry 都會結束
continuity；新 segment 不保留 inactive-link cache，並以 $p^{0}$ 起始。"* Eqs (3.11)/(3.12) at `:253`/`:265`,
`:268`, abstract `:30`. Also
`docs/DEVIATION-REGISTER.md:195-203` (X-4), `docs/PREREG-DRAFT.md:130`, `docs/MIGRATION-TABLE.md:68`,
`docs/CONTROLLER-FINDINGS-W17-2026-08-22.md:56-63`; `PREREG-FROZEN-2026-08-25-R2.json:30,70` freezes
`beam_power_max_w = 1.65`, `segment_start_power_w = 0.825`.

**B2. The cadence — open- vs closed-loop, and any standards anchor: UNDOCUMENTED.** Zero hits for
`power control` / `功率控制` / `open-loop` / `開迴路` / `closed-loop` / `閉迴路` / `ACM` / `DVB-S2X` /
`link adaptation` across `docs/`, `README.md`, all four `PREREG-FROZEN-*.json` and every
`.scratch/multi-catfish-v023-*` contract; 3GPP is cited only for link-budget terms, antenna gain and D2/TTT.
The project's own disclosure convention (`link_budget.py:277` `BEAM_TO_RF_CHAIN_IS_SOURCED`: *"One active beam
↔ one RF chain is a **modelling assumption**, not a fact"*) is **never applied** to the recurrence.

**B3. Handover = zero joules and the reward/endpoint gap: DECLARED INTERNALLY, ABSENT FROM PAPER AND FROM
EVERY FROZEN CONTRACT.**
`docs/decisions/ADR-004-payload-boundary-time-only-c2.md:78-82` — *"`E_HO` is absent from the primary formula
because UE, gateway, random-access, and other procedure-energy components are outside the declared canonical
payload boundary. The statement is not `physical E_HO = 0`."*; `:175` — *"Not allowed: physical handover
energy is zero…"*. `docs/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:153,168-171` — *"None of the audited sources
closes `E_HO` … Setting `E_HO = 0` could be declared as a lower-bound sensitivity, but cannot be called the
sourced physical primary."* `docs/FABLE-51-…-2026-09-02.md:27-28` — *"the handover class enters only the
legacy `r2` reward field and never delivered bits or network power."*
But `PREREG-FROZEN-2026-08-25-R2.json:3117-3122` declares `r2` as *"identity-based handover, phi1=0.5,
phi2=1.0"* with **no cross-reference to `system_power_w`**; the C1/C2 successor contract §6 and the C3-S
contract §5 (`B_t = 30.08 Σ_u R_ut`, `E_t = 30.08·P_system,t`) define the endpoint with **zero** mentions of
handover, phi, joule, segment or anchor. No assumptions/limitations/threats-to-validity artifact exists
anywhere. The thesis says only `ch6-conclusion.md:19` — *"能量效率定義與環境設定也包含理想化假設"*.

**B4. The renewal lever itself: already named internally, with an unmet disclosure obligation.**
`docs/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md:241-244` (repeated `:322-324`) — *"the oracle
switches more often, not less, because handover carries no physical cost in this simulator and a fresh segment
on a better-placed beam usually projects a higher rate than an aged low-received-power segment. This is a
legitimate consequence of the frozen physics **but must be disclosed in any paper**."* Same doc `:20-28`:
*"The simulator contains exactly one action-controlled physical carrier of history: the link power segment."*

**Classification of the combined mechanism: IMPLIED.** Every component is declared somewhere; the
*combination* (anchored power × zero-joule handover ⇒ an EE-positive free renewal option) is named in exactly
one internal design document and is absent from all four frozen PREREGs, both V0.23 endpoint contracts, and
the paper.

## C. Energy accounting as implemented — no joules are charged for a handover

Grep of `src/`, `tests/`, `scripts/` for `signall?ing|switching cost|handover energy|joules? per handover`:
**zero hits.** `HANDOVER_COST` (`action_contract.py:414-418`; `PHI1=0.5` `:408`, `PHI2=1.0` `:411`, both category
**S** = self-chosen) has one call site — `step.py:1101` `r2_handover=-HANDOVER_COST[handover]`, in `_rewards`.

```
ξ_{s,v} = min{ξ_max, ξ_max·√(p_{s,v}/p_sat)}          link_budget.py:468-495   (3.15a)
P^p_{s,v} = p/ξ = √(p·p_sat)/ξ_max = 6.5264√p         link_budget.py:496-520   (3.15)
P^f = Σ_s (N^act_s·P_cir + 1{N^act_s>0}·P_BB)         link_budget.py:521-548   (3.16a)
P^N = P^f + Σ_s Σ_v z_{s,v}·P^p_{s,v}                 link_budget.py:549-587   (3.16)
p_{s,v} = max_{u served} p_{u,s,v}   (never a sum)    link_budget.py:439-467
R_u = (B^w/U_{s,v})·log2(1+γ_u);  E_t = Δt·P^N,       link_budget.py:590-620   (3.14)
  Δt = 47×0.640 = 30.08 s                             constants.py:77; runner:960-982
```

`ξ_max = 0.35`, `BO = 5 dB`, `p_sat = 5.2178 W`, `P_cir = 0.338 W/beam`, `P_BB = 0.200 W/satellite`.
**An inactive beam costs exactly nothing** — absent from both the supply array and the per-satellite tally
(`beam_power_w` `:441-446`; `fixed_power_w` `:526-540`). **The PA never reaches saturation**:
`p ≤ p_max = 0.316·p_sat`, so `ξ ≤ 0.197 < ξ_max` always and the model sits permanently on the `√p` branch.
Per-beam total = `6.5264√p + 0.338` ∈ **[6.266 W at p⁰, 8.721 W at p_max]**. The successor runner and the C3-S
screen accumulate `Δt × system_power_w` only (`v023_c1c2_successor_physical_runner.py:960-982`); the C3-S
objective is `nominal_score = total_bits − η_ref·total_energy_j` (`c3s_policy.py:230-235`) — no handover term.

## D. What changes under continuous per-step power control (CPC)

Define CPC as re-anchoring every step (`start_gain = transmit_gain[uid]` unconditionally): `p ≡ p⁰` for every
served link and `wanted = p⁰·G^T(θ(t))·…`. Then:

1. **The denominator becomes exactly a lit-beam counter**: `P^N = 6.2659·N_beams + 0.200·N_act_sat`; all
   per-beam power variation vanishes (H5 of the review becomes exact rather than approximate).
2. **The renewal lever disappears identically** — no stale anchor to refresh, and the incumbent is priced at
   its own current geometry, so stay-vs-move becomes a fair comparison.
3. **BASE**: mis-specified but not catastrophically — the native 112-d state never carried the anchor
   (`state_encoding.py:29-60`) and `_candidate_sinr` prices **every** candidate, incumbent included, at `p⁰`
   and current gain (`step.py:1209-1218`), already hiding the incumbent's anchor advantage. Direction: BASE's
   EE rises slightly, its ranking barely moves.
4. **The coordinator**: loses the renewal component outright, keeps beam extinction, interference removal and
   bandwidth re-sharing. Direction strictly down; magnitude unbounded from the receipts (see below).
5. **C1/C2 (R7, stage-C ladder) — the load-bearing consequence.** `ee_axis_state.py:49-53` defines the C2
   temporal block as exactly `previous_recurrence_power`, `current_to_segment_start_gain_ratio`, `segment_age`,
   `missing_incumbent`; `:305-336` builds feature 1 as `current_gain/start_gain` = `p⁰/p`. Under CPC feature 0
   ≡ `p⁰/p_max`, feature 1 ≡ 1.0, feature 2 carries no power information — **three of the four become
   constants.** FABLE-51:20-28 says as much in prose: the power segment is the simulator's *only*
   action-controlled carrier of history. **C2's declared channel is the anchor**, so every C1/C2 result — not
   only C3-S — is conditional on this modelling choice.
6. **C3's additive negatives are unaffected** in direction (load balance, which the physics forbids: per-beam
   max, no saturation region, no occupancy ceiling).

**Analytic magnitude (no simulation needed).** With staleness `r = G^T(θ(τ))/G^T(θ(t)) ≥ 1`,
`d lnEE/d ln r = γ/((1+γ)ln(1+γ)) − ½·6.5264√p/(6.5264√p+0.338)`; the second term is **0.4730** at `p⁰`, so
renewal *raises* EE whenever `log2(1+γ) > 2.52 bit/s/Hz`. The panel's realised per-user rate is **3.059e8 bit/s**
on `B^w/U = 166.667/U` MHz, i.e. **SE ≈ 3.67 (U=2) – 4.59 (U=2.5) bit/s/Hz** — well above threshold. Renewing
**one** beam yields, at SE = 4.59: +0.79 % at 0.2 dB, **+2.78 % at 0.718 dB**, +3.84 % at 1.0 dB, **+10.6 % at
the full 3.010 dB**. The staleness reproducing the reported pooled **+2.883 %** on one beam is **0.744 dB**.

**Receipts-only bound.** Pooled BASE mean power 260.53 W is consistent with `N ∈ [29.8 (all maximally stale),
41.4 (all fresh)]` lit beams; renewing every beam would take 260.53 → 187.5 W, i.e. **−28.0 %**, and the
observed pooled `dJ = −1.238 %` is **4.4 % of that ceiling**. The receipts therefore **cannot exclude that
100 % of the energy half is renewal** — and the bits half (56.2 % of the log-EE gain; my recomputation:
dEE +2.8832 % FULL / +2.9218 % LITE, dBits +1.609 %, dJ −1.238 %) is renewal-capable too, since re-anchoring
onto a better-aligned cell raises the wanted transmit gain without bound.

**The receipts contain neither `N_beams` nor `Σ√p`, so "fewer beams" and "lower p per beam" are exactly
degenerate in the recorded scalar** (per-step fields: `bits_hex`, `energy_j_hex`, `opportunities`, `served`,
`step_index`). I did reproduce the dwell-phase table exactly (phase 0/1/2/3: dEE +1.348/+1.748/+3.921/+9.262 %,
P_BASE 377.8/270.1/205.4/170.8 W); the per-step trace is a clean **period-4 sawtooth**, power resetting at
every dwell boundary — the epochal group re-anchoring already on record from the 2026-08-31 C2 gate finding.

### Cheapest decisive tests (in order)

- **T-A (minutes, exact, no new physics).** Replay **one** unit's three arms logging two extra per-step
  scalars, `N_lit_beams` (int) and `Σ_b √p_b`; then `ΔJ/Δt = 6.5264·Δ(Σ√p) + 0.338·ΔN_beams + 0.200·ΔN_act_sat`
  **partitions the energy half exactly** into extinction vs renewal. Deterministic, verifiable bit-for-bit
  against `energy_j_hex`, TEST untouched — cheaper and more decisive than the review's T1/T2 on that channel.
- **T-B (same replay).** Also log per arm per step: mean and p95 of `p_u/p⁰`, mean `segment.age_steps`, and
  `HandoverClass` counts. Under H1, BASE's `p95(p_u/p⁰)` climbs through the dwell phase while FULL's stays at
  1.0. Settles the bits half.
- **T-C (one sub-panel, sensitivity arm).** Re-run BASE + LITE with CPC (`start_gain = transmit_gain[uid]`
  unconditional at `step.py:789-803`, `:835-846`). If dEE survives, H1 is refuted. This changes the physics, so
  report it as a named sensitivity, never as a re-scoring of the sealed screen.

## E. Verdict

**(ii) — a simplification a reviewer will read as an artifact; disclosure alone does not cure it.** Explicitly
**not (iii)**: not a bug — the thesis declares it in the abstract and in eqs (3.11)–(3.12), rulings C-2/F-1 are
explicit, and the code implements exactly what is declared. Not (i) either, because no standard supports the
*cadence*. In the NR downlink there is no per-UE fast power control at all (PDSCH EPRE is semi-statically
configured against CSI-RS; adaptation is by MCS/rank, TS 38.214 §4.1); on satellite forward links DVB-S2X holds
carrier power constant and adapts MODCOD per frame (EN 302 307-2, ACM); where per-carrier power control does
exist (NR/NTN uplink TS 38.213 §7 with TR 38.821's adaptations; gateway ULPC for rain fade) the loop runs per
transmission occasion or per second, bounded below only by the RTT — 10⁻³–10⁰ s. *(Clause numbers to be checked
against the published specs before they enter the paper.)* This model updates `p` every 30.08 s but refreshes
its **reference** only at an association change — here a mean of several steps, ≈120 s at the dwell period.
**No standard has a power-control reference refreshed only by handover.** Combined with a denominator that
charges nothing for that handover while the reward charges Φ₁/Φ₂, the model makes re-association the sole, free
power-control event, and the +2.9 % is measured in precisely that gap. The project reached the same conclusion
on 2026-09-02; the disclosure is still unmet.

**The sentence the paper must carry** (place it in §3 next to (3.12), not in a limitations footnote):

> Transmit power follows the open-loop angle recurrence (3.11)–(3.12): within one uninterrupted served
> segment the product `p·G^T` is held at its segment-start value, so the reference gain `G^T(θ(τ))` is
> refreshed only when the association changes, and the energy denominator (3.16) charges no signalling or
> procedure energy for that change. Re-association is therefore the only power-control event in this model and
> is free in the reported energy efficiency, while the training reward prices it at φ₁/φ₂; the gains reported
> in §X are measured in that gap and would shrink, by an amount we have not quantified, under continuous
> per-step power control.

> 中文版：發射功率依式 (3.11)–(3.12) 的開迴路角度遞推：同一段未中斷服務區段內 `p·G^T` 維持於段起始值，參考
> 增益 `G^T(θ(τ))` 僅在關聯改變時重設；式 (3.16) 的能耗分母不計任何信令或程序能量。故重新關聯是本模型唯一的
> 功率控制事件，且在所報告的能量效率中不計代價，而訓練獎勵卻以 φ₁/φ₂ 計價；第 X 節的增益即量測於此落差之
> 中，若改採每步連續功率控制，其量值將縮減且縮減幅度尚未量化。

Two further disclosures are owed: the stale `0.718 dB` / `outage 0 of 12,000` figures in
`link_budget.py:740-751`, and that C2's entire temporal state block is this same anchor.
