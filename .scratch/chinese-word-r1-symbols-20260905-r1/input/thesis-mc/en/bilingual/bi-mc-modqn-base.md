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

低軌衛星（LEO）網路覆蓋廣、延遲較低，但衛星高速移動使波束覆蓋快速變化，換手因而頻繁且不易決策。既有的多目標深度 Q 學習網路（Multi-Objective Deep Q-Learning Network, MODQN）以吞吐量、換手成本與負載平衡三個獎勵項建模此問題，但吞吐量獎勵未反映偏軸角與干擾對能量效率的影響。每位使用者又各自取最大值、看不到彼此的選擇，容易一起指向同一波束而過度集中；同一波束上的使用者均分頻寬，集中會直接壓低每個人的速率，而學習端從訓練到部署都看不到其他使用者當步的選擇。以該方法為基準，擴充為鯰魚多目標強化式學習（Multi-Catfish Reinforcement Learning, MCRL）框架。獎勵端把吞吐量改為角度感知能量效率，並由鏈路角度增益直接決定發射功率：每一段 uninterrupted served physical link 以固定的段起始功率 $p^{0}$ 起始，只有連續同一實體鏈路時才依前一步功率與角度增益比遞推。偏軸角降低波束增益時，同一連續服務段的遞推功率可能上升，並與實際 SINR、吞吐量及系統耗能共同改變能量效率；handover、outage、unserved、re-entry 與 episode reset 都重新起始。訓練時，主代理與鯰魚代理各是一組三目標 MODQN：兩端的三個 Q 網路均與能量效率、換手及負載平衡一一對應，鯰魚代理三網路則共用一條環境軌跡與一個經驗池。經驗塑形採能效分層、非對稱折扣與週期性混合批次介入，獎勵塑形只在鯰魚代理能效獎勵加入配對競爭項，兩者都只在訓練期作用，部署選法不變。

Keywords: Low Earth Orbit Satellite, Multi-Beam Network, Handover Decision, Multi-Objective Reinforcement Learning, MODQN, Multi-Catfish, Load Balancing, Energy Efficiency

關鍵字：低軌衛星、多波束網路、換手決策、多目標強化式學習、MODQN、Multi-Catfish、負載平衡、能量效率

# 1. Introduction

In recent years, mobile communications have advanced toward sixth-generation systems and non-terrestrial networks. Low Earth Orbit (LEO) satellites provide broad coverage and low propagation delay, and can serve remote areas, maritime regions, and airspace where ground infrastructure is difficult to deploy, which is why they have drawn attention. However, LEO satellites orbit at high speed, causing the available satellites and beams to change continuously, making connection maintenance and handover decisions more difficult.

近年來行動通訊朝第六代行動通訊與非地面網路發展。低軌衛星能提供大範圍覆蓋與較低傳播延遲，可服務偏遠地區、海上與空中等難以部署地面基礎建設的環境，因而受到重視。但低軌衛星高速繞行地球，使用者可連接的衛星與波束隨時間不斷改變，連線維持與換手決策也因此更加困難。

In multi-beam LEO satellite systems, a single satellite serves different geographic regions using multiple beams, and users may require handover between beams or satellites due to satellite movement, coverage boundary changes, or degrading service quality. Using signal strength alone for beam selection may cause excessive load on certain beams, prioritizing handover reduction may leave users on progressively degrading connections, focusing on load balancing may sacrifice transmission quality for some users. Therefore, multi-beam LEO handover should not rely on a single metric but must simultaneously consider multiple objectives such as throughput, handover cost, and load balancing.

在多波束低軌衛星系統中，一顆衛星以多個波束服務不同地理區域，使用者可能因衛星移動、波束覆蓋邊界改變或服務品質下降，而需在不同波束或不同衛星間換手。若只依訊號強度選波束，可能造成部分波束負載過高；只追求減少換手，可能讓使用者停留在逐漸變差的連線；只顧負載平衡，又可能犧牲部分使用者的傳輸品質。因此，低軌衛星的多波束換手不宜只用單一指標，而需同時考慮吞吐量、換手成本與負載平衡等多個目標。

To address this type of dynamic decision problem, existing studies have approached LEO satellite handover through deep reinforcement learning and multi-objective learning, respectively emphasizing access delay and collisions, and throughput and handover cost \[1\], \[2\]. Among them, Sun et al. formulated multi-beam LEO satellite handover as a multi-objective deep-reinforcement-learning problem using a Multi-Objective Deep Q-Learning Network (MODQN) \[2\].

為了處理這類動態決策問題，既有研究已從深度強化式學習與多目標學習等方向處理低軌衛星換手問題，分別關注接取延遲與碰撞，以及吞吐量與換手成本等面向 \[1\], \[2\]。其中，Sun 等人提出的多目標深度 Q 學習網路（Multi-Objective Deep Q-Learning Network, MODQN）將低軌衛星多波束換手表達為多目標深度強化式學習問題 \[2\]。

Energy-aware, beam-gain, and spectrum-coexistence studies further show that link geometry, power cost, and interference affect handover and energy evaluation \[3\], \[4\], \[5\]. Handover work under dynamic propagation emphasizes channel state and load \[6\], while beam management under stochastic traffic and time-varying topology highlights the tradeoff among service quality, load, and system resources \[7\]. These studies, however, mostly address individual parts of the problem, a framework that jointly connects off-axis angle, transmit power determined directly by angle gain, and MODQN-based multi-objective training for multi-beam LEO satellite handover remains absent.

另一方面，能源感知、波束增益與頻譜共存相關研究顯示，鏈路幾何、功率成本與干擾都會影響換手及能源評估 \[3\], \[4\], \[5\]；動態傳播條件下的換手研究強調通道狀態與負載 \[6\]，隨機流量和時變拓樸下的波束管理則凸顯服務品質、負載與系統資源之間的取捨 \[7\]。然而，前述研究多從個別面向處理問題，尚缺少一個將偏軸角、由角度增益直接決定的發射功率，以及 MODQN 多目標訓練整合於低軌衛星多波束換手的框架。

This study therefore extends the MODQN baseline into Multi-Catfish Reinforcement Learning (MCRL), modifying the reward and the training procedure to address energy efficiency and beam concentration. The main contributions are as follows:

因此，本文以 MODQN 為基準，擴充為鯰魚多目標強化式學習（Multi-Catfish Reinforcement Learning, MCRL），並針對能量效率與波束集中問題調整獎勵與訓練方式。主要貢獻如下：

- MCRL retains MODQN's multi-objective reinforcement-learning architecture and replaces the first reward term with angle-aware energy efficiency. Each uninterrupted served physical-link segment starts at the segment-start power $p^{0}$, and consecutive service of the same link applies the previous-step power and angle-gain recurrence, the same realized power then determines interference, throughput, and system power consumption, with no cap, clip, or projection in the physical formula.
- MCRL retains the deployment rule in which each user independently selects its maximum-valued action. Training adds experience shaping and reward shaping, and **both act only during training**, the input representation and the selection rule at deployment are the same as in MODQN.

- MCRL 保留 MODQN 的多目標強化式學習架構，把第一個獎勵項由吞吐量改為角度感知能量效率。每個 uninterrupted served physical-link segment 以段起始功率 $p^{0}$ 起始，連續同一實體鏈路時由前一步功率與角度增益比遞推；同一個實際功率再決定干擾、吞吐量與系統耗能，公式不加 cap、clip 或 projection。
- MCRL 保留部署時逐使用者取最大值的選擇規則。訓練端加入經驗塑形與獎勵塑形，兩者只在訓練期間作用。部署時的輸入表示與選法都與 MODQN 相同。

The remaining chapters are organized as follows. Chapter 2 reviews related work on LEO satellite handover, multi-beam resource management, energy efficiency, and reinforcement learning. Chapter 3 describes the system model and problem formulation. Chapter 4 introduces the MCRL method. Chapter 5 describes the simulation settings and evaluation procedure. Chapter 6 summarizes the study and discusses limitations and future directions.

其餘章節安排如下。第二章回顧低軌衛星換手、多波束資源管理、能量效率與強化式學習的相關研究。第三章說明系統模型與問題形式化。第四章介紹 MCRL 方法。第五章說明模擬設定與評估方式。第六章總結研究內容，並說明研究限制與未來可能方向。

# 2. Background

This chapter reviews LEO satellite handover, multi-objective reinforcement learning, catfish competitive learning, and capacity-constrained decisions, then positions the problem addressed in this study.

