# 偏離登記表 — 相對 MODQN(PAP-2024-MORL-MULTIBEAM)明載值

## Multi-Catfish 實驗證據偏離（不屬於 X 類參數偏離）

### E-1 10EP matched ablation：`VOID_UNINTERPRETABLE_INSTRUMENT`

`artifacts/multi-catfish-v03-10ep-matched-ablation-20260831/receipt.json`
保留為 provenance，但不得作為 C1/C2/C3 正負效果或 EE efficacy 證據。
審核發現三個 Q 的總分主要由 state-independent per-action bias 支配，且
`A101`、`A110`、`N000` 在受查 real-state set 上產生相同動作；因此原本
五個 `directional_pass` 欄位全部失去 route-level 解析力。C1 neutral
control 另有 anchor-user cluster geometry 不匹配，C2 另只使用兩筆
plumbing-smoke rows。正式 invalidation overlay 為同目錄的
`AUDIT-VOID.json`；完整證據與下一個 E1 gate 見
`MULTI-CATFISH-MCRL-V03-10EP-ABLATION-AUDIT-2026-08-31.md`。

### E-2 free-output E1 validation：`DESIGN_ONLY_ACTION_SLOT_SHORTCUT`

第一版 E1 的三個 `228 -> 28` free-output Q surface 在 held-out states 上
有約 0.90--0.96 的 fixed action-slot explanatory fraction；而 C2/C3 的
action-only null MAE 又比 parameter-free zero predictor 更差，因此舊
`skill` 會高估 learnability。這不否定 C1/C2/C3 的物理 target，但否定
該 learner 與單一 action-only denominator 作為 test-opening authority。
修正採三個獨立 local action-shared scalar scorers，並以
`min(action-only, zero, train-median)` 作 stronger null。舊 validation 已
參與修正選擇，降為 design-only；舊 test 仍封存未讀。Fresh 4/3/0
train/validation supplement 與 bounded 500EP gate 見
`MULTI-CATFISH-MCRL-V03-E1-ACTION-SHARED-AMENDMENT-2026-09-01.md`。

### E-3 action-shared E1 validation：`INSUFFICIENT_C2_ACTION_GRAPH_COVERAGE`

Fresh action-shared 4/3/0 corpus 在任何 target、MAE、model prediction、EE 或
test outcome 被檢視之前，target-free census 發現 C1/C3 的 train comparison
graph 已涵蓋全部 28 actions，但 C2 的 36 筆 validation contrasts 中有 6 筆
跨越未連通 component。依 instrument-validity contract §7，這是
`INSUFFICIENT_COVERAGE`，不是 C2 target 或 Multi-Catfish efficacy 的負結果。
依同一 contract §9，只允許一次已封存規則的 C2 train-only fresh-seed
expansion：不得重生 C1/C3、不得更動 validation bytes、不得開 test、不得計算
EE，也不得依 target/outcome 選 seed。補充後若 C2 graph 仍未連通，必須停止並
重新設計，不得再換第二組 seed pool。

固定 20-seed prepare 後，所有原不支援 contrasts 在 schedule topology 上已連通，
但事前加嚴的 `3 clusters / 2 seeds` redundancy gate 中，actions 4 與 14 各只有
`2 clusters / 2 seeds`，因此 receipt 仍為 `INSUFFICIENT_COVERAGE` 且未生成任何
pair outcome。後續 target-free design probe 把 focal enumeration 暫時展開到
100，只能證明 actions 4/14 的物理候選存在；上位 contract §3.1 明定每個 world
anchor 最多五個 focal users，因此該 probe 不得成為正式 source。Opus Max 裁定
下一個合法方向是維持 cap=5、增加 distinct-anchor／per-seed schedule coverage 的
action-balanced C2 source-selector redesign；不得事後放寬 gate、換第二個 seed
pool，亦不得改動 C1/C3/EE 公式。

### E-4 fresh action-shared validation：`ONE_SHOT_MASKED_MEANMAX_FALLBACK`

正式 action-balanced C2 TRAIN expansion 以固定 seed prefix `2026092201--04`
生成 48 筆 sealed rows，completed-row action graph 通過原定的
`3 clusters / 2 seeds` gate；沒有開 test 或計算 EE。其後 fresh V3 validation
在共同 rung 10 通過 C1、C2、collision、action-main-effect 與全部 C2
anchor-balanced／leave-one-anchor-out gates，但 C3 對 strongest null 的 mean
skill 為 `-0.008553`（`0/3` initializations 為正），因此依 action-shared
amendment §6 回傳 `EVALUATE_MASKED_MEANMAX_ONCE`，不是 500EP GO。

