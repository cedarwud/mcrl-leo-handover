# 4. Multi-Catfish Reinforcement Learning (MCRL)

## 4.1 Method Overview

Chapter 3 used the realized connection $x_{u,s,v}(t)$ to describe the physical system. This chapter organizes the selectable beams into a fixed action space for the neural network and explains how MODQN and MCRL use this information.

第三章以實際連線 $x_{u,s,v}(t)$ 描述物理系統。本章則要把可選波束整理成神經網路可處理的固定動作空間，並說明 MODQN 與 MCRL 如何使用這些資訊。

The physical beams available to a user change as the satellites move, but the output length of the neural network must remain fixed. Each user therefore uses a fixed-length candidate table. It retains $L_w$ visible satellites and $J_w$ candidate beams from each satellite, giving $C=L_wJ_w$ positions. Let $\mathcal{C}=\{1,\ldots,C\}$ be the candidate-index set, where $c\in \mathcal{C}$ denotes one table position.

低軌衛星持續移動，每位使用者可選的實際波束會改變，但神經網路的輸出長度必須固定。因此，每位使用者使用一張固定長度的候選表。表中保留 $L_w$ 顆可見衛星，每顆衛星提供 $J_w$ 個候選波束，共有 $C=L_wJ_w$ 個位置。令 $\mathcal{C}=\{1,\ldots,C\}$ 為候選編號集合，$c\in \mathcal{C}$ 表示表中的一個位置。

The table contents change over time. The mapping $b_u(c,t)\in \mathcal{S}\times\mathcal{V}$ gives the physical satellite and beam represented by position $c$ for user $u$ at time $t$. The network selects a candidate index, and $b_u(c,t)$ maps that choice back to the physical indices used in Chapter 3.

候選表的內容會隨時間更新。$b_u(c,t)\in \mathcal{S}\times\mathcal{V}$ 表示候選位置 $c$ 在時間 $t$ 對使用者 $u$ 所對應的實際衛星與波束。後續網路選的是候選編號，實際連線則透過 $b_u(c,t)$ 回到第三章的衛星－波束索引。

This candidate table is a thesis-side fixed-output representation. The original MODQN paper writes its state and access action over the full $L\times V$ beam-position grid, this thesis restricts each moving visibility window to $L_w\times J_w$ candidates.

這張候選表是本論文為固定網路輸出所建立的表示法。原始 MODQN 論文把狀態與 access action 寫在完整的 $L\times V$ 波束位置網格上；本論文則將移動中的可見視窗限制為 $L_w\times J_w$ 個候選。

The user state contains four types of information: the previous connection, a link-level signal-quality value for each candidate, the off-axis angle of each candidate, and the number of users who selected each beam at the previous step. In candidate-table order, the state is

使用者的狀態包含四類資訊：前一步的連線、各候選鏈路的訊號品質、各候選的偏軸角，以及前一步選向各波束的使用者數。將它們依候選表順序排列後，狀態寫成

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

其中，$x_u(t-1)=\big(x_{u,b_u(c,t)}(t-1)\big)_{c\in \mathcal{C}}$ 記錄前一步的連線。兩個圓括號序列依候選順序排列三下標的鏈路 SINR 與偏軸角元素，$\mathrm{concat}$ 再把四個區塊接成一個狀態向量；SINR 沿用第三章唯一的 $\gamma_{u,s,v}$ 定義。這些值在動作前由環境可取得；若實作使用 cached 或 predicted provenance，該標記放在資料欄位 metadata，不改變公式中的物理符號。候選表在時間 $t$ 的排列必須讓上一步實際服務的波束仍可辨識：若使用者 $u$ 在 $t-1$ 被服務，其服務波束 $(\rho_u(t-1),\delta_u(t-1))$ 必須仍占有某一個候選位置，$x_u(t-1)$ 才能還原出式 (3.27) 所需的前一步實體關聯；若該波束已離開候選表，則本步無論選哪一格都構成換手。

