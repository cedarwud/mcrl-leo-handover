# MERGE-PLAN：V0.23 中文論文稿 → V0.25 物理繼任者（逐段併入計畫）

- **基準（唯讀）：** `artifacts/chinese-word-v023-lcsrs-20260905-r2/mcrl-thesis-ZH-v023-method-draft-20260905.docx`
  抽取文字見同目錄 `THESIS-EXTRACTED.txt`（416 段，含 OMML 數學）。
- **替換文字：** 每一列的「區塊」欄指向 `MERGED-SECTIONS-ZH.md` 中同編號的成稿段落。
- **來源：** `.scratch/multi-catfish-v023-controller-handoff-20260907/paper-lane-20260909/`
  之 `DELTA-MAP.md`、`SEC-SYSTEM-MODEL-REWRITE.md`、`SEC-METHOD-REWRITE.md`、
  `TAB-I-model-assumptions.md`、`TAB-II-comparator-contract.md`、
  `SYMBOL-ADDITIONS.md`、`DEVIATION-REGISTER-DELTA.md`、`LIMITATIONS-REGISTER.md`。
- **處置代碼：** `REPLACE`（整段／整節置換）、`INSERT`（新增，不刪原文）、
  `DELETE`（自繼任稿移除）。
- **結果數字紀律：** 凡原稿陳述 V0.23 數值者，一律標為 `⟨結果待填｜需重新推導⟩`，
  不以任何新數字替換。矩陣尚未執行，本計畫不含任何能量效率宣稱。

---

## A. 摘要與關鍵字

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| A1 | 摘要 | 「低軌衛星（LEO）網路覆蓋廣、延遲較低，但衛星高速移動使波束覆蓋快速變化」 | REPLACE | 首段把方法定義在「三個獨立 Q surface 無權重相加、一次 row-wise argmax」上；Δ5 已改為兩層（逐使用者提案＋集合層），且須加入 ACM 階梯與速率目標功率控制。 | M-A1 |
| A2 | 摘要 | 「第一路 C1 使用 focal current-slot own-rate 與完整 opening-step marginal」 | REPLACE | 三路角色全數改寫：C1＝整網單邊增量和 $D(a)$、C2＝續值預測、C3＝集合層交互作用殘差 $\Psi_{\mathcal K}$；LC-SRS 與 $z_{3,i}=e_i+\Psi/2$ 退場（Δ4）。 | M-A2 |
| A3 | 摘要 | 「這是與 current method 對齊的研究草稿，不是 empirical-final。」 | REPLACE | 宣稱結構升級為預先指定的階梯與收容三分法（Δ8）；並須加入 QoS 共同主要結果與目標落差註記。 | M-A3 |
| A4 | 摘要（關鍵字列） | 「關鍵字：低軌衛星、多波束網路、換手決策、網路比值總和能量效率」 | REPLACE | 刪 `LC-SRS`、`預決策關係描述元`；補 `速率目標功率控制`、`調適性調變編碼`、`集合層聯合再評估`、`交互作用殘差`。 | M-A4 |

## B. 第一章 Introduction

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| B1 | 1. Introduction | 「近年來行動通訊朝第六代行動通訊與非地面網路發展。」 | KEEP | 背景陳述不依賴被改的物理。 | — |
| B2 | 1. Introduction | 「因此，本文以 MODQN 的候選與遮罩介面為背景，提出與 Main-only network」 | REPLACE | 「訓練教師與部署學生」的資訊邊界已換成「逐使用者提案頭與集合層協調器」的資訊介面（Δ5）。 | M-B2 |
| B3 | 1. Introduction（貢獻條列 1） | 「將 Main-only 的網路 ratio-of-sums EE 定為唯一最終目標，並保留第三章的角度」 | REPLACE | 直接與 Δ1 衝突：繼任者沒有 segment、沒有 $p^{0}$、沒有遞推。 | M-B3 |
| B4 | 1. Introduction（貢獻條列 2） | 「明確劃分恰好三個獨立 Q surface 的 route roles：C1 的 own-rate／network-energy」 | REPLACE | 三條路線仍在，但角色已改為 $D(a)$／續值／$\Psi_{\mathcal K}$。 | M-B4 |
| B5 | 1. Introduction（貢獻條列 3） | 「定義 C3 的 training-only four-profile teacher、deterministic relational C3View」 | REPLACE | four-profile teacher／C3View／single-pass argmax 三個名詞全被 Δ4／Δ5 取代。 | M-B5 |
| B6 | 1. Introduction（章節安排段） | 「其餘章節安排如下。」 | KEEP | 章序不變。 | — |

