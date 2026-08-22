# PREREG 草案(W-13)— 第一份 baseline MODQN 預先註冊

**狀態:草案。尚未凍結。**
**⚠ 任何 probe(含 P1)在本文件凍結之前不得執行**(SDD §7.1)。

> ## 凍結器已實作(W-13):`src/mcrl/runtime/prereg.py`
>
> 本文件是**人讀的草案**;可執行的凍結由 `freeze_prereg()` 產生,
> 它做三件文件做不到的事:
>
> 1. **每個開放問題都必須先凍結「決定性的選取映射」** —— 不是答案,是**產生答案的規則**。
>    §7.1 寫的是「門檻**或**決定性的選取映射」,那個「或」是關鍵:
>    Q-E(dwell `N`)與 Q-D(`r3` 尺度)**正是 probe P2/P3 要決定的東西**,
>    而 probe 又必須等 PREREG 凍結後才能跑 —— 要求先有值就循環了。
>    必須事先固定的是「從 probe 輸出到決定的映射,寫在輸出存在之前」。
>    (⚠ 這一點我最初實作錯了:原本讓 Q-D/Q-E 未關閉就擋住凍結,那會讓整條流程卡死。)
> 2. **對留出種子做承諾而不揭露它。** 凍結時只存 `sha256(seed ‖ salt)`;
>    日後要用留出集必須拿出對得上的種子 —— **看完 P1 才挑的種子對不上**。
>    §7.1 的「不可存取的、獨立的留出產生器與已承諾的種子」因此變成可檢驗的。
> 3. **自我雜湊。** 凍結後任何編輯都**可偵測**,而不是可爭辯。
>
> **參數區段是從實作它們的模組讀出來的,不是手抄的** —— 手抄的 PREREG 會和程式漂開,
> 而人信的是文件。只有真正屬於預先註冊的東西(probe 網格、門檻、停止規則、參考策略)
> 由呼叫端提供。

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
| 8 | dwell `N` | 待測(P2) | **S** | **開放**(Q-E);`DWELL_N_IS_FROZEN=False` 擋住凍結器 |
| 8a | 大氣衰減模型 | 餘割律 `A_zenith/sin α`(TR 38.811 式 6.6-8) | **P′** | **待凍結**(C-4 已裁決) |
| 8b | 天頂大氣衰減 `A_zenith` | **0.25 dB** @ 20 GHz(= 0.5 × sin 30°,TR 38.821 SC 6) | **P′** | **待凍結**(C-4);~~`H_atm = 10 km`~~ 已撤回 |
| 8e | `L_c`(閃爍) | TR 38.811 表 6.6.6.2.1-1(20 GHz 對流層),線性內插 | **P′** | **待凍結**(C-8 修訂版)。確定值,無隨機性 |
| 8e2 | `L_s`(遮蔽) | 零均值 dB 高斯,σ 依表 6.6.2-3(Ka LOS)內插 | **P′** | **待凍結**(C-8 修訂版)。**隨機項 ⇒ 與 `K_R` 共用種子集** |
| 8f | Rician `K_R` | **20 dB**(單位均值,展幅約 ±1 dB) | **D⚠**(Table I 的 `φ = 20 dB` 讀作 K 因子,屬本專案解讀) | **待凍結**(C-9)。**是隨機抽樣 ⇒ 必須進種子集** |
| 8g | 衰落抽樣粒度 | 逐(使用者, 衛星)每步一抽,按 NORAD 排序 | **S** | **待凍結**(W-17)。同一顆衛星的所有波束共用一條路徑 |
| 8c | 貝索路由門檻 | 34.0 | **S** | **待凍結** |
| 8d | G-2 比較對象 | TR 38.821 SC 6(LEO-600, 20 GHz DL) | — | **待凍結**(選取規則見 L2-2) |
| 9 | `r3` 重新校準尺度 | 待測 | **S** | **開放**(Q-D);`R3_SCALE_IS_FROZEN=False` 擋住凍結器 |
| 9a | 每衛星同時波束上限 | **不存在** | — | **已裁決 2026-08-22:刪除,不留常數或參數** |
| 10 | 學習率 `α` | **受控變因**,不取預設 | **X** | **待凍結為變因網格** |
| 11 | 狀態維度 | **112 = 4C** | **P** | **C-1 已裁決**;13 維契約區塊降為消融開關,**預設關** |
| 11a | 39 個指向格 `cell_id` | 字面清單(見 §4a) | **D** | **C-3 已裁決:必須逐字凍進 PREREG**;量測覆蓋 95.17% |
| 11b | 狀態 `γ` 區塊的 provenance | `theta-current-interference-previous-step` | **S** | **待凍結**(W-17)。(4.1) 允許 cached provenance,但要求標記 |
| 11c | `p⁰` | **0.825 W** = `p_max/2` | **D** | **F-1 已裁決**。段增益預算 3.010 dB;⚠ 預算相對**段起始角度**量,不是對波束軸 |
| 11d | `P^N` 求和粒度 | **逐波束**二重和,過濾器 `z_{s,v}` | — | **F-2 已裁決**。舊式逐鏈路高 2.107–2.626× |
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

