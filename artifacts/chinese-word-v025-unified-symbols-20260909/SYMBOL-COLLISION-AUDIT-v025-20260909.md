---
audit_id: v025-unified-symbol-collision-20260909
status: PASS_WITH_REGISTERED_CONFLICTS_AND_GAPS
supersedes: v023-symbol-collision-single-letter-20260905
scope:
  merged_table: artifacts/chinese-word-v025-unified-symbols-20260909/active-symbol-table-v025-20260909.md
  authority_1: artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md
  authority_2: artifacts/chinese-word-v023-lcsrs-20260905-r2/SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md
  authority_3: .scratch/multi-catfish-v023-controller-handoff-20260907/paper-lane-20260909/SYMBOL-ADDITIONS.md
  authority_4:
    - .scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md
    - .scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1..v1.9
    - .scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md
    - .scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md
    - .scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1.2-AMENDMENT-2026-09-09.md
    - .scratch/multi-catfish-v025-physics-successor/V025-CH5-SWEEP-FIGURE-SPECIFICATION-2026-09-09.md
    - .scratch/multi-catfish-v025-physics-successor/V025-ACM-DEFECT-CONFIRMATION-2026-09-09.md
    - .scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-ACM-FIX-PROBE-SPLIT-2026-09-09.md
    - .scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-PROBE-NEIGHBOURHOOD-2026-09-09.md
    - .scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECISIONS-PROBE-SPLIT-AMENDMENT-1-2026-09-09.md
    - .scratch/multi-catfish-v025-physics-successor/V025-CONTINGENCY-LADDER-PREOUTCOME-2026-09-08.md (+AMENDMENT-1-R7)
    - .scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-FINDING-FIGURE1-AND-BACKOFF-2026-09-09.md   # 於本稽核進行中 16:13 落地，已納入
commands:
  forbidden_subscript_scan: "python3 -c \"re: (?:_|\\^)\\{?(ref|src|dst|beam|sat|own|nf|joint|base|cand|main)\\}?\" merged_table"
  composite_scan: "python3 -c \"re: (?<!\\\\)[_^]\\{[^}\\\\n]+\\}\" merged_table"
counts:
  source_rows: 304
  merged_rows: 409
  added_rows: 105          # 93 marked 【新】, 12 marked 【改】
  registered_conflicts: 15
  sealed_symbols_absent: 16
---

# V0.25 合併符號表 —— 碰撞與單字母稽核

## 0. 裁決

合併表在**碰撞規則層面通過**：V0.25 新增的紙面主符號，其上下標一律是單一字母或
單一數字，複合索引由原子字母／數字組成，且未引入 hat 或多字母標籤。

但本輪**不是一份乾淨的 PASS**。三件事必須被讀到：

1. **15 條登記在案的衝突**（第 4 節）。其中 5 條是密封宣告之間或密封宣告與符號權威
   之間的直接不一致，本表依權威順序採用其一，**未靜默取捨**，並保留另一方的字形作為
   引擎別名。有兩條（C-01 的 \(F\)／\(G\)／\(\Phi\) 歸屬、C-13 的段記憶退場）**目前無法
   由現有文件單方裁決**，需使用者或後續密封宣告確認。
2. **16 個出現在密封宣告、但沒有進入合併表的量**（第 5 節）。這是本稽核最重要的一份
   清單：每一個都附上為何未進表的理由，其中 4 個（C2 延續值、候選刷新週期 \(N\)、
   standby 比例、跨波束交互增益）在正文寫作時**一定會需要字形**，屬於待裁決缺口。
3. **兩個先前未被發現的碰撞**（C-05、C-06）：R-1 把換手成本改名 \(\Phi_u(t)\) 之後，
   與 §10.12.3 的 V0.3 部署分數 \(\Phi_u(t,a)\) 同字母同下標；以及 \(\lambda\) 作為
   凍結 bits-per-joule 乘子，與第 3.1.2 節天線口徑式 \(D=1.0275\lambda/\theta_3\) 中的
   波長 \(\lambda\) 同字母。兩者都不在 `SYMBOL-ADDITIONS.md` 的碰撞檢查中。
4. **一份密封宣告在本稽核進行中落地**（16:13，`V025-CONTROLLER-FINDING-FIGURE1-AND-BACKOFF`）。
   它已被納入：合併表的 \(\mathcal M\)、\(\nu_m\)、\(R^{+}\)、\(m^{q}\) 四列與速率回退段落
   依其更新，並新增衝突 C-15。它同時為 \(m^{q}\) 引入宣告狀態 `NO_MODE`（目標模式已是
   最低模式時無回退空間），該 token 已登記為狀態值而非模式索引。

## 1. 掃描結果（在合併表上重跑）

### 1.1 多字母上下標禁用掃描

