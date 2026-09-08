**V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md**

**狀態：DRAFT，尚未封存。本次僅唯讀起草，無編輯、network、SSH 或實驗。** 本宣告事前固定 C3-S screen；S0 與 oracle diagnostics 已經開封，必須揭露為 development evidence。本文件本身不構成執行或 efficacy authority。

**1. C3-S 定義與機制**

C3-S 將第三 Catfish 定義為兩個 learned heads 之上的 **set-level coordinator**：Q1/Q2 提出 BASE complete profile，deployable model-based decision layer 評估完整候選配置，選定後 atomic execution。沒有第三個 additive Q head、第三頭訓練或個人化 surplus 分配。

[S0 diagnostic](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-probe-results-20260908/PROBE-S0-2026-09-08.md) 使用 E1 的 4 worlds × 3 lineages × 10 anchors、100 users；anchors 間由 learned BASE 推進。以 realised rows 評分，S0 pooled EE +1.812631%，service 與 BASE 同為 99.791667%；U₁ +1.992311%、J₁ +2.222094%；S0-U +1.523026%、S0-J +1.763038%。Nominal／realised score Spearman 平均 0.910408，但 S0 與 U₁、J₁ choice agreement 僅 1.667%、29.167%。這支持「nominal physics 能找到不同但接近最優的配置」，尚未支持 closed-loop 改善。

物理理由是 beam power maxima、PA supply、beam／satellite activation、bandwidth sharing 與 interference 都取決於完整配置。Nominal physics 保留這些交互作用；共同撤空可關閉整支 PA，單人移動也可能改善功率或 bits。S0-U 已有收益，因此不能把全部增益歸因於 evacuation，亦尚無逐項因果分解。

[Oracle marginals](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-probe-results-20260908/ORACLE-MARGINALS-2026-09-08.md) 中，exact others’ delivered-bit externality 經 `argmax(Q1+Q2+z/κ)` 合成後，C3 marginal 在 G0–G3 均 ≤0；該 additive third-head 路線在已測目標與 regimes 上 **closed at the oracle level**。個別 counterfactual 的精確性無法保證同時採納後的 joint gain；不是所有可能 additive encoding 的不可能性定理。Exact C1 約 +8.5–23% 也顯示 learned BASE 尚有誤差，不能宣稱剩餘收益全屬獨有協調能力。

**2. BASE 與 deployable interface**

本 screen 的 BASE 固定為 **E1 原三條 repriced Q1/Q2 lineages** `2026092101–03`，各自 `rung-003000`，Q2 initialisations 對應 `2026108101–03`；不是 FULL2 successor。沿用 E1 的 float32、unweighted masked `Q1+Q2`、最低合法 slot tie；28 slots，空 mask 回傳 `NOOP=-1`。兩臂使用相同 checkpoint，參數全程凍結。

Inherited head constants 不變：λ＝118424222.8550065 bits/J；κ＝10097071012.757404 bits。C3-S 不改寫其 labels 或 scales。

介面：

`coordinate(predecision_snapshot, legal_masks, slot_physical_keys, q12_proposal)`

唯一動態輸入為 S0 所需的當前 pre-decision state、已 committed association／occupancy／tracking state、當前 geometry、合法 masks 與 Q1+Q2 proposals。Nominal channel 固定為 OPS-3 median/no-fading convention：**unit Rician gain、zero-dB shadowing**。Q2 原有 model projections 可以保留；不得讀取實際未來 trajectory。

輸出為完整 action vector、candidate ID、nominal bits／joules／served、candidate census 與 wall time。禁止輸入本步 realised fading、realised candidate scores、oracle winners、未來 state、另一臂 trajectory 或 screen running EE。Realised endpoint 僅由獨立評分端在 commit 後讀取。

S0 implementation 以此介面規約引用；本草案不宣稱 server implementation 已完成封存驗證。

**3. Catalog、objective 與 execution**

每個決策在該臂自己的當前 state 重新產生 BASE proposal \(b_t\)，固定列舉：

