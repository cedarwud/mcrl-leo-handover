---
name: v014-learner-path-review-2026-09-03
description: 2026-09-03 clean-room 審查 V0.14 learner 路線：裁定 PROCEED；Q2 學習只為宣稱非為部署、Q3 state 不漏不缺、通用 mean/max head 不改演算法、最少三段 gate
metadata: 
  node_type: memory
  type: project
  originSessionId: df4dbd76-6288-4d51-9f31-5f3c2fc5aaec
  modified: 2026-09-03T04:29:07.936Z
---

2026-09-03 對 Multi-Catfish V0.14（Q2 448 維 OPS3 特徵、Q3 287 維決策時 state、通用 independent masked mean/max head）做 read-only 審查，裁定 `DECISION=PROCEED_TO_LEARNER_IMPLEMENTATION`。

關鍵判斷（不在 repo 文件裡）：
- Q2 學習對部署是冗餘的：OPS3 16 特徵就是 O2 公式自己的輸入，z2 是這些特徵加凍結常數的確定性函數；學 Q2 只為「三個學來的 head」宣稱。Q2 gate 不得擋 Q3，PREREG 要預宣告 Q2 學不會時的退路。
- Q3 state 的區塊名 `maximum_required_link_power` 實際是候選 beam 已提交最大 RF 功率 / pmax（V0.3 encoder 的 power_block），正是 ZR 的 g 閘門加入端所需，所以 state 不是明顯不足。
- 凍結的 Q1 checkpoint 本身就是 masked mean/max 頭（trainer_algorithm 寫明），Q2/Q3 用同形式是一致而非改動。
- 最少 gate：A 一份合併 PREREG（含組合 argmax 一致率指標）→ B 來源產生 + Q2/Q3 並行 learner gate → C 100-EP 凍結策略 ablation；不另設聯合 policy gate。
- V0.10~V0.13 四份同日文件全是 oracle 端；V0.14 是自 V0.4 後第一個 learner 端步驟，不是繞圈。

**Why:** 使用者反覆問「是否在繞圈」；這次的裁定基準是 oracle 證據 / 學得性 / 部署效力三層分開。
**How to apply:** 後續若有人提議再跑 ZR oracle 確認、再修 Q3 state、或讓 Q2 擋 Q3，引用此裁定拒絕。相關：[[c2-cleanroom-takeover-2026-09-02]]、[[v09-pnfe-c3-review-2026-09-03]]、[[project-venv-has-torch]]。