Let $n_{s,v}(t-1)$ denote the demand directed to beam $(s,v)$ at the previous step. The vector $N_u(t-1)=[n_{b_u(c,t)}(t-1)]_{c\in \mathcal{C}}$ follows the candidate order, whereas $U_{s,v}(t)$ in Eq. (3.3) is the realized served load.

令 $n_{s,v}(t-1)$ 表示前一步選向波束 $(s,v)$ 的使用需求量。$N_u(t-1)=[n_{b_u(c,t)}(t-1)]_{c\in \mathcal{C}}$ 是依候選順序排列的向量；式 (3.3) 的 $U_{s,v}(t)$ 則表示實際服務負載。

Equation (4.1) uses only information available before the current action is selected. The connection, load, SINR, and throughput produced by that action determine the current reward and the next state.

式 (4.1) 只使用選擇動作前可取得的資訊；本步動作造成的連線、負載、SINR 與吞吐量則用於產生本步獎勵及下一步狀態。

The candidate-table length is fixed, but some positions may be unavailable. Let $m_u(t)$ denote the feasible-action mask:

候選表的長度固定，但部分位置在當下可能不可用。以 $m_u(t)$ 表示可行動作遮罩：

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

其中，$m_{u,c}(t)=1$ 表示候選 $c$ 可選，0 表示不可選；$A_u(t)$ 收集所有可選的候選編號。政策輸出的是純量候選編號 $a_u(t)$；環境套用動作時，才使用它在候選 $c$ 上的 one-hot 編碼 $a_{u,c}(t)$。

Let the scalar $a_u(t)$ denote the candidate selected by user $u$. The environment expands it into the one-hot indicator $a_{u,c}(t)$, which is 1 only for the selected candidate:

使用者 $u$ 選出的候選編號記為純量 $a_u(t)$。為了讓環境逐一套用到候選位置，將它展開為 one-hot 指示量 $a_{u,c}(t)$；候選 c 被選中時該分量才為 1：

$$
a_u(t)\in A_u(t),\qquad
a_{u,c}(t)=\mathbf{1}\!\left\{c=a_u(t)\right\},\quad c\in \mathcal{C}.
\tag{4.4}
$$

When the feasible-action set is non-empty, each user selects one candidate at each time step, when it is empty, no candidate can be selected, so

可行動作集合非空時，每位使用者在一個時間步選擇一個候選；可行動作集合為空時沒有任何候選可選，因此

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

$A_u(t)=\varnothing$ 時式 (4.4) 的 $a_u(t)\in A_u(t)$ 無解，該步不執行任何候選：使用者 $u$ 於該步 unserved，其所有 $x_{u,s,v}(t)$ 為 0，該步的轉移不進入經驗回放。本設定不宣稱遮罩恆為非空，因為候選格覆蓋與鏈路可行性可能在同一步同時排除所有候選。

The decision-time mask $m_{u,c}(t)$ and the physical-beam activation $z_{s,v}(t)$ have different roles: the first determines what a user may select, while the second follows the activation rule of Eq. (3.4) and states whether that physical beam radiates. The realized connection is therefore

決策時的遮罩 $m_{u,c}(t)$ 與實體波束啟用變數 $z_{s,v}(t)$ 的功能不同：前者決定使用者能選什麼，後者由式 (3.4) 的啟用規則決定該實體波束是否輻射。實際連線為

$$
x_{u,b_u(c,t)}(t)
=a_{u,c}(t)\,z_{b_u(c,t)}(t).
\tag{4.5a}
$$

Thus, a user is connected only when the candidate was selected and the corresponding beam radiates. The link must then also be feasible: a link whose required power exceeds the per-beam limit is declared infeasible, and that user is in outage for the step. The selections of all users form the joint action:

因此，候選必須被選中且對應波束確實在輻射，使用者才會連上該波束。連上之後仍須滿足鏈路可行性：所需功率超過每波束上限者判為不可行，該使用者於該步為 outage。所有使用者在同一時間步的選擇合稱為聯合動作：

$$
a(t) = \big(a_{1}(t),a_{2}(t),\ldots,a_{U}(t)\big).
\tag{4.6}
$$

