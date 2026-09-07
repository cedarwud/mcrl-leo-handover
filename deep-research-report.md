# V0.23 R6 後 fresh TRAIN gate 與 LC-SRS／CSE／EC 獨立科學裁決

## Direct answer and decision context

`PROJECT-HANDOFF FACT`　R6 的原始、凍結 sign gate 已經失敗，這點沒有模糊空間：informed Spearman = `0.8367467202782021`，informed raw sign accuracy = `0.8293051359516616`，matched-placebo raw sign accuracy = `0.7915407854984894`，所以 raw gap = `0.03776435045317217 < 0.05`。`1038/(1038+286)=0.78399`，也就是 sign-labelled rows 有 78.4% 為正類。開發期 balanced accuracy `[0.6076,0.7227,0.7047]` 對 `[0.5584,0.5970,0.5807]` 的平均差約 `0.09963`，但它們是 R6 之後才具有決策吸引力的診斷量，因此不能回溯挽救 R6。

`INFERENCE`　78.4% 正類意味著「永遠猜正」在這批 row 上已有約 0.784 raw accuracy；R6 placebo 的 0.7915 只比這個 majority baseline 高約 0.0076，而 informed 高約 0.0453。這不能證明 imbalance 是失敗原因，卻足以說明 raw accuracy 對本問題的「兩種 sign 是否都學得到」並非乾淨 estimand。這正是 balanced accuracy 類指標應在**下一個、全新、前瞻註冊的研究**中被考慮的情境，而不是事後重算 R6 的理由。

