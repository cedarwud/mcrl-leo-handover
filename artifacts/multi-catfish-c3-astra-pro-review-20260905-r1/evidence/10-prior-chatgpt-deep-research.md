# 三個 Catfish 正邊際的理論可行性與 C3 設計審查

## 直接答案與可行性判斷

**直接答案：可以，但要非常精確地限定「可以」的含義。**

設計**恰好三個 Catfish、每個接一個 Q-head，最後只做共同 safe mask 後的直接無權重 \(Q_1+Q_2+Q_3\)、一次 argmax、一次 Main action**，在理論上完全可以讓三個 head 對**同一個 scalar network ratio-of-sums EE** 都有正的 FULL-minus-DROP 邊際。這件事**不要求**三個舊有 multi-objective rewards 同時改善，也不要求三個 head 分別對應三個彼此相容的 legacy objectives。真正需要的是：三個 head 所表達的資訊，必須是**同一個 scalar EE action advantage 的互補部分或受控近似**，而不是三個目標投票器。加法式 value decomposition 本身在 cooperative value learning 中是有正當先例的；但 VDN/QMIX 類結果只支持「可施加加法或單調分解結構」，並沒有給出「每個 component 一定具有嚴格正 drop marginal」的定理。citeturn23search2turn21search0

就此 package 而言，我的判斷是：

| 問題 | 判斷 | 信心與控制證據缺口 |
|---|---|---|
| 三個正邊際在 function space 中是否可能？ | **是，而且可嚴格構造。** | 高；可直接給有限 action set 的反例式構造。 |
| 目前 simulator 的 physical channels 是否足以識別第三個非重疊 EE channel？ | **部分可以。** 即時與 frozen-background 下的 unilateral non-focal rate externality 是可定義、可觀測的；真正 simultaneous joint externality 與後續政策 cascade 則不是由單一 pre-action local head 唯一識別。 | 中高；package causal path 很清楚，但尚無 proposed C3 的 action-aligned census。 |
| 固定架構下是否 plausibly learnable/deployable？ | **合理，但未證。** | 中；action-aligned deterministic physical target 可以交給一個 Q3，但 approximation error、scale、shared-snapshot simultaneous cross-terms 尚未解決。 |
| 現有證據較支持一般 complementarity/cannibalization，還是存在 C2/C3 必有一個有害的結構定理？ | **前者。** 沒有理論理由要求 C2 或所有 C3 必然有害；但現有 victim-burden C3 的跨 context 負號是很強的「此 C3 機制失敗」證據。 | 中高。 |
| 最可能的 C3？ | **Projected Non-Focal Physical Externality Residual，簡稱 PNFER。** | 中；它最直接填補 C1/C2 在 canonical EE surplus 中留下的 non-focal numerator residual。 |

這個結論與 package 中的 development facts 一致而不超越它們。六個 fresh TRAIN worlds 上，H-A 與 Fable OPS-3 reading 的 C2 FULL-minus-DROP 分別為 \(+11.700\%\) 與 \(+9.480\%\)，C1 在兩個新 Q2 context 仍為正；相反地 frozen C3 分別為 \(-0.485\%\) 與 \(-2.687\%\)，而 Q1+Q3 versus Q1 在 fresh block 為 \(-9.716\%\)，重現先前約 \(-10.286\%\) 的方向。【專案驗證事實：`START-HERE.md`; `INTEGRATION-VERIFICATION.md`】這些只證明**目前 C3 與較好的 Q2 不互補**；它們既不證明三-head 結構不可能，也不證明任何 learned Q2/Q3 的 held-out efficacy。

最重要的限定是：**目前的三個角色並不是一個已經成立的 exact \(A_{\mathrm{EE}}\) decomposition。** package 中較早的 V0.3 accounting 曾經有很乾淨的 fixed-\(\lambda\) identity：opening focal bits 與全部 opening network energy 給 C1、opening non-focal rate externality 給 C3、offset \(>0\) 的 system surplus 全部給 temporal C2，並檢查三者重建 total window surplus。【專案證據：`source/runtime/ee_surplus_targets.py`】但目前 exact OPS-3 C2 已經改成一個**focal projected-persistence / recurrence-power / outage-risk prior**：它平均未來 offsets 的 focal projected rate-minus-\(\lambda_0\)-marginal-power 並加入 persistence failure penalty，而不是把所有未來 system surplus 接走。【專案證據：`source/runtime/ee_axis_ops3.py`; `docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md`】所以現在合理的論述應是：

> **三個 head 可以作為 scalar-aligned、causally partitioned surrogate views；目前還不能稱為 true EE advantage 的 exact 三項分解。**

這正是為什麼以下建議的 C3 必須是**non-focal physical residual**，而不是再發明第三個 reward objective。

## 形式可能性、證明與反例

先把最強的理論版本寫清楚。給定狀態 \(s\)、共同合法 action set \(\mathcal A(s)\)，假定存在真正的 scalar EE action score/advantage

\[
A_{\mathrm{EE}}(s,a)
\]

以及 exact decomposition

\[
A_{\mathrm{EE}}(s,a)
=
A_1(s,a)+A_2(s,a)+A_3(s,a).
\]

令

\[
a_F
\in
\arg\max_a\{A_1+A_2+A_3\},
\]

而 drop-\(j\) policy 在此狀態選

\[
a_{-j}
\in
\arg\max_a\sum_{i\neq j}A_i(s,a).
\]

因為 full sum 就是真正的 \(A_{\mathrm{EE}}\)，

\[
A_{\mathrm{EE}}(s,a_F)
=
\max_a A_{\mathrm{EE}}(s,a)
\ge
A_{\mathrm{EE}}(s,a_{-j})
\]

對每個 \(j\) 都成立。因此：

\[
\Delta_j
=
A_{\mathrm{EE}}(s,a_F)
-
A_{\mathrm{EE}}(s,a_{-j})
\ge 0.
\]

