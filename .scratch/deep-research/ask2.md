# 總判定

**這套模擬器可以支撐「在此實作中，訓練目標與宣告的 pooled EE 反向」這個內部稽核結論；目前不能支撐「真實 LEO 系統普遍偏好高換手率、集中使用者，且 spreading 必然降低 EE」這種外部物理結論。**

原因不是 pooled EE 定義。以 aggregate useful bits 除以 aggregate energy 的 global EE，是文獻中可辨識的 objective；但 full-buffer Shannon capacity 必須明稱為 capacity benchmark，而不能不加說明地稱為 demand-capped useful traffic。

真正會決定結論方向的是：

> **每個 beam 的 RF／PA energy 如何由多使用者傳輸形成，以及 occupancy 是否透過 airtime、demand、duty cycle 或 simultaneous streams 進入功率。**

---

## 1. 六項差異的 sign／magnitude 判定與損害排名

這裡的「sign-changing」是指：換成有文獻依據、同樣合理的物理模型後，某個 action 對 EE 的邊際效應可能由正變負或由負變正；不表示一定會翻轉，而是目前模型無法鎖定符號。

|    排名 | 模型選擇                                                       | 與文獻的關係                                                                                                                                                                                     | 對結論的影響                                                                                                                                                                                                                            | 審查損害                                                                             |
| ----: | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **1** | **每 beam 功率取 served-user powers 的 `max`**                  | DR-2 找到的明確 multiuser payload 模型是 simultaneous user precoder powers 相加，再跨 beams 相加，並可另收 illuminated-beam hardware overhead；`max` 並不是一般性的 multiuser payload-power 規則。                        | **Sign-changing。** 它使低於既有最大值的新使用者具有零 RF 邊際成本，也使 consolidation 人為有利。換成 additive-stream 或 airtime-integrated energy 後，新增使用者可能增加 RF energy，因而可能翻轉「packing 有利／spreading 有害」及 policy ranking。                                          | **致命／最高**。目前任何關於 load spreading、beam consolidation、`r3` 的物理解讀都由這個 operator 預先決定。 |
| **2** | **occupancy-independent power／沒有 airtime-demand coupling** | 文獻中兩種 convention 都存在：有些模型讓 demand、time slots、activation 或 user precoder powers影響能耗；另一些 beam-hopping 模型不把 `U_b` 直接乘進功率，但 traffic 仍透過 queues、slots 與 activation 進入系統。                        | **Sign-changing。** 「user count 不直接乘 power」本身可辯護；但目前的混合形式讓新增使用者常常完全不增加 airtime、duty-cycle 或 energy，因此不能把所得到的 spreading 符號外推。                                                                                                       | **重大**。與第 1 項是同一根本問題的兩個面向。                                                       |
| **3** | **完全沒有 handover interruption**                             | 文獻與 3GPP 流程一致認為 handover 會造成時間／程序成本。可驗證 paper example 為 CHO **54.375 ms**、RACH-less **40 ms**；TS 38.133 則是依 HO 類型與測試條件給 requirement，不是一個 universal constant。                               | **局部 causal sign 改變，但主結果只改 magnitude。** 每次 HO 對 useful bits 的效果由 0 變成負值；但以目前兩 arm 的 HO-rate 差，40–54.375 ms 只造成約 **0.057–0.078%** 的一階相對 bits 差。要單靠共同 interruption 抹去 1.1975 的 EE ratio，約需 **10.37 s/HO**，DR-2 沒有提供接近此量級的依據。        | **中等**。審查者會合理要求補上，但它不會救回 learner，也不會解釋 19.8% gap。                                |
| **4** | **activation-gated、load-unweighted interference**          | 這不完全是「偏離標準」：已發表 beam-management 模型確實用 binary beam activation，active cochannel beam 貢獻完整 interference；它省略的是 active slot 內的 fractional resource overlap／load scaling。                        | primitive effect 主要是 **magnitude-only**：新增 cochannel transmission 的 interference 方向仍是非負，只是目前模型可能高估外部性。它可能改變 spreading 的總淨效應，但在你目前「啟用 beam 的固定成本已大於可得 de-crowding saving」條件下，單獨修這項不會翻轉既有符號。                                        | **中低**。在 full-buffer、每個 active beam 全時發射的 scope 下可辯護；不能稱為一般 traffic-load model。  |
| **5** | **單一 30.08 s decision interval**                           | 文獻沒有 universal `dt`。例子同時包含 **20/120/200 ms** scheduling epochs、約 **72 s** serving-satellite optimizer update，以及約 **60.12 s** 平均 inter-satellite HO interval。典型結構是 hierarchical timescales。 | 如果 30.08 s 只是 **association decision epoch**，而 geometry、rate、energy 在 interval 內正確積分，主要是 resolution／magnitude 問題，不改 sign。若它同時也是唯一 PHY、interference、fading、beam scheduling 時間尺度，則 stale-state／aliasing 可導致 conditional sign error。 | **低但有條件**。必須明確稱為 association epoch，而非 radio scheduling slot。                     |
| **6** | **zero explicit joules per handover**                      | 這其實**不是已建立的標準偏差**。DR-2 沒找到 3GPP 或可泛化 LEO 文獻提供 universal `J/HO`；文獻主要量化 interruption、messages、outage、failure、retransmission 等。                                                               | 沒有文獻依據可斷言加入某個 event-energy 後會翻轉 arm ranking。若加入經 power-state model 導出的 UE／payload energy，通常只改 denominator magnitude。                                                                                                              | **最低**。問題不是「沒有任意 J/HO」，而是把它敘述成「handover 在物理上免費」。                                 |

