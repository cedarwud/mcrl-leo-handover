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

ASTRA_C3S_LITE=DRAFTED