`masked mean/max` 並非在看到這個 fresh C3 結果後才發明。它先在
design-only rows 上與四個 context variants 比較，當時使用 action-only null：

| scorer | C1 skill | C2 skill | C3 skill |
|---|---:|---:|---:|
| local | 0.2711 | 0.2659 | 0.1298 |
| mean | 0.2477 | 0.2681 | 0.1286 |
| **meanmax** | 0.2440 | 0.2669 | **0.1532** |
| deepset | 0.2402 | 0.2656 | 0.1395 |

因此 meanmax 是 design split 上依 C3 選出的單一 fallback；fresh split 才是
它第一次接受 `min(action-only, zero, train-median)` strongest-null gate。這也
表示同一 fresh validation bytes 共有兩次預先界定的 look：先 local、再且只再
一次 meanmax。此 exploratory sign gate 沒有 alpha-control；第二次結果不論
GO/STOP 都耗盡 fallback，不得改 seed、rung、null、source、target、hyperparameter
或再試第三個 scorer family。

Meanmax 只把每個 route-local shared scorer 的輸入由
`[x_a,g]` 擴成 `[x_a,g,mean_m(x),max_m(x)]`，legal mask 必須使用資料中的
顯式 Boolean action mask，不得從 state feature 推導。每個 head 的輸入寬度
`12 -> 28`、參數數 `8,951 -> 10,551`（約 `+17.9%`）；三個 initialization
seed 相同，但因第一層寬度不同，不是 weight-matched comparison。物理 C1/C2/C3、
三個獨立 Q heads、pair loss、`beta=0.1`、`lr=0.001`、hidden widths、共同 rung
規則、deployment sum/masked argmax 與 EE endpoint 全部不變。只有完整重跑同一
Section 5 gate 且三 routes 全過，才可授權一次 bounded 500-source-epoch screen；
否則必須記為 `STOP_MASKED_MEANMAX_VALIDATION`。

### E-5 C2-k1 successor：`OFFSET_ONE_TARGET_FOUR_OFFSET_FALSIFICATION`

V0.3 §3 的「offsets 1--3 全屬 C2，不能省略 release offset 3」只約束現已退役的
four-offset hold/release C2。V0.5 controlled-tape 因 candidate branch 缺乏 native
support 而封存為 diagnostics-only 後，V0.6 改以 offset 1 的乾淨 branch-local
Q1+Q3 successor effect 作為 C2 target；offsets 2--3 不再進 target，只作為
four-offset oracle-headroom falsification outcome，用來檢查 surrogate reversal。此偏離
不改 final ratio-of-sums EE、C1、C3、三個獨立 Q networks、共同 safe mask、或
deployment 的直接未加權 `argmax(Q1+Q2+Q3)`。V0.6 T1 通過只允許一次 bounded
Q2 learner screen；失敗只否證該 single-application C2-k1 formulation，不得移除
mandatory C2 route。

---

類別依 `NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md` §0:
**P** 原文明載 / **P′** 其他已發表來源 / **D** 推導 / **S** 自訂 / **X** **偏離 P**。

> **`S` 是合法的,`X` 才需要辯護。** 本表只列 `X`。
> 每一條都必須在論文中明講偏離與理由,**不得靠別的東西沒變帶過**。

---

## X-1 學習率 `α`:`0.01 → 0.001`

| | |
|---|---|
| 原文 | Table I 明載 `α = 0.01` |
| 本論文 | `0.001` |
| 理由 | `0.01` 訓練時很快發散(作者確認)。**不是設計選擇,是事故處理** |
| 但書 | 專案自己的消融顯示 `0.001` 買到的**不是鑑別力**:`q_margin` 掉 10×,逃脫機制是 **near-flat Q 下的 argmax 分散**。此揭露必須與偏離寫在一起 |
| 處置 | **列為受控變因**,不得取任一邊預設;P6 掃 `{0.01, 0.003, 0.001}` |
| 出處 | SDD §2.3 |

## X-2 衛星高度:`780 km → 約 485 km`(量測分布)

