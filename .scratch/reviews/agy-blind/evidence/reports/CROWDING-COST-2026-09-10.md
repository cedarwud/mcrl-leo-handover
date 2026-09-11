**On this development panel, opening beams lowers EE: d(EE)/d(active) = -425,009.885 bit/J per added mean-active beam over 8.00–98.25 beams (no panel-level sign flip); the controlled two-user case is the low-load exception, where spreading 1→2 beams raises EE 60.805%; therefore the sibling project's “collapsed means broken” diagnosis does not transfer to this physics as a general diagnosis.**

# CROWDCOST — design-phase measurement, not a claim

## Decision

Crowding is cheap over the development panel. Pooled EE falls monotonically at every measured step as assignments are spread across more beams. The crowded endpoint delivers 46.1104 Mbit/J; the spread endpoint delivers 7.75323 Mbit/J, an 83.1855% loss. The geometric base is 11.0278 Mbit/J, so the crowded endpoint is 4.1813× base EE while the spread endpoint is 0.7031× base EE.

There is a real low-occupancy exception, not a contradiction: for exactly two selected users, separating them onto two private beams both reduces PA energy and increases bits. The controlled spread-minus-shared EE sign flips between N=2 and N=4. At N=4 and N=8, sharing one beam has substantially higher EE; N=16 is legal by mask but the spread assignment serves only 13/16, so it is not an all-served comparison.

This report uses no loss value as evidence. Its numerator is full-buffer successfully decoded information bits with no demand cap, as declaration v1.8 item 5 requires: “the rate target is a power-control setpoint, not a demand model” ([declaration](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.8-AMENDMENT-2026-09-09.md:9)).

## Scope and method — verified by running code

- Panel: `V025_PROBE/world/1`, steps 0–3 × `nearest-eligible`, `stay-if-possible`, and `random-masked`: 12 development anchors. The pilot defines `TRAIN_WORLDS = DEVELOPMENT_WORLD_DOMAINS[:2]` ([run_v025_pilot_c3.py](/home/sat/mcrl-v025-c1c2suff-ws/scripts/run_v025_pilot_c3.py:73)). No evaluation-only claim date was read.
- Physics: current V0.25 `a-r0`, realised field, all 48 within-step boundaries. Pooled EE is `sum(bits)/sum(joules)`, not a mean of anchor EEs.
- Assignment rule: compute an exact minimum legal-beam set cover (8 beams at every step); extend it through the beam/user transversal matroid to the exact maximum distinct-beam matching rank (100); sample 31 graded active counts; give every selected beam a distinct witness user; assign remaining users to their selected legal beam with greatest anchor-wide coverage; discard any row serving fewer users than that anchor's geometric base. The implementation is in [run_crowding_cost.py](/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py:219), and the base-service guard is applied at [run_crowding_cost.py](/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py:464).
- Guard result: zero violations across 356 retained anchor-level family rows. Every reported pooled family member has one retained row per anchor. The exact mask range is 8–100; after the service guard, the spread endpoint is 88–100 across anchors, averaging 98.25.
- Execution: one Python process, `nice=15`, all six recorded BLAS/thread controls set to 1. Peak RSS was **1,770,491,904 bytes = 1.649 GiB**, below 5 GB. The run printed `anchor k/12` at every anchor and completed in 985.64 s. Full machine receipt: [crowding-cost-receipt.json](/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/crowding-cost-receipt.json); log: [run.log](/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run.log).

## Part 1 — the four physics claims

### 1. Per-beam power is a max over served users — **REFUTED for the measured V0.25 a-r0 path**

The recorded statement is real in the legacy environment. It says `p_{s,v} = max_{u:x=1} p_{u,s,v}` and executes `out[beam] = max(out[beam], value)` ([link_budget.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/env/link_budget.py:439), [link_budget.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/env/link_budget.py:464)).

That is not what the current measured `a-r0` path does. It forms TDM slots and selects one active member of each beam per slot:

