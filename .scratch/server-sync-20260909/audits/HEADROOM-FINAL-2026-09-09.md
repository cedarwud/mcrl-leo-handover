Report written to `/home/sat/mcrl-v023-codex-audits/parallel-20260909/HEADROOM-CEILING-2026-09-09.md`.

---

# The coordination headroom ceiling: how much of the corrected physics' infeasibility is interference-driven?

`DIAGNOSTIC_NOT_CLAIM`. 2026-09-09.

This report bounds the maximum value any coordination layer could have under the corrected causal ACM. It is a re-evaluation, not a search: no learner was run, no arm was compared, no threshold, seed or price was touched.

---

## 1. Interference-free counterfactual — the headline

Every wanted-link SINR was recomputed with the interference term set to zero and nothing else changed. **VERIFIED.**

### Regime R0 (`a-r0`, `r* = 50 Mbit/s`), 14,000 user-steps

| quantity | value | status |
|---|---|---|
| user-steps in the evaluation | **14,000** | VERIFIED |
| `rate_target_feasible = false` | **5,714 (40.814 %)** | VERIFIED |
| of those, feasible once `I = 0` | **5,218** | VERIFIED |
| **share of infeasible user-steps rescued** | **91.320 %** | **VERIFIED** |
| share of all user-steps rescued | 37.271 % | VERIFIED |
| feasible user-steps: before → after | 59.186 % → **96.457 %** | VERIFIED |
| user-steps lost by zeroing interference | 0 | VERIFIED |

The counterfactual is read two ways and both give the identical set. Holding the solved power fixed and deleting `I` from the denominator rescues 5,218 user-steps; re-solving the power control from scratch against `I = 0` (`p = min(p_max, Γ·N₀W/G)`, i.e. the true unconstrained ceiling) rescues **the same 5,218**. VERIFIED. The two coincide because 93.675 % of failing transmissions already sit exactly at the 1.65 W cap, where re-solving cannot move them.

**Correction to the framing supplied with the task.** The receipt records **14,000** user-steps and **5,714** infeasible ones, not 28,000 and 11,428. The share, 40.814 %, is identical; only the denominator was doubled. VERIFIED by direct count over `steps[*].arms[*].rate_target_feasible` (100 users × 10 anchors × 14 arms).

### `m_tx` moving off `NO_MODE` (transmission census, arm-weighted)

| quantity | R0 | status |
|---|---|---|
| transmissions in the census | 3,108,768 | VERIFIED (matches receipt exactly) |
| `m_tx = NO_MODE` | 2,379,920 (**76.5551 %**) | VERIFIED (matches receipt exactly) |
| **move off `NO_MODE` at `I = 0`** | 1,147,184 (**48.203 % of `NO_MODE`**) | **VERIFIED** |
| `NO_MODE` share after | **39.654 %** | VERIFIED |

The 62 % figure in the task brief is one arm at one anchor (`E1_U1`, step 0: 14,224 / 23,040 = 61.7 %). Over the whole 14-arm × 10-anchor census the sealed receipt's own number is 76.5551 %, reproduced here to the unit.

### Second and third regimes

Same world, same anchors, same committed assignments; only the sealed rate target changes. Selection was not re-run, so these re-price the physics at the R0 assignment (see HONEST LIMITS).

| | R7 (`r* = 25 Mbit/s`) | R0 (`50`) | R1 (`100`) |
|---|---|---|---|
| infeasible user-steps | 3,434 (24.529 %) | 5,714 (40.814 %) | 8,770 (62.643 %) |
| **rescued by `I = 0`** | **95.166 %** | **91.320 %** | **76.864 %** |
| feasible after | 98.814 % | 96.457 % | 85.507 % |
| `NO_MODE` share before | 98.181 % | 76.555 % | 63.531 % |
| `NO_MODE` moved off | 39.101 % | 48.203 % | 67.960 % |
| `NO_MODE` share after | 59.791 % | 39.654 % | 20.355 % |

