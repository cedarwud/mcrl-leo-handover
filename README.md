# mcrl-leo-handover

MCRL(Multi-Catfish Reinforcement Learning)LEO 多波束換手 — 乾淨重建。

**狀態:W-01…W-17 完成。物理鏈已全部接上 `StepEnvironment`,635 測試通過。**

一個 episode(100 位使用者、10 步、真實 TLE)約 **1 秒**:
星曆 → D2 → dwell → 候選表 → 遞推功率 → 可行性 → 服務 → 干擾 (3.12a)(3.12b)
→ SINR (3.13) → rate (3.14) → 功率 (3.15)-(3.16a) → `r1`/`r2`/`r3`。

⛔ **尚不可訓練**,而且理由是可機器檢查的:`p⁰ = 2 W` 高於 `p_max = 1.65 W`,
所以每一條鏈路在段起始就被判不可行,**outage 率恆為 1.0**。
`StepEnvironment.assert_ready_to_train()` 會擋住。
見 `docs/CONTROLLER-FINDINGS-W17-2026-08-22.md` 的 **F-1**(等待裁決)。

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
- **⛔ 待裁決(擋住訓練)**:`docs/CONTROLLER-FINDINGS-W17-2026-08-22.md`(W-17 接線量出的兩項論文內部矛盾)
- 已裁決:`docs/CONTROLLER-RULINGS-2026-08-22.md`(C-1…C-15),提問見 `docs/CONTROLLER-QUESTIONS-2026-08-22.md`
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