| | |
|---|---|
| 原文 | Table I 明載 `h = 780 km` |
| 本論文 | 真實 Starlink TLE + SGP4 ⇒ 高度成為**量測分布**,可見者中位數約 485 km(語料後段) |
| 理由 | F3:改用真實星曆,高度不再是自由參數 |
| 連鎖 | `R_b` 22.60 → 14.06 km;FSPL 少 4.13 dB;地平離天底角 62.99° → 68.32°;`μ` 上限 64.80 → 67.32;通過時長、角速度、D2 的距離↔仰角對應全部改變 |
| 出處 | SDD F3;量測見 `docs/EPHEMERIS-NOTES.md` |

## X-3 每衛星波束位置數:`7 → 39`(**C-3 已定案**)★

| | |
|---|---|
| 原文 | Table I 的 `V = 7` —— 是 `\|𝒱\|`,一顆衛星的波束位置**總數** |
| 本論文 | **39**(指向格數)。裁決 C-3 定案:以**全序排序**選出後,把 39 個 `cell_id` **字面凍進 PREREG**;量測覆蓋 **95.17%**,達標 |
| 理由 | **原論文的波束沒有幾何**。全文 grep `off-axis / boresight / pointing / 3dB / half-power / footprint / steer / earth-fixed` **零命中** ⇒ 那裡的「波束」是**非空間的載量通道**,`G_{i,l,v}` 實際只依賴衛星—使用者距離,同一顆衛星的 7 道通道完全相同。7 不需要蓋到任何土地,所以它是 7、3 或 70 都沒有差別。 |
| | **本論文加入了他們缺的幾何**(偏軸增益 `G^T(θ)`、含干擾 SINR、角度感知 EE)。波束一旦有指向與 3 dB 涵蓋圈就**必須蓋到地面**,數量不再自由:200×90 km 服務區在 485 km 下需 **39 格**才達 95% 覆蓋(量測 95.5%)。**7 格只蓋得到約 1/5**。 |
| 已否決的替代 | 「讓 7 道寬一點鋪滿」需 Iridium 級寬波束,覆蓋 lumpy 有洞,且寬波束會讓偏軸增益差異塌掉 ⇒ **角度感知 EE 的貢獻本身消失** |
| ⚠ 措辭要求 | 這是 `X` 級場景偏離,與 X-2 同一類。**動作空間 `4 × 7 = 28` 完全不變**,但**不得用「28 沒變」把這條蓋過去** |
| 出處 | 裁決 `RULING-2026-08-22-no-beam-count-cap.md` §7.8、§2 |

### X-3 的附帶:`J_w = 7` 與 `V = 7` 數值相同純屬巧合

| 符號 | 是什麼 | 在本論文 |
|---|---|---|
| `V` | 一顆衛星**有幾個波束位置** | **39**(取代原文的 7) |
| `J_w` | 一位使用者**看得到幾個**(錨定格 + 六鄰居) | **7**(六角鄰域論證) |

在 MODQN 這兩個是同一個 7(全域共用同一組);在本論文它們分開了,
而且**不同使用者的 7 個不是同一組**。**兩者不得互相代入。**
程式端的警語在 `src/mcrl/env/action_contract.py` 的 `NUM_BEAM_SLOTS` 處。

---

## 不是偏離的(常被誤認)

| 項目 | 為何不是 `X` |
|---|---|
| 回合長度 `H = 10` | **維持** Table I,與 `β=0.9` 自洽(F1) |
| 動作空間 `4 × 7 = 28` | **完全不變**,扁平輸出、`(100,50,50)`、tanh、逐使用者獨立 argmax 全部保留 |
| 三色頻率重用 `B^w` | MODQN 完全未提重用 ⇒ 來源沉默,是 **P′/S** 不是 `X` |
| ~~執行遮罩 `m^e`~~ | **已不存在**。裁決 C-11 定為**兩閘** `x = a·z`;`m` 只作決策時遮罩、不進連線恆等式,選上與被服務之間的閘是**逐鏈路功率可行性** |
| **無每衛星波束數上限** | **回到原論文的結構**。`Σ_v z_{s,v} = V` 在原文是**恆等式不是上限**;上限從頭到尾是舊 repo 自己發明的 |

---

## 揭露(非 `X`,但必須在論文明講)

### S-1 `L_c` / `L_s` 的數值來源是 TR 38.811,不是 HOBS