- **BASE**：完整 \(b_t\)。
- **Unilateral**：user index、action index 遞增，列出每個合法、非 NOOP、非 BASE-equivalent 的單人 physical change；其他人保持 \(b_t\)。
- **Evacuation**：依 origin `(NORAD,cell)`、destination `(NORAD,cell)` 遞增，將同一 BASE origin 的全部 served members 移到每人共同合法的同一 destination；其他人保持 \(b_t\)。包含 singleton origins、empty destinations；不增加 heterogeneous destinations、子集合或多次 evacuation 組合。

**未充分指定處採最直接解讀：** origin membership 由 pre-decision snapshot 對 BASE 的 nominal/native service resolution 建立，不讀 E1 realised tape membership。Freeze 必須驗證此 catalog 可由允許資訊完整重建。保留未達預期撤空效果的合法配置；相同 action vectors 可共用一次 nominal evaluation，但保留 aliases。合法 slots 出現重複 physical-key 歧義依 E1/F1 規則拒絕。

每個 complete profile \(x\) 分別計算 \(\hat B_t(x),\hat E_t(x),\hat C_t(x)\)，不得相加 unilateral effects 重建 joint physics：

\[
x_t^*=\arg\max_{x\in\mathcal C_t:\,\hat C_t(x)\ge\hat C_t(b_t)}
\left[\hat B_t(x)-\eta_{\rm ref}\hat E_t(x)\right].
\]

\[
\boxed{\eta_{\rm ref}=124075740.54723135\ {\rm bits/J}}
\]

數值權威固定為 binary64 hex **`0x1.d94fb72305d6ap+26`**，取自 [E1 result record 的 η_BASE](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/E1-RESULT-RECORD-2026-09-08.md)。此處明定使用其公布的 binary64 常數；所有 worlds、lineages、steps 共用。選擇已存在常數最容易稽核，也避免 running-BASE EE 引入適應性或跨臂依賴。

Nominal binary64 coefficients 與此常數按 exact rational 比較，無 score epsilon。同分依固定 tuple key 字典序：BASE `(0)`、unilateral `(1,user,action)`、evacuation `(2,origin_NORAD,origin_cell,destination_NORAD,destination_cell)`；因此 BASE 優先。

BASE 必然通過 nominal guard；無其他合格配置時選 BASE。完整 \(x_t^*\) 一次 atomic commit，不拆成連續單人採納。Nominal evaluator 不得改變 committed state、RNG 或 realised field。Nominal guard 不保證 realised service，後者由 screen 判定。

**4. CLOSED-LOOP panel 與 seeds**

S0 是 matched-anchor one-step deviations；本 screen 執行 **BASE 與 BASE+C3-S 各自完整 fixed-policy episodes**。兩臂同一起點，其後各自由已選 action 推進；mobility、dwell、tracking、occupancy 與後续 proposals 的 state drift 全部保留，禁止逐步重設回 BASE anchors。

固定 4 fresh derived TRAIN worlds × 3 inherited lineages × 2 arms，每個組合一集，共 **24 episodes**。每集 **100 users、T＝30 canonical steps，indices 0–29**。每步 30.08 s＝47×0.640 s，每集 902.4 s。T 為 E1 的三倍，容許持續決策與 29 次後續 state transitions，同時保持 bounded kill screen；不宣稱足以估計長期效益。

Project seed rule 固定為：

`int.from_bytes(SHA256(domain.encode("ascii")).digest()[:8], "big") & ((1<<63)-1)`

| Domain | World seed |
|---|---:|
| `C3S_SCREEN/world/1` | 8464287092499831892 |
| `C3S_SCREEN/world/2` | 7305539127129390835 |
| `C3S_SCREEN/world/3` | 7691130988233444596 |
| `C3S_SCREEN/world/4` | 5887834234954284271 |

Freeze 前對完整 used／allocated world inventory 檢查互斥；碰撞即停止 freeze，不另挑 seed。這些是新 physical worlds、重用 trained lineages，不是十二個獨立 world clusters。

沿用 `_evaluation_rngs(world)`：`SeedSequence(world).spawn(4)`，env／mobility streams 保持原角色。兩臂各自重建相同初態；reset 前綁定：

`KeyedFadingField.from_components("MCRL_V023_LCSRS_C3_OBSERVABILITY_V1", world)`

Arm／lineage 不加入 field key。環境 RNG、keyed field 與其 seed 不暴露給 coordinator。

**5. Endpoints 與唯一 kill rule**

