# ch3→ch4 演算法邊界重構 — turnkey prompt（2026-06-30；track-4 用）

> 貼到**新對話**執行。此 pass = 把「提前出現在 ch3 的 MODQN 演算法」移到 ch4，ch3 收斂成純「系統模型＋問題建構」。
> USER 已決定：**完整重構**（非原地 reframe）、**開新對話專做**。J_w 留 ch3（USER 未反對建議）。

## 啟動讀（依序）
1. 本檔（CH3-CH4-RESTRUCTURE-APPLY-PROMPT.md）— 全部。
2. `thesis-mc/mc-modqn-base.md` ch3 §3.2–§3.4（約 line 334–501）。
3. `thesis-mc/ch4-method.md` §4.1–§4.2（line 1–48）。
4. `thesis-mc/WRITING-RULES.md` STATUS ＋ R2/R5（用詞）＋「ch3 notation pass 套用紀錄」（前一 pass 已把 H→Λ、L^{(1/2/3)}、eq3.26 正式化等套好；本 pass 接續）。
5. `system-model-refs/two-paper-notation-crossref-2026-06-29.md` §1.4（Sun MODQN 演算法式 = 搬移後的依據）。

## 為什麼（診斷，已確認）
- ch3 §3.2(四) 直接出現 MODQN **演算法**：Q 向量 $\overrightarrow{Q}$、純量化 $\zeta$（式 3.33）、各自取 argmax（式 3.34）、Q 更新（式 3.35）、**FIG-3-2（MODQN 架構圖）**。這些是「演算法」不是「問題建構」，提前出現在系統模型章。
- **ch4 已重複**：`eq 4.2` = `eq 3.33`（ch4 自承「式4.2 形式和式3.33 一樣」）；ch4 §4.1 動機段 ≈ ch3 §3.2(六) 動機段；ch4 `eq 4.9/4.10` = ch3 `eq 3.35` 的方法版。→ 本 pass = 把 MODQN baseline **整併到 ch4 只講一次**，ch3 不再出現演算法。
- EE（式 3.28）**不是演算法、是獎勵 r1**（貢獻①）→ **留 ch3**；其「P1 先出現、(一) 後定義」= Sun 公式(5) 風格的 state-then-define，正確，不動。

## 目標結構
- **ch3**：§3.1 系統模型 ＋ §3.2 問題建構（MOO P1/P2/P3 ＋ 三獎勵 r1/r2/r3 ＋ 候選波束目標量 ＋ 獎勵向量 ＋ MOMDP tuple ＋ 評估指標 J_w，**停在問題層**）＋ §3.3 基本想法 ＋ §3.4 比較。**無 Q 網路/純量化/argmax/Q更新/MODQN 架構圖**。
- **ch4**：§4.1 概觀＋**新增「MODQN baseline 回顧」**（Q 向量、純量化、各自取 argmax，prose 為主＋cite [2]）＋ **FIG-4-1 = MODQN 架構圖**（原 FIG-3-2）→ 現有 §4.2 鯰魚…（式號不動）。

## ★ 最小風險策略（binding）：ch4 式號 4.1–4.10 不准動
ch5 引用 ch4 式號（4.1–4.9）**約 25 處**。**重排 ch4 式號 = 連帶改 ~25 處 ch5 → 高風險、禁止。**
- 純量化已在 ch4 `eq 4.2`（$b_u=\zeta=\sum_j\omega_j Q_j$）→ **直接當作 ch4 的純量化正式定義**，不新增式。
- 各自取 argmax（原 3.34）、MODQN baseline 的 Q 更新（原 3.35）→ **以 prose 回顧**（cite [2]），**不新增 ch4 編號式**（method 版更新已是 4.9/4.10）。
- 候選波束目標量（原 3.36/3.37/3.38）→ **留 ch3**（見下；它們是模型導出量、非演算法）→ ch4 不新增式。
→ 結論：**ch4 不新增任何編號式、式號完全不動**；ch4 只動 (a) §4.1 加 baseline 回顧 prose、(b) 圖號 +1、(c) 對 ch3 改過的式號的引用文字。

## 範圍（DO）