`active = tuple(members[min(int(midpoint * len(members)), len(members) - 1)] for members in grouped.values())`

([architectures.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/architectures.py:278)). It then stores one `(beam, power[row])` for that slot ([architectures.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/architectures.py:699)) and integrates the slot schedule ([energy.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/energy.py:146)). Thus the current aggregation over a beam's users is time averaging of per-user TDM transmissions, not a static maximum.

### 2. No PA saturation / no `p_max` clipping in the reached range — **REFUTED as a combined claim**

The PA-efficiency saturation subclaim is true by construction. The constants are:

`BEAM_RF_CAP_W = 1.65`

`PA_SATURATION_POWER_W = BEAM_RF_CAP_W * 10.0 ** (5.0 / 10.0)`

([constants_v025.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/constants_v025.py:34)). Derived on paper, `p_sat = 5.217758139277826 W`, while RF power cannot exceed 1.65 W; therefore the PA never reaches the flat `eta_max` branch of `min(eta_max, eta_max*sqrt(p/p_sat))` ([energy.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/energy.py:23)).

But the claim that `p_max` clipping is not reached is decisively false. The dense path explicitly executes:

`updated = np.minimum(BEAM_RF_CAP_W, targets * (noise + interference) / direct_nominal)`

([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:259)) and counts cap hits at [batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:390). Measured across the reported family: **7,099,336 / 39,878,520 = 17.8024%** transmission observations hit the cap. The geometric base hits it 27.9038% of the time; the crowded and spread endpoints hit it 75.4839% and 16.8484%, respectively. Maximum observed RF power is exactly 1.65 W.

### 3. PA is 94.8% of system power — **PARTIAL**

The measured 94.8% number is accurate only at the most-crowded endpoint: PA energy is **94.8732%** of its pooled modelled partial-payload energy. It is not a panel-wide constant:

- geometric base: **92.7456%**;
- eleven pooled family points: **90.7606%–94.8732%**;
- most-spread endpoint: **91.6687%**.

The dense expression is `pa_w = sum(sqrt(power * PA_SATURATION_POWER_W) / PA_MAX_EFFICIENCY)` ([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:393)). These shares concern the declared partial-payload boundary; bus, terminal, gateway, and other omitted energy are not “system power” in a constellation-wide sense ([declaration](/home/sat/mcrl-hub/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.8-AMENDMENT-2026-09-09.md:7)).

### 4. Bandwidth sharing makes total beam bits invariant to user count — **PARTIAL**

The effective `B/n` premise is verified, but it is implemented as full-band TDM rather than literal per-user sub-band allocation. Slot boundaries divide each beam into `n` equal airtime shares ([architectures.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/architectures.py:283)); each active user gets full `config.bandwidth_hz` in its slot ([architectures.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/architectures.py:697)); rates accumulate as `slot.fraction * rate_model.rate_bps(...)` ([resolution.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/resolution.py:120)). The dense equivalent is `boundary_rate += fraction * slot_rate` ([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:366)).

Derived on paper, one beam's aggregate rate is `B * mean_i(SE_i)`; it is invariant to `n` only if the users' achieved ACM spectral efficiencies remain unchanged. They need not: the controller uses `required_se = rate_target_bps * occupancy / full_bandwidth_hz` ([acm.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/acm.py:95)), so occupancy raises the required mode/SINR and can force the 1.65 W cap. The measured pooled bits are consequently non-invariant and non-monotone, peaking at 1.332089410088443e12 bits around 52.5 mean active beams.

### Fixed opening overhead

Verified from code, a radiating beam chain incurs **0.338 W continuously**, through `circuit_w = sum(active & (power > 0)) * circuit_power_per_active_chain_w` ([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:401)). The first radiating beam on a satellite additionally incurs **0.200 W** of common baseband/processing power through `active_satellites * BASEBAND_POWER_PER_ACTIVE_SATELLITE_W` ([batch.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/batch.py:406)); the constants are declared at [constants_v025.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/constants_v025.py:38). Bus power is exactly zero.

