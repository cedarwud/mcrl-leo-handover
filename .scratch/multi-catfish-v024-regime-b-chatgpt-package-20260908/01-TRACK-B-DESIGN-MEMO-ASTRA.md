**V024 REGIME-B DESIGN — a coordination-relevant regime for C3, pre-outcome**

**1. Framing and disclosure**

Regime B 的問題是：**在事前指定、存在可利用協調收益的 regime，原始 additive three-head 或 set-level coordinator，能否將該收益轉成可部署的 pooled network EE 改善？**

Track A 的 V0.23 two-Catfish stage A/B/C 與 E1 照原契約執行，維持論文主結果。Track B 是獨立、條件式研究。

論文必須寫明：

> Regime B 的機制、候選網格、選擇規則與比較架構，在其自身 outcomes 產生前宣告；研究動機來自 regime A 的歷史失敗。完整網格皆予報告，正式 campaign 的 regime 由已宣告的 development screen 選定，因此結果只支持此選定 regime 下的條件式結論。Regime A 的 C3 負面結果與 two-Catfish 主研究不變；TEST 未開啟。

B 可以支持機制、部署與架構邊界；不能證明一般 LEO 網路必然受益，也不能把 oracle、選點結果或 prediction accuracy 寫成 deployment efficacy。

**2. Physics axes、最小方案與固定網格**

對完整 matched panel：

\[
\eta=\frac{\sum B}{\sum E},\qquad
\eta_{\rm new}>\eta_{\rm ref}
\iff \Delta B-\eta_{\rm ref}\Delta E>0.
\]

現行 \(p_b=\max_{u\in b}p_u\)，合法功率 ≤1.65 W，PA saturation 約5.218 W；fixture 中 PA 占94.8%。頻寬為每束166.667 MHz、由 served users 均分，沒有 occupancy admission ceiling。因此「分流」本身不保證省電。[物理實作](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/link_budget.py:439)

| 候選變動／物理或文獻理由 | Δbits、Δjoules 機制 | BASE、C1/C2、coordination headroom |
|---|---|---|
| **PA curve／operating point**：Cripps 的 class-B 近似與 Piacibello 的 Ka-band Doherty 是不同模型；實測 PAE 也不能直接當 drain efficiency。須綁定器件、OBO、失真與工作區間。 | 改效率首先改 joules；只有另外建模 EVM／失真才改 bits。現行平方根 supply 是**凹函數**，不能自行宣稱飽和附近具有凸成本。 | BASE 須重學；C1/C2 的 network-energy delta 全部重算。是否有分流收益取決於真實曲線，不能保證。 |
| **Per-user allocation／target-SINR power control**：獨立 OFDMA 子通道可使用 \(p_b=\sum p_u\)，\(p_u=\gamma_u(N_0W_u+I_u)/g_u\)。 | 距離、干擾、分配頻寬共同影響需求功率與可達 bits；容量不足可能造成 outage。 | BASE 行為改變；C1 變成真正 load-dependent power surplus，C2 須預測資源可行性。可能提供 headroom，但需同步重寫 noise、interference、feasibility；不能只把 `max` 換成 `sum`。 |
| **Capacity／finite demand**：Zhu 等人的 LEO traffic-arrival／queue 模型提供需求有限的文獻動機；任意「每束最多 K 人」沒有同等物理依據。 | \(B_u=\min(\Delta tR_u,\Delta td_u)\)。容量超出需求不再增加 goodput；需求仍滿足時，聯合撤空可保持 bits 並減少 joules。 | BASE 須學會停止追逐無用容量；C1、C2 都改用 delivered bits。可產生 last-user shutdown complementarity。 |
| **Activation／circuit／baseband weights**：You 等人提供 RF-chain 元件功耗；一束對一 chain 仍是模型假設。 | 提高固定成本增加關束收益，不直接增加 bits；baseband 僅在最後一束關閉時節省。 | BASE 更偏 consolidation；C1/C2 都須完整計價。不能把未核實的2.5 W稱作真實硬體值，或為求正結果加大權重。 |
| **Bandwidth sharing**：Ye 等人的 association 模型支持 load-aware resource sharing；既有166.667 MHz来自500 MHz／FRF 3。 | 同 SINR、full-buffer 時，人數可從 beam sum-rate 抵銷；有限需求、異質 SINR或資源約束才打破此抵銷。 | 改頻寬會改 BASE、noise 與兩個 source 的 rate；coordination 潛力仍須與額外 PA 成本比較。 |

