# EE causal map — Multi-Catfish MCRL LEO simulator

Read-only analysis. Repo: `/home/u24/papers/mcrl-leo-handover`. All line references are
against the working tree at the time of reading. Code is authoritative; where the V0.3
contract or a docstring disagrees with the code, that is flagged explicitly.

---

## 0. The endpoint, as actually computed

`docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md:15-19`

```
eta^N = B / E,   B = sum_t sum_u R_u(t) * dt,   E = sum_t P^N(t) * dt
```

Implemented, exactly, in `src/mcrl/runtime/ee_axis_evaluation.py:155,178,183-184,209-211`:

```python
interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)   # 155
system_rate = float(math.fsum(float(value) for value in rates))                    # 178
total_bits   += system_rate   * interval_s                                         # 183
total_energy += system_power  * interval_s                                         # 184
ratio_of_sums_ee_bits_per_j = total_bits / total_energy                            # 209-211
```

* `rates` is `StepOutcome.link_rate_bps` — per-user realised rate, **0 when unserved**
  (`src/mcrl/env/step.py:958-962`).
* `system_power` is `StepOutcome.system_power_w` — the single global `P^N` scalar.
* `dt = EphemerisConfig.time_step_s = DECISION_STEP_S = 47 * 0.640 = 30.08 s`
  (`src/mcrl/env/ephemeris.py:663`, `src/mcrl/env/constants.py:73-92`).
* Episode horizon `H = STEPS_PER_EPISODE = 10` (`src/mcrl/env/constants.py:102`).

`dt` is a constant and cancels out of any ratio; it is carried explicitly so
mismatched time bases cannot be compared silently.

---

## 1. DELIVERED BITS — the exact per-step formula

### 1.1 Formula chain

`src/mcrl/env/step.py:957-962`:

```python
load = resolution.user_beam_load()                      # 957   U_{b_u}
rate = np.where(
    resolution.served,
    shannon_rate_bps(sinr, beam_load=load, bandwidth_hz=physics.beam_bandwidth_hz),
    0.0,
)                                                        # 958-962
```

`src/mcrl/env/link_budget.py:590-616` — eq. (3.14):

```python
shared = np.where(load > 0.0, bandwidth_hz / np.maximum(load, 1.0), 0.0)
return shared * np.log2(1.0 + sinr)
```

So, **per user per step**:

```
R_u(t) = x_u(t) * (B^w / U_{b_u}(t)) * log2(1 + gamma_u(t))          bits/s
bits_u(t) = R_u(t) * dt                                              bits
```

with

* `x_u(t) ∈ {0,1}` = `resolution.served[u]` — selected a masked action AND the link is
  power-feasible (`src/mcrl/env/service.py:222-251`).
* `B^w = BANDWIDTH_HZ / FREQUENCY_REUSE_FACTOR = 500 MHz / 3 = 166.667 MHz`
  (`src/mcrl/env/link_budget.py:21-29`). Constant.
* `U_{b_u}(t)` = **post-feasibility** eligible load of the beam serving `u`, keyed by
  `(norad_id, cell_id)` (`src/mcrl/env/service.py:164-182`, `112-113`).
* `gamma_u(t)` = realised link SINR, eq. (3.13), `src/mcrl/env/step.py:938-955`.

### 1.2 The SINR numerator and denominator

`src/mcrl/env/step.py:938-955`:

```python
wanted[uid] = ( link_power[uid]                          # p_{u,s,v} — OWN link power
              * field_now.transmit_gain[uid, column]     # G^T(theta_{u,s,v}(t))
              * field_now.path_gain[uid, column]         # 10^(-L/10), L = L_f+L_g+L_c+L_s
              * field_now.fading_gain[uid, column]       # Rician draw h
              * _RX_GAIN_MAX_LINEAR )                    # G^R on boresight, 35 dBi
sinr = np.where(resolution.served,
                wanted / (interference.total_w + physics.noise_power_w), 0.0)
```

* `_RX_GAIN_MAX_LINEAR` = `10^(35/10)` (`src/mcrl/env/step.py:115`, antenna.py:148).
* `sigma^2 = k_B * T_sys * B^w = 5.575e-13 W` (`src/mcrl/env/link_budget.py:367-371`),
  constant, independent of load.
* `I = I^intra + I^inter` (`src/mcrl/env/interference.py:349-399`), summed over the
  **global** radiating set, gated by `z` (membership) and by colour, never weighted by
  load (`interference.py:10-14`).