Valid selections determine beam activation, whose state follows Eq. (3.4). Equation (4.5a) then gives the realized connections, from which the next state and the three rewards are calculated.

各波束依有效選擇形成啟用結果，其啟用狀態由式 (3.4) 決定。接著由式 (4.5a) 得到實際連線，再計算下一個狀態與三個獎勵。

Together, the state, action, reward vector, environment transition, and discount factor form a multi-objective Markov decision process.

以上狀態、動作、獎勵向量、環境轉移與折扣因子共同構成多目標馬可夫決策過程。

The original MODQN builds one Q-network for each objective, giving $\overrightarrow Q(s_u,a)=[Q_1(s_u,a),Q_2(s_u,a),Q_3(s_u,a)]$ \[2\]. The three Q-values are combined with weights $\Omega=[\omega_1,\omega_2,\omega_3]$, and each user selects the action with the largest combined value from $A_u(t)$, $\epsilon$-greedy exploration is added during training. Each Q-network is updated by temporal-difference learning using its own objective reward. The concrete weights are reported in Section 5.1.

原始 MODQN 為三個目標各建立一個 Q 網路，得到 $\overrightarrow Q(s_u,a)=[Q_1(s_u,a),Q_2(s_u,a),Q_3(s_u,a)]$ \[2\]。三個 Q 值以權重 $\Omega=[\omega_1,\omega_2,\omega_3]$ 加權後，每位使用者從 $A_u(t)$ 中選出綜合價值最高的動作；訓練期間再加入 $\epsilon$-greedy 探索。各 Q 網路使用自己的目標獎勵進行時間差分更新。權重的具體設定列於第 5.1 節。

MCRL retains MODQN's three objective Q-networks and per-user independent $\arg\max$ selection. Experience shaping and reward shaping **act only during training**, modifying the training experiences and the catfish agent's first reward respectively, the input representation and the selection rule at deployment are the same as in MODQN.

MCRL 沿用 MODQN 的三個目標 Q 網路與逐使用者 $\arg\max$ 選擇。經驗塑形與獎勵塑形**只在訓練期間作用**，分別調整訓練經驗與鯰魚代理的第一個獎勵；部署時的輸入表示與選法都與 MODQN 相同。

Figure 4-1 locates these mechanisms in data collection and parameter updating.

圖 4-1 標示各機制在資料蒐集與參數更新中的作用位置。

![Fig. 4-1 Intervention points in the MODQN update](figures/0727/fig4-0_modqn-update-interventions.png){width=155mm}

Fig. 4-1: Intervention points of MCRL in the MODQN update. Energy-efficiency stratification and competitive reward process catfish experiences, periodic intervention supplies a mixed batch for the main agent, asymmetric discounting distinguishes the two within-episode weightings.

Figure 4-2 presents the correspondence between the main and catfish agents at the objective-network level.

圖 4-2 以目標網路為單位呈現主代理與鯰魚代理的對應關係。

![Fig. 4-2 Objective-network view of MCRL](figures/0727/fig4-1_mcrl-architecture.png){width=150mm}

Fig. 4-2: Objective-network view of MCRL. The main and catfish sides each contain three objective Q-networks, with the one-to-one correspondence $Q_j^M\leftrightarrow Q_j^{F}\leftrightarrow r_j$. Each side scalarizes its three Q-values using the common weights $\Omega$ and selects one action.

Figure 4-3 shows the trajectories, replay buffers, and periodic intervention from the agent-and-data-flow perspective.

圖 4-3 補充兩個代理的軌跡、經驗池與週期性介入關係。

![Fig. 4-3 Role-level MCRL training architecture](figures/0727/fig4-1_training-architecture.png){width=125mm}

Fig. 4-3: Agent-and-data-flow view of MCRL. The main and catfish agents each generate a training trajectory and maintain a replay buffer. Catfish transitions are routed by their first-objective score, and periodic intervention uses a mixed batch to update the main agent, only the main agent is deployed after training.

## 4.3 Experience Shaping with the Catfish Agent

This section explains how MCRL uses an auxiliary catfish role in the three-objective handover problem.

