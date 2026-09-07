# 接班 prompt — 下一張機制圖（週期性介入）

> **SUPERSEDED 2026-07-22:** this single-figure handoff has been completed and
> expanded into the full CDRL-style Chapter 3/4 batch.  Use
> [`CDRL-STYLE-BATCH.md`](CDRL-STYLE-BATCH.md) and the builders in this directory
> as the current review surface.  The material below remains provenance only.

撰寫依據：`agent-skills/modqn-reproduction-governance/SKILL.md`（claim boundary）＋
`/home/u24/papers/skill/gpt-5-5-prompt-authoring/SKILL.md`（結構）＋
`docs/devkit/templates/implement.md`（鐵則欄位）。2026-07-21。

以下整段可直接貼進新對話。

---

# Personality

繁體中文回覆（prose 繁中、code 與 commit message 英文）。**不要自評圖畫得好不好**——
「看不看得懂」是 USER 的判定，不是你的。畫完就交給他看，不要先寫一段自我評估污染判斷。

# Goal

重畫 `thesis-mc` 的**週期性介入**機制圖。現行版本是六個方框把參數寫在框裡
（`Catfish share ρ_I`、`Mixed batch size B`、`Interval [T_lo, T_hi] random per intervention`），
機制沒有任何一部分被畫出來——與 2026-07-21 剛修好的另外三張是同一個病。

參考 CDRL 原論文的 **fig4-6**，做 stage-3 ADAPT。

# 第一步 —— 現在就開始，不要等指令

**這份 prompt 本身就是授權。** 讀完素材就直接動手畫，不要回頭問「要不要開始」「要用哪個方案」。
本專案的常規是 auto-progress：只有不可回復的 BLOCK、實驗結果出爐、與 go-server 才停下來問人。
下面的 Stop rules **不阻擋開工**——它們只在「要把圖嵌進論文／改章節」那一步才生效，而那一步在
畫完之後。

具體順序，不要跳：

1. 打開 `archive/catfish-route/fig-ref/fig4-6.png` 看清楚（不是憑印象）。
2. 讀 `redrawn-2026-07-21/build_fig_asymmetric_discount.py` 的檔頭——它記錄了同一批圖踩過的坑。
3. 讀 `thesis-mc/figures/src/figkit.py` 檔頭 ＋ `thesis-mc/ch4-method.md` §4.3 策略三。
4. 寫 builder → 跑 → 渲染 → **把圖貼給 USER 看**。

開工前給一句話的預告（在做什麼、大概幾步），然後就開始跑工具，不要逐步請示。

# 素材位置（先全部打開看過再動手）

- **CDRL 原論文參考圖：`archive/catfish-route/fig-ref/`**（15 張）。這次看 `fig4-6.png`。
  ⚠ 這個資料夾**未納入 git 追蹤**，只存在於本機工作區。
- **已完成的同批三張**（產線與慣例照抄）：`thesis-mc/figures/redrawn-2026-07-21/`
  - `build_fig_competitive_reward.py` / `build_fig_competitive_reward_lr.py` /
    `build_fig_asymmetric_discount.py` — **檔頭記錄了每一處對參考圖的偏離與理由，先讀**。
- **目標圖現況**：`thesis-mc/figures/fig-intervention-annealing.png`，
  builder 在 `thesis-mc/figures/src/build_fig_intervention.py`。
- **真相源**：`thesis-mc/ch4-method.md` §4.3 策略三、式 (4.12)。符號以
  `thesis-mc/notation-table.md` 為準（⚠ 折扣一律 β、γ 專指 SINR）。

# 必須用 skill

**`flowchart` skill**（= diagram-kit，`/home/u24/.claude/skills/flowchart` →
`/home/u24/papers/diagram-kit`）。不要自己手刻 SVG。

- 文法：`styles/academic.md`，特別是 **rule 0（fidelity first：REPRODUCE → REPAIR → ADAPT）**
  與 **Part 2**（機制放進幾何，不要用句子解釋）。
