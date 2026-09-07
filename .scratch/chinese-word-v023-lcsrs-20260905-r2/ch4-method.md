# 4. Multi-Catfish Reinforcement Learning (MCRL)

## 4.1 Method Overview

第三章給出衛星、波束、角度、功率、SINR、throughput 與系統耗能的物理鏈。本章在該鏈上定義 current method：保留 MODQN 的候選表與原生 safe mask，將 Main 的唯一最終目標對齊為 network ratio-of-sums energy efficiency，並以恰好三個獨立 Q surface 表達三條不同來源的決策訊號。它們不是三個 legacy reward 的投票，也不是三個部署代理。

低軌衛星持續移動，每位使用者可選的實體波束會改變，但網路輸出長度必須固定。因此，每位使用者使用一張固定長度的候選表。表中保留 $L_w$ 顆可見衛星，每顆衛星提供 $J_w$ 個候選波束，共有 $C=L_wJ_w$ 個位置。令 $\mathcal{C}=\{1,\ldots,C\}$ 為候選編號集合，$c\in\mathcal{C}$ 表示表中的一個位置。

候選表的內容會隨時間更新。$b_u(c,t)\in\mathcal{S}\times\mathcal{V}$ 表示候選位置 $c$ 在時間 $t$ 對使用者 $u$ 所對應的實際衛星與波束。網路輸出的是候選編號，環境套用動作時，再由 $b_u(c,t)$ 回到第三章的衛星－波束索引。這個映射只改變固定輸出槽位，不改變物理鏈的定義。

沿用 MODQN 的原生 predecision state，可將候選順序下的資訊寫成

$$
\begin{aligned}
s_u(t)&=\mathrm{concat}\!\left(
x_u(t-1),
\big(\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_3)\big)_{\substack{(s,v)=b_u(c,t)\\c\in\mathcal{C}}},
\big(\theta_{u,s,v}(t)\big)_{\substack{(s,v)=b_u(c,t)\\c\in\mathcal{C}}},
N_u(t-1)\right).
\end{aligned}
\tag{4.1}
$$

其中 $x_u(t-1)$ 記錄前一步連線，兩個序列依候選順序排列鏈路 SINR 與偏軸角，$N_u(t-1)$ 記錄候選對應的前一步負載資訊。式 (4.1) 只描述動作前可取得的 native observation；本步動作造成的連線、負載、throughput、energy 與 active set 不能回寫成同一步的輸入。Q1 與 Q2 使用其已認證的原生輸入；C3 另外只讀取捕獲後 detached 的 Q1+Q2 描述，不直接把觀測 SINR 或任何 profile outcome 當成 C3 特徵。

候選表的長度固定，但部分位置在當下可能不可用。以 $m_{u,c}(t)$ 表示 native safe-mask 分量：

$$
m_{u,c}(t)\in\{0,1\},\qquad
\mathcal{A}_u^{+}(t)=\{c\in\mathcal{C}\mid m_{u,c}(t)=1\}.
\tag{4.2}
$$

其中 $\mathcal{A}_u^{+}(t)$ 是使用者 $u$ 在時間 $t$ 的 safe action set；上標 $+$ 只表示已通過原生安全條件。使用者選出的候選編號為 $a_u(t)$，其 one-hot 表示為

$$
a_u(t)\in\mathcal{A}_u^{+}(t),\qquad
a_{u,c}(t)=\mathbf{1}\!\{c=a_u(t)\},\quad c\in\mathcal{C}.
\tag{4.3}
$$

當 safe action set 為空時，該使用者不執行候選動作；這個 no-op 由 native environment contract 處理，不由 C3 另加 fallback。全體使用者在同一時間步的動作可記成 roster vector

$$
a(t)=\big(a_1(t),a_2(t),\ldots,a_U(t)\big),
\tag{4.4}
$$

但此向量只是同一步各使用者 action 的集合，不是 joint decoder、協調器或第二次決策。物理連線、波束啟用與能耗仍依第三章的式 (3.1)–(3.17) 計算。

## 4.2 Three Independent Q Surfaces and Main Objective