本節說明 MCRL 如何在三目標換手問題中使用鯰魚輔助角色。

The main agent and the catfish agent are each a three-objective MODQN. Both sides contain three online Q-networks and three target networks. $Q_j^M$ and $Q_j^{F}$ correspond to the same objective $r_j$, where $j=1,2,3$ denote energy efficiency, handover, and load balancing. Within each side, the three objective networks follow the deep Q-network training procedure \[27\] and use the same states, actions, transitions, and replay buffer, while each reads the $j$th component of the reward vector. Training therefore has two MODQN agents, after training, only the main agent is retained.

主代理和鯰魚代理各是一組三目標 MODQN。兩端都使用三個線上 Q 網路和三個目標網路，$Q_j^M$ 與 $Q_j^{F}$ 分別對應同一個目標 $r_j$，其中 $j=1,2,3$ 依序代表能量效率、換手和負載平衡。兩端各自學習自己的軌跡和經驗；每一端的三個目標網路沿用深度 Q 網路的訓練流程 \[27\]，共用該端的狀態、動作、轉移與經驗池，再讀取獎勵向量中各自的第 $j$ 個分量。訓練時共有兩組 MODQN；完成訓練後只保留主代理。

The three rewards have different units and scales. After the environment produces a reward and before it enters a replay buffer, component $j$ is divided by a fixed positive constant $c_j$, so that $\bar r_{j,u}^{d}=r_{j,u}^{d}/c_j$, the complete update expression is given in Eq. (4.13). The term “unshaped reward” denotes this calibrated reward before the competitive term in Eq. (4.11) is added.

三個獎勵的單位和量級不同。環境產生獎勵後、寫入經驗池前，第 $j$ 個分量先除以固定正數 $c_j$，亦即 $\bar r_{j,u}^{d}=r_{j,u}^{d}/c_j$；完整更新式列於式 (4.13)。本文將未加入式 (4.11) 競爭項、但已完成尺度校準的獎勵稱為「未整形獎勵」。

The main-side buffer $D_M$ stores the unshaped, calibrated three-dimensional reward. The catfish-side buffer $D_{F}$ retains both unshaped and competitively shaped calibrated views: catfish TD updates use the shaped view, whereas catfish samples used by periodic intervention use the unshaped view. Only the energy-efficiency stratification threshold directly uses the first objective before calibration. Both buffers operate on complete time-step transitions containing all users.

主代理經驗池 $D_M$ 儲存未整形且已校準的三維獎勵。鯰魚經驗池 $D_{F}$ 同時保留未整形與競爭整形後的校準視圖：鯰魚代理 TD 更新使用整形視圖，週期性介入抽出的鯰魚樣本則使用未整形視圖。只有能效分層的門檻直接使用校準前的第一目標。兩個經驗池都以包含全體使用者的完整時間步轉移為單位。

Experience shaping has three components. Energy-efficiency stratification selects catfish experiences, asymmetric discounting changes how the catfish agent weights returns across steps within an episode, and periodic intervention uses part of the catfish experience for an additional main-agent update.

經驗塑形由三個部分組成：能效分層負責篩選鯰魚經驗，非對稱折扣改變鯰魚代理在回合內對各步回報的加權，週期性介入則把部分鯰魚經驗用於主代理的額外更新。

The first component is energy-efficiency stratification. At each step, the catfish side produces one complete transition bundle containing all users and the three-dimensional reward, denoted $\tau_t^{F}$. Define its stratification score as the mean unshaped additive contribution to the first objective before calibration:
$g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=U^{-1}\sum_{u\in \mathcal{U}}r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$.
This score is then compared with the empirical distribution $F_W$ of the scores from the most recent $W$ bundles. It is used only for training-time stratification and is not an evaluation metric. For $q\in(0,1)$, $F_W^{-1}(q)$ is the $q$-quantile of the empirical distribution, meaning that approximately a proportion $q$ of recent scores are no greater than this threshold. Let $q_1$ and $q_2$ satisfy $0<q_1<q_2<1$. The routing rule is:

第一個部分是能效分層。鯰魚代理在每一步產生一筆包含全體使用者和三維獎勵的完整轉移束 $\tau_t^{F}$。令分層分數為該步校準前、未整形第一目標的平均可加貢獻：
$g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=U^{-1}\sum_{u\in \mathcal{U}}r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$。
此分數再和最近 $W$ 束分數的經驗分布 $F_W$ 比較。此分數僅用於訓練分層，不作為評估指標。對 $q\in(0,1)$，$F_W^{-1}(q)$ 是經驗分布的 $q$ 分位數，表示約有比例 $q$ 的近期分數不高於該門檻。令 $q_1$ 和 $q_2$ 滿足 $0<q_1<q_2<1$，分流規則如下：

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

高分轉移束放入 $D_{F}$，中間分數的轉移束另外送入 $D_M$，低分轉移束則捨棄。分流雖然只看校準前的第一個目標，保留的仍是完整三目標轉移；寫入經驗池的獎勵則使用前述校準後的視圖。

![Fig. 4-4 Energy-efficiency stratification](figures/0727/fig4-2_ee-stratification.png){width=155mm}

Fig. 4-4: Energy-efficiency stratification. The catfish-side transition bundle $\tau_t^{F}$ is scored by its mean unshaped first-objective contribution $g^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ before calibration and compared with the recent distribution $F_W$. High-scoring bundles enter $D_{F}$, middle-scoring bundles are also sent to $D_M$, and low-scoring bundles are discarded (Eq. (4.7)), each retained buffer then uses its corresponding calibrated reward view.

The second component is asymmetric discounting. The three main-side objectives share $\beta_M$, while the three catfish-side objectives share the larger $\beta_{F}$:

第二個部分是非對稱折扣。主代理的三個目標共用 $\beta_M$，鯰魚代理的三個目標共用較大的 $\beta_{F}$：

$$
\beta_M<\beta_{F},\qquad
\beta_j^M\equiv\beta_M,\quad
\beta_j^{F}\equiv\beta_{F},\quad j=1,2,3.
\tag{4.8}
$$

A larger discount factor keeps more of the return from later steps within an episode. At the episode length $H=10$ used here, both effective horizons are at least the episode itself ($1/(1-\beta_M)=10$), so the difference appears as how weight is distributed across steps within an episode: the main side emphasizes nearer-term returns, while the catfish side counts the whole episode almost uniformly. The episode length matches the effective horizon of $\beta_M$ at ten steps, which is the setting of Table I in the source paper and therefore not a deviation.

折扣因子越大，回合內較後步驟的回報保留得越多。在本文的回合長度 $H=10$ 下，兩端的有效視野皆不短於回合本身（$1/(1-\beta_M)=10$），故差異體現為回合內各步權重的分配：主代理較重視近期回報，鯰魚代理則接近均勻計入整個回合。回合長度與 $\beta_M$ 的有效視野一致，均為 10 步，此為原論文 Table I 的設定，不構成偏離。

![Fig. 4-5 Asymmetric discounting](figures/0727/fig4-3_asymmetric-discount.png){width=175mm}

Fig. 4-5: Asymmetric discounting. The three main-side objective networks use $\beta_M$, and the three catfish-side objective networks use the larger $\beta_{F}$ (Eq. (4.8)). The relative weight of a return $n$ steps ahead is $\beta^n$, the bars only illustrate this decay.

The third component is periodic intervention. Each interval $T$ is sampled uniformly from the integer range $[T_1,T_2]$. When the interval expires, a mixed batch $B_I$ is formed from a proportion $\rho_I$ of $D_{F}$ and the remainder from $D_M$:

第三個部分是週期性介入。每次從整數區間 $[T_1,T_2]$ 均勻抽取介入間隔 $T$。間隔到期時，從 $D_{F}$ 取出比例 $\rho_I$ 的樣本，和 $D_M$ 的樣本合成一個混合批次 $B_I$：

$$
\begin{aligned}
n_{F} &= \operatorname{round}\!\left(\rho_I B\right),\\
n_M &= B-n_{F}.
\end{aligned}
\tag{4.9}
$$