## C. 第二章 Background

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| C1 | 2.1 Related Work（第 3 段末句） | 「本文保留恰好三個獨立 Q surface，但以 C1、C2、C3 route roles 對齊 Main-only」 | REPLACE | 末句明文「不引入額外協調器」；繼任者確實引入一個被評估的集合層。只換此一句，該段其餘保留。 | M-C1 |
| C2 | 圖 2-1 圖說 | 「圖 2-1：歷史 MODQN baseline 骨幹。」（末句「現行 C1/C2/C3 route roles 與 Main-only one-pass composition 見第四章。」） | REPLACE | 只改末句指向新的兩層結構；圖檔與前段圖說不動。 | M-C2 |
| C3 | 2.1 Related Work（第 4 段末三句） | 「現行 C3 改以 privileged four-profile teacher 產生嚴格 two-user LC-SRS label」 | REPLACE | teacher／student 邊界改為「集合條件化交互作用頭與其資訊介面」；CDRL lineage 敘述前半保留。 | M-C3 |
| C4 | 2.2 Motivation | 「綜合第 2.1 節，本研究聚焦三個尚未被同時處理的問題。」 | REPLACE | 第三點「若直接加入協調器或 joint decoder，又會改變既有 deployment contract」已被繼任者的設計選擇反轉。 | M-C4 |
| C5 | 2.2 Motivation | 「本研究以一條方法層設計回應上述問題。」 | REPLACE | 三點回應分別對應 Δ1、Δ4、Δ5。 | M-C5 |
| C6 | 2.2 Motivation | 「偏軸角增大時，波束增益降低，接收訊號與 SINR 可能下降」 | REPLACE | 這是 Δ1 的動機段（遞推、新 segment、$p^{0}$）；改為「角度經 $H\,G^T$ 決定所需功率、佔用經 ACM 階梯決定所需 SINR」。 | M-C6 |

