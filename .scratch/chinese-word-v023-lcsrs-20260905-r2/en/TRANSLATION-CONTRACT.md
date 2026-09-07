# EN 翻譯契約（haiku 逐章重譯用；2026-07-20 自 session scratchpad 永久化）

> 用途:任何一章的中文（`thesis-mc/*.md`）改動後,派 haiku agent 重譯對應的 `en/*.en.md`。
> 英譯的**唯一用途是雙語對照版與長度比對**,格式契約比文筆重要。
> 本檔是派工 prompt 的必附件;違反任一條即整章退回。

## 0. 硬性程序（歷史教訓,2026-07-20 實測:四個翻譯 agent 三個自報不實,其一零寫入）

1. agent **必須**用 Write 寫到指定輸出路徑,寫完**重讀檔案**、跑 §4 驗證指令、只貼真實輸出。
2. controller **不信自報**:先驗檔案 **mtime**(晚於 agent 啟動),再用**下游真程式**驗
   （`sys.path.insert(0,"thesis-mc/tools"); import build_bilingual as bb; bb.interleave(zh, en)`）,
   **不要**自寫近似檢查器（近似檢查器的每個化簡都是自裝盲點——HTML 註解就是這樣漏掉的）。
3. 大檔（>50KB／>150 區塊）切段並行,每段給明確區塊數目標,合併後整檔再驗。

## 1. 區塊對齊（`build_bilingual.interleave()` 會 assert,不合即 abort）

- 一個中文段落 → 一個英文段落;禁止合併、禁止拆分;區塊型別序列必須逐一相同。
- 標題、`$$…$$`、`![…](…){width=NNmm}`、表格、`> ` 引言、清單各自維持原位原型別。

## 2. 逐位元照抄（不准翻譯的東西）

- 所有數學:`$…$`、`$$…$$`,連同 `\tag{…}`、`\text{(3.20)}` 原封不動（interleave 逐位元比對,僅
  `\text{}` 內文與空白豁免）。
- 圖行整行照抄（路徑、寬度、alt 一字不動）;HTML 註解 `<!-- … -->` **整塊照抄含中文**;
  引用標記 `\[12\]` 照抄含反斜線;程式識別字、路徑照抄。

## 3. 用詞與語氣

- 唯一用詞權威 = `thesis-mc/TRANSLATION-GLOSSARY.md`（LOCKED 表 + FORBIDDEN 表）。
- 高頻鎖定:MCRL＝Multi-Catfish Reinforcement Learning;經驗/目標/獎勵/懲罰塑形＝
  experience/objective/reward/penalty shaping;對照設定＝**the control setting**（⛔ 絕不譯 ablation）;
  情境正規化＝context normalization;
  容量懲罰＝capacity penalty;經驗池＝replay buffer;競爭者數＝number of contending users。
- 禁出現:`MCCRL`・`Capacity-aware`・`ablation`・`annealing`（唯一例外＝ε-greedy 的 linear annealing）・
  `Double-DQN`・`auction/bid`・`decode(r)`・`distill`・`handoff`・`starve`・`we/our/this thesis` 當主詞。
  例外:圖檔名（如 `fig-cdrl-vs-mccrl.png`）與 HTML 註解內照抄不動。
- 不加中文沒有的宣稱;「預期」譯 "is expected to" 不升級;無 AI 腔（it is worth noting／notably…）。

## 4. 自我驗證（agent 跑完貼真實輸出;controller 再用 §0-2 重驗）

```bash
cd <repo>/thesis-mc && env MPLCONFIGDIR=/tmp/modqn-mplconfig python3 - <<'EOF'
import sys, pathlib; sys.path.insert(0, "tools")
import build_bilingual as bb
zh, en = "<ZH>.md", "en/<ZH>.en.md"
bb.interleave(pathlib.Path(zh).read_text(), pathlib.Path(en).read_text(), label=zh)
print("interleave OK")
EOF
```
