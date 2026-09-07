# 結果數據圖計畫表 — x/y 軸慣例調查 + 重訓 vs 本地 eval 排程

> **★ 2026-07-03 更新指標**:本計畫表提到的結果圖,其 **Origin 投稿版** 現集中在單一 warehouse
> `scratch/final_figures/paper-figures/`(31 張 native `_origin` PNG+SVG+`.opju`,5 project;目錄
> `paper-figures/PAPER-FIGURE-CATALOG.md`)。matplotlib 版(論文現用圖)**保留原地**(USER 決定,兩組並存)。
> 「哪組為最終」= R3,仍屬另一條 thesis 對話,本計畫表結論不變。清理記錄 → `paper-figures/CLEANUP-REPORT.md`。

> 產出日期 2026-06-29。**只讀調查 + 規劃**;本文件未跑任何訓練、未畫任何圖。
> 用途 = Track-1（圖表調查）交付物,供 USER 排程決定哪些圖上 server 重訓、哪些本地 eval 即可。
> 真相源 = `CURRENT-STATE.md` 頂端「★★ LIVE LINE」+「NEXT」。本文件不重述其結論,只引用。

## 0. Frame / RED LINES(綁定,所有圖的誠實邊界)

- 敘事 = **整合式 Multi-Catfish(MCCRL）框架贏**;catfish = 具名核心組件,**非**已證實的 win 主因;de-collapse 引擎 = 協調式波束分配(coordinated allocation/decode）。
- **r1 = angle-aware EE（binding)**。
- **RED LINE (c)**：贏在 **公平/覆蓋（min_cov ≈1.0）+ EE 軸**,**不**在加權純量 J_w —— 在 J_w 上一個更簡單的 `DQN_scalar`（6.41e-4 banked）壓過我們的 A1（4.97e-4)。任何「ours-on-top」CDRL-style 圖,**只有 EE 軸與 coverage 軸是誠實的**;J_w / throughput 軸必須照實畫(DQN_scalar / DQN_throughput 不可裁掉)。
- ROOT-Q（collapse = env/state/algorithm?）未解,不得在圖說呈現為已解。
- 死線勿碰:family_b env-grind、route-C/P4 distillation、r1=throughput。

---

## Part A — 相關論文「結果圖 x/y 軸」慣例(調查綜整)

調查範圍:`paper-catalog/txt_layout_all/` ~37 篇(throughput / EE / 多目標 / LEO handover / beam management),以 5 個平行 agent 抽出每張**結果圖**的 x 軸、y 軸、方法線數、圖型,並標記 ★ = CDRL-style（單調掃描系統參數 × 多方法線)。系統模型/架構/流程圖一律略過。

### A.1 主結論(領域慣用 idiom)

1. **單調 line-sweep × 多方法線(★）是領域的主流結果圖型**:被調查的 ~30 篇有實驗的論文中,超過 2/3 至少有一張 ★ 圖。`cdrl.png`(本所 CDRL 碩論,PAP-2025-CDRL-CATFISH)就是最密的版本(8 條線 × 4 子圖)。
2. **x 軸 = 系統規模 / 資源預算 / 負載 三大族**:
   - **系統規模**:#users / #UEs / #agents / #MTs / #aircraft;#satellites / constellation scale。←最常見
   - **資源預算/容量**:#channels（Cmax)、#RBs、#preambles、#subchannels、**#antennas**、Tx-power / EIRP、RIS-location、beam-overlap%、time-frame Tf。
   - **負載/流量**:user-density λ、packet-arrival-rate λ、**traffic-demand 強度**、satellite-load、min-rate-req Rmin。
   - 其他:terminal/satellite speed、shadowing prob、hysteresis margin、deviation angle θ、orbital altitude。
3. **y 軸 = 一個純量/加權目標 + 各目標分解**:throughput / sum-rate（Mbps、bps/Hz)、**energy efficiency（bit/J、bit/Hz/J)**、handover count/rate/delay、blocking / outage / access-failure、reward（cumulative / weighted)、coverage / QoS-ratio / network-utility、**Jain fairness**、delay。
4. **DRL 論文常見第二類圖** = vs-episode/step 訓練收斂曲線(非系統參數掃描);部分論文(QMIX-BH、Cai)主比較放在 **CDF** 或**表格**而非 ★ 圖。

