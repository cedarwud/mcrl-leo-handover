# LEO／NGSO forward-link successor：批判性一手文獻審查

供 multi-catfish 研究團隊審閱｜2026-09-08｜附件 r5.1

## Executive assessment（300 字以內）

若保留「離軸角須直接影響 RF 發射功率與 EE」的設計目的，a-r 可作主模型，但須明稱為具有逐使用者時槽功率控制的合成 benchmark。文獻支持前向鏈路自適應功率、逐使用者 ACM 及速率約束最佳化；未證實附件的控制律、50 Mbit/s 或硬體常數是業者實況。其成立條件是資源／功率／干擾帳本一致、控制延遲與上限明確、失敗服務仍計實際能耗，並限定 EE 的載荷邊界。固定每波束 RF＋ACM 適合作主要參照；若不願承擔上述架構假設，應以它為主並明示放寬角度直接控制 RF 的要求。標準不替固定 SINR 與速率目標排優先序；不可依三組件的結果正負選模型。[DVB guidelines][guide]、[Zheng][zheng]、[SpaceX][spacex]、[Kuiper][kuiper]。

## 閱讀範圍、證據等級與附件校正

已按要求讀取附件 `multi-catfish-physics-successor-review-package-20260908-r5.1(1).zip` 中的 `00-README.md`，以及 01、03、05、05b、05d、11；另參照 05c、17、19、21 等釐清封存順序、時間與評估規格。這是文獻及文件審查：未執行 simulator、訓練、數值實驗或重算稽核結果。附件含 32 份 Markdown，未含其所引用的原始 simulator、TLE、checkpoint、完整 thesis 或 raw receipts。因此以下「附件載明」不代表獨立重現。

本報告以截至 2026-09-08 可核原始資料為界。**〔直接〕**表示來源明載；**〔推論〕**表示本審查的代數或架構推導；**〔benchmark〕**表示來源不足以決定本案取值；**〔未驗證〕**表示主張欠缺已取得的一手證據。「未查得」限於本次文件與檢索，不能當成所有未公開系統皆不存在的證明。監管申請是申請人的設計披露，廠商公告是其自述，均非獨立實測的現行 fleet 控制規則。

附件有四項關鍵校正，會直接改變文獻對照：

1. **舊規則凍結的是發射端增益乘積。**依 03、05 與稽核摘要，\(p_u(t)=0.825\,G_T(\tau)/G_T(t)\)，其中 \(\tau\) 為 association segment 起點；故保持 \(p_uG_T\)，不是含當下路徑損失、接收增益、fading、干擾的完整 received level 或 SINR。增益變好時功率亦可下降，不能說功率必然隨停留增加。標準支持性與「全部歷史增益由此造成」是兩個問題，後者未由本次文獻驗證。
2. **05d 是已宣告主模型的最新修訂。**其 primary 是 a-r，取代 05c 的固定 SINR a；05 的較早建議才是 b。50 Mbit/s 明列 synthetic、非校準需求。封存時間早於 successor outcomes 是附件的紀錄，本報告未核其外部 seal／server receipts。
3. **ACM profile 是 DVB-S2 的 28 modes，不是完整 DVB-S2X。**任何上限與 service floor 均須帶著這個限定。[DVB-S2 Table 13][s2]
4. **舊 C3-S 約 +2.9% 僅是附件的歷史結果。**其機制未歸因；不構成 successor 效能、三組件各自有效或硬體物理正確的證據。05 已修正早期敘述；不沿用「共同能耗底值必不改排名」或舊 BASE 已依新 Phi 訓練等被更正說法。

## 1. 前向鏈路功率控制：標準允許什麼，業者披露到哪裡

**結論：不能以「衛星 forward link 一律固定功率」否定 a；亦不能以 ACM 或 UE uplink TPC 直接證明 a。**標準、特定 payload 能力及研究控制律，必須分別成立。

### 1.1 標準的實際範圍

| 原始文件 | 明確支持的主張 | 不支持／不能推出的主張 |
|---|---|---|
| [DVB-S2 EN 302 307-1，2014，Introduction、Annex D.5][s2]；[2015 implementation guidelines §§4.1.2、6.1、7.1][guide] | 逐接收端品質回報、逐 frame ACM；雙向非廣播服務可使用 adaptive power；QoS 排程不由 S2 本身完整指定 | 逐 frame ACM 不等於 PA 逐 frame 可變 RF；不指定統一 \(\gamma^*\)、\(r^*\)、回授週期或 association-entry target |
| [DVB-S2X EN 302 307-2，2021，Annex E][s2x]；[TR 102 376-2，2021][s2xguide] | 更多模式與 beam-hopping signal formats；須考慮非線性、濾波、相位雜訊等實作因素 | 訊號格式不是任意每用戶功率配置的硬體保證；guideline 算例不是全系統規定 |
| [3GPP TS 38.213 Rel-18，§7][nrpower] | UE 的 PUSCH／PUCCH／SRS／PRACH **uplink** power control | 不能移植其 references／TPC accumulation 當 satellite user-downlink 規則 |
| [3GPP **TR** 38.821 Rel-16，§6.2.2][ntntr] | 可見的一手索引文字談 NTN uplink power control、beam 參數與 ephemeris | 它是 TR，非 TS；全文未成功取得，不能聲稱全篇或後續版本證明某 downlink law |
| [ITU-R Report S.2174，2010，Annex 1 §§3.1–3.2][alcreport] | satellite ALC 可在操作範圍內維持 **carrier output power**，抵抗 feeder 輸入變化；UPC 受 HPA 與延遲限制 | 這是較早 FSS 工程先例，非 LEO per-user 標準；fixed carrier 需映射後才等於 fixed beam |

〔未驗證〕在上述查核範圍，沒有標準把每位使用者的 forward-link 功率／增益參考設在 association 起點，並要求保持 \(p(t)G_T(t)=p(\tau)G_T(\tau)\)。這比宣稱「所有標準都沒有」更精確。可配置 setpoint、回授濾波或有記憶的實際控制器，也不等於附件的 entry anchor。**memoryless 是消除本案歷史依賴的建模決定，並非 NTN 一般標準要求。**

### 1.2 業者與可重組 payload：支持粒度不能混淆

| 一手披露 | 實際支持 | 仍未披露／不宜外推 |
|---|---|---|
| [SpaceX 2016 Attachment A §§A.3.1、A.6–A.7][spacex] | user downlink 隨 beam steering 增益及斜距調功率以控制地面 PFD；各發射鏈可接收 emission on/off 指令 | 非 beam 內每個 user 的固定 SINR／rate law；無數值 cadence、待機電力或 2026 實作確認 |
| [SpaceX 2022 Ofcom submission pp.1–2][spacex2022] | 為 EPFD 合規調低 carrier power／PSD | 不能由監管 PFD／EPFD 限值直接讀出本案 1.65 W RF port cap |
| [Kuiper 2019 Technical Appendix §I.A.2(a)、Annex A.3][kuiper] | regenerative modem、每 user link ACM；user downlink 調整 beam power 補償 scan／path loss，按披露的 PFD 目標運作 | 「continuously」未給數值週期；每用戶 ACM 不證明同時多工用戶各有獨立 PA；gateway 與 user link 控制律不同 |
| [OneWeb 2016 Attachment A §A.7 fn.17、Annex 2][oneweb] | 明載的 constant-PFD power control 是 **Ka-band gateway downlink** | 這條通常屬 user traffic 的 return path；不能當 Ku-band user forward-link per-user TPC 證據 |
| [MDA，JoeySat，2026-06-09][joeysat] | 廠商披露 LEO 在軌示範 beam steering／hopping，以及 coverage cells 之間即時重分配 bandwidth 與 power | 支持「可實現的 flexible payload」，不代表整個 OneWeb fleet 採相同控制律或已知更新頻率 |
| [Telesat，2025-01-31][telesat] | CNOS 按需求調度 antenna links、spectrum、routing／bandwidth | 本次所見公告未給 per-user TX target、RF/DC curve、功率更新週期或切換能量；均〔未驗證〕 |
| [ESA，Flexible Power Allocation 技術披露][esa] | multiport amplifier 網路可遠控 TWTA anode／collector voltages，重分配功率並調整效率 | logical beam 不必對應獨立 PA；未提供可移植的 flight efficiency curve、切換時間與功率池數值 |

