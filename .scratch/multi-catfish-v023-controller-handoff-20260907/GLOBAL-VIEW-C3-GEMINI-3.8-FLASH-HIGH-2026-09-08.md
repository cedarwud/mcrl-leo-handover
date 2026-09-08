本報告針對系統當前 C3 協調機制、歷史實驗記錄及物理模擬器模型進行全局檢驗（Global-view Examination）。全篇以繁體中文撰寫，保留 English technical terms，包含具體證據指針（evidence pointers），無任何新實驗或已凍結常數調優。

---

### 一、 (a) 負載均衡 ↔ 能效（EE）直覺在該模擬器能量模型中是否成立？

**核心結論：在該模擬器特定的物理與功率模型下，「負載均衡（Load Balancing）必能提升能效」的直覺是不成立的，甚至往往相反。**

1. **功率消耗的非線性與非加性結構**
   * **波束發射功率為最大值而非總和**：依據 [`src/mcrl/env/link_budget.py:442-446`](file:///home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py#L442-L446) 及 eq. (3.12a)，波束 RF 功率取決於該波束上所有被服務使用者的最大鏈路功率需求 $p_{s,v} = \max_{u: x=1} p_{u,s,v}$，而非使用者功率之和。
   * **功放（PA）效率呈次線性（亞線性）凸性**：依據 [`src/mcrl/env/link_budget.py:474-493`](file:///home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py#L474-L493)，$\xi_{s,v} = \min\{\xi_{\max}, \xi_{\max}\sqrt{p_{s,v}/p_{\text{sat}}}\}$，使直流供電功率 $P^p_{s,v} = p_{s,v}/\xi_{s,v} \propto \sqrt{p_{s,v} \cdot p_{\text{sat}}}$（[`link_budget.py:499-518`](file:///home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py#L499-L518)）。RF 功率加倍僅使 DC 功耗增加約 $\sqrt{2} \approx 1.41$ 倍。
   * **固定的硬體啟動開銷占主導**：依據 [`src/mcrl/env/link_budget.py:270-274, 521-546`](file:///home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py#L270-L274)，每開啟一個活動波束需支付電路功率 $P_{\text{cir}} = 0.338\text{ W}$；每開啟一顆活動衛星需支付基帶功率 $P_{\text{BB}} = 0.200\text{ W}$。

2. **重新均衡（Rebalancing）的能量與傳輸量代價**
   * **頻寬共享與傳輸量**：依據 [`src/mcrl/env/link_budget.py:598-616`](file:///home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py#L598-L616)，波束頻寬 $B^w$ 由負載 $U$ 等分。若同波束內使用者 SINR 相似，波束總 Bits 約為 $B^w \overline{\log_2(1+\text{SINR})}$，將使用者自已開啟的重負載波束移出，並不會顯著增加該波束的總 Bits。
   * **波束擴張（Activation Expansion）毀滅 EE**：若為了均衡負載而將使用者移至原本未啟用或低負載的波束，將額外觸發波束啟用電路代價（$+0.338\text{ W}$）甚至衛星基帶代價（$+0.200\text{ W}$），且原波束只要仍有其餘使用者存在，其電路開銷完全不變。歷史證據顯示 V0.10/V0.11 的 oracle 探索即落入「波束擴張區」，導致 EE 下降 −1.5% 至 −4.4%（見 [01-CHRONOLOGY.md:Row 4](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md#L30)）。
   * **幾何路徑損耗惡化**：BASE（Q1+Q2）已讓使用者優先選擇高仰角、近距離衛星。強行將使用者分流至其他衛星以求「負載均衡」，使用者往往承擔更大的 Slant range 與離軸角（Off-axis angle），使所需的鏈路功率上升且 SINR 劣化。

3. **Rebalancing 何時合算？當前世界是否處於該體制？**
   * **合算體制（Profitable Regime）**：僅當（i）原波束嚴重壅塞導致頻寬飢餓且干擾極大；（ii）目標波束本已啟動（無需支付新的 $P_{\text{cir}}$）；（iii）PA 功耗對負載呈超線性（Super-linear, $\alpha > 1$）；或（iv）**波束整合清空（Beam Consolidation/Evacuation）**，即完全撤空某波束使該波束關閉以節省 $0.338\text{ W}$。
   * **評估世界的真實體制**：歷史記錄表明當前環境（100 users / 28 candidate slots / 4 顆衛星）屬於「**整合節能主導、分散負載受罰**」的體制。唯一曾獲正向增益的 V0.13 ZR oracle（+0.94% EE），事後審查證實其增益根本不是來自當步負載均衡的正面外部性，而是下游步驟關閉了 322 個波束步（Beam consolidation: bits −5.7%, energy −6.6%, beam-steps −322，見 [01-CHRONOLOGY.md:Row 6](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md#L34)）。

---

### 二、 (b) 槓桿分解與約束瓶頸（Binding Levers by Evidence）

按實證證據評估 7 項槓桿：

1. **C3 目標公式/標籤（C3 Target Formula / Label）：非主要瓶頸（Not Binding）**
   * *證據*：專案歷經 8 大家族、18 次嘗試（MONE, PNFE, ZR, LC-SRS, D, F 等）。即使提供完美預知真實開銷的 **EXACT Oracle**，在部署合成後依然全面虧損 EE（MONE −2.64%, PNFE −11.06%, D −1.33%, F −4.54%；見 [01-CHRONOLOGY.md:Table 1](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md#L20) 及 [03c-F1-ULTRA-ADJUDICATION.md:13-18](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/03c-F1-ULTRA-ADJUDICATION.md#L13-L18)）。診斷顯示 60/60 單邊外部性為正，但合成之聯合方向有 28 個翻轉為負。換言之，問題出在「單邊標籤無法加總」，換目標公式無法克服此結構矛盾。
2. **決策合成規則（Composition Rule: 獨立每用戶加性 Argmax）：首要致命瓶頸（Primary Binding Bottleneck）**
   * *證據*：18 次嘗試從未改變合成規則：$a_u^* = \text{masked\_argmax}(Q1_u + Q2_u + z_{3u}/\kappa)$（見 [01-CHRONOLOGY.md:§4.1](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md#L72) 及 [06-COMPOSITION-RULING.md:7-16](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/06-COMPOSITION-RULING.md#L7-L16)）。當系統存在 100 個用戶，每個用戶基於「假設其餘 99 人不動」所計算的加性 $z_{3u}$ 獨立做決策時，多個用戶會同時移向同一個目標（群聚效應 / Herding），將原本單一人轉移的邊際收益瞬間轉化為共同塞爆目標波束、或分散啟動多個高功耗波束。物理交互（$\max$ 功率、啟用開銷、頻寬瓜分）皆為非加性集合函數（Non-additive set functions），加性獨立 argmax 必然產生嚴重的外部性錯配。
3. **可部署資訊介面（Deployable Information Interface）：次要關鍵瓶頸（Secondary Binding Bottleneck）**
   * *證據*：部署時用戶無法觀測同一時隙他人的動作 $a_{-u}$，亦無法觀測真實小尺度衰落（Fading）。V0.14 中 Q3 學習器 skill 為 −0.062，正向支援事件（$g \wedge z_3 > 0$）為他人動作所引發之共時協調事件，特徵 AUC 僅 0.72–0.75（見 [01-CHRONOLOGY.md:Row 7](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md#L36)）；V0.20 的 EXACT_ZR（+0.985%）因依賴真實衰落而通過，但一旦改為可部署期望值（EXPECTED_ZR），增益全失並立即觸發 `STOP_EXPECTED_ZR_FAST`（[01-CHRONOLOGY.md:Row 15](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md#L45)）。
4. **決策視野（Decision Horizon）：中度瓶頸（Moderately Binding）**
   * *證據*：C3 始終被限制為單步當前時隙外部性（[01-CHRONOLOGY.md:§4.2](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md#L76)），而 LEO 換手的真實效益體現在後續 47 個子步（30.08 s）的滯留與波束關閉累積。
5. **評估目標與約束（Objective / Evaluation: Ratio of Sums + 服務裕度）：強烈拘束（Strongly Binding Constraint）**
   * *證據*：$\text{EE} = \sum \text{Bits} / \sum \text{Joules}$，分式規劃與單純加權和不對等；且服務率非劣性門檻嚴格要求 $s \ge s_{\text{BASE}} - 0.001$。在 200 次決策中僅漏掉 1 人次服務（0.995）即直接被 F1 判死淘汰（[03c-F1-ULTRA-ADJUDICATION.md:33-37](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/03c-F1-ULTRA-ADJUDICATION.md#L33-L37)）。
6. **物理體制（Physical Regime: 100 users / 28 slots）：中度拘束（Moderately Binding）**
   * *證據*：使用者密度中等（平均每波束 2–4 人），未達極端頻寬匱乏或極端干擾飽和區，波束硬體固定能耗占比偏高。
7. **BASE 強度本身（BASE Strength: Q1+Q2）：極度緊密約束（Severely Binding Baseline）**
   * *證據*：BASE 本身在 TRAIN 上已達到極高能效水準（$\approx 1.186 \times 10^8\text{ bits/J}$，見 [03c-F1-ULTRA-ADJUDICATION.md:15](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/03c-F1-ULTRA-ADJUDICATION.md#L15)）。Q1 完整提取了一階鏈路能效（SINR、距離、單鏈路功率增量），Q2 鎖定了服務風險與幾何演化，留給「純協調」的邊際餘量極其微薄，任何因協調預測不精準造成的額外啟動皆輕易抹平收益。

---

### 三、 (c) 若跳出「第三個加性頭」框架：全域重新設計與事前合規性（Pre-outcome Admissibility）

若不受限於「獨立 per-user 加性頭」，真正的協調應針對「波束集合啟動」與「群體決策」建模：

1. **重構方案選項**：
   * **架構 A：兩階段排程器（Two-stage Macro Scheduler / Beam Budgeting）**：中央調度器每 30.08 s 決定候選波束的「啟用/關閉集合」（例如預先設定最大啟用波束數預算，或判定並強制撤空低效波束），將被撤空波束之用戶從動作遮罩（Mask）中排除，剩餘用戶在安全集合內以 Q1+Q2 獨立選擇最優鏈路。
   * **架構 B：Q1+Q2 的 Tie-breaker / 近似最優約束解碼器**：以 Q1+Q2 為主決策，限定候選動作集合為 $A_u^\epsilon = \{a \mid q_{12,u}(a) \ge \max q_{12,u} - \epsilon\}$。C3 僅在 $\epsilon$ 頻帶內作為共用波束的協調偏好（例如優先聚集到同伴已選波束以促成其餘波束關閉），徹底消除 C3 顛覆 Q1+Q2 高質量決策的破壞力（見 [ADJUDICATION-C3-FUTURE-PATH:Candidate 3](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-C3-FUTURE-PATH-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md#L106-L113)）。
   * **架構 C：集中式聯合貪婪解碼器（Centralized Sequential Decoder）**：中央依照用戶利得差值排序，依序分配用戶，前序用戶分配後更新波束即時負載與啟動狀態，後序用戶感知動態背景。
2. **事前合規性（Pre-outcome Admissibility）檢驗**：
   * 根據專案誠信規則（Integrity rules），禁止利用已打開的殘差、種子或世界進行後驗微調。
   * **可被事前認可的條件**：必須在開跑前凍結機制假說、明確之可部署資訊介面、解析公式/算法、固定超參數（如 Tie-breaker 凍結 $\epsilon=0$ 或具物理依據之常數，禁止 sweep $\epsilon$）、訓練/驗證世界隔離、明確證偽條件（Falsifier），且完全隔離 TEST split。
   * **合規評判**：架構 A（波束撤空啟發式/預算約束）與架構 B（$\epsilon=0$ 之 Tie-breaker）具備清楚物理因果且不依賴未觀測之微觀衰落，只要事前凍結合同，**完全具備 Pre-outcome Admissible 資格**；反之，若在觀察多個世界後回頭調整門檻或權重，則屬違規。

---

### 四、 (d) E1 存在性篩查（Existence Screen E1）四種結果之意涵

當前運行的 E1 以 $U_1$（單錨點至多改變 1 名用戶之 Dinkelbach+DP 嚴格全局最優）與 $J_1$（固定「撤空單一來源波束」之聯合 Catalog）作為物理上限檢驗（[V023-C3-EXISTENCE-TEST-CONTRACT-E1:§2-§3](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md#L20-L45)）：

| 結果矩陣 | 物理意涵與對 Owner 直覺的判定 | 重新設計之後續路線授權 |
|---|---|---|
| **$U_1$ HEADROOM<br>$J_1$ HEADROOM** | 物理上確實存在超額 EE 空間，證明 Owner 的「協調必能省能」在上限層面成立。過去失敗純粹肇因於「獨立加性合成的群聚翻轉」與「部署端缺乏共時資訊」。 | 授權宣告候選殺手篩查（Kill screen），可同時朝微觀單用戶約束及巨觀波束撤空排程器方向探索，並證明加性 argmax 是唯一障礙。 |
| **$U_1$ HEADROOM<br>$J_1$ CLOSED** | 只有精細的單用戶微調能獲得微幅邊際利得；固定波束撤空 Catalog 失敗，說明粗暴撤空波束會因強迫部分用戶切向劣質衛星而破壞服務率或降低總 Bits。 | 僅授權單用戶類別（Unilateral-class）殺手篩查；徹底排除粗粒度波束撤空機制，轉向高精度約束或 Tie-breaker。 |
| **$U_1$ CLOSED<br>$J_1$ HEADROOM** | **最具破壞力與啟發性的結果**：證實單用戶單邊擾動對 BASE 無任何物理改善空間（BASE 在單用戶維度已達局部最優）；**只有多用戶聯合撤空波束關閉硬體（$P_{\text{cir}}$）才能獲益**。徹底證偽過去 18 次「單邊加性 $z_u$」的研究路線。 | 完全關閉所有單邊加性 C3 研究！唯一合規路徑轉向聯合波束撤空調度器（Joint Beam Evacuation Scheduler）。 |
| **$U_1$ CLOSED<br>$J_1$ CLOSED** | 在該評估面板與流量體制下，BASE 已實質觸及物理天花板。Owner 的「負載均衡必能提高 EE」直覺在當前模擬器被客觀證偽：任何脫離 BASE 的再平衡皆無法在守住服務率前提下提升能效。 | 徹底終止本篇論文的 C3 開發。鎖定 C1+Q2 為最終成果，並將此「加性協調在 LEO 換手中的不可能性與負面效應」作為本論文極具學術價值的負面發現。 |

---

### 五、 (e) 誠實、無機率包裝之時間線與後續實驗建議

1. **數天內可現實完成 vs 需作為 Follow-up Paper 的邊界**：
   * **數天內（本篇論文結案）**：
     * **全面保全兩貓魚主成果（Two-Catfish Main Result: Q1+Q2 / FULL2）**：如 [`07-C1C2-SUCCESSOR-DECLARATION.md:13-31`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/07-C1C2-SUCCESSOR-DECLARATION.md#L13-L31) 所定義，Q1（一階能效）與 Q2（幾何服務穩定度）之架構與增益已完全確立。
     * **C3 寫入論文作為嚴謹的 Negative / Structural Analysis Section**：將 18 次嘗試、加性 argmax 的局限性、非線性功率（PA 亞線性 + $P_{\text{cir}}$ 階躍）與 E1 的物理天花板完整揭露。此為高度嚴謹的工程與理論貢獻，足以支撐本論文。
     * 數天內任何「重新設計並訓練部署端三頭神經網絡、通過嚴格驗證並在 Confirmatory panel 上翻正 EE」的企圖在工程時間與誠信門檻上皆不具可行性。
   * **Follow-up Paper**：
     * 設計集中式拓撲排程器（如以整數線性規劃或集中式 Macro-Agent 決定波束開關預算），與分散式 Q1+Q2 形成雙層階層式控制（Hierarchical Control），探討在極端高密度壅塞場景下的協調效益。
2. **E1 結束後最具資訊量的一項單一實驗（Single Most Informative Experiment）**：
   * **「E1 最優聯合分佈在獨立加性 Argmax 下的保真度診斷」（Exact Joint Winner vs Additive-Decoded Diagnostic）**：
     * *操作*：自 E1 產出之最優物理 Profile（若 $J_1$ 或 $U_1$ 有贏家），反解出各用戶的精確邊際貢獻 $z_{u}^*$ 並加回 $Q1+Q2$，透過系統部署規則 $\arg\max(Q1+Q2+z_{u}^*/\kappa)$ 執行解碼。
     * *資訊價值*：直接觀測「當給定絕對真實的最優協調激勵時，加性 argmax 是否會因部分採納（Partial Adoption）或群聚失序而再度自毀」。此一實驗不涉及漫長的神經網絡訓練，僅需幾分鐘計算，即可為「加性解碼結構是否為死路」給出終極且不可辯駁的判決。