沿用 [stage-C physical runner](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/v023_c1c2_successor_physical_runner.py) 的 committed `last_outcome` accounting：

\[
B_t=30.08\sum_uR_{ut},\quad E_t=30.08P_{{system},t},
\quad
\eta_A=\frac{\sum B_t}{\sum E_t},\quad
s_A=\frac{\sum C_t}{36000}.
\]

每臂完整 12 episodes、360 steps、36,000 user-step opportunities；pooled ratio of sums，不平均 episode EE。Served fraction 不是 demand satisfaction 或公平性。Physics 沿用 E1 G0，無新增 finite-demand cap；D2 substeps 不另冒充 energy integrals。

對完整有效 panel：

**`C3S_SCREEN_SUPPORT` iff**
\[
\eta_{\rm C3S}>\eta_{\rm BASE}
\quad\land\quad
s_{\rm C3S}\ge s_{\rm BASE}-0.001.
\]

否則 **`C3S_SCREEN_NO_SUPPORT`**，列出 `EE_NOT_STRICTLY_ABOVE_BASE`、`SERVICE_MARGIN_FAILED` 所有成立原因。Service margin 等於最多少 36 served user-steps。採未四捨五入 coefficients 的 exact pooled comparison；無額外 gain threshold、action-change gate、sign-vote 或 significance gate。

Per-world／lineage EE、service、action changes 全數描述性報告，不選 favorable subset。

Provenance、資訊隔離、physics、matching、非有限值或 coverage 矛盾為 **`INVALID_RUN`**。單純中斷、資源不足或缺集為 **`INCOMPLETE`**；兩者均不得輸出 SUPPORT／NO_SUPPORT。

**6. Compute 與 machinery reuse**

每次 decision 的 compute budget 是 **完整 catalog 一次 exhaustive nominal pass**，相同 vector 可 memoize；S0 約 2,700 profiles，實際數量依合法 catalog 記錄，不以 2,700 截斷。每次記錄 Q inference、enumeration、nominal evaluation、total wall time；彙報 mean、median、p95、max、profile counts、peak RSS。Latency 是 deployability metric，**不是 gate**；不設 timeout-to-BASE 或 outcome-dependent pruning。

本 screen 約 \(12×30×2700=972000\) nominal evaluations，另有兩臂共 720 committed steps。以 E1「12 workers、每 unit 10 steps、17 min」線性估算：

\[
17\times12=204\ {\rm worker\!-\!min},\qquad
204\times3=10.2\ {\rm worker\!-\!hours}.
\]

同等 12-worker 並行約 **51 min**，約 **102 s／decision／worker**，另加 episode execution、I/O、驗證；這是假設 nominal profile 成本相近的規劃值，不是實測承諾。

重用 E1/F1 的 checkpoint authentication、catalog legality、F0 power conservation、keyed matching、immutable receipts；重用 stage-C closed-loop、ratio-of-sums、matched coverage。現有 stage-C 硬編碼 ten steps／four arms，須另建明確 **30-step／two-arm adapter 與 schema**，不能原封套用或改寫既有 authority。

**7. 後續資格與論文 framing**

SUPPORT 僅支持制定下一份 **confirmatory-grade evaluation plan**：stage-C-style `100→500→1500→3000` episode ladder、完整 matched release barriers、新 worlds 與另行封存的分析規約；不是 efficacy，也不直接授權執行。

**第三項正貢獻必須再測於 FULL2 上。** 後續主比較固定為 `FULL2+C3-S vs FULL2`；E1-lineage screen 的 positive marginal 不能替代它。Owner 的「three positive contributions」具體化為：

- C1 marginal：two-Catfish ladder 的 `FULL2 vs DROP_C1`。
- C2 marginal：同 ladder 的 `FULL2 vs DROP_C2`。
- C3-S marginal：`FULL2+C3-S vs FULL2`。

C1/C2 使用 equal-budget neutral-source replacement／retraining 的既定消融，不能用單純刪除 score head 代替。三項各自的 EE／service 條件均須成立；目前不預認 C1/C2 已達成。

共同論文句：

> 「C1、C2 保持為 learned heads；C3-S 是其上的 model-based set-level coordinator。既定 additive third-head 目標在已測 G0–G3 的 oracle-level marginal 檢驗中被關閉。」