這些證據反駁「前向只能固定 RF」的普遍命題，但不能把 constant PFD、constant EIRP、constant SINR 與 constant user rate 視為同一控制目標。尤其 **satellite beam scan angle、使用者相對 beam boresight 的離軸角、地面 elevation angle** 是不同幾何量；前兩個披露不能不經 antenna mapping 就互相替代。〔推論〕

### 1.3 什麼架構下 per-user power 有物理意義

| 架構 | 必須一致的物理與能耗帳本〔推論〕 | 文獻可提供的支持 |
|---|---|---|
| 每 user 獨立 carrier／FDMA／OFDMA 資源 | 明定各自 bandwidth、PSD 與 RF；干擾積分限於頻譜重疊；共享 HPA 受 aggregate RF、非線性與 crest factor 限制，不能任意相加獨立 PA 的 DC | S2／NR mode 與排程能力提供 signal-level 背景，不能代替 payload mapping |
| full-band TDM，一 slot 一 user | slot 中使用該 user 的 RF；同一 slot 波形決定 desired signal、他人 interference 和 PA draw；再按 airtime 積分 | [Zheng et al. 2012 §§II、III-A][zheng] 有每 beam 每 slot 一 user、最小 rate→SINR constraint 的直接研究先例；它是 GEO／理想 CSI 基礎，不是 LEO 業者校準 |
| beam hopping | illumination schedule、gateway／payload 同步及接收端 burst acquisition 必須成立；beam off 不自動等於供電 off | [Fraunhofer 技術說明][fraunhofer] 支持 transparent／regenerative scheduler 架構；[S2X Annex E][s2x] 支持相應訊號格式 |
| digital precoding／power pooling | user stream power 經 precoder 映射到 feed／element／amplifier constraints；beam sum-cap 未必足夠 | [Zheng 的 linear power constraints][zheng] 與 [ESA multiport 架構][esa] 支持此區別 |

因此 a-r 的 equal-airtime full-band TDM 是**可宣告的合成架構**。b 的固定 beam RF 則需固定 active carrier–beam mapping；它不等於對每位使用者固定 directional EIRP。兩者均須把 cap 視為限制，而非可達目標的保證；a-r 的 coupled interference solution、估測誤差／延遲、峰值與共享 payload 上限仍是 model assumptions。

〔推論〕角度較差通常提高 a 的所需 RF，但 cap 飽和後 RF 可保持不變、service 下降；不能要求每一點都嚴格 angle→RF 單調。固定 \(\gamma^*\) 在可行區內使目標 MODCOD 接近固定，主要幾何機制落在 energy；a-r 又讓 occupancy 透過所需 MODCOD 影響 RF。這是所選控制律的結果，文獻沒有因此判定 rate target 普遍優於 SINR target。

## 2. ACM、速率上限與最低 service floor

### 2.1 凍結 profile 可核，但應正確命名

[DVB-S2 Table 13][s2] 的輸入是 normal 64,800-bit FECFRAME、無 pilots、ideal AWGN、PER \(10^{-7}\) 的 \(E_s/N_0\) 與 bit/symbol。若附件的 \(W=(1+\alpha)R_s\)，其換算為：

\[
SE_m=\frac{e_m}{1+\alpha},\qquad
\gamma_{m,\mathrm{dB}}=g_m+M-10\log_{10}(1+\alpha).
\]

這是帶寬與能量定義的換算〔推論〕；把 interference 視為同帶寬等效 Gaussian noise 是額外 link abstraction。

| 模式 | 標準 \(e_m\)，bit/symbol | 標準 ideal \(g_m\)，dB | 附件導出 \(SE_m\)，bit/s/Hz | 附件導出 SINR，dB |
|---|---:|---:|---:|---:|
| QPSK 1/4 | 0.490243 | −2.35 | 0.408535833 | −1.441812460 |
| 8PSK 2/3 | 1.980636 | 6.62 | 1.650530000 | 7.528187540 |
| 32APSK 9/10 | 4.453027 | 16.05 | 3.710855833 | 16.958187540 |

右兩欄沿用附件 \(\alpha=0.20\)、\(M=1.7\) dB，**沒有在本審查重新選值**。表的可追溯性不等於 margin、mode target 或 PHY threshold 已獲實測校準。

**這不是全 S2X ceiling。**[S2X Table 20a][s2x] 已有 256APSK 3/4 的 5.900855 bit/symbol、ideal \(E_s/N_0=19.57\) dB；還容許較低 roll-off。其 normal-frame FER \(10^{-5}\) 與前述 S2 PER 條件不同。表內 nonlinear \(C_{\rm sat}/(N_0R_s)\) 欄也不是普通 received SINR，不可混入同一 threshold 向量。

**1.7 dB 的來歷有限。**[ITU-R BO.1784-1，Annex 1 Attachment 1][bo] 報告的是 2006 年七家設備測試：各 modulation 實作損失範圍不同，1.7 dB 是 32APSK 範圍上端。把它加到所有模式、用於本案 LEO receiver 是〔benchmark〕。該文件另述 nonlinear satellite tests，不能把 receiver loss 當成全部 PA distortion／back-off。[S2X guidelines Table 26][s2xguide] 中 1 dB margin 同樣只是算例假設，不構成另一個通用選值。

### 2.2 NR MCS 不能提供一個通用 NTN SINR floor

[TS 38.214 Rel-18 §5.1.3.1][nrmcs] 給 configured MCS tables：256QAM profile 可達 7.4063，而 1024QAM table 可達 9.2578。這些是表內 spectral efficiency；適用 NTN capability、layers、reference signals、控制／guard／重傳 overhead 須另定，不能直接當 net user rate。§5.2.2.1 的 CQI 依指定 TB error probability 選模式，不是所有 receiver 共用的 SINR→MCS 門檻表。故「NR NTN 統一最高 SE／最低 SINR」〔未驗證〕。

### 2.3 Capped Shannon、decodability 與 rate target

Shannon expression 是理想 rate model，沒有自帶 modem ceiling。作為研究先例，[Garcia-Cabeza et al. 的 Starlink direct-to-cell 作者稿 §III][dtc] 使用 \(\min\{sa\log_2(1+\mathrm{SINR}/b),m\}\)，分開 overhead、實作 fitting 與 cap；**正式同行評審狀態未核**，且研究 LTE direct-to-cell，不能把其係數移到 Ka-band DVB。相反，[Fastenbauer et al. 2025 式 (27)][fasten] 使用未 capped 的 Shannon rate：同行評審存在這種抽象，不代表它已驗證有限 MODCOD 的本案 profile。未查得能替本案確立通用 fitted-Shannon 係數的一手證據。較早 Mogensen 2007 基礎論文只核得書目，未核其全文係數。[作者機構紀錄][mogensen]

