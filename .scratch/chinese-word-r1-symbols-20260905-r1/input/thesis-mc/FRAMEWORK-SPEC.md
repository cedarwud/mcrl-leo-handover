# FRAMEWORK-SPEC — 實際跑的 Multi-Catfish 框架(文字 + 圖 track 共用的單一底稿)

> **SUPERSEDED / HISTORICAL（2026-08-07）：**本檔記錄的是舊 route-B 協調式分配與舊功率／校準敘事，
> 不是目前論文或新協定的 live spec。現役方法 authority 是 `ch4-method.md`（部署為 per-user
> `argmax`，沒有 auction/decoder）；正式 EE authority 是 `../docs/ADR-003-canonical-ee-closure.md` 與
> canonical `runtime/angle_aware_ee.py`。下文任何「分到的功率」、load-only actual `P_DL`、已凍結
> `c_j`、方法勝出或解崩宣稱均只作歷史 provenance，不得供應新 replay、checkpoint、圖表或結論。

> **用途。** 這是 ch4(文字)和架構圖/流程圖(圖)兩條 track **共用的同一份框架描述**,讓兩邊不分岔。
> 內容 = **從實作程式碼核實**的「實際跑了什麼」(`src/modqn_paper_reproduction/route_b_factorial/`),不是設計意圖。
> 口氣 = 不熟通訊/RL 的學生白話;**不用** jargon(蒸餾 / 解碼器 / 攤銷 / 映射 / 前向推論)。code/符號/路徑用英文。
>
> **權威來源(已核實):** 程式碼 `route_b_factorial/{auction_decode,congestion_context,shaped_q,replay,trainer,config}.py`
> + 設計 `route-b-factorial-design-note-v3-2026-06-26.md`(G6-SOUND)+ 建置 `route-b-factorial-BUILD-SDD-2026-06-27.md`
> + 結果/裁決 `route-b-factorial-{RESULT.json,VERDICT-G6,INDEPENDENT-ADJUDICATION}-2026-06-27.md`。
> 敘事權威 = `thesis/THESIS-FRAMING-DECISION-2026-06-28.md`(框架贏 + 3 條 RED LINES)。
>
> ⚠ **不要用 `archive/thesis-route-c/thesis-narrative-restored-2026-07-17/`**(2026-06-15
> 「criticality-aware」舊脈,內容自己說「忽略 coordinator/auction」,
> 跟現在的協調式波束分配框架相反)。一律以本檔 + 上面程式碼為準。

---

## 0. 一句話框架

**Multi-Catfish 框架 =【依目標分工的鯰魚式訓練,替每個使用者的每個候選波束算出多目標估值】＋【在每顆衛星
「最多開 k_cap 個波束」的硬限制下,協調分配波束的協調式波束分配】。**

原本 MODQN 是每個使用者**各自**挑分數最高的波束(獨立 argmax)→ 狀態相近的人撞在同一波束 → 那個波束載入爆掉、
排在後面的人被擠到零吞吐 → 全體比亂選還差(崩潰)。框架把「各自挑」換成「協調著開、再分配」→ 不再全擠一個 → 解崩。

- **catfish(鯰魚)= 框架的具名核心組件**:三隻 per-objective 鯰魚產生每使用者每候選波束的多目標綜合價值。
- **協調式波束分配 = 框架內的選波束步驟**:把鯰魚的綜合價值,在每顆衛星 k_cap 限制下整合成聯合決策(部署時降低過度集中的那一步)。
- 兩步**整合**成一個以鯰魚為核心、會贏過 baseline MODQN 的框架 = 本文貢獻。
- **★ 敘事(binding,USER 2026-06-28):** 協調式波束分配是**框架內的一步**、用鯰魚的估值,**不要寫成獨立於 catfish 的功勞 / 獨立模組**(thesis 把估值+分配當框架內兩步)。但消融(§4/§6)如實呈現每部分的數值(grounded:解崩機制是分配步驟、A2≈A1 → **不寫**鯰魚驅動解崩的假因果)。舊譯(auction / bid 的中文)已棄,thesis 一律用「協調式波束分配 / 綜合價值」。

---