| 樣式 | 命中 | 判定 |
|---|---:|---|
| `ref` | 1 | 位於 §10.14.6「不得進入公式」對照表，引用引擎名稱 `eta_ref`／\(\eta_{\mathrm{ref}}\) 作為**被取代的對象**；非公式使用 |
| `sat` | 1 | 同上，引用 `p_sat` 作為 \(p^{s}\) 的引擎名稱；非公式使用 |
| `src`、`dst`、`beam`、`own`、`nf`、`joint`、`base`、`cand`、`main` | 0 | —— |

公式本體零命中。兩處命中都在對照表的「引擎名稱」欄，且該表開頭明文「不得進入公式」。

### 1.2 複合上下標掃描

V0.25 新增的全部複合形式皆為原子：`{q}`、`{o}`、`{r}`、`{1}`、`{d}`、`{\psi}`、
`{f}`、`{m}`、`{a}`、`{\alpha}`、`{\star}`、`{-}`、`{+}`、`{\mathcal K}` 與既有的
`{u,s,v}`、`{s,v}`、`{u,c}`。

掃描到的**非原子**形式共 7 種，全部是 V0.23 權威表既有的歷史／retired 條目，
本次合併未新增也未改寫任何一個：

| 形式 | 出處 | 分類 |
|---|---|---|
| `_{st}`、`_{st,max}` | §9、§10.51 掃描損耗 \(L_{st}\) | 2026-08-21 已退出公開表面 |
| `_{max}` | §9 的 \(v_{\max}\) | 2026-08-21 已刪除 |
| `_{3dB}` | 2026-09-05 擴充層的舊紙面記號欄 | 對照用舊字形 |
| `_{flat}` | §9 的 \(F_{flat}\) | 已退出公開表面 |
| `^{PA}` | §10.11 的 \(\eta^{PA}\) | legacy provenance |
| `_{i,l,v}` | §9 的 MODQN \(G_{i,l,v}\) | 來源論文記法，明文不合併 |

## 2. 一符兩義（或多義）清單

下表列出合併後**同一字母承載兩個以上意義**的每一個符號，以及區分方式。
「狀態」欄的 `retired` 表示該義只存在於 §10.8／10.9／10.12／10.13 的歷史區。