Note the deliberate asymmetry documented at `src/mcrl/env/interference.py:412-417`: the
**wanted** term uses `p_{u,s,v}` (the user's own recurrence power) while the
**interference** terms use `p_{s,v}` (the beam power = max over that beam's served
users). One user's action therefore cannot raise another user's *wanted* signal, only
their *interference* and their *bandwidth share*.

### 1.3 Which inputs are action-dependent, which are persistent state

| Variable | Source | Depends on current action? | Depends on persistent state from past actions? |
|---|---|---|---|
| `x_u` served flag | `service.py:222-251` | YES (which action; no-op) | YES (feasibility uses the segment; see below) |
| `B^w` | constant | no | no |
| `U_{b_u}` | `service.py:251` | YES — **joint**: every user's action this step | no |
| `p_{u,s,v}` (link power) | `step.py:797-803` | YES via `G^T(theta(t))` of the chosen candidate | YES via `segment.start_transmit_gain` = `G^T(theta(tau))` |
| `G^T(theta(t))` | `antenna.py:89-120` | YES (chosen cell/satellite) | no — pure geometry |
| `path_gain` (L_f, L_g, L_c) | `link_budget.py:340-359,664-691` | YES (chosen satellite: slant, elevation) | no — pure geometry |
| `L_s` shadow (dB) | `link_budget.py:151-169` | keyed per `(event, step, norad)` | no |
| Rician `h` | `link_budget.py:297-317` | keyed per `(event, step, norad)` | no |
| `I` interference | `interference.py:349-399` | YES — **joint** over all users' actions this step | no (no lag in the physics) |
| `sigma^2` | constant | no | no |

**Key structural fact:** interference, load and activation are *purely instantaneous* in
the physics. The only physical quantity that carries information from a past action into
a future step's bits is the **power segment** (§3).

---

## 2. NETWORK ENERGY — every term

### 2.1 Formula chain

`src/mcrl/env/step.py:965-986`:

```python
efficiency = pa_efficiency(beam_power, max_efficiency=..., saturation_power_w=...)  # 972-976
supply     = supply_power_w(beam_power, efficiency)                                 # 977
beams_by_satellite = np.array([sum(1 for key in beam_keys if key[0]==norad)
                               for norad in sorted({key[0] for key in beam_keys})]) # 978-984
fixed       = fixed_power_w(beams_by_satellite)                                     # 985
total_power = system_power_w(supply, beams_by_satellite)                            # 986
```

`src/mcrl/env/link_budget.py:549-587` (eq. 3.16), `521-546` (eq. 3.16a),
`496-518` (eq. 3.15), `468-493` (eq. 3.15a), `439-465` (3.12a preamble):

```
p_{s,v}      = max_{u : x_{u,s,v}=1} p_{u,s,v}                     # beam_power_w
xi_{s,v}     = min( xi_max , xi_max * sqrt(p_{s,v}/p_sat) )        # pa_efficiency
P^p_{s,v}    = p_{s,v} / xi_{s,v}                                  # supply_power_w
P^f          = sum_s ( N^act_s * P_cir  +  1{N^act_s>0} * P_BB )   # fixed_power_w
P^N(t)       = P^f + sum_{s,v} z_{s,v} * P^p_{s,v}                 # system_power_w
E            = sum_t P^N(t) * dt
```

Constants: `xi_max = 0.35`, `p_sat = p_max * 10^(BO/10) = 1.65 * 10^0.5 = 5.2180 W`,
`P_cir = 0.338 W`, `P_BB = 0.200 W`, `p_max = 1.65 W`, `p0 = p_max/2 = 0.825 W`
(`link_budget.py:175,213,254,257,260,270,273`).

### 2.2 Closed form of the PA supply term (verified numerically)

On the live path `p_{s,v} <= p_max = 1.65 W < p_sat = 5.218 W`, so the `min` in eq.
(3.15a) **never binds** and

```
P^p_{s,v} = p / (xi_max * sqrt(p/p_sat)) = ( sqrt(p_sat) / xi_max ) * sqrt(p)
          = 6.526404 * sqrt(p_{s,v})   [W]
```

Checked numerically (`link_budget.pa_efficiency`/`supply_power_w`):
p = 0.825 -> 5.9279 W; p = 1.00 -> 6.5264 W; p = 1.65 -> 8.3833 W.

**Consequence:** network energy is a **concave, square-root** function of beam power.
Doubling a beam's radiated power costs only 1.414x its supply power. Conversely the
*dominant* per-beam cost is the fixed floor of lighting the beam at all
(5.93 W at `p0`, plus 0.338 W circuit), not the marginal power on top.

### 2.3 Term-by-term action sensitivity and sharing

| Term | Formula / cite | Which action choices change it | Shared? |
|---|---|---|---|
| **Angle-recurrence link power** `p_{u,s,v} = p0 * G^T(theta(tau)) / G^T(theta(t))` | `link_budget.py:379-408`, applied `step.py:797-803` | The user's own choice of (satellite slot, beam slot) sets `theta(t)`; whether the choice *continues* the previous association sets `theta(tau)` (hold) or resets it to `theta(t)` (switch -> `p = p0` exactly) | Per user. Not itself charged — it enters E only through the beam max. |
| **Per-beam max aggregation** `p_{s,v} = max_u p_{u,s,v}` | `link_budget.py:439-465`, `step.py:879-881` | Any user joining beam `(s,v)` with `p_u > current max` raises the whole beam's power | **SHARED**: raises `P^p_{s,v}` (in E) and the beam's interference footprint for every co-colour victim |
| **PA supply power** `P^p = p/xi = 6.5264*sqrt(p)` | `link_budget.py:468-518` | Only via `p_{s,v}` above, and via the beam existing at all | Per beam; the beam is shared by its users |
| **Beam circuit power** `N^act_s * P_cir` (0.338 W/beam) | `link_budget.py:521-546` | Lighting a *new distinct* `(s,v)` pair adds 0.338 W; darkening one removes it. `z = 1{U_{s,v} > 0}`, derived, never chosen (`service.py:132-147`) | **SHARED**: a step-level count over all users' choices |
| **Per-satellite baseband** `1{N^act_s>0} * P_BB` (0.200 W/satellite) | `link_budget.py:527,545` | Being the *first* user on a previously dark satellite adds 0.200 W | **SHARED** across that satellite's beams and users |
| Anything else | — | **No other term exists.** No handover energy, no activation transient, no per-satellite or per-beam power cap on the live path (`link_budget.py:196-202,425-427`; `HOBS_LEO_MAX_TRANSMIT_POWER_W` is a check, not a cap) | — |

Measured scale (`artifacts/probe-p2-2026-08-23.json`, 100 users, N=4 arm):
`system_power_w` p50 ~= 268 W, min 228 W, max 311 W, swing 83 W per episode
=> `E` per step ~= 268 * 30.08 ~= 8.06 kJ.

**The externality is real and one-directional:** `P^N` is a single global scalar
appearing in every user's `r1 = R_u/P^N` (`energy_efficiency.py:251-262`,
`step.py:1064`). One user lighting a fresh beam charges ~6.27 W (5.93 PA + 0.338 cir)
against *everyone's* EE, and ~+0.20 W more if the satellite was dark.

---

## 3. PERSISTENT STATE — what survives a decision step and can be changed by the action

`StepEnvironment` owns exactly six mutable per-episode fields (`step.py:384-403`,
committed at `step.py:591-603` and `step.py:848-855`, `1084-1087`):