附件把最低模式 threshold 當 service floor 是清楚的 **hard-threshold abstraction**，但標準的理想 PER 測試點並不要求其下所有 packet 一律零 bits。又應分開：

| 量 | 本案應如何解讀〔推論／附件定義〕 |
|---|---|
| PHY decodability | 所選 ACM abstraction 能否解碼，不等於達到 rate target |
| rate-target attainment | 分配 airtime 後，實際 delivered rate 是否達 \(r^*\) |
| achieved bits | full-buffer 下實際 decodable bits；離散 MODCOD 超出目標的 bits 也被計入，故非 finite-demand served bits |

a-r 的 \(\Gamma_r(n)=\min\{\gamma_m:WSE_m/n\ge r^*\}\) 是附件設計反推。集合為空、cap 不足或 interference 耦合不可行時，標準不保證 target。05d 宣告仍以 cap 嘗試、保留 partial bits／interference／energy、不 pruning 或 repacking；這是可審核 benchmark policy，不是 DVB 規定。因而不同 occupancy 下 \(\Gamma_r\) 是階梯，RF 亦不必平滑。〔推論〕

## 3. Payload energy：可追溯的 component model 不等於 flight calibration

### 3.1 Amplifier back-off 與低負載

〔直接〕[Piacibello et al. 2022，§III、Figs.5–7][pa] 的 Ka-band GaN Doherty **實測設計**在飽和與 6 dB output back-off 有不同 PAE，並以 NPR 測試顯示調變訊號的線性度取捨。這支持「效率依元件、頻率、操作點及 waveform 而變」，不支持附件 \(\eta_{\max}=0.35\)、5 dB OBO 或平方根曲線。PAE 為 \((P_{out}-P_{in})/P_{DC}\)，不能未加說明便當整個 flight amplifier／payload 的 RF-to-supply efficiency。

附件採

\[
P_{\rm PA}(p)=\frac{\sqrt{pP_{\rm sat}}}{\eta_{\max}},\quad p>0;
\qquad P_{\rm PA}(0)=0.
\]

〔未驗證〕未取得匹配本案 TWTA 或 SSPA 的原始量測，證明這條曲線連同零功率極限適用。它可作理想化 benchmark，但不能冠以「實測衛星 PA model」。低 RF 時仍有 bias、供電與控制電路的可能耗能，不能由 RF muted 推出零 DC。[CPI 2025 地面 SSPA/BUC datasheet p.2][cpi] 明列 mute 35 VA 與 linear-output typical 420 VA；這是具體反例，**不是 flight standby calibration**。

本次未查得可移植的 flight-TWTA back-off 全曲線、inactive flight amplifier 待機 draw、wake-up transition energy／time 或通用固定耗能百分比。ESA 提供調壓與 power pooling 架構而非這些數值。[ESA 技術披露][esa]

### 3.2 每 RF chain、每 beam、每 satellite 是三種計數

[You et al. 2022，§II-C、Tables I–II][you] 支持 hybrid-array component accounting。附件的 \(0.338\) W 可追溯至 DAC 300、mixer 19、LPF 14、baseband amplifier 5 mW 的合計；另有 \(P_{BB}=200\) mW。原文還按架構計 RF chains、phase shifters、LO 等，並非量測一顆衛星的全部電子功耗；其場景為 2 GHz／20 MHz，PA efficiency 設為 0.5；component 數值借用既有模型（原文 ref.33，Méndez-Rial et al. 2016），並非 You 團隊對 LEO flight hardware 的原始量測。將 chain→beam、baseband term→每 active satellite，並在沒有服務時關閉該項，都是額外〔benchmark〕假設。

[Fastenbauer et al. 2025，§II-I 式 (28)][fasten] 將固定耗能持續保留；deactivated beam 的零 variable power 是模型假設，RF-chain sleep 被放入 fixed term。這提供 beam-hopping 節省**可變**功率的研究先例，不驗證「beam off，完整 payload draw 為零」。其效率／component 值亦是文獻模型，非 flight 測試。

### 3.3 EE 邊界及 handover／re-steering

〔推論〕本案若只計 PA、選定 RF-chain 與 baseband 項，endpoint 應稱「所建模 payload 範圍的 bits/J」。gateway、terminal、bus、thermal、供電轉換與未納入的處理能耗，不能被讀者理解為真實零值。load-independent fraction 由架構、啟用狀態、分母邊界及 duty cycle 決定；未查得通用比例。

固定共同能耗不直接影響功率差，卻仍可改變 ratio 的大小甚至策略排序，故不能宣稱 omitted bus floor 必定無害。這是分母的代數性質〔推論〕，不是要求在此選一個新 bus 值。

〔未驗證〕沒有查得本案 payload 每次 association／handover／re-steering 的 event joules。電子 steering、換 serving satellite、排程切換與 amplifier power-state transition 也不是同一事件。協定中斷時間只可能在明定 scheduler／power states 後轉成 bits 或能耗影響。[Seeram et al. 2025][seeram] 的 handover delay 是 RAN split 與流程模型；它不能校準 PA switching joules，也沒有驗證附件 62／142 ms 是通用成對常數。Phi／QoS penalty 不能改名為 joules。

## 4. EE estimand、Dinkelbach 與 RL reward 的一致性

### 4.1 Pooled ratio 必須保留自己的分母權重

[Shen–Yu 2018，§I、§II][fp] 區分 network EE 與 sum-of-ratios。對本案每個樣本的 bits \(B_j\)、energy \(E_j>0\)：

\[
\eta_{\rm pool}=\frac{\sum_jB_j}{\sum_jE_j}
=\sum_j\frac{E_j}{\sum_kE_k}\frac{B_j}{E_j}.
\]

右式〔推論〕顯示它是 **energy-weighted** ratio，不是 equal-weight mean-of-ratios。每 user、world、episode、policy seed 的平均比例各有不同 estimand。報告 per-world paired ratios 或 log-ratios 可作補充；其 CI 不能冒充 pooled ratio CI。跨 seed pooling 亦應說清楚：是算法隨機實例的 ratio-of-expectations，還是訓練後固定單一 policy 的表現。

### 4.2 Fixed reference price 是 surrogate，不是完整 Dinkelbach 最佳化

所謂 Dinkelbach「linearisation」對總 bits／energy 是仿射差值，不表示 action／channel 的非凸模型成為線性。Dinkelbach 方法反覆解 \(A(x)-qB(x)\) 並更新 \(q=A(x)/B(x)\)；1967 原始論文是較早基礎，本次只取得其出版者摘要，公式直接查核來自 [Shen–Yu §II.A.2 式 (5)–(6)][fp]。[Dinkelbach 原始書目][dinkelbach]

令比較政策 \(\eta_0=B_0/E_0\)，則本審查可精確推導：

\[
\eta-\eta_0=\frac{(B-B_0)-\eta_0(E-E_0)}{E},
\]

\[
\Delta B-q\Delta E
=E(\eta-\eta_0)+(\eta_0-q)\Delta E.
\]