本章先回顧低軌衛星換手、多目標強化式學習、鯰魚競爭學習與容量受限決策，再說明本研究的問題定位。

## 2.1 Related Work

LEO satellite handover involves high-speed satellite motion, changing beam coverage, user connection quality, and system load. Existing studies have applied deep reinforcement learning directly to handover decisions. Lee et al. \[1\] learned handover protocols that reduce access delay and collisions. Learning through interaction with the environment helps these methods adapt to time-varying communication conditions.

低軌衛星換手問題涉及衛星高速移動、波束覆蓋變化、使用者連線品質與系統負載等因素。既有研究首先將深度強化式學習用於換手決策。Lee 等人 \[1\] 以深度強化式學習學習換手協定，以降低接取延遲與碰撞情形。這類方法透過與環境互動學習決策，較能因應隨時間變化的通訊環境。

As energy costs receive attention, handover decisions have also begun incorporating energy considerations. Ntabeni et al. \[3\] proposed energy-aware Q-learning that jointly considers signal quality, handover frequency, and energy efficiency. Chen et al. \[4\] proposed a joint LEO handover and fast beam switching (HOBS) algorithm that uses historical signal-quality and beam-index information to narrow the search range and reduce beam-training latency, it also accounts for signal-to-interference-plus-noise ratio, beam transmit power, beam gain, beam switching, and both intra-satellite and inter-satellite interference. Mendonça et al. \[5\] considered off-axis antenna loss and interference management in spectrum-coexistence handover, showing that beam angle and interference affect handover decisions. Liu et al. \[6\] used multi-agent deep reinforcement learning with a three-state Markov model of dynamic propagation conditions, allowing decisions to consider channel state, load, and handover performance. The channel, interference, and power models in Chapter 3 draw on these treatments of signal quality and beam power.

隨著能源成本受到重視，換手決策也開始納入能量考量。Ntabeni 等人 \[3\] 提出能量感知 Q 學習，把訊號品質、換手次數與能量效率一併納入。Chen 等人 \[4\] 提出聯合低軌衛星換手與快速波束切換（HOBS）演算法，利用歷史訊號品質與波束索引縮小搜尋範圍，以降低波束訓練延遲；該方法同時考量訊號干擾雜訊比、波束發射功率、波束增益與波束切換，並把同衛星與跨衛星干擾納入訊號品質計算。Mendonça 等人 \[5\] 在頻譜共存的換手情境中考量偏軸天線損失與干擾管理，說明波束角度與干擾對換手決策具有影響。Liu 等人 \[6\] 則以多代理深度強化式學習處理換手，以三態 Markov 模型描述動態傳播條件，使決策能同時考慮通道狀態、負載與換手表現。第三章的通道、干擾與功率模型參考了上述研究對訊號品質與波束功率的處理方式。

Multi-objective reinforcement learning addresses the trade-offs among transmission performance, handover cost, and load distribution. Sun et al. \[2\] formulated LEO multi-beam handover as a multi-objective deep-reinforcement-learning problem in MODQN, using throughput, handover cost, and load balancing as three reward terms and learning their action values with three parallel Q-networks. Because it addresses the same handover setting and objectives, MODQN is the primary baseline for this study. Song et al. \[8\] also incorporated throughput, handover frequency, and load balancing into multi-objective handover. Tajmajer \[9\] used decision values for modular scalarization, whereas Basaklar et al. \[10\] processed the objectives separately during learning rather than combining them into a single scalar at the outset. MCRL retains MODQN's three objective networks and linear scalarization, while changing the first reward and the training procedure.

多目標強化式學習著重於換手決策中的多項取捨。Sun 等人 \[2\] 建立的 MODQN 把低軌衛星的多波束換手設計為多目標深度強化式學習問題，以吞吐量、換手成本與負載平衡為三個獎勵項，並用三個並行的 Q 網路各自學習一個目標的動作價值。由於同樣關注低軌衛星的多波束換手、且需同時處理多個目標，MODQN 是本方法最主要的基準。Song 等人 \[8\] 也以深度強化式學習將吞吐量、換手次數與負載平衡納入多目標換手。Tajmajer \[9\] 以決策值進行模組化純量化；Basaklar 等人 \[10\] 則讓不同目標在學習過程中分別處理，而非在一開始合成單一純量。MCRL 沿用 MODQN 的三個目標網路與線性純量化，改動集中在第一個獎勵的定義與訓練方式。

The MODQN baseline backbone used in this study is shown in Fig. 2-1. Three Q-networks estimate action values for energy efficiency, handover, and load balancing, which are scalarized by weights $\Omega$ and selected with $\epsilon$-greedy exploration. The environment returns a three-dimensional reward and the next state, after transitions enter replay, target networks construct temporal-difference targets for updating the three online networks. The first objective in the figure uses the angle-aware energy efficiency defined in this study, the additional MCRL training mechanisms are described in Chapter 4.

本研究採用的 MODQN 基準骨幹如圖 2-1。三個 Q 網路分別估計能量效率、換手與負載平衡的動作價值，再以權重 $\Omega$ 純量化並透過 $\epsilon$-greedy 選擇動作。環境回傳三維獎勵與下一狀態，轉移存入回放池後，以目標網路建立時間差分目標並更新三個線上網路。圖中第一個目標採用本研究的角度感知能量效率；MCRL 額外的訓練機制於第四章說明。

![Fig. 2-1 MODQN baseline used in this study](figures/0727/fig2-1_modqn-baseline.png){width=155mm}

Fig. 2-1: MODQN baseline backbone used in this study. The three objective Q-networks share state input and a feasible-action mask, then scalarize with weights $\Omega$ to select actions. Environment transitions enter replay, and the three online/target network pairs update with their respective objective rewards. The first objective shows the angle-aware energy efficiency adopted here, which differs from the original MODQN throughput objective, no additional MCRL training-time shaping is included.

The selection and use of training experience also influence the learned policy. Schaul et al. \[11\] proposed prioritized experience replay, adjusting sampling probabilities from temporal-difference errors so that more informative transitions are used more often. Ke \[12\] proposed Catfish Deep Reinforcement Learning (CDRL), which introduces a catfish role during training to promote exploration and experience use without directly producing deployment decisions. CDRL was originally applied to energy-efficient control in RIS-aided communications. This study extends that auxiliary-training approach to multi-objective handover: both the main and catfish agents are three-objective MODQNs, and the three networks within each agent correspond to the three objectives. In entity-based multi-agent reinforcement learning, a user, satellite, or beam is chosen as the agent unit and multiple agents make decisions jointly. The two MCRL agents instead serve as training roles for the same handover problem, neither controls one particular network entity. The catfish agent supplies additional experience and competitive signals during training, while the main agent continues to learn from its own experience. Chapter 4 describes these mechanisms.

訓練經驗的選取與使用也會影響學到的策略。Schaul 等人 \[11\] 提出的優先經驗回放依時間差分誤差調整取樣機率，讓資訊量較高的轉移更常被使用。Ke \[12\] 提出的鯰魚效應深度強化式學習（CDRL）則在主代理旁加入鯰魚角色，於訓練中促進探索與經驗利用，而不直接輸出部署決策。CDRL 原本用於 RIS 輔助通訊的節能控制；本研究將此輔助訓練方式延伸到多目標換手，使主代理與鯰魚代理都採三目標 MODQN，每個代理內的三個網路分別對應三個目標。一般按網路實體建模的多代理強化式學習，會依問題設定把使用者、衛星或波束當作代理單位，讓多個代理共同決策。MCRL 的兩個代理則是同一換手問題中的訓練角色，不分別控制某個使用者、衛星或波束。鯰魚代理在訓練期間提供額外經驗與競爭訊號，主代理仍根據自己的經驗更新。第四章將說明這些訓練機制。

Capacity and resource constraints are another important issue in multi-beam systems. Zhu et al. \[7\] studied beam management under stochastic traffic arrivals and time-varying topology, balancing service quality, beam load, and system resources. For reinforcement-learning problems with constraints, Calvo-Fullana et al. \[13\] added constraint information to the state, and Agorio et al. \[14\] applied the same approach to multi-agent assignment. Holder et al. \[15\] used reinforcement learning for satellite assignment under limited resources, while Ye et al. \[16\] studied load-aware user association in cellular networks. The training-shaping strategies in Chapter 4 draw on these approaches.