### A.2 對本論文最關鍵的兩個模板

**(模板一)本論文 base paper = Sun2024 MODQN(PAP-2024-MORL-MULTIBEAM)**
- 掃描 x:**# users、# satellites、user speed、satellite speed**(各一張)。
- 每張 = (a) 3D-surface 三目標細節 + (b) **2D line-sweep 加權 reward**(★)。
- 方法線 = **MODQN、RSS_max、DQN_throughput、DQN_scalar**(4 條)。
- **★ 重大對應**:Sun2024 的 benchmark 集 `{RSS_max, DQN_throughput, DQN_scalar}` **與我們的 weak-static 集完全相同** → 我們的方法線選擇有 base-paper 直接背書。
- **★ 注意(誠實缺口)**:base paper 掃 **user speed / satellite speed**,但我們 GATE-0 判定 `user_speed_kmh` metric-inert(10-step episode 凍結)、`constellation_speed_km_s` blocked(fixed_defaults)→ **這兩條 base-paper 軸我們無法忠實重現**,需在論文揭露,不可硬湊。

**(模板二)`cdrl.png`(PAP-2025-CDRL-CATFISH,本所同 lab catfish 概念源)**
- 4 子圖,x = **{max transmit power 10-20 dBm, # users 2-10, RIS location 50-100, # Tx antennas 8-15}**。
- y = **energy efficiency（bit/Hz/J)**(另有 sum-rate / SE 版本,共重複 4 次:active/passive × EE/sum-rate = Fig 5.1/5.3/5.4/5.6)。
- 方法線 = **8 條** = 4 方法 {CDRL, Actor-Critic, BPOF, Teacher-Student} × {可調開關, 全開}。proposed(CDRL)永遠在最上面。
- Fig 5.7 = **消融 line-sweep**(full CDRL + 6 個 −/only 變體,x = power),這是我們做消融線圖時的直接範本。

### A.3 ★ CDRL-style 圖目錄(可借鏡的 x/y 組合,跨論文)

| 論文 (id) | ★ 圖的 x 軸 | y 軸 | 線數 |
|---|---|---|---|
| Sun2024 base | #users / #sats / user-speed / sat-speed | weighted reward | 4 |
| CDRL (`cdrl.png`) | Tx-power / #users / RIS-loc / #antennas | EE (bit/Hz/J), sum-rate | 8 |
| HOBS (EE-joint, SINR 源) | time-frame Tf / user-density λ | **EE (bit/J)**, throughput, delay | 3–6 |
| Tervo 2017 (EE beam coord) | **#TX antennas** / P_RD / #pilots | network EE / WsumEE | 6–7 |
| Bian 2022 (reliable EE) | outage-prob / rate R / #rounds L / Rician K | **EE (bits/J)** | 2–4 |
| Guo 2022 (sensors BH) | **traffic arrival intensity** | throughput / delay / access-rate / **delay-variance(fairness)** | 4 |
| SDQL 2022 | **#channels Cmax (10-50)** | reward / **throughput** / forced-term | 6 |
| DHO 2023 | #RBs / #preambles per UE | access-delay / collision | 3 |
| Mega-MA-SHDQL 2024 | user-area / **min-rate Rmin** / **#sats** / **#users** | reward / rate / cost / HO-delay | 5 |
| MAF-DDQN 2024 | **#MTs (10-50)** / arrival-rate λ | reward / revenue / #HO / loss | 7 |
| Nash-SAC 2024 | **available channels (7-11)** | blocking rate | 6 |
| QoE-driven 2020 | **terminal speed** / **satellite load** | HO times / HO-failure / delay | 6 |
| Fast-moving 2025 | **#agents** | throughput / hop / #HO / **Jain fairness** | 4 |
| Net-Flows 2021 | **#UTs M** (ample vs scarce BW) | switching gain / QoE | 6 |
| PHSU 2024 (sat-aircraft) | **satellite load / constellation scale / #subchannels** | rate / utility / HO-freq / HO-delay | 3 |
| MC-CHO 2024 | **beam overlap %** | #HO/s / RLF/s / capacity | 2–4 |
| RSMA soft-HO 2025 | deviation angle θ | MMR / WSR (bps/Hz) | 3–4 |