文獻依據限本地資料；硬體新數值未經本次原文核實。[文獻索引](/home/u24/papers/mcrl-leo-handover/.scratch/chinese-word-v023-lcsrs-20260905-r2/REFERENCES.md:49)

**建議最小改動：只加入 finite demand／delivered-goodput accounting。** 保留現行 PA、max-power、干擾、頻寬、service feasibility 與30.08 s決策時鐘。每人每 interval 提供固定 \(d\Delta t\) bits，未交付部分到期、完整記錄；不跨槽排隊。採 interval-long active carrier，沒有新增 micro-sleep、DTX折扣或餘裕頻寬重分配。這是明示的服務模型，不代表所有 payload。

| Grid | 每人 demand \(d\) | 用途／固定選擇優先序 |
|---|---:|---|
| G0 | ∞，full-buffer | 控制點，不參與選點 |
| G1 | 200 Mbit/s | 第一 |
| G2 | 50 Mbit/s | 第二 |
| G3 | 10 Mbit/s | 第三 |

數值是事前選定的服務情境，並非 field-calibrated traffic。**四點全部執行與報告。**

只提高 legal cap 不會建立 occupancy→power 因果鏈：既有 recurrence 不因 cap 增大而主動提高功率，max 聚合也不因增加使用者而累加。它可能改變部分 outage，但不保證協調收益；若同時提高 \(p^0\) 或依公式重算 \(p_{\rm sat}\)，已不是「只改 cap」。

**3. Decision architecture、targets、arms 與 falsifiers**

區分 **MODQN-B** 與 **FULL2-B**；E1 舊文件的 BASE 是 Q1+Q2，並非 MODQN。

C1 保留「focal delivered-bit delta − \(\lambda_B\)完整 network-energy delta」。C2 保留 OPS-3 的 \(H_t=\min(3,T-1-t)\)、吸收式 service-loss、offset平均與 reference centering，rate 改為 demand-capped goodput；它仍不是 adaptive rollout。[C1](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_opening_source.py:635)、[OPS-3](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_ops3.py:700)

**Additive arm：**沿用 R7 pair selector、LC-SRS target 與三個28-action heads：

\[
V(S)=\Delta B_N(S)-\lambda_B\Delta E_N(S),\quad
\Psi=V(\{i,j\})-V(\{i\})-V(\{j\}),
\]
\[
Q_{3,i}^{*}=\mathbb E[e_i+\Psi/2\mid I_t]/\kappa_B.
\]

\(e_i\)為 unilateral nonfocal delivered-bit delta。保留所有符號、稀疏寫入與原 tie rule；部署仍是一次 unweighted masked argmax \(Q1+Q2+Q3\)。不加 rescue gate。這公平重測原架構及既定 target family，不宣稱窮盡所有 additive targets。

**Set arm：**Q1+Q2產生完整 reference \(b\)、每人 top-2 proposals；catalog 含 \(b\)、top-2 unilateral edits、每個來源束至共同合法目的束的完整 evacuation。部署依**proposal membership**建集合，不偷看 counterfactual served identities。

C3 改為預測完整配置的 conditional \((B_N,E_N,C_{\rm served},C_{\rm demand})\)，使用幾何、D2、lagged telemetry、demand與完整 proposals；禁止 realised fading／未來 action。Decoder 最大化

\[
\Delta\widehat B-\lambda_B\Delta\widehat E
+\kappa_B\sum_u\Delta Q2_u,
\]

通過預測 service constraints 後 atomic execution；reference 永遠在集合內，固定 lexicographic ties。這是固定 surrogate，最終仍由 pooled EE裁決。

五個 arms：

