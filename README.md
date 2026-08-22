# mcrl-leo-handover

MCRL(Multi-Catfish Reinforcement Learning)LEO 多波束換手 — 乾淨重建。

**狀態:W-01…W-18 完成。物理鏈接上 `StepEnvironment`,訓練器接上環境,**694 測試通過**。**

一個 episode(100 位使用者、10 步、真實 TLE)約 **1 秒**:
星曆 → D2 → dwell → 候選表 → 遞推功率 → 可行性 → 服務 → 干擾 (3.12a)(3.12b)
→ SINR (3.13) → rate (3.14) → 功率 (3.15)-(3.16a) → `r1`/`r2`/`r3`。

以凍結常數量測(12,000 個決策步):**outage 0.0000**、每步 41 支波束輻射、
`P^N` 258.4 W、SINR p05/p50/p95 = 11.7 / 16.4 / 19.0 dB。
`assert_ready_to_train()` **通過**。

**移植來的 `MODQNTrainer` 已能在真實星曆上跑真實 episode**
(`runtime/trainer_env.py`,W-18)。

⛔ **但訓練仍被擋住,而且是刻意的**:Q-D(`r3` 尺度)與 Q-E(dwell `N`)未定案,
它們由 probe P3/P2 關閉,而 probe 要先凍 PREREG。
`TrainerEnvironment.assert_ready_to_train()` 會擋。

**兩件在等你:**

1. **簽 PREREG** —— `docs/PREREG-SIGNOFF-2026-08-22.md`。
   凍結之後任何門檻或選取規則的更動都是「看過資料才改」,正是 §7.1 要防的洩漏。
2. **`H = 10` 是否夠** —— `docs/W18-REPLY-2026-08-22.md` §2。
   量測結果:角度感知功率遞推要 **169 步(中位)/ 29 步(最快)** 才吃掉 3 dB 預算,
   而 episode 只有 10 步;100% 的 segment 由 episode 邊界切斷,
   段內最大跌幅 0.718 dB(預算的 24%)。**依指示未動 `H`。**

- 規格:`~/papers/modqn-paper-reproduction/docs/MCRL-NEW-PROJECT-SDD-01-2026-08-21.md`(r8)
- 參數:`~/papers/modqn-paper-reproduction/docs/NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`
- 移植證明:`docs/PROVENANCE.md`
- **補丁帳本**:`docs/PATCH-LEDGER.md` ← 任何偏離來源的改動都必須在此有一列
- 星曆層量測:`docs/EPHEMERIS-NOTES.md`(高度、覆蓋率、通過時長皆為量測值)
- G-9 驗收對照:`docs/G9-TEST-MAP.md`(T1–T12 → 測試名)
- D2 量測:`docs/D2-NOTES.md`
- 鏈路預算/天線/dwell 量測:`docs/LINK-BUDGET-NOTES.md`
- `r3` 與執行遮罩:`docs/R3-AND-EXECUTION-MASK-NOTES.md`
- **偏離登記表**:`docs/DEVIATION-REGISTER.md`(`X` 級偏離,每條都須在論文明講)
- **遷移表**:`docs/MIGRATION-TABLE.md`(舊名 ↔ 新名 ↔ 論文符號,W-14)
- 已裁決:`docs/CONTROLLER-RULINGS-2026-08-22.md`(C-1…C-15)、
  `docs/CONTROLLER-RULINGS-W17-2026-08-22.md`(F-1/F-2);
  提問與量測回報見 `docs/CONTROLLER-QUESTIONS-2026-08-22.md`、
  `docs/CONTROLLER-FINDINGS-W17-2026-08-22.md`
- **PREREG 草案**:`docs/PREREG-DRAFT.md` ← probe 執行前必須凍結

## 開發

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[train,test]'
.venv/bin/python -m pytest
```

## 禁用清單(SDD §8)

拍賣式解碼、capacity penalty、`v_max`/`k_cap`、
`χ`+z-score 預設開啟、Double-DQN 共用純量化動作、任何形式的 catfish。
保留程式碼是為了日後消融,不是為了現在用(G-6 以 grep 零命中驗收)。

⚠ **執行遮罩 `m^e` 已不存在**(裁決 C-11)。該日稍早曾記為「保留為環境端帳務、
連線恆等式維持三閘」,**那一版已被控方撤回**。定案是**兩閘 `x = a·z`**:
`m` 只作決策時遮罩,不進連線恆等式;選上與被服務之間的閘是**逐鏈路功率可行性**。

另:`PowerSurfaceConfig` 與七個 `HOBS_POWER_SURFACE_*` 模式已由 **P-16 整組刪除**
(裁決 C-2「載量式 PA 整條移除」)。功率模型是**角度遞推**,**沒有模式開關**。