Here, $B$ is the batch size and $\operatorname{round}(\cdot)$ denotes rounding to the nearest integer. Drawing $n_M$ samples from $D_M$ and $n_{F}$ samples from $D_{F}$ forms the mixed batch $B_I$, both kinds of samples use the unshaped, calibrated three-dimensional reward. The three main-side networks use the same $B_I$ and perform one additional update with $\beta_M$, a new $T$ is drawn after an intervention.

其中 $B$ 是批次大小，$\operatorname{round}(\cdot)$ 表示取最近整數。由 $D_M$ 抽取 $n_M$ 筆樣本、由 $D_{F}$ 抽取 $n_{F}$ 筆樣本，合併成混合批次 $B_I$；兩類樣本都使用未整形且已校準的三維獎勵。主代理的三個目標網路共同使用 $B_I$，並以 $\beta_M$ 額外更新一次；介入後重新抽取 $T$。

![Fig. 4-6 Periodic intervention](figures/0727/fig4-4_periodic-intervention.png){width=145mm}

Fig. 4-6: Periodic intervention. $n_M$ main-side samples and $n_{F}$ catfish-side samples form $B_I$ (Eq. (4.9)), both use unshaped, calibrated rewards. The same batch then updates $Q_1^M$, $Q_2^M$, and $Q_3^M$.

Together, the three components perform experience shaping, and they change **only** training, deployment still selects actions with the main agent.

三個部分共同完成經驗塑形，且都只改變訓練；部署時仍由主代理選擇動作。

The two sides use the same action-selection rule. Let $d\in\{M,F\}$ denote the main or catfish side, and let $A_u^d(t)$ be the feasible action set for user $u$ on that side. Each side combines its three Q-values with the common weights $\Omega=[\omega_1,\omega_2,\omega_3]$ from Section 3.2 and selects from this set. During training, each side also uses its own $\epsilon$-greedy exploration:

兩端的選動作方式相同。令 $d\in\{M,F\}$ 表示主代理端或鯰魚代理端，$A_u^d(t)$ 表示使用者 $u$ 在該端的可行動作集合。兩端都用第 3.2 節的共同權重 $\Omega=[\omega_1,\omega_2,\omega_3]$ 合成三個 Q 值，再從這個集合中選動作；訓練時另外加入各端自己的 $\epsilon$-greedy 探索：

$$
V_u^d(a,t)
=\sum_{j=1}^{3}\omega_j Q_j^d\big(s_u^d(t),a\big),
\qquad
a_u^d(t)=\arg\max_{a\in A_u^d(t)}V_u^d(a,t),
\quad d\in\{M,F\}.
\tag{4.10}
$$

Equation (4.13) shows the one-to-one correspondence between the two MODQNs. $Q_j^M$ and $Q_j^{F}$ estimate the same objective, and both sides combine their three objective values into the scalarized value $V_u^d(a,t)$. Because the two sides learn independently, they may select different actions. The three networks within one side share its selected action but keep separate network parameters. These Q-networks are trained with calibrated rewards, so the effective trade-off weight in the original units is $\omega_j/c_j$.

式 (4.10) 表示兩組 MODQN 的一一對應關係。$Q_j^M$ 和 $Q_j^{F}$ 估計同一個目標，兩端都把三個目標值合成一個綜合價值 $V_u^d(a,t)$。因為兩端獨立學習，所以可能選出不同動作。每一端的三個網路共用該端選出的動作，但各自保留網路參數。這些 Q 網路以校準後的獎勵訓練，因此原始單位下的實際取捨權重為 $\omega_j/c_j$。

## 4.4 Reward Shaping: the Competitive Reward Mechanism

This section defines the first reward used by the catfish side. The competitive reward mechanism (ACRM) compares the catfish and main agents on the energy-efficiency objective. Handover and load balancing receive no competitive term, but they are still calibrated by the same $c_j$ before entering a replay buffer.

