1. **直覺有條件成立；低信心應指向整體設計，不能只歸咎 r3。** Load balance 改善公平性或個別速率，不保證 pooled EE。對完整 matched panel，改善條件是
   \[
   \Delta B-\eta_{\rm BASE}\Delta E>0
   \]
   且符合 service margin；「更多 bits」與「更平均負載」都不足以成立。十八次嘗試大量共用同一 deployment rule，並非十八次獨立否定 coordination 的可能性。[Chronology](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md:126)、[E1 objective](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:21)。

2. **物理 regime 沒有「人多使 PA 過載，所以分流必然省電」這條鏈。** 每束 RF power 是 served users 的 **max**，不是 sum；合法功率不超過 1.65 W，低於 PA saturation 5.218 W。因此有效區間為 \(P_{\rm PA}=\sqrt{p\,p_{\rm sat}}/0.35\)：效率隨輸出上升，沒有進入飽和後急升的成本區。每多開一束還付 PA＋0.338 W circuit；新活躍衛星另付 0.200 W baseband。F1 BASE fixture 有 66 beams，RF 0.825–1.419 W；總功率 449.638 W 中 PA 為 426.130 W，約 **94.8%**。關束主要省的是整支 PA，不只是 circuit。[物理公式](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py:439)、[既有 fixture，靜態重算](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/fixtures-real-anchor/base-profile-anchor0.npz)。

3. **Bits 的來源是 bandwidth sharing、SINR 與幾何，不是抽象的負載均衡。** \(R_u=(166.667{\rm MHz}/n_b)\log_2(1+\mathrm{SINR}_u)\)；若同束 SINR 相同，總速率中的人數會抵銷。分流至既有 beam、降低 interference、移走 power leader，或完整 evacuation，才可能值得。遠星的 path loss 主要傷害 SINR/bits；此模型的功率 recurrence 補償角度增益，**不做 distance／target-SINR power inversion**。也沒有用戶數造成的容量 admission 門檻或最低速率保障。28 是每人 action slots，不能把 100/28 當網路壅塞程度。[Rate／path loss](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py:320)、[recurrence](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/step.py:770)、[service](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/service.py:185)、[slots](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/action_contract.py:7)。

4. **既有數據確實定位了收益與代價，但尚未完成逐物理項因果分解。** 以下為各自歷史 panel 的 pooled 變化，不能跨列排名：

   | 比較 | Bits | Joules | EE |
   |---|---:|---:|---:|
   | MONE FULL／DROP-C3 | +5.373% | +8.227% | −2.637% |
   | R7 source 11／00 | −2.185% | −2.137% | −0.0493% |
   | F1 D／BASE | +6.928% | +8.367% | −1.328% |
   | F1 F／BASE | +14.749% | +20.202% | −4.536% |

   MONE 同一開場 anchor（world `2026104601`、lineage `2026092101`、t=0）：beams **59→68**，bits **1.369→1.745 Tbit**，energy **12.484→14.400 kJ**，該點其實改善 EE；但全程 beams 平均 **44.267→48.367**，整體失敗。R7 則顯示 consolidation 的節能不足抵銷 bits 損失。F1 **只有 D** 額外失敗於 service 0.995；F 為 1.000。這些證據排除了「完全沒有有利狀態」，尚不能分別量出 bandwidth、interference、path loss 各貢獻多少。[MONE](/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v010-mone-c3-oracle-20260903-r1/server-merged/result.json)、[R7 totals](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/r7-sealed-receipts/result.json)、[F1 totals](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/03-F1-KILL-SCREEN-RESULT.md:123)。

5. **Levers ①label、②composition：目前最強的架構證據指向兩者不相容。** MONE 的 60/60 unilateral surplus 為正，joint 卻反轉 28 次；總預測 \(1.8595\times10^{13}\) bit-equivalent，被 interaction residual \(-1.8117\times10^{13}\) 抵銷約 97%。Exact label 只精確描述其 counterfactual，沒有替同時 argmax 提供保證。R7 learner balanced accuracy 0.705 通過，learned EE 仍 −0.660%、topology consistency 僅 379/707；把 coalition value 分給個人也不保證共同採納。但 teacher composition **+0.335%**，所以不能宣稱 additive rule 普遍不可能成功。[MONE diagnostics](/home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v010-mone-c3-oracle-20260903-r1/RESULT-SUMMARY.md:28)、[R7](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/02-R7-STOP-PHYSICS-RESULT.md:24)。

