# 論文圖片、公式與符號一致性複核（2026-07-28）

## 結論

- **正文方法拓撲已校正。** 現行中英文第四章均把系統寫成兩個 MODQN 代理：主代理與鯰魚代理各有一組三目標 Q 網路。兩端依
  $Q_j^M\leftrightarrow Q_j^{CF}\leftrightarrow r_j$ 一一對應；每一端各自只有一套環境、軌跡、經驗池與聯合動作，並各自由同一個
  $\Omega$ 純量化三個目標值後選出端內唯一動作。兩端的參數、環境、軌跡與經驗池彼此獨立，不能再寫成「三個完整獨立鯰魚代理」。
- **非對稱訓練機制已說清楚。** 一一對應是網路與目標的結構對應，不代表所有訓練操作對稱：ACRM 只塑形鯰魚代理的
  $r_1$／$Q_1^{CF}$；容量懲罰只作用於主代理，而且是先執行獨立容量梯度步，再執行 TD 更新；介入批次則由一個
  $\mathcal{D}_M$ 與一個 $\mathcal{D}_{CF}$ 組成一個 $\mathcal{B}_I$，再更新主代理三個 Q 網路。
- **公式與三份 DOCX 的機器檢查通過。** 最新 `build_all.sh` 建置通過同源、雙語對齊與 DOCX 結構驗證；三版各有
  63 個顯示公式、16 張嵌入圖、31 個標題與 16 個正式圖說，參考文獻共 24 筆。英文版有 677 個行內數學物件，
  清單標記與文字間距為 360 twips。
- **第五章六張數據圖已同步。** 六張圖的橫軸、縱軸與正文／符號表一致；現行正文把這批圖作為
  episode-9000 正式終點證據。內部舊檔名不構成正文證據層級的文字。
- **十張方法圖都尚未安全同步。** 外部
  `../diagram-kit/mcrl-adapt-batch-a-v3/thesis-figures/` 的圖 2-1、圖 3-1 與圖 4-1～圖 4-8
  仍各有符號或資料流缺口；圖 4-8 最接近通過，但容量梯度步與 TD 更新仍可能被誤讀成同一步。安全同步清單目前為空。
  > ⚑ **2026-08-21 狀態更新**：原 §4.5 Penalty Shaping 整節（含圖 4-8 與式 (4.15)–(4.17)）已自論文正文刪除。圖 4-8 不再屬於需要同步或重畫的目標圖；現行方法圖共九張（圖 2-1、圖 3-1、圖 4-1 至圖 4-7）。本節以下的圖 4-8 相關稽核記錄保留作歷史存查，不代表現行設計。
- **尚未有人工作品驗收。** 本報告只記錄來源、符號、結構與自動驗證結果，不把 PNG 或 DOCX 的機器通過誤稱為
  Word 排版或圖面的人類視覺驗收。

## 公式、符號與 DOCX 證據

### 正文公式

- 中英文第三章各有 44 個顯示公式，第四章各有 19 個，共 63 個唯一公式標籤；中英文公式本體一致。
- 式 (3.9) 已採無因次 FSPL 寫法，真空光速使用 $c_0$；式 (3.11) 的接收增益保留完整鏈路相依性
  $G^R_{u,s,v}(t)$。
- 式 (3.16) 把 $\rho_{s,v}(t)=P^{DL}_{s,v}(t)/P_{\mathrm{sat}}$ 定義為無因次輸出功率比例，並把平方根效率曲線
  定位為本研究採用的類 B 型理想化工程近似。
- 式 (3.17) 的三項均為平均功率；事件能量除以 $T_f$ 後才以瓦特相加。波束換手統一使用
  $E_{\mathrm{ho}}$ 與 $b^{\mathrm{ho}}_{s,v}(t)$，且以 $\max(1,N_s^{\mathrm{act}}(t))$ 保持分母有定義。
- 式 (3.26) 的分子已同時套用連接條件與可服務功率上限，與分母的服務集合一致；功率域穩定常數記為
  $\epsilon_P$，比例總和只在 $\epsilon_P$ 相對需求總和可忽略時近似為 1。式 (3.38) 以
  $\max\{U_{s,v}(t),1\}$ 處理空波束，式 (3.39) 則明定未服務使用者的實作能效為 0。
