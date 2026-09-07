國立臺北大學資訊工程學系

Department of Computer Science & Information Engineering

National Taipei University

碩士論文

Master Thesis

指導教授：陳裕賢 博士

Advisor：Dr. Yuh-Shyan Chen

低軌多波束衛星網路之節能換手使用鯰魚多目標強化式學習

Energy-Efficient Handover in Multi-Beam LEO Satellite Networks:
A Multi-Catfish Reinforcement Learning Approach

研究生：吳柏宏

Student：Bo-Hung, Wu

中華民國 115 年 7 月

July, 2026

# Abstract

Low Earth Orbit (LEO) satellite networks offer wide coverage and low latency, but the high speed of the satellites causes rapidly changing beam coverage, so handovers are frequent and hard to decide. The existing Multi-Objective Deep Q-Learning Network (MODQN) models this problem with three reward terms — throughput, handover cost, and load balancing — yet the throughput reward reflects little of how beam off-axis angle and interference affect energy efficiency. Each user also takes its own arg max without seeing the choices of others, so users tend to point at the same beam and over-concentrate, users on one beam share its bandwidth, so concentration directly lowers each of their rates, while the learning side never sees what the other users choose at that step. This baseline is extended into a Multi-Catfish Reinforcement Learning (MCRL) framework. On the reward side, throughput is replaced with angle-aware energy efficiency, and transmit power is determined directly by link angle gain: each uninterrupted served physical-link segment starts at the segment-start power $p^{0}$, and only consecutive service of the same physical link uses the previous-step power and angle-gain recurrence. When off-axis angle reduces beam gain, the recurrence can raise RF power within a continuing segment, while realized SINR, throughput, and system consumption jointly determine energy efficiency, handover, outage, unserved steps, re-entry, and episode reset restart the segment. At training time, the main side and the catfish side are each a three-objective MODQN: their three Q-networks map one-to-one to energy efficiency, handover, and load balancing, while the three catfish-side networks share one environment trajectory and one replay buffer. Experience shaping uses energy-efficiency stratification, asymmetric discounting, and periodic mixed-batch intervention, reward shaping adds a paired competitive term only to the catfish-side energy-efficiency reward. Both operate only during training, the deployment rule is unchanged.

Keywords: Low Earth Orbit Satellite, Multi-Beam Network, Handover Decision, Multi-Objective Reinforcement Learning, MODQN, Multi-Catfish, Load Balancing, Energy Efficiency

低軌衛星（LEO）網路覆蓋廣、延遲較低，但衛星高速移動使波束覆蓋快速變化，換手因而頻繁且不易決策。既有的多目標深度 Q 學習網路（Multi-Objective Deep Q-Learning Network, MODQN）以吞吐量、換手成本與負載平衡三個獎勵項建模此問題，但吞吐量獎勵未反映偏軸角與干擾對能量效率的影響。每位使用者又各自取最大值、看不到彼此的選擇，容易一起指向同一波束而過度集中；同一波束上的使用者均分頻寬，集中會直接壓低每個人的速率，而學習端從訓練到部署都看不到其他使用者當步的選擇。以該方法為基準，擴充為鯰魚多目標強化式學習（Multi-Catfish Reinforcement Learning, MCRL）框架。獎勵端把吞吐量改為角度感知能量效率，並由鏈路角度增益直接決定發射功率：每一段 uninterrupted served physical link 以固定的段起始功率 $p^{0}$ 起始，只有連續同一實體鏈路時才依前一步功率與角度增益比遞推。偏軸角降低波束增益時，同一連續服務段的遞推功率可能上升，並與實際 SINR、吞吐量及系統耗能共同改變能量效率；handover、outage、unserved、re-entry 與 episode reset 都重新起始。訓練時，主代理與鯰魚代理各是一組三目標 MODQN：兩端的三個 Q 網路均與能量效率、換手及負載平衡一一對應，鯰魚代理三網路則共用一條環境軌跡與一個經驗池。經驗塑形採能效分層、非對稱折扣與週期性混合批次介入，獎勵塑形只在鯰魚代理能效獎勵加入配對競爭項，兩者都只在訓練期作用，部署選法不變。

關鍵字：低軌衛星、多波束網路、換手決策、多目標強化式學習、MODQN、Multi-Catfish、負載平衡、能量效率

# 1. Introduction

In recent years, mobile communications have advanced toward sixth-generation systems and non-terrestrial networks. Low Earth Orbit (LEO) satellites provide broad coverage and low propagation delay, and can serve remote areas, maritime regions, and airspace where ground infrastructure is difficult to deploy, which is why they have drawn attention. However, LEO satellites orbit at high speed, causing the available satellites and beams to change continuously, making connection maintenance and handover decisions more difficult.

In multi-beam LEO satellite systems, a single satellite serves different geographic regions using multiple beams, and users may require handover between beams or satellites due to satellite movement, coverage boundary changes, or degrading service quality. Using signal strength alone for beam selection may cause excessive load on certain beams, prioritizing handover reduction may leave users on progressively degrading connections, focusing on load balancing may sacrifice transmission quality for some users. Therefore, multi-beam LEO handover should not rely on a single metric but must simultaneously consider multiple objectives such as throughput, handover cost, and load balancing.

To address this type of dynamic decision problem, existing studies have approached LEO satellite handover through deep reinforcement learning and multi-objective learning, respectively emphasizing access delay and collisions, and throughput and handover cost \[1\], \[2\]. Among them, Sun et al. formulated multi-beam LEO satellite handover as a multi-objective deep-reinforcement-learning problem using a Multi-Objective Deep Q-Learning Network (MODQN) \[2\].