| 符號 | 各義 | 區分方式 | 狀態 |
|---|---|---|---|
| \(F\) | ① 天線角度型樣 \(F(\theta,\theta_3)\) ② 經驗分布 \(F_W\) ③ 鯰魚端標籤上標 \(F\) ④ masked token aggregate \(F_i(a)\) ⑤ 引擎／探針的分數 \(F\) | ① 帶兩引數；② 帶下標 \(W\)；③ 位於上標位；④ 帶成員下標＋動作引數；⑤ 只出現在引擎散文，紙面一律寫 \(\Omega(a)\) | ①active ②③④retired ⑤引擎名 |
| \(G\) | ① 增益族 \(G^T,G^R,G_0\) ② V0.23 profile surplus \(G(x)\) ③ 引擎／探針的協調器目標 \(G\) ④ v1.9 §3 的宣告衰落乘積 | ① 帶單字母上標或下標 0；② 已由 R-2 改為 \(\Omega(a)\)；③④ 本表不採，見 C-01／C-02 | ①active ②retired ③④不採用 |
| \(\Psi\) | ① 換手成本 \(\Psi_u(t)\)（V0.23 式 3.27） ② two-user 交互作用 \(\Psi_B,\Psi_E,\Psi\) ③ 集合層交互作用殘差 \(\Psi_{\mathcal K}\) 及其 \(q/1/f\) 上標版本 | ① V0.25 改名 \(\Phi_u(t)\)（R-1）；② retired；③ **恆帶花體集合下標** | ①V0.23 active ②retired ③V0.25 active |
| \(\Phi\) | ① V0.25 換手／QoS 計價 \(\Phi_u(t)\)、\(\Phi(a)\) ② V0.3 部署分數 \(\Phi_u(t,a)\)（§10.12.3） | 只靠第二引數 \(a\) 與 retired 標記區分 —— **弱區分，見 C-05** | ①active ②retired |
| \(\Omega\) | ① 三目標純量化權重 \(\Omega=[\omega_1,\omega_2,\omega_3]\) ② 組態層剩餘 \(\Omega(a),\Omega^{q}(a),\Omega^{q}_{j}(a)\) | ① 已退場、\(\omega_j\) 不得出現；② **恆帶組態引數** | ①retired ②active |
| \(d\)／\(D\) | ① 斜距 \(d_{u,s,v}\) ② 單邊增量 \(d_i(a)\)（再定義） ③ 總和 \(D(a)\) ④ 天線口徑 \(D=1.0275\lambda/\theta_3\) ⑤ 訓練端索引 \(d\in\{M,F\}\) ⑥ 資料集 \(D^{o},D^{t},D^{a}\)、經驗池 \(D_M,D_F\) | ①三下標；②單成員下標＋引數；③大寫＋引數；④無引數大寫（**待改寫為 \(D_a\) 或文字**）；⑤⑥ retired | ①②③active ④待處理 ⑤⑥retired |
| \(q\) | ① 六角格軸向座標 \(q_{s,v}\) ② 分位通道增益因子 \(q^{\alpha}_{u,s,v}\) ③ 選擇時視圖上標 \(q\) ④ 分位引數 \(q,q_1,q_2\) | ① 雙下標無上標；② 三下標＋上標；③ 純上標；④ retired | ①②③active ④retired |
| \(\alpha\) | ① 仰角 \(\alpha_{u,s}(t)\) ② 分位水準 \(\alpha\)（\(q^{\alpha}\) 的上標） ③ 衛星功率縮放 \(\alpha_s(t)\) | ① 恆雙下標、從不在上標位；② 恆上標、恆無下標；③ legacy | ①②active ③legacy |
| \(m\) | ① 遮罩 \(m_{u,c}\)、\(m_{iar}\) ② ACM 模式索引與 \(m^{r},m^{q},m^{o}\) ③ 型樣索引 \(m\) ④ 執行遮罩 \(m^{e}\) ⑤ v1.7 的選擇時視圖上標 \(m\) | ① 恆下標無上標；② 恆上標＋三下標；③ retired；④ 已刪除；⑤ 本表改採上標 \(q\)（C-03） | ①②active ③④retired ⑤不採用 |
| \(R\) | ① throughput \(R_{u,s,v}\) ② 速率目標 \(R^{\star}\) ③ 每波束最大吞吐量 \(R^{+}\) ④ 地球半徑 \(R_E\) ⑤ 波束覆蓋半徑 \(R_b\) ⑥ 萊斯功率衰落 \(R\) ⑦ 接收端上標 \(G^{R}\)、\(K_R\) ⑧ legacy \(R^{m}\)、\(R_u(t)\)、\(\widetilde R_{s,v}\) | ①三下標；②③上標；④⑤名稱下標；⑥**無上下標且只在衰落乘積式**；⑦上標／下標位；⑧ retired | ①②③④⑤⑥⑦active ⑧retired |
| \(\gamma\)／\(\Gamma\) | ① 實際 SINR \(\gamma_{u,s,v}\) ② 預測 SINR \(\gamma^{q}\) ③ 模式所需 SINR \(\gamma_m\) ④ 可解碼門檻 \(\gamma^{-}\) ⑤ 固定目標 \(\gamma^{\star}\)（僅 a-γ） ⑥ 所需 SINR 函數 \(\Gamma_r(\cdot)\) ⑦ retired \(\gamma^{r},\gamma^{e},\widehat\gamma,\gamma_u\) | ①三下標；②上標 \(q\)；③模式下標；④⑤單一符號上標；⑥大寫＋引數；⑦已刪除 | ①–⑥active ⑦retired |
| \(K\)／\(k\)／\(\mathcal K\) | ① 變動使用者集合 \(\mathcal K\) 與其大小 \(K\) ② 萊斯因子 \(K_R\) ③ 目標網路同步週期 \(K\) ④ 積分邊界索引 \(k\) ⑤ 波茲曼常數 \(k_B\) ⑥ matched-horizon offset \(k\) ⑦ 頻率重用 \(K_{FR}\) | ①花體／正體大寫；②⑦名稱下標；③ retired；④小寫無下標；⑤下標 \(B\)；⑥ retired | ①④⑤active ②⑦legacy ③⑥retired |
| \(X\)／\(x\)／\(\mathcal X\) | ① 連線指示量 \(x_{u,s,v}\) ② dB 域高斯遮蔽 \(X\) ③ 候選組態目錄 \(\mathcal X(t)\) 與其大小 \(\mathrm X\) ④ profile 標籤 \(x^{0},x^{1},x^{2},x^{c}\) | ①斜體小寫三下標；②正體大寫無下標；③花體；④ retired | ①②③active ④retired |
| \(E\)／\(\mathcal E\) | ① 組態能量 \(E(a)\) ② 訓練回合數 \(E\) ③ 評估窗能量 \(\mathcal E\) ④ 事件能量 \(E_{tr},E_{ho}\) | ①帶組態引數；②第五章舊設定（已知 stale）；③花體 retired；④ §10.51 | ①active ②stale ③retired ④legacy |
| \(B\)／\(\mathcal B\) | ① 組態位元 \(B(a)\)、\(B_u(x)\) ② 頻寬 \(B^{w},B^{g},B_{\mathrm{beam}}\) ③ 批次大小 \(B\)、\(B_I\) ④ 接收型樣參數 \(B_R\) ⑤ delivered bits \(\mathcal B\) | ①帶引數；②上標／下標；③④ retired／legacy；⑤花體 retired | ①②active ③④⑤retired |
| \(N\) | ① 系統總功率上標 \(P^{N}\) ② 雜訊指數 \(N_f\) ③ 啟用波束數 \(N^{a}_s\) ④ 需求向量 \(N_u(t-1)\) ⑤ 已刪除的 \(N(t)\) ⑥ 密封宣告的雜訊 \(N\)／\(N_0W\)、候選刷新週期 \(N=4\) | ①上標；②③④下標；⑤已刪；⑥ **本表不採**，見第 5 節 G-02、G-08 | ①②③④active ⑤⑥不採用 |
| \(\eta\) | ① 鏈路 EE \(\eta_{u,s,v}\) ② 網路 EE \(\eta^{N}\) ③ 鯰魚競爭權重 \(\eta_w\) ④ PA 效率 \(\eta^{PA},\eta_0\) ⑤ 引擎的 \(\eta_{\mathrm{ref}}\) | ①三下標（V0.25 退出）；②上標 \(N\)；③④ retired／legacy；⑤ 紙面寫 \(\lambda\) | ②active ①V0.23 active ③④retired ⑤引擎名 |
| \(\lambda\) | ① 凍結 bits-per-joule 乘子 ② 波長（第 3.1.2 節 \(D=1.0275\lambda/\theta_3\)） ③ 已刪除的容量懲罰 \(\lambda\) | ①無下標、只在剩餘式；②只在口徑式 —— **弱區分，見 C-06**；③已刪 | ①active ②正文一次 ③已刪 |
| \(\xi\) | ① 逐波束轉換效率 \(\xi_{s,v}\) ② 飽和效率 \(\xi^{+}\)（V0.25 更名） | 下標 vs 上標 | active |
| \(c\) | ① 候選索引 \(c\in\mathcal C\) ② 顏色 \(c_{s,v}\) ③ 光速 \(c_0\) ④ 尺度常數 \(c_j\) ⑤ profile 上標 \(x^{c}\) ⑥ action-context \(c_{ia}\) ⑦ 電路功率上標 \(P^{c}\) | ①無下標；②雙下標；③④名稱／目標下標；⑤⑥ retired；⑦上標 | ①②⑦active ③④legacy ⑤⑥retired |
| \(s\) | ① 衛星索引 ② 使用者狀態 \(s_u(t)\) ③ 飽和功率上標 \(p^{s}\) ④ 遮蔽損耗 \(L_s\) | ①裸 \(s\)；②帶使用者下標；③上標；④名稱下標 | active |
| \(i\) | ① 一般使用者索引 ② LC-SRS 兩人成員 \(i\in\{1,2\}\) ③ V0.25 聯盟成員 \(i\in\mathcal K\) ④ 同衛星干擾上標 \(I^{i}\) | ①③ 由 \(\mathcal U\)／\(\mathcal K\) 宣告；② retired；④上標 | ①③active ②retired ④active |
| \(a\) | ① 動作 \(a_u(t),a_{u,c}(t)\) ② 組態上標族 \(a^{0},a^{1},a^{d},a^{\psi},a^{\star}\) ③ 啟用波束數上標 \(N^{a}_s\) ④ 動作集合 \(A_u(t),\mathcal A^{+}_u(t)\) | ①恆下標；②恆上標且無使用者下標；③上標於 \(N\)；④大寫／花體 | active |
| \(o\) | ① 實現解碼結果上標 \(m^{o}\) ② 輸出回退 \(b_o\) ③ retired \(D^{o}\)、\(P^{o}\) | ①上標；②下標；③ retired | ①②active ③retired |
| \(W\) | ① retired 視窗長度 ② 密封宣告的頻寬 \(W\) | 本表頻寬恆為 \(B^{w}\)，\(W\) 不採用（C-04） | 不採用 |
| \(\mathcal M\) | ① ACM 模式集合 ② 契約 §A2 的名目物理模型 | ② 本表不給符號、以文字敘述（C-07） | ①active ②不採用 |
| \(\mathcal C\) | ① 候選動作索引域（本表） ② 契約 §A2 的候選組態目錄 | ② 改用 \(\mathcal X(t)\)（C-08） | ①active ②改名 |
| \(\nu\) | ① 頻譜效率 \(\nu_m\) ② V0.3 loss dispersion \(\nu_j\) ③ 字形近似波束索引 \(v\) | ①模式下標；② retired；③ **殘餘風險，備用字形 \(\varepsilon_m\)** | ①active ②retired |
| \(\delta\)／\(\Delta\) | ① 服務波束索引 \(\delta_u(t)\) ② 宣稱邊際 \(\delta=+0.5\%\) ③ 規劃替代 \(\Delta^{\star}=+2\%\) ④ 決策區間 \(\Delta t\) ⑤ 深層校準 \(\delta\)（§10.51） | ①帶使用者下標；②無下標；③大寫＋星號；④帶 \(t\)；⑤ legacy | ①②③④active ⑤legacy |
| \(b\) | ① 候選映射 \(b_u(c,t)\) ② 前次承諾關聯 \(b^{-}(t)\) ③ 輸出回退 \(b_o\) ④ 基頻功率上標 \(P^{b}\) ⑤ 波束覆蓋半徑 \(R_b\) | ①使用者下標＋引數；②上標 \(-\)；③④⑤名稱下標／上標 | active |
| \(H\) | ① 鏈路功率因子 \(H_{u,s,v}\) ② 回合長度 \(H\) ③ matched horizon \(H^{c}\) ④ 中斷處置代號 `H` | ①三下標；②裸字母；③上標 \(c\)；④ **token 而非符號** | ①②active ③retired ④token |
| \(U\) | ① 使用者集合大小 \(U\) ② 波束載量 \(U_{s,v}(t)\) ③ 診斷設定代號 `U-cap`／`U-margin`、比較臂 `U_all` | ①裸大寫；②雙下標；③ **token 而非符號** | ①②active ③token |
| \(S\)／\(J\) | ① 衛星數 \(S\)、波束候選數 \(J_w\)、Bessel \(J_1,J_3\) ② 選擇器 token `S0`、`S3`、`S_UNI`、`J1` | ② **token 而非符號**，不得作上下標 | active／token |

