# 回覆:崩潰四項的取樣點已改,PREREG 已凍(2026-08-23)

凍結前補充的**追加 A 與 B 全部收下並照做**,然後 PREREG 已封存。
以下是實際落在程式與記錄裡的東西,以及一處我要主動揭露的取捨。

---

## A. 「第一步」那條理由不成立 ⇒ 已撤,並改為貪婪 argmax

**你的拆解對,而且我原本那句話是雙重錯的。**

`sampled_at` 原文寫「那是 epsilon-greedy 探索尚未被平均進去之前」。
按你的分類逐項檢查:

| 指標 | 來源 | epsilon 進不進去 | 原理由的處境 |
|---|---|---|---|
| `q_margin`、`q_entropy` | Q 值 | **從不** | **多餘** —— 它們本來就不需要這條保護 |
| `active_beam_count`、`argmax_agreement` | 選出的動作 | **會,第 0 步一樣會** | **無效** —— 擋不住它要擋的東西 |

我用一條對前兩項多餘、對後兩項無效的理由,去正當化一個對四項都適用的取樣點。
**取樣點的選擇與探索退不退出無關**,那句話從頭到尾沒有支撐任何東西。

### 已做

`CollapseSample` 現在把三種讀法分開,而且是**結構上分開**,不是靠註解:

```python
@dataclass(frozen=True)
class CollapseSample:
    # 來自 Q 面:epsilon 無關,兩種讀法完全相同
    q_margin: float; q_entropy: float; q_margin_raw: float; q_range: float
    # 來自貪婪 argmax:策略自己的選擇。B17 Q1 用這一組。
    active_beam_count: float; argmax_agreement: float
    # 來自實際執行的 epsilon-greedy 動作:是什麼點亮了波束。
    active_beam_count_executed: float; argmax_agreement_executed: float
```

`report()` 回的是**貪婪版**,PREREG 的 `actions_used` 明寫
「the two ACTION-derived indicators … are computed from the GREEDY argmax,
**and that version answers B17 Q1**」,並把你給的量級寫進去:
epsilon 由 1 降到 0.01 需 2000 回合而訓練跑 9000 ⇒ **執行版在前五分之一量到的
主要是隨機策略**。執行版留著,但它回答的是別的問題。

⚠ 我加了一個測試專門守這個區分:`test_the_greedy_and_executed_readings_differ_while_epsilon_is_high`。
依 W-27 §5 的通則,它**主動把系統推進 epsilon = 1**,然後斷言兩版確實分歧。
理由是:若兩版在完全探索下都相同,那個區分就只是裝飾,而裝飾性的區分
會在下一次重構時被合併掉,合併的人還會覺得自己在簡化。

## B. 只取第一步會系統性漏掉崩潰 ⇒ 已改為兩點

收下,而且你這一條比 A 更要緊 —— A 是理由錯,B 是**量測本身會漏**。

`EpisodeLog` 現在帶 `collapse_first` 與 `collapse_last` 兩顆樣本,外加
`collapse_drift()` 回傳「最後 − 最初」。訓練迴圈在 `_step_idx == 0` 與
最後一步各算一次,一次餵貪婪 argmax、一次餵實際動作。

PREREG 寫的是:

> BOTH the first and the last decision step of the episode. Collapse develops
> WITHIN an episode … so a first-step-only sample can miss it systematically,
> while averaging over the episode would smooth the process away. Their
> difference (`EpisodeLog.collapse_drift`) is the signal B17 Q1 asks for.

⚠ **一處我自己加的防線**,因為它是這次改動打開的新破口:
`collapse_report()` 在對應端沒有樣本時**拋 `MCRLContractError`,不回報零**。
四項全零讀起來像「沒有崩潰」,而它的真正意思是「什麼都沒量到」——
一份漏掉取樣的 9000 回合 run 會以最令人安心的形式失敗。

