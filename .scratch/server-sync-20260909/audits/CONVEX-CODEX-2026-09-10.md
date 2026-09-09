Interior optima exist under both SEALED and MARGIN; the finite-N optimum changes with off-axis angle (and slant range) on the tested grid.

# OCCUPANCY-CONVEXITY-2026-09-10

`DIAGNOSTIC_NOT_CLAIM` — deterministic closed-form/numeric analysis; no training, learner, or policy run.

## Result in one paragraph

At the reference isolated-link geometry (boresight, 750 km slant, 30 deg elevation), both rules have an interior energy-efficiency optimum: for N=24, both choose 4 packed beams with occupancies `3+7+7+7` under the primary fixed-cost accounting. Across N=1..24 the optimum is neither always one beam nor always one user per beam. Removing chain and baseband costs does not destroy the interior result: at N=24 both rules choose `3+7+7+7`. Thus the discrete ACM threshold/mode-capacity and PA physics—not fixed costs alone—create the interior optimum. Geometry still changes finite-population partitions because it rescales PA power relative to fixed costs and changes cap feasibility.

## Scope and production-law audit

The literal engine ID is `V025-ANGLE-RATE-TPC-TDM-ACM-STAGE2`, with primary architecture `a-r`, rather than the shortened ID in the question ([constants_v025.py:16](src/mcrl/physics_v025/constants_v025.py#L16), [constants_v025.py:18](src/mcrl/physics_v025/constants_v025.py#L18)). The sealed target is 50 Mbit/s; total bandwidth is 500 MHz with reuse 3, so one beam has B=166.6666667 MHz ([constants_v025.py:23](src/mcrl/physics_v025/constants_v025.py#L23), [constants_v025.py:25](src/mcrl/physics_v025/constants_v025.py#L25), [constants_v025.py:47](src/mcrl/physics_v025/constants_v025.py#L47)).

The TDM scheduler gives each of n beam members one equal 1/n interval ([architectures.py:268](src/mcrl/physics_v025/architectures.py#L268), [architectures.py:278](src/mcrl/physics_v025/architectures.py#L278)). Therefore required spectral efficiency is exactly `eta_req(n)=r*n/B=0.3n bit/s/Hz`, which production computes directly before choosing the lowest-threshold qualifying mode ([acm.py:77](src/mcrl/physics_v025/acm.py#L77), [acm.py:95](src/mcrl/physics_v025/acm.py#L95)). The rate endpoint sums full-band ACM rate over those slot fractions ([architectures.py:245](src/mcrl/physics_v025/architectures.py#L245)); hence this report's pooled numerator is actual delivered ACM capacity, not target-clamped `N*r*`.

The frozen EN 302 307-1 table is at [constants_v025.py:92](src/mcrl/physics_v025/constants_v025.py#L92). Production converts raw bit/symbol efficiency and ideal Es/N0 using `eta=efficiency/(1+rolloff)` and `threshold_dB=ideal+1.7-10log10(1+rolloff)` ([acm.py:30](src/mcrl/physics_v025/acm.py#L30)); roll-off 0.20 and margin 1.7 dB are sealed at [constants_v025.py:43](src/mcrl/physics_v025/constants_v025.py#L43). The maximum is 32APSK 9/10, eta=3.710855833 bit/s/Hz; n=13 is the first required SE above it. Rate-target mode choice is the minimum-threshold mode meeting required SE ([acm.py:95](src/mcrl/physics_v025/acm.py#L95)); realised decoder mode choice is separately the greatest-efficiency threshold-eligible mode ([acm.py:55](src/mcrl/physics_v025/acm.py#L55)). The lowest row is QPSK 1/4 at eta=0.408535833 bit/s/Hz and derived threshold -1.441812460476 dB. For n=1, the controller instead uses the separately rounded -1.441812460 dB PHY floor through `max(mode threshold, SINR_MIN)` ([acm.py:104](src/mcrl/physics_v025/acm.py#L104), [constants_v025.py:48](src/mcrl/physics_v025/constants_v025.py#L48)).

For an isolated beam, the coupled solver reduces analytically to `p_req=Gamma*N_noise/g_nom`; production's general update and cap are at [architectures.py:319](src/mcrl/physics_v025/architectures.py#L319) and [architectures.py:349](src/mcrl/physics_v025/architectures.py#L349). The current a-r controller always solves on nominal gains ([architectures.py:671](src/mcrl/physics_v025/architectures.py#L671)); production adds a negligible `1+2e-9` numerical clearance nudge after solving ([architectures.py:383](src/mcrl/physics_v025/architectures.py#L383)). Tables below report the mathematical threshold target exactly, without that solver-certification nudge. Inter-beam interference is zero by construction here because no cross-beam geometry was specified; this isolates the occupancy/activation trade-off asked for.

Nominal direct gain follows the provider exactly: transmit pattern times the path factor ([provider_legacy.py:725](src/mcrl/physics_v025/provider_legacy.py#L725)); the nominal path removes scintillation ([provider_legacy.py:488](src/mcrl/physics_v025/provider_legacy.py#L488)) from the inherited path factor, whose formula and constituent losses are at [link_budget.py:664](src/mcrl/env/link_budget.py#L664) and [link_budget.py:340](src/mcrl/env/link_budget.py#L340). The direct receive gain is the sealed 35 dBi peak ([provider_legacy.py:730](src/mcrl/physics_v025/provider_legacy.py#L730), [constants_v025.py:77](src/mcrl/physics_v025/constants_v025.py#L77)). The channel's free-space formula and noise formula are at [channel.py:41](src/mcrl/physics_v025/channel.py#L41) and [channel.py:49](src/mcrl/physics_v025/channel.py#L49). At the reference geometry, `g_nom=1.425834619886e-11` W/W and `N_noise=5.575393264517e-13` W.

The off-axis law uses full HPBW 3.32 deg and G0=2000 ([constants_v025.py:75](src/mcrl/physics_v025/constants_v025.py#L75)). It converts to the 1.66 deg one-sided half-power edge, sets `mu=2.07123 sin(theta)/sin(1.66 deg)`, and evaluates `G=2000[J1(mu)/(2mu)+36J3(mu)/mu^3]^2` ([channel.py:37](src/mcrl/physics_v025/channel.py#L37), [channel.py:94](src/mcrl/physics_v025/channel.py#L94), [channel.py:121](src/mcrl/physics_v025/channel.py#L121)).

The RF cap is 1.65 W; 5 dB backoff gives P_sat=5.217758139278 W and eta_max=0.35 ([constants_v025.py:34](src/mcrl/physics_v025/constants_v025.py#L34)). Supply is `sqrt(p*P_sat)/eta_max` ([energy.py:33](src/mcrl/physics_v025/energy.py#L33)). Active-chain circuit power is 0.338 W and active-satellite baseband power is 0.200 W ([constants_v025.py:38](src/mcrl/physics_v025/constants_v025.py#L38)); accounting charges circuit per positive-RF chain and baseband once per active satellite ([energy.py:111](src/mcrl/physics_v025/energy.py#L111)). Thus “always-on chain” here means always charged while the chain radiates, not while inactive.

### MARGIN is a diagnostic, not a sealed production option

No MARGIN provisioner or fading-quantile constant exists under `physics_v025`. The task-defined MARGIN calculation therefore uses the project's nearest authenticated fading quantile: elevation-specific q10 from [mechanism_corpus.py:47](src/mcrl/stagec_v025/mechanism_corpus.py#L47) and [mechanism_corpus.py:95](src/mcrl/stagec_v025/mechanism_corpus.py#L95). It is the 10th percentile of the production Rician-times-lognormal-shadow-times-deterministic-scintillation multiplier, evaluated by 192-point Gauss-Hermite quadrature and 60 bisections ([mechanism_corpus.py:53](src/mcrl/stagec_v025/mechanism_corpus.py#L53), [mechanism_corpus.py:78](src/mcrl/stagec_v025/mechanism_corpus.py#L78)). At 30 deg, `q10=0.513683388684`. MARGIN uses `p_req=Gamma*N_noise/(g_nom*q10)`, so a q10 fade lands on the same mode threshold. SEALED uses divisor 1.

## D1 — power versus occupancy

Reference geometry: isolated link, 0 deg off-axis, 750 km slant, 30 deg elevation. `RF needed` is uncapped demand; `RF radiated` and both power columns apply the 1.65 W production cap. The growth column is uncapped RF-demand growth from n to n+1.

### SEALED — nominal threshold exactly (current law)

| n | required SE (bit/s/Hz) | selected mode | target (dB) | RF needed (W) | RF radiated (W) | PA supply (W) | chain+baseband total (W) | RF x to n+1 | total x to n+1 |
|---:|---:|:---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.300000 | QPSK 1/4 | -1.441812 | 0.028056 | 0.028056 | 1.093167 | 1.631167 | 1.6032 | 1.1784 |
| 2 | 0.600000 | QPSK 2/5 | 0.608188 | 0.044981 | 0.044981 | 1.384161 | 1.922161 | 1.7906 | 1.2435 |
| 3 | 0.900000 | QPSK 3/5 | 3.138188 | 0.080542 | 0.080542 | 1.852194 | 2.390194 | 1.5136 | 1.1784 |
| 4 | 1.200000 | QPSK 3/4 | 4.938188 | 0.121906 | 0.121906 | 2.278696 | 2.816696 | 1.8155 | 1.2811 |
| 5 | 1.500000 | 8PSK 2/3 | 7.528188 | 0.221322 | 0.221322 | 3.070340 | 3.608340 | 1.3459 | 1.1362 |
| 6 | 1.800000 | 8PSK 3/4 | 8.818188 | 0.297869 | 0.297869 | 3.561939 | 4.099939 | 1.2764 | 1.1128 |
| 7 | 2.100000 | 16APSK 2/3 | 9.878188 | 0.380211 | 0.380211 | 4.024264 | 4.562264 | 1.3305 | 1.1354 |
| 8 | 2.400000 | 16APSK 3/4 | 11.118188 | 0.505854 | 0.505854 | 4.641801 | 5.179801 | 1.3804 | 1.1567 |
| 9 | 2.700000 | 16APSK 5/6 | 12.518188 | 0.698273 | 0.698273 | 5.453640 | 5.991640 | 1.2942 | 1.1253 |
| 10 | 3.000000 | 32APSK 3/4 | 13.638188 | 0.903702 | 0.903702 | 6.204210 | 6.742210 | 1.4289 | 1.1798 |
| 11 | 3.300000 | 32APSK 5/6 | 15.188188 | 1.291294 | 1.291294 | 7.416286 | 7.954286 | 1.3836 | 1.1216 |
| 12 | 3.600000 | 32APSK 8/9 | 16.598188 | 1.786591 **CAP** | 1.650000 | 8.383317 | 8.921317 | n/a | n/a |

SEALED first hits the RF cap at n=12. Required SE first exceeds the table maximum at n=13.

### MARGIN — threshold divided by elevation-specific fading q10 (diagnostic)

| n | required SE (bit/s/Hz) | selected mode | target (dB) | RF needed (W) | RF radiated (W) | PA supply (W) | chain+baseband total (W) | RF x to n+1 | total x to n+1 |
|---:|---:|:---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.300000 | QPSK 1/4 | -1.441812 | 0.054617 | 0.054617 | 1.525242 | 2.063242 | 1.6032 | 1.1968 |
| 2 | 0.600000 | QPSK 2/5 | 0.608188 | 0.087565 | 0.087565 | 1.931251 | 2.469251 | 1.7906 | 1.2645 |
| 3 | 0.900000 | QPSK 3/5 | 3.138188 | 0.156794 | 0.156794 | 2.584275 | 3.122275 | 1.5136 | 1.1906 |
| 4 | 1.200000 | QPSK 3/4 | 4.938188 | 0.237317 | 0.237317 | 3.179353 | 3.717353 | 1.8155 | 1.2971 |
| 5 | 1.500000 | 8PSK 2/3 | 7.528188 | 0.430853 | 0.430853 | 4.283894 | 4.821894 | 1.3459 | 1.1422 |
| 6 | 1.800000 | 8PSK 3/4 | 8.818188 | 0.579869 | 0.579869 | 4.969798 | 5.507798 | 1.2764 | 1.1171 |
| 7 | 2.100000 | 16APSK 2/3 | 9.878188 | 0.740167 | 0.740167 | 5.614857 | 6.152857 | 1.3305 | 1.1400 |
| 8 | 2.400000 | 16APSK 3/4 | 11.118188 | 0.984758 | 0.984758 | 6.476475 | 7.014475 | 1.3804 | 1.1615 |
| 9 | 2.700000 | 16APSK 5/6 | 12.518188 | 1.359345 | 1.359345 | 7.609195 | 8.147195 | 1.2942 | 1.0950 |
| 10 | 3.000000 | 32APSK 3/4 | 13.638188 | 1.759258 **CAP** | 1.650000 | 8.383317 | 8.921317 | 1.4289 | 1.0000 |
| 11 | 3.300000 | 32APSK 5/6 | 15.188188 | 2.513793 **CAP** | 1.650000 | 8.383317 | 8.921317 | 1.3836 | 1.0000 |
| 12 | 3.600000 | 32APSK 8/9 | 16.598188 | 3.478000 **CAP** | 1.650000 | 8.383317 | 8.921317 | n/a | n/a |

MARGIN first hits the RF cap at n=10. Required SE first exceeds the table maximum at n=13. Once capped, PA and total power remain at their cap values even though uncapped need continues to grow.

## D2 — efficiency-optimal partition, N=1..24

For partition occupancies `(n1,...,nk)`, delivered rate is `sum_b B*eta_mode(nb)` and power is `sum_b(P_PA(p_req(nb))+0.338)+0.200` W. SEALED delivery is evaluated at its nominal design point; MARGIN delivery is evaluated at the q10 fade for which it was provisioned, so each uses the target mode's production ACM capacity. All beams are packed on one active satellite, because no per-satellite beam ceiling is declared and this is the energy-minimizing placement. Infeasible occupancies (uncapped RF above 1.65 W or no ACM mode) are excluded because all N users must be served. EE is delivered bit/s divided by watts, i.e. bit/J.

| N | SEALED beams | SEALED occupancies | SEALED EE (Mbit/J) | MARGIN beams | MARGIN occupancies | MARGIN EE (Mbit/J) |
|---:|---:|:---|---:|---:|:---|---:|
| 1 | 1 | 1 | 41.742696 | 1 | 1 | 33.001126 |
| 2 | 1 | 2 | 57.040268 | 1 | 2 | 44.402354 |
| 3 | 1 | 3 | 69.049717 | 1 | 3 | 52.859605 |
| 4 | 1 | 4 | 73.346019 | 1 | 4 | 55.575428 |
| 5 | 1 | 5 | 76.236809 | 1 | 5 | 57.049850 |
| 6 | 1 | 6 | 75.479578 | 1 | 6 | 56.186098 |
| 7 | 1 | 7 | 80.284241 | 1 | 7 | 59.529728 |
| 8 | 1 | 8 | 79.548536 | 1 | 8 | 58.742177 |
| 9 | 2 | 4+5 | 77.378149 | 2 | 4+5 | 57.760829 |
| 10 | 2 | 3+7 | 78.685439 | 2 | 3+7 | 58.546821 |
| 11 | 2 | 4+7 | 79.798653 | 2 | 4+7 | 59.240843 |
| 12 | 2 | 5+7 | 80.466453 | 2 | 5+7 | 59.524924 |
| 13 | 2 | 5+8 | 80.009622 | 2 | 5+8 | 59.050539 |
| 14 | 2 | 7+7 | 82.083423 | 2 | 7+7 | 60.513226 |
| 15 | 2 | 7+8 | 81.567616 | 2 | 7+8 | 60.021864 |
| 16 | 2 | 8+8 | 81.114514 | 2 | 8+8 | 59.591731 |
| 17 | 3 | 3+7+7 | 80.757578 | 3 | 3+7+7 | 59.728419 |
| 18 | 3 | 4+7+7 | 81.373452 | 3 | 4+7+7 | 60.112991 |
| 19 | 3 | 5+7+7 | 81.703959 | 3 | 5+7+7 | 60.238388 |
| 20 | 3 | 5+7+8 | 81.341998 | 3 | 5+7+8 | 59.889603 |
| 21 | 3 | 7+7+7 | 82.701205 | 3 | 7+7+7 | 60.848320 |
| 22 | 3 | 7+7+8 | 82.319787 | 3 | 7+7+8 | 60.496295 |
| 23 | 3 | 7+8+8 | 81.970807 | 3 | 7+8+8 | 60.174936 |
| 24 | 4 | 3+7+7+7 | 81.661632 | 4 | 3+7+7+7 | 60.239512 |

This is an interior solution for both rules. The unconstrained one-beam efficiency curve peaks at n=7 for both; at N=24 each uses 4 beams with `3+7+7+7`. Over the full sweep the optimum varies with the integer remainder and ACM steps, rather than collapsing to either corner. If every beam is forced onto a distinct satellite, the extra 0.200 W per beam changes only SEALED N=9 (`4+5` to `9`) and N=24 (`3+7+7+7` to `8+8+8`), and MARGIN N=24 (`3+7+7+7` to `8+8+8`) at this geometry; all other N partitions are unchanged.

## D3 — geometry dependence

The grid spans boresight, half-radius, and the 1.66 deg beam edge, with 500/750/1000 km slants; elevation is held at 30 deg so this isolates the two requested axes and keeps q10 fixed. These are analytic link inputs, not assertions that every angle/range pair is one orbital state. Each cell below repeats the N=24 optimization; the script also repeats every N=1..24 cell when producing the change counts.

| off-axis (deg) | slant (km) | SEALED feasible max n | SEALED N=24 optimum | MARGIN feasible max n | MARGIN N=24 optimum |
|---:|---:|---:|:---|---:|:---|
| 0.00 | 500 | 12 | 3 beams: 8+8+8 | 12 | 3 beams: 8+8+8 |
| 0.00 | 750 | 11 | 4 beams: 3+7+7+7 | 9 | 4 beams: 3+7+7+7 |
| 0.00 | 1000 | 10 | 4 beams: 3+7+7+7 | 7 | 4 beams: 3+7+7+7 |
| 0.83 | 500 | 12 | 3 beams: 8+8+8 | 11 | 4 beams: 3+7+7+7 |
| 0.83 | 750 | 11 | 4 beams: 3+7+7+7 | 9 | 4 beams: 3+7+7+7 |
| 0.83 | 1000 | 9 | 4 beams: 3+7+7+7 | 7 | 4 beams: 3+7+7+7 |
| 1.66 | 500 | 12 | 3 beams: 8+8+8 | 10 | 4 beams: 3+7+7+7 |
| 1.66 | 750 | 9 | 4 beams: 3+7+7+7 | 7 | 4 beams: 3+7+7+7 |
| 1.66 | 1000 | 7 | 4 beams: 3+7+7+7 | 5 | 5 beams: 4+5+5+5+5 |

Against the reference-geometry partition at the same N, SEALED changes in 12 of 216 grid-by-N comparisons and MARGIN changes in 40 of 216. Holding slant fixed and moving off boresight changes SEALED in 8/144 comparisons (maximum active-beam change 1) and MARGIN in 26/144 (maximum 2). Holding angle fixed and increasing range changes SEALED in 17/144 comparisons (maximum 1) and MARGIN in 41/144 (maximum 2). Across the grid and N sweep, SEALED uses 1..4 active beams and MARGIN uses 1..5; singleton populations force the lower endpoint. At N=24 the grid spans 3..4 beams for SEALED and 3..5 for MARGIN, while feasible maximum occupancy spans 7..12 and 5..12 respectively. Therefore the optimum is not geometry-invariant: both angle and range can be decision-relevant through PA/fixed-cost scaling and cap feasibility, even without interference.

## D4 — zero fixed-cost discriminator

Here both 0.338 W active-chain cost and 0.200 W active-satellite baseband cost are set to zero only inside the diagnostic optimizer; all RF, ACM, cap, and PA laws remain unchanged.

| N | SEALED with fixed costs | SEALED zero fixed | MARGIN with fixed costs | MARGIN zero fixed |
|---:|:---|:---|:---|:---|
| 1 | 1: 1 | 1: 1 | 1: 1 | 1: 1 |
| 2 | 1: 2 | 1: 2 | 1: 2 | 1: 2 |
| 3 | 1: 3 | 1: 3 | 1: 3 | 1: 3 |
| 4 | 1: 4 | 1: 4 | 1: 4 | 1: 4 |
| 5 | 1: 5 | 1: 5 | 1: 5 | 1: 5 |
| 6 | 1: 6 | 2: 3+3 | 1: 6 | 2: 3+3 |
| 7 | 1: 7 | 1: 7 | 1: 7 | 1: 7 |
| 8 | 1: 8 | 2: 4+4 | 1: 8 | 2: 4+4 |
| 9 | 2: 4+5 | 2: 4+5 | 2: 4+5 | 2: 4+5 |
| 10 | 2: 3+7 | 2: 3+7 | 2: 3+7 | 2: 3+7 |
| 11 | 2: 4+7 | 2: 4+7 | 2: 4+7 | 2: 4+7 |
| 12 | 2: 5+7 | 3: 4+4+4 | 2: 5+7 | 3: 4+4+4 |
| 13 | 2: 5+8 | 3: 4+4+5 | 2: 5+8 | 3: 4+4+5 |
| 14 | 2: 7+7 | 2: 7+7 | 2: 7+7 | 2: 7+7 |
| 15 | 2: 7+8 | 3: 4+4+7 | 2: 7+8 | 3: 4+4+7 |
| 16 | 2: 8+8 | 4: 4+4+4+4 | 2: 8+8 | 4: 4+4+4+4 |
| 17 | 3: 3+7+7 | 3: 3+7+7 | 3: 3+7+7 | 3: 3+7+7 |
| 18 | 3: 4+7+7 | 3: 4+7+7 | 3: 4+7+7 | 3: 4+7+7 |
| 19 | 3: 5+7+7 | 4: 4+4+4+7 | 3: 5+7+7 | 4: 4+4+4+7 |
| 20 | 3: 5+7+8 | 5: 4+4+4+4+4 | 3: 5+7+8 | 5: 4+4+4+4+4 |
| 21 | 3: 7+7+7 | 3: 7+7+7 | 3: 7+7+7 | 3: 7+7+7 |
| 22 | 3: 7+7+8 | 4: 4+4+7+7 | 3: 7+7+8 | 4: 4+4+7+7 |
| 23 | 3: 7+8+8 | 5: 4+4+4+4+7 | 3: 7+8+8 | 5: 4+4+4+4+7 |
| 24 | 4: 3+7+7+7 | 4: 3+7+7+7 | 4: 3+7+7+7 | 4: 3+7+7+7 |

The interior optimum survives. At N=24, SEALED remains `3+7+7+7` and MARGIN remains `3+7+7+7` after fixed costs are removed; neither becomes one beam or 24 singleton beams. The zero-fixed-cost partitions are identical between SEALED and MARGIN because MARGIN multiplies every feasible RF requirement by the same 1/q10 at fixed elevation, and the square-root PA law therefore multiplies every beam's supply by the same `1/sqrt(q10)`. The discriminator says the interior is driven by discrete mode/capacity thresholds plus the PA law; fixed costs shift the selected mix at other N but do not create the interior.

## Reproduction

From `/home/sat/mcrl-v025-arch-ws`:

```bash
nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python scripts/run_occupancy_convexity.py
```

The program prints this report. It imports the production ACM, antenna/noise, nominal-path, PA-supply, and authenticated q10 functions; exhaustive integer partition enumeration is local diagnostic logic. No sealed artifact is modified.

Saved as [OCCUPANCY-CONVEXITY-2026-09-10.md](/home/sat/mcrl-v025-arch-ws/OCCUPANCY-CONVEXITY-2026-09-10.md) with generator [run_occupancy_convexity.py](/home/sat/mcrl-v025-arch-ws/scripts/run_occupancy_convexity.py). The report reproduces byte-for-byte, and 58 relevant production-physics tests pass. The research skill’s source-first audit materially established that MARGIN/q10 is diagnostic rather than part of the sealed `physics_v025` provisioner.
