# 5. Experimental Results

## 5.1 Simulation Settings

This chapter specifies the simulation environment, index domains, channel and energy-consumption model, and the settings used for training and evaluation. Chapter 3 defines the single active EE contract; this chapter supplies numerical scenarios and evaluation scope without redefining SINR, throughput, or EE.

Table 5-1 gives the numerical settings of the environment and index domains. The symbol $v$ in Chapter 3 denotes one beam index, while $V$ denotes the number of beam positions on each satellite; this study sets $V=39$. The symbols $U$, $S$, $V$, and $C$ correspond to the element counts of the respective sets.

Table 5-1. Environment and index-domain settings

| Category | Symbol or relation | Setting in this study |
|---|---|---|
| Satellite constellation | $S$ | Real Starlink ephemerides (TLE with SGP4), 373 daily files covering 2025-07-27 to 2026-08-20; inclination about 53 degrees |
| Satellite altitude | $h_s$ | Determined by the ephemerides rather than set. The daily median altitude over the corpus is 483.0 km, and those daily medians range from 470.7 to 539.7 km; the instantaneous altitudes of individual satellites spread wider than that range |
| Visible-satellite window | $L_w$ | 4 |
| Ground users | $U$ | 100 |
| Beam-pointing locations per satellite | $V$ | 39. Coverage is measured directly on the cell lattice at $h_s=483$ km, where 39 cells cover 95.2% of the service area. The lattice takes $R_b$ as the circumradius of the hexagonal cell, so the centre spacing is $\sqrt{3}R_b=24.24$ km and one cell covers 509.0 km$^2$; each cell is then inscribed in its own 3 dB contour and no coverage hole is left. The same area ratio gives $18000\times0.95/509.0=33.6$ cells, below the measured value, because it ignores the edge spill when the lattice is clipped to the rectangular service area; the measurement governs |
| Local candidate ranks per window satellite | $J_w$ | 7 (the beam location nearest the user and its six adjacent locations) |
| Candidate action domain | $C=L_wJ_w$ | $4\times7=28$ |
| Pointing combinations in the window | $L_wV$ | $4\times39=156$ satellite--beam-location pairs |
| Time discretization | $\Delta t$, $H$ | 30.08 s per step and 10 steps per episode |

The two numbers refer to different model objects: 156 possible satellite--beam-location pairs in the current window, and 28 candidate actions available to each user at decision time.

With $C=28$, the four components in Eq. (4.1)—connection, candidate SINR, off-axis angle, and previous demand—each contain 28 entries. The original state $s_u$ therefore has dimension $4C=112$. That is also the dimension of the Q-network input.

Table 5-2 lists the experimental calibration values for the channel and energy model in Chapter 3. The main chain uses $G^{T}\!\left(\theta,\theta_{3dB}\right)$, the linear link-power factor that does not directly carry the wanted-link angular pattern $H_{u,s,v}(t)$, angle-aware $p_{u,s,v}$, the per-beam $P^{p}_{s,v}$, $P^{f}$, and $P^{N}$; the detailed channel settings in the table belong only to scenario calibration and do not expand the main formula.

Table 5-2. Channel and energy-model settings