`LITERATURE-SUPPORTED PRINCIPLE`　Brodersen、Ong、Stephan、Buhmann 的 *The Balanced Accuracy and Its Posterior Distribution*，IEEE ICPR 2010，明確針對不平衡分類指出 conventional accuracy 可能因 class imbalance 而過度樂觀，並使用 class-conditional accuracies 的平均來平衡兩類貢獻（[DOI 10.1109/ICPR.2010.764](https://doi.org/10.1109/ICPR.2010.764)）。它支持「balanced accuracy 是另一個明確 estimand」，不支持「看完結果後換指標就算原 gate 成功」。citeturn13search15

`INFERENCE`　我的裁決是：**保留 frozen LC-SRS teacher，不自動升級 CSE 或 EC；允許且只允許一次新的 prospective TRAIN gate，把 balanced sign accuracy 預先指定為 learner sign discrimination 的 primary estimand，raw sign accuracy／raw informed-minus-placebo gap 保留為強制可見的 secondary continuity receipt；若這次 balanced gate 失敗，不再進行第二次 metric revision。**這不是 R6 rescue，而是一個新的 estimand、新的 unopened-world confirmatory question。

`PROJECT-HANDOFF FACT`　此判斷也不把兩個 execution 問題誤認成 scientific negative：R6 另有 composition replay-digest/runtime defect；第一次 C1/C2 target generation 在錯誤的 `_network_snapshot` module level、尚未進入 physics 前失敗，且已有經測試的 correction/relaunch。五臂 runner 仍只是 injected-callback admission/receipt skeleton，而不是完整 physical path。這些都不能把 R6 raw predicate 改寫為通過，也不能作為 CSE/EC 的效果證據。

**Research method and source-quality limits**

本次先讀取了指定的 `START-HERE.md`、`CURRENT-STATUS.md`、`CLAIM-CEILING.md`、`EVIDENCE-MAP.md`、`SOURCE-PATH-MAP.md`，並為理解凍結公式與 contingency 邊界查閱 package 內 `METHOD-FREEZE.md`、`LC-SRS-GATE-CONTRACT.md`、`CONTINGENCY-LADDER.md`、`ROOT-FABLE-C3-ADJUDICATION.md`、`FABLE-51-C3-POSTGATE-AUDIT.md`。沒有讀取或依賴 `CHATGPT-QA-PROMPT.md`。

`LITERATURE-SUPPORTED PRINCIPLE`　外部證據僅採原始論文、原始 technical report、first-party conference proceeding 與官方標準；搜尋中出現的 surveys、部落格與二手摘要沒有拿來支持本裁決。尤其文獻只能支持 metric、credit assignment、potential-game、validation 的原理，**不能由論文名稱推導本 simulator 的 efficacy、閾值或部署 readiness**。

## Imbalance-aware metrics and prospective-gate design

`LITERATURE-SUPPORTED PRINCIPLE`　Balanced accuracy 對二元分類可定義為

\[
BA=\frac12\left(\frac{TP}{TP+FN}+\frac{TN}{TN+FP}\right)
=\frac12(TPR_+ + TNR_-).
\]

這把正類 sensitivity 與負類 specificity 各給一半權重，因此與樣本 prevalence 所形成的 majority-class raw baseline 解耦。Brodersen et al. 的 ICPR 2010 工作正是此用途；限制是它沒有告訴本專案「0.60」或「0.05」應該是 gate threshold。citeturn13search15

`LITERATURE-SUPPORTED PRINCIPLE`　Davis 與 Goadrich，*The Relationship Between Precision-Recall and ROC Curves*，ICML 2006，ACM，[DOI 10.1145/1143844.1143874](https://doi.org/10.1145/1143844.1143874)，證明 ROC 與 PR 表示存在精確關係，並顯示在 skewed data 下只看 ROC/AUC 可能隱藏 PR 層面的差異；Saito 與 Rehmsmeier，*The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets*，PLoS ONE 2015，[DOI 10.1371/journal.pone.0118432](https://doi.org/10.1371/journal.pone.0118432)，以模擬與資料實驗展示 PR 對不平衡比例更敏感。兩篇都提醒 prevalence 會改變某些 performance views，但都不是本專案 sign gate 的直接替代定理。citeturn12view2

`LITERATURE-SUPPORTED PRINCIPLE`　Saerens、Latinne、Decaestecker，*Adjusting the Outputs of a Classifier to New a Priori Probabilities: A Simple Procedure*，*Neural Computation* 2002，[DOI 10.1162/089976602753284446](https://doi.org/10.1162/089976602753284446)，研究 class-prior shift 下如何在特定假設成立時修正 posterior；它說明 prevalence 與決策規則並非可隨意混用，但本專案的 `Q3(a)-Q3(a_ref)` 不是經校準 posterior，因此不能直接套其 EM correction。citeturn13search5 Guo、Pleiss、Sun、Weinberger，*On Calibration of Modern Neural Networks*，ICML/PMLR 2017，則實證現代 neural nets 可能嚴重 miscalibrated；其 temperature scaling 結果同樣不能把 Q-difference sign 自動解釋為機率。citeturn12view4

`INFERENCE`　因此本案中 balanced sign 最適合做 **primary**，而非事後 secondary：科學問題是「對真正正／負 target sign，learner 是否都能辨識」，package 沒有提出正類錯誤理應比負類錯誤重要約 3.6 倍的 operational loss。若研究問題本來就是現場 prevalence 下每 row 的平均錯誤率，raw accuracy 應是 primary；若兩者都是獨立決策目的，才應 co-primary 並預先定義 AND/OR 與 multiplicity。此處 raw 最合理的角色是**強制 secondary continuity metric**：公開，但不再用它重判 R6。

`PROPOSAL`　failure-proof 定義應完全鎖死。令 eligibility 與 R6 相同：

\[
{\cal E}=\{r:|\bar y_r|\ge0.02\},
\quad s_r=\operatorname{sign}(\bar y_r).
\]

預測 \(\hat s_r\) 由 \(\hat y_r=Q_3(s_r,a_r)-Q_3(s_r,a_{\rm ref})\) 的嚴格正負號取得；\(\hat y=0\) **不得刪除**，對正／負真值皆計為錯誤。對每 seed \(j\) 在八個 held-out worlds 各出現一次後 pooled：

\[
BA_{m,j}=\frac12\!\left[
\frac{N^{m,j}_{++}}{N^{m,j}_{++}+N^{m,j}_{+-}}
+
\frac{N^{m,j}_{--}}{N^{m,j}_{--}+N^{m,j}_{-+}}
\right],
\]

\(m\in\{I,P\}\) 分別為 INFORMED、MATCHED-PLACEBO；然後

\[
BA_m=\frac13\sum_{j=1}^{3}BA_{m,j},\qquad
\Delta BA=BA_I-BA_P.
\]

任何 seed 若 \(N_+=0\) 或 \(N_-=0\)，**fail closed：BA=undefined 且 learner predicate 失敗**，不得補值、改 threshold、合併類別或挑 seed。每個 denominator 必須逐 seed serialize。Raw accuracy \(A_I,A_P,\Delta A\) 用完全相同 \({\cal E}\) 與 denominator 同時輸出。

## Credit assignment, shared externalities, and decentralized execution

`LITERATURE-SUPPORTED PRINCIPLE`　Wolpert 與 Tumer，*Optimal Payoff Functions for Members of Collectives*，*Advances in Complex Systems* 2001，[DOI 10.1142/S0219525901000188](https://doi.org/10.1142/S0219525901000188)，研究如何為 individual agents 設計與 world utility 對齊且具有較好 learnability 的 local payoff；difference-style reward 的核心價值是比較 agent 行動與特定 counterfactual baseline。它支持「適當反事實可改善 credit signal」，但**不保證任意不同背景上的 unilateral branches 加總等於 simultaneous world utility**。citeturn14search0

`LITERATURE-SUPPORTED PRINCIPLE`　Foerster et al.，*Counterfactual Multi-Agent Policy Gradients*，AAAI 2018，[DOI 10.1609/aaai.v32i1.11794](https://doi.org/10.1609/aaai.v32i1.11794)，COMA 的 counterfactual baseline 是在**其他 agents 的 actions 固定**時 marginalize 單一 agent 的 action；centralized critic、decentralized actors 是其結構性假設。這個 “keep others fixed” 恰是 Fable CSE 證明義務中不能跳過的一步。COMA 沒有主張多個各自在不同 unilateral world 上計算的 marginal contribution 可以相加成 simultaneous action value。citeturn12view6

`LITERATURE-SUPPORTED PRINCIPLE`　Sunehag et al. 的 *Value-Decomposition Networks for Cooperative Multi-Agent Learning Based on Team Reward*，AAMAS 2018，IFAAAMAS/ACM stable record [DOI 10.5555/3237383.3238080](https://doi.org/10.5555/3237383.3238080)，從單一 team reward 學 per-agent values；Rashid et al. 的 *QMIX*，ICML/PMLR 2018，利用 monotonic mixing 約束，才取得 centralized joint-Q maximization 與 decentralized greedy action 的一致性。這兩者說明「decentralized execution 能否代表 global scalar」需要明確 factorization/monotonicity 等結構；不是看到 additive-looking targets 就自動成立。QMIX 本身也只保證其假設下的 argmax consistency，不是任意 global objective 的精確 additive attribution。citeturn14search1turn12view7

`LITERATURE-SUPPORTED PRINCIPLE`　Foerster et al.，*Stabilising Experience Replay for Deep Multi-Agent Reinforcement Learning*，ICML/PMLR 2017，指出 co-agent policies 改變會令 replay data 變得 nonstationary／obsolete，並提出 importance weighting/fingerprints。這支持對 stale background、off-policy counterfactual leakage 與 replay lineage 保持警戒；它不是本 package 已發生 leakage 的證據。citeturn11search1

`INFERENCE`　對本專案而言，local target 要聲稱代表 global \(G\)，至少必須區分四種強度完全不同的命題：**exact identity**（逐狀態代數恆等）、**unbiased estimator**（對指定隨機機制取 expectation 正確）、**aligned/shaping signal**（改善 credit 但不等於 objective）、**heuristic**（只有 plausibility）。CSE/EC 目前最多在後兩層；LC-SRS 對明確四 profile teacher 則具有第一層的窄域 identity。這個分級不能互換。

## Shapley/current-slot residual analysis and the CSE boundary

`PROJECT-COPIED FACT`　Frozen LC-SRS 對兩位使用者使用 matched current-slot profiles \(00,10,01,11\)。若

\[
G(x)=\sum_v B_v(x)-\lambda E(x),
\]

package 定義 unilateral total residual \(d_i=\ell_i+e_i=G(x_i)-G(x_0)\)，以及 interaction residual

\[
\Psi=[G(11)-G(00)]-[G(10)-G(00)]-[G(01)-G(00)],
\]

再取

\[
z_{3,i}=e_i+\Psi/2.
\]

因此

\[
\sum_i(\ell_i+z_{3,i})=G(11)-G(00).
\]

`LITERATURE-SUPPORTED PRINCIPLE`　Shapley 的原始 *A Value for N-Person Games*，RAND P-295，1952，[DOI 10.7249/P0295](https://doi.org/10.7249/P0295)，是在**一個固定 characteristic-function game** 上，以公理導出 value allocation。citeturn12view11 對二人 game

\[
v(\emptyset)=G(00),\;v(\{1\})=G(10),\;
v(\{2\})=G(01),\;v(\{1,2\})=G(11),
\]

LC-SRS 給 agent 1 的總 attributed increment 可重寫為

\[
\ell_1+z_{3,1}
=\frac12[v(\{1\})-v(\emptyset)]
+\frac12[v(\{1,2\})-v(\{2\})],
\]

agent 2 對稱成立。這正是二玩家 Shapley marginal-order average。

`INFERENCE`　所以 **LC-SRS 四-profile identity 對它明示的 two-user current-slot teacher 是科學上合法的**：它精確分配同一 matched profile game 的 \(G(11)-G(00)\)。但 Shapley 的 efficiency/budget-balance 性質本身不證明：（i）Q3 student 能學到此 attribution；（ii）`Q1+Q2+Q3` 各 user 分散 argmax 會實現 profile 11；（iii）population EE 上升；（iv）trajectory/episode policy 上升；（v）FULL 優於 ablation；或（vi）它是 Monderer–Shapley 意義的 strategic potential game。這些都是不同命題。

`LITERATURE-SUPPORTED PRINCIPLE`　Monderer 與 Shapley，*Potential Games*，*Games and Economic Behavior* 14(1), 1996，[DOI 10.1006/game.1996.0044](https://doi.org/10.1006/game.1996.0044)，要求 exact potential 在**相同 \(a_{-u}\)** 下，player \(u\) 的 unilateral utility difference 等於一個共同 potential 的 difference。citeturn13search2 Marden、Arslan、Shamma，*Cooperative Control and Potential Games*，IEEE TSMC-B 2009，[DOI 10.1109/TSMCB.2009.2017273](https://doi.org/10.1109/TSMCB.2009.2017273)，以及 Nie、Comaniciu 在 wireless channel allocation 中的 *Adaptive Channel Allocation Spectrum Etiquette for Cognitive Radio Networks*，*Mobile Networks and Applications* 2006，[DOI 10.1007/s11036-006-0049-y](https://doi.org/10.1007/s11036-006-0049-y)，都是**先構造滿足 potential 結構的 utilities** 才得到分散式性質；不能由「shared cost 剛好可守恆」反推 potential。citeturn12view9turn12view10

`PROJECT-COPIED FACT`　Fable CSE 目前能主張的結構是同一 configuration 上

\[
\sum_u share_u(x)=P^N(x).
\]

`INFERENCE`　這只是 same-profile budget conservation。若每個 agent 的 CSE target 分別在 \(c^1,c^2,\ldots\) 這些不同 unilateral branches 上計算，則一般沒有

\[
\sum_u[share_u(c^u)-share_u(b^0)]
=P^N(c)-P^N(b^0).
\]

要稱「summed-unilateral exact potential」，至少必須證明對所有 admissible \(u,a_u,a'_u,a_{-u}\)

\[
U_u(a'_u,a_{-u})-U_u(a_u,a_{-u})
=
\Phi(a'_u,a_{-u})-\Phi(a_u,a_{-u}),
\]

或直接證明其宣稱的 summed-branch identity 對 simultaneous \(c\) **逐狀態成立**，含 rate interference、shared beam/baseband cost、occupancy 改變與 interaction cross-term。package 已提供反例，因此目前沒有這個證明。

`INFERENCE`　所以 CSE **不能自動 promotion**；EC 更不能。EC 只保留 energy-side correction，若 action 同時改變他人的 rate/interference，它甚至缺少 CSE 所試圖表示的一部分 externality。Shubik 的 joint-cost 原始研究早已指出 cost allocation 與 decentralized incentive alignment 是不同問題；*Incentives, Decentralized Control, the Assignment of Joint Costs and Internal Pricing*，*Management Science* 1962，[DOI 10.1287/mnsc.8.3.325](https://doi.org/10.1287/mnsc.8.3.325)。citeturn12view12

## Validation-design synthesis mapped to this package

`LITERATURE-SUPPORTED PRINCIPLE`　Varma 與 Simon，*Bias in Error Estimation When Using Cross-Validation for Model Selection*，*BMC Bioinformatics* 2006，[DOI 10.1186/1471-2105-7-91](https://doi.org/10.1186/1471-2105-7-91)，實證「用同一 CV 既挑 model/hyperparameter 又報其 error」會產生 optimistic bias，nested separation 可降低該問題。citeturn12view13 Rabinowicz 與 Rosset，*Cross-Validation for Correlated Data*，JASA 2022，[DOI 10.1080/01621459.2020.1801451](https://doi.org/10.1080/01621459.2020.1801451)，從理論與實驗研究 correlated observations 下 standard CV 何時偏誤。citeturn13search3

`LITERATURE-SUPPORTED PRINCIPLE`　Hurlbert，*Pseudoreplication and the Design of Ecological Field Experiments*，*Ecological Monographs* 1984，[DOI 10.2307/1942661](https://doi.org/10.2307/1942661)，核心原則是 subsamples/repeated measurements 不能冒充獨立 experimental units。移植到本案是推論，但含義很直接：三個 learner seeds 不是三個獨立 physical worlds。citeturn14search3

`PROJECT-COPIED FACT`　原 LC-SRS contract 已採八個 leave-one-world-out folds，每 fold 七個 fit worlds、一個 held-out world，三個 seeds 全部保留；每個 held-out world 每 seed 只進 pooled learner metric 一次。因此其「world 是 cluster、seed 不是 world」設計方向與上述原理一致。

`LITERATURE-SUPPORTED PRINCIPLE`　Ojala 與 Garriga，*Permutation Tests for Studying Classifier Performance*，JMLR 2010，研究 label permutation 與 restricted permutation 作為 classifier null checks；其限制是本案 deterministic matched-placebo 不是該文的 formal p-value test。citeturn12view15 Glasserman 與 Yao，*Some Guidelines and Guarantees for Common Random Numbers*，*Management Science* 1992，[DOI 10.1287/mnsc.38.6.884](https://doi.org/10.1287/mnsc.38.6.884)，說明 matched stochastic-system comparisons 使用 common random numbers 可降低比較變異，但效果依 ordering/correlation 條件而定，不能治療模型偏誤。citeturn12view16

`INFERENCE`　本 package 的 placebo 設計值得保留：training-world 內依預先固定 strata 做 nonzero cyclic target shift；features、masks、action identities、weights、sample counts 不變；held-out world targets 不進 fitting/permutation。這比把 labels 任意跨 world 洗牌更能測「具有相似 support/結構但 label association 被破壞」的 learner comparator。新的 balanced denominators 必須讓 INFORMED 與 PLACEBO 共用同一 true held-out \({\cal E}\)，不能讓兩 arm 各自選容易 rows。

`LITERATURE-SUPPORTED PRINCIPLE`　Nosek、Ebersole、DeHaven、Mellor，*The Preregistration Revolution*，PNAS 2018，[DOI 10.1073/pnas.1708274114](https://doi.org/10.1073/pnas.1708274114)，把預測與事後解釋的界線放在 outcome knowledge 之前。citeturn14search2 官方 ICH E9(R1) estimand framework 同樣要求 objective、estimand、design、analysis、interpretation 對齊；它是 clinical-trial standard，移植到 RL gate 僅是 methodology inference。citeturn11search3 Pocock 的 group-sequential 原始工作則顯示 repeated looks 若是決策程序，停止邊界應在資料逐次揭露前定義，而非看到結果後繼續嘗試。*Biometrika* 1977，[DOI 10.1093/biomet/64.2.191](https://doi.org/10.1093/biomet/64.2.191)。citeturn12view18

`INFERENCE`　因此 fresh gate 的 legitimacy 來自四件事共同成立：新 worlds 未開封、balanced estimand 與 thresholds 在 outcome 前 seal、placebo 與 numerator/denominator 完全匹配、失敗後停止 metric revisions。它**不**來自 R6 development balanced numbers 看起來漂亮。

## Ranked candidate dispositions

`PROPOSAL`　**Rank 1 — LC-SRS，RETAIN。** 保持二人、四-profile、current-slot target 原公式，不改 \(\kappa\)、\(\lambda\)、32 draws、student architecture、loss、seed-selection 規則或 one-pass `Q1+Q2+Q3` deployment；僅在一個新的 prospective study 中把 balanced sign estimand 事前升格。理由是它已有可檢查的 scoped algebraic identity，而目前主要未解問題是 learnability/interface/composition，不是 teacher budget identity。

`PROPOSAL`　**Rank 2 — CSE，HOLD contingency；不 promotion。** 它具有有意義的 shared-cost intuition，但欠缺「不同 unilateral branches 加總等於 simultaneous potential」的 proof。最低補強證據是：（a）對 frozen CSE formula 給出上述 fixed-background exact-potential／summed-branch theorem；或（b）若撤回 “exact” 字眼，另做完全 prospective、matched `00/10/01/11` physical test，驗證其 unilateral target 的 sign/magnitude 與真 simultaneous surplus 在 unseen worlds 是否一致且無 double counting。後者只能把它提升為實證候選，仍不能證明 exactness。

`PROPOSAL`　**Rank 3 — EC，HOLD lower-priority contingency；不 promotion。** 其簡化可能降低 target variance，但在 rate/interference externality 存在時沒有理論依據把 energy-only allocation 視為 global objective decomposition。它同樣需要 frozen-formula prospective physical evidence；「比較簡單」不是 promotion criterion。

`INFERENCE`　三者不得在本 gate 做 hybrid，因為那會再打開新的 target family，使一次 metric revision 變成 target/metric joint search。

## One formula-complete next contract and falsification rules

**One formula-complete next contract and falsification rules**

`PROPOSAL`　下一個且僅下一個 contract 定義為：

**Candidate/teacher**：只有 frozen LC-SRS：

\[
z_{3,i}=e_i+\Psi/2,\qquad y_i=z_{3,i}/\kappa
\]

及既有 `00/10/01/11` matched 32-draw teacher；不含 CSE、EC、hybrid、episode-policy training。

**Background lineage**：固定 package 已凍結的 Q1/Q2 V0.20 repriced lineage `2026092101`、rung `003000`、checkpoint SHA-256 `d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc`。Student 保留全部三 seeds `2026135101/02/03`，不因 R6 表現更換或挑選。

**Worlds**：必須是**八個具體命名、在 seal 時有 ledger 證明從未產生 teacher labels、physics outcomes、learner outcomes 或 TEST receipts 的 TRAIN worlds**，並在任何結果開封前將 ordered IDs 與 manifest hash 寫入 contract。現 package 沒有提供足夠證據讓我誠實宣稱某一組新的八個 ID 全部仍 unopened，因此本裁決不虛構 ID；缺少這個 sealed list 時，fresh gate 本身即不合法。

**Cross-validation**：八折 leave-one-world-out；每 fold 只用其餘七 worlds fit informed/placebo；三 seeds 全報，不作 best-seed/rung/checkpoint selection。

**Primary learner predicates**：

\[
\rho_I\ge0.20,
\qquad BA_I\ge0.60,
\qquad\Delta BA=BA_I-BA_P\ge0.05.
\]

`INFERENCE`　`0.60` 與 `0.05` 不是文獻推導出的 universal effects；這裡選擇**沿用原 sign gate 的數值門檻，不因已看過 development balanced values 而放寬**，是最小變更／anti-tuning 決策。這是 project proposal，而非 literature claim。

**Mandatory secondary learner receipts**：原 raw \(A_I,A_P,\Delta A\)、所有 \(N_+,N_-\)、ties/zeros、各 seed 與各 world results 全部顯示；raw 不得被稱為 R6 pass，也不得被隱藏。原 world-stability Spearman rule保持不變。

**Placebo/leakage**：沿用原 matched-support strata、within-training-world deterministic nonzero cyclic shift、相同 S/R/C rows、features、masks、weights、updates；held-out-world targets/statistics 不得進 fitting 或 permutation；INFORMED/PLACEBO 用同一 eligibility set 計 BA/raw。

**Physical/composition/service**：除 learner raw→balanced decision estimand 的單一 revision 外，原 gate predicates全部維持：coverage、mechanics、common-field/mutation integrity、pooled `11-vs-00` physical signature及至少 `4/8` world directions、action exposure、`literal_11`／harmful-partial bounds、topology consistency、TEACHER-ORACLE vs B、INFORMED full-roster vs B、每 world `S_I,w >= S_B,w-0.01`。Balanced metric不得補救 physical、composition 或 service failure。

**Runtime/receipt validity**：任何 replay digest、module binding、common-field hash、checkpoint/model lineage、mutation、receipt completeness 缺陷都標成 `INVALID_RUN`；invalid run 不提供 scientific pass/fail，且不得以它證明 metric imbalance 或 teacher failure。C1/C2 correction 的狀態另列 context，不代替 C3 predicate。

**Hard stop**：任何 required scientific predicate 失敗即 `STOP_OBSERVABILITY/STOP_AND_REDESIGN` 類結論；**不得第二次改 sign metric、sign orientation、\(|\bar y|\) threshold、scale、seed、horizon、world subset 或 placebo formula**。尤其不得因結果而反轉 sign 或挑成功 seed/rung。

**Compute class**：沒有授權執行。本 contract 若其 multi-world physical simulator/rollout projected wall time 超過約 30 分鐘，分類為 **heavy**，只能在 Ubuntu server、另行取得 authorization 後處理；本裁決不授權該工作。

`PROPOSAL`　預先的 falsification/diagnostic mapping如下。**Metric-imbalance hypothesis**只有在 BA/ΔBA prospectively 通過、raw 仍呈 prevalence sensitivity、placebo separation 與 world stability 同時成立時才得到支持；它仍不等於部署 efficacy。**State/interface insufficiency**是在 teacher mechanics/physical signature 正常且 receipts 完整，但 informed BA/Spearman 在 held-out worlds 無法穩定勝過 matched placebo。**Composition failure**是在 teacher與learner source-level evidence 通過，卻 literal one-pass `Q1+Q2+Q3` 無法達到 11/exposure/topology/EE/service predicates。**Runtime/receipt defect**由 hashes、lineage、common-field、callback/receipt 或 replay integrity failure 定義，不應解讀為任何 scientific negative。

`PROPOSAL`　更強的 **three-head thesis falsification** 是：Q3 teacher identity/physical signature成立、Q3 learner在 unopened worlds 對 matched placebo 有穩定可重現 signal，但把這個 Q3 加到凍結 Q1+Q2、單一 native mask、單一 argmax 後，仍系統性不能改善 FULL current-slot EE／service，或產生不可接受 harmful partial。這表示「可學 credit head」沒有轉化成「有效三-head decentralized composition」。反之，只要 learner discrimination 本身都不成立，就還不能把責任定位到三-head composition。

## Claim-to-source ledger

**Claim-to-source ledger**

| 標籤／命題 | Primary source 與 scope | 關鍵限制 |
|---|---|---|
| `LITERATURE-SUPPORTED PRINCIPLE` Balanced accuracy 適合 imbalance-aware class-conditional performance | Brodersen, Ong, Stephan, Buhmann, *The Balanced Accuracy and Its Posterior Distribution*, IEEE ICPR, 2010, [DOI](https://doi.org/10.1109/ICPR.2010.764). citeturn13search15 | 不決定本案 threshold，也不能 retroactively rescue R6 |
| `LITERATURE-SUPPORTED PRINCIPLE` skew/prevalence 會改變 performance interpretation | Davis & Goadrich, ICML 2006, [DOI](https://doi.org/10.1145/1143844.1143874); Saito & Rehmsmeier, PLoS ONE 2015, [DOI](https://doi.org/10.1371/journal.pone.0118432). citeturn12view2 | PR/ROC 是 ranking/retrieval setting，不等同 frozen sign gate |
| `LITERATURE-SUPPORTED PRINCIPLE` prior shift 與 calibration 是額外假設 | Saerens, Latinne, Decaestecker, *Neural Computation*, 2002, [DOI](https://doi.org/10.1162/089976602753284446); Guo et al., ICML 2017, [PMLR](https://proceedings.mlr.press/v70/guo17a.html). citeturn13search5turn12view4 | Q3 delta 不是已校準 probability |
| `LITERATURE-SUPPORTED PRINCIPLE` counterfactual credit 要明確 baseline／fixed background | Wolpert & Tumer, *Advances in Complex Systems*, 2001, [DOI](https://doi.org/10.1142/S0219525901000188); Foerster et al., COMA, AAAI 2018, [DOI](https://doi.org/10.1609/aaai.v32i1.11794). citeturn14search0turn12view6 | useful credit ≠ summed simultaneous exactness |
| `LITERATURE-SUPPORTED PRINCIPLE` decentralized greedy consistency 需要結構假設 | Rashid et al., QMIX, ICML 2018, [PMLR](https://proceedings.mlr.press/v80/rashid18a.html). citeturn12view7 | monotonic factorization 是特殊條件，不是 arbitrary decomposition |
| `LITERATURE-SUPPORTED PRINCIPLE` Shapley efficiency 適用於一個固定 coalition game | Lloyd Shapley, RAND P-295, 1952, [DOI](https://doi.org/10.7249/P0295). citeturn12view11 | 不推出 strategic/deployment potential |
| `LITERATURE-SUPPORTED PRINCIPLE` exact strategic potential 要 matched unilateral deviations | Monderer & Shapley, *Games and Economic Behavior*, 1996, [DOI](https://doi.org/10.1006/game.1996.0044). citeturn13search2 | same-configuration cost conservation 不夠 |
| `LITERATURE-SUPPORTED PRINCIPLE` wireless potential 結果依賴特定 utility construction | Nie & Comaniciu, *Mobile Networks and Applications*, 2006, [DOI](https://doi.org/10.1007/s11036-006-0049-y). citeturn12view10 | 不能直接外推到 satellite LC-SRS/CSE |
| `LITERATURE-SUPPORTED PRINCIPLE` selection 與 validation 資料重用會 optimistic | Varma & Simon, *BMC Bioinformatics*, 2006, [DOI](https://doi.org/10.1186/1471-2105-7-91). citeturn12view13 | generic classifier setting |
| `LITERATURE-SUPPORTED PRINCIPLE` correlated units 需要 respecting dependence | Rabinowicz & Rosset, JASA, 2022, [DOI](https://doi.org/10.1080/01621459.2020.1801451); Hurlbert, *Ecological Monographs*, 1984, [DOI](https://doi.org/10.2307/1942661). citeturn13search3turn14search3 | 對 worlds/seeds 的映射是本報告 inference |
| `LITERATURE-SUPPORTED PRINCIPLE` matched null與 common randomness 可提高 comparator interpretability | Ojala & Garriga, JMLR 2010; Glasserman & Yao, *Management Science* 1992, [DOI](https://doi.org/10.1287/mnsc.38.6.884). citeturn12view15turn12view16 | package placebo 不是 formal permutation p-test；CRN 不消除 bias |
| `LITERATURE-SUPPORTED PRINCIPLE` estimand/stopping 應在 outcome 前固定 | Nosek et al., PNAS 2018, [DOI](https://doi.org/10.1073/pnas.1708274114); ICH E9(R1); Pocock, *Biometrika* 1977, [DOI](https://doi.org/10.1093/biomet/64.2.191). citeturn14search2turn11search3turn12view18 | preregistration 不會把錯誤 metric 變正確，也不取代 simulator validation |

## Remaining uncertainty and final decision

**Remaining uncertainty and final decision**

`PROJECT-COPIED FACT`　LC-SRS 現在所擁有的是非常窄、但真的存在的證據：二人、current-slot、四 matched profiles 的 teacher allocation identity；沒有 coordinator、auction、joint decoder、iterative repair、fallback 或 TEST，deployment 仍只有 native mask 下的一次 `Q1+Q2+Q3` argmax。package 也明確禁止把此 identity 宣稱成 learned efficacy 或 deployment readiness。

`INFERENCE`　目前最可信的 uncertainty decomposition 不是「LC-SRS algebra vs CSE algebra 二選一」，而是：**R6 的 raw metric 是否被 prevalence 遮蔽、student interface 是否能承載 teacher information、literal three-head composition 是否能把 credit signal轉成共同動作、以及 execution receipt 是否完整**。一個前瞻 balanced gate 可以區分前三者中的一部分；它不能證明 trajectory performance。

`INFERENCE`　CSE 的最大問題不是它「看起來不合理」，而是它目前聲稱 exactness 所需的數學對象不匹配：同一 \(x\) 上的 share conservation 與不同 \(c^u\) 上 unilateral target 的加總，是兩個不同命題。原始 potential-game、counterfactual-credit 與 cooperative-game 文獻都要求把背景／game 定義固定清楚。因此在沒有新 proof 或 predeclared matched physical evidence 前，CSE 只能保持 contingency hypothesis；EC 更沒有自動升級依據。

`INFERENCE`　相反地，允許一次 LC-SRS fresh gate 並不是因為 development BA 約 0.678 對 0.579 「看起來會過」。合法性恰恰建立在**不使用這些數字調整 threshold**：公式固定、原 `|bar y|>=0.02` 固定、三 seeds 全保留、numerators/denominators 固定、placebo 固定、八個新 worlds 在 outcome 前鎖定、`BA_I>=0.60` 與 `ΔBA>=0.05` 預先鎖定，而且若失敗即停止 metric revision。如此得到的是一個新的 confirmatory claim，而非 R6 的重新裁判。

`INFERENCE`　綜合 primary literature 與 package authority，我不認為現有證據足以 `PROMOTE_CSE_FAST_ROUTE` 或 `PROMOTE_EC_FAST_ROUTE`；也不認為 R6 的 raw sign-gap failure 已經足以 `STOP_AND_REDESIGN_C3`，因為 class imbalance 提供了一個明確、可前瞻檢驗且不需改 teacher 的 estimand問題，而 LC-SRS 本身尚保有可驗證的 scoped identity。最小、可證偽、沒有第二次 metric escape hatch 的科學決定，因此是保留 LC-SRS，僅給一次 fresh prospective TRAIN gate。

CONTINUE_LCSRS_FRESH_GATE