本稿固定恰好三個獨立 Q surface：$Q_1$、$Q_2$ 與 $Q_3$。它們各自保留 route-specific 的學習來源與表示邊界，輸出先轉入共同的 normalized bits-per-$\kappa$ 單位，再在部署端直接相加。沒有額外的 Q head、pair decoder、allocation vector 或後選擇分支。

在每個 native anchor，先由固定 Q1+Q2 的 inference-mode 分數得到 detached reference action。這個 reference 用來建立 C3 的相對描述，不是最終部署動作。完成三路分數計算後，Main 對每位使用者只做一次 masked argmax：

$$
a_u^\star(t)=\arg\max_{a\in\mathcal{A}_u^{+}(t)}
\left[Q_1\!\left(s_u(t),a\right)+Q_2\!\left(s_u(t),a\right)+Q_3\!\left(s_u(t),a\right)\right].
\tag{4.5}
$$

式 (4.5) 是無權重的 row-wise sum 與單次 argmax。它不執行 coordinator、auction、vote、matching stage、joint decoder、iterative allocation、retry、fallback 或 post-selection repair。Main 的最終評估以 network ratio-of-sums EE 表示：對完整評估範圍，將所有 delivered bits 加總後除以所有 network energy 加總；不可改成 per-row EE 的平均，也不可把三路分數解讀成三個 reward 的多數決。

## 4.3 Shared Current-Slot Counterfactual and Route Roles

三路學習共用同一個 predecision anchor 與 safe action domain，但不共用 privileged outcome。令 $x^0$ 表示 detached reference profile，並令 $x$ 表示同一 anchor 的 candidate profile。共享的 network surplus 記為

$$
G(x)=\sum_{u\in\mathcal{U}}B_u(x)-\lambda E(x),
\tag{4.6}
$$

其中 $B_u(x)$ 是 profile $x$ 中使用者 $u$ 的 delivered bits，$E(x)$ 是該 current-slot profile 的 network energy，$\lambda$ 是凍結的 bits-per-joule multiplier。此式只作 current-slot counterfactual 的共同會計基礎；ratio-of-sums EE 的正式評估仍以整個評估範圍的總 bits 與總 energy 計算。

### C1：focal current-slot own-rate 與 network-energy surplus

C1 以 focal user 的 current-slot own-rate 為核心，同時納入完整 opening-step 的 marginal network-energy surplus。它比較同一 predecision anchor 下 reference 與 candidate 的網路物理變化，讓角度感知發射功率、干擾、throughput 與共同系統能耗沿用第三章的單一物理鏈。C1 的 source 只在 action opening 的完整步驟上形成，不能以只看 focal rate 的局部 proxy 取代。

RIS EXP 與 ACRM 僅保留為此路線的 training-source／comparison lineage；它們不是本稿的 active deployment mechanism，也不能用來宣稱 C1 已具有效能。C1 的 qualification 與任何 efficacy 結論留待獨立實證。

### C2：固定 OPS-3 projected-persistence route

C2 目前固定為 OPS-3 projected-persistence route。它在本稿中是 present but empirically unqualified：保留作為第二個獨立 Q surface 的 route-specific context，但不沿用舊 r2／handover objective 的敘事，不宣稱已定案有效，也不自行發明替代 C2。C2 的狀態、目標與 inference provenance 必須和 C1、C3 分開記錄。

### C3：two-user LC-SRS route

C3 專門表達兩位使用者在同一 current slot 的 Local Coalition-Shapley Spatial Residual Surplus。它的 teacher 使用完整四-profile physical counterfactual；student 只使用可在 action 前捕獲的 deterministic relational descriptors。這個分工讓 C3 能表示 shared source、兩個 designated destinations 與非成員關係，又不把 privileged profile outcome 帶入部署輸入。

## 4.4 Exact Two-User LC-SRS Teacher

對每一個已由 predecision topology enumeration 確定的 two-user pair，使用四個 matched current-slot profiles。令

$$
x^0=00,\qquad x^1=10,\qquad x^2=01,\qquad x^c=11,
\tag{4.7}
$$

