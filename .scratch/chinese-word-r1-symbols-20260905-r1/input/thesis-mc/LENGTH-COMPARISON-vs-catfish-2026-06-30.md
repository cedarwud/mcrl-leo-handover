# 論文長度／結構比對 vs catfish house-norm（2026-06-30）

> 純**唯讀分析**記錄。**未改任何論文內容／圖／build／git／G1／env**；唯一新建檔＝本檔。
> 度量＝**頁數 + 章節佔全文比例（%）**（跨語言：本論文＝繁中 body、catfish＝英文；裸字數 vs 詞數不可比，
> 故不用裸字數當主度量）。catfish/thesis.pdf＝同指導教授（陳裕賢）前作＝house norm。

---

## (a) 方法註 + 兩論文 totals

### 量測方法
- **本論文**：以 `bash`-render 的 docx→PDF `scratch/conversion-test/mc-thesis-ris.pdf` 逐頁 `pdftotext`，
  抓每個英文章節標題（"N. Title" / "N.N Title"）所在頁 → 章節起頁 → 章節頁數＝（下一標題起頁 − 本標題起頁）。
  - ⚠ **PDF 已重新 render（2026-06-30 07:32）**：原 47 頁 PDF（07:03）早於 ch4 去 pseudocode commit `c13284f`（07:22），
    已 stale；用當前 docx（07:23）以 LibreOffice 重 render＝**46 頁**（去兩個演算法 pseudocode 區塊使 ch4 −1 頁）。
- **catfish**：讀目錄（Contents，PDF p5–6）取每章/節**印刷頁碼**起點；以逐頁掃 "Chapter N" 驗證 → 印刷頁→PDF 頁 offset
  穩定 **＝ +9**（ch1 印刷 p1＝PDF p10、…、ch6 印刷 p54＝PDF p63、Bibliography PDF p64），六章全對齊，頁碼非杜撰。
- 章頁數一律「標題起頁差」法，兩篇同法 → 可比。

### ★★ 主方法學警告（load-bearing，先讀）
**兩 PDF 每頁密度不同，裸頁數不可直接比；佔比（%）才是 formatting-robust 的跨文度量。**
- catfish intro＝1161 英文字 / 5 頁＝**232 字/頁**（thesis 範本：寬行距、大邊界，頁面「鬆」）。
- 本論文 intro＝3174 CJK / 3 頁＝**~1058 字/頁**（ris-style render：單行距、頁面「滿」，密度約 catfish 的一倍）。
- ⇒ 本論文「頁數少」很大一部分是**排版較密**，不是內容真的短。**因此本比對以「佔全文/body 比例」為主**
  （密度在各自文件內大致均勻，佔比可消掉 per-document 排版差），裸頁數僅輔助。CJK 字數僅作章內細結構交叉檢查，
  且 ch5/§3.2 被表格/數學灌水（見 §c），不當主度量。

### Totals
| | 本論文（mc-thesis-ris.pdf） | catfish（thesis.pdf） |
|---|---|---|
| 總頁數 | **46** | **68** |
| 前置（題名/摘要/TOC/圖表目錄等） | 2 頁 | 9 頁 |
| 正文 ch1–ch6（body） | **41 頁** | **54 頁** |
| 參考文獻 | 3 頁 | 5 頁 |

> 前置 2 vs 9 頁＝**render artifact，非內容差**：catfish 前置含 Acknowledgements＋Contents＋List of Figures＋
> List of Tables（4 種 scaffolding 頁），本 docx render 只出題名＋中英摘要＋keywords（無 TOC/圖表目錄頁）。
> **故「前置頁數」這軸不可比**；摘要長度改用 R6 字數（§e）。

---

## (b) 主比對表（角色對映；% 為主、頁數輔助）

兩篇主題不同（本＝LEO 多波束換手 / catfish＝RIS 節能），按**角色**對映：intro / related-work / preliminaries(system-model) / method / experiments / conclusion。