## D. 第三章 Preliminaries

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| D1 | 3. Preliminaries（章首段） | 「本章先說明使用者如何從可見波束中選擇服務波束，再介紹這條連線的訊號品質」 | REPLACE | 「最後將這些量整理成能量效率、換手成本與負載平衡三個目標」已不成立（Δ7）。 | M-D1 |
| D2 | 3.1.1 Beam Activation and Load | 接於「沒有使用者的波束不發射功率，也不產生干擾。本研究不另設每顆衛星可同時啟用的波束數上限。」之後 | INSERT | 補 $10^\circ$ 最低操作仰角（D-5 偏差）與「顏色屬於波束—射頻鏈」不變式。 | M-D2 |
| D3 | 3.1.2 Geometry and Channel Model | 接於「其中 GT 直接承載偏軸角，Hu,s,v(t) 保留其餘通道因素的物理意義」該段之後 | INSERT | 唯一補充：$H_{u,s,v}G^{T}$ 的乘積在繼任者中成為功率控制式的分母，須在此處明講。式 (3.5)–(3.10c) 全數 KEEP。 | M-D3 |
| D4 | 3.1.3 Power, SINR and Throughput Model（標題與章首段） | 「以下只保留每一條 UE–衛星–波束鏈路的實際量。pu,s,v 表示實際 RF 發射功率，不再由目標 SINR、最低速率或 lagged interference 反推」 | REPLACE | 標題改為 3.1.3 Power Control, ACM and Throughput Model；原句與繼任者**反向**：功率正是由速率目標所對應的 ACM 門檻反推。 | M-D4 |
| D5 | 3.1.3 | 「令 τu,s,v 為目前 uninterrupted served physical link (u,s,v) segment 的起始時間步」（含式 3.11、3.12 與其後「式 (3.12) 只有在 τu,s,v 到 t 的每一步」段） | DELETE | Δ1：無記憶功率控制沒有跨步遞推、沒有 segment closed form、沒有 $\tau$、沒有 $p^{0}$。 | M-D4 |
| D6 | 3.1.3（波束功率聚合） | 「一支已啟用的波束以單一功率發射，不論其上載有幾位使用者；沿用執行端的聚合慣例」 | REPLACE | 等空中時間 TDM 下同一時隙只有一位使用者在該波束上發射；`max` 聚合退場，改以時隙加權積分（D-7）。 | M-D6 |
| D7 | 3.1.3（干擾） | 「且 Iu,s,v(t,θu,s,v,θ3)=Iu,s,vi(t,θu,s,v,θ3)+Iu,s,vx(t,θu,s,v,θ3)。每一項都以該干擾波束自己的偏軸角」 | REPLACE | 式 (3.12a)(3.12b) 形式保留，但干擾成為功率向量的函數（耦合不動點）；跨增益以 (NORAD, 波束鏈) 為實體鍵；選擇時視圖的干擾維持名目。 | M-D7 |
| D8 | 3.1.3（SINR 後說明） | 「其中 Iu,s,v(t,θu,s,v,θ3)+σ2>0。這個符號同時用於基線鏈路計算與角度感知功率替換」 | REPLACE | 式 (3.13) KEEP，但語意擴充為「聯合解算後」，並引出服務判準 $\gamma\ge\gamma^{-}$ 與名目／實現視圖之分。 | M-D8 |
| D9 | 3.1.3（吞吐量） | 「波束內採時分多工，同一波束上的 Us,v(t) 位使用者依序使用可用頻寬。因此鏈路 throughput 為」（含式 3.14 與其後「Bw 是單一波束可用頻寬」段） | REPLACE | Δ2：連續 Shannon 式改為離散 ACM 階梯與等空中時間 TDM，並新增 $R^{\star}$、$\Gamma_r(\cdot)$、式 (3.14a)。 | M-D9 |
| D10 | 3.1.3（PA 效率） | 接於「平方根可由類 B 的理想近似理解：令 Vo 為輸出電壓振幅」該段之後 | INSERT | $\xi^{+}=0.35$ 必須改稱**飽和效率**；補上限處約 19.7%、$0.32$ W 處約 8.6% 的實現效率，並明列直流律的套用順序（D-6、D-7）。式 (3.15)(3.15a) 本身不動。 | M-D10 |
| D11 | 3.1.3（系統總功率） | 「此處對 (s,v) 求和而非對 (u,s,v) 求和：一支已啟用的波束只有一個放大器」 | REPLACE | 式 (3.16) 需納入待機項（主要 $P_{\text{idle}}=0$；敏感度 $f=1/12$）與時隙加權積分。 | M-D11 |
| D12 | 3.1.3（單鏈路 EE 顯示量） | 「最後，固定鏈路 (u,s,v) 的 EE 顯示量定義為」（含式 3.17 與其後「這裡的三下標固定分子的 UE-link」段） | DELETE | 繼任者唯一的 EE 是匯總比值；逐鏈路顯示量會誘發 per-row EE 平均的誤讀。 | M-D12 |
| D13 | 3.1.3（末段） | 「本研究採用的多目標深度 Q 網路（MODQN）基準，以三個 Q 網路分別學習三個目標」 | DELETE | 三個 legacy reward 的接續敘事在繼任者中無對應。 | M-D12 |
| D14 | **新增 3.1.4 Energy Model and the Metric Boundary** | 置於原 3.1.3 之後、3.2 之前 | INSERT | 能量邊界句必須**逐字**出現於正文與每一份 receipt 標頭；並須說明「被省略的共同能量不會在政策之間相消」、固定與待機項的升格假設。 | M-D14 |
| D15 | 3.2 Problem Formulation（章首段與式 3.24） | 「本研究同時考慮能量效率、換手成本與負載平衡。令 Lw 為每個時間步納入決策的可見衛星數」 | REPLACE | 三目標長期最佳化 P1／P2／P3 退場，改為單一最終目標（匯總 EE）＋QoS 共同主要結果。 | M-D15 |
| D16 | 3.2.1 Angle-Aware Energy Efficiency | 「式 (3.15)–(3.17) 已先定義鏈路耗電、共同系統功率與固定鏈路 EE 顯示量。」 | REPLACE | $r_{1,u}$ 的逐使用者 EE 貢獻和退場，改為 $\eta^{N}=\sum B/\sum E$ 與共同主要結果。 | M-D16 |
| D17 | 3.2.2 Handover Cost | 「沿用上述 (ρu(t),δu(t)) 表示的服務衛星與波束。同衛星換束的成本為 φ1」 | REPLACE | $\Psi_u$ 改名為 $\Phi_u$（$\Psi$ 讓位給交互作用殘差），$\varphi_1=0.5\kappa$、$\varphi_2=1.0\kappa$，並補再進入與 cell re-key 規則。 | M-D17 |
| D18 | 3.2.3 Load Balancing | 「第三個獎勵取使用者所選波束當步服務人數的負值；該人數即式 (3.3) 定義的 Us,v(t)」（含式 3.28 與其後說明段） | DELETE | 佔用人數已經由 $\Gamma_r(U_{s,v})$ 進入所需功率與能量；再放一個 $-U_{b_u}$ 會讓第一目標重複承擔第三目標的工作。 | M-D18 |
| D19 | 3.2.4 Reward Vector and Evaluation Metric | 「MODQN 保留三維獎勵向量」（含式 3.29 與其後三段） | DELETE | 三維獎勵向量沒有繼任對應；保留只會被讀成投票。原節位置改置新的 3.2.3／3.2.4。 | M-D18 |
| D20 | **新增 3.2.3 組態層剩餘與目標落差** | 置於原 3.2.2 之後 | INSERT | 第四章的選擇與學習都在 $\Omega(a)=B(a)-\lambda E(a)-\Phi(a)$ 上進行；frozen-$\lambda$ 的目標落差全文只說一次，須在此說。 | M-D20 |
| D21 | **新增 3.2.4 約束** | 置於新 3.2.3 之後 | INSERT | 決策硬約束沿用式 (3.1)–(3.2)；$p^{+}$ 語意由可行性篩選改為物理上限。 | M-D21 |
| D22 | **新增 3.3 Declared Idealisations of the Model** | 置於第三章結尾 | INSERT | 四項理想化（原子式套用、回溯式軌道重建、部分酬載邊界、全緩衝流量）寫在模型被定義的地方，不塞進註腳。 | M-D22 |

