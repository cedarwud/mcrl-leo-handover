## 裁決

**這個加速方向值得採用，而且是目前最有效的加速方式。**
但需要把它視為一個已事先宣告的**靜態示範池／pre-filled replay 版本**，不能宣稱它只是把原本 streaming Catfish「完全等價地算在前面」。

更精確地說：

> 三個固定規則不再於主 learner 訓練時各自跑一套環境，而是先產生不可變的 `(state, action, B, E, H, next_state)` 資料池；A2／A3 訓練時直接抽取。
> 這對目前的 pilot 是合理且公平的，但它把方法從 online source streaming 改成了 offline/static source replay。

目前完整訓練尚未重新啟動；這個版本正在做最後的 process-level 測試與 agy 差異審查。

---

# 我實際確認到的狀態

Amendment 3 已正式寫下並 commit：

```text
commit 6e1458a5
.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md
```

實作目前在：

```text
/home/u24/papers/mcrl-leo-handover-cf3
branch: cf3/pilot-20260911
review-ready commit: f297334e
```

相關實作 commits：

```text
99252ef8  pre-generated immutable pools
d04d9dbe  修正 pool env/mobility seed range 重疊
f297334e  process-level 測試與 manifest 綁定
```

伺服器上的新 pool 已經全部產生完成：

```text
/home/sat/mcrl-v025-cf3-pilot-ws/pools
```

實測結果：

* 3 個 learner seed
* A2 的 C1／C2／C3
* A3 的 NULL1／NULL2／NULL3
* 共 **18 個 pool**
* 每個 **100,000 transitions**
* 總容量約 **1.7 GB**
* 18 個程序平行產生時，最慢一個約 **470 秒，約 7.8 分鐘**

各 seed 的 pool EE 也很穩定：

| pool                |       seed 0 |       seed 1 |       seed 2 |
| ------------------- | -----------: | -----------: | -----------: |
| C1 `A m=2dB`        |      111.27M |      110.89M |      111.58M |
| C2 `A m=12dB`       |      100.89M |      100.74M |      100.84M |
| C3 `B1_NO_NEW_BEAM` |      104.09M |      103.75M |      104.33M |
| NULL sources        | 約 52.1–52.6M | 約 52.0–52.2M | 約 52.2–52.3M |

這和先前 streaming buffer 中量到的：

```text
C1 約 111.5M
C2 約 100.1M
C3 約 104.4M
NULL 約 52M
```

非常接近，因此目前沒有看到嚴重的 marginal distribution shift。

一開始確實發現過 pool seed 碰撞：

```text
舊 mobility base 9_142_000
會與下一個 seed index 的 env range 重疊
```

但該批在任何 pool 完成前就已停止並封存；現在改為：

```text
env      = 9_141_000 + 1000*k + i
mobility = 9_161_000 + 1000*k + i
```

目前新產生的 18 個 pool 使用的是修正版。

---

# 為什麼這個方法基本上可行

三條 source policy 都是固定的：

```text
C1 = A m=2dB
C2 = A m=12dB
C3 = B1_NO_NEW_BEAM
```

它們只依賴自己環境裡的：

* gain
* incumbent
* previous loads
* legal mask

不會讀取 main learner 的：

* Q-value
* network weights
* eta trajectory
* training loss
* policy performance

因此，source transition 可以先計算，再由 learner off-policy 學習。

目前程式也做到了幾個重要條件：

* pool 儲存的是 raw `(B,E,H)`，eta 改變後仍可重新組合目標；
* pool arrays設為 read-only；
* 每個 minibatch仍然是：

```text
113 main
  5 C1
  5 C2
  5 C3
------------
128 total
```

* 三個 head共用同一個 vector batch；
* A2和A3的 pool具有相同數量與相同環境 seed schedule；
* A2與A3只在 source policy不同；
* pool SHA已放進 run fingerprint；
* resume state綁定 pool hash與pool length；
* pool不再被塞進每次 checkpoint，checkpoint與記憶體負擔都會明顯下降。

因此它不是只有「少跑三個 environment」而已，也會改善：

* checkpoint大小
* checkpoint寫入時間
* A2／A3 RSS
* 12個process同時執行時的memory pressure

---

# 但不能說它與 streaming 完全等價

Amendment 3目前「等價」的文字需要修正。

## 1. 原本 streaming buffer是會移動的 FIFO

原版本的每個 source buffer容量為50,000 transitions，大約50 episodes填滿。填滿後，它保留的是**最近約50 episodes**。

新版本則是在訓練開始前固定一個：

```text
100 episodes
100,000 transitions
```