因此只有 \(q=\eta_0\) 時，surplus 的**正負**與相對該 comparator 的 EE 改善等價；即使如此，surplus 的大小排序也不等於所有 candidate ratio 排序。附件從 disjoint calibration worlds 取得固定 \(\eta_{ref}\)，有助事先固定 surrogate，卻不令它等於每個 evaluation comparator 的比例。凍結 q、近似 Q、非凸／離散 action 與有限 horizon，不能繼承未滿足條件的全域最優保證。

同一未折扣帳本下，\(\sum_t(B_t-qE_t)=B_{total}-qE_{total}\)。折扣、clipping、隨 state 改變 normalization、逐步 ratio 或加 QoS penalty，都可能換了目標〔推論〕。[Jin et al. 2024][fractionalrl] 提供 sequential fractional RL 的方法先例，但研究的是 AoI；其 quotient 更新及 discount→1 的漸近條件，不證明本案任意固定 discount 與 pooled EE 等價。

### 4.3 Difference rewards、shared cost 與 QoS

| 做法 | 文獻支持的有限結論 | 不能宣稱 |
|---|---|---|
| \(D_i=G(a)-G(a_{-i},c_i)\) | baseline 不依賴當前 \(a_i\)、其他 actions 固定時，改善該 difference 對齊 unilateral immediate global reward；[Foerster et al. §3][coma] | \(\sum_iD_i=G\)，或 additive learned Q heads 必然正確排序所有 simultaneous joint moves |
| Difference-reward policy gradient | 在指定共享 reward／function approximation 條件下有 local convergence 分析；[Castellini et al. §3][drpg] | 有限資料 NN、另一種 Q argmax 或本案 pooled EE 的無條件全域保證 |
| Shared energy attribution | 權重和為 1 可讓會計總和一致〔推論〕 | 會計一致不等於邊際 incentive alignment；亦未查得衛星標準指定本案 focal shares |
| Wireless EE＋QoS＋DR | [Li et al. 2022 式 (15)、(20)–(22)、(27)][li] 是無線 association 的原始研究先例 | 它 scalarize EE 與 QoS、循序量 baseline，非本案 LEO 可免費取得同時刻 counterfactual 的證據 |
| QoS 作 constraints | [Achiam et al. 2017 §8.3][cpo] 顯示固定 penalty 與 expected-cost constraints 的差別 | 固定 penalty 不保證每 user／每時刻 QoS；\(\kappa\)、Phi 大小也不是物理能量常數 |

所以附件 C1 的 whole-network difference surplus 有理論動機，但「更易學」「各組件均改善部署 EE」仍是待評估的效能主張，不能由 reward 形式直接證明。以固定 target 可行時 bits 接近固定為由說 C1 完全無作用亦過強：其全網 energy、service／cap 與資源外部性仍可能不同。〔推論，不預測結果正負〕

## 5. RL 比較：哪些聲明與不確定性處理可辯護

### 5.1 沒有通用的最低 seed 數或 effect margin

[Agarwal et al. 2021，§§3–4.1、Fig.6][agarwal] 的實證支持對 training runs、protocol、uncertainty 保持警覺；不同 metrics 所需 runs 不同。它沒有制定所有 RL 研究一律 3、5、10 或任何數目的 seed 標準。附件的 seed／world 下限、0.5% 或 percentage-point effect margin、bootstrap 次數及 cluster 數，均應列 **no source — declare as benchmark／analysis-design choice**。本報告不選替代數字。

可辯護的數量取決於欲辨識的最小效果、training 與 environment variance、錯誤率及精確度。更多 worlds 只能增加固定已訓練 policy 的環境抽樣精度，不能代替 training-seed uncertainty；反之亦然。relative EE percent 與服務率 percentage points 不是同一尺度。若要主張實質改善，effect margin 的工程意義須事先說明，不能用既有結果大小反推。

### 5.2 World clusters × policy seeds：先說明泛化母體

[Owen–Eckles 2012，§§4、7][owen] 是 crossed／nested bootstrap 的較早方法基礎。其理論有 random-effects 條件，不提供本案 TLE 的自動分群法或 small-seed 保證。對本案的適用推論如下：

- 若要泛化到新 training seeds 與新 dates／worlds，應同時反映兩類隨機來源，不能把所有 seed×world cells 當 iid。arms 共用 worlds 時，重抽權重須維持配對；training seeds 是否配對則依真實訓練設計。
- 每次 uncertainty calculation 都應重新加總各 arm 的 bits 與 joules、再形成 ratio 與 contrast。僅 bootstrap per-world ratio 的平均，是另一 estimand。
- 同一 TLE date 是 shared deterministic input，**本身不是相關性已被證明**。推論有限固定 fixture distribution 與推論新日期母體不同；若相鄰日期仍相關，單日 clustering 也未必足夠。
- 〔未驗證〕本次未取得證據保證「相隔兩日即獨立」，或 3–5 seeds／少數日期 clusters 足以提供名目 CI coverage。附件的 166 dates、重複 worlds 等是稽核紀錄，未在本審查重算。

### 5.3 三組件改善：conditional effects、all-neutral 與 interactions

[NIST full-factorial 技術手冊][nist] 明列三個二元 factors 的完整設計有 \(2^3=8\) cells。這不表示每項有限聲明都需要完整 factorial；聲明範圍應對上可識別 contrasts。

| 已有／可定義的 contrast | 可支持的聲明〔設計推論〕 | 不可擴大成 |
|---|---|---|
| 111−011、111−101、111−110 | 其他兩組件 ON 時，各組件的 conditional simple effect | 所有背景組合下都有獨立正 main effect |
| 111−000 | 全部組件相對全部 neutral 的整體效果 | 對三個效果逐一歸因，或識別全部 interactions |
| 全部八個組合 | 估計 full factorial main／interaction contrasts，仍需足夠 uncertainty | 每個 effect 天然為正，或有限資料無誤差 |

所以缺少 000 不會使 FULL−DROP 的有限 conditional claim 自動無效；但沒有 all-neutral，就欠缺 full-vs-none 的直接比較。只增加 000 成為五格，仍非完整 factorial。neutral 也須是前瞻固定且可部署的行為，不是不同訓練資訊／搜尋預算造成的另一項未命名 treatment。

### 5.4 Multiplicity 與 sequential futility：兩個容易過度否定之處

**若唯一成功聲明是「三項全部超過各自預定 margin」**，可寫成
\(H_A:\Delta_1>\delta_1\land\Delta_2>\delta_2\land\Delta_3>\delta_3\)。這是 intersection–union 結構：每項用適當 level-\(\alpha\) 單側檢定、全部通過才成功，不需機械套 Bonferroni。若要逐項公布任何成功者、挑 settings／endpoints，或要求 simultaneous confidence intervals，則是不同 multiplicity 問題。[FDA 2022 §IV.C.1][fda_multi] 是此一般統計原理的官方例證，**不是 RL／衛星法規**。

**預先定義、只因 futility 停在「不成功」的 gate，不必然破壞 final type-I error。**[FDA 2019 §V.A][fda_adapt] 明確區分 nonbinding futility 與 efficacy stopping／adaptive designs。固定最終終點的有效檢定，加 futility 可仍有效；看中途結果改 architecture、加樣本直到過線、換 checkpoint／margin 則需相應方法。nested 3000⊂9000 永遠不是獨立 replication；survivor effect 的 selection、條件化區間及所有探索過的選擇仍須交代。

