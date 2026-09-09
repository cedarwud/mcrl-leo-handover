# DELTA-MAP：V0.23 方法草稿 → V0.25 物理繼任者（逐節處置圖）

- **狀態：** `PAPER-LANE-A v2 DRAFT`（不是 empirical-final；不含任何結果數字）
- **基準文件：** `mcrl-thesis-ZH-v023-method-draft-20260905.docx`（僅讀，不改）
- **繼任來源：** `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION` v1.0 與 v1.1–v1.9 修訂／勘誤、
  `V025-CONTINGENCY-LADDER-PREOUTCOME` 與 amendment 1（R7）、
  `V025-STAGES-6-8-CONTRACT` v1／v1.1／v1.2、全部 `V025-CONTROLLER-DECISION(S)-*`、
  `V025-DESIGN-FREEZE-AND-CLOSURE-RULE`、`V025-PILOT-TRACK-DECLARATION`、
  round9 外部意見（9A／9B／9C／9D）與 `ADJUDICATION-V16-PREREGISTRATION`。
- **符號授權：** `active-symbol-table-v023-20260905.md`；新增量另見 `SYMBOL-ADDITIONS.md`，
  每一個都通過 `SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md` 的單字母／單數字原子規則。
- **輸出邊界：** 本改寫只產生本資料夾內的文字；`docs/`、任何 `.docx` 與
  `/home/sat/mcrl-paper-sources/` 之下的原件均不更動。

---

## 0. 這一版真正改變的物理與方法（改寫的因）

| # | V0.23 稿內的寫法 | V0.25 繼任者的寫法 | 依據 |
|---|---|---|---|
| Δ1 | 逐 segment 錨定遞推功率：新段以 $p^0$ 起始，段內由前一步增益比遞推（式 3.11–3.12），帶 $\tau_{u,s,v}$ continuity 語意 | **無記憶（memoryless）逐使用者速率目標功率控制**：每 30.08 s 步、每個同時輻射的時隙組態獨立求解，$p=\min\{p^{+},\Gamma_r(U_{s,v})(\sigma^2+I)/(H\,G^T)\}$；**沒有 segment、沒有 $\tau$、沒有 $p^0$、沒有跨步狀態** | v1.0 §Declaration；v1.1 §1 |
| Δ2 | 速率為連續 Shannon 式 $\frac{B^w}{U_{s,v}}\log_2(1+\gamma)$ | **離散 ACM 階梯**（EN 302 307-1 Table 13 的 28 列，含 1.7 dB 實作餘裕與 0.20 roll-off 修正）＋**等空中時間 TDM**：速率取模式頻譜效率除以波束佔用人數 | v1.0 §Declaration；stage-1 決議 10、13、16 |
| Δ3 | served ＝ 遮罩通過的動作 ∧ 所需功率 $\le p^{+}$（第 5.1 節「約束的作用範圍」的削頂敘事） | served ＝ **聯合解算後的 PHY 可解碼性**：$\gamma\ge\gamma^{-}=-1.4418$ dB；達不到速率目標者標記 `rate_target_infeasible`、**以上限發射並保留其部分交付、干擾與能量**，不做剪除或重排 | v1.0 §Declaration、§Service definition；v1.1 §2 |
| Δ4 | C3 ＝ two-user LC-SRS teacher，紙面標的 $z_{3,i}=e_i+\Psi/2$，student 只讀 deterministic relational C3View | C3 ＝ **有界目錄上的交互作用殘差 $\Psi_{\mathcal K}$**，協調器是**集合層**的一層；$e_i$ 已被整網 C1 吸收，**繼任者標的不含 $e_i$ 項**；逐使用者 Shapley 分攤只作報告（$K\le 4$） | stage-2 決議 5；contract v1 §B4–B5；v1.7 §3；contract v1.2 §1 |
| Δ5 | 部署為 $Q_1+Q_2+Q_3$ 無權重相加、一次 masked argmax，明文排除 coordinator | 部署為**兩層**：$Q_1+Q_2$ 逐使用者 argmax 形成參考提案 $a^{0}$，再由**集合層選擇器**在有界目錄上選出承諾組態；仍為單次承諾、有截止時間與 fallback | contract v1 §A2、§C1–C2、§F2 |
| Δ6 | 選擇與評分同用一個物理視圖 | **兩個決不混用的分解**：選擇時視圖 $\Omega^{q}$（餘裕調整、決策瞬時）與結果視圖 $\Omega$（實現值、48 個邊界端點）；每一個統計量都標明來自哪一個 | v1.7 §2 |
| Δ7 | 目標為 Main-only network ratio-of-sums EE，三路不投票 | 目標仍是 pooled $\Sigma B/\Sigma E$，但**加上 QoS 共同主要結果**（可用度、換手率、$\Phi$ 計價成本、速率達成率），並明文記錄 **frozen-$\lambda$ 剩餘與 pooled 比值之間的目標落差** | v1.0 §Service definition；v1.2 §5；v1.6 §5 |
| Δ8 | 宣稱結構：「method core 可凍結、efficacy 全開放」 | 宣稱結構升級為**預註冊的階梯與三分法**：Level A／B／C 宣稱階梯、`ADMIT_FULL`／`ADMIT_C1C2`／`NOT_ADMITTED` 收容三分法、$\delta=+0.5\%$ 相對餘裕的交集–聯集合取宣稱、以及 regime-conditional 措辭 | ladder Rung 0；v1.9 §6；v1.2 §4；v1.4 §1；v1.7 §4、§6 |
| Δ9 | （無） | 新增**餘裕調整選擇觀點**（$\alpha$ 分位通道增益因子只作用於想要鏈路的預測接收端，功率仍由名目增益求得）與**目標／發射 MODCOD 對** | v1.6 §1；v1.7 §1；v1.8 §8；v1.9 §1–§3 |
| Δ10 | （無） | 新增**淨避碰值**與**再錨定分解**（於認證單邊局部最適 $a^{1}$ 重錨），作為機制證書 | v1.6 §3；contract v1.2 §5–§6 |