的靜態池，從頭到尾不變。

所以兩者差別是：

| streaming                    | pre-generated         |
| ---------------------------- | --------------------- |
| support隨訓練時間移動               | support固定             |
| 初期資料集中於前幾個source episodes    | 一開始就能抽到全部100 episodes |
| 滿後只保留最近50k                   | 永久保留100k              |
| source epoch stream跟訓練進度一起前進 | source seeds完全獨立      |

這是**合理的設計變更**，不是錯誤；但不是逐位元等價的工程最佳化。

## 2. 「原本前50集沒有source data」其實不正確

原本 main replay大約在第二個decision step就超過batch size 128。

同時，每個source每step會產生約100 transitions，因此到第一次真正update時，source buffer也已經有約200 rows，足夠抽取5 rows。

所以 streaming版本其實也是從第一次update就能抽source data。

真正改變的是：

> static pool從第一次update就能從完整100-episode support抽樣；streaming版本第一次update只能從最前面一兩個episode抽樣。

這個文字建議在 Amendment 3中更正，否則之後會錯誤解釋早期learning curve。

## 3. 100k並不是由「總共抽50k」嚴格推導出來的

1000 episodes ×10 updates ×5 rows：

```text
約 50,000 source draws
```

但不同update之間允許重複抽到同一row，因此「抽50k」不代表需要50k或100k個不重複transition。

100k是合理的diversity設計值，但應寫成：

> 預先選定的pool size，可提供比總抽樣次數更大的support。

不應寫成「因此100k一定足以完全重現streaming」。

---

# 這對比較是否公平

## A2 CF3 對 A3 NULL3：公平

兩者都是：

* static pool
* 每seed三個pool
* 每pool 100k
* 相同環境seed schedule
* 相同source比例
* 相同sampling logic
* 相同checkpoint／eta／network

只差：

```text
A2：有方向的source policies
A3：random legal source policies
```

因此A2對A3仍能回答：

> 有方向的來源是否比同量的隨機來源更有用？

## A2 CF3 對 A1 OFF：也是合法比較，但問題改了

它回答的是：

> static directed-data prefill是否比沒有prefill好？

而不是：

> online streaming Catfish是否比OFF好？

這仍然符合目前 pilot「directed sources是否有用」的目的，也更接近DQfD／hybrid Q-learning的資料注入形式。

但若最終論文要聲稱的是**忠實RIS Catfish的online intervention**，之後仍需另外有faithful RIS comparator。這次結果不能直接替代。

---

# 我找到一個仍應在正式launch前補上的小缺口

目前 `RUN-MANIFEST.json` 綁定的是每個：

```text
*.npz
```

的SHA，但沒有綁定旁邊的：

```text
*.json
```

metadata。

問題在於NPZ本身只有transition arrays；以下資訊只在sidecar JSON中：

* source name
* source head
* source kind
* seed index
* seed list
* TLE hash
* generator commit
* transition count
* t0 observation hashes

`run_cf3_pilot.py`會讀JSON並檢查部分欄位，但JSON本身沒有被manifest hash綁住。

這不會自動讓現在的pool算錯，但在你這個專案已多次出現數字／條件誤綁的背景下，應在launch前補：

1. `RUN-MANIFEST.json` 同時記錄NPZ與sidecar JSON的SHA。
2. driver額外驗證：

   * `kind`
   * `head`
   * `source_index`
   * `transitions == len(pool) == 100000`
   * generator file hashes
3. 記錄pool是在 `d04d9dbe` 產生；並證明正式 `f297334e` 中實際生成pool的核心檔案bytes未變。

**不需要重新產生pool。** 只要綁定現有檔案與生成程式的hash即可，約幾分鐘。

---

# 現在還沒完成的兩個檢查

截至我最後檢查：

## Process-level test仍在跑

```text
scripts/cf3_proctest.py
```

它正在實際測：

* 完整driver stop→resume
* 不重複episode
* resume後weights bit-identical
* learning gate forced failure
* completed／next_episode／logs一致
* `DECISION.lock`
* launcher把真正的stopped run辨識為finished

這不是unit test，而是真launcher＋真driver的vertical test，應等它完成。

## 第二輪agy審查仍在跑

位置：

```text
.scratch/reviews/cf3-agy-2/
```

它正在review：

```text
e8a04ccf..f297334e
```

範圍只限：

* launch-control fixes
* static pool變更
* seed碰撞
* manifest
* failure swallowing
* pool實際載入路徑

在這兩個都綠燈前，不應啟動12個1000-episode runs；但也不需要再新增另一輪廣泛研究或審查。

