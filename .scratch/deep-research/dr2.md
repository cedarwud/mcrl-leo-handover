# LEO／NTN 交接成本、實際操作點與酬載功率模型：3GPP 與學術文獻的可追溯調查

## 摘要與判讀

這份調查得到五個相當清楚、而且對模擬器校準很重要的結論。

第一，**3GPP 與近年的 LEO／NTN 文獻並沒有把一次 handover 標準化成固定的「若干 joule」成本**。可直接找到並量化的成本，主要是服務中斷時間、同步／RACH 時間、RRC/Xn/核心網路訊息、handover failure/outage 風險，以及額外的資料轉送與重傳。IEEE VTC 2024 一篇依 3GPP 流程拆解 conditional handover（CHO）的工作，把一個具體 FR2 CHO 範例拆成 **54.375 ms**，其中 UE processing 20 ms、同步相關 10 ms、等待第一個 PRACH 平均 10 ms、PRACH 0.125 ms、UL grant/TA 1.25 ms、RRC 完成 1 ms，以及兩個 Xn 資料轉送相關訊息共 10 ms；其 RACH-less 方案在同一模型下為 **40 ms**。這些是「時間／程序成本」，不是 handover energy tariff。citeturn20view2turn18view2

第二，**TS 38.133 的標準處理不是「每次 handover 固定抽掉 X ms」的機率分布模型**。Release 17 的規範族系延續了普通 NR handover、DAPS handover、conditional handover 各自的 interruption requirements；可核對的條款位置分別是 §6.1.1.2.2、§6.1.3.2.2、§6.1.4.4.4。3GPP 還有專門針對 Rel-17 DAPS interruption 的維護 CR 2009。規範是依 handover 類型、同步狀態、目標是否已知、RACH／量測條件等給出 requirement/test treatment，而不是一個適用所有 NTN handover 的常數。citeturn10view0turn24search0turn39view1

特別值得注意的是，**我沒有從符合本題來源門檻的可驗證 primary-source extract 中，驗證出「62 ms = 同衛星換 beam、142 ms = 換衛星」這一對數字是 Release-17 NTN 的通用規範常數**。官方 3GPP 索引確實可搜尋到某個 Rel-17 測試配置中的「`Tinterrupt = 62 ms in the test`」，但該搜尋結果不足以把它辨識為一般 NTN same-satellite handover；本次也沒有取得能把 **142 ms** 對應到同一類 NTN normative rule 的官方本文。因此，這一對數字若出現在 Annex 測試案例或特定實作中，最多應視為**特定 test configuration／implementation parameter**，不宜直接提升為「標準的一次 handover cost」。citeturn37search1turn39view1

第三，550–600 km Walker 類系統的學術操作點不是「每幾十秒換一次」或「每十分鐘換一次」其中之一，而是**兩個尺度都存在**。550 km Starlink Phase-I 模擬中，傳統 elevation-threshold 法在 30 min 內有 3 次 handover，約 **0.10 次/user/min**；圖最佳化方法為 5 次／30 min，count-derived rate 約 **0.167/min**，其演算法 handover opportunity spacing 被設定為約 5 min。另一個 600 km、1,200 顆 Walker constellation 的動態 beam-management 模擬則得到平均 inter-satellite handover interval **501 × 120 ms = 60.12 s，約 0.998/min**。因此，可信的研究範圍至少跨越約 **0.1–1 handover/user/min**，而不是單一標準值。citeturn29view1turn27view3

第四，**「每 beam 功率 = 該 beam 所有 users 中最大需求功率」不是本次找到的主流 multiuser payload-power model**。在 GLOBECOM 2022 的衛星 payload power 模型中，一個 beam 的 radiated power 明確為該 beam 上所有 user precoder powers 的**和**，而總 payload objective 再對所有 beams 求和，並另外加入每個 illuminated beam 的固定 hardware power。另一篇 IEEE Wireless Communications Letters 的 multibeam work 也直接最小化**總 radiated power**。換言之，典型 abstraction 是 beam-level power variable，或 simultaneous streams 的 additive transmit power；並不是把 user powers 取 max 後當作一般性的 payload DC power law。citeturn39view2turn38view0

第五，對能源效率而言，文獻裡沒有足夠證據支持把「handover 次數」本身直接乘上一個標準 joule 數放進 EE denominator；**handover frequency 通常是獨立 QoS／mobility objective 或 constraint**。反而，全球 EE（global EE）類工作通常把 aggregate rate／throughput 除以 aggregate consumed/transmit power，而另一些工作採 user-level 或 max-min EE。因此，「ratio of sums」與「per-user ratios」確實是不同問題；本次取樣的 LEO／satellite 文獻並沒有形成一個統一、明文規定的跨 user／跨 time pooling convention。citeturn37view2turn39view3turn26view1

## 交接成本與中斷

下表把 handover 的成本通道拆開。最重要的區別是：**秒、訊息數、失敗機率、joule 並不能互相替代**。目前文獻最扎實的是前三類，而不是 joule。

