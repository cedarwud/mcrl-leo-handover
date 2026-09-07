# Multi-Catfish MCRL V0.23 中文論文 method-draft change report

日期：2026-09-05  
artifact：`chinese-word-v023-lcsrs-20260905-r2`  
定位：current method-aligned draft；不是 empirical-final，也不是 Ch5 結果定稿。

## 已更新且可方法層凍結

- 以 `.scratch/chinese-word-r1-symbols-20260905-r1/input/thesis-mc/` 完整複製成 r2 source mirror，保留 `tools/`、`figures/`、cover 與其餘素材；本次只在 r2 mirror 編輯 Markdown。
- `mc-modqn-base.md`：更新摘要、Ch1 貢獻、Ch2 定位與 Ch3 交叉敘事，使現行方法明確採 Main-only network ratio-of-sums EE、恰好三個獨立 `Q_1,Q_2,Q_3`、共同 safe mask、無權重相加、一次 masked row-wise argmax、單一 Main action。既有 Ch3 物理鏈與 EE 公式未重寫。
- `ch4-method.md`：重建 4.1–4.7 方法結構，包含 native candidate/state/mask、shared current-slot counterfactual、C1/C2/C3 route roles、two-user LC-SRS 四 profile teacher、`z_{3,i}=e_i+Psi/2` 與 scoped identity、deterministic relational C3View、shared 67-to-64-to-64-to-1 scorer、route-specific learning 與 single-pass deployment boundary。舊 six-Q、雙代理、舊 replay/discount/reward-shaping active story 與舊圖引用已移除。
- `ch6-conclusion.md`：只更新方法摘要、貢獻與限制，明示 efficacy 仍待 Ch5，保留 current method-aligned draft 定位。
- `notation-table.md` 與 `active-symbol-table-v023-20260905.md`：新增 active Multi-Catfish V0.23 section 10.13；舊 V0.3 bookkeeping sections 10.8、10.9、10.12 明確標成 historical/retired，不作 active claim。
- `SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md`：記錄新增符號、碰撞裁決、禁止多字母上下標掃描與 composite-index 分類。
- 未新增或修改引用文獻；未執行 simulator、TLE、training、matched pilot 或 TEST split。

## 仍 provisional

- C2 僅寫為目前固定的 OPS-3 projected-persistence route，狀態是 present but empirically unqualified；未沿用舊 handover objective，也未自行發明替代 C2。
- C1 qualification、C2 qualification、C3 learnability、composition benefit、EE efficacy 與 FULL-over-ablation ordering 均未宣稱；本文沒有結果性結論。
- C3 method core 的受限 teacher target、student interface 與 exact scoped identity 已寫入方法草稿，但 gate outcome 尚未開啟。
- `STOP_PHYSICS` 會重開 C3 mechanism；`STOP_OBSERVABILITY` 只重開 state/learner；`REDESIGN_INTERFACE` 只重開 composition descriptors；只有 `GO` 才允許完整 implementation subsection。上述 gate token 不塞入正文。

## 未改且已知 stale（Ch5）

`ch5-experimental-result.md` 由 r1 複製後未改，且前後 byte-level SHA-256 均為：

`4070095c79854d10e7a9735a4e0d8deff326d25c76ca9dd06f90d89e1c7f3052`

比對來源：

- r1：`.scratch/chinese-word-r1-symbols-20260905-r1/input/thesis-mc/ch5-experimental-result.md`
- r2：`.scratch/chinese-word-v023-lcsrs-20260905-r2/ch5-experimental-result.md`
- `diff -q`：`SAME`

因此 Ch5 內仍可能出現舊設定或舊結果敘事；它們是保留的 provenance/stale area，不被本次方法更新重新解讀，也不代表 V0.23 efficacy。

## 圖待補

Ch4 舊 objective-network、雙代理、六-Q 圖與舊圖說已移除；本版 Ch4 沒有 placeholder 或舊圖引用。待後續 gate/authoring decision 後再補一張與 C1/C2/C3、shared mask、single argmax、teacher/student boundary 對齊的新方法圖。Ch3 既有物理圖與 Ch5 結果素材未改。

## QA 結果

- Build：使用 r2 mirror 的 `tools/build_ris.sh`；產生 Word 後套用 canonical cover、A4 與 RIS margins。
- Word：[`mcrl-thesis-ZH-v023-method-draft-20260905.docx`](mcrl-thesis-ZH-v023-method-draft-20260905.docx) 存在，ZIP integrity 通過（`unzip -t`）；原生 `m:oMath=421`、`m:oMathPara=42`。
- PDF：[`mcrl-thesis-ZH-v023-method-draft-20260905.pdf`](mcrl-thesis-ZH-v023-method-draft-20260905.pdf) 存在，LibreOffice 預覽為 34 頁 A4；Ch4 pages 17–22、Ch6 pages 30–31 與 references page 32 已 render 並視覺檢查，contact sheet 在 `renders-final/contact-sheet-relevant.png`。
- DOCX XML naked-LaTeX scan：`$`、`\\tag`、`\\begin` 均為 0；公式保留為 native OMML。LibreOffice 轉 PDF 會在 OMML matrix equation number 顯示已知 `¿`/`(...)` glitch（工具 README 已記錄），所以 PDF 只作預覽，不能宣稱 MS Word 最終視覺驗收。
- Active symbol single-letter audit：`ref, src, dst, beam, sat, own, nf, joint, base, cand, main` 在上下標位置全部 0；Ch4 composite forms 已分類為 atomic components、quantifier 或 description-only operator。
- Ch4 figure scan：Markdown image 0、figure reference 0；未留下會誤導 current method 的舊六-Q圖。
- Obsolete-story scan：live updated chapters 無 literal six-Q positive story，也無 current double-agent deployment positive story；保留的 legacy/double-agent 字樣均是歷史定位或否定邊界。
- `genre_scan.py ch4 ch6`：Ch4 機械檢查全數通過；Ch6 僅有 1 個預期的段首自稱警告（貢獻段）與 1 個同源自稱計數，且 Ch6 參考長度標為不可用，不構成方法或內容 blocker。
- `MANIFEST.sha256` 覆蓋本 artifact 目錄中的產出檔（manifest 自身除外）。

目前沒有阻止交付的 blocker；未完成的 MS Word 實機視覺驗收、Ch5 更新與結果性結論，均按上述界線留待後續授權流程。
