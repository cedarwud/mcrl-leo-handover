## 判斷

我重新檢查主 session、CF3PILOT 的最新程式、server workspace、pre-measurement、smoke、100-episode diagnostic 與實際 checkpoint 後，結論是：

> **「再 1–1.5 小時可以開始 full pilot」從純工程工作量來看仍有可能，但原本的說法確實漏算了幾個 launch-control 問題。現在不能直接執行 12 個完整訓練程序。**
>
> **演算法主體已經大致完成；真正可能浪費 500–1000 episodes 的風險，現在集中在 checkpoint／learning gate／多程序啟動控制，而不是 Catfish source 還沒做好。**

目前應該是：

* **source 選擇：已通過**
* **TLE／評估一致性：已通過**
* **基本 trainer：已通過 smoke**
* **100 episodes 實際垂直測試：已完成**
* **完整 12-run launch：尚未開始**
* **還有 4 個必修問題與 2 個建議檢查**

所以此刻是 **NO-GO for full launch，GO after final hardening**。

---

# 一、現在已經完成到哪裡

## 1. 三個 source 在 pinned TLE 上重新量過，沒有隱藏的 source gate

固定使用：

```text
TLE hash:
427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9
```

正式 pre-measurement：

```text
/home/sat/mcrl-v025-cf3-pilot-ws/premeasure/calibration.json
```

結果：

| source                |          pooled EE | H_inter |  served | beams |
| --------------------- | -----------------: | ------: | ------: | ----: |
| C1 `A m=2dB`          | **112.196 Mbit/J** |  0.5514 | 0.99775 | 62.98 |
| C2 `A m=12dB`         | **100.988 Mbit/J** |  0.2280 | 0.99663 | 71.55 |
| C3 `B1_NO_NEW_BEAM`   | **104.190 Mbit/J** |  0.3534 | 0.99808 | 38.57 |
| frozen trained policy |      93.903 Mbit/J |  0.2260 | 0.99867 | 66.63 |
| random                |      51.866 Mbit/J |  0.6896 | 0.93683 | 76.43 |

三個 source 都：

* 未超過 C-H `0.6016`
* 服務率未比 trained policy 低超過 0.5 percentage point
* 在 pinned archive 下仍維持原本的物理角色

所以**不需要再等 source feasibility**。

---

## 2. Smoke 已通過

完成的 smoke：

* A0 seed 0
* A1 seed 0、1、2
* A2 seed 0
* A3 seed 0

全部：

* status `complete`
* 沒有 exception
* 沒有 NaN／Inf
* checkpoint 能寫
* evaluation 能載入
* 同 checkpoint 重評估為 bit-identical
* learning-check barrier 在 smoke 下成功通過

Smoke wall time：

| arm | 3 episodes |
| --- | ---------: |
| A0  |     約 19 秒 |
| A1  |  約 19–38 秒 |
| A2  |     約 34 秒 |
| A3  |     約 34 秒 |

---

## 3. 100-episode production-config diagnostic 已完成

這一點很重要：**它其實已經是正式設定下的前 100 episodes 訓練，不只是 smoke**，原計畫是之後從 episode 100 繼續。

實測：

| arm      | 100 ep wall time | RSS after save | resume checkpoint |
| -------- | ---------------: | -------------: | ----------------: |
| A1 OFF   |            174 秒 |        1.81 GB |             80 MB |
| A2 CF3   |            657 秒 |      約 4.01 GB |            313 MB |
| A3 NULL3 |            657 秒 |      約 4.02 GB |            313 MB |

A2／A3 的四個 replay buffers：

* main：已飽和至 50,000
* C1：50,000
* C2：50,000
* C3：50,000

因此 episode 100 已經測到接近 steady-state 的 replay memory，而不是只測空 buffer。

### Batch composition 正確

A2／A3 在前 100 episode 累積：

```text
main rows: 112,887
C1 rows:     4,995
C2 rows:     4,995
C3 rows:     4,995
```

正好對應每次：

```text
113 main + 5 C1 + 5 C2 + 5 C3 = 128
```

### Q 尺度沒有明顯爆掉

Episode 100 的 transformed score，B／E term約各占一半：

| arm | B term share | E term share |
| --- | -----------: | -----------: |
| A1  |       49.85% |       50.15% |
| A2  |       52.00% |       48.00% |
| A3  |       49.15% |       50.85% |

所以目前沒有：

* energy scale 吞掉 bits
* bits scale完全壓過 energy
* loss 爆炸
* source data完全沒抽到

