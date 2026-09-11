# LEO／NTN 衛星資源配置中的 RL：指標、基線、多目標、示範引導與「Catfish」文獻調查

## 範圍、證據標準與主要結論

本調查以 2018 年以後的 LEO／NTN 衛星切換、波束管理、beam hopping、用戶—衛星關聯與衛星資源配置為核心，另外納入少量與 energy efficiency（EE）或 demonstration/offline RL 直接相關的無線資源配置工作。較早文獻只在它定義方法學基準時納入，例如 DQfD。正式判讀優先使用同行評審期刊／會議；較新的 arXiv 工作只作補充，而且不讓無法核實引用狀態的新 preprint 主導統計。citeturn39search0turn39search3turn46search0turn46search1

表中使用兩個不同的缺值標記。**NR**（not reported / not relevant）表示該論文不是 EE 工作或該欄位不是其報告指標；**NV**（not verifiable from retrieved text）表示索引到的摘要或 HTML 沒有暴露足以可靠分類的公式，因此我不把「無法從索引文字驗證」錯寫成「論文沒有定義」。這一區別對 EE 特別重要，因為許多論文摘要只寫「maximize energy efficiency」或「higher EE」，不足以判定它實際用的是 bits/J、bits/Hz/J、系統總率除總功率、每用戶 ratio 的平均，或其他正規化方式。citeturn46search2turn32academia30turn32academia31turn32academia32

整體結論相當清楚：

1. **簡單規則基線並沒有在這個領域消失。** 在能直接核對 comparator 身分的核心樣本裡，random、最大瞬時訊號／SINR、最長剩餘服務時間、最大可用 channel、greedy、exhaustive search 等反覆出現；它們可以說是「事實上的 baseline family」，但沒有一套所有論文都遵守的正式標準組合。citeturn16view1turn18view0turn39search1turn46search1

2. **核心 LEO 文獻幾乎都把 RL 論文寫成 positive-result paper。** 我沒有在經同行評審、符合本調查核心範圍的 LEO 樣本中找到一篇以「學習方法最終無法打敗簡單規則」作為主要貢獻的論文；但能找到三種較弱、卻很重要的負面證據：簡單規則贏某一個 objective component；RL 在訓練不足時落後規則；以及 scalarization 權重改變會明顯反轉各子目標表現。citeturn18view0turn17view4turn36view0

3. **weighted-sum scalarization 很常見，但「固定一組權重就是標準做法」並不成立。** 有些工作實驗性調權重，有些掃多組權重，有些乾脆建立 Pareto archive；新的 adaptive multi-objective 手法也明確把權衡視為狀態相依問題，而不是永久固定權重。citeturn18view1turn17view2turn17view3turn41academia2

4. **我沒有找到一篇 LEO／NTN 論文明確示範「固定 reward scalarization 與它自己宣稱的 EE ratio endpoint 反向排序」這種強度的診斷。** 最接近的已發表前例，一是承認 episodic/system-level endpoint 無法直接分解成 step reward，因而改用 surrogate reward；二是 constrained RL 顯示把硬限制塞進 reward shaping 會顯著不如直接解 CMDP。citeturn36view0turn43academia3

5. **demonstration-guided RL 在無線 RRM 中存在，但形式更像 offline RL from behavior policies，而不是 DQfD。** 我找到最直接的無線例子是 Asilomar 2023：資料由 random、greedy、TDM、ITLinQ 與不同訓練程度的 RL policy 產生，再用 BCQ/CQL/IQL 做 offline RL；論文把它們稱為 **behavior policies**，而不是 human/expert demonstrators。citeturn36view0

6. **沒有找到可驗證的衛星 beam/handover DQfD、AWR-from-demonstrations 或 solver-seeded DQfD 證據。** 原始 DQfD 是一般 RL 的 human-demonstration 方法，其關鍵包含 demonstration pre-training、supervised large-margin term 與 prioritized replay；這些元件與「把 solver 軌跡放進一般 replay buffer」不是同一個已發表機制。citeturn34academia3

7. **「Catfish」那條 RIS/CDRL 譜系在公開索引中無法獨立閉環。** 用「catfish effect」搭配 RIS、EE、replay memory、competitive reward，以及使用者提供之 reward 符號進行精確查找，沒有得到能獨立確認該論文 bibliographic identity 的結果。因此本報告不能誠實地把「查不到」寫成「0 citations」；目前能下的結論是**引用數與 citing papers 無法獨立核實**。相反地，「catfish effect」在其他機器學習／最佳化文獻確實存在，但意思分別是 population diversity、pruning 或刻意加入 dissent，與 solver-seeded replay 機制並不相同。citeturn32search0turn25academia4turn25academia1

## 報告結果總表

下表先放核心衛星文獻，再放與 EE／demonstration 有直接解釋力的鄰近無線工作。為遵守「數值結果要能定位到 paper figure/table」的要求，我沒有把只有摘要宣稱、但本次無法定位至圖表的 improvement percentage 搬進「結果量級」欄；因此某些論文會比一般 survey table 更保守。

