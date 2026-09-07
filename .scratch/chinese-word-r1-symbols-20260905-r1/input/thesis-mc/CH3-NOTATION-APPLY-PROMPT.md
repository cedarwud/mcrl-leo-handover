# ch3 notation apply — turnkey prompt（2026-06-30；track-4 integration controller 用）

> 貼這份到**新對話**即可執行。此 pass = 把已累積的 ch3 notation/exposition 規則套進 `thesis-mc/mc-modqn-base.md`。
> 啟動只讀「規則＋crossref」，**不重讀原始論文 PDF/layout**（兩篇知識已蒸餾進 crossref＋規則內嵌）。

## 啟動讀（依序）
1. `thesis-mc/WRITING-RULES.md` — STATUS ＋ R8.2 ＋ R9–R15 ＋「ch3 notation/exposition 批次」summary ＋「ch3 §3.2–§3.4 sweep findings」。
2. `system-model-refs/two-paper-notation-crossref-2026-06-29.md` — 兩篇公式/記號 distilled bible（§3 交叉對照、§4 稿內重用、§5 provenance）。

## 目標
對 `thesis-mc/mc-modqn-base.md` 的 **ch3 §3.1–§3.2** 做**一次協調式 notation pass**（多條規則觸碰同一式，務必一次改完、勿拆零散）。

## 範圍（DO — 全非 figure-coupled、非 env 相依）
- **R15（純機械）**：式 3.14 干擾 `v''` → `v'`（全式）。
- **R12（機械）**：式 3.8/3.9 路損 `FSPL/SF/CL` → 單一母符號＋數字編號 `L^{(1)}/L^{(2)}/L^{(3)}_{u,s}`；prose 一句講三者意義；去函數括號。**physics/引用 [10][11] 不動**。
- **R14（機械＋判斷）**：基數 `U,S,V` → `|\mathcal{U}|,|\mathcal{S}|,|\mathcal{V}|`（含式 3.31 `1/U`→`1/|\mathcal{U}|`、`:148-149` 三基數統一）；**勿** lowercase 物理純量 R/W/S/G（那是對的）。
- **R13（2026-07-28 USER 裁決）**：式 3.11 的接收增益不得再簡化為 `G_{R,u}`；沿用 HOBS 的完整鏈路索引與 T/R 上標，寫為 $G^{R}_{u,s,v}(t)$，並補其可隨使用者、衛星、波束方向與時間改變的定義；補 `g_{u,s,v}`（小尺度）一句定義。
- **R9（撰寫）**：式 3.4 `z_{s,v}` 補動機＋forward-ref（gate 干擾 3.13/3.14 ＋ 扛 k_cap 4.5）＋x/z 層級差別一句（案 A）。
- **R10（撰寫）＋ R14 中央 convention 塊**：在 §3.1 索引慣例（`:148-152`）擴一段：① arity 三族（鏈路量 u,s,v／幾何 u,s／波束屬性 s,v，含「導出量下標＝輸入下標聯集」一句）；② 字體/大小寫四層（黑板 $\mathbb{S},\mathbb{A}$＝RL 空間／花體 $\mathcal{U,S,V}$＝索引集／平體大寫＝基數$|\cdot|$或物理純量／純量依量別慣例 R/W/S/G 大寫、d/f/p 小寫）。
- **R11（低優先，可選）**：§3.3「二元連接變數」keep；若順手把同句「連接」重複收一個／或名詞改「連接指示變數」。
- **R8.2（一併）**：目標索引／權重全章＋圖統一（擇一：j＋ω 或 k＋w）；式 3.33(j,ω) vs 3.39(k,w) 對齊；`k` 與候選索引 `m_{u,k}`/k_cap 釐清。**注意此條跨 ch4/ch5＋圖 → 若只在 ch3 範圍，先統一 ch3 內部、跨章留總表**。
- **小**：`\text{scale}_k`（3.39）宜單符號；§3.4 標題「Catfish-DRL」→「多鯰魚/Multi-Catfish」；`ℓ`(3.38) vs `L` case 註記。

## 不在範圍（DON'T）
- **figure-coupled**：R8.6（k_cap 改名）、R8.3（MCRL↔B/A bridge）、R3（結果句）— 全 gated 在結果圖凍結後。
- **env-dependent**：R8.7（power model）、R8.1（eval-metric 定義）— 需 env `family_b` 資料。
- **EN**：`thesis-mc/en/*` 留**最終一次性重譯**（內容全凍結後），本 pass 只動 ZH `mc-modqn-base.md`。
- **G1/EUV**：`src/.../algorithms/modqn.py`(`aa877676`)、`env/family_b_*.py` READ-ONLY。heavy = 不跑。

## 紀律
- RED LINES：catfish=具名元件非 win-driver；無「catfish 驅動 win/拿掉就崩」因果；無 raw 純量贏 DQN_scalar；無 root-solved；無 2.8×/beats-Sun2024；ROOT-Q UNRESOLVED。
- r1=EE binding；用詞 協調式波束分配／綜合價值／χ_u；禁 decode/auction/蒸餾。
- **零數字、零 claim 改動**（這是 notation pass）；改完**驗所有式號 cross-ref 仍對**（forward-ref、引用式號）。

## 輸出
- 改好的 `thesis-mc/mc-modqn-base.md`（ch3 §3.1–3.2）。
- path-scoped commit 到 main＋push；回報 hash。
- WRITING-RULES STATUS 標各條「已套用 ch3」。