| 標準處理／自然單位，以及與 EE 的關係 | citation（規範條款／論文表格） | numeric value 或 range | 文獻一致或分歧 |
|---|---|---|---|
| **普通 NR handover 的 user-plane interruption**。自然單位是 **ms**。TS 38.133 有獨立 interruption-time requirement；其值依 synchronization、target knowledge、RACH 等條件形成，而非一個隨機分布抽樣值。通常當作 mobility/QoS cost，而不是直接轉為 joule。 | 3GPP TS 38.133 Rel-17，§6.1.1.2.2；官方 ETSI Rel-17 版本鏈可核對。citeturn10view0turn39view1 | **沒有一個普適固定常數。** 官方 3GPP 可索引到某一 Rel-17 test case 的 **62 ms**，但該結果本身不支持把 62 ms 解讀為所有 NTN HO 的固定值。citeturn37search1 | **一致：條件式 requirement；不是 universal constant。** 實際網路 delay 另外有 stochastic signalling/scheduling 成分。 |
| **Conditional handover（CHO）**。CHO 把 preparation 提前，但 execution 仍可能需要同步與 random access；自然單位仍是 ms。 | TS 38.133 Rel-17 §6.1.4.4.4；Iqbal et al., VTC 2024, Table I。citeturn10view0turn20view2 | 該 VTC 研究的 3GPP-aligned FR2 CHO example：**54.375 ms**。細分：UE processing **20 ms**；fine/full timing acquisition 平均 **10 ms**；SSB post-processing margin **2 ms**；first PRACH acquisition 平均 **10 ms**；PRACH preamble **0.125 ms**；UL grant+TA **1.25 ms**；RRC complete **1 ms**；late forwarding 的兩個 Xn messages **10 ms**。citeturn20view2 | **標準原則一致、數值依場景分歧。** 54.375 ms 是 paper 的具體 operating assumption，不是 TS 38.133 對所有 CHO 宣告的固定值。 |
| **DAPS handover**。自然單位為 ms；核心概念是 source/target protocol stacks 同時存活，避免 break-before-make 的長 interruption。 | TS 38.133 §6.1.3.2.2；Rel-17 CR 2009「maintaining interruptions for intra-band DAPS handover」由 RAN4 agreed、RAN approved，進入 17.2.0。citeturn10view0turn24search0 | 本次可驗證的 primary extract **沒有提供一個可安全宣稱為全部 DAPS case 的單一 ms 常數**。因此不把「≈0 ms」當作普適 normative number。 | **一致於「DAPS 是低中斷／make-before-break 類機制」；分歧在具體 RF／sync case 的可達 interruption。** |
| **RACH-less handover**。自然單位 ms。它移除／預先完成 random-access 所需的 target timing acquisition，因此減少 interruption，但仍有 processing、sync、RRC/data-forwarding 成分。 | Iqbal et al., *RACH-less Handover with Early Timing Advance Acquisition for Outage Reduction*, IEEE VTC2024-Spring, Table I／系統評估。citeturn20view2turn18view2 | 在與上述 **54.375 ms** CHO 相同的模型下，partial timing synchronization 已預取時為 **40 ms**，paper 報告該設計在 system-level 模擬中相對降低 interruption **43.2%**、outage **18.7%**。citeturn18view2turn20view2 | **一致於 RACH-less 可降低 interruption；具體幅度依 TA 可預測性、同步與 forwarding procedure 而變。** |
| **Measurement／re-acquisition gap**。自然單位是 ms of unavailable receive/transmit opportunity；它可能發生在 handover 之前，因此不能一概算成「每次 HO 固定 interruption」。 | TS 38.133 的 measurement/RRM requirements 與上述 HO interruption 條款分列；VTC 2024 的具體 decomposition 把 fine/full timing 與 SSB processing 額外列出。citeturn10view0turn20view2 | VTC example：timing acquisition **10 ms average**，SSB post-processing margin **2 ms**；不是通用 measurement-gap constant。citeturn20view2 | **一致：configuration-dependent。** 把全部 measurement cost 固定加在每次 handover 上通常過度簡化。 |
| **Random access / RACH**。自然單位包括 ms、PRACH occasions、messages。通常當作 interruption/signalling，而不是 joule penalty。 | VTC 2024 Table I。citeturn20view2 | first PRACH opportunity 平均 **10 ms**；preamble **0.125 ms**；UL grant + timing advance **1.25 ms**。citeturn20view2 | **機制一致、等待時間分歧**，因 numerology、occasion configuration、同步狀態不同。 |
| **RRC/Xn/control-plane signalling**。自然單位是 messages、bytes、processing/transport ms。標準流程中的 message cost 不會自動等價為 satellite electrical energy。 | VTC 2024 CHO decomposition；該研究以實測文獻值假設每個 Xn message **5 ms**。citeturn20view2 | late data forwarding 中 `HANDOVER SUCCESS` + `SN STATUS TRANSFER` 合計 **10 ms = 2×5 ms** 的研究假設。citeturn20view2 | **程序類型一致；實際 latency/load 不一致。** Xn transport、gNB placement、regenerative/transparent payload 都會改變結果。 |
| **Access/core-network interaction**。自然單位為 messages 與 end-to-end latency。 | Wu et al., *Accelerating Handover in Mobile Satellite Network*；以 Open5GS/UERANSIM 搭配 Starlink/Kuiper geometry 的 prototype，指出 access–core interactions 是傳統流程的重要 latency source。citeturn29view0 | 該公開摘要沒有提供可移植的「每次 HO 固定 messages 或 ms」常數，因此此處不自行補數字。 | **一致於 core signalling 有成本；沒有一個 NTN universal constant。** |
| **UE terminal re-acquisition / synchronization energy**。自然單位若真的計能耗應是 **J = ∫PUE(t)dt**，但 3GPP mobility requirement 本身主要規範時間與程序。 | TS 38.133 interruption clauses；VTC 2024 timing decomposition。citeturn10view0turn20view2 | **本次符合來源門檻的 LEO/NTN literature 中未找到可移植的「J/HO」UE 常數。** 只能取得 10 ms 級同步／PRACH等待等時間項。 | **相當一致地沒有標準 joule tariff。** 若要算 J，必須再有 UE RF/baseband power-state model。 |
| **Payload beam switching energy**。應自然量為 switch transient 的 J/event 或 active hardware 的 W；兩者不能混為一談。衛星 payload 文獻常對「beam illuminated 時」收固定 power，而不是對「switch event」收 joule。 | Ha et al., GLOBECOM 2022, §II-B, eqs. (3)–(6)。citeturn39view2 | `ρ_hw` 是**每個 illuminated beam 的 constant hardware power**，而非 J/handover；paper 沒有建立固定 switching transient energy。citeturn39view2 | **一致於 active-beam power 可有固定 overhead；是否另計 switching transient 則沒有統一模型。** |
| **Radio-link failure／handover outage**。自然單位為 outage probability、outage duration、handover failure rate，而非 joule。 | Iqbal et al. system-level evaluation；Hozayen et al. 將 data rate與delay直接納入 handover path criterion。citeturn18view2turn29view1 | RACH-less study 報告 outage 相對降低 **18.7%**；不是一個「每 HO 有 18.7% failure」的絕對機率。citeturn18view2 | **一致於 failure/outage 是重要 mobility KPI；絕對值高度場景依賴。** |
| **Ping-pong / excessive handovers**。自然單位通常是 handovers/time、reselection events 或短時間返回前一 cell 的比例；文獻常將其視為 signalling/service-continuity trade-off。 | Sun–Zhu–Peng 2024 明確把 inter-satellite handover frequency 作為長期 constraint；3GPP Rel-17 mobility ASN.1 的 `timeToTrigger` 甚至允許 **0 ms** configuration，故 TTT 本身不是 handover-rate ceiling。citeturn37view2turn37search1 | 3GPP 可配置 `timeToTrigger=0 ms`；Sun et al. 的 study-specific long-term threshold 為 **H̄=0.004**。citeturn37search1turn37view3 | **有「避免過度 HO」的共識，但沒有標準 HO/min 上限。** |
| **TCP／HARQ／ARQ／user-perceived stall**。自然單位可以是 retransmissions、goodput loss、stall duration。這些是 handover 的二階結果，而非一個 universal physical-energy surcharge。 | Wu et al. 指出 frequent/high-latency LEO HO 會傷害 latency-sensitive applications；Hozayen et al. 直接以 data rate、delay 作 QoS utility。citeturn29view0turn29view1 | 本次 primary-source set **沒有找到可普遍套用的 TCP stall ms/HO 或 HARQ joules/HO 常數**。 | **高度分歧／protocol dependent。** |