> 完整逐篇逐圖表 = 本文件 Appendix(Part G)。讀法判讀如需第三方核對,可選用 codex cross-check(本任務未跑,屬選配)。

### A.4 我們可直接借的設計招式

- **k_cap = 容量掃描** → 與 SDQL「#channels Cmax」、PHSU「#subchannels」、DHO「#RBs」同一族;**k_cap 並非孤兒軸,是領域標準的「per-beam/per-sat 容量」掃描**(強化故事正當性)。
- **U(num_users)= 領域第一常見軸**(base paper Fig3 + 十餘篇);有最強 precedent。
- **y=EE**:CDRL/HOBS/Tervo/Bian 直接背書 → 我們的誠實 ours-on-top 軸。
- **y=throughput**:base paper 的 r1 + 近乎全領域 → 我們有 `r1_throughput` 可畫(雖 r1 訓練目標=EE)。
- **y=Jain fairness / delay-variance**:Fast-moving 2025、Guo 2022 背書 → 直接支援我們的公平/覆蓋軸(RED LINE c 的正面表述)。
- **多子圖併排**(base/CDRL/Mega 都用 4 panel 一圖)= 我們把 {EE, min_cov, J_w, r2} 併成一張 2×2 的 precedent。

---

## Part B — 對映到我們的 env(可不可重現)

### B.1 可掃的 x 軸

| x 軸 | 狀態 | 重現性 | 備註 |
|---|---|---|---|
| **k_cap**(per-window capacity) | **已掃 13 點 {3..15}** | learned(B0/A2)13/13 已訓 | 我們的主軸;領域=容量掃描族 |
| **U(num_users)** | GATE-0 clean | learned 須**每點重訓**(現只訓 U=100) | **= base-paper Fig3「#users」軸**;但舊 `fig5_3_user_sweep` 曾因 coverage drop 被撤(須誠實重導) |
| **l_w(window length)** | GATE-0 clean | learned 須每點重訓 | **★ env 裡 `num_satellites()` 直接 `return l_w` → l_w sweep = base-paper Fig4「#satellites」軸**;同時改變 n_physical_beams(l_w × pointable cells),掃描時須說明此耦合 |
| ~~user_speed_kmh~~ | **metric-inert** | ✗ 不可 | 10-step episode 凍結;base-paper Fig5 有此軸但我們無法忠實重現 → 揭露 |
| ~~constellation_speed_km_s~~ | **blocked** | ✗ 不可 | fixed_defaults;base-paper Fig6 同上揭露 |

> **base-paper 4 軸對映**:#users→U ✅(heavy)、#satellites→l_w ✅(heavy)、user-speed ✗、sat-speed ✗ → **4 軸有 2 軸可重現**。base 的 y=weighted reward(J_w)→ ours **不在頂**(DQN_scalar 贏,RED LINE c)→ 不可照 base「ours 在頂」呈現,誠實版改 y=EE 或加 coverage 副圖。

### B.2 y 軸候選 + 誠實映射(nominal k=3 實測,決定哪條軸能畫「ours-on-top」)

| y 軸(欄位) | A2 | A1 | AF | DQN_thr | DQN_scalar | B0/RSS/RR | ours-on-top 誠實? |
|---|---|---|---|---|---|---|---|
| **EE(`r1`,η^EE)** @k=3 | 3.85e12 | **3.92e12** | 3.73e12 | 3.24e12 | (待掃) | 1.0–2.2e12 | **⚠ 只在低 k 誠實 ours-on-top** — 見下方 ★ 修正 |