## 3. 單字母符號總表與消歧規則

「位置」欄說明該字母的**唯一合法出現位置**；違反位置即為記法錯誤。

| 字母 | active 意義 | 位置規則 |
|---|---|---|
| \(u,s,v\) | 使用者、衛星、波束索引 | 恆為下標；\(\mathbf v\) 粗體時是方向向量 |
| \(t\) | 時間步 | 函數引數，不是實體下標 |
| \(c\) | 候選索引／顏色／電路 | \(c\in\mathcal C\) 裸用；\(c_{s,v}\) 顏色；\(P^{c}\) 上標 |
| \(i\) | 聯盟成員／使用者 | 由 \(\mathcal K\) 或 \(\mathcal U\) 宣告；\(I^{i}\) 上標為同衛星干擾 |
| \(a\) | 動作／組態 | 下標＝逐使用者動作；上標＝組態角色 |
| \(d\) | 斜距／單邊增量 | 三下標＝斜距；單成員下標＋引數＝增量 |
| \(m\) | 遮罩／ACM 模式 | 下標＝遮罩；上標＋三下標＝模式 |
| \(q\) | 座標／分位／視圖 | 雙下標＝座標；上標＝分位或視圖 |
| \(k\) | 積分邊界索引 | 裸小寫；\(k_B\) 為波茲曼常數 |
| \(o\) | 實現結果 | 只作 \(m^{o}\) 的上標 |
| \(r\) | 速率目標 | 只作 \(m^{r}\)、\(\Gamma_r\) 的標記 |
| \(f\) | 共享 scorer／載波頻率 | \(f(\cdot,\cdot)\) 帶引數；\(f_c\) 帶下標；\(\Psi^{f}\) 上標 |
| \(p\)／\(P\) | RF 功率／電源端功率 | 小寫＝RF；大寫＋上標＝消耗階段 |
| \(B\)／\(E\) | 位元／能量 | 恆帶組態引數，否則是頻寬／回合數 |
| \(D\) | 可加單邊價值總和 | 恆帶組態引數 |
| \(F\) | 天線型樣 | 恆帶 \((\theta,\theta_3)\) 兩引數 |
| \(G\) | 增益 | 恆帶上標 \(T\)／\(R\) 或下標 \(0\) |
| \(H\) | 鏈路功率因子 | 三下標；裸 \(H\) 為回合長度 |
| \(I\) | 干擾 | 三下標；上標 \(i\)／\(x\) 區分同星／跨星 |
| \(L\) | 損耗 | 三下標＝總損耗；名稱下標＝分量；\(L_w\) 為視窗 |
| \(N\) | 網路總計／雜訊指數／啟用數 | 上標＝網路總；下標＝名稱 |
| \(Q\) | Q surface | 恆帶數字下標 \(1,2,3\) |
| \(R\) | 速率族＋萊斯衰落 | 見第 2 節第 ⑥ 義的位置限制 |
| \(U\)／\(S\)／\(V\)／\(C\)／\(K\)／\(\mathrm X\)／\(\mathrm M\) | 集合大小 | 正體大寫，與同字母花體集合配對 |
| \(x\)／\(z\) | 連線指示／波束啟用 | 三下標／雙下標 |
| \(\alpha\) | 仰角／分位水準 | 下標＝仰角；上標＝分位 |
| \(\gamma\)／\(\Gamma\) | SINR／所需 SINR | 見第 2 節 |
| \(\delta\) | 服務波束索引／宣稱邊際 | 帶下標／無下標 |
| \(\eta\) | EE | \(\eta^{N}\) 為唯一 V0.25 宣稱量 |
| \(\theta\) | 角度 | \(\theta_3\) 為波束寬；\(\theta^{R}\) 為接收端 |
| \(\kappa\)／\(\lambda\) | 輸出尺度／bits-per-joule 乘子 | 皆無下標，只出現在剩餘與正規化式 |
| \(\mu\)／\(\nu\) | Bessel 角度參數／頻譜效率 | \(\mu(\theta,\theta_3)\) 帶引數；\(\nu_m\) 帶模式下標 |
| \(\xi\) | PA 效率 | \(\xi_{s,v}\) 逐波束；\(\xi^{+}\) 飽和值 |
| \(\sigma^{2}\) | 雜訊功率 | 系統標量 |
| \(\tau\) | 段起始時間步 | 三下標；V0.25 退出 active |
| \(\varphi\) | 換手價格 | 恆帶數字下標 1／2 |
| \(\Phi\) | 換手／QoS 計價 | 帶使用者下標或組態引數 |
| \(\Psi\) | 交互作用殘差 | **恆帶花體集合下標** |
| \(\Omega\) | 組態層剩餘 | **恆帶組態引數** |
| \(\Upsilon\) | 淨避碰值 | 無下標或帶 \((t)\) |