**所以 exact scalar decomposition 自動給 nonnegative FULL-minus-DROP；但不自動給 strictly positive。**

嚴格正值成立的充要直覺是：刪掉第 \(j\) 個 component 後，drop policy 必須真的被帶到一個**嚴格較差的 true-EE action**。若 drop-\(j\) 仍選到 full optimum，或只是落在另一個同值 global optimum，則 \(\Delta_j=0\)。這就是 redundancy/cannibalization 的第一個基本結果：**一個 head 可以含有真實有用資訊，卻因另一個 head 已經完全替代其 decision role，而得到零 marginal。**

更強地，三個 drop marginal 都嚴格正是可構造的。令 action set 為

\[
\{F,D_1,D_2,D_3\},
\]

三個 components 如下：

\[
\begin{array}{c|ccc|c}
a&A_1&A_2&A_3&A_{\mathrm{EE}}\\
\hline
F&1&1&1&3\\
D_1&-3&2&2&1\\
D_2&2&-3&2&1\\
D_3&2&2&-3&1.
\end{array}
\]

Full sum 選 \(F\)。刪掉 \(A_1\) 後，\(A_2+A_3\) 對 \(D_1\) 是 \(4\)，對 \(F\) 是 \(2\)，所以 drop-1 選 \(D_1\)；同理 drop-2 選 \(D_2\)，drop-3 選 \(D_3\)。因此三個 true scalar marginals 都是

\[
3-1=2>0.
\]

所以「恰好三個 head 每個都必須有嚴格正 marginal」**不是數學矛盾**。

反過來，action richness 很重要。例如若只有兩個 actions \(F,D\)，令

\[
d_i=A_i(F)-A_i(D).
\]

Full 要選 \(F\)，需要

\[
d_1+d_2+d_3>0.
\]

若三個 drop-one 都要改選 \(D\)，就同時需要

\[
d_2+d_3<0,\quad
d_1+d_3<0,\quad
d_1+d_2<0.
\]

三式相加得到

\[
2(d_1+d_2+d_3)<0,
\]

與 full condition 矛盾。因此在**只有兩個 actions 且每個 drop 都必須翻轉到另一 action**的簡化情況下，三個 strict drop marginals 不可能同時以這種方式產生。你們的 wireless action space 遠比兩 action 豐富，所以這不是專案障礙；它只是說明 strict complementarity 是 decision geometry 的性質，不是三個 scalar 隨意相加就會自然得到。

同樣重要的是：**某個 two-head combination 可以比 singleton 更差，同時三個 FULL-minus-DROP 仍全為正。** 例如：

\[
\begin{array}{c|ccc|c}
a&A_1&A_2&A_3&A_{\mathrm{EE}}\\
\hline
F&3&3&3&9\\
S&5&-4&2&3\\
P_{12}&4&4&-6&2\\
P_{13}&4&-6&4&2\\
P_{23}&-6&4&4&2.
\end{array}
\]

Full 選 \(F\)，true value \(9\)。drop-3 的 \(A_1+A_2\) 選 \(P_{12}\)，true value \(2\)；其他兩個 drops 類似，因此三個 FULL-minus-DROP 都是 \(7>0\)。但 \(A_1\) singleton 選 \(S\)，true value \(3\)，所以 \(A_1+A_2\) 的 pair \(P_{12}\) 反而比 \(A_1\) singleton 差。這直接回答 package 中 pair-vs-singleton 診斷的解讀問題：

> **pair-versus-singleton 負值並不在邏輯上排除三個 FULL-minus-DROP 全正。**

不過實際網路用的是 approximation。若

\[
\widehat A(s,a)=\sum_i\widehat A_i(s,a)
\]

且

\[
\|\widehat A-A_{\mathrm{EE}}\|_\infty\le\epsilon,
\]

則 \(\hat a=\arg\max\widehat A\) 只保證

\[
A_{\mathrm{EE}}(a^\star)-A_{\mathrm{EE}}(\hat a)
\le2\epsilon.
\]

證明只有三步：

\[
A(a^\star)
\le
\widehat A(a^\star)+\epsilon
\le
\widehat A(\hat a)+\epsilon
\le
A(\hat a)+2\epsilon.
\]

若三個 head 的 sup-norm errors 分別為 \(\epsilon_i\)，最保守地有 \(\epsilon\le\sum_i\epsilon_i\)。這說明一件對本案很關鍵的事：**只要 genuine marginal action gap 與 approximation error 同量級，FULL-minus-DROP 的 sign 就沒有理論保證。**

「double counting」也可形式化。例如真實 decision difference 是 base \(+1\) 加上一份 externality \(-0.6\)，所以真正差為 \(+0.4\)，應選 action \(x\)。若 Q2、Q3 錯誤地都學到同一份 \(-0.6\)，直接 sum 變成

\[
1-0.6-0.6=-0.2,
\]

argmax 反轉。這不是「三-head 不行」，而是**target bookkeeping 沒有 non-overlap**。在 exact decomposition 中，重複一項必須有另一項補償；在 learned approximate decomposition 中，沒有這種自動守恆，因此 duplicated causal channel 很容易成為 harmful component。