| 角色／章 | 我頁數 | 我 %(/46) | 我 %(body/41) | catfish 頁數 | cat %(/68) | cat %(body/54) | 佔比比(body, 我÷cat) | 判定 | 備註 |
|---|---|---|---|---|---|---|---|---|---|
| 前置（摘要等） | 2 | 4.3% | — | 9 | 13.2% | — | — | N/A | 頁數 render-confounded；摘要見 §e（字數 2×=OVER） |
| ch1 Introduction | 3 | 6.5% | 7.3% | 5 | 7.4% | 9.3% | **0.79** | **UNDER**(頁) | 字數 1.43×(R6) 但佔比較 catfish 小；見 §e |
| ch2 Related/Background | 2 | 4.3% | 4.9% | 5 | 7.4% | 9.3% | **0.53** | **UNDER** | 已 de-dup（`814b68a` 1.9×→1.05×）；catfish 反而投更多 |
| ch3 Preliminaries | 11 | 23.9% | 26.8% | 13 | 19.1% | 24.1% | **1.11** | **OK/微 OVER** | 佔比僅 +11%；**絕對頁數比 catfish ch3 少**（11<13） |
| ch4 Method | 12 | 26.1% | 29.3% | 16 | 23.5% | 29.6% | **0.99** | **對齊** | 去 pseudocode 後幾乎 1:1 命中 norm |
| ch5 Experiments | 10 | 21.7% | 24.4% | 14 | 20.6% | 25.9% | **0.94** | **OK** | 略低於 norm |
| ch6 Conclusion | 3 | 6.5% | 7.3% | 1 | 1.5% | 1.9% | **3.84** | **OVER** | ⚠ catfish 結論異常短（1 頁）；本 3 頁/2816 CJK 重述偏多 |
| 參考文獻 | 3 | 6.5% | — | 5 | 7.4% | — | — | N/A | 非內容軸 |

**Headline**：以 formatting-robust 的 **body 佔比**看，**本論文章節比例與 catfish 貼合**（ch4 0.99、ch5 0.94、ch3 1.11
皆在 norm 附近，ch1/ch2 反而偏短）。**唯一明顯 proportional OVER ＝ ch6 結論**（且一半是 catfish 結論異常短所致）。
**「整體過長」不成立**；過度投入是**局部**的（摘要＝絕對字數 2×；ch6 重述；§3.2 文字密度）。

> ⚠ **修正 turnkey 初判**：prompt 依 CJK 字數猜「ch3＝最大章＝頭號嫌疑」。**頁數測量推翻此猜**：ch3 絕對頁數
> （11）**少於** catfish ch3（13），body 佔比僅 1.11；ch3 看似大只因本論文總頁少（denominator 效應）＋§3.2 數學密。
> ch3 的最大子節 §3.1 系統模型（5 頁）**與 catfish §3.1 完全相等（5 頁）**＝嚴謹度正當、非冗餘。

---

## (c) 我的論文 section-level 拆解（頁數 + CJK 字數交叉檢查）

| 章 | 節 | 我頁數 | CJK 字數 | catfish 對映節（頁） | 註 |
|---|---|---|---|---|---|
| 前置 | 題名+中英摘要+keywords | 2 | 4668 | abstract 240 英字 | 摘要 EN 479 字＝2× catfish（R6，§e）|
| ch1 | Introduction | 3 | 3174 | ch1（5 頁/1161 字） | 字數 1.43×，佔比 0.79 |
| ch2 | 2.1 Related works | 1 | 1930 | 2.1（2 頁） | |
| | 2.2 Motivation | 1 | 439 | 2.2（3 頁） | 本 §2.2 很短；catfish §2.2 反而 3 頁 |
| ch3 | 3.1.1 Network Model | 2 | 2501 | 3.1 系統模型（5 頁，整體） | |
| | 3.1.2 Geometry & Channel | 1 | 2084 | 〃 | |
| | 3.1.3 SINR & Throughput | 1 | 1874 | 〃 | |
| | 3.1.4 State & Action | 1 | 1725 | 〃 | §3.1 合計 5 頁＝catfish §3.1 完全相等 ✓ |
| | **3.2 Problem formulation** | 3 | **4717** | 3.2（3 頁） | **單節最大 CJK**；頁數=catfish；密度/冗餘問題見 §d |
| | 3.3 Basic idea | 1 | 776 | 3.3（3 頁） | 本節比 catfish 短 |
| | 3.4 Comparison | 1 | 1296 | 3.4（2 頁） | 本節比 catfish 短 |
| ch4 | 4.1 Method Overview | 3 | 2200 | 4.1 data prep（3 頁） | |
| | 4.2 Per-Objective Catfish Training | 2 | 2367 | 4.2 DRL training（**11 頁**） | catfish 方法核心集中 §4.2；本論文方法分散 4.2–4.5 |
| | 4.3 Congestion-Context State Aug | 2 | 1659 | 〃 | |
| | 4.4 Coordinated Beam Allocation | 2 | 2558 | 〃 | |
| | 4.5 Overall Training Procedure | 2 | 2114 | 4.3 EE opt（2 頁） | |
| | 4.6 Ablation Experiment Design | 1 | 1023 | — | |
| ch5 | 5.1 Simulation Setup | 2 | 2196 | 5.1 Setup（~1 頁） | |
| | 5.2 Over-Concentration | <1 | 834 | — | |
| | 5.3 Framework vs Baselines | 3 | 3630 | 5.2 Perf（~11 頁，含圖） | |
| | 5.4 Catfish-Component Ablation | 1 | 1190 | 5.3 Ablation（~1–2 頁） | |
| | **5.5 Capacity Sensitivity** | 3 | **4688** | — | CJK 被 TABLE-5.3/5.5＋數學灌水；**頁數 3 才是實況** |
| | 5.6 Discussion | 1 | 1345 | 5.4 RIS sim（2 頁） | |
| ch6 | 6.1 Summary | 1 | 872 | ch6（1 頁，整體） | 重述段，R2 鯰魚密度熱點 |
| | 6.2 Contributions | 1 | 888 | 〃 | |
| | 6.3 Limitations & Future Work | 1 | 1056 | 〃 | load-bearing，保留 |