因此，對「每 handover 是否應該直接付 energy cost」這件事，文獻支持的做法不是隨便指定一個 J/HO，而是先決定要建模哪個物理機制：UE 多開一條 RF chain、額外 Tx/Rx 時間、payload 同時照亮兩個 beams、RACH retransmission，或 data interruption。沒有這些 power-state assumptions，從 3GPP 的 **ms** 直接變成 **J** 沒有量綱上的依據。TS 38.133 本身提供的主要是 interruption/RRM performance framework，而 payload-power paper 則另外建模 active hardware power。citeturn10view0turn39view2

## 實際操作點與交接率

LEO 文獻顯示一個很重要的現象：**beam scheduling、serving-satellite reassignment、實際 satellite handover 是不同時間尺度**。因此「decision interval」不能單獨拿來當作 handover dwell time。

| 標準處理／場景 | citation（paper table/figure） | numeric value 或 range | 文獻一致或分歧 |
|---|---|---|---|
| **550 km Starlink Phase-I：elevation-threshold satellite handover**。1,584 satellites、22 orbital planes、72/plane；Ottawa UE；handover threshold elevation **10°**。 | Hozayen et al. 2022, §III-B–C。citeturn29view1 | 30 min 內 threshold method **3 HO → 0.10 HO/user/min**。citeturn29view1 | 與幾分鐘一次 handover 的傳統 LEO picture 一致。 |
| **同一 550 km constellation，graph-planned HO**。演算法可用較頻繁 HO 換取 rate QoS。 | Hozayen et al., Fig. 5–7 discussion。citeturn29view1 | 30 min 內 **5 HO → 0.167 HO/min**；paper 的 decision grid 是 `2λ=300 s`，描述為約 **每 5 min 一個 HO opportunity**。citeturn29view1 | 顯示最佳 handover rate 不是純 orbital constant，而會依 QoS objective 改變。 |
| **文獻的一般 LEO visibility / association timescale**。 | Hozayen et al. 指出 LEO UE 通常約每 **5–10 min** 需做 satellite handover；2026 NTN association paper指出 fixed location 的單顆 LEO satellite visibility 約 **8–12 min**，取決於 altitude。citeturn29view1turn29view2 | 約 **5–10 min/association**；visibility 約 **8–12 min**。換算幾何尺度約為 **0.1–0.2 HO/min**，但這不是容量／QoS最佳解的上限。 | **range 一致但不是精確常數**；minimum elevation angle、latitude、constellation density 影響很大。 |
| **600 km Walker constellation 的 dynamic satellite association**。40 orbits ×30 satellites = **1,200 sats**、inclination **50°**、minimum elevation **40°**、42 earth-fixed cells。 | Zhu–Sun–Peng 2024, Table II。citeturn26view3turn27view3 | 每 scheduling epoch **120 ms**；serving-satellite allocation 每 **600 epochs =72 s** 重跑一次，或 satellite 失去可服務性時立即觸發。平均 handover interval **501 epochs =60.12 s ≈0.998 HO/min**。citeturn27view3 | **顯著高於 5–10 min/pass 類 heuristic。** 這不是矛盾，而是 dense constellation 下有多顆候選衛星，演算法可主動換星。 |
| **同一 600 km paper 的 beam resource scheduling**。 | Zhu–Sun–Peng 2024, §V-A/B。citeturn26view3turn27view3 | 細粒度實驗中 scheduling epoch **20 ms**，15 slots，所以 slot 約 **1.33 ms**；平均 beam revisit time **14.8–15.8 ms**。citeturn27view3 | **與 satellite HO 完全不同尺度。** beam hopping 可 ms 級，而 satellite association 約 minute 級。 |
| **550 km、1,200-satellite handover-frequency-control study**。30 planes、40 satellites/plane、inclination **53°**、20 earth-fixed beam cells、minimum elevation **35°**。 | Sun–Zhu–Peng 2024, Table I。citeturn37view3 | 每 epoch 含 200 slots；**epoch duration 200 ms**，20,000 epochs = **66.67 min**，與 paper simulation duration 相符。`H̄=0.004`。citeturn37view3 | study-specific control point，不是 3GPP limit。 |
| **上述 H̄ 的物理解讀**。paper 的 handover variable 是按 epoch 統計的長期 inter-satellite HO frequency constraint。 | Sun–Zhu–Peng formulation/simulation。citeturn37view2turn37view3 | 若 `H̄=0.004` 是每 epoch 的 binary event long-run mean，則由 **0.2 s/epoch** 可直接換算成 `0.004/0.2×60 = 1.2 HO/min`，等效平均間隔 **≥50 s**。這是依 paper 定義的**衍生值**，不是標準規定。citeturn37view3 | 與另一 600 km study 約 **1/min** 的 operating point 相當接近。 |
| **beam reassignment / beam hopping decision interval**。 | Sun–Zhu–Peng 2024；Zhu–Sun–Peng 2024。citeturn37view2turn27view3 | 已發表模擬例子橫跨 **20 ms、120 ms、200 ms** scheduling epochs；serving-satellite optimizer 則可為 **72 s** periodic update。citeturn27view3turn37view3 | **明顯沒有單一「文獻標準 dt」；典型設計是 hierarchical timescale。** |
| **可接受的 signalling-load / HO-rate ceiling**。 | 3GPP mobility specs 加上 Sun et al. 的 handover-frequency constraint。TS 38.331 的 TTT 可為 0 ms；Sun et al. 自己指定 H̄，而非引用 3GPP HO/min cap。citeturn37search1turn37view3 | **沒有找到 3GPP 規定的 X handovers/user/min ceiling。** 唯一具體 ceiling 類數字是研究者自訂的 `H̄=0.004`，在該 study timescale 下約 **1.2/min**。 | **一致：標準提供程序、trigger、timer；數值 handover-frequency budget 通常由系統設計者 stipulate。** |

