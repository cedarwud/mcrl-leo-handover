**V023-C3S-FULL2-CONFIRMATORY-PLAN-CONTRACT-2026-09-08.md**

**狀態：`DRAFT_PRE_OUTCOME`。** 本文於 E1 checkout 唯讀起草，未編輯、未使用 network、未執行實驗或讀取 screen outcome。目的為預先固定 SUPPORT 後的確認規約；本文不構成 launch authority。

**1. 權威、資格與 arms**

來源均相對於 `/home/sat/mcrl-leo-handover-e1/`：

- `.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md`，含 Addendum A。
- `.scratch/multi-catfish-v023-c1c2-successor/` 下的 scientific declaration、development contract，以及 `V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-08-R2.md`。
- `.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/` 的 launch、chunking、acceptance、independent verifier、closure machinery。
- `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py` 與 world-plan builder。

配置 `c` 完全依 Addendum A：full、lite 都 SUPPORT 時選 lite；僅一者 SUPPORT 時選該者；都 NO_SUPPORT 時 progression 關閉。缺失或 INVALID 結果不視為 NO_SUPPORT，資格暫不成立。不得依 gain 大小、latency 或 deadline 改選。

固定 arm order：

1. `FULL2`：stage A 封存的 epoch-100 successor Q1/Q2 exports，同一 lineage。
2. `FULL2+C3-S(c)`：同一 exports，加 screen 選定且原樣凍結的 coordinator。

不重訓、不選 checkpoint、不加入第三個 learned head。FULL2 沿用 float32 masked、unweighted `Q1+Q2`、最低合法 slot tie、空 mask `NOOP=-1`。

既有 `FULL2 / DROP_C1 / DROP_C2 / BASELINE` 四臂 ladder 的完整已封存結果僅作 context，不重跑、不併入本 panel、不替代新 worlds 上的 FULL2 control。C1/C2 drops 保持 equal-budget neutral-source replacement／retraining 定義。

Successor 原宣告排除 C3；本案是 screen §7 所述的**另立實驗**，不改寫原宣告，也不把舊五臂 admission 視為本兩臂案的 execution authority。

**2. Coordinator binding**

同一份 frozen C3-S selector、catalog、nominal evaluator、config 與 dependencies 必須由 screen manifest 驗證。新增 FULL2 接線僅負責 authenticated exports、proposal 與 snapshot 介面，不改 coordinator 語義。

**未充分指定處採直接解讀：η_ref 保持 E1 η_BASE，不為 FULL2 重估。**

`η_ref = 124075740.54723135 bits/J`

binary64 權威：`0x1.d94fb72305d6ap+26`，exact rational 為 `4163290999041717 / 33554432`。它是事前選定的固定 reference price，不是 FULL2 EE 的估計值；更換 proposal policy 不要求重新校準，重估反而構成新配置。

每步於各臂自身 state 重新產生 proposal。Coordinator 最大化 `nominal bits − η_ref × nominal joules`，約束 nominal served 不低於當步 proposal。沿用 exact comparison、BASE-first tuple tie、完整 catalog pass、aliases 與 atomic commit。

Full 保留全部 unilateral edits 與 full-origin evacuations；lite 保留每人首個不同 physical action 的 runner-up edit，以及全部 full-origin evacuations。無 timeout-to-BASE、adaptive pruning 或 catalog expansion。

Nominal physics 維持 unit Rician gain、zero-dB shadowing。不得讀 realised fading、候選 realised scores、oracle winner、未來 trajectory、另一臂 state 或 running EE；evaluation 不得修改 committed state、RNG 或 keyed field。

**3. Fresh panel 與 sealed analysis**

**Horizon 未另定，採 stage-C-style 最直接解讀：**每集 100 users、10 committed steps，每步 30.08 s，共 300.8 s；不沿用 screen 的 30-step horizon。這項外推限制必須揭露。

預先生成並封存單一 9000-world plan，主分析使用其前 3000 worlds。對 `i=1,…,9000`：

`seed_i = int.from_bytes(SHA256(f"C3S_CONFIRM/world/{i}".encode("ascii")).digest()[:8], "big") & ((1<<63)-1)`

World ID 為 `c3s-confirm-world-{i:06d}`。Freeze 前檢查 plan 內部及完整 used／allocated inventory，涵蓋 E1、S0、screen、successor、acceptance worlds；碰撞即停止 freeze，不另挑 seed。