Energy-aware, beam-gain, and spectrum-coexistence studies further show that link geometry, power cost, and interference affect handover and energy evaluation \[3\], \[4\], \[5\]. Handover work under dynamic propagation emphasizes channel state and load \[6\], while beam management under stochastic traffic and time-varying topology highlights the tradeoff among service quality, load, and system resources \[7\]. These studies, however, mostly address individual parts of the problem, a framework that jointly connects off-axis angle, transmit power determined directly by angle gain, and MODQN-based multi-objective training for multi-beam LEO satellite handover remains absent.

This study therefore extends the MODQN baseline into Multi-Catfish Reinforcement Learning (MCRL), modifying the reward and the training procedure to address energy efficiency and beam concentration. The main contributions are as follows:

- MCRL retains MODQN's multi-objective reinforcement-learning architecture and replaces the first reward term with angle-aware energy efficiency. Each uninterrupted served physical-link segment starts at the segment-start power $p^{0}$, and consecutive service of the same link applies the previous-step power and angle-gain recurrence, the same realized power then determines interference, throughput, and system power consumption, with no cap, clip, or projection in the physical formula.
- MCRL retains the deployment rule in which each user independently selects its maximum-valued action. Training adds experience shaping and reward shaping, and **both act only during training**, the input representation and the selection rule at deployment are the same as in MODQN.

The remaining chapters are organized as follows. Chapter 2 reviews related work on LEO satellite handover, multi-beam resource management, energy efficiency, and reinforcement learning. Chapter 3 describes the system model and problem formulation. Chapter 4 introduces the MCRL method. Chapter 5 describes the simulation settings and evaluation procedure. Chapter 6 summarizes the study and discusses limitations and future directions.

# 2. Background

This chapter reviews LEO satellite handover, multi-objective reinforcement learning, catfish competitive learning, and capacity-constrained decisions, then positions the problem addressed in this study.

## 2.1 Related Work

LEO satellite handover involves high-speed satellite motion, changing beam coverage, user connection quality, and system load. Existing studies have applied deep reinforcement learning directly to handover decisions. Lee et al. \[1\] learned handover protocols that reduce access delay and collisions. Learning through interaction with the environment helps these methods adapt to time-varying communication conditions.

As energy costs receive attention, handover decisions have also begun incorporating energy considerations. Ntabeni et al. \[3\] proposed energy-aware Q-learning that jointly considers signal quality, handover frequency, and energy efficiency. Chen et al. \[4\] proposed a joint LEO handover and fast beam switching (HOBS) algorithm that uses historical signal-quality and beam-index information to narrow the search range and reduce beam-training latency, it also accounts for signal-to-interference-plus-noise ratio, beam transmit power, beam gain, beam switching, and both intra-satellite and inter-satellite interference. Mendonça et al. \[5\] considered off-axis antenna loss and interference management in spectrum-coexistence handover, showing that beam angle and interference affect handover decisions. Liu et al. \[6\] used multi-agent deep reinforcement learning with a three-state Markov model of dynamic propagation conditions, allowing decisions to consider channel state, load, and handover performance. The channel, interference, and power models in Chapter 3 draw on these treatments of signal quality and beam power.

Multi-objective reinforcement learning addresses the trade-offs among transmission performance, handover cost, and load distribution. Sun et al. \[2\] formulated LEO multi-beam handover as a multi-objective deep-reinforcement-learning problem in MODQN, using throughput, handover cost, and load balancing as three reward terms and learning their action values with three parallel Q-networks. Because it addresses the same handover setting and objectives, MODQN is the primary baseline for this study. Song et al. \[8\] also incorporated throughput, handover frequency, and load balancing into multi-objective handover. Tajmajer \[9\] used decision values for modular scalarization, whereas Basaklar et al. \[10\] processed the objectives separately during learning rather than combining them into a single scalar at the outset. MCRL retains MODQN's three objective networks and linear scalarization, while changing the first reward and the training procedure.

The MODQN baseline backbone used in this study is shown in Fig. 2-1. Three Q-networks estimate action values for energy efficiency, handover, and load balancing, which are scalarized by weights $\Omega$ and selected with $\epsilon$-greedy exploration. The environment returns a three-dimensional reward and the next state, after transitions enter replay, target networks construct temporal-difference targets for updating the three online networks. The first objective in the figure uses the angle-aware energy efficiency defined in this study, the additional MCRL training mechanisms are described in Chapter 4.

![Fig. 2-1 MODQN baseline used in this study](figures/0727/fig2-1_modqn-baseline.png){width=155mm}

Fig. 2-1: MODQN baseline backbone used in this study. The three objective Q-networks share state input and a feasible-action mask, then scalarize with weights $\Omega$ to select actions. Environment transitions enter replay, and the three online/target network pairs update with their respective objective rewards. The first objective shows the angle-aware energy efficiency adopted here, which differs from the original MODQN throughput objective, no additional MCRL training-time shaping is included.

The selection and use of training experience also influence the learned policy. Schaul et al. \[11\] proposed prioritized experience replay, adjusting sampling probabilities from temporal-difference errors so that more informative transitions are used more often. Ke \[12\] proposed Catfish Deep Reinforcement Learning (CDRL), which introduces a catfish role during training to promote exploration and experience use without directly producing deployment decisions. CDRL was originally applied to energy-efficient control in RIS-aided communications. This study extends that auxiliary-training approach to multi-objective handover: both the main and catfish agents are three-objective MODQNs, and the three networks within each agent correspond to the three objectives. In entity-based multi-agent reinforcement learning, a user, satellite, or beam is chosen as the agent unit and multiple agents make decisions jointly. The two MCRL agents instead serve as training roles for the same handover problem, neither controls one particular network entity. The catfish agent supplies additional experience and competitive signals during training, while the main agent continues to learn from its own experience. Chapter 4 describes these mechanisms.

