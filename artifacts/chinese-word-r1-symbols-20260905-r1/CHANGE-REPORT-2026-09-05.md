# 純中文版 Word／R1 紙面記號更新報告

日期：2026-09-05（Asia/Taipei）  
狀態：完成；本報告對應的 Word 與符號表均為版本化副本。

## 1. 交付範圍

本次只在私有 mirror 內更新新版 R1 角度感知 EE／功率的紙面記號，並以
現有 source-first 工具建立純中文版 Word。沒有修改外部 thesis source、
外部 active symbol table、共享 authority、英文稿、簡報、C2／C3 設計或任何
訓練／模擬資料。

私有 mirror：

/home/u24/papers/mcrl-leo-handover/.scratch/chinese-word-r1-symbols-20260905-r1/

輸入快照（建立 mirror 時的 SHA-256）：

| 檔案 | SHA-256 |
|---|---|
| 外部 thesis-mc/mc-modqn-base.md | 1e9e6e31f0da20ef541aaed8695a1f85af229464bde83671e94acdfc35a84b29 |
| 外部 thesis-mc/ch4-method.md | bea6c70e83b402b168ffcd27c36d56b1c0c744d00a9f8d29eb73144831adb945 |
| 外部 thesis-mc/ch5-experimental-result.md | 5fde8b6550698d05df5801d7d02a3b52659978b8f6039c981bc64f98ec5aa739 |
| 外部 active symbol table | 82da73640d0184abda86f1a1f792ffab35cc1339f81372d10a52b4a5e947a49b |

## 2. 紙面記號映射

依 R1-SINGLE-LETTER-NOTATION-MAPPING-2026-09-05.md，R1 主鏈採用：

| 原紙面記號 | 本版紙面記號 |
|---|---|
| theta_{3dB} | theta_3（全 3 dB HPBW；單邊角為 theta_3/2） |
| p_{max} | p^{+} |
| p_{sat} | p^{s} |
| xi_{max} | xi^{+} |
| N^{act}_s | N^a_s |
| P_{cir}、P_{BB} | P^c、P^b |
| P_{RF}、P_{DC} | 不另建立紙面符號；分別用 p_{s,v}、P^p_{s,v} |
| G_{R,min}、G_{R,max} | G^R_-、G^R_+ |
| theta^R_{min} | theta^R_- |
| A_{zen} | A^z |
| I^{intra}、I^{inter} | I^i、I^x |
| B_{sys} | B^g |
| NF、BO | N_f、b_o |
| HOBS provenance L_{fs}、L_{sc}、L_{sf} | L_f、L_c、L_s |

原始 MODQN-only 公式沒有被重寫。P_RF／P_DC 也沒有被當成新增的
paper-facing 符號；正文改以 p／P^p 表達。符號表副本的 R1 overlay 保留
舊記號只作映射對照，不能解讀為 active formula。

## 3. 文件更新

- mc-modqn-base.md：更新 R1 系統模型、角度型樣、接收型樣、功率、SINR、
  throughput、固定功率、總功率與鏈路 EE 的紙面記號；補充 theta_3 是全
  波束寬、單邊半功率角為 theta_3/2 的說明。
- ch4-method.md：只更新 R1 角度參數在方法章中的交叉引用為 theta_3。
  原有 MODQN／MCRL 訓練與 Catfish 內容未改寫。
- ch5-experimental-result.md：只做 R1 紙面記號對齊；所有實驗數字與結果
  文字的數值順序維持不變。
- ch6-conclusion.md：未修改。
- active-symbol-table-r1-20260905.md：由更新後的私有 active table 複製；
  新增 theta^R_- 的 active 定義，避免正文使用而表格漏列。

本次沒有新增或改寫 C2、C3、Expected-ZR、lambda、learner formula，
也沒有加入任何 efficacy claim。

## 4. 驗證結果

- DOCX unzip -t：通過，無壓縮檔錯誤。
- Word 內含原生 OMML：m:oMath = 545、m:oMathPara = 43。
- OMML math style：p = 1995、bi = 47、b = 1；向量／粗斜體數學格式仍
  保留在 OMML，而非被攤平成普通文字。
- 四份中文 source 的 R1 舊記號掃描：NONE。
- active symbol table 主體（排除 overlay 的舊→新對照欄）舊記號掃描：
  NONE。
- 18 個 R1 active tokens 在 source chain 與 symbol-table body 的正規化對齊：
  18/18 PASS。
- R1 紙面 scope 的多字母上下標掃描：NONE。u,s,v、N_f、b_o 等單字母
  索引及 circ／max 等 TeX 運算子不被當作多字母符號。
- Chapter 5 數值 token sequence：原稿與 mirror 均為 280 個，順序完全相同；
  行數均為 96。這只驗證本次沒有改動數值，不代表重新驗證實驗結果。
- 以 source-first 工具建立版本化 DOCX 後，轉出 A4 PDF 共 39 頁；已視覺
  抽查含式 (3.7)–(3.17) 的第 8–13 頁，未見本次 theta_3 替換造成的裁切
  或溢出。

基線比較另以未修改的外部原稿建立只讀 PDF；既有方程標籤的 raw LaTeX
片段在基線與本版都存在，屬既有 ris_preprocess／Word 轉換排版現象，不是
本次記號替換新增的錯誤。

## 5. 交付檔案

- mcrl-thesis-ZH-r1-symbols-20260905.docx：版本化純中文版 Word。
- active-symbol-table-r1-20260905.md：版本化符號表副本。
- renders/mcrl-thesis-ZH-r1-symbols-20260905.pdf：本版 Word 的檢查用 A4
  render。
- CHANGE-REPORT-2026-09-05.md：本報告。
- CHECKSUMS.sha256：上述交付檔案的 SHA-256 清單；已以 sha256sum -c 通過。

建置與檢查均在本 repo 的私有 mirror／artifact 路徑完成；外部原稿仍保持
未寫入狀態。
