# PREREG-V024-REGIME-B-DRAFT-2026-09-08.md

## 0. 狀態與揭露

**DRAFT／未凍結；本文件不構成執行許可。** 本次僅唯讀起草，未修改檔案、連網、SSH、訓練或開啟 TEST。

依據：同目錄 Astra design memo、Gemini physics proposal、`TRACK-B-PROTOCOL-2026-09-08.md`、`V024-WORLD-DERIVATION-2026-09-08.json`；另依 E1 result record 及 `artifacts/PREREG-FROZEN-2026-08-25-R2.json`（R2）。衝突依本次使用者要求、controller protocol、Astra memo、Gemini proposal 順序處理。以下「**補定**」均表示原文未充分指定、現在採用的固定解讀。

Regime A 的 E1 為 U₁ **+1.992%**、J₁ **+2.222%**，兩者皆 HEADROOM；這是 privileged finite-panel oracle evidence。B 的理由是尋找**更大、deployable-information-reachable headroom，以及能表達 coordination 的決策規則**。

論文必載：

> Regime B 是受 regime A 歷史結果啟發、前瞻宣告機制與選點規則的 constructed regime；regime A 已具有 unilateral 與 joint oracle headroom，其 C3 負面結果與 two-Catfish 主研究保持不變。B 完整揭露候選網格及 development selection，結論限於選定 regime、模型與資訊邊界；TEST 始終關閉。

Gemini 提案提供 finite-demand 動機；其 DTX、sum-power、額外固定功耗、增益預估及「A 無收益」推論均不納入。

## 1. 假說與 falsifiers

| 假說 | 固定檢驗與反證 |
|---|---|
| H1 | G1–G3 至少一點通過 §4 全部門檻；三點有效完成且皆不通過即反證。 |
| H2 | 選定點的 C1、C2、C3 **各自**具有正 learned marginal：M123 對每個 DROP 的 pooled EE 嚴格增加並通過 guards；任何一項不成立即反證。 |
| H3 | S3 比 M123 轉換更多 headroom：S3 通過正式增益門檻，且 ηS3−ηM123 的 paired 95% CI 下界 >0；否則不支持。 |
| H4 | privileged oracle 與 deployable S3 存在正資訊落差；同 anchors、同 catalog 下 oracle−S3 的 pooled EE 差及 paired 95% CI 下界皆 >0，且 oracle 通過 guards；否則不支持。 |

**補定：**H2 的 FULL 固定為 M123；S3 成功不能替代 additive 三頭逐頭成功。H4 使用替換 configuration predictor 的配對診斷，不把不同軌跡差全部歸因於資訊。

## 2. Physics change

\[
B_u=\min(\Delta tR_u,\Delta td_u),\quad
B_N=\sum_uB_u,\quad E_N=\Delta tP_{\rm system},\quad
\eta=\frac{\sum B_N}{\sum E_N}.
\]

每人每 interval 注入固定需求，未交付 bits 到期並完整記錄；不跨槽排隊。Carrier 啟動即維持整個 interval，沒有 micro-sleep、DTX 折扣或剩餘頻寬重分配。

| Grid | 每人 demand | 每 interval demand |
|---|---:|---:|
| G0 | ∞，full-buffer control | ∞ |
| G1 | 200 Mbit/s | 6,016 Mbit |
| G2 | 50 Mbit/s | 1,504 Mbit |
| G3 | 10 Mbit/s | 300.8 Mbit |

保留 R2 的 100 users、28 actions、Δt=30.08 s、10 steps、D2、TLE、mobility、warm-start、PA、\(p_b=\max p_u\)、1.65 W legal cap、interference、頻寬及 service feasibility。G0 必須回歸原 accounting。Capacity、delivered bits、expired bits 分欄；所有 EE／C1／C2／C3 的 bits 改用 delivered bits。需求值為預設服務情境，非 field calibration。

## 3. Panels、seeds 與 selection

定義無換行 ASCII 的
\[
h(s)=\operatorname{int}_{big}(\mathrm{SHA256}(s)[0:8])\ \&\ (2^{63}-1).
\]