- 式 (3.23) 與式 (3.24) 已分開說明：$\gamma$ 明定為代表 SINR 的希臘字母，不是獎勵 $r$ 或吞吐量 $R$；
  式 (3.24) 再獨立取出實際吞吐量。式 (4.10) 前已定義 $F_W^{-1}(q)$ 為近期經驗分布的 $q$ 分位數、非倒數；
  式 (4.12) 則改用兩列對齊式，分別呈現樣本數與混合批次的組成。
- 式 (4.15) 的價值域穩定常數已與功率域常數分開，記為 $\epsilon_V$。ACRM 的同步副本統一稱為
  「同步對照環境副本」，並明定每步在相同前置狀態與隨機條件下只改變動作。
- 第四章的兩組 Q 網路、兩個經驗池、兩個聯合動作與共同純量化函數已使用
  $Q_j^M,Q_j^{CF},\mathcal{D}_M,\mathcal{D}_{CF},A_M,A_{CF},\Omega$；正文不再出現三套完整鯰魚資源。
- ACRM 的正式範圍是能效目標 $r_1$；容量懲罰的正式流程是主代理的獨立容量梯度步，不能併入 TD target 或 TD loss。

`notation-table.md` 已同步上述式 (3.16)–(3.17) 與第四章拓撲符號，但現行三版建置沒有把符號表章節嵌入 DOCX；
因此這項結果只能稱為「符號表來源已同步」，不能稱為「DOCX 內符號表已驗收」。

### 最新三版建置

最新收據為 `scratch/conversion-test/mc-thesis-build-receipt.txt`：

| 欄位 | 結果 |
|---|---|
| 建置時間（UTC） | `2026-07-28T05:08:40Z` |
| source set SHA-256 | `be6bea0539cc74e0a8fbb79ebea1c3a9c5c6151186d2dcfd1401d8c443e70d91` |
| source snapshot byte identity | PASS |
| bilingual source alignment | PASS |
| inline math expression multiset alignment | PASS |
| bilingual Markdown rebuild byte identity | PASS |
| DOCX structure parity | PASS |
| drawings | 16 |
| display equations | 63 |
| English inline math objects | 677 |
| headings | 31 |
| formal figure captions | 16 |
| references | 24 |
| list marker/text gap | 360 twips |

成品完整 SHA-256：

- 中文 `mc-thesis-ris.docx`：
  `d8f43e84be5bfd2a974ebd8025085ca8b9e1dc4d8ae23d7e7094c5d52399cd7f`
- 英文 `mc-thesis-ris-EN.docx`：
  `85fd114df6fc335708adf59cebeeba709e7f033850aa8c839a82808cf728a1aa`
- 雙語 `mc-thesis-ris-bilingual.docx`：
  `63f34f3eefb0834ac4b512bceef7895d64ed32fae89ab9ebede05338f8264aff`

## 第五章六張數據圖

六張圖的正式軸符號如下：

| 圖 | 正式橫軸 | 正式縱軸 |
|---|---|---|
| 圖 5-1 | $v_{\max}$ | $\overline{\tilde{\eta}}^{EE}$ |
| 圖 5-2 | $U_{s,v}(t)$ | $\overline{\tilde{\eta}}^{EE}$ |
| 圖 5-3 | $\lvert\mathcal{U}\rvert$ | $\overline{\tilde{\eta}}^{EE}$ |
| 圖 5-4 | $P_{\mathrm{base}}$（W） | $\overline{\tilde{\eta}}^{EE}$ |
| 圖 5-5 | $B_{\mathrm{sys}}$（MHz） | $\overline{\tilde{\eta}}^{EE}$ |
| 圖 5-6 | $N_0$（dBm/Hz） | $\overline{\tilde{\eta}}^{EE}$ |

第五章的數據圖已在三版建置中使用同一批圖。更換未來的正式數據時，必須保持軸符號與圖說位置不變，並以新圖數值為準
逐一重做正文數值核對；本報告不把目前圖值延伸成未來圖的保證。

## Multi-Catfish 拓撲定論

現行方法的正確層級是「兩個 MODQN 代理、六個線上 Q 網路」：