| | |
|---|---|
| 來源 | HOBS 式 (1) **只給四項損耗的名字,沒給值** |
| 本研究 | 以 TR 38.811 的 NTN 表格代入:`L_c` 表 6.6.6.2.1-1(20 GHz 對流層閃爍)、`L_s` 表 6.6.2-3(Ka LOS 遮蔽 σ) |
| 為何不是 `X` | 來源**沉默**,不是本研究偏離了一個已載明的值 —— 與三色重用同一類 |
| 措辭要求 | 必須明講這是**代換**,不得寫成 HOBS 自己的數字 |
| 附帶排除 | 電離層閃爍不計(TR 38.811 §6.6.6.1:僅 6 GHz 以下);clutter loss 不計(僅 NLOS,本研究為固定 VSAT LOS) |
| ⚠ 表格原文的不連續 | `L_s` 的 σ 在 80° 為 3.6 dB、90° 為 **0.4 dB**。**逐字照抄,不得平滑** |

---

## 論文兩處已依 W-17 的量測修正(**不是本專案的偏離**)

兩項都是**論文的兩條式子互相牴觸**,實作無法同時滿足;
控方裁定兩處都改論文、不改實作。詳見
`docs/CONTROLLER-RULINGS-W17-2026-08-22.md` 與 `docs/CONTROLLER-FINDINGS-W17-2026-08-22.md`。

| # | 矛盾 | 裁決 | 量測 |
|---|---|---|---|
| **F-1** | `p⁰ = 2 W` > `p_max = 1.65 W`,而 (3.12) 的段起始就是 `p(τ) = p⁰` | `p⁰ = p_max/2 = 0.825 W`(3 dB 增益預算);`p_max` 被放大器綁死不動 | outage 率 **1.0 → 0.0000**(12,000 決策步) |
| **F-2** | (3.16) 逐**鏈路**求和 `Σ_u Σ_s Σ_v x·P^p`,但一支波束只有一個放大器 | `P^N` 改逐波束二重和,`ξ`/`P^p` 去 `u` 索引 | 舊式高 **2.107–2.626×**;迴歸比值現恆為 **1.0** |

### X-4 `p⁰`:`2 W → 0.825 W`

| | |
|---|---|
| 原文 | Table I 的 `p⁰ = 2 W`(**P**) |
| 本論文 | **0.825 W**,寫成 `p_max/2` 的導出 |
| 理由 | 2 W 與 `p_max = 1.65 W` 直接互斥,實測 outage 恆為 1.0。`p_max` 由 `p_sat = p_max·10^(BO/10) = 5.218 W` 綁死且 `p_sat` 在 (3.15a) 分母裡 ⇒ 只能動 `p⁰` |
| ⚠ 措辭要求 | 導出的**結論**(3 dB 預算)成立,但預算是**相對段起始角度**量的,不是對著波束軸。量測:11.2% 的 segment 起始就在 3 dB 圈外。**不得寫成「outage ⇔ 出格」** |
| 出處 | 裁決 `CONTROLLER-RULINGS-W17-2026-08-22.md` F-1 |

---

## 差點做錯的(量測之後才知道有多接近)

這一欄不是偏離,是**已經避開但值得留檔的錯誤**。留著的理由是:
它們當初都「看起來合理」,而事後才知道代價有多大。

### N-1 (3.12b) 的內層和差點被加上 `v' ≠ v`

| | |
|---|---|
| 差點做的 | 在 (3.12b) 的內層和加上 `v' ≠ v`,理由是「同一格不該干擾自己」 |
| 為什麼會想這樣做 | (3.12a) **有** `v' ≠ v`,把它對稱地套到 (3.12b) 看起來自然 |
| 為什麼是錯的 | (3.12a) 排除 `v` 是因為**在同一顆衛星上**它就是 wanted beam 本身;(3.12b) 對 `s' ≠ s` 求和,那裡的 `v' = v` 是**另一顆衛星照同一格**,是完全不同的一項 |
| **量測到的代價** | **P4:兩顆衛星照同一格發生在 80.0% 的步上** |
| 若做錯的後果 | 刪掉一個在八成步裡都存在的項 ⇒ **系統性低估干擾 ⇒ 高估 SINR 與 EE**,而且高估的方向正好對本論文有利 |
| 為何沒做錯 | 逐字實作 (3.12b),並在 `env/interference.py` 的模組 docstring 寫明「只有 (3.12a) 排除 wanted beam,因為只有那裡它在求和範圍內」 |
| 測試 | `test_w17_interference.py::test_the_same_cell_on_another_satellite_is_the_dominant_term` |

⚠ 這不是罕見邊界情形,是**常態**。「同一格」在直覺上聽起來像自我干擾,
在三色重用 + 多衛星的幾何下它是最強的干擾來源之一 ——
兩顆衛星同時把主瓣對準同一塊地面,受害者同時落在兩者的軸心上。