其中 00 表示兩位成員都維持 reference，10 表示 member 1 移動、member 2 維持 reference，01 表示 member 2 移動、member 1 維持 reference，11 表示兩位成員同時移動。除了這兩位成員外，pair-local profile 不改變其他使用者；同一 matched random field 供四個 profile 使用。

對 ordered member $i\in\{1,2\}$，定義 unilateral local term、non-focal externality 與 partial surplus：

$$
\begin{aligned}
\ell_i
&=B_i(x^i)-B_i(x^0)-\lambda\left[E(x^i)-E(x^0)\right],\\
e_i
&=\sum_{\substack{u\in\mathcal{U}\\u\ne i}}
\left[B_u(x^i)-B_u(x^0)\right],\\
d_i&=\ell_i+e_i.
\end{aligned}
\tag{4.8}
$$

再將兩位成員共同移動相對於兩個 unilateral profiles 的 bits 與 energy interaction 分開記為

$$
\begin{aligned}
\Psi_B
&=\left[\sum_{u\in\mathcal{U}}B_u(x^c)-\sum_{u\in\mathcal{U}}B_u(x^0)\right]
-\sum_{i=1}^{2}\left[\sum_{u\in\mathcal{U}}B_u(x^i)-\sum_{u\in\mathcal{U}}B_u(x^0)\right],\\
\Psi_E
&=\left[E(x^c)-E(x^0)\right]
-\sum_{i=1}^{2}\left[E(x^i)-E(x^0)\right],\\
\Psi&=\Psi_B-\lambda\Psi_E.
\end{aligned}
\tag{4.9}
$$

LC-SRS 的 paper target 為

$$
z_{3,i}=e_i+\frac{\Psi}{2},
\qquad
y_i=\frac{z_{3,i}}{\kappa},
\tag{4.10}
$$

其中 $\kappa$ 是三路共用的輸出尺度。對這個嚴格的 two-user current-slot game，label 滿足 exact scoped identity

$$
\sum_{i=1}^{2}\left(\ell_i+z_{3,i}\right)=G(x^c)-G(x^0).
\tag{4.11}
$$

式 (4.11) 只對命名的兩人、四個 current-slot profiles 成立；它不是 general $m$-player coalition、partial-adoption、all-roster、future-trajectory 或 learned-policy decomposition。teacher 在 profile evaluation 前拒絕成員數不是 2 的 topology，不以 $\Psi$ 除以 coalition size，也不提供替代的 m-player attribution。

teacher 的 privileged physical evaluator 只在 training 使用。它保留四個 profile 的 physical receipts、共同 random field 與公式項，先形成每個 member cell 的 matched label，再由 anchor-level assembler 寫入唯一的 teacher surface。reference cells 與 legal-but-unsupported cells 是零值 structural controls；supported member cells 寫入 $y_i$。正負與零的 measured labels 都保留，不以 sign filter、零填補或 post-hoc 選擇刪除 supported cell。

## 4.5 Deterministic Relational C3View and Student

C3View 是在 profile evaluation 前從 immutable captured state 建立的 deterministic relational descriptor。對 focal user $i$ 與候選 action $a$，令 $c_{ia}$ 表示 action context，$t_{iar}$ 表示 focal／partner／相關使用者的 relation token，$m_{iar}$ 表示 native action 與 relation mask。每一個 legal action 都有一個 typed pair-context token；普通 relation token 與 pair-context token 使用同一個 shared scorer。

action context 可包含 candidate 的角度、距離、仰角、opening feasibility、committed load／active state／power、detached reference occupancy，以及 detached Q1+Q2 的 margin 與 rank。relation tokens 可包含 reference source、focal destination、partner destination 的 physical-key／co-channel relation、使用者角色、開啟可行性、detached occupancy、固定幾何與 deterministic coupling descriptors。這些量都從已捕獲的衛星位置、cell center、使用者位置、顏色與固定 link constants 計算；它們不評估 rate、energy、service、active set 或 hypothetical power。