> **★ 修正(2026-06-29 本地 eval 實證,authority CSV 確認,推翻舊「A2 leads EE all k」措辭)**:把 round_robin / AF 加進 EE 線圖(8-arm CDRL 計畫的本意)後發現 **A2 的 EE 領先只在低/緊容量(k≈3–7)成立**。A2 的 EE 隨 k 下降(3.85e12→0.97e12),round_robin EE 大致持平(~1.6–2.2e12)→ **k≥9 時 round_robin EE 反超 A2**;AF 在高 k 也高於 A2。但 round_robin 的高 EE 伴隨 **min_cov=0**(餓死尾用戶),與 DQN_scalar 在 J_w 上的 gaming 同理。**舊 fig5_4d 只畫 A2+消融(沒畫 round_robin)才看起來 all-k 領先**。→ **誠實 headline = 覆蓋面板(A2+AF≈1.0 vs 其餘≈0,clean 2-regime),NOT 純 EE 線**;EE 線須與 coverage 併讀。本地圖已產出:`scratch/final_figures/cdrl_style/cdrl_{mincov,ee,qos,jw,activebeams}_vs_k_cap.png` + `cdrl_combined_2x2_vs_k_cap.png` + `cdrl_kcap_sweep_raw.csv`(見該夾 `README.md`)。
| **min_coverage** | 0.999 | 0.999 | 1.000 | 0.041 | 0.0/0.11 | 0.0 | **✅ 誠實 + 戲劇性**(2-regime:ours+AF≈1 vs 其餘≈0) |
| **qos_served / served** | 0.97/1.0 | 0.99/1.0 | 0.95/1.0 | 0.63 | ~0.9 | 0.29–0.41 | **✅ 誠實**(ours/AF 領先) |
| **active beams(`eff_beams`)** | 9.4 | 10.6 | 3.6 | 7.0 | ~12.8 | 3.0/RR 11.7 | de-collapse **診斷**軸(3→9-12),非 win 軸 |
| **calib J_w** | 4.82e-4 | 4.97e-4 | 4.44e-4 | 3.80e-4 | **6.41e-4** | <2e-4 | **✗ 非 ours-on-top**(DQN_scalar 最高 → RED LINE c)。可畫但須含 DQN_scalar,且只在 k≲10 主張 CI-win |
| **throughput(`r1_throughput`)** | (待算) | (待算) | — | 高(其目標) | 高 | 低 | **✗ 預期 DQN_throughput 領先**(像 base paper 單準則贏自家軸)→ 照實畫 |
| handover `r2` / load `r3` | penalty(近 0 較好) | | | | | | 混合,非 win 軸 |

### B.3 八條方法線 × 掃描點的 ckpt 可得性(決定 A/B 分組的核心矩陣)

「8 條線 = CDRL 密度」目標集 = **B0 / A1 / A2 / AF / DQN_throughput / DQN_scalar / round_robin / RSS_max**。

| 方法線 | 類型 | 已訓 k 點 | k_cap 全 13 點可 eval-only? | 分組 |
|---|---|---|---|---|
| **B0**(Plain MODQN) | learned | 全 13 | ✅ 已在 sweep CSV | **(B) 已有** |
| **A2**(Proposed MCCRL) | learned | 全 13 | ✅ 已在 sweep CSV | **(B) 已有** |
| **round_robin** | rule | n/a | ✅ 已在 sweep CSV | **(B) 已有** |
| **RSS_max** | rule | n/a | ✅ 已在 sweep CSV | **(B) 已有** |
| **AF**(協調分配啟發式,0 學習) | rule | n/a | ✅ provider 已存在,只須加進 sweep | **(B) 待產生-便宜** |
| (A0 ~RSS-argmax,選配) | rule | n/a | ✅ provider 已存在 | (B) 待產生-便宜 |
| **A1**(Inference-only) | learned | **僅 {3,6,9,12,15}** | 5 錨點 eval-only;缺 8 點 | **(B@5 點)** / 全 13 須 (A) |
| (B1/B2 消融線,選配) | learned | 僅 {3,6,9,12,15} | 同 A1 | (B@5) / 全 13 須 (A) |
| **DQN_throughput** | learned | **僅 k=3**(5-seed) | nominal 才有;掃描須重訓 | **(A) 每點重訓** |
| **DQN_scalar** | learned | **無 ckpt(只有 banked 數)** | 完全須重訓(連 nominal ckpt 都缺) | **(A) 每點重訓-最重** |

