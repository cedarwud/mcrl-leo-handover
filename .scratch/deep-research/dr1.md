# 比率型累積目標的強化學習：DR-1 深度文獻調查

## 比較矩陣

下表只把真正優化「**期望累積量之比**」或與它有嚴格等價關係的方法列為核心方法；把「每一步先算 \(B_t/E_t\) 再做一般 RL」視為不同目標。這個區分不是語義問題：Jin 等人明確比較
\[
\frac{\mathbb E[A]}{\mathbb E[T]}
\quad\text{與}\quad
\mathbb E\!\left[\frac{A}{T}\right]
\]
並指出後者不是前者的等價替代。citeturn36view0turn37view2

記
\[
J_B(\pi)=\mathbb E_\pi\!\left[\sum_t B_t\right],\qquad
J_E(\pi)=\mathbb E_\pi\!\left[\sum_t E_t\right],\qquad
\rho(\pi)=\frac{J_B(\pi)}{J_E(\pi)},\quad J_E>0.
\]

| formulation 與 canonical citation | 實際優化目標 | 收斂結果與假設 | function approximation | off-policy replay 與 \(\eta/\rho\) staleness | discrete + value-based 實例 | 每 transition 訓練訊號 / on-policy correction |
|---|---|---|---|---|---|---|
| **Dinkelbach fractional programming** — Dinkelbach, *Management Science*, 1967, DOI **10.1287/mnsc.13.7.492** | \(\max_\pi J_B/J_E\)。定義 \(F(\eta)=\max_\pi[J_B(\pi)-\eta J_E(\pi)]\)；最優 \(\rho^\star\) 滿足 \(F(\rho^\star)=0\)。 | 經典外迴圈在每個 \(\eta_k\) 解參數化子問題，再以所得 numerator/denominator 更新 quotient；原始理論的強收斂結果依賴正分母與精確 inner solve。Jin 等人特別指出，Dinkelbach 經典證明要求每輪取得 exact solution，而他們的 FQL 才處理有界 inner error。citeturn29search0turn37view1 | Dinkelbach 本身只規定 inner optimisation，不替任意 NN inner solver 提供收斂保證。若 inner solver 有可控誤差，可另外證明 inexact outer convergence；Jin 是一個例子。citeturn37view1 | **關鍵原則**：transition 本身不因 \(\eta\) 改變，但 transformed reward \(B-\eta E\) 會改變。因此，若 replay 儲存舊的 \(B-\eta_{\rm old}E\)，label 會 stale；若儲存 raw \(B,E\)，抽樣時可代入當前 \(\eta\) 重算。這個後者是由 Dinkelbach 代數直接得到的安全做法；**本調查沒有找到經典 Dinkelbach-RL primary source 明文提出 replay relabelling protocol**。 | Dinkelbach 是最佳化框架，不是 RL 實作。純離散 value-based 的 published RL 實例見下方 Suttle 與 Jin。 | 固定 \(\eta\) 時，把全域比率化為 additive signal \(g_\eta=B-\eta E\)，再對 \(g_\eta\) 做一般 Bellman/TD。若 inner learner 是 Q-learning，不因 off-policy control 本身而需要 importance ratio。 |
| **Fractional-cost MDP** — Ren & Krogh, *IEEE Transactions on Automatic Control* 50(5), 2005, pp. 646–650, DOI **10.1109/TAC.2005.846520** | 以 MDP 的 numerator/denominator performance criteria 形成 fractional cost，屬 Dinkelbach/linear-fractional MDP 路線。 | 這是 fractional MDP 的 model-based 前身，不是 deep/model-free learning theorem；後來的 fractional-RL 文獻亦將它歸為「MDP formulation，未處理 RL」。citeturn35view0 | **無該論文的 deep-FA 結果。** | **無 replay。** | **無 RL instantiation。** Jin 等人也把它和後來的 RL 方法分開處理。citeturn35view0 | 透過 fractional-programming 參數化問題取得 additive cost，而非把 instantaneous ratio 當 reward。 |
| **Cost-Aware MDP / CARVI Q-learning** — Suttle et al., ICML 2021, PMLR 139 | \(\rho(\pi)=\bar r_\pi/\bar c_\pi\)，其中分子、分母各自是 long-run average reward/cost。這是 ratio of averages，而非 average of \(r/c\)。citeturn16view0turn18view0 | 有限 \(S,A\)，paper 假設 reward/cost 為正，所有 induced chains ergodic；tabular、Robbins–Monro stepsizes，且 quotient update 比 Q update 慢，即 \(\beta_n/\alpha_n\to0\)。在這些條件下 CARVI 的 \(Q_n,\rho_n\) a.s. 收斂到全域最優解。citeturn18view3turn19view0 | 論文寫出 NN gradient 版本並做 Deep-CARVI 實驗，但 global theorem 是 **tabular**；沒有一般 nonlinear deep-Q convergence theorem。citeturn19view0turn19view2 | Published CARVI 是 **online two-timescale SA，不使用 replay**。因此沒有 old-\(\rho\) replay label 問題，也沒有論文提供 buffer relabel/flush 規則。citeturn18view2turn19view1 | **有。** 有限離散 action 的 RVI-style Q-learning；這是最乾淨的 exact-ratio、value-based published instantiation之一。**但沒有 action-mask 實驗。** | TD error 使用 \(r_n-\rho_n c_n+V_n(s')-V_n(s_{\rm ref})-Q_n(s,a)\)；\(\rho\) 在慢 timescale 更新。這是 transformed **differential** reward。控制版 Q-learning 是 off-policy 型，不靠 trajectory-level ratio reward。citeturn19view0 |
| **Fractional Q-Learning / Frac-DRL** — Jin et al., AAAI 2024, **arXiv:2312.10418** | 原始目標是 expected time-average AoI 的 ratio of expectations。先以 Dinkelbach \(c_N-\gamma c_D\) 改寫，再以 \(\delta\uparrow1\) 的 discounted problem 近似 average formulation。citeturn36view0turn37view0 | 有限 \(S,A\)。FQL theorem 要求 inner Q approximation 滿足 uniform error bound \(\|Q^\star_{\gamma_i}-Q_i\|\le\epsilon_i\) 與特定 stopping condition；在此前提下 \(\gamma_i\) 線性收斂。這比 exact-Dinkelbach 放寬，但 theorem **不是對 D3QN + replay 的 NN convergence theorem**。citeturn36view1turn37view1 | Deep 部分把 D3QN/DDPG 放入 fractional framework，屬 empirical approximation。論文使用 \(\delta=0.9\)，而 average-objective equivalence只主張 \(\delta\to1\) 的 asymptotic approximation。citeturn36view0turn39view1 | **有 replay，而且發現一個重要未解決 staleness。** Paper 先用當前 \(\gamma_i\) 算 \(c_i=A-\gamma_i T\)，再把這個**已 transformed 的 scalar \(c_i\)** 存入 D3QN/DDPG replay；\(\gamma\) 又會跨訓練更新。文中沒有描述清 buffer、relabel 或儲存 raw \(A,T\) 後重算。citeturn37view2turn37view3turn39view0turn39view1 因而 replay 中舊資料對新 \(\gamma\) 的 Bellman problem 是 stale；其 FQL convergence theorem 沒有分析這件事。 | **有，而且是本調查找到最接近需求的 published deep case。** D3QN 負責 discrete offloading；paper 明確使用 experience replay、mini-batch、Double/Dueling target machinery。整體問題仍是 hybrid discrete–continuous，不是純離散 masked DQN。citeturn35view0turn39view1 | 固定 \(\gamma_i\) 時 target 為 \(c_i+\delta Q_{\rm target}(s',\arg\min_a Q_{\rm eval})\)。它不需要 on-policy correction；但跨 \(\gamma_i\) replay 的 reward label 並不固定。citeturn39view1 |
| **普通 average-reward / differential Q-learning** — Howard 1960；Abounadi–Bertsekas–Borkar 2001；Wan–Yu–Sutton 2024, **arXiv:2408.16262** | \(\max_\pi\lim_N\frac1N\mathbb E_\pi\sum_{t<N}B_t\)。這是目標比率的**特例 \(E_t\equiv1\)**，不是任意能量 denominator。 | Abounadi 等的 RVI-Q 理論原本以 unichain 類條件為核心；Wan–Yu–Sutton 把 RVI-Q convergence 推到 finite weakly communicating MDP，並證明 a.s. 收斂到 average-reward optimality-equation 的解集合。citeturn41academia2turn42academia0 | 這一領域有比 fractional RL 更成熟的 linear-FA 結果；例如 Zhang et al. 2021 給出 off-policy average-reward policy evaluation 的收斂方法。但這不能直接升格為 nonlinear deep off-policy **control** theorem。citeturn9view3 | 經典 RVI/differential Q 是 asynchronous online SA，不等同 DQN replay。**沒有發現其一般收斂 theorem 直接涵蓋 replay mini-batches + nonlinear target networks。** | **有，大量 tabular discrete value-based。** Wan 等更明確研究 off-policy control。動態 action masks 在這些 ratio/average-reward theorem 中不是研究變數。 | 本地 TD signal 是 \(B_t-\bar B+V(s')-V(s)\) 或等價 RVI normalization。分母固定為一步，所以沒有額外 \(E_t\)。 |
| **Semi-Markov reward-per-time / reward-per-cost** — classical SMDP；Yu–Wan–Sutton, **arXiv:2512.06218** | 標準 SMDP 的 reward rate 是「累積 reward / 累積 holding time」。若把正的 \(E_t\) 視為一個 additive clock/cost measure，其結構正是 \(\bar B/\bar E\)。 | 最新 RVI-Q 結果涵蓋 finite, weakly communicating SMDPs，採 asynchronous stochastic approximation；其收斂依賴適當 stepsize、visit/asynchrony 與 holding-time regularity。citeturn42academia1 相關 SA 基礎在 Yu–Wan–Sutton 2026 SIAM JCO 進一步建立。citeturn49view0 | 理論主要為 tabular/asynchronous SA；不是 deep replay theorem。 | Published 方法以 online samples 更新 reward-rate correction；**本調查未找到 buffer relabel protocol**。若 rate \(\rho\) 變動，存 raw reward與duration 再代入當前 \(\rho\) 才與當前方程一致，這是 Bellman 式的直接代數後果。 | **有 tabular discrete RVI-Q；無明確 masked-DQN deep instance found。** | 典型 differential signal 的結構為 \(R_t-\rho\,\tau_t+\) relative-value bootstrap；這與任意 \(B-\rho E\) 的 fractional transform 同型。 |
| **Direct ratio policy gradient / CAAC** — Suttle et al., ICML 2021 | 直接對 \(L(\theta)=J_r(\theta)/J_c(\theta)\) 求 policy gradient，而不是先選固定 scalarization weight。citeturn18view2 | 在 paper 的 ergodicity、stepsize、linear critic 等條件下，actor-critic 有 stochastic-approximation 收斂結果；critic 一般可能有 approximation bias，論文只在額外條件下控制其影響。citeturn19view3 | **有 linear critic theory**，但不是 arbitrary deep network guarantee。 | 原演算法不是 replay-based off-policy actor。若拿歷史 behaviour-policy replay 做 gradient，stationary-state/action distribution 已改變，原 theorem 不直接適用；paper 未提供 replay correction。 | **不是 value-based argmax。** 是 actor-critic。 | ratio gradient 可寫成與 \(\frac{1}{J_c}(A_r-\rho A_c)\) 成比例的 score-function update；paper 實作上分別估 reward/cost critics，再組合兩者。citeturn18view2 |
| **CMDP 作為替代 formulation** — Altman, *Constrained Markov Decision Processes*, 1999 | \(\max_\pi J_B(\pi)\;\text{s.t.}\;J_E(\pi)\le c\)，**不是** \(\max J_B/J_E\)。 | finite-state CMDP 可用 occupation measures/LP 表示；一般約束可能需要 randomized stationary policies，並可用 Lagrangian/dual methods。citeturn52search0 | 有大量 actor-critic、primal-dual 與 function-approximation 文獻，但它們的 convergence theorem 對的是 fixed-budget constraint，而非 fractional endpoint。 | dual multiplier \(\lambda\) 改變時，若把 \(B-\lambda E\) 預先存成 scalar reward，會有與 Dinkelbach 類似的 label staleness；成熟實作通常應把 constraint cost 當獨立訊號，但這不是 ratio equivalence theorem。 | **有離散 RL，但優化的是 constrained objective。** | Lagrangian TD signal \(B-\lambda(E-c)\)；若 off-policy actor 使用 replay，需其相應的 off-policy machinery。 |
| **兩個 Q critic \((Q_B,Q_E)\) + per-action ratio / Dinkelbach argmax** | 常見建議是分開學 numerator、denominator，再以 \(Q_B/Q_E\) 或 \(Q_B-\eta Q_E\) 選 action。 | **沒有找到這個完整 architecture 的 primary convergence theorem。** Jin 的 \(Q_\gamma=N_\gamma-\gamma D_\gamma\) 是最接近的數學分解，但 \(N_\gamma,D_\gamma\) 都必須在**同一個 \(\gamma\)-optimal continuation policy**下定義；這不是「各自最大化 numerator Q 與 denominator Q」的兩個獨立 optimality heads。citeturn37view0turn37view1 | Suttle CAAC 確實有分離的 reward/cost critics，但它們是 **state-value actor-critic**，不是兩個 Q-head DQN。citeturn18view2 | **沒有找到**「raw \(B,E\) replay + 兩 Q critics + Dinkelbach outer loop + replay-time relabel + discrete DQN」的 published primary source。 | **完整組合：none found。** | 有嚴格依據的是在固定 \(\eta\) 下比較 \(Q_B^\pi-\eta Q_E^\pi\)，而非一般地對兩個獨立 optimal Q 做 \(Q_B/Q_E\)。 |

### 矩陣的主要結論

對「**off-policy、replay-based、value-based、discrete**」這組條件，文獻不是完全空白：**Jin et al. 2024 的 D3QN 是一個真實 published replay-based fractional DRL instance**，而且它確實把離散 Q-learning 放進 Dinkelbach-like outer update。可是，它不是可直接援引的完整答案，原因有三個：其整體 action space 是 hybrid 而非純離散；其 deep implementation 用 discounted \(\delta=0.9\) 問題近似原 long-run ratio；最重要的是，它將以舊 \(\gamma_i\) 計算的 transformed cost 直接存進 replay，而 \(\gamma\) 之後會改變，論文沒有 relabel、flush 或 convergence analysis 來處理這個 staleness。citeturn36view0turn37view2turn39view1

因此，若標準再收緊成「**exact ratio-of-expectations + deep value-based + experience replay + dynamic legal-action mask + 有針對 \(\eta\)-change replay staleness 的文獻處理**」，本調查的結果是 **none found**。最強的理論底座仍是 Suttle 的 tabular two-timescale CARVI 與 average-reward/SMDP RVI-Q；最接近的 deep implementation 是 Jin，但它恰好暴露了 replay 問題，而不是解決了它。citeturn16view0turn41academia2turn42academia1turn39view1

還有一個容易誤讀的點：無線通訊文獻確實長期把 energy efficiency 定義成 rate/power 或 bits/Joule 的 fractional programme，並用 fractional programming 求解；例如 Isheden et al. 明確以 rate-to-power ratio 建模 EE，Zappone 等亦研究 network-centric bit/Joule maximisation。citeturn52academia8turn45academia2 但許多「EE + DQN」論文只是把當下 EE 或其 weighted combination 當 immediate reward，這並不自動等於 \(\mathbb E[\sum B]/\mathbb E[\sum E]\)。Jin 的 ratio-of-expectations vs expectation-of-ratio 對照正好說明這個落差。citeturn37view2

## 比率目標下的 advantage 與「外部 action 是否更好」

對比率目標來說，「\(a_D\) 是否比 learner action 好？」不能直接借用一個與目標無關的 scalar \(Q\)-margin。文獻中至少有三種彼此相關、但用途不同的定義。

### Dinkelbach／differential advantage

最直接的定義是在一個**固定 quotient parameter** \(\eta\) 下，先把 objective 變成 additive：

\[
g_\eta(s,a,s')=B(s,a,s')-\eta E(s,a,s').
\]

對固定 continuation policy \(\pi\)，定義

\[
Q_\eta^\pi(s,a)
   =Q_B^\pi(s,a)-\eta Q_E^\pi(s,a),
\]

以及

\[
A_\eta^\pi(s,a)
   =Q_\eta^\pi(s,a)-V_\eta^\pi(s)
   =A_B^\pi(s,a)-\eta A_E^\pi(s,a).
\]

在 \(\eta=\rho(\pi)\) 或最優 \(\eta=\rho^\star\) 時，這就是 fractional objective 所對應的自然 local comparison。Jin 的 fractional Q decomposition 正是
\[
Q_\gamma=N_\gamma-\gamma D_\gamma
\]
而 action selection 是依這個**difference Q**，之後才用 \(N/D\) 更新 quotient；它不是直接用 action-wise \(N/D\) 做 Bellman max。citeturn37view0turn38view0 Suttle 的 CARVI 也使用同一結構，只是在 continuing-average setting 中加上 relative-value normalization。citeturn19view0

因此，對一個外部 proposal \(a_D\)，最有文獻根據的 margin 是

\[
m_\eta(s,a_D,a_L)
=
Q_\eta(s,a_D)-Q_\eta(s,a_L)
=
[Q_B(s,a_D)-Q_B(s,a_L)]
-\eta[Q_E(s,a_D)-Q_E(s,a_L)].
\]

若 \(m_\eta>0\)，在當前 \(\eta\) 與相同 continuation semantics 下，\(a_D\) 對 transformed fractional subproblem 較好。**這個 margin 有單位「bits − \(\eta\)·joules」後的共同標度；它不是任意 scalarisation weight。** Dinkelbach 的關鍵正是 \(\eta\) 由 fractional optimum 決定，而非人工指定。citeturn29search0turn37view1

### Direct ratio policy-gradient advantage

Suttle 的 CAAC 給出另一個非常乾淨的答案。對
\[
\rho(\theta)=\frac{J_B(\theta)}{J_E(\theta)},
\]
其 gradient 可以整理為

\[
\nabla\rho(\theta)
=
\frac{1}{J_E(\theta)}
\mathbb E_{\pi_\theta}
\left[
\nabla_\theta\log\pi_\theta(a|s)
\left(
A_B^\pi(s,a)-\rho(\pi)A_E^\pi(s,a)
\right)
\right].
\]

換句話說，忽略全 state-action 共用的正 scale \(1/J_E\) 後，**ratio policy gradient 的 action-level advantage 正是**

\[
A_\rho^\pi(s,a)
=
A_B^\pi(s,a)-\rho(\pi)A_E^\pi(s,a).
\]

Suttle 在演算法中等價地以分開的 reward/cost critic 與 normalized TD errors 組成這個更新方向。citeturn18view2

這使「external action better」有一個自然的一階定義：

\[
a_D\ \text{ratio-advantageous at }s
\quad\Longleftrightarrow\quad
A_B^\pi(s,a_D)-\rho(\pi)A_E^\pi(s,a_D)>0.
\]

但這是**policy-gradient / local policy-improvement signal**，不是說一個單一步驟正值就保證整個新 deterministic policy 的 global ratio 一定更高。CAAC 的 theorem 也建立在 current-policy stationary distribution 與其 stochastic-approximation assumptions 上，而不是 arbitrary replayed demonstration distribution。citeturn18view2turn19view3

### Action-return quotient \(Q_B/Q_E\)

第三種看似直觀的量是

\[
R^\pi_Q(s,a)=\frac{Q_B^\pi(s,a)}{Q_E^\pi(s,a)}.
\]

它對「先做 \(a\)，之後固定跟隨同一個 \(\pi\)」可作為 continuation ratio 的描述；Jin 也確實用 numerator/denominator quotient 來更新 outer coefficient。citeturn37view1 **但找到的 primary fractional-Q 文獻並沒有建立**
\[
Q^\star_{\rm ratio}(s,a)
\stackrel{?}{=}
Q_B^\star(s,a)/Q_E^\star(s,a)
\]
這種「兩個各自 optimal Q 再相除」的 Bellman optimality identity。反而 Jin 的推導要求兩個 component 都跟隨同一個 \(\gamma\)-optimal policy，再形成 \(N_\gamma-\gamma D_\gamma\)。citeturn37view0 這是為什麼「兩頭各自學到最好，再除一下」不是有文獻保證的 ratio-DQN architecture。

### 哪些定義被拿來 gate imitation loss？

在符合本調查來源門檻的 fractional-MDP、cost-aware RL、average-reward/SMDP 與 fractional deep-RL primary literature 中，**沒有找到任何一篇把**
\[
A_B-\rho A_E,\qquad
Q_B-\rho Q_E,
\quad\text{或}\quad
Q_B/Q_E
\]
**用作 demonstration imitation／large-margin regression loss 的 gate，並對 ratio objective 提供理論或 ablation。**

因此，若要使用類似

\[
\mathcal L_{\rm demo}
=
\mathbf 1\!\left[
Q_B(s,a_D)-\eta Q_E(s,a_D)
>
Q_B(s,a_L)-\eta Q_E(s,a_L)
\right]
\mathcal L_{\rm BC},
\]

這個 gate 的**比較量**有 Dinkelbach/ratio-advantage 理論根據，但「用它來開關 imitation loss」本身是新組合；不能稱為已被 fractional-RL 文獻驗證的方法。Suttle 提供的是 actor update，Jin 提供的是 fractional-Q action selection，兩者都不是 demonstration-gated supervised loss。citeturn18view2turn37view0

這也意味著，在 ratio objective 下直接沿用 DQfD 類「單一 scalar Q 上的固定 margin」只有在那個 scalar Q **確實是當前 \(B-\eta E\) fractional subproblem 的 Q** 時才有明確語義；若 scalar Q 是人工加權的多目標 reward，則 margin 對 \(\rho\) 沒有相同的 fractional-programming 保證。這是由 Dinkelbach transform 與 CAAC gradient 共同導出的區別。citeturn29search0turn18view2

## 跨 episode 的 pooled ratio 與 long-run ratio

三個常被混在一起的 estimator/objective 應嚴格分開。

### Episodic ratio 再平均

令第 \(i\) 個 episode 有
\[
B_i=\sum_t B_{it},\qquad E_i=\sum_t E_{it}.
\]

先各自算 ratio 再平均是

\[
\widehat \rho_{\rm mean\ ratio}
=
\frac1N\sum_{i=1}^N\frac{B_i}{E_i}.
\]

它估的是
\[
\mathbb E\!\left[\frac{B}{E}\right],
\]
不是一般情況下的
\[
\frac{\mathbb E[B]}{\mathbb E[E]}.
\]

Jin 等人的 paper 幾乎直接對應這個問題：其 fractional AoI 是 numerator expectation / denominator expectation，而 non-fractional benchmark 把它近似為 expectation of an instantaneous ratio；作者明確說兩者不等價，並在實驗中把後者列為失真的 benchmark。citeturn36view0turn37view2

因此，「mean episode EE」若每 episode 的 joules 不完全相同，就不是題目所宣告的 pooled bits/J endpoint。

### 全 episode pooled ratio

pooled statistic 是

\[
\widehat\rho_{\rm pooled}
=
\frac{\sum_{i=1}^N B_i}
     {\sum_{i=1}^N E_i}
=
\frac{\frac1N\sum_iB_i}
     {\frac1N\sum_iE_i}.
\]

在 episodes 是來自同一固定 policy、具有適當獨立／regenerative law、且 \(\mathbb E[E]>0\) 的通常條件下，sample means 的大數法則使它收斂到

\[
\frac{\mathbb E[B]}{\mathbb E[E]}.
\]

所以 **pooled ratio 是 ratio-of-expectations 的自然 sample estimator**；它不是 mean-of-ratios。這與 fractional-RL 所保留的「分子 expectation、分母 expectation 分開後再取 quotient」完全一致。Jin 的式子與 Dinkelbach reformulation正是按這個順序處理 numerator、denominator。citeturn36view0turn37view0

但需要區分「它是好 estimator」和「文獻直接對這個有限樣本 quotient 做 TD」。在本次找到的 primary RL 文獻中，**沒有找到把一批 completed episodes 的**
\[
\frac{\sum_iB_i}{\sum_iE_i}
\]
**本身當作 replay transition loss、再反向傳播到 DQN 的標準方法**。可訓練的方法反而是：

\[
B_t-\eta E_t
\]

的 Dinkelbach Bellman signal，或者 online reward-rate/differential signal。Suttle 與 Jin 都屬這一類。citeturn19view0turn39view1

換言之，pooled ratio 最自然的角色有兩個：一是作為 **population ratio objective 的一致性評估統計量**；二是用其分子/分母估計值更新 Dinkelbach quotient。它不需要被硬轉成「每 episode ratio reward」。

### Long-run average ratio

continuing-process 文獻常使用

\[
\rho(\pi)
=
\frac{
\displaystyle
\lim_{N\to\infty}
N^{-1}\mathbb E_\pi\!\sum_{t=0}^{N-1}B_t
}{
\displaystyle
\lim_{N\to\infty}
N^{-1}\mathbb E_\pi\!\sum_{t=0}^{N-1}E_t
}.
\]

這就是 Suttle cost-aware MDP 明確訓練的 objective。citeturn18view0 Semi-Markov average-reward 則把 denominator 具體化為 elapsed holding time，並學 reward rate；最新 RVI-Q 理論已延伸到 weakly communicating SMDPs。citeturn42academia1

三者之間因此可整理為：

| quantity | population target | 文獻地位 |
|---|---|---|
| \(\frac1N\sum_i B_i/E_i\) | \(\mathbb E[B/E]\) | **不同目標**；fractional-RL 文獻明確警告不可一般性替代 ratio-of-expectations。citeturn37view2 |
| \(\frac{\sum_iB_i}{\sum_iE_i}\) | \(\mathbb E[B]/\mathbb E[E]\) 的 sample estimator | 適合作為 evaluation / quotient estimation；**未找到直接有限-batch quotient TD objective**。 |
| \(\bar B_\pi/\bar E_\pi\) | continuing long-run reward-per-cost | **明確 trainable**：CARVI、SMDP RVI-Q、direct ratio actor-critic。citeturn16view0turn42academia1 |

有限 episode 的 ratio-of-expectations 與 continuing long-run ratio **不能僅因公式長得像就宣告等價**。若 episode 是真正 regenerative cycles，renewal/reward-per-cycle 結構可把兩者連接；但若 episode boundary 只是訓練人為截斷，則它可能改變分子與分母的 sampling law。Jin 為了從 time-average formulation 進入一般 deep-RL machinery，特別需要額外的 \(\delta\to1\) asymptotic step；這本身就顯示「finite discounted episode」與「exact average ratio」不是無條件同一件事。citeturn36view0

## Ratio objective 與 constrained MDP 的關係

考慮兩個問題：

\[
(P_R)\qquad
\max_\pi\frac{B(\pi)}{E(\pi)},\qquad E(\pi)>0,
\]

與

\[
(P_C(c))\qquad
\max_\pi B(\pi)
\quad\text{s.t.}\quad
E(\pi)\le c.
\]

它們**一般不等價**。無線 energy-efficiency 文獻對這點說得很直接：rate/power EE maximisation 雖然同時涉及 throughput 與 power，但它不同於「固定 power constraint 下最大化 rate」或「固定 rate 下最小化 power」，因為那些 constraint 在 EE optimum 不必 active。citeturn52academia8 CMDP 文獻則把 fixed-cost-bound 問題本身當成另一類 occupation-measure/LP 問題。citeturn52search0

一個簡單例子足以顯示差別。若有兩個政策

\[
(B_1,E_1)=(10,2),\qquad (B_2,E_2)=(12,3),
\]

則

\[
B_1/E_1=5>4=B_2/E_2,
\]

所以 ratio objective 選 \(\pi_1\)。但若固定 budget \(c=3\)，constrained problem 選 \(B_2=12\) 的 \(\pi_2\)。這正是「效率最高」與「在給定能源預算內總產出最高」是不同 preference 的最小反例。

### Ratio optimum 一定可以對應到某個特定 budget

反方向有一個重要、而且很容易被說過頭的條件性關係。

令 \(\pi_R^\star\) 是 ratio optimum，並設

\[
E^\star=E(\pi_R^\star).
\]

則 \(\pi_R^\star\) 必定也是

\[
\max_\pi B(\pi)
\quad\text{s.t.}\quad
E(\pi)\le E^\star
\]

的一個解。理由很直接：假如存在 \(\tilde\pi\) 滿足
\[
E(\tilde\pi)\le E^\star,\qquad
B(\tilde\pi)>B^\star,
\]
則
\[
\frac{B(\tilde\pi)}{E(\tilde\pi)}
>
\frac{B^\star}{E^\star},
\]
與 \(\pi_R^\star\) 的 ratio optimality 矛盾。

所以存在一個「**事後由 ratio optimum 自己決定的 budget**」使 CMDP 包含 ratio optimum。這不等於說，工程師任意先指定的 \(c\) 都會產生同一政策。

### Constrained optimum 何時也是 ratio optimum

令 \(\pi_c^\star\) 解 fixed-budget CMDP，並定義

\[
\rho_c=\frac{B(\pi_c^\star)}{E(\pi_c^\star)}.
\]

它同時是 global ratio optimum 的充要檢驗，可寫為 Dinkelbach root condition：

\[
B(\pi)-\rho_c E(\pi)\le0
\qquad\forall\pi,
\]

且在 \(\pi_c^\star\) 取等號。這正是 Dinkelbach 對 ratio optimum 的 characterization。citeturn29search0

因此，CMDP 的 Lagrangian

\[
L(\pi,\lambda)
=
B(\pi)-\lambda(E(\pi)-c)
\]

雖然在形式上和

\[
B(\pi)-\rho E(\pi)
\]

很像，但兩個 multiplier 的來源不同：

- \(\rho^\star\) 是 **optimal numerator/denominator quotient**，由 zero-residual condition 決定；
- \(\lambda^\star\) 是 **固定 budget \(c\) 的 shadow price**，由 constraint/dual optimality 決定。CMDP 的 occupation-measure 與 Lagrangian theory 正是對後者建立。citeturn52search0

只有當某個 fixed budget 所選的 efficient-frontier point 剛好也是「從原點具有最大斜率 \(B/E\)」的點時，兩者 policy 才一致。這也解釋了無線 FP 文獻為何明確警告 EE maximisation 不是普通的 throughput-max-under-power-budget 問題。citeturn52academia8

對實作而言，這個差別很實質：把 declared endpoint \(B/E\) 換成「最大 \(B\)，並設定一個看起來合理的 energy cap」是在**更改決策偏好**，除非 cap 已經經過上述等價條件校準。反之，Dinkelbach \(B-\eta E\) 是 ratio objective 的 exact parametric reformulation，而不是任意 scalarisation。citeturn29search0turn37view1

## 證據缺口與對目標 architecture 的判決

**兩個 Q heads \((Q_B,Q_E)\)、Dinkelbach outer \(\eta\)、replay、discrete argmax 的完整架構：no source found。** 最接近的兩條 citation trail 都少一塊。Suttle CAAC 有分離的 reward/cost critics，但它是 actor-critic；Jin 有 \(N_\gamma,D_\gamma\) 的 numerator/denominator decomposition，並有 replay-based D3QN，但 deep network 實際訓練的是 transformed cost Q，而且 old-\(\gamma\) scalar rewards 被存進 replay。citeturn18view2turn37view0turn39view1 因此，先前「two-critic \((Q_B,Q_E)\) ratio architecture 已有成熟 citation trail」這個命題，**本調查不支持**。

**用 \(Q_B/Q_E\) 直接做 per-action argmax：no primary convergence source found。** 找到的 fractional-Q 推導反而使用
\[
Q_\gamma=N_\gamma-\gamma D_\gamma
\]
做 action comparison，再用 quotient 更新 \(\gamma\)。citeturn37view0turn37view1 因此，若要分兩個 heads，文獻上較有根據的 decision score 是「在**同一 continuation policy semantics**下」的
\[
Q_B-\eta Q_E,
\]
而不是兩個各自 optimal heads 的 \(Q_B/Q_E\)。

**「replay 存 raw \(B,E\)，每次 sample 用目前 \(\eta\) relabel」：數學上乾淨，但 no primary source found 明確把它作為 fractional-DQN replay protocol。** 它直接消除
\[
(B-\eta_{\rm old}E)\neq(B-\eta_{\rm new}E)
\]
的 label mismatch；然而不能把這個設計選擇包裝成已被文獻驗證。反而現有最接近的 Jin deep implementation 儲存的是已 transformed \(c_i\)，而且 quotient 會更新。citeturn37view2turn39view1 這是本調查最重要的 replay evidence gap。

**「每次 \(\eta\) 更新後清空 replay buffer」：no source found。** 這也能避免 old-\(\eta\) reward labels，但會丟掉 transition data；我沒有找到 fractional-RL primary paper 系統比較 clear、relabel、raw-storage 或 mixed-\(\eta\) replay。

**用 two-timescale argument 證明 deep replay 中 stale-\(\eta\) samples 無害：no source found。** Suttle 的 two-timescale theorem 是 online stochastic approximation：fast Q、slow \(\rho\)，不是有限 replay buffer 隨機重播舊 transformed rewards 的 theorem。citeturn18view3turn19view0 把 CARVI 的 two-timescale proof 直接拿來替 stale replay 背書，超出了該論文結果。

**nonlinear deep function approximation 的 exact-ratio global convergence：no source found。** Suttle 的 global result 是 tabular；其 actor-critic theorem用 linear critic assumptions。Jin 的 outer-loop theorem要求 inner \(Q_i\) 達到明示的 uniform approximation error，並沒有證明 D3QN 必定達到該條件。citeturn18view3turn19view3turn37view1 平均獎勵文獻已有嚴格的 off-policy linear-FA policy evaluation，但這仍不是 nonlinear replay-based Q-control theorem。citeturn9view3

**dynamic illegal-action masking 的 fractional-RL theorem／ablation：none found。** Classical finite MDP/Q-learning 自然可以把 Bellman \(\max_a\) 限制在合法集合 \(A(s)\)，所以 action mask 與 fractional transform 在數學上並不衝突；但在本次找到的 exact-ratio deep papers 中，沒有一篇以 dynamic action masking 作為明示的研究設計或收斂條件。Jin 的 discrete D3QN 是固定 action-space offloading selection，而非本文所問的 masked discrete-action setting。citeturn39view1

**ratio-aware demonstration gate／margin loss：no source found。** 文獻提供了
\[
A_B-\rho A_E
\quad\text{與}\quad
Q_B-\eta Q_E
\]
作為 ratio-consistent local preference quantities，但沒有找到它們被用來 gate supervised imitation、DQfD-style large-margin loss 或 regression-to-demonstrator target 的 fractional-RL paper。citeturn18view2turn37view0 因此，這若被採用，應標為新方法組合而非 replication。

**finite-sample pooled ratio 作為直接 differentiable replay loss：no source found。** 文獻能訓練的是 population fractional objective，做法是 Dinkelbach transformed TD、reward-rate differential TD 或 ratio policy gradient；pooled \(\sum B/\sum E\) 則自然扮演 evaluation/quotient estimator。citeturn16view0turn36view0

**「把 EE immediate ratio 當 DQN reward，就等於最大化 pooled bit/J」：文獻反而提供反證。** 無線通訊中 EE 的 fractional-programming 定義確實是 rate/power。citeturn52academia8turn45academia2 但 fractional RL 明確區分 ratio-of-expectations 與 expectation-of-ratios；因此，instantaneous bit/J reward 經 discounted/episodic summation後一般不會恢復 pooled bits / pooled joules。citeturn37view2

綜合這些證據，對題目所指定的 engineering class，文獻支持程度可分成三層：

| 設計元件 | 文獻支持程度 | 判決 |
|---|---|---|
| 以 \(B-\eta E\) 把 ratio 轉成 additive RL subproblem | **強**：Dinkelbach、CARVI、FQL 都支持。citeturn29search0turn19view0turn37view0 | 有 citation trail |
| discrete value-based ratio learning | **強（tabular）／有限（deep）**：CARVI tabular 有 theorem；Jin D3QN 有 empirical deep instantiation。citeturn18view3turn39view1 | 可據此設計，但 deep guarantee 不可宣稱 |
| replay-based D3QN | **有 published instance**，但 Jin 的 \(\gamma\)-stale transformed reward 未處理。citeturn39view1 | 存在，但不能當 staleness 正確性的證據 |
| raw \(B,E\) replay + sampling-time \(B-\eta E\) recomputation | **代數上直接正確；published protocol 未找到** | 合理新設計，須自行 ablate |
| separate \(Q_B,Q_E\) + difference score | **部分支持**：Jin 有同-policy \(N,D\) decomposition；無完整 deep two-Q replay architecture。citeturn37view0 | 不能稱現成標準方法 |
| separate independently-optimal \(Q_B,Q_E\) + ratio \(Q_B/Q_E\) argmax | **無支持** | 不應由現有理論推出 |
| ratio advantage gate for imitation/margin loss | **無 published instance found** | 新方法 |
| dynamic action masking | **與 MDP 結構相容，但 fractional-deep empirical/theoretical evidence 未找到** | 正交工程機制，不是已驗證 ratio 方法 |

因此，DR-1 最重要的 citation-trail 結論不是「找到了現成的 two-critic replay DQN」，而是更精確的：

> **已發表理論強烈支持以 Dinkelbach／reward-rate 的 \(B-\eta E\) 作為 ratio-consistent Bellman signal；已發表 deep work證明 D3QN + replay 可以被放入 fractional framework，但沒有解決 changing-\(\eta\) replay staleness；已發表 two-critic work則是 actor-critic，不是離散 Q-head architecture。完整的 \((Q_B,Q_E)\) + raw replay + Dinkelbach outer loop + masked discrete argmax 組合，在本調查中沒有找到 primary source。**

這個缺口很實質，因為 Jin 的 paper 恰好提供了一個可檢查的負面案例：其 replay tuple 明文存的是已由當前 \(\gamma_i\) 形成的 \(c_m(k)\)，而 \(\gamma\) 又會定期更新。citeturn37view2turn39view1 換言之，**「changing quotient parameter 與 replay target 如何共存」目前應視為設計問題，而不是已被成熟 fractional-RL 文獻解決的問題。**

## 參考文獻

| 文獻 | 識別資訊與本調查用途 |
|---|---|
| W. Dinkelbach, “On Nonlinear Fractional Programming.” | *Management Science*, 13(7), 1967. DOI **10.1287/mnsc.13.7.492**。fractional transform、zero-residual characterization、outer iteration 的 canonical source。citeturn29search0 |
| Z. Ren and B. H. Krogh, “Markov Decision Processes with Fractional Costs.” | *IEEE Transactions on Automatic Control*, 50(5):646–650, 2005. DOI **10.1109/TAC.2005.846520**。fractional-cost MDP 早期來源；後來 fractional-RL papers 將它列為未含 RL 的前身。citeturn35view0 |
| W. Suttle et al., “Reinforcement Learning for Cost-Aware Markov Decision Processes.” | ICML 2021, PMLR 139:9989–9999。CARVI、CAAC、two-timescale tabular convergence、direct ratio policy gradient。citeturn16view0turn18view3 |
| L. Jin, M. Tang, M. Zhang, H. Wang, “Fractional Deep Reinforcement Learning for Age-Minimal Mobile Edge Computing.” | AAAI 2024; **arXiv:2312.10418**。FQL、Dinkelbach decomposition、D3QN/DDPG fractional DRL、experience replay，以及 ratio-of-expectations / expectation-of-ratio 明確區分。citeturn31academia9turn35view0 |
| R. A. Howard, *Dynamic Programming and Markov Processes*. | MIT Press, 1960。average-reward / relative-value dynamic programming 的 foundational source。 |
| M. L. Puterman, *Markov Decision Processes: Discrete Stochastic Dynamic Programming*. | Wiley, 1994。average-reward、unichain/multichain、SMDP 等 classical theory；Jin 亦援引其 average/discount asymptotic relation。citeturn36view0 |
| J. Abounadi, D. Bertsekas, V. Borkar, “Learning Algorithms for Markov Decision Processes with Average Cost.” | *SIAM Journal on Control and Optimization*, 40(3):681–698, 2001。RVI Q-learning 的 foundational stochastic-approximation result；後來的 weakly-communicating convergence工作以此為起點。citeturn41academia2 |
| Y. Wan, H. Yu, R. S. Sutton, “On Convergence of Average-Reward Q-Learning in Weakly Communicating Markov Decision Processes.” | **arXiv:2408.16262**, 2024。把 RVI Q-learning 的 convergence 從較強的 unichain 類 assumptions 推展到 weakly communicating MDP。citeturn41academia2 |
| S. Zhang, Y. Wan, R. S. Sutton, S. Whiteson, “Average-Reward Off-Policy Policy Evaluation with Function Approximation.” | **arXiv:2101.02808**, 2021。off-policy average-reward linear function approximation 的重要收斂結果；屬 evaluation 而非 nonlinear deep Q-control。citeturn9view3 |
| H. Yu, Y. Wan, R. S. Sutton, “Average-Reward Reinforcement Learning in Semi-Markov Decision Processes via Relative Value Iteration.” | **arXiv:2512.06218**, 2025。finite weakly communicating SMDP 的 RVI-Q／reward-rate convergence。citeturn42academia1 |
| H. Yu, Y. Wan, R. S. Sutton, “Asynchronous Stochastic Approximation with Applications to Average-Reward Reinforcement Learning.” | *SIAM Journal on Control and Optimization* 64(3):1456–1481, 2026; DOI **10.1137/25M1769806**；**arXiv:2409.03915**。提供近年 asynchronous-SA 理論基礎。citeturn49view0 |
| E. Altman, *Constrained Markov Decision Processes*. | CRC Press, 1999, ISBN 9780849303821。CMDP occupation measures、LP、Lagrangian/dual 的 canonical reference。citeturn52search0 |
| C. Isheden, Z. Chong, E. Jorswieck, G. Fettweis, “Framework for Link-Level Energy Efficiency Optimization with Informed Transmitter.” | **arXiv:1110.1990**。無線 EE 作 rate/power fractional programme，並明確區分 EE maximisation 與 rate-max-under-power / power-min-under-rate formulations。citeturn52academia8 |
| A. Zappone et al., “Energy-Efficient Power Control: A Look at 5G Wireless Technologies.” | **arXiv:1503.04609**, 2015。以 bit/Joule 為 wireless network energy-efficiency objective 的代表性 fractional-optimisation工作。citeturn45academia2 |