容量與資源限制也是多波束系統的重要問題。Zhu 等人 \[7\] 在隨機流量到達與時變拓樸的條件下探討多波束低軌衛星網路的波束管理，嘗試在服務品質、波束負載與系統資源之間取得平衡。在以強化式學習處理約束方面，Calvo-Fullana 等人 \[13\] 將約束資訊加入狀態，Agorio 等人 \[14\] 也將此作法用於多代理指派問題。Holder 等人 \[15\] 以強化式學習處理有限資源下的衛星指派，Ye 等人 \[16\] 則在蜂巢式網路中研究兼顧負載平衡的使用者關聯。第四章的訓練塑形策略以這些約束處理方法為參考。

## 2.2 Motivation

Taken together, the studies reviewed in Section 2.1 reveal three issues that have not been addressed jointly. First, the first reward in existing multi-objective handover methods is often still throughput-centered, while energy-aware work less often connects angle gain, off-axis-induced power changes, interference, realized throughput, and system energy consumption in a single energy-efficiency chain. Second, MODQN's three objectives generally use the same learning workflow, while prior catfish-style auxiliary learning has mainly been studied in single-objective problems, objective-wise auxiliary training has not yet been defined. Third, independent per-user selection cannot directly see the other users' choices or the resulting beam congestion at the same time step. Existing constraint approaches often change the deployment-time assignment procedure or add constraint information to the state, fewer address it while retaining the original deployment rule.

綜合第 2.1 節，本研究聚焦三個尚未被同時處理的問題。第一，既有多目標換手方法的第一個獎勵往往仍以吞吐量為主；能量感知研究則較少把鏈路角度增益、偏軸角造成的功率變化、干擾、實際吞吐量與系統能耗串成同一條能效計算鏈。第二，MODQN 的三個目標通常採用相同的學習流程，而既有鯰魚式輔助學習多設定在單一目標問題，尚未定義如何讓輔助訓練按不同目標分工。第三，每位使用者獨立選擇時，無法直接看見同一時間步其他使用者的選擇與各波束的壅塞程度；既有約束處理常改變部署時的指派程序，或將約束資訊加入狀態，較少在保留原本部署選法的前提下處理這個問題。

MCRL addresses these problems through two design choices. First, it replaces the first reward with each user's additive contribution to angle-aware system energy efficiency, so that the link-quality and power costs caused by off-axis angle enter the same objective. Second, in Multi-Catfish training, both the main and catfish sides use three-objective MODQNs, whose three Q-networks correspond to energy efficiency, handover, and load balancing. The training process includes experience shaping and reward shaping: experience shaping uses energy-efficiency stratification, asymmetric discounting, and periodic mixed-batch intervention to change the experiences used during training, reward shaping adds a same-state competitive comparison only to the catfish side's first objective, thereby aligning the auxiliary training with the corresponding objectives. The two shaping strategies act only during training. At deployment, only the main agent is retained and each user still takes its own argmax.

本研究以兩類設計回應上述問題。第一，將第一個獎勵改為角度感知系統能量效率的逐使用者可加貢獻，讓偏軸角造成的鏈路品質與功率代價進入同一個目標。第二，在 Multi-Catfish 訓練中，主代理與鯰魚代理都採三目標 MODQN，兩組各自的三個 Q 網路分別對應能量效率、換手與負載平衡。訓練過程包含經驗塑形與獎勵塑形：經驗塑形透過能效分層、非對稱折扣與週期性混合批次介入改變訓練時取用的經驗；獎勵塑形只在鯰魚代理的第一個目標加入同狀態的競爭比較，使輔助訓練有明確的目標對應。兩個塑形策略只在訓練期作用，部署時只保留主代理，每位使用者仍各自取最大值。

A larger off-axis angle reduces beam gain and can lower the received signal power, SINR, and throughput. Within a continuing served segment, a lower current gain than the previous gain can raise RF power under the previous-step recurrence and may increase power-amplifier consumption. A new segment does not retain inactive-link power and instead restarts at $p^{0}$, the recurrence has no power cap, clip, or projection. Section 3.1.3 gives the complete model, and Section 3.2 defines the formal reward.

偏軸角增大時，波束增益降低，接收訊號與 SINR 可能下降，因而降低吞吐量；在同一連續服務段，前一步增益較高而目前增益降低時，previous-step recurrence 可能提高目前 RF power，並改變功率放大器耗能。新 segment 不沿用 inactive link 的功率，而是重新從 $p^{0}$ 開始；recurrence 不含 power cap、clip 或 projection。完整模型於第 3.1.3 節說明，正式獎勵於第 3.2 節定義。

# 3. Preliminaries

This chapter first explains how a user selects a service beam from the visible beams. It then introduces the signal quality, throughput, and power consumption of the selected link. Finally, these quantities are organized into the three objectives of energy efficiency, handover cost, and load balancing.

本章先說明使用者如何從可見波束中選擇服務波束，再介紹這條連線的訊號品質、吞吐量與耗能。最後將這些量整理成能量效率、換手成本與負載平衡三個目標。

## 3.1 System Model

### 3.1.1 Network Model

Consider a downlink multi-beam LEO satellite communication system. Because the satellites keep moving, the satellites and beams visible to each user change over time. Time is discretized into successive steps of length $\Delta t$, and the system selects one available service beam for each user at every step, the value of $\Delta t$ is given in Section 5.1. The overall scenario is shown in Fig. 3-1.

考慮一個多波束低軌衛星下行通訊系統。低軌衛星持續移動，因此使用者可見的衛星與波束會隨時間改變。將時間離散為依序排列、長度為 $\Delta t$ 的時間步，系統在每一步為每位使用者選擇一個可用的服務波束；$\Delta t$ 的設定列於第 5.1 節。整體場景如圖 3-1 所示。

![Fig. 3-1 LEO multi-beam satellite system model](figures/0727/03_fig3-1__mcrl.png){width=165mm}

Fig. 3-1: System model of a multi-beam LEO satellite network. Each user selects a service beam from the candidates provided by visible satellites. Beam direction affects signal quality, and users selecting the same beam share its resources. The system must also account for beam interference and handover cost, a beam that no user selects is not activated.

#### Users, Satellites, and Beams

Let $\mathcal{U}=\{1,\ldots,U\}$, $\mathcal{S}=\{1,\ldots,S\}$, and $\mathcal{V}=\{1,\ldots,V\}$ denote the user, satellite, and beam-index sets, respectively. The symbols $u$, $s$, $v$, and $t$ denote user, satellite, beam, and time-step indices.

以 $\mathcal{U}=\{1,\ldots,U\}$、$\mathcal{S}=\{1,\ldots,S\}$ 與 $\mathcal{V}=\{1,\ldots,V\}$ 分別表示使用者、衛星與波束索引集合；$u$、$s$、$v$ 與 $t$ 則表示使用者、衛星、波束與時間步索引。

Let $x_{u,s,v}(t)$ represent the realized connection. When $x_{u,s,v}(t)=1$, user $u$ is served by beam $v$ of satellite $s$, otherwise it is 0. Each user can connect to at most one beam, so

令 $x_{u,s,v}(t)$ 表示實際連線結果。當 $x_{u,s,v}(t)=1$ 時，使用者 $u$ 由衛星 $s$ 的波束 $v$ 服務；否則為 0。每位使用者最多連上一個波束，因此

$$
x_{u,s,v}(t) \in \{0,1\},\qquad
\sum_{s \in \mathcal{S}}\sum_{v \in \mathcal{V}}x_{u,s,v}(t) \leq 1.
\tag{3.1}
$$

Let $z_{s,v}(t)$ indicate whether beam $(s,v)$ is active. For every $u\in \mathcal{U}$, $s\in \mathcal{S}$, and $v\in \mathcal{V}$, a user can connect only to an active beam, so

以 $z_{s,v}(t)$ 表示波束 $(s,v)$ 是否啟用。對任意 $u\in \mathcal{U}$、$s\in \mathcal{S}$ 與 $v\in \mathcal{V}$，使用者只能連到已啟用的波束，因此

$$
z_{s,v}(t)\in\{0,1\},\qquad
x_{u,s,v}(t)\le z_{s,v}(t).
\tag{3.2}
$$

#### Beam Activation and Load

The number of users actually served by beam $(s,v)$ is

波束 $(s,v)$ 實際服務的使用者數量為

$$
U_{s,v}(t) = \sum_{u \in \mathcal{U}}x_{u,s,v}(t).
\tag{3.3}
$$

This study activates only beams with connected users, so beam activation follows directly from the connection result:

本研究只啟用有使用者連接的波束，波束的啟用狀態因此由連線結果直接決定：

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

