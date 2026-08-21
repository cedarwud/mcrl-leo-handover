# 新對話啟動 prompt(W-16 → W-02)

專案:`~/papers/mcrl-leo-handover`(已存在,W-01 完成並 commit)
規格來源:`~/papers/modqn-paper-reproduction/docs/`

---

請依 SDD 實作 MCRL 的乾淨 baseline MODQN。**先讀這三份,不要重新設計:**

1. `~/papers/modqn-paper-reproduction/docs/MCRL-NEW-PROJECT-SDD-01-2026-08-21.md`(r8,主規格)
2. `~/papers/modqn-paper-reproduction/docs/NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`(逐參數 P/P′/D/S/X)
3. `~/papers/mcrl-leo-handover/docs/PROVENANCE.md`(W-01 已移植什麼、刻意沒移植什麼)

**這份 SDD 已經過六輪對抗式審查(四個模型家族)。設計決策已凍結,不要重開。**
若你認為某個決策有誤,**先說明再問**,不要逕行更改。裁決紀錄在
`~/papers/modqn-paper-reproduction/docs/sdd01-review-2026-08-21/`。

## 第一件事:W-16(阻擋所有訓練)

SDD §3.8 列出四個**已經被 W-01 逐位元組移植進本 repo** 的 live 缺陷。修 L-1、L-2、L-3:

- **L-1** `src/mcrl/algorithms/modqn.py:304` 與 `:578-580`:無效動作靜默回退索引 0。
  helper `_select_masked_greedy_action`(`:257-268`)正確回傳 `None`,兩個呼叫端把它吞成 0。
  依 §4A.5a:改為 **no-op**,該步 unserved,**該筆轉移不寫入 replay**。
- **L-2** `:756-772` 的 `update()` 缺有限性檢查(休眠孿生 `:700-708` 有)。依 P-3 補齊。
- **L-3** `:1239-1247` 無條件寫入 replay;需配合 L-1 排除全無效轉移。
- **L-4** 屬已停用路徑,**標記潛伏、不要接上、不要修**。

**同時建立 `docs/PATCH-LEDGER.md`**:每個偏離來源的補丁列出「來源行、補丁內容、理由、對應測試」。
W-01 的「逐位元組」授權已改為**逐位元組 + 宣告補丁帳本**,`docs/PROVENANCE.md` 須同步更新。

## 接著:W-02 起,依 SDD §5 的工作項順序

**W-02(TLE + SGP4 星曆層)與 W-03(動作索引契約)是最高風險的兩項。**
W-03 的完整規格在 §4A,包含身分定義、遮罩、狀態欄位與 T1–T12 驗收測試。

## 硬性約束

- **不得更動網路架構**:扁平 28 輸出、`(100,50,50)`、tanh。身分與遮罩屬**環境端帳務**。
- **§8 禁用清單**一律不得接上 live 訓練路徑:拍賣式解碼、capacity penalty、`v_max`/`k_cap`、
  執行遮罩 `m^e`、`χ`+z-score 預設開啟、Double-DQN 共用純量化動作、任何形式的 catfish。
  G-6 以 grep 零命中驗收。
- **§3.7 的 P-1…P-10 是強制的**。那些是運作中的實作已有、而規格先前漏寫的護欄;
  照規格字面重寫會全部消失,且多數缺了會**靜默**出錯。每項附 `file:line`,去讀原始碼再寫。
- **驗收門 G-1…G-12** 必須全綠才算完成,不得宣稱部分通過。

## 這個 session 學到的、最容易再犯的三件事

1. **`μ` 在本論文的半角慣例下恆遠超 34**(550 km 下約 66.75)。
   貝索上升冪級數在 `|x|≳40` 災難性抵消(`J₃(70)` 回傳 −5.8e11,真值 −0.0154)。
   **必須移植 Miller 下降遞迴路由**(P-1 / W-15 / G-10)。
2. **所有以 780 km 算出的數字都失效**。真實 Starlink 約 550 km:
   `R_b` 22.60 → 15.94 km、FSPL 少 3.03 dB、通過時長 12 → 7 分、角速度 +40%。
3. **任何 EE 比較必須同時報 `served` 與 `eff_beams`**(G-8);
   任何崩潰判定必須同時報 `active_beam_count`、`argmax_agreement`、
   **正規化後的 `q_margin`**、`q_entropy`(G-3)。缺任一項即不通過。

## 不要做的事

- 不要再跑設計審查。六輪已經跑完,剩下的缺陷類型需要**讀程式**,不是再想一次。
- 不要開始訓練。訓練屬重計算,要另開 brief 並在 Ubuntu server 執行。
- 不要碰 `~/papers/modqn-paper-reproduction/thesis-mc/`。論文的修改由使用者另行指示。

## 仍開放的兩項(量測後才能填,不是設計決策)

- **Q-D** `r3` 重新校準的尺度取法(W-07)
- **Q-E** dwell `N` 的最終值(probe P2)