> ckpt 來源:`../modqn-weights-consolidated/matched-kcap/kcap_<k>/<arm>/`(B0/A2 全 13;full factorial 僅 {6,9,12,15,18});`route-b/route-b-factorial-2026-06-27/`(nominal full);`artifacts/field-baselines/`(DQN_throughput 5-seed)。
> sweep 驅動 = `scratch/run_matched_kcap_sweep.py`(現 ALGORITHMS = B0/A2/2 消融/RR/RSS);providers = `route_b_factorial/eval_result.py`(`_provider_af/_a0/_rss_max/_round_robin`、`column_greedy_decode`)。DQN_scalar 訓練 harness = `field_baselines/shared_q_isolation.py`(ISO_S == DQN_scalar single-head)。

---

## Part C — 候選圖表(交付主體)

每列 = {圖, x, y, 方法線, claim, 分組, 資料狀態}。**(B)=本地 eval-only/已有,(A)=須 server 重訓。**

| # | 圖名 | x | y | 方法線 | claim(說明什麼) | 分組 | 資料狀態 |
|---|---|---|---|---|---|---|---|
| F1 | **EE vs k_cap**(CDRL-look 主圖) | k_cap 3-15 | EE(η^EE) | B0,A2,AF,RR,RSS(+A1@5) | **ours 在 EE 軸全程領先**(誠實 ours-on-top) | **(B)** | B0/A2/RR/RSS 已有;AF 待加-便宜;A1 僅 5 錨點 |
| F2 | **min_coverage vs k_cap** | k_cap 3-15 | min_cov | 同上(+DQN×2 nominal 點) | ours+AF≈1 保覆蓋;baselines 餓死尾用戶(2-regime) | **(B)** | 已有(同 CSV);DQN 點須 (A) |
| F3 | **qos_served vs k_cap** | k_cap 3-15 | qos_served | 同 F1 | 服務品質隨容量 | **(B)** | 已有 + AF 待加 |
| F4 | **active beams vs k_cap** | k_cap 3-15 | eff_beams | 同 F1 | de-collapse 診斷(3→9-12) | **(B)** | 已有 + AF 待加 |
| F5 | **J_w vs k_cap**(誠實版) | k_cap 3-15 | calib J_w | B0,A2,AF,RR,RSS,**DQN_scalar,DQN_throughput** | 低-k(k≲10)CI-win;高-k 收斂入雜訊;**含 DQN_scalar 不裁** | **混合** | learned/static 已有;**DQN×2 線須 (A)** |
| F6 | **效率-公平 Pareto**(EE×min_cov) | — | min_cov | 散點:各 arm 一點(nominal) | ours 同時高 EE + 全覆蓋;DQN_scalar 高 J_w 但餓死尾用戶 | **(B)** | 已有(route-b + field-dqn RESULT);≈擴充現 FIG-5.2 |
| F7 | (已存)nominal bars / Pareto J_w×min_cov | — | — | 8 arm | 既有 FIG-5.1 / FIG-5.2 | **(B) 完成** | 已產出 |
| F8 | **throughput vs k_cap**(誠實版) | k_cap 3-15 | r1_throughput | 含 DQN_throughput | DQN_throughput 領先自家軸(像 base paper);ours 兼顧多目標 | **混合** | **⚠ 現 sweep CSV 無 throughput 欄(只有 r1=EE)→ 須重跑一輪 eval 補 `r1_throughput`**(本地便宜,須改碼);DQN_throughput 領先線跨 k 須 (A) |
| **—— 以下全須 (A) server 重訓 ——** | | | | | | | |
| F9 | **EE / J_w / coverage vs k_cap**(全 8 線 CDRL-parity) | k_cap 3-15 | EE,J_w,min_cov | **全 8 線完整 13 點** | 補齊 A1 缺 8 點 + DQN×2 全掃 → 與 `cdrl.png` 同密度 | **(A)** | 待產生 |
| F10 | **U(num_users)sweep**(對應 base Fig3) | U {50,75,100,150,200} | EE,J_w,min_cov,throughput | B0,A2(+statics eval) | 規模擴展性;誠實重導 coverage(舊圖曾撤) | **(A)** | 待產生 |
| F11 | **l_w sweep** | l_w(數點) | EE,J_w,min_cov | B0,A2(+statics) | window 長度敏感度 | **(A)** | 待產生 |

