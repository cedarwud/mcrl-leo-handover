---
name: v014-gate-stop-adjudication-2026-09-03
description: 2026-09-03 V0.14 learner gate STOP 的唯讀裁定：Q3 head 失敗是 MSE 對雙峰目標的度量錯配；joint 失敗是支持事件在前一槽 state 下不可觀測，且 O2 的 segment 懸崖讓第 4、8 步全員換手；gate 本身無缺陷（完美 z3 配學到的 Q2 支持率 0.85）；裁定 Q3_OBJECTIVE_REBALANCE 探針，失敗分支是 STOP_THREE_HEAD
metadata: 
  node_type: memory
  type: project
  originSessionId: b41383f4-f20f-4be2-aa65-a57071672356
  modified: 2026-09-03T06:14:28.659Z
---

對 `artifacts/multi-catfish-v014-learnability-20260903-r1` 的裁定（result/authority 雜湊與兩份獨立驗證一致，
Q3 skill −0.061975 用凍結度量逐位重算相符）。

原始 source 統計（21 shard、537k 比較）：
- z3 目標 90% 為負、4% 為正、6% 為零；|y| 中位數 0.01–0.02κ、平均 0.26–0.29κ，雙峰。最強 null 是 TRAIN 中位數。
- 格中位數預測器 MAE 0.2778 < null 0.2844，格平均預測器 0.3279 > null：MSE 訓練的 head 學的是條件平均，
  在 MAE 對中位數的度量下必輸。head 失敗是目標／度量錯配，不是沒有訊號（corr +0.33、符號一致 84%）。
- 但所有格的條件中位數都是負的，重新平衡目標只能過 head gate，過不了 joint gate，除非 state 能辨識支持事件。
- 支持事件（g ∧ z3>0）可觀測性：最佳單特徵 AUC 0.72–0.75；最細合取格支持率 0.16 對基礎率 0.04；
  oracle g=1 候選也只有 0.40 為正；g=1 的目的地有 40% 在前一槽是空 beam。
- 陳舊性是結構性的：b0 續留 incumbent 只有 0.42；第 4、8 步全部 21 shard 都是 0.00，因為 OPS3 的
  z2(hold)−z2(bg) 中位數 −1.38κ、96.5% 觸到 ≤ −0.9κ 的服務風險懸崖（第 8 步 69%）。這是凍結 Q1+O2 行為的確定性節奏。
- 拆解 joint 失敗（VAL 9000 anchors 合併）：學到 Q2+完美 z3 → 支持率 0.851、teacher 改動回收 0.908，
  所以 gate 構造沒有缺陷；精確 O2+學到 Q3 → 支持率 0.106；Q2 雜訊單獨造成 884 次改動（支持率 0.12），
  Q2 置中誤差 0.09–0.11κ 對 Q1+O2 邊際中位數 0.14–0.19κ。
- 學到的 Q3hat 在 y>0 的配對上平均 −0.20、corr −0.08：對正支持完全盲；hold 被 gauge 釘在 ≈0 而真值 −0.24。

**Why:** 使用者要從原始統計分辨五個假說；架構與 gate 構造被排除，目標失衡已證實、可觀測性被強烈懷疑，
只有「同一 state、同一 panel、支持導向目標」的 source-only 探針能分開後兩者。
**How to apply:** 下一步只做那一個探針（≤10 分鐘 CPU），pooled 支持率 ≥ 0.5 才凍結重平衡的 Q3 gate；
否則 STOP_THREE_HEAD。不要再跑 oracle 確認、不要跑 100EP（實體 runner 本來就拒絕非 PASS）。
相關：[[v014-route-audit-2026-09-03]]、[[v014-learner-path-review-2026-09-03]]、[[c2-cleanroom-takeover-2026-09-02]]。
