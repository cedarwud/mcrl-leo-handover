# PREREG 草案(W-13)— 第一份 baseline MODQN 預先註冊

**狀態:草案。尚未凍結。**
**⚠ 任何 probe(含 P1)在本文件凍結之前不得執行**(SDD §7.1)。

依 SDD §7 / §7.1 與 2026-08-22 的作者裁決編寫。
本檔只列**需要被凍結的東西**與**其現況**;推導與量測在 `EPHEMERIS-NOTES.md`、
`D2-NOTES.md`、`PATCH-LEDGER.md`。

出處類別:**P** 原文明載 / **P′** 其他已發表來源 / **D** 推導 / **S** 自訂(須揭露)/ **X** 偏離。

---

## 0. 凍結狀態總表

| # | 項目 | 值 | 類別 | 狀態 |
|---|---|---|---|---|
| 1 | 星曆檔集雜湊 | `file_set_sha256`(373 檔) | — | **可凍結**,產生器已就緒 |
| 2 | 時間切分 | 分塊交替 7 d + 禁運 1 d | **S** | **待凍結**(作者已裁決方案) |
| 3 | 抽樣分布 | 有檔日期均勻 × 時刻均勻 | **S** | **待凍結** |
| 4 | D2 門檻 | `Thresh1` 1500、`Thresh2` 1100、`Hys` 50 km | **S** | **待凍結** |
| 5 | TTT | 1 步(1 s) | **S** | **待凍結** |
| 6 | `Thresh2` sweep 軸 | {900,1000,1100,1200,1300} km | **S** | **待凍結** |
| 7 | outage 門檻 | `1e-3` | **S** | **⚠ 待凍結,且 P1 之前必須凍結** |
| 8 | dwell `N` | 待測(P2) | **S** | **開放**(Q-E) |
| 9 | `r3` 重新校準尺度 | 待測 | **S** | **開放**(Q-D) |
| 10 | 學習率 `α` | **受控變因**,不取預設 | **X** | **待凍結為變因網格** |
| 11 | 狀態維度 | 125 | **D** | **已定** |
| 12 | TLE 畸形上限 | `1e-3` | **S** | **待凍結** |
| 13 | 高度下限 | 300 km | **S** | **待凍結** |

---

## 1. 星曆(SDD §3.1、F3)

```
tle_root            ~/demo/tle_data/starlink/tle
files               373(2025-07-27 … 2026-08-20,日曆跨度 390 天,缺 17 天)
file_set_sha256     由 mcrl.env.ephemeris.build_freeze_manifest() 產生
sgp4                版本 + accelerated 旗標 + gravity_model = wgs72
start_utc           每回合由抽樣器抽,分布如下
time_step_s         1.0                                    (P, Table I)
steps_per_episode   10                                     (P, Table I / F1)
max_tle_age_h       24.0                                   (S, F3)
epoch_search_days   1                                      (S)
```

**`epoch_search_days = 1` 不是裝飾**:單一日檔的 epoch 橫跨約 21 天,
單看一檔的 24 h 覆蓋率會從 97% 掉到 64%,所以「取 epoch 最近者」必須跨檔窗口。

**TLE 畸形記錄處置**:隔離(quarantine),單檔比例上限 `MAX_MALFORMED_RECORD_FRACTION = 1e-3`(**S**)。
語料實測:3,545,756 筆中 1 筆畸形(`starlink_20260528.tle`,BSTAR 指數溢位)。

## 2. 時間切分與抽樣(F3,2026-08-22 裁決改版)

```
scheme              block-alternating-with-embargo
block_days          7                                      (S) ← 凍結
embargo_days        1                                      (S) ← 凍結
first_block_part    train                                  (S) ← 凍結
```

實測分配:**train 166 檔 / test 160 檔 / 禁運 47 檔**;最近的 train–test 日期相距 **2 天**。

**為何改**:原本的連續切分讓 test 的星座比 train 大 12.6%、低 25.1 km(兩個位移同向)。
分塊交替把兩者壓到 ×0.988 與 +5.7 km,且殘差在不同抽樣量下**換符號** ⇒ 是雜訊不是結構。

```
episode_start_sampling
  date        uniform over AVAILABLE file dates in the part(不是日曆區間)
  time_of_day uniform over [0, 86400) s, floor-snapped to time_step_s
```

**必須是「有檔日期」**:17 天缺檔佔 4.4%,在日曆區間上抽會讓那 4.4% 的回合
被迫用鄰日元素,等於偷偷改變齡期分布。

## 3. D2 選星(F4,§3.2)

```
event               3GPP TS 38.331 D2
baseline_uses       候選側 only(D2-2 進入 / D2-4 離開)
thresh1_km          1500.0     (S) ← C4 用,baseline 不接
thresh2_km          1100.0     (S) ← 凍結;同時是結果圖 sweep 軸
thresh2_sweep_km    900, 1000, 1100, 1200, 1300            (S) ← 凍結
hysteresis_km       50.0       (S)
ttt_steps           1          (S) = 1 s(3GPP 離散集 640 ms 配 1 s 時槽)
min_altitude_km     300.0      (S)
ml2_definition      斜距(UE↔衛星)
warmup_steps        max(ttt_steps, 1) = 1                  (S) ← 凍結
```