⚠ 另一處要揭露的**限制**:`steps_per_episode = 10`,所以「第一步與最後一步」
之間只隔 9 步 ≈ 4.5 分鐘的軌道時間。**回合內能發展多少集中,受此上限**。
`collapse_drift` 若接近零,不能直接讀成「策略不崩潰」,只能讀成
「在 10 步的視窗內沒有進一步集中」;`collapse_first` 的絕對水準仍然要看
—— 若第 0 步就已經高度集中,那本身就是答案。這一句已進 PATCH-LEDGER。

---

## C. PREREG 已凍

```
artifacts/PREREG-FROZEN-2026-08-23.json
  schema  mcrl-prereg-v1
  digest  d35ddaffda580c8c109f758372956d41aa947b9eb3915d742f3f5f9b7aaecf08
  holdout b9fa64909f81b70e…   (salt mcrl-leo-handover-2026-08-22)
  17 區段,125,740 bytes
  Q-D ✓  Q-E ✓(N = 4,依 W-28)  Q-F ✓  Q-G ✓ —— 四項全數關閉
```

`scripts/freeze_prereg.py` **拒絕覆寫**。可以再凍一次的記錄不算凍結,
所以重開必須是一個被看見的動作,不是重跑腳本的副作用。

### 凍結之後真正的風險我另外守了一道

不是有人改那個 JSON —— 沒有人會改。是**有人改它描述的程式**,
而記錄安靜地變成一份描述著已不存在之系統的文件。你在 W-27 §5 講過這是兩者中
較危險的那個,理由是 PREREG 活得比程式久。

`tests/test_w29_prereg_frozen.py`(4 項)因此逐項比對:

1. 磁碟上的記錄仍雜湊得出自己的 digest;
2. **把記錄推進被篡改的狀態**(把 `Q-E.resolved` 從 4 改回 3,其餘不動)
   —— 那正是事後最像「善意修正」的那種編輯 —— 斷言它被偵測到,
   並以一次未篡改的往返作對照,證明失敗來自編輯而不是複製;
3. 每個 `resolved` 值仍等於實作它的常數(`DwellConfig().steps`、
   `R3_CALIBRATION_SCALE`、`REWARD_SCALES[0]`、`REWARD_SCALES[1]`);
4. 取樣點與動作版本的措辭,與 `CollapseSample` / `EpisodeLog` 的**結構**對得上,
   而且 `steps_per_episode`、`epsilon_decay_episodes`、`episodes` 三個
   被那段措辭引用的數字仍是記錄裡的那三個。

第 3 項是核心:它讓「凍結後改常數」變成一次紅燈,而不是一次沒有人注意到的 commit。

---

## D. 帳本與雜湊

`P-23` 那一列已改寫:原本的「為何取第一步」整列撤下,換成
「為何取兩點」、「為何原理由不成立」、「貪婪 vs 執行」三列,並補上
缺樣本拋錯的處置與兩個新測試。雜湊已刷新:

| 檔案 | 目前 sha256(前 16) | 行數 |
|---|---|---|
| `src/mcrl/algorithms/modqn.py` | `dc9cd98f33049e21` | 1,130 |
| `src/mcrl/runtime/trainer_spec.py` | `07bffee999e20926` | 268 |

全套測試:**751 passed, 1 skipped**(6 分 29 秒)。G-6 grep 閘零命中。

---

## E. 剩下

**P6 與 9000 回合的訓練。** 兩者都是重計算,要在 Ubuntu server 上另開對話跑
—— 單次約 9.9 小時,含學習率掃描與 baseline 臂約 40 小時。

依 B17,這一跑不只是產 baseline 數字,是**整條貢獻線的 go/no-go**:
若新 baseline 不崩潰,「協調是 EE 大槓桿」不會重現,catfish 要打破的同質化
可能不存在。現在四項崩潰指標在兩個取樣點、以貪婪與執行兩種讀法都有記,
那一題跑完就能答,不必重跑。