---

# 是否還能再快

可以，而且目前最值得看的不是再減episode，而是下面兩個方法。

## 加速一：一次計算shared target Q

目前：

```text
src/mcrl/algorithms/cf_ratio.py:557–617
```

每個head在計算target時，都重新：

1. forward三個target networks以決定shared action；
2. 再forward自己的target network一次。

三個head合計每次update會做：

```text
3 × (3 + 1) = 12 次 target-network forward
```

實際只需要：

```text
Q_B(next)
Q_E(next)
Q_H(next)
```

各算一次，共3次，然後：

* 共用它們算argmax；
* 三個head各自gather同一action。

也就是能把target forward由：

```text
12 → 3
```

其餘online forward與backward不變。

這是數學上等價的cache，不改演算法。建議先做一個10–20 episode microbenchmark：

* targets逐位元或tolerance一致；
* weights在固定seed短跑後一致；
* wall time至少改善10–15%。

若有改善再合入。這很可能是static pool之後剩下最大的code-level加速點。

## 加速二：先測12-way concurrency，不要直接相信1.7秒／episode

目前已知：

* A1單獨：約1.74秒／episode
* 舊A2／A3 streaming：約6.57秒／episode
* 18-way streaming launch：每process慢約3倍
* 伺服器：20個physical cores，沒有SMT；8個高性能核、12個效率核

移除source environments後，A2／A3理論上會接近A1，但**目前尚未量過final static-pool code在12-way條件下的速度**。

在正式root之外跑一次：

```text
12 runs × 20 episodes
```

大約只需要幾分鐘，並比較：

1. 全12個一起跑；
2. 6個A2/A3綁高性能core，6個A0/A1放效率core；
3. 必要時8+4兩波。

選擇的是整批wall-clock最短方案，不是單process最快方案。

這是純排程，不改任何科學結果。

---

# 另外兩個次要加速

## 將非因果的progress evaluation移到訓練後

目前：

* episode 100：只為畫learning curve
* episode 250：lambda已依Amendment 2固定為0，eta也尚未更新，所以只是讀數
* episode 500：必須inline，因為learning gate與eta update
* episode 750：必須inline，因為eta update
* episode 1000：只記錄，不再套用

因此只有：

```text
500
750
```

需要阻塞training。

100、250、1000和A0的所有intermediate readings，可以從保存的policy checkpoint事後平行算。這不改weights，也不改eta trajectory。

對1000-episode pilot只會省數分鐘，但正式3000／9000集時比較有價值。

## 正式長訓練再把pool改為memory-mapped arrays

目前每個NPZ約99 MB，每個A2／A3 process會載入三個。

現在server有約88 GiB可用，問題不大。正式長run可改成：

```text
separate .npy fields
np.load(..., mmap_mode="r")
```

讓不同process共用OS page cache，減少啟動時間與RSS。

這不值得再延後今晚的pilot。

---

# 不建議用來加速的方式

目前不建議：

* 把1000 episodes砍成500；
* 把3 seeds砍成1；
* 拿掉NULL3；
* 拿掉A1 OFF；
* 降低evaluation episodes；
* 為了快而取消resume／manifest；
* 把三個source混成一個而失去來源身份。

這些不是工程加速，而是削弱實驗能回答的問題。

---

# 更新後的時間判斷

pool生成已經完成，所以之前「先花10分鐘生pool」現在不再是等待項目。

完成以下三件事後即可正式launch：

1. process-level test PASS；
2. agy diff review沒有INVALIDATES／BIASES；
3. 補上JSON metadata與generator provenance綁定。

再做一次幾分鐘的12-way throughput benchmark。

合理估計：

| 階段                             |                                時間 |
| ------------------------------ | --------------------------------: |
| 剩餘pre-launch收尾                 |          約15–30分鐘，取決於agy與proctest |
| 12-run ×1000 ep training       | **約45–90分鐘**，需以12-way benchmark校正 |
| final checkpoint evaluation＋報告 |                      約10–20分鐘，可平行 |

因此：

> **static pools的加速是真的，完整方向性結果有機會在正式launch後約1到1.5小時得到；包含launch前收尾與最後評估，較保守是約1.25到2小時。**

我的最終建議是：

> **保留Amendment 3；修正「完全等價」的說法；補綁sidecar metadata；等現有兩項檢查綠燈；做一次12-way短benchmark後直接launch。**

不要再為這個pilot增加新的廣泛科學gate。接下來最大的剩餘加速空間是**target-network forward共用計算**與**CPU affinity／並行度實測選擇**，而不是再縮小實驗。