SUPPORT 時追加：

> 「C3-S 通過 fresh TRAIN closed-loop development screen，支持後續於 FULL2 上確認其 marginal contribution；尚未建立 efficacy。」

NO_SUPPORT 時追加：

> 「固定 C3-S 在本 panel 未同時滿足 EE 改善與 service margin；本配置的 progression 關閉，三項正貢獻尚未成立。」

NO_SUPPORT 關閉本 constant／catalog／BASE／horizon 配置的後續升級，不關閉所有 coordinator，也不重開 additive C3。INVALID_RUN／INCOMPLETE 時只報無有效完整結論。

**8. Integrity 與 freeze checklist**

[Future-path memo](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-C3-FUTURE-PATH-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md) 的 eligibility rules 持續適用：此新架構由既有失敗、global views、E1 與 S0 development evidence 啟發；不得宣稱設計未受已知 diagnostics 影響。R7、F1 舊結論不變。

無 TEST、learner updates、η_ref tuning、catalog expansion、seed／horizon／regime search、realised-information selection、挑選重跑或跨臂 state sharing。有效 NO_SUPPORT 不重跑；僅可修復有證據的 infrastructure defect，保留原結果及 repair provenance。

Freeze 必須完成：

- 封存本文與 E1／S0／oracle／memo／global-view／F1 provenance：`<<BIND_AT_FREEZE:CONTRACT_SHA256>>`、`<<BIND_AT_FREEZE:EVIDENCE_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:EVIDENCE_MANIFEST_SHA256>>`。
- 三 checkpoint、authorities、parameter hashes、PREREG、完整 TLE archive、runtime dependencies：`<<BIND_AT_FREEZE:INPUT_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:INPUT_MANIFEST_SHA256>>`。
- Seeds collision census、初態 matching、nominal-only catalog reconstruction、ties／NOOP、evaluator state purity、30-step termination、F0 accounting、完整 pooled adjudication 驗證。
- 綁定 adapter／selector／verifier、環境與 launch arguments：`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_SHA256>>`。
- 唯一輸出根：`<<BIND_AT_FREEZE:OUTPUT_ROOT_PATH>>`；write-once unit／terminal receipts、atomic publication、0444、重新開啟驗 hash。Resume 只接受 authenticated complete units；部分資料不得裁決。
- 記錄 freeze timestamp、reviewer 與上述明示解讀。所有 manifest entries 各含 path／SHA-256；科學數值與選擇均已在本文固定。

Receipt claim ceiling：

`TRAIN_DEVELOPMENT_C3S_CLOSED_LOOP_KILL_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST`

---

## Addendum A — second declared configuration C3-S(lite) (astra draft 2026-09-08 07:43 UTC, appended by the controller before sealing; §1–§8 above byte-identical to the draft)

## ADDENDUM — C3-S-lite 事前配置與三臂 closed-loop screen

本附錄由 controller 在 outcome 可見前、封存前追加；§1–§8 原文保持 byte-identical。既有 C3-S 明確命名為 **C3-S(full)**；本附錄在同一 screen 增列 **C3-S(lite)**，以下固定其 catalog、三臂執行與後續資格規則。

### A. C3-S-lite 定義與列舉順序

Lite 與 full 使用完全相同的 decision rule、objective、η_ref（binary64 `0x1.d94fb72305d6ap+26`）、nominal service guard、exact score comparison、tie rule、atomic execution、physics 與資訊隔離。唯一差異是 candidate catalog pruning。

每步以該臂自身 pre-decision state 重新計算 float32、unweighted masked `Q1+Q2` 及 BASE proposal，依序列舉：