## 4. 衝突登記（依權威順序採用，未靜默取捨）

| 編號 | 衝突內容 | 來源 A | 來源 B | 本表採用 | 依據與備註 |
|---|---|---|---|---|---|
| C-01 | \(\Phi\) 是否在分數 \(F\) 之內 | 契約 v1 §B4 與探針分裂修訂 1：\(F=B-\eta_{\mathrm{ref}}E-\Phi\) | v1.5 §2：\(F=B-\eta_{\mathrm{ref}}E\)，且 C1 另寫 (+\(\Phi\))；探針鄰域裁決另有 \(G\)（加訊令計價後的協調器目標） | 紙面一律 \(\Omega(a)=B(a)-\lambda E(a)-\Phi(a)\)，\(\Phi\) 只計一次 | **未由單一文件解決**：兩份密封宣告字面互斥。\(\Omega\) 的定義取自權威順序 ③（`SYMBOL-ADDITIONS` A-2），\(F\)／\(G\) 保留為引擎別名。⚠ 待使用者或後續密封宣告確認 \(G\) 的精確定義（本表無法取得探針原始碼，伺服器停機） |
| C-02 | 宣告衰落乘積的字形 | v1.9 §3 在散文中寫 \(G=R\cdot 10^{-(X+L_c(e))/10}\) | R-2（權威順序 ③）裁定「\(G\) 加單字母上標＝增益」為既有讀法，\(G\) 不得再承載剩餘類語意 | 不採 \(G\)；以乘積式直書，並登記 \(R\)、\(X\) 兩個原子字母 | 權威順序 ③ 高於 ④。若正文必須給乘積一個字母，需新裁決 |
| C-03 | 選擇時視圖的上標 | v1.7 §2 用上標 \(m\)：\(d_i^{m}\)、\(\Psi_A^{m}\)、\(F_m\) | `SYMBOL-ADDITIONS` A-1／A-2 用上標 \(q\)：\(d^{q}_i\)、\(\Psi^{q}_{\mathcal K}\)、\(\Omega^{q}\) | 上標 \(q\) | 權威順序 ③；且上標 \(m\) 會與 ACM 模式 \(m\) 直接相撞 |
| C-04 | 單一波束頻寬字形 | 密封宣告一律用 \(W\)（\(N_0W\)、\(W\nu_m/n_b\)） | V0.23 權威表用 \(B^{w}\) | \(B^{w}\) | 權威順序 ①；\(W\) 在本表另有 retired 的視窗語意 |
| C-05 | \(\Phi_u\) 同字母同下標 | R-1 指定 \(\Phi_u(t)\)＝換手／QoS 計價 | §10.12.3（V0.3 retired）已有 \(\Phi_u(t,a)\)＝部署分數 | 採 R-1；區分靠第二引數 \(a\) 與 retired 標記 | **新發現**：`SYMBOL-ADDITIONS` 的碰撞檢查未列此項。區分偏弱，建議正文永不同頁出現 |
| C-06 | \(\lambda\) 同字母 | \(\lambda\)＝凍結 bits-per-joule 乘子（§10.13.1、A-2） | 第 3.1.2 節天線口徑 \(D=1.0275\lambda/\theta_3\) 的 \(\lambda\)＝波長 | 兩者並存，靠所在式子區分 | **新發現**：與 \(D\)／\(D(a)\) 的處置（改寫為 \(D_a\) 或文字）應一併裁決，建議口徑式整句改為文字敘述 |
| C-07 | 花體 M 兩義 | 契約 §A2 的名目物理模型 \(\mathcal M\) | A-6 的 ACM 模式集合 \(\mathcal M\) | 保留 ACM 模式集合；名目模型不給符號 | 權威順序 ③；名目模型在正文以文字敘述 |
| C-08 | 花體 C 兩義 | 契約 §A2 的候選組態目錄 \(\mathcal C\) | V0.23 表的候選動作索引域 \(\mathcal C\) | 目錄改用 \(\mathcal X(t)\) | 權威順序 ①＋③（`SYMBOL-ADDITIONS` §2 已備妥 \(\mathcal X\)） |
| C-09 | 變動使用者集合字形 | 密封宣告用 \(A\)（\(\Psi_A\)、\(a_A\)、\(a^{0}_{-A}\)） | A-4 用花體 \(\mathcal K\)，大小為 \(K\) | 花體 \(\mathcal K\) | 權威順序 ③；且裸 \(A\) 與動作集合 \(A_u(t)\) 相撞 |
| C-10 | 認證單邊最適的上標 | v1.6 §3 與探針用 `u`：\(d_i^{u}\)、\(\Psi_A^{u}\) | A-7 用 \(a^{1}\)，重錨量 \(d^{1}_i\)、\(\Psi^{1}_{\mathcal K}\) | 上標 \(1\) | 權威順序 ③；`u` 與使用者索引 \(u\) 直接相撞，故不可作紙面上標 |
| C-11 | 可加／交互作用組態的字形 | v1.6 §3 用 `a_D`、`a_C` | A-5 備註用 \(a^{d}\)、\(a^{\psi}\) | \(a^{d}\)、\(a^{\psi}\) | 權威順序 ③；下標 \(D\)／\(C\) 會與 \(D(a)\) 與候選數 \(C\) 相撞 |
| C-12 | 淨避碰值的字形 | v1.6 §3 用 `V_CA` | A-5 用 \(\Upsilon\) | \(\Upsilon\) | 權威順序 ②（多字母下標禁用）＋③ |
| C-13 | 段記憶符號的狀態 | 權威順序 ①：\(\tau_{u,s,v}\)、\(p^{0}\)、\(\eta_{u,s,v}\) 是 active | 權威順序 ③④：V0.25 為 memoryless，三者退出 active surface | 原列不改寫，另立 §9.1 記錄狀態變更 | **權威順序內部張力**：規則「來源 ① 的既有列勝出」與 V0.25 物理事實衝突。本表以「保留定義＋標記狀態」處理，⚠ 待使用者確認是否要在 V0.25 論文版本中正式移除 |
| C-14 | \(\xi^{+}\) 的語意名稱 | 權威順序 ①：「最大轉換效率」 | v1.8 §1：\(\eta_{\max}\) 是**飽和**效率，1.65 W 實際效率約 19.7 % | 字形不變，語意更名為飽和效率 | 權威順序 ④ 只更名不改值；\(P^{p}=\sqrt{p\,p^{s}}/\xi^{+}\) 與 `PA_supply` 數學上完全等價，故無數值衝突 |
| C-15 | ACM 模式表的大小 | 圖 1 計算稿 `figure1_compute.py` 的 `ACM_TABLE`：11 個模式、全 QPSK、\(\nu_{\max}=1.4905\) | 優先序宣告與 stage-4h 引擎：28 個模式、\(\nu_{\mathrm M}=3.7109\)、每波束 12 位使用者可達 50 Mbit/s | 28 模式的密封表 | 由 2026-09-09 落地的 controller finding 認定「宣告為準」；圖 1 須以密封表與密封保留量重算。合併表已於 \(\mathcal M\) 列標註 |