> base-paper 風格的「(a)3D 三目標 + (b)2D 加權」雙子圖可選做:(a) 3D-surface(r1/r2/r3 vs 某 x)= 純 eval-only 重繪 (B);但 3D surface 在多方法時可讀性差,建議改用 2×2 line panel(F1+F2+F3+F5 併版),更符合近年慣例。

---

## Part D — 排程分組(交 USER 決定)

### (B) 本地 EVAL-ONLY(快、不重訓,建議先做)— 標籤:**non-heavy**

全部重用現有 ckpt(learned)+ 規則跑(statics),`threads=1`,本地即可,**零訓練**:

1. **擴充 `run_matched_kcap_sweep.py`**:`ALGORITHMS` 加入 `AF`(+ 選配 `A0`),eval-only 跑全 13 k。→ 補上 AF/A0 線。(providers 已存在,改一行 list + provider 分派)
2. **A1 線 @ 5 錨點 {3,6,9,12,15}**:載入既有 A1/B1 weights + auction decode,eval-only。
3. **重切成 CDRL-look 單-y 線圖**:F1(EE)、F2(min_cov)、F3(qos)、F4(active beams)、F5(J_w 誠實版)、F6(Pareto)。資料皆來自 `fig5_4_kcap_sweep_raw.csv` + nominal RESULT.json。
4. 估時:**< 30 分鐘本地**(AF/A0/A1@5 的 eval 各數十 episode;無訓練)。

> 這組 = **最小誠實交付集**,可立即得到 6 條線的 EE/coverage CDRL-look 主圖,**完全不需 server**。

### (A) SERVER 重訓(heavy,須 USER「go-server」硬閘)— 標籤:**heavy**

| 項目 | 內容 | 規模(runs) | 估計 wall(20-core,parallel ≤18,threads=1) |
|---|---|---|---|
| A1 全 13 點 | 補訓 plain(=B1)於缺 8 k × 3 seed | 24 | ~2 波 × 21 min ≈ **0.7–1.5 h** + eval |
| (選配 B1/B2 消融線全 13) | 同上,每多一條 +24 runs | +24/條 | 同量級 |
| DQN_throughput sweep | 13 k × 5 seed 重訓 | 65 | ~4 波 × ~17 min ≈ **~1.1 h** + merge |
| DQN_scalar sweep | 13 k × 5 seed 重訓(無 ckpt,須從零;harness=`shared_q_isolation.py` ISO_S) | 65 | **~1.1 h** + merge |
| U-sweep(F10) | 5 U × {B0,A2} × 3 seed(+statics eval) | 30 | **~0.6 h** + eval(8 線版更重) |
| l_w-sweep(F11) | 同 U-sweep 結構 | ~30 | **~0.6 h** |

> 單 run = 3000 episodes;server 校準 10.5 min/1500ep → ~21 min/run。以上採每點獨立 run 併發(USER policy:result-equivalent 最大併發,per-seed shard `threads=1`,≤cores−2)。
> **若全做(F9+F10+F11 完整 8 線)≈ 4–6 h wall**(視併發與是否含消融線)。
> **若只補「F9 的 DQN×2 兩線 @ k_cap」**(讓 J_w/EE 主圖達 CDRL 8 線密度)≈ **~2.2 h wall**。

---

## Part E — 各圖誠實註記(RED LINES 落地)