部分觀測也有不可消除的限制。若兩個 latent physical states \(x,x'\) 映射到相同 observation \(o\)，但

\[
A_3(x,a)>A_3(x,b),
\qquad
A_3(x',a)<A_3(x',b),
\]

任何 deterministic \(Q_3(o,a)\) 都無法同時表示兩個正確排序。它至多學 conditional expectation。因此「simulator 內存在真實 externality」和「one-head decision-time state 可識別該 externality」是兩個不同命題。

另外還有最重要的 simultaneous-agent counterexample。假設兩個 agents 都看到同一 snapshot，目前各自在不同 resource。任何一人單獨切到空 beam X，都使 global surplus \(+1\)：

\[
\Delta G_1(\text{switch}\mid a_2=\text{stay})=+1,
\]

\[
\Delta G_2(\text{switch}\mid a_1=\text{stay})=+1.
\]

但若兩人同時依相同 unilateral scorer 切入 X，因 load/interference 非線性，global change 為

\[
\Delta G(\text{switch},\text{switch})=-2.
\]

因此「每個 focal user 對 frozen-background 的 difference reward 都正」**不推出 simultaneous execution 的 joint effect 正**。這是 shared-snapshot decentralized execution 的核心 identifiability risk；MARL 文獻早已指出其他 agents 政策改變會使單 agent 所看到的環境變得 nonstationary，而 replay/off-policy data 又會進一步累積 stale-distribution 問題。Lowe et al. 的 MADDPG 以 centralized training critic 處理這種互動；Foerster et al. 則直接研究 multi-agent replay nonstationarity。這些方法本身不符合你們的固定部署架構，但它們說明這個風險不是 package 特例。citeturn14search0turn15search1

最後要把 ratio-of-sums 與 fixed-\(\lambda\) surplus 分開。Dinkelbach 的經典 fractional-programming 結果指出，若

\[
\eta(x)=\frac{B(x)}{E(x)},\qquad E(x)>0,
\]

在最優 ratio \(\lambda^\star\) 下，可用

\[
B(x)-\lambda^\star E(x)
\]

的 parametric problem 表示 ratio optimum；在 optimum 有對應的 zero-surplus condition。Werner Dinkelbach, *On Nonlinear Fractional Programming*, **Management Science**, 1967, DOI `10.1287/mnsc.13.7.492`。citeturn23search0turn23search4 無線 EE 文獻也直接採用 rate/power fractional programming；例如 Isheden, Chong, Jorswieck & Fettweis, *Framework for Link-Level Energy Efficiency Optimization with Informed Transmitter*, **IEEE Transactions on Wireless Communications**, 2012, DOI `10.1109/TWC.2012.060412.111829`。其範圍是 link-level EE optimization，不是三-head MARL theorem。citeturn23search1

對一個**特定 baseline** \(M\)，若設

\[
\lambda_0=\eta_M=\frac{B_M}{E_M},
\]

則任意 candidate \(C\) 有

\[
\eta_C-\eta_M
=
\frac{B_C-\lambda_0E_C}{E_C}
=
\frac{(B_C-B_M)-\lambda_0(E_C-E_M)}{E_C}.
\]

所以 matched candidate 對該 baseline 的 ratio sign 與 fixed-\(\lambda_0\) surplus sign 完全一致。

但一個 frozen \(\lambda_0\) **不是任意兩個 alternatives 的全域 ratio-order oracle**。例如 \(\lambda_0=1\) 時，

\[
C:(B,E)=(12,10),\quad S_C=2,\quad \eta_C=1.2,
\]

\[
D:(B,E)=(2.1,1),\quad S_D=1.1,\quad \eta_D=2.1.
\]

surplus 會排 \(C>D\)，ratio 卻是 \(D>C\)。因此 package 的 common \(\lambda_0/\kappa\) 很適合做**共同單位與局部 scalar alignment**，卻不能把 current Q1+OPS3+Q3 自動升格成 exact final ratio decomposition。真正的 acceptance 仍必須是 package 已規定的 canonical network ratio-of-sums FULL/DROP evaluation。

## 原始文獻綜合與對本案的限制

**Fractional EE。** Dinkelbach 給的是 ratio 與 parametric surplus 的數學關係，而 Isheden et al. 把這個框架具體放到 wireless rate/power EE 上。這支持你們用 common \(\lambda_0\) 把 bits 與 energy 轉進共同 surplus unit 的方法論方向。它不支持「任意 frozen \(\lambda_0\) 下三個 surrogate heads 的 argmax 必定最佳化最終 episode ratio」。citeturn23search0turn23search1

**Value decomposition。** Sunehag et al. 的 VDN 將 cooperative team value 分解成較簡單的 component utilities；Rashid et al. 的 QMIX 則把 direct addition 擴充成受 monotonicity 約束的 mixing function，藉此維持 centralized/decentralized argmax consistency。這些工作支持「把一個共同 scalar team objective 分解後再做一致 action selection」是正規研究方向；同時 QMIX 的存在也反過來提醒：**純 unweighted additive form 是實質 representational constraint，而不是無損的一般定理。** Sunehag et al., *Value-Decomposition Networks for Cooperative Multi-Agent Learning Based on Team Reward*, AAMAS 2018；Rashid et al., *QMIX: Monotonic Value Function Factorisation for Deep Multi-Agent Reinforcement Learning*, ICML/PMLR 2018。citeturn21search0turn23search2

本案與 VDN 還有一個重要差別：VDN 的出發點是**共同 team reward**。你們若把三個 legacy \(r_1,r_2,r_3\) 直接當三個 heads 的「利益代表」，衝突 reward 很容易使 direct sum 變成多目標投票。相反，若 C1/C2/C3 都重新定義成**canonical scalar EE 的 causal accounting views**，legacy reward conflict 就不再構成形式矛盾。也就是說：

\[
A_{\rm EE}=A_1+A_2+A_3
\]

若成立，談的是 scalar EE；它**沒有**蘊含

\[
\Delta r_1>0,\quad\Delta r_2>0,\quad\Delta r_3>0.
\]

**Advantage/residual representation。** Wang et al. 的 dueling architecture 將 state value 與 action-dependent advantage 分開表示，證明 action discrimination 可以有自己的 representation，而不需把每一項都當成獨立 reward objective。Ziyu Wang et al., *Dueling Network Architectures for Deep Reinforcement Learning*, ICML 2016。其 scope 是單一 Q-function 的 \(V/A\) factorization，不是三項 causal residual theorem；對本案的支持僅限於「action-aligned residual representation 是合理的 function-approximation design」。citeturn10search6

**Difference rewards 與 counterfactual credit。** Wolpert & Tumer 的 difference-utility 思路是用「有 focal agent」與合適 counterfactual baseline 的 global utility 差來隔離 agent marginal contribution。David H. Wolpert & Kagan Tumer, *Optimal Payoff Functions for Members of Collectives*, **Advances in Complex Systems**, 2001, DOI `10.1142/S0219525901000188`。citeturn13search2 COMA 則用 centralized critic 建立「其他 agents actions 固定，對 focal action marginalize」的 counterfactual baseline，處理 cooperative MARL credit assignment。Jakob Foerster et al., *Counterfactual Multi-Agent Policy Gradients*, AAAI 2018。citeturn13search0turn22view1

這兩類工作對 C3 很重要，但只能支持**unilateral marginal-contribution target 的方法論**；它們不能消除剛才的 simultaneous-switch counterexample。尤其 COMA 本身使用 centralized critic，不能直接搬來作你們的部署機制。適合借的是 target semantics：

\[
\text{C3} \approx
G(\text{focal action},\text{fixed background})
-
G(\text{baseline focal},\text{fixed background}),
\]

而不是其 actor-critic architecture。

**Nonstationarity 與 off-policy counterfactual error。** Lowe et al. 指出 multi-agent learning 中，從單一 agent 觀點看其他 agents 的 policy change 會使環境非 stationary；Foerster et al. 的 replay work 專門處理舊 experience 在多 agent policy drift 下變 stale。Fujimoto, Meger & Precup 的 batch/off-policy RL 工作則展示 fixed data distribution 以外的 actions 會產生 extrapolation error。這些來源共同支持：即使 C3 oracle target 是合理的，若 learned Q3 要對 training coverage 外的 action combinations 或由新 Q2 造成的新 state/action distribution 排序，sign 仍可能失真。citeturn14search0turn15search1turn19search0

**Wireless physical externalities。** Siomina & Yuan 的 LTE load-coupling analysis formalizes cell load 與 interference 彼此耦合，說明一個 user/resource allocation 決策對其他 users 的 rate environment 產生 externality 是標準 wireless phenomenon，而不是 package 為 C3 人造的概念。Iana Siomina & Di Yuan, *Analysis of Cell Load Coupling for LTE Network Planning and Optimization*, **IEEE Transactions on Wireless Communications**, 2012, DOI `10.1109/TWC.2012.051512.111532`。其限制是 terrestrial LTE cell model，不會驗證你們的 satellite beam/max-power implementation。citeturn16search17turn22view0

同樣，Auer et al. 的 cellular network energy work 強調網路 energy 不只是 user RF transmit power，而有 substantial infrastructure/equipment contributions。Günther Auer et al., *How Much Energy is Needed to Run a Wireless Network?*, **IEEE Wireless Communications**, 2011, DOI `10.1109/MWC.2011.6056691`。citeturn16search30 這與 package 中 per-beam circuit activation、once-per-active-satellite baseband、PA/supply power 的實作方向一致，但**package 的 exact network-energy law 仍只能由 package code 證明**；Auer et al. 不驗證你們的 max-over-served-user beam-power rule。

總合以上文獻，最穩健的 reconciliation 是：

> **對一個共同 scalar utility 做 additive/residual credit assignment 是方法論上成立的；對 wireless EE 而言，non-focal congestion/interference externality 也是真實的物理 channel。真正未解的是：能否在你們固定的 local/shared-snapshot architecture 下，把那個 channel 做成不 double-count C1/C2、又能抵抗 simultaneous-agent cross-terms 的 action-aligned Q3。**

## 專案映射：C1、C2 已覆蓋什麼，C3 還剩什麼

package 的 causal chain 很有助於回答這一題。`source/env/step.py` 將一個 joint decision 的主要物理路徑寫得相當清楚：

\[
\text{actions}
\rightarrow
\text{per-link recurrence power}
\rightarrow
\text{feasibility/service}
\rightarrow
\text{loads/activation}
\rightarrow
\text{beam max RF power}
\rightarrow
\text{interference/SINR}
\rightarrow
\text{rate}
\rightarrow
\text{network power/rewards}.
\]

【專案證據：`source/env/step.py`; `fable-cleanroom-lane/audit/ee-causal-map.md`】

### C1 已經佔掉 opening energy，不能讓 C3 再拿一次

較早的 exact surplus target code 最有解釋力。在 offset \(0\)，focal action 是 intervention，因此 code 定義：

\[
Z_{1,0}(a)
=
\Delta B_{u,0}(a)
-
\lambda_0\Delta E_{0}^{\rm network}(a),
\]

而 non-focal opening contribution 是

\[
Z_{3,0}(a)
=
\Delta B_{-u,0}(a)
=
\Delta t\sum_{v\ne u}\Delta R_{v,0}(a).
\]

`ee_surplus_targets.py` 明確把**所有 opening system energy change 給 Z1**，使 Z3 是 rate-only、因此對 \(\lambda\) invariant；原始 code 還檢查

\[
Z_1+Z_2+Z_3
=
\text{matched fixed-}\lambda\text{ system surplus}.
\]

【專案證據：`source/runtime/ee_surplus_targets.py`】

所以若新的 C3 再包含「candidate beam activation energy」「satellite baseband energy」「PA energy」等項，會直接與 C1 的 opening network-energy accounting 重疊。**activation-power 是一個真實 externality，但在你們目前 accounting ownership 下，它不是新的 C3 殘差；它是 C1 已擁有的 energy term。**

### current OPS-3 C2 已經佔掉 future focal/persistence energy view

current exact OPS-3 的核心不是未來 system-total EE，而是 focal projected persistence。對 \(h=1,\ldots,H\)，它使用 deterministic cloned orbital/D2 projection、candidate persistence、projected required focal power、frozen non-focal background，再形成近似

\[
\widehat Z_{2,h}(a)
=
\chi_h(a)\Delta t
\left[
\widehat R_{u,h}(a)
-
\lambda_0\widehat P^{\rm marg}_{h}(a)
\right]
-
(1-\chi_h(a))\kappa,
\]

最後對 future offsets averaging、Main-reference centering，再以 common \(\kappa\) 進入 action surface。【專案證據：`source/runtime/ee_axis_ops3.py`; `docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md`】

其中 canonical marginal network power 會反映 existing beam 的 max-power leadership、新 beam circuit activation，以及 previously inactive satellite 的 baseband activation。【專案證據：`source/runtime/ee_axis_ops3.py`】因此 C3 也不應再把這些**projected future energy costs**計一次。

而 current OPS-3 **沒有把 future non-focal rate delta 納進來**。這是最重要的 leftover：

\[
\boxed{
\widehat{\Delta B}_{-u,h}(a)
=
\Delta t\sum_{v\ne u}
\left[
\widehat R_{v,h}^{(+u,a)}
-
\widehat R_{v,h}^{(-u)}
\right].
}
\]

因此從 causal bookkeeping 看，C1/C2 留下最自然的第三軸不是另一個 focal metric，而是：

\[
\textbf{spatial non-focal rate externality}.
\]

這個 externality 有兩個直接來源：

1. **same-beam load/congestion**：focal user 加入 beam，其他 users 的 bandwidth share 改變；
2. **interference/max-beam-power externality**：focal link 成為 beam RF-power max、啟動新 radiating beam，或改變 radiating footprint，導致其他 links 的 SINR/rate 改變。

這兩條路徑都直接存在於 package simulator causal graph。【專案證據：`source/env/step.py`; `fable-cleanroom-lane/audit/ee-causal-map.md`】外部 load-coupling literature 也支持它們作為一般 wireless externality，但不證明 package-specific magnitude。citeturn16search17

### 哪些東西不應被偷塞進 C3

**Immediate physical externality** 是 action 在同一 committed/frozen background 下造成的 non-focal rate change。這是合理 C3。

**Later policy cascade** 則是：本次 action 改變 association/segment/incumbency/observation，接著其他 agents 或 focal user 在未來做出不同 policy action，最終改變 EE。這當然可以是 total causal effect 的一部分，但它取決於未來 policy，而且 package 的 OPS-3 contract 有意不呼叫 future learned-policy output。【專案證據：`docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md`】在「不得 coordinator、不得 second decoder」的前提下，把它硬稱為一個精確、可觀測 C3 反而不 defensible。

**reward-only handover quantity** 也不是 canonical EE residual。package causal map 顯示 handover penalty 進 legacy reward，但 canonical network \(B/E\) 沒有獨立 handover-energy/transient term。【專案證據：`fable-cleanroom-lane/audit/ee-causal-map.md`】因此 handover reward 本身不能為了「第三 head 要有東西」而塞進 C3。只有 handover 實際造成的 future rate/power/service consequence 才能經真正物理 channel 影響 EE。

### 為什麼 victim-burden C3 可以為負，而 spatial channel 仍真實

current V0.4 C3 state 的關鍵不是 current-action counterfactual externality，而是**previous committed slot 的 non-focal served-rate burden**，按 candidate beam/satellite key 聚合，再映射成 action features；它刻意不使用 current joint outcome。【專案證據：`source/runtime/ee_axis_v04_c3_state.py`】因此它觀測的是近似：

\[
\text{「這個 beam/satellite 上一槽有多少 victim burden」}
\]

而真正需要的是：

\[
\text{「這個 focal action 現在會使哪些 victim 的 rate 改變多少」}.
\]

兩者在慢變、低 simultaneous churn 的 regime 可以相關，但不是同一 causal estimand。尤其 package 自己指出 realized current SINR 與 pre-action candidate SINR 使用不同 radiating context；current action 會先改 loads/activation/power，再改 interference。【專案證據：`source/env/step.py`】

所以 observed C3 negativity 可以有至少三個普通原因，而不需要假設「spatial externality 是假的」：

**第一，lag mismatch。** 上槽 victim burden 是 exposure proxy，不是 marginal effect。

**第二，new-Q2 distribution shift/cannibalization。** C2 改變 selected actions 後，C3 進入以前較少出現的 action/state region；old C3 可能曾經是在 harmful old-Q2 context 中補償錯誤，而不是獨立提供有益 spatial credit。這一點與 package 所報告「old C3 的約 \(+21\%\) confirmations 均含 old harmful Q2，而 Q2-free 的 Q1+Q3 約 \(-10\%\) 兩次」相符，但仍只是 project-specific inference。【專案驗證事實：`START-HERE.md`】

**第三，simultaneous aliasing。** 各 agent 共用 pre-action snapshot 時，一個「高 victim burden beam」feature 並不知道其他 agents 同步會離開、加入或提高 beam max power。因此它可能系統性過罰或漏罰。

換句話說，現有 evidence 比較像是**C3 observation/estimand mismatch**，而不是「第三個 scalar-aligned physical contribution 在結構上不存在」。

## 排名後的 C3 候選設計

| 排名 | 機制 | 物理 estimand 與 sign | 類型與 C1/C2 non-overlap | 主要風險 |
|---|---|---|---|---|
| **首選** | **Projected Non-Focal Physical Externality Residual (PNFER)** | focal candidate 對所有 non-focal users 造成的 rate-bit change；相對 no-focal insertion 通常 \(\le0\)，Main-centered action difference 可正可負 | frozen-shadow **difference reward / residual surrogate**；只有 non-focal bits，不重複 C1/C2 energy | simultaneous-agent cross-terms；需要比 victim burden 更充分的 victim-sensitive state |
| **次選** | **Beam-Max Interference Externality** | 只算 candidate 抬高 beam max RF / 新增 radiating beam 後，其他 users 的 SINR-rate loss；raw effect \(\le0\) | narrow physical difference reward；排除 load term、排除 energy term | 可能太窄，錯失大部分同 beam bandwidth congestion |
| **第三** | **Bandwidth-Congestion Externality** | 只算 focal occupancy 使 candidate beam load denominator 增加所造成的 non-focal rate loss | narrow difference reward；固定 interference/power，和 C2 recurrence energy 清楚分離 | herding 最嚴重；多人同時看相同 beam load 時 unilateral estimate 容易失真 |

**首選 PNFER** 的理由是它最貼近舊 V0.3 exact accounting 中 C3 的原始科學角色，但把「上一槽 victim burden」改成「action-caused rate externality」，並把 current OPS-3 的 projected physical geometry 延伸到 non-focal victims。它不需要 coordinator、不改最終 decoder、不改 \(\lambda_0\)、不把 Q3 反號，也不靠 route-specific weights。

**Beam-Max Interference Externality** 是很好的 falsification reserve。package 的 beam RF power 是 served users required powers 的 max，因此一個 focal action 若跨越 background max，就可能產生離散的 interference leadership effect。【專案證據：`source/env/step.py`; `source/runtime/ee_axis_ops3.py`】這比 generic victim burden 更 causal，而且與 wireless interference-coupling literature 一致。citeturn16search17 但它故意忽略 same-beam bandwidth sharing，所以比較像「T4-like mechanism probe」，不應先當完整 C3。

**Bandwidth-Congestion Externality** 最容易解釋，但我排第三。它把 radiating powers/interference 固定，只問「focal 多佔一個 beam load slot，使 incumbent non-focal users 各損失多少 rate」。這會給很乾淨的 nonpositive raw difference reward，但 simultaneous migration 最容易造成 nonlinear occupancy error；多 agent 同時往同 beam 移動時，每個人都基於相同 \(n\) 評估 \(n\to n+1\)，真正結果卻可能是 \(n\to n+k\)。

我**不建議**把「handover burden」「future option value」「政策 cascade」列為現在的 C3 前三名。它們比較難與 canonical \(B/E\) 建立直接 non-overlap accounting，而且後兩者比 PNFER 更依賴未觀測 future joint policy。那會把目前可解的 physical residual 問題變成更大的 counterfactual-control 問題。

## 推薦 C3 的完整公式、部署狀態與無訓練 falsification

推薦定義一個 **Projected Non-Focal Physical Externality Residual**。

令 focal user 為 \(u\)，其 legal candidate action 為 \(a\)，Main/reference action 為 \(a_u^M\)。在每個 decision offset \(h\)，建立一個**由當前 committed pre-action snapshot 產生的 focal-removed background**

\[
\mathcal G_{t,h}^{-u}.
\]

對 \(h=0\)，使用當前 committed physical associations/powers/loads；對 \(h>0\)，採與 exact OPS-3 相同的 deterministic orbital/visibility/persistence clock，但**不讓 non-focal agents 執行未來 learned actions**。也就是說，這是 frozen-background shadow，而不是 future-policy rollout。

令 focal candidate 在 offset \(h\) 的 persistence indicator 與 projected required power 為

\[
\chi_{u,a,h}\in\{0,1\},
\qquad
\widehat p_{u,a,h}.
\]

它們直接沿用 C2 的 physical semantics，避免 C2/C3 對「candidate 是否還存在」各自發明不同世界。

對每個 non-focal served user \(v\neq u\)，background rate 為

\[
\widehat R_{v,h}^{-u}
=
\frac{W_{b(v)}}{N_{b(v),h}^{-u}}
\log_2
\left(
1+\widehat\gamma_{v,h}^{-u}
\right).
\]

插入 focal candidate \(a\) 後，若其持續存在，

\[
N_{b,h}^{+a}
=
N_{b,h}^{-u}
+
\chi_{u,a,h}\,
\mathbf 1\{b=b(a)\},
\]

而 candidate beam 的 radiated RF power 按 simulator 的 canonical max rule 更新：

\[
P_{b(a),h}^{+a}
=
\max
\left(
P_{b(a),h}^{-u},
\chi_{u,a,h}\widehat p_{u,a,h}
\right).
\]

若是新 active beam，則把它加入 radiating set。接著用 canonical interference law 重新計算每個 non-focal victim 的

\[
\widehat\gamma_{v,h}^{+a}
\]

與

\[
\widehat R_{v,h}^{+a}
=
\frac{W_{b(v)}}{N_{b(v),h}^{+a}}
\log_2
\left(
1+\widehat\gamma_{v,h}^{+a}
\right).
\]

C3 在 offset \(h\) 的 raw causal externality 定義為

\[
e_{3,h}(s,a)
=
\Delta t
\sum_{v\neq u}
\left[
\widehat R_{v,h}^{+a}
-
\widehat R_{v,h}^{-u}
\right].
\]

在固定 non-focal associations、monotone interference 與 bandwidth-sharing 模型下，這個 **insertion effect** 應為非正：

\[
e_{3,h}(s,a)\le0.
\]

這不是說 Q3 必須為負。不同 candidate 的傷害不同；Main-centering 後，「比 Main 少傷害 victims」自然得到正 action preference。

為了避免把 horizon 長度本身變成偷偷的 Q3 rescaling，採一次簡單的 offset mean：

\[
Z_3(s,a)
=
\frac{1}{H_t+1}
\sum_{h=0}^{H_t}
e_{3,h}(s,a).
\]

最後與 package 的 gauge/unit conventions 相容：

\[
\boxed{
Q_3^\star(s,a)
=
\frac{
Z_3(s,a)-Z_3(s,a_u^M)
}{\kappa}.
}
\]

這裡**沒有 \(-\lambda_0\Delta E\) 項**。原因不是 energy externality 不存在，而是 opening 與 projected future network-energy consequences 已分別由 C1/C2 ownership 接走；把 beam activation/baseband/PA energy 再放進 C3 是 double counting。由於 numerator bits 本來就是

\[
B-\lambda_0E
\]

中的一個同單位加數，rate-only \(Z_3\) 與 common \(\lambda_0/\kappa\) 系統仍具 unit compatibility。

固定部署規則完全不變：

\[
\boxed{
a_u^{\rm exec}
=
\arg\max_{a:\,m_u(a)=1}
\left[
Q_1(s,a)+Q_2(s,a)+Q_3(s,a)
\right].
}
\]

沒有 coordinator、auction、veto、route weight、second decoder、post-training correction，也不需要對 Q3 做 sign reversal 或乘上額外 coefficient。

但必須把一點寫進 method claim：上述 \(Z_3\) 是 **difference reward / projected residual surrogate**，不是 true realized multi-agent \(A_{\rm EE}\) 的 exact third component。因為 future non-focal policies 被 frozen，而且 current OPS-3 自身也使用 offset averaging 與 outage penalty，所以目前的

\[
Q_1+Q_2+Q_3
\]

應被描述成**三個 common-unit scalar-aligned physical views**，不能宣稱重建 exact future network EE advantage。

**Decision-time Q3 state** 不應再只是 previous-rate burden。至少要 action-align 到能辨識 causal derivative 的 inputs：candidate physical beam/satellite identity、candidate persistence/required-power projection、candidate-beam current background load、background beam RF max 與 focal-to-max gap、新 beam/active-beam indicator，以及會受該 candidate interference footprint 影響的 non-focal victim summaries。這些輸入必須都由 decision-time committed snapshot 與 deterministic projection產生；不應使用 realized selected-action outcome、future learner action 或依 outcome 選 source。這符合 outcome-independent Catfish source 的要求。

這個設計不能「保證沒有 herding」；任何聲稱能在無 joint coordination 下完全消除 simultaneous cross-terms 都過度承諾。它能做到的是把錯誤界線畫清楚：Q3 估的是**unilateral physical externality against a committed background**，並讓 feature 本身 victim-與action-specific，而不是把所有 agents 都引向同一個 coarse previous-burden ranking。difference-reward 文獻支持這個 counterfactual credit semantics，但同樣沒有給 simultaneous joint-optimality guarantee。citeturn13search2turn13search0

**最低限度的 no-training oracle test** 應直接測這個科學假說，而不是先訓 Q3：

首先，pre-register PNFER 的全部公式、horizon、background convention、Main centering、\(\kappa\)、victim eligibility 與 tie rules，之後不得依結果改 sign、weight、rung、seed、horizon 或 threshold。

其次，在既有允許的 TRAIN-development oracle framework 中，對所有 legal actions 建立 \(Q_3^\star\)，與凍結的 Q1 與候選 Q2 surface 直接做

\[
Q_1+Q_2+Q_3^\star
\]

同一 mask、同一 argmax，最後**只用 canonical ratio-of-sums \(\eta=B/E\)** 計算：

\[
\eta_{123}-\eta_{12},
\quad
\eta_{123}-\eta_{13},
\quad
\eta_{123}-\eta_{23}.
\]

服務 guard 必須保持原規格；不能用 fixed-\(\lambda\) target gain 取代 final EE acceptance。

第三，增加一個不屬於 acceptance-rescue、而是**mechanism falsification** 的 matched diagnostic：

\[
y^{\rm true}_{3,0}(a)
=
\Delta t
\sum_{v\neq u}
\left[
R_{v,0}^{(+u,a)}
-
R_{v,0}^{(-u)}
\right].
\]

檢查 PNFER 的 h=0 shadow 是否對 true matched one-step non-focal externality 有正確 action ordering。若連 h=0 的 causal channel 都不能由 decision-time representation 分辨，沒有理由進 learner。

第四，專門做 simultaneous cross-term stress diagnostic。對同一 snapshot 中多個 focal agents 若其 individual oracle 都傾向同一 beam，量：

\[
\mathcal I
=
\Delta B_{\rm nonfocal}^{\rm joint}
-
\sum_u
\Delta B_{\rm nonfocal}^{\rm unilateral,u}.
\]

若 \(\mathcal I\) 系統性大到**反轉 individual C3 所偏好的 joint direction**，那就不是增加 data 或更久 training 可修好的普通 approximation 問題，而是 fixed shared-snapshot architecture 下的 interaction identifiability 問題。

**硬 stop rule 應是：**使用目前已凍結的 project FULL/DROP acceptance gate，不降低 threshold。只要 oracle PNFER 在 fixed \(Q_1+Q_2+Q_3\) architecture 下仍不能取得正的 C3 FULL-minus-DROP，或為了取得它必須犧牲既有 C1/C2 binding marginals、改 final EE formula、改 sign/scale、挑 seed/rung，**就不要訓 Q3**。這已足以在昂貴 training 前否證「這個 C3」；不應再用 learner variance 解釋一個 oracle-level complementarity failure。

更強的**三-Catfish thesis falsifiers**有四類：

1. **Residual absence：**在 current physical simulator 中，non-focal causal residual 對 legal actions 幾乎沒有 decision-relevant spread；那第三個 independent physical axis 實際上不存在。
2. **Observation non-identifiability：**相同 pre-action Q3 observation 經常對應相反的 true non-focal action ordering；單一 action-aligned Q3 不可能精確學它。
3. **Joint cross-term domination：**unilateral PNFER 在 shared snapshot 下的排序經 simultaneous execution 穩定反轉；無 coordinator architecture 無法把它當 reliable local contribution。
4. **Oracle complementarity failure：**即使給 Q3 真實/高保真 PNFER oracle surface，固定 unweighted \(Q_1+Q_2+Q_3\) 還是 C3 marginal \(\le0\)。這會直接表示「此物理 residual 雖存在，卻不是目前 C1+C2 decision geometry 中可產生第三正 marginal 的資訊」。

目前最大 research gap 不是「三頭數學上行不行」，而是第 2–4 點尚未對 proposed PNFER 做過封存 oracle screen。尤其 package 已明確說 current exact OPS-3 的 outcome 尚未開；Fable O-arm 不能冒充 exact OPS-3 result。【專案驗證事實：`START-HERE.md`; `INTEGRATION-VERIFICATION.md`】因此現在不應聲稱 C2 已被「選定」，更不應用 Fable \(+9.480\%\) 當 exact OPS-3+C3 redesign 的基準 efficacy。

## Claim-to-source ledger、研究缺口與最終分類

| 類型 | 核心 claim | 主要依據 | Scope limitation |
|---|---|---|---|
| **形式結果** | exact \(A_{\rm EE}=A_1+A_2+A_3\) 時 full argmax 對任何 drop-one action 的 true scalar value 非劣 | 本報告直接 argmax proof | pointwise/common-continuation；若 heads 只是 surrogate，不自動成立 |
| **形式結果** | 三個 strictly positive FULL-minus-DROP 可同時存在；pair 也可比 singleton 差 | 本報告有限 action-set constructions | existence proof，不代表 simulator 一定有相同 geometry |
| **原始文獻** | ratio objective 可在適當 multiplier 下轉為 parametric surplus | Dinkelbach, *On Nonlinear Fractional Programming*, 1967, DOI `10.1287/mnsc.13.7.492` citeturn23search0 | 不保證任意 frozen \(\lambda_0\) 排序所有 policy alternatives |
| **原始文獻** | wireless EE 可用 rate/power fractional-programming framework | Isheden et al., IEEE TWC 2012, DOI `10.1109/TWC.2012.060412.111829` citeturn23search1 | link-level framework，不證三-head decomposition |
| **原始文獻** | additive/monotone value factorization 對共同 team value 有方法論基礎 | Sunehag et al., VDN, AAMAS 2018；Rashid et al., QMIX, ICML 2018 citeturn21search0turn23search2 | MARL agent factorization；不保證各 component strict marginal |
| **原始文獻** | counterfactual/difference utility 可用來定義 focal marginal contribution | Wolpert & Tumer 2001, DOI `10.1142/S0219525901000188`; Foerster et al., COMA, AAAI 2018 citeturn13search2turn13search0 | 通常固定/邊際化 others；不解 simultaneous nonlinear interaction |
| **原始文獻** | simultaneous learning與 stale/off-policy data 造成 nonstationarity/extrapolation risk | Lowe et al. 2017；Foerster et al. 2017；Fujimoto et al. 2019 citeturn14search0turn15search1turn19search0 | 一般 MARL/batch-RL evidence，不是此 simulator efficacy result |
| **原始文獻** | wireless load 與 interference 形成 non-focal externality | Siomina & Yuan, IEEE TWC 2012, DOI `10.1109/TWC.2012.051512.111532` citeturn16search17 | terrestrial LTE model，不驗證 satellite implementation magnitude |
| **專案驗證事實** | fresh TRAIN development 中兩個 C2 directions 正、C1 正、frozen C3 兩個新-Q2 context 均負 | `START-HERE.md`; `INTEGRATION-VERIFICATION.md` | oracle/development signs；非 learned、非 held-out efficacy |
| **專案驗證事實** | old V0.3 曾有 C1 opening focal+energy、C3 opening nonfocal、C2 later system-surplus identity | `source/runtime/ee_surplus_targets.py` | 舊 target accounting；不是 current OPS-3 |
| **專案驗證事實** | current OPS-3 是 focal projected-persistence/rate/marginal-power/outage prior，未含 future non-focal rates | `source/runtime/ee_axis_ops3.py`; OPS-3 formula contract | frozen-background projection；不是 realized future total effect |
| **專案驗證事實** | current C3 state 主要由 previous committed non-focal beam/satellite rate burden 組成 | `source/runtime/ee_axis_v04_c3_state.py` | 是 predictor/state design，不等於 causal current externality |
| **推論** | repeated negative C3 更支持 current victim-burden proxy mismatch/cannibalization，而非「spatial C3 不存在」 | 上述 package causal code + development contrasts + wireless externality literature | 尚需新 C3 oracle falsification |
| **提案** | PNFER 是最乾淨的第三軸：non-focal bits-only、action-caused、frozen-shadow difference residual | 本報告公式 | 未在 package 中實作或評估；不能宣稱 efficacy |

整體信心可以分層表述，而不需要虛構數值機率。

**對 function-space possibility：高信心。** 有直接 construction；不存在「三個 strict marginals 天生互斥」的數學障礙。

**對 simulator 中 spatial residual 的存在：高信心。** package code 明確含 beam load、beam max RF、interference、SINR、rate 的 current-action causal channel；外部 wireless literature 也支持這類 externality 的一般性。citeturn16search17

**對 proposed PNFER 的 unilateral identifiability：中等至中高信心。** 所需的 committed associations/powers、candidate physical identity、load/activation、projected geometry 等大部分已有 causal path；但 package 尚未證明一個固定 Q3 observation 能充分表示 victim-specific rate response。

**對「學成後三個 binding marginals 都嚴格正」：目前只能中低到中等信心，且不能升格。** 關鍵 gap 是新的 PNFER oracle 本身尚未通過 fixed unweighted FULL/DROP test；更沒有 learned/held-out evidence。

因此最合理的 scientific disposition 不是放棄第三頭，也不是宣稱三頭已被證明，而是：

**保留三-head thesis 作為一個可嚴格 falsify 的 scalar-aligned search hypothesis；把現有 victim-burden C3 視為失敗機制，不把它的負號推廣成所有 spatial C3 的不可能性；下一個 C3 必須直接估 action-caused non-focal physical rate residual，並先接受 no-training oracle 與 simultaneous-cross-term falsification。**

THREE_HEAD_POSSIBLE_BUT_C3_IDENTIFIABILITY_UNRESOLVED