這些結果使「realistic handover rate」比較適合表成一個**operating envelope**，而不是常數：在 550–600 km 的本次文獻樣本中，單一 UE／cell 的衛星 reassociation 約從 **0.1/min 到約 1/min**；研究者設定的 explicit handover cap 例子約 **1.2/min**。5–10 分鐘的 visibility/pass timescale 不代表演算法一定要把同一 satellite 用到視界終點；dense Walker constellation 可以基於負載、QoS 或 interference 在可見衛星重疊期間提前換星。citeturn29view1turn27view3turn37view3

另外，「beam dwell」這個詞在衛星文獻很容易混淆：beam hopping 的 service/revisit interval 可以是 **ms 級**，而一顆 LEO satellite 對地面位置的 geometric visibility 是 **minutes 級**，serving-satellite association 又可以介於兩者之間。Zhu–Sun–Peng 的同一篇 600 km paper 同時出現約 **15 ms beam revisit** 與約 **60 s inter-satellite HO interval**，正好說明兩者不應被當成同一個 dwell time。citeturn27view3

## 外生約束與服務可用性

「找一個外生、可引用的 handover-rate constraint」時，來源的性質很重要。**軌道幾何可以給出必要換星的 timescale，但通常不能直接給出「最多只能換幾次」；3GPP timers 也不是 throughput quota。** 真正的 maximum HO frequency 往往仍是設計上的 policy constraint。

| 可作為外生基礎的量 | citation | 可導出的 bound／threshold | derived 還是 stipulated；一致性 |
|---|---|---|---|
| **單顆 LEO visibility / service duration** | Hozayen et al.：550 km Starlink Phase-I；Taksande et al.：LEO fixed-location visibility。citeturn29view1turn29view2 | visibility 約 **8–12 min**；常見 handover spacing 約 **5–10 min**。citeturn29view1turn29view2 | 主要給的是**維持連續服務所需的最低換星頻率量級**，約 0.1–0.2/min，而不是 max-HO ceiling。 |
| **minimum elevation angle / geometric loss of service** | Hozayen simulation **10°** HO threshold；Sun 550 km study **35°**；Zhu 600 km study **40°**。citeturn29view1turn37view3turn27view3 | 10°、35°、40° 都出現在文獻，但分別屬不同 study assumptions。 | 可**導出**每顆 satellite 的最大 service window；不能單獨推出「不得提前 handover」。文獻明顯分歧。 |
| **explicit long-term handover-frequency budget** | Sun–Zhu–Peng 2024, Table I。citeturn37view3 | `H̄=0.004` per epoch indicator；0.2-s epoch 下推得約 **1.2 HO/min、50 s/HO**。 | **stipulated policy constraint**，不是 3GPP／physics hard limit。 |
| **3GPP Time-To-Trigger / measurement-event machinery** | 3GPP TS 38.331 Rel-17 mobility configuration；官方 3GPP indexed test page顯示 `timeToTrigger ms0` 是合法 configuration。citeturn37search1 | 至少存在 **TTT = 0 ms** 的 configuration。 | 這恰好說明 TTT 不能當作固定的 max-HO-rate bound；它是 hysteresis/trigger design parameter。 |
| **mobility robustness / ping-pong avoidance** | TS 38.300／TS 38.331 的 mobility framework；研究文獻把 excessive HO 連結到 signalling overhead/service continuity。Sun et al. 直接加入 HO-frequency constraint。citeturn37view2 | **沒有本次可驗證來源支持「每分鐘最多 N 次」的 3GPP ceiling。** | 只能形成 quality criterion 或 controller design rule；不是標準的數值 quota。 |
| **TR 38.821 NTN geometry/mobility framework** | 3GPP TR 38.821, *Solutions for NR to support NTN*, Release 16；後續 LEO papers在 NTN channel/mobility assumptions 上引用 3GPP NTN models。Sun et al. 的 550-km study使用 3GPP 38.811 channel model。citeturn37view3 | 提供 NTN-specific geometry/channel/mobility assumptions；**沒有查到 handovers/min 的 normative ceiling**。 | 適合用來產生**derived dwell/visibility constraints**，而非直接 stipulate reward penalty。 |
| **operator-reported handover budget** | 本次限定「3GPP + peer-reviewed／academic」來源的檢索結果。 | **沒有找到可泛化到 550–600 km 5G NTN 的 operator-published X HO/user/min budget。** | 缺資料；不能用商業網路 anecdote 代替。 |
| **PHY decodability：NR CQI BLER target** | 3GPP TS 38.214 Rel-17 §5.2.2.1，CQI tables。 | NR link adaptation 的普通 CQI target 是 transport-block error probability **≤0.1**；可靠度型 CQI table 另有 **10⁻⁵** 級 target。 | **標準 PHY target**，但它是 link-adaptation BLER definition，不等於 end-to-end service availability SLA。 |
| **satellite PHY 的另一個明確 BLER example** | Ha et al. GLOBECOM 2022, §II-A；採 DVB-S2X Table 20a–c 的 MODCOD/SINR mapping。citeturn39view2 | paper 明確使用預先設定 **BLER = 10⁻⁵** 的 DVB-S2X target。citeturn39view2 | 一致說明「可 decode」可用 BLER/MODCOD threshold 定義；但 threshold 依 radio system/service class 而不同。 |
| **simulation-level availability：target SNR** | Sun 550 km：Table I；Zhu 600 km：Table II。citeturn37view3turn26view3 | 分別假設 target SNR **12 dB** 與 **20 dB**。citeturn37view3turn26view3 | **純 study-specific assumptions**，不能稱為 3GPP service-availability standard。 |
| **RLF / session continuity** | 3GPP TS 38.331 以 out-of-sync indications、counters/timers 和 RRC recovery 處理 RLF；handover papers則另報 outage、delay/data-rate continuity。VTC work與Hozayen work分別採 outage reduction 與 QoS path。citeturn18view2turn29view1 | **沒有單一「availability ≥ 99.x%」的 NTN handover threshold 可由這些 mobility clauses直接讀出。** | service availability 必須先指定層次：PHY BLER、radio outage、served-time fraction、session continuity或application QoE。 |

