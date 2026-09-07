# 純中文版 Word 論文：Multi-Catfish 穩定內容差異圖

日期：2026-09-05  
狀態：`BLOCKED_SAFE_DELTA_ONLY`（本次不改論文、來源或符號表）

## 1. 範圍與處置

本差異圖只服務於純中文版 Word 論文的後續回寫。未修改英文稿、Markdown 論文來源、PPTX／投影片、圖檔、網頁套件或獨立符號表，也未執行建置、模擬、訓練或 TEST。

目前不能安全直接改 Word：

- 候選檔是 `/home/u24/papers/modqn-paper-reproduction/thesis-mc/outputs/mcrl-thesis-ZH.docx`，屬於由來源 Markdown 產生的輸出物，不是權威來源。`CURRENT-STATE.md` 與 `thesis-mc/tools/build_ris.sh` 都指向 `mc-modqn-base.md`、`ch4-method.md`、`ch5-experimental-result.md`、`ch6-conclusion.md` 等來源鏈。
- 該 Word 輸出物本身相對於 sibling checkout 已是 dirty；來源中的 `ch4-method.md`、`mc-modqn-base.md`、`WRITING-GUIDE.md`、`notation-table.md` 及 build receipt 也有未提交變更。直接改二進位輸出會繞過來源鏈並覆蓋或失去現有 WIP。
- sibling checkout 為 `chore/worktree-cleanup-2026-08-04`，HEAD `8cb4aa66`，另有較廣泛的 staged／unstaged／untracked WIP。`ps` 快照顯示仍有多個 `claude --resume`、`codex`、Astra 與 AGY 工作程序；未發現 Word/LibreOffice writer。`tmux list-sessions` 因權限回報 `Operation not permitted`，故不能把 live-writer 狀態宣稱為已完全排除。
- Word 的建置輸入不含 `thesis-mc/notation-table.md`；該檔是停止維護的 stub，並指向獨立的 `docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md`。因此本次沒有「同一 Word 檔內的權威符號表」可安全更新；獨立符號表依指示不動。

結論：保留所有現有 WIP，等 sibling owner 明確確認來源與回寫窗口後，才可由來源重新產生純中文版 Word。不可用另一種格式代替 Word 編輯。

## 2. 可回寫的穩定中文措辭

以下只可作為後續權威回寫的 bounded prose；不固定任何 C3 估計量、相容性門檻、參考中心化、Q3 標籤／學習式、lambda 更新式、數值、接受規則或偽代碼。

### 網路與訓練邊界

> 本方法的網路拓撲固定為恰好三個 Q 網路 (Q_1,Q_2,Q_3)。C1、C2 與 C3 是訓練階段的機制／資訊視角，訓練時共同服務於最終的 ratio-of-sums 能效目標；它們不是三個獨立的部署決策器，也不構成「三個頭皆已提升能效」的結果宣稱。

### C3 的暫定角色

> C3 目前僅以空間資源共享／波束整併的暫定訓練視角描述，用於評估分母側的能效節省。其可部署估計量、學習來源與公式仍在裁決中，本文不將目前候選式或數值寫成定稿。

### matched counterfactual 邊界

> C3 的訓練比較限於 matched counterfactual：固定同一動作前狀態、同一已承諾背景與相同比較條件。此邊界只約束訓練時的配對歸因，不推出部署時的聯合效果或 C3 成效。

### 唯一部署動作

> 部署時只保留 Main。對每位使用者，在同一個合法且服務安全的動作遮罩下，由 Main 直接以 (Q_1+Q_2+Q_3) 做一次 argmax 並執行唯一動作；不另行執行 Catfish 動作，也沒有拍賣、協調器或訓練後覆寫。

### 論文主張上限

> 在 C3 裁決完成前，本文最多將 Multi-Catfish 稱為方法設計與開發階段證據。不得宣稱 Q3 已學成或可部署、三個 Q 頭皆改善 EE、C3 已具有效能，亦不得把尚未通過 EXPECTED_ZR gate 的學習流程或候選式寫成定稿。

上述措辭刻意不把 C3 描述為 interference relief 或 victim-rate improvement，也不指定任何 `lambda'`、ZR 公式或 C3 learner/source formula。

## 3. 純中文版 Word 的精確定位與處置

行號是以 `pandoc ... -t plain | nl -ba` 取得的 Word 純文字追蹤行號，不是 DOCX XML 行號。