| 對應層 | 主代理 MODQN | 鯰魚代理 MODQN |
|---|---|---|
| 三目標網路 | $Q_1^M,Q_2^M,Q_3^M$ | $Q_1^{CF},Q_2^{CF},Q_3^{CF}$ |
| 目標對應 | $Q_j^M\leftrightarrow r_j$ | $Q_j^{CF}\leftrightarrow r_j$ |
| 純量化與動作 | $\Omega\to A_M$ | $\Omega\to A_{CF}$ |
| 環境／軌跡 | 一套 $E_M$／一條主代理軌跡 | 一套 $E_{CF}$／一條以 $\tau_t^{CF}$ 表示步級轉移束的鯰魚代理軌跡 |
| 經驗池 | 一個 $\mathcal{D}_M$ | 一個 $\mathcal{D}_{CF}$ |

因此，「三個鯰魚」在本文方法中是鯰魚代理三個目標 Q 網路的角色分工，不是三個各自選動作、各自擁有環境與經驗池的完整代理。
兩端結構一一對應，但以下機制有意不對稱：

1. ACRM 只更新／塑形鯰魚代理能效軸 $Q_1^{CF}$。
2. 容量懲罰只對主代理做獨立梯度步。
   > ⚑ **2026-08-21 狀態更新**：容量懲罰（§4.5 Penalty Shaping）已自論文整節移除（2026-08-21）。第 2 點保留作歷史存查；現行塑形策略僅剩兩種（經驗塑形、獎勵塑形），懲罰塑形已刪除，不得列為現行貢獻。
3. 介入時只形成一個 $\mathcal{B}_I$，用來更新主代理的三個 Q 網路；不先把鯰魚代理拆成三個經驗池或三個批次。

## 方法圖逐圖複核

### 外部 PNG 再檢（2026-07-28）

依使用者指定，已逐張檢視
`../diagram-kit/mcrl-adapt-batch-a-v3/thesis-figures/png/`，並與現行嵌入的 `figures/0727/` 圖、第四章正文與圖說比對。
**本輪沒有任何圖片符合安全替換條件，因此未覆蓋論文圖片、未重建 DOCX。** 這個裁決不表示現行方法圖已通過人工驗收；它只表示外部候選圖沒有提供一張可安全取代現行圖的版本。

| 外部候選 | 與現行圖關係 | 裁決與理由 |
|---|---|---|
| 圖 2-1 | 位元相同 | 不替換；同一檔案不產生變更。 |
| 圖 3-1 | 不同 | 不替換；候選未完整表達正文要求的未點亮候選波束零速率條件，且 $\theta_{u,s,v}$ 的時間相依標示未與正文一致。 |
| 圖 4-1 | 不同 | 不替換；仍將 $L_{\mathrm{cap}}$ 併入 TD loss，而正文要求先做獨立容量梯度步、再做 TD 更新。 |
| 圖 4-2、4-3、4-4 | 位元相同 | 不替換；同一檔案不產生變更，且既有拓撲／符號缺口仍不能因複製而視為通過。 |
| 圖 4-5 | 不同 | 不替換；目標網路參數未區分主要與鯰魚代理的 $\theta_j^{M,-}$、$\theta_j^{CF,-}$。 |
| 圖 4-6 | 不同 | 不替換；未完整標示唯一 $\mathcal{B}_I$ 的 $n_M,n_{CF}$ 組成與鯰魚端原始獎勵樣本。 |
| 圖 4-7 | 位元相同 | 不替換；同一檔案不產生變更，且主代理比較值仍未精確標為 $r_{1,u}^{M\mid CF}$。 |
| 圖 4-8 | 不同 | 不替換；仍把容量懲罰直接導向主代理 TD 更新，缺少獨立的 capacity-gradient step。 |

> ⚑ **2026-08-21 狀態更新**：圖 4-8（容量懲罰）已隨 §4.5 整節移除，上表中圖 4-8 的稽核記錄僅作歷史存查。

外部候選圖仍是未納入論文的工作中來源。本表記錄目前已知的最小修正，不替外部來源建立新雜湊基準。

