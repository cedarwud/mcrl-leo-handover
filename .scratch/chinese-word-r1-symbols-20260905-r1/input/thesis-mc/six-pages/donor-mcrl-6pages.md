\graphicspath{{../}{../figs/}{./figs/}{figs/}}
\setlength{\textfloatsep}{5pt plus 2pt minus 3pt}
\setlength{\dbltextfloatsep}{5pt plus 2pt minus 3pt}
\setlength{\abovecaptionskip}{4pt}
\setlength{\floatsep}{6pt plus 2pt minus 2pt}
\setlength{\dblfloatsep}{6pt plus 2pt minus 2pt}

> ⚑ **2026-08-21 狀態更新（donor draft — 本檔為六頁會議稿草稿，非現行論文正文）**
>
> 本檔描述的是**舊版 MCCRL 框架**，以下差異已於論文正文（`thesis-mc/ch4-method.md` 等）定案（2026-08-21），本檔保留歷史存查，**不得以本檔的機制描述覆蓋現行論文決定**：
>
> 1. **容量懲罰（penalty shaping）已整節刪除**：thesis 原 §4.5 Penalty Shaping、式 (4.15)–(4.17) 及圖 4-8 均已移除；本稿中 `capacity penalty`、`penalty shaping` 的描述均屬已移除機制。
> 2. **$v_{\max}$（per-satellite beam cap）已自貢獻機制刪除**：現行論文以 Table I 的場景參數 V=7 呈現，不再列為方法貢獻；執行遮罩 $m^e$ 保留為環境端帳務但不列入塑形策略。
> 3. **$r_3$ 已改為計數式**：本稿使用射頻槽機制（$F$、$\mathcal{F}$、$T_k$、$\tilde R$ beam aggregate），現行論文改為計數式 $r_{3,u} = -U_{bu}$。
> 4. **高度**：本稿使用 780 km；目標為真實 Starlink 約 550 km（尚未執行，值暫不改）。
> 5. **塑形策略**：本稿描述三個策略（含懲罰塑形），現行論文改為**兩個策略**（經驗塑形、獎勵塑形）。

# Introduction

Low Earth Orbit (LEO) satellite networks are a key enabler of future
non-terrestrial networks, offering wide-area coverage, low propagation delay,
and flexible deployment [@lee2024handover]. Because LEO satellites move at high speed relative to the ground, the user--satellite--beam association changes rapidly and handover becomes frequent, a central problem in multi-beam LEO systems [@sun2024handover]. With multi-beam
payloads, a handover is either intra-satellite (between two beams of one
satellite) or inter-satellite (between satellites) [@sun2024handover].

Learning-based handover has been studied to reduce access delay and collisions
[@lee2024handover] and as multi-objective decision-making [@song2025modrl]. The Multi-Objective Deep
Q-Network (MODQN) of Sun *et al.* casts LEO handover as multi-objective
reinforcement learning over throughput, handover cost, and load balancing
[@sun2024handover], building on modular multi-objective value decomposition
[@tajmajer2018modular]. On the energy side, energy-aware Q-learning has been applied to handover
[@ntabeni2025eaql], and joint handover and fast beam switching couples energy
efficiency (EE) with handover cost [@chen2024hobs],
with channel and signal-to-interference-plus-noise ratio (SINR) models
following 3GPP non-terrestrial-network assumptions
and elevation-dependent gain [@3gpp38811; @yu2022sinr; @kim2021shadowed].
State-augmented reinforcement learning couples assignment or constraints with augmented states [@agorio2024assignment; @calvofullana2024stateaug], and sequential satellite assignment pairs learned values with a coordinated one-to-one matching [@holder2025satellite]; these lines assign an agent to a user, satellite, or beam, whereas here the agents are per objective and the allocation is a budgeted many-to-one assignment under per-satellite activation limits. The
catfish effect has been used in deep reinforcement learning as an auxiliary
agent that stimulates the main learner's exploration, originally in a
single-objective energy-saving control task [@ke2025cdrl]; this paper extends
the training idea to one catfish per objective.

MODQN is adopted here as both baseline and backbone. Two limitations motivate this work. First, its raw-throughput reward does not reflect how off-axis angle, antenna gain, interference, and transmit power jointly determine energy efficiency. Second, each user independently selects its highest-scoring beam, and users observing similar states select the same one; under a per-satellite limit on simultaneously active beams this per-user argmax rule can cause beam over-concentration, pushing out the users that do not fit the capacity.

To address both limitations, a
Multi-Catfish Coordinated Reinforcement Learning (MCCRL) framework is proposed.
The contributions are as follows.