| 論文、venue／year | 系統與假設 | 最佳化目標 | EE 定義與報告量級 | Baselines | 簡單規則是否贏 learned method | HO／service 類指標 |
|---|---|---|---|---|---|---|
| Chen et al., *Human Centered Computing*, 2019 | LEO satellite handover；signal-quality-aware | 衛星選擇／HO 品質 | NR | 早期 signal-quality／criterion 類 HO | 可取得索引不足以判定 | HO 為主題；詳細量級 NV。citeturn21search1turn16view0 |
| He et al., IEEE GLOBECOM, 2020 | 多用戶 LEO、有限衛星負載 | 最小化平均 handover、滿足 load constraints；multi-agent Q-learning | NR | basic criterion-based HO strategies | 摘要結論為 MARL 較佳；無可定位數值轉錄 | average HO、blocking。citeturn37search2 |
| Jiang & Zhu, IEEE TWC, 2020 | multi-layer satellite network | capacity management via RL | NR | 傳統 capacity-management 方法；細節 NV | NV | 非主要 HO 論文。citeturn39search4 |
| Hu et al., IEEE TVT, 2020 | flexible satellite payload、mobile terminals | payload/resource adaptation with MADRL | NV；不是以可核對 EE ratio 作主要報告 | satellite resource-allocation methods | NV | resource-demand satisfaction；HO 非主指標。citeturn39search5 |
| Liao et al., IEEE Communications Letters, 2020 | multibeam satellite resource allocation | distributed/multi-agent DRL resource allocation | NR/NV | 傳統分配方法 | NV | 非 HO 主題。citeturn21search2 |
| Wang et al., IEEE WCSP, 2021 | LEO satellite communications | DRL satellite handover | NR | 傳統 HO criterion / RL comparator；索引細節 NV | NV | HO performance。citeturn16view0 |
| Lin et al., IEEE TVT, 2022 | beam-hopping satellite；time/space/frequency flexibility | maximize throughput、minimize inter-cell delay unfairness | NR | conventional greedy BH、heuristic optimization、既有 DRL | 論文將 greedy 描述為不處理 long-term reward；最終 learned method 為正面結果 | traffic satisfaction/delay，非 HO。citeturn39search0 |
| Yin et al., *Wireless Communications and Mobile Computing*, 2022 | satellite-terrestrial integrated network | joint satellite scheduling/resource allocation with DRL | NR/NV | 傳統或 optimization comparators；細節 NV | NV | scheduling/resource metrics。citeturn39search6 |
| Shen et al., IEEE VTC-Spring, 2023 | multi-LEO constellation | hierarchical multi-agent MAB resource allocation | NR/NV | resource-allocation comparators；全文細節 NV | NV | 非 HO 主指標。citeturn42search0 |
| Lee et al., IEEE TWC, 2024 | LEO HO protocol；用 DRL 直接做 HO decision | access delay + collision；reward \(r=-D-\nu C\) | NR | conventional HO、random、不同 DRL algorithms | **有單項例外**：某些設定下 random 的 collision 表現可較佳；DHO 的主張仍是整體 delay/HO protocol 改善 | Table VII 顯示權重敏感性：\(\nu=5\) 時 access delay 0.0875、collision 0.0845；\(\nu=1/20\) 時分別 0.3461、0.0613，明確呈現兩目標 trade-off。citeturn18view0turn18view1 |
| Chen, Ozger & Cavdar, 2024 | OneWeb-style LEO、飛行載具與 ground terminals | network utility：HO、CINR、blocking 的 weighted combination；Nash-SAC | NR | MRST、MAC、MIS、Q-learning、Nash-DQN | Fig. 4 的 composite utility 中沒有：Nash-SAC 71.1、Nash-DQN 70.0、Q-learning 66.5、MRST 64.0、MAC 49.8、MIS 47.9 | handovers、blocking、CINR/network utility。citeturn16view1turn18view2 |
| Sun et al., IEEE Communications Letters, 2024 | multi-beam LEO | multi-objective RL handover | NR | 索引文字不足以完整辨識 | NV | HO multi-objective；全文結果 NV。citeturn46search7 |
| Liu et al., IEEE TWC, 2024 | mega-constellation、dynamic propagation；集中式與分散式設計 | long-term network utility，考慮 user rate 與 load balancing | NR | existing handover schemes | 摘要報 proposed methods 較佳；無圖表定位數值轉錄 | user utility、capacity/load、HO。citeturn46search0 |
| Badini et al., IEEE TAES, 2024 | user-centric LEO，multiple traffic profiles，decentralized MADQN | 低 HO、低 blocking、衛星 load balance、不同 traffic-profile QoS | NR | conventional **single-criterion** HO rules | 摘要主張 MADQN 較單準則優；未把摘要百分比當作圖表數值轉錄 | HO rate、blocking rate、load/QoS。citeturn46search1turn46search6 |
| Chen et al., IEEE VTC-Spring, 2024 | multi-LEO、多 beam、handover + beam switching + power | **maximize EE subject to user SINR requirement** | **EE：NV**；可索引摘要沒有足夠公式判定 bits/J vs 其他；絕對 EE 量級 NV | exhaustive beam search、fixed power control | 摘要為 HOBS 較佳，未找到 simple rule 最終贏 EE | latency、SINR、EE；HO 與 beam search 聯合處理。citeturn46search2 |
| Feng et al., *Electronics*, 2024 | GEO VHTS、multi-beam flexible payload；作為衛星 resource-allocation 鄰近工作 | demand-capacity matching + power reduction；double-timescale MADRL | EE 不是直接 ratio endpoint；報 power consumption/resource utilization | benchmark resource-management scheme | 未報 rule 勝出 | 非 HO；capacity-demand matching 與 power。citeturn39search5 |
| Tong et al., IEEE TAES, 2025 | giant LEO constellation | A2C HO，綜合 bandwidth、elevation、signal strength、potential service time、service quality | NR | random、max free channels、max service time、MADQL、max instantaneous signal strength | 摘要主張 A2C 整體較佳；沒有主 metric rule winner | handover number、signal stability、blocking／handover failures。citeturn39search1 |
| Xie et al., multi-satellite BH work, 2025 | multi-NGSO beam hopping + power allocation | long-term throughput + long-term cumulative average delay；PPO hybrid action | NR | 四個 benchmark methods；可取得摘要未列完整名稱 | 摘要為 proposed method 較佳；未轉錄未定位百分比 | delay、throughput；非 HO。citeturn37academia18 |
| Shen et al., IEEE ICC, 2025 | MF-RIS-assisted LEO | **long-term EE**；MF-RIS amplification/phase/EH ratio + LEO beamforming，federated MADDPG | **EE：NV**；索引摘要未提供可分類公式／絕對值 | centralized DRL、distributed MADDPG；另比較 fixed/no EH、conventional RIS/no RIS architectures | 沒有 simple rule winner；比較主要是 learned/architecture variants | 非 HO；EE/resource configuration。citeturn32academia30turn42search0 |
| Jang et al., *ETRI Journal*, 2026 | integrated LEO-terrestrial、高移動 terminal；CNN-LSTM RSRP prediction + QMIX | predictive target/timing selection、network stability、HO efficiency | NR | 摘要未列完整 comparator set | NV | proactive HO、RSRP prediction、decentralized execution。citeturn39search3 |
| Sun et al., IEEE TAES, 2026, HAS-DDQN | LEO + high-speed rail | multi-objective DDQN：throughput vs handovers；另處理 simultaneous authentication delay | NR | similar HO schemes；索引摘要未列完整名稱 | 摘要為 proposed integrated method 較佳 | handovers、throughput、blocking、HO delay。citeturn46search1 |
| Nguyen et al., RIS-assisted multi-UAV, 2021；鄰近 EE | RIS + multiple UAVs | joint UAV power + RIS phases，maximize EE | **EE：NV**；未從摘要公式分類 | conventional schemes | 摘要報 DRL 較佳；未轉錄無圖表定位數值 | 非衛星 HO。citeturn32academia31 |
| Zhou et al., RIS-aided RAN, 2023；鄰近 EE | RIS + RAN sleep/power control | joint sleep + transmit-power control；hierarchical DRL，另用 fractional programming 控 RIS | **EE：NV**；報 EE 與 energy consumption，但索引未暴露完整 ratio formula | conventional HDRL、surrogate optimization | 沒有 simple-rule primary winner | 非 HO；energy consumption + EE。citeturn32academia32 |
| Nauman et al., integrated terrestrial-satellite NOMA, 2023；鄰近 EE | satellite-terrestrial + NOMA + caching | user association、cache、power via MADDPG；enhance EE / reduce delay | **EE：NV**；無可靠絕對量級可轉錄 | single-agent DRL | comparator 主要 learned-vs-learned | delay + EE。citeturn37academia19 |