## 3a. 鏈路預算與天線(W-06)

```
f_c                 20 GHz                                 (P, Table I)
B                   500 MHz                                (P, Table I)
FRF                 3  ->  B^w = 166.667 MHz               (P' TR 38.821 / D)
theta_3dB           3.32 deg  FULL HPBW,型樣傳入一半      (P', 半角慣例 P-2)
G_0                 2000 (33.010 dBi)                      (P')
G_R,max             35 dBi                                 (P', Mendonca 2025)
G_R 包絡            32 - 25 log10(theta_deg),夾 [-10, 35]  (P', ITU-R S.465-6)
T_a / T_0 / NF      150 K / 290 K / 1.2 dB -> T_sys 242.294 K  (P')
A_zenith            0.25 dB @ 20 GHz                       (P', 見 §3b)
大氣模型            A_zenith / sin(alpha)                   (P', TR 38.811 6.6-8)
L_c                 TR 38.811 表 6.6.6.2.1-1,20 GHz 對流層   (P')  確定值
L_s                 零均值 dB 高斯,sigma 依表 6.6.2-3        (P')  隨機,與 K_R 同種子
                    (電離層閃爍與 clutter loss 皆排除,理由見 §3b)
K_R (Rician)        20 dB,單位均值                          (D, 屬解讀)
p^0 (段起始功率)    0.825 W = p_max/2                       (D, F-1)
每波束功率上限      1.65 W                                 (D, 由 p_sat 與 BO 綁死)
段增益預算          3.010 dB(相對段起始角度,不是對波束軸)
xi_max / BO         0.35 / 5 dB -> p_sat = 5.218 W          (S, 3.15a)
P_cir / P_BB        0.338 W 每波束 / 0.200 W 每衛星         (P', You Table II)
QoS floor           1 Mbit/s                               (P', TS 22.261)
貝索路由門檻        |mu| > 34 -> Miller 下降遞迴            (S, P-1/G-10)
```

### 3b. 大氣模型:**C-4 已裁決,改用 3GPP 餘割律**

論文與來源專案共用的 `3·d·χ/(10·h)` 展開是 `0.3·χ·(d/h_s)`,而 `d/h_s ≈ 1/sin α`
⇒ 等價於**厚 0.3 公里的大氣**,天頂只給 0.015 dB。控方裁定是**抄錯**。

我原本改的平板模型方向對,但 `H_atm = 10 km` 是自選的。**兩份已引用的 3GPP 文件
就給得出來,不用挑**:TR 38.811 式 (6.6-8) 給形式,
TR 38.821 Table 6.1.3.2-1(LEO 目標仰角 30°)+ Table 6.1.3.3-1 SC 6(0.5 dB)給數值
⇒ `A_zenith = 0.5 × sin 30° = 0.25 dB`,類別 **P′**。

實測:天頂 0.2500、30° 0.5000、25° 0.5916、10° 1.4397 dB。
`χ_atm = 0.05` 與 `3dχ/(10h_s)` 整列移進 Legacy provenance。

## 3c. dwell(W-05)

```
N                   待測 {2,3,4}                           (S) ← Q-E,P2 後才凍結
dwell_phase         正規化到 [0,1),0 為邊界步             (D)
re-key 規則         邊界時取當時最近的格為 j=0             (S, §4A.2)
可行性論證的服務窗  >=10 deg 仰角下 378 s(6.3 min p50)   ← 不是 630 s
DWELL_N_IS_FROZEN   False ← 為 True 前凍結器不得產出 PREREG
```

## 3d. 載量與 `r3`(W-07)

```
r3,u                -U_{b_u}                               (B13)
U_{b_u}             通過逐鏈路功率可行性之後的實際服務人數 —— 不是未經閘的 demand
狀態的 beam_loads   未經閘、允入前的全域 demand            (ASSUME-MODQN-REP-013)
載量鍵值            (norad_id, cell_id) —— **波束**,不是格 (P-17)
gamma_req(U)        2^(R_min*U/B^w) - 1,U 用 eligible 載量
連線恆等式          x = a·z  **兩閘**(C-11);m 只作決策時遮罩,不進恆等式
R3_SCALE_IS_FROZEN  False ← 為 True 前凍結器不得產出 PREREG
```

✅ **每衛星同時波束上限:已裁決刪除**(2026-08-22)。
`Σ_v z_{s,v} = V` 在原論文是**恆等式不是上限**;上限是舊 repo 自己發明的。
啟用改為導出:`z_{s,v}(t) = 1{ U_{s,v}(t) > 0 }`,
資源約束由**逐鏈路功率可行性** `p_req > p_max`(1.65 W)承擔。
**不得為此保留任何常數或參數。** 見 `docs/R3-AND-EXECUTION-MASK-NOTES.md` §6。

