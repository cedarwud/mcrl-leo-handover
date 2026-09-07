# MCRL 論文入口

> 狀態：**CURRENT FRONT DOOR**（2026-08-17）。`thesis-mc/` 是論文來源、
> 建置工具、三份 DOCX 與 6-page 材料的唯一現行入口。

## 快速開啟

- [中文版 DOCX](outputs/mcrl-thesis-ZH.docx)
- [英文版 DOCX](outputs/mcrl-thesis-EN.docx)
- [中英雙語版 DOCX](outputs/mcrl-thesis-bilingual.docx)
- [三版本共用的封面來源 DOCX](outputs/thesis-cover.docx)
- [建置與一致性 receipt](outputs/mcrl-thesis-build-receipt.txt)

`outputs/` 只有在三份 DOCX 與 receipt 由同一次 `build_all.sh` 成功發布時，
才可視為一組與當時來源一致的交付物。`thesis-cover.docx` 是輸入來源，
不是生成結果：三條建置流程都會用它完整替換 Markdown 所產生的封面文字；
缺少它或封面浮水印與論文資產不一致時，建置會直接失敗。

> **封面凍結（USER 2026-08-10）。** 這次換上的 `thesis-cover.docx` 題名、封面文字與版面均已
> final/frozen。後續建置只能原樣沿用這份既有 frozen cover，不得編輯、重生、改題、翻譯掃詞或重新設計
> 封面；除非 USER 日後明示解凍，否則不再動封面。

從 repo root
重建與驗證：

```bash
bash thesis-mc/tools/build_all.sh thesis-mc/outputs
.venv/bin/python -B thesis-mc/tools/verify_three_docx.py thesis-mc \
  thesis-mc/outputs/mcrl-thesis-ZH.docx \
  thesis-mc/outputs/mcrl-thesis-EN.docx \
  thesis-mc/outputs/mcrl-thesis-bilingual.docx
```

目前有效的 source-set SHA-256、三份輸出雜湊與結構驗證結果，以
`outputs/mcrl-thesis-build-receipt.txt` 的最近一次成功建置紀錄為準。

## 論文來源與生成關係

> **正文修改前必讀：** [`WRITING-GUIDE.md`](WRITING-GUIDE.md)。它是現行的讀者優先寫作準則，
> 規定章節分工、符號首次出場、段落順序、實作細節邊界與交稿前讀者測試。
> `WRITING-RULES.md` 主要保存較早的裁決與技術脈絡，不可用歷史寫法覆蓋這份現行準則。

- 中文主來源：`mc-modqn-base.md`、`ch4-method.md`、
  `ch5-experimental-result.md`、`ch6-conclusion.md`。
- 英文主來源：`en/*.en.md`。
- 共用來源：`REFERENCES.md`、`notation-table.md`、
  `TRANSLATION-GLOSSARY.md`、`assets/` 與 `figures/`。
- 封面頁來源：`outputs/thesis-cover.docx`。它只主宰三份最終 DOCX 的封面頁；
  摘要起的正文仍由上述 Markdown 來源生成。
- `en/bilingual/bi-*.md` 是由中英文主來源生成的建置材料，不是第三套
  獨立內容權威。
- `tools/` 是三份 DOCX 的唯一現行建置與結構驗證流程。

現行符號規則：集合、索引域、可行動作域、經驗池與批次一律使用一般大寫
符號加必要的短上下標，例如 `D_M`、`D_CF` 與 `B_I`。

集合本身一律使用花體（`\mathcal{U}`、`\mathcal{S}`、`\mathcal{V}`、
`\mathcal{C}`、`\mathcal{F}`），集合大小使用同字母正體大寫
（`U`、`S`、`V`、`C`、`F`，例：`\mathcal{U}=\{1,\ldots,U\}`）；不使用
`N_U` 這類前綴記法，也不使用 `|U|`。此規則於 2026-08-20 由簡化 EE 符號表修訂，
2026-08-21 同步至本檔、`WRITING-GUIDE.md`、中英正文、`notation-table.md`、
`tests/test_angle_aware_ee_manuscript_semantics.py` 與 `/` legacy simulator 前端；
先前「不得使用 `\mathcal` 花體」的規定已作廢。理由：花體集合＋正體大寫基數是
MODQN、HOBS 與一般 RL 文獻的通用慣例。完整對照見 `notation-table.md`，累積規則見
`WRITING-RULES.md` 最上方的 current override。

目前嵌入第二至四章的 10 張非結果圖均列入後續全面重畫。本輪正文整理以文字、
符號、公式與演算法為準，不修改既有圖檔，也不把舊圖內容當成現行科學語意的權威；
重畫時再依已定稿的正文與符號表同步圖中標示及圖說。

中文正文統一使用「低軌衛星」；唯一例外是上述已凍結、不得再改的封面原件，
即使其既有題名用字不同，也不能藉由一般翻譯掃詞改寫。

論文內容與輸出搬到同一入口不會改寫 Chapter 5；Chapter 5 的結果更新仍是
另行、由使用者核准的 empirical 工作。

## 6-page 材料

`six-pages/` 保留最新可恢復的舊稿、六頁 PDF、參考文獻、建置腳本與實際
引用圖。檔名中的 `donor-` 是有效邊界：目前沒有一份已與現行 angle-aware
EE 論文同步的正式 6-page paper。

- [donor Markdown](six-pages/donor-mcrl-6pages.md)
- [donor PDF](six-pages/donor-mcrl-6pages.pdf)
- [狀態與差異說明](six-pages/README.md)

## 權威邊界

- 目前正式的單一 SINR EE 公式（**論文正文、三份 DOCX 與 production Family-B runtime 已完成 executable parity；fresh calibration 尚未構成訓練或結果證據**）：
  [`../docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-presentation-spec.md`](../docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-presentation-spec.md)。
  新主鏈為 `position -> theta -> H_(u,s,v)G^T(theta) -> angle-aware p -> single SINR -> R -> P^N -> eta_(u,s,v)`；
  不再以目標 SINR 反推功率，也不在概念主鏈展開 cap `min/max`。
- 正式 EE 專用符號表（**已與論文正文及 DOCX 完成符號 parity**）：
  [`../docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md`](../docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md)。
- 舊版完整公式、runtime 與既有實驗證據（**archived provenance only**）：
  [`../docs/ADR-003-canonical-ee-closure.md`](../docs/ADR-003-canonical-ee-closure.md)。
- 現行論文來源、figure provenance、建置與輸出：本目錄。
- 一次性整理紀錄：
  [`../archive/manuscript-cleanup-2026-08-09/`](../archive/manuscript-cleanup-2026-08-09/)。
- 已移除的 `manuscript/`、`conf-demo/` 與 `scratch/conversion-test/` 都不是
  有效入口；需要追溯時使用 Git checkpoint 與 archive 紀錄，不要重建舊路由。
