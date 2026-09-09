# SUPERSEDES —— 本目錄取代了什麼，以及什麼仍然有效

- **產出日期：** 2026-09-09
- **本目錄：** `artifacts/chinese-word-v025-unified-symbols-20260909/`
- **本目錄的三份檔案：**
  `active-symbol-table-v025-20260909.md`（**唯一現行符號表**）、
  `SYMBOL-COLLISION-AUDIT-v025-20260909.md`（碰撞稽核）、
  本檔。

自本日起，**符號類別只有一個權威版本**：`active-symbol-table-v025-20260909.md`。
任何新符號都必須加進這一份，不得另立側表；新工作以 delta 形式提出，由使用者併入。

---

## 1. 本表取代的文件（不得再作為現行符號權威引用）

| 被取代的文件 | 取代範圍 | 仍然有效的用途 |
|---|---|---|
| `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` | **符號權威**身分被取代 | ① V0.23 凍結論文與三份 DOCX／PDF 的對照基準；② 本合併表的逐字基底（本表為純插入，零刪除、零改寫）。**檔案密封，不得修改** |
| `artifacts/chinese-word-v023-lcsrs-20260905-r2/SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md` | **稽核報告**身分被取代 | 其**碰撞規則**原封不動繼續有效（單一字母／單一數字上下標、禁多字母標籤、禁 hat、複合索引須由原子成分組成），本表逐條沿用。**檔案密封，不得修改** |
| `.scratch/multi-catfish-v023-controller-handoff-20260907/paper-lane-20260909/SYMBOL-ADDITIONS.md` | **待併入草案**身分結束：其 R-1、R-2 與 A-1–A-7 已全數併入本表 §10.14 | 保留為 R-1／R-2 改名理由與逐符號碰撞檢查的**論證紀錄**；不再是需要另外查閱的清單 |
| `artifacts/chinese-word-r1-symbols-20260905-r1/active-symbol-table-r1-20260905.md` | 早已被 V0.23 表取代，本表再度確認 | 歷史 provenance |
| `thesis-mc/notation-table.md` | 2026-08-22 起已是指標存根 | 維持存根，指向本表 |
| `docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md` 與各 `.scratch` 內的符號表副本 | 全部作廢 | 歷史 provenance；任何流程都不得讀取 |

---

## 2. 未被取代、仍為各自類別權威的文件

| 類別 | 權威文件 | 與本表的關係 |
|---|---|---|
| **物理公式定義** | `2026-08-17-simplified-ee-presentation-spec.md`（正式單一 SINR EE 公式規格） | 依合併表 §1 的既有規則：若本表與公式規格不一致，**以公式規格的物理定義為準**，並立即同步本表 |
| **V0.25 繼任者的設計、常數、閘門與決策規則** | `.scratch/multi-catfish-v025-physics-successor/` 的密封宣告鏈：優先序宣告 v1.0–v1.9、應變階梯（含 R7 修訂）、stages 6–8 契約 v1／v1.1／v1.2、CH5 掃描圖規格、ACM 缺陷確認、各 controller 決策紀錄 | 本表**只固定記法**，不改變任何設計、常數、邊際、臂、面板或裁決規則。密封檔案不得修改 |
| **單一權威登記** | `V025-SINGLE-AUTHORITY-REGISTER-2026-09-09.md` | 其「符號表」一列自本日起指向本目錄的合併表；其餘各列（論文 DOCX、簡報、模擬器）不受影響 |
| **論文中文本體** | `artifacts/chinese-word-v023-lcsrs-20260905-r2/mcrl-thesis-ZH-v023-method-draft-20260905.docx` | 仍是 V0.23 版本的權威；改寫為 V0.25 時以本表為符號來源 |
| **第三／四／五章改寫草案** | `.scratch/…/paper-lane-20260909/` 的 `SEC-SYSTEM-MODEL-REWRITE.md`、`SEC-METHOD-REWRITE.md`、`DELTA-MAP.md`、`TAB-I`、`TAB-II`、`LIMITATIONS-REGISTER.md` | 這些草案應改為引用本表；本表不取代它們的內容 |
| **模擬器** | `~/demo/leo-beam-sim` | 依單一權威登記 §3 刻意延後遷移；遷移時以本表為符號對照來源 |

---

## 3. 三件必須先讀的注意事項

1. **本表是純插入。** 合併表相對 V0.23 權威表零刪除、零改寫；新增的 105 列全部帶
   【新】或【改】標記。V0.23 的任何既有定義都可以在合併表中原樣找到。
2. **有 14 條登記在案的衝突，其中兩條未裁決。** 見稽核 §4 的 C-01（\(F\)／\(G\)／\(\Phi\)
   的歸屬）與 C-13（段記憶符號 \(\tau_{u,s,v}\)、\(p^{0}\)、\(\eta_{u,s,v}\) 的去留）。
   兩者都需要使用者或後續密封宣告確認，本表不代為裁決。
3. **有 4 個真缺口。** 見稽核 §5 的 G-01–G-04：C2 延續值、候選刷新週期 \(N=4\)、
   standby 比例、跨波束交互增益，密封宣告只以文字定義而未固定字形；第四／五章
   寫到相應段落前必須先裁決。

---

## 4. 一句話版本

**符號要查哪一份：** `active-symbol-table-v025-20260909.md`，只有這一份。
**設計與閘門要查哪一份：** `.scratch/multi-catfish-v025-physics-successor/` 的密封宣告鏈。
**物理公式不一致時聽誰的：** `2026-08-17-simplified-ee-presentation-spec.md`。