All VERIFIED. The ceiling is high in all three and rises as the target falls.

---

## 2. Interference-to-noise ratio

`I / (N₀W)` in dB, per transmission, arm-weighted. `N₀W = 5.5754 × 10⁻¹³ W` (166.667 MHz per colour). R0. **VERIFIED.**

| percentile | all | feasible tx | infeasible tx |
|---|---|---|---|
| p05 | −30.37 | −31.56 | **+3.02** |
| p25 | −14.38 | −17.64 | +9.95 |
| **p50** | **−1.92** | **−6.22** | **+13.33** |
| p75 | +8.49 | +2.22 | +15.73 |
| p95 | +15.92 | +11.26 | +17.90 |

| share of transmissions | all | feasible | infeasible |
|---|---|---|---|
| `I/N < −10 dB` | 32.104 % | 40.177 % | **1.877 %** |
| `I/N < 0 dB` | 54.275 % | 67.906 % | **3.236 %** |
| `I/N ≥ 0 dB` | 45.725 % | 32.094 % | **96.764 %** |
| `I = 0` exactly | 0.000 % | — | — |

The premise behind the question — "if interference sits far below thermal noise for most users, the ceiling will be near zero" — does not hold in this physics. Interference is below noise for a slim majority of *all* transmissions, but for the transmissions that actually fail it is **above** noise 96.764 % of the time and sits 13.3 dB above it at the median. The two populations are cleanly separated, which is why the item-1 ceiling is large. Median R7 `I/N` (all) is −4.17 dB and R1 is +3.51 dB; the infeasible-population medians barely move (+13.24, +13.45 dB). VERIFIED.

Interference tax `10·log₁₀((N+I)/N)` — the extra transmit power interference demands: median **2.157 dB** over all transmissions, median **13.526 dB** over failing ones (p25 10.366, p75 15.846). VERIFIED.

---

## 3. Why each infeasible user fails

R0. **VERIFIED.**

### Per failing transmission (655,266 weighted)

| class | share | at the 1.65 W cap |
|---|---|---|
| interference-limited (`I = 0` clears Γ) | **95.590 %** | 93.383 % |
| noise-limited (`I = 0` still short) | **4.410 %** | 100.000 % |
| mode-infeasible (no ACM mode reaches `r*` at this occupancy) | **0.000 %** | — |

### Per infeasible user-step (5,714)

| class | count | share |
|---|---|---|
| interference-limited | 5,206 | **91.110 %** |
| noise-limited | 496 | **8.680 %** |
| not allocated at every boundary (no failing transmission; fails the "present at all 48 boundaries" rule) | 12 | 0.210 % |
| mode-infeasible | 0 | 0.000 % |

R7: 95.02 % / 4.83 % / 0.15 %. R1: 76.70 % / 23.14 % / 0.16 %. VERIFIED.

### On the requested third category, "cap-limited"

It is **not separable in this physics, and that is a measurement, not an omission.** VERIFIED:

* **0.000 %** of feasible transmissions sit at the cap. The rate-target fixed point stops at exactly `Γ·(N+I)/G`, so a link that can reach its target stops strictly below 1.65 W.
* **93.675 %** of failing transmissions sit exactly at the cap; the remaining 6.325 % are within solver tolerance of it (the engine takes one post-loop fixed-point update plus a `nextafter` clearance nudge, so a link can land a few parts in 10⁹ under Γ without being at the cap).

So the cap binds on essentially every failing transmission by construction. "Cap-limited" is a property of the whole infeasible population, not a class disjoint from noise- and interference-limited; splitting it out would double-count. Occupancy is not binding either: maximum observed beam occupancy is **6** against a 12-user ceiling, weighted mean **2.016**, and **0.000 %** of transmissions have no ACM mode able to carry `r*` at their occupancy. VERIFIED.