這裡有一個容易被忽略的邏輯方向：**satellite dwell time 通常是 handover rate 的下界來源，不是上界來源。** 若一顆 satellite 最多只能服務約 5–10 分鐘，continuity 至少要求相應量級的換星；它並不禁止 controller 在兩顆 satellite 同時可見時每 60 秒甚至更快地 reassociate。Hozayen 的 550-km study與 Zhu 的 600-km study正好分別展示了這兩種操作點。citeturn29view1turn27view3

若真正需要一個 externally defensible **maximum** handover rate，目前最乾淨的文獻先例反而是把它明確寫成系統 constraint，就像 Sun–Zhu–Peng 的 `H̄`；但必須誠實稱它為**設計／政策參數**，不能說它是由 3GPP signalling capacity 推出的 hard limit。該 paper 本身就是先設定 `H̄=0.004`，再設計 Lyapunov queue 使長期 handover frequency滿足它。citeturn37view2turn37view3

## 酬載功率模型

功率模型部分的文獻結果比 handover 更明確：**標準做法不是「每 user 各算一個需要功率，再以 max 當整個 beam 的物理供電」這種一般規則。** 多使用者 multibeam 系統通常把 radiated power 定義在 beam／precoder 上，總 payload transmission power再對同時傳輸的 streams/beams 做加總；是否另加 circuit/hardware overhead取決於 paper。

| 標準處理 | citation（paper equation/table） | numeric value／形式 | 文獻一致或分歧 |
|---|---|---|---|
| **同一 beam 上多 user simultaneous precoding：功率相加。** | Ha et al., GLOBECOM 2022, §II-B, eq. (3)。citeturn39view2 | `P_n[t] = Σ_m |w_{n,m}[t]|²`。也就是 beam n 的 transmit power 是所有 user precoder components 的**sum**，不是 max。citeturn39view2 | 對 simultaneous multiuser linear precoding 是標準且物理上自然的 abstraction。 |
| **整顆 satellite 的 transmit/payload objective：再對 beams 加總。** | Ha et al., eq. (6a)；Efrem & Panagopoulos, IEEE WCL 2020。citeturn39view2turn38view0 | Ha：`Σ_{n,t}[P_n[t] + ρ_hw 1(P_n[t]>0)]`；Efrem paper 明確以**total radiated power**為 energy-aware objective。citeturn39view2turn38view0 | **高度一致於 additive radiated power。** |
| **每個 radiating／illuminated beam 的固定 hardware overhead**。 | Ha et al., §II-B, eq. (5)。citeturn39view2 | 每 illuminated beam 收固定 `ρ_hw`；paper列舉 pre-select filter、LNA、frequency converter、input/output multiplexers、pre-amplifier、HPA 等 active hardware。citeturn39view2 | 「有 activation overhead」有文獻先例；**但 ρ_hw 的 W 值不是 3GPP 標準常數。** |
| **每 active satellite 的 baseband/fixed power**。 | 本次檢視的 Ha、Efrem、Sun models。citeturn39view2turn38view0turn37view2 | **沒有通用的 per-active-satellite W 數值。** Ha model主要用 per-beam hardware overhead；Efrem以 radiated power為重點；Sun resource model主要是 RF link/beam power。 | **模型依研究目的而分歧。** 不能把某一 simulator 的 baseband constant 稱為「standard value」。 |
| **PA supply versus radiated power**。 | Ha et al. 的 model把 HPA列在 beam hardware chain，但 objective 使用 radiated power加固定 `ρ_hw`，並另有 per-beam maximum power constraint `P_n≤P̄_n^GEO`。citeturn39view2 | 沒有 universal `P_DC=f(P_RF)` 或 universal efficiency/saturation value；`P̄_n^GEO` 是 beam-power constraint，而不是一條標準 nonlinear PA saturation curve。citeturn39view2 | **高度模型依賴。** 有些 EE work使用 PA efficiency，有些只最佳化 radiated power；3GPP NTN mobility/channel specs不提供衛星 HPA 的通用 DC curve。 |
| **PA saturation位置**。 | 同上。citeturn39view2 | **本次來源沒有支持一個「LEO payload PA 標準在 X W 飽和」的數值。** | 沒有標準值；依 amplifier、frequency、back-off、waveform 而定。 |
| **occupancy 是否影響功率：multiuser／traffic-aware convention**。 | Ha eqs. (2)–(6)：users 有 SINR／data-demand constraints且 power為 user precoder powers之和；beam hopping也會因 demand決定 active beams。citeturn39view2 | user demand增加可要求更多 `|w|²`、更多 time slots或啟用更多 beams，因此 occupancy/demand**可以透過 rate requirement 間接或直接增加 power**。 | 這是資源最佳化文獻中很常見的 convention。 |
| **occupancy-independent beam power convention**。 | Sun et al. 550-km LEO model用 cell-level `P_{s,c}`、target SNR與 binary beam activation `y`；traffic進入 queue/scheduling decision，而非直接出現成 `U_b` 對 RF power 的乘數。citeturn37view2turn37view3 | paper 設 target SNR **12 dB**，beam是否active由 `y∈{0,1}` 決定；user-count 本身不直接是 PA power formula中的線性因子。citeturn37view2turn37view3 | **兩種 convention 都存在**：traffic可以透過 scheduling/activation影響 power，而不必用 occupancy count直接乘 power。 |
| **co-channel inter-beam interference：binary activation gated**。 | Sun et al., §II-A eq. (3)。citeturn37view2 | `I` 對所有同頻同 polarization 的 active beams 求和，每一項由 binary `y`、beam transmit power、off-axis Tx/Rx antenna gains及channel gain組成。citeturn37view2 | **這是合理且常見的 slot-level full-activity model。** |
| **binary activation model省略什麼**。 | 與 Sun model的 eqs. (2)–(3) 對照：activity在一個 slot內是 `y=0/1`，traffic load透過跨-slot scheduler體現。citeturn37view2 | active slot 內沒有額外的 fractional resource-block/load scaling；若 beam被宣告 active，干擾就是完整該 beam term。 | **不是 universal physical law**；更細的 OFDMA/precoding model會由實際同時 resource occupancy 決定干擾。 |
| **precoding式 interference model**。 | Ha et al., eq. (1)。citeturn39view2 | user m 的 SINR denominator含 `Σ_{j≠m}|hᴴ w_j|² + σ²`，也就是由實際 simultaneous streams決定，而不是只有 beam on/off。citeturn39view2 | 與 binary activation model**並存**，粒度不同。 |

