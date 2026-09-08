---
name: v015-learned-context-oracle-gate-review-2026-09-03
description: V0.15 C3 learned-context oracle 兩臂 gate 的偽證審查（2026-09-03）— 裁定 REJECT_HYPOTHESIS；「標籤在 exact O2 脈絡生成/置中」不是 C3 學習失敗的成因
metadata:
  type: project
---

2026-09-03 對 V0.15 契約（artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1）
做 fresh-context 偽證審查，裁定 **REJECT_HYPOTHESIS**。用本機 V0.14 shard 與
rung-3000 Q2 checkpoint 直接量到：learned 背景 b′=argmax(Q1+Q2_hat) 與 exact 背景 b
在 89–92% anchor 相同；完美 z3（在 b 生成）配 Q2_hat 與 exact teacher 的 argmax 一致
94–95%、還原 90–93% teacher 改動。反觀 Q3 head 同分布 skill 為負（−0.02～−0.06）、
探針 exact-O2 臂（完全無錯配）只還原 0–1.3% teacher 改動。ZR 的 reference 列 raw 恆為 0，
centering 是空操作；argmax 與 pairwise loss 都對常數平移不變。

**Why:** V0.15 兩臂 oracle gate 不含 learner，GO 近乎預定（脈絡只差 ~10% anchor），
STOP 則指向 Q2_hat 閉環病理而非標籤脈絡；兩個 token 都判別不了假設。GO 分支會授權
用 ~90% 相同的標籤重跑已在同分布下失敗的 learner。這與 [[v014-q3-probe-stop-design-adjudication-2026-09-03]]
「(c) 重開 oracle 迴圈」的否決一致。

**How to apply:** 若使用者再提「脈絡錯配」或「重新置中標籤」作為 C3 救援方向，先引用
上述數字；C3 的真 blocker 仍是稀有協調事件在可部署 state 下的可學性
（見 [[v014-gate-stop-adjudication-2026-09-03]]）。V0.15 契約若要保留只能當
Q2_hat 閉環健全性檢查，且其 gate 比 V0.13 鬆（2/3 lineage、3/4 world）。