沒有使用者的波束不發射功率，也不產生干擾。本研究不另設每顆衛星可同時啟用的波束數上限。

### 3.1.2 Geometry and Channel Model

In LEO satellite communications, geometry determines both the distance between a user and a satellite and the user's direction relative to a beam center. Following non-terrestrial network channel models and LEO satellite research \[17\], \[18\], the slant range between user $u$ and satellite $s$ is defined as in (3.5):

在低軌衛星通訊中，幾何關係同時決定使用者與衛星的距離，以及使用者相對於波束中心的方向。參考非地面網路通道模型與低軌衛星相關研究 \[17\], \[18\]，定義使用者 $u$ 與衛星 $s$ 之間的斜距如式 (3.5)：

$$
d_{u,s,v}(t) = \sqrt{R_{E}^{2}{\sin}^{2}\alpha_{u,s}(t) + h_{s}^{2} + 2R_{E}h_{s}} - R_{E}\sin\alpha_{u,s}(t).
\tag{3.5}
$$

Here, $\alpha_{u,s}(t)$ is the elevation angle of the user relative to the satellite, $R_{E}$ is the Earth's radius, and $h_{s}$ is the satellite altitude. The index $v$ records the slant range at the candidate-link level, its value may be identical across beams on the same satellite. The slant range is one component of the linear link-power factor used below, which does not directly carry the wanted-link angular pattern.

其中 $\alpha_{u,s}(t)$ 為使用者相對於衛星的仰角，$R_{E}$ 為地球半徑，$h_{s}$ 為衛星高度。$v$ 將斜距記為候選波束鏈路層量；對同一顆衛星的不同波束，它的數值可以相同。斜距是後續線性鏈路功率因子的一部分，該因子不直接承載 wanted-link 的角度型樣。

The off-axis angle describes the angular difference between the user's direction and the beam-center direction. A multibeam LEO model defines this angle through the arccosine of two direction vectors \[19, Eq. (5)\], so the off-axis angle of user $u$ relative to beam $(s,v)$ is defined as in (3.6):

偏軸角描述使用者方向與波束中心方向之間的角度差。多波束低軌衛星模型以兩個方向向量的夾角定義偏軸角 \[19, Eq. (5)\]，因此使用者 $u$ 相對於波束 $(s,v)$ 的偏軸角定義如式 (3.6)：

$$
\theta_{u,s,v}(t) = \arccos\left( \frac{\mathbf{v}_{u,s,v}(t) \cdot \mathbf{r}_{u,s,v}(t)}{\parallel \mathbf{v}_{u,s,v}(t) \parallel \parallel \mathbf{r}_{u,s,v}(t) \parallel} \right).
\tag{3.6}
$$

Here, $\mathbf{v}_{u,s,v}(t)$ is the beam-center direction recorded for candidate link $(u,s,v)$, and $\mathbf{r}_{u,s,v}(t)$ is the satellite-to-user direction recorded for the same link. The three indices mark link-level data ownership. $\mathbf{v}$ may have the same value across users of one beam, and $\mathbf{r}$ may have the same value across beams of one user-satellite pair. The off-axis angle is the point at which geometric information enters the energy-efficiency chain.

其中，$\mathbf{v}_{u,s,v}(t)$ 表示候選鏈路 $(u,s,v)$ 的波束中心方向向量，$\mathbf{r}_{u,s,v}(t)$ 表示同一候選鏈路由衛星指向使用者的方向向量。兩者以三下標標示資料所有權；同一波束的 $\mathbf{v}$ 可在不同使用者間取相同值，同一使用者與衛星的 $\mathbf{r}$ 也可在不同波束間取相同值。偏軸角是本文把幾何資訊導入能量效率的入口。

Following the angular pattern commonly used for multi-beam satellites and adopted in HOBS \[4\], \[20\], the transmit gain is retained only as a function of the off-axis angle:

沿用多波束衛星常用、亦見於 HOBS 的角度型樣 \[4\], \[20\]，發射端增益只保留其對偏軸角的依賴：

$$
G^{T}\!\left(\theta,\theta_{3dB}\right),\qquad
G^{T}\!\left(0,\theta_{3dB}\right)=G_0.
\tag{3.7}
$$

Here, $G_0$ is the beam-center gain. To keep the tunable antenna parameters traceable to the simulator, the main text uses a one-layer normalized-pattern expansion:

其中 $G_0$ 為波束中心增益。為了讓正文的可調天線參數與模擬器一一對應，採用一層 normalized pattern 展開：

$$
G^{T}\!\left(\theta,\theta_{3dB}\right)=G_0F\!\left(\theta,\theta_{3dB}\right),
\qquad
G^{T}\!\left(0,\theta_{3dB}\right)=G_0,
\qquad
F\!\left(0,\theta_{3dB}\right)=1.
\tag{3.8}
$$

The angular pattern adopts the $J_1/J_3$ pattern of HOBS Eq. (3) \[4\], the angle argument and pattern are

角度型樣採用 HOBS 式 (3) \[4\] 的 $J_1/J_3$ 型樣，角度參數與 pattern 為

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

其中 $J_1(\cdot)$ 與 $J_3(\cdot)$ 分別為第一類貝索函數的一階與三階，$2.07123$ 是該式的固定角度參數，同一數值亦見於其他多波束衛星文獻；$F$ 在 $\theta=0$ 自然等於 1（$1/4+3/4$），因此不需要額外的 boresight 正規化常數；但 $J_1(\mu)/(2\mu)$ 與 $36J_3(\mu)/\mu^{3}$ 在 $\mu=0$ 是 $0/0$，數值上以 $|\mu|<\epsilon_\mu$ 時直接取該極限值處理，$\epsilon_\mu$ 的設定列於第 5.1 節。$\theta_{3dB}$ 雖是固定的天線參數，但它出現在 $\mu$ 定義式的右側，並經由 $\mu$ 決定 $F$ 與 $G^{T}$ 的形狀，因此列為三者的引數：每一條定義式的等號左側都必須涵蓋右側出現的量。$G_0$ 不同，它只是乘性的尺度常數，不改變型樣形狀，故不列入引數。式 (3.10) 之後的公式在特定鏈路的偏軸角上套用同一個函數，並明寫固定參數為 $G^{T}(\theta_{u,s,v},\theta_{3dB})$。這一層不引入帶三下標的增益變數，也不設型樣選擇器。

This study does not adopt the $G_0=40$ dBi of Table I of HOBS \[4\]. The aperture $10c/f_c$, the gain of 40 dBi and the beamwidth listed there are mutually inconsistent: under either dimensionally valid reading, 40 dBi requires an aperture efficiency of $\eta=2.53$ (radius reading) or $\eta=10.13$ (diameter reading), **both greater than one**. The aperture is therefore re-derived from the beamwidth, $D=1.0275\lambda/\theta_{3dB}=17.7\lambda$, with the Ka-band aperture efficiencies of $0.639$–$0.645$ back-derived from 3GPP TR 38.821 \[22\], this gives $G_0=2000$ ($33.0$ dBi). The value is listed in Section 5.1. Throughout this thesis $\theta_{3dB}$ denotes the **full** half-power beamwidth, consistent with the cell radius $R_b=h_s\tan(\theta_{3dB}/2)$ in Section 5.1, whereas HOBS Eq. (3) normalizes by the **one-sided** half-power angle, Eq. (3.9) therefore substitutes $\theta_{3dB}/2$. The constant $2.07123$ is calibrated to exactly that point: $F=1/2$ at $\mu=2.07123$.

本研究不沿用 HOBS \[4\] Table I 的 $G_0=40$ dBi。該表列出的孔徑 $10c/f_c$、增益 40 dBi 與波束寬三值互斥；在量綱合法的兩種讀法下，40 dBi 分別要求孔徑效率 $\eta=2.53$（半徑讀法）或 $\eta=10.13$（直徑讀法），**均大於 1**。本研究改由波束寬一致的孔徑重導：$D=1.0275\lambda/\theta_{3dB}=17.7\lambda$；取 3GPP TR 38.821 \[22\] 各列反推的 Ka 頻段孔徑效率 $0.639$–$0.645$，得 $G_0=2000$（$33.0$ dBi）。數值列於第 5.1 節。本研究的 $\theta_{3dB}$ 一律指**全**半功率波束寬，與第 5.1 節的格半徑 $R_b=h_s\tan(\theta_{3dB}/2)$ 一致；HOBS 式 (3) 以**單邊**半功率角為分母，故式 (3.9) 代入 $\theta_{3dB}/2$。常數 $2.07123$ 正校準於此點：$\mu=2.07123$ 時 $F=1/2$。