對本案可辯護的結論範本因此是：**在預定 successor physics、帳本、訓練程序與 QoS 條件下，另兩組件啟用時，三個 FULL−DROP pooled-EE contrasts 全部超過預定 margins，且不確定性涵蓋指定 world/date 與 training-seed 母體。**文獻不替 margins 或 seeds 選值，也不保證最後會滿足這個聲明。

附件 05d 保留原 18 cells 並增加 a-r0／a′-r0 成為 20 cells；這**不是**把 rate-target 主模型與所有 standby／handover／time treatments 完整交叉。舊 a-γ 下的 S/H/T robustness 不能移作 a-r 的證據。此為文件結構限制，非建議執行新實驗。

## 6. 時間基準、幾何積分、dwell 與 hysteresis

### 6.1 文獻的 cadence 是問題設定，不是一個「典型 LEO 常數」

| 一手研究 | 明載時間處理 | 可支持與不可外推 |
|---|---|---|
| [Fastenbauer et al. 2025 §§II-B、V-A.3][fasten] | 1 ms slots、10 ms beam-hopping frame；在 cycle 內做 resource accounting | 支持細粒度排程模型先例；不證明全網 association／PA feedback 同步此 cadence |
| [Seeram et al. 2025 Table 3][seeram] | handover 模擬用 1 s time steps | 該 RAN handover 研究設定，非 ACM integration 精度規範 |
| [Lee et al. 2020 §§II-A、IV][lee] | 將 LEO／UAV 幾何離散為短 interval，研究用 10 s steps | 支持 snapshot／分段近似的研究先例；不校準本案 30.08 s |
| [Kassing et al. 2020，Hypatia §§3.1、5.3][hypatia] | forwarding 更新通常 100 ms，packet latency 幾何在其間連續評估；比較不同更新間隔 | 證明 network-state clock 與 geometry clock 可分開；不是 RF／ACM 誤差界 |
| [Liang et al. 2021 §§5.1–5.2][ndn] | 大型 constellation topology 使用分鐘 snapshots，另分析局部 handover 行為 | 適用 topology 問題；不能支持長 snapshot 已足夠積分 payload energy |

這些尺度差別主要反映 PHY 排程、handover、routing 等不同問題，不能把它們平均成一個推薦 \(\Delta t\)。本次未查得一手依據證明附件 30.08 s decision interval 或 47×0.640 s trapezoids 已足夠精確。

### 6.2 Rate／energy 積分與控制更新必須分開

以 TDM 為例，物理帳本的連續時間定義可寫為〔推論〕：

\[
B_u[t,t+\Delta t]=\int_t^{t+\Delta t}f_u(\tau)W\,SE(\gamma_u(\tau))\,d\tau,
\qquad E[t,t+\Delta t]=\int_t^{t+\Delta t}P_{DC}(\tau)\,d\tau.
\]

Snapshot×\(\Delta t\) 是 quadrature approximation；共同 \(\Delta t\) 在 ratio 的代數約分，不會消除幾何／ACM crossing 誤差，也不會消除 changing decision cadence 的行為影響。MODCOD 階梯、cap、handover、visibility／outage 等可不連續，所以「多幾何節點」與「事件被正確處理」是不同要求。

附件 47 個梯形小區間意味著含兩端的 48 個邊界節點；但仍須區別：**association decision clock、scheduler slot、power／ACM update clock、CSI feedback age、geometry quadrature step**。每 0.640 s 重算功率若代表新控制命令，就改變了控制器；若只是評估已宣告的連續追蹤 law，就應明載該 law 的頻寬／資訊假設。文獻沒有替兩種解讀選邊，亦不能以「memoryless」隱含零延遲／完美 CSI。[DVB guideline 的回授延遲討論][guide]

### 6.3 D2、TTT 與 candidate refresh 不是 dwell 的同義詞

[TS 38.331 Rel-19 V19.2.0（2026），§5.5.4.15a][rrc] 的 D2 entering condition 同時涉及 serving moving reference location 的距離條件與 candidate moving reference location 的距離條件，並含 hysteresis；退出條件也有明定。其 reference 是依 ephemeris 建立的移動地面參考位置，不能直接偷換為 UE–satellite slant range。

該文件 TimeToTrigger IE 包含 1280 ms 這個可配置選項，**不要求所有 NTN 使用它**。因此附件 candidate-only slant-distance gate 應稱 D2-derived；1100 km、50 km、1.280 s 或 10° visibility 的本案組合未獲標準背書。N=4 每 120.32 s 固定 candidate IDs 只限制 candidate refresh；若 association 每 30.08 s 可改，它不是 120.32 s minimum dwell。TTT、hysteresis、minimum residence 與 handover blackout 必須各自定義。〔附件比對推論〕

## 7. 已宣告 successor 常數：最強來源與不可外推之處

以下數字僅轉錄附件或列出其已宣告導出關係。**「no source — declare as benchmark」表示沒有可決定本案該取值／映射的一手證據，不表示數學算式有錯或絕無其他文獻。**