World seed 固定為 `h("V024_REGIME_B/world/{i}")`：

| 階段 | i | 配置 |
|---|---|---|
| Probe | 1–4 | 三個 reference carriers，各10步 |
| Source TRAIN | 101–116 | 三 lineages，各10步 |
| Learner validation | 201–208 | 三 lineages，各10步 |
| Stage B | 301–304 | 三 lineages，各10步 |
| Stage C | 1001–4000 | 三 lineages，各3,000 episodes |
| Calibration | 5001–5016 | 三 lineages，各10步 |

Probe seeds 依序為 `5683200792433982503, 7374843801585642838, 3226893802015760720, 1341435503386059806`。其餘既列數值逐項採 seed JSON；Stage C 首末為 `2877333598185392753`、`4389978391156024947`。全部3,048值由上述公式唯一決定；已重算既有表且內部零碰撞。

**補定：**lineage domains 為 `V024_REGIME_B/lineage/{1,2,3}`，數值依序 `8710838092272495692, 8727472625176752087, 6643398588015606084`。M0 training episode k=1–9000 使用 `h("V024_REGIME_B/modqn-world/{k}")`；各 lineage 共用 worlds，初始化及 sampler 分離。其他 RNG 使用 `h("V024_REGIME_B/{role}/{lineage}")`，role 固定為 `init-q1, init-q2, init-q3, init-set, sampler, policy, mobility, warmstart`。Keyed field namespace 固定 `MCRL_V024_REGIME_B_V1`，不含 arm、grid 或 lineage。

僅使用 R2 TRAIN dates；development、validation、confirmation worlds 分離。Freeze 前核對所有 A／歷史／已分配 world 與 RNG inventories，包含 E1、F1–F3、R7、successor 及 `2026121721`；碰撞即停止，禁止替換 seed。既有 JSON 的 probe collision 空表不代表完整排除已完成。

四 grid 全跑全報；G0 不選點。**G1→G2→G3 第一個通過 §4 的點即 selected point**，不按最大 EE 選擇。**補定：**oracle failure 不允許改選下一點。

## 4. Regime-map probe

Reference carriers 固定 `nearest-eligible`、`stay-if-possible`、`random-masked`，不是 trained lineages。每 grid 為4×3×10=120 anchors、12,000 opportunities；共用 B physical tape，逐 grid 重算 delivered bits。

\[
U_1=\max_{x_p\in\mathcal U_p}\frac{\sum B_{px_p}}{\sum E_{px_p}},
\qquad
J_1=\max_{x_p\in\mathcal J_p}\frac{\sum B_{px_p}}{\sum E_{px_p}}.
\]

共同約束 pooled served fraction ≥reference−0.001。U 包含 reference 及所有合法 unilateral edits；J 包含 reference 及 E1 完整 evacuation catalog，包括 singleton、empty destinations、失敗 evacuation，不做有利篩選。J membership 沿用 E1 realised served occupancy，僅供 privileged diagnostic。

Exact-rational Dinkelbach＋integer-service DP；binary64 tape losslessly 轉 rational，零 residual 才完成。交付完整 census、primal、backpointers 與獨立 certificate；ties reference-first、lexicographic。U、J 不互相包含，J 非 unrestricted upper bound。

Memo §4 門檻：

1. \(J_1/\eta_{\rm ref}-1\ge5\%\)；
2. \((J_1-U_1)/\eta_{\rm ref}\ge1\%\)；
3. J witness的非加性交互 surplus總和／reference bits ≥0.5%；
4. 至少3／4 worlds joint方向正，且witness通過第3節 demand guard。

此處原 memo「第3節」即本稿 §6 guards。**補定：**interaction 為有號的 \(\sum_p[V(S_p)-\sum_{i\in S_p}V(\{i\})]\)，取 \(V=\Delta B-\eta_{\rm ref}\Delta E\)，不截正；world direction 用同一 global witness 的分世界 pooled EE。三 carriers 合池。