這張表揭露一個對 EE 比較非常重要的 reporting problem：**同一批「energy-efficient」論文並沒有提供一個可直接橫向整理成單一 bits/J distribution 的共同報告格式。** HOBS 說 maximize EE subject to SINR，FEMAD 說 long-term EE，RIS-UAV 及 RIS-RAN 工作也說 maximize/improve EE，但可公開索引文字不足以在所有論文上一致區分 system ratio、normalized ratio 或 per-user aggregation；同時不少核心 handover 論文根本不使用 EE，而使用 utility、handover count、blocking、delay、throughput 或它們的 weighted combination。citeturn46search2turn32academia30turn32academia31turn32academia32

因此，本調查**沒有找到足夠證據支持「LEO handover 文獻通常以 pooled decoded bits / pooled system joules across the entire evaluation 為 EE primary endpoint」這個說法**。更準確的描述是：EE 定義與 aggregation layer 在跨論文比較時不一致，而且相當多 handover work 根本不是 ratio-EE paper。這也意味著，把不同論文圖上的「EE」絕對值直接拿來和另一個 simulator 的 bit/J 比較，若沒有先核對 rate aggregation、power model、bandwidth normalization、traffic cap 與時間 aggregation，方法學上並不可靠。citeturn46search2turn32academia30turn37academia19

## 基線實務

就能直接識別 baseline 身分的樣本而言，簡單規則是常客而非例外。He et al. 對 basic-criterion HO；Lee et al. 有 conventional 與 random；Nash-SAC 同時測 MRST、maximum available channels、maximum instantaneous signal strength；Badini et al. 明確以 single-criterion approaches 作比較；Tong et al. 更同時包含 random、maximum free channels、maximum service time 與 maximum instantaneous signal strength。Beam-hopping/resource-allocation 工作也反覆出現 greedy 與 exhaustive-search 類基線。citeturn37search2turn18view0turn16view1turn46search1turn39search1turn39search0

用本報告中 **baseline 身分足以直接編碼的十三篇** 作 audit，十篇明確包含至少一個「random／單準則／greedy／max-signal／max-service-time／exhaustive」這類簡單規則；另有一篇至少包含非學習 surrogate optimization，而 FEMAD 與 integrated-NOMA 的主要 comparator 則較接近 learned-versus-learned。這個計數不是 meta-analysis，也不能當作全領域 population estimate，但足以否定「這個領域通常只做 learned-vs-learned」的強說法。citeturn39search0turn46search2turn32academia30turn37academia19turn32academia32

**沒有正式的 mandatory baseline set。** 不過，跨數篇 handover paper 重複率最高的其實形成一個很明顯的 de facto family：

| Baseline family | 文獻中的典型名稱 | 它測的是什麼 |
|---|---|---|
| 隨機 | Random | 學習方法是否連最基本合法選擇都無法穩定超越。Lee et al.、Tong et al. 都使用。citeturn18view0turn39search1 |
| 最強鏈路 | maximum instantaneous signal strength、greedy largest SINR、max-RSRP association | 測試「直接拿眼前最好 radio link」是否已足夠。Nash-SAC、Tong 與無線 offline-RL RRM 都有此類規則。citeturn16view1turn39search1turn36view0 |
| 最長可服務時間 | MRST、maximum service time | 專門壓低未來 HO 頻率；Nash-SAC 與 Tong 都有。citeturn16view1turn39search1 |
| 負載／容量規則 | maximum available/free channels、single-criterion load rules | 測試 load-aware HO 是否需要 RL。citeturn16view1turn46search1 |
| greedy／exhaustive optimization | greedy beam hopping、exhaustive beam search | 在 beam/resource allocation 中反覆出現。citeturn39search0turn46search2 |