沿用 stage-C RNG 角色與 keyed-field namespace `MCRL_V020_REPRICED_C3_GATE_V1`，以新 seed 建立 field；不加入 arm key。两臂同一 world 初態、exogenous streams 與 field，之後各自 closed-loop 推進，不重設回 control trajectory。

Episodes 為**每臂累計數**：`100→500→1500→3000`；主 panel 共 6000 arm-episodes、60000 committed steps。每 100 episodes 出 authenticated checkpoint；僅完整 matched coverage 可發布 cumulative rung。

Endpoint 沿用 committed `TrainerEnvironment.last_outcome`：

`B_t = 30.08 × Σ_u link_rate_bps[u]`；`E_t = 30.08 × system_power_w`。

保留 stage-C 的逐集 reduction，再以 episode index 排序，對 individual episode totals 使用 `math.fsum`：

`EE_A = pooled bits_A / pooled joules_A`

`s_A = pooled served_user_steps_A / (N × 100 × 10)`。

不平均 episode EE，不把 D2 substeps 當 energy integrals，不新增 demand cap。Service 指 served fraction。

分析程式、reduction order、比較精度與輸出 schema 在任何 confirmatory computation 前封存。採 stage-C 未作展示四捨五入的 binary64 pooled endpoints 直接比較；無 epsilon、significance gate、subset selection 或額外效果量門檻。

**4. 唯一 falsifier**

僅於 independently verified、完整 matched 3000 episodes：

`C3S_CONTRIBUTION_HELD` iff

`EE_FULL2+C3-S > EE_FULL2`

且

`s_FULL2+C3-S ≥ s_FULL2 − 0.001`。

否則唯一 overall token 為 `C3S_CONTRIBUTION_FALSIFIED`，簡稱 FALSIFIED。列出所有成立原因：`EE_NOT_STRICTLY_ABOVE_FULL2`、`SERVICE_MARGIN_FAILED`。每臂 3000000 opportunities；margin 對應 3000 served user-steps。

100／500／1500 僅描述，不能提前判 HELD、科學性停止、換配置或救援。逐 world EE、service、action changes、latency 全部描述性報告。

Coverage 中斷／資源不足標記 `INCOMPLETE`；provenance、matching、physics、非有限值或 verifier 矛盾標記 `INVALID_RUN` 並 `STOP_PHYSICAL_EVALUATION_INTEGRITY`。均不得產生 HELD／FALSIFIED。有效 FALSIFIED 關閉 continuation，無 rescue。

**5. Chunked execution、成本與 deadline**

另封兩臂 adapter、plan builder、assembler、verifier、admission schema；現有四臂硬編碼檢查不可直接放寬後冒充既有 authority。

重用 R2 §2：連續 100-aligned chunks、exclusive locks、write-once episodes、authenticated resume、checkpoint 先於 chunk-complete receipt、append-only attempts。只啟動當前 release interval。Merge 驗所有 indexed hashes、boundary transitions、provenance、日期與完整兩臂 coverage。

唯一跨集 persisted stream 為 `_age_rng`；維持 `uniform-episode-length`，由本 plan episode-1 age stream replay 真實 `integers(0,10,size=100)` draws。其餘 RNG 按 stage-C 規則重建。

Formal chunks 前，**兩臂各做 sequential 200 對 2×100 acceptance**，比較實際 episode、rung、checkpoint、receipt、resume artifacts 的 bitwise binary64；僅排除 R2 §2 明列 provenance fields。Acceptance 使用獨立 domain `C3S_CONFIRM_ACCEPT/world/{i}`、相同 seed derivation，結果封閉，不納入主分析。

成本讀自 `<<BIND_AT_FREEZE:SCREEN_TIMING_RECEIPT_PATH>>`，以 `<<BIND_AT_FREEZE:SCREEN_TIMING_RECEIPT_SHA256>>` 驗證。`τ_c` 定義為選定配置全部 360 decisions 的實測 mean selector wall seconds；同時保存 median／p95／max、phase times、catalog census、RSS。此為機械取值，不保留可調數值空欄。

R2 §4 learned-arm 成本約 13.6 s／episode。保守估計：

`C(N) = N × (27.2 + 10τ_c) / 3600 worker-hours`。

公式額外計入完整 selector time，即使包含重複 Q inference 亦不扣除。Acceptance 增加相當於 `C(400)`，另加 integration、preflight、I/O、verification。Screen 與 FULL2 的 catalog distribution 可能不同，因此估值不是上界。