| 結果 | 決定 |
|---|---|
| U、J皆有headroom | 仍須全部 coordination 門檻 |
| 只有U | unilateral headroom；不選 |
| 只有J | 仍須全部門檻 |
| 皆不足 | 本網格未找到合格點 |
| INCOMPLETE／INVALID | 無科學判決 |

完整 k=2 僅在事前 census ≤100,000 額外 profiles 且 ≤2 worker-hours 時執行；否則 `NOT_RUN`。不截斷後稱 exact。

## 5. 訓練前 oracle marginal probe

每個 §4 合格點均使用相同120 anchors，比較：

`BASE-carrier, +C1, +C1+C2, +C1+C2+C3, privileged-set, DROP_C1={C2,C3}, DROP_C2={C1,C3}, DROP_C3={C1,C2}`。

**補定：**BASE 固定 carrier action；其他 additive arms 直接以 exact target surfaces 相加作 masked argmax，不另加 carrier score，ties 最低合法 index。DROP 在此移除對應 exact source；不更新 learner。僅 reference continuation，非八條 adaptive rollouts。

為避免訓練前校準循環，固定以 calibration worlds×三固定 carriers 取得
\[
\lambda_P=\sum B/\sum E,\qquad
\kappa_P=\sum B/\sum C_{\rm served}.
\]
此 pair 僅供 pretraining oracle，不冒稱 λB／κB。

C1 exact target：
\[
q_{1i}(a)=[\Delta B_i(a)-\lambda_P\Delta E_N(a)]/\kappa_P.
\]

C2 保留 OPS-3：
\[
H_t=\min(3,9-t),\quad
z_i(a)=H_t^{-1}\sum_{h=1}^{H_t}
[\chi_h\Delta t(\min(R_{ih},d)-\lambda_P\Delta P_{Nh})
-(1-\chi_h)\kappa_P],
\]
\[
q_{2i}(a)=[z_i(a)-z_i(b_i)]/\kappa_P.
\]
Service-loss 為 absorbing；H=0 全零；background、opening 與 projection 語義沿用 OPS-3，不改成 adaptive rollout。

C3 沿用 R7 pair selector、LC-SRS：
\[
V(S)=\Delta B_N(S)-\lambda_P\Delta E_N(S),\quad
\Psi=V(\{i,j\})-V(\{i\})-V(\{j\}),
\quad q_{3i}=(e_i+\Psi/2)/\kappa_P,
\]
\(e_i\) 為 unilateral nonfocal delivered-bit delta；保留 sparse writes、符號及 tie rules。Privileged-set 將 §6 predictor 換成同 catalog 的 exact outcomes。

三 oracle marginals 固定為 ηFULL−ηDROP_i。**三者皆 >0，且 FULL 通過相對每個 DROP 的 service／demand guards，才允許 selected point 訓練。** 任一不成立即報告並停止該點；selected point 失敗則本輪無 campaign。單步替換是 target-level oracle，C2 仍保留其 H≤3 target。

## 6. Full campaign

| Arm | 固定定義 |
|---|---|
| M0 | 全新 MODQN-B |
| M12 | FULL2-B |
| M123 | additive Q1+Q2+Q3 |
| S0 | M12 proposals＋nominal-physics set decoder |
| S3 | 相同 proposals／decoder＋learned configuration predictor |
| DROP_C1-B | M123 的 C1 neutral-source retraining |
| DROP_C2-B | M123 的 C2 neutral-source retraining |
| DROP_C3-B | M123 的 C3 neutral-source retraining |

DROP 為同初始化、獨立 optimizer、同 budget 的 source ablations，不是 inference-time removal。M12 與 DROP_C3 分列並驗證差異，不預設等同。

M0 每 lineage 固定9,000 episodes、final policy；沿用 R2 training constants，**補定 learning rate=0.001，不執行 P6 sweep**，r1 使用 delivered rate。以三個新 M0 在 calibration panel 的合池結果固定
\[
\lambda_B=\sum B/\sum E,\qquad
\kappa_B=\sum B/\sum C_{\rm served}.
\]
零／非有限分母即 INVALID。不得 sweep、逐 arm 校準或使用 validation／Stage C 校準。