---

## 1. 逐節處置

處置代碼：**KEEP**（原文可用，至多改術語）／**REWRITE**（本次交付替換文字）／
**DELETE**（自繼任稿移除，理由記於此）／**NEW**（本版新增節）。

### 前置與第一章

| 節 | 處置 | 一行理由 |
|---|---|---|
| 標題頁、指導教授、學生資訊 | KEEP | 與物理繼任無關。 |
| 摘要 | REWRITE | 摘要句句綁在 LC-SRS teacher、$z_{3,i}=e_i+\Psi/2$ 與「三路無權重相加一次 argmax」上，三件事都已被 Δ4／Δ5 取代；並須加入 QoS 共同主要結果與宣稱階梯。（本交付未附摘要文字：摘要留待兩份 REWRITE 定稿後回寫。） |
| 關鍵字 | REWRITE | 刪 `LC-SRS`、`預決策關係描述元`；改為 `速率目標功率控制`、`ACM`、`集合層協調`、`交互作用殘差`、`匯總能量效率`。 |
| 1. Introduction 第 1–3 段（NTN／多波束／既有研究背景） | KEEP | 背景陳述不依賴被改的物理。 |
| 1. Introduction 第 4 段（本文定位） | REWRITE | 「鯰魚不表示第二個部署代理」仍成立，但「現行 C3 的訓練教師與部署學生」的資訊邊界敘述已換成「集合層協調器與逐使用者提案頭」的資訊介面。 |
| 1. 貢獻條列第 1 條（「每個 uninterrupted served physical-link segment 以 $p^0$ 起始…遞推」） | REWRITE | 直接與 Δ1 衝突：繼任者沒有 segment、沒有遞推、沒有 $p^0$。 |
| 1. 貢獻條列第 2 條（三個獨立 Q surface 的 route roles） | REWRITE | 角色仍是三條，但 C1 已是整網差分剩餘、C2 已是續值預測、C3 已是集合層交互作用殘差。 |
| 1. 貢獻條列第 3 條（four-profile teacher／C3View／single-pass argmax） | REWRITE | 三個名詞全部被 Δ4／Δ5 取代。 |
| 1. 章節安排段 | KEEP | 章序不變。 |