| # | Field | How the action updates it | Effect on B or E at LATER steps |
|---|---|---|---|
| P1 | `self._segments[u]` — `Segment(norad_id, cell_id, start_transmit_gain, age_steps)` | `step.py:817-855`. If served AND `segment.continues(association)` AND `_previous_association[u] is not None`: keep `start_transmit_gain`, `age_steps += 1`. Otherwise start a NEW segment with `start_gain = G^T(theta(t))` (so `p = p0` exactly). If unserved: `self._segments[u] = None`. | **PHYSICAL, the main temporal channel.** At `t+k`, if still held: `p(t+k) = p0 * G^T(theta(tau)) / G^T(theta(t+k))`. Raises the user's own wanted power (higher SINR -> more bits), raises the beam max (more E and more interference for others), and once `p > p_max = 1.65 W` the user goes to **outage — zero bits** (`step.py:805-813`, `service.py:242-246`). Switching resets to `p0`. |
| P2 | `self._ledgers[u]._previous` (realised `Association`) | `HandoverLedger.observe` at `step.py:1076-1081` (commit only) | Two consequences: (a) the handover class next step -> `r2` **only** (§4); (b) `incumbent_norad` -> `_incumbent_norads()` (`step.py:1301-1308`) -> `driver.step(incumbent_norads=...)` -> `assign_satellite_slots` puts the incumbent in **slot 0 even when it is not top-4 by D2 margin**, displacing the 4th-best (`action_contract.py:213-224`). **PHYSICAL/AVAILABILITY: changes which four satellites are selectable at the next dwell boundary, hence future feasible B and E.** |
| P3 | `self._previous_association[u]` | `step.py:1084-1087` (commit only) | (a) Gates segment continuation at `step.py:780,826`; (b) feeds state block 1 (`access_vector`, `step.py:1120-1141`) and the V0.3/V0.4 context blocks. |
| P4 | `self._previous_radiating` (`RadiatingBeams`, with `power_w`) | `step.py:591` | **OBSERVATION ONLY.** Feeds the state's `gamma` block via `_candidate_sinr` (`step.py:1184-1298`) under provenance `theta-current-interference-previous-step` (`interference.py:445-451`), and the V0.3 `beam_active` / `maximum_required_link_power` blocks (`ee_axis_state.py:229-280`). It does **not** enter next-step physics: interference at `t+1` is rebuilt from `t+1`'s served set (`step.py:859-935`). |
| P5 | `self._previous_demand` (ungated `n_{s,v}(t)`) | `step.py:603` | **OBSERVATION ONLY** — state block 4 `beam_loads` (`step.py:1174-1183`). |
| P6 | `self._previous_link_power_w`, `self._previous_served_rate_bps` | `step.py:594-602` | **OBSERVATION ONLY** — V0.3 `previous_recurrence_power` (`ee_axis_state.py:291`) and V0.4 C3 `previous_beam_rate_burden` / `previous_satellite_rate_burden` (`ee_axis_v04_c3_state.py:196-240`). |

### 3.1 What is persistent but NOT action-dependent

* **D2 latches** (`d2.py:344-402`) — a pure function of slant range, altitude and the
  hysteresis/TTT history. `D2Tracker.update` takes no action input. Eligibility,
  `margin_km`, `ttt_elapsed`, `range_rate_km_s` are all geometry.
* **Dwell anchoring / re-key** (`dwell.py:156-203`) — boundary is
  `step_index % N == 0` with `N = 4` (`dwell.py:64`), and the anchor is
  `grid.anchor_cell_ids(positions)`. Consulted only at a boundary. Action-independent.
* **Frozen candidate window** `_frozen_window_norad_ids` (`scenario.py:366-388`) — the
  identity set is rebuilt only at a dwell boundary; within a dwell, only eligibility and
  live geometry refresh (`candidates.py:271-338`). This is what makes the incumbent
  channel (P2) fire *only at dwell boundaries*.
* **Mobility** (`mobility.py:117-135`) — driven solely by `mobility_rng`,
  never by actions.
* `self._age_rng` — survives episode resets (`step.py:407-445`); warm-start ages only.

### 3.2 Explicit "no fixed point" property

`step.py:22-26`: `p` depends only on the off-axis angle, never on load or interference,
so the power model cannot chase the SINR it produces. This is what makes the per-step
physics a single forward pass and makes the segment the only carrier of history.

---

## 4. HANDOVER PENALTY — verdict: **REWARD-ONLY**

`HANDOVER_COST`, `PHI1 = 0.5`, `PHI2 = 1.0` are defined at
`src/mcrl/env/action_contract.py:408-418`. A repo-wide grep over `src/mcrl/env` and
`src/mcrl/runtime/energy_efficiency.py` finds exactly **one** consumer:

```python
# src/mcrl/env/step.py:1057   from .action_contract import HANDOVER_COST, UNSERVED, classify_handover
# src/mcrl/env/step.py:1094   r2_handover=-HANDOVER_COST[handover],
```

`r2_handover` is a field of `RewardComponents` (`step_types.py:188`) and appears only in
`StepOutcome.reward_matrix` (`step.py:307`) / `ActionEvaluation.reward_matrix`
(`step.py:353`). It never touches `link_power`, `beam_power`, `supply`, `fixed`,
`total_power`, `sinr`, `rate`, `resolution`, or `energy`.

The handover class is computed from the **realised association**, never the action index
(`action_contract.py:421-456`), and `classify_handover` is called in `_rewards`
(`step.py:1076-1081`) after the physics dict is already complete.

Also checked and found **absent** from `step.py`:

* **No service gap / interruption time.** A handover step is served normally; the user
  contributes bits at the new association in the same step.
* **No dwell reset.** `DwellController.step` is on a fixed `step_index % N` schedule and
  never sees an action (`dwell.py:156-203`, `scenario.py:352-354`).
* **No activation/transition power.** `fixed_power_w` charges only steady-state
  `P_cir` per active beam and `P_BB` per active satellite.
* **No handover-triggered outage.** `outage_infeasible` comes only from
  `p_{u,s,v} > p_max` or `G^T = 0` (`step.py:805-813`).

**However — a handover DOES have a real physical consequence, via a different
mechanism:** changing the association drops the power segment
(`Segment.continues` is False at `step.py:777-781, 823-827`), which resets
`start_gain = G^T(theta(t))` and hence `p = p0 = 0.825 W` exactly
(`link_budget.py:379-408`; verified: `recurrence_power_w(G, G) == p0`). So a switch is a
**power reset to `p0`**, which:

1. lowers the switching user's own wanted power (relative to an aged segment),
2. lowers the beam's `max` if that user was the beam's power setter (lowers E and
   interference), and
3. clears any accumulated infeasibility risk (a fresh segment always satisfies
   `p0 <= p_max`).

This is a *physical* effect of the handover **decision**, not of the handover
**penalty scalar**. `phi1`/`phi2` are inert with respect to `B` and `E`.

---

## 5. DETERMINISTIC GEOMETRY

### 5.1 How each geometric quantity is produced

| Quantity | Where | Formula |
|---|---|---|
| Satellite ECEF position/velocity | `ephemeris.py:496-543` | SGP4 (`sgp4.api.SatrecArray`, WGS-72) on `(jd, fr)` from `step_times` (`ephemeris.py:449-464`), then `teme_to_ecef` with GMST (`geometry.py:92-140`). |
| Slant range `d_{u,s}` | `pointing.py:40-59` (closed form eq. 3.5) and `geometry.look_angles` | `sqrt((R_E sin a)^2 + h^2 + 2 R_E h) - R_E sin a`, algebraically identical to `|r_sat - r_user|`. |
| Elevation | `geometry.look_angles` (220-247), surfaced as `StepCandidates.elevation_deg` | Standard look angle. |
| Off-axis angle `theta_{u,s,v}` | `pointing.py:62-73` -> `geometry.angle_between_deg` | eq. (3.6): angle **at the satellite** between the beam boresight (cell centre - satellite) and the user. Degrees. |
| Signed range rate | `scenario.py:409-417` `_measure` | `v_ecef . unit(r_sat - r_user)`; negative = approaching. Rotating-frame velocity, so no correction needed (`ephemeris.py:532-536`). |
| Remaining visible / legal time | **Not computed anywhere.** | The only availability predicate is the instantaneous D2 latch (`d2.py:376-393`) plus the `min_altitude_km = 300` floor and the cell-visibility elevation test (`candidates.py:341-368`). There is **no** "time-to-set", "remaining dwell", or "remaining visibility" field in the state or in `StepCandidates`. |