對「非學習 baseline 是否會贏」要區分**整體主指標**與**單一 component**。我沒有在上面經同行評審的核心 LEO 論文中找到作者把 simple rule 報為收斂後 composite/primary objective 的最終 winner；然而這不代表 simple rule 從不贏。Lee et al. 的結果顯示 delay-oriented DHO 在 collision component 上可以落後，Table VII 更直接顯示只改 scalarization coefficient 就會讓 delay 與 collision 沿相反方向大幅移動。Li et al. 的 evolutionary multi-objective work 則刻意把一個 greedy ARGP 方法視為 achievable-rate objective 的 upper-bound-like comparator；也就是說，它在那個單一 objective 上本來就可以比平衡型 learned policy 更高。citeturn18view0turn17view4

鄰近 wireless RRM 的結果更直接。Yang et al. 在 Fig. 1 明寫：online SAC 在訓練充分後超越 rule baselines，但**訓練不足時可以比 rule-based policies 差**。這是一個很少被衛星論文正面展示、但與實際 baseline audit 高度相關的 diagnostic precedent。citeturn36view0

所以，一個符合目前文獻實務、又比多數既有論文更嚴格的 LEO handover baseline suite，至少應含 random、max-link-quality、longest-remaining-service、load/capacity-aware rule，以及一個與 objective 結構直接對應的 greedy rule；只拿 DQN、DDQN、PPO、SAC 彼此比較，並不足以代表這個領域最常見的基線實務。這個結論是由上述 recurring comparator families 推得，而不是來自任何單一「標準 baseline」規範。citeturn16view1turn18view0turn39search1turn46search1

## 多目標處理與約束式 RL

固定／線性 scalarization 在這批文獻中**非常常見，但不是唯一做法，而且權重選擇通常不像 physical parameter 那樣有第一原理依據**。

最乾淨的例子是 Lee et al.：reward 是 \(r=-D-\nu C\)，論文明說 \(\nu\) 是 balance access delay 與 collision 的 normalization coefficient，並以實驗調整。Table VII 比較了 \(\nu=5\) 與 \(\nu=1/20\)，前者偏 delay、後者偏 collision；結果不是兩者同步改善，而是典型 Pareto trade-off。這裡的權重不是由 3GPP requirement 或某個物理價格直接推出，而是用來選 operating point。citeturn18view1turn18view0

Nash-SAC 的 network utility 也是明確的 weighted construction：handover、CINR、blocking 分別乘上 \(w_1,w_2,w_3\)，reward 另外納入 remaining visibility、CINR、available channels 與 handover penalty。可取得文字能驗證 weighted-sum 結構，但不足以可靠復原每個實驗的完整 numerical weight vector，因此不應自行補值。citeturn18view2

Cao et al. 則沒有假裝只有一組「正確權重」。其 Table II 明確評估四個三目標 weight vectors：

\[
(1/3,1/3,1/3),\quad
(1/2,1/4,1/4),\quad
(1/4,1/2,1/4),\quad
(1/4,1/4,1/2).
\]

也就是 equal weighting 與三種「單一 objective 權重加倍」情境都被測試。citeturn17view2

Li et al. 走得更遠：每個 task 仍可由 weight vector \(w\) 定義，但不是訓練一個永久固定 scalar reward 後就宣告問題解完，而是用 evolutionary multi-objective DRL 與 Pareto archive 保留一組 nondominated policies。它同時優化 uplink achievable rate、terminal energy consumption 與 satellite switching number，因此方法本身承認「不同 trade-off 對應不同 policy」而不是「一個固定 vector 代表所有 preference」。citeturn17view3turn17view4

鄰近 wireless offline-RL 工作也揭示另一個常見問題：Yang et al. 的最終 system score 是 sum-rate 與 fifth-percentile rate 的 linear combination，但作者明確說這個 episodic score **不能直接 decomposed into per-step reward**，所以實際 RL reward 改採另一個可逐步計算的 PF-like expression，再透過 \(\lambda\) 調整 sum/tail trade-off。這不是 EE anti-alignment 的證明，但它是非常直接的 published precedent：**declared evaluation endpoint 與 training reward 可以不是同一個數學函數。** citeturn36view0

### 對 fixed scalarization 的已發表批評有多強？

在本次檢索到的 LEO／NTN corpus 中，我沒有找到論文做出以下強結論：**存在兩個政策 A/B，使 fixed weighted reward 排 A>B，但真正宣稱的 EE ratio endpoint 排 B>A，並因此證明 scalarized reward anti-aligned。** 因此，若需要這種「反向排序」作 precedent，目前不能把一般 Pareto-tradeoff 文獻誇大成相同結果。

已發表文獻提供的是三個較弱、但可靠的論點：

第一，Lee et al. 的 Table VII 證明 scalarization coefficient 的選擇會實質改變哪個子目標最好；權重不是中性的。citeturn18view0

第二，Yang et al. 明確承認 system endpoint 無法逐步分解，必須另設 surrogate reward，因此「reward 正確最佳化」不自動等於「system metric 正確最佳化」。citeturn36view0

第三，在 energy-constrained wireless control 中，Khairy et al. 不是把所有東西永久塞進 reward weight，而是把問題寫成 CMDP，以 Lagrangian primal-dual policy optimization 直接處理 multiple energy constraints；作者並直接將這種 constrained-DRL 解法與「把 energy costs 透過 reward shaping 處理」的 DRL 做比較，結論支持直接處理 constraints。citeturn43academia3

這使 constrained RL 成為特別重要的替代設計。Khairy et al. 的 primary objective 是 long-term network capacity，而 UAV energy sustainability 是約束；bounds 源自 solar-powered UAV 的能量可持續條件，而不是把 energy 與 capacity 先換成任意同尺度 reward，再手調一組永久權重。citeturn43academia3

