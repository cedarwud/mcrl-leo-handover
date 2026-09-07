# TRANSLATION-GLOSSARY — 中→英 LOCKED 術語表 + FORBIDDEN-English 清單

> **CURRENT MATRIX OVERRIDE — 2026-08-03 (M-06/M-07):** A4b 下方的十臂表保留作歷史對帳，不能當作現行 scored matrix。介入退火已移除；`abl9k_strategy3_annealed` 是 frozen YAML 相容別名，沒有獨立機制或獨立結果。現行唯一三策略代表是 `abl9k_strategy3_static`，9 個 unique arm 的重排與 prereg/hash 邊界見 `../beamshift/docs/review/S11a-ABLATION-REORDER-2026-08-03.md`。英譯不得把這個歷史別名寫成仍在作用的機制。

> **用途。** 後續 Phase C「一次性英文重譯」的**唯一**用詞權威,讓全文英譯**一致**且 **RED-LINE 安全**。
> 本檔**只**鎖定用詞,**不**翻譯論文本體。任何譯詞若有 RED-LINE 風險 → refute-by-default(預設拒用)。
>
> **權威來源(approved English 全部 harvest 自這些,不自創):**
> - `thesis-mc/outputs/thesis-cover.docx` = 三版本最終封面題名與封面文字（USER 2026-08-10）。
> - `thesis-mc/mc-modqn-base.md`(行 28–36)= 雙語 Abstract + Keywords(headline 術語的 gold English)。
> - `thesis-mc/FRAMEWORK-SPEC.md` §0/§3(機制術語)+ §7(RED LINES)。
> - `thesis/THESIS-FRAMING-DECISION-2026-06-28.md`(framework-wins 敘事:MCRL、catfish = named core component)。
> - `thesis-mc/VOICE-CALIBRATION.md` §C(banned jargon)+ `thesis-mc/REFERENCES.md`(venue/author English)。
>
> **封面凍結（USER 2026-08-10）。** `outputs/thesis-cover.docx` 目前的題名、封面文字與版面均已
> final/frozen。本次換上後，後續建置只能原樣沿用既有 frozen cover；不得編輯、重生、改題、翻譯掃詞
> 或重新設計封面，除非 USER 日後明示解凍。封面不屬於後續翻譯掃詞或一致性批次的可編輯範圍。
>
> **讀法。** PART A = LOCKED 譯詞(中文 | English(LOCKED)| note/RED-LINE)。PART B = FORBIDDEN English
> (永不出現在英譯)。PART C = 誠實措辭(grounded / hypothesis / 預期 / 待驗證)的英譯,**去 AI-meta**。
> code / 符號 / 路徑 / 識別字一律保留英文原樣(見 PART B 末「code-identifier 例外」)。

---

## PART A — LOCKED 術語表

### A1. 框架與貢獻(headline;敘事 binding)

> **⛔ 部分列 = OLD-LINE(2026-07-19)。** 「估值／分配兩步」框架已於 `546e622b` 退場,`deferred/` 的舊 ch5
> 數字不得引用。下方標 `[SUPERSEDED]` 的列**只標記、不刪除、LOCKED 字串一字不改**(讀舊稿/舊圖時仍需要),
> **但不得用於新英譯**。現行框架的對應詞條見 **A5c**。
> 現行的「多目標綜合價值」由式 (4.13) 的 $V_u^d(a,t)$ 表示；$b_u(c,t)$ 已專用於候選索引到
> 實際衛星－波束對的映射，不得再拿來表示綜合價值。