---

## 4. Where the interference comes from

Interference-limited population only (626,369 weighted transmissions, R0). **VERIFIED.**

| quantity | value |
|---|---|
| mean share of `I` from the **same satellite, adjacent beam** | **98.879 %** |
| mean share from **other satellites** | 1.121 % |
| transmissions where same-satellite interference is >50 % of `I` | 98.959 % |
| **mean share of `I` carried by the single strongest aggressor** | **74.251 %** |
| top-1 share: p25 / p50 / p75 / p95 | 55.905 % / 75.425 % / 96.081 % / 99.988 % |
| top-1 carries >50 % of `I` | 84.950 % |
| top-1 carries >90 % of `I` | 33.830 % |
| the top-1 aggressor is on the same satellite | 98.950 % |
| non-zero contributors per victim: p25 / p50 / p75 / p95 | 13 / 14 / 15 / 29 |
| **removing only the single strongest aggressor restores feasibility** | **76.444 %** |

R7: 86.766 % fixed by removing the top-1 alone. R1: 57.800 %. VERIFIED.

This is a single-strong-interferer regime, not an aggregate-of-many one: a victim typically has ~14 non-zero co-colour aggressors, but one of them — almost always an adjacent beam on the victim's own satellite — carries three quarters of the power, and deleting it alone clears the target for roughly three quarters of the interference-limited population.

---

## 5. Energy sensitivity

The PA model is `P_supply = √(p·p_sat)/ξ_max`, integrated with the engine's own trapezoid over 48 boundaries. **The reconstruction was checked against the sealed receipt's `energy.pa_j` for all 140 arm-anchors: maximum relative error 1.49 × 10⁻¹³.** VERIFIED.

Recoverable energy = PA energy actually burned at the cap minus PA energy at the power those links would need if their interference were removed (`p = Γ·N₀W/G`), over the interference-limited population only.

| quantity | R7 | R0 | R1 |
|---|---|---|---|
| PA energy, all arm-anchors | 657,274.7 J | **862,198.8 J** | 1,186,790.2 J |
| total energy (PA + circuit + baseband), R0 receipt | — | 941,549.1 J | — |
| **recoverable joules** | **107,584.7 J** | **228,111.5 J** | **329,782.1 J** |
| share of PA energy | 16.37 % | **26.457 %** | 27.79 % |
| share of total energy (R0) | — | **24.227 %** | — |
| per arm-anchor (R0) | — | 1,629.4 J | — |

All VERIFIED. This is real recoverable energy under the corrected ACM: of the interference-limited transmissions, **93.383 %** sit at the 1.65 W cap and **83.746 %** carry `m_tx = NO_MODE` — full power, no mode, and still in the availability denominator. VERIFIED.

---

## 6. How marginal is the rescued population?

Because a link that misses Γ by 10⁻⁹ dB counts as infeasible, the headline was stress-tested. R0, **VERIFIED**:

* Shortfall of failing transmissions below Γ: p25 1.113 dB, **p50 2.724 dB**, p75 5.183 dB, p95 10.294 dB. 7.788 % are below 0.1 dB and 22.812 % below 1 dB.
* Worst shortfall across a rescued user-step's failing transmissions: **p50 3.644 dB**; 15.002 % are below 0.5 dB, 43.796 % below 3 dB.
* Not-rescued (noise-limited) user-steps: p50 worst shortfall 6.542 dB.

So the rescued population is not an artefact of borderline arithmetic: the median rescued user-step needs about 3.6 dB of interference relief, and only about a seventh of it is within half a dB of the target already.

### Partial-suppression ladder (shape, not a receipt value)

Uniformly attenuating `I` and re-testing feasibility with a single AND-over-slots convention. This convention reproduces the committed rule for 90 of 140 arm-anchors but not the 50 scored through the dense batch path, so it reads 57.436 % at 0 dB against the receipt's 59.186 %. Read the *shape*, not the levels.

