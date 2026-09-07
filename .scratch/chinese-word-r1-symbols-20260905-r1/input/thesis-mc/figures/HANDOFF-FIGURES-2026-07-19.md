# 畫圖 session 交接（2026-07-19 · 第二輪【出口 v2】）

> 前一版（第二輪進入交接）記的是「要做什麼」；這一版記「已做完什麼＋還剩什麼」。
> **已完成並 commit：`dd86c648`**（四道 gate 全綠，含 check_eye）。

## 這一輪做完的（USER 2026-07-19 第二輪四項指示中的 1、2、4）

**指示 1（移除頁尾說明文字）＋ 指示 2（填色分類）＝ 完成。**
- 八張既有圖的頁尾 legend 全部移除（`academic.md` **rule 9**）。移除的 52 行內容改寫為**繁中論文圖說**，
  全部落在 `FIG-CAPTIONS-2026-07-19.md`。
- 逐框填色：**sand `#f3efe6` ＝本論文相對 MODQN 基準新增的元件**；白底＝沿用／系統模型。USER 選的軸 A。
  「只填重要的、不鮮豔」＝守住。`figkit.CONTRIB`；`box(contrib=True)`。
- **⛔ USER-SET override 記在 `FIGURE-MANIFEST.md` §2**——牴觸 `academic.md` rule 1（白底），**未**牴觸 rule 2。
  下一個 agent 讀 house style 前務必先讀那條，否則會把填色改回白底。

**指示 4（補圖）＝ 完成。淨變化 8 → 12 張。**
- 修改 6 張（加填色＋移 legend）：4-2、4-7、功率-EE 鏈、系統情境、MDP 結構、情境正規化。
- **4-5 非對稱折扣＝降格移除**（USER「讓位」）：$\beta_M<\beta_{CF}$ 改於 4-7 的更新框呈現，ch4 §4.3 已改文；
  綁定 §4.8 的移除 contingency（消融判 NEUTRAL 就整個拿掉）。
- **4-6 ＝拆成兩張**：能效分層（`fig-stratification`）／週期性介入與介入退火（`fig-intervention-annealing`）。
- 新作 4 張：問題圖（過度集中，口試動機）、CDRL vs MCCRL（圖 4-3）、競爭獎勵 ACRM（§4.5）、容量懲罰（§4.6）。

> ⚑ **2026-08-21 狀態更新**：容量懲罰（舊 §4.6，後改稱 §4.5，在現行論文中已整節移除 2026-08-21）對應的圖（本交接文件中的「新作 4 張」中的容量懲罰圖，即最終 FIGURE-MANIFEST 中的圖 4-8）已不再是需要維護或重畫的論文圖。圖檔 `fig4-6_capacity-penalty.png` 保留 provenance，不刪除。

**ch4 已改（`DEVKIT_THESIS_OVERRIDE=1`，USER 授權）**：3 張已編號圖（4-2/4-3/4-7）嵌入＋圖說；
4-5 降格；2 張拆出圖嵌入（圖號待指派）。

**工具改動（durable）**：`figkit.box(contrib=)` 填色＋載入期 lum 自檢；`figkit.Fig.note()` 對 ≥2 行硬 raise
（rule 9 做成機器檢查，不靠記性）；`fit_height()` 取代 legend-based 畫布高；`fill_eye.py` DEFAULTS 全部改寫
成新 scheme（**不再斷言「no fills / decoded in legend」**——舊 default 會在眼檢記錄裡說假話）。

## 還剩什麼（下一個 session）

1. **指示 3：口試簡報圖另做一組**（USER 選「另做一組」，不是一套兩用）。**本輪未做**，是最大的剩餘塊。
   規格＝slide idiom：`academic-craft-guide.md` §0（16:10、節點 ≥21px、少字大框、一個 headline、
   填色 by role）。自這 12 張論文圖改編，字級與密度重算。**注意 §0 是 SLIDE-ONLY**，與論文圖規格不同。
2. **圖號指派（USER 已明示 deferred）**：新作／拆出的圖目前用內容命名，ch4 有一則「圖號待指派」註記
   （§4.3 末）。USER 指派後：`FIG-CAPTIONS` 的待指派圖說 slot 進 ch4 對應節、檔案改名、回填 manifest §1 與符號表 §16。
   ⚠ 指派會觸發 §4 全章重編號（4-5 移除、多張插入）——prose 的「如圖 4-X」與圖說要一起改。
3. **ch3 圖說 slot**：功率-EE 鏈／系統情境／情境正規化＝ch3 圖，圖說已備在 `FIG-CAPTIONS`，
   但 **ch3（`mc-modqn-base.md`）不在本輪 USER 授權面**——要 slot 需先取得 ch3 編輯授權。
4. **docx 驗證**：ch4 嵌入用 PNG（`rsvg-convert`／`inkscape` 皆缺 ⇒ PNG 是唯一嵌入路徑）。
   本輪未跑完整 `build_ris.sh`；下次改動後在 MS Word（非 LibreOffice）驗一次表格／公式／新圖。

## 凍結點（開工前比對）

| 檔 | 行數 | 最後改動 commit |
|---|---:|---|
| `thesis-mc/ch4-method.md` | 318 | `dd86c648`（本輪；原 304 @ `84f0ed5b`） |
| `thesis-mc/notation-table.md` | 272 | `84f0ed5b`（未動） |
| `thesis-mc/mc-modqn-base.md` | 534 | `84f0ed5b`（未動；ch3 圖說待授權才會動） |

比對：`wc -l <檔>` ＋ `git log -1 --format=%h -- <檔>`。對不上 ⇒ 先讀 diff。

## 啟動讀（依序，全部用 Read 實讀）

1. 本檔
2. `FIGURE-MANIFEST.md`（**§2 的 USER-SET override 區塊**＝最重要；§1 現況；§8 幾何常數與靜默失敗）
3. `FIG-CAPTIONS-2026-07-19.md`（12 張圖的繁中圖說＋落地狀態）
4. `src/figkit.py` 檔頭（USER-SET 區塊＋幾何 78/106/134）
5. `~/.claude/skills/flowchart/styles/academic.md`（含 rule 9）
6. `~/.claude/skills/flowchart/styles/academic-craft-guide.md` §0（**做簡報圖才讀；SLIDE-ONLY，勿套進論文圖**）
7. 目視成品：`/home/u24/.claude/jobs/*/tmp/render/*.png` 或重跑 builder 後自看
   ——**看一眼既有的圖，比讀三份規範更快抓到基調**（連續兩輪被證實）。