| 圖 | 判定 | 目前殘差與最低修正 |
|---|---|---|
| 圖 2-1 | **FAIL** | $a(t)$ 應改為 $a_u(t)$；reward 必須明示每位使用者的三目標向量；Double DQN 要把線上網路選擇動作與目標網路評估動作分開畫出。 |
| 圖 3-1 | **FAIL** | $\theta_{u,s,v}$ 缺少 $(t)$；圖上的 `φ` 字形必須與正文的 $\varphi$ 一致。 |
| 圖 4-1 | **FAIL** | 現圖的 $y_j\rightarrow L_{\mathrm{cap}}\rightarrow$ TD 把兩個更新步驟混在一起。應畫成 $L_{\mathrm{cap}}\rightarrow$ capacity gradient $\rightarrow\theta_j^{M,(\mathrm{cap})}$，再由 $y_{j,u}^M\rightarrow$ TD $\rightarrow\theta_j^{M,+}$；並把 $D_M$ 改成 $\mathcal{D}_M$、補齊 Q／$\theta$ 的主代理上標。 |
| 圖 4-2 | **FAIL** | 現圖讓主代理環境流入能效分層。正確資料流應是鯰魚代理三網路 $\rightarrow\Omega\rightarrow$ 單一 $A_{CF}\rightarrow$ 單一 $E_{CF}\rightarrow\tau_t^{CF}\rightarrow$ stratification $\rightarrow$ 單一 $\mathcal{D}_{CF}$；主代理只產生 $\mathcal{D}_M$，兩池再形成一個 $\mathcal{B}_I$。 |
| 圖 4-3 | **FAIL** | $L_{\mathrm{cap}}$ 仍被送入 `Loss^main`；ACRM 看起來作用於全部鯰魚網路；圖中也缺少唯一的 $\mathcal{B}_I$。必須拆出主代理容量梯度步，並把 ACRM 限定到 $Q_1^{CF}$。 |
| 圖 4-4 | **FAIL** | candidate／$r_1$／$F^{-1}$ 應精確標為 $\tau_t^{CF}$、$\bar r_1^{CF}(t)$、$F_W^{-1}$，並只連到一個 $\mathcal{D}_{CF}$ 與一個 $\mathcal{D}_M$。其 builder 仍留有「三個獨立代理／$\mathcal{D}_{CF,1}$」舊字樣，必須連同來源一起修正。 |
| 圖 4-5 | **FAIL** | 兩端的 $\theta_j^-$ 必須分別寫成 $\theta_j^{M,-}$ 與 $\theta_j^{CF,-}$。 |
| 圖 4-6 | **符號 FAIL** | 一個 mixed batch 的拓撲已正確，但 $\theta_j$ 應為 $\theta_j^M$；需明標 $\mathcal{D}_M$／$\mathcal{D}_{CF}$ 與 `Sample_raw`，並宜把兩側樣本數寫成 $n_M$／$n_{CF}$。 |
| 圖 4-7 | **符號 FAIL** | ACRM 只作用於能效軸的概念正確；$r_1^M$ 應改為配對狀態下的 $r_{1,u}^{M\mid CF}$，其餘比較量應使用 $r_{1,u}^{CF}$、$r_{1,u}^{S}$、$r_{1,u}^{C}$，並明示只有 $Q_1^{CF}$ 被更新。 |
| 圖 4-8 | **近通過但仍不安全** | $L_{\mathrm{cap}}\rightarrow$ TD 的箭頭仍可能被解讀成把容量懲罰併入 TD loss；須插入獨立 capacity-gradient step 與 $\theta_j^{M,(\mathrm{cap})}$，再進入 TD 更新。 |

### 改圖規格：每張圖應如何修正

以下是可直接交給繪圖者的最小改圖規格；未達成前，圖不應替換正文現有檔案。