Derived over the 30.08 s decision interval, these are **10.16704 J per continuously active beam chain** and **6.016 J for the first active beam on a satellite**. They are power increments integrated over active time, not one-time switching impulses. The PA term is not fixed: it varies as `sqrt(p*p_sat)/eta_max`, which is why opening a second beam can sometimes reduce total joules by lowering required RF power.

## Part 2 — measured concentration family

`modal_frac` is pooled modal occupancy divided by 1,200 assigned user-anchor observations. `active` is mean active beams per anchor, with the 12-anchor total in parentheses. All bits and joules are pooled; EE is pooled bits divided by pooled joules.

| Concentration | modal_frac | active mean (total) | pooled bits | pooled joules | pooled EE (bit/J) | served |
|---|---:|---:|---:|---:|---:|---:|
| most crowded | 0.190000 | 8.000 (96) | 1.072637748181269e12 | 23,262.395146 | 46,110,374.337747 | 1,200 |
| Q90 | 0.160833 | 16.750 (201) | 1.108164712295819e12 | 38,192.502394 | 29,015,242.334025 | 1,170 |
| Q80 | 0.160000 | 25.500 (306) | 1.085016896893175e12 | 54,420.010401 | 19,937,829.649219 | 1,144 |
| Q70 | 0.160000 | 34.667 (416) | 1.211339048707730e12 | 61,850.578574 | 19,584,926.715867 | 1,165 |
| Q60 | 0.150833 | 44.250 (531) | 1.293717071911659e12 | 70,949.909194 | 18,234,231.539077 | 1,170 |
| Q50 | 0.143333 | 52.500 (630) | 1.332089410088443e12 | 77,697.648382 | 17,144,526.736945 | 1,170 |
| Q40 | 0.122500 | 61.250 (735) | 1.326701399341023e12 | 87,196.334974 | 15,215,105.081431 | 1,161 |
| Q30 | 0.105000 | 70.000 (840) | 1.324158876974335e12 | 99,894.876317 | 13,255,523.464170 | 1,164 |
| Q20 | 0.101667 | 79.083 (949) | 1.279286115754744e12 | 112,695.429809 | 11,351,712.468899 | 1,147 |
| Q10 | 0.070000 | 88.167 (1,058) | 1.275361070771291e12 | 122,406.932819 | 10,419,026.450520 | 1,146 |
| most spread after guard | 0.023333 | 98.250 (1,179) | 1.166940654912963e12 | 150,510.215668 | 7,753,232.229003 | 1,079 |

The requested single number is therefore:

`d(EE)/d(active) = -425,009.884861425 bit/J per added mean-active beam`

This is the endpoint secant over 8.00–98.25 mean active beams. Relative to the crowded endpoint it is −0.921723% EE per added beam. Every adjacent measured slope is negative, ranging from −1,953,729.372 to −38,498.502 bit/J/beam. **There is no panel-level flip.** More beams can raise bits over part of the range, but their energy cost rises faster.

For reference, the geometric base pools 1.121297101614074e12 bits, 101,679.495970 J, 11,027,760.227532 bit/J, 960 served, and 57.333 mean active beams. It is a guard/reference, not a member of the constructed nested family.

## Part 3 — controlled shared-versus-spread experiment

Anchor: `V025_PROBE/world/1|0|nearest-eligible`. Common beam: `(62045, 38)`. For N=2 the users are 3 and 4; their distinct private beams are `(57502, 37)` and `(57502, 39)`. Both assignments are legal and both users are PHY-served.

