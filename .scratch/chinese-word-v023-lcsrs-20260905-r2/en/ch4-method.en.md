# 4. Multi-Catfish Reinforcement Learning (MCRL)

## 4.1 Method Overview

Chapter 3 used the realized connection $x_{u,s,v}(t)$ to describe the physical system. This chapter organizes the selectable beams into a fixed action space for the neural network and explains how MODQN and MCRL use this information.

The physical beams available to a user change as the satellites move, but the output length of the neural network must remain fixed. Each user therefore uses a fixed-length candidate table. It retains $L_w$ visible satellites and $J_w$ candidate beams from each satellite, giving $C=L_wJ_w$ positions. Let $\mathcal{C}=\{1,\ldots,C\}$ be the candidate-index set, where $c\in \mathcal{C}$ denotes one table position.

The table contents change over time. The mapping $b_u(c,t)\in \mathcal{S}\times\mathcal{V}$ gives the physical satellite and beam represented by position $c$ for user $u$ at time $t$. The network selects a candidate index, and $b_u(c,t)$ maps that choice back to the physical indices used in Chapter 3.

This candidate table is a thesis-side fixed-output representation. The original MODQN paper writes its state and access action over the full $L\times V$ beam-position grid, this thesis restricts each moving visibility window to $L_w\times J_w$ candidates.

The user state contains four types of information: the previous connection, a link-level signal-quality value for each candidate, the off-axis angle of each candidate, and the number of users who selected each beam at the previous step. In candidate-table order, the state is

$$
\begin{aligned}
s_u(t)&=\mathrm{concat}\!\left(
x_u(t-1),\
    \big(\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)\big)_{\substack{(s,v)=b_u(c,t)\\c\in \mathcal{C}}},\
\big(\theta_{u,s,v}(t)\big)_{\substack{(s,v)=b_u(c,t)\\c\in \mathcal{C}}},\
N_u(t-1)\right).
\end{aligned}
\tag{4.1}
$$

Here, $x_u(t-1)=\big(x_{u,b_u(c,t)}(t-1)\big)_{c\in \mathcal{C}}$ records the previous connection. The two parenthesized sequences list the three-index link SINR and off-axis-angle elements in candidate order, and $\mathrm{concat}$ joins the four blocks into one state vector. The SINR reuses the single physical definition of $\gamma_{u,s,v}$ from Chapter 3. These values are available to the environment before the current action. If the implementation uses cached or predicted provenance, that label belongs in field metadata and does not create another physical symbol. The candidate table at step $t$ must be ordered so that the beam that actually served the user at the previous step remains identifiable: if user $u$ was served at $t-1$, its serving beam $(\rho_u(t-1),\delta_u(t-1))$ must still occupy one candidate position, so that $x_u(t-1)$ recovers the previous physical association required by Eq. (3.27), if that beam has left the candidate table, every position selected at this step constitutes a handover.

Let $n_{s,v}(t-1)$ denote the demand directed to beam $(s,v)$ at the previous step. The vector $N_u(t-1)=[n_{b_u(c,t)}(t-1)]_{c\in \mathcal{C}}$ follows the candidate order, whereas $U_{s,v}(t)$ in Eq. (3.3) is the realized served load.

Equation (4.1) uses only information available before the current action is selected. The connection, load, SINR, and throughput produced by that action determine the current reward and the next state.

The candidate-table length is fixed, but some positions may be unavailable. Let $m_u(t)$ denote the feasible-action mask:

$$
m_{u}(t) = \big(m_{u,1}(t),m_{u,2}(t),\ldots,m_{u,C}(t)\big),\qquad
m_{u,c}(t) \in \{0,1\},
\tag{4.2}
$$

$$
A_u(t) = \left\{ c \in \mathcal{C} \mid m_{u,c}(t) = 1 \right\}.
\tag{4.3}
$$

