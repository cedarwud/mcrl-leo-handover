# mcrl-leo-handover

MCRL(Multi-Catfish Reinforcement Learning)LEO 多波束換手 — 乾淨重建。

**狀態:W-01 完成(移植 + 來源凍結)。尚不可執行。**

- 規格:`~/papers/modqn-paper-reproduction/docs/MCRL-NEW-PROJECT-SDD-01-2026-08-21.md`(草稿 r3,**未 SOUND**)
- 參數:`~/papers/modqn-paper-reproduction/docs/NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`
- 移植證明:`docs/PROVENANCE.md`

**⚠ 依 SDD §9,實作(W-02 以後)須待對抗式審查達 SOUND。目前僅跑完第 1 輪。**

## 禁用清單(SDD §8)

拍賣式解碼、capacity penalty、`v_max`/`k_cap`、執行遮罩 `m^e`、
`χ`+z-score 預設開啟、Double-DQN 共用純量化動作、任何形式的 catfish。
保留程式碼是為了日後消融,不是為了現在用。