- Angle-aware EE reward. The throughput reward is replaced with an
  angle-aware energy-efficiency objective that couples the delivered rate
  (shaped by off-axis angle and interference) to the load-dependent transmit
  power, rather than ignoring the power cost altogether [@chen2024hobs; @3gpp38811].
- Coordinated valuation--allocation framework. Each objective is treated as
  a catfish role [@ke2025cdrl]; the three roles produce a multi-objective
  combined value for every candidate beam, and a coordinated beam allocation
  replaces the per-user argmax, jointly deciding which beams to activate and
  which beam each user connects to under the per-satellite capacity limit. The
  allocation is a submodular-greedy (facility-location) round
  [@nemhauser1978submodular; @cornuejols1977facility].
- Attribution and capacity diagnosis. A factorial ablation and a cross-over test (the same trained Q-networks re-decoded under the other selection rule) attribute the de-concentration to the coordinated allocation step; the framework is evaluated against plain MODQN and a set of
rule-based static and learned baselines on the normalized
weighted metric, and the advantage is located on the efficiency--equity axis.

# System Model and Problem Formulation

A window of $S$ satellites serves $U$ ground users; each satellite forms up to
$V$ directional beams and may keep at most $v_{\max}$ of them active per time
step, a per-satellite beam-activation budget, as in dynamic beam management [@zhu2024beam]. A binary connection variable $x_{u,s,v}(t)\in\{0,1\}$ marks whether user
$u$ connects to beam $(s,v)$, and a binary activation variable $z_{s,v}(t)$ marks
whether that beam is active, with $x_{u,s,v}\le z_{s,v}$ and
$\sum_{v} z_{s,v}(t)\le v_{\max}$; $U_{s,v}(t)=\sum_{u} x_{u,s,v}(t)$ counts the
users served by beam $(s,v)$.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figs/fig_sysmodel.png}
\caption{Multi-beam LEO satellite system model.}
\label{fig:sys}
\end{figure}

\paragraph{Channel and SINR} As illustrated in Fig. \ref{fig:sys}, the per-link gain
$h_{u,s,v}(t)=G^{\mathrm{T}}(\theta_{u,s,v}(t))\,G^{\mathrm{R}}_{u}\,H_{u,s}(t)\,g_{u,s,v}(t)$ is the product of the
angle-dependent transmit gain $G^{\mathrm{T}}(\theta)$, a fixed receive gain $G^{\mathrm{R}}_{u}$, the large-scale
attenuation $H_{u,s}(t)=10^{-L_{u,s}(t)/10}$ (3GPP free-space, shadowing, clutter [@3gpp38811]),
and small-scale fading $g_{u,s,v}(t)$. The transmit gain uses a Bessel pattern in the off-axis
angle $\theta_{u,s,v}(t)$, the angle between the beam-center direction and the
satellite-to-user direction [@chen2024hobs; @yu2022sinr],

\begin{equation}
G^{\mathrm{T}}(\theta_{u,s,v}(t))=G_{0}\left[\frac{J_{1}(\mu)}{2\mu}+36\,\frac{J_{3}(\mu)}{\mu^{3}}\right]^{2},
\end{equation}

where $G_{0}$ is the boresight gain, $J_{1},J_{3}$ are first-kind Bessel functions
of orders 1 and 3, the Bessel-pattern argument $\mu=2.07\,\sin\theta_{u,s,v}(t)/\sin\theta_{3\mathrm{dB}}$, and
$\theta_{3\mathrm{dB}}$ is the half-power beamwidth: a larger off-axis angle gives a smaller gain. The cell grid uses a three-color frequency reuse, so a link receives interference only from co-channel active beams: the SINR $\gamma_{u,s,v}(t)$ of a candidate link sums that interference over $\mathcal{I}_{s,v}(t)$, the set of other active beams sharing the color of $(s,v)$, and the achievable rate is the Shannon capacity of the per-color band:

\begin{equation}
\gamma_{u,s,v}(t)=\frac{p_{s,v}(t)\,h_{u,s,v}(t)}{\sigma^{2}+\displaystyle\sum_{(s',v')\in\mathcal{I}_{s,v}(t)} z_{s',v'}(t)\,p_{s',v'}(t)\,h_{u,s',v'}(t)},
\end{equation}
\begin{equation}
R_{u,s,v}(t)=\frac{B_{c}}{U_{s,v}(t)}\log_2\!\big(1+\gamma_{u,s,v}(t)\big),
\end{equation}