Capacity and resource constraints are another important issue in multi-beam systems. Zhu et al. \[7\] studied beam management under stochastic traffic arrivals and time-varying topology, balancing service quality, beam load, and system resources. For reinforcement-learning problems with constraints, Calvo-Fullana et al. \[13\] added constraint information to the state, and Agorio et al. \[14\] applied the same approach to multi-agent assignment. Holder et al. \[15\] used reinforcement learning for satellite assignment under limited resources, while Ye et al. \[16\] studied load-aware user association in cellular networks. The training-shaping strategies in Chapter 4 draw on these approaches.

## 2.2 Motivation

Taken together, the studies reviewed in Section 2.1 reveal three issues that have not been addressed jointly. First, the first reward in existing multi-objective handover methods is often still throughput-centered, while energy-aware work less often connects angle gain, off-axis-induced power changes, interference, realized throughput, and system energy consumption in a single energy-efficiency chain. Second, MODQN's three objectives generally use the same learning workflow, while prior catfish-style auxiliary learning has mainly been studied in single-objective problems, objective-wise auxiliary training has not yet been defined. Third, independent per-user selection cannot directly see the other users' choices or the resulting beam congestion at the same time step. Existing constraint approaches often change the deployment-time assignment procedure or add constraint information to the state, fewer address it while retaining the original deployment rule.

MCRL addresses these problems through two design choices. First, it replaces the first reward with each user's additive contribution to angle-aware system energy efficiency, so that the link-quality and power costs caused by off-axis angle enter the same objective. Second, in Multi-Catfish training, both the main and catfish sides use three-objective MODQNs, whose three Q-networks correspond to energy efficiency, handover, and load balancing. The training process includes experience shaping and reward shaping: experience shaping uses energy-efficiency stratification, asymmetric discounting, and periodic mixed-batch intervention to change the experiences used during training, reward shaping adds a same-state competitive comparison only to the catfish side's first objective, thereby aligning the auxiliary training with the corresponding objectives. The two shaping strategies act only during training. At deployment, only the main agent is retained and each user still takes its own argmax.

A larger off-axis angle reduces beam gain and can lower the received signal power, SINR, and throughput. Within a continuing served segment, a lower current gain than the previous gain can raise RF power under the previous-step recurrence and may increase power-amplifier consumption. A new segment does not retain inactive-link power and instead restarts at $p^{0}$, the recurrence has no power cap, clip, or projection. Section 3.1.3 gives the complete model, and Section 3.2 defines the formal reward.

# 3. Preliminaries

This chapter first explains how a user selects a service beam from the visible beams. It then introduces the signal quality, throughput, and power consumption of the selected link. Finally, these quantities are organized into the three objectives of energy efficiency, handover cost, and load balancing.

## 3.1 System Model

### 3.1.1 Network Model

Consider a downlink multi-beam LEO satellite communication system. Because the satellites keep moving, the satellites and beams visible to each user change over time. Time is discretized into successive steps of length $\Delta t$, and the system selects one available service beam for each user at every step, the value of $\Delta t$ is given in Section 5.1. The overall scenario is shown in Fig. 3-1.

![Fig. 3-1 LEO multi-beam satellite system model](figures/0727/03_fig3-1__mcrl.png){width=165mm}

Fig. 3-1: System model of a multi-beam LEO satellite network. Each user selects a service beam from the candidates provided by visible satellites. Beam direction affects signal quality, and users selecting the same beam share its resources. The system must also account for beam interference and handover cost, a beam that no user selects is not activated.

#### Users, Satellites, and Beams

Let $\mathcal{U}=\{1,\ldots,U\}$, $\mathcal{S}=\{1,\ldots,S\}$, and $\mathcal{V}=\{1,\ldots,V\}$ denote the user, satellite, and beam-index sets, respectively. The symbols $u$, $s$, $v$, and $t$ denote user, satellite, beam, and time-step indices.

Let $x_{u,s,v}(t)$ represent the realized connection. When $x_{u,s,v}(t)=1$, user $u$ is served by beam $v$ of satellite $s$, otherwise it is 0. Each user can connect to at most one beam, so

$$
x_{u,s,v}(t) \in \{0,1\},\qquad
\sum_{s \in \mathcal{S}}\sum_{v \in \mathcal{V}}x_{u,s,v}(t) \leq 1.
\tag{3.1}
$$

Let $z_{s,v}(t)$ indicate whether beam $(s,v)$ is active. For every $u\in \mathcal{U}$, $s\in \mathcal{S}$, and $v\in \mathcal{V}$, a user can connect only to an active beam, so

$$
z_{s,v}(t)\in\{0,1\},\qquad
x_{u,s,v}(t)\le z_{s,v}(t).
\tag{3.2}
$$

#### Beam Activation and Load

The number of users actually served by beam $(s,v)$ is

$$
U_{s,v}(t) = \sum_{u \in \mathcal{U}}x_{u,s,v}(t).
\tag{3.3}
$$

This study activates only beams with connected users, so beam activation follows directly from the connection result:

$$
z_{s,v}(t)=
\begin{cases}
1,& U_{s,v}(t)>0,\\
0,& U_{s,v}(t)=0,
\end{cases}
\qquad \forall s \in \mathcal{S},\ v \in \mathcal{V}.
\tag{3.4}
$$

A beam with no users transmits no power and creates no interference. This study sets no separate upper bound on how many beams one satellite may activate at the same time.

### 3.1.2 Geometry and Channel Model

In LEO satellite communications, geometry determines both the distance between a user and a satellite and the user's direction relative to a beam center. Following non-terrestrial network channel models and LEO satellite research \[17\], \[18\], the slant range between user $u$ and satellite $s$ is defined as in (3.5):

