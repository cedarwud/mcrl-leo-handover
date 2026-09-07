# 5. Experimental Results

## 5.1 Simulation Settings

This chapter specifies the simulation environment, index domains, channel and energy-consumption model, and the settings used for training and evaluation. Chapter 3 defines the single active EE contract; this chapter supplies numerical scenarios and evaluation scope without redefining SINR, throughput, or EE.

本章說明模擬環境、索引域、通道與能耗模型，以及訓練和評估設定。第三章的 active EE 主鏈是唯一的公式契約；本章只補充數值情境與實驗評估範圍，不重新定義 SINR、throughput 或 EE。

Table 5-1 gives the numerical settings of the environment and index domains. The symbol $v$ in Chapter 3 denotes one beam index, while $V$ denotes the number of beam positions on each satellite; this study sets $V=39$. The symbols $U$, $S$, $V$, and $C$ correspond to the element counts of the respective sets.

表 5-1 列出環境與索引域的數值設定。第三章的 $v$ 表示一個波束索引，$V$ 表示每顆衛星的波束位置數；本研究設定 $V=39$。表中的 $U$、$S$、$V$ 與 $C$ 分別對應各集合的元素數。

Table 5-1. Environment and index-domain settings

表 5-1：環境與索引域設定

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

表中的兩個數字分別代表不同的模型對象：156 是視窗內可指向的衛星－波束位置總數，28 是每位使用者可選的候選動作數。

With $C=28$, the four components in Eq. (4.1)—connection, candidate SINR, off-axis angle, and previous demand—each contain 28 entries. The original state $s_u$ therefore has dimension $4C=112$. That is also the dimension of the Q-network input.

在 $C=28$ 下，式 (4.1) 的四類原始分量——前一步連線、候選 SINR、偏軸角與前一步需求——各有 28 個元素，因此 Q 網路輸入 $s_u$ 為 $4C=112$ 維。

Table 5-2 lists the experimental calibration values for the channel and energy model in Chapter 3. The main chain uses $G^{T}\!\left(\theta,\theta_{3dB}\right)$, the linear link-power factor that does not directly carry the wanted-link angular pattern $H_{u,s,v}(t)$, angle-aware $p_{u,s,v}$, the per-beam $P^{p}_{s,v}$, $P^{f}$, and $P^{N}$; the detailed channel settings in the table belong only to scenario calibration and do not expand the main formula.

表 5-2 列出第三章通道與能耗模型的實驗校準值。正文主鏈使用 $G^{T}\!\left(\theta,\theta_{3dB}\right)$、不直接承載 wanted-link 角度型樣的線性鏈路功率因子 $H_{u,s,v}(t)$、角度相關 $p_{u,s,v}$、逐波束的 $P^{p}_{s,v}$、$P^{f}$ 與 $P^{N}$；表中的細部通道設定只用於情境校準，不會擴張主公式。

Table 5-2. Channel and energy-model settings

表 5-2：通道與能耗模型設定

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

式 (3.10b) 的四項損耗中，HOBS 式 (1) 只給出名稱而未給數值；本研究以 3GPP 非地面網路報告 \[17\] 的對應表格代入 $L_g$、$L_c$ 與 $L_s$，$L_f$ 則由斜距與載波頻率直接計算。此代換是本研究的建模選擇，不是 HOBS 的原始設定。$L_s$ 與萊斯衰落 $K_R$ 是本模型僅有的兩個隨機項，實驗以固定亂數種子重現。

The active contract does not put minimum-rate inversion, beam/satellite caps, PA reference curves, or `min`/`max` projections into the EE main formula. If the legacy simulator uses such limits, they are execution history for this chapter and cannot rewrite Eqs. (3.11)–(3.17).

目前 active 契約不把最低速率反推、beam／satellite cap、PA 參考曲線或 `min`／`max` projection 放入 EE 主公式。這些限制若由 legacy simulator 使用，只能作為本章的執行歷史，不能反向改寫式 (3.11)–(3.17)。

If the existing numerical results were generated by the legacy runtime, they must be read as legacy provenance. Until runtime parity with the new contract is implemented and the experiments are rerun, the existing results are not claimed as empirical evidence for the new formulas.

本章既有數值結果若由舊版 runtime 產生，仍須以 legacy provenance 解讀；在新契約完成 runtime parity 並重新執行實驗前，不把既有結果宣稱為新版公式的實證。

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

MODQN \[2\] 報告的學習率為 0.01。本研究不逕自採用任一邊的預設值，而是把學習率列為受控變因並掃描上述三個值；主結果所採用的值於實驗完成後填入。

The frozen scale constants are $(c_1,c_2,c_3)=(2471140.576,\ 1.0,\ 6)$. Here $c_1$ is the 95th percentile of $r_{1,u}$ over 12,000 served decision steps in probe P3, $c_2=\varphi_2=1.0$ is the analytic bound for the handover cost, and $c_3=6$ is the rounded 95th percentile of $|r_{3,u}|$ from P3. They are fixed before training and shared by all update procedures; in the original units, the effective trade-off weight is $\omega_j/c_j$. Post-training effective contributions or weight shares are not available until the trained policy exists and must not be inferred from these pre-training constants.