| suppression | feasible user-steps | share |
|---|---|---|
| 0 dB (as-is) | 8,041 | 57.436 % |
| −3 dB | 10,365 | 74.036 % |
| −6 dB | 11,715 | 83.679 % |
| −10 dB | 12,763 | 91.164 % |
| −20 dB | 13,451 | 96.079 % |
| −∞ (`I = 0`) | 13,504 | 96.457 % |

---

## 7. Reproduction and validation

The measurement is a re-run of the engine's own `a-r` TDM core (`src/mcrl/physics_v025/batch.py::_evaluate_ar_tdm_catalogue_core`) with per-transmission recording added and nothing in the physics changed, against the committed configurations carried in the sealed receipt.

* Workspace: `/home/sat/mcrl-v025-headroom-ws`, `git archive 75c5c78c` from `/home/sat/mcrl-v025-codex-ws-engine`. Nothing was written to any protected path.
* World tape rebuilt from the frozen provider: domain `V025_SMOKE/world/1`, digest `90cc7f6594c95d0baaf517796b195d1785c3ef4a76ffafb9100b4be635bd2270`.
* Receipt read: `.tmp/stage4h-formal/smoke/a-r0-world-1.json` (10 anchors, 14 arms, `r* = 50 Mbit/s`, 100 users).
* Field `realised`, 48 boundaries, `fading_quantile_alpha = 0.10`, `circuit_power_per_active_chain_w = 0.338` — the settings the committed `StepEvaluator` uses.

**Exact agreement with the sealed receipt, all 140 arm-anchors:** per-user `rate_target_feasible` vector, `rf_transmission_observations`, `rf_cap_hits`, the full `m_tx` histogram, and `energy.pa_j` (to 1.5 × 10⁻¹³ relative). VERIFIED.

One engine detail had to be reproduced to get there, and it is worth recording: **two different scoring conventions appear inside one receipt.** Configurations scored through the dense batch path use a chunk-wide refined slot grid and OR feasibility across slots within a boundary (50 of 140 arm-anchors); configurations scored through the scalar object path use their own slot partition, AND across slots, and the `Γ·(1 − 10⁻¹⁰)` tolerance from `architectures._target_feasibility` (90 of 140 — every `BASE`-committed row). Each configuration here is scored both ways and the convention that reproduces the receipt bit-for-bit is the one kept. This is reported as an observation about the engine, not a defect claim; it is out of scope for this diagnostic.

---

## HONEST LIMITS

Every number above covers exactly one world: **`V025_SMOKE/world/1`**, tape digest `90cc7f65…`, the quarantined development smoke world — not a formal world and not the `V025_PROBE` namespace the matrix runs on. It covers **10 anchors** (step indices 0–3 across the three reference carriers `nearest-eligible`, `stay-if-possible`, `random-masked`), **14 arms**, **100 users**, hence **14,000 user-steps** and **3,108,768 transmissions** per regime, at 48 boundaries per anchor. The R0 numbers are validated against the sealed receipt to the unit; the R7 (`25 Mbit/s`) and R1 (`100 Mbit/s`) numbers hold the R0-committed assignments fixed and re-price only the sealed rate target — **what a selector would actually commit under those targets is UNKNOWN**, so R7 and R1 are a sensitivity of the physics, not of the system. Regimes R2 (150 users), R3 and R4 (circuit power) were **not run: UNKNOWN**. The `a′-r` FDM architecture was **not run: UNKNOWN**. Whether these shares hold on the formal worlds 1–10, or on any world other than this one, is **UNKNOWN — a single world cannot show it**. The interference-free counterfactual deletes `I` for the victim while leaving every aggressor's power untouched; that is the intended absolute ceiling and no achievable coordination scheme can exceed it, but nothing here measures what any particular scheme would actually reach, and this report makes no claim about whether C3 will or will not work.
