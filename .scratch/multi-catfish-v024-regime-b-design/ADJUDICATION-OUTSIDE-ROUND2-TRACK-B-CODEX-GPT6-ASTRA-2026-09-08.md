**ADJUDICATION-OUTSIDE-ROUND2-TRACK-B-2026-09-08.md**

只讀交付，未寫檔、連網、SSH 或讀取 B outcomes。memo／protocol 本地內容與 review ZIP 一致；sealed 狀態依 owner 提供。外部文獻數值以下標明轉引，不冒稱本次重新核實原文。

來源：F＝[fable-deep-research.md](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v024-regime-b-design/outside-round2/fable-deep-research.md)，D＝[astra-docx.md](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v024-regime-b-design/outside-round2/astra-docx.md)，CQ＝[claude-qa.md](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v024-regime-b-design/outside-round2/claude-qa.md)，GQ＝[gpt-qa.md](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v024-regime-b-design/outside-round2/gpt-qa.md)。M＝sealed memo；P＝sealed protocol；R＝未封存 prereg。A 若指 R，表示草稿已涵蓋，尚非生效規則。以下 C→P／G／D 分別代表 `AMEND_PREREG`／`AMEND_GRID_BEFORE_MERGE`／`DEFER`。

**1. 去重裁決表**

| 具體提案／異議；來源 | 裁決與理由 |
|---|---|
| Constructed regime、歷史失敗、完整網格及條件式結論；F§4、D§5、CQ§1、GQ§1 | **A**：M§1、R§0/9；不是一般 LEO efficacy。 |
| finite demand 是「唯一先天非加性軸」；CQ§1a | **B**：「唯一」錯誤；activation、max-power、干擾本已有交互。有限需求使容量飽和、聯合撤空可能保住 goodput，正是機制問題，不保證正收益。 |
| 明列 minimal-change 選軸及已知 E1 後定門檻；CQ§1a–b | **C→P**：揭露實際時間序，不能補寫未經紀錄支持的「刻意略高於 E1」。 |
| Mbit/s／Mbit/slot 混用、200 負載極端；F§1、D§2 | **C→G**：採下述 v2 網格；屬科學設計修訂，不是單位勘誤。 |
| ∞/25/10/2.5 與 ∞/50/10/5 替代案；F§1、D§2 | **C→G**：採後者，保留兩個原有情境，補入較有直接用量依據的低負載 proxy。 |
| 定義 terminal、homogeneous demand、expiry、無 retry／DTX／重分配、30.08 s 時鐘；F§1/(A)、D§2/6 | **C→P**：明列 synthetic reserved-service、慢速 association；不稱典型家庭流量或標準時槽。 |
| 加入 heavy tails、activity、queues、時空相關與更完整通道積分／weather；D§2/6 | **C→D**：另一工作負載／物理研究；摘錄未展示不等於程式沒有。 |
| 更換 PA curve／OBO、提高固定成本、sum-power、容量及 sleep；F§2、D§3 | **A**：M§2、R§0/2 已排除；如研究，**C→D**，不得混入本輪。 |
| PAE≠drain efficiency、module≠beam、RF chain≠整束、digital precoder≠整星；F§2、D§3 | **C→P**：明列 accounting boundary；EE denominator 是 modelled communication subsystem。 |
| Del Re／ESA wattage、標準需求與 sum-power 引文、Gemini 凸性及增益預估；F(C)、D§6 | **A**：M§2、R§0 不採這些依據；未找到文獻不能寫成不存在。精確 bibliography mapping **C→P**。 |
| 只宣稱 TDM 即修復 max／rate 一致性；F§2/(B) | **B**：不足，見第2節；完整 reference-plane 修訂 **C→D**。 |
| beam hopping／MARL／Shapley／DCG 可比性及外部百分比；F§3、D§4 | **A**：M§3/7 限定本架構；外部 throughput、DTX power savings 不能移植為本模型 EE 預測。 |
| 控制器位置、demand 可得性、telemetry age、訊息量、latency、共同執行時點；D§4 | **C→P**：部署資訊契約及量測義務仍須補齊。 |
| S0/S3 同 catalog／資訊／guards，mean fading 非 expected goodput，實際違規不得 oracle repair；D§4 | **A**：R§6 已固定多數項；限制措辭與 timing **C→P**。 |
| 反覆 sealed iterations 直到三正；GQ§1、D§5 | **C→P**：R§8 尚須明禁以新 contract 洗成 outcome-independent search。 |
| oracle 失敗後試下一 grid；CQ§1c | **B**：違反已選點不回退原則；採 GQ§1 的先鎖點、失敗停。R§3/5 部分涵蓋。 |
| 選點順序、method-dependent enrichment、threshold conjunction；F§4、D§5、GQ§1 | **C→P**：不是純 realism selection；門檻管選點／進程，不管是否報告。 |
| calibration panel 與 λ/κ 時序、C2「one-step」矛盾；F§4、GQ§1 | **A**：R§3/5/6 已分 λP/κP、λB/κB，保留 OPS-3 H≤3；須綁定實際 manifests。 |
| 改成 G0-relative 5%/1% thresholds；CQ§2 | **C→D**：另換 estimand；保留 M 門檻，G0-relative 差另報 descriptive。 |
| J/U 非巢狀，改 union；D§5、GQ§2 | **A**：M§4、R§4 已承認；union **C→D**，不稱 unrestricted coordination premium。 |
| 任意大小 signed interaction、λprobe、ΣΨ/ΣV；CQ§2、GQ§2 | **A**：R§4 已定 signed aggregate、pooled ηref；比率 **C→G** 僅描述性，分母零／非正記 N/A，不新增門檻。 |
| 三個 worlds 的「正」應為 J−U；CQ§2、GQ§2 | **C→G**：固定 global witnesses 的分世界 contrast，見修訂4；不是推論檢定。 |
| probe 無 M12、U/J demand feasibility 未定；GQ§1–2 | **C→G**：明定 phase reference 與 post-solve rejection。 |
| 新增 pooled bits −0.1% NI guard；CQ§2 | **C→D**：這是更強的服務 estimand；當前保留 demand guards，另報 Δbits/Δjoules，未保住 bits 不得稱「等量節能」。 |
| 強 M12 吸收 headroom／重檢門檻與停止；CQ§1d/4、GQ§4、D§6 | **A**：R§6 重跑§4、不換點；必須在 C3/set targets 前停止。 |
| 第四 demand-aware carrier；CQ§4 | **C→D**：新增 carrier、acquisition 與 heuristic 定義；不能當原 tape 的免費 merge 修訂。 |
| nominal re-solve 保留不到 oracle 一半即 S0 dead；CQ§4 | **B**：不是已證 kill threshold；跨 anchors 的 pooled solve 也未必 deployable。額外診斷 **C→D**。 |
| FULL/DROP masking vs retraining、set-family ablations；CQ§3、GQ§3、D§5 | **A**：R§5/6 已分 target removal／retraining；set proposal ablations **C→D**，不混入 additive H2。 |
| 三正只看 estimates；GQ§3、CQ§3、D§5 | **C→P**：三 marginal 各要求 paired CI 下界>0；明列 conjunction／multiplicity 與固定三 policies 的推論範圍。 |
| H2 降為 exploratory／EE-neutral C2 算成功；F§4、CQ§3 | **B**：改寫 owner 三正目標；可另報服務收益，不能代替正 EE marginal。 |
| coordinator 成功救回 additive；CQ§3、GQ§3 | **A**：R§1/9 明禁；CQ「不存在第三 additive Catfish」仍過強。S3未勝S0只能說未證 learning 增益。 |
| IQM、performance profiles、bootstrap、hashes、失敗與 repairs；F§4/建議、D§5 | **A**：R§6–8 已有 pooled ratio bootstrap／provenance；IQM 替換主 estimand **B**，補充 profiles **C→D**。 |
| 優先 original-regime deployability，暫緩完整 B campaign；CQ§5、GQ§5 | **C→D**：優先已運行 S0/oracle screens；保留 B map。R§8 已是八-arm **759 worker-hours** 上限，勿沿用五-arm估算承諾期限。 |