| 圖 | 必須保留的訊息 | 必須移除或改畫 | 完成條件 |
|---|---|---|---|
| 2-1 MODQN 基準 | 三個目標 Q 網路、共同權重 $\Omega$、可行動作集合與回放更新 | $a(t)$ 改為每位使用者的 $a_u(t)$；$[r_1,r_2,r_3]$ 改為 $[r_{1,u},r_{2,u},r_{3,u}]$；不可把線上選擇與目標評估混成一個箭頭 | 畫出線上網路依 $\Omega$ 選 $a_u^*$、對應目標網路評估該動作，再形成 $y_{j,u}$ 的 Double-DQN 分工。 |
| 3-1 系統模型 | 同星波束換手、跨衛星換手、干擾、偏軸角、容量限制與未點亮波束零速率 | $\theta_{u,s,v}$ 改為 $\theta_{u,s,v}(t)$；圖中 $\phi$ 改為正文同字形 $\varphi$；零速率不可只寫成孤立的 $R_u=0$ | 用 $z_{s,v}(t)=0\Rightarrow R_u(t)=0$ 標示未點亮候選波束，並把共享使用者寫為 $U_{s,v}(t)$。 |
| 4-1 更新介入位置 | 資料蒐集與參數更新的兩個區域，以及六項訓練期機制的位置 | 移除 $y_j\rightarrow L_{\mathrm{cap}}\rightarrow$ TD loss 的串聯；$L_{\mathrm{cap}}$ 不得是 TD loss 的輸入 | 從當步主代理族群輸入的 $Q_j^M$ 另開支路計算 $V\to\pi\to\Pi\to\Delta\to L_{\mathrm{cap}}$，經 capacity-gradient 得 $\theta_j^{M,(\mathrm{cap})}$，再由 TD 支路得到 $\theta_j^{M,+}$。 |
| 4-2 目標網路視角 | 兩個 MODQN 代理各有三個目標網路、$Q_j^M\leftrightarrow Q_j^{CF}\leftrightarrow r_j$、端內共同純量化 | 不可把 Catfish 1–3 畫成三個獨立環境／軌跡／經驗池；主代理環境不可流進分層器 | 鯰魚三網路 $\to\Omega\to A_{CF}\to E_{CF}\to\tau_t^{CF}$，只進一個 $\mathcal D_{CF}$；主代理只形成 $\mathcal D_M$；兩池只在唯一 $\mathcal B_I$ 相會。 |
| 4-3 代理與資料流 | 主代理 $E_M,\mathcal D_M$ 與鯰魚代理 $E_{CF},\mathcal D_{CF}$ 的獨立軌跡；同步比較副本 $\bar E_{CF}$；只部署主代理 | 移除 $L_{\mathrm{cap}}\to\mathrm{Loss}^{main}$；競爭獎勵不可接到三個鯰魚目標；不可直接把鯰魚池倒進主代理池 | 容量支路按圖 4-1 的兩步更新；ACRM 僅接到 $Q_1^{CF}$；跨送與週期介入以原始獎勵的唯一 $\mathcal B_I$ 表示。 |
| 4-4 能效分層 | 一個完整步級轉移束、近期視窗的分位數門檻、三路分流 | `Candidate transition ×N`、籠統的 `EE_hi/EE_lo` 與多個鯰魚池 | 輸入標為 $\tau_t^{CF}$；分數標為 $\bar r_1^{CF}(t)$；門檻標為 $F_W^{-1}(q_{hi})$、$F_W^{-1}(q_{lo})$；高／中／低段分別進單一 $\mathcal D_{CF}$／額外送 $\mathcal D_M$／捨棄。 |
| 4-5 非對稱折扣 | 主代理三網路共用 $\beta_M$、鯰魚代理三網路共用 $\beta_{CF}$，且 $\beta_M<\beta_{CF}$ | 未帶代理上標的 $\theta_j^-$ 與只寫 Big/Small 的非正式標籤 | 寫成 $\theta_j^{M,-}$、$\theta_j^{CF,-}$；在圖上直接列 $0<\beta_M<\beta_{CF}<1$ 與同一未來步距 $n$ 的 $\beta_M^n,\beta_{CF}^n$。 |
| 4-6 週期性介入 | 一個計數器、隨機間隔、兩池組成唯一混合批次、主代理三網路各自更新 | 模糊的 main/catfish buffer、未標示來源樣本數與獎勵型態 | 寫明 $T\sim\operatorname{Unif}\{T_{lo},\ldots,T_{hi}\}$、$n_{CF}=\operatorname{round}(\rho_I B)$、$n_M=B-n_{CF}$，以及 $\mathcal B_I=\operatorname{Concat}(\operatorname{Sample}(\mathcal D_M,n_M),\operatorname{Sample}_{raw}(\mathcal D_{CF},n_{CF}))$；只更新 $Q_j^M$。 |
| 4-7 同狀態配對競爭 | 同一鯰魚前置狀態與隨機條件、只改變動作、能效軸的獎勵差 | $r_1^M$、沒有條件的 `same state`，以及暗示三個鯰魚網路都被整形的箭頭 | 用 $r_{1,u}^{CF}$、$r_{1,u}^{M\mid CF}$、$r_{1,u}^{S}$、$r_{1,u}^{C}$；標示 $A_{CF}$ 與無探索 $A_{M\mid CF}$ 分別在 $E_{CF}$、$\bar E_{CF}$ 執行；只有 $Q_1^{CF}$ 接受 $r_{1,u}^{C}$。 |
| 4-8 容量懲罰 | 可微分偏好鏈與每衛星前 $v_{\max}$ 名之外的尾端質量 | $L_{\mathrm{cap}}$ 直接指向 `Main-agent TD update` | 畫完整 $Q^M\to V_u\to\pi_u\to\Pi_{s,v}\to\Delta_s\to L_{\mathrm{cap}}\to\nabla_{\theta^M}\to\theta^{M,(\mathrm{cap})}$，再接 TD 更新；標明訓練期限定且鯰魚代理不參與。 |