where $B_{c}=B_{\mathrm{sys}}/3$ is the per-color bandwidth under the three-color reuse, split equally among the $U_{s,v}(t)$ users on beam $(s,v)$ (the equal bandwidth-sharing rule of [@sun2024handover; @chen2024hobs]), and $\sigma^{2}=N_{0}B_{c}F_{\mathrm{NF}}$ is the noise power over that band with noise figure $F_{\mathrm{NF}}$. The
served rate is $R_{u}(t)=\sum_{s,v} x_{u,s,v}(t)\,R_{u,s,v}(t)$.

\paragraph{Angle-aware EE reward} The transmit power of a beam is load-dependent,

\begin{equation}
p_{s,v}(t)=z_{s,v}(t)\min\!\big(P_{\mathrm{base}}+P_{\mathrm{scale}}\,U_{s,v}(t)^{\nu},\ P_{\mathrm{beam},\max}\big),
\end{equation}

with base power $P_{\mathrm{base}}$ and coefficients $P_{\mathrm{scale}}$, $\nu\in(0,1)$ setting the concave load growth (our modeling assumption), capped per beam
at $P_{\mathrm{beam},\max}$ and per satellite by a total budget
$\sum_{v}p_{s,v}(t)\le P_{\mathrm{sat},\max}$ [@chen2024hobs]. The first reward term is
the angle-aware energy efficiency

\begin{equation}
r_{1,u}(t)=\eta^{\mathrm{EE}}_{u}(t)=R_{u}(t)\big/p^{\mathrm{alloc}}_{u}(t),
\end{equation}

the delivered rate per unit of allocated power (bit/s/W), where
$p^{\mathrm{alloc}}_{u}(t)=p_{s,v}(t)/U_{s,v}(t)$ is the power given to user $u$ at
its served beam $(s,v)$; an unserved user ($\sum_{s,v}x_{u,s,v}(t)=0$) contributes zero to every objective. Since the bandwidth and power shares cancel, $\eta^{\mathrm{EE}}_{u}(t)=B_{c}\log_2(1+\gamma_{u,s,v}(t))/p_{s,v}(t)$ at the served beam, of order $10^{12}$ bit/s/W (model-internal, used relatively): the numerator scales with the transmit gain, $\gamma_{u,s,v}\propto G^{\mathrm{T}}(\theta)$ (decreasing in $\theta$), and falls with interference, while the denominator power (4) is load-driven and angle-independent, so at equal allocated power a beam-center user attains a higher rate and energy efficiency than a beam-edge user. Unlike the system-level EE of [@chen2024hobs] (total rate over total power), this is a per-user ratio used as a reward.

\paragraph{Handover-cost reward} The second objective is the handover cost. Let $\rho_{u}(t)$ and $\delta_{u}(t)$
denote the satellite and beam serving user $u$ at time $t$ (from $x_{u,s,v}(t)$);
an intra-satellite beam switch costs $\varphi_1$ and an inter-satellite switch
costs $\varphi_2$ ($0<\varphi_1<\varphi_2$), and the reward is
$r_{2,u}(t)=-\Psi_{u}(t)$ [@sun2024handover],

\begin{equation}
\Psi_{u}(t)=\begin{cases}0, & \rho_{u}(t)=\rho_{u}(t{-}1),\ \delta_{u}(t)=\delta_{u}(t{-}1),\\ \varphi_1, & \rho_{u}(t)=\rho_{u}(t{-}1),\ \delta_{u}(t)\neq\delta_{u}(t{-}1),\\ \varphi_2, & \rho_{u}(t)\neq\rho_{u}(t{-}1).\end{cases}
\end{equation}

\paragraph{Load-balancing reward} The third objective is load balancing, the negative
spread between the busiest and least-busy active beam [@ye2013user],

\begin{equation}
r_{3,u}(t)=-\frac{1}{U}\left(\begin{array}{@{}l@{}}
\max\limits_{(s,v)\in\mathcal{B}(t)}\tilde{R}_{s,v}(t)-\\[2pt]
\min\limits_{(s,v)\in\mathcal{B}(t)}\tilde{R}_{s,v}(t)
\end{array}\right),
\end{equation}

where $\mathcal{B}(t)$ is the set of active beams (an inactive beam carries no load) and
$\tilde{R}_{s,v}(t)=\sum_{u}x_{u,s,v}(t)\,R_{u,s,v}(t)$ is the aggregate load of beam
$(s,v)$.

Following the multi-objective formalization of MODQN
[@sun2024handover], the long-term handover problem is stated as a vector
optimization over the connection and activation variables, rather than as a
single weighted sum:

\begin{equation}
\begin{aligned}
\max_{\pi}\ \ &\mathcal{J}(\pi)=\big(\mathcal{J}_{1}(\pi),\ \mathcal{J}_{2}(\pi),\ \mathcal{J}_{3}(\pi)\big)\\
\text{s.t.}\ \ &C_1:\ x_{u,s,v}(t),z_{s,v}(t)\in\{0,1\},\ \textstyle\sum_{s,v} x_{u,s,v}(t)\le 1,\\
&C_2:\ x_{u,s,v}(t)\le z_{s,v}(t),\ \textstyle\sum_{v} z_{s,v}(t)\le v_{\max},
\end{aligned}
\end{equation}

where $\mathcal{J}_{j}(\pi)=\mathbb{E}_{\pi}\big[\sum_{t=0}^{T-1}\bar{r}_{j}(t)\big]$ is
the expected long-term return of objective $j$ over a horizon of $T$ steps,
$\bar{r}_{j}(t)$ is the user mean of the per-user rewards of (5)--(7), and the
policy $\pi$ selects the joint action $a(t)=\{x_{u,s,v}(t),z_{s,v}(t)\}$: $\mathcal{J}_1$ maximizes the long-term angle-aware energy efficiency, $\mathcal{J}_2$ minimizes the handover cost, and $\mathcal{J}_3$ minimizes the load imbalance. C1 makes each user attach to at most one beam,
and C2 makes it attach only to an active beam and caps each satellite at
$v_{\max}$ active beams, a beam-activation budget that MODQN does not impose. The conflicting rewards are kept as a vector rather than summed
[@sun2024handover; @tajmajer2018modular].

For evaluation, the three objectives are combined into one normalized score

\begin{equation}
\mathcal{J}_{w}=\sum_{j=1}^{3}\omega_{j}\,\frac{\bar{r}_{j}}{c_{j}},
\end{equation}

where $\bar{r}_{j}$ is the average of the per-user reward $r_{j,u}(t)$ over all
users and the whole horizon, $c_{j}$ is a fixed per-objective normalization
constant that brings the three otherwise incommensurable magnitudes to a
comparable scale, and $\omega_{j}$ are preference weights shared with the scalarized policies below (both are listed in Table \ref{tab:params}). All compared methods share the same $\omega_{j}$ and $c_{j}$. $\mathcal{J}_w$ is the headline scalar metric (the weights follow [@sun2024handover]). Because the motivating failure mode is tail starvation, coverage metrics (minimum per-user coverage and served fraction, Section IV) are reported as co-primary criteria. The per-objective components are reported separately (Table \ref{tab:main} and the per-objective breakdown in Section IV), so the weighted score hides no per-axis regression.

# The MCCRL Scheme

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figs/fig4.png}
\caption{The proposed MCCRL framework: per-objective catfish valuation followed by coordinated beam allocation.}
\label{fig:frame}
\end{figure}

The backbone trains one Q-network per objective and forms a
linear scalarization $\sum_{k}\omega_k Q_k$; the original method then lets each
user pick its own highest-value beam (per-user argmax)
[@sun2024handover; @mnih2015dqn; @vanhasselt2016ddqn]. This per-user rule has no
mechanism to coordinate how many beams a satellite activates in total, which is the proximate origin of over-concentration under a tight $v_{\max}$.

\paragraph{Per-objective catfish training} Following the catfish effect [@ke2025cdrl],
each objective is assigned a catfish role---a per-objective Q-network trained with two catfish
mechanisms: a value-stratified
experience replay that oversamples the rare high-return transitions where users
compete for the same beam [@schaul2016per], and an asymmetric per-objective
discount $\beta_k$ that gives the handover objective a shorter effective
horizon than the other two. Each Q-network observes a user state that
stacks the connection status, candidate-link SINRs and off-axis angles, and the
beam-load distribution; a congestion-context state augmentation
$\chi_u$ (historical occupancy, number of candidate competitors, signal rank)
is concatenated to form the augmented state $\tilde{s}_u(t)$.