---

## 4. 我另外用既有 `cf3_eval.py` 唯讀評估了 episode-100 checkpoint

輸出只放在 server `/tmp`，沒有修改專案。

| arm，seed 0   | ep100 greedy pooled EE | H_inter |  served |
| ------------ | ---------------------: | ------: | ------: |
| **A1 OFF**   |      **95.209 Mbit/J** |  0.4713 | 0.99596 |
| **A2 CF3**   |      **84.548 Mbit/J** |  0.4807 | 0.99471 |
| **A3 NULL3** |      **82.390 Mbit/J** |  0.4181 | 0.99558 |

目前形狀是：

```text
A1 > A2 > A3
```

但這只有：

* 100 episodes
* 1 seed
* 仍在早期學習
* eta 尚未更新
* 尚未到預宣告的 ep500／ep1000 判讀點

所以不能拿來停止或改設計。

值得記住的是：

> **目前尚未看到 Catfish bundle 超過 OFF 的早期信號；只看到 directed source 比 random source稍好。**

這不是程式錯誤的證據，但也不能再說成功機率已經很高。

---

# 二、full launch 前有四個必修問題

## 必修 1：episode-500 learning-check failure path 有明確 off-by-one bug

相關位置：

```text
src/mcrl/algorithms/cf_ratio.py
CFRatioTrainer.train_cf()

scripts/run_cf3_pilot.py
except LearningCheckStop
```

目前順序是：

1. episode 500 已經完成 rollout 與 update
2. `quarter_update()` 呼叫 learning gate
3. gate 若失敗，直接 raise
4. episode 500 的 log 還沒有被 append
5. driver catch 後使用：

```python
done = len(logs) + 1
save(done)
```

結果會是：

```text
status episodes_completed = 500
resume next_episode = 500
logs length = 499
```

如果之後讀取，driver 自己會因：

```python
len(logs) != start
```

而拒絕 resume。

即使 learning check失敗後本來不打算繼續，仍有兩個問題：

* 第 500 episode 的完整 log 遺失
* status／checkpoint／logs三者互相矛盾

這會使「為什麼被 gate停止」的報告不完整。

### 必須先修

應改成其中一種：

* gate前先正式保存 episode log，再執行 gate；
* 或 catch時把當前 episode log一併寫入；
* 不能用 `len(logs)+1` 偽造 completed count。

要新增一個 forced-failure test，明確驗證：

```text
gate at episode 2 fails
status episodes_completed == 2
resume next_episode == 2
len(logs) == 2
episode IDs == [0, 1]
```

這是目前最明確的 runtime bug。

---

## 必修 2：多程序同時寫 `DECISION.json` 有 race condition

目前每個 A1／A2／A3 process到 episode 500 都會做：

```python
if not dfile.is_file():
    C.write_json(dfile, decision)
```

而 `C.write_json()` 固定使用：

```text
DECISION.json.tmp
```

作為 temp file。

episode 500時可能有多個 process同時：

1. 都看到 `DECISION.json` 不存在
2. 都寫同一個 `DECISION.json.tmp`
3. 都嘗試 rename

Smoke中沒有撞到，但 smoke只有很短的時間窗口；正式會有 9 個 CF process。

### 必須先修

最簡單的方法：

* 只允許 `A1-s0` 寫正式 decision；
* 其他 process只等候與讀取；
* 或使用 file lock／`O_EXCL`；
* temp filename加入 PID，不共用固定 `.tmp`。

另外 `DECISION.json` 必須記錄：

* final code commit
* calibration SHA
* TLE SHA
* A1三個 seed值
* random reference
* gate episode

否則可能讀到舊 run的 decision。

---

## 必修 3：resume fingerprint 沒有 code commit／source hash

我實際讀了目前 A1 status的 fingerprint，只有：

```text
arm
seed_index
seeds
config
settings
calibration_sha256
tle_file_set_sha256
prereg_digest
smoke
```

**沒有：**

* code commit
* `cf_ratio.py` hash
* `cf_sources.py` hash
* `run_cf3_pilot.py` hash
* declaration／amendment hash

所以如果 server tree在 episode 100後被更新，舊 resume state仍可能被新 code接受。

這正好會發生：目前還需要修 learning-gate bug。若直接改 tree再 resume現有100-episode state，fingerprint抓不到。

### 最安全的處理

建立 final commit後：

1. fingerprint加入 `code_commit` 與核心檔案 hash。
2. 建立 root-level：

```text
RUN-MANIFEST.json
```