Let $H_{u,s,v}(t)$ denote the linear link-power factor that does not directly carry the wanted-link angular pattern. To trace it to the channel implementation, expand H as

令 $H_{u,s,v}(t)$ 表示不直接承載 wanted-link 角度型樣的線性鏈路功率因子。為了與通道實作對應，H 展開為

$$
H_{u,s,v}(t)
=10^{-\frac{L_{u,s,v}(t)}{10}}
G^R_{u,s,v}(t),
\tag{3.10a}
$$

where

其中

$$
L_{u,s,v}(t)
=L_f\!\left(d_{u,s,v}(t),f_c\right)
+L_g\!\left(\alpha_{u,s}(t)\right)
+L_c\!\left(\alpha_{u,s}(t)\right)
+L_s\!\left(\alpha_{u,s}(t)\right).
\tag{3.10b}
$$

The four losses correspond to $L=L_{fs}+L_g+L_{sc}+L_{sf}$ of HOBS Eq. (1), this thesis writes them as $L=L_f+L_g+L_c+L_s$ to keep subscripts single-lettered: $L_f$ is the free-space path loss, $L_g$ the atmospheric gaseous absorption, $L_c$ the scintillation and $L_s$ the shadow fading, the last three vary with elevation, and their models and values are given in Section 5.1, all four are dB terms converted to a common linear scale before entering H, and $G^R_{u,s,v}(t)$ is the linear receive gain. These four terms are exactly the loss set of HOBS Eq. (1), the public expansion adds nothing below them. Scan loss, NLoS clutter, and other implementation-layer channel corrections are absorbed into $H_{u,s,v}(t)$, take no public symbol, and are not tunable parameters.

四項損耗對應 HOBS 式 (1) 的 $L=L_{fs}+L_g+L_{sc}+L_{sf}$，本文為維持單字母下標記為 $L=L_f+L_g+L_c+L_s$：$L_f$ 為自由空間路徑損耗、$L_g$ 為大氣氣體吸收、$L_c$ 為閃爍、$L_s$ 為遮蔽衰落，後三項皆隨仰角變化，其模型與數值列於第 5.1 節；四項皆以 dB 表示，代入 H 前轉成線性尺度；$G^R_{u,s,v}(t)$ 是接收端線性增益。這四項即 HOBS 式 (1) 的損耗集合，公開展開不再往下加項；掃描損耗、NLoS clutter 等實作層通道修正併入 $H_{u,s,v}(t)$，不取得公開符號，也不是可調參數。

$G^R_{u,s,v}(t)$ is written as a boresight gain minus an off-axis loss. Let $\theta^{R}_{u,s}(t)$ be the angle in degrees between the user's receive-antenna pointing direction and the direction of satellite $s$. Then

$G^R_{u,s,v}(t)$ 以軸心增益扣除離軸損耗表示。令 $\theta^{R}_{u,s}(t)$ 為使用者接收天線指向與第 $s$ 顆衛星方向之間的夾角（以度為單位），則

$$
G^R_{u,s,v}(t)
=\min\!\left\{\max\!\left\{A_R-B_R\log_{10}\theta^{R}_{u,s}(t),\,G_{R,\min}\right\},\,G_{R,\max}\right\}.
\tag{3.10c}
$$

$A_R$, $B_R$, and the floor $G_{R,\min}$ are taken from the ITU-R S.465-6 earth-station reference radiation pattern \[21\], whose stated range of 2 to 31 GHz covers the $f_c$ used here. The three are not independent settings: the recommendation gives $A_R-B_R\log_{10}\theta^{R}$ for $\theta^{R}_{\min}\le\theta^{R}<48^{\circ}$ and $G_{R,\min}$ for $48^{\circ}\le\theta^{R}\le180^{\circ}$, and the two branches join continuously at $48^{\circ}$. The boresight gain $G_{R,\max}$ is the derated value adopted for a comparable 0.6 m user terminal in an LEO handover setting \[5\], about 4.7 dB below the ideal gain of that aperture. The recommendation defines the envelope only for $\theta^{R}\ge\theta^{R}_{\min}$ (here $\theta^{R}_{\min}\approx2.498^{\circ}$ at $f_c$), this work extends the same envelope into $\theta^{R}<\theta^{R}_{\min}$ up to the $G_{R,\max}$ cap, which is a modelling simplification outside the scope of the recommendation.

$A_R$、$B_R$ 與下限 $G_{R,\min}$ 取自 ITU-R S.465-6 的地球站參考輻射型樣 \[21\]，其適用範圍為 2 至 31 GHz，涵蓋本文的 $f_c$。三者並非各自獨立設定：該建議書以 $A_R-B_R\log_{10}\theta^{R}$ 描述 $\theta^{R}_{\min}\le\theta^{R}<48^{\circ}$，以 $G_{R,\min}$ 描述 $48^{\circ}\le\theta^{R}\le180^{\circ}$，兩段在 $48^{\circ}$ 連續銜接。軸心增益 $G_{R,\max}$ 取自低軌換手情境下同級 0.6 m 使用者終端所採的降額值 \[5\]，較該孔徑的理想增益保守約 4.7 dB。該建議書只在 $\theta^{R}\ge\theta^{R}_{\min}$ 定義此包絡（本文終端在 $f_c$ 下 $\theta^{R}_{\min}\approx2.498^{\circ}$）；本文於 $\theta^{R}<\theta^{R}_{\min}$ 延用同一包絡至 $G_{R,\max}$ 截止，此為建模上的簡化，不在該建議書的規定範圍內。

The two wanted-link linear power-gain factors are still used directly as

wanted-link 的兩個線性功率增益因子仍直接相乘為

$$
H_{u,s,v}(t)G^{T}\!\left(\theta_{u,s,v},\theta_{3dB}\right).
\tag{3.10}
$$

Here, $G^{T}$ directly carries the off-axis-angle dependence, while $H_{u,s,v}(t)$ preserves the physical meaning of the remaining channel factors — the four losses of Eq. (3.10b), the receive gain, and Rician small-scale fading, whose $K$-factor $K_R$ is a scenario calibration listed in Section 5.1. Both are linear power-scale factors, not complex channel amplitudes. The thesis, the simplified symbol table, and the `/` legacy simulator frontend share this one public expansion layer that maps to simulator controls and runtime fields, only layout may differ, not formulas, symbols, or editable parameters. The public expansion is capped at the depth the source paper itself shows: the four loss terms of HOBS Eq. (1) and a single $J_1/J_3$ angular-pattern layer whose two-term structure follows HOBS Eq. (3). Deeper antenna measurement, Bessel-approximation, and channel-calibration details are outside the public formula layer. No intermediate channel symbol distinguished only by letter case is introduced. Note also that the MODQN $G_{i,l,v}$ is a channel gain whose role corresponds to $H_{u,s,v}$ here, semantically different from the antenna gains $G^{T}$ and $G^{R}$, the two same-letter symbols are not merged.

其中 $G^{T}$ 直接承載偏軸角，$H_{u,s,v}(t)$ 保留其餘通道因素的物理意義——包含式 (3.10b) 的四項損耗、接收增益，以及萊斯小尺度衰落（其 $K$ 因子 $K_R$ 屬情境校準，列於第 5.1 節）；兩者都是線性功率尺度的因子，不表示複數通道振幅。正文與簡化符號表、`/` legacy simulator 前端共用這個能和控制項／runtime 欄位對應的一層公開展開；三者只允許排版不同，不允許公式、符號或可調參數不同。公開展開的深度上限即 HOBS 正文所示的深度：式 (1) 的四項損耗，以及式 (3) 那一層的單一 $J_1/J_3$ 角度型樣結構。更深的天線量測、Bessel 近似誤差與通道校準細節不屬於公開主公式層級；不另建立只靠大小寫區分的中間通道符號。另需注意 MODQN 的 $G_{i,l,v}$ 是通道增益，其角色對應本文的 $H_{u,s,v}$，與此處的天線增益 $G^{T}$、$G^{R}$ 語意不同，不可同名合併。

### 3.1.3 Power, SINR and Throughput Model

The following keeps only actual quantities for each user--satellite--beam link. $p_{u,s,v}$ denotes actual RF transmit power, it is not obtained by inverting a target SINR, minimum rate, or lagged interference. If the implementation needs measured, predicted, or cached provenance, that information belongs in field metadata rather than in a second physical SINR.