\paragraph{Coordinated beam allocation} The online decision is reorganized into two
steps (Fig. \ref{fig:frame}). In valuation, the three catfish produce, for every user $u$ and every
candidate beam $a=(s,v)$, a multi-objective combined value $b_u(a)$ (user $u$'s score for beam $a$),

\begin{equation}
b_u(a)=\sum_{k=1}^{3}\omega_k\,Q_k(\tilde{s}_u(t),a).
\end{equation}

Per user these scores are shifted so the worst feasible candidate is zero,
$\hat{b}_u(a)=b_u(a)-\min_{a'\in\mathcal{A}_u(t)} b_u(a')$, making the round invariant to per-user
value offsets, where $\mathcal{A}_u(t)$ is the set of beams reachable by user $u$ at time $t$.

In allocation, a coordinated greedy round replaces the per-user argmax. Starting from an empty
opened set $\mathcal{S}$, it repeatedly opens the beam that adds the most total value. Let
$o(u)=\max\{0,\max_{a\in\mathcal{S}\cap\mathcal{A}_u(t)}\hat{b}_u(a)\}$ be the best value user $u$
already obtains from the opened set (zero if none of its candidates is open); writing
$[x]^{+}=\max(x,0)$, a not-yet-opened beam $(s,v)$ on a satellite still under budget has marginal gain

\begin{equation}
\Delta(s,v)=\sum_{u:\,(s,v)\in\mathcal{A}_u(t)}\big[\,\hat{b}_u(s,v)-o(u)\,\big]^{+}.
\end{equation}

The round opens $(s,v)^{\star}=\arg\max_{(s,v)}\Delta(s,v)$ and repeats until every per-satellite
budget ($\sum_v z_{s,v}\le v_{\max}$) is spent or no positive gain remains. Each user then attaches to
its best opened candidate; a user with no opened candidate is bumped---unserved that step, carrying no
power and contributing zero to every objective---so the executed allocation never violates C1--C2.

This round is the classical facility-location assignment [@nemhauser1978submodular; @cornuejols1977facility]:
with $F(\mathcal{S})=\sum_{u}\max\{0,\max_{(s,v)\in\mathcal{S}\cap\mathcal{A}_u(t)}\hat{b}_u(s,v)\}$ the
total assigned value of an opened set (a user reached by no open beam contributes zero), $\Delta(s,v)$ equals the marginal increase
$F(\mathcal{S}\cup\{(s,v)\})-F(\mathcal{S})$; $F$ is monotone submodular and the per-satellite budgets
form a partition matroid, so the greedy round is $1/2$-approximate for $F$ [@fisher1978analysis]---a
guarantee on the learned values at the current step, not on the long-horizon objective (8).

It costs $O(S^{2}V v_{\max} U)$ per step ($\sim\!3.4\times10^{4}$ operations; lazy-greedy pruning
applies) and, unlike the per-user argmax, is computed centrally from the candidate values (a
coordination assumption shared by the fixed-rule allocation of Section IV), so it accounts for the
total number of active beams and for competition across users, and is designed to counteract the
over-concentration onto a few beams; the realized de-concentration is measured in Section IV. The
framework integrates this coordinated allocation into the MODQN backbone; it is not a new value-decomposition algorithm.





\paragraph{Training procedure} The three Q-networks are trained jointly with Double DQN
[@vanhasselt2016ddqn; @mnih2015dqn]. At each step the environment returns the
three rewards $r_{1},r_{2},r_{3}$, and each $Q_k$ is updated by a one-step temporal-difference target under its own discount $\beta_k$ (with differing discounts the combined value $b_u$ is a scalarization of per-objective values, not the value function of a single discounted problem); the next-step action inside the target is recomputed with the same coordinated allocation
rule, so the training bootstrap matches the deployed decision rule. The value-stratified replay marks a transition $\tau$ as critical when its normalized weighted reward $\mathcal{J}_{w}(\tau)=\sum_{j}\omega_{j}\,r_{j}(\tau)/c_{j}$ (the per-transition analogue of (9)) exceeds a running statistic,

\begin{equation}
\mathcal{J}_{w}(\tau) > m_{J} + \kappa\,s_{J},
\end{equation}

where $m_{J}$ and $s_{J}$ are the running mean and standard deviation of that reward, maintained online over past transitions, and $\kappa$ is a threshold multiplier; critical
transitions enter a priority subset, and every mini-batch draws a fixed fraction
$f_{r}$ from this subset and the remainder uniformly, so the rare
high-competition states are revisited more often. The general-training variant sets $f_{r}=0$, recovering uniform sampling.
Target networks are synchronized periodically and the exploration rate is
annealed over training; all hyper-parameter values are listed in Table \ref{tab:params}. At inference the trained Q-networks are combined into $b_u(a)$ and decoded by the coordinated allocation above.

# Experimental Results

The environment reuses the multi-beam LEO system of Section II: a window of $S=4$ satellites, each with $V=7$ beam slots (28 actions), serving $U=100$ users, with $v_{\max}=3$ active beams per satellite in the main experiment, a deliberately tight budget. Table \ref{tab:params} lists the physical and training constants. Each objective trains one Q-network with Double DQN for 3000 episodes (fewer than the backbone's 9000 [@sun2024handover], a budget the congestion-augmented state and tight per-window action space make sufficient here); the five MODQN and MCCRL variants all train on the reward vector of Section II under the same optimizer and schedule, so the comparisons isolate the decision rule and the training mechanisms rather than the reward design. The catfish variants use the value-stratified replay and the asymmetric per-objective discounts; the general-training variants use uniform sampling ($f_r=0$) and a symmetric discount. The congestion augmentation $\chi_u$ enlarges the state dimension from 140 to 224 for every trained variant except plain MODQN. The five learned variants use three seeds evaluated on 48 matched episodes; intervals are 95% percentile bootstrap over the 48 seed-averaged episodes (20000 resamples; episode-paired for the ablation deltas). The two single-objective DQNs are trained on five independent seeds under a separate field protocol (DQN-throughput on raw throughput, DQN-scalar on a positive-affine transform of the weighted score (9)) and report five-seed $t$-intervals, so their rows are cross-protocol context rather than a matched comparison. The static baselines (RSS-max, round-robin, and a fixed-rule coordinated allocation that decodes observed signal as the value, without learning) use the same matched 48-episode protocol.

\begin{table}[t]
\centering
\caption{Simulation and training parameters.}
\label{tab:params}
\footnotesize
\setlength{\tabcolsep}{3pt}
\resizebox{\columnwidth}{!}{\begin{tabular}{llll}
\hline
Parameter & Value & Parameter & Value \\
\hline
Altitude; carrier & 780 km; 20 GHz & Constellation & Walker-$\delta$ 180/9/1 \\
Area; user speed & $200\times90$ km; 30 km/h & Slot; episode & 1 s; 10 slots \\
$B_{\mathrm{sys}}$ (3-color reuse) & 500 MHz & $N_0$; noise fig. & $-174$ dBm/Hz; 1.2 dB \\
$G_0$; $\theta_{3\mathrm{dB}}$ & 40 dBi; $3.32^{\circ}$ & RX gain; QoS floor & 35 dBi; 10 Mbit/s \\
$P_{\mathrm{base}}$; $P_{\mathrm{scale}}$; $\nu$ & 0.25 W; 0.35 W; 0.5 & Power caps (beam; sat.) & 10 W; $10^{1.3}$ W \\
$\varphi_1$; $\varphi_2$ & 0.5; 1.0 & $\omega$ & $(0.5,0.3,0.2)$ \\
$c_j$ & $2.34{\cdot}10^{15}$; $300.3$; $6.13{\cdot}10^{9}$ & $\beta_k$ (catfish; general) & $(0.99,0.90,0.99)$; $0.9$ \\
$\kappa$; $f_r$ & 0.5; 0.25 & Episodes; batch; LR (Adam) & 3000; 128; 0.01 \\
Hidden layers & $100$--$50$--$50$ (tanh) & Replay; sync; $\varepsilon$ & 50000; 50 ep.; $1.0{\to}0.01$/2000 \\
\hline
\end{tabular}}
\end{table}


\paragraph{Over-concentration of plain MODQN} At $v_{\max}=3$ it
and the variant that only adds the congestion state but keeps the per-user
argmax (MODQN + aug) both over-concentrate: the mean number of active beams is about 3
of a possible 12, the served fraction (the fraction of users meeting their QoS
target) is about 0.29, and the
minimum coverage (the served-time fraction of the worst-off user) is 0. This follows from the per-user argmax rule: users with similar states select the
same beam, its load exceeds capacity, and users beyond the budget are excluded.
That the selection rule, rather than insufficient training, is the proximate lever is confirmed by the cross-over test below. Whether
this over-concentration is inherent to the shared-Q architecture or specific to
the capacity-constrained regime is left open.

\paragraph{Framework versus baselines} Table \ref{tab:main} compares all methods at $v_{\max}=3$.

\begin{table}[t]
\centering
\caption{Comparison of all methods at $v_{\max}=3$.}
\label{tab:main}
\setlength{\tabcolsep}{2pt}
\footnotesize
\resizebox{\columnwidth}{!}{\begin{tabular}{lcccccc}
\hline
Method & $\mathcal{J}_w$ & 95\% CI & EE & Min-cov & Served & Beams \\
\hline
MODQN (plain) & $-0.10$ & $[-0.54,0.37]$ & 1.01 & 0.00 & 0.29 & 3.0 \\
MODQN + aug & $-0.16$ & $[-0.61,0.33]$ & 1.02 & 0.00 & 0.29 & 3.0 \\
MODQN + catfish & $+0.45$ & $[-0.04,0.98]$ & 1.19 & 0.00 & 0.30 & 3.0 \\
RSS-max & $+1.55$ & $[1.01,2.11]$ & 1.50 & 0.00 & 0.31 & 3.2 \\
Round-robin & $+1.60$ & $[1.27,1.96]$ & 2.23 & 0.00 & 0.41 & 11.7 \\
DQN-throughput & $+3.54$ & $[1.73,5.36]$ & 3.20 & 0.00 & 0.63 & 5.6$^\dagger$ \\
Coordinated Alloc. & $+4.44$ & $[3.53,5.30]$ & 3.73 & 1.00 & 0.95 & 3.6 \\
MCCRL (Proposed) & $+4.82$ & $[4.53,5.11]$ & 3.85 & 0.999 & 0.97 & 9.4 \\
MCCRL (Inference-Only) & $+4.97$ & $[4.67,5.27]$ & 3.92 & 0.999 & 0.99 & 10.6 \\
DQN-scalar & $+6.41$ & $[5.96,6.87]$ & 4.79 & 0.00 & 0.89 & 12.8$^\dagger$ \\
\hline
\end{tabular}}

\smallskip
\begin{minipage}{\columnwidth}\footnotesize
$\mathcal{J}_w$ and its CI in $10^{-4}$; EE is the angle-aware $\bar{r}_1$ in $10^{12}$ bit/s/W at the operating point. Intervals: episode bootstrap for the three-seed MODQN/MCCRL and static rows, five-seed $t$-intervals for the DQN rows (Setup). A minimum coverage of $0$ means the worst-off user is never served. MCCRL (Inference-Only) is fully trained (coordinated TD targets); only catfish is off. $^\dagger$DQN rows: distinct requested beams (requests beyond the 12-beam budget are bumped, carrying no power); other rows: concurrently loaded beams (at most 12).
\end{minipage}
\end{table}

The proposed MCCRL and its inference-only variant (coordinated allocation without catfish training) reach $\mathcal{J}_w\approx
4.8$--$5.0\times10^{-4}$, far above plain MODQN ($\approx-1.0\times10^{-5}$),
with non-overlapping confidence intervals. Over-concentration is mitigated: the
effective number of active beams rises from about 3 to about 9--11, the served
fraction from 0.29 to 0.97--0.99, and the minimum coverage from 0 to 0.999. The coordinated MCCRL variants also exceed the
rule-based static baselines RSS-max ($1.55\times10^{-4}$) and round-robin
($1.60\times10^{-4}$) with separated intervals. Round-robin opens many beams yet still has zero minimum coverage: opening beams is not enough without proper assignment. Conversely, the fixed rule reaches full coverage with only 3.6, so the active-beam count is a de-concentration diagnostic rather than a merit metric, and more active beams draw more base power (4).

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figs/ee_users.png}
\caption{Energy efficiency (angle-aware \(r_1\), $10^{12}$ bit/s/W) versus the number of users. DQN-scalar reaches higher EE but under-serves the tail (min-cov 0 at the Table \ref{tab:main} operating point, $\le\!0.85$ over the sweeps) and is omitted.}
\label{fig:ee_u}
\end{figure}

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figs/ee_bw.png}
\caption{Energy efficiency versus the available bandwidth; DQN-scalar omitted as in Fig. \ref{fig:ee_u}.}
\label{fig:ee_bw}
\end{figure}