## E. 第四章 MCRL

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| E1 | 4.1 Method Overview（第 1 段） | 「第三章給出衛星、波束、角度、功率、SINR、throughput 與系統耗能的物理鏈。」 | REPLACE | Δ5：部署由「一次逐使用者無權重相加與 argmax」改為兩層。 | M-E1 |
| E2 | 4.1（候選表段） | 「低軌衛星持續移動，每位使用者可選的實體波束會改變」 | KEEP | 固定長度候選表、$L_w$／$J_w$／$C$／$b_u(c,t)$ 映射完全沿用。 | — |
| E3 | 4.1（原生狀態） | 「沿用 MODQN 的原生 predecision state，可將候選順序下的資訊寫成」（含式 4.1 與其後「其中 xu(t−1) 記錄前一步連線」段） | REPLACE | $Q_1$／$Q_2$ 各有凍結的 schema，且明文**不含**遞推功率、進場增益比與段齡。 | M-E3 |
| E4 | 4.1（遮罩） | 「候選表的長度固定，但部分位置在當下可能不可用。」（式 4.2、4.3） | KEEP | 原生安全遮罩介面不變。 | — |
| E5 | 4.1（roster 但書） | 「但此向量只是同一步各使用者 action 的集合，不是 joint decoder、協調器或第二次決策。」 | REPLACE | roster 現在確實是被集合層評分的對象；但書改為「在有界目錄上評分，仍是單次承諾」。 | M-E5 |
| E6 | 4.2 Three Independent Q Surfaces and Main Objective（整節，含式 4.5） | 「本稿固定恰好三個獨立 Q surface：Q1、Q2 與 Q3。」 | REPLACE | 整節改寫為 4.2 逐使用者提案與集合層（含兩層資訊介面與跨臂等化清單）。 | M-E6 |
| E7 | 4.3 Shared Current-Slot Counterfactual and Route Roles（整節，含式 4.6 與三個 Heading3） | 「三路學習共用同一個 predecision anchor 與 safe action domain，但不共用 privileged outcome。」 | REPLACE | $G(x)$ 改為 $\Omega(a)$；三路角色改為 $D(a)$／續值／$\Psi_{\mathcal K}$，並附恆等式。 | M-E7 |
| E8 | 4.4 Exact Two-User LC-SRS Teacher（整節，式 4.7–4.11） | 「對每一個已由 predecision topology enumeration 確定的 two-user pair，使用四個 matched current-slot profiles。」 | DELETE | Δ4：四 profile、$\ell_i$、$e_i$、$\Psi_B$／$\Psi_E$、$z_{3,i}=e_i+\Psi/2$、two-user scoped identity 與「拒絕成員數不是 2 的 topology」全數退場。節次由 M-E7 與 M-E9 承接。 | M-E7 |
| E9 | **新增 4.4 The Margin-Adjusted Selection View** | 置於新 4.3 之後 | INSERT | 第十百分位通道增益評分規則、其兩項構造限制、目標／發射 MODCOD 對、兩個決不混用的分解、各臂各自的排序鍵。 | M-E9 |
| E10 | **新增 4.5 Bounded Catalogue and Two-Stage Scoring** | 置於新 4.4 之後 | INSERT | 有界目錄 $\mathcal X(t)$ 的四個構成、兩階段評分、10 s 預算與逾時執行已驗證 $a^{0}$。 | M-E10 |
| E11 | 4.5 Deterministic Relational C3View and Student（整節，式 4.12、4.13） | 「C3View 是在 profile evaluation 前從 immutable captured state 建立的 deterministic relational descriptor。」 | REPLACE | 改為 4.6 集合條件化純量交互作用頭 $\Psi^{f}_{\mathcal K}$：置換不變、錨定為零、輸入必含成對跨增益區塊。 | M-E11 |
| E12 | **新增 4.7 Comparators and Mechanism Statistics** | 置於新 4.6 之後 | INSERT | $a^{0}$／$a^{1}$／$a^{d}$／$a^{\psi}$、$D(a)$、淨避碰值 $\Upsilon$、反轉頻率、於 $a^{1}$ 再錨定的分解；表 II 置於此節之後。 | M-E12 |
| E13 | 4.6 Route-Specific Learning and Deployment Procedure（整節七步） | 「current method 的 training／deployment boundary 依下列順序固定：」 | REPLACE | 步序改為：捕獲→提案 $a^{0}$ 並驗證→建目錄→兩階段評分→選擇→承諾；並補四個具名實驗與中性來源規則。 | M-E13 |
| E14 | 4.7 Method Status and Claim Ceiling（整節） | 「本章是 current method-aligned draft。」 | REPLACE | 升級為 4.9 完整宣稱結構：階梯 Level A／B／C、收容三分法、$\delta=+0.5\%$ 交集–聯集合取、校準揭露、用語界定與本章狀態。 | M-E14 |

