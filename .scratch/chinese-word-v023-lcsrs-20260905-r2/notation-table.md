# 符號表 —— 已併入 V0.23 版本化紙面權威副本(2026-09-05)

> ## ⛔ 本檔仍不是獨立符號來源,不要在這裡新增記號。
>
> 本次純中文版 Word 建置使用 artifact 目錄的版本化副本:
> [`../../artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md`](../../artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md)
> (`2026-09-05 V0.23 LC-SRS active method extension`)。原始 R1 active table
> 保持唯讀；此檔只作 source-chain 指標。
>
> - 第 1–9 節:EE 鏈路、通道、功率、SINR 的符號
> - **第 10 節:論文全篇符號**(原本就是本檔的內容,含記號原則與第三、四章符號)
> - 第 10.13 節:V0.23 C1/C2/C3、LC-SRS teacher／student 與 single-pass deployment active symbols
> - 文末:汰換紀錄(已移除的符號與依據)
>
> **併入理由**:兩份符號表並存會分歧。2026-08-21 的一輪清理中,
> 本檔與權威版對同一批符號(`v_max`、`F`／`𝓕`、`N(t)`、`R̃`、`m^e`、`Δ_s`)
> 的狀態一度不一致,而本檔另有 30 處 `F` 需逐一判斷語意。
> 為避免日後再次取到過時定義,合併為一份。
>
> **本檔不在論文 build 內**(`tools/build_ris.sh` 只組 `mc-modqn-base`、`ch4`、`ch5`、
> `ch6`、`REFERENCES` 五個檔),故併入不影響 docx 產出。

## 其他符號來源的角色

| 檔案 | 角色 |
|---|---|
| `docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md` | **唯一符號權威** |
| `system-model-refs/system-model-formulas.md`(+ `paper-source/system-model/` 副本) | **公式推導鏈與引用溯源**;符號以權威為準。⚠ 其終端類別釘定(handheld `0 dBi`／NF `9 dB`)已判定過時,見該檔檔首 |
| `~/demo/leo-beam-sim/src/explain/model/canonicalTermMap.ts` | **模擬器前端實際顯示的符號**。⚠ 2026-08-22 抽查發現與論文不一致(`\theta_{u,b}` 少一下標、`\widetilde{P}^{DL}_b` 為舊記號、`\eta^{PA}` 與論文的 EE `\eta` 同字母不同義),待對齊 |
