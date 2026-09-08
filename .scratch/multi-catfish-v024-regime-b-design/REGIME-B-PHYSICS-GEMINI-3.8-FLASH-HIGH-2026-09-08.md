這是一份針對多使用者 LEO 換手模擬器之 **第二物理體制（Second Regime）** 的獨立物理提議。本提議旨在事前（a priori）引入具備文獻支撐的物理機制，以打破「負載均衡與波束協同對總體能源效率（Pooled EE）無因果貢獻」的退化困境。

---

### 1. 物理改動提案與機制分析 (Physically Justified Model Changes)

#### (1.1) 有界流量需求與波束休眠 (Finite Traffic Demand & Micro-sleep / DTX)
* **文獻依據**：3GPP TR 38.821 §6.1 與 ITU-R M.2514。真實 LEO 寬頻連線並非 Full-Buffer（無限積壓），而是具有時槽級封包需求（例如 $D_u \in [50, 200]\text{ Mbit/slot}$）。
* **$\Delta\text{bits}$ vs $\Delta\text{joules}$ 機制**：
  * 現行體制中，$Bits = \frac{B}{n_b}\log_2(1+\text{SINR})\Delta t$；孤立使用者獨占 166.67 MHz 可產出數十 Gbps 虛擬容量，造成「開波束換取過剩 bits」卻消耗整支波束 PA 能量。
  * 引入 $Bits_u = \min(R_u \Delta t, D_u)$。當波束提早滿足使用者需求後進入微休眠（DTX，消耗降至靜態零功耗），或當多個使用者整合至同一波束時，透過統計多工（Statistical Multiplexing）滿足需求：$\Delta\text{bits} \approx 0$（不失真），而關閉空波束獲得巨大的 $\Delta\text{joules} < 0$ 節省。
* **預期量級**：波束休眠可使系統總消耗能量下降 25%–40%，整體 EE 增益達 $+30\%\text{--}50\%$。
* **C1/C2 邊界效應**：C1（One-step Surplus）被真實需求截斷，防止單一 Agent 為刷高 bits 而過度消耗帶寬；C2（Persistence Risk）因波束整合負載更具預測性而顯著降低。
* **實作風險**：**低**。僅需在 `step.py` 的 rate 計算後增加 demand 截斷與比例休眠係數。

#### (1.2) 下行多用戶功率累加 (Sum-Power per Beam)
* **文獻依據**：3GPP TS 38.213 / 38.214 下行 FDMA/OFDMA 功率分配。當多個使用者共用頻寬時，發射機總 RF 功率為各子通道功率之和：$P_{\text{RF}, b} = \sum_{u \in \mathcal{U}_b} p_u$，而非現行的 $\max_{u} p_u$。
* **$\Delta\text{bits}$ vs $\Delta\text{joules}$ 機制**：
  * 現行 $\max$ 模型賦予後續加入波束之使用者「零邊際 RF 能量成本」，人為誘導無序過度整合。
  * 改為 $\sum p_u$（且總功率受限於 PA 飽和上限 $p_{\text{sat}} = 5.218\text{ W}$）：單一波束負載過高時，RF 總功率呈線性增加，推動 PA 往飽和區移動，使能量消耗加速上升；協調負載（Load Balancing）可使各波束操作於低功率高線性區，產生凸性優化效益（Jensen's Inequality: $\sum \sqrt{p_u} \neq \sqrt{\sum p_u}$）。
* **預期量級**：高負載波束之 PA 功耗直接隨用戶數成比例增長，協調分配可節省 15%–20% RF 功耗。
* **C1/C2 邊界效應**：C1 的邊際能量罰分（$\lambda \cdot \text{energy}$）將正確反映擁塞成本；C2 因避免波束功率打頂 Outage 而增強鏈路穩定度。
* **實作風險**：**低**。僅需修改 `link_budget.py` 中的 `beam_power_w` 聚合算子。

#### (1.3) 現實主動陣列天線 (APAA) 靜態電路與 DBF 功耗權重
* **文獻依據**：Del Re et al. (IEEE Aero. 2020) 與 ESA LEO Payload Survey。數位波束成形（Digital Beamforming, DBF）包含 ADC/DAC、數位濾波與波束加權計算，每支啟動波束之靜態基帶功耗通常在 $2.0\text{--}4.5\text{ W}$，遠高於現行代碼之 $0.338\text{ W}$。
* **$\Delta\text{bits}$ vs $\Delta\text{joules}$ 機制**：
  * 現行模型中 PA 佔比高達 94.8%，開關波束之固定成本微不足道。若將 $P_{\text{circuit, beam}}$ 提高至合理物理值（例如 $2.5\text{ W}$），啟動新波束每 30.08 s 將固定消耗 $75.2\text{ J}$。
  * 協調機制疏散低效邊緣波束時，能換取顯著的 $\Delta\text{joules}$ 削減（跳脫 PA 支配的小幅震盪），使「波束撤收（Evacuation）」具備清晰的熱力學紅利。
* **預期量級**：固定功耗佔比提升至 30%–45%，波束整合效益權重增加 3 倍以上。
* **C1/C2 邊界效應**：大幅提高開啟新波束的門檻，抑制盲目換手；C2 換手代價在能量項中獲得顯式體現。
* **實作風險**：**極低**。僅需調整 `constants.py` 靜態常數。