## F. 第五章 Experimental Results

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| F1 | 5.1（章首段） | 「本章說明模擬環境、索引域、通道與能耗模型，以及訓練和評估設定。」 | REPLACE | 「第三章的 active EE 主鏈」句仍成立，但須改指新的物理契約並宣告 legacy provenance 的新範圍。 | M-F1 |
| F2 | 表 5-1「時間離散化」列 | 「每步 30.08 s；每回合 10 步」 | REPLACE | 改為每步 30.08 s、每個世界 30 個決策錨點（世界建構 33 步）、步內 48 個積分邊界。 | M-F2 |
| F3 | 表 5-1 其餘列 | 「真實 Starlink 星曆（TLE 搭配 SGP4），373 個每日檔」 | KEEP | 星曆、$h_s$、$L_w$、$U$、$V$、$J_w$、$C$ 全部沿用。 | — |
| F4 | 表 5-1 後說明段 | 「在 C=28 下，式 (4.1) 的四類原始分量——前一步連線、候選 SINR、偏軸角與前一步需求——各有 28 個元素，因此 Q 網路輸入 su 為 4C=112 維。」 | REPLACE | 式 (4.1) 已改為 $Q_1$／$Q_2$ 的凍結 schema；112 維敘述不再對應。 | M-F4 |
| F5 | 表 5-2「段起始發射功率 $p^{0}$」列（含 3 dB 增益預算長註） | 「0.825 W，即 p+/2；式 (3.11) 每個新 served segment 的起始值。」 | DELETE | Δ1：段起始功率不存在，3 dB 預算的幾何論證隨之失效。 | M-F5 |
| F6 | 表 5-2「每波束射頻輸出上限 $p^{+}$」列的備註 | 「1.65 W；式 (3.15a) 回退後的每波束操作上限，亦為鏈路可行性檢查的門檻。」 | REPLACE | 數值不變，語意改為物理上限；「鏈路可行性檢查的門檻」一語必須撤回。 | M-F5 |
| F7 | 表 5-2「PA 最大效率與輸出回退」列（類別名稱） | 「PA 最大效率與輸出回退」／「0.35、5 dB」 | REPLACE | 類別名稱改為「PA 飽和效率與輸出回退」；備註補實現效率兩點。正文與表中一律不得出現「35% 效率」。 | M-F5 |
| F8 | **表 5-2 新增列** | 置於「頻率重用」列之後與「固定功率」列之前 | INSERT | 新增 MODCOD 表、實作餘裕、roll-off、速率目標 $R^{\star}$、可解碼門檻 $\gamma^{-}$、分位水準 $\alpha$、待機 $P_{\text{idle}}$、候選更新週期 $N$、收斂容忍度等九列。 | M-F8 |
| F9 | 表 5-2 後段 | 「目前 active 契約不把最低速率反推、beam／satellite cap、PA 參考曲線或 min／max projection 放入 EE 主公式。」 | REPLACE | 此句與繼任者**反向**：新契約正是由速率目標反推所需功率。 | M-F9 |
| F10 | 表 5-2 後段 | 「本章既有數值結果若由舊版 runtime 產生，仍須以 legacy provenance 解讀」 | REPLACE | legacy provenance 的範圍重新界定為「舊物理 runtime」，並明文排除其數值於本文效能宣稱之外（D-0）。 | M-F10 |
| F11 | 「Legacy 執行設定」小表 | 「最低速率門檻 Rm 1 Mbit/s」 | KEEP（改標籤） | 仍是 provenance；小表標題改為「Legacy 舊物理 runtime 執行設定（只作第五章 provenance）」。 | M-F10 |
| F12 | 表 5-3「三目標純量化權重」等列 | 「三目標純量化權重 Ω=(ω1,ω2,ω3) (0.5,0.3,0.2)」（連同「主代理與鯰魚代理折扣」、「能效分層」、「週期性介入」、「競爭獎勵」、「目標尺度常數」五列） | DELETE | 加權純量化、鯰魚競爭獎勵、雙折扣、能效分層、週期性介入與目標尺度常數在繼任者中沒有對應；$\Omega$ 字母釋出改作組態層剩餘。 | M-F12 |
| F13 | 表 5-3「網路結構」「學習與批次」「探索與目標網路」「訓練長度」列 | 「主代理與鯰魚代理的每個 Q 網路均使用 100、50、50 個隱藏單元」 | REPLACE | 學習器組態改為 stages 6–8 契約：16 個學習種子、6 臂、每日期 2 個世界、每 100 個 source epoch 存檢查點。 | M-F12 |
| F14 | 表 5-3「換手成本」列 | 「同衛星換束為 0.5、跨衛星換手為 1.0」 | REPLACE | 改以 $\kappa$ 為單位：$\varphi_1=0.5\kappa$、$\varphi_2=1.0\kappa$，並註明不代表時間也不代表焦耳。 | M-F12 |
| F15 | 表 5-3 後兩段 | 「MODQN [2] 報告的學習率為 0.01。」／「目前凍結的尺度常數為 (c1,c2,c3)=(2471140.576, 1.0, 6)。」 | DELETE | 尺度常數三元組隨加權純量化退場；學習率敘述併入 M-F12 的學習器組態列。 | M-F12 |
| F16 | 5.1「約束的作用範圍」整節（Heading3 與其下四段） | 「在凍結情境下量測本節設定的三項約束是否作用。每波束射頻輸出上限 p+ 在 12,000 個決策步中的 113 步(0.94%) 上開火」 | DELETE | 這一整節量測的是**已被刪除的機制**（段起始功率＋遞推＋$p^{+}$ 削頂）；0.94%／113 步／1.6452 W／117.2%／214.8%／7.60%／4.56 步／2.54 步全部不可轉述。 | M-F16 |
| F17 | **新增 5.2 有效性證書（Validity certificates）** | 置於 5.1 之後、實驗結果之前 | INSERT | 承接被刪除的「約束的作用範圍」：以速率目標不可行率、上限命中率、收斂證書分布、ACM 三物件分布與鏈路閉合帳取代，全部 `⟨結果待填⟩`。 | M-F17 |
| F18 | **新增 5.2.4 ACM 因果性更正的有效性證書** | 置於 M-F17 之內 | INSERT | 記錄 stage-4h 更正的配對驗證：更正前後在同一能量下的可用度與匯總 EE 對比；**這是有效性證書，不是效能結果**，數值 `⟨結果待填⟩`。 | M-F18 |