因此，文獻對 payload power 最穩妥的概括是

\[
P_{\text{payload}}
\approx
\sum_{\text{active beams/streams}}P_{\text{RF}}
+
\sum_{\text{active beams}}P_{\text{hardware}}
+
P_{\text{other fixed/processing}},
\]

其中各項是否完整建模取決於研究目的。Ha 等人的可追溯模型至少明確包含前兩項，而且 transmit term 是 **sum over users / beams**。citeturn39view2

這也代表「新增一個 user 對一個已經發射中的 beam 必然是 0 W」並不是文獻的一般結論。若新增 user 需要額外 spatial stream、較高 SINR、更多 transmit power，或使 beam必須多開 time slots，它可以增加 power；若系統採 multicast/common waveform、固定 beam PSD 或純 TDM，則可能主要改變 time occupancy而不立即增加瞬時 RF power。真正的 occupancy→power coupling 必須由 PHY/scheduler model 決定。Ha 的 demand-constrained precoding model展示前者；Sun 的 binary beam-hopping model則展示後者。citeturn39view2turn37view2

同樣重要的是，**沒有找到 3GPP 規範一個固定「每 radiating beam = X W、active satellite baseband = Y W、PA saturation = Z W」的 LEO payload power template**。3GPP NTN 文件主要標準化 radio/interface/channel/mobility requirements；具體 payload electrical design 在學術系統模型中是另行假設。現有論文甚至在 abstraction level 上就不同：Efrem只把 total radiated power拉進 objective，Ha則額外收 illuminated-beam hardware overhead。citeturn38view0turn39view2

## 能源效率定義與可比性

衛星／NTN 文獻中的「energy efficiency」並不是只有一種數學物件。因此，最重要的不是看到作者寫 EE 就假定和另一篇 paper 的 metric 一樣，而是檢查 numerator、denominator 及 aggregation level。