以下只保留每一條 UE--衛星--波束鏈路的實際量。$p_{u,s,v}$ 表示實際 RF 發射功率，不再由目標 SINR、最低速率或 lagged interference 反推；若程式需要標記 measured、predicted 或 cached provenance，該資訊放在資料欄位 metadata，不另建立第二個物理 SINR。

Let $\tau_{u,s,v}$ be the start time of the current uninterrupted served physical-link $(u,s,v)$ segment. Episode reset, handover, outage, an unserved step, and re-entry all break continuity, a new segment does not retain inactive-link power and starts at $p^{0}$. Only consecutive service of the same physical link uses the previous-step recurrence:

令 $\tau_{u,s,v}$ 為目前 uninterrupted served physical link $(u,s,v)$ segment 的起始時間步。episode reset、handover、outage、unserved 與 re-entry 都會結束 continuity；新 segment 不保留 inactive-link cache，並以 $p^{0}$ 起始。只有同一實體鏈路在前後兩步都被服務時，角度感知功率才使用 previous-step recurrence：

This is an angle-aware power rule defined by this study, not an equation from the original MODQN paper. The modelling condition is to keep the product of transmit power and transmit gain constant within one continuous served segment:
$p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_{3dB})G^T(\theta_{u,s,v}(t),\theta_{3dB})
=p_{u,s,v}(t-1,\theta_{u,s,v}(t-1),\theta_{3dB})G^T(\theta_{u,s,v}(t-1),\theta_{3dB})$.
Solving for the current power gives the equation below. It compensates only the transmit-side angular gain, it does not claim that the full SINR or throughput remains constant.

這是本研究自行定義的角度感知功率規則，不是原始 MODQN 的公式。其建模條件是同一連續服務段內維持發射功率與發射增益的乘積：
$p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_{3dB})G^T(\theta_{u,s,v}(t),\theta_{3dB})
=p_{u,s,v}(t-1,\theta_{u,s,v}(t-1),\theta_{3dB})G^T(\theta_{u,s,v}(t-1),\theta_{3dB})$。
把目前功率解出後，就得到下式；它只補償發射端角度增益，並不宣稱完整 SINR 或 throughput 固定。

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

segment 起始與 segment 內的 closed form 為

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

式 (3.12) 只有在 $\tau_{u,s,v}$ 到 $t$ 的每一步都維持同一 served physical link 且角度增益為正時成立；它是式 (3.11) 的 telescoped identity，不是跨事件的 runtime state。這個關係表達前一步角度增益如何遞推實際鏈路 RF power，不引入目標 SINR、需求功率反推、beam／satellite cap、PA clamp 或 `min`／`max` 投影。

Define the system angle state $\boldsymbol{\theta}(t)$ as the collection of off-axis angles $\theta_{u,s,v}(t)$ over every $u\in \mathcal{U},\ s\in \mathcal{S},\ v\in \mathcal{V}$, and let $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$ denote the total co-channel interference relative to the wanted link.

在系統層定義全體角度狀態 $\boldsymbol{\theta}(t)$——即每一個 $u\in \mathcal{U},\ s\in \mathcal{S},\ v\in \mathcal{V}$ 的偏軸角 $\theta_{u,s,v}(t)$ 所組成的集合——並令 $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$ 表示相對於 wanted link 的總同頻干擾。

The beams use three-colour frequency reuse. Let $c_{s,v}\in\{0,1,2\}$ be the frequency colour of beam $(s,v)$, assigned from the axial coordinates $(q_{s,v},r_{s,v})$ of its ground cell on the hexagonal lattice as $c_{s,v}=(q_{s,v}-r_{s,v})\bmod 3$. The rule guarantees that any two adjacent cells carry different colours: beams of the same colour share one sub-band, and beams of different colours are orthogonal. The bandwidth available to one beam is therefore $B^{w}=B_{\mathrm{sys}}/3$, and interference arrives only from activated beams of the same colour as the serving beam. The cell layout and the axial coordinates are environment settings, given in Section 5.1.

波束以三色頻率重用配置。令 $c_{s,v}\in\{0,1,2\}$ 為波束 $(s,v)$ 的頻率顏色，依其地面蜂巢在六角格上的軸向座標 $(q_{s,v},r_{s,v})$ 指派為 $c_{s,v}=(q_{s,v}-r_{s,v})\bmod 3$。此規則使六角格上任兩個相鄰蜂巢必為異色：同色波束共用同一子頻帶，異色波束彼此正交。因此單一波束的可用頻寬為 $B^{w}=B_{\mathrm{sys}}/3$，而干擾只來自與服務波束同色且已啟用的其他波束。蜂巢排列與各波束的軸向座標屬環境設定，於第 5.1 節說明。

An activated beam radiates at a single power regardless of how many users it carries. Following the aggregation convention of the runtime, let $p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=\max_{u\in\mathcal{U}:\,x_{u,s,v}(t)=1}p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_{3dB}\right)$ be that beam's transmit power. The left-hand side retains the system angle state and the fixed beamwidth because the right-hand side takes a maximum across all served links. Following HOBS and the multi-beam LEO satellite system model \[4\], \[20\], the interference splits into same-satellite and cross-satellite terms, given in Eq. (3.12a) and Eq. (3.12b):

一支已啟用的波束以單一功率發射，不論其上載有幾位使用者；沿用執行端的聚合慣例，令 $p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=\max_{u\in\mathcal{U}:\,x_{u,s,v}(t)=1}p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_{3dB}\right)$ 為該波束的發射功率。左側保留全系統角度狀態與固定波束寬參數，因為右側會在所有已服務鏈路中取最大值。參考 HOBS 與多波束低軌道衛星系統模型 \[4\], \[20\]，將干擾分為同衛星干擾與跨衛星干擾，分別如式 (3.12a) 與式 (3.12b)：

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

且 $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})=I^{\mathrm{intra}}_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})+I^{\mathrm{inter}}_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$。每一項都以該干擾波束自己的偏軸角與線性鏈路因子計算，因為不同波束到同一位使用者的路徑損耗與增益都不同；求和以啟用指示 $z$ 為門檻，而不是以其上載有幾位使用者為權重。

The noise power is $\sigma^{2}=k_BTB^{w}$, where $k_B$ is the Boltzmann constant and $T=T_a+T_0\left(10^{NF/10}-1\right)$ is the receiver system temperature. The antenna temperature $T_a$, the receiver noise figure $NF$ and the noise-figure reference temperature $T_0$ take the VSAT values of 3GPP TR 38.821 \[22\] and are listed in Section 5.1. The noise integrates over the whole beam bandwidth and therefore does not scale with the beam's load. The unique link SINR is

雜訊功率為 $\sigma^{2}=k_BTB^{w}$，其中 $k_B$ 為波茲曼常數，$T=T_a+T_0\left(10^{NF/10}-1\right)$ 為接收系統溫度。$T_a$ 為天線溫度、$NF$ 為接收機雜訊指數、$T_0$ 為雜訊指數的參考溫度，數值取自 3GPP TR 38.821 的 VSAT 設定 \[22\]，列於第 5.1 節。雜訊在整支波束的頻寬上積分，因此與該波束的載量無關。唯一的鏈路 SINR 為

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

其中 $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})+\sigma^2>0$。這個符號同時用於基線鏈路計算與角度感知功率替換；不另定義 estimated、required、target 或帶 serving-index 巢狀下標的 SINR。

Multiplexing within a beam is time division. The $U_{s,v}(t)$ users on a beam take turns using the available bandwidth. The link throughput is \[2\], \[4\]

波束內採時分多工，同一波束上的 $U_{s,v}(t)$ 位使用者依序使用可用頻寬。因此鏈路 throughput 為 \[2\], \[4\]

$$
R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=\frac{B^{w}}{U_{s,v}(t)}
\log_2\!\left(1+\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)\right),
\qquad U_{s,v}(t)>0.
\tag{3.14}
$$

$B^w$ is the available bandwidth of one beam, for a single-user illustration, set $U_{s,v}=1$ without creating a second rate or SINR formula. The connection variable $x_{u,s,v}(t)$ selects the active service link and does not create a user-level SINR or throughput alias.

$B^w$ 是單一波束可用頻寬；單一使用者展示時只令 $U_{s,v}=1$，不另建立第二套 rate 或 SINR 公式。連線變數 $x_{u,s,v}(t)$ 只負責選取實際服務鏈路，不另建立 user-level 的 SINR 或 throughput 別名。