### 5.2 Determinism

All of the above are **deterministic functions of (TLE set, absolute UTC time, user ECEF
position)**. There is no stochastic term anywhere in `geometry.py`, `pointing.py`,
`ephemeris.py`, `tle.py`, `d2.py`, `dwell.py`, `cells.py`, `antenna.py`, or in the
deterministic part of `link_budget.py` (`free_space_path_gain`, `atmospheric_loss_db`,
`scintillation_loss_db` — `link_budget.py:120-136` explicitly notes `L_c` is a table
lookup, "deterministic, not a draw").

So: **given the TLE set and the user positions, every geometric quantity at every future
step is exactly computable at decision time, for any horizon.** The only residual is user
mobility (§6), which is small: 250 m per 30.08 s step subtends 0.0297 deg at 483 km
against a median per-step `|d theta|` of 1.194 deg — a 2.5% contribution, disclosed at
`step.py:1398-1407`.

The environment already exposes the forward/backward propagation seam:
`ScenarioDriver.satellite_ecef_at(offset_steps)` (`scenario.py:270-293`) accepts
**negative or positive** offsets. It is currently used only for the step-0 warm start
(`step.py:750-761`), but nothing prevents a positive offset. **A perfect-foresight
geometry feature for any horizon is one call away and costs one SGP4 propagation.**

### 5.3 Where the candidate list comes from

`ScenarioDriver._resolve` (`scenario.py:295-389`) -> `resolve_candidates`
(`candidates.py:117-268`):

1. `select_elements` + `shortlist_visible` fix the tracked universe once per episode
   (`scenario.py:154-173`).
2. D2 advances 47 sub-steps per decision on the 640 ms clock (`scenario.py:313-350`).
3. At a **dwell boundary** the four satellite slots are rebuilt from the D2-eligible set,
   incumbent first (`candidates.py:186-200` -> `action_contract.py:192-255`).
   Between boundaries the identities are frozen and only eligibility/geometry refresh
   (`candidates.py:271-338`).
4. `mask[a] = slot occupied AND cell exists AND cell sees satellite`
   (`action_contract.py:313-369`, `candidates.py:341-368`). Link feasibility is **not**
   in the decision mask (`candidates.py:21-24`) — it is applied post hoc as outage.

**Can the agent see future geometry?** Not through the state. The 112-D state
(`step.py:1102-1183`) carries only `x(t-1)`, current-`theta` candidate SINR against the
*previous* radiating set, current `theta` in radians, and `n(t-1)`. The signed range rate
is in the §4A.6 contract block which is **an ablation switch, off by default**
(`action_contract.py:524-534`, `step_types.py:109-125`) — the V0.7 C2 encoder is the one
place that re-injects it (`ee_axis_v07_c2_state.py:145-184`), by overwriting the
redundant `beam_active` slice. So the agent currently sees *first-order* motion at best,
and never a multi-step geometric forecast.

---

## 6. STOCHASTICITY

There are exactly **three** random streams, and the model documents that there are only
two random *terms*.

| Source | Where | Keyed? | Predictable at decision time? |
|---|---|---|---|
| **Rician small-scale fading** `h`, unit mean, K = 20 dB | `link_budget.py:297-317`, drawn at `step.py:1310-1389` | YES if a `KeyedFadingField` is supplied: substream = SHA-256 of `(version, root_key, event, step_index, norad)` (`keyed_fading.py:137-150`) | NO. Shallow (~+-1 dB at K=100) but a genuine draw. |
| **Shadow fading** `L_s`, zero-mean dB Gaussian, elevation-dependent sigma | `link_budget.py:139-169` (TR 38.811 Table 6.6.2-3) | YES, same substream as the Rician draw | NO. sigma from 0.4 to 3.6 dB. NOTE `link_budget.py:160-166`: zero-mean in dB is **not** zero-mean in linear power; +1.0 dB mean gain at sigma = 3 dB, reproduced deliberately. |
| **Mobility** (scatter + bounded random turn + reflection) | `mobility.py:96-135` | NO — a plain sequential `mobility_rng` | NO, but bounded: 250.7 m/step, max turn +-pi/4. |
| **Segment warm-start ages** (step 0 only) | `step.py:1370-1389` | own spawned stream, persists across episodes (`step.py:407-445`) | Episode-boundary artefact only. |

**Traffic:** there is no traffic model. Every user always wants service; the only
"demand" quantity is a head count of who selected which beam
(`service.py:109-113`). No queues, no packet arrivals, no buffers.

**Keyed common randomness (critical for matched arms).** Without
`KeyedFadingField`, `_draw_fading` (`step.py:1310-1389`) consumes a sequential generator
in `sorted(satellite_ecef)` order, and the satellite *set* is the union of all users'
windows — which is action-dependent at dwell boundaries. So two counterfactual branches
would silently shift every later draw. `keyed_fading.py:1-14` states exactly this, and
the fix addresses each `(event, step_index, norad)` path to its own PCG64 substream, with
the user axis vector-indexed. Events used: `"physics"` (`step.py:894`),
`"observation"` (`step.py:1201`, `1264`). Held-out EE evaluation **requires** the keyed
field (`ee_axis_evaluation.py:144-146`).

Elevation may differ between branches; the keyed field keeps the underlying standard
normal common and applies branch-local sigma (`keyed_fading.py:98-101`).

**Not predictable from decision-time state:** the two fading draws for the current and
all future steps, and other users' *future* actions (policy-mediated). Everything else —
geometry, D2 eligibility, dwell phase, the whole `p` trajectory of a held segment
(to within mobility) — is predictable.

---

## 7. SERVICE FEASIBILITY, OUTAGE, AND LOST BITS

### 7.1 The gate

Exactly one gate exists, applied per link, **after** the recurrence
(`link_budget.py:411-436`, applied `step.py:805-813`):

```python
infeasible[u] = (G^T(theta_u(t)) <= 0)  OR  (p_{u,s,v}(t) > p_max = 1.65 W)
```

`resolve_service` (`service.py:222-251`) then does:

* `NO_OP_ACTION` -> `no_op_users[u] = True`, nothing else;
* infeasible -> `outage_infeasible[u] = True`; the user's **pre-admission demand still
  counts** in `demand_by_beam` but not in `eligible_load_by_beam` -> no service, no load,
  no activation, no power, and `rate[u] = 0` (`step.py:958-962`).

**Lost bits appear in `B` purely as absence**: `R_u = 0` for that user-step. There is no
separate "lost bits" accumulator anywhere. The evaluation receipt records it as
`outage_fraction = 1 - served_fraction` (`ee_axis_evaluation.py:214`) which is a
*coverage* statistic held beside the ratio, per gate G-8
(`energy_efficiency.py:19-23,187-211`).

### 7.2 Can an action now cause a feasibility failure later? **YES — and it is measured.**

`p(t+k) = p0 * G^T(theta(tau)) / G^T(theta(t+k))` grows monotonically as the beam's
transmit gain toward the user falls. The budget is exactly 3.010 dB
(`link_budget.py:737-752`). Holding an association past that point produces outage.

**Docstring vs. measurement — flag this.** `link_budget.py:748-751` claims "the largest
in-segment loss under the frozen scenario is 0.718 dB against this 3.010 dB budget, so
the feasibility gate is currently non-binding: outage 0 of 12,000 decision steps."
The frozen probe artifacts contradict that:

| artifact | `segment_warm_start` | `outage_rate` | `power_gate_is_binding` | `mask_is_ever_binding` |
|---|---|---|---|---|
| `artifacts/probe-p7-main-arm-2026-08-23.json` | `uniform-episode-length` (main arm) | **0.076** | **True** | False |
| `artifacts/probe-p7-sensitivity-2026-08-23.json` | `uniform-segment-length` | 0.06875 | True | False |
| `artifacts/probe-p7-no-warm-start-2026-08-23.json` | `none` | 0.001625 | True | False |

In the main arm, 608 of 8000 decision steps are infeasible, with median required power
8.67 W = 5.25x `p_max` (7.2 dB of gain loss) and a max of 140.8 kW. So the outage channel
is live and is driven by segment age. **The docstring is stale; the code and the frozen
artifacts are authoritative.**

Note also `mask_is_ever_binding = False` and all three mask-attrition counters are
identically zero in every arm: **the decision mask is never contracted under the frozen
scenario** — every user always has 28 valid actions, and the no-op / starvation path is
never exercised. So "choosing a satellite that will set" does **not** currently reach
the agent as a mask contraction. It reaches it as (a) segment-age outage above, and
(b) at a dwell boundary the incumbent must still be D2-*eligible* to be seated in slot 0
(`action_contract.py:218-224`).

**Cross-user feasibility is impossible.** `infeasible[u]` depends only on `u`'s own
`link_power[u]` and `transmit_gain[u]`. No other user's action can make `u` infeasible.

---

## 8. LINK POWER SHAPE AND THE BEAM-MAX EXTERNALITY

### 8.1 Yes — power is set by the worst (max-power) user on a beam

`link_budget.py:439-465`:

```python
out[beam] = max(out[beam], value)   # over served users only
```

Docstring: *"一支已啟用的波束以單一功率發射，不論其上載有幾位使用者"* — the beam radiates
one power regardless of how many users it carries, so the aggregation is a **max**, never
a sum or a mean. A beam with no served user radiates nothing.

### 8.2 The externality, precisely

Suppose beam `(s,v)` currently serves users with link powers `{p_1, ..., p_n}` and
`p_beam = max_i p_i`. A focal user `u` joining with `p_u`:

1. **Bandwidth**: every existing user's rate is multiplied by `n/(n+1)`
   (`link_budget.py:615`). This is the *largest* immediate non-focal effect.
2. **Beam power**: `p_beam' = max(p_beam, p_u)`. If `p_u > p_beam` the beam's radiated
   power rises for everyone.
   * E rises by `6.5264 * (sqrt(p_beam') - sqrt(p_beam))` W — concave, so a large power
     increase is comparatively cheap.
   * The beam's contribution to **every co-colour victim's interference** rises in
     direct proportion to `p_beam'` (`interference.py:317-323`, `349-399`): the terms are
     `p_{s',v'} * G^T * H * G^R`, linear in beam power.
3. **Activation**: if the beam was dark, `+P_cir = 0.338 W`, `+P^p >= 5.93 W`, and a
   whole new interference source appears for every co-colour victim; `+P_BB = 0.200 W`
   if the satellite was also dark.
4. **What does NOT change**: no other user's *wanted* power (they keep their own
   `p_i`, `interference.py:412-417`), and no other user's feasibility.

### 8.3 Is this the mechanism C3 uses?

Partly. C3/`zeta_3` is defined as the **opening-step non-focal rate externality only**
(V0.3 contract lines 96-110; implemented `ee_surplus_targets.py:254-262`):

```python
z3 = interval * fsum(delta_rates_by_user[0, nonfocal_mask])
```

So C3 captures the *rate* consequences of (1) bandwidth sharing, (2) interference change
from the focal's beam power / activation / de-activation, and (3) nothing else — because
feasibility is per-link and the wanted power is private.

C3 explicitly does **not** carry the energy half of the beam-max effect. The contract
says so at lines 108-110: *"Shared activation and PA energy caused at the opening step is
already charged to C1; duplicating it in C3 would double count."* Correspondingly
`ee_surplus_targets.py:250-252` charges the **whole** opening `Delta P^N` to `zeta_1`:

```python
z1 = float(focal_delta_bits - multiplier * opening_delta_energy)
```

and P4 in the contract (line 262) requires that changing `lambda_0` cannot change C3 —
which holds by construction since `z3` has no `lambda` term.

**So**: the beam-max mechanism reaches C3 through interference-on-others only; its energy
consequence is inside C1; and its *persistence* (a focal user who remains the beam's power
setter for k steps) is inside C2's scope in V0.3 but only partly in V0.7 (§9.3).

---

## 9. MULTIPLIER `lambda_0` AND THE C1/C3 TARGET CODE

### 9.1 Where `lambda_0` is computed and whether it is TRAIN-only

`src/mcrl/runtime/ee_axis_calibration.py` — module docstring line 1 is literally
*"TRAIN-only common-unit calibration for the V0.3 pairwise learner."*

```python
# ee_axis_calibration.py:134-145
result = EEAxisPilotCalibration(
    calibration_seed=calibration_seed,
    useful_bits=useful,
    energy_j=energy,
    ...
    lambda_bits_per_j=useful / energy,          # 141   lambda_0 = B_0^M / E_0^M
    kappa_bits=useful / decisions,              # 142   kappa   = B_0^M / n_0
    ...
)
```

