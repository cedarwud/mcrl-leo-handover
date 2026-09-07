# Frozen Figure Captions

Source: `MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.1-2026-08-27.md`, with the current figure handoff confirming that all nine structural drafting rows are open. These captions are copied as authoring authority; this package does not insert them into the manuscript.

## Fig. 2-1

> 圖 2-1：本文採用的 MODQN 基準骨幹。每位使用者的觀測與可行波束遮罩同時
> 送入能量效率、換手成本與負載平衡三個目標價值網路；其輸出經加權整合與
> 探索後選出可行服務波束。環境回傳完整三目標獎勵與下一觀測，完整轉移進入
> 經驗回放，再由三條目標更新路徑分別學習。第一個目標採用本文的角度感知
> 能量效率；本圖只說明基準，不含 SMC-ER 的額外訓練機制。

## Fig. 3-1

> 圖 3-1：多波束低軌衛星網路的系統模型。每位使用者從可見且可行的候選
> 波束中選擇至多一個服務連線；實線表示實際服務，虛線表示未選取候選。
> 偏軸角 `theta_{u,s,v}(t)` 進入鏈路的 gain、SINR、rate 與 system-power
> chain；同一波束上的使用者形成 `U_{s,v}(t)` 並共享資源，只有
> `U_{s,v}(t)>0` 的波束才啟用。同衛星換束與跨衛星換手分別對應
> `varphi_1` 與 `varphi_2`；本圖只描述第三章物理系統，不含 SMC-ER 方法。

## Fig. 4-1

> 圖 4-1：所提出 SMC-ER 的整體架構。三條彩色實線表示 `F_1`、`F_2` 與
> `F_3` 實際執行後產生的完整經驗束；每條經驗路徑分別通過自己的
> Main-consumer gate，通過者才進入完整 Main learner，未通過者保留為 shadow
> lineage。所有 specialist 與 gate 只存在於訓練期，評估與部署只執行 Main；
> 三條路徑均為 proposed 且 conditional，圖中不包含 action fusion 或協調器。

## Fig. 4-2

> 圖 4-2：所提出 SMC-ER 的 four-learner／six-Q 拓撲。Main 保留
> `Q_1^M,Q_2^M,Q_3^M`，每個 `F_j` 只擁有對應的 `Q_j^F` 與 `D_j^F`；經驗箭頭
> 攜帶完整 reward vector 並指向整個 Main learner，不代表 action、private
> reward 或參數融合。此拓撲只用於訓練，部署只保留 Main；各 specialist
> 是否能供應 Main 仍由自己的 consumer gate conditional 決定。

## Fig. 4-3

> 圖 4-3：所提出 C1 Energy-Frontier 機制。上方箭頭表示 local SNR-greedy
> source 與 masked-uniform neutral source control 經 source-quality gate、分層與
> immutable EXP prefill 進入 `D_1^F`；下方箭頭表示 executed C1 branch 與
> Main comparator 形成 C1-private ACRM 更新。Offline prefill 不直接進入 Main，
> 只有後續實際執行的原始經驗束可經 `F_1` consumer gate 路由；C1 為
> training-only proposed mechanism，部署時移除，source 與 routing 均為
> conditional。

## Fig. 4-4

> 圖 4-4：所提出 C2 Temporal-Continuity option。時間軸上的實線箭頭表示以
> physical satellite-beam ID 選取、持續、明確終止與釋放關聯；通往 canonical
> `r_2` 的實線是直接學習端點，通往 EE 的虛線只表示待驗證的間接 interaction。
> C2 只在訓練期產生經驗，部署不保留 option；其作用與送入 Main 的資格皆為
> proposed 且 conditional。

## Fig. 4-5

> 圖 4-5：所提出 C3 Spatial Load-Balancing 機制。同衛星 relocation 的實線
> 表示 focal user 從高 eligible-load source 移到已啟用的較低負載 destination。
> `+2` 條件使 certified one-user fork 在每個 interval 的 `sum_u r_{3,u}(h)`
> 嚴格增加，其增量為 `2(U_{s,v}(h)-U_{s,v'}(h)-1)`；獨立
> power/service safeguard 線只表示 certificate 與 diagnostic，不進入 TD reward。
> 通往 `r_3` 的實線是直接端點，通往 system energy 與 EE 的虛線是 empirical
> supporting endpoint。C3 為 training-only proposed mechanism，且目前在自己的
> consumer gate 前維持 shadow-only。

## Fig. 4-6

> 圖 4-6：conditional atomic experience routing 與 Main update。藍色箭頭表示
> 含完整 joint action、所有 user rows 與原始 `U x 3` reward 的 atomic bundle；
> 每條來源先接受各自 consumer gate 的獨立檢查；只有 gate-pass bundle 才進入
> Main 並使用 unchanged baseline calibration，gate-fail bundle 保留於自己的
> shadow lineage，且 `F_3` 目前仍為 shadow-only。橘色箭頭表示
> objective-wise parameter update。Private shaping、option state 與 power
> diagnostic 不進入 Main reward，adverse outcome 仍保留且每個 bundle 總權重為一。
> 此 routing 只在訓練期發生，部署只保留 Main。

## Fig. 4-7

> 圖 4-7：所提出 SMC-ER 的 training-to-deployment sequence。Phase I 的箭頭
> 表示 offline source preparation、source-quality gate 與 C1-only prefill；
> Phase II 的箭頭表示 independent collection、retain-all、specialist update、
> source-specific consumer gate 與 conditional atomic routing；Phase III 的箭頭
> 只由 Main scalarization 指向部署 action。Specialist survival、routing 與
> experiment outcomes 仍待 gate 驗證，本圖不表示已完成實證，也不包含
> post-training coordination。