$$
d_{u,s,v}(t) = \sqrt{R_{E}^{2}{\sin}^{2}\alpha_{u,s}(t) + h_{s}^{2} + 2R_{E}h_{s}} - R_{E}\sin\alpha_{u,s}(t).
\tag{3.5}
$$

Here, $\alpha_{u,s}(t)$ is the elevation angle of the user relative to the satellite, $R_{E}$ is the Earth's radius, and $h_{s}$ is the satellite altitude. The index $v$ records the slant range at the candidate-link level, its value may be identical across beams on the same satellite. The slant range is one component of the linear link-power factor used below, which does not directly carry the wanted-link angular pattern.

The off-axis angle describes the angular difference between the user's direction and the beam-center direction. A multibeam LEO model defines this angle through the arccosine of two direction vectors \[19, Eq. (5)\], so the off-axis angle of user $u$ relative to beam $(s,v)$ is defined as in (3.6):

$$
\theta_{u,s,v}(t) = \arccos\left( \frac{\mathbf{v}_{u,s,v}(t) \cdot \mathbf{r}_{u,s,v}(t)}{\parallel \mathbf{v}_{u,s,v}(t) \parallel \parallel \mathbf{r}_{u,s,v}(t) \parallel} \right).
\tag{3.6}
$$

Here, $\mathbf{v}_{u,s,v}(t)$ is the beam-center direction recorded for candidate link $(u,s,v)$, and $\mathbf{r}_{u,s,v}(t)$ is the satellite-to-user direction recorded for the same link. The three indices mark link-level data ownership. $\mathbf{v}$ may have the same value across users of one beam, and $\mathbf{r}$ may have the same value across beams of one user-satellite pair. The off-axis angle is the point at which geometric information enters the energy-efficiency chain.

Following the angular pattern commonly used for multi-beam satellites and adopted in HOBS \[4\], \[20\], the transmit gain is retained only as a function of the off-axis angle:

$$
G^{T}\!\left(\theta,\theta_{3dB}\right),\qquad
G^{T}\!\left(0,\theta_{3dB}\right)=G_0.
\tag{3.7}
$$

Here, $G_0$ is the beam-center gain. To keep the tunable antenna parameters traceable to the simulator, the main text uses a one-layer normalized-pattern expansion:

$$
G^{T}\!\left(\theta,\theta_{3dB}\right)=G_0F\!\left(\theta,\theta_{3dB}\right),
\qquad
G^{T}\!\left(0,\theta_{3dB}\right)=G_0,
\qquad
F\!\left(0,\theta_{3dB}\right)=1.
\tag{3.8}
$$

The angular pattern adopts the $J_1/J_3$ pattern of HOBS Eq. (3) \[4\], the angle argument and pattern are

$$
\mu\!\left(\theta,\theta_{3dB}\right)=2.07123\frac{\sin\theta}{\sin\left(\theta_{3dB}/2\right)},
\qquad
F\!\left(\theta,\theta_{3dB}\right)=
\left[
\frac{J_1\!\left(\mu\!\left(\theta,\theta_{3dB}\right)\right)}{2\mu\!\left(\theta,\theta_{3dB}\right)}
+\frac{36J_3\!\left(\mu\!\left(\theta,\theta_{3dB}\right)\right)}{\left[\mu\!\left(\theta,\theta_{3dB}\right)\right]^{3}}
\right]^2.
\tag{3.9}
$$

Here $J_1(\cdot)$ and $J_3(\cdot)$ are the Bessel functions of the first kind of orders 1 and 3, and $2.07123$ is that equation's fixed angle argument, the same value that appears in other multibeam-satellite work. $F$ is naturally unity at $\theta=0$ ($1/4+3/4$), so no extra boresight normalization constant is required, however $J_1(\mu)/(2\mu)$ and $36J_3(\mu)/\mu^{3}$ are $0/0$ at $\mu=0$, so the limit is taken directly whenever $|\mu|<\epsilon_\mu$, with $\epsilon_\mu$ given in Section 5.1. $\theta_{3dB}$ is a fixed antenna parameter, but it appears on the right-hand side of the definition of $\mu$ and, through $\mu$, sets the shape of $F$ and $G^{T}$, it is therefore listed as an argument of all three, so that the left-hand side of every definition covers the quantities that appear on its right. $G_0$ is different: it is a multiplicative scale constant that does not change the shape of the pattern and is therefore not an argument. From Eq. (3.10) onward the same function is applied at a specific link's off-axis angle, so it is written with the fixed parameter explicitly as $G^{T}(\theta_{u,s,v},\theta_{3dB})$. This layer does not introduce a three-index gain variable and does not add a pattern selector.

This study does not adopt the $G_0=40$ dBi of Table I of HOBS \[4\]. The aperture $10c/f_c$, the gain of 40 dBi and the beamwidth listed there are mutually inconsistent: under either dimensionally valid reading, 40 dBi requires an aperture efficiency of $\eta=2.53$ (radius reading) or $\eta=10.13$ (diameter reading), **both greater than one**. The aperture is therefore re-derived from the beamwidth, $D=1.0275\lambda/\theta_{3dB}=17.7\lambda$, with the Ka-band aperture efficiencies of $0.639$–$0.645$ back-derived from 3GPP TR 38.821 \[22\], this gives $G_0=2000$ ($33.0$ dBi). The value is listed in Section 5.1. Throughout this thesis $\theta_{3dB}$ denotes the **full** half-power beamwidth, consistent with the cell radius $R_b=h_s\tan(\theta_{3dB}/2)$ in Section 5.1, whereas HOBS Eq. (3) normalizes by the **one-sided** half-power angle, Eq. (3.9) therefore substitutes $\theta_{3dB}/2$. The constant $2.07123$ is calibrated to exactly that point: $F=1/2$ at $\mu=2.07123$.