本節定義鯰魚代理使用的第一個獎勵。競爭獎勵機制（ACRM）比較鯰魚代理和主代理在能量效率目標上的表現。換手和負載平衡不加入競爭項，但寫入經驗池前仍依相同的 $c_j$ 校準。

ACRM compares two complete joint actions under the same pre-action state and stochastic conditions. The catfish agent uses Eq. (4.10) to produce $a_{F}(t)$, while the main agent produces the exploration-free greedy action $a_{M\mid F}(t)$. The two simulations therefore differ only in their joint action. Their first objectives are both computed by Eq. (3.25). Let the raw rewards be $r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ and $r_{1,u}^{M\mid F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$, after which the difference and shaped reward are defined as:

ACRM 在相同的動作前狀態和隨機條件下比較兩個完整聯合動作。鯰魚代理依式 (4.10) 產生 $a_{F}(t)$，主代理則產生不含探索的貪婪動作 $a_{M\mid F}(t)$。兩次模擬只有聯合動作不同，第一目標都依式 (3.25) 計算。令原始獎勵為 $r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ 和 $r_{1,u}^{M\mid F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$，接著定義競爭差值和整形獎勵：

$$
r_{1,u}^{S}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)-r_{1,u}^{M\mid F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right),\qquad
r_{1,u}^{C}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=r_{1,u}^{F}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)+\eta_w\,r_{1,u}^{S}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right).
\tag{4.11}
$$

Here, $\eta_w\ge0$ is the competitive weight. Both raw $r_1$ values are calculated by Eq. (3.25) before the difference is formed. $r_{1,u}^{S}>0$ means that the catfish rollout has higher energy efficiency under the same conditions, whereas $r_{1,u}^{S}<0$ means the opposite. When $\eta_w=0$, $r_{1,u}^{C}=r_{1,u}^{F}$.

其中 $\eta_w\ge0$ 是競爭權重。兩個原始 $r_1$ 都先依式 (3.25) 計算，再形成差值。$r_{1,u}^{S}>0$ 表示鯰魚代理在相同條件下的能效較高，$r_{1,u}^{S}<0$ 則相反。當 $\eta_w=0$ 時，$r_{1,u}^{C}=r_{1,u}^{F}$。

The catfish-side shaped vector is $[r_{1,u}^{C},r_{2,u}^{F},r_{3,u}^{F}]$. ACRM first forms $r_{1,u}^{C}$ in the original units and then calibrates the entire vector. Energy-efficiency stratification still scores the uncalibrated $r_{1,u}^{F}$, samples sent to $D_M$ and the intervention batch $B_I$ use the unshaped calibrated view, catfish TD updates use the shaped calibrated view. The competitive term therefore affects only $Q_1^{F}$.

鯰魚代理的整形向量為 $[r_{1,u}^{C},r_{2,u}^{F},r_{3,u}^{F}]$。ACRM 先在原始單位下形成 $r_{1,u}^{C}$，再校準整個向量。能效分層仍以校準前的 $r_{1,u}^{F}$ 評分；送入 $D_M$ 的樣本與介入批次 $B_I$ 使用未整形的校準視圖；鯰魚代理 TD 更新則使用整形後的校準視圖。因此，競爭項只影響 $Q_1^{F}$。

![Fig. 4-7 Competitive reward mechanism](figures/0727/fig4-5_competitive-reward.png){width=175mm}

Fig. 4-7: Competitive reward on the energy-efficiency axis. Under the same pre-action state and stochastic conditions, only the complete joint action changes. Both simulations compute the first objective with Eq. (3.25), then form $r_{1,u}^{S}$ and $r_{1,u}^{C}$ (Eq. (4.11)). Both shaped and unshaped vectors are then calibrated by Eq. (4.13), and only $Q_1^{F}$ uses the competitively shaped value.

## 4.5 Overall Training Procedure

The main and catfish agents generate separate training trajectories. The competitive reward compares the two sides using the main-agent value before the update, and experience routed at that step is available to later parameter updates.

主代理與鯰魚代理各自產生訓練軌跡。競爭獎勵使用更新前的主代理價值進行配對比較；當步完成分流的經驗則供後續參數更新使用。