```
beam_activation     z_{s,v} = 1{ U_{s,v} > 0 }             導出,無選擇步驟
p_max               1.65 W 逐波束                          (S)
可行性              p_req > p_max ⇒ outage_infeasible      逐鏈路,連續,無懸崖
每衛星波束數上限    不存在
衛星級總功率上限    不存在(另一個決策,需另一個出處)
```

## 4. 動作與狀態(§4A)

```
L_w                 4                                      (P, B12)
J_w                 7                                      (D)
C = L_w · J_w       28                                     (D)  ← 網路輸出寬度,不動
V(指向格數)        39,**39 個 cell_id 逐字凍結**          (D, C-3)
state_dim           112 = 4·28                             (P, 4.1 / 5.1)
契約區塊 13 維      消融開關,**預設關**                    (C-1)
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

✅ `epsilon_decay_episodes` 已於 **W-09(補丁 P-06)** 由過時的 7000 改為 **2000**。
核對依據:`family_b_r3/common_trainer.py:296` 為 2000,來源專案 9 份 resolved config
中 8 份為 2000,參數規格 §6.1 明指註冊表 `REP-004` 的 7000 過時。

**`α` 的網格**:P6 規定跑 `{0.01, 0.003, 0.001}`,並須報告 §6 G-3 四項
(`active_beam_count`、`argmax_agreement`、**正規化後的** `q_margin`、`q_entropy`)。

## 6a. W-09 之後的實作面事實

```
opt-in 介面        全部移除,不是設為 False —— 「本 repo 未實作」比「旗標為 false」更強
動作選取路徑        恰好一條(_select_unconstrained_actions)
更新路徑            恰好一條(update);休眠批次孿生已刪(P-11)
TD target 實作      在原始碼中恰好出現一次
有限性政策          唯一一套,fail-loud(P-3 / G-11)
狀態維度            112;契約區塊為消融開關,預設關,缺席不得拋錯(C-1)
```

## 7. 禁用清單(§8,G-6 以 grep 零命中驗收)

拍賣式解碼、capacity penalty、`v_max`/`k_cap`、
`χ`+z-score 預設開啟、Double-DQN 共用純量化動作、任何形式的 catfish。

⚠ **執行遮罩 `m^e` 已不存在**(裁決 C-11,2026-08-22)。

它在 2026-08-22 稍早被移出禁用清單並記為「保留為環境端帳務,連線恆等式維持三閘
`x = a · m^e · z`」—— **那一版已被控方撤回**:符號表汰換紀錄明載該修訂
「是助理裁決、非使用者授權」。定案是**兩閘 `x = a·z`**:
`m` 只作**決策時**遮罩(決定能選什麼),不進連線恆等式;
選上與被服務之間的閘是**逐鏈路功率可行性**,超過每波束上限即該步 outage。
等價性測試 `tests/test_c11_gate_order_equivalence.py` 釘住兩種順序在所有邊界情形一致。

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
~~F-1~~ / ~~F-2~~ **已裁決並實作**(`CONTROLLER-RULINGS-W17-2026-08-22.md`)。
outage 率 1.0 → **0.0000**,`assert_ready_to_train()` 通過,probe 可以跑了。

## 9. §7.1 檢查表(第一個 probe 之前)

| 項目 | 機制 | 狀態 |
|---|---|---|
| 模擬器/TLE/時間的雜湊 | `build_freeze_manifest()` | ✅ 有產生器 |
| 使用者與種子的雜湊 | `freeze_prereg()` 的 `sections` | ✅ 有欄位,值待填 |
| 參考策略(資料盲) | `ReferencePolicy` + `assert_data_blind()` | ✅ 有機制,值待填 |
| **完整的 probe 網格** | `REQUIRED_SECTIONS["probe_grid"]`,空的即拒絕 | ⬜ 待填 |
| estimand、彙總方式 | 同上 | ⬜ 待填 |
| **門檻或決定性選取映射** | `REQUIRED_SECTIONS["thresholds"]` | ⬜ 待填(outage `1e-3` 在此) |
| 停止與重試規則 | `REQUIRED_SECTIONS["stopping_rules"]` | ⬜ 待填 |
| **不可存取的獨立留出 + 已承諾的種子** | `HoldoutCommitment` | ✅ **已可強制執行** |
| Q-D / Q-E 的**選取映射** | `assert_selection_mappings_cover_open_questions()` | ⬜ 待填 —— 這是凍結的前提 |
| Q-D / Q-E 的**值** | `assert_ready_to_train()` | ❌ 兩項都還開著;**擋的是訓練,不是凍結** |

> **在觀察 P1 之後才選門檻即為洩漏,除非該映射事先凍結。**

### 資料盲的兩種破法,都已擋住

| 破法 | 擋法 |
|---|---|
| 用**未訓練的網路**當參考策略 | `assert_data_blind()` 只接受 `ReferencePolicy`。SDD §4 r2:未訓練網路的 argmax 由**初始化與特徵尺度**決定,量到的是初始化不是環境 |
| probe 讀取訓練產物 | 輸入清單中出現 `.pt`/`.pth`/`.ckpt`/`.safetensors` 即拋錯 |
