# WRITING-HANDOFF — 新 thesis(mc-modqn 版)ch1–3 補完(貼進「文字」新對話)

> **HISTORICAL HANDOFF — DO NOT USE AS CURRENT INSTRUCTIONS.** 現行入口與權威路由只看
> `README.md`；本檔保留早期寫作脈絡，內含已撤回的花體符號規則與舊方法分支，均不得回灌現行論文。

> 一句話:以 `thesis-mc/mc-modqn-base.md` 為底,照 `catfish/ris.docx` 章節結構,**只寫前三章**,把第四章會用到的所有公式/符號在第三章定義清楚但不要太難,公式符號寫法以 **MODQN 原論文為聖經**,口氣 = 不熟通訊/衛星/RL 的學生認真讀了論文寫出來的。輸出 markdown,最後用 `to-ris-docx` skill 轉回 word。

## 0. 背景(這串設計對話的結論,避免重啟丟 context)
- 專案 = 重現+延伸 MODQN(Sun2024)LEO 多波束換手 MORL。
- **方向已鎖**:r1 = **角度感知能量效率(EE)**(不是吞吐量);protagonist = **Multi-Catfish**(CDRL 鯰魚效應「輔助代理用高經驗價值刺激主代理探索」延伸成 3 個 per-objective 角色,對應 r1=EE / r2=換手 / r3=負載)。
- **ch4 方法路線還沒最終拍板**(兩條:① 保守忠實 multi-catfish 探索刺激;② route-B「catfish 競標 auction 取代 per-user-argmax、去崩」)→ **本任務只寫 ch1–3,必須對 ch4 兩條都通用(ch4-fork-agnostic)**:只定義系統/目標/MDP 符號(兩條共用),不要把 ch1–3 綁死在 auction 或任何特定鯰魚機制。鯰魚在 ch1–3 只描述到「per-objective 輔助代理、延伸 CDRL」這個層級。
- 誠實框架:比較對象 = 原始 MODQN(+ 之後弱靜態);不誇大;mc-modqn 現有語氣已經是「will be evaluated」的提案式,保持。

## 1. 結構(照 ris.docx,本任務只到 ch3)
```
1. Introduction                         ← base 已寫,潤即可
2. Background
   2.1 Related works                    ← base 已寫
   2.2 Motivation                       ← base 已寫
3. Preliminaries
   3.1 System model                     ← base 已寫(3.1.1 Network / 3.1.2 Geometry+Channel / 3.1.3 SINR+Throughput / 3.1.4 State+Action)
   3.2 Problem formulation              ← ★ 要寫(最重要:EE 獎勵 r1 + r2 + r3 + J_w + MDP)
   3.3 Basic idea                       ← 要寫(鯰魚概念導入,白話)
   3.4 Comparison ... (Catfish-DRL vs competing)  ← 要寫(可用比較表 + 一段文字)
```
base = `thesis-mc/mc-modqn-base.md`(982 行,= mc-modqn.docx 轉的 markdown)。**ch4/ch5/ch6 不寫。**

## 2. ★ 第三章鐵則(USER binding)
1. **不要太多複雜公式/定義/演算法**——老師(不一定 RL 背景)要看得懂。3.1 已是好範例(乾淨、白話括號補述)。
2. **但第四章會用到的「所有」公式 + 符號,第三章要定義齊全**(ch4 不要再臨時定義系統符號)。
3. → 拿捏:3.2 把**基礎記號 + 系統量 + 三個目標獎勵 + 加權指標 + MDP**定義完整且可讀;**複雜的 Multi-Catfish 演算法本身留 ch4**。

### 3.2 必須定義的符號清單(ch4 會用到的全部 system/objective 記號)
- 集合/索引:$\mathcal{U},\mathcal{S},\mathcal{V},\mathcal{K}$;$u,s,v,t,k$(base 3.1 已有)
- 連接/負載:$x_{u,s,v}(t)$、$z_{s,v}(t)$、$U_{s,v}(t)$、$N(t)$(已有)
- 幾何/通道:仰角 $\alpha$、偏軸角 $\theta_{u,s,v}$、斜距 $d$、波束增益 $G_T(\theta)$、複合鏈路增益 $h_{u,s,v}$(已有)
- 訊號:發射功率 $p_{s,v}$、同/跨衛星干擾、候選 SINR $\gamma_{u,s,v}$ 與使用者實際 SINR $\gamma_u$、頻寬 $W$、候選速率 $R_{u,s,v}$ 與使用者實際吞吐量 $R_u$（已有 3.1.3）
- **★ EE(3.2 要新定義,= 貢獻核心)**:角度感知能量效率 $\eta^{EE}_{u}$ 或 $r_1$。需含「每使用者吞吐量 / 對應功率(含偏軸角→增益→所需功率)」,白話講清楚為何不是「吞吐量÷固定功率」。功率項要連到 $\theta$、增益、干擾。**用 MODQN 原論文 + HOBS[4] 的記號風格**。
- **r2(換手獎勵)**:懲罰使用者換服務波束(用 $x_{u,\cdot}(t)$ vs $x_{u,\cdot}(t{-}1)$)。
- **r3(負載平衡獎勵)**:懲罰波束過度集中(用 $U_{s,v}(t)$ / $N(t)$ 的分散度)。
- **加權指標** $J_w=\sum_k w_k (r_k/\text{scale}_k)$,$w=(0.5,0.3,0.2)$,scale 說明。
- **MDP** 元組(狀態 $s_u(t)$、動作 $a_u(t)/a(t)$、獎勵、轉移、折扣 $\beta$ 或 $\gamma$——**符號跟 MODQN 原論文一致**)、Q 函數、MODQN 的「三個並行 Q 網路 + 純量化選動作」。
- ⚠ 三個目標獎勵都要定義 **per-(user) 與(若 ch4 需要)per-(user,beam) 的版本**,因為鯰魚要對每個 (使用者, 候選波束) 估各目標價值。