在我能直接核實的 LEO handover paper 中，則比較常看到「rate/load/HO/blocking 放進 utility」或「maximize EE subject to SINR」的最佳化問題，而**沒有找到一個已成熟、反覆採用的 satellite-handover CMDP baseline family**。Liu et al. 考慮 rate requirement 與 satellite capacity/load，HOBS 明確把 SINR requirement 作為 EE optimization constraint，但這和用 CMDP/Lagrange multiplier 訓練 constrained policy 還是不同概念。citeturn46search0turn46search2

因此，對 EE 類問題最保守的文獻結論不是「linear scalarization 已被證明錯誤」，而是：**它只是 preference encoding 的一種方式，不是 ratio endpoint、constraint satisfaction 或 Pareto optimality 的替代定義。** 現有衛星／無線文獻本身已經同時存在 weight tuning、multi-weight evaluation、Pareto archives 與 CMDP 四條路徑。citeturn18view1turn17view2turn17view3turn43academia3

## 示範引導 RL 在無線與衛星系統中的實際證據

最重要的區分是：**「用 heuristic/solver 產生資料」並不自動等於 DQfD。**

原始 DQfD 的文獻定義很具體：Hester et al. 以 demonstrations 啟動 DQN，結合 temporal-difference updates、supervised classification/large-margin imitation objective 與 prioritized replay，並在正式 online learning 前利用 demonstration data。示範來源是先前的 expert/human control data；演算法也容許 learner 後來超越 demonstrator。citeturn34academia3

在本次 LEO beam/handover/resource-allocation corpus 中，我**沒有找到已發表的 DQfD deployment**；也沒有找到把 solver/heuristic trajectory 直接稱為 DQfD、再做 DQfD-style margin loss + permanent demo prioritization 的衛星實例。這個「未找到」只適用於本次檢索範圍，不應誇張為數學上的不存在證明。

目前最接近且能完整核實的無線案例，是 Yang et al. 的 *Offline Reinforcement Learning for Wireless Network Optimization with Mixture Datasets*，Asilomar 2023。它研究 user scheduling，使用 BCQ、CQL、IQL；資料來源不是單一 human expert，而是不同 **behavior policies**。citeturn36view0

| 工作 | 無線／衛星任務 | 資料／demonstrator 是誰 | 文獻怎麼稱呼 | 學習方式與 reported effect |
|---|---|---|---|---|
| Hester et al., DQfD | 一般 RL benchmark，**非 wireless** | human/expert demonstration | demonstrations | DQN + TD losses + supervised margin + prioritized replay；demonstrations 可加速早期學習，learner 可超越 demonstrator。citeturn34academia3 |
| Yang et al., Asilomar 2023 | wireless RRM user scheduling | Random、Greedy、TDM、ITLinQ；另有 early-stopped 與 fully trained online RL | **behavior policies (BPs)**，資料稱 offline datasets | Fig. 2：高品質 expert dataset 下 offline RL 快速得到好 policy；Fig. 3：單一低品質 BP 會限制 IQL；Fig. 4：混合多個低品質 BP 可大幅改善 offline policy。citeturn36view0 |
| Yang et al. 的 Mixed-ITLinQ / Mixed-RL | 同上 | heuristic + rule policies，或 bad RL + rules | heterogeneous / mixture datasets | Fig. 4 的資料配置為主 BP 50%、Greedy 20%、TDM 20%、Random 10%；核心發現是 diversity/coverage 可以讓多個 individually poor BPs 合成有用 dataset。citeturn36view0 |
| Dong et al., 5G resource allocation, 2020 | bandwidth + power allocation | model-based optimal resource-allocation solutions 用來訓練 NN approximation | deep supervised/model-assisted learning；**不是 RL-from-demonstrations** | 用神經網路近似 optimization policy，再用 transfer learning 適應 non-stationarity；這是 solver supervision 的鄰近範式。citeturn35academia2 |
| CoCoRL, Lindner et al., 2023；**非 wireless** | constrained policy learning | 多個 safe demonstrations，可來自不同、未知 rewards | constraint learning from demonstrations | 從 demonstration construction convex safe set；重點是即使 demos suboptimal，只要它們是 safe，仍可學 transferable constraints。citeturn44academia2 |
| Gaurav et al., 2022；**非 wireless** | inverse constrained RL | constrained expert demonstrations | learning soft constraints | 已知 reward、未知 soft constraints，反推 expert 所遵守的 cumulative constraints。citeturn44academia1 |
| A-SILfD, 2022；**非 wireless** | continuous-control LfD | imperfect-quality expert demonstrations | self-imitation / learning from demonstrations | 透過 policy constraints 與 Q-ensemble 降低被 imperfect demonstrator 誤導的風險。citeturn44academia3 |

這裡對「solver 或 heuristic demonstrator 在無線界叫什麼」有一個非常實際的答案：**offline-RL 文獻通常叫它 behavior policy，而不是 expert demonstrator。** Yang et al. 明確把 Random、Greedy、TDM、ITLinQ 全部當作 BPs；只有最佳 online RL dataset 在 Fig. 2 被叫作 expert dataset。citeturn36view0

這個命名差異很重要，因為它反映假設差異。DQfD 的演算法結構特別利用「demonstrator action 值得模仿」；offline RL 則更關心 data coverage、distribution shift 與 conservative value estimation。Yang et al. 的低品質實驗甚至明確顯示：一個差的 behavior policy 單獨產生的 dataset，offline learner 通常只能得到很有限的增益；但不同差 policy 混合後，coverage 可以改善。citeturn36view0turn34academia3

### Demonstrator 只擅長某一目標、卻在另一目標很差時怎麼辦？

我沒有找到 wireless/satellite paper 精確符合「heuristic expert 在 objective A 很強、但**違反 constraint B**，然後 demonstration-RL 專門解決這件事」的 published case。因此不能虛構一個衛星 precedent。

一般 LfD/safe-RL 文獻提供的處理方式反而很有啟發性：