\paragraph{Efficiency versus equity} The fixed-rule coordinated allocation reaches $\mathcal{J}_w=4.44\times10^{-4}$ and minimum coverage
1.0; the inference-only MCCRL's margin over the fixed rule has a confidence interval covering zero, so
the extra benefit of learning over the fixed rule is not resolved at this seed
count; the de-concentration is attributable mainly to the coordinated
allocation step, not to learning. Conversely, DQN-scalar
attains the highest weighted score ($6.41\times10^{-4}$, above the inference-only MCCRL's
$4.97\times10^{-4}$); no claim is made of beating DQN-scalar on the weighted
scalar. However, DQN-scalar reaches that score by starving the tail: its minimum coverage is 0 and its Jain fairness index over the users' cumulative episode throughput [@jain1984] is about 0.69, whereas the inference-only MCCRL serves almost every user. The proposed
framework is therefore positioned on the efficiency--equity axis --- the only learned method that simultaneously attains high energy efficiency and near-full coverage (0.999) at tight capacity --- rather than as a maximizer of the weighted
scalar alone.

\begin{table}[t]
\centering
\caption{Cross-over decode test at $v_{\max}=3$ (matched 48-episode protocol): the same trained Q-networks, only the decode swapped. Cells: $\mathcal{J}_w$ ($10^{-4}$) / min-cov; diagonals are the native variants of Table \ref{tab:main}).}
\label{tab:xover}
\setlength{\tabcolsep}{5pt}
\begin{tabular}{lcc}
\hline
Trained Q-networks & Argmax decode & Coordinated decode \\
\hline
From MODQN + aug & $-0.16$ / $0.000$ & $+4.76$ / $1.000$ \\
From MCCRL (Inference-Only) & $+0.19$ / $0.000$ & $+4.97$ / $0.999$ \\
\hline
\end{tabular}
\end{table}