### 第二章

| 節 | 處置 | 一行理由 |
|---|---|---|
| 2. 章首段 | KEEP | 只是導言。 |
| 2.1 Related Work 第 1–3 段（[1][3][4][5][6] 與 [2][8][9][10]） | KEEP | 文獻回顧本身不受物理繼任影響；第三章引用這些來源處理訊號品質與波束功率的方式仍成立。 |
| 2.1 第 3 段末句「本文保留恰好三個獨立 Q surface…不引入額外協調器」 | REWRITE | 繼任者**確實**引入了一個集合層協調器（作為受評估的一層），此句已與方法矛盾。 |
| 圖 2-1 與其圖說 | KEEP | 仍只作歷史 MODQN baseline 骨幹；圖說末句改指向新的第四章結構。 |
| 2.1 第 4 段（PER [11]、CDRL [12] 與 teacher／student 邊界） | REWRITE | 末三句描述 four-profile teacher／C3View 邊界，須改為「集合條件化交互作用頭與其資訊介面」。 |
| 2.1 第 5 段（容量與約束式 RL：[7][13][14][15][16]） | KEEP | safe-mask／constrained-state 背景不變。 |
| 2.2 Motivation 第 1 段（三個未被同時處理的問題） | REWRITE | 第三點「若直接加入協調器或 joint decoder，又會改變既有 deployment contract」已被繼任者的設計選擇反轉。 |
| 2.2 第 2 段（方法層回應） | REWRITE | 三點回應分別對應 Δ1、Δ4、Δ5，全數需重寫。 |
| 2.2 第 3 段（偏軸角→增益→前一步遞推→PA 耗能） | REWRITE | 這是 Δ1 的動機段；改為「偏軸角經 $H\,G^T$ 決定所需功率，佔用人數經 ACM 階梯決定所需 SINR，兩者共同決定電源端能量」。 |

### 第三章（→ `SEC-SYSTEM-MODEL-REWRITE.md`）