- **不要把 expert 當成絕對最優。** A-SILfD 明確針對 imperfect expert demonstrations，目標是讓 policy improvement 不被品質不均的 demonstration 綁死。citeturn44academia3
- **安全 constraints 與 reward competence 分開建模。** CoCoRL 允許 demonstrations 對不同 rewards 是 suboptimal，只要求它們落在 safe set；再由 demonstrations 學 constraint，而不是把 demonstrator 的每個 action 都當成正確答案。citeturn44academia2
- **如果 demonstration 本身不安全，不能無條件當成 safety evidence。** 這是從 CoCoRL 的 safe-demonstration 假設直接推得的限制，而不是論文聲稱其方法可以「修復 unsafe expert」。citeturn44academia2
- **在 wireless offline RL 中，可以把低品質 heuristic 視為 behavior data，而不是 expert label。** Mixed-dataset 方法的價值來自 coverage，不是「強迫 learner 模仿 heuristic」。citeturn36view0

因此，在 solver/heuristic 對一個 objective 很強但對另一個 requirement 很差的情境下，現有文獻比較支持「把它當 behavior data／partial expertise」，再用 offline RL、constraint model 或 learner-relative acceptance 決定何時採用，而不是無條件做 DQfD-style imitation。

就本次檢索而言，我也沒有找到 LEO／NTN beam management 或 handover 中的 **Advantage-Weighted Regression from demonstrations** 實例；AWR 類演算法不是目前這個衛星子領域中已建立的 baseline family。相反地，online DQN/DDQN/A2C/PPO/SAC/MADRL 與 rule baselines 才是主流可見組合。citeturn18view0turn39search1turn39search3turn46search0

## 「Catfish」譜系：能驗證什麼，不能驗證什麼

這一部分的結論比其他章節更保守，原因是 bibliographic identity 本身沒有在公開索引中成功閉環。

我針對「catfish effect」與 RIS、reconfigurable/intelligent reflecting surface、energy efficiency、replay memory、competitive reward，以及 \(r^C,r^{CF},r^M\) 等記號做精確查找，**沒有找到能把所描述五段機制綁到一篇可獨立識別之 peer-reviewed/arXiv record 的結果**。因此：

| 問題 | 本次可支持的結論 |
|---|---|
| 有沒有 independent replication？ | **未找到。** 但因原 paper bibliographic identity 未能獨立 resolve，不能把這寫成已證明「不存在」。 |
| 有沒有其他 group follow-up？ | **未找到可與該五段機制一一對應的 follow-up。** |
| 同作者後續？ | 無法在不先可靠識別 source paper/authors 的前提下做 defensible author-lineage attribution。 |
| Citation count？ | **無法核實，不應報 0。** 「搜尋未命中」不是「citation count = 0」。 |
| Who cites it？ | 同理，沒有可靠 source identity 就不能產生 citing-paper list。 |

這種回答雖然不像直接給一個 citation number 那麼漂亮，但研究上比較正確：若連 title/DOI/author record 都沒有獨立對上，任何「0 次引用」或「只有某某引用」都是把 retrieval failure 誤當 bibliometric fact。

### 「SASR / Shen et al.」沒有解析成所需引用

以 SASR + Shen + reinforcement learning／wireless 等關鍵字查找，沒有找到一篇與 competitive-reward term 或 RIS resource allocation 對得上的 Shen et al. 論文。搜尋得到的明確「SASR」反而是 2025 年的 *Step-wise Adaptive Integration of Supervised Fine-tuning and Reinforcement Learning for Task-Specific LLMs*；它的作者是 Chen et al.，研究的是 SFT/GRPO hybrid training，與 RIS／wireless competitive reward 無關。citeturn45academia0

所以，在目前證據下，「SASR / Shen et al.」不能被當成一條已成功解析的 reinforcement-learning attribution。比較安全的 bibliographic 狀態是：**unresolved citation**。

### 「Catfish effect」這個名字確實存在，但機制不是同一件事

這個術語在其他領域不是空白。

較早的 optimization／swarm-intelligence 文獻使用「catfish effect」來維持 population diversity、避免 premature convergence；相關描述是重新配置表現差的 particles 或在 population stagnation 時引入擾動，與 replay-buffer seeding 無關。citeturn32search0turn32search2

2018 年還有 *A Catfish Effect Based Team Recommendation System*，用的是「加入競爭者刺激團隊」的組織／推薦系統概念，也不是 RL replay 機制。citeturn3search1

2023 年的 meta-learning work 使用 **catfish pruning**，將高 memorization-score 的 parameters prune 掉以打破 rote memorization、改善 meta-generalization；同樣不是雙 replay buffer、solver demonstrations 或 competitive reward。citeturn25academia4

2025 年的 multi-agent LLM 醫療推理工作則提出 **Catfish Agent**：它刻意注入 dissent，打破多 agent 過早 consensus。這裡的「catfish」意義是刺激／挑戰既有共識，也與 RL experience replay 無關。citeturn25academia1

因此，可驗證的結論是：**「catfish effect」不是 RL 中一個具有固定技術定義的標準 mechanism name。** 它在 optimization、team recommendation、meta-learning、multi-agent LLM 中都被借用，但機制不同。沒有證據顯示這些工作形成「solver-seeded replay + EE threshold split + asymmetric discount + periodic 70/30 batch mixing + competitive reward」的共同研究線。citeturn32search0turn25academia4turn25academia1

這也意味著，不能因為其他文章出現 “catfish effect” 四個字，就把它們算成 RIS/CDRL 機制的 replication 或 citation lineage。

## 負面與診斷性結果

核心 LEO RL 文獻的 publication pattern 明顯偏向「提出方法並報改善」：He、Liu、Badini、Tong、HOBS、Jang 等摘要都把 proposed method 描述成 outperforming 或 improving network performance。這不等於不存在失敗的 RL policy，而是代表**已發表文章通常沒有把「simple baseline beats RL」當主 headline**。citeturn37search2turn46search0turn46search1turn39search1turn46search2turn39search3