| Arm | 功能 |
|---|---|
| M0 | 重新訓練 MODQN-B |
| M12 | FULL2-B |
| M123 | additive three-Catfish |
| S0 | 同 catalog／decoder，使用 deployable nominal physics |
| S3 | 同 catalog／decoder，使用 learned complete-configuration predictor |

M123／M12測第三頭；S3／M12測 coordinator；S3／S0測 learning 額外價值。另報 privileged teacher diagnostic，不列 deployment arm。

\(\lambda_B\)固定取新 MODQN 的預定 calibration panel pooled EE；\(\kappa_B\)取同 panel每 served-user interval平均 delivered bits。這是預定計算規則，不做 sweep。

正式增益門檻：相對M12 ≥1%，world-cluster paired 95% CI下界>0；served fraction ≥M12−0.001；滿足95% demand的使用者比例 ≥95%且≥M12−0.001。全部arms均報相對M0結果。任一必要條件失敗，即否定該 deployment claim。

**4. First-24-hour regime-map probe**

沿用 [E1 exact machinery](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-existence-e1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:21)：

\[
U_1=\max_{x_p\in\mathcal U_p}\frac{\sum B_{px_p}}{\sum E_{px_p}},
\quad
J_1=\max_{x_p\in\mathcal J_p}\frac{\sum B_{px_p}}{\sum E_{px_p}},
\]

共同約束 pooled served fraction ≥reference−0.001。U集合為 reference＋所有合法單人改動；J集合為 reference＋原E1完整 evacuation catalog。用 exact-rational Dinkelbach＋integer-service DP，交付 census、primal與獨立 certificate。J不是 unrestricted upper bound，兩集合不互相包含。

World domain固定 `V024_REGIME_B/world/{i}`，沿用SHA256前8 bytes、big-endian、63-bit規則：

- i=1–4：probe；
- 101–116：source TRAIN；
- 201–208：learner validation；
- 301–304：stage B；
- 1001–4000：stage C；
- 5001–5016：calibration。

先檢查排除表與碰撞，衝突即停止，不另挑seed。

首輪以本地既有 `nearest-eligible`、`stay-if-possible`、`random-masked` 三個固定規則產生4×3×10 anchors；它們是**reference carriers，不是三個訓練lineages**。不用任何A checkpoint。最小模型允許共享B內部的raw physical tape，再逐grid重算capped bits、各自exact solve與封存。

現在宣告 coordination-relevant：

1. \(J_1/\eta_{\rm ref}-1\ge5\%\)；
2. \((J_1-U_1)/\eta_{\rm ref}\ge1\%\)；
3. J witness的非加性交互 surplus總和／reference bits ≥0.5%；
4. 至少3／4 worlds joint方向正，且witness通過第3節 demand guard。

| 結果 | 決定 |
|---|---|
| U、J皆有實用headroom | 仍須通過joint額外margin與interaction條件 |
| 只有U | unilateral headroom；不選作本研究的coordination regime |
| 只有J | 支持joint方向；仍須通過全部門檻 |
| 兩者皆不足 | 本網格未找到合格點；不宣稱普遍不可能 |
| INVALID／INCOMPLETE | 無科學判決 |

全部grid完成後，選G1→G2→G3中第一個合格點，**不選最大EE**。再於新訓練FULL2-B anchors重做檢查；若headroom消失，報告 comparator-strength falsifier，不回頭換grid。

完整k=2僅在事前census≤100,000額外profiles且≤2 worker-hours時執行；否則記 `NOT_RUN`，不得截斷後稱exact ceiling。

**5. Full campaign與成本**

採新lineages三組；MODQN固定9,000 training episodes。生成C1/C2、LC-SRS與set-level targets，完成source訓練，再執行：

- **Stage A-B：**100 fixed source epochs、三初始化；驗證target單位、prediction、placebo與出口身份。
- **Stage B-B：**四新worlds×三lineages×十步，五arms與teacher診斷；不以結果修改模型。
- **Stage C-B：**五arms×三lineages×3,000 matched、固定policy episodes；所有完整軌跡實際演化。固定終點，無best-checkpoint selection。

成本必須分開：[latency ledger](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/LATENCY-LEDGER-2026-09-07.md)記錄工程延誤；實測速度另見[rehearsal](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/ENGINEERING-LANE-V4-STAGEC-REHEARSAL-REPORT-2026-09-07.md:46)。