Here, $m_{u,c}(t)=1$ means that candidate $c$ is selectable and 0 means that it is not. The set $A_u(t)$ collects all selectable candidate indices. The policy returns the scalar candidate index $a_u(t)$, the environment uses its one-hot encoding $a_{u,c}(t)$ when it applies the action to candidate $c$.

Let the scalar $a_u(t)$ denote the candidate selected by user $u$. The environment expands it into the one-hot indicator $a_{u,c}(t)$, which is 1 only for the selected candidate:

$$
a_u(t)\in A_u(t),\qquad
a_{u,c}(t)=\mathbf{1}\!\left\{c=a_u(t)\right\},\quad c\in \mathcal{C}.
\tag{4.4}
$$

When the feasible-action set is non-empty, each user selects one candidate at each time step, when it is empty, no candidate can be selected, so

$$
\sum_{c\in \mathcal{C}}a_{u,c}(t)=
\begin{cases}
1,& A_u(t)\neq\varnothing,\\
0,& A_u(t)=\varnothing,
\end{cases}
\qquad a_{u,c}(t) \in \{0,1\}.
\tag{4.5}
$$

When $A_u(t)=\varnothing$, the condition $a_u(t)\in A_u(t)$ of Eq. (4.4) has no solution and no candidate is executed at that step: user $u$ is unserved, all its $x_{u,s,v}(t)$ are zero, and the transition of that step does not enter the replay buffer. This setting does not claim that the mask is always non-empty, because candidate-cell coverage and link feasibility can together rule out every candidate at the same step.

The decision-time mask $m_{u,c}(t)$ and the physical-beam activation $z_{s,v}(t)$ have different roles: the first determines what a user may select, while the second follows the activation rule of Eq. (3.4) and states whether that physical beam radiates. The realized connection is therefore

$$
x_{u,b_u(c,t)}(t)
=a_{u,c}(t)\,z_{b_u(c,t)}(t).
\tag{4.5a}
$$

Thus, a user is connected only when the candidate was selected and the corresponding beam radiates. The link must then also be feasible: a link whose required power exceeds the per-beam limit is declared infeasible, and that user is in outage for the step. The selections of all users form the joint action:

$$
a(t) = \big(a_{1}(t),a_{2}(t),\ldots,a_{U}(t)\big).
\tag{4.6}
$$

Valid selections determine beam activation, whose state follows Eq. (3.4). Equation (4.5a) then gives the realized connections, from which the next state and the three rewards are calculated.

Together, the state, action, reward vector, environment transition, and discount factor form a multi-objective Markov decision process.

The original MODQN builds one Q-network for each objective, giving $\overrightarrow Q(s_u,a)=[Q_1(s_u,a),Q_2(s_u,a),Q_3(s_u,a)]$ \[2\]. The three Q-values are combined with weights $\Omega=[\omega_1,\omega_2,\omega_3]$, and each user selects the action with the largest combined value from $A_u(t)$, $\epsilon$-greedy exploration is added during training. Each Q-network is updated by temporal-difference learning using its own objective reward. The concrete weights are reported in Section 5.1.

MCRL retains MODQN's three objective Q-networks and per-user independent $\arg\max$ selection. Experience shaping and reward shaping **act only during training**, modifying the training experiences and the catfish agent's first reward respectively, the input representation and the selection rule at deployment are the same as in MODQN.

Figure 4-1 locates these mechanisms in data collection and parameter updating.

![Fig. 4-1 Intervention points in the MODQN update](figures/0727/fig4-0_modqn-update-interventions.png){width=155mm}

Fig. 4-1: Intervention points of MCRL in the MODQN update. Energy-efficiency stratification and competitive reward process catfish experiences, periodic intervention supplies a mixed batch for the main agent, asymmetric discounting distinguishes the two within-episode weightings.

Figure 4-2 presents the correspondence between the main and catfish agents at the objective-network level.

![Fig. 4-2 Objective-network view of MCRL](figures/0727/fig4-1_mcrl-architecture.png){width=150mm}