目前最有價值的 published diagnostic precedents 有以下幾類。

| Diagnostic precedent | 發現 | 對衛星 RL 方法學的意義 |
|---|---|---|
| Lee et al., IEEE TWC 2024 | Table VII：只改 \(\nu\) 就把 access-delay/collision operating point 大幅移動；某些 collision settings 下 random 也有競爭力。citeturn18view0turn18view1 | reward weight 的成功不能用單一 scalar training curve 取代 component-level audit。 |
| Yang et al., Asilomar 2023 | Fig. 1：online RL 在 training 不足時可落後 rule baselines；Fig. 3：bad behavior-policy dataset 會限制 offline RL gain。citeturn36view0 | 「有 RL」本身不是 superiority guarantee；training budget 與 dataset quality 都需要 baseline-controlled evaluation。 |
| Yang et al., Fig. 4 | 多個 individually poor behavior policies 的 mixture 反而可形成較好的 offline dataset。citeturn36view0 | heuristic 資料的價值可能是 coverage/diversity，而不是 expert optimality。 |
| Li et al., EMODRL | greedy ARGP 被用作 achievable-rate objective 的強 comparator／upper-bound-like reference，而 learned method處理的是多目標 Pareto trade-off。citeturn17view4 | 「simple rule 在一個 component 上更高」不一定意味多目標 learner 失敗；必須先確定 declared endpoint 是哪個。 |
| Khairy et al., constrained DRL | CMDP/Lagrangian 直接處理 energy sustainability，並與 energy-cost reward shaping 比較。citeturn43academia3 | 對 hard requirements，reward penalty 未必是最合適建模方式；constraint satisfaction 應獨立檢查。 |
| DHO／offline-RL endpoint design | 最終 system metric 可能不能逐步 decomposed；文獻會改用 surrogate step reward。citeturn36view0 | 必須分開驗證「training reward」與「evaluation metric」的 ordering，而不能只證明 reward 收斂。 |

值得特別指出，Yang et al. 的論文不是事後 blog 或 benchmark critique，而是正式的 Asilomar paper；它把「online RL 早期可能輸給 rule baseline」、「offline RL 對 behavior-policy quality 敏感」直接放進主要實驗。這是我在 wireless resource-allocation 文獻中找到最接近「diagnostic rather than only victory lap」的 precedent。citeturn36view0

至於更強的結果——**一個訓練完成、驗證充分的 satellite RL checkpoint，在論文自己宣稱的 primary endpoint 上被 one-line physical heuristic 顯著擊敗，而且分析進一步定位成 reward/objective misspecification**——我沒有在符合來源標準的核心 LEO 文獻中找到同等前例。這使這種結果若被嚴格做成 endpoint audit、mechanism ablation 與 baseline-controlled study，並非「文獻早已大量做過」的重複題材；現有 published precedents主要停留在 scalarization trade-off、training insufficiency、surrogate-reward mismatch 與 constrained-vs-shaped reward 等較局部診斷。citeturn18view0turn36view0turn43academia3

同時也要避免反向誇張：這不代表「RL 在 LEO 沒用」。文獻裡有很合理的 RL 動機，例如 dynamic propagation、巨大組合 action space、long-horizon handover consequences、time-varying traffic 與 decentralized partial information；這些都是固定 myopic rule 不一定能處理的結構。真正從文獻得到的教訓，是 **learned policy 仍需對最直接的 rule baseline，以及真正宣稱的 system endpoint 做獨立驗證**。citeturn46search0turn39search0turn46search1turn39search3

## 參考文獻