Let $H_{u,s,v}(t)$ denote the linear link-power factor that does not directly carry the wanted-link angular pattern. To trace it to the channel implementation, expand H as

$$
H_{u,s,v}(t)
=10^{-\frac{L_{u,s,v}(t)}{10}}
G^R_{u,s,v}(t),
\tag{3.10a}
$$

where

$$
L_{u,s,v}(t)
=L_f\!\left(d_{u,s,v}(t),f_c\right)
+L_g\!\left(\alpha_{u,s}(t)\right)
+L_c\!\left(\alpha_{u,s}(t)\right)
+L_s\!\left(\alpha_{u,s}(t)\right).
\tag{3.10b}
$$

The four losses correspond to $L=L_{fs}+L_g+L_{sc}+L_{sf}$ of HOBS Eq. (1), this thesis writes them as $L=L_f+L_g+L_c+L_s$ to keep subscripts single-lettered: $L_f$ is the free-space path loss, $L_g$ the atmospheric gaseous absorption, $L_c$ the scintillation and $L_s$ the shadow fading, the last three vary with elevation, and their models and values are given in Section 5.1, all four are dB terms converted to a common linear scale before entering H, and $G^R_{u,s,v}(t)$ is the linear receive gain. These four terms are exactly the loss set of HOBS Eq. (1), the public expansion adds nothing below them. Scan loss, NLoS clutter, and other implementation-layer channel corrections are absorbed into $H_{u,s,v}(t)$, take no public symbol, and are not tunable parameters.

$G^R_{u,s,v}(t)$ is written as a boresight gain minus an off-axis loss. Let $\theta^{R}_{u,s}(t)$ be the angle in degrees between the user's receive-antenna pointing direction and the direction of satellite $s$. Then

$$
G^R_{u,s,v}(t)
=\min\!\left\{\max\!\left\{A_R-B_R\log_{10}\theta^{R}_{u,s}(t),\,G_{R,\min}\right\},\,G_{R,\max}\right\}.
\tag{3.10c}
$$

$A_R$, $B_R$, and the floor $G_{R,\min}$ are taken from the ITU-R S.465-6 earth-station reference radiation pattern \[21\], whose stated range of 2 to 31 GHz covers the $f_c$ used here. The three are not independent settings: the recommendation gives $A_R-B_R\log_{10}\theta^{R}$ for $\theta^{R}_{\min}\le\theta^{R}<48^{\circ}$ and $G_{R,\min}$ for $48^{\circ}\le\theta^{R}\le180^{\circ}$, and the two branches join continuously at $48^{\circ}$. The boresight gain $G_{R,\max}$ is the derated value adopted for a comparable 0.6 m user terminal in an LEO handover setting \[5\], about 4.7 dB below the ideal gain of that aperture. The recommendation defines the envelope only for $\theta^{R}\ge\theta^{R}_{\min}$ (here $\theta^{R}_{\min}\approx2.498^{\circ}$ at $f_c$), this work extends the same envelope into $\theta^{R}<\theta^{R}_{\min}$ up to the $G_{R,\max}$ cap, which is a modelling simplification outside the scope of the recommendation.

The two wanted-link linear power-gain factors are still used directly as

$$
H_{u,s,v}(t)G^{T}\!\left(\theta_{u,s,v},\theta_{3dB}\right).
\tag{3.10}
$$

Here, $G^{T}$ directly carries the off-axis-angle dependence, while $H_{u,s,v}(t)$ preserves the physical meaning of the remaining channel factors — the four losses of Eq. (3.10b), the receive gain, and Rician small-scale fading, whose $K$-factor $K_R$ is a scenario calibration listed in Section 5.1. Both are linear power-scale factors, not complex channel amplitudes. The thesis, the simplified symbol table, and the `/` legacy simulator frontend share this one public expansion layer that maps to simulator controls and runtime fields, only layout may differ, not formulas, symbols, or editable parameters. The public expansion is capped at the depth the source paper itself shows: the four loss terms of HOBS Eq. (1) and a single $J_1/J_3$ angular-pattern layer whose two-term structure follows HOBS Eq. (3). Deeper antenna measurement, Bessel-approximation, and channel-calibration details are outside the public formula layer. No intermediate channel symbol distinguished only by letter case is introduced. Note also that the MODQN $G_{i,l,v}$ is a channel gain whose role corresponds to $H_{u,s,v}$ here, semantically different from the antenna gains $G^{T}$ and $G^{R}$, the two same-letter symbols are not merged.

### 3.1.3 Power, SINR and Throughput Model

The following keeps only actual quantities for each user--satellite--beam link. $p_{u,s,v}$ denotes actual RF transmit power, it is not obtained by inverting a target SINR, minimum rate, or lagged interference. If the implementation needs measured, predicted, or cached provenance, that information belongs in field metadata rather than in a second physical SINR.

Let $\tau_{u,s,v}$ be the start time of the current uninterrupted served physical-link $(u,s,v)$ segment. Episode reset, handover, outage, an unserved step, and re-entry all break continuity, a new segment does not retain inactive-link power and starts at $p^{0}$. Only consecutive service of the same physical link uses the previous-step recurrence:

This is an angle-aware power rule defined by this study, not an equation from the original MODQN paper. The modelling condition is to keep the product of transmit power and transmit gain constant within one continuous served segment:
$p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_{3dB})G^T(\theta_{u,s,v}(t),\theta_{3dB})
=p_{u,s,v}(t-1,\theta_{u,s,v}(t-1),\theta_{3dB})G^T(\theta_{u,s,v}(t-1),\theta_{3dB})$.
Solving for the current power gives the equation below. It compensates only the transmit-side angular gain, it does not claim that the full SINR or throughput remains constant.

