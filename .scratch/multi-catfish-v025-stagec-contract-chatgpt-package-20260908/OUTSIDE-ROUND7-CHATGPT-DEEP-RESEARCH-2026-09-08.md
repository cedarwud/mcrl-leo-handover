# Learned coordination 的可證明增益、消融估計目標與部署界線

**V025 stages 6–8 合約的一手文獻審查｜2026-09-08（UTC）**  
對象：LEO 多使用者關聯／換手研究作者與方法審查者。範圍：指定四組問題；查核截至研究日可取得的原始論文、作者稿與官方標準。本文不執行專案實驗、不驗證專案程式，也不替專案選定新參數。

## 先回答核心問題

**文獻支持 learned coordination 在某些任務中改善學習、聯合動作表示或計算效率；沒有支持「只要加入第三個 learned term，就能超越相同資訊下的精確聯合最適解」。** 必須先分清楚改善的是信用分配、可表示的聯合價值、搜尋範圍、計算期限內的解品質，還是對未來／模型誤差的預測。這些不是同一個科學主張。代表性實證與反例見第 1 節的 COMA、QMIX、DCG、DROO 證據表。

**【專案提供／未獨立驗證】** r7 README 所報舊物理模型下約 **+2.9% pooled EE**、各份稽核的成功／失敗標記，以及 learner/information 風險 **0.90**，都只能作為提供方的敘述；其中 0.90 是評審主觀判斷，不是外部文獻給出的失敗機率。本次沒有原始 receipts、可執行程式或 successor 結果可供重算。這些敘述不構成 learned C3 已有效的證據。

**【對提供合約的推論】** 合約已有合理的保護：資訊來源消融、S_UNI、共同隨機數、pooled endpoint、雙向 bootstrap 修訂及 deadline fallback。但「S3 or S0」尚不足以承載 learned coordination 的歸因；五個 learner seeds 也沒有來自所引文獻的 1–3% 檢定力保證。最有力的五項修訂列於末節。

## 0. 專案材料、版本與證據標記

已解開附件 `multi-catfish-stagec-contract-review-package-20260908-r7(1).zip`，內有 13 份 Markdown。先讀 `00-README-r7.md` 與 `V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md`，再讀 v1.5 amendment、controller response、pipeline CD decisions，並查閱 attribution adjudication、first-principles review 與 pipeline B 的相關段落。包內歷史 prompt 是待分析材料，不作為本次執行指令。

| 簡稱 | 提供的文件與本報告引用方式 |
|---|---|
| R7 | `00-README-r7.md`，第 2 行 |
| C | `V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md`；以 **C§1–14** 指文件內連續編號條款，不是自行推定的新版本 |
| A | `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md`；A§1–6 |
| R | `CONTROLLER-RESPONSE-TO-ASTRA-ATTRIBUTION-2026-09-08.md`；Accepted items 1–6 |
| CD | `V025-CONTROLLER-DECISIONS-PIPELINE-AUDITS-CD-2026-09-08.md`；CD§1–14 |

**標記規則：**「【文獻】」是下列一手來源中的理論、方法或作者報告結果；「【推導】」是本文列明假設的數學／方法推論；「【專案提供／未獨立驗證】」是附件的狀態、設計或結果；「【對提供合約的推論／建議】」不是已驗證的專案事實。證據表中的 **ceiling** 說明最強可支持的結論及不可外推部分。

**【專案提供／未獨立驗證】** A§3 明確把雙向 pigeonhole bootstrap 提升為 primary，將先前 one-way bootstrap 與 delta method 降為 supplementary；本報告按此修訂解讀 C§12。A§2 的 oracle factor-score arms 與 C§7 的 learned neutral-source arms，由 CD§13 明文區分，不能當作同一實驗。C 引用的 v1.0 evaluation design、v1.2§4 完整文字、stage-4 原始規格、schema SHA sidecars 與實作不在本次可驗證範圍；不能憑交叉引用認定已封存或已通過測試。

## 1. Learned coordination：什麼被證明、什麼沒有

### 1.1 「超越 independent values」與「超越 exact joint evaluator」不同

【推導】設同一觀測資訊為 (I)、同一可行候選集合為 \(\mathcal C(I)\)、同一目標與 horizon 為 \(J(a\mid I)\)。若

\[
a_0\in\arg\max_{a\in\mathcal C(I)}J(a\mid I),
\]

則任何輸出同一集合內動作的 learned selector 都滿足

\[
J(a_{\rm learned}\mid I)\le J(a_0\mid I).
\]

這是 argmax 的定義，不需要一篇實驗論文來建立；也不是對實際 S0 能力的認證。應分開以下四種比較：

| 比較 | 正結果能說明什麼 | 仍不能說明什麼 |
|---|---|---|
| Learned joint 與 independent greedy／完整 unilateral decoder | 在所固定資訊、預算與任務下，聯合選擇可能有額外價值 | 不能單靠此比較把增益歸因於「學習」 |
| Learned scorer 與完整、準確、同目標的 joint argmax | 同目標下只能逼近或持平；可比較成本 | 不能嚴格提升該 argmax 已最大化的目標 |
| Learned 與 **nominal one-step** exact scorer，以真實閉迴路績效評分 | 可能改善模型誤差、風險或時間規劃 | 這不違反上式：被精確求解的函數不是最終閉迴路目標 |
| Learned proposer／surrogate 與有截止時間的 optimiser | 可能在期限內找到較佳可執行解、減少 fallback | 不能改稱超越無限計算預算的 exact optimum |

**【對提供合約的推論】** C§9 的 bounded catalogue、nominal physics 與 30.08 s deadline，使「exact S0」至少需要三個限定詞：對哪個函數 exact、對哪個集合完整、是否真的在期限內完成。R 的「learned S3 must beat matched S0」只有在宣告比較的是閉迴路真實 endpoint、模型失配或期限內性能時，才是合理的可檢驗目標；若是同一函數、同一候選的完整 exact argmax，應改為品質／成本主張。