Re-checked on every `verify()` (`ee_axis_calibration.py:72-75`):

```python
if not math.isclose(multiplier, useful / energy, rel_tol=0.0, abs_tol=1e-9):
    raise EEAxisCalibrationError("lambda does not equal Main bits over energy")
if not math.isclose(scale, useful / self.decision_count, rel_tol=0.0, abs_tol=1e-9):
    raise EEAxisCalibrationError("kappa does not equal Main bits per decision")
```

The value is serialised as **hexadecimal float** (`as_payload`, lines 88-96) precisely so
that "the same hexadecimal floating-point value is used for every arm, window, head, and
candidate in one stage" (contract line 55) is auditable. There is exactly one producer
(`calibrate_ee_axis_pilot`) and no other place in `src/` computes a `lambda`; per-window,
per-arm and per-candidate multipliers are forbidden by the contract (lines 56-57).

`kappa` is the shared output scale, used by the pairwise learner
(`ee_axis_calibration.py:99-116`), and — note — also as the C3 state normaliser
(`ee_axis_v04_c3_state.py:196-240`, `scale = interval_s / kappa_bits`).

### 9.2 How C1 and C3 targets are built (native bits: `dB - lambda_0 * dE`)

`src/mcrl/runtime/ee_surplus_targets.py:239-262` (`ee_surplus_axis_targets_v03`):

```python
delta_rates_by_user = candidate_rates - reference_rates
delta_bits_by_step = np.asarray(
    [interval * math.fsum(float(value) for value in row) for row in delta_rates_by_user],
    dtype=np.float64,
)
delta_energy_by_step = interval * (candidate_power - reference_power)
system_step_surplus = delta_bits_by_step - multiplier * delta_energy_by_step   # g_k

focal_delta_bits      = interval * delta_rates_by_user[0, focal]
opening_delta_energy  = float(delta_energy_by_step[0])
z1 = float(focal_delta_bits - multiplier * opening_delta_energy)               # zeta_1

nonfocal_mask = np.ones(reference_rates.shape[1], dtype=np.bool_)
nonfocal_mask[focal] = False
z3 = float(interval * math.fsum(
        float(value) for value in delta_rates_by_user[0, nonfocal_mask]))      # zeta_3
z2 = float(math.fsum(float(value) for value in system_step_surplus[1:]))       # zeta_2
```

The exact accounting identity `z1 + z2 + z3 == sum_k g_k` is re-checked with a
term-magnitude-scaled tolerance (`ee_surplus_targets.py:264-279`) because the terms can be
O(1e11) bits while their signed sum is near zero.

Consumed by the opening-pair builder at `ee_axis_opening_pairs.py:396-411`:

```python
targets = ee_surplus_axis_targets_v03(..., reference_system_rates_bps=reference_rates[None, :], ...)
if targets.z2_temporal_surplus_bits != 0.0:
    raise OpeningPairContractError("an opening-only row cannot carry zeta2")
target = (targets.z1_focal_surplus_bits if source_route == "C1"
          else targets.z3_nonfocal_externality_bits)
```

C2's target (`ee_axis_temporal_pairs.py:428-444`) is the same `g_k` summed over offsets
1..3:

```python
expected_surplus = [ interval * fsum(delta_rates[offset])
                     - multiplier * interval * (candidate_power[offset] - reference_power[offset])
                     for offset in TEMPORAL_DOWNSTREAM_OFFSETS ]     # (1, 2, 3)
expected_target = fsum(expected_surplus)
```

`TEMPORAL_HORIZON_STEPS = 4`, `TEMPORAL_DOWNSTREAM_OFFSETS = (1, 2, 3)`
(`ee_axis_temporal_pairs.py:40-41`, `ee_axis_v05_c2_controlled_tape.py:38-39`).

### 9.3 What the *current* V0.7 C2 target actually is (narrower than V0.3)

`src/mcrl/runtime/ee_axis_v07_c2_focal_next.py:109-118`:

```python
candidate_marginal = candidate_full - candidate_without      # P_full - P_without_focal
reference_marginal = reference_full - reference_without
rate_delta_bits         = interval * (candidate_rate - reference_rate)      # FOCAL user only
marginal_energy_delta_j = interval * (candidate_marginal - reference_marginal)
target = rate_delta_bits - multiplier * marginal_energy_delta_j
```

Module docstring lines 3-8: *"V0.6 attributed the entire next-slot network response to
one focal opening action. The sealed negative result showed that this network-total label
did not generalise from the causal state. V0.7 keeps C2's temporal role but limits its
public target to the focal user's next-slot rate and marginal network power. **Non-focal
next-slot continuation cascades are deliberately outside the learned target.**"*

The `P_full - P_without_focal` marginal is produced by
`StepEnvironment.evaluate_actions_without_user` / `step_without_user`
(`step.py:550-579`, `653-683`), which substitute `NO_OP_ACTION` for the focal user
behind the action-contract boundary. This is exactly the beam-max displacement measure
(§8.2 item 2) plus activation.

So the **currently learned** C2 covers: focal user's rate at k=1, and the focal user's
*marginal* share of network power at k=1. Nothing at k=2,3; nothing non-focal.

---

## 10. THE EE CAUSAL MAP

Legend for the decision-time predictability class:

* **DP** = DETERMINISTIC-PREDICTABLE — a closed-form function of TLE + absolute time
  (+ current user position), computable now for any horizon.
* **SP** = STATE-PREDICTABLE — determined by state that is already persisted and
  observable at decision time (possibly needing a schema change to expose it).
* **SU** = STOCHASTIC-UNPREDICTABLE — depends on a draw or on other agents' future
  choices.

### 10.1 Immediate channels (action at t -> B/E at t)