| 工作 | 預算／證據界限 |
|---|---|
| Probe | 12–24 worker-hours含solver reserve；17分鐘只證明12 units取得完成，不含完整exact merge |
| 新MODQN訓練 | 暫列15–45 worker-hours；1.66 s/episode是evaluation，不能當training速度 |
| Target generation | 60–160 worker-hours；舊16 shards曾需約8.6 h wall，新增joint profiles另有成本 |
| Source／C3／set fits及stage B | 12–36 worker-hours；1.25 s/epoch只對已測三arms／三shards成立 |
| Stage C | 舊速度下約140.15 worker-hours；加入decoder overhead預留180–280 |

總量約**280–550 worker-hours**，屬planning estimate。18可用cores的算術下限約16–31 h；加入依賴、資料取得與工程，規劃3–6天，不能保證。若評估增至9,000 episodes，stage C原速度已約420.45 worker-hours。

Track A占約16workers時，B限2個單執行緒workers、保留2cores；可重疊宣告、工程、probe與少量shards。不得同時再開12-worker E1或完整training fan-out。重疊容量下，B算力需求可能延伸至約6–12天。

期限只有數天：固定交付全部regime map、selected-regime teacher／deployable screen及五arm小panel；未完成full campaign明列pending，不以短跑替代正式成效。

**6. Integrity與隔離**

建立B專用checkout與 `.scratch/multi-catfish-v024-regime-b/`、`artifacts/v024-regime-b/`；grid、phase、lineage分目錄。另立 `PREREG-V024-REGIME-B`，不修改[凍結R2](/home/u24/papers/mcrl-leo-handover/artifacts/PREREG-FROZEN-2026-08-25-R2.json)。

B重用驗證過的程式與TLE archive，政策、optimizer、replay、targets、seed／field namespaces全部新建。TRAIN內再分development與confirmation；TEST始終拒讀。

禁止：A checkpoint作B policy、outcome後改demand／λ／κ／target／margin、隱藏不利grid、選world重跑、把repair變scientific revision、把E1最適配置當deployment input。保留全部失敗、資源中斷與修復前receipts。

**7. Risks與可發表結果**

Finite demand可能讓MODQN／FULL2自行學完consolidation；probe相對弱reference的headroom不代表相對強BASE仍存在。慢速carrier activation假設也限制外推。

若joint teacher與deployable set成功、additive失敗，支持**本契約的additive target／interface／composition受限**；不能升格為所有additive方法不可能。[Astra global view](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/GLOBAL-VIEW-C3-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md:1)指出97% interaction cancellation；Gemini的composition關切值得檢驗，但其「BASE已耗盡收益／普遍不可能」強推論不採納。

可發表結果包括：B條件式正結果、set優於additive、oracle-to-deployment落差，或強BASE消除全部headroom。均與[既有chronology](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-chatgpt-review-package-20260908/01-CHRONOLOGY.md:1)並列，保留A負面結論。

**8. Concrete first-24-hour tasks**

依序執行：

1. **Controller／non-heavy：**封存本memo、四grid、選點margin、五arms、seed domain、預算與no-TEST規則。
2. **Codex／non-heavy：**建立B隔離邊界；實作capacity／delivered-bits雙欄，更新C1/C2及完整profile accounting；驗證G0回歸、需求上限、功率守恆、counterfactual不污染continuation。
3. **Controller／non-heavy：**綁定code／environment／TLE hashes，核對seed排除表與A資源占用。
4. **Codex／heavy：**建議Ubuntu server執行probe，預留6–12 h受限容量。由執行者SSH、同步B repo＋artifacts、確認Python與所有thread pools，再於server開Codex worker；本次不執行SSH。
5. **Codex／heavy：**取得完整raw tape，完成四點exact solves、certificate與全grid報告；資源不足標INCOMPLETE。
6. **Controller／non-heavy：**按固定順序公布selected point或NONE及選擇理由；封存結果後，依既定campaign契約排程重新訓練。

ASTRA_REGIME_B=DRAFTED