| 節／式 | 處置 | 一行理由 |
|---|---|---|
| 3. 章首段 | REWRITE | 「最後將這些量整理成能量效率、換手成本與負載平衡三個目標」已不成立：繼任者是單一主要目標＋QoS 共同主要結果。 |
| 3.1.1 Network Model（式 3.1–3.4、圖 3-1） | KEEP | 使用者／衛星／波束索引域、$x_{u,s,v}$、$z_{s,v}$、$U_{s,v}$ 與「只啟用有人的波束」全部沿用；僅需補一句 10° 最低仰角可見性門檻。 |
| 3.1.2 Geometry and Channel Model（式 3.5–3.10c） | KEEP | 斜距、偏軸角、$J_1/J_3$ 型樣、$G_0$ 重導、四項損耗、$G^R$ 包絡與 $\theta^R_{-}$ 延伸全部原樣保留——這一層正是 Δ1 之後唯一仍把角度送進功率的入口。**唯一補充**：$H_{u,s,v}G^T$ 的乘積在繼任者中成為功率控制的分母，須在此處明講。 |
| 3.1.3 章首段「$p_{u,s,v}$ 不再由目標 SINR、最低速率或 lagged interference 反推」 | REWRITE | 繼任者**正是**由目標速率所對應的 ACM 門檻反推功率；原句已反向。 |
| 式 (3.11)、(3.12) 與其上下說明（遞推與 telescoped identity） | DELETE | Δ1：無記憶功率控制沒有跨步遞推，也沒有 segment closed form。 |
| $\tau_{u,s,v}$ 與 segment continuity 語意（含符號表 §3、§10.3 相關列） | DELETE | 同上；$\tau$ 自 active surface 退場。 |
| $p^0=0.825$ W 與「3 dB 增益預算」敘事（第 5.1 節 $p^0$ 列與其長註） | DELETE | 段起始功率不存在，3 dB 預算的幾何論證隨之失效。 |
| 波束聚合 $p_{s,v}=\max_u p_{u,s,v}$ | REWRITE | 等空中時間 TDM 下同一時隙只有一位使用者在該波束上發射，波束瞬時 RF 功率就是該使用者的功率；能量改以時隙加權積分，`max` 聚合退場。 |
| 三色重用、$c_{s,v}=(q_{s,v}-r_{s,v})\bmod 3$、$B^w=B^g/3$ | KEEP | 重用計畫不變；僅補「顏色屬於波束—射頻鏈，使用者繼承其服務鏈的顏色」。 |
| 式 (3.12a)、(3.12b)、$I=I^i+I^x$ | REWRITE | 形式保留，但干擾在繼任者中是**功率向量的函數**（耦合不動點），且跨增益以 (NORAD, 波束鏈) 為鍵；同時要說明選擇時視圖的干擾維持名目值。 |
| $\sigma^2=k_BTB^w$、$T=T_a+T_0(10^{N_f/10}-1)$ | KEEP | 雜訊模型不變。 |
| 式 (3.13) 唯一鏈路 SINR $\gamma_{u,s,v}$ | KEEP（語意擴充） | 仍是唯一的實際 SINR；但須加上「聯合解算後」與服務判準 $\gamma\ge\gamma^{-}$，並區分名目視圖與實現視圖。 |
| 式 (3.14) Shannon throughput | REWRITE | Δ2：改為 ACM 階梯 $R=B^{w}\nu_m/U_{s,v}$，並定義速率目標 $R^{\star}$ 與所需 SINR 階梯 $\Gamma_r(\cdot)$。 |
| 式 (3.15)、(3.15a) PA 效率與平方根曲線 | KEEP（改名） | 公式不動；$\xi^{+}=0.35$ 必須改稱**飽和效率**，並明寫上限處實現效率 ≈19.7%、0.32 W 處 ≈8.6%，正文不得出現「35% 效率」。 |
| 類 B 平方根推導段與 GaN Doherty／DVB-DSNG 旁證段 | KEEP | 工程近似的來源說明不變；補一句「這是建模慣例，不是衛星硬體校準」。 |
| 「壓低發射功率不會等比例降低耗電」段 | KEEP | 在速率目標控制下這個結論更強，保留並接到新的目標段。 |
| 式 (3.16a) $P^f=\sum_s(N^a_sP^c+\mathbb 1\{N^a_s>0\}P^b)$ | KEEP（補限制） | 保留；但「一支波束對應一條射頻鏈」與「共用項是宣告的處理增量、不是整星基頻或平台負載」必須升格為表列假設。 |
| 式 (3.16) $P^N$ | REWRITE | 需納入待機（primary $P_{\text{idle}}=0$；敏感度 $f=1/12$、每星 12 條射頻鏈的宣告普查）與時隙積分。 |
| 式 (3.17) $\eta_{u,s,v}$ 單鏈路 EE 顯示量 | DELETE | 繼任者的唯一 EE 是匯總比值；逐鏈路顯示量在新的目標鏈中沒有角色，保留只會誘發 per-row EE 平均的誤讀。 |
| 3.1.3 末段「MODQN 以三個 Q 網路學三個目標／第一個獎勵改為 EE 貢獻和」 | DELETE | 三個 legacy reward 的接續敘事在繼任者中已無對應。 |
| **NEW**：能量邊界宣告段 | NEW | v1.8 §3 的能量邊界句必須**逐字**出現在正文與每一份 receipt 標頭；同段並須說明「被省略的共同能量不會在政策之間相消」。 |
| **NEW**：耦合上限功率解與收斂證書 | NEW | 標準干擾函數、由 $p=0$ 起迭代、唯一上限不動點、`CONVERGED`／`CONVERGED_SLOW`／`INVALID`。 |
| **NEW**：時基與積分 | NEW | 每步 30.08 s、48 個邊界、事件不連續由左右樣本供給；步內使用者位置固定為決策瞬時位置。 |
| **NEW**：模型限制就地陳述 | NEW | 回溯式 TLE、理想原子式套用、部分酬載邊界、全緩衝流量四項，**寫在模型被定義的地方**，不塞進註腳。 |
| 3.2 章首段與式 (3.24) 的 P1／P2／P3 | REWRITE | 三目標長期最佳化改為單一主要目標（pooled EE）＋QoS 共同主要結果；$\min\sum U_{s,v}^2$ 不再是獨立目標。 |
| 3.2.1 Angle-Aware EE（式 3.25） | REWRITE | $r_{1,u}$ 的逐使用者 EE 貢獻和退場，改為組態層剩餘 $\Omega(a)$ 與匯總比值 $\eta^{N}$。 |
| 3.2.2 Handover Cost（式 3.27、$\Psi_u$） | REWRITE | 換手成本改以 $\Phi$ 計價（$\varphi_1=0.5\kappa$ 同星換束、$\varphi_2=1.0\kappa$ 跨星），**在 $\Omega$ 內只計一次**；符號 $\Psi_u$ 讓位給交互作用殘差 $\Psi_{\mathcal K}$，改名為 $\Phi_u$。並補出時再進入的計價規則與「同一 dwell 邊界的 cell re-key 不算換手」。 |
| 3.2.3 Load Balancing（式 3.28、$r_{3,u}$） | DELETE | 負載平衡不再是獨立獎勵：佔用人數已經由 $\Gamma_r(U_{s,v})$ 直接進入所需功率與能量，再放一個 $-U_{b_u}$ 會讓第一目標重複承擔第三目標的工作（原稿式 3.16 下方已警告過同型錯誤）。 |
| 3.2.4 Reward Vector（式 3.29 $\overrightarrow R_u$） | DELETE | 三維獎勵向量沒有繼任對應；保留只會被讀成投票。 |
| 3.2.4 末兩段（訓練用逐步獎勵／MODQN baseline 集中效應） | REWRITE | 併入新的目標段：集中效應在速率目標控制下改由 $\Gamma_r$ 表達，不需要 baseline 敘事。 |

