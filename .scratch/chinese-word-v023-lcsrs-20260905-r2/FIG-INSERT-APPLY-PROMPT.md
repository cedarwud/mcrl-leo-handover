# 論文插圖 + 圖標題 + 檔名 fig1–fig10 — turnkey prompt（2026-06-30；track-4 figure-insert）

> 貼到**新對話**執行。此 pass = 把 `../research-visual-lab/figures/thesis-mc/` 的 **10 張 arch 圖**插進論文
> markdown（取代 `[FIG-*]` 文字 placeholder）＋ 收每張圖的標題 ＋ 把檔名改成 `fig1`–`fig10`。
> **★ 前置事實：ch3→ch4 演算法邊界重構已於 commit `8c9f93e` 套用 → 圖號 slot 已變（見下表）。務必用新 slot map。**

## 啟動讀（依序）
1. 本檔（FIG-INSERT-APPLY-PROMPT.md）全部。
2. `thesis-mc/WRITING-RULES.md` R7 表（已更新的 slot map）＋ R3（結果圖耦合，**結果圖另一條線、不在本 pass**）。
3. `thesis-mc/FIGURE-EXPLAINER.md` §0 13 圖總表（每圖 slot↔章節↔資產 FIG-X 對照）。
4. `thesis-mc/FIGURE-HANDOFF.md`（production FIG-1..6 命名 ＋ 2026-06-30 重構 note）。
5. `CURRENT-STATE.md` 插圖 gate 段（figure session、MS-Word verify needs USER）。

## ★ 現行 slot map（重構後；本 pass 唯一依據）
| 章節 | thesis slot | 現 PNG 檔名（RVL sibling repo） | 建議新檔名 |
|---|---|---|---|
| ch1 | FIG-1-1 | `mc-fig1-overview.png` | `fig1` |
| ch3 §3.1 | FIG-3-1 | `mc-fig2-sysmodel.png` | `fig2` |
| **ch4 §4.1** | **FIG-4-1**（MODQN baseline，本次由 ch3 移來） | `mc-fig3-modqn.png` | `fig3` |
| ch4 §4.1 | FIG-4-2（框架總架構） | `mc-fig4-framework.png` | `fig4` |
| ch4 §4.2 | FIG-4-3（不對稱折扣） | `mc-figC-discount.png` | `fig5` |
| ch4 §4.2 | FIG-4-4（價值分層回放） | `mc-figD-replay.png` | `fig6` |
| ch4 §4.3 | FIG-4-5（壅塞 χ_u） | `mc-figB-congestion.png` | `fig7` |
| ch4 §4.4 | FIG-4-6（協調式波束分配） | `mc-figA-allocation.png` | `fig8` |
| ch4 §4.5 | FIG-4-7（訓練流程） | `mc-fig5-algorithm.png` | `fig9` |
| ch3 §3.4 | （目前無 slot＝文字表格） | `mc-cmp-cdrl-ours.png` | `fig10` |
- 上表 = **論文閱讀順序** fig1–fig10（建議；USER 待確認，見 DECISIONS）。
- **結果圖 FIG-5-1..5-4 不在本 pass**（在 `scratch/final_figures/`＝本 repo、R3-耦合、另一條 result-fig 線）。

## ★★ USER DECISIONS（動工前先收齊，缺一不可）
1. **fig1–10 編號慣例**：採上表「論文閱讀順序」？還是 production 順序 / 其他？（影響每張檔名）
2. **「圖標題名稱」定義**：13 slot 的**長 caption 區塊已存在**（`[FIG-*：……]`）。是要 (a) 另加一行**短標題**（如「圖 4-1 MODQN 架構」），還是 (b) 把現有長 caption 收成正式 caption？兩者都做？
3. **§3.4 cmp 圖（fig10）**：進 `[FIG-3-3]`（取代或搭配現有文字表格），還是**維持表格、不插圖**？
4. **圖檔路徑策略**：論文 embed 用 (a) 相對引用 sibling repo（`![](../research-visual-lab/figures/thesis-mc/figN.png)`），還是 (b) **複製** PNG 進 `thesis-mc/figures/` 再引用？（docx build / `to-ris-docx` 需可解析路徑 → 建議 (b) 複製進本 repo）
5. **結果圖（FIG-5-*）本回合是否一起插？** 預設否（另一條線）。