A beam is driven by a single power amplifier, so supply-side power is a per-beam quantity rather than a per-link one. Let $\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)>0$ be that beam's effective conversion efficiency from RF power to supply-side consumption. Then

一支波束由單一功率放大器驅動，因此電源端功率是逐波束而非逐鏈路的量。令 $\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)>0$ 為該波束由 RF power 到電源端消耗的有效轉換效率，則

$$
P^{p}_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=\frac{p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)}
{\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)}.
\tag{3.15}
$$

Radiated power is not the power actually consumed. A beam's RF signal is produced by a power amplifier, and the ratio of its RF output to the DC power it draws is the $\xi$ of Eq. (3.15). An amplifier is more efficient near saturation but less linear there, so it is operated a fixed distance below saturation, that distance is the output back-off $BO$, expressed in dB, and the saturated power is $p_{\mathrm{sat}}=p_{\max}10^{BO/10}$, where $p_{\max}$ is the per-beam operating limit after back-off. Following the power-efficiency relation of the classical class-B amplifier \[23\], the back-off region is approximated by a load-dependent square-root curve, this is an engineering approximation for system-level analysis, not a full circuit model:

發射出去的功率不等於實際耗掉的功率。波束的射頻訊號由功率放大器產生，其射頻輸出與所取用直流功率之比即為式 (3.15) 的 $\xi$。放大器接近飽和點時效率較高但較不線性，因此實務上退離飽和點一段距離運作，該距離稱為輸出回退 $BO$（以 dB 表示）：飽和功率為 $p_{\mathrm{sat}}=p_{\max}10^{BO/10}$，其中 $p_{\max}$ 是回退後的每波束操作上限。參考傳統類 B 功率放大器的功率與效率關係 \[23\]，以負載相依的平方根曲線近似回退區的效率變化；這是便於系統層分析的工程近似，不是完整的電路模型：

$$
\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=\min\!\left\{\xi_{\max},\ \xi_{\max}\sqrt{\dfrac{p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)}{p_{\mathrm{sat}}}}\right\}.
\tag{3.15a}
$$

The square root follows from the ideal class-B approximation: with $V_o$ the output voltage amplitude at fixed supply voltage and load, the RF output power satisfies $P_{\mathrm{RF}}\propto V_o^{2}$ while the average DC input satisfies $P_{\mathrm{DC}}\propto V_o$, so $\xi=P_{\mathrm{RF}}/P_{\mathrm{DC}}\propto\sqrt{P_{\mathrm{RF}}}$. At one quarter of the saturated output the efficiency is $\xi_{\max}/2$, not $\xi_{\max}/4$. The values of $\xi_{\max}$ and $BO$ are listed in Section 5.1, a Ka-band satellite-downlink GaN Doherty MMIC reports a saturated power-added efficiency of 23--31%, and about 20% at 6 dB output back-off \[24\], which is of the same order as this model without being the same measurement point. Morello and Mignone's two-carrier DVB-DSNG example uses 5.5 dB of output back-off per carrier \[25\], showing that multi-carrier operation needs a larger back-off to stay quasi-linear, that statement does not generalize to all multi-carrier systems and is cited here only as corroboration of the back-off magnitude.

平方根可由類 B 的理想近似理解：令 $V_o$ 為輸出電壓振幅，在固定供應電壓與負載下射頻輸出功率滿足 $P_{\mathrm{RF}}\propto V_o^{2}$，平均直流輸入功率則近似滿足 $P_{\mathrm{DC}}\propto V_o$，因此 $\xi=P_{\mathrm{RF}}/P_{\mathrm{DC}}\propto\sqrt{P_{\mathrm{RF}}}$。射頻輸出為飽和功率的四分之一時，效率是 $\xi_{\max}/2$ 而不是 $\xi_{\max}/4$。$\xi_{\max}$ 與 $BO$ 的數值列於第 5.1 節；Ka 頻段衛星下行 GaN Doherty MMIC 的實測飽和功率附加效率為 23--31%，6 dB 輸出回退時約 20% \[24\]，與本模型的量級一致，但並非同一測量點。Morello 與 Mignone 的雙載波 DVB-DSNG 範例對每一載波採 5.5 dB 輸出回退 \[25\]，說明多載波操作為維持準線性區需要較大的回退；該敘述不足以泛化到所有多載波系統，此處僅作為回退量級的旁證。

This shape has one consequence that matters for this thesis: because efficiency is poorer at low output, lowering the transmit power does not lower the consumed power proportionally. What actually governs energy efficiency is how much throughput a given amount of power buys, and that is why Section 3.2 takes energy efficiency, rather than transmit power alone, as the first objective.

這個形狀有一個對本論文重要的後果：由於低輸出時效率較差，把發射功率壓低並不會等比例降低功率消耗。真正影響能量效率的是「用多少功率換到多少吞吐量」，這也是第 3.2 節把能量效率而非單純發射功率作為第一個目標的理由。

Let $P^{f}(t)$ aggregate all fixed/circuit overhead that is not directly controlled by off-axis angle. With $N^{\mathrm{act}}_{s}(t)=\sum_{v\in\mathcal{V}}z_{s,v}(t)$ the number of active beams on satellite $s$, and with one active beam mapped to one RF chain in this study,

令 $P^{f}(t)$ 彙總所有不直接由偏軸角控制的 fixed／circuit overhead。令 $N^{\mathrm{act}}_{s}(t)=\sum_{v\in\mathcal{V}}z_{s,v}(t)$ 為衛星 $s$ 的啟用波束數；本研究將一支啟用波束對應到一條射頻鏈，則

$$
P^{f}(t)=\sum_{s\in\mathcal{S}}\left(
N^{\mathrm{act}}_{s}(t)\,P_{\mathrm{cir}}
+\mathbb{1}\!\left\{N^{\mathrm{act}}_{s}(t)>0\right\}P_{\mathrm{BB}}
\right).
\tag{3.16a}
$$

The baseband power is shared by all active beams of that satellite and is therefore counted once per satellite, never twice. The values of $P_{\mathrm{cir}}$ and $P_{\mathrm{BB}}$ are taken from Table II of You et al. \[26\] and are listed in Section 5.1. The one-beam-to-one-RF-chain mapping is this study's own, not a conclusion about satellite architecture from that work, that work also includes local-oscillator and phase-shifter power, which this study does not adopt, so Eq. (3.16a) is a partial payload-power model rather than a complete satellite power model. The total system power is

基頻功率由該衛星的所有啟用波束共用，因此每顆衛星只計一次，不會重複計入。$P_{\mathrm{cir}}$ 與 $P_{\mathrm{BB}}$ 的數值取自 You 等人 Table II \[26\]，列於第 5.1 節。「一支波束對應一條射頻鏈」是本研究的對應設定，不是該文的衛星架構結論；該文另含本振功率與相移器功率，本研究不納入，因此式 (3.16a) 是 partial payload-power model，不是完整的衛星總功率模型。系統總功率為

$$
P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=P^{f}(t)+
\sum_{s^{\prime}\in \mathcal{S}}\sum_{v^{\prime}\in \mathcal{V}}
z_{s^{\prime},v^{\prime}}(t)\,
P^{p}_{s^{\prime},v^{\prime}}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right).
\tag{3.16}
$$

The sum runs over $(s,v)$ rather than over $(u,s,v)$: an active beam has a single amplifier, and its supply-side power is not counted once per user it carries, which is consistent with the $p_{s,v}$ aggregation of Eq. (3.12a). A per-link sum would add a spurious term $\sum_{s,v}(U_{s,v}(t)-1)P^{p}_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ that grows with occupancy and would make the first objective duplicate the work of the third.

此處對 $(s,v)$ 求和而非對 $(u,s,v)$ 求和：一支已啟用的波束只有一個放大器，其電源端功率不隨波束上載有幾位使用者而重複計入，這與式 (3.12a) 的 $p_{s,v}$ 聚合一致。若改為逐鏈路加總，多出的項為 $\sum_{s,v}(U_{s,v}(t)-1)P^{p}_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$，隨佔用人數單調上升，會使第一目標重複承擔第三目標的工作。

Finally, the displayed EE for a fixed link $(u,s,v)$ is

最後，固定鏈路 $(u,s,v)$ 的 EE 顯示量定義為

$$
\eta_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=
\frac{R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)}
{P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)},
\qquad P^{N}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)>0.
\tag{3.17}
$$