> ⚑ **2026-08-21 狀態更新**：圖 4-8 及對應的容量懲罰機制已隨正文 §4.5 整節移除，此改圖規格行僅作歷史存查，不代表現行任務清單。

### 第五章數據圖

目前圖 5-1 至圖 5-6 的橫軸、縱軸、單位、圖說與正文數值已對齊，這輪未發現需因圖面語義而重畫的項目。它們仍只代表現行圖資料與式 (3.39) 的實作能量效率；未來更換正式數據時，必須逐一重核圖中數值、正文數值、軸符號和圖說，不能只替換 PNG。

## 同步裁決

1. 第五章六張數據圖與現行三份 DOCX 已同步；最新建置證據以上述收據為準。
2. 圖 2-1、圖 3-1 與圖 4-1～圖 4-8 的安全同步清單仍為空；正文繼續使用目前已建置的嵌入圖。
3. 外部 diagram-kit 是被忽略且仍在變動的 dirty WIP。本輪只讀取既有稽核結果，不改其 SVG、PNG、JSON、builder 或其他檔案。
4. `figures/check_figure_sync.py --update` 暫不執行，避免把未通過的方法圖／圖說組合寫成新基準。
5. 外部圖修正完成後，仍須依序重做 SVG 文字比對、PNG 人工眼檢、正文圖說核對、三版 DOCX 重建與 Word 人工視覺驗收。

## 2026-08-03 P3 formula-rewrite re-review

本輪依現行 `thesis-mc/ch4-method.md:142-194,239-279,298-339` 及其英文對應稿，重新對照圖 2-1、3-1、4-1--4-8 的圖面元素、正文方程與資料流。這是規格複核，不是繪圖或視覺驗收；沒有改動任何 PNG、SVG、builder、manifest 或 DOCX。