| EE／energy-aware 定義 | citation | 數值／單位 | 一致或分歧 |
|---|---|---|---|
| **Global energy efficiency：aggregate useful rate / aggregate consumed power**。這是 wireless EE optimization 常見的 fractional-programming形式，也出現在 LEO EE work；Khan et al. 的 LEO RIS-NOMA study即以 joint power/RIS optimization最大化 system EE。 | Khan et al., *Energy-Efficient RIS-Enabled NOMA Communication for 6G LEO Satellite Networks*, 2023。citeturn27view0turn39view3 | 依 rate 是否先除 bandwidth，可報 **bit/J** 或 **bit/s/Hz/W = bit/Hz/J**；因此單看數字不能跨 paper 比較。 | **global ratio-of-sums 很常見，但單位與 power accounting 不統一。** |
| **Max-min / user-level EE**。研究也可先定義 user/link EE，再最大化最差 user；這不是 global pooled EE。 | Liu et al., *Rate-Splitting Multiple Access for Quantized ISAC LEO Satellite Systems: A Max-Min Fair Energy-Efficient Beam Design*, 2024。citeturn26view1 | objective 是 max-min fairness 類 EE，而非單純 system sum-rate / total-power。 | **與 global EE 是不同優化問題。** |
| **不是 ratio 的 energy-aware objective**。有些 satellite papers避免叫「EE ratio」，而是同時最小化 unmet capacity與 total radiated power。 | Efrem & Panagopoulos, IEEE WCL 2020。citeturn38view0 | objectives：USC + **total radiated power**；沒有必要先形成 bits/J ratio。citeturn38view0 | 顯示「energy-efficient」研究本身並不保證採 ratio metric。 |
| **Demand-constrained payload power minimization**。先保證所有 user demand/MODCOD，再最小化 payload power。 | Ha et al., GLOBECOM 2022, eq. (6)。citeturn39view2 | numerator不進 objective；constraint要求截至 deadline 傳完 `Q̄_m` bits，objective為 aggregate payload power。citeturn39view2 | 又是一種不同 operating point；不應與 bits/J數值直接比較。 |
| **ratio-of-sums vs mean-of-ratios**。global EE 的 numerator先 sum rates、denominator先 sum powers，再相除；user-fairness EE則可能在 user level形成 ratios。 | Khan et al. 與 Liu et al. 提供兩類 satellite/LEO例子。citeturn39view3turn26view1 | `ΣR/ΣP` 一般不等於 `(1/K)Σ(R_k/P_k)`，除非 powers等特殊條件成立。 | **數學上明確不同；文獻並沒有統一成一個跨所有 papers 的 aggregation convention。** |
| **跨時間 pooling**。許多 PHY/resource-allocation papers是在 slot/window 上寫 instantaneous或window objective，而不是特別討論「把整場 evaluation 所有 bits、所有 joules pool 完再取 ratio」與「每 episode/slot EE 再平均」的 estimator distinction。 | Ha 的 time-window formulation；Sun 的 scheduling-epoch formulation均直接顯示時域 aggregation 是 model-specific。citeturn39view2turn37view2 | **沒有找到 3GPP 或 LEO literature 宣告一個 universal evaluator aggregation rule。** | **通常隱含在數學 objective，並非另立一條統計 reporting standard。** |
| **PHY rate的滿載 Shannon proxy vs demand-capped delivered bits**。 | Sun 使用 `W Tslot log(1+SINR)` 計算 slot data，但實際 queue update有 `max(Q-D,0)`，即 traffic queue仍約束服務需求；Ha 則以明確 `Q̄_m` demand/deadline constraint建模。citeturn37view2turn39view2 | Sun 550-km study：200-MHz satellite bandwidth；Ha用 DVB-S2X discrete MODCOD及 demand bits。citeturn37view3turn39view2 | **明顯分歧。** 「full-buffer theoretical rate」和「actually useful delivered bits」不是必然同一 numerator。 |
| **reported EE magnitude的跨 paper比較**。 | 上述 papers的 units、bandwidth、circuit-power coverage與traffic assumptions不同。citeturn39view3turn38view0turn39view2 | **不存在一個可信的 universal LEO EE bit/J range可由這些 papers直接拼成 benchmark。** | 報告一個看似精確的跨-paper magnitude range反而會混淆 units與power boundary，因此本調查不製造這個數字。 |

對本題最有力的文獻判讀是：**global EE 若定義為 aggregate useful rate 除以 aggregate system power，本質上就是 ratio of sums；把每 user 的 EE 先算好再平均是另一個 objective。** Satellite/LEO literature 確實存在 global 與 user-fairness 兩種 formulation，但我沒有找到任何 3GPP NTN 規範說「EE 必須以 mean-of-user-ratios 評估」。citeturn39view3turn26view1

而且，從 resource-allocation literature 看，**有 traffic demand 時通常不應把超過 queue/demand 的 Shannon capacity自動當作有用 delivered bits**：Sun 的 LEO beam-management model顯式維護 data queues；Ha 則要求在 deadline 前傳滿指定 bits。這與純 full-buffer link-capacity benchmark 是不同的 EE numerator convention，應在研究報告中明確標示。citeturn37view2turn39view2

## 文獻真正分歧之處

**交接頻率沒有單一「正確」操作點。** 550-km Starlink Phase-I 的 threshold simulation約為 **0.10 HO/min**，graph QoS solution約 **0.167 HO/min**；600-km dense Walker beam-management study卻得到接近 **1 HO/min**，另一 550-km study甚至把可接受 ceiling設到約 **1.2/min**。差異來自 constellation density、minimum elevation、earth-fixed cell design、load balancing及是否允許在仍有可見時間時提前換星，而不是哪一篇必然「錯」。citeturn29view1turn27view3turn37view3

**handover interruption 的「常數化」程度也有分歧。** 3GPP 是 condition/test-case based performance requirement；system-level paper為了模擬會把 processing、sync、PRACH、Xn 等 component assumptions固化，因而得到如 **54.375 ms** 或 **40 ms** 的 deterministic sample value。把後者誤稱成所有 NTN handover的 normative constant會混淆標準與 simulator assumption。citeturn10view0turn20view2

**payload power abstraction 有明顯層級差異。** 一類 paper只最佳化 total radiated power；另一類加上每 illuminated beam 的 hardware constant；再細的 model可以加入 PA inefficiency、baseband與platform power。可追溯的 multiuser model是 sum-of-stream/beam powers，而不是普遍採 max-over-users。citeturn38view0turn39view2

**interference 的 load model並不唯一。** Beam-hopping paper可在 slot內用 binary active/inactive gate，每個 active cochannel beam貢獻完整 interference term；precoding paper則直接以 simultaneous user streams形成 interference。前者省略 slot內 fractional load，後者需要更細的 PHY/resource model。citeturn37view2turn39view2

**EE 的 system boundary也沒有統一。** 文獻可以是 global rate/power ratio、max-min user EE、USC+power多目標，或 demand-constrained power minimization；因此「bit/J」數字只有在 numerator、power boundary、traffic cap及time pooling都一致時才可比較。citeturn39view3turn26view1turn38view0turn39view2

反而有兩件事在本次文獻中**幾乎沒有真正分歧**：一是沒有 3GPP 規定的 universal **joules per handover**；二是沒有 3GPP 規定的 universal **handovers per user per minute ceiling**。前者必須由 UE/payload power-state model導出，後者通常由 operator/controller policy或 study-specific constraint決定。citeturn20view2turn37view3turn39view2

## 參考文獻

**3GPP / ETSI**