$$
p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_{3dB}\right)
=p_{u,s,v}\!\left(t-1,\theta_{u,s,v}(t-1),\theta_{3dB}\right)
\frac{G^{T}\!\left(\theta_{u,s,v}(t-1),\theta_{3dB}\right)}
     {G^{T}\!\left(\theta_{u,s,v}(t),\theta_{3dB}\right)},
\qquad x_{u,s,v}(t-1)=x_{u,s,v}(t)=1,
\quad G^{T}\!\left(\theta_{u,s,v}(t),\theta_{3dB}\right)>0,
\tag{3.11}
$$

The segment-start condition and its within-segment closed form are:

$$
p_{u,s,v}\!\left(\tau_{u,s,v},\theta_{u,s,v}(\tau_{u,s,v}),\theta_{3dB}\right)
=p^{0},
\qquad p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_{3dB}\right)
=p^{0}\,
\frac{G^{T}\!\left(\theta_{u,s,v}(\tau_{u,s,v}),\theta_{3dB}\right)}
     {G^{T}\!\left(\theta_{u,s,v}(t),\theta_{3dB}\right)}.
\tag{3.12}
$$

Equation (3.12) is valid only when every step from $\tau_{u,s,v}$ through $t$ remains the same served physical link with positive gain, it is the telescoped identity of Eq. (3.11), not runtime state across an event. The recurrence expresses the previous-step angle-gain effect on link RF power and introduces no target SINR, no required-power inversion, no beam/satellite cap, no PA clamp, and no `min`/`max` projection.

Define the system angle state $\boldsymbol{\theta}(t)$ as the collection of off-axis angles $\theta_{u,s,v}(t)$ over every $u\in \mathcal{U},\ s\in \mathcal{S},\ v\in \mathcal{V}$, and let $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$ denote the total co-channel interference relative to the wanted link.

The beams use three-colour frequency reuse. Let $c_{s,v}\in\{0,1,2\}$ be the frequency colour of beam $(s,v)$, assigned from the axial coordinates $(q_{s,v},r_{s,v})$ of its ground cell on the hexagonal lattice as $c_{s,v}=(q_{s,v}-r_{s,v})\bmod 3$. The rule guarantees that any two adjacent cells carry different colours: beams of the same colour share one sub-band, and beams of different colours are orthogonal. The bandwidth available to one beam is therefore $B^{w}=B_{\mathrm{sys}}/3$, and interference arrives only from activated beams of the same colour as the serving beam. The cell layout and the axial coordinates are environment settings, given in Section 5.1.

An activated beam radiates at a single power regardless of how many users it carries. Following the aggregation convention of the runtime, let $p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=\max_{u\in\mathcal{U}:\,x_{u,s,v}(t)=1}p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_{3dB}\right)$ be that beam's transmit power. The left-hand side retains the system angle state and the fixed beamwidth because the right-hand side takes a maximum across all served links. Following HOBS and the multi-beam LEO satellite system model \[4\], \[20\], the interference splits into same-satellite and cross-satellite terms, given in Eq. (3.12a) and Eq. (3.12b):

$$
I^{\mathrm{intra}}_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})
=\sum_{\substack{v'\in\mathcal{V},\ v'\neq v\\ c_{s,v'}=c_{s,v}}}
z_{s,v'}(t)\,p_{s,v'}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)\,G^{T}\!\left(\theta_{u,s,v'}(t),\theta_{3dB}\right)H_{u,s,v'}(t),
\tag{3.12a}
$$

$$
I^{\mathrm{inter}}_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})
=\sum_{s'\in\mathcal{S},\ s'\neq s}\ \sum_{\substack{v'\in\mathcal{V}\\ c_{s',v'}=c_{s,v}}}
z_{s',v'}(t)\,p_{s',v'}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)\,G^{T}\!\left(\theta_{u,s',v'}(t),\theta_{3dB}\right)H_{u,s',v'}(t),
\tag{3.12b}
$$

so that $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})=I^{\mathrm{intra}}_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})+I^{\mathrm{inter}}_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$. Every term uses the interfering beam's own off-axis angle and linear link factor, because different beams reach the same user through different path losses and gains, the sums are gated by the activation indicator $z$ and are not weighted by how many users a beam carries.

The noise power is $\sigma^{2}=k_BTB^{w}$, where $k_B$ is the Boltzmann constant and $T=T_a+T_0\left(10^{NF/10}-1\right)$ is the receiver system temperature. The antenna temperature $T_a$, the receiver noise figure $NF$ and the noise-figure reference temperature $T_0$ take the VSAT values of 3GPP TR 38.821 \[22\] and are listed in Section 5.1. The noise integrates over the whole beam bandwidth and therefore does not scale with the beam's load. The unique link SINR is

$$
\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=
\frac{
p_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
H_{u,s,v}(t)
G^{T}\!\left(\theta_{u,s,v},\theta_{3dB}\right)
}{
I_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)+\sigma^{2}
},
\tag{3.13}
$$

with $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})+\sigma^2>0$. This symbol is used for both baseline-link calculation and angle-aware power substitution, no estimated, required, target, or serving-index-nested SINR is introduced.

Multiplexing within a beam is time division. The $U_{s,v}(t)$ users on a beam take turns using the available bandwidth. The link throughput is \[2\], \[4\]

$$
R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=\frac{B^{w}}{U_{s,v}(t)}
\log_2\!\left(1+\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)\right),
\qquad U_{s,v}(t)>0.
\tag{3.14}
$$