C1–C3 使用 §5 targets，換成 λB／κB；learners 預測其 conditional expectations。Q1/Q2/Q3 架構、loss、sampler、neutralization 與 optimizer 完整沿用 V023 V2 100E contract/config，唯一數值替換為 κB；C2 不二次除 κ。

Set catalog：reference b、每人 top-2 unilateral proposals、每個來源束至共同合法目的束的完整 evacuation；membership 由 proposals 決定，禁止讀 counterfactual served identities。Decoder 固定最大化
\[
\Delta\widehat B-\lambda_B\Delta\widehat E+
\kappa_B\sum_u\Delta Q2_u.
\]
Predicted served count ≥reference−0.1；predicted demand-satisfied count ≥95 且 ≥reference−0.1。Reference 永遠保留，atomic execution、lexicographic ties；不加 outcome rescue gate。

**補定 set learner：**每 user 輸入 Q1 的228 features、Q2 的448 features、28維 mask/reference/proposed-action/top-2-membership 各一份及 \(d/(200\,{\rm Mbit/s})\)，共789維；shared 789→64→64 ReLU、mean pooling、64→64→4 linear outputs。四 targets 為 \((B/(100\kappa_B),\lambda_BE/(100\kappa_B),C_{\rm served}/100,C_{\rm demand}/100)\)，等權 MSE。Adam 0.001、betas=(0.9,0.999)、ε=10⁻⁸、weight decay=0；每 epoch 全 catalog 平均梯度一次更新。S0 使用相同 deployable features、unit-mean nominal fading power；兩者禁止 realised fading／future actions。非物理 prediction 的非reference candidate 排除並計數。

執行順序：oracle gate→M0→校準→C1/C2 targets與M12→在 probe worlds×三M12 lineages 重做 §4。若 headroom 消失，報 `COMPARATOR_STRENGTH_FALSIFIER`，不換 grid。通過後以固定 M12 source anchors 產生 C3/set targets。

Stage A：每 source learner 100 epochs、三初始化；兩頭200 route updates、三頭300、set 100。Validation 僅報 prediction，不選 checkpoint。Stage B：4 worlds×3 lineages×10 steps，八 arms＋teacher diagnostics。Stage C：八 arms×三 lineages×3,000完整 fixed-policy episodes，共72,000 episodes，policy 不更新。

復用 V0.23 acceptance chain：sealed targets→typed provider/unit checks→一 epoch scratch export/reload/exact-resume→`PASS_SOURCE_TRAINING_INTEGRITY`→完整 matched Stage B→`PASS_PLUMBING_INTEGRITY`→authenticated runtime admission→200 sequential versus 2×100 chunks bitwise equivalence→Stage C→獨立 verifier 重算。每100 episodes write-once receipt；不以 loss 或 Stage B EE 方向改模型。

Memo §3 正式門檻：

> 正式增益門檻：相對M12 ≥1%，world-cluster paired 95% CI下界>0；served fraction ≥M12−0.001；滿足95% demand的使用者比例 ≥95%且≥M12−0.001。全部arms均報相對M0結果。任一必要條件失敗，即否定該 deployment claim。

**補定：**service／demand 分母皆為全部 user-interval opportunities，unserved 計失敗；G0 demand guard 為 N/A。H2 對每 DROP 使用相同 guards、比較 reference 改為該 DROP；三 marginal 門檻僅 >0，不另加1%。正式三頭成功需 H2 及 M123 正式門檻同時成立。

CI 固定10,000次 paired world-cluster bootstrap，每次重抽3,000 worlds、保留其三 lineages及全部 arms，重算 ratio-of-sums；percentile 2.5/97.5%，linear quantile。PCG64 seed=`2100193046873290111`，domain=`V024_REGIME_B/bootstrap`。各 marginal 均報 CI；三正點估計與統計支持分開報告。

## 7. Integrity 與 separation

Branch=`v024/regime-b`；checkout=`/home/sat/mcrl-v024-regime-b`；工作根 `.scratch/multi-catfish-v024-regime-b/`，正式根 `artifacts/v024-regime-b/`，依 grid／phase／lineage／arm 分離。