## 3. ★ 公式/符號聖經 = MODQN 原論文
`paper-catalog/ref/2024_09_Handover_for_Multi-Beam_LEO_Satellite_Networks_A_Multi-Objective_Reinforcement_Learning_Method.pdf`
- **優先沿用這篇的符號命名、公式排版、reward/Q/scalarization 的寫法。** 有衝突時以這篇為準。
- 先讀這篇的 system model + reward + MODQN 公式段,把記號對齊再下筆。
- base(mc-modqn)已大致對齊;3.2 的 reward/MDP 一定要再核這篇。

## 4. ★ 口氣(binding,沿用 `thesis/HANDOFF.md` §B/§B.1/§C,USER 再強調)
- 作者人設 = **對通訊/衛星 + RL/DRL 都不熟的學生,讀了幾篇論文努力寫**。白話但仍學術、**不口語**。像「看了論文努力寫出來」,不是專家寫。
- **不要太專業 jargon**(不用 映射/前向推論/攤銷/解碼器/蒸餾);用「做什麼」的白話講機制。
- **也不要太口語**(還是學術論文)。句子平實、拆長句、少巢狀引號、≤1 破折號/頁。
- 去 AI 化:掃掉 誠實-meta/需要再次強調/值得注意的是/工程師腔。保留 本研究/換句話說/「」術語。
- **改完一定 voice-check 再存**(§B.1 教訓)。
- 已寫的 ch1–3.1 也順一次語氣一致性。

## 5. 參考文獻(USER)
- **盡量近年 + 高等級期刊/會議**;經典(如 PBRS Ng-1999、DQN)才用舊的。
- 可從 `thesis/REFERENCES.md`(route-C 版,[1]–[22] 已 claim 級驗證)收割可重用的近年高等級條目;但 mc-modqn 自己用 [1]–[12],**編號要自洽重整**。
- 新加的 ref 一律先確認 venue/年份/作者(refute-by-default),別塞 arXiv/低階。

## 6. 正確性(別只抄論文,要對得上實作)
- ch3 系統模型公式要跟**凍結 env 實作對齊**:`src/modqn_paper_reproduction/env/family_b_*.py`(唯讀,sha `3cd5000a`)。
- 描述的是「真的跑的 env」。理想化/簡化處要心裡有數(可保留論文式乾淨公式,但別寫出 env 沒有的東西)。
- `thesis/ch3-preliminaries.md`(route-C 版,標「Sun2024 公式已驗證」)可參考其驗證過的式子,但**不要照搬其 route-C 脊椎**。

## 7. 輸出 + 邊界
- 輸出:`thesis-mc/ch1-introduction.md` / `ch2-background.md` / `ch3-preliminaries.md`(或直接在 `mc-modqn-base.md` 上補完再拆)。markdown。
- **只動 `thesis-mc/`**。不要碰 `thesis/`(route-C fallback,保留)、不要碰 G1 `modqn.py`(`aa877676`)、env EUV(`3cd5000a`)。
- 最後階段(文字+圖都好):用 **`to-ris-docx` skill** 把 markdown 轉回 ris.docx word 格式。
- 圖:本任務**不畫圖**(另一個「圖」對話做 FIG-1/2/3);文字裡放 `[FIG-1]`/`[FIG-2]`/`[FIG-3]` placeholder,caption 寫清楚當 figure brief。圖好了再回來對齊標籤(USER 的「補完圖再用圖改文字」)。

## 8. 完成定義(ch1–3)
ch1 潤好 · ch2 潤好 · ch3 = 3.1 潤 + **3.2/3.3/3.4 寫完** · 全部符號齊備可餵 ch4 · 聖經對齊 · voice-check 過 · ref 近年高階自洽 · `[FIG-n]` placeholder 就位 · 只動 thesis-mc/。

---

## 9. SESSION 進度 + 下一步(2026-06-26 補)