## 1. 系統背景(對齊凍結 env,兩個 track 共用的事實)

對齊凍結環境 `env/family_b_step.py`(唯讀,EUV `389eaaef`):

- 窗內 **4 顆衛星**(`l_w=4`),每顆 **7 個波束槽** → 動作空間 **28**(一個動作 = 選某顆衛星的某個波束槽)。
- **約 100 個地面使用者**(`num_users=100`)。
- **容量硬限制(關鍵):** 每顆衛星每個時刻**只開最被需要的前 `k_cap` 個實體 cell**;不在開啟 cell 上的使用者
  被 `cap_bump` → **吞吐量歸零**。主實驗 `k_cap=3`(每窗最多 4×3=12 個 active 波束服務 ~100 人)。
- **三個目標獎勵**(per-user,ch3 已定義):
  - `r1` = **角度感知能量效率(EE)** —— 每使用者吞吐量 ÷ 分到的功率(功率經偏軸角→增益→所需功率)。**綁死 EE,不是吞吐量。**
  - `r2` = 換手懲罰(換服務波束就扣)。
  - `r3` = 負載平衡(波束間吞吐量落差)。
  - 加權指標 `J_w = Σ_j ω_j·(r̄_j/c_j)`,`ω=(0.5, 0.3, 0.2)`,`c_j`＝固定校準常數(舊寫 `scale_j`;校準值凍結)。

> 圖 track 注意:FIG-2(系統模型)畫到「k_cap 容量閘」這個概念即可;它是後面崩潰與解崩的物理根源。

---

## 2. 為什麼原 MODQN 會崩(框架要解的問題)`grounded`

1. MODQN 有三個目標 Q 網路 `Q1(EE) Q2(換手) Q3(負載)`,純量化成
   `v_u(a) = Σ_k w_k Q_k(s_u, a)`,然後**每個使用者各自**挑 `a_u = argmax_a v_u(a)`。
2. 「各自挑」是**同時、互相看不到**的:每個人挑的時候不知道別人這一步要挑哪。狀態相近的人算出來的排序也相近 →
   一起挑同一個頂波束 → 那個 cell 載入爆掉(`rate = B/load·log2(1+SINR)`,load 一大、每人速率掉)→ 第 `k_cap+1`
   個之後的人被擠掉 → 歸零。
3. 這是「各自挑」這個**分配規則本身**的問題:獨立 argmax 在數學上沒辦法遵守「每顆衛星只能開 k_cap 個 cell」的
   硬限制(它沒有任何協調 cell 數量的機制)→ 撞車 + 餓死是**演算法性的**,不只是環境刁難。

> 這條 `grounded`(cross-over 實驗證明:見 §6)。但「崩潰的**最終根因**是 ENV / STATE / ALGORITHM」這個更大的問題,
> 全 repo 仍記為 **UNRESOLVED**;框架**繞過**它 —— 同 env / 同 seed / 同 episode / 同權重,只換「分配規則 × 訓練」,
> 比相對輸贏,不管最終根因是哪個都公平。**ch4/ch5 不要寫成「我們解決了崩潰的根因」。**

---

## 3. 框架的兩個步驟:估值 + 分配(實作核實)

> 全程**不改 `modqn.py`**(G1 `aa877676` 唯讀)。新的 Q 網路用**組合**的方式:同一個 `DQNNetwork` 類別,只是
> 輸入層加寬(原 140 維 + 壅塞 84 維 = **224 維**),三個目標各一個網路。

### 3A. 估值步驟 —— 鯰魚式訓練產生多目標綜合價值(`shaped_q.py` / `congestion_context.py` / `replay.py` / `trainer.py`)

三件事,都只動**訓練**,不動部署時挑波束的網路本體:

**(1) 壅塞情境輸入 χ_u(state augmentation)`congestion_context.py`**
每個使用者的狀態,對它**每個候選波束**多帶 3 個跟「這個波束會不會擠」有關的數字:
- `[..,0]` 上一步這個實體 cell 上有幾個人(**歷史**佔用)
- `[..,1]` 這一步有幾個人搆得到這個 cell(候選**競爭者數**)
- `[..,2]` 這個使用者在那些競爭者裡的**訊號排名**(user-specific;訊號好的排前面)
這三個都是**動作前**就能算的(只用上一步歷史 + 這一步的候選結構 + 觀測得到的訊號),**不偷看別人這一步挑了什麼**
(no-leak;有單元測試守 `test_chi_no_leak`,還有一個故意作弊的反例證明測試抓得到洩漏)。
第 3 個「訊號排名」是**打破對稱**的關鍵:兩個狀態幾乎一樣的人,如果只給共用的壅塞訊號會一起挑/一起閃還是撞;給了
各自的排名,網路才**有機會**學到「同一個擠的 cell 上,訊號差的讓開、訊號好的留」。數值正規化到 ~[0,1] 再進網路。

**(2) 依目標不對稱折扣 γ(asymmetric per-objective γ)`config.py` / `trainer.py`**
- **catfish 版(B2/A2):** `γ = [0.99, 0.90, 0.99]`(EE / 換手 / 負載)—— 換手看近、EE 跟負載看遠。
- **plain 對照版(B1/A1):** 三個目標同一個 `γ = 0.9`(= baseline 折扣)。
- (標 `hypothesis`:這是多目標 RL 的常見選擇,**不是** CDRL 的直接繼承;當 ablation 測,不當已證的主驅動。)

**(3) 價值分層回放(value-stratified replay)`replay.py`**
- **catfish 版(B2/A2):** 把「校準加權分數 `J_w` 特別高(超過 `μ_{J_w}+λσ_{J_w}`,`λ=0.5`)」的轉移額外丟進**優先池**;
  每個 minibatch 抽 `ρ=0.25` 的量從優先池(其餘均勻)→ 讓網路在「會發生壅塞競爭的關鍵狀態」上多練。
- **plain 對照版(B1/A1):** `ρ=0`,純均勻回放。

**訓練更新(`trainer.py` `_route_update`):**
- **Double-DQN** + 一步 TD;**每個目標各自**用自己的 `γ_k` 更新。
- TD 目標的「下一步動作 `a'_u`」用**該欄自己的分配規則**重算(argmax 欄用 argmax、協調式波束分配欄用協調式波束分配)→ 訓練跟部署一致
  (不會訓練時用一套、上線用另一套)。
- 因為協調式波束分配是「一步裡所有人一起」的聯合決定,回放存的是 **step-bundle**(整步所有使用者一起存),更新時才重算那一步的
  聯合分配。