#### (1.4) 功放回退（OBO）與非線性失真底限 (PA Non-linear Distortion & Back-off)
* **文獻依據**：Rappaport "Wireless Communications"; Colantonio et al. (Space PA Design)。真實 LEO GaN SSPA 傳輸高 PAPR OFDM 信號時，需保留 $3\text{--}6\text{ dB}$ 輸出回退（OBO）。
* **$\Delta\text{bits}$ vs $\Delta\text{joules}$ 機制**：
  * 當波束總功率接近 $p_{\text{sat}}$ 時，非線性互調失真產生等效 EVM 底限，有效 SINR 變為 $\text{SINR}_{\text{eff}} = (1/\text{SINR} + \text{EVM}^2)^{-1}$。
  * 擁擠波束將遭受嚴重速率崩塌（$\Delta\text{bits} < 0$），迫使協調機制將使用者均勻平衡至其他較乾淨波束。
* **預期量級**：滿載波束頻譜效率下降 30%–50%。
* **C1/C2 邊界效應**：自然形成負載容量軟上限（Soft Capacity Limit）。
* **實作風險**：**中等**。需在 SINR 鏈路中引入非線性衰退項。

---

### 2. 最小改動集與事前聲明網格 (Minimal Set & Fixed Grid, $\le 6$ Points)

為確保實驗嚴謹性，本提議僅選取改動最小、物理可解釋性最高之雙參數組合：
1. **波束靜態基帶功耗 $P_{\text{fix, beam}}$**：反映 APAA/DBF 真實硬體開銷。
2. **流量需求模式 $D_{\text{traffic}}$**：引入時槽級有限資料量，啟用波束滿額微休眠（Sleep Mode）。

固定聲明之 **5 個測試點網格（Grid Points）** 如下：

| 網格點 | 流量需求 $D_{\text{traffic}}$ (Mbit/slot) | 波束靜態功耗 $P_{\text{fix, beam}}$ (W) | RF 功率聚合方式 | 物理體制說明 |
| :--- | :--- | :--- | :--- | :--- |
| **G0 (基準)** | $\infty$ (Full-buffer) | 0.338 W | $\max_u p_u$ | 原現行退化體制（Regime 1 Baseline） |
| **G1** | 150 Mbit | 0.338 W | $\max_u p_u$ | 僅引入有限需求與微休眠 |
| **G2** | 150 Mbit | 2.500 W | $\max_u p_u$ | 有限需求 + 真實 DBF 靜態功耗 |
| **G3** | 150 Mbit | 2.500 W | $\sum_u p_u$ | 有限需求 + 真實 DBF + 總功率累加 |
| **G4** | 300 Mbit | 2.500 W | $\sum_u p_u$ | 高流量負載對照組（驗證擁塞動態） |

---

### 3. 為何單純提高法規功率上限 ($p_{\max}$) 無法產生協同效應？

單純將 $p_{\max} = 1.65\text{ W}$ 提升至 $p_{\text{sat}} = 5.218\text{ W}$ 無法解決問題，物理與數學原因如下：

1. **開迴路角度補償限制**：當前代碼遵循式 (3.11) 遞迴 $p(t) = p^0 \cdot G^T(\theta_0) / G^T(\theta_t)$，功率完全由天線離軸角幾何決定，非回授閉迴路功控。超過 95% 的正常連線功率落在 $[0.825, 1.65]\text{ W}$，拉高上限僅延後極少數大角度鏈路的 Outage，不改變主流功率分佈。
2. **對數速率對抗開根號功耗的劣勢**：
   * 速率增量遵從香農對數曲線：$\Delta R \approx \frac{B}{n_b \ln 2} \frac{\Delta p}{p}$（高 SNR 下邊際回報遞減）。
   * 功放直流功耗遵從 Class-B 開根號模型：$P_{\text{supply}} \approx \frac{\sqrt{p \cdot p_{\text{sat}}}}{0.35}$。
   * 當 $p$ 增加，$\frac{d(\text{Bits})}{dp} \propto \frac{1}{p}$ 下降極快，而 $\frac{d(\text{Joules})}{dp} \propto \frac{1}{\sqrt{p}}$ 下降緩慢。提高發射功率只會使每焦耳產出的 bits 更少，單調惡化 Pooled EE。
3. **優化對稱性未被打破**：單純提高 $p_{\max}$ 未改變「多開一支波束即增加大量 PA 靜態功耗，而整合波束又遭遇 $B/n_b$ 帶寬除算懲罰」的結構剛性，協調行為（如負載重分配、主動撤收）依然無法創造非零的總剩餘（Surplus）。

---

### 4. 重新訓練前的最低成本驗證探針 (Cheapest Pre-training Probe)

無需花費數小時重新訓練多代理神經網絡，直接使用現成之 **17 分鐘 Exact Oracle Probe**（計算「單一用戶換手」與「波束撤收 Evacuate-One-Beam」之上限）：

* **探針操作**：
  1. 在網格點 **G2** 或 **G3** 的環境設定下，載入任意已收斂之單代理（C1/C2）策略軌跡。
  2. 運行 17 分鐘 Oracle Evaluator，對每個 Decision Step 窮舉評估：
     * **探針 A (Evacuate Beam)**：強制將某個負載 $\le 2$ 的邊緣波束使用者移至相鄰可用波束，關閉該波束，量測 $\Delta\text{EE} = \frac{\Delta\text{Bits}}{\Delta\text{Joules}}$。
     * **探針 B (1-Swap Balance)**：挑選最擁擠波束與最空閒波束進行單一用戶轉移。
* **判定準則（Success Criteria）**：
  * **當前 Regime 1 狀態**：Oracle Headroom $\le 1.2\%$（雜訊級別，協調無效）。
  * **Regime 2 成立標準**：Oracle Headroom $\ge 15.0\%$。只要單步窮舉可驗證「撤收 1 支波束節省的 Joules 明顯超過損失的 Bits」，即確認該物理體制已具備真實的協同操作空間（Coordination Headroom），方可進入正式訓練。