**揭露文字(裁決 2026-08-22)**:`Thresh2 = 1100 km ≈ 21.8°`(量測高度 485 km),
**不是** F4 原本以 550 km 算的 25.8°。因可見高度有分布,嚴格說是約 **18°–25° 的帶**。

**`warmup_steps` 必須凍結**:冷啟動閂鎖會讓每回合第 0 步全員無候選,
在 PATCH P-03 下丟掉 10% 決策步,是回合邊界的假象而非幾何。

## 4. 動作與狀態(§4A)

```
L_w                 4                                      (P, B12)
J_w                 7                                      (D)
C = L_w · J_w       28                                     (D)  ← 網路輸出寬度,不動
V(指向格數)        39                                     (D, F5)
state_dim           125 = 4·28 + 13                        (D, §4A.6)
hidden / activation (100, 50, 50) / tanh                    (P, §IV)
slot ordering       現任優先 → D2 餘裕遞減 → NORAD 破平手,**無遲滯**
r2 判定             實現關聯 (norad_id, cell_id),**絕不比較索引**
no-op sentinel      -1(空遮罩;不入 replay)
```

**`V = 39` 的措辭(裁決 2026-08-22)**:F5 的「留有合理餘裕」**撤回**。
量測覆蓋曲線:550 km 需 34 格(非面積比估的 29),485 km 需**恰好 39** 格 ⇒ `V=39` 給 **95.5%**。
**結論(`V=39` 可用)不變;不得再宣稱有餘裕。**

## 5. outage 門檻(§4A.5a(4),2026-08-22 升格為門檻)

```
outage_rate_ceiling  1e-3      (S)  ← ⚠ P1 之前必須凍結
denominator          decision_steps_seen(逐使用者逐步)
numerator            no_op_transitions_skipped + all_invalid_next_transitions_skipped
verdict              rate > ceiling ⇒ semi-MDP 為**強制**,不是可選
```

**為何是門檻而非注意事項**:outage 期間 `r1≈0`、`r2=0`、`r3=0` **全部讀起來中性**;
若再截斷未來,outage 就變成免費 —— 正是 §4A.4 用 re-entry `φ2` 堵的漏洞。
丟棄等於從另一側把同一個洞打開,agent 會**永遠學不到 outage 有代價**。

**現況**:D2 這一側的 starvation 率量到 **0.0000**(四個 epoch × 五個 sweep 點)。
最終判定須等完整遮罩(含格覆蓋與鏈路可行性,W-06)接上。

## 6. 訓練超參數

| 參數 | 值 | 類別 |
|---|---|---|
| 折扣 `β` | 0.9 | **P** |
| 批次 | 128 | **P** |
| 回合數 | 9000 | **P** |
| 回合長度 `H` | 10 | **P**(F1) |
| 目標權重 `Ω` | (0.5, 0.3, 0.2) | **P** |
| 目標網路同步 | 每 50 回合 | **S** |
| Replay 容量 | 50,000 | **S** |
| `ε` 排程 | 1.0 → 0.01,線性 **2000** 回合 | **S** |
| **學習率 `α`** | **受控變因**,不得取任一邊預設 | **X** |
| TD target | MODQN 式 (16) vanilla,**每目標各自取 max**,含 done 項 | **P**(B1) |

⚠ `trainer_spec.py` 的 `epsilon_decay_episodes` 預設仍是移植來的 **7000**;
參數規格 §6.1 指出註冊表 `REP-004` 的 7000 已過時,程式與論文皆為 **2000**。
**W-13 必須以 2000 覆寫,並在 PREREG 明載。**

**`α` 的網格**:P6 規定跑 `{0.01, 0.003, 0.001}`,並須報告 §6 G-3 四項
(`active_beam_count`、`argmax_agreement`、**正規化後的** `q_margin`、`q_entropy`)。

## 7. 禁用清單(§8,G-6 以 grep 零命中驗收)

拍賣式解碼、capacity penalty、`v_max`/`k_cap`、執行遮罩 `m^e`、
`χ`+z-score 預設開啟、Double-DQN 共用純量化動作、任何形式的 catfish。

```
catfish_enabled     false
state_aug           false
decode              argmax
```

## 8. 仍開放(量測後才能填)

| # | 項目 | 卡住誰 |
|---|---|---|
| Q-D | `r3` 重新校準的尺度取法 | W-07 |
| Q-E | dwell `N` 的最終值 | P2。⚠ 可行性論證用 **≥10° 仰角下的 6.3 min**,不是地平到地平的 10.5 min |

## 9. §7.1 檢查表(第一個 probe 之前)

- [x] 模擬器/TLE/時間的雜湊產生器(`build_freeze_manifest`)
- [ ] 使用者與種子的雜湊
- [ ] 參考策略(probe 為資料盲,只用固定參考策略)
- [ ] **完整的 probe 網格**
- [ ] estimand、彙總方式
- [ ] **門檻,或決定性的選取映射** ← outage 1e-3 在此
- [ ] 停止與重試規則
- [ ] **不可存取的、獨立的留出產生器 + 已承諾的種子**

> **在觀察 P1 之後才選門檻即為洩漏,除非該映射事先凍結。**