### A. ch3 — 從 §3.2(四) 移除（移到 ch4 §4.1，下述 E）
- Q 向量 $\overrightarrow{Q}=[Q_1,Q_2,Q_3]$ 的引入句、純量化 **式 3.33**、各自取 argmax **式 3.34**、Q 更新 **式 3.35**、**FIG-3-2 placeholder＋其 caption**。
- §3.2(四) **保留**：獎勵向量 $\overrightarrow{R}_u$（式 3.32）＋ MOMDP tuple $\langle\mathbb{S},\mathbb{A},\overrightarrow{R},P,\beta\rangle$ 定義。
- §3.2(四) 末補一句 forward：「MODQN 以三個並行 Q 網路求解此 MOMDP；其純量化、各自取 argmax 與訓練更新屬解法層，於第四章說明。」(標題可由「獎勵向量與決策過程」→「獎勵向量與多目標馬可夫決策過程」，去掉「決策過程」=演算法味)

### B. ch3 — 候選波束目標量留 ch3、reframe（§3.2(五)）
- **留** 式 3.36/3.37/3.38（$\eta^{EE}_{u,s,v}$、$\Psi_{u,s,v}$、$\ell_{u,s,v}$）：它們是**模型導出量**（候選波束上的目標值，由 §3.1 通道/吞吐量模型算出），非演算法。
- prose reframe：去「第四章的方法**還需要**…」這種「為演算法準備」語氣 → 改「為了在決策前評估每個候選波束在各目標上的值，定義候選波束層級的目標量（第四章方法會用到）」。**仍可 forward-ref ch4，但定位為模型量。**

### C. ch3 — 式號重排（移除 3 式後，候選＋J_w 往前移）
| 原式號 | 新式號 | 內容 | 處置 |
|---|---|---|---|
| 3.26–3.32 | 不變 | MOO/獎勵/獎勵向量 | 留 |
| **3.33** $\zeta$ | — | 純量化 | **移 ch4**（reuse 4.2） |
| **3.34** argmax | — | 各自取 argmax | **移 ch4**（prose） |
| **3.35** Q更新 | — | MODQN TD | **移 ch4**（折入 §4.5 prose） |
| 3.36 $\eta^{EE}_{u,s,v}$ | **3.33** | 候選 EE | 留、renumber |
| 3.37 $\Psi_{u,s,v}$ | **3.34** | 候選 HO | 留、renumber |
| 3.38 $\ell_{u,s,v}$ | **3.35** | 候選 load | 留、renumber |
| 3.39 $J_w$ | **3.36** | 評估指標 | 留、renumber |
- ch3 §3.2 最終式號 = 3.26–3.36（共 11 式，原 14；無 gap/dupe）。

### D. ch3 — 過度集中動機段（§3.2(六)）
- 現引用「式 (3.34)」（argmax）→ 3.34 已移走 → 改「在每位使用者各自取 argmax 的選法下」(prose，或指 ch4 §4.1)。
- 此段與 ch4 §4.1 動機**重複** → ch3 這段**精簡為 1–2 句 bridge**（點出過度集中、引向 §3.3/第四章），完整動機留 ch4 §4.1。
- J_w 定義段（式 3.36 新）保留。

### E. ch4 §4.1 — 加 MODQN baseline 回顧 + 收 FIG
- §4.1 開頭（現「方法概觀」前）加一小段 **MODQN baseline 回顧**（prose）：三個並行 Q 網路得 $\overrightarrow{Q}=[Q_1,Q_2,Q_3]$；以權重 $\Omega=[0.5,0.3,0.2]$ 線性純量化（正式定義見 §4.2 式 4.2 的 $\zeta$）；每位使用者各自取 $\arg\max$ 選波束；各目標以標準 DQN（折扣 $\beta$）更新。cite [2]。
- **FIG-3-2（MODQN 架構）placeholder＋caption 移到 §4.1，改 slot 為 FIG-4-1。**
- §4.2 `eq 4.2` 反向引用「式 (4.2) 的形式和式 (3.33) 的純量化一樣」→ 3.33 已移除 → 改「$b_u$ 沿用 §4.1 回顧的 MODQN 線性純量化 $\zeta$」（intra-ch4）。
- §4.2 line 20「式 3.32 的延伸」**保留**（3.32 不變）。

### F. ch4 — 圖號 +1（新 FIG-4-1=MODQN；其餘往後）
| png | 原 slot | 新 slot |
|---|---|---|
| mc-fig3-modqn.png | FIG-3-2 | **FIG-4-1** |
| mc-fig4-framework.png | FIG-4-1 | FIG-4-2 |
| mc-figC-discount.png | FIG-4-2 | FIG-4-3 |
| mc-figD-replay.png | FIG-4-3 | FIG-4-4 |
| mc-figB-congestion.png | FIG-4-4 | FIG-4-5 |
| mc-figA-allocation.png | FIG-4-5 | FIG-4-6 |
| mc-fig5-algorithm.png | FIG-4-6 | FIG-4-7 |
- 更新 ch4 內所有 `[FIG-4-*]` 引用（lines ~12/30/32/34/36/75/77/114/116/120）。
- ⚠ **不要編輯 PNG 檔本身**；只改 thesis markdown 的 slot label。**figB/fig4 並行 figure session 可能在迭代（R7）→ 動工前確認 figure session 未在跑；若在跑，先同步 slot-map 再改 handoff 檔。**

