# mcrl-leo-handover

MCRL(Multi-Catfish Reinforcement Learning)LEO 多波束換手 — 乾淨重建。

**狀態:W-01、W-16、W-02、W-03、W-04、W-05、W-06、W-15、W-07(`r3` 計數式 + P-5)完成。**
**尚不可訓練:W-08…W-14 未寫。**

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

⚠ **執行遮罩 `m^e` 已於 2026-08-22 移出禁用清單**(SDD §2.2 修訂):
退出貢獻宣稱,但**保留為環境端帳務**。它是 P-5 的護欄,而 B13 的計數式
`r3 = −U_{b_u}` 直接依賴「誰真的被服務」。**W-07 擁有它。**