6. **Lever ③information：ZR 的 deployability 是另一個實證瓶頸。** EXACT_ZR +0.985% 使用 realised fading；EXPECTED_ZR 停止，不能把 oracle 收益當可學習上限。Others’ same-slot actions 則有不同性質：既然已有 central scheduler，它可以先形成完整 proposal，再共同決定；缺少這個資訊是目前 interface 的限制，可以透過新架構處理。Realised fading 仍須預測或邊際化，不能由 coordinator 憑空取得。[ZR chronology](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md:26)。

7. **Levers ④horizon、⑤objective、⑦BASE 都有影響，尚無證據可把它們排除。** C1 已把 unilateral 的**全部 network-energy delta**納入；C2 也價格化未來功率與 service risk，因此「C1 公式固定」不代表 Q1 準確，也不代表剩餘 headroom 已耗盡。歷史 MONE 的 Q1／exact-O1 top agreement 僅 0.2275；R7 的 C2 exposure 0.764 也不是「影響很小」的證明。固定 λ surplus 加上 offset 平均，並不等於 pooled-ratio trajectory optimizer。PNFE 已有 future offsets，但 OPS-3 不演化 mobility、dwell 或後續聯合決策；真正 adaptive trajectories 仍未測。Service guard 保護的是 served count，不是公平速率。[C1 source](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_opening_source.py:635)、[C1 accounting](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_surplus_targets.py:247)、[C2 formula](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_ops3.py:729)、[projection boundary](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_ops3_live.py:16)、[PNFE](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_pnfe.py:9)。

8. **全球重設：我會建 set-level scheduler。** 保留 Q1/Q2 產生 proposals；另預測完整配置的 conditional bits、joules、service，以共同 decoder 選配置並 atomic execution，直接處理 evacuation、activation budgeting、互斥 proposals，避免再把共同收益拆回獨立 argmax。這利用現有中央決策位置；Q3 不必是第三個 Q head。新增 admission/drop action 或 adaptive MPC 則需另定方法與 service 語義。若更換 BASE，必須保留原 BASE 比較，不能用較弱 comparator 製造進步。

   這些方向原則上可作 **separate PRE-OUTCOME research**：先宣告 mechanism/interface/formula/deployment/panel/falsifier，披露歷史結果與 checkpoint reuse；不動 sealed constants、不挑有利 regime、不復活 D/F、不開 TEST。E1 通過只支持下一份 screen 宣告，並非 launch authority。[既有 memo 的邊界與資格規則](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-C3-FUTURE-PATH-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md:22)。

9. **E1 四格應如此解讀；目前不預判結果。**

   | U₁ | J₁ | 對直覺與下一步的意義 |
   |---|---|---|
   | HEADROOM | HEADROOM | 兩類都有物理空間；coordination 並非改善的必要條件，任一類可宣告 screen。 |
   | HEADROOM | CLOSED | 單人改善存在；evacuation catalog 無收益，只支持 unilateral screen。 |
   | CLOSED | HEADROOM | 此 panel 的改善需要超出單人類別；最直接支持 atomic joint redesign。 |
   | CLOSED | CLOSED | 兩個受限類別均無空間；均不支持 candidate screen，不等於所有 joint／trajectory 方法不可能。 |

   BASE 在兩集合內，所以有效 CLOSED 是**等於 BASE**。U₁ 僅是每 anchor 至多一人改動的 certified ceiling；J₁ 是固定 catalog optimum、unrestricted joint potential 的下界，兩集合不互相包含。Exact DP 的 pooled service allocation 與 realised information 都不是現成部署策略；嚴格正增益也不代表實用幅度。INVALID／INCOMPLETE 無四格結論。[E1 contract](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:43)。

10. **數天內可交付的是可判斷的 screen／prototype，不能承諾正向 learner efficacy。** 廣泛 joint optimization、adaptive trajectories、訓練與泛化證明較適合 follow-up paper；原 memo 的完整物理路徑估算已約 140 worker-hours，尚未含新增 C3 成本。

    E1 後最有資訊量的**單一實驗**，是新 TRAIN panel 上的 deployable-information decoder kill screen：共同比較 BASE、privileged oracle diagnostic、只用可部署資訊的 scheduler。先按機制定優先序：J₁ 有 headroom 用 atomic catalog；只有 U₁ 有則限制 single edit；兩者 CLOSED 不啟動。固定 catalog、資訊、公式與 falsifier 後，直接看 pooled EE/service，定位「物理空間是否能穿過資訊與決策介面」。本次未啟動實驗、修改檔案或查詢遠端。[成本與界限](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-C3-FUTURE-PATH-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md:100)、[E1 progression](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:72)。