### 第四章（→ `SEC-METHOD-REWRITE.md`）

| 節 | 處置 | 一行理由 |
|---|---|---|
| 4.1 Method Overview 第 1 段 | REWRITE | 「三個獨立 Q surface、不是投票也不是三個代理」保留精神，但必須改寫成「兩層：逐使用者提案＋集合層評估」。 |
| 4.1 候選表段（$L_w$、$J_w$、$C=L_wJ_w$、$\mathcal C$、$b_u(c,t)$） | KEEP | 固定長度候選表與候選→(s,v) 映射完全沿用。 |
| 式 (4.1) 原生 predecision state $s_u(t)$ | REWRITE | 繼任者的 $Q_1$／$Q_2$ 有各自凍結的 schema（$Q_1$ 九類當步欄位＋歷史欄位；$Q_2$ 22 欄位），且明文**不含遞推功率、進場增益比與段齡**。 |
| 式 (4.2)、(4.3) 遮罩與 $\mathcal A_u^{+}(t)$、one-hot | KEEP | 原生安全遮罩介面不變。 |
| 式 (4.4) roster vector 與「不是 joint decoder」的但書 | REWRITE | roster 現在**確實**是被集合層評分的對象；但書必須改成「集合層在有界目錄上評分，仍是單次承諾」。 |
| 4.2 Three Independent Q Surfaces and Main Objective（式 4.5 單次 masked argmax） | REWRITE | Δ5：$Q_1+Q_2+Q_3$ 直接相加的部署面退場，改為 $a^{0}$ 提案＋集合層選擇。 |
| 4.3 Shared Current-Slot Counterfactual（式 4.6 $G(x)$）與 C1／C2／C3 三個子標題 | REWRITE | $G(x)$ 改名並改定義為 $\Omega(a)=B(a)-\lambda E(a)-\Phi(a)$（含 $\Phi$、只計一次）；三條路線的角色全部更新。 |
| 4.4 Exact Two-User LC-SRS Teacher（式 4.7–4.11） | REWRITE | Δ4：四 profile、$\ell_i$、$e_i$、$d_i=\ell_i+e_i$、$\Psi_B$／$\Psi_E$、$z_{3,i}=e_i+\Psi/2$ 與 two-user scoped identity 全部替換為單邊增量 $d_i$、集合殘差 $\Psi_{\mathcal K}$ 與恆等式 $\sum d_i+\Psi_{\mathcal K}=\Omega(a_{\mathcal K})-\Omega(a^{0})$。 |
| 「teacher 拒絕成員數不是 2 的 topology」段 | DELETE | 繼任者對**任意大小**的選定聯盟都計算 $\Psi_{\mathcal K}$（成本 $K+2$ 次評估）；只有逐使用者 Shapley 分攤停在 $K\le4$ 且只作報告。 |
| 4.5 Deterministic Relational C3View and Student（式 4.12、4.13） | REWRITE | 共享 token scorer 與 reference-centred scalar $Q_{3,i}$ 改為**集合條件化純量交互作用頭**：對 $\mathcal K$ 置換不變、$\Psi^{f}(\varnothing)=\Psi^{f}(\{u\})=0$，且輸入必須含受影響波束之間的**成對跨增益區塊**（純量干擾摘要不足以分辨會翻轉耦合不動點的差異）。 |
| 4.6 Route-Specific Learning and Deployment Procedure（七步） | REWRITE | 步序改為：捕獲→$Q_1+Q_2$ 提案 $a^{0}$ 並驗證為聯合合法（含決定性修復）→建目錄→兩階段評分→選擇→驗證→承諾；並補 10 s 預算、逾時執行已驗證 $a^{0}$、逾時結果計入端點。 |
| 4.7 Method Status and Claim Ceiling | REWRITE | 升級為完整宣稱結構：宣稱階梯 Level A／B／C、收容三分法、$\delta=+0.5\%$ 相對餘裕與交集–聯集合取、regime-conditional 措辭、以及「未達餘裕＝未建立效益，不是效果非正」。 |
| **NEW** 4.x 餘裕調整選擇觀點 | NEW | $q^{\alpha}$ 只作用於想要鏈路的預測接收端；功率與干擾維持名目；目標／發射 MODCOD 對；各臂各自的排序鍵。 |
| **NEW** 4.x 有界目錄與兩階段評分 | NEW | 目錄 $\mathcal X$ 的四個構成、top-8／top-K=10／$M=64$、粗選擇格點與 48 邊界端點的分工。 |
| **NEW** 4.x 比較臂與機制統計 | NEW | $a^{0}$／$a^{1}$／$a^{d}$／$a^{\psi}$、$D(a)$、淨避碰值 $\Upsilon$、反轉頻率、於 $a^{1}$ 再錨定的分解。 |