至少包含：

```text
commit
cf_ratio sha256
cf_sources sha256
driver sha256
calibration sha256
TLE sha256
declaration sha256
amendment sha256
```

3. launch／resume時全部 fail-closed比對。
4. **在 final commit下重新跑 seed-0 的100-episode diagnostic。**

重新跑的額外成本約：

* A1：3分鐘
* A2／A3並行：11分鐘

也就是約 11–15 分鐘，遠小於之後發現 mixed-code run而重跑1000 episodes。

---

## 必修 4：必須做一次真正的 process-level resume vertical test

目前已有的 resume test是 Python內部：

```text
train 2 ep
state_dict
fresh trainer
resume to 4 ep
compare weights
```

這測到 trainer state，沒有測完整 driver：

* `status.json`
* `episode-logs.json`
* `resume.pt`
* `policy checkpoint`
* `--stop-after`
* launcher
* stale PID
* root directory
* source RNG
* fingerprint

現在 episode-100 state正好可用，但不要直接拿正式 state試。

### 必須先做

在獨立 temp root：

```text
A2 run to episode 2 or 3
stop
resume one episode
```

驗證：

```text
status episodes_completed 正確
logs連續且無重複
resume next_episode正確
source buffers有接續
NULL RNG／source RNG接續
policy checkpoint可載入
第二次 launch不會重開已在跑的程序
```

這個測試只需數分鐘。

---

# 三、兩個強烈建議檢查

## 建議 1：在滿 buffer 狀態下測一次 quarter calibration

A2／A3 episode 100時：

* RSS 已約 4.02 GB
* MemoryMax 是 5 GB
* main＋3 source buffers都已達50,000
* 313 MB resume checkpoint已成功寫出

代表普通 episode與 checkpoint save目前能過。

但尚未在這種滿 buffer狀態下執行：

```text
24-episode calibration
+ lambda update
+ checkpoint save
```

正式第一次會在 episode 250。

### 建議做法

載入 episode-100 A2的 copy，執行一次：

```text
measure_on_calibration()
```

在相同 `MemoryMax=5G` 下記錄：

* peak RSS
* cgroup `memory.events`
* wall time
* 是否有 OOM／high event
* calibration後再 save一次是否成功

如果超過4.7–4.8 GB，應在 full launch前：

* 使用更緊湊的 replay serialization；
* 或適度提高 source-arm的 per-process cap；
* 或錯開 checkpoint／calibration時間。

Server整體資源不是問題：

```text
20 CPU cores
約 85 GiB available RAM
約 1.8 TB free disk
```

風險是**單程序5 GB cap**，不是整台 server。

---

## 建議 2：launch script需再做一次 dry run

目前：

```text
/home/sat/mcrl-v025-cf3-pilot-ws/launch.sh
```

基本上有：

* complete skip
* live PID skip
* resume support
* 12 specs
* pinned TLE
* systemd MemoryMax

但仍建議補：

```bash
set -euo pipefail
```

以及：

* root manifest檢查
* PID不只 `kill -0`，還要核對 command line／cwd
* stale PID不能因 PID reuse誤判為仍在跑
* learning-check directory必須不存在，或 fingerprint完全一致
* full launch前列出「3個resume＋9個fresh」，要求正好12個 unique run
* launch後逐一檢查12個 status fingerprint相同
* 任何一個 process啟動失敗立即報錯，不默默繼續

目前 PID file在 process完成後不會自動刪除，因此只用 `kill -0` 不是最穩妥的。

---

# 四、哪些風險不是 launch bug，但會影響結論

## 1. C2目前實際是 inactive

Episode 100：

```text
lambda = 0
Q_H term share = 0
移除 Q_H 後 argmax變化 = 0
```

這符合原先預期，因為目前 policy的 H_inter仍低於0.6016。

因此即使 A2最後贏：

* C2 source transitions仍會透過 common replay訓練 B／E／H
* 但不能說 `Q_H` head真的參與了動作選擇
* 更不能說三個 Catfish都各自活躍

這不是啟動錯誤，而是方法本身可能出現的結果。

---

## 2. C3的 energy credit仍然偏弱

已完成的 `dE_sys` diagnostic：

* 847個與 incumbent不同的 C3 move
* 35.8% 的 energy差異**恰好為0**
* 59.5% 落在 step energy的 ±1%內
* 中位數約 `−1.21 J`
* 但也有一部分大幅正／負差異

所以 equal-share `Q_E` signal對許多單一 action接近 common team signal。

