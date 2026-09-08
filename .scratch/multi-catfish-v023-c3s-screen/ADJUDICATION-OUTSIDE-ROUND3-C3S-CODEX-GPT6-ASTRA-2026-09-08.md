**ADJUDICATION-OUTSIDE-ROUND3-C3S-2026-09-08.md**

唯讀交付本文，未寫檔、未連網、未執行實驗或讀取 running outcomes。K＝指定 contract（含 Addendum A）；R＝旁附 controller review；P＝指定 UNSEALED plan。

K 的 SHA-256 完整核符 `1b19e0f4c6c5f1591e3ca670da368fea0e785ec70fc51af5a9fe9edfdbfc7a7f`。本機副本仍有 DRAFT 標頭、mode 0664，無 seal sidecar；SEALED／RUNNING 依 controller 本輪陳述接受，並非本機驗證。P 缺席，以下替換文字依貼文引用制定，不冒稱已核對 P 全文。

裁定：**AMEND_PLAN；sealed screen 科學規則不變。** A＝已涵蓋；B＝錯誤／不准如此推論；C＝可採納。表中 RO＝`REPORTING_ONLY`、NN＝`NOT_NOW`、AP＝`AMEND_PLAN`。

| Q&A 具體點 | 分類、依據及處置 |
|---|---|
| 目前仍 DRAFT／UNSEALED | B：適用舊 package 標頭，不能推翻 controller 所述後續封存；receipt 揭露版本差異。 |
| decision-time information 不等於 computational deployability；matched physics 有 model privilege | A：K§2 資訊限制；C：RO／AP，收窄 deployable 用語。 |
| centralized controller、及時 telemetry、calibration、atomic execution | A：K§2–3 部分涵蓋；C：RO／AP，明列整組假設。 |
| unilateral／joint × nominal／degraded estimator | C：screen NN；P 明確 defer，不能把「cheap」當已驗證成本。 |
| 固定誤差幅度、相關結構、seeds；同 link 跨候選一致 | C：未來獨立 diagnostic 必要條件；此次不新增實驗。 |
| matched anchors 不證 closed-loop robustness；S3 是另一次 learner experiment | A：K§1、4、8；B：不得以 simulator-trained S3 宣稱消除 model privilege。 |
| S0-U +1.523%、S0 +1.813%；不能全歸 evacuation | A：K§1、S0 原始報告；不是機制占比的因果分解。 |
| state drift 是 treatment-mediated effect | A：K§4、Addendum B；禁止回填 BASE anchors。 |
| initialization、短 horizon、equal seeds 不足；keying／purity | A：K§4、8；C：RO 綁定實作驗證證據。不能要求兩臂選不同 links 後 channel 相同。 |
| 四 world clusters，非十二 worlds／36,000 independent observations | A：K§4–5；C：RO／AP，強制明示。 |
| kill rule 是 operational progression；微小正值可過、容許少36服務次、不證公平 | A：K§5、7；不得追加 significance／fairness gate。 |
| effect sizes、全部 world differences、累積曲線 | A：K§5 已要求前兩項；C：RO／AP 補 cumulative reporting。 |
| P 的 30→10 steps | C：AP，保留30；十步只能回答不同 estimand。 |
| historical η_ref 非隱藏 tuning，但不保證 ratio alignment／跨軌跡收益 | A：K§3 固定來源；C：RO／AP 補限制。 |
| 0.8／1.0／1.2× sensitivity，全值報告、不得 rescue | C：screen NN；AP 採 cached rescoring，只證 choice stability。 |
| phase timing、mean／median／p95／max | A：K§6、Addendum D。 |
| hardware、threads、cache、unique counts、interval ratio、compute exclusions | A：unique counts 已有 runner 欄位；C：RO／AP 補齊。 |
| 約100秒＝3.3×；episode parallelism 只增 throughput；lite十秒未測 | A：K§6、Addendum B 為估算；C：RO／AP，實測前不宣稱達標。 |
| qualification outcome-dependent，但非事後選規則；兩次過關機會 | A：Addendum C、R；C：RO 說明 shared BASE、完整揭露兩臂。 |
| both→lite、one→該臂、none→stop；不按 gain／latency 改選；fresh FULL2 必要 | A：Addendum C、K§7；INVALID／INCOMPLETE 不得算失敗。 |
| 第三 Catfish 是架構重定義；三 contrasts 不證 final-system C1/C2 marginals | A：K§7 部分涵蓋；C：RO／AP 採修正文句。 |
| additive closure 僅限 tested target/composition | A：K§1；不是所有 additive encodings 的不可能定理。 |
| myopic reconfiguration 是最可能 NO_SUPPORT 機制 | C：可列假說；B：尚非事實，尤其 service-only failure 未必符合。 |
| failure codes、累積 B/E/service、reversals、tracking、同態 residuals、禁止 rescue | A：K§5、8 已有 codes／禁止 rescue；C：既有資料 RO，新 replay screen NN；P 預宣告描述協定。 |

事實校正：S0 數字、36 次服務容許量及四 clusters 均正確。100／30.08＝3.324，102／30.08＝3.391；二者皆是規劃估值，不能稱實測 latency。比例恆等式在兩臂總能量皆正時成立；「FULL2 EE 較高」只表示舊能源價格**可能**錯配，並非必然失敗。Immediate realised losses／後續惡化只能支持候選解釋，不能單憑曲線確診 ranking error／deferred costs。