Fig. 4-2: Objective-network view of MCRL. The main and catfish sides each contain three objective Q-networks, with the one-to-one correspondence $Q_j^M\leftrightarrow Q_j^{F}\leftrightarrow r_j$. Each side scalarizes its three Q-values using the common weights $\Omega$ and selects one action.

Figure 4-3 shows the trajectories, replay buffers, and periodic intervention from the agent-and-data-flow perspective.

![Fig. 4-3 Role-level MCRL training architecture](figures/0727/fig4-1_training-architecture.png){width=125mm}

Fig. 4-3: Agent-and-data-flow view of MCRL. The main and catfish agents each generate a training trajectory and maintain a replay buffer. Catfish transitions are routed by their first-objective score, and periodic intervention uses a mixed batch to update the main agent, only the main agent is deployed after training.

## 4.3 Experience Shaping with the Catfish Agent

This section explains how MCRL uses an auxiliary catfish role in the three-objective handover problem.

The main agent and the catfish agent are each a three-objective MODQN. Both sides contain three online Q-networks and three target networks. $Q_j^M$ and $Q_j^{F}$ correspond to the same objective $r_j$, where $j=1,2,3$ denote energy efficiency, handover, and load balancing. Within each side, the three objective networks follow the deep Q-network training procedure \[27\] and use the same states, actions, transitions, and replay buffer, while each reads the $j$th component of the reward vector. Training therefore has two MODQN agents, after training, only the main agent is retained.

The three rewards have different units and scales. After the environment produces a reward and before it enters a replay buffer, component $j$ is divided by a fixed positive constant $c_j$, so that $\bar r_{j,u}^{d}=r_{j,u}^{d}/c_j$, the complete update expression is given in Eq. (4.13). The term “unshaped reward” denotes this calibrated reward before the competitive term in Eq. (4.11) is added.

The main-side buffer $D_M$ stores the unshaped, calibrated three-dimensional reward. The catfish-side buffer $D_{F}$ retains both unshaped and competitively shaped calibrated views: catfish TD updates use the shaped view, whereas catfish samples used by periodic intervention use the unshaped view. Only the energy-efficiency stratification threshold directly uses the first objective before calibration. Both buffers operate on complete time-step transitions containing all users.

Experience shaping has three components. Energy-efficiency stratification selects catfish experiences, asymmetric discounting changes how the catfish agent weights returns across steps within an episode, and periodic intervention uses part of the catfish experience for an additional main-agent update.

The first component is energy-efficiency stratification. At each step, the catfish side produces one complete transition bundle containing all users and the three-dimensional reward, denoted $\tau_t^{F}$. Define its stratification score as the mean unshaped additive contribution to the first objective before calibration:
$g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=U^{-1}\sum_{u\in \mathcal{U}}r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$.
This score is then compared with the empirical distribution $F_W$ of the scores from the most recent $W$ bundles. It is used only for training-time stratification and is not an evaluation metric. For $q\in(0,1)$, $F_W^{-1}(q)$ is the $q$-quantile of the empirical distribution, meaning that approximately a proportion $q$ of recent scores are no greater than this threshold. Let $q_1$ and $q_2$ satisfy $0<q_1<q_2<1$. The routing rule is:

$$
\mathrm{routing}\!\left(\tau_t^{F}\right)=
\begin{cases}
 D_{F}, & g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right) \ge F_W^{-1}(q_2),\\
 D_{M}, & F_W^{-1}(q_1) \le g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right) < F_W^{-1}(q_2),\\
 \varnothing, & g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right) < F_W^{-1}(q_1).
\end{cases}
\tag{4.7}
$$

High-scoring bundles enter $D_{F}$, middle-scoring bundles are also sent to $D_M$, and low-scoring bundles are discarded. Although routing uses only the first objective before calibration, the retained item is the complete three-objective transition, the replay buffer then uses the calibrated view described above.

![Fig. 4-4 Energy-efficiency stratification](figures/0727/fig4-2_ee-stratification.png){width=155mm}