Pseudocode 4-1 summarizes the complete order. $E$ and $H$ are the number of training episodes and the maximum steps per episode, $B$ is the TD batch size, and $K$ is the target-network synchronization period. The interval $T$ is sampled from the range specified for Eq. (4.9).

偽程式碼 4-1 整理完整訓練順序。$E$ 與 $H$ 分別為訓練回合數與每回合最大時間步，$B$ 為 TD 批次大小，$K$ 為目標網路同步週期。介入間隔 $T$ 依式 (4.9) 所述範圍抽取。

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

主代理的 TD 更新讀取未整形的校準向量；鯰魚代理的 TD 更新讀取 $[r_{1,u}^{C},r_{2,u}^{F},r_{3,u}^{F}]$ 校準後的向量。在此令 $d\in\{M,F\}$ 表示主代理或鯰魚代理，並以 $\beta_d$ 表示該端的折扣因子。兩端沿用原論文式 (16) 的形式，**每個目標各自在自己的目標網路上取最大值**：

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

若下一個狀態是終止狀態，TD target 只有當步獎勵；否則再加上折扣後的目標網路價值，且**每個目標各自在自己的目標網路上取最大值**。主代理與鯰魚代理各自做一次 TD 更新；週期性介入則用 $B_I$ 對主代理額外做一次 TD 更新。

Taking a separate maximum per objective during training is distinct from the deployment rule of (4.13), which scalarizes with $\Omega$ before the $\arg\max$. This is the design of the source paper and is retained unchanged.

訓練端每個目標各自取最大值，與部署端式 (4.10) 以 $\Omega$ 純量化後取 $\arg\max$ 是兩件不同的事；這是原論文的設計,本文沿用,不另行更動。

The three rewards have different units and magnitudes: bit/J, handover cost, and a beam-occupancy count. The following calibration is a thesis-defined training contract, not a formula stated in the original MODQN paper. The original paper stores the raw reward components and directly scalarizes the learned Q-values with $\Omega$, it does not introduce $c_j$. This thesis adds $c_j$ so that the three objectives enter training on fixed, declared scales. Before a sample enters a replay buffer, each reward is divided by the fixed calibration constant $c_j$:

三個獎勵的單位和量級不同：第一個的單位為 bit/J，第二個是換手成本，第三個是波束服務人數的計數。下列校準是本論文自己定義的訓練契約，不是原始 MODQN 論文明確寫出的公式。原論文保存原始 reward components，再直接以 $\Omega$ 對學到的 Q 值做純量化，沒有引入 $c_j$。本論文為了讓三個目標以固定且明確宣告的尺度進入訓練，加入 $c_j$；因此樣本放入經驗池前先除以固定的校準常數 $c_j$：

$$
\bar r_{j,u}^{d}(t)=\frac{r_{j,u}^{d}(t)}{c_j},\qquad
c_j>0,\qquad j\in\{1,2,3\},
\tag{4.13}
$$

Here, $r_{j,u}^{d}(t)$ is the $j$th update reward on side $d$ before calibration and $\bar r_{j,u}^{d}(t)$ is the calibrated value. Before training starts, the constants $c_j$ are fixed and then shared by the training procedures. Consequently, the scalarization in Eq. (4.10) and the TD target in Eq. (4.12) use the same scale. In the original units, the effective trade-off weight is $\omega_j/c_j$.

其中 $r_{j,u}^{d}(t)$ 是端 $d$ 校準前的第 $j$ 個更新獎勵，$\bar r_{j,u}^{d}(t)$ 是校準後的值。訓練開始前固定 $c_j$，並由各訓練程序共用。這樣式 (4.10) 的純量化和式 (4.12) 的 TD target 都使用同一尺度；原始單位下的實際取捨權重為 $\omega_j/c_j$。

Deployment retains the three main-agent objective networks. Each user computes the scalarized value in Eq. (4.10) and uses $\arg\max$ to select a service beam.

部署時只保留主代理的三個目標網路。每位使用者依式 (4.10) 計算綜合價值，並以 $\arg\max$ 選出服務波束。