| 文獻 | Bibliographic record |
|---|---|
| Chen et al. | M. Chen et al., “Reinforcement Learning Based Signal Quality Aware Handover Scheme for LEO Satellite Communication Networks,” *Human Centered Computing*, Springer, 2019. citeturn21search1turn16view0 |
| He et al. | S. He et al., “Load-Aware Satellite Handover Strategy Based on Multi-Agent Reinforcement Learning,” IEEE GLOBECOM, 2020. citeturn37search2 |
| Jiang & Zhu | C. Jiang and X. Zhu, “Reinforcement Learning Based Capacity Management in Multi-Layer Satellite Networks,” *IEEE Transactions on Wireless Communications*, 2020. citeturn39search4 |
| Hu et al. | X. Hu et al., “Multi-Agent Deep Reinforcement Learning-Based Flexible Satellite Payload for Mobile Terminals,” *IEEE Transactions on Vehicular Technology*, 2020. citeturn39search5 |
| Liao et al. | X. Liao et al., “Distributed Intelligence: A Verification for Multi-Agent DRL-Based Multibeam Satellite Resource Allocation,” *IEEE Communications Letters*, 2020. citeturn21search2 |
| Wang et al. | J. Wang et al., “Deep Reinforcement Learning-Based Satellite Handover Scheme for Satellite Communications,” IEEE WCSP, 2021. citeturn16view0 |
| Lin et al. | Z. Lin et al., “Dynamic Beam Pattern and Bandwidth Allocation Based on Multi-Agent Deep Reinforcement Learning for Beam Hopping Satellite Systems,” *IEEE Transactions on Vehicular Technology*, 2022. citeturn39search0 |
| Yin et al. | “Deep Reinforcement Learning-Based Joint Satellite Scheduling and Resource Allocation in Satellite-Terrestrial Integrated Networks,” *Wireless Communications and Mobile Computing*, 2022. citeturn39search6 |
| Shen et al. | L.-H. Shen et al., “Hierarchical Multi-Agent Multi-Armed Bandit for Resource Allocation in Multi-LEO Satellite Constellation Networks,” IEEE VTC-Spring, 2023. citeturn42search0 |
| Lee et al. | J.-H. Lee, C. Park, S. Park, and A. F. Molisch, “Handover Protocol Learning for LEO Satellite Networks: Access Delay and Collision Minimization,” *IEEE Transactions on Wireless Communications*, 2024. citeturn37academia21turn18view0turn18view1 |
| Chen, Ozger & Cavdar | “Nash Soft Actor-Critic LEO Satellite Handover Management Algorithm for Flying Vehicles,” 2024. citeturn15view0turn16view1turn18view2 |
| Sun et al. | Y. Sun, Y. Zhai, W. Wu, P. Si, and F. R. Yu, “Handover for Multi-Beam LEO Satellite Networks: A Multi-Objective Reinforcement Learning Method,” *IEEE Communications Letters*, 2024. citeturn46search7 |
| Liu et al. | H. Liu et al., “A Multi-Agent Deep Reinforcement Learning-Based Handover Scheme for Mega-Constellation Under Dynamic Propagation Conditions,” *IEEE Transactions on Wireless Communications*, 2024. citeturn46search0 |
| Badini et al. | N. Badini, M. Jaber, M. Marchese, and F. Patrone, “User-Centric Satellite Handover for Multiple Traffic Profiles Using Deep Q-Learning,” *IEEE Transactions on Aerospace and Electronic Systems*, 2024. citeturn46search1turn46search6 |
| Chen et al., HOBS | S.-H. Chen, L.-H. Shen, K.-T. Feng, L.-L. Yang, and J.-M. Wu, “Energy-Efficient Joint Handover and Beam Switching Scheme for Multi-LEO Networks,” IEEE VTC-Spring, 2024. citeturn46search2turn46search3 |
| Cao et al. | Y. Cao, S.-Y. Lien, Y.-C. Liang, D. Niyato, and X. Shen, “Collaborative Deep Reinforcement Learning for Resource Optimization in Non-Terrestrial Networks,” 2024. citeturn15view2turn17view1turn17view2 |
| Li et al. | J. Li et al., “Collaborative Ground-Space Communications via Evolutionary Multi-Objective Deep Reinforcement Learning,” 2024. citeturn15view3turn17view3turn17view4 |
| Feng et al. | L. Feng et al., “Double-Timescale Multi-Agent Deep Reinforcement Learning for Flexible Payload in VHTS Systems,” *Electronics*, 2024. citeturn39search5 |
| Tong et al. | C. Tong et al., “LEO Satellite Handover Using Advantage Actor-Critic Algorithm in Giant Constellation Network,” *IEEE Transactions on Aerospace and Electronic Systems*, 2025. citeturn39search1 |
| Xie et al. | X. Xie et al., “Multi-Satellite Beam Hopping and Power Allocation Using Deep Reinforcement Learning,” 2025. citeturn37academia18 |
| Shen et al., FEMAD | L.-H. Shen et al., “Federated Deep Reinforcement Learning for Energy Efficient Multi-Functional RIS-Assisted Low-Earth Orbit Networks,” IEEE ICC, 2025. citeturn32academia30turn42search0 |
| Jang et al. | H. Jang et al., “Proactive Handover Optimization via Multi-Agent Deep Reinforcement Learning in Integrated LEO Satellite–Terrestrial Networks for High-Mobility Terminals,” *ETRI Journal*, 2026. citeturn39search3 |
| Nguyen et al. | K. K. Nguyen et al., “Reconfigurable Intelligent Surface-Assisted Multi-UAV Networks: Efficient Resource Allocation with Deep Reinforcement Learning,” 2021. citeturn32academia31 |
| Zhou et al. | H. Zhou et al., “Cooperative Hierarchical Deep Reinforcement Learning Based Joint Sleep and Power Control in RIS-Aided Energy-Efficient RAN,” 2023. citeturn32academia32 |
| Nauman et al. | A. Nauman et al., “Dynamic Resource Management in Integrated NOMA Terrestrial-Satellite Networks Using Multi-Agent Reinforcement Learning,” 2023. citeturn37academia19 |
| Yang et al. | K. Yang, C. Shen, J. Yang, S.-P. Yeh, and J. Sydir, “Offline Reinforcement Learning for Wireless Network Optimization with Mixture Datasets,” Asilomar, 2023. citeturn36view0 |
| Hester et al. | T. Hester et al., “Deep Q-Learning from Demonstrations,” 2017. citeturn34academia3 |
| Dong et al. | R. Dong et al., “Deep Learning for Radio Resource Allocation with Diverse Quality-of-Service Requirements in 5G,” 2020. citeturn35academia2 |
| Khairy et al. | S. Khairy et al., “Constrained Deep Reinforcement Learning for Energy Sustainable Multi-UAV Based Random Access IoT Networks with NOMA,” 2020. citeturn43academia3 |
| Gaurav et al. | A. Gaurav et al., “Learning Soft Constraints From Constrained Expert Demonstrations,” 2022. citeturn44academia1 |
| Lindner et al. | D. Lindner et al., “Learning Safety Constraints from Demonstrations with Unknown Rewards,” 2023. citeturn44academia2 |
| A-SILfD | C. Li, “Accelerating Self-Imitation Learning from Demonstrations via Policy Constraints and Q-Ensemble,” 2022. citeturn44academia3 |
| Wang et al., Catfish Agent | Y. Wang et al., “Silence is Not Consensus: Disrupting Agreement Bias in Multi-Agent LLMs via Catfish Agent for Clinical Decision Making,” 2025. citeturn25academia1 |
| Wang et al., MGAug | R. Wang et al., “Improving Generalization in Meta-Learning via Meta-Gradient Augmentation,” 2023; includes “catfish pruning.” citeturn25academia4 |
| Catfish-effect optimization lineage | Optimization literature uses catfish-effect mechanisms as population-diversification / premature-convergence countermeasures, not as RL replay-memory architecture. citeturn32search0turn32search2 |