$B^w$ is the available bandwidth of one beam, for a single-user illustration, set $U_{s,v}=1$ without creating a second rate or SINR formula. The connection variable $x_{u,s,v}(t)$ selects the active service link and does not create a user-level SINR or throughput alias.

A beam is driven by a single power amplifier, so supply-side power is a per-beam quantity rather than a per-link one. Let $\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)>0$ be that beam's effective conversion efficiency from RF power to supply-side consumption. Then

$$
P^{p}_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=\frac{p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)}
{\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)}.
\tag{3.15}
$$

Radiated power is not the power actually consumed. A beam's RF signal is produced by a power amplifier, and the ratio of its RF output to the DC power it draws is the $\xi$ of Eq. (3.15). An amplifier is more efficient near saturation but less linear there, so it is operated a fixed distance below saturation, that distance is the output back-off $BO$, expressed in dB, and the saturated power is $p_{\mathrm{sat}}=p_{\max}10^{BO/10}$, where $p_{\max}$ is the per-beam operating limit after back-off. Following the power-efficiency relation of the classical class-B amplifier \[23\], the back-off region is approximated by a load-dependent square-root curve, this is an engineering approximation for system-level analysis, not a full circuit model:

$$
\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=\min\!\left\{\xi_{\max},\ \xi_{\max}\sqrt{\dfrac{p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)}{p_{\mathrm{sat}}}}\right\}.
\tag{3.15a}
$$

The square root follows from the ideal class-B approximation: with $V_o$ the output voltage amplitude at fixed supply voltage and load, the RF output power satisfies $P_{\mathrm{RF}}\propto V_o^{2}$ while the average DC input satisfies $P_{\mathrm{DC}}\propto V_o$, so $\xi=P_{\mathrm{RF}}/P_{\mathrm{DC}}\propto\sqrt{P_{\mathrm{RF}}}$. At one quarter of the saturated output the efficiency is $\xi_{\max}/2$, not $\xi_{\max}/4$. The values of $\xi_{\max}$ and $BO$ are listed in Section 5.1, a Ka-band satellite-downlink GaN Doherty MMIC reports a saturated power-added efficiency of 23--31%, and about 20% at 6 dB output back-off \[24\], which is of the same order as this model without being the same measurement point. Morello and Mignone's two-carrier DVB-DSNG example uses 5.5 dB of output back-off per carrier \[25\], showing that multi-carrier operation needs a larger back-off to stay quasi-linear, that statement does not generalize to all multi-carrier systems and is cited here only as corroboration of the back-off magnitude.

This shape has one consequence that matters for this thesis: because efficiency is poorer at low output, lowering the transmit power does not lower the consumed power proportionally. What actually governs energy efficiency is how much throughput a given amount of power buys, and that is why Section 3.2 takes energy efficiency, rather than transmit power alone, as the first objective.

Let $P^{f}(t)$ aggregate all fixed/circuit overhead that is not directly controlled by off-axis angle. With $N^{\mathrm{act}}_{s}(t)=\sum_{v\in\mathcal{V}}z_{s,v}(t)$ the number of active beams on satellite $s$, and with one active beam mapped to one RF chain in this study,

$$
P^{f}(t)=\sum_{s\in\mathcal{S}}\left(
N^{\mathrm{act}}_{s}(t)\,P_{\mathrm{cir}}
+\mathbb{1}\!\left\{N^{\mathrm{act}}_{s}(t)>0\right\}P_{\mathrm{BB}}
\right).
\tag{3.16a}
$$

The baseband power is shared by all active beams of that satellite and is therefore counted once per satellite, never twice. The values of $P_{\mathrm{cir}}$ and $P_{\mathrm{BB}}$ are taken from Table II of You et al. \[26\] and are listed in Section 5.1. The one-beam-to-one-RF-chain mapping is this study's own, not a conclusion about satellite architecture from that work, that work also includes local-oscillator and phase-shifter power, which this study does not adopt, so Eq. (3.16a) is a partial payload-power model rather than a complete satellite power model. The total system power is

$$
P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=P^{f}(t)+
\sum_{s^{\prime}\in \mathcal{S}}\sum_{v^{\prime}\in \mathcal{V}}
z_{s^{\prime},v^{\prime}}(t)\,
P^{p}_{s^{\prime},v^{\prime}}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right).
\tag{3.16}
$$

The sum runs over $(s,v)$ rather than over $(u,s,v)$: an active beam has a single amplifier, and its supply-side power is not counted once per user it carries, which is consistent with the $p_{s,v}$ aggregation of Eq. (3.12a). A per-link sum would add a spurious term $\sum_{s,v}(U_{s,v}(t)-1)P^{p}_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ that grows with occupancy and would make the first objective duplicate the work of the third.

Finally, the displayed EE for a fixed link $(u,s,v)$ is

$$
\eta_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=
\frac{R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)}
{P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)},
\qquad P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)>0.
\tag{3.17}
$$

The three subscripts fix the numerator's UE-link. The denominator remains shared system power, so $\eta_{u,s,v}$ is a displayed single-link contribution to system EE, not true private-power per-user EE.

The multi-objective deep Q-network (MODQN) baseline used in this study trains one Q-network for each of the three objectives, throughput was originally its first reward term \[2\]. This study defines the first reward as the sum of the selected-link EE contributions, so that transmission volume, beam angle, and power consumption are considered together.

## 3.2 Problem Formulation

This study considers energy efficiency, handover cost, and load balancing jointly. Let $L_w$ be the number of visible satellites included at each step. Using the realized connection $x_{u,s,v}(t)$ as the decision outcome, the long-term objectives are \[2\]