僅重用驗證程式及 TLE archive；不得使用 A checkpoints、optimizer、replay、targets 或 field namespaces。R2、A artifacts 與 A 結論 byte-preserved；TEST deny-read。

全部 profiles 檢查 canonical power、served occupancy、unserved zero bits、cost-share conservation、counterfactual state/RNG 無污染及 committed outcome 一致。沿用 F0 roundoff bound，不放寬 scientific comparisons。

Seal 採外部 file SHA-256 sidecar，禁止 self-hash 循環。完整 units atomic publish、0444、重開驗 hash；resume 僅跳過 authenticated complete units。保留所有 failure、repair 前 receipts、grid、arms、lineages、timings、bits／joules／service／demand及相對M0結果。

禁止 outcome 後改 demand、target、λ／κ規則、seed、horizon、margin、架構、epoch、checkpoint selection；禁止隱藏失敗、替換 worlds、截 catalog、把 oracle configuration 當 deployment input。

## 8. Budget 與停止規則

**補定八-arm硬上限：**regime map 24、oracle marginal 24、M0 training 45、target generation 160、source fits＋Stage B＋acceptance 58、Stage C 448 worker-hours；總759。k=2 計入 probe。達任何階段上限即 INCOMPLETE，不減 panels／arms。

Track A 約16 workers時，B最多2個單執行緒 workers，保留2 cores；不得另開大型 fan-out。計時包含 solver、verification，17分鐘不能代表完整 exact pipeline。

本稿只授權宣告一輪：完整 map→oracle→selected campaign。任何有效科學 failure 結束該輪；後續 iteration 必須另立 prospective contract，保留全部歷史。Infrastructure defect 可修復並重播最小 invalid unit；不得重跑有效不利結果。資源延期須獨立 resource-only amendment，不能默默延長。

## 9. 各 outcome 的論文界線

- 無合格 grid：宣告網格未找到 coordination-relevant regime；不主張普遍不可能。
- Oracle marginal failure：該點未支持三 sources 各有正機會。
- 強 M12 消除 headroom：弱 carrier screen 無法延伸至強 comparator。
- H2 成立且 M123 過正式門檻：選定 constructed TRAIN regime 下，三頭各具正 learned marginal。
- S3 成功、additive失敗：支持本 target／interface／composition 的限制；不推論所有 additive 方法不可能。
- Oracle成功、deployable失敗：報告資訊／學習／決策轉換落差；不宣稱 deployment efficacy。
- S3未勝S0：不得宣稱 configuration learning 額外增益。
- INVALID／INCOMPLETE：無科學裁決；短 panel 不替代正式 campaign。

所有 outcomes 均保留 A 結果；不提出 TEST generalization claim。

## 10. Freeze checklist

- [ ] Controller 明確接受全部「補定」，科學規則在 B outcomes 前封存。
- [ ] 本稿、Astra/Gemini、protocol、E1、R2、V023 contracts/config 的 provenance manifest：`<<BIND_AT_FREEZE:PROVENANCE_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:PROVENANCE_MANIFEST_SHA256>>`。
- [ ] 完整 seeds、exclusions、RNG、TRAIN-only plan：`<<BIND_AT_FREEZE:PANEL_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:PANEL_MANIFEST_SHA256>>`。
- [ ] Physics、targets、learner、decoder、solver、verifier、tests、environment、TLE、launch arguments closure：`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_SHA256>>`。
- [ ] G0 regression、demand accounting、oracle certification、DROP source identity、resume／chunk equivalence驗證程序已固定。
- [ ] Output roots 未存在；checkout／commit、thread limits及TEST拒讀已核驗。
- [ ] 校準值日後僅由已固定規則產生並封存；generated checkpoints／receipts 僅作 phase admission bindings，不重新選科學設定。
- [ ] 最終 draft file digest 外置：`<<BIND_AT_FREEZE:PREREG_FILE_SHA256>>`；launch seal：`<<BIND_AT_FREEZE:LAUNCH_MANIFEST_SHA256>>`。未完成前維持 DRAFT。

ASTRA_V024_PREREG=DRAFTED