### 9.1 本次已完成(全在 `thesis-mc/`,**未 commit**)
- **ch1–3 全寫完**(`mc-modqn-base.md`,目前**仍雙語**):
  - **3.2 新寫** — EE r1 = 吞吐量 ÷ 每使用者分配功率(對齊凍結 env `family_b_step.py` 的 `r1_energy_efficiency_credit = r1/(beam_power/load)`;角度經 SINR→Bessel 增益 `G_T(θ)`→偏軸角進來);r2 換手(0/−φ1/−φ2)、r3 負載(波束吞吐量 max−min)、J_w 加權指標、MOMDP+三 Q+純量化 ζ+per-user argmax+Q 更新;**per-(使用者,候選波束)候選價值**(式 3.36–3.38,給 ch4 鯰魚估值)。公式式號連續 3.1–3.39。
  - **3.3 basic idea**(鯰魚→多鯰魚,**ch4-fork 通用**:明寫「探索壓力 or 改變候選選取,留 ch4,涵蓋不只一種機制」)、**3.4 comparison**(對照表 + 文字)。
  - **ch1/ch2/ch3.1 潤**:ch1 英文 blockquote 清掉、ch2 HOBS 重複句刪、用詞統一(本文 ×80 / 主要代理;無 本研究/主要學習者)。