- **F1(EE)**:**⚠ 非 all-k ours-on-top**(見 Part B.2 ★ 修正):A2 只在 k≈3–7 EE 領先,高 k 被 round_robin/AF 反超(但 round_robin min_cov=0)。誠實畫法 = EE 線**必須與 coverage 併讀**,圖說標「A2 在緊容量領先 EE 且維持滿覆蓋;高容量時簡單法在 EE 追上但犧牲覆蓋」。不可單獨用 EE 線宣稱 ours-on-top。
- **F3 / F4(qos / active beams)**:qos A2/A1/AF 領先(誠實);active-beams = de-collapse 診斷(B0≈3 → ours/RR 展開),非 win 軸。
- **F2 / F6(coverage / Pareto)= 真正的誠實 headline**:clean 2-regime,A2+AF≈1.0 vs B0/RR/RSS≈0(RR 僅 k≥13 才爬升),且是 RED LINE c 的**正面**表述(贏在公平/覆蓋)。DQN_scalar 高 J_w 但 min_cov≈0 / round_robin 高 EE 但 min_cov=0 → 正是要呈現的 efficiency-equity trade-off:**A2 是唯一同時高 EE(緊容量)+ 滿覆蓋的 learned 法**。
- **F5 / F8(J_w / throughput)**:**不可**做成 ours-on-top。J_w 須含 DQN_scalar(它最高),win 只在 k≲10 CI-separated;高-k zigzag 入雜訊(見 `CH5-FIG-SMOOTHING-FIX-NOTE-2026-06-29.md`,line 圖一律畫 raw mean、CI 留在 CSV/表)。throughput 須含 DQN_throughput(它領先自家軸)。
- **F10(U-sweep)**:舊 `fig5_3_user_sweep` 曾因 raw coverage drop 與覆蓋主張衝突被撤 → 重做須誠實標示 coverage 隨 U 的真實走勢,不可挑點。
- **A1 線若用「B0 weights + auction decode」充當全 13 點**(替代重訓):可得全 13 點 eval-only,但**不等於 trained-A1**(A1 headline 4.97e-4 來自 factorial plain 訓練權重)→ 須在圖說標 caveat,或僅畫 5 錨點。建議:**主圖只畫 5 錨點 A1(誠實),全 13 點 A1 列為 (A) 重訓**。
- **user_speed / sat_speed**:base-paper 有、我們 inert/blocked → **不畫**(揭露一行說明),不可假造。

---

## Part F — 建議(最小 vs 完整)

- **最小誠實集(零訓練,先交)**:F1(EE-vs-k_cap,6 線)+ F2(min_cov)+ F6(效率-公平 Pareto)+ 既有 F7。→ 立刻有「ours 在 EE+coverage 軸全程領先」的 CDRL-look 主圖,**全本地 eval**。
- **CDRL-parity 完整集(須 go-server)**:+ F5/F8 補 DQN×2 兩線(≈2.2 h)→ 8 線達 `cdrl.png` 密度;再 + F10/F11(U / l_w sweep,對應 base-paper Fig3)。
- **排程建議**:先跑 (B) 組看主圖成形 → 若 USER 要 8 線 CDRL-parity / U-sweep 對齊 base paper,再開 (A) 組(優先 F5 的 DQN×2 @ k_cap,CP 值最高:直接補強最關鍵的 EE/J_w 主圖)。

---

## Part G — Appendix:逐篇逐圖明細(調查原始輸出,壓縮)

> ★ = CDRL-style 單調掃描 × 多方法線。系統模型/架構/流程圖已略。