目前凍結的尺度常數為 $(c_1,c_2,c_3)=(2471140.576,\ 1.0,\ 6)$。其中 $c_1$ 是 P3 探測在 12{,}000 個已服務決策步上的 $r_{1,u}$ 第 95 百分位數，$c_2=\varphi_2=1.0$ 是換手成本的解析上界，$c_3=6$ 是 P3 探測中 $|r_{3,u}|$ 第 95 百分位數的取整值。三者在訓練開始前固定，並由所有更新程序共用；原始單位下的有效取捨權重為 $\omega_j/c_j$。訓練後的有效貢獻或權重占比必須等訓練完成才可量測，目前尚無數值，不能由這些訓練前常數推論。

### Where the constraints bind

Whether the three constraints of this section are active is measured under the frozen scenario. The per-beam RF-output limit $p_{\max}$ fires on **113 of 12{,}000 decision steps (0.94%)**: the power the link requires exceeds the limit, the link is declared infeasible, and the user is unserved at that step.

在凍結情境下量測本節設定的三項約束是否作用。每波束射頻輸出上限 $p_{\max}$ 在 12{,}000 個決策步中的 **113 步(0.94%)** 上開火：該步所需的發射功率超過上限，該鏈路判為不可行，使用者於該步 unserved。

The peak link power among feasible steps is 1.6452 W, which uses 99.6% of the 3 dB gain budget. **This is not a near miss; it is the limit truncating the distribution**: among the steps declared infeasible, the required power has a median of 117.2% of the budget and a maximum of 214.8%. The tail of the required-power distribution reaches beyond twice the limit, and the feasible steps show only the cut left after it is removed.

可行步的峰值鏈路功率為 1.6452 W，已用掉 3 dB 增益預算的 99.6%。**這不是「差一點超過」，是上限在削頂**：被判為不可行的那些步，所需功率的中位數為預算的 117.2%、最大值 214.8%。所需功率的分布尾端伸到上限的兩倍以上，可行步只呈現它被切斷之後的切口。

These figures are bound to three things: $\Delta t=30.08$ s, the warm-start main arm, and the stay-if-possible reference policy. The policy matters most: the same settings under a random-masked reference policy give 7.60%, eight times as much, because that policy does not hold a link that has walked into good geometry. At $\Delta t=1$ s the outage rate is 0.0000, and with the warm start disabled, so that every episode boundary resets the served segment, it is also 0.0000 under the same policy (0.0016 under random-masked) with a peak reaching only 85.1% of the budget.

這組數字綁定於三件事：$\Delta t=30.08$ s、暖啟動主臂，以及 stay-if-possible 參考策略。策略的影響最大：在 random-masked 參考策略下同一組設定給出 7.60%，是前者的八倍，因為它不會保住已經走進良好幾何的鏈路。$\Delta t=1$ s 時 outage 為 0.0000；關閉暖啟動（每個 episode 的 served segment 都由邊界重置）時在同一策略下亦為 0.0000（random-masked 下為 0.0016），可行峰值只到預算的 85.1%。

The constraint fires under both sampling arms for the entry segment age. The main arm $\mathrm{Uniform}\{0,\ldots,H-1\}$ gives a mean entry age of 4.56 steps and a firing rate of 0.94%; the sensitivity arm $\mathrm{Uniform}\{0,\ldots,5\}$ gives 2.54 steps and 0.81%. The latter is the equilibrium age distribution of the measured segment length of 6 steps; the former is independent of the policy but samples ages that run old. The ages differ by a factor of 1.79 while the firing rates differ by only 1.16. The relation is a threshold rather than a linear one: raising the mean entry age from 0 to 2.54 steps takes the firing rate from 0.0000 to 0.0081, and raising it further to 4.56 steps adds only 0.0013. The constraint therefore does not fire because the main arm samples old ages. The main arm is the pre-registered main arm, and its firing rate is read as an upper bound.

進場段齡的兩條抽樣臂都會使約束開火。主臂 $\mathrm{Uniform}\{0,\ldots,H-1\}$ 的平均進場段齡為 4.56 步，開火率 0.94%；敏感度臂 $\mathrm{Uniform}\{0,\ldots,5\}$ 的平均為 2.54 步，開火率 0.81%。後者是量得段長 6 步所對應的平衡態年齡分布，前者與策略無關但年齡偏老。年齡相差 1.79 倍而開火率只相差 1.16 倍。此一關係是門檻型的而非線性的：平均段齡由 0 增至 2.54 步時開火率由 0.0000 升至 0.0081，再增至 4.56 步時只多 0.0013。因此約束會開火並非由主臂的偏老年齡撐起；主臂為預註冊之主臂，其開火率視為上界。

None of the three geometric mask terms binds in this setting, and $\left|A_u(t)\right|$ is 28 throughout. The mask and the power-feasibility rule are different mechanisms: the first decides what a user may select, the second decides whether the selected candidate becomes a connection.

三項幾何遮罩項在本情境下均不作用，$\left|A_u(t)\right|$ 恆為 28。遮罩與功率可行性是不同機制：前者決定使用者能選什麼，後者決定被選中的候選是否成為連線。