P 的最小修訂如下；引號內為可直接置入的 exact text。

1. **替換 horizon 條款：**

   「FULL2+C3-S 與 FULL2 在各 ladder rung 均執行100 users、30 canonical steps（0–29），每步30.08 s，每集902.4 s，各自維持 closed-loop trajectory。主 estimand 為此30-step panel 的 pooled ratio-of-sums EE 與 served fraction。不得以增加10-step episodes 代替30-step persistence；成本不足報 INCOMPLETE，不縮短 horizon。既有 rung、world allocation、release barriers 與決策規則不變。」

2. **加入假設與 endpoint 範圍：**

   「C3-S is a nominal model-based coordinator evaluated under matched simulator physics。評估假設 centralized controller、及時 geometry／committed-state telemetry、正確校準的 channel／interference／power models 與 atomic execution。未證明實機 prediction accuracy 或 computational deployability。Network EE 不含 controller computation energy，亦未模擬計算延遲造成的執行滯後；wall-clock latency 另報。」

3. **加入 η_ref diagnostic：**

   「Primary η_ref 保持 binary64 `0x1.d94fb72305d6ap+26`。在首個100-episode rung 的全部預定 worlds、lineages、30 steps，對主 C3-S 軌跡既有 nominal candidate cache，以 exact rational 倍率4/5、1、6/5重評；沿用同一 guard、catalog、ties，不新增 seeds 或 physics evaluations。逐值報 selected ID、相對primary的choice agreement、nominal B/E/service及score；全數保留。此為 non-decisional choice-stability diagnostic，不估 closed-loop EE sensitivity，不改 primary、progression 或救援失敗。Rescoring 與輸出成本另記。」

4. **加入 latency 報告：**

   「逐臂報完整 decision latency（state取得至action返回）及phase mean／median／p95／max、latency/30.08、超時次數／分母；附hardware、CPU allocation、threads、worker concurrency、cache scope／cold-warm條件、catalog／unique evaluations與cache hits。Lite與同態memoization可能降低成本，仍須實測；保留全部evacuations及固定開銷，不保證十倍加速或低於30.08 s。跨episode並行只代表throughput。Latency不是gate，不觸發fallback、pruning或改選。」

5. **替換 framing；第一句採原文，第二句修明條件：**

   “C1 and C2 remain training-time Catfish mechanisms producing two learned per-user heads, while C3-S is a newly defined deployment-time model-based set-level coordinator, with no third learned Q-head.”

   “The tested additive C3 target/composition showed no positive oracle-level marginal in G0–G3. Three positive staged contributions require FULL2-versus-DROP_C1, FULL2-versus-DROP_C2, and FULL2+C3-S-versus-FULL2 each to satisfy its declared EE/service criteria; these contrasts do not establish C1/C2’s positive marginal within the final coordinated system.”

6. **加入 reporting／NO_SUPPORT descriptive protocol：**

   「Screen有四physical-world clusters、三條重用lineages及每臂36,000 user-step opportunities；不得作36,000獨立觀測。Confirmatory panel報實際distinct-world數。所有結果均報failure codes、全部world／lineage差異、逐步累積bits／joules／served與opportunities。記錄physical association A→B→A（連續三步、A≠B）reversals及native tracking／handover events，勿以slot變號代替。

   「同態residual診斷固定為首rung第一個預定world、全部lineages、steps 0–29；commit後以隔離的predecision-state clone及相同keyed realised field，比較selected action與該C3-S state的BASE proposal。報nominal／realised ΔB、ΔE、Δserved、Δ(B−η_refE)及其差，不拿另一臂state代替。不得回饋selector、調參或rescue；無可驗證state則報不可得。」

7. **加入 degraded-estimator disposition：**

   「本plan不納入degraded-estimator實驗。未來如執行，須在其outcomes前另封non-decisional協定，固定catalog cross、error magnitudes、bias／correlation、physical-link keying、seeds、coverage及成本；同link跨candidate共用誤差，matched-anchor結果不宣稱closed-loop robustness。」

Confirmatory runner **必須**支援30-step termination、coverage／denominator驗證及上述 reporting／隔離diagnostics。本機 runner 已存逐步B/E/service與unique counts，但action hash不能還原reversals，selected nominal不能替代同態BASE residual。

Running v1 不熱改。Hardened v2須另綁code／schema／authority、保留producer版本；merge只從authenticated資料衍生報表，缺欄位標 unavailable，不回寫receipts或為補報重跑有效結果。Screen不追加η／degraded／counterfactual實驗。

`ASTRA_ROUND3=AMEND_PLAN`

`ASTRA_SCREEN_REPORTING=assumptions_and_claim_scope,world_cluster_count_and_lineage_reuse,all_world_lineage_effects,cumulative_bits_joules_served_opportunities,decision_latency_over_30p08,deadline_exceedance_count_and_denominator,hardware_threads_affinity_concurrency,cache_scope_conditions_hits_unique_counts,controller_energy_and_delay_exclusions,matching_and_purity_evidence_refs,both_arm_eligibility_and_shared_BASE_disclosure,producer_version_and_field_availability`