| Category | Symbol or relation | Setting in this study |
|---|---|---|
| Carrier and bandwidth | $f_c$, $B_{\mathrm{sys}}$ | 20 GHz and 500 MHz |
| Gaseous atmospheric absorption | $L_g(\alpha)=A_{\mathrm{zen}}/\sin\alpha$ | $A_{\mathrm{zen}}=0.25$ dB. The form is Eq. (6.6-8) of TR 38.811 \[17\]; the zenith value is recovered from the LEO Ka-band 20 GHz downlink link budget of TR 38.821 \[22\], whose atmospheric loss is 0.5 dB at the LEO target elevation of 30 degrees |
| Scintillation | $L_c(\alpha)$ | Tropospheric scintillation at 20 GHz from Table 6.6.6.2.1-1 of TR 38.811 \[17\]: 0.12 dB at 90 degrees, 0.30 dB at 30 degrees and 1.08 dB at 10 degrees of elevation. Section 6.6.6.1 of the same report considers ionospheric scintillation only below 6 GHz, so it is not counted at 20 GHz |
| Shadow fading | $L_s(\alpha)$ | Ka-band LOS shadow fading from Table 6.6.2-3 of TR 38.811 \[17\], zero-mean Gaussian in dB, with a standard deviation from 0.4 dB at 90 degrees to 1.9 dB at 10 degrees of elevation. Clutter loss applies only to NLOS and is not counted for a fixed LOS terminal |
| Frequency reuse | $c_{s,v}$, $B^{w}$ | Three-color reuse and 166.667 MHz |
| Beamwidth and beam coverage radius | $\theta_{3dB}$, $R_b=h_s\tan(\theta_{3dB}/2)$ | 3.32 degrees and 13.998 km at $h_s=483$ km |
| Boresight gain | $G_0$ | 2000 in linear scale, or 33.010 dBi |
| Receive-gain limits | $G_{R,\max}$, $G_{R,\min}$ | 35 dBi and $-10$ dBi; the clipping values in (3.10c) |
| Receive-gain envelope | $A_R$, $B_R$ | 32 and 25; earth-station reference-pattern parameters of (3.10c), absorbed into $H_{u,s,v}(t)$ |
| Boresight-limit threshold | $\epsilon_\mu$ | $10^{-10}$ |
| Rician fading | $K_R$ | 20 dB |
| Receiver system temperature | $T_a$, $T_0$, $NF$, $T$ | 150 K, 290 K, 1.2 dB, and 242.294 K |
| Fixed power | $P^{f}(t)$ | Aggregate of RF-chain, baseband, and other fixed circuit terms |
| Segment-start transmit power | $p^{0}$ | 0.825 W, that is $p_{\max}/2$; the starting value of every new served segment in Eq. (3.11). $p_{\max}/p^{0}=2$ gives every served segment a 3 dB gain budget; 3 dB is the beam's own half-power contour ($F=1/2$ exactly at $\mu=2.07123$, that is at $\theta=\theta_{3dB}/2$, whose ground radius is $R_b$), so the size of the budget is fixed by geometry rather than chosen. The budget is measured against the **segment-start angle** $\theta_{u,s,v}(\tau_{u,s,v})$, not against the beam axis: the numerator of Eq. (3.12) is $G^{T}\!\left(\theta_{u,s,v}(\tau_{u,s,v})\right)$ and not $G_0$, so the infeasibility test reads "the gain has fallen 3 dB since the link was taken up", which coincides with "has left this cell" only when the segment starts on the axis |
| Per-beam RF-output limit | $p_{\max}$ | 1.65 W; the per-beam operating limit after back-off in Eq. (3.15a), and the threshold of the link-feasibility check. At $V=39$ a satellite radiating every beam at that limit draws $39\times1.65=64.3$ W, below the LEO maximum transmit power $P_{\max}=50$ dBm $=100$ W of Table I of HOBS \[4\], so the per-beam limit is consistent with the per-satellite power budget of the cited work; this study sets no per-satellite limit of its own (see the exclusions below Eq. (3.11)), and the comparison is a budget check only |
| PA maximum efficiency and output back-off | $\xi_{\max}$, $BO$ | 0.35 and 5 dB; Eq. (3.15a), with saturated power $p_{\mathrm{sat}}=p_{\max}10^{BO/10}=5.218$ W |
| Circuit power per active beam | $P_{\mathrm{cir}}$ | 0.338 W ($300+19+14+5$ mW, Table II of You et al. \[26\]); Eq. (3.16a) |
| Shared baseband power per satellite | $P_{\mathrm{BB}}$ | 0.200 W \[26\]; Eq. (3.16a) |

Of the four losses of Eq. (3.10b), Eq. (1) of HOBS gives names but no values; this study substitutes the corresponding tables of the 3GPP non-terrestrial network report \[17\] for $L_g$, $L_c$ and $L_s$, while $L_f$ is computed directly from the slant range and the carrier frequency. This substitution is a modelling choice of this study rather than the original setting of HOBS. $L_s$ and the Rician fading $K_R$ are the only two random terms in this model, and the experiments reproduce them from fixed random seeds.

The active contract does not put minimum-rate inversion, beam/satellite caps, PA reference curves, or `min`/`max` projections into the EE main formula. If the legacy simulator uses such limits, they are execution history for this chapter and cannot rewrite Eqs. (3.11)–(3.17).

If the existing numerical results were generated by the legacy runtime, they must be read as legacy provenance. Until runtime parity with the new contract is implemented and the experiments are rerun, the existing results are not claimed as empirical evidence for the new formulas.

| Legacy execution settings (Chapter 5 provenance only) | Symbol | Historical setting |
|---|---|---|
| Minimum-rate threshold | $R^{m}$ | 1 Mbit/s |
| PA reference output power | $P_0$ | 5.218 W; the old runtime's name for the $p_{\mathrm{sat}}$ of Eq. (3.15a), with the same value |
| Atmospheric attenuation (legacy form) | $\chi_{\mathrm{atm}}$; $L^{\mathrm{atm}}=3d^{\mathrm{km}}\chi_{\mathrm{atm}}/(10h_s^{\mathrm{km}})$ | $\chi_{\mathrm{atm}}=0.05$. This form yields only 0.015 dB at zenith, an equivalent atmospheric thickness of 0.3 km, which does not match the magnitude of gaseous absorption at 20 GHz; it is superseded by the cosecant law of Table 5-2 |
| Satellite-total RF-output limit | $P_{\mathrm{sat},\max}$ | $10^{13/10}=19.953$ W |
| PA reference efficiency (legacy) | $\eta_0$ | 0.35; superseded by $\xi_{\max}$ |