**2. 外部文件的事實錯誤**

- **F§1**：200 小於其自行算出的 250–290 Mbit/s；若 rate 為288.3，cap=200 會截掉約31% capacity，不能推出「rarely binds」。其「高於 speed-test peaks」也與自引284–304 medians矛盾。**G1是高負載，不是已證 effectively full-buffer**；等價須檢查相關 profiles 的 cap binding，本次未讀 tape。
- **F§1/4**：Osoro/Oughton 數值是模型 capacity，不能直接當 measured demand；25 對應較低密度。calibration 不可能「所有 training 前固定」而同時由新 M0 產生；thresholds 不得 gate reporting；「之後開 TEST」直接違反本研究。
- **F§2/(C)**：chip/component 與整星功耗不能直接證明 constants「低幾個數量級」。本地 REFERENCES 已列 Zhu[7]、Ye[16]；You[26] 是另一篇 TWC 論文，不能把新找到的 TCOMM 文章直接稱為既有引用的已確認身分。D 的來源補充應另列。
- **F 的 TDM 修辭**不等於一致性證明：[step.py:943](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/step.py:943) desired signal 使用 individual link power，輻射／PA 使用 beam max。應如實稱繼承的抽象，不能宣稱 literal constant-power TDM 已驗證。
- **CQ§1/3/5**：有限需求不是唯一非加性來源；失敗不證所有 additive 方法不存在；B也不是唯一能研究 coordination 的 regime。E1 已證 U +1.992%、J +2.222%，差為 reference EE 的 **0.230 percentage points**；不是部署收益。
- D、GQ 對舊 package 的未定事項多屬有效批評；其中已被 R 補定者是**版本差異**，不能當成現草稿仍缺失。