| 中文 | English (LOCKED) | note / RED-LINE |
|---|---|---|
| 鯰魚多目標強化式學習（MCRL） | Multi-Catfish Reinforcement Learning (MCRL) | 方法名（非論文標題）。首見拼全名，之後使用 MCRL 或 the framework。現行 Multi-Catfish 機制包含經驗塑形、獎勵塑形與懲罰塑形三種訓練策略；部署仍採 per-user argmax。 |
| (封面論文標題 verbatim) | Energy-Efficient Handover Decision for LEO Multi-Beam Satellite Networks Based on Angle-Aware Multi-Catfish MODQN | **TITLE — DO NOT ALTER**。USER 2026-08-10 明示三版本後續一律以 `outputs/thesis-cover.docx` 替代 Markdown 產生的封面；封面中文題名逐字為「低軌道多波束衛星網路之節能型換手決策：基於角度感知多鯰魚式多目標強化學習」。2026-07-19 的 Markdown 題名只留在會被建置器移除的 front matter，不再是最終 DOCX 封面權威。標題只能由 USER 明示裁決變更，機械掃詞不得自行改動。 |
| 整合的 Multi-Catfish 框架 | integrated Multi-Catfish (MCRL) framework | 首見可寫全名，之後統一用 MCRL 或 the framework，不加 proposed。 |
| MCRL | Multi-Catfish Reinforcement Learning (MCRL) | 縮寫與展開字均為現行名稱；不得恢復 Coordinated 或 Capacity-aware 等已退役展開。 |
| 主代理／鯰魚代理 MODQN | main agent / catfish agent | MCRL 的兩個 MODQN 代理；各自是一組三目標 MODQN，鯰魚代理只在訓練期存在，部署時整組移除。 |
| 鯰魚代理的三個目標 Q 網路 | the three objective Q-networks of the catfish agent | $Q_j^M\leftrightarrow Q_j^{CF}\leftrightarrow r_j$ 一一對應；鯰魚端三個網路共用一條軌跡與一個 $D_{CF}$。不得寫成 three independent catfish agents。 |
| [SUPERSEDED] 估值(步驟) | valuation (step) | 框架兩步之一;三隻 catfish 對每使用者每候選波束算 combined value。abstract 措辭:"valuation, in which the three catfish produce a multi-objective combined value" |
| [SUPERSEDED] 分配(步驟) | allocation (step) | 框架兩步之二;**框架內的一步**,用 catfish 的 combined value;**不可**寫成獨立於 catfish 的功勞/獨立模組(RED-LINE #2)。**但誠實的另一半同樣 binding(FRAMEWORK §0/§6):** 消融如實呈現「**分配規則**是降低過度集中的機制、catfish 訓練沒有額外可量測效益(A2≈A1)」;win 歸給**框架**,**永不**寫 catfish 造成解崩。abstract:"allocation, in which a coordinated beam allocation replaces the per-user argmax" |
| [DEAD] 協調式波束分配 | coordinated beam allocation | **唯一**譯法。**禁** auction / bid / decode(舊譯已棄)→ PART B。Keywords 已收 "Coordinated Beam Allocation" |
| （多目標）綜合價值 | (multi-objective) scalarized value | 以式 (4.13) 的 $V_u^d(a,t)$ 表示。$b_u(c,t)$ 只作候選映射；不得譯為 bid。 |
| [SUPERSEDED] 估值與分配兩步整合 | valuation–allocation two-step integration | 框架 = 兩步整合,以 catfish 為核心 |

### A2. 系統 / 問題(背景)

| 中文 | English (LOCKED) | note |
|---|---|---|
| 低軌衛星 | Low Earth Orbit (LEO) satellite | USER 2026-08-10 中文固定用語；中文正文中的複合用語也以「低軌衛星」為核心，例如「多波束低軌衛星網路」。凍結封面題名是唯一例外；英文 keyword 維持 "Low Earth Orbit Satellite"。 |
| 多波束(網路) | multi-beam (network) | keyword "Multi-Beam Network" |
| 非地面網路 | non-terrestrial network (NTN) | |
| 換手 | handover | **禁** "handoff";keyword "Handover Decision" |
| 波束換手 | beam handover | 本論文自有模型與事件成本的統一用語；式 (3.16) 使用 $E_{\mathrm{ho}}$、$b^{\mathrm{ho}}_{s,v}(t)$。Chen 等人 [4] 的方法名與來源特定描述 `fast beam switching` 是引文例外，不得改寫來源名稱 |
| 換手決策 | handover decision | |
| 換手成本 | handover cost | = r2 對應的目標名;abstract "handover cost" |
| 負載平衡 | load balancing | = r3;keyword "load balancing" |
| 多目標強化學習 | multi-objective reinforcement learning (MORL) | keyword |
| 多目標深度 Q 學習網路 | Multi-Objective Deep Q-Learning Network (MODQN) | abstract gold;首見全名 + 縮寫 |
| 原始 / 既有 MODQN | the original MODQN / Plain MODQN | baseline 指涉;見 A4 arms |
| 吞吐量 | throughput | ⚠ 允許用於 (a) 描述「原 MODQN 把吞吐量當第一獎勵」的**被取代**設計;(b) 物理被服務速率("receive little/zero throughput",gold abstract)。**但 r1 ≠ throughput**(r1 = energy efficiency)→ 見 A3 硬鎖 |
| 偏軸角 | off-axis angle | abstract gold |
| 天線增益 / 波束增益 | antenna gain / beam gain | abstract gold |
| 發射功率 / 波束發射功率 | transmit power / beam transmit power | abstract gold |
| 訊號與干擾加雜訊比 | signal-to-interference-plus-noise ratio (SINR) | abstract gold |
| 干擾 | interference | |
| 仰角 | elevation angle | ch3 幾何 |
| 斜距 | slant range | ch3 幾何 |
| 服務品質 | quality of service (QoS) | |
| 過度集中(波束) | (beam) over-concentration | abstract gold("beam over-concentration");**禁**「崩潰是 catfish 解的」式假因果 |
| (每顆衛星)同時啟用波束數上限 | per-satellite limit on the number of simultaneously active beams | abstract gold;簡寫 "per-satellite active-beam cap" / "capacity limit" |
| 容量限制 / 容量上限 | capacity limit / capacity cap | 以 $v_{\max}$ 表示每顆衛星同時啟用的波束數上限。 |
| 實際衛星－波束對 | physical satellite--beam pair | 候選索引透過 $b_u(c,t)$ 對應到實際衛星與波束。 |
| 波束 / 波束槽 | beam / beam slot | 動作空間 = 衛星×波束槽 |
| 被服務的使用者 | served users | abstract "the number of served users" |
| 活躍 / 被用到的波束 | active beams | abstract "active beams";崩潰 → 數量少 |
| (尾端)使用者覆蓋 | (tail) user coverage | abstract "high user coverage";`min_cov` = minimum tail coverage |
| 排不進去 / 被擠掉的使用者 | users that do not fit / are pushed out | abstract 措辭:"pushed out and receive little throughput"。**禁**「餓死 / starve / starvation」(student voice)→ 用 "pushed out" / "receive little (or zero) throughput" / "left unserved" |
| 各自取最大值 / 每位使用者各自挑分數最高的波束 | per-user argmax | MCRL 保留的部署選法：每位使用者從自己的可行候選中選取綜合價值最高者。`independent per-user selection` 只可作解釋，不另立方法名稱。 |

### A3. 三個目標 + 指標(RED-LINE 重災區)

| 中文 | English (LOCKED) | note / RED-LINE |
|---|---|---|
| r1 = 角度感知能量效率 | r1 = angle-aware energy efficiency | **★ 硬鎖:r1 NEVER "throughput"。** 歷史 bug #19/#20(train/eval r1 退回吞吐量)。keyword "Energy Efficiency"。abstract:"replaces the original throughput reward with an angle-aware energy efficiency objective" |
| 能量效率 | energy efficiency (EE) | |
| 角度感知 | angle-aware | |
| r2 = 換手成本 / 換手懲罰 | r2 = handover cost (handover penalty) | |
| r3 = 負載平衡 | r3 = load balancing | |
| 校準後的三目標純量化 | calibrated three-objective scalarization | 三個目標先以固定正數 $c_j$ 調整尺度，再以 $\Omega=[\omega_1,\omega_2,\omega_3]$ 合成綜合價值；原始單位下的有效權重為 $\omega_j/c_j$。 |
| 三目標純量化權重 | three-objective scalarization weights | 以 $\Omega$ 表示；不得另造現行正文未定義的 $J_w$。 |
| 純量化 | scalarization | `v_u(a)=Σ_k w_k Q_k`;原 MODQN 把多目標純量化 |
| 達標率 | QoS satisfaction rate | = `qos` 欄 |

### A4. Arms(消融臂;LOCKED 標籤 ↔ 內部碼)

> **★ 內部碼 B0/B1/B2/A1/A2 不出現在英譯本文** —— 本文用下方 LOCKED 標籤。**例外:** "AF" 依任務指定保留為該臂的**已定義縮寫**(an opaque defined abbreviation),**永不展開**成 auction/decode 來源。消融數字如實呈現(RED-LINE #1)。


> **⛔ 本表整體 = OLD-LINE PROVENANCE(2026-07-19)。** B0/B1/A1/B2/A2/AF 是 route-B「協調式波束分配」線的臂名;
> 該線的方法章與結果章已於 `546e622b` 退場(舊 ch5 存於 `deferred/`,其數字**不得引用**)。**現行消融 = ch4 §4.8 的
> 八列階梯**(基準 → ＋情境正規化 → ＋三策略 → ＋競爭獎勵 → ＋容量懲罰 → 完整 → 無退火對照 → 完整去競爭獎勵),
> 其 LOCKED 英文標籤**尚未訂**(需 USER 命名後補進本表)。下表僅供讀舊稿/舊圖時對照,**不得用於新英譯**。

| 內部碼 | English label (LOCKED) | 定義 | note / RED-LINE |
|---|---|---|---|
| B0 | Plain MODQN (frozen baseline) | 各自 argmax;凍結 baseline、無 state-aug | = 教授的 bar;崩潰參考 |
| B1 | Plain MODQN + congestion context | 各自 argmax;+χ_u、plain TD 訓練 | aug credit = B1−B0(**需與 B0 區分標籤才讀得出**,RED-LINE #1)|
| ~~A1~~(DEAD) | MCRL (Allocation-Only) | coordinated beam allocation(分配步驟 ON)+ plain training | 與 B2「Training-Only」對稱:只開框架的**分配**半邊。**禁** "Inference-Only"(inference=推論 banned jargon;見 PART B)|
| ~~B2~~(DEAD) | MCRL (Training-Only) | catfish training(估值/訓練半邊 ON)+ 各自 argmax(分配步驟 OFF) | 仍崩(regime-trapped);隔離 catfish 訓練 credit |
| ~~A2~~(DEAD) | Proposed MCRL | coordinated beam allocation + catfish training | **本文主方法**;A2≈A1(誠實當消融) |
| ~~AF~~(DEAD) | Coordinated Allocation Heuristic (AF) | 固定規則、**不學習**的 coordinated beam allocation | gate-control / 無學習 kill-test;"AF" = opaque 已定義縮寫,**禁**展開成 auction、**禁** "auction heuristic"。學習版要贏過它 |

| 弱靜態對照 | English label (LOCKED) | note |
|---|---|---|
| RSS_max | RSS_max (received-signal-strength baseline) | 弱靜態;A1 贏 |
| round_robin | round_robin | 弱靜態 |
| DQN_throughput | DQN_throughput | 弱靜態;A1/A2 平均較高但 J_w **CI 重疊** → 框成「覆蓋贏」不是「J_w CI-separated 贏」 |
| DQN_scalar | DQN_scalar | ⚠ **內部對抗 stress-test,非教授 bar。** **禁**「在原始加權純量上贏 DQN_scalar」(RED-LINE #3)。**兩面如實:** DQN_scalar 在 raw 加權純量上**領先**(A1 4.97e-4 < DQN_scalar lci 5.96e-4,**需揭露**);框架在**覆蓋/公平軸領先**(min_cov 0.999 vs 0.00)→ 兩者 **Pareto 互不支配**。**禁** "輾壓/crush/dominates DQN_scalar";用 "leads on the coverage/fairness axis" |

### A5. 機制術語(ch4 方法;FRAMEWORK-SPEC §3)

> **⛔ 部分列 = OLD-LINE(2026-07-19),同 A1 處理原則:只標記、不刪除、LOCKED 字串不改、不得用於新英譯。**
> ⚠ 其中「依目標不對稱折扣 γ=[0.99,0.90,0.99]」一列**內容已被程式碼覆核推翻**：現行非對稱折扣是
> **主代理 MODQN vs 鯰魚代理 MODQN**，$\beta_M<\beta_{CF}$；每一端的三個目標共同使用該端折扣。
> 這一列若被英譯沿用,會把剛更正掉的錯誤重新種回論文,故特別標出。現行詞條見 **A5c**。

| 中文 | English (LOCKED) | note |
|---|---|---|
| 壅塞情境(輸入)χ_u | congestion context (χ_u) | state augmentation;3 個動作前可算的數值(歷史佔用 / 候選競爭者數 / 訊號排名);no-leak |
| 狀態擴充 | state augmentation | 現行 28-candidate schema：原始狀態 $4N_C=112$ 維，$\chi_u$ 增加 $3N_C=84$ 維，使 $s^{\chi}_u$ 為 196 維；情境正規化串接後的 $\tilde{s}_u$ 為 392 維。ch3 的 $\rho_u$ 僅是 handover 的**服務衛星**記號（沿用 MODQN 原文 $\rho_i(t)$，2026-08-21 由 hat notation 改回），勿與 SINR 的 $\gamma^e_{u,s,v}$ 混用 |
| 歷史佔用 | historical occupancy | χ_u[..,0] |
| (候選)競爭者數 | number of (candidate) contending users | χ_u[..,1] |
| 訊號排名(user-specific) | (user-specific) signal rank | χ_u[..,2];打破對稱的關鍵 |
| [SUPERSEDED · 內容有誤] 依目標不對稱折扣 γ | asymmetric per-objective discount (γ) | catfish 版 γ=[0.99,0.90,0.99];plain 版 γ=0.9。標 `hypothesis`(MORL 常見選擇,非 CDRL 直接繼承) |
| 折扣因子 γ | discount factor (γ) | 順手解釋一句:決定未來 Q 值的重要性,常 0.9–0.99(student voice) |
| [SUPERSEDED] 價值分層回放 | value-stratified replay | catfish 版:高 J 轉移進 priority pool,minibatch ρ=0.25 抽自其中。標 `hypothesis` |
| 經驗回放 / 回放池 | experience replay / replay buffer | |
| [SUPERSEDED] 優先池 | priority pool | |
| [理由句過期] step-bundle(整步一起存) | step-bundle | 協調分配是「一步所有人一起」→ 整步存 |
| 目標 Q 網路 | per-objective Q-network | 三個目標各一個 `DQNNetwork`;**不改 `modqn.py`**(G1) |
| 候選波束 | candidate beam | |
| [DEAD] cross-over(交換分配規則) | cross-over (swapping the allocation rule) | 同一組 Q 換分配規則 → 崩潰翻轉 → 證明「解崩靠分配規則,不是 catfish 訓練」(`grounded`) |

---

### A5c. 現行框架機制詞條(2026-07-19 新開;取代 A5 中標記過期的列)

> **全表已 LOCKED(2026-07-19)。** 前段各列的英文直接取自 ch4 的英文節名(論文自身已用的字面,既成 gold);
> 後段九列由 USER 於 2026-07-19 逐條定案。本表無待確認項,英譯可直接依用。

| 中文 | English | 狀態 | note |
|---|---|---|---|
| 情境正規化 | context normalization | LOCKED(ch4 §4.2 節名) | 式 (4.8a)–(4.9)；在同一時間步跨使用者、逐維度計算平均與標準差，再把原始擴充狀態與正規化結果串接。**禁**譯成 batch normalization；也不另設正文未使用的 `CN_u(·)` 運算子。 |
| 能效分層 | energy-efficiency stratification | LOCKED(USER corrected topology 2026-07-28；消融短名仍可寫 `stratification`) | 式 (4.10)；單一 $F_W$ 與 $D_{CF}$，以步級平均原始 $r_1$ 分流完整三目標轉移束 |
| 非對稱折扣 | asymmetric discounting | LOCKED(A4b 第 10 列 `w/o asymmetric discount`) | 主代理 MODQN 採 $\beta_M$，鯰魚代理 MODQN 採 $\beta_{CF}$；端內三目標共同使用該端折扣，式 (4.11) |
| 週期性介入 | periodic intervention | LOCKED(USER corrected topology 2026-07-28) | 式 (4.12)；共同觸發、唯一 $B_I$ 更新主代理三個 $Q_j^M$ |
| ~~介入退火~~(**已自論文移除 2026-07-20**) | ~~intervention annealing~~ | **DEAD — 不得用於英譯** | USER 2026-07-20:機制仍在測試中,ch4 §4.4 連同式 (4.14)(4.15) 已整節刪除,章節與式號已重編。**英譯若出現 `annealing` 一律視為錯誤**(唯一例外＝ε-greedy 探索的 "linear annealing",那是標準 DQN 超參,與本機制無關)。此列只作讀舊稿對照 |
| 競爭獎勵機制 | competitive reward mechanism (ACRM) | LOCKED(USER corrected topology 2026-07-28) | 式 (4.14)；只整形能效軸 $r_1$，單一 $\eta_w$，線性、tanh 關閉；兩次完整 joint-action rollout 各用自己的 $R_u/P^{sys}$，不用 $\kappa$ 分母；$r_2,r_3$ 保持原始獎勵 |
| 容量懲罰 | capacity penalty | LOCKED(見 A5b) | 式 (4.17)；與 per-satellite beam cap 的分辨見 A5b。**【⚑ 2026-08-21 已自論文移除】式 (4.17)、圖 4-8 及整節 §4.5 均已刪除（2026-08-21）；本詞條保留作歷史辨識，不得用於描述現行方法。** |
| 主要代理 | main agent | LOCKED(USER 2026-07-19) | 與 catfish-side MODQN 相對；只有主要代理部署 |
| 兩個經驗池(合稱) | one main replay buffer and one catfish replay buffer | LOCKED(USER corrected topology 2026-07-28) | $D_M$ 與 $D_{CF}$；兩端不共用，鯰魚代理三網路共用 $D_{CF}$ |
| 主要經驗池 | main replay buffer | LOCKED(USER 2026-07-19) | **用 buffer 不用 pool** — 見本表下方裁決註 |
| 鯰魚經驗池 | catfish replay buffer | LOCKED(USER corrected topology 2026-07-28) | 單一 $D_{CF}$；鯰魚代理三個目標網路共用 |
| 混合批次 | mixed mini-batch | LOCKED(USER corrected topology 2026-07-28) | 唯一 $B_I$；比例 $\rho_I$ 自 $D_{CF}$。注意連字號 `mini-batch` |
| 同狀態配對比較 | paired same-state action comparison | LOCKED(USER 2026-07-28；取代 2026-07-19 舊譯) | §4.4；單一同步對照環境副本 $\bar E_{CF}$，在相同前置狀態與 stochastic realization 下只改變完整聯合動作，且只比較能效軸；$\eta_w>0$ 時多一步 matched environment step，$\eta_w=0$ 時跳過 |
| 偏好質量 | preference mass | LOCKED(USER 2026-07-28) | $\Pi_{s,v}$，式 (4.16)；使用者偏好 $\pi_u(a)$ 依實體波束彙總後的量 |
| 尾端質量 | tail mass | LOCKED(USER 2026-07-19) | $\Delta_s$，式 (4.17) |
| 每位使用者的能效貢獻 | per-user additive energy-efficiency contribution | LOCKED(current formula) | 式 (3.26) 使用 $r_{1,u}=R_u/P^{\mathrm{sys}}$，其使用者總和等於該時間步的系統能量效率。 |

> **buffer vs pool 裁決註(2026-07-19)**:USER 指示「若 ch4 既有英文用 pool 則統一 pool,以 ch4 gold 為準」。
> 查證結果:**ch4 全章沒有任何英文 pool/buffer 字樣**(中文行文,英文只出現在節名),因此 ch4 無 gold 可依;
> 最近的存活 gold 是 A5 的「經驗回放 / 回放池 → experience replay / **replay buffer**」。
> ⟹ **全篇統一用 `buffer`**。A5 的「優先池 / priority pool」屬已被取代的價值分層回放設計(該列已標
> `[SUPERSEDED]`),不構成 pool 的依據。

---

### A4c. 現行三種塑形策略

> 三種策略都屬於 Multi-Catfish 機制的一部分，正文以一般方法敘述介紹即可。懲罰塑形直接在
> 主代理的訓練目標中加入 $\lambda\sum_s(\Delta_s/N_U)^2$，不得寫成由另一個競爭者代理產生。

| 中文 | LOCKED 英文 | 備註 |
|---|---|---|
| 鯰魚機制 | catfish mechanism | 傘詞 |
| 經驗塑形 | experience shaping | 能效分層、非對稱折扣與週期性介入。 |
| 獎勵塑形 | reward shaping | 競爭獎勵機制 ACRM，只調整鯰魚端的第一目標獎勵。 |
| 懲罰塑形 | penalty shaping | 容量懲罰 $L$，直接作用於主代理的訓練目標。**【⚑ 2026-08-21 已自論文移除】懲罰塑形整節（原 ch4 §4.5）連同式 (4.15)–(4.17) 與圖 4-8 均已刪除；現行塑形策略僅剩兩種（經驗塑形、獎勵塑形）。本詞條保留作歷史辨識與英譯對照，不得用於描述現行貢獻。** |

**歷史消融標籤（只供辨認舊稿，不是現行結果章權威）**

| 中文 | LOCKED 英文 | 對應表 4-1 列 |
|---|---|---|
| 完整 MCRL | Full MCRL | 6 |
| 完整 MCRL w/o 懲罰塑形 | w/o penalty shaping | 4 |
| 完整 MCRL w/o 獎勵塑形 | w/o reward shaping | 8 |
| 完整 MCRL w/o 目標塑形 | w/o objective shaping | 3（已退役的舊分類；重建消融時須另定現行名稱） |
| 原始 MODQN | MODQN (raw) | 1 |

### A4b. 消融對照十臂(ch4 §4.8 表 4-1;**LOCKED — USER 定案 2026-07-19;⚠ 上方 A4c 為現行體系,本表僅供對帳**)

> 舊 arm 標籤(A4 表 B0/B1/A1/B2/A2/AF)已全部 DEAD,本表取代之。中文欄＝ch4 表 4-1 的正式列名;
> 英文欄＝USER 定案的 LOCKED 全名(用於表格與內文);**主圖短標籤**只給會出現在主結果圖的線,
> 其餘臂進 §5.3.4「補充消融組」。第 6 列是完整方法,第 4／8／9／10 列各自只從它拿掉一個機制。

| # | 中文(ch4 表 4-1) | English (LOCKED) — 表格/內文全名 | 主圖短標籤 |
|---|---|---|---|
| 1 | MODQN 基準(原始輸入) | MODQN baseline (raw state) | `MODQN` |
| 2 | MODQN ＋情境正規化 | MODQN with context normalization (z-score) | `MODQN+z-score` |
| 3 | 三策略鯰魚式訓練(退火介入) | three-strategy catfish, annealed intervention (no ACRM, no capacity penalty) | —(§5.3.4) |
| 4 | 完整 MCRL 去容量懲罰 | MCRL without capacity penalty | `w/o capacity penalty` |
| 5 | 僅容量懲罰(診斷錨點) | capacity penalty only (diagnostic anchor; not a framework variant) | —(§5.3.4) |
| 6 | 完整 MCRL | MCRL (full) | `MCRL` |
| 7 | 三策略鯰魚式訓練(固定介入) | three-strategy catfish, static intervention (annealing control) | —(§5.3.4) |
| 8 | 完整 MCRL 去競爭獎勵機制 | MCRL without ACRM | `w/o ACRM` |
| 9 | 完整 MCRL 去能效分層 | MCRL without stratification | `w/o stratification` |
| 10 | 完整 MCRL 去非對稱折扣 | MCRL without asymmetric discount | `w/o asymmetric discount`(條件線) |

> **兩條命名約束(已滿足,改動時勿破壞)**:
> 1. 第 5／第 6 列都含容量懲罰,靠 `only (diagnostic anchor; not a framework variant)` 對 `(full)` 區分
>    「單獨加」與「在完整堆疊裡」;第 5 列的 `not a framework variant` 不可省——它擋掉「把診斷錨點讀成
>    框架變體」的誤解。
> 2. 第 3／第 7 列**同名同機制**,只以括號 `annealed` / `static intervention (annealing control)` 區分排程,
>    不可另取兩個名字,否則讀者會以為是兩個不同機制。
>
> **第 10 列＝條件線。** ch4 §4.3／§4.8 帶一條事前宣告規則:若第 6 列與第 10 列之差判定為 NEUTRAL,
> **非對稱折扣自框架敘述刪除**,並引該臂為證。⟹ 英譯時第 10 列的標籤與表說必須保留這個條件性;
> 若規則觸發,框架描述(ch1／ch4／ch6／摘要)一併移除該機制,本列改記為移除依據。

---

### A5b. 英文消歧對(容易被譯混的兩個「capacity」;2026-07-19 新增)

| 中文 | English (LOCKED) | 這是什麼 | **不是**什麼 |
|---|---|---|---|
| 每顆衛星可同時啟用的波束數上限 $v_{\max}$ | **per-satellite beam cap** $v_{\max}$ | 環境的硬約束(式 3.4a);環境端強制執行,與方法無關 | **不是** capacity penalty;不可譯成 "capacity limit penalty"、"beam capacity constraint loss" |
| 容量懲罰 $L$ | **capacity penalty** $L$ | 方法的一個機制(ch4 §4.6):把上述上限寫成可微分懲罰項加進**訓練損失** | **不是** per-satellite beam cap 本身;**不是**部署時的約束(部署選法不變) |

> ⚑ **2026-08-21 狀態更新**：容量懲罰 $L$（下表第二列）已隨 §4.5 整節自論文移除（2026-08-21）；$v_{\max}$（上表第一列）仍為場景參數，但不再作為論文貢獻機制列舉。兩詞條保留作歷史辨識與英譯對照。英譯時若遇「penalty shaping」、「capacity penalty $L$」或式 (4.15)–(4.17)，視為已移除的機制，不應出現在描述現行方法的句子中。

> 一句話分辨:**cap = 環境給的;penalty = 方法自己加的**。英譯中兩者同段出現時,務必用上面兩個 LOCKED 詞組,
> 不可互相代換,也不可只寫 "capacity" 讓讀者自行猜。框架名裡的 **Capacity-aware** 指的是**後者**
> (學習端感知到前者)。

---

## PART B — FORBIDDEN English(**永不**出現在英譯本文)

> 出現任一 = RED-LINE 風險,Phase C 譯者**必須**改寫成 PART A 的 LOCKED 譯詞。

### B1. 機制 jargon(用 PART A 譯詞取代)

| FORBIDDEN | 為何禁 | 改用 |
|---|---|---|
| auction / bid / bidding | 舊譯;敘事已棄(USER 2026-06-28) | coordinated beam allocation / combined value |
| decode / decoder / decoding | jargon + 舊機制名 | coordinated beam allocation / allocation step |
| distill / distillation | route-C 死脈;與框架敘事相反 | (不需要 —— 框架不是蒸餾) |
| amortized / amortization | jargon(攤銷);route-C 脈絡 | (避免;若必須提 field name 則 ch2 一次性,本文不用) |
| mapping(映射式) / forward-inference(前向推論) | banned jargon(VOICE §C) | "online selection" / 平鋪描述 |
| 映射 / 前向推論 / 攤銷 / 解碼器 / 蒸餾 / 推論(中文 jargon) | banned jargon(VOICE §C) | 學生白話 + PART A 譯詞 |
| 拍賣 / 出價(中文) | 舊譯已棄 | 協調式波束分配 / 綜合價值 |
| decorative / 裝飾性 | self-貶損;非敘事 | (不寫;catfish = named core component) |
| starve / starvation / 餓死 | student-voice(VOICE);非 abstract 措辭 | "pushed out" / "receive little/zero throughput" / "left unserved" |
| main agent / 主代理 | banned(C-定稿) | (依實際組件名) |
| handoff | 拼寫變體;A2 已宣告禁,集中於此使清單自足 | handover |
| inference(裸用作機制名 / 臂名,如 "Inference-Only") | inference = 推論(VOICE §C banned);舊機制 = forward-inference | "allocation" / "online selection";臂名用 "MCRL (Allocation-Only)"。**例外:** 「training vs inference」通用 RL 語境的 inference 允許 |

### B2. 假因果 / over-claim(RED-LINE;**任何形式**都禁)

| FORBIDDEN(任何近義) | 為何禁 | 真相 |
|---|---|---|
| "catfish drives/causes the win" | RED-LINE #2;消融打臉(A2≈A1) | 解崩靠**分配步驟**;catfish = named core component(by-association) |
| "removing catfish causes collapse" | RED-LINE #2;cross-over 打臉 | 換**分配規則**才翻轉崩潰,非 catfish 訓練 |
| "ablation proves catfish training is the main driver" | RED-LINE #2 | A2≈A1 → catfish 訓練非因果主驅動 |
| "beats Sun2024" / "outperforms Sun2024"(當 headline) | RED-LINE #5 | 可引 "the original MODQN [2]" / "Sun et al. [2]" 為 MODQN 來源;**不**當勝負 headline |
| "wins on the (original weighted) scalar over DQN_scalar" | RED-LINE #3 | DQN_scalar = 內部 stress-test;只框「公平/覆蓋軸」 |
| "solved the (collapse) root cause" / "fixes the root cause" | RED-LINE #5;ROOT-Q UNRESOLVED | 框架**繞過**崩潰(換分配規則)+ matched 相對贏 |
| "2.8×" / "3.85×" / "0.72C" | RED-LINE #5;family_b-specific 舊數字 | 不放;用實際 RESULT.json 值 + `grounded` 標記 |
| "guarantees full coverage" / "保證全覆蓋" | FRAMEWORK §3B 誠實邊界 | k_cap 名額是結構保證;**覆蓋是量測結果**(min_cov / served / cap_bump 講) |
| "outperforms / beats the original MODQN **[2]**" / 把 win 動詞與 [2]/Sun 放**同一子句** | 把 win 綁上 Sun2024 引用 = "beats Sun2024"(RED-LINE #5) | 比較 baseline = **我們在凍結 env 重實作的 MODQN**;[2]/Sun **只**在介紹 MODQN 方法**來源**時引,**不**與 win 動詞同句。(abstract gold "outperforms the original MODQN"〔無 [2]〕仍允許)|

### B3. code-identifier 例外(允許,但**不入本文 prose**)

`auction_decode.py` / `decode_af_physical_auction` / `decode_a0_argmax` / `congestion_context.py` / `shaped_q.py`
= **凍結 code 識別字**,在「程式碼 / 路徑 / 附錄程式清單」可原樣保留(code 一律英文)。但**論文 prose / 圖標籤 / 演算法框**
**不可**出現 auction / decode 字樣 → 一律改用 PART A 的 "coordinated beam allocation"。若圖/演算法框引用到這些識別字 → 改標籤。
**含 auction/decode 的檔案路徑只可出現在 code block / 附錄程式清單**,running methods prose **不可**寫出該路徑 → prose 一律以 LOCKED 名 "coordinated beam allocation" 指涉該機制。

---

## PART C — 誠實措辭英譯(去 AI-meta;對標 ris 學生口氣)

> VOICE §C:**無 AI-meta**(誠實-meta / 值得注意的是 / 需要再次強調)。英譯同理避開 "it is worth noting" /
> "it should be emphasized" / "notably" / "importantly" / "honestly" / meta 自評句。claim 直接、少 hedge,
> 但 RED-LINE 仍守 → 用樸素的「預期 / 待驗證 / 第五章報告」表達。

| 中文意圖 | English (LOCKED 範式) | 避免 |
|---|---|---|
| `grounded`(已證實驗結果) | "Experiments show that …" / "The results confirm that …" / 直述事實 | "we honestly find" / meta 標籤入 prose |
| `hypothesis`(未證假設) | "is expected to …" / "should …" / "remains to be verified" / "is left to Chapter 5" | 把假設寫成已證;"obviously" |
| 預期 / 應會 | "is expected to" / "we expect" / "should" | "must"(過強) |
| 待第五章驗證 / 留待評估 | "is evaluated in Chapter 5" / "Chapter 5 reports …" / "this is examined in Chapter 5" | "will be proven"(預判結果) |
| 標 `grounded`/`hypothesis`/`ruled-out` | (這些是**內部標記**,**不**直譯進 prose;用上面措辭體現語氣即可) | 把 `grounded`/`hypothesis` 字樣寫進論文句子 |
| k_cap 是崩潰主因之一(grounded;3/15 點 + sweep pending) | "one of the causes of the collapse";**兩面如實:** "under tight capacity the proposed framework leads on the weighted metric; under very loose capacity the over-concentration is mild and the weighted-metric advantage shrinks and no longer leads, while user coverage and energy efficiency lead at all capacity settings" | "the root cause" / "solved";寫成「優勢在所有 k 都領先」(只覆蓋/EE 是,J_w 不是)|
| 框架繞過崩潰 + matched 相對贏 | "under the same environment, seeds, and budget, the framework changes only the allocation rule and training, and is compared on a relative basis" | "solves the collapse" |
| catfish 拿 credit(by-association) | "catfish is a named core component of the framework that produces the combined values" | "catfish causes / drives the win" |
| **A2≈A1(消融誠實;BLOCKER-fix)** | "Adding catfish-style training on top of the coordinated beam allocation gives results statistically indistinguishable from plain training (A2≈A1); the coordinated beam allocation is the component that reduces over-concentration, and catfish is the named core component that produces the values it uses." | "catfish has no effect" / "decorative" / "catfish drives the win" |
| **cross-over(消融誠實;BLOCKER-fix)** | "Holding the trained value networks fixed and changing only the allocation rule reverses the collapse, which shows the allocation rule — not the training recipe — produces the de-collapse." | "removing catfish causes collapse" / "catfish causes the de-collapse" |
| 覆蓋 + EE 在所有 k 領先(grounded;ZH abstract only) | "on user coverage and energy efficiency the proposed framework leads across all capacity settings" | ⚠ 此 grounded claim 在 ZH abstract(`mc-modqn-base.md:34`)有、EN abstract(`:30`)**無** → Phase C 重譯 EN abstract 時補上 + 向 USER 對齊(見邊界) |

---

## 邊界 / 不變量

- 只動 `thesis-mc/`。`thesis/` = 死的 route-C,不碰。G1 `modqn.py`(`aa877676`)+ env `family_b_step.py`(`389eaaef`)**唯讀**。
- 本檔**不**翻譯章節,只鎖用詞;Phase C 重譯以本檔為唯一用詞權威。
- 任何新譯詞若與 PART B 衝突 → refute-by-default,回查 PART A 找 LOCKED 替代;無替代 → 停、問 USER。
- 載重譯詞定稿前過 cross-model voice/claim check(memory #16/#17:同模型聞不到自己 AI 味)。
- **⚠ FLAG to USER(EN/ZH abstract mismatch):** ZH abstract(`mc-modqn-base.md:34`)有 grounded 句「在使用者覆蓋與能量效率上,本文方法在所有容量點都維持領先」,EN abstract(`:30`)**缺**此句。Phase C 重譯 EN abstract 時須補回(用 PART C「覆蓋 + EE 在所有 k 領先」LOCKED 句),並向 USER 確認兩語版一致。