| 常數／規則 | 附件宣告 | 最強可核來源 | 審查判定 |
|---|---|---|---|
| \(\gamma^*\)，a-γ | 8PSK 2/3；7.528187540 dB／5.660030272 linear | [S2 Table 13][s2] 支持原始 mode 點；[BO.1784][bo] 只提供有限 margin 來歷 | 換算可追溯；選這個控制 target：**no source — declare as benchmark** |
| \(r^*\)，a-r | 50,000,000 bit/s | [Zheng 2012][zheng] 支持 rate-constrained power optimization 的架構先例，不支持此值 | **no source — declare as benchmark**；05d 已明稱 synthetic |
| \(P_b\)／slot cap | 1.65 W；FDM sub-cap 1.65／\(n_b\) W | operator filings 支持限制與 adaptive RF，不提供本案 port mapping | **no source — declare as benchmark**；39×1.65≤100 W 只證明某 aggregate inequality，不能導出 1.65 W |
| \(W\)、\(\alpha\) | 500／3 MHz、0.20 | [S2][s2] 允許此 roll-off option | option 可用不等於必選；本案 bandwidth 與 roll-off 選擇是 benchmark |
| \(SE_{max}\) | 3.710855833 bit/s/Hz | [S2 Table 13][s2] 的 4.453027／1.20 | selected S2 profile 的導出 ceiling；非 S2X／NR／NTN 通用上限 |
| implementation margin | 1.7 dB，所有模式共用 | [BO.1784-1 Attachment 1][bo] 的歷史 32APSK 實作損失上端 | 數字來歷有源；跨 modes／LEO 共用：**no source — declare as benchmark** |
| \(SINR_{min}\) | −1.441812460 dB／0.7174947935 linear | [S2 QPSK 1/4][s2] 加附件 margin／bandwidth conversion | profile threshold 可追溯；hard service floor 及其實際 decoding 保證未校準 |
| OBO／\(P_{sat}\) | 5 dB；\(1.65\,10^{5/10}=5.217758139\) W | [Piacibello 2022][pa] 支持 back-off 需匹配元件，不支持此值 | **no source — declare as benchmark**；OBO 已在 saturation 映射中，勿再重複扣 RF |
| \(\eta_{max}\)／PA curve | 0.35；平方根 DC law；cap 時 DC 約 8.383317219 W | 無匹配 flight curve；[You][you] 使用另一種 constant-efficiency model | **no source — declare as benchmark**；不是 TWTA／SSPA 通用量測律 |
| standby，primary | inactive PA 0 W | [Fastenbauer][fasten] 的零 variable term 含另一 fixed term | **no source — declare as benchmark**；不能說真實休眠功率為零 |
| standby，sensitivity | \((35/420)\times8.383317219\approx0.698609768\) W／chain | [CPI 2025 p.2][cpi] 的 ground-unit 35 VA／420 VA | datasheet ratio 真實；跨 ground→flight 與縮放：**no source — declare as benchmark** |
| beam circuit | 0.338 W／active beam | [You Table II][you] 的四個 RF-chain components 合計 | 數值先例存在；one chain per beam／完整 beam circuit 的映射未驗證 |
| baseband | 0.200 W／active satellite | [You Table II][you] 的 modeled BB term | 非 satellite 全部 baseband／electronics 實測；activation 邏輯是 benchmark |
| bus／load-independent fraction | primary 排除 bus；未提供通用固定比例 | [Fastenbauer fixed-term accounting][fasten] | 排除範圍必須揭露；**no source — declare as benchmark**，不得讀成 physical zero |
| handover／re-steering event energy | 0 J | 未取得適用原始量測 | **no source — declare as benchmark**；不能用 reward penalty 替代 |
| handover blackout | primary 0；敏感度 62／142 ms | [Seeram][seeram] 僅支持架構相關的 protocol-delay model | 本案成對數字及缺席 ADR004 的原始依據〔未驗證〕；**no source — declare as benchmark** |
| \(\Delta t\)／quadrature | 30.08 s＝47×0.640 s | Q6 所列 papers 僅提供不同任務的時間離散先例 | **no source — declare as benchmark**；無已核誤差界或標準指定 |
| refresh／D2-derived gates | N=4；10°；1100 km；50 km；TTT 1.280 s；altitude floor 300 km | [38.331 Rel-19][rrc] 支持 D2 結構及 1280 ms option | 本案距離定義／組合未獲規範背書；candidate refresh 非 dwell |
| fixed EE price／QoS shaping | calibration \(\eta_{ref}\)、\(\kappa\)、Phi | [Shen–Yu][fp]、[CPO][cpo] 支持方法區別 | 固定 surrogate 可宣告；其值／最優性：**no source — declare as benchmark** |
| seeds／effect／gates | 05、19、21 中各自的數量及門檻 | [Agarwal][agarwal]、[Owen–Eckles][owen]、[FDA][fda_adapt] | 無通用最小數字；屬 analysis-design choices，不由文獻替團隊選定 |

## 8. 註解參考文獻與取用限制

每筆註解明列它在本報告可支持或限制的主張；不把尚未取得的原證明、作者稿的同行評審狀態或申請書的部署狀態補成已驗證事實。下列出版年早於 2015 者均明標為較早基礎。