C3View 不讀取 teacher 的 profile fields、fading、label、future action、future association 或 post-action state，不抽取新的亂數，也不直接把 raw observed SINR 當成 token。Q1+Q2 的 detached output 只作為已認證原生 observation 的 inference descriptor，不能把 gradient 傳回 Q1、Q2、mask、topology 或 simulator。raw world、anchor、user、action、satellite 與 beam identifiers 只作 provenance metadata，不進入 learner numeric feature。

student 使用一個同時處理 ordinary 與 pair-context token 的 shared token scorer：

$$
f:[c_{ia},t_{iar}]\in\mathbb{R}^{67}
\longrightarrow64_{\mathrm{ReLU}}
\longrightarrow64_{\mathrm{ReLU}}
\longrightarrow1.
\tag{4.12}
$$

它直接輸出 normalized bits-per-$\kappa$ 單位。令

$$
F_i(a)=\sum_{r:m_{iar}=1}f(c_{ia},t_{iar}),
\qquad
Q_{3,i}(a)=F_i(a)-F_i(a_i^0),
\tag{4.13}
$$

其中 $a_i^0$ 是 detached reference action。reference centering 使 reference output 恆為零；native mask 使 illegal row 與其 tokens 皆為零。C3 的公開輸出只有這一個 scalar $Q_3$ surface，不另輸出 $e_i$、$\Psi$、allocation vector、pair identity、profile selector 或 positive-credit head。

## 4.6 Route-Specific Learning and Deployment Procedure

current method 的 training／deployment boundary 依下列順序固定：

1. 在任何 profile evaluation 前，捕獲每位使用者的 native predecision observation、safe mask、physical keys、committed context 與必要的固定幾何；該捕獲結果對四-profile comparison 保持 immutable。
2. 以 inference-mode Q1 與 Q2 建立 detached reference action 與 reference occupancy；此步不讀取 teacher outcome，也不重抽 native observation。
3. 依 deterministic topology enumeration 找出 exactly-two-member pair，並建立每個 legal action 的 C3View；pair selection 在 outcome 開啟前完成。
4. training teacher 針對每個 pair 評估 00、10、01、11 matched profiles，計算式 (4.8)–(4.11) 的 scoped label 與 physical identity。
5. 將每個 anchor 組成一個 unique teacher surface：reference cells、unsupported legal cells 與 masked cells 分別保留其 control／receipt role，supported member cells 僅寫入一次 label。
6. 以 route-specific source fit 三個 Q surface。C1、C2 的來源與診斷各自保留；C3 student 只從 C3View teacher surface 與 structural controls 學習，採 reference-centred scalar regression，不使用 Bellman bootstrap。任何 C3 loss 都不更新 Q1、Q2、native state、mask 或物理 simulator。
7. deployment 時在同一份 captured C3View 上評估 Q3 一次，與 Q1、Q2 直接無權重相加，套用式 (4.5) 的 single masked argmax。選後只記錄同一個 action vector 的 physical receipt；不進行第二次 argmax、協調、retry、fallback 或 repair。

這個程序使 privileged teacher、route-specific learner 與 Main deployment 的因果邊界可分別檢查。C3View 的 relational context 是資訊描述，不是額外的 action-selection stage；它也不把 full roster 的 joint decision 移入網路。

## 4.7 Method Status and Claim Ceiling

本章是 current method-aligned draft。可凍結的內容包括 Main-only network ratio-of-sums EE、恰好三個獨立 Q surface、C1/C2/C3 route roles、two-user LC-SRS teacher、deterministic relational C3View、reference-centred scalar Q3 與 single-pass masked argmax。C2 仍是 present but empirically unqualified；C1 的 RIS EXP／ACRM 只屬 lineage／comparison；C3 的 formula 與 interface 也不等同於已觀察到的 learnability 或 composition benefit。

Chapter 5 的既有實驗章不在本次支線改動。因而本稿不宣稱 C1、C2 或 C3 的 efficacy，不宣稱 FULL 大於任何 ablation，不宣稱學習可組合，也不把 current method 描述成 empirical-final。上述效能問題必須在另行凍結的實驗契約下，以可追溯的結果重新判定。