## G. 第六章 Conclusion

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| G1 | 6.1 Summary（兩段） | 「本稿提出與 current method 對齊的 Multi-Catfish Reinforcement Learning（MCRL）方法草稿。」 | REPLACE | 與 Δ1／Δ4／Δ5 衝突：single-pass argmax、LC-SRS、C3View 全數退場。 | M-G1 |
| G2 | 6.2 Contributions（四條） | 「將 Main-only network ratio-of-sums EE 與第三章的角度、功率、SINR、throughput」 | REPLACE | 四條分別綁 segment 語意、legacy reward 否定、$z_{3,i}=e_i+\Psi/2$ 與 single-pass 無協調器，全部需改。 | M-G2 |
| G3 | 6.3 Limitations and Future Work（兩段） | 「本稿是 current method-aligned draft，不是 empirical-final。」 | REPLACE | 改用 `LIMITATIONS-REGISTER.md` 的七項骨架與 L-10 措辭護欄，並加入凍結後未採納發現的公布規則。 | M-G3 |

## H. 附錄與參考文獻

| # | 目標標題 | 被處置段落的開頭引文 | 處置 | 理由 | 區塊 |
|---|---|---|---|---|---|
| H1 | **新增 表 I（系統模型假設）** | 置於第三章結尾或附錄 | INSERT | `TAB-I-model-assumptions.md` 逐列併入；**須補 B12 的第五欄與新列 B14**（見 M-H1）。 | M-H1 |
| H2 | **新增 表 II（比較器契約）** | 置於 4.7 節之後 | INSERT | `TAB-II-comparator-contract.md` 逐列併入，不另改寫。 | — |
| H3 | **新增 偏差登錄條目 D-11** | 置於偏差登錄（`docs/DEVIATION-REGISTER.md` 的繼任版） | INSERT | M-10 只寫成規則；stage-4h 的**更正事件本身**（發現、修正、配對驗證、更正前數值全數排除）尚未登錄。 | M-H3 |
| H4 | References | 「[27] V. Mnih, K. Kavukcuoglu, D. Silver, et al.」 | INSERT | 新增 [28] ETSI EN 302 307-1（ACM 模式表與門檻）；[1]–[27] 全部保留。 | M-H4 |

---

## 執行順序建議

1. 先落 **D／E**（第三、四章）——它們是替換文字的主體，其餘各章的措辭都要對齊它們。
2. 再落 **H1／H3**（表 I 與偏差登錄）——ACM 更正的登錄必須先於第五章的有效性小節。
3. 再落 **F**（第五章表格與刪除）。
4. 最後落 **A／B／C／G**（摘要、第一、二、六章）——這四處是全篇的措辭出口，
   必須在第三、四章定稿之後才回寫，否則會出現三處各說一套。

## 未列入本計畫者

- **圖 3-1** 需補「同色波束—射頻鏈之間的成對跨增益」與「等空中時間時隙」兩個視覺元素；本交付不產生圖檔。
- **5.2 起的實驗結果**：全部數字須在正式矩陣完成後重寫，本計畫一律以 `⟨結果待填⟩` 佔位。
- **符號表**：`SYMBOL-ADDITIONS.md` §3 的九項異動須併入符號表 §10.11，屬單一權威版本登記的另一條路徑。