\paragraph{Per-objective components} On the handover axis the trained coordinated variants pay the lowest cost ($\bar{r}_2=-0.088$ to $-0.090$, intervals separated from plain MODQN's $-0.100$ and the fixed rule's $-0.189$; the fixed rule reassigns about twice as often, the one axis where learning improves on it). The load-spread term regresses ($\bar{r}_3\approx-7.7\times10^{6}$ versus $-3.8\times10^{6}$ for plain MODQN), as spreading load across ten beams widens the busiest-to-least-busy gap; the weighted score absorbs this disclosed regression.



\paragraph{Ablation} The framework changes two things: the selection rule and the
catfish training. A $2\times 2$ ablation separates them; the four cells share the $\chi_u$-augmented state and differ only in the selection rule (used both online and inside the TD target) and the catfish training of Section III. Replacing per-user argmax with coordinated allocation moves $\mathcal{J}_w$ from $-1.6\times10^{-5}$ to $4.97\times10^{-4}$ and minimum coverage from 0 to 0.999. Under the per-user argmax, catfish training does shift $\mathcal{J}_w$ by $+6.1\times10^{-5}$ (95% CI $[+5.0,+7.3]\times10^{-5}$; MODQN + aug versus MODQN + catfish) but leaves the collapse intact (minimum coverage 0): a real training-side effect that does not substitute for coordination. Adding catfish training under coordinated allocation changes $\mathcal{J}_w$ by only $-1.5\times10^{-5}$, whose confidence interval covers zero: no significant additional gain in this regime, plausibly because coordination removes the beam-competition collisions that the value-stratified replay is designed to oversample. A cross-over test makes the attribution direct
(Table \ref{tab:xover}): taking an argmax-trained Q and decoding it with coordinated allocation lifts minimum coverage from 0 to 1.000 (with $\mathcal{J}_w$ rising to $4.76\times10^{-4}$ and the effective beams from 3 to 10.3), while decoding a coordinated-trained Q with per-user argmax collapses it back (coverage 0, $\mathcal{J}_w=1.9\times10^{-5}$). The same Q-values flip between
collapse and full coverage when only the decode rule changes, so the de-concentration is driven by the coordinated allocation step; the evidence therefore supports neither crediting the catfish training with the improvement nor the claim that removing it causes collapse.