| N | layout | active | served | bits | joules | EE (bit/J) |
|---:|---|---:|---:|---:|---:|---:|
| 2 | shared | 1 | 2 | 2,244,570,555.555556 | 157.10955196699283 | 14,286,658.7515132 |
| 2 | spread | 2 | 2 | 2,859,939,911.1111107 | 124.48794921480122 | 22,973,628.605419047 |
| 4 | shared | 1 | 4 | 4,754,467,666.666668 | 137.39092998309084 | 34,605,396.93014536 |
| 4 | spread | 4 | 4 | 6,108,856,888.888887 | 333.9733908089108 | 18,291,447.93270128 |
| 8 | shared | 1 | 8 | 9,066,611,022.222221 | 226.69799073479626 | 39,994,227.53079819 |
| 8 | spread | 8 | 8 | 11,951,457,199.999998 | 669.6557673428133 | 17,847,165.33902672 |
| 16 | shared | 1 | 16 | 10,710,708,647.22222 | 268.3532219401482 | 39,912,726.106978014 |
| 16 | spread | 16 | 13 | 16,846,434,622.22222 | 1,981.040290728706 | 8,503,832.406167481 |

The memorable two-user result is: **opening the second beam adds 615,369,355.555555 bits, saves 32.621602752192 J, and raises EE by 8,686,969.853906 bit/J (+60.8048%).** Mechanistically, the shared case hits the RF cap in 42/96 transmission observations and consumes 140.926512 PA J; the spread case has zero cap hits and consumes 98.137869 PA J. Its extra beam adds exactly 10.16704 circuit J, but the 42.788643 J PA saving more than pays for it; both layouts use one active satellite and 6.016 baseband J.

The controlled sign flips between N=2 and N=4. Spread-minus-shared EE is +60.8048% at N=2, −47.1428% at N=4, and −55.3756% at N=8. At N=16 it is −78.6939%, but that row is diagnostic only because spread fails the all-served condition (13/16), despite all assignments being legal by mask.

## Part 4 — reward and selection objective

There is **no load, occupancy, balancing, or fairness term** in the V0.25 physical objective or C1/C3 selection factors.

The raw system objective is literally:

`return outcome.bits - eta * outcome.joules`

([targets.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/targets.py:130)); the running engine delegates to it at [run_v025_matrix_probe.py](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1149). Thus the code's raw `F` is `B - eta_ref E`; `Phi` is separate rather than literally subtracted there.

`Phi` contains only handover preferences:

`satellite_change: score -= PHI_SATELLITE_CHANGE`

`beam_change: score -= PHI_SAME_SATELLITE`

([targets.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/targets.py:72)), with costs 1.0 and 0.5 respectively ([constants_v025.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/constants_v025.py:70)). Because `phi_qos` is a higher-is-better negative score, C1 implements `physical_core/kappa + phi` ([targets.py](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/targets.py:169)); if `Phi` is instead named as a positive cost, that is algebraically `physical_core/kappa - Phi_cost`. The exact configuration factors likewise use `C1 = additive/kappa + phi` and `C3 = psi/kappa`, with no occupancy penalty ([run_v025_matrix_probe.py](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1514)). Occupancy appears only inside the physics, notably the TDM share and required-SINR calculation above.

This removal is self-consistent with the panel measurement. **On this panel an explicit load-balancing term would be actively harmful to EE because it would reward movement in the direction whose measured EE slope is negative.** The N=2 exception shows why the correct physical objective should remain authoritative: a generic load penalty cannot encode the observed flip between low occupancy and N≥4.

## What is measured, derived, and inferred

- **Verified by running code:** all table values, service guards, cap-hit rates, PA shares, active-beam ranges, slopes, and controlled comparisons.
- **Derived on paper from quoted code/constants:** `p_sat = 5.217758139277826 W`; 10.16704 J per full-interval active beam circuit; 6.016 J per full-interval active satellite; conditional `B * mean(SE)` beam-rate cancellation.
- **Inferred from the measurement:** concentration alone is not evidence of a broken learned reference here. The sibling project's cross-user z-score result cannot be imported as a collapse diagnosis without showing an EE gain under this project's current TDM, target-SINR, clipping, and energy model. On the measured development panel, the imported diagnosis points in the wrong direction.

Receipt internal canonical digest: `024cd542e9e7a9b9a9a3188ffa54405ec649206685566a134cb5393e4684ab46`. This is a design-phase measurement, not a claim.
