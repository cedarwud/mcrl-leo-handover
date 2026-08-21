# mcrl-leo-handover

MCRL(Multi-Catfish Reinforcement Learning)LEO 多波束換手 — 乾淨重建。

**狀態:W-01(移植 + 來源凍結)、W-16(修 L-1…L-3 + 補丁帳本)完成。**
**尚不可訓練:環境層 W-02…W-07 未寫。**

- 規格:`~/papers/modqn-paper-reproduction/docs/MCRL-NEW-PROJECT-SDD-01-2026-08-21.md`(r8)
- 參數:`~/papers/modqn-paper-reproduction/docs/NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`
- 移植證明:`docs/PROVENANCE.md`
- **補丁帳本**:`docs/PATCH-LEDGER.md` ← 任何偏離來源的改動都必須在此有一列

## 開發

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[train,test]'
.venv/bin/python -m pytest
```

## 禁用清單(SDD §8)

拍賣式解碼、capacity penalty、`v_max`/`k_cap`、執行遮罩 `m^e`、
`χ`+z-score 預設開啟、Double-DQN 共用純量化動作、任何形式的 catfish。
保留程式碼是為了日後消融,不是為了現在用(G-6 以 grep 零命中驗收)。