Table 5-3. Method and evaluation settings

| Category | Symbol | Setting in this study |
|---|---|---|
| Three-objective scalarization weights | $\Omega=(\omega_1,\omega_2,\omega_3)$ | $(0.5,0.3,0.2)$ |
| Handover costs | $(\varphi_1,\varphi_2)$ | 0.5 for an intra-satellite beam change and 1.0 for an inter-satellite handover |
| Network architecture | — | Every Q-network on both the main and catfish sides uses hidden layers of 100, 50, and 50 units |
| Learning and batch | $B$ | The learning rate is a controlled variable swept over $\{0.01,0.003,0.001\}$; the batch size is $B=128$ |
| Exploration and target networks | $\epsilon$, $K$ | $\epsilon$ decays linearly from 1 to 0.01 over 2000 episodes; target synchronization every 50 episodes |
| Training horizon | $E$, $H$ | 9000 episodes and 10 steps per episode |
| Main and catfish discounts | $\beta_M$, $\beta_{F}$ | 0.90 and 0.99 |
| Energy-efficiency stratification | $q_1$, $q_2$, $W$ | 0.50, 0.80, and 5000 transition bundles |
| Periodic intervention | $\rho_I$, $[T_1,T_2]$ | Catfish share 0.30; interval sampled uniformly from 4 to 16 steps |
| Competitive reward | $\eta_w$ | 1.0 |
| Objective scale constants | $(c_1,c_2,c_3)$ | $(2471140.576,\ 1.0,\ 6)$; obtained from P3 and the analytic bound, frozen before training |

MODQN \[2\] reports a learning rate of 0.01. This study adopts neither default outright: the learning rate is treated as a controlled variable and swept over the three values above, and the value used for the main results is filled in once the experiments are complete.

The frozen scale constants are $(c_1,c_2,c_3)=(2471140.576,\ 1.0,\ 6)$. Here $c_1$ is the 95th percentile of $r_{1,u}$ over 12,000 served decision steps in probe P3, $c_2=\varphi_2=1.0$ is the analytic bound for the handover cost, and $c_3=6$ is the rounded 95th percentile of $|r_{3,u}|$ from P3. They are fixed before training and shared by all update procedures; in the original units, the effective trade-off weight is $\omega_j/c_j$. Post-training effective contributions or weight shares are not available until the trained policy exists and must not be inferred from these pre-training constants.

### Where the constraints bind

Whether the three constraints of this section are active is measured under the frozen scenario. The per-beam RF-output limit $p_{\max}$ fires on **113 of 12{,}000 decision steps (0.94%)**: the power the link requires exceeds the limit, the link is declared infeasible, and the user is unserved at that step.

The peak link power among feasible steps is 1.6452 W, which uses 99.6% of the 3 dB gain budget. **This is not a near miss; it is the limit truncating the distribution**: among the steps declared infeasible, the required power has a median of 117.2% of the budget and a maximum of 214.8%. The tail of the required-power distribution reaches beyond twice the limit, and the feasible steps show only the cut left after it is removed.

These figures are bound to three things: $\Delta t=30.08$ s, the warm-start main arm, and the stay-if-possible reference policy. The policy matters most: the same settings under a random-masked reference policy give 7.60%, eight times as much, because that policy does not hold a link that has walked into good geometry. At $\Delta t=1$ s the outage rate is 0.0000, and with the warm start disabled, so that every episode boundary resets the served segment, it is also 0.0000 under the same policy (0.0016 under random-masked) with a peak reaching only 85.1% of the budget.

The constraint fires under both sampling arms for the entry segment age. The main arm $\mathrm{Uniform}\{0,\ldots,H-1\}$ gives a mean entry age of 4.56 steps and a firing rate of 0.94%; the sensitivity arm $\mathrm{Uniform}\{0,\ldots,5\}$ gives 2.54 steps and 0.81%. The latter is the equilibrium age distribution of the measured segment length of 6 steps; the former is independent of the policy but samples ages that run old. The ages differ by a factor of 1.79 while the firing rates differ by only 1.16. The relation is a threshold rather than a linear one: raising the mean entry age from 0 to 2.54 steps takes the firing rate from 0.0000 to 0.0081, and raising it further to 4.56 steps adds only 0.0013. The constraint therefore does not fire because the main arm samples old ages. The main arm is the pre-registered main arm, and its firing rate is read as an upper bound.

None of the three geometric mask terms binds in this setting, and $\left|A_u(t)\right|$ is 28 throughout. The mask and the power-feasibility rule are different mechanisms: the first decides what a user may select, the second decides whether the selected candidate becomes a connection.