Fig. 4-4: Energy-efficiency stratification. The catfish-side transition bundle $\tau_t^{F}$ is scored by its mean unshaped first-objective contribution $g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ before calibration and compared with the recent distribution $F_W$. High-scoring bundles enter $D_{F}$, middle-scoring bundles are also sent to $D_M$, and low-scoring bundles are discarded (Eq. (4.7)), each retained buffer then uses its corresponding calibrated reward view.

The second component is asymmetric discounting. The three main-side objectives share $\beta_M$, while the three catfish-side objectives share the larger $\beta_{F}$:

$$
\beta_M<\beta_{F},\qquad
\beta_j^M\equiv\beta_M,\quad
\beta_j^{F}\equiv\beta_{F},\quad j=1,2,3.
\tag{4.8}
$$

A larger discount factor keeps more of the return from later steps within an episode. At the episode length $H=10$ used here, both effective horizons are at least the episode itself ($1/(1-\beta_M)=10$), so the difference appears as how weight is distributed across steps within an episode: the main side emphasizes nearer-term returns, while the catfish side counts the whole episode almost uniformly. The episode length matches the effective horizon of $\beta_M$ at ten steps, which is the setting of Table I in the source paper and therefore not a deviation.

![Fig. 4-5 Asymmetric discounting](figures/0727/fig4-3_asymmetric-discount.png){width=175mm}

Fig. 4-5: Asymmetric discounting. The three main-side objective networks use $\beta_M$, and the three catfish-side objective networks use the larger $\beta_{F}$ (Eq. (4.8)). The relative weight of a return $n$ steps ahead is $\beta^n$, the bars only illustrate this decay.

The third component is periodic intervention. Each interval $T$ is sampled uniformly from the integer range $[T_1,T_2]$. When the interval expires, a mixed batch $B_I$ is formed from a proportion $\rho_I$ of $D_{F}$ and the remainder from $D_M$:

$$
\begin{aligned}
n_{F} &= \operatorname{round}\!\left(\rho_I B\right),\\
n_M &= B-n_{F}.
\end{aligned}
\tag{4.9}
$$

Here, $B$ is the batch size and $\operatorname{round}(\cdot)$ denotes rounding to the nearest integer. Drawing $n_M$ samples from $D_M$ and $n_{F}$ samples from $D_{F}$ forms the mixed batch $B_I$, both kinds of samples use the unshaped, calibrated three-dimensional reward. The three main-side networks use the same $B_I$ and perform one additional update with $\beta_M$, a new $T$ is drawn after an intervention.

![Fig. 4-6 Periodic intervention](figures/0727/fig4-4_periodic-intervention.png){width=145mm}

Fig. 4-6: Periodic intervention. $n_M$ main-side samples and $n_{F}$ catfish-side samples form $B_I$ (Eq. (4.9)), both use unshaped, calibrated rewards. The same batch then updates $Q_1^M$, $Q_2^M$, and $Q_3^M$.

Together, the three components perform experience shaping, and they change **only** training, deployment still selects actions with the main agent.

The two sides use the same action-selection rule. Let $d\in\{M,F\}$ denote the main or catfish side, and let $A_u^d(t)$ be the feasible action set for user $u$ on that side. Each side combines its three Q-values with the common weights $\Omega=[\omega_1,\omega_2,\omega_3]$ from Section 3.2 and selects from this set. During training, each side also uses its own $\epsilon$-greedy exploration:

$$
V_u^d(a,t)
=\sum_{j=1}^{3}\omega_j Q_j^d\big(s_u^d(t),a\big),
\qquad
a_u^d(t)=\arg\max_{a\in A_u^d(t)}V_u^d(a,t),
\quad d\in\{M,F\}.
\tag{4.10}
$$