### 特別需要拆開的兩件事

**Zero event surcharge** 可以辯護；但下列敘述不可以混為一談：

1. 「沒有文獻支持固定 `J/HO`」；
2. 「handover 不造成任何物理代價」；
3. 「handover 會因 power-segment reset 而節能」。

第 1 項由 DR-2 支持。第 2 項與 interruption／signalling／outage 文獻不符。第 3 項是該模擬器特有的 state-reset 行為，除非另有硬體控制依據，不能作為 LEO handover 的物理性質。

---

## 2. `0.2796` 與 `0.7117` 是否在 realistic envelope

換算如下：

$$
h_{\rm min}=h_{\rm step}\frac{60}{30.08}.
$$

| Arm            | HO/user-step |   HO/user/min |         等效平均間隔 | 判定                                                               |
| -------------- | -----------: | ------------: | -------------: | ---------------------------------------------------------------- |
| learner        |       0.2796 | **0.558/min** | **107.6 s/HO** | **在 DR-2 的 satellite-reassociation envelope 內**                  |
| greedy EE rule |       0.7117 | **1.420/min** |  **42.3 s/HO** | **高於 DR-2 的 inter-satellite 樣本上緣，但不能僅據此稱為 operationally absurd** |

DR-2 的取樣包含：

* 550 km Starlink Phase-I threshold：**0.10/min**；
* 同場景 graph-planned：**0.167/min**；
* 600 km dense Walker dynamic association：**約 0.998/min**；
* 一篇研究自行設定的 explicit policy ceiling：**約 1.2/min**。

因此：

### learner：`0.2796/step`

**在 realistic envelope 內。**

它比 0.10–0.167/min 的「幾分鐘用同一顆 satellite」操作點高，但明顯低於約 1/min 的 dense-Walker dynamic reassociation，以及 1.2/min 的研究型 policy constraint。不能說它也已經超出文獻範圍。

### greedy：`0.7117/step`

若這 **1.420/min 全部都是 inter-satellite handover**：

* 高於調查中的約 1.0/min observed operating point；
* 高於 1.2/min policy example 約 **18.3%**；
* 應判為 **aggressive、未經外部驗證、超出本次 surveyed inter-satellite envelope**。

但「operationally absurd」仍然太強，因為 DR-2 明確沒有找到 3GPP 的 universal HO/min hard ceiling。

更重要的是，目前的 `handover rate` 看起來合併了：

* intra-satellite beam changes；
* inter-satellite changes。

DR-2 的 0.1–1.2/min 數值大多描述 **serving-satellite reassociation／inter-satellite HO**；beam scheduling、beam hopping 與 UE beam handover並不是同一事件。文獻甚至在同一研究中同時出現約 15 ms beam revisit 與約 60 s satellite-HO interval。

所以最準確的審查結論是：

> **0.28 在合理範圍內；0.71 對 inter-satellite HO 而言超出本次文獻範圍，但對 intra+inter aggregate rate 而言證據不足以稱為荒謬。**

論文必須分別報告 `H_intra/min`、`H_inter/min`，最好再報 `H_inter/pass`。只報 aggregate rate 無法做 operational判定。

---

## 3. 實際可導出的 handover ceiling

### 結論先行

**從 DR-2 找不到任何 physics-derived 或 3GPP-derived 的 universal maximum handover rate。**

可以得到的是三種不同性質的數字：