| Word 位置 | 現況／安全差異 | 本次處置 |
|---|---|---|
| 摘要，plain lines 38–40 | 仍寫成 Main 與 Catfish 各一組三目標 MODQN，且帶有舊三目標敘事。 | **待來源 owner 回寫**：可改成「恰好三個 Q 網路、C1/C2/C3 僅為訓練機制、共同指向 ratio-of-sums EE」；不得加入 Q3 已學成、三頭增益或任何 C3 公式／數字。 |
| 緒論貢獻，plain lines 61–72 | 舊文案把 MCRL 說成訓練經驗／reward shaping，部署為每使用者 argmax。 | **待回寫**：只保留方法設計與開發證據上限；部署句改用第 2 節的 Main-only 唯一動作措辭。 |
| 背景與動機，plain lines 97–127、138–145 | 內部 MCRL 描述仍是兩個 agent、每個 agent 三個目標／Q 網路。 | **待回寫且需 owner 審核**：移除過時的兩 agent 部署含意；不要藉此重寫相關工作或引入新符號。 |
| 第 3 章目標／P1–P3，plain lines 493–514 | 含舊的 EE、handover、load-balance 目標與 reward 公式。 | **不得在本次改動**：C1/C2/C3 與新 Q3 learner/source formula 尚未定稿；保留公式，列為待裁決的來源衝突。 |
| 第 4 章 4.1，plain lines 706–714 | `Q_1,Q_2,Q_3` 的三網路事實可保留，但旁邊仍有舊 weighted multi-objective 與兩 agent shaping 敘事。 | **主要穩定差異位置**：owner 回寫時以第 2 節「網路與訓練邊界」取代過時 framing；不要保留權重總和作為部署規則。 |
| 第 4 章圖說，plain lines 727–729 | 圖說寫成 Main/Catfish 各含三個目標 Q 網路。 | **本次不改**：圖檔與圖說同步在禁改範圍；待圖／來源 owner 一起更新，不能單獨修 Word 文字。 |
| 第 4 章 4.3，plain lines 740–843 | 含兩 agent、舊 reward shaping、ACRM 與 (Q_j^M/Q_j^F) 公式。 | **不得定稿化**：最多替換 bounded overview；C3 僅寫空間資源共享／波束整併的暫定視角與分母側節省評估，所有估計量、門檻、reference、Q3 式與 learner 細節留白。EXPECTED_ZR gate 及後續裁決完成前不得補式。 |
| 第 4 章 4.4–4.5，plain lines 845–962 | 含舊 ACRM、競爭 reward、兩 agent 偽代碼、TD 更新與縮放細節。 | **不得在本次改動**：使用者明確禁止定稿未解 C3 偽代碼／接受規則／learner；整段需來源 owner 在裁決後協同重寫。 |
| 第 4 章部署，plain lines 964–965 | 現有句子保留 Main-only，但引用舊 weighted aggregate。 | **主要穩定差異位置**：owner 回寫為同一合法／服務安全遮罩下，Main 以 (Q_1+Q_2+Q_3) 一次 argmax、執行一個動作；不加拍賣、協調器或 post-training override。 |
| 第 5 章，plain lines 967 起 | 實驗設定、數字、表格與結果。 | **NO TOUCH**：不改任何 Chapter 5 數字、接受規則、結果或成效主張。 |
| 第 6 章總結／貢獻，plain lines 1198–1217 | 仍將三目標寫成 EE／handover／load balance，並說兩 agent 各含三個 Q 網路。 | **待第 4 章來源回寫後同步**：只保留三 Q 網路、訓練機制、Main-only 一動作與開發證據上限；不得新增 efficacy 或 C3 learner claim。 |

## 4. 符號檢查與未決接縫

- 允許的新增紙面記號僅為既有單字母形式中的 `Q_1`、`Q_2`、`Q_3`；部署合併必須直接寫成 (Q_1+Q_2+Q_3)。不新增多字母下標、C3 估計符號、ZR 公式或 lambda 數值。
- Word 內現有的 (Q_j^M/Q_j^F)、(D_M/D_F) 等舊兩 agent 公式不得被局部改名或重新解釋成新架構；必須等權威來源整段決定後協同重建。
- `thesis-mc/notation-table.md` 是外部 stub，且真正指向獨立符號表；本次不改。符號表同步是 pending delta，不是已完成項。
- C3 的未決接縫為 EXPECTED_ZR gate → learner/episode training 的先後與通過條件，以及其後的估計量／標籤／來源式。這些未決項不應出現在本次 Word 措辭中。

## 5. 已做的靜態檢查

- 讀取 sibling `CURRENT-STATE.md`、`WRITING-GUIDE.md`、`thesis-mc/tools/build_ris.sh`，確認 Word 是生成輸出、來源鏈與符號表路徑。
- 以 `git status`／`git diff --numstat` 檢查 sibling 的 dirty overlap；以 `file`／OOXML 清單確認候選檔為 DOCX，並以純文字抽取定位上述段落。
- 以 `ps` 檢查 live writer／C3 adjudication 的程序快照；未終止、附加或改動任何程序。`tmux` 檢查受權限限制，已在第 1 節揭露。
- 本次只新增本差異圖；未執行 `build_all.sh`、`build_ris.sh`、模擬、訓練、TEST 或任何 heavy work。後續若要回寫，先由 owner 清理／確認來源 authority，再只產生純中文版 Word 並做 DOCX 靜態與版面檢查。