- spec 格式：`docs/spec-reference.md`。
- 產線：`thesis-mc/figures/redrawn-2026-07-21/build_*.py` 是可直接抄的範本；共用工具
  `thesis-mc/figures/src/figkit.py`——**先讀它的檔頭**，那裡有一整串實測得到的引擎行為
  （方框高度怎麼算、下標寫法、annotation 不吃 autoNotation⋯），能省掉大半來回。

# 只取 fig4-6 的哪一部分

fig4-6 是總覽圖，疊了三件事。**只取左半的兩個構件**：

| fig4-6 的部份 | 取不取 | 理由 |
|---|---|---|
| `S^mix 70% Main + 30% Catfish`（兩個經驗池 → 一個混合批次） | **取** | 策略三的前半 |
| `if cnt == random period` 菱形 ＋ `cnt += 1` ＋ `yes/no → Regular Training` | **取** | 策略三的後半：何時觸發 |
| 右邊兩大塊代理架構（θ、NN、RF chain、s_{t+1}、Reward、Update） | **不取** | 那是我們圖 4-2／4-3 的地盤；一張細部圖一個機制 |
| 鯰魚那塊裡的 `Shapping Reward` | **不取** | 那是競爭獎勵＝已完成的圖 4-6，重複 |
| 回饋／更新迴路 | **不取** | 非本機制主題 |

目標構圖：**兩個經驗池 → 依 ρ_I 分配的混合批次 → 由隨機間隔觸發 → 主要代理的一次額外更新**
（終點是一個方框，不是整套架構）。

# Success criteria

1. **機制在幾何裡，不是寫在方框裡。** 這是唯一真正的驗收軸，其餘都是必要非充分。
2. **兩個可以贏過參考圖的地方**（前三張都沒有這種機會，這張有）：
   - **比例**：fig4-6 把它寫成 `70% + 30%` 兩個字。把批次畫成一排格子、其中 ρ_I 的部分
     塗成鯰魚色 ⇒ 比例變成看得出來的。
   - **隨機間隔**：fig4-6 只寫 `random period`。畫一條時間軸、介入刻度**間距不等**，
     對照等距的常規更新 ⇒ 「隨機」變成看得出來的。
3. **四道 gate 全過**（builder 跑完會自動跑前三道）：
   `check_layout --preset academic` 0 ERR → `check figure` PASS → `validate svg` PASS →
   `eye-pack.sh` → 人眼看彩色與灰階兩張 → `fill_eye.py` → `check_eye` 全 pass/fixable-with-note。
   ⚠ 順序不能顛倒：eye-pack 每次重跑都會把 eye.json 重設為 unreviewed。
4. 字級 **40**、與同批三張一致（會出 3 個 `F0-figure-profile` warning，那是刻意的，別「修」它）。
5. 產出全部落在 `thesis-mc/figures/redrawn-2026-07-21/`（那是這批圖的最終位置）。

# Constraints

1. **絕不碰 G1／EUV 保護面**：`src/modqn_paper_reproduction/algorithms/modqn.py`、
   `runtime/{replay_buffer,catfish_replay,trainer_spec}.py`、`configs/modqn-paper-baseline*`、
   `data/phase02*`、`env/family_b_*.py`。
2. **不進畫布**：任何效果宣稱、任何數值、任何定義式（式 (4.12) 進圖說，不進方框）。
   鯰魚是**具名的訓練元件**，不得出現「鯰魚驅動了改善」這類因果語。
3. 嚴禁樹級 git 操作（stash / checkout / reset / clean）。
4. commit 直接進 main；**`git add` 與 `git commit` 必須分成兩個 tool call**（devkit hook 會擋），
   且 `git add` 要逐一列出路徑（禁 `-A` / `-u` / `.`）。
5. ⚠ **另一個 session 可能同時在寫這個 repo**（2026-07-21 已發生過：對方的 commit 把我
   staged 的檔案一起帶走）。stage 完就立刻 commit，別在兩個 tool call 之間做別的事。
