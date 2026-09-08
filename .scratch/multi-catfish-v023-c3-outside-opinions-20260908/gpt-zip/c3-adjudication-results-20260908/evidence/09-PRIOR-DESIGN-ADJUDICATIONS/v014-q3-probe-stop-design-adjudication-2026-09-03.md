---
name: v014-q3-probe-stop-design-adjudication-2026-09-03
description: 2026-09-03 Q3 support probe STOP 之後的獨立設計裁定：DECISION=STOP_THREE_HEAD；支持事件是他人同時段動作決定的協調事件（前一槽 state 精度上限約 0.3–0.5，Arm B 證明缺的不是 reference 局部特徵）；ZR oracle 的 EE 增益是下游 beam 整併（V0.13 每步 bits 都降、能量降更多），不是標籤宣稱的正外部性；(a)(b) 只是同一條 AUC 0.857 曲線的不同工作點，(c) 重開 oracle 迴圈或重疊 C1 能量角色
metadata:
  type: project
---

對 `artifacts/multi-catfish-v014-q3-support-probe-20260903-r1`（STOP_THREE_HEAD）的 read-only 設計裁定，
比較 (a) 非負精度校準 bonus、(b) 部署對齊的 teacher-action ranking、(c) 新物理 C3 target，裁定 **STOP_THREE_HEAD**。

不在 repo 文件裡的關鍵事實（TRAIN 4 世界 ×3 lineage 描述統計，未碰 VALIDATION；V0.13 merged result 逐步聚合）：
- 支持率依步：step 0 只有 0.95%，其他步 3–7%；b0 續留 incumbent 的比例在 step 0/4/8 為 0（O2 懸崖全員換手）。
- 前一槽可觀測規則的精度：目的地前一槽 active → P(g)=0.31、P(supp)=0.15（recall 0.6）；
  最細合取（active ∧ 有人 ∧ focal 非 leader ∧ b0 續留）→ P(g)=0.47、P(supp)=0.27、recall 0.23。
  支持事件的目的地有 39% 在前一槽根本沒 active。缺的資訊是他人「本槽」的 b0 動作，單一使用者決策時 state 拿不到。
- 探針 learned-Q2 脈絡的 850 次改動是 gauge 假象：predict() 把 harvest 的 b0 位置硬設為 0（不可部署的 oracle 輸入），
  Q3_hat 在其他動作約 −0.25κ，於是把 Q2 雜訊造成的換手拉回 b0，被計成「改動」但 z3(b0)=0 不算支持。乾淨訊號只有 exact-O2 的 6/17。
- ZR oracle（V0.13，+0.94% EE，4/4 世界）：step 0 同一 state 下 bits +0.45%、能量相同（標籤在匹配狀態下是對的），
  但 step 1–9 每一步 FULL 的 bits 都低於 DROP_C3、能量也都更低；總 bits −5.7%、能量 −6.6%、beam-steps −322。
  EE 增益是 g=1 約束推向已 active beam 造成的下游整併，不是標籤所量的當槽正外部性；teacher 改動的 z3 中位數 0.47κ
  對 Q1+O2 margin 中位數 0.18κ，單邊外部性總和約 +7% bits 但實現 −5.7%（V0.10 的非可加性教訓再現）。
- 學到的 bonus 若精度只有 0.3–0.5，錯誤正例中約半數 g=0（啟動擴張，V0.10/V0.11 的 −1.5%~−4.4% 機制），
  真正例的整併效應又需要同 beam 多人同時離開才成立；期望效應 ≤ +0.1%、符號不保證，100EP 五臂 screen 量不到。

**Why:** 使用者要一個「能維持獨立第三網路且合理可望改善 ratio-of-sums EE」的下一個 C3 家族；三個家族都不滿足：
(a)(b) 都是同一個分類器在同一條 AUC 曲線上選工作點，探針已經量過那條曲線；(c) 要嘛回到已產出五個失敗/邊際 target 的 oracle 迴圈（V0.14 路線審查已禁），
要嘛把能量寫進 C3（違反凍結的角色分工，且與 C1 重疊）。
**How to apply:** 終點改為 C1+C2 雙路由，ZR oracle（V0.12/V0.13）與這次 census 寫成 C3 future work。若使用者仍決定 override，
唯一可接受的 fallback 是「非負 bonus + g 精度 gate」：標籤 y=g∧z3>0（teacher/state 不變）、class-balanced BCE、
Q3=β·1[p̂≥τ]（無 gauge、不動 reference 列）、τ 與 β 由 TRAIN 世界 leave-one-world-out cross-fit 決定（β=被標記比較的 cross-fit 平均 z3，≤0 即在 TRAIN 端 STOP）、
在全新 sealed TRAIN 面板上綁定 exposure ≥2%、changed 中 g 率 ≥0.80、支持率 ≥0.50（pooled 且 2/3 lineage）。不得在同一驗證結果上再換 decoder。
相關：[[v014-gate-stop-adjudication-2026-09-03]]、[[v014-learner-path-review-2026-09-03]]、[[c3-stop-adjudication-2026-09-01]]、[[c2-cleanroom-takeover-2026-09-02]]。