**3. 封存前最小修訂文字**

1. **Units／grid：**「\(d\) 為每 terminal 持續 offered rate，單位 Mbit/s；每30.08 s interval 提供 \(30.08d\) Mbit。v2：G0=∞、G1=50、G2=10、G3=5；依此順序選點。」對應∞／1,504／300.8／150.4 Mbit。5 的量級依 D§2 轉引 Preseem 3–4、OpenVault 3.43 Mbit/s；10依轉引 Fastenbauer 情境；50保留 heavy-transfer scenario。均非 LEO field calibration。F 的25/2.5主要來自 capacity proxy，故不優先採用。

2. **Pre-outcome boundary：**「v2 在任何 B grid-dependent accounting、分布檢視、solver／witness／marginal 結果供設計者檢視前封存。raw acquisition 與 demand grid 無關，energy 不變，可沿用其 authenticated tape；不得根據 raw rates 反推有利 grid。紀錄 acquisition、amendment、首次 merge／access 時間；若已有 outcome exposure，揭露 deviation，不稱 pre-outcome。」

3. **Stopping／disclosure：**「本 registration 僅一固定網格、一 selected point、一 campaign。四點完整報告後，先鎖定第一個通過 map 的點，再做該點 oracle gate。無合格點為 NONE；oracle、強 M12 或 campaign 有效失敗即終止，不換點、不修訂科學設定續追三正。後續 redesign 均屬 outcome-informed follow-up，披露全部歷史；資源中斷標 INCOMPLETE，僅修復 invalid units。」

4. **Probe 定義：**「保留5%／1%／0.5%；λprobe=各 grid 三 carriers 合池 ηref。U/J 均先作原 service-constrained exact solve，再以各自 witness 檢查 demand fraction≥0.95且≥carrier reference−0.001；任一失敗該 grid 不合格，不換次佳 witness。G0 demand=N/A。world-positive 定為兩個 global witnesses 的 \(\eta_{J,w}-\eta_{U,w}>0\)，至少3/4；另報 J−reference。強 M12 重檢使用相同規則、reference 換 M12。」

5. **成功推論：**「H2 每項 FULL−DROP 均須點估計>0、paired world-cluster 95% CI下界>0及 guards；三項構成 intersection-union conjunction。個別／其他對比不冒稱 familywise significance。world CI conditional on三條固定 trained policies。服務改善不能替代 EE 三正。」

6. **模型與文獻界線：**「研究測試需求飽和能否暴露並轉換協調機會；不假定其必然存在。模型是 homogeneous expiring reserved-service abstraction，沿用 communication-subsystem energy accounting；非代表性 broadband、真實 payload 或已驗證 TDM。」固定、揭露來源 mapping、實際 Δbits／Δjoules／expired demand。

7. **部署與假說：**固定 controller、資訊時間戳／可得性、通信與計算時限、同步執行及實際違規計數；保留 S0/S3 公平契約。R§1 H4 應稱 **oracle-to-predictor conversion gap**，不能把所有差距純歸因於資訊缺失。

**4. Authority 與排程裁決**

**必須有 versioned successor，不能只改 prereg。** M v1§2/4、P v1 的 grid／world rule／iteration 規則都受影響。保留 v1 bytes，發布共同綁定 predecessor hashes 的 v2 amendment／successors，作為 merges 的唯一 authority；R 同步引用 v2。raw acquisition authority 可保留，merge bindings 必須更新。

原 regime 的 S0／oracle-marginal probes 依 owner 回報正在運行，本次未遠端核驗；它們符合 global view§10及 H4 的 conversion 問題，應先取得有界診斷，不重開相同工作。E1 anchors 的結果仍是 development screen，不能充當 fresh confirmation；也不得流入 B 網格調整。B map 可並行，完整 campaign 暫緩；regime A 結果與 no-TEST 邊界不變。

ASTRA_ROUND2=AMEND_GRID  
ASTRA_GRID_UNITS=sealed-v1 d is Mbit/s per terminal, not Mbit per slot; D_slot=30.08*d Mbit. v1 G0/G1/G2/G3=∞/200/50/10 Mbit/s; proposed-v2=∞/50/10/5 Mbit/s, equivalent to ∞/1504/300.8/150.4 Mbit per 30.08 s slot.

