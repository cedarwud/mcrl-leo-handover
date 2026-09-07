# 論文長度/結構逐章比對 vs catfish house-norm — turnkey prompt（2026-06-30）

> 貼到**新對話**執行。此 pass = 純**唯讀分析 + 記錄**：把「我的論文」逐章節與指導教授前作
> `catfish/thesis.pdf`（英文、house norm）比長度與比例，**找出我這邊「內容過多」的章節**，讓 USER 決定哪裡要砍。
> **不改任何論文內容/圖/build 檔，只產出一份比對記錄 doc。** 不碰 git / G1 / env。

## 啟動讀（依序，最少）
1. 本檔。
2. `thesis-mc/WRITING-RULES.md` **R6**（abstract/intro 長度；已知本 EN abstract ≈ catfish 2×、intro ≈ 1.4×）。
3. `CURRENT-STATE.md` top（確認 live thesis = `thesis-mc/`，非 dead `thesis/`）。

## 目標
跨語言（我=繁中 body / catfish=英文）逐章比對，**用「頁數 + 章節佔全文比例」** 當度量（**不要**用裸字數 vs 詞數，
中文比英文密）。輸出：哪些「我的章節」相對 catfish norm **過長 / 過度投入**，附**具體可砍處**（但**不替 USER 砍**）。

## 我的論文（live = `thesis-mc/`；英文 heading + 繁中 body）
| 檔 | 章節 |
|---|---|
| `mc-modqn-base.md` | 前置(title/Abstract EN/中文摘要/keywords) + ch1 Introduction + ch2 (2.1 Related works, 2.2 Motivation) + ch3 Preliminaries (3.1.1 Network Model / 3.1.2 Geometry & Channel / 3.1.3 SINR & Throughput / 3.1.4 State & Action / 3.2 Problem formulation / 3.3 Basic idea / 3.4 Comparison) |
| `ch4-method.md` | ch4 (4.1 Method Overview / 4.2 Per-Objective Catfish-Style Training / 4.3 Congestion-Context State Augmentation / 4.4 Coordinated Beam Allocation / 4.5 Overall Training Procedure / 4.6 Ablation Experiment Design) |
| `ch5-experimental-result.md` | ch5 (5.1 Simulation Setup / 5.2 Over-Concentration / 5.3 Framework vs Baselines / 5.4 Catfish-Component Ablation / 5.5 Capacity Sensitivity / 5.6 Discussion) |
| `ch6-conclusion.md` | ch6 (6.1 Summary / 6.2 Contributions / 6.3 Limitations & Future Work) |

- **渲染 docx PDF（47 頁）= `scratch/conversion-test/mc-thesis-ris.pdf`**（章節→頁映射用；若舊則先 `bash thesis-mc/tools/build_ris.sh` 重建 — build 一律走此 skill/wrapper，勿直接 pandoc）。
- **已量好的 per-section 字數（CJK 字元 proxy；ch5 被表格/math 灌水，交叉檢查用、勿當主度量）**：
  前置(摘要等) 4668 · ch1 3174 · ch2.1 1930 · ch2.2 439 · ch3.1.1 2501 · ch3.1.2 2084 · ch3.1.3 1874 · ch3.1.4 1725 ·
  **ch3.2 Problem formulation 4717** · ch3.3 776 · ch3.4 1296 · ch4.1 2200 · ch4.2 2367 · ch4.3 1659 · ch4.4 2558 ·
  ch4.5 2114 · ch4.6 1023 · ch5.1 2196 · ch5.2 834 · ch5.3 3630 · ch5.4 1190 · **ch5.5 4688** · ch5.6 1345 · ch6.1 872 ·
  ch6.2 888 · ch6.3 1056。Totals：mc-modqn-base 26112 · ch4 12394 · ch5 14326 · ch6 2936。
  → 初判 **ch3（系統模型 8.2k + 問題定式 4.7k ≈ 15k）= 最大章**，是頭號嫌疑；摘要/intro = R6 已知。

## catfish norm = `catfish/thesis.pdf`（68 頁、英文；同指導教授 陳裕賢前作）
- 讀 TOC/目錄（前 ~10 頁內）→ 章+節清單 + 頁範圍 → 每章頁數。再 content-skim 每章（讀代表頁，**Read 一次 ≤20 頁**）抓深度/結構。
- **不同主題**（catfish-DRL / RIS）→ 按**角色**對映（intro / related-work+background / system-model 或 preliminaries / method / experiments / conclusion），**非**逐主題。
- `catfish/6pages.pdf` = 舊短稿，**忽略**；只用 `thesis.pdf`。

## 方法
1. catfish TOC → 每章頁範圍+頁數；再各章 content-skim 抓深度/結構。
2. 我的論文：`pdftotext -f N -l N scratch/conversion-test/mc-thesis-ris.pdf -` 逐頁找章/節邊界 → 我的每章頁數（用上面字數交叉檢查）。
3. 比對（**頁數 + 佔全文比例 %**；明寫此法+理由）：
   - 主表：`| 角色/章 | 我頁數 | 我 %(/47) | catfish 頁數 | catfish %(/68) | 比例比 (我%÷catfish%) | 判定 OK/OVER/UNDER | 備註 |`。
   - 我的論文 section-level 拆解（哪些小節是主體）。
   - 找出「我的」OVER-LONG 章/節 = 比例 ≫ catfish norm，或內容明顯過細/重複。**worst-first 排名。**
   - 每個 over-long 項：**為何長**（什麼內容撐的）+ **具體可砍建議**（砍/壓哪段；e.g.「3.2 問題定式 4717 — MOO block + 各目標獎勵推導可壓，catfish 問題定式僅約 X 頁」）。**不替 USER 砍。**
4. 區分：過長但**有正當理由**（如系統模型嚴謹度）vs 過長**來自冗餘**。

## 輸出
- **寫** `thesis-mc/LENGTH-COMPARISON-vs-catfish-2026-06-30.md`：(a) 方法註 + 兩論文 totals；(b) 主比對表；(c) 我的 section-level 拆解；(d) **排名 trim-candidate 清單**（每項 理由 + 具體砍法）；(e) 量化確認 R6 摘要/intro 過長。
- 回報：排名清單 + headline 比例 + top 3-5 砍法。

## 紀律（binding）
- **唯讀論文內容**；唯一新建檔 = 比對記錄 doc。**不改** `thesis-mc/*.md`／圖／tooling／git／G1／env。
- 誠實量測 — 真讀 PDF、真數頁，**勿杜撰頁碼**；catfish 若雙語或 TOC 不明，照實說。
- 焦點 = 長度/結構/比例（非 claim/RED-LINE review）。
- build docx（若需）走 `build-mc-thesis-docx` skill（= `build_ris.sh`），勿直接 pandoc/md2docx（guard hook 會擋）。