The three subscripts fix the numerator's UE-link. The denominator remains shared system power, so $\eta_{u,s,v}$ is a displayed single-link contribution to system EE, not true private-power per-user EE.

這裡的三下標固定分子的 UE-link；分母仍是共同系統功率，因此 $\eta_{u,s,v}$ 是單一 UE-link 對系統 EE 的顯示量／貢獻，不宣稱為 private-power 的 true per-user EE。

The multi-objective deep Q-network (MODQN) baseline used in this study trains one Q-network for each of the three objectives, throughput was originally its first reward term \[2\]. This study defines the first reward as the sum of the selected-link EE contributions, so that transmission volume, beam angle, and power consumption are considered together.

本研究採用的多目標深度 Q 網路（MODQN）基準，以三個 Q 網路分別學習三個目標；其中吞吐量原本是第一個獎勵項 \[2\]。本文將第一個獎勵定義為所選鏈路 EE 貢獻的總和，使模型同時考慮傳輸量、波束角度與功率消耗。

## 3.2 Problem Formulation

This study considers energy efficiency, handover cost, and load balancing jointly. Let $L_w$ be the number of visible satellites included at each step. Using the realized connection $x_{u,s,v}(t)$ as the decision outcome, the long-term objectives are \[2\]

本研究同時考慮能量效率、換手成本與負載平衡。令 $L_w$ 為每個時間步納入決策的可見衛星數。以實際連線 $x_{u,s,v}(t)$ 為決策結果，長期目標可寫為 \[2\]

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

P1 希望在相同耗能下傳送更多資料，P2 減少換手，P3 則使各波束承載的使用者數趨於平均：在總服務人數固定時，平方和的最小值恰為各波束人數相差至多一人的配置。以下分別定義三個目標。

### 3.2.1 Angle-Aware Energy Efficiency

Equations (3.15)–(3.17) define link-side consumption, shared system power, and the displayed EE for a fixed link. The first reward sums the EE contributions of the links selected by each user:

式 (3.15)–(3.17) 已先定義鏈路耗電、共同系統功率與固定鏈路 EE 顯示量。第一個獎勵則把使用者實際選取的鏈路 EE 貢獻相加：

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

$r_{1,u}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)$ 的單位為 bit/J，表示使用者 $u$ 對瞬時系統能量效率的可加貢獻。式 (3.25) 只在共同系統功率為正時成立；未選取的鏈路由 $x_{u,s,v}(t)=0$ 排除。這裡不另建立 user-level SINR 或 user-level throughput 符號。

The off-axis angle therefore enters $G^T$ directly, while the wanted-link numerator in Eq. (3.13) uses $p_{u,s,v}H_{u,s,v}G^T(\theta_{u,s,v},\theta_{3dB})$, Eqs. (3.11)–(3.12) use the segment-start power $p^{0}$ and the previous-step recurrence to determine angle-aware link RF power. The same $p$ also enters the total-interference system state and the power/EE relations in Eqs. (3.15)–(3.17). The physical formula needs neither target-SINR inversion nor a protective power cap.

因此，角度直接進入 $G^T$，而式 (3.13) 的 wanted-link numerator 使用 $p_{u,s,v}H_{u,s,v}G^T(\theta_{u,s,v},\theta_{3dB})$；式 (3.11)–(3.12) 以 segment-start $p^{0}$ 與 previous-step recurrence 決定角度相關鏈路 RF power。同一個 $p$ 也進入總干擾所對應的系統狀態，以及式 (3.15)–(3.17) 的功率與 EE。主公式不需要目標 SINR、需求功率反推或保護性 cap。

### 3.2.2 Handover Cost

Using the serving pair $(\rho_u(t),\delta_u(t))$ defined above, the cost of switching beams within one satellite is $\varphi_1$, while the cost of switching satellites is $\varphi_2$, with $0<\varphi_1<\varphi_2$. The second reward is

沿用上述 $(\rho_u(t),\delta_u(t))$ 表示的服務衛星與波束。同衛星換束的成本為 $\varphi_1$，跨衛星換手的成本為 $\varphi_2$，且 $0<\varphi_1<\varphi_2$。第二個獎勵為

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

因此，維持原連線時不產生成本，同衛星換束次之，跨衛星換手的成本最高。

### 3.2.3 Load Balancing

The third reward is the negative occupancy of the beam the user selected, where that occupancy is the $U_{s,v}(t)$ of Eq. (3.3):

第三個獎勵取使用者所選波束當步服務人數的負值；該人數即式 (3.3) 定義的 $U_{s,v}(t)$：

$$
r_{3,u}(t)=-U_{b_u(t)}(t).
\tag{3.28}
$$

Here $b_u(t)$ is the beam user $u$ selects at that step and $U_{b_u(t)}(t)$ is the number of users that beam serves at that step, from (3.28). A more crowded selected beam gives a smaller reward. This reward is **decomposable per user**: since $\sum_{u\in \mathcal{U}}U_{b_u(t)}(t)=\sum_{s,v}U_{s,v}(t)^2$, the sum over users is exactly the negative of the P3 objective, so each user's reward is an exact decomposition of the global objective rather than one system-level scalar shared by every user.

其中 $b_u(t)$ 為使用者 $u$ 當步所選的波束，$U_{b_u(t)}(t)$ 為該波束當步服務的使用者數（式 (3.3)）。所選波束越擁擠，獎勵越低。此獎勵**逐使用者可分解**：由 $\sum_{u\in \mathcal{U}}U_{b_u(t)}(t)=\sum_{s,v}U_{s,v}(t)^2$，所有使用者的獎勵總和恰為 P3 目標的負值，故每位使用者的獎勵是全域目標的精確分解，不同於舊式以系統層級純量共享給所有使用者的作法。

### 3.2.4 Reward Vector and Evaluation Metric

MODQN retains the three-dimensional reward vector \[2\]:

MODQN 保留三維獎勵向量 \[2\]：

$$
\overrightarrow R_u\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)=\left[r_{1,u}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right),\ r_{2,u}(t),\ r_{3,u}(t)\right].
\tag{3.29}
$$

The three components do not take the same arguments: $r_{1,u}$ depends on the whole set of off-axis angles and beamwidth parameter through $\eta_{u,s,v}$ and $P^{N}$ and therefore carries $\boldsymbol{\theta},\theta_{3dB}$, whereas $r_{2,u}$ is fixed by the change of serving satellite and beam and $r_{3,u}$ by the occupancy alone, so neither involves an angle. The vector carries $\boldsymbol{\theta},\theta_{3dB}$ because its first component does. The generic $r_{j,u}$ and $\bar r_{j,u}$ of Chapter 4 do not spell the arguments out component by component, each component keeps the definition given here.

三個分量的引數不同：$r_{1,u}$ 透過 $\eta_{u,s,v}$ 與 $P^{N}$ 依賴整組偏軸角與波束寬參數，故帶 $\boldsymbol{\theta},\theta_{3dB}$；$r_{2,u}$ 只由服務衛星與波束的變動決定、$r_{3,u}$ 只由佔用人數決定，兩者都不含角度。向量本身因第一個分量而帶 $\boldsymbol{\theta},\theta_{3dB}$。第四章的通式 $r_{j,u}$ 與 $\bar r_{j,u}$ 不逐項分寫引數，各分量沿用此處的定義。

Training uses stepwise rewards. Cross-time total-bits/total-energy evaluation belongs to the experimental procedure in Chapter 5, this section does not introduce a second physical EE symbol. Chapter 5 specifies the evaluation interval, service quality, coverage, and handover metrics separately from the per-step link EE in Eq. (3.17).

訓練使用逐步獎勵；跨時間的總位元／總能量評估屬於第五章的實驗評估程序，不在本節再建立第二個 EE 物理符號。第五章另行說明評估時間範圍、服務品質、覆蓋與換手指標，並將它們與式 (3.17) 的當步鏈路 EE 區分。

MODQN lets each user independently select the feasible beam with the largest weighted Q-value. Users with similar states may concentrate on the same few beams. By Eq. (3.14), users on one beam share its bandwidth, so concentration directly lowers each user's rate and worsens the P3 objective in Eq. (3.24). Chapter 4 addresses this issue through two training-shaping strategies.

MODQN 讓每位使用者各自選取加權 Q 值最高的可行波束。狀態相近的使用者可能共同集中到少數波束；由式 (3.14)，同一波束上的使用者均分頻寬，集中會直接壓低每個人的速率，也使式 (3.24) 的 P3 目標惡化。第四章將以兩種訓練塑形策略處理這個問題。