### 第五、六章與參考文獻

| 節 | 處置 | 一行理由 |
|---|---|---|
| 5.1 表 5-1（環境與索引域） | KEEP（一列改） | 星曆、$h_s$、$L_w=4$、$U=100$、$V=39$、$J_w=7$、$C=28$、$\Delta t=30.08$ s 全部沿用；「每回合 10 步」改為每個世界 30 個決策錨點（世界建構 33 步）。 |
| 5.1 表 5-2（通道與能耗）$f_c$、$B^g$、$L_g$、$L_c$、$L_s$、$c_{s,v}$、$B^w$、$\theta_3$、$R_b$、$G_0$、$G^R_{\pm}$、$A_R$、$B_R$、$\epsilon_\mu$、$K_R$、$T$、$P^c$、$P^b$、$p^{+}$、$\xi^{+}$、$b_o$ | KEEP | 通道與功率放大器校準值不隨物理繼任改變。 |
| 5.1 表 5-2 的 $p^0$ 列與其 3 dB 預算長註 | DELETE | 見 Δ1。 |
| 5.1 「Legacy 執行設定」小表（$R^m$、$P_0$、$\chi_{\text{atm}}$、$P_{\text{sat},\max}$、$\eta_0$） | KEEP（改標籤） | 仍是 provenance；但整章的 legacy provenance 範圍要重新界定為「舊物理 runtime」。 |
| 5.1 表 5-3（三目標純量化權重 $\Omega=(\omega_1,\omega_2,\omega_3)$、$\eta_w$、$(c_1,c_2,c_3)$、$\beta_M/\beta_F$、$\rho_I$、$q_1,q_2,W$） | DELETE | 加權純量化、鯰魚競爭獎勵、目標尺度常數與週期性介入在繼任者中沒有對應；$\Omega$ 字母因此釋出，改作組態層剩餘（見 `SYMBOL-ADDITIONS.md`）。 |
| 5.1 表 5-3（學習率掃描、批次、$\epsilon$、目標網路、$B$） | REWRITE | 學習器組態改為 stages 6–8 contract：16 個學習種子（由 `V025_LEARNER/seed/{1..16}` 域規則導出）、6 臂 × 16 種子 × 每日期 2 個世界 × ≈160 個宣稱日期、每 100 個 source epoch 存檢查點。 |
| 5.1 「約束的作用範圍」整段（0.94%／113 步／1.6452 W／117.2%／214.8%／7.60%／0.0000／段齡 4.56 與 2.54 步…） | DELETE | 這一整段量測的是**已被刪除的機制**（段起始功率＋遞推＋$p^{+}$ 削頂）；在繼任者中 $p^{+}$ 仍是上限，但語意變成「速率目標不可行、以上限發射」，舊數字不可轉述。替代敘述留 `⟨結果待填⟩`。 |
| 5.1 其餘段（四項損耗代換說明、兩個隨機項、legacy provenance 但書） | KEEP | 建模選擇的誠實聲明仍然成立且更需要。 |
| 5.2 起之實驗結果 | REWRITE（本次不交付） | 全部結果數字須在 a-r0 正式矩陣後重寫；本交付一律以 `⟨結果待填⟩` 佔位。 |
| 6.1 Summary | REWRITE | 摘要句與 Δ1／Δ4／Δ5 衝突。 |
| 6.2 Contributions 四條 | REWRITE | 四條分別綁 segment 語意、legacy reward 否定、$z_{3,i}=e_i+\Psi/2$ 與 single-pass 無協調器，全部需改。 |
| 6.3 Limitations and Future Work | REWRITE | 改用 `LIMITATIONS-REGISTER.md` 的七項骨架，並加入 design-freeze 規則所要求的「凍結後未採納之發現一律登錄並隨論文公布」。 |
| References [1]–[27] | KEEP + NEW | 全部保留；新增 EN 302 307-1（ACM 表與門檻）、以及本版新引之來源列於 `TAB-I-model-assumptions.md` 的來源欄。 |

---

## 2. 本次交付未觸及但已列管的事項

1. **摘要與第六章文字**：待 `SEC-SYSTEM-MODEL-REWRITE.md` 與 `SEC-METHOD-REWRITE.md` 定稿後回寫，避免三處各說一套。
2. **圖**：圖 3-1 需補「同色波束—射頻鏈之間的成對跨增益」與「等空中時間時隙」兩個視覺元素；圖 2-1 不動。本交付不產生圖檔。
3. **第五章的敘事**：在 `AR0-DONE` 之前，任何開發期數字（SMOKE、pilot、synthetic map、rehearsal）都標記為 `PILOT_NOT_CLAIM`／`SYNTHETIC_MECHANISM_MAP`／engineering-only，**不得進入論文**。
4. **偏差登錄**：物理繼任本身的偏差文字見 `DEVIATION-REGISTER-DELTA.md`，其中包含 v1.6 起之修訂「在檢視開發期數字之後才提出」的揭露。