Equation (4.13) shows the one-to-one correspondence between the two MODQNs. $Q_j^M$ and $Q_j^{F}$ estimate the same objective, and both sides combine their three objective values into the scalarized value $V_u^d(a,t)$. Because the two sides learn independently, they may select different actions. The three networks within one side share its selected action but keep separate network parameters. These Q-networks are trained with calibrated rewards, so the effective trade-off weight in the original units is $\omega_j/c_j$.

## 4.4 Reward Shaping: the Competitive Reward Mechanism

This section defines the first reward used by the catfish side. The competitive reward mechanism (ACRM) compares the catfish and main agents on the energy-efficiency objective. Handover and load balancing receive no competitive term, but they are still calibrated by the same $c_j$ before entering a replay buffer.

ACRM compares two complete joint actions under the same pre-action state and stochastic conditions. The catfish agent uses Eq. (4.10) to produce $a_{F}(t)$, while the main agent produces the exploration-free greedy action $a_{M\mid F}(t)$. The two simulations therefore differ only in their joint action. Their first objectives are both computed by Eq. (3.25). Let the raw rewards be $r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ and $r_{1,u}^{M\mid F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$, after which the difference and shaped reward are defined as:

$$
r_{1,u}^{S}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)-r_{1,u}^{M\mid F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right),\qquad
r_{1,u}^{C}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)+\eta_w\,r_{1,u}^{S}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right).
\tag{4.11}
$$

Here, $\eta_w\ge0$ is the competitive weight. Both raw $r_1$ values are calculated by Eq. (3.25) before the difference is formed. $r_{1,u}^{S}>0$ means that the catfish rollout has higher energy efficiency under the same conditions, whereas $r_{1,u}^{S}<0$ means the opposite. When $\eta_w=0$, $r_{1,u}^{C}=r_{1,u}^{F}$.

The catfish-side shaped vector is $[r_{1,u}^{C},r_{2,u}^{F},r_{3,u}^{F}]$. ACRM first forms $r_{1,u}^{C}$ in the original units and then calibrates the entire vector. Energy-efficiency stratification still scores the uncalibrated $r_{1,u}^{F}$, samples sent to $D_M$ and the intervention batch $B_I$ use the unshaped calibrated view, catfish TD updates use the shaped calibrated view. The competitive term therefore affects only $Q_1^{F}$.

![Fig. 4-7 Competitive reward mechanism](figures/0727/fig4-5_competitive-reward.png){width=175mm}

Fig. 4-7: Competitive reward on the energy-efficiency axis. Under the same pre-action state and stochastic conditions, only the complete joint action changes. Both simulations compute the first objective with Eq. (3.25), then form $r_{1,u}^{S}$ and $r_{1,u}^{C}$ (Eq. (4.11)). Both shaped and unshaped vectors are then calibrated by Eq. (4.13), and only $Q_1^{F}$ uses the competitively shaped value.

## 4.5 Overall Training Procedure

The main and catfish agents generate separate training trajectories. The competitive reward compares the two sides using the main-agent value before the update, and experience routed at that step is available to later parameter updates.

Pseudocode 4-1 summarizes the complete order. $E$ and $H$ are the number of training episodes and the maximum steps per episode, $B$ is the TD batch size, and $K$ is the target-network synchronization period. The interval $T$ is sampled from the range specified for Eq. (4.9).