1. **3GPP TS 38.133**, *NR; Requirements for support of radio resource management*, Release 17。與本調查直接相關的 handover clauses 為 §6.1.1.2.2（NR handover interruption）、§6.1.3.2.2（DAPS handover interruption）、§6.1.4.4.4（conditional handover interruption）。ETSI 官方 archive 顯示 Rel-17 自 V17.5.0 持續維護至 V17.21.0；3GPP CR 2009 對 Rel-17 DAPS interruption 做維護。citeturn39view1turn10view0turn24search0

2. **3GPP TS 38.331**, *NR; Radio Resource Control (RRC); Protocol specification*, Release 17。相關內容包括 measurement events、TimeToTrigger、RRC handover/reconfiguration及RLF timers；官方 3GPP indexed Rel-17 material可見 `timeToTrigger ms0` configuration。citeturn37search1

3. **3GPP TS 38.300**, *NR; NR and NG-RAN Overall Description; Stage-2*, Release 17。用於 NG-RAN mobility／handover architecture與mobility robustness的系統層定義。

4. **3GPP TS 38.214**, *NR; Physical layer procedures for data*, Release 17，§5.2.2.1。用於 CQI／target transport-block error probability；這是 PHY link-adaptation reliability，而不是 NTN session-availability SLA。

5. **3GPP TR 38.821**, *Solutions for NR to support non-terrestrial networks (NTN)*, Release 16。NTN mobility/architecture solution study；應與 Release-17 normative NTN specifications搭配使用，而不應從它推導一個不存在的 handovers/min quota。

6. **3GPP TR 38.811**, *Study on New Radio (NR) to support non-terrestrial networks*, Release 15。Sun–Zhu–Peng 的 550-km LEO simulation明確採用其 NTN channel model。citeturn37view3

**Handover／beam management**

7. S. B. **Iqbal et al.**, “RACH-less Handover with Early Timing Advance Acquisition for Outage Reduction,” **IEEE VTC2024-Spring**, 2024。Table I 提供 54.375-ms CHO interruption decomposition；RACH-less example為40 ms；system-level結果報告 relative outage reduction 18.7%與interruption reduction 43.2%。citeturn20view2turn18view2

8. M. **Hozayen**, T. Darwish, G. Karabulut, H. Yanikomeroglu, “A Graph-Based Customizable Handover Framework for LEO Satellite Networks,” 2022。Starlink Phase-I：1,584 satellites、22 planes、550 km；30-min experiment中 threshold approach 3 HO、graph approach 5 HO。citeturn29view1

9. Y. **Sun**, J. Zhu, M. Peng, “Beam Management in Low Earth Orbit Satellite Communication With Handover Frequency Control and Satellite-Terrestrial Spectrum Sharing,” 2024。1,200 satellites、30 planes、550 km、53°；Table I 設 `H̄=0.004`、200-ms epoch；eq. (3)給出 activation-gated cochannel interference model。citeturn37view2turn37view3

10. J. **Zhu**, Y. Sun, M. Peng, “Beam Management in Low Earth Orbit Satellite Networks with Random Traffic Arrival and Time-varying Topology,” 2024。1,200 satellites、40 planes、600 km；20-ms/120-ms scheduling examples，satellite-allocation update每600 epochs或失去服務能力時執行；平均 inter-satellite HO interval 501 ×120 ms ≈60.12 s。citeturn26view3turn27view3

11. J. **Wu**, S. Su, X. Wang, J. Zhang, Y. Gao, “Accelerating Handover in Mobile Satellite Network,” 2024。以修改版 Open5GS/UERANSIM及實際 LEO constellation geometry做prototype，研究 access/core interaction造成的 handover latency。citeturn29view0

12. P. **Taksande**, J. Mehta, P. Chaporkar, “Handover-Optimal User Association Policy for LEO Satellite-based 5G NTN,” 2026。文中採用 5G gNB-on-satellite context，指出 fixed ground location 對單顆 LEO satellite的典型可見時間約8–12 min，並把 handover minimization與load balancing聯合考慮。citeturn29view2

**Payload power／energy efficiency**

13. C. N. **Efrem**, A. D. Panagopoulos, “Dynamic Energy-Efficient Power Allocation in Multibeam Satellite Systems,” **IEEE Wireless Communications Letters**, vol. 9, no. 2, pp. 228–231, Feb. 2020。以 unmet system capacity與**total radiated power**為multi-objective optimization。citeturn38view0

14. V. N. **Ha**, T. T. Nguyen, E. Lagunas, J. C. Merlano Duncan, S. Chatzinotas, “GEO Payload Power Minimization: Joint Precoding and Beam Hopping Design,” **IEEE GLOBECOM 2022**。§II-B eq. (3) 定義 beam power為 user precoder-power sum；eq. (5)加入 illuminated-beam hardware overhead；eq. (6)最小化其總和。citeturn38view2turn39view2

15. W. U. **Khan**, E. Lagunas, A. Mahmood, S. Chatzinotas, B. Ottersten, “Energy-Efficient RIS-Enabled NOMA Communication for 6G LEO Satellite Networks,” 2023。研究 LEO system energy-efficiency maximization與ground-terminal power allocation。citeturn27view0turn39view3

16. **Liu et al.**, “Rate-Splitting Multiple Access for Quantized ISAC LEO Satellite Systems: A Max-Min Fair Energy-Efficient Beam Design,” 2024。提供 LEO 中 user-fairness／max-min EE 類 objective 的反例，說明「EE」不必等於一個全系統 pooled ratio。citeturn26view1

整體而言，文獻最能支持的 simulator audit baseline 是：**handover 要以 interruption、signalling、failure/outage 等可觀測 cost 分解，而不是假設固定 joules/event；550–600 km 的 satellite-HO operating point 可從約 0.1/min 延伸到約 1/min，explicit 約束則是 study-specific；payload RF power通常對同時傳輸的 streams/beams作加總並可能另加 active-beam hardware overhead；而 activation-gated interference雖有清楚文獻先例，仍不是完整的 traffic-load model。** citeturn20view2turn29view1turn27view3turn39view2turn37view2