- **References `thesis-mc/REFERENCES.md`**:[1]–[12] ris IEEE 格式 + 核實附錄(sub-agent refute-by-default)。**引用號 = 首次出現序(已驗 [1]@117→[12]@769)**。[7] 內文已對齊 TVT(Zhu「Random Traffic Arrival」)。⚠ **5 篇缺欄位**(資料未取得,非格式錯):[3]Ntabeni No./pp./月、[5]月、[4]/[9]/[11] 會議 pp. → 收尾跑 `/ars-citation-check` 補。
- **中文 voice de-AI(重要)**:codex(gpt-5.5,cross-model)**3 輪**冷讀 → 第1版「中偏高 AI 味」→ 第3版「**不像典型 AI、主體語氣接近穩定學生論文**」。教訓:**同模型 Claude 審 Claude 寫的聞不到自己 AI 味,cross-model(codex)才抓得到**(memory #16/#17)。含 1 個誠實框架修正(方法章不宣稱 catfish 已生效 → 「**預期**也能降低」)。
- **圖 placeholder**:FIG-1(ch1 overview)/FIG-2(ch3.1 系統模型)/FIG-3(ch3.2 MODQN baseline)/TABLE-3.2,caption-brief 就位,對齊 `FIGURE-HANDOFF.md`。
- 邊界守住:G1 `modqn.py aa877676` + env EUV `family_b_* 3cd5000a` 未碰;只動 `thesis-mc/`。

### 9.2 本次 USER 決定(binding)
- **內文改純中文**(台灣碩論慣例 = 中文內文 + 雙語摘要;雙語內文是起草 scaffold)。
- **英文最後一次重翻**(內容凍結後),不維持雙語(避免中英分岔 + 雙倍維護)。**英文目前尚未 de-AI**(只掃了中文)→ 中英已分岔,正是刪英文重翻的理由。

### 9.3 下一步(新對話,優先序)
1. **先更新最下方「§10 最新專案狀況」區。**
2. **執行「刪內文英文」**(⚠ 非純機械,先 `cp` 備份 `mc-modqn-base.md`):
   - **保留**:① 中英雙語**摘要** ② 英文**章節標題**(ris 格式)③ **所有公式 `$$...$$`**(目前嵌在英文段、中文用式號引用,刪英文時務必留下)④ 全部中文段。
   - **刪**:英文 **prose 段落**。
   - **轉中文**:FIG-1/2/3 + TABLE-3.2 的 **caption-brief**(目前寫在英文段裡,圖那邊 `FIGURE-HANDOFF.md` 要用)。
   - **驗收**:`grep tag{3.` 仍 39 式、FIG-1/2/3 + TABLE-3.2 仍在、中文段完整、無孤兒式號。
3. 繼續內容:ch4-fork 拍板後對齊、results 待 server。
4. 收尾鏈:`/ars-citation-check` 補頁碼 → **commit(USER 確認、`git commit -- <明確路徑>`、不自行 push)** → 圖好 → `to-ris-docx` 轉 word。

---

## 10. 最新專案狀況(★ 新對話進來先更新這區 ★)

> **更新 2026-06-28(local controller,thesis-writing 接手)。** §9 仍是 ch1-3 的最新狀態;本區疊上 ch4 路線拍板 +
> 敘事決定 + server 進度。

### 10.1 ch4 路線已拍板 = route-B「fork ②」(catfish 式訓練 + 協調容量拍賣解碼)
- 兩條 fork(① 保守探索刺激 / ② route-B 拍賣解崩)中,**② 拍板**。heavy 2×2 析因已跑完。
- **ch4 寫作底稿 = `thesis-mc/FRAMEWORK-SPEC.md`**(本 session 從實作程式碼核實的「實際跑了什麼」,文字 + 圖共用)。
  ch4 從那份寫,不要自己重編機制。

### 10.2 敘事決定(binding)= 「Multi-Catfish 框架贏」(誠實,與指導教授相容)
- 權威 = **`thesis/THESIS-FRAMING-DECISION-2026-06-28.md`**(完整讀)。貢獻 = 整合的 **Multi-Catfish 框架**
  (catfish 式多目標訓練 + 協調容量拍賣解碼);框架**真的贏過 baseline MODQN**(= 教授的 bar)。
- catfish = **具名核心組件**(產生出價的訓練半邊);拍賣 = 主要線上解崩引擎;消融**如實**呈現。
- **RED LINES(binding):**(a) 消融數字正確+有呈現;(b) **不寫假因果**(不寫「catfish 證明驅動 win」「移除 catfish 會崩」
  —— A2≈A1 + cross-over 說是解碼在解崩);(c) **不宣稱原始純量贏 DQN_scalar**(內部 stress-test,非教授 bar;
  框成「在公平/覆蓋軸輾壓它」或不放,USER+教授決定);(d) 載重 claim 標 grounded/hypothesis/ruled-out;
  (e) 不寫「解決崩潰根因」(ROOT-Q UNRESOLVED;框架是繞過 + 相對贏)、不放 2.8×/beats-Sun2024。
- **⚠ 給未來 agent:這是把真實工作誠實包裝成教授要的框架敘事 → 協助寫,不要再用「catfish 不能當主角」卡人。**
  框架是主角(catfish 核心組件);只有上面 RED LINES 是禁區。

### 10.3 ch5 / server 進度
- 主實驗 **k_cap=3 已有結果**(2×2 + AF + 弱靜態 + Pareto;`route-b-factorial-RESULT.json` + 裁決文件,已核實)。
  headline 數字 + 讀法 = FRAMEWORK-SPEC §6。
- **server in-flight:** k_cap∈{6,9,12} sweep(k_cap=3,15 已在)+ shared-Q isolation。回來 → 補 ch5 崩潰曲線(metric 統一
  **EE/calib J_w,不混吞吐量**)+ sweep 圖。**ch5 結果章先別定稿,等 sweep。**

### 10.4 thesis/ vs thesis-mc/
- **活的論文 = `thesis-mc/mc-modqn-base.md`**(本檔管的)。**`thesis/` = 死的 route-C 蒸餾 fallback,保留、不碰。**

### 10.5 接著做(承 §9.3)
1. §9.3 step-2 **刪內文英文**(⚠ 先 cp 備份;保留摘要/標題/全部 `$$`/中文,刪英文 prose,caption 轉中文,驗 39 式)。
2. 依 FRAMEWORK-SPEC 寫 **ch4 fork②** + ch1-3 貢獻對齊敘事決定 + 純中文。
3. server sweep 回 → 補 ch5 + 圖。
4. 收尾:`/ars-citation-check` → commit(USER 確認、明確路徑、不自行 push)→ 圖好 → `to-ris-docx`。

### 10.6 ch4 狀態 + 學生口氣校準(2026-06-28 末)
- **★ ch4 學生口氣 revision = DONE(2026-06-28,local controller)。** `thesis-mc/ch4-method.md` 全章依 `VOICE-CALIBRATION.md`
  改寫(短句直述、名詞:定義清單、樸素連接詞、γ 0.9–0.99 基礎解釋、簡單公式引語);公式 4.1–4.10 逐字保留、術語/RED LINES 全守。
  **cross-model voice-check = 雙模型收斂 SOUND:**(1) agy Gemini 3.1 Pro = 9/10、RED LINES a/b/c/d 全 SAFE、3 白話動詞
  搆到/被搶/相讓 → 已修 列為候選/發生競爭/錯開;(2) codex(USER 換帳號後,2 次完整 run 都 8/10、RED LINES 全守、(b)
  「問題主要出在選動作這一步/才造成集中」語氣偏強建議軟化)→ 已套 6 處收斂 fix(框架整理句拆平鋪兩步 + (b) 軟成
  「主要要改進的是選動作這一步/容易造成集中」+ 處理不了→沒辦法直接處理 + 搶→競爭 + 貢獻能分開檢驗→分別看兩個改動)。
  **最終:公式 4.1–4.10×10 齊、0 禁用 jargon、RED-LINE (b) 軟化、(d) 誠實邊界在。ch4 voice 定稿。**(codex verdict 在
  session jsonl `~/.codex/sessions/2026/06/28/rollout-…019f0e62 / …019f0e53`;stdout 被 buffer/sed 截但 jsonl 留全文。)
- **★ ch1+摘要 貢獻對齊 = DONE + 已寫入活檔 `mc-modqn-base.md`(2026-06-28)。** 8 區塊(EN/ZH 摘要+關鍵字+貢獻清單+方法概述段)
  改成框架贏敘事。Gemini Pro 載重 claim-check = **全 RED LINES PASS**(codex 這台機器反覆 9min timeout 寫不出 verdict → Gemini 合法跨模型 guard)。
  驗證:ch1+摘要區 0 舊框架殘留、formula 14 不變、關鍵字加「協調式波束分配」、無 3.85x/拍賣。backup 在 scratchpad。USER 決定:
  (D1) DQN_scalar = 放 ch5、框公平/覆蓋軸(摘要不提;貢獻 #3 有「避免犧牲尾端使用者覆蓋」一句);(D2) 摘要寫「贏」但**scope 到 k=3–9**
  (k=15 翻盤誠實寫「甚至不再領先」);(D3) FIG-1 caption 圖 track 改;(D4) 關鍵字已加。
- **★ k_cap sweep = DONE + scored(權威 = CSV `scratch/fig5_k_cap_matched_sweep.csv`,非 CURRENT-STATE 轉述,後者數字已修)。** win-bar=calib J_w:
  A2_MCRL vs B0_PlainMODQN → k=3 4.82e-4/-1.0e-5、k=6 2.59e-4/-4e-6、k=9 5.21e-5/1.26e-5(**贏,CI 分離**)、**k=15 -6.85e-5/+2.15e-5(MODQN 反超)**;
  min_cov MCRL ~1.0 全程 vs MODQN ~0。**win scope = k∈{3,6,9};k=15 = 高容量同頻干擾翻盤(誠實 k_cap 診斷邊界)。EE 倍數 3.82/2.31/1.59x 禁 headline。**
- **★ 消融結構 = USER 拍板「兩個都留」:** §4.6 的 2×2 鯰魚-credit(k=3 factorial 有全 arm,守 RED-LINE cross-over/A2≈A1)+ ch5 sweep 的
  目標維度消融(no_handover [0.8,0,0.2] / no_fairness [0.7,0.3,0],跨 k_cap)。ch4 §4.6 已補維度消融段(Q1 DONE)。
- **NEXT(承上):** (1) 對齊 **ch2.2 動機 / ch3.3 basic idea / ch3.4 comparison** 的舊「輔助代理刺激探索」catfish 框架(ch2.1 描述 CDRL [8]
  原文的「auxiliary agent stimulates」是正確的、不動);(2) 寫 **ch5**(鯰魚組件消融表[k=3] + 容量敏感度維度折線圖[跨 k_cap];metric=calib J_w 主、EE 逐軸;
  k=15 翻盤誠實段);(3) 收尾刪英文。**commit 待 USER 指示(明確路徑、不自行 push)。** G1/EUV 唯讀未動。
- 校準來源 + 具體 before/after = **`thesis-mc/VOICE-CALIBRATION.md`**(對標 `catfish/ris.docx`:短句直述、名詞:定義清單、樸素連接詞、順手解釋基礎、簡單公式引語;**不口語**)。
- **fresh session 接手順序:** 讀 `CURRENT-STATE.md` 最上 + 本檔 §10(尤其 §10.7 最新)+ `VOICE-CALIBRATION.md` + `FRAMEWORK-SPEC.md` → (1) ch4 學生口氣 revision【DONE】;(2) ch2.2/3.3/3.4 對齊【DONE 2026-06-29,cross-model PASS,見 §10.7】;(3) 寫 ch5(k_cap 數字等 sweep);(4) 翻轉點定→同步修前面 scope;(5) 內容凍結後刪英文(§9.3 step2)。術語/RED LINES/邊界全照 §10.2 + VOICE-CALIBRATION §C。

### 10.7 ch2.2/3.3/3.4 對齊 DONE + k_cap 翻轉點更新(2026-06-29,local controller)
- **★ ch2.2 動機 / ch3.3 basic idea / ch3.4 comparison 對齊 = DONE**(只動 `mc-modqn-base.md` 中文散文,9 處 Edit):舊「輔助代理刺激探索 / 提供探索壓力」框架 → ch4 兩步框架(估值=鯰魚式訓練 + 分配=協調式波束分配)。**ch3.3 鋪好「兩種用法」並收束「本文採用第二種做法」**(改變候選波束被估值與被選取的方式)→ ch4 §4.2「第 3.3 節留下的第二種做法」指涉解決。術語「協調式波束分配 / 綜合價值」入 3.3×2 + 3.4×1。**ch2.1 CDRL [8] 原文「刺激主要代理探索」未動**(照指示)。route-C 殘留(示範資料 warm-up + 維持探索)清掉。公式/式號/FIG/TABLE 不變;G1 `aa877676` / EUV `389eaaef` 唯讀未碰。
- **cross-model voice/claim check = PASS**:agy Gemini 3.5 Flash(High)= SOUND;3.1 Pro(High)= NOT-SOUND 但唯一 blocker = 術語「協調式波束分配」未現於 NEW 文字 → 已補 → PASS。**兩模型一致:RED LINES (a)-(d) 全 SAFE、對齊成功、口氣 8-9/10。** log `artifacts/_codex-logs/voiceclaim-ch223334-gemini3{1pro,5flash}.txt`。
- **★★ k_cap 翻轉點更新(grounded,CSV 直讀 `scratch/fig5_k_cap_matched_sweep.csv`,目前 5 點 scored {3,6,9,12,15}):**
  - A2_MCRL vs B0_MODQN(calib J_w,CI 分離判定):k=3 / 6 / 9 / **12** = **A2 贏**(k=12 新進、CI 分離贏);k=15 = **B0 反超**(CI 分離)。
  - ⇒ **win 視窗現在 = {3, 6, 9, 12}**(不再是舊記的 {3,6,9});**翻轉落在 13–15 之間**(k=15 確定 B0 贏;13、14 仍處理中才能定死確切點;中間 8 點 {4,5,7,8,10,11,13,14} scored-in-progress)。
  - 誠實 nuance:即使 k=15 加權純量翻盤,**A2 仍 min_cov 0.999 vs B0 0.008**(翻盤只在加權軸;覆蓋軸 A2 仍贏)。ch5 照實寫。
- **⚠⚠ 前面要修正(USER 料中):`abstract` / `ch1` 現寫「k=3–9 贏」= 已偏窄**(k=12 也贏)。**`CURRENT-STATE.md` + memory 的「win scoped k∈{3,6,9}」同樣 STALE。** → 等 {13,14} 定死翻轉點,**一次同步改 abstract + ch1 + ch5 + CURRENT-STATE + memory**(避免分岔);此為載重 honest 數字,不可猜。
- **ch5 / ch6(`thesis-mc/`)= 未開始。** 可現在寫(L1/L2,不等資料):ch5 骨架 = §5.1 設定、兩個消融表框架 + 讀法、敘事脊椎(崩潰 → 框架解崩 → k_cap 容量敏感度 → 誠實翻轉邊界),數字 placeholder。要等(L3):k_cap 曲線數字、確切翻轉點、合併表 → 等 8 點 scored + 圖(research-visual-lab 另對話)。
- **消融「兩個都留」(USER 拍板):** §4.6 的 2×2 鯰魚-credit(k=3 全 arm,守 cross-over / A2≈A1)+ ch5 維度消融(no_handover [0.8,0,0.2] / no_fairness [0.7,0.3,0],跨 k_cap)。CSV 已含這兩個維度消融欄。
- **NEXT:** (1) 寫 ch5;(2) 翻轉點定 → 同步修前面 scope + CURRENT-STATE + memory;(3) ch6 結論;(4) 收尾 `/ars-citation-check` → commit → 圖好 → `to-ris-docx`。**heavy = HARD USER go-server gate;commit 明確路徑、不自行 push。**

### 10.8 ch5 + ch6 DRAFTED + references 12→21 + k_cap 全同步(2026-06-29,local controller — SESSION 結束,建議換對話接後續)
- **★ ch5 `thesis-mc/ch5-experimental-result.md` 全 draft(§5.1–5.6,純中文)** — §5.1 設定+評估協定(TABLE-5.1 參數含 3000 ep/10 步/ε 1→0.01/lr 0.01/batch 128/Double-DQN/3 seed/48-ep matched + TABLE-5.2 arm 定義)、§5.2 崩潰(k=3 B0/B1 active 3/qos .29/min_cov 0)、§5.3 主結果 10-arm(TABLE-5.3 + **J_w 三軸誠實分解:贏集中在 EE 軸,r3 負載反略差** [memory #18] + DQN_scalar 框公平/覆蓋軸 RED-LINE c 守住 + AF gate-control A1≈AF span0 誠實寫)、§5.4 2×2 鯰魚-credit + cross-over(TABLE-5.4,守 RED-LINE b:解崩=分配步驟、A2≈A1、不寫假因果)、§5.5 **k_cap 13 點 sweep(TABLE-5.5)+ 維度消融**、§5.6 討論。數字全部 artifact 直讀(`route-b-factorial-RESULT.json`/`fairness-pareto`/`dqn-scalar-fold` + sweep CSV)。
- **★ ch6 `thesis-mc/ch6-conclusion.md` 全 draft(§6.1 總結 / §6.2 貢獻 C1 grounded + C2 hypothesis + k_cap diagnosis / §6.3 限制+未來)。**
- **★★ k_cap = 全 13 點。⛔ 此條原本的「WIN ZONE = k≤12 / k=11–12 打平 / B0 贏 k=13–15」= SUPERSEDED**(那是平滑值;USER 抓到平滑 artifact)→ 見下 §10.10 + `CH5-FIG-SMOOTHING-FIX-NOTE-2026-06-29.md` §RESOLUTION。authority CSV = `scratch/final_figures/fig5_4_kcap_sweep_raw.csv`(RAW + bootstrap CI;平滑 csv `fig5_4_kcap_sweep.csv` 只給折線視覺)。**RAW+CI 勝方(已套入 ch5/ch6/abstract/ch1/CURRENT-STATE,2026-06-29,agy Gemini-Pro SOUND):A2 CI 分離贏 k=3–10(連續八點);k≥11 兩者趨近 0、勝方逐點互換(B0 在 11/13/15、A2 在 12/14、每點差距 <1e-4、無穩定方向);A2 min_cov ≈1.0 + EE CI 分離 > B0 全 k。** ⚠ 圖曲線(平滑)只作視覺趨勢,勝負一律以 TABLE-5.5 raw + CI 為準。
- **★ references 12 → 21 DONE**:`thesis-mc/REFERENCES.md` 加 `[13]–[21]`(ch3.2 純量化[13]Tajmajer/DQN[14]Mnih;ch4 [15]PD-MORL/[16]PER-Schaul/[17]Calvo-Fullana/[18]Agorio/[19]Holder/[20]Ye/[21]Double-DQN-vanHasselt),內文標記已插 `mc-modqn-base.md` 3.2 + `ch4-method.md`。一致性:內文 `{1..21}` ≡ 清單 `{1..21}` 0 孤兒 0 缺號。CDRL=[8] 在。**殘留:4 個 gated 欄([3]/[9]/[11] pp、[5] 月)= `/ars-citation-check` 或登入 IEEE 補,不可捏造。**
- **★ 內審已做**:3 路 refute-by-default workflow(data-fidelity / red-lines / voice)→ 折進修正(B0/B1 數字、active-vs-eff 波束釐清、誠實-meta tics「誠實邊界/如實/具名/對抗性」清掉、ch6 補 DQN_scalar 較高承認句)。**但 ch5/ch6 = 同模型 Claude 審 → 還沒過 cross-model codex/agy(載重,定稿前必過,= NEXT #1)。**
- **★ `fig5_3_user_sweep` = 不進論文(USER 已 CURRENT-STATE §31 排除)**:資料與主結果矛盾(MCRL min_cov=0 vs 主結果 ~1.0、RSS_max 反贏 Jw、缺 B0)+ 與 k_cap 同壅塞軸重複。訓練收斂圖 fig5_5 USER 也說不需要。
- **NEXT QUEUE(建議新對話依序):** (1) **ch5/ch6 跨模型 voice/claim check**(codex + agy Gemini,refute-by-default;餵 RED LINES[FRAMEWORK-SPEC §7] + VOICE-CALIBRATION + authority 數字)→ 折修;(2) 圖整合(FIG-5.1–5.4 ↔ MANIFEST.md 的 fig5_1/5_2/5_4/5_5 + arm 命名 codes↔`Proposed MCRL` 對照 + 平滑 label/值定案;FIG-1~5 架構圖)→ 同步標籤;(3) **刪 ch1–3 interim 英文**(`mc-modqn-base.md` 565 行英文 prose;⚠ 非純機械,先 cp 備份,保留摘要/標題/全部 `$$`/中文);(4) `/ars-citation-check` 補引用;(5) commit(USER 確認、明確路徑、不自行 push);(6) **英文一次性重翻** + `to-ris-docx` 轉 word。G1 `aa877676`/EUV `389eaaef` 唯讀全程未碰。

### 10.9 刪 ch1–3 interim 英文 + citation-check DONE(2026-06-29,local controller — 本 session)
- **★ 刪內文英文 DONE**:`mc-modqn-base.md` **1371 → 592 行**。備份 `scratchpad/mc-modqn-base.BACKUP-pre-en-deletion.md`。
  - **方法(非機械,腳本化可重跑)**:`scratchpad/strip_en.py`(`$$`-配對狀態機 → 公式段逐字保留;**段落級** CJK 判定 → 留整段含中文)+ `scratchpad/finalize.py`(插中文圖/表 caption + 搬 TABLE-3.2)。
  - **⚠ 關鍵教訓(下次刪英文必看)**:DOCX 硬斷行會把中文段裡的英文 token 單獨成行(作者姓 `Chen`/`Q`/引文 `\[6\]。Zhu`);**逐行「無 CJK 即刪」會切爛中文句**(「能量感知 Q 學習」→「能量感知學習」)。必須**段落級**(整段任一行含中日韓表意字 U+4E00–9FFF 就留整段);全形空格 U+3000 不算 CJK。
  - **驗收(全綠)**:39 式號齊(`\text{(3.1..25)}`+`\tag{3.26..39}`)、72 `$$`、**math block 與備份逐位元相同**(36/36)、**CJK 行集合與原檔完全相同**(279 行)、0 孤兒式號、0 英文洩漏、in-text 引用 [1]–[21] 完整無孤兒。
  - **保留**:中英雙語摘要 + 英文章節標題(13)+ 全部 `$$` + 全部中文段。**轉中文**:FIG-1/2/3 + TABLE-3.2 caption-brief(譯成中文 placeholder `\[FIG-n：…\]`,RED-LINE 自審通過:FIG-1=整合框架敘事、無假因果、無 2.8×/解根因);TABLE-3.2 已搬到其中文引介句之後。
- **★ /ars-citation-check DONE**(refute-by-default,多源:Crossref + dblp + Semantic Scholar + OpenAlex):
  - **[3]** pp. **5657-5666**(dblp+Crossref 雙核)、**[9]** pp. **1-5**(Crossref;full DOI 10.1109/VTC2025-Spring65109.2025.11174574)、**[11]** pp. **633-634**(Crossref;DOI 10.1109/APCC55198.2022.9943773)。3 個 gated pp 全補齊。
  - **[5] 月份 = 查不到**(Crossref/dblp/SemScholar 僅年;OpenAlex 回 placeholder `2025-01-01`;真月需 IEEE Xplore 登入)→ **依「不捏造」+ OJ-COMS 連續卷年份制慣例,維持年份**(與 [3] 一致);`REFERENCES.md` 核實附錄已記。
- **邊界**:只動 `thesis-mc/{mc-modqn-base.md,REFERENCES.md,WRITING-HANDOFF.md}`;G1 `aa877676`/EUV `389eaaef` 唯讀未碰。**未 commit**(待 USER 確認、明確路徑、不自行 push)。
- **NEXT(承 §10.8)**:(1) ch5/ch6 跨模型 codex 2nd 票(quota);(2) 圖整合 + punch-list;(3) commit;(4) 內容凍結後英文一次性重翻 + `to-ris-docx`。caption 中譯的 voice/claim 終審併入(2)的跨模型 pass。

### 10.10 ★ ch5/ch6 必修(2026-06-29,USER 抓到平滑 artifact)— 高 k 誠實重框(載重)
> **權威 = `scratch/final_figures/SMOOTHING-ARTIFACT-AND-HIGHK-FINDINGS-2026-06-29.md`(完整讀 + 直讀 raw CSV)。codex 本輪停,跨模型改 agy Gemini。**
- **發現(grounded,CSV 直讀):** k_cap sweep 的 Gaussian σ=1.3 平滑在**高 k + 邊界**造成失真。(a) `fig5_4e` r2 k=15 懸崖 = artifact(非真);(b) **高 k Jw 比平滑曲線吵很多** —— RAW+CI:A2 **CI 勝 k≤10**,**k=11 RAW 是 B0 CI 勝**(平滑把它變「打平」),k=12-15 在雜訊內 zigzag。
- **ch5/ch6 要改:** (1) TABLE-5.5 數字 + 勝負判定一律用 **RAW mean + bootstrap CI**(平滑只給折線視覺;先查 TABLE-5.5 是否誤用平滑值);(2) 把「win zone k≤12 / k=13 乾淨翻盤」改成「**緊容量(k≤~10)CI 分離勝;高容量加權純量趨近 0、在雜訊內互換小勝;EE+覆蓋全 k 輾壓**」;(3) 同步修 `mc-modqn-base.md` abstract/ch1 + `CURRENT-STATE` 的 k≤12 字樣(k=11 raw B0 勝直接打臉「A2 wins k≤12」)。
- **核心 win 不受影響**(低 k + factorial k=3 = 4.82e-4 vs −1e-5,CI 鐵)。**這是誠實邊界修正,不是 win 死掉**(bidirectional,別過度 deflate)。`fig5_4c` 2 平線 = 真(A2 min_cov≈1.0 / B0≈0 全 k,保留)。
- **流程教訓(anti-MR):** 前一輪 result-fig QA 沒抓到(只比點值對 RESULT.json,沒驗「平滑 transform + 邊界 + raw 上的勝負」)。gemini review 餵**這份 note + raw CSV**,別餵平滑曲線。

### 10.10 final_figures 折線圖 CI 移除 DONE(2026-06-29, local controller)
- **USER 圖表決策:** `scratch/final_figures` 內 Chapter 5 折線圖**不畫信賴區間 band / error bar**。CI 欄位保留在 `fig5_4_kcap_sweep_raw.csv` 與表格中,只用於 win-zone / 顯著性判讀;後續圖整合、Origin 重製或 visual-lab 不要把 CI band 加回折線圖。
  - **★ 2026-06-29 更新(USER 抓到平滑 artifact → 見 §10.10 上方 + `CH5-FIG-SMOOTHING-FIX-NOTE`):** 原本「只畫平滑曲線」已**作廢** —— 折線圖改畫**各容量點的原始平均值(未經平滑、逐點相連)**,讓高 k 的逐點起伏與 k=11 B0 raw 勝直接可見;平滑 csv `fig5_4_kcap_sweep.csv` 降為非繪製、非權威的視覺輔助。仍維持「不畫 CI band」。
- **已同步:** `scratch/render_thesis_chapter5_plots.py` 移除 k-cap line plot 的 `fill_between`;`scratch/final_figures/MANIFEST.md` 加政策;`thesis-mc/ch5-experimental-result.md` FIG-5.3 caption 改為「圖中不畫信賴區間」。