| # | **Pseudocode 4-1: MCRL Training** |
|:--:|:-----------------------------------|
|  | **Input:** Two MODQNs and the training settings required by Eqs. (4.7)–(4.16). **Output:** the trained main agent $Q^M$. |
| 1 | Initialize the online and target networks, replay buffers $D_M,D_{F}$, and the first intervention interval $T$. |
| 2 | **for** $e=1,\ldots,E$ **do**: initialize separate main-agent and catfish-agent training trajectories. |
| 3 | &nbsp,&nbsp,**for** $t=1,\ldots,H$ **do**: construct the two inputs using Eqs. (4.7)–(4.9). |
| 4 | &nbsp,&nbsp,&nbsp,&nbsp,Select the two joint actions independently using Eq. (4.10) and $\epsilon$-greedy exploration. |
| 5 | &nbsp,&nbsp,&nbsp,&nbsp,Execute the main-agent action to obtain $\tau_t^M$, calibrate its unshaped reward, and store the complete transition in $D_M$. |
| 6 | &nbsp,&nbsp,&nbsp,&nbsp,Execute the catfish-agent action to obtain $\tau_t^{F}$, evaluate the main-agent greedy action from the same pre-action state and form the competitive reward using Eq. (4.11). |
| 7 | &nbsp,&nbsp,&nbsp,&nbsp,Route $\tau_t^{F}$ using its uncalibrated first objective in Eq. (4.7). Samples sent to $D_M$ use the unshaped calibrated view, catfish TD updates use the shaped calibrated view. |
| 8 | &nbsp,&nbsp,&nbsp,&nbsp,When enough experience is available, update the main and catfish agents using $\beta_M$ and $\beta_{F}$, respectively. |
| 9 | &nbsp,&nbsp,&nbsp,&nbsp,When the intervention interval expires, form $B_I$ using Eq. (4.9), apply one additional main-agent update, and sample a new $T$. |
| 10 | &nbsp,&nbsp,&nbsp,&nbsp,If the episode terminates, leave the time-step loop. |
| 11 | &nbsp,&nbsp,Synchronize both target networks every $K$ episodes. |
| 12 | **return** $Q^M$. |

The main-side TD update reads the unshaped calibrated vector. The catfish-side TD update reads the calibrated form of $[r_{1,u}^{C},r_{2,u}^{F},r_{3,u}^{F}]$. Let $d\in\{M,F\}$ denote the main or catfish side, and let $\beta_d$ be its discount factor. Both sides keep the form of Eq. (16) of the source paper, with **each objective taking its own maximum over its own target network**:

$$
y_{j,u}^{d}
=\begin{cases}
\bar r_{j,u}^d(t), & s_u^d(t{+}1)\ \text{is a terminal state},\\[4pt]
\bar r_{j,u}^d(t)+\beta_d \displaystyle\max_{a'\in A_u^d(t+1)} Q_j^d
\big(s_u^d(t{+}1),a',\theta_j^{d,-}\big), & \text{otherwise},
\end{cases}
\qquad d\in\{M,F\},\ j=1,2,3.
\tag{4.12}
$$

If the next state is terminal the TD target is the step reward alone, otherwise the discounted target-network value is added, and **each objective takes its own maximum over its own target network**. The main and catfish sides each perform one TD update, periodic intervention performs one additional main-side update with $B_I$.

Taking a separate maximum per objective during training is distinct from the deployment rule of (4.13), which scalarizes with $\Omega$ before the $\arg\max$. This is the design of the source paper and is retained unchanged.

The three rewards have different units and magnitudes: bit/J, handover cost, and a beam-occupancy count. The following calibration is a thesis-defined training contract, not a formula stated in the original MODQN paper. The original paper stores the raw reward components and directly scalarizes the learned Q-values with $\Omega$, it does not introduce $c_j$. This thesis adds $c_j$ so that the three objectives enter training on fixed, declared scales. Before a sample enters a replay buffer, each reward is divided by the fixed calibration constant $c_j$:

$$
\bar r_{j,u}^{d}(t)=\frac{r_{j,u}^{d}(t)}{c_j},\qquad
c_j>0,\qquad j\in\{1,2,3\},
\tag{4.13}
$$

Here, $r_{j,u}^{d}(t)$ is the $j$th update reward on side $d$ before calibration and $\bar r_{j,u}^{d}(t)$ is the calibrated value. Before training starts, the constants $c_j$ are fixed and then shared by the training procedures. Consequently, the scalarization in Eq. (4.10) and the TD target in Eq. (4.12) use the same scale. In the original units, the effective trade-off weight is $\omega_j/c_j$.

Deployment retains the three main-agent objective networks. Each user computes the scalarized value in Eq. (4.10) and uses $\arg\max$ to select a service beam.