---

## (d) 排名 trim-candidate 清單（worst-first；每項＝為何長 + 具體砍法）

> 排序綜合：proportional 超標度 × 絕對量 × 已知冗餘（R2/R6）。**§3.2/§5.5 CJK 雖大但頁數=norm → 屬密度/冗餘
> 而非頁數超標**；以下標明何者是「真頁數超標」何者是「密度/絕對字數」。**不替 USER 砍。**

### #1　摘要（Abstract）— 絕對字數 2×，最該瘦（最確定）
- **為何長**：EN 摘要 479 字 vs catfish 240（2.0×），且為單一大段未分段；一般英文 thesis abstract 慣例 ~200–350，479 本身偏長。此項頁數測不出（密度高、藏在 2 頁前置內）→ 用字數判。
- **具體砍法**：砍向 ~250–300 英字（中文摘要同步）。去背景鋪陳重複句、把方法句的鯰魚連環敘述收一次（R2）、限制句條件化即自然掉字（R1）。**勿動 RED-LINE 數字**（min_cov/EE/k_cap）。
- 與 R6 一致（R6 已執行非圖部分一次性砍長 → 護欄；此處再確認摘要仍是頭號絕對超標）。

### #2　ch6 結論（Conclusion）— proportional 3.84×（body 佔比最高超標）
- **為何長**：本 3 頁/2816 CJK，§6.1 摘要式重述＋§6.2 貢獻＋§6.3 限制；catfish 結論僅 1 頁（無子節）。proportional 倍率高一半來自 catfish 異常短，但本 §6.1 對 ch1/ch4/ch5 的**重述**確實偏厚（R2 標 §6.1/§6.2 為鯰魚密度熱點）。
- **具體砍法**：壓 **§6.1 Summary** 的問題/方法重述（已在 ch1+ch4 講過，結論只需一段收束，不必重走機制）；**§6.2 Contributions 與 §6.3 Limitations 保留**（load-bearing、誠實邊界）。目標：3 頁→~2 頁，重述句鯰魚收斂（R2）。

### #3　§3.2 Problem formulation — 單節最大 CJK（4717），密度/冗餘（非頁數超標）
- **為何長**：頁數 3＝catfish §3.2（3）**相等**，但 CJK 最大。內容＝MOO block（P1/P2/P3 s.t. C1/C2/C3）＋**三個獎勵的完整推導**（r1 角度感知 EE、r2 換手 Ψ、r3 負載平衡）＋MOMDP tuple＋J_w。三獎勵推導**與 ch4 §4.2 per-objective 訓練部分重疊**（同 r1/r2/r3 再被引用/重述）。
- **具體砍法**：§3.2 保留 MOO block＋J_w＋三獎勵的**定義**；把**逐項獎勵的展開推導**壓短、forward-ref 到 ch4 §4.2（r1 EE 的功率/偏軸推導尤其可只留結果式、細節歸 ch4）。屬「壓密度去 ch3↔ch4 重複」，非砍頁。⚠ 觸 ch3↔ch4 耦合，須 track-4 一致處理（連動既有 R8.2 notation）。