### 核心(base / SINR / catfish / MO-DRL)
- **Sun2024 MODQN(base)**:Fig3/4/5/6 各 (a)3D 三目標 + (b)line-sweep 加權 reward;x={#users,#sats,user-speed,sat-speed};線=MODQN/RSS_max/DQN_throughput/DQN_scalar。★ on (b)。
- **HOBS(EE-joint,SINR 源)**:Fig5(a)throughput、(b)delay vs Tf ★;Fig6 EE(bit/J) vs Tf ★;Fig7(a)EE vs Tf、(b)EE vs user-density λ ★;Fig4 SINR vs time(series)。
- **CDRL(`cdrl.png`)**:Fig5.1/5.3 EE、5.4/5.6 sum-rate,各 4 子圖 x={Tx-power,#users,RIS-loc,#antennas},8 線 ★;Fig5.7 消融 vs power(7 線)★。
- **DBH/Hu2020(MO-DRL BH)**:Fig15 delay、Fig18 throughput vs **traffic-demand%** ★(5 線);其餘多為 vs-epoch 收斂 + 表格。

### EE / beam-hopping / beam-mgmt
- **Tervo2017(EE beam coord)**:Fig3/4 EE vs P_RD ★;Fig5 EE vs **#TX antennas** ★(6-7 線);Fig9 EE vs #pilots ★。
- **Bian2022(reliable EE)**:Fig6 EE vs outage-prob、Fig7 EE vs rate R、Fig9 EE vs #rounds L、Fig10 EE vs Rician K、Fig11 EE vs outage ★(2-4 線)。
- **QMIX-BH 2024**:主比較=CDF(Fig8/9 LTNT/LTAD)+表格;Fig6 LTNT/LTAD vs weight α(1 線)。少 ★。
- **Zhu2024(beam-mgmt + HO-freq)**:多為 vs-epoch time-series;Fig11 P0/queue/HO-freq vs **arrival-rate**(1 線)。
- **Cai2025(EE joint uplink BH)**:主=CDF;Fig13 WSEE vs **max Tx-power** ★;Fig12 EE vs bias χ。
- **Ntabeni2025(EA-QL HO)**:Fig1 多指標 vs energy-penalty λ(敏感度,1 法);Fig2-5 vs-time(4 法)。
- **Guo2022(sensors BH)**:Fig8-12 throughput/delay/access-rate/**delay-variance** vs **traffic-arrival-intensity** ★(4 線)。

### MARL / load-balance
- **Load-Aware 2021**:Fig4 blocking vs #users ★、Fig5/6 blocking/HO vs #channels ★(4 線)。
- **RL-LB NS-3 2023**:全 vs-NEP 收斂曲線(無 ★)。
- **Mega MA-SHDQL 2024**:Fig8-11 reward/rate/cost/HO-delay vs {user-area, **Rmin**, **#sats**, **#users**} ★(5 線,各 4 panel)。
- **MADQN 2025(Lee)**:Fig3 QoS-ratio vs UE-groups(bar)、Fig4 throughput vs time。少 ★。
- **MAF-DDQN 2024**:Fig13 6 指標 vs **#MTs** ★、Fig15 vs **arrival-rate λ** ★(7 線)。
- **Multi-Beam MADQN 2025**:Fig2 throughput vs time;主結果在表。
- **REDA 2025(seq assign)**:vs-step 收斂 + Fig4 grouped-bar。

### DRL handover
- **SDQL 2022**:Fig3(a/b/c)reward/throughput/forced-term vs **#channels Cmax** ★(6 線)。
- **DHO 2023**:Fig5/6 delay/collision vs **#RBs / #preambles** ★(3 線)。
- **Energy-Aware 2024(LBEASH)**:全 vs-episode(無 ★)。
- **Nash-SAC 2024**:Fig3 blocking vs **available channels** ★(6 線);Fig5 CINR-CDF。
- **GNN-HO 2024**:Fig5 avg-rate vs **#UEs** ★(4 線)。
- **User-Centric Multi-TP 2024**:全 vs-episode(無 ★)。
- **QoE-driven 2020**:Fig12/13 HO/HO-fail vs **terminal speed** ★、Fig15/16 HO/delay vs **satellite load** ★(6 線)。
- **Fast-moving 2025**:Fig2-6 throughput/hop/#HO/**Jain** vs **#agents** ★(4 線)。

### 其餘 handover 策略
- **User-Centric 2020**:Fig5 throughput vs **altitude** ★、Fig6 vs **shadowing-prob** ★(5 線)。
- **Net-Flows 2021**:Fig3/4 QoE vs **#UTs M**(ample/scarce BW)★(6 線)。
- **Weighted-Graph Aero 2022**:Fig5/6/8 throughput vs **EIRP** ★(3-5 線)。
- **Bipartite-HM 2025**:Fig7 #HO vs connection-duration ★、Fig12 cost vs energy/RTT-weight ★。
- **Sat-Aircraft PHSU 2024**:Fig6-15 rate/utility/HO-freq/HO-delay vs **satellite-load / constellation-scale / #aircraft / #subchannels** ★(3 線,共 10 張)。
- **Multi-Connectivity CHO 2024**:Fig3/4/6 #HO/RLF/capacity vs **beam-overlap%** ★(2-4 線)。
- **RSMA soft-HO 2025**:MMR/WSR vs **deviation-angle θ** ★(3-4 線,部分非單調)。
- **Novel HO 2025**:無自有模擬(position paper)。

---

*產出:Track-1 圖表調查(只讀)。下一步交 USER 排程:先 (B) 本地 eval 看主圖,再決定 (A) heavy 重訓範圍。本文件不觸 G1 `aa877676` / EUV `389eaaef`。*