這表示：

> 如果 C3後來沒有正 marginal，不能直接下結論「consolidation Catfish無效」；也可能是 credit assignment不夠敏感。

不需要因此取消這次 bundle pilot，但後續 drop-C3前必須先處理。

---

## 3. C1／C2仍是同一 hysteresis family的兩個 threshold

CFSCREEN已證明：

* action disagreement是真實的，約35–55%
* 但 C2的 state coverage被 C1包含
* 兩者不是兩個完全不同的 state source

因此這次可以測：

```text
aggressive vs conservative hysteresis data
```

但不能把它包裝成兩個完全不同機理的專家。

---

# 五、episode-100結果應如何處理

目前：

```text
A1 OFF  = 95.21 Mbit/J
A2 CF3  = 84.55 Mbit/J
A3 NULL = 82.39 Mbit/J
```

可以看到：

* directed CF3比 random NULL3好約2.6%
* 但兩者目前都低於OFF

這可能表示：

1. source replay初期拖慢 adaptation；
2. 100 episode太短；
3. Catfish資料真的沒有幫助；
4. eta固定在110.5M時，source distribution使早期 value fitting變慢。

不能在看到這個結果後新增：

```text
若 ep250 A2仍低於A1就停
```

因為那會是看到早期結果後挑 stop rule。

現有事前規則是：

* ep500只檢查 A1是否比 random學得好
* 最終方向在 ep1000讀

這個規則應維持。

所以如果後來A2仍輸，這不是「訓練浪費」，而是 pilot正在回答的核心問題。

---

# 六、1–1.5小時估計是否合理

## 原本說法的問題

原本的1–1.5小時沒有充分計入：

* learning-gate failure path
* multi-process decision-file race
* code fingerprint缺失
* process-level resume
* 滿 buffer後的 calibration memory
* launcher stale-state hardening

所以**不能當成保證**。

## 以現在的進度重新估

目前 premeasure、smoke、dE、100-episode diagnostic都已完成。

如果上述問題修得順利：

| 剩餘工作                                  |       合理時間 |
| ------------------------------------- | ---------: |
| gate bug＋race＋fingerprint             |    20–40分鐘 |
| process-level resume＋launcher dry run |    10–20分鐘 |
| 滿 buffer calibration memory test      |    約5–15分鐘 |
| final commit、sync、重跑100-episode seed0 | 約12–20分鐘並行 |
| launch確認                              |    約5–10分鐘 |

因此：

> **從 Claude session恢復後，再約45–90分鐘安全啟動 full run，確實是合理範圍。**

但前提是沒有在 memory／resume測試中發現新問題。

## 啟動後多久完成

A2／A3目前：

```text
100 episodes ≈ 11分鐘
```

單純線性推算1000 episodes約110分鐘，但還要加入：

* episode 250／500／750／1000 calibration
* checkpoint I/O
* 12 process同時競爭20個CPU cores
* episode 500 barrier

較現實的 full pilot wall time是：

> **啟動後約2–4小時。**

不是1–1.5小時完成；1–1.5小時只是到安全啟動。

---

# 七、給 Claude session 的硬性指令

恢復 CF3PILOT 後，不要立刻執行完整：

```text
launch.sh
```

應先要求它完成：

```text
1. Fix the learning-check failure-path log/checkpoint off-by-one.
2. Make DECISION.json single-writer or lock-protected; reject stale gate files.
3. Add code commit and core-file hashes to the resume fingerprint and RUN-MANIFEST.
4. Run a real driver-level stop/resume test, not only an in-memory trainer test.
5. Exercise one saturated-buffer calibration + save under MemoryMax=5G.
6. Harden and dry-run launch.sh; verify exactly 3 resumed + 9 fresh runs.
7. Freeze a final commit, resync the server tree, rerun the seed-0 100-episode
   diagnostic under that exact commit, then launch all 12.
```

## 最終裁決

**目前不建議直接啟動完整1000-episode batch。**

不是因為三個 source還沒準備好，也不是因為 learner顯然壞掉；而是已找到幾個會讓：

* episode 500 artifact不一致
* 多程序在 gate處碰撞
* resume跨 code version
* stale run被誤認

的具體控制面問題。

這些都屬於**數十分鐘等級的修補與驗證**，不是重新設計幾天。

完成後再啟動，才能 reasonably確保：

> 如果結果不好，是 Catfish pilot真的沒有正效果，而不是訓練跑完才發現 checkpoint、gate、RNG、code version或launcher出了問題。