### #4　ch1 Introduction — 字數 1.43×（R6），但 proportional UNDER（優先級低）
- **為何（半）長**：EN 1664 字 vs catfish 1161（1.43×，R6 word-level 成立）；**但** body 佔比 0.79＝比 catfish intro **小**的 slice，絕對頁數 3<5。即「字數略多、佔比不超」。
- **具體砍法**：若要對齊 R6 絕對字數，砍 10–20%（去與 ch2 related-work 重疊的背景鋪陳、合併並列子句）；**非 proportional 超標 → 非頭號，optional**。勿與 ch2 一起砍過頭（ch2 已偏短）。

### 不要砍（justified / 已偏短）
- **§3.1 系統模型（5 頁／8184 CJK across 3.1.1–3.1.4）**：與 catfish §3.1（5 頁）**完全相等** → 嚴謹度正當，**非冗餘，勿砍**。
- **ch4 方法（12 頁，body 0.99）**：去 pseudocode 後精準命中 norm，**勿再動**。
- **ch2 related work（body 0.53）＋§3.3/§3.4（各 1 頁，皆比 catfish 短）**：已偏短，catfish 反而投更多；**不是 trim 對象**（如要對齊 norm 是「可加」非「該砍」）。
- **§5.5（CJK 4688）**：被 TABLE-5.3/5.5＋數學灌水，**實頁數 3** 才是實況，**非冗餘**。

---

## (e) R6 摘要/intro 過長的量化確認

| | 本論文 EN | catfish EN | 倍率 | 本比對驗證 |
|---|---|---|---|---|
| Abstract | 479 字 | **240 字**（本次 render 量得） | **2.0×** | ✅ **確認 OVER**（且 479 本身 > 慣例 250；絕對軸，robust） |
| Introduction | 1664 字 | **1161 字**（本次 render 量得，p10–14 逐頁 227/332/330/180/100） | **1.43×** | ⚠ **字數軸成立**，但**頁佔比 UNDER**（7.3% vs 9.3% body）→ 非 proportional 超標 |

- **摘要**：兩法一致 OVER（字數 2×、絕對偏長）→ R6 砍向 250–300 的目標**確認有效**。
- **Intro**：R6 的「1.4×」在**字數軸成立**（catfish intro 1161 字非高估，逐頁實量 ~232 字/頁＝thesis 鬆排版所致，非 extraction noise）。但因本論文整體**排版較密 + ch3/ch4 佔比較重**，intro 的 **body 佔比反而小於** catfish intro → **intro 不是 proportional over-investment**。→ 結論：intro **字數可選擇性砍 10–20%（R6）**，但**不是頁數/佔比超標的頭號項**；別當 ch6/摘要同級處理。

---

## 回報摘要（headline + 排名 + top 砍法）

- **Headline 比例**：總頁 **本 46 vs catfish 68**；正文 **41 vs 54**。以 formatting-robust 的 **body 佔比**，本論文章節比例**貼合 catfish norm**（ch4 0.99 / ch5 0.94 / ch3 1.11；ch1 0.79 / ch2 0.53 偏短）。**「整體過長」不成立**——過度投入是**局部**的。
- **方法學關鍵**：兩 PDF 每頁密度差約 2×（catfish 232 字/頁 vs 本 ~1058 CJK/頁，thesis 鬆排版 vs ris 密排版）→ **裸頁數不可直接比，佔比才準**。
- **排名 trim-candidate（worst-first）**：
  1. **摘要** — 絕對 2×（479 vs 240）→ 砍向 250–300 字。**最確定。**
  2. **ch6 結論** — body 佔比 3.84×、§6.1 重述偏厚（R2 鯰魚熱點）→ 壓 §6.1 重述，3 頁→~2 頁；§6.2/§6.3 留。
  3. **§3.2 問題定式** — 單節最大 CJK（4717）、三獎勵推導與 ch4 §4.2 重疊 → 壓推導、forward-ref ch4（密度/去重，非砍頁；觸 ch3↔ch4 耦合）。
  4. **ch1 Introduction** — 字數 1.43×（R6）但佔比 UNDER → optional 砍 10–20%，非頭號。
- **修正初判**：prompt 的「ch3＝頭號嫌疑」被頁數測量推翻——ch3 絕對頁數少於 catfish ch3，§3.1 系統模型與 catfish 完全相等＝正當嚴謹度。**真正該瘦的是摘要與 ch6 結論，不是 ch3。**
- **不要砍**：§3.1 系統模型（=catfish）、ch4（已命中 norm）、ch2/§3.3/§3.4（已偏短）。