6. `thesis-mc/ch4-method.md` 目前帶著別的 session 未提交的正文編輯——**不要 stage 它**。

# Output

畫完 → 渲染 PNG → **直接把圖貼給 USER 看** → 等他的一句話。
不要先寫「我覺得這樣比較清楚」之類的自評。

回報格式：1) 做了什麼（一句話）2) 對參考圖的偏離逐條記帳（改了什麼、為什麼——這要同時寫進
builder 檔頭，那是稽核軌跡）3) 四道 gate 的結果 4) 你自己還看得到的瑕疵 5) 待 USER 裁決的點。

# Stop rules

⚠ **這些都不阻擋開工。** 它們發生在圖畫完之後——先把圖畫出來交給 USER 看，再處理下面這些。

**硬停點（不要自己決定，問 USER）**：

1. **這張圖到底要不要進 ch4。** `FIGURE-MANIFEST.md` 說它「已嵌入 ch4」，但實測 ch4 只有
   8 個圖引用、**這張不在裡面**（§4.3 策略三整段只有式 (4.12)，沒引圖）。manifest 那一列是錯的。
2. **圖號指派**：補圖會讓 4-5～4-9 重新編號，那是論文層決定。
3. 任何需要動 `ch4-method.md` 的事。

# 後續還要畫哪些（一開始就知道全貌）

「參考 CDRL 的圖來改」這條路**只適用於沿用自 CDRL 的四個機制**。ch4 明載：四個鯰魚機制沿用
CDRL，而壅塞情境／情境正規化、三個鯰魚角色、容量懲罰**是本論文加的，CDRL 沒有對應的圖**。

| 機制 | 出處 | CDRL 參考圖 | 狀態 |
|---|---|---|---|
| 能效分層 | CDRL | fig4-7（菱形路由＋垃圾桶） | 我們的圖 4-5 同題，**沒有這個病**（0 個式子在框裡），暫不動 |
| 非對稱折扣 | CDRL | fig4-8 | ✅ 2026-07-21 完成 |
| 競爭獎勵 | CDRL | fig4-9 | ✅ 2026-07-21 完成（另有左右排版變體） |
| **週期性介入** | CDRL | **fig4-6** | **← 本次任務。最後一個 1:1 對應** |
| 壅塞情境／情境正規化 | 本論文 | 無 | 圖 3-3 有同樣的病（z-score 公式寫在框裡），但**沒有參考圖可抄**，只能借語彙 |
| 容量懲罰 | 本論文 | 無 | 圖 4-7 有同樣的病（`λ Σ Δ_s²` 寫在框裡）且是**賭注最大的一張**（唯一有量測訊號的機制）。
  該畫的是「排序後的偏好壓力＋$v_{\max}$ 切線＋被丟掉的尾端質量」。動手前先讀
  `docs/capacity-penalty-explainer-package/`（未納入 git 追蹤） |

做完週期性介入之後，剩下的兩張（容量懲罰、情境正規化）**沒有 CDRL 參考圖**，作法要改成
「借語彙、自己組構圖」。那是另一種工作，**那時候**才需要跟 USER 確認要不要接著做——
不是現在。本次任務就是週期性介入那一張，做完為止。

# 其他待決事項（不阻擋本次任務，但別忘了）

- `Q^M` 符號：非對稱折扣圖的主要代理用不帶上標的 `Q_j`（忠於符號表）；USER 曾提議改成 `Q^M`
  以求兩欄對稱，那需要同時改 `notation-table.md` 與 ch4 全章，未裁決。
- 要不要補一個 catfish 圖示 asset（`diagram-kit/assets/icons/`），讓鯰魚身分像 CDRL fig4-7／4-10
  那樣看得見。目前 kit 裡沒有。
- 40px 字級與「開始使用圖示」要不要推廣到其餘 12 張圖。
- 非對稱折扣圖的圖說必須補一句定義長條（`β^k`，其和為 Q，schematic）——已登記在該圖眼檢的
  唯一 fixable 項。