$$
\begin{aligned}
\mathrm{P1}:&\quad \max \sum_t\sum_{u\in \mathcal{U}}r_{1,u}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right),\\
\mathrm{P2}:&\quad \min \sum_t\sum_{u\in \mathcal{U}}\Psi_u(t),\\
\mathrm{P3}:&\quad \min \sum_t\sum_{s\in \mathcal{S}}\sum_{v\in \mathcal{V}}U_{s,v}(t)^2,\\
\mathrm{s.t.}:&\quad x_{u,s,v}(t)\in\{0,1\},\qquad
\sum_{s\in \mathcal{S}}\sum_{v\in \mathcal{V}}x_{u,s,v}(t)\le 1.
\end{aligned}
\tag{3.24}
$$

P1 seeks to deliver more data for the consumed power, P2 reduces handovers, and P3 drives the per-beam user counts toward an even split: with the served total fixed, the sum of squares is smallest when beam occupancies differ by at most one. The three objectives are defined below.

### 3.2.1 Angle-Aware Energy Efficiency

Equations (3.15)–(3.17) define link-side consumption, shared system power, and the displayed EE for a fixed link. The first reward sums the EE contributions of the links selected by each user:

$$
\begin{aligned}
r_{1,u}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
&=\sum_{s\in \mathcal{S}}\sum_{v\in \mathcal{V}}
x_{u,s,v}(t)\eta_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)\\
&=\frac{\sum_{s\in \mathcal{S}}\sum_{v\in \mathcal{V}}x_{u,s,v}(t)R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)}
{P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)},
\qquad P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)>0.
\end{aligned}
\tag{3.25}
$$

The unit of $r_{1,u}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ is bit/J. It is the additive contribution of user $u$ to instantaneous system energy efficiency. Equation (3.25) is defined when shared system power is positive, unselected links are excluded by $x_{u,s,v}(t)=0$. No user-level SINR or user-level throughput symbol is introduced here.

The off-axis angle therefore enters $G^T$ directly, while the wanted-link numerator in Eq. (3.13) uses $p_{u,s,v}H_{u,s,v}G^T(\theta_{u,s,v},\theta_{3dB})$, Eqs. (3.11)–(3.12) use the segment-start power $p^{0}$ and the previous-step recurrence to determine angle-aware link RF power. The same $p$ also enters the total-interference system state and the power/EE relations in Eqs. (3.15)–(3.17). The physical formula needs neither target-SINR inversion nor a protective power cap.

### 3.2.2 Handover Cost

Using the serving pair $(\rho_u(t),\delta_u(t))$ defined above, the cost of switching beams within one satellite is $\varphi_1$, while the cost of switching satellites is $\varphi_2$, with $0<\varphi_1<\varphi_2$. The second reward is

$$
r_{2,u}(t)=-\Psi_u(t),\qquad
\Psi_u(t)=
\begin{cases}
0,&(\rho_u(t),\delta_u(t))=(\rho_u(t-1),\delta_u(t-1)),\\
\varphi_1,&\rho_u(t)=\rho_u(t-1),\ \delta_u(t)\ne\delta_u(t-1),\\
\varphi_2,&\rho_u(t)\ne\rho_u(t-1).
\end{cases}
\tag{3.27}
$$

Keeping the current connection has no cost, an intra-satellite beam switch has the smaller cost, and an inter-satellite handover has the larger cost.

### 3.2.3 Load Balancing


The third reward is the negative occupancy of the beam the user selected, where that occupancy is the $U_{s,v}(t)$ of Eq. (3.3):

$$
r_{3,u}(t)=-U_{b_u(t)}(t).
\tag{3.28}
$$

Here $b_u(t)$ is the beam user $u$ selects at that step and $U_{b_u(t)}(t)$ is the number of users that beam serves at that step, from (3.28). A more crowded selected beam gives a smaller reward. This reward is **decomposable per user**: since $\sum_{u\in \mathcal{U}}U_{b_u(t)}(t)=\sum_{s,v}U_{s,v}(t)^2$, the sum over users is exactly the negative of the P3 objective, so each user's reward is an exact decomposition of the global objective rather than one system-level scalar shared by every user.

### 3.2.4 Reward Vector and Evaluation Metric

MODQN retains the three-dimensional reward vector \[2\]:

$$
\overrightarrow R_u\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=\left[r_{1,u}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right),\ r_{2,u}(t),\ r_{3,u}(t)\right].
\tag{3.29}
$$

The three components do not take the same arguments: $r_{1,u}$ depends on the whole set of off-axis angles and beamwidth parameter through $\eta_{u,s,v}$ and $P^{N}$ and therefore carries $\boldsymbol{\theta},\theta_{3dB}$, whereas $r_{2,u}$ is fixed by the change of serving satellite and beam and $r_{3,u}$ by the occupancy alone, so neither involves an angle. The vector carries $\boldsymbol{\theta},\theta_{3dB}$ because its first component does. The generic $r_{j,u}$ and $\bar r_{j,u}$ of Chapter 4 do not spell the arguments out component by component, each component keeps the definition given here.

Training uses stepwise rewards. Cross-time total-bits/total-energy evaluation belongs to the experimental procedure in Chapter 5, this section does not introduce a second physical EE symbol. Chapter 5 specifies the evaluation interval, service quality, coverage, and handover metrics separately from the per-step link EE in Eq. (3.17).

MODQN lets each user independently select the feasible beam with the largest weighted Q-value. Users with similar states may concentrate on the same few beams. By Eq. (3.14), users on one beam share its bandwidth, so concentration directly lowers each user's rate and worsens the P3 objective in Eq. (3.24). Chapter 4 addresses this issue through two training-shaping strategies.