### G. ch4/ch5 — 對 ch3 改過式號的引用更新
| 檔:行 | 原引用 | 改為 |
|---|---|---|
| ch4 §4.2 (line 20) | 式 3.36/3.37/3.38 | 式 3.33/3.34/3.35 |
| ch4 §4.2 (line 45) | 式 (3.33) | §4.1 回顧的 $\zeta$（移除 3.33 backref） |
| ch4 §4.1/4.3/4.4 (lines 5/51/81) | 式 (3.34) | 「各自取 argmax」prose 或指 §4.1 |
| ch5 (line 9) | 式 3.39 | 式 **3.36**（J_w） |
| ch5 (line 38) | 式 3.34 | 「各自取 argmax」prose 或指 ch4 §4.1 |
- **ch5 對 ch4 式號（4.1–4.9）的 ~25 處引用 = 不動**（ch4 式號不變）。動工後 grep 確認 0 處需改。
- ch6 = 無 ch3/ch4 式號引用（僅「第四章」字樣）。

### H. figure-handoff 檔同步
- `WRITING-RULES.md` R7 表（FIG-3-2/FIG-4-* 列）、`FIGURE-EXPLAINER.md`、`FIGURE-HANDOFF.md`：更新 FIG-3-2→FIG-4-1 ＋ ch4 圖號 +1。

## 不在範圍（DON'T）
- **ch4 式號 4.1–4.10 重排** = 禁（會連帶 ~25 處 ch5）。
- 候選波束目標量（3.36-38）移 ch4 = 不做（留 ch3；若 USER 之後堅持移，那是另一決策＋觸發 ch4 式號重排）。
- 結果圖/結果句（R3）、R8.6 k_cap 改名、power/eval-metric（R8.7/R8.1，需 env）。
- EN（`en/*`）= 留最終一次性重譯。
- **PNG 圖檔本身**（figure session 擁有）。
- G1/EUV：`src/.../modqn.py`、`env/family_b_*.py` READ-ONLY。heavy 不跑。

## 紀律
- RED LINES：catfish=具名元件非 win-driver；無「catfish 驅動 win/拿掉就崩」因果；無 raw 純量贏 DQN_scalar；無 root-solved；無 2.8×/beats-Sun2024；ROOT-Q UNRESOLVED。
- r1=EE binding；用詞 協調式波束分配／綜合價值／χ_u；禁 decode/auction/蒸餾。
- **零數字、零 claim 改動**（純結構搬移＋式號/圖號重排）。EE/獎勵語意不變、MODQN 內容不變、只是換章＋去重。
- R2 鯰魚密度、R4 無 we/本文、R1 collapse 條件式語氣：搬動時順手守住，勿回胖。

## 驗證（動工後必跑）
1. ch3 式號連續 3.1–3.36、ch4 式號連續 4.1–4.10（皆無 gap/dupe）。
2. ch4 圖號連續 FIG-4-1…FIG-4-7、ch3 圖僅剩 FIG-3-1。
3. cross-ref 全解析：grep 確認無殘留 `式 (3.33)`/`(3.34)`/`(3.35)` 指向已移除者；無 `式 3.39`；ch5 對 ch4 式號 0 處需改。
4. `$$` 與 `aligned`/`matrix` 環境配對（grep -c）。
5. **cross-model G6（binding，這是 load-bearing 結構改動跨 4 檔）**：codex review（若 quota 在）＋ agy Gemini-Pro；refute-by-default 檢「有無語意漂移、有無斷引用、MODQN 內容有無被竄改」。codex quota 盡則 STOP+回報（勿假裝跑）。

## 輸出
- 改好的 `mc-modqn-base.md`（ch3）＋`ch4-method.md`＋`ch5-experimental-result.md`＋figure-handoff 檔。
- path-scoped commit 到 main＋push；回報 hash。
- `WRITING-RULES.md` STATUS 標「ch3/ch4 演算法邊界重構 = 已套用」＋記錄 ch3 式號 map（3.36-39→3.33-36）、ch4 圖號 +1、ch4 式號不動。