\paragraph{Sensitivity} Figs. \ref{fig:ee_u} and \ref{fig:ee_bw} re-evaluate the fixed trained models while sweeping the number of users and the available bandwidth.
Among the methods that keep near-full coverage, the coordinated MCCRL variants lead the energy efficiency point-wise across both sweeps: the margins over plain MODQN, RSS-max, and round-robin are interval-separated throughout; against the fixed rule they separate at most user counts and at low bandwidth and overlap elsewhere. DQN-scalar reaches a higher raw EE, but only by leaving the
tail unserved: its minimum coverage stays between $0.1$ and $0.85$ over the
sweep and is $0$ at the tight $v_{\max}=3$ point of Table \ref{tab:main}. The weighted-scalar advantage over plain MODQN is largest when capacity is tight and shrinks as $v_{\max}$ grows and over-concentration becomes
mild to begin with (matched $v_{\max}$ sweep, not shown).

# Conclusion

This paper has replaced the throughput reward of MODQN with an angle-aware energy-efficiency objective and reorganized the online decision into a valuation step built on three per-objective catfish roles followed by a coordinated beam allocation replacing the per-user argmax. Under a tight
per-satellite beam budget the proposed MCCRL framework substantially mitigates
the over-concentration of plain MODQN, raising the number of served users
and active beams and beating it and the rule-based static baselines on the
normalized
weighted metric, while remaining the only learned method that simultaneously attains high energy efficiency and near-full coverage. Ablation attributes
the de-concentration to the coordinated allocation step rather than to the
catfish training, and the advantage is located on the
efficiency--equity axis rather than on the weighted scalar, on which a simpler
scalar-trained DQN scores higher at the cost of zero minimum coverage. Whether the
over-concentration is rooted in the environment, the state, or the shared-Q
algorithm remains open; integrating the competitive-reward mechanism of the
source catfish method and testing across more environments are left for future
work.

\balance

\section*{Acknowledgment}

This work was supported by the National Science and Technology Council (NSTC), Taiwan, under Grant NSTC 115-2221-E-305-005.

\renewcommand*{\bibfont}{\footnotesize}
\setlength{\bibsep}{0pt plus 0.3ex}