| # | Channel | Path | Class |
|---|---|---|---|
| I1 | Own off-axis angle -> `G^T(theta(t))` -> `p_{u,s,v}` and wanted power -> own SINR -> own `R_u` | `step.py:740-745,797-803,938-955` | **DP** |
| I2 | Own slant range / elevation -> free-space + gaseous + scintillation loss -> own SINR | `link_budget.py:340-359,664-691` | **DP** |
| I3 | Own segment continuation -> `G^T(theta(tau))` in `p` | `step.py:777-803` | **SP** (`start_transmit_gain` is persisted; exposed as `current_to_segment_start_gain_ratio`, `ee_axis_state.py:328-335`) |
| I4 | Own fading + shadow draw -> own SINR | `step.py:1310-1389` | **SU** (keyed -> common across matched arms) |
| I5 | Joint beam occupancy `U_{b_u}` -> bandwidth share `B^w/U` -> everyone's rate on that beam | `service.py:251`, `link_budget.py:615` | **SU at decision time** (simultaneous joint action); the *lagged* proxy is in state (`eligible_served_load`, `ee_axis_state.py:277`) |
| I6 | Joint activation `z = 1{U>0}` -> `P_cir` per beam, `P_BB` per satellite -> `E` | `link_budget.py:521-546` | same as I5 |
| I7 | Joint beam-max `p_{s,v}` -> `P^p = 6.5264*sqrt(p)` -> `E` | `link_budget.py:439-518` | same as I5 |
| I8 | Joint radiating set -> co-channel interference -> everyone's SINR -> everyone's `R` | `interference.py:277-399` | same as I5 |
| I9 | Own `p > p_max` -> outage -> own `R_u = 0` and removal from load/activation/power | `step.py:805-815`, `service.py:242-246` | **DP given I3** (fully determined by `theta(tau)`, `theta(t)`) |

Coverage: **I1-I4, I9** are inside C1 (`zeta_1`, focal rate + total opening energy).
**I5-I8** on non-focal users are inside C3 (`zeta_3`, non-focal rate only); their energy
half is folded into C1's `Delta P^N(0)`.

### 10.2 Temporal channels (action at t -> B/E at t+k, k >= 1)