僅作量級示例，非實測：

| τ_c | 主 panel 3000 | 含 acceptance |
|---|---:|---:|
| 10 s | 106 worker-h | 120.1 worker-h |
| 100 s | 856 worker-h | 970.1 worker-h |

100-rung 的 coordinator chunk 至少約需 `100(13.6+10τ_c)/3600` 小時，不能除以 worker 數。若實際可用 16 workers，按四個 barriers、兩臂分批及 acceptance 排程，上述示例約需 **23.6 小時／198.6 小時**，尚未含工程與驗證時間。

Shared capacity 沿用 `(logical cores−2)−occupied workers`；worker 的 OMP／OpenBLAS／MKL／NumExpr 各 1，merge／verifier 沿用封存 controller thread 設定。不得把現有 stage-C 占用當空閒容量。

**Deadline 未提供確切時間，採條件式排程。** 實測接近 10 s 且有上述容量時，數天窗口可能容納 3000；接近 100 s 時通常不容納。Freeze 將既有 deadline、可用容量與公式計算記入 execution receipt。時間不足只能延後或報 INCOMPLETE；不能縮短 ladder 後宣稱確認成立，也不能改選 lite。

**6. 9000、closure 與 integrity**

3001–9000 不自動執行。只有本案 `C3S_CONTRIBUTION_HELD`、owner notification／literal reply record 及另封 continuation authority 齊備後，才能依同一兩臂 plan 經 6000、9000 barriers 延伸。舊四臂 HELD 不授權本案。

保留 ≤3000 prefix bytes、原 result 與 token；9000 只發布 `continuation-result.json`，不產生第二次 disposition。

依 R2 §3，HELD 後僅在 owner 明示 decline，或 defer 且明示 closure，並確認沒有 continuation execution／activity 後，發布 administrative closure。Silence 不足。保留 decision verbatim、timestamps、channel、controller、sidecar 與全套 bindings；`MANIFEST.sha256` 後最後寫 `COMPLETE`。Figures 必載「continuation to 9000 not performed」。已封 root 不重開。

TEST 永久關閉於本契約範圍；無 learner updates、tuning、seed／horizon／regime search、outcome-selected reruns。僅可修復有證據的 infrastructure defect，另封 repair provenance，重播最小 invalid unit，保存所有有效結果。

HELD 的論文上限：

「固定 C3-S 配置在 fresh TRAIN development panel、100-user／10-step episodes 上，相對 frozen FULL2 提高 pooled EE，且符合 0.001 service margin；此為 development-panel confirmation，未建立 TEST efficacy。」

必揭露 R7、oracle、S0 與 screen 對設計及配置資格的影響。不得據此宣稱 additive third-head efficacy、獨有 evacuation 因果作用或三項正貢獻已全部成立；C1/C2 仍由原四臂證據各自支撐。

Claim ceiling：`TRAIN_DEVELOPMENT_FULL2_C3S_CONFIRMATION_NO_LEARNER_NO_TEST_NO_EFFICACY`。

**7. Freeze checklist**

- 綁定本文、來源契約、screen dispositions／progression、timing、既有四臂 context：`<<BIND_AT_FREEZE:AUTHORITY_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:AUTHORITY_MANIFEST_SHA256>>`。
- 驗 stage-A PASS／epoch-100 exports、stage-B PASS、policy hashes、screen coordinator 原碼／config／η_ref、PREREG、TLE、dependencies；封存 `<<BIND_AT_FREEZE:INPUT_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:INPUT_MANIFEST_SHA256>>`。
- 封存完整新 plan、collision census、RNG／boundary rules、analysis、兩臂 execution closure、acceptance procedure：`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_SHA256>>`。
- 科學規約先封；其後 acceptance 只做機械驗證，PASS receipts 以 append-only supplement 認證，formal launch 前全部核實。
- 唯一 absent output root：`<<BIND_AT_FREEZE:OUTPUT_ROOT_PATH>>`；atomic publication、0444、重開驗 hash、write-once sidecars；外部 manifest 綁契約 digest，禁止 self-hash／循環依賴。
- 記錄 freeze UTC、reviewer、獨立 execution authority，以及本文明示的 η_ref、horizon、precision、deadline 解讀。所有 placeholders 僅填 paths／digests，不留科學選擇待 outcome 決定。

ASTRA_C3S_PLAN=DRAFTED