| 圖 | 現行正文／方程必須表達 | 圖面元素差異 | 元素與方程的衝突 | 判定 |
|---|---|---|---|---|
| 2-1 | 基準方法以每位使用者的 $\a_u(t)$、三目標獎勵向量與線上選動作／目標網路評估的分工表達。 | 現圖仍以無使用者索引的 `$a(t)$` 與單一 reward 元素呈現，選擇與評估未拆開。 | 圖把向量式、每使用者動作及 Double-DQN 的兩個網路角色壓成單一箭頭，不能由圖讀出正文契約。 | **FAIL** |
| 3-1 | 系統模型需保留時間相依的 $\theta_{u,s,v}(t)$、$\varphi$、實際點亮 $\z_{s,v}(t)$、全域波束需求 $\U_{s,v}(t)$，以及未點亮候選的零服務條件。 | 現圖的角度缺少 `(t)`，字形仍有 `φ`／$\varphi$ 混用，且未把暗波束與零速率條件接到鏈路結果。 | 圖面看似所有候選都能產生鏈路速率，與正文的 $\z$ gating／容量後實際連接關係不一致。 | **FAIL** |
| 4-1 | MCRL 的作用位置須把容量懲罰的獨立 gradient step 與一般 TD update 分開；三策略為式 (4.10)--(4.12)。 | 現圖把 $\L_{\mathrm{cap}}$ 直接接入 TD loss／更新主幹，並保留舊的更新順序暗示。 | 式 (4.17) 只定義 penalty，正文 line 8 先調整 $\Q^M$、line 9 再 TD；現圖的合併箭頭會導出錯誤的同一步語義。 | **FAIL** |
| 4-2 | 兩個 MODQN 代理各有三個 objective-wise Q network；每端以 $\Omega$ 形成一個聯合動作，鯰魚端才進單一 $\mathcal D_{CF}$。 | 現圖仍可讀成三個獨立 catfish 環境／軌跡／池，且主端資料流入能效分層器。 | 式 (4.10) 的輸入是單一 $\tau_t^{CF}$ 與 $\bar r_1^{CF}(t)$，不是三個 agent 的三條分流；圖的拓撲與方程對不上。 | **FAIL** |
| 4-3 | ACRM 僅改變 $\Q_1^{CF}$ 的 shaped reward；容量懲罰只更新主代理；原始 reward 才可跨送與進 $\mathcal B_I$。 | 現圖將 $\L_{\mathrm{cap}}$ 連到主代理 TD loss，且 ACRM 的箭頭未限於第一個鯰魚目標；唯一 $\mathcal B_I$ 未清楚畫出。 | 式 (4.14)、(4.17) 與 line 5/8/11 的非對稱範圍被圖面展平成對稱更新。 | **FAIL** |
| 4-4 | 式 (4.10) 使用 $\tau_t^{CF}$、未整形 $\bar r_1^{CF}(t)$ 與單一 $\F_W^{-1}$；高／中／低層分別進 $\mathcal D_{CF}$、跨送 $\mathcal D_M$、捨棄。 | 現圖仍使用籠統的 candidate／EE threshold 與多池語意，沒有完整轉移束及 raw reward 標記。 | 圖的分流元素無法實作式 (4.10) 的三路邏輯，尤其會把單一步級評分誤讀成逐頭或逐樣本優先回放。 | **FAIL** |
| 4-5 | 式 (4.11) 是兩端的 $\beta_M<\beta_{CF}$；參數副本應區分 $\theta_j^{M,-}$ 與 $\theta_j^{CF,-}$。 | 現圖只寫未帶代理上標的 $\theta_j^-$／Big-Small 類標籤。 | 方程的非對稱是在兩個 MODQN 端之間，不是在三個 objective head 之間；現圖會導出錯誤的 head-wise discount。 | **FAIL** |
| 4-6 | 式 (4.12) 只建立一個 $\mathcal B_I$：$n_M=B-n_{CF}$、$n_{CF}=\operatorname{round}(\rho_I B)$，鯰魚樣本帶 raw 三維 reward，並只更新 $\Q_j^M$。 | 現圖未完整標示 $\mathcal D_M$／$\mathcal D_{CF}$、`Sample_raw`、$n_M$／$n_{CF}$ 與唯一混合批次。 | 元素不夠使同一方程可被讀成多個池、多個介入批次或 shaped reward 跨送，與式 (4.12) 的邊界衝突。 | **FAIL** |
| 4-7 | 式 (4.14) 只在相同前置狀態與隨機條件下比較 $r_{1,u}^{CF}$、$r_{1,u}^{M\mid CF}$，並由差值形成 $r_{1,u}^{S}$；只有 $\Q_1^{CF}$ 使用 $r_{1,u}^{C}$。 | 現圖仍有未限定條件的 `$r_1^M$`／generic reward，沒有清楚畫出同步對照副本與單一 shaped head。 | 圖會把同狀態 counterfactual 誤讀成兩個不同環境狀態，且把 ACRM 擴大到 $\Q_2^{CF},Q_3^{CF}$。 | **FAIL** |
| 4-8 | 式 (4.15)--(4.17) 先由 $V_u\to\pi_u\to\Pi_{s,v}\to\Delta_s\to\L_{\mathrm{cap}}$ 建立可微 surrogate，再在 TD 前獨立調整主代理。 | 現圖雖已畫出偏好質量與 tail mass，但 capacity-gradient step／$\theta^{M,(cap)}$ 仍缺少或被 TD 箭頭吞併。 | 方程明確把 $\L_{\mathrm{cap}}$ 定為獨立更新方向，圖面仍可能被讀成 penalty 直接加進 TD target。 | **NEAR-PASS／仍 FAIL** |

> ⚑ **2026-08-21 狀態更新**：原式 (4.15)–(4.17) 與圖 4-8 所對應的容量懲罰整節已自正文移除（2026-08-21）。本 re-review 紀錄中圖 4-8 的條目保留作歷史存查；現行方法圖共九張，無圖 4-8。

### Re-review decision

十張方法圖的安全同步清單仍為空（0/10）。最低改圖規格沿用上方逐圖表；在 SVG／PNG 修正、逐張人工眼檢、圖說與正文核對及 owner visual acceptance 完成前，不執行 `figures/check_figure_sync.py --update`，也不以本輪 bilingual／DOCX build 的機器通過取代圖面驗收。

> ⚑ **2026-08-21 狀態更新**：圖 4-8 已移除，不再列入改圖任務。現行待同步方法圖為圖 2-1、圖 3-1、圖 4-1 至圖 4-7（共九張）。