| # | Channel | Mechanism and cite | Class | Covered by C1? | C3? | C2 (V0.3)? | C2 (V0.7, as coded)? |
|---|---|---|---|---|---|---|---|
| **T1** | **Segment power recurrence.** Holding gives `p(t+k) = p0*G^T(theta(tau))/G^T(theta(t+k))`; switching resets to `p0`. Changes own wanted power, the beam max (E + others' interference), and eventually outage. | `step.py:777-855`, `link_budget.py:379-408` | **DP** (theta trajectory from SGP4; segment start persisted) | no | no | k=1..3, all users | **only focal rate + focal marginal power at k=1** |
| **T2** | **Segment-age outage.** `p` crosses `p_max` after ~3.01 dB of gain loss -> zero bits for that user-step. Measured 7.6% of decision steps in the main arm. | `link_budget.py:411-436,737-752`; `artifacts/probe-p7-main-arm-2026-08-23.json` | **DP** | no | no | k=1..3 (if it fires inside the 4-step window) | k=1 only, focal only |
| **T3** | **Incumbent -> candidate window at the next dwell boundary.** The realised association becomes `incumbent_norad`; at the next boundary (`step_index % 4 == 0`) it is seated in slot 0 **even if outside the top 4 by D2 margin**, displacing the 4th-best satellite. Changes the *action set*, hence future achievable `R` and `P^N`. | `step.py:1076-1087,1301-1308`; `scenario.py:355-388`; `action_contract.py:213-224` | **DP** (D2 margins are pure geometry; the boundary schedule is `step_index % N`) | no | no | **only if the horizon crosses a boundary** — with `H^c = 4` and `N = 4`, an anchor *at* a boundary has its next boundary at offset 4, i.e. outside the window | **no** |
| **T4** | **Persistent beam-power leadership.** A focal user who becomes and remains the beam's `max`-power setter raises `P^p` and the beam's interference at every later step it holds. | `link_budget.py:439-465` + T1 | **SP** (needs other users' segments) / **SU** (needs their future actions) | no | no | k=1..3 (in the system total) | **partly**: the focal marginal `P_full - P_without_focal` at k=1 only |
| **T5** | **Observation-mediated policy feedback.** `_previous_demand`, `_previous_radiating`, `_previous_served_rate_bps`, `_previous_link_power_w`, `_segments` all feed *other* users' state at t+1, so under a fixed continuation policy they change other users' actions, hence B and E. | `step.py:591-603,1102-1298`; `ee_axis_state.py:223-335`; `ee_axis_v04_c3_state.py:196-240` | **SU** (policy-mediated) | no | no | k=1..3, implicitly, under branch-local Main continuation | **no** — explicitly excluded ("non-focal next-slot continuation cascades are deliberately outside the learned target", `ee_axis_v07_c2_focal_next.py:6-8`) |
| **T6** | **Handover class -> `r2`** | `step.py:1094` | — | **Does not touch B or E at all.** |
| **T7** | Dwell re-key, D2 latch, mobility | `dwell.py:156-203`, `d2.py:344-402`, `mobility.py:117-135` | **Not action-dependent.** DP (dwell, D2) / SU (mobility). |
| **T8** | Interference at t+k | rebuilt from t+k's served set, `step.py:859-935` | **No physical lag.** Only T5 carries it forward, via observations. |

### 10.3 Channels that exist in the docs but not in the code (or vice versa)

| Claim | Status |
|---|---|
| "remaining visible / legal time" as a decision-time quantity | **Not in the code.** No time-to-set, no remaining-visibility, no pass-duration field anywhere in `StepCandidates`, the D2 snapshot, or any state encoder. `dwell.segments_per_service_window` (`dwell.py:206-220`) is an offline sizing helper with no live consumer. |
| `link_budget.py:748-751` "outage 0 of 12,000 decision steps, gate non-binding" | **Stale / contradicted by the frozen artifacts.** `probe-p7-main-arm` reports `outage_rate = 0.076`, `power_gate_is_binding = True`. See §7.2. |
| §4A.6 contract block (`is_incumbent`, `d2_ttt_counter`, `radial_rate`, `dwell_phase`) | **In code, disabled by default** (ruling C-1): `action_contract.py:524-534`, `step_types.py:109-125`. `scenario._slot_only` (`scenario.py:392-406`) is *only correct while `radial_rate` is off the live path* — a live dependency, flagged in its own docstring. The V0.7 C2 encoder re-injects the signed range rate by overwriting the redundant `beam_active` slice (`ee_axis_v07_c2_state.py:196-211`). |
| `PhysicsConfig.fading_enabled = False` | Test affordance only; `assert_ready_to_train` refuses to start training with it off (`step.py:475-479`). |
| Per-satellite / per-beam power cap, beam-count ceiling, activation ranking | **Deleted, and their return is guarded.** `link_budget.py:196-202,425-427`; `service.py:132-147`; `step_types.py:31-49`. `HOBS_LEO_MAX_TRANSMIT_POWER_W = 100 W` is a budget *check*, never a clamp. |
| Target-SINR inversion / required-SINR `gamma_req(U)` | **Deleted** (`service.py:289-301`, ruling C-2). |
| Traffic / queue / buffer model | **Does not exist.** |
| `ee_axis_targets.py` (z1/z2/z3 in bits/J) | Present but explicitly "not wired into the trainer" (`ee_axis_targets.py:3`). The live path is `ee_surplus_targets.ee_surplus_axis_targets_v03` (native bits). |
| `ee_surplus_axis_targets` (V0.2, isolated single-user evaluator) | Retained only so frozen receipts stay interpretable; superseded (`ee_surplus_targets.py:3-6`; contract lines 73-76). |

---

## 11. TOP CANDIDATE TEMPORAL CHANNELS NOT COVERED BY C1 OR C3

Ranked by (a) magnitude in B/E, (b) predictability at decision time, (c) distance from
what C1 and C3 already capture.

### #1 — Segment-age power trajectory and the outage cliff (T1 + T2). Confidence: HIGH.

* **What it is.** Holding an association makes `p` climb along
  `p0 * G^T(theta(tau)) / G^T(theta(t+k))`, a *deterministic* trajectory. It raises the
  user's own SINR (more bits), raises the beam max (more E, more interference on others),
  and at ~3.01 dB of gain loss it crosses `p_max` and the user contributes **zero bits**.
* **Why it is not covered.** C1 and C3 are strictly offset-0. C2 in V0.7 sees only the
  focal user's rate and marginal power at **k = 1**; the cliff typically lands at k >= 2
  and the interference/energy externality of a hot segment on *others* is excluded by
  construction.
* **Why it is a good C2/Q2 target.** It is **DETERMINISTIC-PREDICTABLE**:
  `ScenarioDriver.satellite_ecef_at(+k)` (`scenario.py:270-293`) already propagates
  forward, `Segment.start_transmit_gain` is already persisted, and
  `transmit_gain_linear` is a closed form. The state already carries the
  `current_to_segment_start_gain_ratio` and `segment_age`
  (`ee_axis_state.py:314,335`) — i.e. the *level*, but not the *slope* or the
  *time-to-cliff*.
* **Measured evidence it matters.** 608/8000 infeasible decision steps in the main arm,
  median required power 5.25x `p_max` (`artifacts/probe-p7-main-arm-2026-08-23.json`).
  That is a 7.6% direct hit on B with no compensating reduction in E, since an outaged
  user still leaves the beam lit if anyone else is on it.

### #2 — Incumbent-mediated candidate-window control at dwell boundaries (T3). Confidence: MEDIUM-HIGH.

* **What it is.** The realised association at t is the incumbent at t+1..; at the next
  dwell boundary (`step_index % 4 == 0`) it is *guaranteed* slot 0 even when it is not in
  the top four by D2 margin, displacing the 4th-best candidate
  (`action_contract.py:213-224`). One user's current choice therefore edits their own
  future action set.
* **Why it is not covered.** Offset-0 heads cannot see it. The C2 horizon
  `H^c = 4` with `N = 4` means an anchor at a boundary never contains the next boundary,
  so exactly the phase where the mechanism fires is systematically outside the window.
  Nothing in the V0.3/V0.4/V0.7 state exposes the *dwell phase* on the live path — it is
  in the disabled §4A.6 contract block (`action_contract.py:524-534`).
* **Why it is a good target.** **DETERMINISTIC-PREDICTABLE**: the boundary schedule is a
  modulo counter and D2 margins are pure geometry, so "which four satellites will I be
  able to choose from at step `ceil(t/4)*4`, conditional on this action" is exactly
  computable with one extra SGP4 propagation.
* **Caveat that caps confidence.** `mask_is_ever_binding = False` in all three P7 arms —
  the mask is never *empty*, so this channel changes *which* four options exist, not
  whether any exist. Its EE magnitude is the quality gap between the incumbent and the
  displaced 4th-best satellite; that gap has not been measured in this repo.

### #3 — Persistent beam-power leadership and its downstream energy/interference externality (T4). Confidence: MEDIUM.

* **What it is.** `p_{s,v} = max_u p_{u,s,v}` means one user's aged segment sets the whole
  beam's radiated power at every step it holds. That raises `P^p = 6.5264*sqrt(p)` in E and
  scales the beam's interference term linearly for every co-colour victim — for as long
  as the association persists.
* **Why it is not covered.** C3 is offset-0 and rate-only. C1 charges only the opening
  `Delta P^N`. V0.7 C2's `P_full - P_without_focal` measures precisely this displacement
  but **only at k = 1**, and drops the non-focal *rate* consequence of the same
  interference change entirely.
* **Why it is a promising target.** It is where the two nonlinearities compose: a
  **concave** energy response (`sqrt`) against a **linear** interference response, on a
  **max** aggregator. That combination is exactly the shape a value head can exploit and
  a myopic argmax cannot: the cheapest way to add bits is to add a user to an
  already-hot beam (E rises sub-linearly), and the cheapest way to cut energy is to
  vacate the beam whose max you personally set.
* **Predictability.** **STATE-PREDICTABLE** given a schema change: the environment already
  persists `_previous_link_power_w` per user and `_previous_radiating.power_w` per beam,
  and V0.3 already exposes `maximum_required_link_power` per candidate action
  (`ee_axis_state.py:280`). What is missing is the *forward* version — the beam max the
  focal would set at t+k under a hold — which is `p0 * G^T(theta(tau))/G^T(theta(t+k))`
  compared against the persisted per-beam max. DP for the focal half, SP for the
  incumbent-beam half, SU only in the other users' future *choices*.

### Runner-up (noted, not recommended as a primary target)

**T5, observation-mediated policy feedback**, is genuinely temporal and genuinely
uncovered by C1/C3, but it is **STOCHASTIC-UNPREDICTABLE** at decision time: it depends
on the branch-local continuation policy, which the V0.3 contract itself makes part of the
frozen target definition (lines 129-134). It fails the "observable or deterministically
predictable at decision time" criterion, and V0.6's sealed negative result on the
network-total label is direct evidence that this component does not generalise from the
causal state (`ee_axis_v07_c2_focal_next.py:3-8`).

---

## 12. One-paragraph summary of the physics that a new C2/Q2 head should target

Everything that connects a decision at `t` to bits and joules at `t+k` in this simulator
flows through **one** physical object — the power segment
`(norad_id, cell_id, G^T(theta(tau)), age)` — and **one** availability object — the
incumbent NORAD id, which edits the four-satellite window at the next dwell boundary.
Interference, load, bandwidth sharing and activation are rebuilt from scratch every step
and carry **no** physical memory; they reach the future only through other agents'
observations. The segment's trajectory is a closed-form, deterministic function of SGP4
geometry and a single persisted scalar, and it terminates in a hard cliff at 3.010 dB
that is empirically binding 7.6% of the time. That is the temporal quantity that is both
caused by the action and exactly predictable at decision time.