| 數字來源                            | 能導出什麼                             | 不能導出什麼                                                   |
| ------------------------------- | --------------------------------- | -------------------------------------------------------- |
| satellite visibility／dwell time | 維持連續服務所需的換星**量級或最低頻率**            | 不能推出不得提前 reassociate 的 maximum                           |
| 已發表 study 的 `\bar H`            | 可引用的 policy-constraint precedent  | 不是 3GPP、signalling capacity 或 orbital physics hard limit |
| 本研究自行選擇的 churn budget           | 可作為 operational design constraint | 必須明稱 stipulated，不可稱為 derived                             |

DR-2 特別指出：5–10 min association／8–12 min visibility 通常提供的是必要換星的 timescale，方向上較接近下界；它並不禁止在候選衛星重疊期間提早換星。

### `1/15`：一個 inter-satellite HO per pass

以 `dt=30.08 s`：

$$
15\,dt=451.2\ {\rm s}=7.52\ {\rm min},
$$

$$
\frac{1/15}{30.08/60}=0.133\ {\rm HO/min}.
$$

**數值尺度有文獻錨點。** 7.52 min 落在 DR-2 的約 5–10 min association／8–12 min visibility 尺度內。

但 inequality 的方向不能由此導出：

* Geometry 支持的是「約每 7.5 min 最終必須轉換服務 satellite」；
* 它不支持「7.5 min 內最多只能換一次」。

因此：

> `H_inter ≤ 1/15` 是「選定 satellite 後儘量持有至 pass 結束」的**政策限制**。
> `1/15` 的量級受 geometry 支持，但「≤」本身仍是 stipulation。

將它稱為「由 pass duration 導出的 maximum」會被審查者抓到方向錯誤。

### `1/3`：beam-switch budget

$$
3\,dt=90.24\ {\rm s},
\qquad
\frac{1/3}{30.08/60}=0.665\ {\rm HO/min}.
$$

DR-2 沒有找到支持「每 user 約 90 s 最多一次 beam switch」的 3GPP 或通用 LEO 數字。Beam hopping 的 ms 級 slot/revisit 也不能直接當作 UE beam-handover quota。

所以：

> **`1/3` 完全是 stipulated operational budget。**

它可以是合理的工程選擇，但不能被描述成 externally derived ceiling。

### 合成 `H_max ≤ 0.40`

$$
0.40\ {\rm per\ step}
=
0.798\ {\rm HO/min},
$$

等效平均約 75.2 s/HO。

這個值：

* 位於 DR-2 的約 0.1–1.0/min observed envelope 內；
* 低於 1.2/min 的 published policy example；
* 因而是**可辯護的保守設計點**；
* 但仍然不是 physics-derived limit。

只有在 `H_inter` 與 `H_intra` 是互斥計數時，才可寫：

$$
H_{\rm total}=H_{\rm inter}+H_{\rm intra}
\le \frac1{15}+\frac13=0.40.
$$

若「beam switch」計數也包含 inter-satellite event，直接相加會 double-count。

### 唯一可以直接轉換的 published ceiling precedent

Sun–Zhu–Peng 的 study 自行設：

$$
\bar H=0.004
$$

per 0.2-s epoch，換算為約：

$$
1.2\ {\rm HO/min}.
$$

對你的 30.08-s step 等效為：

$$
H_{\max}=1.2\frac{30.08}{60}
=
0.6016\ {\rm HO/user\text{-}step}.
$$

但必須精確描述為：

> **0.6016/step 是從一篇論文的 stipulated inter-satellite policy budget 所做的單位換算；換算是 derived，原始 ceiling 不是。**

該文獻數值與其性質見 DR-2。

---

## 4. `r2`、`r3` 的實際成本應放在哪裡

### `r2`：handover penalty

| 真實機制                                                     | EE／評估中的正確位置                                                               |
| -------------------------------------------------------- | ------------------------------------------------------------------------- |
| user-plane interruption、失去可用傳輸時間                         | **numerator**：減少同 interval 的 useful decoded bits／goodput                  |
| TCP stall、HARQ/ARQ retransmission造成的 useful-goodput loss | **numerator**，也另報 higher-layer QoE                                        |
| RACH／RRC／Xn signalling load                              | 通常是**分開報告的 control-plane outcome**；不能直接變成 payload joules                  |
| UE synchronization／extra RF-chain energy                 | 只有在有 UE power-state model 且 denominator 包含 UE 時，才進 **denominator**        |
| make-before-break 時同時啟用兩個 payload chains／beams           | 有實際 active-power model時進 **denominator**                                  |
| handover failure、RLF、outage、ping-pong                    | **constraint 或 separate QoS outcome**                                     |
| handovers/min 本身                                         | **operational constraint／secondary objective／reported KPI**               |
| 固定 `−0.5`、`−1.0` event price                             | 在沒有校準的 seconds、joules、failure risk 或明示 constraint multiplier 時，**沒有物理位置** |