1. **BASE**：完整 BASE action vector，ID `(0)`。
2. **Top-2 unilateral edits**：依 user index 遞增。每人的合法 slots 按 float32 `Q1+Q2` 由高至低排序，同分取最低 slot index；第一項是 BASE action。由 runner-up 起依序掃描，跳過與 BASE physically equivalent 的項目，保留首個合法、非 NOOP、不同 physical action。僅將此 action 作為該 user 的 unilateral edit，其餘 users 保持 BASE；ID 沿用 `(1,user,action_slot)`。若無不同 action，不產生該 user 的 edit；空 mask 沿用 BASE `NOOP=-1`。BASE 本身不重複列為 unilateral。Physical-key 歧義仍按既有 E1/F1 規則拒絕。
3. **Every full-origin evacuation**：在 lite 自身 state 上完整沿用 full catalog 的 origin membership、共同合法 destination、singleton origins、empty destinations、合法性及 aliases 規則；不以 top-2 限制 evacuation destinations。依 `(origin_NORAD,origin_cell,destination_NORAD,destination_cell)` 遞增，ID 沿用 `(2,...)`。

相同 action vectors 可共用 nominal evaluation，但保留 aliases；objective 同分仍依 §3 tuple key 決定，BASE 優先。每步完整評估此 lite catalog，不加入 timeout-to-BASE 或 outcome-dependent pruning。

### B. 三臂 panel 與成本

Arms 固定為 **BASE、C3-S(full)、C3-S(lite)**。沿用四個 world seeds、三條 frozen lineages、100 users、T＝30、keyed fading 與原有 matching：每個 world／lineage 的三臂由相同初態出發，各自維持完整 closed-loop trajectory，禁止跨臂 state sharing 或重設回 BASE anchors。

總計 **36 episodes、1,080 committed steps**；每臂仍為 12 episodes、360 steps、36,000 user-step opportunities。Adapter、schema、coverage 與 receipts 須涵蓋三臂，沿用 §8 freeze requirements。

Full 約需 **2,700 nominal evaluations／decision**；E1 timing 推估約 **100 s／decision／worker**，對 3,000-episode confirmatory ladder 過慢。Lite 預估約便宜 **10×**。本 screen 規劃成本為 full 約 **10.2 worker-hours**、lite 約 **1–1.5 worker-hours**、BASE 相較可忽略；均為規劃估值，實際 census 與 timing 必須報告。

### C. 獨立裁決與預先固定的 progression

兩個 coordinator arms 各自對共同 BASE，獨立套用同一唯一 kill rule：

\[
\eta_{\rm arm}>\eta_{\rm BASE}
\quad\land\quad
s_{\rm arm}\ge s_{\rm BASE}-0.001.
\]

使用 §5 pooled accounting 與 exact comparison，分別輸出：

- `C3S_FULL_SCREEN_SUPPORT` 或 `C3S_FULL_SCREEN_NO_SUPPORT`
- `C3S_LITE_SCREEN_SUPPORT` 或 `C3S_LITE_SCREEN_NO_SUPPORT`

沿用失敗原因及 `INVALID_RUN`／`INCOMPLETE` 規則；缺失或無效結果不得當作 NO_SUPPORT。Full vs lite 的 EE、service、action changes 與成本比較僅為 **descriptive、non-decisional**，不得用來事後挑選論文主張。

後續 FULL2 confirmatory **plan** 的配置資格現在固定：兩者皆 SUPPORT，lite 因 deployability 優先進入規劃，full 結果完整報告；僅一者 SUPPORT，該者進入規劃；皆 NO_SUPPORT，本 coordinator family 在此 constant／兩個 catalogs／BASE／horizon 下的 progression 關閉。不據 outcome 另訂選擇標準，亦不直接授權 confirmatory execution。

### D. Timing 與 claim ceiling

Full、lite 均逐 decision 記錄 Q inference、enumeration、nominal evaluation、total wall time，分別報告 **mean／median／p95／max**，並沿用 profile counts、peak RSS；latency **不是 gate**。

Claim ceiling 不變：

`TRAIN_DEVELOPMENT_C3S_CLOSED_LOOP_KILL_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST`

僅 lite SUPPORT 時，論文使用：

> 「僅 C3-S(lite) 通過本 fresh TRAIN closed-loop development screen；C3-S(full) 未通過。此結果支持規劃 FULL2+C3-S(lite) 對 FULL2 的確認評估，尚未建立 efficacy 或三項正貢獻。」

僅 full SUPPORT 時，論文使用：

> 「僅 C3-S(full) 通過本 fresh TRAIN closed-loop development screen；C3-S(lite) 未通過。此結果支持規劃 FULL2+C3-S(full) 對 FULL2 的確認評估，尚未建立 efficacy 或三項正貢獻。」