1. **ETSI（2014-11）**，*EN 302 307-1 V1.4.1: DVB-S2*。[官方全文][s2]。較早、但正是附件所選 profile 的基礎。§6 Table 13 支持三個原始 MODCOD 點；不支持本案通用 margin／SINR floor。正文表格文字已核。
2. **DVB（2015-03）**，*BlueBook A171-1, Implementation Guidelines … Part I: DVB-S2*。[官方全文][guide]。§§4.1.2、6.1、7.1 支持 adaptive-power 方向、user ACM 與回授延遲；不規定本案 law／cadence。採 PDF 封面日期。
3. **ETSI（2021-07）**，*EN 302 307-2 V1.3.1: DVB-S2X*。[官方全文][s2x]。§§5.6、6、Annex E 支持擴展 modes／roll-off／BH formats；反駁 selected S2 ceiling 等於完整 S2X ceiling。
4. **ETSI（2021-01）**，*TR 102 376-2 V1.2.1, S2X Implementation Guidelines*。[官方全文][s2xguide]。§§5.2.3.1、6.2 支持實作 impairment／mode-granularity 討論；Table 26 的 margin 是算例，非通用規定。
5. **ITU-R（2016-12）**，*Recommendation BO.1784-1, Digital Satellite Broadcasting System with Flexible Configuration*。[官方全文][bo]。Annex 1 Attachment 1 記載 2006 接收器與非線性測試；限制 1.7 dB 外推。該頁已作表格視覺核對。
6. **3GPP／ETSI（2024-10）**，*TS 38.213 V18.4.0, NR Physical Layer Procedures for Control*。[官方全文][nrpower]。§7 支持 UE uplink power control；不能引用為本案 satellite downlink 規則。
7. **3GPP／ATIS（2019-12）**，*TR 38.821 V16.0.0, Solutions for NR to Support NTN*。[原始文件入口][ntntr]。只核得 primary indexed text 的 §6.2.2 uplink 範圍；完整下載失敗，較後 V16.2.0 亦未取得正文。其餘細節保持未驗證。
8. **3GPP／ETSI（2024-10）**，*TS 38.214 V18.4.0, NR Physical Layer Procedures for Data*。[官方全文][nrmcs]。§§5.1.3.1、5.2.2.1 支持 MCS／CQI tables；不提供通用 NTN SINR thresholds 或 net-rate ceiling。
9. **ITU-R（2010）**，*Report S.2174: Guidelines That May Be Used in the Design of Satellite Networks for Assessing the Impact of Rain Attenuation on the Carrier to Noise Plus Interference Ratios of the FSS Plan Allotments*。[官方全文][alcreport]。較早 FSS 工程基礎；Annex 1 §§3.1–3.2 支持 UPC／carrier ALC 區別，不是 LEO per-user 標準。
10. **SpaceX（2016；2018 政府網站收錄副本）**，*Non-Geostationary Satellite System, Attachment A*。[原始申請附件][spacex]。§§A.3.1、A.6–A.7 支持 scan/path/PFD 調功率及 emission control；未驗證現行 fleet 的每用戶 law。
11. **SpaceX（2022-09-21）**，*Additional Information Regarding the Application for Six NGSO Earth Station (Gateway) Licences*（無獨立標題的覆函，按內容描述）。[Ofcom 收錄原件][spacex2022]。pp.1–2 支持 EPFD 所需 carrier power／PSD reduction；未給本案 RF cap。
12. **Kuiper Systems（2019-07-04）**，*Technical Appendix, SAT-LOA-20190704-00057*。[原始 PDF 鏡像][kuiper]。§I.A.2(a)、Annex A.3 支持 regenerative／per-user ACM 與 beam PFD 控制；來源是申請人原文，透過 FCC.report 讀取，不是 FCC 現況認證。
13. **WorldVu／OneWeb（2016-04-28）**，*Attachment A, SAT-LOI-20160428-00041*。[原始 PDF 鏡像][oneweb]。§A.7 fn.17、Annex 2 的功控證據是 Ka gateway downlink；限制其向 Ku user forward link 的外推。
14. **MDA Space（2026-06-09）**，*JoeySat: Successful Mission Showcases the Evolution of Reconfigurable Satellite Networks*。[廠商在軌示範披露][joeysat]。支持 cell 間 bandwidth／power 動態分配能力；未提供 law、cadence 或完整 fleet 覆蓋的證據。
15. **Glenn Katz／Telesat（2025-01-31）**，*Accelerating Innovation in Space: Telesat Lightspeed and the Trends Shaping 2025*。[業者原文][telesat]。支持 CNOS 資源排程敘述；不足以支持 per-user RF target 與能耗參數。
16. **ESA（頁面未標出版日期）**，*Multi-Beam Satellite Communications Payload with Flexible Power Allocation*。[技術披露][esa]。支持 multiport／TWTA 調壓架構；無本案 efficiency／transition 常數。
17. **Fraunhofer IIS（頁面未標出版日期）**，*Beam Hopping*。[開發機構技術頁][fraunhofer]。支持照射排程、同步及 burst receiver 要求；不提供 PA 關電節能量或 wake-up 時間。
18. **G. Zheng、S. Chatzinotas、B. Ottersten（2012）**，*Generic Optimization of Linear Precoding in Multibeam Satellite Systems*, IEEE TWC 11(6), 2308–2320；DOI 10.1109/TWC.2012.040412.111629。[作者全文][zheng]。較早 GEO 理論基礎；§III-A 式 (12)–(15) 支持 individual rate constraints→SINR 與 linear power caps，不是 LEO 50 Mbit/s 校準。
19. **L. You et al.（2022）**，*Hybrid Analog/Digital Precoding for Downlink Massive MIMO LEO Satellite Communications*, IEEE TWC 21(8), 5962–5976。[作者全文][you]。§II-C、Tables I–II 支持 RF-chain component 數值來歷；不支持完整 per-beam／satellite mapping 或附件 PA 曲線。
20. **CPI（2025-04，Rev.3）**，*GaNLink 80 W Ka-Band SSPA/BUC, MKT-497, SA49KOA/SB49KOA*。[廠商 datasheet][cpi]。p.2 支持 ground-unit 35／420 VA；不支持跨尺寸 flight standby ratio。
21. **A. Piacibello et al.（2022）**，*A 5-W GaN Doherty Amplifier for Ka-Band Satellite Downlink With 4-GHz Bandwidth and 17-dB NPR*, IEEE MWCL 32(8), 964–967；DOI 10.1109/LMWC.2022.3160227。[作者機構原稿][pa]。§III、Figs.5–7 是元件量測一手證據；不能移作本案 flight DC curve。研究 lane 取得正文，主協調者重取該 URL 遭 403。
22. **A. Fastenbauer et al.（2025）**，*LEO Satellite Beam Hopping for Power Consumption Minimization at Different Elevation Angles*, IEEE OJCOMS 6, 6930–6952；DOI 10.1109/OJCOMS.2025.3602090。[機構收錄出版全文][fasten]。式 (27)–(28) 與 §V 支持 slot／fixed-variable energy 的明示模型；不是 flight 測量或 ACM ceiling 校準。
23. **K. Shen、W. Yu（2018）**，*Fractional Programming for Communication Systems—Part I: Power Control and Beamforming*, IEEE TSP 66(10), 2616–2630。[作者全文][fp]。§II 支持 quotient transformation 與迭代更新；不支持任意 fixed price 的完整 ratio 排序等價。
24. **W. Dinkelbach（1967）**，*On Nonlinear Fractional Programming*, Management Science 13(7), 492–498；DOI 10.1287/mnsc.13.7.492。[出版者摘要][dinkelbach]。較早方法基礎；僅核摘要／書目，原證明未取得，公式核對依上筆。
25. **J. Foerster et al.（2018）**，*Counterfactual Multi-Agent Policy Gradients*, AAAI, 2974–2982。[Oxford 作者全文][coma]。§3 支持有條件的 counterfactual credit assignment；非 additive-Q joint ranking 保證。
26. **J. Castellini et al.（2022-11-11 online；2025 卷期）**，*Difference Rewards Policy Gradients*, Neural Computing and Applications 37, 13163–13186；DOI 10.1007/s00521-022-07960-5。[出版者全文][drpg]。§3 支持指定條件下 policy-gradient 結果；不支持本案任意 NN／Q 的全域最優性。
27. **X. Li、T. N. Guo、A. B. MacKenzie（2022）**，*Multi-Agent Reinforcement Learning With Measured Difference Reward for Multi-Association in Ultra-Dense mmWave Network*, IEEE Access 10, 118747–118758。[DOI 原始出版紀錄][li]。global EE、QoS scalarization、DR 的直接無線先例；IEEE PDF 未取得，本次讀取作者分享的完整原論文副本，未把頁末其他文章當其內容。[實際全文入口][li_copy]
28. **L. Jin、M. Tang、M. Zhang、H. Wang（2024）**，*Fractional Deep Reinforcement Learning for Age-Minimal Mobile Edge Computing*, AAAI 38(11), 12947–12955。[出版者][fractionalrl]／[已讀作者全文][fractionalrl_full]。式 (7)–(10) 支持 sequential fractional objective 與 asymptotic discount 條件；屬 AoI 方法先例。
29. **J. Achiam et al.（2017）**，*Constrained Policy Optimization*, ICML, PMLR 70, 22–31。[出版者與全文][cpo]。§8.3 支持 constraints 與固定 penalties 的區別；不選定 NTN QoS 門檻。
30. **R. Agarwal et al.（2021）**，*Deep Reinforcement Learning at the Edge of the Statistical Precipice*, NeurIPS。[會議全文][agarwal]。支持 training-run uncertainty／protocol 敏感性；不制定 universal seed minimum，也不要求改用 IQM 取代本案 pooled EE。
31. **A. B. Owen、D. Eckles（2012）**，*Bootstrapping Data Arrays of Arbitrary Order*, Annals of Applied Statistics 6(3), 895–927；DOI 10.1214/12-AOAS547。[正式論文再印本][owen]。較早 crossed-factor 方法基礎；條件式支持 multi-factor resampling，非 TLE clustering 或少 seed coverage 保證。
32. **NIST／SEMATECH（頁面未列明日期）**，*e-Handbook of Statistical Methods, §5.3.3.3.1: Two-Level Full Factorial Designs*。[官方技術頁][nist]。支持八格與 interactions 的設計定義；不保證效果大小。
33. **FDA（2022-10）**，*Multiple Endpoints in Clinical Trials: Guidance for Industry*。[官方全文][fda_multi]。§IV.C.1 支持 all-required co-primary／IUT 的 multiplicity 區別；只是跨領域統計先例，非本案適用法規。
34. **FDA（2019-11）**，*Adaptive Designs for Clinical Trials of Drugs and Biologics*。[官方全文][fda_adapt]。§V.A 支持 nonbinding futility 與 efficacy stopping 的區別；不背書任意 outcome-driven ladder。
35. **3GPP／ETSI（2026-04）**，*TS 38.331 V19.2.0, NR Radio Resource Control Protocol Specification*。[官方全文][rrc]。§5.5.4.15a／TimeToTrigger IE 支持 D2 與 TTT option；不支持 candidate-only slant gate 等同完整 D2。
36. **S. S. S. G. Seeram、L. Feltrin、M. Ozger、S. Zhang、C. Cavdar（2025）**，*Handover Challenges in Disaggregated Open RAN for LEO Satellites: Tradeoff Between Handover Delay and Onboard Processing*, Frontiers in Space Technologies；DOI 10.3389/frspt.2025.1580005。[出版者全文][seeram]。Table 3、§6 支持情境化時間／handover delay；不校準 payload joules。2026 corrigendum 修正 funding，非本報告引用的技術模型。
37. **J.-H. Lee、J. Park、M. Bennis、Y.-C. Ko（2020）**，*Integrating LEO Satellite and UAV Relaying via Reinforcement Learning for Non-Terrestrial Networks*, IEEE GLOBECOM；DOI 10.1109/GLOBECOM42002.2020.9348105。[作者全文][lee]。§§II-A、IV 支持該研究的分段幾何與 10 s 設定；非本案 cadence／accuracy 標準。
38. **S. Kassing et al.（2020）**，*Exploring the “Internet from Space” with Hypatia*, ACM IMC；DOI 10.1145/3419394.3423635。[原論文全文副本][hypatia]。§§3.1、5.3 支持 forwarding／geometry clocks 區別；不給 RF integration 誤差界。
39. **T. Liang et al.（2021）**，*NDN in Large LEO Satellite Constellations: A Case of Consumer Mobility Support*；DOI 10.1145/3460417.3482970。[NDN 項目收錄原文][ndn]。§5 支持大型網路 topology snapshots 的時間抽象；不支持直接挪用至 PA／ACM。
40. **J. Garcia-Cabeza et al.（2025 作者稿；已讀 v6）**，*Direct-to-Cell: A First Look into Starlink’s Direct Satellite-to-Device Radio Access Network through Crowdsourced Measurements*。[作者全文][dtc]。補充的一手研究稿，**peer-review status unverified**；§III 支持 capped modified-Shannon 形式的使用，不支持本案係數。
41. **P. Mogensen et al.（2007）**，*LTE Capacity Compared to the Shannon Bound*, IEEE VTC Spring, 1234–1238；DOI 10.1109/VETECS.2007.260。[機構書目][mogensen]。較早 LTE 基礎；僅核出版資訊，未讀原始全文，因此沒有用它替任何 fitting constant 背書。