【文獻綜合】沒有 universal theorem 要求所有 cooperative policy 在執行時都拿到全體 joint actions。CTDE 可以用集中式訓練訊息得到局部執行策略；DCG 則在執行時交換訊息。【推導】**若任務要求一個 scorer 對不同 joint profile 給出不同 interaction residual，它的輸入必須能區別那些 profile，或包含足以推斷差異的統計量。** 這個受限的可識別性要求，不等於所有 MARL 都必須採取某種中央 head。[COMA](https://arxiv.org/pdf/1705.08926)、[QMIX](https://arxiv.org/pdf/1803.11485)、[DCG](https://arxiv.org/pdf/1910.00091)

### 1.2 信用分配：改變訓練訊號，不自動提供 joint decoder

以下數值是作者報告的 benchmark 指標；**pp 是該指標的百分點，不是 EE 相對百分比**。本報告不把僅在曲線中的結果讀成精確數字。

| 主張／一手來源 | 已核對的資訊與 learner 結構 | 原文消融與實際幅度 | Ceiling |
|---|---|---|---|
| 反事實 baseline 可改善 policy-gradient credit。[Foerster et al., *Counterfactual Multi-Agent Policy Gradients*, AAAI 2018](https://arxiv.org/pdf/1705.08926)，§§3、5–6，Eq.4、Table1；所讀版本含後來的 proof erratum | Central critic 使用全局／聯合資訊；local recurrent actors 執行。固定他人動作，對 focal action 依 policy 邊際化。這是訓練 advantage baseline | 相對 central-QV，保持 actor 架構與訓練方式，最後 1000 evaluation episodes 的 mean win rate：3m **87 vs 83**、5m **81 vs 71**、5w **82 vs 76**、2d_3z **47 vs 39**，即 **+4/+10/+6/+8 pp**；35 trials | 比 IAC 的比較還改變 critic 資訊，不能全部算成 counterfactual credit；四個 StarCraft 任務不證明獨立部署的 additive C3 或 EE 效果 |
| Difference rewards 可從已知或 learned immediate reward 建立。[Castellini et al., *Difference Rewards Policy Gradients*, 2021/2022；expanded author manuscript](https://arxiv.org/pdf/2012.11258)，§§3–5、7 | Dr.Reinforce 用已知 reward；Dr.ReinforceR 學 centralized reward model，再訓練 policies。避免學 bootstrapped Q 不等於取消 policy learning | Fig.2 比 known-reward、learned-reward、COMA、CentralQ、shared-reward PG 等；rover／predator 任務中 learned reward 通常接近已知 reward。§5.3 的 **so_many_baneling** 顯示不普遍優於 COMA。**精確消融差值未取得** | 理論有適用條件；部分可觀測延伸的 baseline 可因未來歷史相依產生偏差，原文不提供一般收斂保證。不是任意 difference target 都對齊最終政策 |
| Shapley credit 可表達 coalition marginal。[Wang et al., *Shapley Q-value: A Local Reward Approach to Solve Global Reward Games*, AAAI 2020](https://arxiv.org/pdf/1907.05707)，§§3–5、Table2 | Coalition critic／採樣估計邊際貢獻，central training、decentralized DDPG actors；必須定義 coalition value 與缺席語義。理論依賴 extended convex-game 等條件 | Coalition samples 1／3／6：更多採樣主要改善收斂速度，最終表現接近。Traffic-junction vs MADDPG：easy **93.26 vs 93.72%**，medium **88.98 vs 87.92%**，hard **87.04 vs 84.21%**，即 **−0.46/+1.06/+2.83 pp** | 表中是跨演算法比較，非只移除 Shapley 的乾淨消融。公平／加總一致的分配，不保證 argmax 正確或元件具有正邊際 |

【推導】Difference reward 與 Shapley 解答「如何定義或分配個別訓練回饋」；它們不直接解答「多個使用者同時採取哪些動作」。例如一個 coalition 的 interaction 總和有正值，並不代表每位使用者各自挑選最大個人 share 之後，形成的 profile 仍是原本那個 coalition。

**【對提供合約的推論】** C§4 的 \(\Psi/2\) 與 Shapley label 可以是合理的監督目標；但 A§2 的「set interaction game」必須逐一指定子集合反事實、固定背景、joint feasibility 與缺席／不變的意義。較大集合的 coalition 子集是否都能合法評分，是待封存的問題。不能用「這是 Shapley」代替這些定義，也不能把公平分配定理當成正 EE 保證。

### 1.3 Value factorisation：共同 team loss 與 greedy 一致性是關鍵差異

| 主張／一手來源 | 資訊與表示方式 | 原文隔離設計與實際結果 | Ceiling |
|---|---|---|---|
| Additive team decomposition。[Sunehag et al., *Value-Decomposition Networks for Cooperative Multi-Agent Learning*, 2017／AAMAS 2018](https://arxiv.org/pdf/1706.05296)，§§3–4、Table1、Figs.4–5 | Local-history utilities 相加，以**同一 team TD loss 聯合訓練**。不是多個獨立回歸目標的 Q 值相加 | 七個雙人任務、10 runs；逐步比較 decomposition、shared weights、role IDs、communication。效果依任務與搭配而異；**曲線的精確差值未取得** | 逐步加元件不是完整 factorial attribution；VDN 的訓練方式不能由「sum of Q」四個字替代 |
| State-conditioned monotonic mixing。[Rashid et al., *QMIX: Monotonic Value Function Factorisation for Deep Multi-Agent Reinforcement Learning*, ICML 2018](https://arxiv.org/pdf/1803.11485)，§§4、6.2、7，Fig.4 | Global state 調整 training mixer；local recurrent utilities 分散執行。Monotonicity 保證局部 greedy 與**所表示**的 joint Q 相容 | QMIX-NS 去 state conditioning；QMIX-Lin 去非線性；VDN-S 加 state bias。20 runs。3m 不需非線性；2s3z／3s5z 比較受益；8m 上 VDN／QMIX 接近。**精確 pp 未取得** | 分開了資訊和 mixing 的部分效果；不證明 monotonic class 可表示任意真實 joint value，亦非所有任務需要 nonlinear mixer |
| 放寬 additive／monotonic 表示限制。[Son et al., *QTRAN: Learning to Factorize with Transformation for Cooperative Multi-Agent Reinforcement Learning*, ICML 2019](https://arxiv.org/pdf/1905.05408)，§§3.1–3.5、4，Table1 | Individual utilities、joint Q、state value，加 TD 與 greedy consistency constraints；QTRAN-alt 加強 counterfactual consistency | 指定 3×3 one-step game、20,000 steps full exploration：QTRAN 選到 payoff **8**；VDN／QMIX greedy 得 **0**。Base 與 alt 都找到 optimum，alt 更能分離次佳動作 | 是特定 payoff／訓練分布的表示與擬合診斷；不是勝過精確搜尋，更不是可移植成 EE 幅度 |
| IGM-complete advantage factorisation。[Wang et al., *QPLEX: Duplex Dueling Multi-Agent Q-Learning*, ICLR 2021](https://arxiv.org/html/2008.01062v3)，§3、App.E、H–J | Duplex dueling／advantage IGM；completeness 在其函數類與近似能力假設內 | App.E：去多頭 attention 仍近似同等 SMAC；加大參數量的 QMIX 仍較差。App.H：更多 heads 無明顯收益。App.J：較長 exploration 下 **QMIX 與 QPLEX 都能解 predator-prey**。**精確 SMAC 差值未取得** | 表示能力、最佳化與探索失敗不可混為一談；attention 並非各任務必要條件 |
| Weighting 與 unrestricted critic 的組合。[Rashid et al., *Weighted QMIX: Expanding Monotonic Value Function Factorisation for Deep Multi-Agent Reinforcement Learning*, NeurIPS 2020](https://papers.nips.cc/paper_files/paper/2020/file/73a427badebe0e32caa2e1fc7530b7f3-Supplemental.pdf)，§§3–6、App.D–E | Monotonic mixer 之外增加 unrestricted joint critic，重新加權 fitting；理想化 theorem 與 deep 實作須區分 | 只留 weighting 或只留 unrestricted critic，在所設 predator-prey 都失敗；兩者合用成功。Weighting-only 在 5m_vs_6m 較差、3s5z 無改善；corridor 有負結果。**幅度僅在圖中，未量化** | 增加表示能力與加權不能保證普遍提升；QPLEX 的後續 exploration 結果限定了其架構必要性的解讀 |

【文獻綜合】上述工作最直接支持的是「要把 joint representation、訓練 objective、greedy consistency 與 exploration 一起界定」。它們不支持從某個 head 的 regression accuracy 推出 deployed policy 的增益。[VDN](https://arxiv.org/pdf/1706.05296)、[QTRAN](https://arxiv.org/pdf/1905.05408)

**【對提供合約的推論】** C§6 已選擇 pairwise、zero-bootstrap deterministic regression。這是一個可以檢驗的 learner，但不是 VDN／QMIX／QTRAN／QPLEX 的 Bellman factorisation，也不是 COMA 的 policy gradient。引用這些工作的動機與對照設計是合理的；繼承其收斂、IGM 或「必定學會協調」保證則不合理。資料中含 keyed fading 也不必然非法：若不可在執行時觀測，應說明是在學條件期望、風險分位或其他統計量，而非宣稱相同可見 state 唯一決定每個 realized label。

### 1.4 Coordination graphs、max-plus 與 learned proposer＋optimiser

| 主張／一手來源 | 資訊與結構 | 可隔離的比較、幅度 | Ceiling |
|---|---|---|---|
| Explicit pairwise payoffs 能補足 additive utilities。[Böhmer et al., *Deep Coordination Graphs*, ICML 2020](https://arxiv.org/pdf/1910.00091)，§§2–3、5.1、5.4 | Utility＋pairwise payoff；參與 agent 的 histories、shared recurrent parameters、low-rank payoff；**執行時** max-plus messages | 移除 edges 得 VDN。Punishment 0 時差異小；−2 時 IQL／VDN／QMIX 得 **0 return**，fully connected DCG 解出 optimum **40**，8 seeds 都成功。Sparse graphs 有成有敗；SMAC 大部分 maps 與 VDN 接近 | Max-plus 的一般收斂保證限 acyclic graphs；loopy graph 不等於 exact argmax。成功同時涉及資訊傳遞與 interaction 表示；非每個網路都有相同拓樸收益 |
| 學候選可攤提 discrete search 成本。[Huang, Bi & Zhang, *Deep Reinforcement Learning for Online Computation Offloading in Wireless Powered Mobile-Edge Computing Networks*（DROO）, IEEE TMC 2020](https://arxiv.org/pdf/1808.01977)，§4、§§5.3–5.4、Table2 | Channel gains → DNN relaxed binary output → (K) quantized candidates → 每個候選的 conditional continuous-resource optimisation → 以最佳候選回訓 | 30 users：adaptive DROO **0.059 s**、fixed-(K) **0.31 s**、coordinate descent **3.8 s**、linear relaxation **0.81 s**；含平均 online training。計算率接近 CD，normalized intervals 多在 0.99 以上 | CD 是 near-optimal comparator，不是已認證 global oracle。Adaptive-(K) 比較較直接隔離搜尋工作量；未見 matched random/fixed proposer 消融能把全部收益歸為 learned coordination |
| LEO 兩時間尺度協作具有直接先例。[Cao et al., *Collaborative Deep Reinforcement Learning for Resource Optimization in Non-Terrestrial Networks*, IEEE PIMRC 2023；author manuscript 更新 2024](https://arxiv.org/pdf/2402.04056)，Algorithm1、§IV、Figs.2–3、TableII | UE 提供 reference trajectory；satellite 有限步 rollout；分別控制 beam/resource decisions，UE 使用兩 agent 的 sum advantage | Full vs independent vs without sum advantage：Fig.2 報告前者較佳，**精確差值未取得**。TableII 等權 composite、demand 10 時：proposed **0.1056** vs BFS-greedy **0.2794**，越低越好 | Composite 包含滿足誤差、RB 與計算成本；原文稱 BFS-greedy 達 receiving-rate upper bound。不能把 composite 優勢改寫為 EE 或同目標 exact optimum 優勢；也不是多 UE C3 的直接驗證 |

### 1.5 最能隔離「learned coordination term」的比較

以下是**【對提供合約的建議】**，取法於上表消融，但不是任何單篇論文已完整執行的設計：

| 要辨認的作用 | 保持共同的條件 | 關鍵比較 | 應報告的 endpoint |
|---|---|---|---|
| 聯合搜尋超過 unilateral 的價值 | Current delivered information、服務約束、預算、初始 proposal、合法動作 | S_UNI vs exact joint S0；同時記錄 iterated unilateral 是否真到 local optimum 或被期限截斷 | 完整閉迴路 pooled EE／QoS；共同 anchor 的 nonadditivity 作機制補充 |
| Learned residual scorer 的價值 | 相同 joint examples、catalogue、proposer、guard、目標與 horizon | Learned additive predictor vs interaction-capable predictor；資訊與容量控制 | 候選 ranking、對 S0 的 objective regret，以及部署後 B／E／QoS |
| Learned proposer 的價值 | 同一 exact scorer、同候選評分次數或 wall-clock 預算 | Learned vs 預先固定的 heuristic／random proposer | 最佳可行候選品質與期限內結果；不能只報 proposer accuracy |
| Surrogate 的計算效益 | 相同可取得資訊與候選、完整 timing boundary | S3 vs S0：分開 unlimited／deadline-enforced | 品質差、runtime 分布、miss／fallback 比例；若只加速，就以加速為主張 |
| 訓練來源的資訊效果 | 同架構、批次規則、update budget、初始化配對 | Informative-source vs 預先定義的 neutral-source retraining | 訓練程序的平均部署績效差；另列 checkpoint knockout |

**【對提供合約的推論】** A§2 的 \(C1+C3\) 加總恆等式能檢查會計一致性；它不是 causal attribution。Positive joint-vs-unilateral gap 可能來自一次綁定多個各自有利的改動；nonzero interaction 也可能是負交互作用。若主張「非加性協調帶來增益」，還需要 interaction 的符號、它是否改變候選排序，以及在同 anchor 的比較。這些只解釋當下 score，不能無條件分解原閉迴路 EE 增益。

## 2. Retrained ablation、checkpoint knockout 與「歸因」

### 2.1 先寫 estimand，再決定實驗名稱

【推導】令 (T_z(D,s)) 表示介入設定 (z) 下，用資料 (D) 與 learner seed (s) 得到的完整 trained system；令

\[
\rho(\Pi)=\frac{\mathbb E[B(\Pi,W)]}{\mathbb E[E(\Pi,W)]},
\]

其中期望涵蓋已宣告的訓練隨機性與 evaluation-world population。以下比較刻意不同：

| 介入 | 改變了什麼 | 可以說的結論 | 不可替代的結論 |
|---|---|---|---|
| Retrained architecture ablation | 從訓練起移除 X；其餘部分可重新學習 | X 在指定訓練／調參／預算制度內是否改善演算法 | 不是已訓練 FULL 對 X 的依賴度 |
| Retrained neutral-source ablation | 保留架構，X 的訓練來源換成明定中性來源 | Informative vs neutral training source 的效果 | 不是移除 deployed head，也不是 X 架構不可取代 |
| Checkpoint knockout | 固定 FULL checkpoint，停用指定訊號／路徑 | 這組權重與 decoder 對該介入的依賴或敏感度 | 不是少了 X 的系統重新訓練後最佳能做到什麼 |
| Oracle factor-score ablation | 在固定模型與候選中刪除解析 score 項 | 指定 scoring rule 的決策敏感度／理想 headroom | 不是 learned component 的訓練貢獻 |

例如 retraining contrast 是 \(\rho(T_{\rm full})/\rho(T_{-X})-1\)；knockout 則比較 \(\rho(T_{\rm full})\) 與 \(\rho(K_X(T_{\rm full}))\)。兩者的權重分布和適應機會不同；通常沒有相等定理。

### 2.2 方法學證據表

| 主張 | 一手來源與位置 | 精確支持的陳述／結果 | Ceiling |
|---|---|---|---|
| 測試時刪除造成的損失可能混入輸入失配 | [Hooker et al., *A Benchmark for Interpretability Methods in Deep Neural Networks*, NeurIPS 2019](https://arxiv.org/html/1806.10758v3)，§3、§4.3.1、Fig.3 | ImageNet 隨機移除 90% pixels：未 retrain 約 **0.5% accuracy**；retrain 後 **63.53%**，原 baseline **76.68%**。ROAR 明定從隨機初始化重訓，修改 train／test 同時進行 | 直接對象是 feature-importance evaluation，不是 MARL head；可支持兩種介入不可混用，不能據此宣布所有 checkpoint knockout 都無效 |
| Ablation damage 可由後續訓練補償，且元件有交互作用 | [Meyes et al., *Ablation Studies in Artificial Neural Networks*, 2019 preprint](https://arxiv.org/pdf/1901.08644)，§§3.3、4.2、4.4 | VGG-19 指定層去 25% filters 後，多數 top-5 損失在一個 recovery epoch 回到距原值 **不足 1 pp**；雙 unit ablation 效果可超過兩個單獨效果之和 | Recovery fine-tuning 不是從頭 retraining；該結果證明介入與適應制度重要，不給 X 的普遍歸因分數 |
| Mechanism／mediation 比總效果多要求識別條件 | [Imai, Keele & Yamamoto, *Identification, Inference and Sensitivity Analysis for Causal Mediation Effects*, Statistical Science 2010](https://arxiv.org/pdf/1011.1079)，§3，Eq.1，§5；明列早期基礎文獻 | 定義含 mediator potential outcomes 的 ACME，並在特定 sequential ignorability 下識別；只隨機化 treatment 不自動解決 mediator confounding | 是一般因果框架，不是命令所有程式消融都套用同一套觀察資料估計法。可執行的軟體介入仍要清楚定義干預對象與 downstream 適應 |
| Referee 有權要求主張、訓練制度、變異來源清楚 | [NeurIPS 官方 Paper Checklist](https://neurips.cc/public/guides/PaperChecklist)，items 1–2、6–8；查閱 2026-09-08 | 要求主張與證據範圍一致，列 training details、hyperparameter selection、uncertainty 的來源／算法，以及 compute resources | 官方指引**沒有**規定所有論文必須同時做 retraining 與 knockout；不能把本報告的報告建議冒充通用審稿硬規則 |

【文獻綜合／推導】本次沒有查得能把 **“ablation is not attribution”** 當作特定定理名稱或統一審稿規範的一手來源。本文以此表達一個有範圍的警語：**單一消融可以測定所指定干預的因果效果；它不自動給出與干預基準、其他元件狀態無關的獨有貢獻，更不自動辨認物理機制。** 不應反過來說「ablation 永遠不能提供因果證據」。上表的 redundant representations、recovery 與 mediation 定義說明了這個界線。

### 2.3 合約應如何報告

**【專案提供／未獨立驗證】** C§7 明定所有 heads 保留及部署，以 neutral-source substitution 建立 DROP；A§6 指定 retrained ablations 為科學主張，knockouts 分開報告。**【對提供合約的建議】** 保留這個設計，但主文名稱寫成「informative-source training effect」，並為每個 contrast 列：干預位置、neutral label／batch 的生成、保留的計算路徑、初始化與 optimizer 規則、budget、checkpoint selection、評估 population。

**【對提供合約的推論】** 若 DROP_C3 仍有 exact S0 在 selection 階段提供完整 interaction，該 arm 不再測試移除 coordination；若只是 neutral-trained C3 留在系統，測到的是來源資訊效果。兩者都可能是有意義的實驗，但標題不能互換。同樣，「固定所有 hyperparameters」衡量固定 recipe 下的 marginal；「每個 arm 允許相同調參預算」衡量重新適配後的演算法表現。必須預先選定，不能依結果選較有利者。

**【推導】** FULL−DROP 的正值是「其餘元件開啟時」的條件效果，不是 across-all-configurations 的 average main effect。除非額外指定 factorial／coalition allocation，三個 FULL−DROP 不必加總成 FULL−ALL_NEUTRAL；即使採 Shapley 加總，也仍是對指定 coalition game 的分配，不是自然界唯一的機制比例。

## 3. 少量 trained models：seed、date、world 與 ratio-of-sums

### 3.1 文獻沒有給出偵測 1–3% EE 的通用 seeds 數

| 主張／一手來源 | 實際支持的內容 | 對 1–3% 與五 seeds 的 ceiling |
|---|---|---|
| [Henderson et al., *Deep Reinforcement Learning that Matters*, AAAI 2018](https://arxiv.org/pdf/1709.06560)，random-seed discussion、結論、App.Figs.24–25 | 同一演算法／設定取不同五-run 子集，可以出現很不同的 learning curves；應報獨立 runs、實作與統計不確定性 | 五是被展示風險的樣本規模，不是足夠性的背書；没有 1–3% EE 專用 recommendation |
| [Colas et al., *How Many Random Seeds? Statistical Power Analysis in Deep Reinforcement Learning Experiments*, 2018](https://arxiv.org/pdf/1806.08295)，§§4–5 | Power 由 effect、variance、顯著水準、目標 power 共同決定。Worked example：SD 1341／990、difference 1382，N=5 power **0.49**，N=10 **0.81**；小 pilot 的 SD 本身不穩 | Example 的 difference 相對其 baseline 3523 約 **39.2%**（本文算術），不是 1–3%。不能直接套入 paired crossed EE ratio |
| [Colas et al., *A Hitchhiker’s Guide to Statistical Comparisons of Reinforcement Learning Algorithms*, 2019；v2 2022](https://arxiv.org/pdf/1904.06979)，§§2.2、3.1、4–5 | “Relative effect size” 定義為 **mean difference／pooled SD**；研究設定明確為 unpaired。Half-Cheetah SAC／TD3 標準化 effect 約 0.93，約 10–15 runs 得 80% power；其 ordinary percentile-bootstrap comparison 小樣本校準不佳 | 「relative」不是相對百分比。文中對少於 50 的 bootstrap 警告針對所測方法，不是所有 bootstrap 的普遍門檻，也不替 crossed five-seed 方法提供保證 |
| [Agarwal et al., *Deep Reinforcement Learning at the Edge of the Statistical Precipice*, NeurIPS 2021](https://arxiv.org/html/2108.13264v4)，§§2–4.1、App.A.3 | Within-task 獨立重抽 training runs、再聚合 tasks。Atari aggregate median／IQM percentile CI 在 N=10 有良好 coverage；median 偵測人工 25%／10% lift 的案例需 25／100 runs | 同一五模型在許多日期重用，不等於每 task 各自訓練。結果不保證五 seeds 偵測 1–3%；也不應為縮短 CI 把物理 pooled EE 換成 IQM |
| [Owen & Eckles, *Bootstrapping Data Arrays of Arbitrary Order*, AOAS 2012](https://arxiv.org/pdf/1106.2125)，§§1–4、7、9；早期基礎文獻 | Crossed factors 分別抽權重，observation 用其乘積；忽略共享因素的 IID 重抽可能嚴重低估 variance。一定條件下 mildly conservative；§9 討論 smooth functions of means | 不是「只有五個 seed levels 仍保證 95% coverage」。Variance 的保守性不等於任意小樣本 percentile CI 都保守；仍需 exchangeability／regularity |
| [Owen, *The Pigeonhole Bootstrap*, AOAS 2007](https://arxiv.org/pdf/0712.1111)；早期基礎文獻 | 獨立重抽 rows／columns，處理 unbalanced、heteroscedastic crossed effects | 不證明 TLE dates 一定可交換，也不規定 universal seeds count |
| [Deng, Knoblich & Lu, *Applying the Delta Method in Metric Analytics: A Practical Guide with Novel Ideas*, 2018](https://arxiv.org/pdf/1803.06336)，§§2–3、5.2 | Ratio linearization 必須保留 numerator／denominator covariance；overlapping／paired ratios 也需保留相關性 | 支持 delta supplement，不能修補錯誤 sampling units、near-zero denominator 或五 seeds 的有限樣本問題 |

**直接答案：這些作品沒有推薦一個能普遍偵測 1%、2%、3% EE 改善的 seeds 數。** 引用 5、10、20、50 或 100 都必須連同其 effect 定義、variance、metric 與 sampling design。缺少專案的 paired trained-model variance 時，給精確所需 seed 數會是假精確。

### 3.2 為何 evaluation worlds 不能取代 learner seeds

【推導】對 balanced design 的線性化 paired contrast，可用一個說明性的 crossed random-effects 表達式。假設各 random effects 為零均值、有限變異，且彼此及各層級間獨立；否則下式需加入 covariance terms：

\[
Z_{ds}=\mu+A_d+C_s+I_{ds},\qquad
\operatorname{Var}(\bar Z)=
\frac{\sigma_A^2}{D}+\frac{\sigma_C^2}{S}+\frac{\sigma_I^2}{DS}.
\]

這不是已估出的專案 variance model；它只說明：增加日期／worlds 不會消掉 \(\sigma_C^2/S\) 的 trained-model uncertainty。對不平衡 panel、不同 episode 權重、共同世界及 ratio endpoint，需要使用相應線性化和 covariance，而不是直接把所有 steps 當獨立樣本。[Owen–Eckles](https://arxiv.org/pdf/1106.2125)、[Deng et al.](https://arxiv.org/pdf/1803.06336)

**【專案提供／未獨立驗證】** C§8、11 的設計是五 learner seeds、約 600 worlds／約 161 dates，且跨 arms 配對。**【對提供合約的推論】** 應區分至少三個 population：固定這五 checkpoints 的 world 泛化、重新訓練可重現性，以及超出目前 archive／日期範圍的時間泛化。五 seeds 的觀測可估計 contrast，卻不能直接承諾窄 CI 或 adequate power。共同初始化可能降低 paired variance，但效果需從 covariance 說明，不能只憑 CRN 名稱保證。

### 3.3 合適的 paired ratio-of-sums 與重抽方式

【推導／建議】以完整 episode 的 (B_{adsw},E_{adsw}) 表示 arm、date、learner seed、world 的原始 endpoint，並預先定義 population 權重 (q_{dsw})：

\[
\widehat\eta_a=\frac{\sum_{d,s,w}q_{dsw}B_{adsw}}
{\sum_{d,s,w}q_{dsw}E_{adsw}},\qquad
r_j=\frac{\widehat\eta_F}{\widehat\eta_{D_j}}-1.
\]

Pigeonhole draw (b) 分別抽 date multiplicities (U_d^{(b)}) 與 seed multiplicities (V_s^{(b)})，所有 arms 共用：

\[
\widehat\eta_a^{(b)}=
\frac{\sum U_d^{(b)}V_s^{(b)}q_{dsw}B_{adsw}}
{\sum U_d^{(b)}V_s^{(b)}q_{dsw}E_{adsw}},\qquad
r_j^{(b)}=\frac{\widehat\eta_F^{(b)}}{\widehat\eta_{D_j}^{(b)}}-1.
\]

這是把上述 bootstrap 與 ratio 文獻應用至本 endpoint 的明示推導；不是某篇論文原封不動的 LEO 規則。若推論還包含「同日期的新 worlds」，需另外說清楚 world 層的 sampling／共享結構；同一世界在各 seed 與 arm 的結果不能各自任意拆散。

**【對提供合約的建議】** A§3 的兩向做法應寫回 C§11–12，並用同一個公式封存 primary endpoint。`cluster = date × seed` 不足以表示兩向相依：將 date–seed cells 當 IID clusters 抽樣，仍會丟失同一 date 或同一 trained model 的關係。日期本身的跨日相關是否可忽略，也需要列為假設；兩向 bootstrap 不會自動處理時間自相關。

【推導】`mean(B/E)`、`mean_seed(ΣB/ΣE)` 和 `ΣB/ΣE` 是不同估計目標。也要區分以下分母條件：若 (B=0,E>0)，EE **定義為 0**；只有 (E=0) 才使該 arm 的比值未定義。即使 arm EE 有定義，若 comparator EE 為 0，**相對增益**仍可能未定義。

**【專案提供／未獨立驗證】** CD§3 將「zero-bit or all-dark arms」一概寫成 ratio undefined。**【對提供合約的建議】** 把上述兩類零分母情況分開，不要把所有 zero-bit draws 刪掉；若刪除失敗 draws，會改變所報 estimand。

### 3.4 +0.5 pp、檢定力與 conjunction

**【專案提供／未獨立驗證】** C§12 寫「δ = +0.5 pp lower-bound rule per FULL−DROP」，但未在該條明示 normalized formula。**【對提供合約的建議】** 若意圖是相對 EE 提升，應明訂 (r_j=\eta_F/\eta_{D_j}-1) 與門檻 0.005 的對應；這是澄清提供的門檻，不是替專案推薦新數字。若原意是相對共同 BASE 的 normalized scores 差，應另寫公式；兩者不能混用。

【推導】門檻為 (delta>0) 時，檢定力取決於真效果距門檻的 **excess**，不是只取真效果距 0。對 log-relative contrast，差距為 \(\log(1+r_{\rm true})-\log(1+\delta)\)。在簡化為獨立訓練對的常態近似下，所需對數與 paired variance 成正比、與這個差距平方成反比；這不是完整 crossed-design power 公式，五 seeds 的 SD 估計仍很不穩。本報告不拿未量測的 SD 代入假裝得到確定 seeds 數。[Colas 2018](https://arxiv.org/pdf/1806.08295)

【推導】對事前固定的 conjunction \(\bigcap_j\{r_j>\delta_j\}\)，null 為 \(\bigcup_j\{r_j\le\delta_j\}\)。若每個 elementary test 都控制在 level (alpha)，要求**全部**通過的 overall type-I error 不超過 (alpha)，不需要各 contrast 獨立。理由是任一 true elementary null 被錯拒的機率最多 (alpha)，全部錯通過的事件是其子集。

**【對提供合約的推論】** C§12 的 IUT 邏輯可以成立，但不保證各小樣本 test 已校準，不給所有 CI simultaneous coverage，也不允許挑成功的單一元件另作未調整的獨立宣稱。PHYSICS-GO 或其他資料選擇之後的 conditional inference，亦需清楚定義。完整 v1.2§4 未在包內核對；本段提供數學論證，**不冒稱已核實該條的完整統計效力**。

## 4. LEO joint evaluator 的部署能力與時間預算

### 4.1 「可得到 geometry」離「exact counterfactual model」還有距離

| 要查核的資訊／主張 | 官方一手來源與位置 | 精確支持的範圍 | Ceiling |
|---|---|---|---|
| Ephemeris、epoch 與 CHO 準備資訊 | [3GPP TS38.300 v18.5.0，ETSI 2025-04](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/18.05.00_60/ts_138300v180500p.pdf)，§§16.14.2.2、16.14.3、16.14.7；§9.2.3.4 | O&M 向 gNB 提供 ephemeris／epoch／gateway locations；SIB19 有 serving、可選 neighbouring ephemeris；time/location CHO 與預備 target configurations 有規範 | 不等於所有 UE 的精確位置與 interference 都即時可知，更不是每個 counterfactual profile 的精確 PA 能耗或鄰居 learned proposal |
| Ground 與 onboard controller 不同 | [3GPP TS38.300 v19.1.0，ETSI 2026-02](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/19.01.00_60/ts_138300v190100p.pdf)，§16.14.1、Figs.16.14.1-1/2 | Transparent payload 轉送 radio protocol；regenerative payload 可承載 gNB 並終結 Uu、NG、Xn；規格也支援相應 inter-satellite connectivity | 是標準架構能力，不是某營運商已實作、onboard compute 已足夠或 signaling 免費的證據 |
| Load／容量／interference 協調訊息可交換，但有語義和延遲 | [3GPP TS38.423 v18.5.0，ETSI 2025-04](https://www.etsi.org/deliver/etsi_ts/138400_138499/138423/18.05.00_60/ts_138423v180500p.pdf)，§§8.4.10–11、9.1.3.18–21、9.1.3.26、9.2.2.40 | XnAP 有 PRB use、available capacity、active UE／RRC reports。Reporting periodicity 列 **500／1000／2000／5000／10000 ms**，支援時也作 averaging window；另有 requested predictions、intended TDD configuration | 不是 guaranteed instantaneous global occupancy。TDD intention 不是任意 future association proposals；也不代表每個私有 LEO 網路用相同介面／週期 |
| 控制層級有不同時間尺度 | [O-RAN Architecture Description，ETSI TS103982 v8.0.0，2024-01](https://www.etsi.org/deliver/etsi_ts/103900_103999/103982/08.00.00_60/ts_103982v080000p.pdf)，§§6.3.1.2.3、6.3.2 | Near-RT RIC 為約 **10 ms–1 s**；Non-RT RIC 智慧 RRM 為 **>1 s**；受 E2 nodes 所暴露功能限制 | 不是 LEO handover solver 的 universal deadline。不能用 >1 s 推論任意 30 s decision 都符合實際換手需求 |

**【對提供合約的建議】** C§2–5、9 的 manifest 對每個欄位分清楚：在哪裡量到／算到、量測或 ephemeris 的時間、何時收到、平均窗口、可用對象、缺失處理、模型誤差及跨節點傳輸。`current-profile joint physics features` 是需要計算的反事實，不能只因由 telemetry 推導就視為免費。相同資訊比較必須給 S0、S3、S_UNI 相同的取得時刻與 query 權限。

**【專案提供／未獨立驗證】** A§5 保留 nearest-epoch TLE，允許 future epochs，並自稱 non-causal benchmark convention。**【對提供合約的推論】** 這可以是對稱的 retrospective benchmark，卻不能直接支持「僅用決策當時可取得資訊」的部署主張。應區分「未來位置的合法預測」與「事後才產生的軌道資料」；前者可部署，後者不能藉共享給所有 arms 就變成即時可取得。

### 4.2 文獻中的秒／毫秒究竟代表什麼

| 一手來源 | 已核對數值／條件 | 這個數值的性質 | Ceiling |
|---|---|---|---|
| [Zheng et al., *Joint Beam Scheduling and Power Optimization for Beam Hopping LEO Satellite Systems*, 2023 author manuscript](https://arxiv.org/pdf/2312.01292)，§II、Tables1–2、§IV.3 | BH slot **0.5 ms**；BH cycle **20 ms**；geometry update **200 ms**；模型由 signaling beam 蒐集接入／CSI | **模擬控制與更新尺度**。複雜度比較未計共同 power-optimisation 成本 | 沒有證明 solver 每次 20 ms 內完成，也沒有全流程 latency 或 deadline-miss distribution |
| [Hozayen et al., *A Graph-Based Customizable Handover Framework for LEO Satellite Networks*, Globecom Workshops 2022](https://arxiv.org/pdf/2211.07872)，§III、Fig.4 | 例示 **30 min** horizon、**300 s** segments；**0.5 s** 來自 1.8×10⁹ operations／3.6 GHz，假設一 cycle 一 operation | **Operation-count 算術估算** | 不能引用為 measured runtime 或 onboard hardware 驗證；segment 也不是實測可用搜索時間 |
| [Cao et al., LEO collaborative DRL, PIMRC 2023](https://arxiv.org/pdf/2402.04056)，§I | Satellite control cycle 為 hundreds of milliseconds 層級，UE 為 milliseconds 層級 | **架構設計尺度**，以兩時間尺度減少 satellite compute | 未取得 end-to-end 實測 timing 數值；參考軌跡傳送是額外資訊路徑 |
| [Yang et al., *Tyche: A Hybrid Computation Framework of Illumination Pattern for Satellite Beam Hopping*, 2025 preprint](https://arxiv.org/pdf/2512.09312)，§§II–III、VI.D、TableIII | **37 cells：greedy 0.063 ms／MCTS 12.661 s；127 cells：0.281 ms／905.615 s**。模擬 slots **100 ms** | 作者報告的 **pattern computation time**；cache hit 查表、miss 先用 greedy，背景 MCTS 補 cache | 是 **GEO** 及 preprint，不是 operational LEO worst-case 保證；provisional greedy/cache 機制也不完全等於 optimizer timeout 後切 BASE |

**沒有從這批可核對來源得到 universal LEO handover deadline，也沒有得到能背書 30.08 s 的實測部署結果。** 上表同時涵蓋模擬尺度、算術估算與 algorithm runtime，不能混成一個「文獻認可的延遲範圍」。

### 4.3 Fallback 的先例與 claim ceiling

【文獻】Tyche 是直接 satellite precedent：昂貴求解未提供可用 cache 時，先由簡單 online algorithm 提供計畫。它支持「持續提供基準決策」的工程模式，但不證明任意 baseline 安全或 EE 不下降。[Tyche §III](https://arxiv.org/pdf/2512.09312)

【文獻】另一個更正式但**非 NTN**的先例是 Wabersich & Zeilinger 的 predictive safety filter：使用模型檢查 proposed input；完整規劃不可行時，沿已知可行的 shrinking-horizon backup 走向 terminal safe controller。保障依賴模型與可行性假設，並非給一個 fallback 名稱就成立。[*A Predictive Safety Filter for Learning-Based Control of Constrained Nonlinear Dynamical Systems*, Automatica 2021，§§4.1–4.2、Algorithms1–2](https://arxiv.org/pdf/1812.05506)

**【專案提供／未獨立驗證】** C§9 規定 30.08 s deadline 與 BASE-proposal fallback；CD§12 的計時包含 proposal、forecast、catalogue、selection、validation、fallback。**【對提供合約的建議】** 保留此範圍，再明列觀測取得、跨節點傳送及 command delivery 是否在內。分別記 observation epoch、decision cadence、最晚 command issue、action-effective time；若讓 optimizer 用盡全部期間才開始 fallback／傳送，仍可能 miss 真正截止點。

**【對提供合約的建議】** Fallback 在實際生效時刻必須仍是 jointly legal profile；處理 stale／missing input、solver failure、timeout 及 BASE 本身不可行。所有 fallback 產生的 B、E、QoS 都計入 primary endpoint，同報 miss fraction 與 latency 分布。這是本報告依上述架構的工程推論，不是標準已認證專案 fallback 正確。

## 5. 逐條對照合約：支持／矛盾／未涵蓋

本表**每一個專案欄位皆為【專案提供／未獨立驗證】**；判讀欄為**【對提供合約的文獻映射／推論】**。「支持」表示方向有一手依據，不代表已實作；「矛盾」只針對表列解讀；「未涵蓋」不是反證。

| 提供條款／設計 | 判讀 | 支持、矛盾或缺口；主要依據 |
|---|---|---|
| C§1：production builder、TRAIN-only、lineage | **支持原則；實作未驗證** | Reproducible data/training specification 有支持；builder、digest 與 TRAIN-only 是否真的成立，文獻無從判定。[NeurIPS checklist](https://neurips.cc/public/guides/PaperChecklist) |
| C§2：Q1 新 schema，歷史 tail、missing_incumbent | **部分支持／未涵蓋具體欄位** | History、global/local information 差異有先例；沒有文獻驗證此欄位集充分。v1 的 exact schema 不在本報告可驗證範圍。[COMA](https://arxiv.org/pdf/1705.08926) |
| C§3：C2 previous committed background excluding focal | **支持明定語義；未涵蓋最適性** | Timestamps／report averages 有實際意義；「前一已提交集合」是特定反事實基準，標準不認證它等於當前 joint proposal。[XnAP](https://www.etsi.org/deliver/etsi_ts/138400_138499/138423/18.05.00_60/ts_138423v180500p.pdf) |
| C§4：C1／C2 labels；interaction-only C3／Shapley | **部分支持** | Credit allocation 有先例；exact EE target、forecast penalties、κ 與 coalition semantics 都需自證。Shapley fairness 不推出 policy gain。[SQDDPG](https://arxiv.org/pdf/1907.05707) |
| C§5：dependency allowlist、golden fixture | **支持資訊界線；未涵蓋部署實現** | 分開 training-only randomness 與 execution observations。Fixture 可檢查資料流，但不能替代 telemetry availability／模型正確性。[QMIX](https://arxiv.org/pdf/1803.11485)、[TS38.300](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/18.05.00_60/ts_138300v180500p.pdf) |
| C§6：pairwise zero-bootstrap regression、100-epoch checkpoints | **未涵蓋成功保證** | 可作獨立方法；若套用 COMA／factorisation 的 theorem 則不成立。100 epochs 是專案工程選擇，無通用文獻背書。[Dr.Reinforce](https://arxiv.org/pdf/2012.11258)、[QTRAN](https://arxiv.org/pdf/1905.05408) |
| C§7：neutral-source DROP、all heads retained | **支持窄 estimand** | 支持明示 informative vs neutral training effect；與 architectural removal／checkpoint reliance 不相同。[ROAR](https://arxiv.org/html/1806.10758v3)、[Meyes](https://arxiv.org/pdf/1901.08644) |
| C§8：五 learner seeds，CRN、seed separation | **支持 pairing／分層；未涵蓋數量充分性** | 不能將五 seeds 或大量 worlds 說成有文獻認證的 1–3% power。[Colas 2018](https://arxiv.org/pdf/1806.08295)、[Henderson](https://arxiv.org/pdf/1709.06560) |
| C§9：Q1+Q2、S3 or S0、S_UNI、deadline／fallback | **部分支持；需拆開主張** | Joint reasoning／hybrid 有先例；若聲稱 learned gain，S3 與 S0 不宜只是二擇一。S_UNI 的迭代範圍與 timeout 状態要封存。[DCG](https://arxiv.org/pdf/1910.00091)、[DROO](https://arxiv.org/pdf/1808.01977) |
| C§10：jointly feasible commit | **支持** | Local argmax consistency 只在適用表示／可行集合條件下成立；各自 legal 不保證 profile legal。[QMIX](https://arxiv.org/pdf/1803.11485)；一般聯合約束推導 |
| C§11：約600 worlds／161 dates×5 seeds；no TEST | **支持明定 panel；反對 cell-IID 解讀** | 日期與模型是 crossed factors；no TEST 名稱不等於必然 leakage，也不證明 holdout。A§4 的 role-wise disjointness 必須實際成立。[Owen–Eckles](https://arxiv.org/pdf/1106.2125) |
| C§12：ΣB／ΣE、+0.5 pp、cluster CI／IUT | **支持 ratio；需依 A§3 改寫** | 保留完整 covariance；明定相對效果、門檻與 denominator。IUT 不需獨立，但要求每個 elementary test 有效；其邏輯見本文推導。[Deng](https://arxiv.org/pdf/1803.06336) |
| C§13：attempt registry、receipts、one adjudication | **支持透明與可重現；未驗證** | 文獻支持揭露 protocol、失敗／前期 compute；digest 一致不等於 physics 或 endpoint 科學上正確。[NeurIPS checklist](https://neurips.cc/public/guides/PaperChecklist) |
| C§14：先實作／synthetic tests，PHYSICS-GO 後產生正式來源 | **未涵蓋精確 gates；支持前瞻界定** | 論文沒有認證這個 gate 次序或通知門檻。它能限制 outcome-driven choices，但不能自行證明機制存在 |
| A§1：a-r0 primary，其他30 settings exploratory | **支持區分確認與探索；未涵蓋選定 setting** | 主張應限 primary 的 population／assumptions；無文獻證明該 setting 會讓每個 factor 正邊際 |
| A§2：C1+C3 identity、oracle factor arms | **支持可稽核定義；不等於 causal shares** | 恆等式依固定 anchor／objective 成立；oracle score 刪除不等於 C§7 的 source retraining，CD§13 的分離應保留。本文代數／estimand 推導 |
| A§3：two-way pigeonhole primary | **支持但有條件** | 符合 crossed factors，優於把 cells 當 IID 的解讀；不保證五 seed levels 的 finite-sample coverage。[Owen–Eckles](https://arxiv.org/pdf/1106.2125) |
| A§4：successor-development-unused claim dates；記 legacy overlap | **支持誠實限定；實作未驗證** | 命名 TRAIN 不取消 role-disjoint confirmation 的可能性；若實際用於 calibration、selection 或 fitting，則不能再稱未見資料。文獻支持聲明 protocol，不替 manifest 認證 |
| A§5：future-epoch TLE permitted，non-causal | **與 causal deployment claim 矛盾；與 retrospective benchmark 相容** | 「預測未來 geometry」和「取得事後發布資料」不同。所有 arms 共用只能消除比較不對称，不能創造即時資訊可得性 |
| A§6：訓練前封存 learned/coordinator information；retrain vs knockout 分離 | **強支持方向** | 必須實際補上 joint candidate、shared resources、proposal timing 和 query 邊界；兩類消融分別命名。[DCG](https://arxiv.org/pdf/1910.00091)、[ROAR](https://arxiv.org/html/1806.10758v3) |
| R Accepted§4：learned S3 must beat S0 | **依 estimand 而定** | 同函數完整 exact argmax 下不能嚴格超越；deadline／model mismatch／horizon 下可以設有效問題。應先聲明差異軸，不能由結果反推理由 |
| CD§3：zero-bit → undefined | **條件式矛盾** | B=0、E>0 的 EE 為0；E=0 與相對改善 comparator=0 才是另列的分母問題。本文代數推導 |

## 6. 檢索界線與尚未被核實的主張

本次先依四個問題建立證據槽，再分別查原始方法論文、RL 統計方法、ETSI／3GPP／O-RAN 文件與衛星控制原文；第二輪只追查 consequential gaps：原始消融對照與數字、QPLEX／WQMIX 的 exploration 差異、seed 數的 effect 定義、crossed bootstrap 適用性、秒／毫秒的測量對象。對 COMA Table1、DROO Table2、Owen–Eckles 方法、Agarwal 的 run-count 結果、Xn reporting periods 及 Tyche timing table 做了主線複核。未使用二手綜述作結論依據。

停止檢索的原因是四個問題已有可追溯的一手證據與明確 ceiling；再增加相似 benchmark 論文不太可能改變「沒有 universal learner／seeds／deadline guarantee」這個判讀。**這是有界的批判性審查，不是系統性文獻回顧的完整 PRISMA census。**

以下仍未核實，不應在論文中補寫成已知事實：

1. **【專案提供／未獨立驗證】** +2.9% legacy gain 的原始重算、其機制份額、successor physics／learner 實作、資料不重疊及 deadline compliance。本次可核對的是提供文件內容，不是其內部宣稱的驗證活動。
2. 未找到同時具有 **independent learned values、learned interaction term、相同資訊 exact joint evaluator**，並清楚隔離 learned coordination 效應的完整 LEO handover 實證。這是本次未取得證據，不是斷言此類工作不存在。
3. VDN、QMIX、QPLEX、WQMIX、Dr.Reinforce 及 Cao 等部分消融只有曲線／文字方向；未經數位化重建的精確幅度均標為未取得。未把目測趨勢冒充 exact pp，也未把跨演算法結果冒充只改一元件的消融。
4. 未取得可用於本專案 **1–3% EE** 的 paired learner-seed variance 或可靠先驗 power calibration，因此沒有可核實的最小 seed 數。
5. 未取得 operational LEO joint handover evaluator 的 end-to-end deadline／worst-case runtime 認證。Tyche 是 GEO preprint；安全 filter 是非 NTN 外推；標準功能不等於實際營運商功能。
6. IUT 在本文以明示數學論證支持；未取得完整 v1.2§4，也未將未成功開啟的 Berger–Hsu 原始全文列作已核實來源。對 “ablation is not attribution” 亦不虛構同名定理。

來源連結就近列於證據表，日期是所引版本的日期而非宣稱全部為最新版本。2010／2007／2012 因果與 bootstrap 論文已明列為必要基礎文獻。全文的數學與 Markdown 表格做結構核對；未另製作或宣稱完成 PDF 版面檢查。

## 7. 一手來源支持最強的五項設計修訂

以下全部是**【針對提供／未獨立驗證合約的建議】**；排序依其能避免主張失真與來源支持的強度，不預測哪項會使 C3 得正結果。

1. **把 S3、S0、S_UNI 與它們各自能支持的主張寫成明確比較。** 修改 C§9／R§4：明定 exact 的 objective、horizon、候選完備性及預算；分開「聯合協調優勢」「learned surrogate／proposer 的效率」與「模型誤差／長期績效改善」。同一函數上的 exact argmax 用來界定 regret，不能被要求有嚴格正的 learned score 優勢。[DROO](https://arxiv.org/pdf/1808.01977)、[DCG](https://arxiv.org/pdf/1910.00091)、[Cao et al.](https://arxiv.org/pdf/2402.04056)；argmax 界線為本文推導。

2. **在 C3 訓練前封存真正可辨認 joint profile 的輸入、標籤與 decoder。** 落實 A§6／C§4–6：candidate identities、其他人的 proposed actions 或等價充分表示、共享資源／activation／interference 背景、reference anchor、coalition 子集與合法性都要可追溯；完整 selector 優化完整目標。以資訊與容量配對的 additive／interaction 比較隔離效果，不把 credit sharing 或可學性當成 deployed gain。[COMA](https://arxiv.org/pdf/1705.08926)、[SQDDPG](https://arxiv.org/pdf/1907.05707)、[QMIX](https://arxiv.org/pdf/1803.11485)、[QTRAN](https://arxiv.org/pdf/1905.05408)

3. **保留 retrained neutral-source 主實驗，但將名稱、干預路徑與另外三種消融完全對齊。** C§7 的主張限 informative vs neutral training source；architecture removal、checkpoint knockout、oracle factor-score removal 各用獨立名稱和 estimand。明列 neutral 定義、調參／重訓機會、預算、選模程序及沒有繞過介入的 residual evaluator。這支持清晰歸因，不要求把所有消融都當同一 primary gate。[ROAR](https://arxiv.org/html/1806.10758v3)、[Meyes et al.](https://arxiv.org/pdf/1901.08644)、[Imai et al.](https://arxiv.org/pdf/1011.1079)

4. **統一統計條款：crossed paired ratio 為主，seed 數量以 precision／power 證據限定。** 把 A§3 寫回 C§11–12，封存 relative-effect 公式、+0.5 pp 的真正意義、population weights、零分母處理及 conjunction 的範圍。共同重抽 date／seed，保留 arms pairing；並報 seedwise paired effects。若維持五個模型，明說未知的 power／有限 precision，不借別的 benchmark 的 N 宣稱足夠，也不以更多 worlds 取代模型複本。[Owen–Eckles](https://arxiv.org/pdf/1106.2125)、[Colas 2018](https://arxiv.org/pdf/1806.08295)、[Agarwal et al.](https://arxiv.org/html/2108.13264v4)、[Deng et al.](https://arxiv.org/pdf/1803.06336)

5. **把孤立的 30.08 s 改寫成 controller-specific information／timing／fallback 合約。** C§9–10／CD§12 要連接 controller 位置、資料發布與取得時間、量測窗口、資訊傳送、完整計算、joint validation、fallback 和命令生效。保留可行基準決策、將所有 timeout 的後果計入 B／E／QoS；對 future-epoch TLE 僅作 retrospective benchmark 的明示限制。標準支持這些資訊界線，沒有替專案選定任何新 deadline。[TS38.300 Rel-19](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/19.01.00_60/ts_138300v190100p.pdf)、[XnAP](https://www.etsi.org/deliver/etsi_ts/138400_138499/138423/18.05.00_60/ts_138423v180500p.pdf)、[Tyche](https://arxiv.org/pdf/2512.09312)、[Predictive safety filter](https://arxiv.org/pdf/1812.05506)
