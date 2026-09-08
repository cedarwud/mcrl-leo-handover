# 審查來源對照

本頁整理上一則審查答覆的來源，不代表新增文獻搜尋或實驗。專案事實來自使用者提供的審查包；外部文獻用於方法論解釋，不能代替專案結果。

## 套件證據

| 審查內容 | 原始證據 |
|---|---|
| 八類 C3 設計、歷史結果與否證範圍 | [01-CHRONOLOGY.md](evidence/01-CHRONOLOGY.md) |
| R7 held-out prediction、11 vs 00 物理結果、teacher／learner composition 與 topology consistency | [02-R7-STOP-PHYSICS-RESULT.md](evidence/02-R7-STOP-PHYSICS-RESULT.md)；[05-R7-CONTRACT.md](evidence/05-R7-CONTRACT.md) |
| F1 的 D/F EE、bits、energy 與 service 結果 | [03-F1-KILL-SCREEN-RESULT.md](evidence/03-F1-KILL-SCREEN-RESULT.md)；[03b-F1-r2-receipt.json](evidence/03b-F1-r2-receipt.json) |
| F1 的 BASE checkpoint、anchor 與 tape 範圍 | [F1-README.md](evidence/10-PHYSICS-AND-CODE/F1-README.md)；[run_v023_c3_contingency_f1.py](evidence/10-PHYSICS-AND-CODE/run_v023_c3_contingency_f1.py) |
| D/F 定義與 energy-share 代數診斷 | [04-CONTINGENCY-LADDER.md](evidence/04-CONTINGENCY-LADDER.md)；[c3_contingency_f0.py](evidence/10-PHYSICS-AND-CODE/c3_contingency_f0.py) |
| LC-SRS coalition identity 與適用邊界 | [ee_axis_coalition_residual_c3.py](evidence/10-PHYSICS-AND-CODE/ee_axis_coalition_residual_c3.py) |
| 加法合成、raw target 與 learned Q3 的 κ 正規化 | [06-COMPOSITION-RULING.md](evidence/06-COMPOSITION-RULING.md) |
| V0.14 的 coordination 診斷與 correction／margin 尺度 | [v014-q3-probe-stop-design-adjudication-2026-09-03.md](evidence/09-PRIOR-DESIGN-ADJUDICATIONS/v014-q3-probe-stop-design-adjudication-2026-09-03.md) |
| V0.20 exact-oracle 的正面中間結果與 nominal 限制 | [v020-repriced-c3-gate-adjudication-2026-09-05.md](evidence/09-PRIOR-DESIGN-ADJUDICATIONS/v020-repriced-c3-gate-adjudication-2026-09-05.md) |
| OPS-3 的前瞻範圍；避免將既有 own-surplus projection 當成新 externality | [ee_axis_ops3.py](evidence/10-PHYSICS-AND-CODE/ee_axis_ops3.py) |
| C1/C2 successor、既定比較基準與獨立評估邊界 | [07-C1C2-SUCCESSOR-DECLARATION.md](evidence/07-C1C2-SUCCESSOR-DECLARATION.md) |

底層 physical tapes 不在原始上傳包內，因此本封存不提供獨立重算所需的完整實驗資料。

## 外部一手文獻

1. [Lawson & Wolpert，COIN／difference-utility 分析，AAAI 2002](https://cdn.aaai.org/AAAI/2002/AAAI02-051.pdf)。用於區分 learnability 與 factoredness，以及 action-independent baseline 所保留的單方行動排序；不提供同時更新必然改善的保證。
2. [Böhmer et al.，Deep Coordination Graphs，ICML 2020](https://proceedings.mlr.press/v119/boehmer20a.html)。用於說明 pairwise joint payoff 必須配合聯合最大化／協調執行；只有 joint target 並不足以建立相同機制。
3. [Foerster et al.，Counterfactual Multi-Agent Policy Gradients（COMA）](https://arxiv.org/abs/1705.08926)。用於界定 counterfactual credit 在 critic 與 policy-gradient 架構中的角色；不能直接推導任意 additive deployment bonus 的有效性。

完整報告中的 existence-test 修正、pooled ratio 代數、D/F 代數診斷、候選排序與成功機率屬審查者的推導或判斷，並非上述文獻或套件已驗證的新增結果。