## 5. 出現在密封宣告、但未進入合併表的量（**本節最重要**）

| 編號 | 量 | 出處 | 未進表的理由 | 是否為待裁決缺口 |
|---|---|---|---|---|
| G-01 | **C2 的延續值本身** | 契約 v1 §B4「C2 = declared continuation value」；v1.9 §5 | 密封宣告只以文字定義，未固定字形；本表在 §10.14.4 的次鍵欄以文字「C2 延續值」表示。所有未使用的希臘大寫都會與在用的小寫形成大小寫異義對（\(\Xi/\xi\)、\(\Lambda/\lambda\)），無安全字母可用 | **是** —— 第四章寫到三路分數式時必須有字形 |
| G-02 | **候選刷新週期 \(N=4\)** | v1.2 §7（明定為 candidate-refresh period，不是 dwell） | 裸 \(N\) 與 \(P^{N}\) 的網路總標記、\(N_f\)、\(N^{a}_s\)、\(N_u\) 相撞 | **是** —— 第五章設定表需要 |
| G-03 | **standby 比例 \(f=1/12\) 與 \(P_{\text{idle}}\)** | v1.0 處置 S；v1.2 §7 | \(f\) 已是共享 scorer 與載波頻率下標；\(P_{\text{idle}}\) 是多字母下標 | **是**（若 S 處置進入 CH5 圖表） |
| G-04 | **跨波束交互增益（pairwise cross-gain）** | 契約 v1.2 §2（明文要求不可只給純量干擾摘要） | 本表的干擾展開以 \(I^{i},I^{x}\) 與 \(G^T\) 於干擾角度的取值隱含表示，未給成對交互增益字形 | **是** —— 若第四章明寫 C3 編碼器輸入 |
| G-05 | 中斷處置的 62／142 ms 有效時間 | v1.0 §處置 H | \(H\) 已三義；處置以 token `H` 表示，時間常數以數值敘述 | 否 |
| G-06 | C2 預測 offset 索引（\(\{1,2,3\}\)） | 契約 v1 §B4；應變階梯 rung 3 | 小寫 \(k\) 已作步內積分邊界索引；V0.3 的 offset \(k\) 屬 retired | 否（正文以文字「第 1／2／3 個 offset」） |
| G-07 | 校準聚合量 \(B_{\text{ref}},E_{\text{ref}},N_{\text{ref}}\) | 探針分裂修訂 1（\(\eta_{\text{ref}}=B_{\text{ref}}/E_{\text{ref}}\)、\(\kappa=B_{\text{ref}}/(U\cdot N_{\text{ref}})\)） | 多字母下標，權威順序 ② 明文禁止 | 否（識別式以文字敘述） |
| G-08 | \(N_0\)（雜訊功率譜密度） | v1.1 §1 的 \(p_u\) 式 | 本表以 \(\sigma^{2}=k_BTB^{w}\) 表示同一量 | 否 |
| G-09 | FDM 架構（a′）的子頻帶頻寬與每使用者子上限 \(p^{+}/n_b\) | v1.1 §3 | a′ 是敏感度架構，非主格；其專屬字形留待該格報告時再定 | 否 |
| G-10 | 遺漏共同能量 \(E_0\) | v1.8 §4 的邊界不可轉移論證 | 只出現在一次限制論證中；\(E_0\) 會被讀成「offset 0 的能量」 | 否（以文字敘述） |
| G-11 | 宣稱階梯 Level A／B／C | 應變階梯 rung 0 | 宣稱層級標籤，非符號 | 否 |
| G-12 | 比較臂上限 `U_all`、`J1`、`U1` | v1.6 §4；4c gate | 引擎臂名；裸 \(U\) 已是使用者數 | 否（已在 §10.14.5 以 token 登記其類別） |
| G-13 | 開發切片診斷 \(\Sigma g_I\)、\(\Delta I_N\)、\(\Delta c_h^{N}\) | v1.6 §2、§3 | 開發期診斷量，已由 \(\Upsilon\) 的兩個分量與預測／實現落差報告取代 | 否 |
| G-14 | 學習器輸入脈絡 \(Z_t\)、\(I_{\text{heads}}\)、\(I_{\text{coordinator}}\) | 契約 v1 §A1／A2、§C2 | 多字母下標；且 \(I\) 已是干擾 | 否（以文字敘述資訊介面） |
| G-15 | 統計面板常數（16 個 learner seed、約 160 個 claim date、6 臂 × 2 世界、覆蓋率） | 契約 v1.1 §1、v1 §D1 | 面板設定值，非符號 | 否 |
| G-16 | 協調器 10 s 計算預算 | 契約 v1 §F2 | 作業層預算，非公式量 | 否 |

**摘要：** 16 個未進表的量中，12 個是刻意不給字形（token、面板常數、引擎欄位、
多字母名稱），4 個（G-01–G-04）是**真缺口**，在第四／五章寫作前必須裁決字形。

## 6. 本輪未觸及的範圍

- 第 3、5 章的既有物理公式未被本次合併改寫；V0.23 論文版本仍以權威順序 ① 為準。
- 第五章的舊實驗設定（\(E\)、\(K\)、\(c_j\) 等）維持已知 stale provenance 標記。
- 伺服器停機，`probe_interaction_existence.py` 原始碼無法取得，故 C-01 中 \(G\) 的
  精確定義只能由密封宣告的散文推得，本表已明白標示其不確定性。