**未解缺口與停止理由。**標準／業者原文已足以界定可成立的架構與反駁過強命題；其餘關鍵缺口為未公開、存取受限，或沒有匹配本案硬體／統計母體的數值證據。繼續堆疊同類公告不能把 benchmark 變成校準參數。本文未宣稱標準版本全集、全部業者內部控制器或所有 flight PA 已被窮盡；TR 38.821、Dinkelbach、Mogensen 的有限取用尤其保留標記。報告交付為 Markdown，已核對結構、表格與引用；未作分頁版面視覺驗證。

[s2]: https://www.etsi.org/deliver/etsi_en/302300_302399/30230701/01.04.01_60/en_30230701v010401p.pdf
[guide]: https://dvb.org/wp-content/uploads/2019/12/a171-1_s2_guide.pdf
[s2x]: https://www.etsi.org/deliver/etsi_en/302300_302399/30230702/01.03.01_60/en_30230702v010301p.pdf
[s2xguide]: https://www.etsi.org/deliver/etsi_tr/102300_102399/10237602/01.02.01_60/tr_10237602v010201p.pdf
[bo]: https://www.itu.int/dms_pubrec/itu-r/rec/bo/R-REC-BO.1784-1-201612-I!!PDF-E.pdf
[nrpower]: https://www.etsi.org/deliver/etsi_ts/138200_138299/138213/18.04.00_60/ts_138213v180400p.pdf
[ntntr]: https://atisorg.s3.amazonaws.com/archive/3gpp-documents/Rel16/ATIS.3GPP.38.821.V1600.pdf
[nrmcs]: https://www.etsi.org/deliver/etsi_ts/138200_138299/138214/18.04.00_60/ts_138214v180400p.pdf
[alcreport]: https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-S.2174-2010-PDF-E.pdf
[spacex]: https://www.rsm.govt.nz/assets/Uploads/documents/consultations/2018-preparing-for-5g/c4c9f26604/300.3-spacex-submission-preparing-for-5g.pdf
[spacex2022]: https://www.ofcom.org.uk/siteassets/resources/documents/consultations/category-3-4-weeks/238993-starlink-ngso-application/associated-documents/secondary-documents/spacex.pdf
[kuiper]: https://fcc.report/IBFS/SAT-LOA-20190704-00057/1773885.pdf?raw=1
[oneweb]: https://fcc.report/IBFS/SAT-LOI-20160428-00041/1134939.pdf?raw=1
[joeysat]: https://mda.space/insights/joeysat-successful-mission-showcases-the-evolution-of-reconfigurable-satellite-networks
[telesat]: https://www.telesat.com/blog/accelerating-innovation-in-space-telesat-lightspeed-and-the-trends-shaping-2025/
[esa]: https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Multi-Beam_Satellite_Communications_Payload_with_Flexible_Power_Allocation
[fraunhofer]: https://www.iis.fraunhofer.de/en/ff/kom/satkom/hts/beam-hopping.html
[zheng]: https://arxiv.org/pdf/1109.0681
[you]: https://arxiv.org/pdf/2201.06281
[cpi]: https://www.cpii.com/docs/datasheets/826/MKT-497%20SA49KOA_SB49KOA%2080%20W%20SSPA_SSPB.pdf
[pa]: https://iris.polito.it/retrieve/handle/11583/2961521/e384c434-6bf8-d4b2-e053-9f05fe0a1d67/Gandalf_letter_lizard_subm2_nocb.pdf
[fasten]: https://repositum.tuwien.at/bitstream/20.500.12708/219246/1/Fastenbauer-2025-IEEE%20Open%20Journal%20of%20the%20Communications%20Society-vor.pdf
[fp]: https://arxiv.org/pdf/1802.10192
[dinkelbach]: https://pubsonline.informs.org/doi/abs/10.1287/mnsc.13.7.492?journalCode=mnsc
[coma]: https://www.cs.ox.ac.uk/people/shimon.whiteson/pubs/foersteraaai18.pdf
[drpg]: https://link.springer.com/article/10.1007/s00521-022-07960-5
[li]: https://doi.org/10.1109/ACCESS.2022.3221455
[li_copy]: https://www.researchgate.net/publication/365308135_Multi-agent_Reinforcement_Learning_With_Measured_Difference_Reward_for_Multi-Association_in_Ultra-Dense_mmWave_Network
[fractionalrl]: https://ojs.aaai.org/index.php/AAAI/article/view/29192
[fractionalrl_full]: https://arxiv.org/html/2312.10418v2
[cpo]: https://proceedings.mlr.press/v70/achiam17a.html
[agarwal]: https://proceedings.neurips.cc/paper/2021/file/f514cec81cb148559cf475e7426eed5e-Paper.pdf
[owen]: https://arxiv.org/pdf/1106.2125
[nist]: https://www.itl.nist.gov/div898/handbook/pri/section3/pri3331.htm
[fda_multi]: https://www.fda.gov/media/162416/download
[fda_adapt]: https://www.fda.gov/media/78495/download
[rrc]: https://www.etsi.org/deliver/etsi_ts/138300_138399/138331/19.02.00_60/ts_138331v190200p.pdf
[seeram]: https://www.frontiersin.org/journals/space-technologies/articles/10.3389/frspt.2025.1580005/full
[lee]: https://arxiv.org/pdf/2005.12521
[hypatia]: https://bdebopam.github.io/papers/imc2020-hypatia.pdf
[ndn]: https://named-data.net/wp-content/uploads/2022/03/3460417.3482970.pdf
[dtc]: https://arxiv.org/html/2506.00283v6
[mogensen]: https://vbn.aau.dk/en/publications/lte-capacity-compared-to-the-shannon-bound/