文獻支持的是分解 interruption、signalling、outage 等成本，而不是 universal joules/event。

所以 `r2` 有兩種可接受身分：

1. **移除出 EE objective**，讓 interruption 真實地減少 bits，並另外報 HO rate；
2. 將它明確改成 handover-rate constraint 的 Lagrangian penalty。

後者的 multiplier 可以是 dimensionless，但必須對應一個明示的 `H_max` 與 constraint violation，不能再宣稱 `−0.5/−1` 是 handover 的 energy cost。

### `r3`：negative beam occupancy

Raw occupancy `−U_b` **不應直接出現在 EE 中**。

各效果應由下列位置自然形成：

| occupancy 所代表的機制                                    | 正確位置                                                        |
| --------------------------------------------------- | ----------------------------------------------------------- |
| bandwidth／airtime sharing                           | **numerator**中的實際 delivered rate                            |
| queue、demand、deadline未滿足                            | QoS **constraint**與 useful-throughput numerator             |
| 更多 time slots／higher duty cycle／additional RF power | **denominator**                                             |
| 啟用額外 beam 的 circuit power                           | **denominator**                                             |
| cochannel resource overlap                          | 實際 SINR，進而影響 **numerator**與所需 power                         |
| fairness／避免單 beam overload                          | 明示 fairness／minimum-rate／load constraint，或 separate outcome |
| `−U_b` 本身                                           | 若沒有獨立公平性研究目的，**nowhere**                                    |

文獻中的 demand-aware models讓 occupancy透過 power、slots與activation產生成本；binary beam models則可能讓 user count不直接進 power，但仍透過 scheduler／queue運作。沒有共同原則支持「occupancy 大本身就是負 reward」。

因此，對目前三頭 reward 最準確的處理是：

* `r1`：只要與 declared pooled EE 完全同義，可保留為 primary objective；
* `r2`：改為 constraint／secondary mobility KPI，或把 interruption放回 numerator；
* `r3`：移除作為 EE proxy；需要 fairness 時改成明示 constraint，而不是假設 spreading 對 EE 有正貢獻。

---

## 5. 每單位工作量最值得做的單一 physics change

**把 `max`-over-users beam power 改成與實際 access/scheduler 一致的 interval-energy accounting。**

若目前是 equal-airtime TDM，最直接的形式是：

$$
E_{{\rm PA},b}
=
\Delta t
\sum_{u\in b}
\tau_{u,b}\,
P_{\rm PA,DC}(p_{u,b}),
\qquad
\sum_{u\in b}\tau_{u,b}\le 1.
$$

Full-buffer equal airtime 時可先用：

$$
\tau_{u,b}=\frac{1}{U_b}.
$$

重點是先對每個 user slot 的 RF power 做 PA-DC conversion，再依 airtime 積分，而不是：

$$
P_{{\rm beam},b}=\max_u p_{u,b}
$$

然後把該最大值收整個 interval。

若 users 是同時傳輸的 spatial streams／subcarriers，則應在同時傳輸範圍內加總 RF powers，再依實際 PA-chain architecture 計算 supply power。文獻中的 multiuser precoding model明確採 user powers加總，並另加 active-beam hardware overhead。

這項修改優於先加入 interruption，因為：

* interruption 是容易補的 hygiene correction，但依目前 sourced ms 值只改變不到約 0.1 percentage point 的 arm ratio；
* beam-power aggregation影響每個 active beam、每個 step、所有 policy；
* 它直接決定新增 user 的 marginal joules；
* 它是唯一可能翻轉 `r3`、consolidation，以及高換手 heuristic 優勢符號的項目。

**先不重訓。** 應先用同一批 frozen actions 重算：

1. 現行 `max` accounting；
2. TDM airtime-integrated accounting；
3. 若 PHY 允許，同時 stream 的 additive accounting。

若 `MAX_NOMINAL_GAIN > checkpoint` 在這些可辯護模型下仍成立，19.8% 結論才開始具有外部物理可信度；若 ranking 翻轉，現有結果應定位為 reward／simulator counterexample，而不是 LEO handover 的物理發現。

最終審查判語可以壓縮成一句：

> **目前 simulator 足以證明既有 learner 沒有最佳化其宣告 endpoint，但在修正 multiuser beam-energy accounting 以前，不足以證明高 churn、beam consolidation 或 nominal-gain selection 是真實 LEO payload EE 的較佳策略。**