- **ACRM 競爭獎勵 = v1 關閉**(off-by-default,設計 §6.4;打開會丟 `NotImplementedError`)。**PopArt 關。** r1=EE
  每次訓練用 grep + reward-vector 單元測試雙重守(防 r1 退回吞吐量的歷史 bug #19/#20)。

> **honest 註記(寫 ch4 要守):** 這個估值步驟是 CDRL 鯰魚效應的**延伸/再架構**,**不宣稱忠實重現** CDRL。CDRL 原本是單目標
> DDPG、一個 actor 出整個聯合動作、本來就不會崩;它的機制(經驗分層、不對稱折扣、競爭獎勵、70/30 介入)都作用在
> **訓練的 buffer / 折扣 / 獎勵塑形**,不動部署時挑動作的規則。

### 3B. 分配步驟 —— 協調式波束分配(線上,降低過度集中)`auction_decode.py`

每一步,先用訓練好的三個 Q 網路算每個使用者對每個候選波束的**綜合價值**:

  **`b_u(a) = Σ_k ω_k · Q_k(s_u^aug, a)`**  (三個目標 Q 加權,不可用波束遮成 −∞)

然後**不是各自挑**,而是協調著開波束(`decode_af_physical_auction`,greedy facility-location 開集):

- 每個動作 `a` 對應一個**實體 cell** `(l = a//7, c = slot_cell[u,a])`(同一個動作欄,不同使用者可能對到不同實體 cell)。
- 對每顆衛星 `l`,在 `k_cap` 個名額內,**一個一個貪婪地開**「能讓總綜合價值增益最大」的 cell:
  ```
  for 每顆衛星 l(名額 = k_cap):
      重複 k_cap 次:
          對每個還沒開的候選 cell c:
              gain[c] = Σ_u max( b_u(到 c) − b_u(目前已開的最佳) , 0 )
          開 gain 最大的那個 c
  每個使用者 u:分到「自己綜合價值最高、且該實體 cell 有被開」的波束;
              都沒開到 → 退回各自 argmax(env 會 cap_bump 它)
  ```
- 結果**保證**每顆衛星最多開 `k_cap` 個 cell(by construction 遵守硬限制)→ 降低過度集中(實際解崩程度由 ch5 量測,見下 ⚠ 誠實邊界)。
- (學習版 Q 可能為負 → 綜合價值先按每個使用者平移到非負 `shift_to_nonneg=True`,讓「開不開」的決策對 Q 的正負/平移
  穩健;固定規則 AF 版不平移,與凍結量測位元相容。)

**對照(B 欄)= 各自 argmax `decode_a0_argmax`** —— 原本的崩潰規則。

> ⚠ **誠實邊界(設計 §4.2,寫 ch4/ch5 要守):**「遵守 k_cap 名額」**不等於**「每個人都被服務」。一個使用者若它的候選
> 波束全都沒被開到,會退回 fallback、仍被 cap_bump。所以「解崩」是**量測出來的結果**,不是結構保證 —— ch5 要用實際
> 數字(served / cap_bump / min_cov / active_beams)講,不要寫成「協調式波束分配保證全覆蓋」。

---

## 4. 2×2 析因 + 對照(消融,如實 —— RED LINE #1/#2)

**{分配規則:argmax(B)/ 協調式波束分配(A)} × {訓練:plain / catfish}**,架構在四格**完全相同**(state-aug 是共用選擇,
**不算**在 catfish 帳上;「catfish」= 訓練配方 = 不對稱 γ + 價值分層回放)。

| arm | 分配規則 | 狀態 | 訓練 | 角色 / 隔離什麼 |
|---|---|---|---|---|
| **B0** | 各自 argmax | baseline(無 aug) | 凍結 baseline | 崩潰參考 ＋ ~弱靜態 |
| **B1** | 各自 argmax | +χ_u | plain TD | aug credit(B1−B0) |
| **B2** | 各自 argmax | +χ_u | catfish(不對稱 γ + 價值分層) | **B 欄鯰魚 credit(B2−B1)** |
| **AF** | 協調式波束分配 | —(用觀測訊號綜合價值) | 固定規則,不學習 | 無學習 kill-test + **anti-decorative gate-control(學習版要贏過 AF)** |
| **A1** | 協調式波束分配 | +χ_u | plain TD | 學習分配 credit(A1−B1) |
| **A2** | 協調式波束分配 | +χ_u | catfish | **A 欄鯰魚 credit(A2−A1)** |

四格(B1/B2/A1/A2)是 **4 次獨立訓練**(TD 目標用各欄自己的分配規則 → argmax 訓出來的 Q ≠ 協調式波束分配訓出來的 Q,不能共用)→
**heavy → server → HARD USER GATE**。B0 / AF / 弱靜態 = 純評估(local)。

**credit 讀法(誠實,RED LINE #2):**
- **解崩主要靠「分配規則」,不是鯰魚訓練。** 證據 = **cross-over**(§6):同一組 Q,只換分配規則,崩潰就翻轉。
- 鯰魚訓練 credit = B2−B1 / A2−A1(within-column,乾淨);學習分配 credit = A1−B1。
- catfish 用「**框架具名核心組件(產生綜合價值的估值步驟)**」拿 credit,**不寫**「消融證明鯰魚是 win 的主因」「移除鯰魚會崩」
  —— 那會被自己的消融打臉(A2≈A1)。

---

## 5. 整體流程(給圖 track:FIG-4 架構 + FIG-5 流程圖)

**訓練(FIG-5 演算法流程圖):**
```
env.reset
  └► 算 χ_u 壅塞輸入(歷史佔用 + 候選競爭者數 + 訊號排名)
  └► 三個目標 Q 算綜合價值 v_u(a) = Σ w_k Q_k(s_u^aug, a)
  └► 該欄分配規則挑動作:argmax(B)/ 協調式波束分配(A) ＋ ε 探索
  └► env.step →(r1=EE, r2, r3)→ 校準成 J
  └► 存 step-bundle 到回放(catfish:高 J_w 進優先池)
  └► 抽 batch(catfish:ρ=0.25 來自優先池)
  └► 對三個目標各自:Double-DQN、不對稱 γ_k、一步 TD(下一步動作用該欄分配規則重算)→ 更新
  └► 週期同步 target;週期評估 → 存最佳 ckpt
```
**線上推論(FIG-4 右半):** env 狀態 → χ_u → 三個 Q 算綜合價值 `b_u(a)` → **協調式波束分配**(k_cap 限制下開集 + 分配)→ 動作。

**FIG-4 架構(估值+分配兩步整合,以鯰魚為核心):**
- 估值步驟:三個 per-objective 鯰魚 Q + χ_u 壅塞輸入 + 不對稱 γ + 價值分層回放 → 產生多目標綜合價值。
- 分配步驟:協調式波束分配(綜合價值 → 每顆衛星 k_cap 開集 → 指派)→ 框架內的線上選波束。
- baseline 對照(FIG-3,另畫):原 MODQN = 三 Q + 純量化 + **各自 argmax**(無鯰魚、無協調式波束分配;乾淨,之後對照才清楚)。

---

## 6. ch5 已有的 headline 事實(主實驗 k_cap=3;已核實 RESULT.json + 裁決過)

> ⚠ **SUPERSEDED 2026-06-29 — k_cap sweep 已 DONE(全 13 點 k=3–15),且平滑版框架已 RETRACT。** 權威 =
> `scratch/final_figures/fig5_4_kcap_sweep_raw.csv`(RAW 平均 + bootstrap CI)+ `thesis-mc/CH5-FIG-SMOOTHING-FIX-NOTE-2026-06-29.md`
> (USER 抓到 σ=1.3 高斯**邊界假影**)。**RAW+CI 結論(取代舊的「win-zone k≤12 / k=15 崩潰消失」):** A2 的 J_w 在
> **k=3–10 CI 分開贏**(8 連點);k≥11 兩者都 →0、逐點 sub-1e-4 互換(無穩定高下);**A2 min_cov ≈1.0 + EE 在 ALL k CI 分開 > B0。**
> 寫 ch5 用這個 RAW+CI 結論 + `CURRENT-STATE.md`,**不要**用下方「server 正跑 {6,9,12}」/「k=15 崩潰消失」的舊文字。

> **數字權威 = `route-b-factorial-{RESULT.json,VERDICT-G6,INDEPENDENT-ADJUDICATION}-2026-06-27.md`**(codex 跨模型 G6 +
> 獨立二階裁決,SOUND-confirmed)。下面是核實過的值;ch5 寫作以裁決文件為準。

`calib J_w`(校準加權,愈大愈好)/ `min_cov`(尾端覆蓋,0 = 餓死有人)/ `active`(活躍波束數,崩潰→少)/ `qos`(達標率):

| arm | calib J_w | min_cov | active | qos | 讀法 |
|---|---|---|---|---|---|
| **B1**(plain MODQN+argmax,~baseline) | **−1.6e-5** | 0.0 | **3** | 0.29 | 崩潰參考 |
| **B2**(argmax+catfish) | 4.5e-5 | 0.0 | 3 | 0.30 | **仍崩**(regime-trapped) |
| **A1**(協調式波束分配+plain) | **4.97e-4** | **0.999** | **12** | **0.99** | **解崩** |
| **A2**(協調式波束分配+catfish) | 4.82e-4 | 0.999 | 10.8 | 0.97 | 解崩(A2≈A1) |
| AF(固定協調式波束分配,gate-control) | 4.44e-4 | 1.0 | 5.3 | 0.95 | 學習版要贏過它 |
| RSS_max(弱靜態) | 1.55e-4 | 0.0 | 3.3 | 0.31 | A1 贏 |
| round_robin(弱靜態) | 1.60e-4 | 0.0 | 12 | 0.41 | A1 贏 |
| DQN_throughput(弱靜態;5-seed field) | 3.54e-4 | 0.00 | 5.6 | 0.634 | A1/A2 平均較高,但 J_w CI 重疊;覆蓋贏 |
| **DQN_scalar**(弱靜態,衝加權純量) | **6.41e-4**(lci 5.96e-4) | **0.00** | — | — | **A1 在純量上輸它**;但 A1 在 min_cov 輾壓它 |

**框架「真的贏」的(全 `grounded`,可當 headline):**
1. **贏 baseline MODQN(= 教授的 bar):** A1/A2 ≈ 5e-4 vs B1/B0 ≈ −1.6e-5。
   ~~解崩(active **3→12**、qos **0.29→0.99**、min_cov **0→0.999**)~~ —— ⛔ **待重驗（2026-07-20 FOUNDATION CORRECTION）**：此組數字量自 `lr=0.01` 世代，而該世代的「崩潰」已證實是學習率產物（單變數隔離：只翻 lr 0.01→0.001，argmax EE 235.53→472.22、min_cov 0.312→0.698；調校正確的 baseline 並不崩）。**在以 lr=1e-3 正式協定重測之前，不得當 headline、不得標 `grounded`、不得寫成「本框架解除了崩潰」。** 權威：`CURRENT-STATE.md` 最上方 ＋ `analysis/family-b-collapse-diagnosis/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md`。
2. **最佳多目標 operating point:** 滿覆蓋(min_cov 0.999)+ EE 全場最高;贏 RSS_max / round_robin / DQN_throughput。`grounded`。
3. ~~**k_cap 診斷:** k_cap 是 baseline MODQN 崩潰主因之一~~ ⛔ **待重驗（同上，lr=0.01 世代）**：(k_cap=15 容量放寬後崩潰消失;server 正跑 {6,9,12} sweep
   把曲線補硬)。`grounded`(3/15 點)/ sweep `pending`。

**cross-over(§4 credit 的證據,`grounded`):** 同一組 Q 換分配規則 → 崩潰翻轉(B1_xover 解崩、A1_xover 崩)→ **解崩是
分配規則在做,不是鯰魚訓練**。

**A2≈A1(`grounded`):** 協調式波束分配欄裡加鯰魚訓練沒有額外贏 → 鯰魚訓練在這個設計裡是**具名核心組件(by-association)**,
不是 win 的因果主驅動。誠實當消融呈現。

---

## 7. RED LINES(binding;文字 + 圖都守 —— 出自 THESIS-FRAMING-DECISION)

1. **消融數字保持正確 + 有呈現**(B1/B2/A1/A2 都在、且正確;永不竄改)。
2. **不寫消融會打臉的假因果:** 不要寫「消融證明 catfish 訓練是 win 主驅動」或「移除 catfish 導致崩潰」
   —— cross-over + A2≈A1 顯示**解崩是協調式波束分配/分配規則在做**。catfish 用**命名/組件歸屬**拿 credit。
3. **不宣稱在原始加權純量上贏 DQN_scalar。** DQN_scalar = 本專案內部加的對抗性 stress-test,**不是**教授的 bar。
   處理 = USER+教授決定:(a) 放進來、框成「我們在**公平/覆蓋軸**輾壓它(min_cov 0.999 vs 0.00)」;或 (b) 不放。
   兩者皆**不可**宣稱「在原始純量上贏它」。
4. 載重 claim 標 `grounded` / `hypothesis` / `ruled-out`。
5. **不寫**「解決了崩潰根因」(ROOT-Q 仍 UNRESOLVED;框架是繞過 + 相對贏)。不放 2.8× / 0.72C / beats-Sun2024 字樣。

---

## 8. 邊界 / 不變量

- 只動 `thesis-mc/`(+ 圖在 `research-visual-lab`)。`thesis/` = 死的 route-C 蒸餾 fallback,不碰、保留。
- G1 `modqn.py`(`aa877676`)+ env EUV `family_b_step.py`(`389eaaef`)**唯讀**。
- heavy / training = **HARD USER go-server gate**。
- 載重 prose / claim 定稿前過 **cross-model codex** voice/claim check。