## 範圍（DO）— 三件事
### A. 改檔名 mc-fig* → figN（在 RVL sibling repo）
- 每張 PNG 連帶 sibling：`.png` ＋ `.editable.svg` ＋ `.viz.json` ＋ `.validation.json`；以及 build 腳本 `build_*.py` / `compile_all_pngs.py` / `README.txt` / `REUSE-INVENTORY.md` 內的引用。**全部一起改、否則 build 斷。**
- RVL = **獨立 sibling repo** → 改檔名 = 在那個 repo 動工＋它自己的 commit/handoff。**先確認 figure session 已凍結**（PNG mtime 2026-06-29 18:00、現已 idle ~12h，但**動工前再確認該 session 沒在跑**；CURRENT-STATE 警告「do NOT edit figs there」when active）。
- 若 DECISION 4 = 複製進本 repo：把 10 張改名後 PNG 複製到 `thesis-mc/figures/figN.png`（本 repo），RVL 原檔可保留 mc-* 名或同步改名（USER 定）。

### B. 插圖（取代 `[FIG-*]` 文字 placeholder）
- 現論文 9 個 arch slot 仍是 `\[FIG-X-Y\]` 文字 placeholder（+ 其下長 caption 區塊）。插圖 = 在引用點放 `![圖 X-Y 標題](路徑/figN.png)` 或 markdown 圖語法，caption 保留/收斂。
- slot↔檔名嚴格照上表（**特別注意 FIG-4-1=fig3=MODQN baseline**，這是本次重構移來的）。
- ch6 無圖。abstract 不放圖。intro 放 fig1（overview）。

### C. 收圖標題（依 DECISION 2）
- 13 slot 的 caption 區塊已存在於各章；本步驟＝按 USER 定義加短標題 / 收正式 caption。**caption 內容（語意、RED LINE、grounded 標籤）不得改**，只動標題格式。

## 不在範圍（DON'T）
- **結果圖 FIG-5-1..5-4**（另一條線、R3-耦合、需 result-fig session）。
- **改圖的視覺內容 / 重畫 PNG**（figure session 領域；本 pass 只改檔名＋插入＋標題）。
- 改 caption 的語意 / 數字 / claim（RED LINE）。
- ch4 式號、ch3 式號（已凍結於 `8c9f93e`）。
- EN `en/*`（留最終一次性重譯）。
- G1 `modqn.py`、env EUV READ-ONLY。

## 紀律
- RED LINES：catfish=具名元件非 win-driver；無假因果；r1=EE；用詞 協調式波束分配／綜合價值／χ_u；禁 decode/auction/蒸餾。
- 改檔名 = 跨 repo 機械改＋ build 不可斷 → 改完在 RVL 跑一次 build/validate 確認 PNG 仍可生。
- 插圖後 → docx rebuild（`conf-demo/build_paper.sh` 或 `to-ris-docx`）→ **真 MS-Word 開啟驗證圖有顯示 = 需 USER**。
- 同步更新 `WRITING-RULES.md` R7 表（檔名欄 mc-*→figN）、`FIGURE-EXPLAINER.md`（資產列）、`FIGURE-HANDOFF.md`。
- 跨檔/跨 repo 結構改 → cross-model G6（codex + agy）；codex quota 盡則 STOP+回報。

## 驗證（動工後必跑）
1. 10 張 figN 檔名 + siblings + build 腳本引用全部一致；RVL build 不斷。
2. 論文 9 arch slot 的 `[FIG-*]` placeholder 已換成圖引用、路徑可解析；slot↔figN 照表無錯位（尤其 FIG-4-1=fig3）。
3. docx rebuild 成功 + 圖顯示（USER 驗 MS-Word）。
4. caption 語意/數字/claim 未變（diff 只動標題格式 + 檔名）。
5. WRITING-RULES R7 / FIGURE-EXPLAINER / FIGURE-HANDOFF 同步。

## 輸出
- 改好的論文 markdown（含圖引用）＋ RVL 改名後檔案 ＋ 同步的 3 個 figure-handoff 檔。
- path-scoped commit（本 repo）＋ RVL repo 各自 commit；回報 hash。
- 若 docx 驗證需 USER，產出後 STOP+提醒 USER 開 MS-Word 驗。
